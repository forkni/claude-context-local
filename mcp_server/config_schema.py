"""Derives MCP tool-schema property fragments from search/config.py's spec() metadata.

Publishes invariants, never values (see docs/adr/0042-publish-invariants-not-values.md):
``spec(range=...)`` / ``spec(choices=...)`` are true for every install and may be
published in a static tool schema; a field's dataclass default is the lowest of
ADR-0014's four precedence layers (env > per-project overrides > config file >
dataclass), so it is a per-install *value* and is never emitted here.

Membership in CONFIG_BACKED vs. HAND_TYPED is decided by what the corresponding
handler's ``arguments.get(...)`` actually falls back to — not by whether a
similarly-named config field exists. See each HAND_TYPED entry's rationale string
for the handler line that was read to make that call.
"""

import dataclasses
from enum import Enum
from typing import Any

from mcp_server.enricher_specs import ENRICHER_SPECS
from search.config import (
    CallGraphConfig,
    ChunkingConfig,
    EgoGraphConfig,
    EmbeddingConfig,
    GraphEnhancedConfig,
    OutputConfig,
    PerformanceConfig,
    RerankerConfig,
    SearchMode,
    SearchModeConfig,
)


_TYPE_MAP: dict[type, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}

# Fields whose runtime value/type cannot be read straight off the dataclass
# (default_factory, __post_init__ rewrite, MODEL_REGISTRY overwrite). None of
# these are MCP-visible today — this exists so a future CONFIG_BACKED entry
# added by name-similarity fails loudly instead of silently deriving a
# misleading schema fragment.
_UNRESOLVABLE: frozenset[tuple[type, str]] = frozenset(
    {
        (EgoGraphConfig, "edge_weights"),  # default_factory
        (CallGraphConfig, "resolvers"),  # rewritten in __post_init__
        (EmbeddingConfig, "dimension"),  # overwritten from MODEL_REGISTRY
    }
)


def _field(section_cls: type, field_name: str) -> dataclasses.Field:
    for f in dataclasses.fields(section_cls):
        if f.name == field_name:
            return f
    raise KeyError(f"{section_cls.__name__} has no field {field_name!r}")


def _build(mapping: dict[str, tuple[type, str]]) -> dict[str, dict[str, Any]]:
    """Derive a schema-property fragment for each ``key: (section_cls, field_name)``.

    Emits ``type`` (from the field's real type object — ``search/config.py`` has
    no ``from __future__ import annotations``, so ``f.type`` is a real type, not
    a string), ``minimum``/``maximum`` (from ``metadata["range"]``), and ``enum``
    (from ``metadata["choices"]``). Never emits ``default``.

    Raises ``ValueError`` rather than guessing when a field is in
    ``_UNRESOLVABLE`` or its type isn't in ``_TYPE_MAP`` (covers union types and
    container types alike).
    """
    built: dict[str, dict[str, Any]] = {}
    for key, (section_cls, field_name) in mapping.items():
        if (section_cls, field_name) in _UNRESOLVABLE:
            raise ValueError(
                f"{section_cls.__name__}.{field_name} is not schema-derivable "
                f"(default_factory/__post_init__/MODEL_REGISTRY) — {key} must "
                "stay in HAND_TYPED"
            )
        f = _field(section_cls, field_name)
        # pyrefly: ignore [bad-argument-type]
        json_type = _TYPE_MAP.get(f.type)
        if json_type is None:
            raise ValueError(
                f"{section_cls.__name__}.{field_name} has unmapped type "
                f"{f.type!r} — {key} must stay in HAND_TYPED"
            )
        prop: dict[str, Any] = {"type": json_type}
        range_ = f.metadata.get("range")
        if range_ is not None:
            prop["minimum"], prop["maximum"] = range_
        choices = f.metadata.get("choices")
        if choices is not None:
            prop["enum"] = list(choices)
        built[key] = prop
    return built


# Derived once, generalizing the enum list tool_specs.py already built by hand
# at two call sites (search_code.search_mode, configure_search_mode.search_mode).
SEARCH_MODE_ENUM: tuple[str, ...] = tuple(m.value for m in SearchMode)


CONFIG_BACKED: dict[str, dict[str, Any]] = _build(
    {
        # search_code
        "search_code.k": (SearchModeConfig, "max_k"),
        "search_code.auto_reindex": (PerformanceConfig, "enable_auto_reindex"),
        "search_code.max_age_minutes": (PerformanceConfig, "max_index_age_minutes"),
        "search_code.max_context_tokens": (
            SearchModeConfig,
            "default_max_context_tokens",
        ),
        "search_code.ego_graph_k_hops": (EgoGraphConfig, "k_hops"),
        "search_code.ego_graph_max_neighbors_per_hop": (
            EgoGraphConfig,
            "max_neighbors_per_hop",
        ),
        # find_connections
        "find_connections.hide_ambiguous": (
            GraphEnhancedConfig,
            "hide_ambiguous_edges_default",
        ),
        # configure_search_mode (bm25_weight/dense_weight/enable_parallel are
        # patched via config_handlers.py's skip-if-absent apply_config_patch;
        # search_mode itself is set unconditionally — see HAND_TYPED below)
        "configure_search_mode.bm25_weight": (SearchModeConfig, "bm25_weight"),
        "configure_search_mode.dense_weight": (SearchModeConfig, "dense_weight"),
        "configure_search_mode.enable_parallel": (
            PerformanceConfig,
            "use_parallel_search",
        ),
        # configure_reranking — all three settle via _RERANKER_FIELDS
        "configure_reranking.enabled": (RerankerConfig, "enabled"),
        "configure_reranking.model_name": (RerankerConfig, "model_name"),
        "configure_reranking.top_k_candidates": (RerankerConfig, "top_k_candidates"),
        # configure_chunking — all ten settle via _CHUNKING_FIELDS, 1:1 name match
        "configure_chunking.enable_large_node_splitting": (
            ChunkingConfig,
            "enable_large_node_splitting",
        ),
        "configure_chunking.max_chunk_lines": (ChunkingConfig, "max_chunk_lines"),
        "configure_chunking.split_size_method": (
            ChunkingConfig,
            "split_size_method",
        ),
        "configure_chunking.max_split_chars": (ChunkingConfig, "max_split_chars"),
        "configure_chunking.enable_file_summaries": (
            ChunkingConfig,
            "enable_file_summaries",
        ),
        "configure_chunking.sizing_mode": (ChunkingConfig, "sizing_mode"),
        "configure_chunking.adaptive_multiplier_max": (
            ChunkingConfig,
            "adaptive_multiplier_max",
        ),
        "configure_chunking.adaptive_multiplier_min": (
            ChunkingConfig,
            "adaptive_multiplier_min",
        ),
        "configure_chunking.max_complexity_cap": (
            ChunkingConfig,
            "max_complexity_cap",
        ),
        "configure_chunking.glsl_filter_td_prefix": (
            ChunkingConfig,
            "glsl_filter_td_prefix",
        ),
        # Shared across all 18 tools — output_format is popped centrally in
        # mcp_server/server.py's handle_call_tool before any handler runs, so
        # a single (OutputConfig, "format") mapping backs every occurrence.
        "*.output_format": (OutputConfig, "format"),
    }
)

# One shared property definition for the ×18 output_format occurrences —
# description is identical at every call site, so it lives here rather than
# being restated per tool.
OUTPUT_FORMAT_PROPERTY: dict[str, Any] = {
    **CONFIG_BACKED["*.output_format"],
    "description": (
        "Output format: 'verbose' (full), 'compact' (omit empty), 'ultra' "
        "(tabular: 'key[N]{field1,field2}': [[val1,val2], ...]). See "
        "docs/MCP_TOOLS_REFERENCE.md for details. Omit to use the server's "
        "configured value (get_search_config_status.output_format)."
    ),
}


class _NoDefault:
    """Sentinel distinguishing "no default published" from a legitimate ``None``
    default. A bare ``None`` is itself a valid HandTyped.default value.
    """

    def __repr__(self) -> str:
        return "NO_DEFAULT"


NO_DEFAULT = _NoDefault()


@dataclasses.dataclass(frozen=True, kw_only=True)
class HandTyped:
    """The one source of truth for a hand-typed (non-CONFIG_BACKED) MCP
    parameter's fallback: ``arg()`` returns ``default`` to the handler, and
    ``.schema`` spreads the same value into the published tool schema — so the
    two can no longer independently drift, which is exactly the seam
    ``include_exclusive`` fell through (docs/adr/0046).

    ``default=NO_DEFAULT`` marks a deliberately tri-state parameter (e.g. one
    that defers to stored project state, or has no meaningful default at all):
    no schema default may be published for it, and ``arg()`` refuses to be
    called for it — its fallback must be resolved by the caller instead.
    """

    default: Any = NO_DEFAULT
    rationale: str

    @property
    def schema(self) -> dict[str, Any]:
        """The schema fragment for this default. Enum members publish their
        ``.value`` (a plain str) — the handler-facing ``default`` stays the
        enum member itself, so ``arg()``'s return type is unaffected.
        """
        if self.default is NO_DEFAULT:
            return {}
        value = self.default
        return {"default": value.value if isinstance(value, Enum) else value}


def arg(arguments: dict[str, Any], key: str) -> Any:
    """Read a HAND_TYPED parameter's wire value, falling back to its one
    declared default.

    ``key`` is ``"<tool>.<param>"`` (e.g. ``"search_code.include_parent"``),
    matching a HAND_TYPED entry; the tool prefix is stripped before reading
    ``arguments``. Raises ``ValueError`` for a ``NO_DEFAULT`` key — those are
    tri-state by design and must resolve their own fallback, not through
    this accessor.
    """
    record = HAND_TYPED[key]
    if record.default is NO_DEFAULT:
        raise ValueError(
            f"{key} has no default (NO_DEFAULT) — it is tri-state by design; "
            "its fallback must be resolved by the caller, not via arg()"
        )
    _, param = key.split(".", 1)
    return arguments.get(param, record.default)


# arg key -> the one declared default (spread into the schema, returned to the
# handler) plus why no config field backs it (the handler's actual
# arguments.get fallback is a literal, not a search/config.py read).
HAND_TYPED: dict[str, HandTyped] = {
    "search_code.search_mode": HandTyped(
        default=SearchMode.AUTO,
        rationale=(
            "search_orchestrator.py's SearchPlanner.plan() falls back to the "
            "AUTO literal (route-by-intent), not to config.search_mode.default_mode "
            "— enum stays derived from SearchMode via SEARCH_MODE_ENUM"
        ),
    ),
    "search_code.chunk_type": HandTyped(
        rationale=(
            "chunk-kind vocabulary comes from tree-sitter/AST node kinds, not search config"
        ),
    ),
    "search_code.include_context": HandTyped(
        default=True,
        rationale="literal True fallback (search_orchestrator.py) — no config field",
    ),
    "search_code.include_parent": HandTyped(
        default=False,
        rationale="literal False fallback (search_orchestrator.py) — no config field",
    ),
    # Request-scoped enricher opt-ins: one derived entry per EnricherSpec row
    # (mcp_server/enricher_specs.py) — the row is the single declaration of
    # the parameter's default, description, and rationale.
    **{
        f"search_code.{s.param}": HandTyped(default=s.default, rationale=s.rationale)
        for s in ENRICHER_SPECS
    },
    "search_code.include_dirs": HandTyped(
        rationale=(
            "plain arguments.get, no fallback (search_orchestrator.py) — "
            "per-call scope narrowing has no default value to publish, "
            "config or otherwise"
        ),
    ),
    "search_code.exclude_dirs": HandTyped(
        rationale=(
            "plain arguments.get, no fallback (search_orchestrator.py) — "
            "per-call scope narrowing has no default value to publish, "
            "config or otherwise"
        ),
    ),
    "search_code.ego_graph_enabled": HandTyped(
        rationale=(
            "tri-state: omitted (None) defers to config's ego_graph.enabled, "
            "explicit True/False overrides it for this call — collapsing "
            "omission into a published False would make it indistinguishable "
            "from an explicit override (search_orchestrator.py's "
            "SearchPlanner.plan(), see its own comment at the call site)"
        ),
    ),
    "index_directory.incremental": HandTyped(
        default=True,
        rationale="literal True fallback (index_handlers.py) — no config field",
    ),
    "index_directory.wait": HandTyped(
        default=True,
        rationale=(
            "literal True fallback (index_handlers.py) — selects sync vs. "
            "background dispatch, not a config value"
        ),
    ),
    "index_directory.include_exclusive": HandTyped(
        rationale=(
            "falls back to the project's stored project_info.json filter, not a "
            "search config field"
        ),
    ),
    "find_similar_code.exclude_same_file": HandTyped(
        default=False,
        rationale=(
            "literal False fallback (search_handlers.py) — per-call caller "
            "intent, not a config field"
        ),
    ),
    "delete_project.force": HandTyped(
        default=False,
        rationale=(
            "literal False fallback (index_handlers.py) — per-call safety "
            "confirmation, not a config field"
        ),
    ),
    "find_connections.max_depth": HandTyped(
        default=3,
        rationale=(
            "literal 3 fallback (search_handlers.py) — traversal depth is a "
            "per-call concern; no config field"
        ),
    ),
    "find_path.max_hops": HandTyped(
        default=10,
        rationale=(
            "literal 10 fallback, clamped to 20 (search_handlers.py) — no config field"
        ),
    ),
    "configure_search_mode.search_mode": HandTyped(
        default=SearchMode.HYBRID,
        rationale=(
            "config_handlers.py sets this unconditionally from a literal "
            "SearchMode.HYBRID fallback, never deferred to the persisted "
            "default_mode value — default_mode is deliberately excluded from "
            "_SEARCH_MODE_FIELDS' skip-if-absent patch (see that file's own "
            "comment); enum stays derived from SearchMode via SEARCH_MODE_ENUM"
        ),
    ),
}
