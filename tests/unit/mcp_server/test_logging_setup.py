"""Unit tests for mcp_server.server logging setup.

Tests cover:
- _configure_logging() is idempotent: calling it N times never attaches more than one
  RotatingFileHandler (guards against the -m double-import trap)
- _SafeRotatingFileHandler.rotate() swallows PermissionError / OSError so a Windows file
  lock during rollover does not raise into handleError / spam stderr
"""

from __future__ import annotations

import contextlib
import logging
import logging.handlers
import os
from unittest.mock import patch

import pytest


class TestConfigureLoggingIdempotent:
    """_configure_logging() must be a no-op on repeated calls (sentinel guard)."""

    def _count_safe_handlers(self, root: logging.Logger) -> int:
        from mcp_server.server import _SafeRotatingFileHandler

        return sum(isinstance(h, _SafeRotatingFileHandler) for h in root.handlers)

    def test_sentinel_prevents_second_call_from_adding_handlers(self) -> None:
        """With the sentinel True (module already imported), calling again is a no-op."""
        from mcp_server.server import _configure_logging

        root = logging.getLogger()
        # Module import already set the sentinel. Verify the count doesn't grow.
        assert getattr(root, "_code_search_logging_configured", False) is True
        before = len(root.handlers)
        _configure_logging()
        assert len(root.handlers) == before, (
            "Handler count must not grow when sentinel is already True"
        )

    def test_first_call_adds_exactly_one_file_handler(
        self, tmp_path: pytest.FixtureDef
    ) -> None:
        """First call (sentinel False) attaches exactly one file handler; second call
        leaves the count unchanged (sentinel now True)."""
        from mcp_server.server import _configure_logging, _SafeRotatingFileHandler

        root = logging.getLogger()
        original_handlers = list(root.handlers)
        original_sentinel = getattr(root, "_code_search_logging_configured", False)

        # Temporarily remove any existing SafeRotatingFileHandlers so we start clean.
        existing_file_hdlrs = [
            h for h in original_handlers if isinstance(h, _SafeRotatingFileHandler)
        ]
        for h in existing_file_hdlrs:
            root.removeHandler(h)

        try:
            root._code_search_logging_configured = False
            with (
                patch("mcp_server.server._log_dir", tmp_path),
                patch("mcp_server.server._log_path", tmp_path / "test.log"),
            ):
                _configure_logging()  # first call — sentinel False → adds 1 file handler
                count_after_first = self._count_safe_handlers(root)
                total_after_first = len(root.handlers)

                _configure_logging()  # second call — sentinel True → no-op
                count_after_second = self._count_safe_handlers(root)

            assert count_after_first == 1, (
                f"Expected 1 SafeRotatingFileHandler after first call, got {count_after_first}"
            )
            assert count_after_second == 1, (
                f"Second call must not add another handler (got {count_after_second})"
            )
            assert len(root.handlers) == total_after_first, (
                "Total handler count must not grow on second call"
            )
        finally:
            root._code_search_logging_configured = original_sentinel
            for h in list(root.handlers):
                if h not in original_handlers:
                    root.removeHandler(h)
                    with contextlib.suppress(Exception):
                        h.close()
            for h in existing_file_hdlrs:
                root.addHandler(h)


class TestNoFileLogBleedDuringTests:
    """The detach_server_file_logging session fixture (tests/conftest.py) must keep
    mcp_server's rotating file handler off the root logger during the test session, so
    test loggers (Simulated/Mock/corrupted-index negative paths) cannot bleed into
    logs/mcp_server.log and masquerade as real server errors."""

    def test_root_logger_has_no_server_file_handler_during_session(self) -> None:
        from mcp_server.server import _SafeRotatingFileHandler

        root = logging.getLogger()
        offenders = [
            h for h in root.handlers if isinstance(h, _SafeRotatingFileHandler)
        ]
        assert offenders == [], (
            f"Server file handler attached to root during tests (log bleed): {offenders}"
        )


def _make_record(msg: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.error",
        level=logging.ERROR,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )


class TestDropBenignUvicornErrors:
    """_drop_benign_uvicorn_errors must silence known-cosmetic uvicorn.error noise
    (disconnected clients, SSE streams cancelled at Ctrl+C shutdown) while still
    letting genuine server errors through."""

    def test_drops_completing_response_message(self) -> None:
        """The Ctrl+C shutdown symptom: standalone SSE stream cancelled mid-flight
        logs 'ASGI callable returned without completing response.' at ERROR."""
        from mcp_server.server import _drop_benign_uvicorn_errors

        record = _make_record("ASGI callable returned without completing response.")
        assert _drop_benign_uvicorn_errors(record) is False

    def test_drops_unexpected_asgi_message(self) -> None:
        from mcp_server.server import _drop_benign_uvicorn_errors

        record = _make_record(
            "Unexpected ASGI message 'http.response.body' sent, after response already completed."
        )
        assert _drop_benign_uvicorn_errors(record) is False

    def test_keeps_genuine_errors(self) -> None:
        from mcp_server.server import _drop_benign_uvicorn_errors

        record = _make_record("Server error: boom")
        assert _drop_benign_uvicorn_errors(record) is True


class TestSafeRotatingFileHandler:
    """_SafeRotatingFileHandler.rotate() must swallow file-lock errors gracefully."""

    def test_permission_error_on_rename_does_not_raise(
        self, tmp_path: pytest.FixtureDef
    ) -> None:
        from mcp_server.server import _SafeRotatingFileHandler

        log_file = tmp_path / "test.log"
        handler = _SafeRotatingFileHandler(
            str(log_file), maxBytes=50, backupCount=1, delay=True
        )
        handler.setFormatter(logging.Formatter("%(message)s"))

        def _locked_rename(source: str, dest: str) -> None:
            raise PermissionError("[WinError 32] The process cannot access the file")

        with patch.object(os, "rename", side_effect=_locked_rename):
            # emit() triggers shouldRollover → True (content > 50 bytes) → doRollover → rotate
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="x" * 100,
                args=(),
                exc_info=None,
            )
            handler.emit(record)  # must not raise

        handler.close()
        assert log_file.exists(), "Handler must keep writing after a failed rollover"

    def test_os_error_on_rename_does_not_raise(
        self, tmp_path: pytest.FixtureDef
    ) -> None:
        from mcp_server.server import _SafeRotatingFileHandler

        log_file = tmp_path / "test.log"
        handler = _SafeRotatingFileHandler(
            str(log_file), maxBytes=50, backupCount=1, delay=True
        )
        handler.setFormatter(logging.Formatter("%(message)s"))

        def _ioerror_rename(source: str, dest: str) -> None:
            raise OSError("disk full")

        with patch.object(os, "rename", side_effect=_ioerror_rename):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="",
                lineno=0,
                msg="x" * 100,
                args=(),
                exc_info=None,
            )
            handler.emit(record)

        handler.close()
