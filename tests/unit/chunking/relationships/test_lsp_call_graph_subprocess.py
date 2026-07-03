"""Real-subprocess regression tests for chunking.relationships.lsp_call_graph.

The original ``LSPResolver`` implementation spawned a *new* daemon reader
thread per JSON-RPC request and abandoned it (rather than cancelling it) on
timeout, while never continuously draining stdout in the background. Against
a real ``basedpyright-langserver`` this produced a genuine, reproducing
indefinite hang: a bidirectional pipe deadlock (our stdin write blocks once
the server's own stdout pipe buffer fills) plus JSON-RPC framing corruption
(two reader threads concurrently consuming one buffered stream after a
timeout).

Unlike ``test_lsp_call_graph.py`` (which mocks ``Popen``/``_LSP_AVAILABLE`` or
feeds ``io.BytesIO`` streams that hit EOF immediately), these tests drive
``_LspClient`` — and, end-to-end, ``LSPResolver.resolve()`` — against a real
child process (``tests/fixtures/fake_lsp_server.py``) so the concurrency bug
classes above are actually exercised.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from chunking.relationships.lsp_call_graph import LSPResolver, _LspClient


_LOG = logging.getLogger("test_lsp_subprocess")
_FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "fake_lsp_server.py"


def _argv(mode: str) -> list[str]:
    return [sys.executable, str(_FIXTURE), mode]


def _wait_until(predicate, timeout: float = 3.0, interval: float = 0.05) -> bool:
    """Poll *predicate* until it's True or *timeout* elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


# ---------------------------------------------------------------------------
# _dispatch — in-process unit tests (no subprocess needed)
# ---------------------------------------------------------------------------


class TestLspClientDispatch:
    """_dispatch's response-storage and server-request-stub logic in isolation."""

    @staticmethod
    def _bare_client() -> _LspClient:
        """Construct a _LspClient without spawning a real process."""
        client = _LspClient.__new__(_LspClient)
        client._cond = threading.Condition()
        client._responses = {}
        return client

    def test_response_stored_and_retrievable(self) -> None:
        client = self._bare_client()
        client._write = lambda obj: True  # type: ignore[method-assign]

        client._dispatch({"jsonrpc": "2.0", "id": 42, "result": "ok"})
        assert client._responses[42]["result"] == "ok"

    def test_notification_discarded(self) -> None:
        client = self._bare_client()
        client._write = lambda obj: True  # type: ignore[method-assign]

        client._dispatch(
            {
                "jsonrpc": "2.0",
                "method": "textDocument/publishDiagnostics",
                "params": {},
            }
        )
        assert client._responses == {}

    def test_workspace_configuration_stubbed(self) -> None:
        client = self._bare_client()
        writes: list[dict] = []
        client._write = lambda obj: writes.append(obj) or True  # type: ignore[method-assign]

        msg = {
            "jsonrpc": "2.0",
            "id": "srv-1",
            "method": "workspace/configuration",
            "params": {"items": [{"section": "a"}, {"section": "b"}]},
        }
        client._dispatch(msg)

        assert len(writes) == 1
        assert writes[0]["id"] == "srv-1"
        assert writes[0]["result"] == [None, None]
        assert client._responses == {}  # server->client requests aren't responses


# ---------------------------------------------------------------------------
# Real subprocess: baseline lifecycle
# ---------------------------------------------------------------------------


class TestLspClientEchoLifecycle:
    def test_initialize_and_close_leaves_no_process(self, tmp_path: Path) -> None:
        client = _LspClient(
            _argv("echo"),
            tmp_path,
            per_request_timeout=5.0,
            max_total_seconds=10.0,
            logger=_LOG,
        )
        try:
            resp = client.request("initialize", {"processId": None}, req_id=1)
            assert resp is not None
            assert resp["id"] == 1
            assert "capabilities" in resp["result"]

            client.notify("initialized", {})
        finally:
            client.close()

        assert _wait_until(lambda: client._proc.poll() is not None)


# ---------------------------------------------------------------------------
# Real subprocess: chatty server — write-deadlock regression
# ---------------------------------------------------------------------------


class TestLspClientChattyDeadlock:
    def test_chatty_server_does_not_deadlock_on_write(self, tmp_path: Path) -> None:
        """Regression test for the primary bug: a server that floods stdout
        before responding must not block our stdin writes. The old
        implementation never drained stdout in the background, so this
        scenario deadlocked indefinitely; the persistent reader thread must
        keep the pipe drained throughout."""
        client = _LspClient(
            _argv("chatty"),
            tmp_path,
            per_request_timeout=10.0,
            max_total_seconds=20.0,
            logger=_LOG,
        )
        try:
            start = time.monotonic()
            resp = client.request("initialize", {"processId": None}, req_id=1)
            elapsed = time.monotonic() - start

            assert resp is not None, "no response — looks deadlocked"
            assert elapsed < 10.0, f"took {elapsed:.1f}s — looks like a hang"

            # A large didOpen-equivalent write, issued while the chatty flood
            # is still arriving, must also not block.
            big_text = "x" * 500_000
            client.notify(
                "textDocument/didOpen",
                {"textDocument": {"uri": "file:///big.py", "text": big_text}},
            )
        finally:
            client.close()

        assert _wait_until(lambda: client._proc.poll() is not None)


# ---------------------------------------------------------------------------
# Real subprocess: slow server — per-request timeout must not desync
# ---------------------------------------------------------------------------


class TestLspClientSlowServer:
    def test_timeout_then_recovery_stays_correlated(self, tmp_path: Path) -> None:
        """A response slower than the per-request timeout must return None
        for that call without corrupting subsequent request/response
        correlation. The old design spawned a new reader thread per attempt
        and abandoned the old one on timeout, so two threads ended up reading
        the same stream concurrently -- corrupting Content-Length framing for
        every request after the first timeout. The single persistent reader
        makes this structurally impossible; this test proves it end-to-end.
        """
        client = _LspClient(
            _argv("slow"),  # fixture sleeps 0.5s before every response
            tmp_path,
            per_request_timeout=0.1,  # much shorter than the fixture's delay
            max_total_seconds=15.0,
            logger=_LOG,
        )
        try:
            resp1 = client.request("initialize", {"processId": None}, req_id=1)
            assert resp1 is None  # times out well before the fixture responds

            # Let the late id=1 response actually land (harmlessly unclaimed)
            # before issuing a fresh, correctly-timed request.
            time.sleep(0.7)
            client._per_request_timeout = 2.0

            resp2 = client.request(
                "textDocument/prepareCallHierarchy",
                {"textDocument": {"uri": "file:///x.py"}},
                req_id=2,
            )
            assert resp2 is not None
            assert resp2["id"] == 2
            assert resp2["result"] == []
        finally:
            client.close()


# ---------------------------------------------------------------------------
# Real subprocess: hanging server — aggregate watchdog must bound the wait
# ---------------------------------------------------------------------------


class TestLspClientWatchdog:
    def test_hang_bounded_by_aggregate_timeout_not_per_request(
        self, tmp_path: Path
    ) -> None:
        """A server that never responds to anything (the exact user-reported
        symptom) must be bounded by the AGGREGATE watchdog, not left to the
        (deliberately much longer) per-request timeout -- proving
        lsp_total_timeout_seconds, not lsp_timeout_seconds, is what saves us
        here. The subprocess must also actually be dead afterward."""
        max_total = 2.0
        client = _LspClient(
            _argv("hang"),
            tmp_path,
            per_request_timeout=30.0,  # deliberately much longer than max_total
            max_total_seconds=max_total,
            logger=_LOG,
        )
        pid = client._proc.pid
        start = time.monotonic()
        resp = client.request("initialize", {"processId": None}, req_id=1)
        elapsed = time.monotonic() - start

        assert resp is None
        assert elapsed < max_total + 3.0, (
            f"took {elapsed:.1f}s — aggregate watchdog (budget={max_total}s) "
            "did not bound the wait"
        )
        assert client.deadline_exceeded

        client.close()
        assert _wait_until(lambda: client._proc.poll() is not None), (
            f"hung process (pid={pid}) was not killed by the watchdog"
        )


# ---------------------------------------------------------------------------
# End-to-end: LSPResolver.resolve() through the public API
# ---------------------------------------------------------------------------


class TestLSPResolverEndToEnd:
    def test_resolve_bounded_when_server_hangs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The exact user-reported bug, reproduced and bounded: resolve()
        against a hanging basedpyright-langserver must return within the
        aggregate budget instead of hanging indefinitely."""
        import chunking.relationships.lsp_call_graph as lcg

        monkeypatch.setattr(lcg, "_LSP_AVAILABLE", True)
        monkeypatch.setattr(lcg, "_LSP_BINARY", "fake-binary-placeholder")

        (tmp_path / "mod.py").write_text("def foo():\n    pass\n")

        real_popen = subprocess.Popen

        def _fake_popen(argv, **kwargs):
            assert argv[0] == "fake-binary-placeholder"
            assert argv[1] == "--stdio"
            return real_popen(_argv("hang"), **kwargs)

        monkeypatch.setattr(lcg.subprocess, "Popen", _fake_popen)

        resolver = LSPResolver(timeout=30.0, max_total_seconds=2.0)
        start = time.monotonic()
        edges = resolver.resolve(tmp_path, {}, _LOG)
        elapsed = time.monotonic() - start

        assert edges == []
        assert elapsed < 2.0 + 4.0, f"resolve() took {elapsed:.1f}s — not bounded"
