# Retrieval state after the 2026-11-22 work

## State

- done: IVF path removed (new indexes always flat, load-time IVF->flat migration kept);
  MDE column in `--compare`; label audit (11 label fixes); 60 commit-mined golden queries
  (expanded set 133 -> 193); canon re-pinned. All pushed: `origin/development` `cb5b7ad6`, CI green.
- closed: e-means (rejected), reranker-input replay (candidate 3, no gain), Qwen3-Reranker-4B
  probe (candidate 4, excluded by the owner).
- next: no item planned. The only open direction is ranking inside the candidate pool (see
  "Where the room is"). Measure the MDE of the 193q set before the next A/B.
- blocked: none

## Commits

| SHA | Change |
|---|---|
| `ae0feb7e` | Flat-only new indexes; ADR-0083 addendum |
| `c0fed925` | Golden label audit; canon `CANON_20261122_LABEL_AUDIT.md` |
| `1050b3c0` | `test_mcp_eval_regression` baselines re-pinned for the labels |
| `9df523ac` | Probe scripts (`probe_eval_power.py`, `probe_emeans_ivf.py`, `probe_flat_vs_ivf.py`, `probe_rerank_order.py`) and the deep-research prompt |
| `92e71efb` | `run_sscg_benchmark.py --compare` prints the minimum detectable effect (MDE = 2.80 x SE) |
| `acce60b1` | IVF index path removed; `_migrate_ivf_to_flat` converts old indexes on load |
| `a42f1300` | Type-check guard on the migration when faiss is absent |
| `a7877d5c` | H100-H159 added to `golden_dataset_expanded.json`; canon `CANON_20261122B_H_EXPANSION.md` |
| `cb5b7ad6` | Test ids on the migration parametrize (test-smell ratchet) |

## Index change: flat only

- New indexes are always `IndexFlatIP` (exact). An old IVF index converts to flat on load and is
  saved as flat on the next save.
- twozero-dev (63,311 chunks) and TD_Glossary_tox (53,918) were rebuilt as flat. No IVF index is
  left on this machine.
- Measured on the 63K corpus, 8 threads: flat p50/p95 17.1 / 32.6 ms, IVF 17.4 / 20.6 ms. Build:
  flat 0.09 s, IVF 2.26 s. The reranker dominates search time, so the p95 gap does not matter.

## Evaluation changes

- **Label audit.** The rank-1 chunks of every query were reviewed. Labels added at grade 3:
  Q34, Q55, Q114, Q117, Q128, H003, H032, H064, H066. Set to grade 0: Q04
  `validate_index_consistency`, Q117 `_encode`. Effect on the same index: 133q MRR
  0.6718 -> 0.7162 (+0.044). The code did not change; the old labels missed valid answers.
- **60 new H queries (H100-H159).** Mined from fix / feat / perf commits 2026-08-01..11-22,
  labelled against the code at HEAD, then reworded at symptom level (a developer who does not know
  the fix). Rank 1 fell from 40 / 60 (fix wording) to 31 / 60. H108, H124 and H129 stay more
  specific so each keeps one clear answer. One label added in the rewrite (H125, grade 2). Drafts,
  old wording and 27 reserve queries: `evaluation/commit_mined_candidates_20261122.json` (local).

## Current canon (`evaluation/CANON_20261122B_H_EXPANSION.md`, HEAD `a42f1300`, 3,402 chunks)

| View | Queries | MRR | Recall@20 | pool_hit_rate |
|---|---|---|---|---|
| Main set (`golden_dataset.json`) | 63 | **0.8425** | 0.8270 | 1.0000 |
| Expanded (`golden_dataset_expanded.json`) | 193 | **0.7054** | 0.8214 | 0.9585 |
| F-via-similar | 63 | **0.8935** | 0.8255 | 1.0000 |

- 63q r1 == r2: 63 / 63 lists identical.
- The 60 new queries alone: MRR 0.6785, pool_hit 57 / 60.
- 63q recall@20 is 0.0269 below the first 11-22 pin (band -0.02). Recorded as reindex drift: 12
  queries moved in both directions, the two big losses are sibling swaps in "similar to X"
  queries (Q70, Q94), and the old 133 queries changed by only +0.0013 MRR.

## Statistical power

- sigma_d (SD of per-query paired MRR differences) from stored A/Bs: 0.063-0.071 for reranker and
  model A/Bs, 0.115-0.173 for chunking A/Bs.
- MDE on MRR: 133q about 0.016-0.017 (usable as a gate); 63q 0.022 or more (a guard only, not a
  detector). Only 16-24 of 133 queries move per typical A/B.
- The 193q MDE is not measured yet. Run `scripts/benchmark/probe_eval_power.py` on the next
  paired A/B to get it.

## Where the room is

| Measure | 133q (before expansion) | 63q |
|---|---|---|
| pool_hit_rate | 0.962 | 1.000 |
| hit@1 | 0.647 | 0.841 |
| Gold in pool, not at rank 1 | 42 | 10 |
| Gold not in pool | 5 | 0 |

The gold is almost always in the candidate pool. Changes that add candidates to the pool cannot
help much; the gap is in final ranking.

## Closed or rejected (do not re-run without a new mechanism)

- **e-means** (arXiv 2611.09501, faiss `contrib/e_means`). It replaces only IVF centroid training.
  On the 63K and 54K corpora: objective 2-4% lower, recall at production nprobe and training time
  unchanged. Flat search makes it moot. Re-check only for one index of about 1M vectors.
- **Reranker-input replay (deep-research candidate 3).** The path + qualified-name header already
  exists (`_build_rerank_document`), the size cap was swept in ADR-0011 (1,000 chars deployed),
  depth 30 vs 50 was swept, and no input order beat the fused order (`probe_rerank_order.py`;
  reordering alone moves MRR about +-0.02, the noise floor).
- **Qwen3-Reranker-4B probe (candidate 4).** Excluded by the owner.

## Rules for the next A/B

- Run control and treatment legs in one session on one index. A reindex rebuilds the call graph
  and reorders heads through centrality: only 19 / 133 lists were identical after today's reindex.
- Export `CLAUDE_AUTO_REINDEX=0` and `PYTHONHASHSEED=0` for every leg.
- Use the 193q set as the gate and the 63q set as a guard; read the MDE column in `--compare`.

## Next action

The owner chooses whether to open a ranking-side study (the 42 in-pool, not-rank-1 queries).
Nothing is scheduled.
