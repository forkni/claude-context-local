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


def _iter_production_trees():
    """Yield (path, parsed AST) for every parseable non-test, non-venv .py file."""
    for fpath in glob.glob("**/*.py", recursive=True):
        norm = fpath.replace("\\", "/")
        if norm.startswith((".", "tests/", "_archive/")):
            continue
        try:
            tree = ast.parse(Path(fpath).read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        yield norm, tree


class TestIndexWriteSeamOwnership:
    """Ownership gate for the full/incremental index-write seam (ADR-0052).

    IndexWriteStage is the single owner of adding embeddings to the index
    (``add_to_index``) and of the incremental injection gate
    (``inject_call_edges_if_enabled``). If one of these fails you have
    re-introduced a residue that commit 17c000c's extraction left behind and
    ADR-0052 finished removing.
    """

    def test_add_embeddings_called_only_from_write_stage(self):
        """`.add_embeddings(...)` call sites live only in IndexWriteStage.

        The one sanctioned exception is HybridSearcher's internal delegation
        to its own sub-index (receiver ``self.dense_index`` — the wrapper and
        ``index_documents``); everything else must route through
        IndexWriteStage.add_to_index.
        """

        def is_self_dense_index(receiver: ast.expr) -> bool:
            return (
                isinstance(receiver, ast.Attribute)
                and receiver.attr == "dense_index"
                and isinstance(receiver.value, ast.Name)
                and receiver.value.id == "self"
            )

        stray: list[str] = []
        for norm, tree in _iter_production_trees():
            if norm == "search/index_write_stage.py":
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_embeddings"
                    and not (
                        norm == "search/hybrid_searcher.py"
                        and is_self_dense_index(node.func.value)
                    )
                ):
                    stray.append(f"{norm}:{node.lineno}")

        assert not stray, (
            f"Stray .add_embeddings() call sites: {stray}. "
            "Route index writes through IndexWriteStage.add_to_index "
            "(see ADR-0052)."
        )

    def test_inject_on_incremental_read_only_by_write_stage(self):
        """The ADR-0044 gate is read only inside IndexWriteStage.

        search/config.py declares the field (an AnnAssign, not an attribute
        read, so it never trips this walk); the only attribute *read* allowed
        is IndexWriteStage.inject_call_edges_if_enabled's.
        """
        stray: list[str] = []
        for norm, tree in _iter_production_trees():
            if norm == "search/index_write_stage.py":
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Attribute)
                    and node.attr == "inject_on_incremental"
                ):
                    stray.append(f"{norm}:{node.lineno}")

        assert not stray, (
            f"Stray inject_on_incremental reads: {stray}. "
            "The gate belongs to IndexWriteStage.inject_call_edges_if_enabled "
            "(see ADR-0052 / ADR-0044)."
        )

    def test_private_inject_name_gone_from_production_code(self):
        """The pre-rename `_inject_call_edges` symbol must not reappear."""
        stray: list[str] = []
        for norm, tree in _iter_production_trees():
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "_inject_call_edges"
                ) or (
                    isinstance(node, (ast.Attribute, ast.Name))
                    and getattr(node, "attr", getattr(node, "id", None))
                    == "_inject_call_edges"
                ):
                    stray.append(f"{norm}:{node.lineno}")

        assert not stray, (
            f"Stray _inject_call_edges references: {stray}. "
            "The method is public now — IndexWriteStage.inject_call_edges "
            "(unconditional, full path) or inject_call_edges_if_enabled "
            "(gated, incremental path)."
        )
