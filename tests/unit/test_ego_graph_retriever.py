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

        config = EgoGraphConfig(k_hops=2, max_neighbors_per_hop=10)
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
