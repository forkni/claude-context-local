"""Integration tests for incremental indexing."""

import tempfile
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from huggingface_hub import get_token

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from merkle.change_detector import ChangeDetector
from merkle.merkle_dag import MerkleDAG
from merkle.snapshot_manager import SnapshotManager
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager as Indexer


def _has_hf_token():
    """Check if HuggingFace token is available."""
    return get_token() is not None


@pytest.mark.slow
class TestIncrementalIndexing(TestCase):
    """Test incremental indexing functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_path = Path(self.temp_dir) / "test_project"
        self.test_path.mkdir()

        # Storage for snapshots
        self.snapshot_dir = Path(self.temp_dir) / "snapshots"
        self.snapshot_manager = SnapshotManager(self.snapshot_dir)

        # Storage for index
        self.index_dir = Path(self.temp_dir) / "index"
        self.index_dir.mkdir()

        self.create_initial_codebase()

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def create_initial_codebase(self):
        """Create initial Python codebase."""
        # Main module
        (self.test_path / "main.py").write_text(
            '''
def main():
    """Main function."""
    print("Hello World")
    return 0

if __name__ == "__main__":
    main()
'''
        )

        # Utils module
        (self.test_path / "utils.py").write_text(
            '''
def helper(x, y):
    """Helper function."""
    return x + y

class Calculator:
    """Simple calculator."""

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
'''
        )

        # Create subdirectory
        (self.test_path / "lib").mkdir()
        (self.test_path / "lib" / "database.py").write_text(
            '''
class Database:
    """Database connection."""

    def connect(self):
        """Connect to database."""
        pass

    def query(self, sql):
        """Execute query."""
        return []
'''
        )

        # Two more files so a single-file change/deletion stays under the
        # community-redetection drift threshold (30%, search/config.py
        # incremental_community_redetect_threshold). With only 3 files,
        # touching one is 33% churn and _check_community_drift
        # (search/incremental_indexer.py) always promotes to a full
        # reindex, which reports chunks_added/chunks_removed for the whole
        # rebuild rather than the true incremental delta these tests check.
        (self.test_path / "config.py").write_text(
            '''
DEBUG = True

def get_config():
    """Return app config."""
    return {"debug": DEBUG}
'''
        )
        (self.test_path / "lib" / "models.py").write_text(
            '''
class User:
    """User model."""

    def __init__(self, name):
        self.name = name
'''
        )

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_full_index(self, mock_sentence_transformer):
        """Test full indexing of a codebase."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # First index should be full
        result = incremental_indexer.incremental_index(
            str(self.test_path), "test_project"
        )

        assert result.success
        assert result.files_added > 0
        assert result.chunks_added > 0
        assert result.files_removed == 0
        assert result.files_modified == 0

        # Verify snapshot was created
        assert self.snapshot_manager.has_snapshot(str(self.test_path))

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_no_changes(self, mock_sentence_transformer):
        """Test indexing when no changes occur."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # First index
        result1 = incremental_indexer.incremental_index(
            str(self.test_path), "test_project"
        )

        assert result1.success

        # Second index with no changes
        result2 = incremental_indexer.incremental_index(
            str(self.test_path), "test_project"
        )

        assert result2.success
        assert result2.files_added == 0
        assert result2.files_removed == 0
        assert result2.files_modified == 0

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_file_modification(self, mock_sentence_transformer):
        """Test incremental indexing when files are modified."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # Initial index
        incremental_indexer.incremental_index(str(self.test_path), "test_project")

        # Modify a file
        (self.test_path / "utils.py").write_text(
            '''
def helper(x, y):
    """Updated helper function."""
    return x * y  # Changed from addition to multiplication

class Calculator:
    """Enhanced calculator."""

    def add(self, a, b):
        return a + b

    def multiply(self, a, b):
        """New method."""
        return a * b

    def subtract(self, a, b):
        return a - b
'''
        )

        # Incremental index
        result2 = incremental_indexer.incremental_index(
            str(self.test_path), "test_project"
        )

        assert result2.success
        assert result2.files_modified == 1
        assert result2.files_added == 0
        assert result2.files_removed == 0
        # Should have removed old chunks and added new ones
        assert result2.chunks_removed > 0
        assert result2.chunks_added > 0

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_file_addition(self, mock_sentence_transformer):
        """Test incremental indexing when files are added."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # Initial index
        incremental_indexer.incremental_index(str(self.test_path), "test_project")

        # Add a new file
        (self.test_path / "new_module.py").write_text(
            '''
def new_function():
    """A new function."""
    return "new"

class NewClass:
    """A new class."""
    pass
'''
        )

        # Incremental index
        result2 = incremental_indexer.incremental_index(
            str(self.test_path), "test_project"
        )

        assert result2.success
        assert result2.files_added == 1
        assert result2.files_removed == 0
        assert result2.files_modified == 0
        assert result2.chunks_added > 0

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_file_deletion(self, mock_sentence_transformer):
        """Test incremental indexing when files are deleted."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # Initial index
        incremental_indexer.incremental_index(str(self.test_path), "test_project")

        # Delete a file
        (self.test_path / "utils.py").unlink()

        # Incremental index
        result2 = incremental_indexer.incremental_index(
            str(self.test_path), "test_project"
        )

        assert result2.success
        assert result2.files_added == 0
        assert result2.files_removed == 1
        assert result2.files_modified == 0
        assert result2.chunks_removed > 0

    def test_change_detection(self):
        """Test change detection using Merkle trees."""
        detector = ChangeDetector(self.snapshot_manager)

        # Build initial DAG
        dag1 = MerkleDAG(str(self.test_path))
        dag1.build()
        self.snapshot_manager.save_snapshot(dag1)

        # No changes should be detected
        assert not detector.quick_check(str(self.test_path))

        # Modify a file
        time.sleep(0.1)  # Ensure different timestamp
        (self.test_path / "main.py").write_text("# Modified\n")

        # Changes should be detected
        assert detector.quick_check(str(self.test_path))

        # Get detailed changes
        changes, new_dag = detector.detect_changes_from_snapshot(str(self.test_path))

        assert changes.has_changes()
        assert "main.py" in changes.modified

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_needs_reindex(self, mock_sentence_transformer):
        """Test checking if reindex is needed."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # Should need index initially
        assert incremental_indexer.needs_reindex(str(self.test_path))

        # Index the project
        incremental_indexer.incremental_index(str(self.test_path), "test_project")

        # Should not need reindex immediately
        assert not incremental_indexer.needs_reindex(
            str(self.test_path), max_age_minutes=1440
        )  # 24 hours

        # Modify a file
        (self.test_path / "main.py").write_text("# Changed\n")

        # Should need reindex after change
        assert incremental_indexer.needs_reindex(str(self.test_path))

    @patch("embeddings.model_loader.SentenceTransformer")
    def test_indexing_stats(self, mock_sentence_transformer):
        """Test getting indexing statistics."""

        # Mock the model to prevent downloads
        def mock_encode(
            sentences,
            show_progress_bar=False,
            convert_to_tensor=False,
            device=None,
            **kwargs,
        ):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        # else MagicMock auto-vivifies `[0].auto_model.config` (a fake HF config
        # with hasattr()==True on every attribute), so _extract_hf_config()
        # "succeeds" with garbage and estimate_activation_gb_from_config() then
        # compares MagicMock attributes with '>' and raises TypeError.
        mock_model.__getitem__.side_effect = IndexError
        mock_sentence_transformer.return_value = mock_model

        indexer = Indexer(storage_dir=str(self.index_dir))
        embedder = CodeEmbedder()
        chunker = MultiLanguageChunker(str(self.test_path))

        incremental_indexer = IncrementalIndexer(
            indexer=indexer,
            embedder=embedder,
            chunker=chunker,
            snapshot_manager=self.snapshot_manager,
        )

        # No stats initially
        stats = incremental_indexer.get_indexing_stats(str(self.test_path))
        assert stats is None

        # Index the project
        incremental_indexer.incremental_index(str(self.test_path), "test_project")

        # Get stats
        stats = incremental_indexer.get_indexing_stats(str(self.test_path))

        assert stats is not None
        assert stats["project_name"] == "test_project"
        assert stats["file_count"] > 0
        assert "last_snapshot" in stats
        assert "current_chunks" in stats
