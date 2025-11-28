# Claude Context Local

```
 ██████╗ ██╗      █████╗ ██╗   ██╗██████╗ ███████╗
██╔════╝ ██║     ██╔══██╗██║   ██║██╔══██╗██╔════╝
██║      ██║     ███████║██║   ██║██║  ██║█████╗
██║      ██║     ██╔══██║██║   ██║██║  ██║██╔══╝
╚██████╗ ███████╗██║  ██║╚██████╔╝██████╔╝███████╗

 ██████╗ ██████╗ ███╗   ██╗████████╗███████╗██╗  ██╗████████╗
██╔════╝██╔═══██╗████╗  ██║╚══██╔══╝██╔════╝╚██╗██╔╝╚══██╔══╝
██║     ██║   ██║██╔██╗ ██║   ██║   █████╗   ╚███╔╝    ██║
██║     ██║   ██║██║╚██╗██║   ██║   ██╔══╝   ██╔██╗    ██║
╚██████╗╚██████╔╝██║ ╚████║   ██║   ███████╗██╔╝ ██╗   ██║

██╗      ██████╗  ██████╗ █████╗ ██╗
██║     ██╔═══██╗██╔════╝██╔══██╗██║
██║     ██║   ██║██║     ███████║██║
██║     ██║   ██║██║     ██╔══██║██║
███████╗╚██████╔╝╚██████╗██║  ██║███████╗
```

**Local-first semantic code search for Claude Code.** Hybrid search combining semantic understanding with text matching, running 100% locally using EmbeddingGemma or BGE-M3. No API keys, no costs, your code never leaves your machine.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

## Highlights

- **Hybrid Search**: BM25 + semantic fusion (44.4% precision, 100% MRR) - [benchmarks](docs/BENCHMARKS.md)
- **93-97% Token Reduction**: Semantic search vs traditional file reading - [performance analysis](docs/BENCHMARKS.md)
- **Multi-Model Routing**: Intelligent query routing (Qwen3, BGE-M3, CodeRankEmbed) with 100% accuracy - [advanced features](docs/ADVANCED_FEATURES_GUIDE.md)
- **19 File Extensions**: Python, JS, TS, Go, Rust, C/C++, C#, GLSL with AST/tree-sitter chunking
- **15 MCP Tools**: Complete Claude Code integration - [tool reference](docs/MCP_TOOLS_REFERENCE.md)

**Status**: ✅ Production-ready | 352 passing tests | All 15 MCP tools operational | Windows 10/11

## Quick Start

### 1. Install

```powershell
# Clone repository
git clone https://github.com/forkni/claude-context-local.git
cd claude-context-local

# Run installer (auto-detects CUDA)
install-windows.cmd

# Verify installation
verify-installation.cmd
```

**Installer features**: Smart CUDA detection, one-click setup, dependency verification.

> **Note**: HuggingFace authentication required. Get your token at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 2. Configure Claude Code

```powershell
# Register MCP server with Claude Code
.\scripts\batch\manual_configure.bat
```

### 3. Start the MCP Server

```powershell
# Interactive menu with 7 options
start_mcp_server.cmd

# Or use direct launchers:
scripts\batch\start_mcp_debug.bat   # Debug mode
scripts\batch\start_mcp_simple.bat  # Simple mode
```

**Menu options**: Quick start server (SSE), project management (index/reindex), search configuration, advanced tools.

### 4. Use in Claude Code

```bash
# Index your project (one-time)
/index_directory "C:\path\to\your\project"

# Search with natural language
/search_code "authentication functions"
/search_code "error handling patterns"
/search_code "database connection setup"

# Check status
/get_index_status
/get_memory_status
```

**That's it!** You're now searching your code semantically with 93-97% fewer tokens.

## Core Usage

### Index Project

```bash
# Index new project
/index_directory "C:\Projects\MyApp"

# Re-index (incremental, fast)
start_mcp_server.cmd → 2 (Project Management) → 2 (Re-index)

# Force full reindex
start_mcp_server.cmd → 2 (Project Management) → 3 (Force Reindex)
```

### Search Code

```bash
# Natural language queries
/search_code "user authentication logic"
/search_code "error handling try except"
/search_code "async database queries"

# With filters
/search_code "auth handler" --exclude_dirs '["tests/", "vendor/"]'

# Find similar code
/find_similar_code "auth.py:15-42:function:login"

# Analyze dependencies
/find_connections "utils.py:50-100:function:process_data"
```

### Configure Search

```bash
# Set hybrid mode (recommended)
/configure_search_mode "hybrid" 0.4 0.6

# Check configuration
/get_search_config_status

# Switch models
/switch_embedding_model "BAAI/bge-m3"
```

## Search Modes

| Mode | Description | Performance | Quality | Status |
|------|-------------|-------------|---------|--------|
| **hybrid** (default) | BM25 + Semantic fusion | 487ms | 44.4% precision, 100% MRR | ✅ Operational |
| **semantic** | Dense vector search | 487ms | 38.9% precision, 100% MRR | ✅ Operational |
| **bm25** | Text-based sparse search | 162ms | 33.3% precision, 61.1% MRR | ✅ Operational |
| **auto** | Adaptive mode selection | Adaptive | Context-dependent | ✅ Operational |

**Configuration**: See [Hybrid Search Configuration Guide](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md)

## Available MCP Tools

### Core Search

- `/search_code` - Main semantic/hybrid search
- `/index_directory` - Index project for searching
- `/find_similar_code` - Find code similar to chunk
- `/find_connections` - Dependency & impact analysis

### Configuration

- `/configure_search_mode` - Set hybrid search parameters
- `/configure_query_routing` - Configure multi-model routing
- `/get_search_config_status` - View current configuration
- `/list_embedding_models` - List available models
- `/switch_embedding_model` - Switch between models

### Management

- `/get_index_status` - Check index statistics
- `/get_memory_status` - Monitor RAM/VRAM usage
- `/cleanup_resources` - Free memory and caches
- `/clear_index` - Reset search index
- `/list_projects` - List indexed projects
- `/switch_project` - Switch between projects

**Complete reference**: [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md)

## Supported Languages

| Language | Extensions | Parser |
|----------|------------|--------|
| Python | `.py` | AST |
| JavaScript | `.js` | Tree-sitter |
| TypeScript | `.ts`, `.tsx` | Tree-sitter |
| Go | `.go` | Tree-sitter |
| Rust | `.rs` | Tree-sitter |
| C | `.c` | Tree-sitter |
| C++ | `.cpp`, `.cc`, `.cxx`, `.c++` | Tree-sitter |
| C# | `.cs` | Tree-sitter |
| GLSL | `.glsl`, `.frag`, `.vert`, `.comp`, `.geom`, `.tesc`, `.tese` | Tree-sitter |

**Total**: 19 file extensions across 9 programming languages

## Requirements

- **Python**: 3.11+ (tested with 3.11 and 3.12)
- **RAM**: 4GB minimum (8GB+ recommended for large codebases)
- **Disk**: 2-4GB free space (model cache + embeddings)
  - EmbeddingGemma: ~1.2GB
  - BGE-M3: ~2.2GB (optional)
- **Windows**: Windows 10/11 with PowerShell
- **PyTorch**: 2.6.0+ (auto-installed with CUDA 11.8/12.4/12.6 support)
- **GPU** (optional): NVIDIA GPU with CUDA for 8.6x faster indexing

Everything works on CPU if GPU unavailable.

## Configuration

### Environment Variables

```bash
# Storage directory (default: ~/.claude_code_search)
set CODE_SEARCH_STORAGE=C:\custom\path

# Embedding model
set CLAUDE_EMBEDDING_MODEL=BAAI/bge-m3  # or google/embeddinggemma-300m

# Search mode
set CLAUDE_SEARCH_MODE=hybrid  # or semantic, bm25, auto

# Multi-model routing
set CLAUDE_MULTI_MODEL_ENABLED=true
```

### Model Selection

| Model | Dimensions | VRAM | Best For |
|-------|------------|------|----------|
| **EmbeddingGemma-300m** (default) | 768 | 4-8GB | Fast, efficient, smaller projects |
| **BGE-M3** | 1024 | 8-16GB | Higher accuracy (+13.6% F1), production |
| **Qwen3-0.6B** | 1024 | 2.3GB | Routing pool, high efficiency |
| **CodeRankEmbed** | 768 | 2GB | Code-specific retrieval |

**Instant model switching**: <150ms with per-model index storage - no re-indexing needed!

**See also**: [Model Migration Guide](docs/MODEL_MIGRATION_GUIDE.md), [Advanced Features](docs/ADVANCED_FEATURES_GUIDE.md#multi-model-query-routing)

## Architecture

```
claude-context-local/
├── chunking/          # Multi-language AST/tree-sitter parsing
├── embeddings/        # Model loading & embedding generation
├── search/            # FAISS + BM25 hybrid search
├── merkle/            # Incremental indexing with change detection
├── graph/             # Call graph extraction & analysis
├── mcp_server/        # MCP server implementation (15 tools)
├── tools/             # Interactive indexing & search utilities
├── scripts/           # Installation & configuration
├── docs/              # Complete documentation
└── tests/             # 352 passing tests (unit + integration)
```

**Storage** (~/.claude_code_search):

- `models/` - Downloaded embedding models
- `index/` - FAISS indices + metadata (SQLite)
- `merkle/` - Incremental indexing snapshots

**Complete architecture**: [Architecture Documentation](docs/ADVANCED_FEATURES_GUIDE.md)

## Troubleshooting

### Quick Diagnostics

```powershell
# Comprehensive system check
verify-installation.cmd

# Repair common issues
scripts\batch\repair_installation.bat
```

### Common Issues

1. **"No changes detected" but files modified**: Run force reindex or clear Merkle snapshots via repair tool
2. **Model download fails**: Check internet, disk space (2GB+), and HuggingFace authentication
3. **MCP tools not visible**: Run `.\scripts\batch\manual_configure.bat` to register server
4. **CUDA out of memory**: System auto-falls back to CPU (slower but functional)

**Complete troubleshooting guide**: [Installation Guide - Troubleshooting](docs/INSTALLATION_GUIDE.md#troubleshooting)

## Documentation

### Essential Guides

- [Installation Guide](docs/INSTALLATION_GUIDE.md) - Setup, configuration, troubleshooting
- [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md) - Complete tool documentation
- [Advanced Features Guide](docs/ADVANCED_FEATURES_GUIDE.md) - Multi-model routing, graph search, optimization
- [CLAUDE.md Template](docs/CLAUDE_MD_TEMPLATE.md) - Project setup template

### Configuration & Performance

- [Hybrid Search Configuration](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md) - Search modes and tuning
- [Model Migration Guide](docs/MODEL_MIGRATION_GUIDE.md) - Switching embedding models
- [Benchmarks](docs/BENCHMARKS.md) - Performance metrics and comparisons

### Development

- [Testing Guide](tests/TESTING_GUIDE.md) - Running tests (352 passing)
- [Git Workflow](docs/GIT_WORKFLOW.md) - Contributing guidelines
- [Version History](docs/VERSION_HISTORY.md) - Changelog

**Complete index**: [Documentation Index](docs/DOCUMENTATION_INDEX.md)

## Contributing

This is a research project focused on intelligent code chunking and search. Feel free to experiment with:

- Different chunking strategies
- Alternative embedding models
- Enhanced metadata extraction
- Performance optimizations

See [Git Workflow](docs/GIT_WORKFLOW.md) for contribution guidelines.

## License

Licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Inspiration

This Windows-focused fork was adapted from [FarhanAliRaza/claude-context-local](https://github.com/FarhanAliRaza/claude-context-local), which provides cross-platform support for Linux and macOS.

Both projects draw inspiration from [zilliztech/claude-context](https://github.com/zilliztech/claude-context).
