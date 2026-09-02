# Graph-Hop Final-Pool Reserve Probe — GATE FAILED (2026-08-14)

**Verdict: NOT BUILT.** The `v4_graph_hop` reserve variant fails the pre-registered
stratified gate on both datasets. `graph_reserved_slots` is not implemented; the
Phase-5 campaign runs without a reserve arm.

## Context

A1's Track-A arm data (`evaluation/TRACK_A_AB_20260814.md`) showed graph-hop
candidates are the only channel reaching H034/H066-class golds, and A1's recorded
reopening condition was add-without-displacement at final pool assembly (A3).
This probe extends `scripts/benchmark/probe_final_pool_reserve.py` with a
provenance-preserving `v4_graph_hop` variant: candidates carrying
`source == "graph_hop"` in the multi-hop *merged* rerank pool, pool order
(all score 0.0 under the shipped default, so stable sort = discovery order),
top-3, simulated into the FINAL call's window under `_apply_hop1_reserve`
semantics (inject absent, evict same count from window tail).

Substrate: post-`9b2b917` corpus (A4 mechanism committed, disabled), 2,403
vectors, deterministic harness conventions (PYTHONHASHSEED=0,
CLAUDE_AUTO_REINDEX=0). Read-only — membership arithmetic, no reranker re-runs.

## Pre-registered gate (from the approved plan)

A rescue counts toward the build gate only if (a) `had_final_pass=False` for that
query (the merged output IS final — a merged-call-only build can deliver it), OR
(b) the build commits to also threading the reserve through the post-ego final
call sites (`hybrid_searcher.py`). Gate: **≥1 hard-miss gold rescued under (a),
zero gold evictions dataset-wide.** If rescues exist only under
`had_final_pass=True`, scope expands to (b) and the gate re-evaluates on the
full set.

Hard-miss membership targets (9 mrr=0 pool-misses on 133q):
Q101, Q106, Q117, Q122, H008, H034, H050, H054, H066.

## Results

### 133q expanded (`benchmark_results/probe_graph_hop_133q_20260814.json`)

| variant | any_rescue | miss_rescue | miss_rescue @ no-final-pass | collateral |
|---|---|---|---|---|
| v1_bm25_top3 | 8 | 3 (H034, H054, H063) | 0 | 3 |
| v2_dense_top3 | 7 | 1 (H034) | 0 | 2 |
| v3_merged_11_15 | 20 | 1 (H004) | 0 | 6 |
| v1_plus_v3 | 26 | 4 | 0 | 8 |
| **v4_graph_hop** | **4** | **2 (H004, H008)** | **0** | **4 (Q45, Q68, Q91, Q131)** |

- `had_final_pass=True` for **133/133 queries** — scope (a) is empty by
  construction on this substrate. A separate post-ego final rerank runs on every
  query, so a merged-call-only build could deliver nothing at all; any build
  would have to be scope (b).
- Under scope (b), v4 does rescue one hard-miss gold (H008
  `scripts/benchmark/run_sscg_benchmark.py:method:run_single`) plus H004 — but
  the zero-eviction half of the gate fails decisively: in-window golds are
  evicted on **5 queries** —
  - Q45 (hit): `search/incremental_indexer.py:class:IncrementalIndexer`
  - Q68 (hit): `mcp_server/tools/search_orchestrator.py:class:SearchOrchestrator`
  - Q91 (hit): `merkle/merkle_dag.py:class:MerkleDAG`
  - Q131 (hit): `search/index_write_stage.py:method:IndexWriteStage._inject_call_edges`
  - **Q121 (miss)**: `search/faiss_index.py:class:FaissVectorIndex` — its ONLY
    in-window gold (grade 3, window rank ~20). v4 would make the closest
    ranking-miss on the watch list strictly worse.
- Channel volume: mean 2.33 graph-hop injections/query (max 3, the cut);
  8/133 queries have no graph-hop candidates in the merged pool. The channel is
  ubiquitous, which is exactly why blind injection displaces so much: 125
  windows get 2-3 zero-evidence candidates each to buy 2 rescues.

### 63q canonical (`benchmark_results/probe_graph_hop_63q_20260814.json`)

v4_graph_hop: **0 rescues of any kind, 3 collateral** (Q45, Q68, Q91). The
guard-rail set (0 hard misses — nothing to rescue by construction) would be
actively harmed.

## Why this differs from the A1 evidence

A1's H034/H066 rescues came from *scored* graph-hop candidates competing on call
evidence — a selective signal. The reserve as probed is unscored (A1 was not
adopted; graph candidates carry literal 0.0), so "top-3 in discovery order" is
an evidence-free sample of a ~2.3-candidate/query channel. The probe confirms
the channel reaches hard-miss golds (H008 rescue), but without a ranking signal
inside the channel, the displacement cost dwarfs the rescue rate. Notably v4 did
NOT rescue H034/H066 here — the specific golds A1's scoring surfaced are not in
the channel's top-3 by discovery order.

## Disposition

- `graph_reserved_slots` NOT built; no reserve arm in the Phase-5 campaign.
- Probe variant `v4_graph_hop` + `pool_sources` provenance capture + the
  `had_final_pass` stratification stay in
  `scripts/benchmark/probe_final_pool_reserve.py` for future re-probes.
- Reopening condition (supersedes A3's): a reserve over the graph channel needs
  an *in-channel ranking signal* first — i.e. A1-style call-evidence scoring
  used only to ORDER the reserve source (not to compete in fusion), so the
  reserved 1-3 are evidence-bearing rather than discovery-order samples. Any
  such build must also handle the scope-(b) requirement (threading through the
  post-ego final call sites), since `had_final_pass=True` universally.
- The 2026-08-02 probe's V1-only reopening note is now stale on two counts:
  V1 shows 3 collateral on this substrate (was 0), and the no-final-pass
  stratum is empty — re-probe before designing ANY reserve lever.
