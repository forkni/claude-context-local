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

Both SpinnerColumn call sites (search/parallel_chunker.py,
embeddings/embedder.py) now get their column from get_progress_spinner(),
which picks rich's Braille "dots2" spinner (finished glyph U+28DF) on a UTF
stream and the ASCII-only "line" spinner on any other stream. This file locks
down that choice, and that Braille really is the cp1252 encode hazard while
"line" is not.
"""

import io
import re
import sys
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console
from rich.progress import SpinnerColumn

from utils import console as console_module
from utils.console import get_progress_console, get_progress_spinner, phase_spinner


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
        """get_progress_spinner() falls back to "line" on non-UTF streams."""
        frames = self._rendered_frames("line")
        assert len(frames) > 0
        for frame in frames:
            encoded = frame.encode("cp1252")  # must not raise
            assert isinstance(encoded, bytes)


class TestGetProgressSpinner:
    """Braille "dots2" on a UTF stream, ASCII "line" on any other stream."""

    BRAILLE = "⣟"  # '⣟'

    # Real text streams, not MagicMock: Console.file reads
    # getattr(file, "rich_proxied_file", file), and a bare MagicMock
    # would return an auto-created attribute there.
    @staticmethod
    def _console_on(encoding: str) -> Console:
        return Console(file=io.TextIOWrapper(io.BytesIO(), encoding=encoding))

    @staticmethod
    def _frames(column: SpinnerColumn) -> list:
        return list(column.spinner.frames)

    def test_utf8_stream_gets_dots2_with_braille_finish(self):
        column = get_progress_spinner(self._console_on("utf-8"))
        frames = self._frames(column)
        assert "".join(frames) == "⣾⣽⣻⢿⡿⣟⣯⣷"
        assert self.BRAILLE in frames
        # pyrefly: ignore [missing-attribute]
        assert column.finished_text.plain == self.BRAILLE

    def test_cp1252_stream_gets_ascii_line_spinner(self):
        column = get_progress_spinner(self._console_on("cp1252"))
        frames = self._frames(column)
        assert frames == ["-", "\\", "|", "/"]
        for frame in frames:
            frame.encode("cp1252")  # must not raise

    def test_stream_without_encoding_gets_ascii_line_spinner(self):
        """rich reports "utf-8" for such a stream; the helper must not trust it."""
        stream = MagicMock(spec=["write", "flush", "isatty"])
        stream.isatty.return_value = False
        column = get_progress_spinner(Console(file=stream))
        assert self._frames(column) == ["-", "\\", "|", "/"]


class _Utf8Buffer(io.StringIO):
    encoding = "utf-8"


class TestPhaseSpinner:
    """`phase_spinner`: a spinner + elapsed line for steps with no progress count."""

    def test_non_terminal_draws_nothing(self, monkeypatch):
        buf = _Utf8Buffer()
        monkeypatch.setattr(
            console_module, "get_progress_console", lambda: Console(file=buf)
        )
        ran = []
        with phase_spinner("Saving index..."):
            ran.append(True)
        assert ran == [True]
        assert buf.getvalue() == ""

    def test_terminal_ends_with_the_finished_glyph_and_time(self, monkeypatch):
        buf = _Utf8Buffer()
        console = Console(file=buf, force_terminal=True, width=80, color_system=None)
        monkeypatch.setattr(console_module, "get_progress_console", lambda: console)
        with phase_spinner("Building graph..."):
            pass
        plain = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "\n", buf.getvalue())
        frames = [f.strip() for f in plain.replace("\r", "\n").split("\n") if f.strip()]
        assert frames[-1] == "⣟ Building graph... (0s)"

    def test_body_errors_propagate(self, monkeypatch):
        console = Console(file=_Utf8Buffer(), force_terminal=True)
        monkeypatch.setattr(console_module, "get_progress_console", lambda: console)
        with pytest.raises(OSError, match="disk full"), phase_spinner("Saving..."):
            raise OSError("disk full")
