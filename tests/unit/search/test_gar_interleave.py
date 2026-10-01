"""Tests for the merged-pool window interleave and the shared backfill (ADR-0079).

``RerankWindowPolicy.merged_pool()`` decides rerank-window membership by 1:1 alternation between hop-1
survivors (by ``hop1_rank``) and the expansion frontier (by ``anchor_rank``, graph
before semantic inside each anchor) instead of sorting incomparable score scales
together. ``_run_rerank`` backfills: candidates past the listwise window keep their
incoming order and are never dropped.
"""

from unittest.mock import Mock, patch

from search.rerank_window_policy import RerankWindowPolicy
from search.reranker import SearchResult
from search.reranking_engine import RerankingEngine


def _cfg(top_k_candidates: int = 30) -> Mock:
    cfg = Mock()
    cfg.reranker.top_k_candidates = top_k_candidates
    cfg.reranker.dedupe_split_blocks = False
    return cfg


def _hop1(rank: int, score: float = 0.0) -> SearchResult:
    return SearchResult(
        chunk_id=f"h{rank}",
        score=score,
        metadata={"hop1_rank": rank},
        source="multi_hop",
    )


def _graph(name: str, anchor: float | None, score: float = 0.0) -> SearchResult:
    metadata = {} if anchor is None else {"anchor_rank": anchor}
    return SearchResult(
        chunk_id=name, score=score, metadata=metadata, source="graph_hop"
    )


def _semantic(name: str, anchor: float | None, score: float = 0.8) -> SearchResult:
    metadata = {} if anchor is None else {"anchor_rank": anchor}
    return SearchResult(
        chunk_id=name, score=score, metadata=metadata, source="multi_hop"
    )


def _ids(results: list) -> list[str]:
    return [r.chunk_id for r in results]


_GAR = RerankWindowPolicy.merged_pool()


class TestGarInterleaveOrder:
    def test_alternates_hop1_and_frontier_anchor_first(self):
        pool = [
            _semantic("s2", 2),
            _graph("g2", 2),
            _semantic("s1", 1),
            _graph("g1", 1),
            _hop1(3),
            _hop1(1),
            _hop1(2),
        ]
        ordered = RerankingEngine._order_merged_pool(pool, True)
        # Frontier: anchor 1 (graph first), then anchor 2 (graph first).
        assert _ids(ordered) == ["h1", "g1", "h2", "s1", "h3", "g2", "s2"]

    def test_graph_and_semantic_alternate_inside_an_anchor(self):
        pool = [
            _hop1(1),
            _graph("g_a", 1),
            _graph("g_b", 1),
            _semantic("s_a", 1),
        ]
        ordered = RerankingEngine._order_merged_pool(pool, True)
        # Per-anchor frontier: g_a, s_a, g_b.
        assert _ids(ordered) == ["h1", "g_a", "s_a", "g_b"]

    def test_other_side_fills_when_one_runs_out(self):
        pool = [_hop1(1), _hop1(2)] + [_semantic(f"s{i}", 1) for i in range(4)]
        ordered = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(ordered) == ["h1", "s0", "h2", "s1", "s2", "s3"]

        pool = [_hop1(i) for i in range(1, 5)] + [_semantic("s0", 1)]
        ordered = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(ordered) == ["h1", "s0", "h2", "h3", "h4"]

    def test_frontier_without_anchor_sorts_last(self):
        pool = [_hop1(1), _semantic("orphan", None), _semantic("anchored", 9)]
        ordered = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(ordered) == ["h1", "anchored", "orphan"]

    def test_hop1_is_classified_by_metadata_not_source(self):
        # A hop-1 survivor is re-emitted with source "multi_hop", the same as a
        # semantic expansion; only hop1_rank tells them apart. Raw scores must not
        # matter either.
        pool = [_semantic("s1", 1, score=0.99), _hop1(1, score=-0.5)]
        ordered = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(ordered) == ["h1", "s1"]

    def test_is_a_permutation(self):
        pool = (
            [_hop1(i) for i in range(1, 8)]
            + [_graph(f"g{i}", i % 3 + 1) for i in range(6)]
            + [_semantic(f"s{i}", i % 4 + 1) for i in range(9)]
        )
        ordered = RerankingEngine._order_merged_pool(pool, True)
        assert sorted(_ids(ordered)) == sorted(_ids(pool))


class TestGarWindowMembership:
    def test_hop1_rank1_with_lowest_raw_score_stays_in_window(self):
        """Q07-shaped: hop-1 rank 1 carries the lowest (jina) score while 40
        semantic expansions carry cosines of 0.9. A plain score sort pushes it past
        slot 30; the interleave seats it first."""
        engine = RerankingEngine()
        engine._ensure_reranker = Mock(return_value=False)
        cfg = _cfg(top_k_candidates=30)
        pool = [_hop1(1, score=-0.5)] + [
            _semantic(f"s{i}", 1 + i % 10, score=0.9) for i in range(40)
        ]

        with patch("search.reranking_engine.get_search_config", return_value=cfg):
            out = engine.rerank_by_query("q", pool, k=10, config=cfg, window=_GAR)
        assert _ids(out)[0] == "h1"

        engine.neural_reranker = Mock()
        engine.neural_reranker.rerank.side_effect = lambda q, cands, k: list(cands)
        engine._ensure_reranker = Mock(return_value=True)
        with patch("search.reranking_engine.get_search_config", return_value=cfg):
            engine.rerank_by_query("q", pool, k=10, config=cfg, window=_GAR)
        assert "h1" in engine.last_window_ids
        assert len(engine.last_window_ids) == 30

    def test_interleave_is_not_reshaped_after_ordering(self):
        """A pool with 20 hop-1 survivors keeps the interleave byte-for-byte:
        no later step promotes hop-1 ranks 16-20 over the window's tail."""
        engine = RerankingEngine()
        engine._ensure_reranker = Mock(return_value=False)
        cfg = _cfg(top_k_candidates=30)
        pool = (
            [_hop1(i) for i in range(1, 21)]
            + [_graph(f"g{i}", i % 10 + 1) for i in range(10)]
            + [_semantic(f"s{i}", i % 10 + 1) for i in range(15)]
        )

        with patch("search.reranking_engine.get_search_config", return_value=cfg):
            out = engine.rerank_by_query(
                "q", pool, k=len(pool), config=cfg, window=_GAR
            )

        expected = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(out) == _ids(expected)


class TestBackfill:
    @staticmethod
    def _engine_with_reversing_reranker() -> RerankingEngine:
        engine = RerankingEngine()
        engine._ensure_reranker = Mock(return_value=True)
        engine.neural_reranker = Mock()
        # Like JinaRerankerV3: returns the whole scored window, reordered.
        engine.neural_reranker.rerank.side_effect = lambda q, cands, k: list(
            reversed(cands)
        )
        return engine

    def test_candidates_past_the_window_keep_incoming_order(self):
        engine = self._engine_with_reversing_reranker()
        cfg = _cfg(top_k_candidates=30)
        pool = [_hop1(i) for i in range(1, 41)]

        with patch("search.reranking_engine.get_search_config", return_value=cfg):
            out = engine.rerank_by_query("q", pool, k=40, config=cfg, window=_GAR)

        expected = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(out) == [
            *reversed(_ids(expected)[:30]),
            *_ids(expected)[30:],
        ]

    def test_tail_pass_over_a_40_item_pool_returns_all_40(self):
        """Pass-3 shape: the ego tail rerank passes k=len(results). Before
        backfill only the first 30 survived."""
        engine = self._engine_with_reversing_reranker()
        cfg = _cfg(top_k_candidates=30)
        pool = [
            SearchResult(
                chunk_id=f"r{i}", score=1.0 - i / 100, metadata={}, source="unknown"
            )
            for i in range(40)
        ]

        with patch("search.reranking_engine.get_search_config", return_value=cfg):
            out = engine.rerank_by_query(
                "q", pool, k=40, config=cfg, window=RerankWindowPolicy.tail()
            )

        assert sorted(_ids(out)) == sorted(_ids(pool))

    def test_no_op_when_candidates_fit_the_window(self):
        engine = self._engine_with_reversing_reranker()
        cfg = _cfg(top_k_candidates=30)
        pool = [_hop1(i) for i in range(1, 11)]

        with patch("search.reranking_engine.get_search_config", return_value=cfg):
            out = engine.rerank_by_query("q", pool, k=10, config=cfg, window=_GAR)

        expected = RerankingEngine._order_merged_pool(pool, True)
        assert _ids(out) == list(reversed(_ids(expected)))
