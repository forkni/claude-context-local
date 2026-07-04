"""Ego-graph retrieval for context expansion via graph neighbors.

This module implements RepoGraph-style k-hop ego-graph retrieval to expand
search results using code graph relationships instead of just semantic similarity.

Key Insight: Functions are often best understood with their callers, callees,
and related code (ICLR 2025 RepoGraph paper shows 32.8% improvement).
"""

import logging
from typing import TYPE_CHECKING, Any

import numpy as np

from search.config import EgoGraphConfig
from search.graph_integration import is_chunk_id
from search.graph_view import GraphView, PPRConvergenceError
from search.reranker import SearchResult
from search.result_factory import ResultFactory


if TYPE_CHECKING:
    from graph.graph_storage import CodeGraphStorage


logger = logging.getLogger(__name__)


class EgoGraphRetriever:
    """Retrieve k-hop ego-graphs for anchor chunks.

    An ego-graph is a subgraph centered on a node, containing the node itself
    and all nodes within k hops. This provides richer context than just the
    matched chunk by including:
    - Callers (who uses this code?)
    - Callees (what does this code use?)
    - Related types/classes (inheritance, type annotations)
    - Import dependencies
    """

    def __init__(self, graph_storage: "CodeGraphStorage") -> None:
        """Initialize ego-graph retriever.

        Args:
            graph_storage: CodeGraphStorage instance with get_neighbors() method
        """
        self.graph = graph_storage
        self._gv = GraphView(graph_storage)
        self._centrality_scores: dict[str, float] = {}
        self._community_map: dict[str, int] = graph_storage.load_community_map() or {}
        logger.info("EgoGraphRetriever initialized")

    def set_centrality_scores(self, scores: dict[str, float]) -> None:
        """Inject PageRank centrality scores for centrality-aware neighbor ranking.

        Called after centrality is computed in the search handler so that
        the ego-graph retriever can rank BFS neighbors by architectural
        importance before truncation.

        Args:
            scores: Mapping of chunk_id -> PageRank centrality score (0-1 range).
        """
        self._centrality_scores = scores

    def retrieve_ego_graph(
        self,
        anchor_chunk_ids: list[str],
        config: EgoGraphConfig,
    ) -> dict[str, list[str]]:
        """Retrieve k-hop ego-graph for each anchor.

        Args:
            anchor_chunk_ids: Starting nodes (from initial search results)
            config: Ego-graph configuration

        Returns:
            Dict mapping anchor_id -> list of neighbor chunk_ids
        """
        if not anchor_chunk_ids:
            return {}

        # QW3: route to PPR expansion when requested
        if getattr(config, "expansion_mode", "bfs") == "ppr":
            return self._expand_via_ppr(anchor_chunk_ids, config)

        results = {}
        for anchor in anchor_chunk_ids:
            try:
                # Build exclude_import_categories list from config
                exclude_categories = []
                if config.exclude_stdlib_imports:
                    exclude_categories.extend(["stdlib", "builtin"])
                if config.exclude_third_party_imports:
                    exclude_categories.append("third_party")

                # Get neighbors using existing graph traversal
                neighbors = self.graph.get_neighbors(
                    anchor,
                    relation_types=config.relation_types,
                    max_depth=config.k_hops,
                    exclude_import_categories=(
                        exclude_categories if exclude_categories else None
                    ),
                    edge_weights=config.edge_weights,
                )

                # Filter to keep only valid chunk_ids (format: "file:lines:type:name")
                # Exclude symbol-only nodes like "get_searcher", "str", etc.
                # Valid chunk_ids have at least 3 colons
                valid_neighbors = [n for n in neighbors if is_chunk_id(n)]

                if len(neighbors) != len(valid_neighbors):
                    logger.debug(
                        f"Filtered {len(neighbors) - len(valid_neighbors)} symbol-only nodes "
                        f"from {len(neighbors)} neighbors for {anchor}"
                    )

                # Limit neighbors per hop to prevent explosion
                # RepoGraph paper recommends k=2 with moderate limits
                max_total = config.max_neighbors_per_hop * config.k_hops
                if len(valid_neighbors) > max_total:
                    logger.debug(
                        f"Limiting {len(valid_neighbors)} neighbors to {max_total} for {anchor}"
                    )
                    # QW1: rank by centrality before truncation so hub functions
                    # survive the cap rather than being dropped by BFS order
                    if self._centrality_scores:
                        anchor_community = self._community_map.get(anchor)
                        valid_neighbors.sort(
                            key=lambda n: self._rank_neighbor(
                                n, anchor_community, config
                            ),
                            reverse=True,
                        )
                    valid_neighbors = valid_neighbors[:max_total]

                results[anchor] = valid_neighbors

            except Exception as e:  # noqa: BLE001 - resilience: per-anchor ego-graph failure, empty result for anchor
                logger.warning(f"Failed to retrieve ego-graph for {anchor}: {e}")
                results[anchor] = []

        return results

    def _rank_neighbor(
        self,
        neighbor_id: str,
        anchor_community: int | None,
        config: "EgoGraphConfig",
    ) -> float:
        """Compute ranking score for a neighbor during pre-truncation sorting.

        Combines PageRank centrality (QW1) with optional community-boundary
        penalty (QW2). Higher score = higher priority to survive truncation.

        Args:
            neighbor_id: Chunk ID of the neighbor being ranked.
            anchor_community: Community ID of the anchor chunk (None if unknown).
            config: EgoGraphConfig with community_bounded and cross_community_penalty.

        Returns:
            Ranking score in [0, 1] range.
        """
        score = self._centrality_scores.get(neighbor_id, 0.0)

        # QW2: apply community penalty for cross-community neighbors
        if (
            getattr(config, "community_bounded", False)
            and anchor_community is not None
            and self._community_map
        ):
            neighbor_community = self._community_map.get(neighbor_id)
            if neighbor_community != anchor_community:
                penalty = getattr(config, "cross_community_penalty", 0.6)
                score *= penalty

        return score

    def _expand_via_ppr(
        self,
        anchor_chunk_ids: list[str],
        config: EgoGraphConfig,
    ) -> dict[str, list[str]]:
        """Expand anchors using Personalized PageRank instead of k-hop BFS.

        PPR concentrates probability mass in densely connected neighbourhoods
        of the anchor nodes, naturally surfacing structurally important code
        without requiring a fixed hop limit.  Research (Section 4.2 of the
        Code GraphRAG analysis) shows PPR outperforms rigid k-hop bounds for
        multi-hop reasoning queries.

        Args:
            anchor_chunk_ids: Seed nodes (matched by semantic search).
            config: EgoGraphConfig with ppr_alpha and max_neighbors_per_hop.

        Returns:
            Dict mapping each anchor -> list of top-k PPR neighbours.
            Falls back to BFS if PPR fails to converge or graph is empty.
        """
        if self._gv.is_empty():
            return {a: [] for a in anchor_chunk_ids}

        valid_anchors = [a for a in anchor_chunk_ids if self._gv.contains(a)]
        if not valid_anchors:
            return {a: [] for a in anchor_chunk_ids}

        # Build uniform personalisation vector over anchor nodes
        weight = 1.0 / len(valid_anchors)
        personalization = dict.fromkeys(valid_anchors, weight)

        try:
            ppr_scores: dict[str, float] = self._gv.personalized_pagerank(
                personalization,
                alpha=config.ppr_alpha,
            )
        except PPRConvergenceError:
            logger.warning(
                "[PPR] Power iteration failed to converge — falling back to BFS"
            )
            return self.retrieve_ego_graph(anchor_chunk_ids, config)

        max_total = config.max_neighbors_per_hop * config.k_hops
        anchor_set = set(valid_anchors)

        # Rank all non-anchor chunk nodes by PPR score
        candidates = sorted(
            (
                (node, score)
                for node, score in ppr_scores.items()
                if node not in anchor_set and is_chunk_id(node)
            ),
            key=lambda x: x[1],
            reverse=True,
        )
        top_neighbors = [node for node, _ in candidates[:max_total]]

        logger.debug(
            f"[PPR] {len(valid_anchors)} anchors -> {len(top_neighbors)} neighbours "
            f"(from {len(candidates)} candidates)"
        )

        # Assign each neighbour to the nearest anchor (direct edge preference)
        results: dict[str, list[str]] = {a: [] for a in anchor_chunk_ids}
        default_anchor = valid_anchors[0]
        for neighbor in top_neighbors:
            assigned = default_anchor
            for anchor in valid_anchors:
                if self._gv.has_edge(anchor, neighbor) or self._gv.has_edge(
                    neighbor, anchor
                ):
                    assigned = anchor
                    break
            results[assigned].append(neighbor)

        return results

    def flatten_for_context(
        self,
        ego_graphs: dict[str, list[str]],
        config: EgoGraphConfig,
    ) -> list[str]:
        """Flatten ego-graphs to deduplicated chunk list for retrieval.

        Args:
            ego_graphs: Dict mapping anchor -> neighbors
            config: Ego-graph configuration

        Returns:
            List of unique chunk_ids combining all ego-graphs
        """
        all_chunks: set[str] = set()

        for anchor, neighbors in ego_graphs.items():
            if config.include_anchor:
                all_chunks.add(anchor)
            all_chunks.update(neighbors)

        result = list(all_chunks)
        logger.debug(
            f"Flattened {len(ego_graphs)} ego-graphs into {len(result)} unique chunks"
        )
        return result

    def expand_search_results(
        self,
        search_results: list[dict],
        config: EgoGraphConfig,
    ) -> tuple[list[str], dict[str, list[str]]]:
        """Expand search results using ego-graph retrieval.

        This is the main entry point for integrating ego-graph expansion
        into existing search pipelines.

        Args:
            search_results: List of search result dicts with 'chunk_id' field
            config: Ego-graph configuration

        Returns:
            Tuple of:
            - List of chunk_ids to retrieve (anchors + neighbors)
            - Dict mapping anchor -> neighbors for provenance
        """
        if not config.enabled or not search_results:
            # Return original chunk_ids only
            return [r["chunk_id"] for r in search_results], {}

        # Extract anchor chunk_ids from search results
        anchor_chunk_ids = [r["chunk_id"] for r in search_results]

        # Retrieve ego-graphs for each anchor
        ego_graphs = self.retrieve_ego_graph(anchor_chunk_ids, config)

        # Flatten to unique chunk list
        expanded_chunk_ids = self.flatten_for_context(ego_graphs, config)

        logger.info(
            f"Ego-graph expansion: {len(anchor_chunk_ids)} anchors "
            f"-> {len(expanded_chunk_ids)} total chunks "
            f"({len(expanded_chunk_ids) - len(anchor_chunk_ids)} neighbors added)"
        )

        return expanded_chunk_ids, ego_graphs

    def score_neighbors(
        self,
        results: list[SearchResult],
        ego_graphs: dict[str, list[str]],
        expanded_chunk_ids: list[str],
        query: str,
        ego_config: EgoGraphConfig,
        *,
        dense_index: Any,
        embedder: Any,
    ) -> list[SearchResult]:
        """Score ego-graph neighbors into SearchResults using embedding similarity.

        Implements two-pass scoring:
        1. Metadata fetch for all valid neighbors (no embedding work).
        2. Batched FAISS reconstruction + vectorised cosine similarity, with
           anchor-score-scaled decay fallback when embedding fails or the FAISS
           index entry is absent.

        Args:
            results: Anchor SearchResults; their scores serve as the relative
                baseline for neighbor scoring.
            ego_graphs: Dict mapping anchor_id -> list[neighbor_ids], from
                expand_search_results.
            expanded_chunk_ids: Flat list of anchor + neighbor ids; used to
                compute the neighbor-only set.
            query: Original search query for computing the query embedding.
            ego_config: EgoGraphConfig (min_similarity_threshold, etc.).
            dense_index: CodeIndexManager — must expose .chunk_ids,
                .get_chunk_by_id(), and ._faiss_index.reconstruct().
            embedder: Embedding model — must expose .embed_query().

        Returns:
            Uncapped list of scored SearchResult neighbors (no anchors).
        """
        # Track which chunks are neighbors (not original anchors)
        original_chunk_ids = {r.chunk_id for r in results}
        neighbor_chunk_ids = set(expanded_chunk_ids) - original_chunk_ids

        # Build neighbor→anchor mapping for decay scoring
        # ego_graphs: dict[anchor_id, list[neighbor_ids]]
        neighbor_to_anchor: dict[str, str] = {}
        for anchor_id, neighbors in ego_graphs.items():
            for neighbor_id in neighbors:
                if neighbor_id not in original_chunk_ids:
                    neighbor_to_anchor[neighbor_id] = anchor_id

        # Compute query embedding once for all neighbor scoring
        try:
            # pyrefly: ignore [missing-attribute]
            query_embedding = embedder.embed_query(query)
            query_embedding_available = True
        except Exception as e:  # noqa: BLE001 - resilience: embedding unavailable, fall back to fixed decay scoring
            logger.warning(
                f"Failed to compute query embedding for ego-graph scoring: {e}. "
                f"Falling back to fixed decay.",
                exc_info=True,
            )
            query_embedding = None
            query_embedding_available = False

        # Pre-compute anchor scores for relative scoring
        anchor_scores = {r.chunk_id: r.score for r in results}

        # Build chunk_id→FAISS-index map once (#52): avoids O(N) list rebuild
        # + O(N) .index() call *per neighbor* (was O(M×N) total).
        chunk_id_to_faiss_idx: dict[str, int] = {
            cid: i for i, cid in enumerate(dense_index.chunk_ids)
        }

        # Pass 1 — fetch metadata and FAISS indices for all valid neighbors.
        # No embedding work yet; keeps the hot metadata-fetch loop clean.
        valid_neighbors: list[tuple[str, dict, int | None]] = []
        for chunk_id in neighbor_chunk_ids:
            try:
                metadata = dense_index.get_chunk_by_id(chunk_id)
                if not metadata:
                    continue
                faiss_idx = chunk_id_to_faiss_idx.get(chunk_id)
                valid_neighbors.append((chunk_id, metadata, faiss_idx))
            except (KeyError, TypeError) as e:
                logger.debug(f"Failed to retrieve metadata for {chunk_id}: {e}")
                continue

        # Pass 2 — score neighbors, batching FAISS reconstruction and
        # computing similarities in a single matmul (#52/#59).
        neighbor_results: list[SearchResult] = []
        threshold = getattr(ego_config, "min_similarity_threshold", 0.15)

        if query_embedding_available and valid_neighbors:
            assert query_embedding is not None
            # Partition: neighbors with a known FAISS index vs. those without.
            reconstruct_items: list[tuple[str, dict, int]] = []
            decay_items: list[tuple[str, dict]] = []
            for chunk_id, metadata, faiss_idx in valid_neighbors:
                if faiss_idx is not None:
                    reconstruct_items.append((chunk_id, metadata, faiss_idx))
                else:
                    decay_items.append((chunk_id, metadata))

            if reconstruct_items:
                try:
                    # Batch-reconstruct all neighbor embeddings in one call (#52+#59).
                    faiss_indices = np.array(
                        [idx for _, _, idx in reconstruct_items], dtype=np.int64
                    )
                    neighbor_embeddings = np.stack(
                        [
                            dense_index._faiss_index.reconstruct(int(idx))
                            for idx in faiss_indices
                        ]
                    )
                    # Vectorised cosine-similarity (embeddings are L2-normalised).
                    similarities = neighbor_embeddings @ query_embedding  # (M,)
                    for (chunk_id, metadata, _), similarity in zip(
                        reconstruct_items, similarities, strict=False
                    ):
                        similarity = float(similarity)
                        if similarity < threshold:
                            logger.debug(
                                f"Filtering ego-graph neighbor {chunk_id}: "
                                f"similarity={similarity:.3f} < {threshold:.2f}"
                            )
                            continue
                        anchor_id = neighbor_to_anchor.get(chunk_id)
                        anchor_score = (
                            anchor_scores.get(anchor_id, 0.0) if anchor_id else 0.0
                        )
                        neighbor_results.append(
                            ResultFactory.from_expansion(
                                chunk_id,
                                anchor_score * similarity,
                                metadata,
                                "ego_graph",
                            )
                        )
                except (RuntimeError, AttributeError, IndexError) as e:
                    logger.debug(
                        f"Batch reconstruction failed ({e}); falling back to decay for "
                        f"{len(reconstruct_items)} neighbors."
                    )
                    decay_items.extend(
                        (cid, meta) for cid, meta, _ in reconstruct_items
                    )

            # Fixed-decay fallback for neighbors with no FAISS index or batch failure
            for chunk_id, metadata in decay_items:
                anchor_id = neighbor_to_anchor.get(chunk_id)
                anchor_score = anchor_scores.get(anchor_id, 0.0) if anchor_id else 0.0
                neighbor_results.append(
                    ResultFactory.from_expansion(
                        chunk_id, anchor_score * 0.5, metadata, "ego_graph"
                    )
                )
        else:
            # No query embedding — fixed decay for all neighbors
            for chunk_id, metadata, _ in valid_neighbors:
                anchor_id = neighbor_to_anchor.get(chunk_id)
                anchor_score = anchor_scores.get(anchor_id, 0.0) if anchor_id else 0.0
                neighbor_results.append(
                    ResultFactory.from_expansion(
                        chunk_id, anchor_score * 0.5, metadata, "ego_graph"
                    )
                )

        return neighbor_results
