# Canon re-pin with 60 new commit-mined queries (2026-11-22, second pin)

## Status: CANON OF RECORD — supersedes `CANON_20261122_LABEL_AUDIT.md` (same day)

| View | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | pool_hit_rate |
|---|---|---|---|---|---|---|
| 63q (`golden_dataset.json`) | 63 | **0.8425** | 0.6482 | 0.7544 | 0.8270 | 1.0000 |
| Expanded (`golden_dataset_expanded.json`, non-D) | 193 | **0.7054** | 0.6320 | 0.7765 | 0.8214 | 0.9585 |
| F-via-similar | 63 | **0.8935** | 0.6453 | 0.7584 | 0.8255 | 1.0000 |

Substrate: HEAD `a42f1300`, incremental reindex before the legs (254 files, 3,402 chunks; the
reindex saw 11 added and 8 modified files since the first pin: the IVF code removal and four new
probe scripts). Same runner, flags and models as `CANON_20261122_LABEL_AUDIT.md`. 63q r1 == r2:
63 / 63 lists identical. Dumps: `evaluation/canon_<leg>_20261122b.json` (local).

The 133q view is now a 193q view: the "133q" name in older records means the expanded set
before this pin.

## The new queries

60 category-H queries, H100-H159 (splits 36 / 12 / 12), from fix / feat / perf commits on
`development` between 2026-08-01 and 2026-11-22. Gold is labelled against the code at HEAD (the
same-day audit found commit-mined labels that went stale when logic moved). Queries were then
rewritten at symptom level (what a developer would type without knowing the fix), because the
first, fix-describing wording put 40 of 60 at rank 1 and would rarely move in an A/B. Three
queries (H108, H124, H129) stay more specific so each keeps one clear answer. One label added
in the rewrite (H125, grade 2). Drafts, old wording, source commits and 27 reserve queries:
`evaluation/commit_mined_candidates_20261122.json` (local). The owner approved the set.

On this pin the 60 new queries score MRR 0.6785; first grade-3 rank: 1 for 33, 2-5 for 17,
6-10 for 4, not in the top 10 for 6. pool_hit 57 / 60.

## Drift against the first pin (same day)

| Measure | First pin (`ae0feb7e`) | This pin (`a42f1300`) | Delta |
|---|---|---|---|
| 63q MRR | 0.8458 | 0.8425 | -0.0033 |
| 63q recall@20 | 0.8539 | 0.8270 | **-0.0269** |
| Old 133 queries, MRR | 0.7162 | 0.7175 | +0.0013 |
| Old 133 queries, recall@20 | 0.8544 | 0.8435 | -0.0109 |
| F-via-similar MRR | 0.8983 | 0.8935 | -0.0048 |
| F-via-similar recall@20 | 0.8282 | 0.8255 | -0.0027 |

MRR is inside the +-0.02 band on every view. 63q recall@20 breaches the -0.02 band by 0.0069.
Cause, as far as it was checked: substrate drift from the reindex, not a defect. 12 of 63
queries moved, in both directions (5 recall@20 up, 7 down); the two large losses are
"similar to X" queries (Q70 1.00 -> 0.22, Q94 1.00 -> 0.25) whose lists swapped siblings
(Go / C# chunker constructors for JS / TS ones). None of the four new probe scripts entered any
list, and no golden label points at removed IVF code. Only 19 of 133 old-query lists are
identical to the first pin, the same scale as the 10-19 lesson (a reindex rebuilds the call
graph and reorders heads through centrality: 59 / 133 lists changed). Adopted with the breach
recorded, as on 2026-09-20.

## Next action

Pair any A/B against these legs only, in one session, on one index. The new queries are the
first set mined against HEAD; re-run the rank-1 label audit
(`scripts/benchmark/probe_eval_power.py`, `CANON_20261122_LABEL_AUDIT.md`) after the next
large refactor.
