"""Tests for utils.console_colors.ColorFormatter.

Errors render red, warnings yellow, stage-completion INFO blue -- decided by record
level and by message text, so a library that reports a failure at INFO (faiss.loader)
still stands out.
"""

from __future__ import annotations

import logging

import pytest

from utils.console_colors import (
    ANSI_BLUE,
    ANSI_RED,
    ANSI_RESET,
    ANSI_YELLOW,
    ColorFormatter,
)


FAISS_AVX2_LINE = (
    "Could not load library with AVX2 support due to:\n"
    "ModuleNotFoundError(\"No module named 'faiss.swigfaiss_avx2'\")"
)


def _render(level: int, message: str, name: str = "test") -> str:
    record = logging.LogRecord(name, level, __file__, 1, message, None, None)
    return ColorFormatter("%(name)s - %(message)s").format(record)


class TestColorFormatter:
    @pytest.mark.parametrize(
        "level", [logging.ERROR, logging.CRITICAL], ids=["error", "critical"]
    )
    def test_error_levels_are_red(self, level: int) -> None:
        out = _render(level, "plain failure")
        assert out.startswith(ANSI_RED) and out.endswith(ANSI_RESET)

    def test_warning_level_is_yellow(self) -> None:
        assert _render(logging.WARNING, "plain").startswith(ANSI_YELLOW)

    def test_info_exception_class_name_is_red(self) -> None:
        # The motivating case: faiss logs this at INFO.
        assert _render(logging.INFO, FAISS_AVX2_LINE).startswith(ANSI_RED)

    @pytest.mark.parametrize(
        "message",
        ["Error: boom", "3 errors found", "Traceback (most recent call last)"],
        ids=["error_singular", "errors_plural", "traceback"],
    )
    def test_error_words_are_red_at_info_and_debug(self, message: str) -> None:
        assert _render(logging.INFO, message).startswith(ANSI_RED)
        assert _render(logging.DEBUG, message).startswith(ANSI_RED)

    @pytest.mark.parametrize(
        "message",
        ["Warning: low memory", "DeprecationWarning: old api"],
        ids=["warning_word", "warning_class"],
    )
    def test_warning_text_is_yellow(self, message: str) -> None:
        assert _render(logging.INFO, message).startswith(ANSI_YELLOW)

    def test_error_text_beats_warning_level(self) -> None:
        assert _render(logging.WARNING, "ModuleNotFoundError").startswith(ANSI_RED)

    def test_stage_keyword_info_is_blue(self) -> None:
        assert _render(logging.INFO, "model loaded").startswith(ANSI_BLUE)

    def test_error_beats_stage_keyword(self) -> None:
        assert _render(logging.INFO, "index loaded with errors").startswith(ANSI_RED)

    def test_word_containing_error_letters_is_not_red(self) -> None:
        # "mirror" must not trigger the CamelCase *Error rule.
        out = _render(logging.INFO, "mirror ready")
        assert out.startswith(ANSI_BLUE)

    def test_plain_debug_and_info_are_uncolored(self) -> None:
        assert _render(logging.DEBUG, "cache hit") == "test - cache hit"
        assert _render(logging.INFO, "cache hit") == "test - cache hit"

    def test_logger_name_does_not_trigger_color(self) -> None:
        assert _render(logging.INFO, "cache hit", name="error_handler") == (
            "error_handler - cache hit"
        )
