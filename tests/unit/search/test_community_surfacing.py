"""Unit tests for SSCG Phase 4: Community Context Surfacing.

Tests the integration of community detection data into subgraph extraction,
validating the _annotate_communities() method and its serialization.
"""

from unittest.mock import MagicMock

import networkx as nx
import pytest

from search.subgraph_extractor import SubgraphExtractor


@pytest.fixture
def mock_storage_with_communities():
    """Create a mock storage with a simple graph and community map."""
    storage = MagicMock()

    # Use proper chunk_id format: "file.py:lines:type:name"
    # chunk_a, chunk_b in community 0 (graph/ dir)
    # chunk_c in community 1 (search/ dir)
    chunk_a = "graph/module.py:10-20:function:func_a"
    chunk_b = "graph/utils.py:30-40:function:func_b"
    chunk_c = "search/handler.py:50-60:function:func_c"

    g = nx.DiGraph()

    # Add nodes with metadata (stored IN the graph)
    g.add_node(
        chunk_a,
        name="func_a",
        type="function",
        file="graph/module.py",
    )
    g.add_node(
        chunk_b,
        name="func_b",
        type="function",
        file="graph/utils.py",
    )
    g.add_node(
        chunk_c,
        name="func_c",
        type="function",
        file="search/handler.py",
    )

    # Add edges
    g.add_edge(chunk_a, chunk_b, type="calls", line=10)
    g.add_edge(chunk_b, chunk_c, type="calls", line=20)

    storage.graph = g
    storage.project_root = None

    # Mock community map using proper chunk_ids
    storage.load_community_map.return_value = {
        chunk_a: 0,
        chunk_b: 0,
        chunk_c: 1,
    }

    return storage


def test_community_annotation(mock_storage_with_communities):
    """Test basic community annotation with labels and counts."""
    chunk_a = "graph/module.py:10-20:function:func_a"
    chunk_b = "graph/utils.py:30-40:function:func_b"
    chunk_c = "search/handler.py:50-60:function:func_c"

    extractor = SubgraphExtractor(mock_storage_with_communities)

    result = extractor.extract_subgraph([chunk_a, chunk_b, chunk_c])

    # Verify nodes have correct community_id set
    node_map = {n.chunk_id: n for n in result.nodes}
    assert node_map[chunk_a].community_id == 0
    assert node_map[chunk_b].community_id == 0
    assert node_map[chunk_c].community_id == 1

    # Verify communities dict has 2 entries with label and count
    assert result.communities is not None
    assert len(result.communities) == 2
    assert 0 in result.communities
    assert 1 in result.communities

    # Community 0 should have 2 members
    assert result.communities[0]["count"] == 2
    # Community 1 should have 1 member
    assert result.communities[1]["count"] == 1

    # Labels should be present
    assert "label" in result.communities[0]
    assert "label" in result.communities[1]


def test_community_labels_from_directories(mock_storage_with_communities):
    """Test that community labels are derived from parent directories."""
    chunk_a = "graph/module.py:10-20:function:func_a"
    chunk_b = "graph/utils.py:30-40:function:func_b"
    chunk_c = "search/handler.py:50-60:function:func_c"

    extractor = SubgraphExtractor(mock_storage_with_communities)

    result = extractor.extract_subgraph([chunk_a, chunk_b, chunk_c])

    # Community 0 has chunks in graph/ dir
    assert result.communities[0]["label"] == "graph"
    # Community 1 has chunks in search/ dir
    assert result.communities[1]["label"] == "search"


def test_empty_community_map():
    """Test behavior when community map is None or empty."""
    storage = MagicMock()

    # Simple graph
    g = nx.DiGraph()
    g.add_node("chunk_a", name="func_a", type="function", file="module.py")
    g.add_node("chunk_b", name="func_b", type="function", file="utils.py")
    g.add_edge("chunk_a", "chunk_b", type="calls", line=10)
    storage.graph = g
    storage.project_root = None

    # No community map
    storage.load_community_map.return_value = None

    extractor = SubgraphExtractor(storage)
    result = extractor.extract_subgraph(["chunk_a", "chunk_b"])

    # communities should be None
    assert result.communities is None

    # Nodes should have community_id = None
    for node in result.nodes:
        assert node.community_id is None


def test_partial_community_map():
    """Test when community map only covers some nodes."""
    storage = MagicMock()

    # Graph with 3 nodes
    g = nx.DiGraph()
    g.add_node("chunk_a", name="func_a", type="function", file="graph/module.py")
    g.add_node("chunk_b", name="func_b", type="function", file="graph/utils.py")
    g.add_node("chunk_c", name="func_c", type="function", file="search/handler.py")
    g.add_edge("chunk_a", "chunk_b", type="calls", line=10)
    g.add_edge("chunk_b", "chunk_c", type="calls", line=20)
    storage.graph = g
    storage.project_root = None

    # Community map only covers chunk_a and chunk_b
    storage.load_community_map.return_value = {
        "chunk_a": 0,
        "chunk_b": 0,
        # chunk_c not in community map
    }

    extractor = SubgraphExtractor(storage)
    result = extractor.extract_subgraph(["chunk_a", "chunk_b", "chunk_c"])

    # Annotated nodes should have community_id set
    node_map = {n.chunk_id: n for n in result.nodes}
    assert node_map["chunk_a"].community_id == 0
    assert node_map["chunk_b"].community_id == 0

    # Unannotated node should have community_id = None
    assert node_map["chunk_c"].community_id is None

    # Communities dict should only count annotated nodes
    assert result.communities is not None
    assert len(result.communities) == 1
    assert result.communities[0]["count"] == 2


def test_community_in_serialized_output(mock_storage_with_communities):
    """Test that to_dict() includes community data in correct format."""
    chunk_a = "graph/module.py:10-20:function:func_a"
    chunk_b = "graph/utils.py:30-40:function:func_b"
    chunk_c = "search/handler.py:50-60:function:func_c"

    extractor = SubgraphExtractor(mock_storage_with_communities)

    result = extractor.extract_subgraph([chunk_a, chunk_b, chunk_c])
    serialized = result.to_dict()

    # Top-level communities key should be present
    assert "communities" in serialized
    assert isinstance(serialized["communities"], dict)

    # Each community should have label and count
    for _cid, data in serialized["communities"].items():
        assert "label" in data
        assert "count" in data
        assert isinstance(data["count"], int)
        assert data["count"] > 0

    # Nodes should include community field
    for node_dict in serialized["nodes"]:
        if node_dict["id"] in [chunk_a, chunk_b]:
            assert node_dict["community"] == 0
        elif node_dict["id"] == chunk_c:
            assert node_dict["community"] == 1


def test_community_with_ego_neighbors():
    """Test that ego neighbors also get community annotation."""
    storage = MagicMock()

    # Graph: chunk_a -> chunk_b -> chunk_neighbor
    # chunk_neighbor is an ego neighbor, not a search result
    g = nx.DiGraph()
    g.add_node("chunk_a", name="func_a", type="function", file="graph/module.py")
    g.add_node("chunk_b", name="func_b", type="function", file="graph/utils.py")
    g.add_node(
        "chunk_neighbor",
        name="func_neighbor",
        type="function",
        file="graph/neighbor.py",
    )
    g.add_edge("chunk_a", "chunk_b", type="calls", line=10)
    g.add_edge("chunk_b", "chunk_neighbor", type="calls", line=20)
    storage.graph = g
    storage.project_root = None

    # Community map covers all nodes including ego neighbor
    storage.load_community_map.return_value = {
        "chunk_a": 0,
        "chunk_b": 0,
        "chunk_neighbor": 0,
    }

    extractor = SubgraphExtractor(storage)

    # Extract with ego_neighbor_ids
    result = extractor.extract_subgraph(
        chunk_ids=["chunk_a", "chunk_b"], ego_neighbor_ids=["chunk_neighbor"]
    )

    # All nodes should have community_id set
    node_map = {n.chunk_id: n for n in result.nodes}
    assert node_map["chunk_a"].community_id == 0
    assert node_map["chunk_b"].community_id == 0
    assert node_map["chunk_neighbor"].community_id == 0

    # Community should have count of 3
    assert result.communities[0]["count"] == 3


def test_build_temp_graph_project_id(tmp_path):
    """Test that _build_temp_graph derives correct project_id from parent directory."""
    from unittest.mock import MagicMock, patch

    from search.incremental_indexer import IncrementalIndexer

    # Create a real temp directory structure to test path logic
    project_dir = tmp_path / "myproject_abc123_bge-m3_1024d"
    index_dir = project_dir / "index"
    index_dir.mkdir(parents=True)

    # Mock indexer with storage_dir pointing to index subdirectory
    mock_indexer = MagicMock()
    mock_indexer.storage_dir = index_dir

    # Create IncrementalIndexer with mocked indexer
    inc_indexer = IncrementalIndexer(indexer=mock_indexer)

    # Mock GraphIntegration to capture what project_id it receives
    captured_project_id = None
    captured_storage_dir = None

    def mock_graph_integration_init(self, project_id, storage_dir):
        nonlocal captured_project_id, captured_storage_dir
        captured_project_id = project_id
        captured_storage_dir = storage_dir
        self.storage = MagicMock()
        self._logger = MagicMock()
        return None  # __init__ returns None

    with (
        patch(
            "search.incremental_indexer.GraphIntegration.__init__",
            mock_graph_integration_init,
        ),
        patch("search.incremental_indexer.GraphIntegration.build_graph_from_chunks"),
        patch("search.incremental_indexer.logger"),
    ):
        # Call _build_temp_graph
        inc_indexer._build_temp_graph([])

    # Verify project_id is derived from parent directory name with dimension suffix stripped
    # Parent dir: myproject_abc123_bge-m3_1024d
    # Expected project_id: myproject_abc123_bge-m3 (strip "_1024d")
    assert captured_project_id == "myproject_abc123_bge-m3", (
        f"Expected 'myproject_abc123_bge-m3', got '{captured_project_id}'"
    )
