"""Unit tests for utils/progress.py.

Two things need locking down: ``configure_child_logging`` installs exactly
one stderr handler on the *root* logger and is idempotent (a reused
``ProcessPoolExecutor`` worker must never stack duplicate handlers), and
``heartbeat`` throttles to at most one line per interval, resets its counter
and clock on a ``phase`` change, and never emits before the first interval
elapses.
"""

from __future__ import annotations

import logging
import sys

import pytest

from utils.progress import configure_child_logging, heartbeat


@pytest.fixture
def isolated_root_logger():
    """Save and restore the root logger's handlers/level/sentinel attribute.

    configure_child_logging() mutates process-global state (the root
    logger), which pytest's own logging plugin also installs handlers on
    per-test -- so this compares handler-count *deltas* against a baseline
    captured fresh for each test, rather than assuming the root logger
    starts with zero handlers. Yields ``(root_logger, baseline_handler_count)``.
    """
    root = logging.getLogger()
    baseline_handlers = list(root.handlers)
    saved_level = root.level
    had_sentinel = hasattr(root, "_code_search_child_logging_configured")
    saved_sentinel = getattr(root, "_code_search_child_logging_configured", None)
    if had_sentinel:
        delattr(root, "_code_search_child_logging_configured")

    try:
        yield root, len(baseline_handlers)
    finally:
        del root.handlers[len(baseline_handlers) :]
        root.setLevel(saved_level)
        if hasattr(root, "_code_search_child_logging_configured"):
            delattr(root, "_code_search_child_logging_configured")
        if had_sentinel:
            root._code_search_child_logging_configured = saved_sentinel  # type: ignore[attr-defined]


class TestConfigureChildLogging:
    def test_installs_exactly_one_stderr_handler(self, isolated_root_logger) -> None:
        root, baseline = isolated_root_logger
        configure_child_logging(logging.INFO)
        assert len(root.handlers) == baseline + 1
        added = root.handlers[-1]
        assert isinstance(added, logging.StreamHandler)
        assert added.stream is sys.stderr

    def test_sets_root_level(self, isolated_root_logger) -> None:
        root, _baseline = isolated_root_logger
        configure_child_logging(logging.WARNING)
        assert root.level == logging.WARNING

    def test_repeat_calls_do_not_stack_handlers(self, isolated_root_logger) -> None:
        """A reused ProcessPoolExecutor worker calls this once per task --
        must stay a no-op after the first call in that worker's lifetime."""
        root, baseline = isolated_root_logger
        configure_child_logging(logging.INFO)
        configure_child_logging(logging.INFO)
        configure_child_logging(logging.INFO)
        assert len(root.handlers) == baseline + 1

    def test_second_call_does_not_change_level_back(self, isolated_root_logger) -> None:
        """The idempotency guard short-circuits the whole function body,
        including setLevel -- a second call with a different level must not
        override the level the first call already set."""
        root, _baseline = isolated_root_logger
        configure_child_logging(logging.INFO)
        configure_child_logging(logging.ERROR)
        assert root.level == logging.INFO


class _FakeClock:
    """Deterministic stand-in for time.monotonic(), advanced by the test."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class TestHeartbeat:
    @staticmethod
    def _logger() -> logging.Logger:
        return logging.getLogger("test_progress_heartbeat")

    def test_no_emission_before_first_interval_elapses(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import utils.progress as progress_mod

        clock = _FakeClock()
        monkeypatch.setattr(progress_mod.time, "monotonic", clock)

        logger = self._logger()
        with (
            caplog.at_level(logging.INFO, logger=logger.name),
            heartbeat(logger, "[TEST]", 100, unit="files", interval=15.0) as tick,
        ):
            clock.advance(5.0)
            tick()
            clock.advance(5.0)
            tick()
        assert caplog.records == []

    def test_emits_after_interval_elapses(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import utils.progress as progress_mod

        clock = _FakeClock()
        monkeypatch.setattr(progress_mod.time, "monotonic", clock)

        logger = self._logger()
        with (
            caplog.at_level(logging.INFO, logger=logger.name),
            heartbeat(logger, "[TEST]", 100, unit="files", interval=15.0) as tick,
        ):
            clock.advance(16.0)
            tick()
        assert len(caplog.records) == 1
        assert "[TEST]" in caplog.records[0].message
        assert "1/100 files" in caplog.records[0].message

    def test_throttles_to_one_line_per_interval(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import utils.progress as progress_mod

        clock = _FakeClock()
        monkeypatch.setattr(progress_mod.time, "monotonic", clock)

        logger = self._logger()
        with (
            caplog.at_level(logging.INFO, logger=logger.name),
            heartbeat(logger, "[TEST]", 100, unit="files", interval=15.0) as tick,
        ):
            clock.advance(16.0)
            tick()  # 1st emit
            clock.advance(1.0)
            tick()  # too soon, throttled
            clock.advance(1.0)
            tick()  # still too soon
            clock.advance(16.0)
            tick()  # 2nd emit
        assert len(caplog.records) == 2

    def test_phase_change_resets_counter_and_clock(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """pyan walks its file list twice; passing a different phase must
        restart the elapsed-time clock and the completed-count so the ETA
        math (which only makes sense within one pass) does not carry stale
        state across the phase boundary. Phase 1 accumulates to 3 ticks
        before its second emission; if phase 2 did not reset, its own
        second emission would read 5/10 (3 carried over + 2 new) instead
        of 2/10."""
        import utils.progress as progress_mod

        clock = _FakeClock()
        monkeypatch.setattr(progress_mod.time, "monotonic", clock)

        logger = self._logger()
        with (
            caplog.at_level(logging.INFO, logger=logger.name),
            heartbeat(logger, "[PYAN]", 10, unit="files", interval=15.0) as tick,
        ):
            clock.advance(16.0)
            tick(phase="pass 1")  # phase reset (None -> "pass 1"); no emit
            clock.advance(16.0)
            tick(phase="pass 1")  # interval elapsed -> emits 2/10
            clock.advance(16.0)
            tick(phase="pass 1")  # interval elapsed -> emits 3/10
            tick(phase="pass 2")  # phase reset ("pass 1" -> "pass 2"); no emit
            clock.advance(16.0)
            tick(phase="pass 2")  # emits 2/10 -- would be 5/10 without the reset

        messages = [r.message for r in caplog.records]
        assert len(messages) == 3
        assert "2/10 files" in messages[0]
        assert "3/10 files" in messages[1]
        assert "2/10 files" in messages[2]

    def test_tick_n_greater_than_one_advances_completed_count(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import utils.progress as progress_mod

        clock = _FakeClock()
        monkeypatch.setattr(progress_mod.time, "monotonic", clock)

        logger = self._logger()
        with (
            caplog.at_level(logging.INFO, logger=logger.name),
            heartbeat(logger, "[TEST]", 100, unit="chunks", interval=15.0) as tick,
        ):
            clock.advance(16.0)
            tick(n=7)
        assert "7/100 chunks" in caplog.records[0].message

    def test_no_guaranteed_final_line_at_completion(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Reaching total completed items does not by itself force a line
        if the interval has not elapsed -- callers log their own summary."""
        import utils.progress as progress_mod

        clock = _FakeClock()
        monkeypatch.setattr(progress_mod.time, "monotonic", clock)

        logger = self._logger()
        with (
            caplog.at_level(logging.INFO, logger=logger.name),
            heartbeat(logger, "[TEST]", 3, unit="files", interval=15.0) as tick,
        ):
            tick()
            tick()
            tick()
        assert caplog.records == []
