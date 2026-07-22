"""Status and informational tool handlers for MCP server.

Handlers for read-only status queries that don't modify state.
"""

import asyncio
import contextlib
import json
import logging
from typing import Any

from mcp_server.resource_manager import _cleanup_previous_resources
from mcp_server.search_factory import (
    get_index_manager,
    get_searcher,
)
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_storage_dir
from mcp_server.tools import responses
from mcp_server.tools.decorators import error_handler
from merkle.snapshot_manager import SnapshotManager
from search.config import (
    MODEL_REGISTRY,
)


logger = logging.getLogger(__name__)


@error_handler("Status check")
async def handle_get_index_status(arguments: dict[str, Any]) -> dict:
    """Get current status and statistics of the search index.

    When ``job_id`` is provided, reports that background indexing job's
    progress (see ``index_directory``'s ``wait=False`` mode) instead of the
    regular index snapshot below.
    """
    job_id = arguments.get("job_id")
    if job_id:
        from mcp_server.tools.job_registry import get_job_registry

        job = await get_job_registry().get(job_id)
        if job is None:
            return responses.error(f"Unknown job_id: {job_id}")
        return job.to_status_dict()

    state = get_state()

    # Check if a project is selected — offload get_index_manager (may init lazily)
    try:

        def _get_index_stats() -> dict:
            return get_index_manager().get_stats()

        stats = await asyncio.to_thread(_get_index_stats)
    except ValueError as e:
        # No project selected - return clear error
        return responses.error(
            str(e),
            index_statistics={"total_chunks": 0},
            current_project=None,
            system_message="No project indexed. Use index_directory to index a project first.",
        )

    # Include hybrid searcher sync status
    # Use get_config() to check if hybrid is enabled
    config = get_config()
    if config.search_mode.enable_hybrid:
        try:
            # Offload get_searcher + stats fetch off the event loop.
            def _get_hybrid_stats() -> dict | None:
                from mcp_server.tools.searcher_view import SearcherView

                _searcher = get_searcher()
                if SearcherView(_searcher).is_hybrid:
                    return _searcher.get_stats()
                return None

            hybrid_stats = await asyncio.to_thread(_get_hybrid_stats)
            # Only add if these keys exist (HybridSearcher-specific)
            if hybrid_stats and "bm25_documents" in hybrid_stats:
                stats["bm25_documents"] = hybrid_stats.get("bm25_documents")
                stats["dense_vectors"] = hybrid_stats.get("dense_vectors")
                stats["synced"] = hybrid_stats.get("synced")
        except Exception as e:  # noqa: BLE001 - resilience: optional stats enrichment, degrade to base stats
            logger.warning(f"Could not get hybrid searcher stats: {e}")

    # Collect model info (single-model mode)
    model_info = {}
    if "default" in state.embedders and state.embedders["default"] is not None:
        model_info = state.embedders["default"].get_model_info()

    # Add last indexed time from Merkle metadata
    last_indexed_time = None
    if state.current_project:
        try:
            snapshot_mgr = SnapshotManager()
            metadata = snapshot_mgr.load_metadata(state.current_project)
            if metadata:
                last_indexed_time = metadata.get("last_snapshot")
        except Exception as e:  # noqa: BLE001 - resilience: optional metadata enrichment, degrade to no timestamp
            logger.debug(f"Could not get last_indexed_time: {e}")

    return {
        "index_statistics": stats,
        "model_information": model_info,
        "storage_directory": str(get_storage_dir()),
        "last_indexed_time": last_indexed_time,
        "current_project": state.current_project,
    }


@error_handler("List projects")
async def handle_list_projects(arguments: dict[str, Any]) -> dict:
    """List all indexed projects grouped by path with model details."""
    base_dir = get_storage_dir()
    projects_dir = base_dir / "projects"

    # The whole sweep (iterdir + per-project JSON reads + exists checks) is
    # blocking I/O whose cost scales with project count — offload as one unit.
    def _scan_projects() -> list[dict[str, Any]] | None:
        if not projects_dir.exists():
            return None

        # Group projects by path
        projects_by_path = {}  # project_path -> project_data

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            info_file = project_dir / "project_info.json"
            if not info_file.exists():
                continue

            with open(info_file) as f:
                project_info = json.load(f)

            project_path = project_info["project_path"]

            # Initialize project entry if first time seeing this path
            if project_path not in projects_by_path:
                # Check if project exists at stored path
                from pathlib import Path

                from search.filters import find_project_at_different_drive

                path_exists = Path(project_path).exists()
                relocated_to = None

                if not path_exists:
                    # Try to find at different drive letter
                    alt_path = find_project_at_different_drive(project_path)
                    if alt_path:
                        relocated_to = alt_path
                        path_exists = True

                project_data = {
                    "project_name": project_info["project_name"],
                    "project_path": project_path,
                    "project_hash": project_info["project_hash"],
                    "path_exists": path_exists,
                    "models_indexed": [],
                }
                # Only include relocated_to if not None (token optimization)
                if relocated_to is not None:
                    project_data["relocated_to"] = relocated_to
                projects_by_path[project_path] = project_data

            # Prepare model info
            model_info = {
                "model": project_info["embedding_model"],
                "dimension": project_info["model_dimension"],
                "chunks": None,
                "created_at": project_info.get("created_at"),
            }

            # Try to load chunk count from stats
            stats_file = project_dir / "index" / "stats.json"
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                    model_info["chunks"] = stats.get("total_chunks", 0)

            projects_by_path[project_path]["models_indexed"].append(model_info)

        return list(projects_by_path.values())

    projects = await asyncio.to_thread(_scan_projects)
    if projects is None:
        return {
            "projects": [],
            "message": "No projects indexed yet",
        }

    return {
        "projects": projects,
        "current_project": get_state().current_project,
    }


@error_handler("Memory status check")
async def handle_get_memory_status(arguments: dict[str, Any]) -> dict:
    """Get current memory usage status."""
    import psutil
    import torch

    # System memory
    mem = psutil.virtual_memory()
    system_memory = {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "used_gb": round(mem.used / (1024**3), 2),
        "percent": mem.percent,
    }

    # GPU memory — use pynvml for real VRAM (ORT allocates outside PyTorch allocator)
    gpu_memory = {}
    if torch.cuda.is_available():
        # Try pynvml for device-wide VRAM (sum of all processes + drivers + ORT).
        # NOTE: nvmlDeviceGetMemoryInfo().used is device-wide, NOT per-process.
        # non_torch_gb approximates non-PyTorch usage but includes other processes.
        nvml_available = False
        try:
            # pyrefly: ignore [missing-import]
            import pynvml

            pynvml.nvmlInit()
            nvml_available = True
        except Exception as e:  # noqa: BLE001 - dep-probe: optional pynvml unavailable, fall back to torch metrics
            logger.debug(
                "pynvml unavailable, falling back to torch-only VRAM metrics: %s", e
            )

        for i in range(torch.cuda.device_count()):
            torch_allocated = torch.cuda.memory_allocated(i) / (1024**3)
            torch_reserved = torch.cuda.memory_reserved(i) / (1024**3)
            total_vram = torch.cuda.get_device_properties(i).total_memory / (1024**3)

            # Real VRAM from nvml (includes ORT, reranker, all CUDA allocators)
            if nvml_available:
                try:
                    # pyrefly: ignore [unbound-name]
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    # pyrefly: ignore [unbound-name]
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    real_used_gb = round(mem_info.used / (1024**3), 2)
                    real_free_gb = round(mem_info.free / (1024**3), 2)
                except Exception as exc:  # noqa: BLE001 - resilience: optional per-device VRAM query, degrade to None
                    logger.debug(
                        "pynvml per-device query failed for device %d: %s", i, exc
                    )
                    real_used_gb = None
                    real_free_gb = None
            else:
                real_used_gb = None
                real_free_gb = None

            entry: dict[str, Any] = {
                "torch_allocated_gb": round(torch_allocated, 2),
                "torch_reserved_gb": round(torch_reserved, 2),
                "device_name": torch.cuda.get_device_name(i),
                "device_id": i,
                "total_vram_gb": round(total_vram, 1),
                "compute_capability": ".".join(
                    map(str, torch.cuda.get_device_capability(i))
                ),
            }
            if real_used_gb is not None:
                entry["used_gb"] = real_used_gb
                entry["free_gb"] = real_free_gb
                entry["utilization_percent"] = (
                    round((real_used_gb / total_vram * 100), 1) if total_vram > 0 else 0
                )
                entry["non_torch_gb"] = round(
                    max(0.0, real_used_gb - torch_allocated), 2
                )
            else:
                # Fallback: torch only (may undercount ORT allocations)
                entry["allocated_gb"] = round(torch_allocated, 2)
                entry["reserved_gb"] = round(torch_reserved, 2)
                entry["utilization_percent"] = (
                    round((torch_allocated / total_vram * 100), 1)
                    if total_vram > 0
                    else 0
                )
            gpu_memory[f"gpu_{i}"] = entry

        if nvml_available:
            with contextlib.suppress(Exception):
                # pyrefly: ignore [unbound-name]
                pynvml.nvmlShutdown()

    # Index memory estimate
    index_memory = {}
    try:
        state = get_state()
        # Use state.index_manager directly - do not trigger model switch via factory
        if state.index_manager and state.index_manager.index:
            ntotal = state.index_manager.index.ntotal
            dimension = state.index_manager.index.d
            # Rough estimate: 4 bytes per float
            estimated_mb = (ntotal * dimension * 4) / (1024**2)
            index_memory = {
                "vectors": ntotal,
                "dimension": dimension,
                "estimated_mb": round(estimated_mb, 2),
            }
    except (AttributeError, RuntimeError):
        pass

    # Collect per-model VRAM breakdown
    per_model_vram = {}
    try:
        state = get_state()
        for key, embedder in state.embedders.items():
            if embedder is not None and hasattr(embedder, "get_vram_usage"):
                usage = embedder.get_vram_usage()
                if usage:
                    per_model_vram[key] = usage
    except (AttributeError, RuntimeError):
        pass

    return {
        "system_memory": system_memory,
        "gpu_memory": gpu_memory if gpu_memory else {"status": "No GPU available"},
        "index_memory": (
            index_memory if index_memory else {"status": "No index loaded"}
        ),
        "per_model_vram_mb": per_model_vram if per_model_vram else {},
    }


@error_handler("Resource cleanup")
async def handle_cleanup_resources(arguments: dict[str, Any]) -> dict:
    """Manually cleanup all resources to free memory."""
    # _cleanup_previous_resources() runs gc.collect() + torch.cuda.synchronize()
    # + empty_cache() — can take hundreds of ms; offload to thread pool.
    await asyncio.to_thread(_cleanup_previous_resources)
    return responses.ok(success=True, message="Resources cleaned up successfully")


@error_handler("Config status check")
async def handle_get_search_config_status(arguments: dict[str, Any]) -> dict:
    """Get current search configuration status."""
    config = get_config()
    return {
        "search_mode": config.search_mode.default_mode,
        "bm25_weight": config.search_mode.bm25_weight,
        "dense_weight": config.search_mode.dense_weight,
        "rrf_k": config.search_mode.rrf_k_parameter,
        "use_parallel": config.performance.use_parallel_search,
        "embedding_model": config.embedding.model_name,
        "auto_reindex_enabled": config.performance.enable_auto_reindex,
        "max_index_age_minutes": config.performance.max_index_age_minutes,
        "bm25_use_stemming": config.search_mode.bm25_use_stemming,
        "multi_hop_enabled": config.multi_hop.enabled,
        "multi_hop_count": config.multi_hop.hop_count,
        "multi_hop_expansion": config.multi_hop.expansion,
        "reranker_enabled": config.reranker.enabled,
        "reranker_model": config.reranker.model_name,
        "reranker_top_k_candidates": config.reranker.top_k_candidates,
        "default_k": config.search_mode.default_k,
        "max_k": config.search_mode.max_k,
    }


@error_handler("List models")
async def handle_list_embedding_models(arguments: dict[str, Any]) -> dict:
    """List all available embedding models."""
    from mcp_server.state import get_state

    state = get_state()

    # Collect full model names that are actually loaded (non-None CodeEmbedder instances).
    # Using the embedder's .model_name attribute (set to the full registry name at init)
    # avoids the pool-scoped reverse-lookup bug and the None-slot false-positive.
    loaded_names: set[str] = {
        e.model_name for e in state.embedders.values() if e is not None
    }

    models = []
    for model_name, config in MODEL_REGISTRY.items():
        # Check if this model is currently loaded in VRAM
        is_loaded = model_name in loaded_names

        models.append(
            {
                "name": model_name,
                "dimension": config["dimension"],
                "description": config.get("description", ""),
                "recommended_batch_size": config.get(
                    "fallback_batch_size", 128
                ),  # API compatibility: reads from fallback_batch_size
                "vram_gb": config.get("vram_gb", "Unknown"),
                "max_context": config.get("max_context"),  # Token capacity
                "loaded": is_loaded,  # Whether model is in memory
            }
        )

    return {
        "models": models,
        "current_model": get_config().embedding.model_name,
    }
