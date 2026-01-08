"""Graph integration layer for call graph storage operations."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Import graph storage for call graph
try:
    from graph.graph_storage import CodeGraphStorage

    GRAPH_STORAGE_AVAILABLE = True
except ImportError:
    GRAPH_STORAGE_AVAILABLE = False
    CodeGraphStorage = None


# Semantic chunk types that can have relationships
# Based on Codanna's approach: index ALL semantic symbols
SEMANTIC_TYPES = (
    "function",
    "method",
    "decorated_definition",
    "class",
    "struct",
    "interface",
    "enum",
    "trait",
    "impl",
    "constant",
    "variable",
)


class GraphIntegration:
    """Wrapper for call graph storage operations.

    This class isolates all graph-related logic from CodeIndexManager,
    providing a clean interface for graph operations.
    """

    def __init__(self, project_id: Optional[str], storage_dir: Path):
        """Initialize graph storage if available.

        Args:
            project_id: Unique project identifier for graph storage
            storage_dir: Directory where index is stored (graph will be in parent dir)
        """
        self._logger = logging.getLogger(__name__)
        self.storage = None

        if GRAPH_STORAGE_AVAILABLE and project_id:
            try:
                # Store graph in same directory as vector index
                graph_dir = storage_dir.parent
                self.storage = CodeGraphStorage(
                    project_id=project_id, storage_dir=graph_dir
                )
                self._logger.info(
                    f"Call graph storage initialized for project: {project_id}"
                )
            except Exception as e:
                self._logger.warning(f"Failed to initialize graph storage: {e}")

    def add_chunk(self, chunk_id: str, metadata: Dict[str, Any]) -> None:
        """Add chunk to call graph storage.

        Args:
            chunk_id: Unique chunk identifier
            metadata: Chunk metadata including calls and relationships
        """
        if self.storage is None:
            self._logger.debug(f"add_chunk: graph storage is None, skipping {chunk_id}")
            return

        try:
            # Process all semantic chunk types for relationships
            # - Functions/methods: call relationships
            # - Classes/structs/interfaces/etc: inheritance, type usage
            chunk_type = metadata.get("chunk_type")
            chunk_name = metadata.get("name")
            relationships = metadata.get("relationships", [])

            self._logger.debug(
                f"add_chunk called: chunk_id={chunk_id}, type={chunk_type}, name={chunk_name}"
            )

            if chunk_type not in SEMANTIC_TYPES:
                # Allow through if it has relationships (edge case)
                if not relationships:
                    self._logger.debug(
                        f"Skipping non-semantic chunk: {chunk_id} (type={chunk_type})"
                    )
                    return
                else:
                    self._logger.debug(
                        f"Processing non-semantic chunk with relationships: {chunk_id} (type={chunk_type}, rels={len(relationships)})"
                    )

            self._logger.debug(f"Adding {chunk_type} '{metadata.get('name')}' to graph")

            # Add node for this chunk
            self.storage.add_node(
                chunk_id=chunk_id,
                name=metadata.get("name", "unknown"),
                chunk_type=chunk_type,
                file_path=metadata.get("file_path", ""),
                language=metadata.get("language", "python"),
            )

            # Add call edges from function call extraction
            calls = metadata.get("calls", [])
            for call_dict in calls:
                self.storage.add_call_edge(
                    caller_id=chunk_id,
                    callee_name=call_dict.get("callee_name", "unknown"),
                    line_number=call_dict.get("line_number", 0),
                    is_method_call=call_dict.get("is_method_call", False),
                )

            # Add all relationship edges
            relationships = metadata.get("relationships", [])
            if relationships:
                self._logger.debug(
                    f"Processing {len(relationships)} relationship edges for {chunk_id}"
                )
                for rel_dict in relationships:
                    try:
                        # Import RelationshipEdge to reconstruct from dict
                        from graph.relationship_types import (
                            RelationshipEdge,
                            RelationshipType,
                        )

                        # Reconstruct RelationshipEdge from dict
                        edge = RelationshipEdge(
                            source_id=rel_dict.get("source_id", chunk_id),
                            target_name=rel_dict.get("target_name", "unknown"),
                            relationship_type=RelationshipType(
                                rel_dict.get("relationship_type", "calls")
                            ),
                            line_number=rel_dict.get("line_number", 0),
                            confidence=rel_dict.get("confidence", 1.0),
                            metadata=rel_dict.get("metadata", {}),
                        )

                        # Add to graph storage
                        self.storage.add_relationship_edge(edge)

                    except Exception as e:
                        self._logger.warning(
                            f"Failed to add relationship edge from {chunk_id}: {e}"
                        )

        except Exception as e:
            self._logger.warning(f"Failed to add {chunk_id} to graph: {e}")

    def build_graph_from_chunks(self, chunks) -> None:
        """Build graph from chunks WITHOUT embeddings (for pre-embedding community detection).

        This enables the two-pass chunking flow:
        1. Chunk WITHOUT merging
        2. Build graph from unmerged chunks
        3. Detect communities
        4. Remerge with community boundaries
        5. Embed and index

        Uses NetworkX DiGraph API:
        - G.add_node(chunk_id, **attrs)
        - G.add_edge(caller, callee, **attrs)

        Reference: https://networkx.org/documentation/stable/reference/classes/digraph.html

        Args:
            chunks: List of CodeChunk with chunk_id, calls, relationships populated from AST
        """
        if self.storage is None:
            self._logger.warning(
                "Graph storage not initialized, cannot build from chunks"
            )
            return

        # Clear existing graph for fresh build
        self.storage.clear()

        processed_count = 0
        for chunk in chunks:
            if not chunk.chunk_id:
                continue

            try:
                # Add node (NetworkX: G.add_node)
                self.storage.add_node(
                    chunk_id=chunk.chunk_id,
                    name=chunk.name or "unknown",
                    chunk_type=chunk.chunk_type,
                    file_path=chunk.file_path,
                    language=chunk.language,
                )

                # Add call edges (NetworkX: G.add_edge)
                for call in chunk.calls or []:
                    # Handle both CallEdge objects and dicts
                    if hasattr(call, "callee_name"):
                        callee_name = call.callee_name
                        line_number = call.line_number
                        is_method_call = call.is_method_call
                    else:
                        callee_name = call.get("callee_name", "unknown")
                        line_number = call.get("line_number", 0)
                        is_method_call = call.get("is_method_call", False)

                    self.storage.add_call_edge(
                        caller_id=chunk.chunk_id,
                        callee_name=callee_name,
                        line_number=line_number,
                        is_method_call=is_method_call,
                    )

                # Add relationship edges
                for rel in chunk.relationships or []:
                    try:
                        # Import RelationshipEdge for type handling
                        from graph.relationship_types import (
                            RelationshipEdge,
                            RelationshipType,
                        )

                        # Handle both RelationshipEdge objects and dicts
                        if isinstance(rel, RelationshipEdge):
                            self.storage.add_relationship_edge(rel)
                        elif isinstance(rel, dict):
                            edge = RelationshipEdge(
                                source_id=rel.get("source_id", chunk.chunk_id),
                                target_name=rel.get("target_name", "unknown"),
                                relationship_type=RelationshipType(
                                    rel.get("relationship_type", "calls")
                                ),
                                line_number=rel.get("line_number", 0),
                                confidence=rel.get("confidence", 1.0),
                                metadata=rel.get("metadata", {}),
                            )
                            self.storage.add_relationship_edge(edge)
                    except Exception as e:
                        self._logger.debug(f"Failed to add relationship edge: {e}")

                processed_count += 1

            except Exception as e:
                self._logger.warning(
                    f"Failed to add chunk {chunk.chunk_id} to graph: {e}"
                )

        self._logger.info(
            f"Built graph from {processed_count} chunks: {len(self.storage)} nodes"
        )

    def save(self) -> None:
        """Save call graph to disk."""
        # Check if graph storage exists and has nodes
        graph_status = "not None" if self.storage is not None else "None"
        graph_nodes = len(self.storage) if self.storage else 0
        self._logger.info(
            f"[SAVE] Graph storage check: storage={graph_status}, nodes={graph_nodes}"
        )

        if self.storage is not None and len(self.storage) > 0:
            try:
                self._logger.info(
                    f"[SAVE] Saving call graph with {len(self.storage)} nodes to {self.storage.graph_path}"
                )
                self.storage.save()
                self._logger.info("[SAVE] Successfully saved call graph")
            except Exception as e:
                self._logger.warning(f"[SAVE] Failed to save call graph: {e}")
        else:
            skip_reason = "None" if self.storage is None else "empty (0 nodes)"
            self._logger.info(f"[SAVE] Skipping graph save: storage is {skip_reason}")

    def clear(self) -> None:
        """Clear call graph."""
        if self.storage is not None:
            try:
                self.storage.clear()
                self._logger.info("Call graph cleared")
            except Exception as e:
                self._logger.warning(f"Failed to clear call graph: {e}")

    @property
    def is_available(self) -> bool:
        """Check if graph storage is available and initialized."""
        return self.storage is not None

    @property
    def node_count(self) -> int:
        """Get number of nodes in graph."""
        return len(self.storage) if self.storage else 0

    def __len__(self) -> int:
        """Return node count for len() support."""
        return self.node_count
