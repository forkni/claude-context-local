"""Indexing tool handlers for MCP server.

Handlers for creating, updating, and clearing code indices.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from chunking.multi_language_chunker import MultiLanguageChunker
from mcp_server.model_pool_manager import get_embedder
from mcp_server.server import (
    get_index_manager,
    get_searcher,
)
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import (
    get_project_storage_dir,
    get_storage_dir,
    set_current_project,
    update_project_filters,
)
from mcp_server.tools.decorators import error_handler
from search.config import (
    MODEL_POOL_CONFIG,
    MODEL_REGISTRY,
    SearchConfigManager,
)
from search.filters import compute_drive_agnostic_hash, compute_legacy_hash
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
    config = get_config()
    chunker = MultiLanguageChunker(directory_path)
    embedder = get_embedder(model_key)

    if config.search_mode.enable_hybrid:
        # Get project_id from index_dir parent
        project_dir = index_dir.parent
        project_id = project_dir.name.rsplit("_", 1)[0]  # Remove dimension suffix

        indexer = HybridSearcher(
            storage_dir=str(index_dir),
            embedder=embedder,
            bm25_weight=config.search_mode.bm25_weight,
            dense_weight=config.search_mode.dense_weight,
            rrf_k=config.search_mode.rrf_k_parameter,
            max_workers=2,
            bm25_use_stopwords=config.search_mode.bm25_use_stopwords,
            bm25_use_stemming=config.search_mode.bm25_use_stemming,
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
    original_config = get_config()
    original_model = original_config.embedding.model_name

    try:
        for model_key, model_name in MODEL_POOL_CONFIG.items():
            logger.info(f"Indexing with model: {model_name} ({model_key})")

            # Switch to this model temporarily
            config_mgr = SearchConfigManager()
            config = config_mgr.load_config()
            config.embedding.model_name = model_name

            # Update dimension from registry
            if model_name in MODEL_REGISTRY:
                config.embedding.dimension = MODEL_REGISTRY[model_name]["dimension"]

            config_mgr.save_config(config)

            # Invalidate global config cache to force reload from disk
            from search import config as config_module

            config_module._config_manager = None

            # Also invalidate ServiceLocator's cached config (BUG FIX #1: Merkle snapshot naming)
            from mcp_server.services import ServiceLocator

            locator = ServiceLocator.instance()
            locator.invalidate("config")  # Force config reload with new model settings

            # Clear cached components INCLUDING embedders to free GPU memory (BUG FIX #2: Performance)
            state = get_state()
            state.reset_for_model_switch()  # Clears embedders + index_manager + searcher

            # Force garbage collection and GPU memory release
            import gc

            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except ImportError:
                pass

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
            config = get_config()
            if config.search_mode.enable_hybrid:
                project_id = project_dir.name.rsplit("_", 1)[0]
                indexer = HybridSearcher(
                    storage_dir=str(index_dir),
                    embedder=embedder,
                    bm25_weight=config.search_mode.bm25_weight,
                    dense_weight=config.search_mode.dense_weight,
                    rrf_k=config.search_mode.rrf_k_parameter,
                    max_workers=2,
                    bm25_use_stopwords=config.search_mode.bm25_use_stopwords,
                    bm25_use_stemming=config.search_mode.bm25_use_stemming,
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
                    "dimension": config.embedding.dimension,
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
        config.embedding.model_name = original_model
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

    # Check both hashes for backward compatibility
    new_hash = compute_drive_agnostic_hash(str(project_path))
    legacy_hash = compute_legacy_hash(str(project_path))

    # Find ALL model directories for this project (check both patterns)
    base_dir = get_storage_dir()
    projects_dir = base_dir / "projects"
    patterns = [f"{project_name}_{new_hash}_*", f"{project_name}_{legacy_hash}_*"]

    cleared_dirs = []
    seen_dirs = set()  # Avoid processing same dir twice

    for pattern in patterns:
        for model_dir in projects_dir.glob(pattern):
            # Skip if already processed (in case both hashes match same dir)
            if model_dir in seen_dirs:
                continue
            seen_dirs.add(model_dir)

            # Delete BM25 directory
            bm25_dir = model_dir / "index" / "bm25"
            if bm25_dir.exists():
                shutil.rmtree(bm25_dir)
                logger.info(f"Deleted BM25 directory: {bm25_dir}")

            # Delete dense index files
            index_dir = model_dir / "index"
            for file in ["code.index", "chunks_metadata.db", "stats.json"]:
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


@error_handler("Delete project")
async def handle_delete_project(arguments: Dict[str, Any]) -> dict:
    """Delete an indexed project completely (indices + Merkle snapshots).

    This tool properly closes database connections before deletion to prevent
    file lock errors (PermissionError on Windows). Use this instead of manual
    deletion when the MCP server is running.

    Args:
        arguments: Dict with:
            - project_path (str, required): Absolute path to project directory
            - force (bool, optional): Force delete even if current project (default: False)

    Returns:
        dict with:
            - success (bool): True if fully deleted
            - deleted_directories (list): Project directories that were deleted
            - deleted_snapshots (int): Number of Merkle snapshots deleted
            - errors (list or None): Any deletion errors that occurred
            - hint (str, optional): Suggestion if deletion blocked
    """
    import shutil

    from mcp_server.server import close_project_resources
    from merkle.snapshot_manager import SnapshotManager

    # Extract arguments
    project_path = arguments.get("project_path")
    force = arguments.get("force", False)

    if not project_path:
        return {"error": "project_path is required"}

    # 1. Validate project exists
    project_path_resolved = Path(project_path).resolve()
    if not project_path_resolved.exists():
        return {"error": f"Project path does not exist: {project_path}"}

    # 2. Check if this is the current project
    state = get_state()
    is_current = state.current_project == str(project_path_resolved)

    if is_current and not force:
        return {
            "error": "Cannot delete current project without force=True",
            "hint": "Set force=True or switch to another project first",
            "is_current_project": True,
        }

    # 3. Close all resources for this project
    logger.info(f"Closing resources for project: {project_path}")
    close_project_resources(str(project_path_resolved))

    # 4. Find and delete all model directories for this project
    project_name = project_path_resolved.name

    # Check both hashes for backward compatibility
    new_hash = compute_drive_agnostic_hash(str(project_path_resolved))
    legacy_hash = compute_legacy_hash(str(project_path_resolved))

    base_dir = get_storage_dir()
    projects_dir = base_dir / "projects"
    patterns = [f"{project_name}_{new_hash}_*", f"{project_name}_{legacy_hash}_*"]

    deleted_dirs = []
    errors = []
    seen_dirs = set()  # Avoid processing same dir twice

    logger.info(f"Searching for project directories with patterns: {patterns}")

    for pattern in patterns:
        for model_dir in projects_dir.glob(pattern):
            # Skip if already processed
            if model_dir in seen_dirs:
                continue
            seen_dirs.add(model_dir)

            logger.info(f"Deleting project directory: {model_dir}")
            try:
                shutil.rmtree(model_dir)
                deleted_dirs.append(model_dir.name)
                logger.info(f"Successfully deleted: {model_dir}")
            except PermissionError as e:
                error_msg = f"{model_dir.name}: File locked - {e}"
                errors.append(error_msg)
                logger.error(f"Permission error deleting {model_dir}: {e}")
            except Exception as e:
                error_msg = f"{model_dir.name}: {e}"
                errors.append(error_msg)
                logger.error(f"Unexpected error deleting {model_dir}: {e}")

    # 5. Delete Merkle snapshots for this project
    logger.info(f"Deleting Merkle snapshots for: {project_path_resolved}")
    snapshot_manager = SnapshotManager()
    try:
        deleted_snapshots = snapshot_manager.delete_all_snapshots(
            str(project_path_resolved)
        )
        logger.info(f"Deleted {deleted_snapshots} Merkle snapshot(s)")
    except Exception as e:
        deleted_snapshots = 0
        logger.warning(f"Failed to delete Merkle snapshots: {e}")

    # 6. If deletion failed, add to cleanup queue for retry on next startup
    if errors:
        from mcp_server.cleanup_queue import CleanupQueue

        queue = CleanupQueue()
        for error_msg in errors:
            # Extract directory name from error message
            dir_name = error_msg.split(":")[0].strip()
            full_path = str(projects_dir / dir_name)
            queue.add(full_path, error_msg)
            logger.info(f"Added to cleanup queue: {full_path}")

    # 7. Build response
    success = len(errors) == 0
    result = {
        "success": success,
        "deleted_directories": deleted_dirs,
        "deleted_snapshots": deleted_snapshots,
    }

    if errors:
        result["errors"] = errors
        result["queued_for_retry"] = len(errors)
        result["hint"] = (
            "Some files couldn't be deleted (locked). They'll be retried on next server startup."
        )

    if success:
        logger.info(
            f"Project deletion complete: {len(deleted_dirs)} directories, {deleted_snapshots} snapshots"
        )
    else:
        logger.warning(
            f"Project deletion partial: {len(deleted_dirs)} deleted, {len(errors)} failed"
        )

    return result


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
        # Run in thread pool to avoid blocking asyncio event loop (SSE keepalive fix)
        import asyncio

        results = await asyncio.to_thread(
            _index_with_all_models,
            directory_path,
            incremental,
            include_dirs,
            exclude_dirs,
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

        config = get_config()
        indexer = (
            searcher_instance
            if config.search_mode.enable_hybrid
            else get_index_manager(str(directory_path))
        )

        # Run indexing (using helper) - in thread pool to avoid blocking event loop
        import asyncio

        result = await asyncio.to_thread(
            _run_indexing,
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
