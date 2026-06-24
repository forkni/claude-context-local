"""DSPy agent evaluation harness for the code-search MCP tools.

Measures whether a DSPy ReAct agent (powered by :class:`~utils.dspy_claude_code.ClaudeCodeLM`
on the Claude subscription) routes queries to the correct MCP tools and
retrieves the expected chunks, using the project's existing golden datasets
and metric functions.

Phase 1 scope: **evaluation only** — no optimization.
Phase 2 (future): GEPA optimizer over ``CodeNavQA`` instructions and tool
  descriptions in ``mcp_server/tool_registry.py``.

Example usage::

    import asyncio
    from evaluation.dspy_agent_eval import run_eval

    summary = asyncio.run(
        run_eval(project_path="D:/claude-context-local", k=7)
    )
    print(summary["aggregate"]["recall@7"])
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from statistics import mean
from typing import Any

import dspy

from evaluation.metrics import (
    aggregate_metrics,
    calculate_metrics_from_results,
    normalize_chunk_ids,
)
from utils.dspy_claude_code import ClaudeCodeLM
from utils.dspy_mcp import code_search_session


logger = logging.getLogger(__name__)

# Absolute path to the golden dataset shipped with this package.
_GOLDEN_DATASET = Path(__file__).parent / "golden_dataset.json"

# Categories whose expected tool is search_code (all categories with ground truth).
_SEARCH_CODE_CATEGORIES = {"A", "B", "C"}


# ---------------------------------------------------------------------------
# DSPy Signature
# ---------------------------------------------------------------------------


class CodeNavQA(dspy.Signature):
    """Answer a code-navigation question using the local semantic-search MCP tools.

    Use search_code to retrieve semantically relevant code chunks, then return
    the most relevant chunk IDs and a brief explanation.
    """

    question: str = dspy.InputField()
    relevant_chunk_ids: list[str] = dspy.OutputField(
        desc=(
            "Chunk IDs of the most relevant code chunks, most relevant first. "
            "Format: 'relative/path.py:chunk_type:qualified_name', e.g. "
            "'search/config.py:function:get_model_config'. "
            "Return up to 10 IDs."
        )
    )
    answer: str = dspy.OutputField(
        desc="One-line explanation of where the relevant code lives."
    )


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_examples(
    path: str | Path | None = None,
) -> tuple[list[dspy.Example], dict]:
    """Load the SSCG golden dataset as a list of DSPy examples.

    Mirrors the loader pattern in ``scripts/benchmark/run_sscg_benchmark.py``
    (plain ``json.load``; reads ``dataset["queries"]`` and
    ``dataset["thresholds"]``).

    Args:
        path: Path to a golden-dataset JSON file.  Defaults to
            ``evaluation/golden_dataset.json`` relative to this module.

    Returns:
        A tuple ``(examples, thresholds)`` where ``examples`` is a list of
        :class:`dspy.Example` objects with ``.with_inputs("question")`` and
        ``thresholds`` is the raw thresholds dict from the JSON (or ``{}``).

    Each example carries the following fields:
        - ``question`` (InputField) — the query string.
        - ``expected`` — list of relevant chunk IDs (label ≥ 2).
        - ``expected_primary`` — list of highly-relevant chunk IDs (label = 3).
        - ``category`` — ``"A"``, ``"B"``, or ``"C"``.
        - ``expected_tool`` — ``"search_code"`` for all present categories.
        - ``query_id`` — the ID string from the JSON (e.g. ``"Q01"``).
    """
    dataset_path = Path(path) if path else _GOLDEN_DATASET
    with open(dataset_path, encoding="utf-8") as fh:
        dataset = json.load(fh)

    examples = []
    for item in dataset.get("queries", []):
        category = item.get("category", "")
        expected_tool = "search_code" if category in _SEARCH_CODE_CATEGORIES else None
        ex = dspy.Example(
            question=item["query"],
            expected=item.get("expected", []),
            expected_primary=item.get("expected_primary", []),
            category=category,
            expected_tool=expected_tool,
            query_id=item.get("id", ""),
        ).with_inputs("question")
        examples.append(ex)

    thresholds = dataset.get("thresholds", {})
    logger.info(
        "Loaded %d examples from %s (thresholds=%s)",
        len(examples),
        dataset_path,
        thresholds,
    )
    return examples, thresholds


# ---------------------------------------------------------------------------
# Metric functions (DSPy-style: metric(example, pred, trace=None) -> float)
# ---------------------------------------------------------------------------


def _extract_chunk_ids(pred: Any) -> list[str]:
    """Extract and normalise chunk IDs from a DSPy Prediction.

    Tries ``pred.relevant_chunk_ids`` first (typed ``list[str]`` OutputField).
    Falls back to splitting on commas / newlines if DSPy emitted a string.

    Returns an empty list if the field is absent or empty.
    """
    raw = getattr(pred, "relevant_chunk_ids", None)
    if not raw:
        return []
    if isinstance(raw, list):
        return normalize_chunk_ids([str(c) for c in raw if c])
    if isinstance(raw, str):
        # Defensive: split on comma or newline
        parts = [p.strip().strip('"').strip("'") for p in re.split(r"[,\n]", raw)]
        return normalize_chunk_ids([p for p in parts if p])
    return []


def _extract_tools_from_trajectory(trajectory: dict | None) -> set[str]:
    """Return the set of tool names used in a ReAct trajectory.

    Scans all ``tool_name_*`` keys in the trajectory dict.  Case-insensitive.
    """
    if not trajectory:
        return set()
    tools = set()
    for key, val in trajectory.items():
        if "tool_name" in key and isinstance(val, str) and val.strip():
            tools.add(val.strip().lower())
    return tools


def recall_at_k_metric(
    example: dspy.Example,
    pred: Any,
    trace: Any = None,
    k: int = 7,
) -> float:
    """DSPy metric: Recall@k of the agent's retrieved chunk IDs.

    Wraps :func:`evaluation.metrics.calculate_metrics_from_results`.

    Args:
        example: A DSPy example with ``expected`` and ``expected_primary``.
        pred: A DSPy Prediction with ``relevant_chunk_ids``.
        trace: Unused (required by DSPy metric protocol).
        k: Recall cut-off (default 7).

    Returns:
        Recall@k in [0.0, 1.0].
    """
    retrieved = _extract_chunk_ids(pred)
    scores = calculate_metrics_from_results(
        retrieved=retrieved,
        expected=example.expected,
        expected_primary=example.get("expected_primary") or example.expected,
    )
    return float(scores.get(f"recall@{k}", 0.0))


def mrr_metric(
    example: dspy.Example,
    pred: Any,
    trace: Any = None,
) -> float:
    """DSPy metric: MRR of the agent's retrieved chunk IDs (primary relevance).

    Args:
        example: A DSPy example with ``expected_primary``.
        pred: A DSPy Prediction with ``relevant_chunk_ids``.
        trace: Unused.

    Returns:
        MRR in [0.0, 1.0].
    """
    retrieved = _extract_chunk_ids(pred)
    scores = calculate_metrics_from_results(
        retrieved=retrieved,
        expected=example.expected,
        expected_primary=example.get("expected_primary") or example.expected,
    )
    return float(scores.get("mrr", 0.0))


def tool_selection_metric(
    example: dspy.Example,
    pred: Any,
    trace: Any = None,
) -> float:
    """DSPy metric: whether the agent used the expected MCP tool.

    Scores 1.0 if the expected tool appears anywhere in the ReAct trajectory
    (recovery across the whole trajectory, not just step 0).  Scores 0.0 if
    not used.  Returns 1.0 for examples with no ``expected_tool`` (category D,
    which has no ground truth in the current dataset).

    Args:
        example: A DSPy example with an ``expected_tool`` field.
        pred: A DSPy Prediction with a ``trajectory`` dict.
        trace: Unused.

    Returns:
        1.0 (correct tool used or no ground truth), 0.0 (wrong tool used).
    """
    expected = example.get("expected_tool")
    if not expected:
        return 1.0  # no ground truth for this category — not counted

    used = _extract_tools_from_trajectory(getattr(pred, "trajectory", None))
    return 1.0 if expected.lower() in used else 0.0


# ---------------------------------------------------------------------------
# Per-query evaluation coroutine
# ---------------------------------------------------------------------------


async def _eval_one(
    example: dspy.Example,
    agent: dspy.ReAct,
    lm: ClaudeCodeLM,
    sem: asyncio.Semaphore,
    k: int,
) -> dict[str, Any] | None:
    """Evaluate a single example.  Returns a per-query metric dict or None on error."""
    async with sem:
        query_id = example.get("query_id", "?")
        try:
            logger.info("Running query %s: %r", query_id, example.question[:80])
            # dspy.context() is async-task-safe via Python contextvars: each
            # gathered task inherits a copy of the outer context, and
            # `with dspy.context(lm=lm)` overrides only this task's slot.
            with dspy.context(lm=lm):
                pred = await agent.acall(question=example.question)

            # Retrieval metrics (reuse evaluation/metrics.py — do not reimplement)
            retrieved = _extract_chunk_ids(pred)
            scores = calculate_metrics_from_results(
                retrieved=retrieved,
                expected=example.expected,
                expected_primary=example.get("expected_primary") or example.expected,
            )

            # Tool-selection metric (separate from IR metrics)
            tool_score = tool_selection_metric(example, pred)

            row: dict[str, Any] = {
                "query_id": query_id,
                "question": example.question,
                "category": example.get("category", ""),
                "expected_tool": example.get("expected_tool"),
                "tool_used": sorted(
                    _extract_tools_from_trajectory(getattr(pred, "trajectory", None))
                ),
                "tool_selection": tool_score,
                "retrieved_count": len(retrieved),
                "answer": getattr(pred, "answer", ""),
                **scores,
            }
            logger.info(
                "Query %s: recall@7=%.3f mrr=%.3f tool_sel=%.0f",
                query_id,
                scores.get("recall@7", 0.0),
                scores.get("mrr", 0.0),
                tool_score,
            )
            return row

        except Exception as exc:  # noqa: BLE001
            logger.warning("Query %s failed: %r", query_id, exc)
            return None


# ---------------------------------------------------------------------------
# Main async evaluation runner
# ---------------------------------------------------------------------------


async def run_eval(
    project_path: str,
    *,
    dataset_path: str | Path | None = None,
    k: int = 7,
    concurrency: int = 4,
    max_iters: int = 6,
    server_url: str | None = None,
    tool_names: tuple[str, ...] = ("search_code", "find_connections"),
    model: str | None = None,
    **lm_kwargs: Any,
) -> dict[str, Any]:
    """Run the DSPy agent evaluation harness over the golden dataset.

    Opens **one** :func:`~utils.dspy_mcp.code_search_session` shared across
    all queries (warm server, no repeated connection setup), then runs all
    examples concurrently bounded by an :class:`asyncio.Semaphore`.

    All calls stay on a single event loop that owns the MCP session — do NOT
    use ``asyncio.run`` inside a running loop (run from a script via
    ``asyncio.run(run_eval(...))``.

    Args:
        project_path: Absolute path to the already-indexed project directory.
        dataset_path: Path to the golden-dataset JSON.  Defaults to
            ``evaluation/golden_dataset.json``.
        k: Recall cut-off for reporting (default 7).
        concurrency: Maximum parallel agent calls (default 4).
        max_iters: Maximum DSPy ReAct iterations per query (default 6).
        server_url: Override the MCP HTTP server URL.  Default:
            ``http://localhost:8765/mcp`` (or ``CODE_SEARCH_MCP_URL`` env).
        tool_names: Which MCP tools to expose to the agent.
        model: Claude model ID.  Falls back to ``DSPY_LM_MODEL`` then
            ``"claude-sonnet-4-6"``.
        **lm_kwargs: Extra kwargs forwarded to
            :class:`~utils.dspy_claude_code.ClaudeCodeLM`.

    Returns:
        A dict with:
            - ``per_query``: list of per-query metric dicts (None rows omitted).
            - ``aggregate``: aggregate stats from
              :func:`~evaluation.metrics.aggregate_metrics` plus
              ``tool_selection_accuracy`` (mean of per-query tool_selection
              for examples that have an ``expected_tool``).
            - ``failed_count``: number of queries that raised an exception.
            - ``total_queries``: total input queries.
    """
    examples, thresholds = load_examples(dataset_path)
    lm = ClaudeCodeLM(model=model, **lm_kwargs)
    sem = asyncio.Semaphore(concurrency)

    session_kwargs: dict[str, Any] = {
        "project_path": project_path,
        "tool_names": tool_names,
    }
    if server_url is not None:
        session_kwargs["server_url"] = server_url

    async with code_search_session(**session_kwargs) as (_, dspy_tools):
        agent = dspy.ReAct(CodeNavQA, tools=dspy_tools, max_iters=max_iters)

        rows = await asyncio.gather(
            *[_eval_one(ex, agent, lm, sem, k) for ex in examples]
        )

    per_query = [r for r in rows if r is not None]
    failed = len(rows) - len(per_query)

    # Standard IR aggregate (uses the fixed float_keys from aggregate_metrics)
    agg = aggregate_metrics(per_query, thresholds=thresholds) if per_query else {}

    # Tool-selection accuracy — only over examples that have expected_tool
    # (aggregate_metrics doesn't handle custom keys, so we compute separately)
    scored = [r["tool_selection"] for r in per_query if r.get("expected_tool")]
    agg["tool_selection_accuracy"] = round(mean(scored), 4) if scored else None

    return {
        "per_query": per_query,
        "aggregate": agg,
        "failed_count": failed,
        "total_queries": len(examples),
    }
