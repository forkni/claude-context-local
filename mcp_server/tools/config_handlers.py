"""Configuration and state modification tool handlers for MCP server.

Handlers that modify system configuration or project state.
"""

import logging
from pathlib import Path
from typing import Any, Dict

from mcp_server.project_persistence import save_project_selection
from mcp_server.server import _cleanup_previous_resources
from mcp_server.services import get_state
from mcp_server.storage_manager import (
    get_project_storage_dir,
    set_current_project,
)
from mcp_server.tools.decorators import error_handler
from search.config import (
    MODEL_POOL_CONFIG,
    MODEL_REGISTRY,
    get_config_manager,
)

logger = logging.getLogger(__name__)


def _detect_indexed_model(project_path: str) -> str | None:
    """Detect which model has a valid index for this project.

    Args:
        project_path: Path to the project directory

    Returns:
        Model key if found, None otherwise
    """
    for model_key in MODEL_POOL_CONFIG.keys():
        project_dir = get_project_storage_dir(project_path, model_key=model_key)
        code_index_file = project_dir / "index" / "code.index"
        if code_index_file.exists():
            logger.info(f"Detected indexed model for project: {model_key}")
            return model_key
    return None


@error_handler("Project switch")
async def handle_switch_project(arguments: Dict[str, Any]) -> dict:
    """Switch to a different indexed project."""
    project_path = arguments["project_path"]

    project_path = Path(project_path).resolve()
    if not project_path.exists():
        return {"error": f"Project path does not exist: {project_path}"}

    # Cleanup previous resources
    _cleanup_previous_resources()

    # Set new project using setter function (required for cross-module globals)
    set_current_project(str(project_path))

    # Reset and auto-detect model key to ensure correct index is used
    state = get_state()
    state.current_model_key = None
    state.current_index_model_key = None

    # Auto-detect which model was used to index this project
    indexed_model = _detect_indexed_model(str(project_path))
    if indexed_model:
        state.current_model_key = indexed_model
        logger.info(f"Auto-detected and set model key to: {indexed_model}")
    else:
        logger.warning(f"No indexed model detected for project: {project_path}")

    # Save selection for persistence across server restarts
    save_project_selection(str(project_path))

    # Verify project is indexed
    project_dir = get_project_storage_dir(str(project_path), model_key=indexed_model)
    index_dir = project_dir / "index"

    if not index_dir.exists() or not (index_dir / "code.index").exists():
        return {
            "success": True,
            "project": str(project_path),
            "warning": "Project not indexed yet. Run index_directory first.",
            "indexed": False,
        }

    return {
        "success": True,
        "project": str(project_path),
        "indexed": True,
        "message": f"Switched to project: {project_path.name}",
    }


@error_handler("Configure routing")
async def handle_configure_query_routing(arguments: Dict[str, Any]) -> dict:
    """Configure query routing behavior."""
    enable_multi_model = arguments.get("enable_multi_model")
    default_model = arguments.get("default_model")
    confidence_threshold = arguments.get("confidence_threshold")

    config_manager = get_config_manager()
    config = config_manager.load_config()
    changes = {}

    if enable_multi_model is not None:
        # Persist to config file
        config.routing.multi_model_enabled = enable_multi_model
        changes["multi_model_enabled"] = enable_multi_model

        # Update runtime state
        state = get_state()
        state.multi_model_enabled = enable_multi_model

        # Save config
        config_manager.save_config(config)

    if default_model is not None:
        if default_model in MODEL_POOL_CONFIG:
            # Persist to config file
            config.routing.default_model = default_model
            changes["default_model"] = default_model

            # Save config
            config_manager.save_config(config)
        else:
            return {"error": f"Invalid model: {default_model}"}

    if confidence_threshold is not None:
        changes["confidence_threshold"] = confidence_threshold
        # Note: confidence_threshold is runtime-only for now

    return {
        "success": True,
        "changes": changes,
        "message": "Configuration updated and persisted",
        "current_state": {
            "multi_model_enabled": get_state().multi_model_enabled,
        },
    }


@error_handler("Configure search mode")
async def handle_configure_search_mode(arguments: Dict[str, Any]) -> dict:
    """Configure search mode and parameters."""
    search_mode = arguments.get("search_mode", "hybrid")
    bm25_weight = arguments.get("bm25_weight", 0.4)
    dense_weight = arguments.get("dense_weight", 0.6)
    enable_parallel = arguments.get("enable_parallel", True)

    config_manager = get_config_manager()
    config = config_manager.load_config()

    # Update config
    if search_mode in ["hybrid", "semantic", "bm25", "auto"]:
        config.search_mode.default_mode = search_mode
        config.search_mode.enable_hybrid = search_mode in ["hybrid", "auto"]
        config.search_mode.bm25_weight = bm25_weight
        config.search_mode.dense_weight = dense_weight
        config.performance.use_parallel_search = enable_parallel

        config_manager.save_config(config)

        # Reset searcher to pick up new config
        state = get_state()
        state.reset_searcher()

        return {
            "success": True,
            "config": {
                "search_mode": search_mode,
                "bm25_weight": bm25_weight,
                "dense_weight": dense_weight,
                "enable_parallel": enable_parallel,
            },
        }
    else:
        return {"error": f"Invalid search_mode: {search_mode}"}


@error_handler(
    "Switch model",
    error_context=lambda args: {"available_models": list(MODEL_REGISTRY.keys())},
)
async def handle_switch_embedding_model(arguments: Dict[str, Any]) -> dict:
    """Switch to a different embedding model."""
    model_name = arguments["model_name"]

    if model_name not in MODEL_REGISTRY:
        return {
            "error": f"Unknown model: {model_name}",
            "available_models": list(MODEL_REGISTRY.keys()),
        }

    config_manager = get_config_manager()
    config = config_manager.load_config()
    old_model = config.embedding.model_name

    config.embedding.model_name = model_name
    config_manager.save_config(config)

    # Reset embedders to force reload
    state = get_state()
    state.reset_for_model_switch()

    return {
        "success": True,
        "old_model": old_model,
        "new_model": model_name,
        "message": f"Switched to {model_name}. Indexes will use this model.",
        "note": "Existing indices for other models are preserved (per-model storage)",
    }


@error_handler("Configure reranking")
async def handle_configure_reranking(arguments: Dict[str, Any]) -> dict:
    """Configure neural reranker settings.

    Args:
        arguments: Dict with optional keys:
            - enabled: Enable/disable neural reranking
            - model_name: Cross-encoder model to use
            - top_k_candidates: Number of candidates to rerank

    Returns:
        Dict with success status and updated config
    """
    config_manager = get_config_manager()
    config = config_manager.load_config()

    enabled = arguments.get("enabled")
    model_name = arguments.get("model_name")
    top_k_candidates = arguments.get("top_k_candidates")

    if enabled is not None:
        config.reranker.enabled = enabled
    if model_name is not None:
        config.reranker.model_name = model_name
    if top_k_candidates is not None:
        config.reranker.top_k_candidates = top_k_candidates

    config_manager.save_config(config)

    return {
        "success": True,
        "config": {
            "enabled": config.reranker.enabled,
            "model_name": config.reranker.model_name,
            "top_k_candidates": config.reranker.top_k_candidates,
            "min_vram_gb": config.reranker.min_vram_gb,
            "batch_size": config.reranker.batch_size,
        },
        "system_message": "Reranker configuration updated. Changes take effect on next search.",
    }
