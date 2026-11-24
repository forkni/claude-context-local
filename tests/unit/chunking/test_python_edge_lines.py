"""Python call and relationship edges carry file line numbers, not chunk lines.

Regression for 2026-11-24: Python extractors parse the dedented chunk text, so
every ``line_number`` counted from the chunk start (calls at file lines 6, 12
and 17 all reported line 3). Rust/C-family edges come from a whole-file
tree-sitter parse and were already file lines.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import chunking.dedent_utils as dedent_utils
from chunking.dedent_utils import smart_dedent_with_line_shift
from chunking.multi_language_chunker import (
    MultiLanguageChunker,
    _python_edge_file_line,
)


_FIXTURE = """\
import os


def top():
    x = 1
    os.getcwd()
    raise ValueError(x)


class K:
    def m(self):
        y = 2
        self.helper()
        return y

    @staticmethod
    def s():
        os.listdir(".")
"""


@pytest.fixture
def chunks(tmp_path: Path):
    file_path = tmp_path / "fx.py"
    file_path.write_text(_FIXTURE, encoding="utf-8")
    return MultiLanguageChunker(root_path=str(tmp_path)).chunk_file(str(file_path))


def _chunk(chunks, name: str):
    return next(c for c in chunks if c.name == name)


def _call_lines(chunk) -> dict[str, int]:
    return {c.callee_name: c.line_number for c in chunk.calls}


class TestChunkerEmitsFileLines:
    def test_function_call_lines(self, chunks) -> None:
        lines = _call_lines(_chunk(chunks, "top"))
        assert lines["os.getcwd"] == 6
        assert lines["ValueError"] == 7

    def test_method_call_line(self, chunks) -> None:
        assert _call_lines(_chunk(chunks, "m"))["K.helper"] == 13

    def test_decorated_method_call_line(self, chunks) -> None:
        assert _call_lines(_chunk(chunks, "s"))["os.listdir"] == 18

    def test_relationship_edge_line(self, chunks) -> None:
        raises = [
            r
            for r in _chunk(chunks, "top").relationships
            if str(r.relationship_type).endswith("RAISES")
        ]
        assert raises, "expected a RAISES edge for `raise ValueError(x)`"
        assert {r.line_number for r in raises} == {7}


class TestLineShift:
    def test_no_shift_for_plain_code(self) -> None:
        _, shift = smart_dedent_with_line_shift("def f():\n    g()\n")
        assert shift == 0

    def test_leading_blank_lines_are_counted(self) -> None:
        dedented, shift = smart_dedent_with_line_shift("\n\ndef f():\n    g()\n")
        assert dedented.startswith("def f():")
        assert shift == 2

    def test_if_true_wrapper_is_subtracted(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # No natural input found that reaches the wrapper fallback, so stub
        # the dedent result to the wrapper's exact shape.
        monkeypatch.setattr(
            dedent_utils, "smart_dedent", lambda code: "if True:\n    g()"
        )
        _, shift = smart_dedent_with_line_shift("\ng()")
        assert shift == 0  # +1 stripped blank line, -1 wrapper line


class TestSplitBlockMapping:
    """A split_block's text is signature + marker + body; the body starts at
    the chunk's start line."""

    def test_body_line_after_marker(self) -> None:
        # signature (1 line), marker (line 2), first body line is parsed line 3
        assert _python_edge_file_line(3, 40, 0, split_marker_line=2) == 40
        assert _python_edge_file_line(5, 40, 0, split_marker_line=2) == 42

    def test_signature_region_maps_to_chunk_start(self) -> None:
        assert _python_edge_file_line(1, 40, 0, split_marker_line=2) == 40

    def test_unknown_line_stays_zero(self) -> None:
        assert _python_edge_file_line(0, 40, 3, split_marker_line=None) == 0
