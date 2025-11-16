"""Session metrics tracking for MCP server."""

import logging
import time
from typing import Dict, List

logger = logging.getLogger(__name__)


class SessionMetrics:
    """Track MCP session lifecycle metrics."""

    def __init__(self):
        self.active_sessions: Dict[str, float] = {}
        self.total_sessions = 0
        self.session_durations: List[float] = []
        self._session_tool_calls: Dict[str, int] = {}
        
    def start_session(self, session_id: str):
        """Record session start."""
        self.active_sessions[session_id] = time.time()
        self.total_sessions += 1
        self._session_tool_calls[session_id] = 0
        
        logger.info(
            f"[METRICS] Session started: {session_id[:8]}... "
            f"(active: {len(self.active_sessions)}, total: {self.total_sessions})"
        )
    
    def end_session(self, session_id: str):
        """Record session end."""
        if session_id in self.active_sessions:
            duration = time.time() - self.active_sessions[session_id]
            self.session_durations.append(duration)
            tool_calls = self._session_tool_calls.get(session_id, 0)
            
            del self.active_sessions[session_id]
            self._session_tool_calls.pop(session_id, None)
            
            logger.info(
                f"[METRICS] Session ended: {session_id[:8]}... "
                f"(duration: {duration:.2f}s, tool_calls: {tool_calls}, "
                f"active: {len(self.active_sessions)})"
            )
            
            # Log summary every 10 sessions
            if self.total_sessions % 10 == 0:
                self.log_summary()
    
    def record_tool_call(self, session_id: str, tool_name: str):
        """Record a tool call for a session."""
        if session_id in self._session_tool_calls:
            self._session_tool_calls[session_id] += 1
    
    def get_stats(self) -> Dict:
        """Get current metrics statistics."""
        avg_duration = (
            sum(self.session_durations) / len(self.session_durations)
            if self.session_durations
            else 0
        )
        
        return {
            "active_sessions": len(self.active_sessions),
            "total_sessions": self.total_sessions,
            "avg_duration_seconds": round(avg_duration, 2),
            "completed_sessions": len(self.session_durations),
        }
    
    def log_summary(self):
        """Log metrics summary."""
        stats = self.get_stats()
        logger.info(
            f"[METRICS SUMMARY] "
            f"Active={stats['active_sessions']}, "
            f"Total={stats['total_sessions']}, "
            f"Avg Duration={stats['avg_duration_seconds']}s"
        )


# Global metrics instance
_session_metrics = SessionMetrics()


def get_session_metrics() -> SessionMetrics:
    """Get the global session metrics instance."""
    return _session_metrics
