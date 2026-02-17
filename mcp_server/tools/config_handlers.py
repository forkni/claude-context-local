"""Configuration and state modification tool handlers for MCP server.

Handlers that modify system configuration or project state.
"""

import logging
from pathlib import Path
from typing import Any

from mcp_server.project_persistence import save_project_selection
from mcp_server.server import _cleanup_previous_resources
from mcp_server.services import get_state
from mcp_server.storage_manager import (
    get_project_storage_dir,
    set_current_project,
)
from mcp_server.tools.decorators import error_handler
from search.config import (
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
    from mcp_server.model_pool_manager import get_model_pool_manager

    pool_config = get_model_pool_manager().get_pool_config()
    for model_key in pool_config:
        project_dir = get_project_storage_dir(project_path, model_key=model_key)
        code_index_file = project_dir / "index" / "code.index"
        if code_index_file.exists():
            logger.info(f"Detected indexed model for project: {model_key}")
            return model_key
    return None


@error_handler("Project switch")
async def handle_switch_project(arguments: dict[str, Any]) -> dict:
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
async def handle_configure_query_routing(arguments: dict[str, Any]) -> dict:
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
        from mcp_server.model_pool_manager import get_model_pool_manager

        pool_config = get_model_pool_manager().get_pool_config()
        if default_model in pool_config:
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
async def handle_configure_search_mode(arguments: dict[str, Any]) -> dict:
    """Configure search mode and parameters."""
    search_mode = arguments.get("search_mode", "hybrid")
    bm25_weight = arguments.get("bm25_weight", 0.35)
    dense_weight = arguments.get("dense_weight", 0.65)
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
async def handle_switch_embedding_model(arguments: dict[str, Any]) -> dict:
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
async def handle_configure_reranking(arguments: dict[str, Any]) -> dict:
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


@error_handler("Configure chunking")
async def handle_configure_chunking(arguments: dict[str, Any]) -> dict:
    """Configure code chunking settings.

    Args:
        arguments: Dict with optional keys:
            - enable_community_detection: Enable/disable community detection (independent)
            - enable_community_merge: Enable/disable community-based remerge (full index only)
            - community_resolution: Resolution parameter for Louvain community detection (0.1-2.0)
            - token_estimation: Token estimation method ("whitespace" or "tiktoken")
            - enable_large_node_splitting: Enable/disable AST block splitting
            - max_chunk_lines: Maximum lines per chunk before splitting
            - split_size_method: Size method for splitting ("lines" or "characters")
            - max_split_chars: Maximum characters per split chunk (1000-10000)
            - enable_file_summaries: Enable/disable file-level module summaries (A2 feature)

    Returns:
        Dict with success status and updated config

    Note:
        min_chunk_tokens (50) and max_merged_tokens (1000) are optimal defaults
        and not exposed for user configuration.
    """
    config_manager = get_config_manager()
    config = config_manager.load_config()

    enable_community_detection = arguments.get("enable_community_detection")
    enable_community_merge = arguments.get("enable_community_merge")
    community_resolution = arguments.get("community_resolution")
    token_estimation = arguments.get("token_estimation")
    enable_large_node_splitting = arguments.get("enable_large_node_splitting")
    max_chunk_lines = arguments.get("max_chunk_lines")
    split_size_method = arguments.get("split_size_method")
    max_split_chars = arguments.get("max_split_chars")
    enable_file_summaries = arguments.get("enable_file_summaries")
    enable_community_summaries = arguments.get("enable_community_summaries")

    if enable_community_detection is not None:
        config.chunking.enable_community_detection = enable_community_detection
    if enable_community_merge is not None:
        config.chunking.enable_community_merge = enable_community_merge
    if community_resolution is not None:
        if 0.1 <= community_resolution <= 2.0:
            config.chunking.community_resolution = community_resolution
        else:
            return {
                "error": f"Invalid community_resolution: {community_resolution}. Must be between 0.1 and 2.0"
            }
    if token_estimation is not None:
        if token_estimation in ["whitespace", "tiktoken"]:
            config.chunking.token_estimation = token_estimation
        else:
            return {"error": f"Invalid token_estimation: {token_estimation}"}
    if enable_large_node_splitting is not None:
        config.chunking.enable_large_node_splitting = enable_large_node_splitting
    if max_chunk_lines is not None:
        config.chunking.max_chunk_lines = max_chunk_lines
    if split_size_method is not None:
        if split_size_method in ["lines", "characters"]:
            config.chunking.split_size_method = split_size_method
        else:
            return {
                "error": f"Invalid split_size_method: {split_size_method}. Must be 'lines' or 'characters'"
            }
    if max_split_chars is not None:
        if 1000 <= max_split_chars <= 10000:
            config.chunking.max_split_chars = max_split_chars
        else:
            return {
                "error": f"Invalid max_split_chars: {max_split_chars}. Must be between 1000 and 10000"
            }
    if enable_file_summaries is not None:
        config.chunking.enable_file_summaries = enable_file_summaries
    if enable_community_summaries is not None:
        config.chunking.enable_community_summaries = enable_community_summaries

    config_manager.save_config(config)

    return {
        "success": True,
        "config": {
            "enable_community_detection": config.chunking.enable_community_detection,
            "enable_community_merge": config.chunking.enable_community_merge,
            "community_resolution": config.chunking.community_resolution,
            "token_estimation": config.chunking.token_estimation,
            "enable_large_node_splitting": config.chunking.enable_large_node_splitting,
            "max_chunk_lines": config.chunking.max_chunk_lines,
            "split_size_method": config.chunking.split_size_method,
            "max_split_chars": config.chunking.max_split_chars,
            "enable_file_summaries": config.chunking.enable_file_summaries,
            "enable_community_summaries": config.chunking.enable_community_summaries,
        },
        "system_message": "Chunking configuration updated. Re-index project to apply changes.",
    }
