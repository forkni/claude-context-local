#!/usr/bin/env python3
"""Direct-caller recall benchmark.

Evaluates how many of the expected direct callers find_connections() returns.
Reads evaluation/caller_golden.json (or --golden-path) for ground truth.
Calls RelationshipAnalyzer.analyze_impact() directly (in-process, requires .venv).

Usage:
    # Run against live index, using default caller_golden.json
    ./scripts/benchmark/run_caller_recall.sh --project-path F:/RD_PROJECTS/...

    # Save baseline (before fix commits)
    ./scripts/benchmark/run_caller_recall.sh --project-path /path \\
        --output results/caller_recall_baseline.json

    # Compare two saved runs
    ./scripts/benchmark/run_caller_recall.sh \\
        --compare results/caller_recall_baseline.json results/caller_recall_fixed.json

    # Single target quick-check
    ./scripts/benchmark/run_caller_recall.sh --project-path /path \\
        --target C002
"""

import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    calculate_precision_at_k,
    calculate_recall_at_k,
    normalize_chunk_id,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_GOLDEN_PATH = _PROJECT_ROOT / "evaluation" / "caller_golden.json"
DEFAULT_K = 50  # max callers to retrieve per target


def _load_golden(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _get_searcher(project_path: str) -> Any:
    try:
        from mcp_server.search_factory import get_searcher

        return get_searcher(project_path=project_path)
    except TypeError:
        from mcp_server.server import get_searcher  # type: ignore[import]

        return get_searcher()


def _get_direct_callers(
    analyzer: Any,
    target_chunk_id: str,
    max_depth: int = 1,
) -> list[str]:
    """Call analyze_impact and return normalized chunk IDs of direct callers.

    Strips split_block duplicates by normalizing chunk IDs (line ranges stripped).
    """
    try:
        report = analyzer.analyze_impact(
            chunk_id=target_chunk_id,
            max_depth=max_depth,
        )
        raw_callers = [c.get("chunk_id", "") for c in (report.direct_callers or [])]
    except Exception as e:
        print(f"    [ERROR] analyze_impact failed: {e}", file=sys.stderr)
        raw_callers = []

    # Normalize + deduplicate
    seen: set[str] = set()
    result: list[str] = []
    for cid in raw_callers:
        if not cid:
            continue
        norm = normalize_chunk_id(cid)
        if norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def _run_single(
    query: dict[str, Any],
    analyzer: Any,
    k: int,
    verbose: bool = True,
) -> dict[str, Any]:
    """Evaluate one query and return a result dict."""
    qid = query["id"]
    target = normalize_chunk_id(query["target_chunk_id"])
    expected = [normalize_chunk_id(c) for c in query.get("expected_callers", [])]

    if verbose:
        print(f"  [{qid}] {target}", flush=True)

    t0 = time.perf_counter()
    retrieved = _get_direct_callers(analyzer, target)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Trim to k for metric computation
    retrieved_k = retrieved[:k]

    recall = calculate_recall_at_k(retrieved_k, expected, k=len(expected) or 1)
    precision = calculate_precision_at_k(
        retrieved_k, expected, k=max(len(retrieved_k), 1)
    )

    # Per-caller breakdown: which expected callers were found / missed
    expected_set = set(expected)
    retrieved_set = set(retrieved_k)
    found = sorted(expected_set & retrieved_set)
    missed = sorted(expected_set - retrieved_set)
    extra = sorted(retrieved_set - expected_set)

    row: dict[str, Any] = {
        "id": qid,
        "target": target,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "retrieved_count": len(retrieved),
        "expected_count": len(expected),
        "found": found,
        "missed": missed,
        "extra": extra,
        "latency_ms": round(latency_ms, 1),
    }

    if verbose:
        status = "OK" if recall == 1.0 else ("PARTIAL" if recall > 0 else "MISS")
        print(
            f"    recall={recall:.2f} precision={precision:.2f} "
            f"retrieved={len(retrieved)} expected={len(expected)} [{status}]"
        )
        if missed:
            print(f"    missed: {missed}")

    return row


# ---------------------------------------------------------------------------
# Compare mode
# ---------------------------------------------------------------------------


def _compare(file_a: str, file_b: str) -> None:
    """Print a delta table comparing two saved benchmark result JSONs."""
    with open(file_a) as f:
        data_a = json.load(f)
    with open(file_b) as f:
        data_b = json.load(f)

    rows_a = {r["id"]: r for r in data_a.get("results", [])}
    rows_b = {r["id"]: r for r in data_b.get("results", [])}
    all_ids = sorted(set(rows_a) | set(rows_b))

    label_a = Path(file_a).stem
    label_b = Path(file_b).stem

    print(f"\nComparison: {label_a} → {label_b}")
    print(f"{'ID':<8} {'recall_a':>9} {'recall_b':>9} {'delta':>7} {'missed_delta'}")
    print("-" * 60)

    deltas_recall: list[float] = []
    for qid in all_ids:
        a = rows_a.get(qid, {})
        b = rows_b.get(qid, {})
        r_a = a.get("recall", float("nan"))
        r_b = b.get("recall", float("nan"))
        delta = r_b - r_a if r_a == r_a and r_b == r_b else float("nan")
        if delta == delta:
            deltas_recall.append(delta)

        missed_a = set(a.get("missed", []))
        missed_b = set(b.get("missed", []))
        now_found = sorted(missed_a - missed_b)
        still_missed = sorted(missed_b - missed_a)

        delta_str = f"{delta:+.3f}" if delta == delta else "   N/A"
        changes = ""
        if now_found:
            changes = f"+{len(now_found)} recovered"
        if still_missed:
            changes += f" -{len(still_missed)} still missing"

        print(f"{qid:<8} {r_a:>9.4f} {r_b:>9.4f} {delta_str:>7}  {changes}")

    if deltas_recall:
        mean_delta = mean(deltas_recall)
        print("-" * 60)
        print(
            f"{'MEAN':<8} {data_a.get('aggregate', {}).get('mean_recall', 0):>9.4f} "
            f"{data_b.get('aggregate', {}).get('mean_recall', 0):>9.4f} "
            f"{mean_delta:>+7.4f}"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Direct-caller recall benchmark for find_connections()"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Run mode
    run_p = subparsers.add_parser("run", help="Run recall benchmark (default)")
    run_p.add_argument("--project-path", required=True, help="Indexed project path")
    run_p.add_argument(
        "--golden-path",
        default=str(DEFAULT_GOLDEN_PATH),
        help=f"Path to caller_golden.json (default: {DEFAULT_GOLDEN_PATH})",
    )
    run_p.add_argument("--output", help="Save results JSON to this path")
    run_p.add_argument(
        "--target",
        action="append",
        dest="target_ids",
        metavar="ID",
        help="Filter to specific query IDs (e.g. C001). Repeatable.",
    )
    run_p.add_argument(
        "--k",
        type=int,
        default=DEFAULT_K,
        help=f"Max callers to retrieve per target (default: {DEFAULT_K})",
    )
    run_p.add_argument("--quiet", action="store_true", help="Suppress per-query output")

    # Compare mode
    cmp_p = subparsers.add_parser("compare", help="Compare two saved result JSONs")
    cmp_p.add_argument("file_a", help="First results JSON (baseline)")
    cmp_p.add_argument("file_b", help="Second results JSON (after fix)")

    # Handle bare --compare (legacy shorthand from run_benchmark.sh style)
    if "--compare" in sys.argv:
        idx = sys.argv.index("--compare")
        files = sys.argv[idx + 1 : idx + 3]
        if len(files) == 2:
            _compare(files[0], files[1])
            return

    args = parser.parse_args()

    if args.command == "compare":
        _compare(args.file_a, args.file_b)
        return

    # Default: run mode (even if no subcommand given, try to parse as run)
    if args.command is None:
        # Re-parse with run defaults
        args = run_p.parse_args(sys.argv[1:])

    golden_path = Path(args.golden_path)
    if not golden_path.exists():
        print(f"[ERROR] Golden file not found: {golden_path}", file=sys.stderr)
        print(
            "  Run scripts/benchmark/build_caller_oracle.py to build it.",
            file=sys.stderr,
        )
        sys.exit(1)

    dataset = _load_golden(golden_path)
    queries = dataset.get("queries", [])

    if args.target_ids:
        queries = [q for q in queries if q["id"] in set(args.target_ids)]
        if not queries:
            print(
                f"[ERROR] No queries matched target IDs: {args.target_ids}",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"[INFO] Project: {args.project_path}")
    print(f"[INFO] Golden: {golden_path} ({len(queries)} queries)")

    # Load searcher and build RelationshipAnalyzer
    print("[INFO] Loading searcher...")
    searcher = _get_searcher(args.project_path)

    from search.relationship_analyzer import RelationshipAnalyzer  # noqa: E402

    analyzer = RelationshipAnalyzer.from_searcher(searcher)
    print(f"[INFO] RelationshipAnalyzer ready: {type(analyzer).__name__}")

    # Run all queries
    print(f"\n[INFO] Running {len(queries)} queries (k={args.k})...")
    results: list[dict[str, Any]] = []
    for q in queries:
        row = _run_single(q, analyzer, k=args.k, verbose=not args.quiet)
        results.append(row)

    # Aggregate
    recalls = [r["recall"] for r in results]
    precisions = [r["precision"] for r in results]
    total_expected = sum(r["expected_count"] for r in results)
    total_found = sum(len(r["found"]) for r in results)
    total_missed = sum(len(r["missed"]) for r in results)
    perfect = sum(1 for r in results if r["recall"] == 1.0)

    agg: dict[str, Any] = {
        "mean_recall": round(mean(recalls), 4) if recalls else 0.0,
        "mean_precision": round(mean(precisions), 4) if precisions else 0.0,
        "perfect_recall_count": perfect,
        "total_queries": len(results),
        "total_expected_callers": total_expected,
        "total_found_callers": total_found,
        "total_missed_callers": total_missed,
    }

    print("\n" + "=" * 60)
    print("DIRECT-CALLER RECALL SUMMARY")
    print("=" * 60)
    print(f"  Queries:             {len(results)}")
    print(f"  Mean Recall:         {agg['mean_recall']:.4f}")
    print(f"  Mean Precision:      {agg['mean_precision']:.4f}")
    print(f"  Perfect recall (1.0): {perfect}/{len(results)}")
    print(f"  Callers found:       {total_found}/{total_expected}")
    print(f"  Callers missed:      {total_missed}")

    output_data: dict[str, Any] = {
        "aggregate": agg,
        "results": results,
        "meta": {
            "project_path": str(args.project_path),
            "golden_path": str(golden_path),
            "k": args.k,
        },
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        print(f"\n[INFO] Results saved to: {out_path}")
    else:
        print("\n(Use --output FILE to save results for comparison)")


if __name__ == "__main__":
    main()
