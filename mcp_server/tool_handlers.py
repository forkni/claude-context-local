"""Tool handlers for low-level MCP server.

Re-exports all handlers from domain-specific modules and provides TOOL_DISPATCH,
an explicit name→handler map used by handle_call_tool in server.py.

TOOL_DISPATCH must stay in parity with TOOL_REGISTRY in tool_registry.py.
A unit test in tests/unit/mcp_server/test_tool_handlers.py asserts this invariant.

Direct imports from specific handler modules are also fine:
- mcp_server.tools.status_handlers
- mcp_server.tools.config_handlers
- mcp_server.tools.search_handlers
- mcp_server.tools.index_handlers
"""

from collections.abc import Awaitable, Callable

from mcp_server.tools.config_handlers import (
    handle_configure_chunking,
    handle_configure_reranking,
    handle_configure_search_mode,
    handle_switch_embedding_model,
    handle_switch_project,
)
from mcp_server.tools.index_handlers import (
    handle_clear_index,
    handle_delete_project,
    handle_index_directory,
)
from mcp_server.tools.search_handlers import (
    handle_find_connections,
    handle_find_path,
    handle_find_similar_code,
    handle_search_code,
)
from mcp_server.tools.status_handlers import (
    handle_cleanup_resources,
    handle_get_index_status,
    handle_get_memory_status,
    handle_get_search_config_status,
    handle_list_embedding_models,
    handle_list_projects,
)


# Explicit name→handler dispatch table — mirrors TOOL_REGISTRY keys exactly.
# server.py uses this instead of getattr(tool_handlers, f"handle_{name}").
TOOL_DISPATCH: dict[str, Callable[[dict], Awaitable[dict | list]]] = {
    # Status (6)
    "get_index_status": handle_get_index_status,
    "list_projects": handle_list_projects,
    "get_memory_status": handle_get_memory_status,
    "cleanup_resources": handle_cleanup_resources,
    "get_search_config_status": handle_get_search_config_status,
    "list_embedding_models": handle_list_embedding_models,
    # Config (5)
    "switch_project": handle_switch_project,
    "configure_reranking": handle_configure_reranking,
    "configure_search_mode": handle_configure_search_mode,
    "configure_chunking": handle_configure_chunking,
    "switch_embedding_model": handle_switch_embedding_model,
    # Search (4)
    "search_code": handle_search_code,
    "find_similar_code": handle_find_similar_code,
    "find_connections": handle_find_connections,
    "find_path": handle_find_path,
    # Index (3)
    "index_directory": handle_index_directory,
    "clear_index": handle_clear_index,
    "delete_project": handle_delete_project,
}

__all__ = [
    # Dispatch table
    "TOOL_DISPATCH",
    # Status handlers (6)
    "handle_get_index_status",
    "handle_list_projects",
    "handle_get_memory_status",
    "handle_cleanup_resources",
    "handle_get_search_config_status",
    "handle_list_embedding_models",
    # Config handlers (5)
    "handle_switch_project",
    "handle_configure_reranking",
    "handle_configure_search_mode",
    "handle_configure_chunking",
    "handle_switch_embedding_model",
    # Search handlers (4)
    "handle_search_code",
    "handle_find_similar_code",
    "handle_find_connections",
    "handle_find_path",
    # Index handlers (3)
    "handle_index_directory",
    "handle_clear_index",
    "handle_delete_project",
]
