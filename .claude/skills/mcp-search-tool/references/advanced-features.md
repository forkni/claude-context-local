# Advanced Search Features

Internal search-engine behaviors that affect result quality. Most of these operate automatically — they are documented here for debugging and tuning, not for direct invocation.

## Contents
- Multi-Hop Search (always-on)
- Centrality Reranking (always-on)
- BM25 Snowball Stemming (always-on)
- A1: Intent-Adaptive Edge Weights (internal)
- A2: File-Level Summary Chunks (configurable)
- B1: Community-Level Summary Chunks (configurable)

---

## Multi-Hop Search (Graph-Aware)

**Status:** Always-on. Cannot be disabled, but controlled via `ego_graph_*` parameters.

**Purpose:** Discover interconnected code through graph traversal + semantic similarity.

**How it works:**
1. Find chunks matching query (k×2 candidates)
2. Find graph neighbors via weighted BFS (edge weights: `calls`=1.0, `imports`=0.3, others intermediate)
3. Find semantically similar chunks
4. Rerank ALL discovered chunks

**In results:** `source: "multi_hop"` marks chunks discovered via graph (not direct semantic match).

**To use graph expansion explicitly:** `code-search:search_code(..., ego_graph_enabled=True, ego_graph_k_hops=2)`

---

## Centrality Reranking

**Status:** Always-on when graph data is available.

**Formula:** `blended_score = centrality × 0.3 + semantic_score × 0.7`

Functions that are heavily called or imported (high PageRank centrality) receive a small boost. Visible in result field: `centrality`.

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
- `semantic_enabled=False` by default; `semantic_weight=0.3`
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

**Control:** `code-search:configure_chunking(enable_file_summaries=True/False)`

**Usage tip:** If module chunks surface at rank-1 when you need a specific implementation, add `chunk_type="function"` or `chunk_type="class"` to your query to filter them out.

---

## B1: Community-Level Summary Chunks

**Status:** Configurable. Enabled by default.

**What they are:** Synthetic `chunk_type="community"` chunks generated per code community (detected via Louvain algorithm). Contain thematic groupings of related chunks across files.

**ID format:** `__community__/{label}:0-0:community:{label}`

**Score handling:** Demoted by 0.9–0.95× multiplier. Excluded from call graph.

**Control:** `code-search:configure_chunking(enable_community_summaries=True/False)`

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
