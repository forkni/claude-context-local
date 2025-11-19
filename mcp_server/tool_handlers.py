"""Tool handlers for low-level MCP server.

Converted from FastMCP @mcp.tool() decorators to async handlers.
All tool implementations preserve the original business logic.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

# Import dependencies
from chunking.multi_language_chunker import MultiLanguageChunker

# Import guidance and tools
from mcp_server.guidance import add_system_message

# Import server globals and helpers
from mcp_server.server import (
    MODEL_POOL_CONFIG,
    _cleanup_previous_resources,
    _current_project,
    _embedders,
    _multi_model_enabled,
    get_embedder,
    get_index_manager,
    get_project_storage_dir,
    get_searcher,
    get_storage_dir,
)
from mcp_server.tools.code_relationship_analyzer import CodeRelationshipAnalyzer
from search.config import (
    MODEL_REGISTRY,
    SearchConfigManager,
    get_config_manager,
    get_search_config,
)
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
from search.query_router import QueryRouter

logger = logging.getLogger(__name__)


# ============================================================================
# SIMPLE TOOLS (No complex dependencies)
# ============================================================================


async def handle_get_index_status(arguments: Dict[str, Any]) -> dict:
    """Get current status and statistics of the search index."""
    try:
        index_manager = get_index_manager()
        stats = index_manager.get_stats()

        # Collect model info
        model_info = {}
        if _multi_model_enabled:
            loaded_models = []
            for model_key, embedder in _embedders.items():
                if embedder is not None:
                    info = embedder.get_model_info()
                    info["model_key"] = model_key
                    loaded_models.append(info)
            model_info = {
                "multi_model_mode": True,
                "loaded_models": loaded_models,
                "total_loaded": len(loaded_models),
            }
        else:
            if "default" in _embedders and _embedders["default"] is not None:
                model_info = _embedders["default"].get_model_info()
                model_info["multi_model_mode"] = False

        return {
            "index_statistics": stats,
            "model_information": model_info,
            "storage_directory": str(get_storage_dir()),
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_list_projects(arguments: Dict[str, Any]) -> dict:
    """List all indexed projects grouped by path with model details."""
    try:
        base_dir = get_storage_dir()
        projects_dir = base_dir / "projects"

        if not projects_dir.exists():
            return {
                "projects": [],
                "total_projects": 0,
                "total_indices": 0,
                "message": "No projects indexed yet",
            }

        # Group projects by path
        projects_by_path = {}  # project_path -> project_data

        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            info_file = project_dir / "project_info.json"
            if not info_file.exists():
                continue

            with open(info_file) as f:
                project_info = json.load(f)

            project_path = project_info["project_path"]

            # Initialize project entry if first time seeing this path
            if project_path not in projects_by_path:
                projects_by_path[project_path] = {
                    "project_name": project_info["project_name"],
                    "project_path": project_path,
                    "project_hash": project_info["project_hash"],
                    "models_indexed": [],
                }

            # Prepare model info
            model_info = {
                "model": project_info["embedding_model"],
                "dimension": project_info["model_dimension"],
                "chunks": None,
                "created_at": project_info.get("created_at"),
            }

            # Try to load chunk count from stats
            stats_file = project_dir / "index" / "stats.json"
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                    model_info["chunks"] = stats.get("total_chunks", 0)

            projects_by_path[project_path]["models_indexed"].append(model_info)

        # Convert to list
        projects = list(projects_by_path.values())
        total_indices = sum(len(p["models_indexed"]) for p in projects)

        return {
            "projects": projects,
            "total_projects": len(projects),
            "total_indices": total_indices,
            "current_project": _current_project,
        }
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        return {"error": str(e)}


async def handle_get_memory_status(arguments: Dict[str, Any]) -> dict:
    """Get current memory usage status."""
    try:
        import psutil
        import torch

        # System memory
        mem = psutil.virtual_memory()
        system_memory = {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "used_gb": round(mem.used / (1024**3), 2),
            "percent": mem.percent,
        }

        # GPU memory
        gpu_memory = {}
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(i) / (1024**3)
                reserved = torch.cuda.memory_reserved(i) / (1024**3)
                gpu_memory[f"gpu_{i}"] = {
                    "allocated_gb": round(allocated, 2),
                    "reserved_gb": round(reserved, 2),
                }

        # Index memory estimate
        index_memory = {}
        try:
            index_manager = get_index_manager()
            if index_manager and index_manager.index:
                ntotal = index_manager.index.ntotal
                dimension = index_manager.index.d
                # Rough estimate: 4 bytes per float
                estimated_mb = (ntotal * dimension * 4) / (1024**2)
                index_memory = {
                    "vectors": ntotal,
                    "dimension": dimension,
                    "estimated_mb": round(estimated_mb, 2),
                }
        except Exception:
            pass

        return {
            "system_memory": system_memory,
            "gpu_memory": gpu_memory if gpu_memory else {"status": "No GPU available"},
            "index_memory": (
                index_memory if index_memory else {"status": "No index loaded"}
            ),
        }
    except Exception as e:
        logger.error(f"Memory status check failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_cleanup_resources(arguments: Dict[str, Any]) -> dict:
    """Manually cleanup all resources to free memory."""
    try:
        _cleanup_previous_resources()
        return {"success": True, "message": "Resources cleaned up successfully"}
    except Exception as e:
        logger.error(f"Resource cleanup failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_get_search_config_status(arguments: Dict[str, Any]) -> dict:
    """Get current search configuration status."""
    try:
        config = get_search_config()
        return {
            "search_mode": "hybrid" if config.enable_hybrid_search else "semantic",
            "bm25_weight": config.bm25_weight,
            "dense_weight": config.dense_weight,
            "rrf_k": config.rrf_k_parameter,
            "use_parallel": config.use_parallel_search,
            "embedding_model": config.embedding_model_name,
            "multi_model_enabled": _multi_model_enabled,
        }
    except Exception as e:
        logger.error(f"Config status check failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_list_embedding_models(arguments: Dict[str, Any]) -> dict:
    """List all available embedding models."""
    try:
        models = []
        for model_name, config in MODEL_REGISTRY.items():
            models.append(
                {
                    "name": model_name,
                    "dimension": config["dimension"],
                    "description": config.get("description", ""),
                    "recommended_batch_size": config.get("recommended_batch_size", 128),
                }
            )

        return {
            "models": models,
            "count": len(models),
            "current_model": get_search_config().embedding_model_name,
        }
    except Exception as e:
        logger.error(f"List models failed: {e}", exc_info=True)
        return {"error": str(e)}


# ============================================================================
# MEDIUM TOOLS (State mutation)
# ============================================================================


async def handle_switch_project(arguments: Dict[str, Any]) -> dict:
    """Switch to a different indexed project."""
    project_path = arguments["project_path"]

    try:
        global _current_project, _index_manager, _searcher

        project_path = Path(project_path).resolve()
        if not project_path.exists():
            return {"error": f"Project path does not exist: {project_path}"}

        # Cleanup previous resources
        _cleanup_previous_resources()

        # Set new project
        _current_project = str(project_path)

        # Verify project is indexed
        project_dir = get_project_storage_dir(str(project_path))
        index_dir = project_dir / "index"

        if not index_dir.exists() or not (index_dir / "code.index").exists():
            return {
                "success": True,
                "project": str(project_path),
                "warning": "Project not indexed yet. Run index_directory first.",
                "indexed": False,
            }

        return {
            "success": True,
            "project": str(project_path),
            "indexed": True,
            "message": f"Switched to project: {project_path.name}",
        }
    except Exception as e:
        logger.error(f"Project switch failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_clear_index(arguments: Dict[str, Any]) -> dict:
    """Clear the entire search index."""
    try:
        if _current_project is None:
            return {"error": "No active project to clear"}

        index_manager = get_index_manager()
        index_manager.clear_index()

        # Cleanup in-memory state
        global _index_manager, _searcher
        _index_manager = None
        _searcher = None

        return {
            "success": True,
            "message": f"Index cleared for project: {Path(_current_project).name}",
        }
    except Exception as e:
        logger.error(f"Clear index failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_configure_query_routing(arguments: Dict[str, Any]) -> dict:
    """Configure query routing behavior."""
    enable_multi_model = arguments.get("enable_multi_model")
    default_model = arguments.get("default_model")
    confidence_threshold = arguments.get("confidence_threshold")

    try:
        config_manager = get_config_manager()
        config_manager.load_config()

        if enable_multi_model is not None:
            # This would require restarting the server to take effect
            return {
                "warning": "multi_model_enabled requires server restart",
                "current_value": _multi_model_enabled,
                "message": "Set CLAUDE_MULTI_MODEL_ENABLED environment variable",
            }

        changes = {}
        if default_model is not None:
            if default_model in MODEL_POOL_CONFIG:
                changes["default_model"] = default_model
            else:
                return {"error": f"Invalid model: {default_model}"}

        if confidence_threshold is not None:
            changes["confidence_threshold"] = confidence_threshold

        return {
            "success": True,
            "changes": changes,
            "message": "Configuration updated (some changes may require restart)",
        }
    except Exception as e:
        logger.error(f"Configure routing failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_configure_search_mode(arguments: Dict[str, Any]) -> dict:
    """Configure search mode and parameters."""
    search_mode = arguments.get("search_mode", "hybrid")
    bm25_weight = arguments.get("bm25_weight", 0.4)
    dense_weight = arguments.get("dense_weight", 0.6)
    enable_parallel = arguments.get("enable_parallel", True)

    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()

        # Update config
        if search_mode in ["hybrid", "semantic", "bm25", "auto"]:
            config.enable_hybrid_search = search_mode in ["hybrid", "auto"]
            config.bm25_weight = bm25_weight
            config.dense_weight = dense_weight
            config.use_parallel_search = enable_parallel

            config_manager.save_config(config)

            # Reset searcher to pick up new config
            global _searcher
            _searcher = None

            return {
                "success": True,
                "config": {
                    "search_mode": search_mode,
                    "bm25_weight": bm25_weight,
                    "dense_weight": dense_weight,
                    "enable_parallel": enable_parallel,
                },
            }
        else:
            return {"error": f"Invalid search_mode: {search_mode}"}
    except Exception as e:
        logger.error(f"Configure search mode failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_switch_embedding_model(arguments: Dict[str, Any]) -> dict:
    """Switch to a different embedding model."""
    model_name = arguments["model_name"]

    try:
        if model_name not in MODEL_REGISTRY:
            return {
                "error": f"Unknown model: {model_name}",
                "available_models": list(MODEL_REGISTRY.keys()),
            }

        config_manager = get_config_manager()
        config = config_manager.load_config()
        old_model = config.embedding_model_name

        config.embedding_model_name = model_name
        config_manager.save_config(config)

        # Reset embedders to force reload
        global _embedders, _index_manager, _searcher
        _embedders.clear()
        _index_manager = None
        _searcher = None

        return {
            "success": True,
            "old_model": old_model,
            "new_model": model_name,
            "message": f"Switched to {model_name}. Indexes will use this model.",
            "note": "Existing indices for other models are preserved (per-model storage)",
        }
    except Exception as e:
        logger.error(f"Switch model failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_find_similar_code(arguments: Dict[str, Any]) -> dict:
    """Find code chunks similar to a reference chunk."""
    chunk_id = arguments["chunk_id"]
    k = arguments.get("k", 5)

    # Normalize chunk_id path separators
    # Un-double-escape first (MCP JSON transport), then normalize to forward slashes
    if chunk_id:
        chunk_id = chunk_id.replace("\\\\", "\\").replace("\\", "/")

    try:
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
    except Exception as e:
        logger.error(f"Find similar failed: {e}", exc_info=True)
        return {"error": str(e)}


# ============================================================================
# COMPLEX TOOLS (Multi-step workflows)
# ============================================================================


async def handle_search_code(arguments: Dict[str, Any]) -> dict:
    """Search code with natural language query - MOST COMPLEX TOOL."""
    # Extract all arguments
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

    # FAST PATH: Direct chunk_id lookup (no search needed)
    if chunk_id:
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

            # Format SearchResult to JSON-serializable dict
            formatted_result = {
                "file": result.metadata.get("file", ""),
                "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
                "kind": result.metadata.get("chunk_type", "unknown"),
                "score": round(result.score, 2),
                "chunk_id": result.chunk_id,
            }

            # Add graph data if available
            index_manager = None
            if hasattr(searcher, "index_manager"):
                index_manager = searcher.index_manager
            elif hasattr(searcher, "dense_index"):
                index_manager = searcher.dense_index

            if index_manager and index_manager.graph_storage is not None:
                try:
                    calls = index_manager.graph_storage.get_callees(chunk_id)
                    called_by = index_manager.graph_storage.get_callers(chunk_id)

                    if calls or called_by:
                        formatted_result["graph"] = {
                            "calls": calls if calls else [],
                            "called_by": called_by if called_by else [],
                        }
                except Exception as e:
                    logger.debug(f"Failed to get graph data for {chunk_id}: {e}")

            # Convert single result to list format
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

    # NORMAL PATH: Search by query
    search_mode = arguments.get("search_mode", "auto")
    file_pattern = arguments.get("file_pattern")
    chunk_type = arguments.get("chunk_type")
    include_context = arguments.get("include_context", True)
    auto_reindex = arguments.get("auto_reindex", True)
    max_age_minutes = arguments.get("max_age_minutes", 5)
    use_routing = arguments.get("use_routing", True)
    model_key = arguments.get("model_key")

    logger.info(f"[SEARCH] query='{query}', k={k}, mode='{search_mode}'")

    try:
        # Phase 1: Model Routing
        selected_model_key = None
        routing_info = None

        if _multi_model_enabled and use_routing and model_key is None:
            router = QueryRouter(enable_logging=True)
            decision = router.route(query)
            selected_model_key = decision.model_key
            routing_info = {
                "model_selected": decision.model_key,
                "confidence": decision.confidence,
                "reason": decision.reason,
                "scores": decision.scores,
            }
        elif model_key is not None:
            selected_model_key = model_key
            routing_info = {
                "model_selected": model_key,
                "confidence": 1.0,
                "reason": "User-specified override",
            }

        # Phase 2: Auto-reindex if needed
        if auto_reindex and _current_project:
            config = get_search_config()
            if config.enable_hybrid_search:
                project_storage = get_project_storage_dir(_current_project)
                storage_dir = project_storage / "index"
                indexer = HybridSearcher(
                    storage_dir=str(storage_dir),
                    embedder=get_embedder(selected_model_key),
                    bm25_weight=config.bm25_weight,
                    dense_weight=config.dense_weight,
                )
            else:
                indexer = get_index_manager(_current_project)

            embedder = get_embedder(selected_model_key)
            chunker = MultiLanguageChunker(_current_project)
            incremental_indexer = IncrementalIndexer(
                indexer=indexer, embedder=embedder, chunker=chunker
            )

            reindex_result = incremental_indexer.auto_reindex_if_needed(
                _current_project, max_age_minutes=max_age_minutes
            )

            if reindex_result.files_modified > 0 or reindex_result.files_added > 0:
                global _searcher
                _searcher = None

        # Phase 3: Execute search (pass routing decision to get correct model index)
        searcher = get_searcher(model_key=selected_model_key)

        # Check if index ready
        total_chunks = 0
        if hasattr(searcher, "index_manager"):
            stats = searcher.index_manager.get_stats()
            total_chunks = stats.get("total_chunks", 0)
        elif hasattr(searcher, "get_stats"):
            stats = searcher.get_stats()
            total_chunks = stats.get("total_chunks", 0)

        if total_chunks == 0:
            return {
                "error": "No indexed project found",
                "message": "You must index a project before searching",
                "current_project": _current_project or "None",
            }

        # Build filters
        filters = {}
        if file_pattern:
            filters["file_pattern"] = [file_pattern]
        if chunk_type:
            filters["chunk_type"] = chunk_type

        # Perform search
        config_manager = get_config_manager()
        actual_search_mode = config_manager.get_search_mode_for_query(
            query, search_mode
        )

        if isinstance(searcher, HybridSearcher):
            results = searcher.search(
                query=query,
                k=k,
                search_mode=actual_search_mode,
                min_bm25_score=0.1,
                use_parallel=get_search_config().use_parallel_search,
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

        # Phase 4: Format results
        formatted_results = []
        for result in results:
            if hasattr(result, "relative_path"):
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
                item = {
                    "file": result.metadata.get("relative_path", ""),
                    "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
                    "kind": result.metadata.get("chunk_type", "unknown"),
                    "score": round(result.score, 2),
                    "chunk_id": result.chunk_id,
                }

            formatted_results.append(item)

        # Phase 5: Enrich with graph data
        index_manager = None
        if hasattr(searcher, "index_manager"):
            index_manager = searcher.index_manager
        elif hasattr(searcher, "dense_index"):
            index_manager = searcher.dense_index

        if index_manager and index_manager.graph_storage is not None:
            for item in formatted_results:
                chunk_id = item.get("chunk_id")
                if chunk_id:
                    try:
                        calls = index_manager.graph_storage.get_callees(chunk_id)
                        called_by = index_manager.graph_storage.get_callers(chunk_id)

                        if calls or called_by:
                            item["graph"] = {
                                "calls": calls if calls else [],
                                "called_by": called_by if called_by else [],
                            }
                    except Exception as e:
                        logger.debug(f"Failed to get graph data for {chunk_id}: {e}")

        # Build response
        response = {"query": query, "results": formatted_results}

        if routing_info:
            response["routing"] = routing_info

        # Add AI guidance system message
        response = add_system_message(
            response, tool_name="search_code", query=query, chunk_id=None
        )

        return response

    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_index_directory(arguments: Dict[str, Any]) -> dict:
    """Index a directory for code search with multi-model support."""
    directory_path = arguments["directory_path"]
    arguments.get("project_name")
    incremental = arguments.get("incremental", True)
    multi_model = arguments.get("multi_model", None)  # None = auto-detect

    # Auto-detect multi-model mode if not explicitly specified
    if multi_model is None:
        multi_model = _multi_model_enabled

    logger.info(
        f"[INDEX] directory={directory_path}, incremental={incremental}, multi_model={multi_model}"
    )

    try:
        from datetime import datetime

        directory_path = Path(directory_path).resolve()
        if not directory_path.exists():
            return {"error": f"Directory does not exist: {directory_path}"}

        # Set as current project
        global _current_project
        _current_project = str(directory_path)

        # Multi-model batch indexing
        if multi_model and _multi_model_enabled:
            logger.info(f"Multi-model batch indexing for: {directory_path}")

            results = []
            original_config = get_search_config()
            original_model = original_config.embedding_model_name

            # Clear global state for clean model switching
            global _index_manager, _searcher

            try:
                for model_key, model_name in MODEL_POOL_CONFIG.items():
                    logger.info(f"Indexing with model: {model_name} ({model_key})")

                    # Switch to this model temporarily
                    config_mgr = SearchConfigManager()
                    config = config_mgr.load_config()
                    config.embedding_model_name = model_name

                    # Update dimension from registry
                    if model_name in MODEL_REGISTRY:
                        config.model_dimension = MODEL_REGISTRY[model_name]["dimension"]

                    config_mgr.save_config(config)

                    # Invalidate global config cache to force reload from disk
                    # This ensures get_project_storage_dir() sees the updated model
                    from search import config as config_module

                    config_module._config_manager = None

                    # Clear cached components to force reload with new model
                    global _index_manager, _searcher
                    _index_manager = None
                    _searcher = None

                    # Get project storage for this model
                    project_dir = get_project_storage_dir(str(directory_path))
                    index_dir = project_dir / "index"
                    index_dir.mkdir(exist_ok=True)

                    # Initialize components for this model
                    chunker = MultiLanguageChunker(str(directory_path))
                    embedder = get_embedder(
                        model_key
                    )  # Get embedder for specific model

                    # Create fresh indexer instance directly (bypass global cache)
                    # This ensures the storage path is correct for the current model
                    config = get_search_config()
                    if config.enable_hybrid_search:
                        # Create fresh HybridSearcher with correct storage path
                        storage_dir = index_dir  # Already set on line 721
                        project_id = project_dir.name.rsplit("_", 1)[
                            0
                        ]  # Remove dimension suffix

                        indexer = HybridSearcher(
                            storage_dir=str(storage_dir),
                            embedder=embedder,
                            bm25_weight=config.bm25_weight,
                            dense_weight=config.dense_weight,
                            rrf_k=config.rrf_k_parameter,
                            max_workers=2,
                            bm25_use_stopwords=config.bm25_use_stopwords,
                            bm25_use_stemming=config.bm25_use_stemming,
                            project_id=project_id,
                        )
                        logger.info(
                            f"Created fresh HybridSearcher for {model_name} at {storage_dir}"
                        )
                    else:
                        # Create fresh CodeIndexManager with correct storage path
                        project_id = project_dir.name.rsplit("_", 1)[
                            0
                        ]  # Remove dimension suffix
                        indexer = CodeIndexManager(
                            str(index_dir), project_id=project_id
                        )
                        logger.info(
                            f"Created fresh CodeIndexManager for {model_name} at {index_dir}"
                        )

                    # Create incremental indexer with fresh components
                    incremental_indexer = IncrementalIndexer(
                        indexer=indexer, embedder=embedder, chunker=chunker
                    )

                    # Index with this model
                    start_time = datetime.now()

                    if incremental:
                        result = incremental_indexer.incremental_index(
                            str(directory_path)
                        )
                    else:
                        result = incremental_indexer.incremental_index(
                            str(directory_path), force_full=True
                        )

                    elapsed = (datetime.now() - start_time).total_seconds()

                    results.append(
                        {
                            "model": model_name,
                            "model_key": model_key,
                            "dimension": config.model_dimension,
                            "files_added": result.files_added,
                            "files_modified": result.files_modified,
                            "files_removed": result.files_removed,
                            "chunks_added": result.chunks_added,
                            "time_taken": round(elapsed, 2),
                        }
                    )

                    logger.info(
                        f"Completed indexing with {model_name} in {elapsed:.2f}s"
                    )

            finally:
                # Restore original model
                config_mgr = SearchConfigManager()
                config = config_mgr.load_config()
                config.embedding_model_name = original_model
                config_mgr.save_config(config)

                # Clear cached components
                _index_manager = None
                _searcher = None

                logger.info(f"Restored original model: {original_model}")

            # Calculate totals
            total_time = sum(r["time_taken"] for r in results)
            total_files_added = sum(r["files_added"] for r in results)
            total_chunks_added = sum(r["chunks_added"] for r in results)

            return {
                "success": True,
                "multi_model": True,
                "project": str(directory_path),
                "models_indexed": len(results),
                "results": results,
                "total_time": round(total_time, 2),
                "total_files_added": total_files_added,
                "total_chunks_added": total_chunks_added,
                "mode": "incremental" if incremental else "full",
            }

        # Single model indexing (original behavior)
        else:
            logger.info(f"Single-model indexing for: {directory_path}")

            # Get or create project storage
            project_dir = get_project_storage_dir(str(directory_path))
            index_dir = project_dir / "index"
            index_dir.mkdir(exist_ok=True)

            # Initialize components
            chunker = MultiLanguageChunker(str(directory_path))
            embedder = get_embedder()

            # Get index manager
            searcher_instance = get_searcher(str(directory_path))

            config = get_search_config()
            if config.enable_hybrid_search:
                indexer = searcher_instance
            else:
                indexer = get_index_manager(str(directory_path))

            # Create incremental indexer
            incremental_indexer = IncrementalIndexer(
                indexer=indexer, embedder=embedder, chunker=chunker
            )

            # Index the directory
            start_time = datetime.now()

            if incremental:
                result = incremental_indexer.incremental_index(str(directory_path))
            else:
                result = incremental_indexer.incremental_index(
                    str(directory_path), force_full=True
                )

            elapsed = (datetime.now() - start_time).total_seconds()

            return {
                "success": True,
                "multi_model": False,
                "project": str(directory_path),
                "files_added": result.files_added,
                "files_modified": result.files_modified,
                "files_removed": result.files_removed,
                "chunks_added": result.chunks_added,
                "time_taken": round(elapsed, 2),
                "mode": "incremental" if incremental else "full",
            }

    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_find_connections(arguments: Dict[str, Any]) -> dict:
    """Find all code connections to a given symbol."""
    chunk_id = arguments.get("chunk_id")
    symbol_name = arguments.get("symbol_name")
    max_depth = arguments.get("max_depth", 3)

    # Validate inputs
    if not chunk_id and not symbol_name:
        return {
            "error": "Missing required parameter",
            "message": "Provide either chunk_id or symbol_name",
        }

    # Normalize chunk_id path separators (defense-in-depth)
    # Fixes Issue 2: Ensures Windows backslash paths work correctly
    # Un-double-escape first (MCP JSON transport), then normalize to forward slashes
    if chunk_id:
        chunk_id = chunk_id.replace("\\\\", "\\").replace("\\", "/")

    logger.info(
        f"[FIND_CONNECTIONS] chunk_id={chunk_id}, symbol_name={symbol_name}, depth={max_depth}"
    )

    try:
        # Get searcher
        searcher = get_searcher()

        # Create analyzer
        analyzer = CodeRelationshipAnalyzer(searcher)

        # Run analysis
        report = analyzer.analyze_impact(
            chunk_id=chunk_id, symbol_name=symbol_name, max_depth=max_depth
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

    except ValueError as e:
        logger.warning(f"Impact analysis validation error: {e}")
        return {
            "error": "Validation error",
            "message": str(e),
            "chunk_id": chunk_id,
            "symbol_name": symbol_name,
        }
    except Exception as e:
        logger.error(f"Impact analysis failed: {e}", exc_info=True)
        return {"error": str(e), "chunk_id": chunk_id, "symbol_name": symbol_name}
