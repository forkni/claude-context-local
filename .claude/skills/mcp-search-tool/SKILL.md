---
name: mcp-search-tool
description: MCP semantic code search. CRITICAL 2-STEP: (1) search_code()→get chunk_id, (2) find_connections(chunk_id) for callers/deps/flow. USE CASES: codebase exploration, code patterns, relationships, impact analysis. ⚠️ NEVER Grep for caller/dependency discovery (50-60% token waste). 63% savings (validated).
---

# MCP Search Tool Skill

## Purpose

This skill ensures that all MCP semantic search operations follow the correct workflow for accurate, relevant results with maximum token efficiency (40-45% savings). It enforces project context validation before searches and applies optimal search configuration.

## 🎯 QUICK START: Which Tool to Use?

**BEFORE searching, identify your query type:**

```
What are you trying to do?
│
├─ "Find callers of X" ──────────────► find_connections(chunk_id)
├─ "What depends on X" ──────────────► find_connections(chunk_id)
├─ "Trace flow from X to Y" ─────────► find_connections(chunk_id, max_depth=5)
├─ "Find similar code to X" ─────────► find_similar_code(chunk_id)
│
├─ "Find class/function definition" ─► search_code(query, chunk_type)
├─ "Find exact API call pattern" ────► search_code(query, search_mode="bm25")
├─ "Understand concept/feature" ─────► search_code(query) [hybrid mode]
├─ "Find related code via graph" ────► search_code(..., ego_graph_enabled=true)
│
└─ "Validate line numbers only" ─────► Grep (LAST RESORT)
```

**⚠️ CRITICAL**: For ANY query about callers, dependencies, or code flow:

1. First: `search_code()` to get chunk_id
2. Then: `find_connections(chunk_id)` for relationships

**❌ NEVER use Grep for relationship discovery**

---

## ⛔ Common Mistakes (AVOID)

| ❌ Wrong Approach | ✅ Correct Approach | Savings |
|------------------|---------------------|---------|
| `Grep("\.function\(")` for callers | `find_connections(chunk_id)` | 60% fewer tokens |
| Multiple Reads to trace flow | `find_connections(max_depth=5)` | 50% fewer tokens |
| Manual import tracing | `find_connections(symbol_name)` | 50% fewer tokens |

---

## 📚 Quick Function Index

### All 18 MCP Tools at a Glance

| Tool | Category | Purpose | Key Parameters | Jump To |
|------|----------|---------|----------------|---------|
| **search_code** | 🔴 Essential | Find code with NL query or chunk_id lookup | `query`, `chunk_id`, `chunk_type`, `include_dirs`, `exclude_dirs` | [Details](#1-search_codequery-or-chunk_id-k5-search_modehybrid-model_keynone-use_routingtrue-file_patternnone-include_dirsnone-exclude_dirsnone-chunk_typenone-include_contexttrue-auto_reindextrue-max_age_minutes5) |
| **find_connections** | 🔴 Essential | Find callers, dependencies, flow (graph analysis) | `chunk_id`, `symbol_name`, `max_depth`, `exclude_dirs` | [Details](#3-find_connectionschunk_idnone-symbol_namenone-max_depth3-exclude_dirsnone) |
| **index_directory** | 🔴 Setup | Index project for search (one-time) | `directory_path`, `incremental`, `multi_model`, `include_dirs`, `exclude_dirs` | [Details](#2-index_directorydirectory_path-project_namenone-incrementaltrue-multi_modelnone-include_dirsnone-exclude_dirsnone) |
| list_projects | Management | Show all indexed projects | *(none)* | [Details](#4-list_projects) |
| switch_project | Management | Change active project | `project_path` | [Details](#5-switch_projectproject_path) |
| get_index_status | Status | Check index health | *(none)* | [Details](#6-get_index_status) |
| clear_index | Reset | Delete current index | *(none)* | [Details](#7-clear_index) |
| delete_project | Reset | Safely delete indexed project | `project_path`, `force` | [Details](#8-delete_projectproject_path-forcefalse) |
| configure_search_mode | Config | Set search mode & weights | `search_mode`, `bm25_weight`, `dense_weight` | [Details](#9-configure_search_modesearch_modehybrid-bm25_weight04-dense_weight06-enable_paralleltrue) |
| get_search_config_status | Config | View current config | *(none)* | [Details](#10-get_search_config_status) |
| configure_query_routing | Config | Multi-model routing settings | `enable_multi_model`, `default_model`, `confidence_threshold` | [Details](#11-configure_query_routingenable_multi_modelnone-default_modelnone-confidence_thresholdnone) |
| find_similar_code | Secondary | Find functionally similar code | `chunk_id`, `k` | [Details](#12-find_similar_codechunk_id-k5) |
| configure_reranking | Config | Neural reranking settings | `enabled`, `model_name`, `top_k_candidates` | [Details](#13-configure_rerankingenablednone-model_namenone-top_k_candidatesnone) |
| configure_chunking | Config | Configure code chunking settings | `enable_greedy_merge`, `min_chunk_tokens`, `max_merged_tokens`, `token_estimation`, `enable_large_node_splitting`, `max_chunk_lines` | [Details](#18-configure_chunkingenable_greedy_mergenone-min_chunk_tokensnone-max_merged_tokensnone-token_estimationnone-enable_large_node_splittingnone-max_chunk_linesnone) |
| list_embedding_models | Model | Show available models | *(none)* | [Details](#14-list_embedding_models) |
| switch_embedding_model | Model | Change embedding model | `model_name` | [Details](#15-switch_embedding_modelmodel_name) |
| get_memory_status | Monitor | Check RAM/VRAM usage | *(none)* | [Details](#16-get_memory_status) |
| cleanup_resources | Cleanup | Free memory/caches | *(none)* | [Details](#17-cleanup_resources) |

### Usage Patterns by Task

| Task Type | Primary Tool | Secondary Tool | Pattern |
|-----------|--------------|----------------|---------|
| **Find code by concept** | `search_code(query)` | - | Semantic search |
| **Find callers/dependencies** | `search_code()` → `find_connections(chunk_id)` | - | 2-step workflow |
| **Direct symbol lookup** | `search_code(chunk_id="...")` | - | O(1) lookup |
| **Impact assessment** | `find_connections(max_depth=5)` | - | Multi-hop graph |
| **Find similar patterns** | `search_code()` → `find_similar_code(chunk_id)` | - | Similarity search |
| **Find code + graph neighbors** | `search_code(ego_graph_enabled=True)` | - | Graph-enhanced search |
| **Match method, retrieve class** | `search_code(query, include_parent=True)` | - | Parent-child retrieval |
| **Setup new project** | `index_directory(path)` | `get_index_status()` | One-time indexing |
| **Switch projects** | `list_projects()` → `switch_project(path)` | - | Project management |
| **Memory cleanup** | `get_memory_status()` → `cleanup_resources()` | - | Resource management |

### Core Documentation References

| Document | Purpose | When to Consult |
|----------|---------|-----------------|
| [MCP_TOOLS_REFERENCE.md](docs/MCP_TOOLS_REFERENCE.md) | Complete tool reference (18 tools, all parameters) | Detailed parameter options, filter behaviors |
| [HYBRID_SEARCH_CONFIGURATION_GUIDE.md](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md) | Search modes, weights, multi-model routing | Tuning search quality, mode selection |
| [ADVANCED_FEATURES_GUIDE.md](docs/ADVANCED_FEATURES_GUIDE.md) | Multi-hop, graph search, call graph resolution | Understanding advanced features |

---

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

### Step 5: Construct Optimized Query

**Before searching, determine:**

1. **What type of code?**
   - Class → `chunk_type="class"`
   - Function → `chunk_type="function"`
   - Method → `chunk_type="method"`
   - Decorated → `chunk_type="decorated_definition"`

2. **Which module?** (if known)
   - `include_dirs=["module_name/"]`

3. **What to exclude?**
   - Always consider `exclude_dirs=["tests/"]` for implementation searches

**Construct query:**

```bash
search_code(
    "descriptive natural language query",
    chunk_type="<type>",          # Step 1 result
    include_dirs=["<module>/"],   # Step 2 result (optional)
    exclude_dirs=["tests/"],      # Step 3 result (usually)
    k=5                           # Increase if needed
)
```

## Query Construction Guide

### Question Type → Query + Filter Matrix

| Question Type | Query Pattern | Recommended Filters | Example |
|---------------|---------------|---------------------|---------|
| **Find class definition** | "[ClassName] class implementation" | `chunk_type="class"` | `search_code("CodeEmbedder class", chunk_type="class")` |
| **Find function** | "[function_name] function implementation" | `chunk_type="function"` | `search_code("handle_search_code function", chunk_type="function")` |
| **Find method in class** | "[ClassName] [method_name] method" | `chunk_type="method"` | `search_code("CodeIndexManager save_index method", chunk_type="method")` |
| **Find decorated function** | "[decorator_name] decorator handler" | `chunk_type="decorated_definition"` | `search_code("server.call_tool decorator", chunk_type="decorated_definition")` |
| **Find callers** | Use `find_connections(chunk_id)` | `exclude_dirs=["tests/"]` | `find_connections(chunk_id="...", exclude_dirs=["tests/"])` |
| **Find implementation in specific module** | "[concept] implementation" | `include_dirs=["module/"]` | `search_code("change detection", include_dirs=["merkle/"])` |

### Filter Selection Guide

**When to use `chunk_type`:**

- Looking for class definition → `chunk_type="class"`
- Looking for standalone function → `chunk_type="function"`
- Looking for method inside class → `chunk_type="method"`
- Looking for decorated handler → `chunk_type="decorated_definition"`
- Looking for module-level code → `chunk_type="module"`

**When to use `include_dirs`:**

- Know which module contains the code (e.g., `["embeddings/"]`, `["search/"]`)
- Want to exclude test files (use `exclude_dirs=["tests/"]` instead)
- Narrowing search to specific component

**⚠️ FILTER CAVEAT**: `include_dirs` and filters apply **POST-search**. Common pitfalls:

- **Generic query + strict filter = 0 results**
  - Example: `search_code("manager", include_dirs=["embeddings/"])` → 0 results (query too generic)
  - Fix: Make query more specific: `search_code("embedding model manager class", include_dirs=["embeddings/"])` ✅
- **OR**: Remove `include_dirs` filter and let semantic search find all matches first

**When to use `exclude_dirs`:**

- Getting too many test file results → `exclude_dirs=["tests/"]`
- Getting vendor/third-party noise → `exclude_dirs=["vendor/", "node_modules/"]`
- Want implementation, not examples → `exclude_dirs=["examples/", "docs/"]`

**When to use `file_pattern`:**

- Know partial filename → `file_pattern="indexer"` for files containing "indexer"
- Searching specific file type → `file_pattern=".py"` (redundant if using `type`)

## Iterative Search Refinement

### Pattern: "Narrow on Failure"

When first search returns irrelevant results (tests, scripts, examples):

**Step 1: Add `exclude_dirs` filter**

```python
# Before (returned test files)
search_code("EmbeddingManager class")

# After (exclude tests)
search_code("EmbeddingManager class", exclude_dirs=["tests/", "scripts/"])
```

**Step 2: Add `chunk_type` filter**

```python
# Still getting methods/functions, want class
search_code("EmbeddingManager class", exclude_dirs=["tests/"], chunk_type="class")
```

**Step 3: Add `include_dirs` if you know the module**

```python
# Know it's in embeddings module
search_code("embedding class", include_dirs=["embeddings/"], chunk_type="class")
```

### Pattern: "Widen on Zero Results"

When search returns 0 results:

**Step 1: Remove filters one at a time**

```python
# Too narrow - 0 results
search_code("embedding manager", include_dirs=["embeddings/"], chunk_type="class")

# Remove chunk_type - try broader
search_code("embedding manager", include_dirs=["embeddings/"])

# Remove include_dirs - try broadest
search_code("embedding manager class implementation")
```

**Step 2: Make query more specific (filters apply post-search)**

```python
# Generic query + filter = 0 results
search_code("manager", file_pattern="embed")  # Too generic

# Specific query + filter = results
search_code("embedding model manager class", file_pattern="embed")  # Better
```

## Tool Selection Guide

### When to Use Each Tool

| Task | Tool | Why |
|------|------|-----|
| Find where symbol is defined | `search_code(query, chunk_type)` | Semantic + type filter |
| Find what calls a function | `find_connections(chunk_id)` | Graph traversal, not search |
| Find similar implementations | `find_similar_code(chunk_id)` | Embedding similarity |
| Understand dependencies | `find_connections(chunk_id, max_depth=3)` | Multi-hop relationships |
| Find exact text match | `search_code(query, search_mode="bm25")` | Exact keyword matching |

### Anti-Patterns to Avoid

❌ **Don't use Grep for relationship queries**

```python
# Bad: Manual grep for callers
Grep(pattern="\\.chunk_file\\(")

# Good: Graph-based caller discovery
find_connections(chunk_id="chunking/multi_language_chunker.py:...:function:chunk_file")
```

❌ **Don't read entire file for one function**

```python
# Bad: Read 1000+ line file
Read(file_path="mcp_server/tool_handlers.py")

# Good: Use chunk_id for O(1) lookup
search_code(chunk_id="mcp_server/tool_handlers.py:763-919:function:handle_search_code")
```

❌ **Don't search without filters when you know the type**

```python
# Bad: Generic search, gets tests
search_code("EmbeddingManager")

# Good: Filtered search, gets implementation
search_code("EmbeddingManager", chunk_type="class", exclude_dirs=["tests/"])
```

## Complete MCP Tool Reference (15 Tools)

### 🔴 Essential Tools (Use First)

#### 1. `search_code(query OR chunk_id, k=5, search_mode="hybrid", model_key=None, use_routing=True, file_pattern=None, include_dirs=None, exclude_dirs=None, chunk_type=None, include_context=True, auto_reindex=True, max_age_minutes=5, ego_graph_enabled=False, ego_graph_k_hops=2, ego_graph_max_neighbors_per_hop=10, include_parent=False)`

**Purpose**: Find code with natural language queries OR direct symbol lookup (40-45% token savings vs file reading)

**Parameters**:

- `query` (optional): Natural language description of what you're looking for
- `chunk_id` (optional): Direct chunk ID for O(1) lookup (format: "file:lines:type:name")
- `k` (default: 5): Number of results to return
- `search_mode` (default: "hybrid"): Search method - "hybrid", "semantic", or "bm25"
- `model_key` (optional): Force specific model - "qwen3", "bge_m3", or "coderankembed"
- `use_routing` (default: True): Enable multi-model query routing
- `file_pattern` (optional): Filter by filename/path pattern (e.g., "auth", "models")
- `include_dirs` (optional): Only search in these directories (e.g., ["src/", "lib/"])
- `exclude_dirs` (optional): Exclude from search (e.g., ["tests/", "vendor/"])
- `chunk_type` (optional): Filter by code structure - "function", "class", "method", or None for all
- `include_context` (default: True): Include similar chunks and relationships
- `auto_reindex` (default: True): Automatically reindex if index is stale
- `max_age_minutes` (default: 5): Maximum age of index before auto-reindex
- `ego_graph_enabled` (default: False): Enable RepoGraph-style k-hop ego-graph expansion for graph neighbors
- `ego_graph_k_hops` (default: 2, range: 1-5): Depth of graph traversal (higher = more neighbors)
- **Automatic Import Filtering** (v0.8.3+): When ego-graph is enabled, stdlib and third-party imports are automatically filtered from graph traversal for cleaner, more relevant neighbors (RepoGraph Feature #5: Repository-Dependent Relation Filtering)
- `ego_graph_max_neighbors_per_hop` (default: 10, range: 1-50): Maximum neighbors to retrieve per hop
- `include_parent` (default: False): Enable parent-child retrieval - when a method is matched, also retrieve its enclosing class for fuller context ("Match Small, Retrieve Big")

**Examples**:

```bash
# General search
search_code("StreamDiffusionExt callback functions")

# Filtered search
search_code("OSC message handlers", file_pattern="Scripts/", chunk_type="function")

# Broader search with more results
search_code("token merging implementation", k=10)

# Ego-graph expansion for richer context (graph neighbors)
search_code("authentication handler", ego_graph_enabled=True, ego_graph_k_hops=2)

# Parent-child retrieval for fuller method context
search_code("validate user data", chunk_type="method", include_parent=True)
```

**Performance** (Empirically Validated):

- **Hybrid mode**: 68-105ms average (recommended)
- **Semantic mode**: 62-94ms average
- **BM25 mode**: 3-8ms average (fastest for exact symbols)
- **Auto mode**: 52-57ms average

**Result Fields**:

| Field | Type | Always Present | Description |
|-------|------|----------------|-------------|
| `chunk_id` | string | ✅ | Unique identifier (format: `"file:lines:type:name"`) |
| `kind` | string | ✅ | Chunk type (`function`, `class`, `method`, etc.) |
| `score` | float | ✅ | Relevance score (0.0-1.0) |
| `complexity_score` | int | ⚠️ Optional | Cyclomatic complexity (functions/methods only, Python) |
| `graph` | object | ⚠️ Optional | Call relationships (`calls`, `called_by` arrays) |
| `reranker_score` | float | ⚠️ Optional | Neural reranker score (when enabled) |

**Note**: `file` and `lines` fields are present in verbose mode but omitted in compact/ultra modes since `chunk_id` contains this information.

#### 2. `index_directory(directory_path, project_name=None, incremental=True, multi_model=None, include_dirs=None, exclude_dirs=None)`

**Purpose**: Index a project for semantic search (one-time setup)

**Parameters**:

- `directory_path` (required): Absolute path to project root
- `project_name` (optional): Name for organization (defaults to directory name)
- `incremental` (default: True): Use incremental indexing if snapshot exists
- `multi_model` (default: auto): Index for all models when multi-model mode enabled
  - `null/None`: Auto-detect from `CLAUDE_MULTI_MODEL_ENABLED` environment variable
  - `true`: Force multi-model indexing (all 3 models)
  - `false`: Force single-model indexing (current model only)
- `include_dirs` (optional): Only index files in these directories (e.g., `["src/", "lib/"]`)
- `exclude_dirs` (optional): Exclude directories from indexing (e.g., `["tests/", "vendor/"]`)

**Filter Persistence** (v0.5.9+):

- Filters are **automatically saved** to `project_info.json` and reloaded on subsequent indexing
- **Filter change detection**: If filters change during incremental index, automatically triggers **full reindex** to prevent stale data
- Uses path prefix matching with normalized separators (`\` → `/`)

**Progress Bar (v0.6.1+)**:

- Real-time visual feedback during chunking and embedding phases
- Shows progress: `Chunking files... 100% (21/21 files)`, `Embedding... 100% (3/3 batches)`

**Drive-Agnostic Paths (v0.6.3+)**:

- Automatic project discovery when drive letters change (F: → E:)
- Dual-hash lookup for backward compatibility
- `list_projects` shows path relocation status

**Performance**:

- **Full index**: ~30-60s for typical projects
- **Incremental**: 10-50x faster (only processes changed files)
- **Batch removal**: 600-1000x faster for large-scale deletions
- **Multi-model**: 3x time (indexes with all 3 models sequentially)

**Examples**:

```bash
# Basic indexing
index_directory("D:\Users\alexk\FORKNI\STREAM_DIFFUSION")

# Index only source directories
index_directory("C:\Projects\MyApp", include_dirs=["src/", "lib/"])

# Exclude test and vendor directories
index_directory("C:\Projects\MyApp", exclude_dirs=["tests/", "node_modules/", "vendor/"])

# Force multi-model indexing
index_directory("C:\Projects\MyApp", multi_model=True)
```

#### 3. `find_connections(chunk_id=None, symbol_name=None, max_depth=3, exclude_dirs=None)`

**Purpose**: Find all code connections to a given symbol for dependency and impact analysis

**⚠️ USE THIS FOR**: Caller discovery, dependency tracking, flow tracing, impact assessment

**Parameters**:

- `chunk_id` (optional): Direct chunk_id from search results (preferred for precise lookup)
- `symbol_name` (optional): Symbol name to find (may be ambiguous, use chunk_id when possible)
- `max_depth` (default: 3): Maximum depth for dependency traversal (1-5, affects indirect callers)
- `exclude_dirs` (optional): Directories to exclude from symbol resolution and caller lookup (e.g., ["tests/"])

**Returns**: Structured report with direct callers, indirect callers, similar code, and dependency graph

**Call Graph Accuracy** (v0.5.15+): ~90% accuracy for Python projects with import resolution, self/super resolution, type annotation tracking, and assignment tracking

**Use When**:

- Before refactoring or modifying code
- Understanding code relationships and dependencies
- Finding all code connected to a symbol
- Impact assessment for breaking changes
- **Finding function callers** (replaces Grep patterns)
- **Tracing request flows** (replaces manual tracing)

**Example**:

```bash
# Using chunk_id (preferred)
find_connections(chunk_id="auth.py:10-50:function:login")

# Using symbol name
find_connections(symbol_name="User", exclude_dirs=["tests/"])

# With custom depth for deep tracing
find_connections(chunk_id="auth.py:10-50:function:login", max_depth=5)
```

**2-Step Workflow for Relationship Queries**:

```bash
# Step 1: Find the symbol
result = search_code("chunk_file function", chunk_type="function")
chunk_id = result["results"][0]["chunk_id"]

# Step 2: Get all relationships
find_connections(chunk_id=chunk_id, exclude_dirs=["tests/"])
# Returns: Direct callers, indirect callers, similar code, impact graph
# ALL IN ONE CALL vs 4 Grep + 3 Read calls
```

### 🟡 Project Management Tools

#### 4. `list_projects()`

**Purpose**: Show all indexed projects with metadata

**Returns**: JSON with list of projects, paths, and index information

#### 5. `switch_project(project_path)`

**Purpose**: Switch to a different indexed project for searching

**Parameters**:

- `project_path` (required): Path to the project directory

**Example**:

```bash
switch_project("D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13")
```

#### 6. `get_index_status()`

**Purpose**: Check index health and statistics

**Returns**: JSON with index statistics, chunk count, model info, memory usage

#### 7. `clear_index()`

**Purpose**: Delete the entire search index for the current project

**Warning**: Deletes ALL dimension indices (768d, 1024d) and Merkle snapshots. Requires full re-indexing afterward.

#### 8. `delete_project(project_path, force=False)`

**Purpose**: Safely delete an indexed project and all associated data

**Parameters**:

- `project_path` (required): Absolute path to project directory to delete
- `force` (default: False): Force delete even if this is the current project

**Handles deletion of**: Vector indices (FAISS), metadata databases (SQLite), BM25 indices, Merkle snapshots, call graph data

**Important**: Use this tool instead of manual deletion when MCP server is running. Properly closes database connections before deletion to prevent file lock errors. If files are locked, they'll be queued for automatic retry on next server startup.

### 🟢 Search Configuration Tools

#### 9. `configure_search_mode(search_mode="hybrid", bm25_weight=0.4, dense_weight=0.6, enable_parallel=True)`

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

#### 10. `get_search_config_status()`

**Purpose**: View current search configuration and available settings

**Returns**: JSON with current mode, weights, features enabled

#### 11. `configure_query_routing(enable_multi_model=None, default_model=None, confidence_threshold=None)`

**Purpose**: Configure multi-model query routing behavior

**Parameters**:

- `enable_multi_model` (optional): Enable/disable multi-model mode (persisted)
- `default_model` (optional): Set default model ("qwen3", "bge_m3", "coderankembed") (persisted)
- `confidence_threshold` (optional): Minimum confidence for routing (0.0-1.0, default: 0.05) ⚠️ **Runtime-only, not persisted**

**Example**:

```bash
configure_query_routing(enable_multi_model=True, default_model="qwen3", confidence_threshold=0.05)
```

### 🔵 Advanced Tools

#### 12. `find_similar_code(chunk_id, k=5)`

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

#### 13. `configure_reranking(enabled=None, model_name=None, top_k_candidates=None)`

**Purpose**: Configure neural reranking for improved search quality

**Parameters**:

- `enabled` (optional): Enable/disable reranking (5-15% quality improvement)
- `model_name` (optional): Reranker model (default: "BAAI/bge-reranker-v2-m3")
- `top_k_candidates` (optional): Candidates to rerank (default: 50)

**When to enable**:

- Accuracy is critical
- Semantic queries are common
- VRAM available (laptop tier+)

**When to disable**:

- Speed is critical (<100ms searches)
- VRAM limited (minimal tier)

**Example**:

```bash
configure_reranking(enabled=True, top_k_candidates=100)
```

**See**: `docs/ADVANCED_FEATURES_GUIDE.md#neural-reranking-configuration` for all parameters

#### 14. `list_embedding_models()`

**Purpose**: List all available embedding models with specifications

**Returns**: JSON with model info including dimensions, context length, descriptions

**Available Models** (5 total):

- **BGE-M3** ⭐: 1024d, 1-1.5GB VRAM, production baseline
- **Qwen3-0.6B**: 1024d, 2.3GB VRAM, best value & high efficiency
- **Qwen3-4B** 🆕: 1024d (MRL), 8-10GB VRAM, best quality with Matryoshka MRL
- **CodeRankEmbed**: 768d, 2GB VRAM, code-specific retrieval
- **EmbeddingGemma-300m**: 768d, 4-8GB VRAM, default model (fast)

#### 15. `switch_embedding_model(model_name)`

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

#### Lazy Loading Performance (v0.5.17+)

**VRAM Lifecycle**:

- **Startup**: 0 MB VRAM (lazy loading enabled)
- **First search**: 8-15s total (5-10s one-time model loading + 3-5s search)
- **Subsequent searches**: 3-5s (models stay loaded in memory)
- **After first search**: 5.3 GB VRAM total (all 3 models loaded for multi-model routing)
- **After cleanup**: 0 MB VRAM (manual cleanup with `cleanup_resources()`)

**Key Behavior**:

- Models load on-demand during first search operation
- Once loaded, models remain in memory for fast subsequent searches
- Use `cleanup_resources()` to free VRAM when switching projects or when memory is low
- Startup time: 3-5s (no model loading overhead)

**Example Workflow**:

```bash
# Startup: 0 MB VRAM
get_memory_status()  # Shows 0 MB VRAM

# First search: 8-15s (includes model loading)
search_code("authentication functions")  # 5-10s model load + 3-5s search

# Subsequent searches: 3-5s (models already loaded)
search_code("database connections")  # Fast, no loading

# Check memory after searches
get_memory_status()  # Shows ~5.3 GB VRAM (3 models loaded)

# Free memory when done
cleanup_resources()  # Returns to 0 MB VRAM
```

### VRAM Tier Management (v0.5.17+)

**Purpose**: Automatic model and feature configuration based on available GPU memory

**4 VRAM Tiers**:

| Tier | VRAM Range | Recommended Models | Features |
|------|------------|-------------------|----------|
| **Minimal** | <6GB | EmbeddingGemma OR CodeRankEmbed | Single-model only |
| **Laptop** | 6-10GB | BGE-M3 OR Qwen3-0.6B | Multi-model + Reranking |
| **Desktop** | 10-18GB | Qwen3-4B + 3-model pool | Full features |
| **Workstation** | 18GB+ | Full 3-model pool | Maximum quality |

**Automatic Configuration**:

- System detects available VRAM on startup
- Recommends optimal model for tier
- Enables/disables features based on memory

**Environment Override**:

```bash
set CLAUDE_VRAM_TIER=laptop
```

**See**: `docs/MODEL_MIGRATION_GUIDE.md` for detailed tier recommendations

---

### Qwen3 Features (v0.6.4+)

#### Instruction Tuning

**Purpose**: Code-optimized query instructions for better retrieval (1-5% improvement)

**Two modes**:

- **custom** (default): Code-specific instructions
  `"Instruct: Retrieve source code implementations matching the query\nQuery: {query}"`
- **prompt_name**: Model's built-in generic prompt

**Configuration**: Automatic for Qwen3 models, configurable in `search/config.py`

#### Matryoshka MRL (Qwen3-4B only)

**Purpose**: Reduce storage 2x with <1.5% quality drop

**How it works**:

- Full model dimension: 2560
- Truncated to: 1024 (same as Qwen3-0.6B and BGE-M3)
- Keeps 4B model quality (36 layers)

**Benefits**:

- 50% storage reduction
- Same dimension as other 1024d models → instant switching
- Best quality for reasonable VRAM (8-10GB)

**See**: `docs/ADVANCED_FEATURES_GUIDE.md#qwen3-instruction-tuning--mrl-v064` for details

---

### 🟣 Memory Management Tools

#### 16. `get_memory_status()`

**Purpose**: Get current memory usage for index and system

**Returns**: JSON with RAM/VRAM usage, GPU status, available memory

#### 17. `cleanup_resources()`

**Purpose**: Manually cleanup all resources to free memory

**Use When**:

- Switching between large projects
- Memory running low
- GPU memory needs to be freed

#### 18. `configure_chunking(enable_greedy_merge=None, min_chunk_tokens=None, max_merged_tokens=None, token_estimation=None, enable_large_node_splitting=None, max_chunk_lines=None)`

**Purpose**: Configure code chunking settings at runtime

**Parameters**:

- `enable_greedy_merge` (optional): Enable/disable greedy chunk merging (default: True)
- `min_chunk_tokens` (optional): Minimum tokens before merge (10-500, default: 50)
- `max_merged_tokens` (optional): Maximum tokens for merged chunks (100-5000, default: 1000)
- `token_estimation` (optional): Token estimation method - "whitespace" (fast) or "tiktoken" (accurate, default: "whitespace")
- `enable_large_node_splitting` (optional): Enable AST block splitting for large functions (default: False)
- `max_chunk_lines` (optional): Maximum lines per chunk before splitting at AST boundaries (10-1000, default: 100)

**Returns**: Updated configuration + system message

**Note**: Re-index project to apply changes

**Example**:

```bash
# Enable greedy merging with custom token limits
configure_chunking(enable_greedy_merge=True, min_chunk_tokens=50, max_merged_tokens=1000)

# Enable large node splitting for better granularity
configure_chunking(enable_large_node_splitting=True, max_chunk_lines=100)

# View current chunking settings
get_search_config_status()
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
- **Savings**: **63% reduction** (validated benchmark)
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

### Runtime Performance (v0.5.17+)

- **Startup**: 3-5s, 0 MB VRAM (lazy loading enabled)
- **First search**: 8-15s total (5-10s one-time model loading + 3-5s search)
- **Subsequent searches**: 3-5s (models cached in memory)
- **VRAM after first search**: ~5.3 GB (multi-model routing with 3 models loaded)
- **Cleanup**: Returns to 0 MB VRAM with `cleanup_resources()`

### Query Cache (v0.5.17+)

- **LRU cache** for query embeddings (128 entries default)
- **Performance**: Repeated queries = 0ms encoding (instant)
- **Configuration**: `set CLAUDE_QUERY_CACHE_SIZE=256`

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

### Self-Healing Index Sync (v0.5.17+)

**Automatic Maintenance**: The system automatically detects and repairs BM25 index desynchronization (>10% threshold) during incremental indexing. Typical sync time: ~5 seconds for 4000+ documents. No manual intervention required.

## Examples for Python Projects

### Example 1: Finding Authentication Functions

```bash
# 1. Verify project context
list_projects()
switch_project("/path/to/your/project")

# 2. Search for authentication functions
search_code("user authentication login password validation", file_pattern="auth", chunk_type="function", k=10)
```

### Example 2: Understanding Database Connection Setup

```bash
# 1. Verify context
get_index_status()

# 2. Use semantic search for conceptual understanding
configure_search_mode("semantic", 0.3, 0.7)
search_code("database connection initialization setup pool", k=15)
```

### Example 3: Finding Specific Class Implementation

```bash
# 1. Use BM25 for exact class name
configure_search_mode("bm25", 0.8, 0.2)
search_code("UserModel class", chunk_type="class")

# 2. Find similar implementations
find_similar_code("models/user.py:10-100:class:UserModel", k=5)
```

### Example 4: Analyzing API Request Handling

```bash
# 1. Use hybrid for balanced search
configure_search_mode("hybrid", 0.4, 0.6)
search_code("API request handler middleware validation", k=10)

# 2. Get multi-hop context (automatic)
# Multi-hop will discover: implementation, configuration, integration points
```

### Example 5: Debugging Query Performance

```bash
# 1. Find performance-related code
search_code("database query optimization performance caching", include_dirs=["src/", "lib/"], k=15)

# 2. Check memory usage
get_memory_status()
```

## Examples: Relationship Queries (ESSENTIAL)

### Finding Function Callers (The RIGHT Way)

**Problem**: You need to find all code that calls a specific function.

**❌ Wrong Approach** (Manual Grep + Multiple Reads):

```bash
# Bad: Manual grep for callers
Grep(pattern="\\.chunk_file\\(")
# Then read each file individually
Read(file_path="file1.py")
Read(file_path="file2.py")
Read(file_path="file3.py")
# Result: 4 Grep + 3 Read = ~3,800 tokens
```

**✅ Correct Approach** (2-Step Workflow):

```bash
# Step 1: Find the function
result = search_code("chunk_file function", chunk_type="function")
# Result: chunk_id = "chunking/multi_language_chunker.py:215-237:function:chunk_file"

# Step 2: Find ALL callers in ONE call
find_connections(
    chunk_id="chunking/multi_language_chunker.py:215-237:function:chunk_file",
    exclude_dirs=["tests/"]
)
# Returns: direct callers, indirect callers (multi-hop), similar code, impact graph
# Result: 1 search + 1 find_connections = ~1,500 tokens (60% savings)
```

### Tracing Request Flow

**Problem**: Trace the complete flow from entry point to implementation.

**✅ Correct Approach**:

```bash
# Step 1: Find entry point
result = search_code("handle_call_tool function", chunk_type="decorated_definition")
chunk_id = result["results"][0]["chunk_id"]

# Step 2: Trace full flow with deep traversal
find_connections(chunk_id=chunk_id, max_depth=5, exclude_dirs=["tests/"])
# Returns: Complete call chain with depth levels
# Shows: handle_call_tool → handler lookup → specific handler → implementation
```

### Finding Dependencies

**Problem**: Find all code that depends on a class/module.

**✅ Correct Approach**:

```bash
# Option 1: Using chunk_id (preferred)
result = search_code("QueryRouter class", chunk_type="class")
chunk_id = result["results"][0]["chunk_id"]
find_connections(chunk_id=chunk_id, exclude_dirs=["tests/"])

# Option 2: Using symbol_name (when chunk_id unknown)
find_connections(symbol_name="QueryRouter", exclude_dirs=["tests/"])
# Returns: all code that imports/uses QueryRouter, including:
# - Direct importers
# - Functions that use it
# - Indirect dependencies
```

### Impact Assessment Before Refactoring

**Problem**: Before modifying a function, understand its impact.

**✅ Correct Approach**:

```bash
# Step 1: Find the function you want to modify
result = search_code("incremental_index function", chunk_type="function")
chunk_id = result["results"][0]["chunk_id"]

# Step 2: Analyze full impact
find_connections(chunk_id=chunk_id, max_depth=3)
# Returns:
# - Direct callers: Functions that call it directly
# - Indirect callers: Functions that call the callers (multi-hop)
# - Similar code: Other functions that might need similar changes
# - Dependency graph: Visual representation of relationships
```

**Token Savings Summary**:

- Finding callers: 60% fewer tokens vs Grep + Read
- Tracing flow: 50% fewer tokens vs manual tracing
- Finding dependencies: 50% fewer tokens vs import tracing

---

## Summary

This skill ensures that all MCP semantic search operations follow the optimal workflow:

1. ✅ **Validate project context** before every search
2. ✅ **Use search-first protocol** for 40-45% token savings
3. ✅ **Apply optimal search modes** for accurate results
4. ✅ **Leverage multi-hop and stemming** for comprehensive discovery
5. ✅ **Monitor and optimize** for best performance

**Result**: Relevant, accurate code search with maximum efficiency and minimal token usage.
