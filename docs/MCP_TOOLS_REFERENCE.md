# MCP Tools Reference

## Quick Integration Guide

This modular reference can be embedded in any project instructions for Claude Code integration.

---

## Available MCP Tools (14)

| Tool | Priority | Purpose | Parameters |
|------|----------|---------|------------|
| **search_code** | 🔴 **ESSENTIAL** | Find code with natural language + intelligent model routing | query (required), k=5, search_mode="auto", model_key, use_routing=True, file_pattern, chunk_type, include_context=True, auto_reindex=True, max_age_minutes=5 |
| **index_directory** | 🔴 **SETUP** | Index project (multi-model support) | directory_path (required), project_name, incremental=True, multi_model=auto |
| find_similar_code | Secondary | Find alternative implementations | chunk_id (required), k=5 |
| configure_search_mode | Config | Set search mode & weights | search_mode="hybrid", bm25_weight=0.4, dense_weight=0.6, enable_parallel=True |
| configure_query_routing | Config | Configure multi-model routing (v0.5.4+) | enable_multi_model, default_model, confidence_threshold=0.05 |
| get_search_config_status | Config | View current configuration | *(no parameters)* |
| get_index_status | Status | Check index health & model info | *(no parameters)* |
| get_memory_status | Monitor | Check RAM/VRAM usage | *(no parameters)* |
| list_projects | Management | Show indexed projects grouped by path | *(no parameters)* |
| switch_project | Management | Change active project | project_path (required) |
| clear_index | Reset | Delete current index (all dimensions) | *(no parameters)* |
| cleanup_resources | Cleanup | Free memory/caches (GPU + index) | *(no parameters)* |
| list_embedding_models | Model | View available embedding models | *(no parameters)* |
| switch_embedding_model | Model | Switch embedding model (instant <150ms) | model_name (required) |

---

## Essential Workflow

```
1. index_directory("C:\path\to\project")   # One-time setup
2. search_code("what you need")             # Find code instantly
3. Read tool ONLY after search              # Edit specific files
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

## Performance Metrics

| Metric | Traditional Reading | Semantic Search | Improvement |
|--------|---------------------|-----------------|-------------|
| Tokens | 5,600 | 400 | 93% reduction |
| Speed | 30-60s | 3-5s | 10x faster |
| Accuracy | Hit-or-miss | Targeted | Precision |

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

## Multi-Model Batch Indexing

**Feature**: Automatically index projects with all models in the pool (Qwen3, BGE-M3, CodeRankEmbed)

**Status**: ✅ **Production-Ready** (auto-enabled when `CLAUDE_MULTI_MODEL_ENABLED=true`)

### How It Works

When multi-model mode is enabled, `index_directory` automatically indexes with **all 3 models** sequentially:

1. **Qwen3-0.6B** (1024d) - Best for implementation & algorithms
2. **BGE-M3** (1024d) - Best for workflow & configuration
3. **CodeRankEmbed** (768d) - Best for specialized algorithms

### Parameters

- `directory_path` (string, required): Absolute path to project root
- `project_name` (string, optional): Custom name (defaults to directory name)
- `incremental` (boolean, default: true): Use incremental indexing if snapshot exists
- `multi_model` (boolean, default: auto): Index for all models
  - `null` (default): Auto-detect from `CLAUDE_MULTI_MODEL_ENABLED`
  - `true`: Force multi-model indexing (all 3 models)
  - `false`: Force single-model indexing (current model only)

### Usage Examples

**Automatic Multi-Model** (default when multi-model enabled):
```bash
/index_directory "C:\Projects\MyProject"
# Indexes with all 3 models automatically
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
- ❌ **NEVER** read files without searching first
- ❌ **NEVER** use `Glob()` or `grep` for code exploration

**Every file read without search wastes 1,000+ tokens**

---

## Supported Features

- **Languages**: Python, JS, TS, Java, Go, Rust, C, C++, C#, GLSL, Svelte (22 extensions)
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

**Savings**: 93% token reduction + 10x speed increase

---

## End of Modular Reference

This reference is maintained in: `docs/MCP_TOOLS_REFERENCE.md`

For full documentation, see project `CLAUDE.md` and `README.md`
