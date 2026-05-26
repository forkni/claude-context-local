# Scoped tracing-only OTel observability; rejected full OTel + metrics

Status: accepted
Date: 2026-05-23

We added OpenTelemetry distributed tracing to the pipeline, scoped to
traces only (no metrics in v1), using a lazy-import, default-off design.
Several alternatives were rejected or deferred.

## Context

This is a local-first, single-user stdio MCP server (`mcp_server/server.py`).
The primary observability question is "which pipeline stage is slow?" — a
traces-only question. Full OTel (11-file sprawl, MeterProvider, Prometheus
endpoint, 8-metric table) is over-engineered for the current audience.

## Decisions

### 1. Traces only in v1; metrics deferred

`SessionMetrics` (`mcp_server/metrics.py`) is left untouched.
`MeterProvider`, counter/histogram metrics, and `prometheus_endpoint_enabled`
are not implemented. Metrics are deferred to a documented v2, informed by
latency data from v1 traces.

### 2. Module location: `utils/observability.py`

The core module lives in `utils/`, not `mcp_server/`. `utils/timing.py`,
`search/*`, `chunking/*`, and `mcp_server/*` all import from `utils/` without
dependency inversion. `mcp_server/` code cannot be imported by `search/` code
(that would invert the layering).

### 3. OTLP default; console exporter always routes to stderr

The default exporter when enabled is `otlp` (network, never touches stdio).
The MCP server uses stdio transport (`mcp/server/stdio.py`): stdout is the
JSON-RPC channel. Any exporter that writes to stdout would corrupt the
protocol. The `_build_exporter` function always passes `out=sys.stderr` when
building a `ConsoleSpanExporter`. This is a hard guard, not a doc note.

### 4. `@timed` decorator as instrumentation vehicle

Five call sites in the existing pipeline already use `@timed`:
`embeddings/embedder.py` (embed_query), `search/search_executor.py`
(bm25_search, dense_search), `search/multi_hop_searcher.py`
(multi_hop_search), `search/reranking_engine.py` (neural_rerank).
Extending `@timed` to open a `traced_block` spans all five sites from a
single edit to `utils/timing.py`. The `timer` context manager was considered
but has zero call sites; it was not used.

### 5. Thread context propagation at one site

`bm25_search` and `dense_search` run in parallel worker threads
(`search/search_executor.py:_parallel_search`). `wrap_in_context(fn)` is
called on the two `submit()` arguments so child spans nest correctly under
`search.hybrid`. No other ThreadPoolExecutor sites need this.

### 6. Auto-detect from standard OTEL_* env vars

If any `OTEL_*` env var is set and `CLAUDE_OTEL_ENABLED` is absent,
`init_observability` treats this as enabled with `exporter="otlp"`. This
makes the server compatible with standard OTel infrastructure (Docker Compose
with a collector sidecar, Jaeger, Tempo) without requiring project-specific
env vars.

## Considered Alternatives

- **Full OTel with metrics and Prometheus** — deferred; over-engineered for
  a local-first tool. Metrics require a running Prometheus scraper or push
  gateway; this audience rarely has one.
- **Always-on tracing** — rejected; the OTel SDK adds ~5ms import overhead
  and non-trivial per-span allocation. Default-off preserves bit-for-bit
  equivalence with the pre-feature baseline.
- **`mcp_server/observability.py` location** — rejected; `search/` and
  `utils/` cannot import from `mcp_server/` without inverting the layering.
- **Log-only timing** — already present via `@timed`'s `logger.info` lines.
  Insufficient: logs don't capture parent-child relationships or concurrent
  thread timing.

## Consequences

- `utils/observability.py` and `utils/otel_attributes.py` are new leaf modules.
- `utils/timing.py`, `mcp_server/tools/decorators.py`,
  `search/incremental_indexer.py`, `search/hybrid_searcher.py`,
  `search/search_executor.py`, `mcp_server/resource_manager.py` are modified.
- `pyproject.toml` gains an `[otel]` optional extra.
- When disabled (default), there is zero OTel SDK import and `traced_block`
  returns on a single boolean check.

## Documented findings

Two architecture improvements surfaced during this investigation.

- **Improvement A** — Decompose the `_full_index` god-method
  (`search/incremental_indexer.py:666-978`, ~312 lines, complexity 38) into
  named pipeline stages. Status: **in progress**.
  - `SummaryStage` (`search/summary_stage.py`) — **done** (extracted in
    v0.11.10; handles community + module summary generation with the ordering
    constraint documented in its module docstring).
  - `CommunityStage` (`search/community_stage.py`) — **pending**: encapsulates
    community detection (build temp graph, Louvain detect, persist
    `community_map`), `SummaryStage` Phase 1 call, community remerge,
    chunk_id regeneration, `SummaryStage` Phase 2 call, and summary append.
    Interface: `CommunityStage(build_graph_fn, regenerate_ids_fn,
    summary_stage).run(all_chunks, project_path, config) -> list[CodeChunk]`.
  - `IndexWriteStage` (`search/index_write_stage.py`) — **pending**: encapsulates
    embedding, index write, snapshot save, BM25 sync, GPU cache clear.
    Interface: `IndexWriteStage(embedder, indexer, snapshot_manager, bm25_sync,
    build_metadata_fn, clear_gpu_fn).run(...) -> IncrementalIndexResult`.
  - After extraction `_full_index` becomes a ~50-line driver: prologue
    (resource release, DAG build, chunking) → `CommunityStage.run()` →
    `IndexWriteStage.run()`.
  - Sibling candidate: `_refresh_affected_community_summaries:1162-1310`
    (complexity 34) has the same shape and may follow the same treatment.

- **Improvement B** — Close the incremental community-summary gap. Status:
  **done** (closed in v0.11.10): `incremental_indexer.py:1199` now calls
  `load_community_map()` from `graph/graph_storage.py:819`.
