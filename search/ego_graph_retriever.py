"""Ego-graph retrieval for context expansion via graph neighbors.

This module implements RepoGraph-style k-hop ego-graph retrieval to expand
search results using code graph relationships instead of just semantic similarity.

Key Insight: Functions are often best understood with their callers, callees,
and related code (ICLR 2025 RepoGraph paper shows 32.8% improvement).
"""

import logging
from typing import TYPE_CHECKING

from search.config import EgoGraphConfig
from search.graph_integration import is_chunk_id


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

            except Exception as e:
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
        try:
            import networkx as nx
        except ImportError:
            logger.warning("networkx not available — falling back to BFS")
            return self.retrieve_ego_graph(anchor_chunk_ids, config)

        nx_graph = self.graph.get_graph()
        if nx_graph is None or len(nx_graph) == 0:
            return {a: [] for a in anchor_chunk_ids}

        valid_anchors = [a for a in anchor_chunk_ids if a in nx_graph]
        if not valid_anchors:
            return {a: [] for a in anchor_chunk_ids}

        # Build uniform personalisation vector over anchor nodes
        weight = 1.0 / len(valid_anchors)
        personalization = dict.fromkeys(valid_anchors, weight)

        try:
            ppr_scores: dict[str, float] = nx.pagerank(
                nx_graph,
                alpha=config.ppr_alpha,
                personalization=personalization,
                max_iter=100,
                tol=1e-6,
            )
        except nx.PowerIterationFailedConvergence:
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
                if nx_graph.has_edge(anchor, neighbor) or nx_graph.has_edge(
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
