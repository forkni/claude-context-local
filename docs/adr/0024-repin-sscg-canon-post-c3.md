# Re-pin the SSCG canon after the C3 searcher-construction / config-metadata fixes

Status: accepted
Date: 2026-08-03

## Context

Three defects surfaced while exploring the ADR-0018 follow-on plan, none of them the original
scan target:

1. `get_searcher` (`mcp_server/search_factory.py`) and `_check_auto_reindex`
   (`mcp_server/tools/search_handlers.py`) each hand-built an identical `HybridSearcher`
   construction call with 11–12 kwargs, diverging only in dimension-mismatch handling, locking,
   cache-bind timing, and when `current_project` is set — duplication that made those four
   deliberate divergences hard to see against the noise of the shared parts.
2. `initialize_server_state` (`mcp_server/resource_manager.py`) restored the active project on
   both its env-var and persisted-selection branches but never called
   `set_active_project_storage_dir`, so a project's `search_overrides.json` (ADR-0014) was
   silently not merged into the effective config after every server restart until an explicit
   `switch_project` or `index_directory` call. Fixing the binding first required closing a
   second bug it would otherwise turn from occasional into permanent: `save_config` writes its
   result back to the *global* config file unfiltered, so any config-writing MCP tool call made
   while a project's overrides were merged in promotes those overrides into global config.
3. Two of the six `construction_baked=True` flags landed in the prior config-liveness audit
   (`700651a`) were false: `bm25_weight`/`dense_weight` are resolved live per `search()` call,
   not baked into `HybridSearcher.__init__`. Every `--bm25-weight`/`--dense-weight` benchmark arm
   was paying a needless searcher reset and reranker-model reload as a result.

None of these three touch scoring, fusion, or reranking logic. All three edit indexed source,
and — per ADR-0023's own precedent — this project benchmarks against its own codebase, so the
canon in effect at the start of this work (`canon_B1`, ADR-0023, mrr 0.8249) is stale once the
fixes land, the same way `canon_B1` itself made the pre-B1 canon (mrr 0.7942) stale.

A fourth, purely-documentation problem was found alongside these: `CLAUDE.md`, `README.md`,
`docs/BENCHMARKS.md`, `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`, and
`docs/VERSION_HISTORY.md` all still published `0.7987` — the canon from *before* `canon_B1` —
because `canon_B1`'s landing (`7a7dea5`/`df4d408`) recorded its own number in ADR-0023 and
`CHANGELOG.md` but never propagated to the five user-facing surfaces. This ADR repins the canon
past both stale generations at once.

## Decision

Re-measure and publish a new canon, `canon_C3`, after all six Phase 1/2 commits land
(`65f2317`, `f86dced`, `c85d476`, `4d6de41`, `0f8ff8d`, `a22ebe7`), following the same
capture discipline ADR-0023 established: `audit_golden_dataset.py` clean, a full
non-incremental reindex immediately before capture, two rounds per dataset view with a
formal `--compare` confirming 0 flips, `PYTHONHASHSEED=0` (self-pinned per ADR-0021).

Capture covers three views — 63q canonical, 131q expanded, and the F-via-similar
substitution — matching what the five stale doc surfaces publish. Full numbers, procedure,
and the delta breakdown live in `evaluation/CANON_20260803.md`; this ADR records the decision
and the two things worth calling out beyond the numbers themselves.

### The F-view mislabel gets fixed, not just re-measured

`docs/BENCHMARKS.md`/`README.md` published `0.8502` captioned as "F-via-similar (anchor-chunk
view, F-category), 9 [queries]" — but that number is `aggregate.mrr` over the **whole 63-query
run** with the F-via-similar substitution applied, not a 9-query F-category-only mean. The
true F-only mean (filter `per_query` to `category == 'F'`, average `mrr`) is a different,
lower number — **0.8519** in this capture, matching the value
`evaluation/RECALL_CAMPAIGN_CLOSEOUT_20260802.md` already computed correctly and independently
on 2026-08-02. The published tables are corrected to show both numbers, labeled correctly,
rather than perpetuating the whole-aggregate-as-F-only mislabel into a third canon generation.

### `canon_B1` was never wrong to skip publishing — it's superseded before it would have been used

`canon_B1` landed with ADR-0023 and a `CHANGELOG.md` entry but no doc-surface update was made
for it; this ADR's capture happened before anyone acted on that gap. Rather than publish
`canon_B1`'s numbers now only to immediately re-publish `canon_C3`'s, the five doc surfaces are
updated directly to `canon_C3`, and this ADR records the intermediate `canon_B1 → canon_C3`
delta so the chain from `0.7987` stays traceable through both generations.

## Consequences

- **Two canon generations retire at once.** The `0.7987` figure (pre-`canon_B1`, itself already
  superseded once by ADR-0023) and `canon_B1` (0.8249, published only in ADR-0023/CHANGELOG.md)
  both retire; `canon_C3` (0.8348 63q / 0.6816 131q) becomes the published baseline in
  `CLAUDE.md`, `README.md`, `docs/BENCHMARKS.md`, `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`,
  and `docs/VERSION_HISTORY.md`.
- **Delta not attributable to a single mechanism.** Unlike ADR-0023 — where the delta had one
  clear cause, the call-site swap to `SearchOrchestrator.run()` — this capture's small, uniformly
  positive delta (mrr +0.0099, recall@10 +0.0264, recall@20 +0.0119; see
  `evaluation/CANON_20260803.md`) sits behind several intervening commits on `development`
  between the two captures, none of which touch scoring, fusion, or reranking logic by design.
  Recorded as ordinary corpus drift, following the same acceptance ADR-0023 states for its own
  predecessor delta, rather than over-attributed to any one of this plan's six commits.
- **F-view mislabel corrected going forward.** Any future capture of the F-via-similar view must
  report both the whole-aggregate `mrr` and the `category == 'F'`-filtered mean, and label each
  correctly — the whole-aggregate number is not a 9-query figure.
- **Historical records untouched**, per ADR-0023's own precedent: `docs/adr/0019`, `0021`,
  `0023`, `evaluation/GPU_DETERMINISM_AB_*`, `BASELINE_20260801.md`,
  `RECALL_CAMPAIGN_CLOSEOUT_*`, `RERANKER_FP32_*` all keep the numbers they measured at the time;
  none are retroactively corrected to `canon_C3`.
- **This doc commit itself drifts the substrate again**, exactly as ADR-0023 §Context notes for
  `docs/` edits — `docs/` is not in this project's own exclude list. Accepted rather than fixed:
  excluding `docs/` from the index would stabilize future canons but change the corpus and
  invalidate every prior one, including this one.

## Verification

See `evaluation/CANON_20260803.md` for full aggregate metrics, the delta table against
`canon_B1`, and the F-only-mean computation. Summary: two rounds each of 63q, 131q, and the
F-view, 0 flips confirmed via `--compare` on every pair; `audit_golden_dataset.py` clean on both
datasets after the mandatory reindex (one pre-reindex stale-gold report traced to a stale live
index snapshot, not a dataset defect, and resolved by the reindex itself).

## Out of scope

- Re-measuring or re-publishing the per-mode (semantic/BM25-only) historical comparison table in
  `docs/BENCHMARKS.md` — unmeasured since 2026-06-08, unaffected by this plan, left as-is.
- Attributing the `canon_B1 → canon_C3` delta to a specific one of the six Phase 1/2 commits.
  Nothing in this plan's own gate (unit tests, live-weight-read proof for 2a, binding tests for
  1c) depends on that attribution, and isolating it would require a per-commit bisect capture
  this ADR does not attempt.
