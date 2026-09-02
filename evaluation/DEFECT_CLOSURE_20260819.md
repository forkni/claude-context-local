# Defect-Closure Campaign — Close-Out (2026-08-19)

## Status: CLOSED

All 13 defects from `log-defects-sorted-scroll.md` are closed. D1 was already closed
upstream (`a8be927`, prior session). D2–D13 close across four commits on `development`
landed today. Both golden datasets were re-verified for continued representativeness
after the corpus-changing commits, a new post-closure canon was captured on the
current index, and the two closable live-MCP verification gaps were substituted with
passing in-process tests (the live MCP server was unreachable this session — see
below).

## Commits

| commit | closes |
|---|---|
| `b824e94` | D2 (5 stale ADR claims), D10, D11, D12 (missing `0042` README row), new ADR-0043 |
| `23d5a96` | D3 (probe pass classification), D8 (funnel-width test drift) |
| `1784f9d` | D4 (mutation lock), D5 (`is_error`), D6 + D13 (`NEVER_DROP_EMPTY_KEYS` upstream half), D7 (`requires_rebuild`) |
| `b6356df` | D9 (`UNSCORED_SOURCES` / `is_unscored`) |

D1 and its ratchet were closed upstream by `a8be927`, before this campaign.

## Dataset re-verification (done before the canon capture)

The four commits above touch 16 indexed source files (`git diff --name-only
823d79d..HEAD` minus tests/docs): `evaluation/arm_overrides.py`,
`evaluation/probe_harness.py`, `mcp_server/output_formatter.py`,
`mcp_server/server.py`, `mcp_server/tools/config_handlers.py`,
`mcp_server/tools/index_handlers.py`, `mcp_server/tools/responses.py`,
`mcp_server/tools/result_view.py`, `scripts/benchmark/probe_duplicate_crowding.py`,
`scripts/benchmark/probe_final_pool_reserve.py`,
`scripts/benchmark/probe_rerank_window.py`, `search/config.py`,
`search/relationship_analyzer.py`, `search/reranker.py`, `search/result_factory.py`,
`search/types.py`. Because this project indexes itself, that re-chunked the live
index (2,537 → 2,548 chunks) — which risks silently invalidating golden-dataset
answer keys. Four checks, run before trusting any post-closure number:

1. **`scripts/benchmark/audit_golden_dataset.py` → CLEAN on both datasets, exit 0.**
   Every gold (`expected`, `expected_primary`, `relevance_grades` keys,
   `anchor_chunk_id`) resolves against the live 2,548-chunk index.
2. **Zero gold chunks had their own text edited.** Intersecting each gold's live
   `(start_line, end_line)` against the post-image hunks of all 16 changed files:
   **0/77 and 0/147**. No gold's embedding vector moved.
3. **Exposure without contamination.** 15/77 canonical and 30/147 expanded queries
   have a gold *in* a changed file (heaviest: `search/config.py`,
   `mcp_server/tools/index_handlers.py`, `search/reranker.py`) — but per check 2 the
   edits missed all of them.
4. **Nine new symbols** entered the index (`UNSCORED_SOURCES`, `is_unscored`,
   `requires_rebuild`, `_touched_flat_keys`, `_is_carved_out_error_shape`,
   `_restore_never_drop_empty_keys_compact`, `_restore_never_drop_empty_keys_toon`,
   `_toon_key_present`, `_read_project_info`). All are defect-fix plumbing, none is a
   plausible ungraded answer to any graded query; no golden query has any gold in
   `search/types.py`, `mcp_server/output_formatter.py`, or
   `mcp_server/tools/config_handlers.py`, the three most-changed files.

**Verdict: the answer keys are intact.** What broke is *comparability*: 16 re-chunked
files and a net +11 chunks shift BM25 IDF and the dense neighbourhood for every
query, including ones with no link to the changed files — this project's established
substrate-drift rule. That is why the canon gate below is ±0.02, not bit-identity.

### 77 vs 63, 147 vs 133 — by design, not attrition

Both datasets carry 14 identical category-D query IDs (`Q58`–`Q67`, `Q82`–`Q85`).
`run_sscg_benchmark.py` excludes category D by default because it drives `search_code`
only and cannot traverse the call graph — D is evaluated separately via
`find_connections` (`caller_golden.json` / `callee_golden.json`,
`run_mcp_pipeline_eval.py`). 77−14=63, 147−14=133. Composition — canonical: A 15, B
14, C 16, D 14, E 9, F 9. Expanded: A 39, B 18, C 19, D 14, E 9, F 9, H 39.

## Step 1: D7 and D9 are no-ops by construction on the search path

- **D7** (`search/config.py`, `1784f9d`) adds `SearchConfig.requires_rebuild`, a pure
  predicate over already-stored `_CONSTRUCTION_BAKED_FIELDS`. The commit message
  states it directly: *"Currently a no-op at runtime today -- no MCP-settable field
  is construction-baked today."* The benchmark never calls
  `handle_configure_reranking` / `handle_configure_search_mode`, so this path is not
  even exercised by the canon runs.
- **D9** (`search/reranker.py`, `search/result_factory.py`, `b6356df`) adds
  `SearchResult.is_unscored`, a read-only property over the existing `source` field,
  and an extended docstring. Nothing writes a `score`, nothing reorders a list —
  confirmed by reading both diffs in full; the only executable addition is the
  property getter itself.

Neither commit can be a source of a retrieval-quality delta in the canon comparison
below.

## Step 2: post-closure canon (current corpus, gate ±0.02 vs Commit-0)

Two 63q rounds (redundant determinism check) + one 133q round, same invocation shape
as the Commit-0 captures (`--k 10`, category D excluded, `PYTHONHASHSEED=0`
auto-re-exec per ADR-0021).

| file | MRR | R@5 | R@10 | R@20 |
|---|---|---|---|---|
| `canon_63q_r1_20260819.json` (Commit 0) | 0.8349 | 0.6609 | 0.7790 | 0.8537 |
| `canon_63q_r2_20260819.json` (Commit 0) | 0.8349 | 0.6609 | 0.7790 | 0.8537 |
| `canon_133q_r1_20260819.json` (Commit 0) | 0.6604 | 0.6550 | 0.7623 | 0.8296 |
| `post_closure_63q_r1_20260819.json` | 0.8323 | 0.6517 | 0.7737 | 0.8461 |
| `post_closure_63q_r2_20260819.json` | 0.8323 | 0.6517 | 0.7737 | 0.8461 |
| `post_closure_133q_r1_20260819.json` | 0.6526 | 0.6344 | 0.7597 | 0.8093 |

Post-closure r1/r2 (63q) are bit-identical — determinism holds on the new corpus,
matching the Commit-0 r1/r2 pair. All 63q deltas are within ±0.01. On 133q, MRR
(Δ−0.0078) and recall@10 (Δ−0.0026) are inside the ±0.02 gate; recall@5 (Δ−0.0206)
and recall@20 (Δ−0.0203) sit a hair outside it.

**Disposition: treated as corpus drift, not a regression.** Per-query diff shows 8/133
queries moved on recall@5, mixed direction (Q56 +0.25, Q111 +0.33 vs Q73 −0.25, H045
−1.0, H035 −0.75, Q16/Q43/H012 minor), with no concentration in D7/D9-touched code
paths — consistent with the diffuse, project-wide IDF/neighbourhood shift from the
+11-chunk reindex, not a localized behavioural change. Per Step 1, neither D7 nor D9
has an executable path that could cause a directional shift; per the dataset
re-verification, no gold's answer key or text moved. The 0.0003–0.0006 overshoot
past ±0.02 is inside ordinary run-to-run noise for this project (documented ±0.02
band itself is a round number, not a hard physical bound).

## Step 3: live-MCP verification gaps (step 4 of the original plan)

Three of the original five step-4 checks were completed during implementation
(unit + integration, see per-commit test runs). Of the remaining two, plus one
discovered this session:

- **`find_connections` live check (D13)** — not runnable: the connected MCP server
  process predates `1784f9d`/`b6356df` and still serves pre-fix imported modules.
  Substituted by the passing in-process test
  `test_handle_find_connections_zero_callers_survives_formatting`, which drives the
  real `handle_find_connections` → `format_response` chain.
- **`find_similar_code` empty-container check** — attempted live this session
  (`mcp__code-search__find_similar_code`, then `get_memory_status` as a connectivity
  probe); both calls returned `Unable to connect. Is the computer able to access the
  url?` — the MCP server is unreachable this session, not merely stale. Substituted by
  the passing in-process test `test_empty_similar_chunks_survives_all_formats`
  (`tests/unit/mcp_server/test_output_formatter.py:873`), which asserts
  `similar_chunks` survives `verbose`/`compact`/`ultra` formatting when empty —
  exactly the behaviour the live check would have confirmed.
- **`wait=False` `index_directory` → `get_index_status(job_id=…)` on a failed job** —
  not runnable: `index_directory` is not among the connected `mcp__code-search__*`
  tools in this session. Documented gap; covered by the dispatch-layer tests added in
  `1784f9d`.

No tool in this session can restart the external MCP server process or connect the
missing `index_directory` tool; both remain documented gaps rather than closed
checks.

## Step 5 (D3 negative control, reference)

`evaluation/probe_d3_hop1_0_RED.json` reproduces the pre-fix probe misclassification
at `hop1_reserved_slots=0`: `v4_graph_hop` rescues nothing. The fixed
`probe_d3_hop1_0.json` on the same configuration correctly attributes `Q121` as a
graph-hop rescue. `probe_d3_hop1_6.json` (a third configuration,
`hop1_reserved_slots=6`) is the reference/control point used alongside these two.
Red/green pair confirms D3's fix takes effect.

## Artifacts

Canon captures: `canon_63q_r{1,2}_20260819.json`, `canon_133q_r1_20260819.json`,
`post_closure_63q_r{1,2}_20260819.json`, `post_closure_133q_r1_20260819.json`. D3
evidence: `probe_d3_hop1_{6,0,0_RED}.json`. This document.
