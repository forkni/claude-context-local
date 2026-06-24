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
    calculate_recall_at_k,
    normalize_chunk_ids,
)
from utils.dspy_claude_code import ClaudeCodeLM
from utils.dspy_mcp import code_search_session


logger = logging.getLogger(__name__)

# Absolute path to the golden dataset shipped with this package.
_GOLDEN_DATASET = Path(__file__).parent / "golden_dataset.json"

# Categories whose expected tool is search_code (A/B/C).
# Category D uses find_connections instead (connection/relationship queries).
_SEARCH_CODE_CATEGORIES = {"A", "B", "C"}


# ---------------------------------------------------------------------------
# DSPy Signature
# ---------------------------------------------------------------------------


class CodeNavQA(dspy.Signature):
    """Answer a code-navigation question using the local semantic-search MCP tools.

    Code-navigation questions typically have MULTIPLE relevant locations: a class and
    its methods, both halves of a paired operation (encode + decode), a config struct
    and its loader, same-named symbols across multiple subsystems, etc.  Err HARD toward
    inclusion — when in doubt, include the chunk.

    Search strategy:
    1. Call search_code with search_mode="hybrid", k=10, include_context=True.
       Phrase the query with the key symbol/operation names from the question.
       search_code returns metadata rows (chunk_id, type, name, scores) — the response
       does NOT include source bodies.  Do NOT burn extra calls to "confirm" chunk content.
    2. Rank by reranker_score first, then blended_score (higher = better).
    3. Issue a SECOND search with alternate phrasings whenever the question describes a
       generic operation (validate/normalize/encode/decode/load/save/id-handling) that
       could exist in multiple subsystems, or when the first result set is concentrated in
       one module but the concept plausibly also lives in a sibling file.  Use synonyms,
       the names of likely-related symbols/files, and subsystem names as the second query.
       Aim for at least 2–3 diverse queries; do NOT finish after one.
    4. For connection/relationship questions ("what calls X", "what does Y depend on",
       "what inherits from Z"): first use search_code to locate the target chunk_id, then
       call find_connections(chunk_id=<target_id>) to enumerate callers, callees, and
       subclasses.  find_connections returns edges with resolver_confidence — prefer
       lsp/libcst edges (exact) over ast edges (heuristic).  Do NOT attempt to answer
       call-graph questions from search_code results alone.

    Selection (cast a wide net):
    Include the directly-named symbol AND closely-related siblings (definition + methods
    implementing the behavior), relevant config/dataclass chunks, and same-named symbols
    across multiple files.  Include every plausibly-relevant chunk your searches surfaced;
    the most common failure is treating a chunk as relevant in reasoning and then omitting it.

    Ordering — MRR (position 0 matters most):
    Lead with the DEFINITION-level chunk whose name most directly matches the question's
    core symbol.  Prefer class or method/function chunks over split_block, module, or
    decorated_definition fragments — even when those fragments score high.  Do NOT let a
    high-scoring fragment outrank the canonical definition.
    """

    question: str = dspy.InputField()
    relevant_chunk_ids: list[str] = dspy.OutputField(
        desc=(
            "Return EVERY chunk_id from your search results that is relevant to the "
            "question — a class AND its methods, both halves of a paired operation, a "
            "config AND its loader, same-named symbols across subsystems.  Prefer recall: "
            "when unsure whether a result is relevant, INCLUDE it.  Do NOT return only "
            "the single best match. "
            "Copy the 'chunk_id' field VERBATIM from each relevant search_code result "
            "(including its line-range segment, e.g. "
            "'search/config.py:148-161:decorated_definition:EmbeddingConfig'). "
            "Scoring matches on file:type:name only (line numbers are ignored) but always "
            "copy chunk_ids verbatim.  Do NOT rewrite, abbreviate, or reformat them. "
            "Lead with the canonical class/method/function chunk whose name most directly "
            "matches the question — never a split_block, module, or decorated_definition "
            "fragment — then remaining relevant chunks in descending relevance. "
            "Return up to 12 IDs."
        )
    )
    answer: str = dspy.OutputField(
        desc=(
            "Brief (1–2 sentence) explanation naming the primary file(s)/symbol(s) "
            "and what each does in relation to the question."
        )
    )


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------


def load_examples(
    path: str | Path | None = None,
    split: str | None = None,
) -> tuple[list[dspy.Example], dict]:
    """Load the SSCG golden dataset as a list of DSPy examples.

    Mirrors the loader pattern in ``scripts/benchmark/run_sscg_benchmark.py``
    (plain ``json.load``; reads ``dataset["queries"]`` and
    ``dataset["thresholds"]``).

    Args:
        path: Path to a golden-dataset JSON file.  Defaults to
            ``evaluation/golden_dataset.json`` relative to this module.
        split: Optional split filter — ``"train"``, ``"val"``, or ``"test"``.
            When ``None`` (default) all rows are returned (back-compatible).
            Rows without a ``split`` field are included in all splits.

    Returns:
        A tuple ``(examples, thresholds)`` where ``examples`` is a list of
        :class:`dspy.Example` objects with ``.with_inputs("question")`` and
        ``thresholds`` is the raw thresholds dict from the JSON (or ``{}``).

    Each example carries the following fields:
        - ``question`` (InputField) — the query string.
        - ``expected`` — list of relevant chunk IDs (label ≥ 2).
        - ``expected_primary`` — list of highly-relevant chunk IDs (label = 3).
        - ``category`` — ``"A"``, ``"B"``, ``"C"``, or ``"D"``.
        - ``expected_tool`` — ``"search_code"`` for A/B/C; ``"find_connections"``
          for D (connection/relationship queries).
        - ``query_id`` — the ID string from the JSON (e.g. ``"Q01"``).
        - ``split`` — ``"train"``, ``"val"``, or ``"test"`` (when present).
    """
    dataset_path = Path(path) if path else _GOLDEN_DATASET
    with open(dataset_path, encoding="utf-8") as fh:
        dataset = json.load(fh)

    examples = []
    for item in dataset.get("queries", []):
        # Apply split filter when requested; rows without a split field pass through.
        if split is not None:
            row_split = item.get("split")
            if row_split is not None and row_split != split:
                continue

        category = item.get("category", "")
        if category == "D":
            expected_tool = "find_connections"
        elif category in _SEARCH_CODE_CATEGORIES:
            expected_tool = "search_code"
        else:
            expected_tool = None

        ex = dspy.Example(
            question=item["query"],
            expected=item.get("expected", []),
            expected_primary=item.get("expected_primary", []),
            category=category,
            expected_tool=expected_tool,
            query_id=item.get("id", ""),
            split=item.get("split", ""),
        ).with_inputs("question")
        examples.append(ex)

    thresholds = dataset.get("thresholds", {})
    logger.info(
        "Loaded %d examples from %s (split=%s, thresholds=%s)",
        len(examples),
        dataset_path,
        split or "all",
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
# Trajectory-recall diagnostic helpers
# ---------------------------------------------------------------------------

# Matches "chunk_id": "..." in JSON (compact / verbose format).
_CHUNK_ID_RE = re.compile(r'"chunk_id"\s*:\s*"([^"]+)"')

# Ultra format: results[N]{field1,...,chunk_id,...,fieldM} header tells column index.
_ULTRA_HEADER_RE = re.compile(r'"results\[\d+\]\{([^}]+)\}"')


def _parse_ultra_chunk_ids(text: str) -> list[str]:
    """Extract chunk_ids from search_code ultra-format observations.

    Ultra format encodes results as ``{"results[N]{col1,col2,...}": [[v1,v2,...], ...]}``.
    This function locates the ``chunk_id`` column index from the header and reads
    that column from every result row.
    """
    m = _ULTRA_HEADER_RE.search(text)
    if not m:
        return []
    columns = [c.strip() for c in m.group(1).split(",")]
    if "chunk_id" not in columns:
        return []
    idx = columns.index("chunk_id")
    # Extract arrays that are values of the header key
    # Quick approach: find all quoted strings at the right position in each row
    # Full parse is safer but heavy; use a targeted regex instead.
    # Pattern: inside a row array, grab the (idx+1)-th quoted string.
    chunk_ids: list[str] = []
    try:
        data = json.loads(text)
        for header_key, rows in data.items():
            if "chunk_id" in header_key and isinstance(rows, list):
                for row in rows:
                    if isinstance(row, list) and idx < len(row):
                        val = row[idx]
                        if isinstance(val, str) and val:
                            chunk_ids.append(val)
    except (json.JSONDecodeError, TypeError, KeyError):
        pass
    return chunk_ids


def _extract_chunk_ids_from_observations(trajectory: dict | None) -> list[str]:
    """Extract and normalise every chunk_id surfaced by tool calls in a trajectory.

    Scans all ``observation_*`` values in the ReAct trajectory dict for JSON
    ``"chunk_id": "..."`` patterns (robust across compact/verbose/ultra output
    formats).  Applies :func:`evaluation.metrics.normalize_chunk_ids` so the
    result can be compared directly against golden chunk IDs.

    This is the **tool ceiling** — the maximum recall the agent *could* achieve
    from the observations it was given, before its own ID selection/transcription.

    Returns:
        Deduplicated normalised chunk IDs in order of first appearance; ``[]``
        if the trajectory is absent or no tool calls were made.
    """
    if not trajectory:
        return []
    raw: list[str] = []
    for key, val in trajectory.items():
        if "observation" not in key:
            continue
        # Observation may arrive as a raw JSON string (search_code compact output)
        # or, if DSPy converts the result, as a Python repr string.  Coerce to str
        # so isinstance(val, str) never silently skips a dict/list observation.
        val_str = val if isinstance(val, str) else json.dumps(val, default=str)
        found = _CHUNK_ID_RE.findall(val_str)
        if not found:
            # Fallback: single-quoted repr format ("'chunk_id': 'path'")
            found = re.findall(r"'chunk_id'\s*:\s*'([^']+)'", val_str)
            if not found:
                # Ultra format: column header "...chunk_id..." with positional values
                found = _parse_ultra_chunk_ids(val_str)
        logger.debug(
            "Observation %r: found %d chunk_id(s); val type=%s, preview=%r",
            key,
            len(found),
            type(val).__name__,
            (val_str[:120] if isinstance(val_str, str) else repr(val_str)[:120]),
        )
        raw.extend(found)
    return normalize_chunk_ids(raw) if raw else []


def trajectory_recall_metric(
    example: dspy.Example,
    pred: Any,
    trace: Any = None,
    k: int = 7,
) -> float:
    """DSPy metric: Recall@k of chunks **surfaced by tools** (tool ceiling).

    Measures how much relevant material the tool calls actually retrieved,
    independent of what the agent chose to copy into its final answer.
    Useful for separating tool-quality failures from agent ID-fidelity failures.

    gap = trajectory_recall - recall_at_k_metric  →  agent dropped a surfaced ID
    1 − trajectory_recall                          →  tool never retrieved the chunk

    Args:
        example: A DSPy example with ``expected`` and ``expected_primary``.
        pred: A DSPy Prediction with a ``trajectory`` dict containing observations.
        trace: Unused.
        k: Recall cut-off (default 7).

    Returns:
        Unranked recall of the surfaced set in [0.0, 1.0].  Uses ``k = len(surfaced)``
        so ordering within the observation string (which places module/community
        summary chunks first) does not hide method-level chunks at position 8+.
    """
    surfaced = _extract_chunk_ids_from_observations(getattr(pred, "trajectory", None))
    # Ceiling metric: any chunk the tool surfaced counts, regardless of position.
    ceiling_k = max(len(surfaced), k)
    return float(calculate_recall_at_k(surfaced, example.expected, k=ceiling_k))


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
            traj = getattr(pred, "trajectory", None)
            retrieved = _extract_chunk_ids(pred)
            scores = calculate_metrics_from_results(
                retrieved=retrieved,
                expected=example.expected,
                expected_primary=example.get("expected_primary") or example.expected,
            )

            # Trajectory (tool ceiling) — what the tools actually surfaced
            # Use k = len(surfaced) (unranked) so module/summary chunks in the
            # first few positions of the raw observation don't mask method chunks
            # that appear later in the same search result set.
            surfaced = _extract_chunk_ids_from_observations(traj)
            ceiling_k = max(len(surfaced), k)
            traj_recall = float(
                calculate_recall_at_k(surfaced, example.expected, k=ceiling_k)
            )

            # Tool-selection metric (separate from IR metrics)
            tool_score = tool_selection_metric(example, pred)

            row: dict[str, Any] = {
                "query_id": query_id,
                "question": example.question,
                "category": example.get("category", ""),
                "expected_tool": example.get("expected_tool"),
                "tool_used": sorted(_extract_tools_from_trajectory(traj)),
                "tool_selection": tool_score,
                "retrieved_count": len(retrieved),
                # Diagnostic IDs — allow inspection without re-running the query
                "emitted_ids": retrieved,
                "surfaced_ids": surfaced,
                f"trajectory_recall@{k}": traj_recall,
                "answer": getattr(pred, "answer", ""),
                **scores,
            }
            logger.info(
                "Query %s: recall@7=%.3f traj_recall@7=%.3f mrr=%.3f tool_sel=%.0f",
                query_id,
                scores.get("recall@7", 0.0),
                traj_recall,
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
              Each row includes ``emitted_ids`` (normalised ``relevant_chunk_ids``),
              ``surfaced_ids`` (chunk IDs extracted from tool observations), and
              ``trajectory_recall@k`` (tool ceiling recall).
            - ``aggregate``: aggregate stats from
              :func:`~evaluation.metrics.aggregate_metrics` plus
              ``tool_selection_accuracy`` (mean tool_selection for A/B/C examples)
              and ``trajectory_recall@k`` (mean tool-ceiling recall).
              ``trajectory_recall − recall@k`` measures agent ID-fidelity loss;
              ``1 − trajectory_recall`` measures residual tool miss.
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

    # Trajectory recall — tool ceiling (what search_code surfaced, regardless of
    # what the agent copied into its final answer).  Averaged over succeeded rows.
    traj_key = f"trajectory_recall@{k}"
    traj_vals = [r[traj_key] for r in per_query if traj_key in r]
    agg[traj_key] = round(mean(traj_vals), 4) if traj_vals else None

    return {
        "per_query": per_query,
        "aggregate": agg,
        "failed_count": failed,
        "total_queries": len(examples),
    }
