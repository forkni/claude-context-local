"""
Louvain-based community detection for code graphs.

Provides algorithmic (non-LLM) community detection using NetworkX native Louvain algorithm
for modularity maximization on code relationship graphs.

NetworkX Reference: https://networkx.org/documentation/stable/reference/algorithms/community.html
"""

import logging
from collections import Counter
from typing import Dict

from networkx.algorithms.community import louvain_communities, modularity

from graph.graph_storage import CodeGraphStorage

logger = logging.getLogger(__name__)


class CommunityDetector:
    """Louvain-based community detection for code graph.

    Uses NetworkX native Louvain algorithm for community detection on code relationship graphs.
    Purely algorithmic approach (modularity maximization) - no LLM required.

    Features:
    - Graph-theoretic community detection using native NetworkX (no external dependencies)
    - Modularity-based quality scoring
    - Resolution parameter for fine-tuning granularity

    Reference: https://networkx.org/documentation/stable/reference/algorithms/community.html
    """

    def __init__(self, graph_storage: CodeGraphStorage):
        """Initialize community detector.

        Args:
            graph_storage: CodeGraphStorage instance with NetworkX graph
        """
        self.nx_graph = graph_storage.graph  # NetworkX DiGraph
        self.storage = graph_storage
        self.logger = logging.getLogger(__name__)

    def detect_communities(self, resolution: float = 1.0) -> Dict[str, int]:
        """Detect communities using NetworkX native Louvain algorithm.

        Algorithm: Modularity maximization (purely algorithmic, no LLM)
        Reference: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html

        Filters out phantom call target nodes (type="symbol_name" or is_target_name=True)
        before running community detection to prevent artificial fragmentation.

        Args:
            resolution: Resolution parameter (default: 1.0)
                       Higher values = more/smaller communities (fine-grained)
                       Lower values = fewer/larger communities (coarse)

        Returns:
            Dict mapping chunk_id -> community_id (only for actual chunk nodes)

        Example:
            >>> detector = CommunityDetector(graph_storage)
            >>> communities = detector.detect_communities(resolution=1.0)
            >>> # {'file.py:10-20:function:foo': 0, 'file.py:25-35:function:bar': 0}
        """
        if self.nx_graph.number_of_nodes() == 0:
            self.logger.warning("Empty graph - no communities to detect")
            return {}

        # Filter to chunk nodes only (exclude phantom call target nodes)
        # Phantom nodes have type="symbol_name" or is_target_name=True
        chunk_nodes = [
            n
            for n, attrs in self.nx_graph.nodes(data=True)
            if attrs.get("type") != "symbol_name"
            and not attrs.get("is_target_name", False)
        ]

        if not chunk_nodes:
            self.logger.warning("No chunk nodes found after filtering phantom nodes")
            return {}

        # Identify phantom nodes (call targets that aren't real chunks)
        phantom_nodes = [
            n
            for n, attrs in self.nx_graph.nodes(data=True)
            if attrs.get("type") == "symbol_name" or attrs.get("is_target_name", False)
        ]

        if phantom_nodes:
            self.logger.info(
                f"Collapsing {len(phantom_nodes)} phantom call target nodes "
                f"to create direct chunk-to-chunk edges"
            )

        # Build collapsed graph: Preserve chunk-to-chunk edges, collapse phantom nodes
        import networkx as nx

        collapsed_graph = nx.Graph()  # Undirected from the start
        chunk_nodes_set = set(chunk_nodes)

        # Add all chunk nodes
        for node in chunk_nodes:
            attrs = self.nx_graph.nodes[node]
            collapsed_graph.add_node(node, **attrs)

        # First: Preserve direct chunk-to-chunk edges (resolved internal calls, relationships)
        # Filter out self-loops per NetworkX warning: "self-loops are treated as previously reduced communities"
        direct_edges = 0
        for u, v in self.nx_graph.edges():
            if u in chunk_nodes_set and v in chunk_nodes_set and u != v:
                if collapsed_graph.has_edge(u, v):
                    collapsed_graph[u][v]["weight"] += 1
                else:
                    collapsed_graph.add_edge(u, v, weight=1)
                    direct_edges += 1

        # Second: Collapse phantom nodes - connect chunks sharing same call targets
        # This groups chunks that use similar APIs/libraries together
        collapsed_edges = 0
        for phantom in phantom_nodes:
            # Find all chunks that call/reference this phantom
            callers = [
                pred
                for pred in self.nx_graph.predecessors(phantom)
                if pred in chunk_nodes_set
            ]

            # Only create co-reference edges if multiple chunks share this target
            if len(callers) > 1:
                # Create edges between all pairs of callers (they share a common reference)
                for i, caller1 in enumerate(callers):
                    for caller2 in callers[i + 1 :]:
                        # Add undirected edge (or increment weight if exists)
                        if collapsed_graph.has_edge(caller1, caller2):
                            collapsed_graph[caller1][caller2]["weight"] += 1
                        else:
                            collapsed_graph.add_edge(caller1, caller2, weight=1)
                            collapsed_edges += 1

        self.logger.info(
            f"Collapsed graph: {collapsed_graph.number_of_nodes()} nodes, "
            f"{collapsed_graph.number_of_edges()} edges "
            f"({direct_edges} direct chunk-chunk, {collapsed_edges} from phantom collapse)"
        )

        # Use collapsed graph for community detection (already undirected)
        undirected = collapsed_graph

        # Run Louvain algorithm with modularity optimization
        # louvain_communities(G, resolution=1, seed=42) returns list of sets
        try:
            communities_list = louvain_communities(
                undirected, resolution=resolution, seed=42
            )
        except Exception as e:
            self.logger.error(f"Louvain algorithm failed: {e}")
            return {}

        # Convert list of sets to chunk_id -> community_id mapping
        community_map = {}
        for community_id, nodes in enumerate(communities_list):
            for node in nodes:
                community_map[node] = community_id

        # Calculate and log modularity score (quality metric)
        try:
            mod_score = modularity(undirected, communities_list, resolution=resolution)
            self.logger.info(
                f"Detected {len(communities_list)} communities from {len(community_map)} nodes "
                f"(resolution={resolution}, modularity={mod_score:.3f})"
            )
        except Exception as e:
            self.logger.warning(f"Failed to calculate modularity: {e}")
            self.logger.info(
                f"Detected {len(communities_list)} communities from {len(community_map)} nodes "
                f"(resolution={resolution})"
            )

        return community_map

    def get_community_stats(self, communities: Dict[str, int]) -> Dict:
        """Get statistics about detected communities.

        Args:
            communities: Dict mapping chunk_id -> community_id

        Returns:
            Dict with statistics:
                - num_communities: Total number of unique communities
                - avg_size: Average community size
                - largest: Size of largest community
                - smallest: Size of smallest community
                - modularity: Community modularity score (if available)

        Example:
            >>> stats = detector.get_community_stats(communities)
            >>> print(f"Found {stats['num_communities']} communities")
        """
        if not communities:
            return {
                "num_communities": 0,
                "avg_size": 0,
                "largest": 0,
                "smallest": 0,
            }

        sizes = Counter(communities.values())
        return {
            "num_communities": len(sizes),
            "avg_size": sum(sizes.values()) / len(sizes) if sizes else 0,
            "largest": max(sizes.values()) if sizes else 0,
            "smallest": min(sizes.values()) if sizes else 0,
        }

    def get_hierarchical_communities(
        self, max_levels: int = 3
    ) -> Dict[int, Dict[str, int]]:
        """Get multi-level community hierarchy.

        Args:
            max_levels: Maximum hierarchy depth (default: 3)

        Returns:
            Dict mapping level -> communities dict
                Level 0: Fine-grained (high resolution)
                Level 1: Intermediate
                Level 2+: Coarse (low resolution)

        Example:
            >>> hierarchy = detector.get_hierarchical_communities(max_levels=3)
            >>> level0 = hierarchy[0]  # Fine-grained communities
            >>> level2 = hierarchy[2]  # Coarse architectural components

        Note:
            Future enhancement - currently returns single level.
            Full hierarchical implementation requires iterative Leiden.
        """
        # TODO: Implement full hierarchical Leiden
        # For now, return single level
        communities = self.detect_communities(resolution=1.0)
        return {0: communities}
