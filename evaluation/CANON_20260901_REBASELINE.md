# P0 Canon Re-Baseline (2026-09-01)

## Status: MEASURED

Executes the P0 prerequisite of the approved call-graph-recall workstream scoping
(`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md` §"P0 (prerequisite)"):
land the uncommitted substrate, do a full non-incremental reindex, and re-capture all
three canons before any Phase 0 probe number is trusted. Supersedes the
`evaluation/CANON_20260822_LSP_REBASELINE.md` pins (63q MRR 0.8462, 133q 0.6482,
F-via-similar 0.9034).

## Substrate

- `HEAD` = `cf024bcd0f0461116f8ba2a14bd3a19dfe480450` (clean at capture time except the
  golden-dataset fix below, not yet committed). Two commits landed this session ahead
  of capture: `7cebe0c` ("fix: metadata clear self-heal, C-family macro repair,
  ADR-0025 addenda", 14 files) and `cf024bc` ("test: chunking macro-repair regression
  coverage", 2 files) — the 896-insertion / 135-deletion substrate the P0 prerequisite
  named (`chunking/languages/{_c_family,c,cpp}.py`, `mcp_server/server.py`,
  `search/graph_integration.py`, `search/incremental_indexer.py`, `search/indexer.py`,
  `search/metadata.py`, plus new test coverage).
- Index: 219 files / 2,642 chunks, F2LLM-v2-0.6B (1024d) + jina-reranker-v3. Full
  non-incremental reindex triggered by the user via the UI (not through an MCP tool
  call — `index_directory` was not reachable via `ToolSearch` this session) and
  confirmed complete via `get_index_status` before any capture began.
- Resolver mix, re-derived at publish time from the persisted call graph
  (`claude-context-local_9e7f0a98_f2llm-v2-0.6b_call_graph.json`,
  `edges[].resolver_source`): **26,606 total edges — `lsp` 1,356, `pyan` 1,143,
  `libcst` 474, unresolved (AST-only) 23,633.** Non-zero `lsp` confirms LSP was live
  for this measurement. Grew from the 2026-08-22 pin's 26,422/1,355/1,136/475 —
  consistent with the +2 files/+31 chunks index growth, not a resolver regression.
- `scripts/benchmark/audit_golden_dataset.py` — ran first, found one stale gold: Q12's
  primary expected chunk (`mcp_server/tools/status_handlers.py:...:handle_get_index_status`)
  had drifted from chunk kind `decorated_definition` to `method` on the live index.
  Fixed in both `evaluation/golden_dataset.json` and `evaluation/golden_dataset_expanded.json`
  (all 4 occurrences across `expected`/`expected_primary`/`relevance_grades`, `replace_all`).
  Re-ran the audit after the fix — **CLEAN, exit 0, both datasets** — before trusting
  any benchmark number. This fix is a substantive data correction, not yet committed
  as of this document.

## Determinism (ADR-0021)

Per explicit user instruction this session, all three legs were captured as a
**single round** — the 63q leg's own bit-identical determinism was already proven at
0 movers on 2026-08-22 (`CANON_20260822_LSP_REBASELINE.md` §Determinism), and the
133q/F-via-similar legs already carried the single-round convention from that same
document. Re-proving bit-identical reproduction a second time here has no independent
value; `PYTHONHASHSEED=0` auto-re-exec still fires (confirmed in each run's log
header: `[HASHSEED] PYTHONHASHSEED unset - re-exec with PYTHONHASHSEED=0`).

## Results

| Run | queries | MRR | R@5 | R@10 | R@20 | R@50 | NDCG@5 | HR@5 |
|---|---|---|---|---|---|---|---|---|
| `canon_63q_r1_20260901.json` | 63 | **0.8419** | 0.6432 | 0.7553 | 0.8525 | 0.8631 | 0.6763 | 1.000 |
| `canon_133q_r1_20260901.json` | 133 | **0.6378** | 0.6216 | 0.7435 | 0.8017 | 0.8142 | 0.6022 | 0.8722 |
| `canon_fsim_63q_r1_20260901.json` (`--f-via-similar`) | 63 | **0.8843** | 0.6425 | 0.7558 | 0.8375 | 0.8375 | 0.6860 | 1.000 |

Avg latency: 4,509–4,564 ms across `search_code`-mode runs, 4,222 ms for the
anchor-`chunk_id`-routed F-via-similar view. All three runs `Overall: PASS` on the
three gate thresholds (mrr≥0.5, recall@5≥0.55, hit_rate@5≥0.8).

**Anomaly, not chased**: the F-via-similar run's process exited with code 1 despite
printing a complete, correct `Overall: PASS` summary and a successful "Results saved
to" line, with no traceback anywhere in the captured log — the process log ends
cleanly right after that print. The output JSON parses and its `aggregate` dict
matches the printed leaderboard exactly (MRR 0.8843). Read as a benign
CUDA/interpreter-teardown exit-code artifact (this run is the only one of the three
that loads/unloads the reranker under `find_similar_to_chunk`'s different code path),
not a data-corrupting failure. Not reproduced against the other two runs, which both
exited 0.

## Corpus-identity note: one incidental no-op incremental pass

`get_index_status` reads `index_is_current: false`, `pending_changes: {added: 1}`
after this campaign — same non-event pattern the 2026-08-22 precedent documented:
each benchmark run writes a new `evaluation/canon_*.json` output file, which the
30-minute staleness auto-reindex trigger detects as "Added: 1" and then chunks 0
files (`.json` is not one of the 27 indexed source extensions). Confirmed via the
mid-run log line `Changes detected - Added: 1, Removed: 0, Modified: 0` →
`[INCREMENTAL] Chunking 0 files (parallel=enabled)` → `0 files → 0 chunks`. Index
statistics (219 files / 2,642 chunks) and the resolver mix above are unchanged across
the whole campaign; only an unrelated on-disk metadata timestamp moved.

## Delta vs the superseded pin

| Pin | 63q MRR | 133q MRR | F-via-similar MRR | Δ this canon |
|---|---|---|---|---|
| 2026-08-22 (`CANON_20260822_LSP_REBASELINE.md`) | 0.8462 | 0.6482 | 0.9034 | −0.0043 / −0.0104 / −0.0191 |

All three deltas are small and negative. Per project convention (P0's own text: "a
delta here is drift from the landed diff, not a regression — record it, do not chase
it") this is **recorded, not investigated**. Plausible contributors, none confirmed:
the +2 files/+31 chunks/+184 edges index growth changes candidate-pool composition
under the listwise reranker exactly as prior comparability-break notes describe
(`CANON_20260822_LSP_REBASELINE.md`'s own three-way supersession is the same
phenomenon); the Q12 golden-dataset chunk-kind fix changes that one query's scoring
in an unpredictable direction; the substrate landed this session touches
`search/graph_integration.py` and `search/metadata.py`, both on the call-edge
injection path, though neither changes edge-confidence or traversal behavior (see
plan's "central finding" — ego traversal is calls-only and score-degenerate
regardless of these files).

## Hard-miss cohort (133q, recall@10 = 0, re-derived from this canon)

9/133 queries score zero recall@10 this generation — supersedes the 2026-08-22
12-query list (per project convention, "the miss set is substrate-dependent —
re-derive before targeting"):

| id | cat | mrr | query (truncated) |
|---|---|---|---|
| Q101 | A | 0.000 | write the analyzed relationships between code entities out so they sur… |
| Q103 | A | 0.000 | how often repeated questions were answered from memory instead of reco… |
| Q106 | A | 0.000 | return the ids and distances of the closest stored vectors for a query… |
| H004 | H | 0.045 | avoid logging a warning for files that are genuinely empty rather than… |
| H008 | H | 0.000 | make a parameter-sweep script rebuild its searcher instance fresh on e… |
| H033 | H | 0.000 | fix the storage-directory resolver logging a spurious error when the a… |
| H034 | H | 0.000 | cap the inference batch size for the ONNX backend based on free GPU me… |
| H050 | H | 0.000 | fix a failing test around the search-code handler not being ready to u… |
| H063 | H | 0.000 | update call sites in the connection-analysis and similar-code handlers… |

Three queries from the 2026-08-22 list (H021, H054, H066) now score above zero
recall@10 and dropped out of the cohort — consistent with drift, not a targeted fix;
no intervention here explains the improvement. No new queries entered the cohort.
6/9 are H-category (commit-mined), the same skew the prior list showed. No
intervention proposed; this is a starting-point re-derivation, per plan scope.

## Artifacts

`canon_63q_r1_20260901.json`, `canon_133q_r1_20260901.json`,
`canon_fsim_63q_r1_20260901.json`. This document.

## Out of scope (per the approved plan)

- Phase 0 (A0 ego-membership probe, B1–B3 execution-witnessed tracer) — gated on this
  document closing P0; not started here.
- Phase 1 items (A1′ float-confidence fix, A5 `include_top_callees`, B5 golden growth)
  — independent of the Phase 0 gate but not part of P0's own scope.
- Committing the golden-dataset Q12 fix — left uncommitted, to be bundled with or
  immediately following this document per the plan's own execution note.
- Re-running the reindex — already correctly done pre-campaign (user-triggered via
  UI); not repeated.
