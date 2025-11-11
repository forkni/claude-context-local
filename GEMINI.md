# GEMINI.md: Project Overview for claude-context-local

This document provides a comprehensive overview of the `claude-context-local` project, its architecture, and development conventions to serve as a guide for AI-assisted development.

## 1. Project Overview

`claude-context-local` is a sophisticated, private, local-first semantic code search engine optimized for Windows. It is designed to integrate seamlessly with the "Claude Code" editor extension via the Model Context Protocol (MCP), providing intelligent code search capabilities without the need for cloud services. Your code remains on your machine, ensuring privacy and cost-effectiveness.

### Core Technologies

- **Language:** Python 3.11+
- **Package Manager:** `uv`
- **Primary Dependencies:**
    - **AI & Embeddings:** `torch`, `sentence-transformers`, `huggingface-hub`
    - **Embedding Models:** `google/embeddinggemma-300m` (default), `BAAI/bge-m3` (optional upgrade)
    - **Search:** `faiss-cpu` (for vector search), `rank-bm25` (for text search)
    - **Code Parsing:** `tree-sitter` (for 10+ languages), Python `ast` module
    - **Server:** `fastmcp` (for Claude Code integration)
- **Testing:** `pytest` with `pytest-asyncio`, `pytest-cov`, and `pytest-mock`.
- **Code Quality:** `ruff`, `black`, and `isort`.

### Architecture

The project is structured into several key modules:

- `mcp_server/`: The main MCP server (`server.py`) that exposes tools like `/search_code` and `/index_directory` to Claude Code.
- `search/`: Contains the core logic for the hybrid search system.
    - `hybrid_searcher.py`: Combines BM25 (keyword) and semantic search.
    - `indexer.py`: Manages the FAISS vector index and metadata.
    - `incremental_indexer.py`: Optimizes re-indexing by processing only changed files.
    - `config.py`: Manages all search-related configurations.
- `chunking/`: Implements intelligent code chunking using `tree-sitter` and Python's `ast` to create semantically meaningful code segments.
- `embeddings/`: Handles the loading and execution of sentence transformer models for creating code embeddings.
- `merkle/`: Implements a Merkle DAG to efficiently detect file changes for fast incremental indexing.
- `scripts/`: A collection of `.bat` and `.ps1` scripts for automating installation, configuration, and execution on Windows.
- `tools/`: Standalone Python scripts for command-line operations like indexing, searching, and benchmarking.
- `tests/`: Contains the comprehensive test suite, organized into `unit`, `integration`, and `regression` tests.

## 2. Building and Running

The project is designed for a streamlined Windows experience.

### Installation

1.  **Clone the repository.**
2.  Run the main installer script:
    ```batch
    install-windows.bat
    ```
    This script automates the entire setup process:
    - Creates a Python virtual environment in `.venv/`.
    - Installs all dependencies from `pyproject.toml` using `uv`.
    - Detects the system's CUDA version and installs the appropriate `torch` build for GPU acceleration.
    - Configures the MCP server for Claude Code.

### Verification

After installation, run the verification script to ensure all components are working correctly:

```batch
verify-installation.bat
```

This runs a series of 15+ checks, including dependency validation, GPU detection, and a dry-run of the embedding model.

### Running the Server

The primary entry point is the interactive launcher:

```batch
start_mcp_server.bat
```

This script provides a menu-driven interface to:
- Start the MCP server (in `stdio` or `sse` transport mode).
- Manage project indexing (index, re-index, clear).
- Configure search parameters.
- Run performance benchmarks and tests.

### Core Workflow

1.  **Index a Project:** Before searching, a project must be indexed. This can be done via the interactive menu or by using the `/index_directory "C:\path\to\your\project"` command within Claude Code.
2.  **Search Code:** Once indexed, you can use natural language queries to find code. Use the `/search_code "your query"` command in Claude Code.

## 3. Development Conventions

### Testing

The project maintains a high standard of testing.

- **Running Tests:** The entire test suite can be run with `pytest`:
  ```shell
  # Run all tests
  pytest tests/

  # Run only unit tests (fast)
  pytest tests/unit/

  # Run integration tests
  pytest tests/integration/
  ```
- **Test Structure:** Tests are organized by type:
    - `tests/unit/`: For isolated component testing.
    - `tests/integration/`: For end-to-end workflow validation.
    - `tests/regression/`: For ensuring existing functionality isn't broken by new changes.

### Code Style and Linting

The project enforces a consistent code style using `black`, `isort`, and `ruff`.

- **Checking for Issues:**
  ```batch
  scripts\git\check_lint.bat
  ```
- **Automatically Fixing Issues:**
  ```batch
  scripts\git\fix_lint.bat
  ```
Configuration for these tools is located in the `pyproject.toml` file.

### Git Workflow

The repository contains a sophisticated set of scripts in `scripts/git/` to automate and standardize the Git workflow, including enhanced commit messages, branch validation, and safe merging. Refer to `docs/GIT_WORKFLOW.md` for detailed guidelines.
