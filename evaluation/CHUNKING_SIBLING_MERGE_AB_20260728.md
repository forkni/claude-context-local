# A/B: Sibling-Boundary Greedy Merge (63/354) vs Merge-Off Baseline

**Date**: 2026-07-28
**Verdict**: **NEUTRAL — DO NOT ADOPT NOW** (MRR flat within ±0.02 noise gate; consistent
but modest recall gains; adoption deferred as a user decision because it requires an
`INDEX_VERSION` bump and a forced full reindex for every user)

---

## 1. Verdict Detail

| Criterion | Result |
|-----------|--------|
| Primary gate (MRR, ±0.02 noise band) | −0.008 → **flat** (neither adopt nor reject signal) |
| Recall@5 / @10 / @20 | +0.030 / +0.028 / +0.021 → consistent gains, both runs above every baseline run |
| Miss set | Identical across arms (Q12, Q56-flaky, Q99) — no new misses, none fixed |
| Index size | 2,317 → 1,941 chunks (−16.2%), 177 merged chunks |
| Live config | Restored to merge-off; index rebuilt to baseline shape (2,316 chunks, 0 merged) |

The recall gains are real but partly definitional: containment-credit scoring lets one
merged chunk credit several golden symbols at a single rank. From the user's perspective
this is a genuine success (the retrieved chunk contains the target code), but it inflates
recall@k relative to a per-symbol retrieval reading. MRR — which containment credit also
benefits — stayed flat, so sibling merge does not improve *ranking*; it packs more target
material per returned result.

**Recommendation**: keep merge off for now. Revisit if a future change targets recall@k
specifically (e.g., agent workflows consuming k≥5 results), where +0.02–0.03 recall and a
16% smaller index would justify the reindex cost.

## 2. Motivation

The community-boundary merge A/B (`evaluation/CHUNKING_MERGE_AB_20260728.md`) was
rejected with strict MRR −0.090, but root-caused as mostly a scorer artifact: merged
chunks (`type=merged`, named after one representative member) could never match golden
`file:type:name` IDs. Per user direction the workstream pivoted to tuning chunking itself
with a fair scorer. This A/B is the first fair-scored chunking experiment, testing the
**sibling boundary** (merge small same-class siblings by `parent_class`, ignoring Louvain
community assignment) with calibrated budgets.

Prerequisites landed before this A/B (all unit-tested, 3,558 unit tests green):

1. **Containment-credit scoring** (`evaluation/metrics.py`): merged chunks persist a
   qualified `merged_from` member list (`Class.method` / `function`); the scorer expands a
   retrieved merged chunk into the set of golden IDs it absorbed. Provably a no-op on a
   merge-free index (verified: baseline run with the new scorer printed no containment
   line and scored MRR 0.7371, inside the historical band).
2. **`_create_merged_chunk` ordering fix** (`chunking/languages/base.py`): members are
   sorted by source position before merging — previously `module_preamble` was emitted
   last, producing inverted line ranges in 2/114 merged chunks.
3. **Sibling-merge config gate** (`merge_boundary: "community" | "sibling"` in
   `ChunkingConfig`; plumbed through `remerge_chunks_with_communities`
   `use_community_boundary` down to the greedy merger).

## 3. Protocol

- **Golden set**: `evaluation/golden_dataset.json` — 77 queries, 63 scored (category D
  excluded). Embedder: F2LLM-v2-0.6B. Reranker: jina-reranker-v3. Noise band: ±0.02 MRR.
- **Baseline arm** (merge off, live config): ×3 replicates on the 2,317-chunk index
  (`sscg_merge_off_baseline_20260728_142030/142536`, `sscg_containment_noop_check_20260728_151757`).
  The first two ran before the scorer change; on a merge-free index the new scorer is
  byte-identical (unit-tested + verified by replicate 3), so all three are comparable.
- **Treatment arm**: `search_config.json` chunking block set to
  `enable_community_merge: true`, `merge_boundary: "sibling"`, `min_chunk_tokens: 63`,
  `max_merged_tokens: 354` (whitespace tokens; ≈150/840 real F2LLM tokens at the measured
  1:2.369 calibration). Full non-incremental reindex (`tools/batch_index.py --mode force`,
  40.5 s) → 1,941 chunks, 177 merged, all with `merged_from` provenance. ×2 replicates
  (`sscg_sibling_merge_63_354_r1/r2_20260728`). Containment credit active: 22–23 of 63
  queries received credit per run.
- **Restore**: config restored byte-identical from backup (verified with `cmp`), full
  force reindex back to 2,316 chunks / 0 merged, sanity search green.

## 4. Results

Mean over replicates (baseline n=3, treatment n=2):

| Metric | Baseline (merge off) | Sibling 63/354 | Δ |
|--------|----------------------|----------------|---|
| **MRR** | **0.7302** (0.7236 / 0.7300 / 0.7371) | **0.7226** (0.7148 / 0.7303) | **−0.008** |
| recall@1 | 0.2413 | 0.2657 | +0.024 |
| recall@5 | 0.5668 | 0.5963 | +0.030 |
| recall@7 | 0.6626 | 0.6749 | +0.012 |
| recall@10 | 0.7113 | 0.7396 | +0.028 |
| recall@20 | 0.7604 | 0.7813 | +0.021 |
| recall@50 | 0.7629 | 0.7826 | +0.020 |
| nDCG@5 | 0.5809 | 0.5824 | +0.002 |
| hit_rate@5 | 0.9365 | 0.9524 | +0.016 |
| pool_hit_rate | 0.9841 | 0.9762 | −0.008 |
| avg pool size | 30.6 | 29.4 | −1.2 |
| index chunks | 2,317 | 1,941 (177 merged) | −16.2% |

Directional consistency: both treatment runs beat all three baseline runs on recall@5,
@10, @20, @50, and hit_rate@5. MRR replicates straddle the baseline band (0.7148 below,
0.7303 inside), and the treatment spread (0.0155) is comparable to the baseline spread
(0.0135) — the −0.008 delta is indistinguishable from run noise.

## 5. Miss-Set Analysis

Zero-MRR queries are the same in both arms:

- **Q12** "check if index exists for project" — pool miss in every run of both arms (the
  only systematic pool miss; pre-existing, unrelated to merging).
- **Q56** "what does CodeIndexManager orchestrate…" — flaky in both arms (hit in 1 of 3
  baseline runs and 1 of 2 treatment runs).
- **Q99** "find save and restore implementations…" — ranking miss in both arms; in
  treatment r2 it additionally fell out of the candidate pool (the sole cause of the
  pool_hit_rate dip to 0.9683 in that run).

Largest per-query movement (treatment mean vs baseline r3, |Δ| ≥ 0.15): 5 down
(Q90 −0.67, Q05 −0.50, Q71 −0.50, Q77 −0.25, Q48 −0.17), 4 up (Q81 +0.50, Q56 +0.25,
Q95 +0.17, Q55 +0.17). Balanced churn with no category pattern — consistent with
rank-order noise from a re-embedded index rather than a systematic effect. Notably Q05
("normalize file path separators") received containment credit for its target
(`normalize_path` inside a merged chunk) yet still slipped to rank 2 — the merged chunk's
blended embedding ranked slightly lower than the standalone function did.

## 6. Follow-Ups

- Adoption decision is the user's call: gains are recall-side and index-size-side, not
  ranking-side. If adopted, `INDEX_VERSION` must be bumped (silent quality degradation
  otherwise — merged chunks require the containment-aware scorer for fair evaluation and
  a full non-incremental reindex).
- Community-boundary merge defect (stored community map not re-keyed post-merge) remains
  a deferred fix from the previous A/B; it is orthogonal to the sibling boundary (which
  ignores community assignment) but would matter for any community-boundary retry.
- Q12 pool miss and Q99 ranking miss are pre-existing baseline failures worth their own
  investigation (both survive every configuration tested to date).
