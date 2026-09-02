"""RRF (Reciprocal Rank Fusion) reranking implementation."""

import logging
import math
from dataclasses import dataclass
from typing import Any

from search.types import UNSCORED_SOURCES, ResultSource


# TM2C2 (Bruch, Gai & Ingber, ACM TOIS 2023, arXiv 2210.11934) theoretical
# per-leg score bounds used by RRFReranker.fuse_tm2c2's normalization.
BM25_THEORETICAL_MIN = 0.0
DENSE_THEORETICAL_MIN = -1.0


@dataclass
class SearchResult:
    """Unified search result format."""

    chunk_id: str
    score: float
    metadata: dict[str, Any]
    source: ResultSource = ResultSource.UNKNOWN
    rank: int = 0  # Original rank in source list

    @property
    def is_unscored(self) -> bool:
        """Whether ``score`` is a fabricated placeholder (D9), not a rank signal.

        See ``search.types.UNSCORED_SOURCES`` for which sources qualify and why
        ``graph_hop`` -- despite also stamping 0.0 in some configurations -- is
        deliberately not a static member of that set.
        """
        return self.source in UNSCORED_SOURCES


class RRFReranker:
    """Reciprocal Rank Fusion (RRF) reranker for combining multiple result lists."""

    def __init__(self, k: int = 100, alpha: float = 0.5) -> None:  # pragma: no mutate
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
        weights: list[float] | None = None,
        max_results: int = 10,  # pragma: no mutate
        reserved_slots: int = 0,  # pragma: no mutate
        reserve_list_idx: int = 0,  # pragma: no mutate
    ) -> list[SearchResult]:
        """
        Rerank multiple result lists using RRF.

        Args:
            results_lists: List of result lists to combine
            weights: Optional weights for each list (default: equal weights)
            max_results: Maximum number of results to return
            reserved_slots: Reserve up to this many of the max_results slots for
                candidates unique to results_lists[reserve_list_idx] (present
                there but not selected by RRF score). Fills in that list's rank
                order; unused reserve capacity falls back to RRF order, so 0 —
                or no unique candidates — reproduces plain RRF truncation.
            reserve_list_idx: Which list the reserved slots draw from

        Returns:
            Combined and reranked results
        """
        if not results_lists or all(
            not results for results in results_lists
        ):  # pragma: no mutate
            return []

        # Default to equal weights
        if weights is None:
            weights = [1.0] * len(results_lists)  # pragma: no mutate

        if len(weights) != len(results_lists):  # pragma: no mutate
            raise ValueError("Number of weights must match number of result lists")

        # Normalize weights
        total_weight = sum(weights)
        original_weights = weights.copy()
        if total_weight > 0:  # pragma: no mutate
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(results_lists)] * len(results_lists)

        self._logger.debug(
            f"[RRF] Weights - Original: {original_weights}, Normalized: {weights}, k={self.k}"
        )

        # Calculate RRF scores for each document
        rrf_scores: dict[str, float] = {}
        doc_results: dict[str, SearchResult] = {}
        list_appearances: dict[
            str, list[int]
        ] = {}  # Track which lists contain each doc

        for list_idx, (results, weight) in enumerate(
            zip(results_lists, weights, strict=False)  # pragma: no mutate
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
                    or result.score > doc_results[chunk_id].score  # pragma: no mutate
                ):
                    # Create a copy with updated information
                    combined_result = SearchResult(
                        chunk_id=result.chunk_id,
                        score=result.score,  # Keep original score
                        metadata=result.metadata,
                        source=ResultSource.HYBRID,
                        rank=rank,
                    )
                    doc_results[chunk_id] = combined_result

                # Track list appearances
                if chunk_id not in list_appearances:
                    list_appearances[chunk_id] = []
                list_appearances[chunk_id].append(list_idx)

        # Sort by RRF score (descending)
        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)

        selected_ids = self._select_with_reserve(
            sorted_docs, results_lists, max_results, reserved_slots, reserve_list_idx
        )

        # Create final results with RRF scores
        final_results = []
        for rank, chunk_id in enumerate(selected_ids, 1):  # pragma: no mutate
            result = doc_results[chunk_id]

            # Update metadata with RRF information
            result.metadata["rrf_score"] = rrf_scores[chunk_id]
            result.metadata["appears_in_lists"] = len(list_appearances[chunk_id])
            result.metadata["final_rank"] = rank

            final_results.append(result)

        self._logger.debug(
            f"RRF reranked {len(final_results)} results from "
            f"{len(results_lists)} lists with k={self.k}"
        )

        return final_results

    def _select_with_reserve(
        self,
        sorted_docs: list[tuple[str, float]],
        results_lists: list[list[SearchResult]],
        max_results: int,
        reserved_slots: int,
        reserve_list_idx: int,
    ) -> list[str]:
        """Pick the fused pool: RRF top-N plus reserved slots for one leg.

        Reserved candidates are appended after the RRF-ordered head so that
        with neural reranking disabled a ``[:k]`` cut (k <= head size) is
        unaffected; the neural reranker rescores the whole pool regardless of
        this ordering.
        """
        if (
            reserved_slots <= 0
            or not 0 <= reserve_list_idx < len(results_lists)
            or len(sorted_docs) <= max_results  # pragma: no mutate
        ):
            return [chunk_id for chunk_id, _ in sorted_docs[:max_results]]

        reserve = min(reserved_slots, max_results)
        head = [chunk_id for chunk_id, _ in sorted_docs[: max_results - reserve]]
        selected = set(head)

        # Highest-ranked candidates unique to the reserve list, in list order
        fill: list[str] = []
        for result in results_lists[reserve_list_idx]:
            if len(fill) >= reserve:
                break
            if result.chunk_id not in selected:
                fill.append(result.chunk_id)
                selected.add(result.chunk_id)

        # Unused reserve capacity falls back to RRF order past the head
        if len(head) + len(fill) < max_results:
            for chunk_id, _ in sorted_docs[max_results - reserve :]:
                if len(head) + len(fill) >= max_results:
                    break
                if chunk_id not in selected:
                    fill.append(chunk_id)
                    selected.add(chunk_id)

        if fill:
            self._logger.debug(
                f"[RRF] Reserved {len(fill)} pool slots for list "
                f"{reserve_list_idx} candidates"
            )
        return head + fill

    def rerank_simple(
        self,
        bm25_results: list[tuple[str, float, dict]],
        dense_results: list[tuple[str, float, dict]],
        max_results: int = 10,  # pragma: no mutate
        bm25_weight: float = 0.35,  # pragma: no mutate
        dense_weight: float = 0.65,  # pragma: no mutate
        reserved_slots: int = 0,  # pragma: no mutate
    ) -> list[SearchResult]:
        """
        Simple reranking for BM25 + dense vector results.

        Args:
            bm25_results: BM25 results as (chunk_id, score, metadata)
            dense_results: Dense results as (chunk_id, score, metadata)
            max_results: Maximum results to return
            bm25_weight: Weight for BM25 results (0.0 to 1.0)
            dense_weight: Weight for dense results (0.0 to 1.0)
            reserved_slots: Pool slots reserved for BM25-unique candidates
                (see rerank)

        Returns:
            Combined and reranked results
        """
        # Convert tuples to SearchResult objects
        bm25_search_results = [
            SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source=ResultSource.BM25,
            )
            for chunk_id, score, metadata in bm25_results
        ]

        dense_search_results = [
            SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source=ResultSource.DENSE,
            )
            for chunk_id, score, metadata in dense_results
        ]

        # Use main rerank method
        return self.rerank(
            results_lists=[bm25_search_results, dense_search_results],
            weights=[bm25_weight, dense_weight],
            max_results=max_results,
            reserved_slots=reserved_slots,
            reserve_list_idx=0,
        )

    @staticmethod
    def _theoretical_min_max_normalize(
        scored: list[tuple[str, float]], theoretical_min: float
    ) -> dict[str, float]:
        """Per-leg TM2C2 normalization: ``(score - theoretical_min) / (max - theoretical_min)``.

        ``max`` is the empirical per-query max on this leg. A non-positive
        denominator (degenerate query) yields all-zero norms rather than a
        division error. Lifted verbatim from
        scripts/benchmark/probe_tm2c2_fusion.py's reference implementation —
        keep both in sync if either changes.
        """
        if not scored:
            return {}
        empirical_max = max(score for _, score in scored)
        denom = empirical_max - theoretical_min
        if denom <= 0:
            return {chunk_id: 0.0 for chunk_id, _ in scored}
        return {
            chunk_id: (score - theoretical_min) / denom for chunk_id, score in scored
        }

    def fuse_tm2c2(
        self,
        bm25_results: list[tuple[str, float, dict]],
        dense_results: list[tuple[str, float, dict]],
        alpha: float,
    ) -> list[tuple[str, float]]:
        """Convex combination of theoretical-min-max-normalized leg scores.

        ``alpha`` is the dense-side weight (TM2C2, Bruch/Gai/Ingber, ACM TOIS
        2023, arXiv 2210.11934). Lifted verbatim from
        scripts/benchmark/probe_tm2c2_fusion.py's reference implementation —
        keep both in sync if either changes. Returns ``(chunk_id,
        fused_score)`` sorted descending, the same shape
        ``_select_with_reserve`` consumes.
        """
        bm25_norm = self._theoretical_min_max_normalize(
            [(c, s) for c, s, _ in bm25_results], BM25_THEORETICAL_MIN
        )
        dense_norm = self._theoretical_min_max_normalize(
            [(c, s) for c, s, _ in dense_results], DENSE_THEORETICAL_MIN
        )
        fused: dict[str, float] = {}
        for chunk_id, norm in bm25_norm.items():
            fused[chunk_id] = fused.get(chunk_id, 0.0) + (1 - alpha) * norm
        for chunk_id, norm in dense_norm.items():
            fused[chunk_id] = fused.get(chunk_id, 0.0) + alpha * norm
        return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)

    def rerank_tm2c2(
        self,
        bm25_results: list[tuple[str, float, dict]],
        dense_results: list[tuple[str, float, dict]],
        max_results: int = 10,  # pragma: no mutate
        alpha: float = 0.8,  # pragma: no mutate
        reserved_slots: int = 0,  # pragma: no mutate
    ) -> list[SearchResult]:
        """TM2C2 counterpart to rerank_simple — same shape, different fusion arithmetic.

        Reuses ``_select_with_reserve`` unchanged for the reserved-slots
        mechanism (fuse_tm2c2's output is the same ``(chunk_id, score)``
        shape as RRF's sorted_docs). ``.score`` keeps the leg's original
        score, mirroring ``rerank``'s convention; the fused value lives in
        ``metadata["fusion_score"]``.

        Args:
            bm25_results: BM25 results as (chunk_id, score, metadata)
            dense_results: Dense results as (chunk_id, score, metadata)
            max_results: Maximum results to return
            alpha: TM2C2 dense-side weight (1 - alpha on BM25)
            reserved_slots: Pool slots reserved for BM25-unique candidates
                (see rerank / _select_with_reserve)

        Returns:
            Combined and reranked results
        """
        bm25_search_results = [
            SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source=ResultSource.BM25,
            )
            for chunk_id, score, metadata in bm25_results
        ]
        dense_search_results = [
            SearchResult(
                chunk_id=chunk_id,
                score=score,
                metadata=metadata,
                source=ResultSource.DENSE,
            )
            for chunk_id, score, metadata in dense_results
        ]

        doc_results: dict[str, SearchResult] = {}
        for results in (bm25_search_results, dense_search_results):
            for rank, result in enumerate(results, 1):  # pragma: no mutate
                chunk_id = result.chunk_id
                if (
                    chunk_id not in doc_results
                    or result.score > doc_results[chunk_id].score  # pragma: no mutate
                ):
                    doc_results[chunk_id] = SearchResult(
                        chunk_id=result.chunk_id,
                        score=result.score,
                        metadata=result.metadata,
                        source=ResultSource.HYBRID,
                        rank=rank,
                    )

        fused = self.fuse_tm2c2(bm25_results, dense_results, alpha)
        fused_scores = dict(fused)

        selected_ids = self._select_with_reserve(
            fused,
            [bm25_search_results, dense_search_results],
            max_results,
            reserved_slots,
            0,
        )

        final_results = []
        for rank, chunk_id in enumerate(selected_ids, 1):  # pragma: no mutate
            result = doc_results[chunk_id]
            result.metadata["fusion_score"] = fused_scores[chunk_id]
            result.metadata["fusion_function"] = "tm2c2"
            result.metadata["final_rank"] = rank
            final_results.append(result)

        self._logger.debug(
            f"TM2C2 reranked {len(final_results)} results from 2 lists with "
            f"alpha={alpha}"
        )

        return final_results

    def analyze_fusion_quality(
        self,
        results: list[SearchResult],
        threshold: float = 0.5,  # pragma: no mutate
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
            1
            for r in results
            if r.metadata.get("rrf_score", 0) > threshold  # pragma: no mutate
        )

        # Calculate source diversity
        source_counts = {}
        for result in results:  # pragma: no mutate
            source = result.source
            source_counts[source] = (
                source_counts.get(source, 0) + 1
            )  # pragma: no mutate

        # Diversity score: how evenly distributed are the sources
        total_results = len(results)
        if len(source_counts) > 1:  # pragma: no mutate
            expected_per_source = total_results / len(
                source_counts
            )  # pragma: no mutate
            diversity_score = 1.0 - sum(  # pragma: no mutate
                abs(count - expected_per_source) / total_results  # pragma: no mutate
                for count in source_counts.values()
            ) / len(source_counts)  # pragma: no mutate
        else:
            diversity_score = 0.0  # Only one source  # pragma: no mutate

        # Coverage balance: how many results appear in multiple lists
        multi_list_count = sum(
            1
            for r in results
            if r.metadata.get("appears_in_lists", 0) > 1  # pragma: no mutate
        )
        coverage_balance = (
            multi_list_count / total_results
            if total_results > 0
            else 0.0  # pragma: no mutate
        )

        return {
            "total_results": total_results,
            "high_quality_count": high_quality,
            "high_quality_ratio": high_quality / total_results,  # pragma: no mutate
            "diversity_score": diversity_score,
            "coverage_balance": coverage_balance,
            "source_distribution": source_counts,
            "avg_rrf_score": sum(
                r.metadata.get("rrf_score", 0) for r in results
            )  # pragma: no mutate
            / total_results,  # pragma: no mutate
            "rrf_score_std": self._calculate_std(
                [r.metadata.get("rrf_score", 0) for r in results]  # pragma: no mutate
            ),
        }

    def _calculate_std(self, values: list[float]) -> float:
        """Calculate standard deviation."""
        if not values:
            return 0.0  # pragma: no mutate

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def tune_parameters(
        self,
        results_lists: list[list[SearchResult]],
        ground_truth: list[str] | None = None,
        k_values: list[int] | None = None,
        weight_combinations: list[list[float]] | None = None,
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
            k_values = [10, 50, 100, 200]  # pragma: no mutate

        if weight_combinations is None:
            weight_combinations = [
                [0.5, 0.5],  # Equal  # pragma: no mutate
                [0.3, 0.7],  # Favor dense  # pragma: no mutate
                [0.7, 0.3],  # Favor sparse  # pragma: no mutate
                [0.4, 0.6],  # Slight dense preference  # pragma: no mutate
                [0.6, 0.4],  # Slight sparse preference  # pragma: no mutate
            ]

        best_params = {"k": self.k, "weights": [0.5, 0.5]}  # pragma: no mutate
        best_score = 0.0  # pragma: no mutate

        for k in k_values:  # pragma: no mutate
            for weights in weight_combinations:  # pragma: no mutate
                if len(weights) != len(results_lists):  # pragma: no mutate
                    continue  # pragma: no mutate

                # Test this configuration
                temp_reranker = RRFReranker(k=k)
                results = temp_reranker.rerank(results_lists, weights)

                # Score based on fusion quality metrics
                analysis = self.analyze_fusion_quality(results)
                score = (
                    analysis["diversity_score"] * 0.4  # pragma: no mutate
                    + analysis["coverage_balance"] * 0.3  # pragma: no mutate
                    + analysis["high_quality_ratio"] * 0.3  # pragma: no mutate
                )

                if score > best_score:  # pragma: no mutate
                    best_score = score
                    best_params = {"k": k, "weights": weights}

        return {
            "best_params": best_params,
            "best_score": best_score,
            "tested_configurations": len(k_values)
            * len(weight_combinations),  # pragma: no mutate
        }
