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
    initialize_model_pool,
)
from mcp_server.project_persistence import (  # noqa: E402
    load_project_selection,
)
from mcp_server.services import get_config, get_state  # noqa: E402
from mcp_server.storage_manager import (  # noqa: E402
    get_project_storage_dir,
    get_storage_dir,
    set_current_project,
)
from search.config import MODEL_POOL_CONFIG  # noqa: E402
from search.hybrid_searcher import HybridSearcher  # noqa: E402
from search.indexer import CodeIndexManager  # noqa: E402
from search.searcher import IntelligentSearcher  # noqa: E402

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
# HELPER FUNCTIONS (copied from FastMCP backup)
# ============================================================================


def _cleanup_previous_resources():
    """Cleanup previous project resources to free memory."""
    state = get_state()
    try:
        if state.index_manager is not None:
            if (
                hasattr(state.index_manager, "_metadata_db")
                and state.index_manager._metadata_db is not None
            ):
                state.index_manager._metadata_db.close()
            state.index_manager = None
            logger.info("Previous index manager cleaned up")

        if state.searcher is not None:
            if hasattr(state.searcher, "shutdown"):
                state.searcher.shutdown()
                logger.info("Searcher shutdown completed (neural reranker released)")
            state.searcher = None
            logger.info("Previous searcher cleaned up")

        # Clear embedder pool to free GPU memory (explicit user request)
        if state.embedders:
            embedder_count = len(state.embedders)
            logger.info(
                f"Clearing {embedder_count} cached embedder(s): {list(state.embedders.keys())}"
            )
            state.clear_embedders()
            logger.info("Embedder pool cleared - VRAM released")

        # Force garbage collection to immediately free GPU memory
        import gc

        gc.collect()
        logger.info("Garbage collection completed")

        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("GPU cache cleared")
        except ImportError as e:
            logger.debug(f"GPU cache cleanup skipped: {e}")
    except (AttributeError, TypeError) as e:
        logger.warning(f"Error during resource cleanup: {e}")


def close_project_resources(project_path: str) -> bool:
    """Close all resources associated with a specific project.

    This function ensures all database connections and file handles
    are released before project deletion. It's designed to be called
    before deleting a project directory to prevent file lock errors.

    Args:
        project_path: Absolute path to the project directory

    Returns:
        True if cleanup successful
    """
    import gc
    import time
    from pathlib import Path

    state = get_state()
    project_path_resolved = str(Path(project_path).resolve())

    # If this is the current project, clean up state
    if state.current_project == project_path_resolved:
        _cleanup_previous_resources()
        state.current_project = None
        logger.info(f"Cleaned up resources for current project: {project_path}")
    else:
        logger.debug(
            f"Project not current, no active resources to clean: {project_path}"
        )

    # Force garbage collection to release any lingering handles
    gc.collect()

    # Small delay to allow OS to release file handles (especially on Windows)
    time.sleep(0.3)

    return True


def get_index_manager(
    project_path: str = None, model_key: str = None
) -> CodeIndexManager:
    """Get index manager for specific project or current project.

    Args:
        project_path: Path to the project (None = use current project)
        model_key: Model key for routing (None = use config default)
    """
    state = get_state()

    if project_path is None:
        if state.current_project is None:
            raise ValueError(
                "No indexed project found. Please run index_directory first."
            )
        else:
            project_path = state.current_project

    # Invalidate cache if project or model changed
    if (
        state.current_project != project_path
        or state.current_index_model_key != model_key
    ):
        if state.current_project != project_path:
            logger.info(
                f"Switching project from '{state.current_project}' to '{Path(project_path).name}'"
            )
        if state.current_index_model_key != model_key:
            logger.info(
                f"Switching index model from '{state.current_index_model_key}' to '{model_key}'"
            )
        _cleanup_previous_resources()

        state.current_project = project_path
        state.current_index_model_key = model_key
        state.index_manager = None

    if state.index_manager is None:
        project_dir = get_project_storage_dir(project_path, model_key=model_key)
        index_dir = project_dir / "index"
        index_dir.mkdir(exist_ok=True)

        # Extract project_id from storage directory name
        # Format: projectname_hash_modelslug_dimension (e.g., claude-context-local_caf2e75a_qwen3_1024d)
        project_id = project_dir.name.rsplit("_", 1)[0]  # Remove dimension suffix

        state.index_manager = CodeIndexManager(str(index_dir), project_id=project_id)
        logger.info(
            f"Index manager initialized for project: {Path(project_path).name} (ID: {project_id}, model_key: {model_key})"
        )

    return state.index_manager


def get_searcher(project_path: str = None, model_key: str = None):
    """Get searcher for specific project or current project.

    Args:
        project_path: Path to project (None = use current project)
        model_key: Model key for routing (None = preserve current model,
                   or use config default if no current model)
    """
    state = get_state()

    if project_path is None and state.current_project is None:
        project_path = str(PROJECT_ROOT)
        logger.info(f"No active project found. Using server directory: {project_path}")

    # Use effective model key: passed value OR current value (preserve routing)
    effective_model_key = (
        model_key if model_key is not None else state.current_model_key
    )

    # Invalidate cache if project or model changed
    if (
        state.current_project != project_path
        or state.current_model_key != effective_model_key
        or state.searcher is None
    ):
        state.current_project = project_path or state.current_project
        state.current_model_key = effective_model_key
        config = get_config()
        logger.info(
            f"[GET_SEARCHER] Initializing searcher for project: {state.current_project}"
        )
        if config.search_mode.enable_hybrid:
            project_storage = get_project_storage_dir(
                state.current_project, model_key=effective_model_key
            )
            storage_dir = project_storage / "index"
            logger.info(f"[GET_SEARCHER] Using storage directory: {storage_dir}")

            # Extract project_id from storage directory name
            # Format: projectname_hash_dimension (e.g., claude-context-local_caf2e75a_1024d)
            project_id = project_storage.name.rsplit("_", 1)[
                0
            ]  # Remove dimension suffix

            state.searcher = HybridSearcher(
                storage_dir=str(storage_dir),
                embedder=get_embedder(effective_model_key),
                bm25_weight=config.search_mode.bm25_weight,
                dense_weight=config.search_mode.dense_weight,
                rrf_k=config.search_mode.rrf_k_parameter,
                max_workers=2,
                project_id=project_id,
            )
            # REMOVED: get_index_manager() call that was causing state corruption
            # The HybridSearcher already loads existing indices during initialization
            logger.info(
                f"HybridSearcher initialized (BM25: {config.search_mode.bm25_weight}, Dense: {config.search_mode.dense_weight})"
            )
        else:
            state.searcher = IntelligentSearcher(
                get_index_manager(project_path, model_key=effective_model_key),
                get_embedder(effective_model_key),
            )
            logger.info("IntelligentSearcher initialized (semantic-only mode)")

        logger.info(
            f"Searcher initialized for project: {Path(state.current_project).name if state.current_project else 'unknown'}"
        )

    return state.searcher


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

        # Convert to TextContent
        result_text = (
            json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
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

    # Windows SSE fix
    if args.transport == "sse":
        import platform

        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Windows: Using SelectorEventLoop for SSE")

    try:
        if args.transport == "stdio":
            from mcp.server.stdio import stdio_server

            async def run_stdio_server():
                """Run stdio server with proper lifecycle management."""
                state = get_state()

                # Sync multi_model_enabled from config file (with env override)
                from search.config import get_config_manager

                try:
                    config_manager = get_config_manager()
                    config = config_manager.load_config()
                    state.sync_from_config(config)
                except Exception as e:
                    logger.warning(f"[INIT] Config sync failed (using defaults): {e}")

                # Initialize global state BEFORE starting server
                logger.info("=" * 60)
                logger.info("SERVER STARTUP: Initializing global state")
                logger.info("=" * 60)

                # Set default project: env var > persistent selection > none
                default_project = os.getenv("CLAUDE_DEFAULT_PROJECT", None)
                if default_project:
                    project_path = str(Path(default_project).resolve())
                    state.current_project = project_path
                    logger.info(f"[INIT] Default project (env): {project_path}")
                else:
                    # Try to restore from persistent selection
                    selection = load_project_selection()
                    if selection:
                        restored_path = selection["last_project_path"]
                        set_current_project(restored_path)
                        logger.info(
                            f"[INIT] Restored project: {Path(restored_path).name}"
                        )
                    else:
                        logger.info("[INIT] No default project")

                # Defer model pool initialization
                # Models will load on first search/index operation (saves 3-4GB VRAM at startup)
                # if state.multi_model_enabled and not state.model_preload_task_started:
                #     initialize_model_pool(lazy_load=True)
                #     logger.info(
                #         f"[INIT] Model pool initialized: {list(MODEL_POOL_CONFIG.keys())}"
                #     )
                #     state.model_preload_task_started = True
                logger.info("[INIT] Model loading deferred until first use (lazy mode)")
                logger.info(
                    f"[INIT] Available models: {list(MODEL_POOL_CONFIG.keys())}"
                )

                # Log storage directory
                storage = get_storage_dir()
                logger.info(f"[INIT] Storage directory: {storage}")

                # Process deferred cleanup queue on startup
                from mcp_server.cleanup_queue import CleanupQueue

                cleanup_queue = CleanupQueue()
                result = cleanup_queue.process()
                if result["processed"] > 0:
                    logger.info(
                        f"[INIT] Processed {result['processed']} deferred cleanup tasks"
                    )
                if result["failed"]:
                    logger.warning(
                        f"[INIT] Cleanup failed for {len(result['failed'])} items (will retry later)"
                    )

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

            # Starlette app with lifespan integration
            async def app_lifespan(app):
                """Application lifecycle - initialize global state ONCE before accepting connections."""
                state = get_state()

                # Sync multi_model_enabled from config file (with env override)
                from search.config import get_config_manager

                try:
                    config_manager = get_config_manager()
                    config = config_manager.load_config()
                    state.sync_from_config(config)
                except Exception as e:
                    logger.warning(f"[INIT] Config sync failed (using defaults): {e}")

                logger.info("=" * 60)
                logger.info("APPLICATION STARTUP: Initializing global state")
                logger.info("=" * 60)

                try:
                    # Set default project: env var > persistent selection > none
                    default_project = os.getenv("CLAUDE_DEFAULT_PROJECT", None)
                    if default_project:
                        project_path = str(Path(default_project).resolve())
                        state.current_project = project_path
                        logger.info(f"[INIT] Default project (env): {project_path}")
                    else:
                        # Try to restore from persistent selection
                        selection = load_project_selection()
                        if selection:
                            restored_path = selection["last_project_path"]
                            set_current_project(restored_path)
                            logger.info(
                                f"[INIT] Restored project: {Path(restored_path).name}"
                            )
                        else:
                            logger.info("[INIT] No default project")

                    # Initialize model pool in lazy mode
                    if (
                        state.multi_model_enabled
                        and not state.model_preload_task_started
                    ):
                        initialize_model_pool(lazy_load=True)
                        logger.info(
                            f"[INIT] Model pool initialized: {list(MODEL_POOL_CONFIG.keys())}"
                        )
                        state.model_preload_task_started = True
                    elif state.multi_model_enabled:
                        logger.info("[INIT] Model pool already initialized")
                    else:
                        logger.info("[INIT] Single-model mode enabled")

                    # Log storage directory
                    storage = get_storage_dir()
                    logger.info(f"[INIT] Storage directory: {storage}")

                    # Process deferred cleanup queue on startup
                    from mcp_server.cleanup_queue import CleanupQueue

                    cleanup_queue = CleanupQueue()
                    result = cleanup_queue.process()
                    if result["processed"] > 0:
                        logger.info(
                            f"[INIT] Processed {result['processed']} deferred cleanup tasks"
                        )
                    if result["failed"]:
                        logger.warning(
                            f"[INIT] Cleanup failed for {len(result['failed'])} items (will retry later)"
                        )

                    # Optional: Pre-load embedding model
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

            # Define routes: GET /sse + POST /messages/
            routes = [
                Route("/sse", endpoint=handle_sse, methods=["GET"]),
                Mount("/messages/", app=sse.handle_post_message),
            ]

            starlette_app = Starlette(routes=routes, lifespan=app_lifespan)

            # Run server
            logger.info(f"Starting SSE server on {args.host}:{args.port}")
            logger.info(f"SSE endpoint: http://{args.host}:{args.port}/sse")
            logger.info(f"Message endpoint: http://{args.host}:{args.port}/messages/")

            # Increase keep-alive timeout to handle long-running operations (indexing)
            uvicorn.run(
                starlette_app,
                host=args.host,
                port=args.port,
                timeout_keep_alive=120,  # 2 minutes (default: 5s)
                log_level="info",
            )

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)
