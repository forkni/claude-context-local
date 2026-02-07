"""
Graph query engine for code analysis.

Provides high-level query operations on code graphs.
"""

import logging
from typing import Any


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

    def __init__(self, graph_storage: CodeGraphStorage) -> None:
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
    ) -> list[str] | None:
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

    def find_path(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 10,
        edge_types: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """
        Find shortest path between two nodes with optional edge type filtering.

        Uses multi-strategy approach to handle graph structure where edges point
        from chunk_ids to symbol names (not chunk_id to chunk_id).

        Strategies:
        1. Try direct chunk_id → chunk_id path (may work for some edges)
        2. Try chunk_id → target_symbol_name path (edges point to symbol names)
        3. Try chunk_id → bare_method_name path (for qualified names)

        Args:
            source_id: Source chunk ID
            target_id: Target chunk ID
            max_hops: Maximum path length
            edge_types: Filter by relationship types (None = all types)

        Returns:
            Dict with path nodes, edges, and metadata, or None if no path
        """
        # Import normalize_path here to avoid circular import
        from search.filters import normalize_path

        # Normalize paths
        source_id = normalize_path(source_id)
        target_id = normalize_path(target_id)

        # Check source exists (required)
        if source_id not in self.storage.graph:
            self.logger.warning(f"Source node {source_id} not in graph")
            return None

        # Target might exist as chunk_id OR we need symbol name fallback
        target_exists = target_id in self.storage.graph

        # Extract target symbol name for fallback lookup
        # Handles: "file.py:10-20:function:my_func" → "my_func"
        # Also handles qualified names: "ClassName.method" → try both
        target_symbol = target_id.split(":")[-1] if ":" in target_id else target_id
        bare_target = target_symbol.split(".")[-1] if "." in target_symbol else None

        # Get graph (filtered or full)
        if edge_types:
            graph = self._create_filtered_subgraph(edge_types)
        else:
            graph = self.storage.graph

        # Try multiple path strategies
        path_nodes = None
        via_symbol_name = False
        actual_target_symbol = None

        # Strategy 1: Direct chunk_id → chunk_id (if target exists as node)
        if target_exists:
            try:
                path_nodes = nx.bidirectional_shortest_path(graph, source_id, target_id)
                self.logger.debug(f"Found direct path: {source_id} → {target_id}")
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        # Strategy 2: chunk_id → symbol_name (edges point to symbol names)
        if path_nodes is None and target_symbol in self.storage.graph:
            try:
                path_nodes = nx.bidirectional_shortest_path(
                    graph, source_id, target_symbol
                )
                via_symbol_name = True
                actual_target_symbol = target_symbol
                self.logger.debug(
                    f"Found path via symbol name: {source_id} → {target_symbol}"
                )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        # Strategy 3: chunk_id → bare_method_name (for qualified names)
        if path_nodes is None and bare_target and bare_target in self.storage.graph:
            try:
                path_nodes = nx.bidirectional_shortest_path(
                    graph, source_id, bare_target
                )
                via_symbol_name = True
                actual_target_symbol = bare_target
                self.logger.debug(
                    f"Found path via bare name: {source_id} → {bare_target}"
                )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        if path_nodes is None:
            self.logger.debug(f"No path from {source_id} to {target_id}")
            return None

        if len(path_nodes) - 1 > max_hops:
            self.logger.info(
                f"Path exceeds max_hops ({len(path_nodes) - 1} > {max_hops})"
            )
            return None

        # Build result with node and edge metadata
        result = self._build_path_result(path_nodes, edge_types)

        # If path ends at symbol name node, enrich with actual target info
        if via_symbol_name and target_exists:
            result["via_symbol_name"] = actual_target_symbol
            result["resolved_target_chunk_id"] = target_id
            # Update last node in path to show actual target chunk_id
            if result["path"]:
                target_node_data = self.storage.get_node_data(target_id) or {}
                result["path"][-1]["node"]["chunk_id"] = target_id
                result["path"][-1]["node"]["name"] = target_node_data.get(
                    "name", target_symbol
                )
                result["path"][-1]["node"]["type"] = target_node_data.get(
                    "type", "unknown"
                )
                result["path"][-1]["node"]["file"] = target_node_data.get(
                    "file", target_id.split(":")[0]
                )

        return result

    def _create_filtered_subgraph(self, edge_types: list[str]) -> nx.DiGraph:
        """
        Create subgraph containing only edges of specified types.

        Args:
            edge_types: List of relationship types to include

        Returns:
            Filtered subgraph view
        """
        filtered_edges = [
            (u, v)
            for u, v, d in self.storage.graph.edges(data=True)
            if d.get("relationship_type") in edge_types or d.get("type") in edge_types
        ]
        return self.storage.graph.edge_subgraph(filtered_edges)

    def _build_path_result(
        self, path_nodes: list[str], edge_types_filter: list[str] | None
    ) -> dict[str, Any]:
        """
        Build detailed path result with node and edge metadata.

        Args:
            path_nodes: List of chunk IDs forming the path
            edge_types_filter: Edge types filter that was applied (for reference)

        Returns:
            Dict with path, nodes, edges, and metadata
        """
        path = []
        edge_types_traversed = set()

        for i, node_id in enumerate(path_nodes):
            node_data = self.storage.get_node_data(node_id) or {}

            # Get edge to next node (if not last node)
            edge_to_next = None
            if i < len(path_nodes) - 1:
                next_node = path_nodes[i + 1]
                edge_data = self.storage.get_edge_data(node_id, next_node)
                if edge_data:
                    rel_type = edge_data.get("relationship_type") or edge_data.get(
                        "type"
                    )
                    edge_to_next = {
                        "relationship_type": rel_type,
                        "line": edge_data.get("line"),
                    }
                    if rel_type:
                        edge_types_traversed.add(rel_type)

            path.append(
                {
                    "node": {
                        "chunk_id": node_id,
                        "name": node_data.get("name", node_id.split(":")[-1]),
                        "type": node_data.get("type", "unknown"),
                        "file": node_data.get("file", node_id.split(":")[0]),
                    },
                    "edge_to_next": edge_to_next,
                }
            )

        return {
            "path_found": True,
            "path_length": len(path_nodes) - 1,
            "path": path,
            "edge_types_traversed": list(edge_types_traversed),
        }

    def find_all_callers(
        self, chunk_id: str, max_depth: int = 3
    ) -> dict[int, set[str]]:
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
    ) -> dict[int, set[str]]:
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
        self, chunk_id: str, relation_types: list[str] = None, max_depth: int = 2
    ) -> list[dict[str, Any]]:
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

    def get_function_call_count(self, chunk_id: str) -> dict[str, int]:
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

    def find_entry_points(self) -> list[str]:
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

    def find_leaf_functions(self) -> list[str]:
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

    def compute_centrality(self, method: str = "degree") -> dict[str, float]:
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
