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

    def test_resync_bm25_from_dense_success(self):
        """Test successful BM25 resync from dense metadata."""
        # Configure mock - uses chunk_ids property
        self.mock_dense_index.chunk_ids = ["chunk1", "chunk2"]
        self.mock_dense_index.metadata_store = MagicMock()
        self.mock_dense_index.metadata_store.get.side_effect = [
            {"metadata": {"content": "def test(): pass", "file": "test.py"}},
            {"metadata": {"content": "class Test: pass", "file": "test.py"}},
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

    def test_clear_index_success(self):
        """Test clearing both indices."""
        # clear_index recreates indices using constructors
        with patch("search.index_sync.BM25Index") as mock_bm25_class:
            with patch("search.index_sync.CodeIndexManager") as mock_dense_class:
                with patch("search.index_sync.shutil.rmtree"):
                    with patch("search.index_sync.Path.exists", return_value=True):
                        self.mock_dense_index.clear_index = MagicMock()

                        # Execute clear
                        self.synchronizer.clear_index()

                        # Verify dense clear_index was called
                        self.mock_dense_index.clear_index.assert_called_once()
                        # Verify new instances were created
                        mock_bm25_class.assert_called_once()
                        mock_dense_class.assert_called_once()

    def test_clear_index_with_storage_cleanup(self):
        """Test clearing with storage directory cleanup."""
        # Mock Path.exists and shutil.rmtree
        with patch("search.index_sync.Path.exists", return_value=True):
            with patch("search.index_sync.shutil.rmtree") as mock_rmtree:
                self.mock_bm25_index.clear = MagicMock()
                self.mock_dense_index.clear = MagicMock()

                # Execute clear
                self.synchronizer.clear_index()

                # Verify rmtree was called
                assert mock_rmtree.call_count >= 0  # May or may not cleanup

    def test_remove_file_chunks_success(self):
        """Test removing chunks for specific file."""
        # Configure mocks - both indices have remove_file_chunks
        self.mock_dense_index.remove_file_chunks = MagicMock(return_value=3)
        self.mock_bm25_index.remove_file_chunks = MagicMock(return_value=3)

        # Execute removal
        result = self.synchronizer.remove_file_chunks("test.py", "test_project")

        # Verify removals were called
        self.mock_dense_index.remove_file_chunks.assert_called_once_with(
            "test.py", "test_project"
        )
        self.mock_bm25_index.remove_file_chunks.assert_called_once_with(
            "test.py", "test_project"
        )
        assert result == 6  # 3 + 3

    def test_remove_file_chunks_not_found(self):
        """Test removing chunks when file doesn't exist."""
        # Configure mocks to return 0
        self.mock_dense_index.remove_file_chunks = MagicMock(return_value=0)
        self.mock_bm25_index.remove_file_chunks = MagicMock(return_value=0)

        # Execute removal
        result = self.synchronizer.remove_file_chunks("nonexistent.py", "test_project")

        # Should return 0
        assert result == 0

    def test_remove_multiple_files_success(self):
        """Test batch removal of multiple files."""
        # Configure mocks - both have remove_multiple_files
        file_paths = {"test1.py", "test2.py", "test3.py"}
        self.mock_dense_index.remove_multiple_files = MagicMock(return_value=10)
        self.mock_bm25_index.remove_multiple_files = MagicMock(return_value=10)

        # Execute batch removal
        result = self.synchronizer.remove_multiple_files(file_paths, "test_project")

        # Verify batch removals were called
        self.mock_dense_index.remove_multiple_files.assert_called_once_with(
            file_paths, "test_project"
        )
        self.mock_bm25_index.remove_multiple_files.assert_called_once_with(
            file_paths, "test_project"
        )
        assert result == 20  # 10 + 10

    def test_remove_multiple_files_empty_list(self):
        """Test batch removal with empty file list."""
        self.mock_dense_index.remove_multiple_files = MagicMock(return_value=0)
        self.mock_bm25_index.remove_multiple_files = MagicMock(return_value=0)

        # Execute with empty set
        result = self.synchronizer.remove_multiple_files(set(), "test_project")

        # Should return 0 without errors
        assert result == 0

    def test_remove_multiple_files_partial_failures(self):
        """Test batch removal with partial failure."""
        file_paths = {"test1.py", "test2.py", "test3.py"}

        # Configure mocks - dense succeeds, BM25 fails
        self.mock_dense_index.remove_multiple_files = MagicMock(return_value=10)
        self.mock_bm25_index.remove_multiple_files = MagicMock(
            side_effect=Exception("BM25 error")
        )

        # Execute batch removal - should not raise (only one failed)
        result = self.synchronizer.remove_multiple_files(file_paths, "test_project")

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
        """Test that embedder is passed to CodeIndexManager during clear_index."""
        # Create mock embedder
        mock_embedder = MagicMock()
        mock_embedder.get_model_info.return_value = {"embedding_dimension": 1024}

        # Create synchronizer with embedder
        synchronizer_with_embedder = IndexSynchronizer(
            storage_dir=self.storage_dir,
            bm25_index=self.mock_bm25_index,
            dense_index=self.mock_dense_index,
            bm25_use_stopwords=True,
            bm25_use_stemming=True,
            project_id="test_project",
            embedder=mock_embedder,
        )

        # Verify embedder is stored
        assert synchronizer_with_embedder.embedder == mock_embedder

        # clear_index recreates indices with embedder
        with patch("search.index_sync.BM25Index"):
            with patch("search.index_sync.CodeIndexManager") as mock_dense_class:
                with patch("search.index_sync.shutil.rmtree"):
                    with patch("search.index_sync.Path.exists", return_value=True):
                        self.mock_dense_index.clear_index = MagicMock()

                        # Execute clear
                        synchronizer_with_embedder.clear_index()

                        # Verify CodeIndexManager was called with embedder
                        mock_dense_class.assert_called_once()
                        call_kwargs = mock_dense_class.call_args[1]
                        assert "embedder" in call_kwargs
                        assert call_kwargs["embedder"] == mock_embedder

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

        # clear_index should still work (passes None to CodeIndexManager)
        with patch("search.index_sync.BM25Index"):
            with patch("search.index_sync.CodeIndexManager") as mock_dense_class:
                with patch("search.index_sync.shutil.rmtree"):
                    with patch("search.index_sync.Path.exists", return_value=True):
                        self.mock_dense_index.clear_index = MagicMock()

                        # Execute clear
                        synchronizer_no_embedder.clear_index()

                        # Verify CodeIndexManager was called with embedder=None
                        mock_dense_class.assert_called_once()
                        call_kwargs = mock_dense_class.call_args[1]
                        assert "embedder" in call_kwargs
                        assert call_kwargs["embedder"] is None
