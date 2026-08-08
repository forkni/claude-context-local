"""Tests for incremental indexing functionality."""

import dataclasses
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

from search.filters import PathFilter
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
            bm25_resynced=True,
            bm25_resync_count=100,
        )

        result_dict = result.to_dict()

        # Subset validation, not exact equality: to_dict() is asdict(self), so its
        # keys track whatever fields IncrementalIndexResult currently declares (e.g.
        # in-flight call-graph injection fields not yet present on every branch).
        # See tests/TESTING_GUIDE.md "Use subset validation for metadata".
        expected_subset = {
            "files_added": 5,
            "files_removed": 2,
            "files_modified": 3,
            "chunks_added": 50,
            "chunks_removed": 20,
            "time_taken": 1.5,
            "success": True,
            "error": "Test error",
            "bm25_resynced": True,
            "bm25_resync_count": 100,
        }
        for key, value in expected_subset.items():
            assert result_dict[key] == value

        # Completeness check: to_dict() must still surface every dataclass field
        # (catches a field silently dropped from the asdict() conversion).
        field_names = {f.name for f in dataclasses.fields(IncrementalIndexResult)}
        assert result_dict.keys() == field_names

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
        self.mock_indexer.resync_if_desynced.return_value = (False, 0)
        # Default to a clean bill of health: _full_index (and the incremental
        # batch-removal path) now unconditionally consult validate_index_consistency
        # via _consistency_target(), and a bare Mock()'s auto-created attribute
        # returns an unconfigured Mock() that can't be unpacked into (is_valid,
        # issues). Tests that specifically exercise the failure path override this.
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))
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

    def test_initialization_with_defaults(self, tmp_path):
        """Test initialization with default components."""
        with (
            patch("search.incremental_indexer.Indexer") as mock_indexer_class,
            patch("search.incremental_indexer.CodeEmbedder") as mock_embedder_class,
            patch(
                "search.incremental_indexer.MultiLanguageChunker"
            ) as mock_chunker_class,
            patch("search.incremental_indexer.SnapshotManager") as mock_snapshot_class,
        ):
            # Mock SnapshotManager to use temp directory
            mock_snapshot_instance = Mock()
            mock_snapshot_instance.storage_dir = tmp_path / "merkle"
            mock_snapshot_class.return_value = mock_snapshot_instance

            # Pass explicit snapshot_manager to avoid production pollution
            IncrementalIndexer(snapshot_manager=mock_snapshot_instance)

            mock_indexer_class.assert_called_once()
            mock_embedder_class.assert_called_once()
            mock_chunker_class.assert_called_once()
            # SnapshotManager not called when passed explicitly
            mock_snapshot_class.assert_not_called()

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

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_full_index_no_snapshot(self, mock_release):
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
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
            mock_dag_class.return_value = mock_dag

            # Mock chunker
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.is_supported.return_value = True
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            # Mock embedder — return one result per input chunk (1:1,
            # order-preserved), matching the real embed_chunks contract.
            # index_write_stage.py now zips the input chunks against this
            # return value with strict=True, so a fixed-length mock here
            # (e.g. always 1 result) would raise instead of silently
            # truncating.
            self.mock_embedder.embed_chunks.side_effect = lambda chunks, **kwargs: [
                Mock(metadata={}) for _ in chunks
            ]

            result = indexer.incremental_index(str(self.project_path), "test_project")

            assert result.success is True
            assert result.files_added == 3
            assert (
                result.chunks_added == 3
            )  # one embed_chunks result per chunk (3 files -> 3 chunks)
            assert result.files_removed == 0
            assert result.files_modified == 0

            # Verify components were called
            self.mock_indexer.clear_index.assert_called_once()
            self.mock_embedder.embed_chunks.assert_called()
            self.mock_indexer.add_embeddings.assert_called_once()
            self.mock_indexer.save_indices.assert_called_once()

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
        mock_dag.get_all_files.return_value = []  # Mock get_all_files to return empty list
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
        mock_dag.get_all_files.return_value = [
            "new_file.py",
            "old_file.py",
            "changed_file.py",
        ]
        mock_dag.path_filter = PathFilter(None, None, self.project_path)

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
        self.mock_indexer.remove_files = Mock(return_value=10)  # 2 files * 5 chunks

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

    def test_add_new_chunks_passes_partial_pass_cache_to_embedder(self):
        """_add_new_chunks must resolve the chunk cache and forward cache_full_pass=False.

        Regression guard for Fix 3: this embed site previously ran cold every
        time. cache_full_pass=False matters because a full-pass eviction cap
        here would wrongly collapse a cache built by prior full indexes down
        to this run's handful of live keys — see ChunkEmbeddingCache._evict.
        """
        self.mock_indexer.storage_dir = "/fake/storage_dir"
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True

        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = ["new_file.py"]
        mock_changes.removed = []
        mock_changes.modified = []
        mock_dag = Mock()
        mock_dag.get_all_files.return_value = ["new_file.py"]
        mock_dag.path_filter = PathFilter(None, None, self.project_path)

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(return_value=[])
        indexer.change_detector.get_files_to_reindex = Mock(
            return_value=["new_file.py"]
        )

        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        mock_chunk = Mock()
        mock_chunk.content = "test content"
        self.mock_chunker.is_supported.return_value = True
        self.mock_chunker.chunk_file.return_value = [mock_chunk]

        mock_embedding_result = Mock()
        mock_embedding_result.metadata = {}
        self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

        sentinel_cache = Mock()
        with patch(
            "search.incremental_indexer.resolve_chunk_cache",
            return_value=sentinel_cache,
        ) as mock_resolve:
            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        mock_resolve.assert_called_once_with("/fake/storage_dir", self.mock_embedder)
        call_kwargs = self.mock_embedder.embed_chunks.call_args.kwargs
        assert call_kwargs["cache"] is sentinel_cache
        assert call_kwargs["cache_full_pass"] is False

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_error_handling_full_index(self, mock_release):
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

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_force_full_reindex(self, mock_release):
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
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
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

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_chunking_error_handling(self, mock_release):
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
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
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

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_embedding_error_handling(self, mock_release):
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
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
            mock_dag_class.return_value = mock_dag

            self.mock_chunker.is_supported.return_value = True
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            # Mock embedding failure
            self.mock_embedder.embed_chunks.side_effect = Exception("Embedding failed")

            result = indexer.incremental_index(str(self.project_path), "test_project")

            # Embedding failure is reported as a hard failure — no bogus snapshot
            assert result.success is False
            assert result.error is not None
            assert "Embedding failed" in result.error
            assert result.chunks_added == 0
            self.mock_snapshot_manager.save_snapshot.assert_not_called()

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
        mock_dag.get_all_files.return_value = ["old_file1.py", "old_file2.py"]
        mock_dag.path_filter = PathFilter(None, None, self.project_path)

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(
            return_value=["old_file1.py", "old_file2.py"]
        )
        indexer.change_detector.get_files_to_reindex = Mock(return_value=[])

        # Mock batch removal
        self.mock_indexer.remove_files = Mock(return_value=10)  # 2 files * 5 chunks

        # Mock successful validation
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.files_removed == 2
        assert result.chunks_removed == 10  # 2 files * 5 chunks each
        # Verify validation was called
        self.mock_indexer.validate_index_consistency.assert_called_once()

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_batch_removal_validation_failure_triggers_full_reindex(self, mock_release):
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
        mock_dag.path_filter = PathFilter(None, None, self.project_path)

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(return_value=["file1.py"])
        indexer.change_detector.get_files_to_reindex = Mock(return_value=[])

        # Mock file removal
        self.mock_indexer.remove_files = Mock(return_value=5)

        # Mock FAILED validation on the incremental batch-removal check (index
        # corrupted), then a clean bill of health on the second call -- made by
        # _full_index's own tail check once recovery's clear_index() + reindex
        # has actually rebuilt things. Fix 2/3 wire _full_index's completion to
        # re-validate, so a mock that stayed permanently broken would (correctly)
        # make recovery itself report success=False; this test is about recovery
        # being *triggered* and *succeeding*, not about recovery being unable to
        # fix a still-broken index.
        self.mock_indexer.validate_index_consistency = Mock(
            side_effect=[
                (False, ["FAISS index size mismatch"]),
                (True, []),
            ]
        )

        # Mock full re-index components
        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_full_dag = Mock()
            mock_full_dag.get_all_files.return_value = ["remaining_file.py"]
            mock_full_dag.path_filter = PathFilter(None, None, self.project_path)
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
            # Verify validation was attempted twice: once by the incremental
            # batch-removal check (which fails and triggers recovery), and once
            # more by _full_index's own tail check once recovery completes.
            assert self.mock_indexer.validate_index_consistency.call_count == 2

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_error_recovery_via_full_reindex(self, mock_release):
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
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
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
        mock_dag.get_all_files.return_value = files_to_remove
        mock_dag.path_filter = PathFilter(None, None, self.project_path)

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(return_value=files_to_remove)
        indexer.change_detector.get_files_to_reindex = Mock(return_value=[])

        # Mock batch removal returns 30 chunks total (10 files * 3 chunks each)
        self.mock_indexer.remove_files = Mock(return_value=30)

        # Mock successful validation
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.files_removed == 10
        assert result.chunks_removed == 30  # 10 files * 3 chunks each
        # Verify batch removal was called once with all files
        self.mock_indexer.remove_files.assert_called_once()

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

    def test_auto_sync_triggered_when_desync_exceeds_threshold(self):
        """Test auto-sync triggered when desync > 10%."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Mock snapshot exists with changes so auto-sync code is reached
        self.mock_snapshot_manager.has_snapshot.return_value = True

        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = []
        mock_changes.removed = []
        mock_changes.modified = ["modified.py"]  # At least one change
        mock_dag = Mock()
        mock_dag.get_all_files.return_value = ["modified.py"]
        mock_dag.path_filter = PathFilter(None, None, self.project_path)
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )

        # Mock chunking and embedding
        self.mock_chunker.is_supported.return_value = True
        mock_chunk = Mock()
        mock_chunk.content = "test content"
        self.mock_chunker.chunk_file.return_value = [mock_chunk]

        mock_embedding_result = Mock()
        mock_embedding_result.metadata = {}
        self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

        # Mock resync_if_desynced to report significant desync (>10%)
        self.mock_indexer.resync_if_desynced.return_value = (True, 100)
        # Prevent the incremental path from failing at index consistency check
        self.mock_indexer.validate_index_consistency.return_value = (True, [])

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.bm25_resynced is True
        assert result.bm25_resync_count == 100
        self.mock_indexer.resync_if_desynced.assert_called_once_with("INCREMENTAL")

    def test_auto_sync_not_triggered_when_desync_below_threshold(self):
        """Test auto-sync NOT triggered when desync < 10%."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True

        mock_changes = Mock()
        mock_changes.has_changes.return_value = False
        mock_dag = Mock()
        mock_dag.get_all_files.return_value = []
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )

        # setUp default: resync_if_desynced returns (False, 0); no changes → early-exit

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.bm25_resynced is False
        assert result.bm25_resync_count == 0
        self.mock_indexer.resync_if_desynced.assert_not_called()

    def test_auto_sync_not_triggered_when_counts_equal(self):
        """Test auto-sync NOT triggered when BM25 and dense counts are equal."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True

        mock_changes = Mock()
        mock_changes.has_changes.return_value = False
        mock_dag = Mock()
        mock_dag.get_all_files.return_value = []
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )

        # setUp default: resync_if_desynced returns (False, 0); no changes → early-exit

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        assert result.bm25_resynced is False
        assert result.bm25_resync_count == 0
        self.mock_indexer.resync_if_desynced.assert_not_called()

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_filter_persistence_in_full_index(self, mock_release):
        """Test that filters are preserved when _full_index is triggered."""
        # Create indexer WITH filters
        include_dirs = ["src/", "lib/"]
        exclude_dirs = ["tests/", "benchmarks/"]
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
            include_dirs=include_dirs,
            exclude_dirs=exclude_dirs,
        )

        # Real files under the include targets. MerkleDAG is NOT mocked in
        # this test (it exercises the real DAG's directory_filter), and the
        # PathFilter hard-fail (all_includes_unmatched) now aborts full
        # indexing if every include pattern matches zero real files — so at
        # least one file per pattern must exist on disk for the walk to find.
        (self.project_path / "src").mkdir(parents=True)
        (self.project_path / "src" / "main.py").write_text("x = 1")
        (self.project_path / "lib").mkdir(parents=True)
        (self.project_path / "lib" / "utils.py").write_text("y = 2")

        # Mock that no snapshot exists (triggers full index path)
        self.mock_snapshot_manager.has_snapshot.return_value = False

        # Mock chunker/embedder so the real MerkleDAG's discovered files can
        # be "chunked" and "embedded" without touching real file contents.
        self.mock_chunker.is_supported.return_value = True
        mock_chunk = Mock()
        mock_chunk.content = "test content"
        self.mock_chunker.chunk_file.return_value = [mock_chunk]
        self.mock_embedder.embed_chunks.side_effect = lambda chunks, **kwargs: [
            Mock(metadata={}) for _ in chunks
        ]

        # Mock save_snapshot to verify filters are saved
        saved_dag = None

        def capture_dag(dag, metadata):
            nonlocal saved_dag
            saved_dag = dag

        self.mock_snapshot_manager.save_snapshot = Mock(side_effect=capture_dag)

        # Trigger full index via incremental_index
        result = indexer.incremental_index(str(self.project_path), "test_project")

        # Verify operation succeeded
        assert result.success is True

        # Verify the indexer retained filters
        assert indexer.include_dirs == include_dirs
        assert indexer.exclude_dirs == exclude_dirs

        # Verify the DAG was created with filters
        assert saved_dag is not None
        assert saved_dag.directory_filter is not None
        assert saved_dag.directory_filter.include_dirs == include_dirs
        assert saved_dag.directory_filter.exclude_dirs == exclude_dirs

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_filter_recovery_from_snapshot_in_full_index(self, mock_release):
        """Test that filters are recovered from snapshot if not passed to indexer."""
        from search.filters import DirectoryFilter

        # Create indexer WITHOUT filters
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
            include_dirs=None,  # No filters passed!
            exclude_dirs=None,
        )

        # Create a mock snapshot WITH filters
        include_dirs = ["src/", "lib/"]
        exclude_dirs = ["tests/"]
        mock_dag = Mock()
        mock_dag.directory_filter = DirectoryFilter(include_dirs, exclude_dirs)

        self.mock_snapshot_manager.load_snapshot.return_value = mock_dag
        self.mock_snapshot_manager.has_snapshot.return_value = (
            False  # Triggers full index
        )

        # Real files under the recovered include targets. The NEW DAG built
        # by _full_index (after recovering include_dirs/exclude_dirs from
        # the mock snapshot above) is a real, unmocked MerkleDAG — the
        # PathFilter hard-fail (all_includes_unmatched) aborts full indexing
        # if every include pattern matches zero real files.
        (self.project_path / "src").mkdir(parents=True)
        (self.project_path / "src" / "main.py").write_text("x = 1")
        (self.project_path / "lib").mkdir(parents=True)
        (self.project_path / "lib" / "utils.py").write_text("y = 2")

        self.mock_chunker.is_supported.return_value = True
        mock_chunk = Mock()
        mock_chunk.content = "test content"
        self.mock_chunker.chunk_file.return_value = [mock_chunk]
        self.mock_embedder.embed_chunks.side_effect = lambda chunks, **kwargs: [
            Mock(metadata={}) for _ in chunks
        ]

        # Mock save_snapshot
        saved_dag = None

        def capture_dag(dag, metadata):
            nonlocal saved_dag
            saved_dag = dag

        self.mock_snapshot_manager.save_snapshot = Mock(side_effect=capture_dag)

        # Trigger full index
        result = indexer.incremental_index(str(self.project_path), "test_project")

        # Verify operation succeeded
        assert result.success is True

        # Verify filters were recovered from snapshot
        assert indexer.include_dirs == include_dirs
        assert indexer.exclude_dirs == exclude_dirs

        # Verify the new DAG was created with recovered filters
        assert saved_dag is not None
        assert saved_dag.directory_filter is not None
        assert saved_dag.directory_filter.include_dirs == include_dirs
        assert saved_dag.directory_filter.exclude_dirs == exclude_dirs

    def _mock_dependency_only_path_filter(
        self,
        only_dependency_paths_matched: bool,
        all_includes_unmatched: bool = False,
        dependency_segments=None,
    ) -> Mock:
        """Build a Mock standing in for dag.path_filter, configured for the
        _full_index guard-precedence tests below. Mocking the predicate
        methods directly (rather than exercising a real PathFilter) tests
        the guard's *wiring* into _full_index -- the predicates' own logic
        is covered by test_dir_patterns.py::TestPatternClassification."""
        mock_path_filter = Mock()
        mock_path_filter.unmatched_patterns.return_value = []
        mock_path_filter.all_includes_unmatched.return_value = all_includes_unmatched
        mock_path_filter.should_index_file.return_value = True
        mock_path_filter.only_dependency_paths_matched.return_value = (
            only_dependency_paths_matched
        )
        mock_path_filter.dependency_segments.return_value = (
            dependency_segments
            if dependency_segments is not None
            else ["venv", "site-packages"]
        )
        return mock_path_filter

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_full_index_aborts_when_only_dependency_paths_matched(self, mock_release):
        """Backstop guard: a narrowing include list (or include_exclusive)
        that resolves entirely inside a dependency tree must hard-abort
        _full_index BEFORE delete_snapshot/clear_index run -- this is the
        survival property the guard exists for (see incremental_indexer.py
        _full_index, between the all_includes_unmatched check and
        delete_snapshot)."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
            include_dirs=["site-packages/torch"],
        )
        self.mock_snapshot_manager.has_snapshot.return_value = False

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = [
                "venv/Lib/site-packages/torch/mod.py"
            ]
            mock_dag.path_filter = self._mock_dependency_only_path_filter(
                only_dependency_paths_matched=True,
                dependency_segments=["venv", "site-packages"],
            )
            mock_dag_class.return_value = mock_dag
            self.mock_chunker.is_supported.return_value = True

            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is False
        assert "dependency tree" in result.error
        assert "include_exclusive=True" in result.error
        self.mock_snapshot_manager.delete_snapshot.assert_not_called()
        self.mock_indexer.clear_index.assert_not_called()

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_full_index_all_includes_unmatched_takes_precedence(self, mock_release):
        """all_includes_unmatched (a typo'd/absent pattern) is checked first
        and gives a more specific error than the dependency-only guard --
        the guard must not even be consulted once that abort has already
        fired."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
            include_dirs=["nonexistent_dir"],
        )
        self.mock_snapshot_manager.has_snapshot.return_value = False

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = []
            mock_dag.path_filter = self._mock_dependency_only_path_filter(
                only_dependency_paths_matched=True,
                all_includes_unmatched=True,
            )
            mock_dag_class.return_value = mock_dag
            self.mock_chunker.is_supported.return_value = True

            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is False
        assert "matched 0 files" in result.error
        assert "dependency tree" not in result.error
        mock_dag.path_filter.only_dependency_paths_matched.assert_not_called()
        self.mock_snapshot_manager.delete_snapshot.assert_not_called()
        self.mock_indexer.clear_index.assert_not_called()

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_full_index_include_exclusive_downgrades_guard_to_warning(
        self, mock_release
    ):
        """include_exclusive=True is the deliberate override: the guard must
        still fire (log a warning) but let indexing proceed rather than
        aborting."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
            include_dirs=["site-packages/torch"],
            include_exclusive=True,
        )
        self.mock_snapshot_manager.has_snapshot.return_value = False

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = [
                "venv/Lib/site-packages/torch/mod.py"
            ]
            mock_dag.path_filter = self._mock_dependency_only_path_filter(
                only_dependency_paths_matched=True,
                dependency_segments=["venv", "site-packages"],
            )
            mock_dag_class.return_value = mock_dag
            self.mock_chunker.is_supported.return_value = True
            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.chunk_file.return_value = [mock_chunk]
            self.mock_embedder.embed_chunks.side_effect = lambda chunks, **kwargs: [
                Mock(metadata={}) for _ in chunks
            ]

            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        self.mock_snapshot_manager.delete_snapshot.assert_called_once()
        self.mock_indexer.clear_index.assert_called_once()

    def test_incremental_path_never_applies_dependency_only_guard(self):
        """The guard lives in _full_index only -- _add_new_chunks (the
        incremental path) legitimately sees dependency-only file sets after
        e.g. a `pip install`, and must never consult
        only_dependency_paths_matched at all."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = True

        mock_changes = Mock()
        mock_changes.has_changes.return_value = True
        mock_changes.added = ["venv/Lib/site-packages/torch/mod.py"]
        mock_changes.removed = []
        mock_changes.modified = []
        mock_dag = Mock()
        mock_dag.get_all_files.return_value = ["venv/Lib/site-packages/torch/mod.py"]
        mock_dag.path_filter = self._mock_dependency_only_path_filter(
            only_dependency_paths_matched=True,
        )

        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )
        indexer.change_detector.get_files_to_remove = Mock(return_value=[])
        indexer.change_detector.get_files_to_reindex = Mock(
            return_value=["venv/Lib/site-packages/torch/mod.py"]
        )

        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        mock_chunk = Mock()
        mock_chunk.content = "test content"
        self.mock_chunker.is_supported.return_value = True
        self.mock_chunker.chunk_file.return_value = [mock_chunk]

        mock_embedding_result = Mock()
        mock_embedding_result.metadata = {}
        self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

        result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        mock_dag.path_filter.only_dependency_paths_matched.assert_not_called()

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_write_pipeline_rebound_after_resource_refresh(self, mock_release):
        """IndexWriteStage must use the freshly acquired embedder/indexer after
        _release_and_verify_resources() swaps them in — not the original stale ones."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Simulate _release_and_verify_resources replacing embedder/indexer
        fresh_embedder = Mock()
        fresh_embedding_result = Mock()
        fresh_embedding_result.metadata = {}
        fresh_embedder.embed_chunks.return_value = [fresh_embedding_result]
        fresh_indexer = Mock()
        fresh_indexer.resync_if_desynced.return_value = (False, 0)
        # _full_index's tail consults self.indexer (the fresh one, post-swap) via
        # _consistency_target() -- give it the same clean default as self.mock_indexer.
        fresh_indexer.validate_index_consistency = Mock(return_value=(True, []))

        def swap_resources(project_path):
            indexer.embedder = fresh_embedder
            indexer.indexer = fresh_indexer

        mock_release.side_effect = swap_resources

        self.mock_snapshot_manager.has_snapshot.return_value = False

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["main.py"]
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
            mock_dag_class.return_value = mock_dag

            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.is_supported.return_value = True
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        # Fresh embedder must have been used — stale one must NOT
        fresh_embedder.embed_chunks.assert_called()
        self.mock_embedder.embed_chunks.assert_not_called()
        # Fresh indexer received the embeddings — stale one must NOT
        fresh_indexer.add_embeddings.assert_called()
        self.mock_indexer.add_embeddings.assert_not_called()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestConsistencyTarget:
    """_consistency_target() resolution and its wiring into _full_index.

    Regression coverage for the bug found while diagnosing the community-summary
    chunk_id collision: self.indexer is declared CodeIndexManager in type hints
    but is a HybridSearcher in production (mcp_server/tools/index_handlers.py),
    which has no validate_index_consistency method — only its .dense_index
    (a CodeIndexManager) does. The old unguarded call site was dead code on
    every production path; _consistency_target() resolves the right object.
    """

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        (self.project_path / "main.py").write_text("def main(): pass")

        self.mock_indexer = Mock()
        self.mock_indexer.resync_if_desynced.return_value = (False, 0)
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))
        self.mock_embedder = Mock()
        self.mock_chunker = Mock()
        self.mock_snapshot_manager = Mock()

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_consistency_target_resolves_through_hybrid_searcher_shaped_indexer(self):
        """Locks down the original bug. A plain MagicMock/Mock would NOT catch a
        regression here, because hasattr() is unconditionally True on one — that
        is exactly how the dead branch stayed invisible in every prior test.
        spec=HybridSearcher makes the attribute that's genuinely absent in
        production genuinely absent here too."""
        from search.hybrid_searcher import HybridSearcher
        from search.indexer import CodeIndexManager

        hybrid_like = Mock(spec=HybridSearcher)
        hybrid_like.dense_index = Mock(spec=CodeIndexManager)
        hybrid_like.dense_index.validate_index_consistency = Mock(
            return_value=(True, [])
        )

        indexer = IncrementalIndexer(
            indexer=hybrid_like,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        # Sanity check the fixture actually shapes like production: HybridSearcher
        # itself has no validate_index_consistency, only dense_index does.
        assert not hasattr(hybrid_like, "validate_index_consistency")
        assert hasattr(hybrid_like.dense_index, "validate_index_consistency")

        target = indexer._consistency_target()

        assert target is hybrid_like.dense_index

    def test_consistency_target_uses_indexer_directly_when_it_has_the_method(self):
        """Under most existing tests self.indexer is a bare CodeIndexManager
        stand-in (has validate_index_consistency itself) -- _consistency_target
        must not detour through .dense_index in that case."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        target = indexer._consistency_target()

        assert target is self.mock_indexer

    @patch.object(IncrementalIndexer, "_release_and_verify_resources")
    def test_full_index_validation_failure_marks_result_failed(self, mock_release):
        """Fix 2: _full_index's tail now actually re-validates. Before this fix
        the check was dead code (hasattr false on the real HybridSearcher shape)
        so a corrupted index would still come back success=True."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        self.mock_snapshot_manager.has_snapshot.return_value = False
        self.mock_indexer.validate_index_consistency = Mock(
            return_value=(False, ["metadata rows (10) != chunk_ids length (11)"])
        )

        with patch("search.incremental_indexer.MerkleDAG") as mock_dag_class:
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["main.py"]
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
            mock_dag_class.return_value = mock_dag

            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.is_supported.return_value = True
            self.mock_chunker.chunk_file.return_value = [mock_chunk]

            mock_embedding_result = Mock()
            mock_embedding_result.metadata = {}
            self.mock_embedder.embed_chunks.return_value = [mock_embedding_result]

            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is False
        assert result.error is not None
        assert "metadata rows (10) != chunk_ids length (11)" in result.error


class TestBoundedRecovery:
    """_attempt_recovery is bounded by an on-disk marker file, not an instance
    counter, because IncrementalIndexer is constructed fresh per MCP request
    (see _recovery_marker_path's docstring) — a counter on self would reset
    every call and never trip. This is the regression coverage for the "62
    consecutive recovery attempts" incident: once a recovery attempt itself
    fails, further automatic recovery must stop and name cleanup_resources
    instead of retrying against the same held file handle forever.
    """

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        self.storage_dir = Path(self.temp_dir) / "index"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.mock_indexer = Mock()
        self.mock_indexer.storage_dir = str(self.storage_dir)
        self.mock_indexer.resync_if_desynced.return_value = (False, 0)
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))
        self.mock_embedder = Mock()
        self.mock_chunker = Mock()
        self.mock_snapshot_manager = Mock()

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @property
    def marker_path(self) -> Path:
        return self.storage_dir / "index_recovery_failed.marker"

    def test_recovery_failure_writes_marker_and_names_cleanup_resources(self):
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )
        self.mock_indexer.clear_index = Mock(
            side_effect=PermissionError("metadata.db locked")
        )

        result = indexer._attempt_recovery(
            "original failure",
            str(self.project_path),
            "test_project",
            time.time(),
        )

        assert result.success is False
        assert "cleanup_resources" in result.error
        assert self.marker_path.exists(), (
            "a failed recovery attempt must leave a durable marker — an "
            "in-memory counter would reset on the next request"
        )

    def test_recovery_short_circuits_when_marker_already_present(self):
        self.marker_path.write_text("Original: x\nRecovery: y\nTimestamp: 0\n")
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )
        self.mock_indexer.clear_index = Mock()

        result = indexer._attempt_recovery(
            "original failure",
            str(self.project_path),
            "test_project",
            time.time(),
        )

        assert result.success is False
        assert "cleanup_resources" in result.error
        # a prior marker must block retrying clear_index() against the same
        # held handle, not just report the same error after retrying
        self.mock_indexer.clear_index.assert_not_called()

    def test_successful_recovery_clears_a_marker_left_by_the_attempt(self):
        """Defensive cleanup: _attempt_recovery clears any marker present
        after a successful clear_index()/_full_index() pair, even though the
        normal case never sees one appear mid-attempt (the top-of-method
        check already short-circuits a pre-existing marker). Simulates the
        marker being (re)written during the attempt to lock down that the
        success path still sweeps it."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        def _clear_index_and_leave_a_marker():
            self.marker_path.write_text("stale from a concurrent attempt")

        self.mock_indexer.clear_index = Mock(
            side_effect=_clear_index_and_leave_a_marker
        )
        successful_result = IncrementalIndexResult(
            success=True,
            files_added=0,
            files_removed=0,
            files_modified=0,
            chunks_added=0,
            chunks_removed=0,
            time_taken=0.0,
        )
        with patch.object(
            IncrementalIndexer, "_full_index", return_value=successful_result
        ):
            result = indexer._attempt_recovery(
                "original failure",
                str(self.project_path),
                "test_project",
                time.time(),
            )

        assert result.success is True
        assert not self.marker_path.exists(), (
            "a successful recovery must clear the marker so a future "
            "genuine failure can retry once, not stay permanently blocked"
        )


class TestParallelChunking:
    """Test parallel file chunking functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)

        # Create multiple test files
        self.test_files = {
            "file1.py": "def func1(): pass",
            "file2.py": "def func2(): pass",
            "file3.py": "def func3(): pass",
            "file4.py": "def func4(): pass",
            "file5.py": "def func5(): pass",
        }

        for filename, content in self.test_files.items():
            (self.project_path / filename).write_text(content)

    def test_chunk_files_parallel_enabled(self):
        """Test parallel chunking when enabled."""
        # Create indexer with mocked components
        mock_indexer = Mock()
        mock_embedder = Mock()
        mock_snapshot_manager = Mock()

        indexer = IncrementalIndexer(
            indexer=mock_indexer,
            embedder=mock_embedder,
            chunker=None,  # Use real chunker
            snapshot_manager=mock_snapshot_manager,
        )
        indexer.enable_parallel_chunking = True
        indexer.max_chunking_workers = 2

        file_paths = list(self.test_files.keys())

        # Chunk files
        chunks = indexer._chunk_files_parallel(str(self.project_path), file_paths)

        # Verify all files were chunked
        assert len(chunks) >= len(file_paths)
        assert all(isinstance(chunk, object) for chunk in chunks)

    def test_chunk_files_parallel_disabled(self):
        """Test sequential chunking when parallel is disabled."""
        # Create indexer with mocked components
        indexer = IncrementalIndexer(
            indexer=Mock(),
            embedder=Mock(),
            chunker=None,  # Use real chunker
            snapshot_manager=Mock(),
        )
        indexer.enable_parallel_chunking = False

        file_paths = list(self.test_files.keys())

        # Chunk files
        chunks = indexer._chunk_files_parallel(str(self.project_path), file_paths)

        # Verify all files were chunked
        assert len(chunks) >= len(file_paths)

    def test_chunk_files_single_file_fallback(self):
        """Test that single file falls back to sequential processing."""
        indexer = IncrementalIndexer(
            indexer=Mock(),
            embedder=Mock(),
            chunker=None,  # Use real chunker
            snapshot_manager=Mock(),
        )
        indexer.enable_parallel_chunking = True
        indexer.max_chunking_workers = 4

        # Single file - should fall back to sequential
        file_paths = ["file1.py"]

        chunks = indexer._chunk_files_parallel(str(self.project_path), file_paths)

        # Should still work
        assert len(chunks) >= 1

    def test_chunk_files_error_handling(self):
        """Test error handling in parallel chunking."""
        indexer = IncrementalIndexer(
            indexer=Mock(),
            embedder=Mock(),
            chunker=None,  # Use real chunker
            snapshot_manager=Mock(),
        )
        indexer.enable_parallel_chunking = True
        indexer.max_chunking_workers = 2

        # Include a non-existent file
        file_paths = list(self.test_files.keys()) + ["nonexistent.py"]

        # Should handle error gracefully
        chunks = indexer._chunk_files_parallel(str(self.project_path), file_paths)

        # Should still get chunks from valid files
        assert len(chunks) >= len(self.test_files)

    def test_parallel_vs_sequential_same_results(self):
        """Test that parallel and sequential produce same results."""
        indexer = IncrementalIndexer(
            indexer=Mock(),
            embedder=Mock(),
            chunker=None,  # Use real chunker
            snapshot_manager=Mock(),
        )
        file_paths = list(self.test_files.keys())

        # Get results with parallel enabled
        indexer.enable_parallel_chunking = True
        indexer.max_chunking_workers = 2
        parallel_chunks = indexer._chunk_files_parallel(
            str(self.project_path), file_paths
        )

        # Get results with parallel disabled
        indexer.enable_parallel_chunking = False
        sequential_chunks = indexer._chunk_files_parallel(
            str(self.project_path), file_paths
        )

        # Should produce same number of chunks
        assert len(parallel_chunks) == len(sequential_chunks)

        # Sort chunks by file path and content for comparison
        parallel_sorted = sorted(
            parallel_chunks, key=lambda c: (c.file_path, c.content)
        )
        sequential_sorted = sorted(
            sequential_chunks, key=lambda c: (c.file_path, c.content)
        )

        # Verify same chunks produced
        for p_chunk, s_chunk in zip(parallel_sorted, sequential_sorted, strict=False):
            assert p_chunk.content == s_chunk.content
            assert p_chunk.file_path == s_chunk.file_path

    def test_configuration_loading(self):
        """Test that parallel chunking configuration is loaded from config."""
        with patch("search.incremental_indexer.get_search_config") as mock_config:
            mock_config_obj = Mock()
            mock_config_obj.performance.enable_parallel_chunking = False
            mock_config_obj.performance.max_chunking_workers = 8
            mock_config.return_value = mock_config_obj

            indexer = IncrementalIndexer(
                indexer=Mock(),
                embedder=Mock(),
                chunker=None,
                snapshot_manager=Mock(),
            )

            assert indexer.enable_parallel_chunking is False
            assert indexer.max_chunking_workers == 8

    def test_max_workers_configuration(self):
        """Test different worker configurations."""
        indexer = IncrementalIndexer(
            indexer=Mock(),
            embedder=Mock(),
            chunker=None,  # Use real chunker
            snapshot_manager=Mock(),
        )
        file_paths = list(self.test_files.keys())

        # Test with different worker counts
        for workers in [1, 2, 4]:
            indexer.enable_parallel_chunking = True
            indexer.max_chunking_workers = workers

            chunks = indexer._chunk_files_parallel(str(self.project_path), file_paths)

            # Should work with any worker count
            assert len(chunks) >= len(self.test_files)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Direct tests for the three private helpers extracted from incremental_index
# ---------------------------------------------------------------------------


class TestZeroResult:
    """Direct tests for IncrementalIndexer._zero_result static helper."""

    def test_success_result_has_all_zero_counts(self):
        """_zero_result(success=True) returns all-zero file/chunk counts and no error."""
        import time

        before = time.time()
        result = IncrementalIndexer._zero_result(before, success=True)

        assert result.success is True
        assert result.error is None
        assert result.files_added == 0
        assert result.files_removed == 0
        assert result.files_modified == 0
        assert result.chunks_added == 0
        assert result.chunks_removed == 0
        assert result.bm25_resynced is False
        assert result.bm25_resync_count == 0
        assert result.time_taken >= 0

    def test_failure_result_carries_error_string(self):
        """_zero_result(success=False, error=...) propagates the error message."""
        import time

        result = IncrementalIndexer._zero_result(
            time.time(), success=False, error="something went wrong"
        )

        assert result.success is False
        assert result.error == "something went wrong"
        assert result.files_added == 0

    def test_no_error_by_default(self):
        """error defaults to None when not supplied."""
        import time

        result = IncrementalIndexer._zero_result(time.time(), success=True)
        assert result.error is None


class TestRestoreRepoProfile:
    """Direct tests for IncrementalIndexer._restore_repo_profile."""

    def _make_indexer(self):
        indexer = IncrementalIndexer(
            indexer=Mock(),
            embedder=Mock(),
            chunker=Mock(),
            snapshot_manager=Mock(),
        )
        # Set up parallel_chunker mock hierarchy
        indexer._parallel_chunker = Mock()
        return indexer

    def test_no_op_when_sizing_mode_not_adaptive(self):
        """Does not call load_metadata when sizing_mode != 'adaptive'."""
        indexer = self._make_indexer()

        with patch("search.incremental_indexer.get_search_config") as mock_cfg:
            mock_cfg.return_value.chunking.sizing_mode = "fixed"
            indexer._restore_repo_profile("/some/project")

        indexer.snapshot_manager.load_metadata.assert_not_called()

    def test_no_op_when_no_repo_profile_in_metadata(self):
        """Does not assign repo_profile when snapshot metadata lacks 'repo_profile'."""
        indexer = self._make_indexer()
        indexer.snapshot_manager.load_metadata.return_value = {"supported_files": 10}

        with patch("search.incremental_indexer.get_search_config") as mock_cfg:
            mock_cfg.return_value.chunking.sizing_mode = "adaptive"
            # Should not raise; repo_profile on the mock is not set to a RepoProfile
            indexer._restore_repo_profile("/some/project")

        # The mock's tree_sitter_chunker.repo_profile was not called with a RepoProfile
        # (it remains a MagicMock auto-attribute, not a RepoProfile instance)
        from chunking.repo_profiler import RepoProfile

        assigned = indexer._parallel_chunker.chunker.tree_sitter_chunker.repo_profile
        assert not isinstance(assigned, RepoProfile)

    def test_sets_repo_profile_when_present(self):
        """Sets the chunker repo_profile from snapshot metadata when adaptive."""
        indexer = self._make_indexer()
        indexer.snapshot_manager.load_metadata.return_value = {
            "repo_profile": {
                "function_count": 42,
                "p25_chars": 100,
                "p50_chars": 200,
                "p75_chars": 500,
                "p90_chars": 800,
                "mean_chars": 250,
                "max_complexity": 15,
            }
        }

        with patch("search.incremental_indexer.get_search_config") as mock_cfg:
            mock_cfg.return_value.chunking.sizing_mode = "adaptive"
            indexer._restore_repo_profile("/some/project")

        assigned = indexer._parallel_chunker.chunker.tree_sitter_chunker.repo_profile
        assert assigned.p75_chars == 500
        assert assigned.max_complexity == 15


class TestProbeWiring:
    """Auto-tuning probe pass 1 wiring in _full_index (ADR-0014).

    The probe must run exactly once per full reindex (when an active project
    storage dir is set), never on incremental passes, and a probe failure
    must never break indexing.
    """

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        for filename in ("main.py", "utils.py"):
            (self.project_path / filename).write_text("def f(): return 1")

        self.mock_indexer = Mock()
        self.mock_indexer.resync_if_desynced.return_value = (False, 0)
        # See TestIncrementalIndexer.setup_method for why this default is needed.
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "BAAI/bge-m3"
        self.mock_chunker = Mock()
        self.mock_snapshot_manager = Mock()

    def _make_indexer(self) -> IncrementalIndexer:
        return IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

    def _run_full_index(self, indexer: IncrementalIndexer) -> IncrementalIndexResult:
        """Drive a full index with the same mock scaffolding as
        test_full_index_no_snapshot."""
        self.mock_snapshot_manager.has_snapshot.return_value = False
        with (
            patch.object(IncrementalIndexer, "_release_and_verify_resources"),
            patch("search.incremental_indexer.MerkleDAG") as mock_dag_class,
        ):
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["main.py", "utils.py"]
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
            mock_dag_class.return_value = mock_dag

            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.is_supported.return_value = True
            self.mock_chunker.chunk_file.return_value = [mock_chunk]
            self.mock_embedder.embed_chunks.side_effect = lambda chunks, **kwargs: [
                Mock(metadata={}) for _ in chunks
            ]

            return indexer.incremental_index(str(self.project_path), "test_project")

    def test_full_index_calls_probe_once_and_attaches_summary(self):
        sentinel_summary = {"stage": "pre_chunking", "override_keys": ["x"]}
        indexer = self._make_indexer()

        with (
            patch(
                "search.incremental_indexer.get_active_project_storage_dir",
                return_value=self.temp_dir,
            ),
            patch(
                "search.index_probe.probe_pre_chunking",
                return_value=sentinel_summary,
            ) as mock_probe,
        ):
            result = self._run_full_index(indexer)

        assert result.success is True
        mock_probe.assert_called_once()
        args, kwargs = mock_probe.call_args
        assert args[0] == self.temp_dir  # project storage dir
        assert sorted(args[1]) == ["main.py", "utils.py"]  # supported files
        assert kwargs["embedding_model"] == "BAAI/bge-m3"
        assert result.probe_summary == sentinel_summary
        assert result.to_dict()["probe_summary"] == sentinel_summary

    def test_full_index_without_active_storage_dir_skips_probe(self):
        indexer = self._make_indexer()
        with (
            patch(
                "search.incremental_indexer.get_active_project_storage_dir",
                return_value=None,
            ),
            patch("search.index_probe.probe_pre_chunking") as mock_probe,
        ):
            result = self._run_full_index(indexer)

        assert result.success is True
        mock_probe.assert_not_called()
        assert result.probe_summary is None

    def test_incremental_pass_never_probes(self):
        indexer = self._make_indexer()
        self.mock_snapshot_manager.has_snapshot.return_value = True
        mock_changes = Mock()
        mock_changes.has_changes.return_value = False
        mock_dag = Mock()
        mock_dag.get_all_files.return_value = []
        indexer.change_detector.detect_changes_from_snapshot = Mock(
            return_value=(mock_changes, mock_dag)
        )

        with (
            patch(
                "search.incremental_indexer.get_active_project_storage_dir",
                return_value=self.temp_dir,
            ),
            patch("search.index_probe.probe_pre_chunking") as mock_probe,
        ):
            result = indexer.incremental_index(str(self.project_path), "test_project")

        assert result.success is True
        mock_probe.assert_not_called()
        assert result.probe_summary is None

    def test_probe_failure_never_breaks_indexing(self):
        indexer = self._make_indexer()
        with (
            patch(
                "search.incremental_indexer.get_active_project_storage_dir",
                return_value=self.temp_dir,
            ),
            patch(
                "search.index_probe.probe_pre_chunking",
                side_effect=RuntimeError("probe exploded"),
            ),
        ):
            result = self._run_full_index(indexer)

        assert result.success is True
        assert result.probe_summary is None


class TestModuleSummaryInjection:
    """Module-summary generation is called directly from _full_index(),
    not routed through CommunityStage.run() (relocated ahead of its removal).
    """

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        for filename in ("main.py", "utils.py"):
            (self.project_path / filename).write_text("def f(): return 1")

        self.mock_indexer = Mock()
        self.mock_indexer.resync_if_desynced.return_value = (False, 0)
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))
        self.mock_embedder = Mock()
        self.mock_embedder.model_name = "BAAI/bge-m3"
        self.mock_chunker = Mock()
        self.mock_snapshot_manager = Mock()

    def _make_indexer(self) -> IncrementalIndexer:
        return IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

    def _run_full_index(
        self,
        indexer: IncrementalIndexer,
        enable_file_summaries: bool,
        chunker_supported: bool = True,
    ) -> IncrementalIndexResult:
        """Drive a full index with the same mock scaffolding as
        TestProbeWiring._run_full_index, with enable_file_summaries controlled."""
        self.mock_snapshot_manager.has_snapshot.return_value = False
        mock_config = Mock()
        mock_config.chunking.enable_file_summaries = enable_file_summaries

        with (
            patch.object(IncrementalIndexer, "_release_and_verify_resources"),
            patch("search.incremental_indexer.MerkleDAG") as mock_dag_class,
            patch(
                "search.incremental_indexer.get_active_project_storage_dir",
                return_value=None,
            ),
            patch(
                "search.incremental_indexer.get_search_config",
                return_value=mock_config,
            ),
        ):
            mock_dag = Mock()
            mock_dag.get_all_files.return_value = ["main.py", "utils.py"]
            mock_dag.path_filter = PathFilter(None, None, self.project_path)
            mock_dag_class.return_value = mock_dag

            mock_chunk = Mock()
            mock_chunk.content = "test content"
            self.mock_chunker.is_supported.return_value = chunker_supported
            self.mock_chunker.chunk_file.return_value = [mock_chunk]
            self.mock_embedder.embed_chunks.side_effect = lambda chunks, **kwargs: [
                Mock(metadata={}) for _ in chunks
            ]

            return indexer.incremental_index(str(self.project_path), "test_project")

    def test_generates_and_appends_module_summaries(self):
        indexer = self._make_indexer()
        sentinel_summary = Mock()
        with patch.object(
            indexer._summary_stage,
            "generate_module_summaries",
            return_value=[sentinel_summary],
        ) as mock_generate:
            result = self._run_full_index(indexer, enable_file_summaries=True)

        assert result.success is True
        mock_generate.assert_called_once()
        embedded_chunks = self.mock_embedder.embed_chunks.call_args.args[0]
        assert sentinel_summary in embedded_chunks

    def test_disabled_by_config_skips_generation(self):
        indexer = self._make_indexer()
        with patch.object(
            indexer._summary_stage, "generate_module_summaries"
        ) as mock_generate:
            result = self._run_full_index(indexer, enable_file_summaries=False)

        assert result.success is True
        mock_generate.assert_not_called()

    def test_no_chunks_skips_generation(self):
        indexer = self._make_indexer()
        with patch.object(
            indexer._summary_stage, "generate_module_summaries"
        ) as mock_generate:
            result = self._run_full_index(
                indexer, enable_file_summaries=True, chunker_supported=False
            )

        assert result.success is True
        mock_generate.assert_not_called()
