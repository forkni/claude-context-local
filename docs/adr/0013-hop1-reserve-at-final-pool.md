# Reserve hop-1 winners at the multi-hop rerank window, not at hop-1 fusion

Status: accepted
Date: 2026-07-28

Multi-hop search reserves up to `RerankerConfig.hop1_reserved_slots` (default
**6**) of the best-hop1-ranked candidates into the `top_k_candidates` rerank
window whenever hop-2 expansion pushes the pool past it, implemented as a seam
inside `RerankingEngine.rerank_by_query` / `_apply_hop1_reserve`
(`search/reranking_engine.py`). Default 0 (the pre-fix behaviour) is
byte-identical; only `MultiHopSearcher.search()` passes a non-zero value — the
ego-graph/parent-expansion tail rerank calls (`hybrid_searcher.py:768`, `:781`)
are unaffected.

## Context

The 2026-07-28 query-expansion A/B (`evaluation/QUERY_EXPANSION_AB_20260728.md`,
[ADR-0012](0012-curated-vocabulary-query-expansion.md)) surfaced a distinct
defect: Q104 and Q122 rank **1** and **6**
respectively out of hop-1, survive hop-2 expansion into a 66–83-candidate
merged pool, and are then demoted out of the final top-10 by the listwise
reranker — even though query-side expansion has no leverage over this stage.

`probe_rerank_window.py` (Phase 1) instrumented the `rerank_by_query` sort/cut
boundary directly and confirmed the mechanism: the merged pool is sorted by
`.score` across three **incomparable scales** — hop-1 survivors carry an
overwritten jina listwise relevance score (observed range ≈ −0.12…+0.22),
semantic-expansion candidates carry raw FAISS cosine similarity (≈0.5–0.9), and
graph-expansion candidates carry literal `0.0`. Sorted together, every
expansion candidate structurally outranks a hop-1 winner with a middling or
negative jina score. With ~46–57 expansion candidates competing for a 30-slot
`top_k_candidates` window — 30 fixed by
[ADR-0011](0011-listwise-reranker-doc-cap.md) for listwise-rerank latency, not
adjustable per query — the hop-1 winner falls outside `[:30]` and the
listwise model never sees it at all — a **window-cut**, not a ranking
decision.

Phase 2 classified every 96q benchmark miss into three categories:
window-cut (in merged pool, outside window — what this fix targets),
model-demotion (in window, listwise still ranks it below k — not fixable by a
reserve), and pool-loss (absent from the merged pool entirely — a retrieval
gap, out of scope). Of the three original target queries, only Q104 and Q12
are genuine window-cut cases; **Q122 is model-demotion** and stays a miss at
every reserve depth tested (confirmed at N=5, 6, 10) — the listwise model
itself ranks it below k once inside the window, which no reserve can fix.

## Why the reserve lives at the rerank window, not at hop-1 fusion

A prior attempt at a similarly-named idea, `bm25_reserved_slots` (closed
negative, commit `1c9c81d`), reserved slots at hop-1 BM25/RRF fusion instead.
It failed a 9-run sweep with zero `pool_hit` rescues and MRR regressions of
−0.017 to −0.034: injecting a reservation at hop-1 fusion doesn't survive the
downstream reshaping — multi-hop expansion, ego-graph expansion, and parent
expansion all re-merge and re-sort the pool before the final cut, so whatever
the hop-1 reserve protected gets diluted or evicted again well before the
window that actually determines the final ranking. The lesson: **a reserve
must sit at the boundary where the loss actually happens**, not one hop
upstream of it. This fix reserves at the exact seam the probe identified —
immediately before the `top_k_candidates` slice inside
`RerankingEngine.rerank_by_query` — which is also why the caller-side
alternative (reordering `merged_results` before calling `rerank_by_query`) was
rejected during planning: `rerank_by_query`'s own `.score` sort at the top of
the method destroys any pre-ordering the caller supplies, making that variant
a silent no-op.

## Choosing N=6

A single-query probe sweep (Q12, hop1_rank 6) across N=5, 6, 8, 9, 10
established a non-monotonic trade-off: the reserve promotes tagged candidates
by evicting an equal count from the window's tail, and past a threshold that
eviction starts breaking *other* golds for the same query. N=5 does not reach
Q12 (needs N≥6 to promote a rank-6 hop-1 candidate). N=8 flips Q12's own
second gold (sourced via `graph_hop`) from hit to miss; N=9 pool-losses it
entirely. This directly explains why an aggregate 96q run at N=10 showed a net
MRR regression (avg ≈−0.024, wrong direction, recall@20 avg ≈−0.0175) despite
individually rescuing Q104 and Q122's window-cut at that depth — the
collateral damage to unrelated golds outweighed the localized fix.

N=6 was A/B'd (2 runs per dataset, both the 96q expanded set and the 63q base
set) against this trade-off and clears the Phase 4 ship gate:

| Dataset | Metric | Control | N=6 (mean of 2) | Δ |
|---|---|---|---|---|
| 96q | MRR | 0.6638 | 0.6668 | +0.003 (within ±0.02 noise) |
| 96q | recall@20 | 0.7989 | 0.8156 | +0.017 |
| 96q | recall@50 | 0.8025 | 0.8182 | +0.016 |
| 96q | pool_hit_rate | 0.9479 | 0.974 | +0.026 |
| 63q | MRR | 0.7838 | 0.7795 | −0.004 (within ±0.02 noise) |
| 63q | recall@20 | 0.8061 | 0.8216 | +0.016 |
| 63q | pool_hit_rate | 0.9841 | 1.0 | +0.016 |

MRR is flat within noise on both datasets; recall@20, recall@50, and
pool_hit_rate all move in the expected positive direction on both; no latency
regression on either dataset. `pool_hit_rate` moving is expected, not a red
flag — see the boundary-chain analysis in the investigation plan: benchmark
`pool_hit` reflects the ego-tail pass's input pool, which is downstream of the
multi-hop cut this fix repairs, so a successful fix necessarily moves it.

## Consequences

- Default flips from 0 (disabled) to **6**. Existing callers that never pass
  `hop1_reserved_slots` (the ego-graph/parent-expansion tail rerank) are
  unaffected — the parameter is opt-in per call site, not a global toggle.
- Q104's window-cut is fixed (`probe_rerank_window.py` now prints
  `VERDICT: GREEN` with Q104 classified `ok`). Q122 remains a documented,
  intentional miss — it is model-demotion, a different failure mode this fix
  does not and cannot address.
- `RerankingEngine.last_window_ids` was added alongside the pre-existing
  `last_candidate_ids` (pool membership) so future diagnostics can distinguish
  pool membership from rerank-window membership directly, without
  re-instrumenting a probe.
- This fix removes the confound the
  [ADR-0012](0012-curated-vocabulary-query-expansion.md) query-expansion A/B
  was blocked on for Q104: query-expansion decisions for that query can be
  re-evaluated now that the post-retrieval demotion is fixed. Q122 and Q101
  remain unaffected (model-demotion and genuine vocabulary gap, respectively —
  no interaction with this fix).
- Larger reserve depths are not a free dial: the collateral-eviction trade-off
  means re-tuning `hop1_reserved_slots` upward requires re-running the full
  A/B, not just re-checking the probe on the original target queries.
