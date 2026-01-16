"""Integration tests for project selection and switching."""

import pytest


@pytest.mark.asyncio
@pytest.mark.integration
async def test_get_index_status_no_project_selected():
    """Test that get_index_status returns clear error when no project selected."""
    from mcp_server.state import get_state
    from mcp_server.tools.status_handlers import handle_get_index_status

    state = get_state()
    state.current_project = None  # Ensure no project selected

    result = await handle_get_index_status({})

    # Should return error with 0 chunks
    assert "error" in result
    assert "No indexed project found" in result["error"]
    assert result["index_statistics"]["total_chunks"] == 0
    assert result["current_project"] is None
    assert "index_directory" in result["system_message"]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
async def test_switch_project_shows_correct_index(sample_codebase, tmp_path):
    """Test that switch_project makes get_index_status show correct data.

    Workflow:
    1. Index a test project
    2. Simulate server restart (clear current_project)
    3. Verify get_index_status returns error (no project selected)
    4. Switch to the indexed project
    5. Verify get_index_status now shows correct data
    """
    from mcp_server.state import get_state
    from mcp_server.tools.config_handlers import handle_switch_project
    from mcp_server.tools.index_handlers import handle_index_directory
    from mcp_server.tools.status_handlers import handle_get_index_status

    # Get project path from sample_codebase fixture
    # sample_codebase["auth"] is at: temp_project/src/auth/authenticator.py
    # We want: temp_project (3 levels up)
    project_path = str(sample_codebase["auth"].parent.parent.parent)

    # Step 1: Index the test project
    await handle_index_directory({"directory_path": project_path})
    # Index created - we'll verify the chunk count via get_index_status after switch

    # Step 2: Simulate server restart - clear current_project
    state = get_state()
    state.current_project = None

    # Step 3: Verify get_index_status returns error when no project selected
    status_before = await handle_get_index_status({})
    assert "error" in status_before
    assert status_before["index_statistics"]["total_chunks"] == 0

    # Step 4: Switch to the indexed project
    switch_result = await handle_switch_project({"project_path": project_path})
    assert switch_result.get("success") is True
    assert switch_result.get("indexed") is True

    # Step 5: Verify get_index_status now shows correct data
    status_after = await handle_get_index_status({})
    assert "error" not in status_after
    assert status_after["index_statistics"]["total_chunks"] > 0, (
        "Should show indexed chunks after switch"
    )
    assert status_after["current_project"] == project_path

    # Verify the chunk count is reasonable for the sample codebase
    # sample_codebase has 4 modules (auth, database, api, utils) + __init__ files
    # Should have at least a few chunks
    assert status_after["index_statistics"]["total_chunks"] >= 4, (
        "Should have at least 4 chunks from 4 modules"
    )
