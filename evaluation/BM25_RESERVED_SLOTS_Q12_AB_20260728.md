# bm25_reserved_slots A/B — Q12 rescue attempt (2026-07-28)

**Verdict: FAIL — keep `bm25_reserved_slots = 0` (default unchanged).**

Reserved slots inject BM25-unique candidates at the hop-1 RRF fusion stage, but the
production pipeline (multi-hop → ego-graph → parent expansion) discards them before the
final reranker pool: Q12's `pool_hit` stayed **false in 9/9 sweep runs** across reserve
∈ {0, 3, 5}, while aggregate MRR fell 0.02–0.035 — outside the ±0.02 noise band at
reserve=5 and borderline at reserve=3. The knob as currently wired cannot rescue
fusion-cut misses on this pipeline, and it is not free.

Context: follow-up left by the 2026-07-28 golden-dataset repair
(`GOLDEN_DATASET_AUDIT_20260728.md`). Q12 ("check if index exists for project") is the
canonical boundary-riding fusion-cut miss — it still misses on the post-cleanup index
(baseline MRR ≈0.780, r1/r2 0.7825/0.7774), ruling out tmp/-pollution crowding.

## 1. Probe (`scripts/benchmark/probe_reserve_depth.py`)

Method: capture the final reranker pool at reserve=0 via
`reranking_engine.last_candidate_ids` (the same instrument `pool_hit` uses), get the raw
BM25 leg order, and per gold count the BM25-unique (not-in-pool) candidates ahead of it —
the minimal reserve that reaches it at the fusion stage.

Two probe iterations were needed; the discrepancy is itself a finding:

| Gold (Q12) | grade | v1 "bm25 rank" (pipeline-reshaped) | v2 raw-leg rank (true) | reserve needed (v2) |
|---|---|---|---|---|
| `status_handlers.py:…:handle_get_index_status` | 3 | not in top-60 | 42 | 39 |
| `snapshot_manager.py:…:SnapshotManager.has_snapshot` | 3 | 5 | **2** | **1** |
| `incremental_indexer.py:…:IncrementalIndexer.needs_reindex` | 3 | 9 | 20 | 18 |
| `metadata.py:…:MetadataStore.exists` | 2 | 21 | 21 | 19 |
| `index_handlers.py:…:handle_index_directory` | 1 | not in top-60 | not in top-200 | unreachable |

- **v1 gotcha (now documented in the probe):** `searcher.search(..., search_mode="bm25")`
  is *not* the raw BM25 leg — `multi_hop.enabled` gates before the mode branch
  (`hybrid_searcher.search`), so a bm25-mode top-level search still runs the full
  multi-hop/ego/parent pipeline and returns a reshaped, reranked list. The corrected
  probe calls `SearchExecutor.search_bm25` directly. Any historical per-leg probe that
  used top-level bm25-mode search shares this distortion.
- All 5 golds sat outside the fused pool at reserve=0 (pool 100% dense-sourced,
  consistent with `POOL_MISS_DIAGNOSIS.md`).
- On the true raw leg, `has_snapshot` (grade 3) needs only **reserve=1** at the fusion
  stage — so the swept arms {3, 5} were more than deep enough. The sweep therefore tests
  propagation, not depth.

## 2. Sweep — {0, 3, 5} × 3 runs, 63q, post-cleanup index

`run_sscg_benchmark.py --bm25-reserved-slots N` (in-memory override; result files
`benchmark_results/q12_reserve_{N}_r{1..3}.json`, not committed).

| arm | MRR (r1/r2/r3) | mean MRR | Δ vs control | R@5 mean | Q12 pool_hit | Q12 MRR |
|---|---|---|---|---|---|---|
| 0 (control) | 0.7829 / 0.7821 / 0.7864 | 0.7838 | — | 0.6075 | F/F/F | 0.000 |
| 3 | 0.7635 / 0.7618 / 0.7761 | 0.7671 | **−0.0167** | 0.6130 | F/F/F | 0.000 |
| 5 | 0.7400 / 0.7511 / 0.7574 | 0.7495 | **−0.0343** | 0.6178 | F/F/F | 0.000 |

Pass criteria: (a) Q12 pool_hit in ≥2/3 runs — **failed (0/9 across all arms)**;
(b) aggregates within ±0.02 — **failed at reserve=5, borderline at reserve=3**;
(c) no pool_hit flips on other queries — passed (no majority flips either direction).

Collateral damage concentrates in rank-1 slippage (mean MRR over 3 runs):
Q32 1.000→0.500 (reserve=3) / →0.333 (reserve=5); Q53 1.000→0.500 (both arms);
at reserve=5 additionally Q77 −0.333, Q99 −0.333, Q90 −0.167. R@5 ticked *up*
slightly (+0.005–0.010) — the reserve trades top-rank precision for tail recall, a bad
trade at these settings.

The expanded-set guard run was skipped: criteria (a) and (b) already failed on 63q.

## 3. Root cause — injection point vs measurement point

`_select_with_reserve` (`search/reranker.py:152–201`) operates inside
`rerank_simple`, i.e. at the **hop-1 fused list**. With the production config
(`multi_hop.enabled=true`, `ego_graph.enabled=true`, `single_pass=false`) the pipeline
then reshapes that list: multi-hop anchor selection → ego-graph neighbor expansion
(capped) → parent expansion → final `rerank_by_query` pass, whose input is what
`last_candidate_ids` / `pool_hit` measure. Tail-injected BM25 uniques do not survive the
reshaping — even a gold needing reserve=1 at the fusion stage never appeared in the final
pool. Meanwhile the injected candidates *do* perturb anchor selection and expansion,
which is where the Q32/Q53 rank-1 losses come from: the mechanism has cost without
delivery.

## 4. Decision and follow-ups

- **Keep `bm25_reserved_slots = 0`.** No config change. The comment block at
  `search/config.py:179–185` remains accurate ("0 = disabled").
- The real lever for fusion-cut misses would be reserving slots at the **final pool
  assembly** (input of the last `rerank_by_query` pass), not at hop-1 fusion — recorded
  as future work, out of scope here.
- Probe script kept as a committed diagnostic with the necessary-not-sufficient caveat
  baked into its docstring: a passing probe means "worth sweeping", never a predicted
  rescue.
- Q12 remains a known MISS; the remaining in-plan lever for it class-wide is Phase 3
  query expansion (different failure class, though — Q12 is fusion-cut, not vocabulary).
