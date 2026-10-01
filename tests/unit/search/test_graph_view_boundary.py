"""Enforce the GraphView boundary: only search/graph_view.py touches ``.graph``.

``search/`` and ``mcp_server/`` must read the code graph through ``GraphView``
(see the module docstring there).  A direct ``<storage>.graph`` attribute
access bypasses the typed records and the attribute-schema owner.
"""

import ast
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCANNED_DIRS = ("search", "mcp_server")
ALLOWED = {Path("search/graph_view.py")}
# Attribute chains that are NOT a CodeGraphStorage graph (different ``.graph``).
NON_STORAGE_BASES = {"report", "self"}


def _storage_graph_accesses(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "graph":
            base = node.value
            if isinstance(base, ast.Name) and base.id in NON_STORAGE_BASES:
                continue
            hits.append(node.lineno)
    return hits


def _files() -> list[Path]:
    out = []
    for d in SCANNED_DIRS:
        for p in (ROOT / d).rglob("*.py"):
            if p.relative_to(ROOT) not in ALLOWED:
                out.append(p)
    return out


@pytest.mark.parametrize("path", _files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_direct_storage_graph_access(path: Path) -> None:
    hits = _storage_graph_accesses(path)
    assert not hits, (
        f"{path.relative_to(ROOT)} touches '.graph' directly at lines {hits}; "
        "route the read through search.graph_view.GraphView"
    )
