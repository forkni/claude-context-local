"""Tests for incremental indexing functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from search.incremental_indexer import IncrementalIndexer, IncrementalIndexResult


class TestIncrementalIndexResult:
    """Test IncrementalIndexResult dataclass."""

    def test_result_creation(self):
        """Test creating IncrementalIndexResult."""
        result = IncrementalIndexResult(
            files_added=5,
            files_removed=2,
            files_modified=3,
            chunks_added=50,
            chunks_removed=20,
            time_taken=1.5,
            success=True,
        )

        assert result.files_added == 5
        assert result.files_removed == 2
        assert result.files_modified == 3
        assert result.chunks_added == 50
        assert result.chunks_removed == 20
        assert result.time_taken == 1.5
        assert result.success is True
        assert result.error is None

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = IncrementalIndexResult(
            files_added=5,
            files_removed=2,
            files_modified=3,
            chunks_added=50,
            chunks_removed=20,
            time_taken=1.5,
            success=True,
            error="Test error",
        )

        result_dict = result.to_dict()

        expected = {
            "files_added": 5,
            "files_removed": 2,
            "files_modified": 3,
            "chunks_added": 50,
            "chunks_removed": 20,
            "time_taken": 1.5,
            "success": True,
            "error": "Test error",
        }

        assert result_dict == expected

    def test_error_result(self):
        """Test creating error result."""
        result = IncrementalIndexResult(
            files_added=0,
            files_removed=0,
            files_modified=0,
            chunks_added=0,
            chunks_removed=0,
            time_taken=0.1,
            success=False,
            error="Test error message",
        )

        assert result.success is False
        assert result.error == "Test error message"


class TestIncrementalIndexer:
    """Test incremental indexer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Create test files
        self.test_files = {
            "main.py": "def main(): print('Hello, World!')",
            "utils.py": "def utility_function(): return True",
            "config.py": "CONFIG = {'debug': True}",
        }

        for filename, content in self.test_files.items():
            (self.project_path / filename).write_text(content)

        # Mock components
        self.mock_indexer = Mock()
        self.mock_embedder = Mock()
        self.mock_chunker = Mock()
        self.mock_snapshot_manager = Mock()

    def test_initialization(self):
        """Test incremental indexer initialization."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        assert indexer.indexer == self.mock_indexer
        assert indexer.embedder == self.mock_embedder
        assert indexer.chunker == self.mock_chunker
        assert indexer.snapshot_manager == self.mock_snapshot_manager
        assert indexer.change_detector is not None

    def test_initialization_with_defaults(self):
        """Test initialization with default components."""
        with (
            patch("search.incremental_indexer.Indexer") as mock_indexer_class,
            patch("search.incremental_indexer.CodeEmbedder") as mock_embedder_class,
            patch(
                "search.incremental_indexer.MultiLanguageChunker"
            ) as mock_chunker_class,
            patch("search.incremental_indexer.SnapshotManager") as mock_snapshot_class,
        ):
            IncrementalIndexer()

            mock_indexer_class.assert_called_once()
            mock_embedder_class.assert_called_once()
            mock_chunker_class.assert_called_once()
            mock_snapshot_class.assert_called_once()

    def test_detect_changes(self):
        """Test change detection."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock change detector
        mock_changes = Mock()
        mock_dag = Mock()
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )

        changes, dag = indexer.detect_changes(str(self.project_path))

        assert changes == mock_changes
        assert dag == mock_dag
        indexer.change_detector.detect_changes_from_snapshot.assert_called_once_with(
            str(self.project_path)
        )

    def test_full_index_no_snapshot(self):
        """Test full indexing when no snapshot exists."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock no snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = False

        # Mock components for full index
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["main.py", "utils.py", "config.py"]
            mock_dag_class.return_value = mock_dag

            # Mock chunker
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.is_supported.return_value = True
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            # Mock embedder
            mock_embedding_result = Mock()
            mock_embedding_result.metadata = {}
            self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

            result = indexer.incremental_index(str(self.project_path), "test_project")

            assert result.success is True
            assert result.files_added == 3
            assert (
                result.chunks_added == 1
            )  # embed_chunks returns 1 result for all chunks
            assert result.files_removed == 0
            assert result.files_modified == 0

            # Verify components were called
            self.mock_indexer.clear_index.assert_called_once()
            self.mock_embedder.embed_chunks.assert_called()
            self.mock_indexer.add_embeddings.assert_called_once()
            self.mock_indexer.save_index.assert_called_once()

    def test_incremental_update_no_changes(self):
        """Test incremental update when no changes detected."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock no changes
        mock_changes = Mock()
        mock_changes.has_changes.return_value = False
        mock_dag = Mock()
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.files_added == 0
        assert result.files_removed == 0
        assert result.files_modified == 0
        assert result.chunks_added == 0
        assert result.chunks_removed == 0

    def test_incremental_update_with_changes(self):
        """Test incremental update with detected changes."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock changes
        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = ["new_file.py"]
        mock_changes.removed = ["old_file.py"]
        mock_changes.modified = ["changed_file.py"]
        mock_dag = Mock()

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(
            return_value=["old_file.py", "changed_file.py"]
        )
        indexer.change_detector.get_files_to_reindex = Mock(
            return_value=["new_file.py", "changed_file.py"]
        )

        # Mock batch removal (now enabled by default)
        self.mock_indexer.remove_multiple_files = Mock(
            return_value=10
        )  # 2 files * 5 chunks

        # Mock successful validation
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        # Mock adding new chunks
        mock_chunk = Mock()
        mock_chunk.content = "test content"
        self.mock_chunker.is_supported.return_value = True
        self.mock_chunker.chunk_file.return_value = [mock_chunk]

        mock_embedding_result = Mock()
        mock_embedding_result.metadata = {}
        self.mock_embedder.embed_chunks.return_value = [
            mock_embedding_result,
            mock_embedding_result,
        ]

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.files_added == 1
        assert result.files_removed == 1
        assert result.files_modified == 1
        assert result.chunks_removed == 10  # 2 files * 5 chunks each
        assert result.chunks_added == 2

    def test_error_handling_full_index(self):
        """Test error handling during full index."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock no snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = False

        # Mock error during DAG building
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag_class.side_effect = Exception("DAG build failed")

            result = indexer.incremental_index(str(self.project_path), "test_project")

            assert result.success is False
            assert result.error == "DAG build failed"
            assert result.chunks_added == 0

    def test_error_handling_incremental_update(self):
        """Test error handling during incremental update."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock error during change detection
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            side_effect=Exception("Change detection failed")
        )

        # Mock recovery also fails
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag_class.side_effect = Exception("Recovery also failed")

            result = indexer.incremental_index(str(self.project_path), "test_project")

            assert result.success is False
            assert (
                "Change detection failed" in result.error
                or "Recovery also failed" in result.error
            )

    def test_get_indexing_stats(self):
        """Test getting indexing statistics."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock metadata
        mock_metadata = {"project_name": "test_project", "chunks_indexed": 100}
        self.mock_snapshot_manager.load_metadata.return_value = mock_metadata
        self.mock_snapshot_manager.get_snapshot_age.return_value = 300  # 5 minutes
        self.mock_indexer.get_index_size.return_value = 95

        stats = indexer.get_indexing_stats(str(self.project_path))

        assert stats["project_name"] == "test_project"
        assert stats["chunks_indexed"] == 100
        assert stats["current_chunks"] == 95
        assert stats["snapshot_age"] == 300

    def test_get_indexing_stats_no_metadata(self):
        """Test getting stats when no metadata exists."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.load_metadata.return_value = None

        stats = indexer.get_indexing_stats(str(self.project_path))
        assert stats is None

    def test_needs_reindex_no_snapshot(self):
        """Test needs_reindex when no snapshot exists."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = False

        assert indexer.needs_reindex(str(self.project_path)) is True

    def test_needs_reindex_old_snapshot(self):
        """Test needs_reindex when snapshot is too old."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True
        self.mock_snapshot_manager.get_snapshot_age.return_value = 600  # 10 minutes

        assert indexer.needs_reindex(str(self.project_path), max_age_minutes=5) is True

    def test_needs_reindex_fresh_snapshot(self):
        """Test needs_reindex when snapshot is fresh but has changes."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True
        self.mock_snapshot_manager.get_snapshot_age.return_value = 120  # 2 minutes
        indexer.change_detector.quick_check = Mock(return_value=True)

        assert indexer.needs_reindex(str(self.project_path), max_age_minutes=5) is True

    def test_needs_reindex_no_changes(self):
        """Test needs_reindex when no reindexing is needed."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True
        self.mock_snapshot_manager.get_snapshot_age.return_value = 120  # 2 minutes
        indexer.change_detector.quick_check = Mock(return_value=False)

        assert indexer.needs_reindex(str(self.project_path), max_age_minutes=5) is False

    def test_auto_reindex_if_needed_reindex_required(self):
        """Test auto-reindex when reindexing is needed."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock needs reindex
        indexer.needs_reindex = Mock(return_value=True)

        # Mock successful incremental index
        mock_result = IncrementalIndexResult(
            files_added=5,
            files_removed=0,
            files_modified=0,
            chunks_added=50,
            chunks_removed=0,
            time_taken=1.0,
            success=True,
        )
        indexer.incremental_index = Mock(return_value=mock_result)

        result = indexer.auto_reindex_if_needed(str(self.project_path))

        assert result == mock_result
        indexer.needs_reindex.assert_called_once()
        indexer.incremental_index.assert_called_once()

    def test_auto_reindex_if_needed_no_reindex(self):
        """Test auto-reindex when no reindexing is needed."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock no reindex needed
        indexer.needs_reindex = Mock(return_value=False)

        result = indexer.auto_reindex_if_needed(str(self.project_path))

        assert result.success is True
        assert result.files_added == 0
        assert result.chunks_added == 0
        indexer.needs_reindex.assert_called_once()

    def test_force_full_reindex(self):
        """Test force full reindex functionality."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock components for full index
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["main.py"]
            mock_dag_class.return_value = mock_dag

            self.mock_chunker.is_supported.return_value = True
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            mock_embedding_result = Mock()
            mock_embedding_result.metadata = {}
            self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

            result = indexer.incremental_index(
                str(self.project_path), "test_project", force_full=True
            )

            assert result.success is True
            self.mock_indexer.clear_index.assert_called_once()

    def test_chunking_error_handling(self):
        """Test handling of chunking errors."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock no snapshot exists (triggers full index)
        self.mock_snapshot_manager.has_snapshot.return_value = False

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["error_file.py", "good_file.py"]
            mock_dag_class.return_value = mock_dag

            # Mock chunker - one file fails, one succeeds
            def chunker_side_effect(file_path):
                if "error_file" in file_path:
                    raise Exception("Chunking failed")
                else:
                    mock_chunk = Mock()
                    mock_chunk.content = "test content"
                    return [mock_chunk]

            self.mock_chunker.is_supported.return_value = True
            self.mock_chunker.chunk_file.side_effect = chunker_side_effect

            mock_embedding_result = Mock()
            mock_embedding_result.metadata = {}
            self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

            result = indexer.incremental_index(str(self.project_path), "test_project")

            # Should succeed despite one file failing
            assert result.success is True
            assert result.chunks_added == 1  # Only one file succeeded

    def test_embedding_error_handling(self):
        """Test handling of embedding errors."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock no snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = False

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["test_file.py"]
            mock_dag_class.return_value = mock_dag

            self.mock_chunker.is_supported.return_value = True
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            # Mock embedding failure
            self.mock_embedder.embed_chunks.side_effect = Exception("Embedding failed")

            result = indexer.incremental_index(str(self.project_path), "test_project")

            # Should succeed with zero chunks added
            assert result.success is True
            assert result.chunks_added == 0

    def test_batch_removal_with_validation(self):
        """Test batch removal with index consistency validation."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock changes with file removals
        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = []
        mock_changes.removed = ["old_file1.py", "old_file2.py"]
        mock_changes.modified = []
        mock_dag = Mock()

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(
            return_value=["old_file1.py", "old_file2.py"]
        )
        indexer.change_detector.get_files_to_reindex = Mock(return_value=[])

        # Mock batch removal
        self.mock_indexer.remove_multiple_files = Mock(
            return_value=10
        )  # 2 files * 5 chunks

        # Mock successful validation
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.files_removed == 2
        assert result.chunks_removed == 10  # 2 files * 5 chunks each
        # Verify validation was called
        self.mock_indexer.validate_index_consistency.assert_called_once()

    def test_batch_removal_validation_failure_triggers_full_reindex(self):
        """Test that validation failure triggers full re-index recovery."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock changes with file removals
        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = []
        mock_changes.removed = ["file1.py"]
        mock_changes.modified = []
        mock_dag = Mock()

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(return_value=["file1.py"])
        indexer.change_detector.get_files_to_reindex = Mock(return_value=[])

        # Mock file removal
        self.mock_indexer.remove_file_chunks.return_value = 5

        # Mock FAILED validation (index corrupted)
        self.mock_indexer.validate_index_consistency = Mock(
            return_value=(False, ["FAISS index size mismatch"])
        )

        # Mock full re-index components
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_full_dag = Mock()
            mock_full_dag.get_all_files.return_value = ["remaining_file.py"]
            mock_dag_class.return_value = mock_full_dag

            self.mock_chunker.is_supported.return_value = True
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            mock_embedding_result = Mock()
            mock_embedding_result.metadata = {}
            self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

            result = indexer.incremental_index(str(self.project_path), "test_project")

            # Should succeed via full re-index recovery
            assert result.success is True
            # Verify clear_index was called (recovery)
            self.mock_indexer.clear_index.assert_called()
            # Verify validation was attempted
            self.mock_indexer.validate_index_consistency.assert_called_once()

    def test_error_recovery_via_full_reindex(self):
        """Test that errors during incremental indexing trigger full re-index recovery."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock change detection that will fail
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            side_effect=RuntimeError("Index corruption detected")
        )

        # Mock successful full re-index
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["file.py"]
            mock_dag_class.return_value = mock_dag

            self.mock_chunker.is_supported.return_value = True
            mock_chunk = Mock()
            mock_chunk.content = "test"
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            mock_embedding_result = Mock()
            mock_embedding_result.metadata = {}
            self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

            result = indexer.incremental_index(str(self.project_path), "test_project")

            # Should succeed via recovery
            assert result.success is True
            assert result.chunks_added == 1
            # Verify clear_index was called during recovery
            self.mock_indexer.clear_index.assert_called()

    def test_batch_removal_with_multiple_files(self):
        """Test batch removal handles multiple file deletions correctly."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock changes with many file removals
        files_to_remove = [f"file{i}.py" for i in range(10)]
        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = []
        mock_changes.removed = files_to_remove
        mock_changes.modified = []
        mock_dag = Mock()

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(return_value=files_to_remove)
        indexer.change_detector.get_files_to_reindex = Mock(return_value=[])

        # Mock batch removal returns 30 chunks total (10 files * 3 chunks each)
        self.mock_indexer.remove_multiple_files = Mock(return_value=30)

        # Mock successful validation
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.files_removed == 10
        assert result.chunks_removed == 30  # 10 files * 3 chunks each
        # Verify batch removal was called once with all files
        self.mock_indexer.remove_multiple_files.assert_called_once()

    def test_recovery_failure_returns_error(self):
        """Test that recovery failure is properly reported."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists
        self.mock_snapshot_manager.has_snapshot.return_value = True

        # Mock incremental indexing failure
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            side_effect=RuntimeError("Original error")
        )

        # Mock full re-index also fails
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag_class.side_effect = Exception("Recovery failed")

            result = indexer.incremental_index(str(self.project_path), "test_project")

            # Should fail with recovery error (since _full_index catches and returns its own error)
            assert result.success is False
            # The error message will be from _full_index, which returns "Recovery failed"
            assert "Recovery failed" in result.error or "failed" in result.error.lower()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
