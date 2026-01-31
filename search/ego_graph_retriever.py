"""Ego-graph retrieval for context expansion via graph neighbors.

This module implements RepoGraph-style k-hop ego-graph retrieval to expand
search results using code graph relationships instead of just semantic similarity.

Key Insight: Functions are often best understood with their callers, callees,
and related code (ICLR 2025 RepoGraph paper shows 32.8% improvement).
"""

import logging

from search.config import EgoGraphConfig


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

    def __init__(self, graph_storage) -> None:
        """Initialize ego-graph retriever.

        Args:
            graph_storage: CodeGraphStorage instance with get_neighbors() method
        """
        self.graph = graph_storage
        logger.info("EgoGraphRetriever initialized")

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
                valid_neighbors = [n for n in neighbors if n.count(":") >= 3]

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
                    valid_neighbors = valid_neighbors[:max_total]

                results[anchor] = valid_neighbors

            except Exception as e:
                logger.warning(f"Failed to retrieve ego-graph for {anchor}: {e}")
                results[anchor] = []

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
