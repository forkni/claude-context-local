"""index_freshness against the REAL storage lookup (no patch of the folder lookup).

``test_index_freshness.py`` patches the storage lookup out, so it could not
see two defects (2026-11-27): a freshness check created the configured
model's storage folder, and it read that model's include/exclude filters when
checking a different model, so a project indexed by two models with
different filters read as stale with nothing changed.

Storage is a temp dir; the configured model is pinned to bge-m3, so the
"other" model here is F2LLM.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_server import storage_manager
from mcp_server.index_freshness import compute_index_freshness
from search.config import get_model_slug
from search.filters import compute_drive_agnostic_hash, compute_legacy_hash
from search.storage_layout import build_model_dir_name


CONFIGURED = ("BAAI/bge-m3", 1024)
OTHER = ("codefuse-ai/F2LLM-v2-0.6B", 1024)


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "storage"
    (root / "projects").mkdir(parents=True)
    monkeypatch.setenv("CODE_SEARCH_STORAGE", str(root))
    monkeypatch.setattr(storage_manager, "get_storage_dir", lambda: root)
    monkeypatch.setattr(
        storage_manager,
        "get_search_config",
        lambda: SimpleNamespace(embedding=SimpleNamespace(model_name=CONFIGURED[0])),
    )
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    path = tmp_path / "proj"
    (path / "extra").mkdir(parents=True)
    (path / "docs").mkdir()
    (path / "main.py").write_text("x = 1\n", encoding="utf-8")
    (path / "extra" / "lib.py").write_text("y = 2\n", encoding="utf-8")
    return path


def _model_dir(
    storage: Path, project: Path, model: tuple[str, int], *, legacy: bool = False
) -> Path:
    resolved = str(project.resolve())
    project_hash = (
        compute_legacy_hash(resolved)
        if legacy
        else compute_drive_agnostic_hash(resolved)
    )
    return (
        storage
        / "projects"
        / build_model_dir_name(
            project.name, project_hash, get_model_slug(model[0]), model[1]
        )
    )


def _register(
    storage: Path, project: Path, model: tuple[str, int], excluded: list[str] | None
) -> Path:
    folder = _model_dir(storage, project, model)
    folder.mkdir()
    (folder / "project_info.json").write_text(
        json.dumps(
            {
                "project_name": project.name,
                "project_path": str(project.resolve()),
                "embedding_model": model[0],
                "model_dimension": model[1],
                "user_excluded_dirs": excluded,
                "default_excluded_dirs": [],
                "user_included_dirs": None,
                "default_included_dirs": None,
            }
        ),
        encoding="utf-8",
    )
    return folder


def _index(project: Path, model: tuple[str, int], excluded: list[str]) -> None:
    """Save a Merkle snapshot for ``model`` built with ``excluded`` dirs."""
    from chunking.tree_sitter import TreeSitterChunker
    from merkle.change_detector import ChangeDetector
    from merkle.snapshot_manager import SnapshotManager

    slug = get_model_slug(model[0])
    manager = SnapshotManager()
    detector = ChangeDetector(
        manager,
        None,
        excluded,
        supported_extensions=set(TreeSitterChunker.get_supported_extensions()),
        model_slug=slug,
        dimension=model[1],
    )
    _changes, dag = detector.detect_changes_from_snapshot(str(project))
    manager.save_snapshot(dag)
    # save_snapshot names the files for the configured model: rename them.
    for kind in ("snapshot", "metadata"):
        get_path = getattr(manager, f"get_{kind}_path")
        source = get_path(str(project))
        target = get_path(str(project), dimension=model[1], model_slug=slug)
        if source != target:
            shutil.move(source, target)


def _folders(storage: Path) -> set[str]:
    return {p.name for p in (storage / "projects").iterdir()}


class TestFreshnessCheckStorage:
    def test_checking_another_model_creates_no_folder(
        self, storage: Path, project: Path
    ) -> None:
        _register(storage, project, OTHER, ["extra"])
        _index(project, OTHER, ["extra"])
        before = _folders(storage)

        result = compute_index_freshness(
            str(project), model_slug=get_model_slug(OTHER[0]), dimension=OTHER[1]
        )

        assert result is not None and result["index_is_current"]
        assert _folders(storage) == before

    def test_each_model_uses_its_own_filters(
        self, storage: Path, project: Path
    ) -> None:
        """Configured model excludes docs/, the other excludes extra/; tree unchanged."""
        _register(storage, project, CONFIGURED, ["docs"])
        _register(storage, project, OTHER, ["extra"])
        _index(project, OTHER, ["extra"])

        result = compute_index_freshness(
            str(project), model_slug=get_model_slug(OTHER[0]), dimension=OTHER[1]
        )

        assert result == {
            "index_is_current": True,
            "pending_changes": {"added": 0, "modified": 0, "removed": 0},
        }

    def test_configured_model_reads_its_own_filters(
        self, storage: Path, project: Path
    ) -> None:
        _register(storage, project, CONFIGURED, ["extra"])
        _index(project, CONFIGURED, ["extra"])
        (project / "extra" / "new.py").write_text("z = 3\n", encoding="utf-8")

        result = compute_index_freshness(
            str(project),
            model_slug=get_model_slug(CONFIGURED[0]),
            dimension=CONFIGURED[1],
        )

        assert result is not None and result["index_is_current"]


class TestFindProjectStorageDir:
    def test_configured_model_by_default(self, storage: Path, project: Path) -> None:
        folder = _register(storage, project, CONFIGURED, None)
        assert storage_manager.find_project_storage_dir(str(project)) == folder

    def test_explicit_model(self, storage: Path, project: Path) -> None:
        _register(storage, project, CONFIGURED, None)
        other = _register(storage, project, OTHER, None)
        found = storage_manager.find_project_storage_dir(
            str(project), model_slug=get_model_slug(OTHER[0]), dimension=OTHER[1]
        )
        assert found == other

    def test_legacy_hash_folder(self, storage: Path, project: Path) -> None:
        folder = _model_dir(storage, project, CONFIGURED, legacy=True)
        folder.mkdir()
        assert storage_manager.find_project_storage_dir(str(project)) == folder

    def test_missing_folder_is_none_and_nothing_is_created(
        self, storage: Path, project: Path
    ) -> None:
        assert storage_manager.find_project_storage_dir(str(project)) is None
        assert _folders(storage) == set()
