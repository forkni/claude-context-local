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
from pathlib import Path

import faiss
import numpy as np
import pytest

from search.faiss_index import FaissVectorIndex
from search.indexer import CodeIndexManager, probe_metadata_deletable
from search.mmap_vectors import MmapVectorStorage


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
        metadata_db.write_bytes(b"fake sqlite db")

        def _raise_permission_error(*_args, **_kwargs):
            raise PermissionError("[WinError 32] file in use by another process")

        monkeypatch.setattr(os, "replace", _raise_permission_error)

        faiss_clear_called = False
        original_clear = manager._faiss_index.clear

        def _tracking_clear():
            nonlocal faiss_clear_called
            faiss_clear_called = True
            return original_clear()

        monkeypatch.setattr(manager._faiss_index, "clear", _tracking_clear)

        with pytest.raises(PermissionError):
            manager.clear_index()

        assert not faiss_clear_called, (
            "FAISS must not be cleared until metadata.db is proven deletable"
        )
        assert metadata_db.exists(), (
            "a failed probe must leave metadata.db exactly where it was — "
            "the clear is a no-op, not a half-clear"
        )
        assert stats.exists(), "stats.json must survive an aborted clear too"

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
        seed.create(8, "flat")
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
