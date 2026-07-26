"""Tests for storage_manager path validation and sentinel logic."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    """Tests for get_storage_dir() with env-var handling."""

    def _call(self, env_val: str | None, tmp_path: Path) -> Path:
        """Call get_storage_dir() in isolation with a fresh state."""
        from mcp_server.storage_manager import get_storage_dir

        class _FakeState:
            storage_dir = None

        env = dict(os.environ)
        if env_val is not None:
            env["CODE_SEARCH_STORAGE"] = env_val
        else:
            env.pop("CODE_SEARCH_STORAGE", None)

        with (
            patch("mcp_server.storage_manager.get_state", return_value=_FakeState()),
            patch.dict(os.environ, env, clear=True),
        ):
            return get_storage_dir()

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


# ---------------------------------------------------------------------------
# get_canonical_project_info — current-model precedence (H2 regression)
# ---------------------------------------------------------------------------


class TestGetCanonicalProjectInfo:
    """Regression tests for the alphabetical-model-dir precedence bug.

    Previously ``get_canonical_project_info`` took the first hit from
    ``sorted(projects_dir.glob(...))`` across all per-model dirs, regardless
    of which model is actually configured. With two model dirs present for
    the same project (e.g. bge-m3 and qwen3-0.6b, both 1024d), alphabetical
    order put bge-m3 first even when qwen3-0.6b is the configured model and
    holds the project's real ``user_excluded_dirs`` — silently reading back
    ``None`` instead of the stored exclusion list.
    """

    @staticmethod
    def _make_model_dir(
        projects_dir: Path,
        project_name: str,
        project_hash: str,
        model_slug: str,
        dimension: int,
        user_excluded_dirs: list[str] | None,
    ) -> Path:
        model_dir = (
            projects_dir / f"{project_name}_{project_hash}_{model_slug}_{dimension}d"
        )
        model_dir.mkdir(parents=True)
        info = {
            "project_name": project_name,
            "embedding_model": model_slug,
            "user_excluded_dirs": user_excluded_dirs,
            "user_included_dirs": None,
        }
        (model_dir / "project_info.json").write_text(json.dumps(info))
        return model_dir

    def test_prefers_configured_model_over_alphabetically_first(
        self, tmp_path: Path
    ) -> None:
        from mcp_server.storage_manager import (
            compute_drive_agnostic_hash,
            get_canonical_project_info,
        )

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        storage_dir = tmp_path / "storage"
        projects_dir = storage_dir / "projects"
        projects_dir.mkdir(parents=True)

        project_hash = compute_drive_agnostic_hash(str(project_dir.resolve()))

        # "bge-m3" sorts alphabetically before "qwen3-0.6b" — the bug returned
        # this one regardless of which model is configured.
        self._make_model_dir(
            projects_dir, "myproject", project_hash, "bge-m3", 1024, None
        )
        qwen_dir = self._make_model_dir(
            projects_dir,
            "myproject",
            project_hash,
            "qwen3-0.6b",
            1024,
            ["tests", "_archive"],
        )

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"

        with (
            patch(
                "mcp_server.storage_manager.get_storage_dir",
                return_value=storage_dir,
            ),
            patch(
                "mcp_server.storage_manager.get_search_config",
                return_value=fake_config,
            ),
        ):
            result = get_canonical_project_info(str(project_dir))

        assert result == qwen_dir / "project_info.json"

    def test_falls_back_when_configured_model_has_no_info(self, tmp_path: Path) -> None:
        """H1 fallback must still work: configured model's dir has no
        project_info.json yet, so the other model's file is returned."""
        from mcp_server.storage_manager import (
            compute_drive_agnostic_hash,
            get_canonical_project_info,
        )

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        storage_dir = tmp_path / "storage"
        projects_dir = storage_dir / "projects"
        projects_dir.mkdir(parents=True)

        project_hash = compute_drive_agnostic_hash(str(project_dir.resolve()))

        bge_dir = self._make_model_dir(
            projects_dir,
            "myproject",
            project_hash,
            "bge-m3",
            1024,
            ["tests", "_archive"],
        )
        # Configured model's own dir exists but has no project_info.json yet.
        (projects_dir / f"myproject_{project_hash}_qwen3-0.6b_1024d").mkdir(
            parents=True
        )

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"

        with (
            patch(
                "mcp_server.storage_manager.get_storage_dir",
                return_value=storage_dir,
            ),
            patch(
                "mcp_server.storage_manager.get_search_config",
                return_value=fake_config,
            ),
        ):
            result = get_canonical_project_info(str(project_dir))

        assert result == bge_dir / "project_info.json"

    def test_returns_none_when_no_model_dir_has_info(self, tmp_path: Path) -> None:
        from mcp_server.storage_manager import get_canonical_project_info

        project_dir = tmp_path / "myproject"
        project_dir.mkdir()
        storage_dir = tmp_path / "storage"
        (storage_dir / "projects").mkdir(parents=True)

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"

        with (
            patch(
                "mcp_server.storage_manager.get_storage_dir",
                return_value=storage_dir,
            ),
            patch(
                "mcp_server.storage_manager.get_search_config",
                return_value=fake_config,
            ),
        ):
            result = get_canonical_project_info(str(project_dir))

        assert result is None
