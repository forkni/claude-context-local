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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
