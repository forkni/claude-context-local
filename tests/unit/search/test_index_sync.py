"""Tests for index synchronization and management functionality.

Created for Phase 3.3 IndexSynchronizer extraction - completing test coverage.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from search.index_sync import IndexSynchronizer


@pytest.fixture
def mock_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir(parents=True)
    return storage_dir


class TestIndexSynchronizer:
    """Test IndexSynchronizer functionality."""

    @pytest.fixture(autouse=True)
    def setup_synchronizer(self, mock_storage_dir: Path):
        """Set up test fixtures with proper temp directory."""
        self.storage_dir = mock_storage_dir

        # Create mock BM25 index
        self.mock_bm25_index = MagicMock()
        self.mock_bm25_index.size = 100
        self.mock_bm25_index._bm25 = MagicMock()
        self.mock_bm25_index._tokenized_docs = ["doc1", "doc2"]
        self.mock_bm25_index.is_empty = False

        # Create mock dense index
        self.mock_dense_index = MagicMock()
        self.mock_dense_index.index = MagicMock()
        self.mock_dense_index.index.ntotal = 100

        # Create synchronizer instance
        self.synchronizer = IndexSynchronizer(
            storage_dir=self.storage_dir,
            bm25_index=self.mock_bm25_index,
            dense_index=self.mock_dense_index,
            bm25_use_stopwords=True,
            bm25_use_stemming=True,
            project_id="test_project",
        )

    def test_initialization(self):
        """Test IndexSynchronizer initialization."""
        assert self.synchronizer.storage_dir == self.storage_dir
        assert self.synchronizer.bm25_index == self.mock_bm25_index
        assert self.synchronizer.dense_index == self.mock_dense_index
        assert self.synchronizer.bm25_use_stopwords is True
        assert self.synchronizer.bm25_use_stemming is True
        assert self.synchronizer.project_id == "test_project"

    def test_save_indices_success(self):
        """Test successful save of both indices."""
        # Configure mocks
        self.mock_bm25_index.save = MagicMock()
        self.mock_dense_index.save_index = MagicMock()

        # Execute save
        result = self.synchronizer.save_indices()

        # Verify both saves were called
        self.mock_bm25_index.save.assert_called_once()
        self.mock_dense_index.save_index.assert_called_once()
        assert isinstance(result, dict)

    def test_save_indices_bm25_no_save_method(self):
        """Test save when BM25 index doesn't support saving."""
        # Remove save method
        delattr(self.mock_bm25_index, "save")
        self.mock_dense_index.save_index = MagicMock()

        # Execute save - should not raise error
        result = self.synchronizer.save_indices()

        # Dense index should still save
        self.mock_dense_index.save_index.assert_called_once()
        assert isinstance(result, dict)

    def test_save_indices_dense_fallback_to_save(self):
        """Test save when dense index uses 'save' instead of 'save_index'."""
        self.mock_bm25_index.save = MagicMock()

        # Remove save_index, add save method
        delattr(self.mock_dense_index, "save_index")
        self.mock_dense_index.save = MagicMock()

        # Execute save
        result = self.synchronizer.save_indices()

        # Verify fallback to save() method
        self.mock_dense_index.save.assert_called_once()
        assert isinstance(result, dict)

    def test_load_indices_success(self):
        """Test successful loading of indices."""
        # Configure mocks - use load() not load_index()
        self.mock_bm25_index.load = MagicMock(return_value=True)
        self.mock_dense_index.load = MagicMock(return_value=True)

        # Execute load
        result = self.synchronizer.load_indices()

        # Verify both loads were called
        self.mock_bm25_index.load.assert_called_once()
        self.mock_dense_index.load.assert_called_once()
        assert result is True

    def test_load_indices_no_existing_indices(self):
        """Test loading when no indices exist."""
        # Configure mocks to return False (no indices)
        self.mock_bm25_index.load = MagicMock(return_value=False)
        self.mock_dense_index.load_index = MagicMock(return_value=False)

        # Execute load
        result = self.synchronizer.load_indices()

        # Should return False
        assert result is False

    def test_validate_index_sync_in_sync(self):
        """Test validation when indices are in sync."""
        # Configure mocks - uses _doc_ids and ntotal property
        self.mock_bm25_index._doc_ids = ["id1", "id2", "id3"]
        self.mock_dense_index.ntotal = 3

        # Execute validation
        result = self.synchronizer.validate_index_sync()

        # Should return True (in sync)
        assert result is True

    def test_validate_index_sync_out_of_sync(self):
        """Test validation when indices are out of sync."""
        # Configure mocks - different sizes
        self.mock_bm25_index._doc_ids = ["id1", "id2", "id3"]
        self.mock_dense_index.ntotal = 5

        # Execute validation
        result = self.synchronizer.validate_index_sync()

        # Should return False (out of sync)
        assert result is False

    def test_validate_index_sync_empty_dense(self):
        """Test validation when dense index is empty."""
        self.mock_bm25_index._doc_ids = ["id1", "id2", "id3"]
        self.mock_dense_index.index = None
        self.mock_dense_index.ntotal = 0

        # Execute validation
        result = self.synchronizer.validate_index_sync()

        # Should return False
        assert result is False

    def test_validate_index_sync_duplicate_ids_logs_warning_but_stays_synced(
        self, caplog
    ):
        """Fix 4: equal bm25/dense counts can still hide a colliding chunk_id
        (one metadata write silently upserting over another, as happened with
        the community-summary chunk_id collision). validate_index_sync must
        name the cause via a log warning, but must NOT flip synced to False --
        resync_if_desynced only rebuilds BM25 from dense and cannot repair a
        duplicate id, so flipping it here would just churn without fixing
        anything (see graph/community_summarizer.py's chunk_id fix for the
        actual repair)."""
        import logging

        self.mock_bm25_index._doc_ids = ["id1", "id2", "id2"]  # id2 duplicated
        self.mock_dense_index.ntotal = 3

        with caplog.at_level(logging.WARNING):
            result = self.synchronizer.validate_index_sync()

        # Counts are equal, so this must still report synced.
        assert result is True
        assert "Duplicate chunk_ids" in caplog.text
        assert "3 total" in caplog.text
        assert "2 unique" in caplog.text

    def test_validate_index_sync_no_duplicates_no_warning(self, caplog):
        """No false positives: unique ids with equal counts logs no duplicate
        warning at all."""
        import logging

        self.mock_bm25_index._doc_ids = ["id1", "id2", "id3"]
        self.mock_dense_index.ntotal = 3

        with caplog.at_level(logging.WARNING):
            result = self.synchronizer.validate_index_sync()

        assert result is True
        assert "Duplicate chunk_ids" not in caplog.text

    def test_resync_bm25_from_dense_success(self):
        """Test successful BM25 resync from dense metadata."""
        # Configure mock - uses chunk_ids property
        self.mock_dense_index.chunk_ids = ["chunk1", "chunk2"]
        self.mock_dense_index.metadata_store = MagicMock()
        self.mock_dense_index.metadata_store.get.side_effect = [
            {"metadata": {"bm25_text": "def test(): pass", "file": "test.py"}},
            {"metadata": {"bm25_text": "class Test: pass", "file": "test.py"}},
        ]

        # Mock BM25Index constructor and methods
        with patch("search.index_sync.BM25Index") as mock_bm25_class:
            mock_new_bm25 = MagicMock()
            mock_new_bm25.size = 2
            mock_bm25_class.return_value = mock_new_bm25

            # Execute resync
            result = self.synchronizer.resync_bm25_from_dense()

            # Verify BM25 was recreated and indexed
            mock_bm25_class.assert_called_once()
            mock_new_bm25.index_documents.assert_called_once()
            mock_new_bm25.save.assert_called_once()
            assert result == 2  # 2 chunks resynced

    def test_resync_bm25_from_dense_empty_dense(self):
        """Test resync when dense index is empty."""
        self.mock_dense_index.chunk_ids = []

        # Execute resync
        result = self.synchronizer.resync_bm25_from_dense()

        # Should return 0 (no chunks)
        assert result == 0

    def test_resync_bm25_preserves_empty_content_chunks(self):
        """Resync must not drop chunks whose bm25_text is empty or absent.

        The normal add path (BM25Index.index_documents) accepts empty strings
        and keeps every chunk, so BM25 == Dense after indexing.  The resync
        path must mirror that behaviour — dropping empty-content chunks here
        is what causes the chronic BM25=1793, Dense=1801 desync.
        """
        # 3 chunks: two with content, one with NO bm25_text key at all.
        # Use a dict-based callable (not a list) for side_effect so the mock
        # is robust against extra/out-of-order calls that can exhaust an
        # ordered list under certain test-collection orderings.
        _metadata_by_id = {
            "chunk1": {"metadata": {"bm25_text": "def foo(): pass", "file": "a.py"}},
            "chunk2": {"metadata": {"bm25_text": "class Bar: pass", "file": "b.py"}},
            "chunk3_empty": {"metadata": {"file": "c.py"}},  # no bm25_text
        }
        self.mock_dense_index.chunk_ids = ["chunk1", "chunk2", "chunk3_empty"]
        self.mock_dense_index.metadata_store = MagicMock()
        self.mock_dense_index.metadata_store.get.side_effect = _metadata_by_id.get

        with patch("search.index_sync.BM25Index") as mock_bm25_class:
            mock_new_bm25 = MagicMock()
            mock_new_bm25.size = 3
            mock_bm25_class.return_value = mock_new_bm25

            result = self.synchronizer.resync_bm25_from_dense()

            # Must index ALL 3 doc_ids (including the empty-content one)
            call_args = mock_new_bm25.index_documents.call_args
            assert call_args is not None, "index_documents was never called"
            actual_doc_ids = call_args[0][1]  # positional arg 1 = doc_ids list
            assert actual_doc_ids == ["chunk1", "chunk2", "chunk3_empty"], (
                f"Expected all 3 chunk_ids, got {actual_doc_ids}. "
                "resync_bm25_from_dense is dropping empty-content chunks."
            )
            assert result == 3

    def test_clear_index_success(self):
        """Test clearing both indices in place (ADR-0025 -- no reconstruction)."""
        self.synchronizer.clear_index()

        self.mock_dense_index.preflight_clear.assert_called_once()
        self.mock_bm25_index.clear.assert_called_once()
        self.mock_dense_index.clear_index.assert_called_once()
        # Identity is unchanged -- clear_index() never reassigns bm25_index/dense_index.
        assert self.synchronizer.bm25_index is self.mock_bm25_index
        assert self.synchronizer.dense_index is self.mock_dense_index

    def test_clear_index_with_storage_cleanup(self):
        """Test clear_index runs the fail-fast probe before destroying any state.

        preflight_clear() must happen before bm25_index.clear() and
        dense_index.clear_index() -- otherwise a locked metadata.db would only
        abort after the BM25 directory was already gone, a half-clear with no
        rollback.
        """
        call_order = []
        self.mock_dense_index.preflight_clear.side_effect = lambda: call_order.append(
            "preflight_clear"
        )
        self.mock_bm25_index.clear.side_effect = lambda: call_order.append("bm25.clear")
        self.mock_dense_index.clear_index.side_effect = lambda: call_order.append(
            "dense.clear_index"
        )

        self.synchronizer.clear_index()

        assert call_order == ["preflight_clear", "bm25.clear", "dense.clear_index"]

    def test_remove_files_single_file(self):
        """Test removing chunks for a single file (set-of-one)."""
        self.mock_dense_index.remove_files = MagicMock(return_value=3)
        self.mock_bm25_index.remove_files = MagicMock(return_value=3)

        result = self.synchronizer.remove_files({"test.py"}, "test_project")

        self.mock_dense_index.remove_files.assert_called_once_with(
            {"test.py"}, "test_project"
        )
        self.mock_bm25_index.remove_files.assert_called_once_with(
            {"test.py"}, "test_project"
        )
        assert result == 6  # 3 + 3

    def test_remove_files_not_found(self):
        """Test removing chunks when file doesn't exist."""
        self.mock_dense_index.remove_files = MagicMock(return_value=0)
        self.mock_bm25_index.remove_files = MagicMock(return_value=0)

        result = self.synchronizer.remove_files({"nonexistent.py"}, "test_project")

        assert result == 0

    def test_remove_files_batch(self):
        """Test batch removal of multiple files."""
        file_paths = {"test1.py", "test2.py", "test3.py"}
        self.mock_dense_index.remove_files = MagicMock(return_value=10)
        self.mock_bm25_index.remove_files = MagicMock(return_value=10)

        result = self.synchronizer.remove_files(file_paths, "test_project")

        self.mock_dense_index.remove_files.assert_called_once_with(
            file_paths, "test_project"
        )
        self.mock_bm25_index.remove_files.assert_called_once_with(
            file_paths, "test_project"
        )
        assert result == 20  # 10 + 10

    def test_remove_files_empty_set(self):
        """Test batch removal with empty file set."""
        result = self.synchronizer.remove_files(set(), "test_project")

        assert result == 0

    def test_remove_files_partial_failure(self):
        """Test batch removal with partial failure (BM25 fails, dense succeeds)."""
        file_paths = {"test1.py", "test2.py", "test3.py"}

        self.mock_dense_index.remove_files = MagicMock(return_value=10)
        self.mock_bm25_index.remove_files = MagicMock(
            side_effect=Exception("BM25 error")
        )

        # Should not raise (only one failed)
        result = self.synchronizer.remove_files(file_paths, "test_project")

        # Should return 10 (only dense succeeded)
        assert result == 10

    def test_verify_bm25_files_private_method(self):
        """Test _verify_bm25_files is called during save."""
        with patch.object(self.synchronizer, "_verify_bm25_files") as mock_verify:
            self.mock_bm25_index.save = MagicMock()
            self.mock_dense_index.save_index = MagicMock()

            # Execute save
            self.synchronizer.save_indices()

            # Verify _verify_bm25_files was called
            mock_verify.assert_called_once()

    def test_storage_dir_creation(self):
        """Test that storage_dir property is a Path object."""
        assert isinstance(self.synchronizer.storage_dir, Path)
        assert self.synchronizer.storage_dir == self.storage_dir

    def test_embedder_propagation_in_clear_index(self):
        """Test the embedder stays reachable through dense_index across a clear.

        Previously this was tested by asserting a reconstructed
        CodeIndexManager received the embedder kwarg. Under ADR-0025,
        clear_index() never reconstructs dense_index -- it clears the same
        object in place -- so the embedder threaded through at construction
        time is simply never touched.
        """
        mock_embedder = MagicMock()
        mock_embedder.get_model_info.return_value = {"embedding_dimension": 1024}
        self.mock_dense_index.embedder = mock_embedder

        synchronizer_with_embedder = IndexSynchronizer(
            storage_dir=self.storage_dir,
            bm25_index=self.mock_bm25_index,
            dense_index=self.mock_dense_index,
            bm25_use_stopwords=True,
            bm25_use_stemming=True,
            project_id="test_project",
            embedder=mock_embedder,
        )

        assert synchronizer_with_embedder.embedder == mock_embedder

        synchronizer_with_embedder.clear_index()

        # ADR-0025: dense_index identity is stable across a clear, so the
        # embedder it was constructed with is still reachable through it.
        assert synchronizer_with_embedder.dense_index is self.mock_dense_index
        assert synchronizer_with_embedder.dense_index.embedder is mock_embedder

    def test_embedder_none_allowed(self):
        """Test that IndexSynchronizer works with embedder=None for backward compatibility."""
        # Create synchronizer without embedder (backward compatibility)
        synchronizer_no_embedder = IndexSynchronizer(
            storage_dir=self.storage_dir,
            bm25_index=self.mock_bm25_index,
            dense_index=self.mock_dense_index,
            bm25_use_stopwords=True,
            bm25_use_stemming=True,
            project_id="test_project",
            embedder=None,
        )

        # Verify embedder is None
        assert synchronizer_no_embedder.embedder is None

        # clear_index should still work with embedder=None -- nothing in the
        # clear path touches self.embedder or dense_index.embedder at all.
        synchronizer_no_embedder.clear_index()

        assert synchronizer_no_embedder.dense_index is self.mock_dense_index


class TestResyncIfDesynced:
    """P6 behaviour tests for IndexSynchronizer.resync_if_desynced.

    Verifies the threshold logic, data source (live counts, not get_stats()),
    and return values.
    """

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.storage_dir = tmp_path / "storage"
        self.storage_dir.mkdir(parents=True)
        self.bm25 = MagicMock()
        self.dense = MagicMock()
        self.dense.index = MagicMock()
        self.sync = IndexSynchronizer(
            storage_dir=self.storage_dir,
            bm25_index=self.bm25,
            dense_index=self.dense,
        )

    def test_synced_returns_false_zero(self):
        """No resync when counts match."""
        self.bm25._doc_ids = list(range(100))
        self.dense.ntotal = 100

        resynced, count = self.sync.resync_if_desynced("TEST")

        assert resynced is False
        assert count == 0

    def test_below_threshold_no_resync(self):
        """9% difference is below DESYNC_THRESHOLD — no action."""
        self.bm25._doc_ids = list(range(91))
        self.dense.ntotal = 100  # 9% diff

        resynced, count = self.sync.resync_if_desynced("TEST")

        assert resynced is False
        assert count == 0

    def test_above_threshold_triggers_resync(self):
        """11% difference triggers resync and returns (True, rebuild_count)."""
        self.bm25._doc_ids = list(range(89))
        self.dense.ntotal = 100  # 11% diff > 0.10

        self.dense.chunk_ids = ["c1", "c2"]
        self.dense.metadata_store = MagicMock()
        self.dense.metadata_store.get.side_effect = [
            {"metadata": {"bm25_text": "def a(): pass"}},
            {"metadata": {"bm25_text": "def b(): pass"}},
        ]

        with patch("search.index_sync.BM25Index") as mock_bm25_cls:
            mock_new_bm25 = MagicMock()
            mock_new_bm25.size = 2
            mock_bm25_cls.return_value = mock_new_bm25

            resynced, count = self.sync.resync_if_desynced("TEST")

        assert resynced is True
        assert count == 2

    def test_dense_empty_skips_resync(self):
        """Dense count=0 → skip resync (no reference to divide by)."""
        self.bm25._doc_ids = []
        self.dense.ntotal = 0
        self.dense.index = None

        resynced, count = self.sync.resync_if_desynced("TEST")

        assert resynced is False
        assert count == 0

    def test_uses_live_counts_not_get_stats(self):
        """resync_if_desynced never calls get_stats() — live counts only."""
        self.bm25._doc_ids = list(range(100))
        self.dense.ntotal = 100

        self.sync.resync_if_desynced("TEST")

        self.dense.get_stats.assert_not_called()
        self.bm25.get_stats.assert_not_called()
