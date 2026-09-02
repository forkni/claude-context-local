"""Per-request SearchConfig assembly for HybridSearcher-backed search requests.

Extracted from ``SearchOrchestrator._search`` (C3b of the config-seam deepening
that also produced ADR-0030's C4 change) — turns a ``SearchPlan``'s ego-graph /
parent-retrieval overrides plus the process-wide ``SearchConfig`` singleton
into the ``SearchConfig`` a single search request should execute with. Lives
next to ``search/config.py`` (the config it manipulates).
"""

from __future__ import annotations

import copy
import logging
from dataclasses import replace
from typing import TYPE_CHECKING

from search.config import SearchConfig


if TYPE_CHECKING:
    from mcp_server.tools.search_orchestrator import SearchPlan

logger = logging.getLogger(__name__)


def build_effective_config(
    plan: SearchPlan, base_config: SearchConfig, is_hybrid: bool
) -> SearchConfig:
    """Build the SearchConfig a single search request should execute with.

    ``base_config`` is the process-wide cached singleton (``get_search_config()``).
    Requests that don't apply any of the HybridSearcher-only overrides below
    (ego-graph, parent-retrieval) get ``base_config`` back unchanged, so the
    singleton is never mutated and concurrent requests never race. Requests
    that do apply an override get a lazily deep-copied mutable clone instead —
    copied once no matter how many of the blocks below fire.

    ``is_hybrid`` gates the whole region: ego-graph and parent-retrieval are
    both HybridSearcher-only features IntelligentSearcher doesn't have.
    Callers pass ``SearcherView(searcher).is_hybrid``, computed once in
    ``_search`` — this module deliberately takes the already-resolved bool
    rather than the searcher itself, so it stays ignorant of searcher types
    (mcp_server.tools.searcher_view is the application-layer seam that answers
    that question).
    """
    config_copy: SearchConfig | None = None

    def mutable_config() -> SearchConfig:
        """Deep-copy the singleton on first call; return the same copy thereafter."""
        nonlocal config_copy
        if config_copy is None:
            config_copy = copy.deepcopy(base_config)
        assert config_copy is not None  # set immediately above when None
        return config_copy

    if is_hybrid:
        # Tri-state gate: None means the request omitted ego_graph_enabled and defers
        # to base_config's own ego_graph.enabled default (no copy, no override at all).
        # True/False are explicit per-request overrides — both mutate a copy, but only
        # True also applies the hop-count overrides; an explicit False just turns
        # expansion off and leaves k_hops/max_neighbors_per_hop untouched.
        if plan.ego_graph_enabled is not None:
            cfg = mutable_config()
            if plan.ego_graph_enabled:
                cfg.ego_graph = replace(
                    cfg.ego_graph,
                    enabled=True,
                    k_hops=plan.ego_graph_k_hops,
                    max_neighbors_per_hop=plan.ego_graph_max_neighbors,
                )
                logger.info(
                    f"[EGO_GRAPH] Enabled with k_hops={plan.ego_graph_k_hops}, "
                    f"max_neighbors_per_hop={plan.ego_graph_max_neighbors}"
                )
            else:
                cfg.ego_graph = replace(cfg.ego_graph, enabled=False)
                logger.info("[EGO_GRAPH] Explicitly disabled")

        if plan.include_parent:
            cfg = mutable_config()
            cfg.parent_retrieval = replace(
                cfg.parent_retrieval, enabled=plan.include_parent
            )
            logger.info("[PARENT_RETRIEVAL] Enabled")

    return config_copy if config_copy is not None else base_config
