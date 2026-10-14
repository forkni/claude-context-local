"""C-family comments are adopted or kept, not silently dropped (ADR-0087, T5).

Four losses, each measured on the TouchDesigner tree:

- a comment on the line after an `#include` read as the include's
  same-line trailing comment, because the preprocessor node's end row is
  the row its newline ends on;
- a comment directly above a chunk was trimmed from the preamble as
  "claimed" by that chunk, but no C-family chunk adopted it;
- a multi-line comment block between two chunks was dropped as
  boilerplate;
- a preamble chunk ending in a `#define` reported one line too many.
"""

from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker, CudaChunker


_CHUNKERS = (CChunker, CppChunker, CudaChunker)

_AFTER_INCLUDE = "#include <a.h>\n/* about x */\nint x;\n"

_AFTER_ONE_LINE_DEFINE = "#define A 1\n/* doc for B */\n#define B(x) \\\n  x\n"

_DOC_ABOVE_FUNCTION = """int g;

/** Adds one. */
int add(int v) {
    return v + 1;
}
"""

_BLOCKS_BETWEEN_FUNCTIONS = """int f(void) { return 0; }

/*
 * Section: helpers
 * More text.
 */

int g(void) { return 1; }

// ----------------

int h(void) { return 2; }
"""

_DOC_ABOVE_NAMESPACE = """int f() { return 0; }

/**
 * Utilities.
 */
namespace u {
int g() { return 1; }
}
"""

_DOC_ABOVE_EXTERN_C = """int f() { return 0; }

/**
 * C API.
 */
extern "C" {
int g() { return 1; }
}
"""

_PREAMBLE_ENDING_IN_DEFINE = """int f(void) { return 0; }
#define A 1

int g(void) { return 1; }
"""


def _chunks(cls, source):
    return cls().chunk_code(source)


def _named(chunks, name):
    return next(c for c in chunks if c.metadata.get("name") == name)


def _preambles(chunks):
    return [c for c in chunks if c.node_type == "module_preamble"]


class TestCommentAfterInclude:
    def test_comment_is_kept_with_the_next_declaration(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _AFTER_INCLUDE)
            preamble = next(c for c in _preambles(chunks) if "int x;" in c.content)
            assert preamble.content.startswith("/* about x */"), cls.__name__
            assert (preamble.start_line, preamble.end_line) == (2, 3)

    def test_include_does_not_adopt_the_next_line(self):
        for cls in _CHUNKERS:
            include = next(
                c
                for c in _chunks(cls, _AFTER_INCLUDE)
                if c.node_type == "preproc_include"
            )
            assert include.metadata.get("docstring") is None, cls.__name__


class TestDocCommentAdoption:
    def test_macro_adopts_comment_after_a_one_line_define(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _AFTER_ONE_LINE_DEFINE)
            assert _named(chunks, "B").metadata.get("docstring") == "doc for B"
            preamble = _preambles(chunks)[0]
            assert (preamble.start_line, preamble.end_line) == (1, 1)
            assert "doc for B" not in preamble.content

    def test_function_adopts_doxygen_comment(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _DOC_ABOVE_FUNCTION)
            assert _named(chunks, "add").metadata.get("docstring") == "Adds one."

    def test_comment_past_a_blank_line_is_not_adopted(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _BLOCKS_BETWEEN_FUNCTIONS)
            assert _named(chunks, "h").metadata.get("docstring") is None


class TestCommentBlocksBetweenChunks:
    def test_multi_line_block_is_kept_as_a_preamble(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _BLOCKS_BETWEEN_FUNCTIONS)
            block = next(c for c in _preambles(chunks) if "Section" in c.content)
            assert (block.start_line, block.end_line) == (3, 6), cls.__name__

    def test_one_line_divider_is_still_dropped(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _BLOCKS_BETWEEN_FUNCTIONS)
            assert not any("----" in c.content for c in chunks), cls.__name__

    def test_namespace_adopts_the_block_above_it(self):
        for cls in (CppChunker, CudaChunker):
            chunks = _chunks(cls, _DOC_ABOVE_NAMESPACE)
            assert _named(chunks, "u").metadata.get("docstring") == "Utilities."
            assert not any("Utilities." in c.content for c in _preambles(chunks))

    def test_block_above_extern_c_is_kept(self):
        # `extern "C"` is descended, never a chunk, so nothing adopts it.
        for cls in (CppChunker, CudaChunker):
            chunks = _chunks(cls, _DOC_ABOVE_EXTERN_C)
            block = next(c for c in _preambles(chunks) if "C API." in c.content)
            assert (block.start_line, block.end_line) == (3, 5), cls.__name__


class TestPreambleEndLine:
    def test_preamble_ending_in_define_stops_at_its_last_line(self):
        for cls in _CHUNKERS:
            chunks = _chunks(cls, _PREAMBLE_ENDING_IN_DEFINE)
            preamble = next(c for c in _preambles(chunks) if "#define A" in c.content)
            assert (preamble.start_line, preamble.end_line) == (2, 2), cls.__name__
