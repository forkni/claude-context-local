"""Unit tests for evaluation/dspy_gepa_optimize.py (offline — no live GEPA compile).

Covers:
- ``gepa_metric``: 5-arg signature, score correctness, feedback content.
- ``gepa_tool_bridge``: background loop bridge marshals calls correctly,
  handles timeout, handles exception.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import dspy
import pytest

from evaluation.dspy_gepa_optimize import gepa_metric, gepa_tool_bridge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gold(expected: list[str]) -> MagicMock:
    """Minimal gold Example."""
    gold = MagicMock()
    gold.expected = expected
    return gold


def _make_pred(
    chunk_ids: list[str],
    trajectory: dict | None = None,
) -> MagicMock:
    """Minimal pred Prediction."""
    pred = MagicMock()
    pred.relevant_chunk_ids = chunk_ids
    pred.trajectory = trajectory
    # Make attribute access work for getattr(pred, "trajectory", None)
    type(pred).trajectory = property(lambda self: trajectory)  # type: ignore[assignment]
    return pred


def _obs(chunk_ids: list[str]) -> str:
    """Build a JSON observation string containing the given chunk_ids."""
    import json

    return json.dumps(
        [{"chunk_id": cid, "score": 0.9} for cid in chunk_ids], ensure_ascii=False
    )


# ---------------------------------------------------------------------------
# gepa_metric signature compatibility
# ---------------------------------------------------------------------------


class TestGepaMetricSignature:
    def test_5_arg_callable_works(self):
        """GEPA asserts 5-arg arity — must bind with None×5."""
        import inspect

        sig = inspect.signature(gepa_metric)
        params = list(sig.parameters)
        assert len(params) == 5, (
            f"gepa_metric must have exactly 5 parameters; got {params}"
        )

    def test_returns_prediction_with_score_and_feedback(self):
        """Return value must be a dspy.Prediction with .score and .feedback."""
        gold = _make_gold(["a.py:1-5:function:foo"])
        pred = _make_pred(["a.py:1-5:function:foo"])
        result = gepa_metric(gold, pred, None, None, None)
        assert isinstance(result, dspy.Prediction), (
            f"gepa_metric must return dspy.Prediction; got {type(result)}"
        )
        assert isinstance(result.score, float), (
            f"result.score must be float; got {type(result.score)}"
        )
        assert isinstance(result.feedback, str), (
            f"result.feedback must be str; got {type(result.feedback)}"
        )


# ---------------------------------------------------------------------------
# gepa_metric score correctness
# ---------------------------------------------------------------------------


class TestGepaMetricScore:
    def test_perfect_recall_scores_one(self):
        """All expected IDs emitted → Recall@7 = 1.0."""
        ids = ["a.py:1-5:function:foo", "b.py:2-8:class:Bar"]
        gold = _make_gold(ids)
        pred = _make_pred(ids)
        result = gepa_metric(gold, pred)
        assert result.score == pytest.approx(1.0)

    def test_zero_recall_scores_zero(self):
        """No expected IDs emitted → Recall@7 = 0.0."""
        gold = _make_gold(["a.py:1-5:function:foo"])
        pred = _make_pred(["z.py:9-15:function:other"])
        result = gepa_metric(gold, pred)
        assert result.score == pytest.approx(0.0)

    def test_partial_recall_score(self):
        """Half the IDs emitted → score ≈ 0.5."""
        ids = ["a.py:1-5:function:foo", "b.py:2-8:class:Bar"]
        gold = _make_gold(ids)
        pred = _make_pred([ids[0]])  # only first
        result = gepa_metric(gold, pred)
        assert result.score == pytest.approx(0.5)

    def test_empty_prediction_scores_zero(self):
        gold = _make_gold(["a.py:1-5:function:foo"])
        pred = _make_pred([])
        result = gepa_metric(gold, pred)
        assert result.score == pytest.approx(0.0)

    def test_score_consistent_regardless_of_pred_name(self):
        """Score must not change with different pred_name (GEPA warn_on_score_mismatch)."""
        gold = _make_gold(["a.py:1-5:function:foo"])
        pred = _make_pred(["a.py:1-5:function:foo"])
        r1 = gepa_metric(gold, pred, None, "predictor_A", None)
        r2 = gepa_metric(gold, pred, None, "predictor_B", None)
        assert r1.score == pytest.approx(r2.score)


# ---------------------------------------------------------------------------
# gepa_metric feedback content
# ---------------------------------------------------------------------------


class TestGepaMetricFeedback:
    def test_dropped_surfaced_appears_in_feedback(self):
        """Chunk surfaced by tools but omitted from answer must be named in feedback."""
        expected_id = "a.py:1-5:function:foo"
        gold = _make_gold([expected_id])
        # Trajectory observation contains the expected chunk, but pred doesn't emit it.
        traj = {
            "thought_0": "...",
            "tool_name_0": "search_code",
            "observation_0": _obs([expected_id]),
        }
        pred = _make_pred([], trajectory=traj)
        result = gepa_metric(gold, pred, None, None, None)
        assert result.score == pytest.approx(0.0)
        assert (
            expected_id in result.feedback
            or "surfaced but omitted" in result.feedback.lower()
            or "omit" in result.feedback.lower()
        ), (
            f"Expected dropped chunk_id or 'omitted' in feedback; got: {result.feedback!r}"
        )

    def test_never_surfaced_mentioned_separately(self):
        """Chunk not in trajectory at all must be distinguished from dropped chunks."""
        expected_id = "z.py:99-110:class:Missing"
        gold = _make_gold([expected_id])
        pred = _make_pred([], trajectory={"thought_0": "nothing useful"})
        result = gepa_metric(gold, pred, None, None, None)
        # Should mention "never surfaced" or "not found" — distinct from "surfaced but omitted".
        assert (
            "never surfaced" in result.feedback.lower()
            or "not found" in result.feedback.lower()
            or "broader" in result.feedback.lower()
            or expected_id in result.feedback
        ), f"Expected 'never surfaced' signal in feedback; got: {result.feedback!r}"

    def test_correct_hits_mentioned(self):
        """Hits (expected IDs correctly emitted) should appear in feedback."""
        hit_id = "a.py:1-5:function:foo"
        gold = _make_gold([hit_id])
        pred = _make_pred([hit_id])
        result = gepa_metric(gold, pred, None, None, None)
        assert hit_id in result.feedback or "correct" in result.feedback.lower(), (
            f"Hits should be mentioned in feedback; got: {result.feedback!r}"
        )

    def test_recall_score_mentioned_in_feedback(self):
        """Feedback must include the numeric recall score so GEPA can reason about it."""
        gold = _make_gold(["a.py:1-5:function:foo"])
        pred = _make_pred(["a.py:1-5:function:foo"])
        result = gepa_metric(gold, pred)
        assert "recall" in result.feedback.lower() or "1.000" in result.feedback, (
            f"Recall score should be in feedback; got: {result.feedback!r}"
        )

    def test_no_crash_with_no_trajectory(self):
        """None trajectory must not crash the metric."""
        gold = _make_gold(["a.py:1-5:function:foo"])
        pred = MagicMock()
        pred.relevant_chunk_ids = ["a.py:1-5:function:foo"]
        type(pred).trajectory = property(lambda self: None)  # type: ignore[assignment]
        result = gepa_metric(gold, pred, None, None, None)
        assert isinstance(result, dspy.Prediction)


# ---------------------------------------------------------------------------
# gepa_tool_bridge: background loop bridge
# ---------------------------------------------------------------------------


class TestGepaBridge:
    """Exercises the real gepa_tool_bridge() context manager end-to-end, with
    only the network-dependent code_search_session() faked out.

    Previously each test here hand-rolled its own ``_sync(**kwargs)`` closure
    that reimplemented gepa_tool_bridge's internal ``_make_sync_func`` /
    ``_sync_func`` logic (lock + run_coroutine_threadsafe + timeout/exception
    -> observation string) from scratch -- a regression in the real bridge
    code could never be caught, since production code never ran.
    """

    @staticmethod
    def _fake_session_yielding(async_func, tool_name="test_tool"):
        """Build a fake code_search_session() replacement that skips the
        network entirely and yields a single dspy.Tool wrapping async_func,
        matching the ``(session, dspy_tools)`` shape the real session yields.
        """

        @asynccontextmanager
        async def _fake_session(
            *, project_path, server_url, tool_names, tool_timeout_s
        ):
            tools = [
                dspy.Tool(func=async_func, name=tool_name, desc="test tool", args={})
            ]
            yield (None, tools)

        return _fake_session

    def test_sync_wrapper_returns_value(self):
        """A trivial async function should be callable synchronously through
        the real bridge."""

        async def _trivial(**kwargs):  # noqa: ANN202
            return {"answer": 42, **kwargs}

        fake_session = self._fake_session_yielding(_trivial)
        with (
            patch("evaluation.dspy_gepa_optimize.code_search_session", fake_session),
            gepa_tool_bridge(project_path="/fake/project") as sync_tools,
        ):
            val = sync_tools[0].func(x=1)

        assert val == {"answer": 42, "x": 1}

    @pytest.mark.slow
    def test_bridge_timeout_returns_observation_string(self):
        """A very slow async function should yield an observation string via
        the real bridge's TimeoutError handling, not raise.

        gepa_tool_bridge hardcodes its future.result() timeout as
        ``tool_timeout_s + 5`` -- there is no seam to shorten it -- so this
        test genuinely waits ~5s for that real timeout to fire. Marked slow
        accordingly.
        """

        async def _slow(**_kwargs):
            await asyncio.sleep(100)
            return "should not reach here"

        tool_name = "test_tool"
        fake_session = self._fake_session_yielding(_slow, tool_name=tool_name)
        with (
            patch("evaluation.dspy_gepa_optimize.code_search_session", fake_session),
            gepa_tool_bridge(
                project_path="/fake/project", tool_timeout_s=0.1
            ) as sync_tools,
        ):
            result = sync_tools[0].func()

        assert f"Execution error in {tool_name}" in result
        assert "timeout after" in result

    def test_bridge_exception_returns_observation_string(self):
        """A failing async function should yield 'Execution error in …' via
        the real bridge's exception handling, not raise."""

        async def _failing(**_kwargs):
            raise ValueError("deliberate failure")

        tool_name = "test_tool"
        fake_session = self._fake_session_yielding(_failing, tool_name=tool_name)
        with (
            patch("evaluation.dspy_gepa_optimize.code_search_session", fake_session),
            gepa_tool_bridge(project_path="/fake/project") as sync_tools,
        ):
            result = sync_tools[0].func()

        assert result.startswith(f"Execution error in {tool_name}")
        assert "deliberate failure" in result
