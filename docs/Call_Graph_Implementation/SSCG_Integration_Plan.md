# Structural-Semantic Code Graph (SSCG) Integration Plan

**Version**: 1.1
**Date**: 2026-01-29
**Status**: Phase 1 Completed and Validated
**Target Version**: v0.9.0

---

## Executive Summary

This plan transforms MCP `search_code` output from a flat list of matching code chunks into a **coherent subgraph** with typed connections between nodes, topological ordering, community context, and centrality-informed ranking.

**Research basis**:
- **RepoGraph** (ICLR 2025): +27% absolute improvement on SWE-bench via ego-graph retrieval over code dependency graphs
- **LogicLens** (arXiv 2601.10773, Jan 2026): Three-phase graph construction (structural → semantic → concept extraction) yielding 0%→69.5% accuracy improvement over flat RAG
- **GRACE**: Dual-path encoding (semantic + structural) with graph-aware reranking via PageRank centrality
- **Microsoft GraphRAG**: Community detection (Louvain/Leiden) for global code understanding

**Key insight**: Most graph infrastructure already exists in `claude-context-local` (NetworkX DiGraph, 21 relationship types, 14 extractors, ego-graph retriever, community detection, centrality computation). The gap is a **serialization layer** that extracts an induced subgraph over search results and presents it as a connected, typed structure the consuming agent can traverse.

---

## Current State Analysis

### What Exists (Strong Foundation)

| Component | File | Status |
|-----------|------|--------|
| NetworkX DiGraph storage | `graph/graph_storage.py` → `CodeGraphStorage` | Production |
| 21 relationship types (5 priority groups) | `graph/relationship_types.py` → `RelationshipType` enum | Production |
| 14 relationship extractors | `graph/relationship_extractors/*.py` | Production |
| Call graph extraction (Python AST) | `graph/call_graph_extractor.py` | Production |
| Graph query engine | `graph/graph_queries.py` → `GraphQueryEngine` | Production |
| Ego-graph retrieval | `search/ego_graph_retriever.py` → `EgoGraphRetriever` | Production |
| Community detection (Louvain) | `graph/community_detector.py` | Production |
| Centrality computation (PageRank, betweenness, degree, closeness) | `graph/graph_queries.py` → `compute_centrality()` | Production |
| Graph integration orchestration | `search/graph_integration.py` → `GraphIntegration` | Production |
| Impact analysis (22+ fields) | `mcp_server/tools/code_relationship_analyzer.py` → `ImpactReport` | Production |
| Relation filtering (stdlib/third-party) | `graph/relation_filter.py` → `RepositoryRelationFilter` | Production |

### The Gap (What's Missing)

| Gap | Impact | Current Behavior |
|-----|--------|-----------------|
| **No subgraph in search output** | Agent sees disconnected chunks, not a graph | Results are a flat JSON array |
| **Only CALLS edges in search enrichment** | 20 other relationship types invisible | `_get_graph_data_for_chunk()` only queries `get_callees()`/`get_callers()` |
| **No topological ordering** | Dependencies don't appear before usage | Results ordered only by semantic score |
| **Ego-graph loses structure** | Neighbors flattened to list, edges discarded | `flatten_for_context()` strips edge information |
| **Communities not surfaced** | No architectural context in results | Community map stored but never exposed |
| **Centrality unused in ranking** | Structurally important code not prioritized | PageRank computed but never applied to search |

### Current Search Response Format

```json
{
  "query": "authentication handler",
  "results": [
    {
      "file": "auth.py",
      "lines": "10-50",
      "kind": "function",
      "score": 0.87,
      "chunk_id": "auth.py:10-50:function:login",
      "graph": {
        "calls": ["db.query", "session.create"],
        "called_by": ["api.py:5-30:function:handle_request"]
      }
    }
  ]
}
```

### Target Search Response Format (After SSCG)

```json
{
  "query": "authentication handler",
  "results": [
    {
      "file": "auth.py",
      "lines": "10-50",
      "kind": "function",
      "score": 0.87,
      "chunk_id": "auth.py:10-50:function:login",
      "centrality": 0.0342,
      "graph": {
        "calls": ["db.query", "session.create"],
        "called_by": ["api.py:5-30:function:handle_request"],
        "imports": ["hashlib", "jwt"],
        "uses_type": ["UserModel"],
        "raises": ["AuthenticationError"]
      }
    }
  ],
  "subgraph": {
    "nodes": [
      {"id": "auth.py:10-50:function:login", "name": "login", "kind": "function", "file": "auth.py", "community": 2},
      {"id": "auth.py:55-80:class:AuthService", "name": "AuthService", "kind": "class", "file": "auth.py", "community": 2},
      {"id": "db.py:5-20:function:query", "name": "query", "kind": "function", "file": "db.py", "community": 0}
    ],
    "edges": [
      {"src": "auth.py:10-50:function:login", "tgt": "db.py:5-20:function:query", "rel": "calls"},
      {"src": "auth.py:55-80:class:AuthService", "tgt": "auth.py:10-50:function:login", "rel": "calls"},
      {"src": "auth.py:10-50:function:login", "tgt": "AuthenticationError", "rel": "raises", "boundary": true}
    ],
    "topology_order": ["db.py:5-20:function:query", "auth.py:10-50:function:login", "auth.py:55-80:class:AuthService"],
    "communities": {
      "0": {"label": "database", "count": 1},
      "2": {"label": "auth", "count": 2}
    }
  }
}
```

---

## Implementation Phases

### Phase 1: Subgraph Extraction and Serialization ✅ COMPLETED (2026-01-29)

**Goal**: Add a `subgraph` field to `search_code` response containing nodes, typed edges, and topological ordering.

**Why first**: This is the core transformation from "list of functions" to "coherent graph". All other phases build on this.

#### 1.1 Create `search/subgraph_extractor.py`

**Data structures:**

```python
@dataclass(slots=True)
class SubgraphNode:
    chunk_id: str
    name: str
    kind: str           # function, class, method, module...
    file: str
    community_id: int | None = None
    centrality: float | None = None
    is_search_result: bool = True   # False for ego-graph neighbors

@dataclass(slots=True)
class SubgraphEdge:
    source: str          # chunk_id or symbol name
    target: str          # chunk_id or symbol name
    rel_type: str        # One of 21 RelationshipType values
    line: int = 0
    is_boundary: bool = False  # Edge pointing outside the result set

@dataclass
class SubgraphResult:
    nodes: list[SubgraphNode]
    edges: list[SubgraphEdge]
    topology_order: list[str]
    communities: dict[int, dict] | None = None

    def to_dict(self) -> dict:
        """Compact JSON serialization (JSON Graph Format inspired)."""
        result = {
            "nodes": [self._node_dict(n) for n in self.nodes],
            "edges": [self._edge_dict(e) for e in self.edges],
            "topology_order": self.topology_order,
        }
        if self.communities:
            result["communities"] = self.communities
        return result

    def _node_dict(self, n: SubgraphNode) -> dict:
        d = {"id": n.chunk_id, "name": n.name, "kind": n.kind, "file": n.file}
        if n.community_id is not None:
            d["community"] = n.community_id
        if n.centrality:
            d["centrality"] = round(n.centrality, 4)
        if not n.is_search_result:
            d["source"] = "ego_graph"
        return d

    def _edge_dict(self, e: SubgraphEdge) -> dict:
        d = {"src": e.source, "tgt": e.target, "rel": e.rel_type}
        if e.line:
            d["line"] = e.line
        if e.is_boundary:
            d["boundary"] = True
        return d
```

**Core class:**

```python
class SubgraphExtractor:
    """Extract induced subgraph over search result chunk_ids."""

    def __init__(self, graph_storage: CodeGraphStorage):
        self.graph = graph_storage

    def extract_subgraph(
        self,
        chunk_ids: list[str],
        include_boundary_edges: bool = False,
        max_boundary_depth: int = 1,
    ) -> SubgraphResult:
        """
        Extract the induced subgraph over the given chunk_ids.

        Algorithm:
        1. Collect result chunk_ids as node set
        2. For each node, iterate out_edges and in_edges
        3. If both endpoints are in node set → inter-edge (always included)
        4. If one endpoint is outside → boundary edge (optional)
        5. Build topological ordering (SCC condensation for cycles)
        6. Return SubgraphResult
        """
```

**Topological ordering approach:**
- Extract induced subgraph as `nx.DiGraph.subgraph(chunk_ids)`
- Try `nx.topological_sort()` first (works if DAG)
- If cycle detected (`NetworkXUnfeasible`), use `nx.condensation()` to create SCC-based DAG, topologically sort that, then expand SCCs back to individual nodes
- Result: dependencies appear before their users where possible

#### 1.2 Modify `mcp_server/tools/search_handlers.py`

**Integration point**: Lines 748-778 (post-enrichment, before response building):

```python
# === SSCG Phase 1: Extract subgraph over search results ===
subgraph_data = None
if index_manager and index_manager.graph_storage is not None:
    try:
        from search.subgraph_extractor import SubgraphExtractor
        extractor = SubgraphExtractor(index_manager.graph_storage)
        # Top-k limiting: Use only original search results, not ego-graph neighbors
        result_chunk_ids = [r["chunk_id"] for r in formatted_results[:k] if "chunk_id" in r]

        if result_chunk_ids:
            # Boundary edges enabled by default for structural context
            subgraph = extractor.extract_subgraph(result_chunk_ids, include_boundary_edges=True)
            if subgraph.nodes:  # Include even if only boundary edges exist
                subgraph_data = subgraph.to_dict()
                logger.debug(f"[SSCG] Extracted subgraph: {len(subgraph.nodes)} nodes, {len(subgraph.edges)} edges")
            else:
                logger.info(f"[SSCG] No graph nodes found for {len(result_chunk_ids)} chunk_ids")
    except Exception as e:
        logger.debug(f"[SSCG] Subgraph extraction failed: {e}")

# Build response with flattened subgraph keys for TOON format compatibility
response = {"query": query, "results": formatted_results}
if subgraph_data:
    response["subgraph_nodes"] = subgraph_data["nodes"]
    response["subgraph_edges"] = subgraph_data["edges"]
    if subgraph_data.get("topology_order"):
        response["subgraph_order"] = subgraph_data["topology_order"]
    if subgraph_data.get("communities"):
        response["subgraph_communities"] = subgraph_data["communities"]
```

#### 1.3 Output formatter compatibility

The existing `output_formatter.py` handles nested dicts automatically:
- **Compact mode**: Omits empty fields (already the pattern)
- **Ultra/TOON mode**: Converts `nodes`/`edges` arrays to tabular format via existing `_to_toon_format()` logic

No changes needed to `output_formatter.py` for Phase 1.

#### 1.4 Testing

**Unit tests** (`tests/unit/search/test_subgraph_extractor.py`):
- `test_extract_subgraph_basic` -- 5 nodes with 8 typed edges, verify correct extraction
- `test_extract_subgraph_no_edges` -- disconnected nodes, verify no subgraph returned
- `test_topological_order_dag` -- linear dependency chain, verify correct ordering
- `test_topological_order_cycles` -- mutual recursion, verify SCC-based fallback
- `test_boundary_edges` -- with `include_boundary_edges=True`, verify boundary edges marked
- `test_compact_serialization` -- verify `to_dict()` omits empty optional fields
- `test_token_budget` -- measure JSON string length, assert < 600 tokens for 5 nodes + 10 edges

**Functional validation via MCP**:
- Index this project: `index_directory("F:/RD_PROJECTS/COMPONENTS/claude-context-local")`
- Run: `search_code("graph storage operations", k=5)`
- Verify: response contains `"subgraph"` field with typed edges between result chunks

#### Phase 1 Implementation Status: ✅ COMPLETED (2026-01-29)

**Files Created:**
- `search/subgraph_extractor.py` — Core extraction module (315 lines)
- `tests/unit/search/test_subgraph_extractor.py` — 14 unit tests

**Files Modified:**
- `mcp_server/tools/search_handlers.py` — Integration block (lines 748-778)
- `tests/unit/mcp_server/test_output_formatter.py` — 3 subgraph formatting tests

**All planned targets achieved:**

| Plan Target | Status | Implementation |
|-------------|--------|----------------|
| `SubgraphNode` dataclass | ✅ | Exact match + `is_search_result` field |
| `SubgraphEdge` dataclass | ✅ | Exact match |
| `SubgraphResult.to_dict()` | ✅ | Exact match |
| `SubgraphExtractor.extract_subgraph()` | ✅ | Enhanced with boundary cap |
| Topological ordering (DAG + SCC fallback) | ✅ | Exact match |
| Integration in search_handlers.py | ✅ | Flattened keys (see deviations) |
| Output formatter compatibility | ✅ | No formatter changes needed |
| 7 planned unit tests | ✅ | 14 tests (exceeded) + 3 formatter tests |
| MCP functional validation | ✅ | Verified all 3 formats (ultra/compact/verbose) |

**Deviations from original plan (all improvements):**

1. **Flattened response keys**: Instead of nested `response["subgraph"] = {...}`, subgraph data uses top-level keys: `subgraph_nodes`, `subgraph_edges`, `subgraph_order`, `subgraph_communities`. Reason: ultra/TOON format only converts top-level list-of-dicts to tabular format. Nested structures bypass TOON conversion.

2. **Top-k limiting**: Only `formatted_results[:k]` (original search results) are used for subgraph extraction, not ego-graph expanded neighbors. Prevents subgraph token explosion.

3. **Boundary edges enabled by default**: Search handler passes `include_boundary_edges=True`. Original plan had `False` as default. Changed because with diverse top-k results, inter-edges are unlikely — boundary edges provide the structural context.

4. **Boundary edge cap**: `MAX_BOUNDARY_PER_NODE = 3` added to prevent token explosion (a function may call 20+ others). Each source node limited to 3 outgoing boundary edges.

5. **Relative path conversion**: Added `os.path.relpath()` for `file` field in subgraph nodes to reduce token waste from absolute paths. Gated by `project_root` attribute.

6. **Condition relaxed**: Changed `if subgraph.edges:` to `if subgraph.nodes:` to include subgraph even when only boundary edges exist.

**Known issue (deferred):**
- `file` field in subgraph nodes contains absolute paths in MCP output because `CodeGraphStorage` does not expose `project_root`. The relative path logic works (unit tested) but requires `graph_storage.project_root` to be set. Fix in Phase 4 or dedicated follow-up.

**Test results:**
- 14/14 subgraph extractor tests pass
- 40/40 output formatter tests pass
- 188/188 full MCP server tests pass

**MCP validation results (2026-01-29):**
- Ultra: `subgraph_nodes[5]{file,id,kind,name}` + `subgraph_edges[7]{boundary,line,rel,src,tgt}` ✅
- Compact: `subgraph_nodes` + `subgraph_edges` arrays ✅
- Verbose: Full JSON with all subgraph fields ✅
- Token budget: ~370 tokens (under 600 target) ✅

---

### Phase 2: Full Relationship Enrichment Per Result

**Goal**: Expand per-result `graph` field from `{calls, called_by}` to all 21 relationship types.

#### 2.1 Modify `_get_graph_data_for_chunk()` in `search_handlers.py` (line 328)

Replace current implementation:

```python
def _get_graph_data_for_chunk(
    index_manager: CodeIndexManager, chunk_id: str,
    max_per_type: int = 5,
) -> dict | None:
    """Get all graph relationship data for a chunk (21 relationship types)."""
    try:
        graph = index_manager.graph_storage
        normalized = normalize_path(chunk_id)
        result = {}

        # Outgoing edges (this chunk is source)
        if normalized in graph.graph:
            for _, target, data in graph.graph.out_edges(normalized, data=True):
                rel_type = data.get("type", "calls")
                lst = result.setdefault(rel_type, [])
                if len(lst) < max_per_type:
                    lst.append(target)

        # Incoming edges by chunk_id
        if normalized in graph.graph:
            for source, _, data in graph.graph.in_edges(normalized, data=True):
                rel_type = data.get("type", "calls")
                reverse = _get_reverse_relation_name(rel_type)
                lst = result.setdefault(reverse, [])
                if len(lst) < max_per_type:
                    lst.append(source)

        # Incoming edges by symbol name (edges often target bare names)
        symbol_name = normalized.split(":")[-1] if ":" in normalized else None
        if symbol_name and symbol_name != normalized and symbol_name in graph.graph:
            for source, _, data in graph.graph.in_edges(symbol_name, data=True):
                rel_type = data.get("type", "calls")
                reverse = _get_reverse_relation_name(rel_type)
                lst = result.setdefault(reverse, [])
                if len(lst) < max_per_type and source not in lst:
                    lst.append(source)

        return result if result else None
    except Exception as e:
        logger.debug(f"Failed to get graph data for {chunk_id}: {e}")
    return None
```

Add helper function:

```python
_REVERSE_RELATION_MAP = {
    "calls": "called_by",
    "inherits": "inherited_by",
    "uses_type": "type_used_by",
    "imports": "imported_by",
    "decorates": "decorated_by",
    "raises": "raised_by",
    "catches": "caught_by",
    "instantiates": "instantiated_by",
    "implements": "implemented_by",
    "overrides": "overridden_by",
    "assigns_to": "assigned_by",
    "reads_from": "read_by",
    "defines_constant": "constant_defined_in",
    "defines_enum_member": "enum_member_defined_in",
    "defines_class_attr": "class_attr_defined_in",
    "defines_field": "field_defined_in",
    "uses_constant": "constant_used_by",
    "uses_default": "default_used_by",
    "uses_global": "global_used_by",
    "asserts_type": "type_asserted_by",
    "uses_context_manager": "context_manager_used_by",
}

def _get_reverse_relation_name(rel_type: str) -> str:
    return _REVERSE_RELATION_MAP.get(rel_type, f"{rel_type}_by")
```

#### 2.2 Testing

**Unit tests** (`tests/unit/mcp_server/test_graph_enrichment.py`):
- `test_full_relationship_enrichment` -- mock graph with inherits, imports, uses_type edges; verify all appear
- `test_max_per_type_cap` -- 10 callers but cap=5, verify truncation
- `test_backward_compat_calls` -- existing `calls`/`called_by` behavior unchanged
- `test_empty_graph` -- verify None returned gracefully

**Functional validation via MCP**:
- `search_code("BaseRelationshipExtractor", chunk_type="class")`
- Verify: result `graph` field contains `inherits`, `inherited_by`, `imports` etc. (not just calls)

---

### Phase 3: Centrality-Informed Result Ranking

**Goal**: Blend PageRank centrality with semantic scores to boost structurally important results.

#### 3.1 Create `search/centrality_ranker.py`

```python
class CentralityRanker:
    """Boost search results by structural importance via PageRank."""

    def __init__(self, graph_storage: CodeGraphStorage, alpha: float = 0.15):
        self.graph = graph_storage
        self.alpha = alpha
        self._pagerank_cache: dict[str, float] | None = None
        self._cache_node_count: int = 0

    def get_pagerank(self) -> dict[str, float]:
        """Compute or return cached PageRank scores."""
        current = self.graph.graph.number_of_nodes()
        if self._pagerank_cache is None or self._cache_node_count != current:
            self._pagerank_cache = nx.pagerank(self.graph.graph, max_iter=100)
            self._cache_node_count = current
        return self._pagerank_cache

    def rerank(self, results: list[dict], alpha: float | None = None) -> list[dict]:
        """Blend semantic + centrality scores. Annotate each result with centrality."""
        alpha = alpha or self.alpha
        pagerank = self.get_pagerank()
        max_pr = max(pagerank.values()) if pagerank else 1.0

        for r in results:
            pr = pagerank.get(r.get("chunk_id", ""), 0.0)
            normalized_pr = pr / max_pr if max_pr > 0 else 0.0
            r["centrality"] = round(normalized_pr, 4)
            # Blended score used for reranking but not overwriting original score
            r["_blend"] = (1 - alpha) * r.get("score", 0) + alpha * normalized_pr

        results.sort(key=lambda r: r.pop("_blend", 0), reverse=True)
        return results
```

#### 3.2 Configuration

Add to `search/config.py`:

```python
@dataclass
class GraphEnhancedConfig:
    """SSCG graph-enhanced search configuration."""
    subgraph_in_results: bool = True
    centrality_reranking: bool = False
    centrality_alpha: float = 0.15
    include_communities: bool = True
    max_relationships_per_type: int = 5
```

Persist in `search_config.json` under `"graph_enhanced"` key.

#### 3.3 Integration

In `handle_search_code()`, after enrichment, before response building:

```python
if graph_config.centrality_reranking and index_manager and index_manager.graph_storage:
    ranker = CentralityRanker(index_manager.graph_storage, graph_config.centrality_alpha)
    formatted_results = ranker.rerank(formatted_results)
```

#### 3.4 Testing

**Unit tests** (`tests/unit/search/test_centrality_ranker.py`):
- `test_rerank_basic` -- 5 results with known PageRank, verify order change
- `test_alpha_zero` -- alpha=0.0 preserves original semantic order
- `test_alpha_one` -- alpha=1.0 produces pure centrality order
- `test_centrality_annotation` -- verify `centrality` field added to each result
- `test_cache_invalidation` -- add node to graph, verify cache refreshes

**Performance benchmark**:
- PageRank on 5000-node graph: target < 100ms

**Functional validation via MCP**:
- `search_code("search handler", k=5)` with centrality enabled
- Verify: results include `centrality` field, order may differ from pure semantic

---

### Phase 4: Community Context Surfacing

**Goal**: Annotate subgraph nodes with community IDs and heuristic labels for architectural context.

#### 4.1 Modify `search/subgraph_extractor.py`

Add community annotation to `extract_subgraph()`:

```python
def _annotate_communities(self, nodes: list[SubgraphNode]) -> dict[int, dict]:
    """Load community map and annotate nodes with community IDs."""
    community_map = self.graph.load_community_map()
    if not community_map:
        return {}

    communities: dict[int, list[str]] = {}
    for node in nodes:
        cid = community_map.get(node.chunk_id)
        if cid is not None:
            node.community_id = cid
            communities.setdefault(cid, []).append(node.chunk_id)

    # Generate heuristic labels
    labels = self._generate_labels(communities)
    return {
        cid: {"label": labels.get(cid, f"cluster_{cid}"), "count": len(members)}
        for cid, members in communities.items()
    }

def _generate_labels(self, communities: dict[int, list[str]]) -> dict[int, str]:
    """Heuristic community labels from most common directory prefix."""
    from collections import Counter
    labels = {}
    for cid, chunk_ids in communities.items():
        dirs = []
        for cid_str in chunk_ids:
            parts = cid_str.replace("\\", "/").split("/")
            if len(parts) > 1:
                dirs.append(parts[-2])
        if dirs:
            labels[cid] = Counter(dirs).most_common(1)[0][0]
    return labels
```

#### 4.2 Testing

**Unit tests** (`tests/unit/search/test_community_surfacing.py`):
- `test_community_annotation` -- mock community map, verify nodes annotated
- `test_community_labels` -- verify directory-based heuristic labels
- `test_empty_community_map` -- verify graceful handling

**Functional validation via MCP**:
- `search_code("relationship extractor", k=5)`
- Verify: subgraph nodes include `community` field, communities dict has labels

---

### Phase 5: Ego-Graph Structure Preservation

**Goal**: When ego_graph is enabled, preserve edge information instead of flattening to list.

#### 5.1 Modify `search/ego_graph_retriever.py`

Add structured retrieval method:

```python
@dataclass
class EgoGraphData:
    anchor: str
    neighbors: list[str]
    edges: list[tuple[str, str, str]]  # (source, target, rel_type)

def retrieve_ego_graph_structured(
    self,
    anchor_chunk_ids: list[str],
    config: EgoGraphConfig,
) -> list[EgoGraphData]:
    """Retrieve ego-graphs WITH edge information preserved."""
    results = []
    for anchor in anchor_chunk_ids:
        neighbors = set()
        edges = []
        # BFS traversal capturing edges
        visited = {anchor}
        frontier = {anchor}
        for hop in range(config.k_hops):
            next_frontier = set()
            for node in frontier:
                # Outgoing edges
                if node in self.graph.graph:
                    for _, target, data in self.graph.graph.out_edges(node, data=True):
                        rel = data.get("type", "calls")
                        if target not in visited:
                            edges.append((node, target, rel))
                            next_frontier.add(target)
                # Incoming edges
                if node in self.graph.graph:
                    for source, _, data in self.graph.graph.in_edges(node, data=True):
                        rel = data.get("type", "calls")
                        if source not in visited:
                            edges.append((source, node, rel))
                            next_frontier.add(source)
            visited.update(next_frontier)
            neighbors.update(next_frontier)
            frontier = next_frontier

        results.append(EgoGraphData(
            anchor=anchor,
            neighbors=list(neighbors)[:config.max_neighbors_per_hop * config.k_hops],
            edges=edges,
        ))
    return results
```

#### 5.2 Integration with SubgraphExtractor

Modify `SubgraphExtractor.extract_subgraph()` to accept optional ego-graph edges:

```python
def extract_subgraph(
    self,
    chunk_ids: list[str],
    ego_graph_data: list[EgoGraphData] | None = None,
    ...
) -> SubgraphResult:
```

Ego-graph neighbor nodes added to subgraph with `is_search_result=False`. Ego-graph edges merged into edge list.

#### 5.3 Testing

**Unit tests** (`tests/unit/search/test_ego_graph_structured.py`):
- `test_structured_retrieval` -- 3 anchors, verify edges preserved with types
- `test_backward_compat` -- `flatten_for_context()` still works
- `test_integration_with_subgraph` -- ego-graph edges appear in SubgraphResult

**Functional validation via MCP**:
- `search_code("graph storage", ego_graph_enabled=True, ego_graph_k_hops=2)`
- Verify: subgraph contains ego-graph neighbor nodes (marked `source: "ego_graph"`) with typed edges

---

## Token Budget Analysis

| Component | Tokens (5 results, compact) | Notes |
|-----------|----------------------------|-------|
| Current output | ~800-1200 | results + routing + system_message |
| Phase 1: subgraph | +400-600 | 5 nodes + ~10 edges |
| Phase 2: full relationships | +50-150 per result | Most functions only have calls; capped at 5/type |
| Phase 3: centrality | +2 per result | Single float field |
| Phase 4: communities | +50 total | community labels section |
| Phase 5: ego-graph edges | +200-400 | Additional neighbor nodes + edges |
| **Total with all phases** | ~1500-2500 | ~60-100% increase for dramatically richer context |

**Ultra/TOON format mitigates**: Tabular encoding reduces subgraph tokens by ~40%.

---

## Backward Compatibility

- `results` array format **unchanged**
- Per-result `graph` field **expanded** (superset of current `{calls, called_by}`)
- New `subgraph` key only appears when graph data exists and has edges
- New `centrality` field per result only when centrality reranking enabled
- All features gated by `GraphEnhancedConfig` with safe defaults
- Existing 1,472 unit + 84 integration tests must pass unchanged

---

## Phase Dependencies

```
Phase 1 (Subgraph Extraction) ✅ COMPLETED ─── foundation for all others
    ├── Phase 2 (Full Relationships) ── independent, low effort
    ├── Phase 3 (Centrality Ranking) ── independent, medium effort
    ├── Phase 4 (Community Context) ── depends on Phase 1 (annotates subgraph nodes)
    └── Phase 5 (Ego-Graph Structure) ── depends on Phase 1 (feeds edges into subgraph)
```

**Recommended order**: 1 ✅ → 2 → 5 → 3 → 4

---

## Critical Files Reference

| File | Role | Phases | Status |
|------|------|--------|--------|
| `search/subgraph_extractor.py` | **CREATED** - Core subgraph extraction (315 lines) | 1, 4, 5 | ✅ Phase 1 |
| `tests/unit/search/test_subgraph_extractor.py` | **CREATED** - Subgraph extraction tests (14 tests) | 1 | ✅ Phase 1 |
| `search/centrality_ranker.py` | **NEW** - PageRank reranking | 3 | Planned |
| `mcp_server/tools/search_handlers.py` | Integration point (lines 748-778: `handle_search_code`) | 1, 2, 3 | ✅ Phase 1 |
| `tests/unit/mcp_server/test_output_formatter.py` | **MODIFIED** - Added 3 subgraph formatting tests | 1 | ✅ Phase 1 |
| `search/config.py` | Configuration (`GraphEnhancedConfig`) | 3 | Planned |
| `search/ego_graph_retriever.py` | Structured ego-graph retrieval | 5 | Planned |
| `graph/graph_storage.py` | Foundation (NetworkX DiGraph access) | All | Production |
| `graph/community_detector.py` | Community label generation | 4 | Production |
| `mcp_server/output_formatter.py` | Token-optimized formatting (no changes needed) | Verify only | ✅ Phase 1 |

---

## Verification Strategy

### Per-Phase Verification

Each phase follows this verification sequence:

1. **Unit tests**: New test file with isolated tests (mock graph, known inputs/outputs)
2. **Existing test regression**: Run full test suite (`pytest tests/unit/ -x`)
3. **Integration tests**: Index real project, run MCP tool, verify output structure
4. **MCP functional test**: Use the tool from Claude Code agent, verify the agent can interpret the new output

### End-to-End Validation (After All Phases)

1. Index `claude-context-local` project
2. Run representative queries:
   - `search_code("graph storage operations")` -- should show subgraph with CALLS, IMPORTS edges
   - `search_code("relationship extractor base class", chunk_type="class")` -- should show INHERITS edges
   - `search_code("error handling patterns", ego_graph_enabled=True)` -- should show ego-graph edges in subgraph
3. Verify token budget: measure response JSON size, confirm < 2500 tokens for 5-result queries
4. Verify backward compat: responses without graph data unchanged

---

## Research References

1. **RepoGraph** (ICLR 2025) - Line-level dependency graphs with ego-graph retrieval. +32% relative improvement on SWE-bench.
2. **LogicLens** (arXiv 2601.10773, Jan 2026) - Three-phase semantic graph construction. Entity nodes as functional bridges. 69.5% high accuracy.
3. **GRACE** - Hierarchical graph fusion with dual-path encoding and graph-aware reranking.
4. **Microsoft GraphRAG** - Community detection for global understanding.
5. **cAST** - AST-based chunking. +4.3 points Recall@5.
6. **JSON Graph Format** - Lightweight interchange for agent consumption.

Local copies:
- `docs/Call_Graph_Implementation/Improving Code RAG with Structural Analysis.md`
- `docs/Call_Graph_Implementation/LogicLens_Leveraging_Semantic_Code_Graph_to_explor.pdf`
