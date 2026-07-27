"""Indexing tool handlers for MCP server.

Handlers for creating, updating, and clearing code indices.
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from chunking.multi_language_chunker import MultiLanguageChunker
from mcp_server.model_pool_manager import get_embedder
from mcp_server.search_factory import (
    get_index_manager,
    get_searcher,
)
from mcp_server.services import get_config, get_state
from mcp_server.storage_manager import (
    get_canonical_project_info,
    get_project_storage_dir,
    get_storage_dir,
    set_current_project,
    update_project_filters,
)
from mcp_server.tools import responses
from mcp_server.tools.decorators import error_handler, with_mutation_lock
from mcp_server.utils.config_helpers import temporary_ram_fallback_off
from search.config import (
    MODEL_REGISTRY,
    SearchConfigManager,
)
from search.filters import compute_drive_agnostic_hash, compute_legacy_hash
from search.incremental_indexer import IncrementalIndexer


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Index Directory Helper Functions
# ----------------------------------------------------------------------------


def _check_file_accessibility(
    file_paths: list[Path], sample_size: int = 50
) -> list[Path]:
    """Quick check for file accessibility. Returns list of inaccessible files.

    Args:
        file_paths: List of file paths to check
        sample_size: Number of files to sample (default: 50)

    Returns:
        List of inaccessible file paths
    """
    import random

    if not file_paths:
        return []

    sample = random.sample(file_paths, min(sample_size, len(file_paths)))
    inaccessible = []

    for fp in sample:
        try:
            with open(fp, encoding="utf-8") as f:
                f.read(1)  # Just read 1 byte to check access
        except (OSError, PermissionError):
            inaccessible.append(fp)
        except UnicodeDecodeError:
            # Skip other exceptions (encoding errors, etc.)
            pass

    return inaccessible


def _run_accessibility_precheck(directory_path: Path) -> None:
    """Sample project files and warn if any are locked/inaccessible.

    Synchronous by design — walks the directory tree and opens up to 50
    files, so the caller offloads this via asyncio.to_thread rather than
    running it inline on the event loop.

    Args:
        directory_path: Resolved project root to scan.
    """
    try:
        # Quick file accessibility check on a sample of files
        from chunking.tree_sitter import TreeSitterChunker

        ext_set = set(TreeSitterChunker.get_supported_extensions())
        sample_files = []

        # Single lazy pass over the directory tree; break early at 50 files.
        # Avoids up to 19 separate rglob walks (one per extension) and eliminates
        # the materialize-before-slice anti-pattern that defeats rglob laziness.
        for p in directory_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in ext_set:
                sample_files.append(p)
                if len(sample_files) >= 50:
                    break

        if sample_files:
            inaccessible = _check_file_accessibility(sample_files, sample_size=50)
            if inaccessible:
                logger.warning(
                    f"[ACCESSIBILITY] {len(inaccessible)}/{len(sample_files)} sampled files "
                    f"are currently locked or inaccessible. Indexing will skip these files.\n"
                    f"  Example: {inaccessible[0]}\n"
                    f"  Tip: Close other programs (TouchDesigner, IDEs) that may have files open."
                )
    except Exception as e:  # noqa: BLE001 - resilience: optional accessibility check, indexing proceeds regardless
        # Don't fail indexing if accessibility check fails
        logger.debug(f"[ACCESSIBILITY] Check failed (non-critical): {e}")


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
        # Propagated so _build_index_response can turn a caught indexing
        # exception (e.g. PermissionError during force-full pre-clear) into a
        # hard failure instead of reporting success with zeroed counts.
        # Named indexing_succeeded/indexing_error (not success/error) — this is
        # an internal transport dict, not a client-facing response envelope;
        # "success"/"error" keys are reserved for mcp_server.tools.responses
        # (see test_response_envelope_ownership.py's stray-literal gate).
        "indexing_succeeded": result.success,
        "indexing_error": result.error,
        "call_edges_injected": result.call_edges_injected,
        "call_edge_resolvers": result.call_edge_resolvers,
    }


def _build_index_response(
    results: list[dict],
    directory_path: str,
    incremental: bool,
    include_dirs: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
) -> dict:
    """Build the final index response.

    Args:
        results: List with one indexing result dict
        directory_path: The indexed directory
        incremental: Whether incremental mode was used
        include_dirs: Effective include-dirs filter actually used for this run
            (after resolving stored project filters) — surfaced so a caller
            can tell at a glance whether a corpus-size surprise traces back to
            an unexpected filter instead of having to re-derive it.
        exclude_dirs: Effective exclude-dirs filter actually used for this run

    Returns:
        dict: Complete response with success status and statistics. An
        indexing pass that raised internally (``r["indexing_succeeded"] is
        False``) or a full reindex that silently added zero chunks is
        reported as a hard failure rather than the caught/zeroed result being
        papered over as success — both are exactly the "half-purged index,
        reported OK" failure mode this guards against.
    """
    r = results[0]

    if not r.get("indexing_succeeded", True):
        return responses.error(
            r.get("indexing_error") or "Indexing failed (see server logs for detail)",
            project=str(directory_path),
            mode="incremental" if incremental else "full",
        )

    if not incremental and r["chunks_added"] == 0:
        return responses.error(
            "Full reindex added 0 chunks. This is never a legitimate outcome "
            "for a non-empty project — the index may be left in a partially "
            "cleared state (a common cause is another process, e.g. a running "
            "MCP server, holding metadata.db open during the pre-clear).",
            project=str(directory_path),
            mode="full",
        )

    response = responses.ok(
        success=True,
        project=str(directory_path),
        files_added=r["files_added"],
        chunks_added=r["chunks_added"],
        time_taken=r["time_taken"],
        mode="incremental" if incremental else "full",
        # Only include modified/removed counts when non-zero (token optimization)
        files_modified=r["files_modified"] if r["files_modified"] > 0 else None,
        files_removed=r["files_removed"] if r["files_removed"] > 0 else None,
        # Surfaces the resolved filters (explicit arg or recovered stored
        # project filter) so an unexpectedly large/small corpus is visible in
        # the response itself, not just inferred from the chunk count.
        include_dirs=include_dirs if include_dirs else None,
        exclude_dirs=exclude_dirs if exclude_dirs else None,
        # Visible, not fatal: resolvers are optional (pyan/libcst require the
        # [callgraph] extra), so call_edges_injected == 0 is a legitimate
        # outcome for some installs and projects with no cross-module calls.
        # Surfacing it here is what turns a silent zero into an inspectable
        # one, the same guard `50ffead` applied one level up to chunk counts.
        call_edges_injected=r.get("call_edges_injected", 0),
        call_edge_resolvers=list(r["call_edge_resolvers"])
        if r.get("call_edge_resolvers")
        else None,
    )
    return response


def _purge_index_dir(
    index_dir: Path, *, keep_chunk_cache: bool
) -> tuple[list[str], list[str]]:
    """Delete every file that makes up one model's index; return what was deleted.

    Single source of truth for "what files make up an index" — this repo
    previously had four independently-drifted deletion lists, one of which
    named a file (``chunks_metadata.db``) that never existed while silently
    orphaning the ``metadata.db`` WAL/SHM sidecars (routinely full-size, not
    a crash-only edge case) and a legacy ``metadata_symbol_cache.json``.

    ``index_dir`` is a model's ``index/`` directory; the call-graph and
    community-detection files live one level up, in its parent.

    Args:
        index_dir: The model's ``index/`` directory to purge.
        keep_chunk_cache: When True, leave ``chunk_embeddings.bin`` in place
            (the mechanical pre-clear for a force-full reindex, where
            deleting it would destroy the persistent chunk-embedding cache).
            When False, delete it too (an explicit "clear index" is the
            escape hatch for suspect vectors, so it must not re-serve them).

    Returns:
        ``(deleted, failed)``: names of the files/directories actually
        deleted, and names that raised ``OSError`` and are still on disk
        (relative to ``index_dir``, except call-graph/community files which
        are bare filenames from the parent directory). A non-empty ``failed``
        means the purge left a half-cleared index — callers that need this to
        be a hard failure (as opposed to the previous behaviour of only
        logging a warning) must check it explicitly.
    """
    import glob
    import shutil

    deleted: list[str] = []
    failed: list[str] = []

    bm25_dir = index_dir / "bm25"
    if bm25_dir.exists():
        try:
            shutil.rmtree(bm25_dir)
            deleted.append("bm25/")
        except OSError as e:
            logger.warning(f"Could not delete {bm25_dir}: {e}")
            failed.append("bm25/")

    filenames = [
        "code.index",
        "chunk_ids.pkl",
        "code_vectors.mmap",
        "metadata.db",
        "metadata.db-wal",
        "metadata.db-shm",
        "metadata_symbol_cache.json",  # legacy orphan; writer removed in dff893d7
        "stats.json",
    ]
    if not keep_chunk_cache:
        filenames.append("chunk_embeddings.bin")

    for fname in filenames:
        fp = index_dir / fname
        if fp.exists():
            try:
                fp.unlink()
                deleted.append(fname)
            except OSError as e:
                logger.warning(f"Could not delete {fp}: {e}")
                failed.append(fname)

    for pattern in ("*_call_graph.json", "*_communities.json"):
        for graph_file in glob.glob(str(index_dir.parent / pattern)):
            try:
                Path(graph_file).unlink()
                deleted.append(Path(graph_file).name)
            except OSError as e:
                logger.warning(f"Could not delete {graph_file}: {e}")
                failed.append(Path(graph_file).name)

    return deleted, failed


def _clear_index_files_before_create(index_dir: Path) -> None:
    """Clear index files before creating a new HybridSearcher.

    This is needed for force_full reindex to avoid file locks on Windows.
    When MCP server is running and holds references to metadata.db, deleting
    files before creating the new HybridSearcher prevents WinError 32.

    Args:
        index_dir: Directory containing index files to clear
    """
    from mcp_server.storage_manager import get_storage_dir

    storage_root = get_storage_dir().resolve()
    if not index_dir.resolve().is_relative_to(storage_root):
        raise ValueError(
            f"_clear_index_files_before_create refused: {index_dir} is outside "
            f"storage root {storage_root}"
        )

    logger.info(
        f"[PRE-CLEAR] Deleting index files before HybridSearcher creation: {index_dir}"
    )
    deleted, failed = _purge_index_dir(index_dir, keep_chunk_cache=True)
    logger.info(f"[PRE-CLEAR] Deleted: {deleted}")
    if failed:
        logger.warning(f"[PRE-CLEAR] Failed to delete (still on disk): {failed}")


def _release_gpu_memory() -> None:
    """Release GPU memory. Thin alias for :func:`search.gpu_monitor.release_gpu_memory`."""
    from search.gpu_monitor import release_gpu_memory

    release_gpu_memory(synchronize=True)


def _iter_project_model_dirs(project_path: Path) -> Iterator[Path]:
    """Yield each model-dir matching *project_path*'s dual-hash patterns, deduped.

    Checks both the drive-agnostic hash (current) and the legacy hash for
    backward compatibility.  Deduplication ensures each directory is yielded
    at most once even when both hash patterns resolve to the same dir.
    """
    project_name = project_path.name
    new_hash = compute_drive_agnostic_hash(str(project_path))
    legacy_hash = compute_legacy_hash(str(project_path))
    projects_dir = get_storage_dir() / "projects"
    seen: set[Path] = set()
    for pattern in [f"{project_name}_{new_hash}_*", f"{project_name}_{legacy_hash}_*"]:
        for model_dir in projects_dir.glob(pattern):
            if model_dir not in seen:
                seen.add(model_dir)
                yield model_dir


def _invalidate_config_caches() -> None:
    """Invalidate all process-wide config caches after a model switch.

    Must be called after writing an updated config to disk so that the next
    :func:`get_config` call reads the new values instead of returning stale ones.
    Clears two caches in order:

    1. ``search.config._config_manager`` (module-level singleton) — the real cache.
    2. ``state.reset_for_model_switch()`` (clears embedders, index_manager, searcher)
    """
    from search import config as config_module

    config_module._config_manager = None

    state = get_state()
    state.reset_for_model_switch()


def _switch_active_model(model_name: str) -> None:
    """Update the active embedding model in the persisted config and invalidate caches.

    Loads the current config, sets ``embedding.model_name`` and the matching
    ``embedding.dimension`` from :data:`MODEL_REGISTRY`, saves to disk only when
    something changed, then calls :func:`_invalidate_config_caches` so the next
    :func:`get_config` call returns fresh values.

    Args:
        model_name: Full HuggingFace model identifier to activate.
    """
    config_mgr = SearchConfigManager()
    config = config_mgr.load_config()
    new_dimension = config.embedding.dimension
    if model_name in MODEL_REGISTRY:
        model_cfg = MODEL_REGISTRY[model_name]
        new_dimension = model_cfg.get("truncate_dim") or model_cfg["dimension"]

    if (
        config.embedding.model_name != model_name
        or config.embedding.dimension != new_dimension
    ):
        config.embedding.model_name = model_name
        # pyrefly: ignore [bad-assignment]
        config.embedding.dimension = new_dimension
        config_mgr.save_config(config)
    else:
        logger.info(
            f"Config already set to {model_name} ({new_dimension}d), skipping save"
        )
        config.embedding.model_name = model_name
        # pyrefly: ignore [bad-assignment]
        config.embedding.dimension = new_dimension

    _invalidate_config_caches()


# ----------------------------------------------------------------------------
# Main Index Handlers
# ----------------------------------------------------------------------------


@error_handler("Clear index")
@with_mutation_lock
async def handle_clear_index(arguments: dict[str, Any]) -> dict:
    """Clear the entire search index for ALL models."""
    from mcp_server.server import close_project_resources
    from merkle.snapshot_manager import SnapshotManager

    state = get_state()
    current_project = state.current_project
    if current_project is None:
        return responses.error("No active project to clear")

    # Close all open DB/index handles BEFORE deleting files. Without this,
    # SQLite and FAISS file handles are still open when unlink() runs, which
    # raises PermissionError on Windows and leaves a partially-deleted index
    # on any OS (#10). Mirrors the correct order used by handle_delete_project.
    # close_project_resources() calls _cleanup_previous_resources() which
    # blocks (gc.collect, torch.cuda ops, time.sleep(0.3)) — offload.
    import asyncio

    # Exclusive write lock on the per-project reader-writer lock: drains
    # in-flight searches (readers in Blocks B-D of SearchOrchestrator) before
    # tearing down the searcher/embedder they use and unlinking index files
    # they read, and blocks new searches until deletion completes — same
    # protection handle_index_directory takes around its index rewrite. The
    # mutation lock (decorator) alone doesn't cover this: searches never
    # acquire it. Lock order is mutation lock → rwlock.write; nothing acquires
    # them in reverse, so no deadlock. Trade-off: the global mutation lock is
    # held across the drain wait (bounded by one in-flight search) — accepted
    # for this rare admin operation; do NOT invert the order to shorten it,
    # as holding the rwlock while waiting for the mutation lock can deadlock
    # against another mutation doing the opposite.
    async with state.get_reindex_rwlock(current_project).write():
        # clear_current=False: keep state.current_project alive after closing handles.
        # clear_index only removes index files — the project dir still exists and
        # must remain the active project so get_index_status can report empty counts.
        await asyncio.to_thread(
            close_project_resources, current_project, clear_current=False
        )

        project_path = Path(current_project).resolve()

        # File deletion and snapshot removal can block on I/O — offload to thread pool.
        def _delete_index_files() -> tuple[list[str], int, dict[str, list[str]]]:
            """Delete index files + Merkle snapshots.

            Returns (cleared_dirs, snapshots_cleared, failed_by_dir) — a
            model dir is still listed in cleared_dirs even if some of its
            files failed to delete (the operation was attempted for every
            dir), but failed_by_dir surfaces exactly what was left behind so
            the response can report it as a partial failure instead of
            unconditional success.
            """
            _cleared: list[str] = []
            _failed_by_dir: dict[str, list[str]] = {}

            for _model_dir in _iter_project_model_dirs(project_path):
                _idx_dir = _model_dir / "index"
                _deleted, _failed = _purge_index_dir(_idx_dir, keep_chunk_cache=False)
                logger.info(f"Deleted from {_idx_dir}: {_deleted}")
                if _failed:
                    logger.warning(f"Failed to delete from {_idx_dir}: {_failed}")
                    _failed_by_dir[_model_dir.name] = _failed
                _cleared.append(_model_dir.name)

            _snaps = 0
            try:
                _snap_mgr = SnapshotManager()
                _snaps = _snap_mgr.delete_all_snapshots(str(project_path))
                logger.info(f"Cleared {_snaps} Merkle snapshot(s) for {project_path}")
            except Exception as _e:  # noqa: BLE001 - resilience: optional snapshot cleanup, index deletion still succeeds
                logger.warning(f"Failed to clear Merkle snapshots: {_e}")

            return _cleared, _snaps, _failed_by_dir

        cleared_dirs, snapshots_cleared, failed_by_dir = await asyncio.to_thread(
            _delete_index_files
        )

        # Cleanup in-memory state (fast lock-guarded assignment, stays on event loop)
        state.reset_search_components()

    logger.info(f"Cleared indices for {len(cleared_dirs)} models: {cleared_dirs}")

    if failed_by_dir:
        return responses.error(
            "Clear index left files behind (likely file locks — a running "
            "MCP server or open file handle): "
            f"{failed_by_dir}",
            cleared_models=cleared_dirs,
        )

    result = responses.ok(
        success=True,
        cleared_models=cleared_dirs,
        # Only include snapshot count when non-zero (token optimization)
        snapshots_cleared=snapshots_cleared if snapshots_cleared > 0 else None,
    )
    return result


@error_handler("Delete project")
@with_mutation_lock
async def handle_delete_project(arguments: dict[str, Any]) -> dict:
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
        return responses.error("project_path is required")

    # 1. Validate project exists
    project_path_resolved = Path(project_path).resolve()
    if not project_path_resolved.exists():
        return responses.error(f"Project path does not exist: {project_path}")

    # 2. Check if this is the current project
    state = get_state()
    is_current = state.current_project == str(project_path_resolved)

    if is_current and not force:
        return responses.error(
            "Cannot delete current project without force=True",
            hint="Set force=True or switch to another project first",
            is_current_project=True,
        )

    # 3. Close all resources for this project
    # close_project_resources() blocks (gc.collect, torch.cuda ops, time.sleep(0.3))
    # — offload, mirroring handle_clear_index.
    import asyncio

    # Exclusive write lock keyed by the project being deleted (may differ from
    # current_project): drains in-flight searches reading this project's index
    # before the searcher teardown and rmtree below, and blocks new searches
    # until deletion completes — same protection handle_index_directory takes.
    # The mutation lock (decorator) alone doesn't cover this: searches never
    # acquire it. Lock order is mutation lock → rwlock.write; nothing acquires
    # them in reverse, so no deadlock. Same mutation-lock hold-time trade-off
    # as handle_clear_index: held across the drain wait, accepted for this
    # rare admin operation.
    async with state.get_reindex_rwlock(str(project_path_resolved)).write():
        logger.info(f"Closing resources for project: {project_path}")
        await asyncio.to_thread(close_project_resources, str(project_path_resolved))

        # 4. Find and delete all model directories for this project
        projects_dir = get_storage_dir() / "projects"

        deleted_dirs = []
        errors = []

        logger.info(f"Searching for project directories: {project_path_resolved}")

        for model_dir in _iter_project_model_dirs(project_path_resolved):
            logger.info(f"Deleting project directory: {model_dir}")
            try:
                shutil.rmtree(model_dir)
                deleted_dirs.append(model_dir.name)
                logger.info(f"Successfully deleted: {model_dir}")
            except PermissionError as e:
                error_msg = f"{model_dir.name}: File locked - {e}"
                errors.append(error_msg)
                logger.error(f"Permission error deleting {model_dir}: {e}")
            except Exception as e:  # noqa: BLE001 - cleanup: per-directory delete, must not block remaining directories
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
        except Exception as e:  # noqa: BLE001 - cleanup: best-effort snapshot delete, must not block remaining steps
            deleted_snapshots = 0
            logger.warning(f"Failed to delete Merkle snapshots: {e}")

    # Deletion finished (possibly partially — failures are queued below for
    # retry at next startup, which starts with a fresh rwlock dict anyway) —
    # drop the rwlock entry so _reindex_rwlocks doesn't grow unboundedly
    # across many index/delete cycles. Waiters keep their own reference; a
    # later reuse of the path creates a fresh lock.
    state.discard_reindex_rwlock(str(project_path_resolved))

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
    result = responses.ok(
        success=success,
        deleted_directories=deleted_dirs,
        # Only include snapshot count when non-zero (token optimization)
        deleted_snapshots=deleted_snapshots if deleted_snapshots > 0 else None,
    )

    if errors:
        result["errors"] = errors
        # pyrefly: ignore [bad-typed-dict-key]
        result["queued_for_retry"] = len(errors)
        result["hint"] = (
            # pyrefly: ignore [bad-typed-dict-key]
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
async def handle_index_directory(arguments: dict[str, Any]) -> dict:
    """Index a directory for code search.

    By default (``wait=True``) this blocks until indexing completes, exactly
    as before. Pass ``wait=False`` to launch indexing as a background job and
    get a ``job_id`` back immediately (§V-C: don't block a tool call for the
    full duration of a long-running operation) — poll progress with
    ``get_index_status(job_id=...)``.
    """
    wait = arguments.get("wait", True)
    if wait:
        return await _run_index_directory(arguments)
    return await _start_index_directory_job(arguments)


async def _start_index_directory_job(arguments: dict[str, Any]) -> dict:
    """Launch ``_run_index_directory`` as a tracked background task.

    Returns immediately with a ``job_id``; the background task reports its
    outcome into the job registry rather than back through this call, so
    errors raised inside the indexing pipeline are captured on the Job
    (status="error") instead of propagating to a caller who already
    disconnected from this request.
    """
    from mcp_server.tools.job_registry import get_job_registry

    directory_path = str(Path(arguments["directory_path"]).resolve())
    registry = get_job_registry()
    job = await registry.create(kind="index_directory", target=directory_path)

    async def _background() -> None:
        try:
            result = await _run_index_directory(arguments)
        except Exception as e:  # noqa: BLE001 - background job boundary: capture into registry, nothing left to propagate to
            logger.error(f"[INDEX_JOB] {job.job_id} failed: {e}", exc_info=True)
            await registry.mark_error(job.job_id, str(e))
            return
        if "error" in result:
            await registry.mark_error(job.job_id, str(result["error"]))
        else:
            await registry.mark_done(job.job_id, result)

    import asyncio

    task = asyncio.create_task(_background())
    registry.track_background_task(task)

    return responses.ok(
        success=True,
        job_id=job.job_id,
        status="running",
        project=directory_path,
        system_message=(
            f"Indexing started in the background (job_id={job.job_id}). "
            "Poll get_index_status(job_id=...) until status is 'done' or "
            "'error' before relying on search results reflecting this run."
        ),
    )


async def _run_index_directory(arguments: dict[str, Any]) -> dict:
    """Do the actual indexing work (the body formerly inline in the handler).

    Split out of ``handle_index_directory`` so it can be run either inline
    (``wait=True``, default) or as a background task (``wait=False``) without
    duplicating logic.
    """
    directory_path = arguments["directory_path"]
    arguments.get("project_name")
    incremental = arguments.get("incremental", True)
    include_dirs = arguments.get("include_dirs")
    exclude_dirs = arguments.get("exclude_dirs")

    logger.info(f"[INDEX] directory={directory_path}, incremental={incremental}")

    # Step 1: Cleanup previous resources BEFORE starting indexing
    # _cleanup_previous_resources() blocks (gc.collect, torch.cuda ops) — offload,
    # mirroring the pattern used at status_handlers.py and server.py.
    logger.info("[INDEX] Releasing previous resources before indexing...")
    import asyncio

    from mcp_server.resource_manager import _cleanup_previous_resources

    await asyncio.to_thread(_cleanup_previous_resources)

    directory_path = Path(directory_path).resolve()
    if not directory_path.exists():
        return responses.error(f"Directory does not exist: {directory_path}")

    # Step 2: Optional pre-index accessibility check (sample files for locks).
    # Walks the directory tree and opens files — offload off the event loop.
    await asyncio.to_thread(_run_accessibility_precheck, directory_path)

    # Check if project already exists and handle filter immutability.
    # Use get_canonical_project_info() so filter reads work regardless of which
    # model the current config default points to (prevents H1: null-overwrite when
    # the config model's dir has no project_info.json but another model's dir does).
    project_info_file = get_canonical_project_info(str(directory_path)) or (
        get_project_storage_dir(str(directory_path)) / "project_info.json"
    )

    # Load stored filters if project exists — file read blocks, offload.
    stored_include = None
    stored_exclude = None
    if project_info_file.exists():

        def _read_project_info() -> dict[str, Any]:
            with open(project_info_file) as f:
                return json.load(f)

        project_info = await asyncio.to_thread(_read_project_info)
        stored_include = project_info.get("user_included_dirs")
        stored_exclude = project_info.get("user_excluded_dirs")

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

        update_project_filters(str(directory_path), include_dirs, exclude_dirs)

    # Set as current project (using setter for proper cross-module sync)
    set_current_project(str(directory_path))

    # Temporarily disable allow_ram_fallback during indexing for performance
    with temporary_ram_fallback_off() as original_value:
        if original_value:
            logger.info(
                "[INDEX] RAM fallback auto-disabled for this indexing operation"
            )

        # Exclusive write lock on the per-project reader-writer lock: prevents
        # two concurrent index_directory calls (or a concurrent search_code
        # auto-reindex) from reindexing the same project simultaneously, and
        # blocks until any in-flight searches (readers) currently reading the
        # index have drained.
        async with get_state().get_reindex_rwlock(str(directory_path)).write():
            logger.info(f"Indexing for: {directory_path}")

            # Get or create project storage
            project_dir = get_project_storage_dir(str(directory_path))
            index_dir = project_dir / "index"
            index_dir.mkdir(exist_ok=True)

            # Load config for chunker initialization
            config = get_config()

            # Initialize chunker eagerly (cheap, no I/O or model load).
            # for_project() wires RepositoryRelationFilter so import edges are
            # classified (stdlib/third_party/local) rather than stored as "unknown".
            chunker = MultiLanguageChunker.for_project(
                str(directory_path),
                include_dirs,
                exclude_dirs,
                enable_entity_tracking=config.performance.enable_entity_tracking,
            )

            # Capture loop-local values before entering the thread.
            _dir = str(directory_path)
            _enable_hybrid = config.search_mode.enable_hybrid
            _incremental = incremental
            _include = include_dirs
            _exclude = exclude_dirs

            # get_embedder() and get_searcher() can trigger multi-second model/
            # index loads on first use — offload together with the indexing work
            # so the event loop is never blocked during component initialisation.
            import asyncio

            def _setup_and_run():
                _embedder = get_embedder()
                _searcher = get_searcher(_dir)
                _indexer = _searcher if _enable_hybrid else get_index_manager(_dir)
                return _run_indexing(
                    _indexer,
                    _embedder,
                    chunker,
                    _dir,
                    _incremental,
                    _include,
                    _exclude,
                )

            result = await asyncio.to_thread(_setup_and_run)

            # Build response (using helper)
            return _build_index_response(
                [result],
                str(directory_path),
                incremental=incremental,
                include_dirs=include_dirs,
                exclude_dirs=exclude_dirs,
            )
