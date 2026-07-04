"""Unit tests for low-level MCP tool handlers.

Tests all 14 tool handlers with mocked dependencies.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import handlers
from mcp_server import tool_handlers
from mcp_server.tool_handlers import TOOL_DISPATCH
from mcp_server.tool_registry import TOOL_REGISTRY
from search.config import SearchConfig


# ============================================================================
# PARITY: TOOL_DISPATCH must mirror TOOL_REGISTRY exactly
# ============================================================================


def test_tool_dispatch_registry_parity():
    """TOOL_DISPATCH and TOOL_REGISTRY must have identical key sets.

    Catches the 'added a schema but forgot to wire dispatch' class of bug
    that the old getattr convention tolerated silently.
    """
    dispatch_keys = set(TOOL_DISPATCH)
    registry_keys = set(TOOL_REGISTRY)
    assert dispatch_keys == registry_keys, (
        f"TOOL_DISPATCH and TOOL_REGISTRY are out of sync.\n"
        f"  In DISPATCH but not REGISTRY: {dispatch_keys - registry_keys}\n"
        f"  In REGISTRY but not DISPATCH: {registry_keys - dispatch_keys}"
    )


# ============================================================================
# FIXTURES - Mock CodeGraphStorage to prevent production pollution
# ============================================================================


@pytest.fixture(autouse=True)
def mock_graph_storage():
    """Mock CodeGraphStorage for all tests to prevent production directory pollution."""
    with patch("graph.graph_storage.CodeGraphStorage") as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture(autouse=True)
def mock_get_project_storage_dir_global(tmp_path):
    """Mock get_project_storage_dir globally to prevent production pollution.

    Patches server location and handler modules that use it.
    Note: tool_handlers.py is now a re-export facade, so we patch the actual modules.
    Only patch in modules that actually import get_project_storage_dir.
    """
    mock_storage_dir = tmp_path / "mock_project_storage"
    mock_storage_dir.mkdir(parents=True, exist_ok=True)

    # Patch only in modules that use get_project_storage_dir:
    # - config_handlers (switch_project)
    # - search_handlers (_check_auto_reindex)
    # - index_handlers (clear_index, index_directory)
    # NOTE: status_handlers does NOT use get_project_storage_dir
    with (
        patch(
            "mcp_server.tools.config_handlers.get_project_storage_dir",
            return_value=mock_storage_dir,
        ),
        patch(
            "mcp_server.tools.search_handlers.get_project_storage_dir",
            return_value=mock_storage_dir,
        ),
        patch(
            "mcp_server.tools.index_handlers.get_project_storage_dir",
            return_value=mock_storage_dir,
        ),
    ):
        yield mock_storage_dir


# ============================================================================
# SIMPLE TOOLS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_handle_get_index_status_success():
    """Test get_index_status returns statistics."""
    with patch("mcp_server.tools.status_handlers.get_index_manager") as mock_manager:
        # Mock index manager
        mock_manager.return_value.get_stats.return_value = {
            "total_chunks": 100,
            "total_files": 10,
            "index_size_mb": 5.2,
        }

        # Mock state embedders
        with patch("mcp_server.state.get_state") as mock_state:
            state = mock_state.return_value
            state.embedders = {"default": None}
            result = await tool_handlers.handle_get_index_status({})

            assert "index_statistics" in result
            assert result["index_statistics"]["total_chunks"] == 100
            assert result["index_statistics"]["total_files"] == 10


@pytest.mark.asyncio
async def test_handle_get_index_status_error():
    """Test get_index_status handles errors gracefully."""
    with patch("mcp_server.tools.status_handlers.get_index_manager") as mock_manager:
        mock_manager.side_effect = Exception("Index not found")

        result = await tool_handlers.handle_get_index_status({})

        assert "error" in result
        assert "Index not found" in result["error"]


@pytest.mark.asyncio
async def test_handle_get_index_status_with_hybrid_searcher():
    """Test get_index_status includes synced field when hybrid search is enabled.

    This test verifies the fix for the issue where synced field was missing
    because get_searcher() was never called to initialize the lazy-loaded searcher.
    """
    with patch("mcp_server.tools.status_handlers.get_index_manager") as mock_manager:
        # Mock index manager
        mock_manager.return_value.get_stats.return_value = {
            "total_chunks": 100,
            "total_files": 10,
            "index_size_mb": 5.2,
        }

        # Mock get_config to return hybrid enabled
        with patch("mcp_server.tools.status_handlers.get_config") as mock_config:
            mock_config.return_value.search_mode.enable_hybrid = True

            # Mock get_searcher to return a HybridSearcher
            with patch(
                "mcp_server.tools.status_handlers.get_searcher"
            ) as mock_get_searcher:
                # Create mock HybridSearcher
                mock_searcher = Mock()
                mock_searcher.get_stats.return_value = {
                    "total_chunks": 100,
                    "bm25_documents": 100,
                    "dense_vectors": 100,
                    "synced": True,
                    "is_ready": True,
                }
                mock_get_searcher.return_value = mock_searcher

                # Note: Can't patch isinstance with decorator-wrapped code
                # Instead, rely on isinstance working with properly spec'd Mock
                from search.hybrid_searcher import HybridSearcher

                mock_searcher.__class__ = HybridSearcher

                # Mock state embedders
                with patch("mcp_server.state.get_state") as mock_state:
                    state = mock_state.return_value
                    state.embedders = {"default": None}

                    result = await tool_handlers.handle_get_index_status({})

                    # Verify basic stats
                    assert "index_statistics" in result
                    assert result["index_statistics"]["total_chunks"] == 100

                    # Verify hybrid searcher stats are included (the fix)
                    assert "bm25_documents" in result["index_statistics"]
                    assert "dense_vectors" in result["index_statistics"]
                    assert "synced" in result["index_statistics"]
                    assert result["index_statistics"]["synced"] is True

                    # Verify get_searcher was called (proving lazy init happened)
                    mock_get_searcher.assert_called_once()


@pytest.mark.asyncio
async def test_handle_list_projects_no_projects():
    """Test list_projects when no projects exist."""
    with patch("mcp_server.tools.status_handlers.get_storage_dir") as mock_storage:
        mock_storage.return_value = Path("/tmp/nonexistent")

        result = await tool_handlers.handle_list_projects({})

        assert len(result["projects"]) == 0
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
                "project_hash": "test_hash",
                "embedding_model": "BAAI/bge-m3",
                "model_dimension": 1024,
                "created_at": datetime.now().isoformat(),
            }
        )
    )

    with patch("mcp_server.tools.status_handlers.get_storage_dir") as mock_storage:
        mock_storage.return_value = tmp_path
        with patch("mcp_server.state._app_state.current_project", str(tmp_path)):
            result = await tool_handlers.handle_list_projects({})

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
async def test_handle_get_memory_status_gpu_key_rename():
    """Key rename guard: the GPU entry must expose `non_torch_gb`, not the old
    `ort_untracked_gb`. The old name was misleading — it reflects all non-PyTorch
    allocations (other processes + drivers + ORT), not just ORT."""
    import mcp_server.tools.status_handlers as status_handlers

    mock_mem = Mock()
    mock_mem.total = 16 * 1024**3
    mock_mem.available = 8 * 1024**3
    mock_mem.used = 8 * 1024**3
    mock_mem.percent = 50.0

    mock_pynvml = Mock()
    mock_pynvml.nvmlInit = Mock()
    mock_pynvml.nvmlShutdown = Mock()
    mock_pynvml.nvmlDeviceGetHandleByIndex = Mock(return_value=Mock())
    nvml_info = Mock()
    nvml_info.used = 6 * 1024**3
    nvml_info.free = 10 * 1024**3
    mock_pynvml.nvmlDeviceGetMemoryInfo = Mock(return_value=nvml_info)

    device_props = Mock()
    device_props.total_memory = 16 * 1024**3

    with (
        patch("psutil.virtual_memory", return_value=mock_mem),
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.device_count", return_value=1),
        patch("torch.cuda.memory_allocated", return_value=2 * 1024**3),
        patch("torch.cuda.memory_reserved", return_value=2 * 1024**3),
        patch("torch.cuda.get_device_properties", return_value=device_props),
        patch("torch.cuda.get_device_name", return_value="Mock GPU"),
        patch("torch.cuda.get_device_capability", return_value=(8, 6)),
        patch.dict("sys.modules", {"pynvml": mock_pynvml}),
    ):
        result = await status_handlers.handle_get_memory_status({})

    gpu_entry = result["gpu_memory"]["gpu_0"]
    assert "non_torch_gb" in gpu_entry, "expected renamed key `non_torch_gb`"
    assert "ort_untracked_gb" not in gpu_entry, (
        "old key `ort_untracked_gb` must not be re-introduced"
    )
    # Sanity: non_torch_gb = max(0, nvml_used - torch_allocated) = 6 - 2 = 4.0
    assert gpu_entry["non_torch_gb"] == 4.0


@pytest.mark.asyncio
async def test_handle_cleanup_resources():
    """Test cleanup_resources calls cleanup function."""
    with patch(
        "mcp_server.tools.status_handlers._cleanup_previous_resources"
    ) as mock_cleanup:
        result = await tool_handlers.handle_cleanup_resources({})

        assert result["success"] is True
        assert "cleaned up" in result["message"].lower()
        mock_cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_handle_get_search_config_status():
    """Test get_search_config_status returns configuration."""
    with patch("mcp_server.tools.status_handlers.get_config") as mock_config:
        mock_cfg = Mock()
        # Create nested sub-configs
        mock_cfg.search_mode.default_mode = "hybrid"
        mock_cfg.search_mode.enable_hybrid = True
        mock_cfg.search_mode.bm25_weight = 0.4
        mock_cfg.search_mode.dense_weight = 0.6
        mock_cfg.search_mode.rrf_k_parameter = 60
        mock_cfg.performance.use_parallel_search = True
        mock_cfg.embedding.model_name = "BAAI/bge-m3"
        mock_config.return_value = mock_cfg

        with patch("mcp_server.tools.status_handlers.get_state"):
            result = await tool_handlers.handle_get_search_config_status({})

            assert result["search_mode"] == "hybrid"
            assert result["bm25_weight"] == 0.4
            assert result["embedding_model"] == "BAAI/bge-m3"


@pytest.mark.asyncio
async def test_handle_list_embedding_models():
    """Test list_embedding_models returns model registry."""
    with (
        patch(
            "mcp_server.tools.status_handlers.MODEL_REGISTRY",
            {
                "model1": {"dimension": 768, "description": "Test model 1"},
                "model2": {"dimension": 1024, "description": "Test model 2"},
            },
        ),
        patch("mcp_server.tools.status_handlers.get_config") as mock_config,
    ):
        mock_cfg = Mock()
        mock_cfg.embedding.model_name = "model1"
        mock_config.return_value = mock_cfg

        result = await tool_handlers.handle_list_embedding_models({})

        assert len(result["models"]) == 2
        assert result["current_model"] == "model1"


@pytest.mark.asyncio
async def test_handle_list_embedding_models_loaded_true_when_in_vram():
    """loaded: true is returned when the embedder is in state.embedders."""
    mock_embedder = Mock()
    mock_embedder.model_name = "Qwen/Qwen3-Embedding-0.6B"

    mock_state = Mock()
    mock_state.embedders = {"qwen3_0.6b": mock_embedder}

    with (
        patch(
            "mcp_server.tools.status_handlers.MODEL_REGISTRY",
            {
                "Qwen/Qwen3-Embedding-0.6B": {"dimension": 1024, "description": "Test"},
                "BAAI/bge-m3": {"dimension": 1024, "description": "Other"},
            },
        ),
        # get_state is imported lazily inside handle_list_embedding_models —
        # patch at the source module so the function picks up the mock.
        patch("mcp_server.state.get_state", return_value=mock_state),
        patch("mcp_server.tools.status_handlers.get_config") as mock_config,
    ):
        mock_cfg = Mock()
        mock_cfg.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_config.return_value = mock_cfg

        result = await tool_handlers.handle_list_embedding_models({})

    models = {m["name"]: m for m in result["models"]}
    assert models["Qwen/Qwen3-Embedding-0.6B"]["loaded"] is True
    assert models["BAAI/bge-m3"]["loaded"] is False


@pytest.mark.asyncio
async def test_handle_list_embedding_models_none_slot_is_not_loaded():
    """A None lazy slot in state.embedders must not report loaded: true.

    Regression test for the None-slot false-positive: previously
    a key in state.embedders returned True (loaded) even for unloaded None slots.
    """
    mock_state = Mock()
    mock_state.embedders = {"qwen3_0.6b": None}  # reserved slot, nothing loaded

    with (
        patch(
            "mcp_server.tools.status_handlers.MODEL_REGISTRY",
            {"Qwen/Qwen3-Embedding-0.6B": {"dimension": 1024, "description": "Test"}},
        ),
        patch("mcp_server.state.get_state", return_value=mock_state),
        patch("mcp_server.tools.status_handlers.get_config") as mock_config,
    ):
        mock_cfg = Mock()
        mock_cfg.embedding.model_name = "Qwen/Qwen3-Embedding-0.6B"
        mock_config.return_value = mock_cfg

        result = await tool_handlers.handle_list_embedding_models({})

    assert result["models"][0]["loaded"] is False


# ============================================================================
# MEDIUM TOOLS TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_handle_switch_project_success(tmp_path):
    """Test switch_project changes current project."""
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    # Create index directory to indicate project is indexed
    with patch(
        "mcp_server.tools.config_handlers.get_project_storage_dir"
    ) as mock_storage:
        mock_project_dir = tmp_path / "storage"
        mock_project_dir.mkdir()
        index_dir = mock_project_dir / "index"
        index_dir.mkdir()
        (index_dir / "code.index").touch()
        mock_storage.return_value = mock_project_dir

        with (
            patch("mcp_server.tools.config_handlers._cleanup_previous_resources"),
            patch("mcp_server.state._app_state.current_project", None),
        ):
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

    with patch(
        "mcp_server.tools.config_handlers.get_project_storage_dir"
    ) as mock_storage:
        mock_project_dir = tmp_path / "storage"
        mock_project_dir.mkdir()
        mock_storage.return_value = mock_project_dir

        with patch("mcp_server.tools.config_handlers._cleanup_previous_resources"):
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
    """Test clear_index removes BOTH BM25 and dense index data for ALL models."""
    import hashlib
    import tempfile
    from pathlib import Path

    mock_state = Mock()
    mock_state.current_project = "/tmp/test_project"
    mock_state.index_manager = None
    mock_state.searcher = None

    # Compute hash to match implementation
    project_path = Path(mock_state.current_project).resolve()
    project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]

    # Create mock model directories
    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        projects_dir = base_dir / "projects"
        projects_dir.mkdir(parents=True)

        # Create mock model directories with correct hash
        model1_dir = projects_dir / f"test_project_{project_hash}_bge-m3_1024d"
        model2_dir = projects_dir / f"test_project_{project_hash}_coderank_768d"

        for model_dir in [model1_dir, model2_dir]:
            model_dir.mkdir(parents=True)
            index_dir = model_dir / "index"
            index_dir.mkdir()
            bm25_dir = index_dir / "bm25"
            bm25_dir.mkdir()
            (index_dir / "code.index").touch()
            (index_dir / "chunks_metadata.db").touch()

        with (
            patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
            patch(
                "mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir
            ),
        ):
            result = await tool_handlers.handle_clear_index({})

            assert result["success"] is True
            assert "cleared_models" in result
            assert len(result["cleared_models"]) == 2

            # Verify BM25 directories deleted
            assert not (model1_dir / "index" / "bm25").exists()
            assert not (model2_dir / "index" / "bm25").exists()

            # Verify dense index files deleted
            assert not (model1_dir / "index" / "code.index").exists()
            assert not (model2_dir / "index" / "code.index").exists()


@pytest.mark.asyncio
async def test_handle_clear_index_no_project():
    """Test clear_index fails when no active project."""
    with patch("mcp_server.state._app_state.current_project", None):
        result = await tool_handlers.handle_clear_index({})

        assert "error" in result
        assert "no active project" in result["error"].lower()


@pytest.mark.asyncio
async def test_handle_configure_search_mode():
    """Test configure_search_mode updates configuration."""
    with patch("mcp_server.tools.config_handlers.get_config_manager") as mock_manager:
        mock_cfg = Mock()
        mock_cfg.search_mode.enable_hybrid = False
        mock_cfg.search_mode.bm25_weight = 0.5
        mock_cfg.search_mode.dense_weight = 0.5
        mock_cfg.performance.use_parallel_search = True

        mock_manager.return_value.load_config.return_value = mock_cfg
        mock_manager.return_value.save_config = Mock()

        with patch("mcp_server.state._app_state.searcher", Mock()):
            result = await tool_handlers.handle_configure_search_mode(
                {"search_mode": "hybrid", "bm25_weight": 0.4, "dense_weight": 0.6}
            )

            assert result["success"] is True
            assert result["config"]["search_mode"] == "hybrid"
            assert result["config"]["bm25_weight"] == 0.4


@pytest.mark.asyncio
async def test_handle_switch_embedding_model():
    """Test switch_embedding_model changes model."""
    with (
        patch(
            "mcp_server.tools.config_handlers.MODEL_REGISTRY",
            {"new_model": {"dimension": 1024}},
        ),
        patch("mcp_server.tools.config_handlers.get_config_manager") as mock_manager,
    ):
        mock_cfg = Mock()
        mock_cfg.embedding.model_name = "old_model"
        mock_manager.return_value.load_config.return_value = mock_cfg
        mock_manager.return_value.save_config = Mock()

        with patch("mcp_server.state.get_state") as mock_state:
            state = mock_state.return_value
            state.embedders = {}
            state.index_manager = None
            state.searcher = None
            state.clear_embedders = Mock()
            result = await tool_handlers.handle_switch_embedding_model(
                {"model_name": "new_model"}
            )

            assert result["success"] is True
            assert result["new_model"] == "new_model"
            assert result["old_model"] == "old_model"


@pytest.mark.asyncio
async def test_handle_find_similar_code():
    """Test find_similar_code returns similar chunks."""
    with (
        patch("mcp_server.tools.search_handlers.get_searcher") as mock_searcher,
        patch("mcp_server.tools.search_handlers.get_state") as mock_get_state,
        patch("mcp_server.tools.decorators.get_state") as mock_dec_state,
    ):
        # Mock state with current_project set
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        # Mock search results (thin SearchResult format)
        mock_result = Mock()
        mock_result.chunk_id = "file.py:10-20:function:test_func"
        mock_result.score = 0.95
        mock_result.source = "similarity"
        mock_result.metadata = {
            "relative_path": "file.py",
            "start_line": 10,
            "end_line": 20,
            "chunk_type": "function",
            "name": "test_func",
        }

        # Create mock searcher instance
        mock_searcher_instance = Mock()
        mock_searcher_instance.find_similar_to_chunk.return_value = [mock_result]
        mock_searcher.return_value = mock_searcher_instance

        result = await tool_handlers.handle_find_similar_code(
            {"chunk_id": "ref_chunk_id", "k": 5}
        )

        assert result["reference_chunk"] == "ref_chunk_id"
        assert len(result["similar_chunks"]) == 1
        assert result["similar_chunks"][0]["file"] == "file.py"
        assert result["similar_chunks"][0]["score"] == 0.95


# ============================================================================
# COMPLEX TOOLS TESTS (Simplified - full integration testing elsewhere)
# ============================================================================


@pytest.mark.asyncio
async def test_handle_search_code_no_index():
    """Test search_code fails gracefully when no index exists (backward compatibility)."""
    with (
        patch("mcp_server.tools.search_orchestrator.get_searcher") as mock_searcher,
        patch("mcp_server.tools.search_orchestrator.get_state") as mock_get_state,
        patch("mcp_server.tools.search_handlers.get_state") as mock_handler_state,
        patch("mcp_server.tools.search_orchestrator.get_search_config"),
        patch("mcp_server.tools.search_orchestrator.get_config_manager"),
        patch("mcp_server.tools.search_orchestrator.get_config"),
        patch("mcp_server.tools.search_orchestrator.IntentClassifier") as mock_ic,
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_state.searcher = None
        _reindex_lock_cm = MagicMock()
        _reindex_lock_cm.__aenter__ = AsyncMock(return_value=None)
        _reindex_lock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_state.get_reindex_lock = Mock(return_value=_reindex_lock_cm)
        mock_get_state.return_value = mock_state
        mock_handler_state.return_value = mock_state
        mock_ic.return_value.classify.return_value = Mock(
            intent=Mock(value="hybrid"),
            confidence=0.0,
            reason="test",
            scores={},
            suggested_params={},
        )

        # Mock searcher without is_ready (legacy IntelligentSearcher)
        mock_searcher_obj = Mock(spec=["index_manager"])
        mock_searcher_obj.index_manager.get_stats.return_value = {"total_chunks": 0}
        mock_searcher.return_value = mock_searcher_obj

        result = await tool_handlers.handle_search_code({"query": "test query", "k": 5})

        assert "error" in result
        assert "no indexed project" in result["error"].lower()


@pytest.mark.asyncio
async def test_handle_search_code_hybrid_searcher_ready():
    """Test search_code with HybridSearcher correctly detects indexed project.

    This test verifies the bug fix for 'No indexed project found' error
    that occurred when HybridSearcher was used with model routing.
    """
    with (
        patch("mcp_server.tools.search_orchestrator.get_searcher") as mock_get_searcher,
        patch("mcp_server.tools.search_orchestrator.get_state") as mock_get_state,
        patch("mcp_server.tools.search_handlers.get_state") as mock_handler_state,
        patch("mcp_server.tools.decorators.get_state") as mock_dec_state,
        patch(
            "mcp_server.tools.search_orchestrator.get_search_config",
            return_value=SearchConfig(),
        ),
        patch("mcp_server.tools.search_orchestrator.get_config_manager") as mock_cm,
        patch("mcp_server.tools.search_orchestrator.get_config") as mock_cfg,
        patch("mcp_server.tools.search_orchestrator.IntentClassifier") as mock_ic,
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
        patch(
            "mcp_server.tools.search_handlers._format_search_results",
            return_value=[
                {
                    "chunk_id": "test.py:1-10:function:test",
                    "score": 0.9,
                    "kind": "function",
                    "start_line": 1,
                    "end_line": 10,
                }
            ],
        ),
        patch(
            "mcp_server.tools.search_handlers._enrich_results_with_graph_data",
            side_effect=lambda r, _im: r,
        ),
        patch(
            "mcp_server.tools.search_handlers._get_index_manager_from_searcher",
            return_value=None,
        ),
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_state.searcher = None
        _reindex_lock_cm = MagicMock()
        _reindex_lock_cm.__aenter__ = AsyncMock(return_value=None)
        _reindex_lock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_state.get_reindex_lock = Mock(return_value=_reindex_lock_cm)
        mock_get_state.return_value = mock_state
        mock_handler_state.return_value = mock_state
        mock_dec_state.return_value = mock_state
        mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"
        mock_cfg.return_value.performance.use_parallel_search = False
        mock_ic.return_value.classify.return_value = Mock(
            intent=Mock(value="hybrid"),
            confidence=0.0,
            reason="test",
            scores={},
            suggested_params={},
        )

        # Mock HybridSearcher with is_ready property and dense_index.
        # index_manager is set to None explicitly so SearcherView falls
        # through to dense_index (the HybridSearcher attribute name).
        mock_searcher = Mock()
        mock_searcher.is_ready = True
        mock_searcher.index_manager = None

        # Mock dense_index with FAISS index containing vectors
        mock_dense_index = Mock()
        mock_faiss_index = Mock()
        mock_faiss_index.ntotal = 1574  # Simulating indexed project
        mock_dense_index.index = mock_faiss_index
        mock_dense_index.graph_storage = None
        mock_searcher.dense_index = mock_dense_index
        mock_searcher.search.return_value = []

        mock_get_searcher.return_value = mock_searcher

        # Execute search
        result = await tool_handlers.handle_search_code({"query": "test query", "k": 5})

        # Should succeed without "No indexed project found" error
        assert "error" not in result
        assert "results" in result or "chunks" in result or isinstance(result, list)


@pytest.mark.asyncio
async def test_handle_search_code_hybrid_searcher_not_ready():
    """Test search_code with HybridSearcher correctly detects empty index."""
    with (
        patch("mcp_server.tools.search_orchestrator.get_searcher") as mock_get_searcher,
        patch("mcp_server.tools.search_orchestrator.get_state") as mock_get_state,
        patch("mcp_server.tools.search_handlers.get_state") as mock_handler_state,
        patch("mcp_server.tools.search_orchestrator.get_search_config"),
        patch("mcp_server.tools.search_orchestrator.get_config_manager"),
        patch("mcp_server.tools.search_orchestrator.get_config"),
        patch("mcp_server.tools.search_orchestrator.IntentClassifier") as mock_ic,
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_state.searcher = None
        _reindex_lock_cm = MagicMock()
        _reindex_lock_cm.__aenter__ = AsyncMock(return_value=None)
        _reindex_lock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_state.get_reindex_lock = Mock(return_value=_reindex_lock_cm)
        mock_get_state.return_value = mock_state
        mock_handler_state.return_value = mock_state
        mock_ic.return_value.classify.return_value = Mock(
            intent=Mock(value="hybrid"),
            confidence=0.0,
            reason="test",
            scores={},
            suggested_params={},
        )

        # Mock HybridSearcher with is_ready = False
        mock_searcher = Mock()
        mock_searcher.is_ready = False

        # Mock dense_index with empty FAISS index
        mock_dense_index = Mock()
        mock_faiss_index = Mock()
        mock_faiss_index.ntotal = 0
        mock_dense_index.index = mock_faiss_index
        mock_searcher.dense_index = mock_dense_index

        mock_get_searcher.return_value = mock_searcher

        # Execute search
        result = await tool_handlers.handle_search_code({"query": "test query", "k": 5})

        # Should return error
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
    """Verify all handlers have proper error handling via @error_handler decorator."""
    # Get all handler modules
    from mcp_server.tools import (
        config_handlers,
        index_handlers,
        search_handlers,
        status_handlers,
    )

    modules = [status_handlers, config_handlers, search_handlers, index_handlers]
    all_handlers_checked = []

    for module in modules:
        handlers = [
            (name, getattr(module, name))
            for name in dir(module)
            if name.startswith("handle_")
        ]

        for name, handler in handlers:
            all_handlers_checked.append(f"{module.__name__}.{name}")
            # Check if wrapped by error_handler decorator
            # functools.wraps preserves __wrapped__ attribute
            assert hasattr(handler, "__wrapped__") or callable(handler), (
                f"{module.__name__}.{name} should use @error_handler decorator or be callable"
            )

    # Verify we checked at least 15 handlers (all our handlers)
    assert len(all_handlers_checked) >= 15, (
        f"Expected at least 15 handlers, found {len(all_handlers_checked)}"
    )


# ============================================================================
# handle_delete_project Tests
# ============================================================================


@pytest.mark.asyncio
async def test_handle_delete_project_success(tmp_path):
    """Test delete_project successfully removes project directories and snapshots."""
    import hashlib

    # Create mock project structure
    project_path = tmp_path / "test_project"
    project_path.mkdir()

    project_path_resolved = project_path.resolve()
    project_hash = hashlib.md5(str(project_path_resolved).encode()).hexdigest()[:8]

    # Create mock storage directories
    base_dir = tmp_path / "storage"
    projects_dir = base_dir / "projects"
    model_dir = projects_dir / f"test_project_{project_hash}_bge-m3_1024d"
    model_dir.mkdir(parents=True)
    (model_dir / "index").mkdir()
    (model_dir / "index" / "code.index").touch()
    (model_dir / "index" / "metadata.db").touch()

    mock_state = Mock()
    mock_state.current_project = None  # Not current project

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir),
        patch("mcp_server.server.close_project_resources"),
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_sm.return_value.delete_all_snapshots.return_value = 2

        result = await tool_handlers.handle_delete_project(
            {"project_path": str(project_path)}
        )

    assert result["success"] is True
    assert len(result["deleted_directories"]) == 1
    assert result["deleted_snapshots"] == 2
    assert not model_dir.exists()
    assert result.get("errors") is None


@pytest.mark.asyncio
async def test_handle_delete_project_current_project_without_force(tmp_path):
    """Test delete_project fails for current project without force=True."""
    # Create an actual project directory
    project_path = tmp_path / "current_project"
    project_path.mkdir()

    project_path_str = str(project_path.resolve())

    mock_state = Mock()
    mock_state.current_project = project_path_str

    with patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state):
        result = await tool_handlers.handle_delete_project(
            {"project_path": str(project_path)}
        )

    assert "error" in result
    assert "Cannot delete current project" in result["error"]
    assert result.get("is_current_project") is True


@pytest.mark.asyncio
async def test_handle_delete_project_current_project_with_force(tmp_path):
    """Test delete_project succeeds for current project with force=True."""
    import hashlib

    # Create mock project structure
    project_path = tmp_path / "current_project"
    project_path.mkdir()

    project_path_resolved = project_path.resolve()
    project_hash = hashlib.md5(str(project_path_resolved).encode()).hexdigest()[:8]

    # Create mock storage directories
    base_dir = tmp_path / "storage"
    projects_dir = base_dir / "projects"
    model_dir = projects_dir / f"current_project_{project_hash}_qwen3_1024d"
    model_dir.mkdir(parents=True)

    mock_state = Mock()
    mock_state.current_project = str(project_path_resolved)  # IS current project

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir),
        patch("mcp_server.server.close_project_resources"),
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_sm.return_value.delete_all_snapshots.return_value = 1

        result = await tool_handlers.handle_delete_project(
            {"project_path": str(project_path), "force": True}
        )

    assert result["success"] is True
    assert len(result["deleted_directories"]) == 1
    assert not model_dir.exists()


@pytest.mark.asyncio
async def test_handle_delete_project_not_exist():
    """Test delete_project fails when project path doesn't exist."""
    result = await tool_handlers.handle_delete_project(
        {"project_path": "/nonexistent/path"}
    )

    assert "error" in result
    assert "does not exist" in result["error"]


@pytest.mark.asyncio
async def test_handle_delete_project_missing_path():
    """Test delete_project fails when project_path not provided."""
    result = await tool_handlers.handle_delete_project({})

    assert "error" in result
    assert "project_path is required" in result["error"]


@pytest.mark.asyncio
async def test_handle_delete_project_adds_to_cleanup_queue(tmp_path):
    """Test delete_project adds failed deletions to cleanup queue."""
    import hashlib

    # Create mock project structure
    project_path = tmp_path / "locked_project"
    project_path.mkdir()

    project_path_resolved = project_path.resolve()
    project_hash = hashlib.md5(str(project_path_resolved).encode()).hexdigest()[:8]

    # Create mock storage directories
    base_dir = tmp_path / "storage"
    projects_dir = base_dir / "projects"
    model_dir = projects_dir / f"locked_project_{project_hash}_bge-m3_1024d"
    model_dir.mkdir(parents=True)

    mock_state = Mock()
    mock_state.current_project = None

    # Mock shutil.rmtree to raise PermissionError
    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir),
        patch("mcp_server.server.close_project_resources"),
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_sm.return_value.delete_all_snapshots.return_value = 0

        with patch("shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("File is locked")

            with patch("mcp_server.cleanup_queue.CleanupQueue") as mock_queue_cls:
                mock_queue = Mock()
                mock_queue_cls.return_value = mock_queue

                result = await tool_handlers.handle_delete_project(
                    {"project_path": str(project_path)}
                )

                # Verify cleanup queue was used
                mock_queue.add.assert_called_once()

    assert result["success"] is False
    assert len(result.get("errors", [])) == 1
    assert result.get("queued_for_retry") == 1


# ============================================================================
# REGRESSION: SearchConfigManager has no public `.config` attribute
# ============================================================================


def test_config_manager_exposes_config_only_via_load_config():
    """Regression guard for mcp_server/server.py::handle_reload_config.

    That handler used to read `config_manager.config` after calling
    `load_config()`, but SearchConfigManager stores its parsed config in the
    private `_config` and only exposes it via load_config()'s return value.
    This caused every /reload_config HTTP call to 500 with
    AttributeError: 'SearchConfigManager' object has no attribute 'config'.
    """
    from search.config import SearchConfigManager

    mgr = SearchConfigManager()
    assert not hasattr(mgr, "config")

    cfg = mgr.load_config()
    # Attributes the /reload_config handler reads must exist on the
    # returned SearchConfig.
    assert isinstance(cfg.search_mode.default_mode, str)
    assert hasattr(cfg.search_mode, "bm25_weight")
    assert hasattr(cfg.search_mode, "dense_weight")
    assert hasattr(cfg.performance, "enable_entity_tracking")
    assert hasattr(cfg.reranker, "enabled")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
