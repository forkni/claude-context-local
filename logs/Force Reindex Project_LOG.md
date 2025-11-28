=== Claude Context MCP Server Launcher ===
[Hybrid Search Enabled - All Modes Operational]

[Runtime Status]
Model: [MULTI-MODEL] Qwen3-Embedding-0.6B (1024d, 2.3GB)
Multi-model routing: BGE-M3 + Qwen3 + CodeRankEmbed (5.3GB)

What would you like to do?

  1. Quick Start Server (Default Settings)
  2. Installation & Setup
  3. Search Configuration
  4. Performance Tools
  5. Project Management
  6. Advanced Options
  7. Help & Documentation
  M. Quick Model Switch (Code vs General)
  8. Exit

Select option (1-8, M): 5

=== Project Management ===

[Multi-Model Mode: Disabled]

  1. Index New Project
  2. Re-index Existing Project (Incremental)
  3. Force Re-index Existing Project (Full)
  4. List Indexed Projects
  5. Clear Project Indexes
  6. View Storage Statistics
  7. Switch to Project
  8. Back to Main Menu

Select option (1-8): 1

=== Index New Project ===

Enter the full path to the project directory to index.

Examples:
  C:\Projects\MyProject
  D:\Code\WebApp
  F:\Development\TouchDesigner\MyToeFile

Project path (or press Enter to cancel): F:\RD_PROJECTS\COMPONENTS\claude-context-local

[INFO] Indexing new project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
[INFO] This will create a new index and Merkle snapshot
[INFO] Mode: New (first-time full index)

======================================================================
PROJECT INDEXING
======================================================================
Path: F:\RD_PROJECTS\COMPONENTS\claude-context-local
Mode: New (first-time full index)
Incremental: False
Multi-Model: Enabled (Qwen3, BGE-M3, CodeRankEmbed)
======================================================================

[INFO] Starting indexing...

15:42:09 - [INDEX] directory=F:\RD_PROJECTS\COMPONENTS\claude-context-local, incremental=False, multi_model=True
15:42:09 - Multi-model batch indexing for: F:\RD_PROJECTS\COMPONENTS\claude-context-local
15:42:09 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:09 - Search mode: semantic, hybrid enabled: True
15:42:09 - Indexing with model: Qwen/Qwen3-Embedding-0.6B (qwen3)
15:42:09 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:09 - Search mode: semantic, hybrid enabled: True
15:42:09 - Saved search config to C:\Users\Inter/.claude_code_search/search_config.json
15:42:09 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:09 - Search mode: semantic, hybrid enabled: True
15:42:09 - [CONFIG] Using config default model: Qwen/Qwen3-Embedding-0.6B
15:42:09 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_qwen3-0.6b_1024d (model: Qwen/Qwen3-Embedding-0.6B, dimension: 1024d)
15:42:09 - Call graph extraction enabled for Python
15:42:09 - Phase 3: Initialized 3 relationship extractors
15:42:09 - Lazy loading qwen3 (Qwen/Qwen3-Embedding-0.6B)...
15:42:09 - ✓ qwen3 loaded successfully
15:42:09 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25 (stopwords=True, stemming=True)
15:42:09 - [INIT] BM25Index created successfully
15:42:09 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
15:42:09 - No existing BM25 index found
15:42:09 - [INIT] No existing BM25 index found, starting fresh
15:42:09 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
15:42:09 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
15:42:09 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
15:42:09 - Creating new index
15:42:09 - [INIT] No existing dense index found, starting fresh
15:42:09 - [INIT] HybridSearcher initialized - BM25: 0 docs, Dense: 0 vectors
15:42:09 - Creating new index
15:42:09 - Creating new index
15:42:09 - [INIT] Ready status: BM25=False, Dense=False, Overall=False
15:42:09 - Created fresh HybridSearcher for Qwen/Qwen3-Embedding-0.6B at C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index
15:42:09 - Performing full index for claude-context-local
15:42:09 - [FULL_INDEX] Deleting old snapshot for current model: claude-context-local
15:42:09 - [FULL_INDEX] Deleted old snapshot for current model
15:42:09 - Clearing hybrid indices
15:42:09 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index, project_id=claude-context-local_caf2e75a_qwen3-0.6b
15:42:09 - Call graph storage initialized for project: claude-context-local_caf2e75a_qwen3-0.6b
15:42:09 - Successfully cleared hybrid indices
15:42:09 - Found 136 supported files out of 343 total files
15:42:09 -   Supported: chunking\__init__.py
15:42:09 -   Supported: chunking\multi_language_chunker.py
15:42:09 -   Supported: chunking\python_ast_chunker.py
15:42:09 -   Supported: chunking\tree_sitter.py
15:42:09 -   Supported: embeddings\__init__.py
15:42:09 -   Supported: embeddings\embedder.py
15:42:09 -   Supported: graph\__init__.py
15:42:09 -   Supported: graph\call_graph_extractor.py
15:42:09 -   Supported: graph\graph_queries.py
15:42:09 -   Supported: graph\graph_storage.py
15:42:09 -   Supported: graph\relationship_extractors\__init__.py
15:42:09 -   Supported: graph\relationship_extractors\base_extractor.py
15:42:09 -   Supported: graph\relationship_extractors\import_extractor.py
15:42:09 -   Supported: graph\relationship_extractors\inheritance_extractor.py
15:42:09 -   Supported: graph\relationship_extractors\type_extractor.py
15:42:09 -   Supported: graph\relationship_types.py
15:42:09 -   Supported: mcp_server\__init__.py
15:42:09 -   Supported: mcp_server\archived\server_lowlevel.py
15:42:09 -   Supported: mcp_server\archived\server_lowlevel_complete.py
15:42:09 -   Supported: mcp_server\archived\server_lowlevel_minimal.py
15:42:09 -   Supported: mcp_server\guidance.py
15:42:09 -   Supported: mcp_server\metrics.py
15:42:09 -   Supported: mcp_server\server.py
15:42:09 -   Supported: mcp_server\tool_handlers.py
15:42:09 -   Supported: mcp_server\tool_registry.py
15:42:09 -   Supported: mcp_server\tools\__init__.py
15:42:09 -   Supported: mcp_server\tools\code_relationship_analyzer.py
15:42:09 -   Supported: merkle\__init__.py
15:42:09 -   Supported: merkle\change_detector.py
15:42:09 -   Supported: merkle\merkle_dag.py
15:42:09 -   Supported: merkle\snapshot_manager.py
15:42:09 -   Supported: scripts\__init__.py
15:42:09 -   Supported: scripts\list_projects_display.py
15:42:09 -   Supported: scripts\list_projects_parseable.py
15:42:09 -   Supported: scripts\manual_configure.py
15:42:09 -   Supported: scripts\verify_hf_auth.py
15:42:09 -   Supported: scripts\verify_installation.py
15:42:09 -   Supported: search\__init__.py
15:42:09 -   Supported: search\bm25_index.py
15:42:09 -   Supported: search\config.py
15:42:09 -   Supported: search\hybrid_searcher.py
15:42:09 -   Supported: search\incremental_indexer.py
15:42:09 -   Supported: search\indexer.py
15:42:09 -   Supported: search\query_router.py
15:42:09 -   Supported: search\reranker.py
15:42:09 -   Supported: search\searcher.py
15:42:09 -   Supported: tests\__init__.py
15:42:09 -   Supported: tests\benchmarks\capture_baseline.py
15:42:09 -   Supported: tests\conftest.py
15:42:09 -   Supported: tests\fixtures\__init__.py
15:42:09 -   Supported: tests\fixtures\installation_mocks.py
15:42:09 -   Supported: tests\fixtures\sample_code.py
15:42:09 -   Supported: tests\integration\__init__.py
15:42:09 -   Supported: tests\integration\check_auth.py
15:42:09 -   Supported: tests\integration\run_hybrid_tests.py
15:42:09 -   Supported: tests\integration\test_auto_reindex.py
15:42:09 -   Supported: tests\integration\test_complete_workflow.py
15:42:09 -   Supported: tests\integration\test_critical_fixes.py
15:42:09 -   Supported: tests\integration\test_cuda_detection.py
15:42:09 -   Supported: tests\integration\test_direct_indexing.py
15:42:09 -   Supported: tests\integration\test_encoding_validation.py
15:42:09 -   Supported: tests\integration\test_full_flow.py
15:42:09 -   Supported: tests\integration\test_glsl_chunker_only.py
15:42:09 -   Supported: tests\integration\test_glsl_complete.py
15:42:09 -   Supported: tests\integration\test_glsl_without_embedder.py
15:42:09 -   Supported: tests\integration\test_graph_search.py
15:42:09 -   Supported: tests\integration\test_hf_access.py
15:42:09 -   Supported: tests\integration\test_hybrid_search_integration.py
15:42:09 -   Supported: tests\integration\test_incremental_indexing.py
15:42:09 -   Supported: tests\integration\test_installation.py
15:42:09 -   Supported: tests\integration\test_installation_flow.py
15:42:09 -   Supported: tests\integration\test_mcp_functionality.py
15:42:09 -   Supported: tests\integration\test_mcp_indexing.py
15:42:09 -   Supported: tests\integration\test_model_switching.py
15:42:09 -   Supported: tests\integration\test_multi_hop_flow.py
15:42:09 -   Supported: tests\integration\test_phase3_relationships.py
15:42:09 -   Supported: tests\integration\test_semantic_search.py
15:42:09 -   Supported: tests\integration\test_stemming_integration.py
15:42:09 -   Supported: tests\integration\test_system.py
15:42:09 -   Supported: tests\integration\test_token_efficiency_workflow.py
15:42:09 -   Supported: tests\test_data\glsl_project\fragment_shader.frag
15:42:09 -   Supported: tests\test_data\glsl_project\simple_shader.glsl
15:42:09 -   Supported: tests\test_data\glsl_project\vertex_shader.vert
15:42:09 -   Supported: tests\test_data\multi_language\App.svelte
15:42:09 -   Supported: tests\test_data\multi_language\calculator.c
15:42:09 -   Supported: tests\test_data\multi_language\Calculator.cpp
15:42:09 -   Supported: tests\test_data\multi_language\Calculator.cs
15:42:09 -   Supported: tests\test_data\multi_language\calculator.go
15:42:09 -   Supported: tests\test_data\multi_language\Calculator.java
15:42:09 -   Supported: tests\test_data\multi_language\calculator.rs
15:42:09 -   Supported: tests\test_data\multi_language\Component.jsx
15:42:09 -   Supported: tests\test_data\multi_language\Component.tsx
15:42:09 -   Supported: tests\test_data\multi_language\example.js
15:42:09 -   Supported: tests\test_data\multi_language\example.py
15:42:09 -   Supported: tests\test_data\multi_language\example.ts
15:42:09 -   Supported: tests\test_data\python_project\main.py
15:42:09 -   Supported: tests\test_data\python_project\src\api\handlers.py
15:42:09 -   Supported: tests\test_data\python_project\src\auth\authenticator.py
15:42:09 -   Supported: tests\test_data\python_project\src\database\connection.py
15:42:09 -   Supported: tests\test_data\python_project\src\utils\helpers.py
15:42:09 -   Supported: tests\test_data\python_project\src\utils\validators.py
15:42:09 -   Supported: tests\unit\__init__.py
15:42:09 -   Supported: tests\unit\test_bm25_index.py
15:42:09 -   Supported: tests\unit\test_bm25_population.py
15:42:09 -   Supported: tests\unit\test_call_graph_extraction.py
15:42:09 -   Supported: tests\unit\test_code_relationship_analyzer.py
15:42:09 -   Supported: tests\unit\test_embedder.py
15:42:09 -   Supported: tests\unit\test_evaluation.py
15:42:09 -   Supported: tests\unit\test_graph_storage.py
15:42:09 -   Supported: tests\unit\test_hybrid_search.py
15:42:09 -   Supported: tests\unit\test_imports.py
15:42:09 -   Supported: tests\unit\test_incremental_indexer.py
15:42:09 -   Supported: tests\unit\test_mcp_server.py
15:42:09 -   Supported: tests\unit\test_merkle.py
15:42:09 -   Supported: tests\unit\test_model_selection.py
15:42:09 -   Supported: tests\unit\test_multi_language.py
15:42:09 -   Supported: tests\unit\test_path_normalization.py
15:42:09 -   Supported: tests\unit\test_priority1_extractors.py
15:42:09 -   Supported: tests\unit\test_relationship_types.py
15:42:09 -   Supported: tests\unit\test_reranker.py
15:42:09 -   Supported: tests\unit\test_search_config.py
15:42:09 -   Supported: tests\unit\test_token_efficiency.py
15:42:09 -   Supported: tests\unit\test_tool_handlers.py
15:42:09 -   Supported: tests\unit\test_tree_sitter.py
15:42:09 -   Supported: tools\batch_index.py
15:42:09 -   Supported: tools\build_complete_server.py
15:42:09 -   Supported: tools\build_lowlevel_server.py
15:42:09 -   Supported: tools\cleanup_orphaned_projects.py
15:42:09 -   Supported: tools\cleanup_stale_snapshots.py
15:42:09 -   Supported: tools\download_qwen_model.py
15:42:09 -   Supported: tools\extract_tool_handlers.py
15:42:09 -   Supported: tools\index_project.py
15:42:09 -   Supported: tools\search_helper.py
15:42:09 -   Supported: tools\switch_project_helper.py
15:42:09 -   Supported: tools\test_relationship_extraction.py
15:42:09 -   Supported: tools\test_relationship_fixes.py
15:42:09 - Chunked chunking\__init__.py: 1 chunks
15:42:09 - Chunked chunking\multi_language_chunker.py: 7 chunks
15:42:09 - Chunked chunking\python_ast_chunker.py: 1 chunks
15:42:09 - Chunked chunking\tree_sitter.py: 65 chunks
15:42:09 - Chunked embeddings\__init__.py: 1 chunks
15:42:09 - Chunked embeddings\embedder.py: 26 chunks
15:42:09 - Chunked graph\__init__.py: 1 chunks
15:42:09 - Chunked graph\call_graph_extractor.py: 13 chunks
15:42:09 - Chunked graph\graph_queries.py: 10 chunks
15:42:09 - Chunked graph\graph_storage.py: 16 chunks
15:42:09 - Chunked graph\relationship_extractors\__init__.py: 1 chunks
15:42:09 - Chunked graph\relationship_extractors\base_extractor.py: 15 chunks
15:42:09 - Chunked graph\relationship_extractors\import_extractor.py: 8 chunks
15:42:09 - Chunked graph\relationship_extractors\inheritance_extractor.py: 10 chunks
15:42:09 - Chunked graph\relationship_extractors\type_extractor.py: 11 chunks
15:42:09 - Chunked graph\relationship_types.py: 7 chunks
15:42:09 - Chunked mcp_server\__init__.py: 1 chunks
15:42:09 - Chunked mcp_server\archived\server_lowlevel.py: 10 chunks
15:42:09 - Chunked mcp_server\archived\server_lowlevel_complete.py: 17 chunks
15:42:09 - Chunked mcp_server\archived\server_lowlevel_minimal.py: 3 chunks
15:42:09 - Chunked mcp_server\guidance.py: 5 chunks
15:42:09 - Chunked mcp_server\metrics.py: 8 chunks
15:42:09 - Chunked mcp_server\server.py: 18 chunks
15:42:09 - Chunked mcp_server\tool_handlers.py: 15 chunks
15:42:09 - Chunked mcp_server\tool_registry.py: 1 chunks
15:42:09 - Chunked mcp_server\tools\__init__.py: 1 chunks
15:42:09 - Chunked mcp_server\tools\code_relationship_analyzer.py: 8 chunks
15:42:09 - Chunked merkle\__init__.py: 1 chunks
15:42:09 - Chunked merkle\change_detector.py: 10 chunks
15:42:09 - Chunked merkle\merkle_dag.py: 15 chunks
15:42:09 - Chunked merkle\snapshot_manager.py: 14 chunks
15:42:09 - Chunked scripts\__init__.py: 1 chunks
15:42:09 - Chunked scripts\list_projects_display.py: 2 chunks
15:42:09 - Chunked scripts\list_projects_parseable.py: 2 chunks
15:42:09 - Chunked scripts\manual_configure.py: 9 chunks
15:42:09 - Chunked scripts\verify_hf_auth.py: 5 chunks
15:42:09 - Chunked scripts\verify_installation.py: 19 chunks
15:42:09 - Chunked search\__init__.py: 1 chunks
15:42:09 - Chunked search\bm25_index.py: 20 chunks
15:42:09 - Chunked search\config.py: 16 chunks
15:42:09 - Chunked search\hybrid_searcher.py: 37 chunks
15:42:09 - Chunked search\incremental_indexer.py: 12 chunks
15:42:09 - Chunked search\indexer.py: 33 chunks
15:42:09 - Chunked search\query_router.py: 8 chunks
15:42:09 - Chunked search\reranker.py: 8 chunks
15:42:09 - Chunked search\searcher.py: 20 chunks
15:42:09 - Chunked tests\__init__.py: 1 chunks
15:42:09 - Chunked tests\benchmarks\capture_baseline.py: 10 chunks
15:42:09 - Chunked tests\conftest.py: 10 chunks
15:42:09 - Chunked tests\fixtures\__init__.py: 1 chunks
15:42:09 - Chunked tests\fixtures\installation_mocks.py: 16 chunks
15:42:09 - Chunked tests\fixtures\sample_code.py: 1 chunks
15:42:09 - Chunked tests\integration\__init__.py: 1 chunks
15:42:09 - Chunked tests\integration\check_auth.py: 1 chunks
15:42:09 - Chunked tests\integration\run_hybrid_tests.py: 3 chunks
15:42:09 - Chunked tests\integration\test_auto_reindex.py: 1 chunks
15:42:09 - Chunked tests\integration\test_complete_workflow.py: 2 chunks
15:42:09 - Chunked tests\integration\test_critical_fixes.py: 1 chunks
15:42:09 - Chunked tests\integration\test_cuda_detection.py: 21 chunks
15:42:09 - Chunked tests\integration\test_direct_indexing.py: 2 chunks
15:42:09 - Chunked tests\integration\test_encoding_validation.py: 3 chunks
15:42:09 - Chunked tests\integration\test_full_flow.py: 19 chunks
15:42:09 - Chunked tests\integration\test_glsl_chunker_only.py: 1 chunks
15:42:09 - Chunked tests\integration\test_glsl_complete.py: 1 chunks
15:42:09 - Chunked tests\integration\test_glsl_without_embedder.py: 1 chunks
15:42:10 - Chunked tests\integration\test_graph_search.py: 11 chunks
15:42:10 - Chunked tests\integration\test_hf_access.py: 8 chunks
15:42:10 - Chunked tests\integration\test_hybrid_search_integration.py: 23 chunks
15:42:10 - Chunked tests\integration\test_incremental_indexing.py: 13 chunks
15:42:10 - Chunked tests\integration\test_installation.py: 54 chunks
15:42:10 - Chunked tests\integration\test_installation_flow.py: 19 chunks
15:42:10 - Chunked tests\integration\test_mcp_functionality.py: 4 chunks
15:42:10 - Chunked tests\integration\test_mcp_indexing.py: 7 chunks
15:42:10 - Chunked tests\integration\test_model_switching.py: 25 chunks
15:42:10 - Chunked tests\integration\test_multi_hop_flow.py: 12 chunks
15:42:10 - Chunked tests\integration\test_phase3_relationships.py: 16 chunks
15:42:10 - Chunked tests\integration\test_semantic_search.py: 2 chunks
15:42:10 - Chunked tests\integration\test_stemming_integration.py: 12 chunks
15:42:10 - Chunked tests\integration\test_system.py: 3 chunks
15:42:10 - Chunked tests\integration\test_token_efficiency_workflow.py: 14 chunks
15:42:10 - Chunked tests\test_data\glsl_project\fragment_shader.frag: 1 chunks
15:42:10 - Chunked tests\test_data\glsl_project\simple_shader.glsl: 2 chunks
15:42:10 - Chunked tests\test_data\glsl_project\vertex_shader.vert: 1 chunks
15:42:10 - Chunked tests\test_data\multi_language\App.svelte: 3 chunks
15:42:10 - Chunked tests\test_data\multi_language\calculator.c: 10 chunks
15:42:10 - Chunked tests\test_data\multi_language\Calculator.cpp: 3 chunks
15:42:10 - Chunked tests\test_data\multi_language\Calculator.cs: 1 chunks
15:42:10 - Chunked tests\test_data\multi_language\calculator.go: 10 chunks
15:42:10 - Chunked tests\test_data\multi_language\Calculator.java: 8 chunks
15:42:10 - Chunked tests\test_data\multi_language\calculator.rs: 11 chunks
15:42:10 - Chunked tests\test_data\multi_language\Component.jsx: 2 chunks
15:42:10 - Chunked tests\test_data\multi_language\Component.tsx: 4 chunks
15:42:10 - Chunked tests\test_data\multi_language\example.js: 5 chunks
15:42:10 - Chunked tests\test_data\multi_language\example.py: 6 chunks
15:42:10 - Chunked tests\test_data\multi_language\example.ts: 7 chunks
15:42:10 - Chunked tests\test_data\python_project\main.py: 2 chunks
15:42:10 - Chunked tests\test_data\python_project\src\api\handlers.py: 18 chunks
15:42:10 - Chunked tests\test_data\python_project\src\auth\authenticator.py: 12 chunks
15:42:10 - Chunked tests\test_data\python_project\src\database\connection.py: 12 chunks
15:42:10 - Chunked tests\test_data\python_project\src\utils\helpers.py: 20 chunks
15:42:10 - Chunked tests\test_data\python_project\src\utils\validators.py: 8 chunks
15:42:10 - Chunked tests\unit\__init__.py: 1 chunks
15:42:10 - Chunked tests\unit\test_bm25_index.py: 31 chunks
15:42:10 - Chunked tests\unit\test_bm25_population.py: 1 chunks
15:42:10 - Chunked tests\unit\test_call_graph_extraction.py: 32 chunks
15:42:10 - Chunked tests\unit\test_code_relationship_analyzer.py: 15 chunks
15:42:10 - Chunked tests\unit\test_embedder.py: 2 chunks
15:42:10 - Chunked tests\unit\test_evaluation.py: 25 chunks
15:42:10 - Chunked tests\unit\test_graph_storage.py: 1 chunks
15:42:10 - Chunked tests\unit\test_hybrid_search.py: 22 chunks
15:42:10 - Chunked tests\unit\test_imports.py: 1 chunks
15:42:10 - Chunked tests\unit\test_incremental_indexer.py: 31 chunks
15:42:10 - Chunked tests\unit\test_mcp_server.py: 4 chunks
15:42:10 - Chunked tests\unit\test_merkle.py: 32 chunks
15:42:10 - Chunked tests\unit\test_model_selection.py: 29 chunks
15:42:10 - Chunked tests\unit\test_multi_language.py: 16 chunks
15:42:10 - Chunked tests\unit\test_path_normalization.py: 27 chunks
15:42:10 - Chunked tests\unit\test_priority1_extractors.py: 29 chunks
15:42:10 - Chunked tests\unit\test_relationship_types.py: 19 chunks
15:42:10 - Chunked tests\unit\test_reranker.py: 24 chunks
15:42:10 - Chunked tests\unit\test_search_config.py: 17 chunks
15:42:10 - Chunked tests\unit\test_token_efficiency.py: 38 chunks
15:42:10 - Chunked tests\unit\test_tool_handlers.py: 19 chunks
15:42:10 - Chunked tests\unit\test_tree_sitter.py: 18 chunks
15:42:10 - Chunked tools\batch_index.py: 1 chunks
15:42:10 - Chunked tools\build_complete_server.py: 2 chunks
15:42:10 - Chunked tools\build_lowlevel_server.py: 3 chunks
15:42:10 - Chunked tools\cleanup_orphaned_projects.py: 4 chunks
15:42:10 - Chunked tools\cleanup_stale_snapshots.py: 4 chunks
15:42:10 - Chunked tools\download_qwen_model.py: 1 chunks
15:42:10 - Chunked tools\extract_tool_handlers.py: 2 chunks
15:42:10 - Chunked tools\index_project.py: 3 chunks
15:42:10 - Chunked tools\search_helper.py: 10 chunks
15:42:10 - Chunked tools\switch_project_helper.py: 1 chunks
15:42:10 - Chunked tools\test_relationship_extraction.py: 1 chunks
15:42:10 - Chunked tools\test_relationship_fixes.py: 1 chunks
15:42:10 - Total chunks collected: 1445
15:42:10 - Starting embedding for 1445 chunks
15:42:10 - Using batch size 256 from config for 1445 chunks
15:42:10 - Loading model: Qwen/Qwen3-Embedding-0.6B
15:42:10 - [VALIDATED CACHE] Enabling offline mode for faster startup.
15:42:10 - Loading model from validated cache: C:\Users\Inter\.claude_code_search\models\models--Qwen--Qwen3-Embedding-0.6B\snapshots\c54f2e6e80b2d7b7de06f51cec4959f6b3e03418
15:42:10 - [GPU_0] BEFORE_LOAD: Allocated=0.00GB, Reserved=0.00GB, Total=22.49GB (0.0% used)
15:42:10 - Load pretrained SentenceTransformer: C:\Users\Inter\.claude_code_search\models\models--Qwen--Qwen3-Embedding-0.6B\snapshots\c54f2e6e80b2d7b7de06f51cec4959f6b3e03418
15:42:11 - 1 prompt is loaded, with the key: query
15:42:11 - Model loaded successfully on device: cuda:0
15:42:11 - [GPU_0] AFTER_LOAD: Allocated=2.22GB, Reserved=2.22GB, Total=22.49GB (9.9% used)
15:42:15 - Processed 256/1445 chunks
15:42:19 - Processed 512/1445 chunks
15:42:23 - Processed 768/1445 chunks
15:42:26 - Processed 1024/1445 chunks
15:42:29 - Processed 1280/1445 chunks
15:42:32 - Embedding generation completed
15:42:32 - Successfully embedded 1445 chunks
15:42:32 - Adding 1445 embeddings to index
15:42:32 - [ADD_EMBEDDINGS] Called with 1445 results
15:42:32 - [ADD_EMBEDDINGS] Calling index_documents with 1445 docs
15:42:32 - [INDEX_DOCUMENTS] Called with 1445 documents
15:42:32 - [BM25] Starting BM25 indexing...
15:42:32 - [BM25] Before indexing - size: 0
15:42:32 - [BM25_INDEX] index_documents called with 1445 docs
15:42:34 - [BM25_INDEX] BM25 index created successfully with 1445 total documents
15:42:34 - [BM25_INDEX] Successfully indexed 1445 new documents (total: 1445)
15:42:34 - [BM25] After indexing - size: 1445
15:42:34 - Created flat index with dimension 1024
15:42:34 - Added 1445 embeddings to index
15:42:34 - Graph storage check before save: graph_storage=not None, nodes=2721
15:42:34 - Saving call graph with 2721 nodes to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
15:42:34 - Saved call graph: 2721 nodes, 5874 edges → C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
15:42:34 - Successfully saved call graph with 2721 nodes
15:42:34 - Hybrid indexing complete: BM25 1.59s, Dense 0.59s
15:42:34 - [ADD_EMBEDDINGS] Successfully added 1445 embeddings to hybrid index
15:42:34 - Successfully added embeddings to index
15:42:34 - [INCREMENTAL] Saving index...
15:42:34 - Saving hybrid indices
15:42:34 - [SAVE] Starting save operation
15:42:34 - [SAVE] === PRE-SAVE STATE ===
15:42:34 - [SAVE] BM25 directory exists: True
15:42:34 - [SAVE] BM25 index size: 1445 documents
15:42:34 - [SAVE] BM25 has index: True
15:42:34 - [SAVE] BM25 tokenized docs: 1445
15:42:34 - [SAVE] Dense index size: 1445 vectors
15:42:34 - [SAVE] Dense has index: True
15:42:34 - [SAVE] Overall ready state: True
15:42:34 - [SAVE] === END PRE-SAVE STATE ===
15:42:34 - [SAVE] BM25 size before save: 1445
15:42:34 - [SAVE] Calling BM25 index save...
15:42:34 - [BM25_SAVE] Starting save to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
15:42:34 - [BM25_SAVE] Saved index: 934033 bytes
15:42:35 - [BM25_SAVE] Saved docs: 5217708 bytes
15:42:35 - [BM25_SAVE] Saved metadata: 6596751 bytes (version=2, stemming=True)
15:42:35 - [BM25_SAVE] All files saved successfully
15:42:35 - [SAVE] BM25 index save completed
15:42:35 - [SAVE] Calling dense index save_index...
15:42:35 - Saved index to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\code.index
15:42:35 - [save_index] Graph storage check: graph_storage=not None, nodes=2721
15:42:35 - [save_index] Saving call graph with 2721 nodes to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
15:42:35 - Saved call graph: 2721 nodes, 5874 edges → C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\claude-context-local_caf2e75a_qwen3-0.6b_call_graph.json
15:42:35 - [save_index] Successfully saved call graph
15:42:35 - [SAVE] Dense index save completed
15:42:35 - [VERIFY] Checking BM25 files in: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_qwen3-0.6b_1024d\index\bm25
15:42:35 - [VERIFY] bm25.index: 934033 bytes
15:42:35 - [VERIFY] bm25_docs.json: 5217708 bytes
15:42:35 - [VERIFY] bm25_metadata.json: 6596751 bytes
15:42:35 - [VERIFY] BM25 files after save: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
15:42:35 - [VERIFY] bm25.index: 934033 bytes
15:42:35 - [VERIFY] bm25_docs.json: 5217708 bytes
15:42:35 - [VERIFY] bm25_metadata.json: 6596751 bytes
15:42:35 - [SAVE] === POST-SAVE STATE ===
15:42:35 - [SAVE] BM25 directory exists: True
15:42:35 - [SAVE] BM25 files: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
15:42:35 - [SAVE] BM25 index size: 1445 documents
15:42:35 - [SAVE] BM25 has index: True
15:42:35 - [SAVE] Dense index size: 1445 vectors
15:42:35 - [SAVE] Dense has index: True
15:42:35 - [SAVE] Overall ready state: True
15:42:35 - [SAVE] === END POST-SAVE STATE ===
15:42:35 - [SAVE] Hybrid indices saved successfully
15:42:35 - Successfully saved hybrid indices
15:42:35 - [INCREMENTAL] Index saved
15:42:35 - [INCREMENTAL] GPU cache cleared after indexing
15:42:35 - Completed indexing with Qwen/Qwen3-Embedding-0.6B in 26.47s
15:42:35 - Indexing with model: BAAI/bge-m3 (bge_m3)
15:42:35 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:35 - Search mode: semantic, hybrid enabled: True
15:42:35 - Saved search config to C:\Users\Inter/.claude_code_search/search_config.json
15:42:35 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:35 - Search mode: semantic, hybrid enabled: True
15:42:35 - [CONFIG] Using config default model: BAAI/bge-m3
15:42:35 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_bge-m3_1024d (model: BAAI/bge-m3, dimension: 1024d)
15:42:35 - Call graph extraction enabled for Python
15:42:35 - Phase 3: Initialized 3 relationship extractors
15:42:35 - Lazy loading bge_m3 (BAAI/bge-m3)...
15:42:35 - ✓ bge_m3 loaded successfully
15:42:35 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25 (stopwords=True, stemming=True)
15:42:35 - [INIT] BM25Index created successfully
15:42:35 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
15:42:35 - No existing BM25 index found
15:42:35 - [INIT] No existing BM25 index found, starting fresh
15:42:35 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
15:42:35 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
15:42:35 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
15:42:35 - Creating new index
15:42:35 - [INIT] No existing dense index found, starting fresh
15:42:35 - [INIT] HybridSearcher initialized - BM25: 0 docs, Dense: 0 vectors
15:42:35 - Creating new index
15:42:35 - Creating new index
15:42:35 - [INIT] Ready status: BM25=False, Dense=False, Overall=False
15:42:35 - Created fresh HybridSearcher for BAAI/bge-m3 at C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index
15:42:35 - Performing full index for claude-context-local
15:42:35 - [FULL_INDEX] Deleting old snapshot for current model: claude-context-local
15:42:35 - [FULL_INDEX] Deleted old snapshot for current model
15:42:35 - Clearing hybrid indices
15:42:35 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index, project_id=claude-context-local_caf2e75a_bge-m3
15:42:35 - Call graph storage initialized for project: claude-context-local_caf2e75a_bge-m3
15:42:35 - Successfully cleared hybrid indices
15:42:35 - Found 136 supported files out of 343 total files
15:42:35 -   Supported: chunking\__init__.py
15:42:35 -   Supported: chunking\multi_language_chunker.py
15:42:35 -   Supported: chunking\python_ast_chunker.py
15:42:35 -   Supported: chunking\tree_sitter.py
15:42:35 -   Supported: embeddings\__init__.py
15:42:35 -   Supported: embeddings\embedder.py
15:42:35 -   Supported: graph\__init__.py
15:42:35 -   Supported: graph\call_graph_extractor.py
15:42:35 -   Supported: graph\graph_queries.py
15:42:35 -   Supported: graph\graph_storage.py
15:42:35 -   Supported: graph\relationship_extractors\__init__.py
15:42:35 -   Supported: graph\relationship_extractors\base_extractor.py
15:42:35 -   Supported: graph\relationship_extractors\import_extractor.py
15:42:35 -   Supported: graph\relationship_extractors\inheritance_extractor.py
15:42:35 -   Supported: graph\relationship_extractors\type_extractor.py
15:42:35 -   Supported: graph\relationship_types.py
15:42:35 -   Supported: mcp_server\__init__.py
15:42:35 -   Supported: mcp_server\archived\server_lowlevel.py
15:42:35 -   Supported: mcp_server\archived\server_lowlevel_complete.py
15:42:35 -   Supported: mcp_server\archived\server_lowlevel_minimal.py
15:42:35 -   Supported: mcp_server\guidance.py
15:42:35 -   Supported: mcp_server\metrics.py
15:42:35 -   Supported: mcp_server\server.py
15:42:35 -   Supported: mcp_server\tool_handlers.py
15:42:35 -   Supported: mcp_server\tool_registry.py
15:42:35 -   Supported: mcp_server\tools\__init__.py
15:42:35 -   Supported: mcp_server\tools\code_relationship_analyzer.py
15:42:35 -   Supported: merkle\__init__.py
15:42:35 -   Supported: merkle\change_detector.py
15:42:35 -   Supported: merkle\merkle_dag.py
15:42:35 -   Supported: merkle\snapshot_manager.py
15:42:35 -   Supported: scripts\__init__.py
15:42:35 -   Supported: scripts\list_projects_display.py
15:42:35 -   Supported: scripts\list_projects_parseable.py
15:42:35 -   Supported: scripts\manual_configure.py
15:42:35 -   Supported: scripts\verify_hf_auth.py
15:42:35 -   Supported: scripts\verify_installation.py
15:42:35 -   Supported: search\__init__.py
15:42:35 -   Supported: search\bm25_index.py
15:42:35 -   Supported: search\config.py
15:42:35 -   Supported: search\hybrid_searcher.py
15:42:35 -   Supported: search\incremental_indexer.py
15:42:35 -   Supported: search\indexer.py
15:42:35 -   Supported: search\query_router.py
15:42:35 -   Supported: search\reranker.py
15:42:35 -   Supported: search\searcher.py
15:42:35 -   Supported: tests\__init__.py
15:42:35 -   Supported: tests\benchmarks\capture_baseline.py
15:42:35 -   Supported: tests\conftest.py
15:42:35 -   Supported: tests\fixtures\__init__.py
15:42:35 -   Supported: tests\fixtures\installation_mocks.py
15:42:35 -   Supported: tests\fixtures\sample_code.py
15:42:35 -   Supported: tests\integration\__init__.py
15:42:35 -   Supported: tests\integration\check_auth.py
15:42:35 -   Supported: tests\integration\run_hybrid_tests.py
15:42:35 -   Supported: tests\integration\test_auto_reindex.py
15:42:35 -   Supported: tests\integration\test_complete_workflow.py
15:42:35 -   Supported: tests\integration\test_critical_fixes.py
15:42:35 -   Supported: tests\integration\test_cuda_detection.py
15:42:35 -   Supported: tests\integration\test_direct_indexing.py
15:42:35 -   Supported: tests\integration\test_encoding_validation.py
15:42:35 -   Supported: tests\integration\test_full_flow.py
15:42:35 -   Supported: tests\integration\test_glsl_chunker_only.py
15:42:35 -   Supported: tests\integration\test_glsl_complete.py
15:42:35 -   Supported: tests\integration\test_glsl_without_embedder.py
15:42:35 -   Supported: tests\integration\test_graph_search.py
15:42:35 -   Supported: tests\integration\test_hf_access.py
15:42:35 -   Supported: tests\integration\test_hybrid_search_integration.py
15:42:35 -   Supported: tests\integration\test_incremental_indexing.py
15:42:35 -   Supported: tests\integration\test_installation.py
15:42:35 -   Supported: tests\integration\test_installation_flow.py
15:42:35 -   Supported: tests\integration\test_mcp_functionality.py
15:42:35 -   Supported: tests\integration\test_mcp_indexing.py
15:42:35 -   Supported: tests\integration\test_model_switching.py
15:42:35 -   Supported: tests\integration\test_multi_hop_flow.py
15:42:35 -   Supported: tests\integration\test_phase3_relationships.py
15:42:35 -   Supported: tests\integration\test_semantic_search.py
15:42:35 -   Supported: tests\integration\test_stemming_integration.py
15:42:35 -   Supported: tests\integration\test_system.py
15:42:35 -   Supported: tests\integration\test_token_efficiency_workflow.py
15:42:35 -   Supported: tests\test_data\glsl_project\fragment_shader.frag
15:42:35 -   Supported: tests\test_data\glsl_project\simple_shader.glsl
15:42:35 -   Supported: tests\test_data\glsl_project\vertex_shader.vert
15:42:35 -   Supported: tests\test_data\multi_language\App.svelte
15:42:35 -   Supported: tests\test_data\multi_language\calculator.c
15:42:35 -   Supported: tests\test_data\multi_language\Calculator.cpp
15:42:35 -   Supported: tests\test_data\multi_language\Calculator.cs
15:42:35 -   Supported: tests\test_data\multi_language\calculator.go
15:42:35 -   Supported: tests\test_data\multi_language\Calculator.java
15:42:35 -   Supported: tests\test_data\multi_language\calculator.rs
15:42:35 -   Supported: tests\test_data\multi_language\Component.jsx
15:42:35 -   Supported: tests\test_data\multi_language\Component.tsx
15:42:35 -   Supported: tests\test_data\multi_language\example.js
15:42:35 -   Supported: tests\test_data\multi_language\example.py
15:42:35 -   Supported: tests\test_data\multi_language\example.ts
15:42:35 -   Supported: tests\test_data\python_project\main.py
15:42:35 -   Supported: tests\test_data\python_project\src\api\handlers.py
15:42:35 -   Supported: tests\test_data\python_project\src\auth\authenticator.py
15:42:35 -   Supported: tests\test_data\python_project\src\database\connection.py
15:42:35 -   Supported: tests\test_data\python_project\src\utils\helpers.py
15:42:35 -   Supported: tests\test_data\python_project\src\utils\validators.py
15:42:35 -   Supported: tests\unit\__init__.py
15:42:35 -   Supported: tests\unit\test_bm25_index.py
15:42:35 -   Supported: tests\unit\test_bm25_population.py
15:42:35 -   Supported: tests\unit\test_call_graph_extraction.py
15:42:35 -   Supported: tests\unit\test_code_relationship_analyzer.py
15:42:35 -   Supported: tests\unit\test_embedder.py
15:42:35 -   Supported: tests\unit\test_evaluation.py
15:42:35 -   Supported: tests\unit\test_graph_storage.py
15:42:35 -   Supported: tests\unit\test_hybrid_search.py
15:42:35 -   Supported: tests\unit\test_imports.py
15:42:35 -   Supported: tests\unit\test_incremental_indexer.py
15:42:35 -   Supported: tests\unit\test_mcp_server.py
15:42:35 -   Supported: tests\unit\test_merkle.py
15:42:35 -   Supported: tests\unit\test_model_selection.py
15:42:35 -   Supported: tests\unit\test_multi_language.py
15:42:35 -   Supported: tests\unit\test_path_normalization.py
15:42:35 -   Supported: tests\unit\test_priority1_extractors.py
15:42:35 -   Supported: tests\unit\test_relationship_types.py
15:42:35 -   Supported: tests\unit\test_reranker.py
15:42:35 -   Supported: tests\unit\test_search_config.py
15:42:35 -   Supported: tests\unit\test_token_efficiency.py
15:42:35 -   Supported: tests\unit\test_tool_handlers.py
15:42:35 -   Supported: tests\unit\test_tree_sitter.py
15:42:35 -   Supported: tools\batch_index.py
15:42:35 -   Supported: tools\build_complete_server.py
15:42:35 -   Supported: tools\build_lowlevel_server.py
15:42:35 -   Supported: tools\cleanup_orphaned_projects.py
15:42:35 -   Supported: tools\cleanup_stale_snapshots.py
15:42:35 -   Supported: tools\download_qwen_model.py
15:42:35 -   Supported: tools\extract_tool_handlers.py
15:42:35 -   Supported: tools\index_project.py
15:42:35 -   Supported: tools\search_helper.py
15:42:35 -   Supported: tools\switch_project_helper.py
15:42:35 -   Supported: tools\test_relationship_extraction.py
15:42:35 -   Supported: tools\test_relationship_fixes.py
15:42:35 - Chunked chunking\__init__.py: 1 chunks
15:42:35 - Chunked chunking\multi_language_chunker.py: 7 chunks
15:42:35 - Chunked chunking\python_ast_chunker.py: 1 chunks
15:42:35 - Chunked chunking\tree_sitter.py: 65 chunks
15:42:35 - Chunked embeddings\__init__.py: 1 chunks
15:42:35 - Chunked embeddings\embedder.py: 26 chunks
15:42:35 - Chunked graph\__init__.py: 1 chunks
15:42:35 - Chunked graph\call_graph_extractor.py: 13 chunks
15:42:35 - Chunked graph\graph_queries.py: 10 chunks
15:42:35 - Chunked graph\graph_storage.py: 16 chunks
15:42:35 - Chunked graph\relationship_extractors\__init__.py: 1 chunks
15:42:35 - Chunked graph\relationship_extractors\base_extractor.py: 15 chunks
15:42:35 - Chunked graph\relationship_extractors\import_extractor.py: 8 chunks
15:42:35 - Chunked graph\relationship_extractors\inheritance_extractor.py: 10 chunks
15:42:35 - Chunked graph\relationship_extractors\type_extractor.py: 11 chunks
15:42:35 - Chunked graph\relationship_types.py: 7 chunks
15:42:35 - Chunked mcp_server\__init__.py: 1 chunks
15:42:35 - Chunked mcp_server\archived\server_lowlevel.py: 10 chunks
15:42:35 - Chunked mcp_server\archived\server_lowlevel_complete.py: 17 chunks
15:42:35 - Chunked mcp_server\archived\server_lowlevel_minimal.py: 3 chunks
15:42:35 - Chunked mcp_server\guidance.py: 5 chunks
15:42:35 - Chunked mcp_server\metrics.py: 8 chunks
15:42:35 - Chunked mcp_server\server.py: 18 chunks
15:42:35 - Chunked mcp_server\tool_handlers.py: 15 chunks
15:42:36 - Chunked mcp_server\tool_registry.py: 1 chunks
15:42:36 - Chunked mcp_server\tools\__init__.py: 1 chunks
15:42:36 - Chunked mcp_server\tools\code_relationship_analyzer.py: 8 chunks
15:42:36 - Chunked merkle\__init__.py: 1 chunks
15:42:36 - Chunked merkle\change_detector.py: 10 chunks
15:42:36 - Chunked merkle\merkle_dag.py: 15 chunks
15:42:36 - Chunked merkle\snapshot_manager.py: 14 chunks
15:42:36 - Chunked scripts\__init__.py: 1 chunks
15:42:36 - Chunked scripts\list_projects_display.py: 2 chunks
15:42:36 - Chunked scripts\list_projects_parseable.py: 2 chunks
15:42:36 - Chunked scripts\manual_configure.py: 9 chunks
15:42:36 - Chunked scripts\verify_hf_auth.py: 5 chunks
15:42:36 - Chunked scripts\verify_installation.py: 19 chunks
15:42:36 - Chunked search\__init__.py: 1 chunks
15:42:36 - Chunked search\bm25_index.py: 20 chunks
15:42:36 - Chunked search\config.py: 16 chunks
15:42:36 - Chunked search\hybrid_searcher.py: 37 chunks
15:42:36 - Chunked search\incremental_indexer.py: 12 chunks
15:42:36 - Chunked search\indexer.py: 33 chunks
15:42:36 - Chunked search\query_router.py: 8 chunks
15:42:36 - Chunked search\reranker.py: 8 chunks
15:42:36 - Chunked search\searcher.py: 20 chunks
15:42:36 - Chunked tests\__init__.py: 1 chunks
15:42:36 - Chunked tests\benchmarks\capture_baseline.py: 10 chunks
15:42:36 - Chunked tests\conftest.py: 10 chunks
15:42:36 - Chunked tests\fixtures\__init__.py: 1 chunks
15:42:36 - Chunked tests\fixtures\installation_mocks.py: 16 chunks
15:42:36 - Chunked tests\fixtures\sample_code.py: 1 chunks
15:42:36 - Chunked tests\integration\__init__.py: 1 chunks
15:42:36 - Chunked tests\integration\check_auth.py: 1 chunks
15:42:36 - Chunked tests\integration\run_hybrid_tests.py: 3 chunks
15:42:36 - Chunked tests\integration\test_auto_reindex.py: 1 chunks
15:42:36 - Chunked tests\integration\test_complete_workflow.py: 2 chunks
15:42:36 - Chunked tests\integration\test_critical_fixes.py: 1 chunks
15:42:36 - Chunked tests\integration\test_cuda_detection.py: 21 chunks
15:42:36 - Chunked tests\integration\test_direct_indexing.py: 2 chunks
15:42:36 - Chunked tests\integration\test_encoding_validation.py: 3 chunks
15:42:36 - Chunked tests\integration\test_full_flow.py: 19 chunks
15:42:36 - Chunked tests\integration\test_glsl_chunker_only.py: 1 chunks
15:42:36 - Chunked tests\integration\test_glsl_complete.py: 1 chunks
15:42:36 - Chunked tests\integration\test_glsl_without_embedder.py: 1 chunks
15:42:36 - Chunked tests\integration\test_graph_search.py: 11 chunks
15:42:36 - Chunked tests\integration\test_hf_access.py: 8 chunks
15:42:36 - Chunked tests\integration\test_hybrid_search_integration.py: 23 chunks
15:42:36 - Chunked tests\integration\test_incremental_indexing.py: 13 chunks
15:42:36 - Chunked tests\integration\test_installation.py: 54 chunks
15:42:36 - Chunked tests\integration\test_installation_flow.py: 19 chunks
15:42:36 - Chunked tests\integration\test_mcp_functionality.py: 4 chunks
15:42:36 - Chunked tests\integration\test_mcp_indexing.py: 7 chunks
15:42:36 - Chunked tests\integration\test_model_switching.py: 25 chunks
15:42:36 - Chunked tests\integration\test_multi_hop_flow.py: 12 chunks
15:42:36 - Chunked tests\integration\test_phase3_relationships.py: 16 chunks
15:42:36 - Chunked tests\integration\test_semantic_search.py: 2 chunks
15:42:36 - Chunked tests\integration\test_stemming_integration.py: 12 chunks
15:42:36 - Chunked tests\integration\test_system.py: 3 chunks
15:42:36 - Chunked tests\integration\test_token_efficiency_workflow.py: 14 chunks
15:42:36 - Chunked tests\test_data\glsl_project\fragment_shader.frag: 1 chunks
15:42:36 - Chunked tests\test_data\glsl_project\simple_shader.glsl: 2 chunks
15:42:36 - Chunked tests\test_data\glsl_project\vertex_shader.vert: 1 chunks
15:42:36 - Chunked tests\test_data\multi_language\App.svelte: 3 chunks
15:42:36 - Chunked tests\test_data\multi_language\calculator.c: 10 chunks
15:42:36 - Chunked tests\test_data\multi_language\Calculator.cpp: 3 chunks
15:42:36 - Chunked tests\test_data\multi_language\Calculator.cs: 1 chunks
15:42:36 - Chunked tests\test_data\multi_language\calculator.go: 10 chunks
15:42:36 - Chunked tests\test_data\multi_language\Calculator.java: 8 chunks
15:42:36 - Chunked tests\test_data\multi_language\calculator.rs: 11 chunks
15:42:36 - Chunked tests\test_data\multi_language\Component.jsx: 2 chunks
15:42:36 - Chunked tests\test_data\multi_language\Component.tsx: 4 chunks
15:42:36 - Chunked tests\test_data\multi_language\example.js: 5 chunks
15:42:36 - Chunked tests\test_data\multi_language\example.py: 6 chunks
15:42:36 - Chunked tests\test_data\multi_language\example.ts: 7 chunks
15:42:36 - Chunked tests\test_data\python_project\main.py: 2 chunks
15:42:36 - Chunked tests\test_data\python_project\src\api\handlers.py: 18 chunks
15:42:36 - Chunked tests\test_data\python_project\src\auth\authenticator.py: 12 chunks
15:42:36 - Chunked tests\test_data\python_project\src\database\connection.py: 12 chunks
15:42:36 - Chunked tests\test_data\python_project\src\utils\helpers.py: 20 chunks
15:42:36 - Chunked tests\test_data\python_project\src\utils\validators.py: 8 chunks
15:42:36 - Chunked tests\unit\__init__.py: 1 chunks
15:42:36 - Chunked tests\unit\test_bm25_index.py: 31 chunks
15:42:36 - Chunked tests\unit\test_bm25_population.py: 1 chunks
15:42:36 - Chunked tests\unit\test_call_graph_extraction.py: 32 chunks
15:42:36 - Chunked tests\unit\test_code_relationship_analyzer.py: 15 chunks
15:42:36 - Chunked tests\unit\test_embedder.py: 2 chunks
15:42:36 - Chunked tests\unit\test_evaluation.py: 25 chunks
15:42:36 - Chunked tests\unit\test_graph_storage.py: 1 chunks
15:42:36 - Chunked tests\unit\test_hybrid_search.py: 22 chunks
15:42:36 - Chunked tests\unit\test_imports.py: 1 chunks
15:42:36 - Chunked tests\unit\test_incremental_indexer.py: 31 chunks
15:42:36 - Chunked tests\unit\test_mcp_server.py: 4 chunks
15:42:36 - Chunked tests\unit\test_merkle.py: 32 chunks
15:42:36 - Chunked tests\unit\test_model_selection.py: 29 chunks
15:42:36 - Chunked tests\unit\test_multi_language.py: 16 chunks
15:42:36 - Chunked tests\unit\test_path_normalization.py: 27 chunks
15:42:36 - Chunked tests\unit\test_priority1_extractors.py: 29 chunks
15:42:36 - Chunked tests\unit\test_relationship_types.py: 19 chunks
15:42:36 - Chunked tests\unit\test_reranker.py: 24 chunks
15:42:36 - Chunked tests\unit\test_search_config.py: 17 chunks
15:42:36 - Chunked tests\unit\test_token_efficiency.py: 38 chunks
15:42:36 - Chunked tests\unit\test_tool_handlers.py: 19 chunks
15:42:36 - Chunked tests\unit\test_tree_sitter.py: 18 chunks
15:42:36 - Chunked tools\batch_index.py: 1 chunks
15:42:36 - Chunked tools\build_complete_server.py: 2 chunks
15:42:36 - Chunked tools\build_lowlevel_server.py: 3 chunks
15:42:36 - Chunked tools\cleanup_orphaned_projects.py: 4 chunks
15:42:36 - Chunked tools\cleanup_stale_snapshots.py: 4 chunks
15:42:36 - Chunked tools\download_qwen_model.py: 1 chunks
15:42:36 - Chunked tools\extract_tool_handlers.py: 2 chunks
15:42:36 - Chunked tools\index_project.py: 3 chunks
15:42:36 - Chunked tools\search_helper.py: 10 chunks
15:42:36 - Chunked tools\switch_project_helper.py: 1 chunks
15:42:36 - Chunked tools\test_relationship_extraction.py: 1 chunks
15:42:36 - Chunked tools\test_relationship_fixes.py: 1 chunks
15:42:36 - Total chunks collected: 1445
15:42:36 - Starting embedding for 1445 chunks
15:42:36 - Using batch size 256 from config for 1445 chunks
15:42:36 - Loading model: BAAI/bge-m3
15:42:36 - [VALIDATED CACHE] Enabling offline mode for faster startup.
15:42:36 - Loading model from validated cache: C:\Users\Inter\.claude_code_search\models\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181
15:42:36 - [GPU_0] BEFORE_LOAD: Allocated=2.23GB, Reserved=2.24GB, Total=22.49GB (9.9% used)
15:42:36 - Load pretrained SentenceTransformer: C:\Users\Inter\.claude_code_search\models\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181
15:42:38 - Model loaded successfully on device: cuda:0
15:42:38 - [GPU_0] AFTER_LOAD: Allocated=4.34GB, Reserved=4.36GB, Total=22.49GB (19.3% used)
15:42:41 - Processed 256/1445 chunks
15:42:44 - Processed 512/1445 chunks
15:42:46 - Processed 768/1445 chunks
15:42:48 - Processed 1024/1445 chunks
15:42:51 - Processed 1280/1445 chunks
15:42:53 - Embedding generation completed
15:42:53 - Successfully embedded 1445 chunks
15:42:53 - Adding 1445 embeddings to index
15:42:53 - [ADD_EMBEDDINGS] Called with 1445 results
15:42:53 - [ADD_EMBEDDINGS] Calling index_documents with 1445 docs
15:42:53 - [INDEX_DOCUMENTS] Called with 1445 documents
15:42:53 - [BM25] Starting BM25 indexing...
15:42:53 - [BM25] Before indexing - size: 0
15:42:53 - [BM25_INDEX] index_documents called with 1445 docs
15:42:54 - [BM25_INDEX] BM25 index created successfully with 1445 total documents
15:42:54 - [BM25_INDEX] Successfully indexed 1445 new documents (total: 1445)
15:42:54 - [BM25] After indexing - size: 1445
15:42:54 - Created flat index with dimension 1024
15:42:54 - Added 1445 embeddings to index
15:42:54 - Graph storage check before save: graph_storage=not None, nodes=2721
15:42:54 - Saving call graph with 2721 nodes to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
15:42:54 - Saved call graph: 2721 nodes, 5874 edges → C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
15:42:54 - Successfully saved call graph with 2721 nodes
15:42:55 - Hybrid indexing complete: BM25 1.61s, Dense 0.57s
15:42:55 - [ADD_EMBEDDINGS] Successfully added 1445 embeddings to hybrid index
15:42:55 - Successfully added embeddings to index
15:42:55 - [INCREMENTAL] Saving index...
15:42:55 - Saving hybrid indices
15:42:55 - [SAVE] Starting save operation
15:42:55 - [SAVE] === PRE-SAVE STATE ===
15:42:55 - [SAVE] BM25 directory exists: True
15:42:55 - [SAVE] BM25 index size: 1445 documents
15:42:55 - [SAVE] BM25 has index: True
15:42:55 - [SAVE] BM25 tokenized docs: 1445
15:42:55 - [SAVE] Dense index size: 1445 vectors
15:42:55 - [SAVE] Dense has index: True
15:42:55 - [SAVE] Overall ready state: True
15:42:55 - [SAVE] === END PRE-SAVE STATE ===
15:42:55 - [SAVE] BM25 size before save: 1445
15:42:55 - [SAVE] Calling BM25 index save...
15:42:55 - [BM25_SAVE] Starting save to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
15:42:55 - [BM25_SAVE] Saved index: 934033 bytes
15:42:55 - [BM25_SAVE] Saved docs: 5217708 bytes
15:42:55 - [BM25_SAVE] Saved metadata: 6596751 bytes (version=2, stemming=True)
15:42:55 - [BM25_SAVE] All files saved successfully
15:42:55 - [SAVE] BM25 index save completed
15:42:55 - [SAVE] Calling dense index save_index...
15:42:55 - Saved index to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\code.index
15:42:55 - [save_index] Graph storage check: graph_storage=not None, nodes=2721
15:42:55 - [save_index] Saving call graph with 2721 nodes to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
15:42:55 - Saved call graph: 2721 nodes, 5874 edges → C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\claude-context-local_caf2e75a_bge-m3_call_graph.json
15:42:55 - [save_index] Successfully saved call graph
15:42:55 - [SAVE] Dense index save completed
15:42:55 - [VERIFY] Checking BM25 files in: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_bge-m3_1024d\index\bm25
15:42:55 - [VERIFY] bm25.index: 934033 bytes
15:42:55 - [VERIFY] bm25_docs.json: 5217708 bytes
15:42:55 - [VERIFY] bm25_metadata.json: 6596751 bytes
15:42:55 - [VERIFY] BM25 files after save: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
15:42:55 - [VERIFY] bm25.index: 934033 bytes
15:42:55 - [VERIFY] bm25_docs.json: 5217708 bytes
15:42:55 - [VERIFY] bm25_metadata.json: 6596751 bytes
15:42:55 - [SAVE] === POST-SAVE STATE ===
15:42:55 - [SAVE] BM25 directory exists: True
15:42:55 - [SAVE] BM25 files: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
15:42:55 - [SAVE] BM25 index size: 1445 documents
15:42:55 - [SAVE] BM25 has index: True
15:42:55 - [SAVE] Dense index size: 1445 vectors
15:42:55 - [SAVE] Dense has index: True
15:42:55 - [SAVE] Overall ready state: True
15:42:55 - [SAVE] === END POST-SAVE STATE ===
15:42:55 - [SAVE] Hybrid indices saved successfully
15:42:55 - Successfully saved hybrid indices
15:42:55 - [INCREMENTAL] Index saved
15:42:55 - [INCREMENTAL] GPU cache cleared after indexing
15:42:55 - Completed indexing with BAAI/bge-m3 in 20.23s
15:42:55 - Indexing with model: nomic-ai/CodeRankEmbed (coderankembed)
15:42:55 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:55 - Search mode: semantic, hybrid enabled: True
15:42:55 - Saved search config to C:\Users\Inter/.claude_code_search/search_config.json
15:42:55 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:42:55 - Search mode: semantic, hybrid enabled: True
15:42:55 - [CONFIG] Using config default model: nomic-ai/CodeRankEmbed
15:42:55 - [PER_MODEL_INDICES] Using storage: claude-context-local_caf2e75a_coderank_768d (model: nomic-ai/CodeRankEmbed, dimension: 768d)
15:42:55 - Call graph extraction enabled for Python
15:42:55 - Phase 3: Initialized 3 relationship extractors
15:42:55 - Lazy loading coderankembed (nomic-ai/CodeRankEmbed)...
15:42:55 - ✓ coderankembed loaded successfully
15:42:55 - [INIT] Creating BM25Index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25 (stopwords=True, stemming=True)
15:42:55 - [INIT] BM25Index created successfully
15:42:55 - [INIT] BM25 storage path: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
15:42:55 - No existing BM25 index found
15:42:55 - [INIT] No existing BM25 index found, starting fresh
15:42:55 - [INIT] Initializing dense index at: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
15:42:55 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
15:42:55 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
15:42:55 - Creating new index
15:42:55 - [INIT] No existing dense index found, starting fresh
15:42:55 - [INIT] HybridSearcher initialized - BM25: 0 docs, Dense: 0 vectors
15:42:55 - Creating new index
15:42:55 - Creating new index
15:42:55 - [INIT] Ready status: BM25=False, Dense=False, Overall=False
15:42:55 - Created fresh HybridSearcher for nomic-ai/CodeRankEmbed at C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index
15:42:55 - Performing full index for claude-context-local
15:42:55 - [FULL_INDEX] Deleting old snapshot for current model: claude-context-local
15:42:55 - [FULL_INDEX] Deleted old snapshot for current model
15:42:55 - Clearing hybrid indices
15:42:55 - [INIT] CodeIndexManager created: storage_dir=C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index, project_id=claude-context-local_caf2e75a_coderank
15:42:55 - Call graph storage initialized for project: claude-context-local_caf2e75a_coderank
15:42:55 - Successfully cleared hybrid indices
15:42:55 - Found 136 supported files out of 343 total files
15:42:55 -   Supported: chunking\__init__.py
15:42:55 -   Supported: chunking\multi_language_chunker.py
15:42:55 -   Supported: chunking\python_ast_chunker.py
15:42:55 -   Supported: chunking\tree_sitter.py
15:42:55 -   Supported: embeddings\__init__.py
15:42:55 -   Supported: embeddings\embedder.py
15:42:55 -   Supported: graph\__init__.py
15:42:55 -   Supported: graph\call_graph_extractor.py
15:42:55 -   Supported: graph\graph_queries.py
15:42:55 -   Supported: graph\graph_storage.py
15:42:55 -   Supported: graph\relationship_extractors\__init__.py
15:42:55 -   Supported: graph\relationship_extractors\base_extractor.py
15:42:55 -   Supported: graph\relationship_extractors\import_extractor.py
15:42:55 -   Supported: graph\relationship_extractors\inheritance_extractor.py
15:42:55 -   Supported: graph\relationship_extractors\type_extractor.py
15:42:55 -   Supported: graph\relationship_types.py
15:42:55 -   Supported: mcp_server\__init__.py
15:42:55 -   Supported: mcp_server\archived\server_lowlevel.py
15:42:55 -   Supported: mcp_server\archived\server_lowlevel_complete.py
15:42:55 -   Supported: mcp_server\archived\server_lowlevel_minimal.py
15:42:55 -   Supported: mcp_server\guidance.py
15:42:55 -   Supported: mcp_server\metrics.py
15:42:55 -   Supported: mcp_server\server.py
15:42:55 -   Supported: mcp_server\tool_handlers.py
15:42:55 -   Supported: mcp_server\tool_registry.py
15:42:55 -   Supported: mcp_server\tools\__init__.py
15:42:55 -   Supported: mcp_server\tools\code_relationship_analyzer.py
15:42:55 -   Supported: merkle\__init__.py
15:42:55 -   Supported: merkle\change_detector.py
15:42:55 -   Supported: merkle\merkle_dag.py
15:42:55 -   Supported: merkle\snapshot_manager.py
15:42:55 -   Supported: scripts\__init__.py
15:42:55 -   Supported: scripts\list_projects_display.py
15:42:55 -   Supported: scripts\list_projects_parseable.py
15:42:55 -   Supported: scripts\manual_configure.py
15:42:55 -   Supported: scripts\verify_hf_auth.py
15:42:55 -   Supported: scripts\verify_installation.py
15:42:55 -   Supported: search\__init__.py
15:42:55 -   Supported: search\bm25_index.py
15:42:55 -   Supported: search\config.py
15:42:55 -   Supported: search\hybrid_searcher.py
15:42:55 -   Supported: search\incremental_indexer.py
15:42:55 -   Supported: search\indexer.py
15:42:55 -   Supported: search\query_router.py
15:42:55 -   Supported: search\reranker.py
15:42:55 -   Supported: search\searcher.py
15:42:55 -   Supported: tests\__init__.py
15:42:55 -   Supported: tests\benchmarks\capture_baseline.py
15:42:55 -   Supported: tests\conftest.py
15:42:55 -   Supported: tests\fixtures\__init__.py
15:42:55 -   Supported: tests\fixtures\installation_mocks.py
15:42:56 -   Supported: tests\fixtures\sample_code.py
15:42:56 -   Supported: tests\integration\__init__.py
15:42:56 -   Supported: tests\integration\check_auth.py
15:42:56 -   Supported: tests\integration\run_hybrid_tests.py
15:42:56 -   Supported: tests\integration\test_auto_reindex.py
15:42:56 -   Supported: tests\integration\test_complete_workflow.py
15:42:56 -   Supported: tests\integration\test_critical_fixes.py
15:42:56 -   Supported: tests\integration\test_cuda_detection.py
15:42:56 -   Supported: tests\integration\test_direct_indexing.py
15:42:56 -   Supported: tests\integration\test_encoding_validation.py
15:42:56 -   Supported: tests\integration\test_full_flow.py
15:42:56 -   Supported: tests\integration\test_glsl_chunker_only.py
15:42:56 -   Supported: tests\integration\test_glsl_complete.py
15:42:56 -   Supported: tests\integration\test_glsl_without_embedder.py
15:42:56 -   Supported: tests\integration\test_graph_search.py
15:42:56 -   Supported: tests\integration\test_hf_access.py
15:42:56 -   Supported: tests\integration\test_hybrid_search_integration.py
15:42:56 -   Supported: tests\integration\test_incremental_indexing.py
15:42:56 -   Supported: tests\integration\test_installation.py
15:42:56 -   Supported: tests\integration\test_installation_flow.py
15:42:56 -   Supported: tests\integration\test_mcp_functionality.py
15:42:56 -   Supported: tests\integration\test_mcp_indexing.py
15:42:56 -   Supported: tests\integration\test_model_switching.py
15:42:56 -   Supported: tests\integration\test_multi_hop_flow.py
15:42:56 -   Supported: tests\integration\test_phase3_relationships.py
15:42:56 -   Supported: tests\integration\test_semantic_search.py
15:42:56 -   Supported: tests\integration\test_stemming_integration.py
15:42:56 -   Supported: tests\integration\test_system.py
15:42:56 -   Supported: tests\integration\test_token_efficiency_workflow.py
15:42:56 -   Supported: tests\test_data\glsl_project\fragment_shader.frag
15:42:56 -   Supported: tests\test_data\glsl_project\simple_shader.glsl
15:42:56 -   Supported: tests\test_data\glsl_project\vertex_shader.vert
15:42:56 -   Supported: tests\test_data\multi_language\App.svelte
15:42:56 -   Supported: tests\test_data\multi_language\calculator.c
15:42:56 -   Supported: tests\test_data\multi_language\Calculator.cpp
15:42:56 -   Supported: tests\test_data\multi_language\Calculator.cs
15:42:56 -   Supported: tests\test_data\multi_language\calculator.go
15:42:56 -   Supported: tests\test_data\multi_language\Calculator.java
15:42:56 -   Supported: tests\test_data\multi_language\calculator.rs
15:42:56 -   Supported: tests\test_data\multi_language\Component.jsx
15:42:56 -   Supported: tests\test_data\multi_language\Component.tsx
15:42:56 -   Supported: tests\test_data\multi_language\example.js
15:42:56 -   Supported: tests\test_data\multi_language\example.py
15:42:56 -   Supported: tests\test_data\multi_language\example.ts
15:42:56 -   Supported: tests\test_data\python_project\main.py
15:42:56 -   Supported: tests\test_data\python_project\src\api\handlers.py
15:42:56 -   Supported: tests\test_data\python_project\src\auth\authenticator.py
15:42:56 -   Supported: tests\test_data\python_project\src\database\connection.py
15:42:56 -   Supported: tests\test_data\python_project\src\utils\helpers.py
15:42:56 -   Supported: tests\test_data\python_project\src\utils\validators.py
15:42:56 -   Supported: tests\unit\__init__.py
15:42:56 -   Supported: tests\unit\test_bm25_index.py
15:42:56 -   Supported: tests\unit\test_bm25_population.py
15:42:56 -   Supported: tests\unit\test_call_graph_extraction.py
15:42:56 -   Supported: tests\unit\test_code_relationship_analyzer.py
15:42:56 -   Supported: tests\unit\test_embedder.py
15:42:56 -   Supported: tests\unit\test_evaluation.py
15:42:56 -   Supported: tests\unit\test_graph_storage.py
15:42:56 -   Supported: tests\unit\test_hybrid_search.py
15:42:56 -   Supported: tests\unit\test_imports.py
15:42:56 -   Supported: tests\unit\test_incremental_indexer.py
15:42:56 -   Supported: tests\unit\test_mcp_server.py
15:42:56 -   Supported: tests\unit\test_merkle.py
15:42:56 -   Supported: tests\unit\test_model_selection.py
15:42:56 -   Supported: tests\unit\test_multi_language.py
15:42:56 -   Supported: tests\unit\test_path_normalization.py
15:42:56 -   Supported: tests\unit\test_priority1_extractors.py
15:42:56 -   Supported: tests\unit\test_relationship_types.py
15:42:56 -   Supported: tests\unit\test_reranker.py
15:42:56 -   Supported: tests\unit\test_search_config.py
15:42:56 -   Supported: tests\unit\test_token_efficiency.py
15:42:56 -   Supported: tests\unit\test_tool_handlers.py
15:42:56 -   Supported: tests\unit\test_tree_sitter.py
15:42:56 -   Supported: tools\batch_index.py
15:42:56 -   Supported: tools\build_complete_server.py
15:42:56 -   Supported: tools\build_lowlevel_server.py
15:42:56 -   Supported: tools\cleanup_orphaned_projects.py
15:42:56 -   Supported: tools\cleanup_stale_snapshots.py
15:42:56 -   Supported: tools\download_qwen_model.py
15:42:56 -   Supported: tools\extract_tool_handlers.py
15:42:56 -   Supported: tools\index_project.py
15:42:56 -   Supported: tools\search_helper.py
15:42:56 -   Supported: tools\switch_project_helper.py
15:42:56 -   Supported: tools\test_relationship_extraction.py
15:42:56 -   Supported: tools\test_relationship_fixes.py
15:42:56 - Chunked chunking\__init__.py: 1 chunks
15:42:56 - Chunked chunking\multi_language_chunker.py: 7 chunks
15:42:56 - Chunked chunking\python_ast_chunker.py: 1 chunks
15:42:56 - Chunked chunking\tree_sitter.py: 65 chunks
15:42:56 - Chunked embeddings\__init__.py: 1 chunks
15:42:56 - Chunked embeddings\embedder.py: 26 chunks
15:42:56 - Chunked graph\__init__.py: 1 chunks
15:42:56 - Chunked graph\call_graph_extractor.py: 13 chunks
15:42:56 - Chunked graph\graph_queries.py: 10 chunks
15:42:56 - Chunked graph\graph_storage.py: 16 chunks
15:42:56 - Chunked graph\relationship_extractors\__init__.py: 1 chunks
15:42:56 - Chunked graph\relationship_extractors\base_extractor.py: 15 chunks
15:42:56 - Chunked graph\relationship_extractors\import_extractor.py: 8 chunks
15:42:56 - Chunked graph\relationship_extractors\inheritance_extractor.py: 10 chunks
15:42:56 - Chunked graph\relationship_extractors\type_extractor.py: 11 chunks
15:42:56 - Chunked graph\relationship_types.py: 7 chunks
15:42:56 - Chunked mcp_server\__init__.py: 1 chunks
15:42:56 - Chunked mcp_server\archived\server_lowlevel.py: 10 chunks
15:42:56 - Chunked mcp_server\archived\server_lowlevel_complete.py: 17 chunks
15:42:56 - Chunked mcp_server\archived\server_lowlevel_minimal.py: 3 chunks
15:42:56 - Chunked mcp_server\guidance.py: 5 chunks
15:42:56 - Chunked mcp_server\metrics.py: 8 chunks
15:42:56 - Chunked mcp_server\server.py: 18 chunks
15:42:56 - Chunked mcp_server\tool_handlers.py: 15 chunks
15:42:56 - Chunked mcp_server\tool_registry.py: 1 chunks
15:42:56 - Chunked mcp_server\tools\__init__.py: 1 chunks
15:42:56 - Chunked mcp_server\tools\code_relationship_analyzer.py: 8 chunks
15:42:56 - Chunked merkle\__init__.py: 1 chunks
15:42:56 - Chunked merkle\change_detector.py: 10 chunks
15:42:56 - Chunked merkle\merkle_dag.py: 15 chunks
15:42:56 - Chunked merkle\snapshot_manager.py: 14 chunks
15:42:56 - Chunked scripts\__init__.py: 1 chunks
15:42:56 - Chunked scripts\list_projects_display.py: 2 chunks
15:42:56 - Chunked scripts\list_projects_parseable.py: 2 chunks
15:42:56 - Chunked scripts\manual_configure.py: 9 chunks
15:42:56 - Chunked scripts\verify_hf_auth.py: 5 chunks
15:42:56 - Chunked scripts\verify_installation.py: 19 chunks
15:42:56 - Chunked search\__init__.py: 1 chunks
15:42:56 - Chunked search\bm25_index.py: 20 chunks
15:42:56 - Chunked search\config.py: 16 chunks
15:42:56 - Chunked search\hybrid_searcher.py: 37 chunks
15:42:56 - Chunked search\incremental_indexer.py: 12 chunks
15:42:56 - Chunked search\indexer.py: 33 chunks
15:42:56 - Chunked search\query_router.py: 8 chunks
15:42:56 - Chunked search\reranker.py: 8 chunks
15:42:56 - Chunked search\searcher.py: 20 chunks
15:42:56 - Chunked tests\__init__.py: 1 chunks
15:42:56 - Chunked tests\benchmarks\capture_baseline.py: 10 chunks
15:42:56 - Chunked tests\conftest.py: 10 chunks
15:42:56 - Chunked tests\fixtures\__init__.py: 1 chunks
15:42:56 - Chunked tests\fixtures\installation_mocks.py: 16 chunks
15:42:56 - Chunked tests\fixtures\sample_code.py: 1 chunks
15:42:56 - Chunked tests\integration\__init__.py: 1 chunks
15:42:56 - Chunked tests\integration\check_auth.py: 1 chunks
15:42:56 - Chunked tests\integration\run_hybrid_tests.py: 3 chunks
15:42:56 - Chunked tests\integration\test_auto_reindex.py: 1 chunks
15:42:56 - Chunked tests\integration\test_complete_workflow.py: 2 chunks
15:42:56 - Chunked tests\integration\test_critical_fixes.py: 1 chunks
15:42:56 - Chunked tests\integration\test_cuda_detection.py: 21 chunks
15:42:56 - Chunked tests\integration\test_direct_indexing.py: 2 chunks
15:42:56 - Chunked tests\integration\test_encoding_validation.py: 3 chunks
15:42:56 - Chunked tests\integration\test_full_flow.py: 19 chunks
15:42:56 - Chunked tests\integration\test_glsl_chunker_only.py: 1 chunks
15:42:56 - Chunked tests\integration\test_glsl_complete.py: 1 chunks
15:42:56 - Chunked tests\integration\test_glsl_without_embedder.py: 1 chunks
15:42:56 - Chunked tests\integration\test_graph_search.py: 11 chunks
15:42:56 - Chunked tests\integration\test_hf_access.py: 8 chunks
15:42:56 - Chunked tests\integration\test_hybrid_search_integration.py: 23 chunks
15:42:56 - Chunked tests\integration\test_incremental_indexing.py: 13 chunks
15:42:56 - Chunked tests\integration\test_installation.py: 54 chunks
15:42:56 - Chunked tests\integration\test_installation_flow.py: 19 chunks
15:42:56 - Chunked tests\integration\test_mcp_functionality.py: 4 chunks
15:42:56 - Chunked tests\integration\test_mcp_indexing.py: 7 chunks
15:42:56 - Chunked tests\integration\test_model_switching.py: 25 chunks
15:42:56 - Chunked tests\integration\test_multi_hop_flow.py: 12 chunks
15:42:56 - Chunked tests\integration\test_phase3_relationships.py: 16 chunks
15:42:56 - Chunked tests\integration\test_semantic_search.py: 2 chunks
15:42:56 - Chunked tests\integration\test_stemming_integration.py: 12 chunks
15:42:56 - Chunked tests\integration\test_system.py: 3 chunks
15:42:56 - Chunked tests\integration\test_token_efficiency_workflow.py: 14 chunks
15:42:56 - Chunked tests\test_data\glsl_project\fragment_shader.frag: 1 chunks
15:42:56 - Chunked tests\test_data\glsl_project\simple_shader.glsl: 2 chunks
15:42:56 - Chunked tests\test_data\glsl_project\vertex_shader.vert: 1 chunks
15:42:56 - Chunked tests\test_data\multi_language\App.svelte: 3 chunks
15:42:56 - Chunked tests\test_data\multi_language\calculator.c: 10 chunks
15:42:56 - Chunked tests\test_data\multi_language\Calculator.cpp: 3 chunks
15:42:56 - Chunked tests\test_data\multi_language\Calculator.cs: 1 chunks
15:42:56 - Chunked tests\test_data\multi_language\calculator.go: 10 chunks
15:42:56 - Chunked tests\test_data\multi_language\Calculator.java: 8 chunks
15:42:56 - Chunked tests\test_data\multi_language\calculator.rs: 11 chunks
15:42:56 - Chunked tests\test_data\multi_language\Component.jsx: 2 chunks
15:42:56 - Chunked tests\test_data\multi_language\Component.tsx: 4 chunks
15:42:56 - Chunked tests\test_data\multi_language\example.js: 5 chunks
15:42:56 - Chunked tests\test_data\multi_language\example.py: 6 chunks
15:42:56 - Chunked tests\test_data\multi_language\example.ts: 7 chunks
15:42:56 - Chunked tests\test_data\python_project\main.py: 2 chunks
15:42:56 - Chunked tests\test_data\python_project\src\api\handlers.py: 18 chunks
15:42:56 - Chunked tests\test_data\python_project\src\auth\authenticator.py: 12 chunks
15:42:56 - Chunked tests\test_data\python_project\src\database\connection.py: 12 chunks
15:42:56 - Chunked tests\test_data\python_project\src\utils\helpers.py: 20 chunks
15:42:56 - Chunked tests\test_data\python_project\src\utils\validators.py: 8 chunks
15:42:56 - Chunked tests\unit\__init__.py: 1 chunks
15:42:56 - Chunked tests\unit\test_bm25_index.py: 31 chunks
15:42:56 - Chunked tests\unit\test_bm25_population.py: 1 chunks
15:42:56 - Chunked tests\unit\test_call_graph_extraction.py: 32 chunks
15:42:56 - Chunked tests\unit\test_code_relationship_analyzer.py: 15 chunks
15:42:56 - Chunked tests\unit\test_embedder.py: 2 chunks
15:42:56 - Chunked tests\unit\test_evaluation.py: 25 chunks
15:42:56 - Chunked tests\unit\test_graph_storage.py: 1 chunks
15:42:56 - Chunked tests\unit\test_hybrid_search.py: 22 chunks
15:42:56 - Chunked tests\unit\test_imports.py: 1 chunks
15:42:56 - Chunked tests\unit\test_incremental_indexer.py: 31 chunks
15:42:56 - Chunked tests\unit\test_mcp_server.py: 4 chunks
15:42:56 - Chunked tests\unit\test_merkle.py: 32 chunks
15:42:56 - Chunked tests\unit\test_model_selection.py: 29 chunks
15:42:56 - Chunked tests\unit\test_multi_language.py: 16 chunks
15:42:56 - Chunked tests\unit\test_path_normalization.py: 27 chunks
15:42:56 - Chunked tests\unit\test_priority1_extractors.py: 29 chunks
15:42:56 - Chunked tests\unit\test_relationship_types.py: 19 chunks
15:42:57 - Chunked tests\unit\test_reranker.py: 24 chunks
15:42:57 - Chunked tests\unit\test_search_config.py: 17 chunks
15:42:57 - Chunked tests\unit\test_token_efficiency.py: 38 chunks
15:42:57 - Chunked tests\unit\test_tool_handlers.py: 19 chunks
15:42:57 - Chunked tests\unit\test_tree_sitter.py: 18 chunks
15:42:57 - Chunked tools\batch_index.py: 1 chunks
15:42:57 - Chunked tools\build_complete_server.py: 2 chunks
15:42:57 - Chunked tools\build_lowlevel_server.py: 3 chunks
15:42:57 - Chunked tools\cleanup_orphaned_projects.py: 4 chunks
15:42:57 - Chunked tools\cleanup_stale_snapshots.py: 4 chunks
15:42:57 - Chunked tools\download_qwen_model.py: 1 chunks
15:42:57 - Chunked tools\extract_tool_handlers.py: 2 chunks
15:42:57 - Chunked tools\index_project.py: 3 chunks
15:42:57 - Chunked tools\search_helper.py: 10 chunks
15:42:57 - Chunked tools\switch_project_helper.py: 1 chunks
15:42:57 - Chunked tools\test_relationship_extraction.py: 1 chunks
15:42:57 - Chunked tools\test_relationship_fixes.py: 1 chunks
15:42:57 - Total chunks collected: 1445
15:42:57 - Starting embedding for 1445 chunks
15:42:57 - Using batch size 256 from config for 1445 chunks
15:42:57 - Loading model: nomic-ai/CodeRankEmbed
15:42:57 - [CACHE LOCATION MISMATCH] Model weights found in default HuggingFace cache instead of custom cache.
  Expected: C:\Users\Inter\.claude_code_search\models\models--nomic-ai--CodeRankEmbed
  Found: C:\Users\Inter\.cache\huggingface\hub\models--nomic-ai--CodeRankEmbed
  Reason: Models with trust_remote_code=True may ignore cache_folder parameter.
  Impact: Model will load successfully but from default cache location.
15:42:57 - [VALIDATED CACHE] Enabling offline mode for faster startup.
15:42:57 - [CACHE LOCATION MISMATCH] Model weights found in default HuggingFace cache instead of custom cache.
  Expected: C:\Users\Inter\.claude_code_search\models\models--nomic-ai--CodeRankEmbed
  Found: C:\Users\Inter\.cache\huggingface\hub\models--nomic-ai--CodeRankEmbed
  Reason: Models with trust_remote_code=True may ignore cache_folder parameter.
  Impact: Model will load successfully but from default cache location.
15:42:57 - Loading model from validated cache: C:\Users\Inter\.cache\huggingface\hub\models--nomic-ai--CodeRankEmbed\snapshots\3c4b60807d71f79b43f3c4363786d9493691f8b1
15:42:57 - [GPU_0] BEFORE_LOAD: Allocated=4.34GB, Reserved=4.36GB, Total=22.49GB (19.3% used)
15:42:57 - Load pretrained SentenceTransformer: C:\Users\Inter\.cache\huggingface\hub\models--nomic-ai--CodeRankEmbed\snapshots\3c4b60807d71f79b43f3c4363786d9493691f8b1
15:42:58 - <All keys matched successfully>
15:42:58 - 1 prompt is loaded, with the key: query
15:42:58 - Model loaded successfully on device: cuda:0
15:42:58 - [GPU_0] AFTER_LOAD: Allocated=4.85GB, Reserved=4.91GB, Total=22.49GB (21.6% used)
15:42:59 - Processed 256/1445 chunks
15:43:01 - Processed 512/1445 chunks
15:43:41 - Processed 768/1445 chunks
15:44:03 - Processed 1024/1445 chunks
15:44:30 - Processed 1280/1445 chunks
15:44:58 - Embedding generation completed
15:44:58 - Successfully embedded 1445 chunks
15:44:58 - Adding 1445 embeddings to index
15:44:58 - [ADD_EMBEDDINGS] Called with 1445 results
15:44:58 - [ADD_EMBEDDINGS] Calling index_documents with 1445 docs
15:44:58 - [INDEX_DOCUMENTS] Called with 1445 documents
15:44:58 - [BM25] Starting BM25 indexing...
15:44:58 - [BM25] Before indexing - size: 0
15:44:58 - [BM25_INDEX] index_documents called with 1445 docs
15:45:00 - [BM25_INDEX] BM25 index created successfully with 1445 total documents
15:45:00 - [BM25_INDEX] Successfully indexed 1445 new documents (total: 1445)
15:45:00 - [BM25] After indexing - size: 1445
15:45:00 - Created flat index with dimension 768
15:45:00 - Added 1445 embeddings to index
15:45:00 - Graph storage check before save: graph_storage=not None, nodes=2721
15:45:00 - Saving call graph with 2721 nodes to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
15:45:00 - Saved call graph: 2721 nodes, 5874 edges → C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
15:45:00 - Successfully saved call graph with 2721 nodes
15:45:00 - Hybrid indexing complete: BM25 1.60s, Dense 0.60s
15:45:00 - [ADD_EMBEDDINGS] Successfully added 1445 embeddings to hybrid index
15:45:00 - Successfully added embeddings to index
15:45:00 - [INCREMENTAL] Saving index...
15:45:00 - Saving hybrid indices
15:45:00 - [SAVE] Starting save operation
15:45:00 - [SAVE] === PRE-SAVE STATE ===
15:45:00 - [SAVE] BM25 directory exists: True
15:45:00 - [SAVE] BM25 index size: 1445 documents
15:45:00 - [SAVE] BM25 has index: True
15:45:00 - [SAVE] BM25 tokenized docs: 1445
15:45:00 - [SAVE] Dense index size: 1445 vectors
15:45:00 - [SAVE] Dense has index: True
15:45:00 - [SAVE] Overall ready state: True
15:45:00 - [SAVE] === END PRE-SAVE STATE ===
15:45:00 - [SAVE] BM25 size before save: 1445
15:45:00 - [SAVE] Calling BM25 index save...
15:45:00 - [BM25_SAVE] Starting save to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
15:45:00 - [BM25_SAVE] Saved index: 934033 bytes
15:45:00 - [BM25_SAVE] Saved docs: 5217708 bytes
15:45:00 - [BM25_SAVE] Saved metadata: 6596751 bytes (version=2, stemming=True)
15:45:00 - [BM25_SAVE] All files saved successfully
15:45:00 - [SAVE] BM25 index save completed
15:45:00 - [SAVE] Calling dense index save_index...
15:45:00 - Saved index to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\code.index
15:45:00 - [save_index] Graph storage check: graph_storage=not None, nodes=2721
15:45:00 - [save_index] Saving call graph with 2721 nodes to C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
15:45:00 - Saved call graph: 2721 nodes, 5874 edges → C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\claude-context-local_caf2e75a_coderank_call_graph.json
15:45:00 - [save_index] Successfully saved call graph
15:45:01 - [SAVE] Dense index save completed
15:45:01 - [VERIFY] Checking BM25 files in: C:\Users\Inter\.claude_code_search\projects\claude-context-local_caf2e75a_coderank_768d\index\bm25
15:45:01 - [VERIFY] bm25.index: 934033 bytes
15:45:01 - [VERIFY] bm25_docs.json: 5217708 bytes
15:45:01 - [VERIFY] bm25_metadata.json: 6596751 bytes
15:45:01 - [VERIFY] BM25 files after save: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
15:45:01 - [VERIFY] bm25.index: 934033 bytes
15:45:01 - [VERIFY] bm25_docs.json: 5217708 bytes
15:45:01 - [VERIFY] bm25_metadata.json: 6596751 bytes
15:45:01 - [SAVE] === POST-SAVE STATE ===
15:45:01 - [SAVE] BM25 directory exists: True
15:45:01 - [SAVE] BM25 files: ['bm25.index', 'bm25_docs.json', 'bm25_metadata.json']
15:45:01 - [SAVE] BM25 index size: 1445 documents
15:45:01 - [SAVE] BM25 has index: True
15:45:01 - [SAVE] Dense index size: 1445 vectors
15:45:01 - [SAVE] Dense has index: True
15:45:01 - [SAVE] Overall ready state: True
15:45:01 - [SAVE] === END POST-SAVE STATE ===
15:45:01 - [SAVE] Hybrid indices saved successfully
15:45:01 - Successfully saved hybrid indices
15:45:01 - [INCREMENTAL] Index saved
15:45:01 - [INCREMENTAL] GPU cache cleared after indexing
15:45:01 - Completed indexing with nomic-ai/CodeRankEmbed in 126.01s
15:45:01 - Loaded search config from C:\Users\Inter/.claude_code_search/search_config.json
15:45:01 - Search mode: semantic, hybrid enabled: True
15:45:01 - Saved search config to C:\Users\Inter/.claude_code_search/search_config.json
15:45:01 - Restored original model: Qwen/Qwen3-Embedding-0.6B

======================================================================
INDEXING RESULTS
======================================================================
[OK] Indexing completed successfully

Project: F:\RD_PROJECTS\COMPONENTS\claude-context-local
Mode: full

Multi-Model: Enabled (3 models)

  [Qwen3-Embedding-0.6B (1024d)]
    Files added: 136
    Files modified: 0
    Files removed: 0
    Chunks added: 1445
    Time: 26.47s

  [bge-m3 (1024d)]
    Files added: 136
    Files modified: 0
    Files removed: 0
    Chunks added: 1445
    Time: 20.23s

  [CodeRankEmbed (768d)]
    Files added: 136
    Files modified: 0
    Files removed: 0
    Chunks added: 1445
    Time: 126.01s

Total time: 172.71 seconds
Total files added: 408
Total chunks added: 4335
======================================================================