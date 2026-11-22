"""Regression test for CodeIndexManager.clear_index() file deletion scope.

CodeIndexManager.clear_index() is not an admin-only operation — it is the
mechanism behind every force-full reindex (IncrementalIndexer.incremental_index
(force_full=True) -> HybridSearcher.clear_index() -> IndexSynchronizer.
clear_index() -> CodeIndexManager.clear_index()). A prior version of this fix
had it delete chunk_embeddings.bin unconditionally, which cold-started the
persistent chunk embedding cache on every force-full reindex, defeating the
entire feature (33.94s -> 0.78s embedding phase). The explicit admin "clear
index" action (handle_clear_index) never calls this method — it does its own,
independent file purge and is the only place chunk_embeddings.bin should be
deleted.
"""

import os
import pickle
import sys
from pathlib import Path

import faiss
import numpy as np
import pytest

from search.faiss_index import FaissVectorIndex
from search.index_write_lock import IndexFilesInUseError
from search.indexer import CodeIndexManager, probe_metadata_deletable
from search.metadata import MetadataStore
from search.mmap_vectors import MmapVectorStorage
from tests.fixtures.lock_errors import lock_violation


class TestClearIndexPreservesChunkCache:
    def test_clear_index_keeps_chunk_embeddings_bin(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()

        manager = CodeIndexManager(storage_dir=str(storage_dir))

        chunk_cache = storage_dir / "chunk_embeddings.bin"
        chunk_cache.write_bytes(b"fake cache contents")
        (storage_dir / "stats.json").write_text("{}")
        (storage_dir / "metadata_symbol_cache.json").write_text("{}")
        wal = storage_dir / "metadata.db-wal"
        shm = storage_dir / "metadata.db-shm"
        wal.write_bytes(b"wal")
        shm.write_bytes(b"shm")

        manager.clear_index()

        assert chunk_cache.exists(), (
            "clear_index() must preserve chunk_embeddings.bin — it runs on "
            "every force-full reindex, not just an explicit admin clear"
        )
        assert not (storage_dir / "stats.json").exists()
        assert not (storage_dir / "metadata_symbol_cache.json").exists()
        assert not wal.exists()
        assert not shm.exists()


class TestClearIndexSweepsLegacyCommunityFiles:
    """Regression test for a dead-code bug found during the ADR-0015 community
    subsystem deletion post-mortem.

    _clear_index_files_before_create (mcp_server/tools/index_handlers.py) held
    the only glob that ever swept a legacy `*_communities.json` sidecar, but its
    sole call site was removed as collateral damage in 4ec76278 ("refactor:
    remove multi-model routing") — it has had zero production callers since.
    CodeIndexManager.clear_index() is the actual mechanism behind every
    force-full reindex, and never swept this file, so a legacy
    `*_communities.json` (written by the community subsystem deleted in
    ADR-0015) survives force-full reindexes indefinitely.
    """

    def test_clear_index_sweeps_legacy_communities_json(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()

        manager = CodeIndexManager(storage_dir=str(storage_dir))

        # *_communities.json lives one level up from the model's index/ dir,
        # a sibling of it — matching _purge_index_dir's documented layout.
        legacy = tmp_path / "myproject_communities.json"
        legacy.write_text("{}")

        manager.clear_index()

        assert not legacy.exists(), (
            "clear_index() must sweep legacy *_communities.json sidecars — "
            "nothing writes them since ADR-0015, but nothing was purging them "
            "either"
        )


class TestClearIndexFailsFastOnLockedMetadata:
    """Regression test for the inverted-deletion-order bug: clear_index() used
    to delete FAISS and BM25 state before ever attempting to delete
    metadata.db, so a locked metadata.db (a live SQLite handle on Windows)
    surfaced its PermissionError only after everything else was already gone
    — a half-cleared index with no rollback. The fix probes metadata.db's
    deletability (via os.replace) before touching FAISS at all.
    """

    def test_clear_index_raises_before_touching_faiss_when_metadata_locked(
        self, tmp_path, monkeypatch
    ):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()

        manager = CodeIndexManager(storage_dir=str(storage_dir))

        chunk_cache = storage_dir / "chunk_embeddings.bin"
        chunk_cache.write_bytes(b"fake cache contents")
        stats = storage_dir / "stats.json"
        stats.write_text("{}")
        metadata_db = storage_dir / "metadata.db"
        # A real, openable metadata.db (not garbage bytes): preflight_clear()
        # now clears rows in place before probing deletability, so this must
        # be a store that can actually be opened -- the failure this test
        # exercises is the *rename* (os.replace) failing, e.g. a still-open
        # Windows handle from another process, not an unopenable file.
        manager.metadata_store.set("a.py:1-2:function:f", 0, {"relative_path": "a.py"})
        manager.metadata_store.commit()
        manager.metadata_store.close()
        assert metadata_db.exists()

        def _raise_permission_error(*_args, **_kwargs):
            raise lock_violation(str(metadata_db))

        monkeypatch.setattr(os, "replace", _raise_permission_error)

        faiss_clear_called = False
        original_clear = manager._faiss_index.clear

        def _tracking_clear():
            nonlocal faiss_clear_called
            faiss_clear_called = True
            return original_clear()

        monkeypatch.setattr(manager._faiss_index, "clear", _tracking_clear)

        # IndexFilesInUseError subclasses PermissionError, so existing
        # `except OSError` / `except PermissionError` callers keep working.
        with pytest.raises(IndexFilesInUseError) as excinfo:
            manager.clear_index()

        assert isinstance(excinfo.value, PermissionError)
        message = str(excinfo.value)
        assert str(metadata_db) in message, "the message must name the locked file"
        assert "not changed" in message, (
            "the message must say the existing index was left intact"
        )
        assert "MCP server" in message, "the message must name the likely holder"
        assert "index_directory" in message, "the message must say how to proceed"
        assert "WinError" not in message, (
            "the raw OS error belongs in __cause__, not the user-facing text"
        )
        assert isinstance(excinfo.value.__cause__, PermissionError)

        assert not faiss_clear_called, (
            "FAISS must not be cleared until metadata.db is proven deletable"
        )
        assert metadata_db.exists(), (
            "a failed probe must leave metadata.db exactly where it was — "
            "the clear is a no-op, not a half-clear"
        )
        assert stats.exists(), "stats.json must survive an aborted clear too"

        # The row itself must survive, not just the file. preflight_clear()
        # used to call MetadataStore.clear() (DELETE FROM, committed) BEFORE
        # probing deletability, so a failed probe still left an empty-but-
        # present metadata.db — the file existed but the row was already
        # gone. This is the exact 2026-09-25 twozero-dev incident: the
        # server's auto-reindex hit a locked metadata.db held by a
        # concurrent CLI force-full reindex, aborted on WinError 32, but had
        # already deleted every row by then.
        manager.metadata_store.close()
        reopened = MetadataStore(metadata_db)
        try:
            assert len(reopened) == 1, (
                "a failed probe must leave metadata.db's rows intact, not "
                "just the file — clear() must not run before the probe "
                "succeeds"
            )
        finally:
            reopened.close()

    @pytest.mark.skipif(
        sys.platform != "win32",
        reason="reproduces a Windows-only file-lock failure mode (os.replace "
        "succeeds against an open handle on POSIX)",
    )
    def test_clear_index_survives_a_real_locked_handle_from_another_process(
        self, tmp_path
    ):
        """Same defect as the monkeypatched test above, but reproduced with a
        real live SQLite handle instead of a patched os.replace — the actual
        production failure mode (a second process, here a second
        MetadataStore instance, holding metadata.db open) rather than a
        simulated one.
        """
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()

        manager = CodeIndexManager(storage_dir=str(storage_dir))
        manager.metadata_store.set("a.py:1-2:function:f", 0, {"relative_path": "a.py"})
        manager.metadata_store.commit()
        metadata_db = storage_dir / "metadata.db"
        assert metadata_db.exists()

        # A second, independent handle on the same metadata.db — standing in
        # for the concurrent process that held the file open in production.
        other_handle = MetadataStore(metadata_db)
        other_handle.get("a.py:1-2:function:f")  # force the connection open
        try:
            with pytest.raises(IndexFilesInUseError) as excinfo:
                manager.clear_index()

            assert str(metadata_db) in str(excinfo.value)
            assert "not changed" in str(excinfo.value)

            assert metadata_db.exists(), (
                "a failed probe must leave metadata.db exactly where it was"
            )
            assert len(other_handle) == 1, (
                "the row must survive a probe failure against a real "
                "locked handle, not just a monkeypatched one"
            )
        finally:
            other_handle.close()

    # A metadata.db that exists but can't be opened as SQLite at all (as
    # opposed to a valid-but-locked one) is deliberately not covered by a
    # test here: MetadataStore.clear() -> _ensure_open() would raise
    # sqlite3.DatabaseError from SqliteDict's background connection thread,
    # and that thread's own unhandled-exception report surfaces via pytest's
    # thread-exception plugin at the *next* test's setup, not this one --
    # polluting an unrelated test rather than failing cleanly here. The
    # no-half-clear guarantee still holds in that scenario (clear() raises
    # before FAISS/reset/probe run), it's just not practical to assert
    # without destabilizing the suite; see preflight_clear()'s docstring.

    def test_probe_metadata_deletable_is_idempotent(self, tmp_path):
        metadata_path = tmp_path / "metadata.db"
        metadata_path.write_bytes(b"fake sqlite db")

        first = probe_metadata_deletable(metadata_path)
        assert first == Path(str(metadata_path) + ".deleting")
        assert first.exists()
        assert not metadata_path.exists()

        # Second call (e.g. IndexSynchronizer's preflight followed by
        # CodeIndexManager.clear_index()'s own probe) must be a no-op that
        # returns the same already-renamed path, not raise or re-rename.
        second = probe_metadata_deletable(metadata_path)
        assert second == first
        assert second.exists()

    def test_probe_metadata_deletable_no_file_returns_original_path(self, tmp_path):
        metadata_path = tmp_path / "metadata.db"
        assert not metadata_path.exists()

        result = probe_metadata_deletable(metadata_path)

        assert result == metadata_path


class TestClearIndexDiscardsStaleDeletingDebris:
    """Regression test for the force-full-reindex metadata-orphan bug.

    A stale ``metadata.db.deleting`` sibling — stranded by a previously
    aborted clear (e.g. mid-chain WinError 32) — used to shadow the live
    ``metadata.db``: probe_metadata_deletable() short-circuited on it and
    returned the stale path without renaming the live DB, so clear_index()
    unlinked only the stale sibling while the real DB, still holding a
    previous index generation's rows, was silently reopened untouched. This
    is exactly what happened on voro-engine's force-full reindex: 148 rows
    from a pre-rename generation (cito_* symbols in a project since renamed
    to voro_*) survived a reported-successful "full" clear and failed the
    post-index consistency check minutes later.
    """

    def test_stale_deleting_sibling_does_not_shadow_live_metadata(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()

        manager = CodeIndexManager(storage_dir=str(storage_dir))
        manager.metadata_store.set("a.py:1-2:function:f", 0, {"relative_path": "a.py"})
        manager.metadata_store.commit()
        manager.metadata_store.close()

        # Debris from an aborted clear, planted before this clear runs.
        (storage_dir / "metadata.db.deleting").write_bytes(b"stale")

        manager.clear_index()

        assert len(manager.metadata_store) == 0, (
            "a live metadata.db must always be renamed and cleared, even "
            "when a stale .deleting sibling already exists"
        )

    def test_probe_metadata_deletable_discards_stale_sibling_and_renames_live_db(
        self, tmp_path
    ):
        metadata_path = tmp_path / "metadata.db"
        metadata_path.write_bytes(b"live sqlite db")
        deleting_path = Path(str(metadata_path) + ".deleting")
        deleting_path.write_bytes(b"stale debris from an aborted clear")

        result = probe_metadata_deletable(metadata_path)

        assert result == deleting_path
        assert deleting_path.read_bytes() == b"live sqlite db", (
            "the live DB's bytes must win — the stale sibling is discarded, "
            "not the other way around"
        )
        assert not metadata_path.exists()

        # Second call in the chain (e.g. CodeIndexManager.clear_index()'s
        # own probe, after IndexSynchronizer.clear_index() already ran it)
        # must still be a no-op — metadata.db is gone, .deleting stands.
        second = probe_metadata_deletable(metadata_path)
        assert second == deleting_path
        assert second.read_bytes() == b"live sqlite db"

    def test_probe_leaves_access_denied_as_a_plain_permission_error(
        self, tmp_path, monkeypatch
    ):
        """Windows error 5 (read-only file, ACL denial) is not a lock: the
        probe must not call it 'open in another process'."""
        metadata_path = tmp_path / "metadata.db"
        metadata_path.write_bytes(b"live sqlite db")
        denied = lock_violation(str(metadata_path), winerror=5)

        def _raise_denied(*_args, **_kwargs):
            raise denied

        monkeypatch.setattr(os, "replace", _raise_denied)

        with pytest.raises(PermissionError) as excinfo:
            probe_metadata_deletable(metadata_path)

        assert excinfo.value is denied
        assert not isinstance(excinfo.value, IndexFilesInUseError)

    def test_locked_stale_deleting_sibling_reports_unchanged_index(
        self, tmp_path, monkeypatch
    ):
        """The stale-debris unlink runs before the rename, so a lock on it is
        still a no-op failure: same clear message, live DB left in place."""
        metadata_path = tmp_path / "metadata.db"
        metadata_path.write_bytes(b"live sqlite db")
        deleting_path = Path(str(metadata_path) + ".deleting")
        deleting_path.write_bytes(b"stale debris from an aborted clear")

        original_unlink = Path.unlink

        def _locked_unlink(self, *args, **kwargs):
            if self.name.endswith(".deleting"):
                raise lock_violation(str(self))
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _locked_unlink)

        with pytest.raises(IndexFilesInUseError) as excinfo:
            probe_metadata_deletable(metadata_path)

        assert str(deleting_path) in str(excinfo.value)
        assert "not changed" in str(excinfo.value)
        assert metadata_path.read_bytes() == b"live sqlite db"


class TestClearIndexReportsLockedSidecarsAsIncomplete:
    """Files unlinked AFTER the probe (-wal/-shm/stats.json) can still be held
    open by another process. By then FAISS is already cleared, so the message
    must say the index is incomplete, not that it was left unchanged.
    """

    def test_locked_wal_file_raises_files_in_use_with_incomplete_index(
        self, tmp_path, monkeypatch
    ):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        manager = CodeIndexManager(storage_dir=str(storage_dir))
        manager.metadata_store.set("a.py:1-2:function:f", 0, {"relative_path": "a.py"})
        manager.metadata_store.commit()
        manager.metadata_store.close()
        wal_path = Path(str(storage_dir / "metadata.db") + "-wal")
        wal_path.write_bytes(b"wal sidecar held by another process")

        original_unlink = Path.unlink

        def _locked_unlink(self, *args, **kwargs):
            if self.name.endswith("-wal"):
                raise lock_violation(str(self))
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _locked_unlink)

        with pytest.raises(IndexFilesInUseError) as excinfo:
            manager.clear_index()

        message = str(excinfo.value)
        assert str(wal_path) in message, "the message must name the locked sidecar"
        assert "incomplete" in message
        assert "not changed" not in message, (
            "FAISS was already cleared, so claiming the index is unchanged "
            "would be false"
        )
        assert isinstance(excinfo.value.__cause__, PermissionError)


class TestClearIndexReportsLockedFaissAndGraphFiles:
    """The FAISS files and the call-graph JSON are deleted after the probe has
    already renamed metadata.db, so a lock on either leaves an incomplete
    index and must say so instead of raising a raw PermissionError."""

    @staticmethod
    def _manager_with_probe_passing(tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        manager = CodeIndexManager(storage_dir=str(storage_dir))
        manager.metadata_store.set("a.py:1-2:function:f", 0, {"relative_path": "a.py"})
        manager.metadata_store.commit()
        manager.metadata_store.close()
        return storage_dir, manager

    def test_locked_faiss_file_reports_incomplete_index(self, tmp_path, monkeypatch):
        storage_dir, manager = self._manager_with_probe_passing(tmp_path)
        locked = storage_dir / "code.index"

        def _locked_clear():
            raise lock_violation(str(locked))

        monkeypatch.setattr(manager._faiss_index, "clear", _locked_clear)

        with pytest.raises(IndexFilesInUseError) as excinfo:
            manager.clear_index()

        message = str(excinfo.value)
        assert str(locked) in message
        assert "incomplete" in message
        assert "not changed" not in message
        assert isinstance(excinfo.value.__cause__, PermissionError)

    def test_locked_call_graph_file_reports_incomplete_index(
        self, tmp_path, monkeypatch
    ):
        storage_dir, manager = self._manager_with_probe_passing(tmp_path)
        locked = tmp_path / "proj_call_graph.json"

        def _locked_clear():
            raise lock_violation(str(locked))

        monkeypatch.setattr(manager._graph, "clear", _locked_clear)

        with pytest.raises(IndexFilesInUseError) as excinfo:
            manager.clear_index()

        message = str(excinfo.value)
        assert str(locked) in message
        assert "incomplete" in message


class TestCloseReleasesFaissMmapHandle:
    """Regression test for the WinError 32 force-reindex failure.

    CodeIndexManager.close() previously closed only the metadata store —
    its docstring said outright "Does not touch the FAISS index" — leaving
    a mapped code_vectors.mmap live until GC got around to it. A stack-
    referenced CodeIndexManager (searcher #1, built write-only via
    get_searcher(..., load_existing=False)) could then block a second
    instance's clear_index() from unlinking the shared mmap file
    (PermissionError / WinError 32 on Windows). __exit__ had the same gap:
    it inlined its own metadata-close instead of calling close(), so it
    silently skipped the new mmap release too. See
    tests/unit/search/test_faiss_vector_index.py's
    test_close_releases_mmap_handle_so_second_instance_can_clear for the
    FaissVectorIndex-level version of this test.
    """

    @staticmethod
    def _plant_index_with_mmap(storage_dir: Path) -> None:
        """Plant a real on-disk index + mmap file directly (bypassing
        MMAP_THRESHOLD, which only gates FaissVectorIndex.save() — load()
        maps whatever mmap file already exists, threshold or not)."""
        rng = np.random.RandomState(42)
        embeddings = rng.randn(3, 8).astype(np.float32)
        chunk_ids = [f"chunk_{i}" for i in range(3)]

        seed = FaissVectorIndex(storage_dir / "code.index")
        seed.create(8)
        seed.add(embeddings, chunk_ids)
        # pyrefly: ignore [missing-attribute]
        faiss.write_index(seed.index, str(seed.index_path))
        with open(seed.chunk_id_path, "wb") as f:
            pickle.dump(chunk_ids, f)
        MmapVectorStorage(seed._mmap_path, dimension=8).save(embeddings, chunk_ids)

    def test_close_releases_faiss_mmap_handle(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        self._plant_index_with_mmap(storage_dir)

        manager = CodeIndexManager(storage_dir=str(storage_dir))
        assert manager._faiss_index._mmap_storage is not None

        manager.close()

        assert manager._faiss_index._mmap_storage is None

    def test_exit_delegates_to_close_and_releases_faiss_mmap_handle(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        self._plant_index_with_mmap(storage_dir)

        with CodeIndexManager(storage_dir=str(storage_dir)) as manager:
            assert manager._faiss_index._mmap_storage is not None

        assert manager._faiss_index._mmap_storage is None

    def test_close_lets_a_second_manager_clear_the_shared_mmap_file(self, tmp_path):
        """End-to-end version at the CodeIndexManager seam: mirrors the
        production sequence (searcher #1 loads, gets closed by
        _cleanup_previous_resources, searcher #2 loads and clears) rather
        than poking _mmap_storage directly."""
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        self._plant_index_with_mmap(storage_dir)

        manager1 = CodeIndexManager(storage_dir=str(storage_dir))
        manager2 = CodeIndexManager(storage_dir=str(storage_dir))
        assert manager1._faiss_index._mmap_storage is not None
        assert manager2._faiss_index._mmap_storage is not None

        manager1.close()
        manager2.clear_index()

        assert manager2._faiss_index._mmap_storage is None
        assert not manager2._faiss_index._mmap_path.exists()

    def test_second_manager_can_save_and_clear_while_first_still_mapped(self, tmp_path):
        """The save-after-load shape: before this fix, nothing exercised a
        second manager's save_index() (FaissVectorIndex.save()'s
        below-MMAP_THRESHOLD delete-mmap branch, faiss_index.py's
        unprotected ``self._mmap_path.unlink()``) against a *foreign* live
        mapping -- every existing regression test here went straight to
        clear_index() without a save() in between. That's the exact gap
        that let the 2026-08-28 fix (releasing only this instance's own
        handle) look complete while the bug kept recurring through
        whichever door still had two live instances and no closed handle.

        Unlike ``test_close_lets_a_second_manager_clear_the_shared_mmap_file``,
        manager1 is never closed at all here -- its live mapping must not
        block manager2's save() or its later clear_index().
        """
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        self._plant_index_with_mmap(storage_dir)

        manager1 = CodeIndexManager(storage_dir=str(storage_dir))
        manager2 = CodeIndexManager(storage_dir=str(storage_dir))
        assert manager1._faiss_index._mmap_storage is not None
        assert manager2._faiss_index._mmap_storage is not None

        # manager1 is deliberately never closed -- both of manager2's calls
        # below must succeed despite manager1's foreign live mapping.
        manager2.save_index()
        assert not manager2._faiss_index._mmap_path.exists(), (
            "save() below MMAP_THRESHOLD deletes the stale mmap file -- "
            "that unlink must not be blocked by manager1's mapping"
        )

        manager2.clear_index()
        assert manager2._faiss_index._mmap_storage is None
