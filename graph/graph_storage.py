"""
Graph storage and persistence using NetworkX.

Provides NetworkX-based storage for code call graphs with JSON persistence.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any

try:
    import networkx as nx
except ImportError:
    nx = None


class CodeGraphStorage:
    """
    NetworkX-based graph storage with persistence.

    Stores call graph relationships and provides efficient graph operations.

    Storage Format:
        - Nodes: Chunk IDs with metadata (name, type, file, language)
        - Edges: Call relationships with metadata (line_number, is_method_call)
        - Persistence: JSON via nx.node_link_data/graph
    """

    def __init__(self, project_id: str, storage_dir: Optional[Path] = None):
        """
        Initialize graph storage.

        Args:
            project_id: Unique identifier for the project
            storage_dir: Directory for graph storage (default: ~/.claude_code_search/graphs)
        """
        if nx is None:
            raise ImportError(
                "NetworkX is required for graph storage. "
                "Install with: pip install networkx"
            )

        self.logger = logging.getLogger(__name__)
        self.project_id = project_id

        # Setup storage directory
        if storage_dir is None:
            home = Path.home()
            storage_dir = home / ".claude_code_search" / "graphs"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Graph file path
        self.graph_path = self.storage_dir / f"{project_id}_call_graph.json"

        # Initialize directed graph (calls have direction)
        self.graph = nx.DiGraph()

        # Load existing graph if available
        if self.graph_path.exists():
            self.load()

    def add_node(
        self,
        chunk_id: str,
        name: str,
        chunk_type: str,
        file_path: str,
        language: str = "python",
        **kwargs
    ) -> None:
        """
        Add a node to the graph.

        Args:
            chunk_id: Unique chunk identifier
            name: Function/class/method name
            chunk_type: Type of chunk (function, method, class, etc.)
            file_path: Source file path
            language: Programming language
            **kwargs: Additional node attributes
        """
        self.graph.add_node(
            chunk_id,
            name=name,
            type=chunk_type,
            file=file_path,
            language=language,
            **kwargs
        )

    def add_call_edge(
        self,
        caller_id: str,
        callee_name: str,
        line_number: int = 0,
        is_method_call: bool = False,
        **kwargs
    ) -> None:
        """
        Add a call relationship edge.

        Args:
            caller_id: Chunk ID of the caller
            callee_name: Name of the called function (may not have chunk_id yet)
            line_number: Line number of the call
            is_method_call: Whether this is a method call
            **kwargs: Additional edge attributes
        """
        # Note: callee_name might not correspond to a chunk_id yet
        # We store the name and will resolve to chunk_id later if needed
        self.graph.add_edge(
            caller_id,
            callee_name,
            type="calls",
            line=line_number,
            is_method=is_method_call,
            **kwargs
        )

    def get_callers(self, chunk_id: str) -> List[str]:
        """
        Get all functions that call this function.

        Args:
            chunk_id: Chunk ID to find callers for

        Returns:
            List of caller chunk IDs
        """
        if chunk_id not in self.graph:
            return []

        # In a directed graph, predecessors are callers
        return list(self.graph.predecessors(chunk_id))

    def get_callees(self, chunk_id: str) -> List[str]:
        """
        Get all functions called by this function.

        Args:
            chunk_id: Chunk ID to find callees for

        Returns:
            List of callee chunk IDs or names
        """
        if chunk_id not in self.graph:
            return []

        # In a directed graph, successors are callees
        return list(self.graph.successors(chunk_id))

    def get_neighbors(
        self,
        chunk_id: str,
        relation_types: Optional[List[str]] = None,
        max_depth: int = 1
    ) -> Set[str]:
        """
        Get all related chunks within max_depth hops.

        Args:
            chunk_id: Starting chunk ID
            relation_types: Types of relations to follow (e.g., ["calls", "called_by"])
            max_depth: Maximum graph traversal depth

        Returns:
            Set of related chunk IDs
        """
        if chunk_id not in self.graph:
            return set()

        # Default to both directions
        if relation_types is None:
            relation_types = ["calls", "called_by"]

        neighbors = set()

        # BFS traversal
        queue = [(chunk_id, 0)]
        visited = {chunk_id}

        while queue:
            current_id, depth = queue.pop(0)

            if depth >= max_depth:
                continue

            # Get successors (callees) if "calls" in relation_types
            if "calls" in relation_types:
                for callee in self.graph.successors(current_id):
                    if callee not in visited:
                        neighbors.add(callee)
                        visited.add(callee)
                        queue.append((callee, depth + 1))

            # Get predecessors (callers) if "called_by" in relation_types
            if "called_by" in relation_types:
                for caller in self.graph.predecessors(current_id):
                    if caller not in visited:
                        neighbors.add(caller)
                        visited.add(caller)
                        queue.append((caller, depth + 1))

        return neighbors

    def get_node_data(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Get node metadata.

        Args:
            chunk_id: Chunk ID

        Returns:
            Node data dictionary or None if not found
        """
        if chunk_id not in self.graph:
            return None

        return dict(self.graph.nodes[chunk_id])

    def get_edge_data(self, caller_id: str, callee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get edge metadata.

        Args:
            caller_id: Caller chunk ID
            callee_id: Callee chunk ID

        Returns:
            Edge data dictionary or None if not found
        """
        if not self.graph.has_edge(caller_id, callee_id):
            return None

        return dict(self.graph.edges[caller_id, callee_id])

    def save(self) -> None:
        """
        Save graph to JSON file.

        Uses NetworkX's node_link_data format for efficient serialization.
        """
        try:
            # Convert graph to JSON-serializable format
            # Using edges="edges" for NetworkX 3.6+ forward compatibility
            data = nx.node_link_data(self.graph, edges="edges")

            # Save to file
            with open(self.graph_path, 'w') as f:
                json.dump(data, f, indent=2)

            self.logger.info(
                f"Saved call graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges → {self.graph_path}"
            )

        except Exception as e:
            self.logger.error(f"Failed to save graph: {e}")
            raise

    def load(self) -> bool:
        """
        Load graph from JSON file.

        Returns:
            True if graph was loaded, False if file doesn't exist
        """
        if not self.graph_path.exists():
            self.logger.info(f"No existing graph found at {self.graph_path}")
            return False

        try:
            with open(self.graph_path, 'r') as f:
                data = json.load(f)

            # Reconstruct graph from JSON
            # Using edges="edges" for NetworkX 3.6+ forward compatibility
            self.graph = nx.node_link_graph(data, directed=True, edges="edges")

            self.logger.info(
                f"Loaded call graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges ← {self.graph_path}"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to load graph: {e}")
            # Initialize empty graph on error
            self.graph = nx.DiGraph()
            return False

    def clear(self) -> None:
        """Clear all nodes and edges from the graph."""
        self.graph.clear()
        self.logger.info("Cleared call graph")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get graph statistics.

        Returns:
            Dictionary with graph statistics
        """
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "is_directed": self.graph.is_directed(),
            "storage_path": str(self.graph_path),
            "exists_on_disk": self.graph_path.exists(),
        }

    def __len__(self) -> int:
        """Return number of nodes in graph."""
        return self.graph.number_of_nodes()

    def __contains__(self, chunk_id: str) -> bool:
        """Check if chunk_id is in graph."""
        return chunk_id in self.graph
