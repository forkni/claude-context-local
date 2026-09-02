"""Tests for multi-hop search expansion functionality.

Extracted from test_hybrid_search.py (Phase 3.4 refactoring).
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from search.config import SearchConfig
from search.multi_hop_searcher import MultiHopSearcher
from search.reranker import SearchResult
from search.types import RetrievalRequest


def _request(query="test query", k=2, search_mode="hybrid", config=None, filters=None):
    """Build a RetrievalRequest for MultiHopSearcher.search tests.

    config defaults to a bare MagicMock — search() no longer calls
    get_search_config() itself, so a test that used to patch
    that function now sets up its config Mock and hands it here instead.
    """
    return RetrievalRequest(
        query=query,
        k=k,
        search_mode=search_mode,
        bm25_weight=0.35,
        dense_weight=0.65,
        min_bm25_score=0.0,
        use_parallel=True,
        filters=filters,
        config=config if config is not None else MagicMock(),
    )


class TestMultiHopSearcher:
    """Test multi-hop search expansion functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedder = MagicMock()
        self.mock_dense_index = MagicMock()
        self.mock_single_hop_callback = MagicMock()
        self.mock_reranking_engine = MagicMock()
        self.mock_graph_storage = MagicMock()

        self.searcher = MultiHopSearcher(
            embedder=self.mock_embedder,
            dense_index=self.mock_dense_index,
            single_hop_callback=self.mock_single_hop_callback,
            reranking_engine=self.mock_reranking_engine,
            graph_storage=self.mock_graph_storage,
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

    def test_validate_params_excessive_hops(self):
        """Test parameter validation caps excessive hops at 20."""
        hops, expansion = self.searcher.validate_params(hops=100, expansion_factor=0.3)
        assert hops == 20
        assert expansion == 0.3

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

        # Mock get_chunk_by_id (returns inner metadata dict)
        def mock_get_chunk_by_id(chunk_id):
            metadata_map = {
                "chunk1": {"file": "test.py"},
                "chunk2": {"file": "other.py"},
                "chunk3": {"file": "test.py"},
            }
            return metadata_map.get(chunk_id)

        self.mock_dense_index.get_chunk_by_id.side_effect = mock_get_chunk_by_id

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
        self.mock_dense_index.get_chunk_by_id.assert_not_called()

    def test_search_single_hop(self):
        """Test multi-hop search with hops=1 (no expansion)."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False

        # Mock single-hop search results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        # Perform search
        results = self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=1,
        )

        # Should return initial results directly (no expansion or reranking)
        assert results == initial_results[:2]
        self.mock_single_hop_callback.assert_called_once()
        self.mock_dense_index.get_similar_chunks_batched.assert_not_called()
        self.mock_reranking_engine.rerank_by_query.assert_not_called()

    def test_search_multi_hop(self):
        """Test multi-hop search with expansion and reranking."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False

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
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        # Verify full pipeline executed
        assert results == final_results
        self.mock_single_hop_callback.assert_called_once()
        self.mock_dense_index.get_similar_chunks_batched.assert_called_once()
        self.mock_reranking_engine.rerank_by_query.assert_called_once()

    def test_search_multi_hop_tags_hop1_rank(self):
        """Hop-1 survivors get metadata["hop1_rank"] = 1-based rank, so a
        downstream rerank-window reserve can identify them after the merged
        pool's score-scale sort (:270 in reranking_engine.py) reorders them
        away from hop-1 order."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results
        self.mock_reranking_engine.rerank_by_query.return_value = initial_results

        self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        assert initial_results[0].metadata["hop1_rank"] == 1
        assert initial_results[1].metadata["hop1_rank"] == 2

    def test_search_multi_hop_threads_hop1_reserved_slots(self):
        """The merge-pool rerank call passes config.reranker.hop1_reserved_slots
        through to RerankingEngine.rerank_by_query — the only call site that
        does (ego-tail calls in HybridSearcher keep the parameter's 0 default)."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False
        config.reranker.hop1_reserved_slots = 5

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results
        self.mock_reranking_engine.rerank_by_query.return_value = initial_results

        self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        call_kwargs = self.mock_reranking_engine.rerank_by_query.call_args.kwargs
        assert call_kwargs["window"].hop1_reserved_slots == 5

    def test_search_multi_hop_threads_merged_pool_policy(self):
        """The merge-pool rerank call passes config.reranker.merged_pool_policy
        through to RerankingEngine.rerank_by_query — the only call site that
        does (ego-tail calls in HybridSearcher keep the parameter's "score"
        default)."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False
        config.reranker.merged_pool_policy = "channel_priority"

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results
        self.mock_reranking_engine.rerank_by_query.return_value = initial_results

        self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        call_kwargs = self.mock_reranking_engine.rerank_by_query.call_args.kwargs
        assert call_kwargs["window"].merged_pool_policy == "channel_priority"

    def test_search_multi_hop_threads_graph_hop_window_cap(self):
        """The merge-pool rerank call passes config.reranker.graph_hop_window_cap
        through to RerankingEngine.rerank_by_query — the only call site that
        does (ego-tail calls in HybridSearcher keep the parameter's 0
        default)."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False
        config.reranker.graph_hop_window_cap = 3

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results
        self.mock_reranking_engine.rerank_by_query.return_value = initial_results

        self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        call_kwargs = self.mock_reranking_engine.rerank_by_query.call_args.kwargs
        assert call_kwargs["window"].graph_hop_window_cap == 3

    def test_search_multi_hop_threads_graph_hop_unscored_true_when_a1_off(self):
        """search() declares graph_hop_unscored=True to rerank_by_query when
        the A1 call-evidence scorer is off — the same gate _graph_expand
        itself reads (ADR-0039) — since every graph_hop candidate in this
        pool then carries the fabricated 0.0 placeholder, not a real
        score."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False
        config.graph_enhanced.graph_hop_call_evidence_enabled = False

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results
        self.mock_reranking_engine.rerank_by_query.return_value = initial_results

        self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        call_kwargs = self.mock_reranking_engine.rerank_by_query.call_args.kwargs
        assert call_kwargs["window"].graph_hop_unscored is True

    def test_search_multi_hop_threads_graph_hop_unscored_false_when_a1_on(self):
        """search() declares graph_hop_unscored=False when the A1
        call-evidence scorer is on — those graph_hop candidates carry real
        anchor-conditioned scores, so the plain score sort (this arm's
        already-measured behaviour, unchanged by ADR-0039) still applies."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False
        config.graph_enhanced.graph_hop_call_evidence_enabled = True

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results
        self.mock_reranking_engine.rerank_by_query.return_value = initial_results

        self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        call_kwargs = self.mock_reranking_engine.rerank_by_query.call_args.kwargs
        assert call_kwargs["window"].graph_hop_unscored is False

    def test_search_multi_hop_single_pass_skips_rerank(self):
        """Q3 single_pass: merge keeps fusion/expansion score order and
        truncates to k without calling the neural reranker."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = True

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.8, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        batched_results = {
            "chunk1": [("chunk3", 0.7, {"file": "test.py"})],
            "chunk2": [("chunk4", 0.6, {"file": "test.py"})],
        }
        self.mock_dense_index.get_similar_chunks_batched.return_value = batched_results

        results = self.searcher.search(
            _request(query="test query", k=2, search_mode="hybrid", config=config),
            hops=2,
            expansion_factor=0.3,
        )

        self.mock_reranking_engine.rerank_by_query.assert_not_called()
        assert len(results) == 2
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)
        assert results[0].chunk_id == "chunk1"

    def test_search_no_initial_results(self):
        """Test multi-hop search when no initial results found."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False

        # Mock empty initial results
        self.mock_single_hop_callback.return_value = []

        # Perform search
        results = self.searcher.search(
            _request(query="test query", k=5, config=config), hops=2
        )

        # Should return empty list
        assert results == []
        self.mock_single_hop_callback.assert_called_once()
        # No expansion or reranking should occur
        self.mock_dense_index.get_similar_chunks_batched.assert_not_called()
        self.mock_reranking_engine.rerank_by_query.assert_not_called()

    def test_search_embedding_cache(self):
        """Test that query embedding is cached for reuse."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False

        # Mock query embedding
        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # Mock initial results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        # Perform search with semantic mode
        self.searcher.search(
            _request(query="test query", k=2, search_mode="semantic", config=config),
            hops=1,
        )

        # Verify embedding was computed once
        self.mock_embedder.embed_query.assert_called_once_with("test query")

        # Verify embedding was passed to single-hop search
        call_kwargs = self.mock_single_hop_callback.call_args[1]
        assert "query_embedding" in call_kwargs
        assert np.array_equal(call_kwargs["query_embedding"], query_emb)

    def test_search_bm25_mode_no_embedding(self):
        """Test that BM25 mode doesn't compute embeddings."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.reranker.single_pass = False

        # Mock initial results
        initial_results = [
            SearchResult(chunk_id="chunk1", score=0.9, metadata={}),
        ]
        self.mock_single_hop_callback.return_value = initial_results

        # Perform search with BM25 mode
        self.searcher.search(
            _request(query="test query", k=2, search_mode="bm25", config=config),
            hops=1,
        )

        # Verify no embedding was computed
        self.mock_embedder.embed_query.assert_not_called()

    # Phase 3 Tests: Graph-based expansion

    def test_graph_expand_discovers_neighbors(self):
        """Test graph expansion finds graph neighbors and adds to results."""
        initial_results = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]
        all_chunk_ids = {"src/a.py:1-10:function:foo"}
        all_results = {"src/a.py:1-10:function:foo": initial_results[0]}

        # Mock graph neighbors (returns set[str])
        self.mock_graph_storage.get_neighbors_ranked.return_value = {
            "src/b.py:20-30:function:bar",
            "Exception",  # symbol_name node, should be filtered
        }

        # Mock metadata lookup (get_chunk_by_id returns inner dict)
        self.mock_dense_index.get_chunk_by_id.return_value = {
            "file": "src/b.py",
            "type": "function",
        }

        timings = self.searcher._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=5,
            k=5,
        )

        assert "src/b.py:20-30:function:bar" in all_chunk_ids
        assert "Exception" not in all_chunk_ids  # Filtered out
        assert all_results["src/b.py:20-30:function:bar"].source == "graph_hop"
        assert "graph" in timings

    def test_graph_expand_no_graph_storage(self):
        """Test graph expansion gracefully handles missing graph_storage."""
        self.searcher.graph_storage = None

        initial_results = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]
        all_chunk_ids = {"src/a.py:1-10:function:foo"}
        all_results = {"src/a.py:1-10:function:foo": initial_results[0]}

        timings = self.searcher._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=5,
            k=5,
        )

        assert timings == {}
        assert len(all_results) == 1  # No new results added

    def test_graph_expand_filters_symbol_nodes(self):
        """Test that symbol_name nodes (< 3 colons) are filtered out."""
        initial_results = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]
        all_chunk_ids = {"src/a.py:1-10:function:foo"}
        all_results = {"src/a.py:1-10:function:foo": initial_results[0]}

        self.mock_graph_storage.get_neighbors_ranked.return_value = {
            "BaseClass",  # 0 colons - symbol
            "os.path",  # 0 colons - symbol
            "module:func",  # 1 colon  - not a chunk
        }

        self.searcher._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=5,
            k=5,
        )

        assert len(all_results) == 1  # No new results added

    def test_graph_expand_metadata_not_found(self):
        """Test neighbor is skipped if metadata not found."""
        initial_results = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]
        all_chunk_ids = {"src/a.py:1-10:function:foo"}
        all_results = {"src/a.py:1-10:function:foo": initial_results[0]}

        # Neighbor exists in graph
        self.mock_graph_storage.get_neighbors_ranked.return_value = {
            "src/orphan.py:1-10:function:bar",
        }

        # But not in search index (get_chunk_by_id returns None)
        self.mock_dense_index.get_chunk_by_id.return_value = None

        self.searcher._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=5,
            k=5,
        )

        assert len(all_results) == 1  # Neighbor was skipped
        assert "src/orphan.py:1-10:function:bar" not in all_chunk_ids

    def test_graph_expand_truncates_by_ranked_order(self):
        """expansion_k truncation follows get_neighbors_ranked's list order,
        not an arbitrary subset. Regression case for fix #3: before the
        get_neighbors -> get_neighbors_ranked switch, `added_for_source >=
        expansion_k` truncated by Python's set-iteration order instead of
        this priority/discovery order."""
        initial_results = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]
        all_chunk_ids = {"src/a.py:1-10:function:foo"}
        all_results = {"src/a.py:1-10:function:foo": initial_results[0]}

        ranked_neighbors = [
            "src/b.py:1-10:function:first",
            "src/c.py:1-10:function:second",
            "src/d.py:1-10:function:third",
            "src/e.py:1-10:function:fourth",
        ]
        self.mock_graph_storage.get_neighbors_ranked.return_value = ranked_neighbors
        self.mock_dense_index.get_chunk_by_id.return_value = {"file": "src/x.py"}

        self.searcher._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=2,
            k=5,
        )

        # Only the first two neighbors in ranked order survive truncation.
        assert "src/b.py:1-10:function:first" in all_chunk_ids
        assert "src/c.py:1-10:function:second" in all_chunk_ids
        assert "src/d.py:1-10:function:third" not in all_chunk_ids
        assert "src/e.py:1-10:function:fourth" not in all_chunk_ids

    def test_graph_expand_truncation_deterministic_across_repeated_calls(self):
        """Two independent expansions over the identical ranked-neighbor list
        truncate to the identical subset -- the property that regressed
        under set-iteration truncation across process restarts."""
        ranked_neighbors = [
            "src/b.py:1-10:function:first",
            "src/c.py:1-10:function:second",
            "src/d.py:1-10:function:third",
        ]
        self.mock_graph_storage.get_neighbors_ranked.return_value = ranked_neighbors
        self.mock_dense_index.get_chunk_by_id.return_value = {"file": "src/x.py"}

        def _run():
            initial_results = [
                SearchResult(
                    chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}
                ),
            ]
            all_chunk_ids = {"src/a.py:1-10:function:foo"}
            all_results = {"src/a.py:1-10:function:foo": initial_results[0]}
            self.searcher._graph_expand(
                initial_results=initial_results,
                all_chunk_ids=all_chunk_ids,
                all_results=all_results,
                expansion_k=2,
                k=5,
            )
            return set(all_results.keys())

        first = _run()
        second = _run()
        assert (
            first
            == second
            == {
                "src/a.py:1-10:function:foo",
                "src/b.py:1-10:function:first",
                "src/c.py:1-10:function:second",
            }
        )

    def test_hybrid_expand_runs_both(self):
        """Test hybrid expansion runs graph first, then semantic."""
        initial_results = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]
        all_chunk_ids = {"src/a.py:1-10:function:foo"}
        all_results = {"src/a.py:1-10:function:foo": initial_results[0]}

        # Graph returns one neighbor
        self.mock_graph_storage.get_neighbors_ranked.return_value = {
            "src/b.py:20-30:function:bar",
        }
        self.mock_dense_index.metadata_store.get.return_value = {
            "index_id": 5,
            "metadata": {"file": "src/b.py"},
        }

        # Semantic returns a different neighbor
        self.mock_dense_index.get_similar_chunks_batched.return_value = {
            "src/a.py:1-10:function:foo": [
                ("src/c.py:40-50:function:baz", 0.7, {"file": "src/c.py"}),
            ],
        }

        self.searcher._hybrid_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=5,
            hops=2,
            k=5,
        )

        # Both neighbors should be found
        assert "src/b.py:20-30:function:bar" in all_chunk_ids
        assert "src/c.py:40-50:function:baz" in all_chunk_ids
        assert all_results["src/b.py:20-30:function:bar"].source == "graph_hop"
        assert all_results["src/c.py:40-50:function:baz"].source == "multi_hop"

    def test_search_dispatches_graph_mode(self):
        """Test search() dispatches to graph expansion when mode is 'graph'."""
        config = MagicMock()
        config.multi_hop.initial_k_multiplier = 2.0
        config.multi_hop.multi_hop_mode = "graph"
        config.reranker.single_pass = False
        # Mock configs must disable A1 scoring explicitly — a truthy Mock attr
        # would otherwise route _graph_expand into the scoring path. A2's
        # traversal knobs likewise need real values, not Mock attrs.
        config.graph_enhanced.graph_hop_call_evidence_enabled = False
        config.graph_enhanced.min_traversal_confidence = 0.0
        config.graph_enhanced.traversal_confidence_weighting_enabled = False
        config.graph_enhanced.drop_ambiguous_traversal_edges = False

        # Provide initial results from hop 1
        self.mock_single_hop_callback.return_value = [
            SearchResult(chunk_id="src/a.py:1-10:function:foo", score=0.9, metadata={}),
        ]

        # Graph returns neighbor
        self.mock_graph_storage.get_neighbors_ranked.return_value = {
            "src/b.py:20-30:function:bar",
        }
        self.mock_dense_index.metadata_store.get.return_value = {
            "index_id": 5,
            "metadata": {"file": "src/b.py"},
        }

        # Reranker returns whatever it gets
        self.mock_reranking_engine.rerank_by_query.side_effect = lambda **kwargs: (
            kwargs["results"]
        )

        self.searcher.search(_request(query="test", k=5, config=config), hops=2)

        # Verify graph_storage.get_neighbors_ranked was called (graph mode)
        self.mock_graph_storage.get_neighbors_ranked.assert_called()
        # Verify batched search was NOT called (not semantic mode)
        self.mock_dense_index.get_similar_chunks_batched.assert_not_called()


class TestIntentAdaptiveWeights:
    """Tests for A1: intent-driven edge weight profiles."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedder = MagicMock()
        self.mock_dense_index = MagicMock()
        self.mock_single_hop_callback = MagicMock()
        self.mock_reranking_engine = MagicMock()
        self.mock_graph_storage = MagicMock()

        self.searcher = MultiHopSearcher(
            embedder=self.mock_embedder,
            dense_index=self.mock_dense_index,
            single_hop_callback=self.mock_single_hop_callback,
            reranking_engine=self.mock_reranking_engine,
            graph_storage=self.mock_graph_storage,
        )

    def test_graph_expand_uses_custom_weights(self):
        """_graph_expand() should pass custom edge_weights to get_neighbors_ranked()."""

        custom_weights = {"calls": 0.5, "imports": 1.0}

        # Setup: get_neighbors_ranked returns empty set
        self.mock_graph_storage.get_neighbors_ranked.return_value = set()

        # Create mock result
        mock_result = MagicMock()
        mock_result.chunk_id = "test.py:1-10:function:foo"

        self.searcher._graph_expand(
            initial_results=[mock_result],
            all_chunk_ids=set(),
            all_results={},
            expansion_k=5,
            k=5,
            edge_weights=custom_weights,
        )

        # Verify get_neighbors_ranked was called with custom weights
        policy = self.mock_graph_storage.get_neighbors_ranked.call_args.args[1]
        assert policy.edge_weights == custom_weights

    def test_graph_expand_default_weights_when_none(self):
        """_graph_expand() should use DEFAULT_EDGE_WEIGHTS when edge_weights=None."""
        from graph.graph_storage import DEFAULT_EDGE_WEIGHTS

        # Setup: get_neighbors_ranked returns empty set
        self.mock_graph_storage.get_neighbors_ranked.return_value = set()

        # Create mock result
        mock_result = MagicMock()
        mock_result.chunk_id = "test.py:1-10:function:foo"

        self.searcher._graph_expand(
            initial_results=[mock_result],
            all_chunk_ids=set(),
            all_results={},
            expansion_k=5,
            k=5,
            edge_weights=None,
        )

        # Verify get_neighbors_ranked was called with DEFAULT_EDGE_WEIGHTS
        policy = self.mock_graph_storage.get_neighbors_ranked.call_args.args[1]
        assert policy.edge_weights == DEFAULT_EDGE_WEIGHTS

    def test_search_threads_edge_weights(self):
        """search() should thread edge_weights to _graph_expand()."""
        custom_weights = {"calls": 0.3, "imports": 0.9}

        # Mock the single_hop_callback to return initial results
        mock_result = SearchResult(
            chunk_id="test.py:1-10:function:foo",
            score=0.9,
            metadata={},
            source="initial",
            rank=1,
        )
        self.mock_single_hop_callback.return_value = [mock_result]

        # Mock reranker to return results as-is
        self.mock_reranking_engine.rerank_by_query.side_effect = lambda **kwargs: (
            kwargs["results"]
        )

        # Mock graph_storage.get_neighbors_ranked to return empty set
        self.mock_graph_storage.get_neighbors_ranked.return_value = set()

        # Patch _graph_expand to verify it receives edge_weights
        with patch.object(self.searcher, "_graph_expand") as mock_expand:
            mock_expand.return_value = {}  # timings dict

            # Search with custom edge_weights (real config: multi_hop_mode
            # defaults to "hybrid", which dispatches through _hybrid_expand
            # into _graph_expand — the method under test here)
            self.searcher.search(
                _request(query="test", k=5, config=SearchConfig()),
                hops=2,
                edge_weights=custom_weights,
            )

            # Verify _graph_expand was called with edge_weights
            assert mock_expand.called
            call_args = mock_expand.call_args
            assert call_args.kwargs.get("edge_weights") == custom_weights


class TestCallEvidenceScoring:
    """Tests for A1: call-evidence scoring of graph-hop candidates.

    Default-off contract: with graph_hop_call_evidence_enabled=False (or no
    config threaded at all), _graph_expand assigns the legacy 0.0 score.
    Enabled: score = min(anchor * cosine + call_evidence, anchor), with
    cosines from batched FAISS reconstruction and a 0.5 decay fallback.
    """

    NEIGHBOR = "src/b.py:20-30:function:bar"
    ANCHOR = "src/a.py:1-10:function:foo"

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedder = MagicMock()
        self.mock_dense_index = MagicMock()
        self.mock_single_hop_callback = MagicMock()
        self.mock_reranking_engine = MagicMock()
        self.mock_graph_storage = MagicMock()

        self.searcher = MultiHopSearcher(
            embedder=self.mock_embedder,
            dense_index=self.mock_dense_index,
            single_hop_callback=self.mock_single_hop_callback,
            reranking_engine=self.mock_reranking_engine,
            graph_storage=self.mock_graph_storage,
        )

    def _expand(self, config=None, query_embedding=None, anchor_score=0.8):
        """Run _graph_expand over one anchor with one graph neighbor."""
        initial_results = [
            SearchResult(chunk_id=self.ANCHOR, score=anchor_score, metadata={}),
        ]
        all_chunk_ids = {self.ANCHOR}
        all_results = {self.ANCHOR: initial_results[0]}

        self.mock_graph_storage.get_neighbors_ranked.return_value = {self.NEIGHBOR}
        self.mock_dense_index.get_chunk_by_id.return_value = {"file": "src/b.py"}

        self.searcher._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=5,
            k=5,
            query_embedding=query_embedding,
            config=config,
        )
        return all_results

    def test_default_config_scores_zero(self):
        """Byte-identity: real default config keeps the legacy 0.0 score and
        never enters the scoring helper."""
        with patch.object(self.searcher, "_score_graph_candidates") as mock_score:
            all_results = self._expand(config=SearchConfig())
        assert all_results[self.NEIGHBOR].score == 0.0
        assert all_results[self.NEIGHBOR].source == "graph_hop"
        mock_score.assert_not_called()

    def test_no_config_scores_zero(self):
        """Byte-identity: legacy callers that thread no config get 0.0."""
        all_results = self._expand(config=None)
        assert all_results[self.NEIGHBOR].score == 0.0

    def test_enabled_scores_on_anchor_scale(self):
        """Enabled: score = anchor * cosine + evidence, below the anchor cap."""
        config = SearchConfig()
        config.graph_enhanced.graph_hop_call_evidence_enabled = True
        config.graph_enhanced.graph_hop_call_evidence_lambda = 0.05

        query_embedding = np.array([1.0, 0.0, 0.0])
        self.mock_dense_index.chunk_ids = [self.NEIGHBOR]
        self.mock_dense_index._faiss_index.reconstruct.return_value = np.array(
            [0.25, 0.5, 0.0]
        )

        with patch("graph.graph_queries.GraphQueryEngine") as mock_engine_cls:
            mock_engine_cls.return_value.score_call_evidence.return_value = 0.1
            all_results = self._expand(
                config=config, query_embedding=query_embedding, anchor_score=0.8
            )

        # 0.8 * 0.25 + 0.1 = 0.3, under the 0.8 anchor cap
        assert all_results[self.NEIGHBOR].score == pytest.approx(0.3)
        # Evidence is conditioned on the hop-1 snapshot, not other candidates
        evidence_call = mock_engine_cls.return_value.score_call_evidence.call_args
        assert evidence_call.args[0] == self.NEIGHBOR
        assert evidence_call.args[1] == frozenset({self.ANCHOR})

    def test_enabled_caps_at_anchor_score(self):
        """A candidate never outranks its own anchor, however large the
        evidence term is."""
        config = SearchConfig()
        config.graph_enhanced.graph_hop_call_evidence_enabled = True

        query_embedding = np.array([1.0, 0.0, 0.0])
        self.mock_dense_index.chunk_ids = [self.NEIGHBOR]
        self.mock_dense_index._faiss_index.reconstruct.return_value = np.array(
            [1.0, 0.0, 0.0]
        )

        with patch("graph.graph_queries.GraphQueryEngine") as mock_engine_cls:
            mock_engine_cls.return_value.score_call_evidence.return_value = 5.0
            all_results = self._expand(
                config=config, query_embedding=query_embedding, anchor_score=0.8
            )

        assert all_results[self.NEIGHBOR].score == pytest.approx(0.8)

    def test_enabled_bm25_mode_uses_decay_fallback(self):
        """query_embedding is None in BM25 mode: cosine falls back to the
        0.5 decay, evidence still applies — no crash."""
        config = SearchConfig()
        config.graph_enhanced.graph_hop_call_evidence_enabled = True

        with patch("graph.graph_queries.GraphQueryEngine") as mock_engine_cls:
            mock_engine_cls.return_value.score_call_evidence.return_value = 0.1
            all_results = self._expand(
                config=config, query_embedding=None, anchor_score=0.8
            )

        # 0.8 * 0.5 + 0.1 = 0.5
        assert all_results[self.NEIGHBOR].score == pytest.approx(0.5)

    def test_scoring_failure_falls_back_to_zero(self):
        """A scoring crash degrades to the legacy 0.0, never fails the search."""
        config = SearchConfig()
        config.graph_enhanced.graph_hop_call_evidence_enabled = True

        with patch.object(
            self.searcher, "_score_graph_candidates", side_effect=RuntimeError("boom")
        ):
            all_results = self._expand(config=config)

        assert all_results[self.NEIGHBOR].score == 0.0

    def test_similarities_missing_id_gets_fallback(self):
        """Ids absent from the dense index get the 0.5 decay; mapped ids get
        their reconstructed cosine."""
        self.mock_dense_index.chunk_ids = ["known"]
        self.mock_dense_index._faiss_index.reconstruct.return_value = np.array(
            [0.9, 0.0]
        )

        sims = self.searcher._graph_candidate_similarities(
            ["known", "unknown"], np.array([1.0, 0.0])
        )

        assert sims[0] == pytest.approx(0.9)
        assert sims[1] == 0.5

    def test_traversal_confidence_defaults_are_noop(self):
        """A2 byte-identity: a default config threads floor 0.0 and weighting
        False into get_neighbors_ranked."""
        self._expand(config=SearchConfig())
        policy = self.mock_graph_storage.get_neighbors_ranked.call_args.args[1]
        assert policy.min_confidence == 0.0
        assert policy.confidence_weighting is False
        assert policy.drop_ambiguous is False

    def test_no_config_traversal_defaults(self):
        """Legacy callers threading no config get the same no-op traversal."""
        self._expand(config=None)
        policy = self.mock_graph_storage.get_neighbors_ranked.call_args.args[1]
        assert policy.min_confidence == 0.0
        assert policy.confidence_weighting is False
        assert policy.drop_ambiguous is False

    def test_traversal_confidence_threaded_from_config(self):
        """A2: config values reach get_neighbors_ranked on every anchor expansion."""
        config = SearchConfig()
        config.graph_enhanced.min_traversal_confidence = 0.7
        config.graph_enhanced.traversal_confidence_weighting_enabled = True

        self._expand(config=config)

        policy = self.mock_graph_storage.get_neighbors_ranked.call_args.args[1]
        assert policy.min_confidence == 0.7
        assert policy.confidence_weighting is True

    def test_drop_ambiguous_threaded_from_config(self):
        """drop_ambiguous_traversal_edges reaches get_neighbors_ranked."""
        config = SearchConfig()
        config.graph_enhanced.drop_ambiguous_traversal_edges = True

        self._expand(config=config)

        policy = self.mock_graph_storage.get_neighbors_ranked.call_args.args[1]
        assert policy.drop_ambiguous is True

    def test_search_threads_query_embedding_and_config(self):
        """search() threads the pre-computed query embedding and config into
        _graph_expand (hybrid mode dispatches through _hybrid_expand)."""
        config = SearchConfig()
        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        self.mock_single_hop_callback.return_value = [
            SearchResult(chunk_id=self.ANCHOR, score=0.9, metadata={}),
        ]
        self.mock_reranking_engine.rerank_by_query.side_effect = lambda **kwargs: (
            kwargs["results"]
        )
        self.mock_graph_storage.get_neighbors_ranked.return_value = set()

        with patch.object(self.searcher, "_graph_expand") as mock_expand:
            mock_expand.return_value = {}
            self.searcher.search(
                _request(query="test", k=5, search_mode="hybrid", config=config),
                hops=2,
            )

        assert mock_expand.called
        kwargs = mock_expand.call_args.kwargs
        assert np.array_equal(kwargs["query_embedding"], query_emb)
        assert kwargs["config"] is config
