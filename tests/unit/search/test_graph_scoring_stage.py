"""Unit tests for GraphScoringStage (Blocks F and G of the hybrid search scoring pipeline)."""

from __future__ import annotations

from unittest.mock import Mock, patch

from search.config import SearchConfig
from search.graph_scoring_stage import GraphScoringStage
from search.intent_classifier import IntentDecision, QueryIntent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_formatted(chunk_id="a.py:1-5:function:foo", kind="function", score=0.9):
    return {"chunk_id": chunk_id, "kind": kind, "blended_score": score}


def _graph_config_on(reranking: bool = False):
    """Return a GraphEnhancedConfig with centrality_annotation=True."""
    sc = SearchConfig()
    sc.graph_enhanced.centrality_annotation = True
    sc.graph_enhanced.centrality_reranking = reranking
    sc.graph_enhanced.centrality_method = "pagerank"
    sc.graph_enhanced.centrality_alpha = 0.3
    return sc.graph_enhanced


def _graph_config_off():
    """Return a GraphEnhancedConfig with centrality_annotation=False."""
    sc = SearchConfig()
    sc.graph_enhanced.centrality_annotation = False
    return sc.graph_enhanced


def _mock_subgraph_extractor(nodes=None, subgraph_dict=None):
    """Return a patch context for SubgraphExtractor that yields empty nodes by default."""
    fake_subgraph = Mock()
    fake_subgraph.nodes = nodes if nodes is not None else []
    fake_subgraph.edges = []
    fake_subgraph.to_dict.return_value = subgraph_dict or {}
    mock_se = patch("search.subgraph_extractor.SubgraphExtractor")
    return mock_se, fake_subgraph


# ---------------------------------------------------------------------------
# Block F — centrality scoring
# ---------------------------------------------------------------------------


class TestApplyCentrality:
    """Block F (centrality scoring) inside GraphScoringStage.run()."""

    def test_guard_off_returns_results_unchanged(self):
        stage = GraphScoringStage()
        results = [_make_formatted()]
        out_results, subgraph_data = stage.run(
            "q", None, 4, list(results), None, None, _graph_config_off()
        )
        assert out_results == results
        assert subgraph_data is None

    def test_centrality_reranking_calls_rerank(self):
        stage = GraphScoringStage()
        graph_config = _graph_config_on(reranking=True)
        im = Mock()
        im.graph_storage = Mock()

        fake_scores = {"a.py:1-5:function:foo": 0.9}
        mock_ranker = Mock()
        mock_ranker.get_centrality_scores.return_value = fake_scores
        mock_ranker.rerank.return_value = [_make_formatted()]

        with (
            patch(
                "search.centrality_ranker.CentralityRanker", return_value=mock_ranker
            ),
            patch("graph.graph_queries.GraphQueryEngine"),
            patch("search.subgraph_extractor.SubgraphExtractor") as mock_se,
        ):
            mock_se.return_value.extract_subgraph.return_value = Mock(nodes=[])
            out_results, _ = stage.run(
                "q", None, 4, [_make_formatted()], im, None, graph_config
            )

        mock_ranker.rerank.assert_called_once()
        mock_ranker.annotate.assert_not_called()

    def test_centrality_annotation_calls_annotate_not_rerank(self):
        stage = GraphScoringStage()
        graph_config = _graph_config_on(reranking=False)
        im = Mock()
        im.graph_storage = Mock()

        mock_ranker = Mock()
        mock_ranker.get_centrality_scores.return_value = {}
        mock_ranker.annotate.return_value = [_make_formatted()]

        with (
            patch(
                "search.centrality_ranker.CentralityRanker", return_value=mock_ranker
            ),
            patch("graph.graph_queries.GraphQueryEngine"),
            patch("search.subgraph_extractor.SubgraphExtractor") as mock_se,
        ):
            mock_se.return_value.extract_subgraph.return_value = Mock(nodes=[])
            out_results, _ = stage.run(
                "q", None, 4, [_make_formatted()], im, None, graph_config
            )

        mock_ranker.annotate.assert_called_once()
        mock_ranker.rerank.assert_not_called()

    def test_intent_pushes_synthetic_chunks_last(self):
        """Non-GLOBAL intent: module/community chunks moved after real code chunks."""
        stage = GraphScoringStage()
        intent = IntentDecision(
            intent=QueryIntent.LOCAL,
            confidence=0.9,
            reason="test LOCAL intent",
            scores={},
            suggested_params={},
        )
        graph_config = _graph_config_on(reranking=False)
        im = Mock()
        im.graph_storage = Mock()

        real_result = {"chunk_id": "a.py:1-5:function:foo", "kind": "function"}
        synth_result = {"chunk_id": "a.py:0-0:module:a", "kind": "module"}

        mock_ranker = Mock()
        mock_ranker.get_centrality_scores.return_value = {}
        mock_ranker.annotate.return_value = [synth_result, real_result]  # synth first

        with (
            patch(
                "search.centrality_ranker.CentralityRanker", return_value=mock_ranker
            ),
            patch("graph.graph_queries.GraphQueryEngine"),
            patch("search.subgraph_extractor.SubgraphExtractor") as mock_se,
        ):
            mock_se.return_value.extract_subgraph.return_value = Mock(nodes=[])
            out_results, _ = stage.run(
                "q", intent, 4, [synth_result, real_result], im, None, graph_config
            )

        assert out_results[0]["kind"] == "function"
        assert out_results[1]["kind"] == "module"

    def test_exception_in_centrality_returns_original_results(self):
        """ImportError (or any guarded exception) leaves results unchanged."""
        stage = GraphScoringStage()
        graph_config = _graph_config_on(reranking=False)
        im = Mock()
        im.graph_storage = Mock()

        results = [_make_formatted()]
        with (
            patch(
                "graph.graph_queries.GraphQueryEngine",
                side_effect=ImportError("no module"),
            ),
            patch("search.subgraph_extractor.SubgraphExtractor") as mock_se,
        ):
            mock_se.return_value.extract_subgraph.return_value = Mock(nodes=[])
            out_results, _ = stage.run(
                "q", None, 4, list(results), im, None, graph_config
            )

        assert out_results == results

    def test_centrality_scores_forwarded_to_subgraph_extractor(self):
        """centrality_scores from Block F reach extract_subgraph as a kwarg."""
        stage = GraphScoringStage()
        graph_config = _graph_config_on(reranking=False)
        im = Mock()
        im.graph_storage = Mock()

        fake_scores = {"a.py:1-5:function:foo": 0.7}
        mock_ranker = Mock()
        mock_ranker.get_centrality_scores.return_value = fake_scores
        mock_ranker.annotate.return_value = [_make_formatted()]

        with (
            patch(
                "search.centrality_ranker.CentralityRanker", return_value=mock_ranker
            ),
            patch("graph.graph_queries.GraphQueryEngine"),
            patch("search.subgraph_extractor.SubgraphExtractor") as mock_se,
        ):
            fake_subgraph = Mock()
            fake_subgraph.nodes = []
            mock_se.return_value.extract_subgraph.return_value = fake_subgraph
            stage.run("q", None, 4, [_make_formatted()], im, None, graph_config)

        _, kwargs = mock_se.return_value.extract_subgraph.call_args
        assert kwargs.get("centrality_scores") == fake_scores


# ---------------------------------------------------------------------------
# Block G — SSCG subgraph extraction
# ---------------------------------------------------------------------------


class TestExtractSubgraph:
    """Block G (SSCG subgraph extraction) inside GraphScoringStage.run()."""

    def test_returns_none_subgraph_when_no_index_manager(self):
        stage = GraphScoringStage()
        results, subgraph_data = stage.run("q", None, 4, [], None, None, None)
        assert subgraph_data is None

    def test_returns_none_subgraph_when_graph_storage_is_none(self):
        stage = GraphScoringStage()
        im = Mock()
        im.graph_storage = None
        results, subgraph_data = stage.run("q", None, 4, [], im, None, None)
        assert subgraph_data is None

    def test_returns_subgraph_dict_when_nodes_present(self):
        stage = GraphScoringStage()
        im = Mock()
        im.graph_storage = Mock()
        formatted = [
            {"chunk_id": "a.py:1-5:function:foo"},
            {"chunk_id": "b.py:1-5:function:bar"},
        ]
        fake_subgraph = Mock()
        fake_subgraph.nodes = [Mock()]  # non-empty
        fake_subgraph.edges = []
        fake_subgraph.to_dict.return_value = {"nodes": [{}], "edges": []}
        with patch("search.subgraph_extractor.SubgraphExtractor") as mock_se:
            mock_se.return_value.extract_subgraph.return_value = fake_subgraph
            results, subgraph_data = stage.run("q", None, 4, formatted, im, None, None)
        assert subgraph_data == {"nodes": [{}], "edges": []}
        mock_se.assert_called_once_with(im.graph_storage)

    def test_returns_none_subgraph_when_empty(self):
        stage = GraphScoringStage()
        im = Mock()
        im.graph_storage = Mock()
        fake_subgraph = Mock()
        fake_subgraph.nodes = []
        formatted = [{"chunk_id": "a.py:1-5:function:foo"}]
        with patch("search.subgraph_extractor.SubgraphExtractor") as mock_se:
            mock_se.return_value.extract_subgraph.return_value = fake_subgraph
            results, subgraph_data = stage.run("q", None, 4, formatted, im, None, None)
        assert subgraph_data is None

    def test_exception_returns_none_subgraph(self):
        stage = GraphScoringStage()
        im = Mock()
        im.graph_storage = Mock()
        formatted = [{"chunk_id": "x.py:1-5:function:f"}]
        with patch(
            "search.subgraph_extractor.SubgraphExtractor",
            side_effect=RuntimeError("graph fail"),
        ):
            results, subgraph_data = stage.run("q", None, 4, formatted, im, None, None)
        assert subgraph_data is None


# ---------------------------------------------------------------------------
# Integration — F → cap → G
# ---------------------------------------------------------------------------


class TestGraphScoringStageIntegration:
    """End-to-end tests across Block F, the k*4 cap, and Block G."""

    def test_cap_applied_between_centrality_and_subgraph(self):
        """k*4 cap fires; Block G sees the capped list."""
        stage = GraphScoringStage()
        im = Mock()
        im.graph_storage = None  # skip subgraph
        results = [
            _make_formatted(chunk_id=f"f.py:{i}-{i + 1}:function:fn{i}")
            for i in range(20)
        ]
        out_results, subgraph_data = stage.run("q", None, 4, results, im, None, None)
        assert len(out_results) == 16  # k*4 = 4*4
        assert subgraph_data is None

    def test_subgraph_runs_when_centrality_annotation_off(self):
        """Block G fires independently of the Block F centrality guard."""
        stage = GraphScoringStage()
        im = Mock()
        im.graph_storage = Mock()
        graph_config = _graph_config_off()  # centrality off
        formatted = [{"chunk_id": "a.py:1-5:function:foo"}]
        fake_subgraph = Mock()
        fake_subgraph.nodes = [Mock()]
        fake_subgraph.edges = []
        fake_subgraph.to_dict.return_value = {"nodes": [{}], "edges": []}
        with patch("search.subgraph_extractor.SubgraphExtractor") as mock_se:
            mock_se.return_value.extract_subgraph.return_value = fake_subgraph
            out_results, subgraph_data = stage.run(
                "q", None, 4, formatted, im, None, graph_config
            )
        assert subgraph_data == {"nodes": [{}], "edges": []}
        # centrality_scores was never set — must be None
        _, kwargs = mock_se.return_value.extract_subgraph.call_args
        assert kwargs.get("centrality_scores") is None
