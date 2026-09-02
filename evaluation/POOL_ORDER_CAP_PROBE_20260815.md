# Merged-Pool Ordering Campaign — `graph_hop_window_cap` Phase 1 probe — GATE PASSES (2026-08-15)

**Verdict: G1/G2/G3 all pass at cap=2 and cap=3. Phase 2b (default-off implementation) and Phase 3
(A/B) are authorized.** Headroom is thin (net +1 gold window-membership across 124 queries) — this
is a green light to build and measure, not a prediction of adoption. Honest adoption prior: ~20–35%.

## Context

Plan: `humming-wondering-phoenix` (follow-on session), executing reopening direction (b)
pre-registered in `evaluation/POOL_ORDER_AB_20260815.md` §Disposition: *"split the window budget
by channel with a low-dose `graph_hop` cap (N=3) rather than an all-or-nothing tier ordering."*
That A/B rejected `channel_priority` (breached 63q MRR/recall@5 guard-rails by driving `graph_hop`
window occupancy 7→0) and `score_reserve_fix` (statistically zero), but not the underlying
diagnosis: `RerankingEngine._order_merged_pool`'s `"score"` sort mixes three incommensurable
scales, and zero-signal `graph_hop` entries (literal score `0.0`) hold a median 3 window slots per
query regardless.

New mechanism `_apply_graph_hop_window_cap` (`search/reranking_engine.py`, added this session,
landed **inert** — no config field, no kwarg, no call site yet): after the `"score"` sort and
before `_apply_hop1_reserve`, a single stable pass caps how many `graph_hop` candidates occupy the
`top_k_candidates=30` window, deferring excess to just below the window so non-graph candidates
further back backfill the freed slots. Because every `graph_hop` candidate carries literal `0.0`,
"first `cap` admitted" = insertion order — the cap never compares scores across channels, unlike
`channel_priority`'s tiered reordering.

## Method

Read-only offline replay — no GPU, no live search, seconds. Reused the existing captured artifact
`evaluation/probe_rerank_window_20260815.json` (124-query non-D/F sweep, captured for the prior
`merged_pool_policy` probe against the same 209-file/2,446-chunk substrate) via the new `--replay`
mode added to `scripts/benchmark/probe_rerank_window.py` this session:

```
PYTHONHASHSEED=0 .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
    --replay evaluation/probe_rerank_window_20260815.json --caps 2,3
```

For each of the 124 records, `simulate_cap_windows()` replays the captured Pass-2 pool snapshot
(`pass2_call.pool`, pre-sort insertion order) through the **actual production statics**:
`RerankingEngine._order_merged_pool("score")` → `._apply_graph_hop_window_cap(cap)` →
`._apply_hop1_reserve("tail")`, for every `cap` in `SIMULATED_CAPS = (0, 2, 3, 4, 5)`. `cap=0` is
the no-op baseline (byte-identical to the deployed `"score"` policy) and is the comparison point
for every gold rescue/eviction delta. Reusing the production functions rather than reimplementing
them means a G3 mismatch could only indicate a stale pool snapshot, never simulator drift — it
did not occur.

## Pre-registered gate (fixed before this replay ran, per the originating plan)

- **G1 (headroom veto):** net gold window-membership change (golds gaining window membership minus
  golds losing it, summed over all 124 queries) must be **> 0** at the chosen cap; ≤ 0 at every cap
  → abort, stop the campaign.
- **G2 (named/general retention):** no gold in-window at `cap=0` may leave the window at the chosen
  cap — literally `gold_evictions == 0`.
- **G3 (self-validity):** the `cap=0` replay window must equal the observed production
  `pass2_window.window_ids` on every query, else halt (exit 3).
- Selection rule: chosen cap = smallest in `{2,3,4,5}` passing G1+G2 (prior expectation 3, per the
  reopening text). A secondary cap may be pre-registered for the A/B only if the replay shows a
  materially different membership profile, decided here before any GPU run.

## Results

| cap | queries w/ membership change | net graph-in-window Δ | gold rescues | gold evictions | net | G1 | G2 |
|---|---|---|---|---|---|---|---|
| 2 | 73 | −161 | 1 | 0 | **+1** | PASS | PASS |
| 3 | 73 | −127 | 1 | 0 | **+1** | PASS | PASS |
| 4 | 69 | −96 | 1 | 0 | **+1** | PASS | PASS |
| 5 | 66 | −75 | 1 | 0 | **+1** | PASS | PASS |

**G3 self-validity: 124/124 PASS.**

The single rescued gold at every cap is **Q04**'s
`chunking/multi_language_chunker.py:method:MultiLanguageChunker._create_chunk_id` (hop-1 rank 18,
base final rank 15 — Finding D: window promotion alone doesn't guarantee a listwise top-10 finish,
it's already inside base's top-10 window's neighborhood, not the interesting case; recorded for
completeness, not claimed as the campaign's justification).

### Named-gold survival (Q12 / H034 / H066)

| Gold | cap=0 | cap=2 | cap=3 | cap=4 | cap=5 |
|---|---|---|---|---|---|
| Q12 (`SnapshotManager.has_snapshot`, second gold) | in-window | in-window | in-window | in-window | in-window |
| Q12 (graph-sourced gold, `status_handlers.py` handler) | **not in-window** | not in-window | not in-window | not in-window | not in-window |
| H034 (`calculate_optimal_batch_size`) | in-window | in-window | in-window | in-window | in-window |
| H066 (`HybridSearcher.get_stats`) | **not in-window** | not in-window | not in-window | not in-window | not in-window |

Exactly as the design-phase replay (this plan's write-up) predicted: Q12's graph-sourced gold is
unreachable by construction (45 positive-scored candidates fill the window before the scan reaches
the `0.0` graph block, at every cap tested — capping doesn't change *which* graph entries are first
in insertion order, only how many survive), H034 stays in-window throughout, and H066's exclusion
is reserve-driven (Finding E: `_apply_hop1_reserve`'s blind tail eviction), not scale-mixing — the
cap doesn't touch it. None of the three named golds move at any cap. The upside case, if any, is
aggregate window reclamation for the 133q set's broader H-category queries — not named-miss rescue.

## Gate evaluation

**G1: PASS at every cap.** **G2: PASS at every cap** (zero gold evictions, all four). **G3: PASS**
(124/124). The gate does not discriminate between cap=2 and cap=3 on gold-headroom terms — both
clear identically (net +1, 0 evictions) despite reclaiming very different volumes of zero-signal
window slots (−161 vs −127 graph admissions). Per the pre-registered selection rule, chosen cap =
**2** (smallest passing). Per the plan's explicit fallback ("a single secondary cap may be
pre-registered... if the replay shows a materially different membership profile"), **cap=3** is
promoted to a pre-registered secondary for the A/B: the membership-change footprint is close
(73 vs 73 queries changed) but the graph-admission volume differs by 27% (−161 vs −127), and cap=3
is the dose named in the originating reopening text. No selection rule was substituted after
seeing the numbers — both branches were written into the plan before this replay ran.

**Overall: GATE PASSES.** Proceeding to Phase 2b (default-off implementation).

## Phase 3 A/B gate (pre-registered here, before any GPU run)

7 runs mirroring `POOL_ORDER_AB_20260815.md` §Method: fresh force-reindex first (implementation
touches indexed source — substrate-drift rule), `PYTHONHASHSEED=0`, `CLAUDE_AUTO_REINDEX=0`,
`--set intent.enabled=true` on every arm — `base_63q_r1`, `base_63q_r2` (byte-identity determinism
check), `base_133q_r1`, `cap2_63q`, `cap2_133q` (`--set reranker.graph_hop_window_cap=2`),
`cap3_63q`, `cap3_133q` (`--set reranker.graph_hop_window_cap=3`).

- **Upside:** 133q paired 95% CI (10,000-resample bootstrap, seed 0, vs the matching base arm)
  excludes zero positively on recall@10 or recall@20, with the other's point estimate ≥ 0.
- **Guard-rails (any breach disqualifies that arm):** MRR CI must not exclude zero on the loss side
  on either set; 63q recall@5 and recall@10 named; `pool_hit_rate` drop > 0.02; |latency Δ| > 100
  ms/query unexplained.
- **Risk check (reported regardless of verdict):** Q12/H034/H066 — this replay predicts no
  movement for any of the three at either arm cap; live disagreement means substrate drift, flag
  it, do not silently attribute it to the cap. H034/H066 carry `source="hybrid"` in the captured
  pools, not literal `graph_hop` — their sensitivity is to the shared window budget, not graph
  provenance specifically (same caveat as the prior A/B's Risk #4).
- **Adopt** (flip the default for whichever arm — cap2 or cap3 — clears the gate; if both clear,
  prefer the smaller cap per the same "smallest sufficient dose" principle used here) or **reject**
  (both stay default-off; lock `reranker.graph_hop_window_cap` in `FORBIDDEN_AUTO_TUNE_KEYS` +
  `BENCHMARK_LOCK_CITATIONS`). Either way: `evaluation/POOL_ORDER_CAP_AB_<date>.md`, committed.

## Disposition

- **Code landed this session stays inert until Phase 2b.** `_apply_graph_hop_window_cap` exists in
  `search/reranking_engine.py` but has no config field, no `rerank_by_query` kwarg, and no call
  site — unreachable at runtime, verified by the absence of any wiring change in this commit.
- **Next step:** Phase 2b — `RerankerConfig.graph_hop_window_cap` field (default 0), kwarg
  threading through `rerank_by_query` and the Pass-2 call site only, unit tests, green
  `tests/unit/search/ -x -q`, commit. Then Phase 3 per the gate above.
