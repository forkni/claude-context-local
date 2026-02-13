import asyncio
import json
import os
import sys
from pathlib import Path


# Add project root to path so we can import mcp_server modules
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Import MCP Server internals
try:
    from mcp_server.resource_manager import initialize_server_state
    from mcp_server.tools.config_handlers import handle_switch_project
    from mcp_server.tools.graph_handlers import (
        handle_find_connections,
        handle_find_path,
        handle_get_graph_stats,
    )
    from mcp_server.tools.search_handlers import handle_search_code
except ImportError as e:
    print(f"Error importing MCP modules: {e}")
    print(f"Sys Path: {sys.path}")
    sys.exit(1)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python antigravity_bridge.py <command> [args...]")
        print("Commands: search, connections, path, stats")
        sys.exit(1)

    command = sys.argv[1]

    # Initialize global state (database connections, etc.)
    initialize_server_state()

    # Ensure we are in the correct project context
    # We assume the current working directory is the project root or we can derive it
    # For now, let's just use the current directory as the project
    cwd = os.getcwd()
    await handle_switch_project({"project_path": cwd})

    result = None

    try:
        if command == "search":
            if len(sys.argv) < 3:
                print("Usage: python antigravity_bridge.py search <query>")
                sys.exit(1)
            query = " ".join(sys.argv[2:])
            print(f"Running Search: {query}...")
            # Default to k=5 for the agent
            result = await handle_search_code({"query": query, "k": 5})

        elif command == "connections":
            if len(sys.argv) < 3:
                print("Usage: python antigravity_bridge.py connections <chunk_id>")
                sys.exit(1)
            chunk_id = sys.argv[2]
            print(f"Finding Connections: {chunk_id}...")
            result = await handle_find_connections({"target": chunk_id, "distance": 1})

        elif command == "path":
            if len(sys.argv) < 4:
                print(
                    "Usage: python antigravity_bridge.py path <source_id> <target_id>"
                )
                sys.exit(1)
            source = sys.argv[2]
            target = sys.argv[3]
            print(f"Finding Path: {source} -> {target}...")
            result = await handle_find_path({"source": source, "target": target})

        elif command == "stats":
            print("Fetching Graph Stats...")
            result = await handle_get_graph_stats({})

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

        # Output result as JSON for the agent to parse
        print("\n--- RESULT ---")
        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"\nError executing command: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    import asyncio

    # Fix for Windows asyncio loop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
