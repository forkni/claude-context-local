"""Search and query tool handlers for MCP server.

Handlers for code search, similarity finding, and connection analysis.
"""

import logging
from typing import Any, Dict

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
from search.config import get_config_manager
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
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
    from search.config import MODEL_POOL_CONFIG

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
        for model_key_candidate in MODEL_POOL_CONFIG.keys():
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

    config = get_config()
    if config.search_mode.enable_hybrid:
        storage_dir = project_storage / "index"
        indexer = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=get_embedder(selected_model_key),
            bm25_weight=config.search_mode.bm25_weight,
            dense_weight=config.search_mode.dense_weight,
        )
    else:
        indexer = get_index_manager(project_path, model_key=selected_model_key)

    embedder = get_embedder(selected_model_key)
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


def _get_graph_data_for_chunk(
    index_manager: CodeIndexManager, chunk_id: str
) -> dict | None:
    """Get graph relationship data for a chunk.

    Args:
        index_manager: The index manager with graph storage
        chunk_id: The chunk to get graph data for

    Returns:
        dict with 'calls' and 'called_by' lists, or None
    """
    try:
        calls = index_manager.graph_storage.get_callees(chunk_id)
        called_by = index_manager.graph_storage.get_callers(chunk_id)

        if calls or called_by:
            return {
                "calls": calls if calls else [],
                "called_by": called_by if called_by else [],
            }
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
            if hasattr(result, "name") and result.name:
                item["name"] = result.name
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
        if chunk_id:
            graph_data = _get_graph_data_for_chunk(index_manager, chunk_id)
            if graph_data:
                item["graph"] = graph_data

    return results


# ----------------------------------------------------------------------------
# Main Search Handlers
# ----------------------------------------------------------------------------


@error_handler("Search")
async def handle_search_code(arguments: Dict[str, Any]) -> dict:
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
    k = arguments.get("k", 5)

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
    use_routing = arguments.get("use_routing", True)
    model_key = arguments.get("model_key")

    logger.info(f"[SEARCH] query='{query}', k={k}, mode='{search_mode}'")

    # Route query to optimal embedding model
    selected_model_key, routing_info = _route_query_to_model(
        query, use_routing, model_key
    )

    # Check and perform auto-reindex if index is stale
    current_project = get_state().current_project
    if auto_reindex and current_project:
        reindexed = _check_auto_reindex(
            current_project, selected_model_key, max_age_minutes
        )
        if reindexed:
            get_state().searcher = None

    # Execute search with selected model index
    searcher = get_searcher(model_key=selected_model_key)

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

    if isinstance(searcher, HybridSearcher):
        results = searcher.search(
            query=query,
            k=k,
            search_mode=actual_search_mode,
            min_bm25_score=0.1,
            use_parallel=get_config().performance.use_parallel_search,
            filters=filters if filters else None,
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

    # Build response
    response = {"query": query, "results": formatted_results}
    if routing_info:
        response["routing"] = routing_info

    # Add AI guidance system message
    response = add_system_message(
        response, tool_name="search_code", query=query, chunk_id=None
    )

    return response


@error_handler("Find similar")
async def handle_find_similar_code(arguments: Dict[str, Any]) -> dict:
    """Find code chunks similar to a reference chunk."""
    chunk_id = arguments["chunk_id"]
    k = arguments.get("k", 5)

    # Normalize chunk_id path separators
    # Use CodeIndexManager's normalize_chunk_id for proper cross-platform handling
    if chunk_id:
        chunk_id = MetadataStore.normalize_chunk_id(chunk_id)

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
        "count": len(formatted_results),
    }


@error_handler(
    "Impact analysis",
    error_context=lambda args: {
        "chunk_id": args.get("chunk_id"),
        "symbol_name": args.get("symbol_name"),
    },
)
async def handle_find_connections(arguments: Dict[str, Any]) -> dict:
    """Find all code connections to a given symbol."""
    chunk_id = arguments.get("chunk_id")
    symbol_name = arguments.get("symbol_name")
    max_depth = arguments.get("max_depth", 3)
    exclude_dirs = arguments.get("exclude_dirs")

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
