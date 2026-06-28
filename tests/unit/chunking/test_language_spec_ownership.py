"""Completeness gate for P4 Phase A.

Asserts that:
1. LANGUAGE_SPECS covers all 9 expected languages.
2. No leaf LanguageChunker subclass overrides _load_language() or
   _get_splittable_node_types() — those methods are now owned solely by the
   base class (which reads from LANGUAGE_SPECS).
3. LanguageSpec.load_grammar() successfully produces a tree_sitter.Language
   object for each installed grammar.

These are *structural* checks that catch copy-paste regressions if a future
leaf is added without updating LANGUAGE_SPECS.
"""

import ast
import inspect
from pathlib import Path

import pytest

from chunking.language_registry import LANGUAGE_SPECS, LanguageSpec
from chunking.languages import (
    CChunker,
    CppChunker,
    CSharpChunker,
    GLSLChunker,
    GoChunker,
    JavaScriptChunker,
    LanguageChunker,
    PythonChunker,
    RustChunker,
    TypeScriptChunker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LEAF_CLASSES = [
    PythonChunker,
    JavaScriptChunker,
    TypeScriptChunker,
    GoChunker,
    RustChunker,
    CChunker,
    CppChunker,
    CSharpChunker,
    GLSLChunker,
]

EXPECTED_LANGUAGES = {
    "python",
    "javascript",
    "typescript",
    "tsx",
    "go",
    "rust",
    "c",
    "cpp",
    "csharp",
    "glsl",
}

LANGUAGES_DIR = Path(__file__).parent.parent.parent.parent / "chunking" / "languages"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLanguageSpecTable:
    """LANGUAGE_SPECS is complete and well-formed."""

    def test_all_expected_languages_present(self):
        """Every EXT_TO_LANGUAGE value should have a spec entry."""
        missing = EXPECTED_LANGUAGES - set(LANGUAGE_SPECS)
        assert not missing, f"Missing LANGUAGE_SPECS entries: {missing}"

    def test_all_specs_are_language_spec_instances(self):
        for lang, spec in LANGUAGE_SPECS.items():
            assert isinstance(spec, LanguageSpec), (
                f"LANGUAGE_SPECS[{lang!r}] is {type(spec).__name__}, expected LanguageSpec"
            )

    def test_all_specs_have_nonempty_splittable_types(self):
        for lang, spec in LANGUAGE_SPECS.items():
            assert spec.splittable_node_types, (
                f"LANGUAGE_SPECS[{lang!r}].splittable_node_types is empty"
            )

    def test_all_specs_have_grammar_module(self):
        for lang, spec in LANGUAGE_SPECS.items():
            assert spec.grammar_module, (
                f"LANGUAGE_SPECS[{lang!r}].grammar_module is not set"
            )

    def test_load_grammar_returns_language_for_installed_grammars(self):
        """load_grammar() must return a tree_sitter.Language for any installed grammar."""
        from tree_sitter import Language

        for lang, spec in LANGUAGE_SPECS.items():
            try:
                result = spec.load_grammar()
            except (ImportError, ValueError):
                pytest.skip(
                    f"{lang} grammar package not installed — skipping load test"
                )
                continue
            assert isinstance(result, Language), (
                f"LANGUAGE_SPECS[{lang!r}].load_grammar() returned {type(result).__name__}"
            )


class TestLeafChunkerOwnership:
    """No leaf chunker defines _load_language or _get_splittable_node_types."""

    BANNED_METHODS = {"_load_language", "_get_splittable_node_types"}

    def _get_own_methods(self, cls) -> set[str]:
        """Return method names defined directly in cls (not inherited)."""
        return {
            name
            for name, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
            if name in cls.__dict__
        }

    @pytest.mark.parametrize("leaf_cls", LEAF_CLASSES, ids=lambda c: c.__name__)
    def test_leaf_does_not_own_banned_methods(self, leaf_cls):
        """Leaf chunkers must NOT define _load_language or _get_splittable_node_types."""
        own_methods = self._get_own_methods(leaf_cls)
        violations = own_methods & self.BANNED_METHODS
        assert not violations, (
            f"{leaf_cls.__name__} defines {violations!r} — "
            f"these are owned by the base class via LANGUAGE_SPECS; "
            f"remove the override from {leaf_cls.__module__}"
        )

    def test_base_owns_load_language(self):
        """_load_language must be defined in LanguageChunker (the base)."""
        assert "_load_language" in LanguageChunker.__dict__, (
            "LanguageChunker must define _load_language"
        )

    def test_base_owns_get_splittable_node_types(self):
        """_get_splittable_node_types must be defined in LanguageChunker (the base)."""
        assert "_get_splittable_node_types" in LanguageChunker.__dict__, (
            "LanguageChunker must define _get_splittable_node_types"
        )


class TestLeafChunkerASTWalk:
    """AST-level scan: no leaf source file contains the banned method definitions.

    This is a belt-and-suspenders check that catches cases where the inspect
    approach might miss something (e.g. dynamically assigned methods).
    """

    BANNED_METHODS = {"_load_language", "_get_splittable_node_types"}

    LEAF_FILES = [
        LANGUAGES_DIR / "python.py",
        LANGUAGES_DIR / "javascript.py",
        LANGUAGES_DIR / "typescript.py",
        LANGUAGES_DIR / "go.py",
        LANGUAGES_DIR / "rust.py",
        LANGUAGES_DIR / "c.py",
        LANGUAGES_DIR / "cpp.py",
        LANGUAGES_DIR / "csharp.py",
        LANGUAGES_DIR / "glsl.py",
    ]

    @pytest.mark.parametrize("leaf_file", LEAF_FILES, ids=lambda p: p.name)
    def test_leaf_source_has_no_banned_method_defs(self, leaf_file):
        source = leaf_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(leaf_file))
        violations = []
        for node in ast.walk(tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name in self.BANNED_METHODS
            ):
                violations.append(f"line {node.lineno}: def {node.name}()")
        assert not violations, (
            f"{leaf_file.name} still defines banned methods (should be in LANGUAGE_SPECS):\n"
            + "\n".join(violations)
        )
