"""Regression tests for search/index_write_lock.py.

Covers the 2026-09-25 twozero-dev incident's Step 2 fix: a cross-process
mutual-exclusion lock around a project's index storage directory, so a CLI
force-full reindex and the MCP server's auto-reindex can never write the
same metadata.db/FAISS/BM25 files concurrently (see
docs/adr/0025-clear-index-directory-in-place.md, 2026-09-25 amendment).

(a) contention -- a second holder of the same storage_dir's lock, both
    in-process (a second FileLock object) and across a real subprocess.
(b) IncrementalIndexer.incremental_index wraps its whole body in the lock
    and fails clean (never touches clear_index) when it's already held.
(c) the orchestrator's cheap pre-gate skips _check_auto_reindex entirely
    when the lock is already held, instead of building a HybridSearcher
    first and failing only once incremental_index's own lock acquisition
    does -- see tests/unit/mcp_server/test_search_orchestrator.py.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from filelock import FileLock, Timeout

from search.incremental_indexer import IncrementalIndexer, IncrementalIndexResult
from search.index_write_lock import (
    _LOCK_FILE_NAME,
    IndexWriteLockHeldError,
    index_write_lock,
    is_index_write_locked,
)


def _successful_result() -> IncrementalIndexResult:
    return IncrementalIndexResult(
        success=True,
        files_added=0,
        files_removed=0,
        files_modified=0,
        chunks_added=0,
        chunks_removed=0,
        time_taken=0.0,
    )


class TestIndexWriteLockInProcessContention:
    """A second FileLock on the same storage_dir must not be able to
    acquire while the first is held -- this is what makes a concurrent CLI
    reindex and MCP auto-reindex mutually exclusive within one process too,
    not just across processes."""

    def test_second_acquire_raises_index_write_lock_held(self, tmp_path):
        storage_dir = tmp_path / "index"
        with (
            index_write_lock(storage_dir),
            pytest.raises(IndexWriteLockHeldError),
            index_write_lock(storage_dir),
        ):
            pass  # pragma: no cover - must never be entered

    def test_lock_file_created_under_storage_dir(self, tmp_path):
        storage_dir = tmp_path / "index"
        with index_write_lock(storage_dir):
            assert (storage_dir / _LOCK_FILE_NAME).exists()

    def test_storage_dir_created_if_missing(self, tmp_path):
        storage_dir = tmp_path / "does" / "not" / "exist" / "index"
        assert not storage_dir.exists()
        with index_write_lock(storage_dir):
            assert storage_dir.exists()

    def test_released_on_clean_exit_so_a_later_acquire_succeeds(self, tmp_path):
        storage_dir = tmp_path / "index"
        with index_write_lock(storage_dir):
            pass
        with index_write_lock(storage_dir):
            pass  # no IndexWriteLockHeldError -- the first lock let go

    def test_released_even_when_the_held_block_raises(self, tmp_path):
        storage_dir = tmp_path / "index"
        with pytest.raises(ValueError), index_write_lock(storage_dir):
            raise ValueError("boom")
        # A crashed holder's OS-level lock is released with the process/
        # context, so a fresh acquire must still succeed afterwards.
        with index_write_lock(storage_dir):
            pass

    def test_is_index_write_locked_false_for_nonexistent_dir(self, tmp_path):
        assert is_index_write_locked(tmp_path / "never-indexed") is False

    def test_is_index_write_locked_false_when_free(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        assert is_index_write_locked(storage_dir) is False

    def test_is_index_write_locked_true_while_held(self, tmp_path):
        storage_dir = tmp_path / "index"
        with index_write_lock(storage_dir):
            assert is_index_write_locked(storage_dir) is True

    def test_is_index_write_locked_probe_does_not_strand_the_lock(self, tmp_path):
        """The probe's own try-acquire/release must not itself leave the
        lock held -- a bug here would make every later real acquire fail
        even after the true holder released it."""
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        assert is_index_write_locked(storage_dir) is False
        with index_write_lock(storage_dir):
            pass  # the probe above must not have left a stray lock behind


class TestIndexWriteLockSubprocessContention:
    """Real cross-process contention -- an actual second process holding
    the OS-level lock, not just a second Python object in this process.
    This is the literal 2026-09-25 scenario: a CLI process and the MCP
    server process racing the same storage_dir."""

    def test_second_process_cannot_acquire_while_first_holds_it(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        ready_marker = tmp_path / "ready"
        release_marker = tmp_path / "release"
        script = f"""
import time
from pathlib import Path
from filelock import FileLock

lock = FileLock(str(Path({str(storage_dir)!r}) / {_LOCK_FILE_NAME!r}))
lock.acquire()
Path({str(ready_marker)!r}).write_text("ready")
while not Path({str(release_marker)!r}).exists():
    time.sleep(0.05)
lock.release()
"""
        proc = subprocess.Popen([sys.executable, "-c", script])
        try:
            deadline = time.time() + 10
            while not ready_marker.exists():
                assert time.time() < deadline, "subprocess never signalled ready"
                time.sleep(0.05)

            assert is_index_write_locked(storage_dir) is True
            with pytest.raises(IndexWriteLockHeldError), index_write_lock(storage_dir):
                pass  # pragma: no cover - must never be entered
        finally:
            release_marker.write_text("release")
            proc.wait(timeout=10)

        # Once the subprocess released it, this process can acquire cleanly.
        assert is_index_write_locked(storage_dir) is False
        with index_write_lock(storage_dir):
            pass


class TestIncrementalIndexRespectsHeldLock:
    """IncrementalIndexer.incremental_index wraps its whole body in
    index_write_lock (see search/incremental_indexer.py) -- with the lock
    already held by someone else, it must fail clean and never touch
    clear_index, instead of racing the holder the way preflight_clear()'s
    pre-probe destructive clear used to (the root cause of the 2026-09-25
    twozero-dev incident, H1)."""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir) / "test_project"
        self.project_path.mkdir(parents=True, exist_ok=True)
        self.storage_dir = Path(self.temp_dir) / "index"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.mock_indexer = Mock()
        self.mock_indexer.storage_dir = str(self.storage_dir)
        self.mock_indexer.clear_index = Mock()
        self.mock_embedder = Mock()
        self.mock_chunker = Mock()
        self.mock_snapshot_manager = Mock()

    def teardown_method(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_incremental_index_fails_clean_when_lock_already_held(self):
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        with index_write_lock(self.storage_dir):
            result = indexer.incremental_index(
                str(self.project_path), "test_project", force_full=True
            )

        assert result.success is False
        assert result.error is not None and "index write lock" in result.error
        self.mock_indexer.clear_index.assert_not_called()

    def test_incremental_index_succeeds_once_the_lock_is_free(self):
        """Sanity check the negative test above isn't vacuous: the same
        call, without a pre-held lock, reaches _full_index (and
        clear_index) as normal. _full_index itself is faked out -- driving
        it to a real success needs a fully-populated snapshot/filter mock
        unrelated to what this test is checking -- but the fake still goes
        through self.indexer.clear_index(), the exact call site the "held"
        test above asserts is never reached."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        def _fake_full_index(self_indexer, *args, **kwargs):
            self_indexer.indexer.clear_index()
            return _successful_result()

        with patch.object(
            IncrementalIndexer,
            "_full_index",
            autospec=True,
            side_effect=_fake_full_index,
        ):
            result = indexer.incremental_index(
                str(self.project_path), "test_project", force_full=True
            )

        assert result.success is True
        self.mock_indexer.clear_index.assert_called()

    def test_lock_released_after_incremental_index_returns(self):
        """The lock incremental_index takes for itself must not outlive the
        call -- otherwise every reindex after the first would permanently
        see the project as locked."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )
        self.mock_indexer.validate_index_consistency = Mock(return_value=(True, []))

        indexer.incremental_index(
            str(self.project_path), "test_project", force_full=True
        )

        assert is_index_write_locked(self.storage_dir) is False

    def test_no_storage_dir_resolved_runs_unlocked_like_before(self):
        """A bare test double with no storage_dir (most unit tests) must
        keep working exactly as it did before this lock was added -- the
        lock only ever applies when a real storage directory resolves."""
        bare_mock_indexer = Mock(spec=[])  # no storage_dir attribute at all
        bare_mock_indexer.resync_if_desynced = Mock(return_value=(False, 0))
        bare_mock_indexer.validate_index_consistency = Mock(return_value=(True, []))
        bare_mock_indexer.clear_index = Mock()

        indexer = IncrementalIndexer(
            indexer=bare_mock_indexer,
            embedder=self.mock_embedder,
            chunker=self.mock_chunker,
            snapshot_manager=self.mock_snapshot_manager,
        )

        def _fake_full_index(self_indexer, *args, **kwargs):
            self_indexer.indexer.clear_index()
            return _successful_result()

        with patch.object(
            IncrementalIndexer,
            "_full_index",
            autospec=True,
            side_effect=_fake_full_index,
        ):
            result = indexer.incremental_index(
                str(self.project_path), "test_project", force_full=True
            )

        # No lock in play at all: this must reach clear_index normally
        # rather than returning the "another process" failure.
        bare_mock_indexer.clear_index.assert_called()
        assert result.success is True
        assert result.error is None or "index write lock" not in (result.error or "")


class TestFileLockTimeoutBehavior:
    """Locks down the timeout=0 (fail-fast, no queueing) contract that
    index_write_lock relies on filelock.FileLock to provide."""

    def test_filelock_itself_raises_timeout_not_something_else(self, tmp_path):
        lock_path = tmp_path / "raw.lock"
        first = FileLock(str(lock_path), timeout=0)
        second = FileLock(str(lock_path), timeout=0)
        first.acquire()
        try:
            with pytest.raises(Timeout):
                second.acquire()
        finally:
            first.release()
