"""Abstract base class for code searchers.

Provides common cache management, dimension validation, and interface contract.
"""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

from .types import RetrievalRequest


if TYPE_CHECKING:
    from embeddings.embedder import CodeEmbedder
    from graph.graph_storage import CodeGraphStorage
    from search.config import SearchConfig, SearchMode

    from .reranker import SearchResult


class BaseSearcher(ABC):
    """Abstract base for code searchers (HybridSearcher, IntelligentSearcher).

    Provides common functionality:
    - Metadata cache management (2-5x speedup for multi-hop operations)
    - Dimension validation (safety check for model routing)
    - Cache statistics tracking
    - Interface contract for all searchers

    ``execute`` is the seam concrete searchers implement: one signature, a
    fully-resolved ``RetrievalRequest`` in, ``SearchResult``s out. ``search``
    is the concrete convenience wrapper every existing call site (benchmark
    harnesses, probes, MCP orchestration) already uses — it resolves a
    request from ``config``/``**overrides`` via ``RetrievalRequest.build``
    and calls ``execute`` (ADR-0048).
    """

    #: Search mode assumed when a caller doesn't pass one explicitly.
    #: Set by each concrete subclass (HYBRID / SEMANTIC).
    _DEFAULT_SEARCH_MODE: "SearchMode"

    def __init__(self):
        """Initialize common searcher components.

        Subclasses should call super().__init__() and then initialize
        their specific components.
        """
        # In-memory metadata cache for multi-hop operations (find_connections)
        # Avoids repeated SQLite lookups during graph traversal
        self._metadata_cache: dict[str, SearchResult | None] = {}
        self._cache_max_size = 1000  # Limit cache size to prevent memory bloat
        self._cache_hits = 0
        self._cache_misses = 0
        self._logger = logging.getLogger(__name__)

    @abstractmethod
    def execute(self, request: RetrievalRequest) -> list["SearchResult"]:
        """Execute a fully-resolved retrieval request.

        Args:
            request: The resolved request (see RetrievalRequest.build).

        Returns:
            List of SearchResult objects ranked by relevance.
        """
        pass

    def search(
        self,
        query: str,
        k: int = 4,
        *,
        config: Optional["SearchConfig"] = None,
        **overrides: Any,
    ) -> list["SearchResult"]:
        """Resolve a RetrievalRequest from config + overrides, then execute it.

        Args:
            query: Natural language or code query.
            k: Number of results to return.
            config: Optional SearchConfig override; defaults to the process
                singleton (``get_search_config()``) when omitted.
            **overrides: Any RetrievalRequest.build keyword (search_mode,
                bm25_weight, dense_weight, min_bm25_score, use_parallel,
                filters, context_depth). Unset overrides resolve from
                ``config`` or this subclass's ``_DEFAULT_SEARCH_MODE``.

        Returns:
            List of SearchResult objects ranked by relevance.
        """
        from search.config import get_search_config

        effective_config = config if config is not None else get_search_config()
        overrides.setdefault("search_mode", self._DEFAULT_SEARCH_MODE)
        request = RetrievalRequest.build(query, k, effective_config, **overrides)
        return self.execute(request)

    @property
    @abstractmethod
    def is_ready(self) -> bool:
        """Check if searcher is ready for queries.

        Returns:
            bool: True if indices loaded and searcher is operational
        """
        pass

    @property
    @abstractmethod
    def graph_storage(self) -> Optional["CodeGraphStorage"]:
        """Access graph storage for relationship queries.

        Returns:
            CodeGraphStorage instance or None if not available
        """
        pass

    def _validate_dimensions(
        self, index: Any, embedder: Optional["CodeEmbedder"]
    ) -> None:
        """Validate that index and embedder dimensions match.

        Args:
            index: Index object with 'd' attribute (FAISS index)
            embedder: Embedder with get_model_info() method

        Raises:
            ValueError: If dimension mismatch is detected
        """
        if index is not None and embedder is not None:
            try:
                index_dim = index.d
                model_info = embedder.get_model_info()
                embedder_dim = model_info.get("embedding_dimension")

                if embedder_dim and index_dim != embedder_dim:
                    raise ValueError(
                        f"FATAL: Dimension mismatch between index ({index_dim}d) "
                        f"and embedder ({embedder_dim}d for {embedder.model_name}). "
                        f"This indicates a bug in model routing. "
                        f"The index was likely loaded for a different model."
                    )
            except (AttributeError, KeyError) as e:
                self._logger.debug(f"Could not validate dimensions: {e}")

    def _evict_cache_if_needed(self) -> None:
        """Evict oldest cache entries if cache exceeds max size.

        Uses simple FIFO eviction strategy. More sophisticated LRU could
        be implemented if needed, but FIFO is sufficient for most use cases.
        """
        if len(self._metadata_cache) > self._cache_max_size:
            # Evict oldest 20% of entries
            num_to_evict = self._cache_max_size // 5
            keys_to_remove = list(self._metadata_cache.keys())[:num_to_evict]
            for key in keys_to_remove:
                del self._metadata_cache[key]
            self._logger.debug(
                f"Evicted {num_to_evict} entries from metadata cache "
                f"(size: {len(self._metadata_cache)}/{self._cache_max_size})"
            )

    def get_cache_stats(self) -> dict[str, int | float]:
        """Get metadata cache statistics.

        Returns:
            Dict with cache_hits, cache_misses, hit_rate_pct, cache_size, cache_max_size
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (
            (self._cache_hits / total_requests * 100) if total_requests > 0 else 0.0
        )

        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_pct": round(hit_rate, 2),
            "cache_size": len(self._metadata_cache),
            "cache_max_size": self._cache_max_size,
        }
