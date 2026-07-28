#!/usr/bin/env python3
"""SSCG Automated Benchmark Runner.

Evaluates retrieval quality against the SSCG golden dataset (45 queries: A/B/C/D).
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
import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any


# Add project root to sys.path so imports resolve from any working directory
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    THRESHOLDS,
    aggregate_metrics,
    build_chunk_line_lookup,
    build_merged_membership,
    calculate_line_iou,
    calculate_line_precision,
    calculate_line_recall,
    calculate_metrics_from_results,
    expand_retrieved_with_containment,
    flatten_entries,
    normalize_chunk_ids,
    resolve_chunk_ids_to_ranges,
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
    {"config_name": "qwen_4b", "reranker_model": "Qwen/Qwen3-Reranker-4B"},
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


def _apply_weight_overrides(
    bm25_weight: float | None,
    dense_weight: float | None,
    search_mode: str | None,
) -> None:
    """Override BM25/dense weights in the in-memory search config singleton."""
    if bm25_weight is None and dense_weight is None and search_mode is None:
        return
    try:
        from search.config import get_search_config

        cfg = get_search_config()
        if bm25_weight is not None:
            cfg.search_mode.bm25_weight = bm25_weight
        if dense_weight is not None:
            cfg.search_mode.dense_weight = dense_weight
        if search_mode is not None:
            cfg.search_mode.default_mode = search_mode
    except Exception as e:
        print(f"[WARN] Could not apply weight overrides: {e}", file=sys.stderr)


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
    if reranker_model is None and reranker_enabled is None:
        return
    try:
        from search.config import get_search_config

        cfg = get_search_config()
        if reranker_model is not None:
            cfg.reranker.model_name = reranker_model
        if reranker_enabled is not None:
            cfg.reranker.enabled = reranker_enabled
    except Exception as e:
        print(f"[WARN] Could not apply reranker override: {e}", file=sys.stderr)


def _apply_reranker_budget_override(top_k_candidates: int | None) -> None:
    """Override the reranker candidate-pool budget in the in-memory config singleton.

    In-memory only, like ``_apply_reranker_override``. ``top_k_candidates`` is read
    live from config on every search (``search_executor.py``), so no searcher reset
    is needed between runs with different values.
    """
    if top_k_candidates is None:
        return
    try:
        from search.config import get_search_config

        cfg = get_search_config()
        cfg.reranker.top_k_candidates = top_k_candidates
    except Exception as e:
        print(f"[WARN] Could not apply reranker budget override: {e}", file=sys.stderr)


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
    if doc_max_chars is None and listwise_doc_max_chars is None:
        return
    try:
        from search.config import get_search_config

        cfg = get_search_config()
        if doc_max_chars is not None:
            cfg.reranker.doc_max_chars = doc_max_chars
        if listwise_doc_max_chars is not None:
            cfg.reranker.listwise_doc_max_chars = listwise_doc_max_chars
    except Exception as e:
        print(
            f"[WARN] Could not apply reranker doc-max-chars override: {e}",
            file=sys.stderr,
        )


def _apply_reserved_slots_override(reserved_slots: int | None) -> None:
    """Override the BM25 reserved fused-pool slots in the in-memory config.

    In-memory only. Read live from config on every search
    (``search_executor.py``), so no searcher reset is needed between runs.
    """
    if reserved_slots is None:
        return
    try:
        from search.config import get_search_config

        get_search_config().search_mode.bm25_reserved_slots = reserved_slots
    except Exception as e:
        print(f"[WARN] Could not apply reserved-slots override: {e}", file=sys.stderr)


def _apply_rrf_k_override(rrf_k: int | None) -> None:
    """Override the RRF fusion constant in the in-memory config singleton.

    Unlike ``top_k_candidates``, ``rrf_k_parameter`` is baked into ``RRFReranker``
    at HybridSearcher construction (``search_factory.py``) — callers must reset
    the cached searcher afterwards for the value to take effect.
    """
    if rrf_k is None:
        return
    try:
        from search.config import get_search_config

        get_search_config().search_mode.rrf_k_parameter = rrf_k
    except Exception as e:
        print(f"[WARN] Could not apply rrf_k override: {e}", file=sys.stderr)


def _maybe_reset_for_construction_overrides(
    bm25_weight: float | None,
    dense_weight: float | None,
    rrf_k: int | None,
    doc_max_chars: int | None = None,
    listwise_doc_max_chars: int | None = None,
) -> None:
    """Drop the cached HybridSearcher when construction-baked params are overridden.

    ``search_factory.get_searcher()`` caches the searcher in server state, and
    bm25/dense weights, rrf_k, and the reranker document budgets are all baked
    in at construction — without this reset, a ``--sweep`` silently reuses the
    first iteration's params for every subsequent config (Blocker B).
    """
    if (
        bm25_weight is None
        and dense_weight is None
        and rrf_k is None
        and doc_max_chars is None
        and listwise_doc_max_chars is None
    ):
        return
    try:
        from mcp_server.services import get_state

        get_state().reset_searcher()
    except Exception as e:
        print(f"[WARN] Could not reset cached searcher: {e}", file=sys.stderr)


def _apply_centrality_stage(
    searcher: Any,
    query: str,
    raw_results: list[Any],
    k: int,
    alpha: float | None,
) -> list[Any]:
    """Replay the production GraphScoringStage (Block F) over benchmark results.

    The benchmark calls ``HybridSearcher.search()`` directly, which skips the
    orchestrator's centrality scoring stage (Blocker A) — ``blended_score`` /
    ``centrality_alpha`` never execute in this path.  This helper replays the
    production seam exactly (``SearchOrchestrator._assemble`` Blocks F–G):
    format SearchResults into result_view dicts, run ``GraphScoringStage``,
    then reorder the raw SearchResults to match the blended-score order.

    ``intent_decision`` is passed as ``None`` (skips only the synthetic
    module/community demotion; centrality blend + query-aware boosts still
    run because ``query`` is provided).

    Args:
        searcher: Initialized HybridSearcher instance.
        query: The benchmark query string.
        raw_results: SearchResult objects from ``HybridSearcher.search()``.
        k: Result count (drives the k*multiplier cap, as in production).
        alpha: ``centrality_alpha`` override for this run (None = config value).

    Returns:
        SearchResults reordered (and capped) like production; the original
        list unchanged if the stage cannot run.
    """
    if not raw_results:
        return raw_results
    try:
        import copy

        from mcp_server.tools.result_view import _format_search_results
        from search.config import get_search_config
        from search.graph_scoring_stage import GraphScoringStage

        # Mirror SearcherView.index_manager: .index_manager on
        # IntelligentSearcher, .dense_index on HybridSearcher.
        index_manager = getattr(searcher, "index_manager", None) or getattr(
            searcher, "dense_index", None
        )

        graph_cfg = copy.deepcopy(get_search_config().graph_enhanced)
        graph_cfg.centrality_annotation = True
        graph_cfg.centrality_reranking = True
        if alpha is not None:
            graph_cfg.centrality_alpha = alpha

        formatted = _format_search_results(raw_results)
        reordered, _subgraph = GraphScoringStage().run(
            query, None, k, formatted, index_manager, searcher, graph_cfg
        )

        # Map the reordered dicts back onto the raw SearchResult objects.
        # Duplicate chunk_ids (split_block fragments pre-dedup) are consumed
        # in order so each dict claims a distinct SearchResult.
        by_id: dict[str, list[Any]] = {}
        for r in raw_results:
            by_id.setdefault(r.chunk_id, []).append(r)
        out: list[Any] = []
        for item in reordered:
            bucket = by_id.get(item.get("chunk_id"))
            if bucket:
                out.append(bucket.pop(0))
        return out
    except Exception as e:
        print(f"[WARN] Centrality stage failed, using raw order: {e}", file=sys.stderr)
        return raw_results


def _get_searcher(project_path: str):
    """Get an initialized HybridSearcher for the given project."""
    try:
        from mcp_server.search_factory import get_searcher

        return get_searcher(project_path=project_path)
    except TypeError:
        # Fallback: some versions don't accept project_path as keyword arg
        from mcp_server.server import get_searcher  # type: ignore[import]

        return get_searcher()


def _run_query(
    searcher: Any, query: str, k: int, search_mode: str | None = None
) -> tuple[list[Any], float]:
    """Execute a single search query and return (raw SearchResult objects, latency_ms).

    Args:
        search_mode: When set, threaded explicitly into ``HybridSearcher.search()``.
            ``_apply_weight_overrides`` only updates ``cfg.search_mode.default_mode``,
            which ``HybridSearcher.search``'s ``search_mode`` parameter never reads
            (it defaults to ``SearchMode.HYBRID`` at the call site) — so ``--search-mode``
            was previously a silent no-op. Omitted (``None``) preserves prior default
            behaviour (hybrid) exactly.
    """
    start = time.perf_counter()
    kwargs = {"search_mode": search_mode} if search_mode else {}
    results = searcher.search(query, k=k, **kwargs)
    latency_ms = (time.perf_counter() - start) * 1000.0
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


# ---------------------------------------------------------------------------
# Per-query benchmark execution
# ---------------------------------------------------------------------------


def run_benchmark(
    *,
    searcher: Any,
    queries: list[dict[str, Any]],
    k: int,
    category_filter: str | None,
    verbose: bool,
    line_lookup: dict[str, tuple[str, int, int]] | None = None,
    search_mode: str | None = None,
    with_centrality: bool = False,
    centrality_alpha: float | None = None,
    merged_membership: dict[str, tuple[str, frozenset[str]]] | None = None,
) -> tuple[list[dict[str, Any]], list[float]]:
    """Run all queries and return (per_query_results, latencies).

    Args:
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
        with_centrality: Run the production ``GraphScoringStage`` (centrality
            blend + query-aware boosts) over each query's results, closing
            Blocker A for this run. Stage time is included in latency.
        centrality_alpha: ``centrality_alpha`` override (implies
            ``with_centrality``). None = config value.
        merged_membership: Pre-built merged-chunk membership lookup from
            ``_build_merged_membership_lookup``. When non-empty, merged chunks
            are credited for golden symbols they absorbed (containment
            credit); empty/None is an exact no-op vs strict scoring.

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

    for i, item in enumerate(filtered, 1):
        qid = item["id"]
        query = item["query"]
        category = item.get("category", "?")
        expected = item["expected"]  # already normalized in golden_dataset.json
        expected_primary = item.get("expected_primary", expected)

        prefix = f"  [{i:2d}/{len(filtered)}] [{qid}][{category}]"
        if verbose:
            print(f"{prefix} {query}")

        # Reset the pool-hit instrumentation so a query that never reaches a
        # rerank pass doesn't inherit the previous query's candidate pool.
        rerank_engine = getattr(searcher, "reranking_engine", None)
        if rerank_engine is not None:
            rerank_engine.last_candidate_ids = None

        try:
            raw_results, latency_ms = _run_query(
                searcher, query, k=k, search_mode=search_mode
            )
            if with_centrality or centrality_alpha is not None:
                stage_start = time.perf_counter()
                raw_results = _apply_centrality_stage(
                    searcher, query, raw_results, k, centrality_alpha
                )
                latency_ms += (time.perf_counter() - stage_start) * 1000.0
            latencies.append(latency_ms)

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
                print(
                    f"          [{status}] R@5={metrics['recall@5']:.2f}  "
                    f"MRR={metrics['mrr']:.3f}  NDCG@5={metrics['ndcg@5']:.3f}  "
                    f"({latency_ms:.0f} ms){line_str}"
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
                    **({"containment_credits": containment} if containment else {}),
                    **metrics,
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
        "--bm25-reserved-slots",
        type=int,
        help=(
            "Override search_mode.bm25_reserved_slots (fused-pool slots reserved "
            "for BM25-unique candidates) for this run. Default: use config "
            "value (0 = disabled)."
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
        "--with-centrality",
        action="store_true",
        help=(
            "Run the production GraphScoringStage (centrality blend + query-aware "
            "boosts) over each query's results — the benchmark calls "
            "HybridSearcher.search() directly and skips this stage otherwise "
            "(Blocker A). Uses graph_enhanced.centrality_alpha from config unless "
            "--centrality-alpha is given."
        ),
    )
    parser.add_argument(
        "--centrality-alpha",
        type=float,
        help=(
            "Override graph_enhanced.centrality_alpha (0=semantic only, "
            "1=centrality only) for this run. Implies --with-centrality. "
            "Default: use config value (0.2)."
        ),
    )
    parser.add_argument(
        "--reranker-sweep",
        action="store_true",
        help="Run reranker comparison across predefined models (see RERANKER_SWEEP)",
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


def run_single(
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
    with_centrality: bool = False,
    centrality_alpha: float | None = None,
    reranker_doc_max_chars: int | None = None,
    reranker_listwise_doc_max_chars: int | None = None,
) -> dict[str, Any]:
    """Execute one benchmark run and return the result dict."""
    _apply_weight_overrides(bm25_weight, dense_weight, search_mode)
    _apply_reranker_override(reranker_model, reranker_enabled)
    _apply_reranker_budget_override(top_k_candidates)
    _apply_reranker_doc_max_chars_override(
        reranker_doc_max_chars, reranker_listwise_doc_max_chars
    )
    _apply_rrf_k_override(rrf_k)
    _apply_reserved_slots_override(bm25_reserved_slots)
    _maybe_reset_for_construction_overrides(
        bm25_weight,
        dense_weight,
        rrf_k,
        reranker_doc_max_chars,
        reranker_listwise_doc_max_chars,
    )

    try:
        searcher = _get_searcher(project_path)
    except Exception as exc:
        print(f"[ERROR] Could not initialize searcher: {exc}", file=sys.stderr)
        print("[ERROR] Make sure an index is built for this project.", file=sys.stderr)
        sys.exit(1)

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
    if rrf_k is not None:
        print(f"  RRF fusion constant: rrf_k={rrf_k}")
    if bm25_reserved_slots is not None:
        print(f"  BM25 reserved pool slots: {bm25_reserved_slots}")
    if with_centrality or centrality_alpha is not None:
        alpha_str = "config default" if centrality_alpha is None else centrality_alpha
        print(f"  Centrality stage: ON (alpha={alpha_str})")

    # Reset peak VRAM stats and issue a warm-up search so a reranker model swap's
    # first-call load/download cost lands here, not in the timed latency average.
    torch_module = None
    if reranker_model is not None or reranker_enabled is not None:
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

    # Build line-range lookup for line-overlap metrics (one-time scan of MetadataStore)
    line_lookup = _build_line_lookup(searcher)
    # Merged-chunk membership for containment-credit scoring (empty = no-op)
    merged_membership = _build_merged_membership_lookup(searcher)

    per_query, latencies = run_benchmark(
        searcher=searcher,
        queries=queries,
        k=k,
        category_filter=category_filter,
        verbose=verbose,
        line_lookup=line_lookup,
        search_mode=search_mode,
        with_centrality=with_centrality,
        centrality_alpha=centrality_alpha,
        merged_membership=merged_membership,
    )

    dataset_thresholds = dataset.get("thresholds") or {}
    agg = aggregate_metrics(per_query, thresholds=dataset_thresholds)
    avg_lat = round(mean(latencies), 1) if latencies else 0.0

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
    if rrf_k is not None:
        config_metadata["rrf_k"] = rrf_k
    if bm25_reserved_slots is not None:
        config_metadata["bm25_reserved_slots"] = bm25_reserved_slots
    if with_centrality or centrality_alpha is not None:
        config_metadata["with_centrality"] = True
        config_metadata["centrality_alpha"] = (
            centrality_alpha if centrality_alpha is not None else "config_default"
        )
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
    # Require project path for search runs
    # -----------------------------------------------------------------------
    if not args.project_path:
        parser.error(
            "--project-path is required (or use --compare to compare saved results)"
        )

    project_path = str(Path(args.project_path).resolve())
    _setup_project(project_path)

    dataset = _load_golden_dataset(Path(args.golden_dataset))
    verbose = not args.quiet
    reranker_enabled = (
        None if args.reranker_enabled is None else args.reranker_enabled == "true"
    )

    # -----------------------------------------------------------------------
    # Reranker sweep mode: run predefined rerankers head-to-head
    # -----------------------------------------------------------------------
    if args.reranker_sweep:
        print(f"\n{'=' * 70}")
        print("RERANKER SWEEP: model comparison")
        print(f"{'=' * 70}")
        reranker_results: list[dict[str, Any]] = []
        for sweep_cfg in RERANKER_SWEEP:
            result = run_single(
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
                rrf_k=args.rrf_k,
                bm25_reserved_slots=args.bm25_reserved_slots,
                with_centrality=args.with_centrality,
                centrality_alpha=args.centrality_alpha,
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
            result = run_single(
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
                rrf_k=args.rrf_k,
                bm25_reserved_slots=args.bm25_reserved_slots,
                with_centrality=args.with_centrality,
                centrality_alpha=args.centrality_alpha,
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
    result = run_single(
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
        rrf_k=args.rrf_k,
        bm25_reserved_slots=args.bm25_reserved_slots,
        with_centrality=args.with_centrality,
        centrality_alpha=args.centrality_alpha,
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
    main()
