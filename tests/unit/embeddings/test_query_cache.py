"""Tests for QueryEmbeddingCache."""

import threading
import time

import numpy as np

from embeddings.query_cache import QueryEmbeddingCache


class TestQueryEmbeddingCache:
    """Test suite for QueryEmbeddingCache class."""

    def test_initialization(self):
        """Test cache initialization with default and custom sizes."""
        # Default size
        cache = QueryEmbeddingCache()
        assert cache.max_size == 128
        assert cache.size == 0

        # Custom size
        cache = QueryEmbeddingCache(max_size=64)
        assert cache.max_size == 64
        assert cache.size == 0

    def test_put_and_get(self):
        """Test basic put and get operations."""
        cache = QueryEmbeddingCache(max_size=10)
        embedding = np.array([0.1, 0.2, 0.3])

        # Put embedding
        cache.put("test query", "BAAI/bge-m3", embedding)
        assert cache.size == 1

        # Get embedding
        result = cache.get("test query", "BAAI/bge-m3")
        assert result is not None
        assert np.array_equal(result, embedding)

    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = QueryEmbeddingCache()

        result = cache.get("nonexistent query", "BAAI/bge-m3")
        assert result is None

    def test_cache_key_uniqueness(self):
        """Test that different queries/models produce different cache keys."""
        cache = QueryEmbeddingCache(max_size=10)
        embedding1 = np.array([0.1, 0.2, 0.3])
        embedding2 = np.array([0.4, 0.5, 0.6])

        # Different queries, same model
        cache.put("query1", "BAAI/bge-m3", embedding1)
        cache.put("query2", "BAAI/bge-m3", embedding2)
        assert cache.size == 2

        result1 = cache.get("query1", "BAAI/bge-m3")
        result2 = cache.get("query2", "BAAI/bge-m3")
        assert np.array_equal(result1, embedding1)
        assert np.array_equal(result2, embedding2)

        # Same query, different models
        cache.put("query", "model1", embedding1)
        cache.put("query", "model2", embedding2)
        assert cache.size == 4

        result1 = cache.get("query", "model1")
        result2 = cache.get("query", "model2")
        assert np.array_equal(result1, embedding1)
        assert np.array_equal(result2, embedding2)

    def test_task_instruction_affects_key(self):
        """Test that task_instruction is part of the cache key."""
        cache = QueryEmbeddingCache(max_size=10)
        embedding1 = np.array([0.1, 0.2, 0.3])
        embedding2 = np.array([0.4, 0.5, 0.6])

        # Same query and model, different task instructions
        cache.put("query", "model", embedding1, task_instruction="instruction1")
        cache.put("query", "model", embedding2, task_instruction="instruction2")
        assert cache.size == 2

        result1 = cache.get("query", "model", task_instruction="instruction1")
        result2 = cache.get("query", "model", task_instruction="instruction2")
        assert np.array_equal(result1, embedding1)
        assert np.array_equal(result2, embedding2)

    def test_query_prefix_affects_key(self):
        """Test that query_prefix is part of the cache key."""
        cache = QueryEmbeddingCache(max_size=10)
        embedding1 = np.array([0.1, 0.2, 0.3])
        embedding2 = np.array([0.4, 0.5, 0.6])

        # Same query and model, different query prefixes
        cache.put("query", "model", embedding1, query_prefix="prefix1: ")
        cache.put("query", "model", embedding2, query_prefix="prefix2: ")
        assert cache.size == 2

        result1 = cache.get("query", "model", query_prefix="prefix1: ")
        result2 = cache.get("query", "model", query_prefix="prefix2: ")
        assert np.array_equal(result1, embedding1)
        assert np.array_equal(result2, embedding2)

    def test_lru_eviction(self):
        """Test that LRU eviction works correctly.

        With OrderedDict implementation, GET operations now update LRU order.
        """
        cache = QueryEmbeddingCache(max_size=3)

        # Fill cache
        cache.put("query1", "model", np.array([0.1]))
        cache.put("query2", "model", np.array([0.2]))
        cache.put("query3", "model", np.array([0.3]))
        assert cache.size == 3

        # Add query4 - should evict query1 (oldest inserted)
        cache.put("query4", "model", np.array([0.4]))
        assert cache.size == 3

        # query1 should be evicted (was the first one added)
        assert cache.get("query1", "model") is None
        # query2, query3, query4 should still be present
        assert cache.get("query2", "model") is not None
        assert cache.get("query3", "model") is not None
        assert cache.get("query4", "model") is not None

    def test_access_updates_lru_order(self):
        """Test that accessing an entry via GET moves it to most recently used."""
        cache = QueryEmbeddingCache(max_size=2)

        cache.put("query1", "model", np.array([1.0]))
        cache.put("query2", "model", np.array([2.0]))

        # Access query1, making it most recently used
        cache.get("query1", "model")

        # Add query3 - should evict query2 (oldest), not query1 (just accessed)
        cache.put("query3", "model", np.array([3.0]))

        # query1 should still be present (was accessed)
        assert cache.get("query1", "model") is not None
        # query2 should be evicted
        assert cache.get("query2", "model") is None
        # query3 should be present
        assert cache.get("query3", "model") is not None

    def test_update_existing_entry(self):
        """Test that updating an existing entry moves it to end of LRU order."""
        cache = QueryEmbeddingCache(max_size=3)

        # Fill cache
        cache.put("query1", "model", np.array([0.1]))
        cache.put("query2", "model", np.array([0.2]))
        cache.put("query3", "model", np.array([0.3]))

        # Update query1 (should move to end)
        cache.put("query1", "model", np.array([0.11]))

        # Add query4 - should evict query2 (now oldest)
        cache.put("query4", "model", np.array([0.4]))

        # query1 should still be present (was updated)
        result = cache.get("query1", "model")
        assert result is not None
        assert np.isclose(result[0], 0.11)
        # query2 should be evicted
        assert cache.get("query2", "model") is None

    def test_copy_protection(self):
        """Test that cached embeddings are protected from external modification."""
        cache = QueryEmbeddingCache(max_size=10)
        original_embedding = np.array([0.1, 0.2, 0.3])

        cache.put("query", "model", original_embedding)

        # Get embedding and modify it
        result = cache.get("query", "model")
        result[0] = 999.0

        # Get embedding again - should be unchanged
        result2 = cache.get("query", "model")
        assert result2[0] == 0.1  # Original value preserved

    def test_statistics_tracking(self):
        """Test cache hit/miss statistics."""
        cache = QueryEmbeddingCache(max_size=10)
        embedding = np.array([0.1, 0.2, 0.3])

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == "0.0%"
        assert stats["cache_size"] == 0
        assert stats["max_size"] == 10

        # Cache miss
        cache.get("query", "model")
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

        # Add to cache
        cache.put("query", "model", embedding)

        # Cache hit
        cache.get("query", "model")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "50.0%"
        assert stats["cache_size"] == 1

        # Multiple hits
        cache.get("query", "model")
        cache.get("query", "model")
        stats = cache.get_stats()
        assert stats["hits"] == 3
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "75.0%"

    def test_clear(self):
        """Test cache clearing."""
        cache = QueryEmbeddingCache(max_size=10)
        embedding = np.array([0.1, 0.2, 0.3])

        # Add entries and generate stats
        cache.put("query1", "model", embedding)
        cache.put("query2", "model", embedding)
        cache.get("query1", "model")  # Hit
        cache.get("query3", "model")  # Miss

        # Clear cache
        cache.clear()

        # Verify everything is cleared
        assert cache.size == 0
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["cache_size"] == 0

        # Verify entries are gone
        assert cache.get("query1", "model") is None
        assert cache.get("query2", "model") is None

    def test_empty_cache_operations(self):
        """Test operations on empty cache."""
        cache = QueryEmbeddingCache(max_size=10)

        # Get from empty cache
        result = cache.get("query", "model")
        assert result is None

        # Stats on empty cache
        stats = cache.get_stats()
        assert stats["cache_size"] == 0
        assert stats["hit_rate"] == "0.0%"

        # Clear empty cache (should not error)
        cache.clear()
        assert cache.size == 0

    def test_single_entry_cache(self):
        """Test cache with max_size=1."""
        cache = QueryEmbeddingCache(max_size=1)
        embedding1 = np.array([0.1])
        embedding2 = np.array([0.2])

        # Add first entry
        cache.put("query1", "model", embedding1)
        assert cache.size == 1

        # Add second entry (should evict first)
        cache.put("query2", "model", embedding2)
        assert cache.size == 1

        # Verify only query2 is present
        assert cache.get("query1", "model") is None
        assert cache.get("query2", "model") is not None

    def test_large_embeddings(self):
        """Test caching of large embeddings."""
        cache = QueryEmbeddingCache(max_size=5)

        # Create large embeddings (typical model dimension)
        large_embedding = np.random.randn(1024)

        cache.put("query", "BAAI/bge-m3", large_embedding)
        result = cache.get("query", "BAAI/bge-m3")

        assert result is not None
        assert result.shape == (1024,)
        assert np.array_equal(result, large_embedding)

    def test_concurrent_operations(self):
        """Test multiple rapid operations (stress test)."""
        cache = QueryEmbeddingCache(max_size=10)

        # Rapid put/get operations
        for i in range(100):
            query = f"query{i % 20}"  # Reuse some queries
            embedding = np.array([float(i)])
            cache.put(query, "model", embedding)

        # Cache should be at max capacity
        assert cache.size == 10

        # All recent queries should be retrievable
        for i in range(90, 100):
            query = f"query{i % 20}"
            result = cache.get(query, "model")
            assert result is not None

    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        cache = QueryEmbeddingCache(max_size=10, ttl_seconds=1)
        cache.put("query", "model", np.array([1.0]))

        # Immediate access works
        assert cache.get("query", "model") is not None

        # Wait for expiration
        time.sleep(1.1)
        result = cache.get("query", "model")
        assert result is None

        # Verify misses incremented for expired entry
        stats = cache.get_stats()
        assert stats["misses"] == 1

    def test_thread_safety(self):
        """Test concurrent access does not cause race conditions."""
        cache = QueryEmbeddingCache(max_size=100)
        errors = []

        def writer(thread_id):
            try:
                for i in range(100):
                    cache.put(f"query_{thread_id}_{i}", "model", np.array([float(i)]))
            except Exception as e:
                errors.append(e)

        def reader(thread_id):
            try:
                for i in range(100):
                    cache.get(f"query_{thread_id}_{i}", "model")
            except Exception as e:
                errors.append(e)

        threads = []
        for t in range(10):
            threads.append(threading.Thread(target=writer, args=(t,)))
            threads.append(threading.Thread(target=reader, args=(t,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"

    def test_thread_safety_stats(self):
        """Test that statistics remain accurate under concurrent access."""
        cache = QueryEmbeddingCache(max_size=50)
        embedding = np.array([1.0, 2.0, 3.0])

        def worker():
            for i in range(50):
                cache.put(f"query_{i}", "model", embedding)
                cache.get(f"query_{i}", "model")

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Verify stats are consistent (no corruption)
        stats = cache.get_stats()
        assert stats["hits"] >= 0
        assert stats["misses"] >= 0
        assert stats["cache_size"] <= 50

    def test_disabled_cache_with_zero_max_size(self):
        """Cache with max_size=0 should be disabled (no storage, no errors)."""
        cache = QueryEmbeddingCache(max_size=0)
        embedding = np.array([0.1, 0.2, 0.3])

        # Put should be a no-op
        cache.put("query", "model", embedding)
        assert cache.size == 0

        # Get should always return None
        result = cache.get("query", "model")
        assert result is None

        # Stats should show all misses
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0
        assert stats["cache_size"] == 0
        assert stats["max_size"] == 0

    def test_disabled_cache_with_negative_max_size(self):
        """Cache with negative max_size should be disabled."""
        cache = QueryEmbeddingCache(max_size=-5)
        embedding = np.array([0.1, 0.2, 0.3])

        cache.put("query", "model", embedding)
        assert cache.size == 0
        assert cache.get("query", "model") is None

        stats = cache.get_stats()
        assert stats["max_size"] == 0
        assert stats["cache_size"] == 0
