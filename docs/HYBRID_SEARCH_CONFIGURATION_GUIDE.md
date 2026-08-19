# Hybrid Search Configuration Guide

## Overview

The Claude Context MCP system now includes **hybrid search capabilities** that combine BM25 sparse search with dense vector search
for improved accuracy and efficiency. This guide explains how to configure and control these features.

## Key Benefits

### 🚀 **Performance Improvements**

- **Optimized search efficiency** through dual-approach methodology
- **Reduced search iterations** via improved result relevance
- **5-10x faster** indexing through incremental updates
- **Parallel execution** with BM25 on CPU, dense search on GPU

### 🎯 **Improved Accuracy**

- **Reciprocal Rank Fusion (RRF)** combines results from multiple search methods
- **Complementary strengths**: BM25 for exact text matches, dense search for semantic similarity
- **Proven quality metrics**: MRR 0.8722 on the 63-query canonical golden set, k=10, hybrid mode (2026-08-14 deterministic re-pin, shipped default; see [SSCG Retrieval Benchmark](BENCHMARKS.md#sscg-retrieval-benchmark) for the full provenance-stamped tables and comparability notes)
- **Configurable weights** to tune for your specific use case
- **Auto-mode detection** based on query characteristics

## ✅ Empirically Validated Performance (v0.5.2)

All hybrid search features have been **comprehensively tested** and validated for production use:

### Comprehensive Test Results

**Test Coverage**: 256 queries across 16 configurations (4 feature combinations × 4 search modes)
**Success Rate**: 100% (256/256 queries passed)
**Test Date**: 2025-10-23

#### Performance by Search Mode

| Search Mode | Avg Query Time | Results | Use Case | Status |
|-------------|----------------|---------|----------|--------|
| **Hybrid** | 68-105ms | 5.0 | General use (recommended) | ✅ Production Ready |
| **Semantic** | 62-94ms | 5.0 | Natural language queries | ✅ Production Ready |
| **BM25** | 3-8ms | 4-5 | Code symbol search (fastest) | ✅ Production Ready |
| **Auto** | 52-57ms | 5.0 | Mixed query types | ✅ Production Ready |

#### Feature Validation Status

✅ **Multi-Hop Search**

- Overhead: 25-35ms (validated minimal)
- Success rate: 93.3% of queries benefit
- Average discovery: 3.2 unique chunks per query
- Top result changes: 40-60% for complex queries
- **Status**: Enabled by default, optimal configuration validated

✅ **BM25 Snowball Stemming**

- Overhead: ~18ms (validated acceptable)
- Index v2 format: Fully operational
- Backward compatibility: Validated with config mismatch tests
- Configuration mismatch detection: Working correctly
- **Status**: Enabled by default, optimal configuration validated

✅ **Hybrid Search (BM25 + Dense)**

- RRF reranking: Fully operational
- Optimal weights: 0.35 BM25 / 0.65 Dense (benchmark-verified)
- Parallel execution: Working correctly
- Result consistency: 5 results per query maintained
- **Status**: Production ready with empirically validated settings

✅ **Edge Case Handling**

- Empty queries: Handled gracefully (0 results returned)
- Single character: Handled gracefully
- Long queries (200+ chars): Processed normally
- Special characters: Found correctly
- **Status**: All edge cases validated

### Configuration Recommendation

**Current default settings are optimal** - no changes needed:

```json
{
  "search_mode": {
    "default_mode": "hybrid",
    "enable_hybrid": true,
    "bm25_weight": 0.35,
    "dense_weight": 0.65,
    "bm25_use_stemming": true
  },
  "performance": {
    "use_parallel_search": true
  },
  "multi_hop": {
    "enable_multi_hop": true,
    "multi_hop_count": 2,
    "multi_hop_expansion": 0.3,
    "rrf_k_parameter": 100
  },
  "ego_graph": {
    "enabled": false,
    "k_hops": 2,
    "max_neighbors_per_hop": 10
  }
}
```

```

**Validation**: Empirically tested with 256+ queries across multiple codebases.

---

## Ego-Graph Configuration (v0.8.4+)

**Feature**: RepoGraph-style k-hop ego-graph retrieval for context expansion

**Status**: Disabled by default (per-query opt-in)

### Configuration

The ego-graph feature is configured via per-query parameters, not global settings:

```python
# Enable ego-graph expansion for a specific query
search_code(
    "authentication handler",
    ego_graph_enabled=True,     # Opt-in parameter
    ego_graph_k_hops=2,         # Graph traversal depth (default)
    ego_graph_max_neighbors_per_hop=10  # Neighbor limit (default)
)
```

**Parameters**:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `ego_graph_enabled` | `false` | - | Enable k-hop neighbor expansion from call graph |
| `ego_graph_k_hops` | `2` | 1-5 | Graph traversal depth (1=direct, 2=neighbors of neighbors) |
| `ego_graph_max_neighbors_per_hop` | `10` | 1-50 | Limit neighbors per hop to prevent explosion |

### Interaction with Multi-Hop Search

**Both features work together** to provide complementary context:

| Feature | Multi-Hop | Ego-Graph |
|---------|-----------|-----------|
| **Default State** | Enabled | Disabled (opt-in) |
| **Discovery Method** | Semantic similarity | Graph structure (calls, imports) |
| **Context Type** | Related concepts | Code dependencies |
| **Overhead** | +25-35ms | +0-5ms |

**Workflow when both enabled**:

1. **Multi-hop search** finds semantically related code (enabled by default)
   - Query → anchors → semantic expansion → re-ranked results
2. **Ego-graph expansion** adds graph neighbors (when `ego_graph_enabled=True`)
   - Anchors → graph neighbors → filtered & deduplicated

**Result**: Semantic context (multi-hop) + Structural context (ego-graph) = comprehensive understanding

**Example**:

```python
# Multi-hop only (default)
search_code("request handler")
# Returns: handler + semantically similar handlers

# Multi-hop + Ego-graph
search_code("request handler", ego_graph_enabled=True)
# Returns: handler + similar handlers + callers + callees + imports
```

### When to Enable Ego-Graph

**Enable for**:

- Dependency analysis: "What calls this function?"
- Impact assessment: "What breaks if I change this?"
- Call chain understanding: "How does data flow through this?"
- Refactoring preparation: "What code depends on this class?"

**Leave disabled for**:

- Conceptual queries: "How does authentication work?"
- Simple searches: "Find all test files"
- Performance-critical queries: (minimal overhead, but opt-in by design)

### Performance Impact

- **Overhead**: ~0-5ms for graph traversal
- **Expansion factor**: 3.5-4.6× (e.g., 5 anchors → 23 total results)
- **Symbol filtering**: Automatic (removes 4-33 invalid nodes per anchor)

### Latency Profile: PPR Expansion Mode (opt-in)

**Default**: `expansion_mode: "bfs"` — best recall, canonical. Do not change
it unless query latency matters more than recall depth.

`ego_graph.expansion_mode: "ppr"` (Personalized PageRank) is a supported
per-project **latency profile**, measured on the deterministic 131-query
benchmark (2026-08-02, `evaluation/PPR_LATENCY_PROFILE_20260802.md`):

| Metric | bfs (default) | ppr | Delta |
|--------|---------------|-----|-------|
| Avg query latency | 4,501 ms | 3,787 ms | **−15.8%** |
| MRR | 0.6527 | 0.6483 | −0.0044 (flat) |
| recall@10 | 0.7839 | 0.7742 | −0.0097 |
| recall@20 | 0.8365 | 0.8115 | **−0.0250** |

**Mechanism**: BFS floods to the neighbor cap on most queries (mean pool 29.2
chunks); PPR's top-N-by-score selection returns smaller, better-ranked pools
(mean 21.7), making the final listwise rerank ~680 ms cheaper per query. The
smaller pool is equally the source of the recall@20 debit — fewer candidates
survive to the deep-recall window. Known replicated per-query losses: Q51
(0.5→0.333) and Q70 (→0.0) class.

**Enabling per project** (ADR-0014 override layer — create
`search_overrides.json` next to the project's `search_config.json`):

```json
{
  "ego_graph": {
    "expansion_mode": "ppr"
  }
}
```

Verify after switching: benchmark or spot-check with `confounds.ppr_fallback`
= 0 (a nonzero count means the graph lacks PPR support and BFS silently took
over — the latency win will not materialize).

### Latency Profile: Compressed Reranker Documents (opt-in, larger recall debit)

`reranker.doc_representation_mode: "signature_head"` (default `"full"`) feeds
the listwise reranker a compressed document (path/parent context line +
docstring + first ~12 source lines) instead of the full chunk body. Measured
2026-08-14 (`evaluation/REMAINING_LEVERS_AB_20260814.md`, deterministic
harness): **−19% query latency** (63q 3944→3204 ms, 133q 4185→3391 ms) at a
**CI-negative recall cost** — 133q recall@10 −0.0789 and recall@20 −0.0736
(paired 95% CIs exclude zero), pool_hit −0.0677 (11 golds lost vs 2 gained),
and the 63q guard-rail set also loses recall@5. The compression reshapes pool
*membership* (the rerank cuts run over the same documents), not just final
ordering, so this debit is structural. It is a rejected default settled into
`FORBIDDEN_AUTO_TUNE_KEYS` — enable per project via `search_overrides.json`
only if latency genuinely outweighs recall, with the debit above priced in.
The knob is construction-baked (read once at reranker construction; a running
server needs a restart to pick up a change).

---

## Filter Parameters

The `search_code()` function supports filtering results by file path and code structure type.

### Available Filters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `file_pattern` | Substring match on file path | `"test_"`, `"auth"`, `"utils/"` |
| `chunk_type` | Filter by code structure | `"function"`, `"class"`, `"method"` |

### Usage

```bash
# Find only test files
/search_code "authentication" --file_pattern "test_"

# Find only classes
/search_code "user" --chunk_type "class"

# Combined filters
/search_code "database" --file_pattern "models" --chunk_type "method"
```

### How Filtering Works

1. **Initial Search**: BM25 + Dense search find semantically relevant chunks
2. **Multi-Hop Expansion**: Related chunks discovered (expansion ignores filters)
3. **Post-Expansion Filtering**: All results (initial + expanded) filtered before re-ranking
4. **Pattern matching**: `file_pattern` uses substring matching (not glob/regex)

**⚠️ Important**: Filters are post-search, so:

- Query must return chunks that match the filter pattern
- Generic queries like `"test"` may return 0 results if no semantic matches in filtered files
- Use specific queries: `"index directory embedding"` instead of `"test"` when filtering

**Best Mode for Filtering**: Use `hybrid` mode (default) - BM25 keyword matching improves filter hit rate compared to `semantic` mode

---

## Quick Start

### Enable Hybrid Search (Default)

Hybrid search is **enabled by default**. No configuration needed - just use `search_code()` as usual:

```bash
# In Claude Code, use MCP tools:
/search_code "authentication functions"
```

The system will automatically use hybrid search with optimal default settings.

### Check Current Configuration

```bash
/get_search_config_status
```

This shows your current configuration and available options.

## Configuration Options

### 1. Using MCP Tools (Recommended)

#### Configure Search Mode

```bash
/configure_search_mode "hybrid" 0.35 0.65 true
```

Parameters:

- `search_mode`: "hybrid" (default), "semantic", or "bm25"
- `bm25_weight`: Weight for BM25 sparse search (0.0 to 1.0)
- `dense_weight`: Weight for dense vector search (0.0 to 1.0)
- `enable_parallel`: Enable parallel CPU/GPU execution

#### Available Search Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **hybrid** | BM25 + Dense with RRF reranking (recommended) | General use, best balance |
| **semantic** | Dense vector search only | Conceptual queries, code similarity |
| **bm25** | Text-based sparse search only | Exact text matches, error messages |

### Multi-Hop Search Configuration

**Multi-hop search** discovers interconnected code relationships by iteratively expanding search results to find related chunks.
Inspired by ChunkHound and cAST research, it provides deeper code context discovery.

**Empirically validated**: 93.3% of queries benefit, with average 3.2 unique chunks discovered and 40-60% top result changes for complex queries.

#### How Multi-Hop Works

1. **Hop 1**: Finds code chunks matching your query (hybrid search with k×2 results)
2. **Hop 2**: For each top result, finds semantically similar chunks (k×0.3 per result)
3. **Re-ranking**: Sorts all discovered chunks by query relevance using cosine similarity

#### Benefits (Validated Through Testing)

**93.3% of queries benefit** (14/15 test queries):

- **HIGH value** (33.3% queries): Found 5-8 unique chunks
- **MEDIUM value** (46.7% queries): Found 2-3 unique chunks
- **LOW value** (13.3% queries): Found 1 unique chunk

**Example: "configuration management system"**

- Single-hop: Found primary class and direct matches
- Multi-hop: Additionally discovered environment variable parsing, config validation, model integration, path resolution, persistence methods
- **Result**: 60% of top results changed, providing complete system context

**Performance**: +25-35ms average overhead (negligible for 93% benefit rate)

#### Configuration

Multi-hop is **enabled by default** with optimal settings validated through empirical testing:

**Optimal Values (Do Not Change Unless Necessary):**

- `enabled`: `true` (enabled by default)
- `hop_count`: `2` (two hops - validated optimal)
- `expansion`: `0.5` (50% expansion — dataclass factory default and `search_config.json.example` agree)
- `initial_k_multiplier`: `2.0` (2× initial results)

#### To Disable Multi-Hop

Multi-hop is enabled by default with optimal settings. Only disable if you need maximum speed:

```powershell
# Windows (PowerShell)
$env:CLAUDE_ENABLE_MULTI_HOP="false"
```

```bash
# Linux/macOS
export CLAUDE_ENABLE_MULTI_HOP=false
```

**Note**: Disabling multi-hop will:

- Reduce search quality (93% of queries benefit from multi-hop)
- Provide only +25-35ms speedup
- Miss interconnected code relationships

**Recommendation**: Keep multi-hop enabled unless you're debugging performance issues.

**Advanced (Experts Only)**: To modify optimal settings:

```json
{
  "enabled": true,
  "hop_count": 2,
  "expansion": 0.5,
  "initial_k_multiplier": 2.0
}
```

**Warning**: These settings have been empirically validated as optimal. Changing them may:

- Increase overhead without improving results (more hops/expansion)
- Reduce discovery quality (lower expansion)
- Waste computational resources

These parameters were validated with 15+ queries showing 93% benefit rate and optimal result diversity.

### BM25 Stemming Configuration (v0.5.2)

**BM25 Stemming** normalizes word forms to improve recall by matching different variations of the same word. For example,
"indexing", "indexed", "indexes", and "index" all stem to "index" and match each other.

**Empirically validated**: 93.3% of queries benefit, with average 3.33 unique discoveries per query and negligible overhead (0.47ms).

#### How Stemming Works

The Snowball stemmer (Porter2 algorithm) normalizes words during BM25 text preprocessing:

1. **Verb form matching**: "searching" matches "search", "searches", "searched"
2. **Noun/verb handling**: "authentication" matches "authenticator", "authenticate"
3. **Gerund normalization**: "indexing" matches "index", "indexed", "indexes"

**Example queries that benefit:**

- `"indexing and storage workflow"` - Matches code with "index", "indexed", "indexes"
- `"searching for user records"` - Matches functions with "search", "searcher", "searches"
- `"managing configuration settings"` - Matches classes with "manager", "manage", "managed"

#### Configuration

> **Default tokenizer is `bm25_tokenizer: "whole"`, which does not apply stemming at
> all** — `bm25_use_stemming` is only consulted by the `"legacy"` tokenizer variant
> (`search/bm25_index.py`). The `"whole"` default keeps identifiers intact (no
> camelCase/snake_case split, no stemming) and outperforms `"legacy"` on the golden
> sets (+0.05/+0.07 Recall@5, +0.09/+0.10 MRR — see the `bm25_tokenizer` field in
> `search/config.py`'s `SearchModeConfig`; the tokenizer choice is consumed by
> `TextPreprocessor._resolve_tokenizer` in `search/bm25_index.py`). The
> stemming behavior and benchmark numbers below apply only if you opt back into
> `bm25_tokenizer: "legacy"`; switching tokenizers requires a full reindex.

`bm25_use_stemming` defaults to `true` and, under `"legacy"` mode, is validated
through empirical testing:

**Default Setting (legacy mode only):**

- `bm25_use_stemming`: `true` (enabled by default)

**Performance:**

- Query overhead: 0.47ms average (negligible)
- Index size: 11% smaller due to vocabulary consolidation
- No impact on indexing speed

#### To Disable Stemming

Stemming is enabled by default for maximum recall. Only disable if you need exact word matching:

```powershell
# Windows (PowerShell)
$env:CLAUDE_BM25_USE_STEMMING="false"
```

```bash
# Linux/macOS
export CLAUDE_BM25_USE_STEMMING=false
```

**Note**: Disabling stemming will:

- Reduce recall for queries with verb form variations (93% of queries benefit)
- Miss noun/verb mismatches (e.g., "authentication" won't match "authenticator")
- Provide no performance benefit (overhead is 0.47ms)

**Recommendation**: Keep stemming enabled unless you specifically need exact text matching.

**After Upgrade**: Re-index existing projects for optimal stemming benefits. The system automatically detects configuration
mismatches and warns you if loading old indices.

Stemming was validated with comparative testing showing improved recall for morphological variations without impacting precision.

### Query Expansion (opt-in, default off)

**Query expansion** bridges zero-identifier English paraphrases to the identifiers code
actually uses. A curated concept→terms vocabulary (`config/query_expansion_variants.yaml`,
12 concepts: persistence, eviction, pooling, …) is matched against the query by
deterministic lowercase trigger containment; each matched concept adds an extra
**discounted fusion leg** (the query text plus the concept's code-domain terms) to the
existing RRF fusion. Example: "write the analyzed relationships out so they *survive a
restart*" triggers the `persistence` concept and adds a BM25 leg carrying "save",
"persist", "disk".

**Why it ships disabled**: the 2026-07-28 A/B closed FAIL on its primary criterion —
only 1 of 3 target queries flipped, and rescuing the one genuine vocabulary-gap query
required a variant weight that measurably diluted the dense leg for other queries.
Aggregates and latency were neutral. Full verdict:
[ADR-0012](adr/0012-curated-vocabulary-query-expansion.md) and
`evaluation/QUERY_EXPANSION_AB_20260728.md`. The mechanism remains available for opt-in
use and re-evaluation.

#### QueryExpansionConfig fields

All six fields live in `QueryExpansionConfig` (`search/config.py`):

| Field | Default | Meaning |
|-------|---------|---------|
| `enabled` | `false` | Master switch. Disabled/unmatched queries take the exact unexpanded fusion path |
| `variants_path` | `""` | Vocabulary YAML path; empty = package default `config/query_expansion_variants.yaml` |
| `max_variants` | `2` | Max matched concepts per query (deterministic order) |
| `variant_weight_discount` | `0.5` | Variant-leg weight = base leg weight × this |
| `apply_to_bm25` | `true` | Add expanded-query BM25 leg(s) |
| `apply_to_dense` | `false` | Add expanded-query dense leg(s) — needs its own A/B before use |

#### Enabling via `search_config.json`

Nested block:

```json
{
  "query_expansion": {
    "enabled": true,
    "max_variants": 2,
    "variant_weight_discount": 0.5,
    "apply_to_bm25": true,
    "apply_to_dense": false
  }
}
```

Flat-key aliases are also accepted (`search/config.py` `_FLAT_KEY_ALIASES`):
`query_expansion_enabled`, `query_expansion_variants_path`,
`query_expansion_max_variants`, `query_expansion_weight_discount`,
`query_expansion_apply_to_bm25`, `query_expansion_apply_to_dense`.
There are no environment variables for query expansion — use the configuration file.

No reindex is required; expansion is a search-time-only mechanism.

#### Vocabulary curation policy

The YAML header enforces these rules at review time (restated here; the file is
authoritative):

- **Generality test**: every concept must plausibly serve queries outside any benchmark
  set — universal software ideas (persistence, eviction, pooling), never a specific
  query's wording.
- **Never query-keyed**: no entry may be named after, or triggered solely by, a
  golden-dataset query.
- **Cap ~15 concepts**: growth pressure means the approach is wrong (switch to
  embedding-based matching instead of adding entries).
- Matching is verbatim lowercase substring containment — prefer 1–2 word triggers, and
  use longer phrases only to avoid over-firing (e.g. "memory gets tight", not "memory").

### 2. Using Environment Variables

Set environment variables before starting the MCP server:

```powershell
# Windows (PowerShell)
$env:CLAUDE_SEARCH_MODE="hybrid"
$env:CLAUDE_ENABLE_HYBRID="true"
$env:CLAUDE_BM25_WEIGHT="0.35"
$env:CLAUDE_DENSE_WEIGHT="0.65"
$env:CLAUDE_BM25_USE_STEMMING="true"
$env:CLAUDE_USE_PARALLEL="true"
```

### 3. Using Configuration File

Create a `search_config.json` file in your project root:

```json
{
  "search_mode": {
    "default_mode": "hybrid",
    "enable_hybrid": true,
    "bm25_weight": 0.35,
    "dense_weight": 0.65,
    "bm25_use_stemming": true,
    "rrf_k_parameter": 100
  },
  "performance": {
    "use_parallel_search": true,
    "prefer_gpu": true,
    "enable_auto_reindex": true,
    "max_index_age_minutes": 5.0
  }
}
```

## Weight Tuning Guide

### Default Weights (Recommended)

- **BM25 Weight: 0.35** (35%) - Good for exact text matches
- **Dense Weight: 0.65** (65%) - Better for semantic understanding

### Tuning for Different Use Cases

#### Code Structure Queries

```bash
/configure_search_mode "hybrid" 0.3 0.7 true
```

- Emphasize semantic search for understanding code relationships
- Good for: "find classes that implement interface", "similar functions"

#### Error/Log Analysis

```bash
/configure_search_mode "hybrid" 0.7 0.3 true
```

- Emphasize text search for exact error message matches
- Good for: "find error handling", "exception messages"

#### Balanced General Use

```bash
/configure_search_mode "hybrid" 0.35 0.65 true
```

- Default balanced approach
- Good for: most queries, general code exploration

### Auto-Optimization

The system includes weight optimization that can automatically tune weights based on your query patterns:

```python
# This happens automatically in the background
# Weights are optimized based on search success rates
```

## Advanced Configuration

### GPU Memory Management

Configure GPU usage and the VRAM ceiling (`search/config.py` `PerformanceConfig`):

```json
{
  "prefer_gpu": true,
  "vram_limit_fraction": 0.8,
  "allow_ram_fallback": true,
  "enable_auto_reindex": true
}
```

### Parallel Processing Settings

Control search and chunking parallelism:

```json
{
  "use_parallel_search": true,
  "max_parallel_workers": 2,
  "enable_parallel_chunking": true,
  "max_chunking_workers": 8
}
```

### Index Management

Configure automatic reindexing behavior:

```json
{
  "enable_auto_reindex": true,
  "max_index_age_minutes": 5.0
}
```

## Performance Tuning

### For Large Codebases (>10k files)

```json
{
  "bm25_weight": 0.3,
  "dense_weight": 0.7,
  "use_parallel_search": true,
  "prefer_gpu": true
}
```

### For Fast Development Cycles

```json
{
  "bm25_weight": 0.6,
  "dense_weight": 0.4,
  "max_index_age_minutes": 1.0,
  "enable_auto_reindex": true
}
```

### For Semantic Code Discovery

```json
{
  "bm25_weight": 0.2,
  "dense_weight": 0.8,
  "rrf_k_parameter": 50,
  "prefer_gpu": true
}
```

### Query Embedding Cache Configuration

**Version**: v0.8.6+

**Feature**: TTL (Time-to-Live) support for query embedding cache

**Purpose**: Automatic expiration of stale embeddings prevents serving outdated embeddings after model changes.

**Configuration**:

```python
from embeddings.query_cache import QueryEmbeddingCache

# Default TTL: 5 minutes
cache = QueryEmbeddingCache(max_size=128, ttl_seconds=300)

# Custom TTL: 10 minutes (stable production)
cache = QueryEmbeddingCache(max_size=128, ttl_seconds=600)

# Short TTL: 2 minutes (active development)
cache = QueryEmbeddingCache(max_size=128, ttl_seconds=120)
```

**Cache Statistics**:

```python
stats = cache.get_stats()
# Returns: {
#   "hits": N,
#   "misses": M,
#   "hit_rate": "X%",
#   "cache_size": Y,
#   "max_size": 128
# }
```

**When to Adjust TTL**:

| Scenario | Recommended TTL | Reason |
|----------|----------------|--------|
| Stable production | 600-900s (10-15min) | Infrequent model changes, maximize cache hits |
| Active development | 60-120s (1-2min) | Frequent model switching, ensure freshness |
| Testing/benchmarking | 999999s (disabled) | Deterministic behavior, consistent timing |
| Default (recommended) | 300s (5min) | Balance between freshness and performance |

**Benefits**:

- **Prevents stale embeddings**: Auto-expires after model changes
- **Zero manual intervention**: Cleanup happens automatically on access
- **Performance maintained**: Cache hits still return instantly (0ms)
- **Configurable**: Tune TTL based on your workflow

**Performance Impact**:

- **First query**: Full embedding generation (~50ms)
- **Repeated query (within TTL)**: Instant retrieval (0ms)
- **After TTL expiration**: Re-generate embedding (~50ms)
- **Cache overhead**: <0.1ms per access (negligible)

### Chunk Embedding Cache Configuration

**Feature**: Persistent, content-hash-keyed cache of *chunk* embedding vectors (distinct from the
query embedding cache above), stored per model in `chunk_embeddings.bin`.

**Purpose**: Skips re-embedding chunks whose content hash is unchanged between reindexes — on a
full reindex of an otherwise-unchanged codebase this cuts the embedding phase from ~34s to well
under 1s.

**Configuration** (`search_config.json`):

```json
{
  "enable_chunk_cache": true,
  "chunk_cache_max_entries": 0
}
```

| Setting | Default | Meaning |
|---------|---------|---------|
| `enable_chunk_cache` | `true` | Enable/disable the persistent chunk cache entirely |
| `chunk_cache_max_entries` | `0` (auto) | Hard cap on cached entries. `0` uses an auto cap: `max(2× live chunks, 2,000)`, clamped so the cache never exceeds ~32MB on disk |

**Cache invalidation**: The cache header records the embedding model name, vector dimension, and a
provenance string (effective device/dtype/backend, e.g. `v1|device=cuda|dtype=fp16|backend=pytorch`).
Changing the embedding model, or flipping `enable_fp16` or `prefer_bf16` in
`PerformanceConfig`, changes this provenance and invalidates the entire cache — the next reindex
cold-starts (full re-embed) and then re-populates the cache under the new numerics. This is
expected, one-time behavior, not a bug.

**Cache Statistics**: hit rate is logged at INFO level during indexing:

```
[CHUNK_CACHE] run complete: hits=2100 misses=31 hit_rate=98.5% size=2131 cap=4262
```

## Monitoring and Diagnostics

### Check System Status

```bash
/get_memory_status     # Monitor RAM/GPU usage
/get_index_status      # Check index health
/get_search_config_status  # View current settings
```

### Performance Metrics

The system tracks:

- Query response times
- Index build times
- Memory usage patterns
- Search success rates
- Hardware utilization

### Performance Monitoring (v0.8.6+)

**Feature**: Granular timing instrumentation for performance debugging

**Instrumented Operations**:

The system logs timing data for 5 critical operations:

1. **embed_query**: Query embedding generation
2. **bm25_search**: Sparse keyword search
3. **dense_search**: Dense vector search
4. **apply_neural_reranking**: Cross-encoder reranking
5. **multi_hop_search**: Multi-hop expansion

**Enable Timing Logs**:

```powershell
# Windows (PowerShell)
$env:CLAUDE_LOG_LEVEL="INFO"
# Restart MCP server

# Linux/macOS
export CLAUDE_LOG_LEVEL=INFO
# Restart MCP server
```

**Check Logs for `[TIMING]` Entries**:

```
[TIMING] embed_query: 45.23ms
[TIMING] bm25_search: 3.12ms
[TIMING] dense_search: 52.78ms
[TIMING] neural_rerank: 89.45ms
[TIMING] multi_hop_search: 145.67ms
```

**Interpreting Timing Data**:

| Timing Pattern | Status | Action |
|---------------|--------|--------|
| `embed_query: 0ms` | ✅ Optimal | Cache hit, no action needed |
| `embed_query: 40-60ms` | ⚠️ Normal | First query or cache miss |
| `bm25_search: <15ms` | ✅ Fast | No action needed |
| `dense_search: 50-100ms` | ⚠️ Moderate | Acceptable, monitor trends |
| `dense_search: >150ms` | ❌ Slow | Consider BM25 mode or reduce index size |
| `neural_rerank: 80-150ms` | ⚠️ Expensive | Expected with reranking |
| `neural_rerank: >200ms` | ❌ Too slow | Disable or reduce `top_k_candidates` |

**Optimization Strategies**:

1. **Cache optimization**: Monitor `embed_query` timing
   - 0ms = Cache hit (optimal)
   - >60ms consistently = Check cache size/TTL settings

2. **Reranker tuning**: If `neural_rerank` > 200ms
   - Reduce `top_k_candidates` in reranker config
   - Or disable neural reranking entirely

3. **Search mode selection**: If `dense_search` > 150ms
   - Switch to `bm25` mode for keyword-heavy queries
   - Or reduce index size by filtering directories

4. **Multi-hop tuning**: If `multi_hop_search` > 500ms
   - Reduce `hops` parameter (default: 2)
   - Reduce `expansion_factor` (default: 0.3)

**Custom Timing Usage**:

```python
from utils.timing import timed, Timer


# Decorator for functions
@timed("my_operation")
def my_function():
    # Your code
    pass


# Context manager for code blocks
with Timer("custom_operation") as t:
    # Your code
    pass
print(f"Took {t['elapsed_ms']:.2f}ms")
```

### Troubleshooting

#### Search Quality Issues

1. Increase semantic weight for conceptual queries
2. Increase BM25 weight for exact text matches
3. Check index freshness with `/get_index_status`

#### Performance Issues

1. Enable GPU acceleration if available
2. Reduce batch sizes for memory constraints
3. Use auto-reindexing for dynamic codebases

#### Memory Issues

1. Monitor with `/get_memory_status`
2. Cleanup with `/cleanup_resources`
3. Adjust batch sizes in configuration

## Integration Examples

### Claude Code Workflow

```bash
# 1. Index your project
/index_directory "C:\your\project\path"

# 2. Configure for your use case
/configure_search_mode "hybrid" 0.35 0.65 true

# 3. Search naturally
/search_code "database connection pooling"

# 4. Monitor performance
/get_search_config_status
```

### Batch Configuration

```powershell
# Windows batch setup
$env:CLAUDE_SEARCH_MODE="hybrid"
$env:CLAUDE_BM25_WEIGHT="0.35"
$env:CLAUDE_DENSE_WEIGHT="0.65"

# Start server with configuration
start_mcp_server.cmd
```

## Best Practices

### Search Strategy

1. **Start with defaults** - hybrid mode with 0.35/0.65 weights
2. **Monitor results** - adjust based on search success
3. **Use auto-mode** for mixed query types
4. **Tune weights** for specific use cases

### Performance

1. **Enable GPU** when available for better speed
2. **Use parallel search** for optimal resource utilization
3. **Monitor memory** usage with large indices
4. **Regular cleanup** to maintain performance

### Maintenance

1. **Auto-reindex** for active development
2. **Manual reindex** after major changes
3. **Monitor index age** and refresh as needed
4. **Backup indices** for large projects

## Configuration Reference

### Complete Configuration Schema

```json
{
  "search_mode": {
    "default_mode": "hybrid",
    "enable_hybrid": true,
    "bm25_weight": 0.35,
    "dense_weight": 0.65,
    "bm25_tokenizer": "whole",
    "rrf_k_parameter": 100
  },
  "performance": {
    "use_parallel_search": true,
    "max_parallel_workers": 2,
    "prefer_gpu": true,
    "vram_limit_fraction": 0.8,
    "allow_ram_fallback": true,
    "enable_auto_reindex": true,
    "max_index_age_minutes": 30.0
  },
  "multi_hop": {
    "enabled": true,
    "hop_count": 2,
    "expansion": 0.5
  },
  "query_expansion": {
    "enabled": false,
    "variants_path": "",
    "max_variants": 2,
    "variant_weight_discount": 0.5,
    "apply_to_bm25": true,
    "apply_to_dense": false
  }
}
```

Field names mirror `search_config.json.example` — see that file (and `search/config.py`'s
`SearchModeConfig`/`PerformanceConfig`/`MultiHopConfig`/`QueryExpansionConfig` dataclasses)
for the authoritative list; this excerpt is illustrative, not exhaustive. Note `bm25_tokenizer: "whole"` keeps
identifiers intact with **no stemming** — changing it requires a full reindex.

> **Packaged vs. deployed model config**: the dataclass factory defaults and the tracked
> `search_config.json.example` both ship `embedding.model_name = "BAAI/bge-m3"` and
> `reranker.model_name = "Alibaba-NLP/gte-reranker-modernbert-base"`. A **deployed**
> `search_config.json` (gitignored, machine-local) can diverge from that — e.g. this
> development machine currently runs `F2LLM-v2-0.6B` + `jina-reranker-v3`. Docs and
> benchmark reports that name a specific model are describing whichever layer they
> measured; check `get_search_config_status` for the model actually active on your
> installation rather than assuming the packaged default.

This configuration provides optimal performance for most Windows development environments with CUDA-capable GPUs.
