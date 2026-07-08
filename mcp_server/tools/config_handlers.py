"""Configuration and state modification tool handlers for MCP server.

Handlers that modify system configuration or project state.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from mcp_server.project_persistence import save_project_selection
from mcp_server.resource_manager import _cleanup_previous_resources
from mcp_server.services import get_state
from mcp_server.storage_manager import (
    get_project_storage_dir,
    set_current_project,
)
from mcp_server.tools import responses
from mcp_server.tools.decorators import error_handler
from search.config import (
    MODEL_REGISTRY,
    ChunkingConfig,
    RerankerConfig,
    SearchMode,
    SearchModeConfig,
    get_config_manager,
    validate_field_value,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field maps: (arg_key, attr_name) pairs for apply_config_patch.
# Attribute names must match the real dataclass fields so that
# validate_field_value can look up metadata from the spec class.
# ---------------------------------------------------------------------------

_CHUNKING_FIELDS: tuple[tuple[str, str], ...] = (
    ("enable_community_detection", "enable_community_detection"),
    ("enable_community_merge", "enable_community_merge"),
    ("community_resolution", "community_resolution"),
    ("max_phantom_degree", "max_phantom_degree"),
    ("token_estimation", "token_estimation"),
    ("enable_large_node_splitting", "enable_large_node_splitting"),
    ("max_chunk_lines", "max_chunk_lines"),
    ("split_size_method", "split_size_method"),
    ("max_split_chars", "max_split_chars"),
    ("enable_file_summaries", "enable_file_summaries"),
    ("enable_community_summaries", "enable_community_summaries"),
    ("sizing_mode", "sizing_mode"),
    ("adaptive_multiplier_max", "adaptive_multiplier_max"),
    ("adaptive_multiplier_min", "adaptive_multiplier_min"),
    ("max_complexity_cap", "max_complexity_cap"),
)

# Echo subset: the fields the response returns (curated; may include read-only fields).
_CHUNKING_ECHO: tuple[str, ...] = (
    "enable_community_detection",
    "enable_community_merge",
    "community_resolution",
    "max_phantom_degree",
    "token_estimation",
    "enable_large_node_splitting",
    "max_chunk_lines",
    "split_size_method",
    "max_split_chars",
    "enable_file_summaries",
    "enable_community_summaries",
    "sizing_mode",
    "adaptive_multiplier_max",
    "adaptive_multiplier_min",
    "max_complexity_cap",
)

_RERANKER_FIELDS: tuple[tuple[str, str], ...] = (
    ("enabled", "enabled"),
    ("model_name", "model_name"),
    ("top_k_candidates", "top_k_candidates"),
)

# Echoes include non-settable fields (min_vram_gb, batch_size) — read from target after patch.
_RERANKER_ECHO: tuple[str, ...] = (
    "enabled",
    "model_name",
    "top_k_candidates",
    "min_vram_gb",
    "batch_size",
)


def apply_config_patch(
    target: Any,
    spec_cls: type,
    arguments: dict[str, Any],
    field_map: tuple[tuple[str, str], ...],
) -> str | None:
    """Apply a batch of config arguments to *target* with spec-driven validation.

    For each ``(arg_key, attr)`` pair in *field_map*: skip if the key is absent from
    *arguments*, validate the value against *spec_cls*'s field metadata via
    :func:`~search.config.validate_field_value`, then ``setattr(target, attr, value)``.
    Returns the first error message encountered, or ``None`` on success.

    *spec_cls* is the **real** dataclass type (e.g. ``ChunkingConfig``), never
    ``type(target)`` — tests mock ``target``, so specs must come from the real class.
    """
    for arg_key, attr in field_map:
        value = arguments.get(arg_key)
        if value is None:
            continue
        err = validate_field_value(spec_cls, attr, value)
        if err:
            return err
        setattr(target, attr, value)
    return None


@error_handler("Project switch")
async def handle_switch_project(arguments: dict[str, Any]) -> dict:
    """Switch to a different indexed project."""
    project_path = arguments["project_path"]

    project_path = Path(project_path).resolve()
    if not project_path.exists():
        return responses.error(f"Project path does not exist: {project_path}")

    # Cleanup previous resources — blocks (gc.collect, torch.cuda ops); offload
    # so it doesn't stall the shared uvicorn event loop (also reachable via the
    # HTTP switch-project route).
    await asyncio.to_thread(_cleanup_previous_resources)

    # Set new project using setter function (required for cross-module globals)
    set_current_project(str(project_path))

    # Save selection for persistence across server restarts
    save_project_selection(str(project_path))

    # Verify project is indexed
    project_dir = get_project_storage_dir(str(project_path))
    index_dir = project_dir / "index"

    if not index_dir.exists() or not (index_dir / "code.index").exists():
        return responses.ok(
            success=True,
            project=str(project_path),
            warning="Project not indexed yet. Run index_directory first.",
            indexed=False,
        )

    return responses.ok(
        success=True,
        project=str(project_path),
        indexed=True,
        message=f"Switched to project: {project_path.name}",
    )


@error_handler("Configure search mode")
async def handle_configure_search_mode(arguments: dict[str, Any]) -> dict:
    """Configure search mode and parameters."""
    search_mode = arguments.get("search_mode", SearchMode.HYBRID)
    bm25_weight = arguments.get("bm25_weight", 0.35)
    dense_weight = arguments.get("dense_weight", 0.65)
    enable_parallel = arguments.get("enable_parallel", True)

    err = validate_field_value(SearchModeConfig, "default_mode", search_mode)
    if err:
        return responses.error(err)

    config_manager = get_config_manager()
    config = config_manager.load_config()

    config.search_mode.default_mode = search_mode
    config.search_mode.enable_hybrid = search_mode in (
        SearchMode.HYBRID,
        SearchMode.AUTO,
    )
    config.search_mode.bm25_weight = bm25_weight
    config.search_mode.dense_weight = dense_weight
    config.performance.use_parallel_search = enable_parallel

    config_manager.save_config(config)

    # Reset searcher to pick up new config
    state = get_state()
    state.reset_searcher()

    return responses.ok(
        success=True,
        config={
            "search_mode": search_mode,
            "bm25_weight": bm25_weight,
            "dense_weight": dense_weight,
            "enable_parallel": enable_parallel,
        },
    )


@error_handler(
    "Switch model",
    error_context=lambda args: {"available_models": list(MODEL_REGISTRY.keys())},
)
async def handle_switch_embedding_model(arguments: dict[str, Any]) -> dict:
    """Switch to a different embedding model."""
    model_name = arguments["model_name"]

    if model_name not in MODEL_REGISTRY:
        return responses.error(
            f"Unknown model: {model_name}",
            available_models=list(MODEL_REGISTRY.keys()),
        )

    config_manager = get_config_manager()
    config = config_manager.load_config()
    old_model = config.embedding.model_name

    config.embedding.model_name = model_name
    config_manager.save_config(config)

    # Reset embedders to force reload — releases VRAM synchronously; offload.
    state = get_state()
    await asyncio.to_thread(state.reset_for_model_switch)

    return responses.ok(
        success=True,
        old_model=old_model,
        new_model=model_name,
        message=f"Switched to {model_name}. Indexes will use this model.",
        note="Existing indices for other models are preserved (per-model storage)",
    )


@error_handler("Configure reranking")
async def handle_configure_reranking(arguments: dict[str, Any]) -> dict:
    """Configure neural reranker settings."""
    config_manager = get_config_manager()
    config = config_manager.load_config()

    err = apply_config_patch(
        config.reranker, RerankerConfig, arguments, _RERANKER_FIELDS
    )
    if err:
        return responses.error(err)

    config_manager.save_config(config)

    return responses.ok(
        success=True,
        config={attr: getattr(config.reranker, attr) for attr in _RERANKER_ECHO},
        system_message="Reranker configuration updated. Changes take effect on next search.",
    )


@error_handler("Configure chunking")
async def handle_configure_chunking(arguments: dict[str, Any]) -> dict:
    """Configure code chunking settings.

    Valid values per field are enforced by ``ChunkingConfig`` field metadata
    (see ``search.config.validate_field_value``).  Exposed parameters:
    enable_community_detection, enable_community_merge, community_resolution (0.1-2.0),
    max_phantom_degree (1-1000), token_estimation ("whitespace"|"tiktoken"),
    enable_large_node_splitting, max_chunk_lines, split_size_method ("lines"|"characters"),
    max_split_chars (1000-10000), enable_file_summaries, enable_community_summaries,
    sizing_mode ("fixed"|"adaptive"), adaptive_multiplier_max (1.0-2.0),
    adaptive_multiplier_min (0.1-1.0), max_complexity_cap (5-100).

    Note: min_chunk_tokens (50) and max_merged_tokens (1000) are optimal defaults and
    not exposed for user configuration.
    """
    config_manager = get_config_manager()
    config = config_manager.load_config()

    err = apply_config_patch(
        config.chunking, ChunkingConfig, arguments, _CHUNKING_FIELDS
    )
    if err:
        return responses.error(err)

    config_manager.save_config(config)

    return responses.ok(
        success=True,
        config={attr: getattr(config.chunking, attr) for attr in _CHUNKING_ECHO},
        system_message="Chunking configuration updated. Re-index project to apply changes.",
    )
