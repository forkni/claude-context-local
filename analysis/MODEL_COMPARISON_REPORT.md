# Model Comparison Report: BGE-M3 vs Qodo-1.5B

**Date**: 2025-11-10 00:04:57
**Queries Tested**: 30

## Executive Summary

### Overall Results

- **BGE-M3 wins**: 9 queries
- **Qodo-1.5B wins**: 11 queries
- **Ties**: 10 queries

### Results by Category

| Category | BGE-M3 | Qodo-1.5B | Tie |
|----------|--------|-----------|-----|
| Architecture | 0 | 4 | 2 |
| Code Specific | 3 | 4 | 1 |
| Cross Language | 1 | 1 | 2 |
| Error Handling | 3 | 1 | 1 |
| Graph Aware | 1 | 1 | 2 |
| Performance | 1 | 0 | 2 |

### Performance Metrics

| Metric | BGE-M3 | Qodo-1.5B | Difference |
|--------|--------|-----------|------------|
| Median latency | 34ms | 34ms | +-0ms |
| p95 latency | 51ms | 49ms | +-2ms |
| Average latency | 2803ms | 38ms | +-2765ms |

### Result Overlap Metrics

- **Average top-5 overlap (Jaccard)**: 1.00
- **Median top-5 overlap**: 1.00
- **Average rank correlation (Kendall's Tau)**: N/A

### Graph Metadata Analysis

- **BGE-M3 graph presence**: 0.0% of results
- **Qodo-1.5B graph presence**: 0.0% of results
- **Graph consistency**: 30/30 queries (100.0%)

## Per-Query Results

| ID | Category | Query | BGE-M3 Top-1 | Qodo-1.5B Top-1 | Overlap | Winner |
|----|----------|-------|--------------|-----------------|---------|--------|
| 1 | code_specific | function that generates embeddings in ba... |  |  | 1.00 | Qodo-1.5B |
| 2 | code_specific | BM25 tokenization with stopword filterin... |  |  | 1.00 | Qodo-1.5B |
| 3 | code_specific | FAISS index initialization and GPU manag... |  |  | 1.00 | BGE-M3 |
| 4 | code_specific | tree-sitter AST parsing for multiple lan... |  |  | 1.00 | BGE-M3 |
| 5 | code_specific | call graph extraction using Python AST v... |  |  | 1.00 | Tie |
| 6 | code_specific | Merkle tree change detection for increme... |  |  | 1.00 | Qodo-1.5B |
| 7 | code_specific | hybrid search RRF reranking algorithm... |  |  | 1.00 | BGE-M3 |
| 8 | code_specific | model cache validation with incomplete d... |  |  | 1.00 | Qodo-1.5B |
| 9 | architecture | how does multi-hop search discover relat... |  |  | 1.00 | Qodo-1.5B |
| 10 | architecture | MCP server tool implementation pattern... |  |  | 1.00 | Qodo-1.5B |
| 11 | architecture | configuration management and persistence... |  |  | 1.00 | Tie |
| 12 | architecture | incremental indexing workflow with Merkl... |  |  | 1.00 | Qodo-1.5B |
| 13 | architecture | storage directory per-model dimension is... |  |  | 1.00 | Tie |
| 14 | architecture | embedding batch size optimization by mod... |  |  | 1.00 | Qodo-1.5B |
| 15 | error_handling | corrupted model cache recovery and fallb... |  |  | 1.00 | BGE-M3 |
| 16 | error_handling | BM25 index version mismatch detection... |  |  | 1.00 | BGE-M3 |
| 17 | error_handling | GPU memory exhaustion handling... |  |  | 1.00 | Tie |
| 18 | error_handling | file removal with FAISS index rebuild... |  |  | 1.00 | Qodo-1.5B |
| 19 | error_handling | empty query validation and graceful retu... |  |  | 1.00 | BGE-M3 |
| 20 | cross_language | JavaScript function chunking with arrow ... |  |  | 1.00 | Tie |
| 21 | cross_language | GLSL shader parsing for fragment and ver... |  |  | 1.00 | Qodo-1.5B |
| 22 | cross_language | camelCase and snake_case identifier spli... |  |  | 1.00 | Tie |
| 23 | cross_language | tree-sitter node type mapping to chunk t... |  |  | 1.00 | BGE-M3 |
| 24 | graph_aware | functions that call search_code in MCP s... |  |  | 1.00 | BGE-M3 |
| 25 | graph_aware | functions called by HybridSearcher.searc... |  |  | 1.00 | Tie |
| 26 | graph_aware | FastMCP tool decorators and their implem... |  |  | 1.00 | Qodo-1.5B |
| 27 | graph_aware | network graph of incremental indexing co... |  |  | 1.00 | Tie |
| 28 | performance | parallel search execution with ThreadPoo... |  |  | 1.00 | Tie |
| 29 | performance | batch removal optimization single-pass a... |  |  | 1.00 | BGE-M3 |
| 30 | performance | embedding generation with configurable b... |  |  | 1.00 | Tie |

## Recommendations

**Recommendation**: Switch to **Qodo-1.5B** for this codebase.

**Reason**: Qodo-1.5B won 11 queries vs BGE-M3's 9, 
demonstrating superior code-specific retrieval despite being -0ms slower on average.
