"""Unit tests for per-field validation in MCP config handlers.

Covers the validation branches in handle_configure_search_mode and
handle_configure_chunking that each return specific error dicts on bad input.
"""

import json
from unittest.mock import Mock, patch

import pytest

from mcp_server.tools.config_handlers import (
    _detect_indexed_model,
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


# ============================================================================
# _detect_indexed_model — cross-pool detection via project_info.json
# ============================================================================


def test_detect_indexed_model_reads_project_info_cross_pool(tmp_path):
    """_detect_indexed_model returns the correct key via project_info.json
    even when the active pool does not contain the indexing model.

    Regression test: previously only scanned the active pool, causing
    'No indexed model detected' for projects indexed with a different pool.
    """
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    # Construct a valid project_info.json so info_path.exists() is True
    info_file = tmp_path / "project_info.json"
    info_file.write_text(
        json.dumps(
            {"embedding_model": "Qwen/Qwen3-Embedding-0.6B", "model_dimension": 1024}
        )
    )

    # Create a storage dir with code.index so the existence check passes
    index_dir = tmp_path / "storage" / "index"
    index_dir.mkdir(parents=True)
    (index_dir / "code.index").write_bytes(b"")

    # Lazy imports inside _detect_indexed_model are resolved at call time from
    # their source modules — patch there, not on config_handlers.
    with (
        patch(
            "mcp_server.storage_manager.get_canonical_project_info",
            return_value=info_file,
        ),
        patch(
            "mcp_server.model_pool_manager.get_model_key_from_name",
            return_value="qwen3_0.6b",
        ),
        patch(
            "mcp_server.tools.config_handlers.get_project_storage_dir",
            return_value=tmp_path / "storage",
        ),
    ):
        result = _detect_indexed_model(str(project_path))

    assert result == "qwen3_0.6b"


def test_detect_indexed_model_skips_stale_project_info_without_index(tmp_path):
    """When project_info.json exists but its model has no code.index, the function
    falls through to the active-pool directory scan instead of returning that model.

    Regression test: bge-m3 had project_info.json but no index/ directory after a
    force re-index with qwen3 only — previously caused indexed:false in switch_project.
    """
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    # Stale project_info.json (bge_m3) — exists but has no index
    stale_info = tmp_path / "stale_info.json"
    stale_info.write_text(
        json.dumps({"embedding_model": "BAAI/bge-m3", "model_dimension": 1024})
    )

    # A qwen3 storage dir that DOES have code.index (the real index)
    qwen3_storage = tmp_path / "qwen3_storage"
    (qwen3_storage / "index").mkdir(parents=True)
    (qwen3_storage / "index" / "code.index").write_bytes(b"")

    # bge_m3 storage dir has NO code.index — just project_info.json
    bge_m3_storage = tmp_path / "bge_m3_storage"
    bge_m3_storage.mkdir()

    call_count = []

    def fake_get_storage_dir(path, model_key=None):
        call_count.append(model_key)
        if model_key == "bge_m3":
            return bge_m3_storage
        return qwen3_storage

    with (
        patch(
            "mcp_server.storage_manager.get_canonical_project_info",
            return_value=stale_info,
        ),
        patch(
            "mcp_server.model_pool_manager.get_model_key_from_name",
            return_value="bge_m3",
        ),
        patch("mcp_server.model_pool_manager.get_model_pool_manager") as mock_pool_mgr,
        patch(
            "mcp_server.tools.config_handlers.get_project_storage_dir",
            side_effect=fake_get_storage_dir,
        ),
    ):
        # Active pool contains qwen3_0.6b (the one with the real index)
        mock_pool_mgr.return_value.get_pool_config.return_value = {
            "qwen3_0.6b": "Qwen/Qwen3-Embedding-0.6B"
        }
        result = _detect_indexed_model(str(project_path))

    # Should fall through to dir scan and find qwen3 (not return bge_m3)
    assert result == "qwen3_0.6b"


def test_detect_indexed_model_fallback_when_no_project_info(tmp_path):
    """When project_info.json is absent, falls back to active-pool dir scan."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    fake_storage = tmp_path / "storage"
    (fake_storage / "index").mkdir(parents=True)
    (fake_storage / "index" / "code.index").write_bytes(b"")

    with (
        patch(
            "mcp_server.storage_manager.get_canonical_project_info",
            return_value=None,
        ),
        patch("mcp_server.model_pool_manager.get_model_pool_manager") as mock_pool_mgr,
        patch(
            "mcp_server.tools.config_handlers.get_project_storage_dir",
            return_value=fake_storage,
        ),
    ):
        mock_pool_mgr.return_value.get_pool_config.return_value = {
            "gte_modernbert": "Alibaba-NLP/gte-modernbert-base"
        }
        result = _detect_indexed_model(str(project_path))

    assert result == "gte_modernbert"


def test_detect_indexed_model_returns_none_when_nothing_found(tmp_path):
    """Returns None cleanly when project_info.json is absent and no dir scan hits."""
    project_path = tmp_path / "myproject"
    project_path.mkdir()

    empty_storage = tmp_path / "storage"
    empty_storage.mkdir()

    with (
        patch(
            "mcp_server.storage_manager.get_canonical_project_info",
            return_value=None,
        ),
        patch("mcp_server.model_pool_manager.get_model_pool_manager") as mock_pool_mgr,
        patch(
            "mcp_server.tools.config_handlers.get_project_storage_dir",
            return_value=empty_storage,
        ),
    ):
        mock_pool_mgr.return_value.get_pool_config.return_value = {
            "qwen3_0.6b": "Qwen/Qwen3-Embedding-0.6B"
        }
        result = _detect_indexed_model(str(project_path))

    assert result is None
