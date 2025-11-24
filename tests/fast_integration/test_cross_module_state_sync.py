"""Integration tests for cross-module state synchronization."""

from pathlib import Path

import pytest

from mcp_server import server
from mcp_server.project_persistence import (
    clear_project_selection,
    load_project_selection,
    save_project_selection,
)
from mcp_server.state import get_state, reset_state


@pytest.fixture
def temp_projects(tmp_path, monkeypatch):
    """Create temporary test projects."""
    # Mock storage directory
    storage_dir = tmp_path / ".claude_code_search"
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CODE_SEARCH_STORAGE", str(storage_dir))

    # Create test projects
    project1 = tmp_path / "project1"
    project2 = tmp_path / "project2"
    project1.mkdir(parents=True, exist_ok=True)
    project2.mkdir(parents=True, exist_ok=True)

    yield {
        "project1": str(project1),
        "project2": str(project2),
        "storage": storage_dir,
    }

    # Cleanup
    reset_state()
    clear_project_selection()


class TestSetCurrentProjectSynchronization:
    """Tests for set_current_project() cross-module sync."""

    def test_set_current_project_updates_server_global(self, temp_projects):
        """Test that set_current_project updates server.py global variable."""
        project_path = temp_projects["project1"]

        # Set current project
        server.set_current_project(project_path)

        # Verify server module global is updated
        assert server._current_project == project_path

    def test_set_current_project_updates_application_state(self, temp_projects):
        """Test that set_current_project updates ApplicationState."""
        project_path = temp_projects["project1"]

        # Set current project
        server.set_current_project(project_path)

        # Verify ApplicationState is updated
        state = get_state()
        assert state.current_project == project_path

    def test_set_current_project_syncs_both_locations(self, temp_projects):
        """Test that both server global and ApplicationState are synced."""
        project_path = temp_projects["project1"]

        # Set current project
        server.set_current_project(project_path)

        # Verify both locations have the same value
        assert server._current_project == project_path
        assert get_state().current_project == project_path
        assert server._current_project == get_state().current_project

    def test_multiple_project_switches_stay_synced(self, temp_projects):
        """Test multiple project switches maintain synchronization."""
        project1 = temp_projects["project1"]
        project2 = temp_projects["project2"]

        # Switch to project1
        server.set_current_project(project1)
        assert server._current_project == project1
        assert get_state().current_project == project1

        # Switch to project2
        server.set_current_project(project2)
        assert server._current_project == project2
        assert get_state().current_project == project2

        # Switch back to project1
        server.set_current_project(project1)
        assert server._current_project == project1
        assert get_state().current_project == project1


class TestApplicationStateSwitchProject:
    """Tests for ApplicationState.switch_project()."""

    def test_switch_project_updates_current_project(self, temp_projects):
        """Test switch_project updates current_project field."""
        project_path = temp_projects["project1"]
        state = get_state()

        state.switch_project(project_path)

        assert state.current_project == project_path

    def test_switch_project_clears_index_manager(self, temp_projects):
        """Test switch_project clears index_manager."""
        project_path = temp_projects["project1"]
        state = get_state()

        # Set a mock index_manager
        state.index_manager = "mock_index_manager"

        # Switch project
        state.switch_project(project_path)

        # Verify index_manager is cleared
        assert state.index_manager is None

    def test_switch_project_clears_searcher(self, temp_projects):
        """Test switch_project clears searcher."""
        project_path = temp_projects["project1"]
        state = get_state()

        # Set a mock searcher
        state.searcher = "mock_searcher"

        # Switch project
        state.switch_project(project_path)

        # Verify searcher is cleared
        assert state.searcher is None

    def test_switch_project_preserves_embedders(self, temp_projects):
        """Test switch_project preserves embedders dict."""
        project_path = temp_projects["project1"]
        state = get_state()

        # Set mock embedders
        state.embedders = {"bge_m3": "mock_embedder"}

        # Switch project
        state.switch_project(project_path)

        # Verify embedders are preserved
        assert state.embedders == {"bge_m3": "mock_embedder"}

    def test_switch_project_preserves_current_model_key(self, temp_projects):
        """Test switch_project preserves current_model_key."""
        project_path = temp_projects["project1"]
        state = get_state()

        # Set current model
        state.current_model_key = "bge_m3"

        # Switch project
        state.switch_project(project_path)

        # Verify model key is preserved
        assert state.current_model_key == "bge_m3"


class TestProjectPersistenceIntegration:
    """Tests for project persistence integration with state management."""

    def test_save_and_set_current_project_integration(self, temp_projects):
        """Test saving persistence and setting current project together."""
        project_path = temp_projects["project1"]

        # Set current project
        server.set_current_project(project_path)

        # Save persistence
        save_project_selection(project_path, model_key="bge_m3")

        # Verify both are consistent
        assert server._current_project == project_path
        selection = load_project_selection()
        assert selection is not None
        assert Path(selection["last_project_path"]) == Path(project_path)

    def test_load_persistence_matches_current_state(self, temp_projects):
        """Test loaded persistence matches current state."""
        project_path = temp_projects["project1"]

        # Set and save
        server.set_current_project(project_path)
        save_project_selection(project_path, model_key="qwen3")

        # Clear state
        reset_state()

        # Load persistence
        selection = load_project_selection()
        assert selection is not None

        # Set current project from loaded selection
        server.set_current_project(selection["last_project_path"])

        # Verify state matches loaded selection
        assert server._current_project == selection["last_project_path"]
        assert get_state().current_project == selection["last_project_path"]

    def test_clear_persistence_independent_of_state(self, temp_projects):
        """Test clearing persistence doesn't affect current state."""
        project_path = temp_projects["project1"]

        # Set and save
        server.set_current_project(project_path)
        save_project_selection(project_path)

        # Clear persistence
        clear_project_selection()

        # State should still have project
        assert server._current_project == project_path
        assert get_state().current_project == project_path

        # Persistence should be cleared
        assert load_project_selection() is None


class TestCrossModuleImportBehavior:
    """Tests for cross-module import behavior and synchronization."""

    def test_direct_global_assignment_does_not_sync(self, temp_projects):
        """Test that direct global assignment (anti-pattern) doesn't sync.

        This demonstrates WHY we need set_current_project() instead of
        direct assignment.
        """
        project_path = temp_projects["project1"]

        # Anti-pattern: Direct assignment to module global
        # (This is what we DON'T want users to do)
        server._current_project = project_path

        # ApplicationState would NOT be updated (if not using setter)
        # This test documents the problem set_current_project() solves
        # Note: In actual code, _current_project should only be set via
        # set_current_project() to ensure sync

    def test_set_current_project_is_required_for_sync(self, temp_projects):
        """Test that using set_current_project() is required for sync."""
        project1 = temp_projects["project1"]
        project2 = temp_projects["project2"]

        # Correct pattern: Use setter
        server.set_current_project(project1)
        assert get_state().current_project == project1

        # Another correct use
        server.set_current_project(project2)
        assert get_state().current_project == project2

    def test_state_reset_clears_all_locations(self, temp_projects):
        """Test that reset_state() clears all state locations."""
        project_path = temp_projects["project1"]

        # Set current project
        server.set_current_project(project_path)

        # Reset state
        reset_state()

        # Verify state is cleared
        state = get_state()
        assert state.current_project is None
        assert state.index_manager is None
        assert state.searcher is None
        assert state.embedders == {}


class TestRealWorldWorkflows:
    """Tests for real-world usage workflows."""

    def test_server_startup_restore_workflow(self, temp_projects):
        """Test typical server startup workflow with persistence restore."""
        project_path = temp_projects["project1"]

        # 1. User previously selected a project (simulated)
        save_project_selection(project_path, model_key="bge_m3")

        # 2. Server starts (state is fresh)
        reset_state()

        # 3. Server loads last project from persistence
        selection = load_project_selection()
        assert selection is not None

        # 4. Server sets current project using loaded path
        server.set_current_project(selection["last_project_path"])

        # 5. Verify state is correctly initialized
        assert server._current_project == project_path
        assert get_state().current_project == project_path

    def test_project_switch_workflow(self, temp_projects):
        """Test typical project switch workflow."""
        project1 = temp_projects["project1"]
        project2 = temp_projects["project2"]

        # 1. Start with project1
        server.set_current_project(project1)
        save_project_selection(project1, model_key="bge_m3")

        # Simulate some state being created
        state = get_state()
        state.index_manager = "mock_index_1"
        state.searcher = "mock_searcher_1"

        # 2. Switch to project2
        server.set_current_project(project2)
        save_project_selection(project2, model_key="qwen3")

        # Use ApplicationState.switch_project() to clear project-specific state
        state.switch_project(project2)

        # 3. Verify switch
        assert server._current_project == project2
        assert get_state().current_project == project2
        assert state.index_manager is None  # Cleared
        assert state.searcher is None  # Cleared

        # 4. Verify persistence updated
        selection = load_project_selection()
        assert Path(selection["last_project_path"]) == Path(project2)

    def test_multiple_tool_calls_maintain_consistency(self, temp_projects):
        """Test that state remains consistent across multiple operations."""
        project_path = temp_projects["project1"]

        # Initial setup
        server.set_current_project(project_path)
        save_project_selection(project_path)

        # Simulate multiple tool calls checking project
        for _ in range(5):
            # Each "tool call" verifies project is consistent
            assert server._current_project == project_path
            assert get_state().current_project == project_path

            loaded = load_project_selection()
            assert loaded is not None
            assert Path(loaded["last_project_path"]) == Path(project_path)


class TestEdgeCases:
    """Tests for edge cases and error scenarios."""

    def test_set_current_project_with_none(self, temp_projects):
        """Test setting current project to None."""
        # First set a real project
        project_path = temp_projects["project1"]
        server.set_current_project(project_path)

        # Then set to None
        server.set_current_project(None)

        assert server._current_project is None
        assert get_state().current_project is None

    def test_set_current_project_with_empty_string(self, temp_projects):
        """Test setting current project to empty string."""
        server.set_current_project("")

        assert server._current_project == ""
        assert get_state().current_project == ""

    def test_switch_project_multiple_times_rapidly(self, temp_projects):
        """Test rapid project switching maintains sync."""
        projects = [temp_projects["project1"], temp_projects["project2"]]

        for i in range(10):
            project = projects[i % 2]
            server.set_current_project(project)

            # Verify sync after each switch
            assert server._current_project == project
            assert get_state().current_project == project
