"""Relationship analysis: finds and enriches code connections for a given chunk.

Business logic lives here; the MCP tool handler is a thin adapter over
RelationshipAnalyzer.analyze_impact().

Graph traversal is fully delegated to GraphQueryEngine — this module never
calls CodeGraphStorage directly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from graph.graph_queries import GraphQueryEngine, RelationshipEntry
from search.exceptions import SearchError
from search.filters import (
    matches_directory_filter,
    normalize_path,
    normalize_path_lower,
    unescape_mcp_path,
)
from search.types import BUILTIN_TYPES, ImpactReport


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class RelationshipAnalyzer:
    """Analyses the impact radius of code changes."""

    def __init__(
        self,
        searcher: Any,
        graph_engine: GraphQueryEngine | None,
    ) -> None:
        self.searcher = searcher
        self.graph_engine = graph_engine

        # O(1) symbol-name → chunk_id cache (optional, for inherits resolution)
        self.symbol_cache = None
        if hasattr(searcher, "dense_index") and hasattr(
            searcher.dense_index, "symbol_cache"
        ):
            self.symbol_cache = searcher.dense_index.symbol_cache
        elif hasattr(searcher, "symbol_cache"):
            self.symbol_cache = searcher.symbol_cache

        if graph_engine is None:
            logger.warning(
                "[INIT] No GraphQueryEngine supplied — relationship queries will be empty"
            )
        else:
            logger.debug(f"[INIT] GraphQueryEngine ready: {graph_engine.get_stats()}")

    @classmethod
    def from_searcher(cls, searcher: Any) -> RelationshipAnalyzer:
        """Convenience constructor: resolve GraphQueryEngine from a HybridSearcher."""
        engine: GraphQueryEngine | None = None
        if hasattr(searcher, "dense_index") and hasattr(
            searcher.dense_index, "graph_storage"
        ):
            engine = GraphQueryEngine(searcher.dense_index.graph_storage)
        elif hasattr(searcher, "graph_storage"):
            engine = GraphQueryEngine(searcher.graph_storage)
        return cls(searcher, engine)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_impact(
        self,
        chunk_id: str | None = None,
        symbol_name: str | None = None,
        max_depth: int = 3,
        exclude_dirs: list[str] | None = None,
        relationship_types: list[str] | None = None,
    ) -> ImpactReport:
        """Analyse the impact radius of changes to a symbol.

        Args:
            chunk_id: Direct chunk ID lookup (preferred).
            symbol_name: Symbol name (requires search, may be ambiguous).
            max_depth: Maximum depth for caller traversal.
            exclude_dirs: Directories to exclude.
            relationship_types: Edge types to include; None = all.

        Returns:
            ImpactReport with structured impact data.

        Raises:
            SearchError: If neither chunk_id nor symbol_name is provided,
                or the target cannot be found.
        """
        if not chunk_id and not symbol_name:
            raise SearchError("Must provide either chunk_id or symbol_name")

        # Un-double-escape MCP JSON transport encoding before graph queries
        if chunk_id:
            chunk_id = unescape_mcp_path(chunk_id)

        # Step 1: resolve target
        target_result, target_id = self._resolve_target(
            chunk_id, symbol_name, exclude_dirs
        )
        symbol_info = self._extract_symbol_info(target_result, target_id, symbol_name)

        # Step 2+3: inbound callers up to max_depth
        stale_count = 0
        exact_d = recovered_d = ambiguous_d = 0
        direct_callers: list[dict[str, Any]] = []
        indirect_callers: list[dict[str, Any]] = []

        if self.graph_engine:
            inbound = self.graph_engine.get_relationships(
                target_id, direction="inbound", max_depth=max_depth
            )
            direct_raw = [e for e in inbound if e.depth == 1]
            indirect_raw = [e for e in inbound if e.depth > 1]

            enriched_direct, stale_d, exact_d, recovered_d, ambiguous_d = (
                self._enrich_callers(direct_raw, exclude_dirs)
            )
            enriched_indirect, stale_i, _ex_i, _rec_i, _amb_i = self._enrich_callers(
                indirect_raw, exclude_dirs
            )
            direct_callers = enriched_direct
            indirect_callers = enriched_indirect
            stale_count = stale_d + stale_i
        else:
            inbound = []

        # Step 4: semantically similar code
        similar_code = self._find_similar(target_id, exclude_dirs)

        # Step 5: graph relationships (inheritance, type usage, imports, …)
        graph_relationships: dict[str, list[dict[str, Any]]] = {}
        direct_callees: list[dict[str, Any]] = []
        exact_ce = recovered_ce = ambiguous_ce = 0
        if self.graph_engine:
            outbound = self.graph_engine.get_relationships(
                target_id, direction="outbound", max_depth=1
            )
            inbound_1hop = [
                e for e in (inbound if self.graph_engine else []) if e.depth == 1
            ]
            graph_relationships = self._build_graph_relationships(
                target_id, inbound_1hop, outbound, exclude_dirs
            )

            # Step 5b: outbound `calls` edges → direct callees (bidirectional).
            # _build_graph_relationships explicitly skips calls edges; pull them here.
            calls_outbound = [e for e in outbound if e.relationship_type == "calls"]
            direct_callees, _stale_ce, exact_ce, recovered_ce, ambiguous_ce = (
                self._enrich_callees(calls_outbound, exclude_dirs)
            )

        # Step 5.5: filter to requested relationship types
        if relationship_types and graph_relationships:
            graph_relationships = self._filter_by_types(
                graph_relationships, relationship_types
            )

        # Step 6: dependency graph
        dependency_graph = self._build_dependency_graph(
            target_id, direct_callers, indirect_callers
        )

        # Step 7: unique files
        unique_files: set[str] = set()
        for item in [symbol_info] + direct_callers + indirect_callers + similar_code:
            path = self._extract_normalized_path(item)
            if path:
                unique_files.add(path)

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
            parent_classes=graph_relationships.get("parent_classes", []),
            child_classes=graph_relationships.get("child_classes", []),
            uses_types=graph_relationships.get("uses_types", []),
            used_as_type_in=graph_relationships.get("used_as_type_in", []),
            imports=graph_relationships.get("imports", []),
            imported_by=graph_relationships.get("imported_by", []),
            decorates=graph_relationships.get("decorates", []),
            decorated_by=graph_relationships.get("decorated_by", []),
            exceptions_raised=graph_relationships.get("exceptions_raised", []),
            exception_handlers=graph_relationships.get("exception_handlers", []),
            exceptions_caught=graph_relationships.get("exceptions_caught", []),
            instantiates=graph_relationships.get("instantiates", []),
            instantiated_by=graph_relationships.get("instantiated_by", []),
            defines_constants=graph_relationships.get("defines_constants", []),
            uses_constants=graph_relationships.get("uses_constants", []),
            defines_enum_members=graph_relationships.get("defines_enum_members", []),
            uses_defaults=graph_relationships.get("uses_defaults", []),
            defines_class_attrs=graph_relationships.get("defines_class_attrs", []),
            class_attr_definitions=graph_relationships.get(
                "class_attr_definitions", []
            ),
            defines_fields=graph_relationships.get("defines_fields", []),
            field_definitions=graph_relationships.get("field_definitions", []),
            uses_context_managers=graph_relationships.get("uses_context_managers", []),
            context_manager_usages=graph_relationships.get(
                "context_manager_usages", []
            ),
            stale_chunk_count=stale_count,
            direct_callers_exact=exact_d if self.graph_engine else 0,
            direct_callers_recovered=recovered_d if self.graph_engine else 0,
            direct_callers_ambiguous=ambiguous_d if self.graph_engine else 0,
            direct_callees=direct_callees,
            direct_callees_exact=exact_ce if self.graph_engine else 0,
            direct_callees_recovered=recovered_ce if self.graph_engine else 0,
            direct_callees_ambiguous=ambiguous_ce if self.graph_engine else 0,
        )

    # ------------------------------------------------------------------
    # Graph relationship building  (consumes RelationshipEntry lists)
    # ------------------------------------------------------------------

    def _build_graph_relationships(
        self,
        chunk_id: str,
        inbound_1hop: list[RelationshipEntry],
        outbound_1hop: list[RelationshipEntry],
        exclude_dirs: list[str] | None,
    ) -> dict[str, list[dict[str, Any]]]:
        """Build the per-relationship-type dicts from pre-traversed entries.

        Outbound entries → forward fields (parent_classes, uses_types, …).
        Inbound entries  → reverse fields (child_classes, used_as_type_in, …).
        'calls' edges are handled separately (direct/indirect callers) and skipped here.
        """
        from chunking.relationships.relationship_types import (
            get_relationship_field_mapping,
        )

        field_mapping = get_relationship_field_mapping()

        result: dict[str, list[dict[str, Any]]] = {}
        for fwd, rev in field_mapping.values():
            if fwd:
                result[fwd] = []
            if rev:
                result[rev] = []

        def _should_include(file_path: str) -> bool:
            if not file_path:
                return True
            return matches_directory_filter(file_path, None, exclude_dirs)

        logger.debug(
            f"[BUILD_REL] chunk={chunk_id} "
            f"outbound={len(outbound_1hop)} inbound={len(inbound_1hop)}"
        )

        for entry in outbound_1hop:
            if entry.relationship_type == "calls":
                continue
            fwd_field, _ = field_mapping.get(entry.relationship_type, (None, None))
            if not fwd_field or fwd_field not in result:
                continue
            enriched = self._enrich_forward(entry, _should_include)
            if enriched is not None:
                result[fwd_field].append(enriched)

        for entry in inbound_1hop:
            if entry.relationship_type == "calls":
                continue
            _, rev_field = field_mapping.get(entry.relationship_type, (None, None))
            if not rev_field or rev_field not in result:
                continue
            enriched = self._enrich_reverse(entry, _should_include)
            if enriched is not None:
                result[rev_field].append(enriched)

        return result

    def _enrich_forward(
        self,
        entry: RelationshipEntry,
        should_include: Any,
    ) -> dict[str, Any] | None:
        """Enrich an outbound RelationshipEntry with metadata from the searcher."""
        rel_type = entry.relationship_type
        target = entry.chunk_id  # symbol name for uses_type/imports; chunk_id otherwise
        edge_data = entry.edge_data
        line = edge_data.get("line_number") or edge_data.get("line", 0)
        confidence = edge_data.get("confidence", 1.0)

        if rel_type in ("uses_type", "imports"):
            if rel_type == "uses_type" and target in BUILTIN_TYPES:
                if not should_include(""):
                    return None
                return {
                    "chunk_id": "",
                    "target_name": target,
                    "relationship_type": rel_type,
                    "file": "",
                    "lines": "",
                    "kind": "builtin",
                    "line": line,
                    "confidence": confidence,
                    "metadata": edge_data.get("metadata", {}),
                    "note": "Python builtin type (not searchable)",
                }

            resolved = self._resolve_type_chunk(target)
            if resolved:
                file_path = getattr(resolved, "file_path", "") or getattr(
                    resolved, "relative_path", ""
                )
                if not should_include(file_path):
                    return None
                return {
                    "chunk_id": resolved.chunk_id,
                    "target_name": target,
                    "relationship_type": rel_type,
                    "file": file_path,
                    "lines": (
                        f"{getattr(resolved, 'start_line', 0)}"
                        f"-{getattr(resolved, 'end_line', 0)}"
                    ),
                    "kind": getattr(resolved, "chunk_type", "unknown"),
                    "line": line,
                    "confidence": confidence,
                    "metadata": edge_data.get("metadata", {}),
                }
            else:
                if not should_include(""):
                    return None
                return {
                    "chunk_id": "",
                    "target_name": target,
                    "relationship_type": rel_type,
                    "file": "",
                    "lines": "",
                    "kind": "external",
                    "line": line,
                    "confidence": confidence,
                    "metadata": edge_data.get("metadata", {}),
                    "note": "Type not found in index (external or built-in)",
                }

        # All other outbound types (inherits, decorates, raises, …)
        result_obj = self.searcher.get_by_chunk_id(target)
        if result_obj:
            info = self._extract_result_info(result_obj, target)
            if not should_include(info.get("file", "")):
                return None
            info.update(
                {
                    "target_name": edge_data.get("target_name", target.split(":")[-1]),
                    "relationship_type": rel_type,
                    "line": line,
                    "confidence": confidence,
                }
            )
            return info

        # Try O(1) symbol cache
        resolved_id = (
            self.symbol_cache.get_by_symbol_name(target) if self.symbol_cache else None
        )
        if resolved_id:
            chunk_info = self._get_chunk_info(resolved_id)
            if not should_include(chunk_info.get("file", "")):
                return None
            return {
                "chunk_id": resolved_id,
                "target_name": target,
                "kind": chunk_info.get("kind", "unknown"),
                "file": chunk_info.get("file"),
                "line": line,
                "confidence": confidence,
                "relationship_type": rel_type,
            }

        if not should_include(""):
            return None
        return {
            "chunk_id": "",
            "target_name": target,
            "relationship_type": rel_type,
            "line": line,
            "confidence": confidence,
            "note": "External or builtin type (not in index)",
            "resolvable": False,
        }

    def _enrich_reverse(
        self,
        entry: RelationshipEntry,
        should_include: Any,
    ) -> dict[str, Any] | None:
        """Enrich an inbound RelationshipEntry with metadata from the searcher."""
        source = entry.chunk_id
        edge_data = entry.edge_data
        line = edge_data.get("line_number") or edge_data.get("line", 0)
        confidence = edge_data.get("confidence", 1.0)

        source_result = self.searcher.get_by_chunk_id(source)
        if source_result:
            info = self._extract_result_info(source_result, source)
            if not should_include(info.get("file", "")):
                return None
            info.update(
                {
                    "source_name": edge_data.get("source_id", source).split(":")[-1],
                    "relationship_type": entry.relationship_type,
                    "line": line,
                    "confidence": confidence,
                }
            )
            return info

        logger.debug(
            f"Could not find chunk for source {source} in reverse relationship"
        )
        if not should_include(""):
            return None
        return {
            "source_chunk_id": "",
            "relationship_type": entry.relationship_type,
            "line": line,
            "confidence": confidence,
            "note": "Source chunk not found in index",
            "resolvable": False,
        }

    def _enrich_callers(
        self,
        entries: list[RelationshipEntry],
        exclude_dirs: list[str] | None,
    ) -> tuple[list[dict[str, Any]], int, int, int, int]:
        """Convert inbound RelationshipEntry objects to enriched caller dicts.

        On exact lookup miss, retries via the Tier 1→3 symbol-resolution cascade
        (_resolve_by_symbol) instead of silently discarding graph-found callers.
        Callers are tagged with ``confidence``:
          - ``"exact"``     — found directly by chunk_id; edge was unambiguous
          - ``"recovered"`` — exact lookup missed (line-range drift / split_block
                              divergence), but re-resolution by symbol succeeded
          - ``"ambiguous"`` — stored as ambiguous at indexing time (Phase 2 edges)

        Returns:
            (callers, stale_count, exact_count, recovered_count, ambiguous_count)
        """
        callers: list[dict[str, Any]] = []
        stale = 0
        exact_count = 0
        recovered_count = 0
        ambiguous_count = 0

        for entry in entries:
            caller_id = entry.chunk_id
            # Edge-level confidence may be stored at indexing time (e.g. "ambiguous")
            edge_confidence: str | None = entry.edge_data.get("confidence")
            resolver_source: str = entry.edge_data.get("source", "ast")
            resolver_confidence: float = entry.edge_data.get("resolver_confidence", 0.5)

            result = self.searcher.get_by_chunk_id(caller_id)
            if result:
                assigned_confidence = edge_confidence if edge_confidence else "exact"
                d = self._result_to_dict(result, caller_id)
                d["confidence"] = assigned_confidence
                d["resolver_source"] = resolver_source
                d["resolver_confidence"] = resolver_confidence
                file_path = (
                    caller_id.split(":")[0] if ":" in caller_id else d.get("file", "")
                )
                if matches_directory_filter(file_path, None, exclude_dirs):
                    callers.append(d)
                    if assigned_confidence == "ambiguous":
                        ambiguous_count += 1
                    else:
                        exact_count += 1
            else:
                # Exact lookup missed — likely line-range drift after incremental
                # reindex, split_block fragmentation, or graph/metadata divergence.
                # Derive the symbol name and retry via Tier 1→3 resolution cascade.
                symbol = caller_id.split(":")[-1] if ":" in caller_id else caller_id
                recovered = self._resolve_by_symbol(symbol, exclude_dirs)
                if recovered is not None:
                    result2, cid2 = recovered
                    d = self._result_to_dict(result2, cid2)
                    d["confidence"] = "recovered"
                    d["original_chunk_id"] = caller_id
                    d["resolver_source"] = resolver_source
                    d["resolver_confidence"] = resolver_confidence
                    file_path = cid2.split(":")[0] if ":" in cid2 else d.get("file", "")
                    if matches_directory_filter(file_path, None, exclude_dirs):
                        callers.append(d)
                        recovered_count += 1
                        logger.debug(
                            f"[ENRICH_CALLERS] Recovered stale '{caller_id}' → '{cid2}'"
                        )
                    else:
                        stale += 1
                else:
                    stale += 1
        if stale:
            logger.info(
                f"[ENRICH_CALLERS] {stale} of {len(entries)} chunk_ids unresolvable"
            )
        return callers, stale, exact_count, recovered_count, ambiguous_count

    def _enrich_callees(
        self,
        entries: list[RelationshipEntry],
        exclude_dirs: list[str] | None,
    ) -> tuple[list[dict[str, Any]], int, int, int, int]:
        """Convert outbound ``calls`` RelationshipEntry objects to enriched callee dicts.

        Mirrors :meth:`_enrich_callers` for the outbound direction.  For each entry the
        ``chunk_id`` field is the *callee* node (a full chunk_id for pyan/libcst-resolved
        edges, or a symbol name for in-house AST edges).

        On exact lookup miss, retries via the Tier 1→3 symbol-resolution cascade
        (:meth:`_resolve_by_symbol`) so that symbol-name callee nodes from the in-house
        extractor are still surfaced when they can be re-resolved.  Callees are tagged
        with ``confidence``:
          - ``"exact"``     — found directly by chunk_id; edge was unambiguous
          - ``"recovered"`` — symbol-name node re-resolved by ``_resolve_by_symbol``
          - ``"ambiguous"`` — stored as ambiguous at indexing time

        Each dict also includes ``resolver_source`` and ``resolver_confidence`` from the
        edge's provenance data (populated when the edge was injected by a named resolver).

        Returns:
            (callees, stale_count, exact_count, recovered_count, ambiguous_count)
        """
        callees: list[dict[str, Any]] = []
        stale = 0
        exact_count = 0
        recovered_count = 0
        ambiguous_count = 0

        for entry in entries:
            callee_id = entry.chunk_id
            edge_confidence: str | None = entry.edge_data.get("confidence")
            resolver_source: str = entry.edge_data.get("source", "ast")
            resolver_confidence: float = entry.edge_data.get("resolver_confidence", 0.5)

            result = self.searcher.get_by_chunk_id(callee_id)
            if result:
                assigned_confidence = edge_confidence if edge_confidence else "exact"
                d = self._result_to_dict(result, callee_id)
                d["confidence"] = assigned_confidence
                d["resolver_source"] = resolver_source
                d["resolver_confidence"] = resolver_confidence
                file_path = (
                    callee_id.split(":")[0] if ":" in callee_id else d.get("file", "")
                )
                if matches_directory_filter(file_path, None, exclude_dirs):
                    callees.append(d)
                    if assigned_confidence == "ambiguous":
                        ambiguous_count += 1
                    else:
                        exact_count += 1
            else:
                # Callee may be stored as a symbol name (in-house AST edges) or a
                # stale/drifted chunk_id.  Derive the symbol and retry via the cascade.
                symbol = callee_id.split(":")[-1] if ":" in callee_id else callee_id
                recovered = self._resolve_by_symbol(symbol, exclude_dirs)
                if recovered is not None:
                    result2, cid2 = recovered
                    d = self._result_to_dict(result2, cid2)
                    d["confidence"] = "recovered"
                    d["original_chunk_id"] = callee_id
                    d["resolver_source"] = resolver_source
                    d["resolver_confidence"] = resolver_confidence
                    file_path = cid2.split(":")[0] if ":" in cid2 else d.get("file", "")
                    if matches_directory_filter(file_path, None, exclude_dirs):
                        callees.append(d)
                        recovered_count += 1
                        logger.debug(
                            f"[ENRICH_CALLEES] Recovered stale '{callee_id}' → '{cid2}'"
                        )
                    else:
                        stale += 1
                else:
                    stale += 1
        if stale:
            logger.info(
                f"[ENRICH_CALLEES] {stale} of {len(entries)} chunk_ids unresolvable"
            )
        return callees, stale, exact_count, recovered_count, ambiguous_count

    # ------------------------------------------------------------------
    # Target resolution
    # ------------------------------------------------------------------

    def _resolve_by_symbol(
        self,
        symbol_name: str,
        exclude_dirs: list[str] | None,
    ) -> tuple[Any, str] | None:
        """Resolve a symbol name to (result, chunk_id) via the Tier 1→3 cascade.

        Unlike _resolve_target, returns ``None`` on failure instead of raising
        ``SearchError``.  Extracted for reuse in _enrich_callers fallback so that
        stale/drifted caller IDs can be re-resolved by symbol rather than dropped.

        Tiers:
          1. O(1) symbol-cache lookup (populated by indexer for all indexed chunks).
          2. Graph exact-name lookup + suffix scan (":<name>" / ".<name>").
          3. Semantic search with name-match + type-priority ranking.
        """
        # Tier 1: O(1) exact symbol-cache lookup
        if self.symbol_cache:
            cid = self.symbol_cache.get_by_symbol_name(symbol_name)
            if cid:
                result = self.searcher.get_by_chunk_id(cid)
                if result:
                    logger.debug(
                        f"[RESOLVE_SYM] '{symbol_name}' → '{cid}' (symbol_cache)"
                    )
                    return result, cid

        # Tier 2: graph exact-name lookup + suffix scan
        graph_storage = None
        if self.graph_engine is not None:
            graph_storage = getattr(self.graph_engine, "storage", None)
        if graph_storage is None and hasattr(self.searcher, "dense_index"):
            graph_storage = getattr(self.searcher.dense_index, "graph_storage", None)

        if graph_storage is not None and hasattr(graph_storage, "get_nodes_by_name"):
            matches = graph_storage.get_nodes_by_name(symbol_name)
            if not matches:
                # Suffix scan: ":<name>" (bare) or ".<name>" (class-qualified)
                matches = [
                    n
                    for n in graph_storage.graph.nodes()
                    if n.endswith(f":{symbol_name}") or n.endswith(f".{symbol_name}")
                ]
            for cid in matches:
                result = self.searcher.get_by_chunk_id(cid)
                if result:
                    logger.debug(
                        f"[RESOLVE_SYM] '{symbol_name}' → '{cid}' (graph_lookup)"
                    )
                    return result, cid

        # Tier 3: semantic search fallback
        filters = {"exclude_dirs": exclude_dirs} if exclude_dirs else None
        try:
            results = self.searcher.search(symbol_name, k=30, filters=filters)
        except Exception as exc:
            logger.debug(f"Tier 3 semantic search failed for '{symbol_name}': {exc}")
            return None
        if not results:
            return None

        def _name_matches(r: Any) -> bool:
            last_seg = r.chunk_id.split(":")[-1] if hasattr(r, "chunk_id") else ""
            return last_seg == symbol_name or last_seg.split(".")[-1] == symbol_name

        matching = [r for r in results if _name_matches(r)]
        candidates = matching if matching else results

        type_priority = {
            "function": 0,
            "decorated_definition": 1,
            "method": 2,
            "class": 3,
            "interface": 4,
            "struct": 5,
            "enum": 6,
            "trait": 7,
            "type_definition": 8,
        }

        def _priority(r: Any) -> int:
            if hasattr(r, "metadata"):
                chunk_type = r.metadata.get("chunk_type", "unknown")
                file_path = r.metadata.get("file", r.metadata.get("file_path", ""))
            else:
                chunk_type = getattr(r, "chunk_type", "unknown")
                file_path = getattr(r, "file_path", getattr(r, "relative_path", ""))
            base = type_priority.get(chunk_type, 99)
            fp = normalize_path_lower(file_path)
            if "/tests/" in fp or "/test_" in fp or fp.startswith("tests/"):
                base += 100
            return base

        candidates = sorted(candidates, key=_priority)
        best = candidates[0]
        cid = best.chunk_id
        logger.debug(
            f"[RESOLVE_SYM] '{symbol_name}' → '{cid}' "
            f"(semantic, {len(candidates)} candidates)"
        )
        return best, cid

    def _resolve_target(
        self,
        chunk_id: str | None,
        symbol_name: str | None,
        exclude_dirs: list[str] | None,
    ) -> tuple[Any, str]:
        if chunk_id:
            result = self.searcher.get_by_chunk_id(chunk_id)
            if result:
                return result, chunk_id
            # Chunk not found — the index was likely incrementally reindexed and the
            # line range embedded in the chunk_id has drifted (e.g. after editing a
            # file, `path:339-342:method:Cls.m` becomes `path:350-353:method:Cls.m`
            # but the old node survives in the call graph). Derive the symbol name
            # from the last colon-segment and fall through to the Tier 1→3 symbol-
            # resolution block below so we can locate the *current* chunk.
            parts = chunk_id.split(":")
            if len(parts) >= 3:
                symbol_name = parts[-1]
                logger.warning(
                    f"[RESOLVE] chunk_id '{chunk_id}' not in index; "
                    f"retrying by symbol '{symbol_name}'"
                )
            else:
                raise SearchError(f"Chunk not found: {chunk_id}")

        # Delegate Tier 1→3 cascade to shared helper; raise on failure.
        resolved = self._resolve_by_symbol(symbol_name, exclude_dirs)
        if resolved is not None:
            return resolved
        raise SearchError(f"Symbol not found: {symbol_name}")

    # ------------------------------------------------------------------
    # Type resolution
    # ------------------------------------------------------------------

    def _resolve_type_chunk(self, target: str) -> Any | None:
        """Resolve a type/module name to a chunk via the searcher."""
        try:
            search_results = self.searcher.search(target, k=4)
            for sr in search_results:
                sr_name = sr.chunk_id.split(":")[-1] if hasattr(sr, "chunk_id") else ""
                sr_type = getattr(sr, "chunk_type", "")
                if sr_name == target and sr_type in (
                    "class",
                    "type_definition",
                    "interface",
                ):
                    return sr
            for sr in search_results:
                sr_name = sr.chunk_id.split(":")[-1] if hasattr(sr, "chunk_id") else ""
                if sr_name == target:
                    return sr
        except Exception as exc:
            logger.debug(f"Failed to resolve type {target}: {exc}")
        return None

    # ------------------------------------------------------------------
    # Similar-code search
    # ------------------------------------------------------------------

    def _find_similar(
        self, target_id: str, exclude_dirs: list[str] | None
    ) -> list[dict[str, Any]]:
        similar: list[dict[str, Any]] = []
        try:
            similar_results = self.searcher.find_similar_to_chunk(
                target_id, k=10, rerank=True
            )
            for result in similar_results:
                result_id = result.chunk_id
                file_path = result.relative_path or result.file_path
                if result_id == target_id:
                    continue
                if not matches_directory_filter(file_path, None, exclude_dirs):
                    continue
                score_value = getattr(result, "score", result.similarity_score)
                try:
                    final_score = (
                        round(float(score_value), 2) if score_value is not None else 0.0
                    )
                except (TypeError, ValueError):
                    final_score = 0.0
                similar.append(
                    {
                        "chunk_id": result_id,
                        "file": normalize_path(file_path) if file_path else "",
                        "lines": f"{result.start_line}-{result.end_line}",
                        "kind": result.chunk_type,
                        "score": final_score,
                    }
                )
        except Exception as exc:
            logger.warning(f"Failed to find similar code: {exc}")
        return similar

    # ------------------------------------------------------------------
    # Post-processing helpers
    # ------------------------------------------------------------------

    def _filter_by_types(
        self,
        graph_relationships: dict[str, list[dict[str, Any]]],
        relationship_types: list[str],
    ) -> dict[str, list[dict[str, Any]]]:
        from chunking.relationships.relationship_types import (
            get_relationship_field_mapping,
        )

        field_mapping = get_relationship_field_mapping()
        allowed: set[str] = set()
        for rel_type in relationship_types:
            fwd, rev = field_mapping.get(rel_type, (None, None))
            if fwd:
                allowed.add(fwd)
            if rev:
                allowed.add(rev)
        return {k: v for k, v in graph_relationships.items() if k in allowed}

    def _build_dependency_graph(
        self,
        target_id: str,
        direct_callers: list[dict[str, Any]],
        indirect_callers: list[dict[str, Any]],
    ) -> dict[str, list[str]]:
        dep: dict[str, list[str]] = {target_id: [c["chunk_id"] for c in direct_callers]}
        for caller in direct_callers:
            caller_id = caller["chunk_id"]
            caller_callers = [
                c["chunk_id"]
                for c in indirect_callers
                if self._is_caller_of(c["chunk_id"], caller_id)
            ]
            if caller_callers:
                dep[caller_id] = caller_callers
        return dep

    def _is_caller_of(self, potential_caller_id: str, callee_id: str) -> bool:
        if not self.graph_engine or not potential_caller_id:
            return False
        callees = self.graph_engine.get_direct_successors(potential_caller_id)
        callee_symbol = callee_id.split(":")[-1] if ":" in callee_id else callee_id
        return callee_id in callees or callee_symbol in callees

    # ------------------------------------------------------------------
    # Result → dict adapters  (handles both SearchResult types)
    # ------------------------------------------------------------------

    def _result_to_dict(self, result: Any, chunk_id: str) -> dict[str, Any]:
        if isinstance(result, dict):
            result["chunk_id"] = chunk_id
            if "file" in result:
                result["file"] = normalize_path(result["file"])
            return result
        if hasattr(result, "metadata"):
            file_path = result.metadata.get(
                "file", result.metadata.get("file_path", "")
            )
            return {
                "chunk_id": chunk_id,
                "file": normalize_path(file_path) if file_path else "",
                "lines": (
                    f"{result.metadata.get('start_line', 0)}"
                    f"-{result.metadata.get('end_line', 0)}"
                ),
                "kind": result.metadata.get("chunk_type", "unknown"),
                "score": result.score,
            }
        file_path = getattr(result, "file_path", getattr(result, "relative_path", ""))
        return {
            "chunk_id": chunk_id,
            "file": normalize_path(file_path) if file_path else "",
            "lines": (
                f"{getattr(result, 'start_line', 0)}-{getattr(result, 'end_line', 0)}"
            ),
            "kind": getattr(result, "chunk_type", "unknown"),
            "score": getattr(result, "similarity_score", 0.0),
        }

    def _extract_result_info(self, result: Any, chunk_id: str) -> dict[str, Any]:
        if hasattr(result, "metadata"):
            return {
                "chunk_id": chunk_id,
                "file": result.metadata.get(
                    "file", result.metadata.get("file_path", "")
                ),
                "lines": (
                    f"{result.metadata.get('start_line', 0)}"
                    f"-{result.metadata.get('end_line', 0)}"
                ),
                "kind": result.metadata.get("chunk_type", "unknown"),
            }
        return {
            "chunk_id": chunk_id,
            "file": getattr(result, "file_path", getattr(result, "relative_path", "")),
            "lines": (
                f"{getattr(result, 'start_line', 0)}-{getattr(result, 'end_line', 0)}"
            ),
            "kind": getattr(result, "chunk_type", "unknown"),
        }

    def _extract_symbol_info(
        self, result: Any, target_id: str, symbol_name: str | None
    ) -> dict[str, Any]:
        if hasattr(result, "metadata"):
            return {
                "chunk_id": target_id,
                "file": result.metadata.get(
                    "file", result.metadata.get("file_path", "")
                ),
                "lines": (
                    f"{result.metadata.get('start_line', 0)}"
                    f"-{result.metadata.get('end_line', 0)}"
                ),
                "kind": result.metadata.get("chunk_type", "unknown"),
                "name": symbol_name or target_id.split(":")[-1],
            }
        return {
            "chunk_id": target_id,
            "file": getattr(result, "file_path", getattr(result, "relative_path", "")),
            "lines": (
                f"{getattr(result, 'start_line', 0)}-{getattr(result, 'end_line', 0)}"
            ),
            "kind": getattr(result, "chunk_type", "unknown"),
            "name": symbol_name or target_id.split(":")[-1],
        }

    @staticmethod
    def _get_chunk_info(chunk_id: str) -> dict[str, Any]:
        parts = chunk_id.split(":")
        return {
            "file": parts[0] if parts else "",
            "kind": parts[2] if len(parts) > 2 else "unknown",
            "name": parts[3] if len(parts) > 3 else "",
        }

    @staticmethod
    def _extract_normalized_path(item: dict[str, Any]) -> str:
        cid = item.get("chunk_id", "")
        if cid and ":" in cid:
            return normalize_path(cid.split(":")[0])
        file_path = item.get("file", "")
        return normalize_path(file_path) if file_path else ""
