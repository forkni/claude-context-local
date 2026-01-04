# CLAUDE.md Template for Your Projects

This template helps you set up a `CLAUDE.md` file in your project to maximize efficiency when using Claude Code with the semantic code search MCP server.

## Why Use CLAUDE.md?

- **63% Token Reduction**: Real-world efficiency with mixed approach (benchmarked)
- **2x Faster**: Mixed approach (8 min) vs traditional (15 min) - validated benchmark
- **Immediate Access**: MCP tools visible to Claude without explaining each time
- **Project-Specific**: Customize instructions for your codebase

## Minimal Template

Create a `CLAUDE.md` file in your project root with this content:

```markdown
# Project Instructions for Claude Code

## 🔴 CRITICAL: Search-First Protocol

**MANDATORY**: For ALL codebase tasks, ALWAYS use semantic search FIRST before reading files.

### Workflow Sequence

1. **Index**: `/index_directory "C:\path\to\your\project"` - One-time setup
2. **Search**: `/search_code "natural language query"` - Find code instantly
3. **Edit**: Use `Read` tool ONLY after search identifies exact file

### Performance Impact

| Method | Tokens/Query | Speed | Result |
|--------|--------------|-------|--------|
| Traditional file reading | 19,524 tokens | 36s | Limited context |
| Mixed approach (MCP + tools) | 7,200 tokens | 19s | Precision targeting |
| **Token savings** | **63%** | **1.9x faster** | **Cross-file relationships** |

### Critical Rules

- ✅ **ALWAYS**: `search_code()` for exploration/understanding
- ✅ **ALWAYS**: Index before searching: `index_directory(path)`
- ❌ **NEVER**: Read files without searching first
- ❌ **NEVER**: Use `Glob()` for code exploration
- ❌ **NEVER**: Grep manually for code patterns

**Every file read without search wastes 1,000+ tokens**

---

## Available MCP Tools (18)

| Tool | Priority | Purpose |
|------|----------|---------|
| **search_code** | 🔴 **ESSENTIAL** | Find code with natural language |
| **index_directory** | 🔴 **SETUP** | Index project (one-time) |
| **find_connections** | 🟡 **IMPACT** | Analyze code dependencies |
| find_similar_code | Secondary | Find alternative implementations |
| configure_search_mode | Config | Set search mode (hybrid/semantic/BM25) |
| configure_query_routing | Config | Configure multi-model routing |
| configure_reranking | Config | Configure neural reranking |
| get_search_config_status | Config | View current search configuration |
| list_embedding_models | Config | List available models |
| switch_embedding_model | Config | Switch between models |
| get_index_status | Status | Check index health |
| get_memory_status | Monitor | Check RAM/VRAM usage |
| list_projects | Management | Show indexed projects |
| switch_project | Management | Change active project |
| clear_index | Reset | Delete current index |
| delete_project | Management | Safely delete indexed project |
| cleanup_resources | Cleanup | Free memory/caches |

### Quick Examples

```bash
# Essential workflow
/index_directory "C:\Projects\MyApp"
/search_code "authentication functions"
/search_code "error handling patterns"

# Advanced usage
/find_similar_code "auth.py:15-42:function:login"
/configure_search_mode "hybrid" 0.4 0.6
/get_index_status
```

### Search Modes

- **hybrid** (default) - BM25 + semantic fusion (best accuracy)
- **semantic** - Dense vector search only (best for concepts)
- **bm25** - Sparse keyword search only (best for exact terms)
- **auto** - Adaptive mode selection

---

📚 **Full Tool Reference**: See [docs/MCP_TOOLS_REFERENCE.md](https://github.com/forkni/claude-context-local/blob/main/docs/MCP_TOOLS_REFERENCE.md) for complete documentation with all parameters and examples.

```

## Customization Tips

1. **Copy the Template**: Save the content above to `CLAUDE.md` in your project root
2. **Adjust Paths**: Update the `index_directory` path to match your project
3. **Add Project Rules**: Include project-specific coding conventions, architecture notes, or common patterns
4. **Use Full Reference**: For complete tool documentation, copy content from `docs/MCP_TOOLS_REFERENCE.md`

## How It Works

- Claude Code automatically reads `CLAUDE.md` from your project directory
- Instructions apply to all Claude sessions in that project
- MCP tools are immediately available without explanation
- Search-first workflow becomes automatic

## Example Projects

This repository's own `CLAUDE.md` demonstrates advanced usage with:
- Comprehensive MCP tool documentation
- Project-specific architecture notes
- Model selection guidance
- Testing and benchmarking instructions

> **Note**: The `CLAUDE.md` in this repository is project-specific. Use the minimal template above for your own projects, then customize as needed.

## See Also

- [MCP Tools Reference](MCP_TOOLS_REFERENCE.md) - Complete MCP tools documentation
- [Installation Guide](INSTALLATION_GUIDE.md) - Setup instructions
- [Advanced Features Guide](ADVANCED_FEATURES_GUIDE.md) - Advanced search features
