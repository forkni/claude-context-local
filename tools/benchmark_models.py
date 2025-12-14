#!/usr/bin/env python3
"""
Benchmark script to compare embedding model quality.

Runs 20 test queries and measures:
- Relevance Scores (similarity scores)
- Mean Reciprocal Rank (MRR@5)
- Query Latency (ms)

Usage:
    python tools/benchmark_models.py --output benchmark_8b.json
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server.tool_handlers import handle_search_code

# 20 Test Queries by Category
TEST_QUERIES = {
    "Error Handling": [
        "error handling exception try except",
        "validate input parameters",
        "raise exception when invalid",
    ],
    "Configuration": [
        "load configuration settings",
        "environment variable setup",
        "model registry initialization",
    ],
    "Search & Indexing": [
        "semantic search implementation",
        "BM25 sparse index",
        "hybrid search fusion RRF",
        "incremental index update",
    ],
    "Graph & Dependencies": [
        "call graph extraction",
        "find function callers",
        "dependency relationship",
    ],
    "Embeddings": [
        "embedding model loading",
        "batch embedding generation",
        "vector dimension handling",
    ],
    "MCP Server": [
        "MCP tool handler",
        "project switching logic",
    ],
    "Merkle/Change Detection": [
        "merkle tree snapshot",
        "file change detection",
    ],
}


def calculate_mrr(results: List[dict], k: int = 5) -> float:
    """Calculate Mean Reciprocal Rank@k.

    Assumes first result is most relevant (simplification for this benchmark).
    Real MRR would need ground truth labels.

    Args:
        results: List of search results
        k: Top-k results to consider

    Returns:
        MRR score (0-1)
    """
    if not results:
        return 0.0

    # For this benchmark, we consider the first result's position
    # Higher score = better placement
    first_score = results[0].get("score", 0.0)

    # If score is very high (>0.7), assume rank 1
    # This is a simplification - real MRR needs ground truth
    if first_score > 0.7:
        return 1.0
    elif first_score > 0.5:
        return 0.5
    else:
        return 1.0 / k  # Assume last position


async def run_query(query: str) -> Dict:
    """Run a single search query and collect metrics.

    Args:
        query: Search query string

    Returns:
        dict: Query results with metrics
    """
    start_time = time.time()

    try:
        result = await handle_search_code(
            {
                "query": query,
                "k": 5,
                "use_routing": True,  # Enable query routing
            }
        )

        latency_ms = (time.time() - start_time) * 1000

        if result.get("success") and result.get("results"):
            results = result["results"]

            # Extract top scores
            scores = [r.get("score", 0.0) for r in results[:5]]
            top_score = scores[0] if scores else 0.0
            avg_score = sum(scores) / len(scores) if scores else 0.0

            # Calculate MRR
            mrr = calculate_mrr(results, k=5)

            return {
                "query": query,
                "success": True,
                "top_score": top_score,
                "avg_score_top5": avg_score,
                "mrr_at_5": mrr,
                "latency_ms": latency_ms,
                "num_results": len(results),
                "model_routed": result.get("model", "unknown"),
            }
        else:
            return {
                "query": query,
                "success": False,
                "error": result.get("error", "Unknown error"),
                "latency_ms": latency_ms,
            }

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "latency_ms": latency_ms,
        }


async def run_benchmark() -> Dict:
    """Run all benchmark queries.

    Returns:
        dict: Benchmark results with aggregated metrics
    """
    # Set current project
    from mcp_server.services import get_state
    from mcp_server.storage_manager import set_current_project

    project_path = str(Path(__file__).parent.parent.resolve())
    set_current_project(project_path)

    # Verify setup
    state = get_state()
    print("=" * 70)
    print("BENCHMARK: Qwen3 Model Quality Comparison")
    print("=" * 70)
    print(f"Current project: {state.current_project}")
    print(f"Multi-model enabled: {state.multi_model_enabled}")
    print(f"Queries: {sum(len(v) for v in TEST_QUERIES.values())}")
    print("Features: Multi-Model Pool + Query Routing + Neural Reranker")
    print()

    all_results = []
    category_results = {}

    for category, queries in TEST_QUERIES.items():
        print(f"[{category}] Running {len(queries)} queries...")
        category_data = []

        for query in queries:
            result = await run_query(query)
            all_results.append(result)
            category_data.append(result)

            if result["success"]:
                print(
                    f"  [OK] {query[:50]:50s} | Score: {result['top_score']:.3f} | {result['latency_ms']:.0f}ms"
                )
            else:
                print(
                    f"  [X]  {query[:50]:50s} | ERROR: {result.get('error', 'Unknown')}"
                )

        category_results[category] = category_data

    # Calculate aggregate metrics
    successful = [r for r in all_results if r["success"]]

    if successful:
        avg_top_score = sum(r["top_score"] for r in successful) / len(successful)
        avg_score_top5 = sum(r["avg_score_top5"] for r in successful) / len(successful)
        avg_mrr = sum(r["mrr_at_5"] for r in successful) / len(successful)
        avg_latency = sum(r["latency_ms"] for r in successful) / len(successful)

        # Model routing distribution
        model_counts = {}
        for r in successful:
            model = r.get("model_routed", "unknown")
            model_counts[model] = model_counts.get(model, 0) + 1
    else:
        avg_top_score = 0
        avg_score_top5 = 0
        avg_mrr = 0
        avg_latency = 0
        model_counts = {}

    summary = {
        "total_queries": len(all_results),
        "successful_queries": len(successful),
        "failed_queries": len(all_results) - len(successful),
        "metrics": {
            "avg_top_score": avg_top_score,
            "avg_score_top5": avg_score_top5,
            "mrr_at_5": avg_mrr,
            "avg_latency_ms": avg_latency,
        },
        "model_routing": model_counts,
        "category_results": category_results,
        "all_results": all_results,
    }

    # Print summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Successful: {len(successful)}/{len(all_results)}")
    print(f"Avg Top Score:     {avg_top_score:.3f}")
    print(f"Avg Score (Top 5): {avg_score_top5:.3f}")
    print(f"MRR@5:             {avg_mrr:.3f}")
    print(f"Avg Latency:       {avg_latency:.0f} ms")
    print()
    print("Model Routing Distribution:")
    for model, count in sorted(model_counts.items()):
        print(f"  {model}: {count} queries ({count/len(successful)*100:.1f}%)")
    print("=" * 70)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Benchmark embedding model quality")
    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON file (e.g., benchmark_8b.json)",
    )

    args = parser.parse_args()

    # Run benchmark
    results = asyncio.run(run_benchmark())

    # Save to file
    output_path = Path(args.output)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print()
    print(f"Results saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
