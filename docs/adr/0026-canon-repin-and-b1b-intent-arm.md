# Re-pin the SSCG canon to `canon_f1` and capture the `canon_B1b` intent-on arm

Status: accepted
Date: 2026-08-04

## Context

ADR-0023 gated two of an architecture review's highest-value candidates — threading
`RetrievalRequest` into `ReRankingEngine` (`reranker-config-required`, its "P4") and introducing a
plan object that owns retrieval widths (`funnel-plan`, its "A") — on first capturing `canon_B1b`,
the intent-on benchmark arm. A repo-wide search confirmed `canon_B1b` had never been captured; the
only mentions were ADR-0023 itself and a comment at `scripts/benchmark/run_sscg_benchmark.py:1897`.

Capturing it required one prerequisite fix: `run_single`'s per-query re-pin
(`get_search_config().intent.enabled = False`) unconditionally forced intent off regardless of what
an arm's own overrides requested, so `--set intent.enabled=true` alone could not produce a
measurable intent-on run. `f4915c2` made the pin arm-aware (`intent_pinned_by_arm = "intent.enabled"
in overrides`) and added redirect-aware scoring: `find_path` redirects previously scored a silent 0
(`fallback_on_error=False` returns no results at all), which would have made the arm's MRR
uninterpretable without distinguishing "the intent layer chose to answer differently" from "the
intent layer chose nothing."

Five unrelated commits landed in the same round for other reasons
(`parallel-edge-collapse`/`e7d623a`, `mcp-field-derivation`/`cfe83a0`,
`project-activation-pairing`/`dff0ed7`, `config-locator-inline`/`4177d8a`) — none touch retrieval
mechanics, but all edit indexed source, and this project benchmarks against its own codebase, so any
commit invalidates the standing canon per the project's substrate-drift rule. `canon_e1`
(`evaluation/CANON_20260804_ARM_OVERRIDES.md`) is the canon in effect at the start of this round.

## Decision

Re-measure and publish `canon_f1` (supersedes `canon_e1`), and capture `canon_B1b` as a named arm
on the same substrate, following the capture discipline ADR-0023/0024 established:
`audit_golden_dataset.py` clean → full non-incremental reindex → capture → confirm determinism via
the 63q pair (0 flips) → single round for every other view, per the precedent `canon_e1` set.

Full numbers, procedure, and the arm's findings live in `evaluation/CANON_20260804_B1B.md`; this ADR
records the decision and what it means for the intent layer's production status.

### The published canon stays intent-off

Redirects scoring differently from ranked search would silently redefine what the headline MRR
measures and break comparability with the whole chain
(`0.7987 → canon_B1 → canon_C3 → canon_d1/d2 → canon_e1 → canon_f1`). `canon_B1b` is measured and
published as a named arm, not promoted to the production canon.

### `canon_B1b` matched its pre-registered falsifiability table exactly

ADR-0023's gate asked for more than `redirect_rate > 0` — that check is nearly vacuous, satisfied by
a single misfiring query. The pre-registered table instead specified exact `redirect_ids` and
`find_similar` redirect counts per dataset. Both were hit exactly: `['Q72']`/9 (63q) and `['Q72',
'Q121']`/10 (133q). **The gate is discharged**, unblocking `reranker-config-required`, `funnel-plan`,
and `B2` (the 11 config-mutation sweep shims ADR-0023 deferred deleting).

### The arm's actual finding: the intent layer's entire measurable effect is its two redirects, and one of them has no upside

Splitting both datasets by whether a query redirected shows the non-redirect majority (53/63,
121/133) is **unaffected at the pool level** — `pool_size` and `pool_hit_rate` are bit-identical to
four decimals whether or not QW5's intent-adaptive ego thresholds and A1's per-intent edge-weight
profiles are active. They only reshuffle ranking within an identical pool on a handful of queries
(4/53, 9/121), moving MRR on just 3 of those, for a net **+0.0005 MRR**. This machinery is inert on
this substrate, not merely low-impact.

The two redirect classes diverge sharply on evidence:

- **`find_path`** (Q72, Q121): both instances are regex misfires on ordinary prose (`_extract_path_
  endpoints` matching "from chunk_id to get" as a path query), and `fallback_on_error=False` turns
  each into an empty result set. No query in either golden set has any upside from this branch.
- **`find_similar`** (9 queries, exactly the 9 anchored F-category queries): a three-way comparison
  against the normal path and the hand-annotated-anchor F-view shows the mechanism is *sabotaged*,
  not worthless — mean MRR 0.4577 (normal) → 0.2315 (buggy redirect) → 0.8519 (correct anchor). The
  gap is a known, already-diagnosed bug in `_extract_symbol_from_query`
  (`search/intent_classifier.py:618-677`): its three regex passes scan `reversed(query.split())`, so
  a trailing prose word beats a dotted symbol every whole-word regex misses. Live misfires: a
  `InheritanceExtractor._extract_from_tree` query extracted `hook`; a `PythonChunker.__init__` query
  extracted `codebase`.

No config-only lever exists to fix this: misfire confidences (0.78–0.93) sit well above the 0.4
`confidence_threshold` gate, and raising that threshold doesn't isolate bad redirects — it demotes
every sub-threshold query to `default_intent`
(`intent_classifier.py:273`), collapsing the (already-inert) adaptive machinery along with it.

## Consequences

- **`canon_f1`** (mrr 0.8458 63q / 0.6692 133q / F-view whole-aggregate 0.9021, F-only mean 0.8519)
  becomes the published baseline, superseding `canon_e1` (0.8363/0.8362 63q, 0.6803 133q). The move
  is a small, mixed-direction shift consistent with prior same-round re-pins and not attributed to
  any single one of the five unrelated commits.
- **ADR-0023's gate is discharged.** `reranker-config-required`, `funnel-plan`, and `B2` are
  unblocked for future rounds.
- **A follow-up disposition is adopted**, not executed by this ADR: flip `intent.enabled`'s default
  to `False` and remove the `find_path` redirect immediately (stopgap; a runtime override already
  does this locally via the gitignored `<repo>/search_config.json`, but the shipped default at
  `search/config.py:546` is unchanged until that round lands); then repair
  `_extract_symbol_from_query` and re-measure the `find_similar` redirect against a pre-registered
  gate (MRR must exceed the same-substrate normal-path mean **and** recall@20 must not fall below it
  by more than run noise, on both datasets); if the repair fails the gate, remove the similarity
  redirect too and treat the whole intent layer as a removal candidate on the ADR-0015/ADR-0016
  precedent. These are scoped as separate rounds so this ADR remains an honest record of what was
  measured before anything changed.
- **Two known instrument limits are recorded, not fixed**: the canonical `k=10` capture cannot
  exercise the GLOBAL intent's `suggested_k=10` bump (the orchestrator only bumps when
  `suggested_k > k`), so `canon_B1b` measures the intent layer minus that path; and the harness's
  `search_mode` suggestion branch is permanently dead (requires `AUTO`, the harness always passes a
  concrete mode).

## Verification

See `evaluation/CANON_20260804_B1B.md` for full aggregate metrics across all six views, the
redirected-vs-rest split (replicated on both datasets), the three-way similarity comparison, and the
root-cause evidence (live misfire examples, blast-radius confirmation via `find_connections`). 63q
determinism control: 0 flips across all 63 rows (every field but `latency_ms`) between two rounds,
confirming ADR-0021's seed-0 pin holds on this substrate. `audit_golden_dataset.py` CLEAN on both
datasets against the fresh 2324-chunk index.

## Out of scope

- Executing the flip-default / remove-`find_path` / repair-and-gate disposition — scoped as two
  separate follow-up rounds (Round B, Round C), landing after this ADR.
- Any change to `QueryIntent` classification itself, QW5's ego-threshold table, or A1's edge-weight
  profiles — all measured inert on this substrate but not touched by this ADR.
- Re-deriving the `canon_e1 → canon_f1` delta's attribution to a specific one of the five unrelated
  commits — none touch scoring, fusion, or reranking logic by design, matching the acceptance
  standard ADR-0024 already established for its own predecessor delta.
