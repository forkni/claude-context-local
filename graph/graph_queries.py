"""
Graph query engine for code analysis.

Provides high-level query operations on code graphs.
"""

import logging
from typing import Any, Dict, List, Optional, Set

try:
    import networkx as nx
except ImportError:
    nx = None

from .graph_storage import CodeGraphStorage


class GraphQueryEngine:
    """
    High-level query engine for code graphs.

    Provides convenient methods for common graph queries and analysis.
    """

    def __init__(self, graph_storage: CodeGraphStorage):
        """
        Initialize query engine.

        Args:
            graph_storage: CodeGraphStorage instance
        """
        if nx is None:
            raise ImportError(
                "NetworkX is required for graph queries. "
                "Install with: pip install networkx"
            )

        self.storage = graph_storage
        self.logger = logging.getLogger(__name__)

    def find_call_chain(
        self, start_chunk_id: str, end_chunk_id: str, max_depth: int = 10
    ) -> Optional[List[str]]:
        """
        Find shortest call chain from start to end function.

        Args:
            start_chunk_id: Starting function chunk ID
            end_chunk_id: Target function chunk ID
            max_depth: Maximum chain length to search

        Returns:
            List of chunk IDs forming the call chain, or None if no path exists
        """
        if start_chunk_id not in self.storage.graph:
            self.logger.warning(f"Start chunk {start_chunk_id} not in graph")
            return None

        if end_chunk_id not in self.storage.graph:
            self.logger.warning(f"End chunk {end_chunk_id} not in graph")
            return None

        try:
            # Use NetworkX shortest path
            path = nx.shortest_path(
                self.storage.graph, source=start_chunk_id, target=end_chunk_id
            )

            if len(path) > max_depth:
                self.logger.info(
                    f"Call chain exceeds max_depth ({len(path)} > {max_depth})"
                )
                return None

            return path

        except nx.NetworkXNoPath:
            self.logger.debug(f"No call chain from {start_chunk_id} to {end_chunk_id}")
            return None

    def find_all_callers(
        self, chunk_id: str, max_depth: int = 3
    ) -> Dict[int, Set[str]]:
        """
        Find all callers up to max_depth levels.

        Args:
            chunk_id: Function to find callers for
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary mapping depth → set of caller IDs at that depth
        """
        if chunk_id not in self.storage.graph:
            return {}

        callers_by_depth = {}
        visited = {chunk_id}
        queue = [(caller, 1) for caller in self.storage.graph.predecessors(chunk_id)]

        for caller, depth in queue:
            if caller in visited or depth > max_depth:
                continue

            visited.add(caller)

            if depth not in callers_by_depth:
                callers_by_depth[depth] = set()

            callers_by_depth[depth].add(caller)

            # Add next level callers
            for next_caller in self.storage.graph.predecessors(caller):
                if next_caller not in visited:
                    queue.append((next_caller, depth + 1))

        return callers_by_depth

    def find_all_callees(
        self, chunk_id: str, max_depth: int = 3
    ) -> Dict[int, Set[str]]:
        """
        Find all callees up to max_depth levels.

        Args:
            chunk_id: Function to find callees for
            max_depth: Maximum depth to traverse

        Returns:
            Dictionary mapping depth → set of callee IDs at that depth
        """
        if chunk_id not in self.storage.graph:
            return {}

        callees_by_depth = {}
        visited = {chunk_id}
        queue = [(callee, 1) for callee in self.storage.graph.successors(chunk_id)]

        for callee, depth in queue:
            if callee in visited or depth > max_depth:
                continue

            visited.add(callee)

            if depth not in callees_by_depth:
                callees_by_depth[depth] = set()

            callees_by_depth[depth].add(callee)

            # Add next level callees
            for next_callee in self.storage.graph.successors(callee):
                if next_callee not in visited:
                    queue.append((next_callee, depth + 1))

        return callees_by_depth

    def find_related_functions(
        self, chunk_id: str, relation_types: List[str] = None, max_depth: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Find all related functions with metadata.

        Args:
            chunk_id: Starting function
            relation_types: Types of relations (e.g., ["calls", "called_by"])
            max_depth: Maximum traversal depth

        Returns:
            List of dictionaries with function info and relationship metadata
        """
        if relation_types is None:
            relation_types = ["calls", "called_by"]

        related_ids = self.storage.get_neighbors(chunk_id, relation_types, max_depth)
        related_functions = []

        for related_id in related_ids:
            node_data = self.storage.get_node_data(related_id)
            if node_data:
                func_info = {"chunk_id": related_id, **node_data}

                # Determine relationship type
                if self.storage.graph.has_edge(chunk_id, related_id):
                    func_info["relationship"] = "calls"
                    func_info["edge_data"] = self.storage.get_edge_data(
                        chunk_id, related_id
                    )
                elif self.storage.graph.has_edge(related_id, chunk_id):
                    func_info["relationship"] = "called_by"
                    func_info["edge_data"] = self.storage.get_edge_data(
                        related_id, chunk_id
                    )

                related_functions.append(func_info)

        return related_functions

    def get_function_call_count(self, chunk_id: str) -> Dict[str, int]:
        """
        Get call statistics for a function.

        Args:
            chunk_id: Function chunk ID

        Returns:
            Dictionary with call statistics
        """
        if chunk_id not in self.storage.graph:
            return {"calls_made": 0, "called_by_count": 0}

        return {
            "calls_made": self.storage.graph.out_degree(chunk_id),
            "called_by_count": self.storage.graph.in_degree(chunk_id),
        }

    def find_entry_points(self) -> List[str]:
        """
        Find potential entry point functions (not called by anyone).

        Returns:
            List of chunk IDs that have no callers
        """
        entry_points = []

        for node in self.storage.graph.nodes():
            if self.storage.graph.in_degree(node) == 0:
                entry_points.append(node)

        return entry_points

    def find_leaf_functions(self) -> List[str]:
        """
        Find leaf functions (don't call anything).

        Returns:
            List of chunk IDs that make no calls
        """
        leaf_functions = []

        for node in self.storage.graph.nodes():
            if self.storage.graph.out_degree(node) == 0:
                leaf_functions.append(node)

        return leaf_functions

    def compute_centrality(self, method: str = "degree") -> Dict[str, float]:
        """
        Compute centrality scores for functions.

        Args:
            method: Centrality method ("degree", "betweenness", "closeness", "pagerank")

        Returns:
            Dictionary mapping chunk_id → centrality score
        """
        if method == "degree":
            return dict(self.storage.graph.degree())
        elif method == "betweenness":
            return nx.betweenness_centrality(self.storage.graph)
        elif method == "closeness":
            return nx.closeness_centrality(self.storage.graph)
        elif method == "pagerank":
            return nx.pagerank(self.storage.graph)
        else:
            raise ValueError(
                f"Unknown centrality method: {method}. "
                f"Supported: degree, betweenness, closeness, pagerank"
            )
