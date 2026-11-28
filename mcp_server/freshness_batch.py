"""Many index-freshness checks at once (ADR-0058 verdicts), torch-free.

One check (``compute_index_freshness``) is a Merkle scan in Python that holds
the GIL, so threads run it no faster than one loop. Processes do: measured
2026-11-27 on 16 projects, one loop 1.6 s, one thread per check 1.9 s, a
4-process pool 1.0 s.

Two users:

- The launcher's project lists (``scripts/project_status.py``) call
  :func:`check_many` in their own process.
- The server's ``list_projects(check_freshness=True)`` calls
  :func:`run_in_subprocess`. A process pool inside the server would make each
  worker re-import the server (it runs as ``-m mcp_server.server``, about
  4.8 s with torch); a child running this module imports only the check
  (about 0.3 s) and runs the pool itself. The child is a plain
  ``subprocess.run`` so it works under any event loop: the HTTP transport uses
  ``WindowsSelectorEventLoop``, which cannot start asyncio subprocesses.

Each result is a JSON-safe dict: ``{"state": "ok", "verdict": <dict or None>}``
(None: never indexed), ``{"state": "missing"}`` (no project folder) or
``{"state": "error", "message": str}``.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from concurrent.futures import Executor, ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORKERS = 4
SUBPROCESS_TIMEOUT_SECS = 120.0

Job = tuple[str, str, int]  # (project_path, model_slug, dimension)


def check_one(project_path: str, model_slug: str, dimension: int) -> dict:
    """The freshness verdict for one project and model; never raises."""
    if not os.path.isdir(project_path):
        return {"state": "missing"}
    try:
        # Looked up at call time, so a test's patch of the module attribute applies.
        from mcp_server import index_freshness

        verdict = index_freshness.compute_index_freshness(
            project_path, model_slug=model_slug, dimension=dimension
        )
    except Exception as exc:  # noqa: BLE001 - one project's failure must not hide the others
        return {"state": "error", "message": f"{type(exc).__name__}: {exc}"}
    return {"state": "ok", "verdict": verdict}


def _quiet_worker() -> None:
    """Worker start-up: stdout may be a caller's data channel, so print to stderr."""
    sys.stdout = sys.stderr


def _make_pool(workers: int) -> Executor:
    """The executor for :func:`check_many` (tests swap in a thread pool)."""
    return ProcessPoolExecutor(workers, initializer=_quiet_worker)


def check_many(jobs: Sequence[Job], *, workers: int = DEFAULT_WORKERS) -> list[dict]:
    """:func:`check_one` for each job, results in job order.

    Uses a pool of up to ``workers`` processes when there are two or more
    jobs; runs them one by one when ``workers`` is 1 or the pool cannot start
    or breaks.
    """
    jobs = list(jobs)
    if workers > 1 and len(jobs) > 1:
        try:
            with _make_pool(min(workers, len(jobs))) as pool:
                return list(pool.map(check_one, *zip(*jobs, strict=True)))
        except (OSError, BrokenProcessPool) as exc:
            print(
                f"[WARN] Freshness pool failed ({exc}); checking one by one",
                file=sys.stderr,
            )
    return [check_one(*job) for job in jobs]


def run_in_subprocess(
    jobs: Sequence[Job], *, timeout: float = SUBPROCESS_TIMEOUT_SECS
) -> list[dict]:
    """:func:`check_many` in a fresh, torch-free Python process.

    Blocking; the server calls it through ``asyncio.to_thread``. stdin is a
    pipe, never the caller's (the MCP stdio transport owns that).

    Raises:
        RuntimeError: the child timed out (it is killed), exited non-zero, or
            wrote something other than one result per job.
    """
    jobs = list(jobs)
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "mcp_server.freshness_batch"],
            input=json.dumps(jobs),
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"freshness subprocess timed out after {timeout:.0f}s"
        ) from exc
    if completed.returncode != 0:
        tail = (completed.stderr or "").strip().splitlines()[-3:]
        raise RuntimeError(
            f"freshness subprocess exited with {completed.returncode}: {' | '.join(tail)}"
        )
    try:
        results = json.loads(completed.stdout)
    except ValueError as exc:
        raise RuntimeError("freshness subprocess output is not JSON") from exc
    if not isinstance(results, list) or len(results) != len(jobs):
        count = len(results) if isinstance(results, list) else "no"
        raise RuntimeError(
            f"freshness subprocess returned {count} results for {len(jobs)} jobs"
        )
    return results


def main() -> int:
    """Read a JSON job list on stdin, write the JSON result list on stdout."""
    jobs = [
        (str(path), str(slug), int(dim)) for path, slug, dim in json.load(sys.stdin)
    ]
    channel = sys.stdout
    sys.stdout = sys.stderr  # anything a check prints stays off the JSON channel
    try:
        results = check_many(jobs)
    finally:
        sys.stdout = channel
    json.dump(results, channel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
