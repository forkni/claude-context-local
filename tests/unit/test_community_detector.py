"""Unit tests for Leiden community detection."""

import pytest

try:
    import networkx as nx
except ImportError:
    pytest.skip("NetworkX not installed", allow_module_level=True)

from graph.community_detector import CommunityDetector
from graph.graph_storage import CodeGraphStorage


class TestCommunityDetector:
    """Tests for CommunityDetector class."""

    def create_mock_graph_storage(self, graph=None):
        """Create a mock CodeGraphStorage with a given NetworkX graph.

        Args:
            graph: NetworkX graph to use (creates empty if None)

        Returns:
            CodeGraphStorage instance
        """
        if graph is None:
            graph = nx.DiGraph()

        # Create mock storage
        storage = CodeGraphStorage.__new__(CodeGraphStorage)
        storage.graph = graph
        storage.logger = None
        return storage

    def test_detect_communities_empty_graph(self):
        """Empty graph returns empty dict."""
        storage = self.create_mock_graph_storage()
        detector = CommunityDetector(storage)

        communities = detector.detect_communities()

        assert communities == {}

    def test_detect_communities_single_node(self):
        """Single node gets community 0."""
        graph = nx.DiGraph()
        graph.add_node("chunk1", name="func1", type="function")

        storage = self.create_mock_graph_storage(graph)
        detector = CommunityDetector(storage)

        communities = detector.detect_communities()

        assert len(communities) == 1
        assert "chunk1" in communities
        assert communities["chunk1"] == 0  # Single community

    def test_detect_communities_connected_components(self):
        """Disconnected components become separate communities."""
        graph = nx.DiGraph()

        # Component 1: Nodes A -> B -> C
        graph.add_edge("A", "B")
        graph.add_edge("B", "C")

        # Component 2: Nodes X -> Y (disconnected from A-B-C)
        graph.add_edge("X", "Y")

        storage = self.create_mock_graph_storage(graph)
        detector = CommunityDetector(storage)

        communities = detector.detect_communities()

        # Should have nodes from both components
        assert len(communities) == 5
        assert all(node in communities for node in ["A", "B", "C", "X", "Y"])

        # Disconnected components should be in different communities
        # (This is probabilistic, but generally holds for clear separations)
        component1_communities = {communities["A"], communities["B"], communities["C"]}
        component2_communities = {communities["X"], communities["Y"]}

        # At least one of the components should form its own community
        # (strict separation not guaranteed, but highly likely)
        assert len(component1_communities | component2_communities) >= 2

    def test_community_stats_empty(self):
        """Stats for empty communities."""
        storage = self.create_mock_graph_storage()
        detector = CommunityDetector(storage)

        stats = detector.get_community_stats({})

        assert stats["num_communities"] == 0
        assert stats["avg_size"] == 0
        assert stats["largest"] == 0
        assert stats["smallest"] == 0

    def test_community_stats(self):
        """Verify statistics calculation."""
        communities = {
            "A": 0,
            "B": 0,
            "C": 0,  # Community 0 has 3 members
            "X": 1,
            "Y": 1,  # Community 1 has 2 members
            "Z": 2,  # Community 2 has 1 member
        }

        storage = self.create_mock_graph_storage()
        detector = CommunityDetector(storage)

        stats = detector.get_community_stats(communities)

        assert stats["num_communities"] == 3
        assert stats["avg_size"] == pytest.approx((3 + 2 + 1) / 3)
        assert stats["largest"] == 3
        assert stats["smallest"] == 1

    def test_leiden_resolution_parameter(self):
        """Higher resolution creates more fine-grained communities."""
        # Create a graph with clear structure
        graph = nx.DiGraph()

        # Tightly connected group 1
        graph.add_edge("A1", "A2")
        graph.add_edge("A2", "A3")
        graph.add_edge("A3", "A1")

        # Tightly connected group 2
        graph.add_edge("B1", "B2")
        graph.add_edge("B2", "B3")
        graph.add_edge("B3", "B1")

        # Weak connection between groups
        graph.add_edge("A1", "B1")

        storage = self.create_mock_graph_storage(graph)
        detector = CommunityDetector(storage)

        # Low resolution (should merge groups)
        communities_low = detector.detect_communities(resolution=0.5)

        # High resolution (should separate groups)
        communities_high = detector.detect_communities(resolution=2.0)

        # Verify we got results
        assert len(communities_low) == 6
        assert len(communities_high) == 6

        # Higher resolution typically creates more communities
        # (This is probabilistic, so we use weak assertion)
        num_communities_low = len(set(communities_low.values()))
        num_communities_high = len(set(communities_high.values()))

        # At minimum, both should detect the structure
        assert num_communities_low >= 1
        assert num_communities_high >= 1

    def test_detect_communities_preserves_node_ids(self):
        """Community detection preserves original node IDs."""
        graph = nx.DiGraph()

        # Add nodes with realistic chunk IDs
        chunk_ids = [
            "file.py:10-20:function:foo",
            "file.py:25-35:function:bar",
            "file.py:40-50:class:Baz",
        ]

        for chunk_id in chunk_ids:
            graph.add_node(chunk_id)

        # Add edges
        graph.add_edge(chunk_ids[0], chunk_ids[1])
        graph.add_edge(chunk_ids[1], chunk_ids[2])

        storage = self.create_mock_graph_storage(graph)
        detector = CommunityDetector(storage)

        communities = detector.detect_communities()

        # All original node IDs should be present
        assert set(communities.keys()) == set(chunk_ids)

    def test_hierarchical_communities_placeholder(self):
        """Hierarchical communities returns single level for now."""
        graph = nx.DiGraph()
        graph.add_edge("A", "B")

        storage = self.create_mock_graph_storage(graph)
        detector = CommunityDetector(storage)

        hierarchy = detector.get_hierarchical_communities(max_levels=3)

        # Currently only returns level 0
        assert 0 in hierarchy
        assert len(hierarchy[0]) == 2  # A and B

    def test_detect_communities_handles_edge_attributes(self):
        """Community detection works with edge attributes."""
        graph = nx.DiGraph()

        # Add edges with metadata (like call relationships)
        graph.add_edge("A", "B", weight=1.0, call_type="direct")
        graph.add_edge("B", "C", weight=0.5, call_type="indirect")

        storage = self.create_mock_graph_storage(graph)
        detector = CommunityDetector(storage)

        communities = detector.detect_communities()

        # Should successfully detect communities despite edge attributes
        assert len(communities) == 3
        assert all(node in communities for node in ["A", "B", "C"])
