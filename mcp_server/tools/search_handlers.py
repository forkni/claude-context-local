"""Search and query tool handlers for MCP server.

Handlers for code search, similarity finding, and connection analysis.
"""

import asyncio
import logging
from typing import Any

from chunking.multi_language_chunker import MultiLanguageChunker
from mcp_server.guidance import add_system_message
from mcp_server.model_pool_manager import get_embedder
from mcp_server.search_factory import (
    get_index_manager,
    get_searcher,
)
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import get_project_storage_dir
from mcp_server.tools import responses
from mcp_server.tools.decorators import error_handler, require_indexed_project
from mcp_server.tools.search_orchestrator import SearchOrchestrator
from mcp_server.utils.config_helpers import temporary_ram_fallback_off
from search.exceptions import DimensionMismatchError
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
from search.metadata import MetadataStore
from search.relationship_analyzer import RelationshipAnalyzer


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Search Code Helper Functions
# ----------------------------------------------------------------------------


def _check_auto_reindex(project_path: str, max_age_minutes: int) -> tuple[bool, None]:
    """Check if auto-reindex is needed and perform if necessary.

    Args:
        project_path: Path to the project
        max_age_minutes: Maximum age of index before reindex

    Returns:
        Tuple of (reindexed: bool, None)
        - reindexed: True if reindex was performed
    """
    # Load filters from project_info.json to ensure consistent filtering
    import json

    project_storage = get_project_storage_dir(project_path)
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
        except Exception as e:  # noqa: BLE001 - parse-recovery: project_info.json read, fall back to no filters
            logger.warning(f"[AUTO_REINDEX] Failed to load filters: {e}")

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
            return False, None

    # Phase 2: Index is stale — create full machinery and reindex
    logger.debug(
        "[AUTO_REINDEX] Index is stale or missing, proceeding with full reindex check"
    )

    # Validate dimension compatibility BEFORE creating searcher
    from search.dimension_validator import validate_embedder_index_compatibility

    embedder = get_embedder()

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
            bm25_use_stopwords=config.search_mode.bm25_use_stopwords,
            bm25_use_stemming=config.search_mode.bm25_use_stemming,
            project_id=project_id,
            config=config,
        )
        # Track project/model key eagerly (used by downstream get_searcher() routing).
        # Searcher bind is deferred until after auto_reindex_if_needed so we never
        # cache a HybridSearcher whose embedder was just nulled by clear_embedders().
        state = get_state()
        if state.searcher is None or state.current_project != project_path:
            state.current_project = project_path
    else:
        indexer = get_index_manager(project_path)
    # for_project() wires RepositoryRelationFilter so import edges are
    # classified (stdlib/third_party/local) rather than stored as "unknown".
    chunker = MultiLanguageChunker.for_project(
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
        and get_state().searcher is None
        and get_state().embedders.get("default") is embedder
    ):
        get_state().searcher = indexer

    return reindexed, None


def _get_index_manager_from_searcher(searcher) -> CodeIndexManager | None:
    """Extract index_manager from searcher (handles different searcher types).

    Delegates to :class:`~mcp_server.tools.searcher_view.SearcherView`, which
    owns the HybridSearcher/IntelligentSearcher attribute-extraction seam.

    Args:
        searcher: HybridSearcher or IntelligentSearcher instance

    Returns:
        CodeIndexManager or None
    """
    from mcp_server.tools.searcher_view import SearcherView

    return SearcherView(searcher).index_manager


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
    from mcp_server.tools.searcher_view import SearcherView

    gs = SearcherView(searcher).graph_storage
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
            "file": result.metadata.get("relative_path", ""),
            "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
            "kind": result.metadata.get("chunk_type", "unknown"),
            "score": round(result.score, 2),
        }
        if result.metadata.get("name"):
            item["name"] = result.metadata["name"]
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
        return responses.error(
            "Missing required parameter",
            message="Provide either chunk_id or symbol_name",
        )

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
        return responses.error(
            "Missing source",
            message="Provide either source (symbol name) or source_chunk_id",
        )
    if not target and not target_chunk_id:
        return responses.error(
            "Missing target",
            message="Provide either target (symbol name) or target_chunk_id",
        )

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
    from mcp_server.tools.searcher_view import SearcherView

    graph_storage = SearcherView(searcher).graph_storage

    if not graph_storage:
        return responses.error(
            "Graph not available",
            message="Call graph not initialized. Re-index the project.",
        )

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
