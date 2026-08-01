"""Repro + regression test for the HTTP-transport port-conflict startup bug.

Diagnosed 2026-08-01: launching a second ``mcp_server.server --transport http``
instance against a port already held by a healthy server used to load the
embedding model, print "APPLICATION READY - Accepting connections", and only
*then* fail to bind and exit(3). This test drives the real CLI entry point
against a socket held open in-process, so it exercises the actual startup
sequence rather than a mock.
"""

import os
import socket
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def test_http_transport_fails_fast_on_port_conflict():
    """A second HTTP-transport instance on a held port must fail before
    loading the embedding model or claiming readiness.
    """
    # Hold an ephemeral port open for the duration of the subprocess run.
    # Deliberately NOT port 8765 -- must not disturb any real running server.
    holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    port = holder.getsockname()[1]

    try:
        env = {**os.environ, "MCP_PRELOAD_MODEL": "false"}
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mcp_server.server",
                "--transport",
                "http",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    finally:
        holder.close()

    combined = result.stdout + result.stderr

    assert result.returncode == 3, (
        f"expected exit code 3 (uvicorn STARTUP_FAILURE convention), "
        f"got {result.returncode}. Output:\n{combined}"
    )
    assert "already in use" in combined, (
        f"expected an actionable 'already in use' message. Output:\n{combined}"
    )
    assert str(port) in combined, (
        f"expected the conflicting port number in the message. Output:\n{combined}"
    )
    assert "APPLICATION READY" not in combined, (
        "server claimed readiness before the port bind was ever attempted"
    )
    assert "BEFORE_LOAD" not in combined, (
        "server loaded the embedding model before checking port availability"
    )
