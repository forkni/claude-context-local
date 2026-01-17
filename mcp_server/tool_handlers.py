"""Tool handlers for low-level MCP server.

This module re-exports handlers from domain-specific modules.
Direct imports from specific handler modules are recommended:
- mcp_server.tools.status_handlers
- mcp_server.tools.config_handlers
- mcp_server.tools.search_handlers
- mcp_server.tools.index_handlers

All handler implementations have been moved to domain-specific modules with
consistent error handling via the @error_handler decorator.
"""

# Re-export all handlers from new modules for backward compatibility
from mcp_server.tools.config_handlers import (
    handle_configure_chunking,
    handle_configure_query_routing,
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


__all__ = [
    # Status handlers (6)
    "handle_get_index_status",
    "handle_list_projects",
    "handle_get_memory_status",
    "handle_cleanup_resources",
    "handle_get_search_config_status",
    "handle_list_embedding_models",
    # Config handlers (6)
    "handle_switch_project",
    "handle_configure_query_routing",
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
