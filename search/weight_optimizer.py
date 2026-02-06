"""Weight optimization for hybrid search.

This module provides weight optimization utilities for finding optimal
BM25/dense weight combinations through grid search.
"""

import logging
from collections.abc import Callable


class WeightOptimizer:
    """Optimizes BM25/dense weights based on search quality metrics.

    This class performs grid search over weight combinations to find the
    optimal balance between BM25 and dense search results.

    Example:
        >>> def search_fn(query, k):
        ...     return searcher.search(query, k=k, use_parallel=False)
        >>> def analyze_fn(results):
        ...     return searcher.reranker.analyze_fusion_quality(results)
        >>> def set_weights_fn(bm25_w, dense_w):
        ...     searcher.bm25_weight = bm25_w
        ...     searcher.dense_weight = dense_w
        >>> def get_weights_fn():
        ...     return (searcher.bm25_weight, searcher.dense_weight)
        >>> optimizer = WeightOptimizer(search_fn, analyze_fn, set_weights_fn, get_weights_fn)
        >>> results = optimizer.optimize(test_queries)
    """

    DEFAULT_COMBINATIONS = [
        (0.2, 0.8),
        (0.3, 0.7),
        (0.4, 0.6),
        (0.5, 0.5),
        (0.6, 0.4),
        (0.7, 0.3),
        (0.8, 0.2),
    ]

    def __init__(
        self,
        search_callback: Callable[[str, int], list],
        analyze_callback: Callable[[list], dict],
        set_weights_callback: Callable[[float, float], None],
        get_weights_callback: Callable[[], tuple[float, float]],
        logger: logging.Logger | None = None,
    ):
        """
        Initialize weight optimizer with callbacks.

        Args:
            search_callback: Function(query, k) -> results for running searches
            analyze_callback: Function(results) -> quality metrics dict
            set_weights_callback: Function(bm25_w, dense_w) to set weights
            get_weights_callback: Function() -> (bm25_w, dense_w) to get current weights
            logger: Optional logger instance

        Example:
            >>> optimizer = WeightOptimizer(
            ...     search_callback=lambda q, k: searcher.search(q, k=k),
            ...     analyze_callback=lambda r: searcher.reranker.analyze_fusion_quality(r),
            ...     set_weights_callback=lambda b, d: setattr(searcher, 'bm25_weight', b),
            ...     get_weights_callback=lambda: (searcher.bm25_weight, searcher.dense_weight),
            ... )
        """
        self.search_callback = search_callback
        self.analyze_callback = analyze_callback
        self.set_weights_callback = set_weights_callback
        self.get_weights_callback = get_weights_callback
        self._logger = logger or logging.getLogger(__name__)

    def optimize(
        self,
        test_queries: list[str],
        weight_combinations: list[tuple[float, float]] | None = None,
        ground_truth: list[list[str]] | None = None,
    ) -> dict[str, float]:
        """
        Find optimal weights using grid search.

        Evaluates each weight combination by:
        1. Setting the weights temporarily
        2. Running searches on test queries
        3. Analyzing result quality using analyze_callback
        4. Calculating composite score from quality metrics
        5. Selecting combination with highest score

        Args:
            test_queries: Queries to evaluate weights against
            weight_combinations: Weight pairs to test (default: DEFAULT_COMBINATIONS)
            ground_truth: Optional ground truth results for each query (currently unused)

        Returns:
            Dict with optimal weights and metrics:
                - bm25_weight: Optimal BM25 weight
                - dense_weight: Optimal dense weight
                - optimization_score: Best composite score achieved
                - tested_combinations: Number of combinations tested

        Example:
            >>> results = optimizer.optimize(
            ...     test_queries=["error handling", "database connection"],
            ...     weight_combinations=[(0.3, 0.7), (0.5, 0.5), (0.7, 0.3)],
            ... )
            >>> print(f"Optimal: BM25={results['bm25_weight']}, Dense={results['dense_weight']}")
        """
        if weight_combinations is None:
            weight_combinations = self.DEFAULT_COMBINATIONS

        self._logger.info(f"Optimizing weights with {len(test_queries)} test queries")

        # Get current weights to restore later if needed
        current_weights = self.get_weights_callback()
        best_weights = current_weights
        best_score = 0.0

        for bm25_w, dense_w in weight_combinations:
            # Temporarily set weights
            orig_weights = self.get_weights_callback()
            self.set_weights_callback(bm25_w, dense_w)

            total_score = 0.0
            for query in test_queries:
                # Run search with current weights
                results = self.search_callback(query, k=10)

                # Score based on result quality metrics
                if results:
                    analysis = self.analyze_callback(results)
                    # Composite score from multiple quality metrics
                    score = (
                        analysis["diversity_score"] * 0.4
                        + analysis["coverage_balance"] * 0.3
                        + analysis["high_quality_ratio"] * 0.3
                    )
                    total_score += score

            avg_score = total_score / len(test_queries) if test_queries else 0.0

            if avg_score > best_score:
                best_score = avg_score
                best_weights = (bm25_w, dense_w)

            # Restore original weights for next iteration
            self.set_weights_callback(*orig_weights)

        # Set optimal weights
        self.set_weights_callback(*best_weights)

        self._logger.info(
            f"Optimized weights: BM25={best_weights[0]:.2f}, "
            f"Dense={best_weights[1]:.2f} (score: {best_score:.3f})"
        )

        return {
            "bm25_weight": best_weights[0],
            "dense_weight": best_weights[1],
            "optimization_score": best_score,
            "tested_combinations": len(weight_combinations),
        }
