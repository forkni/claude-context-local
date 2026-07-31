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

from search.indexer import CodeIndexManager


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
