"""Pipeline stage: centrality scoring, ego-graph injection, synthetic ordering, SSCG subgraph extraction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from search.hybrid_searcher import HybridSearcher
from search.intent_classifier import IntentDecision, QueryIntent


if TYPE_CHECKING:
    from search.config import GraphEnhancedConfig
    from search.indexer import CodeIndexManager

logger = logging.getLogger(__name__)


class GraphScoringStage:
    """Pipeline stage that applies centrality scoring, ego-graph injection,
    intent-aware synthetic ordering, and SSCG subgraph extraction.

    This stage encapsulates Blocks F and G of the hybrid search scoring pipeline,
    placing the graph-scoring seam entirely within ``search/``. Callers need not
    know about ``GraphQueryEngine``, ``CentralityRanker``, or ``SubgraphExtractor``;
    the stage returns ``(results, subgraph_data)`` in one call.

    The two guards are independent:

    - **Block F** (centrality) fires only when
      ``graph_config.centrality_annotation`` is ``True``.
    - **Block G** (subgraph) fires whenever ``index_manager.graph_storage`` exists,
      regardless of whether Block F ran.
    """

    def run(
        self,
        query: str,
        intent_decision: IntentDecision | None,
        k: int,
        results: list[dict],
        index_manager: CodeIndexManager | None,
        searcher: Any,
        graph_config: GraphEnhancedConfig | None,
    ) -> tuple[list[dict], dict | None]:
        """Apply graph-enhanced scoring and extract the SSCG subgraph.

        Args:
            query: The search query string.
            intent_decision: Classified query intent (``None`` → no intent-aware
                synthetic-chunk ordering).
            k: Primary result count; used for the ``k*4`` cap and the primary /
                ego-graph chunk split inside subgraph extraction.
            results: Formatted search result dicts (mutated and reordered here).
            index_manager: Active ``CodeIndexManager``; ``None`` → both blocks skip.
            searcher: Active ``HybridSearcher`` (or ``None``); used for ego-graph
                centrality-score injection before subgraph extraction.
            graph_config: ``GraphEnhancedConfig`` controlling centrality behaviour;
                ``None`` → Block F skips.

        Returns:
            ``(results, subgraph_data)`` where ``subgraph_data`` is the SSCG
            subgraph dict (``{"nodes": [...], "edges": [...], ...}``) or ``None``
            when no graph nodes are found.
        """
        results, centrality_scores = self._apply_centrality(
            query, intent_decision, results, index_manager, searcher, graph_config
        )
        results = self._cap_results(results, k)
        subgraph_data = self._extract_subgraph(
            results, k, index_manager, centrality_scores
        )
        return results, subgraph_data

    # ------------------------------------------------------------------
    # Block F helpers
    # ------------------------------------------------------------------

    def _apply_centrality(
        self,
        query: str,
        intent_decision: IntentDecision | None,
        results: list[dict],
        index_manager: CodeIndexManager | None,
        searcher: Any,
        graph_config: GraphEnhancedConfig | None,
    ) -> tuple[list[dict], dict[str, float] | None]:
        """Apply centrality annotation/reranking and intent-aware synthetic ordering.

        Returns ``(results, centrality_scores)`` where ``centrality_scores`` is
        ``None`` when the guard conditions are not met or an error occurs.
        """
        centrality_scores: dict[str, float] | None = None

        # ===== Block F: centrality annotation/reranking + intent-aware synthetic ordering =====
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

                centrality_scores = ranker.get_centrality_scores()

                self._inject_ego_centrality(searcher, centrality_scores)

                if graph_config.centrality_reranking:
                    results = ranker.rerank(results, query=query)
                    logger.debug(f"Reranked {len(results)} results by centrality")
                else:
                    results = ranker.annotate(results)
                    logger.debug(f"Annotated {len(results)} results with centrality")

                results = self._reorder_synthetic(results, intent_decision)

            except (ImportError, ValueError, KeyError, RuntimeError, TypeError) as e:
                logger.debug(f"Centrality ranking failed: {e}")

        return results, centrality_scores

    def _inject_ego_centrality(
        self,
        searcher: Any,
        centrality_scores: dict[str, float] | None,
    ) -> None:
        """Inject centrality scores into the ego-graph retriever if available.

        QW1: pass centrality scores to ego-graph retriever so neighbors
        are ranked by architectural importance before truncation.
        NOTE(v0.11.2 follow-up): set_centrality_scores mutates shared retriever
        state, but centrality is graph-derived (not query-derived), so all
        concurrent requests compute the same scores — races here are benign.
        If centrality ever becomes query-aware, isolate this via per-request kwargs
        the same way bm25_weight/dense_weight were isolated in v0.11.2.
        """
        if (
            isinstance(searcher, HybridSearcher)
            and hasattr(searcher, "ego_graph_retriever")
            and searcher.ego_graph_retriever is not None
            and centrality_scores
        ):
            searcher.ego_graph_retriever.set_centrality_scores(centrality_scores)
            logger.debug(
                f"[EGO_GRAPH] Injected {len(centrality_scores)} centrality scores"
            )

    def _reorder_synthetic(
        self,
        results: list[dict],
        intent_decision: IntentDecision | None,
    ) -> list[dict]:
        """Move module/community summary chunks to the end for non-GLOBAL queries.

        Intent-aware synthetic chunk ordering (post-centrality reranking).
        Research: TNO, GRACE, GraphRAG all separate summaries from code retrieval.
        """
        if intent_decision and intent_decision.intent != QueryIntent.GLOBAL:
            real_results = [
                r for r in results if r.get("kind") not in ("module", "community")
            ]
            synthetic_results = [
                r for r in results if r.get("kind") in ("module", "community")
            ]
            if synthetic_results:
                results = real_results + synthetic_results
                logger.debug(
                    f"[INTENT] Moved {len(synthetic_results)} synthetic chunks "
                    f"after {len(real_results)} real code chunks "
                    f"(intent: {intent_decision.intent.value})"
                )
        return results

    # ------------------------------------------------------------------
    # Cap
    # ------------------------------------------------------------------

    def _cap_results(self, results: list[dict], k: int) -> list[dict]:
        """Cap total results to prevent token bloat (k primary + up to 3k context)."""
        max_total = k * 4
        if len(results) > max_total:
            logger.info(f"Capping total results: {len(results)} -> {max_total}")
            results = results[:max_total]
        return results

    # ------------------------------------------------------------------
    # Block G helper
    # ------------------------------------------------------------------

    def _extract_subgraph(
        self,
        results: list[dict],
        k: int,
        index_manager: CodeIndexManager | None,
        centrality_scores: dict[str, float] | None,
    ) -> dict | None:
        """Extract the SSCG subgraph from graph storage if available.

        Returns the subgraph dict or ``None`` when no graph nodes are found.
        """
        # ===== Block G: SSCG subgraph extraction =====
        subgraph_data: dict | None = None
        if index_manager and index_manager.graph_storage is not None:
            try:
                from search.subgraph_extractor import SubgraphExtractor

                extractor = SubgraphExtractor(index_manager.graph_storage)
                result_chunk_ids = [
                    r["chunk_id"] for r in results[:k] if "chunk_id" in r
                ]
                ego_neighbor_ids = [
                    r["chunk_id"]
                    for r in results[k:]
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
                        subgraph_data = subgraph.to_dict()
                    else:
                        logger.info(
                            f"[SSCG] No graph nodes found for {len(result_chunk_ids)} chunk_ids"
                        )
            except Exception as e:
                logger.debug(f"[SSCG] Subgraph extraction failed: {e}")

        return subgraph_data
