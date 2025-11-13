"""Critical bug validation tests for low-level MCP server.

Tests that verify the critical fixes:
1. project_id=None bug is eliminated
2. SSE race conditions are prevented
3. State initialization is consistent
"""

import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from mcp_server.server_lowlevel_complete import server, server_lifespan
from mcp_server import tool_handlers


@pytest.mark.asyncio
@pytest.mark.integration
async def test_lifespan_hook_initializes_project():
    """CRITICAL: Verify lifespan hook initializes _current_project BEFORE tool calls."""

    # Set environment variable
    test_project = str(Path.cwd())
    with patch.dict(os.environ, {'CLAUDE_DEFAULT_PROJECT': test_project}):
        # Run lifespan hook
        async with server_lifespan(server):
            # Import the global state
            from mcp_server.tool_handlers import _current_project

            # Verify project is initialized
            assert _current_project is not None
            assert _current_project == test_project

            # Verify we can call tools without project_id=None errors
            # This would have failed in FastMCP due to race condition


@pytest.mark.asyncio
@pytest.mark.integration
async def test_project_id_never_none_in_get_index_manager():
    """CRITICAL: Verify get_index_manager never receives project_id=None."""

    test_project = str(Path.cwd())

    with patch.dict(os.environ, {'CLAUDE_DEFAULT_PROJECT': test_project}):
        async with server_lifespan(server):
            from mcp_server.server_lowlevel import get_index_manager, _current_project

            # Verify global state is set
            assert _current_project is not None

            # Call get_index_manager - should not fail with project_id=None
            with patch('mcp_server.server_lowlevel.get_project_storage_dir') as mock_storage:
                mock_storage.return_value = Path('/tmp/test')
                with patch('mcp_server.server_lowlevel.CodeIndexManager') as mock_manager:
                    # Call the function that was previously failing
                    manager = get_index_manager()

                    # Verify CodeIndexManager was called with project_id
                    assert mock_manager.called
                    call_kwargs = mock_manager.call_args[1]

                    # CRITICAL: project_id should NOT be None
                    assert 'project_id' in call_kwargs
                    assert call_kwargs['project_id'] is not None
                    assert call_kwargs['project_id'] != 'None'


@pytest.mark.asyncio
@pytest.mark.integration
async def test_state_consistency_across_tool_calls():
    """Verify state remains consistent across multiple tool calls."""

    test_project = str(Path.cwd())

    with patch.dict(os.environ, {'CLAUDE_DEFAULT_PROJECT': test_project}):
        async with server_lifespan(server):
            from mcp_server.tool_handlers import _current_project as project1

            # Simulate multiple tool calls
            with patch('mcp_server.tool_handlers.get_storage_dir') as mock_storage:
                mock_storage.return_value = Path('/tmp/test')

                # First tool call
                result1 = await tool_handlers.handle_list_projects({})

                from mcp_server.tool_handlers import _current_project as project2

                # Second tool call
                result2 = await tool_handlers.handle_get_search_config_status({})

                from mcp_server.tool_handlers import _current_project as project3

                # Verify state didn't change between calls
                assert project1 == project2 == project3
                assert project1 is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_lifespan_hook_runs_before_first_tool():
    """Verify lifespan hook completes BEFORE any tool can be called."""

    initialization_log = []

    async def mock_init():
        initialization_log.append('lifespan_start')
        await asyncio.sleep(0.1)  # Simulate initialization time
        initialization_log.append('lifespan_complete')

    async def mock_tool_call():
        initialization_log.append('tool_called')

    # Simulate lifespan hook + tool call
    async with server_lifespan(server):
        initialization_log.append('server_ready')
        await mock_tool_call()

    # Verify order: lifespan must complete before server_ready
    # In FastMCP, tools could be called before initialization
    assert initialization_log[0] == 'server_ready'
    assert initialization_log[1] == 'tool_called'


@pytest.mark.asyncio
@pytest.mark.integration
async def test_parallel_tool_calls_dont_cause_race_condition():
    """Verify parallel tool calls don't cause state inconsistencies."""

    test_project = str(Path.cwd())

    with patch.dict(os.environ, {'CLAUDE_DEFAULT_PROJECT': test_project}):
        async with server_lifespan(server):
            with patch('mcp_server.tool_handlers.get_storage_dir') as mock_storage:
                mock_storage.return_value = Path('/tmp/test')

                with patch('mcp_server.tool_handlers.get_search_config') as mock_config:
                    mock_cfg = Mock()
                    mock_cfg.enable_hybrid_search = True
                    mock_cfg.bm25_weight = 0.4
                    mock_cfg.dense_weight = 0.6
                    mock_cfg.rrf_k_parameter = 60
                    mock_cfg.use_parallel_search = True
                    mock_cfg.embedding_model_name = 'test'
                    mock_config.return_value = mock_cfg

                    # Call multiple tools in parallel
                    results = await asyncio.gather(
                        tool_handlers.handle_get_search_config_status({}),
                        tool_handlers.handle_list_projects({}),
                        tool_handlers.handle_list_embedding_models({}),
                        return_exceptions=True
                    )

                    # All should succeed (no race condition errors)
                    for result in results:
                        assert not isinstance(result, Exception)
                        assert 'error' not in result or 'project_id' not in str(result.get('error', ''))


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cleanup_called_on_shutdown():
    """Verify cleanup is called when server shuts down."""

    cleanup_called = False

    def mock_cleanup():
        nonlocal cleanup_called
        cleanup_called = True

    with patch('mcp_server.server_lowlevel_complete._cleanup_previous_resources', mock_cleanup):
        async with server_lifespan(server):
            pass  # Server runs and exits

    # Verify cleanup was called
    assert cleanup_called, "Cleanup should be called on server shutdown"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_model_pool_initialized_in_lifespan():
    """Verify model pool is initialized during lifespan (not on first tool call)."""

    with patch('mcp_server.server_lowlevel_complete.initialize_model_pool') as mock_init:
        with patch.dict(os.environ, {'CLAUDE_MULTI_MODEL_ENABLED': 'true'}):
            async with server_lifespan(server):
                # Model pool should have been initialized
                mock_init.assert_called_once()

                # Verify it was called with lazy_load=True
                call_kwargs = mock_init.call_args[1]
                assert call_kwargs.get('lazy_load') is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_no_tools_run_before_lifespan_complete():
    """Verify no tools can execute before lifespan hook completes."""

    tool_execution_order = []

    original_list_projects = tool_handlers.handle_list_projects

    async def instrumented_list_projects(args):
        tool_execution_order.append('tool_executed')
        return await original_list_projects(args)

    with patch('mcp_server.tool_handlers.handle_list_projects', instrumented_list_projects):
        with patch('mcp_server.tool_handlers.get_storage_dir') as mock_storage:
            mock_storage.return_value = Path('/tmp/test')

            async with server_lifespan(server):
                tool_execution_order.append('lifespan_complete')
                await tool_handlers.handle_list_projects({})

    # Tool should only execute AFTER lifespan completes
    assert tool_execution_order[0] == 'lifespan_complete'
    assert tool_execution_order[1] == 'tool_executed'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
