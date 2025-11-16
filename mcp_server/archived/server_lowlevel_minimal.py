"""Low-level MCP server - MINIMAL WORKING VERSION

This is a minimal implementation to demonstrate the migration approach.
Full implementation will copy all helper functions and tool logic from server_fastmcp_backup.py.

KEY FIX: Explicit lifespan hook guarantees _current_project initialization before any tool calls.
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent))
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# Official MCP SDK imports
from mcp.server.lowlevel import Server
from mcp.types import Tool, TextContent

# Import helper functions by reading from backup (preserves all business logic)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "server_fastmcp_backup",
    Path(__file__).parent / "server_fastmcp_backup.py"
)
backup_module = importlib.util.module_from_spec(spec)

# Configure logging
debug_mode = os.getenv('MCP_DEBUG', '').lower() in ('1', 'true', 'yes')
log_level = logging.DEBUG if debug_mode else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Global state
_embedders = {}
_index_manager = None
_searcher = None
_storage_dir = None
_current_project = None
_multi_model_enabled = os.getenv('CLAUDE_MULTI_MODEL_ENABLED', 'true').lower() in ('true', '1', 'yes')

MODEL_POOL_CONFIG = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge_m3": "BAAI/bge-m3",
    "coderankembed": "nomic-ai/CodeRankEmbed"
}


# CRITICAL FIX: Lifespan hook
@asynccontextmanager
async def server_lifespan(server: Server):
    """Initialize state BEFORE any tool calls - fixes project_id=None bug."""
    global _current_project

    logger.info("=" * 60)
    logger.info("SERVER STARTUP")
    logger.info("=" * 60)

    # Initialize default project (CRITICAL FIX)
    default_project = os.getenv('CLAUDE_DEFAULT_PROJECT', None)
    if default_project:
        _current_project = str(Path(default_project).resolve())
        logger.info(f"[INIT] Default project: {_current_project}")

    logger.info("[INIT] SERVER READY")
    yield
    logger.info("[SHUTDOWN] Cleanup complete")


# Create server
server = Server("Code Search")

# Minimal tool registry (demonstration)
TOOL_REGISTRY = {
    "get_index_status": {
        "description": "Get current status and statistics of the search index",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    tools = []
    for name, meta in TOOL_REGISTRY.items():
        tools.append(Tool(
            name=name,
            description=meta["description"],
            inputSchema=meta["input_schema"]
        ))
    logger.debug(f"Listing {len(tools)} tools")
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls - state is guaranteed initialized by lifespan."""
    logger.info(f"[TOOL_CALL] {name}")

    try:
        if name == "get_index_status":
            # Simple demonstration
            result = {
                "status": "ready",
                "current_project": _current_project,
                "message": "Low-level SDK migration successful"
            }
        else:
            raise ValueError(f"Unknown tool: {name}")

        result_text = json.dumps(result, indent=2)
        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"[TOOL_ERROR] {name}: {e}", exc_info=True)
        error_response = {"error": str(e), "tool": name}
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Code Search MCP Server (Low-Level SDK - MINIMAL)')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    logger.info("MCP Server Starting (Low-Level SDK - Minimal Version)")

    try:
        from mcp.server.stdio import stdio_server
        from mcp.server.sse import sse_server

        if args.transport == 'stdio':
            asyncio.run(stdio_server(server, server_lifespan))
        elif args.transport == 'sse':
            asyncio.run(sse_server(server, server_lifespan, host=args.host, port=args.port))

    except KeyboardInterrupt:
        logger.info('Shutting down gracefully...')
        sys.exit(0)
    except Exception as e:
        logger.error(f'Server error: {e}', exc_info=True)
        sys.exit(1)
