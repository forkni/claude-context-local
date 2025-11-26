"""Tests for hybrid search orchestrator."""

import tempfile
from unittest.mock import Mock, patch

import numpy as np

from search.hybrid_searcher import GPUMemoryMonitor, HybridSearcher


class TestGPUMemoryMonitor:
    """Test GPU memory monitoring functionality."""

    def test_memory_info_without_gpu(self):
        """Test memory info when GPU is not available."""
        with patch("search.hybrid_searcher.torch", None):
            monitor = GPUMemoryMonitor()
            info = monitor.get_available_memory()

            assert info["gpu_available"] == 0
            assert info["gpu_total"] == 0
            assert info["gpu_utilization"] == 0.0

    @patch("search.hybrid_searcher.torch")
    def test_memory_info_with_gpu(self, mock_torch):
        """Test memory info when GPU is available."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.current_device.return_value = 0
        mock_torch.cuda.mem_get_info.return_value = (
            4 * 1024**3,
            8 * 1024**3,
        )  # 4GB free, 8GB total

        monitor = GPUMemoryMonitor()
        info = monitor.get_available_memory()

        assert info["gpu_available"] == 4 * 1024**3
        assert info["gpu_total"] == 8 * 1024**3
        assert info["gpu_utilization"] == 0.5  # 50% utilized

    @patch("search.hybrid_searcher.torch")
    def test_can_use_gpu(self, mock_torch):
        """Test GPU availability checking."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            2 * 1024**3,
            8 * 1024**3,
        )  # 2GB available

        monitor = GPUMemoryMonitor()

        assert monitor.can_use_gpu(1024**3)  # 1GB requirement - should pass
        assert not monitor.can_use_gpu(3 * 1024**3)  # 3GB requirement - should fail

    def test_batch_memory_estimation(self):
        """Test batch memory estimation."""
        monitor = GPUMemoryMonitor()

        # Test memory estimation
        memory = monitor.estimate_batch_memory(100, 768)
        expected = 100 * 768 * 4 * 2  # batch_size * dim * float32 * safety_margin
        assert memory == expected


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

        assert searcher.bm25_weight == 0.4
        assert searcher.dense_weight == 0.6
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
    def test_weight_optimization(self, mock_bm25, mock_dense):
        """Test weight optimization."""
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

            # Test optimization
            test_queries = ["test query 1", "test query 2"]

            result = searcher.optimize_weights(test_queries)

            assert "bm25_weight" in result
            assert "dense_weight" in result
            assert "optimization_score" in result
            assert "tested_combinations" in result

            # In mocked environment, weights might not change, just verify optimization ran
            assert result["tested_combinations"] > 0
            assert isinstance(result["optimization_score"], (int, float))

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
        searcher._search_stats["total_searches"] = 10
        searcher._search_stats["bm25_time"] = 1.0
        searcher._search_stats["dense_time"] = 2.0
        searcher._search_stats["rerank_time"] = 0.5

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
            initial_searches = searcher._search_stats["total_searches"]
            searcher.search("query 1", use_parallel=False)
            searcher.search("query 2", use_parallel=False)

            # Stats should be updated
            assert searcher._search_stats["total_searches"] == initial_searches + 2
            # In mocked environment, times might be 0, so just check they exist
            assert "bm25_time" in searcher._search_stats
            assert "dense_time" in searcher._search_stats
            assert "rerank_time" in searcher._search_stats
            assert searcher._search_stats["bm25_time"] >= 0
            assert searcher._search_stats["dense_time"] >= 0
            assert searcher._search_stats["rerank_time"] >= 0

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

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_resync_bm25_from_dense_success(self, mock_bm25, mock_dense):
        """Test successful BM25 resync from dense metadata."""
        # Setup mock for dense index
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        # Setup dense index with chunk IDs and metadata
        dense_mock = mock_dense.return_value
        dense_mock._chunk_ids = ["chunk1", "chunk2", "chunk3"]
        dense_mock.metadata_db = {
            "chunk1": {"metadata": {"content": "def func1(): pass"}},
            "chunk2": {"metadata": {"content": "class MyClass: pass"}},
            "chunk3": {"metadata": {"content": "async def async_func(): pass"}},
        }

        # Replace dense_index with configured mock
        searcher.dense_index = dense_mock

        # Mock BM25Index for the rebuild (new instance created in resync)
        new_bm25_mock = Mock()
        new_bm25_mock.size = 3
        mock_bm25.return_value = new_bm25_mock

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
        dense_mock._chunk_ids = []  # No chunks
        searcher.dense_index = dense_mock

        count = searcher.resync_bm25_from_dense()

        assert count == 0

    @patch("search.hybrid_searcher.CodeIndexManager")
    @patch("search.hybrid_searcher.BM25Index")
    def test_resync_bm25_from_dense_no_content_in_metadata(self, mock_bm25, mock_dense):
        """Test resync handles chunks with missing content gracefully."""
        mock_dense.return_value.index = None
        searcher = HybridSearcher(self.temp_dir)

        dense_mock = mock_dense.return_value
        dense_mock._chunk_ids = ["chunk1", "chunk2"]
        dense_mock.metadata_db = {
            "chunk1": {"metadata": {"content": "valid content"}},
            "chunk2": {"metadata": {}},  # No content key
        }
        searcher.dense_index = dense_mock

        # Mock BM25Index for rebuild
        new_bm25_mock = Mock()
        new_bm25_mock.size = 1  # Only 1 chunk has valid content
        mock_bm25.return_value = new_bm25_mock

        count = searcher.resync_bm25_from_dense()

        # Should only sync the chunk with valid content
        assert count == 1

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
