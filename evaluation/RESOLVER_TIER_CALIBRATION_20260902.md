# Resolver tier calibration against execution-witnessed call edges (2026-09-02)

**Workstream**: WS-B (B1 tracer, B2 integrity, B3 per-tier scoring, B5 miss taxonomy) of
`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`.
**Decision record**: `docs/adr/0059-execution-witnessed-callgraph-ground-truth.md`.
**Status**: measurement complete; hand-labeling of the precision sample NOT done (user task);
B4 (pyan retention) NOT decided here.

Every number below was read from the artifacts named in section 1 during this session. Nothing
in the search path, the resolvers, or their defaults was changed. No commit was made.

## 1. Artifacts

| Artifact | Path | Tracked |
|---|---|---|
| Raw traced runs (3) | `evaluation/traced_runs/r1.json`, `r2.json`, `r3.json` | no (`.gitignore`) |
| Run log (pass/fail counts, timings) | `evaluation/traced_runs/full_runs.log` | no |
| Intersected, chunk-mapped ground truth | `evaluation/traced_callgraph.json` (`traced-callgraph/1`) | uncommitted |
| Per-tier score report | `evaluation/resolver_tier_scores.json` | uncommitted |
| Precision hand-label sample (40 rows, 10 per tier) | `evaluation/resolver_precision_sample.json` (`resolver-precision-sample/1`) | uncommitted |
| Traced goldens for `run_caller_recall.py` | `evaluation/caller_golden_traced.json`, `evaluation/callee_golden_traced.json` | uncommitted |
| Harness results | `evaluation/traced_runs/callers_recall_traced.json`, `callees_recall_traced.json`, `callers_recall_curated.json`, `callees_recall_curated.json` | no |
| Code | `evaluation/tracer/{collector,pytest_callgraph,build,scoring}.py`, `evaluation/index_locator.py`, `scripts/benchmark/traced_callgraph.py`, `tests/unit/evaluation/tracer/`, `tests/fixtures/tracer_pkg/` | uncommitted |

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
|---|---|---|
| r1 (traced) | 4273 passed, 2 failed, 3 skipped | 165.0 s |
| r2 (traced) | 4273 passed, 2 failed, 3 skipped | 136.6 s |
| r3 (traced) | 4273 passed, 2 failed, 3 skipped | 135.8 s |
| baseline (untraced, same flags) | 4274 passed, 2 failed, 2 skipped | 91.8 s |

Slowdown 1.5x to 1.8x. The one extra skip under tracing is `test_plugin_inactive`, which skips
itself by design when the plugin is active. The 2 failures are identical in all four runs and
pre-date this work (section 10).

Integrity block of `evaluation/traced_callgraph.json`:

| Check | Value |
|---|---|
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
|---|---|---|---|---|---|---|---|---|---|---|---|---|
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
- The `ast` fallback is 57% of all stored edges and has the lowest bound (0.1280). The sample
  rows for this tier include several `MetadataStore.set` edges attached to callers that only use
  a builtin `set`; that is the name-only mechanism TraceEval calls class-name-as-callee.

## 6. Traced-golden harness and curated deltas

Traced goldens were emitted for every curated target in `EXEC` (positive-only semantics,
`category: "T"`), then run through `scripts/benchmark/run_caller_recall.py run --golden-path`
at k=50 with `hide_ambiguous=False`. Precision and `extra` columns are meaningless against
positive-only labels and are not reported.

| Golden | Queries | Recall (micro) | Mean recall@n | Skipped targets |
|---|---|---|---|---|
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
|---|---|---|
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
|---|---|
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
