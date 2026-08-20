"""Unit tests for ``search/base_searcher.py``'s concrete logic (Phase 13.3).

``BaseSearcher.search()`` itself (config resolution -> ``RetrievalRequest.build``
-> ``execute()``) already has indirect coverage through ``HybridSearcher``'s own
test suite. The gap this file targets is the base class's *other* concrete
logic that every subclass inherits unchanged: dimension validation, cache
eviction, and cache-stat reporting -- none of which had a dedicated test
before this file existed.

A minimal concrete ``_FakeSearcher`` stands in for ``HybridSearcher`` /
``IntelligentSearcher`` -- a fake, not a mock, per this project's house style
(see ``tests/TESTING_GUIDE.md``). Its ``execute()`` calls
``_validate_dimensions``/``_evict_cache_if_needed`` the same way a real
subclass would from its own ``execute()``, so driving it through the public
``search()`` seam exercises both private helpers without reaching into them
directly -- avoiding the private-API test touches the Phase 13 audit flagged.
"""

from typing import Any

import pytest

from search.base_searcher import BaseSearcher
from search.config import SearchConfig
from search.types import RetrievalRequest


class _FakeSearcher(BaseSearcher):
    """Minimal concrete ``BaseSearcher`` -- stands in for a real subclass."""

    _DEFAULT_SEARCH_MODE = "hybrid"

    def __init__(self, index: Any = None, embedder: Any = None) -> None:
        super().__init__()
        self._index = index
        self._embedder = embedder

    def execute(self, request: RetrievalRequest) -> list:
        self._validate_dimensions(self._index, self._embedder)
        self._evict_cache_if_needed()
        return []

    @property
    def is_ready(self) -> bool:
        return True

    @property
    def graph_storage(self):
        return None


class _FakeIndex:
    def __init__(self, d: int) -> None:
        self.d = d


class _FakeEmbedder:
    def __init__(self, embedding_dimension: int | None) -> None:
        self.model_name = "fake-model"
        self._embedding_dimension = embedding_dimension

    def get_model_info(self) -> dict[str, Any]:
        return {"embedding_dimension": self._embedding_dimension}


class _NoD:
    """An index-like object with no ``d`` attribute -- triggers AttributeError."""


def _run(fake: _FakeSearcher) -> None:
    fake.search("query", k=1, config=SearchConfig())


class TestValidateDimensions:
    def test_matching_dimensions_no_error(self):
        fake = _FakeSearcher(index=_FakeIndex(768), embedder=_FakeEmbedder(768))
        _run(fake)  # must not raise

    def test_mismatched_dimensions_raises(self):
        fake = _FakeSearcher(index=_FakeIndex(768), embedder=_FakeEmbedder(384))
        with pytest.raises(ValueError, match="Dimension mismatch"):
            _run(fake)

    def test_none_index_skips_validation(self):
        fake = _FakeSearcher(index=None, embedder=_FakeEmbedder(768))
        _run(fake)  # no raise, no lookup attempted

    def test_none_embedder_skips_validation(self):
        fake = _FakeSearcher(index=_FakeIndex(768), embedder=None)
        _run(fake)

    def test_missing_embedding_dimension_is_swallowed(self):
        fake = _FakeSearcher(
            index=_FakeIndex(768), embedder=_FakeEmbedder(embedding_dimension=None)
        )
        _run(fake)  # falsy embedder_dim short-circuits the mismatch check

    def test_attribute_error_on_index_d_is_swallowed(self):
        fake = _FakeSearcher(index=_NoD(), embedder=_FakeEmbedder(768))
        _run(fake)  # AttributeError from index.d is caught and logged, not raised


class TestEvictCacheIfNeeded:
    def test_below_max_size_no_eviction(self):
        fake = _FakeSearcher()
        fake._metadata_cache = {f"k{i}": None for i in range(fake._cache_max_size)}
        _run(fake)
        assert len(fake._metadata_cache) == fake._cache_max_size

    def test_over_max_size_evicts_oldest_one_fifth(self):
        fake = _FakeSearcher()
        fake._cache_max_size = 10
        fake._metadata_cache = {f"k{i}": None for i in range(11)}
        _run(fake)
        # 10 // 5 = 2 evicted
        assert len(fake._metadata_cache) == 9
        # dict preserves insertion order -- the oldest keys are evicted first
        assert "k0" not in fake._metadata_cache
        assert "k1" not in fake._metadata_cache
        assert "k2" in fake._metadata_cache


class TestGetCacheStats:
    def test_zero_requests_zero_hit_rate(self):
        fake = _FakeSearcher()
        assert fake.get_cache_stats() == {
            "cache_hits": 0,
            "cache_misses": 0,
            "hit_rate_pct": 0.0,
            "cache_size": 0,
            "cache_max_size": 1000,
        }

    def test_hit_rate_percentage_rounded(self):
        fake = _FakeSearcher()
        fake._cache_hits = 2
        fake._cache_misses = 1
        fake._metadata_cache = {"a": None}
        stats = fake.get_cache_stats()
        assert stats["cache_hits"] == 2
        assert stats["cache_misses"] == 1
        assert stats["hit_rate_pct"] == pytest.approx(66.67)
        assert stats["cache_size"] == 1
