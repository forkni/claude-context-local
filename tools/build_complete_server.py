"""Build complete low-level MCP server with all tool handlers.

This script generates the full server implementation by:
1. Reading helper functions from current server_lowlevel.py
2. Extracting tool implementations from FastMCP backup
3. Converting @mcp.tool() functions to async handlers
4. Adding server handlers and main entry point
"""

import re
from pathlib import Path

BACKUP_PATH = Path(__file__).parent.parent / 'mcp_server' / 'server_fastmcp_backup.py'
CURRENT_SERVER = Path(__file__).parent.parent / 'mcp_server' / 'server_lowlevel.py'
OUTPUT_PATH = Path(__file__).parent.parent / 'mcp_server' / 'server_lowlevel_complete.py'

def extract_tool_function(backup_content, tool_name):
    """Extract complete tool function from backup."""
    # Find @mcp.tool() followed by the function
    pattern = rf'@mcp\.tool\(\)\s*\ndef {tool_name}\((.*?)\n(?=\n@mcp\.|if __name__|$)'
    match = re.search(pattern, backup_content, re.DOTALL)

    if match:
        full_function = f"def {tool_name}({match.group(1)}"
        return full_function
    return None

def convert_to_async_handler(tool_function, tool_name):
    """Convert sync function to async handler."""
    # Simple conversion: change def to async def, rename function
    handler_name = f"handle_{tool_name}"
    async_func = tool_function.replace(f"def {tool_name}(", f"async def {handler_name}(arguments: Dict[str, Any]) -> dict:")

    # Extract parameters for argument unpacking
    # This is a simplified version - full implementation would parse AST
    return async_func

print("Building complete server...")
print("Step 1: Reading backup...")

with open(BACKUP_PATH, 'r', encoding='utf-8') as f:
    backup_content = f.read()

print("Step 2: Reading current server...")
with open(CURRENT_SERVER, 'r', encoding='utf-8') as f:
    current_server = f.read()

# Extract the helper functions section
helpers_end = current_server.find("# CRITICAL FIX: Explicit lifecycle management")
if helpers_end == -1:
    print("ERROR: Could not find lifespan section")
    exit(1)

helpers_section = current_server[:helpers_end].strip()

print("Step 3: Generating server template...")

# Build complete server
server_content = f'''{helpers_section}

# ============================================================================
# CRITICAL FIX: Explicit lifecycle management
# ============================================================================

@asynccontextmanager
async def server_lifespan(server: Server):
    """Server lifecycle management - runs BEFORE any tool calls."""
    global _current_project, _embedders, _model_preload_task_started

    logger.info("=" * 60)
    logger.info("SERVER STARTUP: Initializing global state")
    logger.info("=" * 60)

    try:
        default_project = os.getenv('CLAUDE_DEFAULT_PROJECT', None)
        if default_project:
            _current_project = str(Path(default_project).resolve())
            logger.info(f"[INIT] Default project set: {{_current_project}}")
        else:
            logger.info("[INIT] No default project")

        if _multi_model_enabled:
            initialize_model_pool(lazy_load=True)
            logger.info(f"[INIT] Model pool initialized: {{list(MODEL_POOL_CONFIG.keys())}}")
        else:
            logger.info("[INIT] Single-model mode enabled")

        storage_dir = get_storage_dir()
        logger.info(f"[INIT] Storage directory: {{storage_dir}}")

        if os.getenv('MCP_PRELOAD_MODEL', 'false').lower() in ('true', '1', 'yes'):
            logger.info("[INIT] Pre-loading embedding model...")
            try:
                embedder = get_embedder()
                _ = embedder.model
                logger.info("[INIT] Embedding model pre-loaded")
            except Exception as e:
                logger.warning(f"[INIT] Model pre-load failed (non-critical): {{e}}")

        logger.info("=" * 60)
        logger.info("[INIT] SERVER READY - State initialized, accepting connections")
        logger.info("=" * 60)

        yield

    finally:
        logger.info("=" * 60)
        logger.info("SERVER SHUTDOWN: Cleaning up resources")
        logger.info("=" * 60)
        _cleanup_previous_resources()
        logger.info("[SHUTDOWN] Cleanup complete")
        logger.info("=" * 60)


# Create server instance
server = Server("Code Search")

# Import tool registry
from mcp_server.tool_registry import TOOL_REGISTRY, build_tool_list


# ============================================================================
# SERVER HANDLERS
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List all available tools."""
    tools = build_tool_list()
    logger.debug(f"Listing {{len(tools)}} tools")
    return tools


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Dispatch tool calls to appropriate handlers."""
    logger.info(f"[TOOL_CALL] {{name}}")

    try:
        # Import tool handler module
        from mcp_server import tool_handlers

        # Get handler function
        handler_name = f"handle_{{name}}"
        if not hasattr(tool_handlers, handler_name):
            raise ValueError(f"Unknown tool: {{name}}")

        handler = getattr(tool_handlers, handler_name)

        # Call handler
        result = await handler(arguments)

        # Convert to TextContent
        result_text = json.dumps(result, indent=2) if isinstance(result, dict) else str(result)
        return [TextContent(type="text", text=result_text)]

    except Exception as e:
        logger.error(f"[TOOL_ERROR] {{name}}: {{e}}", exc_info=True)
        error_response = {{"error": str(e), "tool": name, "arguments": arguments}}
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
            mimeType="application/json"
        )
    ]


@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read a resource by URI."""
    logger.info(f"[RESOURCE_READ] {{uri}}")

    if uri == "search://stats":
        try:
            index_manager = get_index_manager()
            stats = index_manager.get_stats()
            return json.dumps(stats, indent=2)
        except Exception as e:
            error = {{"error": f"Failed to get statistics: {{str(e)}}"}}
            return json.dumps(error, indent=2)
    else:
        error = {{"error": f"Unknown resource URI: {{uri}}"}}
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
            arguments=[]
        )
    ]


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, str]) -> GetPromptResult:
    """Get a prompt by name."""
    logger.info(f"[PROMPT_GET] {{name}}")

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
                    role="user",
                    content=TextContent(type="text", text=help_text)
                )
            ]
        )
    else:
        raise ValueError(f"Unknown prompt: {{name}}")


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Code Search MCP Server (Low-Level SDK)')
    parser.add_argument('--transport', choices=['stdio', 'sse'], default='stdio')
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MCP Server Starting (Low-Level SDK)")
    logger.info("=" * 60)
    logger.info(f"Transport: {{args.transport}}")
    if args.transport == 'sse':
        logger.info(f"SSE endpoint: http://{{args.host}}:{{args.port}}")

    # Windows SSE fix
    if args.transport == 'sse':
        import platform
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Windows: Using SelectorEventLoop for SSE")

    try:
        from mcp.server.stdio import stdio_server
        from mcp.server.sse import sse_server

        if args.transport == 'stdio':
            asyncio.run(stdio_server(server, server_lifespan))
        elif args.transport == 'sse':
            asyncio.run(sse_server(server, server_lifespan, host=args.host, port=args.port))

    except KeyboardInterrupt:
        logger.info('\\nShutting down gracefully...')
        sys.exit(0)
    except Exception as e:
        logger.error(f'Server error: {{e}}', exc_info=True)
        sys.exit(1)
'''

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(server_content)

print(f"Server template written to: {OUTPUT_PATH}")
print("Next: Create tool_handlers.py module with all 14 tool implementations")
