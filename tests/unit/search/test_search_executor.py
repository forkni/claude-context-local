"""Unit tests for SearchExecutor mode branches and fallback paths."""

import logging
from unittest.mock import Mock, patch

import pytest

from search.config import SearchConfig
from search.search_executor import SearchExecutor
from search.types import RetrievalRequest


def _request(
    query: str = "test query",
    k: int = 5,
    search_mode: str = "hybrid",
    bm25_weight: float = 0.35,
    dense_weight: float = 0.65,
    min_bm25_score: float = 0.0,
    use_parallel: bool = True,
    filters: dict | None = None,
    config: SearchConfig | None = None,
) -> RetrievalRequest:
    """Build a RetrievalRequest for execute_single_hop tests.

    Defaults to a real SearchConfig() (query_expansion disabled, single_pass
    False, bm25_reserved_slots 0) — since C2, execute_single_hop reads
    everything off request.config; there is no more get_search_config()
    fallback to patch, so tests that need non-default config values build
    one and pass it here.
    """
    return RetrievalRequest(
        query=query,
        k=k,
        search_mode=search_mode,
        bm25_weight=bm25_weight,
        dense_weight=dense_weight,
        min_bm25_score=min_bm25_score,
        use_parallel=use_parallel,
        filters=filters,
        config=config if config is not None else SearchConfig(),
    )


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
    executor.execute_single_hop(_request(k=5, search_mode="bm25"))

    executor.bm25_index.search.assert_called_once()
    executor.dense_index.search.assert_not_called()


def test_semantic_mode_calls_dense_only(executor):
    """Semantic mode calls dense_index.search but not bm25_index.search."""
    executor.execute_single_hop(_request(k=5, search_mode="semantic"))

    executor.dense_index.search.assert_called_once()
    executor.bm25_index.search.assert_not_called()


def test_hybrid_mode_calls_both_and_reranks(executor):
    """Hybrid mode calls both indices, applies RRF reranking, then neural reranking."""
    mock_result = Mock()
    executor.reranker.rerank_simple.return_value = [mock_result]
    executor.reranking_engine.apply_neural_reranking.return_value = [mock_result]

    results = executor.execute_single_hop(_request(k=5, search_mode="hybrid"))

    executor.bm25_index.search.assert_called_once()
    executor.dense_index.search.assert_called_once()
    executor.reranker.rerank_simple.assert_called_once()
    executor.reranking_engine.apply_neural_reranking.assert_called_once()
    assert results == [mock_result]


def test_hybrid_single_pass_skips_hop1_neural_rerank(executor):
    """Q3 single_pass: hop-1 keeps RRF order; neural rerank deferred to the
    one listwise pass at the tail of HybridSearcher.search()."""
    mock_result = Mock()
    executor.reranker.rerank_simple.return_value = [mock_result]

    cfg = SearchConfig()
    cfg.reranker.single_pass = True
    results = executor.execute_single_hop(
        _request(k=5, search_mode="hybrid", config=cfg)
    )

    executor.reranking_engine.apply_neural_reranking.assert_not_called()
    assert results == [mock_result]


def test_hybrid_skips_neural_reranking_when_rrf_returns_empty(executor):
    """Neural reranking is skipped when RRF produces no results."""
    executor.reranker.rerank_simple.return_value = []

    executor.execute_single_hop(_request(k=5, search_mode="hybrid"))

    executor.reranking_engine.apply_neural_reranking.assert_not_called()


def test_request_weights_reach_rerank_simple(executor):
    """request.bm25_weight/dense_weight (resolved upstream by HybridSearcher)
    flow straight through to the fusion call. C2 removed the instance-level
    bm25_weight/dense_weight fields that used to silently hide a dropped
    per-call weight behind a stale construction-time default — there is no
    fallback left to override; the request is the only source now."""
    executor.execute_single_hop(
        _request(k=5, search_mode="hybrid", bm25_weight=0.7, dense_weight=0.3)
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

    executor.execute_single_hop(_request(query="q1", k=3, search_mode="bm25"))
    executor.execute_single_hop(_request(query="q2", k=3, search_mode="semantic"))

    assert executor.stats["total_searches"] == 2


def test_hybrid_disabled_expansion_takes_exact_rerank_simple_path(executor):
    """query_expansion.enabled=False (the default) → today's rerank_simple call,
    never the generic rerank(); regression guard for the unexpanded path."""
    executor.execute_single_hop(
        _request(query="survive a restart", k=5, search_mode="hybrid")
    )

    executor.reranker.rerank_simple.assert_called_once()
    executor.reranker.rerank.assert_not_called()


def test_hybrid_enabled_but_unmatched_query_takes_rerank_simple_path(executor):
    """Enabled expansion with no concept match must still take rerank_simple."""
    cfg = SearchConfig()
    cfg.query_expansion.enabled = True
    cfg.query_expansion.variants_path = ""
    cfg.query_expansion.max_variants = 2
    cfg.query_expansion.variant_weight_discount = 0.5
    cfg.query_expansion.apply_to_bm25 = True
    cfg.query_expansion.apply_to_dense = False

    executor.execute_single_hop(
        _request(
            query="where is QueryRouter defined", k=5, search_mode="hybrid", config=cfg
        )
    )

    executor.reranker.rerank_simple.assert_called_once()
    executor.reranker.rerank.assert_not_called()


def test_hybrid_enabled_matched_query_fuses_variant_legs(executor):
    """Enabled + matched concept → generic rerank() with >2 lists and the
    variant leg weighted at bm25_weight * variant_weight_discount."""
    executor.reranker.rerank.return_value = []
    cfg = SearchConfig()
    cfg.query_expansion.enabled = True
    cfg.query_expansion.variants_path = ""
    cfg.query_expansion.max_variants = 2
    cfg.query_expansion.variant_weight_discount = 0.5
    cfg.query_expansion.apply_to_bm25 = True
    cfg.query_expansion.apply_to_dense = False

    executor.execute_single_hop(
        _request(
            query="how does state survive a restart",
            k=5,
            search_mode="hybrid",
            config=cfg,
        )
    )

    executor.reranker.rerank_simple.assert_not_called()
    kwargs = executor.reranker.rerank.call_args.kwargs
    assert len(kwargs["results_lists"]) == 3  # bm25 + dense + 1 variant leg
    assert kwargs["weights"] == [0.35, 0.65, 0.35 * 0.5]
    assert kwargs["reserve_list_idx"] == 0
    # Variant leg searched BM25 with the expanded query text
    variant_call = executor.bm25_index.search.call_args_list[-1]
    assert "survive a restart" in variant_call.args[0]
    assert "persist" in variant_call.args[0]


def test_shutdown_sets_flag_and_is_idempotent(executor):
    """shutdown() sets is_shutdown=True and is safe to call twice."""
    assert not executor.is_shutdown

    executor.shutdown()
    assert executor.is_shutdown

    executor.shutdown()  # Second call must not raise
    assert executor.is_shutdown
