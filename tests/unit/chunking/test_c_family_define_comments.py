"""A `/* */` splitting a `#define` body no longer ERRORs it (ADR-0087, cause E).

Both grammars give a `#define` one `preproc_arg` token, which stops at
`/*`. A comment with directive content on both sides splits the argument
in two, so the whole macro -- and often the code after it -- becomes an
ERROR (`ocl_defs.hpp`, `moduleobject.h`, the HAL intrinsics headers).
"""

from chunking.languages._c_family import neutralize_define_comments
from chunking.languages.c import CChunker
from chunking.languages.cpp import CppChunker, CudaChunker
from tests.unit.chunking.conftest import assert_length_and_newline_invariants


_BS = chr(92)

_COMMENT_MID_BODY = (
    f"#define RUN(cond) {_BS}\n"
    f"    if (cond) {{ {_BS}\n"
    f"        f(); /* TODO: log */ {_BS}\n"
    f"    }}\n"
    "int after(void) { return 0; }\n"
)

_COMMENT_IN_INITIALIZER = (
    f"#define HEAD_INIT {{ {_BS}\n"
    f"    0, /* m_init */ {_BS}\n"
    f"    0, /* m_index */ {_BS}\n"
    "  }\n"
    "int after(void) { return 0; }\n"
)

_COMMENT_WITH_CONTINUATION_INSIDE = (
    f"#define STATE_INIT {_BS}\n"
    f"    {{ {_BS}\n"
    f"        /* spans {_BS}\n"
    f"           lines */ {_BS}\n"
    f"        .a = 1, {_BS}\n"
    "    }\n"
    "int after(void) { return 0; }\n"
)

_CHUNKERS = (CChunker, CppChunker, CudaChunker)


def _has_error(cls, source: str) -> bool:
    chunker = cls()
    tree = chunker.parser.parse(chunker.preprocess_source_for_parse(source.encode()))
    return tree.root_node.has_error


def _names(cls, source: str) -> set[str]:
    return {c.metadata.get("name") for c in cls().chunk_code(source)}


class TestDefineCommentRepair:
    def test_comment_mid_body_parses_clean(self):
        for cls in _CHUNKERS:
            assert not _has_error(cls, _COMMENT_MID_BODY), cls.__name__
            assert {"RUN", "after"} <= _names(cls, _COMMENT_MID_BODY), cls.__name__

    def test_comments_in_initializer_parse_clean(self):
        for cls in _CHUNKERS:
            assert not _has_error(cls, _COMMENT_IN_INITIALIZER), cls.__name__
            assert {"HEAD_INIT", "after"} <= _names(cls, _COMMENT_IN_INITIALIZER)

    def test_continuation_inside_a_comment_survives(self):
        for cls in _CHUNKERS:
            assert not _has_error(cls, _COMMENT_WITH_CONTINUATION_INSIDE), cls.__name__

    def test_chunk_text_keeps_the_comment(self):
        for cls in _CHUNKERS:
            macro = next(
                c
                for c in cls().chunk_code(_COMMENT_MID_BODY)
                if c.metadata.get("name") == "RUN"
            )
            assert "/* TODO: log */" in macro.content, cls.__name__


class TestNeutralizeDefineComments:
    def test_preserves_length_and_newlines(self):
        for source in (
            _COMMENT_MID_BODY,
            _COMMENT_IN_INITIALIZER,
            _COMMENT_WITH_CONTINUATION_INSIDE,
        ):
            raw = source.encode()
            assert_length_and_newline_invariants(raw, neutralize_define_comments(raw))

    def test_blanks_only_the_splitting_comment(self):
        raw = _COMMENT_MID_BODY.encode()
        out = neutralize_define_comments(raw)
        assert b"/* TODO" not in out
        assert out.replace(b" ", b"") == raw.replace(b"/* TODO: log */", b"").replace(
            b" ", b""
        )

    def test_keeps_continuation_inside_a_blanked_comment(self):
        out = neutralize_define_comments(_COMMENT_WITH_CONTINUATION_INSIDE.encode())
        assert b"spans" not in out
        assert out.count(b"\\\n") == _COMMENT_WITH_CONTINUATION_INSIDE.count(f"{_BS}\n")

    def test_leading_and_trailing_comments_are_untouched(self):
        for source in (
            "#define A /* doc */ 1\n",
            f"#define B(x) {_BS}\n    (x) /* tail */\n",
            f"#define C {_BS}\n    /* lead */ {_BS}\n    2\n",
        ):
            raw = source.encode()
            assert neutralize_define_comments(raw) == raw, source

    def test_comment_marker_inside_a_string_is_not_a_comment(self):
        raw = f'#define S "a /* b" {_BS}\n    "c */ d"\n'.encode()
        assert neutralize_define_comments(raw) == raw

    def test_comments_outside_defines_are_untouched(self):
        raw = b"int f(int a /* x */, int b) { return a; }\n"
        assert neutralize_define_comments(raw) == raw

    def test_crlf_continuation_inside_a_comment_survives(self):
        raw = _COMMENT_WITH_CONTINUATION_INSIDE.replace("\n", "\r\n").encode()
        out = neutralize_define_comments(raw)
        assert b"spans" not in out
        assert out.count(b"\\\r\n") == raw.count(b"\\\r\n")
