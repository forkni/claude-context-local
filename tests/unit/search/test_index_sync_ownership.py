"""P6 completeness gate: BM25SyncManager is gone; resync_if_desynced lives only in IndexSynchronizer.

If this test fails you have either:
- Re-introduced a BM25SyncManager class or sync_if_needed definition outside search/index_sync.py, OR
- Left a stale bm25_sync.py on disk (regression).

Fix: route all desync detection through IndexSynchronizer.resync_if_desynced (and its
HybridSearcher delegate).
"""

import ast
import glob
from pathlib import Path


class TestBM25SyncOwnership:
    """P6 completeness gate for BM25/dense desync detection."""

    def test_bm25_sync_module_deleted(self):
        """search/bm25_sync.py must not exist on disk."""
        assert not Path("search/bm25_sync.py").exists(), (
            "search/bm25_sync.py still exists — delete it; "
            "desync logic now lives in IndexSynchronizer.resync_if_desynced"
        )

    def test_no_bm25_sync_manager_class(self):
        """BM25SyncManager class must not be defined anywhere in the non-test tree."""
        stray: list[str] = []
        for fpath in glob.glob("**/*.py", recursive=True):
            if fpath.startswith(".venv") or fpath.startswith("tests"):
                continue
            try:
                tree = ast.parse(Path(fpath).read_text(encoding="utf-8"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == "BM25SyncManager":
                    stray.append(f"{fpath}:{node.lineno}")

        assert not stray, (
            f"Stray BM25SyncManager class definitions: {stray}. "
            "Desync detection is owned by IndexSynchronizer.resync_if_desynced."
        )

    def test_sync_if_needed_not_defined_outside_owner(self):
        """sync_if_needed must not be defined outside search/index_sync.py (it was deleted)."""
        stray: list[str] = []
        for fpath in glob.glob("**/*.py", recursive=True):
            if fpath.startswith(".venv") or fpath.startswith("tests"):
                continue
            norm = fpath.replace("\\", "/")
            if norm == "search/index_sync.py":
                continue  # owner allowed (though it doesn't define sync_if_needed either)
            try:
                tree = ast.parse(Path(fpath).read_text(encoding="utf-8"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "sync_if_needed"
                ):
                    stray.append(f"{fpath}:{node.lineno}")

        assert not stray, (
            f"Stray sync_if_needed definitions: {stray}. "
            "Use IndexSynchronizer.resync_if_desynced instead."
        )

    def test_desync_threshold_defined_only_in_index_sync(self):
        """DESYNC_THRESHOLD constant must live only in search/index_sync.py."""
        stray: list[str] = []
        for fpath in glob.glob("**/*.py", recursive=True):
            if fpath.startswith(".venv") or fpath.startswith("tests"):
                continue
            norm = fpath.replace("\\", "/")
            if norm == "search/index_sync.py":
                continue
            try:
                tree = ast.parse(Path(fpath).read_text(encoding="utf-8"))
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "DESYNC_THRESHOLD"
                    for t in (node.targets if isinstance(node.targets, list) else [])
                ):
                    stray.append(f"{fpath}:{node.lineno}")

        assert not stray, (
            f"Stray DESYNC_THRESHOLD definitions: {stray}. "
            "Canonical location: search/index_sync.py."
        )
