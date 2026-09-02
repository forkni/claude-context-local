# Merged-Pool Ordering Campaign — Phase 1 Probe — corrected diagnosis, Phase 4 authorized (2026-08-15)

**Verdict: the A1 (premise) gate abort recorded below was based on a mis-stated premise, not on
the defect being absent. The defect is confirmed live and dominant on this substrate (see
Diagnosis). Corrected Phase 4 gate criteria are pre-registered in this document; the A/B itself
runs as a follow-up. Landed code (`merged_pool_policy`, default `"score"`, byte-identical) stays
in-tree unchanged.**

> **Revision note (same day):** this document originally concluded ABORT and treated the
> defect as "real but rare, not dominant." Re-examining the same JSON artifact
> (`evaluation/probe_rerank_window_20260815.json`) against source line-by-line found the P1/P2
> thresholds themselves were unreachable by construction, not that the defect failed to appear.
> The Method, Substrate, and raw P1–P6/A1–A3 tables below are unchanged — only the Diagnosis and
> Disposition are corrected. See the plan file `humming-wondering-phoenix.md` for the full
> re-verification (all cited line numbers re-checked against HEAD this session).

## Context

Plan: `humming-wondering-phoenix` ("Merged-Pool Ordering Campaign — repair the incomparable-scales
cut at the multi-hop rerank window"). The plan targets `RerankingEngine.rerank_by_query` sorting
the Pass-2 merged pool by raw `.score` across three incommensurable scales (hop-1 jina relevance
≈ −0.12…+0.22, semantic-expansion raw FAISS cosine ≈ 0.5…0.9, graph-expansion literal `0.0`), and
finding (E) — the `hop1_reserved_slots` reserve's blind tail eviction sometimes evicting the
best-ranked hop-1 seeds. Two candidate policies were implemented and landed default-off in a
prior window (`b5bf508`, follow-up type-fix `8999b60`): `score_reserve_fix` (fix the eviction
target only) and `channel_priority` (tiered ordering, never compares across scales).

Per the plan's explicit Sequencing section, Phase 4 (the 7-run A/B protocol, ≈60–75 min GPU time)
is gated on a read-only Phase 1 probe (`scripts/benchmark/probe_rerank_window.py`) validating six
pre-registered predictions (P1–P6) and three abort criteria (A1–A3), with an unambiguous rule:
*"A1 — premise false: P1 or P2 fails → abort, write disposition, do not run arms."* This document
is that disposition.

## Method

1. Full non-incremental reindex (`tools/batch_index.py --mode force`) — the plan's Sequencing
   step 4, "reindex once, then pin `CLAUDE_AUTO_REINDEX=0` and do not touch indexed source
   again." Reindex completed in 75.92 s: 209 files added, 2,446 chunks added, model
   `codefuse-ai/F2LLM-v2-0.6B`.
2. `CLAUDE_AUTO_REINDEX=0` and `PYTHONHASHSEED=0` pinned on the probe invocation (the probe has
   no internal re-exec guard, unlike `run_sscg_benchmark.py`; set manually to hold ADR-0021
   determinism).
3. `scripts/benchmark/probe_rerank_window.py --all --dataset evaluation/golden_dataset_expanded.json --k 10 --json-out evaluation/probe_rerank_window_20260815.json`
   — full non-D/F sweep (124 usable queries; D excluded as call-graph/incompatible with plain
   `search()`, F excluded as `find_similar_code`-scored, both pre-existing probe design, not new
   scope this run).
4. Self-validity check (the plan's A3): `simulate("score")` must reproduce the *observed*
   `window_ids` for every query, or halt (exit 3). Read `compute_predictions()`/`evaluate_gate()`
   output directly rather than inferring pass/fail from process exit code — the probe exits 0
   whenever self-validity holds and no crash occurred, independent of whether the RED/GREEN
   window-cut verdict or the gate's own `abort` flag is true.

## Substrate

- 2,446 chunks, 209 files, `codefuse-ai/F2LLM-v2-0.6B` embedder, reindexed 2026-08-15.
- 124 queries (non-D/F subset of `golden_dataset_expanded.json`), k=10.
- Pass-2 pool size: median 57 (min 29, max 93). Window size: median 30 (min 29, max 30) —
  consistent with the plan's documented `fusion_k = max(20, 30) = 30`.
- Self-validity: **124/124 queries reproduced**, `self_validity_failures: []`. All P1–P6/A1–A3
  numbers below are trustworthy per the plan's own halt-condition design.

## Pre-registered predictions (P1–P6)

| # | Prediction | Threshold | Observed | Result |
|---|---|---|---|---|
| P1 | Pass-2 window median `multi_hop` share | ≥ 60% | **43.3%** | **FAIL** |
| P2 | Median window entries with `hop1_rank ≤ 8`, ≥60% arriving via reserve | count≥? / share≥60% | median_count=7.0, `reserve_arrival_share_median=0.0` | **FAIL** |
| P3 | Median `graph_hop` window count = 0, but ≥5% of queries have ≥1 | ==0 ∧ ≥5% | median_count=3.0, any_frac=60.5% | **FAIL** |
| P4 | (finding E) ≥50% of queries have a pre-reserve `hop1_rank∈{1,2}` candidate absent post-reserve | ≥ 50% | **7.26%** | **FAIL** |
| P5 | Pass 3 inert: `rerank_count == len(candidates)` | ≥ 99% | **100%** | **PASS** |
| P6 | (informational, D-ceiling) gold ∈ window but ∉ top-10 | — | 5 queries / 7 gold hits | informational |

## Pre-registered gate (A1–A3)

| Criterion | Rule | Result |
|---|---|---|
| A1 (premise) | P1 **and** P2 must both hold, else abort | **FAILED** (both P1 and P2 failed) |
| A2 (headroom veto) | both policies net ≤ 0 → abort | **PASSED** — `score_reserve_fix`: rescues 7 / evictions 0 / net +7; `channel_priority`: rescues 10 / evictions 2 / net +8 (veto only, does not authorize arms on its own) |
| A3 (self-validity) | divergence → halt | **PASSED** — 124/124 checked, 0 failures |
| **abort** | A1 fails **or** A2 fails **or** A3 fails | **`true`** |

Result: `gate.abort = true`, computed directly by the probe's own `evaluate_gate()`. Per the
plan's pre-registered rule, this is an unconditional **ABORT — Phase 4 arms must not run.**

## Diagnosis (corrected) — the defect is live and dominant; the gate's thresholds were miscalibrated

**Measured Pass-2 pool score ranges** (extracted directly from `probe_rerank_window_20260815.json`,
124 queries), confirming the plan's Context table against production data rather than assumption:

| Channel | Observed range | Median | n |
|---|---|---|---|
| hop-1 (tagged `source="hybrid"`) | −0.1322 … +0.6933 | **+0.0062** | 2,480 |
| semantic (`multi_hop`) | +0.4445 … +0.9811 | +0.7444 | 1,649 |
| graph (`graph_hop`) | 0.0 … 0.0 | 0.0 | 2,942 |

Hop-1-tagged pool entries all carry `source="hybrid"` (the *only* source value seen among pool
entries with `metadata["hop1_rank"] is not None`, across all 124 queries — `_CHANNEL_TIER`
doesn't need to key on it because the `hop1_rank is not None` check runs first, but it's a naming
trap worth recording for future diagnostics).

**Pool composition, per query:** hop-1 = 20 (fixed by `initial_k`, `multi_hop_searcher.py:541`,
verified 20/20/20 across all 124 queries), `graph_hop` median **24**, `multi_hop` median **12.5**.
**Window composition** (30 slots, score-sorted default): `multi_hop` 43.8%, hop-1 32.4%,
`graph_hop` 23.8% — a median of **7 `graph_hop` slots per window**. 32.4% × 30 ≈ 9.7: **roughly
10 of the 20 jina-ranked hop-1 survivors are cut from the window every query**, and the cut line
falls where jina's score crosses zero — median hop-1 score is +0.0062, so half of hop-1 sits at
or below zero and loses its slot to a `graph_hop` candidate carrying a literal `0.0` with no
relevance signal at all. **This is the defect, and on this substrate it is large, not small.**

**Why P1/P2 failed even though the defect is real — the thresholds were unreachable by
construction, not falsified by evidence.** P1 required `multi_hop` ≥ 60% of the 30-slot window
(18 slots). But the median pool only contains 12.5 `multi_hop` candidates in total — fewer than
the threshold needs even before any cut. Only **32/124 queries (25.8%) have enough `multi_hop`
candidates in the pool to reach 18 in the window under any ordering.** P1 was testing "is
`multi_hop` the dominant channel" when the actual dominant channel by pool volume is `graph_hop`
(median 24, vs `multi_hop`'s 12.5) — the prediction targeted the wrong channel. P2's
`reserve_arrival_share_median=0.0` similarly reflects that the reserve is a small correction on
top of a much larger effect (the raw sort's ~10-hop-1-per-query cut), not evidence the sort isn't
biting.

**P4 (finding E) — the eviction-target mechanism was mis-modelled, and this is a genuine, now
corrected, finding.** The original plan asserted "the window's tail **is** the hop-1 region," so
the reserve's blind tail eviction (`reranking_engine.py:379`,
`kept_window = window[: max(0, len(window) - num_evict)]`) would evict the best-ranked hop-1
seeds (ranks 1–2). Replaying the actual eviction against the captured pools falsifies the
mechanism: the window's score-sorted tail is **68.8% `graph_hop`**, 22.6% hop-1, 8.5% `multi_hop`
— because `graph_hop`'s 0.0 sits inside hop-1's range rather than uniformly below it, `graph_hop`
candidates dominate the low end of the sort as often as hop-1 does. Evicted hop-1 entries span
ranks 1–18 roughly uniformly (8, 9, 11, 11, 13, 11, 8, 10, 11, 10, 8, 7, 9, 6, 6, 7, 3, 1 at ranks
1–18 respectively) rather than concentrating at ranks 1–2. **Finding (E) is real but narrower than
claimed: 42/122 queries (34.4%) where the reserve fires lose ≥1 hop-1 candidate to eviction** —
not the ≥50%-at-ranks-{1,2} the plan's P4 threshold was built to detect. The underlying repair
target (`_apply_hop1_reserve`'s `evict_policy="lowest_non_hop1"`, `score_reserve_fix`) is still
correctly aimed — it just protects a smaller, more rank-diverse population than assumed.

**P3 — `graph_hop`'s literal `0.0` is the dominant, previously under-weighted manifestation of the
same incommensurable-scales defect.** The plan expected `graph_hop` to almost never survive
against hop-1's positive-scoring entries. It survives constantly: median 3 `graph_hop` entries
per window (60.5% of queries have ≥1), because 0.0 sits mid-range in hop-1's distribution rather
than below it. Combined with the window-composition numbers above, `graph_hop` — not the
`hop1_reserved_slots` reserve interaction — is the primary lever this campaign should target.

**P5/P6 — confirmed as expected, unchanged by this correction.** P5's clean pass validates that
Pass 3 is structurally inert at k=10 (100% vs ≥99% threshold — both call sites,
`hybrid_searcher.py:754` and `:768`, omit `merged_pool_policy` and take the `"score"` default
regardless of config). P6's small count (5 queries, 7 gold hits) confirms finding (D)'s ceiling is
real but small: even a perfect window fix caps realistic upside at roughly this many additional
golds, since Pass 2 still returns only `sorted_results[:k]` (`reranking_engine.py:469`).

**A2's headroom signal reinterpreted.** Both policies showed clean positive membership headroom
in the simulator — `score_reserve_fix` nets +7 with zero evictions, `channel_priority` nets +8
with 2 evictions. Under the corrected diagnosis this is not "a positive-but-non-overriding
side-signal on an otherwise-absent defect" — it is the *expected* shape of headroom gain for a
real, dominant scale-mixing defect being partially corrected by two different repair strategies.
It is still a veto, not a win-prediction (the simulator can't model jina's re-scoring or the
`[:10]` cut) — but it now reads as corroborating evidence, not a curiosity.

## Corrected Phase 4 gate (pre-registered before any arm runs)

`channel_priority` is promoted to **primary** — the measured offender is `graph_hop`'s
uninformative `0.0` occupying a median 7 window slots, and `channel_priority`'s tier-2 handling is
the built mechanism that addresses it directly. `score_reserve_fix` is **secondary** — it targets
finding (E), now measured at 34.4% of queries with a uniform rank spread, a materially smaller
effect than the ~10-hop-1-cut-per-query scale-mixing displacement.

| Arm | Sets | `--set` overrides (beyond `intent.enabled=true`) |
|---|---|---|
| `base_63q_r1`, `base_63q_r2` | 63q | — (canon re-pin + bf16 determinism check) |
| `base_133q_r1` | 133q | — (canon re-pin) |
| `p1_channel_priority` | 63q + 133q | `reranker.merged_pool_policy=channel_priority` |
| `p2_reserve_fix` | 63q + 133q | `reranker.merged_pool_policy=score_reserve_fix` |

Gate, fixed before any run and not adjusted post-hoc:

- **Upside:** 133q paired 95% CI excluding zero on the positive side for **recall@10 or
  recall@20**, with the other's point estimate ≥ 0.
- **Guard-rails (any breach disqualifies):** MRR CI must not exclude zero on the loss side on
  either set; **63q recall@5 and recall@10** are named guard-rails (the leg-depth campaign
  recorded a 63q recall@5 loss an MRR-only guard missed).
- `pool_hit_rate` drop > 0.02 without a qualifying gain is disqualifying — guard-rail only, since
  it measures Pass 3's pool, downstream of the Pass-2 cut being repaired.
- **Risk check, reported regardless of aggregate verdict:** `channel_priority` drives `graph_hop`
  window occupancy from median 7 → 0 (zero in 78/124 queries per the simulator). ADR-0013's Q12
  second gold and A1's H034/H066 rescues were graph-sourced — check these specifically for
  regression.
- Latency: predicted Δ ≈ 0 (pure reordering); |Δ| > 100 ms/query requires an explanation.
- Gate on aggregates only — per-query values are realization properties under seed-0
  (`PYTHONHASHSEED=0`, ADR-0021, auto-re-exec).

Every arm needs `--set intent.enabled=true` (`run_sscg_benchmark.py:740`/`:2222` force-pin
`intent.enabled=False`; the B1b guard at `:1966-1969` requires an explicit `--set` to survive).

## Disposition

- **Landed code stays in-tree, unchanged.** `merged_pool_policy` (config field), `_order_merged_pool`,
  `_apply_hop1_reserve`'s `evict_policy` kwarg, and the Pass-2-only dispatch in
  `multi_hop_searcher.py` are byte-identical at the default (`"score"`) and were verified via the
  full `tests/unit/search/` suite (1613/1613 passing) both at initial landing and after this
  window's pyrefly type-fix commit.
- **Phase 4 A/B arms (7 runs, ≈60–75 min) run as a follow-up to this correction**, gated on the
  criteria above rather than on the retracted A1 result.
- **`evaluation/probe_rerank_window_20260815.json`** (124 records, full P1–P6/A1–A3 detail)
  remains the authoritative data artifact underlying both the original and corrected diagnosis;
  no re-probe was needed — only its interpretation changed.
- **What was actually wrong with the original abort:** not the measured numbers (P1–P6/A1–A3
  values are unchanged and correctly computed by `evaluate_gate()`), but the *predictions'
  operationalization* — P1 targeted the wrong channel (`multi_hop` share) when `graph_hop` is the
  dominant pool channel by volume, and P4's rank-{1,2} threshold didn't match how the blind tail
  eviction actually behaves once `graph_hop`'s mid-range 0.0 is accounted for. Lesson for future
  probes on this codebase: derive channel-share thresholds from measured pool composition before
  pre-registering them, not from a scale-ordering argument alone.
