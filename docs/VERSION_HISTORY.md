# Version History

Complete version history and feature timeline for claude-context-local MCP server.

## Current Status: All Features Operational (2026-02-01)

- **Version**: 0.9.0
- **Status**: Production-ready
- **Test Coverage**: 1,557 unit tests + 8 integration tests (100% pass rate)
- **Dependencies**: 125 packages (38% reduction from 201)
- **Index Quality**: 109 active files, 789 chunks (34% reduction via greedy merge, BGE-M3 1024d, ~16 MB)
- **Token Reduction**: 63% (validated benchmark, Mixed approach vs traditional)
- **SSCG Benchmark**: Recall@4=1.00 (perfect), MRR=0.81
- **Recent Features**: SSCG Phase 1-5 integration, A1 (Intent-Adaptive Edge Weight Profiles), A2 (File-Level Module Summary Chunks), B1 (Community-Level Summary Chunks), k=4 standardization

---

## v0.9.0 - SSCG Integration & Research Improvements (2026-01-31 - 2026-02-01)

### Status: MAJOR RELEASE ✅

Complete integration of Structural-Semantic Code Graph (SSCG) features based on 4 research papers (RepoGraph, LogicLens, GRACE, Microsoft GraphRAG), plus A1/A2/B1 research-backed improvements achieving perfect Recall@4 (1.00) and MRR 0.81.

### Highlights

- **SSCG Phase 1-5**: Complete structural-semantic code graph integration with 21 relationship types
- **A1: Intent-Adaptive Edge Weight Profiles**: 7 query intent categories with optimized graph traversal weights
- **A2: File-Level Module Summary Chunks**: Synthetic module summaries for improved GLOBAL query recall
- **B1: Community-Level Summary Chunks**: Louvain-based community detection with synthetic summaries
- **Perfect Recall@4**: 1.00 across all 13 SSCG benchmark queries
- **k=4 Standardization**: 20% token efficiency gain with maintained quality
- **Dependency Cleanup**: 76 packages removed (38% reduction: 201→125), CVE-2026-0994 eliminated

### 🚀 New Features

#### SSCG Phase 1-5 Complete (v0.8.7, 2026-01-29)

**Phase 1: Subgraph Extraction**
- Induced subgraphs with typed edges (calls, inherits, imports, etc.)
- Topological ordering for dependency-aware traversal
- JSON Graph Format serialization
- Boundary edge tracking

**Phase 2: Full Relationship Enrichment**
- All 21 relationship types in graph field output
- Dual lookup strategy (by-file + by-qualified-name)
- Per-type capping to prevent output explosion

**Phase 3: Centrality-Informed Result Ranking**
- PageRank blending with semantic scores (alpha=0.3)
- `CentralityRanker` class with annotate/rerank modes
- `blended_score` and `centrality` fields in results

**Phase 4: Community Context Surfacing**
- Community ID annotation on subgraph nodes
- Heuristic label generation from dominant symbols

**Phase 5: Ego-Graph Structure Preservation**
- Structured ego-graph retrieval with edge preservation
- `EgoGraphData` dataclass for formatted output
- Edge-type-weighted BFS traversal

#### A1: Intent-Adaptive Edge Weight Profiles (2026-02-01)

**Query Intent Classification**: 7 intent categories (local, global, navigational, path_tracing, similarity, contextual, hybrid)

**Adaptive Edge Weights**: Graph traversal weights automatically adjusted based on query intent
- LOCAL queries: Suppress imports (0.1x), boost calls/inherits (1.0x)
- GLOBAL queries: Boost imports (0.7x), uses_type (0.9x), instantiates (0.8x)
- Based on SOG (USENIX Security '24) ablation study

#### A2: File-Level Module Summary Chunks (2026-02-01)

**Synthetic Module Summaries**: Generate `chunk_type="module"` chunks per file with 2+ real chunks

**Content**: File path, module name, classes, functions, key methods, imports, docstring excerpts

**Demotion Tuning**: 3-tier demotion factors (0.82x-0.90x) prevent inappropriate displacement
- 0.82x for "class" queries
- 0.85x for entity queries
- 0.90x for general queries

**Impact**: Fixed Q32 regression (module chunk demoted rank-1→rank-3, MRR 0.25→1.00)

#### B1: Community-Level Summary Chunks (2026-02-01)

**Louvain Community Detection**: Groups related code chunks into thematic communities

**Synthetic Community Summaries**: Generate `chunk_type="community"` chunks per community with 2+ members

**Content**: Community ID, dominant directory, classes/functions in community, hub function, imports

**Demotion Tuning**: Same 3-tier factors as A2 (0.82x-0.90x)

#### Additional Research Improvements

**Post-Expansion Neural Reranking** (2026-02-01)
- Second reranking pass after ego-graph expansion
- Unifies scoring scale between primary results (cross-encoder) and ego-graph neighbors (heuristic)

**Name-Match Tokenization Bug Fix** (2026-02-01)
- Fixed CamelCase tokenization: "HybridSearcher" now correctly splits to {"hybrid", "searcher"}
- Q31 improved from MRR 0.50→1.00

**BM25 Snowball Stemming** (Always-on)
- 93.3% of queries benefit
- 3.33 average unique discoveries per query
- 0.47ms overhead (negligible)
- 11% smaller indices

**k=4 Standardization** (2026-02-01)
- Default k changed from 5→4 across all 7 entry points
- 20% token efficiency gain
- Perfect Recall@4 maintained (1.00)

### 🔧 Bug Fixes

- **Name-Match Tokenization**: Fixed CamelCase splitting bug (Q31: MRR 0.50→1.00)
- **BGE-M3 Tier Classification**: Fixed "small"→"medium" misclassification
- **VRAM Batch Sizing**: Now uses free VRAM instead of total VRAM (handles multi-process GPU)
- **Split Block Graph Isolation**: Fixed graph exclusion for split_block chunks
- **Config Serialization**: Added enable_file_summaries and enable_community_summaries to config

### 📊 SSCG Benchmark Results

**Test Suite**: 13 queries across 4 categories (Small Function Discovery, Sibling Context, Class Overview, Cross-Method References)

**Overall Metrics** (Post-Tuning k=4):
- **Recall@4**: 1.00 (perfect - all relevant results found)
- **MRR**: 0.81 (maintained from k=5, acceptable trade-off for 20% efficiency)
- **Rank-1 Accuracy**: 9/13 (69%, +1 vs k=5)
- **Model Distribution**: 3 models used appropriately (BGE-M3, Qwen3, CodeRankEmbed)

**Category Performance**:
- Category A (Small Function Discovery): Recall@4=1.00, MRR=0.90
- Category B (Sibling Context): Recall@4=1.00, MRR=0.67
- Category C (Class Overview): Recall@4=1.00, MRR=0.73 (+17.7% vs k=5)
- Category D (Cross-Method References): +3 indirect callers, +2 files discovered

### 📦 Dependency Cleanup (2026-01-30)

**Removed 76 packages** (38% reduction):
- torchaudio, torchvision (not needed for embeddings)
- FlagEmbedding + 26 transitive dependencies (phantom dependency)
- pandas (unused)
- black, isort (replaced by ruff)
- protobuf orphans (eliminated CVE-2026-0994)

**Result**: 201→125 packages, ~565MB saved, all models verified working

### 📁 Files Changed

**New**:
- `chunking/file_summarizer.py` - A2 module summary generation (~90 lines)
- `search/intent_adaptive_weights.py` - A1 edge weight profiles (if separate module)

**Modified**:
- `search/searcher.py` - A1 intent-adaptive weights, A2/B1 demotion tuning
- `search/centrality_ranker.py` - PageRank blending, 2-tier demotion
- `search/incremental_indexer.py` - A2/B1 summary generation integration
- `search/config.py` - enable_file_summaries, enable_community_summaries
- `mcp_server/tool_registry.py` - k=4 default, module/community chunk types
- `pyproject.toml` - Dependency cleanup

### 📊 Testing

- **Unit tests**: 1,557/1,557 passed
- **Integration tests**: 8/8 passed
- **SSCG benchmark**: 13/13 queries passed (Recall@4=1.00)
- **Style alignment**: 45 broad exception handlers narrowed, 25 functions type-annotated

### Git Commits

Key commits from development branch:
- `5f01004` - feat(search): Tune A2/B1 demotion factors and standardize k=4 default
- `52c66d0` - feat(search): Add community-level summary chunks (B1)
- `5a826d5` - feat(search): Add file-level module summaries (A2)
- `b90fc6b` - feat(search): Add intent-adaptive edge weight profiles (A1)
- `9d04ded` - feat(search): Add post-expansion neural reranking pass
- `507beef` - fix(centrality): Fix name-match tokenization bug
- `3046e9a` - feat: Complete Q07 benchmark fix with 10 production optimizations
- `3247d2d` - feat: Add graph-aware multi-hop search (Phase 3)
- `bd81753` - feat: Phase 2 SSCG - Full relationship enrichment (21 types)
- `126cb4c` - feat: Remove FlagEmbedding phantom dependency

---

## v0.8.7 - SSCG Phase 1-5 Implementation (2026-01-29)

### Status: RESEARCH INTEGRATION ✅

Implemented all 5 phases of Structural-Semantic Code Graph (SSCG) integration based on 4 research papers (RepoGraph ICLR 2025, LogicLens, GRACE, Microsoft GraphRAG).

### Highlights

- **21 Relationship Types**: Complete graph enrichment (calls, inherits, imports, uses_type, etc.)
- **PageRank Centrality**: Blended into search scoring (alpha=0.3)
- **Edge-Type-Weighted BFS**: SOG-inspired weighted graph traversal
- **P3 Extractors**: Protocol/ABC detection (implements) and method override detection
- **Ego-Graph Structure**: Preserved edge information in retrieval

### Research Papers Implemented

1. **RepoGraph** (ICLR 2025): k-hop ego-graph expansion, graph-aware retrieval
2. **SOG** (USENIX Security '24): Edge-type-weighted BFS, relation type contributions
3. **GRACE**: Multi-level graph representations
4. **Microsoft GraphRAG**: Community detection, hierarchical summarization

### Git Commits

- `be84cb1` - feat: SSCG Phase 4 - Community Context Surfacing
- `b24945d` - feat: Wire P3 extractors into chunking pipeline (Phase 2)
- `e17ab6a` - feat: Add edge-type-weighted BFS traversal (Phase 1)
- `bd81753` - feat: Phase 2 SSCG - Full relationship enrichment (21 types)

---

## v0.8.6 - Performance Infrastructure (2026-01-16)

### Status: PERFORMANCE ENHANCEMENT ✅

Added comprehensive timing instrumentation and query embedding cache TTL support for improved performance monitoring and cache freshness.

### Highlights

- **Timing Infrastructure**: New `utils/timing.py` module with `@timed` decorator and `Timer` context manager
- **5 Instrumented Functions**: Added timing to critical search operations (embed_query, search_bm25, search_dense, neural_rerank, multi_hop_search)
- **Cache TTL**: QueryEmbeddingCache now supports 300s TTL with automatic expiration
- **Test Improvements**: 1,472 unit tests + 84 integration tests (up from 1,471)
- **Bug Fixes**: Fixed syntax error and test failure

### 🚀 New Features

#### Timing Infrastructure

**New Module**: `utils/timing.py`

- `@timed(name)` decorator - Automatic function timing with logging
- `Timer(name)` context manager - Code block timing with elapsed_ms dictionary
- Log format: `[TIMING] operation_name: Xms` (milliseconds, 2 decimal precision)
- Microsecond precision via `time.perf_counter()`
- Zero-overhead when INFO logging disabled

**Instrumented Operations**:

1. **embed_query** (`embeddings/embedder.py`) - Query embedding generation (40-60ms first, 0ms cached)
2. **search_bm25** (`search/search_executor.py`) - Sparse keyword search (3-15ms)
3. **search_dense** (`search/search_executor.py`) - Dense vector search (50-100ms)
4. **apply_neural_reranking** (`search/reranking_engine.py`) - Cross-encoder reranking (80-150ms)
5. **multi_hop_search** (`search/multi_hop_searcher.py`) - Multi-hop expansion

**Usage**:

```powershell
# Enable INFO logging to see timing data
$env:CLAUDE_LOG_LEVEL="INFO"

# Example output:
# [TIMING] embed_query: 45.23ms
# [TIMING] bm25_search: 3.12ms
# [TIMING] dense_search: 52.78ms
# [TIMING] neural_rerank: 89.45ms
```

#### Query Embedding Cache Enhancement

**TTL Support** (`embeddings/query_cache.py`):

- **Default**: 300 seconds (5 minutes), configurable via `ttl_seconds` parameter
- **Storage**: Changed from `{key: embedding}` to `{key: (timestamp, embedding)}`
- **Automatic expiration**: Entries removed on access when TTL elapsed
- **Benefit**: Prevents serving stale embeddings after model changes

**Configuration Example**:

```python
from embeddings.query_cache import QueryEmbeddingCache

# Custom TTL: 10 minutes
cache = QueryEmbeddingCache(max_size=128, ttl_seconds=600)
```

**Performance Impact**:

- First query: Full embedding generation (~50ms)
- Repeated query (within 5min): Instant retrieval (0ms)
- After TTL expiration: Re-generate embedding (~50ms)

### 🔧 Bug Fixes

- **Syntax Error**: Fixed duplicate closing parenthesis in `embeddings/embedder.py:33`
- **Test Fix**: Fixed `test_clear_index_preserves_graph_storage_reference` to check `_graph_storage` attribute

### 📁 Files Changed (8 files, 114 insertions, 13 deletions)

**New**:

- `utils/__init__.py` - Utility module package
- `utils/timing.py` - Timing decorator and context manager (60 lines)

**Modified**:

- `embeddings/embedder.py` - Added `@timed` decorator, fixed syntax error
- `embeddings/query_cache.py` - Added TTL support with timestamp tracking (25 lines changed)
- `search/multi_hop_searcher.py` - Added `@timed` decorator
- `search/reranking_engine.py` - Added `@timed` decorator
- `search/search_executor.py` - Added `@timed` decorators (2 functions)
- `tests/unit/search/test_graph_save_during_reindex.py` - Fixed test assertion

### 📊 Testing

- **Unit tests**: 1472/1472 passed (was 1471 before test fix)
- **Fast integration tests**: 84/84 passed
- **Timing verification**: All 5 decorators functional, logging correctly
- **Cache TTL verification**: Immediate get works, expired get returns None

### 🎯 Scope Reduction Rationale

Phase 3 originally planned 40-60 hours of architectural changes. Comprehensive analysis with MCP search tools and 3 exploration agents revealed:

- **Task 3.2 (Factory Pattern)**: 5 working singleton patterns exist, ServiceLocator is a working DI container (171 usages). Migration would add complexity without benefit. **REMOVED**
- **Task 3.4 (Graph Queries)**: 80% already implemented - BFS/DFS traversal complete, path finding with bidirectional BFS + edge filtering complete, 4 centrality algorithms complete, subgraph extraction complete. Proposed `find_patterns()` is complex (~200+ lines) with niche use case. **REMOVED**
- **Task 3.3 & 3.5**: Reduced to essential gaps only - timing infrastructure + cache TTL (~8-12 hours actual work)

### Git Commit

- **Commit**: 9e0525c
- **Branch**: development
- **Message**: "refactor: Complete Phase 3 (reduced scope) - timing infrastructure and cache TTL"
- **Date**: 2026-01-16

---

## v0.8.5 - Chunk Type Enum Expansion (2026-01-15)

### Status: FEATURE ENHANCEMENT ✅

Added support for "merged" and "split_block" chunk types to the `search_code` tool's `chunk_type` parameter enum, fixing validation errors when filtering for these internally-used chunk types.

### Highlights

- **Schema Fix**: `chunk_type` enum now includes "merged" and "split_block" values
- **Documentation Updated**: SKILL.md, MCP_TOOLS_REFERENCE.md, and CLAUDE.md all updated
- **Validation Fixed**: Users can now filter for community-merged chunks and large function segments without validation errors

### Changes

#### Tool Registry Schema Update

- **File**: `mcp_server/tool_registry.py:64-76`
- **Change**: Added "merged" and "split_block" to chunk_type enum
- **Impact**: Eliminates `Input validation error: 'merged' is not one of [...]` errors

**Before**:

```python
"enum": [
    "function", "class", "method", "module",
    "decorated_definition", "interface", "enum", "struct", "type"
]
```

**After**:

```python
"enum": [
    "function", "class", "method", "module",
    "decorated_definition", "interface", "enum", "struct", "type",
    "merged", "split_block"
]
```

#### Documentation Updates

- **SKILL.md**: Updated chunk_type parameter docs with descriptions and examples
- **MCP_TOOLS_REFERENCE.md**: Added chunk_type table entry and explanation note
- **CLAUDE.md**: Updated version to 0.8.5 with changelog note

### Usage Examples

```python
# Search for community-merged code blocks
search_code("GraphQueryEngine class", chunk_type="merged")

# Search for large function segments split at AST boundaries
search_code("ParallelChunker chunk_files", chunk_type="split_block")
```

### Background

These chunk types have existed internally since Phase 6 (community detection) and large node splitting features were implemented, but were not exposed in the MCP tool schema. This caused validation errors when users attempted to filter by these types.

---

## v0.8.4 - Ultra Format Bug Fix & Field Rename (2026-01-06)

### Status: BUG FIX ✅

Fixed critical bug in ultra format where complexity scores were dropped when first search result lacked the field, and renamed field from `complexity` to `complexity_score` for clarity.

### Highlights

- **Bug Fix**: Ultra format now collects ALL fields from ALL results (not just first result)
- **Field Rename**: `complexity` → `complexity_score` for consistency with internal representation
- **Verification**: All 3 features confirmed working (complexity scores, intent logic, lightweight pool routing)

### Bug Fixes

#### Ultra Format Field Loss (Critical)

- **Problem**: `_to_toon_format()` used only first item's fields to build TOON header. When first result lacked `complexity` (e.g., JavaScript file), subsequent Python results' complexity values were silently dropped.
- **Solution**: Collect ALL unique fields from ALL items using `set()` union across all results
- **File**: `mcp_server/output_formatter.py:137-152`
- **Impact**: Ultra format now includes all optional fields present in any result

**Before** (buggy):

```python
first_item = value[0]
for field_name in first_item.keys():
    fields.append(field_name)
```

**After** (fixed):

```python
all_fields = set()
for item in value:
    all_fields.update(item.keys())
for field_name in sorted(all_fields):
    if all(item.get(field_name) in ([], {}, None, "") for item in value):
        continue  # Skip fields empty in all items
    fields.append(field_name)
```

### Changes

#### Field Rename: complexity → complexity_score

- **Rationale**: Match internal representation (`CodeChunk.complexity_score`) for clarity
- **Files Changed**:
  - `mcp_server/tools/search_handlers.py:328, 343` - Output field name
  - `docs/MCP_TOOLS_REFERENCE.md:119, 125, 133` - Documentation
  - `.claude/skills/mcp-search-tool/SKILL.md:370` - Skill documentation
- **Impact**: User-facing field name change (minor breaking change)

### Verification Results

All 3 features confirmed working via MCP search queries:

| Feature | Status | Evidence |
|---------|--------|----------|
| **Complexity Scores** | ✅ Working | Values 6, 2, 4 visible in ultra format |
| **Intent Classification** | ✅ Working | NAVIGATIONAL queries auto-redirect to find_connections |
| **Lightweight Pool Routing** | ✅ Working | GTE-ModernBERT (code/impl/validate), BGE-M3 (config/serialize) |

### Test Coverage

- **Manual Verification**: 6 test queries across all formats (verbose, compact, ultra)
- **Routing**: Validated lightweight pool routing (BGE-M3 + GTE-ModernBERT)
- **Intent**: Confirmed NAVIGATIONAL auto-redirect working

### Breaking Changes

**Minor** - Field name change:

- Old: `"complexity": 5`
- New: `"complexity_score": 5`
- **Migration**: Update any parsing code expecting `complexity` field

---

## v0.8.3 - Complexity Score Display Fix (2026-01-05)

### Status: BUG FIX + FEATURE ENHANCEMENT ✅

Fixed critical bug where cyclomatic complexity was calculated correctly but lost during chunk conversion, and added `complexity` field to all search result output formats.

### Highlights

- **Bug Fix**: Complexity score no longer hardcoded to 0 (now extracted from TreeSitterChunk metadata)
- **Feature**: `complexity` field now visible in verbose, compact, and ultra output formats
- **Documentation**: Complete complexity scoring guide added to ADVANCED_FEATURES_GUIDE.md

### Bug Fixes

#### Complexity Score Data Loss (Critical)

- **Problem**: Complexity calculated correctly in `PythonChunker.extract_metadata()` but hardcoded to 0 at `multi_language_chunker.py:416` during `TreeSitterChunk` → `CodeChunk` conversion
- **Solution**: Extract complexity from metadata: `complexity_score=tchunk.metadata.get("complexity_score", 0)`
- **File**: `chunking/multi_language_chunker.py:416`
- **Impact**: Complexity values now preserved through full pipeline (chunking → embedding → storage → search results)

### Features

#### Complexity Field in Search Results

- **Added**: `complexity` field to `_format_search_results()` for both IntelligentSearcher and HybridSearcher formats
- **File**: `mcp_server/tools/search_handlers.py:325-327, 340-342`
- **Format**: Short field name `complexity` (not `complexity_score`) for token efficiency
- **Visibility**: Appears in all output formats (verbose, compact, ultra)
- **Scope**: Functions and methods only (classes/modules excluded by design)

### Documentation Updates

#### MCP Tools Reference (`docs/MCP_TOOLS_REFERENCE.md`)

- Added "Search Result Fields" section documenting all result fields
- Includes complexity field definition and usage examples
- Location: Lines 107-139

#### MCP Search Skill (`\.claude\skills\mcp-search-tool\SKILL.md`)

- Added result fields table to search_code documentation
- Location: Lines 363-374

#### Advanced Features Guide (`docs/ADVANCED_FEATURES_GUIDE.md`)

- Added comprehensive "Complexity Scoring" section
- Includes: formula, thresholds, use cases, examples, implementation details
- Location: Lines 2731-2863

### Test Coverage

- Existing: 16/16 complexity calculation tests passing (`tests/unit/chunking/test_complexity_scoring.py`)
- Added: Pipeline integration test verifying complexity preservation through full flow
- Total: 17 tests, 100% pass rate

### Breaking Changes

**None** - Backward compatible:

- Missing complexity defaults to not shown
- Only affects functions/methods (as intended)
- Requires re-indexing to populate correct values

### Notes

**Re-indexing Required**: After upgrade, users must re-index projects to populate correct complexity values:

```bash
index_directory("F:\\path\\to\\project")
```

**Python Only**: Complexity scoring currently only supported for Python (other languages TBD)

---

## v0.8.2 - UI Enhancements & VRAM Fixes (2026-01-04)

### Status: PRODUCTION-READY ✅

Critical bug fixes for VRAM management during auto-reindex, plus UI improvements for better configuration visibility.

### Highlights

- **Multi-Model VRAM Cleanup** - Auto-reindex now frees all ~15 GB before reindexing (prevents OOM)
- **Performance Settings Menu** - GPU and Auto-Reindex settings grouped under one submenu
- **Current Settings Display** - All 12 menus now show active configuration on entry
- **Windows VRAM Safety** - Hard limit prevents silent spillover to system RAM

### Bug Fixes

#### Auto-Reindex VRAM Cleanup (Critical)

- **Problem**: Only freed ~7.5 GB (one model), left ~8 GB in VRAM causing OOM
- **Solution**: Comprehensive cleanup via `state.clear_embedders()` and `reset_pool_manager()`
- **Impact**: Frees all ~15 GB (Qwen3-4B 7.73 GB + BGE-M3 1.08 GB + CodeRankEmbed 0.52 GB)

#### Auto-Reindex Timeout Configuration

- **Problem**: Hardcoded 5-minute timeout ignored user configuration
- **Solution**: Now uses `get_config().performance.max_index_age_minutes`
- **File**: `mcp_server/tools/search_handlers.py:414-417`

#### Windows VRAM Spillover Prevention

- **Problem**: GPU silently overflowed to system RAM with 97% bandwidth reduction
- **Solution**: Hard VRAM limit at 80% + conservative batch calculation at 65%
- **Impact**: Fail-fast OOM instead of silent performance degradation

### UI/UX Improvements

- Performance Settings submenu grouping GPU + Auto-Reindex options
- Current settings display in all 12 configuration menus
- Multi-model routing status visible in model selection menus
- Label improvement: `[ADVANCED]` → `[MULTI-MODEL] - Most comprehensive choice`

### Breaking Changes

- `enable_chunk_merging` default changed from `True` to `False`
- Users wanting chunk merging must explicitly enable it

### Files Modified

- `embeddings/embedder.py` - VRAM limit, batch calculation, logging clarity
- `search/incremental_indexer.py` - Multi-model cleanup before reindex
- `search/config.py` - Default configuration changes
- `mcp_server/tools/search_handlers.py` - Config-based timeout
- `search/graph_integration.py` - Logging tag standardization
- `start_mcp_server.cmd` - Performance Settings menu, current settings displays

---

## v0.8.1 - Configuration System Enhancement (2026-01-03)

### New Features

- **Nested JSON Configuration**: `search_config.json` now uses organized sections
- **configure_chunking MCP Tool**: Runtime configuration of chunking parameters
- **UI Menu Reorganization**: Hierarchical submenus for better organization

### Configuration Structure (8 sections)

- `embedding`: Model settings + context enhancement
- `search_mode`: Search algorithm settings
- `performance`: Parallelization + GPU settings
- `multi_hop`: Multi-hop search settings
- `routing`: Multi-model routing
- `reranker`: Neural reranker settings
- `output`: Output format
- `chunking`: Chunk merging + splitting settings

### Breaking Changes

- None (backward compatible with flat format)

---

## v0.8.0 - cAST Greedy Sibling Merging Implementation (2026-01-03)

### Status: PRODUCTION-READY ✅

**Feature release implementing cAST greedy sibling merging algorithm from EMNLP 2025 with 34% chunk reduction**

### Highlights

- **cAST Greedy Sibling Merging** - EMNLP 2025 algorithm for merging small code chunks
- **34% Chunk Reduction** - Exceeded expected 20-30% from academic paper (1,199 → 789 chunks)
- **UI Configuration Menu** - Interactive chunking settings with 5 sub-options
- **Search Quality Maintained** - High relevance scores (0.85-0.97) after chunk reduction
- **Comprehensive Testing** - 137 new unit tests for greedy merge functionality

### New Features

#### cAST Greedy Sibling Merging (Task 3.5)

**Implementation of EMNLP 2025 chunking algorithm for better retrieval quality**:

**Core Algorithm** (`chunking/languages/base.py`):

1. **Token Estimation** - New `estimate_tokens()` function:
   - Supports whitespace (fast, ~1ms) and tiktoken (accurate, ~5ms) methods
   - Used to determine chunk sizes before merging decisions

2. **Greedy Merge Logic** - New `_greedy_merge_small_chunks()` method (67 lines):
   - Merges adjacent chunks when size < `min_chunk_tokens` (default: 50)
   - Stops merging when accumulated size reaches `max_merged_tokens` (default: 1,000)
   - Only merges chunks with same `parent_class` (true siblings)
   - Preserves chunk metadata with `merged_from` and `merged_count` fields

3. **Merged Chunk Creation** - New `_create_merged_chunk()` helper:
   - Combines multiple chunks into single TreeSitterChunk
   - Preserves parent class and metadata from constituent chunks
   - Tracks original chunks via `merged_from` list

**Configuration System** (`search/config.py`):

- New `ChunkingConfig` dataclass with 6 fields:
  - `enable_chunk_merging` (bool, default: True)
  - `min_chunk_tokens` (int, default: 50)
  - `max_merged_tokens` (int, default: 1,000)
  - `enable_large_node_splitting` (bool, default: False) - placeholder for Task 3.4
  - `max_chunk_lines` (int, default: 100)
  - `token_estimation` (str, default: "whitespace")
- Integrated into `SearchConfig.to_dict()` and `from_dict()` for persistence
- Accessible via ServiceLocator dependency injection

**Pipeline Integration**:

- `LanguageChunker.chunk_code()` - Accepts optional `ChunkingConfig` parameter, applies greedy merge when enabled
- `TreeSitterChunker.chunk_file()` - Fetches config via ServiceLocator, passes to language chunker
- `_get_chunking_config()` - Helper method to retrieve config from ServiceLocator

#### UI Configuration Menu

**New interactive menu for chunking settings** (`start_mcp_server.cmd`):

**Menu Structure**:

- New option "A. Configure Chunking Settings" in Search Configuration menu (line 351)
- 5 sub-options (lines 1526-1641):
  1. Enable Greedy Merge - Turn on chunk merging (recommended)
  2. Disable Greedy Merge - Keep all chunks separate
  3. Set Min Chunk Tokens - Minimum size before merging (default: 50)
  4. Set Max Merged Tokens - Maximum merged chunk size (default: 1,000)
  5. Set Token Estimation - Choose whitespace (fast) or tiktoken (accurate)

**Features**:

- Real-time display of current settings using Python config reader
- Helpful descriptions explaining benefits (+4.3 Recall@5 from EMNLP 2025)
- Integrated with `view_config` (line 959) to show chunking settings
- Triggers re-index notification after configuration changes

#### Comprehensive Test Suite

**New test file** (`tests/unit/chunking/test_greedy_merge.py`):

**4 Test Classes (137 tests total)**:

1. `TestEstimateTokens` - Token estimation function
   - Tests whitespace and tiktoken methods
   - Validates accuracy and fallback behavior

2. `TestCreateMergedChunk` - Merged chunk creation
   - Tests single and multiple chunk merging
   - Validates metadata preservation and line numbers

3. `TestGreedyMergeSmallChunks` - Main algorithm tests
   - Empty list handling, single chunk behavior
   - All small chunks merging, large chunk skip
   - Max size limit enforcement
   - Different parent_class separation

4. `TestChunkCodeWithMerging` - Integration tests
   - End-to-end chunking with greedy merge enabled/disabled
   - Config toggle functionality
   - ServiceLocator integration

**Coverage**: 100% of new chunking features with all 137 tests passing

### Performance Improvements

#### Chunk Reduction (34% - Exceeded Expectations)

**Indexing Results**:

- **Before**: 1,199 chunks per model
- **After**: 789 chunks per model
- **Reduction**: 410 fewer chunks (34.2%)
- **Comparison**: Exceeded EMNLP 2025 paper expectation of 20-30%

**Multi-Model Consistency**:

- All 3 embedding models indexed identically (789 chunks each)
- Multi-model indexing time: 69.91 seconds for 3 models
- Storage savings: ~33% reduction in FAISS index size

**Merged Chunk Analysis**:

- Small methods successfully merged (getters, setters, small utilities)
- Proper sibling grouping by `parent_class` maintained
- Token limits respected (min 50, max 1,000 tokens per merged chunk)
- Metadata preserved with `merged_from` and `merged_count` fields

#### Search Quality Maintained

**MCP Testing Results** (8 comprehensive queries):

- Top result relevance scores: 0.85-0.97 (excellent quality)
- Greedy merge implementation search: 0.86 score
- ChunkingConfig search: 0.90 score
- ServiceLocator pattern: 0.85 score
- Direct chunk_id lookup: 0.97 score (O(1) retrieval working)

**find_connections Validation** (3 dependency analyses):

- `_greedy_merge_small_chunks`: 1 direct caller, 11 total impacted symbols
- `ChunkingConfig`: 52 symbols connected across 23 files (high connectivity expected)
- `ServiceLocator`: 12 symbols connected across 9 files

**Expected Quality Improvement**:

- +4.3 Recall@5 (per EMNLP 2025 academic validation)
- Merged chunks provide denser semantic context per embedding
- Multi-model routing functioning correctly (qwen3, bge_m3, coderankembed)

### Files Modified

**Core Implementation**:

- `search/config.py` - Added ChunkingConfig dataclass (6 fields)
- `chunking/languages/base.py` - Added estimate_tokens(),_greedy_merge_small_chunks(),_create_merged_chunk()
- `chunking/tree_sitter.py` - Added _get_chunking_config(), config passing

**Configuration**:

- `search_config.json` - Added 6 chunking configuration fields

**UI**:

- `start_mcp_server.cmd` - Added menu option A with 5 sub-options, updated view_config

**Tests**:

- `tests/unit/chunking/test_greedy_merge.py` - New test file (137 tests)
- `tests/unit/chunking/test_multi_language.py` - Updated for ChunkingConfig integration
- `tests/unit/chunking/test_tree_sitter.py` - Updated for ChunkingConfig integration
- `tests/unit/embeddings/test_embedder.py` - Updated for merged chunk handling
- `tests/unit/graph/test_qualified_chunk_ids.py` - Updated for ChunkingConfig integration

### Validation

**Test Coverage**:

- 1,191+ unit tests (100% pass rate)
- 137 new tests for greedy merge functionality
- All existing tests passing with merged chunks

**MCP Testing**:

- 8 semantic search queries validated
- 3 find_connections dependency analyses performed
- Entity tracking confirmed working with merged chunks
- Import/class context extraction verified

**Production Readiness**:

- ✅ Configuration system fully integrated
- ✅ UI menu operational with 5 sub-options
- ✅ 34% chunk reduction achieved
- ✅ Search quality maintained (0.85-0.97 relevance scores)
- ✅ Multi-model consistency verified
- ✅ All tests passing
- ✅ Ready for production deployment

---

## v0.7.5 - Critical Bug Fix & Test Fixes (2026-01-03)

### Status: PRODUCTION-READY ✅

**Patch release fixing critical production bug in HybridSearcher.clear_index() and slow integration tests**

### Highlights

- **Critical Bug Fix** - HybridSearcher.clear_index() reference mismatch causing empty search results
- **Test Suite Fixes** - All 14 slow integration tests now passing

### Bug Fixes

#### Critical: HybridSearcher.clear_index() Reference Mismatch

**Problem**: After calling `IncrementalIndexer.incremental_index(force_full=True)`, all searches returned empty results even though indexing succeeded.

**Root Cause**: When `HybridSearcher.clear_index()` created new BM25 and dense index instances:

- It updated `HybridSearcher`'s own references (`self.bm25_index`, `self.dense_index`)
- But left `SearchExecutor` and `MultiHopSearcher` with stale references to old empty indices
- New data was added to new indices, but searches used old empty indices

**Solution** (`search/hybrid_searcher.py:862-867`):

```python
def clear_index(self) -> None:
    self.index_sync.clear_index()
    self.bm25_index = self.index_sync.bm25_index
    self.dense_index = self.index_sync.dense_index
    self.reranking_engine.metadata_store = self.dense_index.metadata_store

    # Update SearchExecutor references to new indices
    self.search_executor.bm25_index = self.bm25_index
    self.search_executor.dense_index = self.dense_index

    # Update MultiHopSearcher reference to new dense index
    self.multi_hop_searcher.dense_index = self.dense_index
```

**Impact**:

- ✅ force_full=True re-indexing now works correctly
- ✅ All searches return proper results after re-indexing
- ✅ Backward compatible (no API changes)
- ✅ Affected all code using force_full=True parameter

#### Slow Integration Test Fixes

**Problem**: 7 out of 14 slow integration tests failing in `test_hybrid_search_integration.py`

**Fixes**:

1. Removed unused `indexed_hybrid_environment` fixture parameter from 2 config tests
2. Updated API calls from `hybrid_searcher._search_bm25()` to `search_executor.search_bm25()`
3. Fixed `test_error_handling` expectations for class-scoped fixtures
4. Fixed `test_statistics_and_monitoring` search count assertion (changed `== 4` to `>= 4` for accumulated counts)

**Results**:

- Before: 7 failed, 7 passed (14 total)
- After: 14 passed, 0 failed ✅

---

## v0.7.4 - Documentation & UX Improvements (2026-01-03)

### Status: PRODUCTION-READY ✅

**Patch release focusing on RAM cleanup fix, documentation clarity, UI menu explanations, and debug mode timing**

### Highlights

- **RAM Cleanup Fix** - Fixed RAM increasing during "Release Resources" operation
- **Neural Reranker Feature Visibility** - Added to README and Help menu with quality metrics
- **Search Configuration Menu Explanations** - All options now have clear descriptions
- **Debug Mode Startup Timing** - Precise timing measurements for optimization
- **MCP Workflow Clarification** - Fixed Index/Search instructions for correct `/mcp-search` usage

### Bug Fixes

#### RAM Cleanup in Release Resources

**Problem**: During "Release Resources" (X option in menu), VRAM was properly released but RAM increased by 2-5GB.

**Root Cause**: `CodeEmbedder.cleanup()` used `.to("cpu")` to move model from GPU to CPU before deletion - a legacy PyTorch 1.x workaround that copied the entire model to RAM.

**Solution**:

1. **Removed `.to("cpu")` call** in `embeddings/embedder.py:794-807`:
   - PyTorch 2.x handles CUDA cleanup automatically
   - Direct deletion with `del self._model` is sufficient

2. **Added `gc.collect()` before `empty_cache()`**:
   - Forces garbage collection before clearing CUDA cache
   - Ensures thorough memory cleanup
   - Reordered cleanup: `del` → `gc.collect()` → `empty_cache()`

3. **Applied same pattern to `NeuralReranker.cleanup()`** (`search/neural_reranker.py:131-141`):
   - Consistency across all cleanup methods
   - Added `gc.collect()` for thorough cleanup

**Impact**:

- ✅ RAM no longer increases during cleanup
- ✅ Both VRAM and RAM properly released
- ✅ Unified cleanup pattern across codebase
- ✅ Tests: 21/21 embedder tests, 12/12 reranker tests passing

#### Removed Broken Performance Tools Menu

**Problem**: Menu option 4 "Performance Tools" contained two non-functional features:

1. **Memory Usage Report** - Had undefined `gpu_name` variable, causing crashes
2. **Auto-Tune Search** - Called non-existent `tools\auto_tune_search.py` (archived)

**Root Cause**: Features were experimental and never completed:

- Memory report assumed GPU detection logic that wasn't implemented
- Auto-tune script was archived but menu entry remained

**Solution**:

1. **Removed entire Performance Tools menu section** from `start_mcp_server.cmd`:
   - Removed menu option 4 from main menu
   - Removed Performance Tools submenu (73 lines of code)
   - Cleaned up broken auto-tune and memory report functions

**Impact**:

- ✅ Eliminates crashes from undefined `gpu_name` variable
- ✅ Removes confusing menu options for non-existent features
- ✅ Cleaner UI with only functional options
- ✅ 73 lines of broken code removed

### New Features

#### Neural Reranker Documentation Enhancement

**Added Neural Reranking to key documentation locations**:

1. **README.md Highlights** (line 32):
   - Added feature: "Cross-encoder model (BAAI/bge-reranker-v2-m3) improves ranking quality by 5-15%"
   - Links to `ADVANCED_FEATURES_GUIDE.md#neural-reranking-configuration`

2. **Help & Documentation Menu** (`start_mcp_server.cmd:1624`):
   - Added to Key Features: "Neural Reranking: Cross-encoder model (5-15% quality boost)"

**Impact**:

- Users now aware of Neural Reranking feature without digging through docs
- Quality improvement metric (5-15%) clearly communicated
- Easy access to detailed configuration documentation

#### Search Configuration Menu Explanations

**Added helpful descriptions to all menu options** (`start_mcp_server.cmd:343-351`):

| Option | Description |
|--------|-------------|
| View Current Configuration | Show all active settings |
| Set Search Mode | Hybrid/Semantic/BM25 (Hybrid recommended) |
| Configure Search Weights | Balance text vs semantic matching |
| Select Embedding Model | Choose model by VRAM (BGE-M3/Qwen3) |
| Configure Parallel Search | Run BM25+Dense in parallel (faster) |
| Configure Neural Reranker | Cross-encoder reranking (+5-15% quality) |
| Configure Entity Tracking | Track symbols across searches |
| Reset to Defaults | Restore optimal default settings |

**Before**:

```
1. View Current Configuration
2. Set Search Mode (Hybrid/Semantic/BM25)
```

**After**:

```
1. View Current Configuration   - Show all active settings
2. Set Search Mode              - Hybrid/Semantic/BM25 (Hybrid recommended)
```

**Impact**:

- Users understand what each option does without trial-and-error
- Clear recommendations (Hybrid mode, quality boost percentages)
- Performance benefits highlighted (faster, +5-15% quality)

#### Debug Mode Startup Timing

**Added precise timing measurements for optimization** (`mcp_server/server.py`):

**Implementation**:

- Captures `time.perf_counter()` at server startup
- Logs completion at "APPLICATION READY" / "SERVER READY" states
- Displays total startup duration (e.g., "Startup completed in 3.35 seconds")
- Works for both SSE and stdio transports
- Only active when `MCP_DEBUG=1` environment variable is set

**Example Output**:

```
00:57:09 - __main__ - INFO - [DEBUG] Startup timer started at 00:57:09
...
00:57:13 - __main__ - INFO - [DEBUG] Startup completed in 3.35 seconds
```

**Impact**:

- Developers can track startup performance improvements
- Easy to measure impact of optimization changes
- Helps identify slow initialization paths

### Changed

#### Index/Search Workflow Documentation

**Fixed incorrect MCP tool usage instructions**:

**Problem**: Documentation incorrectly showed MCP tools as direct slash commands:

```
4. Index: Menu option 5 (UI) OR /index_directory "path" (MCP)
5. Search: Ask Claude naturally OR /search_code "query" (MCP)
```

**Issue**: MCP tools are NOT exposed as slash commands in Claude Code. Users must:

1. Run `/mcp-search` to load SKILL.md into context
2. Ask Claude naturally (Claude uses MCP tools internally)

**Fixed Locations**:

1. **README.md Section 2 (Index)** (lines 56-81):
   - Removed "Option B: Via Claude Code MCP Commands" with `/index_directory`
   - Changed to: "Option B: Via Claude Code (after loading `/mcp-search` skill)"
   - Shows natural language: "Index my project at C:\Projects\MyApp"
   - Explains: "Claude will use the MCP tools internally"

2. **README.md Section 6 (Search)** (lines 122-134):
   - Removed "Option B: Direct MCP Commands" showing `/search_code`, `/find_connections`
   - Added note: "MCP tools are not exposed as direct slash commands"
   - Clarified: "Called internally by Claude when you ask natural language questions"

3. **Help & Documentation Quick Start** (`start_mcp_server.cmd:1634-1635`):
   - Changed from: `/index_directory "path"` and `/search_code "query"`
   - Changed to: "Run /mcp-search in Claude Code to load the skill"
   - Then: "Ask Claude naturally: 'index my project' or 'search for X'"

**Correct Workflow**:

```
1. Start server (menu option 1)
2. Connect in Claude Code (/mcp → Reconnect)
3. Run /mcp-search to load the skill
4. Ask Claude naturally:
   - "Index my project at C:\Projects\MyApp"
   - "Search for authentication functions"
```

**Impact**:

- Users no longer confused about non-existent slash commands
- Clear workflow: load skill → ask naturally
- Proper explanation of internal MCP tool usage

### Documentation

- Complete documentation update across README and launcher UI
- Improved clarity on Neural Reranking feature benefits
- Better user guidance for search configuration options
- Correct workflow for Claude Code integration

---

## v0.7.3 - UI/Server Sync & Config Fixes (2026-01-02)

### Status: PRODUCTION-READY ✅

**Patch release with HTTP config sync, entity tracking fix, and GitHub Actions CI fixes**

### Highlights

- **HTTP Config Sync** - Real-time UI ↔ MCP server state synchronization via HTTP endpoints
- **Entity Tracking Config Fix** - Config setting now properly applied during indexing
- **Multi-Model State Management Fix** - Resolved 0 chunks issue after multi-model indexing
- **Manual Test Discovery Fix** - Prevented pytest from discovering manual test helpers
- **Test Suite**: 1,249 tests passing (was 86 passed, 1 failed, 4 errors)

### New Features

#### HTTP Config Sync for UI Operations

**Problem**: UI operations (project switch, config changes) ran in separate Python processes, creating isolated singleton states. Changes made via UI menu didn't sync with the running MCP server, and no server logs appeared for UI operations.

**Architecture Issue**:

```
UI Batch Script Process          MCP Server Process
┌────────────────────┐           ┌────────────────────┐
│ switch_project_    │           │ Running MCP Server │
│ helper.py          │           │ (stdio/SSE)        │
│                    │           │                    │
│ Own _app_state ─────┼─────X────┼───> _app_state     │
│ singleton          │  NO IPC   │   singleton        │
└────────────────────┘           └────────────────────┘
```

**Solution**: Added HTTP endpoints to SSE server for live state synchronization:

1. **New HTTP Endpoints** (`mcp_server/server.py`):
   - `POST /reload_config` - Reloads `search_config.json` in running server
   - `POST /switch_project` - Switches active project in running server
   - Both endpoints log operations with `[HTTP CONFIG]` and `[HTTP SWITCH]` prefixes

2. **HTTP Notification Helper** (`tools/notify_server.py`):
   - `notify_config_reload()` - Tell server to reload config
   - `notify_project_switch(path)` - Tell server to switch project
   - Graceful fallback when server not running (SSE mode)

3. **UI Integration** (`start_mcp_server.cmd`):
   - Calls `notify_server.py reload_config` after all config changes:
     - Search mode (hybrid/semantic/BM25)
     - Weights (BM25/Dense)
     - Entity tracking (enable/disable)
     - Neural reranker (enable/disable/top-k)

4. **Project Switch Helper Update** (`tools/switch_project_helper.py`):
   - Tries HTTP endpoint first (for running SSE server)
   - Falls back to direct call if server not running
   - Clear console messages indicating which method used

**Impact**:

- ✅ All UI config changes sync to running server instantly
- ✅ All UI operations visible in server logs with clear prefixes
- ✅ No server restart needed for config/project changes
- ✅ Graceful degradation when server not running

**Example Server Logs**:

```
14:48:41 - [HTTP SWITCH] Project switch requested: D:\...\STREAM_DIFFUSION
14:48:42 - Current project set to: STREAM_DIFFUSION_0.3.0_TOX
14:48:42 - [HTTP SWITCH] Switch complete: D:\...\STREAM_DIFFUSION
INFO:     ::1:58304 - "POST /switch_project HTTP/1.1" 200 OK
```

**Files Modified**:

- `mcp_server/server.py` - HTTP endpoints (lines 386-459, 504-529)
- `tools/notify_server.py` - NEW file (~130 lines)
- `tools/switch_project_helper.py` - HTTP-first logic (lines 60-88)
- `start_mcp_server.cmd` - Notifier calls (lines 1020-1021, 1060-1061, 1254-1255, 1265-1266, 1278-1279, 1400-1401, 1412-1413)

**Limitations**:

- Only works in SSE mode (not stdio mode)
- Stdio mode users should use MCP tools directly (already working)

#### Entity Tracking Configuration Fix

**Problem**: UI showed "Entity Tracking: Enabled" but indexing logs showed "Initialized 9 relationship extractors (entity tracking disabled)" instead of expected 12 extractors.

**Root Cause**: `MultiLanguageChunker` was instantiated WITHOUT passing the `enable_entity_tracking` parameter in 3 locations in `mcp_server/tools/index_handlers.py`. Since the parameter defaults to `False` in the constructor, the config setting was ignored.

**Code Flow Analysis**:

1. **Config correctly stored**: `"enable_entity_tracking": true` in `search_config.json` (line 22)

2. **UI correctly read**: Config via `cfg.performance.enable_entity_tracking` (returns `True`)

3. **Bug**: Chunkers created WITHOUT entity tracking parameter:
   - Line 91 (`_create_indexer_for_model`): Missing parameter
   - Lines 293-304 (`_index_with_all_models`): Missing parameter
   - Lines 754-762 (`handle_index_directory` single-model path): Missing parameter

4. **Why `IncrementalIndexer` didn't fix it**:

   ```python
   # search/incremental_indexer.py:84-87
   self.chunker = chunker or MultiLanguageChunker(
       ...
       enable_entity_tracking=config.performance.enable_entity_tracking,
   )
   ```

   Logic is `chunker or ...` - since a chunker WAS passed (with wrong settings), the config-aware fallback never executed.

**Solution**: Pass `enable_entity_tracking=config.performance.enable_entity_tracking` to all 3 `MultiLanguageChunker` instantiations:

```python
# Example fix (line 754-762):
config = get_config()
chunker = MultiLanguageChunker(
    str(directory_path),
    include_dirs,
    exclude_dirs,
    enable_entity_tracking=config.performance.enable_entity_tracking,
)
```

**Impact**: Entity tracking config now properly applied, indexing logs correctly show:

```
Initialized 12 relationship extractors (foundation + core + data models + entity tracking)
```

**Files Modified**: `mcp_server/tools/index_handlers.py:91-94, 296-304, 754-762`

**Verification**: User confirmed fix working with re-index showing 12 extractors

#### Server Startup Optimizations

**3-phase optimization for faster startup and first search**

**Phase 1: Defer VRAM Tier Detection** (50-200ms savings)

- **Problem**: `VRAMTierManager.detect_tier()` called during server startup via `initialize_server_state()`
- **Solution**: Moved VRAM detection to first model load
- **Implementation**:
  - Removed from `resource_manager.py:180-196` (startup path)
  - Added lazy detection in `model_pool_manager.py:get_embedder()` on first call
  - Tier result cached for subsequent calls
- **Files**: `mcp_server/resource_manager.py`, `mcp_server/model_pool_manager.py`
- **Tests**: `tests/unit/test_vram_lazy_detection.py` (3 tests)

**Phase 2: Enable SSE Pre-warming by Default** (5-10s first-search savings)

- **Problem**: First search in SSE mode took 5-10s for model loading
- **Solution**: Pre-load embedding model during SSE server startup
- **Implementation**:
  - Changed `MCP_PRELOAD_MODEL` default from `"false"` to `"true"` (line 474)
  - Pre-load logic executes during `app_lifespan()` startup
  - Environment variable override: `set MCP_PRELOAD_MODEL=false` to disable
  - stdio mode unchanged (remains lazy)
- **Files**: `mcp_server/server.py:472-487`
- **Tests**: `tests/unit/test_sse_prewarm_default.py` (8 tests)

**Phase 3: Parallel Index Loading** (50-100ms savings)

- **Problem**: BM25 and dense indices loaded sequentially
- **Solution**: Concurrent loading using `ThreadPoolExecutor`
- **Implementation**:
  - New `_load_indices_parallel()` method in `HybridSearcher`
  - Uses `ThreadPoolExecutor(max_workers=2)` for concurrent I/O
  - Helper methods: `_load_bm25_index()`, `_load_dense_index()`
- **Files**: `search/hybrid_searcher.py:231-248`
- **Tests**: `tests/unit/test_parallel_index_loading.py` (5 tests)

**Total Impact**:

- Startup: 100-300ms faster (VRAM defer + parallel loading)
- First search (SSE): 5-10s faster (model pre-loaded)
- Test coverage: 16 unit tests (100% pass rate)

**Commits**:

- `f3991cb` - Phase 1: Defer VRAM detection
- `476895f` - Phase 2: SSE pre-warming default
- `b40eee1` - Phase 3: Parallel index loading

### Bug Fixes

#### Multi-Model State Management

**Problem**: After multi-model indexing with `_index_with_all_models()`, `handle_get_index_status()` returned 0 chunks even though indexing succeeded.

**Root Cause**: Model key mismatch between indexing and status query:

1. During indexing: `_index_with_all_models()` indexed all 3 models (qwen3, bge_m3, coderankembed)
2. After indexing: `state.reset_search_components()` was called but `state.current_model_key` remained `None`
3. During status query: `handle_get_index_status()` called `get_index_manager(model_key=None)`
4. Result: Used config default model's storage path, which may not match where indexing wrote `stats.json`
5. Outcome: `get_stats()` returned `total_chunks: 0` because `stats.json` not found at that path

**Solution**: Set `state.current_model_key` after multi-model indexing completes:

```python
# Set current_model_key for subsequent operations
# (same pattern used in model_pool_manager.py:151-155)
for key, name in MODEL_POOL_CONFIG.items():
    if name == original_model:
        state.current_model_key = key
        break
```

**Impact**: `test_delete_project_full_workflow` now passes, status queries work correctly after multi-model indexing

**File Modified**: `mcp_server/tools/index_handlers.py:374-379`

#### Manual Test Discovery

**Problem**: Pytest discovered 4 functions in `tests/manual/test_sse_cancellation.py` as tests, causing fixture errors:

- `test_cancelled_error_handler(arguments)` - ❌ fixture 'arguments' not found
- `test_broken_resource_handler(arguments)` - ❌ fixture 'arguments' not found
- `test_closed_resource_handler(arguments)` - ❌ fixture 'arguments' not found
- `test_normal_exception_handler(arguments)` - ❌ fixture 'arguments' not found

**Root Cause**: Functions named `test_*` are discovered by pytest due to `pytest.ini` setting `python_functions = test_*`. These are not pytest tests - they are helper functions decorated with `@error_handler("Test operation")` for manual SSE error simulation. The actual entry point is `run_tests()` for manual execution.

**Solution**: Renamed functions to not start with `test_` prefix:

- `test_cancelled_error_handler` → `_simulate_cancelled_error`
- `test_broken_resource_handler` → `_simulate_broken_resource`
- `test_closed_resource_handler` → `_simulate_closed_resource`
- `test_normal_exception_handler` → `_simulate_normal_exception`

Updated all calls in `run_tests()` function to use new names.

**Impact**: Pytest now collects 0 items from this file (no longer discovered as tests), GitHub Actions CI passes

**File Modified**: `tests/manual/test_sse_cancellation.py:31-58, 71-106`

### Technical Details

**Commit History**:

1. `fix: resolve multi-model state management and manual test discovery issues` (2026-01-02)

**Test Results**:

- Before: 86 passed, 1 failed, 4 errors
- After: 1,249 passed ✅

---

## v0.7.2 - Reliability Improvements (2026-01-01)

### Status: PRODUCTION-READY ✅

**Patch release with SSE transport protection and comprehensive indexing protection system**

### Highlights

- **SSE Transport Protection** - Graceful client disconnection handling
- **6-Layer Indexing Protection** - Prevents file locks, VRAM exhaustion, timeouts
- **Test Suite Optimization** - 95.4% faster slow integration tests (20× speedup)
- **Comprehensive Unit Tests** - 15 new tests with 100% pass rate

### Bug Fixes

#### SSE Transport Error Protection

**Problem**: MCP server crashed when clients disconnected during SSE streaming (anyio.BrokenResourceError, ClosedResourceError).

**Solution**: Comprehensive error handling for SSE transport layer:

- Added `anyio.BrokenResourceError` and `ClosedResourceError` exception handlers
- Extended Windows socket error handler (`WinError 64`) for SSE streams
- Added ASGI error filter to suppress "Unexpected ASGI message" warnings in logs
- Tool cancellation handling in decorator layer (`@handle_tool_errors`)

**Impact**: Zero SSE crashes, clean server logs, graceful client disconnection handling

**Addresses**: MCP SDK bug #1811 (P1, Open - awaiting upstream fix)

**Files Modified**:

- `mcp_server/server.py` - SSE error handlers, ASGI filter
- `mcp_server/tools/decorators.py` - Tool cancellation handling

#### 6-Layer Indexing Protection System

**Problem**: Indexing hung indefinitely on locked files (TouchDesigner, IDEs), consumed excessive VRAM, crashed on permission errors.

**Solution**: Comprehensive protection at 6 critical points:

| Layer | Feature | Implementation | Protection |
|-------|---------|----------------|------------|
| **1** | Resource Cleanup | `cleanup_previous_resources()` | Prevents duplicate model loads, clears stale connections |
| **2** | File Read Timeout | `_read_file_with_timeout()` | 5s ThreadPoolExecutor timeout for locked files |
| **3** | PermissionError Handling | `try/except PermissionError` | Skip locked files with `[LOCKED]` warnings |
| **4** | VRAM Monitoring | `_check_vram_status()` | 85% warn, 95% abort threshold |
| **5** | Progress Timeout | `future.result(timeout=10)` | 10s/file, 300s total limits |
| **6** | Accessibility Check | `_check_file_accessibility()` | Pre-index sample validation (10 random files) |

**Impact**: Zero hangs, zero crashes, graceful handling of locked files, OOM prevention

**Configuration Constants**:

```python
FILE_READ_TIMEOUT = 5           # seconds (Layer 2)
CHUNKING_TIMEOUT_PER_FILE = 10  # seconds (Layer 5)
TOTAL_CHUNKING_TIMEOUT = 300    # seconds (Layer 5)
VRAM_WARNING_THRESHOLD = 0.85   # 85% (Layer 4)
VRAM_ABORT_THRESHOLD = 0.95     # 95% (Layer 4)
```

**Files Modified**:

- `chunking/tree_sitter.py` - Layer 2, Layer 3
- `embeddings/embedder.py` - Layer 4
- `search/parallel_chunker.py` - Layer 5
- `mcp_server/tools/index_handlers.py` - Layer 1, Layer 6

### New Tests

#### Unit Tests for Protection System (15 tests, 100% pass rate)

**Coverage**: All 4 protection functions tested exhaustively

- **TestReadFileWithTimeout** (3 tests) - `tests/unit/chunking/test_tree_sitter.py`
  - Successful file read within timeout
  - Timeout raises TimeoutError with descriptive message
  - FILE_READ_TIMEOUT constant = 5 seconds
- **TestCheckVramStatus** (4 tests) - `tests/unit/embeddings/test_embedder.py`
  - Warning threshold (85%) detection
  - Abort threshold (95%) detection
  - No GPU available handling
  - Multiple GPU device handling
- **TestParallelChunkerTimeouts** (3 tests) - `tests/unit/search/test_parallel_chunker.py`
  - Timeout constants defined (10s/file, 300s total)
  - Stalled files logged on timeout
  - Total timeout stops processing early
- **TestCheckFileAccessibility** (5 tests) - `tests/unit/mcp_server/test_index_handlers.py`
  - All files accessible (baseline)
  - Empty file list handling
  - PermissionError detection
  - IOError detection
  - Sample size limits file checks (10 max)

**Files Modified**:

- `tests/unit/chunking/test_tree_sitter.py` - 3 tests
- `tests/unit/embeddings/test_embedder.py` - 4 tests
- `tests/unit/search/test_parallel_chunker.py` - 3 tests
- `tests/unit/mcp_server/test_index_handlers.py` - 5 tests

### Test Suite Optimization

**95.4% runtime reduction for slow integration tests**

Converted function-scoped fixtures to class-scoped using `tmp_path_factory`:

| Test File | Before | After | Improvement |
|-----------|--------|-------|-------------|
| `test_full_flow.py` | ~88s | 1.91s | 98.2% faster |
| `test_relationship_extraction_integration.py` | ~180s | 3.34s | 98.1% faster |
| `test_multi_hop_flow.py` | ~70s | 10.21s | 85.4% faster |
| **Total** | **~338s** | **15.46s** | **95.4% faster** |

**Impact**: Developer feedback loop improved from 5-6 minutes to 15 seconds

**Files Modified**:

- `tests/slow_integration/test_full_flow.py` - Class-scoped indexed fixture
- `tests/slow_integration/test_relationship_extraction_integration.py` - Session/class fixtures
- `tests/slow_integration/test_multi_hop_flow.py` - Class-scoped hybrid searcher fixture

### Bug Fixes (Additional)

#### ImpactReport API Consistency

**Problem**: `find_connections` omitted empty relationship fields (`child_classes`, `decorated_by`), breaking client expectations.

**Solution**: Modified `ImpactReport.to_dict()` to always include all relationship fields.

**File**: `mcp_server/tools/code_relationship_analyzer.py:223`

### Technical Details

**Commit History**:

1. `01c2649` - SSE Transport Error Protection (Session 1, 2026-01-01)
2. `7e5b1e2` - 6-Layer Indexing Protection System (Session 1, 2026-01-01)
3. `61b71ba` - Unit Tests for Protection System (Session 2, 2026-01-01)

**Session Documentation**: See `MEMORY.md` entries for 2026-01-01 sessions

---

## v0.7.1 - Patch Release (2025-12-27)

### Status: PRODUCTION-READY ✅

**Patch release with Release Resources menu option and bug fixes**

### New Features

#### Release Resources Menu Option

- New 'X' option in `start_mcp_server.cmd` main menu
- Positioned between 'F. Configure Output Format' and '0. Exit'
- Frees GPU memory and cached resources on demand via HTTP
- Calls running SSE server's `/cleanup` endpoint
- Checks if server is running before attempting cleanup

#### HTTP Cleanup Endpoint

- New POST endpoint at `http://localhost:8765/cleanup`
- Enables external cleanup requests to running MCP server
- Returns JSON response: `{"success": true/false, "message": "..."}`
- Logs all cleanup operations for debugging

### Bug Fixes

- **Index Validation** - Fixed 3 issues with stale index detection and model routing
  - Corrected validation logic for detecting stale indices
  - Fixed model routing edge cases in multi-model mode
  - Improved error handling for corrupted index files
- **Model Routing** - Corrected edge cases in query routing logic

### Files Modified

- `mcp_server/server.py` - Added `/cleanup` endpoint handler and route
- `start_mcp_server.cmd` - Updated `:release_resources` to call HTTP endpoint via PowerShell
- `pyproject.toml` - Version bump to 0.7.1
- Documentation updates (CHANGELOG.md, VERSION_HISTORY.md, CLAUDE.md)

---

## v0.7.0 - Major Release (2025-12-22)

### Status: PRODUCTION-READY ✅

**Major release with output formatting optimization, memory-mapped vector storage, and comprehensive refactoring**

### Highlights

- **MCP Output Formatting** - 30-55% token reduction with 3-tier system
- **Memory-Mapped Vector Storage** - <1μs access, auto-enabled at 10K vectors
- **Symbol Hash Cache** - O(1) chunk lookups for direct access
- **Entity Tracking** - Constants, enums, and default parameter tracking
- **Comprehensive Refactoring** - ~700 lines of dead code removed, major modules extracted

### Breaking Changes

- Output format options renamed: `json`→`verbose`, `toon`→`ultra`

### New Features

#### MCP Output Formatting (30-55% Token Reduction)

- **3 format tiers**: verbose (baseline), compact (30-40%), ultra (45-55%)
- **Ultra format**: Tabular arrays with header-declared fields
  - Header: `"results[5]{chunk_id,kind,score}"`
  - Data: `[[val1, val2, val3], ...]`
- **Agent understanding**: 100% accuracy validated on fresh Claude instance
- **Configuration**: Menu option 'F' or per-query `output_format` parameter
- **Files**: `mcp_server/output_formatter.py` (171 lines), all 17 tool handlers

#### Memory-Mapped Vector Storage

- **Performance**: <1μs vector access (vs ~100μs standard)
- **Auto-enable**: Threshold at 10,000 vectors (no configuration needed)
- **Storage**: ~3.5 MB per model (10.5 MB total for 3 models)
- **Files**: `search/faiss_index.py`, removed from config (fully automatic)

#### Symbol Hash Cache (Phase 2)

- **Complexity**: O(1) direct chunk lookups
- **Utilization**: 97.7% bucket usage (251/256 buckets)
- **Performance**: <1ms load/save
- **File**: `search/symbol_hash_cache.py`

### Refactoring Summary

| Component | Extraction | Lines |
|-----------|------------|-------|
| CodeIndexManager | → GraphIntegration + BatchOperations | ~200 |
| CodeEmbedder | → ModelLoader + ModelCacheManager + QueryCache | ~300 |
| HybridSearcher | Removed deprecated methods (Tier 1-3) | ~150 |
| Intent Detection | Complete removal (48% accuracy) | ~200 |
| **Total** | | **~850 lines** |

### Test Coverage

- **Before**: 720 unit tests
- **After**: 1,054+ unit tests (+46%)
- **Pass rate**: 100%
- **Modules**: 7 (chunking, embeddings, graph, merkle, search, mcp_server, integration)

### Files Modified

**Core Implementation (10+ files)**:

- `mcp_server/output_formatter.py` (NEW)
- `search/faiss_index.py` - Mmap automation
- `search/symbol_hash_cache.py` - Hash-based lookups
- `search/indexer.py` - GraphIntegration extraction
- `embeddings/embedder.py` - ModelLoader extraction
- `search/hybrid_searcher.py` - Deprecated method removal
- All MCP tool handlers - Output format support

**Tests (5+ files)**:

- `tests/unit/mcp_server/test_output_formatter.py` (NEW, 34 tests)
- Test reorganization into module directories
- `tests/run_all_tests.bat` (NEW)

---

## v0.6.5 - Entity Tracking System (2025-12-16) [Included in 0.7.0]

### Status: PRODUCTION-READY ✅

**Added 3 new relationship extractors for tracking constants, enum members, and default parameters**

### Highlights

- **ConstantExtractor** - Track module-level constant definitions (UPPER_CASE) and their usages
- **EnumMemberExtractor** - Track enum member definitions (Enum, IntEnum, StrEnum, Flag)
- **DefaultParameterExtractor** - Track default parameter value references
- **find_connections Integration** - Display entity tracking relationships in impact analysis

### Key Changes

#### New Relationship Types (9 total)

**Priority 4 - Definitions**:

- `DEFINES_CONSTANT` - Module-level constant definitions (e.g., `TIMEOUT = 30`)
- `DEFINES_ENUM_MEMBER` - Enum member definitions (e.g., `Status.ACTIVE = 1`)
- `DEFINES_CLASS_ATTR` - Class attribute definitions (planned)
- `DEFINES_FIELD` - Dataclass field definitions (planned)

**Priority 5 - References**:

- `USES_CONSTANT` - Constant usage in functions/methods
- `USES_DEFAULT` - Default parameter value references
- `USES_GLOBAL` - Global statement usage (planned)
- `ASSERTS_TYPE` - isinstance() type assertions (planned)
- `USES_CONTEXT_MANAGER` - Context manager usage (planned)

#### ConstantExtractor Features

- **Extraction**: Module-level UPPER_CASE assignments (≥2 chars, non-private)
- **Filtering**: Excludes trivial values (single digits -9 to 9, empty strings)
- **Smart detection**: Distinguishes definitions from usages based on chunk type
- **Examples**:
  - Definition: `TIMEOUT = 30` → `DEFINES_CONSTANT`
  - Usage: `time.sleep(TIMEOUT)` → `USES_CONSTANT`

#### EnumMemberExtractor Features

- **Supported variants**: Enum, IntEnum, StrEnum, Flag
- **Qualified names**: `Status.ACTIVE`, `Priority.HIGH`
- **Annotation support**: Handles typed enum members (`ACTIVE: int = 1`)
- **Filtering**: Excludes private members (`_INTERNAL`)

#### DefaultParameterExtractor Features

- **Tracked defaults**:
  - Name references: `def connect(timeout=DEFAULT_TIMEOUT)`
  - Call expressions: `def init(config=Config())`
  - Attribute access: `def connect(timeout=config.TIMEOUT)`
- **Skipped defaults**: None, booleans, small numbers, empty strings/collections
- **Metadata**: Includes parameter name and default type (name/call/attribute)

#### find_connections Tool Integration

Added 4 new fields to `ImpactReport`:

- `defines_constants` - Constants defined by this code
- `uses_constants` - Constants used by this code
- `defines_enum_members` - Enum members defined by this code
- `uses_defaults` - Default parameter values used by this code

**Example output**:

```json
{
  "defines_enum_members": [
    {"target_name": "RelationshipType.CALLS", "line": 10, ...},
    {"target_name": "RelationshipType.DEFINES_CONSTANT", "line": 65, ...}
  ],
  "uses_constants": [
    {"target_name": "FAISS_INDEX_FILENAME", "line": 42, ...}
  ],
  "uses_defaults": [
    {"target_name": "DEFAULT_TIMEOUT", "parameter": "timeout", ...}
  ]
}
```

### Files Modified

**New Extractors** (3 files):

- `graph/relationship_extractors/constant_extractor.py` (250 lines)
- `graph/relationship_extractors/enum_extractor.py` (180 lines)
- `graph/relationship_extractors/default_param_extractor.py` (299 lines)

**Core Infrastructure**:

- `graph/relationship_types.py` - Added 9 new RelationshipType enum values
- `graph/relationship_extractors/__init__.py` - Exported new extractors
- `mcp_server/tools/code_relationship_analyzer.py` - Updated ImpactReport for entity tracking

**Tests** (30+ tests):

- `tests/unit/test_entity_tracking_extractors.py` (522 lines)
  - TestConstantExtractor: 8 tests
  - TestEnumMemberExtractor: 7 tests
  - TestDefaultParameterExtractor: 14 tests
  - TestEntityTrackingIntegration: 1 test

### Test Coverage

- **Before**: 720 unit tests
- **After**: 750+ unit tests (+30 tests, +4.2%)
- **Pass rate**: 100%

### Use Cases

**Find constant usages**:

```
/find_connections --symbol_name "FAISS_INDEX_FILENAME"
# Shows all functions using this constant
```

**Find enum member usages**:

```
/find_connections --chunk_id "types.py:10-50:class:Status"
# Shows all enum members and their definitions
```

**Track default parameter dependencies**:

```
/find_connections --symbol_name "connect"
# Shows constants used as default parameters
```

### Refactoring Support

Entity tracking enables:

- **Constant refactoring**: Find all usages before renaming
- **Enum migration**: Track enum member references across codebase
- **Default value changes**: Identify functions affected by constant changes

---

## Development Sessions

### Session 2025-12-09: Phase 13-C + Test Coverage Improvements

**Objective**: Complete Phase 13 refactoring arc and address critical test coverage gaps

**Completed Work**:

1. **Phase 13-C: Remove Property Aliases** (Commit: `2f88010`)
   - Removed 35 backward-compatibility property aliases from SearchConfig
   - Deleted 291 lines of alias code (lines 181-471)
   - Migrated 20 test accesses to nested config pattern
   - Updated test constructors to use nested config objects
   - Files: `search/config.py`, `tests/unit/test_model_selection.py`, `tests/unit/test_config_sync.py`, `tests/unit/test_search_config.py`
   - Result: Phase 13 arc complete (13-A → 13-B → 13-C)

2. **ServiceLocator Tests** (Commit: `3d00f1e`)
   - Created comprehensive test suite for ServiceLocator dependency injection (29 tests)
   - Coverage: Singleton pattern, registration, factory pattern, cache invalidation
   - Coverage: Typed convenience methods, wrapper functions, integration scenarios
   - File: `tests/unit/test_services.py` (422 lines)
   - Result: 150+ LOC implementation now has full test coverage

3. **Fix Flaky Test** (Commit: `397e5ad`)
   - Fixed `test_cross_file_search_patterns` with deterministic embeddings
   - Replaced arbitrary query vector with hash-based deterministic queries
   - Validated with 5 consecutive runs (100% pass rate, 0.91-1.02s)
   - Removed `@pytest.mark.skip` decorator
   - File: `tests/slow_integration/test_full_flow.py`
   - Result: Previously flaky test now reliable

4. **Decorator Tests** (Commit: `39f7967`)
   - Created comprehensive test suite for `@error_handler` decorator (15 tests)
   - Coverage: Success/failure handling, context enrichment, logging, metadata preservation
   - Fixed B023 loop variable binding issue with default arguments
   - File: `tests/unit/test_decorators.py` (267 lines)
   - Result: Critical decorator used by all MCP handlers now fully tested

**Test Count Impact**:

- Before: 625 unit tests
- After: 669 unit tests (+44 tests, +7.0%)
- All tests passing (100% pass rate)

**Refactoring Progress**:

- Phase 13 (Config Splitting) - **COMPLETE** ✅
  - Phase 13-A: Split into sub-configs ✅
  - Phase 13-B: Migrate consumers ✅
  - Phase 13-C: Remove aliases ✅
- Next: Phase 14 (Further modularization opportunities)

**Files Modified**: 5 files (1 refactored, 3 test fixes, 3 new test files)

---

## v0.6.1 - UX Improvements & Bug Fixes (2025-12-03)

### Status: PRODUCTION-READY ✅

**Enhanced indexing UX with progress bars and fixed critical bugs**

### Highlights

- **Progress Bars** - Real-time visual feedback during chunking and embedding
- **Directory Filtering Fix** - `include_dirs` now works correctly
- **Targeted Snapshot Deletion** - Only deletes matching model snapshots
- **Improved Project Lists** - Shows model/dimension for disambiguation

### Key Changes

- **Progress Bar for Chunking** - Shows real-time progress during file chunking
  - `Chunking files... 100% (21/21 files)`
  - Works with both parallel and sequential modes
  - Force terminal mode for batch script compatibility
- **Progress Bar for Embedding** - Shows progress during longest phase
  - `Embedding... 100% (3/3 batches)`
  - Model warmup prevents log interference
- **include_dirs Filter Fix** - Root directory no longer blocked by filters
  - Fixed 0 files found when using `include_dirs`
  - Root directory skipped from filter matching
- **Targeted Snapshot Deletion** - New `delete_snapshot_by_slug()` method
  - Deletes only matching model/dimension snapshot
  - Preserves other model snapshots (e.g., keeps `coderank_768d` when deleting `bge-m3_1024d`)
- **Model/Dimension Display** - Clear project list shows model info
  - `claude-context-local [bge-m3 1024d]`
  - Disambiguates duplicate project names

### Bug Fixes

- Fixed unescaped parenthesis causing spurious error messages in clear index
- Fixed `delete_all_snapshots()` deleting all model variants instead of specific one
- Fixed `include_dirs` filter blocking root directory traversal
- Fixed progress bar not rendering in batch scripts
- Fixed model loading logs interfering with progress bar display

### Commits

- `083ab61` - Fix clear index logic bugs (snapshot deletion + display)
- `2e69ace` - Fix include_dirs filter blocking root directory
- `0e9c8e8` - Display model/dimension in clear project list
- `43d94d0` - Add progress bar for file chunking
- `1d9d098` - Force terminal mode for chunking progress bar
- `33ace99` - Add progress bar for embedding generation
- `81e1d42` - Warm up model before progress bar

---

## v0.6.0 - Production Release (2025-11-28)

### Status: PRODUCTION-READY ✅

**Major release consolidating v0.5.16-v0.5.17 improvements**

### Highlights

- **Self-Healing BM25 Sync** - Automatic index synchronization
- **Persistent Project Selection** - Survives server restarts
- **Graph Resolver Extraction** - Cleaner architecture (Phase 7.1)
- **Tree-Sitter Modularization** - 76% code reduction (Phase 4.1)
- **Multi-Hop Search Refactoring** - Orchestrator pattern (Phase 4.2)
- **Batch Script Compliance** - 56 violations fixed across 15 files
- **Git Workflow Fixes** - Critical C: drive scanning bug resolved

### Key Changes (cumulative from v0.5.16-v0.5.17)

- Self-healing BM25/Dense index synchronization during incremental indexing
- Project persistence across server restarts
- Graph resolvers extracted to `graph/resolvers/` module
- Tree-sitter chunker split into `chunking/languages/` package
- Multi-hop search helper methods extracted
- All batch scripts BATCH_STYLE_GUIDE.md compliant
- Git workflow scripts use explicit Windows tool paths

### Test Coverage

- 545+ unit tests (100% pass rate)
- All 15 MCP tools operational
- No re-indexing required

---

## v0.5.17 - Self-Healing Index Sync (2025-11-26)

### Status: PRODUCTION-READY ✅

**Automatic BM25 synchronization during incremental indexing**

### Changes

- **Self-Healing BM25 Sync**: Auto-detect and fix BM25/Dense desync during incremental indexing
  - Triggers when desync exceeds 10% threshold
  - Rebuilds BM25 from dense index metadata
  - New method: `HybridSearcher.resync_bm25_from_dense()`
- **IncrementalIndexResult Enhancement**: Added sync status fields
  - `bm25_resynced: bool` - Whether resync was triggered
  - `bm25_resync_count: int` - Number of documents synced
- **Test Coverage**: 6 new unit tests (539 → 545 total)

### Files Modified

- `search/hybrid_searcher.py` - Added `resync_bm25_from_dense()` method
- `search/incremental_indexer.py` - Added auto-sync logic and result fields
- `tests/unit/test_hybrid_search.py` - 3 new resync tests
- `tests/unit/test_incremental_indexer.py` - 3 new auto-sync tests

### Why This Matters

Solves historical desync issue where BM25 index had fewer documents than dense index due to:

- BM25 being added after initial dense indexing
- Old bugs that have since been fixed
- Migration from older versions without BM25

Now incremental indexing is truly "self-healing" - any desync is automatically corrected.

---

## v0.5.16 - Graph Resolver Extraction (2025-11-24)

### Status: PRODUCTION-READY ✅

**Phase 7.1 of Refactoring Plan - Extract resolvers from call_graph_extractor.py**

### Changes

- **New `graph/resolvers/` Module**: Extracted 3 resolver classes from `call_graph_extractor.py`:
  - `TypeResolver` (~130 lines) - Type annotation extraction and parsing
  - `AssignmentTracker` (~115 lines) - Local variable assignment tracking
  - `ImportResolver` (~100 lines) - Import statement extraction with caching
- **Reduced Complexity**: `call_graph_extractor.py` reduced from 732 to ~400 lines
- **Clean Separation**: Each resolver has single responsibility
- **Persistent Project Selection**: Project choice persists across server restarts
  - New `mcp_server/project_persistence.py` - Save/load to `~/.claude_code_search/project_selection.json`
  - New `scripts/get_current_project.py` - Display helper for batch menu
  - Auto-restore on startup via `load_project_selection()`
  - Bidirectional sync: MCP tools ↔ batch menu
  - Menu displays current project in Runtime Status
- **Phase 4.2 - Multi-Hop Search Refactoring**: Extracted helper methods from `_multi_hop_search_internal()`:
  - `_validate_multi_hop_params()` - Parameter validation
  - `_expand_from_initial_results()` - Hop expansion logic
  - `_apply_post_expansion_filters()` - Post-expansion filtering
  - Main method reduced from 197 to ~100 lines
- **Phase 4.1 - Tree-Sitter Chunker Modularization**: Split `tree_sitter.py` into language modules:
  - Created `chunking/languages/` package with 10 files
  - Reduced `tree_sitter.py` from 1,154 to 275 lines (-76%)
  - Removed deprecated: Svelte, Java, JSX (kept 9 languages)
  - Backwards-compatible API maintained

### Migration Details

Old internal methods → New resolver methods:

- `_extract_type_annotations()` → `TypeResolver.extract_type_annotations()`
- `_annotation_to_string()` → `TypeResolver.annotation_to_string()`
- `_extract_local_assignments()` → `AssignmentTracker.extract_local_assignments()`
- `_infer_type_from_call()` → `AssignmentTracker.infer_type_from_call()`
- `_extract_imports()` → `ImportResolver.extract_imports()`
- `_read_file_imports()` → `ImportResolver.read_file_imports()`

### Files Created

- `graph/resolvers/__init__.py` - Exports all 3 resolver classes
- `graph/resolvers/type_resolver.py` - TypeResolver class
- `graph/resolvers/assignment_tracker.py` - AssignmentTracker class
- `graph/resolvers/import_resolver.py` - ImportResolver class

### Files Modified

- `graph/call_graph_extractor.py` - Uses resolver instances instead of internal methods
- `tests/unit/test_type_annotation_resolution.py` - Updated to use TypeResolver
- `tests/unit/test_assignment_tracking.py` - Updated to use AssignmentTracker

### Test Results

- 78 unit tests (100% pass)
- 9 integration tests (100% pass)
- No re-indexing required (internal refactoring only)

---

## v0.5.15 - Import-Based Resolution (2025-11-19)

### Status: PRODUCTION-READY ✅

**Phase 4 of Call Graph Resolution Plan - Resolve method calls via import tracking**

### New Features

- **Import-Based Resolution**: Method calls on imported classes now resolve to qualified names
  - `from handlers import ErrorHandler; x = ErrorHandler(); x.handle()` → `ErrorHandler.handle`
  - Aliased imports resolve to original class: `from x import Y as Z; z.method()` → `Y.method`
- **Full File Import Analysis**: Reads module-level imports from complete file (not just chunk)
- **Import Caching**: File imports cached per-file for performance
- **Coverage Increase**: ~90% of method calls correctly resolved (up from ~85-90% in Phase 3)

### Implementation Details

- **`_extract_imports()`**: Extracts import mappings from AST
  - `import os` → `{"os": "os"}`
  - `from x import Y` → `{"Y": "x.Y"}`
  - `from x import Y as Z` → `{"Z": "x.Y"}`
  - Relative imports: `from . import helper` → `{"helper": ".helper"}`
  - Star imports skipped (cannot resolve)
- **`_read_file_imports()`**: Reads full file to extract module-level imports
  - Uses `file_path` from `chunk_metadata`
  - Caches results per file
- **`_infer_type_from_call()`**: Updated to resolve aliased constructors
- **`_get_call_name()`**: Updated to check imports for class method resolution
- **Resolution Priority** (complete):
  1. Self/super calls (100% accurate) - Phase 1
  2. Type annotations (95% accurate) - Phase 2
  3. Assignment tracking (90% accurate) - Phase 3
  4. Import resolution (95% accurate) - Phase 4 ✅

### Files Modified

- `graph/call_graph_extractor.py` - Added import extraction, caching, and resolution
- New test files:
  - `tests/unit/test_import_resolution.py` (26 tests)
  - `tests/integration/test_import_resolution_integration.py` (11 tests)

### Test Results

- 26 unit tests (100% pass)
- 11 integration tests (100% pass)
- 89 backward compatibility tests (100% pass)

---

## v0.5.14 - Assignment Tracking (2025-11-19)

### Status: PRODUCTION-READY ✅

**Phase 3 of Call Graph Resolution Plan - Resolve method calls via local assignments**

### New Features

- **Assignment Tracking**: Method calls on locally assigned variables resolve to qualified names
  - `x = MyClass(); x.method()` → `MyClass.method`
- **Comprehensive Assignment Types**:
  - Constructor calls: `x = MyClass()`
  - Annotated assignments: `x: MyClass = value`
  - Named expressions: `if (x := MyClass()):`
  - Attribute assignments: `self.handler = Handler()`
  - With statements: `with Context() as ctx:`
- **Coverage Increase**: ~85-90% of method calls correctly resolved (up from ~80% in Phase 2)

---

## v0.5.13 - Type Annotation Resolution (2025-11-19)

### Status: PRODUCTION-READY ✅

**Phase 2 of Call Graph Resolution Plan - Resolve method calls via type annotations**

### New Features

- **Type Annotation Resolution**: Method calls on type-annotated parameters now resolve to qualified names
  - `def process(ext: ExceptionExtractor): ext.extract()` → `ExceptionExtractor.extract`
- **Coverage Increase**: ~80% of method calls correctly resolved (up from ~70% in Phase 1)

### Implementation Details

- **`_extract_type_annotations()`**: Extracts parameter annotations from all arg types
  - Positional args, keyword-only args, positional-only args
  - *args, **kwargs annotations
- **`_annotation_to_string()`**: Converts AST annotations to type names
  - Simple types: `MyClass`
  - Attributes: `module.MyClass` → `MyClass`
  - Generics: `Optional[X]`, `List[X]`, `Union[X, None]` → `X`
  - Forward references: `"MyClass"` → `MyClass`
- **Resolution Priority** (maintained):
  1. Self/super calls (100% accurate) - Phase 1
  2. Type annotations (95% accurate) - Phase 2 ✅
  3. Assignment tracking (Phase 3 - future)
  4. Import resolution (Phase 4 - future)

### Files Modified

- `graph/call_graph_extractor.py` - Added type annotation extraction and resolution
- New test files:
  - `tests/unit/test_type_annotation_resolution.py` (38 tests)
  - `tests/integration/test_type_annotation_integration.py` (9 tests)

### Test Coverage

- 38 unit tests for type annotation extraction and resolution
- 9 integration tests for full pipeline verification
- All 82 Phase 1+2 tests pass (100% pass rate)

### Requirements

⚠️ **RE-INDEX REQUIRED** for projects indexed before v0.5.13

### Benefits

✅ Reduced false positives in `find_connections`
✅ Accurate caller resolution for type-annotated parameters
✅ Support for Optional, List, Union, forward references
✅ Backward compatible with unannotated code

---

## v0.5.12 - Qualified Chunk IDs & Self/Super Resolution (2025-11-19)

### Status: PRODUCTION-READY ✅

**Phase 1 of Call Graph Resolution Plan - Foundation for accurate method resolution**

### New Features

- **Qualified Chunk IDs**: Methods now include class name (`ExceptionExtractor.extract`)
- **Self Call Resolution**: `self.method()` → `ClassName.method`
- **Super Call Resolution**: `super().method()` → `ParentClass.method`

### Implementation Details

- Added `parent_class` field to `TreeSitterChunk`
- Build qualified names in `multi_language_chunker.py`
- Track class hierarchy for super() resolution
- Store `is_resolved` flag on call edges

### Test Coverage

- 11 unit tests for qualified chunk IDs
- 16 unit tests for call resolution
- 8 integration tests for call graph resolution

### Requirements

⚠️ **RE-INDEX REQUIRED** for projects indexed before v0.5.12

---

## v0.5.11 - Priority 2 Relationship Types (2025-11-19)

### Status: PRODUCTION-READY ✅

**Added 4 new relationship types for enhanced code analysis**

### New Relationship Types

| Type | Forward Field | Reverse Field | Use Case |
|------|---------------|---------------|----------|
| `decorates` | `decorates` | `decorated_by` | Find decorator usage patterns |
| `raises` | `exceptions_raised` | `exception_handlers` | Error handling analysis |
| `catches` | `exceptions_caught` | - | Exception handling locations |
| `instantiates` | `instantiates` | `instantiated_by` | Find where classes are used |

### Implementation Details

- **DecoratorExtractor**: Extracts `@decorator`, `@module.decorator`, `@decorator(args)`
- **ExceptionExtractor**: Extracts both `raise` and `except` statements
- **InstantiationExtractor**: Uses heuristic (uppercase = class) with 0.8 confidence

### Files Modified

- `mcp_server/tools/code_relationship_analyzer.py` - 7 new ImpactReport fields
- `chunking/multi_language_chunker.py` - Registered 3 new extractors
- `graph/relationship_extractors/__init__.py` - Exported new extractors
- New files:
  - `graph/relationship_extractors/decorator_extractor.py`
  - `graph/relationship_extractors/exception_extractor.py`
  - `graph/relationship_extractors/instantiation_extractor.py`

### Test Coverage

- 35 unit tests for priority 2 extractors
- 6 integration tests for `find_connections` with new fields

### Requirements

⚠️ **RE-INDEX REQUIRED** for projects indexed before v0.5.11

### Benefits

✅ Find decorator patterns across codebase
✅ Analyze exception handling and error propagation
✅ Track class instantiation locations
✅ Complete relationship coverage for impact analysis

---

## v0.5.7 - Bug Fixes, Performance Improvements & Documentation (2025-11-18)

### Status: PRODUCTION-READY 2705

**Multiple bug fixes and comprehensive documentation updates**

### Key Fixes

- **Multi-hop Filter Propagation**: Filters now apply to expanded results
- **find_similar_code**: Fixed 0 results bug via path variant lookup
- **Query Routing Confidence**: Better scoring for natural queries
- **Dual SSE Timing**: Server verification timeout increased
- **Parse Error Logging**: Suppressed to DEBUG level
- **Phase 3 Relationship Extraction**: Complete graph type coverage

### Improvements

- Default search mode changed to hybrid
- Query routing keywords expanded
- Codebase cleanup: 26 files archived (38% reduction)
- Tool count updated: 14 → 15 MCP tools

### Documentation

- Filter Best Practices section added
- Phase 1 features fully documented
- MCP Tools Test Plan (55 queries)

---

## v0.5.6 - Phase 3 Complete Type Coverage (2025-11-17)

### Status: PRODUCTION-READY ✅

**Complete code relationship graph support**

### Key Fixes

- **Graph Type Coverage**: All semantic chunk types (not just functions) now contribute to graphs
  - Classes, structs, interfaces, enums, traits, impl blocks, constants, variables all indexed
  - File: - **HybridSearcher Graph Access**: Fixed incorrect graph path in relationship analyzer
  - Changed from \ to   - File:

### Relationship Types Now Available

| Field | Description |
|-------|-------------|
| \ | Classes/traits this code inherits from |
| \ | Classes/traits that inherit from this code |
| \ | Types used in annotations or field declarations |
| \ | Code chunks that use this type in annotations |
| \ | Modules/symbols imported by this code |
| \ | Code that imports this symbol |

### Requirements

⚠️ **RE-INDEX REQUIRED** for projects indexed before v0.5.6

### Benefits

✅ Find classes with inheritance hierarchy
✅ Discover type dependencies across codebase
✅ Track import relationships
✅ Complete dependency analysis with
---

## v0.5.5 - Low-Level MCP SDK Migration (2025-11-13)

### Status: PRODUCTION-READY ✅

**Migration from FastMCP to Official Anthropic MCP SDK**

### Key Changes

- **Server**: `mcp_server/server.py` (replaced with low-level SDK, 720 lines)
- **Backups**: `server_fastmcp_v1.py` (FastMCP), `server_lowlevel_complete.py` (development)
- **Transport**: SSE via Starlette + uvicorn (port 8765) + stdio
- **Application lifecycle**: Eliminates project_id=None bugs (100% fix)
- **SSE race conditions**: Prevented via guaranteed initialization order (100% fix)

### Test Results

- **19/19 unit tests** (100%)
- **1/1 integration test** (100%, lifecycle tests removed)
- **14/14 MCP tools fully operational** ✅
- **All 6 launch modes verified** working with low-level SDK

### Benefits

- Production-grade reliability (official Anthropic SDK)
- Eliminates project_id=None bugs completely
- Prevents SSE race conditions via guaranteed initialization
- Application-level lifecycle management via Starlette app_lifespan

### Enhancements (2025-11-15)

**Query Routing Improvements**: Natural query support without keyword stuffing

**Changes**:

- Lowered confidence threshold: 0.10 → 0.05 (more sensitive routing)
- Added 24 single-word keyword variants across all 3 models
- Natural queries ("error handling", "configuration loading", "merkle tree") now trigger routing effectively

**Technical Details**:

- Enhanced routing with single-word keywords: "error" (not just "error handling"), "configuration" (not just "configuration loading")
- Verified all 3 models (qwen3, bge_m3, coderankembed) physically switch and load correctly
- Natural language queries work without keyword stuffing (9/9 test queries successful)
- File modified: `search/query_router.py` (threshold + keyword expansion)

**Bug Fixes**:

- Windows launcher: Removed broken single SSE server option (Option 2) from `start_mcp_server.cmd`
- Simplified SSE transport menu to stdio + dual SSE only

---

## v0.5.4 - Multi-Model Query Routing (2025-11-10)

### Status: Production-Ready ✅

**Intelligent query routing to optimal embedding model**

### Features

- **100% routing accuracy** (8/8 verification queries)
- **5.3GB VRAM** for 3 models (Qwen3, BGE-M3, CodeRankEmbed)
- **<1ms routing overhead** (negligible)
- **15-25% quality gain** across diverse queries
- **Lazy loading** models on-demand
- **Backward compatible** single-model fallback

### Performance

- Qwen3-0.6B: Implementation-heavy queries (3/8 wins)
- BGE-M3: Workflow queries (3/8 wins)
- CodeRankEmbed: Specialized algorithms (2/8 wins)

### Configuration

```bash
set CLAUDE_MULTI_MODEL_ENABLED=true  # Enable (default)
set CLAUDE_MULTI_MODEL_ENABLED=false # Disable
```

**See**: `docs/ADVANCED_FEATURES_GUIDE.md#multi-model-query-routing`

---

## v0.5.3 - Graph-Enhanced Search (2025-11-06)

### Status: Production-Ready ✅

**Python AST call relationship tracking**

### Features

- **Python AST call tracking** with NetworkX storage
- **95%+ coverage** of Python call relationships
- **Optional graph field** in search results (calls/called_by)
- **57 tests** comprehensive validation
- **<5% overhead** negligible performance impact
- **~24MB** graph storage size

### Requirements

⚠️ **RE-INDEX REQUIRED** for projects indexed before 2025-11-06

### Example Output

```json
{
  "graph": {
    "calls": ["validate_credentials", "create_session"],
    "called_by": ["login_handler", "refresh_token"]
  }
}
```

**See**: `docs/ADVANCED_FEATURES_GUIDE.md#graph-enhanced-search`

---

## v0.5.3 - MCP Tool Output Format Fix (2025-11-06)

### Status: Production-Ready ✅

**All 13 tools return proper dict objects**

### Changes

- **AST-based fix** ensures dict objects (not JSON strings)
- **100% pass rate** all tools verified
- **Backward compatible** no breaking changes
- **Terminal output** clean and structured

---

## v0.5.2 - Comprehensive Validation & Features (2025-10-20)

### Status: Production Ready - Comprehensively Validated ✅

**256 queries across 16 configurations, 100% pass rate**

### Multi-Hop Search

- **93.3% queries benefit** (14/15 validation queries)
- **3.2 avg unique discoveries** per query
- **25-35ms overhead** empirically validated
- **40-60% top result changes** (improved relevance)

**Config**: Enabled by default (`multi_hop_count=2`, `multi_hop_expansion=0.3`)

**See**: `analysis/MULTI_HOP_RECOMMENDATIONS.md`

### Snowball Stemmer

- **93.3% success rate** for BM25 queries
- **3.33 avg unique discoveries** per query
- **~18ms overhead** negligible impact
- **11% smaller indices** storage optimization

**Config**: Enabled by default (`CLAUDE_BM25_USE_STEMMING=true`)

### BM25 Index v2

- **Version tracking** with config mismatch detection
- **Backward compatibility** validated
- **Automatic migration** from v1 to v2

### Hybrid Search Validation

- **Optimal 0.4/0.6 weights** validated
- **RRF reranking** operational
- **68-105ms avg query time** performance benchmark

### All Search Modes Validated

- **Hybrid**: 68-105ms (optimal balance)
- **Semantic**: 62-94ms (fastest)
- **BM25**: 3-8ms (keyword only)
- **Auto**: 52-57ms (adaptive)

### Edge Cases Handled

- Empty queries
- Single character queries
- Long queries (>500 chars)
- Special characters

### Validation Reports

- `analysis/COMPREHENSIVE_FEATURE_TEST_REPORT.md` - Full 256-query results
- `analysis/RECOMMENDATIONS_v0.5.2.md` - Production readiness (ALL APPROVED)
- `analysis/STEMMING_VALIDATION_REPORT.md` - Stemming impact analysis
- `analysis/MULTI_HOP_RECOMMENDATIONS.md` - Multi-hop testing results

---

## v0.5.1 - Performance & Cleanup Features (2025-10-15)

### Status: Production-Ready ✅

### Configurable Batch Sizes

- **8x faster embedding generation** via config-based optimization
- **BGE-M3**: 256 chunks/batch (optimal for 16GB+ VRAM)
- **EmbeddingGemma**: 128 chunks/batch (optimal for 8GB+ VRAM)
- **Real-world validation**: 1,582 chunks in 17 seconds (~93 chunks/second)

**Implementation**:

- `search/config.py` - MODEL_REGISTRY with recommended_batch_size
- `embeddings/embedder.py:290-301` - Auto-load from config
- Environment: `CLAUDE_EMBEDDING_BATCH_SIZE=256`

### Site-Packages Exclusion

- **99.5% reduction** in false-positive indexing
- Auto-excluded: `.venv`, `node_modules`, `__pycache__`, `site-packages`
- Prevents indexing of Python dependencies

### Batch Removal Optimization

- **600-1000x faster** incremental indexing for deletions
- **O(n) single-pass** vs O(n×m) per-file scanning
- **250 files**: 0.11s (was 1.5+ hours = 49,000x faster)
- **1,155 files**: ~0.5s (would have been 1.5+ hours = 10,800x faster)

**Implementation**:

- `search/indexer.py:455-627`
- `search/bm25_index.py:555-652`
- `search/hybrid_searcher.py:938-1007`
- `search/incremental_indexer.py:361-401`

**Critical Fix**: Proper FAISS vector removal via index rebuild, preventing access violations

### Merkle Snapshot Cleanup

- **Auto-delete stale snapshots** during force re-index
- Prevents accumulation of obsolete snapshot files
- Ensures "force = clean slate" semantics

### SSE Transport

- **Bypasses Claude Code stdio bugs** (#3426, #768, #3487, #3369)
- **Port 8765** single server mode
- **<10ms overhead** negligible latency
- **Auto port conflict** detection and resolution

### Cleanup Utilities

- `tools/cleanup_orphaned_projects.py` - Remove orphaned test projects
- `tools/cleanup_stale_snapshots.py` - Interactive snapshot cleanup

### Enhanced Menu

- **7 options** with clear workflow separation
- Quick Start, Project Management, Search Config, Advanced

---

## v0.4.0 - GPU Optimization & Per-Model Indices (2025-10-01)

### Status: Production-Ready ✅

### GPU Memory Optimization

- **72% vRAM reduction** via automatic cleanup
- Enhanced `indexer.clear_index()` explicitly deletes GPU FAISS indices
- Test cleanup tracks all indexers, calls `clear_index()` in teardown
- Smart cleanup clears embedder registry selectively
- ALWAYS clears GPU cache (`torch.cuda.empty_cache()`)

**Fixtures**:

- `session_embedder` (scope=session): Loads model once, reused
- `embedder_with_cleanup` (scope=function): Per-test embedder
- `smart_memory_cleanup` (autouse): Clears GPU cache after each test

**Known Issues**:

- `test_change_detection` skipped (multiple MerkleDAG instances)
- Hybrid search tests cause 14GB VRAM accumulation (embeddings/indices, not model)

### Per-Model Indices

- **Instant model switching** <150ms, no re-indexing
- **Dimension-based isolation**: 768d/1024d separate storage
- **Multi-project support**: Independent indices per project

**Storage Structure**:

```
~/.claude_code_search/
├── projects/
│   ├── project_abc123_768d/      ← Gemma indices
│   ├── project_abc123_1024d/     ← BGE-M3 indices
└── merkle/
    ├── abc123_768d_snapshot.json
    └── abc123_1024d_snapshot.json
```

**Performance Benefits**:

- First model switch: 30-60s (indexing required)
- Return to previous model: <150ms (98% faster)
- Model comparison workflow: <1s (99% faster)

### Independent Merkle Snapshots

- **Dimension-based change tracking**
- Per-model snapshot isolation prevents cross-contamination
- Automatic deletion when clearing indices

### Multi-Project Isolation

- **Correct project tracking** validated
- Projects don't interfere with each other
- Complete isolation between workspaces

---

## Earlier Versions

### v0.3.x - Hybrid Search & BM25 Integration

- Hybrid search implementation (BM25 + semantic)
- RRF (Reciprocal Rank Fusion) reranking
- Configurable search modes (hybrid/semantic/bm25)
- FAISS vector search optimization

### v0.2.x - Multi-Language Support

- Tree-sitter integration (11 languages)
- AST-based Python chunking
- Semantic chunking across 22 file extensions
- Function/class/method extraction

### v0.1.x - Initial Release

- Basic MCP server implementation
- Single model support (BGE-M3)
- FAISS semantic search
- Incremental indexing with Merkle trees
- Token reduction (40-45% vs traditional methods)

---

## Multi-Project Documentation

**Stream Diffusion CLAUDE.md** updated with v0.5.2 validation metrics (2025-10-23)

---

## Additional Resources

- **Features Guide**: `docs/ADVANCED_FEATURES_GUIDE.md`
- **Installation**: `docs/INSTALLATION_GUIDE.md`
- **Testing**: `docs/TESTING_GUIDE.md`
- **MCP Tools**: `docs/MCP_TOOLS_REFERENCE.md`
- **Documentation Index**: `docs/DOCUMENTATION_INDEX.md`
