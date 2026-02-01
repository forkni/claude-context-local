---
name: mcp-search-tool
description: MCP semantic search instructions. ON ACTIVATION: Acknowledge and wait. Apply rules to all code searches.
---

# MCP Search Tool Skill

## 🚀 On Activation

**IMPORTANT**: This skill provides BEHAVIORAL INSTRUCTIONS, not information to analyze.

**When this skill loads**:
1. Acknowledge: "MCP Search skill active. Ready to use semantic search for code exploration."
2. Wait for the user's actual task
3. Apply the guidance below to all subsequent code search operations

**DO NOT**:
- Explore or analyze this skill document
- Launch agents to investigate the skill
- Treat this as a request for information about MCP tools

---

## Purpose

This skill ensures that all MCP semantic search operations follow the correct workflow for accurate, relevant results with maximum token efficiency (40-45% savings). It enforces project context validation before searches and applies optimal search configuration.

## 🎯 QUICK START: Which Tool to Use?

**BEFORE searching, identify your query type:**

```
What are you trying to do?
│
├─ "Find callers of X" ──────────────► find_connections(chunk_id)
├─ "What depends on X" ──────────────► find_connections(chunk_id)
├─ "Trace flow from X to Y" ─────────► find_path(source_chunk_id, target_chunk_id)
├─ "How does X connect to Y?" ───────► find_path(source_chunk_id, target_chunk_id)
├─ "Find only imports/inheritance" ──► find_connections(chunk_id, relationship_types=["imports", "inherits"])
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

---

## ⛔ Common Mistakes (AVOID)

| ❌ Wrong Approach | ✅ Correct Approach | Savings |
|------------------|---------------------|---------|
| `Grep("\.function\(")` for callers | `find_connections(chunk_id)` | 60% fewer tokens |
| Multiple Reads to trace flow | `find_connections(max_depth=5)` | 50% fewer tokens |
| Manual import tracing | `find_connections(symbol_name)` | 50% fewer tokens |

---

## 📚 Quick Function Index

### All 19 MCP Tools at a Glance

| Tool | Category | Purpose | Key Parameters | Jump To |
|------|----------|---------|----------------|---------|
| **search_code** | 🔴 Essential | Find code with NL query or chunk_id lookup | `query`, `chunk_id`, `chunk_type`, `include_dirs`, `exclude_dirs` | [Details](#1-search_codequery-or-chunk_id-k5-search_modehybrid-model_keynone-use_routingtrue-file_patternnone-include_dirsnone-exclude_dirsnone-chunk_typenone-include_contexttrue-auto_reindextrue-max_age_minutes5) |
| **find_connections** | 🔴 Essential | Find callers, dependencies, flow (graph analysis) | `chunk_id`, `symbol_name`, `max_depth`, `exclude_dirs`, `relationship_types` | [Details](#3-find_connectionschunk_idnone-symbol_namenone-max_depth3-exclude_dirsnone-relationship_typesnone) |
| **find_path** | 🔴 Essential | Trace shortest path between code entities | `source`, `target`, `source_chunk_id`, `target_chunk_id`, `edge_types`, `max_hops` | [Details](#4-find_pathsourcenone-targetnone-source_chunk_idnone-target_chunk_idnone-edge_typesnone-max_hops10) |
| **index_directory** | 🔴 Setup | Index project for search (one-time) | `directory_path`, `incremental`, `multi_model`, `include_dirs`, `exclude_dirs` | [Details](#2-index_directorydirectory_path-project_namenone-incrementaltrue-multi_modelnone-include_dirsnone-exclude_dirsnone) |
| list_projects | Management | Show all indexed projects | *(none)* | [Details](#5-list_projects) |
| switch_project | Management | Change active project | `project_path` | [Details](#6-switch_projectproject_path) |
| get_index_status | Status | Check index health | *(none)* | [Details](#7-get_index_status) |
| clear_index | Reset | Delete current index | *(none)* | [Details](#8-clear_index) |
| delete_project | Reset | Safely delete indexed project | `project_path`, `force` | [Details](#9-delete_projectproject_path-forcefalse) |
| configure_search_mode | Config | Set search mode & weights | `search_mode`, `bm25_weight`, `dense_weight` | [Details](#10-configure_search_modesearch_modehybrid-bm25_weight04-dense_weight06-enable_paralleltrue) |
| get_search_config_status | Config | View current config | *(none)* | [Details](#11-get_search_config_status) |
| configure_query_routing | Config | Multi-model routing settings | `enable_multi_model`, `default_model`, `confidence_threshold` | [Details](#12-configure_query_routingenable_multi_modelnone-default_modelnone-confidence_thresholdnone) |
| find_similar_code | Secondary | Find functionally similar code | `chunk_id`, `k` | [Details](#13-find_similar_codechunk_id-k5) |
| configure_reranking | Config | Neural reranking settings | `enabled`, `model_name`, `top_k_candidates` | [Details](#14-configure_rerankingenablednone-model_namenone-top_k_candidatesnone) |
| configure_chunking | Config | Configure code chunking settings | `enable_community_detection`, `enable_community_merge`, `community_resolution`, `token_estimation`, `enable_large_node_splitting`, `max_chunk_lines` | [Details](#19-configure_chunkingenable_community_detectionnone-enable_community_mergenone-community_resolutionnone-token_estimationnone-enable_large_node_splittingnone-max_chunk_linesnone) |
| list_embedding_models | Model | Show available models | *(none)* | [Details](#15-list_embedding_models) |
| switch_embedding_model | Model | Change embedding model | `model_name` | [Details](#16-switch_embedding_modelmodel_name) |
| get_memory_status | Monitor | Check RAM/VRAM usage | *(none)* | [Details](#17-get_memory_status) |
| cleanup_resources | Cleanup | Free memory/caches | *(none)* | [Details](#18-cleanup_resources) |

### Usage Patterns by Task

| Task Type | Primary Tool | Secondary Tool | Pattern |
|-----------|--------------|----------------|---------|
| **Find code by concept** | `search_code(query)` | - | Semantic search |
| **Find callers/dependencies** | `search_code()` → `find_connections(chunk_id)` | - | 2-step workflow |
| **Trace path between entities** | `search_code()` → `find_path(source_chunk_id, target_chunk_id)` | - | Path discovery |
| **Filter by relationship type** | `find_connections(chunk_id, relationship_types=["inherits"])` | - | Targeted relationship analysis |
| **Direct symbol lookup** | `search_code(chunk_id="...")` | - | O(1) lookup |
| **Impact assessment** | `find_connections(max_depth=5)` | - | Multi-hop graph |
| **Find similar patterns** | `search_code()` → `find_similar_code(chunk_id)` | - | Similarity search |
| **Find code + graph neighbors** | `search_code(ego_graph_enabled=True)` | - | Graph-enhanced search |
| **Match method, retrieve class** | `search_code(query, include_parent=True)` | - | Parent-child retrieval |
| **Setup new project** | `index_directory(path)` | `get_index_status()` | One-time indexing |
| **Switch projects** | `list_projects()` → `switch_project(path)` | - | Project management |
| **Memory cleanup** | `get_memory_status()` → `cleanup_resources()` | - | Resource management |

## Complete MCP Tool Reference (19 Tools)

### 🔴 Essential Tools (Use First)

#### 1. `search_code(query OR chunk_id, k=4, search_mode="auto", model_key=None, use_routing=True, file_pattern=None, include_dirs=None, exclude_dirs=None, chunk_type=None, include_context=True, auto_reindex=True, max_age_minutes=5, ego_graph_enabled=False, ego_graph_k_hops=1, ego_graph_max_neighbors_per_hop=5, include_parent=False)`

**Purpose**: Find code with natural language queries OR direct symbol lookup (40-45% token savings vs file reading)

**Parameters**:

- `query` (optional): Natural language description of what you're looking for
- `chunk_id` (optional): Direct chunk ID for O(1) lookup (format: "file:lines:type:name")
- `k` (default: 4): Number of results to return
- `search_mode` (default: "auto"): Search method - "hybrid", "semantic", "bm25", or "auto"
- `model_key` (optional): Force specific model - "qwen3", "bge_m3", "coderankembed", "gte_modernbert", "c2llm"
- `use_routing` (default: True): Enable multi-model query routing
- `file_pattern` (optional): Filter by filename/path pattern (e.g., "auth", "models")
- `include_dirs` (optional): Only search in these directories (e.g., ["src/", "lib/"])
- `exclude_dirs` (optional): Exclude from search (e.g., ["tests/", "vendor/"])
- `chunk_type` (optional): Filter by code structure - "function", "class", "method", "module", "decorated_definition", "interface", "enum", "struct", "type", "merged", "split_block", or None for all
  - `"merged"`: Community-merged chunks (multiple related code blocks merged together for better context)
  - `"split_block"`: Large function blocks split at AST boundaries for better granularity
- `include_context` (default: True): Include similar chunks and relationships
- `auto_reindex` (default: True): Automatically reindex if index is stale
- `max_age_minutes` (default: 5): Maximum age of index before auto-reindex
- `ego_graph_enabled` (default: False): Enable RepoGraph-style k-hop ego-graph expansion for graph neighbors
- `ego_graph_k_hops` (default: 1, range: 1-5): Depth of graph traversal (1=direct neighbors, reduced from 2 to limit noise)
- **Weighted Graph Traversal** (v0.8.7+): Ego-graph uses edge-type-weighted BFS — `calls` edges (weight=1.0) are prioritized over `imports` edges (weight=0.3). Based on SOG paper ablation showing different relation types contribute differently to code understanding.
- **Automatic Import Filtering** (v0.8.3+): When ego-graph is enabled, stdlib and third-party imports are automatically filtered from graph traversal for cleaner, more relevant neighbors (RepoGraph Feature #5: Repository-Dependent Relation Filtering)
- `ego_graph_max_neighbors_per_hop` (default: 5, range: 1-50): Maximum neighbors to retrieve per hop (reduced from 10 for precision)
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

# Search for community-merged code blocks (better context)
search_code("GraphQueryEngine class", chunk_type="merged")

# Search for large function segments split at AST boundaries
search_code("ParallelChunker chunk_files", chunk_type="split_block")
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
| `blended_score` | float | ✅ | Final ranking score (centrality × alpha + semantic × (1-alpha)) |
| `centrality` | float | ✅ | PageRank centrality score (structurally important code scores higher) |
| `source` | string | ✅ | How result was found: `"hybrid"`, `"multi_hop"`, `"ego_graph"` |
| `complexity_score` | int | ⚠️ Optional | Cyclomatic complexity (functions/methods only, Python) |
| `graph` | object | ⚠️ Optional | Code relationships (21 types: `calls`, `inherits`, `imports`, `uses_type`, etc.) |
| `reranker_score` | float | ⚠️ Optional | Neural reranker score (when enabled) |

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

#### 3. `find_connections(chunk_id=None, symbol_name=None, max_depth=3, exclude_dirs=None, relationship_types=None)`

**Purpose**: Find all code connections to a given symbol for dependency and impact analysis

**⚠️ USE THIS FOR**: Caller discovery, dependency tracking, flow tracing, impact assessment

**Parameters**:

- `chunk_id` (optional): Direct chunk_id from search results (preferred for precise lookup)
- `symbol_name` (optional): Symbol name to find (may be ambiguous, use chunk_id when possible)
- `max_depth` (default: 3): Maximum depth for dependency traversal (1-5, affects indirect callers)
- `exclude_dirs` (optional): Directories to exclude from symbol resolution and caller lookup (e.g., ["tests/"])
- `relationship_types` (optional, v0.8.4+): Filter to only include specific relationship types (e.g., `["inherits", "imports", "decorates"]`). If not provided, all relationship types are included.

  **Valid types (21 total)**: `calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`, `defines_constant`, `defines_enum_member`, `defines_class_attr`, `defines_field`, `uses_constant`, `uses_default`, `uses_global`, `asserts_type`, `uses_context_manager`

**Relationship Extractors** (v0.8.7+): 15 extractors active, including P3 extractors for `implements` (Protocol/ABC detection) and `overrides` (method override detection via inheritance graph)

**Returns**: Structured report with direct callers, indirect callers, similar code, and dependency graph

**Call Graph Accuracy** (v0.5.15+): ~90% accuracy for Python projects with import resolution, self/super resolution, type annotation tracking, and assignment tracking

**Relationship Edge Count** (v0.8.5+): 4,599 edges with 13 active relationship types in production (verified 2026-01-15)

**Use When**:

- Before refactoring or modifying code
- Understanding code relationships and dependencies
- Finding all code connected to a symbol
- Impact assessment for breaking changes
- **Finding function callers** (replaces Grep patterns)
- **Tracing request flows** (replaces manual tracing)
- **Analyzing inheritance hierarchies** (filter by `inherits`)
- **Finding type usage** (filter by `uses_type`, `instantiates`)

**Examples**:

```bash
# Using chunk_id (preferred)
find_connections(chunk_id="auth.py:10-50:function:login")

# Using symbol name
find_connections(symbol_name="User", exclude_dirs=["tests/"])

# With custom depth for deep tracing
find_connections(chunk_id="auth.py:10-50:function:login", max_depth=5)

# Filter for only inheritance relationships (v0.8.4+)
find_connections(symbol_name="PythonChunker", relationship_types=["inherits"])
# ✅ VERIFIED: Returns parent_classes[1]: LanguageChunker
# Returns: Only parent_classes/child_classes populated, all other relationship fields empty

# Filter for only import relationships (v0.8.4+)
find_connections(chunk_id="database.py:10-50:class:Database", relationship_types=["imports"])
# Returns: Only imports/imported_by populated, all other relationship fields empty

# Multiple relationship types (v0.8.4+)
find_connections(symbol_name="InheritanceExtractor", relationship_types=["instantiates", "uses_type"])
# ✅ VERIFIED: Returns uses_types[9]: RelationshipEdge, ast.AST, str, dict, list...
# ✅ VERIFIED: Returns instantiated_by[1]: MultiLanguageChunker
# Returns: Only type usage and instantiation relationships populated

# All calls relationships (default behavior)
find_connections(chunk_id="chunk_file:...", relationship_types=["calls"])
# Returns: Only direct_callers/indirect_callers populated
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

#### 4. `find_path(source=None, target=None, source_chunk_id=None, target_chunk_id=None, edge_types=None, max_hops=10)`

**Purpose**: Find shortest path between two code entities in the relationship graph (v0.8.4+)

**⚠️ USE THIS FOR**: Tracing how code element A connects to code element B, understanding dependency chains, finding call paths

**Parameters**:

- `source` (optional): Source symbol name (may be ambiguous, use source_chunk_id when possible)
- `target` (optional): Target symbol name (may be ambiguous, use target_chunk_id when possible)
- `source_chunk_id` (optional): Source chunk_id from search results (preferred for precision)
- `target_chunk_id` (optional): Target chunk_id from search results (preferred for precision)
- `edge_types` (optional): Filter path to only use specific relationship types (e.g., `["calls", "inherits"]`). If not provided, all relationship types are considered.

  **Valid types (21 total)**: `calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`, `defines_constant`, `defines_enum_member`, `defines_class_attr`, `defines_field`, `uses_constant`, `uses_default`, `uses_global`, `asserts_type`, `uses_context_manager`

- `max_hops` (default: 10, range: 1-20): Maximum path length in edges

**Returns**: Path as sequence of nodes with metadata, edge types traversed, path length (number of hops)

**Algorithm**: Bidirectional Breadth-First Search (BFS) for optimal performance

**Use When**:

- Tracing how code element A connects to code element B
- Understanding dependency chains between modules
- Finding call paths from entry points to specific functions
- Analyzing inheritance or import chains

**Examples**:

```bash
# Using chunk_ids (preferred)
find_path(
    source_chunk_id="auth.py:10-50:function:login",
    target_chunk_id="database.py:100-150:function:query"
)
# Returns: Path showing how login() connects to query() through calls

# Using symbol names
find_path(source="UserModel", target="DatabaseConnection")
# Returns: Path between classes (may be ambiguous if multiple symbols exist)

# Filter by edge types (only follow calls and imports)
find_path(
    source_chunk_id="main.py:1-50:function:main",
    target_chunk_id="utils.py:10-50:function:helper",
    edge_types=["calls", "imports"]
)
# Returns: Path using only call and import relationships

# Trace inheritance chain
find_path(
    source="ChildClass",
    target="BaseClass",
    edge_types=["inherits"]
)
# Returns: Inheritance path from child to base class

# Custom max hops for deeper tracing
find_path(
    source_chunk_id="api.py:10-50:function:handler",
    target_chunk_id="core.py:100-150:function:process",
    max_hops=15
)
# Returns: Path up to 15 hops deep
```

**Return Format**:

```json
{
  "path": [
    {
      "chunk_id": "auth.py:10-50:function:login",
      "name": "login",
      "file": "auth.py",
      "lines": "10-50",
      "kind": "function"
    },
    {
      "chunk_id": "session.py:20-60:function:create_session",
      "name": "create_session",
      "file": "session.py",
      "lines": "20-60",
      "kind": "function"
    },
    {
      "chunk_id": "database.py:100-150:function:query",
      "name": "query",
      "file": "database.py",
      "lines": "100-150",
      "kind": "function"
    }
  ],
  "edge_types": ["calls", "calls"],
  "path_length": 2
}
```

**Performance**: 10/10 tests passed (verified 2026-01-15)

### 🟡 Project Management Tools

#### 5. `list_projects()`

**Purpose**: Show all indexed projects with metadata

**Returns**: JSON with list of projects, paths, and index information

#### 6. `switch_project(project_path)`

**Purpose**: Switch to a different indexed project for searching

**Parameters**:

- `project_path` (required): Path to the project directory

**Example**:

```bash
switch_project("D:\Users\alexk\FORKNI\STREAM_DIFFUSION\STREAM_DIFFUSION_CUDA_0.2.99_CUDA_13")
```

#### 7. `get_index_status()`

**Purpose**: Check index health and statistics

**Returns**: JSON with index statistics, chunk count, model info, memory usage

#### 8. `clear_index()`

**Purpose**: Delete the entire search index for the current project

**Warning**: Deletes ALL dimension indices (768d, 1024d) and Merkle snapshots. Requires full re-indexing afterward.

#### 9. `delete_project(project_path, force=False)`

**Purpose**: Safely delete an indexed project and all associated data

**Parameters**:

- `project_path` (required): Absolute path to project directory to delete
- `force` (default: False): Force delete even if this is the current project

**Handles deletion of**: Vector indices (FAISS), metadata databases (SQLite), BM25 indices, Merkle snapshots, call graph data

**Important**: Use this tool instead of manual deletion when MCP server is running. Properly closes database connections before deletion to prevent file lock errors. If files are locked, they'll be queued for automatic retry on next server startup.

### 🟢 Search Configuration Tools

#### 10. `configure_search_mode(search_mode="hybrid", bm25_weight=0.4, dense_weight=0.6, enable_parallel=True)`

**Purpose**: Configure search mode and hybrid search parameters

**Parameters**:

- `search_mode`: "hybrid" (default), "semantic", "bm25", or "auto"
- `bm25_weight`: Weight for BM25 sparse search (0.0 to 1.0)
- `dense_weight`: Weight for dense vector search (0.0 to 1.0)
- `enable_parallel`: Enable parallel BM25 + Dense search execution

**Optimal Settings** (Empirically Validated):

- **General use**: hybrid mode, 0.4 BM25 / 0.6 Dense (default)
- **Implementation queries**: hybrid mode, 0.6 BM25 / 0.4 Dense (when config ranks over code)
- **Code structure queries**: hybrid mode, 0.3 BM25 / 0.7 Dense
- **Error/log analysis**: hybrid mode, 0.7 BM25 / 0.3 Dense

**Example**:

```bash
configure_search_mode("hybrid", 0.4, 0.6, true)
```

#### 11. `get_search_config_status()`

**Purpose**: View current search configuration and available settings

**Returns**: JSON with current mode, weights, features enabled

#### 12. `configure_query_routing(enable_multi_model=None, default_model=None, confidence_threshold=None)`

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

#### 13. `find_similar_code(chunk_id, k=4)`

**Purpose**: Find code chunks functionally similar to a reference chunk

**Parameters**:

- `chunk_id` (required): ID from search_code results (format: "file:lines:type:name")
- `k` (default: 4): Number of similar chunks to return

**Workflow**:

1. First use `search_code()` to find a reference chunk
2. Use the `chunk_id` from results with this tool
3. Get ranked list of functionally similar code

**Example**:

```bash
# First find a reference
search_code("authentication handler")
# Then find similar code using the chunk_id from results
find_similar_code("src/auth.py:10-50:function:authenticate", k=4)
```

#### 14. `configure_reranking(enabled=None, model_name=None, top_k_candidates=None)`

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

#### 15. `list_embedding_models()`

**Purpose**: List all available embedding models with specifications

**Returns**: JSON with model info including dimensions, context length, descriptions

**Available Models** (5 total):

- **BGE-M3** ⭐: 1024d, 1-1.5GB VRAM, production baseline
- **Qwen3-0.6B**: 1024d, 2.3GB VRAM, best value & high efficiency
- **CodeRankEmbed**: 768d, 0.5-0.6GB VRAM, code-specific retrieval
- **GTE-ModernBERT**: 768d, 0.28GB VRAM, lightweight code-optimized (CoIR: 79.31 NDCG@10)
- **EmbeddingGemma-300m**: 768d, 4-8GB VRAM, default model (fast)

#### 16. `switch_embedding_model(model_name)`

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

#### 17. `get_memory_status()`

**Purpose**: Get current memory usage for index and system

**Returns**: JSON with RAM/VRAM usage, GPU status, available memory

#### 18. `cleanup_resources()`

**Purpose**: Manually cleanup all resources to free memory

**Clears** (v0.8.6+):

- Embedding models from GPU/VRAM
- FAISS indices from RAM
- **Query embedding cache** (with TTL-expired entries)
- BM25 indices
- Call graph data structures

**Use When**:

- Switching between large projects
- Memory running low
- GPU memory needs to be freed

#### 19. `configure_chunking(enable_community_detection=None, enable_community_merge=None, community_resolution=None, token_estimation=None, enable_large_node_splitting=None, max_chunk_lines=None)`

**Purpose**: Configure code chunking settings at runtime

**Parameters**:

- `enable_community_detection` (optional): Enable/disable community detection via Louvain algorithm (default: True)
- `enable_community_merge` (optional): Enable/disable community-based remerge for full index (default: True)
- `community_resolution` (optional): Resolution parameter for Louvain community detection (0.1-2.0, default: 1.0, higher = more communities)
- `token_estimation` (optional): Token estimation method - "whitespace" (fast) or "tiktoken" (accurate, default: "whitespace")
- `enable_large_node_splitting` (optional): Enable AST block splitting for large functions (default: False)
- `max_chunk_lines` (optional): Maximum lines per chunk before splitting at AST boundaries (10-1000, default: 100)

**Returns**: Updated configuration + system message

**Note**: Re-index project to apply changes. `min_chunk_tokens` (50) and `max_merged_tokens` (1000) are optimal defaults and not exposed as parameters.

**Example**:

```bash
# Configure community detection with custom resolution
configure_chunking(enable_community_detection=True, community_resolution=1.5)

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

## Advanced Features

### Feature Classification

| Category | Features | Control | Description |
|----------|----------|---------|-------------|
| **Always-on quality** | Multi-Hop (hybrid mode), Centrality Reranking, BM25 Stemming | Global config | Directly improve result quality — no opt-in needed |
| **Per-query opt-in** | `ego_graph_enabled`, `include_parent` | MCP parameter | Change output shape — Claude agent enables when helpful |

### Multi-Hop Search (Graph-Aware)

**Purpose**: Discover interconnected code relationships through graph traversal and semantic similarity

**How It Works** (3 expansion modes):

| Mode | Expansion Method | Use Case |
|------|-----------------|----------|
| `"hybrid"` (default) | Graph neighbors first, then semantic similarity | Best quality — structurally relevant + semantically similar |
| `"graph"` | Code graph neighbors only (`calls`, `inherits`, `imports`) | When structural dependencies matter most |
| `"semantic"` | FAISS similarity only (legacy) | Pure semantic matching |

1. **Hop 1**: Find chunks matching your query (hybrid search with k×2 results)
2. **Hop 2 (graph)**: For each top result, find graph neighbors via weighted BFS (prioritizes `calls`=1.0 over `imports`=0.3)
3. **Hop 2 (semantic)**: Find semantically similar chunks (skips already-seen from graph)
4. **Re-ranking**: Sort ALL discovered chunks by query relevance through the reranker

**Key Research Finding** (RepoGraph ICLR 2025, SOG USENIX '24):
Graph traversal finds **functionally necessary dependencies** that semantic search misses. A query for `process_payment()` now also finds `db.connect()` and `validate_card()` via `calls` edges.

**Benefits** (Empirically Validated):
- **93.3% of queries benefit** from multi-hop
- **Graph neighbors compete through reranker** — only the best-ranked results survive
- Results show `source: "multi_hop"` when discovered via graph expansion

**Performance**: +25-35ms overhead (negligible for 93% benefit rate)

**Status**: **Always-on** with optimal settings (2 hops, 0.3 expansion, hybrid mode)

### Centrality Reranking (Always-On)

**Purpose**: Boost structurally important code in search results using PageRank graph analysis

**How It Works**: Blends PageRank centrality scores with semantic similarity:
```
blended_score = centrality × alpha + semantic_score × (1 - alpha)
```
Where `alpha = 0.3` (30% centrality, 70% semantic).

**Effect**: Functions that are frequently called, imported, or inherited rank higher. A utility function called by 50 other functions gets a centrality boost over an isolated helper.

**Result Fields Added**:
- `blended_score`: Final ranking score after centrality blending
- `centrality`: Raw PageRank score for the code chunk

**Status**: **Always-on** when graph data is available (no opt-in needed)

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
