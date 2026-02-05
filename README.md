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

**Local-first semantic code search for Claude Code.** Hybrid search combining semantic understanding with text matching, running 100% locally with multi-model routing (Qwen3, BGE-M3, CodeRankEmbed). No API keys, no costs, your code never leaves your machine.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)

## Highlights

- **Hybrid Search**: BM25 + semantic fusion (44.4% precision, 100% MRR) - [benchmarks](docs/BENCHMARKS.md)
- **Neural Reranking**: Cross-encoder model (BAAI/bge-reranker-v2-m3) improves ranking quality by 5-15% - [advanced features](docs/ADVANCED_FEATURES_GUIDE.md#neural-reranking-configuration)
- **63% Token Reduction**: Real-world benchmarked mixed approach - [benchmarks](docs/BENCHMARKS.md)
- **Multi-Model Routing**: Intelligent query routing (Qwen3, BGE-M3, CodeRankEmbed) with 100% accuracy - [advanced features](docs/ADVANCED_FEATURES_GUIDE.md)
- **19 File Extensions**: Python, JS, TS, Go, Rust, C/C++, C#, GLSL with AST/tree-sitter chunking
- **18 MCP Tools**: Complete Claude Code integration - [tool reference](docs/MCP_TOOLS_REFERENCE.md)

**Status**: ✅ Production-ready | 1,068+ passing tests | All 19 MCP tools operational | Windows 10/11

## Quick Start

### 1. Install

```
git clone https://github.com/forkni/claude-context-local.git
cd claude-context-local
```

Double-click `install-windows.cmd` and follow the prompts:

1. **System Detection** - Automatic Python and CUDA/GPU detection
2. **Installation** - Select "Auto-Install" (recommended)
3. **HuggingFace Token** - Enter your token when prompted ([get token](https://huggingface.co/settings/tokens))
4. **Claude Code Setup** - Automatic MCP server registration

### 2. Index Your Project

**Option A: Via UI Menu** (recommended for first-time setup)

Double-click `start_mcp_server.cmd` and select **4. Project Management**:

```
=== Project Management ===

  1. Index New Project       ← Select this
  2. Re-index Existing Project
  3. Force Re-index Project
  4. List Indexed Projects
  ...
```

Enter your project path when prompted (e.g., `C:\Projects\MyApp`).

**Option B: Via Claude Code** (after loading `/mcp-search` skill)

Simply ask Claude naturally:

```
"Index my project at C:\Projects\MyApp"
```

Claude will use the MCP tools internally to index your project.

### 3. Start Server

Return to main menu and select **1. Quick Start Server**:

```
=== Claude Context MCP Server Launcher ===

  1. Quick Start Server      ← Select this
  2. Installation & Setup
  3. Search Configuration
  ...
```

### 4. Connect in Claude Code

After the server starts, connect in Claude Code:

1. Type `/mcp` in Claude Code
2. Select **Reconnect** next to `code-search`
3. Wait for "Connected" confirmation

### 5. Load MCP Search Context

**IMPORTANT**: Run this command at the beginning of each session to load optimal search workflows:

```
/mcp-search
```

This command loads the [mcp-search-tool](.claude/skills/mcp-search-tool/SKILL.md) skill, which provides Claude with:

- Complete MCP tool reference (all 18 tools)
- Search-first protocol enforcement
- 2-step workflow for relationship queries (search → find_connections)
- Project context validation before searches
- 40-45% additional token savings through optimal tool usage

> **Tip**: Running `/mcp-search` ensures Claude uses semantic search efficiently and follows best practices for token optimization.

### 6. Start Searching

Simply ask Claude Code natural questions about your codebase:

- "Find authentication functions in my project"
- "Show me error handling patterns"
- "Where is the database connection setup?"

Claude Code will automatically use the MCP tools internally to find relevant code.

> **Note**: The `/mcp-search` skill must be loaded first (step 5 above). MCP tools like `search_code` and `find_connections` are not exposed as direct slash commands - they are called internally by Claude when you ask natural language questions.

**That's it!** You're now searching your code semantically with up to 63% fewer tokens (real-world benchmarked).

## How It Works

### Claude Code Integration

> **Note**: This is an MCP server designed exclusively for Claude Code integration. It is not a standalone search tool - it requires connection via Claude Code's `/mcp` command.

When connected via `/mcp` → Reconnect, Claude Code gains access to 18 semantic search tools exposed as `mcp__code-search__*` functions.

A [**SKILL.md**](.claude/skills/mcp-search-tool/SKILL.md) file in the repository provides Claude with workflow guidance for optimal tool usage, including project context validation and search mode selection.

### Natural Language Queries

Simply ask questions about your code. Claude Code automatically selects and uses the appropriate MCP tools:

| Your Question | Claude Code Uses |
|---------------|------------------|
| "Find authentication functions" | `search_code("authentication functions")` |
| "What calls the login function?" | `find_connections(symbol_name="login")` |
| "Show similar code to this handler" | `find_similar_code(chunk_id)` |

> **Tip: Forcing MCP Tool Usage**
>
> If Claude doesn't automatically use the search tools, include these phrases:
>
> - "Use the **code-search MCP tools** to find..."
> - "**Search the indexed codebase** for..."
> - "Use **semantic search** to locate..."
> - "**Query the code index** for..."
>
> Example: "Use the code-search MCP tools to find all error handling patterns"

## Core Usage

### Index Project

Ask Claude Code to index your project:

- "Index the project at C:\Projects\MyApp"
- "Re-index the current project to pick up new changes"

Or use the interactive menu:

```bash
start_mcp_server.cmd → 4 (Project Management)
  → 1 (Index New Project) or 2 (Re-index Existing) or 3 (Force Re-index)
```

### Search Code

Ask Claude Code naturally:

- "Find the user authentication logic in my code"
- "Show me all error handling patterns with try except"
- "Where are the async database queries defined?"

For precise control with filters:

- "Search for auth handlers excluding the tests and vendor directories"
- "Find similar code to the login function in auth.py"

To analyze dependencies:

- "What code depends on the process_data function in utils.py?"
- "Show me all functions that call the login handler"

### Configure Search

Ask Claude Code to adjust settings:

- "Configure search mode to hybrid with 0.4 BM25 and 0.6 dense weights"
- "Show me the current search configuration"
- "Switch the embedding model to BGE-M3"

Or use the interactive menu:

```bash
start_mcp_server.cmd → 3 (Search Configuration)
```

## Search Modes

| Mode | Description | Performance | Quality | Status |
|------|-------------|-------------|---------|--------|
| **hybrid** (default) | BM25 + Semantic fusion | 487ms | 44.4% precision, 100% MRR | ✅ Operational |
| **semantic** | Dense vector search | 487ms | 38.9% precision, 100% MRR | ✅ Operational |
| **bm25** | Text-based sparse search | 162ms | 33.3% precision, 61.1% MRR | ✅ Operational |

**Configuration**: See [Hybrid Search Configuration Guide](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md)

## MCP Tool Reference (For Claude Code)

These tools are available to Claude Code as `mcp__code-search__*` functions. You don't invoke them directly - Claude Code uses them automatically when you ask relevant questions. The [SKILL.md](.claude/skills/mcp-search-tool/SKILL.md) file guides Claude's tool usage for optimal results.

### Core Search

- `search_code` - Main semantic/hybrid search
- `index_directory` - Index project for searching
- `find_similar_code` - Find code similar to chunk
- `find_connections` - Dependency & impact analysis

### Configuration

- `configure_search_mode` - Set hybrid search parameters
- `configure_query_routing` - Configure multi-model routing
- `configure_reranking` - Configure neural reranking
- `get_search_config_status` - View current configuration
- `list_embedding_models` - List available models
- `switch_embedding_model` - Switch between models

### Management

- `get_index_status` - Check index statistics
- `get_memory_status` - Monitor RAM/VRAM usage
- `cleanup_resources` - Free memory and caches
- `clear_index` - Reset search index
- `delete_project` - Safely delete indexed project
- `list_projects` - List indexed projects
- `switch_project` - Switch between projects

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

### Interactive Configuration

Run `start_mcp_server.cmd` and select **3. Search Configuration**:

```
=== Search Configuration ===

  1. View Current Configuration       - Show all active settings
  2. Search Mode Configuration        - Mode, weights, parallel search
  3. Select Embedding Model           - Choose model by VRAM (BGE-M3/Qwen3)
  4. Configure Neural Reranker        - Cross-encoder reranking (+5-15% quality)
  5. Entity Tracking Configuration    - Symbol tracking, import/class context
  6. Configure Chunking Settings      - Greedy merge, AST splitting (+4.3 Recall@5)
  9. Reset to Defaults                - Restore optimal default settings
```

#### 1. View Current Configuration

Displays all current settings including model, search mode, weights, GPU status, and feature flags.

#### 2. Set Search Mode

| Mode | Description |
|------|-------------|
| **hybrid** (default) | BM25 + semantic fusion - best accuracy |
| **semantic** | Dense vector search only - conceptual queries |
| **bm25** | Text-based search only - exact matches, fastest |

#### 3. Configure Search Weights

Adjust the balance between text matching and semantic understanding:

- **BM25 Weight**: 0.0-1.0 (default: 0.4) - keyword/text matching strength
- **Dense Weight**: 0.0-1.0 (default: 0.6) - semantic understanding strength

Weights should sum to 1.0.

#### 4. Select Embedding Model

| Model | VRAM | Best For |
|-------|------|----------|
| **BGE-M3** | 1-1.5GB | Production, hybrid search (recommended) |
| **Qwen3-0.6B** | 2.3GB | High efficiency, excellent value |
| **EmbeddingGemma-300m** | 4-8GB | Fast, lightweight (default) |
| **Multi-Model Routing** | 5.3GB | Auto-routes to optimal model |

**Instant switching**: <150ms with no re-indexing required.

#### 5. Configure Parallel Search

Enable/disable parallel execution of BM25 and semantic search:

- **Enabled** (default): ~15-30ms faster, higher CPU usage
- **Disabled**: Sequential execution, lower resource usage

#### 6. Configure Neural Reranker

Cross-encoder model that re-scores results for 15-25% quality improvement:

- **Enable/Disable**: Requires GPU with ≥6GB VRAM
- **Top-K Candidates**: Number of results to rerank (default: 50, range: 5-100)

#### 7. Configure Entity Tracking

Extract additional code relationships during indexing:

- **Enabled**: Tracks enum members, default values, context managers (~25% slower indexing)
- **Disabled** (default): Core relationships only (inheritance, imports, decorators)

#### 8. Reset to Defaults

Resets all settings to: hybrid mode, 0.4/0.6 weights, multi-model enabled, GPU auto-detect.

### Quick Access Options

From the main menu:

- **M - Quick Model Switch**: Fast model switching without entering submenu
- **F - Configure Output Format**: Control token usage (verbose/compact/ultra)

### Environment Variables (Advanced)

For automation and CI/CD, settings can be overridden via environment variables. See [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md) for complete list.

### Model Selection

| Model | Dimensions | VRAM | Best For |
|-------|------------|------|----------|
| **EmbeddingGemma-300m** (default) | 768 | 4-8GB | Fast, efficient, smaller projects |
| **BGE-M3** | 1024 | 8-16GB | Higher accuracy (+13.6% F1), production |
| **Qwen3-0.6B** | 1024 | 2.3GB | Routing pool, high efficiency |
| **CodeRankEmbed** | 768 | 2GB | Code-specific retrieval |

**Instant model switching**: <150ms with per-model index storage - no re-indexing needed!

**See also**: [Advanced Features](docs/ADVANCED_FEATURES_GUIDE.md#multi-model-query-routing)

## Architecture

```
claude-context-local/
├── chunking/          # Multi-language AST/tree-sitter parsing
├── embeddings/        # Model loading & embedding generation
├── search/            # FAISS + BM25 hybrid search
├── merkle/            # Incremental indexing with change detection
├── graph/             # Call graph extraction & analysis
├── mcp_server/        # MCP server implementation (18 tools)
├── tools/             # Interactive indexing & search utilities
├── scripts/           # Installation & configuration
├── docs/              # Complete documentation
└── tests/             # 1,068+ tests (unit + integration)
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

# Verify HuggingFace authentication
verify-hf-auth.cmd

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
- [CLAUDE.md Template](docs/CLAUDE_MD_TEMPLATE.md) - **Setup guide for your projects** (see below)

### Configuration & Performance

- [Hybrid Search Configuration](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md) - Search modes and tuning
- [Benchmarks](docs/BENCHMARKS.md) - Real-world performance metrics (63% token reduction)

### Using CLAUDE.md Template in Your Projects

The [CLAUDE.md Template](docs/CLAUDE_MD_TEMPLATE.md) helps you set up semantic search in your own projects:

**Quick Setup**:

1. Copy template content from [docs/CLAUDE_MD_TEMPLATE.md](docs/CLAUDE_MD_TEMPLATE.md)
2. Create `CLAUDE.md` in your project root
3. Update the `index_directory` path to match your project
4. Claude Code automatically reads `CLAUDE.md` when you open that project

**Benefits**:

- **63% token reduction** through enforced search-first workflow
- **Immediate MCP tool access** without explaining tools each session
- **Project-specific instructions** for your codebase conventions
- **Automatic context loading** for all team members

**Customization**:

- Add project-specific coding conventions
- Include architecture notes
- Document common patterns
- Specify preferred search modes

> **See**: [docs/CLAUDE_MD_TEMPLATE.md](docs/CLAUDE_MD_TEMPLATE.md) for complete template and usage examples

### Development

- [Testing Guide](tests/TESTING_GUIDE.md) - Running tests (1,068+ passing)
- [Git Workflow](docs/GIT_WORKFLOW.md) - Contributing guidelines
- [Version History](docs/VERSION_HISTORY.md) - Changelog

**Complete index**: [Documentation Index](docs/DOCUMENTATION_INDEX.md)

## Contributing

Contributions welcome! Quick start:

1. Fork and clone the repository
2. Install: `install-windows.cmd` or `pip install -e .[dev,test]`
3. Run tests: `pytest tests/ -v`
4. Create a branch from `development`
5. Submit PR to `development` branch

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

Licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Inspiration & Acknowledgments

This project draws inspiration from several excellent semantic code search implementations:

| Project | Author | Key Contribution |
|---------|--------|------------------|
| [claude-context](https://github.com/zilliztech/claude-context) | Zilliz | Original concept, cloud-based architecture, hybrid search with Milvus |
| [claude-context-local](https://github.com/FarhanAliRaza/claude-context-local) | Farhan Ali Raza | Local-first approach, cross-platform support |
| [chunkhound](https://github.com/chunkhound/chunkhound) | ChunkHound | Real-time indexing with watchdog, extensive language support (30+) |
| [codanna](https://github.com/bartolli/codanna) | Bartolli | High-performance Rust implementation, memory-mapped storage, profile system |
| [TOON Format](https://github.com/toon-format/toon) | TOON Format | Tabular Object Output Notation - compact data format inspiration for output formatting |

This Windows-focused implementation builds upon these foundations while adding unique capabilities including multi-model query routing, per-model index storage, and Python call graph analysis.

I am grateful to these projects and their maintainers for pioneering semantic code search for AI assistants.
