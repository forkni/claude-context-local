"""Multi-line C-family macros become their own chunks (ADR-0087, T4).

A `#define` continued over several lines is a definition worth its own
search hit -- the HAL/intrinsics headers carry most of their logic in
`OPENCV_HAL_IMPL_*` macros. One-line `#define`s stay inside preamble chunks:
13k constants as standalone chunks would swamp search results.
"""

from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker, CudaChunker


_MACROS = """#include <stdio.h>

#define ONE_LINE 1
#define SQUARE(x) \\
    ((x) * (x))
#define TABLE \\
    { 1, 2, 3 }
int after_macro = 0;

int use(int v) {
    return SQUARE(v) + ONE_LINE;
}
"""

_EXTERN_C_MACRO = """extern "C" {
#define PyCell_SET(op, v) \\
    (((PyCellObject *)(op))->ob_ref = (v))
int cell_count;
}
"""

_MACRO_TYPES = ("preproc_def", "preproc_function_def")


def _macros(chunks):
    return {c.metadata.get("name"): c for c in chunks if c.node_type in _MACRO_TYPES}


def _preamble_text(chunks):
    return "\n".join(c.content for c in chunks if c.node_type == "module_preamble")


class TestMultiLineMacrosChunk:
    def setup_method(self):
        self.c_chunks = CChunker().chunk_code(_MACROS)
        self.cpp_chunks = CppChunker().chunk_code(_MACROS)
        self.cu_chunks = CudaChunker().chunk_code(_MACROS)

    def test_function_like_macro_is_a_named_chunk(self):
        for chunks in (self.c_chunks, self.cpp_chunks, self.cu_chunks):
            square = _macros(chunks)["SQUARE"]
            assert square.node_type == "preproc_function_def"
            assert (square.start_line, square.end_line) == (4, 5)
            assert square.content.rstrip() == "#define SQUARE(x) \\\n    ((x) * (x))"

    def test_object_macro_is_a_named_chunk(self):
        for chunks in (self.c_chunks, self.cpp_chunks):
            table = _macros(chunks)["TABLE"]
            assert table.node_type == "preproc_def"
            assert (table.start_line, table.end_line) == (6, 7)

    def test_one_line_macro_stays_in_the_preamble(self):
        for chunks in (self.c_chunks, self.cpp_chunks):
            assert "ONE_LINE" not in _macros(chunks)
            assert "#define ONE_LINE 1" in _preamble_text(chunks)

    def test_line_after_a_macro_is_not_dropped(self):
        for chunks in (self.c_chunks, self.cpp_chunks):
            assert "int after_macro = 0;" in _preamble_text(chunks)

    def test_function_using_the_macro_keeps_its_chunk(self):
        names = {c.metadata.get("name") for c in self.c_chunks}
        assert "use" in names


class TestMacroInsideExternC:
    def setup_method(self):
        self.chunks = CppChunker().chunk_code(_EXTERN_C_MACRO)

    def test_nested_macro_is_a_named_chunk(self):
        macro = _macros(self.chunks)["PyCell_SET"]
        assert (macro.start_line, macro.end_line) == (2, 3)

    def test_sibling_declaration_lands_in_a_preamble(self):
        text = _preamble_text(self.chunks)
        assert "int cell_count;" in text
        assert "#define" not in text
