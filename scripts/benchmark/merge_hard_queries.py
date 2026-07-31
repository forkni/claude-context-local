"""Build evaluation/golden_dataset_expanded.json = canonical dataset + hard queries.

Track 1.2 expansion (2026-07-26). The canonical evaluation/golden_dataset.json
is write-protected, so this script reads it plus the graded candidates
(Q100-Q133) and writes a merged copy to golden_dataset_expanded.json for use
via ``run_sscg_benchmark.py --golden-dataset``. Re-runnable: always regenerates
the expanded file from scratch.

Grades were assigned by inspecting the top-10 output of
scripts/benchmark/grade_candidate_queries.py (rounds 1-2,
benchmark_results/grade_candidates_round*.txt): gold = 3, legitimate
delegates/siblings = 2, marginal = 1.
"""

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET = REPO_ROOT / "evaluation" / "golden_dataset.json"
OUTPUT = REPO_ROOT / "evaluation" / "golden_dataset_expanded.json"
CANDIDATES = REPO_ROOT / "evaluation" / "hard_query_candidates.json"

# qid -> {chunk_id: grade}; grade 3 entries become expected_primary.
GRADES: dict[str, dict[str, int]] = {
    "Q100": {
        "search/mmap_vectors.py:method:MmapVectorStorage.save": 3,
        "search/mmap_vectors.py:class:MmapVectorStorage": 2,
        "search/mmap_vectors.py:method:MmapVectorStorage.load": 1,
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache.save": 1,
    },
    "Q101": {
        "graph/graph_storage.py:method:CodeGraphStorage.save": 3,
        "search/graph_integration.py:method:GraphIntegration.save": 2,
        "graph/graph_storage.py:class:CodeGraphStorage": 2,
    },
    "Q102": {
        "graph/graph_storage.py:method:CodeGraphStorage.clear": 3,
        "search/graph_integration.py:method:GraphIntegration.clear": 2,
        "graph/graph_storage.py:method:CodeGraphStorage.remove_file_nodes": 1,
        "mcp_server/tools/index_handlers.py:function:_clear_index_files_before_create": 1,
    },
    "Q103": {
        "embeddings/query_cache.py:method:QueryEmbeddingCache.get_stats": 3,
        "embeddings/embedder.py:method:CodeEmbedder.get_cache_stats": 2,
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache.get_stats": 1,
        "embeddings/query_cache.py:class:QueryEmbeddingCache": 1,
    },
    "Q104": {
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache._evict": 3,
        "search/base_searcher.py:method:BaseSearcher._evict_cache_if_needed": 1,
    },
    "Q105": {
        "search/symbol_cache.py:method:SymbolHashCache.get_by_chunk_id": 3,
        "search/symbol_cache.py:method:SymbolHashCache.get": 2,
        "search/symbol_cache.py:class:SymbolHashCache": 2,
        "search/symbol_cache.py:method:SymbolHashCache.contains": 1,
    },
    "Q106": {
        "search/faiss_index.py:method:FaissVectorIndex.search": 3,
        "search/indexer.py:method:CodeIndexManager.search": 2,
        "search/search_executor.py:decorated_definition:SearchExecutor.search_dense": 1,
    },
    "Q107": {
        "search/reranker.py:method:RRFReranker.rerank": 3,
        "search/reranker.py:method:RRFReranker.rerank_simple": 2,
        "search/reranker.py:class:RRFReranker": 2,
        "search/reranker.py:method:RRFReranker.analyze_fusion_quality": 1,
    },
    "Q108": {
        "search/centrality_ranker.py:method:CentralityRanker.rerank": 3,
        "search/graph_scoring_stage.py:method:GraphScoringStage._apply_centrality": 2,
        "search/centrality_ranker.py:class:CentralityRanker": 2,
        "search/centrality_ranker.py:method:CentralityRanker.annotate": 1,
    },
    "Q111": {
        "search/index_sync.py:method:IndexSynchronizer.resync_bm25_from_dense": 3,
        "search/hybrid_searcher.py:method:HybridSearcher.resync_bm25_from_dense": 2,
        "search/index_sync.py:method:IndexSynchronizer.resync_if_desynced": 2,
        "search/index_sync.py:method:IndexSynchronizer.validate_index_sync": 1,
        "search/index_sync.py:method:IndexSynchronizer._live_counts": 1,
    },
    "Q112": {
        "search/index_sync.py:method:IndexSynchronizer.remove_files": 3,
        "search/hybrid_searcher.py:method:HybridSearcher.remove_files": 2,
        "search/indexer.py:method:CodeIndexManager.remove_files": 2,
        "search/batch_operations.py:method:BatchOperations.remove_files": 2,
        "mcp_server/tools/index_handlers.py:function:_purge_index_dir": 1,
        "search/incremental_indexer.py:method:IncrementalIndexer._remove_old_chunks": 1,
    },
    "Q113": {
        "merkle/change_detector.py:method:ChangeDetector.detect_changes": 3,
        "merkle/change_detector.py:method:ChangeDetector.detect_changes_from_snapshot": 2,
        "search/incremental_indexer.py:method:IncrementalIndexer.detect_changes": 2,
        "merkle/change_detector.py:decorated_definition:FileChanges": 1,
    },
    "Q114": {
        "search/tokenization.py:function:normalize_to_tokens": 3,
        "search/tokenization.py:decorated_definition:normalize_to_tokens": 3,
        "search/bm25_index.py:method:TextPreprocessor.preprocess_code": 2,
        "search/centrality_ranker.py:function:_tokenize_for_matching": 2,
        "search/ranking_heuristics.py:method:RankingHeuristics._normalize_to_tokens": 2,
        "search/tokenization.py:function:is_camelcase": 1,
        "search/tokenization.py:function:is_snake_or_dunder": 1,
    },
    "Q115": {
        "mcp_server/cleanup_queue.py:method:CleanupQueue.process": 3,
        "mcp_server/cleanup_queue.py:method:CleanupQueue.add": 2,
        "mcp_server/cleanup_queue.py:class:CleanupQueue": 2,
        "mcp_server/cleanup_queue.py:method:CleanupQueue.get_pending": 1,
    },
    "Q116": {
        "search/gpu_monitor.py:method:GPUMemoryMonitor.estimate_batch_memory": 3,
        "embeddings/embedder.py:method:calculate_optimal_batch_size": 2,
        "search/gpu_monitor.py:method:GPUMemoryMonitor.can_use_gpu": 1,
        "embeddings/embedder.py:method:CodeEmbedder._check_vram_status": 1,
    },
    "Q117": {
        "chunking/relationships/lsp_call_graph.py:function:_path_to_uri": 3,
        "chunking/relationships/lsp_call_graph.py:function:_encode": 2,
        "chunking/relationships/lsp_call_graph.py:function:_uri_to_path": 1,
    },
    "Q118": {
        "search/filters.py:method:DirectoryFilter.matches": 3,
        "search/filters.py:function:matches_directory_filter": 2,
        "search/filters.py:method:DirectoryFilter.matches_for_traversal": 1,
        "search/filters.py:method:DirectoryFilter.matches_for_file": 1,
    },
    "Q119": {
        "search/filters.py:function:compute_drive_agnostic_hash": 3,
        "search/filters.py:function:find_project_at_different_drive": 2,
        "mcp_server/storage_manager.py:function:_update_stored_path_if_changed": 2,
        "search/filters.py:function:compute_legacy_hash": 1,
        "merkle/snapshot_manager.py:method:SnapshotManager.get_project_id": 1,
    },
    "Q120": {
        "search/index_sync.py:method:IndexSynchronizer.save_indices": 3,
        "search/index_sync.py:method:IndexSynchronizer._verify_bm25_files": 3,
        "search/index_write_stage.py:method:IndexWriteStage.run": 2,
        "search/hybrid_searcher.py:method:HybridSearcher._verify_bm25_files": 2,
        "search/bm25_index.py:method:BM25Index.save": 1,
    },
    "Q121": {
        "search/faiss_index.py:class:FaissVectorIndex": 3,
        "search/indexer.py:class:CodeIndexManager": 2,
        "search/faiss_index.py:method:FaissVectorIndex.create": 1,
    },
    "Q122": {
        "mcp_server/model_pool_manager.py:class:ModelPoolManager": 3,
        "mcp_server/model_pool_manager.py:method:ModelPoolManager.get_embedder": 2,
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache._evict": 1,
    },
    "Q123": {
        "embeddings/chunk_cache.py:decorated_definition:ChunkEmbeddingCache.key_for": 3,
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache.get": 3,
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache.put": 2,
        "embeddings/chunk_cache.py:class:ChunkEmbeddingCache": 2,
        "embeddings/embedder.py:method:CodeEmbedder.embed_chunks": 2,
        "embeddings/chunk_cache.py:method:ChunkEmbeddingCache.load": 1,
    },
    "Q124": {
        "search/mmap_vectors.py:method:MmapVectorStorage.load": 3,
        "search/mmap_vectors.py:method:MmapVectorStorage.save": 3,
        "search/mmap_vectors.py:class:MmapVectorStorage": 2,
        "search/mmap_vectors.py:decorated_definition:MmapVectorStorage.is_loaded": 1,
    },
    "Q125": {
        "search/gpu_monitor.py:function:release_gpu_memory": 3,
        "mcp_server/tools/index_handlers.py:function:_release_gpu_memory": 2,
        "search/incremental_indexer.py:method:IncrementalIndexer._clear_gpu_cache": 2,
        "embeddings/embedder.py:method:CodeEmbedder.cleanup": 2,
    },
    "Q126": {
        "search/intent_classifier.py:method:IntentClassifier.classify": 3,
        "search/intent_classifier.py:class:IntentClassifier": 2,
        "mcp_server/tools/search_orchestrator.py:method:SearchPlanner.plan": 2,
        "search/config.py:method:SearchConfigManager.get_search_mode_for_query": 2,
        "search/intent_classifier.py:class:QueryIntent": 1,
    },
    "Q127": {
        "search/hybrid_searcher.py:method:HybridSearcher._apply_ego_graph_expansion": 3,
        "search/ego_graph_retriever.py:method:EgoGraphRetriever.expand_search_results": 2,
        "search/config.py:decorated_definition:EgoGraphConfig": 2,
        "search/ego_graph_retriever.py:method:EgoGraphRetriever.score_neighbors": 1,
        "search/graph_scoring_stage.py:method:GraphScoringStage._cap_results": 1,
    },
    "Q128": {
        "search/relationship_analyzer.py:method:RelationshipAnalyzer._resolve_by_symbol": 3,
        "search/relationship_analyzer.py:method:RelationshipAnalyzer._resolve_target": 2,
        "mcp_server/tools/search_handlers.py:function:_resolve_symbol_to_chunk_id": 1,
        "evaluation/metrics.py:function:normalize_chunk_id": 1,
    },
    "Q129": {
        "embeddings/query_cache.py:method:QueryEmbeddingCache.get": 3,
        "embeddings/embedder.py:decorated_definition:CodeEmbedder.embed_query": 2,
        "embeddings/query_cache.py:method:QueryEmbeddingCache.put": 1,
        "embeddings/embedder.py:method:CodeEmbedder.clear_query_cache": 1,
    },
    "Q131": {
        "chunking/relationships/call_edge_resolver.py:function:validate_py_files": 3,
        "search/index_write_stage.py:method:IndexWriteStage._inject_call_edges": 2,
        "chunking/relationships/call_edge_resolver.py:function:prepare_scoped_files": 2,
        "chunking/relationships/call_edge_resolver.py:function:scope_to_indexed_files": 1,
    },
    "Q132": {
        "chunking/relationships/lsp_call_graph.py:class:_LspClient": 3,
        "chunking/relationships/lsp_call_graph.py:class:LSPResolver": 2,
        "chunking/relationships/lsp_call_graph.py:method:_LspClient.request": 2,
        "chunking/relationships/lsp_call_graph.py:function:_read_frame": 1,
        "chunking/relationships/lsp_call_graph.py:function:_read_response": 1,
    },
    "Q133": {
        "chunking/relationships/lsp_call_graph.py:method:_LspClient._dispatch": 3,
        "chunking/relationships/lsp_call_graph.py:method:_LspClient.request": 2,
        "chunking/relationships/lsp_call_graph.py:method:_LspClient._reader_loop": 2,
        "chunking/relationships/lsp_call_graph.py:class:_LspClient": 2,
    },
}

SPLITS: dict[str, str] = {
    # A: train 15 / val 4 / test 5
    "Q100": "train",
    "Q103": "train",
    "Q105": "train",
    "Q106": "train",
    "Q107": "train",
    "Q108": "train",
    "Q111": "train",
    "Q114": "train",
    "Q115": "train",
    "Q118": "train",
    "Q119": "train",
    "Q125": "train",
    "Q127": "train",
    "Q128": "train",
    "Q131": "train",
    "Q102": "val",
    "Q116": "val",
    "Q117": "val",
    "Q129": "val",
    "Q101": "test",
    "Q104": "test",
    "Q113": "test",
    "Q126": "test",
    "Q133": "test",
    # B: train 2 / val 1 / test 1
    "Q120": "train",
    "Q124": "train",
    "Q123": "val",
    "Q112": "test",
    # C: train 1 / val 1 / test 1
    "Q122": "train",
    "Q132": "val",
    "Q121": "test",
}


def main() -> None:
    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    candidates = {
        c["id"]: c
        for c in json.loads(CANDIDATES.read_text(encoding="utf-8"))["candidates"]
    }

    existing_ids = {q["id"] for q in dataset["queries"]}
    clash = existing_ids & set(GRADES)
    if clash:
        sys.exit(
            f"Refusing to merge: IDs already present in canonical: {sorted(clash)}"
        )
    # candidates may also hold ungraded drafts (e.g. Category-G QG01-QG14) awaiting
    # promotion via grade_candidate_queries.py; only GRADES's own IDs must resolve.
    if set(GRADES) != set(SPLITS) or not set(GRADES) <= set(candidates):
        sys.exit(
            "ID mismatch between GRADES/SPLITS/candidates: "
            f"{set(GRADES) ^ set(SPLITS)} | {set(GRADES) - set(candidates)}"
        )

    for qid in sorted(GRADES):
        cand = candidates[qid]
        grades = GRADES[qid]
        for gold in cand["intended"]:
            if grades.get(gold) != 3:
                sys.exit(f"{qid}: intended gold {gold} is not graded 3")
        dataset["queries"].append(
            {
                "id": qid,
                "query": cand["query"],
                "category": cand["category"],
                "split": SPLITS[qid],
                "expected": [c for c, g in grades.items() if g >= 2],
                "expected_primary": [c for c, g in grades.items() if g == 3],
                "relevance_grades": grades,
            }
        )

    meta = dataset["_meta"]
    meta["total_queries"] = len(dataset["queries"])
    meta["labeled_by"] += ", Claude Fable 5 (Q100-Q133, hard-query expansion)"
    from collections import Counter

    split_counts = Counter(q["split"] for q in dataset["queries"])
    meta["splits"]["train"] = split_counts["train"]
    meta["splits"]["val"] = split_counts["val"]
    meta["splits"]["test"] = split_counts["test"]
    meta.setdefault("changelog", []).append(
        {
            "date": "2026-07-26",
            "change": (
                "Added 33 hard queries (Q100-Q133, Q130 dropped): distractor-heavy "
                "behavioral paraphrases targeting name-collision sets (save/load/"
                "search/rerank/clear/get_stats/remove_files). Graded via live "
                "search at k=10 (scripts/benchmark/grade_candidate_queries.py, "
                "2 rounds); 8 queries have primary gold outside top-10, several "
                "outside the 30-50 candidate rerank pool. Splits stratified: "
                "A 16/5/5, B 2/1/1, C 1/1/1 (train/val/test)."
            ),
        }
    )
    meta.setdefault("changelog", []).append(
        {
            "date": "2026-07-31",
            "change": (
                "Removed Q109/Q110 (ONNX backend-selection and ONNX-conversion "
                "queries) as part of the ONNX dormant-code deletion: their gold "
                "targets (embeddings/model_loader.py:method:ModelLoader."
                "_should_use_onnx; embeddings/onnx_loader.py:method:"
                "ONNXModelLoader.convert_if_needed and friends) were deleted "
                "with no functional equivalent to retarget to. Also dropped the "
                "dead embeddings/onnx_wrapper.py:method:ONNXEmbeddingModel."
                "cleanup distractor (grade 1) from Q125's relevance_grades. "
                "Splits restratified: A 15/4/5 (was 16/5/5)."
            ),
        }
    )

    OUTPUT.write_text(
        json.dumps(dataset, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\r\n",
    )
    print(
        f"Wrote {OUTPUT.name}: {len(GRADES)} new queries, total {meta['total_queries']}."
    )
    print(f"Splits: {dict(split_counts)}")


if __name__ == "__main__":
    main()
