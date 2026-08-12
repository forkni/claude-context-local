# Default intent classification off; remove the `find_path` redirect

Status: accepted
Date: 2026-08-04

## Context

ADR-0026 captured `canon_B1b`, the intent-on benchmark arm, and found the intent layer's entire
measurable effect on retrieval quality is its two redirects. The non-redirect machinery — QW5's
intent-adaptive ego thresholds, A1's per-intent edge-weight profiles — is inert: `pool_size` and
`pool_hit_rate` are bit-identical to four decimals whether or not it fires, for a net **+0.0005
MRR** across both datasets. Of the two redirects, `find_path` has no upside evidence at all: both of
its live firings (Q72, Q121) are regex misfires of `_extract_path_endpoints` on ordinary prose, and
`fallback_on_error=False` turns each into an empty result set — a query that would have returned
*something* under normal ranked search returns *nothing*. `find_similar` is the opposite case: a
three-way comparison (normal path 0.4577 → buggy redirect 0.2315 → correct-anchor F-view 0.8519)
shows the mechanism is sabotaged by a diagnosed bug in `_extract_symbol_from_query`, not worthless.

`intent.enabled` defaulted to `True` (`search/config.py:546`), so every production `search_code`
call was running the `find_path` bug live. A gitignored `<repo>/search_config.json` override already
disabled it on this machine only; the shipped default was unchanged, and every other deployment of
this server was exposed.

ADR-0026 recorded this disposition as adopted but deliberately did not execute it, so the ADR would
remain an honest record of what was measured before anything changed. This ADR executes the first
step — the stopgap — leaving the `find_similar` repair and re-gate to a separate round (Round C, to
follow as ADR-0029).

## Decision

Two behavior commits (two-hats rule: neither is a refactor, so neither shares a commit with one):

1. **`c55c20a` — default `intent.enabled` to `False`.** One-line default flip in
   `search/config.py`, with a comment citing this ADR's measurement. The field carries no `mcp=` or
   `env=` tag and no test asserted the old default, so nothing else needed to change beyond keeping
   `search_config.json.example` in sync with the new dataclass default (a test enforces the two stay
   identical).
2. **`6a6dc18` — remove the `find_path` redirect entirely.** Deleted, not disabled: the redirect
   construction branch and the now-vacuous `redirect is None` guard in the surviving `find_similar`
   branch (`mcp_server/tools/search_orchestrator.py`), the redirect execution arm and its
   `handle_find_path` import, the `PATH_TRACING` docs in `PlanRedirect`'s docstring, the
   `PATH_TRACING` arm of `_extract_suggested_params`, and `_extract_path_endpoints` itself
   (`search/intent_classifier.py`) — four regex patterns, zero of which had ever produced a useful
   redirect. `QueryIntent.PATH_TRACING` the enum member **stays**: it still selects a QW5 ego
   threshold and an A1 edge-weight profile, both measured inert but not in scope for this round.

Both commits invalidate the canon (they edit indexed source); `evaluation/CANON_20260804_INTENT_OFF.md`
re-pins it to `canon_g1`.

### Why remove instead of just leaving it dead code behind the new default

`intent.enabled=False` alone would have silenced `find_path` for every caller of the shipped
default, but the branch, its extractor, and its empty-result failure mode would still exist for
anyone who re-enables the layer (a local override, a future experiment, or Round C's own
intent-on capture). ADR-0026 already established there is no upside evidence to preserve — keeping
a redirect whose only observed behavior is turning an answerable query into an empty result is not a
default worth keeping available.

### Why not run Round C in the same commit

`find_similar`'s bug and `find_path`'s bug share a root cause file
(`search/intent_classifier.py`'s extractors) but not a fix: `find_path` had no salvageable behavior,
`find_similar` does, and repairing it is a re-tokenization change (promoting
`_detect_code_symbols`'s dotted-symbol tokenizer into a shared helper) gated on a pre-registered
recall/MRR criterion, not a deletion. Landing both in one commit would tie a build-and-measure
change to a pure removal and make either one harder to revert independently.

## Consequences

- **`canon_g1`** (mrr 0.8352 63q / 0.6667 133q / F-view whole-aggregate 0.8915, F-only mean 0.8519 —
  bit-identical to `canon_f1`'s F-only figure) becomes the published baseline, superseding
  `canon_f1`. The ~0.01 MRR shift is substrate drift from the ~121 deleted lines, not the behavior
  change taking effect: the benchmark harness's `pin_intent_off=True` default was already
  re-asserting `intent.enabled=False` per query for every non-arm capture (`run_single`,
  `run_sscg_benchmark.py:707-711`), so `canon_f1` already measured the intent-off condition even
  though the shipped default was still `True`. `canon_g1` is the first re-pin where the harness's
  long-standing assumption and the shipped default agree.
- **The live production bug is fixed**, invisible to the harness precisely because the harness never
  exercised it: a direct capture with intent forced on and `find_path` still present returned an
  empty result set for Q72's query; against this round's index with the branch removed, the same
  query text scores mrr 1.0 through the normal ranked path. See
  `evaluation/CANON_20260804_INTENT_OFF.md` for the reproduction.
- **`find_similar` is untouched and still gated behind `intent.enabled=False`** — it will not fire in
  production until Round C repairs `_extract_symbol_from_query` and its gate passes.
- **Two tracked docs that claimed intent classification is always-on become false** and are corrected
  in this round: `docs/ADVANCED_FEATURES_GUIDE.md`'s A1 section ("Always-on … No configuration
  needed") and `.claude/skills/mcp-search-tool/references/advanced-features.md`'s routing note (which
  also carried two pre-existing inaccuracies fixed alongside: the confidence threshold is 0.4, not
  0.35, and `semantic_enabled` defaults `True`, not `False`).
- Four tests deleted (three `find_path` redirect-construction tests, one redirect-plan-instance
  test), one added (`test_similarity_redirect_plan_is_searchplan_instance`, replacing the deleted
  instance-check's coverage on the surviving `find_similar` path so the `PlanRedirect`/`SearchPlan`
  imports in `test_search_planner.py` stay live). Net test count: −3.

## Verification

`./scripts/test/run_tests.sh tests/unit/ -q` and `tests/fast_integration/ -q` both green on every
commit before landing. `audit_golden_dataset.py` CLEAN on both datasets against the fresh
204-file/2322-chunk index. `evaluation/CANON_20260804_INTENT_OFF.md`: three views (63q, 133q,
F-view) all overall PASS; Q72 end-to-end reproduction confirms the empty-result bug is gone.

## Out of scope

- Repairing `_extract_symbol_from_query` and re-gating the `find_similar` redirect — Round C,
  `docs/adr/0029` (to follow).
- Any change to `QueryIntent` classification, QW5's ego-threshold table, or A1's edge-weight
  profiles — all measured inert by ADR-0026 but not touched here; `intent.enabled=False` already
  silences them regardless of their own merits, and Round C's gate outcome decides whether the whole
  layer becomes a removal candidate.
