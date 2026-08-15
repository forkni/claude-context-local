# Leg-Search-Depth × Fusion Probe — BOTH GATES PASSED, screening only (2026-08-14)

**Verdict: SCREENING GATE PASSED, NOT BUILT.** Both pre-registered gates clear their
thresholds on freshly re-pinned substrate: widening leg-search depth to 200 is a real
gold-membership lever on its own (Gate A), and TM2C2 α=0.8 reopens as a distinct lever
at the deployed depth (Gate B). Per the approved plan's scope decision ("probe first,
gate, then decide"), **Phase 2 (build) does not start** without explicit user go-ahead —
this note is the Phase 1 stop-and-report, not a build.

## Context

Follow-up to the closed TM2C2 fusion probe (`evaluation/TM2C2_FUSION_PROBE_20260814.md`),
which found zero gold-membership change on both datasets at both α, root-caused to
**depth, not arithmetic**: the plan's named exemplar (Q121, dense rank 84 / BM25 rank 80 /
RRF fused rank 41) came from an earlier probe run at depth 200, but the closed probe
replayed the leg-search formula (`search_k = max(reranker.top_k_candidates, k*5)`,
`search_executor.py:130`) at the top-level `k=10` it was given (search_k=50) — too
shallow for Q121 to appear on either leg at all. This probe (`scripts/benchmark/probe_leg_depth_fusion.py`)
tests leg-search depth as its own lever, independent of fusion function, per the closed
probe's reopening condition.

## Depth-50-vs-100 correction (found while building this probe, validated below)

`search_k=50` is not what a default query actually experiences. `multi_hop.enabled=True`
by default, and `MultiHopSearcher.search()` substitutes hop-1's request `k` with
`initial_k = k * multi_hop.initial_k_multiplier` (default 2.0) before calling the
single-hop leg — a top-level `k=10` query's hop-1 stage runs at k=20, giving
`search_k = max(30, 20*5) = 100`. **Depth 100 is the true deployed default-path reference
cell**, not depth 50 (50 is only what a direct single-hop-mode call would see). This
probe treats depth 50 as a diagnostic floor only, depth 100 as the reference, depth 200
as the widening arm under test — matching the closed probe's original (deeper) exemplar.

## Substrate (Phase 0 re-pin)

Corpus drifted again since the TM2C2 probe's own B0 pin (2,406 → 2,429 chunks, this
session's new files under indexed paths). Fresh r1 captured for both datasets and used
as this campaign's reference, superseding `benchmark_results/tm2c2/b0_pin_*`:

| Dataset | MRR | pool_hit_rate | recall@10 | recall@20 |
|---|---|---|---|---|
| 63q (`benchmark_results/leg_depth/pin0_63q_r1.json`) | 0.8461 | 1.0 | 0.78 | 0.8458 |
| 133q (`benchmark_results/leg_depth/pin0_133q_r1.json`) | 0.6649 | 0.9474 | 0.7646 | 0.8267 |

Small MRR move vs the TM2C2 b0 pin (63q 0.8516→0.8461, 133q 0.6713→0.6649), pool_hit up
on both — within the substrate-drift noise band this project already documents; not
attributed to any code change (none made).

Re-derived hard-miss cohort (133q, mrr=0.0), **supersedes the TM2C2 probe's list**:
Q101, Q103, Q117, Q122, H008, H021, H050, H054, H066. H021 is newly a miss; Q106 dropped
out. Hard-miss set is substrate-dependent — always re-derive, per standing project rule.

## Fidelity check (pre-registered, run before trusting any depth delta)

Compared this probe's offline depth-100/RRF cut-30 replay against the live
`"[NEURAL_RERANK-SEARCH]"`-tagged hop-1 rerank call's `candidate_ids`, as sets, on a
10-query sample (Q01, Q04, Q05, Q07, Q12, Q16, Q19, Q20, Q31, Q32) per dataset.

**PASSED on both datasets, 0 mismatches** — the offline replay is set-identical to what
production actually assembles for hop-1 at the deployed depth. Depth deltas below are
trustworthy.

## Pre-registered gates

### Gate A — depth is a lever on its own

*Some depth d ∈ {100, 200} under RRF yields net gold-membership gain ≥ +1 on 133q AND
net ≥ 0 on 63q, vs the depth-100 reference.* (Depth 50 is diagnostic-only, excluded from
the gate by pre-registration; depth 100 is the reference and trivially nets 0 against
itself.)

| depth | dataset | rescued | evicted | net | Q121-class rescues |
|---|---|---|---|---|---|
| 200 | 133q | 9 | 6 | **+3** | 2 |
| 200 | 63q | 5 | 2 | **+3** | 0 |

**PASSES**: +3 ≥ +1 on 133q, +3 ≥ 0 on 63q.

### Gate B — TM2C2 reopens at depth

*At some depth d ∈ {100, 200}, TM2C2 (either α) beats RRF at that same depth by ≥ +1 net
gold membership on 133q, including ≥ 1 Q121-class rescue.*

| depth | arm | dataset | rescued | evicted | net | Q121-class rescues |
|---|---|---|---|---|---|---|
| 100 | tm2c2_0.65 | 133q | 4 | 11 | −7 | 3 |
| 100 | **tm2c2_0.8** | 133q | 6 | 3 | **+3** | **2** |
| 200 | tm2c2_0.65 | 133q | 7 | 19 | −12 | 3 |
| 200 | tm2c2_0.8 | 133q | 6 | 8 | −2 | 3 |
| 100 | tm2c2_0.8 | 63q (context) | 4 | 0 | +4 | 1 |

**PASSES at depth=100 (the deployed default depth), α=0.8 only**: +3 ≥ +1, 2 ≥ 1
Q121-class rescues. **α=0.65 fails badly everywhere it's tested** (net −4 to −12 both
datasets, both depths) — this is not a probe no-op, the arithmetic differs consistently,
it's just the wrong α. Only α=0.8 clears the gate; α=0.65 stays rejected.

## Named exemplar (Q121) reproduces, with a caveat

At depth 100, Q121's grade-3 gold (`search/faiss_index.py:class:FaissVectorIndex`, dense
rank 80 / BM25 rank 81) sits at RRF cut rank **29** — already just inside the cut-30. At
depth 200 it's pushed to rank **None** (evicted — more cross-leg competition floods in).
Simultaneously, Q121's grade-2 gold (`search/indexer.py:class:CodeIndexManager`,
BM25-invisible entirely at depth 100) becomes visible at depth 200 (BM25 rank 107) and
enters the cut at RRF rank **18** — a genuine "depth-bounded, now reachable" rescue,
exactly the mechanism this probe was built to find.

**This is a swap, not a pure gain**, for this specific query: one gold in, a
higher-graded one out. It illustrates the pre-registered conversion hazard explicitly:
pool-membership gain has historically not guaranteed end-metric gain on this pipeline
(`bm25_reserved_slots` and `hop1_reserved_slots` precedents). A screening-gate pass is
"worth a real A/B", never a predicted MRR/recall win — Phase 2, if approved, must gate on
recall@10/20 confidence intervals, not on this probe's membership counts.

## Leg saturation / latency

| depth | mean_bm25_len | mean_dense_len | bm25_sat_frac | bm25_ms | dense_ms | dataset |
|---|---|---|---|---|---|---|
| 50 | 49.7 | 50.0 | 0.02 | 4.8 | 63.0 | 133q |
| 100 | 98.3 | 100.0 | 0.03 | 4.8 | 10.0 | 133q |
| 200 | 191.9 | 200.0 | 0.12 | 4.9 | 18.3 | 133q |
| 50 | 49.2 | 50.0 | 0.04 | 3.8 | 72.7 | 63q |
| 100 | 96.0 | 100.0 | 0.07 | 3.7 | 9.6 | 63q |
| 200 | 182.1 | 200.0 | 0.22 | 3.6 | 19.8 | 63q |

BM25 leg saturates (returns short of the requested depth via the `min_bm25_score=0.1`
floor) on up to 22% of queries at depth 200 — real but modest; BM25 wall-clock is flat
regardless of depth (~4-5ms). Dense leg wall-clock roughly doubles from depth 100→200
(~10ms → ~19ms per query) — this is the priced-in latency debit if depth widening ships.
(The depth-50 dense-ms figures, 63-73ms, are noisy first-call/cold-cache artifacts, not a
real depth-50-vs-100 latency signal — depth 50 is diagnostic-only and excluded from both
gates.)

## Disposition

- **Both gates PASSED** on freshly re-pinned substrate: Gate A (depth=200, RRF) and Gate
  B (depth=100/deployed depth, TM2C2 α=0.8 only). Per the plan's outcome matrix ("A and B
  → build depth first, TM2C2 as a second arm, they must not be confounded in one A/B"),
  this is the outcome that was reached.
- **No production code touched.** `search_executor.py`, `search/config.py`,
  `search/reranker.py` all unmodified. `scripts/benchmark/probe_leg_depth_fusion.py`
  stays in-tree, uncommitted, as the reference implementation.
- **STOPPING HERE per plan scope** ("probe first, gate, then decide"). Phase 2 (build)
  is written in the approved plan but explicitly gated — it does not start without
  explicit user go-ahead.
- **Open build-parameter question for Phase 2, if approved**: the plan's drafted default
  `leg_search_multiplier: int = 5` reproduces today's depth-100 behavior byte-identically
  (`max(30, 20*5) = 100`— no default change). Gate A's passing arm is depth **200**,
  which needs multiplier=**10** at hop-1's k=20 (`max(30, 20*10) = 200`) — Phase 2 must
  treat the multiplier value itself as the swept A/B variable, not assume 5 rescues
  anything; default stays 5 unless adopted.
- **Q121 exemplar reproduces but as a swap, not a pure win** (see above) — flagged
  explicitly so Phase 2's adoption gate is read on recall@10/20 CIs, not on this probe's
  raw membership deltas.
- Reopening condition for anything not adopted here: none needed yet — this is a passed
  screening gate awaiting the user's build decision, not a closed/rejected lever.
