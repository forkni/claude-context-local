"""Encoding-aware rich Console and spinner factories for progress displays."""

import sys
from typing import Any

from rich.console import Console
from rich.progress import SpinnerColumn


_UNICODE_ENCODINGS = ("utf8", "utf16", "utf32")


def _stream_can_unicode(stream: Any) -> bool:
    """Return True when ``stream`` declares a UTF-8/16/32 encoding.

    A stream with no ``encoding`` attribute (some test/CI capture shims) or a
    legacy codepage such as cp1252 returns False.
    """
    enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
    return enc in _UNICODE_ENCODINGS


def get_progress_console() -> Console:
    """Return a Console for the current stdout environment.

    Forces terminal mode (animated output) only when stdout is an interactive
    terminal with a UTF encoding. This does not make every glyph safe: rich's
    legacy_windows auto-detection is a separate knob, so an attached cp1252
    console still renders through LegacyWindowsTerm. Use
    :func:`get_progress_spinner` for the spinner column, which picks an
    ASCII-only spinner on such streams.
    """
    stream = sys.stdout
    is_tty = hasattr(stream, "isatty") and stream.isatty()
    return Console(force_terminal=is_tty and _stream_can_unicode(stream))


def get_progress_spinner(console: Console) -> SpinnerColumn:
    """Return the spinner column for a progress bar drawn on ``console``.

    On a UTF stream: rich's Braille "dots2" spinner (frames include U+28DF
    '⣟'), with '⣟' as the finished glyph. On any other stream (cp1252, no
    declared encoding): the ASCII-only "line" spinner ('-', '\\', '|', '/'),
    because Braille glyphs raise UnicodeEncodeError on a cp1252 console.

    The check reads ``console.file`` and not ``console.encoding``: rich reports
    "utf-8" for a stream that declares no encoding.
    """
    if _stream_can_unicode(console.file):
        return SpinnerColumn(spinner_name="dots2", finished_text="⣟")
    return SpinnerColumn(spinner_name="line")
