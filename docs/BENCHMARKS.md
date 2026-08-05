# Performance Benchmarks - Real-World Usage

This document presents comprehensive performance benchmarks based on **real-world usage** of the Claude Context MCP semantic code search system in actual development workflows (December 2025).

---

## Overview

These benchmarks measure token efficiency and accuracy across three different code exploration approaches using 25 standardized queries that represent typical development tasks. The results demonstrate the practical value of MCP semantic search as a support tool for complex queries.

**Test Date**: December 21, 2025
**Project**: claude-context-local (semantic code search MCP server)
**Queries**: 25 standardized code exploration questions
**Measurement**: Claude Code `/cost` command (actual token consumption)

---

## Executive Summary

| Metric | MCP Only | Traditional | Mixed | Winner |
|--------|----------|-------------|-------|--------|
| **Total Tokens** | 444,100 | 488,100 | **180,000** | Mixed |
| **Accuracy** | 24/25 (96%) | 24/25 (96%) | **25/25 (100%)** | Mixed |
| **Token Reduction** | 9% | baseline | **63%** | Mixed |
| **Time** | ~5 min | ~15 min | ~8 min | Mixed |
| **Avg Tokens/Query** | 17,764 | 19,524 | **7,200** | Mixed |

**Key Finding**: The **Mixed approach** (combining MCP semantic search with targeted traditional tools) delivers the best results in both accuracy (100%) and token efficiency (63% reduction).

---

## Testing Methodology

### Test Setup

Each test was conducted in a **fresh Claude Code session** to ensure accurate token measurement:

1. **Session Initialization**: Record initial token count via `/cost` command
2. **Query Execution**: Execute all 25 queries in order using specified approach
3. **Results Recording**: Document answers, accuracy, and token usage
4. **Session Completion**: Record final token count via `/cost` command

### Three Test Approaches

#### Test 1: Traditional Tools Only

- **Allowed**: `Glob`, `Grep`, `Read` only
- **Forbidden**: All MCP tools (search_code, find_connections)
- **Workflow**: Find files → Search content → Read files
- **Purpose**: Establish baseline token consumption

#### Test 2: MCP Tools Only

- **Allowed**: `search_code`, `find_connections`, MCP project tools
- **Forbidden**: Glob, Grep, Read
- **Workflow**: Semantic search → Direct answers
- **Purpose**: Measure MCP-only efficiency

#### Test 3: Mixed Approach (Optimal)

- **Allowed**: All tools
- **Strategy**: Use best tool for each query type
  - MCP search_code: Semantic/conceptual queries (80%)
  - MCP find_connections: Dependency analysis (4%)
  - Glob + Read: Known file patterns (8%)
  - Grep + Read: Exact text matching (8%)
- **Purpose**: Demonstrate real-world optimal usage

### Standard Query Set

All three tests used identical 25 queries covering:

| Category | Count | Examples |
|----------|-------|----------|
| Entry Points | 2 | "Where is main MCP server entry point?" |
| Architecture | 3 | "How does semantic search work?" |
| Configuration | 3 | "What embedding models are supported?" |
| Implementation | 7 | "How are Python files chunked?" |
| Algorithms | 3 | "What is hybrid search algorithm?" |
| Features | 4 | "How does multi-model routing work?" |
| Tools | 2 | "How is search_code implemented?" |
| Testing | 1 | "What unit tests exist for output formatting?" |
| Performance | 1 | "What is lazy loading strategy?" |

---

## Results Summary

### Token Efficiency Comparison

| Approach | Total Tokens | Per Query | Reduction vs Traditional |
|----------|--------------|-----------|--------------------------|
| **Traditional** | 488,100 | 19,524 | 0% (baseline) |
| **MCP Only** | 444,100 | 17,764 | 9% |
| **Mixed** | **180,000** | **7,200** | **63%** |

### Accuracy Comparison

| Approach | Correct Answers | Accuracy Rate | Failed Queries |
|----------|-----------------|---------------|----------------|
| Traditional | 24/25 | 96% | 1 (Python chunking file not found) |
| MCP Only | 24/25 | 96% | 1 (test file not indexed) |
| **Mixed** | **25/25** | **100%** | **None** |

### Time Efficiency

| Approach | Total Time | Time/Query | Speed vs Traditional |
|----------|------------|------------|----------------------|
| Traditional | ~15 min | 36 sec | 1x (baseline) |
| MCP Only | ~5 min | 12 sec | 3x faster |
| **Mixed** | ~8 min | 19 sec | 1.9x faster |

---

## Key Finding: Mixed Approach Optimal

The **Mixed approach** combining MCP semantic search (80%) with targeted traditional tools (20%) achieved:

### Best Accuracy

- **100% success rate** (25/25 queries)
- Zero failed queries
- Correct answers for all query types

### Best Token Efficiency

- **63% token reduction** vs traditional file reading
- **7,200 tokens per query** average
- **308,100 tokens saved** total

### Tool Distribution (Mixed Approach)

- **MCP search_code**: 20 queries (80%) - Semantic queries
- **MCP find_connections**: 1 query (4%) - Dependency analysis
- **Glob + Read**: 1 query (4%) - Known file patterns
- **Grep + Read**: 2 queries (8%) - Exact text matching
- **Read only**: 1 query (4%) - Direct file access

### Why Mixed Approach Wins

1. **Leverages MCP strengths** - Semantic understanding for complex queries
2. **Fills MCP gaps** - Traditional tools for exact matches and known paths
3. **Reduces overhead** - Smaller session context than pure approaches
4. **Optimal tool selection** - Best tool for each query type

---

## MCP Search as Support Tool

These benchmarks validate **MCP semantic search as an excellent support tool** for development workflows.

### When to Use MCP Search

MCP search excels at:

| Query Type | Why MCP Is Better | Example |
|------------|-------------------|---------|
| **"How does X work?"** | Semantic understanding | "How does hybrid search work?" |
| **"Where is X defined?"** | Class/function discovery | "Where is CodeEmbedder class?" |
| **"What calls X?"** | Dependency analysis | "What calls handle_search_code?" |
| **Conceptual queries** | Natural language understanding | "Multi-model query routing logic" |
| **Cross-file patterns** | Relationship discovery | "Call graph resolution patterns" |

### When to Use Traditional Tools

Traditional tools are better for:

| Query Type | Why Traditional Is Better | Example |
|------------|---------------------------|---------|
| **Known filename** | Direct file access | "Read tool_registry.py" |
| **Exact text match** | Precise pattern matching | "Find 'def get_tools'" |
| **Configuration lists** | Quick extraction | "List all language configs" |
| **Known file paths** | No search needed | "Read tests/test_output_formatter.py" |

### Recommended Workflow

**For Most Queries** (80%):

1. Start with `search_code("<natural language query>")`
2. Use semantic search to narrow scope
3. Read results directly from MCP response

**For Exact Matches** (10%):

1. Use `Grep` for known patterns
2. Fallback to `search_code` if Grep fails

**For Known Files** (10%):

1. Use `Read` directly when path is known
2. Use `Glob` for filename patterns

---

## Tool Selection Guidelines

| Scenario | Optimal Tool | Rationale |
|----------|--------------|-----------|
| "How does authentication work?" | `search_code` | Semantic/conceptual query |
| "Where is User class defined?" | `search_code(chunk_type="class")` | Class definition with filter |
| "What functions call login()?" | `find_connections` | Dependency analysis |
| "List all test files" | `Glob("**/test_*.py")` | Known pattern |
| "Find exact string 'LANGUAGE_CONFIGS'" | `Grep` | Exact text match |
| "Read config.py" | `Read` | Known file path |
| "Find files related to indexing" | `search_code("indexing workflow")` | Semantic file discovery |

---

## Per-Approach Analysis

### Test 1: Traditional Tools Only

**Performance**:

- Total tokens: 488,100 (baseline)
- Accuracy: 24/25 (96%)
- Time: ~15 minutes

**Tool Usage**:

- Glob: 11 calls
- Grep: 14 calls
- Read: 20 calls (~5,985 lines read)

**Strengths**:

- No setup required (works immediately)
- 100% precision for known patterns
- Direct file access when path is known

**Weaknesses**:

- Massive token consumption (19,524 per query)
- Context accumulation over session
- No semantic understanding
- Multiple rounds of exploration needed
- Cannot find "similar" or "related" code
- Must read entire files (no function-level granularity)

**Failed Query**:

- Query #4 (Python chunking): File not found at expected path

---

### Test 2: MCP Tools Only

**Performance**:

- Total tokens: 444,100 (9% reduction)
- Accuracy: 24/25 (96%)
- Time: ~5 minutes

**Tool Usage**:

- search_code: 25 calls
- find_connections: 0 calls
- Zero traditional tool calls (as required)

**Strengths**:

- High accuracy (96%) with zero file reading
- Token efficiency: ~713 tokens per query (effective)
- Sub-second search times (68-105ms hybrid mode)
- Automatic context preservation via multi-hop search
- Call graph integration in results
- Natural language queries work effectively

**Weaknesses**:

- Generic queries may match wrong files
- Requires specific queries for precision
- Test files not indexed (caused 1 failure)

**Failed Query**:

- Query #19 (output formatter tests): Query too generic, matched verification script instead

**Effective Query Cost**:

- While total session consumed 444K tokens, effective "new information" from MCP queries was only ~17.8K tokens (4% of total)
- Remaining 96% was context overhead (CLAUDE.md, skill documentation, conversation history, system messages)
- **Per-query effective cost**: ~713 tokens (vs ~2,796 for traditional)

---

### Test 3: Mixed Approach

**Performance**:

- Total tokens: 180,000 (63% reduction)
- Accuracy: 25/25 (100%)
- Time: ~8 minutes

**Tool Usage**:

- search_code: 20 calls (80%)
- find_connections: 1 call (4%)
- Glob: 1 call (4%)
- Grep: 1 call (4%)
- Read: 3 calls (12%)

**Strengths**:

- Perfect accuracy (100%)
- Best token efficiency (7,200 per query)
- Optimal tool selection based on query type
- Excellent semantic scores (>0.90 for 10 queries)
- Multi-model routing working correctly

**Why It Won**:

- Lower session overhead (smaller context)
- Used MCP for 80% of queries (semantic queries)
- Used traditional for 20% (exact matches, known files)
- Intelligent fallback strategies

**Tool Selection Examples**:

- Query #7 (MCP tools list): Grep → Read (exact function name)
- Query #11 (Tree-sitter langs): Grep → Read (extract list)
- Query #19 (Formatter tests): Glob → Read (known pattern)
- Query #20 (search_code impl): find_connections (dependency analysis)

---

## Cost Analysis

### API Cost Estimates

Based on Claude Sonnet 4.5 pricing ($3/1M input, $15/1M output):

| Approach | Total Tokens | Estimated Cost | Cost per Query |
|----------|--------------|----------------|----------------|
| **Traditional** | 488,100 | $2.63 | $0.105 |
| **MCP Only** | 444,100 | $2.40 | $0.096 |
| **Mixed** | 180,000 | $0.97 | $0.039 |

### Cost Savings

**Daily Usage** (100 queries):

- Traditional: $10.50/day
- Mixed: $3.90/day
- **Savings**: $6.60/day (63%)

**Monthly Usage** (20 days, 2,000 queries):

- Traditional: $210/month
- Mixed: $78/month
- **Savings**: $132/month (63%)

---

## Multi-Model Routing Performance *(removed in v0.19.0)*

> **Note**: Multi-model query routing was removed in v0.19.0. The data below is from the December 2025 mixed-approach study when multi-model routing was active. The current system uses a single configurable embedding model (default: `BAAI/bge-m3`; `F2LLM-v2-0.6B` available as an opt-in — see the SSCG Retrieval Benchmark section below).

The Mixed approach leveraged multi-model query routing:

### Model Distribution (historical, v0.5.4–v0.18.x)

| Model | Queries | Confidence Range | Use Case |
|-------|---------|------------------|----------|
| **BGE-M3** | 10 queries | 0.0 - 0.5 | Workflow/configuration queries |
| **Qwen3** | 11 queries | 0.1 - 0.6 | Implementation/algorithm queries |
| **CodeRankEmbed** | 4 queries | 0.15 - 0.45 | Specialized algorithms (Merkle, RRF) |

### Routing Accuracy (historical)

- **100%** - All models returned relevant results
- Automatic model selection based on query content
- No manual model specification needed

### High-Score Semantic Results

Queries achieving excellent semantic scores (>0.90):

1. **Reranker** (score 1.0) - Perfect match
2. **FAISS index** (score 0.98) - Near-perfect
3. **Multi-hop search** (score 0.98) - Near-perfect
4. **SearchConfig** (score 0.96) - Excellent
5. **Merkle indexing** (score 0.92) - Excellent

---

## Recommendations

### For Development Workflows

1. **Use Mixed Approach** as standard practice
   - Start with MCP search for most queries (80%)
   - Fall back to traditional tools for exact matches (20%)

2. **MCP Search Best Practices**
   - Use natural language for conceptual queries
   - Add specific keywords for precision
   - Include filename in queries for test files
   - Use `chunk_type` filter for classes/functions

3. **Traditional Tools Best Practices**
   - Reserve for known file paths
   - Use for exact pattern matching
   - Quick extraction of configuration lists

### When to Choose Each Approach

**Use MCP Search When**:

- Exploring unfamiliar codebase
- Understanding "how" or "why" questions
- Finding similar code patterns
- Discovering relationships and dependencies

**Use Traditional Tools When**:

- You know exact file path
- Need specific text pattern
- Working with known file structure
- Quick configuration extraction

---

## Conclusion

### Key Achievements

1. **Mixed Approach Validated**
   - 100% accuracy (25/25 queries)
   - 63% token reduction vs traditional
   - Best real-world performance

2. **MCP Search as Support Tool**
   - Excellent for 80% of queries (semantic/conceptual)
   - High semantic scores (>0.90 for 40% of queries)
   - Automatic multi-model routing working correctly

3. **Optimal Workflow Established**
   - MCP for semantic queries
   - Traditional for exact matches
   - Intelligent tool selection based on query type

### Production Readiness

The Mixed approach demonstrates that **MCP semantic search is production-ready** as a support tool for development workflows:

- **Token Efficiency**: 63% reduction saves significant API costs
- **High Accuracy**: 100% success rate validates reliability
- **Fast Performance**: Sub-second search times, ~8 min for 25 queries
- **Scalable**: Maintains efficiency across diverse query types

**Recommendation**: Adopt the Mixed approach for optimal development workflow efficiency.

### Performance Monitoring (v0.8.6+)

**Timing Instrumentation Available**:

- Set `CLAUDE_LOG_LEVEL=INFO` to enable granular timing logs
- **5 instrumented operations**: `embed_query`, `bm25_search`, `dense_search`, `neural_rerank`, `multi_hop_search`
- **Log format**: `[TIMING] operation_name: Xms` (milliseconds)
- **Use case**: Identify bottlenecks, validate cache hits, diagnose performance issues
- **Overhead**: <0.1ms per operation (negligible)

---

## SSCG Retrieval Benchmark

**Added**: v0.9.0 | **Last run**: 2026-08-03 (see provenance below)

Measures end-to-end retrieval quality for `search_code` queries: how well the ranked results cover the labeled relevant chunks for each query.

### Dataset

Golden datasets:

- `evaluation/golden_dataset.json` — 77 queries across categories A–F (canonical; the tables below use the 63 non-D queries)
- `evaluation/golden_dataset_expanded.json` — 147 queries (133 non-D after the 2026-08-02 H-category promotion plus a 2026-08-04 top-up, which together added 39 commit-mined bug-localization queries)

Categories:

- **Category A** — Small function discovery (exact symbol lookup)
- **Category B** — Sibling context (related functions / pairs)
- **Category C** — Class overview (class + key methods)
- **Category D** — Connection queries (callers, impact) — excluded from the tables below
- **Category E** — Cross-file / architectural queries
- **Category F** — Similarity queries (`find_similar_to_chunk`)
- **Category H** — Commit-mined bug-localization queries (expanded set only, added 2026-08-02)

Relevance grades: 3 = primary target, 2 = expected, 1 = acceptable/hard-negative, 0 = distractor. Recall/MRR/NDCG are computed on grade ≥ 2 items; MRR uses grade = 3 items.

**Runner**: `scripts/benchmark/run_sscg_benchmark.py` (shell wrapper: `scripts/benchmark/run_benchmark.sh`)

### Results (2026-08-04, hybrid-only, k=10)

Provenance: `evaluation/CANON_20260804_INTENT_ON_REPAIRED.md`, `scripts/benchmark/run_sscg_benchmark.py --project-path .`, default config (`bm25_weight=0.35`, `dense_weight=0.65`, `query_expansion.enabled=False`, `intent.enabled=True`). Re-pinned to `canon_h1` after the intent-layer disposition (ADR-0026 → ADR-0029): `canon_f1` (ADR-0026) captured the `canon_B1b` intent-on arm and found the layer's only measurable effect was two redirects, one of which (`find_path`) returned nothing at all — regex misfires on ordinary prose; `canon_g1` (ADR-0028) defaulted `intent.enabled=False` and deleted the dead `find_path` redirect as a stopgap; `canon_h1` (ADR-0029) repaired the `find_similar` redirect's anchor-symbol extractor, passed a pre-registered gate on both datasets, and flipped `intent.enabled` back to `True` as the shipped default. The table below cites `canon_h1`'s **intent-on arm** — the figures matching the shipped default — not its intent-off control view (published alongside it in the canon doc for anyone running with the layer disabled via `search_overrides.json`). Only **hybrid** (the default mode) has been measured at this generation — no per-mode A/B has been rerun since 2026-06-08 (historical table below).

| Dataset | Queries | MRR | Recall@5 | Recall@10 | NDCG@5 | pool_hit_rate |
|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8418** (`canon_h1` intent-on arm) | 0.6967 | 0.8036 | 0.7157 | 0.9048 |
| Expanded (`golden_dataset_expanded.json`, non-D, 133 queries) | 133 | **0.6750** (`canon_h1` intent-on arm) | 0.6751 | 0.7766 | 0.6428 | 0.9023 |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8836** (`canon_h1`) | 0.6818 | 0.7963 | 0.7086 | 1.0000 |
| F-via-similar (F-category only, 9 queries) | 9 | **0.8519** (`canon_h1`) | 0.5690 | 0.7185 | 0.6064 | — |

Run-to-run noise band is **±0.02 MRR**, measured directly via a same-code control (two 94-query runs on unchanged code landed 0.701 and 0.683). Treat any delta smaller than that as noise. Note the two F-via-similar rows above: the whole-63-query aggregate (0.8836) and the true F-category-only mean (0.8519) are different numbers over different query sets — a prior generation of this table published only the whole-aggregate figure under a "9-query" caption and mixed a whole-aggregate `file_recall@5` into the F-only row; this generation corrects both.

**Comparability breaks** — do not read the numbers above as a trend against the historical table below:

- ADR-0023 (`canon_B1`, 2026-08-02, mrr 0.8249) routed the harness through `SearchOrchestrator.run()` instead of a direct `HybridSearcher.search()` call — not comparable to anything measured before it.
- ADR-0024 (`canon_C3`, mrr 0.8348/0.6816/0.8907) re-pinned after the C3 searcher-construction dedup and config-metadata fixes; see `evaluation/CANON_20260803.md`.
- `canon_d1`/`canon_d2` (`evaluation/CANON_20260804.md`) re-pinned after 34 further commits and a 2-query dataset top-up (H035, H068 — one stable pool-miss promoted deliberately as a hard case, one rank-2 hit with a corrected gold); MRR moved by less than the ±0.02 noise band on the canonical/F views and by −0.0225 on the expanded view (−0.0162 code drift + −0.0063 dataset change).
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

| Mode | MRR | Recall@5 | Recall@7 | Recall@10 | Hit@5 | NDCG@5 | Line Recall | Line Precision | Line IoU |
|------|-----|----------|----------|-----------|-------|--------|-------------|----------------|----------|
| **Hybrid** (default) | 0.797 | 0.689 | 0.736 | 0.770 | 13/13 (100%) | 0.717 | 0.852 | 0.267 | 0.304 |
| **BM25** | 0.797 | 0.689 | 0.723 | 0.777 | 13/13 (100%) | 0.717 | 0.852 | 0.270 | 0.308 |
| **Semantic** | 0.797 | 0.676 | 0.723 | 0.758 | 13/13 (100%) | 0.705 | 0.852 | 0.268 | 0.303 |

**Line-overlap metrics** (LR/LP/LIoU, historical table only) — Chroma-style source-line coverage between retrieved chunks and the expected primary set:

- **Line Recall (LR 0.852)**: 85% of expected source lines are present in the top-k retrieved chunks.
- **Line Precision (LP 0.267)**: 27% of retrieved source lines are relevant; low LP is expected since chunks contain surrounding context beyond the target function/class.
- **Line IoU (LIoU ~0.304)**: intersection / union; lower than LR due to context overhead in chunks.

### Key Findings

- **Recommended k**: 7 (`golden_dataset.recommended_k=7`). k=5 may miss targets ranked 6–7.
- The reranker-dominated finding from the 2026-06-08 run (all three search modes converging to the same MRR post-rerank) has not been re-verified since — no current per-mode A/B exists on the 2026-08-01 baseline.

### Running the Benchmark

```bash
# Default (hybrid mode):
./scripts/benchmark/run_benchmark.sh --project-path <project-path>

# Specific mode:
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --search-mode bm25
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --search-mode semantic

# Weight sweep (4 BM25/dense splits, default k=10):
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --sweep
```

---

## Caller Recall Benchmark

**Added**: v0.13.0

Measures `find_connections` direct-caller recall — how many callers of a target symbol the system finds vs. the ground-truth set produced by ripgrep.

### Dataset

Golden dataset: `evaluation/caller_golden.json` — 7 queries (C001–C007), including 2 cross-module pyan3 targets. Built with `scripts/benchmark/build_caller_oracle.py` (ripgrep-based oracle).

Baseline results: `results/caller_recall_pyan.json`

### Results (v0.13.0)

| Metric | v0.12.x baseline | v0.13.0 |
|--------|-----------------|---------|
| Direct callers found (7-query set) | — | **14/14 (100%)** |
| Total missed callers | — | **0** |
| mean_recall (5-query set) | 0.5667 | **0.9500** |
| callers found (5-query set) | 8/12 | **12/12** |

### Running the Benchmark

```bash
# Single run — evaluate all 7 golden queries
./scripts/benchmark/run_caller_recall.sh \
  --project-path F:/RD_PROJECTS/COMPONENTS/claude-context-local

# Compare before/after (delta table)
./scripts/benchmark/run_caller_recall.sh \
  --project-path F:/RD_PROJECTS/COMPONENTS/claude-context-local \
  --compare results/caller_recall_pyan.json

# Direct Python invocation
.venv/Scripts/python scripts/benchmark/run_caller_recall.py run \
  --golden evaluation/caller_golden.json \
  --output results/my_run.json
.venv/Scripts/python scripts/benchmark/run_caller_recall.py compare \
  results/caller_recall_pyan.json results/my_run.json
```

### How It Works

1. `build_caller_oracle.py` uses ripgrep to find all files that reference the target symbol and builds a ground-truth caller set.
2. `run_caller_recall.py run` calls `find_connections` via the MCP server and normalizes the returned `direct_callers` chunk IDs.
3. Recall = |found ∩ expected| / |expected|; precision = |found ∩ expected| / |found|.

---

## Appendix: Benchmark Data

### Full Result Files

Complete benchmark results available at:

- `_archive/benchmark_plans/results/test_1_mcp_only_results.md`
- `_archive/benchmark_plans/results/test_2_results_traditional_only.md`
- `_archive/benchmark_plans/results/test_3_mixed_approach_results.md`

### Test Environment

- **Platform**: Windows, Claude Code CLI
- **MCP Server**: Multi-model mode (Qwen3-0.6B, BGE-Code)
- **Project**: claude-context-local (semantic code search MCP server)
- **Index**: 109 active files, 1,199 chunks, ~24 MB
- **Date**: December 21, 2025

---

*Benchmarks conducted with real-world usage patterns on actual development workflows.*
