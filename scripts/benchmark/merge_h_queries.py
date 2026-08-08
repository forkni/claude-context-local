"""Promote graded H-category (commit-mined bug-fix) queries into golden_dataset_expanded.json.

Parallel merge path to merge_hard_queries.py -- deliberately not reused. That
script always rebuilds golden_dataset_expanded.json from scratch out of the
canonical golden_dataset.json plus its own hardcoded Q100-Q133 GRADES/SPLITS.
Replicating that here would mean re-encoding the entire Q100-Q133 GRADES dict
a second time just to regenerate data that already exists. Instead this
script reads the *current* golden_dataset_expanded.json (which already
contains canonical + Q100-Q133) as its base and appends the H queries on top,
writing back to the same file. Consequence: re-running this script after a
successful merge will hit the existing_ids/GRADES clash guard and refuse --
it is a run-once promotion, not a rebuild-every-time generator.

Source: evaluation/commit_mined_candidates.json (H category, single-file,
<=2 golds), paraphrased in benchmark_results/h_candidates_paraphrased.json,
graded via live search at k=10 (scripts/benchmark/grade_candidate_queries.py
--candidates, 2 rounds: benchmark_results/grade_candidates_round{1,2}.txt).

Grading policy: every commit-mined "intended" chunk_id is graded 3 (trusting
the commit-mining ground truth as-is; no manual sibling/near-miss grade-2
embellishment this round -- see the changelog entry this script writes for
the rationale). Two intended golds (H012, H067) named an invalid chunk_id
(mcp_server/server.py:function:app_lifespan); both are corrected here to the
grader's own suggested ID (mcp_server/server.py:decorated_definition:app_lifespan).

Excluded from promotion: H002, H010, H011, H014, H018, H019, H024-H026,
H031, H036-H038, H040, H042 (identical duplicate of H041), H043, H044,
H046-H047, H051, H053, H055, H057-H059, H069-H070 -- graded pool_miss/invalid
across both original rounds. H035/H060/H061/H068 were held back at the time
for a different reason (round 1 top-10, round 2 pool_miss against the same
index) attributed to reranker batch-composition non-determinism -- ADR-0021
(2026-08-02) found and fixed the actual cause (`PYTHONHASHSEED` set-iteration
order, not bf16 rounding) and pinned it, making that flip-based exclusion
rationale void. See `H_QUERIES_TOPUP_20260804` below for the re-grade under
the pin: 2 of the 4 promote, 2 are rejected on query-quality/gold grounds
unrelated to determinism.
"""

import json
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPANDED = REPO_ROOT / "evaluation" / "golden_dataset_expanded.json"

# id -> (query text, [intended gold chunk_ids], split)
H_QUERIES: dict[str, tuple[str, list[str], str]] = {
    "H001": (
        "move per-module summary generation out of the community-detection stage so it runs as a separate step",
        [
            "search/summary_stage.py:class:SummaryStage",
            "search/summary_stage.py:method:SummaryStage.generate_module_summaries",
        ],
        "train",
    ),
    "H003": (
        "quiet the parse-error log level when a file's error content still produces a usable chunk",
        [
            "chunking/tree_sitter.py:decorated_definition:ParsedSource",
            "chunking/tree_sitter.py:method:TreeSitterChunker.chunk_parsed",
        ],
        "train",
    ),
    "H004": (
        "avoid logging a warning for files that are genuinely empty rather than failing to parse",
        [
            "search/parallel_chunker.py:decorated_definition:ParallelChunker._accumulate_chunk_stats",
            "search/parallel_chunker.py:method:ParallelChunker.chunk_files",
        ],
        "train",
    ),
    "H005": (
        "don't drop relationship edges for chunks that aren't semantic definitions when building the graph from embeddings",
        [
            "search/graph_integration.py:method:GraphIntegration._make_spec_from_embedding"
        ],
        "train",
    ),
    "H006": (
        "log which specific files produced zero chunks, and track dropped language-server URIs as a separate counter from other failures",
        [
            "search/parallel_chunker.py:decorated_definition:ParallelChunker._log_chunking_summary",
            "search/parallel_chunker.py:method:ParallelChunker.chunk_files",
        ],
        "train",
    ),
    "H007": (
        "make the graph storage's clear operation also remove the leftover community-detection cache file",
        ["graph/graph_storage.py:method:CodeGraphStorage.clear"],
        "train",
    ),
    "H008": (
        "make a parameter-sweep script rebuild its searcher instance fresh on every iteration instead of reusing a stale one, and expose the RRF k constant as a CLI flag",
        [
            "scripts/benchmark/run_sscg_benchmark.py:function:_apply_reranker_budget_override",
            "scripts/benchmark/run_sscg_benchmark.py:function:build_parser",
        ],
        "train",
    ),
    "H009": (
        "introduce an opt-in reranking mode that scores candidates in a single pass instead of two, off by default",
        ["search/config.py:decorated_definition:RerankerConfig"],
        "train",
    ),
    "H012": (
        "suppress a harmless ASGI error message the web server prints when stopped with Ctrl+C",
        [
            "mcp_server/server.py:function:_configure_logging",
            "mcp_server/server.py:decorated_definition:app_lifespan",
        ],
        "train",
    ),
    "H013": (
        "fix a crash in the config-reload endpoint from accessing an attribute that no longer exists on the config manager",
        ["mcp_server/server.py:function:handle_reload_config"],
        "train",
    ),
    "H015": (
        "fix the routine that rebuilds the BM25 index from the dense index silently skipping chunks with empty text content, which kept the two indices out of sync",
        ["search/index_sync.py:method:IndexSynchronizer.resync_bm25_from_dense"],
        "train",
    ),
    "H020": (
        "decode a percent-encoded drive-letter colon when converting a language-server URI back to a Windows file path",
        ["chunking/relationships/lsp_call_graph.py:function:_uri_to_path"],
        "train",
    ),
    "H021": (
        "fix several protocol bugs in the language-server call-graph resolver: where the symbol probe is positioned, matching response IDs back to requests, and URI parsing",
        [
            "chunking/relationships/lsp_call_graph.py:function:_path_to_uri",
            "chunking/relationships/lsp_call_graph.py:method:LSPResolver._run_lsp",
        ],
        "train",
    ),
    "H022": (
        "tune the call-graph resolvers for precision: filter out a category of callee edges from one resolver, downweight wildcard matches, and fix self-referential calls in another",
        [
            "chunking/relationships/libcst_call_graph.py:method:_CallVisitor.leave_AsyncFunctionDef",
            "chunking/relationships/libcst_call_graph.py:method:_CallVisitor.visit_Call",
        ],
        "train",
    ),
    "H023": (
        "make the call-graph edge lookup keep returning the older string-valued confidence labels instead of coercing them to floats",
        ["graph/graph_storage.py:method:CodeGraphStorage.get_edge_data"],
        "train",
    ),
    "H027": (
        "add logging when the lowest-priority fallback tier of symbol resolution fails to find a semantic match",
        [
            "search/relationship_analyzer.py:method:RelationshipAnalyzer._resolve_by_symbol"
        ],
        "train",
    ),
    "H028": (
        "normalize backslash path separators on Windows when building the line-number-to-chunk lookup",
        ["evaluation/chunk_mapping.py:function:build_line_to_chunk_map"],
        "train",
    ),
    "H029": (
        "detect an embedding model loaded in a different pool when switching projects, and fix an always-false loaded flag in the model-listing tool",
        [
            "mcp_server/tools/status_handlers.py:decorated_definition:handle_list_embedding_models"
        ],
        "train",
    ),
    "H030": (
        "have the graph storage's clear routine also delete the on-disk call-graph JSON so a later reload doesn't resurrect stale nodes",
        ["graph/graph_storage.py:method:CodeGraphStorage.clear"],
        "train",
    ),
    "H032": (
        "add a multi-tier exact-match lookup step to symbol resolution to fix inconsistent results across runs",
        ["search/relationship_analyzer.py:method:RelationshipAnalyzer._resolve_target"],
        "train",
    ),
    "H033": (
        "fix the storage-directory resolver logging a spurious error when the active model belongs to a different pool",
        ["mcp_server/storage_manager.py:method:get_project_storage_dir"],
        "train",
    ),
    "H034": (
        "cap the inference batch size for the ONNX backend based on free GPU memory so the very first run doesn't immediately run out of VRAM",
        ["embeddings/embedder.py:function:calculate_optimal_batch_size"],
        "train",
    ),
    "H039": (
        "change the recommended embedding model for high-VRAM workstations to a newer retrieval-tuned model",
        [
            "search/vram_manager.py:class:VRAMTierManager",
            "search/vram_manager.py:decorated_definition:VRAMTier",
        ],
        "train",
    ),
    "H041": (
        "update the tracked config-file modification time right after saving so the next load can skip re-reading from disk",
        ["search/config.py:method:SearchConfigManager.save_config"],
        "train",
    ),
    "H045": (
        "remove a duplicated block of execution-provider options, accept a numbered CUDA device string in a validation gate, and correct a docstring",
        ["embeddings/model_loader.py:method:ModelLoader._measure_activation_per_item"],
        "train",
    ),
    "H048": (
        "pull a line-parsing helper out to a shared location, fix a flaky size-threshold test, and remove an unused environment-file extension from file-role classification",
        [
            "chunking/multi_language_chunker.py:decorated_definition:MultiLanguageChunker._classify_file_role"
        ],
        "val",
    ),
    "H049": (
        "switch the VRAM-usage monitor to reading the process's own allocated-memory counter instead of the device-wide free/total query",
        ["embeddings/embedder.py:method:CodeEmbedder._check_vram_status"],
        "val",
    ),
    "H050": (
        "fix a failing test around the search-code handler not being ready to use the hybrid searcher",
        ["mcp_server/tools/search_handlers.py:decorated_definition:handle_search_code"],
        "val",
    ),
    "H052": (
        "apply a round of code-review feedback to the query-embedding cache initialization",
        ["embeddings/query_cache.py:method:QueryEmbeddingCache.__init__"],
        "val",
    ),
    "H054": (
        "add a second phase of call-graph edge resolution when saving indices, with broader test coverage",
        [
            "search/hybrid_searcher.py:method:HybridSearcher.add_embeddings",
            "search/hybrid_searcher.py:method:HybridSearcher.save_indices",
        ],
        "val",
    ),
    "H056": (
        "extract docstrings and compute complexity-related metadata during Python chunking as an early low-effort improvement",
        [
            "chunking/languages/python.py:method:PythonChunker._extract_docstring",
            "chunking/languages/python.py:method:PythonChunker.extract_metadata",
        ],
        "val",
    ),
    "H062": (
        "remove a large batch of backward-compatibility property aliases from the main search config class",
        ["search/config.py:class:SearchConfig"],
        "test",
    ),
    "H063": (
        "update call sites in the connection-analysis and similar-code handlers after metadata storage was pulled out into its own class",
        [
            "mcp_server/tools/search_handlers.py:decorated_definition:handle_find_connections",
            "mcp_server/tools/search_handlers.py:decorated_definition:handle_find_similar_code",
        ],
        "test",
    ),
    "H064": (
        "make the clear-index operation remove BM25 index files for every embedding model, not just the active one",
        ["search/hybrid_searcher.py:method:HybridSearcher.clear_index"],
        "test",
    ),
    "H065": (
        "carry forward the directory-exclusion filters from the saved snapshot when detecting incremental changes",
        [
            "merkle/change_detector.py:method:ChangeDetector.detect_changes_from_snapshot",
            "merkle/change_detector.py:method:ChangeDetector.quick_check",
        ],
        "test",
    ),
    "H066": (
        "make the index-status report include a synced flag by lazily initializing the searcher instead of requiring one already loaded",
        ["search/hybrid_searcher.py:method:HybridSearcher.get_stats"],
        "test",
    ),
    "H067": (
        "finish cleaning up leftover references after migrating global server state into an application-state object, including server startup and stdio entrypoints",
        [
            "mcp_server/server.py:decorated_definition:app_lifespan",
            "mcp_server/server.py:function:run_stdio_server",
        ],
        "test",
    ),
}

# Re-grade of H035/H060/H061/H068 under the ADR-0021 PYTHONHASHSEED=0 pin
# (scripts/benchmark/grade_candidate_queries.py --candidates
# benchmark_results/h_candidates_paraphrased.json --only H035,H060,H061,H068,
# 2026-08-04). Under the pin the four are no longer flip-prone -- each is a
# stable, reproducible result -- so the gate becomes query quality + a
# defensible gold, not round agreement:
#
# - H035: stable POOL_MISS. Query and gold are both clean (verified against
#   search/index_write_stage.py:58-196 -- IndexWriteStage.run clears the GPU
#   cache and returns early on embed_error exactly as described). Promoted
#   as-is: a genuine, reproducible retrieval failure is real signal, not
#   noise -- excluding every hard case would bias the benchmark upward.
# - H068: rank=9 in-pool against its original intended gold
#   (CodeIndexManager.get_similar_chunks), but that gold is wrong -- commit
#   06501b66 (the commit this query was mined from) added
#   get_similar_chunks_batched, not get_similar_chunks, and
#   multi_hop_searcher.py (the only production caller matching "during
#   multi-hop search" in the query text) calls the batched method. Corrected
#   gold ranks 2. Same stale-intended-ID pattern as H012/H067 above.
# - H060: stable POOL_MISS, rejected. "fix incremental-indexing tests broken
#   by an API signature mismatch and a performance regression" describes
#   test-level symptoms of the source commit, not any behavior of the
#   intended gold (CodeIndexManager.save_index) -- commit-narrative label
#   noise, same shape flagged for H070.
# - H061: stable POOL_MISS, rejected. Intended gold
#   (resource_manager.py:initialize_server_state) does not do GPU-memory
#   tier management -- initialize_server_state's own docstring lists config
#   sync, default-project restore, model-pool init, and deferred cleanup;
#   the actual VRAM-tier logic is search/vram_manager.py:VRAMTierManager,
#   which occupies pool ranks 1-3. Gold is not defensible, and the query
#   text ("validated against benchmark runs") is commit-narrative rather
#   than behavior-describing, so not eligible for a gold correction either.
H_QUERIES_TOPUP_20260804: dict[str, tuple[str, list[str], str]] = {
    "H035": (
        "free the GPU memory cache before returning early on an embedding failure during index writing",
        ["search/index_write_stage.py:method:IndexWriteStage.run"],
        "test",
    ),
    "H068": (
        "batch multiple vector-similarity lookups into a single FAISS call during multi-hop search to shave latency",
        ["search/indexer.py:method:CodeIndexManager.get_similar_chunks_batched"],
        "test",
    ),
}

CHANGELOG_ENTRY = {
    "date": "2026-08-02",
    "change": (
        "Added 37 H-category queries (Q100-Q133-adjacent, id-prefixed H not Q to keep "
        "the commit-mined batch visually distinct): bug-fix localization queries mined "
        "from single-file/<=2-gold commits, paraphrased from commit subjects "
        "(evaluation/commit_mined_candidates.json, benchmark_results/h_candidates_paraphrased.json) "
        "and graded via live search at k=10 across 2 rounds "
        "(scripts/benchmark/grade_candidate_queries.py --candidates). All intended golds "
        "graded 3 as-is (no manual sibling/near-miss grade-2 embellishment this round). "
        "H012 and H067 had an invalid intended gold (mcp_server/server.py:function:app_lifespan, "
        "a stale pre-refactor ID) corrected to the grader's suggested "
        "mcp_server/server.py:decorated_definition:app_lifespan. Dropped H042 as an exact "
        "duplicate of H041 (same query text and gold, different source commit). Excluded "
        "H035/H060/H061/H068 despite being found in top-10 during round 1: round 2 (an "
        "identical re-run scoped to round 1's passers) dropped all four to pool_miss "
        "against the same live index -- bf16 neural-reranker batch-composition "
        "non-determinism changes score ordering for borderline candidates between runs "
        "of different query-set sizes, and a single lucky run isn't enough signal to fix "
        "these into a golden set. Splits: train 25 / val 6 / test 6. 126 I-category "
        "candidates (multi-file or >2 golds) remain out of scope."
    ),
}

CHANGELOG_ENTRY_TOPUP_20260804 = {
    "date": "2026-08-04",
    "change": (
        "Re-graded H035/H060/H061/H068 under the ADR-0021 PYTHONHASHSEED=0 "
        "determinism pin (scripts/benchmark/grade_candidate_queries.py "
        "--candidates benchmark_results/h_candidates_paraphrased.json --only "
        "H035,H060,H061,H068), superseding the 2026-08-02 bf16-non-determinism "
        "exclusion rationale for these four IDs (ADR-0021 showed the actual "
        "cause was PYTHONHASHSEED set-iteration order). Promoted H035 as a "
        "stable, reproducible pool_miss with a clean query and a verified "
        "gold -- a genuine hard case, not noise. Promoted H068 with its "
        "intended gold corrected from CodeIndexManager.get_similar_chunks to "
        "CodeIndexManager.get_similar_chunks_batched (the method commit "
        "06501b66 actually added, and the one multi_hop_searcher.py calls; "
        "same stale-intended-ID pattern as H012/H067). Rejected H060 "
        "(commit-narrative query text describing test-fix symptoms, not any "
        "behavior of its gold) and H061 (gold does not perform the "
        "GPU-memory-tier-management the query describes; that logic lives in "
        "search/vram_manager.py:VRAMTierManager instead). Splits: both new "
        "queries assigned test."
    ),
}


def main() -> None:
    data = json.loads(EXPANDED.read_text(encoding="utf-8"))
    meta = data["_meta"]
    queries = data["queries"]

    existing_ids = {q["id"] for q in queries}
    to_merge = H_QUERIES_TOPUP_20260804
    clash = existing_ids & set(to_merge)
    if clash:
        sys.exit(
            f"Refusing to merge: IDs already present in expanded dataset: {sorted(clash)}"
        )

    for qid, (_text, golds, split) in to_merge.items():
        if split not in ("train", "val", "test"):
            sys.exit(f"{qid}: invalid split {split!r}")
        if len(golds) != len(set(golds)):
            sys.exit(f"{qid}: duplicate gold chunk_ids in {golds}")

    for qid, (text, golds, split) in to_merge.items():
        grades = dict.fromkeys(golds, 3)
        queries.append(
            {
                "id": qid,
                "query": text,
                "category": "H",
                "split": split,
                "expected": list(golds),
                "expected_primary": list(golds),
                "relevance_grades": grades,
            }
        )

    meta["total_queries"] = len(queries)
    meta["labeled_by"] += ", Claude Sonnet 5 (H035/H068 top-up, ADR-0021 re-grade)"
    split_counts = Counter(q["split"] for q in queries)
    meta["splits"] = {
        "train": split_counts["train"],
        "val": split_counts["val"],
        "test": split_counts["test"],
        "note": meta["splits"].get("note", "") + " H top-up: +2 test (H035, H068).",
    }
    meta.setdefault("changelog", []).append(CHANGELOG_ENTRY_TOPUP_20260804)

    EXPANDED.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\r\n",
    )
    print(
        f"Wrote {EXPANDED.name}: {len(to_merge)} new H queries, total {meta['total_queries']}."
    )
    print(
        f"Splits: train={split_counts['train']} val={split_counts['val']} test={split_counts['test']}"
    )


if __name__ == "__main__":
    main()
