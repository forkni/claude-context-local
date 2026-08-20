"""Layering + wiring ratchets for the resource-refresher seam (ADR-0053).

Converts ADR-0051's prose import count and this refactor's wiring invariant
into checked facts. If either test fails you have either:
- Added a new runtime `mcp_server` import under search/ (inverts ADR-0004's
  layering rule — route through a protocol seam like
  search.resource_refresh.ResourceRefresher instead), OR
- Added an IncrementalIndexer(...) construction under mcp_server/ without an
  explicit resource_refresher= kwarg (silently reverting to
  NullResourceRefresher() in a context that needs the real MCP adapter).
"""

import ast
import glob
from pathlib import Path


def _iter_production_trees(root: str):
    """Yield (path, parsed AST) for every parseable .py file under *root*."""
    for fpath in glob.glob(f"{root}/**/*.py", recursive=True):
        norm = fpath.replace("\\", "/")
        try:
            tree = ast.parse(Path(fpath).read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        yield norm, tree


def _is_type_checking_guard(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


class _UpwardImportVisitor(ast.NodeVisitor):
    """Collects real (non-TYPE_CHECKING) `mcp_server` import line numbers."""

    def __init__(self):
        self.lines: list[int] = []

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            # node.body is type-checking-only (never executes) -- skip it,
            # but still walk orelse in case of runtime imports there.
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "mcp_server" or alias.name.startswith("mcp_server."):
                self.lines.append(node.lineno)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and (
            node.module == "mcp_server" or node.module.startswith("mcp_server.")
        ):
            self.lines.append(node.lineno)
        self.generic_visit(node)


# Files with a documented, deliberate runtime mcp_server import.
# Keep this list short -- each entry is a standing exception to ADR-0004.
_UPWARD_IMPORT_ALLOWLIST = {
    # Cache-dir fallback for a caller-omitted embedder; wrapped in its own
    # try/except so an import failure degrades to Path.home() rather than
    # crashing search. Predates this refactor (see ADR-0051's deferral list).
    "search/search_executor.py",
}


class TestSearchMcpLayering:
    """ADR-0004: search/ must not import mcp_server/ at runtime."""

    def test_no_runtime_mcp_server_imports_outside_allowlist(self):
        stray: list[str] = []
        for norm, tree in _iter_production_trees("search"):
            if norm in _UPWARD_IMPORT_ALLOWLIST:
                continue
            visitor = _UpwardImportVisitor()
            visitor.visit(tree)
            stray.extend(f"{norm}:{lineno}" for lineno in visitor.lines)

        assert not stray, (
            f"Stray runtime mcp_server imports under search/: {stray}. "
            "Route through a protocol seam (see search.resource_refresh."
            "ResourceRefresher) instead of importing mcp_server/ directly."
        )

    def test_allowlist_entries_still_exist_and_still_import_mcp_server(self):
        """The allowlist must not silently rot into dead documentation."""
        for norm in _UPWARD_IMPORT_ALLOWLIST:
            assert Path(norm).exists(), (
                f"Allowlisted file {norm} no longer exists -- remove its "
                "entry from _UPWARD_IMPORT_ALLOWLIST."
            )
            tree = ast.parse(Path(norm).read_text(encoding="utf-8"))
            visitor = _UpwardImportVisitor()
            visitor.visit(tree)
            assert visitor.lines, (
                f"Allowlisted file {norm} no longer has a runtime mcp_server "
                "import -- remove its entry from _UPWARD_IMPORT_ALLOWLIST."
            )


class TestResourceRefresherWiring:
    """Every IncrementalIndexer(...) construction under mcp_server/ must pass
    resource_refresher= explicitly (ADR-0053) -- the default is
    NullResourceRefresher(), which is wrong for a process that owns real
    embedder/searcher/GPU state.
    """

    def test_incremental_indexer_constructions_pass_resource_refresher(self):
        stray: list[str] = []
        for norm, tree in _iter_production_trees("mcp_server"):
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "IncrementalIndexer"
                ):
                    has_kwarg = any(
                        kw.arg == "resource_refresher" for kw in node.keywords
                    )
                    if not has_kwarg:
                        stray.append(f"{norm}:{node.lineno}")

        assert not stray, (
            f"IncrementalIndexer(...) constructed without resource_refresher=: "
            f"{stray}. Pass resource_refresher=McpResourceRefresher() "
            "explicitly -- the class default is NullResourceRefresher()."
        )
