---
name: mcp-search-tool
description: "Guides semantic code search via the code-search MCP server. Use when searching for code definitions, callers, callees, dependencies, or tracing code flow in indexed projects. Provides correct workflows for search_code, find_connections, find_path, find_similar_code. Invoke /mcp-search-tool status to run a health check."
user-invocable: true
argument-hint: "search query or 'status' for index health"
allowed-tools: "Bash, Read, Grep, code-search:search_code, code-search:find_connections, code-search:find_path, code-search:find_similar_code, code-search:index_directory, code-search:list_projects, code-search:switch_project, code-search:get_index_status, code-search:clear_index, code-search:delete_project, code-search:configure_search_mode, code-search:get_search_config_status, code-search:configure_reranking, code-search:configure_chunking, code-search:list_embedding_models, code-search:switch_embedding_model, code-search:get_memory_status, code-search:cleanup_resources"
metadata:
  version: 0.18.0
  mcp-server: code-search
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

**SSCG benchmark (searcher-only, 63-query, 2026-06-26, gte-reranker):** MRR 0.700, Recall@5 0.625, Recall@7 0.696, Hit@5 0.984. Recommended operating k: **7** (some targets rank 6–7). Engine default is `k=7`; pass it explicitly when correctness matters. Use `k=10` for architectural/global queries. See [references/performance.md](references/performance.md) for full results.

**DSPy agent eval (2026-06-26, 77-query dataset, 4-tool):** Recall@7=0.9046, MRR=0.8519, Hit@7=1.000, tool_sel=1.000 on the held-out test split (18 queries, A–F coverage). Use all 4 tools: search_code, find_connections, find_path, find_similar_code. See [references/performance.md](references/performance.md).

---

## Critical: Results Are Candidates, Not Answers

MCP search returns **ranked candidates**, not definitive answers. On the 2026-05-25 13-query SSCG benchmark (hybrid, k=7) Hit@7 = 100% — but the correct result is **not always ranked first**, and this is not a general reliability guarantee for arbitrary queries or codebases.

**Baseline rule:** **pass `k=7` explicitly when correctness matters.** The engine default is `k=7` (changed from 4 on 2026-06-24 based on SSCG benchmark: MRR +0.093, R@7 +0.122 vs k=4); targets may still rank 6–7 on complex or multi-target queries, so passing it explicitly is good defensive practice. Use `k=10` for architectural / global queries.

**Result Interpretation Workflow:**
1. Call `code-search:search_code(query="<your query>", k=7, include_context=true)` — `include_context` fetches ego-graph/graph-hop neighbors inline (more recall per call). Use `k=10` for architectural / global queries.
2. **Scan ALL k results** — results are pre-sorted in relevance order (centrality-reranked blended_score descending) under the server default; module/community summary chunks appear at the tail for non-GLOBAL queries. Array position 0 is the highest blended_score result. The tool returns **metadata rows** (chunk_id, type, name, scores, short snippet). Names + types + scores are enough to judge relevance — you do NOT need to refetch bodies to "confirm". You may optionally re-sort by `reranker_score` for pure cross-encoder order, but doing so will **re-promote demoted summary chunks** (see Gotchas).
3. **Issue a second search with alternate phrasings** only when the question is genuinely ambiguous about *which subsystem* should answer it — a **bare** generic-operation verb with no domain qualifier (e.g. "validate the input", "save the data", "load config") could plausibly map to unrelated implementations in several files, and that ambiguity is worth resolving with 2–3 diverse queries (synonyms, subsystem names, related symbol names). **Do NOT** escalate just because one of those verbs (validate/normalize/encode/decode/load/save/id-handling) appears in the query — if the query already names a specific domain object that pins the subsystem down (e.g. "validate **JWT token**", "encode a **chunk_id**", "save the **index config**"), a single search is enough; see "When rank-1 is most reliable" below. Separately, also issue a second search when the first result set is concentrated in one module but the concept plausibly also exists in a sibling file. Do not pad an already-narrow, domain-qualified query with an unneeded second call.
4. **Identify the best match** based on your actual need.  For MRR / lead-chunk ranking, prefer the canonical `class` or `method`/`function` chunk whose name most directly matches the question — never a `split_block`, `module`, or `decorated_definition` fragment (even if it scores slightly higher; see Gotchas).
5. If the best match is a module/summary chunk but you need specific code, look at lower-ranked results or filter with `chunk_type="function"` / `chunk_type="class"`.
6. Use `chunk_id` from the best match for follow-up tools.

**When rank-1 is most reliable:** small function discovery with a domain-qualified object ("get the user session", "validate **JWT token**"), exact symbol lookup via `chunk_id`

**When you MUST scan all results:** class overview queries, sibling context ("encode and decode"), bare/unqualified generic-operation queries ("validate the input"), queries where the answer may rank 5–7

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
├─ "What does X call" ───────────────► code-search:find_connections(chunk_id=<chunk_id>)
├─ "What depends on X" ──────────────► code-search:find_connections(chunk_id=<chunk_id>)
├─ "Trace flow from X to Y" ─────────► code-search:find_path(source_chunk_id=<src>, target_chunk_id=<tgt>, max_hops=20)
├─ "How does X connect to Y?" ───────► code-search:find_path(source_chunk_id=<src>, target_chunk_id=<tgt>, max_hops=20)
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

**`find_path` — pass `max_hops=20` on the first call.** The tool's default `max_hops` is only 10
(range 1–20). A real path longer than 10 hops returns `path_found:false` with a hint to retry at a
higher `max_hops`, which costs an extra call to reach the same answer. A bidirectional-BFS call at
`max_hops=20` costs the same as one at the default — there's no accuracy or safety trade-off, just
a wasted round trip if you start low. Set it to 20 explicitly whenever you already have both
`source_chunk_id` and `target_chunk_id` and want a definitive answer in one call. Narrow it below 20
only when you deliberately want to test for a *short* connection (e.g. "are these directly
related?") and a `path_found:false` at low `max_hops` is itself the useful signal.

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
| `find_path` at default `max_hops=10`, then retrying higher | Pass `max_hops=20` on the first call when both chunk_ids are already known |
| Second search triggered by the bare presence of a word like "validate"/"save"/"load" | Only escalate when the query has **no** domain-qualifying object — "validate JWT token" already names its subsystem and is answered by one search |

---

## 18-Tool Summary (Core + Advanced tiers)

By default the server's `list_tools` advertises only the **10 core tools** below (tool-count
budget, MCP Architecture-Patterns §VI-C). Set `MCP_EXPOSE_ADVANCED_TOOLS=1` on the server
process and reconnect (`/mcp` → Reconnect) to also *list* the 8 advanced tools.

**An unlisted tool cannot be called — do not assume otherwise.** If a task's "natural" tool is
one of the 8 advanced tools below and it is not currently listed:
1. **Check for an in-band alternative first** — only `configure_search_mode` has one:
   `search_code(search_mode="bm25"|"dense"|"hybrid")` sets the mode for that call without
   needing the advanced tool at all.
2. **If no in-band alternative exists**, tell the user the tool is unlisted and ask them to set
   `MCP_EXPOSE_ADVANCED_TOOLS=1` on the server process and reconnect (`/mcp` → Reconnect) —
   note this accepts the larger tool-surface accuracy cost the 10-tool default exists to avoid.
3. **Never call an advanced tool speculatively while it is unlisted** — an unlisted tool is not
   dispatchable in this session and the call will fail.

**Core (10, listed by default):**

| Tool | Purpose |
|------|---------|
| **code-search:search_code** | Find code with NL query or direct chunk lookup |
| **code-search:find_connections** | Find callers, callees, dependencies, relationships |
| **code-search:find_path** | Shortest path between two entities |
| code-search:find_similar_code | Functionally similar code |
| code-search:index_directory | Index project (one-time setup) |
| code-search:list_projects | Show indexed projects |
| code-search:switch_project | Change active project |
| code-search:get_index_status | Check index health |
| code-search:get_memory_status | Check RAM/VRAM usage |
| code-search:cleanup_resources | Free memory/caches |

**Advanced (8, hidden unless `MCP_EXPOSE_ADVANCED_TOOLS=1` is set and the server is reconnected):**

| Tool | Purpose | In-band alternative |
|------|---------|----------------------|
| code-search:clear_index | Delete current index | None — a stale/corrupted index is fixed by re-running the core `index_directory(path)`, not by clearing first |
| code-search:delete_project | Safely delete project data | None |
| code-search:configure_search_mode | Set search mode & BM25/dense weights | `search_code(search_mode="bm25"\|"dense"\|"hybrid")` for a one-off override |
| code-search:get_search_config_status | View current config | None |
| code-search:configure_reranking | Neural reranking settings | None |
| code-search:configure_chunking | Code chunking & community detection | None |
| code-search:list_embedding_models | Show available models | None |
| code-search:switch_embedding_model | Change embedding model | None |

18-tool catalog (names + one-liner purposes, tiered): [references/tool-index.md](references/tool-index.md)
Full parameter reference for essential tools (search_code, find_connections, find_path): [references/parameters.md](references/parameters.md)
Advanced features (multi-hop, intent routing, summaries): [references/advanced-features.md](references/advanced-features.md)
Benchmark data & mode selection guide: [references/performance.md](references/performance.md)

---

## Gotchas

These are non-obvious traps from real session experience — not things the docs mention.

**Results are pre-sorted by relevance (blended_score descending) under the server default (`source_order_output=false`, v0.18.0+).** Module/community summary chunks are demoted to the tail for non-GLOBAL queries. Array position 0 is now the highest blended_score result. If you need strict cross-encoder order, re-sort by `reranker_score`:
```python
ranked = sorted(results, key=lambda r: (r.get("reranker_score", 0), r.get("blended_score", 0)), reverse=True)
```
**Caveat:** re-sorting by `reranker_score` will re-promote demoted module/community summary chunks (e.g. a `module:hybrid_searcher` summary with reranker_score 0.94 lands at position 28 in the default order because blended_score factors in centrality; re-sorting elevates it back to position 0). Apply the re-sort deliberately when you specifically want pure cross-encoder ranking.

**`search_code` returns metadata only — do NOT refetch chunk bodies.** Each result row contains `chunk_id`, `type`, `name`, `scores`, and a short snippet.  Names, types, and scores are sufficient to judge relevance; additional tool calls to fetch or "confirm" the body of each candidate waste call budget without improving precision.

**`source="ego_graph"` items appear in the main results array.** When `ego_graph_enabled=true` (or when the live config has it on), expansion neighbors are interleaved with direct hits and carry their own `blended_score`. They count toward your top-k window. Don't filter them out before ranking — they are legitimate ranked candidates.

**`ego_graph.enabled=True` in the live config even though the EgoGraphConfig dataclass default is `False`.** The server reads `search_config.json`, which ships with `"ego_graph": {"enabled": true}`. The Python default is irrelevant once the JSON is loaded. Verify with `get_search_config().ego_graph.enabled`.

**`split_block` variants of the same function are one logical hit.** A long function chunked into `split_block` pieces (e.g. `file.py:10-40:split_block:fn` and `file.py:41-80:split_block:fn`) should count as one unique chunk in Recall/Hit metrics. Normalize and deduplicate by stripping the line-range portion: `file.py:10-40:type:name` → `file.py:type:name`. As of v0.12.1, split_block nodes carry full `uses_type`/`imports` relationship edges extracted from the method signature — `find_connections` will return these edges.

**Call edges carry resolver provenance (v0.14.0+).** Every entry in `direct_callers` and `direct_callees` includes `resolver_source` (`"ast"` / `"pyan"` / `"libcst"` / `"lsp"`), `resolver_confidence` (0.5–0.98), and `confidence` tag (`"exact"` / `"recovered"` / `"ambiguous"`). Top-level `caller_confidence` / `callee_confidence` breakdowns show counts per tag. The confidence ladder (AST 0.5/0.7 → pyan 0.75 → LibCST 0.90 → LSP 0.98) means edges are upgraded in-place to the highest-confidence resolver — `resolver_source: "lsp"` means basedpyright confirmed the call. Configure via `call_graph.min_confidence` (drops low-confidence edges) and see `docs/CALL_GRAPH_TUNING.md` for tuning recipes.

**INCLUSION vs ORDERING — do not conflate (top-2 failure modes from GEPA eval).** Two rules that work together but are often confused:
- **INCLUSION:** include *every* relevant chunk you surfaced, regardless of `kind`. A `decorated_definition` config/dataclass (`SearchModeConfig`, `FileChanges`, etc.) that appeared in your results must appear in your answer if it is relevant to the question. The ordering rule below is about ORDER ONLY — it never justifies *dropping* a chunk you judged relevant.
- **ORDERING:** lead with the definition-level chunk (`class`/`method`/`function`) whose name most directly matches the question's core symbol. `split_block`, `module`, and `decorated_definition` chunks often score higher due to compactness, but they must not outrank the canonical definition. Put the canonical definition first; then include all remaining relevant chunks (including those fragments).

For **connection/relationship queries** (find_connections output): emit EVERY returned edge target in `relevant_chunk_ids`, even cross-file ones. The named symbol is the question's *subject*, usually **not** in the relevant set — do **not** lead with it. Lead with the connection targets `find_connections` returned (the actual callers / callees / subclasses), highest `resolver_confidence` first. Do not prune based on file location or kind.

**Community and module summary chunks are demoted to the tail on class-overview queries (v0.18.0+, `source_order_output=false` default).** They have IDs like `__community__/label:0-0:community:label` or `file.py:0-0:module:name`. Under the default ordering they appear at the end of the results array for non-GLOBAL queries — **don't mistake their low array position for low relevance; their reranker_score may be high.** If you need a summary chunk specifically, look at the tail of the result array, or filter with `chunk_type="community"` / `chunk_type="module"`. If `source_order_output=true` is set (DOS-RAG mode), they can still surface at rank-1 of their file group — use `chunk_type="function"` or `chunk_type="class"` to exclude them.

**Unicode symbols crash on Windows cp1252 terminals.** `✓`/`✗` cause `UnicodeEncodeError` in any script that writes to stdout in a cmd/PowerShell window without UTF-8. Use plain ASCII (`PASS`/`FAIL`) or run with `PYTHONUTF8=1`.

**Torch dynamo INFO logs spam stderr** when importing `search.hybrid_searcher`. Suppress with `2>nul` (Windows) or `2>/dev/null` (Linux/WSL).

---

## Pre-Flight: Verify Project Before Searching

**Mandatory when switching context or opening a new session:** before the first `search_code` call, confirm the active project matches the codebase you're working with:

```
code-search:get_index_status   # confirms active project path, chunk count, staleness
code-search:list_projects      # if unsure which project is active
code-search:switch_project     # if the active project is wrong
```

If returned chunk_ids have file paths that don't match the expected project, call `switch_project` **before trusting any results**. Ignoring a wrong active project is a common silent error — results look plausible but are from the wrong codebase.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **No results** | 1. Check active project: `code-search:list_projects` → `code-search:switch_project` if needed. 2. Verify index not empty/stale: `code-search:get_index_status`. 3. If index is missing or stale: **rebuild with `code-search:index_directory(path)`**. |
| **Bad results / wrong project** | Run pre-flight checks above. If the project was recently changed, re-run `switch_project` to confirm. |
| **Bad results (right project)** | Try different mode: hybrid → semantic → bm25. Add filters: `file_pattern`, `chunk_type`. Increase k |
| **Wrong result at rank-1** | Scan all k results — answer likely at rank 2-4. Use `chunk_type` filter to exclude module/community summary chunks |
| **Too slow** | Use `search_mode="bm25"` for exact symbols (fastest). Check: `code-search:get_memory_status`. Free: `code-search:cleanup_resources` |
| **Memory issues** | `code-search:cleanup_resources`. Switch to a lighter model: `code-search:switch_embedding_model("google/embeddinggemma-300m")` (~1.2GB, default) or `code-search:switch_embedding_model("Alibaba-NLP/gte-modernbert-base")` (0.28GB, lightest) |
| **find_similar_code use-case** | Use when you have a seed chunk_id and want to find structural/semantic near-duplicates: sibling method overrides, parallel implementations across language backends, or copied-with-variation functions. Call `search_code` first to get the seed chunk_id, then `find_similar_code(chunk_id=...)`. Returns top-N similar chunks ranked by embedding similarity. |

---

## Status Check

When the user invokes the skill with the argument `status` (e.g. `/mcp-search-tool status`), run this exact sequence and report the result:

1. `code-search:list_projects` — show which project is active, when it was last indexed
2. `code-search:get_index_status` — chunk count, staleness, graph data presence
3. `code-search:get_search_config_status` — current search_mode, BM25/dense weights, reranker state
4. `code-search:get_memory_status` — RAM/VRAM usage

Summarize in one short block: **active project**, **index staleness**, **active search mode**, **memory pressure**. Flag anything that looks off (no active project, stale index, missing graph data, >80% VRAM).
