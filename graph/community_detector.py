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

        Args:
            resolution: Resolution parameter (default: 1.0)
                       Higher values = more/smaller communities (fine-grained)
                       Lower values = fewer/larger communities (coarse)

        Returns:
            Dict mapping chunk_id -> community_id

        Example:
            >>> detector = CommunityDetector(graph_storage)
            >>> communities = detector.detect_communities(resolution=1.0)
            >>> # {'file.py:10-20:function:foo': 0, 'file.py:25-35:function:bar': 0}
        """
        if self.nx_graph.number_of_nodes() == 0:
            self.logger.warning("Empty graph - no communities to detect")
            return {}

        # Convert to undirected graph (community detection requires undirected)
        undirected = self.nx_graph.to_undirected()

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
