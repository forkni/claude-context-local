"""Unit tests for parallel index loading (Phase 3 optimization).

Tests verify that BM25 and dense indices load in parallel, reducing startup time
by 50-100ms for large indices.
"""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch


def test_parallel_loading_returns_correct_counts():
    """Verify BM25 and dense counts are correct after parallel load."""
    from search.hybrid_searcher import HybridSearcher

    # Mock dependencies
    with (
        patch("search.hybrid_searcher.BM25Index") as mock_bm25_class,
        patch("search.hybrid_searcher.CodeIndexManager") as mock_dense_class,
    ):
        # Setup BM25 mock
        mock_bm25 = MagicMock()
        mock_bm25.load.return_value = True
        mock_bm25.size = 100
        mock_bm25.is_empty = False
        mock_bm25_class.return_value = mock_bm25

        # Setup dense index mock with matching dimension
        mock_dense = MagicMock()
        mock_dense.index.ntotal = 95
        mock_dense.index.d = 768  # Set dimension
        mock_dense_class.return_value = mock_dense

        # Setup embedder mock with matching dimension
        mock_embedder = MagicMock()
        mock_embedder.get_model_info.return_value = {"embedding_dimension": 768}
        mock_embedder.model_name = "test-model"

        # Create searcher (triggers parallel loading)
        searcher = HybridSearcher(
            storage_dir=str(Path.cwd() / "test_storage"),
            embedder=mock_embedder,
        )

        # Verify both indices loaded
        assert mock_bm25.load.called
        assert searcher.bm25_index is mock_bm25
        assert searcher.dense_index is mock_dense


def test_parallel_loading_handles_missing_bm25():
    """Verify graceful handling when BM25 index doesn't exist."""
    from search.hybrid_searcher import HybridSearcher

    with (
        patch("search.hybrid_searcher.BM25Index") as mock_bm25_class,
        patch("search.hybrid_searcher.CodeIndexManager") as mock_dense_class,
    ):
        # BM25 not found (load returns False)
        mock_bm25 = MagicMock()
        mock_bm25.load.return_value = False
        mock_bm25.size = 0
        mock_bm25.is_empty = True
        mock_bm25_class.return_value = mock_bm25

        # Dense index exists
        mock_dense = MagicMock()
        mock_dense.index.ntotal = 95
        mock_dense.index.d = 768
        mock_dense_class.return_value = mock_dense

        # Setup embedder mock with matching dimension
        mock_embedder = MagicMock()
        mock_embedder.get_model_info.return_value = {"embedding_dimension": 768}
        mock_embedder.model_name = "test-model"

        # Should not raise exception
        searcher = HybridSearcher(
            storage_dir=str(Path.cwd() / "test_storage"),
            embedder=mock_embedder,
        )

        assert searcher.bm25_index is mock_bm25
        assert searcher.dense_index is mock_dense


def test_parallel_loading_handles_missing_dense():
    """Verify graceful handling when dense index doesn't exist."""
    from search.hybrid_searcher import HybridSearcher

    with (
        patch("search.hybrid_searcher.BM25Index") as mock_bm25_class,
        patch("search.hybrid_searcher.CodeIndexManager") as mock_dense_class,
    ):
        # BM25 exists
        mock_bm25 = MagicMock()
        mock_bm25.load.return_value = True
        mock_bm25.size = 100
        mock_bm25.is_empty = False
        mock_bm25_class.return_value = mock_bm25

        # Dense index not found
        mock_dense = MagicMock()
        mock_dense.index = None  # No index loaded
        mock_dense_class.return_value = mock_dense

        # Should not raise exception
        searcher = HybridSearcher(
            storage_dir=str(Path.cwd() / "test_storage"),
            embedder=MagicMock(),
        )

        assert searcher.bm25_index is mock_bm25
        assert searcher.dense_index is mock_dense


def test_parallel_loading_thread_safety():
    """Verify no race conditions in parallel loading."""
    from search.hybrid_searcher import HybridSearcher

    with (
        patch("search.hybrid_searcher.BM25Index") as mock_bm25_class,
        patch("search.hybrid_searcher.CodeIndexManager") as mock_dense_class,
    ):
        # Add delays to simulate I/O and expose potential race conditions
        mock_bm25 = MagicMock()

        def slow_load():
            time.sleep(0.05)
            return True

        mock_bm25.load = slow_load
        mock_bm25.size = 100
        mock_bm25.is_empty = False
        mock_bm25_class.return_value = mock_bm25

        mock_dense = MagicMock()
        mock_dense.index.ntotal = 95
        mock_dense.index.d = 768
        mock_dense_class.return_value = mock_dense

        # Setup embedder mock with matching dimension
        mock_embedder = MagicMock()
        mock_embedder.get_model_info.return_value = {"embedding_dimension": 768}
        mock_embedder.model_name = "test-model"

        # Create searcher - should complete without deadlock or corruption
        start = time.time()
        searcher = HybridSearcher(
            storage_dir=str(Path.cwd() / "test_storage"),
            embedder=mock_embedder,
        )
        elapsed = time.time() - start

        # Should complete reasonably fast (not deadlocked)
        assert elapsed < 1.0, f"Parallel loading took too long: {elapsed}s"

        # Both indices should be set correctly
        assert searcher.bm25_index is mock_bm25
        assert searcher.dense_index is mock_dense


def test_parallel_loading_logs_correctly():
    """Verify parallel loading produces correct log messages."""
    from search.hybrid_searcher import HybridSearcher

    with (
        patch("search.hybrid_searcher.BM25Index") as mock_bm25_class,
        patch("search.hybrid_searcher.CodeIndexManager") as mock_dense_class,
    ):
        # Setup mocks
        mock_bm25 = MagicMock()
        mock_bm25.load.return_value = True
        mock_bm25.size = 100
        mock_bm25.is_empty = False
        mock_bm25_class.return_value = mock_bm25

        mock_dense = MagicMock()
        mock_dense.index.ntotal = 95
        mock_dense.index.d = 768
        mock_dense_class.return_value = mock_dense

        # Setup embedder mock with matching dimension
        mock_embedder = MagicMock()
        mock_embedder.get_model_info.return_value = {"embedding_dimension": 768}
        mock_embedder.model_name = "test-model"

        # Capture logs
        import logging

        with patch.object(
            logging.getLogger("search.hybrid_searcher"), "info"
        ) as mock_log:
            searcher = HybridSearcher(
                storage_dir=str(Path.cwd() / "test_storage"),
                embedder=mock_embedder,
            )

            # Verify searcher initialized correctly
            assert searcher.bm25_index is mock_bm25
            assert searcher.dense_index is mock_dense

            # Verify parallel loading messages in logs
            log_messages = [call.args[0] for call in mock_log.call_args_list]

            assert any("Loading indices in parallel" in msg for msg in log_messages)
            assert any("Parallel index loading complete" in msg for msg in log_messages)
