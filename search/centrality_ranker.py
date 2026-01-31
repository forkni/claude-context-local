"""
Centrality-based result ranking for SSCG Phase 3.

Blends PageRank centrality scores with semantic similarity to boost
structurally important code in search results.
"""

import logging
from typing import Optional

import networkx as nx


logger = logging.getLogger(__name__)


class CentralityRanker:
    """Ranks search results by blending semantic scores with centrality.

    Two modes:
    - annotate(): Add centrality field without reordering
    - rerank(): Add centrality + reorder by blended score
    """

    def __init__(
        self,
        graph_query_engine,
        method: str = "pagerank",
        alpha: float = 0.3,
    ):
        """Initialize centrality ranker.

        Args:
            graph_query_engine: GraphQueryEngine instance
            method: Centrality method (pagerank, degree, betweenness, closeness)
            alpha: Blending weight (0=semantic only, 1=centrality only)
        """
        self.graph_query_engine = graph_query_engine
        self.method = method
        self.alpha = alpha

        # Cache centrality scores to avoid recomputation
        self._cache: dict[str, float] = {}
        self._cache_node_count = 0

    def _get_centrality_scores(self) -> dict[str, float]:
        """Compute and cache centrality scores.

        Uses node count for cache invalidation (graph rebuild detection).
        Normalizes scores to [0, 1] range.

        Returns:
            dict mapping chunk_id -> normalized centrality score [0, 1]
        """
        current_node_count = self.graph_query_engine.storage.graph.number_of_nodes()

        # Invalidate cache if node count changed
        if current_node_count != self._cache_node_count:
            self._cache.clear()
            self._cache_node_count = current_node_count

        # Return cached scores if available
        if self._cache:
            return self._cache

        # Handle empty graph
        if current_node_count == 0:
            logger.debug("[CENTRALITY] Empty graph, returning empty scores")
            return {}

        # Compute centrality scores
        try:
            raw_scores = self.graph_query_engine.compute_centrality(method=self.method)
        except nx.PowerIterationFailedConvergence:
            logger.warning(
                "[CENTRALITY] PageRank failed to converge, returning empty scores"
            )
            return {}
        except Exception as e:
            logger.error(
                f"[CENTRALITY] Failed to compute {self.method} centrality: {e}"
            )
            return {}

        # Normalize to [0, 1] range
        if raw_scores:
            max_score = max(raw_scores.values())
            if max_score > 0:
                self._cache = {
                    chunk_id: score / max_score
                    for chunk_id, score in raw_scores.items()
                }
            else:
                self._cache = dict.fromkeys(raw_scores, 0.0)
        else:
            self._cache = {}

        logger.debug(
            f"[CENTRALITY] Computed {len(self._cache)} scores "
            f"(method={self.method}, max={max_score:.4f})"
        )

        return self._cache

    def annotate(self, results: list[dict]) -> list[dict]:
        """Add centrality scores to results without reordering.

        Args:
            results: List of search result dicts

        Returns:
            Results with added "centrality" field
        """
        centrality_scores = self._get_centrality_scores()

        for result in results:
            chunk_id = result.get("chunk_id")
            if chunk_id:
                centrality = centrality_scores.get(chunk_id, 0.0)
                result["centrality"] = round(centrality, 4)

        return results

    def rerank(self, results: list[dict], alpha: Optional[float] = None) -> list[dict]:
        """Rerank results by blended semantic + centrality score.

        Args:
            results: List of search result dicts with "score" field
            alpha: Blending weight override (None = use self.alpha)

        Returns:
            Reranked results with "centrality" and "blended_score" fields
        """
        # First, annotate with centrality scores
        results = self.annotate(results)

        # Use provided alpha or fall back to instance alpha
        # CRITICAL: Use `if alpha is not None` to handle alpha=0.0 correctly
        blend_alpha = alpha if alpha is not None else self.alpha

        # Compute blended scores and sort
        for result in results:
            semantic_score = result.get("score", 0.0)
            centrality = result.get("centrality", 0.0)

            # Blend: (1 - alpha) * semantic + alpha * centrality
            blended = (1 - blend_alpha) * semantic_score + blend_alpha * centrality
            result["blended_score"] = round(blended, 4)

        # Sort by blended score descending
        results.sort(key=lambda r: r.get("blended_score", 0.0), reverse=True)

        logger.debug(
            f"[CENTRALITY] Reranked {len(results)} results (alpha={blend_alpha:.2f})"
        )

        return results
