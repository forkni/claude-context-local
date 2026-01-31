# Research Analysis & Focused Improvement Plan

**Date**: 2026-01-30
**Status**: Approved for implementation
**Based on**: Research analysis of 2 papers + full codebase exploration

## Research Documents Analyzed

1. **"Improving Code RAG with Structural Analysis"** - RepoGraph, SSCG, GRACE, cAST, GraphRAG survey
2. **"Code is not Natural Language" (USENIX Security '24)** - Semantics-Oriented Graph (SOG) for code similarity

## What's Already Implemented (SSCG Phases 1-5 complete)

The system has comprehensive coverage of research concepts:

- AST chunking (cAST) via tree-sitter for 9 languages
- 21 relationship types, 14 extractors, NetworkX DiGraph
- Ego-graph k-hop retrieval with stdlib/third-party filtering
- Community detection (Louvain) with surfacing
- PageRank centrality reranking
- Subgraph extraction with topological ordering
- Multi-hop semantic expansion, hybrid BM25+dense search, neural reranking

---

## Critical Gap Analysis

After studying both papers against the codebase, the **single most impactful gap** is:

> **The multi-hop expansion mechanism uses the wrong signal.**

Currently, `MultiHopSearcher` expands results via FAISS semantic similarity (hop-2 finds code that *looks similar*). The core finding of RepoGraph (+27% on SWE-bench) and SOG's ablation study (each edge type adds 1-3% recall) is that **graph traversal finds functionally necessary dependencies** that semantic search misses entirely.

The system already HAS graph-based expansion (ego-graph), but it runs separately from multi-hop, is opt-in, and doesn't influence the main search ranking. The ego-graph neighbors are appended as context with `score=0.0` rather than integrated into the ranked results.

---

## Selected Improvements (3 total, ranked by impact)

### Improvement 1: Graph-Aware Multi-Hop Search

**Impact**: HIGH - addresses the core research finding
**Effort**: Medium

**Problem**: `MultiHopSearcher.search()` (line 262-305 in `search/multi_hop_searcher.py`) does hop-2 expansion via `dense_index.get_similar_chunks_batched()` -- pure semantic similarity. A query for `process_payment()` finds semantically similar functions but misses `db.connect()` and `validate_card()` which are structurally required dependencies.

**Solution**: Add a `graph` multi-hop mode that uses `CodeGraphStorage.get_neighbors()` for expansion, and a `hybrid` mode that blends both signals:

```
multi_hop_mode: "semantic" (current default) | "graph" | "hybrid"
```

**Implementation**:

1. Add `_graph_expand()` method to `MultiHopSearcher` that calls `graph_storage.get_neighbors(chunk_id, max_depth=1)` for each initial result
2. Add `_hybrid_expand()` that combines graph neighbors + semantic neighbors, deduplicating
3. Re-rank all expanded results by query cosine similarity (existing `rerank_by_query()`)
4. Add `multi_hop_mode` config field to `MultiHopConfig` in `search/config.py`
5. Wire into `HybridSearcher.search()` which already passes `graph_storage` context

**Files to modify**:

- `search/multi_hop_searcher.py` - Add graph/hybrid expansion methods
- `search/config.py` - Add `multi_hop_mode` to `MultiHopConfig`
- `search/hybrid_searcher.py` - Pass graph_storage to multi-hop searcher
- `search_config.json` - Add default mode

**Test**: `tests/unit/search/test_multi_hop_searcher.py` - Add tests for graph mode expansion

---

### Improvement 2: Complete P3 Relationship Extractors (implements/overrides)

**Impact**: MEDIUM-HIGH - fills the most valuable missing relationship types for Python
**Effort**: Low-Medium

**Problem**: The `relationship_types.py` defines `implements` and `overrides` as P3 types, and `relationship_extractors/__init__.py` references `ProtocolImplementationExtractor` and `MethodOverrideExtractor`, but these are not yet exported or wired in. For Python codebases, these are critical:

- `implements`: Detects classes implementing `Protocol` or `ABC` interfaces
- `overrides`: Detects methods that override parent class methods

Without these, `find_connections()` cannot trace polymorphic call chains or find all implementations of an abstract interface.

**Implementation**:

1. Implement `ProtocolImplementationExtractor` - detect classes with `Protocol`/`ABC` bases, match method signatures
2. Implement `MethodOverrideExtractor` - detect methods in subclasses that share names with parent class methods (using inheritance graph from `InheritanceExtractor`)
3. Export both from `relationship_extractors/__init__.py`
4. Wire into `MultiLanguageChunker`'s extraction pipeline

**Files to modify**:

- `graph/relationship_extractors/` - New `protocol_implementation_extractor.py`, `method_override_extractor.py`
- `graph/relationship_extractors/__init__.py` - Export new extractors
- `chunking/multi_language_chunker.py` - Register extractors in pipeline

**Test**: New test files for each extractor + verify edges appear in `find_connections()` output

---

### Improvement 3: Edge-Type-Weighted Graph Traversal

**Impact**: MEDIUM - improves ego-graph and find_connections quality
**Effort**: Low

**Problem**: `CodeGraphStorage.get_neighbors()` (in `graph/graph_storage.py`) does unweighted BFS -- a `calls` edge and an `imports` edge have equal priority. The SOG paper's ablation (Table 2) shows that different relation types contribute differently: data flow (calls) > control flow > effect flow. In practice, for code search, an ego-graph neighbor connected via `calls` is much more relevant than one connected via `imports` (which just means "is in the same import list").

**Solution**: Add configurable edge-type weights to graph traversal. Default weights prioritize structural relationships:

```python
DEFAULT_EDGE_WEIGHTS = {
    "calls": 1.0,        # Most important for code understanding
    "inherits": 0.9,     # Critical for class hierarchies
    "implements": 0.9,   # Critical for interface patterns
    "overrides": 0.85,   # Important for polymorphism
    "uses_type": 0.7,    # Type usage
    "instantiates": 0.7, # Object creation
    "imports": 0.3,      # Low signal - most code imports many things
    "decorates": 0.5,    # Moderate signal
    "raises": 0.4,       # Exception patterns
    "catches": 0.4,      # Exception patterns
    # ... defaults to 0.5 for unlisted types
}
```

**Implementation**:

1. Add `edge_weights: dict[str, float]` parameter to `get_neighbors()` in `graph_storage.py`
2. During BFS, use weights to sort/prioritize neighbors before the `max_depth` limit is applied (weighted BFS: higher-weight edges expanded first)
3. Add `edge_weights` to `EgoGraphConfig` in `search/config.py`
4. Pass weights through from `EgoGraphRetriever.retrieve_ego_graph()`

**Files to modify**:

- `graph/graph_storage.py` - Add weighted BFS to `get_neighbors()`
- `search/config.py` - Add `edge_weights` to `EgoGraphConfig`
- `search/ego_graph_retriever.py` - Pass weights to graph storage

**Test**: `tests/unit/graph/test_graph_storage_get_neighbors.py` - Add weighted traversal tests

---

## Why These 3 and Not Others

| Rejected Proposal | Reason |
|---|---|
| Hierarchical Leiden communities | Current Louvain works. Hierarchical adds complexity for marginal architectural-overview benefit in a *search* tool. |
| Recursive summarization | Requires LLM calls per community, adding latency and cost. Not aligned with the system's fast, local search focus. |
| Query-graph fusion (GRACE) | Only helps for queries containing code symbols. Niche benefit. |
| CFG/PDG/taint analysis | Very high complexity for intra-function analysis. The system operates at inter-function granularity. |
| Graph embedding fusion | Requires training custom models. The late-fusion approach (search + graph expansion + centrality reranking) captures most of the benefit. |
| Multi-language graph support | Project is Python-focused by design. |

---

## Key Insights from SOG Paper (Applicable Lessons)

While targeting binary code, these insights transfer to source-code search:

1. **"Code is not natural language"**: Validates the system's AST-based chunking and graph representation over flat text approaches.

2. **Multiple relation types matter**: SOG ablation (Table 2) shows progressive improvement as edge types are added (DFG -> CDFG -> ISCG -> TSCG -> SOG). Each type adds 1-3% recall. Validates the system's 21 relationship types.

3. **Removing noise improves generalization**: SOG's purging of semantics-independent elements improved efficiency by 32% fewer nodes, 23% fewer edges. **Applicable**: Low-value edges (common stdlib imports) should be deprioritized in traversal (addressed by Improvement 3).

4. **Multi-head aggregation**: Different relation types should contribute differently. SOG's multi-head softmax showed 134% improvement over single-head. **Applicable**: Edge-type weighting (Improvement 3).

5. **Graph scales better with pool size**: HermesSim's advantage *increased* as pool size grew (Figure 7). Graph-enhanced search becomes relatively more valuable as codebase size grows.

---

## Verification Strategy

**Per-improvement**:

1. Unit tests with mocked graph/index
2. Regression: `pytest tests/unit/ -x` (all 1,540+ tests pass)
3. Integration: Index `claude-context-local`, run MCP queries
4. Quality check: Compare search results before/after on dependency-heavy queries like:
   - `search_code("graph storage operations")` -- should now find callees in graph-mode multi-hop
   - `find_connections("BaseRelationshipExtractor", relationship_types=["implements"])` -- should return concrete extractors
   - Ego-graph with weights: verify `calls` neighbors ranked above `imports` neighbors
