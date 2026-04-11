# MCP Tool Index (19 tools)

All tools use the `code-search:` server prefix. Always use fully qualified names.

## Contents
- Essential Tools (search_code, find_connections, find_path)
- Project Management (6 tools)
- Search Configuration (3 tools)
- Advanced Search (3 tools)
- Model Management (2 tools)
- Memory Management (2 tools)

---

## Essential Tools (Use These Most)

### code-search:search_code
Find code with natural language query or direct chunk lookup. Use for all initial code searches.

**Key options:** `query`, `chunk_id` (direct O(1) lookup), `k` (results count, default 4), `search_mode` ("hybrid"/"semantic"/"bm25"/"auto"), `model_key` ("qwen3"/"bge_m3"/"coderankembed"/"gte_modernbert"/"c2llm"), `use_routing` (default true), `file_pattern`, `include_dirs`, `exclude_dirs`, `chunk_type` (see below), `include_context` (default true), `auto_reindex` (default true), `max_age_minutes` (default 5), `ego_graph_enabled` (default false), `ego_graph_k_hops` (default 2, range 1-5), `ego_graph_max_neighbors_per_hop` (default 10, range 1-50), `include_parent` (default false), `output_format` ("compact"/"verbose"/"ultra", default "compact"), `max_context_tokens` (token-budget cap). Full parameter reference in [parameters.md](parameters.md).

**chunk_type values:** "function", "class", "method", "module", "decorated_definition", "interface", "enum", "struct", "type", "merged", "split_block", "community", or None

**Chunk ID format:** `file.py:start-end:type:name` (e.g., `auth.py:10-50:function:login`)

**Result fields (always):** `chunk_id`, `kind`, `score`, `blended_score`, `centrality`, `source`
**Result fields (optional):** `complexity_score`, `graph`, `reranker_score`, `summary`

### code-search:find_connections
Find all callers, dependencies, and relationships for a given symbol. Preferred over Grep for caller/dependency discovery.

**Key options:** `chunk_id` (preferred), `symbol_name` (fallback — may be ambiguous), `max_depth` (default 3, range 1-5), `exclude_dirs`, `relationship_types`, `output_format`

**Valid relationship types (21):** calls, inherits, uses_type, imports, decorates, raises, catches, instantiates, implements, overrides, assigns_to, reads_from, defines_constant, defines_enum_member, defines_class_attr, defines_field, uses_constant, uses_default, uses_global, asserts_type, uses_context_manager

### code-search:find_path
Find shortest path between two code entities via the relationship graph. Uses bidirectional BFS.

**Key options:** `source_chunk_id`, `target_chunk_id` (preferred), `source`/`target` symbol names (fallback), `edge_types`, `max_hops` (default 10, range 1-20), `output_format`

---

> This is a name-only catalog. For parameters, types, and examples, see [parameters.md](parameters.md) (essential tools) or call the tool via your MCP client, which will surface the authoritative schema from the server.

## Project Management

| Tool | Purpose |
|------|---------|
| `code-search:list_projects` | Show all indexed projects |
| `code-search:switch_project` | Switch active project |
| `code-search:get_index_status` | Check index health and staleness |
| `code-search:index_directory` | Index or re-index a project (supports incremental and multi-model indexing) |
| `code-search:clear_index` | Delete entire current index |
| `code-search:delete_project` | Safely delete project data |

## Search Configuration

| Tool | Purpose |
|------|---------|
| `code-search:configure_search_mode` | Set hybrid/semantic/bm25 mode and BM25/dense weights |
| `code-search:get_search_config_status` | View current search config |
| `code-search:configure_query_routing` | Multi-model routing settings |

## Advanced Search

| Tool | Purpose |
|------|---------|
| `code-search:find_similar_code` | Find functionally similar code |
| `code-search:configure_reranking` | Neural reranking settings |
| `code-search:configure_chunking` | Chunking + community detection (file/community summaries, sizing mode, etc.) |

## Model Management

| Tool | Purpose |
|------|---------|
| `code-search:list_embedding_models` | Show available models (BGE-M3, Qwen3-0.6B, CodeRankEmbed, GTE-ModernBERT, EmbeddingGemma-300m) |
| `code-search:switch_embedding_model` | Change embedding model (fast if previously loaded) |

**Note:** In `code-search:search_code.model_key`, the BGE-family key is `bge_m3`. `code-search:configure_query_routing.default_model` additionally accepts `bge_code`; consult `code-search:list_embedding_models` at runtime for the authoritative list of currently valid keys.

## Memory Management

| Tool | Purpose |
|------|---------|
| `code-search:get_memory_status` | Check RAM/VRAM usage |
| `code-search:cleanup_resources` | Free indexes, models, and GPU memory |
