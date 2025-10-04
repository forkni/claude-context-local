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
                "language": "python"
                if i < 2 or i == 4
                else "javascript"
                if i == 2
                else "sql",
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
            searcher.search(
                "test query", k=5, use_parallel=False, filters=filters
            )

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

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
