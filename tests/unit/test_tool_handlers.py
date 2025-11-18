"""Unit tests for low-level MCP tool handlers.

Tests all 14 tool handlers with mocked dependencies.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Import handlers
from mcp_server import tool_handlers

# ============================================================================
# SIMPLE TOOLS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_handle_get_index_status_success():
    """Test get_index_status returns statistics."""
    with patch("mcp_server.tool_handlers.get_index_manager") as mock_manager:
        # Mock index manager
        mock_manager.return_value.get_stats.return_value = {
            "total_chunks": 100,
            "total_files": 10,
            "index_size_mb": 5.2,
        }

        # Mock embedders
        with patch("mcp_server.tool_handlers._embedders", {"default": None}):
            with patch("mcp_server.tool_handlers._multi_model_enabled", False):
                result = await tool_handlers.handle_get_index_status({})

                assert "index_statistics" in result
                assert result["index_statistics"]["total_chunks"] == 100
                assert result["index_statistics"]["total_files"] == 10


@pytest.mark.asyncio
async def test_handle_get_index_status_error():
    """Test get_index_status handles errors gracefully."""
    with patch("mcp_server.tool_handlers.get_index_manager") as mock_manager:
        mock_manager.side_effect = Exception("Index not found")

        result = await tool_handlers.handle_get_index_status({})

        assert "error" in result
        assert "Index not found" in result["error"]


@pytest.mark.asyncio
async def test_handle_list_projects_no_projects():
    """Test list_projects when no projects exist."""
    with patch("mcp_server.tool_handlers.get_storage_dir") as mock_storage:
        mock_storage.return_value = Path("/tmp/nonexistent")

        result = await tool_handlers.handle_list_projects({})

        assert result["count"] == 0
        assert result["projects"] == []
        assert "No projects indexed" in result["message"]


@pytest.mark.asyncio
async def test_handle_list_projects_with_projects(tmp_path):
    """Test list_projects returns project information."""
    # Create mock project structure
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    project_dir = projects_dir / "test_project"
    project_dir.mkdir()

    # Create project_info.json
    info_file = project_dir / "project_info.json"
    info_file.write_text(
        json.dumps(
            {
                "project_name": "test_project",
                "project_path": str(tmp_path),
                "created_at": datetime.now().isoformat(),
            }
        )
    )

    with patch("mcp_server.tool_handlers.get_storage_dir") as mock_storage:
        mock_storage.return_value = tmp_path
        with patch("mcp_server.tool_handlers._current_project", str(tmp_path)):
            result = await tool_handlers.handle_list_projects({})

            assert result["count"] == 1
            assert len(result["projects"]) == 1
            assert result["projects"][0]["project_name"] == "test_project"


@pytest.mark.asyncio
async def test_handle_get_memory_status():
    """Test get_memory_status returns system info."""
    with patch("psutil.virtual_memory") as mock_vmem:
        # Mock virtual memory
        mock_mem = Mock()
        mock_mem.total = 16 * 1024**3  # 16 GB
        mock_mem.available = 8 * 1024**3  # 8 GB
        mock_mem.used = 8 * 1024**3  # 8 GB
        mock_mem.percent = 50.0
        mock_vmem.return_value = mock_mem

        with patch("torch.cuda.is_available", return_value=False):
            result = await tool_handlers.handle_get_memory_status({})

            assert "system_memory" in result
            assert result["system_memory"]["total_gb"] == 16.0
            assert result["system_memory"]["percent"] == 50.0


@pytest.mark.asyncio
async def test_handle_cleanup_resources():
    """Test cleanup_resources calls cleanup function."""
    with patch("mcp_server.tool_handlers._cleanup_previous_resources") as mock_cleanup:
        result = await tool_handlers.handle_cleanup_resources({})

        assert result["success"] is True
        assert "cleaned up" in result["message"].lower()
        mock_cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_search_config_status():
    """Test get_search_config_status returns configuration."""
    with patch("mcp_server.tool_handlers.get_search_config") as mock_config:
        mock_cfg = Mock()
        mock_cfg.enable_hybrid_search = True
        mock_cfg.bm25_weight = 0.4
        mock_cfg.dense_weight = 0.6
        mock_cfg.rrf_k_parameter = 60
        mock_cfg.use_parallel_search = True
        mock_cfg.embedding_model_name = "BAAI/bge-m3"
        mock_config.return_value = mock_cfg

        with patch("mcp_server.tool_handlers._multi_model_enabled", True):
            result = await tool_handlers.handle_get_search_config_status({})

            assert result["search_mode"] == "hybrid"
            assert result["bm25_weight"] == 0.4
            assert result["embedding_model"] == "BAAI/bge-m3"
            assert result["multi_model_enabled"] is True


@pytest.mark.asyncio
async def test_handle_list_embedding_models():
    """Test list_embedding_models returns model registry."""
    with patch(
        "mcp_server.tool_handlers.MODEL_REGISTRY",
        {
            "model1": {"dimension": 768, "description": "Test model 1"},
            "model2": {"dimension": 1024, "description": "Test model 2"},
        },
    ):
        with patch("mcp_server.tool_handlers.get_search_config") as mock_config:
            mock_cfg = Mock()
            mock_cfg.embedding_model_name = "model1"
            mock_config.return_value = mock_cfg

            result = await tool_handlers.handle_list_embedding_models({})

            assert result["count"] == 2
            assert len(result["models"]) == 2
            assert result["current_model"] == "model1"


# ============================================================================
# MEDIUM TOOLS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_handle_switch_project_success(tmp_path):
    """Test switch_project changes current project."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # Create index directory to indicate project is indexed
    with patch("mcp_server.tool_handlers.get_project_storage_dir") as mock_storage:
        mock_project_dir = tmp_path / "storage"
        mock_project_dir.mkdir()
        index_dir = mock_project_dir / "index"
        index_dir.mkdir()
        (index_dir / "code.index").touch()
        mock_storage.return_value = mock_project_dir

        with patch("mcp_server.tool_handlers._cleanup_previous_resources"):
            with patch("mcp_server.tool_handlers._current_project", None):
                result = await tool_handlers.handle_switch_project(
                    {"project_path": str(project_path)}
                )

                assert result["success"] is True
                assert result["indexed"] is True
                assert "Switched to project" in result["message"]


@pytest.mark.asyncio
async def test_handle_switch_project_not_indexed(tmp_path):
    """Test switch_project warns when project not indexed."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    with patch("mcp_server.tool_handlers.get_project_storage_dir") as mock_storage:
        mock_project_dir = tmp_path / "storage"
        mock_project_dir.mkdir()
        mock_storage.return_value = mock_project_dir

        with patch("mcp_server.tool_handlers._cleanup_previous_resources"):
            result = await tool_handlers.handle_switch_project(
                {"project_path": str(project_path)}
            )

            assert result["success"] is True
            assert result["indexed"] is False
            assert "not indexed" in result["warning"].lower()


@pytest.mark.asyncio
async def test_handle_switch_project_not_exist():
    """Test switch_project fails when path doesn't exist."""
    result = await tool_handlers.handle_switch_project(
        {"project_path": "/nonexistent/path"}
    )

    assert "error" in result
    assert "does not exist" in result["error"].lower()


@pytest.mark.asyncio
async def test_handle_clear_index():
    """Test clear_index removes index data."""
    with patch("mcp_server.tool_handlers._current_project", "/tmp/test"):
        with patch("mcp_server.tool_handlers.get_index_manager") as mock_manager:
            mock_manager.return_value.clear_index = Mock()

            with patch("mcp_server.tool_handlers._index_manager", Mock()):
                with patch("mcp_server.tool_handlers._searcher", Mock()):
                    result = await tool_handlers.handle_clear_index({})

                    assert result["success"] is True
                    assert "cleared" in result["message"].lower()
                    mock_manager.return_value.clear_index.assert_called_once()


@pytest.mark.asyncio
async def test_handle_clear_index_no_project():
    """Test clear_index fails when no active project."""
    with patch("mcp_server.tool_handlers._current_project", None):
        result = await tool_handlers.handle_clear_index({})

        assert "error" in result
        assert "no active project" in result["error"].lower()


@pytest.mark.asyncio
async def test_handle_configure_search_mode():
    """Test configure_search_mode updates configuration."""
    with patch("mcp_server.tool_handlers.get_config_manager") as mock_manager:
        mock_cfg = Mock()
        mock_cfg.enable_hybrid_search = False
        mock_cfg.bm25_weight = 0.5
        mock_cfg.dense_weight = 0.5
        mock_cfg.use_parallel_search = True

        mock_manager.return_value.load_config.return_value = mock_cfg
        mock_manager.return_value.save_config = Mock()

        with patch("mcp_server.tool_handlers._searcher", Mock()):
            result = await tool_handlers.handle_configure_search_mode(
                {"search_mode": "hybrid", "bm25_weight": 0.4, "dense_weight": 0.6}
            )

            assert result["success"] is True
            assert result["config"]["search_mode"] == "hybrid"
            assert result["config"]["bm25_weight"] == 0.4


@pytest.mark.asyncio
async def test_handle_switch_embedding_model():
    """Test switch_embedding_model changes model."""
    with patch(
        "mcp_server.tool_handlers.MODEL_REGISTRY", {"new_model": {"dimension": 1024}}
    ):
        with patch("mcp_server.tool_handlers.get_config_manager") as mock_manager:
            mock_cfg = Mock()
            mock_cfg.embedding_model_name = "old_model"
            mock_manager.return_value.load_config.return_value = mock_cfg
            mock_manager.return_value.save_config = Mock()

            with patch("mcp_server.tool_handlers._embedders", {}):
                result = await tool_handlers.handle_switch_embedding_model(
                    {"model_name": "new_model"}
                )

                assert result["success"] is True
                assert result["new_model"] == "new_model"
                assert result["old_model"] == "old_model"


@pytest.mark.asyncio
async def test_handle_find_similar_code():
    """Test find_similar_code returns similar chunks."""
    with patch("mcp_server.tool_handlers.get_searcher") as mock_searcher:
        # Mock search results
        mock_result = Mock()
        mock_result.chunk_id = "file.py:10-20:function:test_func"
        mock_result.relative_path = "file.py"
        mock_result.start_line = 10
        mock_result.end_line = 20
        mock_result.chunk_type = "function"
        mock_result.similarity_score = 0.95
        mock_result.name = "test_func"

        mock_searcher.return_value.find_similar.return_value = [mock_result]

        result = await tool_handlers.handle_find_similar_code(
            {"chunk_id": "ref_chunk_id", "k": 5}
        )

        assert result["reference_chunk"] == "ref_chunk_id"
        assert result["count"] == 1
        assert len(result["similar_chunks"]) == 1
        assert result["similar_chunks"][0]["file"] == "file.py"
        assert result["similar_chunks"][0]["score"] == 0.95


# ============================================================================
# COMPLEX TOOLS TESTS (Simplified - full integration testing elsewhere)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_search_code_no_index():
    """Test search_code fails gracefully when no index exists."""
    with patch("mcp_server.tool_handlers.get_searcher") as mock_searcher:
        # Mock searcher with no chunks
        mock_searcher.return_value.index_manager.get_stats.return_value = {
            "total_chunks": 0
        }

        result = await tool_handlers.handle_search_code({"query": "test query", "k": 5})

        assert "error" in result
        assert "no indexed project" in result["error"].lower()


@pytest.mark.asyncio
async def test_handle_index_directory_not_exist():
    """Test index_directory fails when directory doesn't exist."""
    result = await tool_handlers.handle_index_directory(
        {"directory_path": "/nonexistent/directory"}
    )

    assert "error" in result
    assert "does not exist" in result["error"].lower()


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_all_handlers_have_error_handling():
    """Verify all handlers have try/except blocks."""
    import inspect

    handlers = [
        getattr(tool_handlers, name)
        for name in dir(tool_handlers)
        if name.startswith("handle_")
    ]

    for handler in handlers:
        source = inspect.getsource(handler)
        assert "try:" in source, f"{handler.__name__} missing try block"
        assert "except" in source, f"{handler.__name__} missing except block"
        assert "logger.error" in source, f"{handler.__name__} missing error logging"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
