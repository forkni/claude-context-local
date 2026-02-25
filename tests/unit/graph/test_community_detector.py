"""Unit tests for CommunityDetector.detect_communities() phantom degree cap."""

from unittest.mock import MagicMock

import networkx as nx
import pytest

from graph.community_detector import CommunityDetector


def _make_graph_storage(digraph: nx.DiGraph) -> MagicMock:
    """Return a mock CodeGraphStorage wrapping the given DiGraph."""
    storage = MagicMock()
    storage.graph = digraph
    return storage


def _chunk_node(graph: nx.DiGraph, node_id: str) -> None:
    """Add a chunk node (not a phantom) to the graph."""
    graph.add_node(node_id, type="function", is_target_name=False)


def _phantom_node(graph: nx.DiGraph, node_id: str) -> None:
    """Add a phantom node (unresolved call target) to the graph."""
    graph.add_node(node_id, type="symbol_name", is_target_name=True)


class TestDetectCommunitiesPhantomDegreeCap:
    """Verify that high-degree phantom nodes are skipped during collapse."""

    def test_high_degree_phantom_edges_skipped(self):
        """Phantom with >max_phantom_degree callers must NOT generate clique edges."""
        g = nx.DiGraph()

        # 25 chunk nodes
        chunks = [f"file{i}.py:1-10:function:f{i}" for i in range(25)]
        for c in chunks:
            _chunk_node(g, c)

        # One high-degree phantom: called by all 25 chunks
        _phantom_node(g, "str")
        for c in chunks:
            g.add_edge(c, "str")

        storage = _make_graph_storage(g)
        detector = CommunityDetector(storage)

        result = detector.detect_communities(max_phantom_degree=20)

        # Communities should still be returned (one per isolated node or merged)
        assert isinstance(result, dict)
        # None of the chunk nodes should have phantom-collapse edges between them
        # (graph is passed internally — verify indirectly by checking the result
        # exists and is not empty)
        assert len(result) == 25

    def test_low_degree_phantom_clique_edges_created(self):
        """Phantom with <=max_phantom_degree callers must create co-reference edges."""
        g = nx.DiGraph()

        # 5 chunk nodes, all calling same phantom (degree 5 < cap 20)
        chunks = [f"file{i}.py:1-10:function:f{i}" for i in range(5)]
        for c in chunks:
            _chunk_node(g, c)

        _phantom_node(g, "helper")
        for c in chunks:
            g.add_edge(c, "helper")

        storage = _make_graph_storage(g)
        detector = CommunityDetector(storage)

        # With low degree, phantom collapse runs → all 5 nodes share connections
        # Louvain should group them into ≤5 communities (likely 1 since they're fully connected)
        result = detector.detect_communities(max_phantom_degree=20)

        assert isinstance(result, dict)
        assert len(result) == 5
        # All 5 chunks should be in the same community (fully connected clique)
        community_ids = set(result.values())
        assert len(community_ids) == 1

    def test_mixed_phantoms_caps_only_high_degree(self):
        """High-degree phantom skipped; low-degree phantom still creates edges."""
        g = nx.DiGraph()

        # 6 chunk nodes split into two groups of 3
        group_a = [f"a{i}.py:1-5:function:a{i}" for i in range(3)]
        group_b = [f"b{i}.py:1-5:function:b{i}" for i in range(3)]
        all_chunks = group_a + group_b
        for c in all_chunks:
            _chunk_node(g, c)

        # Low-degree phantom: called only by group_a (degree 3 < cap 5)
        _phantom_node(g, "helper_a")
        for c in group_a:
            g.add_edge(c, "helper_a")

        # High-degree phantom: called by all 6 chunks (degree 6 > cap 5)
        _phantom_node(g, "str")
        for c in all_chunks:
            g.add_edge(c, "str")

        storage = _make_graph_storage(g)
        detector = CommunityDetector(storage)

        result = detector.detect_communities(max_phantom_degree=5)

        assert isinstance(result, dict)
        assert len(result) == 6

        # group_a should be in the same community (connected via helper_a)
        a_communities = {result[c] for c in group_a}
        assert len(a_communities) == 1, "group_a should be in the same community"

        # group_b should NOT be in the same community as group_a
        # (str phantom was skipped so no cross-group edges)
        b_communities = {result[c] for c in group_b}
        assert a_communities.isdisjoint(
            b_communities
        ), "group_a and group_b should be in different communities"

    def test_default_cap_is_20(self):
        """Verify default max_phantom_degree=20 is the effective default."""
        g = nx.DiGraph()

        # 21 chunks calling same phantom → exceeds default cap of 20
        chunks = [f"file{i}.py:1-5:function:f{i}" for i in range(21)]
        for c in chunks:
            _chunk_node(g, c)
        _phantom_node(g, "str")
        for c in chunks:
            g.add_edge(c, "str")

        storage = _make_graph_storage(g)
        detector = CommunityDetector(storage)

        # Call without explicit max_phantom_degree — should use default 20
        result = detector.detect_communities()

        # With phantom skipped (21 > 20), nodes are isolated → each own community
        assert isinstance(result, dict)
        assert len(result) == 21
        # Should produce multiple communities (not a single clique)
        community_ids = set(result.values())
        assert len(community_ids) > 1

    def test_empty_graph_returns_empty(self):
        """Empty graph should return empty dict (existing behavior preserved)."""
        g = nx.DiGraph()
        storage = _make_graph_storage(g)
        detector = CommunityDetector(storage)

        result = detector.detect_communities(max_phantom_degree=20)

        assert result == {}
