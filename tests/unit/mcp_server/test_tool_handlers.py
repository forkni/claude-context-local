"""Unit tests for low-level MCP tool handlers.

Tests all 18 tool handlers with mocked dependencies.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import handlers
from mcp_server import tool_specs
from search.config import SearchConfig


# Structural guard coverage (ToolSpec.mutation_lock / .requires_index vs. each
# handler's actual decorator chain) now lives in
# tests/unit/mcp_server/test_tool_specs.py's TestGuardFlagsDerivedFromDecoratorStamps
# -- since docs/adr/0057, those flags are derived properties reading the
# handler's __mcp_guards__ stamp rather than hand-typed fields, so there is no
# longer a second declaration that could drift from the decorator chain.


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
    Note: tool_specs.py re-exports each handler by name (not a facade around
    a separate implementation module), so we patch the actual handler
    modules where get_project_storage_dir is imported, not tool_specs.py.
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
            result = await tool_specs.handle_get_index_status({})

            assert "index_statistics" in result
            assert result["index_statistics"]["total_chunks"] == 100
            assert result["index_statistics"]["total_files"] == 10


@pytest.mark.asyncio
async def test_handle_get_index_status_error():
    """Test get_index_status handles errors gracefully."""
    with patch("mcp_server.tools.status_handlers.get_index_manager") as mock_manager:
        mock_manager.side_effect = Exception("Index not found")

        result = await tool_specs.handle_get_index_status({})

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

                    result = await tool_specs.handle_get_index_status({})

                    # Verify basic stats
                    assert "index_statistics" in result
                    assert result["index_statistics"]["total_chunks"] == 100

                    # Verify hybrid searcher stats are included (the fix)
                    assert "bm25_documents" in result["index_statistics"]
                    assert "dense_vectors" in result["index_statistics"]
                    assert "synced" in result["index_statistics"]
                    assert result["index_statistics"]["synced"] is True
                    # bm25_documents/dense_vectors/synced above come exclusively
                    # from mock_searcher.get_stats.return_value, and mock_searcher
                    # is exclusively reachable via mock_get_searcher.return_value --
                    # those checks already prove get_searcher() fired (lazy init),
                    # so a separate assert_called_once() would be redundant.


@pytest.mark.asyncio
async def test_handle_get_index_status_with_job_id_reports_job_status():
    """P2-A: get_index_status(job_id=...) polls a background index_directory job
    instead of returning the regular index snapshot.
    """
    from mcp_server.tools.job_registry import get_job_registry

    registry = get_job_registry()
    job = await registry.create(kind="index_directory", target="/proj")
    await registry.mark_done(job.job_id, {"chunks_added": 5})

    result = await tool_specs.handle_get_index_status({"job_id": job.job_id})

    assert result["status"] == "done"
    assert result["result"] == {"chunks_added": 5}
    assert result["job_id"] == job.job_id


@pytest.mark.asyncio
async def test_handle_get_index_status_unknown_job_id_returns_error():
    result = await tool_specs.handle_get_index_status({"job_id": "does-not-exist"})

    assert "error" in result
    assert "does-not-exist" in result["error"]


@pytest.mark.asyncio
async def test_handle_list_projects_no_projects():
    """Test list_projects when no projects exist."""
    with patch("mcp_server.tools.status_handlers.get_storage_dir") as mock_storage:
        mock_storage.return_value = Path("/tmp/nonexistent")

        result = await tool_specs.handle_list_projects({})

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

    with (
        patch("mcp_server.tools.status_handlers.get_storage_dir") as mock_storage,
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        # Without this, SnapshotManager() constructs for real inside
        # handle_list_projects and reads/writes the developer's actual
        # ~/.claude_code_search/merkle directory -- a test-isolation leak
        # (defect 3, see docs/adr/0058-index-freshness-verdict.md).
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
    ):
        mock_storage.return_value = tmp_path
        mock_snapshot_cls.return_value = Mock(load_metadata=Mock(return_value=None))

        result = await tool_specs.handle_list_projects({})

        assert len(result["projects"]) == 1
        assert result["projects"][0]["project_name"] == "test_project"


def _write_project_info(
    project_dir: Path,
    *,
    project_path: str,
    embedding_model: str = "BAAI/bge-m3",
    model_dimension: int = 1024,
    created_at: str,
) -> None:
    """Write a project_info.json fixture matching storage_manager's real schema."""
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project_info.json").write_text(
        json.dumps(
            {
                "project_name": Path(project_path).name,
                "project_path": project_path,
                "project_hash": "test_hash",
                "embedding_model": embedding_model,
                "model_dimension": model_dimension,
                "created_at": created_at,
            }
        )
    )


@pytest.mark.asyncio
async def test_handle_list_projects_includes_last_indexed_at(tmp_path):
    """list_projects surfaces last_indexed_at from Merkle metadata (last_snapshot),
    alongside the pre-existing created_at field.
    """
    projects_dir = tmp_path / "projects"
    _write_project_info(
        projects_dir / "test_project",
        project_path=str(tmp_path),
        created_at="2026-08-22T13:12:06.243607",
    )

    with (
        patch(
            "mcp_server.tools.status_handlers.get_storage_dir", return_value=tmp_path
        ),
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
    ):
        mock_snapshot_mgr = Mock()
        mock_snapshot_mgr.load_metadata.return_value = {
            "last_snapshot": "2026-08-30T17:55:07.290674",
        }
        mock_snapshot_cls.return_value = mock_snapshot_mgr

        result = await tool_specs.handle_list_projects({})

    model_info = result["projects"][0]["models_indexed"][0]
    assert model_info["created_at"] == "2026-08-22T13:12:06.243607"
    assert model_info["last_indexed_at"] == "2026-08-30T17:55:07.290674"


@pytest.mark.asyncio
async def test_handle_list_projects_created_at_frozen_while_last_indexed_at_advances(
    tmp_path,
):
    """Regression test for the false-staleness bug: project_info.json's created_at
    is written once at first index and never updated by later re-indexing, so it
    must NOT be read as a freshness signal. Simulates a re-index (Merkle
    last_snapshot advances) while project_info.json (created_at) is untouched --
    exactly the divergence that produced a false "index is N days stale" claim.
    """
    projects_dir = tmp_path / "projects"
    first_indexed = "2026-08-22T13:12:06.243607"
    _write_project_info(
        projects_dir / "test_project",
        project_path=str(tmp_path),
        created_at=first_indexed,
    )

    with (
        patch(
            "mcp_server.tools.status_handlers.get_storage_dir", return_value=tmp_path
        ),
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
    ):
        # Simulate a full re-index that happened days after first indexing.
        re_indexed = "2026-08-30T17:55:07.290674"
        mock_snapshot_mgr = Mock()
        mock_snapshot_mgr.load_metadata.return_value = {"last_snapshot": re_indexed}
        mock_snapshot_cls.return_value = mock_snapshot_mgr

        result = await tool_specs.handle_list_projects({})

    model_info = result["projects"][0]["models_indexed"][0]
    # created_at is frozen at first-index time...
    assert model_info["created_at"] == first_indexed
    # ...while last_indexed_at reflects the actual, later re-index.
    assert model_info["last_indexed_at"] == re_indexed
    assert model_info["last_indexed_at"] != model_info["created_at"]


@pytest.mark.asyncio
async def test_handle_list_projects_multi_model_distinct_last_indexed_at(tmp_path):
    """Each indexed model for a project must resolve its OWN Merkle timestamp --
    not have one model's re-index time attached to every model entry.
    """
    projects_dir = tmp_path / "projects"
    _write_project_info(
        projects_dir / "test_project_bge",
        project_path=str(tmp_path),
        embedding_model="BAAI/bge-m3",
        model_dimension=1024,
        created_at="2026-08-01T00:00:00",
    )
    _write_project_info(
        projects_dir / "test_project_f2llm",
        project_path=str(tmp_path),
        embedding_model="codefuse-ai/F2LLM-v2-0.6B",
        model_dimension=1024,
        created_at="2026-08-05T00:00:00",
    )

    timestamps_by_slug = {
        "bge-m3": "2026-08-20T10:00:00",
        "f2llm-v2-0.6b": "2026-08-30T17:55:07",
    }

    def _load_metadata(project_path, dimension=None, model_slug=None):
        ts = timestamps_by_slug.get(model_slug)
        return {"last_snapshot": ts} if ts else None

    with (
        patch(
            "mcp_server.tools.status_handlers.get_storage_dir", return_value=tmp_path
        ),
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
    ):
        mock_snapshot_mgr = Mock()
        mock_snapshot_mgr.load_metadata.side_effect = _load_metadata
        mock_snapshot_cls.return_value = mock_snapshot_mgr

        result = await tool_specs.handle_list_projects({})

    assert len(result["projects"]) == 1
    models_by_slug = {
        m["model"]: m["last_indexed_at"]
        for m in result["projects"][0]["models_indexed"]
    }
    assert models_by_slug["BAAI/bge-m3"] == "2026-08-20T10:00:00"
    assert models_by_slug["codefuse-ai/F2LLM-v2-0.6B"] == "2026-08-30T17:55:07"


@pytest.mark.asyncio
async def test_handle_list_projects_missing_merkle_metadata_omits_field(tmp_path):
    """A project with no (or unreadable) Merkle metadata still lists successfully,
    simply without a last_indexed_at field -- listing must never fail because one
    project's freshness lookup errors out.
    """
    projects_dir = tmp_path / "projects"
    _write_project_info(
        projects_dir / "test_project",
        project_path=str(tmp_path),
        created_at="2026-08-22T13:12:06",
    )

    with (
        patch(
            "mcp_server.tools.status_handlers.get_storage_dir", return_value=tmp_path
        ),
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
    ):
        mock_snapshot_mgr = Mock()
        mock_snapshot_mgr.load_metadata.side_effect = OSError("corrupt metadata file")
        mock_snapshot_cls.return_value = mock_snapshot_mgr

        result = await tool_specs.handle_list_projects({})

    assert "error" not in result
    model_info = result["projects"][0]["models_indexed"][0]
    assert "last_indexed_at" not in model_info
    assert model_info["created_at"] == "2026-08-22T13:12:06"


@pytest.mark.asyncio
async def test_handle_list_projects_check_freshness_true_returns_verdict_per_model(
    tmp_path,
):
    """check_freshness=True must attach the definitive index_is_current /
    pending_changes verdict (ADR-0058) to each model entry, sourced from
    compute_index_freshness -- not from last_indexed_at/created_at.
    """
    projects_dir = tmp_path / "projects"
    _write_project_info(
        projects_dir / "test_project",
        project_path=str(tmp_path),
        created_at="2026-08-22T13:12:06",
    )

    with (
        patch(
            "mcp_server.tools.status_handlers.get_storage_dir", return_value=tmp_path
        ),
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
        patch(
            "mcp_server.index_freshness.compute_index_freshness"
        ) as mock_compute_freshness,
    ):
        mock_snapshot_cls.return_value = Mock(load_metadata=Mock(return_value=None))
        mock_compute_freshness.return_value = {
            "index_is_current": False,
            "pending_changes": {"added": 0, "modified": 1, "removed": 0},
        }

        result = await tool_specs.handle_list_projects({"check_freshness": True})

    mock_compute_freshness.assert_called_once()
    model_info = result["projects"][0]["models_indexed"][0]
    assert model_info["index_is_current"] is False
    assert model_info["pending_changes"] == {"added": 0, "modified": 1, "removed": 0}


@pytest.mark.asyncio
async def test_handle_list_projects_default_omits_freshness_and_skips_scan(tmp_path):
    """The default call (check_freshness omitted) must neither compute nor
    attach a freshness verdict -- it is an opt-in, heavier per-project scan
    (ADR-0058), not something every list_projects caller should pay for.
    """
    projects_dir = tmp_path / "projects"
    _write_project_info(
        projects_dir / "test_project",
        project_path=str(tmp_path),
        created_at="2026-08-22T13:12:06",
    )

    with (
        patch(
            "mcp_server.tools.status_handlers.get_storage_dir", return_value=tmp_path
        ),
        patch("mcp_server.state._app_state.current_project", str(tmp_path)),
        patch("mcp_server.tools.status_handlers.SnapshotManager") as mock_snapshot_cls,
        patch(
            "mcp_server.index_freshness.compute_index_freshness"
        ) as mock_compute_freshness,
    ):
        mock_snapshot_cls.return_value = Mock(load_metadata=Mock(return_value=None))

        result = await tool_specs.handle_list_projects({})

    mock_compute_freshness.assert_not_called()
    model_info = result["projects"][0]["models_indexed"][0]
    assert "index_is_current" not in model_info
    assert "pending_changes" not in model_info


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
            result = await tool_specs.handle_get_memory_status({})

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
        result = await tool_specs.handle_cleanup_resources({})

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
            result = await tool_specs.handle_get_search_config_status({})

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

        result = await tool_specs.handle_list_embedding_models({})

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

        result = await tool_specs.handle_list_embedding_models({})

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

        result = await tool_specs.handle_list_embedding_models({})

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
            result = await tool_specs.handle_switch_project(
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
            result = await tool_specs.handle_switch_project(
                {"project_path": str(project_path)}
            )

            assert result["success"] is True
            assert result["indexed"] is False
            assert "not indexed" in result["warning"].lower()


@pytest.mark.asyncio
async def test_handle_switch_project_not_exist():
    """Test switch_project fails when path doesn't exist."""
    result = await tool_specs.handle_switch_project(
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
    # handle_clear_index deletes under the per-project reindex write lock.
    mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())

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
            (index_dir / "metadata.db").touch()
            (index_dir / "metadata.db-wal").touch()
            (index_dir / "metadata.db-shm").touch()
            (index_dir / "stats.json").touch()
            (index_dir / "chunk_embeddings.bin").touch()

        with (
            patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
            patch(
                "mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir
            ),
        ):
            result = await tool_specs.handle_clear_index({})

            assert result["success"] is True
            assert "cleared_models" in result
            assert len(result["cleared_models"]) == 2

            # Verify BM25 directories deleted
            assert not (model1_dir / "index" / "bm25").exists()
            assert not (model2_dir / "index" / "bm25").exists()

            # Verify dense index files deleted
            assert not (model1_dir / "index" / "code.index").exists()
            assert not (model2_dir / "index" / "code.index").exists()

            # Verify metadata.db and its WAL/SHM sidecars are deleted too —
            # these were the actual bug: the old code deleted a filename
            # ("chunks_metadata.db") that never existed, leaving the real
            # metadata.db and its (often full-size) WAL/SHM behind.
            for model_dir in [model1_dir, model2_dir]:
                index_dir = model_dir / "index"
                assert not (index_dir / "metadata.db").exists()
                assert not (index_dir / "metadata.db-wal").exists()
                assert not (index_dir / "metadata.db-shm").exists()
                assert not (index_dir / "stats.json").exists()
                # An explicit clear_index must also drop the chunk cache —
                # it's the escape hatch for suspect vectors.
                assert not (index_dir / "chunk_embeddings.bin").exists()


@pytest.mark.asyncio
async def test_handle_clear_index_no_project():
    """Test clear_index fails when no active project."""
    with patch("mcp_server.state._app_state.current_project", None):
        result = await tool_specs.handle_clear_index({})

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
            result = await tool_specs.handle_configure_search_mode(
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
            result = await tool_specs.handle_switch_embedding_model(
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

        result = await tool_specs.handle_find_similar_code(
            {"chunk_id": "ref_chunk_id", "k": 5}
        )

        assert result["reference_chunk"] == "ref_chunk_id"
        assert len(result["similar_chunks"]) == 1
        assert result["similar_chunks"][0]["file"] == "file.py"
        assert result["similar_chunks"][0]["score"] == 0.95

        # Default: exclude_same_file=False when the argument is omitted
        mock_searcher_instance.find_similar_to_chunk.assert_called_once_with(
            "ref_chunk_id", k=5, exclude_same_file=False
        )


@pytest.mark.asyncio
async def test_handle_find_similar_code_exclude_same_file_passthrough():
    """exclude_same_file=True is threaded through to find_similar_to_chunk."""
    with (
        patch("mcp_server.tools.search_handlers.get_searcher") as mock_searcher,
        patch("mcp_server.tools.search_handlers.get_state") as mock_get_state,
        patch("mcp_server.tools.decorators.get_state") as mock_dec_state,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        mock_searcher_instance = Mock()
        mock_searcher_instance.find_similar_to_chunk.return_value = []
        mock_searcher.return_value = mock_searcher_instance

        result = await tool_specs.handle_find_similar_code(
            {"chunk_id": "ref_chunk_id", "k": 4, "exclude_same_file": True}
        )

        assert result["reference_chunk"] == "ref_chunk_id"
        mock_searcher_instance.find_similar_to_chunk.assert_called_once_with(
            "ref_chunk_id", k=4, exclude_same_file=True
        )


@pytest.mark.asyncio
async def test_handle_find_similar_code_default_k_from_config():
    """Omitted k must fall back to search_mode.default_k, not a hardcoded 4.

    The deployed config raised default_k to 7 as a deliberate recall
    adjustment; the handler previously hardcoded ``arguments.get("k", 4)``
    and silently never picked it up. Explicit-k callers are covered by the
    passthrough tests above and stay byte-identical.
    """
    from search.config import SearchConfig

    with (
        patch("mcp_server.tools.search_handlers.get_searcher") as mock_searcher,
        patch("mcp_server.tools.search_handlers.get_state") as mock_get_state,
        patch("mcp_server.tools.decorators.get_state") as mock_dec_state,
        patch(
            "mcp_server.tools.search_handlers.get_search_config"
        ) as mock_search_config,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        config = SearchConfig()
        config.search_mode.default_k = 7
        mock_search_config.return_value = config

        mock_searcher_instance = Mock()
        mock_searcher_instance.find_similar_to_chunk.return_value = []
        mock_searcher.return_value = mock_searcher_instance

        await tool_specs.handle_find_similar_code({"chunk_id": "ref_chunk_id"})

        mock_searcher_instance.find_similar_to_chunk.assert_called_once_with(
            "ref_chunk_id", k=7, exclude_same_file=False
        )


# ============================================================================
# FIND_CONNECTIONS TESTS - hide_ambiguous display filter
# ============================================================================


def _make_impact_report_with_ambiguous():
    """Real ImpactReport containing one exact and one ambiguous direct caller."""
    from search.types import ImpactReport

    return ImpactReport(
        symbol={"name": "target"},
        chunk_id="src/t.py:function:target",
        direct_callers=[
            {
                "chunk_id": "a.py:1-2:function:a",
                "confidence": "exact",
                "resolver_confidence": 0.9,
            },
            {
                "chunk_id": "b.py:1-2:function:b",
                "confidence": "ambiguous",
                "resolver_confidence": 0.5,
            },
        ],
        indirect_callers=[],
        similar_code=[],
        total_impacted=2,
        unique_files={"a.py", "b.py"},
        dependency_graph={},
        direct_callers_exact=1,
        direct_callers_ambiguous=1,
    )


def _patch_find_connections_deps():
    """Common patch stack for handle_find_connections tests."""
    return (
        patch("mcp_server.tools.search_handlers.get_searcher"),
        patch("mcp_server.tools.search_handlers.get_state"),
        patch("mcp_server.tools.decorators.get_state"),
        patch("mcp_server.tools.search_handlers.RelationshipAnalyzer"),
    )


@pytest.mark.asyncio
async def test_handle_find_connections_default_hides_ambiguous():
    """Omitted hide_ambiguous now defaults to True (promoted 2026-08-16,
    GraphEnhancedConfig.hide_ambiguous_edges_default) — the real (unmocked)
    SearchConfig default drops ambiguous callers while caller_confidence
    stays a pre-filter total."""
    p_searcher, p_state, p_dec_state, p_analyzer = _patch_find_connections_deps()
    with (
        p_searcher,
        p_state as mock_get_state,
        p_dec_state as mock_dec_state,
        p_analyzer as mock_analyzer_cls,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        mock_analyzer = Mock()
        mock_analyzer.analyze_impact.return_value = _make_impact_report_with_ambiguous()
        mock_analyzer_cls.from_searcher.return_value = mock_analyzer

        result = await tool_specs.handle_find_connections(
            {"chunk_id": "src/t.py:function:target"}
        )

        assert [e["chunk_id"] for e in result["direct_callers"]] == [
            "a.py:1-2:function:a",
        ]
        assert result["caller_confidence"]["ambiguous"] == 1


@pytest.mark.asyncio
async def test_handle_find_connections_hide_ambiguous_filters_edges():
    """hide_ambiguous=True drops ambiguous call edges but keeps the
    pre-filter caller_confidence breakdown and total_impacted."""
    p_searcher, p_state, p_dec_state, p_analyzer = _patch_find_connections_deps()
    with (
        p_searcher,
        p_state as mock_get_state,
        p_dec_state as mock_dec_state,
        p_analyzer as mock_analyzer_cls,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        mock_analyzer = Mock()
        mock_analyzer.analyze_impact.return_value = _make_impact_report_with_ambiguous()
        mock_analyzer_cls.from_searcher.return_value = mock_analyzer

        result = await tool_specs.handle_find_connections(
            {"chunk_id": "src/t.py:function:target", "hide_ambiguous": True}
        )

        assert [e["chunk_id"] for e in result["direct_callers"]] == [
            "a.py:1-2:function:a"
        ]
        # Pre-filter totals remain the "N were hidden" signal
        assert result["caller_confidence"]["ambiguous"] == 1
        assert result["total_impacted"] == 2


@pytest.mark.asyncio
async def test_handle_find_connections_omitted_falls_back_to_config_default():
    """Omitted hide_ambiguous picks up
    GraphEnhancedConfig.hide_ambiguous_edges_default when the config sets it
    True — Phase 6 promotion path (default flip) must actually take effect
    without every caller having to pass the arg explicitly."""
    from search.config import SearchConfig

    p_searcher, p_state, p_dec_state, p_analyzer = _patch_find_connections_deps()
    with (
        p_searcher,
        p_state as mock_get_state,
        p_dec_state as mock_dec_state,
        p_analyzer as mock_analyzer_cls,
        patch(
            "mcp_server.tools.search_handlers.get_search_config"
        ) as mock_search_config,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        config = SearchConfig()
        config.graph_enhanced.hide_ambiguous_edges_default = True
        mock_search_config.return_value = config

        mock_analyzer = Mock()
        mock_analyzer.analyze_impact.return_value = _make_impact_report_with_ambiguous()
        mock_analyzer_cls.from_searcher.return_value = mock_analyzer

        result = await tool_specs.handle_find_connections(
            {"chunk_id": "src/t.py:function:target"}
        )

        assert [e["chunk_id"] for e in result["direct_callers"]] == [
            "a.py:1-2:function:a"
        ]


@pytest.mark.asyncio
async def test_handle_find_connections_explicit_false_overrides_config_default():
    """An explicit hide_ambiguous=False always wins over the config default,
    even when the config default is True."""
    from search.config import SearchConfig

    p_searcher, p_state, p_dec_state, p_analyzer = _patch_find_connections_deps()
    with (
        p_searcher,
        p_state as mock_get_state,
        p_dec_state as mock_dec_state,
        p_analyzer as mock_analyzer_cls,
        patch(
            "mcp_server.tools.search_handlers.get_search_config"
        ) as mock_search_config,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        config = SearchConfig()
        config.graph_enhanced.hide_ambiguous_edges_default = True
        mock_search_config.return_value = config

        mock_analyzer = Mock()
        mock_analyzer.analyze_impact.return_value = _make_impact_report_with_ambiguous()
        mock_analyzer_cls.from_searcher.return_value = mock_analyzer

        result = await tool_specs.handle_find_connections(
            {"chunk_id": "src/t.py:function:target", "hide_ambiguous": False}
        )

        assert [e["chunk_id"] for e in result["direct_callers"]] == [
            "a.py:1-2:function:a",
            "b.py:1-2:function:b",
        ]


def _make_impact_report_no_callers():
    """A leaf symbol: no callers, no callees. Exercises the D13 zero-caller
    path -- ImpactReport.to_dict() must still emit direct_callers/
    direct_callees as [] rather than omitting the keys."""
    from search.types import ImpactReport

    return ImpactReport(
        symbol={"name": "leaf"},
        chunk_id="src/t.py:function:leaf",
        direct_callers=[],
        indirect_callers=[],
        similar_code=[],
        total_impacted=0,
        unique_files=set(),
        dependency_graph={},
    )


@pytest.mark.asyncio
async def test_handle_find_connections_zero_callers_survives_formatting():
    """D13 regression guard: a leaf symbol's empty direct_callers/
    direct_callees must reach format_response as *present* keys (not
    omitted), in all three output formats -- exercising the real
    handle_find_connections -> format_response chain rather than a
    hand-authored dict, which is exactly the isolation gap that let D13 hide
    behind an otherwise-green TestZeroResultContract suite (both keys were
    already covered there, but only at the formatter layer)."""
    from mcp_server.output_formatter import format_response

    p_searcher, p_state, p_dec_state, p_analyzer = _patch_find_connections_deps()
    with (
        p_searcher,
        p_state as mock_get_state,
        p_dec_state as mock_dec_state,
        p_analyzer as mock_analyzer_cls,
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_get_state.return_value = mock_state
        mock_dec_state.return_value = mock_state

        mock_analyzer = Mock()
        mock_analyzer.analyze_impact.return_value = _make_impact_report_no_callers()
        mock_analyzer_cls.from_searcher.return_value = mock_analyzer

        result = await tool_specs.handle_find_connections(
            {"chunk_id": "src/t.py:function:leaf"}
        )

        # The handler's raw dict must already carry both keys (D13) -- this
        # is what a conditional to_dict() emission would fail before any
        # formatter runs.
        assert result["direct_callers"] == []
        assert result["direct_callees"] == []

        for fmt in ("verbose", "compact", "ultra"):
            formatted = format_response(result, fmt)
            assert formatted["direct_callers"] == [], fmt
            assert formatted["direct_callees"] == [], fmt


# ============================================================================
# COMPLEX TOOLS TESTS (Simplified - full integration testing elsewhere)
# ============================================================================


def _make_rwlock_mock():
    """Mock for ``ApplicationState.get_reindex_rwlock()``'s return value.

    Exposes ``.read()`` and ``.write()``, each returning a fresh no-op async
    context manager on every call.
    """

    def _make_async_cm():
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=None)
        cm.__aexit__ = AsyncMock(return_value=False)
        return cm

    rwlock = MagicMock()
    rwlock.read = Mock(side_effect=_make_async_cm)
    rwlock.write = Mock(side_effect=_make_async_cm)
    return rwlock


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
            "mcp_server.tools.search_handlers._is_index_stale",
            return_value=False,
        ),
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_state.searcher = None
        mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())
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

        result = await tool_specs.handle_search_code({"query": "test query", "k": 5})

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
            "mcp_server.tools.search_handlers._is_index_stale",
            return_value=False,
        ),
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
        patch(
            "mcp_server.tools.result_view._format_search_results",
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
            "mcp_server.tools.result_view.enrich_results",
            side_effect=lambda r, _im, _gates: r,
        ),
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_state.searcher = None
        mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())
        mock_get_state.return_value = mock_state
        mock_handler_state.return_value = mock_state
        mock_dec_state.return_value = mock_state
        mock_cm.return_value.get_search_mode_for_query.return_value = "hybrid"
        mock_cfg.return_value.performance.use_parallel_search = False
        mock_cfg.return_value.intent.default_intent = "HYBRID"
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
        result = await tool_specs.handle_search_code({"query": "test query", "k": 5})

        # Should succeed without "No indexed project found" error
        assert "error" not in result
        assert "results" in result, (
            f"handle_search_code response should carry a 'results' key, got {result.keys()}"
        )
        assert isinstance(result["results"], list)


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
            "mcp_server.tools.search_handlers._is_index_stale",
            return_value=False,
        ),
        patch(
            "mcp_server.tools.search_handlers._check_auto_reindex",
            return_value=(False, None),
        ),
    ):
        mock_state = Mock()
        mock_state.current_project = "/test/project"
        mock_state.searcher = None
        mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())
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
        result = await tool_specs.handle_search_code({"query": "test query", "k": 5})

        # Should return error
        assert "error" in result
        assert "no indexed project" in result["error"].lower()


@pytest.mark.asyncio
async def test_handle_index_directory_not_exist():
    """Test index_directory fails when directory doesn't exist."""
    result = await tool_specs.handle_index_directory(
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
            # functools.wraps preserves __wrapped__ attribute. `callable(handler)`
            # is true for every function reachable via getattr and can never
            # fail, so it was dropped as a disjunct — only the decorator check
            # is a real assertion.
            assert hasattr(handler, "__wrapped__"), (
                f"{module.__name__}.{name} should use @error_handler decorator"
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
    # handle_delete_project deletes under the per-project reindex write lock.
    mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir),
        patch("mcp_server.server.close_project_resources"),
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_sm.return_value.delete_all_snapshots.return_value = 2

        result = await tool_specs.handle_delete_project(
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
        result = await tool_specs.handle_delete_project(
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
    # handle_delete_project deletes under the per-project reindex write lock.
    mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=base_dir),
        patch("mcp_server.server.close_project_resources"),
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_sm.return_value.delete_all_snapshots.return_value = 1

        result = await tool_specs.handle_delete_project(
            {"project_path": str(project_path), "force": True}
        )

    assert result["success"] is True
    assert len(result["deleted_directories"]) == 1
    assert not model_dir.exists()


@pytest.mark.asyncio
async def test_handle_delete_project_not_exist():
    """Test delete_project fails when project path doesn't exist."""
    result = await tool_specs.handle_delete_project(
        {"project_path": "/nonexistent/path"}
    )

    assert "error" in result
    assert "does not exist" in result["error"]


@pytest.mark.asyncio
async def test_handle_delete_project_missing_path():
    """Test delete_project fails when project_path not provided."""
    result = await tool_specs.handle_delete_project({})

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
    # handle_delete_project deletes under the per-project reindex write lock.
    mock_state.get_reindex_rwlock = Mock(return_value=_make_rwlock_mock())

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

                result = await tool_specs.handle_delete_project(
                    {"project_path": str(project_path)}
                )

                # Verify cleanup queue was used
                mock_queue.add.assert_called_once_with(
                    str(model_dir),
                    f"{model_dir.name}: File locked - File is locked",
                )

    assert result["success"] is False
    assert len(result.get("errors", [])) == 1
    assert result.get("queued_for_retry") == 1


def _make_recording_rwlock(events: list[str]):
    """Rwlock mock whose write() CM records enter/exit into ``events``."""

    class _RecordingCM:
        async def __aenter__(self):
            events.append("enter")

        async def __aexit__(self, *exc):
            events.append("exit")
            return False

    rwlock = MagicMock()
    rwlock.write = Mock(side_effect=lambda: _RecordingCM())
    return rwlock


@pytest.mark.asyncio
async def test_handle_clear_index_deletes_under_reindex_write_lock(tmp_path):
    """Regression guard: clear_index must hold the per-project reindex write
    lock across resource teardown + index-file deletion, so it drains
    in-flight searches (read-lock holders) instead of deleting files out
    from under them. The mutation lock alone does not provide this —
    searches never acquire it.
    """
    events: list[str] = []

    mock_state = Mock()
    mock_state.current_project = "/tmp/test_project"
    mock_state.get_reindex_rwlock = Mock(return_value=_make_recording_rwlock(events))

    (tmp_path / "projects").mkdir()

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=tmp_path),
        patch("mcp_server.server.close_project_resources") as mock_close,
    ):
        mock_close.side_effect = lambda *a, **kw: events.append("teardown")

        result = await tool_specs.handle_clear_index({})

    assert result["success"] is True
    # Lock keyed by the active project, and teardown happened inside it.
    mock_state.get_reindex_rwlock.assert_called_once_with("/tmp/test_project")
    assert events == ["enter", "teardown", "exit"]


@pytest.mark.asyncio
async def test_handle_clear_index_write_lock_drains_inflight_reader(tmp_path):
    """Same guarantee as the recording-mock test above, but exercised against
    the REAL _AsyncRWLock: while a fake in-flight search holds .read(),
    clear_index's .write() must block — no teardown/deletion may start until
    the reader releases. Catches regressions in the lock's drain semantics,
    not just call-site wiring.
    """
    import asyncio

    from mcp_server.state import _AsyncRWLock

    events: list[str] = []
    rwlock = _AsyncRWLock()

    mock_state = Mock()
    mock_state.current_project = "/tmp/test_project"
    mock_state.get_reindex_rwlock = Mock(return_value=rwlock)

    (tmp_path / "projects").mkdir()

    reader_holding = asyncio.Event()
    release_reader = asyncio.Event()

    async def inflight_search():
        async with rwlock.read():
            events.append("reader_enter")
            reader_holding.set()
            await release_reader.wait()
            events.append("reader_exit")

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch("mcp_server.tools.index_handlers.get_storage_dir", return_value=tmp_path),
        patch("mcp_server.server.close_project_resources") as mock_close,
    ):
        mock_close.side_effect = lambda *a, **kw: events.append("teardown")

        reader = asyncio.create_task(inflight_search())
        await reader_holding.wait()

        clear = asyncio.create_task(tool_specs.handle_clear_index({}))
        # Real wall-clock (not just loop turns) so the handler could have
        # reached its to_thread teardown if write() failed to block.
        await asyncio.sleep(0.05)
        assert "teardown" not in events, (
            "clear_index proceeded past write() while a reader held the lock"
        )
        assert not clear.done()

        release_reader.set()
        result = await clear
        await reader

    assert result["success"] is True
    assert events == ["reader_enter", "reader_exit", "teardown"]


@pytest.mark.asyncio
async def test_handle_delete_project_deletes_under_reindex_write_lock(tmp_path):
    """Regression guard: delete_project must hold the reindex write lock of
    the project being deleted (which may differ from current_project) across
    resource teardown + rmtree — same rationale as clear_index.
    """
    events: list[str] = []

    project_path = tmp_path / "doomed_project"
    project_path.mkdir()
    storage_dir = tmp_path / "storage"
    (storage_dir / "projects").mkdir(parents=True)

    mock_state = Mock()
    mock_state.current_project = None
    mock_state.get_reindex_rwlock = Mock(return_value=_make_recording_rwlock(events))
    mock_state.discard_reindex_rwlock = Mock(
        side_effect=lambda key: events.append("discard")
    )

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch(
            "mcp_server.tools.index_handlers.get_storage_dir",
            return_value=storage_dir,
        ),
        patch("mcp_server.server.close_project_resources") as mock_close,
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_close.side_effect = lambda *a, **kw: events.append("teardown")
        mock_sm.return_value.delete_all_snapshots.return_value = 0

        result = await tool_specs.handle_delete_project(
            {"project_path": str(project_path)}
        )

    assert result["success"] is True
    # Lock keyed by the resolved path of the project being deleted.
    mock_state.get_reindex_rwlock.assert_called_once_with(str(project_path.resolve()))
    # Lock entry dropped only AFTER the write lock is released (deleting it
    # while held would let a new acquirer get a fresh, uncontended lock).
    mock_state.discard_reindex_rwlock.assert_called_once_with(
        str(project_path.resolve())
    )
    assert events == ["enter", "teardown", "exit", "discard"]


@pytest.mark.asyncio
async def test_handle_delete_project_write_lock_drains_inflight_reader(tmp_path):
    """delete_project counterpart of the clear_index real-lock drain test:
    while a fake in-flight search holds .read() on the doomed project's
    rwlock, delete_project's .write() must block — teardown/rmtree cannot
    start until the reader releases.
    """
    import asyncio

    from mcp_server.state import _AsyncRWLock

    events: list[str] = []
    rwlock = _AsyncRWLock()

    project_path = tmp_path / "doomed_project"
    project_path.mkdir()
    storage_dir = tmp_path / "storage"
    (storage_dir / "projects").mkdir(parents=True)

    mock_state = Mock()
    mock_state.current_project = None
    mock_state.get_reindex_rwlock = Mock(return_value=rwlock)
    mock_state.discard_reindex_rwlock = Mock()

    reader_holding = asyncio.Event()
    release_reader = asyncio.Event()

    async def inflight_search():
        async with rwlock.read():
            events.append("reader_enter")
            reader_holding.set()
            await release_reader.wait()
            events.append("reader_exit")

    with (
        patch("mcp_server.tools.index_handlers.get_state", return_value=mock_state),
        patch(
            "mcp_server.tools.index_handlers.get_storage_dir",
            return_value=storage_dir,
        ),
        patch("mcp_server.server.close_project_resources") as mock_close,
        patch("merkle.snapshot_manager.SnapshotManager") as mock_sm,
    ):
        mock_close.side_effect = lambda *a, **kw: events.append("teardown")
        mock_sm.return_value.delete_all_snapshots.return_value = 0

        reader = asyncio.create_task(inflight_search())
        await reader_holding.wait()

        delete = asyncio.create_task(
            tool_specs.handle_delete_project({"project_path": str(project_path)})
        )
        # Real wall-clock (not just loop turns) so the handler could have
        # reached its to_thread teardown if write() failed to block.
        await asyncio.sleep(0.05)
        assert "teardown" not in events, (
            "delete_project proceeded past write() while a reader held the lock"
        )
        assert not delete.done()

        release_reader.set()
        result = await delete
        await reader

    assert result["success"] is True
    assert events == ["reader_enter", "reader_exit", "teardown"]
    mock_state.discard_reindex_rwlock.assert_called_once_with(
        str(project_path.resolve())
    )


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
