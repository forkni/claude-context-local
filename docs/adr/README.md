# Architecture Decision Records

Index of all ADRs for claude-context-local. Each record captures a decision, its context, and
the alternatives considered — including declined options, which are as valuable as accepted ones
for avoiding re-litigating settled questions.

| # | Title | Status | Date |
|---|---|---|---|
| [0001](0001-faiss-as-vector-index-backend.md) | Use FAISS as the vector index backend; do not migrate to turbovec | accepted | 2026-05-15 |
| [0002](0002-pyrefly-over-pyright.md) | Use Pyrefly as the type checker; do not adopt Pyright or Mypy | accepted | 2026-05-15 |
| [0003](0003-decline-llm-hierarchical-summaries.md) | Decline LLM-generated hierarchical summaries from NVIDIA/context-aware-rag | accepted | 2026-05-23 |
| [0004](0004-scoped-tracing-only-observability.md) | Scoped tracing-only OTel observability; rejected full OTel + metrics | accepted | 2026-05-23 |
| [0005](0005-no-di-container-module-singleton-state.md) | Prefer module singletons over DI containers for process-global state | accepted | 2026-05-29 |
| [0006](0006-thread-safety-of-module-singletons.md) | Thread-safety of module singletons via coarse locks | accepted | 2026-06-11 |
| [0007](0007-onnx-token-contract-and-activation-floors.md) | 2048-token ONNX contract and `max()` activation-cost floors | superseded (`72b6881`) | 2026-06-12 |
| [0008](0008-reindex-search-rwlock.md) | Reader-writer lock for auto-reindex vs. in-flight searches | accepted (amended 2026-07-27) | 2026-07-12 |
| [0009](0009-decline-parse-once-profile-chunk.md) | Decline parse-once tree reuse between the profile and chunk passes | accepted | 2026-07-20 |
| [0010](0010-centrality-memo-invalidation.md) | Centrality memo invalidation: version counter, not node/edge counts | accepted | 2026-07-27 |
| [0011](0011-listwise-reranker-doc-cap.md) | Cap JinaRerankerV3's listwise document budget at 1000 chars | accepted | 2026-07-28 |
| [0012](0012-curated-vocabulary-query-expansion.md) | Curated-vocabulary query expansion over PRF or LLM query rewriting | accepted | 2026-07-28 |
| [0013](0013-hop1-reserve-at-final-pool.md) | Reserve hop-1 winners at the multi-hop rerank window, not at hop-1 fusion | accepted | 2026-07-28 |
| [0014](0014-per-project-search-config-overrides.md) | Per-project search config overrides via `search_overrides.json` | accepted | 2026-07-29 |
| [0015](0015-remove-community-subsystem.md) | Remove the community-detection subsystem; cancel the Leiden migration | accepted | 2026-07-30 |
| [0016](0016-remove-dspy-eval-subsystem.md) | Remove the DSPy eval subsystem | accepted | 2026-08-01 |
| [0017](0017-adopt-mcp-sdk-v2.md) | Adopt MCP Python SDK v2 | accepted | 2026-08-01 |
| [0018](0018-retrieval-request-carries-effective-config.md) | `RetrievalRequest` carries the effective config; per-layer re-fetch removed | accepted | 2026-08-01 |
| [0019](0019-reject-intent-adaptive-fusion-weights.md) | Reject intent-adaptive fusion weights (measured, replicated, removed) | accepted | 2026-08-01 |
| [0020](0020-config-field-liveness-audit.md) | Config field liveness audit: wire the hardcoded, delete the orphaned | accepted | 2026-08-02 |
| [0021](0021-benchmark-hash-seed-determinism.md) | Benchmark determinism: pin PYTHONHASHSEED, reject the GPU kernel pin | accepted | 2026-08-02 |
| [0022](0022-config-field-spec-and-liveness-ratchet.md) | Config field spec table and liveness ratchet | accepted | 2026-08-02 |
| [0023](0023-benchmark-routes-through-orchestrator.md) | Route the SSCG benchmark through `SearchOrchestrator` | accepted | 2026-08-02 |
| [0024](0024-repin-sscg-canon-post-c3.md) | Re-pin the SSCG canon after the C3 searcher-construction / config-metadata fixes | accepted | 2026-08-03 |
| [0025](0025-clear-index-directory-in-place.md) | Clear and resync index objects in place instead of replacing them | accepted | 2026-08-03 |
| [0026](0026-canon-repin-and-b1b-intent-arm.md) | Re-pin the SSCG canon to `canon_f1` and capture the `canon_B1b` intent-on arm | accepted | 2026-08-04 |
| [0027](0027-parallel-edge-bucketing.md) | Parallel edges carry through `find_connections` instead of collapsing to one primary type | accepted | 2026-08-04 |
| [0028](0028-intent-off-by-default-and-remove-find-path-redirect.md) | Default intent classification off; remove the `find_path` redirect | accepted | 2026-08-04 |
| [0029](0029-repair-symbol-extraction-and-regate-find-similar.md) | Repair `_extract_symbol_from_query` and re-gate the `find_similar` redirect | accepted | 2026-08-04 |
| [0030](0030-deepen-config-searcher-seam.md) | Deepen the config→searcher seam (C3 + C4) | accepted | 2026-08-05 |
| [0031](0031-delete-intent-policy-tables.md) | Delete the two intent policy tables (QW5 + A1) | accepted | 2026-08-05 |
| [0032](0032-config-liveness-audit.md) | Config liveness audit: 124/124 fields live, five defects fixed | accepted | 2026-08-06 |
| [0033](0033-lift-torch-ceiling.md) | Lift the torch `<2.9.0` ceiling, bump the ML stack | accepted | 2026-08-06 |
| [0034](0034-pyan-gpl-quarantine.md) | GPL-2.0-or-later quarantine for the pyan call-graph tier | accepted | 2026-08-07 |
| [0035](0035-cpp-call-edge-tier-scope.md) | C/C++ call-edge strategy: tree-sitter tier only, sequenced behind chunking parity | accepted | 2026-08-07 |
| [0036](0036-include-dirs-additive-for-dependency-trees.md) | Make `include_dirs` additive for dependency trees, narrowing for source | accepted | 2026-08-07 |
| [0037](0037-decline-index-version-bump-for-cpp-parity.md) | Decline an `INDEX_VERSION` bump for C++ chunking parity | accepted | 2026-08-12 |
| [0038](0038-cpp-only-container-traversal-seam.md) | Fix the container-traversal seam for C++ only; defer the Rust/C# analogues | accepted | 2026-08-12 |
| [0039](0039-merged-pool-provenance-bands.md) | Replace the merged-pool score sort's incidental graph band with an explicit one | accepted | 2026-08-15 |
| [0040](0040-probe-harness-seam.md) | Shared interface for offline retrieval probes: `evaluation/probe_harness.py` | accepted | 2026-08-17 |
| [0041](0041-find-connections-indirect-caller-fanout.md) | Dedup/sort `find_connections`' `indirect_callers`; decline the fan-out cap | accepted | 2026-08-18 |
| [0042](0042-publish-invariants-not-values.md) | Derive the MCP tool schema's bounds/enums from `spec()`; never derive `default` | accepted | 2026-08-19 |
| [0043](0043-point-stale-prose-counts-at-derived-source.md) | Point stale ADR/README prose counts at their derived source, not a re-pinned number | accepted | 2026-08-19 |
| [0044](0044-incremental-call-edge-injection-opt-in-only.md) | Incremental-pass call-edge re-injection: opt-in only, default stays off | accepted | 2026-08-19 |
| [0045](0045-extract-embedding-document-composer.md) | Extract the embedding-document composer from `CodeEmbedder` | accepted | 2026-08-19 |
| [0046](0046-single-source-mcp-parameter-defaults.md) | Single-source hand-typed MCP parameter defaults through `config_schema.py` | accepted | 2026-08-19 |
| [0047](0047-result-source-strenum.md) | Replace `SearchResult.source`'s bare `str` with a `ResultSource` StrEnum | accepted | 2026-08-19 |
| [0048](0048-base-searcher-execute-seam.md) | One retrieval seam on `BaseSearcher`: `execute(request)` behind `search(...)` | accepted | 2026-08-19 |
| [0049](0049-enricher-spec-rows.md) | One spec row per request-scoped result enricher; derive schema, default, plan, and gate | accepted | 2026-08-20 |
| [0050](0050-per-layer-confidence-unknown-defaults.md) | Decline a shared policy object for the four `resolver_confidence`-unknown defaults | accepted | 2026-08-20 |

## Adding a new ADR

1. Copy the format of a recent record (title as H1 — no `ADR-NNNN:` prefix — then plain
   `Status:` / `Date:` lines, `## Context`, `## Decision`, `## Reasons` or `## Consequences`).
2. Number sequentially, zero-padded to 4 digits: `00NN-kebab-case-title.md`.
3. Add a row to the table above.
4. Link the ADR from `CHANGELOG.md` and/or `docs/VERSION_HISTORY.md` when the decision ships.
