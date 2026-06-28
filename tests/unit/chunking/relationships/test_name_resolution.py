"""Unit tests for chunking/relationships/name_resolution.py.

Covers all three public functions across the expected AST node varieties.
Also contains the slot-leak regression for ExceptionExtractor to verify
that reusing an extractor across two chunks does not carry stale
relationship_type from the first chunk into the second.
"""

import ast

from chunking.relationships.name_resolution import (
    base_class_name,
    call_target_name,
    dotted_name,
)
from chunking.relationships.relationship_extractors.exception_extractor import (
    ExceptionExtractor,
)
from chunking.relationships.relationship_types import RelationshipType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_expr(source: str) -> ast.expr:
    """Parse a single Python expression into an ast node."""
    return ast.parse(source, mode="eval").body


# ---------------------------------------------------------------------------
# dotted_name
# ---------------------------------------------------------------------------


class TestDottedName:
    def test_none_returns_none(self):
        assert dotted_name(None) is None

    def test_name_node(self):
        node = _parse_expr("os")
        assert dotted_name(node) == "os"

    def test_attribute_one_level(self):
        node = _parse_expr("a.b")
        assert dotted_name(node) == "a.b"

    def test_attribute_two_levels(self):
        node = _parse_expr("a.b.c")
        assert dotted_name(node) == "a.b.c"

    def test_attribute_three_levels(self):
        node = _parse_expr("a.b.c.d")
        assert dotted_name(node) == "a.b.c.d"

    def test_non_name_root_returns_suffix(self):
        # Call at the root: something().attr — rare in practice, but defined.
        # The iterative implementation returns just the attr chain without the root.
        node = _parse_expr("foo().bar")
        assert isinstance(node, ast.Attribute)
        result = dotted_name(node)
        assert result == "bar"

    def test_constant_returns_none(self):
        node = _parse_expr("42")
        assert dotted_name(node) is None

    def test_call_returns_none(self):
        # call_target_name handles Call; dotted_name treats it as unknown
        node = _parse_expr("foo()")
        assert dotted_name(node) is None


# ---------------------------------------------------------------------------
# call_target_name
# ---------------------------------------------------------------------------


class TestCallTargetName:
    def test_none_returns_none(self):
        assert call_target_name(None) is None

    def test_name(self):
        node = _parse_expr("Foo")
        assert call_target_name(node) == "Foo"

    def test_attribute(self):
        node = _parse_expr("mod.Foo")
        assert call_target_name(node) == "mod.Foo"

    def test_call_of_name(self):
        node = _parse_expr("Foo()")
        assert call_target_name(node) == "Foo"

    def test_call_of_attribute(self):
        node = _parse_expr("mod.Foo()")
        assert call_target_name(node) == "mod.Foo"

    def test_nested_call(self):
        # get_factory()() — double call; should recurse to the innermost name
        node = _parse_expr("get_factory()()")
        assert call_target_name(node) == "get_factory"

    def test_constant_returns_none(self):
        node = _parse_expr("42")
        assert call_target_name(node) is None


# ---------------------------------------------------------------------------
# base_class_name
# ---------------------------------------------------------------------------


class TestBaseClassName:
    def test_none_returns_none(self):
        assert base_class_name(None, full=True) is None
        assert base_class_name(None, full=False) is None

    # --- Name ---

    def test_name_full_true(self):
        node = _parse_expr("Parent")
        assert base_class_name(node, full=True) == "Parent"

    def test_name_full_false(self):
        node = _parse_expr("Parent")
        assert base_class_name(node, full=False) == "Parent"

    # --- Attribute (the load-bearing fork) ---

    def test_attribute_full_true_returns_dotted(self):
        node = _parse_expr("module.Parent")
        assert base_class_name(node, full=True) == "module.Parent"

    def test_attribute_full_false_returns_leaf(self):
        node = _parse_expr("typing.Protocol")
        assert base_class_name(node, full=False) == "Protocol"

    def test_attribute_full_false_abc(self):
        node = _parse_expr("abc.ABC")
        assert base_class_name(node, full=False) == "ABC"

    def test_attribute_full_true_deep(self):
        node = _parse_expr("collections.abc.MutableMapping")
        assert base_class_name(node, full=True) == "collections.abc.MutableMapping"

    def test_attribute_full_false_deep(self):
        # full=False should always return just the leaf
        node = _parse_expr("collections.abc.MutableMapping")
        assert base_class_name(node, full=False) == "MutableMapping"

    # --- Subscript (generics) ---

    def test_subscript_full_true(self):
        # class Child(Generic[T])
        node = _parse_expr("Generic[T]")
        assert base_class_name(node, full=True) == "Generic"

    def test_subscript_full_false(self):
        node = _parse_expr("Protocol[T]")
        assert base_class_name(node, full=False) == "Protocol"

    def test_subscript_qualified_full_true(self):
        node = _parse_expr("typing.Generic[T]")
        assert base_class_name(node, full=True) == "typing.Generic"

    def test_subscript_qualified_full_false(self):
        node = _parse_expr("typing.Protocol[T]")
        assert base_class_name(node, full=False) == "Protocol"

    # --- Call (metaclass) ---

    def test_call_full_true(self):
        # class Foo(metaclass=ABCMeta()) — unusual but should not crash
        node = _parse_expr("Meta()")
        assert base_class_name(node, full=True) == "Meta"

    def test_call_attribute_full_true(self):
        node = _parse_expr("abc.ABCMeta()")
        assert base_class_name(node, full=True) == "abc.ABCMeta"

    def test_call_attribute_full_false(self):
        node = _parse_expr("abc.ABCMeta()")
        assert base_class_name(node, full=False) == "ABCMeta"

    # --- Unknown type ---

    def test_unknown_returns_none(self):
        node = _parse_expr("42")
        assert base_class_name(node, full=True) is None


# ---------------------------------------------------------------------------
# Slot-leak regression
# ---------------------------------------------------------------------------


class TestExceptionExtractorSlotLeak:
    """Verify that ExceptionExtractor does not carry stale relationship_type
    from one chunk into the next when the extractor instance is reused.

    Previously, `self.relationship_type` was mutated in _extract_raise and
    _extract_except_handlers.  When the extractor was reused across chunks
    (as it is in multi_language_chunker.py), the type from chunk A would
    persist into chunk B.  The fix is to pass relationship_type per-edge.
    """

    def test_raises_chunk_followed_by_empty_chunk(self):
        extractor = ExceptionExtractor()
        meta_a = {
            "chunk_id": "test.py:1-5:function:a",
            "file_path": "test.py",
        }
        meta_b = {
            "chunk_id": "test.py:6-10:function:b",
            "file_path": "test.py",
        }

        # Chunk A: raises an exception — sets the edge type to RAISES
        edges_a = extractor.extract("raise ValueError('oops')", meta_a)
        assert len(edges_a) == 1
        assert edges_a[0].relationship_type == RelationshipType.RAISES

        # Chunk B: no raises / no except — should produce zero edges
        # (not accidentally reuse the RAISES type from chunk A)
        edges_b = extractor.extract("x = 1 + 2", meta_b)
        assert len(edges_b) == 0

    def test_catches_chunk_followed_by_empty_chunk(self):
        extractor = ExceptionExtractor()
        meta_a = {
            "chunk_id": "test.py:1-5:function:a",
            "file_path": "test.py",
        }
        meta_b = {
            "chunk_id": "test.py:6-10:function:b",
            "file_path": "test.py",
        }

        # Chunk A: catches — sets type to CATCHES
        catches_code = "try:\n    pass\nexcept ValueError:\n    pass"
        edges_a = extractor.extract(catches_code, meta_a)
        assert len(edges_a) == 1
        assert edges_a[0].relationship_type == RelationshipType.CATCHES

        # Chunk B: empty — must not produce edges
        edges_b = extractor.extract("pass", meta_b)
        assert len(edges_b) == 0

    def test_raises_and_catches_in_same_chunk(self):
        """Verify both RAISES and CATCHES edges are emitted correctly
        within a single chunk (the original multi-type use case)."""
        extractor = ExceptionExtractor()
        code = (
            "def foo():\n"
            "    try:\n"
            "        raise ValueError('v')\n"
            "    except KeyError:\n"
            "        pass\n"
        )
        meta = {"chunk_id": "test.py:1-5:function:foo", "file_path": "test.py"}
        edges = extractor.extract(code, meta)

        types = {e.relationship_type for e in edges}
        assert RelationshipType.RAISES in types
        assert RelationshipType.CATCHES in types
        targets = {e.target_name for e in edges}
        assert "ValueError" in targets
        assert "KeyError" in targets
