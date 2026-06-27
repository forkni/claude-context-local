"""Resource cleanup and lifecycle management for MCP server.

This module handles:
- Cleanup of previous project resources (index managers, searchers, embedders)
- Project resource closure before deletion
- Shared server state initialization for stdio and StreamableHTTP modes
"""

import gc
import logging
import os
import time
from pathlib import Path


logger = logging.getLogger(__name__)


def _cleanup_previous_resources() -> None:
    """Cleanup previous project resources to free memory.

    Cleans up:
    - Index manager (closes metadata DB connections)
    - Searcher (shuts down neural reranker, releases GPU memory)
    - Embedder pool (clears all cached embedders)
    - GPU cache (if PyTorch/CUDA available)

    This function should be called before switching projects or
    when explicitly requested by the user to free memory.

    Each component cleanup is isolated so that failures in one component
    don't prevent cleanup of other components.
    """
    from mcp_server.state import get_state

    state = get_state()

    # Component 1: Index manager cleanup
    try:
        if state.index_manager is not None:
            state.index_manager.close()
            state.index_manager = None
            logger.info("Previous index manager cleaned up")
    except Exception as e:
        logger.warning(f"Error cleaning index_manager: {e}")

    # Component 2: Searcher cleanup
    try:
        if state.searcher is not None:
            if hasattr(state.searcher, "shutdown"):
                state.searcher.shutdown()
                logger.info("Searcher shutdown completed (neural reranker released)")
            state.searcher = None
            logger.info("Previous searcher cleaned up")
    except Exception as e:
        logger.warning(f"Error cleaning searcher: {e}")

    # Component 3: Embedder pool cleanup (always try even if above failed)
    try:
        if state.embedders:
            embedder_count = len(state.embedders)
            logger.info(
                f"Clearing {embedder_count} cached embedder(s): {list(state.embedders.keys())}"
            )
            state.clear_embedders()
            logger.info("Embedder pool cleared - VRAM released")
    except Exception as e:
        logger.warning(f"Error cleaning embedders: {e}")

    # Component 4: ModelPoolManager reset (always try)
    try:
        from mcp_server.model_pool_manager import reset_pool_manager

        reset_pool_manager()
        logger.info("ModelPoolManager singleton reset")
    except Exception as e:
        logger.warning(f"Error resetting pool manager: {e}")

    # Component 5+6: GPU memory release (gc.collect + CUDA cache if available)
    try:
        from search.gpu_monitor import release_gpu_memory

        release_gpu_memory(synchronize=False)
        logger.info("GPU memory released (gc + CUDA cache)")
    except Exception as e:
        logger.warning(f"Error releasing GPU memory: {e}")

    # Component 7: OTel force-flush — drain pending spans before resource teardown.
    # Do NOT call shutdown_observability() here: shutdown permanently disables the
    # global TracerProvider and belongs at server exit, not at per-request cleanup.
    try:
        from utils.observability import force_flush

        force_flush()
    except Exception as e:
        logger.warning(f"Error flushing OTel spans: {e}")


def close_project_resources(project_path: str, *, clear_current: bool = True) -> bool:
    """Close all resources associated with a specific project.

    This function ensures all database connections and file handles
    are released before project deletion. It's designed to be called
    before deleting a project directory to prevent file lock errors.

    Args:
        project_path: Absolute path to the project directory
        clear_current: Whether to null state.current_project after cleanup.
            True (default) for deletion — the project is gone, so the
            current-project pointer must be cleared.
            False for clear-index — only the index files are removed; the
            project directory still exists and stays the active project, so
            nulling the pointer would cause subsequent get_index_status calls
            to hit the ValueError early-return path and drop bm25_documents.

    Returns:
        True if cleanup successful
    """
    from mcp_server.state import get_state

    state = get_state()
    project_path_resolved = str(Path(project_path).resolve())

    # If this is the current project, clean up state
    if state.current_project == project_path_resolved:
        _cleanup_previous_resources()
        if clear_current:
            state.current_project = None
        logger.info(f"Cleaned up resources for current project: {project_path}")
    else:
        logger.debug(
            f"Project not current, no active resources to clean: {project_path}"
        )

    # Force garbage collection to release any lingering handles
    gc.collect()

    # Small delay to allow OS to release file handles (especially on Windows)
    time.sleep(0.3)

    return True


def initialize_server_state() -> None:
    """Initialize global server state (shared by stdio and StreamableHTTP modes).

    Performs:
    1. Config sync from file with env override
    2. Default project restoration (env var > persistent selection > none)
    3. Model pool initialization in lazy mode
    4. Deferred cleanup queue processing

    This function consolidates the duplicate initialization logic that
    was previously in both run_stdio_server() and app_lifespan().
    """
    from mcp_server.cleanup_queue import CleanupQueue
    from mcp_server.project_persistence import load_project_selection
    from mcp_server.state import get_state
    from mcp_server.storage_manager import get_storage_dir, set_current_project
    from search.config import get_config_manager

    state = get_state()

    # 1. Load config
    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()
        logger.info("[INIT] Config loaded")
        from utils.observability import init_observability

        init_observability(config.observability)
    except Exception as e:
        logger.warning(f"[INIT] Config sync failed (using defaults): {e}")

    # 2. Set default project
    default_project = os.getenv("CLAUDE_DEFAULT_PROJECT", None)
    if default_project:
        project_path = str(Path(default_project).resolve())
        state.current_project = project_path
        logger.info(f"[INIT] Default project (env): {project_path}")
    else:
        selection = load_project_selection()
        if selection:
            restored_path = selection["last_project_path"]
            set_current_project(restored_path)
            logger.info(f"[INIT] Restored project: {Path(restored_path).name}")
        else:
            logger.info("[INIT] No default project")

    # 3. Lazy model loading
    logger.info("[INIT] Model loading deferred until first use (lazy mode)")

    # 3.5. VRAM tier detection - DEFERRED to first model load
    logger.info("[INIT] VRAM tier detection deferred until first model request")

    # 4. Storage directory
    storage = get_storage_dir()
    logger.info(f"[INIT] Storage directory: {storage}")

    # 5. Process deferred cleanup queue
    cleanup_queue = CleanupQueue()
    result = cleanup_queue.process()
    if result["processed"] > 0:
        logger.info(f"[INIT] Processed {result['processed']} deferred cleanup tasks")
    if result["failed"]:
        logger.warning(
            f"[INIT] Cleanup failed for {len(result['failed'])} items: {result['failed']}"
        )

    logger.info("[INIT] Server initialization complete")
