"""Search request planning and orchestration for handle_search_code.

SearchPlanner (Phase A): synchronous, side-effect-free decision stage.
SearchOrchestrator (Phases B–D): async execution + assembly + run driver.

Circular-import rule: never import search_handlers at module level. All helpers
from search_handlers are imported lazily inside methods.
"""

from __future__ import annotations

import asyncio
import copy
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mcp_server.server import get_searcher
from mcp_server.services import get_config, get_state
from search.config import (
    EgoGraphConfig,
    ParentRetrievalConfig,
    SearchConfig,
    get_config_manager,
    get_search_config,
)
from search.exceptions import DimensionMismatchError
from search.hybrid_searcher import HybridSearcher
from search.intent_classifier import IntentClassifier, IntentDecision, QueryIntent


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder
    from search.indexer import CodeIndexManager

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


# ---------------------------------------------------------------------------
# Phase B: Execute stage
# ---------------------------------------------------------------------------


@dataclass
class ExecutionOutcome:
    """Result of the execute phase: raw search results + context for assembly.

    Contains no formatting decisions — only I/O results and the per-request
    config snapshot needed by _assemble.
    """

    results: list
    searcher: Any
    index_manager: CodeIndexManager | None
    effective_config: SearchConfig


class SearchOrchestrator:
    """Orchestrates search execution and result assembly.

    Phase B adds _execute. Phases C and D add _assemble and run.
    """

    async def _execute(self, plan: SearchPlan) -> ExecutionOutcome | dict:
        """Blocks A–D: auto-reindex, searcher acquisition, config assembly, search.

        Returns ExecutionOutcome on success; returns a dict (error response) when
        a DimensionMismatchError is raised or the index is not ready.
        """
        from mcp_server.tools.search_handlers import (
            _check_auto_reindex,
            _get_index_manager_from_searcher,
        )

        # ===== Block A: Auto-reindex =====
        current_project = get_state().current_project
        stored_model_key = None
        if plan.auto_reindex and current_project:
            try:
                reindexed, stored_model_key = _check_auto_reindex(
                    current_project, plan.selected_model_key, plan.max_age_minutes
                )
                if reindexed:
                    get_state().searcher = None
            except DimensionMismatchError as e:
                return {
                    "error": "Dimension mismatch",
                    "message": str(e),
                    "recovery_suggestion": (
                        f"Run index_directory with force_reindex=True to rebuild "
                        f"the index for model {e.embedder_model}"
                    ),
                    "embedder_dimension": e.embedder_dim,
                    "index_dimension": e.index_dim,
                }

        # ===== Block B: Searcher acquisition + readiness check =====
        effective_search_model = (
            stored_model_key if stored_model_key else plan.selected_model_key
        )
        if stored_model_key and stored_model_key != plan.selected_model_key:
            logger.info(
                f"[SEARCH] Using stored index model '{stored_model_key}' instead of "
                f"routed model '{plan.selected_model_key}' to preserve searcher cache"
            )

        try:
            searcher = get_searcher(model_key=effective_search_model)
        except DimensionMismatchError as e:
            return {
                "error": "Dimension mismatch",
                "message": str(e),
                "recovery_suggestion": (
                    f"Run index_directory with force_reindex=True to rebuild "
                    f"the index for model {e.embedder_model}"
                ),
                "embedder_dimension": e.embedder_dim,
                "index_dimension": e.index_dim,
            }

        total_chunks = 0
        is_ready = False
        if hasattr(searcher, "is_ready"):
            is_ready = searcher.is_ready
            if (
                hasattr(searcher, "dense_index")
                and searcher.dense_index
                and hasattr(searcher.dense_index, "index")
                and searcher.dense_index.index
            ):
                total_chunks = searcher.dense_index.index.ntotal
        elif hasattr(searcher, "index_manager") and searcher.index_manager:
            stats = searcher.index_manager.get_stats()
            total_chunks = stats.get("total_chunks", 0)
            is_ready = total_chunks > 0
        elif hasattr(searcher, "get_stats"):
            stats = searcher.get_stats()
            total_chunks = stats.get("total_chunks", 0)
            is_ready = total_chunks > 0

        if not is_ready or total_chunks == 0:
            return {
                "error": "No indexed project found",
                "message": "You must index a project before searching",
                "current_project": current_project or "None",
            }

        # ===== Block C: Filter build + config assembly =====
        filters: dict = {}
        if plan.file_pattern:
            filters["file_pattern"] = [plan.file_pattern]
        if plan.include_dirs:
            filters["include_dirs"] = plan.include_dirs
        if plan.exclude_dirs:
            filters["exclude_dirs"] = plan.exclude_dirs
        if plan.chunk_type:
            filters["chunk_type"] = plan.chunk_type

        config_manager = get_config_manager()
        actual_search_mode = config_manager.get_search_mode_for_query(
            plan.query, plan.search_mode
        )

        # get_search_config() returns a process-wide cached singleton. Requests that
        # don't apply ego-graph / parent-retrieval / intent-edge overrides can pass the
        # singleton straight through. Requests that do mutate lazily deep-copy once,
        # so the singleton is never written and concurrent requests don't race.
        config_singleton = get_search_config()
        config_copy: SearchConfig | None = None

        def mutable_config() -> SearchConfig:
            """Deep-copy the singleton on first call; return the same copy thereafter."""
            nonlocal config_copy
            if config_copy is None:
                config_copy = copy.deepcopy(config_singleton)
            return config_copy

        if isinstance(searcher, HybridSearcher) and plan.ego_graph_enabled:
            mutable_config().ego_graph = EgoGraphConfig(
                enabled=plan.ego_graph_enabled,
                k_hops=plan.ego_graph_k_hops,
                max_neighbors_per_hop=plan.ego_graph_max_neighbors,
            )
            logger.info(
                f"[EGO_GRAPH] Enabled with k_hops={plan.ego_graph_k_hops}, "
                f"max_neighbors_per_hop={plan.ego_graph_max_neighbors}"
            )

        # QW5: apply intent-adaptive similarity threshold to ego-graph expansion
        if (
            isinstance(searcher, HybridSearcher)
            and plan.ego_graph_enabled
            and plan.intent_decision
        ):
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

        if isinstance(searcher, HybridSearcher) and plan.include_parent:
            mutable_config().parent_retrieval = ParentRetrievalConfig(
                enabled=plan.include_parent
            )
            logger.info("[PARENT_RETRIEVAL] Enabled")

        # Apply intent-driven weight overrides (per-request kwargs — no shared-state mutation)
        # Use plan.suggested_bm25/dense — already computed by SearchPlanner (no re-derivation needed)
        if (
            isinstance(searcher, HybridSearcher)
            and plan.suggested_bm25 is not None
            and plan.suggested_dense is not None
            and plan.intent_decision is not None
        ):
            logger.info(
                f"[INTENT] Weight override for {plan.intent_decision.intent.value}: "
                f"BM25={searcher.bm25_weight:.2f}→{plan.suggested_bm25:.2f}, "
                f"Dense={searcher.dense_weight:.2f}→{plan.suggested_dense:.2f}"
            )

        # Apply intent-driven edge weights for graph traversal (A1)
        if isinstance(searcher, HybridSearcher) and plan.intent_decision:
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

        effective_config = config_copy if config_copy is not None else config_singleton

        # ===== Block D: Search execution =====
        if isinstance(searcher, HybridSearcher):
            results = await asyncio.to_thread(
                searcher.search,
                query=plan.query,
                k=plan.k,
                search_mode=actual_search_mode,
                min_bm25_score=0.1,
                use_parallel=get_config().performance.use_parallel_search,
                filters=filters if filters else None,
                config=effective_config,
                bm25_weight=plan.suggested_bm25,
                dense_weight=plan.suggested_dense,
            )
        else:
            context_depth = 1 if plan.include_context else 0
            results = await asyncio.to_thread(
                searcher.search,
                query=plan.query,
                k=plan.k,
                search_mode=actual_search_mode,
                context_depth=context_depth,
                filters=filters if filters else None,
            )

        index_manager = _get_index_manager_from_searcher(searcher)
        return ExecutionOutcome(
            results=results,
            searcher=searcher,
            index_manager=index_manager,
            effective_config=effective_config,
        )

    # ---------------------------------------------------------------------------
    # Phase C: Assemble stage — helpers (Blocks F–I) + orchestrating _assemble
    # ---------------------------------------------------------------------------

    @staticmethod
    def _apply_centrality(
        plan: SearchPlan,
        outcome: ExecutionOutcome,
        index_manager: CodeIndexManager | None,
        formatted_results: list[dict],
    ) -> tuple[list[dict], dict | None]:
        """Block F: centrality annotation/reranking + intent-aware synthetic ordering.

        Returns (possibly-reranked results, centrality_scores) — centrality_scores is
        forwarded to subgraph extraction. Returns (formatted_results, None) when the
        graph_enhanced guard fails or any of (ImportError, ValueError, KeyError,
        RuntimeError, TypeError) is raised inside the block.
        """
        centrality_scores = None
        graph_config = getattr(outcome.effective_config, "graph_enhanced", None)

        if (
            graph_config
            and graph_config.centrality_annotation
            and index_manager
            and index_manager.graph_storage
        ):
            try:
                from graph.graph_queries import GraphQueryEngine
                from search.centrality_ranker import CentralityRanker

                graph_query_engine = GraphQueryEngine(index_manager.graph_storage)
                ranker = CentralityRanker(
                    graph_query_engine=graph_query_engine,
                    method=graph_config.centrality_method,
                    alpha=graph_config.centrality_alpha,
                    config=graph_config,
                )

                centrality_scores = ranker._get_centrality_scores()

                # QW1: pass centrality scores to ego-graph retriever so neighbors
                # are ranked by architectural importance before truncation.
                # NOTE(v0.11.2 follow-up): set_centrality_scores mutates shared retriever
                # state, but centrality is graph-derived (not query-derived), so all
                # concurrent requests compute the same scores — races here are benign.
                # If centrality ever becomes query-aware, isolate this via per-request kwargs
                # the same way bm25_weight/dense_weight were isolated in v0.11.2.
                if (
                    isinstance(outcome.searcher, HybridSearcher)
                    and hasattr(outcome.searcher, "ego_graph_retriever")
                    and outcome.searcher.ego_graph_retriever is not None
                    and centrality_scores
                ):
                    outcome.searcher.ego_graph_retriever.set_centrality_scores(
                        centrality_scores
                    )
                    logger.debug(
                        f"[EGO_GRAPH] Injected {len(centrality_scores)} centrality scores"
                    )

                if graph_config.centrality_reranking:
                    formatted_results = ranker.rerank(
                        formatted_results, query=plan.query
                    )
                    logger.debug(
                        f"Reranked {len(formatted_results)} results by centrality"
                    )
                else:
                    formatted_results = ranker.annotate(formatted_results)
                    logger.debug(
                        f"Annotated {len(formatted_results)} results with centrality"
                    )

                # Intent-aware synthetic chunk ordering (post-centrality reranking)
                # For non-GLOBAL queries, push module/community summary chunks to end of results
                # Research: TNO, GRACE, GraphRAG all separate summaries from code retrieval
                if (
                    plan.intent_decision
                    and plan.intent_decision.intent != QueryIntent.GLOBAL
                ):
                    real_results = [
                        r
                        for r in formatted_results
                        if r.get("kind") not in ("module", "community")
                    ]
                    synthetic_results = [
                        r
                        for r in formatted_results
                        if r.get("kind") in ("module", "community")
                    ]
                    if synthetic_results:
                        formatted_results = real_results + synthetic_results
                        logger.debug(
                            f"[INTENT] Moved {len(synthetic_results)} synthetic chunks "
                            f"after {len(real_results)} real code chunks (intent: {plan.intent_decision.intent.value})"
                        )

            except (ImportError, ValueError, KeyError, RuntimeError, TypeError) as e:
                logger.debug(f"Centrality ranking failed: {e}")

        return formatted_results, centrality_scores

    @staticmethod
    def _extract_subgraph(
        plan: SearchPlan,
        index_manager: CodeIndexManager | None,
        formatted_results: list[dict],
        centrality_scores: dict | None,
    ) -> dict | None:
        """Block G: SSCG subgraph extraction. Returns subgraph.to_dict() or None."""
        if not (index_manager and index_manager.graph_storage is not None):
            return None
        try:
            from search.subgraph_extractor import SubgraphExtractor

            extractor = SubgraphExtractor(index_manager.graph_storage)
            result_chunk_ids = [
                r["chunk_id"] for r in formatted_results[: plan.k] if "chunk_id" in r
            ]
            ego_neighbor_ids = [
                r["chunk_id"]
                for r in formatted_results[plan.k :]
                if r.get("source") == "ego_graph" and "chunk_id" in r
            ]
            max_ego_in_subgraph = 10
            if ego_neighbor_ids and len(ego_neighbor_ids) > max_ego_in_subgraph:
                ego_neighbor_ids = ego_neighbor_ids[:max_ego_in_subgraph]

            if result_chunk_ids:
                subgraph = extractor.extract_subgraph(
                    result_chunk_ids,
                    include_boundary_edges=True,
                    centrality_scores=centrality_scores,
                    ego_neighbor_ids=ego_neighbor_ids if ego_neighbor_ids else None,
                )
                if subgraph.nodes:
                    ego_count = len(ego_neighbor_ids) if ego_neighbor_ids else 0
                    logger.debug(
                        f"[SSCG] Extracted subgraph: {len(subgraph.nodes)} nodes "
                        f"({ego_count} ego-graph neighbors), {len(subgraph.edges)} edges"
                    )
                    return subgraph.to_dict()
                else:
                    logger.info(
                        f"[SSCG] No graph nodes found for {len(result_chunk_ids)} chunk_ids"
                    )
        except Exception as e:
            logger.debug(f"[SSCG] Subgraph extraction failed: {e}")
        return None

    @staticmethod
    def _apply_source_order_and_budget(
        plan: SearchPlan,
        outcome: ExecutionOutcome,
        formatted_results: list[dict],
    ) -> list[dict]:
        """Block H: source-position reorder (when output.source_order_output) +
        context-token-budget truncation (when plan.max_context_tokens > 0).
        """
        from mcp_server.tools.search_handlers import _reorder_by_source_position

        if (
            getattr(outcome.effective_config.output, "source_order_output", True)
            and len(formatted_results) > 1
        ):
            formatted_results = _reorder_by_source_position(formatted_results)
            logger.debug(
                f"[SOURCE_ORDER] Reordered {len(formatted_results)} results by file position"
            )

        if plan.max_context_tokens > 0 and formatted_results:
            import json as _json

            budget_used = 0
            truncated = []
            for r in formatted_results:
                est_tokens = len(_json.dumps(r)) // 4
                if budget_used + est_tokens <= plan.max_context_tokens:
                    truncated.append(r)
                    budget_used += est_tokens
                else:
                    logger.info(
                        f"[CONTEXT_BUDGET] Truncated {len(formatted_results)}→{len(truncated)} results (budget={plan.max_context_tokens})"
                    )
                    break
            formatted_results = truncated

        return formatted_results

    @staticmethod
    def _build_response(
        plan: SearchPlan,
        formatted_results: list[dict],
        subgraph_data: dict | None,
    ) -> dict:
        """Block I: assemble the response dict (results + optional subgraph keys +
        conditional routing info), then attach the system guidance message.
        """
        from mcp_server.guidance import add_system_message

        response: dict = {"query": plan.query, "results": formatted_results}
        if subgraph_data:
            response["subgraph_nodes"] = subgraph_data["nodes"]
            response["subgraph_edges"] = subgraph_data["edges"]
            if subgraph_data.get("topology_order"):
                response["subgraph_order"] = subgraph_data["topology_order"]
            if subgraph_data.get("communities"):
                response["subgraph_communities"] = subgraph_data["communities"]

        if plan.routing_info:
            confidence = plan.routing_info.get("confidence", 0.0)
            reason = plan.routing_info.get("reason", "")
            if confidence < 0.9 or "Fallback" in reason or "routed" in reason.lower():
                response["routing"] = plan.routing_info

        response = add_system_message(
            response, tool_name="search_code", query=plan.query, chunk_id=None
        )
        return response

    def _assemble(self, plan: SearchPlan, outcome: ExecutionOutcome) -> dict:
        """Blocks E–I: format, enrich, centrality, subgraph, reorder, build response."""
        from mcp_server.tools.search_handlers import (
            _enrich_results_with_graph_data,
            _format_search_results,
            _get_index_manager_from_searcher,
        )

        index_manager = _get_index_manager_from_searcher(outcome.searcher)

        # Block E: format + enrich
        formatted_results = _enrich_results_with_graph_data(
            _format_search_results(outcome.results), index_manager
        )

        # Block F: centrality annotation/reranking (+ intent-aware synthetic ordering)
        formatted_results, centrality_scores = self._apply_centrality(
            plan, outcome, index_manager, formatted_results
        )

        # Cap total results to prevent token bloat (k primary + up to 3k context)
        max_total = plan.k * 4
        if len(formatted_results) > max_total:
            logger.info(
                f"Capping total results: {len(formatted_results)} -> {max_total}"
            )
            formatted_results = formatted_results[:max_total]

        # Block G: subgraph extraction
        subgraph_data = self._extract_subgraph(
            plan, index_manager, formatted_results, centrality_scores
        )

        # Block H: source-position reorder + context-budget truncation
        formatted_results = self._apply_source_order_and_budget(
            plan, outcome, formatted_results
        )

        # Block I: response assembly
        return self._build_response(plan, formatted_results, subgraph_data)

    # ---------------------------------------------------------------------------
    # Phase D: run driver
    # ---------------------------------------------------------------------------

    async def run(self, arguments: dict[str, Any]) -> dict:
        """Full search_code pipeline: validate → plan → redirect? → execute → assemble."""
        query = arguments.get("query")
        chunk_id = arguments.get("chunk_id")

        if not query and not chunk_id:
            return {
                "error": "Missing required parameter",
                "message": "Provide either query or chunk_id parameter",
            }
        if query and chunk_id:
            return {
                "error": "Invalid parameters",
                "message": "Provide either query OR chunk_id, not both",
            }

        if chunk_id:
            from mcp_server.tools.search_handlers import _handle_chunk_id_lookup

            return _handle_chunk_id_lookup(chunk_id)

        plan = SearchPlanner().plan(arguments)

        if plan.redirect is not None:
            redirect = plan.redirect
            if redirect.kind == "find_path":
                logger.info(
                    f"[INTENT] Redirecting PATH_TRACING query to find_path: "
                    f"{redirect.params.get('source')} → {redirect.params.get('target')}"
                )
                from mcp_server.tools.search_handlers import handle_find_path

                return await handle_find_path(redirect.params)
            if redirect.kind == "find_similar":
                logger.info(
                    f"[INTENT] Redirecting SIMILARITY query to find_similar_code: "
                    f"{redirect.params.get('symbol_name')}"
                )
                try:
                    _redirect_searcher = get_searcher(model_key=redirect.model_key)
                    _redirect_result = await asyncio.to_thread(
                        _redirect_searcher.search,
                        redirect.params["symbol_name"],
                        k=1,
                    )
                    if _redirect_result:
                        from mcp_server.tools.search_handlers import (
                            handle_find_similar_code,
                        )

                        return await handle_find_similar_code(
                            {"chunk_id": _redirect_result[0].chunk_id, "k": redirect.k}
                        )
                except Exception as e:
                    logger.warning(
                        f"[INTENT] Failed to redirect SIMILARITY query: {e}. "
                        f"Falling back to normal search."
                    )

        logger.info(
            f"[SEARCH] query='{plan.query}', k={plan.k}, mode='{plan.search_mode}'"
        )

        outcome = await self._execute(plan)
        if isinstance(outcome, dict):
            return outcome
        return self._assemble(plan, outcome)
