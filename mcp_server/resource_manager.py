"""Resource cleanup and lifecycle management for MCP server.

This module handles:
- Cleanup of previous project resources (index managers, searchers, embedders)
- Project resource closure before deletion
- Shared server state initialization for stdio and SSE modes
"""

import gc
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class ResourceManager:
    """Manages cleanup and lifecycle of MCP server resources.

    This class encapsulates resource management operations that were
    previously scattered across server.py, providing a cleaner separation
    of concerns and easier testability.
    """

    def __init__(self):
        """Initialize ResourceManager.

        The manager operates on global state via ServiceLocator pattern.
        """
        pass

    def cleanup_previous_resources(self) -> None:
        """Cleanup previous project resources to free memory.

        Cleans up:
        - Index manager (closes metadata DB connections)
        - Searcher (shuts down neural reranker, releases GPU memory)
        - Embedder pool (clears all cached embedders)
        - GPU cache (if PyTorch/CUDA available)

        This method should be called before switching projects or
        when explicitly requested by the user to free memory.
        """
        from mcp_server.services import get_state

        state = get_state()
        try:
            if state.index_manager is not None:
                if (
                    hasattr(state.index_manager, "_metadata_db")
                    and state.index_manager._metadata_db is not None
                ):
                    state.index_manager._metadata_db.close()
                state.index_manager = None
                logger.info("Previous index manager cleaned up")

            if state.searcher is not None:
                if hasattr(state.searcher, "shutdown"):
                    state.searcher.shutdown()
                    logger.info(
                        "Searcher shutdown completed (neural reranker released)"
                    )
                state.searcher = None
                logger.info("Previous searcher cleaned up")

            # Clear embedder pool to free GPU memory (explicit user request)
            if state.embedders:
                embedder_count = len(state.embedders)
                logger.info(
                    f"Clearing {embedder_count} cached embedder(s): {list(state.embedders.keys())}"
                )
                state.clear_embedders()
                logger.info("Embedder pool cleared - VRAM released")

            # Reset ModelPoolManager singleton to release all model references
            from mcp_server.model_pool_manager import reset_pool_manager

            reset_pool_manager()
            logger.info("ModelPoolManager singleton reset")

            # Force garbage collection to immediately free GPU memory
            gc.collect()
            logger.info("Garbage collection completed")

            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    logger.info("GPU cache cleared")
            except ImportError as e:
                logger.debug(f"GPU cache cleanup skipped: {e}")
        except (AttributeError, TypeError) as e:
            logger.warning(f"Error during resource cleanup: {e}")

    def close_project_resources(self, project_path: str) -> bool:
        """Close all resources associated with a specific project.

        This function ensures all database connections and file handles
        are released before project deletion. It's designed to be called
        before deleting a project directory to prevent file lock errors.

        Args:
            project_path: Absolute path to the project directory

        Returns:
            True if cleanup successful
        """
        from mcp_server.services import get_state

        state = get_state()
        project_path_resolved = str(Path(project_path).resolve())

        # If this is the current project, clean up state
        if state.current_project == project_path_resolved:
            self.cleanup_previous_resources()
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
    """Initialize global server state (shared by stdio and SSE modes).

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
    from mcp_server.services import get_state
    from mcp_server.storage_manager import get_storage_dir, set_current_project
    from search.config import MODEL_POOL_CONFIG, get_config_manager

    state = get_state()

    # 1. Sync multi_model_enabled from config file
    try:
        config_manager = get_config_manager()
        config = config_manager.load_config()
        state.sync_from_config(config)
        logger.info("[INIT] Config synced from file")
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
    logger.info(f"[INIT] Available models: {list(MODEL_POOL_CONFIG.keys())}")

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


# ============================================================================
# Module-level singleton and backward-compatible wrappers
# ============================================================================

_resource_manager = None


def get_resource_manager() -> ResourceManager:
    """Get or create singleton ResourceManager instance.

    Returns:
        Singleton ResourceManager instance
    """
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager


def _cleanup_previous_resources():
    """Cleanup previous project resources to free memory.

    .. note::
        This is a backward-compatible wrapper around ResourceManager.
        For new code, consider using ResourceManager directly.
    """
    return get_resource_manager().cleanup_previous_resources()


def close_project_resources(project_path: str) -> bool:
    """Close all resources associated with a specific project.

    Args:
        project_path: Absolute path to the project directory

    Returns:
        True if cleanup successful

    .. note::
        This is a backward-compatible wrapper around ResourceManager.
        For new code, consider using ResourceManager directly.
    """
    return get_resource_manager().close_project_resources(project_path)
