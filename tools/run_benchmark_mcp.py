"""Run benchmark using MCP search infrastructure directly.

This script properly imports the search functionality to evaluate retrieval quality.
"""

import json
import sys
import time
from pathlib import Path
from statistics import mean
from typing import List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.server import get_searcher


def calculate_recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    """Calculate Recall@k = |retrieved[:k] ∩ relevant| / |relevant|."""
    if not relevant:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(relevant_set)


def calculate_precision_at_k(
    retrieved: List[str], relevant: List[str], k: int
) -> float:
    """Calculate Precision@k = |retrieved[:k] ∩ relevant| / k."""
    if k == 0:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / k


def calculate_mrr(retrieved: List[str], relevant: List[str]) -> float:
    """Calculate Mean Reciprocal Rank."""
    for i, chunk_id in enumerate(retrieved, 1):
        if chunk_id in relevant:
            return 1.0 / i
    return 0.0


def run_benchmark(ground_truth_path: str, output_path: str, config_name: str):
    """Run benchmark queries and calculate metrics."""

    # Load ground truth
    with open(ground_truth_path, "r") as f:
        ground_truth = json.load(f)

    queries = ground_truth["queries"]
    print(f"Loaded {len(queries)} ground truth queries")

    # Get searcher from MCP server context
    try:
        searcher = get_searcher()
    except Exception as e:
        print(f"ERROR: Could not get searcher: {e}")
        print("Make sure an index is loaded in the MCP server context.")
        sys.exit(1)

    # Run queries
    results = []
    recall_1_scores = []
    recall_5_scores = []
    recall_10_scores = []
    mrr_scores = []
    latencies = []

    for i, item in enumerate(queries, 1):
        query = item["query"]
        expected = item["expected_chunk_ids"]
        category = item["category"]

        print(f"[{i}/{len(queries)}] {category:20s} | {query}")

        try:
            start_time = time.time()
            search_results = searcher.search(query, k=10)
            latency = (time.time() - start_time) * 1000

            retrieved_ids = [r.chunk_id for r in search_results]

            # Calculate metrics
            r1 = calculate_recall_at_k(retrieved_ids, expected, 1)
            r5 = calculate_recall_at_k(retrieved_ids, expected, 5)
            r10 = calculate_recall_at_k(retrieved_ids, expected, 10)
            mrr = calculate_mrr(retrieved_ids, expected)

            recall_1_scores.append(r1)
            recall_5_scores.append(r5)
            recall_10_scores.append(r10)
            mrr_scores.append(mrr)
            latencies.append(latency)

            # Store result
            results.append(
                {
                    "query": query,
                    "category": category,
                    "expected": expected,
                    "retrieved": retrieved_ids[:10],
                    "recall_at_1": r1,
                    "recall_at_5": r5,
                    "recall_at_10": r10,
                    "mrr": mrr,
                    "latency_ms": latency,
                    "hit": r5 > 0,
                }
            )

            status = "HIT" if r5 > 0 else "MISS"
            print(f"          [{status}]     (R@5={r5:.2f}, MRR={mrr:.3f})")

        except Exception as e:
            print(f"          [ERROR] {str(e)}")
            results.append(
                {
                    "query": query,
                    "category": category,
                    "expected": expected,
                    "error": str(e),
                    "hit": False,
                }
            )

    # Calculate aggregate metrics
    metrics = {
        "config_name": config_name,
        "recall_at_1": mean(recall_1_scores) if recall_1_scores else 0.0,
        "recall_at_5": mean(recall_5_scores) if recall_5_scores else 0.0,
        "recall_at_10": mean(recall_10_scores) if recall_10_scores else 0.0,
        "mrr": mean(mrr_scores) if mrr_scores else 0.0,
        "avg_latency_ms": mean(latencies) if latencies else 0.0,
        "total_queries": len(queries),
        "success_count": sum(1 for r in results if r.get("hit", False)),
    }

    print("\n=== Aggregate Metrics ===")
    print(f"Recall@1:     {metrics['recall_at_1']:.4f}")
    print(f"Recall@5:     {metrics['recall_at_5']:.4f}")
    print(f"Recall@10:    {metrics['recall_at_10']:.4f}")
    print(f"MRR:          {metrics['mrr']:.4f}")
    print(f"Avg Latency:  {metrics['avg_latency_ms']:.2f} ms")
    print(
        f"Success@5:    {metrics['success_count']}/{metrics['total_queries']} ({metrics['success_count']/metrics['total_queries']*100:.1f}%)"
    )

    # Save results
    output = {"config_name": config_name, "metrics": metrics, "results": results}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run benchmark using MCP infrastructure"
    )
    parser.add_argument("--config", default="option_a", help="Configuration name")
    parser.add_argument(
        "--output", default="results/option_a_results.json", help="Output path"
    )
    parser.add_argument(
        "--ground-truth",
        default="tools/chunking_ground_truth.json",
        help="Ground truth path",
    )

    args = parser.parse_args()

    run_benchmark(args.ground_truth, args.output, args.config)
