"""Characterization tests for the search funnel's width arithmetic.

This file pins what the funnel *does today*, not what it should do — it is
the B0 step of the "characterize, own, observe" architecture-deepening pass
(see plan `study-this-plan-from-purring-meadow.md`). Its job is to make the
next benchmark sweep that silently moves a width (as `search_k`'s floor did,
`50 -> 30`, in `f936d0b`) fail loudly instead of shipping unnoticed.

All values below assume the outer query enters with ``k=7`` — the production
default (``SearchMode.default_k``, ``config.py:408-417``) — and multi-hop
enabled. Multi-hop's hop-1 call widens that to ``initial_k = int(7 * 2.0)
= 14`` (``multi_hop_searcher.py:557``) *before* it reaches
``SearchExecutor.execute_single_hop``. The widen/cut formulas are not
re-derived inline here or below — they live once, canonically, as
``leg_search_depth`` and ``fused_pool_cut`` (``search_executor.py:29-57``,
called at ``:161``/``:204``); most individual tests below instead use
explicit, self-contained k values (``k=4``, ``k=8``, ``k=40``, etc.) to pin
those formulas in isolation, independent of whatever the outer default
happens to be. The table traces what the formulas produce when actually fed
the production default, end to end:

    outer k=7
      -> multi-hop widen:      int(7 * 2.0)                 = 14
      -> hybrid widen:         max(reranker_budget=30, 14*5) = 70
      -> BM25 re-widen (dir):  70 * 5                        = 350
      -> BM25 re-widen (other):70 * 3                        = 210
      -> dense:                dense_index.search(emb, 70)   = 70
      -> FAISS widen (indexer.py:288-290): min(70*3, ntotal)  = 210
      -> fusion:                max(k=14, reranker_budget=30) = 30
      -> rerank slice:         min(top_k_candidates=30, len)  = 30
      -> ego cap (outer k=7):  min(10*2, 7*3)                = 20
      -> parent cap (outer k=7): results[:7]                 = 7
      -> output cap (outer k=7): 7 * 8                       = 56

Assertions inspect ``call_args`` on the mocked ``bm25_index``/``dense_index``
directly — nothing else in the suite does this (``test_hybrid_search.py:312``
inspects ``dense_mock.search.call_args`` but only ever asserts ``filters``,
never the width).

The hop-1-skip-under-single_pass pin already exists at
``test_search_executor.py::test_hybrid_single_pass_skips_hop1_neural_rerank``
(``:119``) and is not duplicated here.
"""

import logging
from unittest.mock import Mock, patch

import numpy as np
import pytest

from search.chunk_id import dedupe_results
from search.config import (
    EgoGraphConfig,
    GraphEnhancedConfig,
    ParentRetrievalConfig,
    SearchMode,
)
from search.graph_scoring_stage import GraphScoringStage
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager
from search.multi_hop_searcher import MultiHopSearcher
from search.rerank_window_policy import RerankWindowPolicy
from search.reranker import SearchResult
from search.reranking_engine import RerankingEngine
from search.search_executor import SearchExecutor
from search.types import RetrievalRequest


# ---------------------------------------------------------------------------
# SearchExecutor: hybrid widen + fusion via leg_search_depth/fused_pool_cut
# (search_executor.py:29-57, called at :161/:204)
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


def _cfg(
    top_k_candidates=30, single_pass=False, bm25_reserved_slots=0, hop1_reserved_slots=0
):
    cfg = Mock()
    cfg.reranker.top_k_candidates = top_k_candidates
    cfg.reranker.single_pass = single_pass
    cfg.reranker.hop1_reserved_slots = hop1_reserved_slots
    cfg.search_mode.bm25_reserved_slots = bm25_reserved_slots
    cfg.search_mode.leg_search_multiplier = 5
    cfg.search_mode.fusion_function = "rrf"
    cfg.query_expansion.enabled = False  # Mock attrs are truthy by default
    return cfg


def _request(
    query="q",
    k=4,
    search_mode=SearchMode.HYBRID,
    use_parallel=True,
    filters=None,
    config=None,
    bm25_weight=0.35,
    dense_weight=0.65,
    min_bm25_score=0.0,
):
    """Build a RetrievalRequest for execute_single_hop funnel-width tests.

    config defaults to _cfg() (rather than a real SearchConfig) so these
    tests keep asserting against the same explicit knob values they always
    have — execute_single_hop reads everything off request.config now, there
    is no more get_search_config() import in search_executor.py to patch.
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
        config=config if config is not None else _cfg(),
    )


def test_hybrid_widen_uses_reranker_budget_floor(executor):
    """search_k = max(reranker_budget, k*5); budget wins when k*5 < budget."""
    executor.execute_single_hop(_request(k=4, use_parallel=False))

    assert executor.bm25_index.search.call_args[0][1] == 30
    assert executor.dense_index.search.call_args[0][1] == 30


def test_hybrid_widen_uses_k5_when_larger_than_budget(executor):
    """search_k = max(reranker_budget, k*5); k*5 wins once k is large enough."""
    executor.execute_single_hop(_request(k=8, use_parallel=False))

    assert executor.bm25_index.search.call_args[0][1] == 40
    assert executor.dense_index.search.call_args[0][1] == 40


def test_fusion_k_uses_reranker_budget_floor(executor):
    """fusion_k = max(k, reranker_budget) (fused_pool_cut, search_executor.py:204)."""
    executor.reranker.rerank_simple.return_value = [
        SearchResult(chunk_id="x", score=1.0, metadata={})
    ]
    executor.execute_single_hop(_request(k=4, use_parallel=False))

    assert executor.reranker.rerank_simple.call_args.kwargs["max_results"] == 30


def test_parallel_search_forwards_k_unmodified(executor):
    """Pins _parallel_search's k-forwarding contract explicitly by keyword.

    test_search_executor.py:164 exercises this same call site positionally
    (``_parallel_search("query", 5, 0.0, None, None)``) and would silently
    absorb a signature reorder; this pin names the argument.
    """
    executor._parallel_search(
        query="q", k=17, min_bm25_score=0.0, filters=None, query_embedding=None
    )

    assert executor.bm25_index.search.call_args[0][1] == 17
    assert executor.dense_index.search.call_args[0][1] == 17


# ---------------------------------------------------------------------------
# SearchExecutor.search_bm25: re-widen + filter cutoff (:375-428)
# ---------------------------------------------------------------------------


def test_bm25_widens_5x_for_directory_filters(executor):
    """search_k = k*5 when filters carry include_dirs/exclude_dirs (:383-384)."""
    executor.search_bm25("q", k=40, min_score=0.0, filters={"include_dirs": ["src"]})

    assert executor.bm25_index.search.call_args[0][1] == 200


def test_bm25_widens_3x_for_other_filters(executor):
    """search_k = k*3 for any other (non-directory) filter (:385-386)."""
    executor.search_bm25("q", k=40, min_score=0.0, filters={"chunk_type": "function"})

    assert executor.bm25_index.search.call_args[0][1] == 120


def test_bm25_no_filters_uses_k_unwidened(executor):
    """search_k = k when no filters are given (:387-388)."""
    executor.search_bm25("q", k=4, min_score=0.0, filters=None)

    assert executor.bm25_index.search.call_args[0][1] == 4


def test_bm25_filter_cutoff_stops_at_k(executor):
    """Filtering stops accumulating once len(filtered) >= k (:407), not search_k."""
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
# CodeIndexManager.search: FAISS widen (search/indexer.py:288-290)
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
    """search_k = min(k*3, ntotal); k*3 wins when ntotal is large (:288-290)."""
    manager = _bare_index_manager(ntotal=1000)

    manager.search(np.zeros(4), k=40)

    assert manager._faiss_index.search.call_args[0][1] == 120


def test_faiss_search_capped_by_ntotal_when_smaller():
    """search_k = min(k*3, ntotal); ntotal wins when the index is small."""
    manager = _bare_index_manager(ntotal=50)

    manager.search(np.zeros(4), k=40)

    assert manager._faiss_index.search.call_args[0][1] == 50


# ---------------------------------------------------------------------------
# MultiHopSearcher: hop-1 widen + single_pass tail (:557, :652-659)
# ---------------------------------------------------------------------------


def _mh_request(query="q", k=4, config=None, filters=None):
    """Build a RetrievalRequest for MultiHopSearcher.search tests.

    config defaults to a bare Mock (rather than _cfg()) since these tests
    exercise multi_hop-specific knobs that _cfg() doesn't set.
    """
    return RetrievalRequest(
        query=query,
        k=k,
        search_mode=SearchMode.HYBRID,
        bm25_weight=0.35,
        dense_weight=0.65,
        min_bm25_score=0.0,
        use_parallel=True,
        filters=filters,
        config=config if config is not None else Mock(),
    )


def test_multihop_widens_initial_k_by_multiplier():
    """initial_k = int(k * initial_k_multiplier) (multi_hop_searcher.py:557)."""
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

    searcher.search(_mh_request(k=4, config=cfg), hops=1)

    req = callback.call_args.args[0]
    assert req.k == 8


def test_multihop_single_pass_tail_sorts_and_slices_without_reranker():
    """single_pass=True skips reranking_engine.rerank_by_query at the tail and
    instead sorts by score + slices to k directly (:652-659)."""
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

    results = searcher.search(_mh_request(k=1, config=cfg, filters=None), hops=2)

    reranking_engine.rerank_by_query.assert_not_called()
    assert [r.chunk_id for r in results] == ["b"]


# ---------------------------------------------------------------------------
# RerankingEngine: rerank slice + dedupe-before-truncate (:236, :548-551)
# ---------------------------------------------------------------------------


def test_rerank_slice_caps_at_top_k_candidates():
    """rerank_count = min(top_k_candidates, len(candidates)) (reranking_engine.py:236)."""
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


def test_hop1_reserve_default_zero_is_identical_window():
    """hop1_reserved_slots=0 (default) must reproduce the exact pre-existing
    window — no reserve logic runs at all (multi-hop pool flooding fix,
    docs/adr/0013-hop1-reserve-at-final-pool.md)."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)  # skip neural rerank branch
    cfg = _cfg(top_k_candidates=5, hop1_reserved_slots=0)
    # 10 candidates: only the top 5 by score should ever reach the reranker,
    # even though a lower-scored candidate is tagged hop1_rank=1.
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=float(9 - i), metadata={})
        for i in range(10)
    ]
    candidates[9].metadata["hop1_rank"] = 1  # lowest score, best hop1 rank

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query("q", candidates, k=5, config=cfg)

    assert [r.chunk_id for r in out] == ["c0", "c1", "c2", "c3", "c4"]


def test_hop1_reserve_promotes_tagged_candidate_into_window():
    """hop1_reserved_slots > 0 promotes the best-hop1-ranked candidate from
    outside the top_k_candidates window back into it, evicting the window's
    worst-scored entry (order otherwise irrelevant — the reranker re-scores
    the whole window)."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)  # skip neural rerank branch
    cfg = _cfg(top_k_candidates=5, hop1_reserved_slots=1)
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=float(9 - i), metadata={})
        for i in range(10)
    ]
    candidates[9].metadata["hop1_rank"] = (
        1  # score 0.0, would be cut without the reserve
    )

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q",
            candidates,
            k=5,
            config=cfg,
            window=RerankWindowPolicy(hop1_reserved_slots=1),
        )

    out_ids = {r.chunk_id for r in out}
    assert "c9" in out_ids
    assert "c4" not in out_ids  # evicted to make room
    assert len(out) == 5


def test_hop1_reserve_noop_when_pool_within_window():
    """No-op when the merged pool doesn't exceed top_k_candidates — nothing
    to reserve room for."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)  # skip neural rerank branch
    cfg = _cfg(top_k_candidates=30, hop1_reserved_slots=3)
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=float(9 - i), metadata={})
        for i in range(10)
    ]
    candidates[9].metadata["hop1_rank"] = 1

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q",
            candidates,
            k=5,
            config=cfg,
            window=RerankWindowPolicy(hop1_reserved_slots=3),
        )

    assert [r.chunk_id for r in out] == ["c0", "c1", "c2", "c3", "c4"]


def test_hop1_reserve_ego_tail_call_site_unaffected():
    """rerank_by_query's hop1_reserved_slots parameter defaults to 0 — calls
    that don't pass it explicitly (the ego-graph/parent-expansion tail in
    HybridSearcher) are byte-identical even when the config value is
    non-zero, because the config is only read for top_k_candidates unless
    the caller opts in via the argument."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)  # skip neural rerank branch
    # Config has a non-zero knob value, but the caller (simulating the
    # ego-tail call sites) doesn't pass hop1_reserved_slots.
    cfg = _cfg(top_k_candidates=5, hop1_reserved_slots=3)
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=float(9 - i), metadata={})
        for i in range(10)
    ]
    candidates[9].metadata["hop1_rank"] = 1

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q", candidates, k=5, config=cfg
        )  # no window kwarg -- default policy is tail()

    assert [r.chunk_id for r in out] == ["c0", "c1", "c2", "c3", "c4"]


def test_dedupe_split_blocks_can_return_fewer_than_k():
    """dedupe_split_blocks=True collapses split_block siblings *before* the
    [:k] truncation (:548-551), so the funnel can legitimately return fewer
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
        out = engine.rerank_by_query("q", results, k=3, config=cfg)

    assert len(out) == 2 < 3
    # Cross-check against the canonical dedupe helper directly.
    assert out == dedupe_results(sorted(results, key=lambda r: r.score, reverse=True))


# ---------------------------------------------------------------------------
# merged_pool_policy: ordering + eviction fix (reranking_engine.py:267-336)
#
# Repairs finding (E) — the merged multi-hop pool's raw-.score sort mixes
# three incomparable scales (hop-1 jina relevance, semantic-expansion raw
# FAISS cosine, graph-expansion literal 0.0), so hop1_reserved_slots' blind
# tail eviction can evict a BETTER-ranked hop-1 survivor to make room for a
# worse-ranked one. See docs/adr/0013-hop1-reserve-at-final-pool.md and
# evaluation/POOL_ORDER_AB_20260815.md.
# ---------------------------------------------------------------------------


def test_merged_pool_policy_default_is_score():
    """merged_pool_policy="score" (default) is byte-identical to the
    pre-existing sort — negatives, ties, and zero scores all sort purely by
    .score descending, independent of source/metadata. Ties preserve
    original (stable-sort) order."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=10)
    candidates = [
        SearchResult(chunk_id="neg", score=-0.5, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="zero_a", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(
            chunk_id="zero_b", score=0.0, metadata={"hop1_rank": 1}, source="unknown"
        ),
        SearchResult(chunk_id="hi", score=0.9, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="tie_a", score=0.4, metadata={}, source="graph_hop"),
        SearchResult(
            chunk_id="tie_b", score=0.4, metadata={"hop1_rank": 2}, source="unknown"
        ),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query("q", candidates, k=6, config=cfg)

    assert [r.chunk_id for r in out] == [
        "hi",
        "tie_a",
        "tie_b",
        "zero_a",
        "zero_b",
        "neg",
    ]


def test_merged_pool_policy_ego_tail_call_site_unaffected():
    """rerank_by_query's merged_pool_policy defaults to "score" — calls that
    don't pass it explicitly (the ego-graph/parent-expansion tail in
    HybridSearcher) stay on the plain score sort regardless of what
    config.reranker.merged_pool_policy holds, because the policy is a
    call-scoped argument, not something read off config internally."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=10)
    candidates = [
        SearchResult(chunk_id="hi", score=0.9, metadata={}, source="graph_hop"),
        SearchResult(
            chunk_id="hop1_best",
            score=-0.5,
            metadata={"hop1_rank": 1},
            source="unknown",
        ),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q", candidates, k=2, config=cfg
        )  # no window kwarg -- default policy is tail()

    # Plain score sort — graph_hop's 0.9 beats hop1's -0.5, exactly as
    # today, regardless of the policy live in config.
    assert [r.chunk_id for r in out] == ["hi", "hop1_best"]


def test_channel_priority_orders_hop1_then_semantic_then_graph():
    """channel_priority never compares across scales: hop-1 survivors (by
    hop1_rank ascending) sort ahead of semantic expansion (by score
    descending), which sorts ahead of graph expansion (insertion order) —
    even when the hop-1 entries have the lowest raw scores in the fixture."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=10)
    candidates = [
        SearchResult(chunk_id="graph_a", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(
            chunk_id="semantic_hi", score=0.9, metadata={}, source="multi_hop"
        ),
        SearchResult(
            chunk_id="hop1_worst",
            score=-0.9,
            metadata={"hop1_rank": 2},
            source="unknown",
        ),
        SearchResult(chunk_id="graph_b", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(
            chunk_id="semantic_lo", score=0.5, metadata={}, source="multi_hop"
        ),
        SearchResult(
            chunk_id="hop1_best",
            score=-0.95,
            metadata={"hop1_rank": 1},
            source="unknown",
        ),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q",
            candidates,
            k=6,
            config=cfg,
            window=RerankWindowPolicy(merged_pool_policy="channel_priority"),
        )

    assert [r.chunk_id for r in out] == [
        "hop1_best",
        "hop1_worst",
        "semantic_hi",
        "semantic_lo",
        "graph_a",
        "graph_b",
    ]


def test_channel_priority_makes_hop1_reserve_inert():
    """Under channel_priority, all hop-1 candidates already sit in tier 0
    (ahead of top_k_candidates), so _apply_hop1_reserve's tail scan finds no
    hop1-tagged tail entries and hits its early return — passing a non-zero
    hop1_reserved_slots changes nothing versus 0 (retires the analytical
    confound noted in the plan's Phase 2)."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=3)
    candidates = [
        SearchResult(
            chunk_id=f"hop1_{i}",
            score=float(i),
            metadata={"hop1_rank": i},
            source="unknown",
        )
        for i in range(3)
    ] + [
        SearchResult(
            chunk_id=f"semantic_{i}",
            score=float(9 - i),
            metadata={},
            source="multi_hop",
        )
        for i in range(5)
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        without_reserve = engine.rerank_by_query(
            "q",
            candidates,
            k=8,
            config=cfg,
            window=RerankWindowPolicy(
                merged_pool_policy="channel_priority", hop1_reserved_slots=0
            ),
        )
        with_reserve = engine.rerank_by_query(
            "q",
            candidates,
            k=8,
            config=cfg,
            window=RerankWindowPolicy(
                merged_pool_policy="channel_priority", hop1_reserved_slots=5
            ),
        )

    assert [r.chunk_id for r in without_reserve] == [r.chunk_id for r in with_reserve]


def test_hop1_reserve_tail_eviction_drops_top_hop1_characterization():
    """Characterizes finding (E): under the default "score"/"tail" eviction,
    promoting a worse-ranked hop-1 candidate can evict a BETTER-ranked hop-1
    candidate already sitting in the window's score-sorted tail — because
    the score sort puts every hop-1 survivor below every semantic-expansion
    candidate, the window's tail IS the hop-1 region."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=4, hop1_reserved_slots=1)
    candidates = [
        # Window (top 4 by score): 3 semantic winners + hop1 rank-1 (best),
        # sitting in the window's lowest-scored (tail) slot.
        SearchResult(chunk_id="semantic_a", score=0.9, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="semantic_b", score=0.8, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="semantic_c", score=0.7, metadata={}, source="multi_hop"),
        SearchResult(
            chunk_id="hop1_rank1",
            score=0.6,
            metadata={"hop1_rank": 1},
            source="unknown",
        ),
        # Outside the window: a WORSE-ranked hop1 candidate, lower score.
        SearchResult(
            chunk_id="hop1_rank2",
            score=0.1,
            metadata={"hop1_rank": 2},
            source="unknown",
        ),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q",
            candidates,
            k=5,
            config=cfg,
            window=RerankWindowPolicy(hop1_reserved_slots=1),
        )

    out_ids = [r.chunk_id for r in out]
    assert "hop1_rank2" in out_ids  # promoted, as intended
    assert "hop1_rank1" not in out_ids  # but the BETTER-ranked survivor got evicted


def test_score_reserve_fix_evicts_lowest_non_hop1():
    """merged_pool_policy="score_reserve_fix" keeps the score sort but fixes
    finding (E): eviction prefers the window's lowest-scored NON-hop1 entry,
    so a hop-1 promotion no longer evicts a better-ranked hop-1 incumbent.
    Also pins the permutation contract via Counter — no items are silently
    duplicated or dropped beyond the intended eviction."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=4, hop1_reserved_slots=1)
    candidates = [
        SearchResult(chunk_id="semantic_a", score=0.9, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="semantic_b", score=0.8, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="semantic_c", score=0.7, metadata={}, source="multi_hop"),
        SearchResult(
            chunk_id="hop1_rank1",
            score=0.6,
            metadata={"hop1_rank": 1},
            source="unknown",
        ),
        SearchResult(
            chunk_id="hop1_rank2",
            score=0.1,
            metadata={"hop1_rank": 2},
            source="unknown",
        ),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q",
            candidates,
            k=5,
            config=cfg,
            window=RerankWindowPolicy(
                hop1_reserved_slots=1, merged_pool_policy="score_reserve_fix"
            ),
        )

    out_ids = [r.chunk_id for r in out]
    assert "hop1_rank1" in out_ids  # the better-ranked hop1 survivor is kept
    assert "hop1_rank2" in out_ids  # the promoted candidate is present too
    assert "semantic_c" not in out_ids  # lowest-scored non-hop1 entry evicted instead

    from collections import Counter

    assert Counter(out_ids) == Counter(
        ["semantic_a", "semantic_b", "hop1_rank1", "hop1_rank2"]
    )


def test_order_merged_pool_score_returns_plain_sorted_by_score():
    """_order_merged_pool("score") is the literal pre-existing sort
    expression — direct unit check independent of rerank_by_query's
    surrounding config/reranker plumbing."""
    candidates = [
        SearchResult(chunk_id="lo", score=-1.0, metadata={}),
        SearchResult(chunk_id="hi", score=1.0, metadata={}),
        SearchResult(chunk_id="mid", score=0.0, metadata={}),
    ]

    out = RerankingEngine._order_merged_pool(candidates, "score")

    assert [r.chunk_id for r in out] == ["hi", "mid", "lo"]
    assert out == sorted(candidates, key=lambda r: r.score, reverse=True)


def test_order_merged_pool_unknown_policy_raises():
    """Guards against a typo'd --set arm silently no-op'ing on an unknown
    merged_pool_policy value."""
    with pytest.raises(ValueError, match="Unknown merged_pool_policy"):
        RerankingEngine._order_merged_pool([], "bogus")


# ---------------------------------------------------------------------------
# graph_hop_unscored: explicit provenance-banded ordering (ADR-0039). A
# caller-declared, default-off refinement of the "score"/"score_reserve_fix"
# branch above — replaces the incidental placement of graph_hop's literal
# 0.0 placeholder (tied with real 0.0 scores under a plain sort) with an
# explicit band, without comparing it against a real score. See
# evaluation/probe_rerank_window_20260815.json (0 of 4,129 non-graph pool
# entries score exactly 0.0 — the only case where the two orderings diverge).
# ---------------------------------------------------------------------------


def test_order_merged_pool_graph_hop_unscored_bands_by_provenance():
    """graph_hop_unscored=True: positive-scored descending, then every
    graph_hop entry in insertion order, then nonpositive-scored descending —
    and, absent a non-graph exact-0.0 tie, this is byte-identical to the
    plain score sort."""
    candidates = [
        SearchResult(chunk_id="pos_hi", score=0.9, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="pos_lo", score=0.2, metadata={}, source="hybrid"),
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g1", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="neg_hi", score=-0.1, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="neg_lo", score=-0.5, metadata={}, source="multi_hop"),
    ]

    banded = RerankingEngine._order_merged_pool(
        candidates, "score", graph_hop_unscored=True
    )
    plain = RerankingEngine._order_merged_pool(candidates, "score")

    expected = ["pos_hi", "pos_lo", "g0", "g1", "neg_hi", "neg_lo"]
    assert [r.chunk_id for r in banded] == expected
    assert [r.chunk_id for r in plain] == expected


def test_order_merged_pool_graph_hop_unscored_divergence_pin():
    """The one case where banded and plain sort diverge: a non-graph
    candidate scoring exactly 0.0. Pinned direction — it lands in the
    nonpositive band, i.e. after every graph_hop entry — even though it
    appears BEFORE the graph entries in insertion order, which is where a
    plain stable sort's tie-breaking would keep it."""
    candidates = [
        SearchResult(chunk_id="pos", score=0.5, metadata={}, source="multi_hop"),
        SearchResult(
            chunk_id="zero_nongraph", score=0.0, metadata={}, source="unknown"
        ),
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g1", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="neg", score=-0.3, metadata={}, source="multi_hop"),
    ]

    plain = RerankingEngine._order_merged_pool(candidates, "score")
    banded = RerankingEngine._order_merged_pool(
        candidates, "score", graph_hop_unscored=True
    )

    # Plain: stable-sort tie at 0.0 keeps zero_nongraph's original position
    # ahead of g0/g1.
    assert [r.chunk_id for r in plain] == [
        "pos",
        "zero_nongraph",
        "g0",
        "g1",
        "neg",
    ]
    # Banded: zero_nongraph is not source=="graph_hop", so it is never
    # placed in the graph band regardless of insertion order.
    assert [r.chunk_id for r in banded] == [
        "pos",
        "g0",
        "g1",
        "zero_nongraph",
        "neg",
    ]


def test_order_merged_pool_graph_hop_unscored_permutation_invariant():
    """Banding never drops or duplicates entries, and the graph band
    preserves the original relative order of graph_hop candidates even when
    interleaved with other sources."""
    from collections import Counter

    candidates = [
        SearchResult(chunk_id="s0", score=0.7, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="s1", score=-0.2, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="g1", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g2", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="s2", score=0.3, metadata={}, source="hybrid"),
    ]

    out = RerankingEngine._order_merged_pool(
        candidates, "score", graph_hop_unscored=True
    )

    assert Counter(r.chunk_id for r in out) == Counter(r.chunk_id for r in candidates)
    graph_ids = [r.chunk_id for r in out if r.source == "graph_hop"]
    assert graph_ids == ["g0", "g1", "g2"]


def test_order_merged_pool_channel_priority_ignores_graph_hop_unscored():
    """graph_hop_unscored only affects the "score"/"score_reserve_fix"
    branch -- channel_priority's output is identical regardless of it."""
    candidates = [
        SearchResult(chunk_id="graph_a", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="semantic_a", score=0.6, metadata={}, source="multi_hop"),
        SearchResult(
            chunk_id="hop1_a", score=-0.4, metadata={"hop1_rank": 1}, source="unknown"
        ),
    ]

    default = RerankingEngine._order_merged_pool(candidates, "channel_priority")
    with_flag = RerankingEngine._order_merged_pool(
        candidates, "channel_priority", graph_hop_unscored=True
    )

    assert [r.chunk_id for r in default] == [r.chunk_id for r in with_flag]


def test_graph_hop_unscored_ego_tail_call_site_unaffected():
    """rerank_by_query's graph_hop_unscored defaults to False -- calls that
    don't pass it explicitly (the ego-graph/parent-expansion tail in
    HybridSearcher) stay on the plain score sort even on a pool that WOULD
    band differently, because Pass-2 survivors reaching that tail under
    source=="graph_hop" carry real, already-reranked scores, not
    placeholders."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=10)
    candidates = [
        SearchResult(chunk_id="pos", score=0.5, metadata={}, source="multi_hop"),
        SearchResult(
            chunk_id="zero_nongraph", score=0.0, metadata={}, source="unknown"
        ),
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="neg", score=-0.3, metadata={}, source="multi_hop"),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q", candidates, k=4, config=cfg
        )  # no window kwarg -- default policy is tail()

    # Plain sort: zero_nongraph keeps its stable-sort tie position ahead of
    # g0, the opposite of what banding would do.
    assert [r.chunk_id for r in out] == ["pos", "zero_nongraph", "g0", "neg"]


def test_apply_hop1_reserve_unknown_evict_policy_raises():
    """Guards against a typo'd evict_policy value silently no-op'ing."""
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=float(9 - i), metadata={})
        for i in range(10)
    ]
    candidates[9].metadata["hop1_rank"] = 1

    with pytest.raises(ValueError, match="Unknown evict_policy"):
        RerankingEngine._apply_hop1_reserve(
            candidates, top_k_candidates=5, reserved_slots=1, evict_policy="bogus"
        )


# ---------------------------------------------------------------------------
# graph_hop_window_cap: caps zero-signal graph_hop occupancy in the rerank
# window (reranking_engine.py:338-390). Reopening direction (b) from
# evaluation/POOL_ORDER_AB_20260815.md, gated by
# evaluation/POOL_ORDER_CAP_PROBE_20260815.md — a standalone knob, not a
# fourth merged_pool_policy choice, since that key is verdict-locked.
# ---------------------------------------------------------------------------


def test_graph_hop_window_cap_zero_is_noop_same_object():
    """cap<=0 is the deployed default -- must return the identical input
    object (no copy), same contract as _order_merged_pool's byte-identical
    "score" path."""
    candidates = [
        SearchResult(chunk_id=f"g{i}", score=0.0, metadata={}, source="graph_hop")
        for i in range(40)
    ]

    out = RerankingEngine._apply_graph_hop_window_cap(
        candidates, top_k_candidates=30, cap=0
    )

    assert out is candidates


def test_graph_hop_window_cap_small_pool_is_noop_same_object():
    """Pool not exceeding top_k_candidates never needs capping -- identical
    input object returned even with cap>0."""
    candidates = [
        SearchResult(chunk_id=f"g{i}", score=0.0, metadata={}, source="graph_hop")
        for i in range(5)
    ]

    out = RerankingEngine._apply_graph_hop_window_cap(
        candidates, top_k_candidates=30, cap=2
    )

    assert out is candidates


def test_graph_hop_window_cap_permutation_invariant():
    """Output is always a permutation of the input -- nothing silently
    duplicated or dropped, regardless of channel mix."""
    from collections import Counter

    candidates = [
        SearchResult(chunk_id=f"g{i}", score=0.0, metadata={}, source="graph_hop")
        for i in range(10)
    ] + [
        SearchResult(
            chunk_id=f"s{i}", score=float(10 - i), metadata={}, source="multi_hop"
        )
        for i in range(25)
    ]

    out = RerankingEngine._apply_graph_hop_window_cap(
        candidates, top_k_candidates=30, cap=3
    )

    assert len(out) == len(candidates)
    assert Counter(r.chunk_id for r in out) == Counter(r.chunk_id for r in candidates)


def test_graph_hop_window_cap_admits_exactly_cap_and_backfills():
    """Admits the first `cap` graph_hop entries (insertion order) into the
    window, defers the rest just below it preserving their relative order,
    and backfills the freed slots with the next non-graph candidates in
    scan order -- the unscanned tail is appended last, untouched."""
    candidates = [
        SearchResult(chunk_id="s0", score=0.9, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g1", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g2", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="s1", score=-0.1, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="g3", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="s2", score=-0.2, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="s3", score=-0.3, metadata={}, source="multi_hop"),
    ]

    out = RerankingEngine._apply_graph_hop_window_cap(
        candidates, top_k_candidates=5, cap=2
    )

    # window (first 5): s0, g0, g1 admitted; g2 deferred so s1, s2 backfill
    # the freed slot instead. deferred (g2, g3) sits just below the window,
    # order preserved. Unscanned tail (s3) is appended last.
    assert [r.chunk_id for r in out] == [
        "s0",
        "g0",
        "g1",
        "s1",
        "s2",
        "g2",
        "g3",
        "s3",
    ]


def test_graph_hop_window_cap_degenerate_all_graph_no_backfill_source():
    """When there's nothing but graph_hop to backfill with, deferred flows
    straight back into the same positions it vacated -- the cap changes
    nothing about the effective window content, only confirming it never
    drops or reorders items when there's no non-graph candidate to promote
    in its place."""
    candidates = [
        SearchResult(chunk_id=f"g{i}", score=0.0, metadata={}, source="graph_hop")
        for i in range(40)
    ]

    out = RerankingEngine._apply_graph_hop_window_cap(
        candidates, top_k_candidates=30, cap=2
    )

    assert [r.chunk_id for r in out] == [c.chunk_id for c in candidates]


def test_graph_hop_window_cap_ego_tail_call_site_unaffected():
    """rerank_by_query's graph_hop_window_cap defaults to 0 -- calls that
    don't pass it explicitly (the ego-graph/parent-expansion tail in
    HybridSearcher) stay on the plain score sort regardless of what
    config.reranker.graph_hop_window_cap holds, because the cap is a
    call-scoped argument, not something read off config internally."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=3)
    candidates = [
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g1", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g2", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="s0", score=-0.1, metadata={}, source="multi_hop"),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q", candidates, k=4, config=cfg
        )  # no window kwarg -- default policy is tail()

    assert [r.chunk_id for r in out] == ["g0", "g1", "g2", "s0"]


def test_graph_hop_window_cap_applied_before_hop1_reserve():
    """graph_hop_window_cap runs after _order_merged_pool and before
    hop1_reserved_slots' eviction -- capping graph_hop's window occupancy
    can keep a candidate the blind tail-eviction reserve would otherwise
    drop entirely (finding E), by never letting it sit in the pre-reserve
    window in the first place."""
    engine = RerankingEngine(embedder=Mock(), metadata_store=Mock())
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=3, hop1_reserved_slots=1)
    candidates = [
        SearchResult(chunk_id="s0", score=0.9, metadata={}, source="multi_hop"),
        SearchResult(chunk_id="g0", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(chunk_id="g1", score=0.0, metadata={}, source="graph_hop"),
        SearchResult(
            chunk_id="hop1_a", score=-0.5, metadata={"hop1_rank": 1}, source="unknown"
        ),
    ]

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        without_cap = engine.rerank_by_query(
            "q",
            candidates,
            k=4,
            config=cfg,
            window=RerankWindowPolicy(hop1_reserved_slots=1),
        )
        with_cap = engine.rerank_by_query(
            "q",
            candidates,
            k=4,
            config=cfg,
            window=RerankWindowPolicy(hop1_reserved_slots=1, graph_hop_window_cap=1),
        )

    # Without the cap: window = [s0, g0, g1], hop1_a promotes in via the
    # blind tail eviction -- g1 is dropped entirely, not merely demoted.
    assert [r.chunk_id for r in without_cap] == ["s0", "g0", "hop1_a"]
    # With cap=1: g0 admits, g1 defers and hop1_a backfills the freed slot
    # during the cap pass itself -- the reserve then finds no hop1-tagged
    # tail entry left to promote (early return) and g1 survives in the tail.
    assert [r.chunk_id for r in with_cap] == ["s0", "g0", "hop1_a", "g1"]


# ---------------------------------------------------------------------------
# HybridSearcher: ego cap + parent cap (:902-904, :957-961)
# ---------------------------------------------------------------------------


def _bare_hybrid_searcher():
    """object.__new__ bypass: only the attributes these two methods read."""
    searcher = object.__new__(HybridSearcher)
    searcher._logger = logging.getLogger("test")
    searcher.dense_index = Mock()
    searcher.embedder = Mock()
    return searcher


def test_ego_cap_uses_min_of_max_neighbors_and_3k():
    """max_ego = min(max_neighbors_per_hop * k_hops, original_k * 3) (:902-904)."""
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
    (:957-961); results past that slice never reach dense_index.get_chunk_by_id."""
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


def test_include_parent_content_false_strips_content_from_parent_metadata():
    """include_parent_content=False strips `content` before ResultFactory builds
    the parent SearchResult, but leaves other metadata keys intact."""
    searcher = _bare_hybrid_searcher()
    searcher.dense_index.get_chunk_by_id.return_value = {
        "content": "full parent source",
        "file_path": "foo.py",
    }
    results = [
        SearchResult(chunk_id="r0", score=1.0, metadata={"parent_chunk_id": "parent0"})
    ]
    config = ParentRetrievalConfig(enabled=True, include_parent_content=False)

    combined = searcher._apply_parent_expansion(
        results, config, max_results_to_expand=4
    )

    parent_result = next(r for r in combined if r.chunk_id == "parent0")
    assert "content" not in parent_result.metadata
    assert parent_result.metadata["file_path"] == "foo.py"


def test_include_parent_content_true_keeps_content_in_parent_metadata():
    """include_parent_content=True (default) is unchanged: content stays attached."""
    searcher = _bare_hybrid_searcher()
    searcher.dense_index.get_chunk_by_id.return_value = {
        "content": "full parent source",
        "file_path": "foo.py",
    }
    results = [
        SearchResult(chunk_id="r0", score=1.0, metadata={"parent_chunk_id": "parent0"})
    ]
    config = ParentRetrievalConfig(enabled=True)

    combined = searcher._apply_parent_expansion(
        results, config, max_results_to_expand=4
    )

    parent_result = next(r for r in combined if r.chunk_id == "parent0")
    assert parent_result.metadata["content"] == "full parent source"


def test_parent_expansion_stamps_zero_score_and_unscored_source():
    """Parent chunks always get score=0.0 and source='parent_expansion' (:982-983),
    and SearchResult.is_unscored reads that source as fabricated, not ranked (D9)."""
    searcher = _bare_hybrid_searcher()
    searcher.dense_index.get_chunk_by_id.return_value = {"file_path": "foo.py"}
    results = [
        SearchResult(chunk_id="r0", score=0.83, metadata={"parent_chunk_id": "parent0"})
    ]
    config = ParentRetrievalConfig(enabled=True)

    combined = searcher._apply_parent_expansion(
        results, config, max_results_to_expand=4
    )

    parent_result = next(r for r in combined if r.chunk_id == "parent0")
    assert parent_result.score == 0.0
    assert parent_result.source == "parent_expansion"
    assert parent_result.is_unscored is True
    # The original, real-scored result must not be flagged.
    original = next(r for r in combined if r.chunk_id == "r0")
    assert original.is_unscored is False


def test_parent_expansion_appends_parents_after_all_originals():
    """combined_results = results + parent_results (:993) -- parents always
    sort last, after every original result, regardless of relative score."""
    searcher = _bare_hybrid_searcher()
    searcher.dense_index.get_chunk_by_id.return_value = {"file_path": "foo.py"}
    results = [
        SearchResult(chunk_id="r0", score=0.1, metadata={"parent_chunk_id": "parent0"}),
        SearchResult(chunk_id="r1", score=0.9, metadata={}),
    ]
    config = ParentRetrievalConfig(enabled=True)

    combined = searcher._apply_parent_expansion(
        results, config, max_results_to_expand=4
    )

    # Both originals (in original order) precede the appended parent, even
    # though r0's real score (0.1) is far below r1's (0.9).
    assert [r.chunk_id for r in combined] == ["r0", "r1", "parent0"]


def test_parent_expansion_skipped_when_config_disabled():
    """Sanity complement to the enabled-path tests above: config.enabled=False
    is a no-op, matching hybrid_searcher.py:765's gate (`not config.enabled`
    short-circuits before dense_index.get_chunk_by_id is ever called)."""
    searcher = _bare_hybrid_searcher()
    results = [
        SearchResult(chunk_id="r0", score=1.0, metadata={"parent_chunk_id": "parent0"})
    ]
    config = ParentRetrievalConfig(enabled=False)

    combined = searcher._apply_parent_expansion(
        results, config, max_results_to_expand=4
    )

    assert combined == results
    searcher.dense_index.get_chunk_by_id.assert_not_called()


# ---------------------------------------------------------------------------
# GraphScoringStage: output cap (:245, arithmetic at :261; config.py:1231-1236)
# ---------------------------------------------------------------------------


def test_output_cap_is_k_times_max_results_multiplier():
    """max_total = k * max_results_multiplier, default multiplier 8 (config.py:1231-1236)."""
    stage = GraphScoringStage()
    results = [{"chunk_id": f"c{i}"} for i in range(40)]

    capped = stage._cap_results(results, k=4, graph_config=None)

    assert len(capped) == 32


# ---------------------------------------------------------------------------
# Derived output ceiling vs. the advertised k*8 cap
# ---------------------------------------------------------------------------


def test_real_output_ceiling_has_slack_vs_advertised_cap():
    """The real worst-case output size is k multi-hop + ego + k parent, not
    the naive 5k (k + 3k + k) this test used to assert -- the ego term is
    itself a min() (:902-904) that saturates once max_neighbors_per_hop*k_hops
    is smaller than k*3, which it is at the production default k=7. Assert
    the derived ceiling explicitly so a future width change that closes this
    gap (or blows past it) is machine-checked rather than discovered in
    production.
    """
    k = 7
    multi_hop_ceiling = k
    ego_config = EgoGraphConfig()
    ego_ceiling = min(ego_config.max_neighbors_per_hop * ego_config.k_hops, k * 3)
    parent_ceiling = k  # one parent per primary result, worst case
    derived_ceiling = multi_hop_ceiling + ego_ceiling + parent_ceiling

    advertised_cap = k * GraphEnhancedConfig().max_results_multiplier

    assert derived_ceiling == 34  # 7 + min(10*2, 21)=20 + 7, not the naive 5*k=35
    assert derived_ceiling < advertised_cap  # 34 < 56 today — cap has slack
