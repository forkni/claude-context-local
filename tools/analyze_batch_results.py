#!/usr/bin/env python3
"""Analyze MCP search results against verified ground truth."""

import json
from pathlib import Path


# Results from first 10 MCP searches (manually collected)
BATCH_1_RESULTS = {
    1: {
        "query": "estimate_tokens function",
        "expected": "chunking/languages/base.py:22-56:function:estimate_tokens",
        "category": "exact_function",
        "top_5": [
            "chunking/languages/base.py:22-56:function:estimate_tokens",
            "chunking/languages/base.py:59-75:function:estimate_characters",
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
        ],
    },
    2: {
        "query": "token estimation with tiktoken or whitespace",
        "expected": "chunking/languages/base.py:22-56:function:estimate_tokens",
        "category": "exact_function",
        "top_5": [
            "chunking/languages/base.py:22-56:function:estimate_tokens",
            "chunking/languages/base.py:59-75:function:estimate_characters",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
        ],
    },
    3: {
        "query": "greedy merge small chunks algorithm",
        "expected": "chunking/languages/base.py:243-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        "category": "algorithm",
        "top_5": [
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "search/config.py:296-351:merged:ChunkingConfig",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
        ],
    },
    4: {
        "query": "_greedy_merge_small_chunks method",
        "expected": "chunking/languages/base.py:243-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        "category": "exact_function",
        "top_5": [
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        ],
    },
    5: {
        "query": "split large node at AST boundaries",
        "expected": "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
        "category": "algorithm",
        "top_5": [
            "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
            "graph/call_graph_extractor.py:238-395:merged:PythonCallGraphExtractor._extract_call_from_node",
            "chunking/languages/base.py:638-686:method:LanguageChunker._create_split_chunk",
            "chunking/languages/base.py:789-817:method:LanguageChunker._calculate_accumulated_size",
            "chunking/languages/go.py:27-35:method:GoChunker._get_splittable_node_types",
        ],
    },
    6: {
        "query": "_split_large_node method",
        "expected": "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
        "category": "exact_function",
        "top_5": [
            "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
            "chunking/languages/base.py:138-145:decorated_definition:LanguageChunker._get_splittable_node_types",
            "chunking/languages/base.py:638-686:method:LanguageChunker._create_split_chunk",
            "chunking/languages/base.py:767-787:method:LanguageChunker._get_split_threshold",
            "chunking/languages/python.py:33-56:merged:PythonChunker._get_splittable_node_types",
        ],
    },
    7: {
        "query": "create merged chunk from multiple chunks",
        "expected": "chunking/languages/base.py:195-241:method:LanguageChunker._create_merged_chunk",
        "category": "algorithm",
        "top_5": [
            "chunking/languages/base.py:195-241:method:LanguageChunker._create_merged_chunk",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        ],
    },
    8: {
        "query": "_create_merged_chunk method",
        "expected": "chunking/languages/base.py:243-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        "category": "exact_function",
        "top_5": [
            "chunking/languages/base.py:195-241:method:LanguageChunker._create_merged_chunk",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        ],
    },
    9: {
        "query": "community-based chunk remerging",
        "expected": "chunking/languages/base.py:381-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        "category": "algorithm",
        "top_5": [
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
            "search/incremental_indexer.py:694-766:method:IncrementalIndexer._regenerate_chunk_ids",
            "search/graph_integration.py:162-239:split_block:GraphIntegration.build_graph_from_chunks",
        ],
    },
    10: {
        "query": "remerge_chunks_with_communities static method",
        "expected": "chunking/languages/base.py:381-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        "category": "exact_function",
        "top_5": [
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
            "search/incremental_indexer.py:694-766:method:IncrementalIndexer._regenerate_chunk_ids",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        ],
    },
}

BATCH_2_RESULTS = {
    11: {
        "query": "get block boundary types for splitting",
        "expected": "chunking/languages/base.py:588-597:method:LanguageChunker._get_block_boundary_types",
        "category": "algorithm",
        "top_5": [
            "chunking/languages/base.py:588-597:method:LanguageChunker._get_block_boundary_types",
            "chunking/languages/go.py:27-35:method:GoChunker._get_splittable_node_types",
            "chunking/languages/python.py:33-56:merged:PythonChunker._get_splittable_node_types",
            "tools/analyze_batch_results.py:133-147:function:normalize_chunk_id",
            "chunking/languages/base.py:638-686:method:LanguageChunker._create_split_chunk",
        ],
    },
    12: {
        "query": "CodeEmbedder class for embedding generation",
        "expected": "embeddings/embedder.py:303-1308:class:CodeEmbedder",
        "category": "exact_class",
        "top_5": [
            "embeddings/embedder.py:303-1308:class:CodeEmbedder",
            "embeddings/__init__.py:1-2:module",
            "embeddings/embedder.py:294-300:decorated_definition:EmbeddingResult",
            "embeddings/embedder.py:686-763:method:CodeEmbedder.embed_chunk",
            "search/reranking_engine.py:27-39:method:RerankingEngine.__init__",
        ],
    },
    13: {
        "query": "embedding model with SentenceTransformer",
        "expected": "embeddings/embedder.py:303-1308:class:CodeEmbedder",
        "category": "algorithm",
        "top_5": [
            "embeddings/embedder.py:465-476:merged:CodeEmbedder.model",
            "embeddings/embedder.py:686-763:method:CodeEmbedder.embed_chunk",
            "embeddings/embedder.py:303-1308:class:CodeEmbedder",
            "search/indexer.py:134-220:split_block:CodeIndexManager.add_embeddings",
            "search/indexer.py:221-237:split_block:CodeIndexManager.add_embeddings",
        ],
    },
    14: {
        "query": "IncrementalIndexer class for indexing",
        "expected": "search/incremental_indexer.py:190-340:split_block:IncrementalIndexer.incremental_index",
        "category": "exact_class",
        "top_5": [
            "search/incremental_indexer.py:59-1104:class:IncrementalIndexer",
            "search/incremental_indexer.py:385-394:split_block:IncrementalIndexer._full_index",
            "search/incremental_indexer.py:196-210:split_block:IncrementalIndexer.incremental_index",
            "search/incremental_indexer.py:212-340:split_block:IncrementalIndexer.incremental_index",
            "mcp_server/tools/index_handlers.py:130-176:function:_run_indexing",
        ],
    },
    15: {
        "query": "incremental indexing with snapshots",
        "expected": "search/incremental_indexer.py:190-340:split_block:IncrementalIndexer.incremental_index",
        "category": "algorithm",
        "top_5": [
            "merkle/__init__.py:1-9:module",
            "search/incremental_indexer.py:196-210:split_block:IncrementalIndexer.incremental_index",
            "search/incremental_indexer.py:212-340:split_block:IncrementalIndexer.incremental_index",
            "search/incremental_indexer.py:59-1104:class:IncrementalIndexer",
            "search/incremental_indexer.py:395-623:split_block:IncrementalIndexer._full_index",
        ],
    },
    16: {
        "query": "CommunityDetector class Louvain algorithm",
        "expected": "graph/community_detector.py:21-243:class:CommunityDetector",
        "category": "exact_class",
        "top_5": [
            "graph/community_detector.py:21-243:class:CommunityDetector",
            "graph/community_detector.py:46-152:split_block:CommunityDetector.detect_communities",
            "graph/community_detector.py:153-181:split_block:CommunityDetector.detect_communities",
            "graph/community_detector.py:35-43:method:CommunityDetector.__init__",
            "search/config.py:296-351:merged:ChunkingConfig",
        ],
    },
    17: {
        "query": "community detection with Louvain modularity",
        "expected": "graph/community_detector.py:21-243:class:CommunityDetector",
        "category": "algorithm",
        "top_5": [
            "graph/community_detector.py:21-243:class:CommunityDetector",
            "graph/community_detector.py:46-152:split_block:CommunityDetector.detect_communities",
            "graph/community_detector.py:153-181:split_block:CommunityDetector.detect_communities",
            "search/incremental_indexer.py:652-692:method:IncrementalIndexer._build_temp_graph",
            "search/graph_integration.py:162-239:split_block:GraphIntegration.build_graph_from_chunks",
        ],
    },
    18: {
        "query": "calculate MRR metric for evaluation",
        "expected": "tools/run_benchmark_mcp.py:47-159:function:run_benchmark",
        "category": "algorithm",
        "top_5": [
            "tools/benchmark_models.py:66-93:function:calculate_mrr",
            "tools/benchmark_chunking.py:101-128:merged:calculate_mrr",
            "tools/run_benchmark_mcp.py:39-44:function:calculate_mrr",
            "tools/run_benchmark_mcp.py:47-159:function:run_benchmark",
            "search/reranker.py:246-314:merged:RRFReranker._calculate_std",
        ],
    },
    19: {
        "query": "calculate_mrr function",
        "expected": "tools/benchmark_models.py:66-93:function:calculate_mrr",
        "category": "exact_function",
        "top_5": [
            "tools/benchmark_models.py:66-93:function:calculate_mrr",
            "tools/benchmark_chunking.py:101-128:merged:calculate_mrr",
            "tools/run_benchmark_mcp.py:39-44:function:calculate_mrr",
            "tools/benchmark_retrieval_quality.py:236-260:function:calculate_metrics_from_results",
            "tools/run_benchmark_mcp.py:47-159:function:run_benchmark",
        ],
    },
    20: {
        "query": "Mean Reciprocal Rank calculation",
        "expected": "tools/run_benchmark_mcp.py:39-44:function:calculate_mrr",
        "category": "algorithm",
        "top_5": [
            "tools/benchmark_chunking.py:101-115:function:calculate_mrr",
            "tools/benchmark_models.py:66-93:function:calculate_mrr",
            "tools/run_benchmark_mcp.py:39-44:function:calculate_mrr",
            "search/reranker.py:20-314:class:RRFReranker",
            "search/reranker.py:246-314:merged:RRFReranker._calculate_std",
        ],
    },
}

BATCH_3_RESULTS = {
    21: {
        "query": "SearchExecutor class for search",
        "expected": "search/hybrid_searcher.py:397-416:decorated_definition:HybridSearcher.stats",
        "category": "exact_class",
        "top_5": [
            "search/search_executor.py:22-402:class:SearchExecutor",
            "search/hybrid_searcher.py:396-416:decorated_definition:HybridSearcher.stats",
            "search/hybrid_searcher.py:44-1243:class:HybridSearcher",
            "search/config.py:180-251:merged:SearchModeConfig",
            "search/searcher.py:35-473:class:IntelligentSearcher",
        ],
    },
    22: {
        "query": "parallel BM25 and dense search execution",
        "expected": "search/search_executor.py:22-402:class:SearchExecutor",
        "category": "conceptual",
        "top_5": [
            "search/search_executor.py:22-402:class:SearchExecutor",
            "search/hybrid_searcher.py:311-328:method:HybridSearcher._load_indices_parallel",
            "search/hybrid_searcher.py:44-1243:class:HybridSearcher",
            "search/search_executor.py:181-225:merged:SearchExecutor._parallel_search",
            "search/search_executor.py:83-179:method:SearchExecutor.execute_single_hop",
        ],
    },
    23: {
        "query": "NeuralReranker class with CrossEncoder",
        "expected": "search/neural_reranker.py:17-159:class:NeuralReranker",
        "category": "exact_class",
        "top_5": [
            "search/neural_reranker.py:17-57:merged:NeuralReranker",
            "search/config.py:276-284:decorated_definition:RerankerConfig",
            "search/reranking_engine.py:24-284:class:RerankingEngine",
            "search/hybrid_searcher.py:436-447:decorated_definition:HybridSearcher.neural_reranker",
            "search/neural_reranker.py:59-76:decorated_definition:NeuralReranker.model",
        ],
    },
    24: {
        "query": "neural reranking with cross-encoder",
        "expected": "search/neural_reranker.py:17-159:class:NeuralReranker",
        "category": "algorithm",
        "top_5": [
            "search/neural_reranker.py:17-159:class:NeuralReranker",
            "search/neural_reranker.py:78-129:method:NeuralReranker.rerank",
            "search/config.py:276-284:decorated_definition:RerankerConfig",
            "search/reranking_engine.py:24-284:class:RerankingEngine",
            "search/neural_reranker.py:35-57:method:NeuralReranker.__init__",
        ],
    },
    25: {
        "query": "RerankingEngine class",
        "expected": "search/multi_hop_searcher.py:28-50:method:MultiHopSearcher.__init__",
        "category": "exact_class",
        "top_5": [
            "search/reranking_engine.py:24-284:class:RerankingEngine",
            "search/config.py:276-284:decorated_definition:RerankerConfig",
            "search/multi_hop_searcher.py:28-50:method:MultiHopSearcher.__init__",
            "search/search_executor.py:28-81:method:SearchExecutor.__init__",
            "search/reranking_engine.py:27-39:method:RerankingEngine.__init__",
        ],
    },
    26: {
        "query": "reranking search results for quality",
        "expected": [
            "search/reranking_engine.py:91-194:split_block:RerankingEngine.rerank_by_query",
            "search/reranker.py:35-136:method:RRFReranker.rerank",
        ],
        "category": "conceptual",
        "top_5": [
            "search/reranker.py:35-136:method:RRFReranker.rerank",
            "search/reranking_engine.py:24-284:class:RerankingEngine",
            "search/neural_reranker.py:17-159:class:NeuralReranker",
            "search/neural_reranker.py:78-129:method:NeuralReranker.rerank",
            "search/reranker.py:138-179:method:RRFReranker.rerank_simple",
        ],
    },
    27: {
        "query": "BM25SyncManager class for index sync",
        "expected": "search/bm25_sync.py:16-70:class:BM25SyncManager",
        "category": "exact_class",
        "top_5": [
            "search/bm25_sync.py:16-70:class:BM25SyncManager",
            "search/index_sync.py:16-431:class:IndexSynchronizer",
            "search/bm25_sync.py:19-25:method:BM25SyncManager.__init__",
            "search/hybrid_searcher.py:997-1002:method:HybridSearcher.resync_bm25_from_dense",
            "search/hybrid_searcher.py:993-995:method:HybridSearcher.validate_index_sync",
        ],
    },
    28: {
        "query": "BM25 index synchronization",
        "expected": "search/hybrid_searcher.py:993-995:method:HybridSearcher.validate_index_sync",
        "category": "conceptual",
        "top_5": [
            "search/hybrid_searcher.py:993-995:method:HybridSearcher.validate_index_sync",
            "search/bm25_sync.py:16-70:class:BM25SyncManager",
            "search/index_sync.py:16-431:class:IndexSynchronizer",
            "search/hybrid_searcher.py:997-1002:method:HybridSearcher.resync_bm25_from_dense",
            "search/hybrid_searcher.py:1004-1006:method:HybridSearcher.load_indices",
        ],
    },
    29: {
        "query": "IndexSynchronizer class",
        "expected": "search/hybrid_searcher.py:419-434:decorated_definition:HybridSearcher.index_synchronizer",
        "category": "exact_class",
        "top_5": [
            "search/index_sync.py:16-431:class:IndexSynchronizer",
            "search/bm25_sync.py:16-70:class:BM25SyncManager",
            "search/hybrid_searcher.py:418-434:decorated_definition:HybridSearcher.index_synchronizer",
            "search/hybrid_searcher.py:993-995:method:HybridSearcher.validate_index_sync",
            "search/hybrid_searcher.py:997-1002:method:HybridSearcher.resync_bm25_from_dense",
        ],
    },
    30: {
        "query": "synchronize BM25 and vector indices",
        "expected": "search/hybrid_searcher.py:993-995:method:HybridSearcher.validate_index_sync",
        "category": "conceptual",
        "top_5": [
            "search/bm25_sync.py:16-70:class:BM25SyncManager",
            "search/index_sync.py:16-431:class:IndexSynchronizer",
            "search/hybrid_searcher.py:993-995:method:HybridSearcher.validate_index_sync",
            "search/hybrid_searcher.py:1004-1006:method:HybridSearcher.load_indices",
            "search/hybrid_searcher.py:997-1002:method:HybridSearcher.resync_bm25_from_dense",
        ],
    },
}

BATCH_4_RESULTS = {
    31: {
        "query": "GraphIntegration class for code graph",
        "expected": "search/incremental_indexer.py:652-692:method:IncrementalIndexer._build_temp_graph",
        "category": "exact_class",
        "top_5": [
            "search/graph_integration.py:38-423:class:GraphIntegration",
            "search/incremental_indexer.py:652-692:method:IncrementalIndexer._build_temp_graph",
            "graph/__init__.py:1-40:module",
            "graph/call_graph_extractor.py:57-85:class:CallGraphExtractor",
            "search/ego_graph_retriever.py:18-169:class:EgoGraphRetriever",
        ],
    },
    32: {
        "query": "integrate call graph with search",
        "expected": "search/indexer.py:593-603:method:CodeIndexManager._add_to_graph",
        "category": "conceptual",
        "top_5": [
            "graph/__init__.py:1-40:module",
            "mcp_server/tools/search_handlers.py:627-692:split_block:handle_search_code",
            "search/hybrid_searcher.py:977-991:method:HybridSearcher.save_indices",
            "graph/call_graph_extractor.py:57-85:class:CallGraphExtractor",
            "search/indexer.py:593-603:method:CodeIndexManager._add_to_graph",
        ],
    },
    33: {
        "query": "ResultFactory class create search results",
        "expected": "search/result_factory.py:10-161:class:ResultFactory",
        "category": "exact_class",
        "top_5": [
            "search/result_factory.py:10-161:class:ResultFactory",
            "mcp_server/search_factory.py:19-206:class:SearchFactory",
            "search/result_factory.py:88-125:decorated_definition:ResultFactory.from_direct_lookup",
            "search/result_factory.py:22-86:merged:ResultFactory.from_bm25_results",
            "mcp_server/search_factory.py:216-259:merged:get_search_factory",
        ],
    },
    34: {
        "query": "create SearchResult from similarity scores",
        "expected": "search/result_factory.py:128-161:decorated_definition:ResultFactory.from_similarity_results",
        "category": "conceptual",
        "top_5": [
            "search/result_factory.py:127-161:decorated_definition:ResultFactory.from_similarity_results",
            "search/searcher.py:14-32:decorated_definition:SearchResult",
            "search/searcher.py:142-202:merged:IntelligentSearcher._create_search_result",
            "search/bm25_index.py:322-367:method:BM25Index.search",
            "search/neural_reranker.py:78-129:method:NeuralReranker.rerank",
        ],
    },
    35: {
        "query": "ModelPoolManager class for models",
        "expected": "mcp_server/model_pool_manager.py:330-339:function:get_model_pool_manager",
        "category": "exact_class",
        "top_5": [
            "mcp_server/model_pool_manager.py:19-323:class:ModelPoolManager",
            "mcp_server/model_pool_manager.py:330-339:function:get_model_pool_manager",
            "mcp_server/model_pool_manager.py:381-388:function:reset_pool_manager",
            "mcp_server/model_pool_manager.py:351-378:merged:get_embedder",
            "mcp_server/tools/status_handlers.py:296-332:decorated_definition:handle_list_embedding_models",
        ],
    },
    36: {
        "query": "manage multiple embedding models",
        "expected": [
            "mcp_server/tools/status_handlers.py:297-332:decorated_definition:handle_list_embedding_models",
            "mcp_server/model_pool_manager.py:19-323:class:ModelPoolManager",
        ],
        "category": "conceptual",
        "top_5": [
            "embeddings/embedder.py:303-1308:class:CodeEmbedder",
            "mcp_server/model_pool_manager.py:19-323:class:ModelPoolManager",
            "mcp_server/model_pool_manager.py:211-323:split_block:ModelPoolManager.get_embedder",
            "mcp_server/model_pool_manager.py:133-210:split_block:ModelPoolManager.get_embedder",
            "embeddings/embedder.py:768-835:split_block:CodeEmbedder.embed_chunks",
        ],
    },
    37: {
        "query": "calculate optimal batch size for embedding",
        "expected": "embeddings/embedder.py:135-244:split_block:calculate_optimal_batch_size",
        "category": "algorithm",
        "top_5": [
            "embeddings/embedder.py:143-181:split_block:calculate_optimal_batch_size",
            "embeddings/embedder.py:183-244:split_block:calculate_optimal_batch_size",
            "search/gpu_monitor.py:48-51:method:GPUMemoryMonitor.estimate_batch_memory",
            "search/config.py:164-284:merged:EmbeddingConfig",
            "embeddings/embedder.py:837-1021:split_block:CodeEmbedder.embed_chunks",
        ],
    },
    38: {
        "query": "batch size optimization based on VRAM",
        "expected": "embeddings/embedder.py:135-244:split_block:calculate_optimal_batch_size",
        "category": "conceptual",
        "top_5": [
            "embeddings/embedder.py:143-181:split_block:calculate_optimal_batch_size",
            "embeddings/embedder.py:183-244:split_block:calculate_optimal_batch_size",
            "embeddings/embedder.py:247-291:function:parse_vram_gb_from_registry",
            "search/gpu_monitor.py:17-51:class:GPUMemoryMonitor",
            "search/gpu_monitor.py:48-51:method:GPUMemoryMonitor.estimate_batch_memory",
        ],
    },
    39: {
        "query": "abstract base class for language chunkers",
        "expected": "chunking/languages/csharp.py:10-82:class:CSharpChunker",
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:105-949:class:LanguageChunker",
            "chunking/languages/csharp.py:10-82:class:CSharpChunker",
            "chunking/tree_sitter.py:187-385:class:TreeSitterChunker",
            "chunking/languages/cpp.py:10-82:class:CppChunker",
            "chunking/languages/javascript.py:10-58:class:JavaScriptChunker",
        ],
    },
    40: {
        "query": "IntelligentSearcher class",
        "expected": "mcp_server/tools/code_relationship_analyzer.py:236-264:method:CodeRelationshipAnalyzer.__init__",
        "category": "exact_class",
        "top_5": [
            "search/searcher.py:35-473:class:IntelligentSearcher",
            "search/base_searcher.py:17-137:class:BaseSearcher",
            "mcp_server/tools/code_relationship_analyzer.py:236-264:method:CodeRelationshipAnalyzer.__init__",
            "mcp_server/search_factory.py:19-206:class:SearchFactory",
            "mcp_server/tools/code_relationship_analyzer.py:233-1067:class:CodeRelationshipAnalyzer",
        ],
    },
}

BATCH_5_RESULTS = {
    41: {
        "query": "intelligent search with embedder",
        "expected": [
            "mcp_server/tools/search_handlers.py:429-692:split_block:handle_search_code",
            "search/hybrid_searcher.py:170-238:method:HybridSearcher._init_search_components",
        ],
        "category": "conceptual",
        "top_5": [
            "search/hybrid_searcher.py:170-238:method:HybridSearcher._init_search_components",
            "search/multi_hop_searcher.py:28-50:method:MultiHopSearcher.__init__",
            "search/search_executor.py:277-328:decorated_definition:SearchExecutor.search_dense",
            "search/base_searcher.py:17-137:class:BaseSearcher",
            "search/hybrid_searcher.py:47-168:method:HybridSearcher.__init__",
        ],
    },
    42: {
        "query": "how chunks are merged based on size constraints",
        "expected": "chunking/languages/base.py:243-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        "category": "conceptual",
        "top_5": [
            "search/config.py:296-351:merged:ChunkingConfig",
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
        ],
    },
    43: {
        "query": "AST boundary detection for function splitting",
        "expected": "chunking/languages/base.py:638-686:method:LanguageChunker._create_split_chunk",
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:588-597:method:LanguageChunker._get_block_boundary_types",
            "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
            "chunking/languages/base.py:138-145:decorated_definition:LanguageChunker._get_splittable_node_types",
            "chunking/languages/base.py:638-686:method:LanguageChunker._create_split_chunk",
            "chunking/languages/python.py:33-56:merged:PythonChunker._get_splittable_node_types",
        ],
    },
    44: {
        "query": "prevent cross-file chunk merging",
        "expected": "chunking/languages/base.py:381-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "search/parallel_chunker.py:232-237:split_block:ParallelChunker.chunk_files",
            "search/parallel_chunker.py:69-231:split_block:ParallelChunker.chunk_files",
        ],
    },
    45: {
        "query": "token vs character size estimation",
        "expected": "chunking/languages/base.py:22-56:function:estimate_tokens",
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:22-56:function:estimate_tokens",
            "chunking/languages/base.py:59-75:function:estimate_characters",
            "search/config.py:296-351:merged:ChunkingConfig",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
            "chunking/languages/base.py:252-315:split_block:LanguageChunker._greedy_merge_small_chunks",
        ],
    },
    46: {
        "query": "merge chunks with same parent_class or community_id",
        "expected": "chunking/languages/base.py:381-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:195-241:method:LanguageChunker._create_merged_chunk",
            "chunking/languages/base.py:317-378:split_block:LanguageChunker._greedy_merge_small_chunks",
        ],
    },
    47: {
        "query": "split large functions at for/if/while boundaries",
        "expected": [
            "chunking/languages/python.py:41-56:method:PythonChunker._get_block_boundary_types",
            "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
        ],
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:688-765:method:LanguageChunker._split_large_node",
            "chunking/languages/base.py:638-686:method:LanguageChunker._create_split_chunk",
            "chunking/languages/base.py:588-597:method:LanguageChunker._get_block_boundary_types",
            "chunking/languages/python.py:15-307:class:PythonChunker",
            "chunking/languages/base.py:819-924:method:LanguageChunker.chunk_code",
        ],
    },
    48: {
        "query": "community-based boundaries for merging",
        "expected": "chunking/languages/base.py:381-586:split_block:LanguageChunker.remerge_chunks_with_communities",
        "category": "conceptual",
        "top_5": [
            "chunking/languages/base.py:389-461:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:462-509:split_block:LanguageChunker.remerge_chunks_with_communities",
            "chunking/languages/base.py:510-586:split_block:LanguageChunker.remerge_chunks_with_communities",
            "search/incremental_indexer.py:694-766:method:IncrementalIndexer._regenerate_chunk_ids",
            "search/config.py:296-351:merged:ChunkingConfig",
        ],
    },
    49: {
        "query": "Louvain community detection on code graph",
        "expected": "graph/community_detector.py:21-243:class:CommunityDetector",
        "category": "conceptual",
        "top_5": [
            "graph/community_detector.py:21-243:class:CommunityDetector",
            "graph/community_detector.py:46-152:split_block:CommunityDetector.detect_communities",
            "graph/community_detector.py:153-181:split_block:CommunityDetector.detect_communities",
            "graph/community_detector.py:35-43:method:CommunityDetector.__init__",
            "search/graph_integration.py:162-239:split_block:GraphIntegration.build_graph_from_chunks",
        ],
    },
    50: {
        "query": "reciprocal rank fusion for search",
        "expected": "search/reranker.py:20-314:class:RRFReranker",
        "category": "conceptual",
        "top_5": [
            "search/reranker.py:20-314:class:RRFReranker",
            "search/neural_reranker.py:17-159:class:NeuralReranker",
            "tools/benchmark_chunking.py:101-115:function:calculate_mrr",
            "tools/benchmark_quick_test.py:34-39:function:calculate_mrr",
            "tools/run_benchmark_mcp.py:39-44:function:calculate_mrr",
        ],
    },
}


def normalize_chunk_id(chunk_id):
    """Normalize chunk_id to handle split blocks.

    Example: chunking/languages/base.py:252-315 and 317-378 both belong to
    the same logical function that was split, so we normalize to the base symbol.
    """
    # Extract file and symbol name
    parts = chunk_id.split(":")
    if len(parts) < 4:
        return chunk_id

    file_path = parts[0]
    symbol = parts[3]  # e.g., "LanguageChunker._greedy_merge_small_chunks"

    return f"{file_path}:{symbol}"


def check_match(expected, retrieved_list, fuzzy=True):
    """Check if expected chunk is in retrieved list.

    Args:
        expected: Expected chunk_id
        retrieved_list: List of retrieved chunk_ids
        fuzzy: If True, use fuzzy matching for split blocks

    Returns:
        tuple: (found, rank) where rank is 1-indexed (or None if not found)
    """
    # Exact match
    for i, retrieved in enumerate(retrieved_list, 1):
        if retrieved == expected:
            return True, i

    if fuzzy:
        # Fuzzy match for split blocks
        expected_norm = normalize_chunk_id(expected)
        for i, retrieved in enumerate(retrieved_list, 1):
            retrieved_norm = normalize_chunk_id(retrieved)
            if expected_norm == retrieved_norm:
                return True, i

    return False, None


def analyze_results(batch_num=1):
    """Analyze batch results.

    Args:
        batch_num: 1 for batch 1, 2 for batch 2, 3 for batch 3, 4 for batch 4, 5 for batch 5, 0 for all batches combined
    """
    if batch_num == 1:
        batch_data = BATCH_1_RESULTS
        batch_name = "BATCH 1"
    elif batch_num == 2:
        batch_data = BATCH_2_RESULTS
        batch_name = "BATCH 2"
    elif batch_num == 3:
        batch_data = BATCH_3_RESULTS
        batch_name = "BATCH 3"
    elif batch_num == 4:
        batch_data = BATCH_4_RESULTS
        batch_name = "BATCH 4"
    elif batch_num == 5:
        batch_data = BATCH_5_RESULTS
        batch_name = "BATCH 5"
    elif batch_num == 0:
        batch_data = {
            **BATCH_1_RESULTS,
            **BATCH_2_RESULTS,
            **BATCH_3_RESULTS,
            **BATCH_4_RESULTS,
            **BATCH_5_RESULTS,
        }
        batch_name = "ALL BATCHES (1-5)"
    else:
        raise ValueError(f"Invalid batch_num: {batch_num}")

    print("=" * 80)
    print(f"{batch_name} RESULTS ANALYSIS ({len(batch_data)} queries)")
    print("=" * 80)
    print()

    stats = {
        "total": 0,
        "exact_match": 0,
        "fuzzy_match": 0,
        "miss": 0,
        "rank_1": 0,
        "rank_2_5": 0,
        "mrr_sum": 0.0,
    }

    detailed_results = []

    for query_id, data in batch_data.items():
        stats["total"] += 1
        query = data["query"]
        expected = data["expected"]
        category = data["category"]
        top_5 = data["top_5"]

        # Support multiple expected chunk IDs (for ambiguous queries)
        if isinstance(expected, str):
            expected_list = [expected]
        else:
            expected_list = expected

        # Check if ANY expected chunk is found (exact or fuzzy)
        exact_found = False
        fuzzy_found = False
        exact_rank = None
        fuzzy_rank = None

        for exp_chunk_id in expected_list:
            # Check exact match
            found, rank = check_match(exp_chunk_id, top_5, fuzzy=False)
            if found and (exact_rank is None or rank < exact_rank):
                exact_found = True
                exact_rank = rank

            # Check fuzzy match
            found, rank = check_match(exp_chunk_id, top_5, fuzzy=True)
            if found and (fuzzy_rank is None or rank < fuzzy_rank):
                fuzzy_found = True
                fuzzy_rank = rank

        if exact_found:
            stats["exact_match"] += 1
            if exact_rank == 1:
                stats["rank_1"] += 1
            else:
                stats["rank_2_5"] += 1
            stats["mrr_sum"] += 1.0 / exact_rank
            status = f"[OK] EXACT (rank {exact_rank})"
        elif fuzzy_found:
            stats["fuzzy_match"] += 1
            if fuzzy_rank == 1:
                stats["rank_1"] += 1
            else:
                stats["rank_2_5"] += 1
            stats["mrr_sum"] += 1.0 / fuzzy_rank
            status = f"[~] FUZZY (rank {fuzzy_rank})"
        else:
            stats["miss"] += 1
            status = "[X] MISS"

        result = {
            "query_id": query_id,
            "query": query,
            "category": category,
            "expected": expected,
            "retrieved_rank_1": top_5[0] if top_5 else None,
            "exact_found": exact_found,
            "fuzzy_found": fuzzy_found,
            "rank": exact_rank
            if exact_found
            else (fuzzy_rank if fuzzy_found else None),
            "status": status,
        }

        detailed_results.append(result)

        print(f"[{query_id:2d}] {status:20s} {category:15s}")
        print(f"     Query: {query}")
        if isinstance(expected, list):
            print(f"     Expected (any of {len(expected)}):")
            for exp in expected:
                print(f"       - {exp}")
        else:
            print(f"     Expected: {expected}")
        if top_5:
            print(f"     Got (rank 1): {top_5[0]}")
        print()

    # Calculate metrics
    hit_rate = (stats["exact_match"] + stats["fuzzy_match"]) / stats["total"]
    exact_rate = stats["exact_match"] / stats["total"]
    mrr = stats["mrr_sum"] / stats["total"]

    print("=" * 80)
    print("METRICS SUMMARY")
    print("=" * 80)
    print(f"Total Queries:        {stats['total']}")
    print(f"Exact Matches:        {stats['exact_match']} ({exact_rate:.1%})")
    print(f"Fuzzy Matches:        {stats['fuzzy_match']}")
    print(
        f"Total Hits:           {stats['exact_match'] + stats['fuzzy_match']} ({hit_rate:.1%})"
    )
    print(f"Misses:               {stats['miss']}")
    print()
    print("Rank Distribution:")
    print(
        f"  Rank 1:             {stats['rank_1']} ({stats['rank_1'] / stats['total']:.1%})"
    )
    print(
        f"  Rank 2-5:           {stats['rank_2_5']} ({stats['rank_2_5'] / stats['total']:.1%})"
    )
    print()
    print(f"Mean Reciprocal Rank: {mrr:.4f}")
    print("=" * 80)
    print()

    # Save detailed results
    output = {
        "batch": batch_num if batch_num > 0 else "all",
        "total_queries": stats["total"],
        "metrics": {
            "exact_matches": stats["exact_match"],
            "fuzzy_matches": stats["fuzzy_match"],
            "total_hits": stats["exact_match"] + stats["fuzzy_match"],
            "misses": stats["miss"],
            "hit_rate": round(hit_rate, 4),
            "exact_rate": round(exact_rate, 4),
            "mrr": round(mrr, 4),
            "rank_1_count": stats["rank_1"],
            "rank_2_5_count": stats["rank_2_5"],
        },
        "results": detailed_results,
    }

    if batch_num == 0:
        output_file = "results/all_batches_analysis.json"
    else:
        output_file = f"results/batch_{batch_num}_analysis.json"

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Detailed results saved to: {output_path}")

    return output


if __name__ == "__main__":
    import sys

    batch = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    analyze_results(batch)
