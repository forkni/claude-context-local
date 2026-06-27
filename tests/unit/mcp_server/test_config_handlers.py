"""Unit tests for per-field validation in MCP config handlers.

Covers the validation branches in handle_configure_search_mode and
handle_configure_chunking that each return specific error dicts on bad input.
"""

from unittest.mock import Mock, patch

import pytest

from mcp_server.tools.config_handlers import (
    handle_configure_chunking,
    handle_configure_search_mode,
)


@pytest.fixture
def mock_config_manager():
    """Mock config manager whose load_config returns a plain Mock config."""
    mgr = Mock()
    mgr.load_config.return_value = Mock()
    return mgr


@pytest.fixture
def mock_state():
    """Mock app state used by handle_configure_search_mode on success."""
    state = Mock()
    return state


# ============================================================================
# handle_configure_search_mode
# ============================================================================


@pytest.mark.asyncio
async def test_configure_search_mode_invalid_returns_error(mock_config_manager):
    """Invalid search_mode returns an error dict without calling save_config."""
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_search_mode({"search_mode": "fuzzy"})

    assert "error" in result
    assert "fuzzy" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.parametrize("mode", ["hybrid", "semantic", "bm25", "auto"])
@pytest.mark.asyncio
async def test_configure_search_mode_valid_saves_config(
    mode, mock_config_manager, mock_state
):
    """Each valid search_mode succeeds and persists via save_config."""
    with (
        patch(
            "mcp_server.tools.config_handlers.get_config_manager",
            return_value=mock_config_manager,
        ),
        patch(
            "mcp_server.tools.config_handlers.get_state",
            return_value=mock_state,
        ),
    ):
        result = await handle_configure_search_mode({"search_mode": mode})

    assert "error" not in result
    assert result.get("success") is True
    mock_config_manager.save_config.assert_called_once()


# ============================================================================
# handle_configure_chunking — per-field validation
# ============================================================================


@pytest.mark.asyncio
async def test_chunking_community_resolution_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"community_resolution": 0.05})

    assert "error" in result
    assert "community_resolution" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_max_phantom_degree_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"max_phantom_degree": 0})

    assert "error" in result
    assert "max_phantom_degree" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_token_estimation_invalid(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"token_estimation": "gpt4"})

    assert "error" in result
    assert "token_estimation" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_split_size_method_invalid(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"split_size_method": "tokens"})

    assert "error" in result
    assert "split_size_method" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_max_split_chars_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"max_split_chars": 500})

    assert "error" in result
    assert "max_split_chars" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_sizing_mode_invalid(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"sizing_mode": "dynamic"})

    assert "error" in result
    assert "sizing_mode" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_adaptive_multiplier_max_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"adaptive_multiplier_max": 3.0})

    assert "error" in result
    assert "adaptive_multiplier_max" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_adaptive_multiplier_min_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"adaptive_multiplier_min": 0.0})

    assert "error" in result
    assert "adaptive_multiplier_min" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_max_complexity_cap_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"max_complexity_cap": 200})

    assert "error" in result
    assert "max_complexity_cap" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_all_valid_saves_config(mock_config_manager):
    """A fully valid chunking call succeeds and calls save_config once."""
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking(
            {
                "community_resolution": 1.0,
                "max_phantom_degree": 50,
                "token_estimation": "whitespace",
                "split_size_method": "lines",
                "max_split_chars": 5000,
                "sizing_mode": "adaptive",
                "adaptive_multiplier_max": 1.5,
                "adaptive_multiplier_min": 0.5,
                "max_complexity_cap": 20,
            }
        )

    assert "error" not in result
    assert result.get("success") is True
    mock_config_manager.save_config.assert_called_once()
