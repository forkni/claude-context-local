# MCP Tools Reference

## Quick Integration Guide

This modular reference can be embedded in any project instructions for Claude Code integration.

---

## Available MCP Tools (12)

| Tool | Priority | Purpose | Parameters |
|------|----------|---------|------------|
| **search_code** | 🔴 **ESSENTIAL** | Find code with natural language | query, k=5, search_mode, file_pattern, chunk_type |
| **index_directory** | 🔴 **SETUP** | Index project (one-time) | directory_path, project_name, incremental=True |
| find_similar_code | Secondary | Find alternative implementations | chunk_id, k=5 |
| configure_search_mode | Config | Set search mode & weights | search_mode, bm25_weight=0.4, dense_weight=0.6 |
| get_search_config_status | Config | View current configuration | *(no parameters)* |
| get_index_status | Status | Check index health | *(no parameters)* |
| get_memory_status | Monitor | Check RAM/VRAM usage | *(no parameters)* |
| list_projects | Management | Show indexed projects | *(no parameters)* |
| switch_project | Management | Change active project | project_path |
| clear_index | Reset | Delete current index | *(no parameters)* |
| cleanup_resources | Cleanup | Free memory/caches | *(no parameters)* |
| run_benchmark | Testing | Validate search quality | benchmark_type, project_path, max_instances=3 |

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

# Benchmark performance
/run_benchmark "token-efficiency"
/run_benchmark "method-comparison" "."
```

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
.\scripts\powershell\configure_claude_code.ps1 -Global

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
- [ ] Benchmark run to validate performance

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
