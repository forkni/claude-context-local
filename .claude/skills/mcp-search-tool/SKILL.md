---
name: mcp-search-tool
description: "Guides semantic code search via the code-search MCP server. Use when searching for code definitions, callers, callees, dependencies, or tracing code flow in indexed projects — also when switching between indexed projects, verifying which project is active, or checking whether an index is stale before trusting results. Provides correct workflows for search_code, find_connections, find_path, find_similar_code, switch_project, index_directory. Invoke /mcp-search-tool status to run a health check."
user-invocable: true
argument-hint: "search query or 'status' for index health"
# allowed-tools lists all 18 (10 core + 8 advanced: clear_index, delete_project,
# configure_search_mode, get_search_config_status, configure_reranking, configure_chunking,
# list_embedding_models, switch_embedding_model). Granting permission here does NOT make the
# 8 advanced tools dispatchable — they must also be listed by the server's list_tools, which
# requires MCP_EXPOSE_ADVANCED_TOOLS=1 on the server process + reconnect. See "Tool Tiers" below.
allowed-tools: "Bash, Read, Grep, code-search:search_code, code-search:find_connections, code-search:find_path, code-search:find_similar_code, code-search:index_directory, code-search:list_projects, code-search:switch_project, code-search:get_index_status, code-search:clear_index, code-search:delete_project, code-search:configure_search_mode, code-search:get_search_config_status, code-search:configure_reranking, code-search:configure_chunking, code-search:list_embedding_models, code-search:switch_embedding_model, code-search:get_memory_status, code-search:cleanup_resources"
metadata:
  version: 0.25.0
  mcp-server: code-search
---

# MCP Search Tool Skill

## On Activation

**IMPORTANT**: This skill provides BEHAVIORAL INSTRUCTIONS, not information to analyze.

**When this skill loads**:

1. Acknowledge: "MCP Search skill active. Results are ranked candidates — I'll scan all results, not just rank-1."
2. Wait for the user's actual task
3. Apply the guidance below to all subsequent code search operations

**DO NOT**: Explore or analyze this skill document, launch agents to investigate the skill, or treat this as a request for information about MCP
tools.

---

## Purpose

Ensures all MCP semantic search operations follow correct workflows for accurate results. The key behavioral rule: **search results are ranked
candidates, not definitive answers — always scan all returned results.**

**`docs/BENCHMARKS.md` is the single source of truth for benchmark numbers.** This skill states the current headline once, here, and does not
duplicate figures elsewhere — every other reference file in this skill points back to `docs/BENCHMARKS.md` instead of restating numbers that will
drift out of date on the next benchmark run.

**Current headline (2026-08-22 close-out §4 LSP re-baseline, canonical 63-query set, hybrid, k=10, intent-on, deterministic PYTHONHASHSEED=0):** MRR
**0.8462**, Recall@5 0.6562, Recall@10 0.7618, NDCG@5 0.6854, pool_hit_rate 1.0000 (r1==r2 bit-identical — zero run-to-run flap on the deterministic
harness). Expanded 133-query set: MRR 0.6482. Provenance: `evaluation/CANON_20260822_LSP_REBASELINE.md`.
The dataset has been repaired and expanded multiple times since earlier benchmark runs (comparability breaks are
logged in `docs/BENCHMARKS.md`) — do not compare an older cached number here against a fresh run without checking both the dataset size/date and the
config it ran under. Engine default is `k=7`; pass it explicitly when correctness matters. Use `k=10` for architectural/global queries.

**Note:** `evaluation/golden_dataset.json`'s own `_meta.current_metrics` block still cites a 2026-06-26 DSPy agent eval. That subsystem was removed
wholesale in v0.23.0 (ADR-0016) — treat that block as stale metadata, not a current benchmark status; `docs/BENCHMARKS.md` is current.

---

## Critical: Results Are Candidates, Not Answers

MCP search returns **ranked candidates**, not definitive answers. On the canonical benchmark set MRR is well under 1.0 (see the headline above) — the
correct result is **not always ranked first**, and this is not a general reliability guarantee for arbitrary queries or codebases. Pool-hit
instrumentation makes the scan-all-k rule concrete: on the canonical set essentially every gold chunk reaches the pre-rerank candidate pool
(pool_hit_rate ≈ 0.90–1.0 depending on the run), so most benchmark misses are *ordering* misses — the right answer can legitimately sit at rank 5–7
of an otherwise-correct result set, not just missing outright.

**Baseline rule:** **pass `k=7` explicitly when correctness matters.** The `search_code` tool schema publishes no `default` for `k` at all
(`mcp_server/tool_registry.py`) — only `minimum: 1`/`maximum: 100` (the invariant ceiling of `SearchModeConfig.max_k`, itself a separate per-install
value, not the bound's own number). The handler falls back to `search_config.search_mode.default_k` whenever `k` is omitted — both the shipped
`search_config.json.example` and this deployment's config set that to **7**, which is what makes `k=7` the effective default in practice. Pass it
explicitly regardless: an MCP client isn't guaranteed to omit the field the same way in every context, and targets may still rank 6–7 on complex or
multi-target queries. Use `k=10` for architectural / global queries.

**Result Interpretation Workflow:**

1. Call `code-search:search_code(query="<your query>", k=7)`. Multi-hop and graph-hop expansion of the initial hits run **always-on and unconditionally**.
   Ego-graph expansion runs **by default** (`EgoGraphConfig.enabled=True`) but is a genuine tri-state gate via `ego_graph_enabled`: omit it to defer to
   the server's configured default (on, in this deployment), pass `true` to force it on and apply the `ego_graph_k_hops`/
   `ego_graph_max_neighbors_per_hop` overrides, or pass `false` to force it off for that call (see Gotchas) — so expect `source: "ego_graph"` rows in
   every result set unless you explicitly disable it. `include_context` has **no effect on the default `HybridSearcher` search path**
   (`SearchOrchestrator._search` in `mcp_server/tools/search_orchestrator.py` only threads it through for a non-default searcher) — don't rely on it.
   Use `k=10` for architectural / global queries.
2. **Scan ALL k results** — results are pre-sorted in relevance order (centrality-reranked blended_score descending) under the server default;
   module summary chunks appear at the tail for non-GLOBAL queries. Array position 0 is the highest blended_score result. The tool returns
   **metadata rows** (`chunk_id`, `kind`, `name`, scores) — no code body. Names + kinds + scores are enough to judge relevance — you do NOT need to
   refetch bodies to "confirm". You may optionally re-sort by `reranker_score` for pure cross-encoder order, but doing so will **re-promote demoted
   summary chunks** (see Gotchas).
3. **Issue a second search with alternate phrasings** only when the question is genuinely ambiguous about *which subsystem* should answer it — a
   **bare** generic-operation verb with no domain qualifier (e.g. "validate the input", "save the data", "load config") could plausibly map to
   unrelated implementations in several files, and that ambiguity is worth resolving with 2–3 diverse queries (synonyms, subsystem names, related
   symbol names). **Do NOT** escalate just because one of those verbs (validate/normalize/encode/decode/load/save/id-handling) appears in the query —
   if the query already names a specific domain object that pins the subsystem down (e.g. "validate **JWT token**", "encode a **chunk_id**", "save the
   **index config**"), a single search is enough; see "When rank-1 is most reliable" below. Separately, also issue a second search when the first
   result set is concentrated in one module but the concept plausibly also exists in a sibling file. Do not pad an already-narrow, domain-qualified
   query with an unneeded second call.
4. **Identify the best match** based on your actual need.  For MRR / lead-chunk ranking, prefer the canonical `class` or `method`/`function` chunk
   whose name most directly matches the question — never a `split_block`, `module`, or `decorated_definition` fragment (even if it scores slightly
   higher; see Gotchas).
5. If the best match is a module/summary chunk but you need specific code, look at lower-ranked results or filter with `chunk_type="function"` /
   `chunk_type="class"`.
6. Use `chunk_id` from the best match for follow-up tools.

**When rank-1 is most reliable:** small function discovery with a domain-qualified object ("get the user session", "validate **JWT token**"), exact
symbol lookup via `chunk_id`

**When you MUST scan all results:** class overview queries, sibling context ("encode and decode"), bare/unqualified generic-operation queries
("validate the input"), queries where the answer may rank 5–7

---

## Prerequisites

- MCP server running and connected in Claude Code (`/mcp` → Reconnect next to `code-search`)
- At least one project indexed: `code-search:index_directory(directory_path="<your-project>")`

---

## Quick Start: Which Tool?

> **Note on snippet style:** the arrow-diagram and examples below are pseudocode, not executable Python. MCP tool arguments are JSON-shaped —
> booleans are written `true`/`false` (not `True`/`False`), and every argument is named. Pass the values to your MCP client as native parameters
> rather than copy-pasting the text.

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
├─ "Understand concept/feature" ─────► code-search:search_code(query="<your query>", k=7)  [auto mode]
├─ "Architectural / global query" ───► code-search:search_code(query="<your query>", k=10)
├─ "Expand via call graph neighbors"─► code-search:search_code(..., ego_graph_enabled=true, ego_graph_k_hops=2)
│
└─ "Validate line numbers only" ─────► Grep (LAST RESORT)
```

**`find_path` — pass `max_hops=20` on the first call.** The tool's default `max_hops` is only 10 (range 1–20). A real path longer than 10 hops returns
`path_found:false` with a hint to retry at a higher `max_hops`, which costs an extra call to reach the same answer. A bidirectional-BFS call at
`max_hops=20` costs the same as one at the default — there's no accuracy or safety trade-off, just a wasted round trip if you start low. Set it to 20
explicitly whenever you already have both `source_chunk_id` and `target_chunk_id` and want a definitive answer in one call. Narrow it below 20 only
when you deliberately want to test for a *short* connection (e.g. "are these directly related?") and a `path_found:false` at low `max_hops` is itself
the useful signal.

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

## Tool Tiers: 10 Core (Listed) + 8 Advanced (Hidden by Default)

By default the server's `list_tools` advertises only the **10 core tools** below (tool-count budget, MCP Architecture-Patterns §VI-C). Set
`MCP_EXPOSE_ADVANCED_TOOLS=1` on the server process and reconnect (`/mcp` → Reconnect) to also *list* the 8 advanced tools (`clear_index`,
`delete_project`, `configure_search_mode`, `get_search_config_status`, `configure_reranking`, `configure_chunking`, `list_embedding_models`,
`switch_embedding_model`).

**An unlisted tool cannot be called — do not assume otherwise.** If a task's "natural" tool is one of the 8 advanced tools and it is not currently
listed:

1. **Check for an in-band alternative first** — only `configure_search_mode` has one:
`search_code(search_mode="bm25"|"semantic"|"hybrid"|"auto")` sets the mode for that call without needing the advanced tool at all.
2. **If no in-band alternative exists**, tell the user the tool is unlisted and ask them to set
`MCP_EXPOSE_ADVANCED_TOOLS=1` on the server process and reconnect (`/mcp` → Reconnect) — note this accepts the larger tool-surface accuracy cost the
10-tool default exists to avoid.
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

Full purpose + in-band-alternative table for the 8 advanced tools (only `configure_search_mode` has one — see step 1 above):
[references/tool-index.md](references/tool-index.md) Full parameter reference for essential tools (search_code, find_connections, find_path):
[references/parameters.md](references/parameters.md) Advanced features (multi-hop, intent routing, summaries):
[references/advanced-features.md](references/advanced-features.md) Benchmark data & mode selection guide:
[references/performance.md](references/performance.md)

---

## Gotchas

These are non-obvious traps from real session experience — not things the docs mention.

| Gotcha | What to do |
|---|---|
| Results are pre-sorted by `blended_score` descending under the server default (`source_order_output=false`, v0.18.0+); module summaries are demoted to the tail for non-GLOBAL queries | Array position 0 is already the best default-order match. For strict cross-encoder order instead, re-sort by `reranker_score` then `blended_score`: `sorted(results, key=lambda r: (r.get("reranker_score", 0), r.get("blended_score", 0)), reverse=True)`. **Caveat:** this re-promotes demoted summary chunks (e.g. a `module:hybrid_searcher` summary with `reranker_score=0.94` moves from position 28 to position 0) — apply it only when you specifically want pure cross-encoder ranking |
| `search_code` returns metadata only — `file`, `lines`, `kind`, `score`, `chunk_id`, usually `name` — never a code body (full field list: [references/parameters.md](references/parameters.md)) | Don't spend extra calls "confirming" a candidate's body; names, kinds, and scores are sufficient to judge relevance |
| **Ego-graph expansion is on by default, but `ego_graph_enabled` is a real tri-state gate, not a widen-only knob.** `EgoGraphConfig.enabled` defaults to `True` in the dataclass (`search/config.py`). `search/effective_config.py`'s `build_effective_config()` reads the tool argument as tri-state: omitted (`None`) defers to that server default; explicit `true` forces expansion on *and* applies the `ego_graph_k_hops`/`ego_graph_max_neighbors_per_hop` overrides; explicit `false` sets `EgoGraphConfig.enabled=False` for that call (logs `"[EGO_GRAPH] Explicitly disabled"`) and leaves the hop-count args untouched. The schema itself publishes no `default` for this argument (only the description tells you to omit it to get the server's configured value) | Expect `source="ego_graph"` rows interleaved into every result set unless you pass `ego_graph_enabled=false` to suppress them for that call. When they're present, count them toward your top-k window, don't filter them out |
| `k` is not the result count — multi-hop/graph-hop/ego-graph expansion adds rows *after* `k` is applied to the initial retrieval. Measured on the live index, same query: `k=1` → 4 results, `k=5` → 20, `k` omitted (effective 7) → 26 | Don't size a context budget off `k` directly — expect roughly 3–5× more rows back than `k`. Total rows are capped at `k × graph_enhanced.max_results_multiplier` (default 8) |
| `find_connections`'s `relationship_types` filter only scopes *some* response sections — `direct_callers`, `indirect_callers`, `direct_callees`, and `similar_code` come back unfiltered no matter what you pass; only sections like `uses_types`/`exceptions_caught`/`instantiates` are actually narrowed by it | Don't rely on `relationship_types` to prune caller/callee lists — filter those client-side by their own `resolver_source`/edge-type fields instead |
| `split_block` pieces of one long function (e.g. `file.py:10-40:split_block:fn` + `file.py:41-80:split_block:fn`) are one logical hit | Normalize/dedupe by stripping the line range (`file.py:10-40:type:name` → `file.py:type:name`) before counting unique chunks in Recall/Hit metrics. Since v0.12.1 they also carry full `uses_type`/`imports` edges, so `find_connections` returns these too |
| Call edges carry resolver provenance (v0.14.0+): `resolver_source` (`"ast"`/`"pyan"`/`"libcst"`/`"lsp"`), `resolver_confidence` (0.5–0.98), `confidence` tag (`"exact"`/`"recovered"`/`"ambiguous"`) | Higher-confidence resolvers upgrade edges in place — `resolver_source: "lsp"` means basedpyright confirmed the call. Tune via `call_graph.min_confidence`; see `docs/CALL_GRAPH_TUNING.md` |
| INCLUSION vs ORDERING are separate rules, often conflated (top-2 GEPA-eval failure modes, historical — subsystem removed, ADR-0016) | **INCLUSION:** every relevant chunk you surfaced must appear in your answer regardless of `kind` — ordering never justifies *dropping* one. **ORDERING:** lead with the definition-level chunk (`class`/`method`/`function`) whose name matches the question, even if a `split_block`/`module`/`decorated_definition` fragment scored higher; then include the rest |
| For `find_connections` output, the symbol you searched for is the question's *subject*, usually not itself part of the relevant set | Lead with the actual connection targets (callers/callees/subclasses) it returned, highest `resolver_confidence` first — emit every returned edge target, even cross-file ones; don't prune by file location or kind |
| Module summary chunks (`file.py:0-0:module:name`) are demoted to the tail on class-overview queries under the default ordering | Low array position ≠ low relevance — their `reranker_score` may be high. Filter with `chunk_type="module"` to find them directly, or `chunk_type="function"`/`"class"` to exclude them (also needed under `source_order_output=true`, where they can surface at rank-1 of their file group) |
| Unicode `✓`/`✗` crash on Windows cp1252 terminals (`UnicodeEncodeError`) | Use plain ASCII (`PASS`/`FAIL`) or run with `PYTHONUTF8=1` |
| Torch dynamo INFO logs spam stderr when importing `search.hybrid_searcher` | Suppress with `2>nul` (Windows) or `2>/dev/null` (Linux/WSL) |

---

## Pre-Flight: Verify Project Before Searching

**Mandatory when switching context or opening a new session:** before the first `search_code` call, confirm the active project matches the codebase
you're working with:

```
code-search:get_index_status   # confirms active project path, chunk count, index_is_current
code-search:list_projects      # if unsure which project is active
code-search:switch_project     # if the active project is wrong
```

If returned chunk_ids have file paths that don't match the expected project, call `switch_project` **before trusting any results**. Ignoring a wrong
active project is a common silent error — results look plausible but are from the wrong codebase.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **No results** | 1. Check active project: `code-search:list_projects` → `code-search:switch_project` if needed. 2. Verify index not empty/stale: `code-search:get_index_status`. 3. If index is missing or stale: **rebuild with `code-search:index_directory(directory_path)`**. |
| **Judging whether a project's index is stale** | Use `last_indexed_at` from `code-search:list_projects` (or `last_indexed_time` from `get_index_status` for the active project) — both read live Merkle snapshot data that advances on every re-index, incremental or full. **Never** judge staleness from `list_projects`' `created_at` — that field is frozen at first-index registration and never updates on later re-indexing, so a freshly-rebuilt project can still show a `created_at` from days or weeks ago. |
| **Bad results / wrong project** | Run pre-flight checks above. If the project was recently changed, re-run `switch_project` to confirm. |
| **Bad results (right project)** | Try different mode: hybrid → semantic → bm25. Add filters: `file_pattern`, `chunk_type`. Increase k |
| **Wrong result at rank-1** | Scan all k results — answer likely at rank 2-4. Use `chunk_type` filter to exclude module summary chunks |
| **Too slow** | Use `search_mode="bm25"` for exact symbols (fastest). Check: `code-search:get_memory_status`. Free: `code-search:cleanup_resources` |
| **Memory issues** | 1. `code-search:cleanup_resources` (core, always listed) — free indexes/models/GPU memory first. 2. For a lasting fix, switch to the lightest of the 4 registered embedding models (`BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`, `codefuse-ai/F2LLM-v2-0.6B`, `google/embeddinggemma-300m` — this machine's locally deployed default is `codefuse-ai/F2LLM-v2-0.6B` per `search_config.json`): `code-search:switch_embedding_model("google/embeddinggemma-300m")` (~1.2GB, lightest) — **advanced tool, unlisted by default**; requires `MCP_EXPOSE_ADVANCED_TOOLS=1` + reconnect (see "Tool Tiers" below) |
| **find_similar_code use-case** | Use when you have a seed chunk_id and want to find structural/semantic near-duplicates: sibling method overrides, parallel implementations across language backends, or copied-with-variation functions. Call `search_code` first to get the seed chunk_id, then `find_similar_code(chunk_id=...)`. Returns top-N similar chunks ranked by embedding similarity. Pass `exclude_same_file=true` when you specifically want cross-file matches (e.g. parallel implementations in sibling files) — default is byte-identical results including same-file neighbors. |

---

## Status Check

When the user invokes the skill with the argument `status` (e.g. `/mcp-search-tool status`), run this exact sequence and report the result:

1. `code-search:list_projects(check_freshness=True)` — show which project is active, and each indexed model's definitive freshness via
   `index_is_current`/`pending_changes` (a content-only Merkle diff against the working tree). Do **not** read `created_at` or `last_indexed_at`
   for staleness — both only say *when* the indexer last ran, not whether the index still matches the tree; `created_at` is additionally frozen
   at first-index registration and never advances on re-index at all.
2. `code-search:get_index_status` — chunk count, `index_is_current`/`pending_changes` (active project only, same definitive check), graph data
   presence
3. `code-search:get_search_config_status` — current search_mode, BM25/dense weights, reranker state. **This is an advanced tool with no in-band
   alternative — it is unlisted unless `MCP_EXPOSE_ADVANCED_TOOLS=1` is set (see "Tool Tiers" below).** If it isn't listed, do NOT fail the whole
   status check: skip this step, report "search mode/reranker state: unavailable under the 10-tool default (set `MCP_EXPOSE_ADVANCED_TOOLS=1` and
   reconnect to include it)", and continue to step 4.
4. `code-search:get_memory_status` — RAM/VRAM usage

Summarize in one short block: **active project**, **index staleness**, **active search mode** (or "unavailable" per step 3), **memory pressure**. Flag
anything that looks off (no active project, stale index, missing graph data, >80% VRAM).
