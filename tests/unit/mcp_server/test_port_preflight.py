"""Unit tests for the HTTP-transport port pre-flight check in mcp_server.server.

Diagnosed 2026-08-01: a second `--transport http` instance launched against a
port already held by another process used to load the embedding model and log
"APPLICATION READY" before discovering the bind failure. _find_port_conflict()
and _describe_port_owner() let the server detect the conflict up front, before
any of that work happens. See tests/fast_integration/test_http_port_conflict.py
for the end-to-end regression test that drives the real CLI entry point.
"""

from __future__ import annotations

import socket

from mcp_server.server import _describe_port_owner, _find_port_conflict


class TestFindPortConflict:
    def test_returns_none_for_free_ephemeral_port(self) -> None:
        # Reserve a free port, then release it immediately so it's (almost
        # certainly) free again -- avoids hardcoding a port number that might
        # collide with something else on the test machine.
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        assert _find_port_conflict("127.0.0.1", port) is None

    def test_returns_description_for_bound_port(self) -> None:
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        try:
            result = _find_port_conflict("127.0.0.1", port)
            assert result is not None
            assert str(port) in result
            assert "127.0.0.1" in result
        finally:
            holder.close()

    def test_dual_stack_localhost_detects_conflict_on_either_family(self) -> None:
        """ "localhost" resolves to both ::1 and 127.0.0.1 on this machine;
        a conflict on either address must be reported.
        """
        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        try:
            result = _find_port_conflict("localhost", port)
            assert result is not None
        finally:
            holder.close()

    def test_probe_does_not_leave_port_bound(self) -> None:
        """A free-port probe must release the socket, not hold it open."""
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        assert _find_port_conflict("127.0.0.1", port) is None
        # If the probe leaked the socket, a second bind attempt would fail.
        recheck = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        recheck.bind(("127.0.0.1", port))
        recheck.close()


class TestDescribePortOwner:
    def test_returns_a_string_for_unbound_port(self) -> None:
        """No listener on the port -- still returns a human-readable string,
        never raises.
        """
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        result = _describe_port_owner(port)
        assert isinstance(result, str)
        assert result != ""

    def test_identifies_pid_for_bound_port(self) -> None:
        """When something is actually listening, the description should
        reference the current process's own PID (this test process holds
        the socket).
        """
        import os

        holder = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        holder.bind(("127.0.0.1", 0))
        holder.listen(1)
        port = holder.getsockname()[1]
        try:
            result = _describe_port_owner(port)
            # psutil may be unavailable/restricted in some CI sandboxes; if so
            # this degrades to the manual-lookup hint instead of a PID match.
            assert isinstance(result, str)
            assert str(os.getpid()) in result or "unknown process" in result
        finally:
            holder.close()
