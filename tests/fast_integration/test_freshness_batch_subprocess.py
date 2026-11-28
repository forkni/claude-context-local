"""mcp_server.freshness_batch.run_in_subprocess end to end: a real child process.

Covers what the unit tests patch out: the ``-m`` start, the JSON channel on
stdout (worker prints must stay off it), the process pool inside the child,
and the storage lookup creating no folder.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from chunking.tree_sitter import TreeSitterChunker
from mcp_server import freshness_batch
from merkle.change_detector import ChangeDetector
from merkle.snapshot_manager import SnapshotManager


SLUG, DIM = "bge-m3", 1024


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "storage"
    (root / "projects").mkdir(parents=True)
    monkeypatch.setenv("CODE_SEARCH_STORAGE", str(root))  # inherited by the child
    return root


def _indexed_project(storage: Path, path: Path) -> str:
    path.mkdir()
    (path / "main.py").write_text("x = 1\n", encoding="utf-8")
    manager = SnapshotManager(storage / "merkle")
    detector = ChangeDetector(
        manager,
        supported_extensions=set(TreeSitterChunker.get_supported_extensions()),
        model_slug=SLUG,
        dimension=DIM,
    )
    _changes, dag = detector.detect_changes_from_snapshot(str(path))
    manager.save_snapshot(dag)
    for kind in ("snapshot", "metadata"):  # saved under the configured model's name
        get_path = getattr(manager, f"get_{kind}_path")
        source, target = get_path(str(path)), get_path(str(path), DIM, SLUG)
        if source != target:
            shutil.move(source, target)
    return str(path)


def test_child_process_returns_each_verdict(storage: Path, tmp_path: Path) -> None:
    current = _indexed_project(storage, tmp_path / "current")
    stale = _indexed_project(storage, tmp_path / "stale")
    (Path(stale) / "main.py").write_text("x = 2\n", encoding="utf-8")
    never = tmp_path / "never"
    never.mkdir()

    results = freshness_batch.run_in_subprocess(
        [
            (current, SLUG, DIM),
            (stale, SLUG, DIM),
            (str(never), SLUG, DIM),
            (str(tmp_path / "gone"), SLUG, DIM),
        ]
    )

    assert results == [
        {
            "state": "ok",
            "verdict": {
                "index_is_current": True,
                "pending_changes": {"added": 0, "modified": 0, "removed": 0},
            },
        },
        {
            "state": "ok",
            "verdict": {
                "index_is_current": False,
                "pending_changes": {"added": 0, "modified": 1, "removed": 0},
            },
        },
        {"state": "ok", "verdict": None},
        {"state": "missing"},
    ]
    assert list((storage / "projects").iterdir()) == []
