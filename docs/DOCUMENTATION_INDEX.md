# Documentation Index

Complete navigation hub for claude-context-local documentation.

## 📚 Quick Navigation

- [Getting Started](#getting-started)
- [Core Guides](#core-guides)
- [Advanced Features](#advanced-features)
- [MCP Integration](#mcp-integration)
- [Development Tools](#development-tools)
- [Git Automation](#git-automation)
- [Testing & Validation](#testing--validation)
- [Technical Implementation](#technical-implementation)
- [Research & Analysis](#research--analysis)

---

## Getting Started

Essential documentation for setup and initial use.

| Document | Description |
|----------|-------------|
| **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** | Complete installation process for Windows |
| **[LOCAL_LLM_GUIDE.md](LOCAL_LLM_GUIDE.md)** | Use local LLMs via LM Studio instead of Anthropic API |
| **[CLAUDE_MD_TEMPLATE.md](CLAUDE_MD_TEMPLATE.md)** | CLAUDE.md template for project setup |
| **[PYTORCH_COMPATIBILITY.md](PYTORCH_COMPATIBILITY.md)** | PyTorch version requirements & installation |

---

## Core Guides

Fundamental documentation for daily use.

| Document | Description |
|----------|-------------|
| **[MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md)** | Complete API reference for all 19 MCP tools |
| **[HYBRID_SEARCH_CONFIGURATION_GUIDE.md](HYBRID_SEARCH_CONFIGURATION_GUIDE.md)** | Search modes configuration (hybrid/semantic/BM25/auto) |
| **[BENCHMARKS.md](BENCHMARKS.md)** | Performance benchmarks: SSCG retrieval (MRR/Recall/NDCG/line-overlap), token efficiency, caller recall |
| **[KNOWN_ISSUES.md](KNOWN_ISSUES.md)** | Known issues and workarounds |

---

## Advanced Features

Comprehensive guides for advanced functionality.

| Document | Description |
|----------|-------------|
| **[ADVANCED_FEATURES_GUIDE.md](ADVANCED_FEATURES_GUIDE.md)** | **Complete guide to all advanced features** |
| - Multi-Hop Search | Discover interconnected code relationships (93% queries benefit) |
| - Graph-Enhanced Search | Call relationship tracking for Python code |
| - Multi-Model Query Routing | Intelligent routing to optimal models (100% accuracy) |
| - Multi-Model Batch Indexing | Index with all 3 models simultaneously |
| - Per-Model Index Storage | Instant model switching <150ms |
| - Model Selection Guide | Complete model comparison tables |

---

## MCP Integration

MCP server implementation and transport options.

| Document | Description |
|----------|-------------|
| **[MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md)** | All 19 tools with parameters, examples, output formats |

### Transport Options

- **StreamableHTTP** (port 8765, `/mcp` endpoint) — **current default** (v0.12.0+): `{"type": "http", "url": "http://localhost:8765/mcp"}`. Re-run `scripts\batch\manual_configure.bat` to apply.
- **stdio** (legacy): Standard MCP mode via `manual_configure.bat`
- **SSE** (port 8765, legacy): Bypasses Claude Code stdio bugs (#3426, #768)
- **Dual SSE** (ports 8765/8766, legacy): VSCode + CLI simultaneous access

---

## Development Tools

Interactive scripts and batch files.

### Interactive Scripts

| Script | Purpose |
|--------|---------|
| `tools/batch_index.py` | Universal indexing (new/incremental/force) |
| `tools/cleanup_orphaned_projects.py` | Remove orphaned test projects |
| `tools/cleanup_stale_snapshots.py` | Interactive snapshot cleanup |

### Batch Files

| Script | Purpose |
|--------|---------|
| `start_mcp_server.bat` | Main launcher (8 options: Quick Start, Project Management, Search Config, Advanced) |
| `scripts/batch/start_mcp_sse.bat` | SSE transport (port 8765) |
| `scripts/batch/start_mcp_sse_cli.bat` | CLI SSE transport (port 8766) |
| `scripts/batch/start_both_sse_servers.bat` | Dual SSE servers |
| `scripts/batch/manual_configure.bat` | Claude Code MCP setup |
| `scripts/batch/install_pytorch_cuda.bat` | PyTorch CUDA installation |

---

## Git Automation

Git workflow automation and safety.

| Document | Description |
|----------|-------------|
| **[AUTOMATED_GIT_WORKFLOW.md](AUTOMATED_GIT_WORKFLOW.md)** | Step-by-step git workflow for Claude Code |
| **[GIT_WORKFLOW.md](GIT_WORKFLOW.md)** | Troubleshooting and advanced operations |
| **[PRE_COMMIT_HOOKS.md](PRE_COMMIT_HOOKS.md)** | Pre-commit hook configuration |
| **[scripts/git/README.md](../scripts/git/README.md)** | Complete git scripts documentation |

### Git Scripts

**Directory Structure**:

- **Shell scripts (.sh)**: `scripts/git/` - **PRIMARY for automated workflows**
- **Batch scripts (.bat)**: `scripts/git/batch/` - Manual Windows CMD execution

| Script | Shell (PRIMARY) | Batch (manual) | Purpose |
|--------|----------------|----------------|---------|
| `commit_enhanced` | `scripts/git/` | `scripts/git/batch/` | Enhanced commits with validation |
| `merge_with_validation` | `scripts/git/` | `scripts/git/batch/` | Merge with comprehensive validation |
| `check_lint` | `scripts/git/` | `scripts/git/batch/` | Lint validation (ruff) |
| `fix_lint` | `scripts/git/` | `scripts/git/batch/` | Auto-fix lint issues (ruff) |
| `validate_branches` | `scripts/git/` | `scripts/git/batch/` | Pre-merge validation |
| `cherry_pick_commits` | `scripts/git/` | `scripts/git/batch/` | Cherry-pick specific commits |
| `merge_docs` | `scripts/git/` | `scripts/git/batch/` | Documentation-only merge |
| `rollback_merge` | `scripts/git/` | `scripts/git/batch/` | Emergency rollback |
| `install_hooks` | `scripts/git/` | `scripts/git/batch/` | Install pre-commit hooks |
| `_common` | `scripts/git/` | `scripts/git/batch/` | Shared utility functions |

---

## Testing & Validation

Test suite documentation and validation reports.

| Document | Description |
|----------|-------------|
| **[tests/TESTING_GUIDE.md](../tests/TESTING_GUIDE.md)** | Comprehensive testing documentation (2,853 unit + 19 integration tests) |
| **[tests/README.md](../tests/README.md)** | Test suite organization and best practices |

### Testing Tools (scripts/test/)

| Script | Purpose |
|--------|---------|
| **detect_flaky_tests.sh** | Detect intermittent test failures by running tests multiple times (pytest-repeat integration) |

**Flaky Test Detection Features:**

- Configurable repeat count (default: 5 runs)
- Automatic venv Python/pytest detection
- Identifies timing-sensitive tests
- See [tests/TESTING_GUIDE.md](../tests/TESTING_GUIDE.md) Section 9 for complete guide

---

## Technical Implementation

Detailed technical documentation.

| Document | Description |
|----------|-------------|
| **[CHUNKING_ENHANCEMENTS_PLAN.md](CHUNKING_ENHANCEMENTS_PLAN.md)** | Code chunking enhancements and strategy |
| **[CALL_GRAPH_TUNING.md](CALL_GRAPH_TUNING.md)** | pyan3 + LibCST + LSP API reference, confidence tiers, `min_confidence` recipes, §6.4 LSP diagnostics counters |

### Architecture Files

- `chunking/` - Semantic chunking (AST + Tree-sitter)
- `embeddings/` - Model loading & embedding generation
  - `query_cache.py` - LRU cache with TTL for query embeddings (v0.8.6+)
- `graph/` - Call graph extraction and relationship tracking
  - `resolvers/` - Type, import, and assignment resolvers
- `mcp_server/` - MCP tool implementations (19 tools)
- `merkle/` - Incremental indexing (snapshot management)
- `search/` - FAISS + BM25 hybrid search
- `utils/` - Performance monitoring and utilities (v0.8.6+)
  - `timing.py` - `@timed` decorator and `Timer` context manager for performance instrumentation

---

## Version History

| Document | Description |
|----------|-------------|
| **[VERSION_HISTORY.md](VERSION_HISTORY.md)** | Complete version history from v0.1.x to v0.17.0 |

### Key Versions

- **v0.17.0** (2026-06-24): DSPy/GEPA agent-eval harness, `ClaudeCodeLM` subscription backend, `default_k` 4→7 (MRR +0.093, Recall@7 +0.122), CVE remediation 53→5, Batch 3/4/5 perf+fixes, 2,853 tests
- **v0.16.0** (2026-06-11): code-review hardening — 30 correctness/concurrency fixes (Batch 1/2A/2B); thread-safe MCP server, MultiDiGraph call graph, atomic writes, 2,533 tests
- **v0.15.0** (2026-06-03): LSP resolver repair (0 → 938 edges), resolver precision tuning, `min_confidence`/`use_pyproject_toml` config knobs, `docs/CALL_GRAPH_TUNING.md`, 2,495 tests
- **v0.14.0** (2026-06-03): Layered call-graph resolver pipeline (AST→pyan→LibCST→LSP), optional `[callgraph]`/`[lsp]` extras, `find_connections` bidirectional callees + `resolver_source`/`resolver_confidence` provenance
- **v0.13.0** (2026-06-03): pyan3 cross-module caller edges, `find_connections` recall 0.57→0.95, split_block call-edge recovery, Windows path fixes
- **v0.12.4** (2026-05-29): MCP server bug fixes (`switch_project`, `list_embedding_models`, `CodeGraphStorage.clear()`), `ServiceLocator` removal (ADR-0005)
- **v0.12.3** (2026-05-29): `chunking↔graph` import cycle eliminated (24 files moved), `SearchOrchestrator` refactor
- **v0.12.2** (2026-05-26): `IndexWriteStage` stale-resource fix, embedding OOM recovery, `GraphIntegration` shared initializer, jina-reranker-v3 default
- **v0.12.1** (2026-05-25): split_block call + relationship edges, Starlette 307 fix, `RelationshipAnalyzer` moved to `search/`
- **v0.12.0** (2026-05-25): StreamableHTTP transport migration (SSE → `/mcp` single endpoint)
- **v0.11.7** (2026-05-03): Defense-in-depth for destructive operations (storage sentinel, path-containment guards)
- **v0.11.6** (2026-04-21): Incremental-index hashing parity (`ChangeDetector` gets `supported_extensions`)
- **v0.11.5** (2026-04-21): Full-index DAG hashing performance (stat-based hash for non-code files, ~100× speedup)
- **v0.10.x** (2026-04-06 – 2026-04-21): ONNX backend, parallel chunker, OTel tracing, call-graph refactor, security patches
- **v0.9.5** (2026-04-06): Installer fixes (cu118→cu128, dead preview install, hardcoded Python path), 8 CI review fixes (intent classifier caching, semantic_weight clamping, O(1) graph name index, reranker score propagation, thread-safe stdout, benchmark compat)
- **v0.9.4** (2026-04-06): Ego-graph QW1-QW5, semantic intent classification, SSCG benchmark pipeline, 5 MCP bug fixes, startup performance, security patches
- **v0.9.3** (2026-02-21): Resource lifecycle stabilization, mandatory release before reindex, RAM fallback
- **v0.9.2** (2026-02-06): SSCG benchmark results, documentation alignment, search quality fixes, security hardening
- **v0.9.1** (2026-01-30): Dependency cleanup (76 packages removed), Python style guide alignment
- **v0.9.0** (2026-02-01): SSCG Phase 1-5 integration, A1 (Intent-Adaptive Edge Weight Profiles), A2 (File-Level Module Summary Chunks), B1 (Community-Level Summary Chunks), dependency cleanup (76 packages removed), k=4 standardization, perfect Recall@4 (1.00)
- **v0.8.7** (2026-01-29): SSCG implementation complete (21 relationship types, PageRank centrality, edge-weighted BFS)
- **v0.8.6** (2026-01-16): Performance infrastructure (timing decorators, cache TTL)
- **v0.8.5** (2026-01-15): Chunk type enum expansion (merged, split_block)
- **v0.8.4** (2026-01-06): Ultra format bug fix & field rename
- **v0.8.3** (2026-01-06): Documentation cleanup & CLAUDE.md restructure
- **v0.8.2** (2026-01-04): Production updates
- **v0.7.5** (2026-01-03): HybridSearcher reference mismatch fix
- **v0.7.1** (2025-12-27): Release Resources menu option + bug fixes
- **v0.7.0** (2025-12-22): Output formatting, mmap storage, entity tracking
- **v0.6.4** (2025-12-16): Qwen3 Instruction Tuning & Matryoshka MRL
- **v0.6.3** (2025-12-13): Drive-Agnostic Project Paths & Filter Persistence Fix
- **v0.6.2** (2025-12-13): VRAM Tier Management & TTY Auto-Detection
- **v0.6.1** (2025-12-03): UX Improvements (progress bars, filter fixes, snapshot deletion)
- **v0.6.0** (2025-11-28): Production Release (self-healing BM25, persistent projects)
- **v0.5.16** (2025-11-24): Graph Resolver Extraction + Persistent Project Selection
- **v0.5.15** (2025-11-19): Phase 4 Import-Based Resolution (~90% accuracy)
- **v0.5.14** (2025-11-19): Phase 3 Assignment Tracking
- **v0.5.13** (2025-11-19): Phase 2 Type Annotation Resolution
- **v0.5.12** (2025-11-19): Phase 1 Self/Super Resolution
- **v0.5.5** (2025-11-13): Low-Level MCP SDK migration
- **v0.5.4** (2025-11-10): Multi-Model Query Routing
- **v0.5.3** (2025-11-06): Graph-Enhanced Search + MCP tool output fix
- **v0.5.2** (2025-10-20): Comprehensive validation (256 queries, 100% pass rate)
- **v0.4.0** (2025-10-01): GPU optimization, per-model indices

---

## Related Projects

### Multi-Project Documentation

- **Stream Diffusion CLAUDE.md** - Updated with v0.5.2 validation metrics (2025-10-23)

---

## Additional Resources

### Archive

- `_archive/` directory contains historical content (738+ files, excluded from index)
- `_archive/README.md` - Archive restoration guide

### Slash Commands (.claude/commands/)

- `/auto-git-workflow` - Automated commit→merge→push workflow
- `/create-pr` - Create pull request with template
- `/run-merge` - Merge branches with validation
- `/validate-changes` - Pre-commit validation

### Custom Skills (.claude/skills/)

- `mcp-search-tool` - Semantic search skill for Claude Code

---

## Navigation Tips

- **New users**: Start with [Getting Started](#getting-started)
- **MCP tools**: See [MCP_TOOLS_REFERENCE.md](MCP_TOOLS_REFERENCE.md)
- **Advanced features**: See [ADVANCED_FEATURES_GUIDE.md](ADVANCED_FEATURES_GUIDE.md)
- **Troubleshooting**: Check [Git Automation](#git-automation) and [Testing & Validation](#testing--validation)

---

**Last Updated**: 2026-06-11 (v0.16.0 — code-review hardening: Batch 1/2A/2B correctness + concurrency fixes; 2,533 tests)
