# ADR-0019: Reject intent-adaptive fusion weights (measured, replicated, removed)

**Status**: Accepted (2026-08-01)
**Supersedes the open question left by**: ADR-0018

## Context

ADR-0018's C2 refactor fixed the parameter-drop defect (D1) that had silently prevented
`IntentClassifier`'s per-intent BM25/dense weight suggestions from ever reaching the retrieval
leg, and landed the repaired path behind `SearchModeConfig.intent_adaptive_weights = False`
pending A/B evidence. This ADR records that evidence and the decision.

The candidate weight table (`INTENT_WEIGHT_PROFILES`) vs the deployed default (0.35/0.65):
LOCAL (0.35, 0.65) — numerically a no-op; GLOBAL/CONTEXTUAL (0.30, 0.70);
NAVIGATIONAL (0.50, 0.50); PATH_TRACING / SIMILARITY / matched-HYBRID (0.40, 0.60).
Production blast radius (confidence ≥ 0.35, category D and would-redirect queries removed):
14 scored queries on the 63q golden set, 16 on the 96q expanded set — all at confidence 1.0.

## Evidence

### Step 1 — Weight-sensitivity probe (evidence gate)

`scripts/benchmark/probe_weight_sensitivity.py` extended to 9 weight points including both
non-default intent-profile operating points (0.30/0.70, 0.40/0.60), run over both golden
datasets at k=10. Under the pre-registered gate rule (headroom counts only at a query's *own*
profile point, > 0.02 noise band):

- 63q run: GLOBAL Q54 +0.167 and Q55 +0.033 at 0.30/0.70 — gate opened.
- 96q run (same queries re-measured): Q54 **−0.167** (sign flip → fp16 near-tie noise),
  Q55 0.000. No affected query showed replicated profile-point headroom.
- The only *replicated* profile-point signal was damage: PATH_TRACING Q90 dropped
  1.000 → 0.333 at 0.40/0.60 in **both** probe runs.
- The probe's nominal headroom lists (9/63, 21/94 queries) sit almost entirely at tail
  points (0.10/0.90, 0.90/0.10 …) that the intent table never applies.

### Step 3 — Pre-registered A/B (3 replicates × 2 arms × 2 datasets, 12 runs)

Measurement vehicle: honest replay in `run_sscg_benchmark.py --intent-weights` — per-query
classification mirroring the orchestrator gate byte-for-byte (same five AND-conditions,
would-redirect queries skipped, suggested weights passed as explicit
`HybridSearcher.search()` kwargs — the identical mechanism `search_orchestrator.py` used).

| Dataset | base MRR (3 runs) | replay MRR (3 runs) | Δ aggregate |
|---|---|---|---|
| 63q | 0.8012 / 0.7855 / 0.8094 (mean 0.7987) | 0.7873 / 0.7778 / 0.7861 (mean 0.7837) | **−0.0150** |
| 96q | 0.6771 / 0.6872 / 0.6803 (mean 0.6815) | 0.6755 / 0.6748 / 0.6861 (mean 0.6788) | **−0.0027** |

Pre-registered rule: ADOPT only if (a) 96q Δ > +0.02 with 63q Δ ≥ −0.02, AND (b) affected-
subset mean per-query MRR Δ positive, AND (c) control-subset Δ within ±0.02.

- (a) **FAIL** — both aggregates negative.
- (b) **FAIL** — pooled affected-subset Δ **−0.0497** (n=14+16). Q90 (PATH_TRACING,
  0.40/0.60) dropped 1.000 → 0.333 in all 6 replay runs across both datasets; Q54, Q86,
  Q89 also negative. The only positive mover was Q112 (+0.028, within noise).
- (c) PASS — pooled control-subset Δ +0.0023: the pairing is valid; the losses are signal,
  not noise.

**Verdict: REJECT.** The intent-derived fusion weights measurably hurt retrieval on the
affected queries and help nowhere beyond noise.

## Decision

Delete the feature rather than leave it dormant (same policy as ADR-0015/0016):

- `SearchModeConfig.intent_adaptive_weights` field, its `_FLAT_KEY_ALIASES` entry, and the
  `search_config.json.example` line — removed.
- `SearchOrchestrator._search` gate block and the `bm25_weight=`/`dense_weight=` kwargs it
  fed into `searcher.search()` — removed. (The `HybridSearcher.search()` explicit-override
  kwargs themselves stay: they are C2 API, used by benchmarks/tools.)
- `SearchPlan.suggested_bm25`/`suggested_dense` and their derivation in `SearchPlanner.plan`
  — removed.
- `INTENT_WEIGHT_PROFILES`, the profile append and LOCAL existence-check weight suggestion in
  `_extract_suggested_params`, and the weight-override debug log in `intent_classifier.py`
  — removed. **The classifier itself stays**: it drives redirects, k adjustment, ego-graph
  enablement, and edge-weight profiles (`INTENT_EDGE_WEIGHT_PROFILES`), none of which this
  ADR touches.
- `run_sscg_benchmark.py --intent-weights` replay machinery — removed (its purpose is
  fulfilled; this ADR records the numbers).
- `probe_weight_sensitivity.py` — kept as a general per-query weight-sensitivity tool,
  docstring retagged with the outcome.

## Consequences

- Every `search_code` request continues to execute at the deployed fusion weights
  (0.35/0.65), now without a dormant alternate path to maintain or re-litigate.
- Future per-query weight adaptivity proposals must first explain Q90: a listwise-reranked
  funnel reshapes the pool downstream of fusion, so small fusion-weight shifts can demote a
  rank-1 gold out of the final pool entirely — per-intent *static* profiles are the wrong
  granularity.
- Raw A/B artifacts: `benchmark_results/ab_intent/` (12 run JSONs + `analyze_ab.py`).
