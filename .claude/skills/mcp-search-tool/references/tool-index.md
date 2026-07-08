# MCP Tool Index (18 tools: 10 core + 8 advanced)

All tools use the `code-search:` server prefix. Always use fully qualified names.

**Tiering:** by default the server's `list_tools` advertises only the **10 core** tools
(tool-count budget, MCP Architecture-Patterns §VI-C). Set `MCP_EXPOSE_ADVANCED_TOOLS=1` on
the server process **and reconnect** (`/mcp` → Reconnect) to also *list* the 8 **advanced**
tools (marked below). **An unlisted tool cannot be called — it is not dispatchable in this
session, and calling it speculatively will fail.** Check the "In-band alternative" column
below before asking the user to enable the flag; only `configure_search_mode` has one. See
`SKILL.md` → "Tool Tiers" for the full decision procedure.

## Contents

- Essential Tools (search_code, find_connections, find_path)
- Project Management (6 tools)
- Search Configuration (2 tools)
- Advanced Search (3 tools)
- Model Management (2 tools)
- Memory Management (2 tools)

---

## Essential Tools (Use These Most)

### code-search:search_code

Find code with natural language query or direct chunk lookup. Use for all initial code searches.

**Key options:** `query`, `chunk_id` (direct O(1) lookup), `k` (results count, default 7), `search_mode` ("hybrid"/"semantic"/"bm25"/"auto"), `file_pattern`, `include_dirs`, `exclude_dirs`, `chunk_type` (see below), `include_context` (default true), `auto_reindex` (default true), `max_age_minutes` (default 5), `ego_graph_enabled` (default false), `ego_graph_k_hops` (default 2, range 1-5), `ego_graph_max_neighbors_per_hop` (default 10, range 1-50), `include_parent` (default false), `output_format` ("compact"/"verbose"/"ultra", default "compact"), `max_context_tokens` (token-budget cap). Full parameter reference in [parameters.md](parameters.md).

**chunk_type values:** "function", "class", "method", "module", "decorated_definition", "interface", "enum", "struct", "type", "merged", "split_block", "community" (omit the field to match any chunk type)

**Chunk ID format:** `file.py:start-end:type:name` (e.g., `auth.py:10-50:function:login`)

**Result fields (always):** `chunk_id`, `kind`, `score`, `blended_score`, `centrality`, `source`
**Result fields (optional):** `complexity_score`, `graph`, `reranker_score`, `summary`

### code-search:find_connections

Find all callers, callees, dependencies, and relationships for a given symbol. Returns `direct_callers` (inbound) and `direct_callees` (outbound) with per-entry provenance (`resolver_source`, `resolver_confidence`). Preferred over Grep for caller/dependency discovery.

**Key options:** `chunk_id` (preferred), `symbol_name` (fallback — may be ambiguous), `max_depth` (default 3, range 1-5), `exclude_dirs`, `relationship_types`, `output_format`

**Valid relationship types (21):** calls, inherits, uses_type, imports, decorates, raises, catches, instantiates, implements, overrides, assigns_to, reads_from, defines_constant, defines_enum_member, defines_class_attr, defines_field, uses_constant, uses_default, uses_global, asserts_type, uses_context_manager

### code-search:find_path

Find shortest path between two code entities via the relationship graph. Uses bidirectional BFS.

**Key options:** `source_chunk_id`, `target_chunk_id` (preferred), `source`/`target` symbol names (fallback), `edge_types`, `max_hops` (default 10, range 1-20), `output_format`

---

> This is a name-only catalog. For parameters, types, and examples, see [parameters.md](parameters.md) (essential tools) or call the tool via your MCP client, which will surface the authoritative schema from the server.

## Project Management

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:list_projects` | Core | Show all indexed projects | — |
| `code-search:switch_project` | Core | Switch active project | — |
| `code-search:get_index_status` | Core | Check index health and staleness | — |
| `code-search:index_directory` | Core | Index or re-index a project (supports incremental indexing) | — |
| `code-search:clear_index` | Advanced | Delete entire current index | None — a stale/corrupted index is fixed by re-running the core `index_directory(path)`, not by clearing first |
| `code-search:delete_project` | Advanced | Safely delete project data | None |

## Search Configuration

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:configure_search_mode` | Advanced | Set hybrid/semantic/bm25 mode and BM25/dense weights | `search_code(search_mode="bm25"\|"dense"\|"hybrid")` for a one-off override |
| `code-search:get_search_config_status` | Advanced | View current search config | None |

## Advanced Search

*(Section name is functional grouping, not the Core/Advanced dispatch tier — see the
per-row Tier column; `find_similar_code` is a core-tier tool despite the section title.)*

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:find_similar_code` | Core | Find functionally similar code | — |
| `code-search:configure_reranking` | Advanced | Neural reranking settings | None |
| `code-search:configure_chunking` | Advanced | Chunking + community detection (file/community summaries, sizing mode, etc.) | None |

## Model Management

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:list_embedding_models` | Advanced | Show available models (BGE-M3, Qwen3-0.6B, EmbeddingGemma-300m, CodeRankEmbed, GTE-ModernBERT) | None |
| `code-search:switch_embedding_model` | Advanced | Change active embedding model (single-model; swaps index when switching) | None |

## Memory Management

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:get_memory_status` | Core | Check RAM/VRAM usage | — |
| `code-search:cleanup_resources` | Core | Free indexes, models, and GPU memory | — |
