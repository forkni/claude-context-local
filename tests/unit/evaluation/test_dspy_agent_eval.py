"""Unit tests for evaluation/dspy_agent_eval.py.

All tests are offline — no network, no MCP server, no subscription.
Tests cover dataset loading, metric correctness on synthetic predictions,
and tool-selection scoring.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import dspy
import pytest

from evaluation.dspy_agent_eval import (
    CodeNavQA,
    _extract_chunk_ids,
    _extract_chunk_ids_from_observations,
    _extract_tools_from_trajectory,
    load_examples,
    mrr_metric,
    recall_at_k_metric,
    tool_selection_metric,
    trajectory_recall_metric,
)


pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GOLDEN_PATH = Path(__file__).parents[3] / "evaluation" / "golden_dataset.json"


@pytest.fixture
def golden_dataset_path() -> Path:
    """Absolute path to the real golden dataset."""
    return _GOLDEN_PATH


def _make_pred(
    chunk_ids: list[str] | None = None,
    trajectory: dict | None = None,
    answer: str = "Found it.",
) -> MagicMock:
    """Build a minimal dspy.Prediction stub."""
    pred = MagicMock(spec=dspy.Prediction)
    pred.relevant_chunk_ids = chunk_ids or []
    pred.trajectory = trajectory or {}
    pred.answer = answer
    return pred


def _make_example(
    question: str = "where is X defined?",
    expected: list[str] | None = None,
    expected_primary: list[str] | None = None,
    category: str = "A",
    expected_tool: str | None = "search_code",
    query_id: str = "Q01",
) -> dspy.Example:
    """Build a minimal dspy.Example for testing."""
    return dspy.Example(
        question=question,
        expected=expected or ["path/to/file.py:function:foo"],
        expected_primary=expected_primary or ["path/to/file.py:function:foo"],
        category=category,
        expected_tool=expected_tool,
        query_id=query_id,
    ).with_inputs("question")


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


class TestLoadExamples:
    def test_returns_13_examples(self, golden_dataset_path):
        if not golden_dataset_path.exists():
            pytest.skip("golden_dataset.json not found")
        examples, _ = load_examples(golden_dataset_path)
        assert len(examples) == 13

    def test_thresholds_dict_returned(self, golden_dataset_path):
        if not golden_dataset_path.exists():
            pytest.skip("golden_dataset.json not found")
        _, thresholds = load_examples(golden_dataset_path)
        assert isinstance(thresholds, dict)

    def test_examples_have_required_fields(self, golden_dataset_path):
        if not golden_dataset_path.exists():
            pytest.skip("golden_dataset.json not found")
        examples, _ = load_examples(golden_dataset_path)
        ex = examples[0]
        assert ex.question  # non-empty string
        assert isinstance(ex.expected, list)
        assert isinstance(ex.expected_primary, list)
        assert ex.category in ("A", "B", "C")

    def test_expected_tool_set_for_abc_categories(self, golden_dataset_path):
        if not golden_dataset_path.exists():
            pytest.skip("golden_dataset.json not found")
        examples, _ = load_examples(golden_dataset_path)
        for ex in examples:
            if ex.category in ("A", "B", "C"):
                assert ex.expected_tool == "search_code"

    def test_with_inputs_marks_question_as_input(self, golden_dataset_path):
        if not golden_dataset_path.exists():
            pytest.skip("golden_dataset.json not found")
        examples, _ = load_examples(golden_dataset_path)
        ex = examples[0]
        # dspy.Example.with_inputs stores the input keys
        assert "question" in ex._input_keys  # type: ignore[attr-defined]

    def test_synthetic_dataset_roundtrip(self, tmp_path):
        """load_examples works on any conforming JSON, not just the real golden."""
        data = {
            "queries": [
                {
                    "id": "T01",
                    "query": "find the embedder",
                    "category": "A",
                    "expected": ["a.py:function:foo"],
                    "expected_primary": ["a.py:function:foo"],
                }
            ],
            "thresholds": {"mrr": 0.5, "recall_at_5": 0.6, "hit_rate_at_5": 0.7},
        }
        p = tmp_path / "test_golden.json"
        p.write_text(json.dumps(data), encoding="utf-8")

        examples, thresholds = load_examples(p)
        assert len(examples) == 1
        assert examples[0].question == "find the embedder"
        assert examples[0].expected_tool == "search_code"
        assert thresholds["mrr"] == 0.5


# ---------------------------------------------------------------------------
# _extract_chunk_ids
# ---------------------------------------------------------------------------


class TestExtractChunkIds:
    def test_list_input_normalised(self):
        pred = _make_pred(chunk_ids=["a/b.py:100-120:function:foo"])
        result = _extract_chunk_ids(pred)
        assert result == ["a/b.py:function:foo"]

    def test_string_input_split_on_comma(self):
        pred = MagicMock()
        pred.relevant_chunk_ids = "a.py:function:foo, b.py:class:Bar"
        result = _extract_chunk_ids(pred)
        assert "a.py:function:foo" in result
        assert "b.py:class:Bar" in result

    def test_empty_returns_empty_list(self):
        pred = _make_pred(chunk_ids=[])
        assert _extract_chunk_ids(pred) == []

    def test_absent_field_returns_empty_list(self):
        pred = MagicMock(spec=["answer"])  # no relevant_chunk_ids attr
        assert _extract_chunk_ids(pred) == []

    def test_deduplication_after_normalisation(self):
        """Two chunk IDs that differ only in line range normalize to one."""
        pred = _make_pred(
            chunk_ids=[
                "a/b.py:10-20:function:foo",
                "a/b.py:10-30:function:foo",  # same name, different range → deduped
            ]
        )
        result = _extract_chunk_ids(pred)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# _extract_tools_from_trajectory
# ---------------------------------------------------------------------------


class TestExtractToolsFromTrajectory:
    def test_extracts_tool_names(self):
        traj = {
            "thought_0": "I should search",
            "tool_name_0": "search_code",
            "observation_0": "Found chunks",
        }
        assert "search_code" in _extract_tools_from_trajectory(traj)

    def test_multiple_steps(self):
        traj = {
            "tool_name_0": "search_code",
            "tool_name_1": "find_connections",
        }
        result = _extract_tools_from_trajectory(traj)
        assert "search_code" in result
        assert "find_connections" in result

    def test_empty_trajectory(self):
        assert _extract_tools_from_trajectory({}) == set()
        assert _extract_tools_from_trajectory(None) == set()

    def test_case_insensitive(self):
        traj = {"tool_name_0": "Search_Code"}
        result = _extract_tools_from_trajectory(traj)
        assert "search_code" in result


# ---------------------------------------------------------------------------
# recall_at_k_metric
# ---------------------------------------------------------------------------


class TestRecallAtKMetric:
    def test_full_recall(self):
        ex = _make_example(expected=["a.py:function:foo", "b.py:class:Bar"])
        pred = _make_pred(chunk_ids=["a.py:function:foo", "b.py:class:Bar"])
        assert recall_at_k_metric(ex, pred, k=7) == 1.0

    def test_zero_recall(self):
        ex = _make_example(expected=["a.py:function:foo"])
        pred = _make_pred(chunk_ids=["z.py:function:unrelated"])
        assert recall_at_k_metric(ex, pred, k=7) == 0.0

    def test_partial_recall(self):
        ex = _make_example(expected=["a.py:function:foo", "b.py:class:Bar"])
        pred = _make_pred(chunk_ids=["a.py:function:foo"])
        score = recall_at_k_metric(ex, pred, k=7)
        assert score == pytest.approx(0.5)

    def test_empty_prediction(self):
        ex = _make_example(expected=["a.py:function:foo"])
        pred = _make_pred(chunk_ids=[])
        assert recall_at_k_metric(ex, pred, k=7) == 0.0

    def test_line_range_normalised_before_comparison(self):
        """Chunk IDs with line ranges in pred should still match golden IDs."""
        ex = _make_example(expected=["a.py:function:foo"])
        pred = _make_pred(chunk_ids=["a.py:10-30:function:foo"])  # raw form
        assert recall_at_k_metric(ex, pred, k=7) == 1.0


# ---------------------------------------------------------------------------
# mrr_metric
# ---------------------------------------------------------------------------


class TestMRRMetric:
    def test_first_hit_gives_mrr_1(self):
        ex = _make_example(expected_primary=["a.py:function:foo"])
        pred = _make_pred(chunk_ids=["a.py:function:foo", "b.py:class:Bar"])
        assert mrr_metric(ex, pred) == pytest.approx(1.0)

    def test_second_hit_gives_mrr_half(self):
        ex = _make_example(expected_primary=["b.py:function:bar"])
        pred = _make_pred(chunk_ids=["a.py:function:foo", "b.py:function:bar"])
        assert mrr_metric(ex, pred) == pytest.approx(0.5)

    def test_no_hit_gives_zero(self):
        ex = _make_example(expected_primary=["z.py:function:target"])
        pred = _make_pred(chunk_ids=["a.py:function:foo"])
        assert mrr_metric(ex, pred) == 0.0


# ---------------------------------------------------------------------------
# tool_selection_metric
# ---------------------------------------------------------------------------


class TestToolSelectionMetric:
    def test_correct_tool_scores_one(self):
        ex = _make_example(expected_tool="search_code")
        pred = _make_pred(trajectory={"tool_name_0": "search_code"})
        assert tool_selection_metric(ex, pred) == 1.0

    def test_wrong_tool_scores_zero(self):
        ex = _make_example(expected_tool="search_code")
        pred = _make_pred(trajectory={"tool_name_0": "find_connections"})
        assert tool_selection_metric(ex, pred) == 0.0

    def test_correct_tool_in_later_step_scores_one(self):
        """Recovery across the trajectory — not just step 0."""
        ex = _make_example(expected_tool="search_code")
        pred = _make_pred(
            trajectory={
                "tool_name_0": "find_connections",  # wrong first attempt
                "tool_name_1": "search_code",  # correct on retry
            }
        )
        assert tool_selection_metric(ex, pred) == 1.0

    def test_no_expected_tool_returns_one(self):
        """Category D (no ground truth) should not count against the score."""
        ex = _make_example(expected_tool=None)
        pred = _make_pred(trajectory={"tool_name_0": "find_connections"})
        assert tool_selection_metric(ex, pred) == 1.0

    def test_empty_trajectory_scores_zero(self):
        ex = _make_example(expected_tool="search_code")
        pred = _make_pred(trajectory={})
        assert tool_selection_metric(ex, pred) == 0.0

    def test_no_trajectory_attr_scores_zero(self):
        ex = _make_example(expected_tool="search_code")
        pred = MagicMock(spec=["answer"])  # no trajectory attr
        assert tool_selection_metric(ex, pred) == 0.0


# ---------------------------------------------------------------------------
# CodeNavQA signature
# ---------------------------------------------------------------------------


class TestCodeNavQASignature:
    # In DSPy 3.x, input_fields / output_fields are class-level dicts,
    # not callable methods.
    def test_has_question_input_field(self):
        assert "question" in CodeNavQA.input_fields

    def test_has_relevant_chunk_ids_output_field(self):
        assert "relevant_chunk_ids" in CodeNavQA.output_fields

    def test_has_answer_output_field(self):
        assert "answer" in CodeNavQA.output_fields

    def test_relevant_chunk_ids_desc_says_verbatim(self):
        """The fix: desc must instruct copying chunk_id verbatim."""
        field = CodeNavQA.output_fields["relevant_chunk_ids"]
        desc = field.json_schema_extra.get("desc", "")
        assert "verbatim" in desc.lower(), (
            "OutputField desc must tell the agent to copy chunk_id verbatim; "
            f"got: {desc!r}"
        )


# ---------------------------------------------------------------------------
# _extract_chunk_ids_from_observations
# ---------------------------------------------------------------------------


def _make_observation_trajectory(observations: list[str]) -> dict:
    """Build a minimal trajectory dict with observation_N keys."""
    return {f"observation_{i}": obs for i, obs in enumerate(observations)}


class TestExtractChunkIdsFromObservations:
    def test_extracts_chunk_id_from_json_observation(self):
        obs = '{"chunks": [{"chunk_id": "search/config.py:10-20:function:foo", "score": 0.9}]}'
        traj = _make_observation_trajectory([obs])
        result = _extract_chunk_ids_from_observations(traj)
        assert "search/config.py:function:foo" in result

    def test_normalises_line_range_from_observation(self):
        """Line ranges are stripped during normalization."""
        obs = '{"chunk_id": "a/b.py:100-200:method:Bar.baz"}'
        traj = _make_observation_trajectory([obs])
        result = _extract_chunk_ids_from_observations(traj)
        assert "a/b.py:method:Bar.baz" in result

    def test_multiple_observations_merged(self):
        obs1 = '{"chunk_id": "a.py:1-5:function:alpha"}'
        obs2 = '{"chunk_id": "b.py:6-10:function:beta"}'
        traj = _make_observation_trajectory([obs1, obs2])
        result = _extract_chunk_ids_from_observations(traj)
        assert "a.py:function:alpha" in result
        assert "b.py:function:beta" in result

    def test_deduplicates_after_normalisation(self):
        """Two observations with the same chunk (different line range) deduplicate."""
        obs1 = '{"chunk_id": "x.py:1-10:method:Foo.run"}'
        obs2 = '{"chunk_id": "x.py:1-15:method:Foo.run"}'  # same after normalisation
        traj = _make_observation_trajectory([obs1, obs2])
        result = _extract_chunk_ids_from_observations(traj)
        assert result.count("x.py:method:Foo.run") == 1

    def test_ignores_non_observation_keys(self):
        traj = {
            "thought_0": '{"chunk_id": "should/be/ignored.py:1-2:function:ghost"}',
            "tool_name_0": "search_code",
            "observation_0": '{"chunk_id": "real/file.py:5-10:function:real"}',
        }
        result = _extract_chunk_ids_from_observations(traj)
        assert "real/file.py:function:real" in result
        assert "should/be/ignored.py:function:ghost" not in result

    def test_empty_trajectory_returns_empty(self):
        assert _extract_chunk_ids_from_observations({}) == []
        assert _extract_chunk_ids_from_observations(None) == []

    def test_observation_with_no_chunk_ids_returns_empty(self):
        traj = _make_observation_trajectory(['{"error": "no results"}'])
        assert _extract_chunk_ids_from_observations(traj) == []


# ---------------------------------------------------------------------------
# trajectory_recall_metric
# ---------------------------------------------------------------------------


def _make_pred_with_trajectory(
    observations: list[str], chunk_ids: list[str] | None = None
) -> MagicMock:
    """Build a Prediction stub with a trajectory and optional emitted chunk IDs."""
    pred = MagicMock(spec=dspy.Prediction)
    pred.relevant_chunk_ids = chunk_ids or []
    pred.trajectory = _make_observation_trajectory(observations)
    return pred


class TestTrajectoryRecallMetric:
    def test_full_trajectory_recall(self):
        """Tool surfaced all expected chunks — ceiling is 1.0."""
        ex = _make_example(expected=["a.py:function:foo"])
        obs = '{"chunk_id": "a.py:1-5:function:foo"}'
        pred = _make_pred_with_trajectory([obs])
        assert trajectory_recall_metric(ex, pred, k=7) == pytest.approx(1.0)

    def test_partial_trajectory_recall(self):
        ex = _make_example(expected=["a.py:function:foo", "b.py:class:Bar"])
        obs = '{"chunk_id": "a.py:1-5:function:foo"}'
        pred = _make_pred_with_trajectory([obs])
        assert trajectory_recall_metric(ex, pred, k=7) == pytest.approx(0.5)

    def test_zero_trajectory_recall(self):
        ex = _make_example(expected=["target.py:function:missing"])
        obs = '{"chunk_id": "other.py:1-5:function:irrelevant"}'
        pred = _make_pred_with_trajectory([obs])
        assert trajectory_recall_metric(ex, pred, k=7) == pytest.approx(0.0)

    def test_empty_trajectory_returns_zero(self):
        ex = _make_example(expected=["a.py:function:foo"])
        pred = _make_pred_with_trajectory([])
        assert trajectory_recall_metric(ex, pred, k=7) == 0.0


# ---------------------------------------------------------------------------
# Regression: verbatim raw chunk IDs still score correctly after normalisation
# ---------------------------------------------------------------------------


class TestVerbatimChunkIdNormalization:
    """Locks in that raw (line-range-bearing) chunk IDs from search_code
    normalise to the golden shape so 'copy verbatim' is safe for the agent."""

    def test_raw_line_range_id_scores_recall_one(self):
        """An emitted ID with a line range still hits the golden after normalization."""
        ex = _make_example(
            expected=[
                "search/incremental_indexer.py:method:IncrementalIndexer.needs_reindex"
            ]
        )
        # Raw form as search_code would return it:
        raw_id = "search/incremental_indexer.py:1253-1273:method:IncrementalIndexer.needs_reindex"
        pred = _make_pred(chunk_ids=[raw_id])
        assert recall_at_k_metric(ex, pred, k=7) == pytest.approx(1.0)

    def test_split_block_id_normalises_to_method(self):
        ex = _make_example(
            expected=[
                "graph/graph_integration.py:method:GraphIntegration.populate_from_embeddings"
            ]
        )
        raw_id = "graph/graph_integration.py:276-310:split_block:GraphIntegration.populate_from_embeddings"
        pred = _make_pred(chunk_ids=[raw_id])
        assert recall_at_k_metric(ex, pred, k=7) == pytest.approx(1.0)

    def test_decorated_definition_id_passes_through_unchanged(self):
        ex = _make_example(
            expected=["search/config.py:decorated_definition:EmbeddingConfig"]
        )
        raw_id = "search/config.py:148-161:decorated_definition:EmbeddingConfig"
        pred = _make_pred(chunk_ids=[raw_id])
        assert recall_at_k_metric(ex, pred, k=7) == pytest.approx(1.0)
