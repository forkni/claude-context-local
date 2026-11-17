"""Inter-process mutual exclusion for a project's index storage directory.

Before this module existed, the only mutual exclusion around an index
storage directory was the MCP server's in-process ``_AsyncRWLock``
(``mcp_server/state.py::get_reindex_rwlock``) — nothing stopped a CLI
indexer (``tools/batch_index.py``) and the server's own auto-reindex from
writing the same ``metadata.db``/FAISS/BM25 files at the same time. That is
exactly what happened in the 2026-09-25 twozero-dev incident: a CLI
force-full reindex held ``metadata.db`` open while the running server's
auto-reindex raced it, cleared every row via
``CodeIndexManager.preflight_clear()``, then aborted on ``WinError 32`` —
but the CLI went on to save FAISS/BM25/graph on top of an already-empty
metadata store, failing its own post-index consistency check. See the
2026-09-25 amendment to ``docs/adr/0025-clear-index-directory-in-place.md``.

``filelock.FileLock`` is an OS-level lock (``LockFile``/``flock``) that the
OS releases automatically if the holding process dies, so a crashed indexer
can never strand the lock. ``search/incremental_indexer.py::incremental_index``
is the single chokepoint this wraps — the shared entry point for CLI
force-full reindex, MCP ``index_directory``, and auto-reindex.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock, Timeout


logger = logging.getLogger(__name__)

_LOCK_FILE_NAME = "index_write.lock"


class IndexWriteLockHeldError(RuntimeError):
    """Raised when another process already holds a project's index write lock."""


class IndexFilesInUseError(PermissionError):
    """Raised when an index file (metadata.db) is open in another process.

    Unlike ``IndexWriteLockHeldError`` (another *writer* holds the write lock),
    this is a *reader* -- typically the running MCP server with the project
    loaded -- holding the file, so the write lock was free. The failed clear is
    a no-op: the existing index is untouched. Subclasses ``PermissionError`` so
    callers and tests that catch ``PermissionError``/``OSError`` keep working;
    the raw ``WinError`` is kept as ``__cause__``.
    """


def files_in_use_error(
    path: Path | str, *, index_changed: bool
) -> IndexFilesInUseError:
    """Build the user-facing error for an index file held open elsewhere.

    One builder keeps every raise site on the same wording. The only thing
    that varies is the fact the reader needs first: whether the failed clear
    changed the index.

    Args:
        path: The file or directory another process holds open.
        index_changed: False when the failure came before anything was
            deleted (the probe rename), True when part of the index is
            already gone (deletes after the probe).

    Returns:
        The error to raise. Callers chain the original ``PermissionError``
        with ``raise ... from exc`` so the raw ``WinError`` stays in
        ``__cause__``.
    """
    name = Path(path).name or str(path)
    holder = (
        "Likely holder: the running code-search MCP server with this project "
        "loaded, or a second indexer."
    )
    if index_changed:
        message = (
            f"Cannot finish clearing the index: {name} is open in another process.\n"
            f"  File: {path}\n"
            "The index is now incomplete.\n"
            f"{holder} Stop that process, then run a force reindex "
            "(index_directory with incremental=False) to rebuild it."
        )
    else:
        message = (
            f"Cannot rebuild the index: {name} is open in another process.\n"
            f"  File: {path}\n"
            "The existing index was not changed.\n"
            f"{holder} Stop that process, or run this reindex through the MCP "
            "server's index_directory tool (it releases its own handle first), "
            "then try again."
        )
    return IndexFilesInUseError(message)


@contextmanager
def files_in_use_guard(path_hint: Path | str, *, index_changed: bool) -> Iterator[None]:
    """Turn a ``PermissionError`` raised inside the block into the clear error.

    Wrap each delete of an index file with this instead of repeating a
    ``try/except``. An ``IndexFilesInUseError`` raised inside the block (for
    example by a nested guard or the probe) passes through unchanged.

    Args:
        path_hint: File or directory to name when the ``PermissionError``
            carries no file name of its own.
        index_changed: Same meaning as in :func:`files_in_use_error`.

    Raises:
        IndexFilesInUseError: Built from the ``PermissionError``, which stays
            available as ``__cause__``.
    """
    try:
        yield
    except IndexFilesInUseError:
        raise
    except PermissionError as exc:
        raise files_in_use_error(
            exc.filename or path_hint, index_changed=index_changed
        ) from exc


def _lock_path(storage_dir: Path | str) -> Path:
    return Path(storage_dir) / _LOCK_FILE_NAME


@contextmanager
def index_write_lock(storage_dir: Path | str) -> Iterator[None]:
    """Acquire the exclusive, cross-process write lock for *storage_dir*.

    Non-blocking: fails immediately (``timeout=0``) rather than queueing —
    a queued waiter would just as easily race the same
    clear-before-probe-style destructive step this lock exists to prevent,
    since nothing about waiting makes a subsequent acquire safe to run
    concurrently with the holder's own writes.

    Args:
        storage_dir: The project's index storage directory (the same
            directory ``CodeIndexManager`` uses — one level below the
            project's model-scoped storage root). Created if it doesn't
            exist yet, so the lock file itself never blocks on a missing
            directory during first-time indexing.

    Yields:
        Nothing — used purely for its enter/exit side effects.

    Raises:
        IndexWriteLockHeldError: Another process already holds the lock for this
            *storage_dir*.
    """
    storage_dir = Path(storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)
    lock = FileLock(str(_lock_path(storage_dir)), timeout=0)
    try:
        lock.acquire()
    except Timeout as exc:
        raise IndexWriteLockHeldError(
            "Another indexer is already writing this project's index "
            f"(lock: {_lock_path(storage_dir)}). Nothing was changed. "
            "Wait for it to finish, then try again."
        ) from exc
    try:
        yield
    finally:
        lock.release()


def is_index_write_locked(storage_dir: Path | str) -> bool:
    """Cheap try-acquire/release probe for *storage_dir*'s write lock.

    Used as a pre-gate (e.g. ``mcp_server/tools/search_orchestrator.py``'s
    auto-reindex check) to skip building a full searcher — which would map
    ``code_vectors.mmap`` and could itself block the other process's save —
    when a concurrent writer is already known to hold the lock.

    Args:
        storage_dir: The project's index storage directory.

    Returns:
        True iff another process currently holds the lock. False both when
        the lock is free and when *storage_dir* doesn't exist yet (nothing
        has ever indexed this project, so there is nothing to hold a lock
        on).
    """
    storage_dir = Path(storage_dir)
    if not storage_dir.exists():
        return False
    lock = FileLock(str(_lock_path(storage_dir)), timeout=0)
    try:
        lock.acquire()
    except Timeout:
        return True
    lock.release()
    return False
