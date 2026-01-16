"""Unit tests for SymbolHashCache with FNV-1a hashing."""

import json
import tempfile
import time
import unittest
from pathlib import Path

from search.symbol_cache import SymbolHashCache


class TestFNV1aHash(unittest.TestCase):
    """Test FNV-1a hash function implementation."""

    def test_fnv1a_deterministic(self):
        """Test that FNV-1a hash is deterministic."""
        text = "search/indexer.py:277-304:method:CodeIndexManager.get_chunk_by_id"

        hash1 = SymbolHashCache.fnv1a_hash(text)
        hash2 = SymbolHashCache.fnv1a_hash(text)

        self.assertEqual(hash1, hash2)

    def test_fnv1a_different_inputs(self):
        """Test that different inputs produce different hashes."""
        hash1 = SymbolHashCache.fnv1a_hash("chunk_id_1")
        hash2 = SymbolHashCache.fnv1a_hash("chunk_id_2")

        self.assertNotEqual(hash1, hash2)

    def test_fnv1a_unicode(self):
        """Test FNV-1a with unicode characters."""
        text = "search/файл.py:10-20:function:тест"
        hash_val = SymbolHashCache.fnv1a_hash(text)

        # Should not crash and produce valid 64-bit hash
        self.assertIsInstance(hash_val, int)
        self.assertGreater(hash_val, 0)
        self.assertLessEqual(hash_val, 0xFFFFFFFFFFFFFFFF)


class TestSymbolHashCacheBasics(unittest.TestCase):
    """Test basic SymbolHashCache operations."""

    def setUp(self):
        """Create temporary cache for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = Path(self.temp_dir) / "test_cache.json"
        self.cache = SymbolHashCache(self.cache_path)

    def test_initialization_empty(self):
        """Test cache initializes empty."""
        self.assertEqual(len(self.cache), 0)
        self.assertEqual(self.cache._total_symbols, 0)

    def test_add_single_chunk(self):
        """Test adding a single chunk_id."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        hash_val = self.cache.add(chunk_id)

        self.assertIsInstance(hash_val, int)
        self.assertEqual(len(self.cache), 1)
        self.assertTrue(self.cache._dirty)

    def test_get_by_hash(self):
        """Test retrieving chunk_id by hash."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        hash_val = self.cache.add(chunk_id)

        retrieved = self.cache.get(hash_val)
        self.assertEqual(retrieved, chunk_id)

    def test_get_by_chunk_id(self):
        """Test convenience method get_by_chunk_id."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        self.cache.add(chunk_id)

        retrieved = self.cache.get_by_chunk_id(chunk_id)
        self.assertEqual(retrieved, chunk_id)

    def test_contains(self):
        """Test contains/in operator."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        self.cache.add(chunk_id)

        self.assertTrue(self.cache.contains(chunk_id))
        self.assertTrue(chunk_id in self.cache)
        self.assertFalse("nonexistent" in self.cache)

    def test_remove(self):
        """Test removing chunk_id."""
        chunk_id = "search/indexer.py:10-20:function:test_func"
        self.cache.add(chunk_id)

        self.assertTrue(self.cache.remove(chunk_id))
        self.assertEqual(len(self.cache), 0)
        self.assertFalse(chunk_id in self.cache)

    def test_remove_nonexistent(self):
        """Test removing non-existent chunk_id."""
        result = self.cache.remove("nonexistent")
        self.assertFalse(result)

    def test_clear(self):
        """Test clearing all symbols."""
        for i in range(10):
            self.cache.add(f"chunk_{i}")

        self.assertEqual(len(self.cache), 10)

        self.cache.clear()
        self.assertEqual(len(self.cache), 0)

    def test_get_nonexistent(self):
        """Test getting non-existent hash."""
        result = self.cache.get(999999)
        self.assertIsNone(result)


class TestSymbolHashCachePersistence(unittest.TestCase):
    """Test save/load persistence."""

    def setUp(self):
        """Create temporary cache for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = Path(self.temp_dir) / "test_cache.json"

    def test_save_and_load(self):
        """Test saving and loading cache."""
        # Create and populate cache
        cache1 = SymbolHashCache(self.cache_path)
        chunks = [
            "search/indexer.py:10-20:function:func1",
            "search/metadata.py:30-40:class:MetadataStore",
            "chunking/base.py:50-60:method:ChunkBase.process",
        ]

        for chunk in chunks:
            cache1.add(chunk)

        cache1.save()

        # Load into new cache instance
        cache2 = SymbolHashCache(self.cache_path)

        # Verify all chunks loaded
        self.assertEqual(len(cache2), len(chunks))
        for chunk in chunks:
            self.assertTrue(chunk in cache2)

    def test_save_creates_directory(self):
        """Test that save creates parent directories."""
        deep_path = Path(self.temp_dir) / "deep" / "nested" / "cache.json"
        cache = SymbolHashCache(deep_path)

        cache.add("test_chunk")
        cache.save()

        self.assertTrue(deep_path.exists())

    def test_save_json_format(self):
        """Test saved JSON format."""
        cache = SymbolHashCache(self.cache_path)
        cache.add("test_chunk")
        cache.save()

        with open(self.cache_path, "r") as f:
            data = json.load(f)

        self.assertIn("version", data)
        self.assertEqual(data["version"], 2)  # Version 2 includes symbol_buckets
        self.assertIn("bucket_count", data)
        self.assertEqual(data["bucket_count"], 256)
        self.assertIn("total_symbols", data)
        self.assertEqual(data["total_symbols"], 1)
        self.assertIn("buckets", data)
        self.assertIn("symbol_buckets", data)  # New in version 2
        self.assertIn("total_symbol_mappings", data)  # New in version 2

    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        nonexistent_path = Path(self.temp_dir) / "nonexistent.json"
        cache = SymbolHashCache(nonexistent_path)

        # Should initialize empty (warning logged but no exception)
        self.assertEqual(len(cache), 0)

    def test_dirty_flag(self):
        """Test dirty flag behavior."""
        cache = SymbolHashCache(self.cache_path)

        # Not dirty initially
        self.assertFalse(cache._dirty)

        # Dirty after add
        cache.add("chunk1")
        self.assertTrue(cache._dirty)

        # Not dirty after save
        cache.save()
        self.assertFalse(cache._dirty)

        # Dirty after modification
        cache.remove("chunk1")
        self.assertTrue(cache._dirty)


class TestBucketDistribution(unittest.TestCase):
    """Test hash bucket distribution."""

    def test_bucket_count(self):
        """Test that BUCKET_COUNT is power of 2."""
        # 256 is 2^8
        self.assertEqual(SymbolHashCache.BUCKET_COUNT, 256)
        self.assertTrue(
            SymbolHashCache.BUCKET_COUNT & (SymbolHashCache.BUCKET_COUNT - 1) == 0,
            "BUCKET_COUNT must be power of 2",
        )

    def test_distribution_fairness(self):
        """Test that hashes distribute fairly across buckets."""
        temp_dir = tempfile.mkdtemp()
        cache_path = Path(temp_dir) / "test.json"
        cache = SymbolHashCache(cache_path)

        # Add 1000 diverse chunk_ids
        for i in range(1000):
            chunk_id = f"file_{i}.py:{i*10}-{i*10+10}:function:func_{i}"
            cache.add(chunk_id)

        stats = cache.get_stats()

        # With good distribution, we should use a decent percentage of buckets
        # Expected: ~1000/256 ≈ 3.9 per bucket
        self.assertGreater(stats["used_buckets"], 190, "Should use most buckets")
        self.assertLess(stats["max_bucket_size"], 20, "No bucket should be too crowded")
        self.assertGreater(
            stats["avg_bucket_size"], 2, "Average bucket should have ~4 items"
        )
        self.assertLess(stats["avg_bucket_size"], 6)


class TestPerformance(unittest.TestCase):
    """Test performance characteristics."""

    def setUp(self):
        """Create cache with test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = Path(self.temp_dir) / "perf_cache.json"
        self.cache = SymbolHashCache(self.cache_path)

        # Populate with realistic data
        self.chunk_ids = []
        for i in range(1000):
            chunk_id = f"search/module_{i % 10}.py:{i*10}-{i*10+10}:function:func_{i}"
            self.chunk_ids.append(chunk_id)
            self.cache.add(chunk_id)

    def test_lookup_performance(self):
        """Test that lookups are <0.1ms (target: <0.1ms)."""
        iterations = 1000

        # Test hash lookups
        start = time.perf_counter()
        for chunk_id in self.chunk_ids:
            hash_val = SymbolHashCache.fnv1a_hash(chunk_id)
            self.cache.get(hash_val)
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000

        self.assertLess(avg_time_ms, 0.1, f"Average lookup: {avg_time_ms:.4f}ms")
        print(f"\n✓ Symbol cache lookup performance: {avg_time_ms:.4f}ms average")

    def test_hash_performance(self):
        """Test that FNV-1a hash computation is fast."""
        iterations = 10000
        test_string = (
            "search/indexer.py:277-304:method:CodeIndexManager.get_chunk_by_id"
        )

        start = time.perf_counter()
        for _ in range(iterations):
            SymbolHashCache.fnv1a_hash(test_string)
        end = time.perf_counter()

        avg_time_us = ((end - start) / iterations) * 1_000_000

        # Should be <10 microseconds
        self.assertLess(avg_time_us, 10, f"Average hash time: {avg_time_us:.2f}μs")
        print(f"\n✓ FNV-1a hash performance: {avg_time_us:.2f}μs average")

    def test_add_performance(self):
        """Test that adding symbols is fast."""
        temp_cache = SymbolHashCache(Path(self.temp_dir) / "add_perf.json")
        iterations = 1000

        start = time.perf_counter()
        for i in range(iterations):
            temp_cache.add(f"chunk_{i}")
        end = time.perf_counter()

        avg_time_ms = ((end - start) / iterations) * 1000

        # Should be <0.1ms per add
        self.assertLess(avg_time_ms, 0.1, f"Average add time: {avg_time_ms:.4f}ms")


class TestCacheStatistics(unittest.TestCase):
    """Test cache statistics and reporting."""

    def test_get_stats_empty(self):
        """Test stats for empty cache."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "stats.json")

        stats = cache.get_stats()

        self.assertEqual(stats["total_symbols"], 0)
        self.assertEqual(stats["used_buckets"], 0)
        self.assertEqual(stats["avg_bucket_size"], 0.0)
        self.assertEqual(stats["max_bucket_size"], 0)
        self.assertEqual(stats["load_factor"], 0.0)

    def test_get_stats_populated(self):
        """Test stats for populated cache."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "stats.json")

        # Add 100 symbols
        for i in range(100):
            cache.add(f"chunk_{i}")

        stats = cache.get_stats()

        self.assertEqual(stats["total_symbols"], 100)
        self.assertGreater(stats["used_buckets"], 0)
        self.assertGreater(stats["avg_bucket_size"], 0)
        self.assertGreater(stats["max_bucket_size"], 0)
        self.assertGreater(stats["load_factor"], 0)
        self.assertLessEqual(stats["load_factor"], 100)

    def test_memory_estimate(self):
        """Test memory usage estimation."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "memory.json")

        # Add 1000 symbols
        for i in range(1000):
            cache.add(f"chunk_{i}")

        stats = cache.get_stats()

        # Should estimate reasonable memory usage
        # ~98 bytes per symbol + bucket overhead
        # 1000 symbols * 98 = ~98KB
        self.assertGreater(stats["memory_estimate_mb"], 0.05)  # At least 50KB
        self.assertLess(stats["memory_estimate_mb"], 1.0)  # Less than 1MB


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_string_chunk_id(self):
        """Test handling empty string."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "edge.json")

        hash_val = cache.add("")
        self.assertIsNotNone(hash_val)
        self.assertEqual(cache.get(hash_val), "")

    def test_very_long_chunk_id(self):
        """Test handling very long chunk_id."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "edge.json")

        long_id = "a" * 10000
        hash_val = cache.add(long_id)
        self.assertEqual(cache.get(hash_val), long_id)

    def test_special_characters(self):
        """Test chunk_ids with special characters."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "edge.json")

        special_ids = [
            "file:with:colons.py:10-20:function:test",
            "file\\with\\backslashes.py:10-20:function:test",
            "file/with/slashes.py:10-20:function:test",
            "file with spaces.py:10-20:function:test",
            "file_with_unicode_файл.py:10-20:function:тест",
        ]

        for chunk_id in special_ids:
            with self.subTest(chunk_id=chunk_id):
                cache.add(chunk_id)
                self.assertTrue(chunk_id in cache)

    def test_repr(self):
        """Test string representation."""
        temp_dir = tempfile.mkdtemp()
        cache = SymbolHashCache(Path(temp_dir) / "repr.json")

        cache.add("chunk1")
        cache.add("chunk2")

        repr_str = repr(cache)
        self.assertIn("SymbolHashCache", repr_str)
        self.assertIn("symbols=2", repr_str)


if __name__ == "__main__":
    unittest.main()
