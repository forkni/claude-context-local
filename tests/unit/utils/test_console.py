"""Unit tests for utils/console.py.

get_progress_console() had zero test coverage before this file. It also
carries a claim, in its own docstring, that turned out to be false on a live
Windows terminal: "On redirected/piped/non-UTF-8 streams (pytest capture,
Windows cp1252, piped MCP stdio) rich auto-degrades to plain non-animated
text -- no UnicodeEncodeError." That is not what happens on an *attached*
cp1252 console (is_tty=True, encoding=cp1252): get_progress_console() only
sets force_terminal, a separate rich knob from legacy_windows auto-detection,
so LegacyWindowsTerm rendering still runs. SpinnerColumn's default "dots"
spinner renders Braille glyphs (U+2800+) with no ascii_only gating, and that
raised UnicodeEncodeError live on this host.

The production fix is at the two SpinnerColumn call sites
(search/parallel_chunker.py, embeddings/embedder.py: spinner_name="line"),
not in this module. This file locks down both halves of that fix: that the
default "dots" spinner really is the encode hazard, and that "line" (what
production now uses) is not, under a simulated cp1252 stream.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from rich.progress import SpinnerColumn

from utils.console import get_progress_console


class TestGetProgressConsole:
    """force_terminal is set from (is_tty and can_unicode); nothing else."""

    def test_interactive_utf8_stream_forces_terminal_on(self):
        stream = MagicMock()
        stream.encoding = "utf-8"
        stream.isatty.return_value = True
        with patch.object(sys, "stdout", stream):
            console = get_progress_console()
        assert console.is_terminal is True

    def test_interactive_cp1252_stream_does_not_force_terminal_on(self):
        """The scenario that actually crashed: an attached Windows console
        (isatty True) whose encoding is cp1252, not UTF-8."""
        stream = MagicMock()
        stream.encoding = "cp1252"
        stream.isatty.return_value = True
        with patch.object(sys, "stdout", stream):
            console = get_progress_console()
        assert console.is_terminal is False

    def test_non_interactive_stream_does_not_force_terminal_on(self):
        """Redirected/piped output (e.g. pytest capture, piped MCP stdio)."""
        stream = MagicMock()
        stream.encoding = "utf-8"
        stream.isatty.return_value = False
        with patch.object(sys, "stdout", stream):
            console = get_progress_console()
        assert console.is_terminal is False

    def test_stream_with_no_encoding_attribute_does_not_crash(self):
        """Some streams (e.g. certain test/CI capture shims) omit .encoding
        entirely; getattr(..., None) must not raise."""
        stream = MagicMock(spec=["isatty"])
        stream.isatty.return_value = True
        with patch.object(sys, "stdout", stream):
            console = get_progress_console()
        assert console.is_terminal is False


class TestSpinnerEncodingUnderCp1252:
    """Locks down the actual crash mechanism and its fix, independent of
    get_progress_console(): can the rendered spinner frame be encoded on a
    cp1252 stream, the default Windows console codepage."""

    @staticmethod
    def _rendered_frames(spinner_name: str) -> list[str]:
        column = SpinnerColumn(spinner_name=spinner_name)
        # Sample several time offsets so we exercise more than just frame 0.
        # Spinner.render() is annotated as the broader RenderResult union,
        # but always returns a rich.text.Text instance in practice.
        return [
            # pyrefly: ignore [missing-attribute]
            column.spinner.render(t).plain
            for t in (0.0, 0.1, 0.2, 0.3)
        ]

    def test_default_dots_spinner_is_not_cp1252_encodable(self):
        """Regression anchor: confirms *why* the crash happened, so this
        test would fail loudly if a future change reverted spinner_name back
        to the default without also fixing the underlying cause."""
        frames = self._rendered_frames("dots")
        with pytest.raises(UnicodeEncodeError):
            for frame in frames:
                frame.encode("cp1252")

    def test_line_spinner_is_cp1252_encodable(self):
        """production now passes spinner_name="line" at both call sites."""
        frames = self._rendered_frames("line")
        for frame in frames:
            frame.encode("cp1252")  # must not raise
