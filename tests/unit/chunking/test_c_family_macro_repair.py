"""Regression tests for macro-wrapped-return-type declaration repair.

tree-sitter-cpp cannot parse the macro-wrapped-return-type idiom that
pervades C-compatible headers -- `PyAPI_FUNC(PyObject *) PyCell_New(PyObject
*);` and `CVAPI(void) cvSetErrMode(int mode);` both desync into an `ERROR`
node instead of a `declaration`, silently dropping the prototype from
chunking. `_MACRO_WRAPPED_RETURN` + `repair_macro_wrapped_declarations`
(`chunking/languages/_c_family.py`) blank the macro name/parens inside
confirmed `ERROR` spans only, then keep the rewrite only if a reparse
strictly reduces the ERROR line count -- see that function's docstring for
the full contract and the 948-file (cpp) / 69-file (c) measurements.

Regression test for a real boundary bug: matching within each ERROR node's
own byte span missed the first of two adjacent macro-wrapped declarations,
whose span ended exactly at the macro call's closing paren -- one token
before the trailing lookahead needs to see. Fixed by matching the whole
buffer and filtering to matches whose macro-name group starts inside an
ERROR span.
"""

from chunking.languages._c_family import repair_macro_wrapped_declarations
from chunking.languages.cpp import CppChunker, CudaChunker
from tests.unit.chunking.conftest import assert_length_and_newline_invariants


_EXTERN_C_MACRO_WRAPPED_SOURCE = """
extern "C" {

PyAPI_FUNC(PyObject *) PyCell_New(PyObject *ob);
CVAPI(void) cvSetErrMode(int mode);

}
"""
_EXTERN_C_MACRO_WRAPPED_SOURCE_BYTES = _EXTERN_C_MACRO_WRAPPED_SOURCE.encode()


def _all_names(chunker, source):
    """Return every (node_type, name) pair, preserving duplicates."""
    return [
        (chunk.node_type, chunk.metadata.get("name"))
        for chunk in chunker.chunk_code(source)
        if chunk.metadata.get("name") is not None
    ]


class TestExternCMacroWrappedPrototypesRecover:
    """Two macro-wrapped prototypes inside an `extern "C"` linkage block --
    the exact shape from the TouchDesigner CPython headers that started
    this workstream."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_both_prototypes_recover_with_correct_names(self):
        names = _all_names(self.chunker, _EXTERN_C_MACRO_WRAPPED_SOURCE)
        assert ("declaration", "PyCell_New") in names
        assert ("declaration", "cvSetErrMode") in names

    def test_raw_parse_without_the_fix_actually_errors(self):
        """Sanity check that this shape is a genuine regression case, not a
        no-op the fix happens to not break -- confirms the fixture is
        meaningful."""
        tree = self.chunker.parser.parse(_EXTERN_C_MACRO_WRAPPED_SOURCE_BYTES)
        assert tree.root_node.has_error is True

    def test_first_of_two_adjacent_declarations_recovers(self):
        """Regression test for the ERROR-span-boundary-truncation bug: the
        first of two adjacent macro-wrapped declarations was silently
        skipped because its ERROR span ended exactly at the macro call's
        own closing paren, leaving no trailing context for
        `_MACRO_WRAPPED_RETURN`'s lookahead within a per-span slice."""
        repaired = repair_macro_wrapped_declarations(
            _EXTERN_C_MACRO_WRAPPED_SOURCE_BYTES, self.chunker.parser.parse
        )
        # The first declaration's macro wrapper must be blanked just like
        # the second's -- both survive as a bare, parseable return type.
        assert b"PyAPI_FUNC" not in repaired
        assert b"PyObject *  PyCell_New(PyObject *ob);" in repaired
        assert b"CVAPI" not in repaired
        assert b"void  cvSetErrMode(int mode);" in repaired


class TestCamelCaseMethodsNeverRepaired:
    """`getParDouble2`/`setParDouble2` match `_MACRO_WRAPPED_RETURN`'s
    two-uppercase-letter test as well as a real macro -- must survive
    untouched via ERROR-scoping, not regex avoidance (the 82-file
    regression that rejected a global, non-ERROR-scoped version)."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_standalone_control_class_is_byte_identical_no_error_case(self):
        """A class with no macro-wrapped declarations anywhere has no ERROR
        node at all, so `repair_macro_wrapped_declarations` must take its
        early-return path and change nothing."""
        source = b"""
class Calculator {
public:
    double getParDouble2(int index) const;
    void setParDouble2(int index, double value);
};
"""
        tree = self.chunker.parser.parse(source)
        assert tree.root_node.has_error is False
        assert (
            repair_macro_wrapped_declarations(source, self.chunker.parser.parse)
            == source
        )

    def test_control_methods_resolve_correctly(self):
        source = """
class Calculator {
public:
    double getParDouble2(int index) const;
    void setParDouble2(int index, double value);
};
"""
        names = _all_names(self.chunker, source)
        assert ("field_declaration", "getParDouble2") in names
        assert ("field_declaration", "setParDouble2") in names

    def test_control_class_untouched_when_a_real_macro_wrap_is_elsewhere_in_the_same_file(
        self,
    ):
        """The critical cross-contamination guard: a genuine ERROR-scoped
        macro wrap earlier in the file must not cause the *unrelated*,
        already-clean camelCase methods later in the same file to be
        touched -- ERROR-scoping is per-span, not file-wide."""
        source = """
extern "C" {

PyAPI_FUNC(PyObject *) PyCell_New(PyObject *ob);

}

class Calculator {
public:
    double getParDouble2(int index) const;
    void setParDouble2(int index, double value);
};
"""
        names = _all_names(self.chunker, source)
        assert ("declaration", "PyCell_New") in names
        assert ("field_declaration", "getParDouble2") in names
        assert ("field_declaration", "setParDouble2") in names


class TestByteLengthAndNewlinePositionInvariants:
    """`repair_macro_wrapped_declarations` must preserve total byte length
    and every newline's byte offset exactly -- downstream chunk start_line/
    end_line are computed against the rewritten buffer."""

    def test_extern_c_block_preserves_length_and_newlines(self):
        chunker = CppChunker()
        repaired = repair_macro_wrapped_declarations(
            _EXTERN_C_MACRO_WRAPPED_SOURCE_BYTES, chunker.parser.parse
        )
        assert_length_and_newline_invariants(
            _EXTERN_C_MACRO_WRAPPED_SOURCE_BYTES, repaired
        )

    def test_repair_is_idempotent(self):
        """Repairing an already-repaired buffer a second time must be a
        no-op -- the second parse has no ERROR spans left to act on."""
        chunker = CppChunker()
        once = repair_macro_wrapped_declarations(
            _EXTERN_C_MACRO_WRAPPED_SOURCE_BYTES, chunker.parser.parse
        )
        twice = repair_macro_wrapped_declarations(once, chunker.parser.parse)
        assert twice == once


class TestCudaChunkerOverrideWired:
    """`CudaChunker` inherits `CppChunker`'s macro repair unchanged after
    its own CUDA blanking -- proves the seam composes rather than each
    rewrite being exercised in isolation."""

    def test_kernel_and_macro_wrapped_prototype_both_recover(self):
        chunker = CudaChunker()
        source = """
__global__ void kernel(float* out) {
    out[0] = 1.0f;
}

CVAPI(void) cvSetErrMode(int mode);
"""
        names = _all_names(chunker, source)
        assert ("function_definition", "kernel") in names
        assert ("declaration", "cvSetErrMode") in names
