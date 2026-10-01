# GAR-style rerank-window membership: pre-registration (2026-10-01)

Status: **pre-registered, A/B not yet run.** This file is the plan of record; results are
appended below the line at the end after the V2 legs run.

Related: ADR-0079 (Proposed), `evaluation/POOL_ORDER_AB_20260815.md` (precedent),
`evaluation/CANON_20260923_PREAMBLE_PACKING.md` (last canon).

## Problem

Canon (`092f14ab`) to HEAD (`3f90c5f6`): MRR 63q 0.8177 -> 0.7980, 133q 0.6527 -> 0.6128,
F-via-similar 0.8668 -> 0.8560. The ranking code did not change in that range. Content drift
changes how often a pre-existing defect fires: `_order_merged_pool("score")` sorts jina scores
(hop-1 survivors) and FAISS cosines (semantic expansions) together, and
`_apply_hop1_reserve(evict_policy="tail")` then drops hop-1 items from the pool, including
hop-1 rank 1. On HEAD, 29 of 147 queries lose a grade-3 gold at that step.

## Treatment

New `merged_pool_policy` value `"gar_interleave"` (GAR, arXiv 2208.08942): alternate 1:1 between
hop-1 survivors (by `hop1_rank`, hop-1 first) and the frontier (expansion candidates); when one
side runs out the other fills the rest. It bypasses `_apply_hop1_reserve` and
`_apply_graph_hop_window_cap`. Candidates past slot 30 are backfilled in interleave order, never
dropped. Hop-1 vs frontier is classified by `metadata["hop1_rank"]`, not by `source`.

`anchor_rank` (commit `cf825fc1`) = the lowest hop-1 rank among the anchors that produced the
candidate, in either channel.

## Offline simulation (frontier order), HEAD index, 124 queries (D/F excluded), k=10

Probe: `scripts/benchmark/probe_rerank_window.py --all` (self-validity 124/124 OK; every one of
4,571 frontier items carries an `anchor_rank`). Grade-3 golds present in the Pass-2 pool: 174.

| policy | golds in window | queries losing a gold vs `score` | queries rescued vs `score` | graph_hop window median | queries with 0 graph_hop | hop-1 rank 1 in window |
|---|---|---|---|---|---|---|
| score (deployed) | 145 | 0 | 0 | 1.0 | 48.4% | 101/115 |
| score_no_reserve | 150 | 11 | 15 | 5.0 | 31.5% | 107/115 |
| score_reserve_fix | 158 | 3 | 15 | 1.5 | 37.9% | 115/115 |
| channel_priority | 165 | 3 | 21 | 0.0 | 60.5% | 115/115 |
| **gar_anchor_first** | **169** | 1 | 23 | 10.0 | 0.0% | 115/115 |
| gar_round_robin | 166 | 2 | 21 | 9.0 | 0.0% | 115/115 |

Frontier order alternates graph_hop and semantic inside each anchor, graph first.

**Pre-registered winner: `gar_anchor_first`** (more golds in window than round-robin, 169 vs
166, and fewer queries losing one; the plan said anchor-first on a tie, so the rule is
satisfied either way). The V2 treatment uses this order only; round-robin is not run.

Caveats stated up front: the simulation counts window membership, not final rank. A gold in the
window can still be demoted by the listwise model, and the probe cannot say whether the 23
rescued queries gain top-10 rank. `gar_anchor_first` does cost one query a gold that `score`
had in the window (lost_vs_score = 1); the A/B per-query diff will name it.

Note on the probe's built-in A1 gate (`ABORT/HALT`): its P1/P2/P3/P4 predictions belong to the
2026-08 `merged_pool_policy` investigation and describe an older pool shape. They are not this
plan's gate and were not used. A3 (self-validity) is the part that matters here, and it passed.

## V2 A/B protocol

- Index: HEAD index, no reindex between legs. `CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0`.
- Control: `reranker.merged_pool_policy="score"` (deployed). Treatment: `"gar_interleave"`.
- Views: 63q, 133q, F-via-similar; plus 63q r2 of the treatment for determinism.
- Adoption gate (ADR-0077 style), all must hold:
  1. No paired CI excluding 0 on the negative side for MRR, recall@10, recall@20 on any view.
  2. No negative-excluding paired CI on recall@5 on any view; 63q MRR CI checked on its own.
     (These are the two CIs that disqualified `channel_priority`: 63q MRR [-0.0437, -0.0013],
     recall@5 [-0.0529, -0.0013].)
  3. Median graph_hop window occupancy above 0 (base 7 in the 2026-08 report).
  4. 63q r1/r2 bit-identical.
- Reported, not gating: Q12, H034, H066 (precedent movers); `gold_in_window` per query;
  `pool_hit_rate` (informational only, backfill can inflate it).
- If the gate passes: flip the default, re-pin the canon, ADR-0079 Accepted, then delete the
  legacy reserve/band/cap code in a separate commit. If it fails: this report is committed with
  the result and the default stays `"score"`.

## Results

One run per leg on the HEAD index (3,114 chunks), `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`,
paired bootstrap CIs from `run_sscg_benchmark.py --compare`. Control `"score"`, treatment
`"gar_interleave"`.

| view | metric | control | treatment | delta [95% CI] |
|---|---|---|---|---|
| 63q | MRR | 0.8275 | 0.8415 | +0.0140 [-0.018, +0.046] |
| 63q | recall@5 / @10 / @20 | 0.6417 / 0.7537 / 0.8206 | 0.6506 / 0.7631 / 0.8425 | +0.009 / +0.010 / +0.022, all CIs span 0 |
| 133q | MRR | 0.6268 | 0.6637 | +0.0369 [-0.003, +0.077] |
| 133q | recall@5 | 0.5946 | 0.6558 | **+0.0612 [+0.018, +0.105]** |
| 133q | recall@10 | 0.6859 | 0.7794 | **+0.0935 [+0.043, +0.144]** |
| 133q | recall@20 | 0.7521 | 0.8427 | **+0.0906 [+0.046, +0.135]** |
| F-via-similar | MRR | 0.8854 | 0.8915 | +0.0061 [-0.022, +0.034] |
| F-via-similar | recall@5 / @10 / @20 | 0.6438 / 0.7578 / 0.7994 | 0.6459 / 0.7671 / 0.8163 | +0.002 / +0.009 / +0.017, all CIs span 0 |

Window membership (`gold_in_window_rate`, control -> treatment): 63q 0.984 -> 1.000,
133q 0.880 -> 0.970, F-via-similar 0.982 -> 1.000. Queries with a gold evicted by the reserve under
the control: 8, 25, 6. The treatment has no reserve.

### Gate

1. No negative-excluding CI on MRR / recall@10 / recall@20, any view: **PASS** (no CI is negative
   anywhere; the three 133q recall CIs exclude 0 on the positive side).
2. recall@5 and 63q MRR on their own: **PASS**. 63q MRR CI [-0.018, +0.046] against
   `channel_priority`'s [-0.0437, -0.0013]; recall@5 CIs span 0 on 63q and F-via-similar and are
   positive on 133q.
3. Graph_hop window occupancy: **PASS**. Measured with `probe_rerank_window.py --all
   --set reranker.merged_pool_policy=gar_interleave` on the observed Pass-2 `window_ids` (124
   queries): median **10**, mean 9.6, **0** queries with no graph_hop item (the offline
   simulation predicted 10; control simulation median 1; `channel_priority` 0). Hop-1 rank 1 is
   in the window on 124/124.
4. 63q r1 vs r2: **PASS**, aggregates and retrieved lists bit-identical.

The probe's own A1/A3 gate prints ABORT/HALT on that run. That is expected and not a result: its
self-validity check compares the observed window to the simulated `"score"` window, and the live
policy is no longer `"score"`. Only the observed `window_ids` were used.

### Movers

- Gains: Q106, H029, H048, Q126 (0 -> 1.0); Q99, Q133, H022, H066 (0 -> 0.5); H006, Q54, Q77
  (0.5 -> 1.0); H034 (0 -> 0.25); H039, H045, H009 smaller.
- Losses: Q04, Q102, Q104, H062, H067 (1.0 -> 0.5), Q119 (0.33 -> 0.08), Q127 (0.5 -> 0.25),
  H035 (0.33 -> 0.14), Q12 (0.2 -> 0). Q12 regressed under `channel_priority` too, but here it
  is one query among 39 movers and the aggregate CIs are not negative.
- 63q changed on 9 queries, 133q on 39.
- The one gold `"score"` had in the window and `gar_interleave` lost is the offline
  simulation's `lost_vs_score=1`; the observed run does not name it per query.

### Caveat: control drift

The control scores 63q MRR 0.8275, but the first HEAD run of this investigation (02:56, same SHA,
same 3,114 chunks, same policy) scored 0.7980. Nine queries differ between the two, including Q07
(0 -> 1.0). The 0.8275 reproduces in the A0 same-index run, so it is stable now. The cause of the
earlier lower value is **unresolved**; an index rebuild between the two runs (embedding
batch-composition noise, ~1e-3 in 1-cos) is the leading but unconfirmed suspect. The A/B is
unaffected, since both legs share one index. It does weaken the claim that the 0.7980 drop was
entirely this defect: the control is now above the 09-23 canon on 63q (0.8275 vs 0.8177) and still
below it on 133q (0.6268 vs 0.6527).
