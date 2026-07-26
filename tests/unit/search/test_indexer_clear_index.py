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
