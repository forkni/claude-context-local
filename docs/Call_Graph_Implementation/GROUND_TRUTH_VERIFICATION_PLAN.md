# Ground Truth Verification Plan

# SSCG Integration (5 Phases) + Research Improvements (3 Features)

**Date**: 2026-01-30
**Status**: Ready for Execution
**Purpose**: Comprehensive verification of all 8 implemented features using MCP tool calls with known expected results

---

## Test Set Overview

| Test ID | Feature | MCP Tool | Expected Result | Ground Truth |
|---------|---------|----------|-----------------|--------------|
| GT-1 | Phase 1: Subgraph | search_code | subgraph_nodes, subgraph_edges, subgraph_order present | SubgraphExtractor found in results |
| GT-2 | Phase 1: Topology | search_code | subgraph_order shows dependencies before usages | Graph classes ordered by calls |
| GT-3 | Phase 2: 21 Relations | search_code | graph field has >2 relationship types | Not just calls/called_by |
| GT-4 | Phase 3: Centrality | search_code | results have centrality and blended_score fields | CentralityRanker found |
| GT-5 | Phase 4: Communities | search_code | subgraph_communities present with labels | Community IDs on nodes |
| GT-6 | Phase 5: Ego-graph | search_code | Results with source="ego_graph" | Ego-graph neighbors in subgraph |
| GT-7 | Imp 1: Multi-hop | search_code | Results with source="graph_hop" or "hybrid" | Graph expansion active |
| GT-8 | Imp 2: P3 Extractors | find_connections | implements and overrides in relationships | P3 edges found |
| GT-9 | Imp 3: Weighted BFS | search_code | Higher centrality for highly-called functions | Weighted traversal active |

---

## GT-1: Phase 1 - Subgraph Extraction

### Test Query

```python
search_code(
    query="SubgraphExtractor class extract subgraph",
    k=5
)
```

### Expected Ground Truth

- **subgraph_nodes**: Array with at least 1 node containing:
  - `id`: "search/subgraph_extractor.py:93-390:class:SubgraphExtractor"
  - `kind`: "class"
  - `name`: "SubgraphExtractor"
  - `community`: Integer (community ID)

- **subgraph_edges**: Array with typed edges:
  - At least one edge with `rel` field (relationship type)
  - `src` and `tgt` point to valid chunk_ids in subgraph_nodes

- **subgraph_order**: Array of chunk_ids in topological order
  - SubgraphExtractor should appear in list
  - Dependencies (like BaseClass) should appear before SubgraphExtractor if inherited

### Verification Steps

1. Check `response.subgraph_nodes` exists and is non-empty
2. Verify SubgraphExtractor is in nodes list
3. Check `response.subgraph_edges` exists
4. Verify edges have `rel` field (typed relationships)
5. Check `response.subgraph_order` exists and is non-empty

---

## GT-2: Phase 1 - Topological Ordering

### Test Query

```python
search_code(
    query="graph storage operations get_neighbors add_edge",
    k=10
)
```

### Expected Ground Truth

- **subgraph_order** should show:
  - `CodeGraphStorage` class before methods that use it
  - `get_neighbors()` method in correct position relative to callers
  - If A calls B, then B appears before A in ordering (dependencies first)

### Verification Steps

1. Extract subgraph_order from response
2. Find CodeGraphStorage class chunk_id in order
3. Find methods that call get_neighbors
4. Verify called methods appear before calling methods in subgraph_order

---

## GT-3: Phase 2 - Full Relationship Coverage (21 Types)

### Test Query

```python
search_code(
    query="BaseRelationshipExtractor extract relationships",
    k=5
)
```

### Expected Ground Truth

- **results[].graph** should contain more than just "calls" and "called_by":
  - Expected types in BaseRelationshipExtractor:
    - `inherits`: Child extractors inheriting from BaseRelationshipExtractor
    - `uses_type`: Type annotations (str, dict, list, RelationshipEdge)
    - `imports`: Imported modules
    - `catches`: Exception handling (SyntaxError, etc.)
    - `instantiates`: Object creation (RelationshipEdge(), etc.)

### Verification Steps

1. Get first result from response
2. Extract `result.graph` field
3. Count unique relationship types (keys in graph dict)
4. Verify count > 2 (more than just calls/called_by)
5. Check for specific types: inherits, uses_type, catches

---

## GT-4: Phase 3 - Centrality Ranking (PageRank)

### Test Query

```python
search_code(
    query="CentralityRanker PageRank rerank annotate",
    k=5
)
```

### Expected Ground Truth

- **results[]** should have:
  - `centrality`: Float value (0.0 to 1.0 range)
  - `blended_score`: Float value (weighted combination of semantic + centrality)
  - `score`: Original semantic score

- **Specific values**:
  - CentralityRanker class should have centrality > 0 (it's used in search pipeline)
  - blended_score should differ from semantic score (proving blending occurred)

### Verification Steps

1. Get first result (CentralityRanker)
2. Verify `centrality` field exists and is > 0
3. Verify `blended_score` field exists
4. Check blended_score != score (proves blending active)

---

## GT-5: Phase 4 - Community Context (Louvain)

### Test Query

```python
search_code(
    query="relationship extractors inheritance implements override",
    k=10
)
```

### Expected Ground Truth

- **subgraph_communities**: Dict mapping community_id → {label, count}
  - Expected: Community ID for "relationship_extractors" or "graph"
  - Label should be descriptive (extracted from file paths)
  - Count should match number of nodes in that community

- **subgraph_nodes[]**: Each node should have `community` field
  - All ImplementsExtractor, OverrideExtractor should share same community ID
  - Community ID should match one of the keys in subgraph_communities

### Verification Steps

1. Check `response.subgraph_communities` exists
2. Verify it has at least 1 community entry
3. Extract community IDs from subgraph_nodes
4. Verify all community IDs in nodes exist in subgraph_communities
5. Check label is meaningful (not just a number)

---

## GT-6: Phase 5 - Ego-Graph Integration

### Test Query

```python
search_code(
    query="MultiHopSearcher search method",
    k=3,
    ego_graph_enabled=True,
    ego_graph_k_hops=2
)
```

### Expected Ground Truth

- **results[]**: Should contain results with `source="ego_graph"`
  - These are neighbors of primary search results
  - Should have lower scores (0.0 or near-zero)

- **subgraph_nodes[]**: Ego-graph neighbors should be in subgraph
  - Nodes with `source="ego_graph"` in metadata
  - Connected to primary results via typed edges

### Verification Steps

1. Filter results where `source="ego_graph"`
2. Verify at least 1 ego-graph result exists
3. Check ego-graph results have score ≈ 0
4. Verify ego-graph node IDs are in subgraph_nodes
5. Check subgraph_edges connects ego-graph nodes to primary results

---

## GT-7: Improvement 1 - Graph-Aware Multi-Hop Search

### Test Query

```python
search_code(
    query="graph expansion search results",
    k=3
    # Note: multi_hop is enabled by default with mode="hybrid"
)
```

### Expected Ground Truth

- **results[]**: Should contain results with:
  - `source="hybrid"` (primary results from hybrid search)
  - `source="graph_hop"` (results found via graph traversal)
  - OR results from initial search + multi-hop expanded results

- **Expected behavior**:
  - Results > k (due to multi-hop expansion)
  - Graph neighbors of top results should appear in expanded set
  - Multi-hop expansion should find structurally related code

### Verification Steps

1. Count total results (should be > k if expansion happened)
2. Check for `source` field in results
3. Verify at least one result has source indicating multi-hop expansion
4. Confirm results include both semantic matches and structural neighbors

---

## GT-8: Improvement 2 - P3 Relationship Extractors (implements/overrides)

### Test Query A: Implements Relationship

```python
find_connections(
    chunk_id="graph/relationship_extractors/base_extractor.py:25-309:class:BaseRelationshipExtractor",
    relationship_types=["implements", "inherits"]
)
```

### Expected Ground Truth

- **child_classes[]**: Should include:
  - ImplementsExtractor (relationship_type="inherits")
  - OverrideExtractor (relationship_type="inherits")
  - Other concrete extractor classes

- **relationship_types**: Should include "implements" in available types
  - Even if BaseRelationshipExtractor doesn't have implements edges itself

### Test Query B: Override Relationship

```python
find_connections(
    chunk_id="graph/relationship_extractors/override_extractor.py:27-318:class:OverrideExtractor",
    relationship_types=["overrides"]
)
```

### Expected Ground Truth

- **Overrides edges**: Should find methods with override relationships
  - Look for `_extract_from_method` or `_extract_from_class` overrides
  - These override parent methods from BaseRelationshipExtractor

### Verification Steps

1. Execute find_connections with inherits filter
2. Verify child_classes includes P3 extractors (ImplementsExtractor, OverrideExtractor)
3. Check relationship_type field shows "inherits"
4. Execute find_connections with overrides filter
5. Verify override edges are found (even if 0, confirms extractor is active)

---

## GT-9: Improvement 3 - Edge-Type-Weighted BFS

### Test Query

```python
search_code(
    query="CodeGraphStorage get_neighbors",
    k=5
)
```

### Expected Ground Truth

- **Centrality scores** should reflect weighted graph:
  - Functions with many `calls` edges should have higher centrality
  - Functions with only `imports` edges should have lower centrality
  - get_neighbors itself should have moderate-to-high centrality (it's widely used)

- **Indirect evidence**:
  - Multi-hop graph expansion (GT-7) uses DEFAULT_EDGE_WEIGHTS
  - Results should prioritize high-value relationships (calls > imports)

### Verification Steps

1. Get centrality score for get_neighbors method
2. Compare to other methods in same file
3. Verify high-centrality methods are those with many calls edges
4. Check that DEFAULT_EDGE_WEIGHTS is referenced in codebase (proves weights are active)

---

## Execution Plan

### Phase 1: Execute All Test Queries

For each GT test (GT-1 through GT-9):

1. Execute the MCP tool call
2. Capture full response JSON
3. Extract relevant fields for verification

### Phase 2: Verify Ground Truth

For each test:

1. Run verification steps listed above
2. Document PASS/FAIL with evidence
3. Note any unexpected results or deviations

### Phase 3: Summary Report

Create table with:

- Test ID
- Feature
- Status (PASS/FAIL)
- Evidence (key response fields)
- Notes (any issues or unexpected behavior)

---

## Success Criteria

**All tests PASS** means:

- All 5 SSCG phases are working correctly
- All 3 Research improvements are active
- Features are properly integrated into search pipeline
- MCP tools return expected structured data

**Expected Pass Rate**: 9/9 (100%)

---

## Next Steps After Verification

1. If all tests PASS:
   - Document verification results
   - Mark implementation as fully validated
   - Update SSCG_Integration_Plan.md and Research_Improvement_Plan.md with verification date

2. If any tests FAIL:
   - Document failure details
   - Identify root cause (implementation bug vs. test assumption error)
   - Create fix plan for failed features
   - Re-run verification after fixes
