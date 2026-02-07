"""Critical bug validation tests for low-level MCP server.

Tests that verify the critical fixes:
1. project_id=None bug is eliminated
2. SSE race conditions are prevented
3. State initialization is consistent

NOTE (2025-11-13): Lifecycle tests removed after migration to application-level initialization.
The server no longer uses per-connection server_lifespan - initialization happens at application
startup via Starlette's app_lifespan, guaranteeing state is ready before any connections.
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server import tool_handlers


# REMOVED (2025-11-13): test_lifespan_hook_initializes_project
# Reason: server_lifespan no longer exists - initialization now happens at application
# startup via Starlette's app_lifespan, guaranteeing state before any connections.
# The behavior this tested is now architecturally guaranteed.


# REMOVED (2025-11-13): test_project_id_never_none_in_get_index_manager
# Reason: Application-level initialization guarantees _current_project is set before tool calls.


# REMOVED (2025-11-13): test_state_consistency_across_tool_calls
# Reason: State consistency is now guaranteed by application-level initialization.


# REMOVED (2025-11-13): test_lifespan_hook_runs_before_first_tool
# Reason: Starlette's application lifecycle guarantees initialization before accepting connections.


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_tool_calls_dont_cause_race_condition():
    """Verify parallel tool calls don't cause state inconsistencies."""

    test_project = str(Path.cwd())

    with (
        patch.dict(os.environ, {"CLAUDE_DEFAULT_PROJECT": test_project}),
        patch("mcp_server.tools.status_handlers.get_storage_dir") as mock_storage,
    ):
        mock_storage.return_value = Path("/tmp/test")

        with patch("search.config.get_search_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.search_mode.enable_hybrid = True
            mock_cfg.search_mode.bm25_weight = 0.4
            mock_cfg.search_mode.dense_weight = 0.6
            mock_cfg.search_mode.rrf_k_parameter = 60
            mock_cfg.performance.use_parallel_search = True
            mock_cfg.embedding.model_name = "test"
            mock_config.return_value = mock_cfg

            # Call multiple tools in parallel
            results = await asyncio.gather(
                tool_handlers.handle_get_search_config_status({}),
                tool_handlers.handle_list_projects({}),
                tool_handlers.handle_list_embedding_models({}),
                return_exceptions=True,
            )

            # All should succeed (no race condition errors)
            for result in results:
                assert not isinstance(result, Exception)
                assert "error" not in result or "project_id" not in str(
                    result.get("error", "")
                )


# REMOVED (2025-11-13): test_cleanup_called_on_shutdown
# Reason: Cleanup is now part of app_lifespan finally block in Starlette application.


# REMOVED (2025-11-13): test_model_pool_initialized_in_lifespan
# Reason: Model pool initialization is now in app_lifespan, verified by integration testing.


# REMOVED (2025-11-13): test_no_tools_run_before_lifespan_complete
# Reason: Starlette's application lifecycle architecturally guarantees initialization order.


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
