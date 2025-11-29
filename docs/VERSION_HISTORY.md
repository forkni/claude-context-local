# Version History

Complete version history and feature timeline for claude-context-local MCP server.

## Current Status: All Features Operational (2025-11-28)

- **Version**: 0.6.0
- **Status**: Production-ready
- **Test Coverage**: 545 unit tests + integration tests (100% pass rate)
- **Index Quality**: 109 active files, 1,199 chunks (site-packages excluded, BGE-M3 1024d, ~24 MB)
- **Token Reduction**: 85-95% (validated benchmark)
- **Call Graph Resolution**: Phase 4 complete (~90% accuracy)
- **Refactoring**: Phase 7.1 complete (resolver extraction)

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

**See**: `docs/PER_MODEL_INDICES_IMPLEMENTATION.md`

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
- Configurable search modes (hybrid/semantic/bm25/auto)
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
