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
