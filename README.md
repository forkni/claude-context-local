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

**Local-first semantic code search for Claude Code.** Hybrid search combining semantic understanding with text matching, running 100% locally. No API keys, no costs, your code never leaves your machine.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![codecov](https://codecov.io/gh/forkni/claude-context-local/branch/development/graph/badge.svg)](https://codecov.io/gh/forkni/claude-context-local)

## Highlights

- **Hybrid Search**: BM25 + semantic fusion — on the [SSCG benchmark](#benchmark-results) (2026-07-27, 63 queries, hybrid k=7): **Hit@5 100%, MRR 0.787-0.796, Recall@7 0.719-0.734, Recall@20 0.80-0.81** - [benchmarks](docs/BENCHMARKS.md)
- **Neural Reranking**: Cross-encoder models (default: `Alibaba-NLP/gte-reranker-modernbert-base`; alternatives: jinaai/jina-reranker-v3, Qwen3-Reranker-0.6B) improve ranking quality by 15-25% - [advanced features](docs/ADVANCED_FEATURES_GUIDE.md#neural-reranking-configuration)
- **SSCG Integration**: Structural-Semantic Code Graph — 21 relationship types, PageRank centrality reranking; see [benchmarks](docs/BENCHMARKS.md) for mode-comparison history
- **63% Token Reduction**: Real-world benchmarked mixed approach - [benchmarks](docs/BENCHMARKS.md)
- **Layered Call-Graph Resolver Pipeline**: `find_connections` returns callers **and** callees with per-entry provenance (`resolver_source`, `resolver_confidence`). Confidence ladder: AST 0.5/0.7 → pyan 0.75 → LibCST 0.90 → LSP 0.98. Install `pip install -e ".[callgraph]"` for pyan3 + LibCST; core is Apache-2.0-clean — [caller recall benchmark](docs/BENCHMARKS.md#caller-recall-benchmark)
- **OTel Tracing** (opt-in): Zero-overhead `traced_block` / `@timed` spans across the search and index pipeline — export to Jaeger, Tempo, or any OTLP collector. See [Observability](docs/OBSERVABILITY.md).
- **Persistent Chunk Embedding Cache**: content-hash-keyed cache of chunk embedding vectors cuts a full reindex's embedding phase from ~34s to well under 1s once the codebase is unchanged; invalidates automatically on model or precision/backend changes - [configuration](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md#chunk-embedding-cache-configuration)
- **20 File Extensions**: Python, JS, TS, Go, Rust, C/C++, C#, GLSL with AST/tree-sitter chunking
- **18 MCP Tools** (10 core + 8 advanced, gated behind `MCP_EXPOSE_ADVANCED_TOOLS`): Complete Claude Code integration - [tool reference](docs/MCP_TOOLS_REFERENCE.md)
- **Source-Position Reranking** (opt-in, `source_order_output=true`): Groups results by file, sorted by line number instead of relevance — LLMs read code in logical order (+5.3% accuracy, DOS RAG); relevance order is the default since v0.18.0
- **Centrality-Adaptive BM25 Boost**: High-centrality nodes (base classes, utilities) get BM25 score boost — compensates for single-vector ceiling (DeepMind LIMIT, ICLR 2026)
- **File-Role Tagging**: Chunks tagged `role:src/test/doc/config` at index time — enables role-aware ranking and precision boosts

**Status**: ✅ Production-ready | 5,540 unit tests passing (+102 fast_integration, +19 integration, +108 slow_integration) | All 18 MCP tools operational | Concurrency-safe | Windows 10/11

*Last reviewed: 2026-08-02*

## What's New in v0.23.0

- **MCP Python SDK v1 → v2 migration**: six JSON-RPC handlers converted to the v2 constructor-kwarg pattern; wire format unchanged, verified end-to-end
- **Three subsystems removed**: community-detection/summarization (ADR-0015), DSPy evaluation (ADR-0016, 4,849 lines), and the ONNX inference path
- **Per-project config overrides + auto-tune probe** (ADR-0014) and `exclude_same_file` on `find_similar_code`
- **Richer evaluation**: `recall@20`/`recall@50`/`pool_hit_rate`/`file_acc@k` metrics, a CI regression gate, and the golden dataset expanded 108 → 145 queries
- **Config field liveness audit** (ADR-0020): 7 previously-hardcoded settings wired to real config control (byte-identical default behavior), 6 dead fields removed
- ⚠️ **Breaking**: `nomic-ai/CodeRankEmbed`, `Alibaba-NLP/gte-modernbert-base`, and `Qwen/Qwen3-Reranker-4B` removed from the model registries — a deployed config pinned to one of these will fail to load until repointed. See [CHANGELOG.md](CHANGELOG.md)

Previous release notes: [CHANGELOG.md](CHANGELOG.md)

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

- "Configure search mode to hybrid with 0.35 BM25 and 0.65 dense weights"
- "Show me the current search configuration"
- "Switch the embedding model to BGE-M3"

Or use the interactive menu:

```bash
start_mcp_server.cmd → 3 (Search Configuration)
```

## Search Modes

Quality metrics below are from the [SSCG benchmark](#benchmark-results) (2026-06-08, 13-query dataset, k=10) and are **stale** — the canonical golden dataset (`evaluation/golden_dataset.json`) has since grown to 77 queries across 6 categories, and a separate expanded set (`evaluation/golden_dataset_expanded.json`) now holds 145. No per-mode (hybrid/semantic/bm25) A/B has been rerun on either; see [Benchmark Results](#benchmark-results) for the current hybrid-only baseline. This table describes mode performance on the old 13-query benchmark only — not general reliability guarantees.

| Mode | Description | SSCG Quality (2026-06-08, k=10) | Status |
|------|-------------|-------------------------------|--------|
| **hybrid** (default) | BM25 + Semantic fusion | MRR 0.797, R@5 0.689, R@7 0.736, R@10 0.770, Hit@5 100% | ✅ Operational |
| **semantic** | Dense vector search | MRR 0.797, R@5 0.676, R@10 0.758, Hit@5 100% | ✅ Operational |
| **bm25** | Text-based sparse search | MRR 0.797, R@5 0.689, R@10 0.777, Hit@5 100% | ✅ Operational |

**Configuration**: See [Hybrid Search Configuration Guide](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md)

## MCP Tool Reference (For Claude Code)

These tools are available to Claude Code as `mcp__code-search__*` functions. You don't invoke them directly - Claude Code uses them automatically when you ask relevant questions. The [SKILL.md](.claude/skills/mcp-search-tool/SKILL.md) file guides Claude's tool usage for optimal results.

### Core Search

- `search_code` - Main semantic/hybrid search
- `index_directory` - Index project for searching
- `find_similar_code` - Find code similar to chunk
- `find_connections` - Dependency & impact analysis
- `find_path` - Shortest path between code entities

### Configuration

- `configure_search_mode` - Set hybrid search parameters
- `configure_reranking` - Configure neural reranking
- `configure_chunking` - Configure code chunking settings
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

> **Note:** The server tracks one active project and one active embedding model at a
> time (process-wide state). `switch_project`, `switch_embedding_model`, and the
> `configure_*`/`clear_index`/`delete_project` tools change that shared state for every
> connected client, not just the caller.

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
| GLSL | `.glsl`, `.frag`, `.vert`, `.comp`, `.geom`, `.tesc`, `.tese`, `.glslinc` | Tree-sitter |

**Total**: 20 file extensions across 9 programming languages

## Requirements

- **Python**: 3.11+ (tested with 3.11 and 3.12)
- **RAM**: 4GB minimum (8GB+ recommended for large codebases)
- **Disk**: 2-4GB free space (model cache + embeddings)
  - EmbeddingGemma: ~1.2GB
  - BGE-M3: 1–1.5 GB (default)
  - Qwen3-0.6B: ~2.3GB
  - F2LLM-v2-0.6B: ~2.2GB
- **Windows**: Windows 10/11 with PowerShell
- **PyTorch**: `>=2.10.0,<2.11.0` (auto-installed with CUDA 12.8 primary / CUDA 12.4 fallback support; ceiling reflects the pinned `cu128` wheel index's current maximum)
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
  4. Configure Neural Reranker        - Cross-encoder reranking (+15-25% quality)
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

- **BM25 Weight**: 0.0-1.0 (default: 0.35) - keyword/text matching strength
- **Dense Weight**: 0.0-1.0 (default: 0.65) - semantic understanding strength

Weights should sum to 1.0.

#### 4. Select Embedding Model

| Model | VRAM | Best For |
|-------|------|----------|
| **BGE-M3** | 1-1.5GB | Default — hybrid search, balanced quality/VRAM |
| **EmbeddingGemma-300m** | ~1.2GB | Lightweight, low-VRAM systems |
| **Qwen3-0.6B** | 2.3GB | High efficiency, excellent value |
| **F2LLM-v2-0.6B** | 2.2GB | Best retrieval ordering (MTEB avg 66.47) |

**Instant switching**: <150ms with no re-indexing required.

#### 5. Configure Parallel Search

Enable/disable parallel execution of BM25 and semantic search:

- **Enabled** (default): ~15-30ms faster, higher CPU usage
- **Disabled**: Sequential execution, lower resource usage

#### 6. Configure Neural Reranker

Cross-encoder model that re-scores results for 15-25% quality improvement:

- **Enable/Disable**: Requires GPU with ≥2GB VRAM
- **Top-K Candidates**: Number of results to rerank (default: 30, range: 5-100)

#### 7. Configure Entity Tracking

Extract additional code relationships during indexing:

- **Enabled**: Tracks enum members, default values, context managers (~25% slower indexing)
- **Disabled** (default): Core relationships only (inheritance, imports, decorators)

#### 8. Reset to Defaults

Resets all settings to: hybrid mode, 0.35/0.65 weights, GPU auto-detect.

### Quick Access Options

From the main menu:

- **M - Quick Model Switch**: Fast model switching without entering submenu
- **F - Configure Output Format**: Control token usage (verbose/compact/ultra)

### Environment Variables (Advanced)

For automation and CI/CD, settings can be overridden via environment variables. See [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md) for complete list.

### Model Selection

| Model | Dimensions | VRAM | Best For |
|-------|------------|------|----------|
| **BGE-M3** | 1024 | 1-1.5GB | Default — hybrid search, balanced quality/VRAM |
| **EmbeddingGemma-300m** | 768 | ~1.2GB | Lightweight, low-VRAM systems |
| **Qwen3-0.6B** | 1024 | 2.3GB | High efficiency, excellent value |
| **F2LLM-v2-0.6B** | 1024 | 2.2GB | Best retrieval ordering (MTEB avg 66.47) |

**Instant model switching**: <150ms with per-model index storage - no re-indexing needed!

**See also**: [Advanced Features Guide](docs/ADVANCED_FEATURES_GUIDE.md)

## Architecture

```
claude-context-local/
├── chunking/          # Multi-language AST/tree-sitter parsing
│   └── relationships/ # Call graph extraction & relationship extractors
├── embeddings/        # Model loading & embedding generation
├── search/            # FAISS + BM25 hybrid search, graph-scoring stage
├── merkle/            # Incremental indexing with change detection
├── graph/             # Graph storage & queries
├── mcp_server/        # MCP server implementation (18 tools)
├── tools/             # Interactive indexing & search utilities
├── scripts/           # Installation & configuration
├── docs/              # Complete documentation
└── tests/             # 5,540 unit tests (+102 fast_integration, 19 integration, 108 slow_integration)
```

**Storage** (~/.claude_code_search):

- `models/` - Downloaded embedding models
- `index/` - FAISS indices + metadata (SQLite)
- `merkle/` - Incremental indexing snapshots

**Complete architecture**: [Architecture Documentation](docs/ADVANCED_FEATURES_GUIDE.md)

## Benchmark Results

### Latest Validation (2026-08-04, hybrid-only, k=10)

Provenance: `evaluation/CANON_20260804_INTENT_ON_REPAIRED.md`, `scripts/benchmark/run_sscg_benchmark.py --project-path .`, default config (`bm25_weight=0.35`, `dense_weight=0.65`, `query_expansion.enabled=False`, `intent.enabled=True`). Re-pinned to `canon_h1` after the intent-layer disposition (ADR-0026 → ADR-0029): `canon_f1` (ADR-0026) captured the `canon_B1b` intent-on arm and found the layer's only measurable effect was two redirects, one of which (`find_path`) returned nothing at all — regex misfires on ordinary prose; `canon_g1` (ADR-0028) defaulted `intent.enabled=False` and deleted the dead `find_path` redirect as a stopgap; `canon_h1` (ADR-0029) repaired the `find_similar` redirect's anchor-symbol extractor, passed a pre-registered gate on both datasets, and flipped `intent.enabled` back to `True` as the shipped default. The table below cites `canon_h1`'s **intent-on arm** — the figures matching the shipped default — not its intent-off control view (published alongside it in the canon doc for anyone running with the layer disabled via `search_overrides.json`). Only **hybrid** (the default mode) has been measured at this generation — no per-mode A/B has been rerun since 2026-06-08 (historical table below).

| Dataset | Queries | MRR | Recall@5 | Recall@10 | NDCG@5 | pool_hit_rate |
|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8418** (`canon_h1` intent-on arm) | 0.6967 | 0.8036 | 0.7157 | 0.9048 |
| Expanded (`golden_dataset_expanded.json`, non-D, 133 queries) | 133 | **0.6750** (`canon_h1` intent-on arm) | 0.6751 | 0.7766 | 0.6428 | 0.9023 |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8836** (`canon_h1`) | 0.6818 | 0.7963 | 0.7086 | 1.0000 |
| F-via-similar (F-category only, 9 queries) | 9 | **0.8519** (`canon_h1`) | 0.5690 | 0.7185 | 0.6064 | — |

Run-to-run noise band is **±0.02 MRR**, measured directly via a same-code control (two 94-query runs on unchanged code landed 0.701 and 0.683). Treat any delta smaller than that as noise. Note the two F-via-similar rows above: the whole-63-query aggregate (0.8836) and the true F-category-only mean (0.8519) are different numbers over different query sets — a prior generation of this table published only the whole-aggregate figure under a "9-query" caption and mixed a whole-aggregate `file_recall@5` into the F-only row; this generation corrects both.

**Comparability breaks** — do not read the numbers above as a trend against older figures in this repo's history:

- ADR-0023 (`canon_B1`, 2026-08-02, mrr 0.8249) routed the harness through `SearchOrchestrator.run()` instead of a direct `HybridSearcher.search()` call — not comparable to anything measured before it.
- ADR-0024 (`canon_C3`, mrr 0.8348/0.6816/0.8907) re-pinned after the C3 searcher-construction dedup and config-metadata fixes; see `evaluation/CANON_20260803.md`.
- `canon_d1`/`canon_d2` (`evaluation/CANON_20260804.md`) re-pinned after 34 further commits and a 2-query dataset top-up (H035, H068); MRR moved by less than the ±0.02 noise band on the canonical/F views and by −0.0225 on the expanded view (−0.0162 code drift + −0.0063 dataset change).
- ADR-0026 (`canon_f1`, `evaluation/CANON_20260804_B1B.md`) re-pinned after further commits and captured `canon_B1b`, the first intent-on arm — the measurement that started the intent-layer disposition below.
- ADR-0028 (`canon_g1`, `evaluation/CANON_20260804_INTENT_OFF.md`) defaulted `intent.enabled=False` and removed the dead `find_path` redirect as a stopgap while the `find_similar` extractor bug was diagnosed.
- ADR-0029 (`canon_h1`, `evaluation/CANON_20260804_INTENT_ON_REPAIRED.md`) repaired `_extract_symbol_from_query`, passed the pre-registered similarity-query gate on both datasets, and re-enabled `intent.enabled=True` as the shipped default — `canon_h1`'s intent-on arm is the published baseline above.
- The 2026-07-28 golden-dataset repair (`6df36db`) changed scoring for 3-part `split_block` chunks; nothing measured before that commit is comparable to what's measured after.
- The 2026-08-02 H-category promotion grew the expanded set 108→145 queries (94→131 non-D); the 2026-08-04 top-up grew it further to 147 (133 non-D). H queries are harder by construction (single-file, ≤2 golds), so treat each generation's figure as a separate measurement, not a before/after comparison.
- `0.797` in the historical table below (2026-06-08, 13 queries) predates the golden-dataset repair, the H-promotion, the SDK v2 migration, and every re-pin since; kept only for continuity.

### Live MCP pipeline eval (k=7, orchestrator + multi-hop, 2026-08-01)

`run_mcp_pipeline_eval.py --k 7`, categories A/B/C (n=45) — exercises the full multi-hop + ego-graph + reranker orchestrator path, not just the bare searcher:

| MRR | Recall@7 | Hit@7 | NDCG@5 | Recall@5 |
|---|---|---|---|---|
| **0.9019** | **0.7741** | 97.8% | 0.7278 | 0.7122 |

### Historical: 2026-06-08 mode comparison (13-query dataset, superseded)

Kept for continuity only — do not compare against the tables above. No current per-mode (hybrid/semantic/bm25) A/B exists on the 2026-08-01 baseline; only hybrid was measured there.

| Mode | MRR | Recall@5 | Recall@7 | Recall@10 | Hit@5 | Best for |
|------|-----|----------|----------|-----------|-------|----------|
| **Hybrid** (default) | 0.797 | 0.689 | 0.736 | 0.770 | 13/13 (100%) | Deep recall, balanced |
| **BM25** | 0.797 | 0.689 | 0.723 | 0.777 | 13/13 (100%) | Exact symbol lookup |
| **Semantic** | 0.797 | 0.676 | 0.723 | 0.758 | 13/13 (100%) | Concept/intent queries |

A separate embedder A/B (2026-07-26, 63-query original golden set, `F2LLM-v2-0.6B` vs `Qwen3-Embedding-0.6B`) showed a consistent MRR gain for F2LLM (+0.026/+0.027 mean, 4/4 runs); recall and latency were flat. F2LLM is available as an opt-in embedding model — see `evaluation/EMBEDDER_F2LLM_AB_20260726.md` for the full protocol and results.

See [benchmarks](docs/BENCHMARKS.md) for full SSCG retrieval metrics and token efficiency results (63% reduction).

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
- [Advanced Features Guide](docs/ADVANCED_FEATURES_GUIDE.md) - Graph search, ego-graph expansion, optimization
- [Call-Graph Tuning](docs/CALL_GRAPH_TUNING.md) - Resolver pipeline tuning, `min_confidence`, LSP diagnostics
- [CLAUDE.md Template](docs/CLAUDE_MD_TEMPLATE.md) - **Setup guide for your projects** (see below)

### Configuration & Performance

- [Hybrid Search Configuration](docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md) - Search modes and tuning
- [Observability](docs/OBSERVABILITY.md) - OTel tracing (Jaeger/Tempo/Grafana), env vars, overhead
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

- [Testing Guide](tests/TESTING_GUIDE.md) - Running tests (5,540 unit tests, 100% pass rate)
- [Git Workflow](docs/GIT_WORKFLOW.md) - Contributing guidelines
- [Version History](docs/VERSION_HISTORY.md) - Changelog

**Complete index**: [Documentation Index](docs/DOCUMENTATION_INDEX.md)

## Contributing

Contributions welcome! Quick start:

1. Fork and clone the repository
2. Install: `install-windows.cmd` or `pip install -e .[dev,test]`
3. Run tests: `./scripts/test/run_tests.sh tests/unit/ -q` (the project `.venv` is not auto-activated; bare `pytest` resolves to system Python and fails the venv guard in `tests/conftest.py`)
4. Create a branch from `development`
5. Submit PR to `development` branch

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

Licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.

## Research References

This project's architecture is informed by the following research:

| Paper | Venue | Key Contribution |
|-------|-------|------------------|
| **LogicLens: Leveraging Semantic Code Graph for Multi-Repository Exploration** | arXiv 2601.10773, 2026 | Three-phase graph construction (structural + semantic + entity); ReAct agent with specialized tools |
| **HermesSim: Semantics-Oriented Graphs** (He et al.) | USENIX Security 2024 | Three-subgraph decomposition (data/control/effect) with multi-head fusion; foundation for intent-adaptive graph weights |
| **Orchestrating Graph and Semantic Searches for Code Analysis** (Prast et al.) | TNO 2025 | BOLAA orchestration; validates separate graph/vector DB architecture and summary-first retrieval |

## Inspiration & Acknowledgments

This project draws inspiration from several excellent semantic code search implementations:

| Project | Author | Key Contribution |
|---------|--------|------------------|
| [claude-context](https://github.com/zilliztech/claude-context) | Zilliz | Original concept, cloud-based architecture, hybrid search with Milvus |
| [claude-context-local](https://github.com/FarhanAliRaza/claude-context-local) | Farhan Ali Raza | Local-first approach, cross-platform support |
| [chunkhound](https://github.com/chunkhound/chunkhound) | ChunkHound | Real-time indexing with watchdog, extensive language support (30+) |
| [codanna](https://github.com/bartolli/codanna) | Bartolli | High-performance Rust implementation, memory-mapped storage, profile system |
| [TOON Format](https://github.com/toon-format/toon) | TOON Format | Tabular Object Output Notation - compact data format inspiration for output formatting |

This Windows-focused implementation builds upon these foundations while adding unique capabilities including per-model index storage and Python call graph analysis.

I am grateful to these projects and their maintainers for pioneering semantic code search for AI assistants.
