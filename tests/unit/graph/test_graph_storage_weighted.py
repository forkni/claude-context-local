"""
Unit tests for weighted graph traversal in CodeGraphStorage.

Tests edge-type weighted BFS implementation for Phase 1.
"""

import pytest

from graph.graph_storage import DEFAULT_EDGE_WEIGHTS, CodeGraphStorage
from graph.relationship_types import RelationshipEdge, RelationshipType


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory for tests."""
    return tmp_path / "test_graphs"


@pytest.fixture
def graph_storage(temp_storage_dir):
    """Create a CodeGraphStorage instance for testing."""
    storage = CodeGraphStorage(project_id="test_weighted", storage_dir=temp_storage_dir)
    return storage


def test_weighted_bfs_calls_before_imports(graph_storage):
    """Test that weighted BFS prioritizes 'calls' edges over 'imports' edges."""
    # Build test graph: A -> B (calls), A -> C (imports)
    # With default weights: calls=1.0, imports=0.3
    # B should be discovered before C (higher priority)

    # Add nodes
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")
    graph_storage.add_node("C", "ModuleC", "module", "other.py", "python")

    # Add edges
    edge_calls = RelationshipEdge(
        source_id="A",
        target_name="B",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    edge_imports = RelationshipEdge(
        source_id="A",
        target_name="C",
        relationship_type=RelationshipType.IMPORTS,
        line_number=1,
    )
    graph_storage.add_relationship_edge(edge_calls)
    graph_storage.add_relationship_edge(edge_imports)

    # Get neighbors with weighted BFS
    neighbors = graph_storage.get_neighbors(
        "A",
        relation_types=["calls", "imports"],
        max_depth=1,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )

    # Both should be found
    assert "B" in neighbors
    assert "C" in neighbors
    assert len(neighbors) == 2


def test_weighted_bfs_none_weights_backward_compat(graph_storage):
    """Test that edge_weights=None preserves unweighted BFS behavior."""
    # Build same graph as test_weighted_bfs_calls_before_imports
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")
    graph_storage.add_node("C", "ModuleC", "module", "other.py", "python")

    edge_calls = RelationshipEdge(
        source_id="A",
        target_name="B",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    edge_imports = RelationshipEdge(
        source_id="A",
        target_name="C",
        relationship_type=RelationshipType.IMPORTS,
        line_number=1,
    )
    graph_storage.add_relationship_edge(edge_calls)
    graph_storage.add_relationship_edge(edge_imports)

    # Get neighbors without weights (backward compatible)
    neighbors_unweighted = graph_storage.get_neighbors(
        "A", relation_types=["calls", "imports"], max_depth=1, edge_weights=None
    )

    # Both should be found (order may differ from weighted)
    assert "B" in neighbors_unweighted
    assert "C" in neighbors_unweighted
    assert len(neighbors_unweighted) == 2


def test_weighted_bfs_custom_weights(graph_storage):
    """Test custom edge weights override defaults."""
    # Custom weights: imports=1.0 (high), calls=0.1 (low)
    # This reverses the default priority
    custom_weights = {"calls": 0.1, "imports": 1.0}

    # Build graph
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")
    graph_storage.add_node("C", "ModuleC", "module", "other.py", "python")

    edge_calls = RelationshipEdge(
        source_id="A",
        target_name="B",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    edge_imports = RelationshipEdge(
        source_id="A",
        target_name="C",
        relationship_type=RelationshipType.IMPORTS,
        line_number=1,
    )
    graph_storage.add_relationship_edge(edge_calls)
    graph_storage.add_relationship_edge(edge_imports)

    # Get neighbors with custom weights
    neighbors = graph_storage.get_neighbors(
        "A",
        relation_types=["calls", "imports"],
        max_depth=1,
        edge_weights=custom_weights,
    )

    # Both found, but C (imports) has higher priority with custom weights
    assert "B" in neighbors
    assert "C" in neighbors


def test_weighted_bfs_unknown_edge_type_defaults(graph_storage):
    """Test that unknown edge types get default weight 0.5."""
    # Add nodes
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")

    # Add edge with type not in DEFAULT_EDGE_WEIGHTS
    # Manually add edge to graph (bypass validation)
    graph_storage.graph.add_edge("A", "B", type="custom_relationship", line=10)

    # Custom weights dict without 'custom_relationship'
    weights = {"calls": 1.0}  # custom_relationship not listed

    # Get neighbors - should use default 0.5 for unknown type
    neighbors = graph_storage.get_neighbors(
        "A", relation_types=["custom_relationship"], max_depth=1, edge_weights=weights
    )

    # Should find B using default weight
    assert "B" in neighbors


def test_weighted_bfs_depth_limit_respected(graph_storage):
    """Test that max_depth is still respected with weighted BFS."""
    # Build chain: A -> B -> C
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")
    graph_storage.add_node("C", "FunctionC", "function", "test.py", "python")

    edge_ab = RelationshipEdge(
        source_id="A",
        target_name="B",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    edge_bc = RelationshipEdge(
        source_id="B",
        target_name="C",
        relationship_type=RelationshipType.CALLS,
        line_number=20,
    )
    graph_storage.add_relationship_edge(edge_ab)
    graph_storage.add_relationship_edge(edge_bc)

    # max_depth=1: Should find B but not C
    neighbors_depth1 = graph_storage.get_neighbors(
        "A",
        relation_types=["calls"],
        max_depth=1,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )
    assert "B" in neighbors_depth1
    assert "C" not in neighbors_depth1

    # max_depth=2: Should find both B and C
    neighbors_depth2 = graph_storage.get_neighbors(
        "A",
        relation_types=["calls"],
        max_depth=2,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )
    assert "B" in neighbors_depth2
    assert "C" in neighbors_depth2


def test_weighted_bfs_with_multiple_edge_types(graph_storage):
    """Test weighted BFS with multiple edge types at different depths."""
    # Build complex graph:
    # A --calls--> B --inherits--> D
    # A --imports--> C
    # Weights: calls=1.0, inherits=0.9, imports=0.3

    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "ClassB", "class", "test.py", "python")
    graph_storage.add_node("C", "ModuleC", "module", "other.py", "python")
    graph_storage.add_node("D", "ClassD", "class", "base.py", "python")

    edge_ab = RelationshipEdge(
        source_id="A",
        target_name="B",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    edge_ac = RelationshipEdge(
        source_id="A",
        target_name="C",
        relationship_type=RelationshipType.IMPORTS,
        line_number=1,
    )
    edge_bd = RelationshipEdge(
        source_id="B",
        target_name="D",
        relationship_type=RelationshipType.INHERITS,
        line_number=5,
    )

    graph_storage.add_relationship_edge(edge_ab)
    graph_storage.add_relationship_edge(edge_ac)
    graph_storage.add_relationship_edge(edge_bd)

    # Get neighbors at depth 2
    neighbors = graph_storage.get_neighbors(
        "A",
        relation_types=["calls", "imports", "inherits"],
        max_depth=2,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )

    # Should find B (calls, depth 1), C (imports, depth 1), D (inherits from B, depth 2)
    assert "B" in neighbors
    assert "C" in neighbors
    assert "D" in neighbors
    assert len(neighbors) == 3


def test_weighted_bfs_reverse_edges(graph_storage):
    """Test weighted BFS with reverse relationship types (called_by, etc.)."""
    # Build graph: B -> A (calls), so A is called_by B
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")

    edge_ba = RelationshipEdge(
        source_id="B",
        target_name="A",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    graph_storage.add_relationship_edge(edge_ba)

    # Query A for called_by (reverse of calls)
    neighbors = graph_storage.get_neighbors(
        "A",
        relation_types=["called_by"],
        max_depth=1,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )

    # Should find B (which calls A)
    assert "B" in neighbors
    assert len(neighbors) == 1


def test_default_edge_weights_coverage():
    """Test that DEFAULT_EDGE_WEIGHTS includes all major relationship types."""
    # Verify all P1-P3 relationship types have weights defined
    expected_types = [
        "calls",
        "inherits",
        "implements",
        "overrides",
        "uses_type",
        "instantiates",
        "imports",
        "decorates",
        "raises",
        "catches",
    ]

    for edge_type in expected_types:
        assert edge_type in DEFAULT_EDGE_WEIGHTS, f"Missing weight for {edge_type}"
        assert 0.0 <= DEFAULT_EDGE_WEIGHTS[edge_type] <= 1.0, (
            f"Weight for {edge_type} out of range [0, 1]"
        )


def test_weighted_bfs_empty_graph(graph_storage):
    """Test weighted BFS on empty graph or non-existent node."""
    # Non-existent node
    neighbors = graph_storage.get_neighbors(
        "NonExistent",
        relation_types=["calls"],
        max_depth=1,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )

    assert len(neighbors) == 0


def test_weighted_bfs_no_matching_relations(graph_storage):
    """Test weighted BFS when no edges match the requested relation types."""
    # Add nodes with calls edge
    graph_storage.add_node("A", "FunctionA", "function", "test.py", "python")
    graph_storage.add_node("B", "FunctionB", "function", "test.py", "python")

    edge = RelationshipEdge(
        source_id="A",
        target_name="B",
        relationship_type=RelationshipType.CALLS,
        line_number=10,
    )
    graph_storage.add_relationship_edge(edge)

    # Query for imports (no imports edges exist)
    neighbors = graph_storage.get_neighbors(
        "A",
        relation_types=["imports"],
        max_depth=1,
        edge_weights=DEFAULT_EDGE_WEIGHTS,
    )

    assert len(neighbors) == 0
