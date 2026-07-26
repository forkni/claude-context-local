# Pool-Miss Diagnosis: Expanded Golden Set (Track B)

**Date**: 2026-07-26 | **Baseline**: `benchmark_results/sscg_expanded_baseline_20260726.json`
(pool_hit = 0.9792 on the 96-query expanded set; 63-query set is at 1.0)

Both pool-miss queries are **true retrieval misses** — the gold chunks exist in the live
index under their exact chunk_ids, and the dataset labels are correct. No label drift.
They are recorded here as the target population for Track A (BM25 tokenizer) and any
future pool-composition work.

---

## Q102 (category A) — structurally excluded despite a BM25 hit

**Query**: "prevent phantom entries from an earlier analysis from reappearing after a
from-scratch rebuild"
**Gold**: `graph/graph_storage.py:860-872:method:CodeGraphStorage.clear`
(secondary: `GraphIntegration.clear`)

Per-leg behavior (live index, 2026-07-26):

| Leg | Gold rank | Notes |
|-----|-----------|-------|
| BM25 (`search_mode="bm25"`) | ~6 | Docstring literally contains "stale phantom nodes" — strong lexical match |
| Dense base retrieval | absent from top-35 | In the full semantic pipeline the gold reaches rank 2, but only via `ego_graph` expansion, which runs *after* pool formation |
| Hybrid fused pool (30) | **absent** | pool_hit = 0 |

### Root cause: weighted-RRF arithmetic makes BM25-unique candidates unpoolable

Fusion (`search/search_executor.py:97-245` → `search/reranker.py:83-183`): each leg
retrieves `search_k = max(30, k*5)` candidates; RRF contribution is
`weight * 1/(rrf_k + rank)` with `bm25_weight=0.35`, `dense_weight=0.65`, `rrf_k=100`;
the fused list is truncated to `fusion_k = max(k, reranker.top_k_candidates=30)`.

- Worst dense candidate (rank 35): `0.65 / 135 ≈ 0.00481`
- Best possible BM25-unique candidate (rank 1): `0.35 / 101 ≈ 0.00347`

Every dense candidate outscores every BM25-unique candidate, so the top-30 pool is
filled entirely from the dense leg's 35. For a BM25 rank-1 candidate to beat a dense
candidate at rank r requires `r > 101 * (0.65/0.35) − 100 ≈ 87.6` — the dense leg never
returns that many. **Under current parameters the BM25 leg can only reorder chunks the
dense leg already retrieved; it can never introduce a candidate into the pool.**

This is not a regression from the pool 50 → 30 reduction (commit f936d0b): at pool 50,
the worst dense contribution was `0.65/150 ≈ 0.00433`, still above 0.00347. The
exclusion is inherent to the weight ratio (0.65:0.35) + rrf_k=100 + `search_k` being
approximately the pool size.

## Q122 (category C) — bilateral vocabulary/paraphrase miss

**Query**: "hold several loaded encoders at once and drop the least valuable when
memory gets tight"
**Gold**: `mcp_server/model_pool_manager.py:class:ModelPoolManager`
(secondary: `ModelPoolManager.get_embedder`)

Per-leg behavior:

| Leg | Gold rank | Notes |
|-----|-----------|-------|
| BM25 | absent | Vocabulary mismatch: query says "encoders" / "drop the least valuable"; code says "embedder" / LRU-eviction terms |
| Dense base retrieval | absent | Module-level chunk of the right file ranked 3 in the baseline, but the gold class chunk did not surface |
| Graph expansion | rescues | `get_embedder` reaches the results only via `ego_graph` (post-pool stage) |

No structural fix applies — both legs genuinely miss the paraphrase. The live pipeline's
ego-graph stage recovers a secondary gold, but pool_hit is measured on the fused
pre-expansion pool.

---

## Implications for the remaining tracks

1. **pool_hit ceiling = dense-leg recall@search_k.** Under current fusion parameters,
   no BM25-side change (Track A tokenizer, Track C k1/b, Track D path tokens) can move
   fused pool_hit. Track A/D gains *can* still move fused Recall@5/MRR by improving the
   BM25 ranks of overlapping candidates (RRF ordering), and they directly improve
   BM25-standalone quality.
2. **Track A/D gate adjustment**: judge primarily on BM25-standalone Recall@5/MRR on
   both golden sets, with fused metrics as a no-regression check — not as the primary
   signal (it is partially insensitive by construction).
3. **Recommended follow-up (out of Track B scope)**: guaranteed per-leg pool slots —
   reserve a small number of reranker-pool slots (e.g., 5) for top BM25-unique
   candidates and let the neural reranker judge them. This is the only cheap change
   that makes Q102-type queries poolable. It must be benchmarked on both golden sets
   before adoption (fused weights/rrf_k themselves are saturated per prior sweeps —
   this is a pool-membership change, not a weight change).

**Track B verdict**: expanded set stays at 0.9792 with 2 documented true misses; the
eval gate is clear for Tracks A/C/D with the adjusted gate above.

---

## Addendum (2026-07-26): Track I result — reserved slots do NOT rescue the misses

The follow-up recommended in item 3 was implemented (`bm25_reserved_slots` in
`SearchModeConfig`, reserve logic in `RRFReranker`) and swept at reserve ∈ {3, 5, 8}
on the expanded set with matched flags (`--with-centrality --centrality-alpha 0.0`,
whole tokenizer, INDEX_VERSION 3):

| Config | MRR | R@5 | hit@5 | pool_hit | misses |
|---|---|---|---|---|---|
| reserve=0 | 0.6517 | 0.6696 | 0.9583 | 0.9688 | Q102, Q103, Q122 |
| reserve=3 | 0.6611 | 0.6690 | 0.9479 | 0.9688 | Q102, Q103, Q122 |
| reserve=5 | 0.6495 | 0.6699 | 0.9583 | 0.9688 | Q102, Q103, Q122 |
| reserve=8 | 0.6757 | 0.6449 | 0.9479 | 0.9688 | Q102, Q103, Q122 |

The knob is confirmed live (88/96 queries had changed retrieved sets at reserve=8),
yet pool_hit never moves and the miss set is identical at every level. Conclusion:
the gold chunks for Q102/Q103/Q122 are absent from the BM25 leg's top-30 candidates
too — these are **dual-leg retrieval misses**, not fusion-membership artifacts.
Reserving pool slots cannot inject a candidate BM25 never retrieved. Ranking-metric
movement across reserve levels is within run noise, with reserve=8 showing the
predicted displacement cost (R@5 −0.025, hit@5 −0.010).

**Verdict**: default stays `bm25_reserved_slots = 0`. The wiring is kept as a
behavior-neutral experiment knob. The plausible fix for these queries shifts to
Track D (path/symbol tokens in BM25 documents), which raises BM25-leg recall itself
rather than re-allocating pool membership.

---

## Correction (2026-07-26, later): direct BM25-leg probe refines the Track I addendum

A read-only probe of the live index (whole tokenizer, 2,174 docs; `BM25Index.search`
at k=30, `min_score` 0.0 vs 0.1) corrects two statements above:

| Query | BM25 raw leg | leg after min_score=0.1 | raw score range | gold in BM25 top-30? |
|---|---|---|---|---|
| Q102 | 30 | 30 | 6.08–11.52 | **yes — rank 19, score 6.61** |
| Q103 | 30 | 30 | 5.53–11.77 | no |
| Q122 | 30 | 30 | 5.94–11.98 | no |

1. **Q102 is a fusion-cut miss, not a dual-leg miss.** Its gold chunk *is* in the
   whole-tokenizer BM25 top-30 (rank 19), but its RRF-fused rank falls below the
   top-30 pool cut (the dense leg lacks it), and reserve fill — which takes
   BM25-unique candidates in BM25 rank order — exhausts its slots on higher-ranked
   candidates before reaching rank 19. Q103/Q122 remain true dual-leg misses.
2. **The "knob is live: 88/96 retrieved sets changed" evidence was noise.** Retrieved
   sets differ 82/96 even between the reserve=3 and reserve=5 runs — GPU-reranker
   near-tie nondeterminism, not knob engagement. The knob *did* engage (each leg
   returns 30 raw candidates, so the fused union always exceeds the pool cut and the
   no-truncation guard in `_select_with_reserve` never fires; note `pool_size` in the
   benchmark is a post-dedup count and can read < 30 even when the raw pool is full),
   but per-query retrieved-set diffs across runs are not usable as evidence for it.
   The stable signal is the identical miss set at every reserve level.
3. `min_bm25_score = 0.1` is inert for real queries: raw Okapi scores sit at 5–12,
   so the filter removes nothing. Lowering it to 0.0 is a provable no-op.

The Track I verdict is unchanged (default stays 0), and Track D remains the plausible
fix for all three misses: Q103/Q122 golds need to *enter* the BM25 top-30; Q102's
needs to *climb* from rank 19.
