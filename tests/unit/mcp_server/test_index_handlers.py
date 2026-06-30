"""Unit tests for index_handlers — file accessibility + pre-clear path guard."""

from pathlib import Path
from unittest.mock import patch

import pytest


class TestCheckFileAccessibility:
    """Test _check_file_accessibility() function for pre-index file checks."""

    def test_all_files_accessible(self, tmp_path):
        """Test when all sampled files are accessible."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        # Create test files
        files = [tmp_path / f"file{i}.py" for i in range(5)]
        for f in files:
            f.write_text("pass")

        inaccessible = _check_file_accessibility(files, sample_size=5)

        assert len(inaccessible) == 0

    def test_empty_file_list(self):
        """Test with empty file list."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        inaccessible = _check_file_accessibility([], sample_size=10)

        assert inaccessible == []

    def test_permission_error_detected(self, tmp_path):
        """Test that PermissionError files are detected."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        test_file = tmp_path / "locked.py"
        test_file.write_text("pass")

        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            inaccessible = _check_file_accessibility([test_file], sample_size=1)

        assert len(inaccessible) == 1
        assert test_file in inaccessible

    def test_io_error_detected(self, tmp_path):
        """Test that IOError files are detected."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        test_file = tmp_path / "broken.py"
        test_file.write_text("pass")

        with patch("builtins.open", side_effect=OSError("Read error")):
            inaccessible = _check_file_accessibility([test_file], sample_size=1)

        assert len(inaccessible) == 1

    def test_sample_size_limits_checks(self, tmp_path):
        """Test that only sample_size files are checked."""
        from mcp_server.tools.index_handlers import _check_file_accessibility

        # Create 100 test files
        files = [tmp_path / f"file{i}.py" for i in range(100)]
        for f in files:
            f.write_text("pass")

        # Track how many files are opened
        original_open = open
        open_count = [0]

        def counting_open(*args, **kwargs):
            open_count[0] += 1
            return original_open(*args, **kwargs)

        with patch("builtins.open", side_effect=counting_open):
            _check_file_accessibility(files, sample_size=10)


# ---------------------------------------------------------------------------
# _clear_index_files_before_create — path-safety assertion
# ---------------------------------------------------------------------------


class TestClearIndexFilesBeforeCreate:
    """Verify the storage-root assertion in _clear_index_files_before_create."""

    def test_path_inside_storage_accepted(self, tmp_path: Path) -> None:
        from mcp_server.tools.index_handlers import _clear_index_files_before_create

        index_dir = tmp_path / "storage" / "projects" / "proj_abc_bge_512d" / "index"
        index_dir.mkdir(parents=True)

        # Patch the module-level function so the in-function import picks it up
        with patch(
            "mcp_server.storage_manager.get_storage_dir",
            return_value=tmp_path / "storage",
        ):
            _clear_index_files_before_create(index_dir)

    def test_path_outside_storage_raises(self, tmp_path: Path) -> None:
        from mcp_server.tools.index_handlers import _clear_index_files_before_create

        storage = tmp_path / "storage"
        storage.mkdir()
        bogus = tmp_path / "some_other_directory" / "index"
        bogus.mkdir(parents=True)

        with (
            patch(
                "mcp_server.storage_manager.get_storage_dir",
                return_value=storage,
            ),
            pytest.raises(ValueError, match="_clear_index_files_before_create refused"),
        ):
            _clear_index_files_before_create(bogus)


class TestReleaseGpuMemory:
    """Direct tests for _release_gpu_memory module-level helper."""

    def test_calls_gc_collect(self):
        """gc.collect() is always called regardless of CUDA availability."""
        from mcp_server.tools.index_handlers import _release_gpu_memory

        with patch("search.gpu_monitor.gc") as mock_gc:
            with patch("search.gpu_monitor.torch") as mock_torch:
                mock_torch.cuda.is_available.return_value = False
                _release_gpu_memory()
            mock_gc.collect.assert_called_once()

    def test_no_error_when_torch_unavailable(self):
        """Survives gracefully when torch is not installed (ImportError)."""
        from mcp_server.tools.index_handlers import _release_gpu_memory

        with patch("search.gpu_monitor.torch", None):
            _release_gpu_memory()  # Must not raise


class TestSwitchActiveModel:
    """Direct tests for _switch_active_model module-level helper."""

    def _make_config(self):
        cfg = __import__("unittest.mock", fromlist=["MagicMock"]).MagicMock()
        cfg.embedding.model_name = "old-model"
        cfg.embedding.dimension = 768
        return cfg

    def test_saves_config_when_model_changes(self):
        """Config is saved to disk when the model name differs from current."""
        from unittest.mock import MagicMock, patch

        from mcp_server.tools.index_handlers import _switch_active_model

        mock_cfg = self._make_config()
        mock_mgr = MagicMock()
        mock_mgr.load_config.return_value = mock_cfg

        with (
            patch(
                "mcp_server.tools.index_handlers.SearchConfigManager",
                return_value=mock_mgr,
            ),
            patch(
                "mcp_server.tools.index_handlers.MODEL_REGISTRY",
                {"new-model": {"dimension": 512}},
            ),
            patch("mcp_server.tools.index_handlers.get_state"),
            patch("mcp_server.tools.index_handlers._invalidate_config_caches"),
        ):
            _switch_active_model("new-model")

        mock_mgr.save_config.assert_called_once()

    def test_invalidates_caches(self):
        """Cache invalidation helper is called after config update."""
        from unittest.mock import MagicMock, patch

        from mcp_server.tools.index_handlers import _switch_active_model

        mock_cfg = self._make_config()
        mock_mgr = MagicMock()
        mock_mgr.load_config.return_value = mock_cfg

        with (
            patch(
                "mcp_server.tools.index_handlers.SearchConfigManager",
                return_value=mock_mgr,
            ),
            patch("mcp_server.tools.index_handlers.MODEL_REGISTRY", {}),
            patch("mcp_server.tools.index_handlers.get_state"),
            patch(
                "mcp_server.tools.index_handlers._invalidate_config_caches"
            ) as mock_inv,
        ):
            _switch_active_model("old-model")

        mock_inv.assert_called_once()


class TestHandlerChunkerOwnership:
    """Both handler sites must build their chunker via MultiLanguageChunker.for_project.

    These tests lock in the import-classification fix so it cannot silently regress
    (someone replacing .for_project(...) with the bare constructor would drop
    relation_filter and re-introduce the "unknown" import-category bug).
    """

    def test_handle_index_directory_uses_for_project(self, tmp_path: Path) -> None:
        """handle_index_directory builds its chunker via MultiLanguageChunker.for_project."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock, patch

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()

        with (
            patch(
                "mcp_server.tools.index_handlers.MultiLanguageChunker"
            ) as mock_chunker_cls,
            # _cleanup_previous_resources is a lazy in-function import; patch at source
            patch("mcp_server.resource_manager._cleanup_previous_resources"),
            patch("mcp_server.tools.index_handlers.get_state") as mock_state,
            patch("mcp_server.tools.index_handlers.get_config") as mock_cfg,
            patch(
                "mcp_server.tools.index_handlers.get_canonical_project_info",
                return_value=None,
            ),
            patch(
                "mcp_server.tools.index_handlers.get_project_storage_dir"
            ) as mock_psd,
            patch("mcp_server.tools.index_handlers.set_current_project"),
            patch("mcp_server.tools.index_handlers.temporary_ram_fallback_off"),
            patch(
                "mcp_server.tools.index_handlers._build_index_response", return_value={}
            ),
            # TreeSitterChunker is used in the accessibility pre-check (lazy import)
            patch(
                "chunking.tree_sitter.TreeSitterChunker.get_supported_extensions",
                return_value=[],
            ),
        ):
            # Wire enough state for the handler to reach the chunker line
            mock_cfg.return_value.performance.enable_entity_tracking = False
            mock_cfg.return_value.search_mode.enable_hybrid = False
            lock_mock = AsyncMock()
            lock_mock.__aenter__ = AsyncMock(return_value=None)
            lock_mock.__aexit__ = AsyncMock(return_value=None)
            mock_state.return_value.get_reindex_lock.return_value = lock_mock
            proj_dir = tmp_path / "storage" / "proj"
            proj_dir.mkdir(parents=True)
            index_dir = proj_dir / "index"
            index_dir.mkdir()
            mock_psd.return_value = proj_dir
            mock_chunker_cls.for_project.return_value = MagicMock()

            from mcp_server.tools.index_handlers import handle_index_directory

            asyncio.run(handle_index_directory({"directory_path": str(project_dir)}))

        mock_chunker_cls.for_project.assert_called_once()
        # The bare constructor must NOT be called (that would be the regression)
        mock_chunker_cls.assert_not_called()

    def test_check_auto_reindex_uses_for_project(self, tmp_path: Path) -> None:
        """_check_auto_reindex builds its chunker via MultiLanguageChunker.for_project."""
        from unittest.mock import MagicMock, patch

        project_path = str(tmp_path / "myproject")
        Path(project_path).mkdir()

        with (
            patch(
                "mcp_server.tools.search_handlers.MultiLanguageChunker"
            ) as mock_chunker_cls,
            patch(
                "mcp_server.tools.search_handlers.get_project_storage_dir"
            ) as mock_psd,
            patch("mcp_server.tools.search_handlers.get_config") as mock_cfg,
            patch("mcp_server.tools.search_handlers.get_embedder") as mock_emb,
            patch("mcp_server.tools.search_handlers.get_index_manager"),
            patch("mcp_server.tools.search_handlers.IncrementalIndexer") as mock_ii,
            patch("mcp_server.tools.search_handlers.temporary_ram_fallback_off"),
            # validate_embedder_index_compatibility is a lazy in-function import
            patch("search.dimension_validator.validate_embedder_index_compatibility"),
            # SnapshotManager and ChangeDetector are lazy in-function imports
            patch("merkle.snapshot_manager.SnapshotManager") as mock_snap_cls,
            patch("merkle.change_detector.ChangeDetector"),
            patch(
                "chunking.tree_sitter.TreeSitterChunker.get_supported_extensions",
                return_value=[],
            ),
        ):
            storage = tmp_path / "storage"
            storage.mkdir()
            mock_psd.return_value = storage
            (storage / "project_info.json").write_text("{}")

            snap_mock = MagicMock()
            snap_mock.has_snapshot.return_value = False
            mock_snap_cls.return_value = snap_mock

            cfg = MagicMock()
            cfg.search_mode.enable_hybrid = False
            cfg.performance.enable_entity_tracking = False
            mock_cfg.return_value = cfg

            mock_emb.return_value = MagicMock()
            mock_chunker_cls.for_project.return_value = MagicMock()
            ii_inst = MagicMock()
            ii_result = MagicMock()
            ii_result.files_modified = 0
            ii_result.files_added = 0
            ii_inst.auto_reindex_if_needed.return_value = ii_result
            mock_ii.return_value = ii_inst

            from mcp_server.tools.search_handlers import _check_auto_reindex

            _check_auto_reindex(project_path, max_age_minutes=60)

        mock_chunker_cls.for_project.assert_called_once()
        mock_chunker_cls.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
