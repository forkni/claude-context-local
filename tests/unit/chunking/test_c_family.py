"""Direct branch coverage for the shared C-family declarator unwrap helpers.

These exercise edge cases that either can't occur through a valid tree-sitter
parse (an unknown node type breaking the unwrap chain) or would require
contrived/degenerate source to reach through real parsing (a wrapper node with
no `declarator` field and no named children at all). Fake nodes make both
directly reachable without fighting the grammar.
"""

from chunking.languages._c_family import (
    declarator_is_function_shaped,
    unwrap_declarator_name,
)


class _FakeNode:
    def __init__(self, node_type, children=None, is_missing=False, declarator=None):
        self.type = node_type
        self.children = children or []
        self.is_named = True
        self.is_missing = is_missing
        self._declarator = declarator

    def child_by_field_name(self, name):
        if name == "declarator":
            return self._declarator
        return None


def _text(node):
    return node.type


class TestUnwrapDeclaratorName:
    def test_terminal_returns_name(self):
        node = _FakeNode("identifier")
        assert unwrap_declarator_name(node, _text) == "identifier"

    def test_missing_terminal_returns_none(self):
        node = _FakeNode("identifier", is_missing=True)
        assert unwrap_declarator_name(node, _text) is None

    def test_unknown_declarator_type_returns_none(self):
        """`array_declarator` is neither a terminal name node nor a wrapper
        this unwraps through -- e.g. `int arr[10];`'s declarator chain."""
        node = _FakeNode("array_declarator")
        assert unwrap_declarator_name(node, _text) is None

    def test_wrapper_with_no_named_children_returns_none(self):
        """Degenerate case: a wrapper node with a None `declarator` field and
        no named children at all, so both the field lookup and the fallback
        scan fail and the chain terminates on None."""
        node = _FakeNode("reference_declarator", children=[])
        assert unwrap_declarator_name(node, _text) is None


class TestDeclaratorIsFunctionShaped:
    def test_chain_ending_in_none_returns_false(self):
        """Same degenerate no-field/no-named-children case as above, on the
        other unwrap loop -- the chain terminates on None without ever
        reaching a `function_declarator`."""
        node = _FakeNode("pointer_declarator", children=[])
        assert declarator_is_function_shaped(node) is False
