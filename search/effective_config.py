"""Per-request SearchConfig assembly for HybridSearcher-backed search requests.

Extracted from ``SearchOrchestrator._search`` (C3b of the config-seam deepening
that also produced ADR-0030's C4 change) — turns a ``SearchPlan``'s ego-graph /
parent-retrieval / intent-edge overrides plus the process-wide ``SearchConfig``
singleton into the ``SearchConfig`` a single search request should execute
with. Lives next to ``search/config.py`` (the config it manipulates) and next
to the retrieval modules that consume the two policy tables it writes
(``graph.graph_storage.INTENT_EDGE_WEIGHT_PROFILES`` and the module-local
ego-graph intent thresholds).
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
    (ego-graph, parent-retrieval, intent-edge weights) get ``base_config`` back
    unchanged, so the singleton is never mutated and concurrent requests never
    race. Requests that do apply an override get a lazily deep-copied mutable
    clone instead — copied once no matter how many of the four blocks below
    fire.

    ``is_hybrid`` gates the whole region: ego-graph, parent-retrieval, and
    intent-edge weights are all HybridSearcher-only features IntelligentSearcher
    doesn't have. Callers pass ``SearcherView(searcher).is_hybrid``, computed
    once in ``_search`` — this module deliberately takes the already-resolved
    bool rather than the searcher itself, so it stays ignorant of searcher
    types (mcp_server.tools.searcher_view is the application-layer seam that
    answers that question).
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
        if plan.ego_graph_enabled:
            cfg = mutable_config()
            cfg.ego_graph = replace(
                cfg.ego_graph,
                enabled=plan.ego_graph_enabled,
                k_hops=plan.ego_graph_k_hops,
                max_neighbors_per_hop=plan.ego_graph_max_neighbors,
            )
            logger.info(
                f"[EGO_GRAPH] Enabled with k_hops={plan.ego_graph_k_hops}, "
                f"max_neighbors_per_hop={plan.ego_graph_max_neighbors}"
            )

        # QW5: apply intent-adaptive similarity threshold to ego-graph expansion
        if plan.ego_graph_enabled and plan.intent_decision:
            _intent_ego_thresholds = {
                "local": 0.25,
                "global": 0.10,
                "contextual": 0.12,
                "navigational": 0.20,
                "path_tracing": 0.15,
                "similarity": 0.10,
                "hybrid": 0.15,
            }
            intent_threshold = _intent_ego_thresholds.get(
                plan.intent_decision.intent.value, 0.15
            )
            if intent_threshold != 0.15:
                logger.info(
                    f"[EGO_GRAPH] Intent-adaptive threshold: "
                    f"{plan.intent_decision.intent.value} -> {intent_threshold}"
                )
            mutable_config().ego_graph.min_similarity_threshold = intent_threshold

        if plan.include_parent:
            cfg = mutable_config()
            cfg.parent_retrieval = replace(
                cfg.parent_retrieval, enabled=plan.include_parent
            )
            logger.info("[PARENT_RETRIEVAL] Enabled")

        # Apply intent-driven edge weights for graph traversal (A1)
        if plan.intent_decision:
            from graph.graph_storage import INTENT_EDGE_WEIGHT_PROFILES

            intent_key = plan.intent_decision.intent.value
            edge_profile = INTENT_EDGE_WEIGHT_PROFILES.get(intent_key)
            if edge_profile:
                cfg = mutable_config()
                cfg.multi_hop.edge_weights = edge_profile
                if cfg.ego_graph:
                    cfg.ego_graph.edge_weights = edge_profile
                logger.info(
                    f"[INTENT] Edge weight profile set for {intent_key}: "
                    f"calls={edge_profile.get('calls', 'N/A')}, imports={edge_profile.get('imports', 'N/A')}"
                )

    return config_copy if config_copy is not None else base_config
