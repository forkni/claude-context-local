"""Regression tests for Workstream A2 -- C/C++ preprocessor-conditional
neutralization.

Neither tree-sitter-c nor tree-sitter-cpp implements the preprocessor:
`#if`/`#ifdef`/.../`#endif` are parsed as literal tokens, and an unbalanced
or macro-heavy conditional desyncs the parser into an ERROR node that
swallows every definition until the next recovery point -- e.g. a `#if` in
the middle of a parameter list or an initializer list. `neutralize_
preprocessor_conditionals` (chunking/languages/_c_family.py) blanks those
directive lines to whitespace before parsing, via the same
`LanguageChunker.preprocess_source_for_parse` seam GLSL already uses for its
own, unrelated parse-error case (see
`test_glsl_layout_qualifier_neutralization.py`, which this module is modeled
on) -- both branches of a conditional keep their bodies in place, only the
directive lines themselves are blanked.

Measured over 294 real C/C++ files: ERROR lines 45,786 (23.3%) -> 3,803
(1.9%), a 91.7% reduction, with zero definitions lost (10,217 -> 10,217).

The blanker must replace every non-newline byte individually
(`re.sub(rb"[^\\n]", b" ", ...)`), not multiply a space by the match's total
length (`b" " * len(match)`) -- the naive form preserves total byte length
but collapses every embedded newline in a multi-line match (e.g. a
backslash-continued directive) into a space, silently shifting every
downstream `start_line`/`end_line` for the rest of the file. This is called
out in the plan as the highest-severity risk in this workstream, so it gets
a dedicated invariant test that also exercises the naive form for contrast.
"""

import re

from chunking.languages._c_family import neutralize_preprocessor_conditionals
from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker


def _names(chunker, source):
    """Return {node_type: name} for every chunk with a resolved name."""
    return {
        chunk.node_type: chunk.metadata.get("name")
        for chunk in chunker.chunk_code(source)
        if chunk.metadata.get("name") is not None
    }


class TestConditionalInParameterListRecovers:
    """A `#if` inside a function's parameter list desyncs the raw parser
    (confirmed via `chunker.parser.parse(source_bytes)` directly: `has_error`
    is True without the fix) -- the neutralized parse must still resolve the
    enclosing function's name and body correctly."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_enclosing_function_recovers(self):
        source = """
int compute(int a,
#if FEATURE_X
    int b,
#endif
    int c) {
    return a + c;
}
"""
        assert _names(self.chunker, source) == {"function_definition": "compute"}

    def test_raw_parse_without_the_fix_actually_errors(self):
        """Sanity check that this shape is a genuine regression case, not a
        no-op the fix happens to not break -- confirms the fixture is
        meaningful."""
        source = b"""
int compute(int a,
#if FEATURE_X
    int b,
#endif
    int c) {
    return a + c;
}
"""
        tree = self.chunker.parser.parse(source)
        assert tree.root_node.has_error is True


class TestConditionalInInitializerListRecovers:
    """A `#if` inside an initializer list desyncs the raw parser the same
    way -- the enclosing function must still resolve."""

    def setup_method(self):
        self.chunker = CppChunker()

    def test_enclosing_function_recovers(self):
        source = """
void configure(void) {
    int table[] = {
        1,
#if FEATURE_Y
        2,
#endif
        3
    };
}
"""
        assert _names(self.chunker, source) == {"function_definition": "configure"}

    def test_raw_parse_without_the_fix_actually_errors(self):
        source = b"""
void configure(void) {
    int table[] = {
        1,
#if FEATURE_Y
        2,
#endif
        3
    };
}
"""
        tree = self.chunker.parser.parse(source)
        assert tree.root_node.has_error is True


class TestByteLengthAndNewlinePositionInvariants:
    """`neutralize_preprocessor_conditionals` must preserve total byte length
    and every newline's byte offset exactly -- downstream chunk start_line/
    end_line are computed against the rewritten buffer and must line up with
    the original source `chunk_parsed` actually slices text from."""

    def _assert_invariants(self, original: bytes, rewritten: bytes) -> None:
        assert len(rewritten) == len(original)
        original_newlines = [i for i, b in enumerate(original) if b == 0x0A]
        rewritten_newlines = [i for i, b in enumerate(rewritten) if b == 0x0A]
        assert rewritten_newlines == original_newlines

    def test_simple_ifdef_endif_preserves_length_and_newlines(self):
        source = b"#ifdef DEBUG\nint x;\n#endif\nint y;\n"
        self._assert_invariants(source, neutralize_preprocessor_conditionals(source))

    def test_backslash_continued_directive_preserves_length_and_newlines(self):
        """The naive-blanker trap: a `#if` continued onto a second physical
        line via a trailing backslash. Both physical lines of the directive
        must be blanked (byte-for-byte) while the embedded newline between
        them stays exactly where it was."""
        source = b"#if defined(FOO) \\\n    && defined(BAR)\nint y;\n#endif\nint z;\n"
        rewritten = neutralize_preprocessor_conditionals(source)
        self._assert_invariants(source, rewritten)
        # The directive's own two lines are blanked to spaces only -- no
        # stray '#', 'if', 'defined', etc. survives inside them.
        rewritten_lines = rewritten.split(b"\n")
        assert rewritten_lines[0].strip(b" ") == b""
        assert rewritten_lines[1].strip(b" ") == b""
        # Non-directive lines are untouched.
        assert rewritten_lines[2] == b"int y;"
        assert rewritten_lines[4] == b"int z;"

    def test_naive_multiply_blanker_would_have_collapsed_the_newline(self):
        """Contrast case proving the invariant test above is not vacuous:
        the rejected `b" " * len(match)` form passes the length check but
        fails the newline-position check on the exact same fixture."""
        source = b"#if defined(FOO) \\\n    && defined(BAR)\nint y;\n#endif\nint z;\n"
        pattern = re.compile(
            rb"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|elif|elifdef|elifndef|else|endif)\b"
            rb"(?:[^\n]*\\\n)*[^\n]*",
            re.M,
        )
        naive = pattern.sub(lambda m: b" " * len(m.group(0)), source)

        assert len(naive) == len(source)  # length preserved...
        original_newlines = [i for i, b in enumerate(source) if b == 0x0A]
        naive_newlines = [i for i, b in enumerate(naive) if b == 0x0A]
        assert naive_newlines != original_newlines  # ...but positions are not

    def test_multiple_conditionals_preserve_length_and_newlines(self):
        source = (
            b"#if A\nint a;\n#elif B\nint b;\n#else\nint c;\n#endif\nvoid f(void) {}\n"
        )
        self._assert_invariants(source, neutralize_preprocessor_conditionals(source))


class TestIncludeDefinePragmaNotBlanked:
    """`#include`/`#define`/`#pragma` are deliberately excluded -- they parse
    as real `preproc_include`/`preproc_def` chunk nodes
    (`chunking/language_registry.py`'s `NODE_TYPE_MAP`), so blanking them
    would silently delete indexed content."""

    def test_include_define_pragma_pass_through_unchanged(self):
        source = (
            b"#include <stdio.h>\n"
            b"#define MAX(a, b) ((a) > (b) ? (a) : (b))\n"
            b"#pragma once\n"
            b"int x;\n"
        )
        assert neutralize_preprocessor_conditionals(source) == source

    def test_conditional_alongside_include_define_pragma(self):
        """Only the conditional directive lines are blanked; include/define/
        pragma lines in the same file stay byte-identical."""
        source = (
            b"#include <stdio.h>\n"
            b"#define FOO 1\n"
            b"#pragma once\n"
            b"#ifdef FOO\n"
            b"int x;\n"
            b"#endif\n"
        )
        rewritten = neutralize_preprocessor_conditionals(source)
        lines = rewritten.split(b"\n")
        assert lines[0] == b"#include <stdio.h>"
        assert lines[1] == b"#define FOO 1"
        assert lines[2] == b"#pragma once"
        assert lines[3].strip(b" ") == b""  # #ifdef FOO -- blanked
        assert lines[4] == b"int x;"
        assert lines[5].strip(b" ") == b""  # #endif -- blanked


class TestChunkContentPreservesOriginalDirectiveText:
    """`chunk_parsed` slices chunk text from the original, un-rewritten
    source (see `LanguageChunker.chunk_code`'s docstring) -- a chunk
    spanning a neutralized conditional must contain the real directive text
    users expect to see, not spaces."""

    def test_function_chunk_contains_original_directive_lines(self):
        chunker = CppChunker()
        source = """void configure(void) {
    int table[] = {
        1,
#if FEATURE_Y
        2,
#endif
        3
    };
}
"""
        chunks = chunker.chunk_code(source)
        (chunk,) = [c for c in chunks if c.metadata.get("name") == "configure"]
        assert "#if FEATURE_Y" in chunk.content
        assert "#endif" in chunk.content


class TestCChunkerOverrideWired:
    """`CChunker.preprocess_source_for_parse` mirrors `CppChunker`'s --
    smoke-test that the override is actually wired, not just present."""

    def test_c_conditional_in_parameter_list_recovers(self):
        chunker = CChunker()
        source = """
int compute(int a,
#if FEATURE_X
    int b,
#endif
    int c) {
    return a + c;
}
"""
        assert _names(chunker, source) == {"function_definition": "compute"}
