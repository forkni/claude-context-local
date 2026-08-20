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

``TestValidateDimensions`` (Phase 14.1 rewrite) instruments ``_FakeIndex``/
``_FakeEmbedder`` to record whether ``index.d``/``embedder.get_model_info()``
were actually reached, so each "skips validation" test asserts the skip
instead of relying on "must not raise" -- a body that validated and happened
to pass was previously indistinguishable from one that never ran.
"""

import logging
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
    """Records whether ``.d`` was actually read, not just its value."""

    def __init__(self, d: int) -> None:
        self._d = d
        self.d_accessed = False

    @property
    def d(self) -> int:
        self.d_accessed = True
        return self._d


class _FakeEmbedder:
    """Records whether ``get_model_info()`` was actually called."""

    def __init__(self, embedding_dimension: int | None) -> None:
        self.model_name = "fake-model"
        self._embedding_dimension = embedding_dimension
        self.get_model_info_called = False

    def get_model_info(self) -> dict[str, Any]:
        self.get_model_info_called = True
        return {"embedding_dimension": self._embedding_dimension}


class _NoD:
    """An index-like object with no ``d`` attribute -- triggers AttributeError."""


def _run(fake: _FakeSearcher) -> None:
    fake.search("query", k=1, config=SearchConfig())


class TestValidateDimensions:
    def test_matching_dimensions_no_error(self):
        index = _FakeIndex(768)
        embedder = _FakeEmbedder(768)
        fake = _FakeSearcher(index=index, embedder=embedder)
        _run(fake)  # must not raise
        assert index.d_accessed, "matching dimensions must still read index.d"
        assert embedder.get_model_info_called, (
            "matching dimensions must still consult the embedder"
        )

    def test_mismatched_dimensions_raises(self):
        fake = _FakeSearcher(index=_FakeIndex(768), embedder=_FakeEmbedder(384))
        with pytest.raises(ValueError, match="Dimension mismatch"):
            _run(fake)

    def test_none_index_skips_validation(self):
        embedder = _FakeEmbedder(768)
        fake = _FakeSearcher(index=None, embedder=embedder)
        _run(fake)  # no raise
        assert not embedder.get_model_info_called, (
            "a None index must short-circuit before the embedder is consulted"
        )

    def test_none_embedder_skips_validation(self):
        index = _FakeIndex(768)
        fake = _FakeSearcher(index=index, embedder=None)
        _run(fake)  # no raise
        assert not index.d_accessed, (
            "a None embedder must short-circuit before index.d is read"
        )

    def test_missing_embedding_dimension_is_swallowed(self):
        index = _FakeIndex(768)
        embedder = _FakeEmbedder(embedding_dimension=None)
        fake = _FakeSearcher(index=index, embedder=embedder)
        _run(fake)  # falsy embedder_dim short-circuits the mismatch check
        assert index.d_accessed
        assert embedder.get_model_info_called, (
            "both sides must be read before the falsy embedder_dim short-circuits"
        )

    def test_attribute_error_on_index_d_is_swallowed(self, caplog):
        fake = _FakeSearcher(index=_NoD(), embedder=_FakeEmbedder(768))
        with caplog.at_level(logging.DEBUG, logger="search.base_searcher"):
            _run(fake)  # AttributeError from index.d is caught, not raised
        assert "Could not validate dimensions" in caplog.text, (
            "the except branch must log the swallowed AttributeError, not just eat it"
        )


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
