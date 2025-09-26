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

### 2. Using Environment Variables

Set environment variables before starting the MCP server:

```powershell
# Windows (PowerShell)
$env:CLAUDE_SEARCH_MODE="hybrid"
$env:CLAUDE_ENABLE_HYBRID="true"
$env:CLAUDE_BM25_WEIGHT="0.4"
$env:CLAUDE_DENSE_WEIGHT="0.6"
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

### Reranking Parameters

Fine-tune the RRF (Reciprocal Rank Fusion) algorithm:

```json
{
  "rrf_k_parameter": 100,
  "enable_result_reranking": true
}
```

- **Lower k values**: More emphasis on top-ranked results
- **Higher k values**: More balanced consideration of all results

### Parallel Execution

Control CPU/GPU parallel execution:

```json
{
  "use_parallel_search": true,
  "max_parallel_workers": 2
}
```

## Troubleshooting

### Common Issues

#### 1. Hybrid Search Not Working

**Check current mode:**
```bash
/get_search_config_status
```

**Enable hybrid search:**
```bash
/configure_search_mode "hybrid" 0.4 0.6 true
```

#### 2. Poor Search Results

**Try different weights:**
```bash
# More semantic focus
/configure_search_mode "hybrid" 0.2 0.8 true

# More text matching focus
/configure_search_mode "hybrid" 0.8 0.2 true
```

**Switch to specific mode:**
```bash
# Force semantic-only
/configure_search_mode "semantic" 0.0 1.0 true

# Force text-only
/configure_search_mode "bm25" 1.0 0.0 true
```

#### 3. Performance Issues

**Check memory status:**
```bash
/get_memory_status
```

**Disable parallel execution:**
```bash
/configure_search_mode "hybrid" 0.4 0.6 false
```

**Clear resources:**
```bash
/cleanup_resources
```

### Debugging

Enable debug mode to see detailed search execution:

```powershell
# Windows PowerShell
$env:MCP_DEBUG="1"
```

Then restart the MCP server to see detailed logging.

## Performance Monitoring

### Search Statistics

Monitor search performance and effectiveness:

```bash
/get_search_config_status
```

Look for the `runtime_status` section to see:
- Current searcher type being used
- Active project
- Configuration file location

### Memory Usage

Monitor GPU and system memory usage:

```bash
/get_memory_status
```

This shows:
- Available RAM/VRAM
- Current index memory usage
- GPU acceleration status

## Migration from Semantic-Only

If you were previously using semantic-only search:

### No Action Needed

Hybrid search is backward compatible. Your existing workflows continue working with improved results.

### To Disable Hybrid Search

If you prefer the old semantic-only behavior:

```bash
/configure_search_mode "semantic" 0.0 1.0 true
```

Or set environment variable:
```powershell
$env:CLAUDE_ENABLE_HYBRID="false"
```

## Best Practices

### 1. Query Optimization

#### Good Hybrid Queries
- "authentication functions" - Finds both exact text and semantic matches
- "database connection setup" - Combines technical terms with concepts
- "error handling patterns" - Balances exact error terms with patterns

#### Mode-Specific Queries
- **BM25 Mode**: "UserNotFound exception", "import statements"
- **Semantic Mode**: "similar functionality", "code that does X"
- **Auto Mode**: Let system decide based on query characteristics

### 2. Weight Adjustment

Start with defaults (0.4, 0.6) and adjust based on results:

- **Too many irrelevant results**: Increase BM25 weight
- **Missing obvious matches**: Increase BM25 weight
- **Not finding conceptual matches**: Increase dense weight
- **Results too literal**: Increase dense weight

### 3. Performance Optimization

For large codebases:
1. Use parallel execution (default: true)
2. Enable GPU acceleration (default: true)
3. Set reasonable k values (default: 5-10 results)
4. Enable auto-reindexing for changed files

## Configuration Reference

### Complete Configuration Schema

```json
{
  "default_search_mode": "hybrid",
  "enable_hybrid_search": true,
  "bm25_weight": 0.4,
  "dense_weight": 0.6,
  "use_parallel_search": true,
  "max_parallel_workers": 2,
  "bm25_k_parameter": 100,
  "bm25_use_stopwords": true,
  "min_bm25_score": 0.1,
  "rrf_k_parameter": 100,
  "enable_result_reranking": true,
  "prefer_gpu": true,
  "gpu_memory_threshold": 0.8,
  "enable_auto_reindex": true,
  "max_index_age_minutes": 5.0,
  "default_k": 5,
  "max_k": 50
}
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_SEARCH_MODE` | "hybrid" | Default search mode |
| `CLAUDE_ENABLE_HYBRID` | true | Enable hybrid search |
| `CLAUDE_BM25_WEIGHT` | 0.4 | BM25 weight (0.0-1.0) |
| `CLAUDE_DENSE_WEIGHT` | 0.6 | Dense weight (0.0-1.0) |
| `CLAUDE_USE_PARALLEL` | true | Enable parallel execution |
| `CLAUDE_PREFER_GPU` | true | Prefer GPU acceleration |
| `CLAUDE_GPU_THRESHOLD` | 0.8 | Max GPU memory usage |
| `CLAUDE_AUTO_REINDEX` | true | Enable auto-reindexing |
| `CLAUDE_MAX_INDEX_AGE` | 5.0 | Max index age in minutes |
| `CLAUDE_DEFAULT_K` | 5 | Default results count |
| `CLAUDE_MAX_K` | 50 | Maximum results count |

## Conclusion

Hybrid search provides significant improvements in both accuracy and efficiency. The default configuration works well for most use cases, but the extensive configuration options allow fine-tuning for specific needs.

**Key Takeaways:**
- ✅ **Default hybrid mode** provides best balance for most users
- ✅ **Weight tuning** allows optimization for specific query types
- ✅ **Multiple configuration methods** provide flexibility
- ✅ **Backward compatibility** ensures smooth migration
- ✅ **Performance monitoring** helps optimize usage

For questions or issues, refer to the troubleshooting section above or check the system logs with debug mode enabled.