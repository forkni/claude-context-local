# Enhanced Commit Workflow Analysis Report

**Workflow**: Enhanced Commit
**Date**: Fri, Dec 19, 2025  8:52:15 PM
**Branch**: development
**Status**: [OK] SUCCESS

## Summary
Successfully committed changes with full validation and logging.

## Files Committed

A	chunking/dedent_utils.py
A	chunking/language_registry.py
M	chunking/multi_language_chunker.py
A	logs/commit_enhanced_analysis_20251219_092921.md
M	pyproject.toml
A	search/bm25_sync.py
M	search/hybrid_searcher.py
M	search/incremental_indexer.py
M	search/multi_hop_searcher.py
A	search/parallel_chunker.py
M	search/result_factory.py
A	search/search_executor.py
M	tests/conftest.py
A	tests/unit/chunking/__init__.py
R100	tests/unit/test_multi_language.py	tests/unit/chunking/test_multi_language.py
R100	tests/unit/test_smart_dedent.py	tests/unit/chunking/test_smart_dedent.py
R100	tests/unit/test_tree_sitter.py	tests/unit/chunking/test_tree_sitter.py
A	tests/unit/embeddings/__init__.py
R100	tests/unit/test_embedder.py	tests/unit/embeddings/test_embedder.py
R100	tests/unit/test_model_cache.py	tests/unit/embeddings/test_model_cache.py
R100	tests/unit/test_model_loader.py	tests/unit/embeddings/test_model_loader.py
R100	tests/unit/test_model_selection.py	tests/unit/embeddings/test_model_selection.py
R100	tests/unit/test_query_cache.py	tests/unit/embeddings/test_query_cache.py
A	tests/unit/graph/__init__.py
R100	tests/unit/test_assignment_tracking.py	tests/unit/graph/test_assignment_tracking.py
R100	tests/unit/test_call_graph_extraction.py	tests/unit/graph/test_call_graph_extraction.py
R100	tests/unit/test_call_resolution.py	tests/unit/graph/test_call_resolution.py
R100	tests/unit/test_entity_tracking_extractors.py	tests/unit/graph/test_entity_tracking_extractors.py
R100	tests/unit/test_graph_storage.py	tests/unit/graph/test_graph_storage.py
R100	tests/unit/test_import_resolution.py	tests/unit/graph/test_import_resolution.py
R100	tests/unit/test_priority1_extractors.py	tests/unit/graph/test_priority1_extractors.py
R100	tests/unit/test_priority2_extractors.py	tests/unit/graph/test_priority2_extractors.py
R100	tests/unit/test_qualified_chunk_ids.py	tests/unit/graph/test_qualified_chunk_ids.py
R100	tests/unit/test_relationship_types.py	tests/unit/graph/test_relationship_types.py
R100	tests/unit/test_tier1_extractors.py	tests/unit/graph/test_tier1_extractors.py
R100	tests/unit/test_type_annotation_resolution.py	tests/unit/graph/test_type_annotation_resolution.py
A	tests/unit/mcp_server/__init__.py
R100	tests/unit/test_cleanup_queue.py	tests/unit/mcp_server/test_cleanup_queue.py
R100	tests/unit/test_code_relationship_analyzer.py	tests/unit/mcp_server/test_code_relationship_analyzer.py
R100	tests/unit/test_config_sync.py	tests/unit/mcp_server/test_config_sync.py
R100	tests/unit/test_decorators.py	tests/unit/mcp_server/test_decorators.py
R100	tests/unit/test_mcp_server.py	tests/unit/mcp_server/test_mcp_server.py
R100	tests/unit/test_project_persistence.py	tests/unit/mcp_server/test_project_persistence.py
R100	tests/unit/test_services.py	tests/unit/mcp_server/test_services.py
A	tests/unit/mcp_server/test_tool_handlers.py
A	tests/unit/merkle/__init__.py
R100	tests/unit/test_merkle.py	tests/unit/merkle/test_merkle.py
A	tests/unit/search/__init__.py
R100	tests/unit/test_batch_operations.py	tests/unit/search/test_batch_operations.py
R100	tests/unit/test_bm25_index.py	tests/unit/search/test_bm25_index.py
R100	tests/unit/test_bm25_population.py	tests/unit/search/test_bm25_population.py
R100	tests/unit/test_faiss_vector_index.py	tests/unit/search/test_faiss_vector_index.py
R100	tests/unit/test_filter_engine.py	tests/unit/search/test_filter_engine.py
R100	tests/unit/test_filters.py	tests/unit/search/test_filters.py
R100	tests/unit/test_gpu_monitor.py	tests/unit/search/test_gpu_monitor.py
R100	tests/unit/test_graph_integration.py	tests/unit/search/test_graph_integration.py
R096	tests/unit/test_hybrid_search.py	tests/unit/search/test_hybrid_search.py
R100	tests/unit/test_incremental_indexer.py	tests/unit/search/test_incremental_indexer.py
R100	tests/unit/test_index_sync.py	tests/unit/search/test_index_sync.py
R100	tests/unit/test_metadata_store.py	tests/unit/search/test_metadata_store.py
R097	tests/unit/test_multi_hop_searcher.py	tests/unit/search/test_multi_hop_searcher.py
R100	tests/unit/test_neural_reranker.py	tests/unit/search/test_neural_reranker.py
R100	tests/unit/test_path_normalization.py	tests/unit/search/test_path_normalization.py
R100	tests/unit/test_query_router.py	tests/unit/search/test_query_router.py
R100	tests/unit/test_reranker.py	tests/unit/search/test_reranker.py
R100	tests/unit/test_reranking_engine.py	tests/unit/search/test_reranking_engine.py
R078	tests/unit/test_result_factory.py	tests/unit/search/test_result_factory.py
R100	tests/unit/test_search_config.py	tests/unit/search/test_search_config.py
R100	tests/unit/test_vram_manager.py	tests/unit/search/test_vram_manager.py
R100	tests/unit/test_weight_optimizer.py	tests/unit/search/test_weight_optimizer.py
M	tools/cleanup_orphaned_projects.py
M	tools/summarize_audit.py

## Commit Details

- **Hash**: 1b668ab9c8824343680770c61875c5500852c242
- **Message**: refactor: Reorganize tests and extract utility modules (3-part refactoring)
- **Author**: forkni
- **Date**: Fri Dec 19 20:52:15 2025 -0500

## Validations Passed

- [OK] No local-only files committed (CLAUDE.md, MEMORY.md, _archive)
- [OK] Branch-specific validations passed
- [OK] Code quality checks passed
- [OK] Conventional commit format validated

## Logs

- Execution log: `logs/commit_enhanced_20251219_205144.log`
- Analysis report: `logs/commit_enhanced_analysis_20251219_205144.md`

