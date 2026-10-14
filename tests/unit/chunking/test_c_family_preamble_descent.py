"""Regression tests for C-family preamble descent (ADR-0087, cause F).

`_collect_module_preamble_chunks` skips every root child that has a chunked
descendant, so non-chunked content nested beside a chunk -- `#define`s and
data declarations inside `extern "C" { ... }`, the leftovers of a root-level
ERROR node -- landed in no chunk at all. `_CFamilyChunker` opts into
descending through such nodes (`_preamble_descend_children`); every other
language keeps the root-only collector.
"""

from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker
from chunking.languages.python import PythonChunker


_EXTERN_C_BLOCK = """#include <stdio.h>

extern "C" {

#define PY_CELL_FLAG 1

struct PyCellObject {
    int value;
};

int cell_count = 0;
const char *cell_name = "cell";

int PyCell_Get(struct PyCellObject *op);

}
"""

_DECLARATION_WITH_CHUNKED_STRUCT = """static struct Config {
    int verbose;
} config = {
    1,
};

int after(int x) {
    return x;
}
"""


def _preambles(chunks):
    return [c for c in chunks if c.node_type == "module_preamble"]


def _others(chunks):
    return [c for c in chunks if c.node_type != "module_preamble"]


class TestExternCBlockDescent:
    def setup_method(self):
        self.chunks = CppChunker().chunk_code(_EXTERN_C_BLOCK)

    def test_define_and_data_declarations_land_in_a_preamble_chunk(self):
        text = "\n".join(c.content for c in _preambles(self.chunks))
        assert "#define PY_CELL_FLAG 1" in text
        assert "int cell_count = 0;" in text
        assert 'const char *cell_name = "cell";' in text

    def test_no_preamble_carries_the_linkage_tokens(self):
        for chunk in _preambles(self.chunks):
            assert 'extern "C"' not in chunk.content

    def test_preambles_do_not_overlap_symbol_chunks(self):
        symbol_lines = {
            line
            for c in _others(self.chunks)
            for line in range(c.start_line, c.end_line + 1)
        }
        for chunk in _preambles(self.chunks):
            span = set(range(chunk.start_line, chunk.end_line + 1))
            assert span.isdisjoint(symbol_lines), chunk.content

    def test_symbols_inside_the_block_still_chunk(self):
        names = {c.metadata.get("name") for c in _others(self.chunks)}
        assert {"PyCellObject", "PyCell_Get"} <= names

    def test_preamble_lines_match_their_content(self):
        lines = _EXTERN_C_BLOCK.split("\n")
        for chunk in _preambles(self.chunks):
            first = lines[chunk.start_line - 1]
            assert first.strip() and chunk.content.startswith(first.strip())


class TestDeclarationWithChunkedStruct:
    """`static struct T {...} x = {...};` -- the struct chunks on its own;
    only the initializer lines it does not cover may surface, never a bare
    `static` fragment from the struct's first line."""

    def setup_method(self):
        self.chunks = CChunker().chunk_code(_DECLARATION_WITH_CHUNKED_STRUCT)

    def test_struct_and_function_keep_their_chunks(self):
        names = {c.metadata.get("name") for c in _others(self.chunks)}
        assert {"Config", "after"} <= names

    def test_no_fully_covered_fragment_is_emitted(self):
        for chunk in _preambles(self.chunks):
            assert chunk.content.strip() != "static"
            assert "struct Config" not in chunk.content

    def test_initializer_lines_past_the_struct_are_recovered(self):
        text = "\n".join(c.content for c in _preambles(self.chunks))
        assert "1," in text


class TestPreprocessorChunkEndLine:
    """A preprocessor node ends at column 0 of the next row (it owns its
    newline). `end_point[0] + 1` reported that next row as the chunk's last
    line, and descent then treated the line after a nested `#include` as
    already covered and dropped it."""

    _SOURCE = 'extern "C" {\n#include "x.h"\nint foo_data;\n}\n'

    def setup_method(self):
        self.chunks = CppChunker().chunk_code(self._SOURCE)

    def test_include_chunk_ends_on_its_own_line(self):
        (include,) = [c for c in self.chunks if c.node_type == "preproc_include"]
        assert (include.start_line, include.end_line) == (2, 2)

    def test_line_after_nested_include_is_not_dropped(self):
        text = "\n".join(c.content for c in _preambles(self.chunks))
        assert "int foo_data;" in text


class TestOtherLanguagesKeepRootOnlyCollection:
    def test_base_hook_never_descends(self):
        chunker = PythonChunker()
        tree = chunker.parser.parse(
            b"if True:\n    X = 1\n    def f():\n        pass\n"
        )
        guard = tree.root_node.children[0]
        assert chunker._preamble_descend_children(guard) is None
