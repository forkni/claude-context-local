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
import subprocess
import sys
from pathlib import Path
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


class TestIndexHandlersConfiguresLoggingEagerly:
    """Log-hygiene item F: a real force-reindex (tools/batch_index.py ->
    mcp_server.tool_specs.handle_index_directory) showed zero INFO-level
    "Call graph extraction enabled..." lines from chunking.multi_language_chunker,
    though exactly one is expected per index run (MultiLanguageChunker.__init__
    logs it once, at INFO; worker threads log the same message at DEBUG).

    Root cause: mcp_server.tools.index_handlers.handle_index_directory (:879)
    constructs the chunker (which logs at INFO in __init__) *before* anything
    in that function imports mcp_server.server -- the module whose import-time
    _configure_logging() call raises the root logger from Python's default
    level (WARNING) to DEBUG and attaches the file handler. That import is
    deferred: it only happens later in the same call, inside
    search_factory.get_searcher() (called from _setup_and_run(), after the
    chunker already exists). batch_index.py's own import graph
    (mcp_server.tool_specs -> mcp_server.tools.index_handlers) never
    imports mcp_server.server directly, so in a fresh process the chunker's
    one INFO record is emitted while root.level is still WARNING --
    logger.isEnabledFor(INFO) is False at the source, so the record never
    reaches a handler at all, file or otherwise. The later per-worker DEBUG
    records survive because by the time ParallelChunker's ThreadPoolExecutor
    workers run, get_searcher() has already forced mcp_server.server's
    import.

    Fix: _run_index_directory (the body handle_index_directory delegates to,
    both for wait=True and the background-job path) now does a deferred,
    function-local `import mcp_server.server` as its very first statement --
    before its own first logger.info call and well before
    MultiLanguageChunker.for_project() further down the same function --
    guaranteeing _configure_logging() has already run. Deferred rather than
    a module-level import: mcp_server/server.py itself (module level)
    imports mcp_server.tools (line ~53, before _configure_logging() at line
    ~192), so an eager top-level import here -- reached while
    mcp_server.tools.__init__ is still mid-execution importing this very
    module -- would re-enter mcp_server.server while it's only partially
    initialised. A call-time import carries none of that risk, and matches
    the existing deferred `from mcp_server.server import
    close_project_resources` already used elsewhere in this file (see
    handle_clear_index).

    Runs in a subprocess for the same reason as
    TestMCPServerImport.test_mcp_server_can_import_as_first_module in
    test_mcp_server.py: conftest.py's session-scoped
    detach_server_file_logging fixture force-imports mcp_server.server before
    any test runs, so within the shared pytest process
    'mcp_server.server' in sys.modules is always True and root.level is
    already DEBUG -- the exact ordering this test exists to pin down is
    unobservable there. A fresh interpreter, importing only
    mcp_server.tools.index_handlers the way batch_index.py's import graph
    does, reproduces the true starting state.
    """

    def test_importing_index_handlers_alone_does_not_configure_logging(self) -> None:
        """Merely importing the module must NOT be what carries the fix --
        the fix is call-time (function-local import), not import-time.
        Pinning this documents that choice and would catch a well-intentioned
        but circular-import-risky "just import mcp_server.server at module
        level" regression from silently changing this precondition."""
        repo_root = Path(__file__).resolve().parents[3]
        script = (
            "import logging\n"
            "import mcp_server.tools.index_handlers\n"
            "root = logging.getLogger()\n"
            "print('LEVEL', root.level)\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert result.returncode == 0, result.stderr
        assert "LEVEL 30" in result.stdout, (
            "root logger changed level on bare import alone -- if this is "
            "now DEBUG (10), the fix moved to a module-level import; verify "
            "that's not reintroducing the mcp_server.server <-> "
            f"mcp_server.tools circular-import risk.\nstdout={result.stdout}"
        )

    def test_run_index_directory_configures_logging_before_first_log(self) -> None:
        """Calling _run_index_directory -- with a directory_path that does
        not exist, so it returns the "Directory does not exist" error right
        after the existence check, before touching a real project, embedder,
        or model -- must leave the root logger configured. A nonexistent
        path keeps this fast and deterministic while still exercising the
        exact function whose prologue previously left
        MultiLanguageChunker.__init__'s one-time INFO message unloggable."""
        repo_root = Path(__file__).resolve().parents[3]
        script = (
            "import asyncio\n"
            "import logging\n"
            "import mcp_server.tools.index_handlers as ih\n"
            "root = logging.getLogger()\n"
            "print('LEVEL_BEFORE', root.level)\n"
            "result = asyncio.run(\n"
            "    ih._run_index_directory(\n"
            "        {'directory_path': 'Z:/__nonexistent_claude_context_test__'}\n"
            "    )\n"
            ")\n"
            "print('ERROR_KEY', 'error' in result)\n"
            "print('LEVEL_AFTER', root.level)\n"
            "print('HANDLERS_AFTER', len(root.handlers))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=60,
        )

        assert result.returncode == 0, result.stderr
        assert "LEVEL_BEFORE 30" in result.stdout, (
            "sanity check: root logger must start unconfigured (WARNING=30) "
            f"in a fresh process -- otherwise this test proves nothing.\n"
            f"stdout={result.stdout}"
        )
        assert "ERROR_KEY True" in result.stdout, (
            "expected _run_index_directory to short-circuit on the "
            f"nonexistent path.\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "LEVEL_AFTER 10" in result.stdout, (
            "root logger must be at DEBUG (10) once _run_index_directory has "
            "run, or any INFO log emitted before search_factory."
            "get_searcher()'s deferred mcp_server.server import -- including "
            "MultiLanguageChunker.__init__'s one-time call-graph message -- "
            f"is silently filtered before it reaches a handler.\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "HANDLERS_AFTER 0" not in result.stdout, (
            "root logger has no handlers after _run_index_directory -- the "
            "file handler that would carry that log to logs/mcp_server.log "
            f"has not been attached yet.\nstdout={result.stdout}"
        )


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
            handler.emit(record)  # must not raise

        handler.close()
        assert log_file.exists(), "Handler must keep writing after a failed rollover"

        handler.close()
