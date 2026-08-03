#!/usr/bin/env python3
"""SSCG Automated Benchmark Runner.

Evaluates retrieval quality against the SSCG golden dataset (77 queries: categories A-F).
Supports single-run evaluation and parameter sweep (config comparison).

Inspired by DeepLearning.AI "Building and Evaluating Advanced RAG" patterns:
  - Lesson 1: eval loop  (query -> retrieve -> score)
  - Lesson 2: leaderboard + per-query drill-down
  - Lesson 3: parameter sweep (sweep BM25/dense weights, k values)
  - Lesson 4: config comparison across runs

Key difference from course: we use deterministic IR metrics (MRR, Recall@k,
NDCG@k) instead of LLM-as-judge (TruLens RAG Triad), because our system
returns code chunks directly — there is no answer synthesis step.

Usage:
    # Single run with current config
    ./scripts/benchmark/run_benchmark.sh --project-path /path/to/project

    # Override weights for this run
    ./scripts/benchmark/run_benchmark.sh --project-path /path \\
        --bm25-weight 0.5 --dense-weight 0.5 --config-name "bm25_50_50"

    # Parameter sweep: run multiple weight combinations, print leaderboard
    ./scripts/benchmark/run_benchmark.sh --project-path /path --sweep

    # Filter to category A/B/C only
    ./scripts/benchmark/run_benchmark.sh --project-path /path --category A

    # Compare two previous benchmark result JSON files
    ./scripts/benchmark/run_benchmark.sh \\
        --compare results/run1.json results/run2.json
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any


def _ensure_pinned_hash_seed() -> None:
    """Re-exec with PYTHONHASHSEED=0 when unset (script execution only).

    Reproducibility: chunk-ID set iteration order feeds candidate-pool
    composition, so unpinned hash randomization flips ~25/131 queries between
    otherwise-identical rounds (evaluation/GPU_DETERMINISM_AB_20260802.md).
    Any explicit PYTHONHASHSEED, including "random", is respected. Must only
    run under __main__ — at import time (tests import this module) sys.argv
    belongs to the importer and re-exec'ing it is wrong.
    """
    if os.environ.get("PYTHONHASHSEED") is None:
        print(
            "[HASHSEED] PYTHONHASHSEED unset - re-exec with PYTHONHASHSEED=0 "
            "for reproducible rounds",
            file=sys.stderr,
        )
        raise SystemExit(
            subprocess.call(
                [sys.executable, *sys.argv],
                env={**os.environ, "PYTHONHASHSEED": "0"},
            )
        )


# Add project root to sys.path so imports resolve from any working directory
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation import arm_overrides  # noqa: E402
from evaluation.arm_overrides import ArmOverrideError  # noqa: E402
from evaluation.metrics import (  # noqa: E402
    THRESHOLDS,
    aggregate_metrics,
    build_chunk_line_lookup,
    build_community_file_map,
    build_community_membership,
    build_file_entries,
    build_merged_membership,
    calculate_acc_at_k,
    calculate_file_recall_at_k,
    calculate_line_iou,
    calculate_line_precision,
    calculate_line_recall,
    calculate_metrics_from_results,
    calculate_mrr,
    calculate_recall_at_k,
    chunk_ids_to_files,
    expand_retrieved_with_community_credit,
    expand_retrieved_with_containment,
    flatten_entries,
    normalize_chunk_id,
    normalize_chunk_ids,
    resolve_chunk_ids_to_ranges,
    to_file_entries,
)


# ---------------------------------------------------------------------------
# Sweep configurations (Lesson 3 pattern: parameter sweep over BM25 weight)
# ---------------------------------------------------------------------------
SWEEP_CONFIGS: list[dict[str, Any]] = [
    {"config_name": "bm25_20_80", "bm25_weight": 0.20, "dense_weight": 0.80},
    {"config_name": "bm25_35_65", "bm25_weight": 0.35, "dense_weight": 0.65},
    {"config_name": "bm25_50_50", "bm25_weight": 0.50, "dense_weight": 0.50},
    {"config_name": "bm25_65_35", "bm25_weight": 0.65, "dense_weight": 0.35},
]

# ---------------------------------------------------------------------------
# Reranker sweep configurations (compare rerankers head-to-head)
# ---------------------------------------------------------------------------
RERANKER_SWEEP: list[dict[str, Any]] = [
    {
        "config_name": "gte",
        "reranker_model": "Alibaba-NLP/gte-reranker-modernbert-base",
    },
    {"config_name": "jina_v3", "reranker_model": "jinaai/jina-reranker-v3"},
    {"config_name": "qwen_0.6b", "reranker_model": "Qwen/Qwen3-Reranker-0.6B"},
    {"config_name": "bge_v2_m3", "reranker_model": "BAAI/bge-reranker-v2-m3"},
    {"config_name": "none", "reranker_enabled": False},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_golden_dataset(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _setup_project(project_path: str) -> None:
    """Set the active project in the MCP server state."""
    try:
        from mcp_server.services import get_state

        state = get_state()
        state.current_project = project_path
    except Exception as e:
        print(f"[WARN] Could not set project via get_state(): {e}", file=sys.stderr)
        print("[WARN] Proceeding — project may already be loaded.", file=sys.stderr)


def _non_none_overrides(pairs: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None``-valued entries.

    The eleven ``_apply_*_override`` functions below share one contract:
    only override the fields the caller actually passed a value for. Each
    used to encode that as its own hand-written ``if X is None and Y is
    None...: return`` guard; ``apply_overrides({})`` is already a no-op, so
    filtering here is sufficient — expressed once instead of eleven times.
    """
    return {key: value for key, value in pairs.items() if value is not None}


def _apply_weight_overrides(
    bm25_weight: float | None,
    dense_weight: float | None,
    search_mode: str | None,
) -> None:
    """Override BM25/dense weights in the in-memory search config singleton."""
    overrides = _non_none_overrides(
        {
            "search_mode.bm25_weight": bm25_weight,
            "search_mode.dense_weight": dense_weight,
            "search_mode.default_mode": search_mode,
        }
    )
    if not overrides:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(get_search_config(), overrides)


def _apply_reranker_override(
    reranker_model: str | None,
    reranker_enabled: bool | None,
) -> None:
    """Override the reranker model/enabled flag in the in-memory search config singleton.

    In-memory only (no file write): does not touch ``search_config.json``, so it survives
    the config-revert hook and never bumps the file mtime that ``SearchConfigManager``
    watches for reload. ``RerankingEngine._ensure_reranker()`` picks up the change on the
    next search and hot-swaps the loaded model (cleanup + rebuild) when ``model_name``
    differs from what is currently loaded.
    """
    overrides = _non_none_overrides(
        {
            "reranker.model_name": reranker_model,
            "reranker.enabled": reranker_enabled,
        }
    )
    if not overrides:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(get_search_config(), overrides)


def _apply_reranker_budget_override(top_k_candidates: int | None) -> None:
    """Override the reranker candidate-pool budget in the in-memory config singleton.

    In-memory only, like ``_apply_reranker_override``. ``top_k_candidates`` is read
    live from config on every search (``search_executor.py``), so no searcher reset
    is needed between runs with different values.
    """
    if top_k_candidates is None:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"reranker.top_k_candidates": top_k_candidates}
    )


def _apply_reranker_doc_max_chars_override(
    doc_max_chars: int | None,
    listwise_doc_max_chars: int | None,
) -> None:
    """Override the per-reranker document budgets in the in-memory config singleton.

    Unlike ``top_k_candidates``, these are baked into the reranker instance at
    construction (``create_reranker(...)`` in ``RerankingEngine._ensure_reranker``)
    and only reloaded there when ``model_name`` changes — so, like ``rrf_k``,
    callers must reset the cached searcher afterwards for a same-model override
    to take effect (see ``_maybe_reset_for_construction_overrides``).
    """
    overrides = _non_none_overrides(
        {
            "reranker.doc_max_chars": doc_max_chars,
            "reranker.listwise_doc_max_chars": listwise_doc_max_chars,
        }
    )
    if not overrides:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(get_search_config(), overrides)


def _apply_reranker_dtype_override(reranker_dtype: str | None) -> None:
    """Override the listwise reranker weight dtype in the in-memory config singleton.

    Like the doc budgets, ``listwise_dtype`` is baked into the JinaRerankerV3
    instance at construction (``create_reranker(...)`` in
    ``RerankingEngine._ensure_reranker``) and the swap branch there reloads only
    on ``model_name`` change — a dtype-only override silently no-ops without a
    searcher reset (see ``_maybe_reset_for_construction_overrides``).
    """
    if reranker_dtype is None:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"reranker.listwise_dtype": reranker_dtype}
    )


def _apply_reserved_slots_override(reserved_slots: int | None) -> None:
    """Override the BM25 reserved fused-pool slots in the in-memory config.

    In-memory only. Read live from config on every search
    (``search_executor.py``), so no searcher reset is needed between runs.
    """
    if reserved_slots is None:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"search_mode.bm25_reserved_slots": reserved_slots}
    )


def _apply_multi_hop_expansion_override(expansion: float | None) -> None:
    """Override the multi-hop expansion factor in the in-memory config singleton.

    In-memory only. Read live from config on every search
    (``multi_hop_searcher.py``), so no searcher reset is needed between runs.
    """
    if expansion is None:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"multi_hop.expansion": expansion}
    )


def _apply_hop1_reserved_slots_override(reserved_slots: int | None) -> None:
    """Override the hop1-reserve rerank-window knob in the in-memory config.

    In-memory only. Read live from config on every search
    (``multi_hop_searcher.py``), so no searcher reset is needed between runs.
    """
    if reserved_slots is None:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"reranker.hop1_reserved_slots": reserved_slots}
    )


def _apply_query_expansion_override(enabled: bool) -> None:
    """Enable curated-vocabulary query expansion in the in-memory config.

    In-memory only. Read live from config on every search
    (``search_executor.py``), so no searcher reset is needed between runs.
    """
    if not enabled:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"query_expansion.enabled": True}
    )


def _apply_ego_graph_overrides(
    ego_graph: str | None,
    community_bounded: str | None,
    cross_community_penalty: float | None,
    expansion_mode: str | None,
) -> None:
    """Override ego-graph knobs in the in-memory config singleton.

    In-memory only, like ``_apply_query_expansion_override``. ``enabled`` and
    ``expansion_mode`` are real ``EgoGraphConfig`` fields, read live per
    search — ``HybridSearcher.search()`` re-reads ``effective_config.ego_graph``
    on every call — so no searcher reset is needed between runs.

    ``community_bounded``/``cross_community_penalty`` are pre-existing here
    but are **not** declared ``EgoGraphConfig`` fields and are not read
    anywhere in ``search/`` (confirmed by grep — likely vestigial from the
    since-rejected community-merge experiment; see project memory
    ``project_benchmark_noise_and_pool_hit``). Migrating this pair through
    ``arm_overrides.apply_overrides`` would turn that silent no-op into a
    hard ``ArmOverrideError`` ("unknown field"), a real behavior change this
    refactor must not make — so they keep the original raw ``setattr``.
    """
    if ego_graph is not None or expansion_mode is not None:
        from search.config import get_search_config

        arm_overrides.apply_overrides(
            get_search_config(),
            _non_none_overrides(
                {
                    "ego_graph.enabled": ego_graph == "on"
                    if ego_graph is not None
                    else None,
                    "ego_graph.expansion_mode": expansion_mode,
                }
            ),
        )

    if community_bounded is not None or cross_community_penalty is not None:
        try:
            from search.config import get_search_config

            cfg = get_search_config()
            if community_bounded is not None:
                cfg.ego_graph.community_bounded = community_bounded == "on"
            if cross_community_penalty is not None:
                cfg.ego_graph.cross_community_penalty = cross_community_penalty
        except Exception as e:
            print(f"[WARN] Could not apply ego-graph overrides: {e}", file=sys.stderr)


def _apply_rrf_k_override(rrf_k: int | None) -> None:
    """Override the RRF fusion constant in the in-memory config singleton.

    Unlike ``top_k_candidates``, ``rrf_k_parameter`` is baked into ``RRFReranker``
    at HybridSearcher construction (``search_factory.py``) — callers must reset
    the cached searcher afterwards for the value to take effect.
    """
    if rrf_k is None:
        return
    from search.config import get_search_config

    arm_overrides.apply_overrides(
        get_search_config(), {"search_mode.rrf_k_parameter": rrf_k}
    )


def _reset_cached_searcher() -> None:
    """Drop the cached ``HybridSearcher`` in server state.

    Shared by ``_maybe_reset_for_construction_overrides`` (the 32 named
    flags) and ``run_single``'s ``--set`` handling — both need the same
    reset once a construction-baked field has changed underneath a cached
    searcher.
    """
    try:
        from mcp_server.services import get_state

        get_state().reset_searcher()
    except Exception as e:
        print(f"[WARN] Could not reset cached searcher: {e}", file=sys.stderr)


def _maybe_reset_for_construction_overrides(
    bm25_weight: float | None,
    dense_weight: float | None,
    rrf_k: int | None,
    doc_max_chars: int | None = None,
    listwise_doc_max_chars: int | None = None,
    reranker_dtype: str | None = None,
) -> None:
    """Drop the cached HybridSearcher when construction-baked params are overridden.

    ``search_factory.get_searcher()`` caches the searcher in server state, and
    rrf_k, the reranker document budgets, and the listwise reranker dtype are
    baked in at construction — without this reset, a ``--sweep`` silently
    reuses the first iteration's params for every subsequent config
    (Blocker B). The decision is derived from ``arm_overrides.requires_rebuild``,
    which reads the same ``spec(construction_baked=True)`` flag (ADR-0022) that
    every other seam caller reads — one source of truth for "which fields are
    baked in at construction" instead of a second, hand-maintained one that
    could silently drift from it.

    bm25_weight/dense_weight are accepted here for backward-compatible call
    sites but are NOT construction-baked (Phase 2a, ADR-0018 follow-on):
    ``HybridSearcher`` takes no weight parameters and resolves both live from
    the effective config on every ``search()`` call
    (``hybrid_searcher.py:731-739``) — so touching only these two no longer
    triggers a reset, and a ``--sweep`` over ``SWEEP_CONFIGS`` (bm25/dense
    weight arms) stops paying a spurious searcher reset + reranker reload.
    """
    touched = _non_none_overrides(
        {
            "search_mode.bm25_weight": bm25_weight,
            "search_mode.dense_weight": dense_weight,
            "search_mode.rrf_k_parameter": rrf_k,
            "reranker.doc_max_chars": doc_max_chars,
            "reranker.listwise_doc_max_chars": listwise_doc_max_chars,
            "reranker.listwise_dtype": reranker_dtype,
        }
    )
    if arm_overrides.requires_rebuild(touched):
        _reset_cached_searcher()


class _EgoConfoundRecorder(logging.Handler):
    """Capture per-query ego-graph confound signals from log records (0f).

    Listens to the ``search.ego_graph_retriever`` logger instead of editing the
    behavior under test: the pre-truncation gate logs
    ``"Limiting N neighbors to M for <anchor>"`` (DEBUG) when it fires, which
    carries the anchor id — so anchor-in-community-map status (the third
    penalty gate at ego_graph_retriever.py:169) can be checked exactly — and
    the PPR path logs a ``"[PPR] ... falling back to BFS"`` warning when power
    iteration fails to converge.  The loop resets this recorder before every
    query.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.truncated_anchors: list[str] = []
        self.ppr_fallback = False

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if msg.startswith("Limiting ") and " for " in msg:
            self.truncated_anchors.append(msg.rsplit(" for ", 1)[1])
        elif "[PPR]" in msg and "falling back to BFS" in msg:
            self.ppr_fallback = True

    def reset(self) -> None:
        self.truncated_anchors = []
        self.ppr_fallback = False


def _attach_ego_confound_recorder() -> _EgoConfoundRecorder:
    """Attach an ``_EgoConfoundRecorder`` to the ego-graph retriever logger.

    Forces that one logger to DEBUG so the truncation records are emitted at
    all; benchmark-process-only, never touches production logging config.
    """
    ego_logger = logging.getLogger("search.ego_graph_retriever")
    recorder = _EgoConfoundRecorder()
    ego_logger.addHandler(recorder)
    if ego_logger.getEffectiveLevel() > logging.DEBUG:
        ego_logger.setLevel(logging.DEBUG)
    return recorder


def _instrument_rerank_calls(searcher: Any) -> list[tuple[int | None, int]]:
    """Wrap ``reranking_engine.rerank_by_query`` to record (k_arg, pool_size).

    Detects whether the ego-gated secondary rerank pass fired for a query
    (``hybrid_searcher.py`` default path: only when ego expansion grew the
    pool past k, called with ``k=len(results)``) — that pass is a confound on
    every ego on/off A/B, so a null result without this signal is
    uninterpretable.  The returned list is shared with the wrapper and
    cleared by the loop before each query.  Idempotent: re-instrumenting the
    same engine returns the existing list.
    """
    engine = getattr(searcher, "reranking_engine", None)
    if engine is None:
        return []
    existing = getattr(engine, "_sscg_rerank_calls", None)
    if existing is not None:
        return existing
    calls: list[tuple[int | None, int]] = []
    original = engine.rerank_by_query

    def _recording_rerank(*args: Any, **kwargs: Any) -> Any:
        pool = kwargs.get("results")
        if pool is None and len(args) >= 2:
            pool = args[1]
        calls.append((kwargs.get("k"), len(pool) if pool is not None else -1))
        return original(*args, **kwargs)

    engine.rerank_by_query = _recording_rerank
    engine._sscg_rerank_calls = calls
    return calls


def _get_searcher(project_path: str):
    """Get an initialized HybridSearcher for the given project."""
    try:
        from mcp_server.search_factory import get_searcher

        return get_searcher(project_path=project_path)
    except TypeError:
        # Fallback: some versions don't accept project_path as keyword arg
        from mcp_server.server import get_searcher  # type: ignore[import]

        return get_searcher()


async def _run_query(
    orchestrator: Any,
    searcher: Any,
    query: str,
    k: int,
    search_mode: str | None = None,
) -> tuple[list[Any], float]:
    """Execute a single query through ``SearchOrchestrator.run()`` (ADR-0023).

    Routes through the same pipeline the MCP ``search_code`` tool serves,
    mirroring the adapter in ``run_mcp_pipeline_eval.py`` — instead of calling
    ``HybridSearcher.search()`` directly (the prior Blocker-A seam), so
    centrality blending (``blended_score``/``centrality``) and every other
    ``_assemble`` stage run for real instead of being hand-replayed by the
    now-deleted ``_apply_centrality_stage``.

    ``max_context_tokens=0`` disables Block H's context-budget truncation
    (its guard is ``> 0``), so the full ranked list survives — matching what
    ``HybridSearcher.search()`` returned before. ``search_mode`` is always
    passed as a concrete string, never bare ``"auto"``, so intent-based mode
    re-derivation can't silently change what is measured (with intent pinned
    off for this arm it would be a no-op anyway, but this keeps the harness
    correct if a future arm flips intent back on).

    ``run()`` returns thin formatted dicts (``result_view._format_search_results``)
    with no ``metadata`` field, so each result is rehydrated from the shared
    searcher's own MetadataStore by ``chunk_id`` — the same store
    ``_build_line_lookup``/``_build_community_scoring_lookup`` already read
    directly — into ``SearchResult``-shaped objects (``chunk_id``/``score``/
    ``metadata``/``source``). This keeps every downstream call site
    (``raw_ids = [r.chunk_id ...]``, ``getattr(r, "metadata", {})``,
    ``_extract_ranges_from_results``) working unchanged, with full metadata
    fidelity (line ranges, community ``tags``) instead of degrading to N/A.

    Args:
        orchestrator: Shared ``SearchOrchestrator`` instance (constructed once
            per process in ``run_single``).
        searcher: Initialized HybridSearcher instance — used here only for
            MetadataStore rehydration; the search itself runs through
            ``orchestrator``.
        search_mode: Threaded into the ``run()`` arguments dict. ``None``
            defaults to ``"hybrid"`` (matches the prior harness default).
    """
    start = time.perf_counter()
    arguments: dict[str, Any] = {
        "query": query,
        "k": k,
        "search_mode": search_mode or "hybrid",
        "include_context": True,
        "max_context_tokens": 0,
    }
    response = await orchestrator.run(arguments)
    latency_ms = (time.perf_counter() - start) * 1000.0

    from search.reranker import SearchResult

    metadata_store = getattr(
        getattr(searcher, "dense_index", None), "metadata_store", None
    )
    results: list[Any] = []
    for formatted in response.get("results") or []:
        chunk_id = formatted.get("chunk_id", "")
        entry = metadata_store.get(chunk_id) if metadata_store is not None else None
        metadata = (entry or {}).get("metadata", {}) or {}
        results.append(
            SearchResult(
                chunk_id=chunk_id,
                score=formatted.get("score", 0.0),
                metadata=metadata,
                source=formatted.get("source", "unknown"),
            )
        )
    return results, latency_ms


def _extract_ranges_from_results(
    results: list[Any],
) -> dict[str, list[tuple[int, int]]]:
    """Extract per-file line ranges from SearchResult objects.

    Reads line data from ``result.metadata`` (where ``HybridSearcher`` stores it)
    rather than top-level attributes, and normalises path separators to forward
    slashes so keys match those produced by ``build_chunk_line_lookup``.

    Args:
        results: List of SearchResult objects whose ``.metadata`` dict contains
            ``relative_path``, ``start_line``, and ``end_line``.

    Returns:
        ``{relative_path: [(start_line, end_line), ...]}`` grouped by file,
        with forward-slash path separators.
    """
    ranges: dict[str, list[tuple[int, int]]] = {}
    for r in results:
        meta = getattr(r, "metadata", {}) or {}
        path = (meta.get("relative_path", "") or "").replace("\\", "/")
        start = meta.get("start_line") or 0
        end = meta.get("end_line") or 0
        if path and start and end:
            try:
                s, e = int(start), int(end)
            except (TypeError, ValueError):
                continue
            ranges.setdefault(path, []).append((s, e))
    return ranges


def _build_line_lookup(searcher: Any) -> dict[str, tuple[str, int, int]]:
    """Build chunk-ID-to-line-range lookup from the searcher's MetadataStore.

    Walks ``searcher.dense_index.metadata_store`` once and builds a lookup
    that maps normalized chunk IDs to (relative_path, start_line, end_line).
    Returns an empty dict if the MetadataStore is not accessible.

    Args:
        searcher: Initialized HybridSearcher instance.

    Returns:
        Lookup dict for use with ``resolve_chunk_ids_to_ranges``.
    """
    try:
        metadata_store = searcher.dense_index.metadata_store
        lookup = build_chunk_line_lookup(metadata_store)
        print(f"  Built line-range lookup: {len(lookup)} chunks indexed", flush=True)
        return lookup
    except AttributeError as exc:
        print(f"  [WARN] Could not build line-range lookup: {exc}", file=sys.stderr)
        return {}


def _build_anchor_lookup(searcher: Any) -> dict[str, list[str]]:
    """Map normalized chunk IDs to raw (line-ranged) IDs for anchor resolution.

    Golden ``anchor_chunk_id`` values are stored normalized (stable across
    reindexes), but ``find_similar_to_chunk`` resolves via the MetadataStore /
    symbol cache, whose keys are the raw 4-part IDs with line ranges and whose
    lookup is exact-string — a normalized ID would never resolve. Multiple raw
    IDs can normalize to the same ID (split_block parts), so values are lists;
    ``_resolve_anchor`` requires exactly one.
    """
    lookup: dict[str, list[str]] = {}
    try:
        for raw_id, _ in searcher.dense_index.metadata_store.items():
            lookup.setdefault(normalize_chunk_id(raw_id), []).append(raw_id)
    except AttributeError as exc:
        print(f"  [WARN] Could not build anchor lookup: {exc}", file=sys.stderr)
    return lookup


def _resolve_anchor(anchor: str, anchor_lookup: dict[str, list[str]]) -> str:
    """Resolve a normalized golden anchor to its unique raw index ID (or raise)."""
    raw_ids = anchor_lookup.get(normalize_chunk_id(anchor), [])
    if len(raw_ids) != 1:
        raise ValueError(
            f"anchor_chunk_id {anchor!r} resolves to {len(raw_ids)} live chunks "
            f"(need exactly 1): {raw_ids}"
        )
    return raw_ids[0]


def _build_merged_membership_lookup(
    searcher: Any,
) -> dict[str, tuple[str, frozenset[str]]]:
    """Build the merged-chunk membership lookup for containment-credit scoring.

    Empty on a merge-free index (scoring is then byte-identical to the strict
    scorer).  Prints the merged-chunk count so runs are self-documenting about
    whether containment credit was in play.

    Args:
        searcher: Initialized HybridSearcher instance.

    Returns:
        Lookup for ``expand_retrieved_with_containment``.
    """
    try:
        metadata_store = searcher.dense_index.metadata_store
        membership = build_merged_membership(metadata_store)
        if membership:
            print(
                f"  Containment credit active: {len(membership)} merged chunks",
                flush=True,
            )
        return membership
    except AttributeError as exc:
        print(f"  [WARN] Could not build merged membership: {exc}", file=sys.stderr)
        return {}


def _build_community_scoring_lookup(searcher: Any) -> dict[str, Any]:
    """Build community lookups + size stats for Category-G file-recall scoring.

    Inverts the persisted community map (already loaded by the ego retriever)
    into per-community file-sets and (path, name) member pairs, and counts the
    synthetic community chunks actually present in the index.  The chunk count
    gates ``mrr_community_credit``: zero community chunks (summaries-off or
    detection-off arms) → the metric is omitted (N/A), never reported as 0.0.

    The size stats satisfy the protocol rule that every Category-G table is
    published alongside the community size distribution — with few large
    communities, expanded file recall is cheap credit, and the reader needs
    the distribution to judge the strict/expanded gap.

    Returns:
        ``{"files": ..., "membership": ..., "chunk_count": int, "stats": {...}}``
        (empty structures when no community map exists).
    """
    community_map: dict[str, int] = (
        getattr(getattr(searcher, "ego_graph_retriever", None), "_community_map", None)
        or {}
    )
    chunk_count = 0
    try:
        for _raw_id, entry in searcher.dense_index.metadata_store.items():
            meta = entry.get("metadata", {}) or {}
            if meta.get("chunk_type") == "community":
                chunk_count += 1
    except AttributeError as exc:
        print(f"  [WARN] Could not count community chunks: {exc}", file=sys.stderr)

    stats: dict[str, Any] = {}
    if community_map:
        sizes = sorted(Counter(community_map.values()).values())
        stats = {
            "chunks_in_map": len(community_map),
            "communities": len(sizes),
            "singletons": sum(1 for s in sizes if s == 1),
            "summarizable": sum(1 for s in sizes if s >= 2),
            "max_size": sizes[-1],
            "size_histogram": {
                "1": sum(1 for s in sizes if s == 1),
                "2-9": sum(1 for s in sizes if 2 <= s <= 9),
                "10-49": sum(1 for s in sizes if 10 <= s <= 49),
                "50+": sum(1 for s in sizes if s >= 50),
            },
            "community_chunks_in_index": chunk_count,
        }
        print(
            f"  Community structure: {stats['communities']} communities "
            f"({stats['summarizable']} summarizable, max size {stats['max_size']}); "
            f"{chunk_count} summary chunks in index",
            flush=True,
        )
    return {
        "files": build_community_file_map(community_map),
        "membership": build_community_membership(community_map),
        "chunk_count": chunk_count,
        "stats": stats,
    }


# ---------------------------------------------------------------------------
# Per-query benchmark execution
# ---------------------------------------------------------------------------


async def run_benchmark(
    *,
    orchestrator: Any,
    searcher: Any,
    queries: list[dict[str, Any]],
    k: int,
    category_filter: str | None,
    verbose: bool,
    line_lookup: dict[str, tuple[str, int, int]] | None = None,
    search_mode: str | None = None,
    merged_membership: dict[str, tuple[str, frozenset[str]]] | None = None,
    f_via_similar: bool = False,
    confound_recorder: "_EgoConfoundRecorder | None" = None,
    rerank_calls: list[tuple[int | None, int]] | None = None,
    community_lookup: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Run all queries and return (per_query_results, latencies).

    Args:
        orchestrator: Shared ``SearchOrchestrator`` instance — the normal
            (non-F-via-similar) branch routes through ``orchestrator.run()``
            via ``_run_query`` (ADR-0023) so centrality blending and every
            other ``_assemble`` stage run unconditionally, config-driven,
            exactly like production.
        searcher: Initialized HybridSearcher instance.
        queries: List of query dicts from golden_dataset.json.
        k: Number of search results to retrieve.
        category_filter: If set, only run queries in categories from this comma-separated
            set (e.g. ``"A,B,C"`` or a single letter like ``"D"``).  When ``None``
            (default), category D is excluded automatically — the pure-searcher
            cannot traverse the call graph and D rows would score ~0 recall,
            polluting the A/B/C aggregate.  Pass ``"D"`` explicitly to benchmark D.
        verbose: Print per-query details.
        line_lookup: Pre-built ``{normalized_chunk_id: (path, start, end)}`` lookup
            from ``_build_line_lookup``. When provided, line-overlap metrics
            (line_recall, line_precision, line_iou) are computed for each query
            whose golden primary chunks resolve to line ranges.
        search_mode: Passed through to ``_run_query`` (see its docstring for why
            this parameter exists — closes the previous ``--search-mode`` no-op).
        merged_membership: Pre-built merged-chunk membership lookup from
            ``_build_merged_membership_lookup``. When non-empty, merged chunks
            are credited for golden symbols they absorbed (containment
            credit); empty/None is an exact no-op vs strict scoring.
        f_via_similar: Score category-F queries carrying an ``anchor_chunk_id``
            via ``HybridSearcher.find_similar_to_chunk(anchor, rerank=False)``
            (the ``find_similar_code`` MCP path) instead of ``search_code``.
            Secondary flagged view only — official aggregates keep search_code.
            The similar-code path is a dense-only single-leg call with no fused
            pool, so ``pool_metrics`` stays empty for those rows.
        confound_recorder: Ego-graph confound recorder from
            ``_attach_ego_confound_recorder``; when provided, each per-query
            row gains a ``"confounds"`` dict (ego rerank pass fired, neighbor
            truncation events, truncated-anchor-in-community-map counts,
            centrality seeded, PPR fallback).
        rerank_calls: Shared call list from ``_instrument_rerank_calls``;
            cleared before each query.
        community_lookup: Lookup from ``_build_community_scoring_lookup``.
            Queries carrying ``expected_files`` (Category G) gain
            ``file_recall_strict`` / ``file_recall_expanded`` (both at the
            run's k), plus the secondary ``mrr_community_credit`` when the
            index contains community chunks (omitted otherwise — N/A, not 0.0).

    Every successful query also gains ``file_recall@{5,10}`` /
    ``file_acc@{5,10}`` (SweRank max-pool rollup of the ordinary chunk-level
    retrieved/expected lists to file-path sets — no community credit; a
    different axis from the Category-G block above), and, when the query's
    dataset row carries ``relevance_grades``, ``ndcg@{5,10}_graded`` and
    ``hard_negative_intrusion`` (see ``calculate_metrics_from_results``).

    Returns:
        Tuple of (per_query_results, latencies).
    """
    if category_filter:
        cats = {c.strip() for c in category_filter.split(",") if c.strip()}
        filtered = [q for q in queries if q.get("category") in cats]
        print(f"  Filtered to {len(filtered)} queries in category '{category_filter}'")
    else:
        # Exclude category D by default: this runner uses search_code only and cannot
        # evaluate connection/call-graph queries.  Use --category D to run explicitly.
        filtered = [q for q in queries if q.get("category") != "D"]
        d_count = len(queries) - len(filtered)
        if d_count:
            print(
                f"  Excluded {d_count} category-D queries (use --category D to include)"
            )

    per_query: list[dict[str, Any]] = []
    latencies: list[float] = []
    anchor_lookup = _build_anchor_lookup(searcher) if f_via_similar else {}

    for i, item in enumerate(filtered, 1):
        qid = item["id"]
        query = item["query"]
        category = item.get("category", "?")
        # Already normalized in golden_dataset.json
        expected: list[str] = item["expected"]
        expected_primary: list[str] = item.get("expected_primary") or expected

        prefix = f"  [{i:2d}/{len(filtered)}] [{qid}][{category}]"
        if verbose:
            print(f"{prefix} {query}")

        # Reset the pool-hit instrumentation so a query that never reaches a
        # rerank pass doesn't inherit the previous query's candidate pool.
        rerank_engine = getattr(searcher, "reranking_engine", None)
        if rerank_engine is not None:
            rerank_engine.last_candidate_ids = None
        if confound_recorder is not None:
            confound_recorder.reset()
        if rerank_calls is not None:
            rerank_calls.clear()

        anchor = (
            item.get("anchor_chunk_id") if f_via_similar and category == "F" else None
        )

        try:
            if anchor:
                raw_anchor = _resolve_anchor(anchor, anchor_lookup)
                start = time.perf_counter()
                raw_results = searcher.find_similar_to_chunk(
                    raw_anchor,
                    k=k,
                    rerank=False,
                    exclude_same_file=item.get("similar_exclude_same_file", False),
                )
                latency_ms = (time.perf_counter() - start) * 1000.0
            else:
                raw_results, latency_ms = await _run_query(
                    orchestrator,
                    searcher,
                    query,
                    k=k,
                    search_mode=search_mode,
                )
            latencies.append(latency_ms)

            # Confound signals for this query (0f): the ego-gated secondary
            # rerank pass is the hybrid_searcher default-path call with
            # k == pool_size after ego expansion grew the pool past the
            # requested k.
            confounds: dict[str, Any] = {}
            if confound_recorder is not None:
                truncated = list(confound_recorder.truncated_anchors)
                ego_retriever = getattr(searcher, "ego_graph_retriever", None)
                community_map = getattr(ego_retriever, "_community_map", None) or {}
                confounds = {
                    "rerank_calls": len(rerank_calls or []),
                    "ego_rerank_pass": any(
                        k_arg is not None and k_arg == pool and pool > k
                        for k_arg, pool in (rerank_calls or [])
                    ),
                    "truncation_events": len(truncated),
                    "truncated_anchors_in_map": sum(
                        1 for a in truncated if a in community_map
                    ),
                    "centrality_seeded": bool(
                        getattr(ego_retriever, "_centrality_scores", None)
                    ),
                    "ppr_fallback": confound_recorder.ppr_fallback,
                }

            # Normalize chunk IDs for chunk-level metrics.  With a non-empty
            # merged_membership, merged chunks widen to per-rank ID sets that
            # include absorbed golden symbols (containment credit); on a
            # merge-free index the entries are plain normalized IDs.
            raw_ids = [r.chunk_id for r in raw_results]
            retrieved = normalize_chunk_ids(raw_ids)
            retrieved_entries = expand_retrieved_with_containment(
                raw_ids, expected, merged_membership or {}
            )

            metrics = calculate_metrics_from_results(
                retrieved=retrieved_entries,
                expected=expected,
                expected_primary=expected_primary,
                relevance_grades=item.get("relevance_grades"),
            )

            # File-level rollup (SweRank max-pool, 1d): a different axis from
            # the Category-G file_recall_strict/expanded block below -- this
            # rolls the ordinary chunk-level retrieved/expected lists up to
            # file-path sets and reuses calculate_recall_at_k/calculate_acc_at_k
            # unchanged, with no community credit involved.
            file_rollup_entries = to_file_entries(retrieved_entries)
            expected_files_rollup = list(chunk_ids_to_files(expected))
            file_rollup_metrics = {
                "file_recall@5": calculate_recall_at_k(
                    file_rollup_entries, expected_files_rollup, 5
                ),
                "file_recall@10": calculate_recall_at_k(
                    file_rollup_entries, expected_files_rollup, 10
                ),
                "file_acc@5": calculate_acc_at_k(
                    file_rollup_entries, expected_files_rollup, 5
                ),
                "file_acc@10": calculate_acc_at_k(
                    file_rollup_entries, expected_files_rollup, 10
                ),
            }

            # Category-G file-level metrics (0g): strict counts real code
            # chunks only; expanded additionally credits a retrieved community
            # chunk with its member file-set.  The strict/expanded gap is the
            # finding — never blended.
            file_metrics: dict[str, float] = {}
            expected_files = item.get("expected_files") or []
            if expected_files:
                lookup = community_lookup or {}
                results_meta = [getattr(r, "metadata", {}) or {} for r in raw_results]
                strict_entries, expanded_entries = build_file_entries(
                    results_meta, lookup.get("files")
                )
                file_metrics = {
                    "file_recall_strict": round(
                        calculate_file_recall_at_k(strict_entries, expected_files, k),
                        4,
                    ),
                    "file_recall_expanded": round(
                        calculate_file_recall_at_k(expanded_entries, expected_files, k),
                        4,
                    ),
                }
                # SECONDARY, community arms only: absent (N/A) when the index
                # has no community chunks — never 0.0.
                if lookup.get("chunk_count"):
                    credit_entries = expand_retrieved_with_community_credit(
                        raw_ids,
                        [meta.get("tags") for meta in results_meta],
                        expected_primary,
                        lookup.get("membership", {}),
                    )
                    file_metrics["mrr_community_credit"] = round(
                        calculate_mrr(credit_entries, expected_primary), 4
                    )

            # Containment credits actually applied (JSON-serializable record)
            containment: dict[str, list[str]] = {}
            for entry, norm_id in zip(retrieved_entries, retrieved, strict=True):
                if isinstance(entry, set) and len(entry) > 1:
                    containment[norm_id] = sorted(entry - {norm_id})

            # Pool-hit-rate (R0): was any gold chunk in the fused candidate
            # pool that entered the final rerank pass?  Same containment
            # credit as ranked scoring, so pool_hit stays consistent.
            pool_metrics: dict[str, Any] = {}
            if rerank_engine is not None and rerank_engine.last_candidate_ids:
                pool_entries = expand_retrieved_with_containment(
                    rerank_engine.last_candidate_ids,
                    expected,
                    merged_membership or {},
                )
                pool_ids = flatten_entries(pool_entries)
                pool_metrics = {
                    "pool_size": len(pool_entries),
                    "pool_hit": any(e in pool_ids for e in expected),
                }

            # Line-overlap metrics (when line_lookup is available)
            line_metrics: dict[str, float] = {}
            if line_lookup:
                golden_ranges = resolve_chunk_ids_to_ranges(
                    expected_primary, line_lookup
                )
                if golden_ranges:
                    retrieved_ranges = _extract_ranges_from_results(raw_results[:k])
                    line_metrics = {
                        "line_recall": calculate_line_recall(
                            retrieved_ranges, golden_ranges
                        ),
                        "line_precision": calculate_line_precision(
                            retrieved_ranges, golden_ranges
                        ),
                        "line_iou": calculate_line_iou(retrieved_ranges, golden_ranges),
                    }

            status = "HIT " if metrics["hit"] else "MISS"
            if verbose:
                line_str = (
                    f"  LR={line_metrics['line_recall']:.2f} "
                    f"LP={line_metrics['line_precision']:.2f} "
                    f"LIoU={line_metrics['line_iou']:.2f}"
                    if line_metrics
                    else ""
                )
                file_str = (
                    f"  FR@{k} strict={file_metrics['file_recall_strict']:.2f} "
                    f"expanded={file_metrics['file_recall_expanded']:.2f}"
                    if file_metrics
                    else ""
                )
                print(
                    f"          [{status}] R@5={metrics['recall@5']:.2f}  "
                    f"MRR={metrics['mrr']:.3f}  NDCG@5={metrics['ndcg@5']:.3f}  "
                    f"({latency_ms:.0f} ms){line_str}{file_str}"
                )
                # Failure drill-down
                if not metrics["hit"]:
                    retrieved_set = set(retrieved[:5])
                    missing = [e for e in expected_primary if e not in retrieved_set]
                    if missing:
                        print(f"          MISSING: {', '.join(missing[:3])}")

            per_query.append(
                {
                    "id": qid,
                    "query": query,
                    "category": category,
                    "retrieved": retrieved[:k],
                    "expected": expected,
                    "expected_primary": expected_primary,
                    "latency_ms": round(latency_ms, 1),
                    **({"f_via_similar": True} if anchor else {}),
                    **({"containment_credits": containment} if containment else {}),
                    **({"confounds": confounds} if confounds else {}),
                    **metrics,
                    **file_rollup_metrics,
                    **file_metrics,
                    **line_metrics,
                    **pool_metrics,
                }
            )

        except Exception as exc:
            print(f"          [ERROR] {exc}", file=sys.stderr)
            per_query.append(
                {
                    "id": qid,
                    "query": query,
                    "category": category,
                    "error": str(exc),
                    "hit": False,
                    "hit@7": False,
                    "recall@1": 0.0,
                    "recall@5": 0.0,
                    "recall@7": 0.0,
                    "recall@10": 0.0,
                    "recall@20": 0.0,
                    "recall@50": 0.0,
                    "precision@1": 0.0,
                    "precision@5": 0.0,
                    "precision@10": 0.0,
                    "mrr": 0.0,
                    "ndcg@5": 0.0,
                    "ndcg@10": 0.0,
                }
            )

    return per_query, latencies


# ---------------------------------------------------------------------------
# Leaderboard output (Lesson 2 pattern: aggregate table)
# ---------------------------------------------------------------------------


def print_leaderboard(
    runs: list[dict[str, Any]],
    title: str = "BENCHMARK LEADERBOARD",
) -> None:
    """Print a leaderboard table comparing one or more benchmark runs."""
    # Detect whether any run has line-overlap metrics or reranker VRAM data
    has_line = any("line_iou" in run.get("aggregate", {}) for run in runs)
    has_vram = any(
        run.get("config_metadata", {}).get("peak_vram_reserved_gb") is not None
        for run in runs
    )

    def _vram_str(run: dict[str, Any]) -> str:
        vram = run.get("config_metadata", {}).get("peak_vram_reserved_gb")
        return f" {vram:>8.2f}" if vram is not None else f" {'-':>8}"

    if has_line:
        width = 107 + (9 if has_vram else 0)
        sep = "=" * width
        print(f"\n{sep}\n{title}\n{sep}")
        vram_header = f" {'VRAM(GB)':>8}" if has_vram else ""
        header = (
            f"{'Config':<22} {'MRR':>6} {'R@5':>6} {'R@7':>6} {'R@10':>6} {'HR@5':>6} "
            f"{'NDCG@5':>8} {'Lat(ms)':>8}{vram_header} | {'LR':>6} {'LP':>6} {'LIoU':>6}"
        )
        print(header)
        print("-" * width)
        for run in runs:
            agg = run["aggregate"]
            lat = run.get("avg_latency_ms", agg.get("avg_latency_ms", 0))
            lr = agg.get("line_recall")
            lp = agg.get("line_precision")
            li = agg.get("line_iou")
            line_str = (
                f" | {lr:>6.3f} {lp:>6.3f} {li:>6.3f}"
                if lr is not None
                else " |      -      -      -"
            )
            vram_str = _vram_str(run) if has_vram else ""
            print(
                f"{run['config_name']:<22} "
                f"{agg['mrr']:>6.3f} {agg['recall@5']:>6.3f} {agg.get('recall@7', 0.0):>6.3f} "
                f"{agg['recall@10']:>6.3f} "
                f"{agg['hit_rate@5']:>6.3f} {agg['ndcg@5']:>8.3f} "
                f"{lat:>8.0f}{vram_str}{line_str}"
            )
        if has_line:
            n = next(
                (
                    agg.get("line_recall_count")
                    for run in runs
                    if (agg := run.get("aggregate", {})) and "line_recall_count" in agg
                ),
                None,
            )
            if n is not None:
                print(
                    f"  (LR/LP/LIoU = line-overlap metrics, averaged over {n} queries)"
                )
        print(sep)
    else:
        width = 87 + (9 if has_vram else 0)
        sep = "=" * width
        print(f"\n{sep}\n{title}\n{sep}")
        vram_header = f" {'VRAM(GB)':>8}" if has_vram else ""
        header = (
            f"{'Config':<22} {'MRR':>6} {'R@5':>6} {'R@7':>6} {'R@10':>6} {'HR@5':>6} "
            f"{'NDCG@5':>8} {'Lat(ms)':>8}{vram_header} {'MRR':>5} {'R@5':>5} {'HR@5':>5}"
        )
        print(header)
        print("-" * width)
        for run in runs:
            agg = run["aggregate"]
            pf = agg.get("pass_fail", {})
            pf_str = f"{pf.get('mrr', '?'):>5} {pf.get('recall@5', '?'):>5} {pf.get('hit_rate@5', '?'):>5}"
            lat = run.get("avg_latency_ms", agg.get("avg_latency_ms", 0))
            vram_str = _vram_str(run) if has_vram else ""
            print(
                f"{run['config_name']:<22} "
                f"{agg['mrr']:>6.3f} {agg['recall@5']:>6.3f} {agg.get('recall@7', 0.0):>6.3f} "
                f"{agg['recall@10']:>6.3f} "
                f"{agg['hit_rate@5']:>6.3f} {agg['ndcg@5']:>8.3f} "
                f"{lat:>8.0f}{vram_str} {pf_str}"
            )
        print(sep)


def print_per_query_drilldown(
    per_query: list[dict[str, Any]], config_name: str
) -> None:
    """Print per-query results for a single run (Lesson 2 drill-down pattern)."""
    has_line = any("line_iou" in q for q in per_query)
    print(f"\n--- Per-query drill-down: {config_name} ---")
    if has_line:
        print(
            f"{'ID':<5} {'Cat':<3} {'R@5':>6} {'R@7':>6} {'MRR':>6} {'NDCG@5':>8} "
            f"{'LR':>6} {'LP':>6} {'LIoU':>6} {'Status':<5} Query"
        )
        print("-" * 92)
        for q in per_query:
            status = "HIT" if q.get("hit") else "MISS"
            r5 = q.get("recall@5", 0.0)
            r7 = q.get("recall@7", 0.0)
            mrr = q.get("mrr", 0.0)
            ndcg = q.get("ndcg@5", 0.0)
            lr = q.get("line_recall")
            lp = q.get("line_precision")
            li = q.get("line_iou")
            line_str = (
                f"{lr:>6.3f} {lp:>6.3f} {li:>6.3f}"
                if lr is not None
                else f"{'n/a':>6} {'n/a':>6} {'n/a':>6}"
            )
            query_short = q["query"][:28]
            print(
                f"{q['id']:<5} {q.get('category', '?'):<3} {r5:>6.3f} {r7:>6.3f} {mrr:>6.3f} "
                f"{ndcg:>8.3f} {line_str} {status:<5} {query_short}"
            )
    else:
        print(
            f"{'ID':<5} {'Cat':<3} {'R@5':>6} {'R@7':>6} {'MRR':>6} {'NDCG@5':>8} {'Status':<5} Query"
        )
        print("-" * 77)
        for q in per_query:
            status = "HIT" if q.get("hit") else "MISS"
            r5 = q.get("recall@5", 0.0)
            r7 = q.get("recall@7", 0.0)
            mrr = q.get("mrr", 0.0)
            ndcg = q.get("ndcg@5", 0.0)
            query_short = q["query"][:35]
            print(
                f"{q['id']:<5} {q.get('category', '?'):<3} {r5:>6.3f} {r7:>6.3f} {mrr:>6.3f} "
                f"{ndcg:>8.3f} {status:<5} {query_short}"
            )


# ---------------------------------------------------------------------------
# Compare mode (Lesson 4 pattern: compare saved runs)
# ---------------------------------------------------------------------------


def compare_runs(result_files: list[str]) -> None:
    """Load saved benchmark JSONs and print a comparison leaderboard."""
    runs = []
    for f in result_files:
        with open(f, encoding="utf-8") as fh:
            data = json.load(fh)
        # Sweep files are wrapped as {"sweep_results": [...]}; unwrap them so
        # each individual run is comparable against single-run output files.
        if "sweep_results" in data:
            runs.extend(data["sweep_results"])
        else:
            runs.append(data)
    print_leaderboard(runs, title="COMPARISON LEADERBOARD")
    # Per-query delta for first two runs
    if len(runs) >= 2:
        r1, r2 = runs[0], runs[1]
        q1 = {q["id"]: q for q in r1.get("per_query", [])}
        q2 = {q["id"]: q for q in r2.get("per_query", [])}
        deltas = []
        for qid, q in q2.items():
            if qid in q1:
                delta_mrr = q.get("mrr", 0) - q1[qid].get("mrr", 0)
                delta_r5 = q.get("recall@5", 0) - q1[qid].get("recall@5", 0)
                if abs(delta_mrr) > 0.001 or abs(delta_r5) > 0.001:
                    deltas.append((qid, q["query"][:40], delta_mrr, delta_r5))
        if deltas:
            print(
                f"\n--- Changes from '{r1['config_name']}' -> '{r2['config_name']}' ---"
            )
            print(f"{'ID':<5} {'dMRR':>7} {'dR@5':>7} Query")
            print("-" * 60)
            for qid, query, dmrr, dr5 in sorted(deltas, key=lambda x: -abs(x[2])):
                sign = "+" if dmrr >= 0 else ""
                print(
                    f"{qid:<5} {sign}{dmrr:>6.3f} {'+' if dr5 >= 0 else ''}{dr5:>6.3f} {query}"
                )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SSCG automated benchmark: evaluate retrieval quality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project-path",
        help="Path to the indexed project (required unless --compare is used)",
    )
    parser.add_argument(
        "--golden-dataset",
        default=str(_PROJECT_ROOT / "evaluation" / "golden_dataset.json"),
        help="Path to golden_dataset.json (default: evaluation/golden_dataset.json)",
    )
    parser.add_argument(
        "--output",
        help="Path to save JSON results (default: benchmark_results/sscg_<timestamp>.json)",
    )
    parser.add_argument(
        "--config-name",
        default="default",
        help="Label for this configuration run (default: 'default')",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=10,
        help="Number of search results to retrieve per query (default: 10)",
    )
    parser.add_argument(
        "--category",
        help=(
            "Filter queries by category, comma-separated (A=small_function, B=sibling, "
            "C=class_overview, D=connection, E=path/flow, F=similarity). Example: "
            "'A,B,C'. Category D is excluded by default because this runner uses "
            "search_code only and cannot traverse the call graph; pass --category D to "
            "run it explicitly (expect low recall — use find_connections for D queries)."
        ),
    )
    parser.add_argument(
        "--bm25-weight",
        type=float,
        help="Override BM25 weight (0.0-1.0). Default: use config value.",
    )
    parser.add_argument(
        "--dense-weight",
        type=float,
        help="Override dense/semantic weight (0.0-1.0). Default: use config value.",
    )
    parser.add_argument(
        "--search-mode",
        choices=["hybrid", "semantic", "bm25", "auto"],
        help="Override search mode. Default: use config value.",
    )
    parser.add_argument(
        "--sweep",
        action="store_true",
        help="Run parameter sweep across predefined BM25/dense weight combinations",
    )
    parser.add_argument(
        "--reranker-model",
        help=(
            "Override the reranker model for this run (e.g. "
            "'jinaai/jina-reranker-v3', 'Qwen/Qwen3-Reranker-0.6B', "
            "'Alibaba-NLP/gte-reranker-modernbert-base'). Default: use config value."
        ),
    )
    parser.add_argument(
        "--reranker-enabled",
        choices=["true", "false"],
        help="Override whether neural reranking is enabled for this run (baseline: 'false').",
    )
    parser.add_argument(
        "--top-k-candidates",
        type=int,
        help=(
            "Override reranker.top_k_candidates (rerank pool budget) for this run. "
            "Default: use config value (30)."
        ),
    )
    parser.add_argument(
        "--reranker-doc-max-chars",
        type=int,
        help=(
            "Override reranker.doc_max_chars (GenerativeReranker pointwise "
            "per-document budget) for this run. Resets the cached searcher so "
            "the value takes effect. Default: use config value (4000)."
        ),
    )
    parser.add_argument(
        "--reranker-listwise-doc-max-chars",
        type=int,
        help=(
            "Override reranker.listwise_doc_max_chars (JinaRerankerV3 shared-"
            "context per-document budget) for this run. Resets the cached "
            "searcher so the value takes effect. Default: use config value (1000)."
        ),
        # 1000 is the RerankerConfig default (search/config.py) — kept aligned
        # since docs/adr/0011-listwise-reranker-doc-cap.md reverted it there.
    )
    parser.add_argument(
        "--reranker-dtype",
        choices=["auto", "fp32", "bf16", "fp16"],
        help=(
            "Override reranker.listwise_dtype (JinaRerankerV3 weight dtype) "
            "for this run. 'auto' = checkpoint default (bf16, run-to-run "
            "non-deterministic at ranking boundaries); 'fp32' = deterministic "
            "scores at ~2x reranker VRAM. Resets the cached searcher so the "
            "value takes effect. Default: use config value ('auto')."
        ),
    )
    parser.add_argument(
        "--deterministic-gpu",
        action="store_true",
        help=(
            "Pin deterministic CUDA kernels for this run "
            "(CUBLAS_WORKSPACE_CONFIG + torch.use_deterministic_algorithms + "
            "cuDNN determinism). Applied at startup before any model load. "
            "Strict by default (RuntimeError on ops without a deterministic "
            "implementation) — see --determinism-warn-only."
        ),
    )
    parser.add_argument(
        "--determinism-warn-only",
        action="store_true",
        help=(
            "With --deterministic-gpu: downgrade non-deterministic-op errors "
            "to warnings (those ops stay non-deterministic). Use only if the "
            "strict mode raises."
        ),
    )
    parser.add_argument(
        "--bm25-reserved-slots",
        type=int,
        help=(
            "Override search_mode.bm25_reserved_slots (fused-pool slots reserved "
            "for BM25-unique candidates) for this run. Default: use config "
            "value (0 = disabled)."
        ),
    )
    parser.add_argument(
        "--multi-hop-expansion",
        type=float,
        help=(
            "Override multi_hop.expansion (hop-2 expansion factor, controls "
            "candidate-pool size before the multi-hop rerank cut) for this run. "
            "Default: use config value (0.5)."
        ),
    )
    parser.add_argument(
        "--hop1-reserved-slots",
        type=int,
        help=(
            "Override reranker.hop1_reserved_slots (promotes up to N "
            "best-hop1-ranked candidates from outside the multi-hop rerank "
            "window back into it) for this run. Default: use config value "
            "(0 = disabled)."
        ),
    )
    parser.add_argument(
        "--query-expansion",
        action="store_true",
        help=(
            "Enable curated-vocabulary query expansion "
            "(query_expansion.enabled=True) for this run. Matched concepts add "
            "discounted BM25 variant legs to the hybrid fusion. Default: use "
            "config value (disabled)."
        ),
    )
    parser.add_argument(
        "--f-via-similar",
        action="store_true",
        help=(
            "Score category-F queries with an anchor_chunk_id via "
            "find_similar_to_chunk (the find_similar_code MCP path) instead of "
            "search_code. Secondary flagged view — official aggregates keep "
            "search_code. Other categories are unaffected."
        ),
    )
    parser.add_argument(
        "--rrf-k",
        type=int,
        help=(
            "Override search_mode.rrf_k_parameter (RRF fusion constant) for this "
            "run. Resets the cached searcher so the value takes effect. "
            "Default: use config value (100)."
        ),
    )
    parser.add_argument(
        "--ego-graph",
        choices=["on", "off"],
        help=(
            "Override ego_graph.enabled for this run (community-ablation arm "
            "A1). In-memory only; read live per search, no searcher reset "
            "needed. Default: use config value."
        ),
    )
    parser.add_argument(
        "--community-bounded",
        choices=["on", "off"],
        help=(
            "Override ego_graph.community_bounded (cross-community penalty "
            "during ego neighbor truncation) for this run. Only observable "
            "when truncation fires AND centrality is seeded AND the anchor is "
            "in the community map — see the per-query confound log. Default: "
            "use config value."
        ),
    )
    parser.add_argument(
        "--cross-community-penalty",
        type=float,
        help=(
            "Override ego_graph.cross_community_penalty (score multiplier for "
            "cross-community neighbors during truncation ranking) for this "
            "run. Default: use config value (0.6)."
        ),
    )
    parser.add_argument(
        "--expansion-mode",
        choices=["bfs", "ppr"],
        help=(
            "Override ego_graph.expansion_mode (k-hop BFS vs Personalized "
            "PageRank ego expansion) for this run (arm A4). Default: use "
            "config value (bfs)."
        ),
    )
    parser.add_argument(
        "--reranker-sweep",
        action="store_true",
        help="Run reranker comparison across predefined models (see RERANKER_SWEEP)",
    )
    parser.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        metavar="section.field=value",
        help=(
            "Override an arbitrary SearchConfig field for this run, e.g. "
            "'--set reranker.top_k_candidates=33'. Repeatable; later "
            "duplicates win. Routed through evaluation.arm_overrides — value "
            "is coerced to the field's declared type and validated against "
            "its spec(range=...)/choices=... before anything is mutated. "
            "Sugar for the 32 named flags above where one exists; use this "
            "for any field without a dedicated flag."
        ),
    )
    parser.add_argument(
        "--compare",
        nargs="+",
        metavar="RESULT_JSON",
        help="Compare two or more saved benchmark result JSON files (no search run)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-query output (only print aggregate table)",
    )
    parser.add_argument(
        "--no-drilldown",
        action="store_true",
        help="Skip per-query drill-down table",
    )
    return parser


async def run_single(
    *,
    project_path: str,
    dataset: dict[str, Any],
    config_name: str,
    k: int,
    bm25_weight: float | None,
    dense_weight: float | None,
    search_mode: str | None,
    category_filter: str | None,
    verbose: bool,
    reranker_model: str | None = None,
    reranker_enabled: bool | None = None,
    top_k_candidates: int | None = None,
    rrf_k: int | None = None,
    bm25_reserved_slots: int | None = None,
    reranker_doc_max_chars: int | None = None,
    reranker_listwise_doc_max_chars: int | None = None,
    reranker_dtype: str | None = None,
    f_via_similar: bool = False,
    query_expansion: bool = False,
    multi_hop_expansion: float | None = None,
    hop1_reserved_slots: int | None = None,
    ego_graph: str | None = None,
    community_bounded: str | None = None,
    cross_community_penalty: float | None = None,
    expansion_mode: str | None = None,
    set_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute one benchmark run and return the result dict."""
    _apply_weight_overrides(bm25_weight, dense_weight, search_mode)
    _apply_reranker_override(reranker_model, reranker_enabled)
    _apply_reranker_budget_override(top_k_candidates)
    _apply_reranker_doc_max_chars_override(
        reranker_doc_max_chars, reranker_listwise_doc_max_chars
    )
    _apply_reranker_dtype_override(reranker_dtype)
    _apply_rrf_k_override(rrf_k)
    _apply_reserved_slots_override(bm25_reserved_slots)
    _apply_multi_hop_expansion_override(multi_hop_expansion)
    _apply_hop1_reserved_slots_override(hop1_reserved_slots)
    _apply_query_expansion_override(query_expansion)
    _apply_ego_graph_overrides(
        ego_graph, community_bounded, cross_community_penalty, expansion_mode
    )
    _maybe_reset_for_construction_overrides(
        bm25_weight,
        dense_weight,
        rrf_k,
        reranker_doc_max_chars,
        reranker_listwise_doc_max_chars,
        reranker_dtype,
    )
    if set_overrides:
        from search.config import get_search_config

        if arm_overrides.apply_overrides(get_search_config(), set_overrides):
            _reset_cached_searcher()
        print(f"  --set overrides: {set_overrides}")

    try:
        searcher = _get_searcher(project_path)
    except Exception as exc:
        print(f"[ERROR] Could not initialize searcher: {exc}", file=sys.stderr)
        print("[ERROR] Make sure an index is built for this project.", file=sys.stderr)
        sys.exit(1)

    # ADR-0023 (B1): route search through the same pipeline the MCP
    # search_code tool serves, instead of calling HybridSearcher.search()
    # directly. One shared instance per run_single call, mirroring
    # run_mcp_pipeline_eval.py's adapter.
    from mcp_server.tools.search_orchestrator import SearchOrchestrator

    orchestrator = SearchOrchestrator()

    queries = dataset["queries"]
    print(f"\nRunning: {config_name} | k={k} | {len(queries)} queries")
    if bm25_weight is not None or dense_weight is not None:
        print(
            f"  Weights: BM25={bm25_weight or 'default'}  dense={dense_weight or 'default'}"
        )
    if reranker_model is not None or reranker_enabled is not None:
        print(
            f"  Reranker: model={reranker_model or 'default'}  "
            f"enabled={reranker_enabled if reranker_enabled is not None else 'default'}"
        )
    if top_k_candidates is not None:
        print(f"  Reranker pool budget: top_k_candidates={top_k_candidates}")
    if (
        reranker_doc_max_chars is not None
        or reranker_listwise_doc_max_chars is not None
    ):
        print(
            f"  Reranker doc budget: doc_max_chars={reranker_doc_max_chars or 'default'}  "
            f"listwise_doc_max_chars={reranker_listwise_doc_max_chars or 'default'}"
        )
    if reranker_dtype is not None:
        print(f"  Reranker dtype: listwise_dtype={reranker_dtype}")
    if rrf_k is not None:
        print(f"  RRF fusion constant: rrf_k={rrf_k}")
    if bm25_reserved_slots is not None:
        print(f"  BM25 reserved pool slots: {bm25_reserved_slots}")
    if multi_hop_expansion is not None:
        print(f"  Multi-hop expansion factor: {multi_hop_expansion}")
    if hop1_reserved_slots is not None:
        print(f"  Hop1 reserved rerank-window slots: {hop1_reserved_slots}")
    if ego_graph is not None:
        print(f"  Ego-graph expansion: {ego_graph}")
    if community_bounded is not None:
        print(f"  Community-bounded ego truncation: {community_bounded}")
    if cross_community_penalty is not None:
        print(f"  Cross-community penalty: {cross_community_penalty}")
    if expansion_mode is not None:
        print(f"  Ego expansion mode: {expansion_mode}")
    if f_via_similar:
        print(
            "  F-via-similar: ON (anchored F queries scored via "
            "find_similar_to_chunk; secondary view, not the official aggregate)"
        )
    if query_expansion:
        print(
            "  Query expansion: ON (curated-vocabulary variant legs, "
            "config/query_expansion_variants.yaml)"
        )

    # Reset peak VRAM stats and issue a warm-up search so a reranker model swap's
    # (or dtype swap's) first-call load/download cost lands here, not in the
    # timed latency average.
    torch_module = None
    if (
        reranker_model is not None
        or reranker_enabled is not None
        or reranker_dtype is not None
    ):
        try:
            import torch

            if torch.cuda.is_available():
                torch_module = torch
                torch.cuda.reset_peak_memory_stats()
        except ImportError:
            pass
        if queries:
            try:
                searcher.search(queries[0]["query"], k=k)
            except Exception as exc:
                print(f"  [WARN] Warm-up search failed: {exc}", file=sys.stderr)

    # Centrality cold-start warm-up (0d) is no longer needed: routing through
    # SearchOrchestrator.run() (ADR-0023) means GraphScoringStage runs inside
    # each query's own scoring stage unconditionally, exactly as production
    # does — there is no separate replay stage left to seed.

    # Confound instrumentation (0f)
    confound_recorder = _attach_ego_confound_recorder()
    rerank_calls = _instrument_rerank_calls(searcher)

    # Build line-range lookup for line-overlap metrics (one-time scan of MetadataStore)
    line_lookup = _build_line_lookup(searcher)
    # Merged-chunk membership for containment-credit scoring (empty = no-op)
    merged_membership = _build_merged_membership_lookup(searcher)
    # Community lookups for Category-G file recall + size distribution (0g)
    community_lookup = _build_community_scoring_lookup(searcher)

    per_query, latencies = await run_benchmark(
        orchestrator=orchestrator,
        searcher=searcher,
        queries=queries,
        k=k,
        category_filter=category_filter,
        verbose=verbose,
        line_lookup=line_lookup,
        search_mode=search_mode,
        merged_membership=merged_membership,
        f_via_similar=f_via_similar,
        confound_recorder=confound_recorder,
        rerank_calls=rerank_calls,
        community_lookup=community_lookup,
    )

    # Detach the recorder so repeated run_single calls (sweeps) don't stack handlers
    logging.getLogger("search.ego_graph_retriever").removeHandler(confound_recorder)

    dataset_thresholds = dataset.get("thresholds") or {}
    agg = aggregate_metrics(per_query, thresholds=dataset_thresholds)
    avg_lat = round(mean(latencies), 1) if latencies else 0.0

    # Confound summary (0f): an A1 null result is only interpretable if we
    # know the gated machinery actually fired ("penalty useless" vs "penalty
    # never exercised").
    confound_rows = [q["confounds"] for q in per_query if "confounds" in q]
    confound_summary: dict[str, Any] = {}
    if confound_rows:
        n = len(confound_rows)
        confound_summary = {
            "queries": n,
            "ego_rerank_pass_fired": sum(
                1 for c in confound_rows if c["ego_rerank_pass"]
            ),
            "truncation_events": sum(c["truncation_events"] for c in confound_rows),
            "truncated_anchors_in_map": sum(
                c["truncated_anchors_in_map"] for c in confound_rows
            ),
            "centrality_seeded": sum(
                1 for c in confound_rows if c["centrality_seeded"]
            ),
            "ppr_fallbacks": sum(1 for c in confound_rows if c["ppr_fallback"]),
        }
        print(
            f"\n  Confounds: ego-rerank pass fired on "
            f"{confound_summary['ego_rerank_pass_fired']}/{n} queries; "
            f"truncation events={confound_summary['truncation_events']} "
            f"(anchors in community map: "
            f"{confound_summary['truncated_anchors_in_map']}); "
            f"centrality seeded on {confound_summary['centrality_seeded']}/{n}; "
            f"PPR fallbacks={confound_summary['ppr_fallbacks']}"
        )

    # Config metadata for comparison / experiment tracking (Lesson 4 pattern)
    config_metadata: dict[str, Any] = {
        "project_path": project_path,
        "k": k,
        "category_filter": category_filter,
    }
    if bm25_weight is not None:
        config_metadata["bm25_weight"] = bm25_weight
    if dense_weight is not None:
        config_metadata["dense_weight"] = dense_weight
    if search_mode is not None:
        config_metadata["search_mode"] = search_mode
    if reranker_model is not None:
        config_metadata["reranker_model"] = reranker_model
    if reranker_enabled is not None:
        config_metadata["reranker_enabled"] = reranker_enabled
    if top_k_candidates is not None:
        config_metadata["top_k_candidates"] = top_k_candidates
    if reranker_dtype is not None:
        config_metadata["reranker_dtype"] = reranker_dtype
    if rrf_k is not None:
        config_metadata["rrf_k"] = rrf_k
    if bm25_reserved_slots is not None:
        config_metadata["bm25_reserved_slots"] = bm25_reserved_slots
    if multi_hop_expansion is not None:
        config_metadata["multi_hop_expansion"] = multi_hop_expansion
    if hop1_reserved_slots is not None:
        config_metadata["hop1_reserved_slots"] = hop1_reserved_slots
    if f_via_similar:
        config_metadata["f_via_similar"] = True
    if query_expansion:
        config_metadata["query_expansion"] = True
    if ego_graph is not None:
        config_metadata["ego_graph"] = ego_graph
    if community_bounded is not None:
        config_metadata["community_bounded"] = community_bounded
    if cross_community_penalty is not None:
        config_metadata["cross_community_penalty"] = cross_community_penalty
    if expansion_mode is not None:
        config_metadata["expansion_mode"] = expansion_mode
    if torch_module is not None:
        config_metadata["peak_vram_reserved_gb"] = round(
            torch_module.cuda.max_memory_reserved() / 1e9, 2
        )

    return {
        "config_name": config_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "aggregate": agg,
        "avg_latency_ms": avg_lat,
        "config_metadata": config_metadata,
        **({"confound_summary": confound_summary} if confound_summary else {}),
        **(
            {"community_stats": community_lookup["stats"]}
            if community_lookup.get("stats")
            else {}
        ),
        "thresholds": {**THRESHOLDS, **dataset_thresholds},
        "per_query": per_query,
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # -----------------------------------------------------------------------
    # Compare mode: just load saved JSONs and print comparison
    # -----------------------------------------------------------------------
    if args.compare:
        compare_runs(args.compare)
        return

    # -----------------------------------------------------------------------
    # Require project path for search runs (checked here, not in main_async,
    # so parser.error()'s usage-string + exit(2) behavior is available).
    # -----------------------------------------------------------------------
    if not args.project_path:
        parser.error(
            "--project-path is required (or use --compare to compare saved results)"
        )

    try:
        asyncio.run(main_async(args))
    except ArmOverrideError as exc:
        # Only --set overrides raise this today (the 32 named flags are
        # pre-validated by argparse choices=/type=) - surface it as a clean
        # CLI error instead of a traceback, matching the --project-path
        # check above.
        print(f"[ERROR] Invalid override: {exc}", file=sys.stderr)
        sys.exit(1)


async def main_async(args: argparse.Namespace) -> None:
    # Determinism must be pinned before the first cuBLAS call (first model
    # load), so this precedes _setup_project/_get_searcher.
    if args.deterministic_gpu:
        from utils.determinism import apply_gpu_determinism

        apply_gpu_determinism(warn_only=args.determinism_warn_only)
        print(
            f"  GPU determinism: ON (warn_only={args.determinism_warn_only})",
            file=sys.stderr,
        )

    project_path = str(Path(args.project_path).resolve())
    _setup_project(project_path)

    # B1 (ADR-0023): pin intent classification off. Routing through
    # SearchOrchestrator.run() now exercises plan.intent_decision live;
    # B1b (a later, separate arm) flips this on to measure the intent
    # layer's retrieval impact in isolation.
    from search.config import get_search_config

    get_search_config().intent.enabled = False

    dataset = _load_golden_dataset(Path(args.golden_dataset))
    verbose = not args.quiet
    reranker_enabled = (
        None if args.reranker_enabled is None else args.reranker_enabled == "true"
    )
    # Parse once, up front, so a malformed --set fails before any search run
    # (and before any sweep iteration) rather than mid-sweep.
    set_overrides = arm_overrides.parse_set_flags(args.set_overrides)

    # -----------------------------------------------------------------------
    # Reranker sweep mode: run predefined rerankers head-to-head
    # -----------------------------------------------------------------------
    if args.reranker_sweep:
        print(f"\n{'=' * 70}")
        print("RERANKER SWEEP: model comparison")
        print(f"{'=' * 70}")
        reranker_results: list[dict[str, Any]] = []
        for sweep_cfg in RERANKER_SWEEP:
            result = await run_single(
                project_path=project_path,
                dataset=dataset,
                config_name=sweep_cfg["config_name"],
                k=args.k,
                bm25_weight=args.bm25_weight,
                dense_weight=args.dense_weight,
                search_mode=args.search_mode,
                category_filter=args.category,
                verbose=False,  # quiet during sweep
                reranker_model=sweep_cfg.get("reranker_model"),
                reranker_enabled=sweep_cfg.get("reranker_enabled"),
                top_k_candidates=args.top_k_candidates,
                reranker_doc_max_chars=args.reranker_doc_max_chars,
                reranker_listwise_doc_max_chars=args.reranker_listwise_doc_max_chars,
                reranker_dtype=args.reranker_dtype,
                rrf_k=args.rrf_k,
                bm25_reserved_slots=args.bm25_reserved_slots,
                multi_hop_expansion=args.multi_hop_expansion,
                hop1_reserved_slots=args.hop1_reserved_slots,
                f_via_similar=args.f_via_similar,
                query_expansion=args.query_expansion,
                ego_graph=args.ego_graph,
                community_bounded=args.community_bounded,
                cross_community_penalty=args.cross_community_penalty,
                expansion_mode=args.expansion_mode,
                set_overrides=set_overrides,
            )
            reranker_results.append(result)

        print_leaderboard(reranker_results, title="RERANKER SWEEP LEADERBOARD")

        # Save sweep results
        output_path = args.output or str(
            _PROJECT_ROOT
            / "benchmark_results"
            / f"sscg_reranker_sweep_{time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"sweep_results": reranker_results}, f, indent=2)
        print(f"\nReranker sweep results saved to: {output_path}")
        return

    # -----------------------------------------------------------------------
    # Sweep mode: run multiple weight combinations and print leaderboard
    # -----------------------------------------------------------------------
    if args.sweep:
        print(f"\n{'=' * 70}")
        print("PARAMETER SWEEP: BM25/dense weight combinations")
        print(f"{'=' * 70}")
        sweep_results: list[dict[str, Any]] = []
        for sweep_cfg in SWEEP_CONFIGS:
            result = await run_single(
                project_path=project_path,
                dataset=dataset,
                config_name=sweep_cfg["config_name"],
                k=args.k,
                bm25_weight=sweep_cfg["bm25_weight"],
                dense_weight=sweep_cfg["dense_weight"],
                search_mode=args.search_mode,
                category_filter=args.category,
                verbose=False,  # quiet during sweep
                reranker_model=args.reranker_model,
                reranker_enabled=reranker_enabled,
                top_k_candidates=args.top_k_candidates,
                reranker_doc_max_chars=args.reranker_doc_max_chars,
                reranker_listwise_doc_max_chars=args.reranker_listwise_doc_max_chars,
                reranker_dtype=args.reranker_dtype,
                rrf_k=args.rrf_k,
                bm25_reserved_slots=args.bm25_reserved_slots,
                multi_hop_expansion=args.multi_hop_expansion,
                hop1_reserved_slots=args.hop1_reserved_slots,
                f_via_similar=args.f_via_similar,
                query_expansion=args.query_expansion,
                ego_graph=args.ego_graph,
                community_bounded=args.community_bounded,
                cross_community_penalty=args.cross_community_penalty,
                expansion_mode=args.expansion_mode,
                set_overrides=set_overrides,
            )
            sweep_results.append(result)

        print_leaderboard(sweep_results, title="PARAMETER SWEEP LEADERBOARD")

        # Save sweep results
        output_path = args.output or str(
            _PROJECT_ROOT
            / "benchmark_results"
            / f"sscg_sweep_{time.strftime('%Y%m%d_%H%M%S')}.json"
        )
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"sweep_results": sweep_results}, f, indent=2)
        print(f"\nSweep results saved to: {output_path}")
        return

    # -----------------------------------------------------------------------
    # Single run
    # -----------------------------------------------------------------------
    result = await run_single(
        project_path=project_path,
        dataset=dataset,
        config_name=args.config_name,
        k=args.k,
        bm25_weight=args.bm25_weight,
        dense_weight=args.dense_weight,
        search_mode=args.search_mode,
        category_filter=args.category,
        verbose=verbose,
        reranker_model=args.reranker_model,
        reranker_enabled=reranker_enabled,
        top_k_candidates=args.top_k_candidates,
        reranker_doc_max_chars=args.reranker_doc_max_chars,
        reranker_listwise_doc_max_chars=args.reranker_listwise_doc_max_chars,
        reranker_dtype=args.reranker_dtype,
        rrf_k=args.rrf_k,
        bm25_reserved_slots=args.bm25_reserved_slots,
        multi_hop_expansion=args.multi_hop_expansion,
        hop1_reserved_slots=args.hop1_reserved_slots,
        f_via_similar=args.f_via_similar,
        query_expansion=args.query_expansion,
        ego_graph=args.ego_graph,
        community_bounded=args.community_bounded,
        cross_community_penalty=args.cross_community_penalty,
        expansion_mode=args.expansion_mode,
        set_overrides=set_overrides,
    )

    # Print leaderboard (single row)
    print_leaderboard([result])

    # Per-query drill-down (Lesson 2 pattern)
    if not args.no_drilldown and verbose:
        print_per_query_drilldown(result["per_query"], result["config_name"])

    # Recall-headroom summary (R0): deep recall + pre-rerank pool hit rate
    agg = result["aggregate"]
    if "pool_hit_rate" in agg:
        print(
            f"\nRecall headroom: R@20={agg.get('recall@20', 0.0):.3f}  "
            f"R@50={agg.get('recall@50', 0.0):.3f}  "
            f"pool_hit_rate={agg['pool_hit_rate']:.3f} "
            f"(avg pool {agg.get('avg_pool_size', 0.0):.1f} candidates, "
            f"n={agg.get('pool_hit_count', 0)} queries)"
        )

    # Pass/fail summary
    pf = result["aggregate"].get("pass_fail", {})
    all_pass = all(v == "PASS" for v in pf.values())
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    run_thresholds = result.get("thresholds", THRESHOLDS)
    for metric, status in pf.items():
        threshold = run_thresholds.get(metric.replace("@", "_at_"), "?")
        print(f"  {metric:<14}: {status}  (threshold >= {threshold})")

    # Save results
    output_path = args.output or str(
        _PROJECT_ROOT
        / "benchmark_results"
        / f"sscg_{args.config_name}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    _ensure_pinned_hash_seed()
    main()
