"""Search and query tool handlers for MCP server.

Handlers for code search, similarity finding, and connection analysis.
"""

import asyncio
import logging
from typing import Any

from chunking.multi_language_chunker import MultiLanguageChunker
from mcp_server.guidance import add_system_message
from mcp_server.model_pool_manager import get_embedder
from mcp_server.server import (
    get_index_manager,
    get_searcher,
)
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_project_storage_dir
from mcp_server.tools.decorators import error_handler, require_indexed_project
from mcp_server.tools.search_orchestrator import SearchOrchestrator
from mcp_server.utils.config_helpers import temporary_ram_fallback_off
from search.exceptions import DimensionMismatchError
from search.filters import normalize_path
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
from search.metadata import MetadataStore
from search.query_router import QueryRouter
from search.relationship_analyzer import RelationshipAnalyzer


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Search Code Helper Functions
# ----------------------------------------------------------------------------


def _handle_chunk_id_lookup(chunk_id: str) -> dict:
    """Handle direct O(1) chunk lookup by chunk_id.

    Args:
        chunk_id: The chunk identifier to look up directly

    Returns:
        dict: Response with single result or error
    """
    logger.info(f"[DIRECT_LOOKUP] chunk_id='{chunk_id}'")

    try:
        searcher = get_searcher()
        result = searcher.get_by_chunk_id(chunk_id)

        if result is None:
            return {
                "error": "Chunk not found",
                "message": f"No chunk found with ID: {chunk_id}",
                "chunk_id": chunk_id,
            }

        # Reuse existing formatting function for consistency
        formatted_results = _format_search_results([result])
        formatted_result = formatted_results[0]

        # Add graph data if available
        index_manager = _get_index_manager_from_searcher(searcher)
        if index_manager and index_manager.graph_storage is not None:
            graph_data = _get_graph_data_for_chunk(index_manager, chunk_id)
            if graph_data:
                formatted_result["graph"] = graph_data

        # Build response
        response = {
            "query": None,
            "chunk_id": chunk_id,
            "results": [formatted_result],
            "routing": None,
        }

        # Add AI guidance
        response = add_system_message(
            response, tool_name="search_code", query=None, chunk_id=chunk_id
        )

        return response

    except Exception as e:
        logger.error(f"Direct lookup failed: {e}", exc_info=True)
        return {"error": str(e), "chunk_id": chunk_id}


def _route_query_to_model(
    query: str, use_routing: bool, model_key: str | None
) -> tuple[str | None, dict | None]:
    """Route query to optimal embedding model.

    Validates that the routed model has an index for the current project.
    Falls back to auto-detected model if routing selects unindexed model.

    Args:
        query: The search query
        use_routing: Whether to use automatic model routing
        model_key: User-specified model override (None for auto)

    Returns:
        tuple: (selected_model_key, routing_info_dict)
    """
    # User-specified override always wins
    if model_key is not None:
        return model_key, {
            "model_selected": model_key,
            "confidence": 1.0,
            "reason": "User-specified override",
        }

    # Try query routing if enabled
    if get_state().multi_model_enabled and use_routing:
        router = QueryRouter(enable_logging=True)
        decision = router.route(query)

        # Validate routed model has an index for current project
        current_project = get_state().current_project
        if current_project:
            project_dir = get_project_storage_dir(
                current_project, model_key=decision.model_key
            )
            code_index_file = project_dir / "index" / "code.index"

            if code_index_file.exists():
                # Routed model has valid index
                return decision.model_key, {
                    "model_selected": decision.model_key,
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                    "scores": decision.scores,
                }
            else:
                logger.warning(
                    f"Routed model '{decision.model_key}' has no index. "
                    f"Falling back to auto-detected model."
                )

        # Routed model doesn't have index, fall back to auto-detected
        fallback_model = get_state().current_model_key
        if fallback_model:
            return fallback_model, {
                "model_selected": fallback_model,
                "confidence": decision.confidence,
                "reason": f"Fallback to indexed model (routed '{decision.model_key}' not indexed)",
                "routed_model": decision.model_key,
            }

        # Last resort: Try configured default model first, then scan remaining models
        # GUARD: Skip model scanning if no project is selected
        if current_project is None:
            logger.warning(
                "No project selected and no fallback model available. "
                "Cannot determine model for routing."
            )
            return None, None

        from search.config import get_search_config

        config = get_search_config()
        default_model = config.routing.default_model

        # Validate default_model against active pool before trying it
        from mcp_server.model_pool_manager import get_model_pool_manager

        pool_config = get_model_pool_manager().get_pool_config()

        if default_model in pool_config:
            # Try default model first
            logger.info(f"Trying configured default model: {default_model}")
            project_dir = get_project_storage_dir(
                current_project, model_key=default_model
            )
            code_index_file = project_dir / "index" / "code.index"
            if code_index_file.exists():
                logger.info(f"Using configured default model: {default_model}")
                return default_model, {
                    "model_selected": default_model,
                    "confidence": 0.0,
                    "reason": f"Fallback to configured default ({default_model}), routed '{decision.model_key}' not indexed",
                    "routed_model": decision.model_key,
                }
        else:
            logger.info(
                f"Configured default '{default_model}' not in active pool "
                f"{list(pool_config.keys())}, scanning pool models"
            )

        # Then scan remaining models (excluding default since we already checked it)
        for model_key_candidate in pool_config:
            if model_key_candidate == default_model:
                continue  # Already checked above
            project_dir = get_project_storage_dir(
                current_project, model_key=model_key_candidate
            )
            code_index_file = project_dir / "index" / "code.index"
            if code_index_file.exists():
                logger.info(f"Found indexed model: {model_key_candidate}")
                return model_key_candidate, {
                    "model_selected": model_key_candidate,
                    "confidence": 0.0,
                    "reason": f"Auto-detected from indices (routed '{decision.model_key}' not indexed)",
                    "routed_model": decision.model_key,
                }

    return None, None


def _check_auto_reindex(
    project_path: str, selected_model_key: str | None, max_age_minutes: int
) -> tuple[bool, str | None]:
    """Check if auto-reindex is needed and perform if necessary.

    Args:
        project_path: Path to the project
        selected_model_key: The selected model key for embeddings
        max_age_minutes: Maximum age of index before reindex

    Returns:
        Tuple of (reindexed: bool, stored_model_key: str | None)
        - reindexed: True if reindex was performed
        - stored_model_key: The model key from project_info.json (for cache consistency)
    """
    # Load filters from project_info.json to ensure consistent filtering
    import json

    project_storage = get_project_storage_dir(
        project_path, model_key=selected_model_key
    )
    project_info_file = project_storage / "project_info.json"

    include_dirs = None
    exclude_dirs = None
    project_info = None
    if project_info_file.exists():
        try:
            with open(project_info_file) as f:
                project_info = json.load(f)

            # Resolve effective filters (default + user-defined)
            from search.filters import get_effective_filters

            include_dirs, exclude_dirs = get_effective_filters(project_info)
            if include_dirs or exclude_dirs:
                logger.info(
                    f"[AUTO_REINDEX] Loaded filters: include={include_dirs}, exclude={exclude_dirs}"
                )
        except Exception as e:
            logger.warning(f"[AUTO_REINDEX] Failed to load filters: {e}")

    # CRITICAL: For existing indexes, use the model that created the index
    # NOT the routing-selected model (prevents dimension mismatch errors)
    model_key_for_embedder = selected_model_key
    if project_info and project_info.get("embedding_model"):
        from mcp_server.model_pool_manager import get_model_key_from_name

        stored_model_name = project_info["embedding_model"]
        stored_model_key = get_model_key_from_name(stored_model_name)
        if stored_model_key:
            model_key_for_embedder = stored_model_key
            logger.info(
                f"[AUTO_REINDEX] Using stored model from index: {stored_model_name} "
                f"(key: {stored_model_key}) instead of routing selection"
            )
        else:
            logger.error(
                f"[AUTO_REINDEX] Stored model '{stored_model_name}' is not registered in "
                f"MODEL_POOL_CONFIG or MODEL_POOL_CONFIG_LIGHTWEIGHT_SPEED. Existing index "
                f"will be discarded and rebuilt with routing-selected model "
                f"'{selected_model_key}'. Update search/config.py:ALL_POOL_MODELS to "
                f"register this model and prevent data loss."
            )

    # Phase 1: Lightweight freshness check (no HybridSearcher/embedder needed)
    from chunking.tree_sitter import TreeSitterChunker
    from merkle.change_detector import ChangeDetector
    from merkle.snapshot_manager import SnapshotManager

    snapshot_mgr = SnapshotManager()
    change_detector = ChangeDetector(
        snapshot_mgr,
        include_dirs,
        exclude_dirs,
        supported_extensions=set(TreeSitterChunker.get_supported_extensions()),
    )

    # Check if snapshot exists and is fresh
    if snapshot_mgr.has_snapshot(project_path):
        age = snapshot_mgr.get_snapshot_age(project_path)
        # Index is fresh by age — do quick change detection
        if (
            age is not None
            and age <= max_age_minutes * 60
            and not change_detector.quick_check(project_path)
        ):
            logger.debug(
                f"[AUTO_REINDEX] Index for {project_path} is fresh (age: {age:.1f}s, "
                f"max: {max_age_minutes * 60}s), skipping reindex"
            )
            return False, model_key_for_embedder

    # Phase 2: Index is stale — create full machinery and reindex
    logger.debug(
        "[AUTO_REINDEX] Index is stale or missing, proceeding with full reindex check"
    )

    # Validate dimension compatibility BEFORE creating searcher
    from search.dimension_validator import validate_embedder_index_compatibility

    embedder = get_embedder(model_key_for_embedder, allow_cross_pool=True)

    try:
        validate_embedder_index_compatibility(
            embedder, project_storage, raise_on_mismatch=True
        )
    except DimensionMismatchError as e:
        logger.error(
            f"Dimension mismatch detected for index '{project_storage.name}': {e}. "
            f"Existing index will be discarded and rebuilt."
        )
        # Continue - the incremental_indexer will handle reindex

    config = get_config()
    if config.search_mode.enable_hybrid:
        storage_dir = project_storage / "index"
        # Extract project_id from storage directory name (same pattern as search_factory.py:175)
        project_id = project_storage.name.rsplit("_", 1)[0]  # Remove dimension suffix
        indexer = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=embedder,
            bm25_weight=config.search_mode.bm25_weight,
            dense_weight=config.search_mode.dense_weight,
            rrf_k=config.search_mode.rrf_k_parameter,
            max_workers=2,
            project_id=project_id,
            config=config,
        )
        # Track project/model key eagerly (used by downstream get_searcher() routing).
        # Searcher bind is deferred until after auto_reindex_if_needed so we never
        # cache a HybridSearcher whose embedder was just nulled by clear_embedders().
        state = get_state()
        if (
            state.searcher is None
            or state.current_project != project_path
            or state.current_model_key != model_key_for_embedder
        ):
            state.current_project = project_path
            state.current_model_key = model_key_for_embedder
    else:
        indexer = get_index_manager(project_path, model_key=selected_model_key)
    chunker = MultiLanguageChunker(
        project_path,
        include_dirs,
        exclude_dirs,
        enable_entity_tracking=config.performance.enable_entity_tracking,
    )
    incremental_indexer = IncrementalIndexer(
        indexer=indexer,
        embedder=embedder,
        chunker=chunker,
        include_dirs=include_dirs,
        exclude_dirs=exclude_dirs,
    )

    # Temporarily disable allow_ram_fallback during auto-reindex for performance
    with temporary_ram_fallback_off():
        reindex_result = incremental_indexer.auto_reindex_if_needed(
            project_path, max_age_minutes=max_age_minutes
        )

    reindexed = reindex_result.files_modified > 0 or reindex_result.files_added > 0

    # Bind the local indexer as the cached searcher only if its embedder is still alive.
    # clear_embedders() (called during needs_reindex paths) resets state.searcher=None AND
    # replaces the pool entry with a fresh CodeEmbedder. The identity check (is embedder)
    # confirms the pool still holds the same object we built indexer with — if clear_embedders
    # ran, a new object will be in the pool and we skip the bind, letting get_searcher()
    # construct a fresh HybridSearcher from the new embedder.
    if (
        config.search_mode.enable_hybrid
        and model_key_for_embedder
        and get_state().searcher is None
        and get_state().embedders.get(model_key_for_embedder) is embedder
    ):
        get_state().searcher = indexer

    # Return stored model key for searcher cache consistency
    return reindexed, model_key_for_embedder


def _get_index_manager_from_searcher(searcher) -> CodeIndexManager | None:
    """Extract index_manager from searcher (handles different searcher types).

    Args:
        searcher: HybridSearcher or IntelligentSearcher instance

    Returns:
        CodeIndexManager or None
    """
    if hasattr(searcher, "index_manager"):
        return searcher.index_manager
    elif hasattr(searcher, "dense_index"):
        return searcher.dense_index
    return None


async def _resolve_symbol_to_chunk_id(
    symbol_name: str,
    searcher: Any,
) -> tuple[str | None, dict[str, str] | None]:
    """Resolve a symbol name to a chunk_id via a 3-tier cascade.

    Returns ``(chunk_id, resolution_info)`` on success, or ``(None, None)`` when
    the symbol cannot be resolved.  Callers are responsible for returning an
    appropriate error response.

    Tier 1: O(1) symbol_cache direct lookup
    Tier 2: graph node name index + suffix scan (both ``:name`` and ``.name`` so
            class-qualified names like ``ClassName.method_name`` are handled)
    Tier 3: semantic search with name-preference filter
    """
    # Tier 1 — O(1) symbol cache
    index_manager = _get_index_manager_from_searcher(searcher)
    if (
        index_manager
        and hasattr(index_manager, "symbol_cache")
        and index_manager.symbol_cache
    ):
        resolved = index_manager.symbol_cache.get_by_symbol_name(symbol_name)
        if resolved:
            return resolved, {
                "resolved_from": symbol_name,
                "chunk_id": resolved,
                "resolution_method": "direct_lookup",
            }

    # Tier 2 — graph node name index + suffix scan
    if hasattr(searcher, "dense_index"):
        gs = getattr(searcher.dense_index, "graph_storage", None)
        if gs:
            matches = (
                gs.get_nodes_by_name(symbol_name)
                if hasattr(gs, "get_nodes_by_name")
                else []
            )
            if not matches:
                # Plain ":name" (chunk_id suffix) or class-qualified ".name"
                matches = [
                    n
                    for n in gs.graph.nodes()
                    if n.endswith(f":{symbol_name}") or n.endswith(f".{symbol_name}")
                ]
            if matches:
                return matches[0], {
                    "resolved_from": symbol_name,
                    "chunk_id": matches[0],
                    "resolution_method": "graph_lookup",
                }

    # Tier 3 — semantic search with name-preference filter
    results = await asyncio.to_thread(searcher.search, symbol_name, k=5)
    for r in results:
        meta = r.metadata if hasattr(r, "metadata") else {}
        if meta.get("name") == symbol_name:
            return r.chunk_id, {
                "resolved_from": symbol_name,
                "chunk_id": r.chunk_id,
                "resolution_method": "semantic_search",
            }
    if results:
        return results[0].chunk_id, {
            "resolved_from": symbol_name,
            "chunk_id": results[0].chunk_id,
            "resolution_method": "semantic_search",
        }

    return None, None


# ============================================================================
# Full Relationship Enrichment Per Result
# ============================================================================

# Reverse relation names for incoming edge enrichment
# Matches graph_storage._get_reverse_relation_type() naming convention
_REVERSE_RELATION_MAP: dict[str, str] = {
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


def _get_reverse_relation_name(rel_type: str) -> str:
    """Get the reverse name for a relationship type.

    Args:
        rel_type: Forward relationship type (e.g., "calls", "inherits")

    Returns:
        Reverse relationship name (e.g., "called_by", "inherited_by")
    """
    return _REVERSE_RELATION_MAP.get(rel_type, f"{rel_type}_by")


def _get_graph_data_for_chunk(
    index_manager: CodeIndexManager, chunk_id: str, max_per_type: int = 5
) -> dict | None:
    """Get all graph relationship data for a chunk (21 relationship types).

    Iterates outgoing and incoming edges, grouping by relationship type.
    Also checks incoming edges by bare symbol name, since edges often
    target symbol names (e.g., "login") rather than full chunk_ids.

    Args:
        index_manager: The index manager with graph storage
        chunk_id: The chunk to get graph data for
        max_per_type: Maximum targets/sources per relationship type (default: 5)

    Returns:
        dict mapping relationship names to lists of chunk_ids/symbols, or None
    """
    try:
        graph = index_manager.graph_storage
        normalized = normalize_path(chunk_id)
        result: dict[str, list[str]] = {}

        # Early return if node not in graph
        if normalized not in graph.graph:
            return None

        # Outgoing edges (this chunk is source) -> forward relation names
        for _, target, edge_data in graph.graph.out_edges(normalized, data=True):
            rel_type = edge_data.get("type", "calls")
            lst = result.setdefault(rel_type, [])
            if len(lst) < max_per_type:
                lst.append(target)

        # Incoming edges by chunk_id -> reverse relation names
        for source, _, edge_data in graph.graph.in_edges(normalized, data=True):
            rel_type = edge_data.get("type", "calls")
            reverse = _get_reverse_relation_name(rel_type)
            lst = result.setdefault(reverse, [])
            if len(lst) < max_per_type:
                lst.append(source)

        # Incoming edges by symbol name (edges often target bare names)
        symbol_name = normalized.rsplit(":", 1)[-1] if ":" in normalized else None
        if symbol_name and symbol_name != normalized and symbol_name in graph.graph:
            for source, _, edge_data in graph.graph.in_edges(symbol_name, data=True):
                rel_type = edge_data.get("type", "calls")
                reverse = _get_reverse_relation_name(rel_type)
                lst = result.setdefault(reverse, [])
                if len(lst) < max_per_type and source not in lst:
                    lst.append(source)

        return result if result else None
    except Exception as e:
        logger.debug(f"Failed to get graph data for {chunk_id}: {e}")
    return None


def _format_search_results(results: list) -> list[dict]:
    """Format search results to JSON-serializable dicts.

    Args:
        results: List of SearchResult objects

    Returns:
        List of formatted result dictionaries
    """
    formatted_results = []
    for result in results:
        if hasattr(result, "relative_path"):
            # IntelligentSearcher result format
            item = {
                "file": result.relative_path,
                "lines": f"{result.start_line}-{result.end_line}",
                "kind": result.chunk_type,
                "score": round(result.similarity_score, 2),
                "chunk_id": result.chunk_id,
            }
            # Note: name field omitted (redundant with chunk_id last component)
            # Add complexity score if available (functions only)
            if hasattr(result, "complexity_score") and result.complexity_score:
                item["complexity_score"] = result.complexity_score
            # Propagate source field for ego-graph neighbor identification
            if hasattr(result, "source") and result.source:
                item["source"] = result.source
        else:
            # HybridSearcher result format
            item = {
                "file": result.metadata.get("relative_path", ""),
                "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
                "kind": result.metadata.get("chunk_type", "unknown"),
                "score": round(result.score, 2),
                "chunk_id": result.chunk_id,
            }
            # Add name for module-type results (helps identify what the chunk represents)
            name = result.metadata.get("name", "")
            if name:
                item["name"] = name
            # Add docstring preview for module summaries (compressed context)
            if result.metadata.get("chunk_type") in ("module", "community"):
                doc = result.metadata.get("docstring", "")
                if doc:
                    item["summary"] = doc[:200]
            # Add reranker score if available (neural reranking)
            if "reranker_score" in result.metadata:
                item["reranker_score"] = round(result.metadata["reranker_score"], 4)
            # Add complexity score if available (functions only)
            if result.metadata.get("complexity_score"):
                item["complexity_score"] = result.metadata["complexity_score"]
            # Propagate source field for ego-graph neighbor identification
            if hasattr(result, "source") and result.source:
                item["source"] = result.source
        formatted_results.append(item)
    return formatted_results


def _parse_line(lines_str: str, part: int = 0) -> int:
    """Extract start (part=0) or end (part=-1) line from 'start-end' format."""
    try:
        return int(lines_str.split("-")[part])
    except (ValueError, IndexError, AttributeError):
        return 0


def _reorder_by_source_position(results: list[dict]) -> list[dict]:
    """Reorder results by file source position (DOS RAG technique).

    Groups results by file path and sorts each group by start line number.
    Inter-file ordering is preserved by each file group's highest score.
    Gap indicators are added between non-contiguous chunks from the same file.

    Based on: "Stronger Baselines for RAG with Long-Context LMs" (EMNLP 2025).
    Sorting retrieved chunks into original document order gives +5.3% accuracy
    over similarity-ranked order at zero retrieval cost.

    Args:
        results: List of formatted result dicts with "file" and "lines" fields

    Returns:
        Results reordered by source position, with gap indicators inserted
    """
    if not results:
        return results

    # Group results by file, preserving highest score per group for inter-file ordering
    file_groups: dict[str, list[dict]] = {}
    file_best_score: dict[str, float] = {}

    for result in results:
        file_key = result.get("file", "")
        bs = result.get("blended_score")
        score = bs if bs is not None else result.get("score", 0.0)
        if file_key not in file_groups:
            file_groups[file_key] = []
            file_best_score[file_key] = score
        else:
            file_best_score[file_key] = max(file_best_score[file_key], score)
        file_groups[file_key].append(result)

    # Sort file groups by their best score (descending)
    sorted_files = sorted(
        file_groups.keys(), key=lambda f: file_best_score[f], reverse=True
    )

    reordered: list[dict] = []
    for file_key in sorted_files:
        group = file_groups[file_key]
        # Sort chunks within each file by start line
        group.sort(key=lambda r: _parse_line(r.get("lines", "0"), 0))

        # Annotate gap info on the preceding chunk (gap_after field) to avoid
        # injecting synthetic rows that would dilute downstream [:k] slices.
        for i, chunk in enumerate(group):
            reordered.append(chunk)
            if i < len(group) - 1:
                curr_end = _parse_line(group[i].get("lines", "0"), -1)
                next_start = _parse_line(group[i + 1].get("lines", "0"), 0)
                gap = next_start - curr_end - 1
                if gap > 0:
                    chunk["gap_after"] = f"[... {gap} lines omitted ...]"

    return reordered


def _enrich_results_with_graph_data(
    results: list[dict], index_manager: CodeIndexManager | None
) -> list[dict]:
    """Add graph relationship data to search results.

    Args:
        results: List of formatted result dicts
        index_manager: Index manager with graph storage

    Returns:
        Results with graph data added where available
    """
    if not index_manager or index_manager.graph_storage is None:
        return results

    for item in results:
        chunk_id = item.get("chunk_id")
        # Skip per-result graph data for ego-graph neighbors (captured in subgraph_edges instead)
        # Saves ~400 chars per ego neighbor, ~8K chars total for 20 neighbors
        if chunk_id and item.get("source") != "ego_graph":
            graph_data = _get_graph_data_for_chunk(index_manager, chunk_id)
            if graph_data:
                item["graph"] = graph_data

    return results


# ----------------------------------------------------------------------------
# Main Search Handlers
# ----------------------------------------------------------------------------


@error_handler("Search")
@require_indexed_project
async def handle_search_code(arguments: dict[str, Any]) -> dict:
    """Search code with natural language query. Delegates to SearchOrchestrator.run()."""
    return await SearchOrchestrator().run(arguments)


@error_handler("Find similar")
@require_indexed_project
async def handle_find_similar_code(arguments: dict[str, Any]) -> dict:
    """Find code chunks similar to a reference chunk."""
    chunk_id = arguments["chunk_id"]
    k = arguments.get("k", 4)  # Align with default_k=4

    # Normalize chunk_id path separators
    # Use CodeIndexManager's normalize_chunk_id for proper cross-platform handling
    if chunk_id:
        chunk_id = MetadataStore.normalize_chunk_id(chunk_id)

    # Offload blocking get_searcher + find_similar_to_chunk off the event loop.
    def _run_find_similar() -> list:
        _searcher = get_searcher()
        return _searcher.find_similar_to_chunk(chunk_id, k=k)

    results = await asyncio.to_thread(_run_find_similar)

    formatted_results = []
    for result in results:
        item = {
            "chunk_id": result.chunk_id,
            "file": result.relative_path,
            "lines": f"{result.start_line}-{result.end_line}",
            "kind": result.chunk_type,
            "score": round(result.similarity_score, 2),
        }
        if hasattr(result, "name") and result.name:
            item["name"] = result.name
        formatted_results.append(item)

    return {
        "reference_chunk": chunk_id,
        "similar_chunks": formatted_results,
    }


@error_handler(
    "Impact analysis",
    error_context=lambda args: {
        "chunk_id": args.get("chunk_id"),
        "symbol_name": args.get("symbol_name"),
    },
)
@require_indexed_project
async def handle_find_connections(arguments: dict[str, Any]) -> dict:
    """Find all code connections to a given symbol."""
    chunk_id = arguments.get("chunk_id")
    symbol_name = arguments.get("symbol_name")
    max_depth = arguments.get("max_depth", 3)
    exclude_dirs = arguments.get("exclude_dirs")
    relationship_types = arguments.get("relationship_types")

    # Validate inputs
    if not chunk_id and not symbol_name:
        return {
            "error": "Missing required parameter",
            "message": "Provide either chunk_id or symbol_name",
        }

    # Normalize chunk_id path separators for cross-platform compatibility
    if chunk_id:
        chunk_id = MetadataStore.normalize_chunk_id(chunk_id)

    logger.info(
        f"[FIND_CONNECTIONS] chunk_id={chunk_id}, symbol_name={symbol_name}, depth={max_depth}"
    )

    # Offload blocking get_searcher + analyze_impact off the event loop.
    def _run_find_connections():
        _searcher = get_searcher()
        _analyzer = RelationshipAnalyzer.from_searcher(_searcher)
        return _analyzer.analyze_impact(
            chunk_id=chunk_id,
            symbol_name=symbol_name,
            max_depth=max_depth,
            exclude_dirs=exclude_dirs,
            relationship_types=relationship_types,
        )

    report = await asyncio.to_thread(_run_find_connections)

    # Convert to dict
    response = report.to_dict()

    # Add system message
    response = add_system_message(
        response,
        tool_name="find_connections",
        total_impacted=report.total_impacted,
        file_count=len(report.unique_files),
    )

    return response


@error_handler(
    "Find path",
    error_context=lambda args: {
        "source": args.get("source") or args.get("source_chunk_id"),
        "target": args.get("target") or args.get("target_chunk_id"),
    },
)
@require_indexed_project
async def handle_find_path(arguments: dict[str, Any]) -> dict:
    """Find shortest path between two code entities."""
    # Extract parameters
    source = arguments.get("source")
    target = arguments.get("target")
    source_chunk_id = arguments.get("source_chunk_id")
    target_chunk_id = arguments.get("target_chunk_id")
    max_hops = min(arguments.get("max_hops", 10), 20)
    edge_types = arguments.get("edge_types")

    # Validate: need at least one source and one target identifier
    if not source and not source_chunk_id:
        return {
            "error": "Missing source",
            "message": "Provide either source (symbol name) or source_chunk_id",
        }
    if not target and not target_chunk_id:
        return {
            "error": "Missing target",
            "message": "Provide either target (symbol name) or target_chunk_id",
        }

    # Normalize chunk_ids
    if source_chunk_id:
        source_chunk_id = MetadataStore.normalize_chunk_id(source_chunk_id)
    if target_chunk_id:
        target_chunk_id = MetadataStore.normalize_chunk_id(target_chunk_id)

    # Offload get_searcher off the event loop (can construct HybridSearcher on miss).
    searcher = await asyncio.to_thread(get_searcher)

    # Resolve symbol names to chunk_ids if needed
    resolved_source = source_chunk_id
    resolved_target = target_chunk_id
    source_info = None
    target_info = None

    if not resolved_source and source:
        resolved_source, source_info = await _resolve_symbol_to_chunk_id(
            source, searcher
        )
        if not resolved_source:
            return {
                "path_found": False,
                "error": f"Could not resolve source symbol: {source}",
            }

    if not resolved_target and target:
        resolved_target, target_info = await _resolve_symbol_to_chunk_id(
            target, searcher
        )
        if not resolved_target:
            return {
                "path_found": False,
                "error": f"Could not resolve target symbol: {target}",
            }

    # Get graph query engine
    graph_storage = None
    if hasattr(searcher, "dense_index") and hasattr(
        searcher.dense_index, "graph_storage"
    ):
        graph_storage = searcher.dense_index.graph_storage
    elif hasattr(searcher, "graph_storage"):
        graph_storage = searcher.graph_storage

    if not graph_storage:
        return {
            "error": "Graph not available",
            "message": "Call graph not initialized. Re-index the project.",
        }

    # Create query engine and find path
    from graph.graph_queries import GraphQueryEngine

    query_engine = GraphQueryEngine(graph_storage)

    result = await asyncio.to_thread(
        query_engine.find_path,
        source_id=resolved_source,
        target_id=resolved_target,
        max_hops=max_hops,
        edge_types=edge_types,
    )

    if result is None:
        # Get node info for error message
        source_node = graph_storage.get_node_data(resolved_source)
        target_node = graph_storage.get_node_data(resolved_target)

        response: dict[str, Any] = {
            "path_found": False,
            "source": {
                "chunk_id": resolved_source,
                "name": (
                    source_node.get("name")
                    if source_node
                    else resolved_source.split(":")[-1]
                ),
                "exists_in_graph": resolved_source in graph_storage.graph,
            },
            "target": {
                "chunk_id": resolved_target,
                "name": (
                    target_node.get("name")
                    if target_node
                    else resolved_target.split(":")[-1]
                ),
                "exists_in_graph": resolved_target in graph_storage.graph,
            },
            "reason": "No path exists"
            + (f" with edge_types={edge_types}" if edge_types else ""),
        }
    else:
        # Add source/target metadata
        response: dict[str, Any] = result
        response["source"] = result["path"][0]["node"] if result["path"] else {}
        response["target"] = result["path"][-1]["node"] if result["path"] else {}

    # Add resolution info if symbols were searched
    if source_info:
        response["source_resolved"] = source_info
    if target_info:
        response["target_resolved"] = target_info

    # Add system message
    if response.get("path_found"):
        path_len = response["path_length"]
        src_name = response["source"].get("name", "source")
        tgt_name = response["target"].get("name", "target")
        # pyrefly: ignore [no-matching-overload]
        edge_summary = ", ".join(response.get("edge_types_traversed", [])) or "various"
        response["system_message"] = (
            f"Found path of length {path_len} from {src_name} to {tgt_name} "
            f"via {edge_summary} relationships."
        )
    else:
        response["system_message"] = (
            "No path found. Try: (1) removing edge_types filter, "
            "(2) increasing max_hops, (3) verifying both symbols exist in graph."
        )

    return response
