"""Low-level MCP server for Claude Code integration.

AUTO-GENERATED from FastMCP backup.
DO NOT EDIT MANUALLY - regenerate with tools/build_lowlevel_server.py

Migrated from FastMCP to official MCP SDK for:
- Explicit lifecycle management
- Predictable state initialization
- Better production reliability
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

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

# Configure logging
debug_mode = os.getenv("MCP_DEBUG", "").lower() in ("1", "true", "yes")
log_level = logging.DEBUG if debug_mode else logging.INFO
log_format = (
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if debug_mode
    else "%(asctime)s - %(message)s"
)
logging.basicConfig(level=log_level, format=log_format, datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

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
async def handle_list_tools() -> List[Tool]:
    """List all available tools."""
    tools = build_tool_list()
    logger.debug(f"Listing {len(tools)} tools")
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls to appropriate handlers."""
    logger.info(f"[TOOL_CALL] {name}")

    try:
        # Import tool handler module
        from mcp_server import tool_handlers

        # Get handler function
        handler_name = f"handle_{name}"
        if not hasattr(tool_handlers, handler_name):
            raise ValueError(f"Unknown tool: {name}")

        handler = getattr(tool_handlers, handler_name)

        # Call handler
        result = await handler(arguments)

        # Apply output formatting (formatting-only, preserves all data)
        # Use config default if no format specified
        from search.config import get_search_config

        config = get_search_config()
        default_format = config.output.format

        output_format = (
            arguments.pop("output_format", default_format)
            if isinstance(arguments, dict)
            else default_format
        )
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

        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"[TOOL_ERROR] {name}: {e}", exc_info=True)
        error_response = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


# ============================================================================
# RESOURCE HANDLERS
# ============================================================================


@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List all available resources."""
    return [
        Resource(
            uri="search://stats",
            name="Search Statistics",
            description="Detailed search index statistics",
            mimeType="application/json",
        )
    ]


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
async def handle_list_prompts() -> List[Prompt]:
    """List all available prompts."""
    return [
        Prompt(
            name="search_help",
            description="Get help on how to use the code search tools effectively",
            arguments=[],
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
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
    import argparse

    parser = argparse.ArgumentParser(
        description="Code Search MCP Server (Low-Level SDK)"
    )
    parser.add_argument("--transport", choices=["stdio", "sse"], default="stdio")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    # Enable MCP debug logging
    import logging

    logging.getLogger("mcp").setLevel(logging.DEBUG)
    logging.getLogger("mcp.server").setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("MCP Server Starting (Low-Level SDK)")
    logger.info("=" * 60)
    logger.info(f"Transport: {args.transport}")
    if args.transport == "sse":
        logger.info(f"SSE endpoint: http://{args.host}:{args.port}")

    try:
        if args.transport == "stdio":
            from mcp.server.stdio import stdio_server

            async def run_stdio_server():
                """Run stdio server with proper lifecycle management."""
                # Initialize global state BEFORE starting server
                logger.info("=" * 60)
                logger.info("SERVER STARTUP: Initializing global state")
                logger.info("=" * 60)

                # Use shared initialization logic from resource_manager
                initialize_server_state()

                logger.info("=" * 60)
                logger.info("SERVER READY - Accepting connections")
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
        elif args.transport == "sse":
            # SSE transport using Starlette + SseServerTransport + uvicorn
            import platform

            import uvicorn
            from mcp.server.sse import SseServerTransport
            from starlette.applications import Starlette
            from starlette.responses import Response
            from starlette.routing import Mount, Route

            # Create SSE transport with message endpoint
            sse = SseServerTransport("/messages/")

            # SSE handler - establishes bidirectional streams
            async def handle_sse(request):
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    await server.run(
                        streams[0],  # read_stream
                        streams[1],  # write_stream
                        server.create_initialization_options(),
                    )
                return Response()  # Prevent TypeError on disconnect

            # Cleanup endpoint - trigger resource cleanup via HTTP
            async def handle_cleanup(request):
                """HTTP endpoint to trigger resource cleanup.

                Releases GPU memory and cached resources in the running server process.
                """
                from starlette.responses import JSONResponse

                try:
                    logger.info(
                        "[HTTP CLEANUP] Resource cleanup requested via /cleanup endpoint"
                    )
                    _cleanup_previous_resources()
                    logger.info("[HTTP CLEANUP] Resources cleaned up successfully")
                    return JSONResponse(
                        {
                            "success": True,
                            "message": "Resources cleaned up successfully",
                        }
                    )
                except Exception as e:
                    logger.error(f"[HTTP CLEANUP] Cleanup failed: {e}")
                    return JSONResponse(
                        {"success": False, "error": str(e)}, status_code=500
                    )

            # Starlette app with lifespan integration
            async def app_lifespan(app):
                """Application lifecycle - initialize global state ONCE before accepting connections."""
                logger.info("=" * 60)
                logger.info("APPLICATION STARTUP: Initializing global state")
                logger.info("=" * 60)

                try:
                    # Use shared initialization logic from resource_manager
                    initialize_server_state()

                    # Optional: Pre-load embedding model (SSE-specific feature)
                    if os.getenv("MCP_PRELOAD_MODEL", "false").lower() in (
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
                    logger.info("=" * 60)

                    yield  # Application runs

                finally:
                    logger.info("=" * 60)
                    logger.info("APPLICATION SHUTDOWN: Cleaning up")
                    logger.info("=" * 60)
                    _cleanup_previous_resources()
                    logger.info("[SHUTDOWN] Cleanup complete")

            # Define routes: GET /sse + POST /messages/ + POST /cleanup
            routes = [
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Route("/cleanup", endpoint=handle_cleanup, methods=["POST"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]

            starlette_app = Starlette(routes=routes, lifespan=app_lifespan)

            # Run server with Windows-specific event loop handling
            logger.info(f"Starting SSE server on {args.host}:{args.port}")
            logger.info(f"SSE endpoint: http://{args.host}:{args.port}/sse")
            logger.info(f"Message endpoint: http://{args.host}:{args.port}/messages/")
            logger.info(f"Cleanup endpoint: http://{args.host}:{args.port}/cleanup")

            # Uvicorn config (explicit asyncio loop, not uvloop)
            config = uvicorn.Config(
                starlette_app,
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
                def handle_win_socket_error(loop, context):
                    exc = context.get("exception")
                    if (
                        isinstance(exc, OSError)
                        and getattr(exc, "winerror", None) == 64
                    ):
                        logger.debug(
                            f"Client disconnect (WinError 64): {context.get('message', '')}"
                        )
                        return
                    loop.default_exception_handler(context)

                loop.set_exception_handler(handle_win_socket_error)

                logger.info(
                    "Windows: Using SelectorEventLoop for SSE (uvicorn 0.36+ fix)"
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
