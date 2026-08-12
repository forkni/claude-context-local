"""Progress reporting for long-running call-graph resolver passes.

Two pieces used together across the resolver pipeline
(``chunking/relationships/{external_call_graph,libcst_call_graph,lsp_call_graph}.py``):

- ``configure_child_logging`` gives a ``ProcessPoolExecutor`` worker a stderr
  handler, since the parent's ``Logger`` (with its unpicklable handlers) never
  crosses the process boundary -- see
  ``call_edge_resolver.py:_resolve_in_subprocess``.
- ``heartbeat`` throttles per-unit progress into periodic log lines instead of
  a rich progress bar: the expensive resolver (pyan) runs in a child process
  and cannot share the parent's ``Console``, so raw stderr writes from two
  processes would scramble a bar's frames. Log lines behave identically on a
  TTY, in a pipe, and under MCP stdio.
"""

from __future__ import annotations

import logging
import sys
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager


_CHILD_LOGGING_CONFIGURED = "_code_search_child_logging_configured"


def configure_child_logging(level: int) -> None:
    """Install a stderr handler on this process's root logger, once.

    Call at the top of a ``ProcessPoolExecutor`` worker before any resolver
    code logs -- the parent's ``Logger`` cannot be passed across the process
    boundary (its handlers hold an unpicklable ``threading.RLock``), so the
    child's root logger otherwise has no handlers and every line is silently
    dropped.

    Deliberately stderr, not the shared rotating log file: two processes
    rotating one ``RotatingFileHandler`` is a Windows file-lock hazard, and
    the child already inherits the parent's stderr fd, so lines land in the
    same stream the parent's console handler uses -- including under
    ``--transport stdio``, where stdout is the JSON-RPC channel and stderr is
    free. Tradeoff: these lines reach the console but not
    ``logs/mcp_server.log``; the parent's per-resolver summary line already
    covers that file.

    Idempotent -- a reused pool worker calling this again is a no-op, so
    handlers never stack.
    """
    root = logging.getLogger()
    if getattr(root, _CHILD_LOGGING_CONFIGURED, False):
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(handler)
    root.setLevel(level)
    root._code_search_child_logging_configured = True  # type: ignore[attr-defined]


def _format_duration(seconds: float) -> str:
    total_seconds = int(seconds)
    if total_seconds < 60:
        return f"{total_seconds}s"
    minutes, secs = divmod(total_seconds, 60)
    return f"{minutes}m{secs:02d}s"


@contextmanager
def heartbeat(
    logger: logging.Logger,
    prefix: str,
    total: int,
    *,
    unit: str,
    interval: float = 15.0,
) -> Iterator[Callable[..., None]]:
    """Yield a ``tick(n=1, phase=None)`` callable that logs throttled progress.

    Emits at most one line per *interval* seconds::

        [PYAN] pass 1: 302/1483 files (20%), 24s elapsed, ~1m35s remaining

    ``phase`` lets one counter be reused across a resolver's distinct passes
    (pyan walks its file list twice) -- passing a different phase than the
    previous tick resets the completed-count and restarts the elapsed clock,
    since the ETA math only makes sense within one pass.

    No line is guaranteed at completion; callers already log their own
    "Resolved N edges" summary once ``resolve()`` returns.
    """
    current_phase: str | None = None
    start = time.monotonic()
    completed = 0
    last_emit = time.monotonic()

    def tick(n: int = 1, phase: str | None = None) -> None:
        nonlocal current_phase, start, completed, last_emit
        now = time.monotonic()
        if phase != current_phase:
            current_phase = phase
            start = now
            completed = 0
            last_emit = now
        completed += n
        if now - last_emit < interval:
            return
        last_emit = now

        elapsed = now - start
        pct = int(completed / total * 100) if total else 0
        label = f"{prefix} {phase}:" if phase else prefix
        rate = completed / elapsed if elapsed > 0 else 0.0
        remaining = (
            (total - completed) / rate if rate > 0 and total > completed else None
        )
        if remaining is not None:
            logger.info(
                "%s %d/%d %s (%d%%), %s elapsed, ~%s remaining",
                label,
                completed,
                total,
                unit,
                pct,
                _format_duration(elapsed),
                _format_duration(remaining),
            )
        else:
            logger.info(
                "%s %d/%d %s (%d%%), %s elapsed",
                label,
                completed,
                total,
                unit,
                pct,
                _format_duration(elapsed),
            )

    yield tick
