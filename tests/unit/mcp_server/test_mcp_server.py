"""Unit tests for MCP server functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestMCPServerImport:
    """Test that MCP server can be imported."""

    def test_mcp_server_can_import(self):
        """Test that MCP server module can be imported without errors."""
        try:
            import mcp_server.server  # noqa: F401

            assert True  # If we get here, import succeeded
        except ImportError as e:
            pytest.fail(f"Failed to import MCP server: {e}")


class TestGetterFunctions:
    """Test MCP server getter functions return proper values."""

    @patch("graph.graph_storage.CodeGraphStorage")
    @patch("search.indexer.CodeIndexManager")
    @patch("mcp_server.storage_manager.get_project_storage_dir")
    def test_get_index_manager_returns_value(
        self, mock_get_storage, mock_index_manager_class, mock_graph_storage
    ):
        """Test that get_index_manager() returns a CodeIndexManager instance.

        This is a regression test for a bug where get_index_manager() was missing
        a return statement, causing it to return None instead of the manager object.
        """
        # Import here after mocks are set up
        from mcp_server import search_factory as server

        # Set up mocks - create a proper Path mock with mkdir method
        mock_storage_dir = MagicMock(spec=Path)
        mock_storage_dir.name = "project_abc123_1024d"
        mock_index_dir = MagicMock(spec=Path)
        mock_index_dir.mkdir = MagicMock()  # Mock mkdir to avoid file operations
        mock_storage_dir.__truediv__ = MagicMock(
            return_value=mock_index_dir
        )  # Mock / operator

        mock_get_storage.return_value = mock_storage_dir

        # Mock CodeGraphStorage to prevent production directory pollution
        mock_graph_instance = MagicMock()
        mock_graph_storage.return_value = mock_graph_instance

        mock_manager_instance = MagicMock()
        mock_index_manager_class.return_value = mock_manager_instance

        # Call the function
        result = server.get_index_manager("/mock/project/path")

        # Verify it returns the manager instance, not None
        assert result is not None, "get_index_manager() must return a value, not None"
        assert (
            result is mock_manager_instance
        ), "get_index_manager() must return the CodeIndexManager instance"

        # Verify the manager was created with correct parameters
        mock_index_manager_class.assert_called_once()
        call_args = mock_index_manager_class.call_args
        assert (
            "project_id" in call_args.kwargs
        ), "CodeIndexManager must be initialized with project_id"

    @patch("search.searcher.IntelligentSearcher")
    @patch("mcp_server.model_pool_manager.get_embedder")
    @patch("mcp_server.search_factory.SearchFactory.get_index_manager")
    @patch("search.config.get_search_config")
    def test_get_searcher_preserves_model_key_when_none_passed(
        self,
        mock_get_config,
        mock_get_index_manager,
        mock_get_embedder,
        mock_intelligent_searcher,
    ):
        """Verify get_searcher() preserves current_model_key when model_key=None.

        This is a regression test for the cross-model chunk_id lookup issue.
        When multi-model routing selects a model (e.g., qwen3), follow-up
        operations that call get_searcher() without model_key should preserve
        the routed model, not reset it to None.
        """
        # Import here after mocks are set up
        from mcp_server import search_factory as server
        from mcp_server.state import get_state

        # Mock config to disable hybrid search for simpler test
        mock_config = MagicMock()
        mock_config.search_mode.enable_hybrid = False
        mock_get_config.return_value = mock_config

        # Mock embedder
        mock_embedder = MagicMock()
        mock_get_embedder.return_value = mock_embedder

        # Mock index manager
        mock_index_mgr = MagicMock()
        mock_get_index_manager.return_value = mock_index_mgr

        # Mock IntelligentSearcher
        mock_searcher_instance = MagicMock()
        mock_intelligent_searcher.return_value = mock_searcher_instance

        # Get state and reset it
        state = get_state()
        state.current_project = "/mock/project"
        state.current_model_key = None
        state.searcher = None

        # Step 1: Simulate routing selecting a model (like handle_search_code does)
        searcher1 = server.get_searcher(model_key="qwen3")
        assert state.current_model_key == "qwen3", "Routing should set model to qwen3"
        assert searcher1 is mock_searcher_instance

        # Step 2: Call get_searcher without model_key (like follow-up operations do)
        # This should PRESERVE the qwen3 model, not reset it to None
        searcher2 = server.get_searcher()

        # Verify model was preserved
        assert (
            state.current_model_key == "qwen3"
        ), "Model should be preserved when model_key=None, not reset"

        # Verify searcher was reused (not recreated since model didn't change)
        assert searcher2 is searcher1, "Searcher should be reused when model unchanged"


# Note: Most MCP server functionality is tested in integration tests
# where the actual tool handlers and MCP framework are working properly.
# Unit tests here would just be testing mocks, not real functionality.


class TestToolHandlers:
    """Test MCP tool handlers return correct data."""

    @pytest.mark.asyncio
    @patch("search.config.get_search_config")
    async def test_get_search_config_includes_auto_reindex_fields(
        self, mock_get_search_config
    ):
        """Verify config status returns auto_reindex settings (Issue #3)."""
        from mcp_server.tool_handlers import handle_get_search_config_status

        # Mock config with nested structure
        mock_config = MagicMock()
        # Create nested sub-configs
        mock_config.search_mode.default_mode = "hybrid"
        mock_config.search_mode.bm25_weight = 0.4
        mock_config.search_mode.dense_weight = 0.6
        mock_config.search_mode.rrf_k_parameter = 60
        mock_config.search_mode.bm25_use_stemming = True
        mock_config.performance.use_parallel_search = True
        mock_config.performance.enable_auto_reindex = True
        mock_config.performance.max_index_age_minutes = 5.0
        mock_config.embedding.model_name = "BAAI/bge-m3"
        mock_config.multi_hop.enabled = True
        mock_config.multi_hop.hop_count = 5
        mock_config.multi_hop.expansion = 0.2
        mock_get_search_config.return_value = mock_config

        # Call handler
        with patch("mcp_server.tools.status_handlers.get_state") as mock_get_state:
            mock_state = MagicMock()
            mock_state.multi_model_enabled = False
            mock_get_state.return_value = mock_state

            result = await handle_get_search_config_status({})

        # Verify auto_reindex fields are present
        assert "auto_reindex_enabled" in result
        assert "max_index_age_minutes" in result
        assert isinstance(result["auto_reindex_enabled"], bool)
        assert isinstance(result["max_index_age_minutes"], (int, float))
        assert result["auto_reindex_enabled"] is True
        assert result["max_index_age_minutes"] == 5.0

    @pytest.mark.asyncio
    @patch("mcp_server.tools.status_handlers.SnapshotManager")
    @patch("mcp_server.tools.status_handlers.get_storage_dir")
    @patch("search.config.get_search_config")
    @patch("mcp_server.tools.status_handlers.get_index_manager")
    @patch("mcp_server.tools.status_handlers.get_state")
    async def test_get_index_status_includes_last_indexed_time(
        self,
        mock_get_state,
        mock_get_index_manager,
        mock_get_search_config,
        mock_get_storage_dir,
        mock_snapshot_manager_class,
    ):
        """Verify get_index_status returns last_indexed_time from Merkle metadata (Issue #2)."""
        from mcp_server.tool_handlers import handle_get_index_status

        # Mock state
        mock_state = MagicMock()
        mock_state.current_project = "/mock/project/path"
        mock_state.current_model_key = "default"
        mock_state.multi_model_enabled = False
        mock_state.embedders = {"default": None}
        mock_get_state.return_value = mock_state

        # Mock index manager
        mock_manager = MagicMock()
        mock_manager.get_stats.return_value = {
            "total_chunks": 100,
            "index_size": 100,
            "embedding_dimension": 768,
        }
        mock_get_index_manager.return_value = mock_manager

        # Mock search config
        mock_config = MagicMock()
        mock_config.search_mode.enable_hybrid = False
        mock_get_search_config.return_value = mock_config

        # Mock storage dir
        mock_get_storage_dir.return_value = Path("/mock/storage")

        # Mock SnapshotManager
        mock_snapshot_mgr = MagicMock()
        mock_snapshot_mgr.load_metadata.return_value = {
            "last_snapshot": "2025-12-06T10:30:00",
            "project_path": "/mock/project/path",
        }
        mock_snapshot_manager_class.return_value = mock_snapshot_mgr

        # Call handler
        result = await handle_get_index_status({})

        # Verify last_indexed_time is present
        assert "last_indexed_time" in result
        assert result["last_indexed_time"] == "2025-12-06T10:30:00"
        assert "current_project" in result
        assert result["current_project"] == "/mock/project/path"

        # Verify SnapshotManager was called
        mock_snapshot_manager_class.assert_called_once()
        mock_snapshot_mgr.load_metadata.assert_called_once_with("/mock/project/path")

    @pytest.mark.asyncio
    @patch("search.config.get_search_config")
    async def test_get_search_config_includes_multi_hop_and_stemming_fields(
        self, mock_get_search_config
    ):
        """Verify config status returns multi-hop and stemming settings."""
        from mcp_server.tool_handlers import handle_get_search_config_status

        # Mock config with nested structure
        mock_config = MagicMock()
        # Create nested sub-configs
        mock_config.search_mode.default_mode = "hybrid"
        mock_config.search_mode.bm25_weight = 0.4
        mock_config.search_mode.dense_weight = 0.6
        mock_config.search_mode.rrf_k_parameter = 60
        mock_config.search_mode.bm25_use_stemming = True
        mock_config.performance.use_parallel_search = True
        mock_config.performance.enable_auto_reindex = True
        mock_config.performance.max_index_age_minutes = 5.0
        mock_config.embedding.model_name = "BAAI/bge-m3"
        mock_config.multi_hop.enabled = True
        mock_config.multi_hop.hop_count = 2
        mock_config.multi_hop.expansion = 0.3
        mock_get_search_config.return_value = mock_config

        # Call handler
        with patch("mcp_server.tools.status_handlers.get_state") as mock_get_state:
            mock_state = MagicMock()
            mock_state.multi_model_enabled = False
            mock_get_state.return_value = mock_state

            result = await handle_get_search_config_status({})

        # Verify multi-hop and stemming fields are present
        assert "bm25_use_stemming" in result
        assert "multi_hop_enabled" in result
        assert "multi_hop_count" in result
        assert "multi_hop_expansion" in result
        assert isinstance(result["bm25_use_stemming"], bool)
        assert isinstance(result["multi_hop_enabled"], bool)
        assert isinstance(result["multi_hop_count"], int)
        assert isinstance(result["multi_hop_expansion"], float)
        assert result["bm25_use_stemming"] is True
        assert result["multi_hop_enabled"] is True
        assert result["multi_hop_count"] == 2
        assert result["multi_hop_expansion"] == 0.3

    @pytest.mark.asyncio
    @patch("mcp_server.tools.status_handlers.get_state")
    async def test_list_embedding_models_includes_vram(self, mock_get_state):
        """Verify list_embedding_models includes vram_gb field."""
        from mcp_server.tool_handlers import handle_list_embedding_models

        # Mock state
        mock_state = MagicMock()
        mock_get_state.return_value = mock_state

        # Mock get_search_config
        with patch("search.config.get_search_config") as mock_get_config:
            mock_config = MagicMock()
            mock_config.embedding.model_name = "BAAI/bge-m3"
            mock_get_config.return_value = mock_config

            # Call handler
            result = await handle_list_embedding_models({})

        # Verify vram_gb field is present in all models
        assert "models" in result
        assert len(result["models"]) > 0
        for model in result["models"]:
            assert "vram_gb" in model
            assert model["vram_gb"] is not None

    @pytest.mark.asyncio
    @patch("torch.cuda.is_available", return_value=True)
    @patch("torch.cuda.device_count", return_value=1)
    @patch("torch.cuda.memory_allocated", return_value=2147483648)
    @patch("torch.cuda.memory_reserved", return_value=3221225472)
    @patch("torch.cuda.get_device_name", return_value="NVIDIA GeForce RTX 4090")
    @patch("torch.cuda.get_device_properties")
    @patch("torch.cuda.get_device_capability", return_value=(8, 9))
    @patch("mcp_server.tools.status_handlers.get_state")
    async def test_get_memory_status_includes_gpu_details(
        self,
        mock_get_state,
        mock_capability,
        mock_properties,
        mock_device_name,
        mock_reserved,
        mock_allocated,
        mock_device_count,
        mock_cuda_available,
    ):
        """Verify memory status returns GPU hardware details."""
        from mcp_server.tool_handlers import handle_get_memory_status

        # Mock GPU properties
        mock_props = MagicMock()
        mock_props.total_memory = 25769803776  # 24 GB
        mock_properties.return_value = mock_props

        # Mock state
        mock_state = MagicMock()
        mock_state.current_project = "/mock/project"
        mock_state.current_model_key = "default"
        mock_state.embedders = {}
        mock_get_state.return_value = mock_state

        # Call handler
        result = await handle_get_memory_status({})

        # Verify GPU hardware details are present
        assert "gpu_memory" in result
        gpu = result["gpu_memory"]
        assert "gpu_0" in gpu
        gpu_0 = gpu["gpu_0"]
        assert "device_name" in gpu_0
        assert "device_id" in gpu_0
        assert "total_vram_gb" in gpu_0
        assert "compute_capability" in gpu_0
        assert "utilization_percent" in gpu_0
        assert gpu_0["device_name"] == "NVIDIA GeForce RTX 4090"
        assert gpu_0["compute_capability"] == "8.9"

    @pytest.mark.asyncio
    @patch("mcp_server.tools.search_handlers.get_state")
    async def test_search_code_no_project_selected(self, mock_get_state):
        """Test search_code returns graceful error when no project is selected."""
        from mcp_server.tools.search_handlers import handle_search_code

        # Mock state with no project selected
        mock_state = MagicMock()
        mock_state.current_project = None
        mock_get_state.return_value = mock_state

        # Call handler
        result = await handle_search_code({"query": "test query", "k": 5})

        # Verify graceful error response
        assert "error" in result
        assert "No indexed project found" in result["error"]
        assert result["current_project"] is None
        assert "index_directory" in result["message"]
        assert "system_message" in result

    @pytest.mark.asyncio
    @patch("mcp_server.tools.search_handlers.get_state")
    async def test_find_similar_code_no_project_selected(self, mock_get_state):
        """Test find_similar_code returns graceful error when no project is selected."""
        from mcp_server.tools.search_handlers import handle_find_similar_code

        # Mock state with no project selected
        mock_state = MagicMock()
        mock_state.current_project = None
        mock_get_state.return_value = mock_state

        # Call handler
        result = await handle_find_similar_code(
            {"chunk_id": "test.py:1-10:function:test_func"}
        )

        # Verify graceful error response
        assert "error" in result
        assert "No indexed project found" in result["error"]
        assert result["current_project"] is None
        assert "index_directory" in result["message"]

    @pytest.mark.asyncio
    @patch("mcp_server.tools.search_handlers.get_state")
    async def test_find_connections_no_project_selected(self, mock_get_state):
        """Test find_connections returns graceful error when no project is selected."""
        from mcp_server.tools.search_handlers import handle_find_connections

        # Mock state with no project selected
        mock_state = MagicMock()
        mock_state.current_project = None
        mock_get_state.return_value = mock_state

        # Call handler
        result = await handle_find_connections({"symbol_name": "TestClass"})

        # Verify graceful error response
        assert "error" in result
        assert "No indexed project found" in result["error"]
        assert result["current_project"] is None
        assert "index_directory" in result["message"]
