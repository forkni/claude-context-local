"""Unit tests for mcp_server/resource_manager.py.

_cleanup_previous_resources() is the routine every async index/switch/clear
handler offloads via asyncio.to_thread before touching the next project's
resources. Each of its six steps is independently try/excepted so a failure
in one component (e.g. a hung index_manager.close()) never blocks cleanup of
the others. These tests cover the two properties that guarantee: the happy
path invokes every dependency, and a raising early step doesn't stop later
steps from running.

bind_active_project_overrides()/initialize_server_state() are covered
separately (Phase 1c, ADR-0018 follow-on; promoted to public + non-swallowing
in the project-activation-pairing refactor). Before Phase 1c, server startup
restored the active project (env var or persisted selection) on both
branches but never bound search/config.py's ``_active_project_storage_dir``,
so a restored project's search_overrides.json (ADR-0014) was silently not
merged into effective config until an explicit switch_project or
index_directory call. These tests assert the binding now happens on both
restoration paths.

bind_active_project_overrides() itself is non-swallowing: a bind failure at
a handler call site (handle_switch_project, _run_index_directory) must
propagate so @error_handler surfaces it, rather than returning success while
the previous project's overrides keep serving. Only initialize_server_state's
two startup call sites wrap it in a non-fatal try/except, since a project
storage lookup failure at boot should not crash the server.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server.resource_manager import (
    _cleanup_previous_resources,
    bind_active_project_overrides,
    initialize_server_state,
)
from mcp_server.storage_manager import get_project_storage_dir


def _make_fake_state() -> MagicMock:
    """Build a fake ApplicationState with a populated index_manager/searcher/embedders."""
    state = MagicMock()
    state.index_manager = MagicMock()
    state.searcher = MagicMock()
    state.embedders = {"default": MagicMock()}
    return state


def test_cleanup_previous_resources_happy_path_invokes_all_dependencies():
    """Every component cleanup step runs when nothing raises."""
    fake_state = _make_fake_state()
    # The function nulls state.index_manager/state.searcher after using them,
    # so capture the original mocks now — asserting via fake_state.index_manager
    # after the call would dereference None.
    index_manager_mock = fake_state.index_manager
    searcher_mock = fake_state.searcher

    with (
        patch("mcp_server.state.get_state", return_value=fake_state),
        patch("mcp_server.model_pool_manager.reset_pool_manager") as mock_reset_pool,
        patch("search.gpu_monitor.release_gpu_memory") as mock_release_gpu,
        patch("utils.observability.force_flush") as mock_force_flush,
    ):
        result = _cleanup_previous_resources()

    assert result is None

    # Component 1: index manager closed and cleared.
    index_manager_mock.close.assert_called_once()
    assert fake_state.index_manager is None
    # Component 2: searcher shut down and cleared.
    searcher_mock.shutdown.assert_called_once()
    assert fake_state.searcher is None
    # Component 3: embedder pool cleared (embedders dict was truthy).
    fake_state.clear_embedders.assert_called_once()
    # Component 4: model pool manager singleton reset.
    mock_reset_pool.assert_called_once()
    # Component 5+6: GPU memory released without a blocking synchronize.
    mock_release_gpu.assert_called_once_with(synchronize=False)
    # Component 7: pending OTel spans flushed.
    mock_force_flush.assert_called_once()


def test_cleanup_previous_resources_isolates_component_failures():
    """A raising early step must not prevent later steps from running."""
    fake_state = _make_fake_state()
    fake_state.index_manager.close.side_effect = RuntimeError("locked handle")
    index_manager_mock = fake_state.index_manager
    # Component 1 raises before reassigning state.index_manager, so it stays
    # the same mock — but component 2 succeeds and nulls state.searcher, so
    # capture that reference now too.
    searcher_mock = fake_state.searcher

    with (
        patch("mcp_server.state.get_state", return_value=fake_state),
        patch("mcp_server.model_pool_manager.reset_pool_manager") as mock_reset_pool,
        patch("search.gpu_monitor.release_gpu_memory") as mock_release_gpu,
        patch("utils.observability.force_flush") as mock_force_flush,
    ):
        result = _cleanup_previous_resources()

    # The raising step must not propagate — cleanup degrades, it doesn't crash.
    assert result is None

    index_manager_mock.close.assert_called_once()
    # index_manager is NOT nulled — the exception fired before that reassignment.
    assert fake_state.index_manager is index_manager_mock
    # Later steps still ran despite the Component 1 failure.
    searcher_mock.shutdown.assert_called_once()
    assert fake_state.searcher is None
    fake_state.clear_embedders.assert_called_once()
    mock_reset_pool.assert_called_once()
    mock_release_gpu.assert_called_once_with(synchronize=False)
    mock_force_flush.assert_called_once()


class TestBindActiveProjectOverrides:
    """Unit tests for bind_active_project_overrides (Phase 1c; promoted to
    public + non-swallowing by the project-activation-pairing refactor)."""

    def test_happy_path_binds_storage_dir_and_invalidates_caches(self):
        """The helper resolves the project's storage dir, binds it as the
        active overrides layer, and drops the config caches that step 1 of
        initialize_server_state populated before any project was bound."""
        fake_storage_dir = MagicMock()

        with (
            patch(
                "mcp_server.storage_manager.get_project_storage_dir",
                return_value=fake_storage_dir,
            ) as mock_get_dir,
            patch("search.config.set_active_project_storage_dir") as mock_set_dir,
            patch("mcp_server.state.invalidate_config_caches") as mock_invalidate,
        ):
            result = bind_active_project_overrides("/some/project")

        assert result is None
        mock_get_dir.assert_called_once_with("/some/project")
        mock_set_dir.assert_called_once_with(fake_storage_dir)
        mock_invalidate.assert_called_once()

    def test_storage_lookup_failure_propagates(self):
        """Non-swallowing by design: a raising project-storage lookup (e.g.
        an unregistered embedding model) must propagate to the caller.
        Handler call sites rely on this so @error_handler surfaces a bind
        failure instead of returning success while the previous project's
        search_overrides.json keeps serving; startup call sites are
        responsible for their own non-fatal try/except around this call
        (see TestInitializeServerStateSwallowsBindFailure)."""
        with (
            patch(
                "mcp_server.storage_manager.get_project_storage_dir",
                side_effect=ValueError("unknown embedding model"),
            ),
            patch("search.config.set_active_project_storage_dir") as mock_set_dir,
            patch("mcp_server.state.invalidate_config_caches") as mock_invalidate,
            pytest.raises(ValueError, match="unknown embedding model"),
        ):
            bind_active_project_overrides("/some/project")

        mock_set_dir.assert_not_called()
        mock_invalidate.assert_not_called()


class TestInitializeServerStateBindsOverrides:
    """Integration-style tests: after initialize_server_state restores the
    active project — env var or persisted selection — search.config's
    _active_project_storage_dir must be bound to that project's storage dir.
    Before Phase 1c, neither restoration path bound it, so a restored
    project's search_overrides.json (ADR-0014) was silently inactive until
    an explicit switch_project/index_directory call.
    """

    def test_env_var_branch_binds_overrides(self, tmp_path, monkeypatch):
        import search.config as config_module

        monkeypatch.setattr(config_module, "_active_project_storage_dir", None)

        project_path = tmp_path / "env_project"
        project_path.mkdir()
        monkeypatch.setenv("CLAUDE_DEFAULT_PROJECT", str(project_path))

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"
        with patch(
            "mcp_server.storage_manager.get_search_config", return_value=fake_config
        ):
            initialize_server_state()
            expected_storage = get_project_storage_dir(str(project_path))

        assert config_module.get_active_project_storage_dir() == str(expected_storage)

    def test_persisted_selection_branch_binds_overrides(self, tmp_path, monkeypatch):
        import search.config as config_module
        from mcp_server.project_persistence import save_project_selection

        monkeypatch.setattr(config_module, "_active_project_storage_dir", None)
        monkeypatch.delenv("CLAUDE_DEFAULT_PROJECT", raising=False)

        project_path = tmp_path / "restored_project"
        project_path.mkdir()
        save_project_selection(str(project_path))

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"
        with patch(
            "mcp_server.storage_manager.get_search_config", return_value=fake_config
        ):
            initialize_server_state()
            expected_storage = get_project_storage_dir(str(project_path))

        assert config_module.get_active_project_storage_dir() == str(expected_storage)


class TestInitializeServerStateSwallowsBindFailure:
    """bind_active_project_overrides() is non-swallowing (see
    TestBindActiveProjectOverrides.test_storage_lookup_failure_propagates),
    so initialize_server_state's two startup call sites are responsible for
    their own non-fatal try/except — a project storage lookup failure at
    boot must not crash the server on either restoration path."""

    def test_env_var_branch_does_not_crash_on_bind_failure(self, tmp_path, monkeypatch):
        project_path = tmp_path / "env_project"
        project_path.mkdir()
        monkeypatch.setenv("CLAUDE_DEFAULT_PROJECT", str(project_path))

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"
        with (
            patch(
                "mcp_server.storage_manager.get_search_config", return_value=fake_config
            ),
            patch(
                "mcp_server.resource_manager.bind_active_project_overrides",
                side_effect=ValueError("unknown embedding model"),
            ) as mock_bind,
        ):
            initialize_server_state()  # must not raise

        mock_bind.assert_called_once_with(str(project_path))

    def test_persisted_selection_branch_does_not_crash_on_bind_failure(
        self, tmp_path, monkeypatch
    ):
        from mcp_server.project_persistence import save_project_selection

        monkeypatch.delenv("CLAUDE_DEFAULT_PROJECT", raising=False)

        project_path = tmp_path / "restored_project"
        project_path.mkdir()
        save_project_selection(str(project_path))

        fake_config = MagicMock()
        fake_config.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"
        with (
            patch(
                "mcp_server.storage_manager.get_search_config", return_value=fake_config
            ),
            patch(
                "mcp_server.resource_manager.bind_active_project_overrides",
                side_effect=ValueError("unknown embedding model"),
            ) as mock_bind,
        ):
            initialize_server_state()  # must not raise

        mock_bind.assert_called_once_with(str(project_path))
