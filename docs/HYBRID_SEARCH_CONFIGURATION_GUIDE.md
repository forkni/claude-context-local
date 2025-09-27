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
  "use_parallel_search": true,
  "rrf_k_parameter": 100,
  "prefer_gpu": true,
  "gpu_batch_size": 32,
  "cpu_chunk_size": 100,
  "max_worker_threads": 4,
  "enable_auto_reindex": true,
  "max_index_age_minutes": 5.0,
  "force_reindex_on_startup": false,
  "gpu_memory_threshold": 0.8,
  "cache_embeddings": true,
  "debug_mode": false
}
```

This configuration provides optimal performance for most Windows development environments with CUDA-capable GPUs.
