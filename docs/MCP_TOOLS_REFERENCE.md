# MCP Tools Reference

## Quick Integration Guide

This modular reference can be embedded in any project instructions for Claude Code integration.

---

## Available MCP Tools (19)

| Tool | Priority | Purpose | Parameters |
|------|----------|---------|------------|
| **search_code** | 🔴 **ESSENTIAL** | Find code with natural language OR lookup by symbol ID | query OR chunk_id, k=4, search_mode="hybrid", model_key, use_routing=True, file_pattern, include_dirs, exclude_dirs, chunk_type, include_context=True, auto_reindex=True, max_age_minutes=5, ego_graph_enabled=False, ego_graph_k_hops=2, ego_graph_max_neighbors_per_hop=10, include_parent=False, max_context_tokens=0 |
| **find_connections** | 🟡 **IMPACT** | Analyze dependencies & impact (~90% accuracy with import resolution) | chunk_id (preferred) OR symbol_name, max_depth=3, exclude_dirs, relationship_types |
| **find_path** | 🟡 **IMPACT** | Trace shortest path between code entities in relationship graph | source OR source_chunk_id, target OR target_chunk_id, edge_types, max_hops=10 |
| **index_directory** | 🔴 **SETUP** | Index project (multi-model support) | directory_path (required), project_name, incremental=True, multi_model=auto |
| **find_similar_code** | 🟡 **IMPACT** | Find alternative implementations | chunk_id (required), k=4 |
| configure_search_mode | Config | Set search mode & weights | search_mode="hybrid", bm25_weight=0.4, dense_weight=0.6, enable_parallel=True |
| configure_query_routing | Config | Configure multi-model routing (v0.5.4+) | enable_multi_model, default_model, confidence_threshold=0.05 |
| configure_reranking | Config | Configure neural reranker settings | enabled, model_name, top_k_candidates=50 |
| configure_chunking | Config | Configure code chunking settings | enable_community_detection, enable_community_merge, community_resolution, token_estimation, enable_large_node_splitting, max_chunk_lines, split_size_method, max_split_chars, enable_file_summaries, enable_community_summaries |
| get_search_config_status | Config | View current configuration | *(no parameters)* |
| get_index_status | Status | Check index health & model info | *(no parameters)* |
| get_memory_status | Monitor | Check RAM/VRAM usage | *(no parameters)* |
| list_projects | Management | Show indexed projects grouped by path | *(no parameters)* |
| switch_project | Management | Change active project | project_path (required) |
| clear_index | Reset | Delete current index (all dimensions) | *(no parameters)* |
| delete_project | Management | Safely delete indexed project | project_path (required), force=False |
| cleanup_resources | Cleanup | Free memory/caches (GPU + index) | *(no parameters)* |
| list_embedding_models | Model | View available embedding models | *(no parameters)* |
| switch_embedding_model | Model | Switch embedding model (instant <150ms) | model_name (required) |

---

## Filter Parameters for search_code

| Parameter | Type | Description | Valid Values |
|-----------|------|-------------|--------------|
| **file_pattern** | string | Substring match on file path | Any string (e.g., "auth", "test_", "utils/") |
| **include_dirs** | array | Only search in these directories (prefix match) | `["src/", "lib/"]` |
| **exclude_dirs** | array | Exclude from search (prefix match) | `["tests/", "vendor/", "node_modules/"]` |
| **chunk_type** | string | Filter by code structure type | `"function"`, `"class"`, `"method"`, `"module"`, `"community"`, `"decorated_definition"`, `"interface"`, `"enum"`, `"struct"`, `"type"`, `"merged"`, `"split_block"` |

**Synthetic Summary Chunk Types (v0.9.0+)**:

- `"module"`: File-level module summary chunks (A2 feature). Synthetic chunks generated per file with 2+ real chunks, containing file path, module name, classes, functions, key methods, imports, and docstring excerpts. Improves GLOBAL query recall.
- `"community"`: Community-level summary chunks (B1 feature). Synthetic chunks generated per community (via Louvain detection) with 2+ members, containing community ID, dominant directory, classes/functions in the community, hub function, and imports. Improves GLOBAL query recall.

**Chunking Chunk Types (v0.8.4+)**:

- `"merged"`: Community-merged chunks created by community detection. Multiple related code blocks merged together for better semantic context (e.g., related helper functions merged with main class).
- `"split_block"`: Large function blocks split at AST boundaries when exceeding `max_chunk_lines` (default: 100 lines). Enables better granularity for very large functions.

### Directory Filtering (v0.5.9+)

**Path Matching**: Uses prefix matching with normalized separators (`\` → `/`)

```python
# Only search in source directories
search_code("auth handler", include_dirs=["src/", "lib/"])

# Exclude tests and vendor
search_code("database connection", exclude_dirs=["tests/", "vendor/"])

# Combine both
search_code("user model", include_dirs=["src/"], exclude_dirs=["src/tests/"])
```

**For find_connections**: Use `exclude_dirs` to filter symbol resolution:

```python
# Find production code, not test doubles
find_connections(symbol_name="UserService", exclude_dirs=["tests/"])
```

**Note**: In `find_connections`, `exclude_dirs` applies to symbol resolution only. Callers are not filtered (to preserve test coverage visibility).

**Filter by relationship types** (v0.8.4+): Use `relationship_types` to get only specific relationship data:

```python
# Get only inheritance relationships
find_connections(symbol_name="BaseClass", relationship_types=["inherits"])
# Returns: Only parent_classes/child_classes populated, all others empty

# Get only import relationships
find_connections(chunk_id="...", relationship_types=["imports"])
# Returns: Only imports/imported_by populated

# Get multiple specific types
find_connections(symbol_name="MyClass", relationship_types=["inherits", "imports", "decorates"])
```

**Valid relationship types**: `calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`, `defines_constant`, `defines_enum_member`, `defines_class_attr`, `defines_field`, `uses_constant`, `uses_default`, `uses_global`, `asserts_type`, `uses_context_manager`

### Filter Examples

```bash
# Find functions in test files only
/search_code "authentication" --file_pattern "test_"

# Find only classes
/search_code "user model" --chunk_type "class"

# Find methods in specific module
/search_code "database" --file_pattern "models" --chunk_type "method"
```

### Filter Best Practices

**⚠️ Post-Filtering Behavior**: Filters apply AFTER search, not during.

**Implications**:

- Query must find semantically relevant code first
- Filter then removes non-matching results
- Generic queries may return 0 results if initial search doesn't find matching files

**Examples**:

| Query | Filter | Expected Result |
|-------|--------|-----------------|
| `"test"` | `indexer` | ❌ 0 results (query too generic) |
| `"index directory embedding"` | `indexer` | ✅ Results from indexer files |
| `"search implementation"` | `hybrid` | ✅ Results from hybrid_searcher.py |

**Recommendation**: Use specific, descriptive queries when filtering:

- ❌ `"test"` with `file_pattern="indexer"` → Too generic
- ✅ `"incremental index file update"` with `file_pattern="indexer"` → Specific query

**Multi-Hop Note**: Filters are applied to both initial results AND expanded results to maintain consistency.

---

## Ego-Graph Expansion Parameters (v0.8.4+)

**Feature**: RepoGraph-style k-hop ego-graph retrieval for context expansion (ICLR 2025)

**Purpose**: Automatically retrieve graph neighbors (callers, callees, related code) for search results to provide richer context beyond semantic similarity.

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `ego_graph_enabled` | boolean | false | - | Enable k-hop neighbor expansion from call graph |
| `ego_graph_k_hops` | integer | 2 | 1-5 | Graph traversal depth (1=direct neighbors, 2=neighbors of neighbors) |
| `ego_graph_max_neighbors_per_hop` | integer | 10 | 1-50 | Limit neighbors per hop to prevent explosion |

**⭐ NEW (v0.8.3): Automatic Import Filtering**

When ego-graph expansion is enabled, **stdlib and third-party imports are automatically filtered** from graph traversal (RepoGraph Feature #5: Repository-Dependent Relation Filtering). This results in:

- **30-50% fewer edges** traversed (cleaner graphs)
- **More relevant neighbors** (project-internal code only)
- **Faster graph traversal** (fewer nodes to process)

Filtering uses Python 3.10+ `sys.stdlib_module_names` for comprehensive stdlib detection and auto-discovers project modules from directory structure.

### Usage Examples

```python
# Basic ego-graph expansion (2-hop, max 10 neighbors per hop)
search_code("authentication handler", ego_graph_enabled=True)

# Shallow expansion (only direct neighbors)
search_code("database connection", ego_graph_enabled=True, ego_graph_k_hops=1)

# Deep expansion with more neighbors
search_code("request processing", ego_graph_enabled=True, ego_graph_k_hops=3, ego_graph_max_neighbors_per_hop=20)
```

### Performance Characteristics

- **Neighbor retrieval**: 780-1000 neighbors per anchor (complex classes)
- **Symbol filtering**: 4-33 symbol-only nodes removed per anchor
- **Expansion factor**: 3.5-4.6× (e.g., 5 anchors → 23 total results)
- **Overhead**: Minimal (~0-5ms for graph traversal)

### Result Marking

Ego-graph neighbors are marked in results with:

- `score`: 0.0 (neighbors are context, not direct matches)
- `source`: "ego_graph" (identifies origin)
- `rank`: 0 (default rank)

---

## Parent-Child Retrieval Parameters (v0.8.4+)

**Feature**: "Match Small, Retrieve Big" pattern for improved LLM comprehension

**Purpose**: When a method is matched during search, automatically retrieve its enclosing class to provide full context. Solves the "orphan chunk" problem where methods lack class-level context.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `include_parent` | boolean | false | Enable parent chunk retrieval for methods |

### Usage Examples

```python
# Basic parent retrieval (method + enclosing class)
search_code("validate user data", chunk_type="method", include_parent=True)

# Search for authentication methods with class context
search_code("authentication methods", include_parent=True)
```

### How It Works

1. **Search Phase**: Find methods matching your query
2. **Expansion Phase**: For each matched method, retrieve its parent class using `parent_chunk_id` metadata
3. **Results**: Return both the method (scored) and its parent class (score=0.0)

### Performance Characteristics

- **Expansion overhead**: Minimal (~0-5ms for metadata lookup)
- **Result expansion**: 1-2× (e.g., 5 methods → 5-10 total results)
- **Re-indexing**: Required once to populate `parent_chunk_id` metadata

### Result Marking

Parent chunks are marked in results with:

- `score`: 0.0 (parents provide context, not direct matches)
- `source`: "parent_expansion" (identifies origin)
- `rank`: 0 (default rank)

### Example Output

```json
{
  "results": [
    {
      "chunk_id": "auth.py:45-52:method:validate",
      "kind": "method",
      "score": 0.89,
      "name": "validate"
    },
    {
      "chunk_id": "auth.py:10-60:class:User",
      "kind": "class",
      "score": 0.0,
      "source": "parent_expansion",
      "name": "User"
    }
  ]
}
```

---

## Search Result Fields

The `search_code` tool returns results with the following fields:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `chunk_id` | string | ✅ | Unique identifier (format: `"file:lines:type:name"`) |
| `kind` | string | ✅ | Chunk type (`function`, `class`, `method`, etc.) |
| `score` | float | ✅ | Relevance score (0.0-1.0, rounded to 2 decimals) |
| `source` | string | ⚠️ Optional | Result source (`"ego_graph"` for graph neighbors, omitted for direct matches) |
| `file` | string | ✅ (verbose only) | Relative file path (omitted in compact/ultra since `chunk_id` contains this) |
| `lines` | string | ✅ (verbose only) | Line range (e.g., `"10-25"`, omitted in compact/ultra) |
| `name` | string | ⚠️ Optional | Symbol name (when available) |
| `complexity_score` | integer | ⚠️ Optional | Cyclomatic complexity (functions/methods only) |
| `reranker_score` | float | ⚠️ Optional | Neural reranker score (when reranking enabled, rounded to 4 decimals) |
| `graph` | object | ⚠️ Optional | Call relationships (`calls`, `called_by` arrays) |

### Field Details

**`complexity_score`** (Cyclomatic Complexity):

- **Only present for**: Functions and methods (Python only currently)
- **Calculation**: CC = 1 + decision_points (if/elif, for, while, except, and/or, ternary, match/case)
- **Use cases**:
  - Identify complex code needing refactoring (CC > 10 is high complexity)
  - Prioritize code review focus areas
  - Find simple entry points for code understanding (CC = 1-2)
- **Example**: `"complexity_score": 5` indicates 5 decision paths through the function

**`graph`** (Call Relationships):

- **Structure**: `{"calls": ["chunk_id1", ...], "called_by": ["chunk_id2", ...]}`
- **Only present when**: Graph storage is available and relationships exist
- **Use with**: `find_connections` for detailed dependency analysis

---

## Output Format Options

All 19 MCP tools support configurable output formatting via the `output_format` parameter. This allows you to optimize token usage while preserving 100% of data.

### Available Formats

| Format | Token Reduction | Use Case | Description |
|--------|----------------|----------|-------------|
| **verbose** | 0% (baseline) | Debugging, backward compatibility | Verbose JSON with indent=2, all fields included |
| **compact** | 30-40% | Default, recommended | Omits empty fields, no indentation, removes redundant data |
| **ultra** | 45-55% | Large result sets, bandwidth-constrained | Tabular arrays with header-declared fields |

### Configuration

**Set default format** (persists across sessions):

```bash
# Via interactive menu
start_mcp_server.cmd → 3. Search Configuration → A. Configure Output Format

# Or directly in search_config.json
"output_format": "compact"  # verbose, compact, or ultra
```

**Override per-query**:

```python
# Use Ultra format for this query only
search_code("authentication", k=10, output_format="ultra")
find_connections(chunk_id="...", output_format="compact")
```

### Understanding Ultra Tabular Format

Ultra format optimizes token usage by declaring field names once in a header, then providing data as arrays of values.

#### Format Structure

**Header Pattern**: `"array_name[count]{field1,field2,field3}"`

- `array_name`: Name of the array (e.g., "results", "callers")
- `[count]`: Number of elements in the array
- `{fields}`: Comma-separated field names in order

**Data Pattern**: `[[val1, val2, val3], [val1, val2, val3], ...]`

- Each row is an array of values
- Values map to fields by position (index 0 → field1, index 1 → field2, etc.)

#### Examples

**Standard JSON** (baseline):

```json
{
  "results": [
    {"chunk_id": "auth.py:10-25:function:login", "kind": "function", "score": 0.95},
    {"chunk_id": "auth.py:30-45:function:logout", "kind": "function", "score": 0.87}
  ]
}
```

**Tokens**: ~60 chars for field names × 2 = 120 chars overhead

**Ultra Format** (45-55% reduction):

```json
{
  "results[2]{chunk_id,kind,score}": [
    ["auth.py:10-25:function:login", "function", 0.95],
    ["auth.py:30-45:function:logout", "function", 0.87]
  ],
  "_format_note": "Ultra format: header[count]{fields}: [[row1], [row2], ...]"
}
```

**Tokens**: 36 chars for field names × 1 = 36 chars overhead (70% reduction)

#### Parsing Ultra Format

**Step-by-step algorithm**:

1. **Extract header**: `"results[2]{chunk_id,kind,score}"`
   - Array name: `"results"`
   - Count: `2`
   - Fields: `["chunk_id", "kind", "score"]`

2. **Map row values to fields**:

   ```python
   fields = ["chunk_id", "kind", "score"]
   row1 = ["auth.py:10-25:function:login", "function", 0.95]
   
   # Reconstruct object
   object1 = {
       "chunk_id": row1[0],  # "auth.py:10-25:function:login"
       "kind": row1[1],       # "function"
       "score": row1[2]       # 0.95
   }
   ```

3. **Result**: Standard JSON object reconstructed from tabular data

#### Real-World Example

**Query**: `find_connections("mcp_server/output_formatter.py:109-177:function:_to_toon_format")`

**Ultra Response**:

```json
{
  "symbol": "_to_toon_format",
  "chunk_id": "mcp_server/output_formatter.py:109-177:function:_to_toon_format",
  "direct_callers[1]{chunk_id,kind,score}": [
    ["mcp_server/output_formatter.py:17-34:function:format_response", "function", 1.0]
  ],
  "similar_code[10]{chunk_id,kind,score}": [
    ["mcp_server/output_formatter.py:37-77:function:_to_compact_format", "function", 0.82],
    ["search/hybrid_searcher.py:245-289:function:_format_results", "function", 0.76],
    ...
  ],
  "_format_note": "Ultra format: header[count]{fields}: [[row1], [row2], ...]"
}
```

**Token Savings**:

- Standard JSON: 10 similar_code results × 3 fields = 30 field name occurrences
- TOON format: 3 field names declared once = 3 occurrences
- **Reduction**: (30-3)/30 = 90% field name token savings for this array

#### Schema Flexibility

Different arrays in the same response can have different schemas:

```json
{
  "direct_callers[1]{chunk_id,kind,score}": [...],
  "uses_types[1]{target_name,relationship_type,kind,line,confidence,note}": [...]
}
```

Notice:

- `direct_callers` has 3 fields
- `uses_types` has 6 fields
- Both use TOON format with appropriate headers

### Token Reduction Analysis

**Test Query**: `find_connections` with 5 callers + 10 similar_code results

| Format | Characters | Estimated Tokens | Reduction |
|--------|-----------|------------------|-----------|
| JSON | 3,259 | ~814 | 0% (baseline) |
| Compact | 2,167 | ~541 | 33.5% |
| TOON | 1,877 | ~469 | 42.4% |

**Recommendation**:

- Use **compact** as default (good balance of readability and efficiency)
- Use **toon** for large result sets (k > 10) or bandwidth-constrained environments
- Use **json** only for debugging or when you need maximum readability

---

## Essential Workflow

**Discovery & Exploration**:

```
1. index_directory("C:\path\to\project")          # One-time setup
2. search_code("what you need")                    # Find code instantly
3. find_connections(chunk_id)                      # Analyze impact/dependencies
4. Read tool ONLY after search                     # Edit specific files
```

**Direct Symbol Lookup** (when you have chunk_id from previous search):

```
search_code(chunk_id="file.py:10-20:function:name")  # O(1) unambiguous lookup
```

---

## Search Configuration

### Available Modes

- **hybrid** (default) - BM25 + semantic fusion (best accuracy)
- **semantic** - Dense vector search only (best for concepts)
- **bm25** - Sparse keyword search only (best for exact terms)
- **auto** - Adaptive mode selection

### Commands

```
/configure_search_mode "hybrid" 0.4 0.6   # Set mode + weights
/get_search_config_status                 # Check current config
```

---

## Chunking Configuration

### configure_chunking

**Purpose**: Configure code chunking settings at runtime

**Parameters**:

- `enable_chunk_merging` (bool): Enable/disable greedy chunk merging (default: True)
- `min_chunk_tokens` (int): Minimum tokens before merge (10-500, default: 50)
- `max_merged_tokens` (int): Maximum tokens for merged chunks (100-5000, default: 1000)
- `token_estimation` (str): Token estimation method - "whitespace" (fast) or "tiktoken" (accurate, default: "whitespace")
- `enable_large_node_splitting` (bool): Enable AST block splitting for large functions (default: False)
- `max_chunk_lines` (int): Maximum lines per chunk before splitting at AST boundaries (10-1000, default: 100)

**Returns**: Updated configuration + system message

**Note**: Re-index project to apply changes

### Commands

```
/configure_chunking --enable_chunk_merging true --min_chunk_tokens 50
/configure_chunking --enable_large_node_splitting true --max_chunk_lines 100
/get_search_config_status  # View current chunking settings
```

---

## Performance Metrics

| Metric | Traditional Reading | Semantic Search (First) | Semantic Search (Cached) | Improvement |
|--------|---------------------|-------------------------|--------------------------|-------------|
| Tokens | 5,600 | 400 | 400 | 93% reduction |
| Speed | 30-60s | 8-15s (includes 5-10s model load) | 3-5s | 2-3x faster |
| VRAM | 0 MB | 0 MB → 1.5-5.3 GB (on-demand) | 1.5-5.3 GB | Lazy loading |
| Accuracy | Hit-or-miss | Targeted | Targeted | Precision |

**Performance Notes (v0.5.17+)**:

- **Startup**: 3-5s server start, 0 MB VRAM (models load on first search)
- **First search per session**: 8-15s total (5-10s one-time model loading + 3-5s search)
- **Subsequent searches**: 3-5s (models stay loaded in memory)
- **Manual cleanup**: Use `/cleanup_resources` to unload models and return to 0 MB VRAM

**Timing Instrumentation (v0.8.6+)**:

- **Enable logging**: Set `CLAUDE_LOG_LEVEL=INFO` to see `[TIMING]` logs for 5 critical operations
- **Instrumented operations**: `embed_query`, `bm25_search`, `dense_search`, `neural_rerank`, `multi_hop_search`
- **Log format**: `[TIMING] operation_name: Xms` (milliseconds, 2 decimal precision)
- **Module**: `utils/timing.py` provides `@timed()` decorator and `Timer()` context manager
- **Overhead**: <0.1ms per operation (negligible)

---

## Example Usage

```
# Index project
/index_directory "C:\Projects\MyApp"

# Search for functionality
/search_code "authentication login functions"
/search_code "error handling try except"
/search_code "database connection setup"

# Find similar code
/find_similar_code "auth.py:15-42:function:login"

# Configure search
/configure_search_mode "hybrid" 0.4 0.6
/get_search_config_status

# Model management
/list_embedding_models
/switch_embedding_model "BAAI/bge-m3"

# Multi-model routing configuration (v0.5.4+)
/configure_query_routing true                       # Enable multi-model mode (default)
/configure_query_routing false                      # Disable multi-model (single-model fallback)
/configure_query_routing true "qwen3" 0.05          # Enable + set default model + confidence threshold (default)
/configure_query_routing None "bge_m3" None         # Just change default model (keep multi-model enabled)

# Multi-model search usage
/search_code "Merkle tree detection"                # Auto-routes to optimal model (CodeRankEmbed)
/search_code "error handling" --model_key "qwen3"   # Force specific model override
/search_code "configuration" --use_routing False    # Disable routing for this query (use default)

# Natural query routing examples (v0.5.5+)
# Natural language queries now work without keyword stuffing
/search_code "error handling"                       # Routes to Qwen3 (implementation focus)
/search_code "configuration loading"                # Routes to BGE-M3 (workflow focus)
/search_code "merkle tree"                          # Routes to CodeRankEmbed (specialized algorithm)
/search_code "algorithm implementation"             # Routes to Qwen3 (confidence ~0.12)
/search_code "initialization process"               # Routes to BGE-M3 (confidence ~0.11)

# Routing transparency - every search shows which model was used
# Output includes: "routing": {"model_selected": "qwen3", "confidence": 0.08, "reason": "..."}
```

---

## cleanup_resources - Manual Memory Cleanup

**Tool**: `cleanup_resources`  
**Priority**: 🔧 Maintenance  
**Purpose**: Free model memory, GPU cache, and index data

### When to Use

- After indexing large projects (free VRAM)
- When switching between multiple projects
- Before intensive GPU operations
- If you notice high VRAM usage (check with `/get_memory_status`)
- To return to baseline 0 MB VRAM state

### What It Does

1. **Unloads all embedding models** from VRAM (returns to 0 MB baseline)
2. **Clears GPU cache** (`torch.cuda.empty_cache()`)
3. **Clears FAISS index data** from memory
4. **Runs Python garbage collection** (7000+ objects typically)
5. **Returns memory statistics** (models unloaded, GPU freed, objects collected)

### Parameters

**None** - No parameters required

### Usage Examples

```bash
# Basic usage - free all memory
/cleanup_resources
# Output: {"success": true, "message": "Resources cleaned up successfully"}

# Check memory before cleanup
/get_memory_status
# Output: {"allocated_vram_mb": 5300, "models_loaded": 3}

# Clean up resources
/cleanup_resources

# Check memory after cleanup  
/get_memory_status
# Output: {"allocated_vram_mb": 0, "models_loaded": 0}
```

### Common Workflow

```bash
# 1. Index large project (uses memory)
/index_directory "C:\LargeProject"

# 2. Perform searches (models loaded, ~5.3 GB VRAM)
/search_code "authentication"
/search_code "database connection"

# 3. Done with project - free memory
/cleanup_resources  
# ✓ Models unloaded
# ✓ GPU cache freed
# ✓ Index data cleared
# ✓ 7000+ objects garbage collected

# 4. Switch to different project
/switch_project "C:\AnotherProject"

# 5. Next search will reload models (5-10s)
/search_code "error handling"  # Triggers model load
```

### Performance Impact

| Metric | Value | Notes |
|--------|-------|-------|
| **VRAM freed** | Returns to 0 MB | Baseline state |
| **Operation time** | 1-2s | Fast cleanup |
| **Next search** | +5-10s delay | One-time model reload |
| **Recommended frequency** | After project switches | Or when memory constrained |

### Memory Lifecycle (v0.5.17+)

```
Server startup:              0 MB VRAM (lazy loading)
       ↓ First search:       5-10s model loading
       ↓ Models loaded:      1.5-5.3 GB VRAM (depending on config)
       ↓ Searches:           3-5s per search
       ↓ cleanup_resources:  Returns to 0 MB
       ↓ Next search:        5-10s model reload (one-time)
```

### Benefits

- **Free VRAM**: Return to baseline 0 MB state
- **Multi-project workflow**: Clean slate between projects
- **GPU memory management**: Prevent OOM errors
- **Debugging**: Clear state for troubleshooting

### Notes

- **Automatic on exit**: Resources automatically cleaned on server shutdown
- **Models reload automatically**: Next search triggers 5-10s load (normal behavior)
- **No data loss**: Index files remain on disk, only in-memory state cleared
- **Safe operation**: Can run anytime without breaking functionality

---

## Query Enhancement for Optimal Routing

### Why Query Enhancement Matters

The multi-model routing system uses keyword matching to select optimal embedding models. Natural language queries often produce **low confidence scores (0.05-0.15)**, causing fallback to the default model even when a specialized model would perform better.

**Solution**: Claude Code should enhance queries with routing keywords before sending to MCP search.

### Enhancement Protocol for Claude Code

When calling `search_code()`, Claude Code should analyze user intent and expand queries:

**1. Classify Query Intent & Add Domain Keywords**

| User Query About | Add These Keywords | Route To |
|------------------|-------------------|----------|
| Error handling, exceptions | `error handling exception try except pattern` | Qwen3 |
| Implementation, algorithms | `implementation algorithm function pattern` | Qwen3 |
| Async/concurrent code | `async await coroutine concurrent implementation` | Qwen3 |
| Configuration, setup | `configuration loading initialization workflow setup` | BGE-M3 |
| Workflows, processes | `workflow process pipeline flow` | BGE-M3 |
| Vector search, FAISS | `faiss vector similarity embedding dense` | BGE-M3 |
| Trees, graphs, DAGs | `merkle tree graph structure binary dag` | CodeRankEmbed |
| Ranking, fusion | `rrf reranking reciprocal rank fusion` | CodeRankEmbed |

**2. Expand Natural Language to Technical Terms**

| User Says | Expand To | Reason |
|-----------|-----------|--------|
| "find error code" | `"error handling exception try except pattern"` | Add domain keywords |
| "config stuff" | `"configuration loading initialization setup workflow"` | Clarify vague terms |
| "tree search" | `"merkle tree binary graph structure search"` | Disambiguate "tree" |
| "async code" | `"async await coroutine asyncio concurrent implementation"` | Add technical terms |
| "database setup" | `"database connection initialization configuration setup"` | Add setup keywords |
| "how errors handled" | `"error handling exception try except implementation"` | Add intent keywords |

**3. Use Model Override for Low Confidence Scenarios**

When confidence would be <0.10, explicitly specify the model:

```python
# Instead of hoping for correct routing:
search_code("handle errors")  # Low confidence, may default to BGE-M3

# Enhance query AND override model:
search_code("error handling exception try except pattern", model_key="qwen3")
```

### Quick Reference: Model Selection

| Model | Best For | Key Triggers |
|-------|----------|--------------|
| **Qwen3** | Implementation, algorithms, error handling, async | `implement`, `algorithm`, `error`, `exception`, `async`, `pattern` |
| **BGE-M3** | Configuration, workflows, vector search | `config`, `workflow`, `setup`, `faiss`, `vector`, `embedding` |
| **CodeRankEmbed** | Data structures, specialized algorithms | `merkle`, `tree`, `graph`, `rrf`, `rerank`, `fusion` |

### Example: Complete Enhancement Flow

**User request**: "Find where errors are caught in the codebase"

**Claude Code enhancement**:

```
1. Intent: Error handling implementation
2. Expanded query: "error handling exception try except catch pattern"
3. Expected routing: Qwen3 (implementation focus)
4. Call: search_code("error handling exception try except catch pattern")
```

**Alternative with model override** (for guaranteed routing):

```
search_code("error handling exception try except", model_key="qwen3")
```

### Benefits of Enhancement

1. **Higher confidence scores**: 0.05 → 0.15+ with added keywords
2. **Correct model selection**: Queries route to optimal model
3. **Better results**: Specialized models outperform default by 15-25%
4. **Zero latency**: No additional API calls (Claude Code is the LLM)

---

## Symbol ID Lookup Examples (Phase 1.1)

**Feature**: O(1) unambiguous symbol retrieval using chunk IDs from previous search results.

**Format**: `"file.py:start-end:type:name"`

**Examples**:

```
# Direct lookup (no semantic search overhead)
/search_code --chunk_id "auth.py:15-42:function:login"
/search_code --chunk_id "models.py:100-150:class:User"
/search_code --chunk_id "utils.py:50-75:function:validate_email"

# Use chunk_id from previous search results
# Step 1: Semantic search returns chunk_id in results
/search_code "authentication functions"
# Result includes: "chunk_id": "auth.py:15-42:function:login"

# Step 2: Direct lookup for unambiguous retrieval
/search_code --chunk_id "auth.py:15-42:function:login"
```

**Benefits**:

- **O(1) retrieval**: No semantic search overhead
- **Unambiguous**: Exact symbol match, no ranking needed
- **Tool chaining**: Use chunk_id from search → find_connections → read file
- **AI-suggested**: System messages guide you to use chunk_id when available

---

## Dependency Analysis Examples (Phase 1.3)

**Tool**: `find_connections` - Multi-hop dependency graph analysis

**Purpose**: Understand code impact before refactoring/modification.

**Accuracy**: ~90% for Python method calls with call graph resolution:

- Phase 1: Self/super calls (v0.5.12)
- Phase 2: Type annotations (v0.5.13)
- Phase 3: Assignment tracking (v0.5.14)
- Phase 4: Import resolution (v0.5.15)

**Examples**:

```
# Analyze function dependencies
/find_connections "auth.py:15-42:function:login"

# Or search by symbol name (may be ambiguous)
/find_connections --symbol_name "authenticate_user"

# Control traversal depth (default: 3)
/find_connections "auth.py:15-42:function:login" --max_depth 5
```

**Output Includes**:

- **Direct callers**: Functions that call this symbol
- **Indirect callers**: Multi-hop call chains (depth 1-N)
- **Similar code**: Semantically related implementations
- **Impact severity**: Low/Medium/High based on caller count
- **Dependency graph**: Visual representation (Mermaid format)

**Example Output**:

```json
{
  "symbol": "authenticate_user",
  "chunk_id": "auth.py:15-42:function:login",
  "direct_callers": [
    {"chunk_id": "api.py:100-120:function:login_endpoint", "name": "login_endpoint"}
  ],
  "indirect_callers": {
    "depth_2": [
      {"chunk_id": "routes.py:50-70:function:auth_route", "name": "auth_route"}
    ]
  },
  "similar_code": [
    {"chunk_id": "oauth.py:30-55:function:oauth_login", "similarity": 0.87}
  ],
  "impact_summary": {
    "direct_callers": 2,
    "total_connected": 5,
    "severity": "Medium",
    "recommendation": "Review callers before modification"
  },
  "dependency_graph": "graph TD\n  authenticate_user --> login_endpoint\n  ..."
}
```

**Use Cases**:

- **Before refactoring**: Check what code depends on target function
- **Impact assessment**: Understand blast radius of breaking changes
- **Code navigation**: Discover related functionality
- **Documentation**: Generate dependency diagrams

**System Message Integration**: Results include AI guidance on next steps (e.g., "Consider reading api.py to review direct caller implementation").

---

### Graph-Based Relationships (v0.5.6+)

**Feature**: `find_connections` now includes detailed relationship analysis for inheritance, type usage, and imports.

⚠️ **Re-indexing required**: Projects indexed before v0.5.6 need re-indexing for Phase 3 relationships to populate.

**Additional Output Fields**:

| Field | Description | Output Format |
|-------|-------------|---------------|
| `parent_classes` | Classes this class inherits from | Name-only (may include chunk_id if resolved) |
| `child_classes` | Classes that inherit from this class | Full chunk details |
| `uses_types` | Types used in this function/method | Name-only (type names) |
| `used_as_type_in` | Functions/methods that use this as a type | Full chunk details |
| `imports` | Modules/symbols imported by this code | Name-only (module paths) |
| `imported_by` | Code that imports this symbol | Full chunk details |

**Forward Relationships** (this chunk is the source):

```json
{
  "parent_classes": [
    {
      "target_name": "BaseModel",
      "relationship_type": "inherits",
      "line": 10,
      "confidence": 1.0,
      "note": "Type resolution not implemented - showing name only"
    }
  ],
  "uses_types": [
    {
      "target_name": "User",
      "relationship_type": "uses_type",
      "line": 15,
      "confidence": 1.0,
      "metadata": {"annotation_location": "parameter"}
    },
    {
      "target_name": "int",
      "relationship_type": "uses_type",
      "line": 15,
      "confidence": 1.0,
      "metadata": {"annotation_location": "return"}
    }
  ],
  "imports": [
    {
      "target_name": "typing.List",
      "relationship_type": "imports",
      "line": 1,
      "confidence": 1.0,
      "metadata": {"import_type": "from"}
    }
  ]
}
```

**Reverse Relationships** (this chunk is the target):

```json
{
  "child_classes": [
    {
      "chunk_id": "models.py:40-60:class:DerivedModel",
      "file": "models.py",
      "lines": "40-60",
      "kind": "class",
      "source_name": "DerivedModel",
      "relationship_type": "inherits",
      "line": 40,
      "confidence": 1.0
    }
  ],
  "used_as_type_in": [
    {
      "chunk_id": "service.py:10-20:function:process_user",
      "file": "service.py",
      "lines": "10-20",
      "kind": "function",
      "source_name": "process_user",
      "relationship_type": "uses_type",
      "line": 10,
      "confidence": 1.0
    }
  ],
  "imported_by": [
    {
      "chunk_id": "main.py:1-50:function:main",
      "file": "main.py",
      "lines": "1-50",
      "kind": "function",
      "source_name": "main",
      "relationship_type": "imports",
      "line": 1,
      "confidence": 1.0
    }
  ]
}
```

**Known Limitations**:

1. **Forward relationships** (parent_classes, uses_types, imports):
   - Return **type/module names only**, not full chunk_ids
   - Cannot provide file location or line details for external types (stdlib, builtins)
   - Example: `"int"`, `"User"`, `"typing.List"` are names, not resolvable symbols

2. **Type resolution**:
   - If a type is defined in the project, we show the name but cannot currently resolve it to the defining chunk_id
   - Future enhancement: TypeResolver will map names → chunk_ids for in-project symbols

3. **External dependencies**:
   - Standard library imports (`os`, `sys`) and builtins (`int`, `str`) are tracked but not resolvable
   - Shown with relationship type but no file/chunk information

4. **Graceful degradation**:
   - If source chunk lookup fails, partial info returned with `"note"` field explaining limitation
   - Example: `{"source_chunk_id": "...", "note": "Source chunk not found in index"}`

**Best Practices**:

- ✅ Use `chunk_id` parameter for unambiguous lookup (preferred)
- ✅ Check both forward and reverse relationships for complete picture
- ✅ For forward relationships, expect name-only output (this is by design)
- ✅ For reverse relationships, expect full chunk details (file, lines, kind)
- ⚠️ Be aware that external types (stdlib, builtins) won't have chunk_ids

---

### Call Graph Resolution (v0.5.12+)

**Feature**: Improved method call resolution for accurate dependency tracking.

**Problem Solved**: Before v0.5.12, calls like `self.method()` or `obj.method()` couldn't be traced to their actual definitions, causing false positives and missed connections in `find_connections`.

**Resolution Features**:

| Version | Feature | Accuracy |
|---------|---------|----------|
| v0.5.12 | Qualified chunk_ids + self/super resolution | ~70% |
| v0.5.13 | + Type annotation resolution | ~80% |
| v0.5.14 | + Assignment tracking | ~85-90% |
| v0.5.15 | + Import resolution | ~90% |

**Qualified Chunk IDs for Methods**:

Methods are now stored with their class context:

```python
class UserService:
    def get_user(self, id):  # chunk_id: "service.py:5-10:method:UserService.get_user"
        pass

class AdminService:
    def get_user(self, id):  # chunk_id: "service.py:15-20:method:AdminService.get_user"
        pass
```

**Self/Super Resolution**:

```python
class DataProcessor:
    def process(self):
        self.validate()     # Resolves to "DataProcessor.validate"
        super().cleanup()   # Resolves to "BaseProcessor.cleanup"
```

**Type Annotation Resolution** (v0.5.13):

```python
def process_order(order: Order, payment: PaymentGateway):
    order.validate()           # Resolves to "Order.validate"
    payment.charge(amount)     # Resolves to "PaymentGateway.charge"
```

**Example - Finding Method Callers**:

```bash
# Find all callers of a specific method (qualified name)
/find_connections "service.py:5-10:method:UserService.get_user"

# Output now shows callers through typed parameters:
# - api/handlers.py:25 process_request(svc: UserService) → svc.get_user()
# - tests/test_user.py:10 test via self.service.get_user()
```

**Requirements**:

- **Re-indexing required**: Projects indexed before v0.5.12 need re-indexing
- **Python only**: Type resolution currently Python-specific
- See `docs/ADVANCED_FEATURES_GUIDE.md#call-graph-resolution-v0512` for full details

---

## AI Guidance Messages (Phase 1.2)

**Feature**: Context-aware tool chaining suggestions automatically added to MCP responses.

**How It Works**:

- All MCP tools return optional `system_message` field
- Contains AI-readable guidance for intelligent tool chaining
- Non-intrusive (separate from main results)
- Tool-specific recommendations

**Example - search_code() with chunk_id available**:

```json
{
  "results": [...],
  "system_message": "💡 TIP: Use chunk_id 'auth.py:15-42:function:login' with find_connections() to analyze dependencies, or with search_code(chunk_id=...) for O(1) direct lookup."
}
```

**Example - find_connections() with high impact**:

```json
{
  "direct_callers": [...],
  "impact_summary": {"severity": "High"},
  "system_message": "⚠️ HIGH IMPACT: This function has 8 direct callers. Consider: 1) Review all callers before modification 2) Use search_code(chunk_id=...) to read each caller 3) Plan backward-compatible changes"
}
```

**Example - index_directory() completion**:

```json
{
  "success": true,
  "chunks_added": 1199,
  "system_message": "✅ Indexing complete! Try: search_code('your query') to find code, or find_connections(chunk_id) to analyze dependencies."
}
```

**Benefits**:

- **Intelligent workflows**: AI learns optimal tool sequences
- **Reduced user friction**: Suggestions appear automatically
- **Context-aware**: Messages adapt to result content
- **Non-intrusive**: Doesn't pollute main response data

**Tool Coverage**:

- `search_code`: Suggests chunk_id usage when available
- `find_connections`: Impact severity warnings + next steps
- `index_directory`: Post-indexing workflow suggestions
- `find_similar_code`: Chunk chaining recommendations

---

## Multi-Model Batch Indexing

**Feature**: Automatically index projects with all models in the pool (Qwen3, BGE-M3, CodeRankEmbed)

**Status**: ✅ **Production-Ready** (auto-enabled when `CLAUDE_MULTI_MODEL_ENABLED=true`)

### How It Works

When multi-model mode is enabled, `index_directory` automatically indexes with **all models in the pool** sequentially:

1. **Qwen3-0.6B** (1024d) - Logic specialist: action-oriented queries and algorithms
2. **BGE-Code-v1** (1536d) - Semantic specialist: workflow and architectural reasoning

### Parameters

- `directory_path` (string, required): Absolute path to project root
- `project_name` (string, optional): Custom name (defaults to directory name)
- `incremental` (boolean, default: true): Use incremental indexing if snapshot exists
- `multi_model` (boolean, default: auto): Index for all models
  - `null` (default): Auto-detect from `CLAUDE_MULTI_MODEL_ENABLED`
  - `true`: Force multi-model indexing (all models in the pool)
  - `false`: Force single-model indexing (current model only)

### Usage Examples

**Automatic Multi-Model** (default when multi-model enabled):

```bash
/index_directory "C:\Projects\MyProject"
# Indexes with all models in the pool automatically
```

**Explicit Control**:

```bash
# Force multi-model (even if disabled)
/index_directory "C:\Projects\MyProject" --multi_model true

# Force single-model (even if enabled)
/index_directory "C:\Projects\MyProject" --multi_model false
```

### Response Format

**Multi-Model Response**:

```json
{
  "success": true,
  "multi_model": true,
  "project": "C:\\Projects\\MyProject",
  "models_indexed": 3,
  "results": [
    {
      "model": "BAAI/bge-m3",
      "model_key": "bge_m3",
      "dimension": 1024,
      "files_added": 40,
      "files_modified": 14,
      "files_removed": 8,
      "chunks_added": 1199,
      "time_taken": 28.5
    },
    // ... results for other models
  ],
  "total_time": 82.3,
  "total_files_added": 120,
  "total_chunks_added": 3597,
  "mode": "incremental"
}
```

**Single-Model Response**:

```json
{
  "success": true,
  "multi_model": false,
  "project": "C:\\Projects\\MyProject",
  "files_added": 40,
  "files_modified": 14,
  "files_removed": 8,
  "chunks_added": 1199,
  "time_taken": 28.5,
  "mode": "incremental"
}
```

### Performance

- **Sequential Indexing**: 3x time (e.g., 30s → 90s)
- **Acceptable**: Indexing is infrequent (one-time per project + updates)
- **Future Optimization**: Parallel chunking planned (2x speedup)

### Benefits

✅ **Single operation** updates all models
✅ **Optimal search quality** across all query types
✅ **Per-model isolation** maintained
✅ **Smart defaults** (auto-enable with multi-model mode)

---

## Critical Rules

- ✅ **ALWAYS** use `search_code()` for exploration/understanding
- ✅ **ALWAYS** index before searching: `index_directory(path)`
- ✅ **USE** `chunk_id` for O(1) lookups when available (follow system messages)
- ✅ **USE** `find_connections()` before modifying code (impact analysis)
- ❌ **NEVER** read files without searching first
- ❌ **NEVER** use `Glob()` or `grep` for code exploration

**Every file read without search wastes 1,000+ tokens**

---

## Supported Features

- **Languages**: Python, JavaScript, TypeScript, Go, Rust, C, C++, C#, GLSL (9 languages, 19 extensions)
- **Parsing**: AST (Python) + Tree-sitter (all others)
- **Search Modes**: Semantic, BM25, Hybrid
- **Chunking**: Functions, classes, methods, interfaces, enums, modules, etc.
- **Token Reduction**: 40-45% via semantic chunking

---

## Quick Setup (Windows)

```powershell
# 1. Install system
.\install-windows.bat

# 2. Configure Claude Code
.\scripts\batch\manual_configure.bat

# 3. Start using
/index_directory "C:\Projects\MyProject"
/search_code "your query here"
```

---

## Cross-Platform Notes

- **Windows**: Batch scripts + PowerShell automation
- **Linux/Mac**: Use equivalent shell scripts
- **Working Directory**: `mcp_server_wrapper.bat` ensures correct context
- **Path Handling**: Automatic Windows/Unix path resolution

---

## Integration Checklist

- [ ] MCP server installed and configured
- [ ] Claude Code config updated (`configure_claude_code.ps1`)
- [ ] Hugging Face authentication completed
- [ ] Project indexed with `index_directory()`
- [ ] Search mode configured (hybrid recommended)
- [ ] Embedding model selected (BGE-M3 recommended for accuracy)

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Model not found" | Run `scripts\powershell\hf_auth.ps1` |
| "Index stale" | Use `auto_reindex=True` (default) |
| "Slow searches" | Check `/get_memory_status`, run `/cleanup_resources` |
| "Wrong results" | Try different search mode: `/configure_search_mode` |
| "Dimension mismatch" | Re-index after model switch |

---

## Token Efficiency Example

**Traditional approach** (reading 3 files):

- auth.py (2,000 tokens)
- login.py (1,800 tokens)
- session.py (1,800 tokens)
- **Total**: 5,600 tokens

**Semantic search approach**:

- Query: "authentication login functions"
- Results: 3 relevant chunks (400 tokens)
- **Total**: 400 tokens

**Savings**: 63% token reduction + 2-3x speed increase

---

## End of Modular Reference

This reference is maintained in: `docs/MCP_TOOLS_REFERENCE.md`

For full documentation, see project `CLAUDE.md` and `README.md`
