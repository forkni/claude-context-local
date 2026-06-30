"""P7 completeness gate: searcher-type resolution owned by searcher_view.py.

If this test fails you have either:
- Added a new ``hasattr(searcher, "dense_index")`` or
  ``hasattr(searcher, "index_manager")`` or ``isinstance(..., HybridSearcher)``
  call in an ``mcp_server/tools/`` handler outside ``searcher_view.py``, OR
- The existing call sites haven't been migrated yet.

The canonical owner is ``mcp_server.tools.searcher_view.SearcherView``.  All
handler-layer searcher-type resolution must go through it.
"""

from __future__ import annotations

import ast
import glob
from pathlib import Path


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parents[3]
_TOOLS_DIR = _PROJECT_ROOT / "mcp_server" / "tools"


def _collect_resolution_sites(src_file: str) -> list[str]:
    """Return ``"file:line"`` for hasattr/isinstance searcher-resolution calls.

    Detects:
    - ``hasattr(*, "dense_index")`` — Hybrid-only attribute probe
    - ``hasattr(*, "index_manager")`` — Intelligent-only attribute probe
    - ``isinstance(*, HybridSearcher)`` — direct type-check

    Both are permitted inside ``searcher_view.py`` itself (that is where they
    must live); all other ``mcp_server/tools/*.py`` files are forbidden.
    """
    try:
        source = Path(src_file).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, OSError):
        return []

    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # hasattr(x, "dense_index") or hasattr(x, "index_manager")
        if isinstance(func, ast.Name) and func.id == "hasattr" and len(node.args) == 2:
            second = node.args[1]
            if isinstance(second, ast.Constant) and second.value in (
                "dense_index",
                "index_manager",
            ):
                hits.append(f"{src_file}:{node.lineno}")

        # isinstance(x, HybridSearcher)
        if (
            isinstance(func, ast.Name)
            and func.id == "isinstance"
            and len(node.args) == 2
        ):
            second = node.args[1]
            if isinstance(second, ast.Name) and second.id == "HybridSearcher":
                hits.append(f"{src_file}:{node.lineno}")

    return hits


def _read_line(src_file: str, hit: str) -> str:
    """Return the source line at ``file:lineno`` hit string."""
    try:
        lineno = int(hit.split(":")[-1])
        lines = Path(src_file).read_text(encoding="utf-8").splitlines()
        return lines[lineno - 1] if 0 < lineno <= len(lines) else ""
    except (ValueError, OSError):
        return ""


# ---------------------------------------------------------------------------
# gate
# ---------------------------------------------------------------------------


# Files that are explicitly allowed to contain isinstance(*, HybridSearcher)
# for reasons OTHER than attribute extraction (e.g., feature-gating search
# parameters that only apply to HybridSearcher).  The hasattr "dense_index" /
# "index_manager" probes are still forbidden in these files.
_ISINSTANCE_ALLOWLIST = {
    "search_orchestrator.py",  # feature-gates: ego_graph, parent-retrieval, weight overrides
}


class TestSearcherViewOwnership:
    """P7 completeness gate: no stray searcher-type resolution in handlers.

    Scans every ``mcp_server/tools/*.py`` file except ``searcher_view.py``
    and asserts that:
    - No ``hasattr(*, "dense_index")`` or ``hasattr(*, "index_manager")``
      appears anywhere outside ``searcher_view.py``.
    - No ``isinstance(*, HybridSearcher)`` appears outside ``searcher_view.py``
      unless the file is in ``_ISINSTANCE_ALLOWLIST`` (for feature-gate uses).

    Note: all three patterns *inside* searcher_view.py are exactly where they
    must live; the gate only checks other files.
    """

    def test_no_stray_searcher_resolution_in_tool_handlers(self):
        """All searcher polymorphism resolution must live in searcher_view.py."""
        tool_files = glob.glob(str(_TOOLS_DIR / "*.py"))
        stray: list[str] = []
        for f in tool_files:
            p = Path(f)
            if p.name == "searcher_view.py":
                continue  # canonical owner — allowed
            sites = _collect_resolution_sites(f)
            if p.name in _ISINSTANCE_ALLOWLIST:
                # Only flag the hasattr probes, not the feature-gate isinstance
                sites = [s for s in sites if "isinstance" not in _read_line(f, s)]
            stray.extend(sites)

        assert not stray, (
            "Stray searcher-type resolution found outside searcher_view.py:\n"
            + "\n".join(f"  {s}" for s in sorted(stray))
            + "\n\nRoute through SearcherView(searcher).index_manager / "
            ".graph_storage / .is_hybrid instead."
        )
