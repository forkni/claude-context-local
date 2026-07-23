"""In-memory background-job registry for long-running MCP tool calls.

Implements the paper's mitigation (arXiv:2606.30317v1 §V-C, "Synchronous
Long-Running Operations" anti-pattern): instead of blocking a tool call for
the full duration of an expensive operation (e.g. indexing a large repo),
the handler launches the work as a background asyncio task, returns a
``job_id`` immediately, and the caller polls a status tool
(``get_index_status``) until the job reaches a terminal state.

Process-local and in-memory by design — jobs do not survive a server
restart and are not shared across worker processes. That is an acceptable
trade-off for this server (a single long-lived stdio/HTTP process).
"""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Literal


JobStatus = Literal["running", "done", "error"]


@dataclass
class Job:
    """One tracked background operation."""

    job_id: str
    kind: str
    target: str
    status: JobStatus = "running"
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def to_status_dict(self) -> dict[str, Any]:
        """Render this job as a JSON-safe dict for a tool response."""
        d: dict[str, Any] = {
            "job_id": self.job_id,
            "kind": self.kind,
            "target": self.target,
            "status": self.status,
        }
        end = self.finished_at if self.finished_at is not None else time.time()
        d["elapsed_seconds"] = round(end - self.started_at, 2)
        if self.status == "done" and self.result is not None:
            d["result"] = self.result
        elif self.status == "error" and self.error is not None:
            d["error"] = self.error
        return d


class JobRegistry:
    """Process-wide registry of background jobs, guarded by an asyncio.Lock."""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = asyncio.Lock()
        self._counter = itertools.count(1)
        # Fire-and-forget asyncio.create_task() results must be held with a
        # strong reference or the event loop's task may be garbage-collected
        # before it finishes — a well-documented asyncio pitfall. Tracking
        # tasks here (and dropping them on completion) prevents that.
        self._background_tasks: set[asyncio.Task] = set()

    def _new_job_id(self, kind: str) -> str:
        return f"{kind}-{next(self._counter)}-{int(time.time())}"

    async def create(self, kind: str, target: str) -> Job:
        """Register a new running job for *target* (e.g. a project path)."""
        job = Job(job_id=self._new_job_id(kind), kind=kind, target=target)
        async with self._lock:
            self._jobs[job.job_id] = job
        return job

    async def mark_done(self, job_id: str, result: dict[str, Any]) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "done"
            job.result = result
            job.finished_at = time.time()

    async def mark_error(self, job_id: str, error: str) -> None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "error"
            job.error = error
            job.finished_at = time.time()

    async def get(self, job_id: str) -> Job | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def latest_for_target(self, target: str) -> Job | None:
        """Return the most recently created job for *target*, if any.

        Uses dict insertion order (guaranteed since Python 3.7) rather than
        ``started_at`` — jobs created in the same wall-clock second would
        otherwise tie and make this non-deterministic.
        """
        async with self._lock:
            candidates = [j for j in self._jobs.values() if j.target == target]
        return candidates[-1] if candidates else None

    def track_background_task(self, task: asyncio.Task) -> None:
        """Hold a strong reference to *task* until it completes.

        Without this, a bare ``asyncio.create_task(...)`` result that isn't
        awaited or stored anywhere can be garbage-collected mid-execution,
        silently cancelling the job. See the asyncio docs' note on
        "Important: Save a reference to the result of this function".
        """
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)


_registry: JobRegistry | None = None


def get_job_registry() -> JobRegistry:
    """Return the process-wide :class:`JobRegistry` singleton (lazy-created)."""
    global _registry
    if _registry is None:
        _registry = JobRegistry()
    return _registry


def reset_job_registry() -> None:
    """Reset the singleton. Test-only: ensures no cross-test job leakage."""
    global _registry
    _registry = None
