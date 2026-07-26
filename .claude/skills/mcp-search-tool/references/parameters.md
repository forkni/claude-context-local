# Essential Tools — Detailed Parameter Reference

Covers `code-search:search_code`, `code-search:find_connections`, and `code-search:find_path` in full depth. For all other tools, see [tool-index.md](tool-index.md).

> **Note on example style:** the fenced `text` blocks below are pseudocode that describe MCP tool calls. They are not executable Python. Booleans use JSON style (`true`/`false`), all arguments are named (no positional calls), and any `results[0]["chunk_id"]`-style indexing is a conceptual placeholder — your MCP client hands you the full result object, which you then pass back in as a parameter.

## Contents
- search_code — all parameters + examples
- find_connections — all parameters + examples
- find_path — all parameters + examples

---

## code-search:search_code

**Purpose**: Find code with natural language queries OR direct symbol lookup.

**Full parameter list:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `query` | — | Natural language description. Optional if `chunk_id` given. |
| `chunk_id` | — | Direct chunk ID for O(1) lookup. Format: `"file:lines:type:name"` |
| `k` | 7 | Number of results to return. **Recommended: pass `k=7` explicitly** — targets may rank 6–7 on complex queries (SSCG benchmark: Hit@5=100% at k=7). Use `k=10` for architectural queries. |
| `search_mode` | "auto" | "hybrid", "semantic", "bm25", "auto" |
| `file_pattern` | — | Filter by filename/path substring (e.g., "auth", "models") |
| `include_dirs` | — | Whitelist directories, e.g. `["src/"]` |
| `exclude_dirs` | — | Blacklist directories, e.g. `["tests/"]` |
| `chunk_type` | — | Filter by structure type (see below) |
| `include_context` | true | Include similar chunks and relationships |
| `auto_reindex` | true | Auto-reindex if index is stale |
| `max_age_minutes` | 5 | Max age (minutes) before auto-reindex triggers |
| `ego_graph_enabled` | false | Enable k-hop graph expansion for neighbors |
| `ego_graph_k_hops` | 2 | Graph traversal depth (range 1-5) |
| `ego_graph_max_neighbors_per_hop` | 10 | Max neighbors per hop (range 1-50) |
| `include_parent` | false | Also retrieve enclosing class when matching methods |
| `output_format` | "compact" | "compact" (omit empty fields) / "verbose" / "ultra" (tabular) |
| `max_context_tokens` | — | Token-budget cap to prevent context overflow |

**chunk_type values:** "function", "class", "method", "module", "decorated_definition", "interface", "enum", "struct", "type", "merged", "split_block", "community"

**Result fields (always):** `chunk_id`, `kind`, `score`, `blended_score`, `centrality`, `source`

**Result fields (optional):** `complexity_score`, `graph`, `reranker_score`, `summary`

**Source values:** `"search"` (direct lexical/dense match), `"multi_hop"` (always-on semantic expansion of initial hits), `"graph_hop"` (always-on call/import graph expansion of initial hits), `"ego_graph"` (opt-in k-hop neighbors via `ego_graph_enabled=true`). See [advanced-features.md](advanced-features.md) for the full disambiguation.

**Examples:**

```text
# General search
code-search:search_code("authentication handler")

# Filtered by directory and type
code-search:search_code("OSC message handlers", include_dirs=["Scripts/"], chunk_type="function")

# Graph-enhanced search with neighbors
code-search:search_code("token merging", ego_graph_enabled=true, ego_graph_k_hops=2)

# BM25 for exact symbol name
code-search:search_code("HybridSearcher", search_mode="bm25")

# Direct chunk lookup by ID
code-search:search_code(chunk_id="search/hybrid_searcher.py:45-120:class:HybridSearcher")

# Broader k for global/architectural queries
code-search:search_code("how does the indexing pipeline work", k=10)
```

---

## code-search:find_connections

**Purpose**: Find all code connections to a given symbol — callers, dependencies, relationships.

**Full parameter list:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `chunk_id` | — | Direct chunk_id from search results (preferred) |
| `symbol_name` | — | Symbol name to find (fallback; may be ambiguous) |
| `max_depth` | 3 | Max depth for dependency traversal (range 1-5) |
| `exclude_dirs` | — | Directories to exclude, e.g. `["tests/"]` |
| `relationship_types` | — | Filter to specific types (see list below) |
| `output_format` | "compact" | "compact" / "verbose" / "ultra" |

**Valid relationship_types (21 total):**

`calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`, `defines_constant`, `defines_enum_member`, `defines_class_attr`, `defines_field`, `uses_constant`, `uses_default`, `uses_global`, `asserts_type`, `uses_context_manager`

**Returns:** Direct callers (inbound) and direct callees (outbound), indirect callers, dependency graph (DOT format), similar code (when available).

Per-entry provenance fields on every caller and callee entry (v0.14.0+):
- `confidence`: string tag — `"exact"` (direct chunk_id resolution), `"recovered"` (stale ID re-resolved via `_resolve_by_symbol` Tier 1→3), `"ambiguous"` (multiple candidates)
- `resolver_source`: which resolver produced the edge — `"ast"`, `"pyan"`, `"libcst"`, or `"lsp"`
- `resolver_confidence`: float 0.5–0.98 (higher = more trusted)

Top-level breakdowns (when any counter is non-zero):
- `caller_confidence: {exact, recovered, ambiguous}` — count of each tag in `direct_callers`
- `callee_confidence: {exact, recovered, ambiguous}` — count of each tag in `direct_callees`

**Standard 2-step workflow:**

```text
# Step 1: Find the symbol (k=7 baseline — see SKILL.md for rationale)
results = code-search:search_code("chunk_file function", k=7, chunk_type="function")
chunk_id = results[0]["chunk_id"]  # scan all k results, pick best match

# Step 2: Get all relationships
code-search:find_connections(chunk_id=chunk_id, exclude_dirs=["tests/"])
```

**More examples:**

```text
# By chunk_id (preferred)
code-search:find_connections(chunk_id="mcp_server/server.py:100-180:function:handle_tool_call")

# Filter for only inheritance
code-search:find_connections(symbol_name="BaseChunker", relationship_types=["inherits"])

# Deep tracing
code-search:find_connections(chunk_id="...", max_depth=5)

# Only find what this code imports
code-search:find_connections(chunk_id="...", relationship_types=["imports", "uses_type"])
```

---

## code-search:find_path

**Purpose**: Find shortest path between two code entities in the relationship graph.

**Full parameter list:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `source_chunk_id` | — | Starting chunk ID (preferred) |
| `target_chunk_id` | — | Ending chunk ID (preferred) |
| `source` | — | Starting symbol name (fallback — may be ambiguous) |
| `target` | — | Ending symbol name (fallback) |
| `edge_types` | — | Filter path to specific relationship types (12-type subset — see below) |
| `max_hops` | 10 | Maximum path length (range 1-20) |
| `output_format` | "compact" | "compact" / "verbose" / "ultra" |

**Valid `edge_types` for `find_path` (12 types, a subset of the 21 `find_connections` types):**

`calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`

**Algorithm:** Bidirectional BFS for optimal performance.

**Returns:** Path as sequence of nodes with metadata, edge types traversed, path length.

**Examples:**

```text
# Preferred: by chunk_ids
code-search:find_path(
    source_chunk_id="mcp_server/server.py:100-180:function:handle_tool_call",
    target_chunk_id="search/hybrid_searcher.py:45-120:class:HybridSearcher"
)

# Restrict to only call and import edges
code-search:find_path(
    source_chunk_id="...",
    target_chunk_id="...",
    edge_types=["calls", "imports"]
)

# By symbol name (use when chunk_id unknown)
code-search:find_path(source="main", target="HybridSearcher")
```
