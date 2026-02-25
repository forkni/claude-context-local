"""Unit tests for ego-graph retrieval."""

from unittest.mock import Mock

import pytest

from search.config import EgoGraphConfig
from search.ego_graph_retriever import EgoGraphRetriever


class TestEgoGraphRetriever:
    """Test cases for EgoGraphRetriever."""

    @pytest.fixture
    def mock_graph_storage(self):
        """Create a mock graph storage."""
        mock = Mock()
        mock.load_community_map.return_value = None  # No community data by default
        return mock

    @pytest.fixture
    def retriever(self, mock_graph_storage):
        """Create a retriever instance."""
        return EgoGraphRetriever(mock_graph_storage)

    def test_init(self, retriever, mock_graph_storage):
        """Test initialization."""
        assert retriever.graph == mock_graph_storage

    def test_retrieve_ego_graph_basic(self, retriever, mock_graph_storage):
        """Test basic ego-graph retrieval."""
        # Setup mock - use valid chunk_id format (file:lines:type:name)
        mock_graph_storage.get_neighbors = Mock(
            return_value=[
                "file1.py:10-20:function:neighbor1",
                "file2.py:30-40:function:neighbor2",
            ]
        )

        config = EgoGraphConfig(k_hops=2, max_neighbors_per_hop=10, edge_weights=None)
        result = retriever.retrieve_ego_graph(["anchor1"], config)

        assert "anchor1" in result
        assert result["anchor1"] == [
            "file1.py:10-20:function:neighbor1",
            "file2.py:30-40:function:neighbor2",
        ]
        mock_graph_storage.get_neighbors.assert_called_once_with(
            "anchor1",
            relation_types=None,
            max_depth=2,
            exclude_import_categories=["stdlib", "builtin", "third_party"],
            edge_weights=None,
        )

    def test_retrieve_ego_graph_multiple_anchors(self, retriever, mock_graph_storage):
        """Test retrieval for multiple anchors."""
        mock_graph_storage.get_neighbors = Mock(
            side_effect=[
                [
                    "file1.py:10-20:function:n1",
                    "file2.py:30-40:function:n2",
                ],  # For anchor1
                [
                    "file3.py:50-60:function:n3",
                    "file4.py:70-80:function:n4",
                ],  # For anchor2
            ]
        )

        config = EgoGraphConfig(k_hops=1)
        result = retriever.retrieve_ego_graph(["anchor1", "anchor2"], config)

        assert len(result) == 2
        assert result["anchor1"] == [
            "file1.py:10-20:function:n1",
            "file2.py:30-40:function:n2",
        ]
        assert result["anchor2"] == [
            "file3.py:50-60:function:n3",
            "file4.py:70-80:function:n4",
        ]

    def test_retrieve_ego_graph_limits_neighbors(self, retriever, mock_graph_storage):
        """Test that neighbors are limited to prevent explosion."""
        # Return 30 neighbors but limit should cap at max_neighbors_per_hop * k_hops
        many_neighbors = [f"file{i}.py:10-20:function:neighbor{i}" for i in range(30)]
        mock_graph_storage.get_neighbors = Mock(return_value=many_neighbors)

        config = EgoGraphConfig(k_hops=2, max_neighbors_per_hop=5)  # 2 * 5 = 10 max
        result = retriever.retrieve_ego_graph(["anchor1"], config)

        assert len(result["anchor1"]) == 10  # Limited

    def test_retrieve_ego_graph_empty_anchors(self, retriever):
        """Test with empty anchor list."""
        config = EgoGraphConfig()
        result = retriever.retrieve_ego_graph([], config)

        assert result == {}

    def test_retrieve_ego_graph_with_relation_filter(
        self, retriever, mock_graph_storage
    ):
        """Test retrieval with relation type filter."""
        mock_graph_storage.get_neighbors = Mock(
            return_value=["file1.py:10-20:function:n1"]
        )

        config = EgoGraphConfig(relation_types=["CALLS", "INHERITS"])
        retriever.retrieve_ego_graph(["anchor1"], config)

        # Verify relation types were passed
        call_args = mock_graph_storage.get_neighbors.call_args
        assert call_args[1]["relation_types"] == ["CALLS", "INHERITS"]

    def test_flatten_for_context_basic(self, retriever):
        """Test flattening ego-graphs to chunk list."""
        ego_graphs = {
            "anchor1": ["n1", "n2"],
            "anchor2": ["n3", "n1"],  # n1 is duplicate
        }
        config = EgoGraphConfig(include_anchor=True, deduplicate=True)

        result = retriever.flatten_for_context(ego_graphs, config)

        # Should have anchors + unique neighbors
        assert set(result) == {"anchor1", "anchor2", "n1", "n2", "n3"}
        assert len(result) == 5

    def test_flatten_without_anchors(self, retriever):
        """Test flattening without including anchors."""
        ego_graphs = {
            "anchor1": ["n1", "n2"],
            "anchor2": ["n3"],
        }
        config = EgoGraphConfig(include_anchor=False)

        result = retriever.flatten_for_context(ego_graphs, config)

        assert "anchor1" not in result
        assert "anchor2" not in result
        assert set(result) == {"n1", "n2", "n3"}

    def test_expand_search_results_disabled(self, retriever):
        """Test that expansion is skipped when disabled."""
        search_results = [
            {"chunk_id": "chunk1", "score": 0.9},
            {"chunk_id": "chunk2", "score": 0.8},
        ]
        config = EgoGraphConfig(enabled=False)

        chunk_ids, ego_graphs = retriever.expand_search_results(search_results, config)

        # Should return original chunk_ids only
        assert chunk_ids == ["chunk1", "chunk2"]
        assert ego_graphs == {}

    def test_expand_search_results_enabled(self, retriever, mock_graph_storage):
        """Test full expansion workflow."""
        search_results = [
            {"chunk_id": "chunk1", "score": 0.9},
            {"chunk_id": "chunk2", "score": 0.8},
        ]

        # Mock neighbors for each chunk - use valid chunk_id format
        mock_graph_storage.get_neighbors = Mock(
            side_effect=[
                [
                    "file1.py:10-20:function:n1",
                    "file2.py:30-40:function:n2",
                ],  # For chunk1
                ["file3.py:50-60:function:n3"],  # For chunk2
            ]
        )

        config = EgoGraphConfig(enabled=True, k_hops=1, include_anchor=True)

        chunk_ids, ego_graphs = retriever.expand_search_results(search_results, config)

        # Should have anchors + neighbors
        assert set(chunk_ids) == {
            "chunk1",
            "chunk2",
            "file1.py:10-20:function:n1",
            "file2.py:30-40:function:n2",
            "file3.py:50-60:function:n3",
        }
        assert ego_graphs == {
            "chunk1": [
                "file1.py:10-20:function:n1",
                "file2.py:30-40:function:n2",
            ],
            "chunk2": ["file3.py:50-60:function:n3"],
        }

    def test_expand_search_results_empty(self, retriever):
        """Test expansion with empty results."""
        config = EgoGraphConfig(enabled=True)
        chunk_ids, ego_graphs = retriever.expand_search_results([], config)

        assert chunk_ids == []
        assert ego_graphs == {}

    def test_error_handling(self, retriever, mock_graph_storage):
        """Test error handling when graph retrieval fails."""
        mock_graph_storage.get_neighbors = Mock(side_effect=Exception("Graph error"))

        config = EgoGraphConfig()
        result = retriever.retrieve_ego_graph(["anchor1"], config)

        # Should return empty list for failed anchor
        assert result["anchor1"] == []

    # --- QW1: Centrality-aware neighbor ranking ---

    def test_set_centrality_scores(self, retriever):
        """set_centrality_scores injects scores into the retriever."""
        assert retriever._centrality_scores == {}
        retriever.set_centrality_scores({"a": 0.5, "b": 0.3})
        assert retriever._centrality_scores == {"a": 0.5, "b": 0.3}

    def test_centrality_ranking_survives_truncation(self, mock_graph_storage):
        """High-centrality neighbors survive truncation over low-centrality ones."""
        mock_graph_storage.load_community_map.return_value = None
        retriever = EgoGraphRetriever(mock_graph_storage)

        # 20 neighbors but cap = k_hops * max_neighbors_per_hop = 2*5 = 10
        neighbors = [f"file{i}.py:10-20:function:n{i}" for i in range(20)]
        mock_graph_storage.get_neighbors = Mock(return_value=neighbors)

        # n10-n19 have highest centrality scores
        centrality = {f"file{i}.py:10-20:function:n{i}": i / 20.0 for i in range(20)}
        retriever.set_centrality_scores(centrality)

        config = EgoGraphConfig(k_hops=2, max_neighbors_per_hop=5)
        result = retriever.retrieve_ego_graph(["anchor1"], config)

        assert len(result["anchor1"]) == 10
        # Top-10 by centrality (n10..n19) should survive
        for i in range(10, 20):
            assert f"file{i}.py:10-20:function:n{i}" in result["anchor1"]

    def test_without_centrality_uses_bfs_order(self, retriever, mock_graph_storage):
        """Without centrality scores, truncation preserves BFS order (first N)."""
        neighbors = [f"file{i}.py:10-20:function:n{i}" for i in range(20)]
        mock_graph_storage.get_neighbors = Mock(return_value=neighbors)

        config = EgoGraphConfig(k_hops=2, max_neighbors_per_hop=5)
        result = retriever.retrieve_ego_graph(["anchor1"], config)

        assert len(result["anchor1"]) == 10
        # Without centrality, should be the first 10 (BFS discovery order)
        assert result["anchor1"] == neighbors[:10]

    # --- QW2: Community-bounded ego-graph expansion ---

    def test_community_bounded_penalizes_cross_community(self, mock_graph_storage):
        """Cross-community neighbors get penalized; same-community neighbors preferred."""
        community_map = {
            "anchor.py:1-10:function:anchor": 0,
            "same.py:10-20:function:same": 0,  # same community as anchor
            "other.py:10-20:function:other": 1,  # different community
        }
        mock_graph_storage.load_community_map.return_value = community_map
        retriever = EgoGraphRetriever(mock_graph_storage)

        # 10 neighbors alternating same/other
        neighbors = [
            "same.py:10-20:function:same",
            "other.py:10-20:function:other",
        ] * 5
        mock_graph_storage.get_neighbors = Mock(return_value=neighbors)

        # Equal raw centrality — community penalty should differentiate ranking
        centrality = {
            "same.py:10-20:function:same": 0.5,
            "other.py:10-20:function:other": 0.5,
        }
        retriever.set_centrality_scores(centrality)

        # cap = 2*1 = 2, forces truncation
        config = EgoGraphConfig(
            k_hops=2,
            max_neighbors_per_hop=1,
            community_bounded=True,
            cross_community_penalty=0.6,
        )
        result = retriever.retrieve_ego_graph(
            ["anchor.py:1-10:function:anchor"], config
        )

        # Same-community scores 0.5; cross-community scores 0.5*0.6=0.3 → same wins
        assert (
            result["anchor.py:1-10:function:anchor"][0] == "same.py:10-20:function:same"
        )

    def test_community_bounded_false_disables_penalty(self, mock_graph_storage):
        """community_bounded=False means cross-community neighbors keep full centrality."""
        community_map = {
            "anchor.py:1-10:function:anchor": 0,
            "cross.py:10-20:function:cross": 1,
        }
        mock_graph_storage.load_community_map.return_value = community_map
        retriever = EgoGraphRetriever(mock_graph_storage)
        retriever.set_centrality_scores({"cross.py:10-20:function:cross": 0.8})

        config = EgoGraphConfig(community_bounded=False)
        score = retriever._rank_neighbor("cross.py:10-20:function:cross", 0, config)

        # No penalty: returns raw centrality score
        assert score == 0.8

    # --- QW3: Personalized PageRank expansion mode ---

    def test_ppr_expansion_routes_correctly(self, mock_graph_storage):
        """expansion_mode='ppr' finds connected neighbors via Personalized PageRank."""
        import networkx as nx

        nx_graph = nx.DiGraph()
        nx_graph.add_edge("anchor.py:1-10:function:a", "file1.py:10-20:function:n1")
        nx_graph.add_edge("anchor.py:1-10:function:a", "file2.py:30-40:function:n2")
        mock_graph_storage.get_graph = Mock(return_value=nx_graph)
        mock_graph_storage.load_community_map.return_value = None
        retriever = EgoGraphRetriever(mock_graph_storage)

        config = EgoGraphConfig(
            expansion_mode="ppr", ppr_alpha=0.85, k_hops=2, max_neighbors_per_hop=10
        )
        result = retriever.retrieve_ego_graph(["anchor.py:1-10:function:a"], config)

        assert "anchor.py:1-10:function:a" in result
        neighbors = result["anchor.py:1-10:function:a"]
        assert len(neighbors) > 0
        # All returned nodes should be valid chunk_ids (contain at least 3 colons)
        for n in neighbors:
            assert n.count(":") >= 3

    def test_ppr_empty_graph_returns_empty(self, mock_graph_storage):
        """PPR with an empty graph returns empty neighbor lists."""
        import networkx as nx

        mock_graph_storage.get_graph = Mock(return_value=nx.DiGraph())
        mock_graph_storage.load_community_map.return_value = None
        retriever = EgoGraphRetriever(mock_graph_storage)

        config = EgoGraphConfig(expansion_mode="ppr")
        result = retriever.retrieve_ego_graph(["anchor1"], config)

        assert result == {"anchor1": []}
