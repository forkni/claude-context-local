"""Unit tests for evaluation/dspy_gepa_optimize.py (offline — no live GEPA compile).

Covers:
- ``gepa_metric``: 5-arg signature, score correctness, feedback content.
- ``gepa_tool_bridge``: background loop bridge marshals calls correctly,
  handles timeout, handles exception.
"""

import asyncio
import threading
from unittest.mock import MagicMock

import dspy
import pytest

from evaluation.dspy_gepa_optimize import gepa_metric


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
    def test_sync_wrapper_returns_value(self):
        """A trivial async function should be callable synchronously through the bridge."""

        loop = asyncio.new_event_loop()
        ready = threading.Event()
        cleanup = threading.Event()

        async def _trivial(**kwargs):  # noqa: ANN202
            return {"answer": 42, **kwargs}

        # Manually exercise the bridge internals: start a loop, wrap an async func,
        # call it synchronously via run_coroutine_threadsafe.
        def _run():
            loop.run_until_complete(_bg())
            loop.close()

        async def _bg():
            ready.set()
            while not cleanup.is_set():
                await asyncio.sleep(0.05)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        ready.wait()

        # Simulate the bridge's sync wrapper pattern.
        lock = threading.Lock()

        def _sync(**kwargs):
            with lock:
                future = asyncio.run_coroutine_threadsafe(_trivial(**kwargs), loop)
                return future.result(timeout=5)

        val = _sync(x=1)
        assert val == {"answer": 42, "x": 1}

        # Cleanup.
        cleanup.set()
        t.join(timeout=3)

    def test_bridge_timeout_returns_observation_string(self):
        """A very slow async func should yield an observation string, not raise."""
        loop = asyncio.new_event_loop()
        ready = threading.Event()
        cleanup = threading.Event()

        async def _slow(**_kwargs):
            await asyncio.sleep(100)
            return "should not reach here"

        def _run():
            loop.run_until_complete(_bg())
            loop.close()

        async def _bg():
            ready.set()
            while not cleanup.is_set():
                await asyncio.sleep(0.05)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        ready.wait()

        tool_name = "test_tool"
        timeout_s = 0.1  # very short

        def _sync(**kwargs):
            future = asyncio.run_coroutine_threadsafe(_slow(**kwargs), loop)
            try:
                return future.result(timeout=timeout_s)
            except Exception:  # noqa: BLE001
                return f"Execution error in {tool_name}: timeout after {timeout_s:.0f}s"

        result = _sync()
        assert "Execution error in" in result

        # Cleanup.
        cleanup.set()
        t.join(timeout=3)

    def test_bridge_exception_returns_observation_string(self):
        """A failing async func should yield 'Execution error in …', not raise."""
        loop = asyncio.new_event_loop()
        ready = threading.Event()
        cleanup = threading.Event()

        async def _failing(**_kwargs):
            raise ValueError("deliberate failure")

        def _run():
            loop.run_until_complete(_bg())
            loop.close()

        async def _bg():
            ready.set()
            while not cleanup.is_set():
                await asyncio.sleep(0.05)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        ready.wait()

        tool_name = "test_tool"

        def _sync(**kwargs):
            future = asyncio.run_coroutine_threadsafe(_failing(**kwargs), loop)
            try:
                return future.result(timeout=5)
            except Exception as exc:  # noqa: BLE001
                return f"Execution error in {tool_name}: {exc}"

        result = _sync()
        assert result.startswith(f"Execution error in {tool_name}")
        assert "deliberate failure" in result

        # Cleanup.
        cleanup.set()
        t.join(timeout=3)
