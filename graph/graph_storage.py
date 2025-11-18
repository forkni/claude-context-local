"""
Graph storage and persistence using NetworkX.

Provides NetworkX-based storage for code call graphs with JSON persistence.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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
        **kwargs,
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
            **kwargs,
        )

    def add_call_edge(
        self,
        caller_id: str,
        callee_name: str,
        line_number: int = 0,
        is_method_call: bool = False,
        **kwargs,
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
            **kwargs,
        )

    def add_relationship_edge(self, edge: "RelationshipEdge") -> None:
        """
        Add a relationship edge to the graph (Phase 3).

        This is the new unified method for adding any type of relationship edge.
        It replaces add_call_edge() for Phase 3 code.

        Args:
            edge: RelationshipEdge object with all relationship data

        Example:
            >>> from graph.relationship_types import RelationshipEdge, RelationshipType
            >>> edge = RelationshipEdge(
            ...     source_id="child.py:1-10:class:Child",
            ...     target_name="Parent",
            ...     relationship_type=RelationshipType.INHERITS,
            ...     line_number=1
            ... )
            >>> graph_storage.add_relationship_edge(edge)
        """
        # Normalize source_id path separators to forward slashes (cross-platform)
        normalized_source = edge.source_id.replace("\\", "/")

        # CRITICAL FIX: Create lightweight node for target_name if it doesn't exist
        # This enables queries like get_callers("BaseRelationshipExtractor") to work
        #
        # Background: Edges use symbol names as targets (e.g., "BaseRelationshipExtractor")
        # but only full chunk_ids exist as nodes initially. Without target name nodes,
        # queries fail silently because NetworkX checks "if node in graph" before traversing.
        #
        # Solution: Create lightweight "symbol_name" nodes that serve as query endpoints.
        # These nodes have minimal metadata and are flagged with is_target_name=True.
        if edge.target_name not in self.graph:
            self.graph.add_node(
                edge.target_name,
                name=edge.target_name,
                type="symbol_name",  # Distinguish from full chunk nodes
                is_target_name=True,  # Flag for query filtering if needed
                file="",  # Unknown file (symbol might be external or not yet indexed)
                language="",  # Unknown language
            )

        # Add edge to graph with all attributes
        self.graph.add_edge(
            normalized_source,
            edge.target_name,
            type=edge.relationship_type.value,
            line=edge.line_number,
            confidence=edge.confidence,
            **edge.metadata,  # Include all additional metadata
        )

    def get_callers(self, chunk_id: str) -> List[str]:
        """
        Get all functions that call this function.

        Args:
            chunk_id: Chunk ID to find callers for

        Returns:
            List of caller chunk IDs
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Fixes Issue 2: Query path normalization mismatch
        normalized_chunk_id = chunk_id.replace("\\", "/")

        # Debug logging for Phase 3 relationship queries
        self.logger.debug(
            f"[GET_CALLERS] {chunk_id} → normalized: {normalized_chunk_id}"
        )
        self.logger.debug(
            f"  [GET_CALLERS] Node exists: {normalized_chunk_id in self.graph}, Total nodes: {self.graph.number_of_nodes()}"
        )

        if normalized_chunk_id not in self.graph:
            self.logger.debug("  [GET_CALLERS] → Node not found, returning []")
            return []

        # In a directed graph, predecessors are callers
        predecessors = list(self.graph.predecessors(normalized_chunk_id))
        self.logger.debug(
            f"  [GET_CALLERS] → Found {len(predecessors)} predecessors: {predecessors[:3] if predecessors else '[]'}..."
        )
        return predecessors

    def get_callees(self, chunk_id: str) -> List[str]:
        """
        Get all functions called by this function.

        Args:
            chunk_id: Chunk ID to find callees for

        Returns:
            List of callee chunk IDs or names
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Fixes Issue 2: Query path normalization mismatch
        normalized_chunk_id = chunk_id.replace("\\", "/")

        if normalized_chunk_id not in self.graph:
            return []

        # In a directed graph, successors are callees
        return list(self.graph.successors(normalized_chunk_id))

    def get_neighbors(
        self,
        chunk_id: str,
        relation_types: Optional[List[str]] = None,
        max_depth: int = 1,
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
        # Normalize path separators to forward slashes for consistent lookup
        # Fixes Issue 2: Query path normalization mismatch
        normalized_chunk_id = chunk_id.replace("\\", "/")

        if normalized_chunk_id not in self.graph:
            return set()

        # Default to both directions
        if relation_types is None:
            relation_types = ["calls", "called_by"]

        neighbors = set()

        # BFS traversal
        queue = [(normalized_chunk_id, 0)]
        visited = {normalized_chunk_id}

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
        # Normalize path separators to forward slashes for consistent lookup
        # Fixes Issue 2: Query path normalization mismatch
        normalized_chunk_id = chunk_id.replace("\\", "/")

        if normalized_chunk_id not in self.graph:
            return None

        return dict(self.graph.nodes[normalized_chunk_id])

    def get_edge_data(self, caller_id: str, callee_id: str) -> Optional[Dict[str, Any]]:
        """
        Get edge metadata with validation and normalization.

        Args:
            caller_id: Caller chunk ID (source node)
            callee_id: Callee chunk ID (target node)

        Returns:
            Edge data dictionary with normalized keys, or None if edge not found.
            Guaranteed to have 'relationship_type' and 'line_number' fields (with defaults).
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Fixes Issue 2: Query path normalization mismatch
        normalized_caller = caller_id.replace("\\", "/")
        normalized_callee = callee_id.replace("\\", "/")

        if not self.graph.has_edge(normalized_caller, normalized_callee):
            return None

        edge_data = dict(self.graph.edges[normalized_caller, normalized_callee])

        # Validate and normalize required fields
        # Support both old ('type', 'line') and new ('relationship_type', 'line_number') keys

        # 1. Normalize relationship_type
        if "relationship_type" not in edge_data:
            if "type" in edge_data:
                edge_data["relationship_type"] = edge_data["type"]
            else:
                self.logger.warning(
                    f"Edge {caller_id} → {callee_id} missing relationship type, defaulting to 'calls'"
                )
                edge_data["relationship_type"] = "calls"

        # 2. Normalize line_number
        if "line_number" not in edge_data:
            if "line" in edge_data:
                edge_data["line_number"] = edge_data["line"]
            else:
                # No line number available - use 0 as sentinel
                edge_data["line_number"] = 0

        # 3. Ensure confidence exists (optional but useful)
        if "confidence" not in edge_data:
            edge_data["confidence"] = 1.0  # Default to full confidence

        # 4. Validate data types
        try:
            # Ensure line_number is int
            edge_data["line_number"] = int(edge_data["line_number"])
        except (ValueError, TypeError):
            self.logger.warning(
                f"Edge {caller_id} → {callee_id} has invalid line_number, defaulting to 0"
            )
            edge_data["line_number"] = 0

        try:
            # Ensure confidence is float
            edge_data["confidence"] = float(edge_data["confidence"])
        except (ValueError, TypeError):
            self.logger.warning(
                f"Edge {caller_id} → {callee_id} has invalid confidence, defaulting to 1.0"
            )
            edge_data["confidence"] = 1.0

        return edge_data

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
            with open(self.graph_path, "w") as f:
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
            with open(self.graph_path, "r") as f:
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
