"""GEPA (Genetic-Pareto reflective prompt optimizer) harness for CodeNavQA.

Drives ``dspy.GEPA`` to evolve the ``CodeNavQA`` signature instructions toward
higher Recall@7, using the project's golden dataset as trainset.

Key design decisions
--------------------
*Async→sync bridge.*  The MCP ``ClientSession`` (opened via
:func:`~utils.dspy_mcp.code_search_session`) is bound to one asyncio event loop.
``dspy.GEPA.compile()`` is synchronous and spawns worker threads.  The
:func:`gepa_tool_bridge` context manager solves this by running the event loop in
a daemon thread, entering the session there, and exposing **synchronous** tool
wrappers that marshal calls via :func:`asyncio.run_coroutine_threadsafe`.  A
single :class:`threading.Lock` serialises MCP I/O (the session cannot serve two
in-flight requests simultaneously); the expensive ``claude -p`` LM calls still
run in parallel.

*Train/val split.*  The golden dataset has 45 queries with a ``split`` field
(``"train"``/``"val"``/``"test"``).  GEPA uses the train split (27 rows) for
optimisation and the val split (10 rows) for evaluation; ``run_dspy_eval.py``
reports the held-out test split (8 rows) as the final generalisation check.

*Subscription billing.*  Both the rollout LM (``claude-sonnet-4-6``) and the
reflection LM (``claude-opus-4-8``) are driven through
:class:`~utils.dspy_claude_code.ClaudeCodeLM`, which strips ``ANTHROPIC_API_KEY``
so all calls bill to the Claude Code Max subscription.

Usage::

    from pathlib import Path
    from evaluation.dspy_gepa_optimize import run_gepa_optimization

    result = run_gepa_optimization(
        "D:/claude-context-local",
        budget="light",
        reflection_model="claude-opus-4-8",
        output_dir=Path("results"),
    )
    print(result["best_score"])
    print(result["optimized_instruction"])

Prerequisite: The code-search HTTP server must be running on port 8765 and
the project must be indexed.  No ``ANTHROPIC_API_KEY`` in env.
Set ``CLAUDE_CODE_RETRY_WATCHDOG=1`` and ``CLAUDE_CODE_OAUTH_TOKEN`` for long runs.
"""

import asyncio
import json
import logging
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import dspy

from evaluation.dspy_agent_eval import (
    CodeNavQA,
    _extract_chunk_ids,
    _extract_chunk_ids_from_observations,
    load_examples,
)
from evaluation.metrics import calculate_recall_at_k, normalize_chunk_ids
from utils.dspy_claude_code import ClaudeCodeLM
from utils.dspy_mcp import code_search_session


logger = logging.getLogger(__name__)

# Default MCP server URL (mirrors utils/dspy_mcp.py default).
_DEFAULT_SERVER_URL = "http://localhost:8765/mcp"

# GEPA metric uses Recall@7 — the same k as the eval harness.
_RECALL_K = 7


# ---------------------------------------------------------------------------
# Async→sync bridge
# ---------------------------------------------------------------------------


@contextmanager
def gepa_tool_bridge(
    project_path: str,
    *,
    server_url: str = _DEFAULT_SERVER_URL,
    tool_names: tuple[str, ...] = ("search_code", "find_connections"),
    tool_timeout_s: float = 120.0,
):
    """Synchronous context manager: expose MCP tools as sync callables.

    Opens the ``code_search_session`` on a background asyncio loop (daemon
    thread) and yields synchronous ``dspy.Tool`` objects whose ``func`` is a
    plain callable that marshals each call to the session loop via
    :func:`asyncio.run_coroutine_threadsafe`.

    A :class:`threading.Lock` serialises all MCP requests so the single
    ``ClientSession`` is never called concurrently.  GEPA's LM calls (the
    expensive ``claude -p`` subprocess invocations) still run in parallel —
    only tool I/O is serialised.

    Observation strings for timeout / exception mirror ``_with_timeout``'s
    format: ``"Execution error in <tool>: <reason>"``.

    Args:
        project_path: Absolute path to the indexed project directory.
        server_url: Full URL of the MCP HTTP endpoint (must include ``/mcp``).
        tool_names: MCP tool names to expose.  Keep to read-only search tools.
        tool_timeout_s: Per-call timeout forwarded to ``code_search_session``.

    Yields:
        List of synchronous ``dspy.Tool`` objects.
    """
    loop = asyncio.new_event_loop()
    session_ready = threading.Event()
    session_error: list[Exception] = []
    cleanup_signal = threading.Event()

    # The MCP session lifecycle lives on this lock so the single session is
    # never entered from two worker threads simultaneously.
    mcp_lock = threading.Lock()

    # Will be populated before session_ready is set.
    async_tools_ref: list[Any] = []

    async def _session_lifecycle() -> None:
        try:
            async with code_search_session(
                project_path=project_path,
                server_url=server_url,
                tool_names=tool_names,
                tool_timeout_s=tool_timeout_s,
            ) as (_, dspy_tools):
                async_tools_ref.extend(dspy_tools)
                session_ready.set()
                # Wait until the outer sync context exits.
                while not cleanup_signal.is_set():
                    await asyncio.sleep(0.1)
        except Exception as exc:  # noqa: BLE001
            session_error.append(exc)
            session_ready.set()  # unblock the waiter so it can raise

    def _run_loop() -> None:
        loop.run_until_complete(_session_lifecycle())
        loop.close()

    bg_thread = threading.Thread(target=_run_loop, daemon=True)
    bg_thread.start()
    session_ready.wait()

    if session_error:
        cleanup_signal.set()
        bg_thread.join(timeout=5)
        raise session_error[0]

    # Build synchronous dspy.Tool wrappers around the async tools.
    sync_tools: list[dspy.Tool] = []
    for async_tool in async_tools_ref:
        _tool_name = async_tool.name
        _async_func = async_tool.func  # the async callable

        def _make_sync_func(tool_name: str, async_func: Any) -> Any:
            def _sync_func(**kwargs: Any) -> Any:
                with mcp_lock:
                    future = asyncio.run_coroutine_threadsafe(
                        async_func(**kwargs), loop
                    )
                    try:
                        return future.result(timeout=tool_timeout_s + 5)
                    except TimeoutError:
                        future.cancel()  # prevent coroutine leak on the loop
                        msg = (
                            f"Execution error in {tool_name}: "
                            f"timeout after {tool_timeout_s:.0f}s"
                        )
                        logger.warning(
                            "Bridge tool %r timed out after %.0fs",
                            tool_name,
                            tool_timeout_s,
                        )
                        return msg
                    except Exception as exc:  # noqa: BLE001
                        msg = f"Execution error in {tool_name}: {exc}"
                        logger.warning("Bridge tool %r raised %r", tool_name, exc)
                        return msg

            return _sync_func

        sync_func = _make_sync_func(_tool_name, _async_func)
        # Copy the async_tool but replace func with the sync wrapper.
        # dspy.Tool stores name, desc, args, func.
        sync_tool = dspy.Tool(
            func=sync_func,
            name=async_tool.name,
            desc=async_tool.desc,
            args=async_tool.args,
        )
        sync_tools.append(sync_tool)

    logger.info(
        "GEPA bridge ready: %d sync tool(s) backed by session loop",
        len(sync_tools),
    )

    try:
        yield sync_tools
    finally:
        cleanup_signal.set()
        bg_thread.join(timeout=15)
        logger.info("GEPA bridge closed.")


# ---------------------------------------------------------------------------
# Feedback metric
# ---------------------------------------------------------------------------


def gepa_metric(
    gold: Any,
    pred: Any,
    trace: Any = None,
    pred_name: Any = None,
    pred_trace: Any = None,
) -> dspy.Prediction:
    """GEPA 5-arg metric: Recall@7 score + textual feedback for reflection.

    GEPA requires a 5-argument callable.  The 5th argument (``pred_trace``) is
    asserted to exist at ``dspy.GEPA`` construction time.

    The feedback string is the key lever for GEPA's reflection step.  It
    follows the HotpotQA "list hit/missed docs" recipe from the GEPA docs:
    explicitly naming the chunk_ids the agent surfaced but dropped is far more
    actionable than a bare numeric score.

    Args:
        gold: A ``dspy.Example`` with ``gold.expected`` (list of chunk IDs).
        pred: A ``dspy.Prediction`` with ``relevant_chunk_ids`` and optionally
            a ``trajectory`` dict.
        trace: DSPy internal (unused).
        pred_name: DSPy internal (unused — metric returns consistent score).
        pred_trace: DSPy internal (unused).

    Returns:
        ``dspy.Prediction(score=float, feedback=str)`` where ``score`` is
        Recall@7 in [0, 1].
    """
    # normalize_chunk_ids is idempotent — golden_dataset IDs are already
    # line-range-stripped but raw IDs (e.g. from tests) are handled too.
    expected = set(normalize_chunk_ids(list(getattr(gold, "expected", []) or [])))
    emitted = set(_extract_chunk_ids(pred))
    surfaced = set(
        _extract_chunk_ids_from_observations(getattr(pred, "trajectory", None))
    )

    score = calculate_recall_at_k(list(emitted), list(expected), k=_RECALL_K)

    # ---- Categorise chunk IDs -----------------------------------------------
    hits = expected & emitted
    dropped = (expected - emitted) & surfaced
    never_surfaced = expected - emitted - surfaced

    # ---- Build feedback string -----------------------------------------------
    parts: list[str] = []
    parts.append(
        f"Recall@{_RECALL_K} = {score:.3f}  ({len(hits)}/{len(expected)} expected chunks retrieved)."
    )

    if hits:
        parts.append(
            "CORRECT: the following expected chunk_ids were in your answer — "
            "keep returning these:\n  " + "\n  ".join(sorted(hits))
        )

    if dropped:
        parts.append(
            "MISSED (surfaced but omitted): your search_code calls RETURNED these "
            "relevant chunk_ids but you did NOT include them in relevant_chunk_ids. "
            "Always include every relevant chunk your searches returned:\n  "
            + "\n  ".join(sorted(dropped))
        )

    if never_surfaced:
        parts.append(
            "MISSED (never surfaced): these expected chunk_ids were NOT found by "
            "your search calls at all.  Try broader or alternate search queries:\n  "
            + "\n  ".join(sorted(never_surfaced))
        )

    # Remind the LM that MRR matters too — don't regress rank-1.
    if emitted and list(emitted)[0] not in expected and hits:
        best_hit = sorted(hits)[0]
        parts.append(
            f"MRR note: your first listed chunk_id was not in the expected set. "
            f"List the most relevant chunk first (e.g. {best_hit!r}) to improve MRR."
        )

    feedback = "\n\n".join(parts)
    return dspy.Prediction(score=score, feedback=feedback)


# ---------------------------------------------------------------------------
# Optimisation runner
# ---------------------------------------------------------------------------


def run_gepa_optimization(
    project_path: str,
    *,
    budget: str | None = "light",
    max_full_evals: int | None = None,
    max_metric_calls: int | None = None,
    reflection_model: str = "claude-opus-4-8",
    rollout_model: str | None = None,
    num_threads: int = 4,
    max_iters: int = 6,
    output_dir: Path | str = Path("results"),
    server_url: str = _DEFAULT_SERVER_URL,
) -> dict[str, Any]:
    """Run GEPA to evolve the ``CodeNavQA`` instructions for higher Recall@7.

    Runs ``dspy.GEPA`` with the train split (27 queries) and validates on the
    val split (10 queries) from the golden dataset (45 queries total).  The
    held-out test split (8 queries) is reserved for ``run_dspy_eval.py``.
    The discovered instruction should be compared to the hand-written seed in
    ``evaluation/dspy_agent_eval.py``.

    Both rollout and reflection LMs use :class:`~utils.dspy_claude_code.ClaudeCodeLM`
    (subscription billing; no ``ANTHROPIC_API_KEY`` required).

    Args:
        project_path: Absolute path to the indexed project directory.
        budget: GEPA ``auto`` preset — ``"light"`` (6), ``"medium"`` (12),
            or ``"heavy"`` (18) candidate evaluations.  Ignored when
            ``max_full_evals`` or ``max_metric_calls`` is set.
        max_full_evals: Explicit full-evaluation cap passed as
            ``dspy.GEPA(max_full_evals=...)``.  Computes metric calls as
            ``max_full_evals × (len(trainset) + len(valset))``, e.g. 5 → 185
            on train=27 / val=10.  Overrides ``budget`` when set.
        max_metric_calls: Hard rollout ceiling passed directly to GEPA.
            Overrides both ``budget`` and ``max_full_evals`` when set.
        reflection_model: Claude model for GEPA's reflective step.
            Default ``"claude-opus-4-8"`` (strong instruction proposer).
        rollout_model: Claude model for agent rollouts.  ``None`` falls back
            to ``DSPY_LM_MODEL`` env var then ``"claude-sonnet-4-6"``.
        num_threads: GEPA worker threads.  Keep ≤ 4; MCP I/O is serialised on
            the single session but LM calls run in parallel.
        max_iters: Max ReAct iterations per rollout.
        output_dir: Directory for GEPA artifacts (program JSON + stats JSON).
            Defaults to ``results/`` which is gitignored.
        server_url: Full MCP HTTP endpoint URL (must include ``/mcp``).

    Returns:
        Dict with keys:
            ``seed_score`` — Recall@7 of the unoptimised student on trainset.
            ``best_score``  — best Recall@7 found by GEPA.
            ``optimized_instruction`` — the evolved signature instructions text.
            ``artifact_paths`` — list of saved artifact paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Timestamp for artifact filenames (caller stamps after the workflow returns
    # — computed here in the sync context so it's deterministic for the run).
    import time as _time

    ts = _time.strftime("%Y%m%d_%H%M%S")

    logger.info(
        "GEPA: using train/val split from golden dataset (train=27, val=10, test=8 held out)."
    )

    # Load golden dataset — train and val splits separately.
    examples, _thresholds = load_examples(split="train")
    val_examples, _ = load_examples(split="val")
    logger.info(
        "GEPA: loaded %d train examples, %d val examples.",
        len(examples),
        len(val_examples),
    )

    # Configure the global DSPy LM for rollouts.
    task_lm = ClaudeCodeLM(model=rollout_model)
    dspy.configure(lm=task_lm)
    logger.info("GEPA: rollout LM = %s", task_lm.model)

    # Reflection LM — opus for stronger instruction proposals; longer timeout.
    reflection_lm = ClaudeCodeLM(model=reflection_model, timeout=600)
    logger.info("GEPA: reflection LM = %s", reflection_lm.model)

    # Build GEPA log dir.
    log_dir = output_dir / "gepa_logs" / ts
    log_dir.mkdir(parents=True, exist_ok=True)

    artifact_paths: list[str] = []

    with gepa_tool_bridge(
        project_path=project_path,
        server_url=server_url,
        tool_timeout_s=45.0,
    ) as sync_tools:
        student = dspy.ReAct(CodeNavQA, tools=sync_tools, max_iters=max_iters)  # pyrefly: ignore[bad-argument-type]  # DSPy stub requires Callable but list[Tool] is the real API

        # Resolve budget: explicit knobs take priority over the auto preset.
        # dspy.GEPA enforces exactly-one-of {auto, max_full_evals, max_metric_calls}.
        if max_metric_calls is not None:
            budget_kwargs: dict[str, Any] = {"max_metric_calls": max_metric_calls}
        elif max_full_evals is not None:
            budget_kwargs = {"max_full_evals": max_full_evals}
        else:
            budget_kwargs = {"auto": budget}
        logger.info("GEPA: budget_kwargs=%s", budget_kwargs)

        gepa = dspy.GEPA(
            metric=gepa_metric,  # pyrefly: ignore[bad-argument-type]  # DSPy GEPA stub uses GEPAFeedbackMetric; callable metric is valid at runtime
            **budget_kwargs,
            reflection_lm=reflection_lm,  # pyrefly: ignore[bad-argument-type]  # DSPy stub expects LM | None; ClaudeCodeLM inherits BaseLM at runtime
            num_threads=num_threads,
            track_stats=True,
            log_dir=str(log_dir),
            seed=0,
        )
        logger.info(
            "GEPA: starting compile (budget=%s, num_threads=%d)…", budget, num_threads
        )

        optimized = gepa.compile(
            student,
            trainset=examples,
            valset=val_examples,
        )

    # Extract the evolved instruction.
    # dspy.ReAct wraps the signature in a predict module; access via
    # optimized.predict.signature or optimized.react.signature depending on version.
    optimized_instruction: str = ""
    for attr_name in ("predict", "react", "module"):
        predictor = getattr(optimized, attr_name, None)
        if predictor is not None:
            sig = getattr(predictor, "signature", None)
            if sig is not None:
                optimized_instruction = getattr(sig, "instructions", "")
                if optimized_instruction:
                    break
    if not optimized_instruction:
        # Fallback: walk all sub-modules for a Signature.
        for name, mod in optimized.named_sub_modules():
            sig = getattr(mod, "signature", None)
            if sig is not None:
                candidate = getattr(sig, "instructions", "")
                if candidate:
                    optimized_instruction = candidate
                    logger.info("Found evolved instruction in sub-module %r.", name)
                    break

    # Extract scores from detailed_results.
    seed_score: float = 0.0
    best_score: float = 0.0
    if (
        hasattr(optimized, "detailed_results")
        and optimized.detailed_results is not None
    ):
        dr = optimized.detailed_results
        val_scores = getattr(dr, "val_aggregate_scores", None)
        if val_scores:
            best_score = float(max(val_scores))
            seed_score = float(val_scores[0]) if val_scores else 0.0
        logger.info(
            "GEPA detailed_results: best_idx=%s, total_metric_calls=%s",
            getattr(dr, "best_idx", "?"),
            getattr(dr, "total_metric_calls", "?"),
        )

    # Save the optimised program.
    gepa_dir = output_dir / "gepa"
    gepa_dir.mkdir(parents=True, exist_ok=True)
    program_path = gepa_dir / f"optimized_codenavqa_{ts}.json"
    try:
        optimized.save(str(program_path))
        artifact_paths.append(str(program_path))
        logger.info("Saved optimised program → %s", program_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not save optimised program: %r", exc)

    # Save a human-readable summary.
    stats_path = gepa_dir / f"gepa_stats_{ts}.json"
    stats: dict[str, Any] = {
        "timestamp": ts,
        "project_path": project_path,
        "budget": budget_kwargs,
        "rollout_model": task_lm.model,
        "reflection_model": reflection_model,
        "num_threads": num_threads,
        "max_iters": max_iters,
        "seed_score": seed_score,
        "best_score": best_score,
        "optimized_instruction": optimized_instruction,
    }
    if (
        hasattr(optimized, "detailed_results")
        and optimized.detailed_results is not None
    ):
        dr = optimized.detailed_results
        stats["best_idx"] = getattr(dr, "best_idx", None)
        stats["val_aggregate_scores"] = getattr(dr, "val_aggregate_scores", None)
        stats["total_metric_calls"] = getattr(dr, "total_metric_calls", None)

    with open(stats_path, "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2, default=str)
    artifact_paths.append(str(stats_path))
    logger.info("Saved GEPA stats → %s", stats_path)

    return {
        "seed_score": seed_score,
        "best_score": best_score,
        "optimized_instruction": optimized_instruction,
        "artifact_paths": artifact_paths,
    }
