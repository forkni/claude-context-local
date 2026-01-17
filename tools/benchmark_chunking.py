"""Benchmark chunking strategies for code retrieval quality.

This script evaluates how different chunking configurations affect search quality
by measuring Recall@k, Precision@k, and MRR metrics against ground truth queries.

Usage:
    # Run baseline benchmark
    python tools/benchmark_chunking.py --config baseline --output results/baseline_B1.json

    # Compare two results
    python tools/benchmark_chunking.py --compare results/baseline_B1.json results/character_A1.json

Requirements:
    - MCP server must be running with index loaded
    - Ground truth queries file at tools/chunking_ground_truth.json
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class ChunkStats:
    """Statistics for a chunking configuration."""

    total_chunks: int
    total_tokens: int
    min_tokens: int
    max_tokens: int
    avg_tokens: float
    median_tokens: float
    std_tokens: float
    oversized_chunks: int  # > max_merged_tokens
    undersized_chunks: int  # < min_chunk_tokens
    oversized_ratio: float
    undersized_ratio: float


@dataclass
class RetrievalMetrics:
    """Retrieval quality metrics."""

    recall_at_1: float
    recall_at_5: float
    recall_at_10: float
    precision_at_1: float
    precision_at_5: float
    precision_at_10: float
    mrr: float  # Mean Reciprocal Rank
    avg_latency_ms: float
    total_queries: int


def calculate_recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Calculate Recall@k = |retrieved[:k] ∩ relevant| / |relevant|.

    Args:
        retrieved: List of retrieved chunk_ids (in rank order)
        relevant: List of expected chunk_ids (ground truth)
        k: Number of top results to consider

    Returns:
        Recall@k score (0.0 to 1.0)
    """
    if not relevant:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(relevant_set)


def calculate_precision_at_k(
    retrieved: List[str], relevant: List[str], k: int
) -> float:
    """Calculate Precision@k = |retrieved[:k] ∩ relevant| / k.

    Args:
        retrieved: List of retrieved chunk_ids (in rank order)
        relevant: List of expected chunk_ids (ground truth)
        k: Number of top results to consider

    Returns:
        Precision@k score (0.0 to 1.0)
    """
    if k == 0:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / k


def calculate_mrr(retrieved: List[str], relevant: List[str]) -> float:
    """Calculate Mean Reciprocal Rank = 1 / rank_of_first_relevant.

    Args:
        retrieved: List of retrieved chunk_ids (in rank order)
        relevant: List of expected chunk_ids (ground truth)

    Returns:
        MRR score (0.0 to 1.0)
    """
    relevant_set = set(relevant)
    for i, chunk_id in enumerate(retrieved, 1):
        if chunk_id in relevant_set:
            return 1.0 / i
    return 0.0


def load_ground_truth(path: str = "tools/chunking_ground_truth.json") -> Dict:
    """Load ground truth queries from JSON file.

    Args:
        path: Path to ground truth JSON file

    Returns:
        Dictionary with queries and metadata
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def search_with_mcp(query: str, k: int = 10) -> List[Dict]:
    """Search using MCP code-search tool (must be running in MCP context).

    Args:
        query: Search query string
        k: Number of results to return

    Returns:
        List of search results with chunk_id and score

    Note:
        This function is designed to be called from within Claude Code
        where MCP tools are available. For standalone testing, you need
        to have the MCP server running and index loaded.
    """
    try:
        # Import the MCP tool function directly
        # This requires the MCP server to be running
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))

        # Use the actual MCP search tool
        # This will only work if called from Claude Code context
        from mcp_server.tools import code_search_tool

        # Create a mock request object
        class MockRequest:
            def __init__(self, params):
                self.params = params

        # Call the tool
        request = MockRequest(
            {
                "query": query,
                "k": k,
                "search_mode": "hybrid",
                "include_context": False,
            }
        )

        result = code_search_tool.search_code(request)

        # Extract results
        if isinstance(result, dict) and "results" in result:
            return result["results"]

        return []

    except Exception as e:
        print(f"Search error: {e}")
        print(
            "NOTE: This benchmark requires MCP server to be running with index loaded."
        )
        print(
            "      Please run this script from within Claude Code context, not standalone."
        )
        return []


def run_benchmark(
    config_name: str,
    ground_truth_path: str = "tools/chunking_ground_truth.json",
    output_path: Optional[str] = None,
) -> Dict:
    """Run benchmark with current chunking configuration.

    Args:
        config_name: Name of this configuration (for reporting)
        ground_truth_path: Path to ground truth queries
        output_path: Optional path to save results JSON

    Returns:
        Dictionary with per-query and aggregate metrics
    """
    print(f"=== Running Benchmark: {config_name} ===\n")

    # Load ground truth
    ground_truth = load_ground_truth(ground_truth_path)
    queries = ground_truth["queries"]

    print(f"Loaded {len(queries)} ground truth queries")
    print(f"Categories: {', '.join(ground_truth.get('categories', []))}\n")

    # Initialize results
    results = {
        "config_name": config_name,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "queries": [],
        "aggregate": {},
    }

    # Accumulators for aggregate metrics
    all_recalls_1, all_recalls_5, all_recalls_10 = [], [], []
    all_precisions_1, all_precisions_5, all_precisions_10 = [], [], []
    all_mrrs, all_latencies = [], []

    # Run each query
    for i, query_data in enumerate(queries, 1):
        query = query_data["query"]
        expected = query_data["expected_chunk_ids"]
        category = query_data.get("category", "unknown")

        print(f"[{i}/{len(queries)}] {category:20s} | {query[:50]}")

        # Run search with timing
        start = time.perf_counter()
        try:
            search_results = search_with_mcp(query, k=10)
            latency = (time.perf_counter() - start) * 1000

            # Extract chunk_ids
            retrieved_ids = [r.get("chunk_id", "") for r in search_results]

            # Calculate metrics
            r1 = calculate_recall_at_k(retrieved_ids, expected, 1)
            r5 = calculate_recall_at_k(retrieved_ids, expected, 5)
            r10 = calculate_recall_at_k(retrieved_ids, expected, 10)
            p1 = calculate_precision_at_k(retrieved_ids, expected, 1)
            p5 = calculate_precision_at_k(retrieved_ids, expected, 5)
            p10 = calculate_precision_at_k(retrieved_ids, expected, 10)
            mrr = calculate_mrr(retrieved_ids, expected)

            all_recalls_1.append(r1)
            all_recalls_5.append(r5)
            all_recalls_10.append(r10)
            all_precisions_1.append(p1)
            all_precisions_5.append(p5)
            all_precisions_10.append(p10)
            all_mrrs.append(mrr)
            all_latencies.append(latency)

            # Store per-query result
            results["queries"].append(
                {
                    "query": query,
                    "category": category,
                    "recall@1": round(r1, 4),
                    "recall@5": round(r5, 4),
                    "recall@10": round(r10, 4),
                    "precision@1": round(p1, 4),
                    "precision@5": round(p5, 4),
                    "precision@10": round(p10, 4),
                    "mrr": round(mrr, 4),
                    "latency_ms": round(latency, 2),
                    "retrieved_top5": retrieved_ids[:5],
                    "expected": expected,
                    "found_in_top5": r5 == 1.0,
                }
            )

            # Print quick feedback
            if r5 == 1.0:
                print(f"          [OK] Found (R@5={r5:.2f}, MRR={mrr:.3f})")
            else:
                print(f"          [MISS]     (R@5={r5:.2f}, MRR={mrr:.3f})")

        except Exception as e:
            print(f"          ERROR: {e}")
            # Add failed query with zero metrics
            results["queries"].append(
                {
                    "query": query,
                    "category": category,
                    "error": str(e),
                    "recall@1": 0.0,
                    "recall@5": 0.0,
                    "recall@10": 0.0,
                    "precision@1": 0.0,
                    "precision@5": 0.0,
                    "precision@10": 0.0,
                    "mrr": 0.0,
                    "latency_ms": 0.0,
                }
            )
            all_recalls_1.append(0.0)
            all_recalls_5.append(0.0)
            all_recalls_10.append(0.0)
            all_precisions_1.append(0.0)
            all_precisions_5.append(0.0)
            all_precisions_10.append(0.0)
            all_mrrs.append(0.0)
            all_latencies.append(0.0)

    # Calculate aggregate metrics
    results["aggregate"] = {
        "recall@1": round(mean(all_recalls_1), 4),
        "recall@5": round(mean(all_recalls_5), 4),
        "recall@10": round(mean(all_recalls_10), 4),
        "precision@1": round(mean(all_precisions_1), 4),
        "precision@5": round(mean(all_precisions_5), 4),
        "precision@10": round(mean(all_precisions_10), 4),
        "mrr": round(mean(all_mrrs), 4),
        "avg_latency_ms": round(mean(all_latencies), 2),
        "total_queries": len(queries),
        "successful_at_5": sum(1 for r in all_recalls_5 if r == 1.0),
        "success_rate_at_5": round(
            sum(1 for r in all_recalls_5 if r == 1.0) / len(all_recalls_5), 4
        ),
    }

    # Print summary
    print("\n=== Aggregate Metrics ===")
    print(f"Recall@1:     {results['aggregate']['recall@1']:.4f}")
    print(f"Recall@5:     {results['aggregate']['recall@5']:.4f}")
    print(f"Recall@10:    {results['aggregate']['recall@10']:.4f}")
    print(f"Precision@5:  {results['aggregate']['precision@5']:.4f}")
    print(f"MRR:          {results['aggregate']['mrr']:.4f}")
    print(f"Avg Latency:  {results['aggregate']['avg_latency_ms']:.2f} ms")
    print(
        f"Success@5:    {results['aggregate']['successful_at_5']}/{results['aggregate']['total_queries']} ({results['aggregate']['success_rate_at_5']:.1%})"
    )

    # Save results if output path provided
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_path}")

    return results


def compare_results(baseline_path: str, comparison_path: str) -> None:
    """Compare two benchmark results and print analysis.

    Args:
        baseline_path: Path to baseline results JSON
        comparison_path: Path to comparison results JSON
    """
    # Load results
    with open(baseline_path, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(comparison_path, "r", encoding="utf-8") as f:
        comparison = json.load(f)

    print(f"\n{'='*70}")
    print(f"{'Chunking Strategy Comparison':^70}")
    print(f"{'='*70}\n")

    print("Configuration:")
    print(f"  Baseline:    {baseline['config_name']}")
    print(f"  Comparison:  {comparison['config_name']}")
    print(f"  Timestamp:   {baseline['timestamp']} vs {comparison['timestamp']}")

    # Extract aggregates
    base_agg = baseline["aggregate"]
    comp_agg = comparison["aggregate"]

    print(f"\n{'Retrieval Quality':-^70}")
    print(
        f"{'Metric':<20} {'Baseline':>12} {'Comparison':>12} {'Delta':>12} {'Change':>10}"
    )
    print(f"{'-'*70}")

    def print_metric(name: str, key: str):
        base_val = base_agg[key]
        comp_val = comp_agg[key]
        delta = comp_val - base_val
        change_pct = (delta / base_val * 100) if base_val > 0 else 0
        change_str = f"{change_pct:+.1f}%"
        delta_str = f"{delta:+.4f}"

        # Indicator
        if delta > 0:
            indicator = "UP"
        elif delta < 0:
            indicator = "DOWN"
        else:
            indicator = "="

        print(
            f"{name:<20} {base_val:>12.4f} {comp_val:>12.4f} {delta_str:>12} {change_str:>9} {indicator}"
        )

    print_metric("Recall@1", "recall@1")
    print_metric("Recall@5", "recall@5")
    print_metric("Recall@10", "recall@10")
    print_metric("Precision@5", "precision@5")
    print_metric("MRR", "mrr")

    print(f"\n{'Performance':-^70}")
    avg_lat_base = base_agg["avg_latency_ms"]
    avg_lat_comp = comp_agg["avg_latency_ms"]
    lat_delta = avg_lat_comp - avg_lat_base
    lat_change = (lat_delta / avg_lat_base * 100) if avg_lat_base > 0 else 0
    print(
        f"{'Avg Latency (ms)':<20} {avg_lat_base:>12.2f} {avg_lat_comp:>12.2f} {lat_delta:>+12.2f} {lat_change:>+9.1f}%"
    )

    # Success rate
    print(f"\n{'Success Metrics':-^70}")
    base_success = base_agg["successful_at_5"]
    comp_success = comp_agg["successful_at_5"]
    total = base_agg["total_queries"]
    print(
        f"{'Found in Top-5':<20} {base_success:>12}/{total} {comp_success:>12}/{total} {comp_success - base_success:>+12}"
    )

    # Decision
    print(f"\n{'Decision Analysis':-^70}")
    recall5_improvement = comp_agg["recall@5"] - base_agg["recall@5"]
    recall5_pct = recall5_improvement * 100

    print(f"Recall@5 Change: {recall5_pct:+.2f}%")

    if recall5_pct >= 3.0:
        print(f"[WIN] {comparison['config_name']}")
        print(f"  Reason: Recall@5 improved by {recall5_pct:.2f}% (>= +3% threshold)")
    elif recall5_pct <= -3.0:
        print(f"[WIN] {baseline['config_name']}  (Baseline)")
        print(f"  Reason: Comparison decreased Recall@5 by {-recall5_pct:.2f}%")
    else:
        print("[TIE] No significant difference")
        print(f"  Reason: Recall@5 change ({recall5_pct:+.2f}%) below ±3% threshold")

    print(f"{'='*70}\n")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark chunking strategies for code retrieval quality"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Configuration name (e.g., 'baseline', 'character_based')",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output path for results JSON (e.g., 'results/baseline.json')",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        default="tools/chunking_ground_truth.json",
        help="Path to ground truth queries JSON",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("BASELINE", "COMPARISON"),
        help="Compare two result files (baseline vs comparison)",
    )

    args = parser.parse_args()

    if args.compare:
        # Compare mode
        compare_results(args.compare[0], args.compare[1])
    elif args.config:
        # Benchmark mode
        run_benchmark(
            config_name=args.config,
            ground_truth_path=args.ground_truth,
            output_path=args.output,
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
