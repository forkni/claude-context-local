"""Configuration and state modification tool handlers for MCP server.

Handlers that modify system configuration or project state.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from mcp_server.project_persistence import save_project_selection
from mcp_server.resource_manager import (
    _cleanup_previous_resources,
    bind_active_project_overrides,
)
from mcp_server.services import get_state
from mcp_server.storage_manager import (
    get_project_storage_dir,
    set_current_project,
)
from mcp_server.tools import responses
from mcp_server.tools.decorators import error_handler, with_mutation_lock
from search.config import (
    MODEL_REGISTRY,
    ChunkingConfig,
    PerformanceConfig,
    RerankerConfig,
    SearchConfig,
    SearchMode,
    SearchModeConfig,
    _derive_mcp_field_names,
    get_config_manager,
    validate_field_value,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Field maps: (arg_key, attr_name) pairs for apply_config_patch.
# Attribute names must match the real dataclass fields so that
# validate_field_value can look up metadata from the spec class.
#
# _CHUNKING_FIELDS/_ECHO and _RERANKER_FIELDS/_ECHO are derived from each
# field's spec(mcp=...) tag (see ADR-0022) — the settable/echo split is
# declared once, on the field, instead of restated here.
# ---------------------------------------------------------------------------

_CHUNKING_FIELD_NAMES: tuple[str, ...] = _derive_mcp_field_names(
    ChunkingConfig, "chunking"
)
_CHUNKING_FIELDS: tuple[tuple[str, str], ...] = tuple(
    (name, name) for name in _CHUNKING_FIELD_NAMES
)

# Echo subset: the fields the response returns (curated; may include read-only fields).
_CHUNKING_ECHO: tuple[str, ...] = _CHUNKING_FIELD_NAMES

_RERANKER_SETTABLE_NAMES: tuple[str, ...] = _derive_mcp_field_names(
    RerankerConfig, "reranker"
)
_RERANKER_FIELDS: tuple[tuple[str, str], ...] = tuple(
    (name, name) for name in _RERANKER_SETTABLE_NAMES
)

# Echoes include non-settable fields (min_vram_gb, batch_size) — read from target after patch.
_RERANKER_ECHO: tuple[str, ...] = _derive_mcp_field_names(
    RerankerConfig, "reranker", "reranker_echo"
)

_SEARCH_MODE_FIELDS: tuple[tuple[str, str], ...] = tuple(
    (name, name) for name in _derive_mcp_field_names(SearchModeConfig, "search_mode")
)  # bm25_weight, dense_weight

# Wire arg name differs from the field name; renaming it would break the
# published tool schema.
_PERFORMANCE_SEARCH_FIELDS: tuple[tuple[str, str], ...] = (
    ("enable_parallel", "use_parallel_search"),
)

# default_mode stays out of _SEARCH_MODE_FIELDS: it is set unconditionally
# above (and drives enable_hybrid), not a skip-if-absent patch.


def _touched_flat_keys(
    arguments: dict[str, Any],
    field_map: tuple[tuple[str, str], ...],
    section: str,
) -> dict[str, Any]:
    """Dotted-key ``{"section.field": value}`` subset of *field_map* whose
    ``arg_key`` is actually present in *arguments* (D7).

    Mirrors apply_config_patch's own skip-if-absent rule so the two stay in
    sync: a field this call didn't touch must never count toward
    SearchConfig.requires_rebuild, or an unrelated argument would trigger an
    unnecessary reset_searcher().
    """
    return {
        f"{section}.{attr}": arguments[arg_key]
        for arg_key, attr in field_map
        if arguments.get(arg_key) is not None
    }


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
@with_mutation_lock
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

    # Point the config layer at the new project's storage dir so its
    # search_overrides.json (ADR-0014) is merged into subsequent config loads,
    # then drop config-derived caches (the global file's mtime does not change
    # on a project switch, so without this the old project's merged config —
    # and the searcher built from it — would keep serving). Non-swallowing:
    # a bind failure here must surface via @error_handler rather than
    # returning success: True while the previous project's overrides serve.
    bind_active_project_overrides(str(project_path))

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
@with_mutation_lock
async def handle_configure_search_mode(arguments: dict[str, Any]) -> dict:
    """Configure search mode and parameters.

    Unspecified fields (bm25_weight, dense_weight, enable_parallel) retain their
    persisted values — only search_mode/enable_hybrid are unconditionally set from
    this call; the rest are patched via apply_config_patch, matching
    handle_configure_reranking/handle_configure_chunking's skip-if-absent pattern.
    """
    search_mode = arguments.get("search_mode", SearchMode.HYBRID)

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
    err = apply_config_patch(
        config.search_mode, SearchModeConfig, arguments, _SEARCH_MODE_FIELDS
    )
    if err:
        return responses.error(err)

    err = apply_config_patch(
        config.performance, PerformanceConfig, arguments, _PERFORMANCE_SEARCH_FIELDS
    )
    if err:
        return responses.error(err)

    config_manager.save_config(config)

    # Reset the searcher only if a construction-baked field was actually
    # touched (D7): default_mode/enable_hybrid/bm25_weight/dense_weight/
    # use_parallel_search are all read live from effective_config on every
    # search() call, so resetting for them was pure pessimisation — an
    # unconditional reset forces a full HybridSearcher rebuild (model/BM25
    # index reload) on every configure_search_mode call regardless of what
    # changed. None of this handler's settable fields are construction_baked
    # today, so this is a no-op at runtime; it exists so a future baked
    # search_mode/performance field (e.g. bm25_tokenizer, rrf_k_parameter —
    # see SearchConfig._CONSTRUCTION_BAKED_FIELDS — becoming MCP-settable)
    # is handled correctly without anyone having to remember to wire it in.
    touched = {
        "search_mode.default_mode": search_mode,
        "search_mode.enable_hybrid": config.search_mode.enable_hybrid,
    }
    touched.update(_touched_flat_keys(arguments, _SEARCH_MODE_FIELDS, "search_mode"))
    touched.update(
        _touched_flat_keys(arguments, _PERFORMANCE_SEARCH_FIELDS, "performance")
    )
    state = get_state()
    if SearchConfig.requires_rebuild(touched):
        state.reset_searcher()

    return responses.ok(
        success=True,
        config={
            "search_mode": search_mode,
            "bm25_weight": config.search_mode.bm25_weight,
            "dense_weight": config.search_mode.dense_weight,
            "enable_parallel": config.performance.use_parallel_search,
        },
    )


@error_handler(
    "Switch model",
    error_context=lambda args: {"available_models": list(MODEL_REGISTRY.keys())},
)
@with_mutation_lock
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
@with_mutation_lock
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

    # Reset only if a construction-baked reranker field was actually touched
    # (D7). None of enabled/model_name/top_k_candidates — this handler's
    # three MCP-settable fields — is construction_baked today (see
    # SearchConfig._CONSTRUCTION_BAKED_FIELDS), so this is a no-op at
    # runtime and the "next search" promise below is currently true. Wired
    # in anyway, mirroring handle_configure_search_mode, so a future baked
    # settable reranker field doesn't silently break that promise.
    touched = _touched_flat_keys(arguments, _RERANKER_FIELDS, "reranker")
    if SearchConfig.requires_rebuild(touched):
        state = get_state()
        state.reset_searcher()

    return responses.ok(
        success=True,
        config={attr: getattr(config.reranker, attr) for attr in _RERANKER_ECHO},
        system_message="Reranker configuration updated. Changes take effect on next search.",
    )


@error_handler("Configure chunking")
@with_mutation_lock
async def handle_configure_chunking(arguments: dict[str, Any]) -> dict:
    """Configure code chunking settings.

    Valid values per field are enforced by ``ChunkingConfig`` field metadata
    (see ``search.config.validate_field_value``).  Exposed parameters:
    enable_large_node_splitting, max_chunk_lines,
    split_size_method ("lines"|"characters"),
    max_split_chars (1000-10000), enable_file_summaries,
    sizing_mode ("fixed"|"adaptive"), adaptive_multiplier_max (1.0-2.0),
    adaptive_multiplier_min (0.1-1.0), max_complexity_cap (5-100),
    glsl_filter_td_prefix (bool).
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
