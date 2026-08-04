"""Regression tests for CodeIndexManager.close() (ADR-0025).

close() used to null ``_metadata_store`` and re-wire ``_batch_ops`` around
it, while the ``metadata_store`` property is annotated ``-> MetadataStore``
and just returns the field -- so any metadata access after close() raised
``'NoneType' object has no attribute ...``. Under the stable-identity
invariant, close() only releases the SQLite handle; the object stays live
and lazily reopens on the next access, so no re-wiring is needed anywhere.
"""

from search.indexer import CodeIndexManager, probe_metadata_deletable


class TestCodeIndexManagerClose:
    def test_close_is_idempotent(self, tmp_path):
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        manager = CodeIndexManager(storage_dir=str(storage_dir))

        manager.close()
        manager.close()  # must not raise

    def test_close_releases_metadata_lock_for_probe(self, tmp_path):
        """The manual check named in ADR-0025's plan: after close(),
        metadata.db must be deletable -- the real Windows file-lock guard.
        """
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        manager = CodeIndexManager(storage_dir=str(storage_dir))
        manager.metadata_store.set(
            "file.py:1-10:function:foo", 0, {"relative_path": "file.py"}
        )
        manager.metadata_store.commit()

        manager.close()

        # Raises if the file is still locked/undeletable.
        probe_metadata_deletable(manager.metadata_path)

    def test_close_then_metadata_access_lazily_reopens(self, tmp_path):
        """Identity stays stable per ADR-0025 -- the store is not replaced,
        so it reopens itself on the next access instead of raising.
        """
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        manager = CodeIndexManager(storage_dir=str(storage_dir))
        chunk_id = "file.py:1-10:function:foo"
        manager.metadata_store.set(chunk_id, 0, {"relative_path": "file.py"})
        manager.metadata_store.commit()

        manager.close()

        assert manager.metadata_store.exists(chunk_id)

    def test_close_preserves_batch_ops_metadata_store_reference(self, tmp_path):
        """_batch_ops caches metadata_store at construction time; close()
        must not null it out from under that reference (ADR-0025 -- the
        repair site this used to require deletes itself).
        """
        storage_dir = tmp_path / "index"
        storage_dir.mkdir()
        manager = CodeIndexManager(storage_dir=str(storage_dir))

        manager.close()

        assert manager._batch_ops._metadata_store is manager.metadata_store
