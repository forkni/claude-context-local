"""
Graph query engine for code analysis.

Provides high-level query operations on code graphs.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import networkx as nx

from utils.path_utils import normalize_path

from .graph_storage import CodeGraphStorage


@dataclass
class RelationshipEntry:
    """A single relationship edge in the code graph."""

    chunk_id: str
    relationship_type: str
    direction: str  # "inbound" | "outbound"
    depth: int
    edge_data: dict[str, Any] = field(default_factory=dict)


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
        # Normalize path separators before graph lookup (#40). chunk_ids on
        # Windows may use backslashes while the graph was built with forward
        # slashes (or vice-versa), causing spurious "not in graph" misses.
        start_chunk_id = start_chunk_id.replace("\\", "/")
        end_chunk_id = end_chunk_id.replace("\\", "/")

        if start_chunk_id not in self.storage.graph:
            self.logger.warning(f"Start chunk {start_chunk_id} not in graph")
            return None

        if end_chunk_id not in self.storage.graph:
            self.logger.warning(f"End chunk {end_chunk_id} not in graph")
            return None

        try:
            # Use NetworkX shortest path
            # pyrefly: ignore [missing-attribute]
            path = nx.shortest_path(
                self.storage.graph, source=start_chunk_id, target=end_chunk_id
            )

            if len(path) > max_depth:
                self.logger.info(
                    f"Call chain exceeds max_depth ({len(path)} > {max_depth})"
                )
                return None

            return path

        # pyrefly: ignore [missing-attribute]
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
                # pyrefly: ignore [missing-attribute]
                path_nodes = nx.bidirectional_shortest_path(graph, source_id, target_id)
                self.logger.debug(f"Found direct path: {source_id} → {target_id}")
            # pyrefly: ignore [missing-attribute]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        # Strategy 2: chunk_id → symbol_name (edges point to symbol names)
        if path_nodes is None and target_symbol in self.storage.graph:
            try:
                # pyrefly: ignore [missing-attribute]
                path_nodes = nx.bidirectional_shortest_path(
                    graph, source_id, target_symbol
                )
                via_symbol_name = True
                actual_target_symbol = target_symbol
                self.logger.debug(
                    f"Found path via symbol name: {source_id} → {target_symbol}"
                )
            # pyrefly: ignore [missing-attribute]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

        # Strategy 3: chunk_id → bare_method_name (for qualified names)
        if path_nodes is None and bare_target and bare_target in self.storage.graph:
            try:
                # pyrefly: ignore [missing-attribute]
                path_nodes = nx.bidirectional_shortest_path(
                    graph, source_id, bare_target
                )
                via_symbol_name = True
                actual_target_symbol = bare_target
                self.logger.debug(
                    f"Found path via bare name: {source_id} → {bare_target}"
                )
            # pyrefly: ignore [missing-attribute]
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

    # pyrefly: ignore [missing-attribute]
    def _create_filtered_subgraph(self, edge_types: list[str]) -> nx.DiGraph:
        """
        Create subgraph containing only edges of specified types.

        Args:
            edge_types: List of relationship types to include

        Returns:
            Filtered subgraph view
        """
        # Collect (u, v, key) triples — MultiDiGraph.edge_subgraph requires keys.
        filtered_edges = [
            (u, v, k)
            for u, v, k, d in self.storage.graph.edges(keys=True, data=True)
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
        self,
        chunk_id: str,
        relation_types: list[str] | None = None,
        max_depth: int = 2,
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

        # Use distinct-neighbor counts to preserve "unique callee/caller" semantics
        # under MultiDiGraph (out_degree/in_degree would count each parallel edge).
        return {
            "calls_made": len(set(self.storage.graph.successors(chunk_id))),
            "called_by_count": len(set(self.storage.graph.predecessors(chunk_id))),
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

    def _simple_digraph_view(self) -> "nx.DiGraph":
        """Collapse the MultiDiGraph to a simple DiGraph (one edge per (u,v) pair).

        Used to preserve pre-multigraph parity for degree-based and pagerank
        centrality so this correctness batch introduces no score drift.

        .. note::
            TODO: switch ``degree`` and ``pagerank`` to native MultiDiGraph counts
            (degree = total relationship sites, pagerank weighted by edge multiplicity)
            once dedicated value-shift tests are written.  Deferred from Batch 2A.
        """
        return nx.DiGraph(self.storage.graph)

    def compute_centrality(self, method: str = "degree") -> dict[str, float]:
        """
        Compute centrality scores for functions.

        Args:
            method: Centrality method ("degree", "betweenness", "closeness", "pagerank")

        Returns:
            Dictionary mapping chunk_id → centrality score (float for all methods)
        """
        if method == "degree":
            # Route through simple DiGraph view to preserve pre-multigraph parity.
            # TODO: embrace multigraph counts once dedicated value-shift tests exist.
            simple = self._simple_digraph_view()
            return {node: float(deg) for node, deg in simple.degree()}
        elif method == "betweenness":
            # betweenness_centrality is invariant to parallel edges (unweighted
            # shortest paths), so no projection needed.
            # pyrefly: ignore [missing-attribute]
            return nx.betweenness_centrality(self.storage.graph)
        elif method == "closeness":
            # closeness_centrality is invariant to parallel edges.
            # pyrefly: ignore [missing-attribute]
            return nx.closeness_centrality(self.storage.graph)
        elif method == "pagerank":
            # Route through simple DiGraph view to preserve pre-multigraph parity.
            # TODO: embrace multigraph pagerank (parallel edges → weight sum) once
            # dedicated value-shift tests are written.
            # pyrefly: ignore [missing-attribute]
            return nx.pagerank(self._simple_digraph_view())
        else:
            raise ValueError(
                f"Unknown centrality method: {method}. "
                f"Supported: degree, betweenness, closeness, pagerank"
            )

    # ------------------------------------------------------------------
    # Relationship traversal (deep interface over CodeGraphStorage)
    # ------------------------------------------------------------------

    def get_relationships(
        self,
        chunk_id: str,
        direction: str = "both",
        relation_types: list[str] | None = None,
        max_depth: int = 1,
    ) -> list[RelationshipEntry]:
        """Find all relationships for a chunk up to max_depth hops.

        Handles the graph's symbol-name edge storage: edges go from
        caller_chunk_id → target_symbol_name (not → target_chunk_id), so both
        the chunk_id and its symbol-name variants are queried as targets when
        traversing inbound edges.

        Args:
            chunk_id: Origin chunk to analyse.
            direction: "inbound" (callers), "outbound" (callees), or "both".
            relation_types: Edge types to include; None = all types.
            max_depth: Maximum traversal depth.

        Returns:
            Flat list of RelationshipEntry, each tagged with direction and depth.
        """
        results: list[RelationshipEntry] = []
        if direction in ("inbound", "both"):
            results.extend(self._traverse_inbound(chunk_id, relation_types, max_depth))
        if direction in ("outbound", "both"):
            results.extend(self._traverse_outbound(chunk_id, relation_types, max_depth))
        return results

    def get_direct_successors(self, chunk_id: str) -> list[str]:
        """Return direct outbound neighbour IDs (depth-1 callees)."""
        return self.storage.get_callees(chunk_id)

    def get_stats(self) -> dict[str, Any]:
        """Return graph statistics from the underlying storage."""
        return self.storage.get_stats()

    # ------------------------------------------------------------------
    # Private BFS helpers
    # ------------------------------------------------------------------

    def _node_variants(self, chunk_id: str) -> list[str]:
        """Return lookup variants for a node.

        Graph edges point to symbol names, not full chunk_ids.  For a chunk
        like ``file.py:10:function:bar`` the callers store an edge to ``bar``
        (and possibly ``ClassName.bar`` → bare ``bar``).  Querying both forms
        finds callers regardless of which variant they stored.
        """
        variants = [chunk_id]
        if ":" in chunk_id:
            symbol = chunk_id.split(":")[-1]
            if symbol and symbol != chunk_id:
                variants.append(symbol)
                bare = symbol.split(".")[-1]
                if bare and bare != symbol:
                    variants.append(bare)
        return variants

    def _traverse_inbound(
        self,
        chunk_id: str,
        relation_types: list[str] | None,
        max_depth: int,
    ) -> list[RelationshipEntry]:
        """BFS over inbound edges with dual symbol-name lookup at each hop.

        Uses two separate sets to prevent the "visited-before-filter" bug (#23):
        - ``visited``: tracks nodes queued for BFS expansion (prevents loops).
        - ``reported``: tracks nodes already added to results (prevents duplicates).

        Without this separation, a predecessor reachable from two different
        query-nodes via edges of different types would be marked visited on the
        first (possibly non-matching) encounter, silently suppressing the second
        (possibly matching) edge.
        """
        results: list[RelationshipEntry] = []
        origin_set = set(self._node_variants(chunk_id))
        visited: set[str] = set(origin_set)  # nodes queued for BFS expansion
        reported: set[str] = set()  # nodes already in results

        # query_nodes: the node IDs whose predecessors we will inspect at this depth
        current_query: set[str] = {v for v in origin_set if v in self.storage.graph}

        for depth in range(1, max_depth + 1):
            next_query: set[str] = set()

            for query_node in current_query:
                for pred in self.storage.get_callers(query_node):
                    edge_data = self.storage.get_edge_data(pred, query_node) or {}
                    rel_type = edge_data.get("relationship_type") or edge_data.get(
                        "type", "unknown"
                    )

                    # Report once per node on first matching edge (#23).
                    if pred not in reported and (
                        relation_types is None or rel_type in relation_types
                    ):
                        results.append(
                            RelationshipEntry(
                                chunk_id=pred,
                                relationship_type=rel_type,
                                direction="inbound",
                                depth=depth,
                                edge_data=edge_data,
                            )
                        )
                        reported.add(pred)

                    # Queue for BFS expansion using a separate visited guard.
                    if depth < max_depth:
                        for v in self._node_variants(pred):
                            if v not in visited:
                                next_query.add(v)
                                visited.add(v)

            if not next_query:
                break
            current_query = next_query

        return results

    def _traverse_outbound(
        self,
        chunk_id: str,
        relation_types: list[str] | None,
        max_depth: int,
    ) -> list[RelationshipEntry]:
        """BFS over outbound edges.

        Uses two separate sets for the same reason as _traverse_inbound (#23):
        - ``visited``: BFS expansion dedup.
        - ``reported``: result dedup.
        """
        results: list[RelationshipEntry] = []
        visited: set[str] = {chunk_id}  # nodes queued for BFS expansion
        reported: set[str] = set()  # nodes already in results
        current_nodes: set[str] = (
            {chunk_id} if chunk_id in self.storage.graph else set()
        )

        for depth in range(1, max_depth + 1):
            next_nodes: set[str] = set()

            for node in current_nodes:
                for succ in self.storage.get_callees(node):
                    edge_data = self.storage.get_edge_data(node, succ) or {}
                    rel_type = edge_data.get("relationship_type") or edge_data.get(
                        "type", "unknown"
                    )

                    # Report once per node on first matching edge (#23).
                    if succ not in reported and (
                        relation_types is None or rel_type in relation_types
                    ):
                        results.append(
                            RelationshipEntry(
                                chunk_id=succ,
                                relationship_type=rel_type,
                                direction="outbound",
                                depth=depth,
                                edge_data=edge_data,
                            )
                        )
                        reported.add(succ)

                    # Queue for BFS expansion.
                    if depth < max_depth and succ not in visited:
                        next_nodes.add(succ)
                        visited.add(succ)

            if not next_nodes:
                break
            current_nodes = next_nodes

        return results
