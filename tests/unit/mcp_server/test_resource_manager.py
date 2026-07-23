"""Unit tests for _cleanup_previous_resources (mcp_server/resource_manager.py).

_cleanup_previous_resources() is the routine every async index/switch/clear
handler offloads via asyncio.to_thread before touching the next project's
resources. Each of its six steps is independently try/excepted so a failure
in one component (e.g. a hung index_manager.close()) never blocks cleanup of
the others. These tests cover the two properties that guarantee: the happy
path invokes every dependency, and a raising early step doesn't stop later
steps from running.
"""

from unittest.mock import MagicMock, patch

from mcp_server.resource_manager import _cleanup_previous_resources


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
