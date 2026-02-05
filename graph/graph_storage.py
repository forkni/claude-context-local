"""
Graph storage and persistence using NetworkX.

Provides NetworkX-based storage for code call graphs with JSON persistence.
"""

import heapq
import json
import logging
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from search.filters import normalize_path


if TYPE_CHECKING:
    from graph.relationship_types import RelationshipEdge

try:
    import networkx as nx
except ImportError:
    nx = None


# Edge-type weights for weighted BFS (SOG paper: data flow > control flow > effect flow)
# Higher weight = higher priority in graph traversal
DEFAULT_EDGE_WEIGHTS: dict[str, float] = {
    "calls": 1.0,  # Most important for code understanding
    "inherits": 0.9,  # Critical for class hierarchies
    "implements": 0.9,  # Critical for interface patterns
    "overrides": 0.85,  # Important for polymorphism
    "uses_type": 0.7,  # Type usage
    "instantiates": 0.7,  # Object creation
    "decorates": 0.5,  # Moderate signal
    "raises": 0.4,  # Exception patterns
    "catches": 0.4,  # Exception patterns
    "imports": 0.3,  # Low signal - most code imports many things
    "assigns_to": 0.5,  # Assignment tracking
    "reads_from": 0.5,  # Read tracking
    "defines_constant": 0.4,  # Constant definitions
    "defines_enum_member": 0.4,  # Enum members
    "defines_class_attr": 0.5,  # Class attributes
    "defines_field": 0.5,  # Dataclass fields
    "uses_constant": 0.4,  # Constant usage
    "uses_default": 0.3,  # Default parameter values
    "uses_global": 0.3,  # Global references
    "asserts_type": 0.4,  # Type assertions
    "uses_context_manager": 0.4,  # Context manager usage
}

# Intent-specific edge weight profiles for graph traversal
# Each profile adjusts weights to prioritize relationships relevant to the query intent
INTENT_EDGE_WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "local": {
        # Symbol lookup: boost calls, inherits, overrides (structural relationships)
        **DEFAULT_EDGE_WEIGHTS,
        "calls": 1.0,
        "inherits": 1.0,
        "overrides": 1.0,
        "implements": 1.0,
        "imports": 0.1,  # Suppress noisy import edges
    },
    "global": {
        # Architectural: boost imports, uses_type (module-level relationships)
        **DEFAULT_EDGE_WEIGHTS,
        "imports": 0.7,
        "uses_type": 0.9,
        "instantiates": 0.8,
        "calls": 0.6,  # Less emphasis on individual call chains
    },
    "navigational": {
        # Relationship tracing: boost calls, called_by direction
        **DEFAULT_EDGE_WEIGHTS,
        "calls": 1.0,
        "inherits": 0.9,
        "imports": 0.5,
    },
    "path_tracing": {
        # Path finding: uniform-ish weights for shortest path
        **dict.fromkeys(DEFAULT_EDGE_WEIGHTS, 0.7),
        "calls": 1.0,
        "inherits": 0.9,
    },
    "similarity": {
        # Similar code: boost structural relationships
        **DEFAULT_EDGE_WEIGHTS,
        "uses_type": 0.9,
        "decorates": 0.7,
        "defines_class_attr": 0.7,
    },
    "contextual": {
        # Context exploration: all relationships matter equally
        **{k: max(v, 0.5) for k, v in DEFAULT_EDGE_WEIGHTS.items()},
    },
    "hybrid": DEFAULT_EDGE_WEIGHTS.copy(),  # Default fallback
}


class CodeGraphStorage:
    """
    NetworkX-based graph storage with persistence.

    Stores call graph relationships and provides efficient graph operations.

    Storage Format:
        - Nodes: Chunk IDs with metadata (name, type, file, language)
        - Edges: Call relationships with metadata (line_number, is_method_call)
        - Persistence: JSON via nx.node_link_data/graph
    """

    def __init__(self, project_id: str, storage_dir: Optional[Path] = None) -> None:
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
        is_resolved: bool = False,
        **kwargs,
    ) -> None:
        """
        Add a call relationship edge.

        Args:
            caller_id: Chunk ID of the caller
            callee_name: Name of the called function. Can be:
                - Qualified name (ClassName.method) for self/super calls
                - Bare name (method) for unresolved calls
                - Full chunk_id (future: for fully resolved calls)
            line_number: Line number of the call
            is_method_call: Whether this is a method call
            is_resolved: Whether callee_name is fully resolved to a chunk_id
                (vs qualified name or bare name)
            **kwargs: Additional edge attributes
        """
        # Create lightweight target_name node if it doesn't exist
        # This enables get_callers(callee_name) queries to work
        # (matching add_relationship_edge() behavior at lines 167-175)
        if callee_name not in self.graph:
            self.graph.add_node(
                callee_name,
                name=callee_name,
                type="symbol_name",  # Distinguish from full chunk nodes
                is_target_name=True,  # Flag for query filtering
                is_call_target=True,  # New flag: distinguishes from relationship targets
                file="",  # Unknown file (will be resolved if chunk exists)
                language="",  # Unknown language
            )

        self.graph.add_edge(
            caller_id,
            callee_name,
            type="calls",
            line=line_number,
            is_method=is_method_call,
            is_resolved=is_resolved,
            **kwargs,
        )

    def add_relationship_edge(self, edge: "RelationshipEdge") -> None:
        """
        Add a relationship edge to the graph.

        This is the new unified method for adding any type of relationship edge.
        It replaces add_call_edge().

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
        normalized_source = normalize_path(edge.source_id)

        # Create lightweight node for target_name if it doesn't exist
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

    def get_callers(self, chunk_id: str) -> list[str]:
        """
        Get all functions that call this function.

        Args:
            chunk_id: Chunk ID to find callers for

        Returns:
            List of caller chunk IDs
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        # Debug logging for relationship queries
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

    def get_callees(self, chunk_id: str) -> list[str]:
        """
        Get all functions called by this function.

        Args:
            chunk_id: Chunk ID to find callees for

        Returns:
            List of callee chunk IDs or names
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return []

        # In a directed graph, successors are callees
        return list(self.graph.successors(normalized_chunk_id))

    def get_neighbors(
        self,
        chunk_id: str,
        relation_types: Optional[list[str]] = None,
        max_depth: int = 1,
        exclude_import_categories: Optional[list[str]] = None,
        edge_weights: Optional[dict[str, float]] = None,
    ) -> set[str]:
        """
        Get all related chunks within max_depth hops.

        Args:
            chunk_id: Starting chunk ID
            relation_types: Types of relations to follow (e.g., ["calls", "called_by", "inherits", "imports"])
                Supports all 21 relationship types. Use "_by" suffix for reverse direction
                (e.g., "called_by", "imported_by", "inherited_by")
            max_depth: Maximum graph traversal depth
            exclude_import_categories: Categories to exclude for "imports" edges
                (e.g., ["stdlib", "third_party"] to filter out noise)
            edge_weights: Optional edge-type weights for weighted BFS (higher weight = higher priority).
                When None, uses unweighted BFS (default behavior). When provided, uses priority queue
                to expand higher-weight edges first.

        Returns:
            Set of related chunk IDs
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return set()

        # Default to both directions of call relationships for backward compatibility
        if relation_types is None:
            relation_types = ["calls", "called_by"]

        neighbors = set()

        # Choose BFS implementation based on edge_weights parameter
        if edge_weights is None:
            # Unweighted BFS (original behavior, backward compatible)
            queue = deque([(normalized_chunk_id, 0)])
            visited = {normalized_chunk_id}

            while queue:
                current_id, depth = queue.popleft()

                if depth >= max_depth:
                    continue

                # Process outgoing edges (forward relationships)
                for _, target, edge_data in self.graph.out_edges(current_id, data=True):
                    edge_type = edge_data.get("relationship_type") or edge_data.get(
                        "type"
                    )

                    # Check if this edge type is requested
                    if edge_type and edge_type in relation_types:
                        # Apply import category filtering if needed
                        if edge_type == "imports" and exclude_import_categories:
                            if self._should_exclude_edge(
                                current_id, target, exclude_import_categories
                            ):
                                continue

                        if target not in visited:
                            neighbors.add(target)
                            visited.add(target)
                            queue.append((target, depth + 1))

                # Process incoming edges (reverse relationships)
                for source, _, edge_data in self.graph.in_edges(current_id, data=True):
                    edge_type = edge_data.get("relationship_type") or edge_data.get(
                        "type"
                    )

                    # Convert to reverse type name (e.g., "calls" -> "called_by")
                    reverse_type = (
                        self._get_reverse_relation_type(edge_type)
                        if edge_type
                        else None
                    )

                    # Check if this reverse type is requested
                    if reverse_type and reverse_type in relation_types:
                        # Apply import category filtering if needed
                        if edge_type == "imports" and exclude_import_categories:
                            if self._should_exclude_edge(
                                source, current_id, exclude_import_categories
                            ):
                                continue

                        if source not in visited:
                            neighbors.add(source)
                            visited.add(source)
                            queue.append((source, depth + 1))

        else:
            # Weighted BFS using priority queue (higher weight = higher priority)
            # Priority queue format: (-weight, counter, chunk_id, depth)
            # Use negative weight so heapq min-heap becomes max-heap for weights
            # Mark visited on dequeue (not enqueue) for correct priority semantics
            counter = 0  # Tie-breaker for equal weights
            pq = [(0.0, counter, normalized_chunk_id, 0)]  # Start node has priority 0
            visited = set()

            while pq:
                neg_weight, _, current_id, depth = heapq.heappop(pq)

                # Skip if already processed via higher-priority path
                if current_id in visited:
                    continue
                visited.add(current_id)

                # Add to neighbors (except start node)
                if current_id != normalized_chunk_id:
                    neighbors.add(current_id)

                if depth >= max_depth:
                    continue

                # Process outgoing edges (forward relationships)
                for _, target, edge_data in self.graph.out_edges(current_id, data=True):
                    edge_type = edge_data.get("relationship_type") or edge_data.get(
                        "type"
                    )

                    # Check if this edge type is requested
                    if edge_type and edge_type in relation_types:
                        # Apply import category filtering if needed
                        if edge_type == "imports" and exclude_import_categories:
                            if self._should_exclude_edge(
                                current_id, target, exclude_import_categories
                            ):
                                continue

                        if target not in visited:
                            # Get weight for this edge type (default 0.5 if not in dict)
                            weight = edge_weights.get(edge_type, 0.5)
                            counter += 1
                            heapq.heappush(pq, (-weight, counter, target, depth + 1))

                # Process incoming edges (reverse relationships)
                for source, _, edge_data in self.graph.in_edges(current_id, data=True):
                    edge_type = edge_data.get("relationship_type") or edge_data.get(
                        "type"
                    )

                    # Convert to reverse type name (e.g., "calls" -> "called_by")
                    reverse_type = (
                        self._get_reverse_relation_type(edge_type)
                        if edge_type
                        else None
                    )

                    # Check if this reverse type is requested
                    if reverse_type and reverse_type in relation_types:
                        # Apply import category filtering if needed
                        if edge_type == "imports" and exclude_import_categories:
                            if self._should_exclude_edge(
                                source, current_id, exclude_import_categories
                            ):
                                continue

                        if source not in visited:
                            # Get weight for the forward edge type (not reverse)
                            weight = edge_weights.get(edge_type, 0.5)
                            counter += 1
                            heapq.heappush(pq, (-weight, counter, source, depth + 1))

        return neighbors

    def _get_reverse_relation_type(self, relation_type: str) -> str:
        """
        Get the reverse name for a relationship type.

        Args:
            relation_type: Forward relationship type (e.g., "calls", "imports", "inherits")

        Returns:
            Reverse relationship type (e.g., "called_by", "imported_by", "inherited_by")

        Note:
            Most verb-based types need past participle form + "_by".
            Special irregular forms are handled explicitly.
        """
        # Comprehensive mapping for all relationship types
        reverse_mapping = {
            "calls": "called_by",
            "inherits": "inherited_by",
            "uses_type": "used_as_type_by",
            "imports": "imported_by",
            "decorates": "decorated_by",
            "raises": "raised_by",
            "catches": "caught_by",
            "instantiates": "instantiated_by",
            "implements": "implemented_by",
            "overrides": "overridden_by",
            "assigns_to": "assigned_by",
            "reads_from": "read_by",
            "defines_constant": "constant_defined_by",
            "defines_enum_member": "enum_member_defined_by",
            "defines_class_attr": "class_attr_defined_by",
            "defines_field": "field_defined_by",
            "uses_constant": "constant_used_by",
            "uses_default": "default_used_by",
            "uses_global": "global_used_by",
            "asserts_type": "type_asserted_by",
            "uses_context_manager": "context_manager_used_by",
        }

        if relation_type in reverse_mapping:
            return reverse_mapping[relation_type]

        # Fallback: append "_by" (should not be reached if mapping is complete)
        return f"{relation_type}_by"

    def _should_exclude_edge(
        self, source_id: str, target_id: str, exclude_categories: list[str]
    ) -> bool:
        """
        Check if edge should be excluded based on import category.

        Args:
            source_id: Source node ID
            target_id: Target node ID
            exclude_categories: Categories to exclude (e.g., ["stdlib", "third_party"])

        Returns:
            True if edge should be excluded, False otherwise
        """
        # Get edge data
        edge_data = self.get_edge_data(source_id, target_id)
        if not edge_data:
            return False

        # Only filter "imports" relationships
        edge_type = edge_data.get("relationship_type") or edge_data.get("type")
        if edge_type != "imports":
            return False

        # Check import category
        import_category = edge_data.get("metadata", {}).get("import_category")
        if not import_category:
            # Fallback: check if import_category is a direct edge attribute
            import_category = edge_data.get("import_category")

        if import_category in exclude_categories:
            self.logger.debug(
                f"Excluding {edge_type} edge {source_id} -> {target_id} "
                f"(category: {import_category})"
            )
            return True

        return False

    def get_node_data(self, chunk_id: str) -> Optional[dict[str, Any]]:
        """
        Get node metadata.

        Args:
            chunk_id: Chunk ID

        Returns:
            Node data dictionary or None if not found
        """
        # Normalize path separators to forward slashes for consistent lookup
        # Query path normalization mismatch
        normalized_chunk_id = normalize_path(chunk_id)

        if normalized_chunk_id not in self.graph:
            return None

        return dict(self.graph.nodes[normalized_chunk_id])

    def get_edge_data(self, caller_id: str, callee_id: str) -> Optional[dict[str, Any]]:
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
        # Query path normalization mismatch
        normalized_caller = normalize_path(caller_id)
        normalized_callee = normalize_path(callee_id)

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

    def get_stats(self) -> dict[str, Any]:
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

    def store_community_map(self, community_map: dict[str, int]) -> None:
        """Persist community assignments to JSON file.

        Args:
            community_map: Dict mapping chunk_id -> community_id
        """
        community_path = self.storage_dir / f"{self.project_id}_communities.json"
        with open(community_path, "w") as f:
            json.dump(community_map, f, indent=2)
        self.logger.info(
            f"Stored {len(community_map)} community assignments to {community_path}"
        )

    def load_community_map(self) -> Optional[dict[str, int]]:
        """Load stored community assignments.

        Returns:
            Dict mapping chunk_id -> community_id, or None if not found
        """
        community_path = self.storage_dir / f"{self.project_id}_communities.json"
        if community_path.exists():
            with open(community_path, "r") as f:
                return json.load(f)
        return None

    def get_community_for_chunk(self, chunk_id: str) -> Optional[int]:
        """Get community ID for a specific chunk.

        Args:
            chunk_id: Chunk identifier

        Returns:
            Community ID (int) or None if not found
        """
        community_map = self.load_community_map()
        if community_map:
            return community_map.get(chunk_id)
        return None
