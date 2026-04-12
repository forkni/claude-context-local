# Advanced Search Features

Internal search-engine behaviors that affect result quality. Most of these operate automatically — they are documented here for debugging and tuning, not for direct invocation.

The project has **three distinct graph-aware subsystems** that are often confused. This page disambiguates them.

## Contents
- Multi-Hop Search (always-on — semantic + graph expansion, tags `multi_hop`/`graph_hop`)
- Ego-Graph Expansion (**opt-in** via `ego_graph_enabled`, default `false`)
- Centrality Reranking (always-on when graph data exists)
- BM25 Snowball Stemming (always-on)
- A1: Intent-Adaptive Edge Weights (internal)
- A2: File-Level Summary Chunks (configurable)
- B1: Community-Level Summary Chunks (configurable)

---

## Multi-Hop Search (semantic + graph expansion)

**Status:** Always-on. Runs unconditionally on every `code-search:search_code` call. Not exposed at the MCP boundary.

**Purpose:** Expand the initial hit set with semantically similar chunks and graph-neighbor chunks, so the candidate pool is richer than pure lexical/dense retrieval.

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
| `ego_graph` | Reached by the opt-in ego-graph k-hop retriever (see below) |

You cannot disable multi-hop via tool parameters. For debugging, edit `search_config.json` and restart.

> **Implementation notes (may drift — 2026-04-11):** internal config flag `MultiHopConfig.enabled` in `search/config.py` (default `True`); invoked from `HybridSearcher.search()` in `search/hybrid_searcher.py`; core logic in `search/multi_hop_searcher.py`.

---

## Ego-Graph Expansion (opt-in)

**Status:** **Opt-in.** Default `ego_graph_enabled=false` in the `code-search:search_code` tool schema. Separate subsystem from multi-hop above — the two are not the same thing.

**Purpose:** Explicitly fetch k-hop neighbors of the top result(s) via weighted BFS, with configurable hop depth and neighbor caps. Useful when you know you want a local neighborhood of related code rather than the engine's default expansion.

**Observable behavior:**
1. Run normal search (which already includes always-on multi-hop above).
2. **If `ego_graph_enabled=true`**, take top result(s) and do weighted BFS out to `ego_graph_k_hops` (default `2`) with edge weights `calls=1.0`, `imports=0.3`, others intermediate.
3. Cap neighbors per hop via `ego_graph_max_neighbors_per_hop` (default `10`).
4. An **additional** post-expansion neural rerank (to unify scoring across the original results + the ego-graph-added results on a single cross-encoder scale) runs only when this gate is open. The standard neural reranker used by hybrid search is independent of `ego_graph_enabled` and continues to run as configured via `code-search:configure_reranking`.

> **Implementation notes (may drift — 2026-04-11):** default declared in `mcp_server/tool_registry.py` `search_code` schema; core logic in `search/ego_graph_retriever.py`; gated inside `HybridSearcher.search()` in `search/hybrid_searcher.py` on `effective_config.ego_graph.enabled`.

**To enable:** `code-search:search_code(..., ego_graph_enabled=true, ego_graph_k_hops=2)`

**When to use:** contextual / local-neighborhood queries ("show me everything that touches this class"). Overkill for simple symbol lookups.

---

## Centrality Reranking

**Status:** Always-on when graph data is available — runs independently of `ego_graph_enabled`.

**Formula:** `blended_score = centrality × 0.3 + semantic_score × 0.7`

Functions that are heavily called or imported (high PageRank centrality) receive a small boost. Visible in result field: `centrality`.

> **Implementation notes (may drift — 2026-04-11):** applied in `mcp_server/tools/search_handlers.py`, gated on `graph_config.centrality_reranking` and presence of `index_manager.graph_storage`.

---

## BM25 Snowball Stemming

**Status:** Always-on. Enabled by default.

Normalizes word forms so "indexing", "indexed", and "index" all resolve to the same stem. Benefits queries with verb forms or plurals. No action required.

---

## A1: Intent-Adaptive Edge Weights

**Status:** Internal to the search engine. NOT directly exposed at the MCP boundary.

**What it does:** Classifies queries into 7 intent categories using a keyword + anchor-embedding ensemble, then adjusts graph traversal edge weights and search parameters accordingly.

**⚠️ Note on automatic routing:** The intent classifier may internally redirect `search_code` to `find_path` (path_tracing intent) or `find_similar_code` (similarity intent) when confidence ≥ 0.35. This routing is transparent — the MCP dispatcher does NOT change which tool is called on the wire. If you need deterministic behavior, call `code-search:find_path` or `code-search:find_similar_code` directly.

**Intent categories and adjustments (for reference):**

| Intent | Graph weight adjustments | Automatic action |
|--------|--------------------------|-----------------|
| `local` | calls=1.0, inherits=1.0, imports=0.1 | Standard search |
| `global` | imports=0.7, uses_type=0.9, instantiates=0.8 | k expanded |
| `navigational` | calls=1.0, inherits=0.9, imports=0.5 | Standard search |
| `path_tracing` | uniform 0.7 base, calls=1.0, inherits=0.9 | Internal redirect to find_path |
| `similarity` | uses_type=0.9, decorates=0.7, defines_class_attr=0.7 | Internal redirect to find_similar_code |
| `contextual` | all weights raised to min 0.5 | ego_graph enabled |
| `hybrid` | default weights | Standard search |

**Semantic enhancement** (opt-in, default off):
- `semantic_enabled=false` by default; `semantic_weight=0.3`
- Ensemble: `0.7 × keyword_score + 0.3 × anchor_embedding_score`
- Anchor queries: 8–10 representative phrases per intent, defined in `config/intent_anchors.yaml`
- Confidence threshold: 0.35 (queries below fall back to HYBRID intent)
- Enable via `code-search:configure_search_mode` or `search_config.json`

---

## A2: File-Level Summary Chunks

**Status:** Configurable. Enabled by default.

**What they are:** Synthetic `chunk_type="module"` chunks, one per file with 2+ top-level chunks. Contain classes, functions, and imports as a file overview.

**ID format:** `{file_path}:0-0:module:{module_name}`

**Score handling:** Demoted by 0.82–0.90× multiplier to rank below concrete implementations. Excluded from call graph.

**Control:** `code-search:configure_chunking(enable_file_summaries=true/false)`

**Usage tip:** If module chunks surface at rank-1 when you need a specific implementation, add `chunk_type="function"` or `chunk_type="class"` to your query to filter them out.

---

## B1: Community-Level Summary Chunks

**Status:** Configurable. Enabled by default.

**What they are:** Synthetic `chunk_type="community"` chunks generated per code community (detected via Louvain algorithm). Contain thematic groupings of related chunks across files.

**ID format:** `__community__/{label}:0-0:community:{label}`

**Score handling:** Demoted by 0.9–0.95× multiplier. Excluded from call graph.

**Control:** `code-search:configure_chunking(enable_community_summaries=true/false)`

---

## configure_chunking Advanced Options

`code-search:configure_chunking` exposes many options beyond just file/community summaries:

- `sizing_mode`: "fixed" (default) or "adaptive" (adjusts chunk size by complexity)
- `adaptive_multiplier_max` / `adaptive_multiplier_min`: bounds for adaptive sizing
- `max_complexity_cap`: cap on complexity-based growth
- `max_phantom_degree`: limit on phantom node degree
- `token_estimation`: algorithm for token counting
- `enable_large_node_splitting` / `max_chunk_lines` / `split_size_method` / `max_split_chars`

These are advanced tuning options. For most projects, defaults are correct.
