"""Status and informational tool handlers for MCP server.

Handlers for read-only status queries that don't modify state.
"""

import json
import logging
from typing import Any

from mcp_server.server import (
    _cleanup_previous_resources,
    get_index_manager,
    get_searcher,
)
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_storage_dir
from mcp_server.tools.decorators import error_handler
from merkle.snapshot_manager import SnapshotManager
from search.config import (
    MODEL_REGISTRY,
)
from search.hybrid_searcher import HybridSearcher


logger = logging.getLogger(__name__)


@error_handler("Status check")
async def handle_get_index_status(arguments: dict[str, Any]) -> dict:
    """Get current status and statistics of the search index."""
    state = get_state()

    # Check if a project is selected
    try:
        index_manager = get_index_manager(model_key=state.current_model_key)
        stats = index_manager.get_stats()
    except ValueError as e:
        # No project selected - return clear error
        return {
            "error": str(e),
            "index_statistics": {"total_chunks": 0},
            "current_project": None,
            "system_message": "No project indexed. Use index_directory to index a project first.",
        }

    # Include hybrid searcher sync status
    # Use get_config() to check if hybrid is enabled
    config = get_config()
    if config.search_mode.enable_hybrid:
        try:
            # Initialize searcher if needed (lazy init)
            searcher = get_searcher()
            if isinstance(searcher, HybridSearcher):
                hybrid_stats = searcher.get_stats()
                # Only add if these keys exist (HybridSearcher-specific)
                if "bm25_documents" in hybrid_stats:
                    stats["bm25_documents"] = hybrid_stats.get("bm25_documents")
                    stats["dense_vectors"] = hybrid_stats.get("dense_vectors")
                    stats["synced"] = hybrid_stats.get("synced")
        except Exception as e:
            logger.warning(f"Could not get hybrid searcher stats: {e}")

    # Collect model info
    model_info = {}
    if state.multi_model_enabled:
        loaded_models = []
        for model_key, embedder in state.embedders.items():
            if embedder is not None:
                info = embedder.get_model_info()
                info["model_key"] = model_key
                loaded_models.append(info)
        model_info = {
            "multi_model_mode": True,
            "loaded_models": loaded_models,
            "total_loaded": len(loaded_models),
        }
    else:
        if "default" in state.embedders and state.embedders["default"] is not None:
            model_info = state.embedders["default"].get_model_info()
            model_info["multi_model_mode"] = False

    # Add last indexed time from Merkle metadata
    last_indexed_time = None
    if state.current_project:
        try:
            snapshot_mgr = SnapshotManager()
            metadata = snapshot_mgr.load_metadata(state.current_project)
            if metadata:
                last_indexed_time = metadata.get("last_snapshot")
        except Exception as e:
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

    if not projects_dir.exists():
        return {
            "projects": [],
            "message": "No projects indexed yet",
        }

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

    # Convert to list
    projects = list(projects_by_path.values())

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

    # GPU memory
    gpu_memory = {}
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / (1024**3)
            reserved = torch.cuda.memory_reserved(i) / (1024**3)
            total_vram = torch.cuda.get_device_properties(i).total_memory / (1024**3)

            gpu_memory[f"gpu_{i}"] = {
                "allocated_gb": round(allocated, 2),
                "reserved_gb": round(reserved, 2),
                # Add GPU hardware details
                "device_name": torch.cuda.get_device_name(i),
                "device_id": i,
                "total_vram_gb": round(total_vram, 1),
                "compute_capability": ".".join(
                    map(str, torch.cuda.get_device_capability(i))
                ),
                "utilization_percent": (
                    round((allocated / total_vram * 100), 1) if total_vram > 0 else 0
                ),
            }

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
        for model_key, embedder in state.embedders.items():
            if embedder is not None and hasattr(embedder, "get_vram_usage"):
                usage = embedder.get_vram_usage()
                if usage:
                    per_model_vram[model_key] = usage
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
    _cleanup_previous_resources()
    return {"success": True, "message": "Resources cleaned up successfully"}


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
        "multi_model_enabled": get_state().multi_model_enabled,
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
    from mcp_server.model_pool_manager import get_model_pool_manager
    from mcp_server.state import get_state

    state = get_state()

    # Build reverse mapping: model_name -> model_key
    pool_config = get_model_pool_manager()._get_pool_config()
    name_to_key = {v: k for k, v in pool_config.items()}

    models = []
    for model_name, config in MODEL_REGISTRY.items():
        # Check if model is loaded
        model_key = name_to_key.get(model_name)
        is_loaded = model_key in state.embedders if model_key else False

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
