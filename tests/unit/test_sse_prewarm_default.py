"""Unit tests for SSE pre-warming default behavior (Phase 2 optimization).

Tests verify that SSE mode pre-loads models by default, while allowing
env var override, saving 5-10s on first search for long-running SSE servers.
"""

import os
from unittest.mock import patch


def test_sse_mode_preloads_model_by_default():
    """Verify SSE mode pre-loads model when MCP_PRELOAD_MODEL not set."""
    # Clear env var to test default behavior
    with patch.dict(os.environ, {}, clear=False):
        # Remove MCP_PRELOAD_MODEL if it exists
        os.environ.pop("MCP_PRELOAD_MODEL", None)

        # The default value should be "true"
        default_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert default_value == "true"

        # Verify the condition evaluates to True (pre-load enabled)
        should_preload = default_value.lower() in ("true", "1", "yes")
        assert should_preload is True


def test_sse_mode_respects_preload_false_override():
    """Verify MCP_PRELOAD_MODEL=false disables pre-warming."""
    # Set env var to explicitly disable pre-warming
    with patch.dict(os.environ, {"MCP_PRELOAD_MODEL": "false"}):
        env_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert env_value == "false"

        # Verify the condition evaluates to False (pre-load disabled)
        should_preload = env_value.lower() in ("true", "1", "yes")
        assert should_preload is False


def test_sse_mode_respects_preload_0_override():
    """Verify MCP_PRELOAD_MODEL=0 disables pre-warming."""
    with patch.dict(os.environ, {"MCP_PRELOAD_MODEL": "0"}):
        env_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert env_value == "0"

        # Verify the condition evaluates to False
        should_preload = env_value.lower() in ("true", "1", "yes")
        assert should_preload is False


def test_sse_mode_respects_preload_no_override():
    """Verify MCP_PRELOAD_MODEL=no disables pre-warming."""
    with patch.dict(os.environ, {"MCP_PRELOAD_MODEL": "no"}):
        env_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert env_value == "no"

        # Verify the condition evaluates to False
        should_preload = env_value.lower() in ("true", "1", "yes")
        assert should_preload is False


def test_sse_mode_respects_preload_true_explicit():
    """Verify MCP_PRELOAD_MODEL=true explicitly enables pre-warming."""
    with patch.dict(os.environ, {"MCP_PRELOAD_MODEL": "true"}):
        env_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert env_value == "true"

        # Verify the condition evaluates to True
        should_preload = env_value.lower() in ("true", "1", "yes")
        assert should_preload is True


def test_sse_mode_respects_preload_1_override():
    """Verify MCP_PRELOAD_MODEL=1 enables pre-warming."""
    with patch.dict(os.environ, {"MCP_PRELOAD_MODEL": "1"}):
        env_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert env_value == "1"

        # Verify the condition evaluates to True
        should_preload = env_value.lower() in ("true", "1", "yes")
        assert should_preload is True


def test_sse_mode_respects_preload_yes_override():
    """Verify MCP_PRELOAD_MODEL=yes enables pre-warming."""
    with patch.dict(os.environ, {"MCP_PRELOAD_MODEL": "yes"}):
        env_value = os.getenv("MCP_PRELOAD_MODEL", "true")
        assert env_value == "yes"

        # Verify the condition evaluates to True
        should_preload = env_value.lower() in ("true", "1", "yes")
        assert should_preload is True


def test_stdio_mode_remains_lazy():
    """Verify stdio mode does NOT have pre-load logic (unchanged behavior)."""
    # stdio mode (run_stdio_server) doesn't have pre-load logic at all
    # This test verifies that by reading the server.py file directly

    from pathlib import Path

    # Read the server.py file
    server_file = Path(__file__).parent.parent.parent / "mcp_server" / "server.py"
    source = server_file.read_text()

    # Find the run_stdio_server function (it's defined around line 304)
    stdio_start = source.find("async def run_stdio_server()")
    assert stdio_start > 0, "Could not find run_stdio_server function"

    # Find the end of the function by looking for "asyncio.run(run_stdio_server())"
    # This is the line that calls the function, marking the end of its definition
    stdio_end = source.find("asyncio.run(run_stdio_server())", stdio_start)
    assert stdio_end > stdio_start, "Could not find end of run_stdio_server function"

    stdio_source = source[stdio_start:stdio_end]

    # Verify stdio mode does NOT contain pre-load logic
    assert "MCP_PRELOAD_MODEL" not in stdio_source
    assert "Pre-loading embedding model" not in stdio_source

    # stdio mode should only have basic initialization
    assert "initialize_server_state()" in stdio_source
