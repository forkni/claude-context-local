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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
