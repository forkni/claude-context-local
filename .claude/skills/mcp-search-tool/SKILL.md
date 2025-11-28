---
name: mcp-search-tool
description: Ensures proper MCP semantic search workflow with automatic project switching and optimal search configuration for maximum token efficiency and accurate results
---

# MCP Search Tool Skill

## Purpose

This skill ensures that all MCP semantic search operations follow the correct workflow for accurate, relevant results with maximum token efficiency (40-45% savings). It enforces project context validation before searches and applies optimal search configuration.

## When to Activate

This skill should **ALWAYS** be used when:

- Performing codebase exploration or understanding
- Searching for code patterns, functions, or implementations
- Analyzing code structure or relationships
- Finding similar code across the project
- Any task involving `search_code()` or related MCP tools

## Critical Workflow: Project Context Validation

**MANDATORY STEPS BEFORE ANY SEARCH:**

### Step 1: Check Indexed Projects

```bash
# List all available indexed projects
list_projects()
```

This shows all projects indexed in `C:\Users\Inter\.claude_code_search\projects\`.

### Step 2: Compare with Current Working Directory

Compare the current working directory with available indexed projects:

- **Current Directory**: Get from environment (e.g., `D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13`)
- **Available Projects**: Check output from `list_projects()`

### Step 3: Switch to Correct Project (If Needed)

If the current project doesn't match the working directory:

```bash
switch_project("D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13")
```

**CRITICAL**: Only after successful project switch can you proceed with searches.

### Step 4: Verify Index Status

Before searching, check that the index is fresh and ready:

```bash
get_index_status()
```

This confirms:

- Index exists and is loaded
- Total chunks available
- Model dimension (768d or 1024d)
- Last index time

### Step 5: Perform Search

Now you can safely execute searches knowing results will be relevant:

```bash
search_code("your natural language query", k=5, search_mode="hybrid")
```

## Complete MCP Tool Reference (15 Tools)

### 🔴 Essential Tools (Use First)

#### 1. `search_code(query, k=5, search_mode="hybrid", file_pattern=None, chunk_type=None, include_context=True, auto_reindex=True, max_age_minutes=5)`

**Purpose**: Find code with natural language queries (40-45% token savings vs file reading)

**Parameters**:

- `query` (required): Natural language description of what you're looking for
- `k` (default: 5): Number of results to return
- `search_mode` (default: "hybrid"): Search method - "hybrid", "semantic", "bm25", or "auto"
- `file_pattern` (optional): Filter by filename/path pattern (e.g., "Scripts/", "wrapper_td")
- `chunk_type` (optional): Filter by code structure - "function", "class", "method", or None for all
- `include_context` (default: True): Include similar chunks and relationships
- `auto_reindex` (default: True): Automatically reindex if index is stale
- `max_age_minutes` (default: 5): Maximum age of index before auto-reindex

**Examples**:

```bash
# General search
search_code("StreamDiffusionExt callback functions")

# Filtered search
search_code("OSC message handlers", file_pattern="Scripts/", chunk_type="function")

# Broader search with more results
search_code("token merging implementation", k=10)
```

**Performance** (Empirically Validated):

- **Hybrid mode**: 68-105ms average (recommended)
- **Semantic mode**: 62-94ms average
- **BM25 mode**: 3-8ms average (fastest for exact symbols)
- **Auto mode**: 52-57ms average

#### 2. `index_directory(directory_path, project_name=None, file_patterns=None, incremental=True)`

**Purpose**: Index a project for semantic search (one-time setup)

**Parameters**:

- `directory_path` (required): Absolute path to project root
- `project_name` (optional): Name for organization (defaults to directory name)
- `file_patterns` (optional): File patterns to include (default: all supported extensions)
- `incremental` (default: True): Use incremental indexing if snapshot exists

**Performance**:

- **Full index**: ~30-60s for typical projects
- **Incremental**: 10-50x faster (only processes changed files)
- **Batch removal**: 600-1000x faster for large-scale deletions

**Example**:

```bash
index_directory("D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13")
```

### 🟡 Project Management Tools

#### 3. `list_projects()`

**Purpose**: Show all indexed projects with metadata

**Returns**: JSON with list of projects, paths, and index information

#### 4. `switch_project(project_path)`

**Purpose**: Switch to a different indexed project for searching

**Parameters**:

- `project_path` (required): Path to the project directory

**Example**:

```bash
switch_project("D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13")
```

#### 5. `get_index_status()`

**Purpose**: Check index health and statistics

**Returns**: JSON with index statistics, chunk count, model info, memory usage

#### 6. `clear_index()`

**Purpose**: Delete the entire search index for the current project

**Warning**: Deletes ALL dimension indices (768d, 1024d) and Merkle snapshots. Requires full re-indexing afterward.

### 🟢 Search Configuration Tools

#### 7. `configure_search_mode(search_mode="hybrid", bm25_weight=0.4, dense_weight=0.6, enable_parallel=True)`

**Purpose**: Configure search mode and hybrid search parameters

**Parameters**:

- `search_mode`: "hybrid" (default), "semantic", "bm25", or "auto"
- `bm25_weight`: Weight for BM25 sparse search (0.0 to 1.0)
- `dense_weight`: Weight for dense vector search (0.0 to 1.0)
- `enable_parallel`: Enable parallel BM25 + Dense search execution

**Optimal Settings** (Empirically Validated):

- **General use**: hybrid mode, 0.4 BM25 / 0.6 Dense
- **Code structure queries**: hybrid mode, 0.3 BM25 / 0.7 Dense
- **Error/log analysis**: hybrid mode, 0.7 BM25 / 0.3 Dense

**Example**:

```bash
configure_search_mode("hybrid", 0.4, 0.6, true)
```

#### 8. `get_search_config_status()`

**Purpose**: View current search configuration and available settings

**Returns**: JSON with current mode, weights, features enabled

#### 9. `configure_query_routing(enable_multi_model=None, default_model=None, confidence_threshold=None)`

**Purpose**: Configure multi-model query routing behavior

**Parameters**:

- `enable_multi_model` (optional): Enable/disable multi-model mode
- `default_model` (optional): Set default model ("qwen3", "bge_m3", "coderankembed")
- `confidence_threshold` (optional): Minimum confidence for routing (0.0-1.0, default: 0.3)

**Example**:

```bash
configure_query_routing(enable_multi_model=True, default_model="qwen3", confidence_threshold=0.4)
```

### 🔵 Advanced Tools

#### 10. `find_similar_code(chunk_id, k=5)`

**Purpose**: Find code chunks functionally similar to a reference chunk

**Parameters**:

- `chunk_id` (required): ID from search_code results (format: "file:lines:type:name")
- `k` (default: 5): Number of similar chunks to return

**Workflow**:

1. First use `search_code()` to find a reference chunk
2. Use the `chunk_id` from results with this tool
3. Get ranked list of functionally similar code

**Example**:

```bash
# First find a reference
search_code("authentication handler")
# Then find similar code using the chunk_id from results
find_similar_code("src/auth.py:10-50:function:authenticate", k=5)
```

#### 11. `list_embedding_models()`

**Purpose**: List all available embedding models with specifications

**Returns**: JSON with model info including dimensions, context length, descriptions

**Available Models**:

- **EmbeddingGemma-300m**: 768d, 4-8GB VRAM, fast
- **BGE-M3**: 1024d, 8-16GB VRAM, +3-6% accuracy

#### 12. `switch_embedding_model(model_name)`

**Purpose**: Switch to a different embedding model without deleting indices

**Parameters**:

- `model_name` (required): Model identifier (e.g., "BAAI/bge-m3", "google/embeddinggemma-300m")

**Performance**: Instant switching (<150ms) if model was previously used (per-model indices)

**Example**:

```bash
# Switch to BGE-M3 for better accuracy
switch_embedding_model("BAAI/bge-m3")

# Switch back to Gemma for speed
switch_embedding_model("google/embeddinggemma-300m")
```

### 🟣 Memory Management Tools

#### 13. `get_memory_status()`

**Purpose**: Get current memory usage for index and system

**Returns**: JSON with RAM/VRAM usage, GPU status, available memory

#### 14. `cleanup_resources()`

**Purpose**: Manually cleanup all resources to free memory

**Use When**:

- Switching between large projects
- Memory running low
- GPU memory needs to be freed

#### 15. `find_connections(chunk_id=None, symbol_name=None, max_depth=3, exclude_dirs=None)`

**Purpose**: Find all code connections to a given symbol for dependency and impact analysis

**Parameters**:

- `chunk_id` (optional): Direct chunk_id from search results (preferred for precise lookup)
- `symbol_name` (optional): Symbol name to find (may be ambiguous, use chunk_id when possible)
- `max_depth` (default: 3): Maximum depth for dependency traversal (1-5, affects indirect callers)
- `exclude_dirs` (optional): Directories to exclude from symbol resolution and caller lookup (e.g., ["tests/"])

**Returns**: Structured report with direct callers, indirect callers, similar code, and dependency graph

**Use When**:

- Before refactoring or modifying code
- Understanding code relationships and dependencies
- Finding all code connected to a symbol
- Impact assessment for breaking changes

**Example**:

```bash
# Using chunk_id (preferred)
find_connections(chunk_id="auth.py:10-50:function:login")

# Using symbol name
find_connections(symbol_name="User", exclude_dirs=["tests/"])

# With custom depth
find_connections(chunk_id="auth.py:10-50:function:login", max_depth=5)
```

## Search Modes Explained

### Hybrid Mode (Recommended Default)

**Best For**: General use, balanced accuracy and speed

**How It Works**: Combines BM25 sparse search (exact text matches) with dense vector search (semantic similarity) using Reciprocal Rank Fusion (RRF) reranking

**Performance**: 68-105ms average
**Weights**: 0.4 BM25 / 0.6 Dense (optimal, empirically validated)

### Semantic Mode

**Best For**: Conceptual queries, code similarity, natural language

**How It Works**: Dense vector search only using embedding similarity

**Performance**: 62-94ms average

**Example Queries**:

- "error handling patterns"
- "authentication implementations"
- "database connection setup"

### BM25 Mode

**Best For**: Exact text matches, specific error messages, code symbols

**How It Works**: Text-based sparse search with Snowball stemming

**Performance**: 3-8ms average (fastest)

**Example Queries**:

- "StreamDiffusionExt" (exact class name)
- "def process_frame" (exact function signature)
- "AttributeError: 'NoneType'" (exact error message)

### Auto Mode

**Best For**: Mixed query types, let system decide

**How It Works**: Intelligently selects optimal mode based on query characteristics

**Performance**: 52-57ms average

## Advanced Features (Enabled by Default)

### Multi-Hop Search

**Purpose**: Discover interconnected code relationships through iterative semantic search

**How It Works**:

1. **Hop 1**: Find chunks matching your query (hybrid search with k×2 results)
2. **Hop 2**: For each top result, find semantically similar chunks (k×0.3 per result)
3. **Re-ranking**: Sort all discovered chunks by query relevance

**Benefits** (Empirically Validated):

- **93.3% of queries benefit** from multi-hop
- **Average 3.2 unique chunks** discovered per query
- **40-60% top result changes** for complex queries
- **Example**: "configuration management" → finds primary class + env vars + validation + persistence

**Performance**: +25-35ms overhead (negligible for 93% benefit rate)

**Status**: **Enabled by default** with optimal settings (2 hops, 0.3 expansion)

### BM25 Snowball Stemming

**Purpose**: Normalize word forms to improve recall

**How It Works**: Matches different variations of the same word

- "indexing", "indexed", "indexes", "index" → all match each other
- "searching", "search", "searches", "searched" → all match
- "authentication", "authenticator", "authenticate" → all match

**Benefits** (Empirically Validated):

- **93.3% of queries benefit**
- **3.33 average unique discoveries** per query
- **0.47ms overhead** (negligible)
- **11% smaller indices** due to vocabulary consolidation

**Status**: **Enabled by default**

## Best Practices

### 1. Always Use Search-First Protocol

❌ **WRONG**: Read files randomly → Waste 5,000+ tokens
✅ **CORRECT**: `index_directory()` → `search_code()` → `Read()` for targeted edits → **40-45% token savings**

### 2. Project Context Validation

**Before any search**:

1. `list_projects()` - Check available projects
2. Compare with current working directory
3. `switch_project()` if needed
4. `get_index_status()` - Verify index is ready
5. `search_code()` - Now get relevant results

### 3. Use Appropriate Search Modes

- **Code exploration**: hybrid mode (default)
- **Conceptual queries**: semantic mode
- **Exact symbol search**: BM25 mode
- **Mixed queries**: auto mode

### 4. Leverage Multi-Hop for Complex Queries

Multi-hop is enabled by default and discovers interconnected code:

- Configuration systems → env vars, validation, persistence
- Pipeline implementations → data flow, transformations, outputs
- Authentication → login, session, permissions, tokens

### 5. Filter Searches for Precision

Use `file_pattern` and `chunk_type` to narrow results:

```bash
# Only search in Scripts folder for functions
search_code("callback handlers", file_pattern="Scripts/", chunk_type="function")

# Only search for classes
search_code("extension classes", chunk_type="class")
```

### 6. Optimize Result Count

- **k=5**: Default, balanced
- **k=10-15**: Complex queries needing more context
- **k=3**: Simple, focused queries

### 7. Monitor Performance

```bash
get_memory_status()     # Check RAM/GPU usage
get_index_status()      # Check index health
get_search_config_status()  # View current settings
```

### 8. Cleanup When Needed

```bash
cleanup_resources()     # Free memory between projects
clear_index()          # Full reset (requires re-indexing)
```

## Performance Metrics

### Token Efficiency

- **Traditional file reading**: ~5,600 tokens
- **Semantic search**: ~400 tokens
- **Savings**: **93% reduction** (40-45% in practice)
- **Speed**: **5-10x faster** discovery

### Search Performance (Validated)

- **Hybrid**: 68-105ms (recommended)
- **Semantic**: 62-94ms
- **BM25**: 3-8ms (fastest)
- **Auto**: 52-57ms

### Index Performance

- **Full index**: 30-60s typical projects
- **Incremental**: 10-50x faster (only changed files)
- **Batch removal**: 600-1000x faster (large deletions)

### Quality Metrics (Validated)

- **Precision**: 44.4%
- **F1-score**: 46.7%
- **MRR**: 100%
- **Success rate**: 100% (256/256 test queries)

## Troubleshooting

### Issue: Search returns no results

**Solution**:

1. Check project context: `list_projects()` and `switch_project()` if needed
2. Verify index exists: `get_index_status()`
3. Re-index if stale: `index_directory(project_path)`

### Issue: Results not relevant

**Solution**:

1. Try different search mode (hybrid → semantic → BM25)
2. Adjust weights: `configure_search_mode("hybrid", 0.7, 0.3)` for more exact matching
3. Use filters: `file_pattern` or `chunk_type`
4. Increase result count: `k=10` or `k=15`

### Issue: Search too slow

**Solution**:

1. Use BM25 mode for exact symbol searches (3-8ms)
2. Check GPU memory: `get_memory_status()`
3. Cleanup resources: `cleanup_resources()`
4. Reduce result count: `k=3`

### Issue: Memory issues

**Solution**:

1. Monitor: `get_memory_status()`
2. Cleanup: `cleanup_resources()`
3. Switch to smaller model: `switch_embedding_model("google/embeddinggemma-300m")`

## Examples for TouchDesigner Projects

### Example 1: Finding Callback Functions

```bash
# 1. Verify project context
list_projects()
switch_project("D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13")

# 2. Search for callbacks
search_code("StreamDiffusionExt callback functions", file_pattern="Scripts/", chunk_type="function", k=10)
```

### Example 2: Understanding Pipeline Components

```bash
# 1. Verify context
get_index_status()

# 2. Use semantic search for conceptual understanding
configure_search_mode("semantic", 0.3, 0.7)
search_code("pipeline initialization and setup", k=15)
```

### Example 3: Finding Specific Class Implementation

```bash
# 1. Use BM25 for exact class name
configure_search_mode("bm25", 0.8, 0.2)
search_code("StreamDiffusionExt class", chunk_type="class")

# 2. Find similar implementations
find_similar_code("Scripts/streamdiffusionTD__Text__main_sdtd__td.py:10-100:class:StreamDiffusionExt", k=5)
```

### Example 4: Analyzing Token Merging

```bash
# 1. Use hybrid for balanced search
configure_search_mode("hybrid", 0.4, 0.6)
search_code("tomesd token merging spatial algorithms", k=10)

# 2. Get multi-hop context (automatic)
# Multi-hop will discover: implementation, configuration, integration points
```

### Example 5: Debugging Performance Issues

```bash
# 1. Find performance-related code
search_code("performance optimization cook time", file_pattern="Scripts/", k=15)

# 2. Check memory usage
get_memory_status()
```

## Summary

This skill ensures that all MCP semantic search operations follow the optimal workflow:

1. ✅ **Validate project context** before every search
2. ✅ **Use search-first protocol** for 40-45% token savings
3. ✅ **Apply optimal search modes** for accurate results
4. ✅ **Leverage multi-hop and stemming** for comprehensive discovery
5. ✅ **Monitor and optimize** for best performance

**Result**: Relevant, accurate code search with maximum efficiency and minimal token usage.
