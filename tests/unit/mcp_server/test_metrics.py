"""Unit tests for SessionMetrics (mcp_server/metrics.py)."""

from mcp_server.metrics import SessionMetrics, get_session_metrics


def test_start_session_tracks_active_and_total():
    metrics = SessionMetrics()

    metrics.start_session("session-1")

    assert "session-1" in metrics.active_sessions
    assert metrics.total_sessions == 1
    assert metrics._session_tool_calls["session-1"] == 0


def test_start_session_multiple_sessions_increments_total():
    metrics = SessionMetrics()

    metrics.start_session("session-1")
    metrics.start_session("session-2")

    assert len(metrics.active_sessions) == 2
    assert metrics.total_sessions == 2


def test_end_session_removes_active_and_records_duration():
    metrics = SessionMetrics()
    metrics.start_session("session-1")

    metrics.end_session("session-1")

    assert "session-1" not in metrics.active_sessions
    assert "session-1" not in metrics._session_tool_calls
    assert len(metrics.session_durations) == 1
    assert metrics.session_durations[0] >= 0


def test_end_session_unknown_session_id_is_noop():
    metrics = SessionMetrics()

    metrics.end_session("never-started")

    assert metrics.session_durations == []


def test_end_session_logs_summary_every_ten_sessions():
    metrics = SessionMetrics()

    for i in range(10):
        session_id = f"session-{i}"
        metrics.start_session(session_id)
        metrics.end_session(session_id)

    assert metrics.total_sessions == 10
    assert len(metrics.session_durations) == 10


def test_record_tool_call_increments_count_for_active_session():
    metrics = SessionMetrics()
    metrics.start_session("session-1")

    metrics.record_tool_call("session-1", "search_code")
    metrics.record_tool_call("session-1", "find_connections")

    assert metrics._session_tool_calls["session-1"] == 2


def test_record_tool_call_unknown_session_id_is_noop():
    metrics = SessionMetrics()

    metrics.record_tool_call("never-started", "search_code")

    assert metrics._session_tool_calls == {}


def test_get_stats_empty_metrics():
    metrics = SessionMetrics()

    stats = metrics.get_stats()

    assert stats == {
        "active_sessions": 0,
        "total_sessions": 0,
        "avg_duration_seconds": 0,
        "completed_sessions": 0,
    }


def test_get_stats_reflects_active_and_completed_sessions():
    metrics = SessionMetrics()
    metrics.start_session("session-1")
    metrics.start_session("session-2")
    metrics.end_session("session-1")

    stats = metrics.get_stats()

    assert stats["active_sessions"] == 1
    assert stats["total_sessions"] == 2
    assert stats["completed_sessions"] == 1
    assert isinstance(stats["avg_duration_seconds"], float)


def test_log_summary_does_not_raise():
    metrics = SessionMetrics()
    metrics.start_session("session-1")
    metrics.end_session("session-1")

    metrics.log_summary()


def test_get_session_metrics_returns_singleton():
    first = get_session_metrics()
    second = get_session_metrics()

    assert first is second
    assert isinstance(first, SessionMetrics)
