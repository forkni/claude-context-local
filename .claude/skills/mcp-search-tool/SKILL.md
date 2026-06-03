---
name: mcp-search-tool
description: "Guides semantic code search via the code-search MCP server. Use when searching for code definitions, callers, dependencies, or tracing code flow in indexed projects. Provides correct workflows for search_code, find_connections, find_path, find_similar_code. Invoke /mcp-search-tool status to run a health check."
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

**SSCG benchmark:** 100% Hit@7 (k=7 hybrid, 2026-05-25): MRR 0.806, Recall@5 0.646, Recall@7 0.700. Recommended operating k: **7** (some targets rank 6–7; k=5 misses them). Default is `k=4`. See [references/performance.md](references/performance.md) for full results.

---

## Critical: Results Are Candidates, Not Answers

MCP search returns **ranked candidates**, not definitive answers. On the 2026-05-25 13-query SSCG benchmark (hybrid, k=7) Hit@7 = 100% — but the correct result is **not always ranked first**, and this is not a general reliability guarantee for arbitrary queries or codebases.

**Baseline rule:** **pass `k=7` explicitly when correctness matters.** The tool default is `k=4`; some targets rank 6–7 (e.g. `FaissVectorIndex.__init__` in the SSCG benchmark), so Hit@7 > Hit@5. Use `k=10` for architectural / global queries.

**Result Interpretation Workflow:**
1. Run `code-search:search_code(query="<your query>", k=7)` with appropriate filters
2. **Scan ALL k results** — read each chunk_id and code snippet
3. **Identify the best match** based on your actual need (not just highest score)
4. If the best match is a module/summary chunk but you need specific code, look at lower-ranked results
5. Use `chunk_id` from the best match for follow-up tools

**When rank-1 is most reliable:** small function discovery ("get X", "validate Y"), exact symbol lookup via `chunk_id`

**When you MUST scan all results:** class overview queries, sibling context ("encode and decode"), queries where module/community chunks may surface at rank-1

---

## Prerequisites

- MCP server running and connected in Claude Code (`/mcp` → Reconnect next to `code-search`)
- At least one project indexed: `code-search:index_directory(path="<your-project>")`

---

## Quick Start: Which Tool?

> **Note on snippet style:** the arrow-diagram and examples below are pseudocode, not executable Python. MCP tool arguments are JSON-shaped — booleans are written `true`/`false` (not `True`/`False`), and every argument is named. Pass the values to your MCP client as native parameters rather than copy-pasting the text.


```
What are you trying to do?
│
├─ "Find callers of X" ──────────────► code-search:find_connections(chunk_id=<chunk_id>)
├─ "What depends on X" ──────────────► code-search:find_connections(chunk_id=<chunk_id>)
├─ "Trace flow from X to Y" ─────────► code-search:find_path(source_chunk_id=<src>, target_chunk_id=<tgt>)
├─ "How does X connect to Y?" ───────► code-search:find_path(source_chunk_id=<src>, target_chunk_id=<tgt>)
├─ "Find only imports/inheritance" ──► code-search:find_connections(chunk_id=<chunk_id>, relationship_types=["imports", "inherits"])
├─ "Find similar code to X" ─────────► code-search:find_similar_code(chunk_id=<chunk_id>)
│
├─ "Find function definition" ───────► code-search:search_code(query="<your query>", k=7, chunk_type="function")
├─ "Find class definition" ──────────► code-search:search_code(query="<your query>", k=7, chunk_type="class")
├─ "Find exact API call pattern" ────► code-search:search_code(query="<your query>", k=7, search_mode="bm25")
├─ "Understand concept/feature" ─────► code-search:search_code(query="<your query>", k=7)  [hybrid mode]
├─ "Architectural / global query" ───► code-search:search_code(query="<your query>", k=10)
├─ "Expand via call graph neighbors"─► code-search:search_code(..., ego_graph_enabled=true, ego_graph_k_hops=2)
│
└─ "Validate line numbers only" ─────► Grep (LAST RESORT)
```

**CRITICAL**: For ANY query about callers, dependencies, or code flow:
1. First: `code-search:search_code(query=..., k=7)` to get chunk_id
2. Then: `code-search:find_connections(chunk_id=<chunk_id>)` for relationships

**NEVER use Grep for relationship discovery.**

---

## Common Mistakes

| Wrong Approach | Correct Approach |
|----------------|------------------|
| `Grep("\.function\(")` for callers | 1. `code-search:search_code(query="<your query>", k=7)` → pick `chunk_id`. 2. `code-search:find_connections(chunk_id=<chunk_id>)` |
| Multiple Reads to trace a call chain | `code-search:find_connections(chunk_id=<chunk_id>, max_depth=5)` |
| Manual import tracing | `code-search:find_connections(chunk_id=<chunk_id>, relationship_types=["imports"])` |

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

19-tool catalog (names + one-liner purposes): [references/tool-index.md](references/tool-index.md)
Full parameter reference for essential tools (search_code, find_connections, find_path): [references/parameters.md](references/parameters.md)
Advanced features (multi-hop, intent routing, summaries): [references/advanced-features.md](references/advanced-features.md)
Benchmark data & mode selection guide: [references/performance.md](references/performance.md)

---

## Gotchas

These are non-obvious traps from real session experience — not things the docs mention.

**Results are NOT sorted by blended_score.** The returned array is ordered by internal file/community grouping, not by score. When you need a true ranking (e.g. for MRR/Recall evaluation), sort by `blended_score` descending yourself:
```python
ranked = sorted(results, key=lambda r: r.get("blended_score", 0), reverse=True)
```
Failing to sort is why a result at array position 0 isn't always rank-1.

**`source="ego_graph"` items appear in the main results array.** When `ego_graph_enabled=true` (or when the live config has it on), expansion neighbors are interleaved with direct hits and carry their own `blended_score`. They count toward your top-k window. Don't filter them out before ranking — they are legitimate ranked candidates.

**`ego_graph.enabled=True` in the live config even though the EgoGraphConfig dataclass default is `False`.** The server reads `search_config.json`, which ships with `"ego_graph": {"enabled": true}`. The Python default is irrelevant once the JSON is loaded. Verify with `get_search_config().ego_graph.enabled`.

**`split_block` variants of the same function are one logical hit.** A long function chunked into `split_block` pieces (e.g. `file.py:10-40:split_block:fn` and `file.py:41-80:split_block:fn`) should count as one unique chunk in Recall/Hit metrics. Normalize and deduplicate by stripping the line-range portion: `file.py:10-40:type:name` → `file.py:type:name`. As of v0.12.1, split_block nodes carry full `uses_type`/`imports` relationship edges extracted from the method signature — `find_connections` will return these edges.

**Community and module summary chunks surface at rank-1 on class-overview queries.** They have IDs like `__community__/label:0-0:community:label` or `file.py:0-0:module:name`. Add `chunk_type="function"` or `chunk_type="class"` to filter them when you need a specific implementation.

**Unicode symbols crash on Windows cp1252 terminals.** `✓`/`✗` cause `UnicodeEncodeError` in any script that writes to stdout in a cmd/PowerShell window without UTF-8. Use plain ASCII (`PASS`/`FAIL`) or run with `PYTHONUTF8=1`. The smoke test in this skill uses plain ASCII for this reason.

**Torch dynamo INFO logs spam stderr** when importing `search.hybrid_searcher`. Suppress with `2>nul` (Windows) or `2>/dev/null` (Linux/WSL).

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **No results** | Check project: `code-search:list_projects`, `code-search:switch_project` if needed. Verify index: `code-search:get_index_status`. Re-index: `code-search:index_directory(path)` |
| **Bad results** | Try different mode: hybrid → semantic → bm25. Add filters: `file_pattern`, `chunk_type`. Increase k |
| **Wrong result at rank-1** | Scan all k results — answer likely at rank 2-4. Use `chunk_type` filter to exclude module/community summary chunks |
| **Too slow** | Use `search_mode="bm25"` for exact symbols (fastest). Check: `code-search:get_memory_status`. Free: `code-search:cleanup_resources` |
| **Memory issues** | `code-search:cleanup_resources`. Switch to a lighter model: `code-search:switch_embedding_model("google/embeddinggemma-300m")` (~1.2GB, default) or `code-search:switch_embedding_model("Alibaba-NLP/gte-modernbert-base")` (0.28GB, lightest) |

---

## Status Check

When the user invokes the skill with the argument `status` (e.g. `/mcp-search-tool status`), run this exact sequence and report the result:

1. `code-search:list_projects` — show which project is active, when it was last indexed
2. `code-search:get_index_status` — chunk count, staleness, graph data presence
3. `code-search:get_search_config_status` — current search_mode, BM25/dense weights, reranker state
4. `code-search:get_memory_status` — RAM/VRAM usage

Summarize in one short block: **active project**, **index staleness**, **active search mode**, **memory pressure**. Flag anything that looks off (no active project, stale index, missing graph data, >80% VRAM).
