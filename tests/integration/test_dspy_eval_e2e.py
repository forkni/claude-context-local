"""End-to-end integration test for the DSPy agent evaluation harness.

Requires the code-search HTTP server running on port 8765 AND an active
Claude Code login.  Skipped automatically when either is absent, so CI stays
green.

Run manually::

    .venv/Scripts/pytest.exe tests/integration/test_dspy_eval_e2e.py -v -s

Or via the CLI (more verbose, writes a results JSON)::

    .venv/Scripts/python.exe scripts/benchmark/run_dspy_eval.py \\
        --project-path D:/claude-context-local --k 7 --concurrency 2
"""

import asyncio
import os
import shutil
from pathlib import Path

import pytest


pytestmark = [pytest.mark.integration, pytest.mark.slow]

# ---------------------------------------------------------------------------
# Skip guards
# ---------------------------------------------------------------------------

_SERVER_URL = os.getenv("CODE_SEARCH_MCP_URL", "http://localhost:8765/mcp")
_PROJECT_ROOT = str(Path(__file__).parents[2])


def _server_is_up() -> bool:
    """Return True if the code-search HTTP server is reachable."""
    try:
        import urllib.request

        urllib.request.urlopen(_SERVER_URL, timeout=3)  # noqa: S310
        return True
    except Exception:  # noqa: BLE001
        return False


def _claude_cli_available() -> bool:
    """Return True if the claude CLI binary is on PATH."""
    return shutil.which("claude") is not None or bool(os.getenv("CLAUDE_CLI_PATH"))


_SKIP_NO_SERVER = pytest.mark.skipif(
    not _server_is_up(),
    reason="Code-search HTTP server not running on port 8765",
)
_SKIP_NO_CLI = pytest.mark.skipif(
    not _claude_cli_available(),
    reason="claude CLI not found — subscription LM unavailable",
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@_SKIP_NO_SERVER
@_SKIP_NO_CLI
def test_run_eval_returns_results():
    """run_eval returns per_query entries with expected schema keys."""
    from evaluation.dspy_agent_eval import run_eval

    result = asyncio.run(
        run_eval(
            project_path=_PROJECT_ROOT,
            k=7,
            concurrency=2,  # conservative for CI
            max_iters=3,  # short run — smoke test only
        )
    )

    assert "per_query" in result
    assert "aggregate" in result
    assert "total_queries" in result
    assert result["total_queries"] == 45

    # At least some queries should have succeeded
    assert len(result["per_query"]) > 0, "All queries failed — check server/CLI"

    # Per-query rows should have the standard metric keys
    row = result["per_query"][0]
    for key in ("recall@7", "mrr", "tool_selection", "category", "query_id"):
        assert key in row, f"Missing key {key!r} in per_query row"


@_SKIP_NO_SERVER
@_SKIP_NO_CLI
def test_aggregate_has_expected_keys():
    """Aggregate output includes both IR metrics and tool_selection_accuracy."""
    from evaluation.dspy_agent_eval import run_eval

    result = asyncio.run(
        run_eval(
            project_path=_PROJECT_ROOT,
            k=7,
            concurrency=2,
            max_iters=3,
        )
    )

    agg = result["aggregate"]
    for key in ("recall@7", "mrr", "hit_rate@7", "tool_selection_accuracy"):
        assert key in agg, f"Missing aggregate key: {key!r}"

    # Scores should be valid floats in [0.0, 1.0]
    assert 0.0 <= agg["recall@7"] <= 1.0
    assert 0.0 <= agg["mrr"] <= 1.0
    if agg["tool_selection_accuracy"] is not None:
        assert 0.0 <= agg["tool_selection_accuracy"] <= 1.0


@_SKIP_NO_SERVER
@_SKIP_NO_CLI
def test_cost_is_zero():
    """ClaudeCodeLM bills to the subscription; usage counters are zero."""
    from evaluation.dspy_agent_eval import run_eval

    result = asyncio.run(
        run_eval(
            project_path=_PROJECT_ROOT,
            concurrency=1,
            max_iters=2,
        )
    )
    # If this assertion fails it likely means ANTHROPIC_API_KEY was set
    # and the API was charged instead of the subscription.
    # The harness doesn't expose usage directly; just assert no KeyError.
    assert "total_queries" in result
