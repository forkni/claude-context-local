"""Multi-hop search expansion logic for discovering interconnected code relationships.

Handles iterative expansion of search results through semantic similarity
to discover related code across multiple hops.
"""

import logging
import time
from dataclasses import replace
from typing import Any

import numpy as np

from graph.graph_storage import DEFAULT_EDGE_WEIGHTS
from search.config import SearchMode
from search.graph_integration import is_chunk_id
from utils.timing import timed

from .reranker import SearchResult as RerankerSearchResult
from .types import RetrievalRequest


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
        logger: logging.Logger | None = None,
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
        elif hops > 20:
            self._logger.warning(f"hops={hops} exceeds maximum, capping at 20")
            validated_hops = 20

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

            except Exception as e:  # noqa: BLE001 - resilience: per-hop expansion optional, continue without it
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
        edge_weights: dict[str, float] | None = None,
        query_embedding: np.ndarray | None = None,
        config=None,
    ) -> dict[int | str, float]:
        """Expand results via graph neighbor traversal (weighted BFS).

        Modifies all_chunk_ids and all_results IN-PLACE.

        When config.graph_enhanced.graph_hop_call_evidence_enabled is set,
        discovered candidates get a real score on the anchor's scale
        (see _score_graph_candidates) instead of the legacy flat 0.0 that
        sorted them below every other score scale at the merged pool's
        rerank-window cut. Default-off: byte-identical to legacy behavior.

        Returns:
            Dict mapping hop number/name to duration in seconds.
        """
        expansion_timings = {}

        # Truthiness, not `is not None`: a valid-but-empty graph_storage (0 nodes)
        # also short-circuits here and gets the same "is None" log message, since
        # CodeGraphStorage is falsy when empty (see its __len__ docstring). Left
        # as-is intentionally — empty and absent both mean "nothing to expand"
        # for this caller — but the message is imprecise about which it was.
        if not self.graph_storage:
            self._logger.warning(
                "[MULTI_HOP] Graph expansion requested but graph_storage is None"
            )
            return expansion_timings

        hop_start = time.time()
        hop_discovered = 0

        source_results = initial_results[:k]

        # Snapshot the hop-1 reference set before expansion mutates it —
        # call-evidence scoring is conditioned on what the query surfaced,
        # not on other expansion candidates.
        reference_ids = frozenset(all_chunk_ids)
        # (neighbor_id, metadata, anchor_score) awaiting score assignment
        pending: list[tuple[str, dict, float]] = []

        ge_cfg = getattr(config, "graph_enhanced", None) if config is not None else None
        min_confidence = 0.0
        confidence_weighting = False
        if ge_cfg is not None:
            min_confidence = ge_cfg.min_traversal_confidence
            confidence_weighting = ge_cfg.traversal_confidence_weighting_enabled

        for result in source_results:
            # Weighted BFS -- prioritizes calls (1.0) over imports (0.3)
            neighbors: set[str] = self.graph_storage.get_neighbors(
                chunk_id=result.chunk_id,
                max_depth=1,
                edge_weights=edge_weights or DEFAULT_EDGE_WEIGHTS,
                min_confidence=min_confidence,
                confidence_weighting=confidence_weighting,
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
                pending.append((neighbor_id, metadata, result.score))
                hop_discovered += 1
                added_for_source += 1

        if pending and ge_cfg is not None and ge_cfg.graph_hop_call_evidence_enabled:
            try:
                scores = self._score_graph_candidates(
                    pending,
                    query_embedding=query_embedding,
                    lambda_weight=ge_cfg.graph_hop_call_evidence_lambda,
                    reference_ids=reference_ids,
                )
            except Exception as e:  # noqa: BLE001 - resilience: scoring is an enhancement; fall back to legacy 0.0
                self._logger.warning(
                    f"[MULTI_HOP] Call-evidence scoring failed: {e}; using 0.0"
                )
                scores = [0.0] * len(pending)
        else:
            scores = [0.0] * len(pending)  # Legacy: reranker assigns final score

        for (neighbor_id, metadata, _anchor), score in zip(
            pending, scores, strict=True
        ):
            all_results[neighbor_id] = RerankerSearchResult(
                chunk_id=neighbor_id,
                score=score,
                metadata=metadata,
                source="graph_hop",
            )

        expansion_timings["graph"] = time.time() - hop_start

        self._logger.info(
            f"[MULTI_HOP] Graph expand: {hop_discovered} new chunks "
            f"(total: {len(all_results)}, {expansion_timings['graph'] * 1000:.1f}ms)"
        )

        return expansion_timings

    def _score_graph_candidates(
        self,
        pending: list[tuple[str, dict, float]],
        query_embedding: np.ndarray | None,
        lambda_weight: float,
        reference_ids: frozenset[str],
    ) -> list[float]:
        """Score graph-hop candidates on their anchor's score scale (A1).

        score = min(anchor_score * cosine(query, candidate) + call_evidence,
        anchor_score) — anchored to the hop-1 scale so the merged pool's
        raw-score sort in RerankingEngine.rerank_by_query compares like with
        like, and capped so a candidate never outranks its own anchor. This
        anchoring only matters under merged_pool_policy="score" (or
        "score_reserve_fix", same sort) — "channel_priority" ignores raw
        score for graph_hop placement entirely (stable insertion order
        within its own tier), so this scoring's benefit is inert there.
        call_evidence = lambda_weight * log2(1 + distinct reference_ids the
        candidate shares a calls-edge with); see
        GraphQueryEngine.score_call_evidence for the query-conditioning
        rationale.

        Args:
            pending: (chunk_id, metadata, anchor_score) per candidate
            query_embedding: Pre-computed query embedding (None in BM25 mode)
            lambda_weight: Call-evidence multiplier per log2 unit
            reference_ids: Hop-1 chunk IDs the evidence is conditioned on

        Returns:
            One score per pending entry, in order.
        """
        from graph.graph_queries import GraphQueryEngine

        engine = GraphQueryEngine(self.graph_storage)
        similarities = self._graph_candidate_similarities(
            [chunk_id for chunk_id, _, _ in pending], query_embedding
        )

        scores = []
        for (chunk_id, _metadata, anchor_score), similarity in zip(
            pending, similarities, strict=True
        ):
            evidence = engine.score_call_evidence(
                chunk_id, reference_ids, lambda_weight
            )
            scores.append(min(anchor_score * similarity + evidence, anchor_score))
        return scores

    def _graph_candidate_similarities(
        self, chunk_ids: list[str], query_embedding: np.ndarray | None
    ) -> list[float]:
        """Query-candidate cosines via batched FAISS reconstruction.

        Mirrors EgoGraphRetriever.score_neighbors: reconstruct stored
        (L2-normalized) embeddings by FAISS position, one matmul against the
        query — zero new embedding compute. Falls back to a neutral 0.5
        decay per candidate when the embedding is unavailable (BM25 mode,
        id not in the dense index) or reconstruction fails, same as the ego
        path's decay fallback.
        """
        similarities = [0.5] * len(chunk_ids)
        if query_embedding is None or not chunk_ids:
            return similarities

        try:
            id_to_faiss_idx = {
                cid: i for i, cid in enumerate(self.dense_index.chunk_ids)
            }
            mapped = [
                (pos, id_to_faiss_idx[cid])
                for pos, cid in enumerate(chunk_ids)
                if cid in id_to_faiss_idx
            ]
            if not mapped:
                return similarities
            embeddings = np.stack(
                [
                    self.dense_index._faiss_index.reconstruct(int(faiss_idx))
                    for _, faiss_idx in mapped
                ]
            )
            batch = embeddings @ query_embedding
            for (pos, _), sim in zip(mapped, batch, strict=True):
                similarities[pos] = float(sim)
        except (RuntimeError, AttributeError, IndexError, TypeError) as e:
            self._logger.debug(
                f"[MULTI_HOP] Graph-hop similarity reconstruction failed ({e}); "
                "using 0.5 decay fallback"
            )
        return similarities

    def _hybrid_expand(
        self,
        initial_results: list,
        all_chunk_ids: set,
        all_results: dict,
        expansion_k: int,
        hops: int,
        k: int,
        edge_weights: dict[str, float] | None = None,
        query_embedding: np.ndarray | None = None,
        config=None,
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
            edge_weights=edge_weights,
            query_embedding=query_embedding,
            config=config,
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
        filters: dict[str, Any] | None,
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
            metadata = getattr(result, "metadata", None)
            if not metadata:
                # Fallback to index lookup if result lacks metadata
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
        request: RetrievalRequest,
        hops: int = 2,
        expansion_factor: float = 0.3,
        edge_weights: dict[str, float] | None = None,
    ) -> list:
        """
        Internal multi-hop search implementation.

        Discovers interconnected code relationships by:
        1. Initial query-based search (Hop 1)
        2. Finding similar chunks for each result (Hop 2+)
        3. Re-ranking all discovered chunks by query relevance

        Args:
            request: The RetrievalRequest this search executes against. Hop 1
                runs against a derived copy with a widened k
                (config.multi_hop.initial_k_multiplier); later hops and the
                final rerank use request's own k. Multi-hop policy (hops,
                expansion_factor, edge_weights) is not part of the request —
                it is not what a single leg executes against.
            hops: Number of search hops (default: 2)
            expansion_factor: Fraction of k to expand per hop (default: 0.3)
            edge_weights: Optional per-intent edge weights for graph expansion

        Returns:
            List of SearchResult objects with discovered related code
        """
        query = request.query
        k = request.k
        search_mode = request.search_mode
        filters = request.filters
        config = request.config

        # Reset session-level OOM tracking at start of new search
        if hasattr(self, "reranking_engine") and self.reranking_engine:
            self.reranking_engine.reset_session_state()

        # Validate parameters
        hops, expansion_factor = self.validate_params(hops, expansion_factor)

        # Initialize timing tracker
        timings = {
            "total": time.time(),
            "hop_1": 0.0,
            "expansion": {},
            "rerank": 0.0,
        }

        self._logger.info(
            f"[MULTI_HOP] Starting {hops}-hop search for '{query}' "
            f"(k={k}, expansion={expansion_factor}, mode={search_mode})"
        )

        # Pre-compute query embedding once for reuse (optimization)
        query_embedding = None
        if search_mode in (SearchMode.SEMANTIC, SearchMode.HYBRID) and self.embedder:
            try:
                query_embedding = self.embedder.embed_query(query)
                self._logger.debug(
                    "[MULTI_HOP] Pre-computed query embedding for caching"
                )
            except Exception as e:  # noqa: BLE001 - resilience: query embedding pre-cache optional, recomputed later if needed
                self._logger.warning(
                    f"[MULTI_HOP] Failed to pre-compute embedding: {e}"
                )

        # Hop 1: Initial query-based search, against a k-widened copy of the request
        initial_k = int(k * config.multi_hop.initial_k_multiplier)
        hop1_request = replace(request, k=initial_k)

        hop1_start = time.time()
        initial_results = self._single_hop_search(
            hop1_request, query_embedding=query_embedding
        )
        timings["hop_1"] = time.time() - hop1_start

        if not initial_results:
            self._logger.info("[MULTI_HOP] No initial results found")
            return []

        self._logger.info(
            f"[MULTI_HOP] Hop 1: Found {len(initial_results)} initial results "
            f"({timings['hop_1'] * 1000:.1f}ms)"
        )

        # Tag hop-1 provenance so a downstream rerank-window reserve
        # (RerankingEngine.rerank_by_query, hop1_reserved_slots) can promote
        # these candidates back in if the merged pool's score-scale sort
        # pushes them out of the top_k_candidates cut.
        for i, r in enumerate(initial_results):
            r.metadata["hop1_rank"] = i + 1

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
                edge_weights=edge_weights,
                query_embedding=query_embedding,
                config=config,
            )
        elif multi_hop_mode == "hybrid" and self.graph_storage:
            timings["expansion"] = self._hybrid_expand(
                initial_results=initial_results,
                all_chunk_ids=all_chunk_ids,
                all_results=all_results,
                expansion_k=expansion_k,
                hops=hops,
                k=k,
                edge_weights=edge_weights,
                query_embedding=query_embedding,
                config=config,
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
        merged_results = list(all_results.values())
        if config.reranker.single_pass:
            # Q3 single-pass: defer neural reranking to the one listwise pass
            # at the tail of HybridSearcher.search(); keep fusion/expansion
            # score order so ego expansion still seeds from this top-k.
            merged_results.sort(key=lambda r: r.score, reverse=True)
            final_results = merged_results[:k]
        else:
            final_results = self.reranking_engine.rerank_by_query(
                query=query,
                results=merged_results,
                k=k,
                search_mode=search_mode,
                hop1_reserved_slots=config.reranker.hop1_reserved_slots,
                merged_pool_policy=config.reranker.merged_pool_policy,
                graph_hop_window_cap=config.reranker.graph_hop_window_cap,
                config=config,
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
