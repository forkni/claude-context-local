"""Tests for hybrid search orchestrator.

Note: GPUMemoryMonitor tests have been moved to test_gpu_monitor.py (Phase 3.1 refactoring).
"""

import contextlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from search.config import SearchConfig
from search.hybrid_searcher import HybridSearcher
from utils.otel_attributes import ATTR_CAPTURE_QUERY


class TestHybridSearcher:
    """Test hybrid search orchestrator functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create mock documents and metadata
        self.documents = [
            "def calculate_sum(a, b): return a + b",
            "class UserManager: def get_user(self, user_id): return users[user_id]",
            "function processData(data) { return data.filter(x => x.valid); }",
            "SELECT name, email FROM users WHERE active = true",
            "async def fetch_data(): return await api_client.get('/data')",
        ]
        self.doc_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]
        self.embeddings = [np.random.rand(768).tolist() for _ in self.documents]
        self.metadata = {
            doc_id: {
                "language": (
                    "python" if i < 2 or i == 4 else "javascript" if i == 2 else "sql"
                ),
                "type": "function" if i in [0, 4] else "class" if i == 1 else "query",
                "lines": i + 1,
            }
            for i, doc_id in enumerate(self.doc_ids)
        }

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_initialization(self, mock_bm25, mock_dense):
        """Test hybrid searcher initialization."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        assert searcher.max_workers == 2
        assert not searcher._is_shutdown

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_context_manager(self, mock_bm25, mock_dense):
        """Test context manager functionality."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        with HybridSearcher(self.temp_dir) as searcher:
            assert not searcher._is_shutdown

        assert searcher._is_shutdown

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_is_ready_property(self, mock_bm25, mock_dense):
        """Test is_ready property."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock empty indices
        mock_bm25.return_value.is_empty = True
        mock_dense.return_value.index = None

        assert not searcher.is_ready

        # Mock non-empty indices
        mock_bm25.return_value.is_empty = False
        mock_dense_instance = Mock()
        mock_dense_instance.ntotal = 100
        mock_dense.return_value.index = mock_dense_instance

        assert searcher.is_ready

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_index_documents(self, mock_bm25, mock_dense):
        """Test document indexing."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock the indices
        bm25_mock = mock_bm25.return_value
        dense_mock = mock_dense.return_value

        # Index documents
        searcher.index_documents(
            self.documents, self.doc_ids, self.embeddings, self.metadata
        )

        # Verify BM25 indexing
        bm25_mock.index_documents.assert_called_once_with(
            self.documents, self.doc_ids, self.metadata
        )

        # Verify dense indexing
        dense_mock.add_embeddings.assert_called_once()

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_weight_change_takes_effect_without_rebuild(self, mock_bm25, mock_dense):
        """Direct proof that search_mode.bm25_weight/dense_weight are NOT
        construction_baked (Phase 2a, ADR-0018 follow-on): HybridSearcher
        takes no weight parameters at construction (hybrid_searcher.py:61-75)
        - both are resolved live from effective_config on every search() call
        (:731-739). Mutating the live config between two search() calls on
        the SAME instance, with no rebuild in between, must change the
        RetrievalRequest weights the second call is built with.
        """
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices as ready so search() reaches weight resolution.
        mock_bm25.return_value.is_empty = False
        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100

        live_config = SearchConfig()
        live_config.search_mode.bm25_weight = 0.35
        live_config.search_mode.dense_weight = 0.65
        # Force the single-hop branch so the patched _single_hop_search below
        # is what actually resolves the request - multi-hop is enabled by
        # default and would otherwise route through multi_hop_searcher instead.
        live_config.multi_hop.enabled = False

        captured_requests = []

        def fake_single_hop(request, query_embedding=None):
            captured_requests.append(request)
            return []

        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=live_config,
            ),
            patch.object(searcher, "_single_hop_search", side_effect=fake_single_hop),
        ):
            searcher.search("test query", use_parallel=False)

            # Mutate the live config in place - no HybridSearcher rebuild.
            live_config.search_mode.bm25_weight = 0.9
            live_config.search_mode.dense_weight = 0.1

            searcher.search("test query", use_parallel=False)

        assert len(captured_requests) == 2
        assert captured_requests[0].bm25_weight == 0.35
        assert captured_requests[0].dense_weight == 0.65
        assert captured_requests[1].bm25_weight == 0.9
        assert captured_requests[1].dense_weight == 0.1

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_search_not_ready(self, mock_bm25, mock_dense):
        """Test search when indices are not ready."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock empty indices
        mock_bm25.return_value.is_empty = True
        mock_dense.return_value.index = None

        results = searcher.search("test query")
        assert results == []

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_sequential_search(self, mock_bm25, mock_dense):
        """Test sequential search execution."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices as ready
        bm25_mock = mock_bm25.return_value
        bm25_mock.is_empty = False
        bm25_mock.search.return_value = [("doc1", 0.8, {"type": "function"})]

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100
        dense_mock.search.return_value = [("doc2", 0.9, {"type": "class"})]

        # Mock embedder
        with patch("embeddings.embedder.CodeEmbedder") as mock_embedder:
            embedder_mock = mock_embedder.return_value
            embedder_mock.embed_text.return_value = np.random.rand(768)

            results = searcher.search("test query", k=5, use_parallel=False)

            # Should get reranked results
            assert isinstance(results, list)
            bm25_mock.search.assert_called_once()
            dense_mock.search.assert_called_once()

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_parallel_search(self, mock_bm25, mock_dense):
        """Test parallel search execution."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices as ready
        bm25_mock = mock_bm25.return_value
        bm25_mock.is_empty = False
        bm25_mock.search.return_value = [("doc1", 0.8, {"type": "function"})]

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100
        dense_mock.search.return_value = [("doc2", 0.9, {"type": "class"})]

        # Mock embedder
        with patch("embeddings.embedder.CodeEmbedder") as mock_embedder:
            embedder_mock = mock_embedder.return_value
            embedder_mock.embed_text.return_value = np.random.rand(768)

            results = searcher.search("test query", k=5, use_parallel=True)

            # Should get reranked results
            assert isinstance(results, list)
            bm25_mock.search.assert_called_once()
            dense_mock.search.assert_called_once()

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_search_with_filters(self, mock_bm25, mock_dense):
        """Test search with filters."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices as ready
        bm25_mock = mock_bm25.return_value
        bm25_mock.is_empty = False
        bm25_mock.search.return_value = [("doc1", 0.8, {"language": "python"})]

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100
        dense_mock.search.return_value = [("doc1", 0.9, {"language": "python"})]

        # Mock embedder
        with patch("embeddings.embedder.CodeEmbedder") as mock_embedder:
            embedder_mock = mock_embedder.return_value
            embedder_mock.embed_text.return_value = np.random.rand(768)

            filters = {"language": "python"}
            searcher.search("test query", k=5, use_parallel=False, filters=filters)

            # Dense search should be called with filters
            dense_mock.search.assert_called_once()
            args, kwargs = dense_mock.search.call_args
            if len(args) >= 3:
                assert args[2] == filters
            else:
                assert kwargs.get("filters") == filters

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_search_error_handling(self, mock_bm25, mock_dense):
        """Test search error handling."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices as ready but with search errors
        bm25_mock = mock_bm25.return_value
        bm25_mock.is_empty = False
        bm25_mock.search.side_effect = Exception("BM25 search failed")

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100
        dense_mock.search.side_effect = Exception("Dense search failed")

        # Should handle errors gracefully
        results = searcher.search("test query", k=5)
        # Should return empty results when both searches fail
        assert results == []

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_stats_collection(self, mock_bm25, mock_dense):
        """Test statistics collection."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices
        bm25_mock = mock_bm25.return_value
        bm25_mock.get_stats.return_value = {"total_documents": 100}

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100

        stats = searcher.stats

        assert "bm25_stats" in stats
        assert "dense_stats" in stats
        assert "gpu_memory" in stats
        assert stats["dense_stats"]["total_vectors"] == 100

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_save_and_load_indices(self, mock_bm25, mock_dense):
        """Test saving and loading indices."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        # Setup both save methods on dense mock
        dense_mock = mock_dense.return_value
        dense_mock.save_index = Mock()
        dense_mock.save = Mock()

        searcher = HybridSearcher(self.temp_dir)

        bm25_mock = mock_bm25.return_value

        # Test saving
        searcher.save_indices()
        bm25_mock.save.assert_called_once()
        # Dense index should call save_index() first
        dense_mock.save_index.assert_called_once()

        # Test loading
        bm25_mock.load.return_value = True
        dense_mock.load.return_value = True

        success = searcher.load_indices()
        assert success

        # Note: load may be called multiple times during initialization
        assert bm25_mock.load.call_count >= 1
        assert dense_mock.load.call_count >= 1

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_search_mode_stats(self, mock_bm25, mock_dense):
        """Test search mode statistics."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Initially no searches
        stats = searcher.get_search_mode_stats()
        assert "No searches performed" in stats["message"]

        # Mock a search to generate stats
        searcher.search_executor._search_stats["total_searches"] = 10
        searcher.search_executor._search_stats["bm25_time"] = 1.0
        searcher.search_executor._search_stats["dense_time"] = 2.0
        searcher.search_executor._search_stats["rerank_time"] = 0.5

        stats = searcher.get_search_mode_stats()

        assert stats["total_searches"] == 10
        assert "average_times" in stats
        assert stats["average_times"]["bm25"] == 0.1
        assert stats["average_times"]["dense"] == 0.2
        assert stats["average_times"]["reranking"] == 0.05

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_performance_tracking(self, mock_bm25, mock_dense):
        """Test performance tracking during searches."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock indices as ready
        bm25_mock = mock_bm25.return_value
        bm25_mock.is_empty = False
        bm25_mock.search.return_value = [("doc1", 0.8, {"type": "function"})]

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100
        dense_mock.search.return_value = [("doc2", 0.9, {"type": "class"})]

        # Mock embedder
        with patch("embeddings.embedder.CodeEmbedder") as mock_embedder:
            embedder_mock = mock_embedder.return_value
            embedder_mock.embed_text.return_value = np.random.rand(768)

            # Perform searches
            initial_searches = searcher.search_executor._search_stats["total_searches"]
            searcher.search("query 1", use_parallel=False)
            searcher.search("query 2", use_parallel=False)

            # Stats should be updated
            assert (
                searcher.search_executor._search_stats["total_searches"]
                == initial_searches + 2
            )
            # In mocked environment, times might be 0, so assert type + non-negative
            # rather than a positivity threshold mocked I/O can't guarantee.
            for key in ("bm25_time", "dense_time", "rerank_time"):
                assert key in searcher.search_executor._search_stats
                value = searcher.search_executor._search_stats[key]
                assert isinstance(value, (int, float)), (
                    f"{key} should be a numeric duration, got {type(value)}"
                )
                assert value >= 0

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_batched_similar_chunks(self, mock_bm25, mock_dense):
        """Test batched similar chunks search."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100

        # Mock batched search results
        batched_results = {
            "doc1": [
                ("doc2", 0.9, {"type": "function"}),
                ("doc3", 0.8, {"type": "class"}),
            ],
            "doc2": [
                ("doc1", 0.85, {"type": "function"}),
                ("doc4", 0.75, {"type": "method"}),
            ],
        }
        dense_mock.get_similar_chunks_batched.return_value = batched_results

        # Call batched method
        result = dense_mock.get_similar_chunks_batched(["doc1", "doc2"], k=2)

        assert result == batched_results
        assert "doc1" in result
        assert "doc2" in result
        assert len(result["doc1"]) == 2
        assert len(result["doc2"]) == 2

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_batched_vs_individual_consistency(self, mock_bm25, mock_dense):
        """Test that batched search produces same results as individual searches."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100

        # Mock individual search results
        individual_results_1 = [("doc2", 0.9, {"type": "function"})]
        individual_results_2 = [("doc1", 0.85, {"type": "class"})]

        dense_mock.get_similar_chunks.side_effect = [
            individual_results_1,
            individual_results_2,
        ]

        # Mock batched search to return same results
        batched_results = {
            "doc1": individual_results_1,
            "doc2": individual_results_2,
        }
        dense_mock.get_similar_chunks_batched.return_value = batched_results

        # Call both methods
        individual_1 = dense_mock.get_similar_chunks("doc1", k=1)
        individual_2 = dense_mock.get_similar_chunks("doc2", k=1)
        batched = dense_mock.get_similar_chunks_batched(["doc1", "doc2"], k=1)

        # Results should match
        assert batched["doc1"] == individual_1
        assert batched["doc2"] == individual_2

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_batched_empty_input(self, mock_bm25, mock_dense):
        """Test batched search with empty input."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100

        # Mock empty result
        dense_mock.get_similar_chunks_batched.return_value = {}

        result = dense_mock.get_similar_chunks_batched([], k=5)

        assert result == {}

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_find_similar_default_forwards_exclude_false(self, mock_bm25, mock_dense):
        """Default call forwards exclude_same_file=False (byte-identical path)."""
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.get_similar_chunks.return_value = []

        searcher.find_similar_to_chunk("doc1", k=3)

        dense_mock.get_similar_chunks.assert_called_once_with(
            "doc1", 3, exclude_same_file=False
        )

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_find_similar_forwards_exclude_same_file(self, mock_bm25, mock_dense):
        """exclude_same_file=True is forwarded to the dense index."""
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.get_similar_chunks.return_value = []

        searcher.find_similar_to_chunk("doc1", k=3, exclude_same_file=True)

        dense_mock.get_similar_chunks.assert_called_once_with(
            "doc1", 3, exclude_same_file=True
        )

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_find_similar_exclude_composes_with_rerank_fetch_k(
        self, mock_bm25, mock_dense
    ):
        """rerank=True keeps the 2x fetch_k; exclusion overfetch lives in the indexer."""
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.get_similar_chunks.return_value = []

        searcher.find_similar_to_chunk("doc1", k=3, rerank=True, exclude_same_file=True)

        dense_mock.get_similar_chunks.assert_called_once_with(
            "doc1", 6, exclude_same_file=True
        )

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_multi_hop_uses_batched_search(self, mock_bm25, mock_dense):
        """Test that multi-hop expansion uses batched search."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Enable multi-hop in config
        searcher.enable_multi_hop = True
        searcher.multi_hop_hops = 2

        # Mock indices as ready
        bm25_mock = mock_bm25.return_value
        bm25_mock.is_empty = False
        bm25_mock.search.return_value = [
            ("doc1", 0.9, {"type": "function", "chunk_id": "doc1"}),
            ("doc2", 0.8, {"type": "class", "chunk_id": "doc2"}),
        ]

        dense_mock = mock_dense.return_value
        dense_mock.index = Mock()
        dense_mock.index.ntotal = 100
        dense_mock.search.return_value = [
            ("doc1", 0.9, {"type": "function", "chunk_id": "doc1"}),
            ("doc2", 0.8, {"type": "class", "chunk_id": "doc2"}),
        ]

        # Mock batched similar chunks
        batched_results = {
            "doc1": [("doc3", 0.85, {"type": "method", "chunk_id": "doc3"})],
            "doc2": [("doc4", 0.75, {"type": "function", "chunk_id": "doc4"})],
        }
        dense_mock.get_similar_chunks_batched.return_value = batched_results

        # Mock embedder
        with patch("embeddings.embedder.CodeEmbedder") as mock_embedder:
            embedder_mock = mock_embedder.return_value
            embedder_mock.embed_text.return_value = np.random.rand(768)

            # Perform search with multi-hop enabled
            results = searcher.search("test query", k=5, use_parallel=False)

            # Verify batched search was called
            dense_mock.get_similar_chunks_batched.assert_called()

            # Results should include multi-hop discoveries
            assert isinstance(results, list)

    @patch("search.index_sync.BM25Index")
    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_resync_bm25_from_dense_success(
        self, mock_bm25_hs, mock_dense, mock_bm25_sync
    ):
        """Test successful BM25 resync from dense metadata."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Setup dense index with chunk IDs and metadata
        dense_mock = mock_dense.return_value
        dense_mock.chunk_ids = ["chunk1", "chunk2", "chunk3"]
        dense_mock.metadata_store.get = Mock(
            side_effect=[
                {"metadata": {"bm25_text": "def func1(): pass"}},
                {"metadata": {"bm25_text": "class MyClass: pass"}},
                {"metadata": {"bm25_text": "async def async_func(): pass"}},
            ]
        )

        # Replace dense_index in both HybridSearcher and IndexSynchronizer
        searcher.dense_index = dense_mock
        searcher.index_sync.dense_index = dense_mock

        # Mock BM25Index for the rebuild (new instance created in resync)
        new_bm25_mock = Mock()
        new_bm25_mock.size = 3
        mock_bm25_sync.return_value = new_bm25_mock

        # Call resync
        count = searcher.resync_bm25_from_dense()

        # Verify
        assert count == 3
        new_bm25_mock.index_documents.assert_called_once()
        new_bm25_mock.save.assert_called_once()

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_resync_bm25_from_dense_empty_dense_index(self, mock_bm25, mock_dense):
        """Test resync returns 0 when dense index has no chunks."""
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Setup empty dense index
        dense_mock = mock_dense.return_value
        dense_mock.chunk_ids = []  # No chunks
        searcher.dense_index = dense_mock

        count = searcher.resync_bm25_from_dense()

        assert count == 0

    @patch("search.index_sync.BM25Index")
    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_resync_bm25_from_dense_no_content_in_metadata(
        self, mock_bm25_hs, mock_dense, mock_bm25_sync
    ):
        """Test resync handles chunks with missing content gracefully."""
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock.chunk_ids = ["chunk1", "chunk2"]
        dense_mock.metadata_store.get = Mock(
            side_effect=[
                {"metadata": {"bm25_text": "valid content"}},
                {"metadata": {}},  # No bm25_text key
            ]
        )
        searcher.dense_index = dense_mock
        searcher.index_sync.dense_index = dense_mock

        # Mock BM25Index for rebuild (in index_sync)
        new_bm25_mock = Mock()
        new_bm25_mock.size = 1  # Only 1 chunk has valid content
        mock_bm25_sync.return_value = new_bm25_mock

        count = searcher.resync_bm25_from_dense()

        # Should only sync the chunk with valid content
        assert count == 1

    @patch("search.index_sync.CodeIndexManager")
    @patch("search.index_sync.BM25Index")
    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_clear_index_clears_both_indices(
        self, mock_bm25_hs, mock_dense_hs, mock_bm25_sync, mock_dense_sync
    ):
        """Test clear_index clears both BM25 and dense indices in place (ADR-0025)."""
        # Setup mocks for HybridSearcher __init__
        mock_bm25_hs.return_value = Mock(name="BM25_1")
        mock_dense_instance_1 = Mock(name="Dense_1")
        mock_dense_instance_1.index = None
        # A1's fail-fast probe (index_sync.py:clear_index) calls
        # os.replace() on this path before destroying BM25/FAISS state, so
        # it must be a real path like production's CodeIndexManager sets,
        # not an unconfigured Mock attribute.
        mock_dense_instance_1.metadata_path = Path(self.temp_dir) / "metadata.db"
        mock_dense_hs.return_value = mock_dense_instance_1

        searcher = HybridSearcher(self.temp_dir)

        # Store original instances
        original_bm25 = searcher.bm25_index
        original_dense = searcher.dense_index

        # Clear indices
        searcher.clear_index()

        # ADR-0025: index object identity is stable across a clear -- no swap,
        # no repair list. bm25_index.clear() and dense_index.clear_index() are
        # called on the *same* objects instead of new ones being constructed.
        original_dense.preflight_clear.assert_called_once()
        original_bm25.clear.assert_called_once()
        original_dense.clear_index.assert_called_once()
        assert searcher.bm25_index is original_bm25
        assert searcher.dense_index is original_dense

    @patch("search.index_sync.CodeIndexManager")
    @patch("search.index_sync.BM25Index")
    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_clear_index_preserves_collaborator_identity(
        self, mock_bm25_hs, mock_dense_hs, mock_bm25_sync, mock_dense_sync
    ):
        """ADR-0025 invariant: every collaborator that cached bm25_index/
        dense_index at construction time still resolves to the *same*
        objects after clear_index() -- search_executor, multi_hop_searcher
        and reranking_engine included. This is the regression commit
        db4c181 shipped without coverage: search_executor.bm25_index in
        particular used to go stale after a resync because nothing repaired
        it; under the stable-identity invariant there is nothing to repair.
        """
        mock_bm25_hs.return_value = Mock(name="BM25_1")
        mock_dense_instance_1 = Mock(name="Dense_1")
        mock_dense_instance_1.index = None
        mock_dense_instance_1.metadata_path = Path(self.temp_dir) / "metadata.db"
        mock_dense_hs.return_value = mock_dense_instance_1

        searcher = HybridSearcher(self.temp_dir)

        original_bm25 = searcher.bm25_index
        original_dense = searcher.dense_index
        original_metadata_store = searcher.reranking_engine.metadata_store

        searcher.clear_index()

        assert searcher.search_executor.bm25_index is original_bm25
        assert searcher.search_executor.dense_index is original_dense
        assert searcher.multi_hop_searcher.dense_index is original_dense
        assert searcher.reranking_engine.metadata_store is original_metadata_store

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestCallEdgeResolution:
    """Test call edge resolution in HybridSearcher.add_embeddings() (Phase 2)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_unique_function_name_resolved(self, mock_bm25, mock_dense):
        """Test that unique function names are resolved to full chunk_ids."""
        # Setup mocks
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding results with unique function name
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:unique_func",
                metadata={
                    "name": "unique_func",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [],
                },
                embedding=np.random.rand(768),
                document="def unique_func(): pass",
            ),
            Mock(
                chunk_id="file_b.py:5-15:function:caller",
                metadata={
                    "name": "caller",
                    "chunk_type": "function",
                    "file_path": "file_b.py",
                    "language": "python",
                    "calls": [
                        {
                            "callee_name": "unique_func",  # Should be resolved
                            "line_number": 7,
                            "is_method_call": False,
                        }
                    ],
                },
                embedding=np.random.rand(768),
                document="def caller(): unique_func()",
            ),
        ]

        # Call add_embeddings
        searcher.add_embeddings(embedding_results)

        # Verify add_call_edge was called with resolved chunk_id
        calls = mock_graph.add_call_edge.call_args_list
        assert len(calls) == 1

        # Check that the edge was added with resolved target
        call_kwargs = calls[0][1]  # keyword args
        assert call_kwargs["caller_id"] == "file_b.py:5-15:function:caller"
        assert (
            call_kwargs["callee_name"] == "file_a.py:1-10:function:unique_func"
        )  # Resolved!
        assert call_kwargs["is_resolved"] is True

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_ambiguous_function_name_keeps_all_candidates(self, mock_bm25, mock_dense):
        """Phase 2: ambiguous function names (multiple project matches) now create
        confidence='ambiguous' edges to all candidates instead of dropping to phantom.
        This preserves recall while tagging low-confidence edges explicitly.
        """
        # Setup mocks
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding results with duplicate function name
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:extract",
                metadata={
                    "name": "extract",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [],
                },
                embedding=np.random.rand(768),
                document="def extract(): pass",
            ),
            Mock(
                chunk_id="file_b.py:1-10:function:extract",
                metadata={
                    "name": "extract",  # Duplicate name — ambiguous
                    "chunk_type": "function",
                    "file_path": "file_b.py",
                    "language": "python",
                    "calls": [],
                },
                embedding=np.random.rand(768),
                document="def extract(): pass",
            ),
            Mock(
                chunk_id="file_c.py:5-15:function:caller",
                metadata={
                    "name": "caller",
                    "chunk_type": "function",
                    "file_path": "file_c.py",
                    "language": "python",
                    "calls": [
                        {
                            "callee_name": "extract",  # Ambiguous: 2 candidates
                            "line_number": 7,
                            "is_method_call": False,
                        }
                    ],
                },
                embedding=np.random.rand(768),
                document="def caller(): extract()",
            ),
        ]

        # Call add_embeddings
        searcher.add_embeddings(embedding_results)

        # Phase 2: ambiguous call → 2 edges (one per candidate), each tagged
        calls = mock_graph.add_call_edge.call_args_list
        assert len(calls) == 2  # one edge per ambiguous candidate

        # All edges from the caller, all resolved, all confidence='ambiguous'
        callee_names = {c[1]["callee_name"] for c in calls}
        assert callee_names == {
            "file_a.py:1-10:function:extract",
            "file_b.py:1-10:function:extract",
        }
        for c in calls:
            kw = c[1]
            assert kw["caller_id"] == "file_c.py:5-15:function:caller"
            assert kw["is_resolved"] is True
            assert kw.get("confidence") == "ambiguous"

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_external_call_phantom(self, mock_bm25, mock_dense):
        """Test that external library calls remain as phantom nodes."""
        # Setup mocks
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding result calling external library
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:my_func",
                metadata={
                    "name": "my_func",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [
                        {
                            "callee_name": "os.path.join",  # External call
                            "line_number": 5,
                            "is_method_call": True,
                        }
                    ],
                },
                embedding=np.random.rand(768),
                document="def my_func(): os.path.join('a', 'b')",
            )
        ]

        # Call add_embeddings
        searcher.add_embeddings(embedding_results)

        # Verify add_call_edge was called with unresolved name
        calls = mock_graph.add_call_edge.call_args_list
        assert len(calls) == 1

        call_kwargs = calls[0][1]
        assert call_kwargs["callee_name"] == "os.path.join"  # NOT resolved
        assert call_kwargs["is_resolved"] is False

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_no_calls_no_errors(self, mock_bm25, mock_dense):
        """Test that functions with no calls don't cause errors."""
        # Setup mocks
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Mock graph storage
        mock_graph = Mock()
        searcher.graph_storage = mock_graph

        # Create embedding result with no calls
        embedding_results = [
            Mock(
                chunk_id="file_a.py:1-10:function:simple_func",
                metadata={
                    "name": "simple_func",
                    "chunk_type": "function",
                    "file_path": "file_a.py",
                    "language": "python",
                    "calls": [],  # No calls
                },
                embedding=np.random.rand(768),
                document="def simple_func(): return 42",
            )
        ]

        # Should not raise any errors
        searcher.add_embeddings(embedding_results)

        # Verify add_call_edge was never called
        mock_graph.add_call_edge.assert_not_called()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


@patch("search.hybrid_searcher.CodeIndexManager")
@patch("search.hybrid_searcher.BM25Index")
def test_search_accepts_per_call_weights(mock_bm25, mock_dense):
    """Per-call bm25_weight/dense_weight resolve into the RetrievalRequest
    handed to SearchExecutor. There is no instance state left to mutate or
    leave untouched — C2 deleted the construction-time weight fields that
    this test used to also assert on."""
    import tempfile

    temp_dir = tempfile.mkdtemp()
    try:
        # Make indices appear ready
        mock_bm25.return_value.is_empty = False
        mock_dense_inst = Mock()
        mock_dense_inst.ntotal = 10
        mock_dense.return_value.index = mock_dense_inst

        searcher = HybridSearcher(temp_dir)

        exec_mock = Mock(return_value=[])
        searcher.search_executor.execute_single_hop = exec_mock

        with patch(
            "search.hybrid_searcher._get_config_via_service_locator"
        ) as mock_cfg:
            cfg = Mock()
            cfg.multi_hop.enabled = False
            cfg.ego_graph.enabled = False
            cfg.parent_retrieval.enabled = False
            mock_cfg.return_value = cfg
            searcher.search("test query", bm25_weight=0.9, dense_weight=0.1)

        exec_mock.assert_called_once()
        req = exec_mock.call_args.args[0]
        assert req.bm25_weight == 0.9
        assert req.dense_weight == 0.1
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


@patch("search.hybrid_searcher.CodeIndexManager")
@patch("search.hybrid_searcher.BM25Index")
def test_intent_weights_reach_the_leg_via_multihop(mock_bm25, mock_dense):
    """D1 regression: per-call weights must reach the leg through the
    multi-hop branch — the branch production actually runs (MultiHopConfig
    defaults to enabled=True) and the one that used to drop them across the
    single_hop_callback seam before RetrievalRequest existed."""
    import tempfile

    temp_dir = tempfile.mkdtemp()
    try:
        mock_bm25.return_value.is_empty = False
        mock_dense_inst = Mock()
        mock_dense_inst.ntotal = 10
        mock_dense.return_value.index = mock_dense_inst

        searcher = HybridSearcher(temp_dir)

        leg = Mock(return_value=[])
        searcher.search_executor.execute_single_hop = leg

        with patch(
            "search.hybrid_searcher._get_config_via_service_locator"
        ) as mock_cfg:
            cfg = Mock()
            cfg.multi_hop.enabled = True
            cfg.multi_hop.hop_count = 2
            cfg.multi_hop.expansion = 0.3
            cfg.multi_hop.edge_weights = None
            cfg.multi_hop.initial_k_multiplier = 2
            cfg.ego_graph.enabled = False
            cfg.parent_retrieval.enabled = False
            mock_cfg.return_value = cfg
            searcher.search("q", k=4, bm25_weight=0.9, dense_weight=0.1)

        leg.assert_called_once()
        req = leg.call_args.args[0]
        assert (req.bm25_weight, req.dense_weight) == (0.9, 0.1)
    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


class TestSearchTailDedup:
    """Q1: split_block dedup at the tail of HybridSearcher.search()."""

    def _make_searcher_and_config(self, mock_bm25, mock_dense, dedupe: bool):
        from search.config import (
            MultiHopConfig,
            RerankerConfig,
            SearchConfig,
        )

        mock_dense.return_value.index = None
        searcher = HybridSearcher(tempfile.mkdtemp())

        # Indices ready for hybrid mode
        mock_bm25.return_value.is_empty = False
        dense_index = Mock()
        dense_index.ntotal = 100
        mock_dense.return_value.index = dense_index

        # Single-hop only: no multi-hop, no ego, no parent expansion — the
        # tail dedup is the ONLY dedup site on this path.
        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(dedupe_split_blocks=dedupe),
        )
        config.ego_graph.enabled = False
        config.parent_retrieval.enabled = False
        return searcher, config

    def _dup_results(self):
        from search.reranker import SearchResult

        return [
            SearchResult(
                chunk_id="src/big.py:10-40:split_block:Cls.long_method",
                score=0.9,
                metadata={},
            ),
            SearchResult(
                chunk_id="src/big.py:41-80:split_block:Cls.long_method",
                score=0.8,
                metadata={},
            ),
            SearchResult(
                chunk_id="src/other.py:5-15:function:helper",
                score=0.7,
                metadata={},
            ),
        ]

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_tail_dedup_collapses_fragments(self, mock_bm25, mock_dense):
        """Fragments of one function collapse even when no rerank_by_query fires
        (single-hop path with ego expansion disabled)."""
        searcher, config = self._make_searcher_and_config(
            mock_bm25, mock_dense, dedupe=True
        )
        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=config,
            ),
            patch.object(
                searcher, "_single_hop_search", return_value=self._dup_results()
            ),
        ):
            results = searcher.search("query", k=5)

        assert [r.chunk_id for r in results] == [
            "src/big.py:10-40:split_block:Cls.long_method",
            "src/other.py:5-15:function:helper",
        ]

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_tail_dedup_disabled_keeps_fragments(self, mock_bm25, mock_dense):
        """dedupe_split_blocks=False preserves the pre-Q1 behaviour."""
        searcher, config = self._make_searcher_and_config(
            mock_bm25, mock_dense, dedupe=False
        )
        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=config,
            ),
            patch.object(
                searcher, "_single_hop_search", return_value=self._dup_results()
            ),
        ):
            results = searcher.search("query", k=5)

        assert [r.chunk_id for r in results] == [
            "src/big.py:10-40:split_block:Cls.long_method",
            "src/big.py:41-80:split_block:Cls.long_method",
            "src/other.py:5-15:function:helper",
        ]


class TestSinglePassTailRerank:
    """Q3: single_pass runs exactly one listwise rerank at the search() tail."""

    def _make_searcher_and_config(self, mock_bm25, mock_dense, single_pass: bool):
        from search.config import (
            MultiHopConfig,
            RerankerConfig,
            SearchConfig,
        )

        mock_dense.return_value.index = None
        searcher = HybridSearcher(tempfile.mkdtemp())

        # Indices ready for hybrid mode
        mock_bm25.return_value.is_empty = False
        dense_index = Mock()
        dense_index.ntotal = 100
        mock_dense.return_value.index = dense_index

        # Single-hop only, ego/parent expansion off: on the default path the
        # tail rerank never fires here; under single_pass it must fire anyway.
        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(single_pass=single_pass),
        )
        config.ego_graph.enabled = False
        config.parent_retrieval.enabled = False
        return searcher, config

    def _results(self):
        from search.reranker import SearchResult

        return [
            SearchResult(
                chunk_id="src/a.py:1-10:function:alpha", score=0.9, metadata={}
            ),
            SearchResult(
                chunk_id="src/b.py:1-10:function:beta", score=0.8, metadata={}
            ),
            SearchResult(
                chunk_id="src/c.py:1-10:function:gamma", score=0.7, metadata={}
            ),
        ]

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_single_pass_reranks_once_with_k(self, mock_bm25, mock_dense):
        """The tail pass fires exactly once with k=k even though ego expansion
        never grew results past k (the default path's trigger condition)."""
        searcher, config = self._make_searcher_and_config(
            mock_bm25, mock_dense, single_pass=True
        )
        engine = Mock()
        engine.rerank_by_query.side_effect = lambda **kw: kw["results"][: kw["k"]]
        searcher.reranking_engine = engine
        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=self._results()),
        ):
            results = searcher.search("query", k=2)

        engine.rerank_by_query.assert_called_once()
        assert engine.rerank_by_query.call_args.kwargs["k"] == 2
        assert [r.chunk_id for r in results] == [
            "src/a.py:1-10:function:alpha",
            "src/b.py:1-10:function:beta",
        ]

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_default_path_unchanged_when_single_pass_off(self, mock_bm25, mock_dense):
        """single_pass=False preserves pre-Q3 behaviour: no tail rerank when
        ego expansion is disabled."""
        searcher, config = self._make_searcher_and_config(
            mock_bm25, mock_dense, single_pass=False
        )
        engine = Mock()
        searcher.reranking_engine = engine
        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=self._results()),
        ):
            results = searcher.search("query", k=2)

        engine.rerank_by_query.assert_not_called()
        assert [r.chunk_id for r in results] == [
            "src/a.py:1-10:function:alpha",
            "src/b.py:1-10:function:beta",
            "src/c.py:1-10:function:gamma",
        ]


class TestConfigThreadedToReranker:
    """C2 (docs/adr/0018): the config a caller passes to search() must be
    what RerankingEngine actually acts on, not silently replaced by the
    process-global singleton reranking_engine.rerank_by_query() re-fetches
    internally when no config kwarg is threaded through.

    Before this refactor rerank_by_query() had no config parameter at all,
    so `call_args.kwargs["config"]` would KeyError — this assertion was
    unwritable until search()'s call sites threaded the request-scoped
    config through (search/hybrid_searcher.py:799, :812).
    """

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_passed_config_reaches_reranking_engine_not_the_singleton(
        self, mock_bm25, mock_dense
    ):
        from search.config import MultiHopConfig, RerankerConfig, SearchConfig
        from search.reranker import SearchResult

        mock_dense.return_value.index = None
        searcher = HybridSearcher(tempfile.mkdtemp())
        mock_bm25.return_value.is_empty = False
        dense_index = Mock()
        dense_index.ntotal = 100
        mock_dense.return_value.index = dense_index

        # The service-locator default (what a stale re-fetch would read) —
        # deliberately a different top_k_candidates than the config passed
        # to search(), so the two are distinguishable.
        singleton_config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(single_pass=True, top_k_candidates=11),
        )
        singleton_config.ego_graph.enabled = False
        singleton_config.parent_retrieval.enabled = False

        passed_config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            reranker=RerankerConfig(single_pass=True, top_k_candidates=99),
        )
        passed_config.ego_graph.enabled = False
        passed_config.parent_retrieval.enabled = False

        results = [
            SearchResult(
                chunk_id="src/a.py:1-10:function:alpha", score=0.9, metadata={}
            ),
            SearchResult(
                chunk_id="src/b.py:1-10:function:beta", score=0.8, metadata={}
            ),
        ]

        engine = Mock()
        engine.rerank_by_query.side_effect = lambda **kw: kw["results"][: kw["k"]]
        searcher.reranking_engine = engine

        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=singleton_config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=results),
        ):
            searcher.search("query", k=2, config=passed_config)

        engine.rerank_by_query.assert_called_once()
        # Identity, not just equal fields — proves the engine received the
        # request-scoped object the caller passed rather than a value that
        # happens to match it.
        assert engine.rerank_by_query.call_args.kwargs["config"] is passed_config
        assert (
            engine.rerank_by_query.call_args.kwargs["config"].reranker.top_k_candidates
            == 99
        )


class TestCaptureQueryText:
    """observability.capture_query_text gates ATTR_CAPTURE_QUERY on the
    search.hybrid span (:688-695 fails closed unless config opts in)."""

    def _make_ready_searcher(self, mock_bm25, mock_dense):
        mock_dense.return_value.index = None
        searcher = HybridSearcher(tempfile.mkdtemp())

        mock_bm25.return_value.is_empty = False
        dense_index = Mock()
        dense_index.ntotal = 100
        mock_dense.return_value.index = dense_index
        return searcher

    def _make_config(self, *, capture: bool):
        from search.config import MultiHopConfig, ObservabilityConfig, SearchConfig

        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=False),
            observability=ObservabilityConfig(capture_query_text=capture),
        )
        config.ego_graph.enabled = False
        config.parent_retrieval.enabled = False
        return config

    def _run_search_capturing_spans(self, searcher, config, query):
        spans: list[Mock] = []

        @contextlib.contextmanager
        def _fake_traced_block(name, **attrs):  # noqa: ARG001 - matches traced_block signature
            span = Mock()
            spans.append(span)
            yield span

        with (
            patch(
                "search.hybrid_searcher._get_config_via_service_locator",
                return_value=config,
            ),
            patch.object(searcher, "_single_hop_search", return_value=[]),
            patch("search.hybrid_searcher.traced_block", _fake_traced_block),
        ):
            searcher.search(query, k=5)

        assert spans, "search.hybrid span was never opened"
        return spans[0]

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_capture_query_text_true_sets_span_attribute(self, mock_bm25, mock_dense):
        searcher = self._make_ready_searcher(mock_bm25, mock_dense)
        config = self._make_config(capture=True)

        span = self._run_search_capturing_spans(searcher, config, "secret query text")

        span.set_attribute.assert_any_call(ATTR_CAPTURE_QUERY, "secret query text")

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_capture_query_text_false_does_not_set_span_attribute(
        self, mock_bm25, mock_dense
    ):
        searcher = self._make_ready_searcher(mock_bm25, mock_dense)
        config = self._make_config(capture=False)

        span = self._run_search_capturing_spans(searcher, config, "secret query text")

        calls = [
            c
            for c in span.set_attribute.call_args_list
            if c.args[0] == ATTR_CAPTURE_QUERY
        ]
        assert calls == []
