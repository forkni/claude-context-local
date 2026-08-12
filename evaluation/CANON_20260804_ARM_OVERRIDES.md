# SSCG canon re-pin — 2026-08-04 (`canon_e1`, benchmark override-plumbing refactor)

Re-pins the SSCG canon after the benchmark-harness refactor that collapses
`scripts/benchmark/run_sscg_benchmark.py`'s override plumbing onto the
`evaluation/arm_overrides.py` seam (ADR-0018 Part 2/C1's intended caller,
never previously wired up). Supersedes `canon_d1`/`canon_d2`
(`evaluation/CANON_20260804.md`, pinned same day) as the current published
baseline — this is a same-day re-pin because the refactor lands on top of
that pin's commit.

## What changed, and why a re-pin is required

The refactor (plan `federated-forging-newell`, Candidate A) replaces eleven
`_apply_*_override()` functions plus a hand-written
`_maybe_reset_for_construction_overrides` with one declarative `_KNOBS`
table consumed by `_overrides_from_args`, `_build_config_metadata`, and
`_print_overrides`. `run_single`'s signature collapses from 24 keyword
params to 8. This is a behavior-preserving refactor of the *harness*, not
the search path — but `scripts/` is inside the indexed corpus (the harness's
own chunks are searchable, which is why two golds point into it), so any
edit shifts chunk boundaries and BM25 statistics on the next reindex. Per
the project's substrate-drift rule, a fresh canon is required; exact replay
against the pre-refactor pin is neither expected nor meaningful.

**Two golds were re-pointed** (not removed — the underlying capability they
test still exists, just relocated):

| Dataset | Old gold | New gold | Grade |
|---|---|---|---|
| `golden_dataset.json` (63q) | `…:function:_apply_weight_overrides` | `…:method:run_single` | 1, tail |
| `golden_dataset_expanded.json` (147q) | `…:function:_apply_weight_overrides` | `…:method:run_single` | 1, tail |
| `golden_dataset_expanded.json` — H008 | `…:function:_apply_reranker_budget_override` | `…:method:run_single` | 3, primary |

`scripts/benchmark/audit_golden_dataset.py` confirms both datasets CLEAN
against the post-refactor index (77q/147q).

**A real bug was found and fixed during verification, not by any unit
test.** The characterization tests added to safety-net the refactor
(`tests/unit/evaluation/test_line_overlap_metrics.py`) exercise config
mutation in isolation (`_overrides_from_args` + `arm_overrides.apply_overrides`
against a scratch `SearchConfig`) — none of them call `run_single` itself.
Steps 3–4 of the plan's mechanics (substituting `run_single`'s inline
`config_metadata` block and `search_mode` handling for the table-driven
versions) were never actually applied to the code, despite being recorded
as done — `_build_config_metadata` existed but was dead code, and
`run_single` still referenced now-deleted local variables
(`search_mode`, `bm25_weight`, etc.) left over from before the Step 6
signature collapse. This surfaced only when the first live capture crashed
with `NameError: name 'search_mode' is not defined`. Fixed by wiring
`run_benchmark(..., search_mode=overrides.get("search_mode.default_mode"), ...)`
and replacing the dead inline `config_metadata` block with the
`_build_config_metadata(...)` call it was always meant to be. Full unit
gate re-confirmed green after the fix (5652 passed, 1 skipped) — this gap
is a real limitation of the characterization-test approach (see
Comparability below), not a flaw in the recipe itself.

## Procedure

1. `cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force`
   → **204 files, 2316 chunks**, 39.07s (down 1 chunk from the immediately
   prior `canon_d2` reindex's 2317 — `run_single` shrank by the dead-code
   block this session's bugfix removed).
2. `audit_golden_dataset.py` — CLEAN on both datasets (77q/147q) against the
   fresh 2316-chunk index.
3. `CLAUDE_AUTO_REINDEX=0` exported for every capture (standing mitigation
   against a silent inline reindex + `reset_searcher()` mid-run).
   Two rounds of the 63q canonical dataset:
   - `sscg_canon_e1_63q_r{1,2}.json`
4. **One round only** of the 147q expanded dataset
   (`--golden-dataset evaluation/golden_dataset_expanded.json`):
   - `sscg_canon_e1_expanded_r1.json`

   A second round was deliberately not captured: the 63q pair already
   establishes 0-flip, byte-identical determinism under ADR-0021's seed-0
   pin on this exact code path and index, so a second ~15-minute,
   133-query GPU pass on the same substrate would confirm nothing new.

## Results

### `canon_e1` — canonical (63 queries, A–F excl. D, k=10)

mrr **0.8363** (r1) / **0.8362** (r2, aggregate identical to 3 s.f. as
printed: 0.836/0.836), recall@1 0.2759, recall@5 0.6755, recall@7 0.7268,
recall@10 0.7791, recall@20 0.843, recall@50 0.8483, precision@1 0.8254,
ndcg@5 0.6945, ndcg@10 0.7412, hit_rate@5/7 1.0, pool_hit_rate 1.0
(avg pool 29.1), line_recall 0.9403, line_precision 0.2284, line_iou
0.2808, file_recall@5 0.838, file_recall@10 0.9119,
hard_negative_intrusion_rate 0.28, avg_latency_ms 4688.2 (r1) / 4652 (r2,
timing noise only). Overall: PASS.

**0 flips between r1 and r2** — confirmed by direct per-query JSON diff
(every field except `latency_ms` identical across all 63 rows) and by the
printed leaderboard's identical aggregate row.

### `canon_e1` — expanded (133 non-D queries, k=10, round 1 only)

total_queries 133, success_count 117, mrr **0.6803**, recall@1 0.3024,
recall@5 0.6619, recall@7 0.7122, recall@10 0.7713, recall@20 0.8254,
recall@50 0.8317, precision@1 0.6767, ndcg@5 0.6396, ndcg@10 0.6849,
hit_rate@5 0.8797, hit_rate@7 0.9023, pool_hit_rate 0.9624 (avg pool 28.1),
line_recall 0.8686, line_precision 0.1634, line_iou 0.1938, file_recall@5
0.8387, file_recall@10 0.9138, hard_negative_intrusion_rate 0.2083,
avg_latency_ms 4629.9. Overall: PASS.

## Delta vs. `canon_d2` (`evaluation/CANON_20260804.md`, mrr 0.8339 / 0.6591)

**63q:** mrr +0.0024, recall@5 +0.0192, recall@10 +0.0034, pool_hit_rate
unchanged at 1.0. **Expanded:** mrr +0.0212, recall@5 +0.0056, recall@10
−0.0021, pool_hit_rate −0.0075 (0.9699→0.9624).

Both moves are small and mixed in direction — inside the ±0.02 noise band
already established for this benchmark across prior same-day re-pins, and
expected: the refactor changed only the harness's own chunk boundaries
around `run_single`/the deleted wrappers plus two re-pointed golds, not any
retrieval mechanism (fusion, reranking, graph expansion, scoring). Read as
noise, not a finding. H008 in particular — the plan's stated regression
watch — holds: its surviving primary (`build_parser`) is untouched and its
re-pointed primary (`run_single`) is exactly the code that now answers the
query end-to-end.

## Comparability

- **Supersedes `canon_d2`** as the current published baseline for both
  views (canonical 63q and expanded non-D).
- **Captured against a 2316-chunk index that reflects the code state
  *before* this session's `search_mode`/`config_metadata` bugfix was
  followed by one more trivial reindex.** Sequence: reindex (2317 chunks,
  post Step-7 wrapper deletion) → captures above → bugfix applied →
  reindex again (2316 chunks, dead-code trim only) → golds re-audited
  CLEAN against the 2316-chunk index. The captures themselves were **not**
  re-run against the final 2316-chunk index — the only content delta
  between the two indexed states is the harness's own now-fixed
  `config_metadata` block (never a golden target itself), and the two
  golds that *do* target `run_single` (Q67, H008) point at it
  parent-kind/line-agnostic, so the correction doesn't invalidate the
  gold, only trims a few lines from the chunk actually embedded. Documented
  here rather than silently accepted: a future session touching this file
  again should recapture from a reindex taken *after* all edits land, not
  interleave capture and fix as this session did.
- **Exposes a gap in the characterization-test safety net**: tests built
  around `_overrides_from_args`/`apply_overrides`/`_build_config_metadata`
  in isolation gave high confidence in config *mutation* correctness but
  none in `run_single`'s own wiring of those pieces together — the
  `NameError` this session found and fixed was only caught by a live run.
  No test was added to close this gap (logged here as an observation, not
  actioned — the plan's own scope was the refactor, and adding
  `run_single`-level integration coverage is a separate, unscoped
  improvement).
- Not comparable byte-for-byte to `canon_d1`/`canon_d2`'s per-query rows
  (chunk IDs for `run_single`/the deleted wrappers moved), only at the
  aggregate level.

## ADR

**No new ADR.** No retrieval mechanism changed; this is a harness-internal
refactor (fewer restatements of the same 19 knobs) plus a bugfix restoring
intended-but-never-wired behavior, not a new architectural decision.
