#!/usr/bin/env python3
"""SSCG Automated Benchmark Runner.

Evaluates retrieval quality against the 13-query SSCG golden dataset.
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
    calculate_metrics_from_results,
    normalize_chunk_ids,
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


def _get_searcher(project_path: str):
    """Get an initialized HybridSearcher for the given project."""
    try:
        from mcp_server.search_factory import get_searcher

        return get_searcher(project_path=project_path)
    except TypeError:
        # Fallback: some versions don't accept project_path as keyword arg
        from mcp_server.server import get_searcher  # type: ignore[import]

        return get_searcher()


def _run_query(searcher: Any, query: str, k: int) -> tuple[list[str], float]:
    """Execute a single search query and return (normalized_chunk_ids, latency_ms)."""
    start = time.perf_counter()
    results = searcher.search(query, k=k)
    latency_ms = (time.perf_counter() - start) * 1000.0
    raw_ids = [r.chunk_id for r in results]
    normalized = normalize_chunk_ids(raw_ids)
    return normalized, latency_ms


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
) -> tuple[list[dict[str, Any]], list[float]]:
    """Run all queries and return (per_query_results, latencies).

    Args:
        searcher: Initialized HybridSearcher instance.
        queries: List of query dicts from golden_dataset.json.
        k: Number of search results to retrieve.
        category_filter: If set, only run queries in this category.
        verbose: Print per-query details.

    Returns:
        Tuple of (per_query_results, latencies).
    """
    filtered = queries
    if category_filter:
        filtered = [q for q in queries if q.get("category") == category_filter]
        print(f"  Filtered to {len(filtered)} queries in category '{category_filter}'")

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

        try:
            retrieved, latency_ms = _run_query(searcher, query, k=k)
            latencies.append(latency_ms)

            metrics = calculate_metrics_from_results(
                retrieved=retrieved,
                expected=expected,
                expected_primary=expected_primary,
            )

            status = "HIT " if metrics["hit"] else "MISS"
            if verbose:
                print(
                    f"          [{status}] R@5={metrics['recall@5']:.2f}  "
                    f"MRR={metrics['mrr']:.3f}  NDCG@5={metrics['ndcg@5']:.3f}  "
                    f"({latency_ms:.0f} ms)"
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
                    **metrics,
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
                    "recall@1": 0.0,
                    "recall@5": 0.0,
                    "recall@10": 0.0,
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
    sep = "=" * 80
    print(f"\n{sep}\n{title}\n{sep}")
    header = f"{'Config':<22} {'MRR':>6} {'R@5':>6} {'R@10':>6} {'HR@5':>6} {'NDCG@5':>8} {'Lat(ms)':>8} {'MRR':>5} {'R@5':>5} {'HR@5':>5}"
    print(header)
    print("-" * 80)
    for run in runs:
        agg = run["aggregate"]
        pf = agg.get("pass_fail", {})
        pf_str = f"{pf.get('mrr', '?'):>5} {pf.get('recall@5', '?'):>5} {pf.get('hit_rate@5', '?'):>5}"
        lat = run.get("avg_latency_ms", agg.get("avg_latency_ms", 0))
        print(
            f"{run['config_name']:<22} "
            f"{agg['mrr']:>6.3f} {agg['recall@5']:>6.3f} {agg['recall@10']:>6.3f} "
            f"{agg['hit_rate@5']:>6.3f} {agg['ndcg@5']:>8.3f} "
            f"{lat:>8.0f} {pf_str}"
        )
    print(sep)


def print_per_query_drilldown(
    per_query: list[dict[str, Any]], config_name: str
) -> None:
    """Print per-query results for a single run (Lesson 2 drill-down pattern)."""
    print(f"\n--- Per-query drill-down: {config_name} ---")
    print(
        f"{'ID':<5} {'Cat':<3} {'R@5':>6} {'MRR':>6} {'NDCG@5':>8} {'Status':<5} Query"
    )
    print("-" * 70)
    for q in per_query:
        status = "HIT" if q.get("hit") else "MISS"
        r5 = q.get("recall@5", 0.0)
        mrr = q.get("mrr", 0.0)
        ndcg = q.get("ndcg@5", 0.0)
        query_short = q["query"][:35]
        print(
            f"{q['id']:<5} {q.get('category', '?'):<3} {r5:>6.3f} {mrr:>6.3f} {ndcg:>8.3f} {status:<5} {query_short}"
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
        choices=["A", "B", "C"],
        help="Filter queries by category (A=small_function, B=sibling, C=class_overview)",
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
) -> dict[str, Any]:
    """Execute one benchmark run and return the result dict."""
    _apply_weight_overrides(bm25_weight, dense_weight, search_mode)

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

    per_query, latencies = run_benchmark(
        searcher=searcher,
        queries=queries,
        k=k,
        category_filter=category_filter,
        verbose=verbose,
    )

    agg = aggregate_metrics(per_query)
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

    return {
        "config_name": config_name,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "aggregate": agg,
        "avg_latency_ms": avg_lat,
        "config_metadata": config_metadata,
        "thresholds": dataset.get("thresholds", THRESHOLDS),
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
    )

    # Print leaderboard (single row)
    print_leaderboard([result])

    # Per-query drill-down (Lesson 2 pattern)
    if not args.no_drilldown and verbose:
        print_per_query_drilldown(result["per_query"], result["config_name"])

    # Pass/fail summary
    pf = result["aggregate"].get("pass_fail", {})
    all_pass = all(v == "PASS" for v in pf.values())
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    for metric, status in pf.items():
        threshold = THRESHOLDS.get(
            metric.replace("@", "_at_").replace("hit_rate_at_5", "hit_rate_at_5"), "?"
        )
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
