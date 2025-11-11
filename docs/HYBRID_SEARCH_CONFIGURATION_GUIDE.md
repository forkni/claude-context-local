# Hybrid Search Configuration Guide

## Overview

The Claude Context MCP system now includes **hybrid search capabilities** that combine BM25 sparse search with dense vector search for improved accuracy and efficiency. This guide explains how to configure and control these features.

## Key Benefits

### 🚀 **Performance Improvements**

- **Optimized search efficiency** through dual-approach methodology
- **Reduced search iterations** via improved result relevance
- **5-10x faster** indexing through incremental updates
- **Parallel execution** with BM25 on CPU, dense search on GPU

### 🎯 **Improved Accuracy**

- **Reciprocal Rank Fusion (RRF)** combines results from multiple search methods
- **Complementary strengths**: BM25 for exact text matches, dense search for semantic similarity
- **Proven quality metrics**: 44.4% precision, 46.7% F1-score, 100% MRR (see [BENCHMARKS.md](BENCHMARKS.md))
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
- Optimal weights: 0.4 BM25 / 0.6 Dense (validated)
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
  "default_search_mode": "hybrid",
  "enable_hybrid_search": true,
  "bm25_weight": 0.4,
  "dense_weight": 0.6,
  "bm25_use_stemming": true,
  "enable_multi_hop": true,
  "multi_hop_count": 2,
  "multi_hop_expansion": 0.3,
  "use_parallel_search": true,
  "rrf_k_parameter": 100
}
```

**Validation Reports**:
- [Comprehensive Feature Test Report](../analysis/COMPREHENSIVE_FEATURE_TEST_REPORT.md) - Full 256-query validation
- [v0.5.2 Recommendations](../analysis/RECOMMENDATIONS_v0.5.2.md) - Production readiness assessment
- [Multi-Hop Validation](../analysis/MULTI_HOP_RECOMMENDATIONS.md) - Multi-hop testing results
- [Stemming Validation](../analysis/STEMMING_VALIDATION_REPORT.md) - Stemming impact analysis

---

## Multi-Model Query Routing (v0.5.4+)

**Feature**: Intelligent automatic selection of optimal embedding model based on query characteristics

### Overview

The system can automatically route queries to the most suitable model from a pool of three specialized embedding models:
- **Qwen3-0.6B**: Implementation queries, algorithms, error handling
- **BGE-M3**: Workflow queries, configuration, system plumbing (most consistent)
- **CodeRankEmbed**: Specialized algorithms (Merkle trees, RRF reranking)

### Configuration

**Enable/Disable Multi-Model Mode**:

```bash
# Enable (default in v0.5.4+)
set CLAUDE_MULTI_MODEL_ENABLED=true

# Disable (single-model fallback to BGE-M3)
set CLAUDE_MULTI_MODEL_ENABLED=false
```

**Interactive Configuration** (MCP tool):

```bash
# View current routing configuration
/get_search_config_status  # Shows multi-model status, default model, confidence threshold

# Enable/disable multi-model mode
/configure_query_routing true   # Enable multi-model (default)
/configure_query_routing false  # Disable (single-model fallback)

# Set default model for single-model fallback or when routing disabled
/configure_query_routing None "qwen3" None       # Use Qwen3-0.6B
/configure_query_routing None "bge_m3" None      # Use BGE-M3 (default)
/configure_query_routing None "coderankembed" None  # Use CodeRankEmbed

# Adjust confidence threshold (advanced)
/configure_query_routing None None 0.10  # Lower threshold (more aggressive routing)
/configure_query_routing None None 0.50  # Higher threshold (more conservative)

# Combined configuration
/configure_query_routing true "qwen3" 0.10  # Enable routing + Qwen3 default + 0.10 threshold
```

### Model Specializations

| Model | Best For | Example Queries | Win Rate | VRAM |
|-------|----------|-----------------|----------|------|
| **Qwen3-0.6B** | Implementation, algorithms | "error handling patterns", "BM25 implementation", "multi-hop search" | 37.5% (3/8) | ~2.3 GB |
| **BGE-M3** | Workflow, configuration | "configuration loading", "embedding workflow", "incremental indexing" | 37.5% (3/8) | ~2.3 GB |
| **CodeRankEmbed** | Specialized algorithms | "Merkle tree detection", "RRF reranking" | 25.0% (2/8) | ~0.6 GB |

**Total VRAM**: 5.3 GB for all 3 models (verified on RTX 4090)

### Performance Impact

- **VRAM Usage**: 5.3 GB total (vs 2.3 GB single-model)
- **Routing Overhead**: <1ms per query (negligible)
- **Quality Improvement**: +15-25% for specialized queries vs single-model
- **Routing Accuracy**: 100% on 8 ground truth verification queries
- **Load Time**: ~5 seconds for all 3 models (from cache, first load only)

### Routing Transparency

All searches include routing metadata showing which model processed the query:

```json
{
  "routing": {
    "model_selected": "qwen3",
    "confidence": 0.12,
    "reason": "Matched Implementation queries and algorithms",
    "scores": {
      "qwen3": 0.12,
      "bge_m3": 0.08,
      "coderankembed": 0.05
    }
  },
  "results": [...]
}
```

### Manual Model Override

Force a specific model for a query:

```bash
# Auto-routing (default)
/search_code "Merkle tree detection"  # Routes to CodeRankEmbed

# Force specific model
/search_code "error handling" --model_key "qwen3"

# Disable routing (use default BGE-M3)
/search_code "configuration" --use_routing False
```

### Memory Management

Models load on-demand (lazy loading) and can be cleaned up:

```bash
# Check memory usage
/get_memory_status

# Free VRAM (unload all models)
/cleanup_resources
```

### Verification Results

- **Test Suite**: 5/5 integration tests passing
- **Routing Accuracy**: 8/8 ground truth queries correct (100%)
- **VRAM Efficiency**: 20.5% utilization on RTX 4090 (79.5% headroom)
- **Cleanup Verified**: VRAM drops to 0.0 GB after cleanup
- **Documentation**: [Complete Verification Report](../analysis/mcp_multi_model_verification_report.md)

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
/configure_search_mode "hybrid" 0.4 0.6 true
```

Parameters:

- `search_mode`: "hybrid" (default), "semantic", "bm25", or "auto"
- `bm25_weight`: Weight for BM25 sparse search (0.0 to 1.0)
- `dense_weight`: Weight for dense vector search (0.0 to 1.0)
- `enable_parallel`: Enable parallel CPU/GPU execution

#### Available Search Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **hybrid** | BM25 + Dense with RRF reranking (recommended) | General use, best balance |
| **semantic** | Dense vector search only | Conceptual queries, code similarity |
| **bm25** | Text-based sparse search only | Exact text matches, error messages |
| **auto** | Automatically choose based on query | Let system decide optimal mode |

### Multi-Hop Search Configuration

**Multi-hop search** discovers interconnected code relationships by iteratively expanding search results to find related chunks. Inspired by ChunkHound and cAST research, it provides deeper code context discovery.

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
- `enable_multi_hop`: `true` (enabled by default)
- `multi_hop_count`: `2` (two hops - validated optimal)
- `multi_hop_expansion`: `0.3` (30% expansion - validated optimal)
- `multi_hop_initial_k_multiplier`: `2.0` (2× initial results)

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
  "enable_multi_hop": true,
  "multi_hop_count": 2,
  "multi_hop_expansion": 0.3,
  "multi_hop_initial_k_multiplier": 2.0
}
```

**Warning**: These settings have been empirically validated as optimal. Changing them may:
- Increase overhead without improving results (more hops/expansion)
- Reduce discovery quality (lower expansion)
- Waste computational resources

See `analysis/MULTI_HOP_RECOMMENDATIONS.md` for detailed testing results showing why these are optimal.

### BM25 Stemming Configuration (v0.5.2)

**BM25 Stemming** normalizes word forms to improve recall by matching different variations of the same word. For example, "indexing", "indexed", "indexes", and "index" all stem to "index" and match each other.

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

Stemming is **enabled by default** with optimal settings validated through empirical testing:

**Default Setting:**
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

**After Upgrade**: Re-index existing projects for optimal stemming benefits. The system automatically detects configuration mismatches and warns you if loading old indices.

See `analysis/STEMMING_VALIDATION_REPORT.md` for detailed testing results showing why stemming is beneficial.

### 2. Using Environment Variables

Set environment variables before starting the MCP server:

```powershell
# Windows (PowerShell)
$env:CLAUDE_SEARCH_MODE="hybrid"
$env:CLAUDE_ENABLE_HYBRID="true"
$env:CLAUDE_BM25_WEIGHT="0.4"
$env:CLAUDE_DENSE_WEIGHT="0.6"
$env:CLAUDE_BM25_USE_STEMMING="true"
$env:CLAUDE_USE_PARALLEL="true"
```

### 3. Using Configuration File

Create a `search_config.json` file in your project root:

```json
{
  "default_search_mode": "hybrid",
  "enable_hybrid_search": true,
  "bm25_weight": 0.4,
  "dense_weight": 0.6,
  "bm25_use_stemming": true,
  "use_parallel_search": true,
  "rrf_k_parameter": 100,
  "prefer_gpu": true,
  "enable_auto_reindex": true,
  "max_index_age_minutes": 5.0
}
```

## Weight Tuning Guide

### Default Weights (Recommended)

- **BM25 Weight: 0.4** (40%) - Good for exact text matches
- **Dense Weight: 0.6** (60%) - Better for semantic understanding

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
/configure_search_mode "hybrid" 0.4 0.6 true
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

Configure GPU usage and memory thresholds:

```json
{
  "prefer_gpu": true,
  "gpu_memory_threshold": 0.8,
  "enable_auto_reindex": true
}
```

### Parallel Processing Settings

Control CPU and GPU coordination:

```json
{
  "use_parallel_search": true,
  "max_worker_threads": 4,
  "gpu_batch_size": 32,
  "cpu_chunk_size": 100
}
```

### Index Management

Configure automatic reindexing behavior:

```json
{
  "enable_auto_reindex": true,
  "max_index_age_minutes": 5.0,
  "force_reindex_on_startup": false
}
```

## Performance Tuning

### For Large Codebases (>10k files)

```json
{
  "bm25_weight": 0.3,
  "dense_weight": 0.7,
  "use_parallel_search": true,
  "gpu_batch_size": 64,
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
/configure_search_mode "hybrid" 0.4 0.6 true

# 3. Search naturally
/search_code "database connection pooling"

# 4. Monitor performance
/get_search_config_status
```

### Batch Configuration

```powershell
# Windows batch setup
$env:CLAUDE_SEARCH_MODE="hybrid"
$env:CLAUDE_BM25_WEIGHT="0.4"
$env:CLAUDE_DENSE_WEIGHT="0.6"

# Start server with configuration
start_mcp_server.bat
```

## Best Practices

### Search Strategy

1. **Start with defaults** - hybrid mode with 0.4/0.6 weights
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
  "default_search_mode": "hybrid",
  "enable_hybrid_search": true,
  "bm25_weight": 0.4,
  "dense_weight": 0.6,
  "bm25_use_stemming": true,
  "use_parallel_search": true,
  "rrf_k_parameter": 100,
  "prefer_gpu": true,
  "gpu_batch_size": 32,
  "cpu_chunk_size": 100,
  "max_worker_threads": 4,
  "enable_auto_reindex": true,
  "max_index_age_minutes": 5.0,
  "enable_multi_hop": true,
  "multi_hop_count": 2,
  "multi_hop_expansion": 0.3,
  "force_reindex_on_startup": false,
  "gpu_memory_threshold": 0.8,
  "cache_embeddings": true,
  "debug_mode": false
}
```

This configuration provides optimal performance for most Windows development environments with CUDA-capable GPUs.
