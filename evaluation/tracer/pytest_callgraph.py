"""Opt-in pytest plugin that records witnessed project call edges.

Load explicitly, never from ``conftest.py``::

    PYTHONHASHSEED=0 pytest -p no:randomly --timeout=0 \\
        -p evaluation.tracer.pytest_callgraph --callgraph-trace \\
        --callgraph-output evaluation/traced_runs/run1.json tests/unit

Without ``--callgraph-trace`` the plugin registers its options and does
nothing else. With it, the plugin refuses to run in configurations that make
the trace non-reproducible or incomplete:

* pytest-xdist workers or ``-n`` (each worker would profile its own process);
* pytest-randomly active without an explicit ``--randomly-seed`` (test order
  changes which module-level and cached code paths are hit first);
* ``PYTHONHASHSEED`` unset (set iteration order leaks into some code paths).

The profiler is installed after collection (import-time calls are not
witnessed) and removed at the start of ``pytest_sessionfinish`` so the
repository ``conftest.py`` cleanup subprocess runs untraced. The raw payload
is written as ``callgraph-trace-raw/1`` plus a ``meta`` block.
"""

from __future__ import annotations

import atexit
import json
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from evaluation.tracer.collector import TraceCollector


DEFAULT_OUTPUT = "evaluation/traced_runs/run.json"
PLUGIN_NAME = "callgraph-tracer"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("callgraph", "execution-witnessed call graph")
    group.addoption(
        "--callgraph-trace",
        action="store_true",
        dest="callgraph_trace",
        default=False,
        help="Profile the session and write witnessed project call edges.",
    )
    group.addoption(
        "--callgraph-output",
        action="store",
        dest="callgraph_output",
        default=DEFAULT_OUTPUT,
        help=f"Output JSON path, relative to rootdir (default: {DEFAULT_OUTPUT}).",
    )
    group.addoption(
        "--callgraph-include-test-callers",
        action="store_true",
        dest="callgraph_include_test_callers",
        default=False,
        help="Also record test-function -> project-function edges.",
    )


def _check_guards(config: pytest.Config) -> None:
    """Raise ``pytest.UsageError`` for configurations that break the trace."""
    if hasattr(config, "workerinput"):
        raise pytest.UsageError("--callgraph-trace cannot run inside an xdist worker")
    if config.pluginmanager.hasplugin("xdist"):
        numprocesses = config.getoption("numprocesses", default=None)
        if numprocesses not in (None, 0):
            raise pytest.UsageError(
                "--callgraph-trace requires a serial run; drop -n/--numprocesses"
            )
    if config.pluginmanager.hasplugin("randomly"):
        # Runs tryfirst so pytest-randomly has not yet replaced "default" with
        # a fresh random seed; anything but an explicit int is refused.
        seed = config.getoption("randomly_seed", default=None)
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise pytest.UsageError(
                "--callgraph-trace needs a fixed test order: pass -p no:randomly "
                "or an explicit --randomly-seed=<int>"
            )
    if os.environ.get("PYTHONHASHSEED", "") == "":
        raise pytest.UsageError(
            "--callgraph-trace requires PYTHONHASHSEED to be set (use 0)"
        )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if not config.getoption("callgraph_trace"):
        return
    _check_guards(config)
    config.pluginmanager.register(CallgraphTracerPlugin(config), PLUGIN_NAME)


class CallgraphTracerPlugin:
    """Session-scoped state: one collector, one output file."""

    def __init__(self, config: pytest.Config) -> None:
        self.config = config
        self.root = Path(config.rootpath)
        out = Path(config.getoption("callgraph_output"))
        self.output = out if out.is_absolute() else self.root / out
        self.collector = TraceCollector(
            self.root,
            test_dirs=("tests",),
            record_test_callers=config.getoption("callgraph_include_test_callers"),
        )
        self.collected = 0
        self.started_at: float | None = None
        self.written = False
        self._atexit_registered = False

    # -- hooks --------------------------------------------------------------

    def pytest_collection_finish(self, session: pytest.Session) -> None:
        self.collected = len(session.items)
        self.started_at = time.perf_counter()
        if not self._atexit_registered:
            atexit.register(self._backstop)
            self._atexit_registered = True
        self.collector.install()

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        self.collector.uninstall()
        self.write(session=session, exitstatus=int(exitstatus))

    # -- output -------------------------------------------------------------

    def _backstop(self) -> None:
        """Interpreter exit without ``pytest_sessionfinish`` (hard crash path)."""
        if self.written:
            return
        self.collector.uninstall()
        self.write(session=None, exitstatus=-1)

    def _outcome_counts(self) -> dict[str, int]:
        reporter = self.config.pluginmanager.get_plugin("terminalreporter")
        stats: dict[str, list[Any]] = getattr(reporter, "stats", {}) or {}
        return {
            key: len(stats.get(key, []))
            for key in ("passed", "failed", "error", "skipped", "xfailed", "xpassed")
        }

    def build_meta(self, session: pytest.Session | None, exitstatus: int) -> dict:
        duration = (
            time.perf_counter() - self.started_at
            if self.started_at is not None
            else None
        )
        randomly_seed = None
        if self.config.pluginmanager.hasplugin("randomly"):
            randomly_seed = self.config.getoption("randomly_seed", default=None)
        return {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "repo_root": str(self.root),
            "invocation_args": list(self.config.invocation_params.args),
            "pythonhashseed": os.environ.get("PYTHONHASHSEED"),
            "randomly_seed": randomly_seed,
            "collected": self.collected,
            "testsfailed": session.testsfailed if session is not None else None,
            "outcomes": self._outcome_counts(),
            "exitstatus": exitstatus,
            "duration_s": duration,
            "include_test_callers": self.collector.record_test_callers,
        }

    def write(self, session: pytest.Session | None, exitstatus: int) -> Path:
        payload = self.collector.to_payload()
        payload["meta"] = self.build_meta(session, exitstatus)
        self.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.output.with_suffix(self.output.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1, sort_keys=False)
            fh.write("\n")
        os.replace(tmp, self.output)
        self.written = True
        counters = payload["counters"]
        sys.stderr.write(
            f"[callgraph-trace] wrote {self.output} "
            f"(nodes={len(payload['nodes'])}, edges={len(payload['edges'])}, "
            f"call_events={counters['call_events']}, "
            f"handler_errors={counters['handler_errors']})\n"
        )
        return self.output
