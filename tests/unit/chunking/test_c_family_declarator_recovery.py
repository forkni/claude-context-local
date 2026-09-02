"""Regression tests for Workstream A1 -- C-family declarator-name recovery.

tree-sitter-cpp synthesizes a bogus `qualified_identifier` (with a MISSING
`::` child) as error recovery when an unrecognized macro is absorbed as a
declaration's return type -- e.g. an unknown export/visibility attribute
like `CITO_PLUGIN_EXPORT`. Before this fix, `unwrap_declarator_name` treated
`qualified_identifier` as always-terminal and returned the whole malformed
span (name, return type, and parameter list glued together with an embedded
newline) as the chunk name, e.g.
`'AudioEnginePluginListV1*\\ncito_plugin_list_v1(void)'`. See
`chunking/languages/_c_family.py`'s `_scope_is_missing` docstring for the
exact tree shape this recovers from.

These tests exercise the fix two ways: black-box, through `CppChunker.
chunk_code` on real macro-prefixed source (proving the fix against
tree-sitter's actual grammar output, not a hand-built fake tree), and
white-box, directly against `_scope_is_missing` and `unwrap_declarator_name`
using the same `_FakeNode` style as `test_c_family.py`.
"""

from chunking.languages._c_family import _scope_is_missing, unwrap_declarator_name
from chunking.languages.cpp import CppChunker


def _names(chunker, source):
    """Return {node_type: name} for every chunk with a resolved name."""
    return {
        chunk.node_type: chunk.metadata.get("name")
        for chunk in chunker.chunk_code(source)
        if chunk.metadata.get("name") is not None
    }


class TestMalformedExportMacroRecovery:
    """The three malformed shapes measured against the real voro-td /
    voro-engine projects, reproduced with representative source: an
    unrecognized macro directly ahead of a pointer-returning function
    absorbs as the return type, and the real function name must still
    resolve correctly."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_cito_plugin_list_v1_recovers(self):
        source = """
CITO_PLUGIN_EXPORT
AudioEnginePluginListV1*
cito_plugin_list_v1(void) {
    return nullptr;
}
"""
        assert _names(self.chunker, source) == {
            "function_definition": "cito_plugin_list_v1"
        }

    def test_cito_tap_open_recovers(self):
        source = """
CITO_PLUGIN_EXPORT
CitoTapHandle*
cito_tap_open(const char* path) {
    return nullptr;
}
"""
        assert _names(self.chunker, source) == {"function_definition": "cito_tap_open"}

    def test_create_chop_instance_recovers(self):
        source = """
DLLEXPORT
CHOP_CPlusPlusBase*
CreateCHOPInstance(const OP_NodeInfo* info) {
    return nullptr;
}
"""
        assert _names(self.chunker, source) == {
            "function_definition": "CreateCHOPInstance"
        }


class TestRealShapesUnchanged:
    """Real qualified names, operators, destructors, and function-pointer
    declarators must resolve exactly as before -- the recovery branch only
    fires when `_scope_is_missing` is True, which never holds for a real
    `Foo::bar`."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_out_of_class_qualified_name_unchanged(self):
        source = """
class Foo {
public:
    int* getPtr();
};

int* Foo::getPtr() {
    return nullptr;
}
"""
        assert _names(self.chunker, source)["function_definition"] == "Foo::getPtr"

    def test_in_class_operator_assign_unchanged(self):
        source = """
class Vector {
public:
    Vector& operator=(const Vector& other) {
        return *this;
    }
};
"""
        assert _names(self.chunker, source)["function_definition"] == "operator="

    def test_in_class_destructor_unchanged(self):
        source = """
class S {
public:
    ~S() {}
};
"""
        assert _names(self.chunker, source)["function_definition"] == "~S"

    def test_function_pointer_declarator_unchanged(self):
        source = "void (*cb)(int);\n"
        assert _names(self.chunker, source)["declaration"] == "cb"


class TestNoMalformedNamesEscape:
    """Property guard: whatever CppChunker emits, a chunk name must never
    contain a newline or an opening paren -- the two tells of the pre-fix
    malformed span (name + return type + parameter list glued together)."""

    def test_no_emitted_name_contains_newline_or_paren(self):
        chunker = CppChunker()
        source = """
CITO_PLUGIN_EXPORT
AudioEnginePluginListV1*
cito_plugin_list_v1(void) {
    return nullptr;
}

DLLEXPORT
CHOP_CPlusPlusBase*
CreateCHOPInstance(const OP_NodeInfo* info) {
    return nullptr;
}

class Vector {
public:
    Vector& operator=(const Vector& other) {
        return *this;
    }
    ~Vector() {}
};

int* Foo::getPtr() {
    return nullptr;
}

void (*cb)(int);
"""
        chunks = chunker.chunk_code(source)
        names = [c.metadata.get("name") for c in chunks if c.metadata.get("name")]
        assert names, "expected at least one named chunk"
        for name in names:
            assert "\n" not in name, f"chunk name contains a newline: {name!r}"
            assert "(" not in name, f"chunk name contains an opening paren: {name!r}"


class _Token:
    """Minimal fake for a leaf tree-sitter node -- only `.type`/`.is_missing`/
    `.is_named` are read by `_scope_is_missing`."""

    def __init__(self, node_type, is_missing=False, is_named=True):
        self.type = node_type
        self.is_missing = is_missing
        self.is_named = is_named


class _FakeNode:
    """Same shape as `test_c_family.py`'s `_FakeNode` -- kept local since each
    C-family test module owns its own fixtures."""

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


class TestScopeIsMissing:
    """White-box coverage for `_scope_is_missing`."""

    def test_missing_scope_operator_detected(self):
        node = _FakeNode(
            "qualified_identifier",
            children=[
                _Token("namespace_identifier"),
                _Token("::", is_missing=True, is_named=False),
            ],
        )
        assert _scope_is_missing(node) is True

    def test_present_scope_operator_not_flagged(self):
        node = _FakeNode(
            "qualified_identifier",
            children=[
                _Token("namespace_identifier"),
                _Token("::", is_named=False),
            ],
        )
        assert _scope_is_missing(node) is False


class TestUnwrapDeclaratorNameRecoveryDescent:
    """White-box coverage for `unwrap_declarator_name`'s recovery branch,
    reproducing the exact tree shape from `_c_family.py`'s A1 docstring:

    qualified_identifier (MISSING `::`)
      namespace_identifier   'AudioEnginePluginListV1'
      ::  MISSING
      pointer_type_declarator
        function_declarator
          type_identifier    'cito_plugin_list_v1'   <- the real name
    """

    def test_descends_through_missing_scope_to_the_real_name(self):
        real_name = _FakeNode("type_identifier")
        func_declarator = _FakeNode("function_declarator", children=[real_name])
        pointer_type_declarator = _FakeNode(
            "pointer_type_declarator", declarator=func_declarator
        )
        qualified = _FakeNode(
            "qualified_identifier",
            children=[
                _Token("namespace_identifier"),
                _Token("::", is_missing=True, is_named=False),
                pointer_type_declarator,
            ],
        )
        assert (
            unwrap_declarator_name(qualified, lambda n: "cito_plugin_list_v1")
            == "cito_plugin_list_v1"
        )

    def test_real_qualified_identifier_still_short_circuits_as_terminal(self):
        """A `qualified_identifier` with a present `::` must never enter the
        recovery branch -- it returns via the pre-existing terminal path,
        unchanged from before this fix."""
        qualified = _FakeNode(
            "qualified_identifier",
            children=[
                _Token("namespace_identifier"),
                _Token("::", is_named=False),
                _Token("identifier"),
            ],
        )
        assert (
            unwrap_declarator_name(qualified, lambda n: "Foo::getPtr") == "Foo::getPtr"
        )
