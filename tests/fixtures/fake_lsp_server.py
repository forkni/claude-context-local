"""Standalone stdio JSON-RPC fixture server for LSP-client tests.

Speaks the same ``Content-Length`` framing as ``basedpyright-langserver``,
with configurable behavior selected via the first CLI argument (*mode*):

- ``echo``   — responds immediately and correctly to every request; a
  sane-path baseline.
- ``chatty`` — floods ~1.2MB of unsolicited notifications to stdout *before*
  reading/responding to anything, simulating a server that fills the OS pipe
  buffer with diagnostics. A client that doesn't continuously drain stdout in
  the background will deadlock trying to write its next request while this
  server is stuck writing its own flood — exactly the bidirectional pipe
  deadlock ``_LspClient``'s persistent reader thread exists to prevent.
- ``slow``   — sleeps briefly before every response (longer than a short
  per-request timeout, shorter than the aggregate test budget) — verifies a
  per-request timeout doesn't desynchronise the session.
- ``hang``   — never responds to anything after reading it (including
  ``initialize``) — verifies the aggregate watchdog is what ends the session.

This is not a real language server — it implements only the request/response
shapes the real ``_LspClient``/``LSPResolver`` session drives: ``initialize``,
``initialized``, ``shutdown``, ``exit``, ``textDocument/didOpen``,
``textDocument/prepareCallHierarchy``, ``callHierarchy/outgoingCalls``.
"""

from __future__ import annotations

import json
import sys
import time
from typing import Any, BinaryIO


def _encode(obj: dict[str, Any]) -> bytes:
    body = json.dumps(obj, separators=(",", ":")).encode()
    header = f"Content-Length: {len(body)}\r\n\r\n".encode()
    return header + body


def _read_frame(stdin: BinaryIO) -> dict[str, Any] | None:
    header = b""
    while b"\r\n\r\n" not in header:
        ch = stdin.read(1)
        if not ch:
            return None
        header += ch
    length = 0
    for line in header.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":")[1].strip())
    if length == 0:
        return None
    body = stdin.read(length)
    return json.loads(body)


def _write(stdout: BinaryIO, obj: dict[str, Any]) -> None:
    stdout.write(_encode(obj))
    stdout.flush()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "echo"
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    if mode == "chatty":
        # Flood ~1.2MB of unsolicited notifications before doing anything
        # else. A client not continuously draining stdout in the background
        # will block writing its next stdin request once this fills the
        # pipe buffer (typically 4-64KB), reproducing the deadlock this
        # fixture exists to catch.
        junk = "x" * 2000
        for _ in range(600):
            _write(
                stdout,
                {
                    "jsonrpc": "2.0",
                    "method": "window/logMessage",
                    "params": {"type": 3, "message": junk},
                },
            )

    while True:
        msg = _read_frame(stdin)
        if msg is None:
            return  # EOF — client closed stdin

        method = msg.get("method")
        req_id = msg.get("id")

        if method == "exit":
            return

        if mode == "hang":
            # Never respond to anything, including initialize — the
            # aggregate watchdog must be what ends the session.
            continue

        if req_id is None:
            # Notification (didOpen, initialized) — nothing to reply to.
            continue

        if mode == "slow":
            time.sleep(0.5)

        if method == "initialize":
            _write(
                stdout,
                {"jsonrpc": "2.0", "id": req_id, "result": {"capabilities": {}}},
            )
        elif method == "shutdown":
            _write(stdout, {"jsonrpc": "2.0", "id": req_id, "result": None})
        elif (
            method == "textDocument/prepareCallHierarchy"
            or method == "callHierarchy/outgoingCalls"
        ):
            _write(stdout, {"jsonrpc": "2.0", "id": req_id, "result": []})
        else:
            _write(stdout, {"jsonrpc": "2.0", "id": req_id, "result": None})


if __name__ == "__main__":
    main()
