"""
Unit tests for graph storage.

Tests NetworkX-based graph storage, persistence, and query operations.
"""

import json
import tempfile
from pathlib import Path

import pytest


try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from graph.graph_storage import CodeGraphStorage


@pytest.mark.skipif(not NETWORKX_AVAILABLE, reason="NetworkX not installed")
class TestCodeGraphStorage:
    """Test CodeGraphStorage functionality."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create a temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def graph_storage(self, temp_storage_dir):
        """Create a CodeGraphStorage instance."""
        return CodeGraphStorage(project_id="test_project", storage_dir=temp_storage_dir)

    def test_initialization(self, graph_storage, temp_storage_dir):
        """Test graph storage initialization."""
        assert graph_storage.project_id == "test_project"
        assert graph_storage.storage_dir == temp_storage_dir
        assert isinstance(graph_storage.graph, nx.DiGraph)
        assert len(graph_storage) == 0

    def test_add_node(self, graph_storage):
        """Test adding a node to the graph."""
        graph_storage.add_node(
            chunk_id="test.py:1-10:function:foo",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        assert len(graph_storage) == 1
        assert "test.py:1-10:function:foo" in graph_storage

    def test_add_multiple_nodes(self, graph_storage):
        """Test adding multiple nodes."""
        graph_storage.add_node(
            chunk_id="test.py:1-10:function:foo",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_node(
            chunk_id="test.py:12-20:function:bar",
            name="bar",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        assert len(graph_storage) == 2

    def test_add_call_edge(self, graph_storage):
        """Test adding a call edge."""
        # Add nodes first
        graph_storage.add_node(
            chunk_id="test.py:1-10:function:foo",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        # Add call edge (foo calls bar)
        graph_storage.add_call_edge(
            caller_id="test.py:1-10:function:foo",
            callee_name="bar",
            line_number=5,
            is_method_call=False,
        )

        assert graph_storage.graph.number_of_edges() == 1
        assert graph_storage.graph.has_edge("test.py:1-10:function:foo", "bar")

    def test_get_callers(self, graph_storage):
        """Test getting callers of a function."""
        # Setup: foo calls bar, baz calls bar
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        graph_storage.add_call_edge("baz_id", "bar_id", line_number=2)

        callers = graph_storage.get_callers("bar_id")

        assert len(callers) == 2
        assert "foo_id" in callers
        assert "baz_id" in callers

    def test_get_callers_creates_target_node(self, graph_storage):
        """Test that add_call_edge creates target_name node for callee."""
        # Add call edge without pre-creating callee node
        graph_storage.add_call_edge("foo_id", "bar_func", line_number=1)

        # Verify target_name node was created
        assert "bar_func" in graph_storage
        node_data = graph_storage.get_node_data("bar_func")
        assert node_data is not None
        assert node_data["type"] == "symbol_name"
        assert node_data["is_target_name"] is True
        assert node_data.get("is_call_target") is True

    def test_get_callers_by_symbol_name(self, graph_storage):
        """Test get_callers works with bare symbol name (not full chunk_id)."""
        # Setup: Multiple callers for same method
        graph_storage.add_call_edge(
            "test.py:1-10:function:foo", "embed_chunks", line_number=5
        )
        graph_storage.add_call_edge(
            "test.py:20-30:function:bar", "embed_chunks", line_number=25
        )

        # Query by symbol name should find both callers
        callers = graph_storage.get_callers("embed_chunks")
        assert len(callers) == 2
        assert "test.py:1-10:function:foo" in callers
        assert "test.py:20-30:function:bar" in callers

    def test_add_call_edge_idempotent_node_creation(self, graph_storage):
        """Test that multiple calls don't duplicate target_name node."""
        # Add multiple edges to same callee
        graph_storage.add_call_edge("foo_id", "target_func", line_number=1)
        graph_storage.add_call_edge("bar_id", "target_func", line_number=2)
        graph_storage.add_call_edge("baz_id", "target_func", line_number=3)

        # Should have 4 nodes: 3 callers + 1 target_name
        # (NetworkX creates implicit nodes for callers too)
        assert "target_func" in graph_storage

        # Verify only one target_func node exists
        target_nodes = [n for n in graph_storage.graph.nodes() if n == "target_func"]
        assert len(target_nodes) == 1

    def test_get_callees(self, graph_storage):
        """Test getting callees of a function."""
        # Setup: foo calls bar and baz
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        graph_storage.add_call_edge("foo_id", "baz_id", line_number=2)

        callees = graph_storage.get_callees("foo_id")

        assert len(callees) == 2
        assert "bar_id" in callees
        assert "baz_id" in callees

    def test_get_callers_empty(self, graph_storage):
        """Test getting callers when there are none."""
        callers = graph_storage.get_callers("nonexistent_id")

        assert len(callers) == 0

    def test_get_callees_empty(self, graph_storage):
        """Test getting callees when there are none."""
        callees = graph_storage.get_callees("nonexistent_id")

        assert len(callees) == 0

    def test_get_neighbors_calls_only(self, graph_storage):
        """Test getting neighbors with calls relation only."""
        # Setup: foo -> bar -> baz
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        graph_storage.add_call_edge("bar_id", "baz_id", line_number=2)

        # Get neighbors within 1 hop (calls only)
        neighbors = graph_storage.get_neighbors(
            "foo_id", relation_types=["calls"], max_depth=1
        )

        assert "bar_id" in neighbors
        assert "baz_id" not in neighbors  # 2 hops away

    def test_get_neighbors_both_directions(self, graph_storage):
        """Test getting neighbors in both directions."""
        # Setup: foo -> bar -> baz
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        graph_storage.add_call_edge("bar_id", "baz_id", line_number=2)

        # Get neighbors of bar in both directions
        neighbors = graph_storage.get_neighbors(
            "bar_id", relation_types=["calls", "called_by"], max_depth=1
        )

        assert "foo_id" in neighbors  # Caller
        assert "baz_id" in neighbors  # Callee

    def test_get_neighbors_multi_hop(self, graph_storage):
        """Test multi-hop neighbor discovery."""
        # Setup: foo -> bar -> baz
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        graph_storage.add_call_edge("bar_id", "baz_id", line_number=2)

        # Get neighbors within 2 hops
        neighbors = graph_storage.get_neighbors(
            "foo_id", relation_types=["calls"], max_depth=2
        )

        assert "bar_id" in neighbors  # 1 hop
        assert "baz_id" in neighbors  # 2 hops

    def test_get_node_data(self, graph_storage):
        """Test getting node metadata."""
        graph_storage.add_node(
            chunk_id="test.py:1-10:function:foo",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
            custom_attr="value",
        )

        node_data = graph_storage.get_node_data("test.py:1-10:function:foo")

        assert node_data is not None
        assert node_data["name"] == "foo"
        assert node_data["type"] == "function"
        assert node_data["file"] == "test.py"
        assert node_data["language"] == "python"
        assert node_data["custom_attr"] == "value"

    def test_get_node_data_nonexistent(self, graph_storage):
        """Test getting node data for nonexistent node."""
        node_data = graph_storage.get_node_data("nonexistent_id")

        assert node_data is None

    def test_get_edge_data(self, graph_storage):
        """Test getting edge metadata."""
        graph_storage.add_call_edge(
            caller_id="foo_id",
            callee_name="bar_id",
            line_number=42,
            is_method_call=True,
            custom_attr="value",
        )

        edge_data = graph_storage.get_edge_data("foo_id", "bar_id")

        assert edge_data is not None
        assert edge_data["type"] == "calls"
        assert edge_data["line"] == 42
        assert edge_data["is_method"] is True
        assert edge_data["custom_attr"] == "value"

    def test_get_edge_data_nonexistent(self, graph_storage):
        """Test getting edge data for nonexistent edge."""
        edge_data = graph_storage.get_edge_data("foo_id", "bar_id")

        assert edge_data is None

    def test_save_and_load(self, graph_storage, temp_storage_dir):
        """Test saving and loading graph."""
        # Add some data
        graph_storage.add_node(
            chunk_id="test.py:1-10:function:foo",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_node(
            chunk_id="test.py:12-20:function:bar",
            name="bar",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_call_edge(
            caller_id="test.py:1-10:function:foo",
            callee_name="test.py:12-20:function:bar",
            line_number=5,
        )

        # Save graph
        graph_storage.save()

        # Verify file exists
        assert graph_storage.graph_path.exists()

        # Create new storage instance and load
        new_storage = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )

        assert len(new_storage) == 2
        assert new_storage.graph.number_of_edges() == 1

    def test_load_nonexistent_graph(self, temp_storage_dir):
        """Test loading when graph file doesn't exist."""
        storage = CodeGraphStorage(
            project_id="nonexistent_project", storage_dir=temp_storage_dir
        )

        # Should initialize empty graph without error
        assert len(storage) == 0

    def test_clear(self, graph_storage):
        """Test clearing the graph."""
        # Add some data
        graph_storage.add_node(
            chunk_id="test.py:1-10:function:foo",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)

        assert len(graph_storage) > 0
        assert graph_storage.graph.number_of_edges() > 0

        # Clear graph
        graph_storage.clear()

        assert len(graph_storage) == 0
        assert graph_storage.graph.number_of_edges() == 0

    def test_get_stats(self, graph_storage):
        """Test getting graph statistics."""
        # Add some data
        graph_storage.add_node(
            chunk_id="foo_id",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_node(
            chunk_id="bar_id",
            name="bar",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)

        stats = graph_storage.get_stats()

        assert stats["total_nodes"] == 2
        assert stats["total_edges"] == 1
        assert stats["is_directed"] is True
        assert "storage_path" in stats

    def test_contains_operator(self, graph_storage):
        """Test __contains__ operator."""
        graph_storage.add_node(
            chunk_id="foo_id",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        assert "foo_id" in graph_storage
        assert "nonexistent_id" not in graph_storage

    def test_len_operator(self, graph_storage):
        """Test __len__ operator."""
        assert len(graph_storage) == 0

        graph_storage.add_node(
            chunk_id="foo_id",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        assert len(graph_storage) == 1

    def test_save_load_preserves_directionality(self, graph_storage, temp_storage_dir):
        """Test that save/load preserves directed graph structure."""
        # Setup: foo -> bar (directed edge)
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        graph_storage.save()

        # Load in new instance
        new_storage = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )

        # Verify directionality
        assert new_storage.graph.has_edge("foo_id", "bar_id")
        assert not new_storage.graph.has_edge("bar_id", "foo_id")  # Not bidirectional
        assert isinstance(new_storage.graph, nx.DiGraph)

    def test_json_serialization_format(self, graph_storage):
        """Test that saved JSON has expected format."""
        graph_storage.add_node(
            chunk_id="foo_id",
            name="foo",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)

        graph_storage.save()

        # Read and verify JSON structure
        with open(graph_storage.graph_path) as f:
            data = json.load(f)

        assert "nodes" in data
        assert "edges" in data  # NetworkX 3.6+ uses "edges" for edges
        assert "directed" in data
        assert data["directed"] is True
