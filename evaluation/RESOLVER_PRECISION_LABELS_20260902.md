# Resolver Precision Labels — 2026-09-02

Hand-labels for the 40 rows in `evaluation/resolver_precision_sample.json`
(`"label": null` on all of them — see
`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md` B4 and
`evaluation/RESOLVER_TIER_CALIBRATION_20260902.md` §11). Positive-only tracer
witnessing can't answer these — every row here is an *unwitnessed but
covered* static edge, so the only way to know whether it's a true or false
positive is to read the actual source.

**Method.** For each row, resolved the caller symbol with plain `ast`
(scratch script `tmp/gather_precision_evidence.py`, read-only, no index/GPU/
DB), then read the caller's full body/decorators/imports by hand to answer
one question: *does the caller's body really reach the declared callee?*
Constructions (`Callee(...)`) count as reaching a `class:`/`decorated_definition:`
callee — this matches the ground truth's own `canonical_callee` collapsing
`C.__init__` into `class:C` (`evaluation/tracer/scoring.py:77-82`). Aliased
imports and decorators count. Docstring/comment-only mentions do not.

**Rule pinned by review (2026-09-03).** "Really can call" is read strictly:
an edge is true only if the caller's body executes a call or construction of
the callee. Enum-member access (`Enum.MEMBER`), type annotations, `Protocol`
references, and `self.<attr>` reads that pyan resolves to the binding
`__init__` are **false** — none of them invokes anything a tracer could
witness, and `init_equivalence` only equates `C.__init__` with `class:C`, not
attribute access. Non-call dependencies are already captured by the separate
`uses_type` (6,545) and `uses_constant` (454) relationship edges, so a
0.75-confidence `calls` edge to an enum is misleading in `find_connections`.
Indirect reachability through third-party code does not count either (row 11).

**Review outcome (2026-09-03).** Row 11 flipped true → false (the claimed
OTel chain does not exist — see the row). Rows 21/26/29 resolved false under
the pinned rule. All other labels stand; the reasons for rows 6, 9, 22, 23 and
28 were rewritten because the original text misdiagnosed the mechanism (see
"Systemic finding" at the end).

**Status:** reviewed and decided 2026-09-03 (see "Decisions" below); the
labels in this file are final and match `evaluation/resolver_precision_labels.json`.

---

## LSP tier (rows 0–9, declared confidence 0.98)

| # | Caller → Callee | Evidence | Label | Reason |
|---|---|---|---|---|
| 0 | `collect_symbol_summary` → `class:SymbolSummary` | `chunking/file_summarizer.py:76` `return SymbolSummary(classes, functions, methods, all_imports, docstring_lines)` | **true** | direct construction |
| 1 | `_LspClient.close` → `_kill_process_tree` | `lsp_call_graph.py:403` `_kill_process_tree(self._proc, self._logger)` in the `TimeoutExpired` fallback branch | **true** | direct call |
| 2 | `paths_for` → `decorated_definition:IndexPaths` | `evaluation/index_locator.py:125` `return IndexPaths(...)` | **true** | direct construction |
| 3 | `get_searcher` → `build_hybrid_searcher` | `mcp_server/search_factory.py:194` (region) direct call | **true** | direct call |
| 4 | `SearchConfig.__init__` → `decorated_definition:MultiHopConfig` | `search/config.py:1972` `self.multi_hop = multi_hop if multi_hop is not None else MultiHopConfig()` | **true** | direct construction |
| 5 | `GraphView.in_edges` → `decorated_definition:EdgeRecord` | `search/graph_view.py:189` `EdgeRecord(...)` constructed | **true** | direct construction |
| 6 | `HybridSearcher.index_documents` → `class:CodeIndexManager` | `search/hybrid_searcher.py:624` `self.dense_index.add_embeddings(...)`. The stored edge's `line` is `search/indexer.py:181` = `def add_embeddings` — basedpyright resolved the **right method**. That method exists in the index only as `split_block` chunks (`indexer.py:182-217/218-240/241-281:split_block:CodeIndexManager.add_embeddings`), which `build_line_to_chunk_map` excludes (`evaluation/chunk_mapping.py:50-53`), so `find_enclosing_chunk` fell through to the enclosing `class:` chunk | **false** | real call, wrong callee id — `split_block` callee collapsed to its class; a chunk-mapping defect, not a resolver miss |
| 7 | `IndexSynchronizer.clear_index` → `CodeIndexManager.preflight_clear` | `search/index_sync.py:319` `self.dense_index.preflight_clear()`; `dense_index: CodeIndexManager` (ctor param, line 28); method confirmed at `search/indexer.py:821` | **true** | direct attribute call, receiver type confirmed |
| 8 | `CodeIndexManager.get_similar_chunks` → `CodeIndexManager.search` | `search/indexer.py` `self.search(embedding, search_k)` (own-class method call) | **true** | direct call |
| 9 | `RerankingEngine._run_rerank` → `class:GenerativeReranker` | `search/reranking_engine.py:242` `self.neural_reranker.rerank(...)`; `neural_reranker` is a union of reranker classes (lines 62-67). The stored edge's `line` is `search/neural_reranker.py:619` = `def rerank` of `GenerativeReranker` (a sibling edge to `JinaRerankerV3` points at line 1095, its `rerank`). Both `rerank` bodies exist only as `split_block` chunks, so the callee collapsed to the class exactly as in row 6 | **false** | real call, wrong callee id — same `split_block` collapse as row 6 |

**LSP: 8/10 true, p̂ = 0.80.** Both false rows are the same defect and it is
**not in the resolver**: basedpyright returned the correct method, and the
post-processing line→chunk lookup collapsed it to the enclosing class because
long methods are stored as `split_block` chunks that the line map omits. In the
stored graph 63 of 304 LSP edges whose target is a `class:` chunk carry a `line`
inside the class body rather than at the `class` statement — the same
signature. LSP's true precision is therefore understated by this sample; fixing
the mapping (follow-up below) is a prerequisite for a fair LSP estimate.

---

## LibCST tier (rows 10–19, declared confidence 0.90)

| # | Caller → Callee | Evidence | Label | Reason |
|---|---|---|---|---|
| 10 | `MultiLanguageChunker._init_thread_extractors` → `decorated_definition:ExtractorContext` | `chunking/multi_language_chunker.py:~198` `ctx = ExtractorContext(relation_filter=self.relation_filter)` | **true** | direct construction |
| 11 | `_cleanup_previous_resources` → `_NoopExporter.force_flush` | `mcp_server/resource_manager.py:97-99` calls the **module-level** `force_flush()` (`utils/observability.py:90`). The claimed 2-hop OTel chain does not exist: `TracerProvider.force_flush` → `SimpleSpanProcessor.force_flush` just `return True` (`sdk/trace/export/__init__.py:141-143`), and `BatchSpanProcessor` delegates to `_shared_internal`, which only ever calls `exporter.export(` (line 182) — the SDK never invokes an exporter's `force_flush`. The libcst edge is a `chunk_id_from_fqn` suffix-name collision: same file, same bare name, method chosen over the module function. The correct edge (`→ function:force_flush`) is already present via pyan | **false** | wrong callee — same-file same-name collision in `chunk_id_from_fqn`; flipped from true on review 2026-09-03 |
| 12 | `get_searcher` → `validate_embedder_index_compatibility` | `mcp_server/search_factory.py:186` direct call (imported line 144) | **true** | direct call |
| 13 | `handle_configure_reranking` → `get_config_manager` | `mcp_server/tools/config_handlers.py:295` `config_manager = get_config_manager()` | **true** | direct call |
| 14 | `handle_clear_index` → `error_handler` | `mcp_server/tools/index_handlers.py:405` `@error_handler("Clear index")` decorator | **true** | decorator reference |
| 15 | `handle_find_connections` → `error` | `mcp_server/tools/search_handlers.py:347` `return responses.error(...)` | **true** | direct call |
| 16 | `SearchOrchestrator.run` → `decorated_definition:handle_find_similar_code` | `mcp_server/tools/search_orchestrator.py:709` `return await handle_find_similar_code(...)` | **true** | direct call |
| 17 | `FaissVectorIndex.create` → `class:IndexError` | `search/faiss_index.py:15` `from search.exceptions import IndexError as SearchIndexError`, raised at line 189 as `SearchIndexError(...)` | **true** | aliased import — same class, renamed to dodge the builtin name |
| 18 | `GraphIntegration.add_chunk` → `decorated_definition:RelationshipEdge` | `search/graph_integration.py` `edge = RelationshipEdge(source_id=..., target_name=..., relationship_type=...)` | **true** | direct construction |
| 19 | `IncrementalIndexer.__init__` → `class:CodeEmbedder` | `search/incremental_indexer.py:96` `self.embedder = embedder or CodeEmbedder()` | **true** | direct construction |

**LibCST: 9/10 true, p̂ = 0.90.** The one false row is an FQN→chunk mapping
collision, not a libcst resolution error.

---

## pyan tier (rows 20–29, declared confidence 0.75) — the B4 tier

| # | Caller → Callee | Evidence | Label | Reason |
|---|---|---|---|---|
| 20 | `generate_file_summaries` → `decorated_definition:CodeChunk` | `chunking/file_summarizer.py:22-42` (full body) — only type annotations (`list["CodeChunk"]`, `dict[str, list[CodeChunk]]`); delegates to `_build_file_summary(...)`, a *different* function, which does the actual construction | **false** | wrong caller — construction is one call-hop deeper |
| 21 | `ContextManagerExtractor.__init__` → `class:RelationshipType` | `context_manager_extractor.py:57` `self.relationship_type = RelationshipType.USES_CONTEXT_MANAGER` | **false** | enum-member access, no call or construction (rule pinned 2026-09-03) |
| 22 | `CodeEmbedder.cleanup` → `class:ModelLoader` | `embeddings/embedder.py:1572-1637` (full body) — never names `ModelLoader`; touches `self._model_loader = None` (line 1624). The stored edge's `line` is `embeddings/model_loader.py:327` = `def load`: pyan followed the `self._model_loader` attribute to `ModelLoader.load`, and that method exists only as `split_block` chunks (328-619), so it collapsed to the class. `cleanup` never calls `load` | **false** | attribute-flow false positive, plus the `split_block` collapse of rows 6/9 |
| 23 | `CodeGraphStorage.clear` → `class:CodeGraphStorage` | `graph/graph_storage.py:1121-1134` (full body) — reads `self.graph` / `self._name_index` / `self.storage_path`. The **raw** stored edge targets `method:CodeGraphStorage.__init__` (line 172), which the sample canonicalized to `class:`; pyan resolves a `self.<attr>` read to the `__init__` that binds the attribute. No construction happens | **false** | pyan `self.<attr>` → binding `__init__` false positive (not a docstring mention) |
| 24 | `enrich_results` → `decorated_definition:ResultEnricher` | `mcp_server/tools/result_view.py:644-663` (full body) — `ResultEnricher.key` named only in the docstring; body iterates a pre-built `RESULT_ENRICHERS` list and calls `.apply(...)` | **false** | docstring-only reference, construction (if any) happens where `RESULT_ENRICHERS` is defined, not here |
| 25 | `_overrides_from_args` → `decorated_definition:_Knob` | `scripts/benchmark/run_sscg_benchmark.py:262-300` (full body) — docstring mentions `_KNOBS` (the list), never `_Knob` (the class); body iterates pre-built `_KNOBS` instances | **false** | iterates existing instances, doesn't construct the class |
| 26 | `PathFilter._classify` → `class:MatchKind` | `search/filters.py:536,539` `return False, None, MatchKind.NONE`; `if exclude_kind is MatchKind.INSIDE` | **false** | enum-member access, no call or construction (rule pinned 2026-09-03) |
| 27 | `IncrementalIndexer.__init__` → `decorated_definition:ResourceRefresher` | `search/incremental_indexer.py:62-96` (full body) — only ever constructs `NullResourceRefresher()` (line 65); `ResourceRefresher` is declared `class ResourceRefresher(Protocol)` (`search/resource_refresh.py:40`) and is **never instantiated anywhere** by design | **false** | type-only reference to a `Protocol`; the resolver mistook a type hint for a construction of an un-instantiable class |
| 28 | `IndexWriteStage._resolve_chunk_cache` → `class:IndexWriteStage` | `search/index_write_stage.py:291-308` (full body) — one line `return resolve_chunk_cache(self._chunk_cache, ...)`. The **raw** stored edge targets `method:IndexWriteStage.__init__` (line 61), canonicalized to `class:` in the sample — the same `self.<attr>` → binding-`__init__` mechanism as row 23 | **false** | pyan `self.<attr>` → binding `__init__` false positive (not a docstring mention) |
| 29 | `RRFReranker.rerank_tm2c2` → `class:ResultSource` | `search/reranker.py:357,366` `source=ResultSource.BM25` / `ResultSource.DENSE` | **false** | enum-member access, no call or construction (rule pinned 2026-09-03) |

**pyan: 0/10 true, p̂ = 0.00** (decided 2026-09-03; the 3/10 = 0.30 reading
under an enum-access-counts rule is recorded in the labels JSON as
`alternative_label` for rows 21/26/29). All 10 sampled edges are class-shaped
callees after canonicalization (the plan's "9 of 10" predates that step), and
**none of the 10 involve the caller instantiating the class.** They share a
single root cause rather than three failure modes: the pyan resolver
(`chunking/relationships/external_call_graph.py:258-269`) admits `uses` edges
whose callee flavor is `CLASS` — intended to catch `MyClass()` — without
checking that the reference sits in call position. Everything pyan records as
a class *use* therefore leaks in: type annotations (20, 27), enum-member
access (21, 26, 29), `self.<attr>` reads resolved to the binding `__init__`
(23, 28), references to instances of a dataclass (24, 25), and attribute-flow
into a method that then collapsed to its class (22). Fixing that one admission
rule is the follow-up; it should remove most of the 537 `unlabeled_cov` edges.

---

## AST tier (rows 30–39, declared confidence 0.5/0.7 — lowest rung, not gated by B4)

| # | Caller → Callee | Evidence | Label | Reason |
|---|---|---|---|---|
| 30 | `_build_file_summary` → `MetadataStore.set` | `chunking/file_summarizer.py:104` `sorted(set(summary.all_imports))` | **false** | builtin `set()` collision — the plan's own named example |
| 31 | `DecoratorExtractor._extract_from_tree` → `MetadataStore.get` | `chunk_metadata.get("chunk_id", "")` — `chunk_metadata: dict[str, Any]` | **false** | plain-dict `.get()` collision |
| 32 | `build_community_membership` → `MetadataStore.items` | `community_map.items()` / `pairs.items()` — local dicts | **false** | plain-dict `.items()` collision |
| 33 | `GraphQueryEngine._traverse_outbound` → `MetadataStore.set` | `graph/graph_queries.py:778-838` (full body) — zero mentions; only `set.add(...)` on local Python sets | **false** | no reference at all |
| 34 | `_touched_flat_keys` → `SymbolHashCache.get` | `arguments.get(arg_key)` — `arguments: dict[str, Any]` | **false** | plain-dict `.get()` collision |
| 35 | `handle_get_index_status` → `ChunkEmbeddingCache.get_stats` | calls found: `get_index_manager().get_stats()`, `_searcher.get_stats()` — neither returns/is a `ChunkEmbeddingCache` | **false** | same-method-name, different-class collision |
| 36 | `SearchConfig._apply_model_registry_dimension` → `ChunkEmbeddingCache.get` | `embedding_data.get("model_name")`, `model_config.get(...)` — plain dicts | **false** | plain-dict `.get()` collision |
| 37 | `HybridSearcher._load_bm25_index` → `FaissVectorIndex.load` | `search/hybrid_searcher.py:330` `self.bm25_index.load()`; `self.bm25_index = BM25Index(...)` (line 142) | **false** | same-method-name, different-class collision (`BM25Index.load`, not `FaissVectorIndex.load`) |
| 38 | `IndexWriteStage.add_to_index` → `HybridSearcher.add_embeddings` | `self._indexer.add_embeddings(...)`; `indexer: Indexer` where `Indexer = CodeIndexManager` (import alias, `index_write_stage.py:19`) | **false** | same-method-name, different-class collision (`CodeIndexManager.add_embeddings`, not `HybridSearcher.add_embeddings`) |
| 39 | `RelationshipAnalyzer._enrich_callees` → `SymbolHashCache.get` | `entry.edge_data.get("confidence")` etc. — `edge_data: dict` | **false** | plain-dict `.get()` collision |

**AST: 0/10 true, p̂ = 0.00.** Consistent with AST being the lowest-rung,
"always-on" naive resolver (0.5/0.7 declared) — this sample landed entirely
on common method names (`get`/`set`/`items`/`load`/`add_embeddings`) where
pure syntactic matching can't distinguish receiver types. Not a B4 input,
included for completeness since the sample already covers all four tiers.

---

## Decisions (2026-09-03)

1. **Rows 21, 26, 29 (pyan) → false.** Enum-member access is not a call
   (rule pinned above). Stakes, with `prec_est(pyan) = (186 + p̂·537)/723`:

   | p̂ | prec_est | Wilson 95% on p̂ (n=10) | prec_est range | vs `tag:exact` 0.4228 |
   |---|---|---|---|---|
   | 0/10 | 0.257 | [0.000, 0.278] | [0.257, 0.464] | below at the point, CI straddles |
   | 3/10 | 0.480 | [0.108, 0.603] | [0.337, 0.705] | **above** at the point, CI straddles |

   Either reading's CI straddles `tag:exact`, so the plan's open issue (2)
   — n=10 cannot separate pyan from `tag:exact` — stands regardless.
2. **Row 11 (libcst) → false.** Not a judgement call after all: the OTel
   SDK never invokes an exporter's `force_flush`, so the edge is simply
   wrong (suffix collision in `chunk_id_from_fqn`).

## Systemic finding: `split_block` callees collapse to their class

Rows 6, 9 and 22 share a defect that is neither a labeling question nor a
resolver error. `build_line_to_chunk_map` (`evaluation/chunk_mapping.py:50-53`)
defaults `semantic_types` to `{function, method, class, decorated_definition}`,
so the 288 `split_block` chunks in the index (long methods such as
`CodeIndexManager.add_embeddings`, `GenerativeReranker.rerank`,
`JinaRerankerV3.rerank`, `ModelLoader.load`) are absent from the line map, and
`find_enclosing_chunk` returns the enclosing `class:` chunk instead. Measured
on the stored graph (edges to `class:`-kind targets whose recorded `line` lies
inside the class body rather than on the `class` statement):

| tier | collapsed (inside body) | at `class` statement |
|---|---|---|
| lsp | **63** | 241 |
| pyan | 18 | 516 |
| libcst | 18 | 91 other / 1 at def (libcst lines are unreliable) |

Roughly one in five LSP class-target edges is a mis-routed method call. This
inflates LSP's false count here, and in production it points
`find_connections` at a class when the user asked about a method.

---

## Summary

| Tier | n | true | p̂ | declared confidence |
|---|---|---|---|---|
| lsp | 10 | 8 | 0.80 | 0.98 |
| libcst | 10 | 9 | 0.90 | 0.90 |
| **pyan** | **10** | **0** | **0.00** | **0.75** |
| ast | 10 | 0 | 0.00 | 0.5/0.7 |

Labels are persisted to `evaluation/resolver_precision_labels.json`
(local, gitignored like every `evaluation/*.json`) keyed by
`(tier, caller, callee)`, and `scripts/benchmark/precision_estimate.py`
combines them with `evaluation/resolver_tier_scores.json`'s
`edges_cov`/`hits_cov`/`unlabeled_cov` to produce per-tier p̂, a Wilson 95%
CI, `prec_est` with its range, and the plan's ω(tier) (`prec_est` rounded to
0.05). The plan (B4) contains no pass/fail bucket table for the sample; its
only rules are `ω(tier) := prec_est_tier` and the pyan-vs-`tag:exact` (0.4228)
comparison, and an earlier draft of this worksheet cited a "≤8/10 / 9–10/10"
table that exists nowhere — that citation is withdrawn. `search/config.py` is
untouched: §11 licenses no confidence change until the estimator output is
recorded, and the LSP figure should not be read until the `split_block`
collapse is fixed and the calibration re-run.

## Estimator output (2026-09-03)

`scripts/benchmark/precision_estimate.py` on the persisted labels and the B3
counts in `evaluation/resolver_tier_scores.json`:

| tier | n | true | p̂ | Wilson 95% | edges_cov | hits_cov | unlabeled_cov | prec_lb_cov | prec_est | range | ω | declared | vs tag:exact 0.4228 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lsp | 10 | 8 | 0.80 | [0.490, 0.943] | 1,026 | 819 | 207 | 0.7982 | **0.9596** | [0.8971, 0.9886] | 0.95 | 0.98 | above (CI clear) |
| libcst | 10 | 9 | 0.90 | [0.596, 0.982] | 318 | 239 | 79 | 0.7516 | **0.9752** | [0.8996, 0.9956] | 1.00 | 0.90 | above (CI clear) |
| pyan | 10 | 0 | 0.00 | [0.000, 0.278] | 723 | 186 | 537 | 0.2573 | **0.2573** | [0.2573, 0.4634] | 0.25 | 0.75 | below at point, CI straddles |
| ast | 10 | 0 | 0.00 | [0.000, 0.278] | 2,437 | 312 | 2,125 | 0.1280 | **0.1280** | [0.1280, 0.3700] | 0.15 | 0.5/0.7 | below (CI clear) |

Rejected alternative reading, kept for the record: pyan 3/10 → prec_est
0.4801, ω 0.50.

Reading: lsp and libcst clear `tag:exact` with room to spare, and their ω
lands within 0.05 of the declared confidence (the libcst ω of 1.00 is an
artefact of a 9/10 sample on a small `unlabeled_cov`; do not promote it).
pyan's point estimate sits a full 0.17 below `tag:exact` and its ω (0.25) is
one third of its declared 0.75, but the n=10 interval still reaches 0.46, so
the sample cannot *prove* pyan is worse than the untagged-exact reference —
it can only fail to show it is better. What this licenses per §11 is a
proposal, not a change: either re-declare pyan at ω=0.25 (which drops every
pyan edge below the 0.65 `min_confidence` injection floor, i.e. removes the
tier in effect) or fix the `CLASS`-flavor admission first and re-measure —
the latter is the cheaper experiment because it attacks the root cause of all
10 sampled false positives instead of pricing them in.

## Follow-ups spawned from this review

1. Include `split_block` chunks in `build_line_to_chunk_map` (or map them to
   the parent method id) so LSP/pyan callees stop collapsing to `class:`;
   re-run the B3 calibration afterwards.
2. `chunk_id_from_fqn`: same-file, same-bare-name method vs module function
   collision (row 11).
3. pyan `CLASS`-flavor admission: require call position before emitting
   (rows 20–29).
