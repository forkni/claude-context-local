"""Indexing tool handlers for MCP server.

Handlers for creating, updating, and clearing code indices.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from chunking.multi_language_chunker import MultiLanguageChunker
from mcp_server.server import (
    get_embedder,
    get_index_manager,
    get_project_storage_dir,
    get_searcher,
    get_storage_dir,
    set_current_project,
    update_project_filters,
)
from mcp_server.state import get_state
from mcp_server.tools.decorators import error_handler
from search.config import (
    MODEL_POOL_CONFIG,
    MODEL_REGISTRY,
    SearchConfigManager,
    get_search_config,
)
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Index Directory Helper Functions
# ----------------------------------------------------------------------------


def _create_indexer_for_model(
    model_key: str | None, directory_path: str, index_dir: Path
) -> tuple:
    """Create indexer and embedder for a specific model.

    Args:
        model_key: The model key (e.g., 'qwen3', 'bge_m3') or None for default
        directory_path: Path to the project directory
        index_dir: Path to store the index

    Returns:
        tuple: (indexer, embedder, chunker)
    """
    config = get_search_config()
    chunker = MultiLanguageChunker(directory_path)
    embedder = get_embedder(model_key)

    if config.enable_hybrid_search:
        # Get project_id from index_dir parent
        project_dir = index_dir.parent
        project_id = project_dir.name.rsplit("_", 1)[0]  # Remove dimension suffix

        indexer = HybridSearcher(
            storage_dir=str(index_dir),
            embedder=embedder,
            bm25_weight=config.bm25_weight,
            dense_weight=config.dense_weight,
            rrf_k=config.rrf_k_parameter,
            max_workers=2,
            bm25_use_stopwords=config.bm25_use_stopwords,
            bm25_use_stemming=config.bm25_use_stemming,
            project_id=project_id,
        )
    else:
        project_dir = index_dir.parent
        project_id = project_dir.name.rsplit("_", 1)[0]
        indexer = CodeIndexManager(str(index_dir), project_id=project_id)

    return indexer, embedder, chunker


def _run_indexing(
    indexer,
    embedder,
    chunker,
    directory_path: str,
    incremental: bool,
    include_dirs=None,
    exclude_dirs=None,
) -> dict:
    """Run the indexing process and return results.

    Args:
        indexer: HybridSearcher or CodeIndexManager
        embedder: Embedding model
        chunker: Code chunker
        directory_path: Path to index
        incremental: Whether to do incremental indexing
        include_dirs: Optional list of directories to include
        exclude_dirs: Optional list of directories to exclude

    Returns:
        dict: Indexing results with files/chunks counts and timing
    """
    incremental_indexer = IncrementalIndexer(
        indexer=indexer,
        embedder=embedder,
        chunker=chunker,
        include_dirs=include_dirs,
        exclude_dirs=exclude_dirs,
    )

    start_time = datetime.now()

    if incremental:
        result = incremental_indexer.incremental_index(directory_path)
    else:
        result = incremental_indexer.incremental_index(directory_path, force_full=True)

    elapsed = (datetime.now() - start_time).total_seconds()

    return {
        "files_added": result.files_added,
        "files_modified": result.files_modified,
        "files_removed": result.files_removed,
        "chunks_added": result.chunks_added,
        "time_taken": round(elapsed, 2),
    }


def _build_index_response(
    results: list[dict], directory_path: str, multi_model: bool, incremental: bool
) -> dict:
    """Build the final index response.

    Args:
        results: List of per-model indexing results
        directory_path: The indexed directory
        multi_model: Whether multi-model mode was used
        incremental: Whether incremental mode was used

    Returns:
        dict: Complete response with success status and statistics
    """
    if multi_model:
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
    else:
        # Single model - results has one item
        r = results[0]
        return {
            "success": True,
            "multi_model": False,
            "project": str(directory_path),
            "files_added": r["files_added"],
            "files_modified": r["files_modified"],
            "files_removed": r["files_removed"],
            "chunks_added": r["chunks_added"],
            "time_taken": r["time_taken"],
            "mode": "incremental" if incremental else "full",
        }


def _index_with_all_models(
    directory_path: Path, incremental: bool, include_dirs=None, exclude_dirs=None
) -> list[dict]:
    """Index a project with all models in MODEL_POOL_CONFIG.

    Args:
        directory_path: Resolved path to the project directory
        incremental: Whether to use incremental indexing
        include_dirs: Optional list of directories to include
        exclude_dirs: Optional list of directories to exclude

    Returns:
        list: Results for each model with timing and statistics
    """
    results = []
    original_config = get_search_config()
    original_model = original_config.embedding_model_name

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
            from search import config as config_module

            config_module._config_manager = None

            # Clear cached components to force reload with new model
            state = get_state()
            state.reset_search_components()

            # Get project storage for this model
            project_dir = get_project_storage_dir(str(directory_path))
            index_dir = project_dir / "index"
            index_dir.mkdir(exist_ok=True)

            # Initialize components for this model
            chunker = MultiLanguageChunker(
                str(directory_path), include_dirs, exclude_dirs
            )
            embedder = get_embedder(model_key)

            # Create fresh indexer instance directly (bypass global cache)
            config = get_search_config()
            if config.enable_hybrid_search:
                project_id = project_dir.name.rsplit("_", 1)[0]
                indexer = HybridSearcher(
                    storage_dir=str(index_dir),
                    embedder=embedder,
                    bm25_weight=config.bm25_weight,
                    dense_weight=config.dense_weight,
                    rrf_k=config.rrf_k_parameter,
                    max_workers=2,
                    bm25_use_stopwords=config.bm25_use_stopwords,
                    bm25_use_stemming=config.bm25_use_stemming,
                    project_id=project_id,
                )
                logger.info(f"Created HybridSearcher for {model_name} at {index_dir}")
            else:
                project_id = project_dir.name.rsplit("_", 1)[0]
                indexer = CodeIndexManager(str(index_dir), project_id=project_id)
                logger.info(f"Created CodeIndexManager for {model_name} at {index_dir}")

            # Create incremental indexer and run
            incremental_indexer = IncrementalIndexer(
                indexer=indexer,
                embedder=embedder,
                chunker=chunker,
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
            )

            start_time = datetime.now()
            if incremental:
                result = incremental_indexer.incremental_index(str(directory_path))
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
            logger.info(f"Completed indexing with {model_name} in {elapsed:.2f}s")

    finally:
        # Restore original model
        config_mgr = SearchConfigManager()
        config = config_mgr.load_config()
        config.embedding_model_name = original_model
        config_mgr.save_config(config)

        # Clear cached components
        state = get_state()
        state.reset_search_components()
        logger.info(f"Restored original model: {original_model}")

    return results


# ----------------------------------------------------------------------------
# Main Index Handlers
# ----------------------------------------------------------------------------


@error_handler("Clear index")
async def handle_clear_index(arguments: Dict[str, Any]) -> dict:
    """Clear the entire search index for ALL models."""
    import shutil

    state = get_state()
    current_project = state.current_project
    if current_project is None:
        return {"error": "No active project to clear"}

    # Get project info for pattern matching
    project_path = Path(current_project).resolve()
    project_name = project_path.name
    project_hash = hashlib.md5(str(project_path).encode()).hexdigest()[:8]

    # Find ALL model directories for this project
    base_dir = get_storage_dir()
    projects_dir = base_dir / "projects"
    pattern = f"{project_name}_{project_hash}_*"

    cleared_dirs = []
    for model_dir in projects_dir.glob(pattern):
        # Delete BM25 directory
        bm25_dir = model_dir / "index" / "bm25"
        if bm25_dir.exists():
            shutil.rmtree(bm25_dir)
            logger.info(f"Deleted BM25 directory: {bm25_dir}")

        # Delete dense index files
        index_dir = model_dir / "index"
        for file in ["code.index", "chunks_metadata.db"]:
            filepath = index_dir / file
            if filepath.exists():
                filepath.unlink()
                logger.info(f"Deleted: {filepath}")

        cleared_dirs.append(model_dir.name)

    # Cleanup in-memory state
    state.reset_search_components()

    logger.info(f"Cleared indices for {len(cleared_dirs)} models: {cleared_dirs}")

    return {
        "success": True,
        "message": f"Index cleared for project: {project_name}",
        "cleared_models": cleared_dirs,
    }


@error_handler("Index")
async def handle_index_directory(arguments: Dict[str, Any]) -> dict:
    """Index a directory for code search with multi-model support.

    Uses extracted helper functions for clarity:
    - _index_with_all_models(): Multi-model batch indexing
    - _create_indexer_for_model(): Create indexer/embedder for a model
    - _run_indexing(): Execute the indexing process
    - _build_index_response(): Format the final response
    """
    directory_path = arguments["directory_path"]
    arguments.get("project_name")
    incremental = arguments.get("incremental", True)
    multi_model = arguments.get("multi_model", None)  # None = auto-detect
    include_dirs = arguments.get("include_dirs")
    exclude_dirs = arguments.get("exclude_dirs")

    # Auto-detect multi-model mode if not explicitly specified
    if multi_model is None:
        multi_model = get_state().multi_model_enabled

    logger.info(
        f"[INDEX] directory={directory_path}, incremental={incremental}, multi_model={multi_model}"
    )

    directory_path = Path(directory_path).resolve()
    if not directory_path.exists():
        return {"error": f"Directory does not exist: {directory_path}"}

    # Check if project already exists and handle filter immutability
    # First call without filters to check existence
    project_dir = get_project_storage_dir(str(directory_path))
    project_info_file = project_dir / "project_info.json"

    # Load stored filters if project exists
    stored_include = None
    stored_exclude = None
    if project_info_file.exists():
        with open(project_info_file) as f:
            project_info = json.load(f)
        stored_include = project_info.get("include_dirs")
        stored_exclude = project_info.get("exclude_dirs")

    # Determine effective filters
    # If user didn't provide filters, use stored filters (auto-reindex case)
    effective_include = include_dirs if include_dirs is not None else stored_include
    effective_exclude = exclude_dirs if exclude_dirs is not None else stored_exclude

    # Check for filter change
    filters_changed = project_info_file.exists() and (
        effective_include != stored_include or effective_exclude != stored_exclude
    )

    # Force full reindex if filters changed during incremental
    if filters_changed and incremental:
        logger.warning(
            f"[FILTER_CHANGE] Filters changed, forcing full reindex\n"
            f"  Old: include={stored_include}, exclude={stored_exclude}\n"
            f"  New: include={effective_include}, exclude={effective_exclude}"
        )
        incremental = False  # Force full reindex

    # Use effective filters for indexing
    include_dirs = effective_include
    exclude_dirs = effective_exclude

    # Save/update filters in project_info.json
    if not project_info_file.exists() or filters_changed:
        # First time or filters changed - create/update project storage with new filters
        project_dir = get_project_storage_dir(
            str(directory_path),
            include_dirs=include_dirs,
            exclude_dirs=exclude_dirs,
        )

        # Update all model-specific project_info.json files
        # (needed for both first index AND filter changes in multi-model setup)
        if get_state().multi_model_enabled:
            # Update each model's project_info.json
            for model_key in MODEL_POOL_CONFIG.keys():
                update_project_filters(
                    str(directory_path),
                    include_dirs,
                    exclude_dirs,
                    model_key=model_key,
                )
        else:
            # Single model - update default model's project_info
            update_project_filters(str(directory_path), include_dirs, exclude_dirs)

    # Set as current project (using setter for proper cross-module sync)
    set_current_project(str(directory_path))

    # Multi-model batch indexing
    if multi_model and get_state().multi_model_enabled:
        logger.info(f"Multi-model batch indexing for: {directory_path}")
        results = _index_with_all_models(
            directory_path, incremental, include_dirs, exclude_dirs
        )
        return _build_index_response(
            results, str(directory_path), multi_model=True, incremental=incremental
        )

    # Single model indexing (original behavior)
    else:
        logger.info(f"Single-model indexing for: {directory_path}")

        # Get or create project storage
        project_dir = get_project_storage_dir(str(directory_path))
        index_dir = project_dir / "index"
        index_dir.mkdir(exist_ok=True)

        # Initialize components using cached getter functions
        chunker = MultiLanguageChunker(str(directory_path), include_dirs, exclude_dirs)
        embedder = get_embedder()
        searcher_instance = get_searcher(str(directory_path))

        config = get_search_config()
        indexer = (
            searcher_instance
            if config.enable_hybrid_search
            else get_index_manager(str(directory_path))
        )

        # Run indexing (using helper)
        result = _run_indexing(
            indexer,
            embedder,
            chunker,
            str(directory_path),
            incremental,
            include_dirs,
            exclude_dirs,
        )

        # Build response (using helper)
        return _build_index_response(
            [result],
            str(directory_path),
            multi_model=False,
            incremental=incremental,
        )
