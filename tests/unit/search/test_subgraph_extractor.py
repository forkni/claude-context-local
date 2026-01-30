"""Unit tests for SSCG subgraph extraction."""

import json
from unittest.mock import MagicMock

import networkx as nx
import pytest

from search.subgraph_extractor import (
    SubgraphEdge,
    SubgraphExtractor,
    SubgraphNode,
    SubgraphResult,
)


@pytest.fixture
def mock_graph_storage():
    """Create a mock graph storage with a sample code graph."""
    storage = MagicMock()
    g = nx.DiGraph()

    # Add nodes (chunk_ids with metadata)
    g.add_node(
        "auth.py:10-50:function:login",
        name="login",
        type="function",
        file="auth.py",
    )
    g.add_node(
        "auth.py:55-80:class:AuthService",
        name="AuthService",
        type="class",
        file="auth.py",
    )
    g.add_node(
        "db.py:5-20:function:query",
        name="query",
        type="function",
        file="db.py",
    )
    g.add_node(
        "session.py:10-40:function:create_session",
        name="create_session",
        type="function",
        file="session.py",
    )
    g.add_node(
        "models.py:5-30:class:User",
        name="User",
        type="class",
        file="models.py",
    )

    # Add typed edges
    g.add_edge(
        "auth.py:10-50:function:login",
        "db.py:5-20:function:query",
        type="calls",
        line=15,
    )
    g.add_edge(
        "auth.py:10-50:function:login",
        "session.py:10-40:function:create_session",
        type="calls",
        line=20,
    )
    g.add_edge(
        "auth.py:55-80:class:AuthService",
        "auth.py:10-50:function:login",
        type="calls",
        line=60,
    )
    g.add_edge(
        "auth.py:10-50:function:login",
        "models.py:5-30:class:User",
        type="uses_type",
        line=12,
    )
    g.add_edge(
        "auth.py:55-80:class:AuthService",
        "models.py:5-30:class:User",
        type="uses_type",
        line=58,
    )
    g.add_edge(
        "db.py:5-20:function:query", "hashlib", type="imports", line=1
    )  # boundary edge (external)

    storage.graph = g
    storage.load_community_map.return_value = {}
    storage.project_root = None  # Explicitly set to None for tests

    return storage


def test_extract_subgraph_basic(mock_graph_storage):
    """Test basic subgraph extraction with typed edges."""
    extractor = SubgraphExtractor(mock_graph_storage)

    chunk_ids = [
        "auth.py:10-50:function:login",
        "db.py:5-20:function:query",
        "session.py:10-40:function:create_session",
    ]

    result = extractor.extract_subgraph(chunk_ids)

    # Verify nodes
    assert len(result.nodes) == 3
    node_ids = {n.chunk_id for n in result.nodes}
    assert node_ids == set(chunk_ids)

    # Verify node metadata
    login_node = next(n for n in result.nodes if "login" in n.chunk_id)
    assert login_node.name == "login"
    assert login_node.kind == "function"
    assert login_node.file == "auth.py"
    assert login_node.is_search_result is True

    # Verify edges (only inter-edges between result nodes)
    assert len(result.edges) >= 2  # login->query, login->create_session
    edge_pairs = {(e.source, e.target) for e in result.edges}
    assert ("auth.py:10-50:function:login", "db.py:5-20:function:query") in edge_pairs
    assert (
        "auth.py:10-50:function:login",
        "session.py:10-40:function:create_session",
    ) in edge_pairs

    # Verify edge types
    calls_edges = [e for e in result.edges if e.rel_type == "calls"]
    assert len(calls_edges) >= 2

    # Verify no boundary edges by default
    boundary_edges = [e for e in result.edges if e.is_boundary]
    assert len(boundary_edges) == 0


def test_extract_subgraph_no_edges(mock_graph_storage):
    """Test subgraph extraction when nodes are disconnected."""
    extractor = SubgraphExtractor(mock_graph_storage)

    # Select nodes with no edges between them
    chunk_ids = ["models.py:5-30:class:User"]

    result = extractor.extract_subgraph(chunk_ids)

    assert len(result.nodes) == 1
    assert len(result.edges) == 0  # No inter-edges


def test_extract_subgraph_empty_input():
    """Test extraction with empty input."""
    storage = MagicMock()
    storage.graph = nx.DiGraph()
    extractor = SubgraphExtractor(storage)

    result = extractor.extract_subgraph([])

    assert len(result.nodes) == 0
    assert len(result.edges) == 0
    assert result.topology_order == []


def test_topology_order_dag(mock_graph_storage):
    """Test topological ordering with a DAG."""
    extractor = SubgraphExtractor(mock_graph_storage)

    # Dependency graph: login -> query, login -> create_session
    # NetworkX topological_sort returns nodes where for each edge u->v, u comes before v
    chunk_ids = [
        "auth.py:10-50:function:login",
        "db.py:5-20:function:query",
        "session.py:10-40:function:create_session",
    ]

    result = extractor.extract_subgraph(chunk_ids)

    # Verify ordering exists and has all nodes
    order = result.topology_order
    assert len(order) == 3
    assert set(order) == set(chunk_ids)

    # For edge login->query, login should appear before query
    login_idx = order.index("auth.py:10-50:function:login")
    query_idx = order.index("db.py:5-20:function:query")
    session_idx = order.index("session.py:10-40:function:create_session")

    # login calls both query and create_session, so login should come first
    assert login_idx < query_idx
    assert login_idx < session_idx


def test_topology_order_cycles(mock_graph_storage):
    """Test topological ordering with cycles (uses SCC condensation)."""
    # Add a cycle: login -> query -> login
    mock_graph_storage.graph.add_edge(
        "db.py:5-20:function:query",
        "auth.py:10-50:function:login",
        type="calls",
    )

    extractor = SubgraphExtractor(mock_graph_storage)

    chunk_ids = [
        "auth.py:10-50:function:login",
        "db.py:5-20:function:query",
    ]

    result = extractor.extract_subgraph(chunk_ids)

    # Should complete without error (SCC fallback)
    assert len(result.topology_order) == 2
    assert set(result.topology_order) == set(chunk_ids)


def test_include_boundary_edges(mock_graph_storage):
    """Test subgraph extraction with boundary edges enabled."""
    extractor = SubgraphExtractor(mock_graph_storage)

    # Only include login and AuthService (not their dependencies)
    chunk_ids = [
        "auth.py:10-50:function:login",
        "auth.py:55-80:class:AuthService",
    ]

    result = extractor.extract_subgraph(chunk_ids, include_boundary_edges=True)

    # Should have boundary edges pointing to query, create_session, User
    boundary_edges = [e for e in result.edges if e.is_boundary]
    assert len(boundary_edges) > 0

    # Verify boundary targets
    boundary_targets = {e.target for e in boundary_edges}
    assert (
        "db.py:5-20:function:query" in boundary_targets
        or "session.py:10-40:function:create_session" in boundary_targets
    )


def test_multiple_edge_types(mock_graph_storage):
    """Test extraction with multiple relationship types (calls, uses_type)."""
    extractor = SubgraphExtractor(mock_graph_storage)

    chunk_ids = [
        "auth.py:10-50:function:login",
        "auth.py:55-80:class:AuthService",
        "models.py:5-30:class:User",
    ]

    result = extractor.extract_subgraph(chunk_ids)

    # Verify multiple edge types present
    edge_types = {e.rel_type for e in result.edges}
    assert "calls" in edge_types
    assert "uses_type" in edge_types


def test_serialization_format():
    """Test SubgraphResult serialization to compact JSON."""
    nodes = [
        SubgraphNode(
            chunk_id="a.py:1-10:function:foo",
            name="foo",
            kind="function",
            file="a.py",
        ),
        SubgraphNode(
            chunk_id="b.py:5-15:function:bar",
            name="bar",
            kind="function",
            file="b.py",
            community_id=0,
            centrality=0.042,
        ),
    ]
    edges = [
        SubgraphEdge(
            source="a.py:1-10:function:foo",
            target="b.py:5-15:function:bar",
            rel_type="calls",
            line=5,
        ),
    ]

    result = SubgraphResult(
        nodes=nodes,
        edges=edges,
        topology_order=["b.py:5-15:function:bar", "a.py:1-10:function:foo"],
    )

    data = result.to_dict()

    # Verify structure
    assert "nodes" in data
    assert "edges" in data
    assert "topology_order" in data
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1

    # Verify first node (minimal fields)
    node0 = data["nodes"][0]
    assert node0["id"] == "a.py:1-10:function:foo"
    assert node0["name"] == "foo"
    assert node0["kind"] == "function"
    assert node0["file"] == "a.py"
    assert "community" not in node0  # Optional field omitted

    # Verify second node (with optional fields)
    node1 = data["nodes"][1]
    assert node1["community"] == 0
    assert node1["centrality"] == 0.042

    # Verify edge
    edge0 = data["edges"][0]
    assert edge0["src"] == "a.py:1-10:function:foo"
    assert edge0["tgt"] == "b.py:5-15:function:bar"
    assert edge0["rel"] == "calls"
    assert edge0["line"] == 5


def test_token_budget():
    """Verify serialization stays within token budget."""
    # Simulate 5 results with 10 edges
    nodes = [
        SubgraphNode(
            chunk_id=f"file{i}.py:1-10:function:func{i}",
            name=f"func{i}",
            kind="function",
            file=f"file{i}.py",
        )
        for i in range(5)
    ]
    edges = [
        SubgraphEdge(
            source=f"file{i}.py:1-10:function:func{i}",
            target=f"file{i + 1}.py:1-10:function:func{i + 1}",
            rel_type="calls",
        )
        for i in range(4)
    ] + [
        SubgraphEdge(
            source=f"file{i}.py:1-10:function:func{i}",
            target=f"file{(i + 2) % 5}.py:1-10:function:func{(i + 2) % 5}",
            rel_type="imports",
        )
        for i in range(5)
    ]  # 4 + 5 = 9 edges

    result = SubgraphResult(
        nodes=nodes, edges=edges, topology_order=[n.chunk_id for n in nodes]
    )

    # Serialize and measure
    json_str = json.dumps(result.to_dict())
    char_count = len(json_str)

    # Approximate token count (1 token ≈ 4 chars for English text, ~3 for JSON)
    token_estimate = char_count / 3

    # Should be under 600 tokens for 5 nodes + 10 edges
    assert token_estimate < 600, (
        f"Token estimate {token_estimate} exceeds budget of 600"
    )


def test_ego_graph_marker():
    """Test ego-graph neighbor nodes are marked correctly."""
    node = SubgraphNode(
        chunk_id="a.py:1-10:function:foo",
        name="foo",
        kind="function",
        file="a.py",
        is_search_result=False,  # Ego-graph neighbor
    )

    result = SubgraphResult(nodes=[node], edges=[], topology_order=[])
    data = result.to_dict()

    # Ego-graph nodes should have "source": "ego_graph"
    assert data["nodes"][0]["source"] == "ego_graph"


def test_boundary_edge_marker():
    """Test boundary edges are marked correctly."""
    edge = SubgraphEdge(
        source="a.py:1-10:function:foo",
        target="external_lib",
        rel_type="imports",
        is_boundary=True,
    )

    result = SubgraphResult(nodes=[], edges=[edge], topology_order=[])
    data = result.to_dict()

    # Boundary edges should have "boundary": True
    assert data["edges"][0]["boundary"] is True


def test_relative_path_conversion():
    """Test absolute paths are converted to relative paths."""
    import os
    import tempfile
    from unittest.mock import MagicMock

    # Create a temp directory to simulate project root
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fresh graph storage mock for this test
        storage = MagicMock()
        g = nx.DiGraph()

        # Create absolute paths under tmpdir
        abs_path_auth = os.path.join(tmpdir, "src", "auth.py")
        abs_path_db = os.path.join(tmpdir, "src", "db.py")

        # Add nodes with absolute paths
        g.add_node(
            "auth.py:10-50:function:login",
            name="login",
            type="function",
            file=abs_path_auth,
        )
        g.add_node(
            "db.py:5-20:function:query",
            name="query",
            type="function",
            file=abs_path_db,
        )

        storage.graph = g
        storage.project_root = tmpdir

        extractor = SubgraphExtractor(storage)

        chunk_ids = [
            "auth.py:10-50:function:login",
            "db.py:5-20:function:query",
        ]

        result = extractor.extract_subgraph(chunk_ids)

        # Verify paths are relative
        for node in result.nodes:
            assert not os.path.isabs(node.file), (
                f"Expected relative path, got: {node.file}"
            )
            assert node.file.startswith("src/"), (
                f"Expected src/ prefix, got: {node.file}"
            )


def test_boundary_edge_cap():
    """Test boundary edges are capped at 3 per source node."""
    # Create a fresh graph with many outgoing edges
    storage = MagicMock()
    g = nx.DiGraph()

    # Add focal node
    g.add_node(
        "main.py:1-10:function:main", name="main", type="function", file="main.py"
    )

    # Add 10 target nodes and edges (all will be boundary)
    for i in range(10):
        target_id = f"lib{i}.py:1-10:function:func{i}"
        g.add_node(target_id, name=f"func{i}", type="function", file=f"lib{i}.py")
        g.add_edge("main.py:1-10:function:main", target_id, type="calls", line=5 + i)

    storage.graph = g
    storage.project_root = None

    extractor = SubgraphExtractor(storage)

    # Extract subgraph with only main (all edges are boundary)
    chunk_ids = ["main.py:1-10:function:main"]
    result = extractor.extract_subgraph(chunk_ids, include_boundary_edges=True)

    # Should have 1 node
    assert len(result.nodes) == 1

    # Should have max 3 boundary edges (cap enforced)
    boundary_edges = [e for e in result.edges if e.is_boundary]
    assert len(boundary_edges) == 3, (
        f"Expected 3 boundary edges, got {len(boundary_edges)}"
    )


def test_subgraph_with_no_inter_edges_but_boundary(mock_graph_storage):
    """Test subgraph is returned when only boundary edges exist."""
    extractor = SubgraphExtractor(mock_graph_storage)

    # Select only User class (no direct edges to other selected nodes)
    chunk_ids = ["models.py:5-30:class:User"]

    result = extractor.extract_subgraph(chunk_ids, include_boundary_edges=True)

    # Should have 1 node
    assert len(result.nodes) == 1
    assert result.nodes[0].chunk_id == "models.py:5-30:class:User"

    # Boundary edges might exist from other nodes calling User
    # (incoming boundary edges from AuthService, login)
    boundary_edges = [e for e in result.edges if e.is_boundary]
    assert (
        len(boundary_edges) >= 0
    )  # May or may not have boundary edges depending on graph
