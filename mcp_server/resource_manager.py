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
from typing import Any


logger = logging.getLogger(__name__)

# Minimum GPU memory (MB) considered "still allocated" after cleanup.
# Below this threshold, residual allocations are expected (PyTorch runtime overhead ~50MB).
GPU_CLEANUP_THRESHOLD_MB = 100


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
    except Exception as e:  # noqa: BLE001 - cleanup: isolated teardown step, must not block sibling cleanup
        logger.warning(f"Error cleaning index_manager: {e}")

    # Component 2: Searcher cleanup
    try:
        if state.searcher is not None:
            if hasattr(state.searcher, "shutdown"):
                state.searcher.shutdown()
                logger.info("Searcher shutdown completed (neural reranker released)")
            state.searcher = None
            logger.info("Previous searcher cleaned up")
    except Exception as e:  # noqa: BLE001 - cleanup: isolated teardown step, must not block sibling cleanup
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
    except Exception as e:  # noqa: BLE001 - cleanup: isolated teardown step, must not block sibling cleanup
        logger.warning(f"Error cleaning embedders: {e}")

    # Component 4: ModelPoolManager reset (always try)
    try:
        from mcp_server.model_pool_manager import reset_pool_manager

        reset_pool_manager()
        logger.info("ModelPoolManager singleton reset")
    except Exception as e:  # noqa: BLE001 - cleanup: isolated teardown step, must not block sibling cleanup
        logger.warning(f"Error resetting pool manager: {e}")

    # Component 5+6: GPU memory release (gc.collect + CUDA cache if available)
    try:
        from search.gpu_monitor import release_gpu_memory

        release_gpu_memory(synchronize=False)
        logger.info("GPU memory released (gc + CUDA cache)")
    except Exception as e:  # noqa: BLE001 - cleanup: isolated teardown step, must not block sibling cleanup
        logger.warning(f"Error releasing GPU memory: {e}")

    # Component 7: OTel force-flush — drain pending spans before resource teardown.
    # Do NOT call shutdown_observability() here: shutdown permanently disables the
    # global TracerProvider and belongs at server exit, not at per-request cleanup.
    try:
        from utils.observability import force_flush

        force_flush()
    except Exception as e:  # noqa: BLE001 - cleanup: isolated teardown step, must not block sibling cleanup
        logger.warning(f"Error flushing OTel spans: {e}")


class McpResourceRefresher:
    """The MCP-side resource-lifecycle collaborator used by a full reindex.

    Moved out of ``search.incremental_indexer.IncrementalIndexer`` — indexing
    logic and MCP process-state management were living in the same method.
    ``search/`` depends on this only through the
    ``search.resource_refresh.ResourceRefresher`` protocol; this class
    satisfies it structurally (no base class, no import of that module), so
    no import arrow crosses from ``search/`` up into ``mcp_server/`` here.
    """

    def refresh_before_full_index(
        self, project_path: str, embedder: Any, indexer: Any
    ) -> tuple[Any, Any]:
        """Mandatory resource release and verification before full reindex.

        Ensures all previous resources (index managers, searchers, embedders, GPU memory)
        are properly released before starting a full reindex operation. This prevents
        VRAM/memory pressure that could cause reindexing to fail.

        Performs:
        1. Save current model key before cleanup
        2. Release via ResourceManager.cleanup_previous_resources() (same as UI command)
        3. Verification of cleanup completeness
        4. Refresh embedder with fresh instance (preserving model key)
        5. Refresh indexer/searcher (required since cleanup shut it down)

        Args:
            project_path: Path to the project being indexed (needed to recreate searcher)
            embedder: The caller's current embedder — released and superseded here.
            indexer: The caller's current indexer — refreshed here only if
                shut down by cleanup; otherwise returned unchanged.

        Returns:
            Tuple of (embedder, indexer) the caller must rebind onto itself.

        This method is idempotent - safe to call even if cleanup was already performed.
        """
        logger.info("[FULL_INDEX] Mandatory pre-reindex resource release starting...")

        # Step 1: Release resources (same operation as UI "Release Resources" command)
        _cleanup_previous_resources()
        logger.info("[FULL_INDEX] Resource release completed")

        # Step 2: Verify cleanup completeness
        from mcp_server.services import get_state

        state = get_state()
        verification_passed = True
        warnings = []

        # Check embedder pool cleared
        if state.embedders:
            warnings.append(
                f"Embedder pool not fully cleared: {list(state.embedders.keys())}"
            )
            verification_passed = False

        # Check index_manager released
        if state.index_manager is not None:
            warnings.append("state.index_manager not None after cleanup")
            verification_passed = False

        # Check searcher released
        if state.searcher is not None:
            warnings.append("state.searcher not None after cleanup")
            verification_passed = False

        # Check GPU memory (if CUDA available)
        try:
            import torch

            if torch.cuda.is_available():
                allocated_mb = torch.cuda.memory_allocated() / (1024**2)
                if allocated_mb > GPU_CLEANUP_THRESHOLD_MB:
                    warnings.append(
                        f"GPU memory still allocated: {allocated_mb:.1f} MB"
                    )
                    verification_passed = False
        except ImportError:
            pass

        # If verification failed, attempt secondary cleanup and re-verify
        if not verification_passed:
            logger.warning(
                f"[FULL_INDEX] Initial verification failed: {warnings}. "
                "Attempting secondary cleanup..."
            )
            gc.collect()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

            # Re-verify
            state = get_state()
            recheck_warnings = []
            if state.embedders:
                recheck_warnings.append(
                    f"Embedder pool still not cleared: {list(state.embedders.keys())}"
                )
            if state.index_manager is not None:
                recheck_warnings.append("state.index_manager still not None")
            if state.searcher is not None:
                recheck_warnings.append("state.searcher still not None")

            if recheck_warnings:
                logger.warning(
                    f"[FULL_INDEX] Re-verification still shows issues: {recheck_warnings}. "
                    "Proceeding with reindex anyway."
                )
            else:
                logger.info(
                    "[FULL_INDEX] Secondary cleanup successful - verification passed"
                )
        else:
            logger.info(
                "[FULL_INDEX] Resource verification passed — all resources released"
            )

        # Step 3: Refresh embedder (required since cleanup cleared it)
        from mcp_server.model_pool_manager import get_embedder

        embedder = get_embedder()  # Fresh instance with config model
        logger.info("[FULL_INDEX] Fresh embedder acquired for reindex")

        # Step 4: Refresh indexer/searcher (required since cleanup shut it down)
        # Only refresh if the indexer was actually shut down (has _is_shutdown flag set to True)
        if hasattr(indexer, "_is_shutdown") and indexer._is_shutdown:
            from mcp_server.search_factory import get_searcher

            # load_existing=False (#reindex-log-audit-2026-07-30): this searcher
            # is a write-only target for the force-full reindex about to run —
            # _full_index() calls clear_index()/clear_hybrid_indices() on it
            # moments later, so loading the stale on-disk BM25 index here would
            # only cost time and log spurious version/tokenizer mismatch
            # warnings for data that is about to be discarded.
            indexer = get_searcher(project_path, load_existing=False)
            logger.info("[FULL_INDEX] Fresh indexer/searcher acquired for reindex")
        else:
            logger.debug(
                "[FULL_INDEX] Indexer not shut down or doesn't need refresh (test mock)"
            )

        return embedder, indexer

    def invalidate_searcher_cache(self) -> None:
        """Null out state.searcher — compensating inverse of a failed refresh.

        (#reindex-log-audit-2026-07-30) The searcher acquired by
        ``refresh_before_full_index`` was built with ``load_existing=False``,
        so if a full-index failure happened after construction but before
        ``clear_hybrid_indices()``/rebuild completed, ``state.searcher`` is an
        empty write-only instance. Null it — same one-line invalidation
        ``search_factory.get_searcher()`` already does for
        ``DimensionMismatchError`` — so the next call rebuilds from disk
        instead of returning an empty cached searcher.
        """
        from mcp_server.services import get_state

        get_state().searcher = None


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


def bind_active_project_overrides(project_path: str) -> None:
    """Point the config layer at *project_path*'s storage dir and drop stale caches.

    The one project-activation pairing, called at every site that makes a
    project active (``handle_switch_project``, ``_run_index_directory``, and
    ``initialize_server_state``'s startup restoration): binding
    ``_active_project_storage_dir`` (search/config.py) is what makes the
    project's ``search_overrides.json`` (ADR-0014) get merged into subsequent
    ``load_config()`` calls, and ``invalidate_config_caches()`` is required
    alongside it so the config singleton cached by an earlier ``load_config()``
    call (before this project was bound) doesn't keep serving the un-merged
    config.

    Non-swallowing by design: a bind failure here means the previous
    project's overrides would otherwise keep silently serving. Handler call
    sites let it propagate through ``@error_handler`` so failure is visible
    to the caller; startup call sites wrap this in their own non-fatal
    try/except, since a project storage lookup failure at boot should not
    crash the server.
    """
    from mcp_server.state import invalidate_config_caches
    from mcp_server.storage_manager import get_project_storage_dir
    from search.config import set_active_project_storage_dir

    set_active_project_storage_dir(get_project_storage_dir(project_path))
    invalidate_config_caches()


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
    except Exception as e:  # noqa: BLE001 - cleanup: non-fatal init step, falls back to default config
        logger.warning(f"[INIT] Config sync failed (using defaults): {e}")

    # 2. Set default project
    default_project = os.getenv("CLAUDE_DEFAULT_PROJECT", None)
    if default_project:
        project_path = str(Path(default_project).resolve())
        state.current_project = project_path
        try:
            bind_active_project_overrides(project_path)
        except Exception as e:  # noqa: BLE001 - cleanup: non-fatal init step, project still activates without overrides
            logger.warning(f"[INIT] Could not bind project overrides layer: {e}")
        logger.info(f"[INIT] Default project (env): {project_path}")
    else:
        selection = load_project_selection()
        if selection:
            restored_path = selection["last_project_path"]
            set_current_project(restored_path)
            try:
                bind_active_project_overrides(restored_path)
            except Exception as e:  # noqa: BLE001 - cleanup: non-fatal init step, project still activates without overrides
                logger.warning(f"[INIT] Could not bind project overrides layer: {e}")
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
