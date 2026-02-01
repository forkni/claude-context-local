"""Graph integration layer for call graph storage operations."""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional


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
    "merged",  # Community-merged chunks from Louvain detection
    "split_block",  # Large node split blocks (AST block splitting)
)


class GraphIntegration:
    """Wrapper for call graph storage operations.

    This class isolates all graph-related logic from CodeIndexManager,
    providing a clean interface for graph operations.
    """

    def __init__(self, project_id: Optional[str], storage_dir: Path) -> None:
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

    def add_chunk(self, chunk_id: str, metadata: dict[str, Any]) -> None:
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

                    except (ValueError, KeyError, TypeError) as e:
                        self._logger.warning(
                            f"Failed to add relationship edge from {chunk_id}: {e}"
                        )

        except (KeyError, TypeError) as e:
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

        Two-pass approach for symbol resolution:
        - Pass 1: Add all chunk nodes + build name→chunk_id mapping
        - Pass 2: Add edges with call target resolution (creates direct chunk-chunk edges)

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

        # === PASS 1: Add all chunk nodes + build symbol resolution map ===
        name_to_chunk_ids: dict[str, list[str]] = defaultdict(list)
        processed_count = 0

        for chunk in chunks:
            if not chunk.chunk_id:
                continue
            # Skip synthetic module summaries — no parseable code, would be isolated nodes
            if chunk.chunk_type == "module":
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

                # Build name→chunk_id mapping for call resolution
                if chunk.name and chunk.name != "unknown":
                    name_to_chunk_ids[chunk.name].append(chunk.chunk_id)

                    # Also index by bare name for methods (ClassName.method → method)
                    if "." in chunk.name:
                        bare_name = chunk.name.split(".")[-1]
                        name_to_chunk_ids[bare_name].append(chunk.chunk_id)

                    # Index qualified name (ClassName.method) for self.method() resolution
                    # Fixes intra-class method calls by indexing "ClassName.method"
                    if chunk.parent_name and chunk.name:
                        qualified_name = f"{chunk.parent_name}.{chunk.name}"
                        name_to_chunk_ids[qualified_name].append(chunk.chunk_id)

                processed_count += 1

            except (AttributeError, KeyError, TypeError) as e:
                self._logger.warning(
                    f"Failed to add chunk {chunk.chunk_id} to graph: {e}"
                )

        self._logger.info(
            f"Built graph nodes: {processed_count} chunks, {len(name_to_chunk_ids)} unique symbol names"
        )

        # === PASS 2: Add edges with call target resolution ===
        resolved_edges = 0
        phantom_edges = 0

        for chunk in chunks:
            if not chunk.chunk_id:
                continue

            try:
                # Add call edges with resolution (NetworkX: G.add_edge)
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

                    # Try to resolve callee_name to a chunk_id
                    resolved_chunk_id = self._resolve_call_target(
                        callee_name, name_to_chunk_ids, caller_file=chunk.file_path
                    )

                    if resolved_chunk_id:
                        # Direct chunk-to-chunk edge!
                        self.storage.add_call_edge(
                            caller_id=chunk.chunk_id,
                            callee_name=resolved_chunk_id,  # Use resolved chunk_id
                            line_number=line_number,
                            is_method_call=is_method_call,
                            is_resolved=True,
                        )
                        resolved_edges += 1
                    else:
                        # Fallback to phantom node (existing behavior)
                        self.storage.add_call_edge(
                            caller_id=chunk.chunk_id,
                            callee_name=callee_name,  # Use bare symbol name
                            line_number=line_number,
                            is_method_call=is_method_call,
                            is_resolved=False,
                        )
                        phantom_edges += 1

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
                    except (ValueError, KeyError, TypeError) as e:
                        self._logger.debug(f"Failed to add relationship edge: {e}")

            except Exception as e:
                self._logger.warning(
                    f"Failed to add edges for chunk {chunk.chunk_id}: {e}"
                )

        self._logger.info(
            f"Built graph from {processed_count} chunks: {len(self.storage)} nodes, "
            f"{resolved_edges} direct edges, {phantom_edges} phantom edges"
        )

    def _resolve_call_target(
        self,
        callee_name: str,
        name_to_chunk_ids: dict[str, list[str]],
        caller_file: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve a call target name to its chunk_id.

        Conservative approach: Only resolve if exactly ONE match exists.
        Ambiguous matches (multiple functions with same name) create phantom nodes.

        Args:
            callee_name: Symbol name from the call (e.g., "foo", "ClassName.method")
            name_to_chunk_ids: Mapping from symbol names to chunk_ids
            caller_file: Optional file path of caller for disambiguation

        Returns:
            chunk_id if exactly one match, None otherwise (creates phantom node)
        """
        # Skip builtins (len, print, etc.) -- they never resolve to project code
        import builtins

        if hasattr(builtins, callee_name):
            return None  # Create phantom node (will be filtered in traversals)

        # Check if base name (after last dot) is a common method builtin
        base_name = callee_name.split(".")[-1] if "." in callee_name else callee_name
        if base_name in {
            "append",
            "extend",
            "get",
            "items",
            "keys",
            "values",
            "split",
            "join",
            "strip",
            "replace",
            "format",
            "lower",
            "upper",
        }:
            return None

        candidates = name_to_chunk_ids.get(callee_name, [])

        if len(candidates) == 1:
            return candidates[0]

        # Context-aware disambiguation: prefer same-file match for ambiguous calls
        if len(candidates) > 1 and caller_file:
            # Try same-file preference - overwhelmingly the intended target
            same_file = [c for c in candidates if caller_file in c]
            if len(same_file) == 1:
                return same_file[0]

            # Split block disambiguation: when all candidates are split_blocks
            # of the same function (same file, same name), resolve to the first
            # block (lowest start line = function entry point). This fixes graph
            # isolation for large split functions.
            if len(candidates) > 1:
                split_blocks = [c for c in candidates if ":split_block:" in c]
                if len(split_blocks) == len(candidates):
                    # All candidates are split_blocks - pick the entry block
                    def _start_line(chunk_id: str) -> int:
                        parts = chunk_id.split(":")
                        if len(parts) >= 2:
                            line_range = parts[1]  # e.g., "793-860"
                            try:
                                return int(line_range.split("-")[0])
                            except (ValueError, IndexError):
                                pass
                        return float("inf")

                    split_blocks.sort(key=_start_line)
                    return split_blocks[0]

        # No match or still ambiguous - create phantom node
        return None

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
            except (OSError, RuntimeError) as e:
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
            except (RuntimeError, AttributeError) as e:
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
