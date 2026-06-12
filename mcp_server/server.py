"""Low-level MCP server for Claude Code integration.

AUTO-GENERATED from FastMCP backup.
DO NOT EDIT MANUALLY - regenerate with tools/build_lowlevel_server.py

Migrated from FastMCP to official MCP SDK for:
- Explicit lifecycle management
- Predictable state initialization
- Better production reliability
"""

import argparse
import asyncio
import contextlib
import json
import logging
import logging.handlers
import os
import platform
import sys
import time
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

import anyio


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Official MCP SDK imports
from mcp.server.lowlevel import Server  # noqa: E402
from mcp.types import (  # noqa: E402
    GetPromptResult,
    Prompt,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)

# Project imports
from mcp_server.model_pool_manager import (  # noqa: E402
    get_embedder,
)

# Output formatting
from mcp_server.output_formatter import format_response  # noqa: E402


# Configure logging — dual-handler: console (colored) + rotating file (plain)
debug_mode = os.getenv("MCP_DEBUG", "").lower() in ("1", "true", "yes")
log_level = logging.DEBUG if debug_mode else logging.INFO
console_format = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if debug_mode
    else "%(asctime)s - %(message)s"
)
file_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

_log_dir = PROJECT_ROOT / "logs"
_log_path = _log_dir / "mcp_server.log"
_SESSION_START = datetime.now().strftime("%m%d%y%H%M%S")

# ANSI color codes
_ANSI_RED = "\033[91m"
_ANSI_YELLOW = "\033[93m"
_ANSI_BLUE = "\033[94m"
_ANSI_RESET = "\033[0m"

# Stage-completion keywords → blue in console output
_STAGE_KEYWORDS: frozenset[str] = frozenset(
    [
        "✓",
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


def _enable_windows_ansi() -> None:
    """Enable ANSI Virtual Terminal Processing on Windows CMD."""
    if platform.system() != "Windows":
        return
    try:
        import ctypes

        # STD_OUTPUT_HANDLE=-11, STD_ERROR_HANDLE=-12; ENABLE_VIRTUAL_TERMINAL_PROCESSING=0x0004
        kernel32 = ctypes.windll.kernel32
        for std_handle in (-11, -12):
            handle = kernel32.GetStdHandle(std_handle)
            mode = ctypes.c_ulong(0)
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


class _ColorFormatter(logging.Formatter):
    """Console formatter: ERROR/CRITICAL→red, WARNING→yellow, stage INFO→blue."""

    def format(self, record: logging.LogRecord) -> str:
        text = super().format(record)
        if record.levelno >= logging.ERROR:
            return f"{_ANSI_RED}{text}{_ANSI_RESET}"
        if record.levelno == logging.WARNING:
            return f"{_ANSI_YELLOW}{text}{_ANSI_RESET}"
        if record.levelno == logging.INFO:
            msg_lower = record.getMessage().lower()
            if any(kw in msg_lower for kw in _STAGE_KEYWORDS):
                return f"{_ANSI_BLUE}{text}{_ANSI_RESET}"
        return text


class _SafeRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """RotatingFileHandler that tolerates Windows file locks during rollover.

    Swallows WinError 32 (another process holds the file open) so rotation skips
    gracefully rather than spamming stderr with logging-error tracebacks.

    Backup files are named ``mcp_server_<mmddyyhhmmss>.log`` where the timestamp
    is fixed at session start — unique per server run, no numeric suffix needed.
    """

    def rotate(self, source: str, dest: str) -> None:
        with contextlib.suppress(PermissionError, OSError):
            super().rotate(source, dest)

    def doRollover(self) -> None:  # noqa: N802
        if self.stream:
            self.stream.close()
            self.stream = None  # pyrefly: ignore [bad-assignment]  # stdlib sets stream=None during rollover; typeshed stub is non-optional
        stem = Path(self.baseFilename).stem  # "mcp_server"
        dfn = str(Path(self.baseFilename).parent / f"{stem}_{_SESSION_START}.log")
        self.rotate(self.baseFilename, dfn)  # suppresses PermissionError/OSError
        if not self.delay:
            self.stream = self._open()


def _configure_logging() -> None:
    """Configure root-logger handlers exactly once regardless of how many times this
    module body executes (guards against the -m double-import trap)."""
    root = logging.getLogger()
    if getattr(root, "_code_search_logging_configured", False):
        return

    _enable_windows_ansi()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(_ColorFormatter(console_format, datefmt="%H:%M:%S"))

    _log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = _SafeRotatingFileHandler(
        _log_path, maxBytes=5_000_000, backupCount=3, encoding="utf-8", delay=True
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(file_format, datefmt="%H:%M:%S"))

    root.setLevel(logging.DEBUG)
    root.addHandler(console_handler)
    root.addHandler(file_handler)
    root._code_search_logging_configured = True  # type: ignore[attr-defined]


_configure_logging()

logger = logging.getLogger(__name__)
logger.info("File logging -> %s", _log_path)

if debug_mode:
    logging.getLogger("mcp").setLevel(logging.DEBUG)
else:
    logging.getLogger("mcp").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

# Multi-model pool configuration imported from search.config


# ============================================================================
# HELPER FUNCTIONS - Now imported from dedicated modules
# ============================================================================

# Import resource management functions from resource_manager.py
from mcp_server.resource_manager import (  # noqa: E402, F401 - Re-exported for backward compatibility
    _cleanup_previous_resources,
    close_project_resources,
    initialize_server_state,
)

# Import search factory functions from search_factory.py
from mcp_server.search_factory import (  # noqa: E402, F401 - Re-exported for backward compatibility
    get_index_manager,
    get_searcher,
)


# ============================================================================
# Explicit lifecycle management
# ============================================================================
# Server instance will be created without custom lifespan
# Global state initialization happens in Starlette app_lifespan below

# Create server instance
server = Server("Code Search")

# Import tool registry
from mcp_server.tool_registry import build_tool_list  # noqa: E402


# ============================================================================
# SERVER HANDLERS
# ============================================================================


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available tools."""
    tools = build_tool_list()
    logger.debug(f"Listing {len(tools)} tools")
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch tool calls to appropriate handlers."""
    logger.info(f"[TOOL_CALL] {name}")

    try:
        from mcp_server.tool_handlers import TOOL_DISPATCH

        handler = TOOL_DISPATCH.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")

        # Extract output_format BEFORE dispatch so handlers never receive the
        # key (all current handlers ignore it, but future ones might not) (#36).
        from search.config import get_search_config

        config = get_search_config()
        default_format = config.output.format

        output_format = (
            arguments.pop("output_format", default_format)
            if isinstance(arguments, dict)
            else default_format
        )

        # Call handler (arguments dict no longer contains output_format)
        result = await handler(arguments)
        formatted_result = (
            format_response(result, output_format)
            if isinstance(result, dict)
            else result
        )

        # Use compact JSON (no indent) for compact/toon formats, verbose for json format
        if output_format in ("compact", "ultra"):
            result_text = (
                json.dumps(formatted_result, separators=(",", ":"))
                if isinstance(formatted_result, dict)
                else str(formatted_result)
            )
        else:  # json format (backward compatible)
            result_text = (
                json.dumps(formatted_result, indent=2)
                if isinstance(formatted_result, dict)
                else str(formatted_result)
            )

        # Return both content (backward compat) and structuredContent (native JSON, no double encoding)
        # MCP SDK 1.25.0+ supports structuredContent - clients can choose which to read
        from mcp import types as mcp_types

        # pyrefly: ignore [bad-return]
        return mcp_types.CallToolResult(
            content=[TextContent(type="text", text=result_text)],
            structuredContent=formatted_result
            if isinstance(formatted_result, dict)
            else None,
        )

    except asyncio.CancelledError:
        # Don't catch CancelledError - let it propagate for proper cleanup
        logger.info(f"[TOOL_CANCELLED] {name} was cancelled by client")
        raise
    except Exception as e:
        logger.error(f"[TOOL_ERROR] {name}: {e}", exc_info=True)
        error_response = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


# ============================================================================
# RESOURCE HANDLERS
# ============================================================================


@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List all available resources."""
    return [
        Resource(
            uri="search://stats",
            name="Search Statistics",
            description="Detailed search index statistics",
            mimeType="application/json",
        )
    ]


# pyrefly: ignore [bad-argument-type]
@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a resource by URI."""
    logger.info(f"[RESOURCE_READ] {uri}")

    if uri == "search://stats":
        try:
            index_manager = get_index_manager()
            stats = index_manager.get_stats()
            return json.dumps(stats, indent=2)
        except Exception as e:
            error = {"error": f"Failed to get statistics: {str(e)}"}
            return json.dumps(error, indent=2)
    else:
        error = {"error": f"Unknown resource URI: {uri}"}
        return json.dumps(error, indent=2)


# ============================================================================
# PROMPT HANDLERS
# ============================================================================


@server.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """List all available prompts."""
    return [
        Prompt(
            name="search_help",
            description="Get help on how to use the code search tools effectively",
            arguments=[],
        )
    ]


# pyrefly: ignore [bad-argument-type]
@server.get_prompt()
async def handle_get_prompt(name: str, arguments: dict[str, str]) -> GetPromptResult:
    """Get a prompt by name."""
    logger.info(f"[PROMPT_GET] {name}")

    if name == "search_help":
        help_text = """# Code Search Tool Help

This tool provides semantic search capabilities for codebases using AI embeddings.

## Quick Start

1. Index your project:
   ```
   index_directory("/path/to/project")
   ```

2. Search for code:
   ```
   search_code("authentication functions", k=10)
   ```

## Available Tools

- **search_code**: Natural language code search
- **index_directory**: Index a project for search
- **find_similar_code**: Find similar code to a reference chunk
- **get_index_status**: Check index statistics

## Search Tips

1. Use natural language descriptions
2. Include technical terms for better results
3. Use filters (file_pattern, chunk_type) to narrow results

For more information, see the project documentation.
"""
        return GetPromptResult(
            description="Help documentation for code search tools",
            messages=[
                PromptMessage(
                    role="user", content=TextContent(type="text", text=help_text)
                )
            ],
        )
    else:
        raise ValueError(f"Unknown prompt: {name}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Code Search MCP Server (Low-Level SDK)"
    )
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Enable MCP debug logging
    logging.getLogger("mcp").setLevel(logging.DEBUG)
    logging.getLogger("mcp.server").setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("MCP Server Starting (Low-Level SDK)")
    logger.info("=" * 60)
    if debug_mode:
        # pyrefly: ignore [unknown-name]
        global _startup_time
        _startup_time = time.perf_counter()
        logger.info(f"[DEBUG] Startup timer started at {time.strftime('%H:%M:%S')}")
    logger.info(f"Transport: {args.transport}")
    if args.transport == "http":
        logger.info(f"HTTP endpoint: http://{args.host}:{args.port}/mcp")

    try:
        if args.transport == "stdio":
            from mcp.server.stdio import stdio_server

            async def run_stdio_server() -> None:
                """Run stdio server with proper lifecycle management."""
                # Initialize global state BEFORE starting server
                logger.info("=" * 60)
                logger.info("SERVER STARTUP: Initializing global state")
                logger.info("=" * 60)

                # Use shared initialization logic from resource_manager
                initialize_server_state()

                logger.info("=" * 60)
                logger.info("SERVER READY - Accepting connections")
                if debug_mode:
                    startup_duration = time.perf_counter() - _startup_time
                    logger.info(
                        f"[DEBUG] Startup completed in {startup_duration:.2f} seconds"
                    )
                logger.info("=" * 60)

                # Run server using stdio transport (OFFICIAL MCP SDK PATTERN)
                async with stdio_server() as (read_stream, write_stream):
                    await server.run(
                        read_stream,
                        write_stream,
                        server.create_initialization_options(),
                    )

                # Cleanup after server stops
                logger.info("=" * 60)
                logger.info("SERVER SHUTDOWN: Cleaning up")
                logger.info("=" * 60)
                _cleanup_previous_resources()
                logger.info("[SHUTDOWN] Cleanup complete")

            # Run the async function
            asyncio.run(run_stdio_server())
        elif args.transport == "http":
            # StreamableHTTP transport using Starlette + StreamableHTTPSessionManager + uvicorn
            import uvicorn
            from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
            from starlette.applications import Starlette
            from starlette.responses import JSONResponse
            from starlette.routing import Route

            # Create StreamableHTTP session manager (stateless: one transport per request,
            # no mcp-session-id bookkeeping; json_response: plain JSON body, no SSE framing)
            session_manager = StreamableHTTPSessionManager(
                app=server,
                event_store=None,
                json_response=True,
                stateless=True,
            )

            # ASGI adapter — session_manager.handle_request requires run() task group
            async def handle_mcp(scope: Any, receive: Any, send: Any) -> None:
                await session_manager.handle_request(scope, receive, send)

            # Cleanup endpoint - trigger resource cleanup via HTTP
            async def handle_cleanup(request: Any) -> JSONResponse:
                """HTTP endpoint to trigger resource cleanup.

                Releases GPU memory and cached resources in the running server process.
                """

                try:
                    logger.info(
                        "[HTTP CLEANUP] Resource cleanup requested via /cleanup endpoint"
                    )
                    # _cleanup_previous_resources() blocks (gc, CUDA ops, sleep) —
                    # offload so the uvicorn event loop stays responsive.
                    await asyncio.to_thread(_cleanup_previous_resources)
                    logger.info("[HTTP CLEANUP] Resources cleaned up successfully")
                    return JSONResponse(
                        {
                            "success": True,
                            "message": "Resources cleaned up successfully",
                        }
                    )
                except Exception as e:
                    logger.error(f"[HTTP CLEANUP] Cleanup failed: {e}", exc_info=True)
                    return JSONResponse(
                        {"success": False, "error": str(e)}, status_code=500
                    )

            # Config reload endpoint - reload search_config.json
            async def handle_reload_config(request: Any) -> JSONResponse:
                """HTTP endpoint to reload config from search_config.json.

                Allows UI config changes to sync with running server.
                """
                try:
                    logger.info("[HTTP CONFIG] Config reload requested")

                    # Reload config from file
                    from search.config import SearchConfigManager

                    config_manager = SearchConfigManager()
                    config_manager.load_config()  # Re-reads search_config.json

                    # Get updated values for response
                    # pyrefly: ignore [missing-attribute]
                    config = config_manager.config

                    logger.info(
                        f"[HTTP CONFIG] Reloaded: mode={config.search_mode.default_mode}, "
                        f"entity_tracking={config.performance.enable_entity_tracking}"
                    )

                    return JSONResponse(
                        {
                            "success": True,
                            "config": {
                                "search_mode": config.search_mode.default_mode,
                                "bm25_weight": config.search_mode.bm25_weight,
                                "dense_weight": config.search_mode.dense_weight,
                                "entity_tracking": config.performance.enable_entity_tracking,
                                "reranker_enabled": config.reranker.enabled,
                            },
                        }
                    )
                except Exception as e:
                    logger.error(f"[HTTP CONFIG] Reload failed: {e}", exc_info=True)
                    return JSONResponse({"error": str(e)}, status_code=500)

            # Project switch endpoint - switch active project
            async def handle_switch_project_http(request: Any) -> JSONResponse:
                """HTTP endpoint for UI project switching.

                Allows UI project switch to sync with running server.
                """
                try:
                    body = await request.json()
                    project_path = body.get("project_path")

                    if not project_path:
                        return JSONResponse(
                            {"error": "project_path required"}, status_code=400
                        )

                    logger.info(
                        f"[HTTP SWITCH] Project switch requested: {project_path}"
                    )

                    from mcp_server.tools.config_handlers import handle_switch_project

                    result = await handle_switch_project({"project_path": project_path})

                    logger.info(
                        f"[HTTP SWITCH] Switch complete: {result.get('project')}"
                    )
                    return JSONResponse(result)

                except Exception as e:
                    logger.error(f"[HTTP SWITCH] Failed: {e}", exc_info=True)
                    return JSONResponse({"error": str(e)}, status_code=500)

            # Starlette app with lifespan integration
            async def app_lifespan(app: Any) -> AsyncGenerator[None, None]:
                """Application lifecycle - initialize global state ONCE before accepting connections."""
                logger.info("=" * 60)
                logger.info("APPLICATION STARTUP: Initializing global state")
                logger.info("=" * 60)

                try:
                    # Use shared initialization logic from resource_manager
                    initialize_server_state()

                    # Optional: Pre-load embedding model
                    # Default: true for HTTP mode (long-running servers benefit from pre-warming)
                    if os.getenv("MCP_PRELOAD_MODEL", "true").lower() in (
                        "true",
                        "1",
                        "yes",
                    ):
                        logger.info("[INIT] Pre-loading embedding model...")
                        try:
                            embedder = get_embedder()
                            _ = embedder.model
                            logger.info("[INIT] Embedding model pre-loaded")
                        except Exception as e:
                            logger.warning(
                                f"[INIT] Model pre-load failed (non-critical): {e}"
                            )

                    logger.info("=" * 60)
                    logger.info("APPLICATION READY - Accepting connections")
                    if debug_mode:
                        startup_duration = time.perf_counter() - _startup_time
                        logger.info(
                            f"[DEBUG] Startup completed in {startup_duration:.2f} seconds"
                        )
                    logger.info("=" * 60)

                    # Suppress noisy ASGI errors for disconnected clients
                    # (secondary errors after BrokenResourceError)
                    logging.getLogger("uvicorn.error").addFilter(
                        lambda record: (
                            "Unexpected ASGI message" not in record.getMessage()
                        )
                    )

                    # session_manager.run() creates the task group required by handle_request
                    async with session_manager.run():
                        yield  # Application runs

                finally:
                    logger.info("=" * 60)
                    logger.info("APPLICATION SHUTDOWN: Cleaning up")
                    logger.info("=" * 60)
                    _cleanup_previous_resources()
                    logger.info("[SHUTDOWN] Cleanup complete")

            # Define routes: POST /cleanup + POST /reload_config + POST /switch_project
            # NOTE: /mcp is intentionally NOT in the Starlette routes list.
            # Mount("/mcp", ...) causes Starlette's redirect_slashes Router logic to
            # issue a 307 on exact "POST /mcp" (no trailing slash), because the Mount
            # regex /mcp/{path:path} requires trailing content. We bypass this by
            # intercepting /mcp at the ASGI level in asgi_app below.
            routes = [
                Route("/cleanup", endpoint=handle_cleanup, methods=["POST"]),
                Route(
                    "/reload_config", endpoint=handle_reload_config, methods=["POST"]
                ),
                Route(
                    "/switch_project",
                    endpoint=handle_switch_project_http,
                    methods=["POST"],
                ),
            ]

            # pyrefly: ignore [bad-argument-type]
            starlette_app = Starlette(routes=routes, lifespan=app_lifespan)

            # Top-level ASGI app: routes /mcp directly to StreamableHTTP before
            # Starlette routing sees it (avoids the 307 redirect described above).
            # Lifespan events fall through to starlette_app which owns the context.
            async def asgi_app(scope: Any, receive: Any, send: Any) -> None:
                if scope.get("type") == "http":
                    path = scope.get("path", "")
                    if path == "/mcp" or path.startswith("/mcp/"):
                        await handle_mcp(scope, receive, send)
                        return
                await starlette_app(scope, receive, send)

            # Run server with Windows-specific event loop handling
            logger.info(f"Starting HTTP server on {args.host}:{args.port}")
            logger.info(f"HTTP endpoint: http://{args.host}:{args.port}/mcp")
            logger.info(f"Cleanup endpoint: http://{args.host}:{args.port}/cleanup")
            logger.info(
                f"Config reload endpoint: http://{args.host}:{args.port}/reload_config"
            )
            logger.info(
                f"Project switch endpoint: http://{args.host}:{args.port}/switch_project"
            )

            # Uvicorn config (explicit asyncio loop, not uvloop)
            config = uvicorn.Config(
                asgi_app,
                host=args.host,
                port=args.port,
                timeout_keep_alive=120,  # 2 minutes (default: 5s)
                log_level="info",
                loop="asyncio",  # Force asyncio (fixes uvicorn 0.36+ regression)
            )
            uvi_server = uvicorn.Server(config)

            # Windows: Use SelectorEventLoop to prevent WinError 64
            # (uvicorn 0.36+ ignores asyncio.set_event_loop_policy when using uvicorn.run)
            if platform.system() == "Windows":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                # Set exception handler for residual socket errors
                def handle_win_socket_error(loop: Any, context: dict[str, Any]) -> None:
                    exc = context.get("exception")
                    # Swallow common transient SSE-disconnect codes; these are
                    # normal client disconnects, not server faults.
                    _transient_winerrors = {
                        64,  # The specified network name is no longer available
                        995,  # Operation aborted
                        10053,  # Connection aborted by software
                        10054,  # Connection reset by peer
                    }
                    if (
                        isinstance(exc, OSError)
                        and getattr(exc, "winerror", None) in _transient_winerrors
                    ):
                        logger.debug(
                            f"Client disconnect (WinError {exc.winerror}): {context.get('message', '')}"
                        )
                        return
                    # Handle anyio stream errors (client disconnections)
                    if isinstance(
                        exc, (anyio.BrokenResourceError, anyio.ClosedResourceError)
                    ):
                        logger.debug(f"HTTP stream closed: {exc}")
                        return
                    loop.default_exception_handler(context)

                loop.set_exception_handler(handle_win_socket_error)

                logger.info(
                    "Windows: Using SelectorEventLoop for HTTP (uvicorn 0.36+ fix)"
                )
                try:
                    loop.run_until_complete(uvi_server.serve())
                finally:
                    loop.close()
            else:
                asyncio.run(uvi_server.serve())

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
