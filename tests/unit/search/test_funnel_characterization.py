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
        logger=logging.getLogger("test"),
    )


def _cfg(top_k_candidates=30, single_pass=False, bm25_reserved_slots=0):
    cfg = Mock()
    cfg.reranker.top_k_candidates = top_k_candidates
    cfg.reranker.single_pass = single_pass
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
    engine = RerankingEngine()
    engine.neural_reranker = Mock()
    engine.neural_reranker.rerank.return_value = []
    cfg = _cfg(top_k_candidates=30)
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=1.0, metadata={}) for i in range(50)
    ]

    engine._run_rerank("q", candidates, k=4, log_prefix="[TEST]", config=cfg)

    passed_candidates = engine.neural_reranker.rerank.call_args[0][1]
    assert len(passed_candidates) == 30


def test_tail_window_ignores_hop1_rank_tags():
    """The tail pass (ego-graph/parent-expansion in HybridSearcher, no window=
    kwarg) is plain score order and window membership: a low-scored candidate
    tagged hop1_rank=1 is cut like any other, byte-identical to before ADR-0079
    (only the Pass-2 merged call interleaves)."""
    engine = RerankingEngine()
    engine._ensure_reranker = Mock(return_value=False)  # skip neural rerank branch
    cfg = _cfg(top_k_candidates=5)
    candidates = [
        SearchResult(chunk_id=f"c{i}", score=float(9 - i), metadata={})
        for i in range(10)
    ]
    candidates[9].metadata["hop1_rank"] = 1  # lowest score, best hop1 rank

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query("q", candidates, k=5, config=cfg)

    assert [r.chunk_id for r in out] == ["c0", "c1", "c2", "c3", "c4"]


def test_dedupe_split_blocks_can_return_fewer_than_k():
    """dedupe_split_blocks=True collapses split_block siblings *before* the
    [:k] truncation (:548-551), so the funnel can legitimately return fewer
    than k rows even though k results were requested."""
    engine = RerankingEngine()
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
# Merged-pool window membership (ADR-0079): interleave, not a mixed-scale sort
#
# The merged multi-hop pool carries three incomparable score scales (hop-1 jina
# relevance, semantic-expansion raw FAISS cosine, graph-expansion literal 0.0).
# Sorting them together pushed every hop-1 survivor, rank 1 included, past the
# window cut. The interleave seats hop-1 survivors and the frontier alternately.
# See docs/adr/0079-gar-style-rerank-window-membership.md.
# ---------------------------------------------------------------------------


def _mixed_scale_pool():
    """Hop-1 rank 1 has the LOWEST raw score; 12 semantic expansions score 0.9."""
    hop1 = SearchResult(
        chunk_id="hop1_a",
        score=-0.5,
        metadata={"hop1_rank": 1},
        source="multi_hop",
    )
    frontier = [
        SearchResult(
            chunk_id=f"s{i}",
            score=0.9,
            metadata={"anchor_rank": 1 + i % 3},
            source="multi_hop",
        )
        for i in range(12)
    ]
    return [*frontier, hop1]


def test_plain_score_order_cuts_hop1_rank1_from_a_mixed_scale_window():
    """Characterization of the pre-ADR-0079 defect, kept as the contrast: under
    plain score order the lowest-scored hop-1 rank 1 never reaches the window."""
    engine = RerankingEngine()
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=5)

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q", _mixed_scale_pool(), k=5, config=cfg, window=RerankWindowPolicy.tail()
        )

    assert "hop1_a" not in {r.chunk_id for r in out}


def test_merged_pool_window_always_contains_hop1_rank1():
    """The same pool under the merged-pool policy: hop-1 rank 1 leads the
    window, whatever its raw score."""
    engine = RerankingEngine()
    engine._ensure_reranker = Mock(return_value=False)
    cfg = _cfg(top_k_candidates=5)

    with patch("search.reranking_engine.get_search_config", return_value=cfg):
        out = engine.rerank_by_query(
            "q",
            _mixed_scale_pool(),
            k=5,
            config=cfg,
            window=RerankWindowPolicy.merged_pool(),
        )

    assert out[0].chunk_id == "hop1_a"
    assert len(out) == 5


def test_order_merged_pool_without_interleave_is_plain_sorted_by_score():
    """interleave=False (tail pass, single_pass) sorts purely by score."""
    pool = [
        SearchResult(chunk_id="a", score=0.0, metadata={}),
        SearchResult(chunk_id="b", score=-0.3, metadata={}),
        SearchResult(chunk_id="c", score=0.7, metadata={}),
    ]

    ordered = RerankingEngine._order_merged_pool(pool, False)

    assert [r.chunk_id for r in ordered] == ["c", "a", "b"]


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
