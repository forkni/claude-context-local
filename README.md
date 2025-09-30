```
  ██████╗ ██╗       █████╗  ██╗   ██╗ ██████╗  ███████╗
 ██╔════╝ ██║      ██╔══██╗ ██║   ██║ ██╔══██╗ ██╔════╝
 ██║      ██║      ███████║ ██║   ██║ ██║  ██║ █████╗
 ██║      ██║      ██╔══██║ ██║   ██║ ██║  ██║ ██╔══╝
 ╚██████╗ ███████╗ ██║  ██║ ╚██████╔╝ ██████╔╝ ███████╗
  ╚═════╝ ╚══════╝ ╚═╝  ╚═╝  ╚═════╝  ╚═════╝  ╚══════╝

  ██████╗  ██████╗  ███╗   ██╗ ████████╗ ███████╗ ██╗  ██╗ ████████╗
 ██╔════╝ ██╔═══██╗ ████╗  ██║ ╚══██╔══╝ ██╔════╝ ╚██╗██╔╝ ╚══██╔══╝
 ██║      ██║   ██║ ██╔██╗ ██║    ██║    █████╗    ╚███╔╝     ██║
 ██║      ██║   ██║ ██║╚██╗██║    ██║    ██╔══╝    ██╔██╗     ██║
 ╚██████╗ ╚██████╔╝ ██║ ╚████║    ██║    ███████╗ ██╔╝ ██╗    ██║
  ╚═════╝  ╚═════╝  ╚═╝  ╚═══╝    ╚═╝    ╚══════╝ ╚═╝  ╚═╝    ╚═╝

 ██╗       ██████╗   ██████╗  █████╗  ██╗
 ██║      ██╔═══██╗ ██╔════╝ ██╔══██╗ ██║
 ██║      ██║   ██║ ██║      ███████║ ██║
 ██║      ██║   ██║ ██║      ██╔══██║ ██║
 ███████╗ ╚██████╔╝ ╚██████╗ ██║  ██║ ███████╗
 ╚══════╝  ╚═════╝   ╚═════╝ ╚═╝  ╚═╝ ╚══════╝

```

**General-Purpose Semantic Code Search for Windows.** Advanced **hybrid search** that combines semantic understanding with text matching, running 100% locally using EmbeddingGemma. No API keys, no costs, your code never leaves your machine.

- 🔍 **Hybrid search: BM25 + semantic for best accuracy (44.4% precision, 100% MRR)**
- 📈 **Optimized search efficiency with sub-second response times (162-487ms)**
- 🔒 **100% local - completely private**
- 💰 **Zero API costs - forever free**
- ⚡ **5-10x faster indexing with incremental updates**
- 🪟 **Windows-optimized** for maximum performance and compatibility

An intelligent code search system that uses Google's EmbeddingGemma model and advanced multi-language chunking to provide semantic search capabilities across 22 file extensions and 11 programming languages, integrated with Claude Code via MCP (Model Context Protocol).


## ✅ Production Ready

- Core functionality fully operational
- Windows-optimized installation with automated setup
- All search modes working (semantic, BM25, hybrid)
- Please report any issues!

## Demo

<img src="https://github.com/FarhanAliRaza/claude-context-local/releases/download/v0.1/example.gif" alt="Demo of local semantic code search" width="900" />

## Features

### 🔍 **Advanced Search Capabilities**

- **Hybrid search**: BM25 + Semantic fusion combines text matching with semantic understanding
- **Three search modes**: Semantic, BM25 text-based, and hybrid with RRF reranking
- **Proven search quality**: 44.4% precision, 46.7% F1-score, 100% MRR (see [benchmarks](docs/BENCHMARKS.md))
- **Sub-second performance**: 162-487ms response times across all search modes
- **Configurable weights**: Tune balance between text and semantic search
- **Auto-mode detection**: System automatically chooses best search strategy

### 🚀 **Core Features**

- **Multi-language support**: 11 programming languages with 22 file extensions
- **Intelligent chunking**: AST-based (Python) + tree-sitter (JS/TS/JSX/TSX/Svelte/Go/Java/Rust/C/C++/C#/GLSL)
- **Semantic search**: Natural language queries to find code across all languages
- **Rich metadata**: File paths, folder structure, semantic tags, language-specific info
- **MCP integration**: Direct integration with Claude Code for seamless workflow
- **Local processing**: All embeddings stored locally, no API calls required
- **Fast search**: FAISS for efficient similarity search with GPU acceleration support
- **Incremental indexing**: 5-10x faster updates with Merkle tree change detection

## Why this

Claude’s code context is powerful, but sending your code to the cloud costs tokens and raises privacy concerns. This project keeps semantic code search entirely on your machine. It integrates with Claude Code via MCP, so you keep the same workflow—just faster, cheaper, and private.

## Requirements

- Python 3.11+ (tested with Python 3.11+)
- Disk: 1–2 GB free (model + caches + index)
- Optional: NVIDIA GPU (CUDA 11/12) for FAISS acceleration; Apple Silicon (MPS) for embedding acceleration. These also speed up running the embedding model with SentenceTransformer, but everything still works on CPU.

## Install & Update

### Windows Installation (Recommended)

```powershell
# 1. Clone the repository
git clone https://github.com/forkni/claude-context-local.git
cd claude-context-local

# 2. Run the unified Windows installer (auto-detects CUDA)
install-windows.bat

# 3. Verify installation
verify-installation.bat

# 4. (Optional) Configure Claude Code MCP integration
scripts\powershell\configure_claude_code.ps1 -Global
```

> **⚠️ Important**: The installer will prompt for HuggingFace authentication during setup. You'll need a HuggingFace token to access the EmbeddingGemma model. Get your token at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) and accept terms at [https://huggingface.co/google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m).

**Windows Installer Features:**

- **Smart CUDA Detection**: Automatically detects your CUDA version and installs appropriate PyTorch
- **One-Click Setup**: Complete installation with single command
- **Built-in Verification**: Comprehensive testing with verify-installation.bat
- **Professional Organization**: Clean, streamlined script structure

### Update existing installation

Update by pulling latest changes:

```powershell
# Navigate to your project directory
cd claude-context-MCP
git pull

# Re-run the Windows installer to update dependencies
install-windows.bat

# Verify the update
verify-installation.bat
```

The Windows installer will:

- Update the code and dependencies automatically
- Preserve your embeddings and indexed projects in `~/.claude_code_search`
- Update only changed components with intelligent caching
- Maintain your existing MCP server configuration

### What the Windows installer does

- Detects and installs `uv` package manager if missing
- Creates and manages the project virtual environment
- Installs Python dependencies with optimized resolution using `uv sync`
- Downloads the EmbeddingGemma model (~1.2–1.3 GB) if not already cached
- Automatically detects CUDA and installs appropriate PyTorch version
- Configures `faiss-gpu` if an NVIDIA GPU is detected
- **Preserves all your indexed projects and embeddings** across updates

## Quick Start

### 1) Install and Setup

```powershell
# Windows (Recommended) - One-click installation
install-windows.bat

# Verify everything is working
verify-installation.bat

# The installer automatically:
# - Detects your hardware (CUDA/CPU)
# - Installs appropriate PyTorch version
# - Sets up all dependencies
# - Creates virtual environment
```

### 2) Start the MCP Server

```powershell
# Main entry point - Interactive menu with 8 functional options
start_mcp_server.bat

# Alternative launchers:
# Debug mode with enhanced logging
scripts\batch\start_mcp_debug.bat

# Simple mode with minimal output
scripts\batch\start_mcp_simple.bat
```

**Optional: Configure Claude Code Integration**

```powershell
# One-time setup to register MCP server with Claude Code
scripts\powershell\configure_claude_code.ps1 -Global

# Manual registration (alternative)
claude mcp add code-search --scope user -- "F:\path\to\claude-context-MCP\.venv\Scripts\python.exe" -m mcp_server.server
```

### 3) Use in Claude Code

#### Essential Workflow

```bash
# 1. Index your project (one-time setup)
/index_directory "C:\path\to\your\project"

# 2. Search your code with natural language
/search_code "authentication functions"
/search_code "error handling patterns"
/search_code "database connection setup"
/search_code "API endpoint handlers"
/search_code "configuration loading"
```

#### Advanced Search Examples

```bash
# Find similar code to existing implementations
/find_similar_code "project_file.py:123-145:function:authenticate_user"

# Check system status and performance
/get_index_status
/get_memory_status

# Configure search modes for specific needs
/configure_search_mode "hybrid" 0.4 0.6 true
/get_search_config_status

# Project management
/list_projects
/switch_project "C:\different\project\path"
```

#### Practical Usage Tips

- **Start simple**: Use natural language queries like "error handling" or "database connection"
- **Be specific**: "React component with useState hook" vs just "React"
- **Use context**: "authentication middleware" vs "auth" for better results
- **Try different modes**: Switch between semantic, hybrid, and text search as needed
- **Clean up**: Use `/cleanup_resources` when switching between large projects

**No manual configuration needed** - the system automatically uses the best search mode for your queries.

## Running Benchmarks

The project includes comprehensive benchmarking tools to validate performance:

### Quick Start

```bash
# Windows - Interactive benchmark menu
run_benchmarks.bat
```

**Available Options:**

1. **Token Efficiency Benchmark** (~10 seconds)
   - Validates 98.6% token reduction vs traditional file reading
   - Results saved to: `benchmark_results/token_efficiency/`

2. **Search Method Comparison** (~2-3 minutes)
   - Automatically compares all 3 search methods (hybrid, BM25, semantic)
   - Uses current project directory for realistic evaluation
   - Results saved to: `benchmark_results/method_comparison/`
   - Generates comparison report with winner declaration

3. **Auto-Tune Search Parameters** (~2 minutes)
   - Optimize BM25/Dense weights for your codebase
   - Tests 3 strategic configurations
   - Results saved to: `benchmark_results/tuning/`

4. **Run All Benchmarks** (~4-5 minutes)
   - Complete test suite including auto-tuning
   - Comprehensive results across all metrics

### Command Line Usage

```bash
# Method comparison (recommended)
.venv\Scripts\python.exe evaluation/run_evaluation.py method-comparison --project "." --k 5

# Token efficiency evaluation
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency

# Force CPU usage (if GPU issues)
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency --cpu
```

Results are saved to `benchmark_results/` directory (gitignored for privacy).
See [docs/BENCHMARKS.md](docs/BENCHMARKS.md) for detailed performance metrics.

## Test Suite

The project includes a comprehensive test suite with 37 test files organized into professional categories:

### Test Organization

- **Unit Tests** (14 files): Component isolation testing in `tests/unit/`
- **Integration Tests** (23 files): Workflow validation testing in `tests/integration/`
- **Test Fixtures**: Reusable mocks and sample data in `tests/fixtures/`
- **Test Data**: Sample projects and datasets in `tests/test_data/`

### Running Tests

```bash
# Run all tests
pytest tests/

# Run only unit tests (fast)
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=. --cov-report=html
```

📚 **Detailed testing documentation**: [View Test Suite Guide](tests/README.md)

## Running Performance Benchmarks

To validate the system's performance claims and test your hardware setup, you can run comprehensive benchmarks:

### Quick Benchmark (Recommended)

```bash
# Windows - Interactive menu with 5 benchmark options
run_benchmarks.bat

# Select option 1: Token Efficiency Benchmark (~10 seconds)
# Shows 98.6% token reduction vs traditional file reading
```

### Available Benchmarks

| Benchmark | Description | Duration | Key Metrics |
|-----------|-------------|----------|-------------|
| **Token Efficiency** | Compares MCP semantic search vs vanilla file reading | ~10 seconds | 98.6% token reduction, 8.6x GPU speedup |
| **Search Method Comparison** | Compares all 3 search methods (hybrid, BM25, semantic) | ~2-3 minutes | Precision, recall, F1-score, winner declaration |
| **Complete Suite** | Runs both token efficiency and method comparison | ~3-4 minutes | Comprehensive performance profile |

### Command Line Usage

```bash
# Token efficiency benchmark (measures token savings)
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency

# Search method comparison (evaluates all 3 methods)
.venv\Scripts\python.exe evaluation/run_evaluation.py method-comparison --project "."
```

### Why Run Benchmarks?

- **Validate Performance**: Confirm 98.6% token reduction on your hardware
- **Test GPU Acceleration**: Verify CUDA performance (8.6x faster indexing)
- **Quality Assurance**: Measure search accuracy on your specific codebase
- **Hardware Optimization**: Compare CPU vs GPU performance

📊 **Detailed results and methodology**: [View Complete Benchmarks](docs/BENCHMARKS.md)

## Search Modes & Performance

### Available Search Modes

| Mode | Description | Best For | Performance | Quality Metrics | Status |
|------|-------------|----------|-------------|-----------------|--------|
| **hybrid** | BM25 + Semantic with RRF reranking (default) | General use, balanced accuracy | 487ms, optimal accuracy | 44.4% precision, 100% MRR | ✅ Fully operational |
| **semantic** | Dense vector search only | Conceptual queries, code similarity | 487ms, semantic understanding | 38.9% precision, 100% MRR | ✅ Fixed 2025-09-25 |
| **bm25** | Text-based sparse search only | Exact matches, error messages | 162ms, fastest | 33.3% precision, 61.1% MRR | ✅ Fully operational |
| **auto** | Automatically choose based on query | Let system optimize | Adaptive performance | Context-dependent | ✅ Fully operational |

For detailed configuration options, see [Hybrid Search Configuration Guide](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md).

📊 **Performance benchmarks and detailed metrics**: [View Benchmarks](docs/BENCHMARKS.md)


## Architecture

```
claude-context-local/
├── chunking/                         # Multi-language chunking (22 extensions)
│   ├── multi_language_chunker.py     # Unified orchestrator (Python AST + tree-sitter)
│   ├── python_ast_chunker.py         # Python-specific chunking (rich metadata)
│   └── tree_sitter.py                # Tree-sitter: JS/TS/JSX/TSX/Svelte/Go/Java/Rust/C/C++/C#/GLSL
├── embeddings/
│   └── embedder.py                   # EmbeddingGemma; device=auto (CUDA→MPS→CPU); offline cache
├── search/
│   ├── indexer.py                    # FAISS index (CPU by default; GPU when available)
│   ├── searcher.py                   # Intelligent ranking & filters
│   ├── incremental_indexer.py        # Merkle-driven incremental indexing
│   ├── hybrid_searcher.py            # BM25 + semantic fusion
│   └── bm25_index.py                 # BM25 text search implementation
├── merkle/
│   ├── merkle_dag.py                 # Content-hash DAG of the workspace
│   ├── change_detector.py            # Diffs snapshots to find changed files
│   └── snapshot_manager.py           # Snapshot persistence & stats
├── mcp_server/
│   └── server.py                     # MCP tools for Claude Code (stdio/HTTP)
├── tools/                           # Development utilities
│   ├── index_project.py             # Interactive project indexing
│   └── search_helper.py             # Standalone search interface
├── evaluation/                       # Comprehensive evaluation framework
│   ├── semantic_evaluator.py         # Performance testing and benchmarking
│   └── README.md                     # Evaluation documentation
├── scripts/
│   ├── batch/                       # Essential Windows batch scripts
│   │   ├── install_pytorch_cuda.bat # PyTorch CUDA installation
│   │   └── mcp_server_wrapper.bat  # MCP server wrapper script
│   ├── powershell/                  # Windows PowerShell scripts
│   │   ├── configure_claude_code.ps1 # Claude Code MCP configuration
│   │   ├── hf_auth.ps1              # Hugging Face authentication helper
│   │   ├── install-windows.ps1     # Windows automated installer
│   │   └── start_mcp_server.ps1     # PowerShell MCP server launcher
│   └── verify_installation.py       # Python verification system
├── start_mcp_server.bat             # Main launcher (Windows)
├── install-windows.bat              # Primary installer (Windows)
└── verify-installation.bat          # Installation verification
```

### Data flow

```mermaid
graph TD
    A["Claude Code (MCP client)"] -->|index_directory| B["MCP Server"]
    B --> C{IncrementalIndexer}
    C --> D["ChangeDetector<br/>(Merkle DAG)"]
    C --> E["MultiLanguageChunker"]
    E --> F["Code Chunks"]
    C --> G["CodeEmbedder<br/>(EmbeddingGemma)"]
    G --> H["Embeddings"]
    C --> I["CodeIndexManager<br/>(FAISS CPU/GPU)"]
    H --> I
    D --> J["SnapshotManager"]
    C --> J
    B -->|search_code| K["Searcher"]
    K --> I
```

## Intelligent Chunking

The system uses advanced parsing to create semantically meaningful chunks across all supported languages:

### Chunking Strategies

- **Python**: AST-based parsing for rich metadata extraction
- **All other languages**: Tree-sitter parsing with language-specific node type recognition

### Chunk Types Extracted

- **Functions/Methods**: Complete with signatures, docstrings, decorators
- **Classes/Structs**: Full definitions with member functions as separate chunks
- **Interfaces/Traits**: Type definitions and contracts
- **Enums/Constants**: Value definitions and module-level declarations
- **Namespaces/Modules**: Organizational structures
- **Templates/Generics**: Parameterized type definitions
- **GLSL Shaders**: Vertex, fragment, compute, geometry, tessellation shaders with uniforms and layouts

### Rich Metadata for All Languages

- File path and folder structure
- Function/class/type names and relationships
- Language-specific features (async, generics, modifiers, etc.)
- Parent-child relationships (methods within classes)
- Line numbers for precise code location
- Semantic tags (component, export, async, etc.)

## Configuration

### Environment Variables

- `CODE_SEARCH_STORAGE`: Custom storage directory (default: `~/.claude_code_search`)

### Model Configuration

The system uses `google/embeddinggemma-300m` by default.

Notes:

- Download size: ~1.2–2 GB on disk depending on variant and caches
- Device selection: auto (CUDA on NVIDIA, MPS on Apple Silicon, else CPU)
- You can pre-download via installer or at first use
- FAISS backend: CPU by default. If an NVIDIA GPU is detected, the installer
  attempts to install `faiss-gpu-cu12` (or `faiss-gpu-cu11`) and the index will
  run on GPU automatically at runtime while saving as CPU for portability.

#### Hugging Face authentication (if prompted)

The `google/embeddinggemma-300m` model is hosted on Hugging Face and may require
accepting terms and/or authentication to download.

1. Visit the model page and accept any terms:

   - <https://huggingface.co/google/embeddinggemma-300m>

2. Authenticate one of the following ways:

   - CLI (recommended):

     ```bash
     uv run huggingface-cli login
     # Paste your token from https://huggingface.co/settings/tokens
     ```

   - Environment variable:

     ```bash
     export HUGGING_FACE_HUB_TOKEN=hf_XXXXXXXXXXXXXXXXXXXXXXXX
     ```

After the first successful download, we cache the model under `~/.claude_code_search/models`
and prefer offline loads for speed and reliability.

### Hybrid Search Configuration

The system supports multiple search modes with configurable parameters:

#### Quick Configuration via MCP Tools

```bash
# Configure hybrid search (recommended)
/configure_search_mode "hybrid" 0.4 0.6 true

# Check current configuration
/get_search_config_status

# Switch to semantic-only mode
/configure_search_mode "semantic" 0.0 1.0 true

# Switch to text-only mode
/configure_search_mode "bm25" 1.0 0.0 true
```

#### Environment Variable Configuration

```bash
# Windows (PowerShell)
$env:CLAUDE_SEARCH_MODE="hybrid"
$env:CLAUDE_ENABLE_HYBRID="true"
$env:CLAUDE_BM25_WEIGHT="0.4"
$env:CLAUDE_DENSE_WEIGHT="0.6"

```

#### Available Search Modes

| Mode | Description | Best For | Performance | Quality Metrics | Status |
|------|-------------|----------|-------------|-----------------|--------|
| **hybrid** | BM25 + Semantic with RRF reranking (default) | General use, balanced accuracy | 487ms, optimal accuracy | 44.4% precision, 100% MRR | ✅ Fully operational |
| **semantic** | Dense vector search only | Conceptual queries, code similarity | 487ms, semantic understanding | 38.9% precision, 100% MRR | ✅ Fixed 2025-09-25 |
| **bm25** | Text-based sparse search only | Exact matches, error messages | 162ms, fastest | 33.3% precision, 61.1% MRR | ✅ Fully operational |
| **auto** | Automatically choose based on query | Let system optimize | Adaptive performance | Context-dependent | ✅ Fully operational |

For detailed configuration options, see [Hybrid Search Configuration Guide](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md).

📊 **Performance benchmarks and detailed metrics**: [View Benchmarks](docs/BENCHMARKS.md)

## MCP Tools Reference

The following MCP tools are available in Claude Code:

### Core Search Tools

- `/search_code` - Main search with hybrid capabilities
- `/index_directory` - Index a project for searching
- `/find_similar_code` - Find code similar to a specific chunk

### Configuration Tools

- `/configure_search_mode` - Configure hybrid search parameters
- `/get_search_config_status` - View current configuration

### Management Tools

- `/get_index_status` - Check index statistics
- `/get_memory_status` - Monitor memory usage
- `/cleanup_resources` - Free memory and cleanup
- `/clear_index` - Reset search index
- `/list_projects` - List indexed projects
- `/switch_project` - Switch between projects

### Supported Languages & Extensions

**Fully Supported (22 extensions across 10+ languages):**

| Language | Extensions |
|----------|------------|
| **Python** | `.py` |
| **JavaScript** | `.js`, `.jsx` |
| **TypeScript** | `.ts`, `.tsx` |
| **Java** | `.java` |
| **Go** | `.go` |
| **Rust** | `.rs` |
| **C** | `.c` |
| **C++** | `.cpp`, `.cc`, `.cxx`, `.c++` |
| **C#** | `.cs` |
| **Svelte** | `.svelte` |
| **GLSL** | `.glsl`, `.frag`, `.vert`, `.comp`, `.geom`, `.tesc`, `.tese` |

**Total**: **22 file extensions** across **11 programming languages**

## Storage

Data is stored in the configured storage directory:

```
~/.claude_code_search/
├── models/          # Downloaded models
├── index/           # FAISS indices and metadata
│   ├── code.index   # Vector index
│   ├── metadata.db  # Chunk metadata (SQLite)
│   ├── stats.json   # Index statistics
│   └── bm25/        # BM25 text search index
│       ├── bm25.index      # BM25 sparse index
│       ├── bm25_docs.json  # Document storage
│       └── bm25_metadata.json # BM25 metadata
```

## Performance

- **Model size**: ~1.2GB (EmbeddingGemma-300m and caches)
- **Embedding dimension**: 768 (can be reduced for speed)
- **Index types**: Flat (exact) or IVF (approximate) based on dataset size
- **Batch processing**: Configurable batch sizes for embedding generation

Tips:

- First index on a large repo will take time (model load + chunk + embed). Subsequent runs are incremental.
- With GPU FAISS, searches on large indexes are significantly faster.
- Embeddings automatically use CUDA (NVIDIA) or MPS (Apple) if available.

## Recent Improvements (2025-09-25)

### 🎉 **Semantic Search Mode Restored**

- **Fixed critical bug**: Restored semantic search functionality with simple one-line fix
- **Root cause**: `HybridSearcher` was calling non-existent `embed_text()` instead of `embed_query()`
- **Impact**: All three search modes (semantic, BM25, hybrid) now fully operational

### ✅ **Hybrid Search System Complete**

- **Production ready**: Hybrid search system is complete and ready for use
- **Performance maintained**: 39.4% token reduction capability intact
- **Windows-optimized**: Streamlined for Windows environments with comprehensive automation
- **BM25 integration**: Successfully completed with proper index population

### 🚀 **Enhanced Performance**

- **Sub-second response times**: Fast search across all modes
- **Memory optimization**: Efficient resource usage and cleanup
- **Incremental indexing**: 5-10x faster updates with change detection

This update completes the hybrid search implementation and provides a fully functional semantic code search system.

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed with `uv sync`
2. **Model download fails**: Check internet connection and disk space
3. **Memory issues**: Reduce batch size in indexing script
4. **No search results**: Verify the codebase was indexed successfully
5. **FAISS GPU not used**: Ensure `nvidia-smi` is available and CUDA drivers are installed; re-run installer to pick `faiss-gpu-cu12`/`cu11`.
6. **Force offline**: We auto-detect a local cache and prefer offline loads; you can also set `HF_HUB_OFFLINE=1`.

### Ignored directories (for speed and noise reduction)

`node_modules`, `.venv`, `venv`, `env`, `.env`, `.direnv`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.pytype`, `.ipynb_checkpoints`, `build`, `dist`, `out`, `public`, `.next`, `.nuxt`, `.svelte-kit`, `.angular`, `.astro`, `.vite`, `.cache`, `.parcel-cache`, `.turbo`, `coverage`, `.coverage`, `.nyc_output`, `.gradle`, `.idea`, `.vscode`, `.docusaurus`, `.vercel`, `.serverless`, `.terraform`, `.mvn`, `.tox`, `target`, `bin`, `obj`

## Contributing

This is a research project focused on intelligent code chunking and search. Feel free to experiment with:

- Different chunking strategies
- Alternative embedding models
- Enhanced metadata extraction
- Performance optimizations

## License

Licensed under the GNU General Public License v3.0 (GPL-3.0). See the `LICENSE` file for details.

## Inspiration

This Windows-focused fork was adapted from [FarhanAliRaza/claude-context-local](https://github.com/FarhanAliRaza/claude-context-local), which provides cross-platform support for Linux and macOS.

Both projects draw inspiration from [zilliztech/claude-context](https://github.com/zilliztech/claude-context). We adapted the concepts to a Python implementation with fully local embeddings and Windows-specific optimizations.
