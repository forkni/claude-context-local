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
    scores = ranker._get_centrality_scores()

    assert scores == {}


def test_generic_exception_returns_empty_scores():
    """Test that generic exceptions return empty scores."""
    engine = MagicMock()
    engine.storage = MagicMock()
    engine.storage.graph = nx.DiGraph()
    engine.compute_centrality = MagicMock(side_effect=RuntimeError("Test error"))

    ranker = CentralityRanker(engine, method="pagerank", alpha=0.3)
    scores = ranker._get_centrality_scores()

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

    # Both should have the same blended score (semantic 0.8, centrality 1.0 normalized)
    # Blended = 0.7 * 0.8 + 0.3 * 1.0 = 0.86
    # With 1.1× boost: 0.86 * 1.1 = 0.946
    assert reranked[0]["blended_score"] == pytest.approx(0.946, abs=0.01)
    assert reranked[1]["blended_score"] == pytest.approx(0.946, abs=0.01)


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
