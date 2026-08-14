# Essential Tools — Detailed Parameter Reference

Covers `code-search:search_code`, `code-search:find_connections`, and `code-search:find_path` in full depth. For all other tools, see
[tool-index.md](tool-index.md).

> **Note on example style:** the fenced `text` blocks below are pseudocode that describe MCP tool calls. They are not executable Python. Booleans use
> JSON style (`true`/`false`), all arguments are named (no positional calls), and any `results[0]["chunk_id"]`-style indexing is a conceptual
> placeholder — your MCP client hands you the full result object, which you then pass back in as a parameter.

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
| `k` | schema **4**, effective **7** | Schema default is `4` (`mcp_server/tool_registry.py`); `search_orchestrator.py` falls back to `search_config.search_mode.default_k` when omitted, and both the shipped `search_config.json.example` and this machine's local config set `default_k: 7`. **Recommended: pass `k=7` explicitly** — targets may rank 6–7 on complex queries (SSCG benchmark: Hit@5=100% at k=7). Use `k=10` for architectural queries. |
| `search_mode` | "auto" | "hybrid", "semantic", "bm25", "auto" |
| `file_pattern` | — | Filter by filename/path substring (e.g., "auth", "models") |
| `include_dirs` | — | Whitelist directories, e.g. `["src/"]` — a pure path-prefix narrowing filter over the already-built index. Distinct from `index_directory`'s `include_dirs` (see [tool-index.md](tool-index.md), replace-wholesale + ADR-0036 additive dependency-tree semantics); this one has no additive case. |
| `exclude_dirs` | — | Blacklist directories, e.g. `["tests/"]` |
| `chunk_type` | — | Filter by structure type (see below) |
| `include_context` | true | Include similar chunks and relationships |
| `auto_reindex` | schema **true**, effective **true** | If omitted, `search_orchestrator.py` falls back to `config.performance.enable_auto_reindex` — dataclass default is also `True`, so schema and effective values agree today. Documented for the same reason as the two rows below: if a project's `search_config.json` ever overrides this, the schema-shown default becomes stale, not the behavior. |
| `max_age_minutes` | schema **5**, effective **30** | If omitted, the server falls back to `config.performance.max_index_age_minutes` (`SearchPlanner.plan` in `mcp_server/tools/search_orchestrator.py`), not the schema's 5 — dataclass factory default is 5.0, and both the shipped `search_config.json.example` and this machine's local config set 30.0. Pass the value explicitly if you need a specific staleness window. |
| `ego_graph_enabled` | false | **Does not gate ego-graph expansion — it always runs.** Only widens `ego_graph_k_hops`/`ego_graph_max_neighbors_per_hop` when `true`; see `SKILL.md` Gotchas and [advanced-features.md](advanced-features.md). |
| `ego_graph_k_hops` | 2 | Graph traversal depth (range 1-5) |
| `ego_graph_max_neighbors_per_hop` | 10 | Max neighbors per hop (range 1-50) |
| `include_parent` | false | Also retrieve enclosing class when matching methods |
| `output_format` | schema `"compact"`, effective `"ultra"` | If omitted, `handle_call_tool` (`mcp_server/server.py`) falls back to `config.output.format`, which ships as **`"ultra"`** (`OutputConfig.format` in `search/config.py`, for 45-55% token reduction). Pass `output_format="compact"` or `"verbose"` explicitly to override. |
| `max_context_tokens` | schema **0**, effective **0** | If omitted, falls back to `config.search_mode.default_max_context_tokens` — dataclass default is also `0` (no cap), so schema and effective values agree today. Same drift risk as `auto_reindex` above if a project overrides the config value. |
| `include_top_callers` | false | (2026-08-14) Attach `top_callers` — up to 2 `{name, file}` caller hints per result from raw call-graph in-edges. Ranked by resolver confidence when present, insertion order otherwise (most in-file AST edges carry no confidence float — treat ordering as a hint). Silently absent when the graph or incoming call edges are missing. |

**chunk_type values (12):** "function", "class", "method", "module", "module_preamble", "decorated_definition", "interface", "enum", "struct", "type",
"merged", "split_block"

**Result fields (always):** `file`, `lines`, `kind`, `score`, `chunk_id` (`_format_search_results` in `mcp_server/tools/result_view.py`).

**Present whenever the project has an indexed call graph** (on by default — `GraphEnhancedConfig.centrality_annotation`/`centrality_reranking` in
`search/config.py`): `centrality`, `blended_score` (with the default `centrality_alpha=0.0`, `blended_score` is numerically identical to `score`).

**Result fields (optional):** `name` (chunk has a name), `summary` (module chunks with a docstring), `reranker_score` (neural reranking ran),
`complexity_score` (functions with a computed score), `source` (present whenever the underlying result object carries a non-empty `source`
attribute — in practice this covers essentially every result path (`hybrid`/`multi_hop`/`graph_hop`/`ego_graph`/`direct_lookup`), but it is not a
schema-guaranteed field, so check for its presence rather than assuming it), `top_callers` (only with `include_top_callers=true` — up to 2
`{name, file}` caller hints).

**Source values:** `"search"` (direct lexical/dense match), `"multi_hop"` (always-on semantic expansion of initial hits), `"graph_hop"` (always-on
call/import graph expansion of initial hits), `"ego_graph"` (always-on k-hop neighbors — `ego_graph_enabled=true` widens the neighborhood, it doesn't
switch this on). A direct `chunk_id` lookup instead returns `"direct_lookup"` plus a `graph` summary object. See
[advanced-features.md](advanced-features.md) for the full disambiguation.

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
| `hide_ambiguous` | false | (2026-08-14) Drop `"ambiguous"`-tagged entries from `direct_callers`/`direct_callees`/`indirect_callers` only. `caller_confidence`/`callee_confidence` breakdowns and `total_impacted` intentionally stay **pre-filter totals** (e.g. `ambiguous: 5` alongside a shorter list means 5 were hidden); `dependency_graph` is not filtered and can still show hidden entries. |
| `output_format` | "compact" | "compact" / "verbose" / "ultra" |

**Valid relationship_types (21 enum members; only 19 actually route to a response field):**

`calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`,
`defines_constant`, `defines_enum_member`, `defines_class_attr`, `defines_field`, `uses_constant`, `uses_default`, `uses_global`, `asserts_type`,
`uses_context_manager`

`assigns_to` and `reads_from` have no extractor in `get_relationship_field_mapping()`
(`chunking/relationships/relationship_types.py` — deliberate, to protect the GLSL tree-sitter dynamic-conversion path from a silently-swallowed
`ValueError`), so passing either one filters every relationship block to empty. **Also note:** the filter only scopes a *subset* of the response —
`direct_callers`, `indirect_callers`, `direct_callees`, and `similar_code` are returned unfiltered regardless of `relationship_types`; only sections
like `uses_types`/`exceptions_caught`/`instantiates` are actually narrowed by it (confirmed by live probing — see `SKILL.md` Gotchas).

`uses_global` and `asserts_type` route to a field like the other 17, but the live tool schema notes they additionally require
`enable_entity_tracking` (default `True`) — on a project indexed before that setting was enabled, these two sections stay empty until you reindex,
even though the type itself is valid and routable.

**Returns:** Direct callers (inbound) and direct callees (outbound), indirect callers, dependency graph (DOT format), similar code (when available).

Per-entry provenance fields on every caller and callee entry (v0.14.0+):

- `confidence`: string tag — `"exact"` (direct chunk_id resolution), `"recovered"` (stale ID re-resolved via `_resolve_by_symbol` Tier 1→3),
  `"ambiguous"` (multiple candidates)
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
| `max_hops` | 10 | Maximum path length. **Silently clamped to 20** via `min(arguments.get("max_hops", 10), 20)` (`search_handlers.py`) — passing 30 does not error, it just runs at 20. |
| `output_format` | "compact" | "compact" / "verbose" / "ultra" |

**Valid `edge_types` for `find_path` (12 types, a subset of the 21 `find_connections` types):**

`calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`

This list includes `assigns_to`/`reads_from`, which — same as in `find_connections` above — match zero edges in practice; they're listed in the
schema's allowed values but have no routing behind them.

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
