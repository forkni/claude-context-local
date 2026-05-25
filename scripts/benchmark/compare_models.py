#!/usr/bin/env python3
"""Differential benchmark: compare retrieval quality across two embedding models.

Phase A of semantic model routing validation. Confirms whether bge_code outperforms
qwen3 on code queries from domains NOT covered by routing_keywords.yaml (e.g.
StreamDiffusion: VAE, UNet, CUDA IPC, ControlNet).

Decision gate:
  bge_code wins  → proceed to Phase B (semantic anchor-based routing)
  qwen3 wins     → routing stays; conservative keyword threshold was intentional

Usage:
    # Qualitative side-by-side (no golden labels required)
    ./scripts/benchmark/compare_models.sh \\
        --project-path D:/dev/.../StreamDiffusion

    # Rigorous MRR/Recall scoring (requires labeled golden dataset)
    ./scripts/benchmark/compare_models.sh \\
        --project-path D:/dev/.../StreamDiffusion \\
        --golden-dataset evaluation/streamdiffusion_golden.json

    # Override which models to compare
    ./scripts/benchmark/compare_models.sh \\
        --project-path D:/dev/.../StreamDiffusion \\
        --model-a bge_code --model-b qwen3

    # Compare previously saved result JSONs
    ./scripts/benchmark/compare_models.sh \\
        --compare results/run_bge.json results/run_qwen.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


# Add project root to sys.path so imports resolve from any working directory
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    aggregate_metrics,
    calculate_metrics_from_results,
    normalize_chunk_ids,
)


# ---------------------------------------------------------------------------
# Default query set: 11 real StreamDiffusion queries from mcp_server.log
# (logged at lines 1017, 1522, 1811, 1916, 2022, 2148, 2285, 2398, 2613, 2902, 3189)
# plus 4 additional representative code queries for broader coverage.
# ---------------------------------------------------------------------------
STREAMDIFFUSION_QUERIES: list[dict[str, str]] = [
    # Logged queries (domain: StreamDiffusion — VAE, UNet, IPC, ControlNet)
    {"id": "SD01", "query": "main inference loop per-frame call image to image"},
    {"id": "SD02", "query": "VAE encode image to latent"},
    {"id": "SD03", "query": "VAE decode latent to image output tensor"},
    {"id": "SD04", "query": "UNet denoising step predict noise residual scheduler"},
    {"id": "SD05", "query": "CUDA IPC import get_frame zero-copy receive input"},
    {"id": "SD06", "query": "TouchDesigner per-frame cook run inference call write"},
    {"id": "SD07", "query": "update_control_image set controlnet hint image tensor"},
    {"id": "SD08", "query": "controlnet module prepare control image preprocess"},
    {"id": "SD09", "query": "_ipc_pack_rgba convert pipeline output to HWC uint8"},
    {"id": "SD10", "query": "profiler region NVTX range_push range_pop CUDA event"},
    {"id": "SD11", "query": "_process_controlnet_frame CUDA IPC get_frame update"},
    # Extended queries: broader coverage of StreamDiffusion code domain
    {"id": "SD12", "query": "denoising timestep alpha_prod scheduler step"},
    {
        "id": "SD13",
        "query": "stream diffusion pipeline initialization model load warmup",
    },
    {"id": "SD14", "query": "latent noise addition blend alpha beta diffusion"},
    {"id": "SD15", "query": "CUDA stream synchronize event record wait"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_searcher_for_model(project_path: str, model_key: str) -> Any:
    """Get an initialized HybridSearcher for the given project and model."""
    from mcp_server.search_factory import get_searcher

    return get_searcher(project_path=project_path, model_key=model_key)


def _run_query(searcher: Any, query: str, k: int) -> tuple[list[Any], float]:
    """Execute one search query and return (raw SearchResult objects, latency_ms)."""
    start = time.perf_counter()
    results = searcher.search(query, k=k)
    latency_ms = (time.perf_counter() - start) * 1000.0
    return results, latency_ms


def _run_model(
    project_path: str,
    model_key: str,
    queries: list[dict[str, str]],
    k: int,
    golden: dict[str, list[str]] | None,
    verbose: bool,
) -> dict[str, Any]:
    """Run all queries through one model and return result dict.

    Args:
        project_path: Path to indexed project.
        model_key: Model key, e.g. "bge_code" or "qwen3".
        queries: List of ``{"id": ..., "query": ...}`` dicts.
        k: Top-k results to retrieve.
        golden: Optional ``{query_id: [expected_chunk_ids]}`` for metric scoring.
        verbose: Print per-query output.

    Returns:
        Dict with model_key, per_query results, aggregate metrics, avg_latency_ms.
    """
    print(f"\n{'=' * 60}")
    print(f"Model: {model_key}  |  k={k}  |  {len(queries)} queries")
    print(f"{'=' * 60}")

    try:
        searcher = _get_searcher_for_model(project_path, model_key)
    except Exception as exc:
        print(
            f"[ERROR] Could not load searcher for model '{model_key}': {exc}",
            file=sys.stderr,
        )
        print(
            f"[ERROR] Ensure project is indexed with model '{model_key}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    per_query: list[dict[str, Any]] = []
    latencies: list[float] = []

    for i, item in enumerate(queries, 1):
        qid = item["id"]
        query = item["query"]
        prefix = f"  [{i:2d}/{len(queries)}] [{qid}]"

        try:
            raw_results, latency_ms = _run_query(searcher, query, k=k)
            latencies.append(latency_ms)

            retrieved_ids = [r.chunk_id for r in raw_results]
            retrieved_norm = normalize_chunk_ids(retrieved_ids)

            result_entry: dict[str, Any] = {
                "id": qid,
                "query": query,
                "model_key": model_key,
                "retrieved": retrieved_norm[:k],
                "retrieved_raw": retrieved_ids[:k],
                "latency_ms": round(latency_ms, 1),
            }

            if golden and qid in golden:
                expected = golden[qid]
                metrics = calculate_metrics_from_results(
                    retrieved=retrieved_norm,
                    expected=expected,
                    expected_primary=expected,
                )
                result_entry.update(metrics)
                status = "HIT " if metrics["hit"] else "MISS"
                if verbose:
                    print(
                        f"{prefix} [{status}] MRR={metrics['mrr']:.3f} "
                        f"R@5={metrics['recall@5']:.3f}  ({latency_ms:.0f}ms)  {query[:50]}"
                    )
            else:
                result_entry.update({"hit": False, "mrr": 0.0, "recall@5": 0.0})
                if verbose:
                    top3 = "  |  ".join(r.split(":")[-1] for r in retrieved_norm[:3])
                    print(f"{prefix} ({latency_ms:.0f}ms)  {query[:45]}  ->  {top3}")

            per_query.append(result_entry)

        except Exception as exc:
            print(f"{prefix} [ERROR] {exc}", file=sys.stderr)
            per_query.append(
                {
                    "id": qid,
                    "query": query,
                    "model_key": model_key,
                    "error": str(exc),
                    "retrieved": [],
                    "latency_ms": 0.0,
                    "hit": False,
                    "mrr": 0.0,
                    "recall@5": 0.0,
                }
            )

    from statistics import mean

    avg_lat = round(mean(latencies), 1) if latencies else 0.0

    agg: dict[str, Any] = {}
    if golden:
        agg = aggregate_metrics(per_query)

    return {
        "model_key": model_key,
        "config_name": model_key,
        "project_path": project_path,
        "k": k,
        "avg_latency_ms": avg_lat,
        "per_query": per_query,
        "aggregate": agg,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


# ---------------------------------------------------------------------------
# Output: side-by-side qualitative comparison
# ---------------------------------------------------------------------------


def print_side_by_side(
    run_a: dict[str, Any],
    run_b: dict[str, Any],
    k_display: int = 5,
) -> None:
    """Print top-k results side-by-side per query for human judgment."""
    model_a = run_a["model_key"]
    model_b = run_b["model_key"]

    qa_map = {r["id"]: r for r in run_a["per_query"]}
    qb_map = {r["id"]: r for r in run_b["per_query"]}
    all_ids = list(qa_map.keys())

    overlap_totals: list[float] = []

    print(f"\n{'=' * 90}")
    print(f"SIDE-BY-SIDE COMPARISON:  {model_a}  vs  {model_b}  (top {k_display})")
    print(f"{'=' * 90}")

    for qid in all_ids:
        ra = qa_map.get(qid, {})
        rb = qb_map.get(qid, {})
        query = ra.get("query") or rb.get("query", "?")
        print(f"\n[{qid}] {query}")

        a_results = ra.get("retrieved", [])[:k_display]
        b_results = rb.get("retrieved", [])[:k_display]

        # Compute overlap
        set_a = set(a_results)
        set_b = set(b_results)
        overlap = len(set_a & set_b)
        union = len(set_a | set_b)
        overlap_pct = overlap / union * 100 if union > 0 else 0.0
        overlap_totals.append(overlap_pct)

        a_only = set_a - set_b
        b_only = set_b - set_a

        print(
            f"  {model_a:<12} | {model_b:<12} | overlap {overlap}/{max(len(a_results), len(b_results))} ({overlap_pct:.0f}%)"
        )
        print(f"  {'-' * 50}")
        max_rows = max(len(a_results), len(b_results))
        for i in range(max_rows):
            a_chunk = _short_chunk_id(a_results[i]) if i < len(a_results) else ""
            b_chunk = _short_chunk_id(b_results[i]) if i < len(b_results) else ""
            a_mark = "<" if (i < len(a_results) and a_results[i] in a_only) else " "
            b_mark = ">" if (i < len(b_results) and b_results[i] in b_only) else " "
            print(f"  [{i + 1}] {a_mark}{a_chunk:<38} {b_mark}{b_chunk}")

    avg_overlap = sum(overlap_totals) / len(overlap_totals) if overlap_totals else 0.0
    print(f"\n  Average overlap: {avg_overlap:.1f}%")
    print("  < = unique to left model   > = unique to right model")
    print("=" * 90)


def _short_chunk_id(chunk_id: str) -> str:
    """Shorten a chunk ID for compact display."""
    # Show file basename + symbol name (last two parts after last /)
    parts = chunk_id.split("/")
    tail = parts[-1] if parts else chunk_id
    # Truncate long tails
    return tail[:38] if len(tail) > 38 else tail


# ---------------------------------------------------------------------------
# Output: aggregate metrics leaderboard (when golden dataset available)
# ---------------------------------------------------------------------------


def print_comparison_leaderboard(
    run_a: dict[str, Any],
    run_b: dict[str, Any],
) -> None:
    """Print aggregate MRR/Recall leaderboard when golden data is available."""
    runs = [run_a, run_b]
    width = 80
    sep = "=" * width
    print(f"\n{sep}\nMODEL COMPARISON LEADERBOARD\n{sep}")
    print(
        f"{'Model':<15} {'MRR':>6} {'R@5':>6} {'R@10':>6} {'HR@5':>6} "
        f"{'NDCG@5':>8} {'Lat(ms)':>8}"
    )
    print("-" * width)
    for run in runs:
        agg = run.get("aggregate", {})
        if not agg:
            print(f"  {run['model_key']:<15} (no golden dataset — qualitative mode)")
            continue
        lat = run.get("avg_latency_ms", 0)
        print(
            f"  {run['model_key']:<13} "
            f"{agg.get('mrr', 0):>6.3f} {agg.get('recall@5', 0):>6.3f} "
            f"{agg.get('recall@10', 0):>6.3f} {agg.get('hit_rate@5', 0):>6.3f} "
            f"{agg.get('ndcg@5', 0):>8.3f} {lat:>8.0f}"
        )
    print(sep)

    # Per-query delta table
    qa_map = {r["id"]: r for r in run_a["per_query"]}
    qb_map = {r["id"]: r for r in run_b["per_query"]}
    print(
        f"\n--- Per-query comparison: {run_a['model_key']} vs {run_b['model_key']} ---"
    )
    print(
        f"{'ID':<6} {'MRR-A':>6} {'MRR-B':>6} {'dMRR':>7} {'R5-A':>6} {'R5-B':>6} {'Winner':<10} Query"
    )
    print("-" * 90)
    a_wins = b_wins = ties = 0
    for qid in qa_map:
        qa = qa_map.get(qid, {})
        qb = qb_map.get(qid, {})
        mrr_a = qa.get("mrr", 0.0)
        mrr_b = qb.get("mrr", 0.0)
        r5_a = qa.get("recall@5", 0.0)
        r5_b = qb.get("recall@5", 0.0)
        dmrr = mrr_b - mrr_a
        if abs(dmrr) < 0.001:
            winner = "TIE"
            ties += 1
        elif dmrr > 0:
            winner = f"▶ {run_b['model_key']}"
            b_wins += 1
        else:
            winner = f"◀ {run_a['model_key']}"
            a_wins += 1
        query_short = qa.get("query", "?")[:30]
        print(
            f"{qid:<6} {mrr_a:>6.3f} {mrr_b:>6.3f} "
            f"{'+' if dmrr >= 0 else ''}{dmrr:>6.3f} "
            f"{r5_a:>6.3f} {r5_b:>6.3f} {winner:<10} {query_short}"
        )
    print(
        f"\nSummary: {run_a['model_key']} wins={a_wins}  {run_b['model_key']} wins={b_wins}  ties={ties}"
    )


# ---------------------------------------------------------------------------
# Compare saved JSON files
# ---------------------------------------------------------------------------


def compare_saved_runs(result_files: list[str]) -> None:
    """Load two saved comparison JSONs and print leaderboard."""
    if len(result_files) != 2:
        print("[ERROR] --compare requires exactly 2 result files", file=sys.stderr)
        sys.exit(1)
    runs = []
    for f in result_files:
        with open(f, encoding="utf-8") as fh:
            runs.append(json.load(fh))
    print_comparison_leaderboard(runs[0], runs[1])
    print_side_by_side(runs[0], runs[1])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Differential model benchmark: compare two embedding models on code queries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--project-path",
        help="Path to indexed project (required unless --compare is used)",
    )
    parser.add_argument(
        "--model-a",
        default="bge_code",
        help="First model key (default: bge_code)",
    )
    parser.add_argument(
        "--model-b",
        default="qwen3",
        help="Second model key (default: qwen3)",
    )
    parser.add_argument(
        "--golden-dataset",
        help="Optional: path to golden_dataset.json for rigorous MRR/Recall scoring",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of search results to retrieve per query (default: 5)",
    )
    parser.add_argument(
        "--queries",
        help="Optional: path to JSON file with custom queries [{id, query}]",
    )
    parser.add_argument(
        "--output",
        help="Path to save JSON results (default: benchmark_results/compare_<timestamp>.json)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar="RESULT_JSON",
        help="Compare two saved result JSON files instead of running new searches",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-query output",
    )
    parser.add_argument(
        "--no-side-by-side",
        action="store_true",
        help="Skip side-by-side chunk comparison (faster output)",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.compare:
        compare_saved_runs(args.compare)
        return

    if not args.project_path:
        parser.error("--project-path is required (or use --compare for saved results)")

    project_path = str(Path(args.project_path).resolve())

    # Load query set
    if args.queries:
        with open(args.queries, encoding="utf-8") as f:
            queries = json.load(f)
        print(f"[INFO] Loaded {len(queries)} queries from {args.queries}")
    else:
        queries = STREAMDIFFUSION_QUERIES
        print(f"[INFO] Using {len(queries)} default StreamDiffusion queries")

    # Load golden dataset if provided
    golden: dict[str, list[str]] | None = None
    if args.golden_dataset:
        with open(args.golden_dataset, encoding="utf-8") as f:
            ds = json.load(f)
        golden = {
            q["id"]: q.get("expected_primary", q["expected"])
            for q in ds.get("queries", [])
        }
        print(f"[INFO] Loaded golden labels for {len(golden)} queries")

    verbose = not args.quiet

    # Run model A (bge_code by default)
    run_a = _run_model(
        project_path=project_path,
        model_key=args.model_a,
        queries=queries,
        k=args.k,
        golden=golden,
        verbose=verbose,
    )

    # Run model B (qwen3 by default)
    run_b = _run_model(
        project_path=project_path,
        model_key=args.model_b,
        queries=queries,
        k=args.k,
        golden=golden,
        verbose=verbose,
    )

    # Output
    if golden:
        print_comparison_leaderboard(run_a, run_b)
    if not args.no_side_by_side:
        print_side_by_side(run_a, run_b, k_display=args.k)

    # Verdict
    _print_verdict(run_a, run_b)

    # Save results
    output_path = args.output or str(
        _PROJECT_ROOT
        / "benchmark_results"
        / f"compare_{args.model_a}_vs_{args.model_b}_{time.strftime('%Y%m%d_%H%M%S')}.json"
    )
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    result = {
        "run_a": run_a,
        "run_b": run_b,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {output_path}")


def _print_verdict(run_a: dict[str, Any], run_b: dict[str, Any]) -> None:
    """Print Phase A gate verdict."""
    model_a = run_a["model_key"]
    model_b = run_b["model_key"]

    agg_a = run_a.get("aggregate", {})
    agg_b = run_b.get("aggregate", {})

    print(f"\n{'=' * 60}")
    print("PHASE A VERDICT")
    print(f"{'=' * 60}")

    if agg_a and agg_b:
        mrr_a = agg_a.get("mrr", 0.0)
        mrr_b = agg_b.get("mrr", 0.0)
        if mrr_a > mrr_b + 0.02:
            winner, loser = model_a, model_b
        elif mrr_b > mrr_a + 0.02:
            winner, loser = model_b, model_a
        else:
            print(f"  TIED  (MRR {model_a}={mrr_a:.3f}, {model_b}={mrr_b:.3f})")
            print("  → No clear winner. Keep current routing (qwen3 default).")
            return
        print(f"  WINNER: {winner}  (MRR {mrr_a:.3f} vs {mrr_b:.3f})")
        if winner == "bge_code":
            print("  → Proceed to Phase B: implement semantic anchor-based routing.")
        else:
            print(
                f"  → {loser} wins. Routing stays as-is (keyword threshold was intentional)."
            )
    else:
        print("  No golden dataset provided — inspect side-by-side output above.")
        print("  If bge_code retrieves more relevant code: proceed to Phase B.")
        print("  If results look equivalent: routing stays as-is.")
    print("=" * 60)


if __name__ == "__main__":
    main()
