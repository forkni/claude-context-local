# TM2C2 Normalized-Score Fusion Probe — GATE FAILED (2026-08-14)

**Verdict: NOT BUILT.** The TM2C2 fusion probe finds zero gold rescues on the 133q
expanded set at both pre-registered alpha values. Phase B2 (production build) does
not proceed; `fusion_function`/`tm2c2_alpha` are not added to `search/config.py`.

## Context

`docs/plans/RAG_IMPROVEMENT_ROADMAP_20260814.md`'s Track B proposed TM2C2
(Bruch, Gai & Ingber, "An Analysis of Fusion Functions for Hybrid Retrieval",
ACM TOIS 2023, arXiv 2210.11934) — a convex combination of theoretical-min-max-
normalized BM25/dense leg scores — as a replacement fusion arithmetic targeting
the RRF-exclusion class: candidates that place decently on both legs but miss
RRF's fused cut because reciprocal rank saturates fast. The graph-reserve half
of Track B was already dropped (`GRAPH_RESERVE_PROBE_20260814.md`); this note
covers the fusion half only, per user decision "Drop reserve, ship TM2C2 only."

Read-only probe: `scripts/benchmark/probe_tm2c2_fusion.py`. Replays each golden
query's raw BM25/dense legs at the exact deployed leg-search depth
(`search_k = max(reranker.top_k_candidates, k*5)`, `search_executor.py:130`) and
fused-pool cut (`fusion_k = max(k, reranker.top_k_candidates)`, `:177`), then
compares RRF's cut membership (`RRFReranker.rerank_simple`, unmodified) against
a local TM2C2 implementation (theoretical min 0.0 BM25 / −1.0 cosine, empirical
per-query max, `alpha` = dense-side weight). No production code touched.

## Substrate

Live index, 2,406 vectors (post-`ecc15fe`). B0 re-pin found the canon substrate
(2,403 vectors, `REMAINING_LEVERS_AB_20260814.md`) had drifted — fresh baselines
captured and used as this campaign's reference per the plan's mandatory-re-pin
rule:

| Dataset | MRR | pool_hit_rate |
|---|---|---|
| 63q (`benchmark_results/tm2c2/b0_pin_63q_r1.json`) | 0.8516 | 0.9048 |
| 133q (`benchmark_results/tm2c2/b0_pin_133q_r1.json`) | 0.6713 | 0.9023 |

Re-derived hard-miss cohort (mrr=0.0 on 133q, supersedes the stale
`REMAINING_LEVERS_AB_20260814.md` list): Q101, Q103, Q106, Q117, Q122, H008,
H050, H054, H066.

## Pre-registered gate (from the approved plan)

**Each α independently:** 133q ≥1 membership rescue with ≥1 of them Q121-class
(`dense_rank > cut ∧ bm25_rank > cut`, i.e. beyond the cut on both raw legs);
63q net (rescues − evictions) ≥ 0. **Abort:** neither α passes → mechanism dead,
disposition note, no production code.

## Results

`benchmark_results/tm2c2/probe_tm2c2_{63q,133q}.json`, α ∈ {0.65, 0.8}, cut=30
(`reranker.top_k_candidates`), search_k=50 (`k=10`), both datasets.

| dataset | alpha | rescued golds | evicted golds | net | q121-class rescues |
|---|---|---|---|---|---|
| 63q | 0.65 | 0 | 0 | 0 | 0 |
| 63q | 0.8 | 0 | 0 | 0 | 0 |
| 133q | 0.65 | 0 | 0 | 0 | 0 |
| 133q | 0.8 | 0 | 0 | 0 | 0 |

Zero gold-membership change at both α on both datasets (196 queries × 2 α =
392 query/alpha evaluations). The 133q half of the gate (≥1 rescue) fails at
both α → **abort triggers**.

### This is not a probe no-op

Before accepting an all-zero result, the fusion arithmetic was checked against
raw cut-membership (not just gold rows): across all 266 query/alpha pairs on
the 133q set, **8 pairs (Q38, Q44, Q46, Q55, ...) show a real cut-membership
difference** between RRF and TM2C2, max 2 candidates swapped per pair. TM2C2
genuinely reorders candidates near the cut boundary — it just never happens to
swap in a graded gold on either dataset. The null result is a real finding
about this substrate's gold distribution relative to the cut, not a bug in the
probe.

### Why the Q121 exemplar doesn't fire

The plan's cited exemplar (dense rank 84 / BM25 rank 80 / RRF fused rank 41)
came from an earlier probe run at `probe_depth=200` — deeper than the deployed
funnel. Re-checked at the **deployed** leg-search depth (`search_k=50`, the
depth this probe correctly uses per its design), Q121's three golds are mostly
unreachable in the raw legs at all:

```
search/faiss_index.py:class:FaissVectorIndex   dense_rank None  bm25_rank None
search/indexer.py:class:CodeIndexManager       dense_rank 46    bm25_rank None
search/faiss_index.py:method:...create         dense_rank None  bm25_rank 32
cut=30  search_k=50
```

The top-graded gold (grade 3) is absent from both legs within the deployed
window; the other two are visible on only one leg each, past the cut. No
fusion function — RRF or TM2C2 — can rescue a candidate that isn't retrieved.
This is a **leg-search-depth** problem, not a fused-cut-arithmetic problem: the
Q121-class mechanism this probe targets requires candidates that ARE visible
on both legs (just past the cut), and at deployed depth Q121 itself doesn't
qualify. The probe design (deployed depth, per the plan) is correct; the named
exemplar just doesn't reproduce at that depth on the current substrate.

## Disposition

- `fusion_function`/`tm2c2_alpha` NOT added to `search/config.py`; no
  `RRFReranker.fuse_tm2c2`/`_theoretical_min_max_normalize` in
  `search/reranker.py`; no dispatch change in `search/search_executor.py`.
  `scripts/benchmark/probe_tm2c2_fusion.py` stays in-tree as the reference
  implementation for any future re-probe.
- Track B is now fully closed: graph reserve NOT BUILT
  (`GRAPH_RESERVE_PROBE_20260814.md`), fusion NOT BUILT (this note). No
  production code from either half ships.
- Reopening condition: this null result is depth-bounded, not
  arithmetic-bounded — TM2C2 does reorder near the cut (8/266 pairs), so the
  mechanism isn't inert, but the deployed leg-search depth (`search_k=50` at
  `k=10`) is too shallow for the golds that would demonstrate a rescue on this
  substrate. A future attempt should probe leg-search depth itself (independent
  of fusion function) as the lever — e.g. whether widening `search_k` surfaces
  more Q121-class candidates for ANY fusion function to act on — before
  re-proposing TM2C2 or any other cut-arithmetic change at the current depth.
- No canon re-pin needed (no production code changed); `b0_pin_*` captures in
  `benchmark_results/tm2c2/` stand as this campaign's substrate record but are
  not promoted to published canons since nothing shipped.
