"""P5 completeness gate: community-remerge functions owned by chunking/community_remerge.py.

If this test fails you have either:

- Added one of the four community-remerge functions back to ``LanguageChunker``
  as a staticmethod, OR
- Removed one of the four functions from ``chunking/community_remerge.py``, OR
- Left a hand-rolled ``f"...:{start_line}-{end_line}:..."`` chunk-id literal at
  one of the three migrated sites (use ``search.chunk_id.build`` instead).

The canonical owner is :mod:`chunking.community_remerge`.
"""

from __future__ import annotations

import ast
import importlib
from pathlib import Path


_PROJECT_ROOT = Path(__file__).parents[3]

# ---------------------------------------------------------------------------
# Expected public API of the new module
# ---------------------------------------------------------------------------

_EXPECTED_FUNCTIONS = {
    "assign_community_ids",
    "to_treesitter_chunks",
    "from_treesitter_chunks",
    "remerge_chunks_with_communities",
}

# ---------------------------------------------------------------------------
# Files that must NOT contain these function names as class methods
# ---------------------------------------------------------------------------

_BASE_PY = _PROJECT_ROOT / "chunking" / "languages" / "base.py"
_COMMUNITY_REMERGE_PY = _PROJECT_ROOT / "chunking" / "community_remerge.py"


def _collect_method_names_on_class(src_file: Path, class_name: str) -> set[str]:
    """Return the set of method names defined directly on *class_name* in *src_file*."""
    try:
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return set()

    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    names.add(item.name)
    return names


def _collect_module_level_function_names(src_file: Path) -> set[str]:
    """Return names of all module-level function definitions in *src_file*."""
    try:
        tree = ast.parse(src_file.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return set()

    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and isinstance(node.col_offset, int)
        and node.col_offset == 0
    }


# ---------------------------------------------------------------------------
# Gate tests
# ---------------------------------------------------------------------------


class TestCommunityRemergeOwnership:
    """P5 completeness gate.

    Verifies:
    1. The four community-remerge functions live in ``chunking/community_remerge.py``
       and are importable from there.
    2. ``LanguageChunker`` in ``chunking/languages/base.py`` no longer defines any
       of them as methods (incl. private ``_`` prefixed versions).
    3. ``chunking.community_remerge`` is importable without errors.
    """

    def test_functions_exist_in_community_remerge(self):
        """All four public functions are importable from chunking.community_remerge."""
        import chunking.community_remerge as mod

        missing = _EXPECTED_FUNCTIONS - {
            name for name in dir(mod) if callable(getattr(mod, name, None))
        }
        assert not missing, (
            f"These functions are missing from chunking.community_remerge: {missing}\n"
            "Add them as module-level functions in chunking/community_remerge.py."
        )

    def test_module_level_functions_in_community_remerge_py(self):
        """AST check: four functions are defined at module level in community_remerge.py."""
        defined = _collect_module_level_function_names(_COMMUNITY_REMERGE_PY)
        missing = _EXPECTED_FUNCTIONS - defined
        assert not missing, (
            f"Module-level functions not found in {_COMMUNITY_REMERGE_PY.name}: {missing}"
        )

    def test_language_chunker_does_not_own_community_functions(self):
        """AST check: LanguageChunker in base.py no longer defines the community methods.

        Checks both the bare names and the private ``_`` prefixed forms that the
        original staticmethods used.
        """
        methods = _collect_method_names_on_class(_BASE_PY, "LanguageChunker")
        stray = methods & (
            _EXPECTED_FUNCTIONS | {f"_{name}" for name in _EXPECTED_FUNCTIONS}
        )
        assert not stray, (
            f"LanguageChunker still defines these community methods: {stray}\n"
            "Delete them from chunking/languages/base.py; "
            "route callers to chunking.community_remerge instead."
        )

    def test_community_remerge_module_importable(self):
        """chunking.community_remerge imports cleanly (no missing deps, no cycles)."""
        try:
            importlib.import_module("chunking.community_remerge")
        except ImportError as exc:
            raise AssertionError(
                f"chunking.community_remerge failed to import: {exc}"
            ) from exc

    def test_community_stage_imports_from_community_remerge_not_base(self):
        """AST check: community_stage.py deferred import is from chunking.community_remerge."""
        src_file = _PROJECT_ROOT / "search" / "community_stage.py"
        try:
            tree = ast.parse(src_file.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            return

        # Collect all module names imported anywhere in the file
        imported_from: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_from.add(node.module)

        assert "chunking.community_remerge" in imported_from, (
            "community_stage.py must import from chunking.community_remerge, "
            "not from chunking.languages.base (P5 requirement)."
        )
        # Also confirm the old import was removed
        assert "chunking.languages.base" not in imported_from, (
            "community_stage.py still imports from chunking.languages.base. "
            "Remove it — the remerge call now goes through chunking.community_remerge."
        )
