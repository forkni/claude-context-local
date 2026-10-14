"""Regression tests for bare-macro-line repair (ADR-0087, cause B).

A macro invoked alone on its line with no trailing `;` -- namespace
brackets (`CV_CPU_OPTIMIZATION_HAL_NAMESPACE_BEGIN`), struct-head macros
(`PyException_HEAD`), statement macros (`Py_BEGIN_ALLOW_THREADS`) and
namespace-level generator invocations (`OPENCV_HAL_IMPL_RVV_INIT(...)`) --
is not C++ syntax, so tree-sitter-cpp either glues it onto the following
declaration (a function whose span starts at the macro) or opens an ERROR
node. `repair_bare_macro_lines` (`chunking/languages/_c_family.py`) blanks
such lines inside ERROR spans only, and keeps a round only if a reparse
strictly reduces the ERROR line count.
"""

from chunking.languages._c_family import (
    _error_nodes,
    bare_macro_line_matches,
    repair_bare_macro_lines,
)
from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker
from tests.unit.chunking.conftest import assert_length_and_newline_invariants


_NAMESPACE_BRACKETED = """CV_CPU_OPTIMIZATION_HAL_NAMESPACE_BEGIN

inline int f(int x) {
    return x;
}

inline int g(int x) {
    return x;
}

CV_CPU_OPTIMIZATION_HAL_NAMESPACE_END
"""

_NESTED_INLINE_NAMESPACE = """namespace cv {
CV__DNN_INLINE_NS_BEGIN

int f(int x) {
    return x;
}

CV__DNN_INLINE_NS_END
}
"""

_STRUCT_HEAD_MACRO = """typedef struct {
    PyException_HEAD
    PyObject *msg;
    PyObject *filename;
} PySyntaxErrorObject;

int after(int x) {
    return x;
}
"""


def _error_line_count(chunker, source_bytes):
    tree = chunker.parser.parse(source_bytes)
    return sum(
        n.end_point[0] - n.start_point[0] + 1 for n in _error_nodes(tree.root_node)
    )


def _spans(chunker, source):
    return {
        chunk.metadata.get("name"): (chunk.start_line, chunk.end_line)
        for chunk in chunker.chunk_code(source)
        if chunk.metadata.get("name") is not None
    }


class TestNamespaceBracketMacros:
    """BEGIN/END bracket macros must not be glued onto the first function."""

    def test_raw_parse_without_the_fix_actually_errors(self):
        chunker = CppChunker()
        assert _error_line_count(chunker, _NAMESPACE_BRACKETED.encode()) > 0

    def test_root_level_brackets_leave_functions_on_their_own_lines(self):
        spans = _spans(CppChunker(), _NAMESPACE_BRACKETED)
        assert spans["f"] == (3, 5)
        assert spans["g"] == (7, 9)

    def test_brackets_inside_a_namespace_leave_the_function_alone(self):
        spans = _spans(CppChunker(), _NESTED_INLINE_NAMESPACE)
        assert spans["f"] == (4, 6)

    def test_preprocessed_buffer_has_no_error_lines(self):
        chunker = CppChunker()
        repaired = chunker.preprocess_source_for_parse(_NAMESPACE_BRACKETED.encode())
        assert _error_line_count(chunker, repaired) == 0


class TestStructHeadMacro:
    """`PyException_HEAD` alone on a struct-body line."""

    def test_struct_with_head_macro_parses_cleanly(self):
        chunker = CChunker()
        repaired = chunker.preprocess_source_for_parse(_STRUCT_HEAD_MACRO.encode())
        assert _error_line_count(chunker, repaired) == 0

    def test_struct_and_following_function_keep_names_and_lines(self):
        spans = _spans(CChunker(), _STRUCT_HEAD_MACRO)
        assert spans["PySyntaxErrorObject"] == (1, 5)
        assert spans["after"] == (7, 9)


class TestCandidateGuards:
    """Lines that look like bare macros but carry real syntax stay put.

    Exercised on `bare_macro_line_matches` directly: every shape here parses
    cleanly, so ERROR-scoping alone would already hide them from the repair
    -- the guards matter when one of them shares an ERROR span with a real
    bare macro.
    """

    @staticmethod
    def _names(source):
        return [m.group(1).decode() for m in bare_macro_line_matches(source.encode())]

    def test_a_real_bare_macro_is_a_candidate(self):
        assert self._names("PyObject_HEAD\nint x;\n") == ["PyObject_HEAD"]

    def test_invocation_with_arguments_is_a_candidate(self):
        source = "OPENCV_HAL_IMPL_RVV_INIT(v_uint8, uchar, u8)\n"
        assert self._names(source) == ["OPENCV_HAL_IMPL_RVV_INIT"]

    def test_gtest_header_followed_by_brace_is_kept(self):
        assert self._names("TEST(Suite, Name)\n{\n}\n") == []

    def test_constructor_before_init_list_is_kept(self):
        source = "struct Foo {\n    Foo()\n        : a_(0)\n    {\n    }\n};\n"
        assert self._names(source) == []

    def test_declarator_before_trailing_return_is_kept(self):
        assert self._names("auto make_value()\n    -> int;\n") == []

    def test_last_enumerator_is_kept(self):
        assert self._names("enum Color {\n    RED,\n    LIGHT_BLUE\n};\n") == []

    def test_define_continuation_line_is_kept(self):
        assert self._names("#define WRAP(x) \\\n    INNER_CALL(x)\n") == []

    def test_operand_continuation_line_is_kept(self):
        assert self._names("int y = 1 +\n    SOME_CONSTANT\n    ;\n") == []

    def test_keyword_is_kept(self):
        assert self._names("__attribute__((unused))\nstatic int x;\n") == []

    def test_line_after_a_block_comment_is_a_candidate(self):
        source = "/* bracket */\nCV_NAMESPACE_BEGIN\nint x;\n"
        assert self._names(source) == ["CV_NAMESPACE_BEGIN"]

    def test_line_after_an_include_is_a_candidate(self):
        source = "#include <vector>\nCV_NAMESPACE_BEGIN\nint x;\n"
        assert self._names(source) == ["CV_NAMESPACE_BEGIN"]


class TestRepairContract:
    """Length/newline invariants, idempotence, and the no-ERROR fast path."""

    def test_preserves_length_and_newlines(self):
        chunker = CppChunker()
        source = _NAMESPACE_BRACKETED.encode()
        repaired = repair_bare_macro_lines(source, chunker.parser.parse)
        assert repaired != source
        assert_length_and_newline_invariants(source, repaired)

    def test_repair_is_idempotent(self):
        chunker = CppChunker()
        once = repair_bare_macro_lines(
            _NAMESPACE_BRACKETED.encode(), chunker.parser.parse
        )
        twice = repair_bare_macro_lines(once, chunker.parser.parse)
        assert twice == once

    def test_clean_source_is_returned_unchanged(self):
        """Namespace-level invocations that already parse cleanly are left
        alone -- there is no ERROR span to scope a rewrite to."""
        chunker = CppChunker()
        source = (
            b"OPENCV_HAL_IMPL_RVV_INIT(v_uint8, uchar, u8)\n"
            b"OPENCV_HAL_IMPL_RVV_INIT(v_int8, schar, i8)\n"
        )
        assert _error_line_count(chunker, source) == 0
        assert repair_bare_macro_lines(source, chunker.parser.parse) == source
