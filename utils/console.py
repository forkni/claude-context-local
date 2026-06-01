"""Encoding-aware rich Console factory for progress displays."""

import sys

from rich.console import Console


def get_progress_console() -> Console:
    """Return a Console safe for the current stdout environment.

    Forces the animated spinner only when stdout is an interactive terminal
    that can encode rich's Braille glyphs.  On redirected/piped/non-UTF-8
    streams (pytest capture, Windows cp1252, piped MCP stdio) rich
    auto-degrades to plain non-animated text — no UnicodeEncodeError.
    """
    stream = sys.stdout
    enc = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
    is_tty = hasattr(stream, "isatty") and stream.isatty()
    can_unicode = enc in ("utf8", "utf16", "utf32")
    return Console(force_terminal=is_tty and can_unicode)
