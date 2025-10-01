# Evaluation Framework for Claude Context MCP

This directory contains the comprehensive evaluation framework for the Claude Context MCP semantic code search system. The framework provides benchmarking capabilities to measure search quality, token efficiency, and performance characteristics with GPU auto-detection.

## Overview

The evaluation framework provides:

- **Token Efficiency Evaluation**: Measures 93-97% token savings vs traditional file reading
- **Multi-metric Search Quality**: Precision, Recall, F1-score, MRR, NDCG
- **GPU Acceleration Testing**: Automatic hardware detection and performance comparison
- **Comparative Analysis**: Compare different search methods (Hybrid, BM25-only, Dense-only)
- **Model Comparison**: BGE-M3 vs Gemma benchmarking capabilities
- **Interactive Benchmarks**: User-friendly `run_benchmarks.bat` interface in root directory
- **Comprehensive Reporting**: Detailed performance reports and visualizations
- **Extensible Architecture**: Easy to add new evaluation methods and metrics

## Quick Start

### Interactive Benchmarks (Recommended)

```bash
# Windows - User-friendly menu interface (run from project root)
run_benchmarks.bat
```

**Available Options:**

1. **Token Efficiency Benchmark** (~10 seconds) - Validates 93-97% token reduction
2. **Search Method Comparison** (~2-3 minutes) - Compare Hybrid, BM25, and Semantic methods
3. **Auto-Tune Search Parameters** (~2 minutes) - Optimize BM25/Dense weights for your codebase
4. **Complete Suite** (~5 minutes) - Comprehensive performance profile including all benchmarks

### Command Line Interface

```bash
# Token efficiency evaluation (recommended first test)
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency

# Method comparison (Hybrid vs BM25 vs Semantic)
.venv\Scripts\python.exe evaluation/run_evaluation.py method-comparison --project "."

# Custom project evaluation
.venv\Scripts\python.exe evaluation/run_evaluation.py custom --project "path/to/project"

# GPU vs CPU comparison
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency --gpu
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency --cpu

# Auto-tune search parameters for your codebase
.venv\Scripts\python.exe tools/auto_tune_search.py --project "." --dataset evaluation/datasets/debug_scenarios.json

# Apply optimized parameters automatically
.venv\Scripts\python.exe tools/auto_tune_search.py --project "." --apply

# BGE-M3 model benchmarking
.venv\Scripts\python.exe evaluation/run_bge_m3_benchmark.py
```

## Framework Architecture

### Core Components

#### 1. Base Evaluator (`base_evaluator.py`)

- Abstract base class defining the evaluation interface
- Common metrics calculation (precision, recall, F1, MRR, NDCG)
- Dataset loading and result aggregation
- Report generation utilities

#### 2. Semantic Search Evaluator (`semantic_evaluator.py`)

- Concrete implementation for our hybrid search system
- Supports different search configurations:
  - `SemanticSearchEvaluator`: Full hybrid search (BM25 + Dense)
  - `BM25OnlyEvaluator`: Text-based search only
  - `DenseOnlyEvaluator`: Vector-based search only

#### 3. Token Efficiency Evaluator (`token_efficiency_evaluator.py`)

- Measures token savings vs traditional file reading approaches
- Token counting using tiktoken (cl100k_base encoding for GPT-4/Claude compatibility)
- Vanilla file reading simulation for comparison
- GPU vs CPU performance benchmarking
- 93-97% token reduction validation

#### 4. Evaluation Runner (`run_evaluation.py`)

- Command-line interface with GPU auto-detection
- Multiple evaluation modes:
  - `token-efficiency`: Token savings evaluation
  - `method-comparison`: Compare all search methods (hybrid, BM25, semantic)
  - `custom`: Project-specific search quality
  - `create-sample`: Generate test datasets
- Automatic hardware detection and optimization
- Logging and progress tracking

#### 5. Parameter Optimizer (`parameter_optimizer.py`)

- Auto-tune hybrid search parameters for your codebase
- Tests multiple weight configurations (BM25/Dense)
- Builds index once, tests parameters quickly (~2 minutes)
- Uses tie-breaking logic (F1-score primary, query time secondary)
- Generates recommendations with statistical analysis
- Optional parameter application to hybrid_searcher.py

**Key Features:**

- Strategic parameter testing (0.3/0.7, 0.4/0.6, 0.6/0.4)
- Index reuse for fast evaluation
- Clear status reporting ([OK], [BEST], [FAILED])
- Query time comparison for tie-breaking
- Automatic or manual parameter application

#### 6. BGE-M3 Benchmark Runner (`run_bge_m3_benchmark.py`)

- Wrapper script for running benchmarks with BGE-M3 model
- Sets `CLAUDE_EMBEDDING_MODEL=BAAI/bge-m3` environment variable
- Executes comprehensive benchmark suite:
  - Token efficiency benchmark with BGE-M3
  - Method comparison benchmark with BGE-M3
- Saves results to `benchmark_results/` for comparison
- Useful for evaluating BGE-M3 performance vs Gemma baseline

## Key Features Ported from Zilliz

Based on analysis of the original Zilliz implementation, we've incorporated:

### 1. **Comprehensive Metrics Suite**

```python
@dataclass
class SearchMetrics:
    query_time: float          # Search latency
    total_results: int         # Number of results returned
    precision: float           # Precision at k
    recall: float             # Recall at k
    f1_score: float           # Harmonic mean of precision and recall
    mrr: float                # Mean Reciprocal Rank
    ndcg: float               # Normalized Discounted Cumulative Gain
    token_usage: int          # Token consumption (for efficiency analysis)
    tool_calls: int           # Number of tool invocations
```

### 2. **Multi-Method Comparison**

- **Hybrid Search**: BM25 + Dense vector search with configurable weights
- **BM25-Only**: Traditional keyword/text search baseline
- **Dense-Only**: Pure semantic vector search
- **Efficiency Analysis**: Token usage and tool call reduction metrics

### 3. **Statistical Analysis**

- Aggregate metrics across multiple queries
- Standard deviation calculations
- Comparative improvement analysis
- Performance distribution analysis

## Usage Examples

### 1. Quick Start - Sample Evaluation

Create and run a sample evaluation:

```bash
# Create sample dataset
python evaluation/run_evaluation.py create-sample --output sample_dataset.json

# Run custom evaluation on test project
python evaluation/run_evaluation.py custom \
    --dataset sample_dataset.json \
    --project ./test_td_project \
    --method hybrid \
    --k 10 \
    --max-instances 5
```

### 2. Method Comparison

Compare all search methods on your project:

```bash
# Compare hybrid, BM25, and semantic search methods
python evaluation/run_evaluation.py method-comparison \
    --project "." \
    --output-dir method_comparison_results \
    --max-instances 10 \
    --k 10
```

### 3. Custom Dataset Evaluation

```bash
# Prepare your custom dataset (JSON format)
{
  "metadata": {
    "name": "my_evaluation_dataset",
    "description": "Custom evaluation for my project"
  },
  "instances": [
    {
      "instance_id": "query_001",
      "query": "authentication functions",
      "ground_truth_files": ["auth.py", "login.py"],
      "metadata": {"difficulty": "medium"}
    }
  ]
}

# Run evaluation
python evaluation/run_evaluation.py custom \
    --dataset my_dataset.json \
    --project /path/to/my/project \
    --method hybrid \
    --output-dir my_results
```

### 4. Auto-Tune Search Parameters

Optimize hybrid search weights for your specific codebase:

```bash
# Basic auto-tuning (shows recommendations)
python tools/auto_tune_search.py \
    --project "path/to/your/project" \
    --dataset evaluation/datasets/debug_scenarios.json

# Auto-tuning with automatic parameter application
python tools/auto_tune_search.py \
    --project "." \
    --apply

# With verbose logging
python tools/auto_tune_search.py \
    --project "." \
    --verbose
```

**Expected Output:**

```
Configuration Comparison:
BM25/Dense      F1-Score     Precision    Recall       Query(s)   Status
0.3/0.7         0.367        0.250        0.714        0.049      [OK]
0.4/0.6         0.367        0.250        0.714        0.043      [BEST]
0.6/0.4         0.338        0.226        0.714        0.041      [OK]

NOTE: Multiple configurations achieved F1=0.367
      Tie broken by query time (faster is better)

RECOMMENDED CONFIGURATION:
  bm25_weight: 0.4
  dense_weight: 0.6
  rrf_k: 60
```

**Key Benefits:**

- Codebase-specific optimization
- Fast evaluation (~2 minutes with index reuse)
- Statistical tie-breaking with query time
- Optional automatic parameter application
- Detailed performance reporting

### 5. BGE-M3 Model Benchmarking

Run comprehensive benchmarks with the BGE-M3 model:

```bash
# Run BGE-M3 benchmark suite
python evaluation/run_bge_m3_benchmark.py
```

This script will:
1. Set the embedding model to BGE-M3 (BAAI/bge-m3)
2. Run token efficiency benchmark with BGE-M3
3. Run method comparison benchmark with BGE-M3
4. Save results to `benchmark_results/token_efficiency_bge/` and `benchmark_results/method_comparison_bge/`

**Use Case:** Compare BGE-M3 performance (1024 dimensions, higher accuracy) against the Gemma baseline (768 dimensions, faster).

## Expected Results

Based on the Zilliz evaluation findings, you can expect:

### Actual Performance Results

**Measured evaluation results with test dataset (3 diverse queries):**

| Method | Precision | Recall | F1-Score | MRR | NDCG | Query Time |
|--------|-----------|--------|----------|-----|------|------------|
| **Hybrid** | **0.444** | 0.500 | **0.467** | **1.000** | **1.798** | 487ms |
| Dense-only | 0.389 | 0.500 | 0.433 | 1.000 | 1.594 | 487ms |
| BM25-only | 0.333 | 0.500 | 0.400 | 0.611 | 1.344 | 162ms |

**Key Achievements:**

- **Hybrid search superiority**: 33% higher precision than BM25-only
- **Perfect ranking**: 100% MRR for hybrid and dense methods
- **Sub-second performance**: All methods respond under 500ms
- **Optimal balance**: Hybrid provides best accuracy/speed trade-off

For complete methodology and analysis, see [BENCHMARKS.md](../docs/BENCHMARKS.md).

### Performance Improvements with Hybrid Search

- **Improved search accuracy** through dual-approach methodology
- **Reduced search iterations** via better result relevance
- **Superior F1-scores** (46.7% vs 40.0% for BM25-only)
- **Parallel query processing** with BM25+Dense search

### Expected Metrics Range

- **Precision**: 0.3-0.8 depending on dataset complexity
- **Recall**: 0.3-0.7 for top-k results
- **F1-Score**: 0.35-0.65 harmonic mean
- **Query Time**: 0.1-2.0 seconds per query
- **MRR**: 0.2-1.0 depending on ranking quality

## Configuration Options

### Search Method Configuration

```python
# Hybrid Search (default)
SemanticSearchEvaluator(
    bm25_weight=0.4,      # BM25 contribution
    dense_weight=0.6,     # Dense vector contribution
    use_gpu=True,         # GPU acceleration
    k=10                  # Top-k results
)

# BM25-Only Search
BM25OnlyEvaluator(
    k=10
)

# Dense-Only Search
SemanticSearchEvaluator(
    bm25_weight=0.0,
    dense_weight=1.0,
    use_gpu=True
)
```

### Evaluation Parameters

```python
evaluator = SemanticSearchEvaluator(
    output_dir="results",           # Results directory
    max_instances=50,               # Limit evaluation size
    k=10,                          # Top-k evaluation
    storage_dir="indices",         # Index storage location
    use_gpu=True                   # GPU acceleration
)
```

## Output Structure

The evaluation framework generates comprehensive outputs:

### Directory Structure

```
evaluation_results/
├── evaluation_results.json      # Detailed results
├── evaluation_summary.json      # Aggregate metrics
├── evaluation_report.txt        # Human-readable report
└── search_indices/              # Generated search indices
    ├── bm25/                    # BM25 index files
    └── dense/                   # Dense vector index files
```

### Results Format

```json
{
  "metadata": {
    "total_instances": 10,
    "project_path": "/path/to/project",
    "k": 10,
    "build_time": 45.2,
    "evaluation_timestamp": "2024-01-01T12:00:00"
  },
  "aggregate_metrics": {
    "precision": {"mean": 0.65, "stdev": 0.12},
    "recall": {"mean": 0.58, "stdev": 0.15},
    "f1_score": {"mean": 0.61, "stdev": 0.13},
    "query_time": {"mean": 0.45, "stdev": 0.23}
  },
  "results_by_instance": {
    "query_001": {
      "metrics": {...},
      "timestamp": 1234567890
    }
  }
}
```

## Advanced Features

### 1. Custom Metrics

Extend the framework with custom metrics:

```python
class CustomEvaluator(BaseEvaluator):
    def calculate_custom_metric(self, retrieved, ground_truth):
        # Implement your custom metric
        return custom_score
```

### 2. Dataset Filtering

Create focused evaluation datasets tailored to your project's search patterns and code structure for testing relevance and accuracy.

### 3. Performance Profiling

Track detailed performance metrics:

```python
evaluator = SemanticSearchEvaluator(output_dir="results")
results = evaluator.run_evaluation(instances, project_path)

# Access performance statistics
search_stats = evaluator.get_search_stats()
print(f"Average search time: {search_stats['average_times']['total']}")
print(f"GPU utilization: {search_stats['gpu_utilization']}")
```

## Integration with Existing System

The evaluation framework integrates seamlessly with the existing Claude Context MCP system:

### Components Used

- **HybridSearcher**: Core search orchestrator
- **CodeEmbedder**: GPU-accelerated embedding generation
- **MultiLanguageChunker**: Code parsing and chunking
- **BM25Index**: Sparse text search index
- **CodeIndexManager**: Dense vector index management

### GPU Optimization

- Automatic GPU detection and utilization
- Batch processing for efficient embedding generation
- Memory management for large datasets
- Fallback to CPU when GPU unavailable

## Testing

Comprehensive test suite covering all components:

```bash
# Run evaluation framework tests
python -m pytest tests/unit/test_evaluation.py -v

# Run token efficiency tests
python -m pytest tests/unit/test_token_efficiency.py -v

# Run all evaluation-related tests
python -m pytest tests/unit/test_evaluation.py tests/unit/test_token_efficiency.py -v

# Tests cover: base evaluator, metrics calculation, token efficiency,
# dataset loading, parameter optimization, and more
```

## Limitations and Future Work

### Current Limitations

- **Limited Dataset Size**: Optimized for datasets up to 1000 instances
- **Multi-Language Testing**: While the system supports 22 file extensions (11 languages), evaluation datasets primarily cover Python codebases
- **Manual Dataset Creation**: Custom evaluation datasets require manual preparation

### Planned Enhancements

- **SWE-bench Integration**: Industry-standard software engineering benchmark support with full repository management
- **Automated Dataset Generation**: Create evaluation datasets from existing codebases
- **Multi-language Evaluation Datasets**: Expanded test coverage for Java, TypeScript, Go, Rust, and other supported languages
- **Interactive Evaluation Dashboard**: Web-based interface for benchmark visualization
- **Continuous Evaluation**: Integration with CI/CD pipelines for automated quality tracking

## Conclusion

This evaluation framework provides a robust foundation for measuring and improving semantic code search systems. Based on proven methodologies from the Zilliz implementation, it offers comprehensive metrics, comparative analysis, and extensible architecture for adding new evaluation methods.

The framework demonstrates the effectiveness of hybrid search approaches, showing 93-97% token efficiency gains and superior search quality compared to individual methods. With support for both Gemma and BGE-M3 embedding models, it enables data-driven optimization decisions for your specific codebase. This makes it an essential tool for developing and optimizing semantic code search systems.
