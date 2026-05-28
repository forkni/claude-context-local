"""Search request planning for handle_search_code.

SearchPlanner is synchronous and side-effect-free: it reads application config
and cached state, and returns a SearchPlan containing every execution parameter
decided for a search_code request, or a PlanRedirect when intent classification
determines a different handler is more appropriate.

Phase A of the staged SearchOrchestrator extraction (see docs/adr/0004). Subsequent
phases will extract _execute (auto-reindex, searcher, config assembly) and _assemble
(centrality, subgraph, post-processing) into this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mcp_server.services import get_config, get_state
from search.config import get_search_config
from search.intent_classifier import IntentClassifier, IntentDecision, QueryIntent


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder

logger = logging.getLogger(__name__)


@dataclass
class SearchPlan:
    """All execution parameters decided for a search_code request.

    Produced by SearchPlanner.plan() and consumed by the execute/assemble sections
    of handle_search_code. Contains no I/O results — only decisions.
    """

    query: str
    k: int
    selected_model_key: str
    routing_info: dict[str, Any] | None
    intent_decision: IntentDecision | None
    search_mode: str
    ego_graph_enabled: bool
    ego_graph_k_hops: int
    ego_graph_max_neighbors: int
    include_parent: bool
    file_pattern: str | None
    include_dirs: list[str] | None
    exclude_dirs: list[str] | None
    chunk_type: str | None
    include_context: bool
    auto_reindex: bool
    max_age_minutes: float
    max_context_tokens: int
    suggested_bm25: float | None
    suggested_dense: float | None
    redirect: PlanRedirect | None = None


@dataclass
class PlanRedirect:
    """Intent-based redirect to a different MCP handler.

    kind:
      "find_path"     — redirect to handle_find_path; params contains {source, target, max_hops}.
      "find_similar"  — redirect to handle_find_similar_code after a 1-result symbol lookup;
                        params["symbol_name"] is the target symbol.

    fallback_on_error: when True (SIMILARITY), the handler should fall through to normal
        search if the I/O lookup raises. When False (PATH_TRACING), no fallback.
    model_key: model to use for the preliminary symbol-lookup search (find_similar only).
    k: k to forward to find_similar_code.
    """

    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    fallback_on_error: bool = False
    model_key: str | None = None
    k: int = 4


def _get_intent_embedder() -> CodeEmbedder | None:
    """Resolve the cached embedder for semantic intent anchor scoring.

    Returns the embedder from the cached searcher if it has been initialized,
    otherwise None (keyword-only intent scoring on the first request).
    """
    cached = get_state().searcher
    if cached is not None and hasattr(cached, "search_executor"):
        return getattr(cached.search_executor, "embedder", None)
    return None


class SearchPlanner:
    """Transforms raw MCP arguments into a SearchPlan.

    Synchronous and side-effect-free (reads config + cached state; writes nothing).
    All search-routing decisions live here so they can be tested without
    the MCP framework or an active index.

    The caller is responsible for:
      - Validating that arguments contains "query" (not "chunk_id").
      - Executing any PlanRedirect.redirect returned (including I/O).
      - Falling through to normal search when redirect.fallback_on_error is True
        and the redirect raises.
    """

    def plan(self, arguments: dict[str, Any]) -> SearchPlan:
        """Build a SearchPlan from raw MCP tool arguments.

        Performs model routing, intent classification, intent redirect detection,
        and all intent-driven parameter adjustments. Returns a SearchPlan whose
        .redirect field is non-None when an intent-based redirect is suggested.

        Args:
            arguments: raw MCP tool arguments dict; must contain "query".
        """
        from mcp_server.tools.search_handlers import _route_query_to_model

        query: str = arguments["query"]

        # k: respect per-request arg, clamp to max_k
        search_config = get_search_config()
        k = int(arguments.get("k", search_config.search_mode.default_k))
        k = min(k, search_config.search_mode.max_k)

        # Model routing
        use_routing = bool(arguments.get("use_routing", True))
        model_key: str | None = arguments.get("model_key")
        selected_model_key, routing_info = _route_query_to_model(
            query, use_routing, model_key
        )

        # Ego-graph defaults (may be overridden by CONTEXTUAL intent below)
        ego_graph_enabled = bool(arguments.get("ego_graph_enabled", False))
        ego_graph_k_hops = int(arguments.get("ego_graph_k_hops", 2))
        ego_graph_max_neighbors = int(
            arguments.get("ego_graph_max_neighbors_per_hop", 10)
        )

        # Intent classification
        config = get_config()
        intent_decision: IntentDecision | None = None
        redirect: PlanRedirect | None = None

        if config.intent.enabled:
            _intent_embedder: CodeEmbedder | None = (
                _get_intent_embedder() if config.intent.semantic_enabled else None
            )
            intent_classifier = IntentClassifier(
                confidence_threshold=config.intent.confidence_threshold,
                enable_logging=config.intent.log_classifications,
                embedder=_intent_embedder,
                semantic_enabled=config.intent.semantic_enabled,
                semantic_weight=config.intent.semantic_weight,
            )
            intent_decision = intent_classifier.classify(query)

            logger.info(
                # pyrefly: ignore [unsupported-operation]
                f"[INTENT] query='{query[:50]}...' -> {intent_decision.intent.value} "
                f"(conf={intent_decision.confidence:.2f}, reason={intent_decision.reason})"
            )

            # Suggest PATH_TRACING redirect (no fallback — if source/target absent, skip)
            if (
                intent_decision.intent == QueryIntent.PATH_TRACING
                and intent_decision.confidence >= config.intent.confidence_threshold
            ):
                source = intent_decision.suggested_params.get("source")
                target = intent_decision.suggested_params.get("target")
                if source and target:
                    redirect = PlanRedirect(
                        kind="find_path",
                        params={"source": source, "target": target, "max_hops": 10},
                        fallback_on_error=False,
                    )

            # Suggest SIMILARITY redirect (fallback on error — I/O lookup may fail)
            if (
                redirect is None
                and intent_decision.intent == QueryIntent.SIMILARITY
                and intent_decision.confidence >= config.intent.confidence_threshold
            ):
                symbol_name = intent_decision.suggested_params.get("symbol_name")
                if symbol_name:
                    redirect = PlanRedirect(
                        kind="find_similar",
                        params={"symbol_name": symbol_name},
                        fallback_on_error=True,
                        model_key=selected_model_key,
                        k=k,
                    )

            # Apply ego_graph for CONTEXTUAL queries (enhance, don't redirect)
            if (
                intent_decision.intent == QueryIntent.CONTEXTUAL
                and intent_decision.suggested_params.get("ego_graph_enabled")
            ):
                ego_graph_enabled = True
                ego_graph_k_hops = int(
                    intent_decision.suggested_params.get("ego_graph_k_hops", 2)
                )
                logger.info(
                    f"[INTENT] Enabling ego_graph for CONTEXTUAL query "
                    f"(k_hops={ego_graph_k_hops})"
                )

            # Adjust k for GLOBAL queries
            if intent_decision.intent == QueryIntent.GLOBAL:
                suggested_k = intent_decision.suggested_params.get("k", k)
                if suggested_k > k:
                    logger.info(
                        f"[INTENT] Increasing k from {k} to {suggested_k} for GLOBAL query"
                    )
                    k = int(suggested_k)

        # Search mode: apply intent suggestion when user left 'auto'
        search_mode = str(arguments.get("search_mode", "auto"))
        if intent_decision and search_mode == "auto":
            suggested_mode = intent_decision.suggested_params.get("search_mode")
            if suggested_mode:
                logger.info(
                    f"[INTENT] Applying suggested search_mode '{suggested_mode}' "
                    f"for {intent_decision.intent.value} query"
                )
                search_mode = suggested_mode

        # Remaining argument extraction
        max_age_minutes = float(
            arguments.get("max_age_minutes", config.performance.max_index_age_minutes)
        )
        max_context_tokens = int(
            arguments.get(
                "max_context_tokens", config.search_mode.default_max_context_tokens
            )
        )

        # Intent-driven weight suggestions (applied in execute section)
        suggested_bm25: float | None = None
        suggested_dense: float | None = None
        if intent_decision:
            suggested_bm25 = intent_decision.suggested_params.get("bm25_weight")
            suggested_dense = intent_decision.suggested_params.get("dense_weight")

        return SearchPlan(
            query=query,
            k=k,
            selected_model_key=selected_model_key,
            routing_info=routing_info,
            intent_decision=intent_decision,
            search_mode=search_mode,
            ego_graph_enabled=ego_graph_enabled,
            ego_graph_k_hops=ego_graph_k_hops,
            ego_graph_max_neighbors=ego_graph_max_neighbors,
            include_parent=bool(arguments.get("include_parent", False)),
            file_pattern=arguments.get("file_pattern"),
            include_dirs=arguments.get("include_dirs"),
            exclude_dirs=arguments.get("exclude_dirs"),
            chunk_type=arguments.get("chunk_type"),
            include_context=bool(arguments.get("include_context", True)),
            auto_reindex=bool(arguments.get("auto_reindex", True)),
            max_age_minutes=max_age_minutes,
            max_context_tokens=max_context_tokens,
            suggested_bm25=suggested_bm25,
            suggested_dense=suggested_dense,
            redirect=redirect,
        )
