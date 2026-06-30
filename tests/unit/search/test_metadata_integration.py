"""Unit tests for MetadataStore integration with SymbolHashCache."""

import tempfile
import unittest
from pathlib import Path

from search.metadata import MetadataStore


class TestMetadataStoreHashCacheIntegration(unittest.TestCase):
    """Test SymbolHashCache integration with MetadataStore."""

    def setUp(self):
        """Create temporary metadata store for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "metadata.db"
        self.store = MetadataStore(self.db_path)

    def tearDown(self):
        """Clean up test resources."""
        self.store.close()

    def test_set_adds_to_hash_cache(self):
        """Test that set() adds chunk_id to hash cache."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        metadata = {"relative_path": "search/indexer.py", "chunk_type": "function"}

        self.store.set(chunk_id, 0, metadata)

        # Verify chunk is in hash cache
        self.assertTrue(chunk_id in self.store._symbol_cache)

    def test_get_uses_hash_cache(self):
        """Test that get() uses hash cache for O(1) lookup."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        metadata = {"relative_path": "search/indexer.py", "chunk_type": "function"}

        # Add chunk
        self.store.set(chunk_id, 0, metadata)

        # Get should use hash cache
        result = self.store.get(chunk_id)

        self.assertIsNotNone(result)
        self.assertEqual(result["index_id"], 0)
        self.assertEqual(result["metadata"], metadata)

    def test_get_cache_miss_then_direct_db_lookup(self):
        """Test that get() falls back to direct DB lookup if not in cache (P1b).

        Post-P1b, set() stores the canonical (forward-slash) key, so the
        cache miss always resolves to that canonical key — not a backslash
        variant.  The backslash input is canonicalized before lookup.
        """
        # Add chunk with backslash separator — set() canonicalizes to forward-slash
        chunk_id_backslash = "search\\indexer.py:10-20:function:test_func"
        chunk_id_canonical = "search/indexer.py:10-20:function:test_func"
        metadata = {"relative_path": "search/indexer.py", "chunk_type": "function"}
        self.store.set(chunk_id_backslash, 0, metadata)

        # Clear hash cache to test direct-DB fallback path
        self.store._symbol_cache.clear()

        # get() with either separator variant finds the canonical key via direct DB
        result = self.store.get("search/indexer.py:10-20:function:test_func")
        self.assertIsNotNone(result)
        self.assertEqual(result["index_id"], 0)

        # After the miss-then-find, the CANONICAL key is re-cached (not backslash)
        self.assertTrue(chunk_id_canonical in self.store._symbol_cache)

        # Backslash lookup also resolves via canonicalization
        self.store._symbol_cache.clear()
        result2 = self.store.get(chunk_id_backslash)
        self.assertIsNotNone(result2)
        self.assertEqual(result2["index_id"], 0)

    def test_delete_removes_from_hash_cache(self):
        """Test that delete() removes chunk_id from hash cache."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        metadata = {"relative_path": "search/indexer.py", "chunk_type": "function"}

        # Add chunk
        self.store.set(chunk_id, 0, metadata)
        self.assertTrue(chunk_id in self.store._symbol_cache)

        # Delete chunk
        self.store.delete(chunk_id)

        # Verify removed from hash cache
        self.assertFalse(chunk_id in self.store._symbol_cache)

    def test_commit_saves_hash_cache(self):
        """Test that commit() persists hash cache to disk."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        metadata = {"relative_path": "search/indexer.py", "chunk_type": "function"}

        # Add chunk and commit
        self.store.set(chunk_id, 0, metadata)
        self.store.commit()

        # Verify cache file exists
        cache_path = self.db_path.parent / f"{self.db_path.stem}_symbol_cache.json"
        self.assertTrue(cache_path.exists())

        # Reload and verify persisted
        self.store.close()
        store2 = MetadataStore(self.db_path)
        self.assertTrue(chunk_id in store2._symbol_cache)
        store2.close()

    def test_multiple_chunks_hash_cache(self):
        """Test hash cache with multiple chunks."""
        chunks = [
            ("search/indexer.py:10-20:function:func1", 0),
            ("search/metadata.py:30-40:class:MetadataStore", 1),
            ("chunking/base.py:50-60:method:ChunkBase.process", 2),
        ]

        # Add all chunks
        for chunk_id, idx in chunks:
            metadata = {"relative_path": chunk_id.split(":")[0]}
            self.store.set(chunk_id, idx, metadata)

        # Verify all in hash cache
        for chunk_id, _ in chunks:
            self.assertTrue(chunk_id in self.store._symbol_cache)

        # Verify all retrievable
        for chunk_id, expected_idx in chunks:
            result = self.store.get(chunk_id)
            self.assertIsNotNone(result)
            self.assertEqual(result["index_id"], expected_idx)


if __name__ == "__main__":
    unittest.main()
