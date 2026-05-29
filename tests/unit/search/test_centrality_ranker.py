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
        assert result["blended_score"] < 1.0
