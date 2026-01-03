"""Tests for multi-hop search expansion functionality.

Extracted from test_hybrid_search.py (Phase 3.4 refactoring).
"""

from unittest.mock import MagicMock, patch

import numpy as np

from search.multi_hop_searcher import MultiHopSearcher
from search.reranker import SearchResult


class TestMultiHopSearcher:
    """Test multi-hop search expansion functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedder = MagicMock()
        self.mock_dense_index = MagicMock()
        self.mock_single_hop_callback = MagicMock()
        self.mock_reranking_engine = MagicMock()

        self.searcher = MultiHopSearcher(
            embedder=self.mock_embedder,
            dense_index=self.mock_dense_index,
            single_hop_callback=self.mock_single_hop_callback,
            reranking_engine=self.mock_reranking_engine,
        )

    def test_validate_params_valid(self):
        """Test parameter validation with valid inputs."""
        hops, expansion = self.searcher.validate_params(hops=2, expansion_factor=0.3)
        assert hops == 2
        assert expansion == 0.3

    def test_validate_params_invalid_hops(self):
        """Test parameter validation with invalid hops."""
        hops, expansion = self.searcher.validate_params(hops=0, expansion_factor=0.3)
        assert hops == 1  # Should be corrected to minimum
        assert expansion == 0.3

    def test_validate_params_invalid_expansion(self):
        """Test parameter validation with invalid expansion factor."""
        hops, expansion = self.searcher.validate_params(hops=2, expansion_factor=3.0)
        assert hops == 2
        assert expansion == 0.3  # Should be corrected to default

    def test_validate_params_negative_expansion(self):
        """Test parameter validation with negative expansion factor."""
        hops, expansion = self.searcher.validate_params(hops=2, expansion_factor=-0.5)
        assert hops == 2
        assert expansion == 0.3  # Should be corrected to default

    def test_expand_from_initial_results_batched(self):
        """Test expansion using batched FAISS search."""
        # Create initial results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]

        all_chunk_ids = {"chunk1", "chunk2"}
        all_results = {
            "chunk1": initial_results[0],
            "chunk2": initial_results[1],
        }

        # Mock batched search results
        batched_results = {
            "chunk1": [
                ("chunk3", 0.7, {"file": "test.py"}),
                ("chunk4", 0.6, {"file": "test.py"}),
            ],
            "chunk2": [
                ("chunk5", 0.65, {"file": "test.py"}),
            ],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results

        # Perform expansion
        timings = self.searcher.expand_from_initial_results(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=2,
            hops=2,
            k=2,
        )

        # Verify results
        assert len(all_chunk_ids) == 5  # Original 2 + 3 new
        assert "chunk3" in all_chunk_ids
        assert "chunk4" in all_chunk_ids
        assert "chunk5" in all_chunk_ids
        assert len(all_results) == 5
        assert 2 in timings  # Hop 2 timing recorded

    def test_expand_from_initial_results_no_duplicates(self):
        """Test that expansion doesn't add duplicate chunks."""
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
        ]

        all_chunk_ids = {"chunk1"}
        all_results = {"chunk1": initial_results[0]}

        # Mock batched search returning chunk that's already in results
        batched_results = {
            "chunk1": [
                ("chunk1", 1.0, {"file": "test.py"}),  # Self-reference
                ("chunk2", 0.7, {"file": "test.py"}),
            ],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results

        # Perform expansion
        self.searcher.expand_from_initial_results(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=2,
            hops=2,
            k=1,
        )

        # Verify no duplicate
        assert len(all_chunk_ids) == 2  # Original 1 + 1 new (not 2 new)
        assert "chunk2" in all_chunk_ids

    def test_expand_from_initial_results_error_handling(self):
        """Test expansion handles FAISS errors gracefully."""
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
        ]

        all_chunk_ids = {"chunk1"}
        all_results = {"chunk1": initial_results[0]}

        # Mock batched search to raise exception
        self.mock_dense_index.get_similar_chunks_batched.side_effect = Exception(
            "FAISS error"
        )

        # Should not raise exception
        timings = self.searcher.expand_from_initial_results(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=2,
            hops=2,
            k=1,
        )

        # Verify expansion was attempted but failed gracefully
        assert 2 in timings
        assert len(all_chunk_ids) == 1  # No new chunks added

    def test_apply_post_expansion_filters_no_filters(self):
        """Test that no filtering occurs when filters are None."""
        all_results = {
            "chunk1": SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            "chunk2": SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        }

        filtered = self.searcher.apply_post_expansion_filters(
            all_results=all_results, initial_results_count=1, filters=None
        )

        assert len(filtered) == 2
        assert filtered == all_results

    def test_apply_post_expansion_filters_with_filters(self):
        """Test filtering of expanded results."""
        all_results = {
            "chunk1": SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            "chunk2": SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
            "chunk3": SearchResult(chunk_id="chunk3", score=0.7, metadata={}),
        }

        # Mock metadata store
        def mock_get(chunk_id):
            metadata_map = {
                "chunk1": {"metadata": {"file": "test.py"}},
                "chunk2": {"metadata": {"file": "other.py"}},
                "chunk3": {"metadata": {"file": "test.py"}},
            }
            return metadata_map.get(chunk_id)

        self.mock_dense_index.metadata_store.get.side_effect = mock_get

        # Mock filter matching
        def mock_matches_filters(metadata, filters):
            if filters and "file_pattern" in filters:
                return filters["file_pattern"] in metadata.get("file", "")
            return True

        self.mock_dense_index._matches_filters.side_effect = mock_matches_filters

        # Apply filters
        filtered = self.searcher.apply_post_expansion_filters(
            all_results=all_results,
            initial_results_count=1,
            filters={"file_pattern": "test"},
        )

        # Should keep chunk1 and chunk3 (test.py), but not chunk2 (other.py)
        assert len(filtered) == 2
        assert "chunk1" in filtered
        assert "chunk3" in filtered
        assert "chunk2" not in filtered

    def test_apply_post_expansion_filters_no_expansion(self):
        """Test that filtering is skipped when no expansion occurred."""
        all_results = {
            "chunk1": SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
        }

        # Should skip filtering since len(all_results) <= initial_results_count
        filtered = self.searcher.apply_post_expansion_filters(
            all_results=all_results,
            initial_results_count=1,
            filters={"file_pattern": "test"},
        )

        assert filtered == all_results
        # Verify no metadata lookups occurred
        self.mock_dense_index.metadata_store.get.assert_not_called()

    @patch("search.multi_hop_searcher._get_config_via_service_locator")
    def test_search_single_hop(self, mock_config):
        """Test multi-hop search with hops=1 (no expansion)."""
        # Mock config
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        mock_config.return_value = config

        # Mock single-hop search results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        # Perform search
        results = self.searcher.search(
            query="test query", k=2, search_mode="hybrid", hops=1
        )

        # Should return initial results directly (no expansion or reranking)
        assert results == initial_results[:2]
        self.mock_single_hop_callback.assert_called_once()
        self.mock_dense_index.get_similar_chunks_batched.assert_not_called()
        self.mock_reranking_engine.rerank_by_query.assert_not_called()

    @patch("search.multi_hop_searcher._get_config_via_service_locator")
    def test_search_multi_hop(self, mock_config):
        """Test multi-hop search with expansion and reranking."""
        # Mock config
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        mock_config.return_value = config

        # Mock query embedding
        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # Mock single-hop search results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        # Mock batched search results
        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results

        # Mock reranking results
        final_results = [
            SearchResult(chunk_id="chunk1", score=0.95, metadata={}),
            SearchResult(chunk_id="chunk3", score=0.85, metadata={}),
        ]
        self.mock_reranking_engine.rerank_by_query.return_value = final_results

        # Perform search
        results = self.searcher.search(
            query="test query",
            k=2,
            search_mode="hybrid",
            hops=2,
            expansion_factor=0.3,
        )

        # Verify full pipeline executed
        assert results == final_results
        self.mock_single_hop_callback.assert_called_once()
        self.mock_dense_index.get_similar_chunks_batched.assert_called_once()
        self.mock_reranking_engine.rerank_by_query.assert_called_once()

    @patch("search.multi_hop_searcher._get_config_via_service_locator")
    def test_search_no_initial_results(self, mock_config):
        """Test multi-hop search when no initial results found."""
        # Mock config
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        mock_config.return_value = config

        # Mock empty initial results
        self.mock_single_hop_callback.return_value = []

        # Perform search
        results = self.searcher.search(query="test query", k=5, hops=2)

        # Should return empty list
        assert results == []
        self.mock_single_hop_callback.assert_called_once()
        # No expansion or reranking should occur
        self.mock_dense_index.get_similar_chunks_batched.assert_not_called()
        self.mock_reranking_engine.rerank_by_query.assert_not_called()

    @patch("search.multi_hop_searcher._get_config_via_service_locator")
    def test_search_embedding_cache(self, mock_config):
        """Test that query embedding is cached for reuse."""
        # Mock config
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        mock_config.return_value = config

        # Mock query embedding
        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # Mock initial results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        # Perform search with semantic mode
        self.searcher.search(query="test query", k=2, search_mode="semantic", hops=1)

        # Verify embedding was computed once
        self.mock_embedder.embed_query.assert_called_once_with("test query")

        # Verify embedding was passed to single-hop search
        call_kwargs = self.mock_single_hop_callback.call_args[1]
        assert "query_embedding" in call_kwargs
        assert np.array_equal(call_kwargs["query_embedding"], query_emb)

    def test_search_bm25_mode_no_embedding(self):
        """Test that BM25 mode doesn't compute embeddings."""
        # Mock config
        with patch(
            "search.multi_hop_searcher._get_config_via_service_locator"
        ) as mock_config:
            config = MagicMock()
            config.multi_hop.initial_k_multiplier = 2.0
            mock_config.return_value = config

            # Mock initial results
            initial_results = [
                SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            ]
            self.mock_single_hop_callback.return_value = initial_results

            # Perform search with BM25 mode
            self.searcher.search(query="test query", k=2, search_mode="bm25", hops=1)

            # Verify no embedding was computed
            self.mock_embedder.embed_query.assert_not_called()
