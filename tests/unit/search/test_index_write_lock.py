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
    IndexFilesInUseError,
    IndexWriteLockHeldError,
    files_in_use_error,
    files_in_use_guard,
    index_write_lock,
    is_index_write_locked,
    is_lock_violation,
)
from tests.fixtures.lock_errors import lock_violation


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


class TestFilesInUseErrorMessage:
    """files_in_use_error builds the one user-facing text for a locked index
    file. The two variants differ in the one fact the reader needs: did the
    failed clear change the index or not?"""

    def test_unchanged_variant_names_file_and_says_index_not_changed(self, tmp_path):
        path = tmp_path / "metadata.db"
        err = files_in_use_error(path, index_changed=False)

        assert isinstance(err, IndexFilesInUseError)
        assert isinstance(err, PermissionError)
        text = str(err)
        assert "metadata.db is open in another process" in text
        assert str(path) in text
        assert "not changed" in text
        assert "incomplete" not in text
        assert "MCP server" in text
        assert "index_directory" in text

    def test_changed_variant_says_index_incomplete_and_how_to_rebuild(self, tmp_path):
        path = tmp_path / "metadata.db-wal"
        err = files_in_use_error(path, index_changed=True)

        text = str(err)
        assert "metadata.db-wal is open in another process" in text
        assert str(path) in text
        assert "incomplete" in text
        assert "force reindex" in text
        assert "not changed" not in text
        assert "MCP server" in text
        # Same two routes as the unchanged variant, so the advice never conflicts.
        assert "index_directory" in text
        assert "incremental=False" in text


class TestFilesInUseGuard:
    """files_in_use_guard turns a PermissionError from a delete into the clear
    IndexFilesInUseError, so no call site repeats the try/except."""

    def test_converts_permission_error_using_the_failing_file(self, tmp_path):
        locked = tmp_path / "code.index"
        with (
            pytest.raises(IndexFilesInUseError) as excinfo,
            files_in_use_guard(tmp_path, index_changed=True),
        ):
            raise lock_violation(str(locked))

        text = str(excinfo.value)
        assert str(locked) in text, "the file the OS named wins over the hint"
        assert "incomplete" in text
        assert isinstance(excinfo.value.__cause__, PermissionError)

    def test_falls_back_to_the_hint_when_the_error_names_no_file(self, tmp_path):
        with (
            pytest.raises(IndexFilesInUseError) as excinfo,
            files_in_use_guard(tmp_path / "bm25", index_changed=True),
        ):
            raise lock_violation()

        assert str(tmp_path / "bm25") in str(excinfo.value)

    def test_message_follows_index_changed(self, tmp_path):
        with (
            pytest.raises(IndexFilesInUseError) as excinfo,
            files_in_use_guard(tmp_path / "metadata.db", index_changed=False),
        ):
            raise lock_violation()

        assert "not changed" in str(excinfo.value)
        assert "incomplete" not in str(excinfo.value)

    def test_is_lock_violation_reads_the_windows_error_code(self):
        assert is_lock_violation(lock_violation(winerror=32)) is True
        assert is_lock_violation(lock_violation(winerror=33)) is True
        assert is_lock_violation(lock_violation(winerror=5)) is False
        # No Windows error code at all (any POSIX PermissionError, or a bare one).
        assert is_lock_violation(PermissionError("denied")) is False

    def test_access_denied_is_not_reported_as_a_lock(self, tmp_path):
        """Windows error 5 is a real permission problem (read-only file, ACL
        denial). Calling it 'open in another process' would send the reader to
        the wrong fix, so it must reach the caller as the original error."""
        denied = lock_violation(str(tmp_path / "metadata.db"), winerror=5)
        with (
            pytest.raises(PermissionError) as excinfo,
            files_in_use_guard(tmp_path, index_changed=True),
        ):
            raise denied

        assert excinfo.value is denied
        assert not isinstance(excinfo.value, IndexFilesInUseError)

    def test_passes_an_existing_files_in_use_error_through_unchanged(self, tmp_path):
        original = IndexFilesInUseError("built by the probe")
        with (
            pytest.raises(IndexFilesInUseError) as excinfo,
            files_in_use_guard(tmp_path, index_changed=True),
        ):
            raise original

        assert excinfo.value is original

    def test_leaves_other_exceptions_alone(self, tmp_path):
        with (
            pytest.raises(ValueError, match="not a lock"),
            files_in_use_guard(tmp_path, index_changed=True),
        ):
            raise ValueError("not a lock")

    def test_no_error_means_no_effect(self, tmp_path):
        with files_in_use_guard(tmp_path, index_changed=True):
            result = 1 + 1

        assert result == 2


class TestIndexWriteLockHeldMessage:
    """IndexWriteLockHeldError text must name the lock file, say nothing was
    changed, and say what to do -- not just 'already held for <dir>'."""

    def test_message_names_lock_file_and_next_step(self, tmp_path):
        storage_dir = tmp_path / "index"
        with (
            index_write_lock(storage_dir),
            pytest.raises(IndexWriteLockHeldError) as excinfo,
            index_write_lock(storage_dir),
        ):
            pass  # pragma: no cover - must never be entered

        text = str(excinfo.value)
        assert "Another indexer is already writing this project's index" in text
        assert _LOCK_FILE_NAME in text
        assert str(storage_dir) in text
        assert "Nothing was changed" in text
        assert "try again" in text


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
        assert not is_index_write_locked(storage_dir)
        with index_write_lock(storage_dir):
            pass  # no IndexWriteLockHeldError -- the first lock let go
        assert not is_index_write_locked(storage_dir)

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
        assert result.error is not None and "already writing" in result.error
        assert "Nothing was changed" in result.error
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
        assert result.error is None or "already writing" not in (result.error or "")


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
