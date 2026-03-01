---
name: mcp-search-tool
description: MCP semantic search workflow. Results are ranked candidates — scan top-4, don't blindly trust rank-1. Acknowledge on load, apply to all searches.
---

# MCP Search Tool Skill

## 🚀 On Activation

**IMPORTANT**: This skill provides BEHAVIORAL INSTRUCTIONS, not information to analyze.

**When this skill loads**:

1. Acknowledge: "MCP Search skill active. Results are ranked candidates — I'll scan all results, not just rank-1."
2. Wait for the user's actual task
3. Apply the guidance below to all subsequent code search operations

**DO NOT**: Explore or analyze this skill document, launch agents to investigate the skill, or treat this as a request for information about MCP tools.

---

## Purpose

Ensures all MCP semantic search operations follow correct workflows for accurate, relevant results with maximum token efficiency (40-45% savings). Enforces project context validation before searches and applies optimal search configuration.

## ⚠️ Critical: Search Results Are Candidates, Not Answers

MCP search returns **ranked candidates**, not definitive answers. The correct result is reliably present in the top-5 results (Hit Rate@5 = 92.3%), but it is NOT always ranked first (Rank-1 accuracy ≈ 69%).

**What this means for you:**

1. **SCAN all returned results** (default k=4) — don't stop at rank-1
2. **EVALUATE relevance** — read chunk names, file paths, and code snippets
3. **The answer is IN the results** — if you need to find X, it's there, but possibly at rank 2-4
4. **Module/summary chunks** may appear — these provide overview context but may not be the specific implementation you need

**Result Interpretation Workflow:**

1. Run `search_code()` with appropriate query and filters
2. **Scan ALL k results** — read each chunk_id and code snippet
3. **Identify the best match** based on your actual need (not just highest score)
4. If the best match is a module/summary chunk but you need specific code, look at lower-ranked results
5. Use `chunk_id` from the best match for follow-up tools (`find_connections`, `find_similar_code`)

**When rank-1 is reliable (≈90% MRR):**

- Small function discovery: "get X", "validate Y", "normalize Z"
- Exact symbol lookup via `chunk_id` parameter

**When you MUST scan all results (≈67-73% MRR):**

- Class overview queries: "what does X do", "how does X work"
- Sibling context queries: "encode and decode", "save and load"
- Queries where module-level summaries may surface alongside implementations

## 🎯 QUICK START: Which Tool to Use?

**BEFORE searching, identify your query type:**

```
What are you trying to do?
│
├─ "Find callers of X" ──────────────► find_connections(chunk_id)
├─ "What depends on X" ──────────────► find_connections(chunk_id)
├─ "Trace flow from X to Y" ─────────► find_path(source_chunk_id, target_chunk_id)
│     [or search_code() — intent classifier auto-routes to find_path if confident]
├─ "How does X connect to Y?" ───────► find_path(source_chunk_id, target_chunk_id)
├─ "Find only imports/inheritance" ──► find_connections(chunk_id, relationship_types=["imports", "inherits"])
├─ "Find similar code to X" ─────────► find_similar_code(chunk_id)
│     [or search_code() — intent classifier auto-routes to find_similar_code if confident]
│
├─ "Find class/function definition" ─► search_code(query, chunk_type)
├─ "Find exact API call pattern" ────► search_code(query, search_mode="bm25")
├─ "Understand concept/feature" ─────► search_code(query) [hybrid mode]
├─ "How does the whole X system work"► search_code(query) [global intent → k auto-expanded]
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

## 📚 MCP Tools Quick Index (19 Tools)

**For full API reference**: See `docs/MCP_TOOLS_REFERENCE.md`

| Tool | Purpose | Primary Use |
|------|---------|-------------|
| **search_code** | Find code with NL query or direct chunk lookup | All code searches |
| **find_connections** | Find callers, dependencies, flow (graph analysis) | Relationship discovery |
| **find_path** | Trace shortest path between entities | Flow tracing |
| index_directory | Index project (one-time setup) | Initial setup |
| list_projects | Show indexed projects | Project management |
| switch_project | Change active project | Project switching |
| get_index_status | Check index health | Status monitoring |
| clear_index | Delete current index | Index reset |
| delete_project | Safely delete project data | Cleanup |
| configure_search_mode | Set search mode & weights | Search tuning |
| get_search_config_status | View current config | Config inspection |
| configure_query_routing | Multi-model routing settings | Model routing |
| find_similar_code | Find functionally similar code | Similarity search |
| configure_reranking | Neural reranking settings | Quality tuning |
| configure_chunking | Code chunking settings | Chunking config |
| list_embedding_models | Show available models | Model discovery |
| switch_embedding_model | Change embedding model | Model switching |
| get_memory_status | Check RAM/VRAM usage | Memory monitoring |
| cleanup_resources | Free memory/caches | Resource cleanup |

---

## 🔴 Essential Tools (Detailed Reference)

### 1. search_code()

**Purpose**: Find code with natural language queries OR direct symbol lookup (40-45% token savings vs file reading)

**Key Parameters**:

- `query` (optional): Natural language description
- `chunk_id` (optional): Direct chunk ID for O(1) lookup (format: "file:lines:type:name")
- `k` (default: 4): Number of results
- `search_mode` (default: "auto"): "hybrid", "semantic", "bm25", "auto"
- `model_key` (optional): Force model ("qwen3", "bge_m3", "coderankembed", "gte_modernbert", "c2llm")
- `use_routing` (default: True): Enable multi-model query routing
- `file_pattern` (optional): Filter by filename/path (e.g., "auth", "models")
- `include_dirs` / `exclude_dirs` (optional): Directory filters (e.g., ["src/"], ["tests/"])
- `chunk_type` (optional): Filter by structure — "function", "class", "method", "module", "decorated_definition", "interface", "enum", "struct", "type", "merged", "split_block", "community", or None
- `include_context` (default: True): Include similar chunks and relationships
- `auto_reindex` (default: True): Auto-reindex if stale
- `max_age_minutes` (default: 5): Max age before auto-reindex
- `ego_graph_enabled` (default: False): Enable k-hop graph expansion for neighbors
- `ego_graph_k_hops` (default: 2, range: 1-5): Graph traversal depth
- `ego_graph_max_neighbors_per_hop` (default: 10, range: 1-50): Max neighbors per hop
- `include_parent` (default: False): Retrieve enclosing class when matching methods

**Examples**:

```bash
# General search
search_code("authentication handler")

# Filtered search
search_code("OSC message handlers", file_pattern="Scripts/", chunk_type="function")

# Graph-enhanced search with neighbors
search_code("token merging", ego_graph_enabled=True, ego_graph_k_hops=2)
```

**Performance**: Hybrid 68-105ms | Semantic 62-94ms | BM25 3-8ms | Auto 52-57ms

**Result Fields**: `chunk_id`, `kind`, `score`, `blended_score`, `centrality`, `source` (always) | `complexity_score`, `graph`, `reranker_score`, `summary` (optional)

**Result Quality Expectations (SSCG benchmark, 13 hard code-retrieval queries):**

- **Hit Rate@5 = 92.3%** (12/13 queries): Relevant result in top 5 for well-formed queries
- **Recall@4 = 0.89**: ~89% of relevant results surface in top 4
- **Rank-1 accuracy ≈ 69%**: The best result is first ~70% of the time
- **MRR = 0.94**: On average, the best result is very near position 1
- **Action**: Always scan all k results before selecting the one to use or read

### 2. find_connections()

**Purpose**: Find all code connections to a given symbol for dependency and impact analysis

**⚠️ USE THIS FOR**: Caller discovery, dependency tracking, flow tracing, impact assessment

**Key Parameters**:

- `chunk_id` (optional): Direct chunk_id from search results (preferred)
- `symbol_name` (optional): Symbol name to find (may be ambiguous)
- `max_depth` (default: 3, range: 1-5): Max depth for dependency traversal
- `exclude_dirs` (optional): Directories to exclude (e.g., ["tests/"])
- `relationship_types` (optional): Filter to specific types (e.g., ["inherits", "imports"])

**Valid relationship types (21 total)**: `calls`, `inherits`, `uses_type`, `imports`, `decorates`, `raises`, `catches`, `instantiates`, `implements`, `overrides`, `assigns_to`, `reads_from`, `defines_constant`, `defines_enum_member`, `defines_class_attr`, `defines_field`, `uses_constant`, `uses_default`, `uses_global`, `asserts_type`, `uses_context_manager`

**Returns**: Direct/indirect callers, similar code, dependency graph

**Examples**:

```bash
# Using chunk_id (preferred)
find_connections(chunk_id="auth.py:10-50:function:login")

# Filter for only inheritance
find_connections(symbol_name="PythonChunker", relationship_types=["inherits"])

# Deep tracing with custom depth
find_connections(chunk_id="auth.py:10-50:function:login", max_depth=5)
```

**2-Step Workflow**:

```bash
# Step 1: Find the symbol
result = search_code("chunk_file function", chunk_type="function")
chunk_id = result["results"][0]["chunk_id"]

# Step 2: Get all relationships
find_connections(chunk_id=chunk_id, exclude_dirs=["tests/"])
```

### 3. find_path()

**Purpose**: Find shortest path between two code entities in the relationship graph

**⚠️ USE THIS FOR**: Tracing how code element A connects to B, understanding dependency chains, finding call paths

**Key Parameters**:

- `source` / `target` (optional): Symbol names (may be ambiguous)
- `source_chunk_id` / `target_chunk_id` (optional): Chunk IDs (preferred for precision)
- `edge_types` (optional): Filter path to specific relationship types (e.g., ["calls", "inherits"])
- `max_hops` (default: 10, range: 1-20): Maximum path length

**Returns**: Path as sequence of nodes with metadata, edge types traversed, path length. Uses bidirectional BFS for optimal performance.

**Examples**:

```bash
# Using chunk_ids (preferred)
find_path(
    source_chunk_id="auth.py:10-50:function:login",
    target_chunk_id="database.py:100-150:function:query"
)

# Filter by edge types (only calls and imports)
find_path(
    source_chunk_id="main.py:1-50:function:main",
    target_chunk_id="utils.py:10-50:function:helper",
    edge_types=["calls", "imports"]
)
```

---

## 🟢 Other Tools (16 Tools)

**For complete parameter lists, examples, and detailed usage**: See `docs/MCP_TOOLS_REFERENCE.md`

**Project Management**:

- `list_projects()` — Show all indexed projects
- `switch_project(project_path)` — Switch active project
- `get_index_status()` — Check index health
- `index_directory(directory_path, incremental=True)` — Index project (one-time setup)
- `clear_index()` — Delete entire index
- `delete_project(project_path, force=False)` — Safely delete project data

**Search Configuration**:

- `configure_search_mode(search_mode="hybrid", bm25_weight=0.35, dense_weight=0.65)` — Configure search mode
- `get_search_config_status()` — View current config
- `configure_query_routing(enable_multi_model=True, default_model="qwen3", confidence_threshold=0.35)` — Multi-model routing

**Advanced Tools**:

- `find_similar_code(chunk_id, k=4)` — Find functionally similar code
- `configure_reranking(enabled, model_name, top_k_candidates)` — Neural reranking settings
- `configure_chunking(enable_community_detection, community_resolution, ...)` — Chunking settings

**Model Management**:

- `list_embedding_models()` — Show available models (BGE-M3, Qwen3-0.6B, CodeRankEmbed, GTE-ModernBERT, EmbeddingGemma-300m)
- `switch_embedding_model(model_name)` — Change model (instant <150ms if previously used)

**Memory Management**:

- `get_memory_status()` — Check RAM/VRAM usage
- `cleanup_resources()` — Free memory/caches

---

## 🚀 Advanced Features

### Multi-Hop Search (Graph-Aware)

**Purpose**: Discover interconnected code through graph traversal + semantic similarity. Always-on with optimal settings (2 hops, 0.3 expansion, hybrid mode).

**How It Works**: (1) Find chunks matching query with k×2 results, (2) Find graph neighbors via weighted BFS (prioritizes `calls`=1.0 over `imports`=0.3), (3) Find semantically similar chunks, (4) Rerank ALL discovered chunks. Results show `source: "multi_hop"` when discovered via graph.

**Benefit**: 93.3% of queries benefit. Graph traversal finds functionally necessary dependencies that semantic search misses.

### A1: Intent-Adaptive Edge Weights + Semantic Enhancement

**Purpose**: Automatically adjust graph traversal weights and search parameters based on query intent, using a keyword + anchor-embedding ensemble classifier.

**Intent Classification**: System classifies queries into 7 categories. Each intent adjusts both graph edge weights and search parameters:

| Intent | Graph / Parameter Adjustments | Automatic Action |
|--------|-------------------------------|-----------------|
| `local` | `calls`=1.0, `inherits`=1.0, `imports`=0.1 | Standard search (definition lookup) |
| `global` | `imports`=0.7, `uses_type`=0.9, `instantiates`=0.8 | **k expanded** (e.g., 4 → 10) |
| `navigational` | `calls`=1.0, `inherits`=0.9, `imports`=0.5 | Standard search (call chain priority) |
| `path_tracing` | Uniform 0.7 base, `calls`=1.0, `inherits`=0.9 | **Redirects to `find_path()`** |
| `similarity` | `uses_type`=0.9, `decorates`=0.7, `defines_class_attr`=0.7 | **Redirects to `find_similar_code()`** |
| `contextual` | All weights raised to min 0.5 | **ego_graph enabled** |
| `hybrid` | Default weights | Standard search |

**Automatic Tool Routing** (when confidence ≥ `confidence_threshold=0.4`):

- `path_tracing` → `search_code()` is transparently redirected to `find_path()`
- `similarity` → `search_code()` is transparently redirected to `find_similar_code()`
- `global` → k expanded to `suggested_k` for broader coverage
- `contextual` → ego_graph expansion enabled

**Semantic Enhancement** (current config: `semantic_enabled=True`, `semantic_weight=0.3`):

- Classifier blends keyword pattern matching with anchor-embedding cosine similarity
- Ensemble: `0.7 × keyword_score + 0.3 × anchor_embedding_score`
- Anchor queries: 8–10 representative phrases per intent in `config/intent_anchors.yaml`
- Benefit: rescues ambiguous queries that keyword-only scoring leaves as HYBRID
- `confidence_threshold=0.4`: queries below threshold fall back to HYBRID (safe default)
- Embedder cached from previous search — zero startup cost after first query

**Status**: Always-on. Semantic enhancement activates automatically when an embedder is loaded.

### Centrality Reranking

Blends PageRank centrality with semantic similarity: `blended_score = centrality × 0.3 + semantic_score × 0.7`. Functions frequently called/imported rank higher. Always-on when graph data available.

### BM25 Snowball Stemming

Normalizes word forms for better recall (e.g., "indexing"/"indexed"/"index" all match). Benefits 93.3% of queries with 0.47ms overhead. Enabled by default.

### A2/B1: Synthetic Summary Chunks

**A2 (File-Level)**: Generates `chunk_type="module"` synthetic chunks per file with 2+ chunks. Contains classes, functions, imports. ID format: `{path}:0-0:module:{name}`. Score demotion: 0.82-0.90x multiplier.

**B1 (Community-Level)**: Uses Louvain detection to generate `chunk_type="community"` synthetic chunks per community with 2+ members. Contains thematic groupings across files. ID format: `__community__/{label}:0-0:community:{label}`. Score demotion: 0.9-0.95x multiplier.

Both enabled by default, controlled via `configure_chunking(enable_file_summaries, enable_community_summaries)`. Excluded from call graph.

---

## 🔧 Troubleshooting

| Issue | Solution |
|-------|----------|
| **No results** | Check project context: `list_projects()`, `switch_project()` if needed. Verify index: `get_index_status()`. Re-index if stale: `index_directory(project_path)` |
| **Bad results** | Try different search mode (hybrid → semantic → BM25). Adjust weights: `configure_search_mode("hybrid", 0.7, 0.3)` for exact matching. Use filters: `file_pattern`, `chunk_type`. Increase k: `k=10` |
| **Wrong result at rank-1** | Scan all k results — answer is likely at rank 2-4. Module/summary chunks may outrank specific implementations. Use `chunk_type` filter to exclude module chunks if needed. |
| **Too slow** | Use BM25 mode for exact symbols (3-8ms). Check GPU: `get_memory_status()`. Cleanup: `cleanup_resources()`. Reduce k: `k=3` |
| **Memory issues** | Monitor: `get_memory_status()`. Cleanup: `cleanup_resources()`. Switch to smaller model: `switch_embedding_model("google/embeddinggemma-300m")` |

---

## 📖 Complete Documentation

**For full API reference, all parameters, detailed examples, and advanced configuration**:

- `docs/MCP_TOOLS_REFERENCE.md` — Complete 19-tool API reference
- `docs/ADVANCED_FEATURES_GUIDE.md` — Multi-hop, routing, models, graph search
- `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md` — Search modes, weights, optimization
