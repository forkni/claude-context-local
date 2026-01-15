"""Unit tests for GraphQueryEngine.find_path() method."""

import tempfile
from pathlib import Path

import pytest

from graph.graph_queries import GraphQueryEngine
from graph.graph_storage import CodeGraphStorage


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def graph_storage(temp_storage):
    """Create a graph storage instance."""
    storage = CodeGraphStorage(project_id="test_project", storage_dir=temp_storage)
    return storage


@pytest.fixture
def query_engine(graph_storage):
    """Create a query engine instance."""
    return GraphQueryEngine(graph_storage)


@pytest.fixture
def simple_chain_graph(graph_storage):
    """Create a simple chain: A -> B -> C."""
    # Add nodes
    graph_storage.add_node(
        "test.py:1-10:function:function_a",
        name="function_a",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )
    graph_storage.add_node(
        "test.py:20-30:function:function_b",
        name="function_b",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )
    graph_storage.add_node(
        "test.py:40-50:function:function_c",
        name="function_c",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )

    # Add edges with relationship type
    graph_storage.graph.add_edge(
        "test.py:1-10:function:function_a",
        "test.py:20-30:function:function_b",
        relationship_type="calls",
        line=5,
    )
    graph_storage.graph.add_edge(
        "test.py:20-30:function:function_b",
        "test.py:40-50:function:function_c",
        relationship_type="calls",
        line=25,
    )

    return graph_storage


@pytest.fixture
def multi_edge_graph(graph_storage):
    """Create a graph with multiple edge types: A -calls-> B -inherits-> C."""
    # Add nodes
    graph_storage.add_node(
        "test.py:1-10:function:function_a",
        name="function_a",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )
    graph_storage.add_node(
        "test.py:20-30:class:ClassB",
        name="ClassB",
        chunk_type="class",
        file_path="test.py",
        language="python",
    )
    graph_storage.add_node(
        "test.py:40-50:class:ClassC",
        name="ClassC",
        chunk_type="class",
        file_path="test.py",
        language="python",
    )

    # Add edges with different relationship types
    graph_storage.graph.add_edge(
        "test.py:1-10:function:function_a",
        "test.py:20-30:class:ClassB",
        relationship_type="calls",
        line=5,
    )
    graph_storage.graph.add_edge(
        "test.py:20-30:class:ClassB",
        "test.py:40-50:class:ClassC",
        relationship_type="inherits",
        line=20,
    )

    return graph_storage


def test_find_path_basic(query_engine, simple_chain_graph):
    """Test basic path finding between two connected nodes."""
    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:40-50:function:function_c",
    )

    assert result is not None
    assert result["path_found"] is True
    assert result["path_length"] == 2
    assert len(result["path"]) == 3

    # Check nodes in path
    assert result["path"][0]["node"]["name"] == "function_a"
    assert result["path"][1]["node"]["name"] == "function_b"
    assert result["path"][2]["node"]["name"] == "function_c"

    # Check edges
    assert result["path"][0]["edge_to_next"]["relationship_type"] == "calls"
    assert result["path"][1]["edge_to_next"]["relationship_type"] == "calls"
    assert result["path"][2]["edge_to_next"] is None

    # Check edge types traversed
    assert "calls" in result["edge_types_traversed"]


def test_find_path_no_path(query_engine, graph_storage):
    """Test when no path exists between nodes."""
    # Add two disconnected nodes
    graph_storage.add_node(
        "test.py:1-10:function:function_a",
        name="function_a",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )
    graph_storage.add_node(
        "test.py:20-30:function:function_b",
        name="function_b",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )

    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:20-30:function:function_b",
    )

    assert result is None


def test_find_path_with_edge_types_filter(query_engine, multi_edge_graph):
    """Test filtering by relationship type."""
    # Path exists with both "calls" and "inherits" edges
    result_no_filter = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:40-50:class:ClassC",
    )
    assert result_no_filter is not None
    assert result_no_filter["path_length"] == 2

    # Filter to only "calls" edges - should fail because ClassB -> ClassC is "inherits"
    result_calls_only = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:40-50:class:ClassC",
        edge_types=["calls"],
    )
    assert result_calls_only is None

    # Filter to both "calls" and "inherits" - should succeed
    result_both = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:40-50:class:ClassC",
        edge_types=["calls", "inherits"],
    )
    assert result_both is not None
    assert result_both["path_length"] == 2


def test_find_path_max_hops_exceeded(query_engine, simple_chain_graph):
    """Test max_hops limit."""
    # Path from A to C is 2 hops
    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:40-50:function:function_c",
        max_hops=1,  # Too short
    )

    assert result is None


def test_find_path_self(query_engine, graph_storage):
    """Test path from node to itself."""
    graph_storage.add_node(
        "test.py:1-10:function:function_a",
        name="function_a",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )

    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:1-10:function:function_a",
    )

    assert result is not None
    assert result["path_found"] is True
    assert result["path_length"] == 0
    assert len(result["path"]) == 1
    assert result["path"][0]["node"]["name"] == "function_a"
    assert result["path"][0]["edge_to_next"] is None


def test_find_path_nonexistent_source(query_engine, simple_chain_graph):
    """Test with nonexistent source node."""
    result = query_engine.find_path(
        source_id="nonexistent.py:1-10:function:foo",
        target_id="test.py:40-50:function:function_c",
    )

    assert result is None


def test_find_path_nonexistent_target(query_engine, simple_chain_graph):
    """Test with nonexistent target node."""
    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="nonexistent.py:1-10:function:foo",
    )

    assert result is None


def test_find_path_direct_connection(query_engine, simple_chain_graph):
    """Test direct connection (1 hop)."""
    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:20-30:function:function_b",
    )

    assert result is not None
    assert result["path_found"] is True
    assert result["path_length"] == 1
    assert len(result["path"]) == 2


def test_find_path_legacy_edge_type(query_engine, graph_storage):
    """Test with legacy 'type' field instead of 'relationship_type'."""
    # Add nodes
    graph_storage.add_node(
        "test.py:1-10:function:function_a",
        name="function_a",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )
    graph_storage.add_node(
        "test.py:20-30:function:function_b",
        name="function_b",
        chunk_type="function",
        file_path="test.py",
        language="python",
    )

    # Add edge with legacy 'type' field
    graph_storage.graph.add_edge(
        "test.py:1-10:function:function_a",
        "test.py:20-30:function:function_b",
        type="calls",  # Legacy field
        line=5,
    )

    # Should work with edge_types filter
    result = query_engine.find_path(
        source_id="test.py:1-10:function:function_a",
        target_id="test.py:20-30:function:function_b",
        edge_types=["calls"],
    )

    assert result is not None
    assert result["path_found"] is True


def test_find_path_multiple_edge_types_traversed(query_engine, graph_storage):
    """Test path that traverses multiple relationship types."""
    # Create path: A -calls-> B -imports-> C -inherits-> D
    nodes = [
        ("test.py:1-10:function:function_a", "function_a", "function"),
        ("test.py:20-30:module:module_b", "module_b", "module"),
        ("test.py:40-50:class:ClassC", "ClassC", "class"),
        ("test.py:60-70:class:ClassD", "ClassD", "class"),
    ]

    for chunk_id, name, chunk_type in nodes:
        graph_storage.add_node(
            chunk_id,
            name=name,
            chunk_type=chunk_type,
            file_path="test.py",
            language="python",
        )

    edges = [
        (nodes[0][0], nodes[1][0], "calls", 5),
        (nodes[1][0], nodes[2][0], "imports", 25),
        (nodes[2][0], nodes[3][0], "inherits", 45),
    ]

    for source, target, rel_type, line in edges:
        graph_storage.graph.add_edge(
            source, target, relationship_type=rel_type, line=line
        )

    result = query_engine.find_path(source_id=nodes[0][0], target_id=nodes[3][0])

    assert result is not None
    assert result["path_length"] == 3
    assert set(result["edge_types_traversed"]) == {"calls", "imports", "inherits"}
