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
        assert isinstance(graph_storage.graph, nx.MultiDiGraph)
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

    def test_clear_persists_to_disk(
        self, graph_storage: CodeGraphStorage, temp_storage_dir: Path
    ) -> None:
        """clear() must remove the backing JSON so re-initialization starts empty.

        Regression test for the phantom-node bug: without deleting the JSON file,
        a new CodeGraphStorage over the same directory would reload stale phantom
        nodes (e.g. deleted methods) that survived a full re-index.
        """
        # Arrange: add a node and persist it to disk
        graph_storage.add_node(
            chunk_id="test_file.py:1-10:function:my_func",
            name="my_func",
            chunk_type="function",
            file_path="test_file.py",
        )
        graph_storage.save()
        assert graph_storage.graph_path.exists(), "JSON file must exist after save()"

        # Act: clear (must delete the backing file)
        graph_storage.clear()

        # Assert: file is gone from disk
        assert not graph_storage.graph_path.exists(), (
            "clear() must delete the backing JSON file"
        )

        # Assert: fresh instance over the same directory starts empty (no phantom reload)
        fresh = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )
        assert len(fresh) == 0, "Fresh instance after clear() must have 0 nodes"
        assert fresh.graph.number_of_edges() == 0

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
        assert isinstance(new_storage.graph, nx.MultiDiGraph)

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
        assert data.get("multigraph") is True, (
            "Saved JSON must mark graph as multigraph"
        )
        assert data.get("graph", {}).get("schema_version") == 2, (
            "Saved JSON must carry schema_version=2"
        )

    # ------------------------------------------------------------------
    # Fix 3: remove_file_nodes — graph prune on incremental reindex
    # ------------------------------------------------------------------

    def test_remove_file_nodes_removes_matching_nodes(self, graph_storage):
        """Nodes whose chunk_id starts with 'file_path:' are removed."""
        graph_storage.add_node(
            "src/auth.py:10-20:method:Auth.login", "login", "method", "src/auth.py"
        )
        graph_storage.add_node(
            "src/auth.py:30-40:function:hash_pw", "hash_pw", "function", "src/auth.py"
        )
        graph_storage.add_node(
            "src/utils.py:1-10:function:helper", "helper", "function", "src/utils.py"
        )

        removed = graph_storage.remove_file_nodes("src/auth.py")

        assert removed == 2
        assert len(graph_storage) == 1
        assert "src/utils.py:1-10:function:helper" in graph_storage

    def test_remove_file_nodes_cleans_name_index(self, graph_storage):
        """_name_index entries for removed nodes are pruned."""
        graph_storage.add_node(
            "src/auth.py:10-20:method:Auth.login", "login", "method", "src/auth.py"
        )
        graph_storage.add_node(
            "src/utils.py:5-10:function:login", "login", "function", "src/utils.py"
        )

        # Both nodes share name "login"
        assert "login" in graph_storage._name_index
        assert len(graph_storage._name_index["login"]) == 2

        graph_storage.remove_file_nodes("src/auth.py")

        # "login" entry for auth.py removed; utils.py entry remains
        assert "login" in graph_storage._name_index
        assert len(graph_storage._name_index["login"]) == 1

    def test_remove_file_nodes_removes_empty_name_index_key(self, graph_storage):
        """When the last node for a name is removed, the name key is deleted."""
        graph_storage.add_node(
            "src/auth.py:10-20:method:Auth.login", "login", "method", "src/auth.py"
        )

        graph_storage.remove_file_nodes("src/auth.py")

        assert "login" not in graph_storage._name_index
        assert len(graph_storage) == 0

    def test_remove_file_nodes_removes_incident_edges(self, graph_storage):
        """Edges to/from removed nodes are also removed."""
        graph_storage.add_node(
            "src/auth.py:10-20:function:do_auth", "do_auth", "function", "src/auth.py"
        )
        graph_storage.add_node(
            "src/main.py:1-5:function:main", "main", "function", "src/main.py"
        )
        graph_storage.add_call_edge(
            "src/main.py:1-5:function:main", "do_auth", line_number=3
        )

        # Resolve call edge so there's a real edge
        graph_storage.add_node(
            "src/auth.py:10-20:function:do_auth", "do_auth", "function", "src/auth.py"
        )
        graph_storage.graph.add_edge(
            "src/main.py:1-5:function:main", "src/auth.py:10-20:function:do_auth"
        )

        removed = graph_storage.remove_file_nodes("src/auth.py")

        assert removed >= 1
        assert "src/auth.py:10-20:function:do_auth" not in graph_storage
        # Caller node still present
        assert "src/main.py:1-5:function:main" in graph_storage

    def test_remove_file_nodes_normalizes_windows_path(self, graph_storage):
        """Backslash-separated paths are normalized and match forward-slash chunk_ids."""
        graph_storage.add_node(
            "src/auth.py:10-20:function:fn", "fn", "function", "src/auth.py"
        )

        removed = graph_storage.remove_file_nodes("src\\auth.py")  # Windows-style

        assert removed == 1
        assert len(graph_storage) == 0

    def test_remove_file_nodes_no_match_returns_zero(self, graph_storage):
        """Returns 0 when no nodes match the given file path."""
        graph_storage.add_node(
            "src/other.py:1-10:function:foo", "foo", "function", "src/other.py"
        )

        removed = graph_storage.remove_file_nodes("src/auth.py")

        assert removed == 0
        assert len(graph_storage) == 1

    def test_remove_file_nodes_does_not_remove_prefix_siblings(self, graph_storage):
        """'src/auth.py' must not remove nodes from 'src/auth_utils.py'."""
        graph_storage.add_node(
            "src/auth.py:1-5:function:a", "a", "function", "src/auth.py"
        )
        graph_storage.add_node(
            "src/auth_utils.py:1-5:function:b", "b", "function", "src/auth_utils.py"
        )

        removed = graph_storage.remove_file_nodes("src/auth.py")

        assert removed == 1
        assert "src/auth_utils.py:1-5:function:b" in graph_storage

    # ------------------------------------------------------------------
    # Workstream D: prune_orphan_symbol_nodes
    # ------------------------------------------------------------------

    def test_prune_orphan_symbol_nodes_removes_degree_zero_phantom(self, graph_storage):
        """A phantom (symbol_name/is_target_name) node with no incident
        edges left is removed. remove_file_nodes cannot reach it directly
        (no path: prefix), so it is only reachable once its last referent
        is gone and its degree drops to 0."""
        graph_storage.add_node(
            "src/main.py:1-5:function:main", "main", "function", "src/main.py"
        )
        graph_storage.add_call_edge(
            "src/main.py:1-5:function:main", "helper_func", line_number=3
        )
        assert "helper_func" in graph_storage

        # Removing the only caller drops helper_func's incident edges too,
        # leaving it at degree 0.
        graph_storage.remove_file_nodes("src/main.py")
        assert graph_storage.graph.degree("helper_func") == 0

        pruned = graph_storage.prune_orphan_symbol_nodes()

        assert pruned == 1
        assert "helper_func" not in graph_storage

    def test_prune_orphan_symbol_nodes_keeps_phantom_at_degree_one(self, graph_storage):
        """A phantom shared by two files is NOT pruned while it still has
        one referent (degree 1); it is pruned once both are gone."""
        graph_storage.add_node("src/a.py:1-5:function:a", "a", "function", "src/a.py")
        graph_storage.add_node("src/b.py:1-5:function:b", "b", "function", "src/b.py")
        graph_storage.add_call_edge(
            "src/a.py:1-5:function:a", "shared_func", line_number=1
        )
        graph_storage.add_call_edge(
            "src/b.py:1-5:function:b", "shared_func", line_number=1
        )

        graph_storage.remove_file_nodes("src/a.py")
        assert graph_storage.graph.degree("shared_func") == 1

        pruned = graph_storage.prune_orphan_symbol_nodes()
        assert pruned == 0
        assert "shared_func" in graph_storage

        graph_storage.remove_file_nodes("src/b.py")
        assert graph_storage.graph.degree("shared_func") == 0

        pruned = graph_storage.prune_orphan_symbol_nodes()
        assert pruned == 1
        assert "shared_func" not in graph_storage

    def test_prune_orphan_symbol_nodes_never_removes_real_chunk_at_degree_zero(
        self, graph_storage
    ):
        """A real chunk node (no symbol_name type, no is_target_name flag)
        with degree 0 -- e.g. a leaf function with no callers/callees --
        must never be pruned; it fails the type/flag half of the predicate."""
        graph_storage.add_node(
            "src/leaf.py:1-5:function:leaf", "leaf", "function", "src/leaf.py"
        )
        assert graph_storage.graph.degree("src/leaf.py:1-5:function:leaf") == 0

        pruned = graph_storage.prune_orphan_symbol_nodes()

        assert pruned == 0
        assert "src/leaf.py:1-5:function:leaf" in graph_storage

    def test_prune_orphan_symbol_nodes_leaves_unrelated_name_index_entries_intact(
        self, graph_storage
    ):
        """On the in-memory add path, phantoms created via add_call_edge are
        never added to _name_index -- only add_node populates it (see
        get_nodes_by_name's docstring). So the _name_index cleanup in
        prune_orphan_symbol_nodes is a no-op HERE specifically because this
        test never persists and reloads the graph.

        That is NOT true in general: CodeGraphStorage.load() rebuilds
        _name_index from every node carrying a `name` attribute, and phantoms
        do carry NODE_ATTR_NAME -- so on any persisted-then-reloaded index
        (every real one) phantoms ARE in _name_index and this cleanup is
        load-bearing, not defensive. See
        test_prune_orphan_symbol_nodes_cleans_name_index_after_reload below
        for that branch.
        """
        graph_storage.add_node(
            "src/main.py:1-5:function:main", "main", "function", "src/main.py"
        )
        graph_storage.add_node(
            "src/other.py:1-5:function:bystander",
            "bystander",
            "function",
            "src/other.py",
        )
        graph_storage.add_call_edge(
            "src/main.py:1-5:function:main", "helper_func", line_number=3
        )
        assert "helper_func" not in graph_storage._name_index
        graph_storage.remove_file_nodes("src/main.py")

        graph_storage.prune_orphan_symbol_nodes()

        assert "bystander" in graph_storage._name_index
        assert "helper_func" not in graph_storage._name_index

    def test_prune_orphan_symbol_nodes_cleans_name_index_after_reload(
        self, graph_storage, temp_storage_dir
    ):
        """The branch test_..._leaves_unrelated_name_index_entries_intact
        above doesn't cover: after save()/reload, the phantom genuinely is in
        _name_index (CodeGraphStorage.load() rebuilds it from every node
        carrying NODE_ATTR_NAME, which phantoms do), so the cleanup inside
        prune_orphan_symbol_nodes actually does work here, not just
        defensively."""
        graph_storage.add_node(
            "src/main.py:1-5:function:main", "main", "function", "src/main.py"
        )
        graph_storage.add_node(
            "src/other.py:1-5:function:bystander",
            "bystander",
            "function",
            "src/other.py",
        )
        graph_storage.add_call_edge(
            "src/main.py:1-5:function:main", "helper_func", line_number=3
        )
        graph_storage.remove_file_nodes("src/main.py")
        assert graph_storage.graph.degree("helper_func") == 0
        graph_storage.save()

        reloaded = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )
        # Confirms the premise: after a reload, the phantom really is in
        # _name_index -- the opposite of the in-memory-only case above.
        assert "helper_func" in reloaded._name_index
        assert "bystander" in reloaded._name_index

        pruned = reloaded.prune_orphan_symbol_nodes()

        assert pruned == 1
        assert "helper_func" not in reloaded._name_index
        assert "bystander" in reloaded._name_index

    def test_prune_orphan_symbol_nodes_no_match_returns_zero(self, graph_storage):
        """No orphan candidates → returns 0."""
        graph_storage.add_node(
            "src/leaf.py:1-5:function:leaf", "leaf", "function", "src/leaf.py"
        )
        assert graph_storage.prune_orphan_symbol_nodes() == 0

    def test_prune_orphan_symbol_nodes_bumps_version_when_removed(self, graph_storage):
        graph_storage.add_node(
            "src/main.py:1-5:function:main", "main", "function", "src/main.py"
        )
        graph_storage.add_call_edge(
            "src/main.py:1-5:function:main", "helper_func", line_number=3
        )
        graph_storage.remove_file_nodes("src/main.py")
        before = graph_storage.version

        pruned = graph_storage.prune_orphan_symbol_nodes()

        assert pruned == 1
        assert graph_storage.version > before

    def test_prune_orphan_symbol_nodes_does_not_bump_version_when_nothing_removed(
        self, graph_storage
    ):
        before = graph_storage.version
        pruned = graph_storage.prune_orphan_symbol_nodes()
        assert pruned == 0
        assert graph_storage.version == before

    # ------------------------------------------------------------------
    # Regression: resolver_source must survive save/load round-trip
    # ------------------------------------------------------------------

    def test_resolver_source_survives_save_load_round_trip(
        self, graph_storage: "CodeGraphStorage", temp_storage_dir: Path
    ) -> None:
        """``resolver_source`` edge attr must survive a node-link JSON round-trip.

        NetworkX's node-link format reserves the keys ``"source"`` and ``"target"``
        for edge endpoints.  Any edge attribute named ``"source"`` is silently
        destroyed on save/load.  We use ``"resolver_source"`` instead — this test
        guards against regression to the broken ``"source"`` key name.
        """
        caller = "src/a.py:1-5:function:caller"
        callee = "src/b.py:1-5:function:callee"
        graph_storage.add_node(caller, "caller", "function", "src/a.py")
        graph_storage.add_node(callee, "callee", "function", "src/b.py")

        graph_storage.add_call_edge(
            caller,
            callee,
            line_number=3,
            is_method_call=False,
            is_resolved=True,
            resolver_source="pyan",
            resolver_confidence=0.75,
        )

        graph_storage.save()

        reloaded = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )

        assert reloaded.graph.has_edge(caller, callee), "Edge must survive round-trip"
        edge_data = reloaded.graph.edges[caller, callee, "calls"]
        assert edge_data.get("resolver_source") == "pyan", (
            "resolver_source must survive node-link JSON round-trip; "
            "if this fails the edge attr was accidentally named 'source' (reserved key)"
        )
        assert edge_data.get("resolver_confidence") == 0.75

    def test_source_key_not_used_as_edge_attr(
        self, graph_storage: "CodeGraphStorage"
    ) -> None:
        """Guard: add_call_edge must not write a graph edge attr named 'source'.

        NetworkX node-link serialization reserves 'source' / 'target' for endpoint
        keys.  This test ensures no code path passes ``source=...`` as an edge kwarg,
        which would be silently discarded on the first save/load cycle.
        """
        caller = "src/x.py:1-5:function:x"
        callee = "src/y.py:1-5:function:y"
        graph_storage.add_node(caller, "x", "function", "src/x.py")
        graph_storage.add_node(callee, "y", "function", "src/y.py")

        # Simulate what the injection seam does with resolver_source (correct key)
        graph_storage.add_call_edge(
            caller,
            callee,
            line_number=1,
            resolver_source="libcst",
            resolver_confidence=0.90,
        )

        edge_data = graph_storage.graph.edges[caller, callee, "calls"]
        # 'source' must NOT appear as an edge attribute (it would collide with the
        # node-link endpoint key and be lost on save/load)
        assert "source" not in edge_data, (
            "Edge attr 'source' would be destroyed by node-link save/load. "
            "Use 'resolver_source' instead."
        )
        assert edge_data.get("resolver_source") == "libcst"

    # ------------------------------------------------------------------
    # Regression: legacy string confidence tags must survive get_edge_data
    # ------------------------------------------------------------------

    def _add_relationship_edge(self, gs: "CodeGraphStorage", confidence_value) -> None:
        """Helper: add a synthetic calls edge with the given confidence via the graph API."""
        # Directly inject edge attrs so the test doesn't depend on the full
        # RelationshipEdge path, which requires more fixture setup.
        gs.graph.add_edge(
            "src/caller.py:1-5:function:caller",
            "src/callee.py:1-5:function:callee",
            type="calls",
            line=2,
            confidence=confidence_value,
        )

    def test_get_edge_data_preserves_ambiguous_confidence_tag(
        self, graph_storage: "CodeGraphStorage"
    ) -> None:
        """get_edge_data must not warn or clobber legacy string 'ambiguous'."""
        caller = "src/caller.py:1-5:function:caller"
        callee = "src/callee.py:1-5:function:callee"
        graph_storage.add_node(caller, "caller", "function", "src/caller.py")
        graph_storage.add_node(callee, "callee", "function", "src/callee.py")
        self._add_relationship_edge(graph_storage, "ambiguous")

        edge_data = graph_storage.get_edge_data(caller, callee)
        assert edge_data is not None
        assert edge_data["confidence"] == "ambiguous", (
            "get_edge_data must pass legacy 'ambiguous' string through unchanged; "
            "it must not coerce it to float or emit a warning"
        )

    def test_get_edge_data_preserves_exact_confidence_tag(
        self, graph_storage: "CodeGraphStorage"
    ) -> None:
        """get_edge_data must not warn or clobber legacy string 'exact'."""
        caller = "src/caller.py:1-5:function:caller"
        callee = "src/callee.py:1-5:function:callee"
        graph_storage.add_node(caller, "caller", "function", "src/caller.py")
        graph_storage.add_node(callee, "callee", "function", "src/callee.py")
        self._add_relationship_edge(graph_storage, "exact")

        edge_data = graph_storage.get_edge_data(caller, callee)
        assert edge_data is not None
        assert edge_data["confidence"] == "exact", (
            "get_edge_data must pass legacy 'exact' string through unchanged"
        )

    def test_get_edge_data_warns_on_genuinely_invalid_confidence(
        self, graph_storage: "CodeGraphStorage"
    ) -> None:
        """get_edge_data must still warn + default for non-string, non-float values."""
        caller = "src/caller.py:1-5:function:caller"
        callee = "src/callee.py:1-5:function:callee"
        graph_storage.add_node(caller, "caller", "function", "src/caller.py")
        graph_storage.add_node(callee, "callee", "function", "src/callee.py")
        # Use an object() — not a known string tag, not a float-convertible value
        self._add_relationship_edge(graph_storage, object())

        edge_data = graph_storage.get_edge_data(caller, callee)
        assert edge_data is not None
        # Existing fallback: invalid value → defaulted to 1.0
        assert edge_data["confidence"] == 1.0, (
            "Genuinely invalid confidence (non-string non-numeric) must default to 1.0"
        )

    # ------------------------------------------------------------------
    # MultiDiGraph — parallel edge correctness (#3)
    # ------------------------------------------------------------------

    def test_parallel_edge_types_survive_save_load(
        self, graph_storage, temp_storage_dir
    ):
        """Two relationship types on the same (u, v) pair must both survive a save/load round-trip."""
        u = "src/a.py:1-5:function:foo"
        v = "src/b.py:1-5:function:bar"
        graph_storage.add_node(u, "foo", "function", "src/a.py")
        graph_storage.add_node(v, "bar", "function", "src/b.py")

        # First edge via the public API (key="calls")
        graph_storage.add_call_edge(u, v, line_number=3)
        # Second edge injected directly with a different key
        graph_storage.graph.add_edge(
            u, v, key="imports", type="imports", line=1, confidence=1.0
        )

        graph_storage.save()

        reloaded = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )
        assert isinstance(reloaded.graph, nx.MultiDiGraph)
        all_edges = reloaded.graph.get_edge_data(u, v)
        assert all_edges is not None, "Edge (u, v) must exist after reload"
        assert "calls" in all_edges, "calls edge must survive round-trip"
        assert "imports" in all_edges, "imports edge must survive round-trip"

    def test_get_edge_data_relationship_type_filter(self, graph_storage):
        """get_edge_data(u, v, relationship_type=...) must return the specific edge, not the primary."""
        u = "src/a.py:1-5:function:foo"
        v = "src/b.py:1-5:function:bar"
        graph_storage.add_node(u, "foo", "function", "src/a.py")
        graph_storage.add_node(v, "bar", "function", "src/b.py")

        graph_storage.add_call_edge(u, v, line_number=3, resolver_confidence=0.8)
        graph_storage.graph.add_edge(
            u, v, key="imports", type="imports", line=1, confidence=1.0
        )

        calls_data = graph_storage.get_edge_data(u, v, relationship_type="calls")
        assert calls_data is not None
        assert calls_data.get("resolver_confidence") == 0.8

        imports_data = graph_storage.get_edge_data(u, v, relationship_type="imports")
        assert imports_data is not None
        assert imports_data.get("relationship_type") == "imports"

        # Missing key must return None
        assert graph_storage.get_edge_data(u, v, relationship_type="inherits") is None

    def test_get_all_edge_data_returns_every_parallel_edge(self, graph_storage):
        """get_all_edge_data(u, v) must return every parallel edge, not just the primary.

        Consumed by GraphQueryEngine._traverse_outbound/_traverse_inbound to
        populate RelationshipEntry.parallel_edges (the parallel-edge-collapse
        fix, ADR-0027) -- this was previously an orphaned zero-caller method.
        """
        u = "src/a.py:1-5:function:foo"
        v = "src/b.py:1-5:function:bar"
        graph_storage.add_node(u, "foo", "function", "src/a.py")
        graph_storage.add_node(v, "bar", "function", "src/b.py")

        graph_storage.add_call_edge(u, v, line_number=3, resolver_confidence=0.8)
        graph_storage.graph.add_edge(
            u, v, key="imports", type="imports", line=1, confidence=1.0
        )

        all_edges = graph_storage.get_all_edge_data(u, v)

        assert len(all_edges) == 2
        types = {d["relationship_type"] for d in all_edges}
        assert types == {"calls", "imports"}
        # Each dict must be independently normalized, matching get_edge_data's output.
        calls_entry = next(d for d in all_edges if d["relationship_type"] == "calls")
        assert calls_entry.get("resolver_confidence") == 0.8

    def test_get_all_edge_data_no_edge_returns_empty_list(self, graph_storage):
        """get_all_edge_data(u, v) must return [] (not None) when no edge exists."""
        u = "src/a.py:1-5:function:foo"
        v = "src/b.py:1-5:function:bar"
        graph_storage.add_node(u, "foo", "function", "src/a.py")
        graph_storage.add_node(v, "bar", "function", "src/b.py")

        assert graph_storage.get_all_edge_data(u, v) == []

    def test_coerce_on_load_upgrades_old_digraph_json(self, temp_storage_dir):
        """Loading an old DiGraph-format (no 'multigraph' key) must yield a MultiDiGraph."""
        import networkx as nx
        from networkx.readwrite import node_link_data

        # Build a plain DiGraph and write it as a node-link JSON (no multigraph key)
        dg = nx.DiGraph()
        dg.add_node("src/x.py:1-5:function:x", name="x", type="function")
        dg.add_edge(
            "src/x.py:1-5:function:x",
            "src/y.py:1-5:function:y",
            type="calls",
            line=1,
            confidence=1.0,
        )
        legacy_data = node_link_data(dg)
        # Sanity: node_link_data for DiGraph must not have multigraph=True
        assert not legacy_data.get("multigraph", False)

        storage = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )
        graph_path = storage.graph_path
        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        # Load a fresh instance — coerce-on-load must upgrade to MultiDiGraph
        reloaded = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )
        assert isinstance(reloaded.graph, nx.MultiDiGraph), (
            "Old DiGraph JSON must be coerced to MultiDiGraph on load"
        )
        assert reloaded.graph.number_of_nodes() >= 1

    # ------------------------------------------------------------------
    # P3-3 (search-latency plan): version counter + centrality memo
    # ------------------------------------------------------------------

    def test_init_bumps_version(self, graph_storage):
        """A freshly-constructed storage already has a version (not the -1 sentinel)."""
        assert graph_storage.version == 0

    def test_add_node_bumps_version(self, graph_storage):
        before = graph_storage.version
        graph_storage.add_node("a.py:1-5:function:a", "a", "function", "a.py")
        assert graph_storage.version > before

    def test_add_call_edge_bumps_version(self, graph_storage):
        before = graph_storage.version
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        assert graph_storage.version > before

    def test_upgrade_call_edge_bumps_version(self, graph_storage):
        """upgrade_call_edge mutates edge attrs in place — no node/edge count change,
        so a count-keyed cache (the design this replaces) would miss this entirely."""
        graph_storage.add_call_edge("foo_id", "bar_id", line_number=1)
        before = graph_storage.version
        graph_storage.upgrade_call_edge("foo_id", "bar_id", resolver_source="pyan")
        assert graph_storage.version > before

    def test_add_relationship_edge_bumps_version(self, graph_storage):
        from chunking.relationships.relationship_types import (
            RelationshipEdge,
            RelationshipType,
        )

        before = graph_storage.version
        edge = RelationshipEdge(
            source_id="child.py:1-10:class:Child",
            target_name="Parent",
            relationship_type=RelationshipType.INHERITS,
            line_number=1,
        )
        graph_storage.add_relationship_edge(edge)
        assert graph_storage.version > before

    def test_load_bumps_version(self, graph_storage, temp_storage_dir):
        graph_storage.add_node("a.py:1-5:function:a", "a", "function", "a.py")
        graph_storage.save()

        storage = CodeGraphStorage(
            project_id="test_project", storage_dir=temp_storage_dir
        )
        before = storage.version
        storage.load()
        assert storage.version > before

    def test_load_missing_file_returns_false_without_bumping(
        self, graph_storage, temp_storage_dir
    ):
        """load()'s early return (file doesn't exist) takes no action on self.graph,
        so — unlike the try/except branches below it — it must not bump the version."""
        storage = CodeGraphStorage(
            project_id="nonexistent_project", storage_dir=temp_storage_dir
        )
        before = storage.version
        assert storage.load() is False
        assert storage.version == before

    def test_clear_bumps_version(self, graph_storage):
        graph_storage.add_node("a.py:1-5:function:a", "a", "function", "a.py")
        before = graph_storage.version
        graph_storage.clear()
        assert graph_storage.version > before

    def test_remove_file_nodes_bumps_version_when_nodes_removed(self, graph_storage):
        graph_storage.add_node("a.py:1-5:function:a", "a", "function", "a.py")
        before = graph_storage.version
        removed = graph_storage.remove_file_nodes("a.py")
        assert removed == 1
        assert graph_storage.version > before

    def test_remove_file_nodes_does_not_bump_version_when_nothing_removed(
        self, graph_storage
    ):
        """No matching nodes → no mutation → version must stay unchanged.

        Guards against an over-eager bump that would invalidate the memo on every
        no-op prune call (harmless for correctness, but would defeat the point of
        the memo on a hot no-op path).
        """
        before = graph_storage.version
        removed = graph_storage.remove_file_nodes("nonexistent.py")
        assert removed == 0
        assert graph_storage.version == before

    def test_equal_count_churn_invalidates_cache(self, graph_storage):
        """remove_file_nodes + re-add restores node/edge counts but must still miss.

        This is exactly the gap the old CentralityRanker instance cache (keyed on
        (node_count, edge_count)) could not see. The version-keyed memo below
        must still invalidate even though the counts round-trip back to their
        original values.
        """
        graph_storage.add_node("a.py:1-10:function:a", "a", "function", "a.py")
        node_count_before = graph_storage.graph.number_of_nodes()

        graph_storage.set_cached_centrality(
            "pagerank", graph_storage.version, {"a.py:1-10:function:a": 1.0}
        )
        assert graph_storage.get_cached_centrality("pagerank") is not None

        # Body-only edit: file's chunk removed and re-added under the same id.
        graph_storage.remove_file_nodes("a.py")
        graph_storage.add_node("a.py:1-10:function:a", "a", "function", "a.py")

        assert graph_storage.graph.number_of_nodes() == node_count_before
        assert graph_storage.get_cached_centrality("pagerank") is None, (
            "Memo must invalidate on equal-count churn, not just count changes"
        )

    def test_get_cached_centrality_returns_none_when_absent(self, graph_storage):
        assert graph_storage.get_cached_centrality("pagerank") is None

    def test_set_then_get_cached_centrality_round_trips(self, graph_storage):
        scores = {"a": 0.5, "b": 1.0}
        graph_storage.set_cached_centrality("pagerank", graph_storage.version, scores)
        assert graph_storage.get_cached_centrality("pagerank") == scores

    def test_get_cached_centrality_returns_copy_not_alias(self, graph_storage):
        """Two reads of the same memo entry must be equal but distinct objects.

        Required for per-query isolation: the caller hands this dict onward to
        shared, long-lived state (ego_graph_retriever.set_centrality_scores), so
        every call must return a fresh object, never a shared reference.
        """
        scores = {"a": 0.5}
        graph_storage.set_cached_centrality("pagerank", graph_storage.version, scores)

        first = graph_storage.get_cached_centrality("pagerank")
        second = graph_storage.get_cached_centrality("pagerank")

        assert first == second
        assert first is not second
        assert first is not scores  # not the caller's original dict either

    def test_get_cached_centrality_misses_after_mutation(self, graph_storage):
        graph_storage.set_cached_centrality(
            "pagerank", graph_storage.version, {"a": 1.0}
        )
        graph_storage.add_node("new.py:1-5:function:new", "new", "function", "new.py")

        assert graph_storage.get_cached_centrality("pagerank") is None

    def test_get_cached_centrality_is_scoped_per_method(self, graph_storage):
        """A memo entry for one centrality method must not answer for another."""
        graph_storage.set_cached_centrality(
            "pagerank", graph_storage.version, {"a": 1.0}
        )
        assert graph_storage.get_cached_centrality("betweenness") is None
