"""Fix #4: search.hybrid_searcher.drop_nonpositive_ego_results.

Bounds ego-graph output to the cross-encoder's own non-negative judgment
instead of a relative-ratio floor (rejected design -- see the plan doc: a
ratio inverts when best_score <= 0 and needs a per-query-unstable magic
constant). Only source == "ego_graph" results with reranker_score <= 0 are
dropped; anchors and multi_hop/graph_hop results are never filtered, and
results with no reranker_score yet (rerank never ran) are left alone.
"""

from search.hybrid_searcher import drop_nonpositive_ego_results
from search.reranker import SearchResult


def _result(chunk_id: str, source: str, reranker_score: float | None = None):
    metadata = {} if reranker_score is None else {"reranker_score": reranker_score}
    return SearchResult(chunk_id=chunk_id, score=0.5, metadata=metadata, source=source)


class TestDropNonpositiveEgoResults:
    def test_empty_list_is_a_noop(self):
        assert drop_nonpositive_ego_results([]) == []

    def test_no_ego_graph_sources_is_byte_identical(self):
        results = [
            _result("a.py:1-5:function:a", "hybrid", 0.4),
            _result("b.py:1-5:function:b", "multi_hop", -0.9),
            _result("c.py:1-5:function:c", "graph_hop", 0.0),
        ]
        assert drop_nonpositive_ego_results(results) == results

    def test_drops_ego_graph_with_negative_reranker_score(self):
        r = _result("a.py:1-5:function:a", "ego_graph", -0.1207)
        assert drop_nonpositive_ego_results([r]) == []

    def test_drops_ego_graph_with_exact_zero_reranker_score(self):
        """<= 0, not < 0: a result can land at exactly 0.0."""
        r = _result("a.py:1-5:function:a", "ego_graph", 0.0)
        assert drop_nonpositive_ego_results([r]) == []

    def test_keeps_ego_graph_with_positive_reranker_score(self):
        r = _result("a.py:1-5:function:a", "ego_graph", 0.02)
        assert drop_nonpositive_ego_results([r]) == [r]

    def test_keeps_ego_graph_with_missing_reranker_score(self):
        """Rerank never ran on this result -- this is a cut on the
        cross-encoder's own judgment, not a guess, so it's left alone."""
        r = _result("a.py:1-5:function:a", "ego_graph", None)
        assert drop_nonpositive_ego_results([r]) == [r]

    def test_never_drops_a_negatively_scored_non_ego_result(self):
        """multi_hop/graph_hop/hybrid results are never filtered, regardless
        of their own reranker_score."""
        r = _result("a.py:1-5:function:a", "multi_hop", -0.9)
        assert drop_nonpositive_ego_results([r]) == [r]

    def test_mixed_batch_drops_only_nonpositive_ego_entries(self):
        keep_hybrid = _result("a.py:1-5:function:a", "hybrid", 0.4)
        keep_multi_hop_negative = _result("b.py:1-5:function:b", "multi_hop", -0.9)
        keep_ego_positive = _result("c.py:1-5:function:c", "ego_graph", 0.02)
        keep_ego_no_score = _result("d.py:1-5:function:d", "ego_graph", None)
        drop_ego_negative = _result("e.py:1-5:function:e", "ego_graph", -0.1464)
        drop_ego_zero = _result("f.py:1-5:function:f", "ego_graph", 0.0)

        results = [
            keep_hybrid,
            keep_multi_hop_negative,
            keep_ego_positive,
            keep_ego_no_score,
            drop_ego_negative,
            drop_ego_zero,
        ]
        assert drop_nonpositive_ego_results(results) == [
            keep_hybrid,
            keep_multi_hop_negative,
            keep_ego_positive,
            keep_ego_no_score,
        ]

    def test_preserves_relative_order_of_survivors(self):
        results = [
            _result("a.py:1-5:function:a", "ego_graph", 0.3),
            _result("b.py:1-5:function:b", "ego_graph", -0.1),
            _result("c.py:1-5:function:c", "ego_graph", 0.1),
        ]
        assert [r.chunk_id for r in drop_nonpositive_ego_results(results)] == [
            "a.py:1-5:function:a",
            "c.py:1-5:function:c",
        ]
