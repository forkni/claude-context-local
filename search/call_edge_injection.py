"""Pure resolver-to-graph transform: inject cross-module call edges into the code graph.

Extracted from ``IndexWriteStage.inject_call_edges`` — the only part of that
class that passes the deletion test outright. Callers no longer need to know
about ``run_resolvers``, the three resolver constructors, the ``min_confidence``
floor, the confidence-precedence merge, or the ``resolver_source``-not-``source``
NetworkX trap (an edge attribute literally named ``source`` is silently
destroyed on save/load round-trip, since NetworkX node-link format reserves
``source``/``target`` as endpoint keys). They get one :class:`InjectionStats`
value back.

The config read that used to be inlined here (``get_search_config().call_graph``)
is now the ``cg_cfg`` parameter, so this function is pure with respect to
config and testable without the config singleton.
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chunking.relationships.call_edge_resolver import CallEdgeResolver, run_resolvers
from chunking.relationships.external_call_graph import PyanResolver
from evaluation.chunk_mapping import build_line_to_chunk_map


if TYPE_CHECKING:
    from graph.graph_storage import CodeGraphStorage
    from search.config import CallGraphConfig
    from search.metadata import MetadataStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InjectionStats:
    """Outcome of one call-edge injection pass.

    ``error`` is set (and the rest left at zero) on the two failure modes
    that used to be indistinguishable from "legitimately found nothing":
    an empty graph, or a resolver-pipeline exception.
    """

    injected: int = 0
    added: int = 0
    upgraded: int = 0
    skipped: int = 0
    resolvers_run: tuple[str, ...] = ()
    error: str | None = None


def inject_call_edges(
    storage: CodeGraphStorage,
    meta_store: MetadataStore,
    project_path: str,
    cg_cfg: CallGraphConfig | None,
) -> InjectionStats:
    """Inject cross-module call edges from the resolver pipeline into the code graph.

    Must run *after* the graph's nodes are populated (e.g. after
    ``add_embeddings``) and *before* the graph is persisted (e.g. before
    ``save_indices``). Multiple resolvers are merged by confidence
    precedence — a higher-confidence resolver can upgrade an edge that was
    already added by a lower-confidence one.

    Args:
        storage: Graph storage whose ``.graph`` (a NetworkX graph) holds the
            already-populated chunk nodes to connect.
        meta_store: Metadata store used to build the line-number-to-chunk map
            resolvers need to attribute calls to chunks.
        project_path: Absolute path to the project root.
        cg_cfg: Call-graph configuration (``search.config.CallGraphConfig``),
            or ``None`` to fall back to the ``pyan`` + ``libcst`` defaults.

    Returns:
        :class:`InjectionStats` describing what happened. ``injected == 0``
        does not by itself mean failure — an installation without the
        ``[callgraph]`` extra, or a project with no cross-module calls, both
        legitimately produce zero edges. Check ``error`` to distinguish a
        genuine failure from a legitimate zero.
    """
    # Loud empty-graph guard. Explicit node-count check, never truthiness —
    # CodeGraphStorage implements __len__ without __bool__, so `if not storage`
    # or `if not storage.graph` silently treats "empty" as "falsy-but-fine"
    # instead of the failure it actually is (the exact shape of a past bug).
    if storage.graph.number_of_nodes() == 0:
        logger.error(
            "[CALL_EDGES] Graph has zero nodes — skipping edge injection "
            "(expected populated graph nodes before injection runs)"
        )
        return InjectionStats(error="graph has zero nodes")

    try:
        # Build raw-id line map (normalize=False → ids match graph node keys).
        raw_line_map = build_line_to_chunk_map(meta_store, normalize=False)

        # Build the resolver list from CallGraphConfig.
        enabled_names: set[str] = (
            set(
                cg_cfg.resolvers if cg_cfg.resolvers is not None else ["pyan", "libcst"]
            )
            if cg_cfg is not None
            else {"pyan", "libcst"}
        )

        # `resolvers` governs Stages 1-2 only; Stage 3 (LSP) is governed
        # solely by the separate `lsp_enabled` bool below and is silently
        # ignored if named here (2026-08-06 config-liveness audit, D3).
        unknown_names = enabled_names - {"pyan", "libcst"}
        if unknown_names:
            if "lsp" in unknown_names:
                logger.warning(
                    "[CALL_EDGES] call_graph.resolvers contains 'lsp', which "
                    "has no effect — Stage 3 (LSP) is enabled solely via "
                    "call_graph.lsp_enabled, not the resolvers list"
                )
                unknown_names = unknown_names - {"lsp"}
            if unknown_names:
                logger.warning(
                    "[CALL_EDGES] call_graph.resolvers contains unrecognized "
                    "name(s) %s — ignored (valid: 'pyan', 'libcst')",
                    sorted(unknown_names),
                )

        resolvers: list[CallEdgeResolver] = []
        resolver_names: list[str] = []
        if "pyan" in enabled_names:
            resolvers.append(
                PyanResolver(
                    max_total_seconds=(
                        cg_cfg.pyan_total_timeout_seconds
                        if cg_cfg is not None
                        else 600.0
                    ),
                    seconds_per_file=(
                        cg_cfg.pyan_seconds_per_file if cg_cfg is not None else 2.5
                    ),
                    cap_seconds=(
                        cg_cfg.pyan_total_timeout_cap_seconds
                        if cg_cfg is not None
                        else 3600.0
                    ),
                )
            )
            resolver_names.append("pyan")
        # Stage 2 — LibCST FQN resolver (MIT, default in [callgraph] extra):
        if "libcst" in enabled_names:
            from chunking.relationships.libcst_call_graph import LibCSTResolver

            resolvers.append(
                LibCSTResolver(
                    use_pyproject_toml=(
                        cg_cfg.use_pyproject_toml if cg_cfg is not None else False
                    )
                )
            )
            resolver_names.append("libcst")
        # Stage 3 — basedpyright LSP resolver (requested by default; no-ops
        # unless the [lsp] extra is installed, highest accuracy):
        if cg_cfg is not None and cg_cfg.lsp_enabled:
            from chunking.relationships.lsp_call_graph import LSPResolver

            resolvers.append(
                LSPResolver(
                    timeout=cg_cfg.lsp_timeout_seconds,
                    max_total_seconds=cg_cfg.lsp_total_timeout_seconds,
                    seconds_per_chunk=cg_cfg.lsp_seconds_per_chunk,
                    cap_seconds=cg_cfg.lsp_total_timeout_cap_seconds,
                )
            )
            resolver_names.append("lsp")

        if not resolvers:
            logger.info("[CALL_EDGES] No resolvers configured — skipping injection")
            return InjectionStats()

        # Run all available resolvers; merge by max confidence.
        merged = run_resolvers(
            resolvers, Path(project_path).resolve(), raw_line_map, logger
        )

        # Apply min_confidence floor — discard edges below the threshold.
        min_conf: float = cg_cfg.min_confidence if cg_cfg else 0.0
        if min_conf > 0.0:
            before = len(merged)
            merged = {k: v for k, v in merged.items() if v.confidence >= min_conf}
            dropped = before - len(merged)
            if dropped:
                logger.info(
                    "[CALL_EDGES] min_confidence=%.2f dropped %d edge(s) "
                    "(confidence below threshold)",
                    min_conf,
                    dropped,
                )

        # Inject / upgrade edges with confidence-precedence semantics.
        g = storage.graph
        injected = added = upgraded = skipped = 0
        for edge in merged.values():
            caller_id = edge.caller_id
            callee_id = edge.callee_id
            if caller_id not in g or callee_id not in g:
                skipped += 1
                continue

            if not g.has_edge(caller_id, callee_id, "calls"):
                storage.add_call_edge(
                    caller_id,
                    callee_name=callee_id,
                    line_number=edge.line,
                    is_method_call=edge.is_method,
                    is_resolved=True,
                    # Use "resolver_source" not "source": NetworkX node-link format
                    # reserves "source"/"target" as endpoint keys — any edge attribute
                    # named "source" is silently destroyed on save/load round-trip.
                    resolver_source=edge.source,
                    resolver_confidence=edge.confidence,
                )
                added += 1
                injected += 1
            else:
                # Upgrade if this resolver has higher confidence.
                # Key on "calls" — a parallel "imports"/"uses_type" edge on the same
                # (u, v) pair must not be confused with the "calls" edge we manage.
                existing_confidence: float = g.edges[caller_id, callee_id, "calls"].get(
                    "resolver_confidence", 0.0
                )
                if edge.confidence > existing_confidence:
                    upgrade_attrs: dict[str, Any] = {
                        "resolver_source": edge.source,
                        "resolver_confidence": edge.confidence,
                        "is_resolved": True,
                    }
                    # Only overwrite the existing line if this edge actually
                    # has one — a resolver that doesn't track lines (e.g.
                    # libcst with PositionProvider dropped) reports line=0,
                    # which must not clobber a good AST-sourced line number.
                    if edge.line > 0:
                        upgrade_attrs["line"] = edge.line
                    storage.upgrade_call_edge(caller_id, callee_id, **upgrade_attrs)
                    upgraded += 1
                    injected += 1
                else:
                    skipped += 1

        logger.info(
            "[CALL_EDGES] Injected %d edges (added=%d, upgraded=%d, skipped=%d — "
            "node not in graph, edge already present at equal/higher confidence)",
            injected,
            added,
            upgraded,
            skipped,
        )
        return InjectionStats(
            injected=injected,
            added=added,
            upgraded=upgraded,
            skipped=skipped,
            resolvers_run=tuple(resolver_names),
        )

    except Exception as e:  # noqa: BLE001 - resilience: optional call-edge injection non-fatal, indexing continues
        logger.warning(
            "[CALL_EDGES] Edge injection failed (non-fatal):\n%s",
            traceback.format_exc(),
        )
        return InjectionStats(error=str(e))
