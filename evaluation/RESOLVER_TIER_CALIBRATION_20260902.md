# Resolver tier calibration against execution-witnessed call edges (2026-09-02)

**Workstream**: WS-B (B1 tracer, B2 integrity, B3 per-tier scoring, B5 miss taxonomy) of
`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`.
**Decision record**: `docs/adr/0059-execution-witnessed-callgraph-ground-truth.md`.
**Status**: measurement complete; hand-labeling of the precision sample done 2026-09-02
(`RESOLVER_PRECISION_LABELS_20260902.md`); pyan call-position gate landed 2026-09-03 and
re-scored in section 12; B4 (pyan retention) decided there: pyan stays.

Every number below was read from the artifacts named in section 1 during this session. Nothing
in the search path, the resolvers, or their defaults was changed. No commit was made.

## 1. Artifacts

| Artifact | Path | Tracked |
| --- | --- | --- |
| Raw traced runs (3) | `evaluation/traced_runs/r1.json`, `r2.json`, `r3.json` | no (`.gitignore`) |
| Run log (pass/fail counts, timings) | `evaluation/traced_runs/full_runs.log` | no |
| Intersected, chunk-mapped ground truth | `evaluation/traced_callgraph.json` (`traced-callgraph/1`) | uncommitted |
| Per-tier score report | `evaluation/resolver_tier_scores.json` | uncommitted |
| Precision hand-label sample (40 rows, 10 per tier) | `evaluation/resolver_precision_sample.json` (`resolver-precision-sample/1`) | uncommitted |
| Traced goldens for `run_caller_recall.py` | `evaluation/caller_golden_traced.json`, `evaluation/callee_golden_traced.json` | yes (`d070066`) |
| Harness results | `evaluation/traced_runs/callers_recall_traced.json`, `callees_recall_traced.json`, `callers_recall_curated.json`, `callees_recall_curated.json` | no |
| Code | `evaluation/tracer/{collector,pytest_callgraph,build,scoring}.py`, `evaluation/index_locator.py`, `scripts/benchmark/traced_callgraph.py`, `tests/unit/evaluation/tracer/`, `tests/fixtures/tracer_pkg/` | yes (`d070066`) |

**Correction (2026-09-02 audit):** the tracer package and the traced goldens were marked
"uncommitted" above at capture time; `git ls-files` confirms both landed in `d070066`
alongside this file. The three JSON dumps (`traced_callgraph.json`, `resolver_tier_scores.json`,
`resolver_precision_sample.json`) were also committed in `d070066` but were untracked again by
the later `bb87513` ("chore: untrack regenerable evaluation dumps, keep benchmark inputs only"),
consistent with the standing rule that `evaluation/` dumps stay local — their "uncommitted" row
above is accurate as the current state, not stale.

## 2. Substrate

- Index: `claude-context-local`, model `codefuse-ai/F2LLM-v2-0.6B`, full CLI force reindex at
  01:49 on 2026-09-02 (`tools/batch_index.py --path . --mode force`, 76.7 s) so that chunk ids
  match the graph the tracer was mapped onto. 229 files, 2,760 chunks (function 714, method 883,
  class 149, decorated_definition 223, split_block 285, module 211, module_preamble 295).
- Stored exclude list reused unchanged: `_archive tests audit_reports benchmark_results htmlcov
  tmp code-search-extension`. `tests/` is therefore unindexed (0 chunks).
- Call graph after resolver injection: 6,418 nodes, 28,058 edges. `calls` edges by
  `resolver_source`: untagged (scored as `ast`) 12,956, `lsp` 1,423, `pyan` 1,205, `libcst` 498.
  After phantom removal and id normalization the scored tier sets are the `edges` column in
  section 5.
- Resolver defaults at capture (unchanged): `lsp_enabled=True`, `min_confidence=0.65`,
  `inject_on_incremental=False`; declared confidences `ast` 0.5/0.7, `pyan` 0.75, `libcst` 0.90,
  `lsp` 0.98.
- Python 3.11.15 (`sys.setprofile` collector; `sys.monitoring` unavailable).

## 3. Capture protocol and integrity (B2)

Command, run three times back to back, serial, no xdist, randomization disabled, hash seed
pinned:

```bash
PYTHONHASHSEED=0 ./scripts/test/run_tests.sh tests/unit -q -p no:randomly --timeout=0 \
  -p evaluation.tracer.pytest_callgraph --callgraph-trace \
  --callgraph-output evaluation/traced_runs/r1.json
```

| Run | Result | Wall time |
| --- | --- | --- |
| r1 (traced) | 4273 passed, 2 failed, 3 skipped | 165.0 s |
| r2 (traced) | 4273 passed, 2 failed, 3 skipped | 136.6 s |
| r3 (traced) | 4273 passed, 2 failed, 3 skipped | 135.8 s |
| baseline (untraced, same flags) | 4274 passed, 2 failed, 2 skipped | 91.8 s |

Slowdown 1.5x to 1.8x. The one extra skip under tracing is `test_plugin_inactive`, which skips
itself by design when the plugin is active. The 2 failures are identical in all four runs and
pre-date this work (section 10).

Integrity block of `evaluation/traced_callgraph.json`:

| Check | Value |
| --- | --- |
| runs | 3 |
| deterministic | true |
| dropped_nondeterministic | 0 |
| cross_function_edges | 1,894 |
| direct_cross_function_edges | 1,675 |
| unresolved_endpoints | 42 |
| unresolved_edge_endpoints | 69 |
| density_ok | true |
| schema_ok | true |

Mapping: 1,318 executed chunks (`EXEC`), 1,923 traced edges after mapping, 0 `test_edges`
(the `--callgraph-include-test-callers` flag was off). Dropped at build: `unmapped_endpoint` 42
(all module-level lambdas in `chunking/language_registry.py`, which own no chunk),
`self_loop` 361,658 (comprehension and generator frames collapsing onto their enclosing chunk).

## 4. Metric definitions (verbatim from `resolver_tier_scores.json`, key `definitions`)

- **D**: traced edges that are direct (external_depth 0) with both endpoints resolved to
  non-phantom graph nodes; one shared denominator for all tiers.
- **I**: traced edges with external_depth > 0, both endpoints resolved; scored in a separate
  column and never added to D.
- **E_t**: static call edges whose resolver_source is t (ast when absent), both endpoints
  non-phantom, ids normalized; a tier's stored edges are its marginal contribution over the
  tiers above it.
- **recall_marginal(t)** = |E_t ∩ D| / |D|.
- **recall_cumulative(≥t)** = |(∪ over t' ≥ t of E_t') ∩ D| / |D| down the ladder
  lsp > libcst > pyan > ast.
- **recall_ladder_total** = |E_all ∩ D| / |D|.
- **recall_indirect(t)** = |E_t ∩ I| / |I|.
- **prec_lb(t)** = |E_t ∩ E_traced| / |E_t| where E_traced is every traced edge (direct and
  indirect).
- **EXEC**: every chunk that owns at least one traced endpoint.
- **E_t_cov** = {e ∈ E_t : caller(e) ∈ EXEC}; caller-only restriction, since requiring the
  callee in EXEC would push the bound to 1 by construction.
- **prec_lb_cov(t)** = |E_t_cov ∩ E_traced| / |E_t_cov|.
- **unwitnessable(t)** = |E_t| − |E_t_cov|.
- **prec_est(t)** = (|E_t_cov ∩ E_traced| + p̂ · |E_t_cov minus E_traced|) / |E_t_cov| where p̂
  is the hand-labeled true-positive rate of the unwitnessed sample.
- **init_equivalence**: a traced callee `p.py:method:C.__init__` matches a static callee
  `p.py:class:C` and vice versa (both sides canonicalized to `class:C`); hits obtained this way
  are counted in `hits_via_init_equivalence`.
- **ast_name_only**: lenient column: a missed D edge counts as a name-only hit iff the graph has
  caller → phantom whose key equals the callee's bare name or `Class.method`; never added to any
  recall.

Denominators: |D| = 1,675, |I| = 222, |E_traced| = 1,894, |EXEC| = 1,318.

## 5. Per-tier results (B3)

| tier | edges | hits_D | recall_marginal | recall_cumulative | hits_I | recall_indirect | prec_lb | edges_cov | hits_cov | prec_lb_cov | unwitnessable | unlabeled_cov |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lsp | 1,421 | 816 | 0.4872 | 0.4872 | 3 | 0.0135 | 0.5764 | 1,026 | 819 | 0.7982 | 395 | 207 |
| libcst | 498 | 235 | 0.1403 | 0.6275 | 4 | 0.0180 | 0.4799 | 318 | 239 | 0.7516 | 180 | 79 |
| pyan | 1,183 | 183 | 0.1093 | 0.7063 | 3 | 0.0135 | 0.1572 | 723 | 186 | 0.2573 | 460 | 537 |
| ast | 3,891 | 301 | 0.1797 | 0.8860 | 13 | 0.0586 | 0.0802 | 2,437 | 312 | 0.1280 | 1,454 | 2,125 |

Ladder total: 6,876 edges, 1,484 of 1,675 D edges hit, **recall_ladder_total 0.8860**,
prec_lb 0.2189. `hits_via_init_equivalence` 98 (counted inside the hits above).
`ast_name_only`: 4 of the 191 misses have a caller → phantom name match.

`unlabeled_cov` = `edges_cov − hits_cov` is the population the hand-label sample is drawn from.

Reading guide:

- The lsp tier alone witnesses just under half of all direct executed edges, and 80% of its
  edges whose caller ran were actually taken. The remaining 20% are unlabeled, not wrong.
- libcst and pyan are marginal contributions after lsp overwrote whatever it also resolved, so
  their recall columns understate standalone recall by construction and cannot be compared with
  their declared confidences directly.
- pyan's `prec_lb_cov` (0.2573) is the only tier bound that sits far below its declared
  confidence (0.75). Whether the 537 unlabeled pyan edges are untaken-branch true positives or
  false positives is exactly what the sample decides; nothing about B4 is concluded here.
  **Update 2026-09-03:** the sample came back 0/10 true for pyan (every row was a non-call
  CLASS reference admitted as a `calls` edge); the fix and post-gate numbers are in section 12.
- The `ast` fallback is 57% of all stored edges and has the lowest bound (0.1280). The sample
  rows for this tier include several `MetadataStore.set` edges attached to callers that only use
  a builtin `set`; that is the name-only mechanism TraceEval calls class-name-as-callee.

### 5a. Re-run after ADR-0061 (split_block callee folding), 2026-09-03

`evaluation/RESOLVER_PRECISION_LABELS_20260902.md` found that callees inside long
(`split_block`-chunked) methods were mapped to their enclosing `class:` chunk because the
resolver line map excluded split fragments. ADR-0061 folds each split symbol's fragments into
one span that also covers the `def` line, keyed to the first fragment. Both arms below start
from the same stored graph with resolver provenance stripped, re-run `inject_call_edges` with
the full pyan → libcst → lsp pipeline, and score against the unchanged
`traced_callgraph.json` (denominators identical: |D| 1,675, |I| 222, |E_traced| 1,894,
|EXEC| 1,318). The stored graph had drifted since section 5 (6,535 nodes; the baseline arm
lands at 28,528 edges vs the 28,058 above), so the *baseline* column, not section 5, is the
comparison point. Script: `tmp/ab_split_callee.py` (scratch, not committed).

| tier | edges (old → new) | edges_cov (old → new) | prec_lb_cov (old → new) | recall_marginal (old → new) | recall_cumulative (old → new) |
|---|---|---|---|---|---|
| lsp | 1,437 → 1,848 | 1,023 → 1,249 | 0.7918 → **0.8159** | 0.4818 → 0.6048 | 0.4818 → 0.6048 |
| libcst | 533 → 731 | 321 → 425 | 0.7477 → 0.6894 | 0.1409 → 0.1701 | 0.6227 → 0.7749 |
| pyan | 1,276 → 1,234 | 754 → 896 | 0.2520 → 0.2511 | 0.1116 → 0.1325 | 0.7039 → 0.8704 |
| ast | 3,748 → 3,377 | 2,272 → 1,954 | 0.1325 → 0.0276 | 0.1731 → 0.0299 | 0.8770 → 0.8991 |

Ladder total: 6,874 → 7,021 edges, hits_D 1,469 → 1,506, **recall_ladder_total 0.8770 →
0.8991**, prec_lb 0.2168 → 0.2175; classified misses 206 → 169.

Inside-body `class:` targets (resolver-sourced `calls` edges whose target is a `class` chunk
and whose recorded line is not the class statement line): lsp 38 → **0**, pyan 10 → **0**.
libcst reads 72 → 96 but that count is not meaningful for libcst: libcst-only edges carry
`line=0` and upgraded ones keep the AST call-site line, so the line never identifies the callee.

Reading guide:

- The lsp gain is mostly on the *caller* side. A split method's `def` line is now inside a
  mapped span, so lsp probes 97 methods it previously never saw as callers; that is the
  +411 edges and the recall_marginal jump from 0.48 to 0.60. Precision of the covered edges
  rises 0.7918 → 0.8159 because the callee side no longer lands on class nodes.
- pyan's `prec_lb_cov` is flat (0.2520 → 0.2511). Its class-target problem is fixed (10 → 0)
  but that was never the bulk of its unlabeled edges; the pyan CLASS-admission issue in the
  precision-labels record stands.
- The `ast` and libcst marginal columns shrink or lose precision by construction: lsp now
  overwrites edges those tiers previously owned, and what remains for libcst is dominated by
  new split-method callers whose libcst resolution is weaker. Marginal accounting, not a
  regression of either resolver.
- Three of the 97 split groups have a `def`-to-body gap of 10+ lines (long decorators or
  signatures). `_find_def_position` in the lsp resolver scans only 10 lines from the span
  start, so those three are still not lsp callers. Follow-up, not addressed here.

## 6. Traced-golden harness and curated deltas

Traced goldens were emitted for every curated target in `EXEC` (positive-only semantics,
`category: "T"`), then run through `scripts/benchmark/run_caller_recall.py run --golden-path`
at k=50 with `hide_ambiguous=False`. Precision and `extra` columns are meaningless against
positive-only labels and are not reported.

| Golden | Queries | Recall (micro) | Mean recall@n | Skipped targets |
| --- | --- | --- | --- | --- |
| `caller_golden_traced.json` (TC001 TC002 TC003 TC006 TC007) | 5 | 1.0 (18/18) | 0.70 | C004 no traced direct callers; C005 target never executed |
| `callee_golden_traced.json` (TOB01 to TOB04, TOB07) | 5 | 1.0 (13/13) | 0.5167 | OB05, OB06 no traced direct callees |
| `caller_golden.json` (curated, pre-repair) | 7 | 0.9231 (12/13), mean 0.8571 | 0.369 | none |
| `callee_golden.json` (curated, pre-repair) | 7 | 0.7143 (5/7), mean 0.8571 | 0.500 | none; both misses are OB03 (`run_resolvers`, `upgrade_call_edge`), see TOB03 below |
| `caller_golden.json` (curated, repaired 2026-09-02) | 7 | 1.0 (23/23), mean 1.0 | 0.5238 | none |
| `callee_golden.json` (curated, repaired 2026-09-02) | 7 | 1.0 (7/7), mean 1.0 | 0.5714 | none |

Every traced-vs-curated difference, with cause:

- **TC001** (`evaluation/metrics.py:normalize_chunk_id` callers): 9 traced callers
  absent from curated C001 (`metrics.expand_retrieved_with_community_credit`,
  `metrics.expand_retrieved_with_containment`, `probe_harness.ProbeSession.instrument`,
  `probe_harness.load_golden_queries`, `probe_harness.replay_legs`,
  `tracer/scoring.emit_traced_golden`, `tracer/scoring.extract_static_edges`,
  `tracer/scoring.make_source_lookup`, and one more in `evaluation/`). Curated C001 is incomplete
  on this substrate; the graph finds all of them.
- **TC006**: traced adds `evaluation/tracer/build.map_endpoints` (new code).
- **TC007**: traced adds `tracer/build.build_line_map` and
  `search/call_edge_injection.inject_call_edges`; curated names
  `search/index_write_stage.IndexWriteStage.inject_call_edges`, which no longer makes the call
  after the extraction into `call_edge_injection.py`. Curated C007 is stale.
- **TOB01**: traced adds `LibCSTResolver.available` and `LSPResolver.available`.
- **TOB02**: traced adds `class:_TrackedVisitor` (instantiation, via init equivalence) and
  `_node_to_raw_chunk_id`.
- **TOB03**: traced has `call_edge_injection.inject_call_edges` and `get_search_config`;
  curated has `run_resolvers` and `upgrade_call_edge`, which are now reached indirectly through
  `call_edge_injection` (present in `I`, not `D`). Same refactor as TC007.
- **TOB04**: traced adds `matches_directory_filter`.
- **TOB07**: traced adds `_bump_version`.

Curated repairs applied 2026-09-02 from the deltas above (`evaluation/traced_runs/*_recall_curated_repaired.json`):
C001 gains the 9 missing direct callers (12 total); C007 retargets its caller to
`search/call_edge_injection.py:method:inject_call_edges` and adds `tracer/build.build_line_map`;
OB03 retargets to `search/call_edge_injection.py:method:inject_call_edges`, keeping
`run_resolvers` and `upgrade_call_edge`. Both curated goldens now score recall 1.0 on the same
graph. The `method:` form for the two module-level functions is the `normalize_chunk_id` image of
their `split_block` fragments (both exceed `max_chunk_lines`); the golden-set guard accepts that
alias for split-eligible nodes since the same date.

## 7. Miss taxonomy (B5)

191 direct executed edges are found by no tier. First-match order is the order below.

| Class | Count | Example (caller → callee) |
| --- | --- | --- |
| wrapper_routed | 20 | `chunking/languages/base.py:method:LanguageChunker._child_is_chunked → chunking/languages/cpp.py:method:CppChunker.should_chunk_node` |
| class_body_eval | 9 | `chunking/tree_sitter.py:class:TreeSitterChunker → chunking/languages/c.py:class:CChunker` (registry dict built in the class body) |
| via_external | 28 | `chunking/languages/base.py:method:LanguageChunker._load_language → chunking/language_registry.py:decorated_definition:LanguageSpec` |
| name_only_unresolved | 4 | `chunking/tree_sitter.py:method:TreeSitterChunker.chunk_parsed → chunking/languages/base.py:method:LanguageChunker.chunk_parsed` |
| dynamic_dispatch | 51 | `chunking/languages/base.py:method:LanguageChunker._apply_complexity_score → chunking/languages/glsl.py:method:GLSLChunker.get_node_complexity` |
| no_syntactic_call | 56 | `chunking/language_registry.py:decorated_definition:LanguageSpec → chunking/language_registry.py:function:_ts_loader` (heuristic: no call syntax in the caller chunk's source) |
| unclassified | 23 | `chunking/tree_sitter.py:method:TreeSitterChunker.parse_file → chunking/languages/_c_family.py:method:_CFamilyChunker.preprocess_source_for_parse` (dispatch with zero static candidates from that caller) |

Strict vs collapsed: 12 of the 20 `wrapper_routed` misses have a static A → B edge once the
`<locals>` wrapper frame is collapsed (`wrapper_collapsed_credits` 12). Reported beside, never
substituted into, the strict numbers.

`dynamic_dispatch` and `no_syntactic_call` together are 56% of misses; both are subclass method
dispatch through `LanguageChunker` and dataclass-held loader callables. They are outside what
any of the four static tiers can resolve without type information at the call site.

## 8. Live MCP spot check

Performed against the running server (`find_connections`, `max_depth=1`) after the CLI
reindex. Server-side `cleanup_resources` was needed first to release the metadata lock for the
reindex. Calls made while another process held the metadata store (the curated callee harness)
timed out and were retried serially afterwards; parallel `find_connections` calls also timed
out, so each check below was a single sequential call.

| Edge (tier attributed by scorer) | `find_connections` result |
| --- | --- |
| lsp: `chunking/file_summarizer.py:function:generate_file_summaries → _build_file_summary` | listed in `direct_callees`, `resolver_source: lsp`, `resolver_confidence 0.98` (confirmed) |
| libcst: `chunking/languages/base.py:method:LanguageChunker._get_chunking_config → search/config.py:function:get_chunking_config` | listed, `resolver_source: libcst`, 0.9 (confirmed) |
| pyan: `chunking/languages/cpp.py:method:CudaChunker._neutralize → chunking/languages/_c_family.py:function:blank_preserving_layout` | listed, `resolver_source: pyan`, 0.75 (confirmed); the same call also lists `_CFamilyChunker._neutralize` as `lsp` 0.98 |
| unclassified miss: `chunking/tree_sitter.py:method:TreeSitterChunker.parse_file` (three split fragments) should list no `preprocess_source_for_parse` callee | fragment `384-416` lists five `ast` callees (`_read_file_with_timeout`, `ParsedSource`, `_collect_error_line_ranges`, `get_chunker`, and a name-only `mcp_server/tools/responses.py:function:error`); fragments `418-471` and `473-505` list none. No `preprocess_source_for_parse` edge anywhere (miss confirmed; the `responses.error` entry is itself a name-only false positive of the kind the sample will label) |

## 9. Caveats and blind spots

- **Marginal provenance.** `run_resolvers` overwrites lower-tier edges in place, so each tier's
  stored set is what it added beyond the tiers above it. Standalone per-tier recall would need a
  four-way re-injection run per tier; not done. Do not publish ω values from section 5.
- **Positive-only labels.** A static edge absent from the trace is unlabeled, never false.
  `prec_lb` and `prec_lb_cov` are lower bounds; `prec_est` needs the hand-labeled sample.
- **Coverage follows the unit suite.** 1,318 of 2,760 chunks executed. Untested modules have no
  witnessed edges and their static edges are all `unwitnessable`.
- **Blind spots recorded in the report**: `tests/` is unindexed so test-to-project calls are never
  scored; dataclass-generated `__init__` runs from `<string>` and is invisible; threads started
  before the profiler installed are untraceable on 3.11; C-implemented callables (`sorted(key=)`,
  `map`) create no Python frame, so a callback shows as a direct edge from the caller.
- **Nondeterministic display counts in the harness.** `run_caller_recall.py`'s per-target
  `resolver_sources` histogram depends on which parallel MultiDiGraph edge is seen first after
  dedupe and varied between identical runs (TC001 showed `lsp 5 / libcst 26 / ast 14` then
  `ast 45` on the same graph file). Recall was identical. Gate on recall only.
- **Index status after capture** reports `index_is_current: false` with 15 added and 1 modified
  file: the new tracer package, tests and this record. The graph used for scoring predates them
  and does not contain them, which is correct for this measurement.
- **Untracked metadata write** during r2 (`metadata.db` mtime 01:53:14, WAL activity) was
  noticed, not investigated; chunk count was unchanged before and after.

## 10. Pre-existing failure, reported not fixed

`tests/unit/evaluation/test_golden_set_guard.py::test_golden_chunk_ids_exist_in_live_index`
fails for both `golden_dataset.json` and `golden_dataset_expanded.json` (3 drifted chunk ids
each) in all four runs, including the untraced baseline. Cause: Q12's gold
`mcp_server/tools/status_handlers.py:method:handle_get_index_status` now exists only as three
`split_block` fragments (`33-68`, `69-111`, `112-135`) after the function grew past the split
threshold in commit `9526267`. Repairing the gold implies a canon re-baseline
(`evaluation/CANON_20260901_REBASELINE.md` rules), which is a user decision and out of scope
for WS-B.

## 11. What this does and does not license

- Licensed: using `evaluation/traced_callgraph.json` as the positive set for any future
  resolver A/B on this substrate; using section 7 as the target list for resolver work
  (`dynamic_dispatch` and `no_syntactic_call` first, as they dominate).
- Not licensed: changing any declared confidence, removing pyan (B4), or treating any
  `prec_lb` as a precision estimate before the sample in
  `evaluation/resolver_precision_sample.json` is labeled.

## 12. Post-gate re-score: pyan CLASS callees gated on call position (2026-09-03)

**Change**: commit `27262f2` (`fix(callgraph): gate pyan CLASS callees on call position`),
`chunking/relationships/external_call_graph.py` and its unit tests only. pyan records every
*use* of a class in `uses_edges`, so admitting the CLASS flavor leaked type annotations,
enum-member access, `self.<attr>` reads (resolved to the binding `__init__`) and instance
references as 0.75-confidence `calls` edges. `_TrackedVisitor.visit_Call` now records, per
caller namespace, the resolved callee names that sit in call position (plus `Class.__init__`
for a class call); `PyanResolver` skips CLASS callees and `__init__` METHOD callees absent from
that record. `super()` is excluded from the record. Attribute calls count only when the
resolved node's name equals the syntactic attribute, because pyan's attribute fallback returns
the *class* node for `self._index.clear()` (labeled rows 23 to 25). Names recorded inside
lambda/comprehension scopes are folded onto the parent alongside pyan's `collapse_inner`.
CLASS admission is kept rather than replaced by the `__init__` METHOD edge because pyan
contracts the undefined `__init__` node of classes without an own initializer (dataclasses).
Declared confidences are unchanged.

**Substrate**: the change was measured in the linked worktree
`.claude/worktrees/heuristic-dijkstra-6e3607` (branch `claude/heuristic-dijkstra-6e3607`), force
reindexed with the same excludes and `PYTHONHASHSEED=0`, scored against the unchanged
`evaluation/traced_callgraph.json`. Denominators on that index: |D| = 1,671, |I| = 222,
|E_traced| = 1,894, |EXEC| = 1,318, `traced_unresolved` 4. The worktree index differs from the
section 2 main index by the intervening `evaluation/tracer` commits, which is why the
baseline row below (worktree, pre-change HEAD) is not identical to section 5; compare the two
worktree rows with each other, not with section 5.

| arm | pyan edges | hits_D | recall_marginal | recall_cumulative | prec_lb | edges_cov | hits_cov | prec_lb_cov | unwitnessable | unlabeled_cov |
|---|---|---|---|---|---|---|---|---|---|---|
| main index, section 5 | 1,183 | 183 | 0.1093 | 0.7063 | 0.1572 | 723 | 186 | 0.2573 | 460 | 537 |
| worktree, pre-change | 1,267 | 186 | 0.1113 | 0.7062 | 0.1492 | 753 | 189 | 0.2510 | 514 | 564 |
| worktree, post-gate | 648 | 184 | 0.1101 | 0.7050 | 0.2886 | 310 | 187 | 0.6032 | 338 | 123 |

Other tiers on the post-gate worktree index (for the ladder line): lsp 1,405 edges /
0.4853 / 0.7957; libcst 524 / 0.1400 / 0.7461; ast 3,809 / 0.1795 / 0.1291. Ladder total
6,273 edges, `recall_ladder_total` 0.8845 (pre-change 0.8857), `hits_via_init_equivalence`
96, misses 193 (pre-change 191).

**The two lost hits** are both traced edges from `_TrackedVisitor._prescan_one` and
`_TrackedVisitor.process_one` to `class:_TrackedVisitor` in the file being edited, classified
`no_syntactic_call` / name-absent. They were accidental hits of the leak mechanism, not
instantiations; losing them is the intended behaviour, and they are a self-index artifact of
the substrate.

**Hand-labeled rows**: 9 of the 10 pyan rows in `resolver_precision_labels.json` (rows 20 to
29) are gone from the post-gate index. Row 22 (`CodeEmbedder.cleanup → class:ModelLoader`)
survives because it is a different mechanism: a METHOD callee (`ModelLoader.load`) reached by
attribute flow whose `split_block` chunks collapse to the class chunk. That is outside the
CLASS gate and remains open.

**`precision_estimate.py` reading**: with the 2026-09-02 labels, pyan `prec_est` moves
0.2510 → 0.6032 (ω 0.25 → 0.60), now "above tag:exact 0.4228, CI clear". That p̂ term is
biased low: the 0/10 sample was drawn from the pre-gate population and consisted entirely of
the leak class that no longer exists, so a fresh post-gate sample was drawn and labeled.

**Post-gate pyan sample (labeled 2026-09-03, same rule as section 5's sample)**: 10 rows,
evenly spaced over the 123 unlabeled covered pyan edges of the post-gate index. Files (local,
untracked per the `evaluation/` rule): `evaluation/resolver_precision_sample_postgate_20260903.json`,
`evaluation/resolver_precision_labels_postgate_20260903.json`. Only the pyan rows are labeled;
26 of the 30 lsp/libcst/ast rows differ from the 2026-09-02 sample, whose labels remain
authoritative for those tiers.

| row | caller → callee | label | mechanism |
|---|---|---|---|
| 20 | `LanguageChunker.function_node_types` → `LanguageChunker._get_splittable_node_types` | false | attribute flow: reads `self.splittable_node_types`, bound in `__init__` from the callee |
| 21 | `CodeEmbedder.embed_query` → `CodeEmbedder.__enter__` | false | `with self._lifecycle_lock:` enters a `threading.Lock`; pyan resolved the dunder to the class's own |
| 22 | `CodeEmbedder.embed_chunk` → `CodeEmbedder.__exit__` | false | same as row 21 |
| 23 | `TraceCollector.uninstall` → `_current_thread_profile` | false | attribute flow: passes `self._prev_thread_profile`, bound in `install()` from the callee |
| 24 | `handle_switch_embedding_model` → `with_mutation_lock` | false | decorator application at module import, not in the handler body |
| 25 | `handle_find_connections` → `RelationshipAnalyzer.from_searcher` | **true** | direct call (`search_handlers.py:363`) |
| 26 | `_install_layer3_embedding_split` → `class:CodeEmbedder` | false | monkeypatches class attributes; never constructs |
| 27 | `PathFilter.all_includes_unmatched` → `PathFilter._parse_all` | false | attribute flow: reads `self.include_patterns` / `self.include_hits`, bound in `__init__` via the callee |
| 28 | `HybridSearcher.add_embeddings` → `GraphIntegration.from_storage` | false | attribute flow: calls `self._graph.populate_from_embeddings`; `_graph` was bound from the callee |
| 29 | `CodeIndexManager.search` → `FaissVectorIndex.search` | **true** | direct call (`indexer.py:305`) |

p̂ = 2/10, Wilson 95% [0.057, 0.510]. Estimator on the post-gate scores: pyan
`prec_est` **0.6826**, range [0.6257, 0.8055], **ω 0.70**, declared 0.75 inside the range,
"above tag:exact 0.4228, CI clear". Wilson n=10 is thin; the ω is indicative, not a
re-declaration.

What the remaining false rows say: the CLASS leak is gone (only row 26 is a class target,
and it is a monkeypatch, not a reference leak). The dominant residual mechanism is
**attribute flow** (rows 20, 23, 27, 28, plus row 22 of the earlier sample): pyan resolves a
`self.<attr>` read to the function whose return value was bound to that attribute elsewhere,
and emits a FUNCTION/METHOD callee the body never calls. Second is **dunder misresolution**
(rows 21, 22): `with`/context-manager protocol calls on a non-class attribute resolve to the
enclosing class's own `__enter__`/`__exit__`. Both are callable-flavor callees, so the
call-position gate cannot touch them; a fix would need pyan's attribute-flow edges
distinguished from its direct-call edges, which `uses_edges` does not expose. Row 24 is a
decorator-application edge, arguably a correct static dependency but not a body call under
the pinned rule.

**B4 decision**: pyan's marginal recall over libcst is unchanged (0.1113 → 0.1101, 186 → 184
direct hits), far outside the run-to-run noise on this substrate, so the plan's removal
condition ("marginal recall inside noise") is not met. pyan stays, at 51% of its former edge
count, with lower-bound precision 0.6032 and a labeled `prec_est` of 0.6826 (ω 0.70) whose
range contains the declared 0.75. Declared confidences remain a separate decision.

## 13. Composed-HEAD verification (2026-09-03) — the two fixes measured together, first time

§5a (ADR-0061 split-callee fold) and §12 (pyan CLASS call-position gate) were each measured in
isolation, on substrates that did not carry both fixes at once (§12's worktree baseline
0.8857/0.8991 predates ADR-0061). This section re-runs the full execution-witnessed protocol on
`development` HEAD with both fixes composed, after a clean Phase 0 force reindex
(233 files / 2,832 chunks, `user_excluded_dirs` unchanged) and a fresh 3-run trace capture
(`evaluation/traced_runs/r{1,2,3}.json`, all `4437 passed, 3 skipped`). Integrity block:
`deterministic=False dropped_nondeterministic=6` (all six drops are `CodeEmbedder.__del__`
GC-finalizer timing noise, unrelated to call-graph resolution) `schema_ok=True density_ok=True`.

```
denominators: D=1732 I=225 E_traced=1953 EXEC=1352 traced_unresolved=0
lsp     recall_marginal=0.6109 recall_cumulative=0.6109 prec_lb=0.5681 prec_lb_cov=0.8267 |E_t|=1873
libcst  recall_marginal=0.1663 recall_cumulative=0.7771 prec_lb=0.4111 prec_lb_cov=0.6948 |E_t|=720
pyan    recall_marginal=0.1282 recall_cumulative=0.8695 prec_lb=0.4106 prec_lb_cov=0.5799 |E_t|=548
ast     recall_marginal=0.0306 recall_cumulative=0.8984 prec_lb=0.0170 prec_lb_cov=0.0265 |E_t|=3347
ladder  recall_ladder_total=0.8984 prec_lb=0.2492 |E_all|=6329
```

| metric | pre-fix (worktree) | §12 post-fix (isolated) | composed HEAD (this section) | verdict |
|---|---|---|---|---|
| pyan edges | 1,267 | 648 | 552 (live graph) | large drop confirmed |
| pyan `prec_lb_cov` | 0.2510 | 0.6032 | 0.5799 | clears the ≥0.50 bar |
| pyan `recall_marginal` | 0.1113 | 0.1101 | 0.1282 | rose, not dropped — no interference |
| `recall_ladder_total` | 0.8857 | 0.8991 | 0.8984 | 0.0006 under target, noise-level |
| lsp `recall_marginal` | 0.4818 | 0.6048 | 0.6109 | exceeds ADR-0061's own headline claim |

**Verdict: pyan call-graph fidelity is confirmed improved on the composed HEAD, measured
independently rather than taken from the docs.** `prec_lb_cov` more than doubling while
`recall_marginal` simultaneously *rises* rules out the failure mode the plan was checking for
(a precision gain bought by dropping recall via the CLASS gate over-triggering). `lsp` benefits
too, past its own §5a-isolated number — the split-block span fold and the pyan gate compose
without interference. This closes the verification question the burst of `adf4efb`/`dfbf48b`/
`050f684`/`4d8fbdc`/`748b6f1`/`e48736d`/`09c4a34`/`cc6419e` commits made a claim about; nothing
here changes the B4 retention decision or the declared `ResolverConfidence` values, per §12's
own scope note (this measures the precision floor, not the point estimate).

## §14 — Policy S+ (`pyan_strict_callable_gate`) A/B: REJECTED, recall floor breached

Follow-up to §12's residual-leak finding (8/10 false rows: attribute flow + dunder
misresolution, both callable-flavor, unreachable by the existing CLASS-only gate). Design
**S+**: a second per-caller *spelled*-name witness set `S` (from `node.func.attr`/`node.func.id`,
recorded unconditionally in `visit_Call`) alongside the existing dotted set `D`
(`call_position_names`), gating all five callee flavors instead of just CLASS/`__init__`:
CLASS → `callee.name ∈ S` only (no `D` fallback — closes §12 row 26's `ast.Name`-shaped hole);
`__init__` → `"__init__" ∈ S` or owning class's bare name `∈ S`; FUNCTION/METHOD/STATICMETHOD/
CLASSMETHOD → `callee.name ∈ S` **or** `callee.get_name() ∈ D`. Shipped behind a temporary
`CallGraphConfig.pyan_strict_callable_gate` flag (default `False`, no `benchmark_locked`
citation — investigation knob only) so both arms share one HEAD and one trace capture. Full
implementation + a `TestCallableGate` regression suite (6 tests against a real-pyan fixture
covering attribute-read, `with`-dunder, and decorator-application false-edge mechanisms, plus
three survives-the-gate controls) passed the whole unit suite unchanged with the flag off
(4,450 passed / 2 skipped, byte-identical to today's-HEAD baseline).

**Protocol**: `git rev-parse HEAD` pinned at `2256b21`. Re-captured 3 fresh traces on the
Item-1-edited substrate (§13's traces are invalidated by any edit to
`external_call_graph.py` — it is itself traced, and `EndpointKey` is line-number-keyed) —
`PYTHONHASHSEED=0`, all three runs `4449 passed, 3 skipped`, `traced_callgraph.py build`
integrity `deterministic=True dropped_nondeterministic=0`. Built `traced_callgraph.json`
**once**; scored **both arms against the identical file** (`search_config.json` surgically
single-key-edited, byte-exact backup + SHA-256 verified each direction, never `save_config()`)
so the A/B denominators are exactly equal — this is the controlled comparison, not a comparison
against §13's numbers (which used a different trace capture and are not bit-comparable; see the
"re-derive, don't inherit" rule already established for Item 2).

```
denominators (both arms, identical): D=1712 I=220 E_traced=1928 EXEC=1330 traced_unresolved=0

OFF (flag=false, today's default)         ON (flag=true, S+)
pyan  recall_marginal   = 0.1262          pyan  recall_marginal   = 0.1157   (-0.0105)
pyan  prec_lb_cov       = 0.5733          pyan  prec_lb_cov       = 0.7363   (+0.1630)
pyan  |E_t|             = 548             pyan  |E_t|             = 394     (-154, -28.1%)
ladder recall_ladder_total = 0.8616       ladder recall_ladder_total = 0.8511 (-0.0105)
```

**Acceptance gate (pre-registered, "precision up, recall not down"): FAILED.** `prec_lb_cov`
clears the bar by a wide margin (+0.163, both above the §13-derived 0.5799 threshold and the
same-substrate 0.5733 floor). Both recall metrics drop below **every** applicable floor —
same-substrate (`recall_marginal` 0.1262, `recall_ladder_total` 0.8616) and the stricter §13
number (0.1282 / 0.8984) alike. This is a small (~1 point absolute, ~8% relative on pyan's own
marginal recall) but fully deterministic, reproducible-on-this-substrate loss — not measurement
noise: both arms were scored against one identical `traced_callgraph.json`, and the only
variable between the two force-reindex passes was the config flag.

**Root cause, diagnosed via a diff of the two arms' `via_external`-classified misses** (13 D
edges lost under S+ that were present under legacy; `via_external` = the caller's source
references the callee's bare name but never spells it as a direct call — see
`evaluation/tracer/scoring.py:317-318`):

| Mechanism | Count | Example |
|---|---|---|
| `@property`/`@cached_property` getter read via plain attribute access (`obj.total_chunks`) | 7/13 | `SearchOrchestrator._search` → `SearcherView.total_chunks`/`.is_ready`/`.is_hybrid`; `CodeIndexManager.add_embeddings` → `FaissVectorIndex.ntotal`; `FaissVectorIndex.load` → `MmapVectorStorage.count` |
| `cls(...)` construction inside a `@classmethod` factory (literal spelling is `cls`, never the class's own name) | 3/13 | `FilterEngine.from_dict` → `class:FilterEngine`; `MerkleDAG.from_dict` → `class:MerkleDAG`; `MultiLanguageChunker.for_project` → `class:MultiLanguageChunker` |
| Unclassified FUNCTION-flavor (not investigated further — 2/13, below the threshold that would change the verdict) | 2/13 | `_c_family.py:neutralize_preprocessor_conditionals`/`CudaChunker._neutralize` → `blank_preserving_layout` |
| Ambiguous CLASS target (not investigated further) | 1/13 | `TraceCollector.to_payload` → `Endpoint` |

Both diagnosed mechanisms are **structural**, not tunable: a property access has no `ast.Call`
node at all (nothing to record into either `S` or `D`), and `cls` is never the callee's own
name, so it can never populate `S`, and CLASS callees deliberately have no `D` fallback under
S+ (that is precisely the design choice that closes §12 row 26). Under legacy/OFF, these edges
survived because the pre-existing gate only ever screened CLASS/`__init__` — S+'s extension of
the gate to METHOD/FUNCTION/STATICMETHOD/CLASSMETHOD is what newly exposes the property-getter
gap, and property getters account for the majority (7/13, 54%) of the measured loss.

**Disposition: reverted wholesale**, per the plan's pre-registered failure path. `search_config.json`
restored from its byte-exact backup (SHA-256 verified), `git checkout --` on all five changed
files (`chunking/relationships/external_call_graph.py`, `search/call_edge_injection.py`,
`search/config.py`, `search_config.json.example`,
`tests/unit/chunking/relationships/test_external_call_graph.py`), force reindex to restore the
on-disk graph, whole-suite bookend green (4,438 passed / 2 skipped, matching the pre-Item-1
baseline). The full diff is archived locally at
`tmp/item1_pyan_strict_callable_gate_REJECTED_20260903.patch` (not tracked — `tmp/` is
gitignored) for anyone who wants to resume this design rather than restart it.

**Recommendation for a future attempt ("S++")**: both diagnosed mechanisms look independently
fixable without touching the CLASS-gate fix that motivated S+ in the first place — (a) exempt
`@property`/`@cached_property`-decorated (chunk-kind `decorated_definition` with a property
decorator) callees from the call-position screen entirely, since no syntactic witness can ever
exist for them; (b) when the literal call spelling is `cls` inside a `@classmethod`, treat it as
if it spelled the owning class's bare name (mirroring the existing `__init__`
owning-class-name special case). The two mechanisms account for 10/13 (77%) of the measured
loss; whether closing them recovers enough of `recall_marginal`/`recall_ladder_total` to clear
the gate is unmeasured and would need its own A/B, not assumed from this diagnosis. The
remaining 3/13 (unclassified FUNCTION-flavor, ambiguous CLASS) were not investigated further —
below the threshold that would change this verdict.
own scope note (this measures the precision floor, not the point estimate).
