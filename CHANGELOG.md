# Changelog

All notable changes to the Claude Context Local (MCP) semantic code search system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.1] - 2025-10-05

### Fixed

- **Critical Bug: find_similar_code MCP Tool** - Added missing `find_similar_to_chunk()` method to HybridSearcher class (search/hybrid_searcher.py:428-465)
  - Previously only existed in IntelligentSearcher, causing AttributeError when hybrid search enabled (default mode)
  - Tool now functional for both searcher implementations
  - Verified with multi-model testing (BGE-M3 1024d, Gemma 768d)

### Changed

- **MCP Tools Interface** - Removed `run_benchmark` from user-facing MCP tools
  - Tool count reduced from 14 → 13 (development-only access via evaluation/run_evaluation.py)
  - Updated documentation in mcp_server/server.py, CLAUDE.md (both projects), docs/MCP_TOOLS_REFERENCE.md
- **Documentation Updates**
  - Added missing tools: list_embedding_models, switch_embedding_model
  - Updated all tool parameters to match current API
- **Development Session Logging** - Updated MEMORY.md with session 2025-10-05 accomplishments
- **Version Bump**: 0.4.0 → 0.4.1

---

## [0.4.0] - 2025-10-03

### Added

- **Git Workflow Automation System** (9 scripts total)
  - `.gitattributes` with merge strategies (ours, union, diff3) for dual-branch workflow
  - Core Scripts: `merge_with_validation.bat`, `validate_branches.bat`, `rollback_merge.bat`
  - Helper Scripts: `merge_docs.bat`, `cherry_pick_commits.bat`, `commit_enhanced.bat`, `check_lint.bat`, `fix_lint.bat`, `install_hooks.bat`
  - Automated branch synchronization with .gitattributes support
  - Pre-merge validation and rollback capabilities

- **GitHub Actions Workflows** (5 workflows)
  - `branch-protection.yml` - Automated CI/CD validation, testing, linting on every push
  - `merge-development-to-main.yml` - Manual merge workflow with .gitattributes support
  - `docs-validation.yml` - Documentation quality checks (markdown lint, link checking, spelling)
  - `claude.yml` - Interactive @claude mentions in GitHub issues/PRs (OAuth-based authentication)
  - `claude-code-review.yml` - Automated code review workflow

- **Claude Code GitHub Integration**
  - Custom command templates in `.claude/commands/` directory
  - `create-pr.md` - Automated PR creation with clean, professional formatting
  - `run-merge.md` - Guided merge workflow with validation and rollback support
  - `validate-changes.md` - Pre-commit validation checklist (blocks local-only files, validates conventional commits)
  - Interactive AI assistance via @claude mentions in GitHub issues and pull requests

- **Per-Model Index Storage** (0.4.0 major feature)
  - Instant model switching (<150ms) with 98% time reduction (50-90s → <1s)
  - Dimension-based storage isolation (768d for Gemma, 1024d for BGE-M3)
  - Independent Merkle snapshots per model dimension
  - Zero re-indexing overhead when switching back to previously used models
  - Storage format: `{project}_{hash}_{dimension}d/` directories

- **Enhanced MCP Configuration**
  - Python-based manual configuration fallback for improved reliability
  - Automatic detection and handling of Claude CLI failures
  - Path verification and validation system
  - Cross-directory compatibility with wrapper scripts

### Changed

- **Documentation Structure**: `docs/GIT_WORKFLOW.md` moved to development-only (internal workflow guide)
- **Configuration Scripts**: Migrated from PowerShell to Python for better cross-platform reliability
- **MCP Server Setup**: Added automatic fallback mechanisms when Claude CLI fails
- **README.md**: Updated architecture section with Git scripts and GitHub Actions workflows
- **Installation Guide**: Added GitHub Actions integration section
- **Development-Only File Protection**: Expanded .gitignore and .gitattributes rules

### Fixed

- **MCP Configuration**: Enhanced path validation and error handling
- **Branch Synchronization**: Improved status reporting in sync scripts
- **Variable Initialization**: Fixed variable scoping issues in batch scripts

---

## [0.3.0] - 2025-09-29

### Added

- **CHANGELOG.md**: Comprehensive change tracking following Keep a Changelog format
- **GIT_WORKFLOW.md**: Complete Git workflow documentation with versioning guidance
  - Semantic versioning strategy (MAJOR.MINOR.PATCH)
  - Release workflow steps
  - CHANGELOG maintenance guidelines

### Changed

- **Documentation Accuracy**: Corrected token efficiency metrics across all documentation
  - Token reduction: 99.9% → 98.6% (accurate measured value)
  - Tokens saved: 20,667 → 89,531 (actual benchmark results)
  - Efficiency ratio: 1000x → 71x (realistic multiplier)
  - Test scenarios: 3 → 7 (expanded test coverage)
  - Search quality metrics updated: Precision 0.611, Recall 0.500, F1-Score 0.533
- **Benchmark Documentation**: Updated `docs/BENCHMARKS.md` with accurate metrics (12 sections)
- **README.md**: Corrected token efficiency claims (4 locations)
- **Evaluation README**: Updated framework documentation (3 locations)
- **Installation Guide**: Corrected expected benchmark results
- **MCP Server Docstring**: Updated tool description with accurate metrics
- **Version Bump**: 0.2.0 → 0.3.0

### Fixed

- **Evaluation Consistency**: Verified all evaluators use identical calculation methods from `BaseEvaluator`
- **Documentation Conflicts**: Removed outdated `Git_Workflow_Strategy.md` to eliminate contradictions

### Removed

- **Outdated Documentation**: Deleted `docs/Git_Workflow_Strategy.md` (contradicted current .gitignore setup)

---

## [0.2.0] - 2025-09-28

### Added

- **Auto-Tuning System**: Parameter optimization tool for hybrid search weights (`tools/auto_tune_search.py`)
  - Tests multiple BM25/Dense weight configurations (0.3/0.7, 0.4/0.6, 0.6/0.4)
  - Uses F1-score as primary metric with query time as tie-breaker
  - Generates optimization reports with recommended configurations
  - Results saved to `benchmark_results/tuning/`
- **Debug Scenarios Dataset**: 7 diverse test scenarios for evaluation (`evaluation/datasets/debug_scenarios.json`)
- **Parameter Optimizer Module**: Core auto-tuning logic (`evaluation/parameter_optimizer.py`)

### Changed

- **Benchmark System**: Enhanced run_benchmarks.bat with auto-tuning option
- **Evaluation Framework**: Added method-comparison mode for testing all search methods
- **Version Bump**: 0.1.0 → 0.2.0

### Fixed

- **Model Loading Overhead**: Fixed first query timing issue in auto-tuning by passing pre-created embedder
- **Search Method Comparison**: Improved benchmark comparison reporting

---

## [0.1.0] - 2025-01-27

### Added

- **Multi-Language Support**: 22 file extensions across 11 programming languages
  - Python (AST-based parsing)
  - JavaScript, TypeScript, JSX, TSX (tree-sitter)
  - Java, Go, Rust, C, C++, C#, Svelte (tree-sitter)
  - GLSL shaders (.glsl, .frag, .vert, .comp, .geom, .tesc, .tese)
- **Hybrid Search System**: BM25 + semantic search with RRF (Reciprocal Rank Fusion)
  - Configurable weights (default: BM25 0.4, Dense 0.6)
  - Parallel query execution
  - Three search modes: hybrid, BM25-only, semantic-only
- **MCP Server Integration**: 10 semantic search tools for Claude Code
  - `index_directory()` - Project indexing
  - `search_code()` - Natural language code search
  - `find_similar_code()` - Alternative implementation discovery
  - Memory management and project switching tools
- **Token Efficiency Evaluator**: Benchmark system measuring token savings vs traditional file reading
- **Windows-Optimized Installation**:
  - `install-windows.bat` - One-click setup
  - `verify-installation.bat` - Comprehensive validation
  - CUDA auto-detection and PyTorch installation
  - HuggingFace authentication handling
- **Comprehensive Test Suite**:
  - 184+ unit tests (tests/unit/)
  - 23+ integration tests (tests/integration/)
  - All tests passing with robust mocking
- **Benchmarking System**:
  - `run_benchmarks.bat` - Interactive benchmark menu
  - Token efficiency evaluation
  - Search method comparison
  - Performance validation
- **Git Workflow Documentation**: Local-first privacy model with automated scripts
  - `.gitignore` protection for development files
  - `scripts/git/commit.bat` - Safe committing
  - `scripts/git/sync_branches.bat` - Branch synchronization

### Changed

- **Project Rename**: Claude-context-MCP → claude-context-local
- **Test Organization**: Reorganized from root to unit/integration subdirectories
- **Branch Strategy**: Dual-branch workflow (development for internal, main for public)
- **Documentation Structure**: Professional organization with comprehensive guides

### Fixed

- **Hybrid Search Integration**: Fixed BM25 + semantic search fusion
- **Semantic Search Mode**: Corrected method name issues
- **Branch Synchronization**: Resolved development/main branch conflicts
- **Test Failures**: Fixed all 184 unit tests and integration tests
- **HuggingFace Authentication**: Robust handling with retry logic

---

## [Unreleased]

### Planned Features

- Real-world usage pattern analysis
- Expanded language support
- Interactive evaluation dashboard
- CI/CD pipeline integration
- SWE-bench evaluation completion

---

## Version History

- **v0.4.1** - Critical bug fix: find_similar_code, MCP tools cleanup (2025-10-05)
- **v0.4.0** - Git automation, GitHub Actions, instant model switching (2025-10-03)
- **v0.3.0** - Documentation accuracy & workflow consolidation (2025-09-29)
- **v0.2.0** - Auto-tuning parameter optimization (2025-09-28)
- **v0.1.0** - Initial release with hybrid search (2025-01-27)

---

## Links

- **Repository**: <https://github.com/forkni/claude-context-local>
- **Documentation**: See `docs/` directory
- **Issue Tracker**: <https://github.com/forkni/claude-context-local/issues>
