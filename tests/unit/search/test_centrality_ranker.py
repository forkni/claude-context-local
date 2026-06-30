"""
Unit tests for centrality-based result ranking (SSCG Phase 3).
"""

from unittest.mock import MagicMock

import networkx as nx
import pytest

from search.centrality_ranker import CentralityRanker


@pytest.fixture
def mock_graph_query_engine():
    """Mock GraphQueryEngine with a simple graph."""
    graph = nx.DiGraph()
    graph.add_edge("A", "B")  # A calls B
    graph.add_edge("A", "C")  # A calls C
    graph.add_edge("B", "C")  # B calls C (C is most central)

    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = graph
    engine.compute_centrality = MagicMock(return_value={"A": 0.3, "B": 0.2, "C": 0.5})

    return engine


@pytest.fixture
def sample_results():
    """Sample search results with scores."""
    return [
        {"chunk_id": "A", "score": 0.9, "file": "a.py"},
        {"chunk_id": "B", "score": 0.7, "file": "b.py"},
        {"chunk_id": "C", "score": 0.5, "file": "c.py"},
    ]


def test_annotate_adds_centrality_field(mock_graph_query_engine, sample_results):
    """Test that annotate() adds centrality scores without reordering."""
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)

    result = ranker.annotate(sample_results)

    # Should return same results with added centrality field
    assert len(result) == 3
    assert result[0]["chunk_id"] == "A"
    assert result[1]["chunk_id"] == "B"
    assert result[2]["chunk_id"] == "C"

    # Centrality should be normalized to [0, 1] (max=0.5, so divide by 0.5)
    assert result[0]["centrality"] == pytest.approx(0.6, abs=0.01)  # 0.3 / 0.5
    assert result[1]["centrality"] == pytest.approx(0.4, abs=0.01)  # 0.2 / 0.5
    assert result[2]["centrality"] == pytest.approx(1.0, abs=0.01)  # 0.5 / 0.5


def test_rerank_reorders_by_blended_score(mock_graph_query_engine, sample_results):
    """Test that rerank() reorders results by blended score."""
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)

    result = ranker.rerank(sample_results, alpha=0.5)

    # Should have centrality and blended_score
    assert all("centrality" in r for r in result)
    assert all("blended_score" in r for r in result)

    # With alpha=0.5, blended = 0.5 * semantic + 0.5 * centrality
    # A: 0.5 * 0.9 + 0.5 * 0.6 = 0.75
    # B: 0.5 * 0.7 + 0.5 * 0.4 = 0.55
    # C: 0.5 * 0.5 + 0.5 * 1.0 = 0.75 (tie with A, stable sort keeps A first)

    # Check blended scores
    assert result[0]["blended_score"] == pytest.approx(0.75, abs=0.01)
    assert result[1]["blended_score"] == pytest.approx(0.75, abs=0.01)
    assert result[2]["blended_score"] == pytest.approx(0.55, abs=0.01)

    # Results should be sorted by blended_score descending
    assert result[0]["blended_score"] >= result[1]["blended_score"]
    assert result[1]["blended_score"] >= result[2]["blended_score"]


def test_alpha_zero_preserves_semantic_order(mock_graph_query_engine, sample_results):
    """Regression test: alpha=0.0 should preserve semantic order (100% semantic)."""
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)

    result = ranker.rerank(sample_results, alpha=0.0)

    # With alpha=0.0, blended = 1.0 * semantic + 0.0 * centrality
    # Should preserve original semantic order: A (0.9), B (0.7), C (0.5)
    assert result[0]["chunk_id"] == "A"
    assert result[1]["chunk_id"] == "B"
    assert result[2]["chunk_id"] == "C"

    # Blended scores should equal semantic scores
    assert result[0]["blended_score"] == pytest.approx(0.9, abs=0.01)
    assert result[1]["blended_score"] == pytest.approx(0.7, abs=0.01)
    assert result[2]["blended_score"] == pytest.approx(0.5, abs=0.01)


def test_rerank_missing_centrality_kills_neg_default_mutant(mock_graph_query_engine):
    """Result without a 'centrality' key must blend as 0.0, not -1.0.

    Kills L196 NumberReplacer 0.0→-1.0 mutant in rerank():
      With alpha=0.5: blended = 0.5*score + 0.5*0.0 = 0.5*score
      Mutant:         blended = 0.5*score + 0.5*(-1.0) → negative for small scores.
    """
    # chunk_id not in the compute_centrality return → centrality missing after annotate
    mock_graph_query_engine.compute_centrality.return_value = {}
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)
    results = [{"chunk_id": "X", "score": 0.6}]

    reranked = ranker.rerank(results, alpha=0.5)

    # Expected: 0.5*0.6 + 0.5*0.0 = 0.30
    # Mutant:   0.5*0.6 + 0.5*(-1.0) = -0.20  → negative
    assert reranked[0]["blended_score"] == pytest.approx(0.30, abs=0.001)


def test_rerank_sort_missing_blended_default_kills_one_mutant(mock_graph_query_engine):
    """Result without 'blended_score' must sort last, not first.

    Kills L224 NumberReplacer 0.0→1.0 in the sort key default:
      default 0.0 → no-blended sinks to bottom
      default 1.0 → no-blended floats to top (wrong)
    """
    mock_graph_query_engine.compute_centrality.return_value = {"A": 1.0}
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)
    # "no_blend" has no "score" → semantic=0.0, centrality=0.0 → blended=0.0
    # "A" has score=0.9, centrality=1.0 (normalized) → blended=0.5*0.9+0.5*1.0=0.95
    results2 = [
        {"chunk_id": "no_blend"},
        {"chunk_id": "A", "score": 0.9},
    ]
    reranked2 = ranker.rerank(results2, alpha=0.5)
    assert reranked2[0]["chunk_id"] == "A"  # A must rank first (0.95 > 0.0)


def test_empty_graph_returns_unchanged(sample_results):
    """Test that empty graph returns results with 0.0 centrality."""
    # Empty graph
    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = nx.DiGraph()
    engine.compute_centrality = MagicMock(return_value={})

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    result = ranker.annotate(sample_results)

    # Should add centrality=0.0 for all results
    assert all(r.get("centrality") == 0.0 for r in result)


def test_cache_invalidation_on_graph_change(mock_graph_query_engine, sample_results):
    """Test that cache invalidates when graph node or edge count changes."""
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)

    # First call populates cache
    ranker.annotate(sample_results)
    assert ranker._cache_key == (3, 3)  # (node_count, edge_count)
    assert len(ranker._cache) > 0
    call_count_1 = mock_graph_query_engine.compute_centrality.call_count

    # Second call uses cache (no new compute)
    ranker.annotate(sample_results)
    call_count_2 = mock_graph_query_engine.compute_centrality.call_count
    assert call_count_2 == call_count_1  # No additional call

    # Modify graph (add node) to change node count
    mock_graph_query_engine.storage.graph.add_node("D")

    # Third call should invalidate cache and recompute
    ranker.annotate(sample_results)
    call_count_3 = mock_graph_query_engine.compute_centrality.call_count
    assert call_count_3 == call_count_1 + 1  # One additional call
    assert ranker._cache_key == (4, 3)  # Node count increased


def test_convergence_failure_returns_empty_scores():
    """Test that PageRank convergence failure returns empty scores."""
    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = nx.DiGraph()
    engine.compute_centrality = MagicMock(
        side_effect=nx.PowerIterationFailedConvergence(3)
    )

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    scores = ranker.get_centrality_scores()

    assert scores == {}


def test_generic_exception_returns_empty_scores():
    """Test that generic exceptions return empty scores."""
    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = nx.DiGraph()
    engine.compute_centrality = MagicMock(side_effect=RuntimeError("Test error"))

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    scores = ranker.get_centrality_scores()

    assert scores == {}


def test_split_block_type_boost():
    """Test that split_block chunks get 1.1× type boost (same as function/method)."""
    # Create graph with nodes
    graph = nx.DiGraph()
    graph.add_node("A")
    graph.add_node("B")

    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = graph
    engine.compute_centrality = MagicMock(return_value={"A": 0.5, "B": 0.5})

    results = [
        {"chunk_id": "A", "score": 0.8, "kind": "function"},
        {"chunk_id": "B", "score": 0.8, "kind": "split_block"},
    ]

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    reranked = ranker.rerank(results, query="test query")

    # Blended score calculation: 0.7 * semantic + 0.3 * centrality = 0.7 * 0.8 + 0.3 * 1.0 = 0.86
    # Function gets higher boost (1.2×): 0.86 * 1.2 = 1.032
    # Split_block gets standard boost (1.1×): 0.86 * 1.1 = 0.946
    assert reranked[0]["blended_score"] == pytest.approx(1.032, abs=0.02)  # function
    assert reranked[1]["blended_score"] == pytest.approx(0.946, abs=0.02)  # split_block


def test_split_block_entity_query_boost():
    """Test that split_block gets 1.1× boost for entity queries too."""
    # Create graph with node
    graph = nx.DiGraph()
    graph.add_node("A")

    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = graph
    engine.compute_centrality = MagicMock(return_value={"A": 0.5})

    results = [
        {"chunk_id": "A", "score": 0.8, "kind": "split_block"},
    ]

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    reranked = ranker.rerank(results, query="what class does this")

    # Entity query (contains "class"), split_block should still get 1.1× boost
    # Blended = 0.7 * 0.8 + 0.3 * 1.0 = 0.86
    # With 1.1× boost: 0.86 * 1.1 = 0.946
    assert reranked[0]["blended_score"] == pytest.approx(0.946, abs=0.01)


def test_zero_centrality_synthetic_demotion():
    """Test that module/community chunks with centrality=0 get 0.5× demotion."""
    # Create graph with only function node (module not in graph → centrality=0)
    graph = nx.DiGraph()
    graph.add_node("func.py:10-20:function:foo")

    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = graph
    engine.compute_centrality = MagicMock(
        return_value={"func.py:10-20:function:foo": 0.5}
    )

    results = [
        {"chunk_id": "func.py:10-20:function:foo", "score": 0.8, "kind": "function"},
        {
            "chunk_id": "module.py:0-0:module:module",
            "score": 0.8,
            "kind": "module",
        },  # Not in graph
    ]

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    reranked = ranker.rerank(results, query="test query")

    # Function chunk (in graph, centrality=1.0 normalized):
    # Blended = 0.7 * 0.8 + 0.3 * 1.0 = 0.86
    # Type boost: 0.86 * 1.2 = 1.032
    assert reranked[0]["blended_score"] == pytest.approx(1.032, abs=0.02)

    # Module chunk (not in graph, centrality=0):
    # Blended = 0.7 * 0.8 + 0.3 * 0.0 = 0.56
    # Type demotion: 0.56 * 0.90 = 0.504
    # Zero-centrality demotion: 0.504 * 0.5 = 0.252
    assert reranked[1]["blended_score"] == pytest.approx(0.252, abs=0.02)


def test_zero_centrality_does_not_affect_real_code():
    """Test that zero-centrality demotion only affects module/community, not real code."""
    # Empty graph - all chunks get centrality=0
    graph = nx.DiGraph()

    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = graph
    engine.compute_centrality = MagicMock(return_value={})

    results = [
        {"chunk_id": "func.py:10-20:function:foo", "score": 0.8, "kind": "function"},
        {"chunk_id": "cls.py:10-50:class:Bar", "score": 0.8, "kind": "class"},
        {
            "chunk_id": "module.py:0-0:module:module",
            "score": 0.8,
            "kind": "module",
        },
    ]

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    reranked = ranker.rerank(results, query="test query")

    # Function and class chunks: centrality=0 but NO zero-centrality demotion
    # Blended = 0.7 * 0.8 + 0.3 * 0.0 = 0.56
    # Function type boost: 0.56 * 1.2 = 0.672
    # Class type boost: 0.56 * 1.35 = 0.756
    assert reranked[0]["blended_score"] == pytest.approx(0.756, abs=0.02)  # class
    assert reranked[1]["blended_score"] == pytest.approx(0.672, abs=0.02)  # function

    # Module chunk: centrality=0 AND gets zero-centrality demotion
    # Blended = 0.56
    # Type demotion: 0.56 * 0.90 = 0.504
    # Zero-centrality demotion: 0.504 * 0.5 = 0.252
    assert reranked[2]["blended_score"] == pytest.approx(0.252, abs=0.02)  # module


def test_zero_score_centrality_gives_zero_not_error(mock_graph_query_engine):
    """compute_centrality returning all-zero scores yields centrality=0.0, no ZeroDivisionError.

    Kills Gt_Eq/Gt_LtE/Gt_GtE/Gt_Lt/NumberReplacer at 'if max_score > 0' (genuine gap:
    mutants either ZeroDivide or skip normalization) and occ=16/17 NumberReplacer at
    the else-branch 0.0 default.
    """
    mock_graph_query_engine.compute_centrality.return_value = {"A": 0.0, "B": 0.0}
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)
    results = [{"chunk_id": "A", "score": 0.5}, {"chunk_id": "B", "score": 0.3}]
    reranked = ranker.rerank(results, alpha=0.5)
    # blend = 0.5*score + 0.5*0.0; A (0.25) > B (0.15)
    assert reranked[0]["blended_score"] == pytest.approx(0.25, abs=0.001)
    assert reranked[0]["centrality"] == pytest.approx(0.0, abs=0.001)


def test_score_default_kills_semantic_score_mutant(mock_graph_query_engine):
    """Result missing 'score' key uses 0.0 default, not 1.0.

    Kills NumberReplacer occ=22,23 at result.get('score', 0.0): with 1.0 default,
    noscore blended=0.5 beats scored blended=0.15, inverting rank order.
    """
    mock_graph_query_engine.compute_centrality.return_value = {}
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.3)
    results = [
        {"chunk_id": "noscore"},
        {"chunk_id": "scored", "score": 0.3},
    ]
    reranked = ranker.rerank(results, alpha=0.5)
    # noscore: blend=0 (orig) or 0.5 (mutant); scored: blend=0.15 both
    assert reranked[0]["chunk_id"] == "scored"


def test_empty_name_falls_back_to_chunk_id_name_kills_or_mutant(
    mock_graph_query_engine,
):
    """name='' falls back to _extract_name_impl(chunk_id) via 'or'.

    Kills ReplaceOrWithAnd: with 'and', empty name gives '' so name-match boost is skipped.
    """
    mock_graph_query_engine.compute_centrality.return_value = {
        "search/foo.py:1-10:function:cache": 0.5
    }
    ranker = CentralityRanker(mock_graph_query_engine, method="pagerank", alpha=0.0)
    results = [
        {"chunk_id": "search/foo.py:1-10:function:cache", "score": 0.5, "name": ""},
    ]
    reranked = ranker.rerank(results, alpha=0.0, query="cache invalidation logic")
    # name="" → fallback "cache"; overlap 1/1=1.0 → tier-1 ×1.3; core_dir ×1.1
    # 0.5 * 1.0(type) * 1.1(core) * 1.3(name) = 0.715
    assert reranked[0]["blended_score"] == pytest.approx(0.715, abs=0.005)


# ---------------------------------------------------------------------------
# Direct unit tests for the extracted scoring policy helpers
# ---------------------------------------------------------------------------


class TestApplySizeNormalization:
    """Tests for CentralityRanker._apply_size_normalization."""

    def _make_ranker(self, target_lines=200, alpha=0.1):
        from unittest.mock import Mock

        from search.config import GraphEnhancedConfig

        engine = Mock()
        config = GraphEnhancedConfig(
            enable_size_normalization=True,
            size_norm_target_lines=target_lines,
            size_norm_alpha=alpha,
        )
        return CentralityRanker(engine, config=config)

    def test_penalizes_oversized_chunk(self):
        ranker = self._make_ranker(target_lines=50, alpha=0.1)
        # chunk_id line range 1-200 → 200 lines > 50
        result = {"chunk_id": "file.py:1-200:function:big", "blended_score": 1.0}
        ranker._apply_size_normalization(result)
        assert result["blended_score"] < 1.0

    def test_skips_small_chunk(self):
        ranker = self._make_ranker(target_lines=200, alpha=0.1)
        result = {"chunk_id": "file.py:1-10:function:small", "blended_score": 0.8}
        ranker._apply_size_normalization(result)
        assert result["blended_score"] == 0.8  # unchanged

    def test_exact_factor_kills_div_and_mul_mutants(self):
        """Pin exact normalized score to kill operator-replacement mutants.

        Kills L243 Div_Sub, L245 Add_Div, L246 Mul_*, L248 NumberReplacer(precision).
        target=50, alpha=0.1, chunk_lines=200:
          ratio = 200/50 = 4
          size_factor = 1.0 / (1.0 + 0.1 * log(4)) ≈ 1.0 / 1.1386 ≈ 0.8782
          blended = round(1.0 * 0.8782, 4) ≈ 0.8782
        Wrong operators produce wildly different values (negative, >1, or wrong sign).
        """
        import math

        ranker = self._make_ranker(target_lines=50, alpha=0.1)
        result = {"chunk_id": "file.py:1-200:function:big", "blended_score": 1.0}
        ranker._apply_size_normalization(result)

        expected = 1.0 / (1.0 + 0.1 * math.log(200 / 50))
        assert result["blended_score"] == pytest.approx(expected, abs=0.0002)

    def test_floor_div_kills_div_floordiv_mutant(self):
        """Non-divisible ratio distinguishes / from // in log(chunk/target).

        Kills Div_FloorDiv: 75/50=1.5 → log(1.5)≈0.405 vs 75//50=1 → log(1)=0.
        FloorDiv mutant sets size_factor=1.0 (no penalty), producing blended=1.0.
        """
        import math

        ranker = self._make_ranker(target_lines=50, alpha=0.1)
        result = {"chunk_id": "file.py:1-75:function:big", "blended_score": 1.0}
        ranker._apply_size_normalization(result)

        expected = 1.0 / (1.0 + 0.1 * math.log(75 / 50))
        assert result["blended_score"] == pytest.approx(expected, abs=0.0002)


class TestApplyBm25Boost:
    """Tests for CentralityRanker._apply_bm25_boost."""

    def _make_ranker(self, factor=5.0, cap=0.15):
        from unittest.mock import Mock

        from search.config import GraphEnhancedConfig

        engine = Mock()
        config = GraphEnhancedConfig(
            centrality_bm25_boost=True,
            centrality_boost_factor=factor,
            centrality_boost_cap=cap,
        )
        return CentralityRanker(engine, config=config)

    def test_adds_boost_capped_at_cap(self):
        ranker = self._make_ranker(factor=5.0, cap=0.15)
        result = {"chunk_id": "f.py:1-2:function:x", "blended_score": 0.5}
        # centrality=0.1 → boost = min(0.1*5.0, 0.15) = 0.15 (capped)
        ranker._apply_bm25_boost(result, centrality=0.1)
        assert result["blended_score"] == pytest.approx(0.65, abs=0.001)

    def test_boost_below_cap(self):
        ranker = self._make_ranker(factor=5.0, cap=0.15)
        result = {"chunk_id": "f.py:1-2:function:x", "blended_score": 0.5}
        # centrality=0.02 → boost = min(0.02*5.0, 0.15) = 0.1
        ranker._apply_bm25_boost(result, centrality=0.02)
        assert result["blended_score"] == pytest.approx(0.6, abs=0.001)


class TestApplyTypeBoost:
    """Tests for CentralityRanker._apply_type_boost."""

    def _make_ranker(self):
        from unittest.mock import Mock

        engine = Mock()
        return CentralityRanker(engine)

    def test_entity_query_boosts_class(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_type_boost(result, "class", "find class definition")
        assert result["blended_score"] == pytest.approx(1.35, abs=0.001)

    def test_code_query_boosts_function(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_type_boost(result, "function", "authentication logic")
        assert result["blended_score"] == pytest.approx(1.2, abs=0.001)

    def test_entity_query_demotes_module(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_type_boost(result, "module", "find class")
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)

    def test_decorated_definition_entity_query_boost(self):
        """decorated_definition with entity query → ×1.1.

        Kills NumberReplacer occ=40,41 at 'decorated_definition': 1.1 in entity dict
        (mutation 1.1→0.1 gives 0.1 ≠ 1.1).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_type_boost(
            result, "decorated_definition", "find class constructor"
        )
        assert result["blended_score"] == pytest.approx(1.1, abs=0.001)

    def test_decorated_definition_code_query_neutral(self):
        """decorated_definition with non-entity query → ×1.0 neutral (no change).

        Kills NumberReplacer occ=44,45 at 'decorated_definition': 1.0 in code dict
        (mutation 1.0→0.0 gives 0.0 ≠ 1.0).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_type_boost(result, "decorated_definition", "authentication logic")
        assert result["blended_score"] == pytest.approx(1.0, abs=0.001)


class TestApplySyntheticDemotion:
    """Tests for CentralityRanker._apply_synthetic_demotion."""

    def _make_ranker(self):
        from unittest.mock import Mock

        engine = Mock()
        return CentralityRanker(engine)

    def test_demotes_module_chunk_zero_centrality(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0, "centrality": 0}
        ranker._apply_synthetic_demotion(result, "module", "file.py:0-0:module:file")
        assert result["blended_score"] == pytest.approx(0.5, abs=0.001)

    def test_skips_nonzero_centrality(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0, "centrality": 0.05}
        ranker._apply_synthetic_demotion(result, "module", "file.py:0-0:module:file")
        assert result["blended_score"] == pytest.approx(1.0, abs=0.001)  # unchanged


class TestApplyCoreDirBoost:
    """Tests for CentralityRanker._apply_core_dir_boost."""

    def _make_ranker(self):
        from unittest.mock import Mock

        engine = Mock()
        return CentralityRanker(engine)

    def test_boosts_search_dir(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_core_dir_boost(
            result, "search/hybrid_searcher.py:1-10:function:f"
        )
        assert result["blended_score"] == pytest.approx(1.1, abs=0.001)

    def test_skips_non_core_dir(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_core_dir_boost(result, "scripts/helper.py:1-5:function:f")
        assert result["blended_score"] == pytest.approx(1.0, abs=0.001)  # unchanged


class TestApplyRoleDemotion:
    """Tests for CentralityRanker._apply_role_demotion."""

    def _make_ranker(self):
        from unittest.mock import Mock

        engine = Mock()
        return CentralityRanker(engine)

    def test_demotes_test_file_without_test_query(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "tests/unit/test_foo.py:1-10:function:x", [], "search logic"
        )
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)

    def test_boosts_test_file_with_test_query(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "tests/unit/test_foo.py:1-10:function:x", [], "test coverage"
        )
        assert result["blended_score"] == pytest.approx(1.15, abs=0.001)

    def test_role_tag_takes_precedence_over_path(self):
        """indexed role:test tag should be used even for non-test path."""
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "src/feature.py:1-5:function:x", ["role:test"], "search logic"
        )
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)

    def test_doc_without_intent_exact_kills_factor_mutants(self):
        """Doc role without doc intent → ×0.80 (kills L376/L378 NumberReplacer mutants).

        Also kills L375 ReplaceUnaryOperator_Delete_Not (inverted condition would
        apply ×0.80 WHEN query HAS doc intent, not when it lacks it).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "docs/guide.md:1-50:module:guide", [], "search logic"
        )
        assert result["blended_score"] == pytest.approx(0.80, abs=0.001)

    def test_doc_with_intent_not_demoted_kills_delete_not_mutant(self):
        """Doc role WITH doc intent → unchanged score.

        Kills L375 ReplaceUnaryOperator_Delete_Not: without 'not',
        the condition triggers demotion when intent IS present (wrong).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "docs/guide.md:1-50:module:guide", [], "documentation guide"
        )
        assert result["blended_score"] == pytest.approx(1.0, abs=0.001)

    def test_config_without_intent_exact_kills_factor_mutants(self):
        """Config role without config intent → ×0.88 (kills L378 NumberReplacer mutants)."""
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "config.py:1-20:function:load", [], "search logic"
        )
        assert result["blended_score"] == pytest.approx(0.88, abs=0.001)

    def test_nonstring_tag_kills_isinstance_or_mutant(self):
        """Non-string tag is skipped; subsequent string role tag still applies.

        Kills ReplaceAndWithOr: isinstance(42, str) or 42.startswith('role:') raises
        AttributeError, crashing the test instead of skipping the non-string element.
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_role_demotion(
            result, "src/feature.py:1-5:function:x", [42, "role:test"], "search logic"
        )
        # Non-string 42 skipped; "role:test" → test role, no test intent → ×0.85
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)


class TestApplyNameMatchBoost:
    """Tests for CentralityRanker._apply_name_match_boost."""

    def _make_ranker(self):
        from unittest.mock import Mock

        engine = Mock()
        return CentralityRanker(engine)

    def test_high_overlap_applies_1_3_boost(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        # name="authenticate_user", query="authenticate user" → overlap≥0.8
        ranker._apply_name_match_boost(
            result, "authenticate_user", "authenticate user", "authenticate user"
        )
        assert result["blended_score"] == pytest.approx(1.3, abs=0.001)

    def test_lifecycle_demotion_init_without_intent(self):
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        ranker._apply_name_match_boost(
            result, "__init__", "authentication logic", "authentication logic"
        )
        # lifecycle demotion ×0.85 (no init/enter/exit in query)
        # Exact value kills Mul_Sub mutant (1.0 - 0.85 = 0.15 ≠ 0.85)
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)

    def test_dotted_name_lifecycle_kills_index_and_inversion_mutants(self):
        """Dotted name — terminal component extracted via [-1] must be used.

        Kills:
          L389 NumberReplacer [-1]→[-2]: 'MyClass.__init__'[-2]='MyClass' → no demotion → 1.0
          L389 AddNot (invert dot-check): uses whole string 'MyClass.__init__' → no demotion → 1.0
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        # terminal = "__init__" (via split(".")[-1]) → lifecycle demotion × 0.85
        ranker._apply_name_match_boost(
            result, "MyClass.__init__", "some logic", "some logic"
        )
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)

    def test_overlap_fraction_tier2_kills_div_mutants(self):
        """3/5 name-token overlap (tier 2: ×1.2) kills all / replacement operators.

        Kills L402 mutations: Div→LShift,BitAnd,FloorDiv,Pow,Mul.
        All give wrong overlap values (>0.8→tier1=1.3x, or 0→no boost) instead of 0.6→1.2x.
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        # name tokens: {handle, cache, miss, for, request} = 5 tokens (all ≥3 chars)
        # query tokens: {handle, cache, miss} = 3 tokens
        # intersection = {handle, cache, miss} = 3 → overlap = 3/5 = 0.6 → tier 2 → ×1.2
        ranker._apply_name_match_boost(
            result,
            "handle_cache_miss_for_request",
            "handle cache miss",
            "handle cache miss",
        )
        assert result["blended_score"] == pytest.approx(1.2, abs=0.001)

    def test_three_part_dotted_name_kills_index_shift_mutants(self):
        """3-element dotted name: split('.')[-1] extracts '__init__', not 'A'.

        Kills USub_UAdd ([-1]→[+1]): 'outer.A.__init__'[1]='A' → no lifecycle demotion
        → result stays 1.0 instead of 0.85.  2-element test_dotted_name_lifecycle only
        proves [-2] fails; this proves [+1] also fails (they coincide for 2 elements).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        # split(".")[-1] = "__init__"; split(".")[1] = "A" (not a lifecycle name)
        ranker._apply_name_match_boost(
            result, "outer.A.__init__", "some logic", "some logic"
        )
        assert result["blended_score"] == pytest.approx(0.85, abs=0.001)

    def test_exact_half_overlap_kills_gte_and_minlen_mutants(self):
        """overlap=0.5 exactly at tier-2 boundary; 2-char tokens kept with min_len=2.

        Kills GtE→Gt: >=0.5 → ×1.2 (tier 2), >0.5 → ×1.1 (tier 3).
        Also kills min_len=2→3: 'go','to' (2-char) are filtered out → empty name_tokens
        → no boost (result stays 1.0 ≠ 1.2).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        # name "go_to" → tokens {"go","to"} (both len=2, kept with min_len=2)
        # query "go cache" → tokens {"go","cache"}; intersection {"go"}; overlap=1/2=0.5
        # 0.5 >= 0.5 → tier 2 → ×1.2
        ranker._apply_name_match_boost(result, "go_to", "go cache", "go cache")
        assert result["blended_score"] == pytest.approx(1.2, abs=0.001)

    def test_acronym_name_kills_split_acronyms_mutant(self):
        """All-caps acronym prefix in name splits correctly with split_acronyms=True.

        Kills ReplaceTrueWithFalse at split_acronyms=True in _tokenize_for_matching:
        without splitting, 'XMLNode' → {'xmlnode'} (1 token, no query match → no boost).
        """
        ranker = self._make_ranker()
        result = {"blended_score": 1.0}
        # "XMLNode" with split_acronyms=True → {"xml","node"}; query {"xml","node","data"}
        # overlap=2/2=1.0 → tier 1 → ×1.3
        ranker._apply_name_match_boost(
            result, "XMLNode", "xml node data", "xml node data"
        )
        assert result["blended_score"] == pytest.approx(1.3, abs=0.001)
