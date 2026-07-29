# Multi-hop pool flooding — blast radius (2026-07-28)

Phase 1–2 of the diagnose plan (`log-investigate-multi-hop-pool-optimized-starlight`).
Probe: `scripts/benchmark/probe_rerank_window.py --all`, full run at
`scripts/logs/probe_rerank_window_k10_all.log`. 87 non-D/F golden queries
(`evaluation/golden_dataset_expanded.json`), 132 grade-3 golds total, k=10,
deployed geometry (`multi_hop.expansion=0.5`, `initial_k_multiplier=2.0`,
`reranker.top_k_candidates=30`, listwise jina-reranker-v3).

## Raw totals

```
Totals: window-cut=4 model-demotion=2 pool-loss=3 ok=123
VERDICT: RED - 4 grade-3 gold(s) window-cut at k=10
```

## Per-query detail (all non-`ok` grade-3 golds)

| Query | hop1_rank | in_pool | in_window | final_rank | score | source | label | **actual outcome** |
|-------|-----------|---------|-----------|------------|-------|--------|-------|---------------------|
| Q01 | 9 | yes | yes | miss | 0.035 | hybrid | model-demotion | **genuine miss** (2nd gold, rank 17, never reached hop-1 top-10 either) |
| Q04 | 3 | yes | yes | 3 | 0.103 | hybrid | ok | — |
| Q04 | 2 | yes | yes | 2 | 0.296 | hybrid | ok | — |
| Q04 | 6 | yes | yes | 13 | 0.018 | hybrid | model-demotion | masked — query already hits via the rank-2/3 golds above |
| Q12 | 6 | yes | **no** | miss | 0.099 | hybrid | window-cut | **genuine miss** |
| Q12 | – | yes | no | miss | 0.000 | graph_hop | ok | never ranked in hop-1; unrelated to H1 |
| Q90 | – | no | no | miss | – | – | pool-loss | out of scope (retrieval gap); query still hits overall via its 2nd gold (rank 4, `multi_hop`-sourced, classified `ok`) |
| Q101 | – | no | no | miss | – | – | pool-loss | out of scope (known ADR-0012 vocab gap) |
| Q102 | – | no | no | miss | – | – | pool-loss | out of scope (retrieval gap) |
| Q104 | **1** | yes | **no** | miss | 0.224 | hybrid | window-cut | **genuine miss** |
| Q122 | 6 | yes | **no** | miss | -0.037 | hybrid | window-cut | **genuine miss** |
| Q125 | 5 | yes | **no** | **3** | 0.092 | hybrid | window-cut | **not a miss** — recovered via the ego-graph tail pass (see caveat below) |

## Classification caveat (important, not anticipated in the plan)

The `window-cut` label only encodes "excluded from the multi-hop merge-pool's
30-slot rerank window" — it does **not** imply the query ultimately misses.
**Q125 proves this**: its gold is cut from the multi-hop window (boundary
score 0.259 vs. gold's 0.092) exactly like Q12/Q104/Q122, yet the final
benchmark result hits at rank 3. The gold must re-enter through
`HybridSearcher`'s ego-graph/parent-expansion tail pass (item 4 in the plan's
verified boundary chain) — i.e. it's structurally adjacent to one of the
multi-hop top-10 survivors and gets pulled back in downstream. This is a
**second, independent rescue path** that only fires when the gold happens to
be graph-adjacent to a chunk that did survive the cut; it is not something
the planned `hop1_reserved_slots` fix creates or relies on.

**Net effect**: of the 4 `window-cut` labels, only **3 are actual benchmark
misses**: Q12, Q104, Q122. Q125 is a near-miss that self-heals.

## Revised failure-mode counts (query-level, out of 87 queries / 132 golds)

| Classification | Count | Actionable by `hop1_reserved_slots` reserve (H1 fix)? |
|---|---|---|
| **True window-cut miss** (Q12, Q104, Q122) | 3 | **Yes** — this is exactly the mechanism the reserve targets |
| Window-cut but self-recovered via ego-tail (Q125) | 1 | N/A — already a hit |
| In-window model-demotion, genuine miss (Q01) | 1 | **No** — gold already reached the listwise model and was still outranked; a reserve only affects window membership, not the model's own ranking (H3, not H1) |
| In-window model-demotion, masked by another gold (Q04) | 1 | No (query already hits) |
| Pool-loss, retrieval gap (Q90, Q101, Q102) | 3 | No — out of scope, pre-existing dense/BM25 miss, not a rerank-stage defect |

## Hypothesis verdicts (H1–H5)

- **H1 (score-scale incomparability at the 30-slot cut) — CONFIRMED, and it is
  the whole story for the 3 true window-cut misses.** In every true window-cut
  row the gold's jina-scaled `.score` (0.099, 0.224, -0.037) is far below the
  30th-candidate boundary score (0.625, 0.693, 0.039) — i.e. cosine-scored
  `multi_hop`/`hybrid`-sourced expansion candidates dominate the sort at
  `reranking_engine.py:270` purely because they're on a different scale, not
  because they're more relevant. Matches the plan's boundary-chain trace
  exactly.
- **H2 (listwise regime change with candidate count)** — not needed to explain
  any observed miss; deferred to the cheap `--top-k-candidates` arms in Phase 3
  since it's a free comparison point once that harness flag is exercised.
- **H3 (genuine in-window demotion) — CONFIRMED as a second, independent
  mechanism, out of reach for the reserve fix.** Q01's second gold (rank 9,
  score 0.035) is in-window and still not promoted to the top 10 by the
  listwise model itself. No amount of pool-composition change fixes this — it
  would need either a different reranker or `reranker.top_k_candidates`
  reduction concentrating attention (Phase 3's cheap arms will show whether
  that helps or hurts).
- **H4 (double listwise rerank compounding)** — not implicated; nothing in the
  trace suggests the hop-1 pass and merge pass interact destructively beyond
  the score-scale issue already covered by H1.
- **H5 (`dedupe_split_blocks` collapsing gold)** — not implicated in any of
  the 9 non-`ok` rows; no evidence of a gold's chunk_id disappearing via
  dedup.

## Expected ceiling on the fix, before implementing

Only 3 of 87 queries (132 golds) are actionable window-cut misses, and their
hop-1 ranks are 1, 6, 6 — reciprocal ranks 1.0, 0.167, 0.167 if the reserve
fully restores them to their hop-1 rank in the final results (optimistic
upper bound; the listwise model could still re-rank them lower once inside
the window, same as it already does for Q01/Q04's in-window golds).

Optimistic ceiling: `Δaggregate MRR ≈ (1.0 + 0.167 + 0.167) / 87 ≈ +0.0157`.

That is **inside the established ±0.02 noise band** for this benchmark. This
does not mean the fix is worthless (recall@20/recall@50/pool_hit_rate should
still move cleanly, and 3/3 fixed window-cut queries is a meaningful,
mechanism-verified win even if the aggregate MRR delta is noise-sized), but
it means the Phase 4 A/B must not be graded on aggregate MRR movement alone —
the per-query flip (does Q12/Q104/Q122 hit at k=10 post-fix, with everything
else held constant) is the primary acceptance signal, matching the plan's
Phase 5 requirement to re-run the Phase 1 probe and see it go green.

## Next steps (Phase 3)

1. Cheap config-only arms first (`--top-k-candidates 20/50`,
   `--multi-hop-expansion 0.25`) — free data on H2, and on whether narrowing
   the pool incidentally fixes some of these 3 without a new knob at all.
2. Implement `RerankerConfig.hop1_reserved_slots` per the plan (inside
   `rerank_by_query`, between the `:270` sort and `:278` `_run_rerank` call).
3. A/B, graded primarily on the Q12/Q104/Q122 per-query flip plus
   recall@20/recall@50/pool_hit_rate direction, with aggregate MRR as a
   secondary/guard metric given the ±0.02 ceiling estimated above.
