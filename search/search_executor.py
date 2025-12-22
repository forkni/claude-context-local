"""Search execution engine for BM25 and dense semantic search.

Handles the core search execution logic including parallel/sequential search,
BM25 and dense vector search, and performance statistics tracking.
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .filters import FilterEngine
from .reranker import SearchResult
from .result_factory import ResultFactory


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
        bm25_weight: float = 0.4,
        dense_weight: float = 0.6,
        max_workers: int = 2,
        logger: Optional[logging.Logger] = None,
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
            bm25_weight: Weight for BM25 results (0.0 to 1.0)
            dense_weight: Weight for dense results (0.0 to 1.0)
            max_workers: Maximum thread pool workers
            logger: Optional logger instance
        """
        self.bm25_index = bm25_index
        self.dense_index = dense_index
        self.embedder = embedder
        self.reranker = reranker
        self.reranking_engine = reranking_engine
        self.gpu_monitor = gpu_monitor

        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
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
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: Optional[Dict[str, Any]] = None,
        query_embedding: Optional[np.ndarray] = None,
    ) -> List[SearchResult]:
        """
        Execute single-hop search (direct query matching).

        Args:
            query: Search query
            k: Number of results to return
            search_mode: Search mode - "hybrid", "semantic", or "bm25"
            use_parallel: Whether to run BM25 and dense search in parallel
            min_bm25_score: Minimum BM25 score threshold
            filters: Optional filters for dense search
            query_embedding: Pre-computed query embedding (optional, for caching)

        Returns:
            Search results from single-hop search
        """
        self._logger.debug(f"{search_mode.title()} search for: '{query}' (k={k})")

        start_time = time.time()
        bm25_results = []
        dense_results = []

        # Handle different search modes
        if search_mode == "bm25":
            # BM25-only search
            bm25_results = self.search_bm25(query, k, min_bm25_score)
            # Convert BM25 results to SearchResult format
            final_results = ResultFactory.from_bm25_results(bm25_results)
            rerank_time = 0.0  # No reranking for single mode

        elif search_mode == "semantic":
            # Dense-only search
            dense_results = self.search_dense(query, k, filters, query_embedding)
            # Convert dense results to SearchResult format
            final_results = ResultFactory.from_dense_results(dense_results)
            rerank_time = 0.0  # No reranking for single mode

        else:  # hybrid mode
            search_k = k * 2  # Get more results for better reranking

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

            # Rerank results
            rerank_start = time.time()
            self._logger.debug(
                f"[RERANK] Using weights: BM25={self.bm25_weight}, Dense={self.dense_weight}, "
                f"BM25_results={len(bm25_results)}, Dense_results={len(dense_results)}"
            )
            final_results = self.reranker.rerank_simple(
                bm25_results=bm25_results,
                dense_results=dense_results,
                max_results=k,
                bm25_weight=self.bm25_weight,
                dense_weight=self.dense_weight,
            )
            rerank_time = time.time() - rerank_start
            self._logger.debug(
                f"[RERANK] Produced {len(final_results)} results in {rerank_time:.3f}s"
            )

            # Neural reranking (Quality First mode) - delegate to reranking_engine
            if len(final_results) > 0:
                final_results = self.reranking_engine.apply_neural_reranking(
                    query, final_results, k, context="search"
                )

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

    def _parallel_search(
        self,
        query: str,
        k: int,
        min_bm25_score: float,
        filters: Optional[Dict[str, Any]],
        query_embedding: Optional[np.ndarray] = None,
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Execute BM25 and dense search in parallel using shared thread pool."""
        try:
            # Reuse existing thread pool instead of creating new one per search
            # This avoids ~1-2ms overhead of ThreadPoolExecutor creation
            bm25_future = self._thread_pool.submit(
                self.search_bm25, query, k, min_bm25_score, filters
            )
            dense_future = self._thread_pool.submit(
                self.search_dense, query, k, filters, query_embedding
            )

            # Wait for results with timeout to prevent deadlocks
            bm25_results = bm25_future.result(timeout=30.0)
            dense_results = dense_future.result(timeout=30.0)

            return bm25_results, dense_results

        except Exception as e:
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
        filters: Optional[Dict[str, Any]],
        query_embedding: Optional[np.ndarray] = None,
    ) -> Tuple[List[Tuple], List[Tuple]]:
        """Execute BM25 and dense search sequentially."""
        bm25_results = self.search_bm25(query, k, min_bm25_score, filters)
        dense_results = self.search_dense(query, k, filters, query_embedding)
        return bm25_results, dense_results

    def search_bm25(
        self, query: str, k: int, min_score: float, filters: Optional[Dict] = None
    ) -> List[Tuple]:
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
                filtered_results = []
                for result in results:
                    # BM25 results are (chunk_id, score, metadata)
                    if len(result) >= 3:
                        _chunk_id, _score, metadata = result[0], result[1], result[2]
                    else:
                        # Skip malformed results
                        continue

                    if FilterEngine.from_dict(filters).matches(metadata):
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
            self._logger.error(f"BM25 search failed: {e}")
            return []

    def search_dense(
        self,
        query: str,
        k: int,
        filters: Optional[Dict],
        query_embedding: Optional[np.ndarray] = None,
    ) -> List[Tuple]:
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
            self._logger.error(f"Dense search failed: {e}")
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
        if search_mode == "bm25":
            self._logger.debug(
                f"BM25 search complete: {results_count} results, "
                f"Total time: {total_time:.3f}s"
            )
        elif search_mode == "semantic":
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
    def stats(self) -> Dict[str, Any]:
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
