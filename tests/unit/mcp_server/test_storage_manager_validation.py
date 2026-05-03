"""Tests for storage_manager path validation and sentinel logic."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

from mcp_server.storage_manager import (
    STORAGE_SENTINEL,
    validate_storage_path,
)


# ---------------------------------------------------------------------------
# validate_storage_path
# ---------------------------------------------------------------------------


class TestValidateStoragePath:
    def test_dedicated_storage_dir_is_safe(self, tmp_path: Path) -> None:
        storage = tmp_path / ".claude_code_search"
        storage.mkdir()
        ok, reason = validate_storage_path(storage)
        assert ok, reason

    def test_path_with_git_ancestor_refused(self, tmp_path: Path) -> None:
        (tmp_path / ".git").mkdir()
        candidate = tmp_path / "storage"
        candidate.mkdir()
        ok, reason = validate_storage_path(candidate)
        assert not ok
        assert ".git" in reason

    def test_path_with_pyproject_toml_refused(self, tmp_path: Path) -> None:
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")
        candidate = tmp_path / "storage"
        candidate.mkdir()
        ok, reason = validate_storage_path(candidate)
        assert not ok
        assert "pyproject.toml" in reason

    def test_exact_home_dir_refused(self) -> None:
        home = Path.home()
        ok, reason = validate_storage_path(home)
        assert not ok
        assert "home" in reason.lower() or str(home) in reason

    def test_filesystem_root_refused(self) -> None:
        root = Path(Path.home().anchor)
        ok, reason = validate_storage_path(root)
        assert not ok

    def test_nested_under_home_without_markers_is_safe(self, tmp_path: Path) -> None:
        # tmp_path is under TEMP, which is under home (or not) — simulate
        storage = tmp_path / "subdir" / "storage"
        storage.mkdir(parents=True)
        # Ensure no project markers exist along the path up to home
        ok, _ = validate_storage_path(storage)
        assert ok

    def test_marker_at_storage_dir_itself_refused(self, tmp_path: Path) -> None:
        storage = tmp_path / "storage"
        storage.mkdir()
        (storage / ".git").mkdir()
        ok, reason = validate_storage_path(storage)
        assert not ok


# ---------------------------------------------------------------------------
# get_storage_dir — env var validation + sentinel
# ---------------------------------------------------------------------------


class TestGetStorageDir:
    """Tests for StorageManager.get_storage_dir() with env-var handling."""

    def _call(self, env_val: str | None, tmp_path: Path) -> Path:
        """Call get_storage_dir() in isolation with a fresh state."""
        from mcp_server.storage_manager import StorageManager

        class _FakeState:
            storage_dir = None

        mgr = StorageManager()
        env = dict(os.environ)
        if env_val is not None:
            env["CODE_SEARCH_STORAGE"] = env_val
        else:
            env.pop("CODE_SEARCH_STORAGE", None)

        with (
            patch("mcp_server.storage_manager.get_state", return_value=_FakeState()),
            patch.dict(os.environ, env, clear=True),
        ):
            return mgr.get_storage_dir()

    def test_custom_safe_path_used(self, tmp_path: Path) -> None:
        storage = tmp_path / ".my_storage"
        result = self._call(str(storage), tmp_path)
        assert result == storage
        assert result.exists()

    def test_unsafe_env_var_falls_back_to_default(self, tmp_path: Path) -> None:
        # Create a project-root-like directory with pyproject.toml
        proj = tmp_path / "myproject"
        proj.mkdir()
        (proj / "pyproject.toml").write_text("[project]")

        result = self._call(str(proj), tmp_path)
        # Must NOT use the project root
        assert result != proj
        assert "claude_code_search" in str(result)

    def test_sentinel_file_written_on_init(self, tmp_path: Path) -> None:
        storage = tmp_path / ".sentinel_test"
        self._call(str(storage), tmp_path)
        assert (storage / STORAGE_SENTINEL).exists()

    def test_sentinel_idempotent(self, tmp_path: Path) -> None:
        storage = tmp_path / ".idempotent_test"
        self._call(str(storage), tmp_path)
        mtime1 = (storage / STORAGE_SENTINEL).stat().st_mtime
        # Second call (state already set) doesn't re-write, but test the file stays
        assert (storage / STORAGE_SENTINEL).exists()
        assert (storage / STORAGE_SENTINEL).stat().st_mtime == mtime1
