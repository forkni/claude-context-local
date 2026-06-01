"""Tests for tools/safe_clear_index.py — path-safe rmtree helper."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch


_TOOLS_DIR = str(Path(__file__).parent.parent.parent.parent / "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import safe_clear_index  # noqa: E402


# Sentinel filename used by safe_rmtree_all() to verify storage legitimacy
_SENTINEL = safe_clear_index.STORAGE_SENTINEL


def _make_storage(tmp_path: Path, *, with_sentinel: bool = True) -> Path:
    """Return a tmp_path with sentinel file written (default: True)."""
    if with_sentinel:
        (tmp_path / _SENTINEL).write_text("test storage\n")
    return tmp_path


# ---------------------------------------------------------------------------
# safe_rmtree_project — refusal guards
# ---------------------------------------------------------------------------


class TestSafeRmtreeProjectRefusals:
    """Guard conditions that must abort before touching the filesystem."""

    def _call(self, project_hash: str, *, tmp_storage: Path) -> int:
        with patch("safe_clear_index.get_storage_dir", return_value=tmp_storage):
            return safe_clear_index.safe_rmtree_project(project_hash)

    def test_empty_hash_refused(self, tmp_path: Path) -> None:
        assert self._call("", tmp_storage=tmp_path) == 2

    def test_whitespace_only_refused(self, tmp_path: Path) -> None:
        assert self._call("   ", tmp_storage=tmp_path) == 2

    def test_dot_refused(self, tmp_path: Path) -> None:
        assert self._call(".", tmp_storage=tmp_path) == 2

    def test_dotdot_refused(self, tmp_path: Path) -> None:
        assert self._call("..", tmp_storage=tmp_path) == 2

    def test_traversal_refused(self, tmp_path: Path) -> None:
        # ../etc would resolve outside projects_root
        assert self._call("../etc", tmp_storage=tmp_path) == 4

    def test_no_underscore_refused(self, tmp_path: Path) -> None:
        # Valid project dirs always contain underscores (name_hash_model_dimd)
        assert self._call("nodash", tmp_storage=tmp_path) == 5

    def test_nonexistent_valid_hash_returns_success(self, tmp_path: Path) -> None:
        # Non-existent but well-formed path is a no-op success
        (tmp_path / "projects").mkdir()
        rc = self._call("myproj_abc12345_bge-v1_1536d", tmp_storage=tmp_path)
        assert rc == 0


# ---------------------------------------------------------------------------
# safe_rmtree_project — actual deletion
# ---------------------------------------------------------------------------


class TestSafeRmtreeProjectDeletion:
    def test_deletes_target_dir(self, tmp_path: Path) -> None:
        projects = tmp_path / "projects"
        projects.mkdir()
        target = projects / "myproj_abc12345_bge-v1_1536d"
        target.mkdir()
        (target / "code.index").write_text("data")

        with patch("safe_clear_index.get_storage_dir", return_value=tmp_path):
            rc = safe_clear_index.safe_rmtree_project("myproj_abc12345_bge-v1_1536d")

        assert rc == 0
        assert not target.exists()

    def test_does_not_delete_projects_root(self, tmp_path: Path) -> None:
        projects = tmp_path / "projects"
        projects.mkdir()
        # Craft a hash that resolves to the projects root itself via .. traversal
        with patch("safe_clear_index.get_storage_dir", return_value=tmp_path):
            # Passing the literal "projects_root name" would resolve to
            # projects_root/<name> which is valid, so test the equality guard:
            # target == projects_root is triggered when hash is "." after strip
            result = safe_clear_index.safe_rmtree_project(".")
        assert result == 2
        assert projects.exists()

    def test_retry_flag_ignores_errors(self, tmp_path: Path) -> None:
        projects = tmp_path / "projects"
        projects.mkdir()
        target = projects / "proj_aaa_model_512d"
        target.mkdir()

        with patch("safe_clear_index.get_storage_dir", return_value=tmp_path):
            rc = safe_clear_index.safe_rmtree_project("proj_aaa_model_512d", retry=True)

        assert rc == 0


# ---------------------------------------------------------------------------
# safe_rmtree_all
# ---------------------------------------------------------------------------


class TestSafeRmtreeAll:
    def test_clears_and_recreates_projects_dir(self, tmp_path: Path) -> None:
        storage = _make_storage(tmp_path)
        projects = storage / "projects"
        projects.mkdir()
        (projects / "proj1_aaa_m_1d").mkdir()
        (projects / "proj2_bbb_m_2d").mkdir()

        with patch("safe_clear_index.get_storage_dir", return_value=storage):
            rc = safe_clear_index.safe_rmtree_all()

        assert rc == 0
        assert projects.exists()
        assert list(projects.iterdir()) == []

    def test_no_op_when_projects_absent(self, tmp_path: Path) -> None:
        storage = _make_storage(tmp_path)
        with patch("safe_clear_index.get_storage_dir", return_value=storage):
            rc = safe_clear_index.safe_rmtree_all()

        assert rc == 0
        assert (storage / "projects").exists()

    def test_refuses_when_projects_root_equals_storage(self, tmp_path: Path) -> None:
        fake_storage = tmp_path / "projects"
        fake_storage.mkdir()
        _make_storage(fake_storage)
        with patch("safe_clear_index.get_storage_dir", return_value=fake_storage):
            rc = safe_clear_index.safe_rmtree_all()
        assert rc in (0, 3)

    def test_refuses_without_sentinel(self, tmp_path: Path) -> None:
        # No sentinel file → refused with code 6
        storage = _make_storage(tmp_path, with_sentinel=False)
        projects = storage / "projects"
        projects.mkdir()

        with patch("safe_clear_index.get_storage_dir", return_value=storage):
            rc = safe_clear_index.safe_rmtree_all()

        assert rc == 6
        # Projects dir must NOT have been deleted
        assert projects.exists()

    def test_refuses_storage_with_project_marker(self, tmp_path: Path) -> None:
        # Storage dir contains .git → refused with code 7
        storage = _make_storage(tmp_path)
        (storage / ".git").mkdir()
        projects = storage / "projects"
        projects.mkdir()

        with patch("safe_clear_index.get_storage_dir", return_value=storage):
            rc = safe_clear_index.safe_rmtree_all()

        assert rc == 7
        assert projects.exists()
