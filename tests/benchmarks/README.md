# Benchmarking Infrastructure

This directory contains tools for benchmarking code search performance and tracking improvements across implementation phases.

## Files

- **`test_queries.json`** - Standard set of 50 test queries across 5 categories
- **`capture_baseline.py`** - Script to capture performance metrics
- **`baseline_metrics.json`** - Captured baseline metrics (v0.5.2)
- **`comparison_report.md`** - Generated comparison reports

## Usage

### Capture Baseline Metrics (v0.5.2)

Before implementing Phase 1, capture current performance:

```bash
cd F:\RD_PROJECTS\COMPONENTS\claude-context-local

# Capture baseline for current project
python tests/benchmarks/capture_baseline.py --project-path . --output tests/benchmarks/baseline_metrics.json

# Capture baseline for another project
python tests/benchmarks/capture_baseline.py --project-path "C:\Projects\MyProject" --output baseline_myproject.json
```

### Metrics Captured

1. **Index Statistics**
   - Total chunks indexed
   - Files indexed
   - Embedding model and dimension
   - Index type (FAISS, BM25)

2. **Performance Metrics** (per search mode)
   - Average query time (ms)
   - Median, min, max, stddev
   - P95 latency
   - Average results returned

3. **Multi-Hop Performance**
   - Success rate (% queries with results)
   - Average unique discoveries
   - Discovery statistics

4. **Search Quality** (requires ground truth labels)
   - Success@5, Success@10
   - Mean Reciprocal Rank (MRR)

### After Each Phase

1. Run the benchmark script again:

   ```bash
   python tests/benchmarks/capture_baseline.py --output tests/benchmarks/phase1_metrics.json
   ```

2. Compare metrics:

   ```bash
   python tests/benchmarks/compare_metrics.py baseline_metrics.json phase1_metrics.json
   ```

3. Generate report:

   ```bash
   python tests/benchmarks/generate_report.py --baseline baseline_metrics.json --current phase1_metrics.json --output phase1_report.md
   ```

## Test Queries

The `test_queries.json` file contains 50 queries across 5 categories:

1. **Identifier Queries** (10) - Test identifier matching (camelCase, snake_case)
2. **Semantic Queries** (10) - Natural language queries
3. **Structural Queries** (10) - Call graph and structural understanding
4. **Code Pattern Queries** (10) - Specific code patterns
5. **Domain-Specific Queries** (10) - Python/GLSL/C++ specific

### Adding Ground Truth Labels

To compute Success@k and MRR, add ground truth labels:

```json
{
  "query": "user data handler",
  "relevant_chunks": [
    "handlers.py:10-25:function:handle_user_data",
    "models.py:50-80:class:UserDataHandler"
  ],
  "most_relevant": "handlers.py:10-25:function:handle_user_data"
}
```

## Benchmark Results Format

```json
{
  "version": "v0.5.2",
  "timestamp": "2025-11-05 14:30:00",
  "index_statistics": {
    "total_chunks": 1199,
    "files_indexed": 109,
    "embedding_dimension": 1024,
    "model_name": "BAAI/bge-m3"
  },
  "performance": {
    "hybrid": {
      "avg_time_ms": 85.3,
      "median_time_ms": 78.2,
      "p95_time_ms": 125.4
    },
    "semantic": {
      "avg_time_ms": 78.1
    },
    "bm25": {
      "avg_time_ms": 5.2
    }
  },
  "multi_hop": {
    "success_rate": 0.933,
    "avg_unique_discoveries": 3.2
  }
}
```

## Success Criteria by Phase

### Phase 1 Targets

- Call graph coverage: 90%+ functions
- No performance regression: <10% increase in query time
- All existing tests pass: 100%

### Phase 2 Targets

- Identifier query improvement: +15% Success@10
- Multi-hop improvement: +10% discoveries
- Tokenization overhead: <5ms

### Phase 3 Targets

- Composite tool usage: 50%+ queries
- Context completeness: 80%+ queries
- Tool latency: <200ms

### Phase 4 Targets

- Type extraction coverage: 70%+
- Dependency graph accuracy: 95%+
- PageRank relevance boost: +5-10%

### Phase 5 Targets

- C++ call graph coverage: 80%+
- GLSL call graph coverage: 80%+
- Multi-language support: 100%

## Notes

- Run benchmarks on the same hardware for consistency
- Use a consistent set of test queries across phases
- Document any changes to test queries or methodology
- Keep baseline metrics for all phases for historical comparison
