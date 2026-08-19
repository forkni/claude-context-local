# MCP Tool Index (18 tools: 10 core + 8 advanced)

All tools use the `code-search:` server prefix. Always use fully qualified names.

**Tiering:** by default the server's `list_tools` advertises only the **10 core** tools (tool-count budget, MCP Architecture-Patterns §VI-C). Set
`MCP_EXPOSE_ADVANCED_TOOLS` to `1`/`true`/`yes` (case-insensitive) on the server process **and reconnect** (`/mcp` → Reconnect) to also *list* the 8
**advanced** tools (marked below). This flag only controls what `list_tools` advertises — `TOOL_DISPATCH` internally registers all 18 tools
regardless, so an advanced tool called by exact name while unlisted still fails at the client/protocol level (the client won't offer it), not because
the server can't route it. **An unlisted tool cannot be called — it is not dispatchable in this session, and calling it speculatively will fail.**
Check the "In-band alternative" column below before asking the user to enable the flag; only `configure_search_mode` has one. See `SKILL.md` → "Tool
Tiers" for the full decision procedure.

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

**Key options:** `query`, `chunk_id` (direct O(1) lookup), `k` (schema publishes no default, only bounds min 1/max 100; effective default **7** via
`search_mode.default_k`), `search_mode` ("hybrid"/"semantic"/"bm25"/"auto"), `file_pattern`, `include_dirs`, `exclude_dirs`, `chunk_type` (see below),
`include_context` (default true), `auto_reindex` (default true), `max_age_minutes` (schema publishes no default; effective default **30** via
`performance.max_index_age_minutes`), `ego_graph_enabled` (schema publishes no default, server default **on** — **real tri-state gate**: omit to
defer to the server default, `true` forces it on and applies the hop overrides, `false` forces it off for that call), `ego_graph_k_hops` (default 2,
range 1-3), `ego_graph_max_neighbors_per_hop` (default 10, range 1-50), `include_parent` (default false), `include_signatures` (default false —
attach a signature-only view per result), `output_format` (schema publishes no default, effective default **"ultra"** via `config.output.format`),
`max_context_tokens` (token-budget cap, default 0/no cap), `include_top_callers` (default false — attach up to 2 `{name, file}` caller hints per
result, 2026-08-14). Full parameter reference (with the schema-vs-effective fallback chains) in [parameters.md](parameters.md).

**chunk_type values (12):** see [parameters.md](parameters.md) (omit the field to match any chunk type)

**Chunk ID format:** `file.py:start-end:type:name` (e.g., `auth.py:10-50:function:login`)

**Result fields (always):** `file`, `lines`, `kind`, `score`, `chunk_id`, `source` (`_format_search_results` in `mcp_server/tools/result_view.py`).
**Present whenever the project has an indexed call graph** (on by default — `GraphEnhancedConfig.centrality_annotation`/`centrality_reranking` in
`search/config.py`): `centrality`, `blended_score` (with the default `centrality_alpha=0.0`, `blended_score` is numerically identical to `score`).
**Result fields (optional):** `name` (chunk has a name), `summary` (module chunks with a docstring), `reranker_score` (neural reranking ran),
`complexity_score` (functions with a computed score), `top_callers` (only with `include_top_callers=true`).

### code-search:find_connections

Find all callers, callees, dependencies, and relationships for a given symbol. Returns `direct_callers` (inbound) and `direct_callees` (outbound) with
per-entry provenance (`resolver_source`, `resolver_confidence`). Preferred over Grep for caller/dependency discovery.

**Key options:** `chunk_id` (preferred), `symbol_name` (fallback — may be ambiguous), `max_depth` (default 3, range 1-5), `exclude_dirs`,
`relationship_types`, `hide_ambiguous` (schema publishes no default, server default **true** since 2026-08-16 — hide `"ambiguous"`-tagged call edges;
confidence counters stay pre-filter totals; pass `false` to see unfiltered edges), `output_format`

**Valid relationship types (21 enum members, only 19 route to a response field — `assigns_to`/`reads_from` don't):** see
[parameters.md](parameters.md)

### code-search:find_path

Find shortest path between two code entities via the relationship graph. Uses bidirectional BFS.

**Key options:** `source_chunk_id`, `target_chunk_id` (preferred), `source`/`target` symbol names (fallback), `edge_types`, `max_hops` (default 10,
range 1-20), `output_format`

---

> This is a name-only catalog. For parameters, types, and examples, see [parameters.md](parameters.md) (essential tools) or call the tool via your
> MCP client, which will surface the authoritative schema from the server.

## Project Management

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:list_projects` | Core | Show all indexed projects | — |
| `code-search:switch_project` | Core | Switch active project | — |
| `code-search:get_index_status` | Core | Check index health and staleness | — |
| `code-search:index_directory` | Core | Index or re-index a project (supports incremental indexing). **Key options:** `directory_path` (required), `project_name` (optional, defaults to the directory name — use to organize/disambiguate), `incremental` (default true), `wait` (default true — blocks until done and returns results inline; pass `false` for large repos to get a `job_id` immediately and poll `get_index_status(job_id=...)` until `status="done"`/`"error"`). `include_dirs`/`exclude_dirs` can be changed on a later re-index — passing either forces a full reindex and **replaces** the stored filters wholesale (never merges), so re-pass the full list, not just the delta (`_run_index_directory`/`update_project_filters` in `mcp_server/tools/index_handlers.py`/`mcp_server/storage_manager.py`). Omit both to keep the stored filters. **ADR-0036:** an include pattern naming a normally-excluded dependency-tree path (`venv`, `site-packages`, `node_modules`, `.tox`, etc. — `DEPENDENCY_TREE_DIRS` in `chunking/language_registry.py`) is **additive** — it re-admits that path on top of normal project scope without narrowing out anything else. Any other include path still **narrows**, replacing scope with just what it names. `exclude_dirs` always wins on a matching path. | — |
| `code-search:clear_index` | Advanced | Delete entire current index | None — a stale/corrupted index is fixed by re-running the core `index_directory(directory_path=...)`, not by clearing first |
| `code-search:delete_project` | Advanced | Safely delete project data | None |

## Search Configuration

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:configure_search_mode` | Advanced | Set hybrid/semantic/bm25 mode and BM25/dense weights | `search_code(search_mode="bm25"\|"semantic"\|"hybrid")` for a one-off override |
| `code-search:get_search_config_status` | Advanced | View current search config | None |

## Advanced Search

*(Section name is functional grouping, not the Core/Advanced dispatch tier — see the per-row Tier column; `find_similar_code` is a core-tier tool
despite the section title.)*

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:find_similar_code` | Core | Find functionally similar code. **Key options:** `chunk_id` (required), `k` (schema declares **no default** — the handler falls back to `search_mode.default_k`, same as `search_code`; effective default is **7** on this deployment, not 4), `exclude_same_file` (default false — set true for cross-file-only matches) | — |
| `code-search:configure_reranking` | Advanced | Neural reranking settings | None |
| `code-search:configure_chunking` | Advanced | Chunking settings (file summaries, sizing mode, etc.) | None |

## Model Management

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:list_embedding_models` | Advanced | Show available models (BGE-M3, Qwen3-0.6B, EmbeddingGemma-300m, F2LLM-v2-0.6B) | None |
| `code-search:switch_embedding_model` | Advanced | Change active embedding model (single-model; swaps index when switching) | None |

## Memory Management

| Tool | Tier | Purpose | In-band alternative |
|------|------|---------|----------------------|
| `code-search:get_memory_status` | Core | Check RAM/VRAM usage | — |
| `code-search:cleanup_resources` | Core | Free indexes, models, and GPU memory | — |
