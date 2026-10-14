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

from types import SimpleNamespace

import pytest

from chunking.languages._c_family import (
    repair_export_macro_class_heads,
    repair_macro_wrapped_declarations,
)
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


class TestErrorStartingAfterTheMacroRecovers:
    """The parser can accept `MACRO(T)` as a call statement with a MISSING
    `;` and open the ERROR only at the declarator after it -- the macro name
    itself lies outside every ERROR span. The gate must still admit the
    match when an ERROR span intersects the rest of the macro's line."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_primitive_wrapped_type_inside_extern_c(self):
        source = """extern "C" {
PyAPI_FUNC(long) PyLong_AsLong(PyObject *);
PyAPI_FUNC(double) PyLong_AsDouble(PyObject *);
}
"""
        names = _all_names(self.chunker, source)
        assert ("declaration", "PyLong_AsLong") in names
        assert ("declaration", "PyLong_AsDouble") in names

    def test_type_identifier_wrapped_type_at_root(self):
        source = """CVAPI(CvRect) cvGetImageROI(const IplImage* image);
CVAPI(CvSize) cvGetSize(const CvArr* arr);
"""
        names = _all_names(self.chunker, source)
        assert ("declaration", "cvGetImageROI") in names
        assert ("declaration", "cvGetSize") in names


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

    def test_method_with_a_trailing_macro_keeps_its_name(self):
        """The ERROR sits on the trailing `CV_OVERRIDE`, on the same line as
        a camelCase method that `_MACRO_WRAPPED_RETURN` matches. A gate
        spanning the whole line blanked `getThreadNum()` and renamed the
        method `CV_OVERRIDE` (the opencv parallel backends)."""
        source = """
class Backend {
public:
    virtual int getThreadNum() const CV_OVERRIDE
    {
        return 0;
    }
    virtual int setNumThreads(int nThreads) CV_OVERRIDE
    {
        return nThreads;
    }
};
"""
        names = _all_names(self.chunker, source)
        assert ("function_definition", "getThreadNum") in names
        assert ("function_definition", "setNumThreads") in names
        assert ("function_definition", "CV_OVERRIDE") not in names


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
    its own launch-config blanking -- proves the seam composes rather than
    each rewrite being exercised in isolation."""

    def test_kernel_launch_and_macro_wrapped_prototype_all_recover(self):
        chunker = CudaChunker()
        source = """
__global__ void kernel(float* out) {
    out[0] = 1.0f;
}

void launch(float* out) {
    kernel<<<1, 1>>>(out);
}

CVAPI(void) cvSetErrMode(int mode);
"""
        names = _all_names(chunker, source)
        assert ("function_definition", "kernel") in names
        assert ("function_definition", "launch") in names
        assert ("declaration", "cvSetErrMode") in names


class TestExportMacroClassHeads:
    """`class CV_EXPORTS Foo : public Bar {` (ADR-0087, cause H).

    tree-sitter-cpp reads the macro as the class name, then the real name
    as a declarator, and the body becomes a bogus `function_definition:Foo`
    -- most of these heads parse with no ERROR at all.
    """

    def setup_method(self):
        self.chunker = CppChunker()

    @pytest.mark.parametrize(
        "head",
        [
            "class CV_EXPORTS Foo : public Bar {",
            "class CV_EXPORTS Foo {",
            "struct CV_EXPORTS_W Foo {",
            "class CV_EXPORTS_W_SIMPLE Foo final : public Bar {",
            "class CV_EXPORTS_AS(Baz) Foo {",
            "class CV_EXPORTS Foo\n{",
            "class CV_EXPORTS Foo\n    : public Bar\n{",
            "class CV_EXPORTS_W CV_WRAP_AS(Baz) Foo\n{",
        ],
        ids=[
            "base",
            "plain",
            "struct",
            "final",
            "macro_args",
            "brace_next",
            "base_next",
            "two_macros",
        ],
    )
    def test_head_parses_as_a_class(self, head):
        source = f"{head}\npublic:\n    int f() const {{ return 1; }}\n}};\n"
        names = _all_names(self.chunker, source)
        kind = "struct_specifier" if head.startswith("struct") else "class_specifier"
        assert (kind, "Foo") in names
        assert ("function_definition", "f") in names
        assert ("function_definition", "Foo") not in names

    def test_nested_class_defined_outside_keeps_its_qualified_name(self):
        # opencv gapi/media.hpp: `class GAPI_EXPORTS MediaFrame::View final {`.
        source = (
            "class GAPI_EXPORTS MediaFrame::View final {\n"
            "public:\n    int f() const { return 1; }\n};\n"
        )
        chunks = self.chunker.chunk_code(source)
        names = {(c.node_type, c.metadata.get("name")): c for c in chunks}
        assert ("class_specifier", "MediaFrame::View") in names
        assert names[("function_definition", "f")].parent_class == "MediaFrame::View"

    def test_template_head_parses_as_a_class(self):
        source = b"template<typename T> class CV_EXPORTS Foo {\n    T x;\n};\n"
        parse = self.chunker.parser.parse
        repaired = repair_export_macro_class_heads(source, parse)
        assert b"CV_EXPORTS" not in repaired
        (template,) = parse(repaired).root_node.children[:1]
        assert "class_specifier" in [c.type for c in template.children]

    @pytest.mark.parametrize(
        "source",
        [
            "class Foo : public Bar {\n    int a;\n};\n",
            "class FOO {\n    int a;\n};\n",
            "class FOO final {\n    int a;\n};\n",
            "struct S s;\n",
            "struct POINT p;\n",
            "enum class K : int {\n    A,\n};\n",
            "typedef struct FOO Bar;\n",
            "class CV_EXPORTS Foo;\n",
        ],
        ids=[
            "no_macro",
            "caps_name",
            "caps_name_final",
            "variable",
            "caps_variable",
            "enum_class",
            "typedef",
            "forward_decl",
        ],
    )
    def test_other_shapes_are_untouched(self, source):
        src = source.encode()
        assert repair_export_macro_class_heads(src, self.chunker.parser.parse) == src

    def test_preserves_length_and_newlines(self):
        source = (
            b"namespace cv {\n"
            b"class CV_EXPORTS_W Foo : public Bar {\r\n"
            b"public:\n    int f();\n};\n"
            b"template<typename T> struct CV_EXPORTS_AS(B) Q\n{\n    T x;\n};\n"
            b"}\n"
        )
        repaired = repair_export_macro_class_heads(source, self.chunker.parser.parse)
        assert repaired != source
        assert_length_and_newline_invariants(source, repaired)

    def test_rewrite_that_adds_error_lines_is_dropped(self):
        """The blanked file is kept only if it parses no worse."""
        source = b"class CV_EXPORTS Foo {\n    int a;\n};\n"
        clean = self.chunker.parser.parse(source)
        broken = self.chunker.parser.parse(b"int x = ;\n")

        def parse(src: bytes):
            return clean if src == source else broken

        assert repair_export_macro_class_heads(source, parse) == source

    def test_guard_compares_after_the_later_repairs(self):
        """A rewrite that ties on its own but leaves `then` worse is dropped."""
        source = b"class CV_EXPORTS Foo {\n    int a;\n};\n"
        parse = self.chunker.parser.parse
        broken = b"int x = ;\n" + b" " * (len(source) - 10)

        def then(src: bytes) -> bytes:
            return src if src == source else broken

        assert repair_export_macro_class_heads(source, parse, then=then) == source
        assert repair_export_macro_class_heads(source, parse) != source

    def test_pipeline_parses_each_buffer_once(self):
        """The repairs share one parse per distinct buffer in a call."""
        chunker = CppChunker()
        real_parse = chunker.parser.parse
        parsed: list[bytes] = []

        def counting_parse(src: bytes):
            parsed.append(src)
            return real_parse(src)

        chunker.parser = SimpleNamespace(parse=counting_parse)
        chunker.preprocess_source_for_parse(
            b"class CV_EXPORTS Foo : public Bar {\npublic:\n    int f();\n};\n"
        )
        assert len(parsed) == len(set(parsed))
