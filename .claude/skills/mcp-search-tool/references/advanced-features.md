# Advanced Search Features

Internal search-engine behaviors that affect result quality. Most of these operate automatically — they are documented here for debugging and tuning,
not for direct invocation.

**Tooling note:** `configure_reranking` and `configure_chunking`, referenced throughout this page as the controls for some of these behaviors, are
**advanced, unlisted-by-default** MCP tools — unlisted unless `MCP_EXPOSE_ADVANCED_TOOLS=1` is set on the server and the client reconnects — with **no
in-band alternative**. See `SKILL.md` → "Tool Tiers" before assuming either is callable in the current session.

The project has **three distinct graph-aware subsystems** that are often confused. This page disambiguates them.

## Contents

- Retrieval Funnel & Reranker Budget (v0.21.0 — per-leg pool sizing, graph cap)
- Multi-Hop Search (always-on — semantic + graph expansion, tags `multi_hop`/`graph_hop`)
- Ego-Graph Expansion (**on by server default** — `ego_graph_enabled` is a real tri-state gate: omit/`true`/`false`)
- Centrality Reranking (always-on when graph data exists)
- BM25 Snowball Stemming (inactive under the default `bm25_tokenizer="whole"`)
- Intent Classification: Effects That Still Exist (on by default — ADR-0029)
- A2: File-Level Summary Chunks (configurable)
- **pyan3 Cross-Module Caller Edges** (v0.13.0 — injected at full-index time)

---

## Retrieval Funnel & Reranker Budget (widened v0.21.0, budget retuned v0.22.0)

**Status:** Always-on engine behavior; not exposed as tool parameters.

**Per-leg pool sizing:** hybrid search retrieves `search_k = max(reranker.top_k_candidates, k*5)` candidates per leg (BM25 + dense) — the shipped
reranker budget is **30** (`RerankerConfig.top_k_candidates` in `search/config.py`; retuned down from 50 by the 2026-07-26 Q2 sweep, which found 30 vs 50
quality-neutral within ±0.025 on both golden sets and 32% faster). RRF fusion then keeps `max(k, budget)` candidates, the **listwise neural reranker
orders the full pool**, and truncation to `k` happens only after reranking. Consequence: a small `k` no longer starves the reranker (before v0.21.0
the fused pool was only `k*2` ≈ 14 candidates at k=7, so the pre-retune 50-candidate reranker budget was never reached). Benchmark impact of the
funnel widening itself: Recall@5 +0.04–0.06, Hit@5 0.968 → 1.000 (see [performance.md](performance.md)).

**Graph-stage result cap:** total returned results (k primary + multi-hop/ego-graph/parent context chunks) are capped at `k ×
graph_enhanced.max_results_multiplier` (default **8**, previously hardcoded `k*4`). This is why a k=7 search typically returns ~27 rows — everything
past the first k is graph-derived context, not extra primary hits.

**Configuration** (`search_config.json`):

```json
{
  "reranker": {"top_k_candidates": 30},
  "graph_enhanced": {"max_results_multiplier": 8}
}
```

---

## Multi-Hop Search (semantic + graph expansion)

**Status:** Always-on. Runs unconditionally on every `code-search:search_code` call. Not exposed at the MCP boundary.

**Purpose:** Expand the initial hit set with semantically similar chunks and graph-neighbor chunks, so the candidate pool is richer than pure
lexical/dense retrieval.

**Observable behavior:**

1. Retrieve initial hits for the query (direct semantic/BM25 match). These chunks carry `source="search"`.
2. Expand each initial hit along **semantic** similarity → expansion chunks tagged `source="multi_hop"`.
3. Expand along **graph** edges (calls / imports) → expansion chunks tagged `source="graph_hop"`.
4. Merge, dedupe, and rerank the combined set.

**In results:** the `source` field distinguishes origins:

| `source` value | Meaning |
|---|---|
| `search` | Direct lexical / dense match to the query |
| `multi_hop` | Reached by semantic expansion of an initial hit |
| `graph_hop` | Reached by call / import graph traversal from an initial hit |
| `ego_graph` | Reached by the ego-graph k-hop retriever, on by server default (see below — the tool argument is a real tri-state gate: omit for the server default, `true` widens it, `false` suppresses it for that call) |

You cannot disable multi-hop via tool parameters. For debugging, edit `search_config.json` and restart.

> **Implementation notes (may drift — 2026-04-11):** internal config flag `MultiHopConfig.enabled` in `search/config.py` (default `True`); invoked
> from `HybridSearcher.search()` in `search/hybrid_searcher.py`; core logic in `search/multi_hop_searcher.py`.

---

## Ego-Graph Expansion (on by server default; the tool argument is a real tri-state gate)

**Status:** **On by server default, and can be disabled per-call from the MCP boundary.** `EgoGraphConfig.enabled` defaults to `True` in the
dataclass (`search/config.py`). `search/effective_config.py`'s `build_effective_config()` reads `ego_graph_enabled` as tri-state: omitted (`None`)
leaves the base config's `enabled` value untouched (on, by default); explicit `true` mutates a copy to `enabled=True` and applies the
`ego_graph_k_hops`/`ego_graph_max_neighbors_per_hop` overrides (logs `"[EGO_GRAPH] Enabled with k_hops=..."`); explicit `false` mutates a copy to
`enabled=False` and leaves the hop-count args untouched (logs `"[EGO_GRAPH] Explicitly disabled"`). The schema itself publishes no `default` for this
argument — only a description telling you to omit it to get the server's configured value. A plain `search_code` call with `ego_graph_enabled`
omitted returns rows carrying `"source": "ego_graph"` because the server default is on, not because the argument is inert. Separate subsystem from
multi-hop above — the two are not the same thing.

**Purpose:** Fetch k-hop neighbors of the top result(s) via weighted BFS, with configurable hop depth and neighbor caps. Useful when you know you
want a local neighborhood of related code rather than the engine's default expansion — or when you want to suppress it entirely for a call where
graph-neighbor rows would just add noise.

**Observable behavior:**

1. Run normal search (which already includes always-on multi-hop above).
2. Ego-graph BFS runs whenever `EgoGraphConfig.enabled` resolves to `True` for the call (server default, or an explicit `ego_graph_enabled=true`),
   taking top result(s) out to `ego_graph_k_hops` (default `2`) with edge weights `calls=1.0`, `imports=0.3`, others intermediate. Passing
   `ego_graph_enabled=true` also raises this to the hop/neighbor values you pass; passing `ego_graph_enabled=false` skips this step entirely for that
   call.
3. Cap neighbors per hop via `ego_graph_max_neighbors_per_hop` (default `10`).
4. An **additional** post-expansion neural rerank (to unify scoring across the original results + the ego-graph-added results on a single
   cross-encoder scale) runs whenever ego-graph neighbors are present. The standard neural reranker used by hybrid search is independent of this and
   continues to run as configured via `code-search:configure_reranking`.

> **Implementation notes (may drift — 2026-08-18):** dataclass default in `search/config.py` (`EgoGraphConfig.enabled`); the tri-state merge logic is
> `search/effective_config.py`'s `build_effective_config()`; the arg-to-tri-state parsing (`None` if omitted, else `bool(...)`) is
> `mcp_server/tools/search_orchestrator.py`; core BFS logic in `search/ego_graph_retriever.py`; consumed inside `HybridSearcher.search()` in
> `search/hybrid_searcher.py` via `effective_config.ego_graph.enabled`.

**To widen it:** `code-search:search_code(..., ego_graph_enabled=true, ego_graph_k_hops=2)`.

**To disable it for one call:** `code-search:search_code(..., ego_graph_enabled=false)` — turns off ego-graph BFS for that call only; the server's
configured default is unaffected for subsequent calls.

**When to use the wider setting:** contextual / local-neighborhood queries ("show me everything that touches this class"). The server default
already adds neighbor rows to every result set; `ego_graph_enabled=true` is for when that isn't enough context, `ego_graph_enabled=false` is for when
you specifically don't want graph-neighbor rows mixed into that result set.

### `relation_types` in `ego_graph` config

The `ego_graph.relation_types` field (exposed in `search_config.json`) controls which edge types the k-hop BFS walks:

- **`null` (default) = traverse all 21 edge types** — no filter. BFS still applies the `edge_weights` priority ordering, so high-weight edges
  (`calls=1.0`, `inherits=0.9`) are favoured even when all types are eligible.
- **List of strings** = restrict traversal to those types only, e.g. `["calls", "inherits"]`.

**`relation_types` vs `edge_weights` — two separate knobs:**

| Knob | Effect |
|------|--------|
| `relation_types` | Which edges are *walked at all* (gate) |
| `edge_weights` | Priority / ranking within the walked edges (weight) |

Setting `relation_types: ["calls"]` limits BFS to call edges only. Setting `edge_weights: {"calls": 1.0, "imports": 0.1}` still walks import edges but
ranks them low. Both can be set together.

**Additional import filters (independent of `relation_types`):** `exclude_stdlib_imports: true` and `exclude_third_party_imports: true` (both default
`true`) drop stdlib / third-party import neighbors even when `relation_types` includes `"imports"`.

**All 21 valid values** (same as `code-search:find_connections.relationship_types`) — see [parameters.md](parameters.md).

---

## Centrality Reranking

**Status:** Always-on when graph data is available — runs independently of `ego_graph_enabled`.

**Formula:** `blended_score = (1 - centrality_alpha) × semantic_score + centrality_alpha × centrality` (`search/centrality_ranker.py`,
`CentralityRanker.rerank()`), where `GraphEnhancedConfig.centrality_alpha` (`search/config.py`) ships at **0.0** — so the centrality term drops out and
`blended_score` starts from `semantic_score` before `CentralityRanker.rerank()` applies its other, non-centrality adjustments (size penalty,
name-match boost, chunk-type boosts, directory/test/doc-intent factors). Higher `centrality_alpha` values were tested and found to cost recall
(replicated finding) — this is a deliberate tuning choice, not an oversight. Visible in result field: `centrality`.

> **Implementation notes (may drift — 2026-08-02):** applied in `GraphScoringStage._apply_centrality` (`search/graph_scoring_stage.py`), gated on
> `graph_config.centrality_annotation` (adds `centrality`) and, additionally, `graph_config.centrality_reranking` (adds `blended_score`) — both
> default `true` — plus presence of `index_manager.graph_storage`. Score blending itself is `search/centrality_ranker.py`'s `CentralityRanker`.

---

## BM25 Snowball Stemming

**Status:** Configured but **inactive under the shipped default.** `bm25_use_stemming=true` is a real config field, but it is only consulted by the
`bm25_tokenizer="legacy"` path (`tokenize(preprocess_code(text))` in `search/bm25_index.py`). The shipped default is `bm25_tokenizer="whole"`, which
routes through `_tokenize_identifiers()` instead — that path does **not** stem at all, regardless of `bm25_use_stemming`'s value. So "indexing",
"indexed", and "index" are three distinct BM25 tokens under the default config. To get stemming behavior, set `bm25_tokenizer="legacy"` explicitly
(and reindex — tokenizer changes require a full rebuild).

---

## Intent Classification: Effects That Still Exist

**Status:** On by default (`intent.enabled=true`, ADR-0029) — re-enabled after ADR-0028 had turned it off pending a repair of the SIMILARITY-intent
symbol extractor (`_extract_symbol_from_query`), which was misfiring on trailing prose words instead of the query's actual anchor symbol. NOT
directly exposed at the MCP boundary — there is no tool argument that reads intent classification results.

**What this page used to document, and why it doesn't anymore:** an earlier version documented a 7-row table of per-intent graph-traversal
edge-weight adjustments (`INTENT_EDGE_WEIGHT_PROFILES` in `graph/graph_storage.py`) plus a separate `_intent_ego_thresholds` policy in
`search/effective_config.py`. **Both were deleted** (ADR-0031, `4a93c65`) — ADR-0026 had measured the edge-weight table as inert on the canonical
benchmark (pool composition bit-identical whether it fired or not, net +0.0005 MRR), and a later measurement (QW5) found the CONTEXTUAL
ego-threshold policy produced 0 diffs across all 63 canonical queries. A repo-wide grep for either name now returns zero production hits;
`effective_config.py` is 77 lines with no `graph` import at all. **Both were already tried and measured inert — don't re-add either without new
evidence.**

**What intent classification actually still does** (`mcp_server/tools/search_orchestrator.py`), each with its own evidence status:

1. **`SIMILARITY` intent + confidence ≥ 0.4 + an extractable symbol → redirects `search_code` to `find_similar_code`** instead of running the normal
   search path (`fallback_on_error=True` — a redirect failure falls back to normal search rather than erroring out). **The only effect with positive
   measured evidence:** the repaired extractor's redirect beats the normal ranked path on MRR for the 9 similarity queries in the golden set, on both
   the 63q and 133q datasets (ADR-0029).
2. **`CONTEXTUAL` intent → forces `ego_graph_enabled=True`** for that search (`mcp_server/tools/search_orchestrator.py`, unconditionally overwriting
   whatever the raw argument resolved to, including an explicit `false`). **Measured as inert under the previous always-on ego-graph
   implementation** — that measurement predates the 2026-08-18 tri-state-gate fix (see "Ego-Graph Expansion" above) and has not been re-verified
   since; the one case where this override could now matter is a `CONTEXTUAL`-classified query that also explicitly passed
   `ego_graph_enabled=false`, which this code path would silently flip back to `true`.
3. **`GLOBAL` intent → suggests `k=10`**, applied only when greater than the caller's `k` (plus suggests `search_mode=HYBRID`).
4. **Any intent whose `suggested_params` includes `search_mode="auto"` → applies that suggested `search_mode`** to the actual search call.
5. **`NAVIGATIONAL` intent writes `symbol_name`/`relationship_types` into `suggested_params` that nothing consumes.** `PlanRedirect` only ever
   constructs `kind="find_similar"` — there is no `find_connections` redirect path for these values to feed into. This is dead code that computes a
   result and discards it, not a documented feature; don't expect `NAVIGATIONAL` classification to do anything beyond whichever of effects 3/4 above
   also apply.

**`path_tracing` intent no longer redirects to `find_path`** — that branch was removed outright (ADR-0028): both of its live golden-dataset firings
were regex misfires of `_extract_path_endpoints` on ordinary prose, and `fallback_on_error=False` turned each into an empty result set with no
upside case ever observed. `find_path` remains available as a standalone MCP tool (`code-search:find_path`); only the automatic `search_code`
redirect to it is gone.

**How a query gets its intent label** (the classification mechanism itself, separate from the four effects above):

- Classifies queries into 7 categories (`LOCAL`, `GLOBAL`, `NAVIGATIONAL`, `PATH_TRACING`, `SIMILARITY`, `CONTEXTUAL`, `HYBRID` —
  `search/intent_classifier.py`) using a keyword + anchor-embedding ensemble: `0.7 × keyword_score + 0.3 × anchor_embedding_score`
  (`semantic_enabled=true`, `semantic_weight=0.3` by default).
- Anchor queries: 8–10 representative phrases per intent, defined in `config/intent_anchors.yaml`.
- Confidence threshold: 0.4 (queries below fall back to `HYBRID` intent).
- Configure via `search_config.json` (`IntentConfig`, 6 fields: `enabled`, `confidence_threshold`, `default_intent`, `log_classifications`,
  `semantic_enabled`, `semantic_weight`); **not** exposed through any MCP config tool (`configure_search_mode` does not accept any `intent_*` field).

---

## A2: File-Level Summary Chunks

**Status:** Configurable. Enabled by default.

**What they are:** Synthetic `chunk_type="module"` chunks, one per file with 2+ top-level chunks. Contain classes, functions, and imports as a file
overview.

**ID format:** `{file_path}:0-0:module:{module_name}`

**Score handling:** Demoted by 0.82–0.90× multiplier to rank below concrete implementations. Excluded from call graph.

**Control:** `code-search:configure_chunking(enable_file_summaries=true/false)`

**Usage tip:** If module chunks surface at rank-1 when you need a specific implementation, add `chunk_type="function"` or `chunk_type="class"` to your
query to filter them out.

---

## configure_chunking Advanced Options

`code-search:configure_chunking` exposes many options beyond just file summaries:

- `sizing_mode`: "adaptive" (default — adjusts chunk size by complexity) or "fixed"
- `adaptive_multiplier_max` / `adaptive_multiplier_min`: bounds for adaptive sizing
- `max_complexity_cap`: cap on complexity-based growth
- `max_phantom_degree`: limit on phantom node degree
- `enable_large_node_splitting` / `max_chunk_lines` / `split_size_method` / `max_split_chars`

These are advanced tuning options. For most projects, defaults are correct.

---

## Layered Call-Graph Resolver Pipeline (v0.14.0)

**Status:** Runs at full-index time via `search/call_edge_injection.py`'s `inject_call_edges()`. Core (AST) is always-on; pyan3/LibCST require
`pip install -e ".[callgraph]"` **and** their names present in `call_graph.resolvers`; LSP requires `pip install -e ".[lsp]"` and is gated by the
separate `lsp_enabled` flag, which now **defaults to `true`** — not by `call_graph.resolvers` (see the trap below).

**Purpose:** Improve `find_connections` cross-module caller/callee recall. Each resolver adds edges with a confidence score; a higher-confidence
resolver can upgrade an edge already contributed by a lower one.

**Confidence ladder:**

| Resolver | Confidence | Requires |
|----------|-----------|----------|
| In-house AST (intra-file) | 0.5 | nothing — always-on |
| In-house AST (cross-file) | 0.7 | nothing — always-on |
| pyan3 | 0.75 | `pip install -e ".[callgraph]"` (GPL-2.0, optional) |
| LibCST (`FullyQualifiedNameProvider`) | 0.90 | `pip install -e ".[callgraph]"` (MIT, optional) |
| LSP/basedpyright | 0.98 | `pip install -e ".[lsp]"` + `lsp_enabled=true` |

**Configuration** (`search_config.json`):

```json
{
  "call_graph": {
    "resolvers": ["pyan", "libcst"],
    "lsp_enabled": true,
    "lsp_timeout_seconds": 30.0,
    "min_confidence": 0.65,
    "use_pyproject_toml": false
  }
}
```

`min_confidence` (default **`0.65`** — this is the shipped precision/recall tradeoff, not a suggestion to raise toward): edges below the threshold are
dropped before injection — e.g. `0.65` discards pyan wildcard fan-out edges (tagged 0.60) while keeping direct pyan edges (0.75) and everything from
LibCST/LSP. Lower it toward `0.0` to accept all edges (more recall, more noise) without reindexing. See `docs/CALL_GRAPH_TUNING.md` §6.1.
`use_pyproject_toml` (default `false`): pass to LibCST `FullRepoManager` for src-layout package discovery.

**⚠️ Trap: `resolvers` and `lsp_enabled` are two independent gates.** `call_graph.resolvers` governs the pyan3/LibCST resolvers **only** — putting
`"lsp"` in that list is accepted but is a no-op that just logs a warning (`search/call_edge_injection.py`). The LSP/basedpyright resolver (Stage 3) is
gated solely by the separate `lsp_enabled` boolean, independent of what `resolvers` contains.

**How it works:**

1. At full-index time, `search/call_edge_injection.py`'s `inject_call_edges()` reads `CallGraphConfig` and instantiates the enabled + available
   resolvers (subject to the `resolvers`-vs-`lsp_enabled` trap above). `search/index_write_stage.py`'s `_inject_call_edges` now only handles
   collaborator resolution before delegating to `inject_call_edges()` — it is not where resolver instantiation happens anymore.
2. `run_resolvers()` (`chunking/relationships/call_edge_resolver.py`) runs all resolvers in ascending confidence order; the merged result keeps the
   highest-confidence edge per `(caller_id, callee_id)` pair.
3. Edges carry provenance: `resolver_source` (`"ast"|"pyan"|"libcst"|"lsp"`) and `resolver_confidence` (float).
4. Each file is pre-validated with `ast.parse`; injection is scoped to indexed files only.

**Observable in `find_connections` output (v0.14.0+):**

Every entry in `direct_callers` and `direct_callees` now includes:

- `confidence`: string tag (`"exact"` / `"recovered"` / `"ambiguous"`)
- `resolver_source`: which resolver produced the edge (`"ast"`, `"pyan"`, `"libcst"`, `"lsp"`)
- `resolver_confidence`: float 0.5–0.98

Top-level breakdowns:

```json
{
  "caller_confidence": {"exact": 3, "recovered": 1, "ambiguous": 0},
  "callee_confidence": {"exact": 2, "recovered": 0, "ambiguous": 0}
}
```

`direct_callees` (outbound calls) is now returned alongside `direct_callers` (inbound).

**Recall improvement (v0.13.0 baseline, maintained in v0.14.0+):**

- 7-query golden set: 14/14 callers found, 0 missed
- 5-query set: `mean_recall` 0.5667 → 0.9500

**LSP tier verified working (v0.15.0):** After three protocol bug fixes in v0.15.0 (`_find_def_position` probe position, `_read_until_id` ID
correlation, `unquote()` before `url2pathname` for `file:///f%3A/...` URIs), LSP resolves **938 edges on this codebase** (added=64, upgraded=869 from
LibCST 0.90 → 0.98). Diagnostics: `[LSP] probes=N ... dropped_uri=N dropped_no_chunk=N` logged at INFO each session; see `docs/CALL_GRAPH_TUNING.md`
§6.4 for counter meanings.
