# Changelog

All notable changes to the Claude Context Local (MCP) semantic code search system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Changed

- No unreleased changes

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
