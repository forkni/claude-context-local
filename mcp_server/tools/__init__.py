"""MCP Server Tools.

Additional tool implementations for specialized functionality.
"""

# Specialized tools
from mcp_server.tools.code_relationship_analyzer import (
    CodeRelationshipAnalyzer,
    ImpactReport,
)

# Handler modules
from mcp_server.tools.config_handlers import (
    handle_configure_query_routing,
    handle_configure_reranking,
    handle_configure_search_mode,
    handle_switch_embedding_model,
    handle_switch_project,
)
from mcp_server.tools.decorators import error_handler
from mcp_server.tools.index_handlers import (
    handle_clear_index,
    handle_delete_project,
    handle_index_directory,
)
from mcp_server.tools.search_handlers import (
    handle_find_connections,
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
    # Specialized tools
    "CodeRelationshipAnalyzer",
    "ImpactReport",
    # Decorator
    "error_handler",
    # Status handlers (6)
    "handle_get_index_status",
    "handle_list_projects",
    "handle_get_memory_status",
    "handle_cleanup_resources",
    "handle_get_search_config_status",
    "handle_list_embedding_models",
    # Config handlers (5)
    "handle_switch_project",
    "handle_configure_query_routing",
    "handle_configure_reranking",
    "handle_configure_search_mode",
    "handle_switch_embedding_model",
    # Search handlers (3)
    "handle_search_code",
    "handle_find_similar_code",
    "handle_find_connections",
    # Index handlers (3)
    "handle_index_directory",
    "handle_clear_index",
    "handle_delete_project",
]
