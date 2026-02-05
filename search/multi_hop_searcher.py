"""Multi-hop search expansion logic for discovering interconnected code relationships.

Handles iterative expansion of search results through semantic similarity
to discover related code across multiple hops.
"""

import logging
import time
from typing import Any, Optional

from graph.graph_storage import DEFAULT_EDGE_WEIGHTS
from mcp_server.utils.config_helpers import (
    get_config_via_service_locator as _get_config_via_service_locator,
)
from search.graph_integration import is_chunk_id
from utils.timing import timed

from .reranker import SearchResult as RerankerSearchResult


class MultiHopSearcher:
    """Handles multi-hop semantic search expansion logic.

    Discovers interconnected code relationships by:
    1. Initial query-based search (Hop 1)
    2. Finding similar chunks for each result (Hop 2+)
    3. Re-ranking all discovered chunks by query relevance
    """

    def __init__(
        self,
        embedder,
        dense_index,
        single_hop_callback,  # Callable for _single_hop_search
        reranking_engine,  # RerankingEngine instance
        graph_storage=None,  # CodeGraphStorage instance for graph-based expansion
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize multi-hop searcher.

        Args:
            embedder: CodeEmbedder instance for query embeddings
            dense_index: CodeIndexManager instance for similarity search
            single_hop_callback: Callback to parent's _single_hop_search() method
            reranking_engine: RerankingEngine instance for result reranking
            logger: Optional logger instance
        """
        self.embedder = embedder
        self.dense_index = dense_index
        self._single_hop_search = single_hop_callback
        self.reranking_engine = reranking_engine
        self.graph_storage = graph_storage
        self._logger = logger or logging.getLogger(__name__)

    def validate_params(self, hops: int, expansion_factor: float) -> tuple[int, float]:
        """
        Validate and sanitize multi-hop search parameters.

        Args:
            hops: Number of search hops requested
            expansion_factor: Expansion factor per hop

        Returns:
            Tuple of (validated_hops, validated_expansion_factor)
        """
        validated_hops = hops
        validated_expansion = expansion_factor

        if hops < 1:
            self._logger.warning(f"Invalid hops={hops}, using 1")
            validated_hops = 1

        if expansion_factor < 0 or expansion_factor > 2.0:
            self._logger.warning(
                f"Invalid expansion_factor={expansion_factor}, using 0.3"
            )
            validated_expansion = 0.3

        return validated_hops, validated_expansion

    def expand_from_initial_results(
        self,
        initial_results: list,
        all_chunk_ids: set,
        all_results: dict,
        expansion_k: int,
        hops: int,
        k: int,
    ) -> dict[int, float]:
        """
        Expand search results by finding similar chunks for each initial result.

        Uses batched FAISS search for significant performance improvements (50-100ms savings).

        Args:
            initial_results: Results from initial search (hop 1)
            all_chunk_ids: Set of already discovered chunk IDs (modified in-place)
            all_results: Dict of chunk_id -> result (modified in-place)
            expansion_k: Number of similar chunks to find per result
            hops: Total number of hops to perform
            k: Original k value for limiting expansion sources

        Returns:
            Dict mapping hop number to duration in seconds
        """
        expansion_timings = {}

        for hop in range(2, hops + 1):
            hop_start = time.time()
            hop_discovered = 0

            # Expand from top initial results only (not from previously expanded)
            source_results = initial_results[:k]

            # Collect all chunk_ids for batched search
            chunk_ids_to_expand = [result.chunk_id for result in source_results]

            try:
                # Perform batched search (single FAISS call instead of N individual calls)
                batched_results = self.dense_index.get_similar_chunks_batched(
                    chunk_ids=chunk_ids_to_expand,
                    k=expansion_k,
                )

                # Process batched results
                for result in source_results:
                    similar_chunks_raw = batched_results.get(result.chunk_id, [])

                    # Convert raw results to SearchResult format
                    for cid, similarity, metadata in similar_chunks_raw:
                        if cid not in all_chunk_ids:
                            all_chunk_ids.add(cid)
                            # Convert to reranker.SearchResult format
                            reranker_result = RerankerSearchResult(
                                chunk_id=cid,
                                score=similarity,
                                metadata=metadata,
                                source="multi_hop",
                            )
                            all_results[cid] = reranker_result
                            hop_discovered += 1

            except Exception as e:
                self._logger.warning(
                    f"[MULTI_HOP] Batched search failed for hop {hop}: {e}"
                )
                # Continue without expansion for this hop
                pass

            expansion_timings[hop] = time.time() - hop_start

            self._logger.info(
                f"[MULTI_HOP] Hop {hop}: Discovered {hop_discovered} new chunks "
                f"(total: {len(all_results)}, {expansion_timings[hop] * 1000:.1f}ms)"
            )

        return expansion_timings

    def _graph_expand(
        self,
        initial_results: list,
        all_chunk_ids: set,
        all_results: dict,
        expansion_k: int,
        k: int,
    ) -> dict[int | str, float]:
        """Expand results via graph neighbor traversal (weighted BFS).

        Modifies all_chunk_ids and all_results IN-PLACE.

        Returns:
            Dict mapping hop number/name to duration in seconds.
        """
        expansion_timings = {}

        if not self.graph_storage:
            self._logger.warning(
                "[MULTI_HOP] Graph expansion requested but graph_storage is None"
            )
            return expansion_timings

        hop_start = time.time()
        hop_discovered = 0

        source_results = initial_results[:k]

        for result in source_results:
            # Weighted BFS -- prioritizes calls (1.0) over imports (0.3)
            neighbors: set[str] = self.graph_storage.get_neighbors(
                chunk_id=result.chunk_id,
                max_depth=1,
                edge_weights=DEFAULT_EDGE_WEIGHTS,
            )

            added_for_source = 0
            for neighbor_id in neighbors:
                # Filter symbol_name nodes (e.g. "Exception", "ABC").
                # Real chunk IDs: "file.py:10-20:function:name" (>= 3 colons)
                if not is_chunk_id(neighbor_id):
                    continue

                if neighbor_id in all_chunk_ids:
                    continue

                if added_for_source >= expansion_k:
                    break

                # Look up metadata from dense index
                metadata = self.dense_index.get_chunk_by_id(neighbor_id)
                if metadata is None:
                    continue  # In graph but not in search index

                all_chunk_ids.add(neighbor_id)
                all_results[neighbor_id] = RerankerSearchResult(
                    chunk_id=neighbor_id,
                    score=0.0,  # Reranker assigns final score
                    metadata=metadata,
                    source="graph_hop",
                )
                hop_discovered += 1
                added_for_source += 1

        expansion_timings["graph"] = time.time() - hop_start

        self._logger.info(
            f"[MULTI_HOP] Graph expand: {hop_discovered} new chunks "
            f"(total: {len(all_results)}, {expansion_timings['graph'] * 1000:.1f}ms)"
        )

        return expansion_timings

    def _hybrid_expand(
        self,
        initial_results: list,
        all_chunk_ids: set,
        all_results: dict,
        expansion_k: int,
        hops: int,
        k: int,
    ) -> dict[int | str, float]:
        """Expand using graph neighbors first, then semantic similarity.

        Graph runs first so graph_hop results claim chunk IDs. Semantic
        expansion then naturally skips already-seen IDs, giving graph priority.

        Modifies all_chunk_ids and all_results IN-PLACE.
        """
        # Graph expansion first (claims chunk IDs with source="graph_hop")
        graph_timings = self._graph_expand(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=expansion_k,
            k=k,
        )

        # Semantic expansion (skips IDs already found via graph)
        semantic_timings = self.expand_from_initial_results(
            initial_results=initial_results,
            all_chunk_ids=all_chunk_ids,
            all_results=all_results,
            expansion_k=expansion_k,
            hops=hops,
            k=k,
        )

        # Merge timing dicts (sum durations on collision)
        combined = {}
        for hop_num, duration in graph_timings.items():
            combined[hop_num] = duration
        for hop_num, duration in semantic_timings.items():
            combined[hop_num] = combined.get(hop_num, 0) + duration

        return combined

    def apply_post_expansion_filters(
        self,
        all_results: dict,
        initial_results_count: int,
        filters: Optional[dict[str, Any]],
    ) -> dict:
        """
        Apply filters to expanded results.

        Args:
            all_results: Dict of chunk_id -> result
            initial_results_count: Number of initial results (before expansion)
            filters: Optional filters to apply

        Returns:
            Filtered results dict
        """
        if not filters or len(all_results) <= initial_results_count:
            return all_results

        filtered_results = {}
        for chunk_id, result in all_results.items():
            # Get metadata from dense index
            metadata = self.dense_index.get_chunk_by_id(chunk_id)
            if metadata:
                if self.dense_index._matches_filters(metadata, filters):
                    filtered_results[chunk_id] = result
            else:
                # Keep results without metadata (shouldn't happen)
                filtered_results[chunk_id] = result

        removed_count = len(all_results) - len(filtered_results)
        self._logger.info(
            f"[MULTI_HOP] Applied filters: {len(filtered_results)} results remain "
            f"({removed_count} removed)"
        )

        return filtered_results

    @timed("multi_hop_search")
    def search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        hops: int = 2,
        expansion_factor: float = 0.3,
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: Optional[dict[str, Any]] = None,
    ) -> list:
        """
        Internal multi-hop search implementation.

        Discovers interconnected code relationships by:
        1. Initial query-based search (Hop 1)
        2. Finding similar chunks for each result (Hop 2+)
        3. Re-ranking all discovered chunks by query relevance

        Args:
            query: Search query
            k: Number of final results to return
            search_mode: Search mode - "hybrid", "semantic", or "bm25"
            hops: Number of search hops (default: 2)
            expansion_factor: Fraction of k to expand per hop (default: 0.3)
            use_parallel: Whether to use parallel search
            min_bm25_score: Minimum BM25 score threshold
            filters: Optional filters for search

        Returns:
            List of SearchResult objects with discovered related code
        """
        # Reset session-level OOM tracking at start of new search
        if hasattr(self, "reranking_engine") and self.reranking_engine:
            self.reranking_engine.reset_session_state()

        # Validate parameters
        hops, expansion_factor = self.validate_params(hops, expansion_factor)

        # Initialize timing tracker
        timings = {
            "total": time.time(),
            "hop_1": 0,
            "expansion": {},
            "rerank": 0,
        }

        self._logger.info(
            f"[MULTI_HOP] Starting {hops}-hop search for '{query}' "
            f"(k={k}, expansion={expansion_factor}, mode={search_mode})"
        )

        # Pre-compute query embedding once for reuse (optimization)
        query_embedding = None
        if search_mode in ("semantic", "hybrid") and self.embedder:
            try:
                query_embedding = self.embedder.embed_query(query)
                self._logger.debug(
                    "[MULTI_HOP] Pre-computed query embedding for caching"
                )
            except Exception as e:
                self._logger.warning(
                    f"[MULTI_HOP] Failed to pre-compute embedding: {e}"
                )

        # Hop 1: Initial query-based search
        # Use ServiceLocator helper instead of inline import
        config = _get_config_via_service_locator()
        initial_k = int(k * config.multi_hop.initial_k_multiplier)

        hop1_start = time.time()
        initial_results = self._single_hop_search(
            query=query,
            k=initial_k,
            search_mode=search_mode,
            use_parallel=use_parallel,
            min_bm25_score=min_bm25_score,
            filters=filters,
            query_embedding=query_embedding,
        )
        timings["hop_1"] = time.time() - hop1_start

        if not initial_results:
            self._logger.info("[MULTI_HOP] No initial results found")
            return []

        self._logger.info(
            f"[MULTI_HOP] Hop 1: Found {len(initial_results)} initial results "
            f"({timings['hop_1'] * 1000:.1f}ms)"
        )

        # Track all discovered chunks
        all_chunk_ids = {r.chunk_id for r in initial_results}
        all_results = {r.chunk_id: r for r in initial_results}

        # If only 1 hop requested, return initial results
        if hops == 1:
            return initial_results[:k]

        # Hop 2+: Expand from initial results
        expansion_k = max(1, int(k * expansion_factor))
        multi_hop_mode = config.multi_hop.multi_hop_mode

        if multi_hop_mode == "graph" and self.graph_storage:
            timings["expansion"] = self._graph_expand(
                initial_results=initial_results,
                all_chunk_ids=all_chunk_ids,
                all_results=all_results,
                expansion_k=expansion_k,
                k=k,
            )
        elif multi_hop_mode == "hybrid" and self.graph_storage:
            timings["expansion"] = self._hybrid_expand(
                initial_results=initial_results,
                all_chunk_ids=all_chunk_ids,
                all_results=all_results,
                expansion_k=expansion_k,
                hops=hops,
                k=k,
            )
        else:
            # "semantic" (default) or fallback when graph_storage is None
            timings["expansion"] = self.expand_from_initial_results(
                initial_results=initial_results,
                all_chunk_ids=all_chunk_ids,
                all_results=all_results,
                expansion_k=expansion_k,
                hops=hops,
                k=k,
            )

        # Apply filters to expanded results
        all_results = self.apply_post_expansion_filters(
            all_results=all_results,
            initial_results_count=len(initial_results),
            filters=filters,
        )

        # Re-rank all discovered results by query relevance
        self._logger.info(
            f"[MULTI_HOP] Re-ranking {len(all_results)} total chunks by query relevance"
        )

        rerank_start = time.time()
        final_results = self.reranking_engine.rerank_by_query(
            query=query,
            results=list(all_results.values()),
            k=k,
            search_mode=search_mode,
            query_embedding=query_embedding,
        )

        timings["rerank"] = time.time() - rerank_start

        # Final summary
        timings["total"] = time.time() - timings["total"]
        expansion_time = (
            sum(timings["expansion"].values()) if timings["expansion"] else 0
        )

        self._logger.info(
            f"[MULTI_HOP] Complete: {len(final_results)} results | "
            f"Total={timings['total'] * 1000:.0f}ms "
            f"(Hop1={timings['hop_1'] * 1000:.0f}ms, "
            f"Expansion={expansion_time * 1000:.0f}ms, "
            f"Rerank={timings['rerank'] * 1000:.0f}ms)"
        )

        return final_results
