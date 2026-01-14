"""RRF (Reciprocal Rank Fusion) reranking implementation."""

import logging
import math
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SearchResult:
    """Unified search result format."""

    chunk_id: str
    score: float
    metadata: dict[str, Any]
    source: str = "unknown"  # "bm25", "dense", "hybrid"
    rank: int = 0  # Original rank in source list


class RRFReranker:
    """Reciprocal Rank Fusion (RRF) reranker for combining multiple result lists."""

    def __init__(self, k: int = 100, alpha: float = 0.5) -> None:
        """Initialize RRF reranker.

        Args:
            k: RRF parameter for smoothing (higher = less emphasis on rank)
            alpha: Weight balance between first and second list (0.0 to 1.0)
                  0.5 = equal weight, 0.7 = favor first list, 0.3 = favor second list
        """
        self.k = k
        self.alpha = alpha
        self._logger = logging.getLogger(__name__)

    def rerank(
        self,
        results_lists: list[list[SearchResult]],
        weights: Optional[list[float]] = None,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """
        Rerank multiple result lists using RRF.

        Args:
            results_lists: List of result lists to combine
            weights: Optional weights for each list (default: equal weights)
            max_results: Maximum number of results to return

        Returns:
            Combined and reranked results
        """
        if not results_lists or all(not results for results in results_lists):
            return []

        # Default to equal weights
        if weights is None:
            weights = [1.0] * len(results_lists)

        if len(weights) != len(results_lists):
            raise ValueError("Number of weights must match number of result lists")

        # Normalize weights
        total_weight = sum(weights)
        original_weights = weights.copy()
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(results_lists)] * len(results_lists)

        self._logger.debug(
            f"[RRF] Weights - Original: {original_weights}, Normalized: {weights}, k={self.k}"
        )

        # Calculate RRF scores for each document
        rrf_scores: dict[str, float] = {}
        doc_results: dict[str, SearchResult] = {}
        list_appearances: dict[str, list[int]] = (
            {}
        )  # Track which lists contain each doc

        for list_idx, (results, weight) in enumerate(
            zip(results_lists, weights, strict=False)
        ):
            for rank, result in enumerate(results, 1):  # Rank starts from 1
                chunk_id = result.chunk_id

                # Calculate RRF score contribution from this list
                rrf_contribution = weight * (1.0 / (self.k + rank))

                # Add to total RRF score
                if chunk_id in rrf_scores:
                    rrf_scores[chunk_id] += rrf_contribution
                else:
                    rrf_scores[chunk_id] = rrf_contribution

                # Store the result (use the one with highest original score)
                if (
                    chunk_id not in doc_results
                    or result.score > doc_results[chunk_id].score
                ):
                    # Create a copy with updated information
                    combined_result = SearchResult(
                        chunk_id=result.chunk_id,
                        score=result.score,  # Keep original score
                        metadata=result.metadata,
                        source="hybrid",
                        rank=rank,
                    )
                    doc_results[chunk_id] = combined_result

                # Track list appearances
                if chunk_id not in list_appearances:
                    list_appearances[chunk_id] = []
                list_appearances[chunk_id].append(list_idx)

        # Sort by RRF score (descending)
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        # Create final results with RRF scores
        final_results = []
        for rank, (chunk_id, rrf_score) in enumerate(sorted_docs[:max_results], 1):
            result = doc_results[chunk_id]

            # Update metadata with RRF information
            result.metadata["rrf_score"] = rrf_score
            result.metadata["appears_in_lists"] = len(list_appearances[chunk_id])
            result.metadata["final_rank"] = rank

            final_results.append(result)

        self._logger.debug(
            f"RRF reranked {len(final_results)} results from "
            f"{len(results_lists)} lists with k={self.k}"
        )

        return final_results

    def rerank_simple(
        self,
        bm25_results: list[tuple[str, float, dict]],
        dense_results: list[tuple[str, float, dict]],
        max_results: int = 10,
        bm25_weight: float = 0.4,
        dense_weight: float = 0.6,
    ) -> list[SearchResult]:
        """
        Simple reranking for BM25 + dense vector results.

        Args:
            bm25_results: BM25 results as (chunk_id, score, metadata)
            dense_results: Dense results as (chunk_id, score, metadata)
            max_results: Maximum results to return
            bm25_weight: Weight for BM25 results (0.0 to 1.0)
            dense_weight: Weight for dense results (0.0 to 1.0)

        Returns:
            Combined and reranked results
        """
        # Convert tuples to SearchResult objects
        bm25_search_results = [
            SearchResult(
                chunk_id=chunk_id, score=score, metadata=metadata, source="bm25"
            )
            for chunk_id, score, metadata in bm25_results
        ]

        dense_search_results = [
            SearchResult(
                chunk_id=chunk_id, score=score, metadata=metadata, source="dense"
            )
            for chunk_id, score, metadata in dense_results
        ]

        # Use main rerank method
        return self.rerank(
            results_lists=[bm25_search_results, dense_search_results],
            weights=[bm25_weight, dense_weight],
            max_results=max_results,
        )

    def analyze_fusion_quality(
        self, results: list[SearchResult], threshold: float = 0.5
    ) -> dict[str, Any]:
        """
        Analyze the quality of fusion results.

        Args:
            results: Fusion results to analyze
            threshold: Threshold for considering a result "high quality"

        Returns:
            Analysis metrics
        """
        if not results:
            return {
                "total_results": 0,
                "high_quality_count": 0,
                "diversity_score": 0.0,
                "coverage_balance": 0.0,
            }

        # Count high-quality results
        high_quality = sum(
            1 for r in results if r.metadata.get("rrf_score", 0) > threshold
        )

        # Calculate source diversity
        source_counts = {}
        for result in results:
            source = result.source
            source_counts[source] = source_counts.get(source, 0) + 1

        # Diversity score: how evenly distributed are the sources
        total_results = len(results)
        if len(source_counts) > 1:
            expected_per_source = total_results / len(source_counts)
            diversity_score = 1.0 - sum(
                abs(count - expected_per_source) / total_results
                for count in source_counts.values()
            ) / len(source_counts)
        else:
            diversity_score = 0.0  # Only one source

        # Coverage balance: how many results appear in multiple lists
        multi_list_count = sum(
            1 for r in results if r.metadata.get("appears_in_lists", 0) > 1
        )
        coverage_balance = (
            multi_list_count / total_results if total_results > 0 else 0.0
        )

        return {
            "total_results": total_results,
            "high_quality_count": high_quality,
            "high_quality_ratio": high_quality / total_results,
            "diversity_score": diversity_score,
            "coverage_balance": coverage_balance,
            "source_distribution": source_counts,
            "avg_rrf_score": sum(r.metadata.get("rrf_score", 0) for r in results)
            / total_results,
            "rrf_score_std": self._calculate_std(
                [r.metadata.get("rrf_score", 0) for r in results]
            ),
        }

    def _calculate_std(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def tune_parameters(
        self,
        results_lists: list[list[SearchResult]],
        ground_truth: Optional[list[str]] = None,
        k_values: list[int] = None,
        weight_combinations: list[list[float]] = None,
    ) -> dict[str, Any]:
        """
        Tune RRF parameters for optimal performance.

        Args:
            results_lists: Result lists for tuning
            ground_truth: Optional ground truth for evaluation
            k_values: K values to try (default: [10, 50, 100, 200])
            weight_combinations: Weight combinations to try

        Returns:
            Best parameters and their performance
        """
        if k_values is None:
            k_values = [10, 50, 100, 200]

        if weight_combinations is None:
            weight_combinations = [
                [0.5, 0.5],  # Equal
                [0.3, 0.7],  # Favor dense
                [0.7, 0.3],  # Favor sparse
                [0.4, 0.6],  # Slight dense preference
                [0.6, 0.4],  # Slight sparse preference
            ]

        best_params = {"k": self.k, "weights": [0.5, 0.5]}
        best_score = 0.0

        for k in k_values:
            for weights in weight_combinations:
                if len(weights) != len(results_lists):
                    continue

                # Test this configuration
                temp_reranker = RRFReranker(k=k)
                results = temp_reranker.rerank(results_lists, weights)

                # Score based on fusion quality metrics
                analysis = self.analyze_fusion_quality(results)
                score = (
                    analysis["diversity_score"] * 0.4
                    + analysis["coverage_balance"] * 0.3
                    + analysis["high_quality_ratio"] * 0.3
                )

                if score > best_score:
                    best_score = score
                    best_params = {"k": k, "weights": weights}

        return {
            "best_params": best_params,
            "best_score": best_score,
            "tested_configurations": len(k_values) * len(weight_combinations),
        }
