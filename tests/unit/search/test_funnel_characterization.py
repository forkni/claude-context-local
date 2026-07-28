"""Characterization tests for the search funnel's width arithmetic.

This file pins what the funnel *does today*, not what it should do — it is
the B0 step of the "characterize, own, observe" architecture-deepening pass
(see plan `study-this-plan-from-purring-meadow.md`). Its job is to make the
next benchmark sweep that silently moves a width (as `search_k`'s floor did,
`50 -> 30`, in `f936d0b`) fail loudly instead of shipping unnoticed.

All values below assume the outer query enters with ``k=4`` and multi-hop
enabled. Multi-hop's hop-1 call widens that to ``initial_k = int(4 * 2.0)
= 8`` (``multi_hop_searcher.py:400``) *before* it reaches
``SearchExecutor.execute_single_hop`` — so the ``SearchExecutor``-level
tests below use ``k=8``/``k=40`` directly (the hop-level input), not the
outer ``k=4``, to reproduce the table in the plan's B0 step verbatim:

    outer k=4
      -> multi-hop widen:      int(4 * 2.0)                = 8
      -> hybrid widen:         max(reranker_budget=30, 8*5) = 40
      -> BM25 re-widen (dir):  40 * 5                       = 200
      -> BM25 re-widen (other):40 * 3                       = 120
      -> dense:                dense_index.search(emb, 40)  = 40
      -> fusion:                max(k=8, reranker_budget=30) = 30
      -> rerank slice:         min(top_k_candidates=30, len) = 30
      -> ego cap (outer k=4):  min(5*1, 4*3)                = 5
      -> parent cap (outer k=4): results[:4]                = 4
      -> output cap (outer k=4): 4 * 8                      = 32

Assertions inspect ``call_args`` on the mocked ``bm25_index``/``dense_index``
directly — nothing else in the suite does this (``test_hybrid_search.py:216``
inspects ``dense_mock.search.call_args`` but only ever asserts ``filters``,
never the width).

The hop-1-skip-under-single_pass pin already exists at
``test_search_executor.py::test_hybrid_single_pass_skips_hop1_neural_rerank``
and is not duplicated here.
"""

import logging
from unittest.mock import Mock, patch

import numpy as np
import pytest

from search.chunk_id import dedupe_results
from search.config import EgoGraphConfig, GraphEnhancedConfig, ParentRetrievalConfig
from search.graph_scoring_stage import GraphScoringStage
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager
from search.multi_hop_searcher import MultiHopSearcher
from search.reranker import SearchResult
from search.reranking_engine import RerankingEngine
from search.search_executor import SearchExecutor


# ---------------------------------------------------------------------------
# SearchExecutor: hybrid widen + fusion (search_executor.py:138-139, :165)
# ---------------------------------------------------------------------------


@pytest.fixture
def executor():
    """SearchExecutor with all dependencies mocked (matches test_search_executor.py)."""
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


def _cfg(top_k_candidates=30, single_pass=False, bm25_reserved_slots=0):
    cfg = Mock()
    cfg.reranker.top_k_candidates = top_k_candidates
    cfg.reranker.single_pass = single_pass
    cfg.search_mode.bm25_reserved_slots = bm25_reserved_slots
    return cfg


def test_hybrid_widen_uses_reranker_budget_floor(executor):
    """search_k = max(reranker_budget, k*5); budget wins when k*5 < budget."""
    with patch("search.search_executor.get_search_config", return_value=_cfg()):
        executor.execute_single_hop("q", k=4, use_parallel=False)

    assert executor.bm25_index.search.call_args[0][1] == 30
    assert executor.dense_index.search.call_args[0][1] == 30


def test_hybrid_widen_uses_k5_when_larger_than_budget(executor):
    """search_k = max(reranker_budget, k*5); k*5 wins once k is large enough."""
    with patch("search.search_executor.get_search_config", return_value=_cfg()):
        executor.execute_single_hop("q", k=8, use_parallel=False)

    assert executor.bm25_index.search.call_args[0][1] == 40
    assert executor.dense_index.search.call_args[0][1] == 40


def test_fusion_k_uses_reranker_budget_floor(executor):
    """fusion_k = max(k, reranker_budget) (search_executor.py:165)."""
    executor.reranker.rerank_simple.return_value = [
        SearchResult(chunk_id="x", score=1.0, metadata={})
    ]
    with patch("search.search_executor.get_search_config", return_value=_cfg()):
        executor.execute_single_hop("q", k=4, use_parallel=False)

    assert executor.reranker.rerank_simple.call_args.kwargs["max_results"] == 30


def test_parallel_search_forwards_k_unmodified(executor):
    """Pins _parallel_search's k-forwarding contract explicitly by keyword.

    test_search_executor.py:112 exercises this same call site positionally
    (``_parallel_search("query", 5, 0.0, None, None)``) and would silently
    absorb a signature reorder; this pin names the argument.
    """
    executor._parallel_search(
        query="q", k=17, min_bm25_score=0.0, filters=None, query_embedding=None
    )

    assert executor.bm25_index.search.call_args[0][1] == 17
    assert executor.dense_index.search.call_args[0][1] == 17


# ---------------------------------------------------------------------------
# SearchExecutor.search_bm25: re-widen + filter cutoff (:257-285)
# ---------------------------------------------------------------------------


def test_bm25_widens_5x_for_directory_filters(executor):
    """search_k = k*5 when filters carry include_dirs/exclude_dirs (:257-258)."""
    executor.search_bm25("q", k=40, min_score=0.0, filters={"include_dirs": ["src"]})

    assert executor.bm25_index.search.call_args[0][1] == 200


def test_bm25_widens_3x_for_other_filters(executor):
    """search_k = k*3 for any other (non-directory) filter (:259-260)."""
    executor.search_bm25("q", k=40, min_score=0.0, filters={"chunk_type": "function"})

    assert executor.bm25_index.search.call_args[0][1] == 120


def test_bm25_no_filters_uses_k_unwidened(executor):
    """search_k = k when no filters are given (:261-262)."""
    executor.search_bm25("q", k=4, min_score=0.0, filters=None)

    assert executor.bm25_index.search.call_args[0][1] == 4


def test_bm25_filter_cutoff_stops_at_k(executor):
    """Filtering stops accumulating once len(filtered) >= k (:281), not search_k."""
    executor.bm25_index.search.return_value = [
        (f"id{i}", 1.0, {"chunk_type": "function", "relative_path": f"f{i}.py"})
        for i in range(10)
    ]

    results = executor.search_bm25(
        "q", k=4, min_score=0.0, filters={"chunk_type": "function"}
    )

    assert len(results) == 4
    assert [r[0] for r in results] == ["id0", "id1", "id2", "id3"]


# ---------------------------------------------------------------------------
# CodeIndexManager.search: FAISS widen (search/indexer.py:247-249)
# ---------------------------------------------------------------------------


def _bare_index_manager(ntotal: int):
    """object.__new__ bypass: search() only reads _faiss_index/_metadata_store/_logger."""
    manager = object.__new__(CodeIndexManager)
    manager._faiss_index = Mock()
    manager._faiss_index.index = Mock()  # non-None sentinel, guard checks `is None`
    manager._faiss_index.ntotal = ntotal
    manager._faiss_index.search.return_value = ([], [])
    manager._metadata_store = Mock()
    manager._logger = logging.getLogger("test")
    return manager


def test_faiss_search_widens_3x_capped_by_ntotal():
    """search_k = min(k*3, ntotal); k*3 wins when ntotal is large (:247-249)."""
    manager = _bare_index_manager(ntotal=1000)

    manager.search(np.zeros(4), k=40)

    assert manager._faiss_index.search.call_args[0][1] == 120


def test_faiss_search_capped_by_ntotal_when_smaller():
    """search_k = min(k*3, ntotal); ntotal wins when the index is small."""
    manager = _bare_index_manager(ntotal=50)

    manager.search(np.zeros(4), k=40)

    assert manager._faiss_index.search.call_args[0][1] == 50


# ---------------------------------------------------------------------------
# MultiHopSearcher: hop-1 widen + single_pass tail (:400, :479-491)
# ---------------------------------------------------------------------------


def test_multihop_widens_initial_k_by_multiplier():
    """initial_k = int(k * initial_k_multiplier) (multi_hop_searcher.py:400)."""
    cfg = Mock()
    cfg.multi_hop.initial_k_multiplier = 2.0
    callback = Mock(return_value=[])  # empty -> early return, still records the call
    searcher = MultiHopSearcher(
        embedder=Mock(),
        dense_index=Mock(),
        single_hop_callback=callback,
        reranking_engine=Mock(),
        logger=logging.getLogger("test"),
    )

    with patch(
        "search.multi_hop_searcher._get_config_via_service_locator", return_value=cfg
    ):
        searcher.search("q", k=4, hops=1)

    assert callback.call_args.kwargs["k"] == 8


def test_multihop_single_pass_tail_sorts_and_slices_without_reranker():
    """single_pass=True skips reranking_engine.rerank_by_query at the tail and
    instead sorts by score + slices to k directly (:479-484)."""
    cfg = Mock()
    cfg.multi_hop.initial_k_multiplier = 1.0
    cfg.multi_hop.multi_hop_mode = "semantic"
    cfg.reranker.single_pass = True

    initial = [
        SearchResult(chunk_id="a", score=0.5, metadata={}),
        SearchResult(chunk_id="b", score=0.9, metadata={}),
    ]
    callback = Mock(return_value=initial)
    reranking_engine = Mock()
    searcher = MultiHopSearcher(
        embedder=Mock(),
        dense_index=Mock(),
        single_hop_callback=callback,
        reranking_engine=reranking_engine,
        logger=logging.getLogger("test"),
    )
    # Bypass hop-2+ expansion internals (not what this test pins).
    searcher.expand_from_initial_results = Mock(return_value={})
    searcher.apply_post_expansion_filters = Mock(
        side_effect=lambda all_results, **_: all_results
    )

    with patch(
        "search.multi_hop_searcher._get_config_via_service_locator", return_value=cfg
    ):
        results = searcher.search("q", k=1, hops=2, filters=None)

    reranking_engine.rerank_by_query.assert_not_called()
    assert [r.chunk_id for r in results] == ["b"]


# ---------------------------------------------------------------------------
# RerankingEngine: rerank slice + dedupe-before-truncate (:209, :278-281)
# ---------------------------------------------------------------------------


def test_rerank_slice_caps_at_top_k_candidates():
    """rerank_count = min(top_k_candidates, len(candidates)) (reranking_engine.py:209)."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine.neural_reranker = Mock()
    engine.neural_reranker.rerank.return_value = []
    cfg = _cfg(top_k_candidates=30)
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=1.0, metadata={}) for i in range(50)
    ]

    engine._run_rerank("q", candidates, k=4, log_prefix="[TEST]", config=cfg)

    passed_candidates = engine.neural_reranker.rerank.call_args[0][1]
    assert len(passed_candidates) == 30


def test_dedupe_split_blocks_can_return_fewer_than_k():
    """dedupe_split_blocks=True collapses split_block siblings *before* the
    [:k] truncation (:278-281), so the funnel can legitimately return fewer
    than k rows even though k results were requested."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)  # skip neural rerank branch
    cfg = Mock()
    cfg.reranker.dedupe_split_blocks = True
    results = [
        SearchResult(chunk_id="mod.py:10-20:split_block:foo", score=0.9, metadata={}),
        SearchResult(chunk_id="mod.py:20-30:split_block:foo", score=0.8, metadata={}),
        SearchResult(chunk_id="other.py:1-5:function:bar", score=0.5, metadata={}),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query("q", results, k=3)

    assert len(out) == 2 < 3
    # Cross-check against the canonical dedupe helper directly.
    assert out == dedupe_results(sorted(results, key=lambda r: r.score, reverse=True))


# ---------------------------------------------------------------------------
# HybridSearcher: ego cap + parent cap (:887-889, :942-946)
# ---------------------------------------------------------------------------


def _bare_hybrid_searcher():
    """object.__new__ bypass: only the attributes these two methods read."""
    searcher = object.__new__(HybridSearcher)
    searcher._logger = logging.getLogger("test")
    searcher.dense_index = Mock()
    searcher.embedder = Mock()
    return searcher


def test_ego_cap_uses_min_of_max_neighbors_and_3k():
    """max_ego = min(max_neighbors_per_hop * k_hops, original_k * 3) (:887-889)."""
    searcher = _bare_hybrid_searcher()
    anchor = SearchResult(chunk_id="anchor", score=1.0, metadata={})
    neighbor_results = [
        SearchResult(chunk_id=f"n{i}", score=0.5, metadata={}) for i in range(10)
    ]
    ego_retriever = Mock()
    ego_retriever.expand_search_results.return_value = (
        [r.chunk_id for r in neighbor_results],
        {},
    )
    ego_retriever.score_neighbors.return_value = neighbor_results
    searcher.ego_graph_retriever = ego_retriever

    ego_config = EgoGraphConfig(max_neighbors_per_hop=5, k_hops=1)
    combined = searcher._apply_ego_graph_expansion(
        [anchor], ego_config, original_k=4, query="q"
    )

    # min(5*1, 4*3) == 5 neighbors survive, plus the 1 anchor.
    assert len(combined) == 6


def test_parent_cap_only_expands_first_max_results_to_expand():
    """results[:max_results_to_expand] bounds which primaries get parent-expanded
    (:942-946); results past that slice never reach dense_index.get_chunk_by_id."""
    searcher = _bare_hybrid_searcher()
    searcher.dense_index.get_chunk_by_id.return_value = {"content": "x"}
    results = [
        SearchResult(
            chunk_id=f"r{i}", score=1.0, metadata={"parent_chunk_id": f"parent{i}"}
        )
        for i in range(6)
    ]
    config = ParentRetrievalConfig(enabled=True)

    searcher._apply_parent_expansion(results, config, max_results_to_expand=4)

    requested = {c.args[0] for c in searcher.dense_index.get_chunk_by_id.call_args_list}
    assert requested == {"parent0", "parent1", "parent2", "parent3"}


# ---------------------------------------------------------------------------
# GraphScoringStage: output cap (:245-249; config.py:451)
# ---------------------------------------------------------------------------


def test_output_cap_is_k_times_max_results_multiplier():
    """max_total = k * max_results_multiplier, default multiplier 8 (config.py:451)."""
    stage = GraphScoringStage()
    results = [{"chunk_id": f"c{i}"} for i in range(40)]

    capped = stage._cap_results(results, k=4, graph_config=None)

    assert len(capped) == 32


# ---------------------------------------------------------------------------
# Derived output ceiling vs. the advertised k*8 cap
# ---------------------------------------------------------------------------


def test_real_output_ceiling_has_slack_vs_advertised_cap():
    """The real worst-case output size is 5k (k multi-hop + 3k ego + k parent),
    not the k*8 the config advertises via max_results_multiplier. Assert the
    derived ceiling explicitly so a future width change that closes this gap
    (or blows past it) is machine-checked rather than discovered in production.
    """
    k = 4
    multi_hop_ceiling = k
    ego_ceiling = k * 3  # min(max_neighbors_per_hop * k_hops, k*3), worst case k*3
    parent_ceiling = k  # one parent per primary result, worst case
    derived_ceiling = multi_hop_ceiling + ego_ceiling + parent_ceiling

    advertised_cap = k * GraphEnhancedConfig().max_results_multiplier

    assert derived_ceiling == 5 * k == 20
    assert derived_ceiling < advertised_cap  # 20 < 32 today — cap has slack
