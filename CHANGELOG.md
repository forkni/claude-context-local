# Changelog

All notable changes to the Claude Context Local (MCP) semantic code search system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **`.tdgraph.json` TouchDesigner network indexing** (ADR-0062, opt-in) — a new pseudo-language
  chunker (`chunking/td_network_chunker.py`, `TDNetworkChunker`) builds `operator`/`class`/`network`
  chunks directly from a TD network JSON snapshot (no tree-sitter grammar involved), so
  `search_code`, `find_connections`, and `find_path` work over TD operators, their scripts, and the
  `td` class hierarchy the same way they work over Python symbols. 8 new `RelationshipType` members
  (`wires_to`, `docked_to`, `contains`, `references_op`, `binds_to`, `exports_to`, `scripted_by`,
  `shares_tag`). Gated
  behind `ChunkingConfig.enable_td_network_indexing` (`search_config.json`, default `False`) —
  inert on every existing indexed project, including this repo's own self-index, until a project
  opts in.
- **C/C++ call-edge tier** (ADR-0060) — C and C++ chunks now emit `calls`/`imports`/
  `instantiates`/`inherits` edges the same way Python chunks do, closing a gap where every C/C++
  chunk was graph-isolated (`find_connections`/`find_path` returned nothing for them). Tree-sitter
  name matching only (confidence 0.6, no type resolution — `v.size()` and `myObj.size()` are
  indistinguishable); libclang/clangd tiers remain deferred per ADR-0035's unmet reopening
  condition (no `compile_commands.json`/clangd/libclang available in this environment). New
  `CallGraphConfig.ambiguous_fanout_cap` (default `3`) caps per-symbol candidate fan-out for
  C-family languages only — Python resolution is unaffected by construction (language-gated) and
  by measurement (63q/133q golden-set canons flat, see
  `evaluation/CANON_GATE_FANOUT_CAP_20260903.md`).

### Fixed

- **`find_connections`: `direct_callers`/`indirect_callers` are now `calls`-edge lists only.**
  `RelationshipAnalyzer.analyze_impact` fed every inbound edge type into the caller lists (and
  into `caller_confidence`/`total_impacted`), so on a TouchDesigner operator chunk its `contains`/
  `docked_to`/`shares_tag`/`instantiates` neighbours all appeared as "callers" tagged
  `confidence: "exact"` — eleven phantom callers on `Logger/Logger` in the first real export.
  Python chunks were affected the same way whenever `inherits`/`imports`/`uses_type` edges pointed
  at them; it only looked like a call graph because those are rare. The caller traversal now
  passes `relation_types=["calls"]` (mirroring the existing outbound-callee filter) and the typed
  `relationships` sections get their own one-hop all-types inbound query, so `contained_by`,
  `docked_by`, `shares_tag_with`, etc. are unchanged. Legacy untyped edges still normalise to
  `calls` in `CodeGraphStorage.get_edge_data`, so old-format call edges are not dropped.
  `GraphQueryEngine._traverse_inbound`/`_traverse_outbound` now also *expand* only through
  edges that match the requested `relation_types`, so a depth-N `indirect_caller` sits at the end
  of N real `calls` edges — previously the BFS walked through a `contains`/`docked_to` hop and
  then picked up `calls` edges into the neighbour (four Python "indirect callers" on the same TD
  operator). Unfiltered queries (`relation_types=None`) are unchanged.
- **`.tdgraph.json` chunker: `scripted_by` edges were silently dropped.** The real exporter emits
  them (`{type: scripted_by, src: <host op>, dst: <DAT>, par, via}` — 110 in the first export)
  but `_SIMPLE_EDGE_MAP` had no row, so each hit the "Unrecognized edge type" debug branch.
  Added `"scripted_by" → RelationshipType.SCRIPTED_BY` with `par`/`via` metadata, exporter-native
  direction. Index-time change: re-chunk the graph file (re-export in TD, or force reindex) to see
  the edges. Fixture gains one `scripted_by` edge (`edge_count` 38).
- **`.tdgraph.json` chunker: real line spans and no nameless root id** (ADR-0062 follow-up, found
  on the first real TouchDesigner export). Operator/class/network spans are now derived from the
  JSON file's own element positions (`TDNetworkChunker._json_element_spans`) instead of the
  exporter's `node_line_spans`, which holds Python-DAT script line counts, not file positions —
  previously ~75% of operator chunks carried a `0-0` span and the rest meaningless values; class
  and network chunks were hard-coded `0-0`. The exported target COMP (a depth-0 node) no longer
  becomes an operator chunk with an empty name (`<file>:0-0:operator`); it is folded into the
  `network` chunk and every edge touching it (`contains`/`wire`/`dock`/`shared_tag`) attaches
  there. A `_drop_nameless` guard rejects any chunk whose id fails `ChunkId.parse`. Operator chunk
  ids change (`...:330-358:operator:Logger/Logger`) — any existing index built with the gate on
  needs one full reindex of that project. Fixture gains a root node + root-hosted `dock`/`shared_tag`
  edges; 12 new/rewritten unit tests derive expected spans from the fixture text.

### Changed

- **`CallGraphConfig.resolvers` and `CallGraphConfig.ambiguous_fanout_cap` are now
  `benchmark_locked`** (22 → 24 `FORBIDDEN_AUTO_TUNE_KEYS`) — `resolvers` cites
  `RESOLVER_TIER_CALIBRATION_20260902` §11/§12 (B4 decided pyan stays: post-gate
  `prec_lb_cov` 0.2510→0.6032, `recall_marginal` flat); `ambiguous_fanout_cap` cites ADR-0060
  and `evaluation/CANON_GATE_FANOUT_CAP_20260903.md` (cap holds voro-engine ambiguous-edge growth
  to +90% vs +190% uncapped, Python retrieval canons flat). Neither changes behavior — the lock
  only blocks `search/index_probe.py`'s automated probe from rewriting the field; both remain
  legitimate manual config edits. Introduces a citation-genre-prefix convention
  (`[retrieval]`/`[latency]`/`[graph]`/`[precision]`/`[pending]`/`[decision]`) on all
  `benchmark_locked` strings so a reader can tell a measured-and-pinned retrieval result apart
  from a settled human decision without a second metadata key.
- **`CallGraphConfig.inject_on_incremental` is now `benchmark_locked`** (24 → 25
  `FORBIDDEN_AUTO_TUNE_KEYS`), citation genre `[latency]` — ADR-0044 measured +1.58s on a 4-file
  fixture and left the default (`False`) unquantified for larger projects;
  `evaluation/INJECT_ON_INCREMENTAL_COST_20260903.md` closes that gap on this 233-file repo:
  +36-38s per incremental pass (~10-19x the opt-out baseline), flat in K because the resolver
  pass rescans the whole indexed set regardless of change size. ADR-0044's own reopening
  condition (a changed-file-scoped injection variant landing) is unmet, so the default stays
  `False`. `search/call_edge_injection.py` also gained a permanent inline
  `resolve=%.1fs total=%.1fs` timer on its `[CALL_EDGES] Injected...` log line (plain
  `time.perf_counter()`, not `utils.timing.timed()` — decorating either injection entry point
  flips that chunk's kind to `decorated_definition:` and breaks five golden dataset entries).

### Migration

- **Opting in to `.tdgraph.json` indexing.** Set `"chunking": {"enable_td_network_indexing": true}`
  in a project's `search_config.json`, then run a non-incremental reindex
  (`index_directory(..., incremental=False)`) — a new extension means new files, not a format
  change to existing ones, so `INDEX_VERSION` is not bumped (ADR-0037 precedent). The Merkle
  hashing scheme (`merkle/merkle_dag.py`) will also compute a real content hash instead of a
  `size=0` stat hash for `.tdgraph.json` files once the flag is on, producing a one-time "modified"
  flip on those files and their ancestor directory nodes.
- **Reindex required to see C/C++ call edges.** File content is unchanged by this change, so
  `index_directory(..., incremental=True)` (the default) will not re-chunk already-indexed C/C++
  files and the old zero-edge chunks will persist. Run
  `index_directory(<project>, incremental=False)` (or `tools/batch_index.py --mode force`) once
  per C/C++ project to pick up the new edges.

### Security

- **nltk CVE-2026-81726 / GHSA-8mgp-746c-j5xp** (pathsec bypass in model-artifact APIs,
  affects every release through 3.10.3, no fixed release yet) assessed **not applicable**: the
  affected tagger/parser/maxent persistence APIs are unused and `pathsec` is never enabled; the
  only nltk surface is stopwords/stemmer/tokenize with hardcoded data paths
  (`search/bm25_index.py`). Deferred in the `pyproject.toml` CVE ledger with a reopening
  condition (raise the floor once nltk publishes >3.10.3); Dependabot alert #33 dismissed
  `not_used`. The predecessor deferral for CVE-2026-12243 no longer flags on 3.10.3 and was
  folded into the same ledger entry.

---

## [0.26.0] - 2026-09-02

Three weeks of post-v0.25.0 work in one release (158 commits). Retrieval side: the Track A +
remaining-levers campaigns (2026-08-14), a merged-pool / ego-graph research log (2026-08-15 to
2026-09-02) in which every arm was pre-registered, measured on the deterministic harness, and
rejected, and the 2026-08-16 / 2026-08-19 defect-closure sweeps. The only default that flipped is
`find_connections.hide_ambiguous` (now on). Architecture side: the ADR-0039 to ADR-0059 deepening
wave (`BaseSearcher.execute`, `IndexWriteStage`, `ResourceRefresher`, enricher spec rows, derived
`ToolSpec` guard flags, `TraversalPolicy`, `spec(benchmark_locked=...)`), each behaviour-preserving
and ratcheted by a test. Plus a real content-based `index_is_current` verdict (ADR-0058), CUDA
routing (ADR-0054), test-suite hardening Phases 13-14, and three canon re-baselines ending at the
2026-09-01 pin. Dispositions live under `evaluation/*_2026MMDD.md`; decisions under `docs/adr/`.

### Added

- **`hide_ambiguous` on `find_connections`** — hides `"ambiguous"`-tagged entries from
  `direct_callers`/`direct_callees`/`indirect_callers`; confidence breakdowns and
  `total_impacted` intentionally remain pre-filter totals, and `dependency_graph` is unfiltered.
  Shipped opt-in on 2026-08-14, then **promoted to default-on** on 2026-08-16
  (`GraphEnhancedConfig.hide_ambiguous_edges_default = True`) after its A/B gate passed:
  recall byte-identical both directions, precision up both
  (`evaluation/CONFIDENCE_EGO_AB_20260816.md`). Pass `hide_ambiguous=False` for unfiltered edges.
- **`include_top_callees` on `search_code`** (opt-in, default `false`, 2026-09-02) — symmetric
  twin of `include_top_callers`: up to 2 `{name, file}` callee hints per result from raw
  call-graph out-edges. Resolved chunk targets rank first (resolver confidence descending);
  unresolved bare-symbol targets follow with `file: ""`. One `EnricherSpec` row + one
  `ResultEnricher` row (ADR-0049).
- **`include_signatures` on `search_code`** (opt-in, default `false`, 2026-08-18) — attaches a
  signature-only `signature: str` view per result. Measured ~687 tokens/query overhead (~36% over
  the compact payload) in `evaluation/CONTEXT_COST_PROBE_20260818.md`; module chunks are skipped,
  non-Python chunks degrade to the first 3 raw lines (≤600 chars). Never touches scoring.
- **Real index-freshness verdict** (ADR-0058) — `get_index_status` now returns
  `index_is_current` (True/False/null; a content-only Merkle diff against the working tree, so a
  freshly built index never reads stale just because a timestamp is old) plus `pending_changes`
  `{added, modified, removed}`, and accepts `job_id`. `list_projects` gained
  `check_freshness=True` for the same per-model verdict on any project without `switch_project`.
  Closes the ADR-0004 layering gap (`mcp_server/index_freshness.py`).
- **`graph_enhanced.drop_ambiguous_traversal_edges`** (default `false`, benchmark-locked) —
  drops `tag:ambiguous` call edges *during* ego-graph and multi-hop traversal (as opposed to
  `hide_ambiguous`, which only filters `find_connections` display). Offline replay screen passed
  at the bar, not above it (`evaluation/AMBIGUOUS_EDGE_REPLAY_20260902.md`); stays off pending a
  live A/B. Carried by the new `TraversalPolicy` object (see Changed).
- **`call_graph.inject_on_incremental`** (default `false`, ADR-0044) — opt-in re-injection of
  resolver-attributed pyan/LibCST/LSP call edges on incremental passes; the default keeps
  incremental passes AST-only to avoid the measured +1.58 s per-pass cost.
- **Merged-pool provenance bands** (`MergedPoolBand`, ADR-0039) and
  **`reranker.graph_hop_window_cap`** (default `0` = off, benchmark-locked) — the merged-pool
  rerank window now bands graph-hop candidates explicitly rather than by incidental sort order.
  The cap A/B was then **rejected** at both doses (`evaluation/POOL_ORDER_CAP_AB_20260815.md`)
  and the evidence-ordered band probe discharged with zero headroom
  (`evaluation/GRAPH_BAND_EVIDENCE_PROBE_20260815.md`). Both ship default-off.
- **Execution-witnessed call-graph ground truth** (ADR-0059) — `scripts/benchmark/` gained a
  witness pipeline that records resolver-tier outputs at execution time plus a split-aware golden
  guard; the curated caller/callee goldens were repaired against it
  (`evaluation/RESOLVER_TIER_CALIBRATION_20260902.md`,
  `evaluation/UNTAGGED_EDGE_WITNESS_20260902.md`).
- **`evaluation.probe_harness`** (ADR-0040) — one importable seam for offline retrieval probes
  (hash-seed pin, searcher construction, arm overrides); the pre-existing probe scripts and
  `run_sscg_benchmark.py` migrated onto it. `evaluation/` is packaged as importable with its data
  files excluded from wheels.
- **`include_top_callers` on `search_code`** (opt-in, default `false`) — attaches up to 2
  `{name, file}` caller hints per result from raw call-graph in-edges (chunk-id and
  bare-symbol-name node lookups, deduplicated before the top-2 cut).
- **jina-reranker-v3.5 support** — version-aware length kwargs; model selectable but rejected as
  the default reranker after A/B showed no recall upside over jina-reranker-v3.
- **Rejected-but-shipped mechanisms (all default-off, measured, do not enable without re-gating)**:
  A1 `graph_hop_call_evidence_enabled` (seed displacement fails the recall gate), A2
  `traversal_confidence_weighting_enabled`/`min_traversal_confidence` (structurally inert at
  shipped depth/floor), A4 `reranker.doc_representation_mode="signature_head"` (CI-negative recall
  on both datasets; −19% reranker latency is the only win — priced-in opt-in, settled into
  `FORBIDDEN_AUTO_TUNE_KEYS`). A3 final-pool graph reserve was NOT built (probe gate failed).
- **CUDA (`.cu`/`.cuh`) indexing support** — routed to the existing `tree-sitter-cpp` grammar via a
  `CudaChunker` that blanks CUDA-only execution-space attributes (`__global__`, `__device__`, ...)
  and `<<<grid, block>>>` kernel-launch syntax ahead of parsing (0 → 18 files / 2,091 lines indexed
  on the motivating projects, ERROR-line rate 3.0% → 0.0%). No new dependency; `language_name`
  stays `"cpp"`. See `docs/adr/0054-route-cuda-extensions-to-cpp-grammar.md`.
- **`chunking.max_file_size_bytes`** (default `5242880` / 5 MB, range 1024–104857600) — caps file
  size on the chunking path via `configure_chunking`; `chunk_file()` previously had no size guard
  even though the adaptive-sizing profiler did.
- **`graph_enhanced.centrality_exclude_phantoms`** (default `False`, file-only —
  `FORBIDDEN_AUTO_TUNE_KEYS`) — excludes phantom placeholder nodes (unresolved call/symbol targets)
  from centrality computation across all four centrality methods. Read-only pre-flight found
  phantoms are 60.7% of graph nodes and 75% of the top-20 raw-PageRank nodes on this repo's own
  index, with the single highest-PageRank node itself a phantom (`"str"`) — max-normalizing against
  it suppresses `centrality_bm25_boost` for over 99% of real chunks. Ships default-off pending a
  pre-registered A/B (re-tuning `centrality_boost_threshold` inside the arm, not just flipping the
  flag). See `docs/adr/0055-exclude-phantom-nodes-from-centrality.md`.
- **`CodeGraphStorage.prune_orphan_symbol_nodes()`** — removes phantom placeholder nodes once they
  drop to degree 0, wired into the incremental-reindex path right after the `remove_file_nodes`
  loop. Insurance against unbounded phantom accumulation on long-lived incrementally-reindexed
  projects; provably a no-op on a from-scratch index. Same ADR as above.

### Changed

- **Architecture-deepening wave (ADR-0039 to ADR-0057), all behaviour-preserving** —
  `BaseSearcher.execute(request)` seam collapses `SearchOrchestrator` dispatch (ADR-0048);
  `IndexWriteStage` owns index-adds and the injection gate for full and incremental passes
  (ADR-0052); `ResourceRefresher` protocol lifts MCP process-resource release out of
  `IncrementalIndexer` (ADR-0053); result enrichment is a registry (`RESULT_ENRICHERS` + one
  `EnricherSpec` row per opt-in, ADR-0049); MCP parameter defaults are single-sourced in
  `mcp_server/config_schema.py` (ADR-0046); `SearchResult.source` is a `ResultSource` `StrEnum`
  (ADR-0047); the embedding-document composer is extracted from `CodeEmbedder` (ADR-0045);
  `graph_scoring_stage`'s upward `mcp_server` import is deleted (ADR-0051); `rerank_by_query`'s
  four primitive knobs became `RerankWindowPolicy`; the MCP tool registry/dispatch collapsed into
  a single `ToolSpec` table whose guard flags derive from the handler decorators (ADR-0057);
  per-layer confidence-unknown defaults stay per-layer by decision (ADR-0050). Each seam is
  ratcheted by a test so it cannot silently regress.
- **`TraversalPolicy` parameter object** (`graph/traversal_policy.py`, 2026-09-02) — the seven
  traversal knobs (`relation_types`, `max_depth`, `exclude_import_categories`, `edge_weights`,
  `min_confidence`, `confidence_weighting`, `drop_ambiguous`) travel as one frozen dataclass.
  `CodeGraphStorage.get_neighbors_ranked(chunk_id, policy)` is the seam; `get_neighbors(...)`
  keeps its loose-kwarg shape as the convenience. `TraversalPolicy.ego(...)` /
  `.graph_hop(...)` derive the gates from config at the two production call sites, and
  `policy.gates_edges` short-circuits the per-edge lookups when no gate is armed. 63q canon
  replayed with 0 MRR movers.
- **Benchmark locks declared on `spec()` rows** — `spec(benchmark_locked="<citation>")` on each
  pinned config field; `SearchConfig._BENCHMARK_LOCK_CITATIONS` derives from those rows and
  `search/index_probe.py`'s `FORBIDDEN_AUTO_TUNE_KEYS` / `BENCHMARK_LOCK_CITATIONS` are views over
  it plus the single routing lock `INDEX_ROUTING_LOCKED_KEYS = {"embedding.model_name"}`. The two
  hand-typed parallel tables are gone (ADR-0022 addendum); `ego_graph.max_neighbors_per_hop` and
  `ego_graph.drop_nonpositive_output` joined the locked set after their A/Bs were rejected.
- **CUDA sources route to the `cpp` grammar** (ADR-0054) — `.cu`/`.cuh` are chunked as C++
  (kernels, `__device__` functions, host launchers) instead of being skipped.
- **Phantom nodes excluded from centrality** (`graph_enhanced.centrality_exclude_phantoms`,
  default `false`, benchmark-locked; ADR-0055) — unresolved call targets no longer absorb
  PageRank mass when enabled; ships off pending the pre-registered A/B.
- **GLSL's chunker-native call/relationship-edge bridge generalized into a spec-row table** —
  `chunking/relationships/edge_specs.py`'s `EdgeEmissionSpec`/`EDGE_EMISSION_SPECS`, keyed by
  language name, replaces `MultiLanguageChunker`'s three `tchunk.language == "glsl"` switches
  and two bridge methods. Behavior-preserving (all `test_glsl_relationships.py` tests, the
  `test_chunker_parity.py` snapshot gate, and the 63q/133q/F-via-similar SSCG canons
  unchanged); clears the way for a C/C++ call-edge tier (ADR-0035) to land as one new row
  instead of a widened switch. See `docs/adr/0056-spec-row-edge-emission-seam.md`.
- **`ToolSpec.mutation_lock`/`.requires_index` are now derived properties**, read off each
  handler's `__mcp_guards__` stamp (set by `@with_mutation_lock`/`@require_indexed_project` via
  `functools.wraps` propagation) instead of 36 hand-typed kwargs across the 18 spec rows — a row
  can no longer drift from its handler's actual decorator chain. Replaces the ~130-line
  bytecode-reflection test (`co_names` grepping) with a stamp-derivation ratchet in
  `test_tool_specs.py` plus a new behavioural test proving `index_directory`'s internal lock is
  actually acquired at runtime. Behavior-preserving: derived values are byte-identical to the
  pre-refactor hand-typed ones on all 18 rows. See
  `docs/adr/0057-derive-tool-guard-flags-from-decorators.md`.
- **`DEFAULT_IGNORED_DIRS` grew by 12 vendored/dependency-tree directory names** (`third_party`,
  `thirdparty`, `third-party`, `3rdparty`, `vendor`, `vendored`, `extern`, `deps`, `_deps`,
  `subprojects`, `submodules`; mirrored into `DEPENDENCY_TREE_DIRS`). Files under these directory
  names drop out of the merkle walk on the next reindex and their chunks are removed — an
  unannounced but correct index shrink for any existing project with a directory matching one of
  these names. Use additive `include_dirs` (ADR-0036) to bring specific paths back if needed; the
  effective exclusion list is visible via `get_index_status`'s `default_excluded_dirs`.

- **Benchmark canons re-pinned** (deterministic, PYTHONHASHSEED=0) three times in this window,
  each a comparability break rather than a trend: 2026-08-14 post-campaign 0.8722/0.6843 →
  2026-08-22 LSP re-baseline 0.8462/0.6482 (index 2,403→2,611 chunks; `[lsp]` extra dark
  2026-08-20→08-22 then re-locked) → **2026-09-01 P0 re-baseline: 63q MRR 0.8419, 133q 0.6378,
  F-via-similar 0.8843** (219 files / 2,642 chunks, LSP confirmed live, one stale Q12 gold
  repaired first). The 09-01 pin is the published baseline. See `docs/BENCHMARKS.md`,
  `evaluation/CANON_20260822_LSP_REBASELINE.md`, `evaluation/CANON_20260901_REBASELINE.md`.
- **Measured and rejected, no default changed** (all pre-registered, paired-CI gated) —
  merged-pool ordering A/B, neither arm (`evaluation/POOL_ORDER_AB_20260815.md`); leg-depth ×
  fusion and TM2C2 probes (`evaluation/LEG_DEPTH_FUSION_AB_20260815.md`,
  `evaluation/TM2C2_FUSION_PROBE_20260814.md`); ego-graph tail cut
  `ego_graph.drop_nonpositive_output` (`evaluation/CONFIDENCE_EGO_AB_20260816.md`); ego gate-2
  cap relief `max_neighbors_per_hop` 10→50 (`evaluation/EGO_GATE2_AB_20260901.md`);
  duplicate-crowding and cross-system probes (`evaluation/DUPLICATE_CROWDING_PROBE_20260817.md`,
  `evaluation/CROSS_SYSTEM_*_20260817.md`).
- **`mcp_server/tool_registry.py`'s config-backed bounds/enums now derive from `search/config.py`'s
  `spec()` metadata** (new `mcp_server/config_schema.py`, pure refactor — every property is
  byte-identical to the post-fix schema above except the deletions "publish invariants, never
  values" mandates; see `docs/adr/0042-publish-invariants-not-values.md`). The 18 verbatim
  `output_format` blocks collapse to one shared `OUTPUT_FORMAT_PROPERTY` definition, and
  `search_mode`'s enum derives once via `SEARCH_MODE_ENUM` instead of two hand-listed copies. The
  parity test (`tests/unit/mcp_server/test_tool_registry.py`) widens from a 4-tool parametrized
  check to a whole-registry ratchet asserting every `minimum`/`maximum`/`enum`-carrying property is
  classified as either config-backed or explicitly hand-typed with a documented rationale — a
  hand-typed bound can no longer be added without either classification catching it or the ratchet
  going red. One field, `search_code.max_context_tokens`, lost its unbacked `minimum`/`maximum`
  entirely: no `search/config.py` field ever governed it, so under the same rule nothing was
  derived to replace it. `mcp_server/tool_handlers.py`'s `__all__` now derives from
  `TOOL_DISPATCH.values()` instead of hand-restating all 18 handler names a third time.

### Fixed

- **PR #62 review** (2026-09-02) — `CodeEmbedder.cleanup()` now calls
  `EmbeddingDocumentComposer.clear_caches()`: the composer's mtime-keyed file caches were never
  evicted over a process-lifetime embedder (the `ModelPoolManager` slot), an unbounded-growth
  path across repeated reindexes of large trees. `CudaChunker._LAUNCH_CFG` no longer stops at the
  first `>` inside a `<<<grid, block>>>` launch config — a ternary or shift (`n > 0 ? n : 1`,
  `n >> 2`) previously left the launch unblanked; the body now admits any `>` that does not
  start the closing `>>>`. Both regression-tested.
- **`start_mcp_server.cmd` model menu** — embedding menu labels re-aligned with the code
  defaults (BGE-M3 `[DEFAULT]`, F2LLM-v2-0.6B `[RECOMMENDED 12GB+]` citing the 2026-09-01
  canon); Jina reranker v3.5 removed from the reranker submenu (measured-and-rejected,
  `evaluation/JINA_V35_AB_20260814.md`).
- **Four live-MCP call-graph defects** (2026-08-16, `evaluation/CONFIDENCE_EGO_AB_20260816.md`)
  — confidence-default inversion, ambiguous-edge fan-out, dead BFS priority / nondeterministic
  traversal order, and ego-graph tail flooding.
- **Defect-closure sweep D1–D12** (2026-08-19, `evaluation/DEFECT_CLOSURE_20260819.md`) —
  `find_connections.indirect_callers` deduplicated and sorted (ADR-0041); `ego_graph_enabled` is
  a two-way gate (`False` now really disables expansion); parent-expansion's fabricated `0.0`
  labelled `unscored`; `find_similar_code` zero-result contract and the `NEVER_DROP_EMPTY_KEYS`
  gap (`similar_chunks`) closed; MCP-layer lock scoping, error propagation, key-set scope and
  reset contract; probe pass classification and funnel-width test drift; `min_bm25_score` and
  the embedding-document degraded-path caps now read from config instead of literals; stale
  `.bat` launcher references in tests.
- **Force reindex blocked by a live FAISS mmap handle** — the handle is released
  deterministically before the index directory is purged.
- **Metadata clear self-heal + C-family macro-wrapped declarations** (ADR-0025 addenda) — stale
  `.deleting` debris is discarded when a live `metadata.db` exists (no resurrection of
  old-generation rows on shadowed rename), rows are emptied before reset with a loud post-clear
  failure if any remain; `repair_macro_wrapped_declarations` in
  `chunking/languages/_c_family.py` fixes adjacent-declaration boundaries (e.g. `extern "C"`
  blocks), with regression coverage.
- **Stale Q12 golden** — the primary expected chunk had drifted from kind
  `decorated_definition` to `method`; repaired in both datasets and the audit re-run clean
  before the 2026-09-01 canon.
- **`ego_graph_k_hops`/`ego_graph_max_neighbors_per_hop` omission fallback** — `search_code`
  hardcoded literals `2`/`10` as the value used when these args were omitted, shadowing
  `EgoGraphConfig.k_hops`/`.max_neighbors_per_hop`. On the explicit-enable path
  (`ego_graph_enabled=True`), a configured non-default value was silently ignored. Byte-identical
  on an unconfigured install (2 == 2, 10 == 10).
- **`mcp_server/tool_registry.py` schema/config divergences** (documentation only — `input_schema`
  is never validated at runtime) — six confirmed defects corrected: `output_format`
  (×18) hand-typed `default: "compact"` while `OutputConfig.format = "ultra"` and carried no
  `spec(choices=)` until now; `search_code.k`'s `maximum: 100` had no backing invariant until
  `SearchModeConfig.max_k` gained `spec(range=(1, 100))`; `ego_graph_k_hops`'s `maximum: 5`
  disagreed with the real `spec(range=(1, 3))` (now `3`); `ego_graph_max_neighbors_per_hop` had no
  `spec(range=)` until `EgoGraphConfig.max_neighbors_per_hop` gained `range=(1, 50)`;
  `max_age_minutes`'s `default: 5` disagreed with `max_index_age_minutes = 30.0`;
  `find_connections.hide_ambiguous`'s `default: False` disagreed with
  `hide_ambiguous_edges_default = True`. Per "publish invariants, never values", every stale
  `default` was deleted rather than corrected — descriptions now end in "Omit to use the server's
  configured value (`get_search_config_status.<field>`)." `find_path`'s short-form
  `output_format` description was also reconciled to the long-form text used by the other 17.
  `get_search_config_status` gained two previously-missing keys, `ego_graph_k_hops` /
  `ego_graph_max_neighbors_per_hop`, so that pointer is truthful.
- **BOM-tolerant pyan/import resolvers** — files starting with a UTF-8 byte-order mark previously
  failed silently in the pyan and import-resolver call-edge tiers; both now strip a leading BOM
  before parsing.
- **Ambiguous-resolution edges were miscounted as phantom edges** — an ambiguous call-target
  resolution creates no phantom node, but was counted in `phantom_edges` as if it had. Split out
  into a separate `ambiguous_edges` counter in `search/graph_integration.py`.

### Testing

- **Test-suite hardening Phases 13–14** (`tests/TESTING_GUIDE.md`) — coverage re-scoped to the
  package (`tools/` dropped) with a ratcheted `fail_under`; `pytest-timeout` added and an env
  leak fixed; the golden-set guard collapsed from ~2,200 parametrized cases to per-file cases,
  so the unit count drops from 5,8xx to **4,351 collected** with no coverage lost; pure
  `mcp_server`/`utils` cores covered; weak `assert_called_once` sites upgraded and fixed sleeps
  removed; a complexity / CRAP gate (radon + crap4py) added; `test_hybrid_search.py` de-mocked
  and its mutation-testing gaps closed. Current counts: 4,351 unit · 102 fast_integration ·
  20 integration · 108 slow_integration.
- New ratchets: `EDGE_EMISSION_SPECS` drift, `ToolSpec` guard-stamp, `IndexWriteStage` seam
  ownership, resource-refresher seam, split-aware golden guard, `TraversalPolicy` set/ranked
  equivalence.

### Dependencies

- **Dependency audit 2026-09-02** (`audit_reports/2026-09-02-1253-audit-summary.md`) — 180
  packages audited, 5 CVEs across 4 packages:
  - **setuptools 81.0.0 → 84.0.0** — fixes CVE-2026-59890 / GHSA-h35f-9h28-mq5c (high).
    Installed into the venv ad hoc (`uv pip install setuptools==84.0.0`) — it **cannot be
    locked**: torch 2.11.0 declares `setuptools<82`, so `uv.lock` stays at 81.0.0 and any
    `uv sync --locked` reverts the venv to 81.0.0 (re-run the ad-hoc install afterwards).
    Durable fix waits on torch 2.13.0 or a `[tool.uv] override-dependencies` entry.
  - **torch 2.11.0+cu128** — CVE-2025-3000 (GHSA-rrmf-rvhw-rf47), fix at 2.13.0; deferred
    — ML-core, requires tested ecosystem upgrade beyond this release scope.
  - **nltk 3.10.3** — PYSEC-2026-3740 / CVE-2026-81726, no fix released yet; monitor.
  - **sqlitedict 2.1.0** — PYSEC-2026-1939 / CVE-2024-35515, no fix released yet; monitor.
  - 56 packages outdated beyond the above — swept the same day, see next entry.
- **Safe-update sweep 2026-09-02** (`audit_reports/{before,after}-fixes-2026-09-02.json`) —
  every package updated one at a time with the full unit suite between steps (4,349 → 4,352
  passed, 2 skipped, `pytest-randomly` shuffling on), then `fast_integration` (102) and
  `integration` (20). Post-sweep audit: only the two no-fix CVEs remain (nltk, sqlitedict).
  - **Retrieval / resolver stack**: `sentence-transformers` 5.7.0 → 6.0.1 (`CrossEncoder.predict`
    now upcasts logits to float32 before activation — reranker scores can shift, canon re-run
    below), `transformers` 5.14.1 → 5.16.1, `tokenizers` 0.22.2 → 0.23.1, `pyan3` 2.6.2 → 2.8.1,
    `mcp` 2.0.0 → 2.1.1 (+ `mcp-types`).
  - **pyan3 2.8 pipeline**: upstream dropped `cull_inherited` and moved `cull_subsumed` to the
    end behind a `cull_subsumed_edges` constructor flag; `_TrackedVisitor.postprocess`
    (`chunking/relationships/external_call_graph.py`) mirrors the new
    `resolve_imports → contract_nonexistents → expand_unknowns → collapse_inner → cull_subsumed`
    order (16 tests failed on `ImportError: cull_inherited` before the fix). `docs/CALL_GRAPH_TUNING.md`
    pipeline listing updated.
  - **Test plugins**: `pytest-randomly` 4.1.0 → 5.0.0, `syrupy` 5.5.3 → 6.0.0 (27 snapshots pass).
  - **Tooling / transitive** (43): `ruff` 0.16.5, `pydantic` 2.13.5 / `pydantic-core` 2.46.5 /
    `pydantic-settings` 2.15.0, `cryptography` 50.0.1, `protobuf` 7.36.1, `opentelemetry-*`
    1.44.0 (+ `semantic-conventions` 0.65b0), `sqlalchemy` 2.0.52, `coverage` 7.16.0,
    `virtualenv` 21.7.8, `typer` 0.27.2, `click` 8.5.0, `regex` 2026.9.3, `idna` 3.19,
    `cosmic-ray` 8.7.0, `cyclonedx-python-lib` 11.12.0, `pipdeptree` 4.2.3, `pygments` 2.21.0,
    `platformdirs` 4.11.7, `filelock` 3.32.5, `gitpython` 3.1.61, `joblib` 1.6.0, and the
    remaining patch-level tail (`build`, `charset-normalizer`, `greenlet`, `msgpack`,
    `narwhals`, `stevedore`, `typing-inspection`, `wcwidth`, `linkify-it-py`, `nab-*`, …).
  - **Not upgradeable**: `tree-sitter` 0.25.2 → 0.26.0 — no bundled grammar wheel targets the
    0.26 ABI yet (python 0.25.0, cpp 0.23.4, c 0.24.2, javascript 0.25.0, typescript 0.23.2,
    go 0.25.0, rust 0.24.2, c-sharp 0.23.5, glsl 0.2.0); `tree-sitter>=0.25.0,<0.26` pin stays.
    `fsspec` held by the `datasets` `<=2025.10.0` constraint; `torch` untouched (ML-core).
  - **Post-sweep canon** (`canon_63q_r1_20260902_deps`, force reindex, 232 files / 2,795 chunks
    vs the pin's 219 / 2,642 — growth is the source committed since 2026-09-01, golden audit
    clean on both datasets; resolver mix 28,640 edges / lsp 1,443 / pyan 1,295 / libcst 524):
    63q MRR **0.8345** vs the 0.8419 pin and 0.8425 on the same-day pre-sweep run. The whole
    delta is Q77, a rank-1/rank-2 swap between the two near-tie `index_documents` methods
    (`HybridSearcher` over `BM25Index`) — every recall@k, pool_hit (1.0) and the other 62
    queries are unchanged, consistent with the float32 reranker-logit change. Recorded as
    drift, pin not re-based.
- **`evaluation/` slimmed to inputs only** (2026-09-02): 51 regenerable benchmark/probe run dumps
  (~28 MB) untracked; `.gitignore` now ignores `evaluation/*.json` except the eleven inputs that
  scripts and tests read (`golden_dataset*.json`, `caller/callee_golden*.json`,
  `hard_query_candidates.json`, `commit_mined_candidates.json`, the three pinned
  `raw_mcp_results_{hybrid,bm25,semantic}.json` snapshots).
  Write-ups (`.md`) and modules stay tracked; local copies of the dumps are untouched and every
  one is reproducible from its `scripts/benchmark/` producer named in the matching write-up.
- Dependency audits 2026-08-20 and 2026-09-01 (`audit_reports/`); `setproctitle` repaired;
  `uv.lock` synced for radon/crap4py; `evaluation/` packaged as importable.

### Migration

- **Existing C/C++ indexes need one `incremental=False` reindex** to pick up the declarator-recovery
  and preprocessor-conditional-neutralization parsing fixes bundled in this batch — both change how
  *already-registered* `.c`/`.cpp`/`.h` extensions parse, so an incremental pass alone won't
  reprocess unchanged files. `.cu`/`.cuh` are exempt: registering them flips their merkle
  hash-strategy from name/size/mtime to content, so they read as modified and self-migrate on the
  next incremental pass with no explicit reindex required.

## [0.25.0] - 2026-08-13

Closes out PR #57 review findings before merge: two real chunking bugs fixed (nested same-named
container linkage, templated prototype/alias naming), one reviewer claim disproven with evidence
(pure-C headers parse cleanly under the `cpp` grammar), one false positive documented with a
regression assertion (anonymous namespace/enum name is absent, never `""`), and a minor
declarator-descent dedup — on top of the C++ chunking parity work itself (20 → 27 file
extensions, headers now indexed).

### Added

- **C++ chunking parity** (20 → 27 file extensions) — `.h`, `.hpp`, `.hh`, `.hxx`, `.inl`, `.ipp`,
  `.tpp` now route to the `cpp` tree-sitter grammar (`chunking/language_registry.py`), so C++
  headers are chunked and searchable for the first time; previously none of these extensions were
  supported at all (`is_supported()` returned `False` for every one of them), so entire
  header-only codebases were invisible to search. New container-node traversal seam
  (`_CONTAINER_NODE_TYPES`, `chunking/languages/base.py`) lets `CppChunker` register
  `class_specifier`, `struct_specifier`, `union_specifier`, and `namespace_definition` as
  containers whose nested methods chunk
  separately instead of being swallowed into one opaque blob — see ADR-0038 for why this is
  scoped to C++ only, with the equivalent Rust (`impl_item`) and C# (`namespace_declaration`)
  swallowing bugs verified live and deliberately deferred. `chunking/languages/cpp.py` rewritten
  from a 57-line stub: declarator-unwrapping name extraction shared with C via new
  `chunking/languages/_c_family.py` (`unwrap_declarator_name`), function/container node-type
  overrides, and a `should_chunk_node` narrowing so template-wrapped classes still chunk once
  instead of twice.

### Fixed

- **C name extraction gaps** (`chunking/languages/c.py`) — pointer-returning function
  definitions (e.g. `int* getPtr()`) previously returned `name=None` because the old direct-child
  scan only matched a bare `function_declarator`, not one wrapped in `pointer_declarator`; now
  unwrapped via the shared `_c_family.unwrap_declarator_name`. Anonymous struct/enum typedef
  metadata (`typedef struct {...} Color;`) previously returned `name=None` because only plain
  `identifier` children were checked; the new type name is a `type_identifier` child, which is
  now also checked.
- **`INDEX_VERSION` bump declined** for this change (ADR-0037) — the field is BM25-document-format-
  scoped and warn-only (`bm25_index.py`); bumping it here would false-alarm every indexed
  Python-only project for an unrelated C++ chunking change. The `chunker_version` snapshot marker
  proposed alongside it is deferred, not rejected — recorded so it isn't re-litigated.
- **Nested same-named container `parent_chunk_id` collisions** (`chunking/multi_language_chunker.py`)
  — a C++ file with two same-named containers at different nesting depths (e.g. a reopened
  `namespace A { namespace A { ... } ... }`) resolved every child's `parent_chunk_id` to whichever
  container was chunked *last*, regardless of actual nesting. `class_chunk_map` now keys each name
  to a list of `(start_line, end_line, chunk_id)` spans and resolves to the innermost span that
  actually encloses the child, falling back to the last-registered span when no span contains it
  (load-bearing: Python `split_block` chunks can truncate a class span short of a method's real
  start line, so strict containment alone would silently drop `parent_chunk_id` for that
  pre-existing, non-colliding case).
- **Templated header-only prototypes and aliases chunked nameless** (`chunking/languages/cpp.py`)
  — `template<typename T> void proto(T v);` and `template<class T> using Ptr = T*;` both chunked
  with `name=None`. The `template_declaration` metadata scan only matched
  `function_definition`/`class_specifier`/`struct_specifier`/`union_specifier` as template
  children, and the latter three were unreachable there (`should_chunk_node` already returns
  `False` for a template-wrapped class/struct/union, so those chunk directly and never reach this
  branch). Now matches `function_definition`/`declaration`/`alias_declaration` — the two dead
  branches are replaced with the two node types that actually needed handling.
- **Deduplicated declarator-descent fallback** (`chunking/languages/_c_family.py`) — the
  `declarator` field-then-first-named-child fallback was implemented twice, once each in
  `unwrap_declarator_name` and `declarator_is_function_shaped`; extracted into a shared
  `_next_declarator()` helper used by both. No behavior change.

## [0.24.0] - 2026-08-12

119 non-merge commits since the `v0.23.0` content landed on `main` (2026-08-02) — `v0.23.0` had
never been tagged despite `pyproject.toml`/`server.py`/`CHANGELOG.md` all declaring it shipped, so
this release retroactively tags `v0.23.0` at that point and rolls everything since into `v0.24.0`.
Headline: call-graph resolver pipeline hardening, two new ADRs (0034 pyan GPL-2.0-or-later license
quarantine, 0035 C/C++ call-edge tier scope), ADR-0036 additive/narrowing `include_dirs` semantics,
ADR-0032 config-field liveness audit, and a full documentation/skill resync against `development`.

### Added

- **Heartbeat progress logging for long-running relationship extraction** (`utils/progress.py`,
  part of the call-graph resolver hardening pass below) — surfaces periodic progress on large
  projects where extraction previously ran silently for minutes at a time.
- **SSCG benchmark harness can measure the per-request ego-graph path for the first time** — new
  `--ego-per-request` flag sets `plan.ego_graph_enabled` on `SearchOrchestrator.run()`'s arguments
  dict, distinct from the pre-existing `--ego-graph on|off`, which only overrides the *config
  field* `ego_graph.enabled` (already `True` by default) and never reached this path. This is the
  only way to exercise `_intent_ego_thresholds` (QW5, `search/effective_config.py`), which fires
  when both `plan.ego_graph_enabled` and `plan.intent_decision` are set — a path production MCP
  callers exercise by default (`mcp_server/tool_registry.py`) but no benchmark capture had ever
  measured. Four-view 63q capture (ego-off/on × intent-off/on) isolates `D − C` (QW5 alone) as
  flat: MRR +0.0013, driven by one already-known boundary-riding query, recall@10 −0.0053 — fed
  ADR-0031's deletion of the two intent policy tables (see Changed, below). Pure harness/test
  addition, no production source touched; `canon_i1` remains the published canon. See
  `evaluation/EGO_PER_REQUEST_VIEW_20260805.md`.

### Fixed

- **Documentation/skill resync against `development`** — stale test counts (5,540 → 5,801
  collected unit cases) corrected across `README.md`, `docs/DOCUMENTATION_INDEX.md`,
  `docs/VERSION_HISTORY.md`, and `tests/TESTING_GUIDE.md`; benchmark figures in `README.md`,
  `docs/VERSION_HISTORY.md`, and `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md` re-pinned from the
  one-generation-stale `canon_h1` to the current `canon_l1` (ADR-0033); the `mcp-search-tool`
  skill's `references/tool-index.md` and `references/parameters.md` updated with ADR-0036's
  additive/narrowing `include_dirs` semantics (skill was last resynced before that ADR landed) and
  bumped to `version: 0.24.0`.
- **Windows short/long path mismatch resolved in 3 flaky tests** (`710a16e`) — tests comparing
  paths against a project root captured via different Windows path-normalization forms
  (`\\?\`-prefixed long paths vs. 8.3 short paths) intermittently failed depending on which form
  the OS returned first; both sides now normalize through the same resolver before comparison.
- **Call-graph resolver pipeline hardened** (`5af6589`, plus the three preceding fixes it
  consolidates) — pyan's `visit_Lambda` now self-heals the same way `analyze_comprehension`
  already did for a lambda nested inside another anonymous scope (`analyze_scopes()` doesn't
  number that case but `_next_anon_scope_name()` always does, so `ExecuteInInnerScope` previously
  raised and aborted the entire pyan pass for the project); `process_one` now isolates any
  remaining per-file pyan failure so one bad file no longer costs the whole tier; the LSP
  resolver's aggregate wall-clock budget is no longer a static 180s regardless of project size —
  `LSPResolver.resolve()` now derives `budget = min(cap, max(floor, 2.0 + seconds_per_chunk *
  n_probes))` from indexed chunk count, with `lsp_seconds_per_chunk`/`lsp_total_timeout_cap_seconds`
  as new `CallGraphConfig` fields (a 2,177-file/~32k-chunk project needed ~240s but was previously
  killed at the 180s floor); relationship extraction no longer runs all 16 extractors per chunk
  inside one try block — a single extractor raising (e.g. a positional-only-parameter `IndexError`)
  previously discarded every edge the other 15 extractors collected for that chunk, not just the
  raising extractor's own contribution, and per-extractor failures are now tallied and
  escalation-logged instead of silently dropped; `default_param_extractor.py`/`type_extractor.py`
  now index into `posonlyargs + args` combined (PEP 570's right-alignment for `ast.arguments.
  defaults`) instead of `args.args` alone, fixing an `IndexError` (or silent misattribution) on any
  positional-only parameter carrying a default, confirmed against real third-party signatures in
  torch's `custom_ops.py`.
- **`index_directory`'s `include_dirs`/`exclude_dirs` filtering corrected** (`c95730d`) — filters
  now apply correctly against both absolute and relative paths, wildcard patterns are supported,
  and `exclude_dirs` reliably beats `include_dirs` on a conflicting path; zero-match patterns now
  log a loud per-pattern warning instead of failing silently, and a new `--dry-run` mode previews
  the effective filter set before paying for a full index.
- **pyan3 license mislabeled `GPL-2.0-only` instead of `GPL-2.0-or-later`** (ADR-0034,
  `8345055`) — inverted the Apache-2.0 compatibility read for the optional `[callgraph]` extra;
  `pyproject.toml` corrected, and `external_call_graph.py` (which subclasses pyan in-process) now
  carries its own `GPL-2.0-or-later` header with a `NOTICE` file added, rather than inheriting the
  project's blanket Apache-2.0 license text. Also fixed along the way: `docs/CALL_GRAPH_TUNING.md`
  cited a nonexistent `ast_call_graph.py` module and a stale `min_confidence` default; `docs/adr/
  README.md` was missing the ADR-0033 row.
- **Config-field liveness audit closed** (ADR-0032, `75eb4ba`/`5c1fbc1`/`179b227`) — a two-question
  audit (search_config/example sync, and full 124-field liveness via the ADR-0020 three-method
  methodology) found zero dead fields but five defects, now fixed: `start_mcp_server.cmd`'s
  GPU-acceleration submenu text incorrectly implied `prefer_gpu` selects the device (it only gates
  dynamic embedding batch sizing — CUDA runs whenever available either way);
  `CallGraphConfig.resolvers` accepting `'lsp'` or other unrecognized values silently had no
  effect (Stage 3 is gated solely by `lsp_enabled`) and now warns; `reranker.batch_size`/
  `reranker.instruction` were untagged `construction_baked`, so `requires_rebuild()` silently
  ignored benchmark-arm overrides on them; two stale doc claims fixed
  (`docs/MCP_TOOLS_REFERENCE.md`'s `configure_chunking` defaults, `docs/
  HYBRID_SEARCH_CONFIGURATION_GUIDE.md`'s now-false `multi_hop.expansion` divergence claim).
- **Six BM25/worker config fields could be silently ignored by a benchmark arm** (ADR-0030) —
  `bm25_k1`, `bm25_b`, `bm25_use_stopwords`, `bm25_use_stemming`, `bm25_tokenizer`, and
  `max_parallel_workers` are read once into `HybridSearcher`/`BM25Index` at construction, but
  were untagged in `spec()`, so `evaluation/arm_overrides.py::requires_rebuild()` returned
  `False` for them — an arm overriding e.g. `search_mode.bm25_k1` would mutate the live config
  in place, the cached `HybridSearcher` would be reused, and the arm would measure the
  pre-override value instead of its own. All six now carry `construction_baked=True`, forcing a
  rebuild; a corrected code comment states the true liveness (inert until index reload or
  searcher rebuild, not query-time). No published benchmark result used any of these six as an
  A/B'd knob, so the hazard was latent, not realized.
- **`find_similar` redirects no longer anchor on a trailing prose word** (ADR-0029) —
  `_extract_symbol_from_query`'s fallback scanned `reversed(query.split())` and accepted any
  non-blocklisted lowercase word as the redirect's target symbol, so queries like "find code
  similar to `InheritanceExtractor._extract_from_tree` hook" redirected on `'hook'` instead of the
  actual symbol (also: dotted names truncated at the dot, leading-underscore privates and
  UPPER_CONST constants matched nothing). Rewritten to reuse `_detect_code_symbols`'s
  dot-preserving tokenizer and predicate-precedence ranking (promoted to a shared
  `search/tokenization.py` helper), returning `None` — no redirect, normal ranked search — when no
  token qualifies. Nine golden-query regression tests pin the exact anchor each must extract.
- **`search_code` no longer returns an empty result set for path-shaped queries** (ADR-0028) —
  the `find_path` redirect's extractor (`_extract_path_endpoints`) regex-matched ordinary prose
  (e.g. "strip line range **from** chunk_id **to get** stable normalized identifier" parsed as a
  `source`/`target` path query), and the redirect carried `fallback_on_error=False`, so a misfire
  returned nothing instead of falling back to ranked search. ADR-0026 found no query in either
  golden dataset ever benefited from this branch, so it is removed outright — construction branch,
  execution arm, extractor, and its dedicated tests — rather than left disabled behind a flag.
  `QueryIntent.PATH_TRACING` itself is unaffected; it still selects a QW5 ego threshold and an A1
  edge-weight profile.
- **`find_connections` no longer silently drops non-primary relationship edges** (ADR-0027) — a
  `(u, v)` node pair can carry more than one relationship type (e.g. `implements` + `uses_constant`,
  which collide whenever a base class is ALL_CAPS such as `abc.ABC`), but both graph traversals
  called `get_edge_data` with no type filter and kept only the single primary edge it selects. The
  loss was not confined to filtered calls — `analyze_impact` never passes `relation_types`, so every
  unfiltered `find_connections` call lost non-primary types during bucketing.
  `RelationshipEntry` now carries every parallel edge (via the previously-orphaned
  `get_all_edge_data`), and the analyzer fans out over all of them before bucketing.
  `direct_callers`/`direct_callees`/`total_impacted`/`dependency_graph` are provably unchanged on the
  unfiltered path (a `calls` edge always wins the primary selection when one exists); only the
  `relationships` buckets gain the previously-dropped rows.

### Changed

- **`index_directory`'s `include_dirs` is additive for dependency-tree paths, narrowing for
  everything else** (ADR-0036, `aa65a92`) — `include_exclusive` threaded through `PathFilter`,
  `get_effective_filters` (2-tuple → 3-tuple), `MerkleDAG`, the incremental indexer, and the
  index/search MCP handlers: naming a dependency-tree path (`venv`, `site-packages`,
  `node_modules`, `.tox`, … — `DEPENDENCY_TREE_DIRS` in `chunking/language_registry.py`, 13
  entries) now re-admits that path *on top of* normal project scope instead of narrowing the whole
  project down to just it; any other include path still narrows as before. The H033 golden-dataset
  gold is retargeted to the split_block-collapsed `method:` kind, causally coupled to this change
  (`get_project_storage_dir` only crosses the character-based split threshold once this diff's
  params land) and must ship together with it.
- **C/C++ call-edge resolver tier scope formalized, no code change** (ADR-0035) — documents the
  intended coverage boundary for the C/C++ resolver tier in the layered call-graph pipeline.
- **ML stack bumped (retrieval libs + torch 2.11.0); SSCG canon re-pinned to `canon_l1`**
  (ADR-0033) — three independently-gated stages: transformers 5.13.0→5.14.1,
  sentence-transformers 5.6.1→5.7.0, faiss-cpu 1.14.3→1.15.0, huggingface-hub 1.22.0→1.26.1,
  hf-xet 1.5.1→1.6.0 (stage 1, byte-identical retrieval outcome, 0 queries moved), then torch
  2.8.0+cu128→2.10.0+cu128 (stage 2, all five paired 95% CIs include zero — gate passes), then
  torch 2.10.0+cu128→2.11.0+cu128 (stage 3, correcting a factual error discovered in stage 2's own
  CVE claims — see Security below; also byte-identical retrieval outcome, 0 queries moved). The
  `torch<2.9.0` ceiling's stated rationale (ModernBERT `torch.compile` inductor conflict) was
  verified dead: the embedder it protected was deleted in `24f6b8c` and `transformers>=5.3.0`
  removed ModernBERT's `reference_compile` path entirely. New ceiling `<2.12.0` reflects the
  pinned `cu128` wheel index's current publish maximum, not a known regression. Re-pin: intent-on
  arm mrr 0.8603 (63q, unchanged) / 0.6789 (133q), F-via-similar mrr 0.9021, superseding
  `canon_j1`'s figures (0.8603/0.6869/0.8836) — deltas attributed to torch's kernel-level
  floating-point reordering, not a functional change. See `docs/adr/0033-lift-torch-ceiling.md`.
- **Deleted the two intent policy tables (QW5 + A1); SSCG canon re-pinned to `canon_j1`**
  (ADR-0031) — `_intent_ego_thresholds` (`search/effective_config.py`) and
  `INTENT_EDGE_WEIGHT_PROFILES` (`graph/graph_storage.py`) were measured inert by ADR-0026 and
  isolated as flat on the per-request ego-graph path by a prior harness round
  (`evaluation/EGO_PER_REQUEST_VIEW_20260805.md`); both are now deleted. Every intent-on request
  (the shipped default) carrying only `intent_decision` — no ego, no parent — now gets its
  `SearchConfig` back from `build_effective_config` by identity instead of a `copy.deepcopy`.
  A pre-registered difference-of-differences gate (revert threshold: either metric < −0.02 on
  either dataset) passed cleanly on both MRR and recall@10, both datasets (all four deltas within
  ±0.004 of zero); a follow-up capture with `--ego-per-request` confirmed 0 per-query diffs against
  the plain arm across all 63 queries, proving nothing but QW5 rode that flag. Re-pin: intent-on
  arm mrr 0.8603 (63q) / 0.6869 (133q), superseding `canon_i1`'s figures (0.8524/0.6879). See
  `docs/adr/0031-delete-intent-policy-tables.md`.
- **Config→searcher seam deepened; SSCG canon re-pinned to `canon_i1`** (ADR-0030) — unified two
  architectural-review candidates: `SearchOrchestrator._search`'s five raw
  `isinstance(searcher, HybridSearcher)` checks now route through the previously-uncalled
  `SearcherView.is_hybrid`; its per-request config assembly is extracted into
  `build_effective_config()` (new module `search/effective_config.py`); and
  `HybridSearcher`/`IndexSynchronizer` construction now preserves the whole `SearchConfig` object
  instead of unpacking seven fields into primitives that ten dead `self.` copies never read.
  Pure refactor, 0 behaviour change. Re-pin: intent-on arm mrr 0.8524 (63q) / 0.6879 (133q),
  superseding `canon_h1`'s figures (0.8418/0.6750) — 0 flips measured, deltas attributed to
  substrate drift from six intervening commits, not the refactor. See
  `evaluation/CANON_20260805_CONFIG_SEAM_REPIN.md`.
- **Intent classification defaults back on; `find_similar` re-gated live; SSCG canon re-pinned to
  `canon_h1`** (ADR-0029) — after the extractor repair (see Fixed, above), a pre-registered gate on
  the 9 similarity-category golden queries required the intent-on arm's MRR to exceed the
  normal-path mean and its recall@20 to not fall below the `find_similar` correct-anchor ceiling,
  on both the 63q and 133q datasets. Both passed (MRR 0.4594 → 0.5593, recall@20 0.7185 ceiling vs.
  0.7418 arm), so `IntentConfig.enabled`'s default flips back `False` → `True`
  (`search/config.py`, `search_config.json.example`). Re-pin: intent-on arm mrr 0.8418 (63q) /
  0.6750 (133q), superseding `canon_g1`'s intent-off figures as the published baseline (kept
  alongside as the intent-off reference). See `evaluation/CANON_20260804_INTENT_ON_REPAIRED.md`.
- **Intent classification defaults off; SSCG canon re-pinned to `canon_g1`** (ADR-0028) — following
  ADR-0026's measurement that the intent layer's non-redirect machinery is inert (+0.0005 MRR,
  bit-identical pools) and one of its two redirects is a pure regression (see Fixed, above),
  `IntentConfig.enabled`'s default flips `True` → `False` (`search/config.py`). The `find_similar`
  redirect is untouched but stays gated off pending a repair-and-gate round. Re-pin: mrr 0.8352
  (63q) / 0.6667 (133q) / F-view whole-aggregate 0.8915, F-only mean 0.8519 — bit-identical to
  `canon_f1`'s F-only figure, confirming the ~0.01 MRR shift on the other two views is substrate
  drift from the `find_path` deletion, not the default flip (the benchmark harness already
  re-asserted `intent.enabled=False` per query on every non-arm capture, so `canon_f1` was already
  measuring this condition). See `evaluation/CANON_20260804_INTENT_OFF.md` for full numbers.
- **MCP config-field liveness closed for `search_mode`/`performance` fields, project-activation
  pairing unified, a dead config-locator wrapper removed.** `SearchModeConfig.bm25_weight`/
  `.dense_weight` and `PerformanceConfig.use_parallel_search` are MCP-settable but carried no `mcp=`
  tag; both field maps now derive from the same `mcp=` declaration ADR-0022 established, plus a new
  ratchet test asserting no MCP-settable field is ever `construction_baked`. The existing
  `_bind_active_project_overrides` helper — previously inlined at two handler call sites instead of
  called — is now shared and non-swallowing there, so a bind failure surfaces via `@error_handler`
  instead of silently leaving the previous project's `search_overrides.json` active.
  `get_config_via_service_locator` (11 call sites, all invoked with no arguments, its `key`/`default`
  lookup dead) is deleted in favor of a direct `get_search_config()` import.
- **SSCG benchmark harness measures the intent layer's redirect behavior** — `run_single`'s
  unconditional per-query intent-off re-pin now stands down when an arm's own overrides set
  `intent.enabled`, and `find_path`/`find_similar` redirects are scored as a distinct outcome
  (`mrr_excl_redirect`, `redirect_rate`, `redirect_ids`, per-query `redirect_kind`) rather than
  silently as a zero or an already-fair fallback. Discharges ADR-0023's `canon_B1b` gate.
- **SSCG canon re-pinned to `canon_f1`** (ADR-0026) — the four fixes/refactors above edit indexed
  source, so the canon is re-measured: mrr 0.8458 (63q, up from `canon_e1`'s 0.8362) / 0.6692 (133q).
  The `canon_B1b` intent-on arm is captured for the first time and matches its pre-registered
  falsifiability table exactly, but reveals the intent layer's entire measurable effect is two
  redirect branches: `find_path` is a pure regression (both instances are prose misfires returning
  empty results), while `find_similar` is a real, sabotaged capability (mean mrr 0.4577 normal →
  0.2315 buggy redirect → 0.8519 correct anchor) with no config-only fix. Disposition: flip
  `intent.enabled` off by default and remove `find_path` as a stopgap, then repair the symbol
  extractor and re-measure `find_similar` against a pre-registered gate before deciding to keep or
  remove it. See `evaluation/CANON_20260804_B1B.md` for full numbers.
- **SSCG benchmark harness routes through `SearchOrchestrator.run()`** (ADR-0023) —
  `run_sscg_benchmark.py` previously called `HybridSearcher.search()` directly, one layer
  below the path the MCP `search_code` tool actually serves, forcing two hand-written replays
  of production logic (`_apply_centrality_stage`, ADR-0019's intent-weight replay). The harness
  now calls the real `SearchOrchestrator.run()` (intent classification pinned off for this arm;
  a later arm measures it on), with `max_context_tokens: 0` to bypass Block H's presentation-
  layer truncation so MRR keeps meaning "over a ranked list of k". `--with-centrality` /
  `--centrality-alpha` CLI flags are removed — centrality scoring is now unconditional and
  config-driven like every other knob, matching what every published canon already measured.
  New `canon_B1`: MRR 0.8249 (63q), a small delta from the pre-change canon (0.7942) — see the
  ADR for the full breakdown and two surfaced-but-unrelated bugs (a non-atomic `clear_index()`
  and a legacy-Windows console crash in `rich`'s progress bar) found while verifying this change.
- **Duplicated `HybridSearcher` construction extracted; two per-project config bugs fixed** —
  `get_searcher` and `_check_auto_reindex` each hand-built an identical searcher with 11-12
  kwargs; both now call a shared `build_hybrid_searcher` helper (pure refactor, the four
  deliberate divergences between the two call sites are preserved). Two real bugs found along
  the way: server startup never bound the config layer to the active project, so a project's
  `search_overrides.json` (ADR-0014) was silently not merged after every restart until an
  explicit `switch_project`/`index_directory` call — fixed in `initialize_server_state`. That fix
  would have turned a second, pre-existing bug from occasional into permanent: `save_config`
  wrote its result back to the *global* config file unfiltered, promoting any active project's
  overrides into global config — fixed by subtracting the overrides-layer keys before writing.
  Also: the two false `construction_baked=True` flags on `bm25_weight`/`dense_weight` (they
  resolve live per `search()` call, not at construction) are corrected, eliminating a needless
  searcher reset + reranker-model reload on every weight-arm benchmark run; the orphaned
  `_switch_active_model` helper (dead since `4ec7627` removed its only caller) is deleted; and
  the three `SearchConfig`-mutating benchmark probe scripts move onto the `arm_overrides` seam.
- **SSCG canon re-pinned to `canon_C3`** (ADR-0024) — the searcher-construction dedup and
  config-metadata fixes above edit indexed source, so the canon is re-measured:
  MRR 0.8348 (63q, up from `canon_B1`'s 0.8249) / 0.6816 (131q expanded). Also corrects a
  standing mislabel: the previously-published `0.8502` F-via-similar figure was the
  whole-63-query aggregate, not a 9-query F-category mean — the true F-only mean is **0.8519**.
  Five user-facing docs (`CLAUDE.md`, `README.md`, `docs/BENCHMARKS.md`,
  `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`, `docs/VERSION_HISTORY.md`) still cited the
  pre-`canon_B1` figure (`0.7987`) — none had been updated when `canon_B1` landed — and are
  updated directly to `canon_C3`. See `evaluation/CANON_20260803.md` for full numbers.
- **SSCG canon re-pinned to `canon_d1`/`canon_d2`** — 34 commits landed on top of `canon_C3`
  (ADR-0025 index-clearing rework, two new relationship extractors in `e99ecef`, `ImpactReport`
  consolidation), none of which changed retrieval mechanics but all of which touch indexed
  corpus and/or graph edges feeding multi-hop expansion. `canon_d1` (code drift only, captured
  pre-dataset-edit): MRR 0.8339 (63q, down 0.0009 from `canon_C3`, inside the ±0.02 noise band) /
  0.6654 (131q, down 0.0162, describing the same 145-query dataset `canon_C3` measured) / 0.8915
  whole-aggregate F-view (F-only mean 0.8519, unchanged). Also re-graded four previously-excluded
  commit-mined candidates (H035/H060/H061/H068) under the ADR-0021 determinism pin, since the
  bf16-non-determinism rationale their exclusion cited was disproven by that ADR: H035 promoted
  as a genuine, reproducible hard case (stable `POOL_MISS`) and H068 promoted with a corrected
  gold (its originally-mined gold predated the batched method the query actually describes);
  H060/H061 stay excluded on query-quality/gold-defensibility grounds, unrelated to determinism.
  `canon_d2` (dataset change only, 145→147 queries / 131→133 non-D post top-up): MRR 0.6591 — a further
  −0.0063 from promoting two queries that were excluded specifically for being hard, not a
  retrieval regression (0 flips, same code/index as `canon_d1`). Also fixes a mislabeled
  `file_recall@5` in the F-category-only benchmark row (it was the whole-aggregate figure) and
  corrects a split-count citation (train/val/test figures previously cited full-file counts
  including the out-of-scope category D; the actually-scored counts are smaller). Five
  user-facing docs updated to the new figures. See `evaluation/CANON_20260804.md` for full
  numbers, the per-category/per-split breakdown, and the frontier disposition
  (`evaluation/CATEGORY_G_DESCOPE_20260804.md` for the Category G descope).

### Security

- **`gitpython` bumped 3.1.57 → 3.1.58** (`bef99e6`, routine dependabot patch release, no CVE
  tracked against 3.1.57 at time of bump).
- **torch 2.8.0+cu128 → 2.11.0+cu128 closes 7 of 8 tracked CVEs** (ADR-0033), including both
  CVSS 8.8 vulnerabilities: `CVE-2026-24747` (a `weights_only` unpickler bypass) and
  `CVE-2025-3001` (a `torch.lstm_cell` memory-corruption bug — not a second `weights_only`
  bypass, correcting an earlier mischaracterization in this project's own tracking notes), plus
  `CVE-2026-4538` (`PYSEC-2026-139`, a `pt2` loader deserialization issue). Remaining 1:
  `CVE-2025-3000` (fixed in 2.13.0, which the pinned `cu128` wheel index does not yet publish).
  See `pyproject.toml`'s "Deferred (no upstream fix)" tracking comment and
  `docs/adr/0033-lift-torch-ceiling.md`.
- **Correction**: an intermediate pass of this same audit (torch 2.10.0) claimed
  `CVE-2026-4538` had "no upstream fix at any version" and closed the ledger at 6 of 8. That was
  wrong — `pip-audit`'s default OSV lookup silently drops findings for local-version wheels like
  `torch==2.10.0+cu128` (no `skip_reason`, the entry is just absent from the report). Querying the
  OSV API directly (`https://api.osv.dev/v1/vulns/PYSEC-2026-139`) shows `last_affected: "2.10.0"`
  with a merged fix PR (`pytorch/pytorch#176791`) — `2.10.0` was still vulnerable, `2.11.0` closes
  it. New standing rule: always cross-check torch CVE claims against the raw OSV API, not just
  `pip-audit`'s report, when the installed wheel carries a local version suffix.

---

## [0.23.0] - 2026-08-02

86 commits since `v0.22.0`. The headline is three subsystem removals (community, DSPy, ONNX)
plus an MCP SDK major-version migration; see `### Removed` for the breaking changes.

### Migration

- **MCP SDK bumped to v2** (`mcp>=2,<3`, ADR-0017) — `mcp_server/server.py`'s six JSON-RPC
  handlers moved from post-construction `@server.*()` decorators to v2's constructor-kwarg
  `on_*` pattern. Wire format is unchanged (verified end-to-end over HTTP transport and a live
  MCP client); no client-side action needed unless you vendor `mcp_server/server.py` directly.
- **Reindex recommended, not required.** `INDEX_VERSION` stays at 4 — no forced rebuild — but
  the community-subsystem removal (below) dropped `community` from the score-demotion tables
  while any stale `__community__/*` chunks from a pre-0.23.0 index persist on disk and now
  compete at full score instead of being demoted. A full reindex clears them; leaving an old
  index in place is safe, just not optimal.
- Before upgrading a deployed `search_config.json`, check `embedding.model_name` and
  `reranker.model_name` — three models were removed from the registries this release (see
  `### Removed`); a deployed config pinned to one of them will fail to load until repointed.

### Added

- **Per-project config overrides + auto-tune probe** (ADR-0014) — a `search_overrides.json`
  layer sits between the shipped defaults and a project's live config.
- **`exclude_same_file` on `find_similar_code`** (`d468dcb`) — caller-controlled cross-file-only
  filtering; default is byte-identical to prior behavior.
- **Listwise reranker document-budget config** (ADR-0011) — `listwise_doc_max_chars`, decoupled
  from the pointwise reranker's `doc_max_chars`.
- **Curated query-expansion feature**, shipped **disabled** (ADR-0012) — complete but opt-in;
  re-evaluated and closed in ADR-0012's follow-up with the flag left off (pool-flooding
  interaction with the listwise reranker, not a vocabulary gap).
- **Four new evaluation metrics** (`21a438c`) — `recall@20`, `recall@50`, `pool_hit_rate`,
  `file_acc@k`/`file_recall@k` for multi-file-localization queries.
- **`mcp_eval` CI regression gate** (`d20e0de`) — golden-set drift guard runs in CI.
- **Golden dataset expanded 108 → 145 queries** (`988f1f9`) — 37 commit-mined bug-fix-
  localization queries promoted after a 2-round grading pass.
- **Commit-mined query-candidate harness** (`scripts/benchmark/grade_candidate_queries.py`,
  `merge_h_queries.py`) — mines historical bug-fix commits into candidate golden queries.
- **Stable-miss funnel probe** (`c5467e3`, `scripts/benchmark/probe_stable_misses.py`) —
  diagnostic tooling for queries that miss consistently across repeated runs.
- **Config field liveness audit** (ADR-0020) — 7 previously-hardcoded fields wired to real
  config control: `embedding.query_cache_size`, `search_mode.min_bm25_score`,
  `performance.max_parallel_workers`, `intent.default_intent`, `ego_graph.deduplicate`,
  `parent_retrieval.include_parent_content`, `observability.capture_query_text`. Every wired
  default equals the prior hardcoded value, so this is byte-identical behavior on a default
  config.

### Changed

- **`RetrievalRequest` carries effective config** (ADR-0018) — search-time config resolution
  moved onto the request object instead of being re-derived mid-pipeline.
- **Base install trimmed** — fewer transitive packages after the DSPy and ONNX removals below.
- `tmp/` and `temp/` directories added to default index excludes (`838c24d`) — these were
  previously indexed as ordinary source, polluting search results with scratch files.
- **`CallGraphConfig` defaults flipped** (`70c8904`): `lsp_enabled` `False` → `True` (LSP is now
  requested by default; it still no-ops unless the `[lsp]` extra is installed), and
  `min_confidence` `0.0` → `0.65` (drops pyan-wildcard-tagged 0.60 edges from injection by
  default). Prior docs describing LSP as "opt-in, default off" predate this flip.

### Fixed

- **HTTP transport now fails fast on port conflicts** (`7606b40`) instead of hanging.
- **Two clear/force-reindex bugs** (`db4c181`): `CodeGraphStorage.clear()` wasn't deleting its
  backing JSON, and the ego-graph retriever was silently returning zero neighbors after every
  in-process full reindex.
- **Hop-1 candidate reservation** (ADR-0013, default 6 slots) — multi-hop expansion no longer
  displaces strong hop-1 candidates via score-scale incomparability at the rerank-window cut.
- **19 stale golden-dataset entries repaired** (`6df36db`) after a `dedup_key` normalization
  gap let 3-part `split_block` golds drift from their parent chunk.
- **Ego-graph config reset bug** (ADR-0020, `search/ego_graph_retriever.py`) — found and fixed
  alongside the config-field audit.

### Removed

- **Community-detection/summarization/remerge subsystem** (ADR-0015) — deleted
  `graph/community_detector.py`, `graph/community_summarizer.py`, `search/community_stage.py`,
  and `search/community_refresh_stage.py`; removed community-map persistence from
  `graph/graph_storage.py`, the cross-community ego-graph penalty, `subgraph_communities`
  annotation, the orphaned `_greedy_merge_small_chunks` primitive, and all `community`/
  `enable_community_*` fields from chunking and index-probe auto-tune config. Module-summary
  and synthetic-chunk demotion machinery (~194 `module` chunks) and the ablation harness/metrics
  used to gate ADR-0015 are unaffected and remain in place. `chunk_type="community"` no longer
  exists; existing indices carrying legacy `*_communities.json` files are unaffected on load and
  are purged on next full reindex. This removal is scoped to the retrieval pipeline —
  `evaluation/metrics.py` and `scripts/benchmark/run_sscg_benchmark.py` retain
  community-membership helpers used only for benchmark ablation, not for live search.
- **DSPy evaluation subsystem** (ADR-0016) — 13 files, 4,849 lines, superseded by
  `run_mcp_pipeline_eval.py`; zero production consumers at time of removal.
- **ONNX inference path** (`72b6881`).
- **Three models removed from the registries** (`24f6b8c`, **breaking** for any deployed config
  pinned to one of these): `nomic-ai/CodeRankEmbed` and `Alibaba-NLP/gte-modernbert-base` from
  `MODEL_REGISTRY`, and `Qwen/Qwen3-Reranker-4B` from `GENERATIVE_RERANKERS`.
  `MODEL_REGISTRY` now has 4 entries: `google/embeddinggemma-300m`, `BAAI/bge-m3`,
  `Qwen/Qwen3-Embedding-0.6B`, `codefuse-ai/F2LLM-v2-0.6B`.
- **`[eval]` and `[profile]` optional-dependency extras** — no longer needed after the DSPy
  removal.
- **6 dead config fields deleted** (ADR-0020), each confirmed orphaned by three independent
  methods (semantic search, call-graph zero-caller lookup, exhaustive grep):
  `chunking.min_chunk_tokens`, `chunking.max_merged_tokens`, `chunking.token_estimation`,
  `chunking.size_method`, `search_mode.enable_result_reranking`,
  `parent_retrieval.max_parents_per_result`. Their driver — the greedy-merge chunk pass — had
  already been removed from `chunking/languages/base.py` in a prior refactor; this audit deleted
  the ~94 lines of now-orphaned code the fields still configured, plus two test files that only
  exercised it (`tests/unit/chunking/test_greedy_merge.py`,
  `tests/unit/chunking/test_token_estimation.py`).

### Security

- 8 previously-deferred `torch` CVEs addressed (`4332736`); `nltk` bumped to 3.10.0, `uv` to
  0.12.0; a 24-package safe-update wave across the rest of the dependency tree.

### Performance

- Full index builds ~7-9s (11-14%) faster from the community-subsystem removal (fewer stages in
  the write path).

---

## [0.22.0] - 2026-07-27

### Migration

- **Existing indices need one full, non-incremental reindex.** Three changes in this release each
  bump the on-disk BM25/GLSL data format, and all three fail *silently*: an `INDEX_VERSION`
  mismatch (now **4**, up from 2) and a BM25 tokenizer mismatch each only emit a `logger.warning`
  on load — there is no automatic rebuild, no error, and the warning never reaches the MCP
  response. The only auto-heal path (`IndexSynchronizer.resync_if_desynced`) triggers solely on a
  >10% BM25-vs-dense *document-count* difference, which a version bump never produces. Left
  un-migrated, you get a working but silently degraded index: divergent index/query tokenization,
  missing BM25 path/symbol augmentation, and GLSL files still parsed by the old fictional-node
  chunker. One force-full reindex (`index_directory(..., incremental=False)`) resolves all three
  at once. Measured cost of skipping it: −0.05 to −0.11 Recall@5 and −0.09 to −0.11 MRR across the
  two migrations that have dedicated A/B evidence (`evaluation/BM25_PATH_AUG_TRACK_D_20260726.md`,
  BM25 tokenizer A/B).

### Added

- **GLSL indexing parity with Python** — corrected 18 fictional tree-sitter node types across
  GLSL/JS/TS/TSX/Go (`chunking/language_registry.py`) that made ~60% of
  `GLSLChunker.extract_metadata` dead code, and rewrote `GLSLChunker`
  (`chunking/languages/glsl.py`) around the real grammar shape: named uniforms/UBO blocks/structs/
  macros/includes, leading- and trailing-comment docstring attachment, a chunk-granularity gate
  (uncommented one-liners merge into `module_preamble` instead of exploding into near-empty
  chunks), and length-preserving parse-error neutralization for anonymous layout qualifiers.
  Adds a GLSL call-graph walk (`call_expression` → `metadata["calls"]`) with GLSL-builtin and
  TouchDesigner `TD*`-prefix filtering (`glsl_filter_td_prefix`, default on), GLSL relationship
  edges (`imports`/`uses_type`/`instantiates`/`defines_field`/`defines_constant`), a `"shader"`
  file role (ranking-neutral), a `"struct"` entity type boost, `.glslinc` as the 8th GLSL
  extension (20 extensions total), and a base-class fix that had left `complexity_score` at 0 for
  every tree-sitter language overriding `get_node_complexity` (GLSL/C/C++/C#/Go/Rust). One real
  file measured: 4 chunks (2 unnamed blobs, 0 docstrings, 0 call edges, complexity 0) → 13 chunks
  (11 named, 9 with docstrings, 1 resolved call edge, non-zero complexity).
- **Persistent chunk embedding cache** (`embeddings/chunk_cache.py`) — content-hash-keyed cache of
  chunk embedding vectors persisted to `chunk_embeddings.bin`, cutting a full reindex's embedding
  phase from 33.94s to 0.75s (43×) once the codebase is unchanged. On by default
  (`enable_chunk_cache`, `search/config.py`).
- **Widened retrieval funnel** — hybrid `search_k` raised from `k*2` to
  `max(reranker_budget, k*5)`, and the fused pool is held at the reranker's `top_k_candidates`
  before neural rerank, truncated to `k` after. The graph-enhanced cap changed from a hardcoded
  `k*4` to a configurable `graph_enhanced.max_results_multiplier` (default 8). Adds
  `recall@20`/`recall@50`/`pool_hit_rate`/`pool_size` benchmark metrics — the single largest
  recall improvement in this release.
- **Identifier-preserving BM25 tokenizer** (`bm25_tokenizer` config: `legacy`/`whole`/`additive`,
  default now `whole`) — keeps identifiers intact instead of stemming them apart.
- **BM25 path/symbol token augmentation** — BM25 documents are now augmented with path and symbol
  tokens at build time. **Adopted** after A/B verification (`evaluation/BM25_PATH_AUG_TRACK_D_20260726.md`):
  63-query set MRR 0.3207 → 0.4337 (+0.113), Recall@5 0.3180 → 0.3992 (+0.081), 13 queries
  improved vs. 1 regressed. Drives the `INDEX_VERSION` 3 → 4 bump.
- Real Okapi `bm25_k1`/`bm25_b` scoring parameters are now wired and query-time tunable (no
  reindex required); a k1×b sweep confirmed the shipped defaults (1.5/0.75) are not beaten
  decisively by any tested cell (`evaluation/BM25_K1B_SWEEP_20260726.md`).
- `bm25_reserved_slots` — an RRF pool-reserve knob for BM25-only recall, default 0
  (byte-identical behavior at default; retained for experimentation).
- **Opt-in single-pass rerank mode** (`RerankerConfig.single_pass`, env
  `CLAUDE_RERANKER_SINGLE_PASS`, default off) — roughly halves reranking latency at a measured
  recall cost, so it ships as a documented latency knob rather than a new default.
- **`codefuse-ai/F2LLM-v2-0.6B` embedding model registered** and available via the launcher's
  Quick Model Switch (option 6). A/B evidence (`evaluation/EMBEDDER_F2LLM_AB_20260726.md`): MRR
  +0.026/+0.027 mean over `Qwen3-Embedding-0.6B` across both golden sets, recall flat, latency and
  VRAM footprint unchanged. **This is a new available model, not a changed default** — the
  packaged default embedder remains `BAAI/bge-m3`.
- `index_directory`'s response now includes a `call_edges_injected` count.
- Search-latency and full-index phase profilers (`scripts/benchmark/profiling/`) for measuring
  per-phase wall-clock cost of a search or reindex run.
- 96-query expanded golden evaluation set (63 original + 33 hard queries) with a grading harness,
  for benchmark runs that need more coverage than the original SSCG set.

### Changed

- Reranker pool budget (`top_k_candidates`) reduced from 50 to 30 — quality-neutral within ±0.025
  on both golden sets, −32% reranking latency. `configure_reranking`'s documented default updated
  to match.
- `search_code` results now **collapse `split_block` fragments by default**
  (`RerankerConfig.dedupe_split_blocks = True`) — a query that previously returned multiple
  fragments of one oversized chunk now returns one. Manual split_block dedupe on the client side
  is no longer necessary.
- `graph_enhanced.centrality_alpha` default lowered from 0.3 to 0.0 — centrality now only
  reorders results via `CentralityRanker.rerank()` rather than blending into the ranking score
  directly; the benchmark runner gained `--with-centrality`/`--centrality-alpha` flags to make
  this tunable and measurable.
- `call_graph.lsp_total_timeout_seconds` default raised from 120 to 180.
- `auto_reindex` now honors `config.performance.enable_auto_reindex` instead of being silently
  ignored; drift detection now counts distinct changed *files* rather than change *events* (a
  2-file change could previously promote to a full rebuild while a 348-file change stayed
  incremental).
- `index_directory` now returns the *effective* `include_dirs`/`exclude_dirs` actually applied,
  and hard-fails on a full reindex that adds 0 chunks instead of silently reporting success.
- **Chunk embedding cache now records provenance** — the cache header stores a
  `device|dtype|backend` string (`ModelLoader.describe_numerics()`, computed without loading the
  model) alongside the existing model/dimension check, so flipping `enable_fp16`, `prefer_bf16`, or
  `use_onnx` now correctly invalidates cached vectors instead of silently reusing ones computed
  under different numerics. Cache format bumped to version 2; existing v1 cache files cold-start
  once on upgrade (one full re-embed, then cached as normal).
- **Auto size cap retuned** from `max(4× live entries, 20,000)` to `max(2× live entries, 2,000)`
  (clamped to a 32MB byte ceiling) — cuts the eviction ceiling from ~82MB to ~17.5MB for a typical
  project without discarding any currently-live entries.
- Chunk cache hit rate is now logged (`[CHUNK_CACHE] ... hits=N misses=N hit_rate=X% size=N cap=N`)
  on both the all-cached-hit and normal save paths; previously silent even on a 0% hit-rate
  regression.
- **`mcp-search-tool` skill reinstated** — the skill removed in v0.21.0 (superseded by
  `auto-git-workflow` for git operations) has been restored and substantially expanded for MCP
  search-tool guidance (`SKILL.md` plus `references/advanced-features.md`, `performance.md`,
  `parameters.md`, `search-patterns.md`, `tool-index.md`), documenting the widened retrieval
  funnel, core/advanced tool tiers, and the 2026-07-25/26 benchmark results.

### Fixed

- **Every full reindex discarded 100% of resolver-derived call edges** — `HybridSearcher.clear_index()`'s
  graph re-sync was guarded by `if ... and self.dense_index._graph:`, but `GraphIntegration`
  defines `__len__` without `__bool__`, so a freshly-created 0-node graph was falsy and the
  re-sync silently never ran. Verified impact before the fix: 4,720 nodes / 14,118 edges saved
  with **0** pyan/libcst/LSP resolver-sourced edges. This is the highest-severity fix in this
  release.
- `handle_clear_index` deleted a filename that never existed (`chunks_metadata.db` instead of the
  real `metadata.db`), silently leaving the metadata DB, its `-wal`/`-shm` sidecars (routinely
  full-size, not crash-only debris), `chunk_ids.pkl`, and the call graph behind after a "clear
  index." Consolidated the three divergent index-deletion lists (`index_handlers.py` ×2,
  `search/indexer.py::clear_index`) onto one corrected file set, including cleanup of the legacy
  `metadata_symbol_cache.json` orphan. An explicit clear-index now also drops the chunk embedding
  cache itself — the escape hatch for suspect vectors — while the internal pre-reindex clear path
  correctly preserves it.
- `CodeGraphStorage.clear()` left an orphaned `communities.json` behind, read back live by
  `CommunityRefreshStage`/`SubgraphExtractor`/`EgoGraphRetriever` — the same phantom-artifact
  class as the fix above, applied to a file that fix missed.
- **Non-semantic chunks lost relationship edges on the live indexing path** —
  `GraphIntegration._make_spec_from_embedding` (`search/graph_integration.py`) dropped every
  chunk outside `SEMANTIC_TYPES` unconditionally, while its `add_chunk` twin lets non-semantic
  chunks through when they carry relationship edges. Since `populate_from_embeddings` (the path
  `HybridSearcher.add_embeddings` actually uses) builds specs via the former, GLSL
  `include`/`macro`/`declaration` chunks silently lost their `imports`/`defines_constant` edges.
  The spec builder now mirrors `add_chunk`'s escape hatch; covered by a unit test and a
  persisted-roundtrip integration test (`tests/fast_integration/test_glsl_call_graph_resolution.py`).
- A caught `PermissionError` during a force-full pre-clear previously reported success with 0
  chunks (a half-purged, unusable index); force-reindex now hard-fails instead.
  `get_canonical_project_info` previously picked the alphabetically-first per-model
  `project_info.json`, silently dropping stored `user_excluded_dirs` (9,211 chunks / 603 files
  indexed instead of the intended ~2,182 / 200).
- Drift-based reindex promotion counted change *events* rather than distinct changed *files* (a
  2-file change could promote to a full rebuild while a 348-file change stayed incremental), and
  a drift-promoted reindex reported the full-rebuild file count instead of the actual change set.
  Repairing this uncovered the rotted `slow_integration` suite (14 failed / 92 passed / 3 errors)
  and that `clear_index()` nulled `BatchOperations._metadata_store` without re-wiring it, crashing
  every post-full-index `remove_files()`.
- **Centrality memo never actually hit** — moved from the per-query `CentralityRanker` instance
  (recreated every call, so the cache was always empty) to the long-lived `CodeGraphStorage`,
  keyed on a monotonic version counter rather than node/edge counts (which equal-count churn and
  in-place edge mutation could defeat). Eliminates ~53ms/query of redundant PageRank recompute.
  See `docs/adr/0010-centrality-memo-invalidation.md`.
- SSCG subgraph extraction is now skipped when `include_subgraph` is false — previously computed
  unconditionally on every query and discarded under the production default.
- Result assembly (centrality scoring + subgraph extraction) was running outside the reindex read
  lock — a concurrent reindex could mutate the graph mid-scoring. `SearchOrchestrator._execute`
  split into `_maybe_reindex` (write-lock scope) + `_search`, so `run()` now holds one read lock
  across `_search` and `_assemble`. Closes the ADR-0008 gap.
- Dropped `SymbolHashCache` disk persistence and a dead symbol-name lookup path.
- Log hygiene: zero-chunk files are now named in warnings; the dropped-URI counter is split into
  `n_dropped_non_file_uri`/`n_dropped_outside_root`; legitimately-empty files no longer warn;
  scan counters now sum (`scanned + skipped + empty == supported`); a GLSL call-graph log line
  that was discarded at source by a too-late logging configuration now reaches a handler; recovery-
  ladder probe misses no longer warn; `[PARSE_WARN]` (formerly `[PARSE_ERROR]`) downgrades to
  DEBUG when the surrounding content survives chunking.
- Minor: safer futures-dict typing, tmp-file cleanup no longer raises out of
  `ChunkEmbeddingCache.save()`, and a corrected pyrefly suppression category.

### Performance

- Composite search-latency win from six independent fixes (parallelized call-edge resolvers,
  `readline()`-based frame reads, length-sorted embedding batching, memoized BM25 tokenizer
  fallback, process-isolated pyan/libcst resolvers, single round-trip `MetadataStore.get`):
  measured **138ms/query (13.5%)** on an isolated before/after A/B on the same index, with the
  untouched rerank phase (~80% of wall clock) differing by only 0.43% as a comparability check.
- Full-index embedding phase: 33.94s → 0.75s warm-cache median (43×) via the persistent chunk
  embedding cache above.

### Security

- `gitpython` bumped to ≥3.1.55 (8 argument-injection CVEs) and `setuptools` to ≥83.0.0
  (CVE-2026-59890 MANIFEST.in path traversal) — 9 CVEs total.

### Removed

- `bm25_k_parameter` config field — dead code, never read by any scoring path, superseded by
  real `bm25_k1`/`bm25_b`. Safe for existing configs: unknown keys are silently dropped.
- `tree-sitter-java` dependency — was declared but had no corresponding language-registry entry.

---

## [0.21.0] - 2026-07-23

### Added

- **MCPB extension bundle** (`code-search-extension/`) — packages the MCP server as a distributable
  Claude Desktop extension.
- **Module-preamble chunks** — emit a dedicated chunk for each file's leading imports/module
  docstring and respect it in reranker ordering, giving searches import-context without inflating
  the first code chunk.
- **MCP-server hardening** per the architecture-patterns paper on tool-count budgets (arXiv:2606.30317):
  core/advanced tool tiers gated behind `MCP_EXPOSE_ADVANCED_TOOLS` (10 core tools always listed, 8
  advanced config/tuning/destructive tools hidden from `list_tools` by default but still dispatchable
  by name), async index jobs, dispatch telemetry, and a mutation lock serializing index-mutating calls.
- **Claude Desktop MCP setup guide** — new doc walking through StreamableHTTP client configuration.
- **Parse-once measurement harness** — profiled a single shared `ParsedSource` per file across chunking
  and relationship extraction; declined as its own ADR (ADR-0009) since the seam landed as a
  straightforward refactor rather than an architecturally contentious choice.
- **Reranker comparison benchmarking** (`scripts/benchmark/run_sscg_benchmark.py`) — `--reranker-model`
  and `--reranker-enabled` flags override the reranker for a single run; `--reranker-sweep` runs a
  predefined `RERANKER_SWEEP` (gte, jina_v3, qwen_0.6b, bge_v2_m3, none) and prints a comparison
  leaderboard. `--category` now accepts a comma-separated list (e.g. `A,B,C`). Leaderboard gained a
  `VRAM(GB)` column (peak `torch.cuda.max_memory_reserved()` per run).

### Changed

- **Default embedding model** switched to `BAAI/bge-m3` across every config reader
  (`search/config.py:EmbeddingConfig`, `ModelPoolManager`), replacing the prior per-reader defaults.
- **`SearchMode` StrEnum** (`search/config.py`) centralizes the `hybrid`/`semantic`/`bm25`/`auto`
  search-mode literals that were previously scattered as bare strings.
- **`ParsedSource` seam** extracted for `TreeSitterChunker`, decoupling parse output from the chunker's
  internal representation.
- Removed the superseded `mcp-search-tool` skill (folded into `auto-git-workflow`).
- Untracked `search_config.json` from the repo index; added a `.example` template with a loader
  fallback so a missing local config no longer breaks startup.
- `call_graph.use_pyproject_toml` default corrected; added `lsp_total_timeout_seconds` config knob.
- **Reranker selection UI** (`start_mcp_server.cmd`) — removed BGE (`BAAI/bge-reranker-v2-m3`) from the
  interactive "Select Reranker Model" menu: benchmarked as strictly dominated by GTE on speed (MRR
  0.748 @ 193ms vs BGE's 0.716 @ 268ms, same VRAM) and by Qwen3/Jina on quality, with no scenario where
  it's the right pick. Remaining GTE/Qwen3/Jina v3 choices renumbered 1-3 and annotated with
  VRAM-tier guidance and benchmark numbers (MRR/latency/VRAM) to help pick a model for a given machine.
  `README.md` and `docs/ADVANCED_FEATURES_GUIDE.md` updated to match (BGE reranker mentions removed
  from current-facing docs; dated historical/changelog records elsewhere left untouched).

### Fixed

- **Qwen3-Reranker prompt bug** — `GenerativeReranker.rerank()` (`search/neural_reranker.py`) built an
  ad-hoc prompt with capitalized `Yes`/`No` target tokens instead of the official Qwen3-Reranker
  instruct template (arXiv:2506.05176 §2 "Reranking Models": chat-wrapped
  `<Instruct>`/`<Query>`/`<Document>` fields, lowercase `yes`/`no`). Off-distribution for the
  fine-tuned model, causing degenerate, poorly-calibrated relevance scores — measured MRR 0.311, *below*
  the no-reranker baseline (0.372) on the SSCG A/B/C golden-query benchmark. Switched to the official
  template; verified fix restores correct top-of-list ranking on a live repro query and lifts MRR to
  0.754 (RTX 4090, 45 queries, k=7), now competitive with GTE (0.748). Added a regression test
  (`test_rerank_uses_official_qwen3_template`) asserting the required template markers.
- **Stale golden-dataset chunk IDs** — 3 of 45 category A/B/C queries in
  `evaluation/golden_dataset.json` (Q12, Q48, Q53) referenced symbols deleted by the v0.12.3
  multi-model-pool → single-model refactor (`mcp_server/tools/config_handlers.py:_detect_indexed_model`,
  `ModelPoolManager.initialize_pool`, `ModelPoolManager._load_pool_embedder` — confirmed removed via
  direct index lookup). Retargeted to the live `ModelPoolManager.get_embedder` equivalent; 0 stale
  references remain.
- **LSP call-graph resolver deadlock** eliminated via a persistent reader thread instead of a
  per-request subprocess pipe.
- **Scope-aware call-graph resolution** — fixed alias misbinding where an imported name shadowed by a
  local variable of the same name was resolved to the wrong callee.
- Serialized auto-reindex against in-flight searches; added reranker inference locks to prevent
  concurrent GPU access during model swap.
- **Effective-Python audit** — narrowed broad `except` handlers to their real raise surface, added
  write-locks around shared mutable state, offloaded event-loop-blocking calls (`asyncio.to_thread`),
  fixed an O(n²) constant-usage scan, and addressed the remaining PR #40 review follow-ups (rwlock
  cleanup, a real-lock drain test, a logger parameter fix).
- Corrected several drifted golden-dataset caller/callee relevance grades (C004, OB02, OB07) and
  `ParsedSource` typing in `repo_profiler.profile_parsed` / `measure_parse_once`.
- Silenced a benign uvicorn ASGI error on Ctrl+C HTTP-server shutdown.
- Stopped pytest failure-injection logs from bleeding into `logs/mcp_server.log`.
- Aligned CI and local quality gates (pyrefly, Node 20 `upload-artifact@v6`, pre-commit).

### Performance

- Shared a single AST walk across relationship extractors instead of re-walking per extractor.
- Dedent-once for call-graph and phase-3 relationship extraction.
- Memoized per-file import context and class signature lookups (I2/I2b).
- Collapsed per-query config fetches in the reranking engine (R1).
- Shared mtime-cached file read between context-extraction helpers (I1).
- Removed a dead metadata re-score loop from `rerank_by_query` (Q1).
- Read each source file once during chunking instead of re-reading per chunk (B3).
- Deferred semantic-search enrichment until after rank+truncate (A1).
- Iterative (non-recursive) complexity walk; faster non-whitespace counting in the chunker.

### Security

- Resolved 21 dependency CVEs; re-synced `transformers` to its security-patched pin.
- Upgraded `transformers` to 5.x and dropped the ONNX optional extra to unblock CVE-2026-4372.

*3 chore-only commits (uv.lock relocks, a trailing-newline cleanup) omitted as non-user-facing.*

---

## [0.20.1] - 2026-07-02

### Fixed

- **Intent-classifier verification-term routing (Q12)** — merged a long-pending fix
  (`fae6256d`, originally opened before the `INTENT_RULES` extraction to
  `config/intent_rules.yaml`) adding `check whether` / `verify` keyword and pattern
  coverage to the `local` intent rules, so existence-checking queries such as "verify
  X exists" and "check whether Y is present" route correctly. Ported into the YAML
  config instead of the superseded hardcoded dict to preserve the current
  config-driven architecture.

---

## [0.20.0] - 2026-06-30

### Added

- **Codecov integration** — `codecov/codecov-action@v5` upload step in `branch-protection.yml` CI (test
  job, development-branch only). Pytest now emits `--cov-report=xml`; XML is uploaded to Codecov on every
  CI run, including on `--cov-fail-under` failures so coverage regressions are still visible. README badge
  tracks the `development` branch (the only branch where tests run).

### Changed

- **Campaign-2 Tier-1 refactors** (all behavior-preserving, 3100 pass / 13 skip):
  - `43465afc` — `SnapshotManager.resolve_project_id()` single owner; both cleanup scripts routed
    through it, fixing a false-positive stale-snapshot flag on Windows v2 projects.
  - `c1e58e37` — `ResultFactory._from_tuples()` private helper; three byte-identical `source=`-only
    loops collapsed into one.
  - `e808db94` — `edge_relation_type()` accessor in `graph/schema.py`; 6 inline dual-key `.get()` calls
    replaced.
  - `455e56be` — `BaseReranker` ABC owns `is_loaded`, `get_vram_usage`, `cleanup`; three reranker
    classes inherit instead of duplicating.
  - `0d4d5bc6` — `prepare_scoped_files()` shared preamble in `call_edge_resolver.py`; three resolver
    `resolve()` methods deduped.
  - `bde66586` — `_two_pass_build()` shared graph builder in `graph_integration.py`; `cx32` hotspot
    decomposed via two thin normalizer wrappers.

### Fixed

- **Pyrefly type regressions** (`33f40dc2`) — restored `# pyrefly: ignore` annotations dropped during
  T2/T6 refactors (`search/graph_integration.py` lines 403, 404, 425); tightened reverse-edge guard in
  `graph/graph_storage.py` for cross-variable narrowing. 0 pyrefly errors on `development`.
- **Integration-test model downloads** (`234a3176`) — 7 integration tests that attempted a real
  `Alibaba-NLP/gte-modernbert-base` download in CI now mock `embeddings.model_loader.ModelLoader.load`
  via `_FakeEmbeddingModel` (768-dim, CPU, no real attributes). CI green without model caching.

---

## [0.19.0] - 2026-06-27

### Removed

- **Multi-model embedding routing** — `RoutingConfig` and all `cfg.routing.*` references deleted from
  `search/config.py`. `MODEL_REGISTRY` pruned from 7 to **5 models**: `BAAI/bge-m3`,
  `google/embeddinggemma-300m` (default), `nomic-ai/CodeRankEmbed`,
  `Alibaba-NLP/gte-modernbert-base`, `Qwen/Qwen3-Embedding-0.6B`. Removed models: `BAAI/bge-code-v1`,
  `Qwen/Qwen3-Embedding-4B`, `jinaai/jina-embeddings-v5*`.
- **`configure_query_routing` MCP tool** — removed from `mcp_server/tool_registry.py`. Server now
  exposes exactly **18 tools** (down from 19).

### Changed

- **Launcher UI cleanup** (`5717afd`, `start_mcp_server.cmd`) — dead code blocks deleted
  (`:install_cuda`, `:force_cpu_mode`, `:test_install`, `:end`); duplicate `:select_embedding_model`
  menu body replaced with `goto quick_model_switch` (single source of truth); stale SSE tombstone
  comment block removed. Ten display values corrected to match `search/config.py` actuals:
  BM25/Dense weights 0.4/0.6→**0.35/0.65**, community_resolution 1.1/1.5→**1.0**,
  `min_vram_gb` ≥6GB→**≥2GB**, output format default compact→**ultra**, reranker quality
  +5-15%%→**+15-25%%**.
- **Docs cleanup** (`ef0b1ba`) — multi-model routing sections deleted from
  `docs/ADVANCED_FEATURES_GUIDE.md` (~250 lines: §Multi-Model Query Routing + §Multi-Model Batch
  Indexing), `docs/MCP_TOOLS_REFERENCE.md` (`configure_query_routing` row; §Multi-Model Batch
  Indexing; `model_key`/`use_routing` params from `search_code`; `k=4`→7 in example),
  `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md` (~183 lines: §Multi-Model Query Routing v0.5.4+),
  and `docs/CLAUDE_MD_TEMPLATE.md` (`configure_query_routing` row; tool count 19→18).

---

## [0.18.0] - 2026-06-26

### Changed

- **`source_order_output` default `True→False`** (`search/config.py`, `docs/MCP_TOOLS_REFERENCE.md`) —
  `search_code` now emits results in **relevance order** (centrality-reranked blended_score descending)
  instead of DOS-RAG file/line order. Module/community summary chunks are demoted to the tail for
  non-GLOBAL queries; `reranker_score` is preserved per-row for optional consumer re-sort. DOS-RAG order
  is still available via `source_order_output=true`. The searcher-only SSCG harness
  (`run_sscg_benchmark.py`, calls `searcher.search()` directly) and the DSPy agent eval (re-sorts by
  `reranker_score` internally) bypass `SearchOrchestrator._apply_source_order_and_budget` and are
  unaffected. Validated on MCP-pipeline eval (45 A/B/C golden queries through `SearchOrchestrator.run()`):
  **MRR 0.700→0.8278** (+0.128), **Hit@7 0.978** (44/45), Recall@7 0.666 (≈flat vs 0.696 baseline).

### Added

- **`scripts/benchmark/run_mcp_pipeline_eval.py`** — emission-order SSCG eval through the real
  `SearchOrchestrator.run()` pipeline. Measures position-sensitive MRR/Recall@7 using chunk IDs in
  emission order (no post-sort), testing the full `_apply_source_order_and_budget` code path that
  `run_sscg_benchmark.py` bypasses.

---

## [0.17.0] - 2026-06-24

### Added — DSPy/GEPA agent-evaluation harness

- **Claude Code subscription LM backend for DSPy** (`d696615`, `utils/dspy_claude_code.py`, `docs/DSPY_SETUP.md`) — `ClaudeCodeLM(dspy.BaseLM)` shells to `claude -p --output-format json` for rollout and reflection, routing all LM calls through a Claude Max subscription with zero API cost. Handles CLI JSON envelope parsing (dict and array shapes), async dispatch via `asyncio.to_thread`, and intentionally-zero token/cost accounting. Configured via `configure_dspy()` helper.
- **DSPy ReAct → code-search HTTP server bridge** (`d4396a5`) — wraps the running MCP HTTP transport as DSPy-callable tools, enabling structured agent rollouts against the live search index for benchmark and optimization work.
- **DSPy agent-evaluation harness** (`af7f812`) — end-to-end harness for evaluating and optimizing the code-search MCP tool-use agent via `dspy.Evaluate` and `dspy.GEPA`; dataset loading, metric wiring, and trace collection included.
- **GEPA optimization harness for CodeNavQA** (`21f74c5`, `883d6ad`, `5766c12`, `ebf6002`, `721c4cf`) — reflective evolutionary search over the `CodeNavQA` DSPy signature with the subscription LM as the reflection/proposer backend. GEPA-discovered guidance distilled back into the signature improved **Recall@7 0.668→0.717**. Includes chunk-id verbatim copy fix (`ebf6002`), unranked recall ceiling metric (`721c4cf`), and tool-vs-agent recall diagnostic.
- **Optional `[gpu]` extra** (`pyproject.toml`) — `nvidia-ml-py>=12.535.77`; previously a transitive dependency, now explicitly pinned under `[gpu]` for NVML-backed VRAM monitoring.
- **`ClaudeCodeLM` test suite** (`e2fcd2f`, `tests/unit/utils/test_dspy_claude_code.py`) — CLI array-format and dict-format JSON parsing tests; **2,853 unit tests** total.

### Changed

- **Search `default_k` 4→7** (`447dc9a`, `search_config.json`) — SSCG benchmark (k=7 hybrid, 2026-05-25): MRR 0.806, Recall@7 0.700, Hit@7 100% — vs k=4 baseline: MRR +0.093, Recall@7 +0.122. Targets that previously fell at rank 5–7 are now reliably retrieved. Pass `k=7` explicitly in production code (defensive against config drift).
- **`mcp<2` upper pin** (`946f087`, `pyproject.toml`) — pins `mcp>=1.27.0,<2` to prevent accidental uptake of the v2 breaking-change release; `starlette>=1.3.1` promoted to a direct dependency so the CVE floor is enforced without transitive drift.
- **GEPA-discovered search guidance ported to `mcp-search-tool` skill** (`110e4d1`) — multi-query strategy (3–6 diverse phrasings), `include_context=true` default, `reranker_score`-first sort, MRR lead-chunk rule, and metadata-only refetch gotcha added to the dotfiles skill.

### Security

- **CVE remediation: 53→5 advisories** — two rounds of dependency upgrades:
  - **Round 1** (`3331c57`): 12 packages upgraded; 53→11 advisories. Includes `aiohttp>=3.14.1`, `python-dotenv>=1.2.2`, plus updates to `certifi`, `urllib3`, `requests`, `cryptography`, and others.
  - **Round 2** (`946f087`): `starlette 0.52.1→1.3.1`; 11→5 advisories. 5 advisories remain (all low/medium-severity; documented in `pyproject.toml` security comment block).

### Performance

- **AST parse-once across relationship extractors** (`fb3d628`, `chunking/relationships/`) — a single parse result is now shared across all extractor passes per chunk instead of re-parsing per extractor; reduces CPU 2–4× on Python-heavy codebases. (#15)
- **Single-pass file-accessibility probe** (`e995376`, `aec4e2c`, `mcp_server/tools/index_handlers.py`) — `rglob` runs once per index operation; `chunked_paths` set hoisted out of the inner loop; per-file `supported`-extension log line removed. (#17, #18)
- **Batch 4 — embedding throughput + NVML** (`33c3b12`) — 7 targeted improvements: batch-size auto-tuner, ONNX warm-up token count, NVML free-memory polling, sentence-transformers `trust_remote_code`, and related throughput micro-opts. (#50–#56, #59)

### Fixed

- **Merged community chunks lost call/relationship edges** (`43dde19`, `graph/graph_storage.py`) — `union_edges` only iterated the first member's edges; a merged chunk spanning multiple members silently dropped all non-lead-member edges from `find_connections`. Fixed: union across all members. (#28, #16)
- **Batch 3 — event-loop and contract fixes** (`9e88b20`) — six async handlers offloaded to `asyncio.to_thread`; metadata cache cleared on reindex; ONNX session max-sequence-length contract enforced at 2048 tokens; dead `_graph_scorer` field removed; graph node-ID normalization; benchmark line-check fix; Merkle sentinel write. (#43–#49)
- **Batch 5 — routing-metadata and clarity** (`e4998f0`) — routing-metadata `None` propagation bug fixed; five P3 code-clarity refactors. (#57, #58, #60–#62)
- **Indexing RAM-fallback override decoupled from config singleton** (`0e60a1d`) — override no longer mutates the shared `SearchConfig` singleton, preventing cross-request contamination in concurrent HTTP scenarios.
- **Arena-polluted ONNX activation measurement excluded from batch sizing** (`2608aca`) — first-batch measurements inflated by arena allocation were used to set the per-batch ceiling, causing overly conservative sizes after warm-up. Fixed: discard the first measurement.
- **Non-hybrid path strips persisted content** (`f89fdb7`, `search/`) — BM25-only and semantic-only paths now strip persisted `content` fields from results, consistent with the hybrid path. ONNX memory-management ADR added (`docs/adr/`).
- **Windows cp1252 decode errors on `claude` CLI subprocess** (`ceb737e`, `utils/dspy_claude_code.py`) — `claude -p` output contains Unicode characters; `subprocess.run` on Windows defaults to cp1252. Fixed: `encoding="utf-8"` on the subprocess call.
- **Pyrefly static-type cleanup** (`c6a9a1d`, `475d11c`) — `get_embedder` non-None assertion; `_class_file_cache` `getattr` annotated `Optional`. No runtime changes.

---

## [0.16.0] - 2026-06-11

### Fixed — Correctness & integrity (Batch 1)

- **Silent, permanent index data loss on embed failure** (`0b7b94c`, `search/incremental_indexer.py:_add_new_chunks`) — `embed_chunks` was wrapped in a swallowing `except Exception: logger.warning(...)` that returned `0`. The incremental flow had already deleted old chunks, then silently advanced the Merkle snapshot, permanently dropping modified files from the index until their content changed again. Fix: removed the swallowing handler; let `embed_chunks` raise so the outer handler routes to `_attempt_recovery`. (#1)
- **Stale searcher served for wrong project/model after failed switch** (`0b7b94c`, `mcp_server/search_factory.py:get_searcher`) — `current_project`/`current_model_key` were mutated *before* construction; a `DimensionMismatchError` left `state.searcher` pointing to the previous project's index while cache keys matched the new one, so the next call silently returned stale results. Fix: commit all three state fields atomically on success only; set `state.searcher = None` on failure. (#2)
- **File-read "timeout" deadlocked instead of timing out** (`f4c3891`, `chunking/tree_sitter.py:_read_file_with_timeout`) — the `with ThreadPoolExecutor(...)` context-manager `__exit__` called `shutdown(wait=True)`, blocking forever on a genuinely locked file. Fix: drop context-manager form; call `shutdown(wait=False, cancel_futures=True)` on timeout. (#6)
- **Import resolution silently broken when CWD ≠ project root** (`6780a94`, `chunking/multi_language_chunker.py`) — `chunk.relative_path` was passed to the import resolver, which opened it against the process CWD. For an MCP server started anywhere other than the project root every import read failed with `OSError`; an empty import map was cached per file, quietly degrading call-graph quality. Fix: pass `chunk.file_path` (absolute) to both call and phase-3 extraction passes. (#8)
- **ONNX `provider_options` type mismatch caused silent PyTorch fallback** (`fb8372c`, `embeddings/onnx_loader.py:340`) — passing a list `[{...}]` to Optimum 1.25.0 (`provider_options: Optional[Dict]`) created a nested `[[{...}]]`; session creation failed and `load()` silently fell back to PyTorch, losing both the ONNX speedup and the VRAM cap. Fix: pass a plain dict. (#9)
- **`handle_clear_index` deleted files while handles were open** (`535f5cd`, `mcp_server/tools/index_handlers.py`) — SQLite and index files were deleted before `reset_search_components()`, raising `PermissionError` on Windows. Fix: call `close_project_resources()` before any `rmtree`/`unlink`, matching `handle_delete_project`. (#10)
- **`HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` leaked across model loads** (`fb8372c`, `embeddings/model_loader.py`) — env vars set after a successful cached load put the whole process in offline mode; loading a different uncached model later failed with a misleading "not found on Hub". Fix: removed both `os.environ.setdefault(...)` calls; the constructor's `local_files_only=True` is sufficient. (#11)
- **Ancestor-directory names disabled indexing entirely** (`f4c3891`, `chunking/multi_language_chunker.py`, `merkle/merkle_dag.py`) — `any(part in DEFAULT_IGNORED_DIRS for part in file_path.parts)` matched *absolute* path components; a repo under any ancestor named `build`, `dist`, `env`, `logs`, etc. indexed zero files. Fix: scope the check to `file_path.relative_to(dir_path).parts`; guard `build_node` with `path != self.root_path`. (#12)
- **`find_connections` results were iteration-order dependent** (`07965a0`, `graph/graph_queries.py`) — BFS marked nodes `visited` before the `relation_types` filter, so a first encounter via a non-matching edge permanently suppressed a later matching one. Fix: separate `visited` (BFS expansion) from `reported` (result dedup) sets. (#23)

### Fixed — Concurrency / event-loop (Batch 2B)

- **Shared MCP singletons had no construction/teardown synchronization** (`7067978`, `mcp_server/state.py`, `mcp_server/search_factory.py`, `mcp_server/model_pool_manager.py`) — in HTTP stateless mode concurrent `call_tool` requests could each construct their own `CodeEmbedder` (doubling VRAM, leaking the loser), produce duplicate FAISS/BM25 loads, or null a searcher mid-request during teardown. Fix: single `threading.RLock` on `ApplicationState` (survives `reset()`; reentrancy covers `get_searcher → get_index_manager → get_embedder` chain) + separate module-level `threading.Lock` for the pool factory; double-checked locking at every lazy-init and teardown site. See [ADR-0006](docs/adr/0006-thread-safety-of-module-singletons.md). (#7)
- **Heavy synchronous work stalled the event loop** (`4ffa9cc`, `mcp_server/tools/search_orchestrator.py`, `mcp_server/tools/search_handlers.py`, `mcp_server/tools/index_handlers.py`) — `_check_auto_reindex` (worst case: full GPU reindex triggered by a routine `search_code` on a stale index) ran synchronously on the event loop, freezing all concurrent requests and timing out MCP pings for minutes. `get_searcher` (cache-miss path) and `_handle_chunk_id_lookup` also blocked inline. Fix: wrap each in `asyncio.to_thread()`; add a per-project `asyncio.Lock` (stored on `ApplicationState`) so two concurrent searches cannot start overlapping reindexes for the same project. (#5)
- **Parallel chunker shared non-thread-safe parser and extractor state** (`7d8efc5`, `chunking/tree_sitter.py`, `chunking/multi_language_chunker.py`) — py-tree-sitter ≥0.25 releases the GIL during `parse()`; concurrent `parse()` calls on a shared `TSParser` are undefined behavior (crashes, corrupt trees). The call-graph and relationship extractors mutated per-call instance state (`self.edges`, `self._imports`, `self._current_class`), so concurrent files cross-contaminated. Fix: `TreeSitterChunker.get_chunker` uses `threading.local` for per-thread parser/chunker cache; `MultiLanguageChunker` builds `call_graph_extractor` and `relationship_extractors` per-thread via `_init_thread_extractors()` / `_ensure_thread_extractors()`. Parallel-vs-serial determinism verified: identical chunk IDs and relationship edges across 8 threads. (#4)

### Changed — Batch 2A correctness

- **Call graph migrated from `DiGraph` to `MultiDiGraph`** (`ae13947`, `d1b98da`, `graph/graph_storage.py`, `search/graph_integration.py`) — `nx.DiGraph` permits one edge per `(u, v)` pair; a chunk that both `calls` and `instantiates` the same symbol kept only the last extractor's type. All downstream consumers (`get_relationships`, `find_connections`, subgraph extraction) operated on a lossy graph. Fix: `MultiDiGraph` keyed by relationship type; backward-compat coerce-on-load for existing serialized graphs; centrality parity via a simple-digraph view. (#3)
- **Atomic JSON writes at all snapshot and graph save sites** (`4a0981e`, `merkle/snapshot_manager.py`, `graph/graph_storage.py`) — `write_json_atomic` helper (write tmp → `os.replace`) introduced and wired into all 4 JSON write sites; a crash mid-write no longer leaves a truncated file that breaks the next load. Also fixed a caller-dict mutation bug in `save_snapshot`. (#27)
- **Merkle traversal hardened** (`6b2aa45`, `merkle/merkle_dag.py`, `merkle/change_detector.py`) — symlink-cycle guard prevents infinite rglob traversal (= silent subtree-drop); per-entry exception isolation so one bad path doesn't abort the whole walk; snapshot-ignore path now compared relative to the root so it actually matches. (#21)
- **Static type cleanup (pyrefly)** (`8773263`, `ad0a095`, `20502ed`) — Optional guards, unconditional `networkx` import, widened extractor annotations across `mcp_server/`, `search/`, and `chunking/relationships/`. No runtime behavior changes.

### Fixed — Easy wins

- `faiss_index.py:save()` — replaced `[reconstruct(i) for i in range(ntotal)]` with `reconstruct_n(0, ntotal)` (one C++ memcpy). (#19)
- `embedder.py:embed_chunks` — module logger now restored in `finally`; a `VRAMExhaustedError` no longer silently left the logger at WARNING for the rest of the process. (#20)
- `faiss_index.py:add()` — added `.copy()` before `faiss.normalize_L2` to avoid in-place mutation of the caller's embedding array. (#29)
- `embedder.py:embed_chunk` — wrapped `model.encode()` in `with self._lifecycle_lock:` so a concurrent `cleanup()` cannot null `self.model` mid-call. (#35)
- `embedder.py` / `incremental_indexer.py` — two `zip(...)` changed to `strict=True`; a length mismatch is now a loud failure, not a silent truncation. (#38)
- `merkle/snapshot_manager.py` — `print(...)` version-mismatch warning changed to `logger.warning()` to avoid corrupting the MCP stdio JSON-RPC channel. (#32)
- `utils/version_check.py` — version tuples padded to ≥3 elements; `(2, 8) < (2, 8, 0)` false-positive fixed. Pre-release stripping uses `re.split`. (#41)
- `graph/graph_queries.py` — `find_call_chain` now normalizes path separators (Windows backslash fix); `compute_centrality("degree")` return values cast to `float`. (#40)
- `mcp_server/server.py` — `output_format` popped before dispatch rather than after. (#36)
- `embeddings/embedder.py` — `logging.basicConfig(level=INFO)` removed from `CodeEmbedder.__init__`; library code should not mutate root logging. (#37)

### Added

- **`tests/unit/chunking/test_thread_isolation.py`** — 4 determinism tests: `TreeSitterChunker` 8-thread parallel-vs-serial chunk-ID equality; `MultiLanguageChunker` parallel chunk-ID equality, parallel relationship-edge equality, and cross-file non-contamination (4-file × 4-repeat matrix). All pass against production indexing paths.

### Fixed — Benchmark harness (post-0.15.0, 2026-06-08)

- **Line-overlap metrics returned 0.000** (`184e13b`, `scripts/benchmark/run_sscg_benchmark.py`) — `_extract_ranges_from_results` read line data as top-level attributes; `SearchResult` stores them in `.metadata`. Real values: LR 0.852, LP 0.267, LIoU 0.304.
- **SSCG golden-set drift** (`b5cfc24`, `evaluation/golden_dataset.json`) — stale `search/filters.py:normalize_path` removed from Q05 (capped Recall at 0.67); two MISSING distractors cleaned from Q35.
- **Pass/fail gate now enforces JSON thresholds** (`b5cfc24`, `evaluation/metrics.py`) — `aggregate_metrics` reads `thresholds` from `golden_dataset.json`; the module constant is a fallback only.
- **`recall@7` / `hit_rate@7`** auto-computed by the benchmark runner; previously manual figures only.

---

## [0.15.0] - 2026-06-03

### Added

- **Resolver precision tuning** — pyan3 callee-flavor filter (drops callee-side edges from pyan, which has no callee role, reducing false positives); wildcard-import down-weighting; LibCST self-call resolution for method-on-self patterns; namespace guard to prevent re-injection of already-resolved namespaces; `resolve_cache` for repeat-FQN lookup de-duplication across large codebases.
- **`CallGraphConfig.min_confidence`** (`search/config.py`) — injection floor (float, default `0.0` — accepts all edges, no behaviour change); raising it (e.g. `0.65`) drops edges below the threshold before graph injection, allowing users to trade recall for precision without reindexing.
- **`CallGraphConfig.use_pyproject_toml`** (`search/config.py`) — boolean flag (default `false`); passes LibCST's `use_pyproject_toml=True` for correct src-layout package discovery.
- **`docs/CALL_GRAPH_TUNING.md`** — API reference, confidence tiers, tuning recipes, and §6.4 LSP diagnostics counters (`probes`, `null_prepares`, `items`, `outgoing_calls`, `dropped_uri`, `dropped_no_chunk`) with health-signal interpretation.
- **2,495 unit tests** + 19 integration tests (net ~44 new tests from resolver tuning and LSP repair).

### Fixed

- **LSP resolver repair (`aee8c63`, `3ffca25`)** — three protocol bugs fixed: (1) `prepareCallHierarchy` was probing at column 0 instead of the symbol-name character offset; (2) JSON-RPC responses were not correlated by `id` — notifications discarded, `workspace/configuration` server-requests stubbed, wrong-id responses skipped; (3) basedpyright emits `file:///f%3A/...` (lowercase drive + percent-encoded colon) which Python ≤3.13 `url2pathname` cannot parse without a preceding `unquote()`. Combined effect: LSP tier went from silently resolving **0 edges** to **938 edges (added=64, upgraded=869)** on this codebase.
- **LibCST: absolute path keys + UTF-8 reads** (`b50d234`) — chunk-ID path normalization now produces absolute-path keys consistent with the graph store, fixing FQN resolution misses.
- **LibCST: `zip(strict=False)` in resolve loop** (`5b7954d`) — prevents `ValueError` on mismatched iterable lengths in edge injection.

---

## [0.14.0] - 2026-06-03

### Added

- **Layered call-graph resolver pipeline** (`chunking/relationships/call_edge_resolver.py`) — `ResolvedEdge` frozen dataclass, `CallEdgeResolver` `@runtime_checkable` Protocol, shared file-collection helpers (`gather_py_files`, `scope_to_indexed_files`, `validate_py_files`), and `run_resolvers()` that merges edges from all available resolvers by `(caller_id, callee_id)` key keeping the highest-confidence version. Confidence ladder: AST 0.5/0.7 → pyan 0.75 (`chunking/relationships/external_call_graph.py`, now import-guarded) → LibCST 0.90 (`chunking/relationships/libcst_call_graph.py`, new) → LSP/basedpyright 0.98 (`chunking/relationships/lsp_call_graph.py`, new, opt-in).
- **Optional extras** (`pyproject.toml`) — `[callgraph]` (pyan3 + libcst, GPL-2.0 isolated) and `[lsp]` (basedpyright). Core install is Apache-2.0-clean; without extras only in-house AST edges are produced. Install `pip install -e ".[callgraph]"` to activate pyan3 + LibCST resolvers.
- **`CallGraphConfig`** (`search/config.py`) — `resolvers: list[str]`, `lsp_enabled: bool`, `lsp_timeout_seconds: float`; wired into `SearchConfig` + `search_config.json`.
- **Bidirectional callees** — `direct_callees`, `direct_callees_exact/recovered/ambiguous`, and `callee_confidence` breakdown added to `ImpactReport` (`search/types.py`). `RelationshipAnalyzer._enrich_callees()` mirrors `_enrich_callers` for outbound `calls` edges. `find_connections` now returns both callers and callees with `resolver_source` / `resolver_confidence` per-entry provenance.
- **`upgrade_call_edge()`** (`graph/graph_storage.py`) — in-place edge-attribute update enabling confidence-precedence upgrades during injection.
- **`_inject_call_edges`** (`search/index_write_stage.py`) — replaces `_inject_pyan_edges`; reads `CallGraphConfig`, instantiates enabled + available resolvers, calls `run_resolvers()`, and merges with confidence-precedence semantics.
- **Callee golden set** (`evaluation/callee_golden.json`) — 7-query outbound golden set for `--direction callees` benchmarking.
- **63 new unit tests**: `test_call_edge_resolver.py` (31), `test_call_graph_config.py` (15), `test_libcst_call_graph.py` (15), `test_lsp_call_graph.py` (17).

### Fixed

- **`c478f54` — edge attribute renamed `source` → `resolver_source`** (`search/index_write_stage.py`, `search/relationship_analyzer.py`) — NetworkX node-link format reserves `"source"` and `"target"` as endpoint keys; an edge attribute named `"source"` was silently destroyed on save/load round-trip, making resolver provenance invisible after reindex.
- **`ec005b2` — `get_edge_data` preserves legacy string confidence tags** (`graph/graph_storage.py`) — string tags `"exact"`, `"ambiguous"`, `"recovered"` were unconditionally coerced to `float()`, yielding `1.0` with a spurious warning and causing ambiguous edges to be miscounted as exact in `callee_confidence` breakdowns. Fixed via `_LEGACY_CONFIDENCE_TAGS` pass-through.

### Changed

- **pyan3 demoted from core to optional extra** — pyan3 (GPL-2.0) moved from `install_requires` to the `[callgraph]` optional extra. Without extras only in-house AST edges (confidence 0.5/0.7) are produced — cross-module recall is lower but there is no crash and the Apache-2.0 core license is preserved.

---

## [0.13.0] - 2026-06-03

### Added

- **pyan3 cross-module caller edges in `find_connections`** (`chunking/relationships/external_call_graph.py`, new; `search/index_write_stage.py`) — `build_call_edges()` runs pyan3 on all indexed project `.py` files at full-index time and injects resolved `(caller_raw_id, callee_raw_id)` pairs directly into the code graph via `CodeGraphStorage.add_call_edge(source="pyan")`. The injection seam sits after `add_embeddings` (graph nodes populated) and before `save_indices` (edges persisted). Node→chunk_id mapping tries `filename + ast_node.lineno → find_enclosing_chunk` first, falls back to `chunk_id_from_fqn`. pyan3 is a hard `install_requires` dependency (no import guard, no enabled flag). Any pyan3 runtime failure is caught and logged as a non-fatal warning so it never aborts a full index. On the project's own codebase: 5,341 cross-module edges resolved, 3,594 injected, 1,747 skipped (node absent or edge already present).

- **Shared FQN / line-number → chunk_id helpers** (`evaluation/chunk_mapping.py`, new) — `build_line_to_chunk_map`, `find_enclosing_chunk`, and `chunk_id_from_fqn` promoted from private `build_caller_oracle.py` internals to a shared public module. `build_line_to_chunk_map(normalize=False)` returns raw store-key ids (with `:start-end:` line range) for graph alignment; `normalize=True` (default) strips line ranges for stable IDs. `find_enclosing_chunk` picks the innermost (smallest-span) chunk containing a given line, correctly handling nested class/method constructs.

- **Direct-caller recall evaluation harness** (`evaluation/caller_golden.json`, `scripts/benchmark/build_caller_oracle.py`, `scripts/benchmark/run_caller_recall.py`, `scripts/benchmark/run_caller_recall.sh`) — deterministic feedback loop for `find_connections` caller recall. `build_caller_oracle.py` uses ripgrep to build a ground-truth caller set for any target chunk_id. `run_caller_recall.py` provides `run` (per-query recall/precision/latency) and `compare` (before/after delta table) subcommands. Golden dataset covers 7 queries (C001–C007) including 2 cross-module pyan3 targets; baseline `results/caller_recall_pyan.json` shows `total_missed_callers: 0` (14/14 expected callers found).

### Fixed

- **`find_connections` missed direct callers after incremental reindex** (`search/relationship_analyzer.py`, `search/graph_integration.py`, `search/types.py`) — root-caused two independent failure classes and fixed across four phases:
  - *Phase 1*: Extracted `_resolve_by_symbol(symbol_name) → tuple | None` as a shared Tier 1→3 cascade (symbol_cache → graph suffix-scan → semantic search). `_enrich_callers` now retries stale callers via `_resolve_by_symbol` instead of silently discarding them; recovered callers are tagged `confidence="recovered"`.
  - *Phase 2*: `_resolve_call_target` common-method blocklist (`get`, `format`, etc.) now only drops a name when no project definition exists, preventing false drops for project-defined methods with generic names. Ambiguous-name resolution changed from a single phantom node to per-candidate `confidence="ambiguous"` edges, keeping all candidates retrievable.
  - *Phase 4*: `ImpactReport` gains `direct_callers_exact`, `direct_callers_recovered`, `direct_callers_ambiguous` counters; `to_dict()` emits a `"caller_confidence"` breakdown when any counter is non-zero. Recall improvement on 5-query golden set: `mean_recall` 0.5667 → 0.9500, callers found 8/12 → 12/12.

- **Stale graph node IDs caused `SearchError: Chunk not found`** (`search/relationship_analyzer.py`, `graph/graph_storage.py`, `search/incremental_indexer.py`) — the call graph and metadata store were maintained independently; incremental reindex deleted chunks from the metadata store but left their graph nodes, and any line-range drift after edits produced stale node IDs. Three layered fixes: (1) `_resolve_target` no longer raises immediately on a chunk_id miss — it derives the symbol name from the last colon-segment and falls through to Tier 1→3 symbol resolution; (2) `_enrich_reverse` / `_enrich_forward` zero out dead graph-node IDs (`resolvable=False`) so callers don't re-query them; (3) `CodeGraphStorage.remove_file_nodes(file_path)` prunes all nodes and incident edges for a file; `IncrementalIndexer._remove_old_chunks` now calls it for every deleted/modified file, keeping the two stores in sync.

- **`split_block` chunks emitted zero call edges** (`search/graph_integration.py`, `evaluation/metrics.py`) — `_extract_split_block_calls` attempted to `ast.parse` the stored content fragment (a bare body slice, not valid Python), so `PythonCallGraphExtractor.extract_calls` always returned `[]`. Fix: re-read the enclosing `FunctionDef` from the original source file using a per-file AST cache (one parse per file per build pass) and locate the method by line-range containment. A `_seen_split_methods` set deduplicates across split-block pieces so only the first block emits edges. `normalize_chunk_id` now maps `:split_block:` → `:method:` for benchmark ID alignment. Recall improvement on 5-query golden set: `mean_recall` 0.5667 → 0.9500, callers found 8/12 → 12/12 (baseline before Phase 3 pyan3 addition).

- **Windows backslash `relative_path` caused zero pyan3 edges injected** (`evaluation/chunk_mapping.py`) — the metadata store persists `relative_path` with Windows backslashes (`chunking\file_summarizer.py`) while `_node_to_raw_chunk_id` produced forward-slash lookup paths, so every dict lookup returned `[]`. Added `.replace("\\", "/")` normalization in `build_line_to_chunk_map`. Regression test `test_windows_backslash_relative_path_normalized` added.

- **Normalized chunk_ids raised `SearchError` in `_resolve_target`** (`search/relationship_analyzer.py`) — the stale-chunk_id symbol-retry fallback required `>= 4` colon-segments (raw format `file.py:10-20:type:name`) but `find_connections` callers and golden targets pass normalized ids with 3 segments (`file.py:type:name`). Threshold changed `>= 4` → `>= 3` so normalized ids fall through to symbol-retry instead of raising.

- **Tier 3 semantic search failures in `_resolve_by_symbol` logged without stack trace** (`search/relationship_analyzer.py`) — added `exc_info=True` to the `logger.warning` so tracebacks appear in debug logs.

- **pynvml per-device query failures in `handle_get_memory_status` swallowed silently** (`mcp_server/tools/status_handlers.py`) — added `exc_info=True` to the per-GPU exception handler so the failing device and error are visible in logs.

- **pyan3 edge injection scoped to indexed files; per-file `ast.parse` pre-validation** (`chunking/relationships/external_call_graph.py`) — the injector now iterates only over files that were indexed in the current run, eliminating spurious edges from unindexed trees such as `Scripts/` and site-packages. Each file is pre-validated with `ast.parse` before being passed to pyan3, so one unparseable file (e.g. a TouchDesigner YAML-in-`.py` config) no longer aborts edge injection for the whole project.

### Refactored

- **`exc_info=True` added to swallow-and-degrade exception handlers** (`graph/`, `search/`, `chunking/`, `utils/`, `tools/`) — exception handlers that log a warning and continue (rather than re-raising) now include `exc_info=True` so stack traces appear in debug logs without changing runtime behavior. Affected files: `graph/community_detector.py`, `search/hybrid_searcher.py`, `search/reranking_engine.py`, `search/incremental_indexer.py`, `chunking/multi_language_chunker.py`, `chunking/relationships/call_graph_extractor.py`, `utils/observability.py`, `tools/convert_onnx.py`.

### Security

- Dependency audit 2026-06-03: `pyjwt` 2.12.1 → 2.13.0 (CVE-2026-48522, CVE-2026-48524, CVE-2026-48525, CVE-2026-48526), `uv` 0.11.6 → 0.11.18 (GHSA-4gg8-gxpx-9rph, malicious-wheel entry-point path traversal). Four advisories remain deferred: sqlitedict CVE-2024-35515 (mitigated via JSON serialization in `metadata.py`), transformers 2×RCE (blocked by optimum-onnx pin), starlette host-header injection (localhost-only deployment, low risk).

---

## [0.12.4] - 2026-05-29

### Fixed

- **`CodeGraphStorage.clear()` left stale phantom nodes after full reindex** (`graph/graph_storage.py`) — `clear()` now deletes the backing `{project_id}_call_graph.json` file in addition to clearing the in-memory graph. Previously a subsequent `CodeGraphStorage` re-initialization reloaded the old JSON (including phantom nodes for deleted methods), causing them to survive rebuild and emit `WARNING - Chunk not found` during relationship queries. New test `test_clear_persists_to_disk` verifies the file is absent after clearing and a fresh instance starts empty.

- **`switch_project` always logged "No indexed model detected"** (`mcp_server/tools/config_handlers.py`) — `_detect_indexed_model` now reads `project_info.json` (pool-agnostic, written at index time) before falling back to the active-pool directory scan. Previously it only checked the active pool (e.g. `lightweight-speed`: `gte_modernbert`, `bge_m3`) and missed projects indexed with a model from a different pool (e.g. `qwen3_0.6b`). Guard added: if `project_info.json` names a model whose `code.index` is missing (stale metadata from a partial index), the function falls through to the directory scan rather than returning a stale key.

- **`list_embedding_models` always returned `loaded: false`** (`mcp_server/tools/status_handlers.py`) — two bugs fixed: (1) the `name → model_key` reverse-lookup used the active pool only (2-4 models), forcing `False` for the other 4-6 registry entries regardless of actual VRAM state; (2) `model_key in state.embedders` checked key *presence*, returning `True` for `None` lazy-initialized slots. Now computes `loaded_names = {e.model_name for e in state.embedders.values() if e is not None}` for an accurate live check across all 8 registry models.

### Refactored

- **`GraphScoringStage` extracted from `SearchOrchestrator`** (`search/graph_scoring_stage.py`, new file) — centrality scoring (Block F: `_apply_centrality`), SSCG subgraph extraction (Block G: `_extract_subgraph`), and the k×4 candidate cap are encapsulated in a single `GraphScoringStage.run()` call. `SearchOrchestrator._assemble` is reduced from a 200-line orchestration block to a 3-call sequence. `CentralityRanker._get_centrality_scores` publicised to `get_centrality_scores`.

- **`SearchOrchestrator._assemble` helpers extracted** (`mcp_server/tools/search_orchestrator.py`) — `_apply_source_order_and_budget` (Block H: source-position reorder + context-token budget truncation) and `_build_response` (Block I: response dict assembly + system guidance) extracted as `@staticmethod` decorated definitions. Cyclomatic complexity of `_assemble` reduced from ~30 to ~5.

- **`ServiceLocator` / `ResourceManager` / `SearchFactory` collapsed to module-level accessors** (`mcp_server/services.py`, `mcp_server/resource_manager.py`, `mcp_server/search_factory.py`) — the `ServiceLocator` DI container (a closed auto-registration loop between `state.py` and `services.get_state()`) and the two single-method wrapper classes are deleted. `services.py` is a 2-line re-export shim; methods inlined as module-level functions. Three `ServiceLocator`-first config paths in `chunking/`, `merkle/`, and `search/config.py` collapsed. ADR-0005 recorded (`docs/adr/0005-no-di-container-module-singleton-state.md`).

### Security

- **idna upgraded 3.11 → 3.17** (`pyproject.toml`) — fixes CVE-2026-45409 (incomplete fix of CVE-2024-3651; DoS via crafted Unicode in `idna.encode`). Transitive dependency via `anyio`/`httpx`/`requests`/`yarl`; no direct pin required. 4 advisories remain deferred and documented in `pyproject.toml`.

### Changed

- **`search_config.json`** — new optional config fields (all backward-compatible, existing configs are forward-compatible): `default_max_context_tokens` (0 = unlimited), `ego_graph.edge_weights` (21 relationship-type weights for PPR traversal), `ego_graph.community_bounded` / `cross_community_penalty` / `expansion_mode` / `ppr_alpha` / `min_similarity_threshold`, `parent_retrieval` section (`enabled`, `include_parent_content`, `max_parents_per_result`), `multi_hop.edge_weights`, `graph_enhanced.centrality_bm25_boost` / `centrality_boost_threshold` / `centrality_boost_factor` / `centrality_boost_cap`, `output.source_order_output`.

---

## [0.12.3] - 2026-05-29

### Refactored

- **`chunking↔graph` import cycle eliminated** — 24 files forming a self-contained extraction cluster moved from `graph/` into `chunking/relationships/` (`call_graph_extractor.py`, `relation_filter.py`, `relationship_types.py`, `resolvers/`, `relationship_extractors/`). `git mv` history preserved. Import prefixes updated across 45 source files; `graph/__init__.py` re-exports for backward compatibility. Verified: `rg "^\s*(from|import) graph" chunking/` → 0 results. Remaining dependency direction: `graph → chunking` (architecturally correct).

---

## [0.12.2] - 2026-05-26

### Fixed

- **`IndexWriteStage` bound to stale resources after full reindex** (`search/incremental_indexer.py`) — `IndexWriteStage` and `BM25SyncManager` are now rebuilt via `_build_write_pipeline()` immediately after `_release_and_verify_resources()` reassigns `self.embedder`/`self.indexer`. Previously, successive full-reindex passes could silently embed against a released embedder, report `success=True`, and persist a zero-chunk snapshot.
- **Embedding errors silently swallowed** (`search/index_write_stage.py`) — `run()` now returns `success=False` with the error message when `embed_chunks()` raises; the snapshot is no longer written, preventing a zero-chunk "success" state from corrupting the incremental index.
- **GPU cache not cleared on embedding failure** (`search/index_write_stage.py`) — `_clear_gpu("FULL_INDEX")` is now called before the early-return on embedding failure, preventing VRAM pressure that could cause immediate OOM on the next retry.

### Refactored

- **`GraphIntegration` shared initializer** (`search/graph_integration.py`) — extracted `_setup_from_storage(storage)` called by both `__init__` and `from_storage()`, eliminating drift risk when `__init__` gains new instance attributes.
- **`CommunityDetector` import hoisted to module level** (`search/community_stage.py`) — `ImportError` now surfaces at module load instead of being masked as a "community detection failed" warning. Deferred `LanguageChunker` import annotated with circular-import explanation.
- **`RelationshipEdge`/`RelationshipType` import hoisted to module level** (`search/graph_integration.py`) — removed three per-call inline copies in `add_chunk`, `populate_from_embeddings`, and `build_graph_from_chunks`.

### Changed

- **Embedding model** (`search_config.json`): `Qwen/Qwen3-Embedding-0.6B` (1024-dim) → `Alibaba-NLP/gte-modernbert-base` (768-dim). **Breaking:** existing FAISS indices built at 1024-dim are dimension-incompatible and require a full reindex.
- **Reranker** (`search_config.json`): `Alibaba-NLP/gte-reranker-modernbert-base` → `jinaai/jina-reranker-v3`; `min_vram_gb` 4.0 → 6.0 (VRAM-verified: 1.12 GB / 8 GB on RTX 4060).
- **Routing** (`search_config.json`): `multi_model_enabled` false → true; `multi_model_pool` "full" → "lightweight-speed"; `embedding.batch_size` 128 → 64.

---

## [0.12.1] - 2026-05-25

### Added

- **ANSI color output in MCP server console** (`mcp_server/server.py`) — stage markers print in blue, warnings in yellow, errors in red for easier log scanning.

### Fixed

- **Starlette `redirect_slashes` 307 on POST `/mcp`** (`mcp_server/server.py`) — ASGI wrapper intercepts trailing-slash redirects before Starlette issues a 307, preventing clients from switching to GET and breaking the StreamableHTTP handshake.
- **Call graph edges missing for `split_block` chunks** (`chunking/multi_language_chunker.py`) — added `"split_block"` to the call-extraction allowlist; large methods that are split at AST boundaries now generate call edges for all body fragments.
- **Relationship edges (`uses_type`, `imports`, etc.) missing for `split_block` chunks** (`chunking/multi_language_chunker.py`) — `_extract_phase3_relationships` now restricts extraction to the signature portion (before the `# ... (split block)` marker) and appends `pass` to make it syntactically valid for `ast.parse`. Previously, incomplete body fragments (dangling `else:`/`except:`) triggered a silent `SyntaxError → return []`, leaving all split_block nodes with zero relationship edges in the graph (+584 new edges after re-index).

### Changed

- **`CodeRelationshipAnalyzer` moved to search layer** — business logic extracted from `mcp_server/tools/code_relationship_analyzer.py` (now a backward-compat shim re-exporting `RelationshipAnalyzer`) to `search/relationship_analyzer.py`, with a new `GraphQueryEngine` seam (`graph/graph_queries.py`) and shared types (`search/types.py`).

### Security

- Dependency audit 2026-05-25: `pip ≥ 26.1.1` (CVE-2026-3219, CVE-2026-6357), `pillow ≥ 12.2.0` (CVE-2026-40192, CVE-2026-42308, CVE-2026-42309, CVE-2026-42310, CVE-2026-42311), `python-multipart ≥ 0.0.27` (CVE-2026-42561). Three advisories remain deferred: sqlitedict CVE-2024-35515 (mitigated), transformers 2×RCE (blocked by optimum-onnx pin), starlette host-header injection (low risk).

---

## [0.12.0] - 2026-05-25

### Changed

- **Transport: SSE → StreamableHTTP** (`mcp_server/server.py`) — replaced `SseServerTransport` (two-endpoint: GET `/sse` + POST `/messages/`) with `StreamableHTTPSessionManager(stateless=True, json_response=True)` (single `/mcp` endpoint). Port 8765 unchanged.
- **`--transport` flag**: `sse` → `http`; `scripts/manual_configure.py` now emits `{"type": "http", "url": "http://localhost:8765/mcp"}`.
- **Batch launchers**: `start_mcp_sse.bat` → `start_mcp_http.bat`, `start_mcp_sse_cli.bat` → `start_mcp_http_cli.bat`, `start_both_sse_servers.bat` → `start_both_http_servers.bat`; `start_mcp_debug.bat` updated in-place.
- **Gemini skill health check** (`gemini-skills/.../start_mcp_sse.py`): switched from `GET /sse` HTTP poll to TCP port probe (stateless StreamableHTTP doesn't respond to bare GET).
- **Regression test** (`tests/regression/test_mcp_configuration.ps1`): expects `type == "http"`, URL pattern `http://host:port/mcp`.
- **`start_mcp_server.cmd`**: menu labels, batch file references, help text updated.

### Migration

Update `.claude.json` MCP entry: `{"type": "sse", "url": "...8765/sse"}` → `{"type": "http", "url": "http://localhost:8765/mcp"}`. Re-run `scripts\batch\manual_configure.bat` to apply automatically.

---

## [0.11.10] - 2026-05-25

### Changed

- **Workstation VRAM tier (18 GB+) switched to single-model + reranker mode** (`search/vram_manager.py`) — Qwen3-0.6B (1024d, ~2.5 GB VRAM), `multi_model_enabled=False`, `multi_model_pool=None`. The full 3-model pool (~6.8 GB) was replaced after the jina-v5 / Qwen3-4B experiments revealed no quality uplift over the 0.6B baseline (MRR 0.94). Resolves OOM headroom concerns on 24 GB cards.
- **Default routing model** `bge_m3` → `qwen3_0.6b`; `routing.multi_model_enabled` → `false` in `search_config.json`.

### Fixed

- **Embedding pool key disambiguation** (`mcp_server/model_pool_manager.py`) — pool key renamed `qwen3` → `qwen3_0.6b` (now parameter-specific) to stop the 4B/0.6B query-vs-index 2560d/1024d dimension mismatch.
- **Config `multi_model_enabled:false` now wins over `CLAUDE_MULTI_MODEL_ENABLED` env var** in `sync_from_config` — the env var was overriding an explicit `false` in the JSON config.
- **Configured model not in active pool loads directly as single-model** instead of silently falling back to the first pool key (`mcp_server/model_pool_manager.py`).
- **Auto-reindex loop caused by `search_config.json` mtime changes** — every config read was touching the file's mtime, triggering an immediate re-index on the next request.

### Added

- **Phase-A model-comparison harness** (`scripts/benchmark/compare_models.py` + `compare_models.sh`) — side-by-side SSCG benchmark runner for evaluating multiple embedding models in a single pass. Outputs a leaderboard table with per-query and aggregate MRR, Recall@k, and Hit@k.

### Evaluation / Tests

- **Golden-dataset label corrections** for Q01 (`CodeEmbedder._get_model_config` / `get_model_config` grade-3), Q05 (`utils/path_utils.normalize_path` grade-3), Q19 (`ONNXEmbeddingModel.encode` grade-2); added `recommended_k=7` (`evaluation/golden_dataset.json`).
- **SSCG benchmark re-run at k=7** (hybrid mode): MRR **0.806**, Recall@5 **0.646**, Recall@7 **0.700**, Hit@7 **1.00** (post-label-fix; +0.203 MRR, +0.108 Recall@5 vs the pre-fix k=5 baseline).
- **Model-key test assertions updated** `qwen3` → `qwen3_0.6b` across the unit-test suite.

---

## [0.11.9] - 2026-05-24

### Added

- **Opt-in OTel tracing across search and index pipeline** (`utils/observability.py`, `utils/otel_attributes.py`) — zero-overhead when disabled (one boolean check per `traced_block` call); degrades silently to no-op when the `opentelemetry` package is not installed. Instrumented sites: `@timed` decorator (all 5 existing timing sites gain spans automatically), `error_handler` (emits `mcp.tool.<name>` span per MCP tool call), `incremental_indexer` (`index.full` + `index.incremental` spans), `hybrid_searcher` (`search.hybrid` span with mode/result-count attributes). `init_observability()` reads `ObservabilityConfig` (env: `CLAUDE_OTEL_ENABLED`, `CLAUDE_OTEL_EXPORTER`, `CLAUDE_OTEL_ENDPOINT`); console exporter always routes to **stderr** to avoid corrupting the MCP stdio channel. `wrap_in_context()` propagates the OTel context into worker threads. Install with `pip install -e ".[otel]"`. New docs: `docs/OBSERVABILITY.md`, ADR-0003 (decline LLM hierarchical summaries), ADR-0004 (scoped tracing only). New domain glossary: `CONTEXT.md`.
- **SummaryStage — named, testable extraction of community/file summary orchestration** (`search/summary_stage.py`) — extracts the ~360-line summary section from `_full_index` in `IncrementalIndexer` into a dedicated class that owns the two-phase ordering invariant (centrality + remerge constraint). Behavior is bit-for-bit identical; the class docstring is the single source of truth for the ordering constraint.
- **Incremental community-summary refresh** (`search/incremental_indexer.py`) — closes the gap where incremental runs silently skipped community summary updates. A threshold-hybrid strategy: below `incremental_community_redetect_threshold` (default 0.3 = 30% of indexed files changed), `_refresh_affected_community_summaries` rebuilds only the affected community summary chunks from the persisted `community_map` + `MetadataStore` without re-chunking; above the threshold, the run promotes to a full re-index to redetect community structure. Community summary chunks now carry a `community:N` tag for precise stale-chunk lookup. New `ChunkingConfig` flags: `enable_incremental_community_summaries` (default `True`), `incremental_community_redetect_threshold` (default `0.3`).
- **Persistent file logging** (`mcp_server/server.py`) — replaces bare `basicConfig` with a dual-handler setup: `StreamHandler` for console (existing behavior) + `_SafeRotatingFileHandler` writing to `logs/mcp_server.log` (always DEBUG level, UTF-8, 5 MB rotate). Crash tracebacks and verbose DEBUG output now survive window scroll and are available after the server exits. Backup log files are named `mcp_server_<mmddyyhhmmss>.log` (session-start timestamp, no numeric suffix) so each server run is uniquely identifiable.
- **`utils/console.py` — `get_progress_console()` factory** — returns a `rich.Console` that forces the animated spinner only when stdout is an interactive UTF-8 terminal. Eliminates `UnicodeEncodeError` on Windows when stdout is redirected to a cp1252 stream (e.g. a log file or the MCP stdio channel).

### Fixed

- **`_refresh_affected_community_summaries` TypeError** (`search/incremental_indexer.py`) — a `list` was passed where a `set` was expected during chunk-ID lookup, causing a `TypeError` on every incremental run that had changed files. The error was silently caught and escalated every incremental index into a full re-index.
- **Duplicate `RotatingFileHandler` from `-m` double-import trap** (`mcp_server/server.py`) — running via `python -m mcp_server.server` executed the module body as `__main__`; a subsequent `from mcp_server.server import ...` re-executed the body under the qualified name, attaching a second `RotatingFileHandler` to the root logger. Fixed with an idempotency sentinel (`_code_search_logging_configured`) on the root logger singleton, guarding `_configure_logging()` against repeated execution.
- **`logs/` directory triggered spurious "Modified: 1" on every incremental re-index** (`chunking/language_registry.py`) — the MerkleDAG stat-hashed the growing `mcp_server.log` file, classifying it as modified on each run. Added `"logs"` to `DEFAULT_IGNORED_DIRS`.
- **`WinError 32` log-rotation spam** (`mcp_server/server.py`) — `RotatingFileHandler.rotate()` raised `PermissionError` on Windows when another process held the log file open during rollover, printing `--- Logging error ---` tracebacks to stderr on every log write during an index run. Replaced with `_SafeRotatingFileHandler` whose `rotate()` swallows `PermissionError` / `OSError` via `contextlib.suppress`, allowing log writes to continue uninterrupted.
- **`shutdown_observability()` permanently disabled OTel before indexing** (`mcp_server/resource_manager.py`) — `cleanup_previous_resources()` (called at the start of every `index_directory` request) was invoking `shutdown_observability()`, which calls `TracerProvider.shutdown()`. After shutdown, all subsequent `traced_block` calls produce non-recording no-op spans — making the entire tracing layer a no-op for the duration of indexing. Replaced with `force_flush()` which drains pending spans without permanently disabling the provider. `shutdown_observability()` is now reserved for process-exit teardown only.
- **OTel test isolation when running alongside the e2e test module** (`tests/unit/utils/test_observability.py`, `tests/integration/test_observability_e2e.py`) — OTel ≥ 1.x silently refuses to replace the global `TracerProvider` once set. The e2e module installs its provider at collection time; the unit test's `_enable_with_in_memory()` was then trying to replace it, silently failing, and leaving the unit test's exporter unreachable. Fixed by detecting an already-installed SDK provider and adding the test exporter to it instead of replacing. The e2e `_clear_spans` fixture now also restores `_obs._enabled` and `_obs._tracer_provider` before each test to counteract unit-test teardowns.

### Tests

- 27 tests added across 4 new files:
  - `tests/unit/utils/test_observability.py` (15 tests) — noop path, enabled path with `InMemorySpanExporter`, `wrap_in_context` thread propagation, stdio safety (console exporter → stderr)
  - `tests/integration/test_observability_e2e.py` (7 fast + 2 slow tests) — functional span emission for `@timed`, `error_handler`, `search.hybrid`, thread context propagation; slow tier exercises the real embedding model
  - `tests/unit/search/test_summary_stage.py` (9 tests) — `SummaryStage` extraction correctness
  - `tests/unit/search/test_incremental_community_summaries.py` (10 tests) — community refresh threshold logic, TypeError regression
  - `tests/unit/mcp_server/test_logging_setup.py` (4 tests) — `_configure_logging()` idempotency, `_SafeRotatingFileHandler` resilience under file-lock errors
  - `tests/unit/merkle/test_merkle.py` (+1 test) — `logs/` directory ignored by `MerkleDAG`

---

## [0.11.8] - 2026-05-16

### Fixed

- **`safe_clear_index.py` crash on startup** (`tools/safe_clear_index.py`) — `ModuleNotFoundError: No module named 'graph'` when `start_mcp_server.cmd` invoked the script. Root cause: the editable install (v0.9.3-era) predated `graph` and `utils` being added to `[tool.setuptools.packages.find]`, so the custom editable finder's hard-coded `MAPPING` omitted both packages. Added the `_PROJECT_ROOT / sys.path.insert` bootstrap matching all five sibling tools; refreshed the editable install to v0.11.8 so `graph` and `utils` are now exposed to any Python process using the venv.
- **Silent loss of user-defined index exclusions on re-index** — user-configured `exclude_dirs` were dropped when triggering an incremental re-index via auto-reindex or explicit re-index calls.
- **Config cache bypass** (`search/config.py`) — `save_config()` did not update `_config_mtime` after writing, so `load_config()` never short-circuited to cache on the next call; every read re-parsed the file from disk.
- **`snapshot_manager.py` logging** — replaced bare `print()` calls with structured `logger` output; tightened bare `except` clauses to preserve exception context.
- **Circular graph–search import** — broke a circular import between `graph` and `search` packages that surfaced when importing from a bare `python` process (no editable-install finder active).
- **Pyrefly type suppressions replaced** (`search/`, `graph/`, `mcp_server/`, `utils/`) — 165 `# type: ignore` / pyrefly-suppress comments replaced with correct type annotations across 29 files; pyrefly 1.0 now reports 0 errors on the full codebase (155 pre-existing errors remain suppressed via baseline).

### Added

- **Pyrefly 1.0 type checker integrated** — `pyrefly check` runs as a non-blocking step in the CGW pre-commit hook (`CGW_TYPECHECK_CMD="pyrefly"`). `[tool.pyrefly]` config in `pyproject.toml`; suppress baseline at `.pyrefly_suppress` covers 155 pre-existing errors across 29 files. ADR-0002 records the pyrefly-over-pyright decision.
- **ADR-0001** (`docs/adr/0001-faiss-as-vector-index-backend.md`) — records the FAISS-vs-turbovec evaluation and re-evaluation triggers.
- **ADR-0002** (`docs/adr/0002-pyrefly-over-pyright.md`) — records the static type-checker selection rationale.
- **`utils/path_utils.py`** — shared path-normalisation helpers extracted from scattered inline usage.
- **`cgw.conf.example`** — documents new `CGW_TYPECHECK_*` and `CGW_INDEX_LOCK_*` options added in the latest claude-git-workflow release.

### Refactored

- **`search/config.py`** — migrated from `os.path` to `pathlib` throughout.
- **Silent `except` blocks in critical paths** — added `logger.exception` / `logger.error` with `exc_info=True` to previously-silent exception handlers across `mcp_server/`, `search/`, and `graph/` so errors surface in logs instead of being swallowed.
- **Traceback preservation** (`mcp_server/server.py`) — `except` blocks now pass `exc_info=True`; top-level imports hoisted out of function bodies; pickle trust boundary documented.
- **Lazy imports removed** (`search/incremental_indexer.py`, `embeddings/embedder.py`) — redundant deferred imports converted to module-level imports.

### Tests

- **2,045 unit tests** (up from 2,044 in v0.11.7).
- New integration test: `tests/integration/test_auto_reindex_fixes.py` (166 lines) — covers the index-exclusion loss regression end-to-end.
- New unit tests: `tests/unit/search/test_search_config.py` (+21 tests) — covers `save_config` / `load_config` cache round-trips.

---

## [0.11.7] - 2026-05-03

### Security

- **Defense-in-depth for all destructive filesystem operations** — every `shutil.rmtree` call in the codebase is now gated by layered path-containment guards. Fixes a regression where selecting "0" (Cancel) in the `start_mcp_server.cmd` "Clear Project Indexes" menu could delete project source files instead of cancelling.
- **`validate_storage_path()`** (`mcp_server/storage_manager.py`) — new helper that refuses any `CODE_SEARCH_STORAGE` path that sits inside a project source tree (`.git`, `pyproject.toml`, `Cargo.toml`, etc. as ancestors). Falls back to `~/.claude_code_search` with a logged error rather than raising, keeping the MCP server runnable under misconfiguration.
- **Storage sentinel file** — `get_storage_dir()` now writes `.claude_code_search_storage` on first init. `safe_rmtree_all()` refuses with exit code 6 if the sentinel is absent, and with exit code 7 if the storage directory contains a project marker.
- **`tools/safe_clear_index.py`** (new) — standalone path-safe rmtree helper with `safe_rmtree_project()` (5-guard chain: empty hash, target==root, `relative_to` containment, traversal, underscore presence) and `safe_rmtree_all()` (sentinel + project-marker guards).
- **Cleanup queue re-validation** (`mcp_server/cleanup_queue.py`) — paths read from persisted `cleanup_queue.json` are re-validated against `projects_root` before `rmtree`, preventing a tampered queue from triggering arbitrary deletion at server startup.
- **Index handler assertion** (`mcp_server/tools/index_handlers.py`) — `_clear_index_files_before_create` now asserts the target directory is under the storage root before clearing any files.
- **Snapshot manager** (`merkle/snapshot_manager.py`) — default `storage_dir` is now resolved via `get_storage_dir()` instead of the hardcoded `~/.claude_code_search/merkle` path, so `CODE_SEARCH_STORAGE` is honoured.
- **Cleanup tools** (`tools/cleanup_orphaned_projects.py`, `tools/cleanup_stale_snapshots.py`) — replaced hardcoded `~/.claude_code_search/projects` with `get_storage_dir() / "projects"`.
- **ONNX conversion guard** (`tools/convert_onnx.py`) — `--force` now refuses to `rmtree` directories that lack `*.onnx` / ONNX meta artifacts, preventing accidental deletion of arbitrary user-supplied paths.
- **`scripts/batch/repair_installation.bat`** — destructive operations now route through `safe_clear_index.py`; confirmation prompts changed from `y/N` to `Type YES to confirm`.

### Tests

- 97 new/updated tests across 6 modules: `test_storage_manager_validation.py` (10), `test_safe_clear_index.py` (12), `test_cleanup_queue.py` (4), `test_index_handlers.py` (2), `test_merkle.py` (3).
- All 2,044 unit tests pass.

---

## [0.11.6] - 2026-04-21

### Performance

- **~100-second incremental-index stall eliminated** (`merkle/change_detector.py`, `search/incremental_indexer.py`, `mcp_server/tools/search_handlers.py`) — companion fix to v0.11.5. `ChangeDetector.detect_changes_from_snapshot` and `quick_check` build a fresh `MerkleDAG` on every incremental run and auto-reindex freshness check, but the constructor was called without `supported_extensions`, so it fell back to content-hashing every file — hitting the exact same ~103 s / 1134-file cost the full-index path just got rid of.
  - `ChangeDetector.__init__` now accepts `supported_extensions: set[str] | None` and threads it to both `MerkleDAG(...)` sites. `IncrementalIndexer.__init__` computes the set once from `TreeSitterChunker.get_supported_extensions()` and caches it on `self.supported_extensions` so both the incremental path and `_full_index` reuse it (no more redundant `TreeSitterChunker` import inside `_full_index`). `mcp_server/tools/search_handlers.py` passes the same set when constructing its lightweight `ChangeDetector` for the auto-reindex freshness check.
  - Also fixes a correctness bug: v0.11.5 snapshots stored stat-hashes for non-code files, but the next incremental run's DAG used content-hashes — every non-code file appeared as "modified" (log: `Modified: 1076` out of 1080 unsupported assets). Consistent hashing across snapshot save / incremental compare is now enforced by test `test_incremental_consistent_with_new_scheme_snapshot` in `tests/unit/merkle/test_merkle.py`, which reproduces the failure mode.

### Fixed

- **Snapshot/incremental hash-scheme drift** — see Performance section above. Without the fix, users on v0.11.5 would see every unsupported file classified as "modified" on every incremental run, triggering unnecessary `Batch removing chunks` work for files that have no chunks to remove.

---

## [0.11.5] - 2026-04-21

### Performance

- **~2-minute full-index stall eliminated** (`merkle/merkle_dag.py`, `search/incremental_indexer.py`, `mcp_server/tools/index_handlers.py`) — `MerkleDAG.build()` was SHA-256 content-hashing every file in the project tree before the extension filter ran, which on a 1134-file TouchDesigner project (61 supported code files, 1073 `.tox`/media/binary assets) took ~103 s per model due to Windows Defender on-access scanning and NTFS per-file open overhead (~90 ms/file). The cost doubled for multi-model indexing because each per-model `IncrementalIndexer` rebuilt the DAG from scratch on unchanged files.
  - `MerkleDAG.__init__` now accepts `supported_extensions: set[str] | None`. When provided, files whose suffix is NOT in the set get a cheap stat-based hash (`name:st_size:int(st_mtime)`) instead of a content hash. `stat()` is ~100× cheaper than `open()+read()+close()` on Windows because it bypasses Defender and doesn't touch file contents. Change detection accuracy is preserved: size+mtime is the canonical fast-path signal (same approach used by rsync/git) and is sufficient for files that are never chunked or searched.
  - `IncrementalIndexer.__init__` now accepts `prebuilt_dag: MerkleDAG | None` and exposes the built DAG via `self.built_dag` after `_full_index`. The multi-model loop in `_index_with_all_models` captures the first model's DAG into `cached_dag` and passes it to subsequent models (same pattern already in use for `cached_repo_profile`). The second model's DAG build is skipped entirely.
  - Expected impact: ~103 s/model → ~5 s for the first model, near-instant for each subsequent model. For a two-model pool the total `clear_index` → `Found N supported` window collapses from ~210 s to ~5 s (>95% reduction).

---

## [0.11.4] - 2026-04-21

### Fixed

- **Selection-reset one-liner SyntaxError** (`start_mcp_server.cmd:1037`, new helper `tools/reset_selection_if_orphaned.py`) — the embedded `python -c "..."` call that resets `project_selection.json` after clearing the last index for a path had a Python grammar error: an inline `if` compound statement after `;`-chained simple statements (Python forbids compound statements after `;`). The error was hidden by `2>nul` in earlier commits; `1b818b2` removed the suppression to surface real bugs and correctly exposed this one. Every `Clear Project Indexes` run since that refactor printed a SyntaxError traceback per cleared index, and the reset logic never ran — leaving stale `last_project_path` values in `project_selection.json`. Logic extracted to `tools/reset_selection_if_orphaned.py`: reads `CGW_PROJ_PATH` from env (already set at line 1023), checks selection first (cheap early-exit), short-circuits the projects-dir glob on first matching `project_info.json`. Also drops a latent filter bug where `Path(p.parent.name).exists()` checked a bare hash string against CWD instead of `projects_dir`

---

## [0.11.3] - 2026-04-19

### Added

- **Multi-select in "Clear Project Indexes" menu** (`start_mcp_server.cmd`, label `:clear_project_indexes`) — the prompt now accepts multiple selections separated by commas or spaces (e.g. `1,3`, `1 3`, `1, 3`). Useful when a project has multiple indexed model dimensions (e.g. BGE-M3 1024d + gte-modernbert 768d) that previously required re-entering the menu once per index. Duplicates are deduped (`1,1,3` → `1,3`); invalid tokens are warned about and skipped. Confirmation is `y/N` for a single selection (preserves existing muscle memory) and `YES` for 2+ selections — matched case-insensitively via `if /i`, consistent with the `:clear_all_indices` strong-confirm at line 1094. Sentinels `X` and `0` are honored only as the sole token — mixed inputs like `1,X` or `0,2` are rejected with an error and re-prompt

### Changed

- **Locked-index auto-retry** (`start_mcp_server.cmd`, `:delete_one_index`) — when `shutil.rmtree` fails on a locked index directory, the script now automatically retries once with `ignore_errors=True` after a 2s wait instead of prompting per item. The previous per-item `Try force cleanup? (y/N)` prompt has been removed from the loop path; a single pre-loop "Make sure MCP server is NOT running" warning + netstat check runs once up front. Failed items are accumulated and listed in the post-loop `=== Clear Summary ===` block
- **Per-item delete body extracted to `:delete_one_index` subroutine** — called once per selected index from the outer `for /f` loop. Keeps non-delayed `%PROJECT_HASH%` expansion semantics identical to the pre-refactor single-select path; all four existing Python one-liners (index rmtree, force-retry rmtree, snapshot delete, selection reset) are reused verbatim

### Fixed

- **Multi-failure summary now prints one line per failure** (`start_mcp_server.cmd`, `:clear_project_indexes_summary`) — failures were previously accumulated in a `set` variable, which collapses to a single line because cmd variables cannot contain newlines. Failures are now written to `%TEMP%\mcp_fail_list.txt` (one `echo >> ...` per item) and displayed with `type` in the summary
- **`%PROJECT_PATH%` no longer shell-interpolated into Python raw-string literals** (`start_mcp_server.cmd`, `:delete_one_index`) — paths with apostrophes could terminate the `r'...'` literal and inject arbitrary Python. The two affected one-liners (snapshot delete, selection reset) now receive the path via `os.environ['CGW_PROJ_PATH']`, which is set from `%PROJECT_PATH%` just before each python call and cleared (`set "CGW_PROJ_PATH="`) on `exit /b`
- **`for /f` loops reading temp files now use `usebackq` and quoted paths** (`start_mcp_server.cmd`, `:clear_project_indexes`) — unquoted `%TEMP_PROJECTS%` / `%TEMP_SELECTED%` would silently break if `%TEMP%` contains spaces. Four sites updated to `"usebackq tokens=... delims=|" ... in ("%TEMP_PROJECTS%")` / `in ("%TEMP_SELECTED%")`
- **Auto-retry `LAST_REASON` now attributed accurately** (`start_mcp_server.cmd`, `:delete_one_index`) — the retry path previously reported every first-attempt failure as `locked` in the summary, even when the actual cause was an `rmtree` error on a sub-path. `LAST_REASON` is now set tentatively to `rmtree error` when the first attempt fails and only overwritten to `locked` if the directory still exists after the auto-retry
- **Auto-retry existence check no longer hardcodes `%USERPROFILE%\.claude_code_search`** (`start_mcp_server.cmd`, `:delete_one_index`) — the post-retry `if exist` check used a hardcoded path that ignored any customized `STORAGE_DIR`, which would have produced a false `[OK] Force cleanup successful` when the index actually still existed elsewhere. The check now calls `storage_manager.get_storage_dir()` and propagates the result via `sys.exit(0/1)` → `if errorlevel 1`
- **Duplicate token input no longer double-processes** (`start_mcp_server.cmd`, `:clear_project_indexes`) — the tokenizer produced a deduped `!tokens!` string (bracket-tagged) but the resolver loop still iterated `!project_choice!` (raw input). Input like `1,1,3` wrote index `1` twice to `%TEMP_SELECTED%`, ran deletion twice, inflated `valid_count`, and could incorrectly escalate the single-item `y/N` confirmation to the multi-item `YES` prompt. A new plain `!dedup_choice!` variable is built alongside `!tokens!` and drives the resolver loop

---

## [0.11.2] - 2026-04-19

### Fixed

- **Request-scoped weight overrides no longer race under concurrent search** (`mcp_server/tools/search_handlers.py`, `search/hybrid_searcher.py`, `search/search_executor.py`) — `handle_search_code` previously mutated `searcher.bm25_weight`, `searcher.dense_weight`, and their `SearchExecutor` mirrors before `asyncio.to_thread`; concurrent requests could overwrite each other's intent-driven weights, causing nondeterministic RRF ranking. Weights are now threaded as per-call kwargs from `handle_search_code` → `HybridSearcher.search` → `_single_hop_search` → `SearchExecutor.execute_single_hop` → `RRFReranker.rerank_simple` (which already accepted per-call weights). Instance state is never mutated
- **`SearchConfig` singleton no longer mutated per request** (`mcp_server/tools/search_handlers.py`) — `get_search_config()` returns a cached process-wide singleton; five sites in `handle_search_code` wrote to `search_config.ego_graph`, `search_config.ego_graph.min_similarity_threshold`, `search_config.parent_retrieval`, `search_config.multi_hop.edge_weights`, and `search_config.ego_graph.edge_weights` at request time. The handler now takes a single `copy.deepcopy` of the singleton before any mutations so all per-request changes stay request-local

---

## [0.11.1] - 2026-04-18

### Added

- **`CodeEmbedder.embed_queries_batch(queries)`** (`embeddings/embedder.py:1461-1513`) — batch query embedding in one model forward pass; reuses `_format_query_text` formatting and `embed_chunks` batching machinery. Infrastructure for future coalesced search; not yet wired into the hot path
- **`NeuralReranker.rerank_batch(batch, top_k)`** (`search/neural_reranker.py`) — flattens all `(query, doc)` pairs across N queries into one `CrossEncoder.predict` call, splits results back per-query using offsets. Infrastructure for future batched reranking; not yet wired into the hot path
- **Batched FAISS search** (`search/faiss_index.py`) — `FaissVectorIndex.search()` now accepts `[N, d]` input and returns `[N, k]` output, preserving the batch dimension when N > 1. Adds a `query.copy()` guard before `faiss.normalize_L2` to prevent in-place mutation of caller-owned arrays

### Changed

- **`NeuralReranker.model` lazy-load** (`search/neural_reranker.py`) — now uses double-checked locking with `threading.Lock`. Previously, two concurrent requests on a cold cache could both enter the bare `if self._model is None` branch and instantiate duplicate `CrossEncoder` objects (duplicate VRAM allocation, wasted load latency). Mirrors the existing locking pattern in `JinaRerankerV3`
- **Extracted `_format_query_text(query, model_config)`** (`embeddings/embedder.py`) — replaces a ~40-line instruction-mode formatting ladder that was duplicated between `embed_query` and `embed_queries_batch`. Future `instruction_mode` branches can no longer silently diverge between single-query and batch paths
- **Extracted `_tensor_to_numpy(emb)`** (`embeddings/embedder.py`) — deduplicates the tensor→numpy conversion used at two call sites
- **Extracted `_apply_rerank_score(candidate, score)`** (`search/neural_reranker.py`) — the `original_score`/`reranker_score`/`candidate.score = float(score)` triple previously appeared 5× in the file; now called from both `rerank` and `rerank_batch`

### Fixed

- **`embed_queries_batch` empty-batch shape** (`embeddings/embedder.py`) — empty input now returns `np.empty((0, dim), dtype=float32)` matching the `(N, embedding_dim)` contract; previously returned `(0,)` which would raise `IndexError` on `.shape[1]` or FAISS ingestion
- **Query cache key includes `instruction_mode` and `query_instruction`** (`embeddings/query_cache.py`, `embeddings/embedder.py`) — cache keys in both `embed_query` and `embed_queries_batch` now incorporate these fields; previously a query cached in `"custom"` mode could be returned to a `"prompt_name"` caller with the wrong instruction prepended. `embed_query` and `embed_queries_batch` now share cache entries correctly when called with identical configs
- **Search handlers no longer block the event loop** (`mcp_server/tools/search_handlers.py`) — 5 blocking search calls are now wrapped in `asyncio.to_thread`. Previously, every inbound `search_code` / `find_path` / `find_connections` call held the event loop for the full pipeline (embed → FAISS → BM25 → RRF → neural rerank), serializing N concurrent MCP requests. The GIL-releasing FAISS and CrossEncoder C/CUDA sections now run truly in parallel. (`mcp_server/tools/index_handlers.py` already had its 2 index wraps from commit `2e1e4a2` on main; those are not part of this PR diff)

### Removed

- **`SearchBatchCoordinator`** (`mcp_server/search_coordinator.py`, ~200 lines) — deleted along with `ApplicationState.search_coordinator`, the startup block in `server.py`, and the `concurrency` section of `search_config.json`. The coordinator's batched fast-path always raised `TypeError` (because `HybridSearcher.search` does not accept `query_embedding`), which was silently swallowed by `except Exception` — every request fell through to serial execution. It was pure overhead with zero benefit

---

## [0.11.0] - 2026-04-16

### Added

- **ONNX Runtime backend** (`embeddings/onnx_loader.py`, `embeddings/onnx_wrapper.py`) — opt-in inference path (`performance.use_onnx`) that loads eligible models via `ORTModelForFeatureExtraction` with the `CUDAExecutionProvider`. Auto-converts HuggingFace models to ONNX on first use, caches under `~/.cache/huggingface/hub/onnx/`. Supported pooling strategies: `cls`, `mean` (declared via `onnx_pooling` in `MODEL_REGISTRY`). Backend selection is per-model via `_should_use_onnx()` in `embeddings/model_loader.py`
- **ORT CUDA arena cap** (`performance.onnx_gpu_mem_limit`, default `true`) — constrains ORT's CUDAExecutionProvider memory arena via the `gpu_mem_limit` provider option, using the same effective VRAM cap as the PyTorch `set_per_process_memory_fraction()` path. Prevents WDDM shared-memory spillover on Windows when external processes (browsers, games) hold GPU memory. Check `[ONNX_VRAM]` log lines for the computed cap
- **BFCArena OOM recovery** (`CodeEmbedder.embed_chunks`) — when ORT raises a `BFCArena` OOM, the embedder now halves the dynamic batch size and retries (same flow as PyTorch `torch.cuda.OutOfMemoryError`). Detection uses `isinstance(e, torch.cuda.OutOfMemoryError)` with a string fallback for ORT-specific errors (`"bfcarena"`, `"available memory" + "smaller than requested"`)
- **`onnx_supported` registry flag** — opt-out field on `MODEL_REGISTRY` entries whose upstream pooling is not representable in `onnx_wrapper.py` (currently `cls` / `mean` only). Set on `BAAI/bge-code-v1` (`lasttoken`) to prevent silent semantic drift. Gate lives in `_should_use_onnx()`
- **Per-model activation measurement** (`ModelLoader._measure_activation_per_item`) — Tier-1 runtime measurement of peak VRAM delta per batch item via PyTorch memory stats (torch path) or NVML snapshots (ONNX path). Feeds dynamic batch sizing and replaces hardcoded per-model constants for models without explicit floors

### Changed

- **Default embedding pool: lightweight-speed** — `search_config.json` ships with `routing.multi_model_pool: "lightweight-speed"` (`BAAI/bge-m3` + `Alibaba-NLP/gte-modernbert-base`) and `routing.default_model: "bge_m3"`. Targeted at 8 GB laptop GPUs with zero shared-memory spillover under the ORT cap. Existing users with Qwen3 + BGE-Code indexes must re-index when switching pools
- **Default reranker: `Alibaba-NLP/gte-reranker-modernbert-base`** — replaces `BAAI/bge-reranker-v2-m3` in the default config. Lighter VRAM footprint, comparable quality on the SSCG benchmark
- **dtype-aware activation estimate** (`estimate_activation_gb_from_config`) — reads `config.torch_dtype` and uses 4 bytes for fp32 / 2 bytes for fp16/bf16. Previously hardcoded 2 bytes; fp32 models (rare in embeddings) were 2× under-estimated
- **ORT-aware activation floors** (`MODEL_ACTIVATION_COST_OVERRIDES_ONNX`) — empirically calibrated per-item floors for BGE-M3 (0.28 GB) and GTE-ModernBERT (0.25 GB) prevent Tier-1 warmup undercounting (single-op peaks that warmup batches miss) from causing OOM at real batch sizes
- **`_measure_activation_per_item` accepts `cuda:N`** — previously the device gate only accepted bare `"cuda"`; `cuda:0`/`cuda:1` silently skipped measurement and fell through to lower tiers

### Fixed

- **Duplicated ORT provider-options block** (`embeddings/onnx_loader.py`) — two near-identical 54-line blocks computed the same `provider_options`; only the second reached `from_pretrained` because the first was reset to `None`. The dead block has been removed
- **OOM type detection** (`CodeEmbedder.embed_chunks`) — replaces string-only `"out of memory"` substring check with `isinstance(e, torch.cuda.OutOfMemoryError)` + a dedicated ORT BFCArena string fallback. Non-OOM `RuntimeError`s now propagate correctly without triggering batch halving
- **`validate()` docstring** (`tools/convert_onnx.py`) — previously claimed "max cosine diff < 0.001"; code computes `abs(pt - onnx).max()` on L2-normalised embeddings. Docstring updated to match
- **Narrowed exception tuples** (`CodeEmbedder`) — `(RuntimeError, ValueError, AssertionError, TypeError)` → `(RuntimeError, ValueError, AssertionError)` on paths where `TypeError` would mask real bugs
- **Silent excepts logged at DEBUG** — VRAM-cap re-apply and ORT-cap compute paths previously swallowed errors silently. Now emit a DEBUG log line with the exception type for diagnostics

### Breaking changes

- **`handle_get_memory_status()` field rename**: GPU entries now expose `non_torch_gb` instead of `ort_untracked_gb`. The old name was misleading — the computed value is device-wide NVML usage minus per-process PyTorch allocations, which conflates other processes + drivers + ORT, not just ORT. Any external dashboard or monitor reading the old key will receive `None`

### Security

- **Transitive dependency patch upgrades** (4 CVEs fixed) — `pygments` 2.19.2 → 2.20.0 (CVE-2026-4539, ReDoS in `AdlLexer`), `pyjwt` 2.10.1 → 2.12.0 (CVE-2026-32597, missing `crit` header validation per RFC 7515), `python-multipart` 0.0.22 → 0.0.26 (CVE-2026-40347, DoS via large multipart preamble/epilogue), `requests` 2.32.5 → 2.33.0 (CVE-2026-25645, predictable tempfile name in `extract_zipped_paths()`)
- **Orphan dependency cleanup** — uninstalled `cryptography` (no dependents after `authlib` was removed upstream; eliminated CVE-2026-34073 + CVE-2026-39892), `typer-slim` and `shellingham` (pulled in by unused `mcp[cli]`/`huggingface_hub[mcp]` extras). Venv dropped from 127 → 124 packages; open CVE count dropped from 8 → 2 (remaining: `sqlitedict` CVE-2024-35515 mitigated via JSON serialization in `metadata.py`; `transformers` CVE-2026-1839 blocked by `optimum-onnx <4.58.0` pin)
- **pyproject.toml security-comments block refreshed** — stale `cryptography`/`authlib` references removed; new transitive-dep CVE fixes documented; last-audit date bumped to 2026-04-16

### Tests

- Unit test count: **1,987** (up from 1,985). Additions cover narrowed OOM string fallback propagation, ONNX `cuda:1` device parametrization, and key-rename assertions (`non_torch_gb` present, `ort_untracked_gb` absent)

---

## [0.10.0] - 2026-04-09

### Added

- **Source-position reranking** (`_reorder_by_source_position()` in `search_handlers.py`) — after retrieval, results from the same file are grouped and sorted by start line. Non-contiguous chunks from the same file get `[... N lines omitted ...]` gap indicators. Based on DOS RAG (EMNLP 2025, +5.3% LLM accuracy). Controlled by `OutputConfig.source_order_output` (default: True)
- **Centrality-adaptive BM25 boost** in `CentralityRanker.rerank()` — chunks with PageRank centrality > threshold (0.02) receive additive score boost (`centrality × 5.0`, capped at 0.15). Addresses sign-rank bottleneck for high-connectivity nodes (DeepMind LIMIT paper, ICLR 2026). Tunable via `GraphEnhancedConfig`: `centrality_bm25_boost`, `centrality_boost_threshold`, `centrality_boost_factor`, `centrality_boost_cap`
- **File-role tagging** (`_classify_file_role()` in `multi_language_chunker.py`) — classifies each chunk's file as `role:src`, `role:test`, `role:doc`, or `role:config` at index time. Role-based demotion in `CentralityRanker.rerank()`: test → 0.85×, doc → 0.80×, config → 0.88× (test boosted 1.15× when query has test intent). Source: ConDB filesystem adapter pattern
- **Output & Ranking Enhancements menu** in `start_mcp_server.cmd` (option 8 under Search Configuration) — toggle source-position ordering, enable/disable centrality BM25 boost, tune boost threshold/factor/cap. New settings visible in "View Current Configuration"

### Changed

- **`ChunkingConfig` defaults** — `max_split_chars` 3000→1600 (~400 tokens, Chroma benchmark shows 3-9% better recall), `max_merged_tokens` 1000→400, `enable_large_node_splitting` False→True. Research basis: chunking_evaluation benchmark (Chroma, EMNLP 2024)
- **Documentation aligned** — fixed stale defaults across MCP_TOOLS_REFERENCE, HYBRID_SEARCH_CONFIGURATION_GUIDE, DOCUMENTATION_INDEX (ego_graph k_hops 2→1, max_neighbors 10→5; BM25 weights 0.4/0.6→0.35/0.65; test counts; tool counts)

---

## [0.9.5] - 2026-04-06

### Fixed

- **Installer: dead cu118 torch install** — `install-windows.cmd` was mapping all CUDA 12.x systems to the `cu118` PyTorch index, installing torch 2.7.1 (fails `>=2.8.0` requirement). The manual `uv pip install torch --index-url cu118` step has been removed; `uv sync` now handles PyTorch installation directly from the `cu128` index defined in `pyproject.toml`
- **Installer: dead transformers preview install** — `pip install transformers@v4.56.0-Embedding-Gemma-preview` step removed; EmbeddingGemma is supported in transformers 5.0+ and `uv sync` installs the correct version
- **Installer: hardcoded Python path** — `scripts/powershell/install-windows.ps1` had `C:\Users\Inter\...` hardcoded; replaced with `(Get-Command python).Source` to work on any machine
- **IntentClassifier per-request overhead** — `_load_anchor_config()` was called (YAML parse) on every request due to per-request instantiation; added `@lru_cache` so the file is read once. Anchor embeddings are now shared across instances via module-level `_ANCHOR_EMBEDDINGS_CACHE` keyed by `id(embedder)`, eliminating repeated embedding of ~70 anchor queries
- **`semantic_weight` not validated** — Out-of-range values (config typo, migration bug) could produce negative keyword weight or semantic weight > 1; now clamped to `[0.0, 1.0]` in `__init__`
- **Negative cosine similarity in ensemble** — Cosine similarities in `[-1, 1]` were blended directly with keyword scores `[0, 1]`; negative values now clamped to `0.0` before blending so semantic acts as a boost, not a penalty
- **find_path O(N) graph scan** — Tier-2 name lookup iterated all graph nodes with attribute access; `CodeGraphStorage` now maintains `_name_index: dict[str, list[str]]` populated by `add_node()`, rebuilt by `load()`, cleared by `clear()`; `find_path` handler uses `get_nodes_by_name()` (O(1)) instead
- **find_similar_code score/order inconsistency** — After neural reranking, original `SearchResult` objects were restored in reranked order but kept original `similarity_score`; reranker score now propagated to `metadata["reranker_score"]` so order and scores agree
- **sys.stdout swap not thread-safe** — `JinaRerankerV3._load_model` used a global `sys.stdout` replacement; replaced with `contextlib.redirect_stdout` + per-instance `threading.Lock`
- **Benchmark `--sweep` incompatible with `--compare`** — Sweep output was wrapped as `{"sweep_results": [...]}` but `--compare` expected a flat run object; `compare_runs()` now detects and unwraps sweep files
- **Redundant classification in benchmark Part B** — `test_semantic_intent.py` called `_classify_one()` again in Part B to get `suggested_params` already computed in Part A; params now cached in Part A rows

### Performance

- **Intent classifier** — Anchor YAML parsed once per process (was once per request); anchor embeddings computed once per embedder lifetime (was once per IntentClassifier instance)
- **find_path** — Graph name lookup is now O(1) vs O(N·attrs) for the secondary tier

---

## [0.9.4] - 2026-04-06

### Added

- **Ego-Graph Quick Wins QW1-QW5** - Centrality-based ranking, community-bounded expansion, Personalized PageRank mode, hub node detection, and configurable threshold; 10 new unit tests
- **Max Phantom Degree Cap** - Limits high-fanout phantom nodes in community detection to fix low modularity (modularity 0.24→0.56)
- **Automated SSCG Benchmark Pipeline** - `scripts/benchmark/run_sscg_benchmark.py` with single-run, parameter sweep, and config comparison modes; venv-aware shell wrapper
- **Semantic Intent Classification** - Opt-in anchor-based ensemble scoring for 7 intent types (`local`, `global`, `navigational`, `path_tracing`, `similarity`, `contextual`, `hybrid`); ensemble: `0.7×keyword + 0.3×semantic`
- **Semantic Intent Config Roundtrip** - `semantic_enabled`/`semantic_weight` fields persisted through config save/load cycle; status display in server UI
- **Adaptive Chunking Params in UI** - View Current Configuration and Reset to Defaults panels now show `max_phantom_degree` and adaptive chunking parameters

### Fixed

- **Searcher cache miss** - `get_searcher()` now resolves `project_path=None` to `state.current_project` before cache check; eliminates ~7s Jina reranker reload on every tool call (back-to-back calls now 49× faster: 140ms vs 6856ms)
- **Reranker AttributeError** - `find_similar_code` neural reranking crashed with `'SearchResult' has no attribute 'score'` due to two conflicting `SearchResult` dataclasses; fix converts to `reranker.SearchResult` for the reranking step then restores rich result objects
- **find_path wrong symbol resolution** - Symbol names now resolved via graph exact-name lookup before falling back to semantic search (k=5 with name filtering); `handle_search_code` previously resolved to wrong file
- **VRAM monitor false alarms** - `_check_vram_status()` used `mem_get_info()` (driver-level, includes PyTorch caching allocator reserved blocks) causing permanent 87% warnings; fixed to use `memory_allocated()` / `get_device_properties().total_memory`
- **max_phantom_degree config roundtrip** - Field now correctly persisted through `from_dict`/`to_dict` in `SearchConfig`
- **Qwen3 routing keywords** - Extended keyword list to correctly route FaissVectorIndex queries to qwen3 model

### Security

- Patched nltk CVE-2025-14009 (ReDoS in `punkt` tokenizer)
- Locked `cryptography`, `regex`, and `pip` to CVE-free minimum versions

### Performance

- **Startup optimization** - Fixed 4 startup bugs; added model warm-up to eliminate first-query cold-start latency (Jina reranker pre-loaded)
- **Searcher caching** - Verified: second tool call reuses HybridSearcher + Jina reranker without re-initialization
- **Multi-model indexing** - Deduplicated repo profiler; eliminated redundant profiling when indexing with multiple embedding models simultaneously

---

## [0.9.3] - 2026-02-21

### Added

- **Mandatory Resource Release Before Reindexing** - Ensures all embedding model resources (GPU memory, thread pools) are explicitly released before full reindex starts, preventing VRAM leaks and corruption

### Changed

- **RAM Fallback Enabled** - `allow_ram_fallback: true` in search_config.json for graceful degradation when GPU VRAM is insufficient
- **Public Pool Config API** - Renamed `_get_pool_config` to public API with defensive copy for safer consumption

### Fixed

- Resource cleanup failures at start of full reindex
- Model validation: restored model now verified against active pool before use
- Auto-reindex graph persistence: model_key and routing config preserved across reindex cycles
- Falsy float check in resource manager (was incorrectly treating 0.0 as falsy)
- Misleading log messages and dead code removed from cleanup components
- Broadened exception handling in resource_manager cleanup (was too narrow)
- `model_key=None` guard preventing AttributeError on unset model key
- GPU threshold moved to named constant for maintainability
- pyrefly cross-platform compatibility fix
- Search pipeline optimization: eliminated double HybridSearcher creation and pool config log spam

---

## [0.9.2] - 2026-02-06

### Added

- **Intent Classifier Symbol Detection** - Fallback for noun-only queries (CamelCase, UPPER_CASE, snake_case, dunder methods, dot.notation)
- **CI Agent Review Improvements** - Type-safe enum comparison, documented double-demotion, snake_case regex fix, zero-centrality test coverage

### Changed

- **Documentation-Codebase Alignment** - Fixed 34 discrepancies across 20 files
  - Config defaults aligned: 0.35/0.65 weights (was 0.4/0.6 in 5 code files)
  - Query routing defaults: default_model="qwen3", confidence_threshold=0.35
  - Version bumped: pyproject.toml (0.8.5→0.9.2), all docs updated
  - Removed stale Qwen3-4B references (model replaced with Qwen3-0.6B)
  - Fixed EmbeddingGemma "default" label (still valid for low-VRAM systems)
  - Removed 7 broken analysis/ directory references
  - Updated test count (1,557→1,635+), tool count (18→19 in docstring)
  - Fixed MODEL_POOL_CONFIG docs (show 2 separate pools)
- **Search Quality Regression Fix** - Routing + intent weight fixes (commit b00a366)
- **Query Router Test Updates** - Aligned with new default_model (qwen3) and threshold (0.35)

### Fixed

- Type-safe enum comparison (QueryIntent.GLOBAL vs string comparison)
- Snake_case underscore prefix support in intent classifier regex
- Zero-centrality synthetic chunk demotion (0.5x multiplier) with test coverage
- MCP tool registry docstring (18→19 tools)
- index_directory description (removed false JSX/Svelte support claim)

---

## [0.9.1] - 2026-02-04

### Added

- **Jina v3 Reranker Integration** - 131K context window listwise reranker (jinaai/jina-reranker-v3)
- **QueryEmbeddingCache Thread Safety** - O(1) LRU cache with threading.Lock protection

### Changed

- **Model Pool Optimization** - 2-model configuration
  - Full pool: Qwen3-0.6B (2.3GB) + BGE-Code-v1 (4GB) = ~6.3GB total
  - Lightweight pool: GTE-ModernBERT + BGE-M3
  - Removed Qwen3-4B (7.5GB) in favor of Qwen3-0.6B for better VRAM efficiency
- **VRAM Tier Optimization** - Workstation tier (18GB+) now uses Qwen3-0.6B instead of 4B variant

### Performance

- Query cache O(1) operations with OrderedDict (was O(n) list operations)
- Thread-safe cache operations (get, put, clear, get_stats, size)
- Reranker factory supports both BGE and Jina models

---

## [0.9.0] - 2026-02-01

### Added

- **SSCG Integration (Phases 1-5)** - Structural-Semantic Code Graph based on RepoGraph (ICLR 2025), SOG (USENIX '24), GRACE, Microsoft GraphRAG
  - Phase 1: Subgraph extraction from call graphs
  - Phase 2: 21 relationship types (calls, inherits, imports, uses_type, decorates, raises, catches, instantiates, implements, overrides, assigns_to, reads_from, defines_constant, defines_enum_member, defines_class_attr, defines_field, uses_constant, uses_default, uses_global, asserts_type, uses_context_manager)
  - Phase 3: PageRank centrality scoring with blended reranking (alpha=0.3)
  - Phase 4: Community detection via Louvain algorithm for contextual grouping
  - Phase 5: Ego-graph structure for k-hop expansion with edge-type-weighted BFS
- **A1: Intent-Adaptive Edge Weight Profiles** - 7 query intent categories adjusting graph traversal weights dynamically
- **A2: File-Level Module Summary Chunks** - Synthetic `chunk_type="module"` chunks per file for improved GLOBAL query recall with 3-tier demotion (0.82x/0.85x/0.90x)
- **B1: Community-Level Summary Chunks** - Synthetic `chunk_type="community"` chunks via Louvain detection for GLOBAL query recall with demotion tuning
- **`find_path` tool** (19th MCP tool) - Bidirectional BFS shortest path between code entities with edge type filtering
- **Post-Expansion Neural Reranking** - Second reranking pass after ego-graph expansion for improved precision
- **BM25 Snowball Stemming** - 93.3% queries benefit, 0.47ms overhead (always-on)

### Changed

- **k=4 Standardization** - Default result count changed from k=5 to k=4 (20% token efficiency gain, Recall@4=1.00)
- **`configure_chunking` parameters expanded** - Added `enable_community_detection`, `enable_community_merge`, `community_resolution`, `enable_file_summaries`, `enable_community_summaries`, `split_size_method`, `max_split_chars`
- **chunk_type enum expanded** - Added `"module"` and `"community"` synthetic summary types

### Performance

- **SSCG Benchmark**: Recall@4=1.00 (perfect), MRR=0.81, 9/13 Rank-1 accuracy across 13 scored queries
- **Dependency Cleanup**: 76 packages removed (201→125, 38% reduction), eliminated protobuf CVE-2026-0994, saved ~565MB

---

## [0.8.7] - 2026-01-29

### Added

- **SSCG Phase 1-5 Implementation** - Complete Structural-Semantic Code Graph
  - Edge-type-weighted BFS (SOG-inspired: calls=1.0, imports=0.3)
  - PageRank centrality scoring
  - Community context via Louvain detection
  - P3 relationship extractors

---

## [0.8.6] - 2026-01-16

### Added

- **Performance Instrumentation** - `@timed` decorator and `Timer` context manager for 5 critical search paths
- **Query Embedding Cache** - LRU cache with 300s TTL for <50ms cached query results

---

## [0.8.5] - 2026-01-15

### Changed

- **Chunk Type Enum Expansion** - Added `merged` and `split_block` chunk types for greedy merge and AST splitting

---

## [0.8.4] - 2026-01-06

### Fixed

- **Ultra Format Bug** - Fixed field name rendering issue in ultra output format
- **Field Rename** - Corrected inconsistent field names in output formatter

---

## [0.8.3] - 2026-01-06

### Changed

- **Documentation Cleanup** - Major documentation reorganization
- **CLAUDE.md Restructure** - Streamlined project instructions

---

## [0.8.2] - 2026-01-04

### Added

- **Performance Settings Submenu** - Groups GPU acceleration and Auto-Reindex configuration under one menu
- **Current Settings Display** - Shows active settings when entering each of 12 configuration menus
- **Multi-Model Routing Status** - Visible in both model selection menus with improved labeling
- **Model-Aware Batch Calculation** - Empirical activation memory estimation for optimal batch sizing

### Changed

- Logging tag standardization: All `[save]` tags now uppercase `[SAVE]` for consistency
- Batch size logs now show "128 chunks" instead of ambiguous "128"
- Suppressed INFO logs during Rich progress bars to prevent line mixing
- **BREAKING**: `enable_chunk_merging` default changed from `True` to `False` (opt-in)

### Fixed

- **Auto-Reindex Timeout** - Now respects configured `max_index_age_minutes` (was hardcoded to 5 minutes)
- **Multi-Model VRAM Cleanup** - Properly frees all ~15 GB before reindex (was only ~7.5 GB, caused OOM)
- **Model Loader Preservation** - Fixed AttributeError on lazy reload after cleanup
- **Windows VRAM Spillover** - Hard limit prevents silent overflow to system RAM (97% bandwidth loss)
- **CI Test Failures** - 5 integration tests fixed by changing greedy merge default

### Performance

- VRAM safety: All 3 models (~15 GB) properly released during auto-reindex
- Fail-fast OOM instead of silent spillover to shared memory
- 18% CUDA memory fragmentation overhead now accounted for

---

## [0.8.1] - 2026-01-03

### Added

- `configure_chunking` MCP tool (18th tool) for runtime chunking configuration
- Nested JSON configuration structure (8 sections: embedding, search_mode, etc.)
- Context enhancement parameters in EmbeddingConfig (v0.8.0+)
- UI menu reorganization with hierarchical submenus

### Changed

- `search_config.json` format: flat → nested structure (backward compatible)
- Menu structure: "Search Mode Configuration" and "Entity Tracking Configuration" are now submenus
- Updated documentation to reflect 18 MCP tools

### Fixed

- 4 unit tests updated for nested config structure

---

## [0.8.0] - 2026-01-03

### Added

- **cAST Greedy Sibling Merging (Task 3.5)** - Implementation of EMNLP 2025 chunking algorithm
  - Added 6 chunking configuration fields to `search_config.json`: `enable_chunk_merging`, `min_chunk_tokens`, `max_merged_tokens`, `enable_large_node_splitting`, `max_chunk_lines`, `token_estimation`
  - New `ChunkingConfig` dataclass in `search/config.py` for centralized chunking settings
  - New `estimate_tokens()` function supporting whitespace (fast) and tiktoken (accurate) methods
  - New `_greedy_merge_small_chunks()` algorithm in `chunking/languages/base.py` (67 lines)
  - New `_create_merged_chunk()` helper for combining adjacent small chunks
  - Configuration integration via ServiceLocator dependency injection
  - Files: `search/config.py`, `chunking/languages/base.py`, `chunking/tree_sitter.py`

- **UI Configuration Menu for Chunking** - Interactive chunking settings management
  - New menu option "A. Configure Chunking Settings" in Search Configuration menu
  - 5 sub-options: Enable/Disable greedy merge, Set min/max tokens, Set token estimation method
  - Real-time configuration display showing current settings
  - Helpful descriptions explaining benefits (+4.3 Recall@5 improvement from EMNLP 2025 paper)
  - Integrated with `view_config` to display chunking settings
  - Files: `start_mcp_server.cmd` (lines 351, 376, 1526-1641, 959)

- **Comprehensive Test Suite** - 137 unit tests for greedy merge functionality
  - New `tests/unit/chunking/test_greedy_merge.py` with 4 test classes
  - Tests for token estimation, merged chunk creation, greedy merge algorithm, and integration
  - Coverage: empty lists, single chunks, all small chunks, large chunks, max size limits, parent_class grouping
  - All 137 tests passing with 100% coverage of new chunking features

### Changed

- **Chunking Pipeline Enhancement** - Greedy merge integration into code chunking flow
  - `LanguageChunker.chunk_code()` now accepts optional `ChunkingConfig` parameter
  - Automatic merge of adjacent small chunks when `enable_chunk_merging=True`
  - Config fetched via ServiceLocator if not provided
  - `TreeSitterChunker.chunk_file()` passes config to language chunker
  - Files: `chunking/languages/base.py`, `chunking/tree_sitter.py`

### Performance

- **34% Chunk Reduction** - Exceeded expected 20-30% from EMNLP 2025 paper
  - Before: 1,199 chunks per model
  - After: 789 chunks per model
  - Reduction: 410 fewer chunks (34.2%)
  - Small methods successfully merged (getters, setters, small utilities)
  - Token limits respected (min 50, max 1,000 tokens per merged chunk)
  - Multi-model consistency: All 3 models indexed identically (789 chunks each)

- **Search Quality Maintained** - High relevance scores after chunk reduction
  - Top result scores: 0.85-0.97 (excellent quality)
  - Expected Recall@5 improvement: +4.3% (per EMNLP 2025 academic validation)
  - Merged chunks provide denser semantic context per embedding
  - Multi-model routing functioning correctly (qwen3, bge_m3, coderankembed)

### Documentation

- MCP testing validation confirmed all features operational
- find_connections showing comprehensive dependency graphs
- Entity tracking and import extraction working with merged chunks
- Production-ready for v0.8.0 release

---

## [0.7.5] - 2026-01-03

### Fixed

- **Critical: HybridSearcher.clear_index() Reference Mismatch** - Fixed production bug causing empty search results after force_full=True
  - SearchExecutor and MultiHopSearcher now receive updated index references after clear_index()
  - Previously held stale references to old empty indices after re-indexing
  - Affected all code using IncrementalIndexer.incremental_index(force_full=True)
  - File: `search/hybrid_searcher.py:862-867`

- **Slow Integration Tests** - Fixed 7 failing tests in test_hybrid_search_integration.py
  - Removed unused fixture parameters from TestHybridSearchConfigIntegration tests
  - Updated API calls from `_search_bm25` to `search_executor.search_bm25`
  - Fixed test_error_handling expectations for class-scoped fixtures
  - Fixed test_statistics_and_monitoring search count assertion (accumulates across tests)
  - Test results: 14/14 passed (was 7 failed, 7 passed)
  - File: `tests/slow_integration/test_hybrid_search_integration.py`

---

## [0.7.4] - 2026-01-03

### Fixed

- **RAM Cleanup in Release Resources** - Fixed RAM increasing during VRAM release
  - Removed `.to("cpu")` call in `CodeEmbedder.cleanup()` that was copying 2-5GB model to RAM
  - Legacy PyTorch 1.x workaround no longer needed in PyTorch 2.x
  - Added `gc.collect()` before `empty_cache()` for thorough cleanup
  - Applied same pattern to `NeuralReranker.cleanup()` for consistency
  - Files: `embeddings/embedder.py:794-807`, `search/neural_reranker.py:131-141`

- **Removed Broken Performance Tools Menu** - Removed non-functional menu option
  - Removed "Performance Tools" menu (former option 4) with two broken features
  - Memory Usage Report had undefined `gpu_name` variable bug
  - Auto-Tune Search called non-existent `tools\auto_tune_search.py` (archived)
  - Removed 73 lines of broken code from launcher
  - File: `start_mcp_server.cmd`

### Added

- **Neural Reranker Feature Visibility** - Added Neural Reranking to key documentation
  - Added to `README.md` Highlights section with 5-15% quality improvement metric
  - Added to `start_mcp_server.cmd` Help & Documentation menu Key Features
  - Cross-encoder model (BAAI/bge-reranker-v2-m3) now prominently featured
  - Links to advanced features documentation for detailed configuration
  - Files: `README.md:32`, `start_mcp_server.cmd:1624`

- **Search Configuration Menu Explanations** - Added helpful descriptions to all menu options
  - Each option now includes purpose, benefits, and recommendations
  - Examples: "Hybrid recommended", "faster", "+5-15% quality", "VRAM (BGE-M3/Qwen3)"
  - Improves user experience by clarifying what each setting does
  - File: `start_mcp_server.cmd:343-351`

- **Debug Mode Startup Timing** - Added precise timing measurements for optimization
  - Captures startup timer at server launch with `perf_counter()`
  - Logs completion time at "APPLICATION READY" state
  - Shows total startup duration in debug logs (e.g., "Startup completed in 3.35 seconds")
  - Works for both SSE and stdio transports
  - Only active when `MCP_DEBUG=1` environment variable is set
  - File: `mcp_server/server.py:47, 297-300, 322-325, 501-504`

### Changed

- **Index/Search Workflow Documentation** - Clarified correct MCP tool usage
  - Updated `README.md` Section 2 (Index) to show `/mcp-search` skill requirement
  - Updated `README.md` Section 6 (Search) to remove direct MCP command examples
  - Updated `start_mcp_server.cmd` Quick Start instructions
  - Clarified that users run `/mcp-search` first, then ask Claude naturally
  - Explained that MCP tools like `search_code` are called internally, not as slash commands
  - Files: `README.md:56-81, 122-134`, `start_mcp_server.cmd:1634-1635`

### Documentation

- Complete documentation update across README and launcher UI
- Improved clarity on Neural Reranking feature benefits
- Better user guidance for search configuration options
- Correct workflow for Claude Code integration

---

## [0.7.3] - 2026-01-02

### Added

- **HTTP Config Sync for UI Operations** - Real-time config synchronization between UI and running MCP server
  - New `/reload_config` HTTP endpoint for SSE mode - reloads `search_config.json` without restart
  - New `/switch_project` HTTP endpoint for SSE mode - switches active project in running server
  - New `tools/notify_server.py` helper for HTTP notifications to running server
  - UI batch script now calls notifier after all config changes (search mode, weights, entity tracking, reranker)
  - `tools/switch_project_helper.py` tries HTTP first, falls back to direct call if server not running
  - Server logs all UI operations with `[HTTP CONFIG]` and `[HTTP SWITCH]` prefixes
  - Resolves UI ↔ MCP server state disconnect and missing server logs for UI operations
  - Files: `mcp_server/server.py`, `tools/notify_server.py`, `tools/switch_project_helper.py`, `start_mcp_server.cmd`

- **Server Startup Optimizations** - 100-400ms faster startup, 5-10s faster first search
  - Phase 1: Defer VRAM tier detection (50-200ms savings) - commit f3991cb
    - Moved VRAM detection from `initialize_server_state()` to first `get_embedder()` call
    - Lazy detection in `ModelPoolManager` with tier caching
    - Files: `mcp_server/resource_manager.py`, `mcp_server/model_pool_manager.py`
  - Phase 2: Enable SSE pre-warming by default (5-10s first-search savings) - commit 476895f
    - Changed `MCP_PRELOAD_MODEL` default from `"false"` to `"true"` for SSE mode
    - Embedding model pre-loads during server startup
    - Environment variable override available
    - Files: `mcp_server/server.py`
  - Phase 3: Parallel index loading (50-100ms savings) - commit b40eee1
    - BM25 and dense indices load concurrently using `ThreadPoolExecutor`
    - New `_load_indices_parallel()` method in `HybridSearcher`
    - Files: `search/hybrid_searcher.py`
  - Test coverage: 16 unit tests (100% pass rate)
    - `tests/unit/test_vram_lazy_detection.py` (3 tests)
    - `tests/unit/test_sse_prewarm_default.py` (8 tests)
    - `tests/unit/test_parallel_index_loading.py` (5 tests)

### Fixed

- **Entity Tracking Configuration** - Fixed `enable_entity_tracking` config not being applied during indexing
  - `MultiLanguageChunker` now receives `enable_entity_tracking` parameter from config in all 3 instantiation paths
  - Resolves UI showing "Entity Tracking: Enabled" while indexing logs showed "entity tracking disabled" (9 vs 12 extractors)
  - Root cause: Parameter defaulted to `False` in constructor, config setting was ignored
  - Files: `mcp_server/tools/index_handlers.py:91-94, 296-304, 754-762`

- **Multi-Model State Management** - Fixed `state.current_model_key` not being set after multi-model indexing
  - After `_index_with_all_models()` completes, `state.current_model_key` is now properly set to the restored config default model
  - Resolves issue where `handle_get_index_status()` returned 0 chunks after successful indexing
  - Root cause: Model key mismatch between indexing path and status query path
  - File: `mcp_server/tools/index_handlers.py:374-379`

- **Manual Test Discovery** - Renamed helper functions to prevent pytest discovery
  - Renamed 4 functions in `tests/manual/test_sse_cancellation.py` from `test_*` to `_simulate_*`
  - Prevents pytest from discovering manual testing helpers as unit tests
  - Resolves 4 fixture errors in GitHub Actions CI
  - File: `tests/manual/test_sse_cancellation.py:31-58, 71-106`

---

## [0.7.2] - 2026-01-01

### Added

- **Unit Tests for Protection System** - 15 new tests across 4 test classes
  - `TestReadFileWithTimeout` - File timeout handling (3 tests)
  - `TestCheckVramStatus` - VRAM monitoring (4 tests)
  - `TestParallelChunkerTimeouts` - Chunking timeouts (3 tests)
  - `TestCheckFileAccessibility` - Pre-index checks (5 tests)
  - 100% pass rate
  - Files: `tests/unit/chunking/test_tree_sitter.py`, `tests/unit/embeddings/test_embedder.py`, `tests/unit/search/test_parallel_chunker.py`, `tests/unit/mcp_server/test_index_handlers.py`

- **Test Suite Optimization** - 95.4% runtime reduction for slow integration tests
  - 36 tests across 3 files optimized with class-scoped fixtures
  - Runtime: 338s → 15.46s (20× speedup)
  - Files: `tests/slow_integration/test_full_flow.py`, `test_relationship_extraction_integration.py`, `test_multi_hop_flow.py`

### Fixed

- **SSE Transport Error Protection** - Graceful handling of client disconnections
  - Added `anyio.BrokenResourceError` and `ClosedResourceError` handling
  - Extended Windows socket error handler for SSE streams
  - Added ASGI error filter for cleaner logs
  - Addresses MCP SDK bug #1811 (P1, Open)
  - Files: `mcp_server/server.py`, `mcp_server/tools/decorators.py`

- **6-Layer Indexing Protection System** - Prevents file locks, hangs, and VRAM exhaustion
  - Layer 1: Resource cleanup before re-indexing (`cleanup_previous_resources()`)
  - Layer 2: File read timeout (5s) for locked files
  - Layer 3: PermissionError handling with `[LOCKED]` warnings
  - Layer 4: VRAM monitoring (85% warn, 95% abort with `_check_vram_status()`)
  - Layer 5: Progress timeout (10s/file, 300s total with future cancellation)
  - Layer 6: Pre-index accessibility check (`_check_file_accessibility()`)
  - Files: `chunking/tree_sitter.py`, `embeddings/embedder.py`, `search/parallel_chunker.py`, `mcp_server/tools/index_handlers.py`

- **ImpactReport API Consistency** - All relationship fields now guaranteed in output
  - `find_connections` includes empty fields (`child_classes`, `decorated_by`, etc.)
  - Ensures predictable API contract for clients
  - File: `mcp_server/tools/code_relationship_analyzer.py`

---

## [0.7.1] - 2025-12-27

### Added

- **Release Resources Menu Option** - New 'X' option in MCP launcher (`start_mcp_server.cmd`)
  - Frees GPU memory and cached resources from main menu
  - Calls running SSE server via HTTP `/cleanup` endpoint
  - Clears metadata DB connections, neural reranker, embedders, and CUDA cache
  - Positioned between 'F. Configure Output Format' and '0. Exit'

- **HTTP Cleanup Endpoint** - New `/cleanup` POST endpoint in SSE server
  - Enables external cleanup requests to running server
  - Returns JSON success/error response
  - Logs cleanup operations for debugging

### Fixed

- **Index Validation Bugs** - Resolved 3 issues with index validation and model routing
  - Fixed validation logic for stale indices
  - Corrected model routing edge cases
  - Improved error handling for corrupted indices

- **get_memory_status Cleanup Bug** - Fixed unintended resource cleanup when checking memory status
  - Status check no longer triggers model switches
  - Uses cached index_manager instead of factory method

---

## [0.7.0] - 2025-12-22

### Breaking Changes

- **Output Format Rename** - Renamed MCP output format options for clarity
  - `json` → `verbose` (unchanged behavior)
  - `compact` (unchanged)
  - `toon` → `ultra` (tabular format, maximum compression)
  - Migration: Update any scripts using `output_format="toon"` to `output_format="ultra"`

### Added

- **MCP Output Formatting Optimization** - 30-55% token reduction across all 17 tools
  - 3 format tiers: verbose (baseline), compact (30-40% reduction), ultra (45-55% reduction)
  - Ultra format uses tabular arrays with header-declared fields
  - `_format_note` interpretation hint for agent understanding
  - 100% agent understanding accuracy validated
  - 34 unit tests for output formatter
  - Files: `mcp_server/output_formatter.py`, all tool handlers

- **Memory-Mapped Vector Storage** - <1μs vector access performance
  - Auto-enables at 10,000 vector threshold
  - Fully automatic (no user configuration needed)
  - 10.5 MB total storage for 3 models
  - Files: `search/faiss_index.py`, `search/config.py`

- **Symbol Hash Cache** - O(1) chunk lookups (Phase 2)
  - 97.7% bucket utilization (251/256 buckets)
  - <1ms load/save time
  - File: `search/symbol_hash_cache.py`

- **Entity Tracking System** - Track constants, enums, and default parameters
  - 3 new extractors: ConstantExtractor, EnumMemberExtractor, DefaultParameterExtractor
  - 9 new relationship types (Priority 4: definitions, Priority 5: references)
  - 4 new ImpactReport fields in find_connections
  - 30+ unit tests
  - Files: `graph/relationship_extractors/constant_extractor.py`, `enum_extractor.py`, `default_param_extractor.py`

- **VRAM Tier Management** - Adaptive model selection based on GPU memory
  - 4 tiers: minimal (<6GB), laptop (6-10GB), desktop (10-18GB), workstation (18GB+)
  - Automatic feature enablement (multi-model routing, neural reranking)
  - 42 unit tests for VRAM manager
  - Files: `embeddings/vram_manager.py`, `mcp_server/model_pool_manager.py`

- **Git Automation Logging** - Comprehensive structured logging for all scripts
  - 5 new logging functions in `scripts/git/_common.sh`
  - Timestamps, durations, error counts, summary tables
  - All 10 git scripts enhanced

### Changed

- **Test Suite Reorganization** - 1,054+ tests organized into modules
  - Tests grouped by module: chunking, embeddings, graph, merkle, search, mcp_server
  - Module-by-module execution for reliable results
  - Created automated test runner `tests/run_all_tests.bat`

- **Major Refactoring** (no breaking changes)
  - CodeIndexManager → extracted GraphIntegration + BatchOperations classes
  - CodeEmbedder → extracted ModelLoader + ModelCacheManager + QueryEmbeddingCache
  - HybridSearcher → removed deprecated methods (Tier 1-3)
  - Removed Intent Detection feature (~200 lines dead code)

- **Default Output Format** - Changed from compact to ultra for maximum efficiency

- **Mmap Storage** - Now fully automatic (removed user configuration)

### Fixed

- **WinError 64 in SSE Transport** - Fixed by using uvicorn programmatic API
- **User-Defined Filters Lost After Restart** - Filters now persist correctly
- **Model-Aware Batch Sizing** - Prevents GPU memory swapping on 8GB GPUs
- **CI Test Failures** - Fixed GitHub Actions test dependencies and platform-specific tests
- **MRL Dimension Naming** - Correct Merkle snapshot names for Qwen3-4B (1024d vs 2560d)
- **Entity Tracking Display** - Fixed find_connections output for new relationship types

### Removed

- **Intent Detection Feature** - Removed ~200 lines (48% accuracy = ineffective)
- **Mmap User Configuration** - Now automatic (threshold-based)

---

## [0.6.4] - 2025-12-16

### Added

- **Qwen3 Instruction Tuning** - Code-optimized query instructions for better retrieval
  - Automatically applies: `"Instruct: Retrieve source code implementations matching the query\nQuery: {query}"`
  - Configurable `instruction_mode`: "custom" (code-optimized) vs "prompt_name" (generic)
  - 1-5% retrieval precision improvement (per Qwen3 documentation)
  - Files: `search/config.py`, `embeddings/embedder.py`

- **Matryoshka MRL Support** - Reduces storage 2x with <1.5% quality drop
  - Full dimension 2560 → Truncated to 1024 (same as Qwen3-0.6B)
  - Enabled by default for Qwen3-4B model
  - 50% storage reduction while preserving 4B model quality (36 layers)
  - Configuration: `truncate_dim=1024`, `mrl_dimensions` in MODEL_REGISTRY
  - Files: `search/config.py`, `embeddings/embedder.py`

- **Benchmark Instruction Tool** - Compare instruction modes
  - Script: `tools/benchmark_instructions.py`
  - Validates identical performance between custom and prompt_name modes
  - Files: `tools/benchmark_instructions.py`

### Changed

- Model configuration for Qwen3-0.6B and Qwen3-4B updated with instruction tuning parameters

---

## [0.6.3] - 2025-12-13

### Added

- **Drive-Agnostic Project Path Detection** - Automatic project discovery for external drives
  - Auto-detect relocated projects when drive letters change (F: → E:)
  - Backward compatible dual-hash lookup for existing indices
  - 4 utility functions: `compute_drive_agnostic_hash()`, `compute_legacy_hash()`, `get_effective_filters()`, `normalize_path_filters()`
  - Path relocation status in `list_projects` output
  - 20 new unit tests for drive-agnostic utilities
  - Files: `search/filters.py`, `mcp_server/utils/path_utils.py`, `merkle/snapshot_manager.py`

### Fixed

- **User-Defined Filters Lost After MCP Restart** - Filters now persist across server restarts and re-indexing
  - Root cause: Field name inconsistency (`included_dirs` vs `user_included_dirs`)
  - Fix: Corrected field names in `index_handlers.py` and `incremental_indexer.py`
  - Result: Consistent filter persistence across all models during multi-model indexing
  - Files: `mcp_server/index_handlers.py`, `search/incremental_indexer.py`

- **pip-audit Header Line Handling** - Skip header line in deps-audit slash command
  - Fix: Updated Python paths in deps-audit slash command
  - Files: `.claude/commands/deps-audit.md`

- **Stale Imports in start_mcp_server.cmd** - Fixed get_storage_dir import error
  - Files: `start_mcp_server.cmd`

---

## [0.6.2] - 2025-12-13

### Added

- **VRAM Tier Management** - Adaptive model selection based on available GPU memory
  - 4 VRAM tiers: minimal (<6GB), laptop (6-10GB), desktop (10-18GB), workstation (18GB+)
  - Automatic feature enablement based on tier (multi-model routing, neural reranking)
  - Auto-configuration recommendations via `VRAMTierManager`
  - 42 comprehensive unit tests for VRAM manager
  - Files: `embeddings/vram_manager.py`, `mcp_server/model_pool_manager.py`

- **Benchmark Model Analysis Tool** - Validate model performance
  - Script: `tools/benchmark_models.py`
  - Validates Qwen3-4B: 90% of 8B quality at 2-3x speed
  - Documents neural reranker impact: 5.2% improvement, 30% result changes
  - Archived benchmark results

### Changed

- Model pool manager updated with tier-based configuration
- Production config validated: Qwen3-4B + Neural Reranker ENABLED

### Fixed

- **TTY Auto-Detection for Git Scripts** - Commit enhanced shell script improvements
  - Automatically enables `--non-interactive` and `--skip-md-lint` when no TTY detected
  - Environment variable overrides: `CLAUDE_GIT_NON_INTERACTIVE=1`, `CLAUDE_GIT_SKIP_MD_LINT=1`
  - New `--interactive` flag for forcing prompts in automated contexts
  - Files: `scripts/git/commit_enhanced.sh`

---

## [0.6.1] - 2025-12-03

### Added

- **Progress Bar for Chunking** - Real-time visual feedback during file chunking
  - Shows: `Chunking files... 100% (21/21 files)`
  - Force terminal mode (`Console(force_terminal=True)`) for batch script compatibility
  - Works with both parallel and sequential chunking modes
  - File: `search/incremental_indexer.py`

- **Progress Bar for Embedding** - Progress during longest indexing phase (~15 seconds)
  - Shows: `Embedding... 100% (3/3 batches)`
  - Model warmup prevents log interference
  - File: `embeddings/embedder.py`

- **Model/Dimension Display in Project List** - Clear project identification
  - Format: `claude-context-local [bge-m3 1024d]`
  - Disambiguates duplicate project names with different models
  - File: `start_mcp_server.cmd`

- **Targeted Snapshot Deletion** - New `delete_snapshot_by_slug()` method
  - Only deletes matching model/dimension snapshot
  - Preserves other model variants (e.g., keeps `coderank_768d` when deleting `bge-m3_1024d`)
  - File: `merkle/snapshot_manager.py`

### Fixed

- **include_dirs Filter Root Directory Bug** - Fixed 0 files found when using `include_dirs`
  - Root cause: Root directory `"."` was incorrectly filtered, blocking tree traversal
  - Fix: Added root directory exception in `merkle/merkle_dag.py:141`
  - Result: `include_dirs` filter now works correctly for all directories

- **Snapshot Deletion Logic** - Fixed clearing one model's index deleting ALL model snapshots
  - Root cause: `delete_all_snapshots()` used glob pattern matching all dimensions
  - Fix: Created targeted `delete_snapshot_by_slug()` method
  - Result: Clearing specific model index preserves other model indices

- **Display Bug in Clear Index** - Fixed unescaped parenthesis causing spurious error messages
  - Root cause: Unescaped `)` in batch script ended if block prematurely
  - Fix: Removed parenthetical text from echo statement
  - Result: Clean output when clearing indices

- **Progress Bar Terminal Compatibility** - Fixed progress bar not rendering in batch scripts
  - Root cause: Rich Console auto-detection failed in batch environment
  - Fix: Added `Console(force_terminal=True)` and `transient=False`
  - Result: Progress bars display correctly in all environments

- **Model Loading Interference** - Fixed model loading logs interleaving with progress bar
  - Root cause: Model first load triggers verbose transformers logging
  - Fix: Added model warmup (`self.model.encode(["warmup"], show_progress_bar=False)`) before progress bar starts
  - Result: Clean progress bar display without log interference

---

## [0.6.0] - 2025-11-28

### Added

- **Self-Healing BM25 Sync** - Automatic BM25/Dense index synchronization
  - Auto-detects desync exceeding 10% threshold during incremental indexing
  - Rebuilds BM25 from dense index metadata automatically
  - New method: `HybridSearcher.resync_bm25_from_dense()`
  - New result fields: `bm25_resynced`, `bm25_resync_count`

- **Persistent Project Selection** - Project choice survives server restarts
  - New `mcp_server/project_persistence.py` - Save/load selection to JSON
  - New `scripts/get_current_project.py` - Display helper for batch menu
  - Server startup restores last project automatically (stdio + SSE)
  - MCP tools and batch menu stay synchronized bidirectionally
  - Storage: `~/.claude_code_search/project_selection.json`
  - Menu now displays current project in Runtime Status section

### Fixed

- **Git Workflow Scripts** - Critical bug fix for C: drive scanning issue
  - Root cause: Git Bash interpreted `find /c` as Unix find command → full C: drive scan → infinite hang
  - Fix: All scripts now use explicit Windows tool paths: `"%WINDIR%\System32\find.exe"` and `"%WINDIR%\System32\findstr.exe"`
  - Performance: commit_enhanced.bat now completes in 6.8s (was: infinite hang)
  - Affected scripts: commit_enhanced.bat, merge_with_validation.bat, validate_branches.bat, cherry_pick_commits.bat, merge_docs.bat
  - Commits: `273e821`, `d6f5a70`

- **cherry_pick_commits.bat** - Fixed delayed expansion bug in backup tag creation
  - Changed `git tag %BACKUP_TAG%` → `git tag "!BACKUP_TAG!"`
  - Backup tags now created correctly with timestamp format: `pre-cherry-pick-YYYYMMDD_HHMMSS`

### Changed

- **All Batch Scripts** - Comprehensive BATCH_STYLE_GUIDE.md compliance (56 violations fixed across 15 files)
  - Quoted variable assignments: `set VAR=value` → `set "VAR=value"` (prevents trailing spaces per Guide 1.1)
  - Files updated:
    - `start_mcp_server.cmd` (27 violations) - Main launcher with search configuration
    - `install-windows.cmd` (10 violations) - Installation script
    - `verify-hf-auth.cmd` (1 violation) - HuggingFace authentication check
    - `verify-installation.cmd` (2 violations) - Installation verification
    - `scripts/batch/repair_installation.bat` (2 violations) - Repair utility
    - `scripts/batch/start_both_sse_servers.bat` (4 violations) - Dual SSE launcher
    - `scripts/batch/start_mcp_debug.bat` (5 violations) - Debug mode launcher
    - `scripts/batch/start_mcp_simple.bat` (2 violations) - Simple mode launcher
    - `scripts/batch/start_mcp_sse.bat` (3 violations) - SSE transport launcher
  - Ensures consistency with project coding standards and prevents variable contamination

- **Git Workflow Scripts** - Applied BATCH_STYLE_GUIDE.md compliance across all 8 scripts
  - Quoted variable assignments: `set "VAR=value"` (prevents trailing spaces)
  - Project root navigation with error handling: `pushd "%~dp0..\.." || exit /b 1`
  - Safe argument handling: `set "ARG=%~1"` with quote stripping
  - Proper cleanup: `popd` at all exit points
  - Unix command replacements: `head -1` → Batch loop, `wmic` → PowerShell `Get-Date`
  - Added comments with guide references for maintainability

- **Graph Module Refactoring (Phase 7.1)** - Extracted resolvers from call_graph_extractor.py
  - Created `graph/resolvers/` directory with 3 resolver classes:
    - `TypeResolver` (~130 lines) - Type annotation extraction and parsing
    - `AssignmentTracker` (~115 lines) - Local variable assignment tracking
    - `ImportResolver` (~100 lines) - Import statement extraction with caching
  - Reduced `call_graph_extractor.py` from 732 to ~400 lines
  - Updated unit tests to use resolver classes directly
  - All 87 unit + integration tests passing
  - **No re-indexing required** - internal refactoring only

- **Multi-Hop Search Refactoring (Phase 4.2)** - Extracted 3 helper methods from `_multi_hop_search_internal`
  - `_validate_multi_hop_params()` - Parameter validation (~27 lines)
  - `_expand_from_initial_results()` - Hop expansion logic (~70 lines)
  - `_apply_post_expansion_filters()` - Post-expansion filtering (~38 lines)
  - Main method reduced from 197 to ~100 lines (orchestrator pattern)
  - All 40 hybrid/multi-hop tests passing
  - **No re-indexing required** - internal refactoring only

- **Tree-Sitter Chunker Refactoring (Phase 4.1)** - Split `tree_sitter.py` into modular language files
  - Created `chunking/languages/` package with 10 files:
    - `base.py` - TreeSitterChunk dataclass + LanguageChunker ABC
    - `python.py`, `javascript.py`, `typescript.py`, `go.py`, `rust.py`
    - `c.py`, `cpp.py`, `csharp.py`, `glsl.py`
  - Reduced `tree_sitter.py` from 1,154 to 275 lines (-76%)
  - Removed deprecated languages: Svelte, Java, JSX (kept 9 languages)
  - Backwards-compatible: chunkers support both direct and factory instantiation
  - All 11 tree_sitter tests passing
  - **No re-indexing required** - internal refactoring only

---

## [0.5.15] - 2025-11-19

### Added

- **Phase 4: Import-Based Resolution** - Complete call graph resolution system (~90% accuracy)
  - Import tracking: `from x import Y; y = Y(); y.method()` → `Y.method`
  - Alias resolution: `from x import Y as Z` → resolves Z to Y
  - Relative imports: `from . import helper` → `.helper`
  - File-level import caching for performance
  - New methods: `_extract_imports()`, `_read_file_imports()`
  - **Re-indexing required** for projects indexed before this version

- **Comprehensive Test Suite** - 37 new tests for Phase 4
  - Unit tests: 26 tests in `tests/unit/test_import_resolution.py`
  - Integration tests: 11 tests in `tests/integration/test_import_resolution_integration.py`
  - All 126 tests passing (100% success rate)

### Changed

- **Call Graph Resolution Accuracy** - Improved from ~85% to ~90%
  - Complete resolution priority chain: self/super > annotations > assignments > imports
  - Qualified chunk_ids for methods: `"file.py:1-10:method:ClassName.method"`

### Documentation

- Updated ADVANCED_FEATURES_GUIDE.md with Phase 4 section
- Updated MCP_TOOLS_REFERENCE.md with ~90% accuracy claims
- Updated VERSION_HISTORY.md with v0.5.15 entry
- Updated CLAUDE.md to version 0.5.15

---

## [0.5.14] - 2025-11-19

### Added

- **Phase 3: Assignment Tracking** - Local variable type inference
  - Tracks constructor assignments: `result = MyClass()` → type is `MyClass`
  - Resolves subsequent calls: `result.method()` → `MyClass.method`
  - Supports walrus operator (named expressions)
  - 27 unit tests for assignment tracking

---

## [0.5.13] - 2025-11-19

### Added

- **Phase 2: Type Annotation Resolution** - Parameter type inference
  - Resolves type-annotated parameters: `def foo(client: HttpClient):`
  - Tracks calls through annotations: `client.get()` → `HttpClient.get`
  - 16 unit tests for type annotation resolution

---

## [0.5.12] - 2025-11-19

### Added

- **Phase 1: Self/Super Resolution** - Method context inference
  - Resolves `self.method()` calls to `ClassName.method`
  - Resolves `super().method()` calls to parent class
  - Qualified chunk_ids for methods with class context
  - 19 unit tests for self/super resolution

---

## [0.5.11] - 2025-11-18

### Fixed

- **Priority 2 Relationships** - Type annotation and decorator extractors
- **Path Normalization** - Consistent path handling across Windows/Linux

---

## [0.5.8-0.5.10] - 2025-11-18

### Fixed

- Various bug fixes and stability improvements
- Git workflow enhancements
- Documentation updates

---

## [0.5.7] - 2025-11-18

### Fixed

- **Multi-hop Filter Propagation** - Filters now apply to both initial and expanded results
  - **Root cause**: Multi-hop expansion (Hop 2+) called `find_similar_to_chunk` without passing filters
  - **Fix**: Added post-expansion filtering in `search/hybrid_searcher.py:725-744`
  - **Result**: `file_pattern` and `chunk_type` filters work correctly across all hops

- **find_similar_code Path Variant Lookup** - Fixed 0 results bug for path-based queries
  - **Root cause**: Strict path matching failed when chunk_id used different separators
  - **Fix**: Added path variant lookup in `search/indexer.py:542-555`
  - **Result**: `find_similar_code()` now finds chunks regardless of path format

- **Query Routing Confidence Calculation** - Better scoring for natural language queries
  - **Root cause**: Old calculation did not account for keyword weights properly
  - **Fix**: New calculation in `search/query_router.py:275-279`
  - **Result**: Natural queries trigger routing more effectively

- **Dual SSE Server Verification Timing** - Fixed false negatives in server startup checks
  - **Root cause**: 3-second timeout too short for server initialization
  - **Fix**: Increased timeout to 5 seconds in `scripts/batch/start_both_sse_servers.bat:92`

- **Parse Error Logging** - Suppressed verbose parse errors to DEBUG level
  - **Files**: Type/import/inheritance extractors in `graph/relationship_extractors/`
  - **Result**: Cleaner logs during normal operation

- **Phase 3 Relationship Extraction** - All semantic chunk types now contribute to relationship graphs
  - Extended indexer to allow classes, structs, interfaces, enums, traits, impl blocks, constants, variables
  - Fixed HybridSearcher graph access path in `code_relationship_analyzer.py`
  - `find_connections()` now returns complete relationship data
  - **Re-indexing required** for projects indexed before this fix

### Changed

- **Default Search Mode** - Changed from `semantic` to `hybrid` for better filter hit rate
  - BM25 keyword matching improves filter results compared to semantic-only

- **Query Routing Keywords** - Expanded keyword variants for better routing
  - Added: async, await, vector, matrix and other domain-specific terms

- **Codebase Cleanup** - 26 files archived (38% reduction)
  - Moved deprecated/backup files to `_archive/` directories

- **Tool Count** - Updated from 14 to 15 MCP tools
  - Added `find_connections` tool for dependency analysis

### Added

- **Filter Best Practices Documentation** - Post-filtering behavior explained
  - Added to: `docs/MCP_TOOLS_REFERENCE.md`, `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`

- **Phase 1 Features Documentation** - Complete user-facing documentation
  - Symbol ID lookups, AI Guidance messages, Dependency analysis
  - File: `docs/ADVANCED_FEATURES_GUIDE.md`

- **MCP Tools Test Plan** - 55 test queries across 6 categories

---

## [0.5.6] - 2025-11-17

### Fixed

- **Phase 3 Relationship Extraction - Complete Graph Type Coverage** - All semantic chunk types now contribute to relationship graphs
  - Extended indexer to allow classes, structs, interfaces, enums, traits, impl blocks, constants, variables
  - Fixed HybridSearcher graph access path in `code_relationship_analyzer.py`
  - `find_connections()` now returns complete relationship data
  - **Re-indexing required** for projects indexed before this fix

### Fixed

- **Phase 3 Relationship Extraction - Complete Graph Type Coverage** - All semantic chunk types now contribute to relationship graphs
  - **Root cause 1**: Graph was limited to functions/methods only in `search/indexer.py:902-931`
  - **Root cause 2**: HybridSearcher graph access path incorrect in `code_relationship_analyzer.py:74-94`
  - **Fix 1**: Extended indexer to allow classes, structs, interfaces, enums, traits, impl blocks, constants, variables
  - **Fix 2**: Changed graph access from `searcher.graph_storage` to `searcher.dense_index.graph_storage`
  - **Result**: `find_connections()` now returns complete relationship data:
    - `parent_classes` / `child_classes` - Inheritance relationships
    - `uses_types` / `used_as_type_in` - Type annotation relationships
    - `imports` / `imported_by` - Import relationships
  - **Re-indexing required**: Projects indexed before this fix need re-indexing for Phase 3 relationships to populate
  - **Backward compatibility**: Zero breaking changes, graceful degradation if relationships unavailable

---

## [0.5.5] - 2025-11-13

### Added

- **GPU Memory Logging** - Comprehensive VRAM tracking during model loading
  - Added `_log_gpu_memory(stage)` method in `embeddings/embedder.py`
  - Logs allocation/reserved/total at BEFORE_LOAD, AFTER_LOAD, AFTER_FALLBACK_LOAD stages
  - Per-GPU device tracking with detailed metrics (Allocated GB, Reserved GB, Total GB, Usage %)
  - Helps debug memory issues and optimize multi-model loading (3 models = 5.3GB total VRAM)
  - Example: `[GPU_0] AFTER_LOAD: Allocated=4.85GB, Reserved=5.12GB, Total=22.49GB (21.6% used)`
  - File: `embeddings/embedder.py` lines 114-134

- **Multi-Hop Search Performance Timing** - Detailed timing breakdown for search operations
  - Added comprehensive timing tracker in `search/hybrid_searcher.py`
  - Tracks: Hop1, Expansion (per hop), Rerank, Total timing
  - Performance metrics: Cold searches 1.7-3.7s, cached 17-117ms (60-140x faster)
  - Example: `[MULTI_HOP] Complete: 10 results | Total=117ms (Hop1=85ms, Expansion=18ms, Rerank=14ms)`
  - Helps identify bottlenecks and validate caching effectiveness
  - File: `search/hybrid_searcher.py` timing implementation

### Changed

- **Path Standardization** - Unified path handling across codebase
  - Replaced `os.path.expanduser()` with `Path.home() / ".cache" / "huggingface" / "hub"`
  - Improved cross-platform compatibility (Windows/Linux/macOS)
  - Cleaner, more maintainable code using pathlib.Path
  - File: `embeddings/embedder.py` line 52

- **SSE Transport Configuration** - Simplified to single server mode
  - Removed dual SSE server option (ports 8765 + 8766)
  - Single SSE server on port 8765 only
  - Updated `start_mcp_server.cmd` menu: Option 2 now "Single Server (port 8765)"
  - Updated global Claude Code config (`C:/Users/Inter/.claude.json`) to single server
  - Removed `code-search-cli` server entry (port 8766)
  - Cleaner architecture, simpler deployment

- **MCP Tools Documentation** - Enhanced clarity for users and Claude Code integration
  - Updated tool count: 13 → 14 tools (confirmed `configure_query_routing` included)
  - Enhanced parameter descriptions with defaults and required markers
  - Added complete parameter lists for all tools in `docs/MCP_TOOLS_REFERENCE.md`
  - Updated `README.md` with new feature sections (GPU logging, timing, paths)
  - All documentation now accurately reflects current system state

- **MCP Server Architecture** - Migrated from FastMCP to Official Anthropic Low-Level MCP SDK
  - **Production-grade reliability**: Official Anthropic SDK implementation (`mcp_server/server.py`, 720 lines)
  - **Transport options**: SSE via Starlette + uvicorn (port 8765) + stdio
  - **Application lifecycle management**: Eliminates project_id=None bugs completely (100% fix)
  - **SSE race condition prevention**: Guaranteed initialization order via Starlette app_lifespan (100% fix)
  - **All 6 launch modes verified**: stdio, SSE single, SSE dual, debug modes all working
  - **Backward compatibility**: Zero breaking changes, FastMCP backup preserved (`server_fastmcp_v1.py`)

- **Query Routing Enhancements** (2025-11-15) - Natural language query support without keyword stuffing
  - **Lowered confidence threshold**: 0.10 → 0.05 (more sensitive routing for natural queries)
  - **Expanded keyword variants**: Added 24 single-word keywords across all 3 models
    - CodeRankEmbed: Added "binary", "graph", "fuse", "combine"
    - Qwen3: Added "implementing", "implements", "algorithms", "function", "method", "class", "search", "searching", "query", "iterative", "recursive", "code", "coding", "write", "create", "build"
    - BGE-M3: Added "flow", "initialize", "configure", "load", "generate", "connect", "integrate"
  - **Natural queries now work**: Simple phrases like "error handling", "configuration loading", "merkle tree" trigger routing effectively
  - **Verified model switching**: All 3 models (qwen3, bge_m3, coderankembed) physically load to GPU and switch correctly
  - **File modified**: `search/query_router.py` (threshold + keyword expansion)

### Fixed

- **Windows Batch Launcher** - Removed broken single SSE server option
  - **Root cause**: Single SSE server mode (Option 2) caused crashes in Windows batch environment
  - **Fix**: Simplified SSE transport menu to stdio + dual SSE only
  - **File modified**: `start_mcp_server.cmd` (enhanced SSE transport options documentation)

### Testing

- **100% test success rate**: 19/19 unit tests + 1/1 integration test passing
- **14/14 MCP tools fully operational**: All tools verified working with low-level SDK
- **Natural query validation**: 9/9 natural language queries successfully routed (confidence 0.057-0.357)

### Performance

- **No routing overhead regression**: Natural query support maintains <1ms routing overhead
- **Model switching verified**: Physical GPU loading confirmed via server logs for all 3 models

---

## [0.5.4] - 2025-11-10

### Added

- **Multi-Model Query Routing System** - Intelligent automatic model selection based on query characteristics
  - Automatic routing to optimal embedding model (Qwen3-0.6B, BGE-M3, or CodeRankEmbed)
  - 100% routing accuracy on 8 ground truth verification queries
  - Keyword-based routing with confidence scoring (threshold: 0.10, aggressive for optimal coverage)
  - Model specializations based on empirical verification:
    - **Qwen3-0.6B** (3/8 wins): Implementation-heavy queries, algorithms, complete systems
      - Example queries: "error handling patterns", "BM25 index implementation", "multi-hop search algorithm"
    - **BGE-M3** (3/8 wins): Workflow queries, configuration, system plumbing (most consistent baseline)
      - Example queries: "configuration loading system", "incremental indexing logic", "embedding generation workflow"
    - **CodeRankEmbed** (2/8 wins): Specialized algorithms with high precision
      - Example queries: "Merkle tree change detection", "hybrid search RRF reranking"
  - Memory efficient: Only 5.3 GB VRAM for all 3 models simultaneously (20.5% of RTX 4090, 79.5% headroom)
  - Lazy loading: Models load on-demand to minimize memory footprint
  - User control via `use_routing` parameter and model_key override in `search_code()`
  - Expected quality improvement: 15-25% better top-1 relevance for diverse queries vs single-model
  - Model pool architecture with proper cleanup via `_cleanup_previous_resources()`

- **Routing Metadata Transparency** - Every search result now shows which model processed the query
  - `search_code()` ALWAYS returns routing metadata in results (even when routing disabled)
  - Metadata includes:
    - `model_selected`: Which model processed the query (e.g., "qwen3", "bge_m3", "coderankembed")
    - `confidence`: Routing confidence score (0.0 when routing disabled)
    - `reason`: Human-readable explanation of why this model was selected
    - `scores`: Confidence scores for all available models
  - Benefits: Better debugging, user transparency, consistent API response structure
  - Works in all modes: routing enabled, routing disabled, manual model override

### Fixed

- **CRITICAL: CodeRankEmbed Loading Performance** - 52% faster model loading (2.1s → 1.0s)
  - **Root cause**: Models with `trust_remote_code=True` ignore `cache_folder` parameter in SentenceTransformer
  - **Symptom**: Auto-recovery loop on every load caused unnecessary cache deletion and re-download
  - **Fix**: Dual cache location checking in `embeddings/embedder.py`
    - Check custom cache location first: `~/.claude_code_search/models/`
    - Fallback to default HuggingFace cache: `~/.cache/huggingface/hub/`
    - Enhanced `_validate_model_cache()` with `_get_default_hf_cache_path()` and `_check_cache_at_location()` helpers
  - **Impact**: Eliminates auto-recovery overhead, 52% faster loading, better user experience
  - **Implementation**: Lines 628-941 in `embeddings/embedder.py`

- **Routing Metadata Missing When Routing Disabled** - Fixed transparency gap
  - **Root cause**: `routing_info` was `None` when `use_routing=False`, breaking user visibility
  - **Fix**: Always populate routing_info dict even when routing disabled
  - **Impact**: Users always know which model processed their query (defaults to "bge_m3")
  - **Implementation**: Lines 488-506 in `mcp_server/server.py`

### Performance

- **VRAM Efficiency**: All 3 models use only 5.3 GB / 25.8 GB on RTX 4090 (20.5% utilization)
- **Routing Overhead**: <1ms per query (negligible impact on search latency)
- **Model Load Time**: ~5 seconds total for all 3 models (from cache, first load only)
- **Search Quality**: +15-25% improvement in top-1 relevance for implementation/specialized queries
- **Verified Cleanup**: `_cleanup_previous_resources()` properly unloads models and frees VRAM (0.0 GB after cleanup)

### Testing

- **Integration Tests**: 5/5 tests passing (100% success rate)
  - Basic search with routing
  - Manual model override
  - Routing disabled (default model)
  - CodeRankEmbed cache behavior
  - All 8 verification queries
- **Cleanup Verification**: Dedicated test confirms model lifecycle management works correctly
  - VRAM drops to 0.0 GB after cleanup
  - Model pool dictionary clears completely
  - GPU cache properly freed
- **Comprehensive Documentation**: Full verification report in `analysis/mcp_multi_model_verification_report.md`

---

## [0.5.3] - 2025-11-07

### Added

- **Dual-Server SSE Transport** - Run VSCode Extension and Native CLI servers simultaneously
  - Two SSE server instances on different ports sharing indexed projects
    - VSCode Extension: `http://localhost:8765/sse`
    - Native CLI: `http://localhost:8766/sse`
  - Launch options:
    - Quick Start: `start_mcp_server.bat` → Quick Start Server → Option 3
    - Dedicated launcher: `scripts\batch\start_both_sse_servers.bat`
  - Both servers run in separate console windows with clean logging
  - Zero configuration changes required - servers share `~/.claude_code_search/` storage
  - Enables simultaneous usage from both VSCode Extension and Native CLI

- **Graph-Enhanced Search (Phase 1)** - Call relationship tracking for code navigation
  - Python AST-based call graph extraction with NetworkX storage
  - Optional `"graph"` field in `search_code()` results containing:
    - `calls`: Array of function names this code calls
    - `called_by`: Array of function names that call this code
  - Automatic graph population during indexing when `project_id` provided
  - Example result format:

    ```json
    {
      "chunk_id": "auth.py:10-25:function:authenticate_user",
      "graph": {
        "calls": ["validate_credentials", "create_session"],
        "called_by": ["login_handler", "refresh_token"]
      }
    }
    ```

  - Performance: <5% indexing overhead, ~24MB storage for typical projects
  - 50+ unit tests + 7 integration tests passing
  - **Re-indexing required**: Projects indexed before 2025-11-06 need re-indexing for graph data

### Fixed

- **[Windows] SSE Transport Socket Errors (WinError 64)** - Eliminated "network name is no longer available" errors
  - **Root cause**: Windows ProactorEventLoop bug where socket errors during TCP handshake close listening socket instead of just the connection
  - **Impact**: Caused "OSError: [WinError 64] The specified network name is no longer available" warnings during client disconnections
  - **Solution**: Windows-specific SelectorEventLoop configuration for SSE transport
  - **Implementation**: Platform detection before SSE server startup (`mcp_server/server.py:1186-1191`)
  - **Testing**: Validated with 15+ rapid MCP commands, zero errors over extended monitoring
  - **Result**: Clean server logs, stable operation, graceful client disconnection handling
  - **Cross-platform**: Fix only applies to Windows; other platforms unaffected

- **CRITICAL: Double-Encoded JSON in MCP Tool Responses** - All 13 MCP tools now return human-readable dict objects
  - **Root cause**: Tools returned `-> str` with `json.dumps()` calls, causing FastMCP to double-encode JSON strings
  - **Impact**: All MCP tool output was escaped and unreadable (e.g., `"{\"query\":\"...\"}"`instead of proper JSON)
  - **Solution**: AST-based transformation to change all return types `-> str` → `-> Dict` and remove `json.dumps()` calls
  - **Changes**: Modified `mcp_server/server.py` (13 function signatures, 37 return statements)
  - **Implementation**: Used `astor` library for safe AST transformation preserving all code logic
  - **Testing**: All 13 tools validated (100% pass rate) - output now properly formatted and human-readable
  - **Tools affected**: search_code, index_directory, find_similar_code, get_index_status, list_projects, switch_project, clear_index, get_memory_status, cleanup_resources, configure_search_mode, get_search_config_status, list_embedding_models, switch_embedding_model
  - **Backward compatibility**: Zero API changes for users, FastMCP handles serialization automatically
  - **Benefits**: Terminal output clean, structured, and properly formatted for both human and machine consumption
  - **Files modified**: `mcp_server/server.py` (442 insertions, 911 deletions - includes formatting changes from AST transformation)

- **CRITICAL: Graph Metadata Missing from MCP Search Results** - Phase 1 call graph feature now operational
  - **Root cause**: `CodeIndexManager` initialized without `project_id` parameter in `HybridSearcher` (hybrid mode) and `get_index_manager()` (dense-only mode)
  - **Impact**: ALL projects indexed via MCP server (both hybrid and dense-only modes) had graph storage disabled
  - **Fix 1**: Added `project_id` parameter to `HybridSearcher.__init__()` (`search/hybrid_searcher.py:70`)
  - **Fix 2**: Pass `project_id` to `CodeIndexManager` in `HybridSearcher` (`search/hybrid_searcher.py:137`)
  - **Fix 3**: Generate and pass `project_id` in `index_directory()` for hybrid mode (`mcp_server/server.py:213-223`)
  - **Fix 4**: Added `project_id` generation in `get_index_manager()` for dense-only mode (`mcp_server/server.py:246-253`)
  - **Fix 5**: Changed truthiness check to explicit `is not None` for graph_storage (`mcp_server/server.py:445`)
  - **Consequence**: Existing projects require re-indexing to populate graph data
  - **Detection**: Search results now include `"graph"` field with `calls`/`called_by` arrays (Python only)
  - **Backward compatibility**: Zero breaking changes (project_id parameter optional, graph field optional)
  - **Testing**: 50+ unit tests + 7 integration tests for graph extraction already passing
  - **Validation**: Comprehensive testing with 8 diverse queries across both indexed projects confirmed operational

- **FastMCP Port Configuration** - Server now correctly respects `--port` CLI argument
  - **Root cause**: Using `mcp.server.fastmcp.FastMCP` from MCP SDK, which requires port/host in constructor, not `run()` method
  - **Fix**: Added early argument parsing before FastMCP instantiation (`mcp_server/server.py:36-51`)
  - **Result**: Port configuration now works correctly for both single and dual-server modes

- **Batch File Menu Navigation** - Fixed Project Management menu access
  - **Root cause**: Nested if/else block in `:start_server_sse` section corrupted batch parser state
  - **Fix**: Replaced nested if/else with early-exit pattern using `goto` (`start_mcp_server.bat:169-173`)
  - **Result**: All menu navigation now works correctly

### Changed

- **SSE Transport Documentation** - Updated to distinguish single vs dual-server modes
  - Single-server mode now labeled "VSCode Extension OR Native CLI (exclusive use)"
  - Dual-server mode clearly labeled for simultaneous VSCode + CLI usage
  - Updated in: `CLAUDE.md`, `README.md`, `docs/INSTALLATION_GUIDE.md`

- **MCP Server Logging** - Removed verbose debug output for cleaner terminal display
  - Removed `MCP_DEBUG=1` from `scripts/batch/start_mcp_sse.bat`
  - Both servers (8765, 8766) now show clean, professional output

### Performance

- **Graph Storage**: <5% overhead during indexing, ~24MB storage for typical projects
- **Dual-Server**: Minimal resource overhead - two server processes share same index storage

---

## [0.4.0] - 2025-10-03

### Added

- **Git Workflow Automation System** (9 scripts total)
  - `.gitattributes` with merge strategies (ours, union, diff3) for dual-branch workflow
  - Core Scripts: `merge_with_validation.bat`, `validate_branches.bat`, `rollback_merge.bat`
  - Helper Scripts: `merge_docs.bat`, `cherry_pick_commits.bat`, `commit_enhanced.bat`, `check_lint.bat`, `fix_lint.bat`, `install_hooks.bat`
  - Automated branch synchronization with .gitattributes support
  - Pre-merge validation and rollback capabilities

- **GitHub Actions Workflows** (5 workflows)
  - `branch-protection.yml` - Automated CI/CD validation, testing, linting on every push
  - `merge-development-to-main.yml` - Manual merge workflow with .gitattributes support
  - `docs-validation.yml` - Documentation quality checks (markdown lint, link checking, spelling)
  - `claude.yml` - Interactive @claude mentions in GitHub issues/PRs (OAuth-based authentication)
  - `claude-code-review.yml` - Automated code review workflow

- **Claude Code GitHub Integration**
  - Custom command templates in `.claude/commands/` directory
  - `create-pr.md` - Automated PR creation with clean, professional formatting
  - `run-merge.md` - Guided merge workflow with validation and rollback support
  - `validate-changes.md` - Pre-commit validation checklist (blocks local-only files, validates conventional commits)
  - Interactive AI assistance via @claude mentions in GitHub issues and pull requests

- **Per-Model Index Storage** (0.4.0 major feature)
  - Instant model switching (<150ms) with 98% time reduction (50-90s → <1s)
  - Dimension-based storage isolation (768d for Gemma, 1024d for BGE-M3)
  - Independent Merkle snapshots per model dimension
  - Zero re-indexing overhead when switching back to previously used models
  - Storage format: `{project}_{hash}_{dimension}d/` directories

- **Enhanced MCP Configuration**
  - Python-based manual configuration fallback for improved reliability
  - Automatic detection and handling of Claude CLI failures
  - Path verification and validation system
  - Cross-directory compatibility with wrapper scripts

### Changed

- **Documentation Structure**: `docs/GIT_WORKFLOW.md` moved to development-only (internal workflow guide)
- **Configuration Scripts**: Migrated from PowerShell to Python for better cross-platform reliability
- **MCP Server Setup**: Added automatic fallback mechanisms when Claude CLI fails
- **README.md**: Updated architecture section with Git scripts and GitHub Actions workflows
- **Installation Guide**: Added GitHub Actions integration section
- **Development-Only File Protection**: Expanded .gitignore and .gitattributes rules

### Fixed

- **MCP Configuration**: Enhanced path validation and error handling
- **Branch Synchronization**: Improved status reporting in sync scripts
- **Variable Initialization**: Fixed variable scoping issues in batch scripts

---

## [0.3.0] - 2025-09-29

### Added

- **CHANGELOG.md**: Comprehensive change tracking following Keep a Changelog format
- **GIT_WORKFLOW.md**: Complete Git workflow documentation with versioning guidance
  - Semantic versioning strategy (MAJOR.MINOR.PATCH)
  - Release workflow steps
  - CHANGELOG maintenance guidelines

### Changed

- **Documentation Accuracy**: Corrected token efficiency metrics across all documentation
  - Token reduction: 99.9% → 98.6% (accurate measured value)
  - Tokens saved: 20,667 → 89,531 (actual benchmark results)
  - Efficiency ratio: 1000x → 71x (realistic multiplier)
  - Test scenarios: 3 → 7 (expanded test coverage)
  - Search quality metrics updated: Precision 0.611, Recall 0.500, F1-Score 0.533
- **Benchmark Documentation**: Updated `docs/BENCHMARKS.md` with accurate metrics (12 sections)
- **README.md**: Corrected token efficiency claims (4 locations)
- **Evaluation README**: Updated framework documentation (3 locations)
- **Installation Guide**: Corrected expected benchmark results
- **MCP Server Docstring**: Updated tool description with accurate metrics
- **Version Bump**: 0.2.0 → 0.3.0

### Fixed

- **Evaluation Consistency**: Verified all evaluators use identical calculation methods from `BaseEvaluator`
- **Documentation Conflicts**: Removed outdated `Git_Workflow_Strategy.md` to eliminate contradictions

### Removed

- **Outdated Documentation**: Deleted `docs/Git_Workflow_Strategy.md` (contradicted current .gitignore setup)

---

## [0.2.0] - 2025-09-28

### Added

- **Auto-Tuning System**: Parameter optimization tool for hybrid search weights (`tools/auto_tune_search.py`)
  - Tests multiple BM25/Dense weight configurations (0.3/0.7, 0.4/0.6, 0.6/0.4)
  - Uses F1-score as primary metric with query time as tie-breaker
  - Generates optimization reports with recommended configurations
  - Results saved to `benchmark_results/tuning/`
- **Debug Scenarios Dataset**: 7 diverse test scenarios for evaluation (`evaluation/datasets/debug_scenarios.json`)
- **Parameter Optimizer Module**: Core auto-tuning logic (`evaluation/parameter_optimizer.py`)

### Changed

- **Benchmark System**: Enhanced run_benchmarks.bat with auto-tuning option
- **Evaluation Framework**: Added method-comparison mode for testing all search methods
- **Version Bump**: 0.1.0 → 0.2.0

### Fixed

- **Model Loading Overhead**: Fixed first query timing issue in auto-tuning by passing pre-created embedder
- **Search Method Comparison**: Improved benchmark comparison reporting

---

## [0.1.0] - 2025-01-27

### Added

- **Multi-Language Support**: 22 file extensions across 11 programming languages
  - Python (AST-based parsing)
  - JavaScript, TypeScript, JSX, TSX (tree-sitter)
  - Java, Go, Rust, C, C++, C#, Svelte (tree-sitter)
  - GLSL shaders (.glsl, .frag, .vert, .comp, .geom, .tesc, .tese)
- **Hybrid Search System**: BM25 + semantic search with RRF (Reciprocal Rank Fusion)
  - Configurable weights (default: BM25 0.4, Dense 0.6)
  - Parallel query execution
  - Three search modes: hybrid, BM25-only, semantic-only
- **MCP Server Integration**: 10 semantic search tools for Claude Code
  - `index_directory()` - Project indexing
  - `search_code()` - Natural language code search
  - `find_similar_code()` - Alternative implementation discovery
  - Memory management and project switching tools
- **Token Efficiency Evaluator**: Benchmark system measuring token savings vs traditional file reading
- **Windows-Optimized Installation**:
  - `install-windows.bat` - One-click setup
  - `verify-installation.bat` - Comprehensive validation
  - CUDA auto-detection and PyTorch installation
  - HuggingFace authentication handling
- **Comprehensive Test Suite**:
  - 184+ unit tests (tests/unit/)
  - 23+ integration tests (tests/integration/)
  - All tests passing with robust mocking
- **Benchmarking System**:
  - `run_benchmarks.bat` - Interactive benchmark menu
  - Token efficiency evaluation
  - Search method comparison
  - Performance validation
- **Git Workflow Documentation**: Local-first privacy model with automated scripts
  - `.gitignore` protection for development files
  - `scripts/git/commit.bat` - Safe committing
  - `scripts/git/sync_branches.bat` - Branch synchronization

### Changed

- **Project Rename**: Claude-context-MCP → claude-context-local
- **Test Organization**: Reorganized from root to unit/integration subdirectories
- **Branch Strategy**: Dual-branch workflow (development for internal, main for public)
- **Documentation Structure**: Professional organization with comprehensive guides

### Fixed

- **Hybrid Search Integration**: Fixed BM25 + semantic search fusion
- **Semantic Search Mode**: Corrected method name issues
- **Branch Synchronization**: Resolved development/main branch conflicts
- **Test Failures**: Fixed all 184 unit tests and integration tests
- **HuggingFace Authentication**: Robust handling with retry logic

---

## [0.5.6] - 2025-11-17

### Fixed

- **Phase 3 Relationship Extraction - Complete Graph Type Coverage** - All semantic chunk types now contribute to relationship graphs
  - Extended indexer to allow classes, structs, interfaces, enums, traits, impl blocks, constants, variables
  - Fixed HybridSearcher graph access path in `code_relationship_analyzer.py`
  - `find_connections()` now returns complete relationship data
  - **Re-indexing required** for projects indexed before this fix

### Planned Features

- Real-world usage pattern analysis
- Expanded language support
- Interactive evaluation dashboard
- CI/CD pipeline integration
- SWE-bench evaluation completion

---

## Version History

- **v0.9.0** - SSCG Integration, A1/A2/B1 features, k=4 standardization, dependency cleanup (2026-02-01)
- **v0.8.7** - SSCG Phase 1-5 complete (2026-01-29)
- **v0.8.6** - Performance instrumentation, query cache (2026-01-16)
- **v0.8.5** - Chunk type enum expansion (2026-01-15)
- **v0.8.4** - Ultra format bug fix & field rename (2026-01-06)
- **v0.8.3** - Documentation cleanup & CLAUDE.md restructure (2026-01-06)
- **v0.7.2** - Reliability improvements: SSE protection, 6-layer indexing protection (2026-01-01)
- **v0.7.1** - Bug fixes: Release Resources option, index validation, memory status (2025-12-27)
- **v0.7.0** - Major release: Output formatting, mmap storage, entity tracking, refactoring (2025-12-22)
- **v0.6.1** - UX Improvements: Progress bars, filter fixes, targeted snapshot deletion (2025-12-03)
- **v0.6.0** - Release: Self-healing BM25, persistent projects, batch compliance (2025-11-28)
- **v0.5.16** - Graph Resolver Extraction, persistent project selection, multi-hop refactoring (2025-11-24)
- **v0.5.15** - Phase 4: Import-Based Resolution (~90% accuracy) (2025-11-19)
- **v0.5.14** - Phase 3: Assignment Tracking (2025-11-19)
- **v0.5.13** - Phase 2: Type Annotation Resolution (2025-11-19)
- **v0.5.12** - Phase 1: Self/Super Resolution (2025-11-19)
- **v0.5.11** - Priority 2 relationships + path normalization (2025-11-18)
- **v0.5.7** - Bug fixes, performance improvements & documentation (2025-11-18)
- **v0.5.6** - Phase 3 complete type coverage (2025-11-17)
- **v0.5.5** - Low-level MCP SDK migration, natural query routing support (2025-11-13)
- **v0.5.4** - Multi-model query routing system (2025-11-10)
- **v0.5.3** - Graph-enhanced search Phase 1, dual-server SSE transport, critical bug fixes (2025-11-07)
- **v0.5.2** - Multi-hop search, BM25 stemming, comprehensive validation (2025-10-23)
- **v0.5.1** - Configurable batch sizes, site-packages exclusion, Merkle cleanup (2025-10-19)
- **v0.5.0** - SSE transport, batch removal optimization, enhanced project management (2025-10-18)
- **v0.4.1** - Critical bug fix: find_similar_code, MCP tools cleanup (2025-10-05)
- **v0.4.0** - Git automation, GitHub Actions, instant model switching (2025-10-03)
- **v0.3.0** - Documentation accuracy & workflow consolidation (2025-09-29)
- **v0.2.0** - Auto-tuning parameter optimization (2025-09-28)
- **v0.1.0** - Initial release with hybrid search (2025-01-27)

---

## Links

- **Repository**: <https://github.com/forkni/claude-context-local>
- **Documentation**: See `docs/` directory
- **Issue Tracker**: <https://github.com/forkni/claude-context-local/issues>
