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
    """Answer a code-navigation question over a Python codebase using the local
    semantic-search MCP tools (search_code, find_connections, find_path,
    find_similar_code, finish). The input field
    is `question`. You must produce two outputs: `relevant_chunk_ids` (an ordered list)
    and `answer` (a concise description of what the symbol(s) do).

    WHAT search_code RETURNS
    This codebase is indexed for hybrid (semantic + lexical/BM25) retrieval. search_code
    returns ONLY metadata rows per chunk — chunk_id, kind/type, name, reranker_score,
    blended_score, score, source, centrality, complexity_score — never source bodies.
    The metadata (name + kind + file path) is enough to judge relevance. Do NOT spend
    calls trying to "confirm" a chunk's contents.

    CHUNK_ID FORMAT
    Raw results use "file.py:START-END:kind:QualifiedName"
    (e.g. "chunking/languages/base.py:227-237:method:LanguageChunker.get_node_text").
    The graded/expected form DROPS the line range:
    "file.py:kind:QualifiedName" (e.g.
    "chunking/languages/base.py:method:LanguageChunker.get_node_text").
    Either form is accepted, but be consistent and definition-accurate.

    Common `kind` values you will see: class, method, function, decorated_definition,
    split_block, module. NOTE: config objects and dataclasses frequently appear with
    kind=decorated_definition (e.g. "search/config.py:decorated_definition:SearchModeConfig",
    "merkle/change_detector.py:decorated_definition:FileChanges").

    CODE-NAVIGATION QUESTIONS ALMOST ALWAYS HAVE MULTIPLE RELEVANT CHUNKS:
    - a class PLUS the methods that implement the described behavior
    - both halves of a paired operation (encode+decode, save+load, tokenize+clean)
    - a config/dataclass PLUS its loader
    - the SAME-NAMED operation living in sibling subsystems/files
    - a backing/helper class that the named class delegates to (e.g. HybridSearcher is
      accompanied by SearchExecutor and the SearchModeConfig dataclass; a save/load
      question on FaissVectorIndex also pulls in CodeIndexManager.save_index).

    Err HARD toward inclusion. The #1 observed failure is reasoning that a chunk is
    relevant and then omitting it from `relevant_chunk_ids` — ESPECIALLY
    decorated_definition config/dataclass chunks. If a search surfaced it and it relates
    to the question's subject, INCLUDE it. The #2 failure is stopping after one search
    and missing methods/files an alternate phrasing would surface (e.g. missing
    BM25Index.search, or a paired dataclass in a different module).

    CRITICAL DISTINCTION — INCLUSION vs ORDERING (do not conflate these):
    - INCLUSION: include EVERY relevant chunk regardless of kind. A decorated_definition
      config/dataclass (SearchModeConfig, FileChanges, etc.) that your search returned
      must appear in `relevant_chunk_ids`. The "prefer class over fragment" rule below is
      about ORDER ONLY — it never justifies dropping a chunk.
    - ORDERING: a higher-scoring decorated_definition / split_block / module fragment
      must NOT outrank the canonical class/method/function definition. Lead with the
      definition-level chunk whose name most directly matches the question's core symbol.

    SEARCH STRATEGY
    1. First call: search_code with search_mode="hybrid", k=10, include_context=True.
       Phrase the query using the concrete symbol/operation names from the question.
    2. ALWAYS issue at least a SECOND search (aim for 2–3 diverse queries total) with
       alternate phrasings — synonyms, names of likely-paired symbols (the other half of
       encode/decode, save/load, the config/dataclass behind a class), likely method
       names hinted in summaries, and sibling subsystem/file names. Do this especially
       when (a) the question names a generic operation
       (validate/normalize/encode/decode/load/save/tokenize/id-handling/combine) that
       plausibly exists in multiple subsystems, or (b) your first results cluster in one
       module but the concept could live in a sibling file. You may use file_pattern to
       focus a follow-up, but ALSO run at least one UNfiltered alternate query so
       cross-module same-named chunks can surface — these are frequently expected.
       (Exception: a single tight search may already return the full paired set, e.g. a
       FaissVectorIndex save/load query returning the class + save + load + the manager's
       save_index — but still confirm with a second query before finishing.)
    3. CONNECTION / RELATIONSHIP questions ("what calls X", "what does Y call internally",
       "what depends on / inherits from Z"): first search_code to get the target chunk_id,
       then call find_connections(chunk_id=<target>). Prefer edges with higher
       resolver_confidence / source lsp|libcst (exact) over ast (heuristic). Do not answer
       call-graph questions from search_code alone. Note that internal-call targets often
       span multiple files (e.g. ChangeDetector.detect_changes_from_snapshot reaches into
       merkle_dag.MerkleDAG and its methods, snapshot_manager.SnapshotManager.load_snapshot,
       plus the FileChanges dataclass) — include all of them. EMIT EVERY RETURNED EDGE
       TARGET in relevant_chunk_ids, even cross-file ones; do not prune based on file
       location. Lead with the named symbol's canonical definition, then all connections.
    4. PATH / FLOW questions ("how does X reach Y", "trace the call path from A to B",
       "what is the execution path between X and Y"): first call search_code to resolve
       the chunk_id for BOTH the source and target symbols. Then call
       find_path(source_chunk_id=<src>, target_chunk_id=<tgt>) to retrieve the shortest
       call path between them. Emit every node on the returned path in
       relevant_chunk_ids. If find_path returns an empty path, fall back to
       find_connections on the source chunk. Lead with the source symbol's canonical
       definition, then every path node in order.
    5. SIMILARITY questions ("find implementations similar to X", "other constructors like
       Y", "code similar to Z"): first call search_code to find the seed chunk_id for the
       named symbol. Then call find_similar_code(chunk_id=<seed>) to retrieve
       structurally/semantically similar chunks. Lead ordering with the highest-similarity
       neighbors returned — these should appear first in relevant_chunk_ids, as ordering
       is critical for similarity queries (MRR is the primary signal). Include the seed
       chunk's canonical definition plus all returned similar chunks.

    RANKING WITHIN RESULTS
    Rank candidates by reranker_score first, then blended_score (higher = better).

    SELECTION (cast a wide net for recall)
    Include: the directly-named symbol; its closely-related sibling methods that implement
    the behavior; any relevant config/dataclass (even kind=decorated_definition) and its
    loader; the backing/helper class a named class delegates to; and every same-named or
    paired symbol your searches surfaced across all files. Do not prune any chunk you
    reasoned was relevant.

    ORDERING — MRR matters most for position 0
    List FIRST the definition-level chunk (class/method/function) whose name most directly
    matches the question's core symbol — never a fragment, even if the fragment scored
    higher. (E.g. lead with class:HybridSearcher, method:FaissVectorIndex.save, or
    method:LanguageChunker.get_node_text — not a decorated_definition or split_block.)

    FINISHING
    Call finish once your 2–3 searches (and any find_connections call) have surfaced the
    canonical definition plus its related/paired/cross-module/config siblings. Then output
    `relevant_chunk_ids` ordered as above (canonical definition first, every surfaced
    relevant chunk — including decorated_definition configs/dataclasses — included) and a
    concise `answer` describing what the symbol(s) do.
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
            expected_tool = ["find_connections"]
        elif category == "E":
            expected_tool = ["find_path"]
        elif category == "F":
            expected_tool = ["find_similar_code"]
        elif category in _SEARCH_CODE_CATEGORIES:
            expected_tool = ["search_code"]
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
    """DSPy metric: whether the agent used an acceptable MCP tool.

    Scores 1.0 if any tool from the ``expected_tool`` list appears anywhere in
    the ReAct trajectory (recovery across the whole trajectory, not just step 0).
    Scores 0.0 if none used.  Returns 1.0 for examples with no ``expected_tool``.

    ``expected_tool`` is a list of acceptable tool names per category:
    A/B/C → ["search_code"]; D → ["find_connections"]; E → ["find_path"];
    F → ["find_similar_code"].  Accepts either a list or a bare string for
    backwards compatibility.  Examples without an ``expected_tool`` field are
    excluded from tool-selection accuracy (counted as 1.0).

    Args:
        example: A DSPy example with an ``expected_tool`` field (list or str).
        pred: A DSPy Prediction with a ``trajectory`` dict.
        trace: Unused.

    Returns:
        1.0 (an acceptable tool used, or no expected_tool set), 0.0 otherwise.
    """
    expected = example.get("expected_tool")
    if not expected:
        return 1.0  # no expected_tool set — excluded from accuracy mean

    used = _extract_tools_from_trajectory(getattr(pred, "trajectory", None))
    acceptable = [
        t.lower() for t in (expected if isinstance(expected, list) else [expected])
    ]
    return 1.0 if any(t in used for t in acceptable) else 0.0


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
    split: str | None = None,
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
        split: Dataset split to evaluate — ``"train"``, ``"val"``, ``"test"``,
            or ``None`` (all 45 rows, default).  Pass ``"test"`` for the
            held-out evaluation; ``None`` preserves the full-dataset assertion
            in the e2e integration test.
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
    examples, thresholds = load_examples(dataset_path, split=split)
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
