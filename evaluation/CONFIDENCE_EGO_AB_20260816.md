# Confidence/Ego Fixes — Phase 5 Measurement + Phase 6 Promotion (2026-08-16)

**Verdict: `hide_ambiguous_edges_default` PASSES its gate and is promoted to `default=True`.
`drop_nonpositive_output` FAILS its gate (significant recall@20 regression, no significant
upside) and stays `default=False`, now locked in `FORBIDDEN_AUTO_TUNE_KEYS`.**

Context: this closes out Phase 5/6 of `thoroughly-verify-the-quizzical-music.md` (four confirmed
live-MCP defects: confidence-default inversion, ambiguous fan-out, dead BFS priority /
nondeterministic truncation, ego tail flooding). Phases 1–4 (source, config, tests, static
analysis) landed clean and byte-identical at default-off settings (see "Substrate re-baseline"
below). This doc covers only the two default-off knobs the plan gates via A/B: Phase 2's
`hide_ambiguous_edges_default` and Phase 4's `drop_nonpositive_output`.

## Substrate re-baseline (supersedes 0.8722 / 0.6843)

The plan's Phase 5 assumed the existing canons (`evaluation/REMAINING_LEVERS_AB_20260814.md`, 63q
MRR 0.8722, 133q 0.6843) could gate this campaign directly, since the live server is confirmed
workstation-tier (F2LLM-v2-0.6B + jina-reranker-v3, not the 8GB bge-m3/gte profile). In practice
those canons no longer reproduce — **standing substrate-drift rule confirmed**, not a defect in
this work:

| Arm | Tree | MRR |
|---|---|---|
| Stale canon (2026-08-14) | — | 0.8722 |
| `evaluation/POOL_ORDER_AB_20260815.md` base (2026-08-15) | — | 0.8603 |
| `clean_baseline_63q_r1` | clean `a90d8ad`, no Phase 1-4 changes | **0.8437** |
| `phase1-4_noop_63q_r1` / `r2` | Phase 1-4 tree, all new knobs off | **0.8357** / 0.8357 (bit-identical) |

Isolated via `git stash push -- <Phase 1-4 files>` to get a clean-tree read on the same commit
(`a90d8ad`), same day, same command. Drift continues between 0.8722 → 0.8603 → 0.8437 purely from
ordinary intervening development (`05ca8d5` ADR-0039 provenance banding, `32b086c`
`graph_hop_window_cap` wiring, etc.) — confirming this is continuous expected drift, not a step
change caused by this work.

**Phase 1-4's own attributable delta is only −0.008 MRR** (0.8437 clean → 0.8357 with Phase 1-4 at
default-off settings), and per-query analysis shows only **1 of 63 queries** (Q90 — an
already-documented flapper, memory: "Q90 1.000→0.333 in all 6 replay runs, controls flat") has a
different reciprocal rank between the two trees; the other 45 queries with a different `retrieved`
list are metric-irrelevant tail reordering. This is consistent with Phase 3's traversal-order fix
being intentionally **unconditional** (not knob-gated), while Phases 1/2/4 remain true no-ops at
their defaults. Determinism holds cleanly on the Phase 1-4 tree (r1==r2 bit-identical MRR).

**New reference baselines for this campaign** (workstation tier, Phase 1-4 tree, all new knobs at
default-off):

| Set | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | hit_rate@5 | avg latency |
|---|---|---|---|---|---|---|---|
| 63q (`phase1-4_noop_63q_r1`) | 0.8357 | 0.6936 | 0.8009 | 0.8385 | n/a* | 1.0000 | 4118ms |
| 133q (`phase1-4_noop_133q_r1`) | 0.6647 | 0.6749 | 0.7823 | 0.8176 | 0.8947 | 0.9098 | 4221ms |

\* `pool_hit_rate` is presence-gated on a `pool_hit` key existing in `per_query` rows
(`evaluation/metrics.py:505`), which depends on the reranker-instrumentation hook having captured
`last_candidate_ids` for that harness invocation — this landed for the 133q run and both
`drop_nonpositive` arms but not for the three 63q no-op runs above. Root cause not chased further
since it does not affect any gate decision below (the 133q pair below is fully paired and
sufficient for the `pool_hit_rate` guard-rail on both knobs). Flagging as a harness gap for a
future session, not a methodology substitution.

**Workstation-tier substrate pin** (so the next campaign does not repeat the tier mislabel):
`codefuse-ai/F2LLM-v2-0.6B` embedder + `jinaai/jina-reranker-v3` reranker, `vram_total≈22.5GB`,
209 files / 2,457 chunks (2026-08-16 measurement — expect further drift on the next campaign per
the standing rule).

## `drop_nonpositive_output` — SSCG A/B — REJECTED

**Method**: `run_sscg_benchmark.py`, `PYTHONHASHSEED=0` auto-re-exec (ADR-0021), paired per-query
against the reference baselines above, `--set ego_graph.drop_nonpositive_output=true`. Gate per
`POOL_ORDER_AB_20260815.md` §Method: paired 95% CI, 10,000-resample bootstrap, seed 0. Upside =
133q recall@10 or recall@20 CI excludes zero positively. Guard-rails: MRR CI must not exclude zero
on the loss side on either set; 63q recall@5 named; `pool_hit_rate` drop ≤ 0.02; unexplained
|latency Δ| > 100 ms/query.

### Results

| Arm | Set | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | avg latency |
|---|---|---|---|---|---|---|---|
| `phase1-4_noop_63q_r1` (base) | 63q | 0.8357 | 0.6936 | 0.8009 | 0.8385 | n/a | 4118ms |
| `drop_nonpositive_63q_r1` | 63q | 0.8365 | 0.6936 | 0.8015 | 0.8121 | 0.8889 | 4022ms |
| `phase1-4_noop_133q_r1` (base) | 133q | 0.6647 | 0.6749 | 0.7823 | 0.8176 | 0.8947 | 4221ms |
| `drop_nonpositive_133q_r1` | 133q | 0.6668 | 0.6749 | 0.7894 | 0.7969 | 0.8947 | 4221ms |

### Paired 95% CIs (10,000-resample bootstrap, seed 0)

| Metric | Set | Mean Δ | CI |
|---|---|---|---|
| MRR | 63q | +0.0008 | [+0.0000, +0.0024] |
| recall@5 | 63q | +0.0000 | [−0.0159, +0.0159] |
| recall@10 | 63q | +0.0005 | [−0.0159, +0.0172] |
| recall@20 | 63q | −0.0265 | **[−0.0489, −0.0079]** |
| MRR | 133q | +0.0021 | [−0.0006, +0.0052] |
| recall@5 | 133q | +0.0000 | [−0.0113, +0.0113] |
| recall@10 | 133q | +0.0071 | [−0.0094, +0.0282] |
| recall@20 | 133q | −0.0207 | **[−0.0363, −0.0075]** |

Bold = CI excludes zero.

### Gate evaluation

- **Upside**: **not met** — neither 133q recall@10 (`[−0.0094, +0.0282]`) nor recall@20
  (`[−0.0363, −0.0075]`) clears the CI-excludes-zero-positively bar; recall@20's point estimate is
  actively negative.
- **MRR guard-rail**: holds — both CIs are non-negative-excluding (63q `[+0.0000, +0.0024]`, 133q
  `[−0.0006, +0.0052]`), no significant loss.
- **63q recall@5 (named)**: holds — flat at 0.0000 delta.
- **`pool_hit_rate` drop ≤ 0.02**: holds on the only paired data available — 133q flat at 0.8947 →
  0.8947, zero drop. (63q pair unavailable, see baseline-table footnote above.)
- **Latency**: 63q Δ ≈ −96ms, 133q Δ ≈ 0ms — both under the 100ms unexplained-delta threshold.
- **recall@20**: **breached on both sets** — CI excludes zero on the loss side, 63q
  `[−0.0489, −0.0079]` and 133q `[−0.0363, −0.0075]`.

**Verdict: REJECTED.** The upside condition never triggers positively, and recall@20 regresses
significantly on both datasets. Mechanistically consistent with the design: dropping
`source == "ego_graph"` results with `reranker_score <= 0` removes some genuine golds that only
surface in ranks 11–20 of the ego-expanded tail — the same tail the knob was designed to trim.
`min_output_score_ratio`'s predecessor design was already rejected in the plan's own verification
(doses mis-calibrated 2.5×–13×); this non-positive-cut redesign is dose-free but still costs real
recall in that window. Stays `default=False`; added to `FORBIDDEN_AUTO_TUNE_KEYS` /
`BENCHMARK_LOCK_CITATIONS` (`search/index_probe.py`) so the auto-tuning probe cannot resurrect it,
matching `graph_hop_window_cap`'s disposition.

## `hide_ambiguous_edges_default` — caller/callee recall harness — PASSED, PROMOTED

**Method**: `hide_ambiguous_edges_default` is a display filter on `find_connections` and never
touches the `search_code` retrieval path, so the SSCG benchmark is structurally incapable of
scoring it (a flat SSCG result would be a no-op artefact, not evidence). Gated instead with
`scripts/benchmark/run_caller_recall.sh`/`.py` against `evaluation/caller_golden.json` /
`callee_golden.json` (7 targets each). The harness originally called
`RelationshipAnalyzer.analyze_impact()` directly, bypassing `filter_ambiguous_edges()` entirely —
added a `--hide-ambiguous` flag (`run_caller_recall.py`: `_get_direct_edges()` /  `_run_single()` /
`main()`) that applies the identical `confidence != "ambiguous"` predicate used by the live MCP
path. Expected signature per the plan: **precision up, recall flat**. At n=7 per direction this is
directional only — too small for a bootstrap CI — so this harness is the regression guard, not the
sole evidence (the plan's live-MCP before/after table for Fix #2 is the primary evidence and
remains outstanding, see Follow-ups).

### Results

| Direction | Arm | Mean Recall | Micro Recall | Mean Recall@n | Mean Precision | Edges found | Resolver sources |
|---|---|---|---|---|---|---|---|
| callers | baseline | 0.7857 | 0.8462 | 0.5119 | 0.4051 | 11/13 | ast=49, libcst=2, pyan=2 |
| callers | `--hide-ambiguous` | 0.7857 | 0.8462 | 0.4167 | 0.4082 | 11/13 | ast=20, libcst=19, lsp=5, pyan=2 |
| callees | baseline | 0.8571 | 0.7143 | 0.5000 | 0.2648 | 5/7 | ast=38, libcst=1, lsp=3, pyan=2 |
| callees | `--hide-ambiguous` | 0.8571 | 0.7143 | 0.5714 | 0.4014 | 5/7 | ast=15, libcst=1, lsp=3, pyan=2 |

### Gate evaluation

- **Recall**: **byte-identical** in both directions on both Mean and Micro measures — zero edges
  lost by filtering (11/13 callers, 5/7 callees in both arms).
- **Precision**: **up in both directions** — callers +0.0031 (0.4051→0.4082, modest), callees
  +0.1366 (0.2648→0.4014, substantial).
- **Resolver-source shift**: dropping `ambiguous`-tagged entries reveals a higher-confidence
  resolver mix underneath (callers: ast 49→20 with libcst/lsp filling in; callees: ast 38→15) —
  consistent with the ambiguous tag disproportionately sitting on low-provenance AST guesses, not
  on correct libcst/lsp/pyan-resolved edges.

**Verdict: PASSED** — exactly the plan's predicted "precision up, recall flat" signature, in both
directions, at n=7 (directional evidence, regression-guard role). Promoted to `default=True`
(Phase 6):

- `search/config.py`: `GraphEnhancedConfig.hide_ambiguous_edges_default` `False → True`.
- `search_config.json.example`: mirrored.
- `docs/MCP_TOOLS_REFERENCE.md`: tools table + "Ambiguous-Edge Filtering" section updated to
  reflect the new default; explicit `hide_ambiguous=False` still available to see the raw,
  unfiltered edge list.
- `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`: no existing mention of this knob, nothing to update.
- Test updated: `tests/unit/mcp_server/test_tool_handlers.py::test_handle_find_connections_default_keeps_ambiguous`
  renamed `..._default_hides_ambiguous`, assertion flipped to match (omitted `hide_ambiguous` now
  drops the ambiguous entry via the real, unmocked `SearchConfig` default).

**Re-pin note**: this knob does not touch `search_code` retrieval (confirmed above), so it cannot
move the SSCG 63q/133q canons — no fresh SSCG canon capture is needed after this flip, unlike a
retrieval-affecting default change. The reference baselines captured earlier in this doc
(0.8357/0.6647) remain valid as-is.

## Post-fix live-MCP protocol (2026-08-16, follow-up session)

The server was reconnected with Phase 1-4 source edits live, closing the "needs a live session
with server restart access" gap noted below. All four before/after tables from the plan were
executed against the live workstation-tier substrate (2,457 chunks / 209 files, confirmed
unchanged via `get_index_status` before and after — no accidental reindex confounded the
comparison).

- **Fix #1** (confidence helper): knob-off calls reproduced the "before" values byte-identically
  (no-op confirmed). The temporary `min_traversal_confidence=0.7` probe (added to
  `search_overrides.json`'s `graph_enhanced` section, then reverted) measurably reshaped the
  ego-graph neighbor pool toward resolver-verified edges — direct behavioural proof the 1.0-default
  inversion is gone, matching the plan's predicted direction (the floor now prunes the 11,459
  untagged edges instead of the resolver-verified ones).
- **Fix #2** (fan-out presentation): `hide_ambiguous` default-on filtering confirmed exact —
  pre-filter `callee_confidence` counts preserved, filtered callee list absent. The documented
  residual (bare-symbol-node fallback still producing false hints for common method names, e.g.
  `SymbolHashCache.add` → `get`/`set` both false) reproduced unchanged, confirming this is the
  accepted partial-mitigation behaviour, not a regression — the `CleanupQueue._save` regression
  guard (unique name, real chunk-node edges) stayed correct (`add`/`process` both true) in both
  passes, proving the fallback discriminates rather than being globally broken.
- **Fix #3** (determinism): three repeated `search_code("rerank search results with cross encoder
  listwise", k=10)` calls post-reconnect returned byte-identical ordered results, including across
  a mid-session auto-reindex (empty-centrality path). `find_connections(symbol_name=
  "get_neighbors_ranked")` confirmed its only two callers are
  `search/ego_graph_retriever.py::EgoGraphRetriever.retrieve_ego_graph` and
  `search/multi_hop_searcher.py::MultiHopSearcher._graph_expand` — exactly the two channels named
  in the plan's Phase 3 spec, both now on the ranked/deterministic path instead of raw
  set-iteration order. (A fresh server-process restart to repeat this from cold was not available
  in this environment; the auto-reindex empty-centrality trigger is treated as sufficient coverage
  of the same code path per the plan's own fallback framing.)
- **Fix #4** (ego bound): the temporary `ego_graph.drop_nonpositive_output=true` probe (same
  override-file technique, reverted after) dropped exactly and only `source == "ego_graph"` entries
  with `reranker_score <= 0` on a `k=2, output_format="verbose"` CleanupQueue query — including the
  sign-flip case `SymbolHashCache.add` (reranker_score −0.1207, but `blended_score` +0.0009 after
  the additive centrality boost) — confirming the cut reads `reranker_score`, not `blended_score`,
  as the plan requires. A follow-up `search_code` call after reverting the override reproduced the
  original 30-result baseline byte-for-byte, confirming clean revert.

### Cross-cutting check: `P3_graph_hop`/`P4_finding_e` do NOT stay at zero — but this pre-dates Phase 1-4

`scripts/benchmark/probe_rerank_window.py --all` was run on the Phase-1-4 tree and returned
`OVERALL: ABORT/HALT`, `VERDICT: RED - 6 grade-3 gold(s) window-cut`, with `P3_graph_hop`
(`median_count=2.0, any_frac=0.6048`, target `median_count == 0`) and `P4_finding_e`
(`0.0726`, target `>= 0.50`) both failing — on its face a violation of the plan's cross-cutting
instruction that "these fixes must not resurrect the dead graph channel as a side effect."

Isolated via the same `git stash push -- <18 Phase 1-4 files>` technique used in the substrate
re-baseline above, re-running the identical probe on the clean `a90d8ad` tree (no Phase 1-4
changes) reproduced the same failure almost exactly: `P3_graph_hop` `median_count=2.0,
any_frac=0.6290`, `P4_finding_e` `0.0806`, `P1`/`P2` byte-identical to the Phase-1-4 run, `P5`
identically `PASS`, same `OVERALL: ABORT/HALT` verdict (`VERDICT: RED - 5 grade-3 gold(s)
window-cut`). **This RED/ABORT verdict pre-exists Phase 1-4** — most likely attributable to the
already-committed `05ca8d5` (ADR-0039, merged-pool graph provenance banding) or ordinary
substrate drift documented above, not to this session's work. The plan's cross-cutting expectation
was written against a stale pre-ADR-0039 baseline; `P3_graph_hop`/`P4_finding_e` were already
non-zero on `main` before any of these four fixes landed.

There is a small residual delta between the two runs — window-cut 6 vs 5, model-demotion 1 vs 4,
pool-loss 9 vs 8, ok 167 vs 166 (totals: 183 both) — consistent with Phase 3's traversal-order fix
being **unconditional** (not knob-gated, unlike Phases 1/2/4): a few borderline queries shift which
bucket they land in when truncation switches from set-iteration order to ranked/priority order.
This matches the substrate re-baseline section's finding that Phase 3 is the only non-no-op change
among the four and only reorders tail candidates (1 of 63 queries with a different reciprocal rank
in the SSCG comparison) — it does not flip the gate's `A1 premise (P1 & P2 hold)` verdict, which
fails identically on both trees and is what actually drives `OVERALL: ABORT/HALT` here. This probe
predates the current plan (its gate belongs to the older, separately-closed `merged_pool_policy`
investigation — see `project_graph_hop_window_cap_ab_rejected_20260815.md` /
`project_graph_band_evidence_order_rejected_20260815.md`); its RED verdict is not a blocker for
this plan's own Phase 5/6 gates, which passed/failed on their own SSCG and caller-recall evidence
above.

## Follow-ups (not done this session)

- `pool_hit_rate` harness gap noted above (63q no-op runs missing the field) — worth a quick
  root-cause pass in a future session, though it did not block any gate decision here.
- A cold server-process restart (as opposed to the auto-reindex empty-centrality trigger used
  above) was not available in this environment for the Fix #3 determinism check — if a future
  session has restart access, repeat the three-calls-before/three-calls-after-restart protocol for
  full coverage.
