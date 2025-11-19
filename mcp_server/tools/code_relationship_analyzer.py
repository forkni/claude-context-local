"""Impact Analysis Tool for MCP Server.

Provides dedicated impact analysis functionality that shows what code would be
affected by changes to a given symbol.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)

# Builtin types that should not be searched for in uses_type resolution
# These are Python primitives, stdlib types, and typing module types
BUILTIN_TYPES = frozenset({
    # Python primitives
    "str", "int", "bool", "float", "bytes", "complex",
    # Collection types
    "list", "dict", "tuple", "set", "frozenset",
    # Special types
    "None", "type", "object", "slice", "range",
    # Typing module common types
    "Any", "Union", "Optional", "List", "Dict", "Tuple", "Set", "FrozenSet",
    "Type", "Callable", "Iterator", "Iterable", "Generator", "Sequence",
    "Mapping", "MutableMapping", "MutableSequence", "MutableSet",
    "Awaitable", "Coroutine", "AsyncIterator", "AsyncIterable", "AsyncGenerator",
    # Generic type vars
    "T", "K", "V", "KT", "VT",
})


@dataclass
class ImpactReport:
    """Structured impact analysis report."""

    symbol: Dict[str, Any]  # The symbol being analyzed
    chunk_id: str
    direct_callers: List[Dict[str, Any]]  # Functions that directly call this
    indirect_callers: List[
        Dict[str, Any]
    ]  # Functions that call the callers (multi-hop)
    similar_code: List[Dict[str, Any]]  # Semantically similar implementations
    total_impacted: int  # Total number of impacted symbols
    unique_files: Set[str]  # Set of unique files affected
    dependency_graph: Dict[str, List[str]]  # Graph representation

    # Phase 3: Relationship fields
    parent_classes: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Classes this inherits from
    child_classes: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Classes that inherit from this
    uses_types: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Types used in annotations
    used_as_type_in: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Where this is used as a type
    imports: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Modules/symbols imported
    imported_by: List[Dict[str, Any]] = field(
        default_factory=list
    )  # Files that import this
    stale_chunk_count: int = 0  # Count of chunk_ids not found in current index

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "symbol": self.symbol,
            "chunk_id": self.chunk_id,
            "direct_callers": self.direct_callers,
            "indirect_callers": self.indirect_callers,
            "similar_code": self.similar_code,
            "total_impacted": self.total_impacted,
            "file_count": len(self.unique_files),
            "affected_files": sorted(self.unique_files),
            "dependency_graph": self.dependency_graph,
            # Phase 3: Relationship fields
            "parent_classes": self.parent_classes,
            "child_classes": self.child_classes,
            "uses_types": self.uses_types,
            "used_as_type_in": self.used_as_type_in,
            "imports": self.imports,
            "imported_by": self.imported_by,
            "stale_chunk_count": self.stale_chunk_count,
        }


class CodeRelationshipAnalyzer:
    """Analyzes the impact radius of code changes."""

    def __init__(self, searcher):
        """
        Initialize impact analyzer.

        Args:
            searcher: IntelligentSearcher or HybridSearcher instance
        """
        self.searcher = searcher

        # Access graph_storage through the correct path:
        # - HybridSearcher: graph is on searcher.dense_index.graph_storage
        # - IntelligentSearcher: graph is on searcher.graph_storage (if it exists)
        self.graph = None
        if hasattr(searcher, "dense_index") and hasattr(
            searcher.dense_index, "graph_storage"
        ):
            self.graph = searcher.dense_index.graph_storage
            logger.debug(
                f"[INIT] Graph loaded from HybridSearcher.dense_index: {self.graph.get_stats()}"
            )
        elif hasattr(searcher, "graph_storage"):
            self.graph = searcher.graph_storage
            logger.debug(
                f"[INIT] Graph loaded from searcher.graph_storage: {self.graph.get_stats()}"
            )
        else:
            logger.warning(
                "[INIT] No graph_storage found on searcher - relationship queries will be empty"
            )

    def analyze_impact(
        self, chunk_id: str = None, symbol_name: str = None, max_depth: int = 3
    ) -> ImpactReport:
        """
        Analyze the impact radius of changes to a symbol.

        Args:
            chunk_id: Direct chunk ID lookup (preferred for unambiguous analysis)
            symbol_name: Symbol name (requires search, may be ambiguous)
            max_depth: Maximum depth for dependency traversal (default: 3)

        Returns:
            ImpactReport with structured impact data

        Raises:
            ValueError: If neither chunk_id nor symbol_name provided
        """
        if not chunk_id and not symbol_name:
            raise ValueError("Must provide either chunk_id or symbol_name")

        # Step 1: Get the target symbol
        if chunk_id:
            # Direct lookup - returns reranker.SearchResult
            target_result = self.searcher.get_by_chunk_id(chunk_id)
            if not target_result:
                raise ValueError(f"Chunk not found: {chunk_id}")
            target_id = chunk_id
        else:
            # Search by name - returns reranker.SearchResult
            # Search with more results to find best match by type preference
            results = self.searcher.search(symbol_name, k=10)
            if not results:
                raise ValueError(f"Symbol not found: {symbol_name}")

            # Preference ranking: class > type_definition > interface > function > method
            # This ensures "HybridSearcher" finds the class, not a method with same name
            type_priority = {
                "class": 0,
                "type_definition": 1,
                "interface": 2,
                "struct": 3,
                "enum": 4,
                "trait": 5,
                "function": 6,
                "decorated_definition": 7,
                "method": 8,
            }

            # Filter to results with matching name
            matching_results = []
            for r in results:
                r_name = r.chunk_id.split(":")[-1] if hasattr(r, "chunk_id") else ""
                if r_name == symbol_name:
                    matching_results.append(r)

            # If we have exact name matches, use them; otherwise use all results
            candidates = matching_results if matching_results else results

            # Sort by type priority (prefer classes over methods)
            # ALSO deprioritize test files to prefer production code
            def get_priority(result):
                if hasattr(result, "metadata"):
                    chunk_type = result.metadata.get("chunk_type", "unknown")
                    file_path = result.metadata.get("file", result.metadata.get("file_path", ""))
                else:
                    chunk_type = getattr(result, "chunk_type", "unknown")
                    file_path = getattr(result, "file_path", getattr(result, "relative_path", ""))

                base_priority = type_priority.get(chunk_type, 99)

                # Deprioritize test files (add 100 to base priority)
                # Check for common test directory patterns
                file_path_normalized = file_path.replace("\\", "/").lower()
                if "/tests/" in file_path_normalized or "/test_" in file_path_normalized or file_path_normalized.startswith("tests/"):
                    base_priority += 100

                return base_priority

            candidates.sort(key=get_priority)
            target_result = candidates[0]
            # Both SearchResult types now use chunk_id
            target_id = target_result.chunk_id

            logger.debug(
                f"[ANALYZE_IMPACT] symbol_name='{symbol_name}' resolved to chunk_id='{target_id}' "
                f"(selected from {len(candidates)} candidates)"
            )

        # Extract symbol info (handle both reranker.SearchResult and searcher.SearchResult)
        if hasattr(target_result, "metadata"):
            # reranker.SearchResult (from HybridSearcher)
            symbol_info = {
                "chunk_id": target_id,
                "file": target_result.metadata.get(
                    "file", target_result.metadata.get("file_path", "")
                ),
                "lines": f"{target_result.metadata.get('start_line', 0)}-{target_result.metadata.get('end_line', 0)}",
                "kind": target_result.metadata.get("chunk_type", "unknown"),
                "name": symbol_name or target_id.split(":")[-1],
            }
        else:
            # searcher.SearchResult (from IntelligentSearcher)
            symbol_info = {
                "chunk_id": target_id,
                "file": getattr(
                    target_result,
                    "file_path",
                    getattr(target_result, "relative_path", ""),
                ),
                "lines": f"{getattr(target_result, 'start_line', 0)}-{getattr(target_result, 'end_line', 0)}",
                "kind": getattr(target_result, "chunk_type", "unknown"),
                "name": symbol_name or target_id.split(":")[-1],
            }

        # Step 2: Find direct callers using graph
        direct_callers = []
        stale_caller_count = 0  # Track unresolved chunk_ids
        if self.graph:
            try:
                # Extract symbol name from chunk_id for name-based lookup
                # Graph stores edges as: caller_chunk_id → callee_name (not callee_chunk_id)
                # So we need to query by both the full chunk_id and the symbol name
                symbol_name_for_callers = (
                    target_id.split(":")[-1] if ":" in target_id else target_id
                )

                # Get callers using both chunk_id AND symbol name
                callers_by_id = self.graph.get_callers(target_id)
                callers_by_name = (
                    self.graph.get_callers(symbol_name_for_callers)
                    if symbol_name_for_callers != target_id
                    else []
                )

                # Combine and deduplicate callers
                all_callers = list(set(callers_by_id + callers_by_name))

                logger.debug(
                    f"[FIND_CONNECTIONS] Direct callers: by_id={len(callers_by_id)}, "
                    f"by_name={len(callers_by_name)}, combined={len(all_callers)}"
                )

                for caller_id in all_callers:
                    # Get caller details
                    caller_result = self.searcher.get_by_chunk_id(caller_id)
                    if caller_result:
                        direct_callers.append(
                            self._result_to_dict(caller_result, caller_id)
                        )
                    else:
                        stale_caller_count += 1

                # Log summary if any stale IDs found
                if stale_caller_count > 0:
                    logger.info(
                        f"[FIND_CONNECTIONS] {stale_caller_count} of {len(all_callers)} caller chunk_ids "
                        f"not found in index (stale from previous indexing)"
                    )
            except Exception as e:
                logger.warning(f"Failed to get callers from graph: {e}")

        # Step 3: Find indirect callers (multi-hop)
        indirect_callers = []
        stale_indirect_count = 0  # Track stale chunk_ids in multi-hop
        visited = {target_id}

        if self.graph and direct_callers:
            # Traverse up the call graph
            for depth in range(1, max_depth):
                current_level = []
                for caller_dict in (
                    direct_callers
                    if depth == 1
                    else indirect_callers[-len(direct_callers) :]
                ):
                    caller_id = caller_dict.get("chunk_id")
                    if caller_id in visited:
                        continue
                    visited.add(caller_id)

                    try:
                        # Extract symbol name for name-based lookup (same fix as Step 2)
                        caller_symbol = (
                            caller_id.split(":")[-1] if ":" in caller_id else caller_id
                        )

                        # Get callers using both chunk_id AND symbol name
                        callers_by_id = self.graph.get_callers(caller_id)
                        callers_by_name = (
                            self.graph.get_callers(caller_symbol)
                            if caller_symbol != caller_id
                            else []
                        )
                        next_callers = list(set(callers_by_id + callers_by_name))

                        for next_id in next_callers:
                            if next_id not in visited:
                                result = self.searcher.get_by_chunk_id(next_id)
                                if result:
                                    current_level.append(
                                        self._result_to_dict(result, next_id)
                                    )
                                else:
                                    stale_indirect_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to get callers for {caller_id}: {e}")

                if not current_level:
                    break
                indirect_callers.extend(current_level)

        # Step 4: Find similar code (semantic)
        # Note: find_similar_to_chunk() returns searcher.SearchResult (different type!)
        similar_code = []
        try:
            similar_results = self.searcher.find_similar_to_chunk(target_id, k=5)
            for result in similar_results:
                # Both SearchResult types now use chunk_id
                result_id = result.chunk_id
                if result_id != target_id:
                    # Convert searcher.SearchResult to dict (has direct attributes, not metadata)
                    similar_dict = {
                        "chunk_id": result_id,
                        "file": result.file_path or result.relative_path,
                        "lines": f"{result.start_line}-{result.end_line}",
                        "kind": result.chunk_type,
                        "score": round(result.similarity_score, 2),
                    }
                    similar_code.append(similar_dict)
        except Exception as e:
            logger.warning(f"Failed to find similar code: {e}")

        # Step 5: Extract graph relationships (inheritance, type usage, imports)
        graph_relationships = self._extract_relationships(target_id)

        # Step 6: Build dependency graph
        dependency_graph = {target_id: [c["chunk_id"] for c in direct_callers]}
        for caller in direct_callers:
            caller_id = caller["chunk_id"]
            # Find who calls this caller
            caller_callers = [
                c["chunk_id"]
                for c in indirect_callers
                if self._is_caller_of(c, caller_id)
            ]
            if caller_callers:
                dependency_graph[caller_id] = caller_callers

        # Step 7: Calculate unique files
        unique_files = {symbol_info["file"]}
        for item in direct_callers + indirect_callers + similar_code:
            unique_files.add(item.get("file", ""))

        # Build report
        total_impacted = len(direct_callers) + len(indirect_callers) + len(similar_code)

        return ImpactReport(
            symbol=symbol_info,
            chunk_id=target_id,
            direct_callers=direct_callers,
            indirect_callers=indirect_callers,
            similar_code=similar_code,
            total_impacted=total_impacted,
            unique_files=unique_files,
            dependency_graph=dependency_graph,
            # Populate graph-based relationship fields
            parent_classes=graph_relationships.get("parent_classes", []),
            child_classes=graph_relationships.get("child_classes", []),
            uses_types=graph_relationships.get("uses_types", []),
            used_as_type_in=graph_relationships.get("used_as_type_in", []),
            imports=graph_relationships.get("imports", []),
            imported_by=graph_relationships.get("imported_by", []),
            stale_chunk_count=stale_caller_count + stale_indirect_count,
        )

    def _result_to_dict(self, result, chunk_id: str) -> Dict[str, Any]:
        """Convert search result to dict format."""
        if isinstance(result, dict):
            result["chunk_id"] = chunk_id
            return result

        # Handle both reranker.SearchResult and searcher.SearchResult
        if hasattr(result, "metadata"):
            # reranker.SearchResult (from HybridSearcher)
            return {
                "chunk_id": chunk_id,
                "file": result.metadata.get(
                    "file", result.metadata.get("file_path", "")
                ),
                "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
                "kind": result.metadata.get("chunk_type", "unknown"),
                "score": result.score,
            }
        else:
            # searcher.SearchResult (from IntelligentSearcher)
            return {
                "chunk_id": chunk_id,
                "file": getattr(
                    result, "file_path", getattr(result, "relative_path", "")
                ),
                "lines": f"{getattr(result, 'start_line', 0)}-{getattr(result, 'end_line', 0)}",
                "kind": getattr(result, "chunk_type", "unknown"),
                "score": getattr(result, "similarity_score", 0.0),
            }

    def _is_caller_of(self, potential_caller: Dict, callee_id: str) -> bool:
        """Check if potential_caller calls callee_id."""
        if not self.graph:
            return False

        try:
            caller_id = potential_caller.get("chunk_id")
            callees = self.graph.get_callees(caller_id)
            # Graph stores callees as symbol names, not full chunk_ids
            # Extract symbol name from callee_id for comparison
            callee_symbol = callee_id.split(":")[-1] if ":" in callee_id else callee_id
            # Check both full chunk_id and symbol name
            return callee_id in callees or callee_symbol in callees
        except Exception:
            return False

    def _extract_result_info(self, result, chunk_id: str) -> Dict[str, Any]:
        """
        Extract file/line/kind info from search result.

        Handles both reranker.SearchResult and searcher.SearchResult.
        """
        if hasattr(result, "metadata"):
            # reranker.SearchResult (from HybridSearcher)
            return {
                "chunk_id": chunk_id,
                "file": result.metadata.get(
                    "file", result.metadata.get("file_path", "")
                ),
                "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
                "kind": result.metadata.get("chunk_type", "unknown"),
            }
        else:
            # searcher.SearchResult (from IntelligentSearcher)
            return {
                "chunk_id": chunk_id,
                "file": getattr(
                    result, "file_path", getattr(result, "relative_path", "")
                ),
                "lines": f"{getattr(result, 'start_line', 0)}-{getattr(result, 'end_line', 0)}",
                "kind": getattr(result, "chunk_type", "unknown"),
            }

    def _extract_relationships(self, chunk_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract graph-based relationships (inheritance, type usage, imports) for a chunk.

        Args:
            chunk_id: Chunk ID to analyze

        Returns:
            Dict mapping relationship field names to lists of relationship dicts
        """
        from graph.relationship_types import get_relationship_field_mapping

        if not self.graph:
            return {}

        # Normalize chunk_id path separators to forward slashes for consistent queries
        # Fixes Issue 2: Query path normalization mismatch (defense-in-depth)
        # Note: graph_storage.py methods also normalize, but doing it here ensures
        # symbol_name extraction works correctly
        # Un-double-escape first (MCP JSON transport), then normalize to forward slashes
        chunk_id = chunk_id.replace("\\\\", "\\").replace("\\", "/")

        # Get relationship field mapping
        field_mapping = get_relationship_field_mapping()

        # Initialize result dict with all possible fields
        result = {}
        for forward_field, reverse_field in field_mapping.values():
            if forward_field:
                result[forward_field] = []
            if reverse_field:
                result[reverse_field] = []

        try:
            # Debug logging for Phase 3 relationship extraction
            logger.debug(f"[EXTRACT_REL] _extract_relationships({chunk_id})")
            logger.debug(f"  [EXTRACT_REL] Graph loaded: {self.graph is not None}")
            if self.graph:
                logger.debug(f"  [EXTRACT_REL] Graph stats: {self.graph.get_stats()}")

            # Get all outgoing edges (this chunk is source)
            callees = self.graph.get_callees(chunk_id)
            logger.debug(
                f"  [EXTRACT_REL] Outgoing callees: {len(callees)} → {callees[:3] if callees else '[]'}..."
            )
            for target in callees:
                try:
                    edge_data = self.graph.get_edge_data(chunk_id, target)
                    if edge_data:
                        # Get relationship type
                        rel_type = edge_data.get("relationship_type") or edge_data.get(
                            "type", "calls"
                        )

                        # Skip legacy 'calls' relationships (handled separately)
                        if rel_type == "calls":
                            continue

                        # Get forward field for this relationship type
                        forward_field, _ = field_mapping.get(rel_type, (None, None))
                        if forward_field and forward_field in result:
                            # For uses_type and imports, target is a type/module name, not a chunk_id
                            # Try to resolve it to a chunk_id by searching
                            if rel_type in ["uses_type", "imports"]:
                                # Skip builtin/primitive types - they won't be in the index
                                if rel_type == "uses_type" and target in BUILTIN_TYPES:
                                    result[forward_field].append({
                                        "chunk_id": "",
                                        "target_name": target,
                                        "relationship_type": rel_type,
                                        "file": "",
                                        "lines": "",
                                        "kind": "builtin",
                                        "line": edge_data.get("line_number") or edge_data.get("line", 0),
                                        "confidence": edge_data.get("confidence", 1.0),
                                        "metadata": edge_data.get("metadata", {}),
                                        "note": "Python builtin type (not searchable)",
                                    })
                                    continue

                                # Try to find a chunk matching this type/module name
                                target_chunk = None
                                try:
                                    # Search for classes/types with this name
                                    search_results = self.searcher.search(target, k=5)
                                    # Find best match (prefer class definitions)
                                    for sr in search_results:
                                        sr_name = (
                                            sr.chunk_id.split(":")[-1]
                                            if hasattr(sr, "chunk_id")
                                            else ""
                                        )
                                        sr_type = getattr(sr, "chunk_type", "")
                                        if sr_name == target and sr_type in [
                                            "class",
                                            "type_definition",
                                            "interface",
                                        ]:
                                            target_chunk = sr
                                            break
                                    # Fall back to any name match
                                    if not target_chunk:
                                        for sr in search_results:
                                            sr_name = (
                                                sr.chunk_id.split(":")[-1]
                                                if hasattr(sr, "chunk_id")
                                                else ""
                                            )
                                            if sr_name == target:
                                                target_chunk = sr
                                                break
                                except Exception as e:
                                    logger.debug(
                                        f"Failed to resolve type {target}: {e}"
                                    )

                                if target_chunk:
                                    # Resolved to a chunk
                                    result[forward_field].append(
                                        {
                                            "chunk_id": target_chunk.chunk_id,
                                            "target_name": target,
                                            "relationship_type": rel_type,
                                            "file": getattr(
                                                target_chunk, "file_path", ""
                                            )
                                            or getattr(
                                                target_chunk, "relative_path", ""
                                            ),
                                            "lines": f"{getattr(target_chunk, 'start_line', 0)}-{getattr(target_chunk, 'end_line', 0)}",
                                            "kind": getattr(
                                                target_chunk, "chunk_type", "unknown"
                                            ),
                                            "line": edge_data.get("line_number")
                                            or edge_data.get("line", 0),
                                            "confidence": edge_data.get(
                                                "confidence", 1.0
                                            ),
                                            "metadata": edge_data.get("metadata", {}),
                                        }
                                    )
                                else:
                                    # Couldn't resolve - external or built-in type
                                    result[forward_field].append(
                                        {
                                            "chunk_id": "",
                                            "target_name": target,
                                            "relationship_type": rel_type,
                                            "file": "",
                                            "lines": "",
                                            "kind": "external",
                                            "line": edge_data.get("line_number")
                                            or edge_data.get("line", 0),
                                            "confidence": edge_data.get(
                                                "confidence", 1.0
                                            ),
                                            "metadata": edge_data.get("metadata", {}),
                                            "note": "Type not found in index (external or built-in)",
                                        }
                                    )
                            else:
                                # For inherits, target is ALSO a name (not chunk_id)
                                # Try to look it up, but fall back to name-only if not found
                                target_result = self.searcher.get_by_chunk_id(target)
                                if target_result:
                                    # Found as chunk_id (rare case, backward compatibility)
                                    info = self._extract_result_info(
                                        target_result, target
                                    )
                                    info.update(
                                        {
                                            "target_name": edge_data.get(
                                                "target_name", target.split(":")[-1]
                                            ),
                                            "relationship_type": rel_type,
                                            "line": edge_data.get("line_number")
                                            or edge_data.get("line", 0),
                                            "confidence": edge_data.get(
                                                "confidence", 1.0
                                            ),
                                        }
                                    )
                                    result[forward_field].append(info)
                                else:
                                    # Target is a name (expected case for inherits)
                                    # Store with graceful degradation
                                    result[forward_field].append(
                                        {
                                            "target_name": target,
                                            "relationship_type": rel_type,
                                            "line": edge_data.get("line_number")
                                            or edge_data.get("line", 0),
                                            "confidence": edge_data.get(
                                                "confidence", 1.0
                                            ),
                                            "metadata": edge_data.get("metadata", {}),
                                            "note": "Type resolution not implemented - showing name only",
                                        }
                                    )
                except Exception as e:
                    logger.debug(
                        f"Failed to process outgoing edge {chunk_id} -> {target}: {e}"
                    )

            # Get all incoming edges (this chunk is target)
            # CRITICAL: Graph relationships store targets as SYMBOL NAMES, not chunk_ids
            # Example: Edge is "service.py:10:function:process → 'User'" (name, not chunk_id)
            # If our chunk_id is "models.py:50:class:User", we need to search for "User"

            # Extract symbol name from chunk_id (last part after final colon)
            symbol_name = chunk_id.split(":")[-1] if ":" in chunk_id else chunk_id
            logger.debug(f"  [EXTRACT_REL] Extracted symbol_name: {symbol_name}")

            # Get callers using BOTH chunk_id (backward compat) and symbol name
            callers_by_id = self.graph.get_callers(chunk_id)
            callers_by_name = (
                self.graph.get_callers(symbol_name) if symbol_name != chunk_id else []
            )

            # Debug logging for callers
            logger.debug(
                f"  [EXTRACT_REL] callers_by_id ({len(callers_by_id)}): {callers_by_id[:3] if callers_by_id else '[]'}..."
            )
            logger.debug(
                f"  [EXTRACT_REL] callers_by_name ({len(callers_by_name)}): {callers_by_name[:3] if callers_by_name else '[]'}..."
            )

            # Combine and deduplicate callers
            all_callers = list(set(callers_by_id + callers_by_name))
            logger.debug(
                f"  [EXTRACT_REL] all_callers combined ({len(all_callers)}): {all_callers[:3] if all_callers else '[]'}..."
            )

            for source in all_callers:
                try:
                    # Try to get edge data using both chunk_id and symbol_name as target
                    edge_data = self.graph.get_edge_data(source, chunk_id)
                    if not edge_data and symbol_name != chunk_id:
                        edge_data = self.graph.get_edge_data(source, symbol_name)

                    if edge_data:
                        # Get relationship type with validation
                        rel_type = edge_data.get("relationship_type") or edge_data.get(
                            "type", "calls"
                        )

                        # Skip legacy 'calls' relationships (handled separately)
                        if rel_type == "calls":
                            continue

                        # Get reverse field for this relationship type
                        _, reverse_field = field_mapping.get(rel_type, (None, None))
                        if reverse_field and reverse_field in result:
                            # Source should always be a valid chunk_id
                            source_result = self.searcher.get_by_chunk_id(source)
                            if source_result:
                                # Full chunk lookup successful
                                info = self._extract_result_info(source_result, source)
                                info.update(
                                    {
                                        "source_name": edge_data.get(
                                            "source_id", source
                                        ).split(":")[-1],
                                        "relationship_type": rel_type,
                                        "line": edge_data.get("line_number")
                                        or edge_data.get("line", 0),
                                        "confidence": edge_data.get("confidence", 1.0),
                                    }
                                )
                                result[reverse_field].append(info)
                            else:
                                # Graceful degradation: source lookup failed
                                # This shouldn't happen for valid graphs, but handle it
                                logger.debug(
                                    f"Could not find chunk for source {source} in reverse relationship"
                                )
                                result[reverse_field].append(
                                    {
                                        "source_chunk_id": source,
                                        "relationship_type": rel_type,
                                        "line": edge_data.get("line_number")
                                        or edge_data.get("line", 0),
                                        "confidence": edge_data.get("confidence", 1.0),
                                        "note": "Source chunk not found in index",
                                    }
                                )
                except Exception as e:
                    logger.debug(
                        f"Failed to process incoming edge {source} -> {chunk_id}/{symbol_name}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Failed to extract graph relationships for {chunk_id}: {e}")

        return result
