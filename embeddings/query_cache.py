"""Query embedding cache with LRU eviction.

This module provides a simple LRU (Least Recently Used) cache for query embeddings,
improving performance for repeated queries.
"""

import hashlib
import logging
from typing import Any, Dict, Optional

import numpy as np


class QueryEmbeddingCache:
    """LRU cache for query embeddings.

    Caches query embeddings based on a deterministic key generated from
    the query text, model name, and model-specific configuration (prefixes,
    instructions, etc.).

    The cache implements a simple LRU eviction policy: when the cache is full,
    the least recently used entry is removed to make space for new entries.

    Example:
        >>> cache = QueryEmbeddingCache(max_size=128)
        >>> embedding = np.array([0.1, 0.2, 0.3])
        >>> cache.put("example query", "BAAI/bge-m3", embedding)
        >>> result = cache.get("example query", "BAAI/bge-m3")
        >>> stats = cache.get_stats()
        >>> print(stats["hit_rate"])
    """

    def __init__(self, max_size: int = 128):
        """Initialize the query embedding cache.

        Args:
            max_size: Maximum number of entries to cache. Defaults to 128.
        """
        self._max_size = max_size
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_order: list = []  # Track insertion order for LRU
        self._hits = 0
        self._misses = 0
        self._logger = logging.getLogger(__name__)

    def _generate_cache_key(
        self,
        query: str,
        model_name: str,
        task_instruction: str = "",
        query_prefix: str = "",
    ) -> str:
        """Generate deterministic cache key from query and model config.

        Args:
            query: The query text
            model_name: Name of the embedding model
            task_instruction: Optional task instruction (e.g., for CodeRankEmbed)
            query_prefix: Optional query prefix (e.g., for retrieval models)

        Returns:
            MD5 hash of the combined key data
        """
        key_data = f"{query}|{model_name}|{task_instruction}|{query_prefix}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(
        self,
        query: str,
        model_name: str,
        task_instruction: str = "",
        query_prefix: str = "",
    ) -> Optional[np.ndarray]:
        """Retrieve cached embedding for a query.

        Args:
            query: The query text
            model_name: Name of the embedding model
            task_instruction: Optional task instruction
            query_prefix: Optional query prefix

        Returns:
            Cached embedding if found, None otherwise. Returns a copy to
            prevent external modification of cached data.
        """
        cache_key = self._generate_cache_key(
            query, model_name, task_instruction, query_prefix
        )

        if cache_key in self._cache:
            self._hits += 1
            self._logger.debug(f"Cache hit for query: {query[:50]}...")
            # Return a copy to prevent external modification
            return self._cache[cache_key].copy()

        self._misses += 1
        self._logger.debug(f"Cache miss for query: {query[:50]}...")
        return None

    def put(
        self,
        query: str,
        model_name: str,
        embedding: np.ndarray,
        task_instruction: str = "",
        query_prefix: str = "",
    ):
        """Add or update an embedding in the cache.

        Implements LRU eviction: if the cache is full, removes the least
        recently used entry before adding the new one.

        Args:
            query: The query text
            model_name: Name of the embedding model
            embedding: The embedding vector to cache
            task_instruction: Optional task instruction
            query_prefix: Optional query prefix
        """
        cache_key = self._generate_cache_key(
            query, model_name, task_instruction, query_prefix
        )

        # Remove key if it already exists (to update order)
        if cache_key in self._cache:
            self._cache_order.remove(cache_key)

        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_size:
            oldest_key = self._cache_order.pop(0)
            del self._cache[oldest_key]

        # Add to cache (store a copy to prevent external modification)
        self._cache[cache_key] = embedding.copy()
        self._cache_order.append(cache_key)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache hit/miss statistics.

        Returns:
            Dictionary containing:
                - hits: Number of cache hits
                - misses: Number of cache misses
                - hit_rate: Cache hit rate as percentage string
                - cache_size: Current number of cached entries
                - max_size: Maximum cache capacity
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self._cache),
            "max_size": self._max_size,
        }

    def clear(self):
        """Clear the cache and reset statistics.

        Removes all cached embeddings and resets hit/miss counters.
        """
        self._cache.clear()
        self._cache_order.clear()
        self._hits = 0
        self._misses = 0
        self._logger.info("Query embedding cache cleared")

    @property
    def size(self) -> int:
        """Current number of cached entries."""
        return len(self._cache)

    @property
    def max_size(self) -> int:
        """Maximum cache capacity."""
        return self._max_size
