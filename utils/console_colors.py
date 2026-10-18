"""ANSI-colored console log formatter shared by the MCP server and its worker processes.

Lives in ``utils`` (not ``mcp_server``) so ``utils/progress.py`` can use it without
importing the server package.
"""

import logging
import re


# ANSI color codes
ANSI_RED = "\033[91m"
ANSI_YELLOW = "\033[93m"
ANSI_BLUE = "\033[94m"
ANSI_RESET = "\033[0m"

# Stage-completion keywords -> blue in console output
STAGE_KEYWORDS: frozenset[str] = frozenset(
    [
        "\u2713",  # checkmark (escaped to keep this file ASCII-only; still
        # matches the literal glyph some log messages emit, e.g. embeddings/model_loader.py)
        "ready",
        "complete",
        "loaded",
        "startup",
        "starting",
        "shutdown",
        "initialized",
        "indexed",
        "built",
        "preload",
        "pre-load",
        "[tool_call]",
        "[tool_cancelled]",
        "[resource_read]",
        "[prompt_get]",
        "[init]",
        "[http cleanup]",
        "[http config]",
        "[shutdown]",
        "[switch_project]",
    ]
)

# Message-text rules, applied to INFO/DEBUG records as well as ERROR/WARNING ones, so a
# library that reports a failure at INFO (e.g. faiss.loader's "Could not load library ...
# ModuleNotFoundError(...)") still stands out. The CamelCase patterns are case-sensitive
# on purpose: they match exception/warning class names (ModuleNotFoundError,
# DeprecationWarning) but not words like "mirror".
_ERROR_TEXT_RE = re.compile(
    r"(?i:\berrors?\b)|[a-z](?:Error|Exception)\b|\bTraceback\b"
)
_WARNING_TEXT_RE = re.compile(r"(?i:\bwarnings?\b)|[a-z]Warning\b")


class ColorFormatter(logging.Formatter):
    """Console formatter: errors->red, warnings->yellow, stage INFO->blue.

    Red: ERROR/CRITICAL records, or any record whose message mentions an error.
    Yellow: WARNING records, or any record whose message mentions a warning.
    Blue: INFO records containing a stage keyword. Red beats yellow beats blue.
    The message text is matched, not the formatted line, so a logger name cannot
    trigger a color.
    """

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        message = record.getMessage()
        if record.levelno >= logging.ERROR or _ERROR_TEXT_RE.search(message):
            return f"{ANSI_RED}{text}{ANSI_RESET}"
        if record.levelno == logging.WARNING or _WARNING_TEXT_RE.search(message):
            return f"{ANSI_YELLOW}{text}{ANSI_RESET}"
        if record.levelno == logging.INFO:
            msg_lower = message.lower()
            if any(kw in msg_lower for kw in STAGE_KEYWORDS):
                return f"{ANSI_BLUE}{text}{ANSI_RESET}"
        return text
