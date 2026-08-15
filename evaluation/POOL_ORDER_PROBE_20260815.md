# Merged-Pool Ordering Campaign — Phase 1 Probe — GATE FAILED at A1 (2026-08-15)

**Verdict: ABORT at the pre-registered A1 (premise) gate. Phase 4 A/B arms NOT run. Landed
code (`merged_pool_policy`, default `"score"`, byte-identical) stays in-tree; nothing is
reverted.**

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

## Diagnosis — why the premise didn't hold on this substrate

**P1/P2 — hop-1 survivors are more score-competitive than the plan's narrative assumed.**
Hop-1-tagged pool entries all carry `source="hybrid"` (verified: the *only* source value seen
among pool entries with `metadata["hop1_rank"] is not None` is `"hybrid"`, across all 124
queries — `_CHANNEL_TIER` doesn't need to key on it because the `hop1_rank is not None` check
runs first, but it's worth recording as a naming trap for future diagnostics). With a median 7 of
the top-8 hop-1 seeds already surviving into the window on raw score alone
(`reserve_arrival_share_median=0.0`), the reserve mechanism is rarely load-bearing here — the
naive sort isn't pushing hop-1 out as hard as the plan's Context section hypothesized. That's
also why P4 (finding E, direct measurement) fires on only 7.26% of queries rather than the ≥50%
predicted: the defect is real (7.26% > 0%, and A2's positive headroom below confirms it isn't a
no-op) but rare, not dominant, on this current substrate.

**P3 — `graph_hop`'s literal `0.0` is a different, non-monotonic manifestation of the same
incommensurable-scales defect.** The plan expected `graph_hop` (score `0.0`) to almost never
survive against hop-1's positive-scoring survivors. In fact `0.0` sits *inside* hop-1's observed
range (≈ −0.12…+0.22), not below it — so a `graph_hop` candidate beats roughly the bottom half of
hop-1 survivors on raw score alone. Median 3 `graph_hop` entries per window, present in 60.5% of
queries. This is still evidence *for* the underlying incommensurable-scales problem (arguably a
worse-behaved one, since it's non-monotonic rather than a clean channel-dominance pattern) — it
just isn't the specific `multi_hop`-dominance shape P1/P3 were designed to detect.

**P5/P6 — confirmed as expected.** P5's clean pass validates the funnel model's claim that Pass 3
is structurally inert at k=10 (100% vs ≥99% threshold). P6's small count (5 queries, 7 gold
hits) confirms finding (D)'s ceiling caveat is real but small — even a perfect window fix caps
realistic upside at roughly this many additional golds on this substrate.

**A2's positive-but-non-overriding signal.** Both policies show clean membership headroom in the
simulator — `score_reserve_fix` in particular nets +7 with **zero** evictions, the cleanest
possible shape a membership-rescue signal can take. Per the plan's own explicit design ("passing
A2 is a veto only, never a prediction of a win"), this does not authorize running Phase 4 on its
own: A2 only rules out "no headroom at all," it was never sufficient by itself, and A1 gates
first. The two failures are independent signals — A1 says the *narrative reason* the fix should
matter (channel-share dominance, reserve-dependency) isn't true here; A2 says the fix still moves
*something* in the right direction. Both are true simultaneously and both are recorded here
without one being used to talk the other down.

## Disposition

- **Landed code stays in-tree, unchanged.** `merged_pool_policy` (config field), `_order_merged_pool`,
  `_apply_hop1_reserve`'s `evict_policy` kwarg, and the Pass-2-only dispatch in
  `multi_hop_searcher.py` are byte-identical at the default (`"score"`) and were verified via the
  full `tests/unit/search/` suite (1613/1613 passing) both at initial landing and after this
  window's pyrefly type-fix commit. A1 failing means "don't spend Phase-4 GPU-hours on this
  substrate," not "the code is wrong" — no revert is warranted.
- **Phase 4 A/B arms (7 runs, ≈60–75 min) are NOT run.** This is a mechanical consequence of the
  plan's own pre-registered, already-approved abort rule, not a new judgment call.
- **`evaluation/probe_rerank_window_20260815.json`** (124 records, full P1–P6/A1–A3 detail) is
  the authoritative data artifact for this disposition; stdout was piped/buffered during the
  background run and its printed summary block was cross-checked against this JSON for exact
  agreement before drawing any conclusion here.
- **Reopening condition.** Re-derive P1–P4 on a substrate/dataset where hop-1 survivors are
  actually being displaced at the rate the plan's Context section assumed — e.g. a corpus or
  query mix with a higher semantic-expansion-to-hop1 density, or after `graph_hop` candidates are
  given a real anchor-conditioned score instead of the literal `0.0` (a smaller, more targeted
  fix than either landed policy, and the one P3's finding argues for most directly — `graph_hop`
  is the channel actually causing 60.5%-of-queries mid-window intrusion here, not `multi_hop`).
  Absent a substrate change or that follow-up fix, do not re-run this probe expecting a different
  P1/P2 outcome — the current numbers are self-validity-clean, not noise.
