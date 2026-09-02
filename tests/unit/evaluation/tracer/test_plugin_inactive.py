"""The tracer plugin must leave normal test runs untouched.

``evaluation.tracer.pytest_callgraph`` is loaded only via ``-p`` and only acts
with ``--callgraph-trace``; a plain run must have no profiler installed.
"""

from __future__ import annotations

import sys

import pytest


def test_no_profiler_in_normal_run(pytestconfig: pytest.Config) -> None:
    if pytestconfig.getoption("callgraph_trace", default=False):
        pytest.skip("run is being traced on purpose")
    assert sys.getprofile() is None
    assert pytestconfig.pluginmanager.get_plugin("callgraph-tracer") is None
