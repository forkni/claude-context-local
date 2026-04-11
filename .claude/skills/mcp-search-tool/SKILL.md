---
name: mcp-search-tool
description: "Guides semantic code search via the code-search MCP server. Provides correct workflows for code-search:search_code, code-search:find_connections, and code-search:find_path. Triggers when searching for code definitions, callers, dependencies, or tracing code flow in indexed projects."
user-invocable: true
argument-hint: "search query or 'status' for index health"
allowed-tools: "Bash, Read, Grep, code-search:search_code, code-search:find_connections, code-search:find_path, code-search:find_similar_code, code-search:index_directory, code-search:list_projects, code-search:switch_project, code-search:get_index_status, code-search:clear_index, code-search:delete_project, code-search:configure_search_mode, code-search:get_search_config_status, code-search:configure_query_routing, code-search:configure_reranking, code-search:configure_chunking, code-search:list_embedding_models, code-search:switch_embedding_model, code-search:get_memory_status, code-search:cleanup_resources"
---

# MCP Search Tool Skill

## On Activation

**IMPORTANT**: This skill provides BEHAVIORAL INSTRUCTIONS, not information to analyze.

**When this skill loads**:
1. Acknowledge: "MCP Search skill active. Results are ranked candidates — I'll scan all results, not just rank-1."
2. Wait for the user's actual task
3. Apply the guidance below to all subsequent code search operations

**DO NOT**: Explore or analyze this skill document, launch agents to investigate the skill, or treat this as a request for information about MCP tools.

---

## Purpose

Ensures all MCP semantic search operations follow correct workflows for accurate results. The key behavioral rule: **search results are ranked candidates, not definitive answers — always scan all returned results.**

**SSCG benchmark (2026-04-10, 13 queries, 3 modes):** **100% Hit@5** across all modes — but only when `k≥5`. Default is `k=4`. Best MRR: BM25 0.846. See [references/performance.md](references/performance.md) for full results.

---

## Critical: Results Are Candidates, Not Answers

MCP search returns **ranked candidates**, not definitive answers. The correct result is always present in the top 5 (100% Hit@5), but it is NOT always ranked first.

**Baseline rule:** **use `k=5` when correctness matters.** The tool default is `k=4`, which means one answer in twenty will be missed purely because you didn't ask for enough candidates. Use `k=10` for architectural / global queries.

**Result Interpretation Workflow:**
1. Run `code-search:search_code(query, k=5)` with appropriate filters
2. **Scan ALL k results** — read each chunk_id and code snippet
3. **Identify the best match** based on your actual need (not just highest score)
4. If the best match is a module/summary chunk but you need specific code, look at lower-ranked results
5. Use `chunk_id` from the best match for follow-up tools

**When rank-1 is most reliable:** small function discovery ("get X", "validate Y"), exact symbol lookup via `chunk_id`

**When you MUST scan all results:** class overview queries, sibling context ("encode and decode"), queries where module/community chunks may surface at rank-1

---

## Quick Start: Which Tool?

```
What are you trying to do?
│
├─ "Find callers of X" ──────────────► code-search:find_connections(chunk_id)
├─ "What depends on X" ──────────────► code-search:find_connections(chunk_id)
├─ "Trace flow from X to Y" ─────────► code-search:find_path(source_chunk_id, target_chunk_id)
├─ "How does X connect to Y?" ───────► code-search:find_path(source_chunk_id, target_chunk_id)
├─ "Find only imports/inheritance" ──► code-search:find_connections(chunk_id, relationship_types=["imports", "inherits"])
├─ "Find similar code to X" ─────────► code-search:find_similar_code(chunk_id)
│
├─ "Find function definition" ───────► code-search:search_code(query, k=5, chunk_type="function")
├─ "Find class definition" ──────────► code-search:search_code(query, k=5, chunk_type="class")
├─ "Find exact API call pattern" ────► code-search:search_code(query, search_mode="bm25")
├─ "Understand concept/feature" ─────► code-search:search_code(query, k=5)  [hybrid mode]
├─ "Architectural / global query" ───► code-search:search_code(query, k=10)
├─ "Expand via call graph neighbors"─► code-search:search_code(..., ego_graph_enabled=True, ego_graph_k_hops=2)
│
└─ "Validate line numbers only" ─────► Grep (LAST RESORT)
```

**CRITICAL**: For ANY query about callers, dependencies, or code flow:
1. First: `code-search:search_code()` to get chunk_id
2. Then: `code-search:find_connections(chunk_id)` for relationships

**NEVER use Grep for relationship discovery.**

---

## Common Mistakes

| Wrong Approach | Correct Approach |
|----------------|------------------|
| `Grep("\.function\(")` for callers | `code-search:find_connections(chunk_id)` |
| Multiple Reads to trace flow | `code-search:find_connections(max_depth=5)` |
| Manual import tracing | `code-search:find_connections(symbol_name)` |

---

## 19-Tool Summary

| Tool | Purpose |
|------|---------|
| **code-search:search_code** | Find code with NL query or direct chunk lookup |
| **code-search:find_connections** | Find callers, dependencies, relationships |
| **code-search:find_path** | Shortest path between two entities |
| code-search:find_similar_code | Functionally similar code |
| code-search:index_directory | Index project (one-time setup) |
| code-search:list_projects | Show indexed projects |
| code-search:switch_project | Change active project |
| code-search:get_index_status | Check index health |
| code-search:clear_index | Delete current index |
| code-search:delete_project | Safely delete project data |
| code-search:configure_search_mode | Set search mode & BM25/dense weights |
| code-search:get_search_config_status | View current config |
| code-search:configure_query_routing | Multi-model routing settings |
| code-search:configure_reranking | Neural reranking settings |
| code-search:configure_chunking | Code chunking & community detection |
| code-search:list_embedding_models | Show available models |
| code-search:switch_embedding_model | Change embedding model |
| code-search:get_memory_status | Check RAM/VRAM usage |
| code-search:cleanup_resources | Free memory/caches |

Full parameter reference: [references/tool-index.md](references/tool-index.md)
Detailed params for essential tools: [references/parameters.md](references/parameters.md)
Advanced features (multi-hop, intent routing, summaries): [references/advanced-features.md](references/advanced-features.md)
Benchmark data & mode selection guide: [references/performance.md](references/performance.md)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **No results** | Check project: `code-search:list_projects`, `code-search:switch_project` if needed. Verify index: `code-search:get_index_status`. Re-index: `code-search:index_directory(path)` |
| **Bad results** | Try different mode: hybrid → semantic → bm25. Add filters: `file_pattern`, `chunk_type`. Increase k |
| **Wrong result at rank-1** | Scan all k results — answer likely at rank 2-4. Use `chunk_type` filter to exclude module/community summary chunks |
| **Too slow** | Use `search_mode="bm25"` for exact symbols (fastest). Check: `code-search:get_memory_status`. Free: `code-search:cleanup_resources` |
| **Memory issues** | `code-search:cleanup_resources`. Smaller model: `code-search:switch_embedding_model("google/embeddinggemma-300m")` |

---

## Status Check

When the user invokes the skill with the argument `status` (e.g. `/mcp-search-tool status`), run this exact sequence and report the result:

1. `code-search:list_projects` — show which project is active, when it was last indexed
2. `code-search:get_index_status` — chunk count, staleness, graph data presence
3. `code-search:get_search_config_status` — current search_mode, BM25/dense weights, reranker state
4. `code-search:get_memory_status` — RAM/VRAM usage

Summarize in one short block: **active project**, **index staleness**, **active search mode**, **memory pressure**. Flag anything that looks off (no active project, stale index, missing graph data, >80% VRAM).
