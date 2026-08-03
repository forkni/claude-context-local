"""Search execution engine for BM25 and dense semantic search.

Handles the core search execution logic including parallel/sequential search,
BM25 and dense vector search, and performance statistics tracking.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from search.config import SearchMode
from utils.observability import wrap_in_context
from utils.timing import timed

from .filters import FilterEngine
from .reranker import SearchResult
from .result_factory import ResultFactory
from .types import RetrievalRequest


class SearchExecutor:
    """Executes BM25 and dense semantic searches with parallel/sequential modes.

    Extracted from HybridSearcher to isolate search execution logic.
    """

    def __init__(
        self,
        bm25_index,  # BM25Index
        dense_index,  # CodeIndexManager
        embedder,  # CodeEmbedder
        reranker,  # RRFReranker
        reranking_engine,  # RerankingEngine
        gpu_monitor,  # GPUMemoryMonitor
        max_workers: int = 2,
        logger: logging.Logger | None = None,
    ):
        """
        Initialize search executor.

        Args:
            bm25_index: BM25 sparse index instance
            dense_index: Dense vector index instance (CodeIndexManager)
            embedder: CodeEmbedder for query embedding generation
            reranker: RRFReranker for result fusion
            reranking_engine: RerankingEngine for neural reranking
            gpu_monitor: GPUMemoryMonitor for VRAM tracking
            max_workers: Maximum thread pool workers
            logger: Optional logger instance
        """
        self.bm25_index = bm25_index
        self.dense_index = dense_index
        self.embedder = embedder
        self.reranker = reranker
        self.reranking_engine = reranking_engine
        self.gpu_monitor = gpu_monitor

        self.max_workers = max_workers

        self._logger = logger or logging.getLogger(__name__)
        self._thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._shutdown_lock = threading.Lock()
        self._is_shutdown = False

        # Performance tracking
        self._search_stats = {
            "total_searches": 0,
            "bm25_time": 0.0,
            "dense_time": 0.0,
            "rerank_time": 0.0,
            "parallel_efficiency": 0.0,
            "last_bm25_time": 0.0,
            "last_dense_time": 0.0,
        }

    def execute_single_hop(
        self,
        request: RetrievalRequest,
        query_embedding: np.ndarray | None = None,
    ) -> list[SearchResult]:
        """
        Execute single-hop search (direct query matching).

        Args:
            request: The RetrievalRequest this leg executes against.
            query_embedding: Pre-computed query embedding (optional, for caching)

        Returns:
            Search results from single-hop search
        """
        query = request.query
        k = request.k
        search_mode = request.search_mode
        use_parallel = request.use_parallel
        min_bm25_score = request.min_bm25_score
        filters = request.filters
        config = request.config

        self._logger.debug(f"{search_mode.title()} search for: '{query}' (k={k})")

        start_time = time.time()
        bm25_results = []
        dense_results = []

        # Handle different search modes
        if search_mode == SearchMode.BM25:
            # BM25-only search
            bm25_results = self.search_bm25(query, k, min_bm25_score, filters)
            # Convert BM25 results to SearchResult format
            final_results = ResultFactory.from_bm25_results(bm25_results)
            rerank_time = 0.0  # No reranking for single mode

        elif search_mode == SearchMode.SEMANTIC:
            # Dense-only search
            dense_results = self.search_dense(query, k, filters, query_embedding)
            # Convert dense results to SearchResult format
            final_results = ResultFactory.from_dense_results(dense_results)
            rerank_time = 0.0  # No reranking for single mode

        else:  # hybrid mode
            # Widened funnel (R1a): retrieve enough per leg that the fused pool
            # can actually fill the neural reranker's candidate budget
            # (reranker.top_k_candidates, deployed 30) instead of starving it at
            # k*2. Exact FlatIP dense search makes the wider sweep ~free.
            reranker_budget = config.reranker.top_k_candidates
            search_k = max(reranker_budget, k * 5)

            if use_parallel and not self._is_shutdown:
                # Parallel execution
                bm25_results, dense_results = self._parallel_search(
                    query, search_k, min_bm25_score, filters, query_embedding
                )
            else:
                # Sequential execution
                bm25_results, dense_results = self._sequential_search(
                    query, search_k, min_bm25_score, filters, query_embedding
                )

            # Resolved once, upstream in HybridSearcher.search — never None
            # here (ADR-0018 deletes the is-not-None fallback that used to
            # hide a dropped weight as a stale construction-time default).
            eff_bm25 = request.bm25_weight
            eff_dense = request.dense_weight

            # Curated-vocabulary query expansion (opt-in): matched concepts add
            # discounted variant legs to the fusion below. Disabled or unmatched
            # queries skip this entirely and take the exact rerank_simple path.
            variant_legs: list[list[SearchResult]] = []
            variant_weights: list[float] = []
            qe_cfg = config.query_expansion
            if qe_cfg.enabled:
                variant_legs, variant_weights = self._build_variant_legs(
                    query,
                    search_k,
                    min_bm25_score,
                    filters,
                    qe_cfg,
                    eff_bm25,
                    eff_dense,
                )

            # Rerank results
            rerank_start = time.time()
            self._logger.debug(
                f"[RERANK] Using weights: BM25={eff_bm25}, Dense={eff_dense}, "
                f"BM25_results={len(bm25_results)}, Dense_results={len(dense_results)}"
            )
            # Keep the fused pool at the reranker budget rather than k: RRF
            # ordering decides *membership* of the neural-rerank pool, the
            # neural reranker decides the final top-k. When reranking is
            # disabled/unavailable, apply_neural_reranking returns the pool
            # unchanged and the [:k] below reproduces the old RRF top-k.
            fusion_k = max(k, reranker_budget)
            if variant_legs:
                # Generic N-list fusion: primary legs keep their weights,
                # variant legs enter discounted; reserved slots stay pointed
                # at the primary BM25 leg (index 0) — the bm25_reserved_slots
                # interaction is unchanged, not extended to variant legs.
                # Same tuple->SearchResult conversion rerank_simple performs
                primary_bm25 = [
                    SearchResult(chunk_id=c, score=s, metadata=m, source="bm25")
                    for c, s, m in bm25_results
                ]
                primary_dense = [
                    SearchResult(chunk_id=c, score=s, metadata=m, source="dense")
                    for c, s, m in dense_results
                ]
                final_results = self.reranker.rerank(
                    results_lists=[primary_bm25, primary_dense, *variant_legs],
                    weights=[eff_bm25, eff_dense, *variant_weights],
                    max_results=fusion_k,
                    reserved_slots=config.search_mode.bm25_reserved_slots,
                    reserve_list_idx=0,
                )
            else:
                final_results = self.reranker.rerank_simple(
                    bm25_results=bm25_results,
                    dense_results=dense_results,
                    max_results=fusion_k,
                    bm25_weight=eff_bm25,
                    dense_weight=eff_dense,
                    reserved_slots=config.search_mode.bm25_reserved_slots,
                )
            rerank_time = time.time() - rerank_start
            self._logger.debug(
                f"[RERANK] Produced {len(final_results)} results in {rerank_time:.3f}s"
            )

            # Neural reranking (Quality First mode) - delegate to reranking_engine.
            # Skipped under reranker.single_pass: the one listwise pass runs at
            # the tail of HybridSearcher.search(); hop-1 seeds keep RRF order.
            if len(final_results) > 0 and not config.reranker.single_pass:
                final_results = self.reranking_engine.apply_neural_reranking(
                    query, final_results, k, context="search", config=config
                )
            final_results = final_results[:k]

        # Update statistics and log completion
        total_time = time.time() - start_time
        self._update_search_stats(
            search_mode=search_mode,
            use_parallel=use_parallel,
            rerank_time=rerank_time,
            total_time=total_time,
            results_count=len(final_results),
            bm25_count=len(bm25_results),
            dense_count=len(dense_results),
        )

        return final_results

    def _build_variant_legs(
        self,
        query: str,
        search_k: int,
        min_bm25_score: float,
        filters: dict[str, Any] | None,
        qe_cfg,  # QueryExpansionConfig
        bm25_weight: float,
        dense_weight: float,
    ) -> tuple[list[list[SearchResult]], list[float]]:
        """Build discounted fusion legs for concepts matched by query expansion.

        One leg per matched concept per enabled backend (BM25 and/or dense),
        each searched with the original query plus the concept's terms and
        weighted at ``base_leg_weight * variant_weight_discount``. Returns
        ``([], [])`` when no concept matches, keeping the caller on the
        unexpanded fusion path.
        """
        from search.query_expansion import build_variant_query, match_concepts

        matches = match_concepts(query, qe_cfg.variants_path, qe_cfg.max_variants)
        if not matches:
            return [], []

        legs: list[list[SearchResult]] = []
        weights: list[float] = []
        for concept, terms in matches:
            variant_query = build_variant_query(query, terms)
            self._logger.debug(
                f"[QUERY-EXPANSION] concept={concept} variant_query={variant_query!r}"
            )
            if qe_cfg.apply_to_bm25:
                tuples = self.search_bm25(
                    variant_query, search_k, min_bm25_score, filters
                )
                legs.append(
                    [
                        SearchResult(
                            chunk_id=c, score=s, metadata=m, source="bm25_variant"
                        )
                        for c, s, m in tuples
                    ]
                )
                weights.append(bm25_weight * qe_cfg.variant_weight_discount)
            if qe_cfg.apply_to_dense:
                tuples = self.search_dense(variant_query, search_k, filters)
                legs.append(
                    [
                        SearchResult(
                            chunk_id=c, score=s, metadata=m, source="dense_variant"
                        )
                        for c, s, m in tuples
                    ]
                )
                weights.append(dense_weight * qe_cfg.variant_weight_discount)
        return legs, weights

    def _parallel_search(
        self,
        query: str,
        k: int,
        min_bm25_score: float,
        filters: dict[str, Any] | None,
        query_embedding: np.ndarray | None = None,
    ) -> tuple[list[tuple], list[tuple]]:
        """Execute BM25 and dense search in parallel using shared thread pool."""
        try:
            # Reuse existing thread pool instead of creating new one per search
            # This avoids ~1-2ms overhead of ThreadPoolExecutor creation
            bm25_future = self._thread_pool.submit(
                wrap_in_context(self.search_bm25), query, k, min_bm25_score, filters
            )
            dense_future = self._thread_pool.submit(
                wrap_in_context(self.search_dense), query, k, filters, query_embedding
            )

            # Wait for results with timeout to prevent deadlocks
            bm25_results = bm25_future.result(timeout=30.0)
            dense_results = dense_future.result(timeout=30.0)

            return bm25_results, dense_results

        except Exception as e:  # noqa: BLE001 - resilience: parallel search failure, falls back to sequential search
            self._logger.warning(
                f"Parallel search failed, falling back to sequential: {e}"
            )
            return self._sequential_search(
                query, k, min_bm25_score, filters, query_embedding
            )

    def _sequential_search(
        self,
        query: str,
        k: int,
        min_bm25_score: float,
        filters: dict[str, Any] | None,
        query_embedding: np.ndarray | None = None,
    ) -> tuple[list[tuple], list[tuple]]:
        """Execute BM25 and dense search sequentially."""
        bm25_results = self.search_bm25(query, k, min_bm25_score, filters)
        dense_results = self.search_dense(query, k, filters, query_embedding)
        return bm25_results, dense_results

    @timed("bm25_search")
    def search_bm25(
        self, query: str, k: int, min_score: float, filters: dict | None = None
    ) -> list[tuple]:
        """Search using BM25 index with optional filtering."""
        start_time = time.time()
        try:
            # Get more results if filtering, to ensure enough after filter
            # Use higher multiplier for directory filters (can exclude 50%+ of results)
            if filters and ("include_dirs" in filters or "exclude_dirs" in filters):
                search_k = k * 5
            elif filters:
                search_k = k * 3
            else:
                search_k = k
            results = self.bm25_index.search(query, search_k, min_score)

            # Apply filters post-search
            if filters and results:
                # Build the filter engine once — filters are loop-invariant, so
                # rebuilding it per-candidate below was wasted work on every hit.
                filter_engine = FilterEngine.from_dict(filters)
                filtered_results = []
                for result in results:
                    # BM25 results are (chunk_id, score, metadata)
                    if len(result) >= 3:
                        _chunk_id, _score, metadata = result[0], result[1], result[2]
                    else:
                        # Skip malformed results
                        continue

                    if filter_engine.matches(metadata):
                        filtered_results.append(result)
                        if len(filtered_results) >= k:
                            break
                results = filtered_results
            else:
                results = results[:k]

            search_time = time.time() - start_time

            self._search_stats["bm25_time"] += search_time
            self._search_stats["last_bm25_time"] = search_time

            self._logger.debug(
                f"BM25 search: {len(results)} results in {search_time:.3f}s"
            )
            return results

        except Exception as e:
            # Intentionally broad: this is the "search never crashes" resilience
            # boundary — sequential/single-mode callers have no outer guard, and
            # RuntimeError -> [] is pinned by test_search_executor.py.
            self._logger.error(f"BM25 search failed: {e}", exc_info=True)
            return []

    @timed("dense_search")
    def search_dense(
        self,
        query: str,
        k: int,
        filters: dict | None,
        query_embedding: np.ndarray | None = None,
    ) -> list[tuple]:
        """Search using dense vector index."""
        start_time = time.time()
        try:
            # Only compute embedding if not provided (caching optimization)
            if query_embedding is None:
                # Use stored embedder or create one if not provided
                if self.embedder is None:
                    self._logger.warning(
                        "No embedder provided to SearchExecutor, creating new instance"
                    )
                    from pathlib import Path

                    from embeddings.embedder import CodeEmbedder

                    # Use same cache directory as main embedder
                    cache_dir = Path.home() / ".claude_code_search" / "models"
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    self.embedder = CodeEmbedder(cache_dir=str(cache_dir))
                    self._logger.info(
                        "Created new CodeEmbedder instance for semantic search"
                    )

                query_embedding = self.embedder.embed_query(query)

            # Search in dense index
            results = self.dense_index.search(query_embedding, k, filters)

            search_time = time.time() - start_time
            self._search_stats["dense_time"] += search_time
            self._search_stats["last_dense_time"] = search_time

            self._logger.debug(
                f"Dense search: {len(results)} results in {search_time:.3f}s"
            )
            return results

        except Exception as e:
            # Intentionally broad: same resilience boundary as search_bm25 above —
            # no outer guard on the sequential/single-mode search paths, and
            # behavior here is test-pinned.
            self._logger.error(f"Dense search failed: {e}", exc_info=True)
            import traceback

            self._logger.error(
                f"Dense search exception details: {traceback.format_exc()}"
            )
            return []

    def _update_search_stats(
        self,
        search_mode: str,
        use_parallel: bool,
        rerank_time: float,
        total_time: float,
        results_count: int,
        bm25_count: int = 0,
        dense_count: int = 0,
    ) -> None:
        """Update search performance statistics and log completion.

        Args:
            search_mode: Search mode used ("bm25", "semantic", or "hybrid")
            use_parallel: Whether parallel execution was used
            rerank_time: Time spent on reranking (seconds)
            total_time: Total search time (seconds)
            results_count: Number of results returned
            bm25_count: Number of BM25 results (for hybrid mode logging)
            dense_count: Number of dense results (for hybrid mode logging)
        """
        # Update statistics
        self._search_stats["total_searches"] += 1
        self._search_stats["rerank_time"] += rerank_time

        # Calculate parallel efficiency if applicable
        if use_parallel:
            parallel_time = max(
                self._search_stats.get("last_bm25_time", 0),
                self._search_stats.get("last_dense_time", 0),
            )
            sequential_time = self._search_stats.get(
                "last_bm25_time", 0
            ) + self._search_stats.get("last_dense_time", 0)
            if sequential_time > 0:
                efficiency = 1.0 - (parallel_time / sequential_time)
                self._search_stats["parallel_efficiency"] = efficiency

        # Mode-specific logging
        if search_mode == SearchMode.BM25:
            self._logger.debug(
                f"BM25 search complete: {results_count} results, "
                f"Total time: {total_time:.3f}s"
            )
        elif search_mode == SearchMode.SEMANTIC:
            self._logger.debug(
                f"Semantic search complete: {results_count} results, "
                f"Total time: {total_time:.3f}s"
            )
        else:  # hybrid
            self._logger.debug(
                f"Hybrid search complete: {results_count} results, "
                f"BM25: {bm25_count}, Dense: {dense_count}, "
                f"Total time: {total_time:.3f}s"
            )

    @property
    def stats(self) -> dict[str, Any]:
        """Get search performance statistics."""
        return self._search_stats.copy()

    @property
    def is_shutdown(self) -> bool:
        """Check if executor is shutdown."""
        return self._is_shutdown

    def shutdown(self) -> None:
        """Shutdown the thread pool."""
        with self._shutdown_lock:
            if not self._is_shutdown:
                self._thread_pool.shutdown(wait=True)
                self._is_shutdown = True
                self._logger.info("SearchExecutor shut down")
