"""Unit tests for SearchExecutor mode branches and fallback paths."""

import logging
from unittest.mock import Mock, patch

import pytest

from search.search_executor import SearchExecutor


@pytest.fixture
def executor():
    """SearchExecutor with all dependencies mocked."""
    bm25_index = Mock()
    bm25_index.search.return_value = []

    dense_index = Mock()
    dense_index.search.return_value = []

    embedder = Mock()
    embedder.embed_query.return_value = [0.1] * 768

    reranker = Mock()
    reranker.rerank_simple.return_value = []

    reranking_engine = Mock()
    reranking_engine.apply_neural_reranking.return_value = []

    return SearchExecutor(
        bm25_index=bm25_index,
        dense_index=dense_index,
        embedder=embedder,
        reranker=reranker,
        reranking_engine=reranking_engine,
        gpu_monitor=Mock(),
        logger=logging.getLogger("test"),
    )


def test_bm25_mode_calls_bm25_only(executor):
    """BM25 mode calls bm25_index.search but not dense_index.search."""
    executor.execute_single_hop("test query", k=5, search_mode="bm25")

    executor.bm25_index.search.assert_called_once()
    executor.dense_index.search.assert_not_called()


def test_semantic_mode_calls_dense_only(executor):
    """Semantic mode calls dense_index.search but not bm25_index.search."""
    executor.execute_single_hop("test query", k=5, search_mode="semantic")

    executor.dense_index.search.assert_called_once()
    executor.bm25_index.search.assert_not_called()


def test_hybrid_mode_calls_both_and_reranks(executor):
    """Hybrid mode calls both indices, applies RRF reranking, then neural reranking."""
    mock_result = Mock()
    executor.reranker.rerank_simple.return_value = [mock_result]
    executor.reranking_engine.apply_neural_reranking.return_value = [mock_result]

    results = executor.execute_single_hop("test query", k=5, search_mode="hybrid")

    executor.bm25_index.search.assert_called_once()
    executor.dense_index.search.assert_called_once()
    executor.reranker.rerank_simple.assert_called_once()
    executor.reranking_engine.apply_neural_reranking.assert_called_once()
    assert results == [mock_result]


def test_hybrid_skips_neural_reranking_when_rrf_returns_empty(executor):
    """Neural reranking is skipped when RRF produces no results."""
    executor.reranker.rerank_simple.return_value = []

    executor.execute_single_hop("test query", k=5, search_mode="hybrid")

    executor.reranking_engine.apply_neural_reranking.assert_not_called()


def test_per_call_weights_override_instance_defaults(executor):
    """Explicit bm25_weight/dense_weight args override the instance-level defaults."""
    executor.execute_single_hop(
        "test query", k=5, search_mode="hybrid", bm25_weight=0.7, dense_weight=0.3
    )

    kwargs = executor.reranker.rerank_simple.call_args.kwargs
    assert kwargs["bm25_weight"] == 0.7
    assert kwargs["dense_weight"] == 0.3


def test_parallel_search_falls_back_to_sequential(executor):
    """_parallel_search falls back to _sequential_search when thread pool raises."""
    executor._thread_pool.submit = Mock(side_effect=Exception("pool failure"))

    # Must not raise; fallback result is two empty lists from sequential
    bm25_r, dense_r = executor._parallel_search("query", 5, 0.0, None, None)

    # Sequential path called both indices
    executor.bm25_index.search.assert_called()
    executor.dense_index.search.assert_called()
    assert bm25_r == []
    assert dense_r == []


def test_search_bm25_returns_empty_on_exception(executor):
    """search_bm25 catches exceptions and returns an empty list."""
    executor.bm25_index.search.side_effect = RuntimeError("index corrupted")

    results = executor.search_bm25("query", 5, 0.0)

    assert results == []


def test_search_dense_returns_empty_on_exception(executor):
    """search_dense catches exceptions and returns an empty list."""
    executor.dense_index.search.side_effect = RuntimeError("faiss error")

    results = executor.search_dense("query", 5, None)

    assert results == []


def test_search_dense_creates_embedder_lazily_when_none(executor):
    """search_dense instantiates CodeEmbedder on demand when embedder=None."""
    executor.embedder = None

    mock_instance = Mock()
    mock_instance.embed_query.return_value = [0.0] * 768

    with patch(
        "embeddings.embedder.CodeEmbedder", return_value=mock_instance
    ) as mock_ce:
        executor.search_dense("query", 5, None)

    mock_ce.assert_called_once()
    assert executor.embedder is mock_instance


def test_stats_increment_after_each_search(executor):
    """stats property reflects total_searches count after calls."""
    assert executor.stats["total_searches"] == 0

    executor.execute_single_hop("q1", k=3, search_mode="bm25")
    executor.execute_single_hop("q2", k=3, search_mode="semantic")

    assert executor.stats["total_searches"] == 2


def test_shutdown_sets_flag_and_is_idempotent(executor):
    """shutdown() sets is_shutdown=True and is safe to call twice."""
    assert not executor.is_shutdown

    executor.shutdown()
    assert executor.is_shutdown

    executor.shutdown()  # Second call must not raise
    assert executor.is_shutdown
