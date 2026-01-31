"""Search and query tool handlers for MCP server.

Handlers for code search, similarity finding, and connection analysis.
"""

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
from mcp_server.tools.code_relationship_analyzer import CodeRelationshipAnalyzer
from mcp_server.tools.decorators import error_handler
from mcp_server.utils.config_helpers import temporary_ram_fallback_off
from search.config import (
    EgoGraphConfig,
    ParentRetrievalConfig,
    get_config_manager,
    get_search_config,
)
from search.exceptions import DimensionMismatchError
from search.filters import normalize_path
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
from search.intent_classifier import IntentClassifier, QueryIntent
from search.metadata import MetadataStore
from search.query_router import QueryRouter


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
        default_model = config.routing.default_model  # "bge_m3"

        # Try default model first
        logger.info(f"Trying configured default model: {default_model}")
        project_dir = get_project_storage_dir(current_project, model_key=default_model)
        code_index_file = project_dir / "index" / "code.index"
        if code_index_file.exists():
            logger.info(f"Using configured default model: {default_model}")
            return default_model, {
                "model_selected": default_model,
                "confidence": 0.0,
                "reason": f"Fallback to configured default ({default_model}), routed '{decision.model_key}' not indexed",
                "routed_model": decision.model_key,
            }

        # Then scan remaining models (excluding default since we already checked it)
        from mcp_server.model_pool_manager import get_model_pool_manager

        pool_config = get_model_pool_manager()._get_pool_config()
        for model_key_candidate in pool_config.keys():
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
) -> bool:
    """Check if auto-reindex is needed and perform if necessary.

    Args:
        project_path: Path to the project
        selected_model_key: The selected model key for embeddings
        max_age_minutes: Maximum age of index before reindex

    Returns:
        bool: True if reindex was performed
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
            logger.warning(
                f"[AUTO_REINDEX] Could not map stored model '{stored_model_name}' to key, "
                f"falling back to routing selection: {selected_model_key}"
            )

    # Validate dimension compatibility BEFORE creating searcher
    from search.dimension_validator import validate_embedder_index_compatibility

    embedder = get_embedder(model_key_for_embedder)

    try:
        validate_embedder_index_compatibility(
            embedder, project_storage, raise_on_mismatch=True
        )
    except DimensionMismatchError as e:
        logger.warning(f"Dimension mismatch detected, will trigger full reindex: {e}")
        # Continue - the incremental_indexer will handle reindex

    config = get_config()
    if config.search_mode.enable_hybrid:
        storage_dir = project_storage / "index"
        indexer = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=embedder,
            bm25_weight=config.search_mode.bm25_weight,
            dense_weight=config.search_mode.dense_weight,
        )
    else:
        indexer = get_index_manager(project_path, model_key=selected_model_key)
    chunker = MultiLanguageChunker(
        project_path, enable_entity_tracking=config.performance.enable_entity_tracking
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

    return reindex_result.files_modified > 0 or reindex_result.files_added > 0


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


# ============================================================================
# SSCG Phase 2: Full Relationship Enrichment Per Result
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
            # SSCG Phase 5: Propagate source field for ego-graph neighbor identification
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
            # Add reranker score if available (neural reranking)
            if "reranker_score" in result.metadata:
                item["reranker_score"] = round(result.metadata["reranker_score"], 4)
            # Add complexity score if available (functions only)
            if result.metadata.get("complexity_score"):
                item["complexity_score"] = result.metadata["complexity_score"]
            # SSCG Phase 5: Propagate source field for ego-graph neighbor identification
            if hasattr(result, "source") and result.source:
                item["source"] = result.source
        formatted_results.append(item)
    return formatted_results


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
async def handle_search_code(arguments: dict[str, Any]) -> dict:
    """Search code with natural language query.

    Supports two modes:
    1. Direct chunk_id lookup (O(1) - fast path)
    2. Semantic/hybrid search by query (normal path)

    Uses extracted helper functions for clarity:
    - _handle_chunk_id_lookup(): Direct lookups
    - _route_query_to_model(): Model routing decisions
    - _check_auto_reindex(): Index freshness checks
    - _format_search_results(): Result formatting
    - _enrich_results_with_graph_data(): Graph relationship enrichment
    """
    # Extract arguments
    query = arguments.get("query")
    chunk_id = arguments.get("chunk_id")

    # Get k from arguments, falling back to config default_k (Easy Win 2 + 3)
    search_config = get_search_config()
    config_default_k = search_config.search_mode.default_k
    k = arguments.get("k", config_default_k)

    # Enforce max_k limit (Easy Win 3)
    k = min(k, search_config.search_mode.max_k)

    # Validate: must provide either query OR chunk_id, not both
    if not query and not chunk_id:
        return {
            "error": "Missing required parameter",
            "message": "Provide either query or chunk_id parameter",
        }
    if query and chunk_id:
        return {
            "error": "Invalid parameters",
            "message": "Provide either query OR chunk_id, not both",
        }

    # FAST PATH: Direct chunk_id lookup
    if chunk_id:
        return _handle_chunk_id_lookup(chunk_id)

    # Early extraction for model routing (needed by intent redirects)
    use_routing = arguments.get("use_routing", True)
    model_key = arguments.get("model_key")

    # Ego-graph defaults (may be overridden by CONTEXTUAL intent)
    ego_graph_enabled = arguments.get("ego_graph_enabled", False)
    ego_graph_k_hops = arguments.get("ego_graph_k_hops", 2)
    ego_graph_max_neighbors = arguments.get("ego_graph_max_neighbors_per_hop", 10)

    # Route query to optimal embedding model
    selected_model_key, routing_info = _route_query_to_model(
        query, use_routing, model_key
    )

    # Intent Classification (Phase 2)
    config = get_config()
    if config.intent.enabled:
        intent_classifier = IntentClassifier(
            confidence_threshold=config.intent.confidence_threshold,
            enable_logging=config.intent.log_classifications,
        )
        intent_decision = intent_classifier.classify(query)

        logger.info(
            f"[INTENT] query='{query[:50]}...' -> {intent_decision.intent.value} "
            f"(conf={intent_decision.confidence:.2f}, reason={intent_decision.reason})"
        )

        # Redirect PATH_TRACING queries to find_path
        if (
            intent_decision.intent == QueryIntent.PATH_TRACING
            and intent_decision.confidence >= config.intent.confidence_threshold
        ):
            source = intent_decision.suggested_params.get("source")
            target = intent_decision.suggested_params.get("target")
            if source and target:
                logger.info(
                    f"[INTENT] Redirecting PATH_TRACING query to find_path: {source} → {target}"
                )
                return await handle_find_path(
                    {
                        "source": source,
                        "target": target,
                        "max_hops": 10,
                    }
                )

        # Redirect SIMILARITY queries to find_similar_code
        if (
            intent_decision.intent == QueryIntent.SIMILARITY
            and intent_decision.confidence >= config.intent.confidence_threshold
        ):
            symbol_name = intent_decision.suggested_params.get("symbol_name")
            if symbol_name:
                # First search to get chunk_id, then find similar
                logger.info(
                    f"[INTENT] Redirecting SIMILARITY query to find_similar_code: {symbol_name}"
                )
                try:
                    # Get searcher if not already initialized
                    if "searcher" not in locals():
                        searcher = get_searcher(model_key=selected_model_key)
                    search_result = searcher.search(symbol_name, k=1)
                    if search_result:
                        return await handle_find_similar_code(
                            {
                                "chunk_id": search_result[0].chunk_id,
                                "k": k,
                            }
                        )
                except Exception as e:
                    logger.warning(
                        f"[INTENT] Failed to redirect SIMILARITY query: {e}. "
                        f"Falling back to normal search."
                    )

        # Apply ego_graph for CONTEXTUAL queries (don't redirect, enhance search)
        if intent_decision.intent == QueryIntent.CONTEXTUAL:
            if intent_decision.suggested_params.get("ego_graph_enabled"):
                ego_graph_enabled = True
                ego_graph_k_hops = intent_decision.suggested_params.get(
                    "ego_graph_k_hops", 2
                )
                logger.info(
                    f"[INTENT] Enabling ego_graph for CONTEXTUAL query (k_hops={ego_graph_k_hops})"
                )

        # Redirect NAVIGATIONAL queries to find_connections
        if (
            intent_decision.intent == QueryIntent.NAVIGATIONAL
            and intent_decision.confidence >= config.intent.confidence_threshold
            and config.intent.enable_navigational_redirect
        ):
            symbol_name = intent_decision.suggested_params.get("symbol_name")
            rel_types = intent_decision.suggested_params.get("relationship_types")
            if symbol_name:
                logger.info(
                    f"[INTENT] Redirecting NAVIGATIONAL query to find_connections: {symbol_name}"
                    + (f" with relationship_types={rel_types}" if rel_types else "")
                )
                return await handle_find_connections(
                    {
                        "symbol_name": symbol_name,
                        "exclude_dirs": arguments.get("exclude_dirs"),
                        "max_depth": 3,
                        "relationship_types": rel_types,  # Pass detected relationship types
                    }
                )

        # Adjust k parameter for GLOBAL queries
        if intent_decision.intent == QueryIntent.GLOBAL:
            suggested_k = intent_decision.suggested_params.get("k", k)
            if suggested_k > k:
                logger.info(
                    f"[INTENT] Increasing k from {k} to {suggested_k} for GLOBAL query"
                )
                k = suggested_k

    # NORMAL PATH: Search by query
    search_mode = arguments.get("search_mode", "auto")
    file_pattern = arguments.get("file_pattern")
    include_dirs = arguments.get("include_dirs")
    exclude_dirs = arguments.get("exclude_dirs")
    chunk_type = arguments.get("chunk_type")
    include_context = arguments.get("include_context", True)
    auto_reindex = arguments.get("auto_reindex", True)
    # Use config default instead of hardcoded 5 (respects search_config.json)
    max_age_minutes = arguments.get(
        "max_age_minutes", get_config().performance.max_index_age_minutes
    )

    # Parent chunk retrieval parameter (Match Small, Retrieve Big)
    include_parent = arguments.get("include_parent", False)

    logger.info(f"[SEARCH] query='{query}', k={k}, mode='{search_mode}'")

    # Early validation: Check if a project is indexed before routing
    current_project = get_state().current_project
    if not current_project:
        return {
            "error": "No indexed project found",
            "message": "You must index a project before searching. Use index_directory first.",
            "current_project": None,
            "system_message": "No project indexed. Use index_directory(directory_path) to index a project first.",
        }

    # Check and perform auto-reindex if index is stale
    current_project = get_state().current_project
    if auto_reindex and current_project:
        try:
            reindexed = _check_auto_reindex(
                current_project, selected_model_key, max_age_minutes
            )
            if reindexed:
                get_state().searcher = None
        except DimensionMismatchError as e:
            # Recovery: Return helpful error with suggested action
            return {
                "error": "Dimension mismatch",
                "message": str(e),
                "recovery_suggestion": (
                    f"Run index_directory with force_reindex=True to rebuild "
                    f"the index for model {e.embedder_model}"
                ),
                "embedder_dimension": e.embedder_dim,
                "index_dimension": e.index_dim,
            }

    # Execute search with selected model index
    try:
        searcher = get_searcher(model_key=selected_model_key)
    except DimensionMismatchError as e:
        return {
            "error": "Dimension mismatch",
            "message": str(e),
            "recovery_suggestion": (
                f"Run index_directory with force_reindex=True to rebuild "
                f"the index for model {e.embedder_model}"
            ),
            "embedder_dimension": e.embedder_dim,
            "index_dimension": e.index_dim,
        }

    # Check if index ready - support both HybridSearcher and IntelligentSearcher
    total_chunks = 0
    is_ready = False

    # Option 1: HybridSearcher (has is_ready property and dense_index)
    if hasattr(searcher, "is_ready"):
        is_ready = searcher.is_ready
        if hasattr(searcher, "dense_index") and searcher.dense_index:
            if hasattr(searcher.dense_index, "index") and searcher.dense_index.index:
                total_chunks = searcher.dense_index.index.ntotal
    # Option 2: IntelligentSearcher (has index_manager)
    elif hasattr(searcher, "index_manager") and searcher.index_manager:
        stats = searcher.index_manager.get_stats()
        total_chunks = stats.get("total_chunks", 0)
        is_ready = total_chunks > 0
    # Option 3: Direct stats method
    elif hasattr(searcher, "get_stats"):
        stats = searcher.get_stats()
        total_chunks = stats.get("total_chunks", 0)
        is_ready = total_chunks > 0

    if not is_ready or total_chunks == 0:
        return {
            "error": "No indexed project found",
            "message": "You must index a project before searching",
            "current_project": current_project or "None",
        }
    # Build filters
    filters = {}
    if file_pattern:
        filters["file_pattern"] = [file_pattern]
    if include_dirs:
        filters["include_dirs"] = include_dirs
    if exclude_dirs:
        filters["exclude_dirs"] = exclude_dirs
    if chunk_type:
        filters["chunk_type"] = chunk_type

    # Perform search
    config_manager = get_config_manager()
    actual_search_mode = config_manager.get_search_mode_for_query(query, search_mode)

    # Build SearchConfig with ego-graph settings if enabled
    search_config = None
    if isinstance(searcher, HybridSearcher) and ego_graph_enabled:
        # Get base config and override ego-graph settings
        base_config = get_search_config()
        ego_config = EgoGraphConfig(
            enabled=ego_graph_enabled,
            k_hops=ego_graph_k_hops,
            max_neighbors_per_hop=ego_graph_max_neighbors,
        )
        # Create modified config with ego-graph enabled
        search_config = base_config
        search_config.ego_graph = ego_config
        logger.info(
            f"[EGO_GRAPH] Enabled with k_hops={ego_graph_k_hops}, "
            f"max_neighbors_per_hop={ego_graph_max_neighbors}"
        )

    # Build SearchConfig with parent-retrieval settings if enabled
    if isinstance(searcher, HybridSearcher) and include_parent:
        # Get base config if not already set
        if search_config is None:
            search_config = get_search_config()
        # Override parent-retrieval settings
        parent_config = ParentRetrievalConfig(enabled=include_parent)
        search_config.parent_retrieval = parent_config
        logger.info("[PARENT_RETRIEVAL] Enabled")

    if isinstance(searcher, HybridSearcher):
        results = searcher.search(
            query=query,
            k=k,
            search_mode=actual_search_mode,
            min_bm25_score=0.1,
            use_parallel=get_config().performance.use_parallel_search,
            filters=filters if filters else None,
            config=search_config,  # Pass config with ego-graph settings
        )
    else:
        context_depth = 1 if include_context else 0
        results = searcher.search(
            query=query,
            k=k,
            search_mode=actual_search_mode,
            context_depth=context_depth,
            filters=filters if filters else None,
        )

    # Format search results
    formatted_results = _format_search_results(results)

    # Enrich results with call graph data
    index_manager = _get_index_manager_from_searcher(searcher)
    formatted_results = _enrich_results_with_graph_data(
        formatted_results, index_manager
    )

    # === SSCG Phase 3: Centrality annotation/reranking ===
    centrality_scores = None
    if search_config is None:
        search_config = get_search_config()
    graph_config = getattr(search_config, "graph_enhanced", None)

    if (
        graph_config
        and graph_config.centrality_annotation
        and index_manager
        and index_manager.graph_storage
    ):
        try:
            from graph.graph_queries import GraphQueryEngine
            from search.centrality_ranker import CentralityRanker

            graph_query_engine = GraphQueryEngine(index_manager.graph_storage)
            ranker = CentralityRanker(
                graph_query_engine=graph_query_engine,
                method=graph_config.centrality_method,
                alpha=graph_config.centrality_alpha,
            )

            # Compute centrality scores for subgraph population
            centrality_scores = ranker._get_centrality_scores()

            # Rerank results by blended score if enabled in config
            if graph_config.centrality_reranking:
                formatted_results = ranker.rerank(formatted_results)
                logger.debug(
                    f"[SSCG Phase 3] Reranked {len(formatted_results)} results by centrality"
                )
            else:
                formatted_results = ranker.annotate(formatted_results)
                logger.debug(
                    f"[SSCG Phase 3] Annotated {len(formatted_results)} results with centrality"
                )
        except Exception as e:
            logger.debug(f"[SSCG Phase 3] Centrality ranking failed: {e}")

    # === SSCG Phase 1: Extract subgraph over search results ===
    subgraph_data = None
    if index_manager and index_manager.graph_storage is not None:
        try:
            from search.subgraph_extractor import SubgraphExtractor

            extractor = SubgraphExtractor(index_manager.graph_storage)
            # Extract top-k search result chunk_ids
            result_chunk_ids = [
                r["chunk_id"] for r in formatted_results[:k] if "chunk_id" in r
            ]

            # SSCG Phase 5: Collect ego-graph neighbor chunk_ids (if present)
            ego_neighbor_ids = [
                r["chunk_id"]
                for r in formatted_results[k:]
                if r.get("source") == "ego_graph" and "chunk_id" in r
            ]

            # Cap ego-graph neighbors in subgraph to limit output size (defensive)
            MAX_EGO_IN_SUBGRAPH = 10
            if ego_neighbor_ids and len(ego_neighbor_ids) > MAX_EGO_IN_SUBGRAPH:
                ego_neighbor_ids = ego_neighbor_ids[:MAX_EGO_IN_SUBGRAPH]

            if result_chunk_ids:
                subgraph = extractor.extract_subgraph(
                    result_chunk_ids,
                    include_boundary_edges=True,
                    centrality_scores=centrality_scores,
                    ego_neighbor_ids=ego_neighbor_ids if ego_neighbor_ids else None,
                )
                # Include subgraph if there are nodes (boundary edges provide structural context)
                if subgraph.nodes:
                    subgraph_data = subgraph.to_dict()
                    ego_count = len(ego_neighbor_ids) if ego_neighbor_ids else 0
                    logger.debug(
                        f"[SSCG] Extracted subgraph: {len(subgraph.nodes)} nodes "
                        f"({ego_count} ego-graph neighbors), {len(subgraph.edges)} edges"
                    )
                else:
                    logger.info(
                        f"[SSCG] No graph nodes found for {len(result_chunk_ids)} chunk_ids"
                    )
        except Exception as e:
            logger.debug(f"[SSCG] Subgraph extraction failed: {e}")

    # Build response
    response = {"query": query, "results": formatted_results}
    # Flatten subgraph to top-level keys for ultra format TOON conversion
    if subgraph_data:
        response["subgraph_nodes"] = subgraph_data["nodes"]
        response["subgraph_edges"] = subgraph_data["edges"]
        if subgraph_data.get("topology_order"):
            response["subgraph_order"] = subgraph_data["topology_order"]
        if subgraph_data.get("communities"):
            response["subgraph_communities"] = subgraph_data["communities"]

    # Only include routing info when useful for debugging:
    # - Skip for explicit user overrides (they know what they picked)
    # - Skip for high-confidence routing (>= 0.9, expected behavior)
    # - Include for low confidence (< 0.9) or fallback scenarios
    if routing_info:
        confidence = routing_info.get("confidence", 0.0)
        reason = routing_info.get("reason", "")

        # Include routing info if:
        # - Low confidence routing (< 0.9) - might need review
        # - Fallback scenarios - user should know routing failed
        if confidence < 0.9 or "Fallback" in reason or "routed" in reason.lower():
            response["routing"] = routing_info

    # Add AI guidance system message
    response = add_system_message(
        response, tool_name="search_code", query=query, chunk_id=None
    )

    return response


@error_handler("Find similar")
async def handle_find_similar_code(arguments: dict[str, Any]) -> dict:
    """Find code chunks similar to a reference chunk."""
    chunk_id = arguments["chunk_id"]
    k = arguments.get("k", 5)

    # Normalize chunk_id path separators
    # Use CodeIndexManager's normalize_chunk_id for proper cross-platform handling
    if chunk_id:
        chunk_id = MetadataStore.normalize_chunk_id(chunk_id)

    # Early validation: Check if a project is indexed
    if not get_state().current_project:
        return {
            "error": "No indexed project found",
            "message": "You must index a project before finding similar code. Use index_directory first.",
            "current_project": None,
        }

    searcher = get_searcher()

    # Simple implementation - delegate to searcher
    results = searcher.find_similar_to_chunk(chunk_id, k=k)

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

    # Early validation: Check if a project is indexed
    if not get_state().current_project:
        return {
            "error": "No indexed project found",
            "message": "You must index a project before analyzing connections. Use index_directory first.",
            "current_project": None,
        }

    # Get searcher
    searcher = get_searcher()

    # Create analyzer
    analyzer = CodeRelationshipAnalyzer(searcher)

    # Run analysis - raises ValueError for validation errors
    report = analyzer.analyze_impact(
        chunk_id=chunk_id,
        symbol_name=symbol_name,
        max_depth=max_depth,
        exclude_dirs=exclude_dirs,
        relationship_types=relationship_types,
    )

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
async def handle_find_path(arguments: dict[str, Any]) -> dict:
    """Find shortest path between two code entities."""
    # Extract parameters
    source = arguments.get("source")
    target = arguments.get("target")
    source_chunk_id = arguments.get("source_chunk_id")
    target_chunk_id = arguments.get("target_chunk_id")
    max_hops = arguments.get("max_hops", 10)
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

    # Check project indexed
    if not get_state().current_project:
        return {
            "error": "No indexed project found",
            "message": "You must index a project before finding paths. Use index_directory first.",
        }

    # Normalize chunk_ids
    if source_chunk_id:
        source_chunk_id = MetadataStore.normalize_chunk_id(source_chunk_id)
    if target_chunk_id:
        target_chunk_id = MetadataStore.normalize_chunk_id(target_chunk_id)

    # Get searcher and graph
    searcher = get_searcher()

    # Resolve symbol names to chunk_ids if needed
    resolved_source = source_chunk_id
    resolved_target = target_chunk_id
    source_info = None
    target_info = None

    if not resolved_source and source:
        # Try direct symbol lookup first (O(1) from secondary symbol index)
        index_manager = _get_index_manager_from_searcher(searcher)
        if (
            index_manager
            and hasattr(index_manager, "symbol_cache")
            and index_manager.symbol_cache
        ):
            resolved_source = index_manager.symbol_cache.get_by_symbol_name(source)
            if resolved_source:
                source_info = {
                    "resolved_from": source,
                    "chunk_id": resolved_source,
                    "resolution_method": "direct_lookup",
                }

        # Fall back to semantic search if direct lookup failed
        if not resolved_source:
            results = searcher.search(source, k=1)
            if results:
                resolved_source = results[0].chunk_id
                source_info = {
                    "resolved_from": source,
                    "chunk_id": resolved_source,
                    "resolution_method": "semantic_search",
                }
            else:
                return {
                    "path_found": False,
                    "error": f"Could not resolve source symbol: {source}",
                }

    if not resolved_target and target:
        # Try direct symbol lookup first (O(1) from secondary symbol index)
        index_manager = _get_index_manager_from_searcher(searcher)
        if (
            index_manager
            and hasattr(index_manager, "symbol_cache")
            and index_manager.symbol_cache
        ):
            resolved_target = index_manager.symbol_cache.get_by_symbol_name(target)
            if resolved_target:
                target_info = {
                    "resolved_from": target,
                    "chunk_id": resolved_target,
                    "resolution_method": "direct_lookup",
                }

        # Fall back to semantic search if direct lookup failed
        if not resolved_target:
            results = searcher.search(target, k=1)
            if results:
                resolved_target = results[0].chunk_id
                target_info = {
                    "resolved_from": target,
                    "chunk_id": resolved_target,
                    "resolution_method": "semantic_search",
                }
            else:
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

    result = query_engine.find_path(
        source_id=resolved_source,
        target_id=resolved_target,
        max_hops=max_hops,
        edge_types=edge_types,
    )

    if result is None:
        # Get node info for error message
        source_node = graph_storage.get_node_data(resolved_source)
        target_node = graph_storage.get_node_data(resolved_target)

        response = {
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
        response = result
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
