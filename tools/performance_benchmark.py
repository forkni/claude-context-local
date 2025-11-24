#!/usr/bin/env python3
"""
Performance Benchmark Tool for claude-context-local

Measures search performance to track optimization progress.
Run before and after each optimization phase.

Usage:
    python tools/performance_benchmark.py [--runs N]
"""

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def benchmark_search(searcher, query: str, runs: int = 10) -> dict:
    """Benchmark a single search query."""
    times = []

    for _ in range(runs):
        start = time.perf_counter()
        results = searcher.search(query, k=5)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)  # Convert to ms

    return {
        "query": query,
        "runs": runs,
        "avg_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "std_ms": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
        "results_count": len(results) if results else 0,
    }


def benchmark_multi_hop(searcher, query: str, runs: int = 5) -> dict:
    """Benchmark multi-hop search."""
    times = []

    for _ in range(runs):
        start = time.perf_counter()
        results = searcher._multi_hop_search_internal(
            query=query, k=5, hops=2, expansion_factor=0.3
        )
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return {
        "query": query,
        "runs": runs,
        "avg_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "std_ms": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
        "results_count": len(results) if results else 0,
    }


def benchmark_bm25(bm25_index, query: str, runs: int = 20) -> dict:
    """Benchmark BM25 search specifically."""
    times = []

    for _ in range(runs):
        start = time.perf_counter()
        results = bm25_index.search(query, k=10)
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return {
        "query": query,
        "runs": runs,
        "avg_ms": round(statistics.mean(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "std_ms": round(statistics.stdev(times) if len(times) > 1 else 0, 2),
    }


def benchmark_config_loading(runs: int = 50) -> dict:
    """Benchmark config loading overhead."""
    from search.config import SearchConfigManager

    times = []

    for _ in range(runs):
        start = time.perf_counter()
        config_manager = SearchConfigManager()
        config = config_manager.load_config()
        elapsed = time.perf_counter() - start
        times.append(elapsed * 1000)

    return {
        "operation": "config_load",
        "runs": runs,
        "avg_ms": round(statistics.mean(times), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
        "total_ms": round(sum(times), 2),
    }


def benchmark_query_routing(runs: int = 50) -> dict:
    """Benchmark query routing overhead."""
    from search.query_router import QueryRouter

    queries = [
        "error handling exception",
        "configuration loading",
        "merkle tree implementation",
        "async await pattern",
        "database connection",
    ]

    times = []

    for _ in range(runs):
        for query in queries:
            start = time.perf_counter()
            router = QueryRouter()
            decision = router.route(query)
            elapsed = time.perf_counter() - start
            times.append(elapsed * 1000)

    return {
        "operation": "query_routing",
        "runs": runs * len(queries),
        "avg_ms": round(statistics.mean(times), 3),
        "min_ms": round(min(times), 3),
        "max_ms": round(max(times), 3),
    }


def run_full_benchmark(runs: int = 10) -> dict:
    """Run complete benchmark suite."""
    print("=" * 60)
    print("Performance Benchmark - claude-context-local")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Runs per test: {runs}")
    print()

    results = {
        "timestamp": datetime.now().isoformat(),
        "runs_per_test": runs,
        "benchmarks": {},
    }

    # Test queries covering different patterns
    test_queries = [
        "error handling exception try except",
        "search code implementation",
        "configuration loading workflow",
        "embedding model encode",
        "hybrid search parallel",
    ]

    # Benchmark config loading (no searcher needed)
    print("[1/5] Benchmarking config loading...")
    try:
        config_result = benchmark_config_loading(runs=50)
        results["benchmarks"]["config_loading"] = config_result
        print(f"  Config load: {config_result['avg_ms']:.3f}ms avg")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Benchmark query routing (no searcher needed)
    print("[2/5] Benchmarking query routing...")
    try:
        routing_result = benchmark_query_routing(runs=20)
        results["benchmarks"]["query_routing"] = routing_result
        print(f"  Query routing: {routing_result['avg_ms']:.3f}ms avg")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Try to initialize searcher for search benchmarks
    try:
        from mcp_server.server import get_storage_dir
        from search.hybrid_searcher import HybridSearcher

        storage_dir = get_storage_dir()
        projects_dir = storage_dir / "projects"
        project_dirs = (
            list(projects_dir.glob("*_1024d")) if projects_dir.exists() else []
        )

        if not project_dirs:
            project_dirs = (
                list(projects_dir.glob("*_768d")) if projects_dir.exists() else []
            )

        # Also check old format (direct storage)
        if not project_dirs:
            project_dirs = list(storage_dir.glob("*_1024d"))
        if not project_dirs:
            project_dirs = list(storage_dir.glob("*_768d"))

        if not project_dirs:
            print("\nNo indexed projects found. Skipping search benchmarks.")
            return results

        project_dir = project_dirs[0]
        index_dir = project_dir / "index"
        print(f"\nUsing index: {project_dir.name}")

        searcher = HybridSearcher(storage_dir=str(index_dir))

        if not searcher.is_ready:
            print("Searcher not ready. Skipping search benchmarks.")
            return results

        # Benchmark single-hop search
        print("[3/5] Benchmarking single-hop search...")
        single_hop_results = []
        for query in test_queries:
            result = benchmark_search(searcher, query, runs=runs)
            single_hop_results.append(result)
            print(f"  '{query[:30]}...': {result['avg_ms']:.1f}ms avg")

        results["benchmarks"]["single_hop_search"] = {
            "queries": single_hop_results,
            "overall_avg_ms": round(
                statistics.mean([r["avg_ms"] for r in single_hop_results]), 2
            ),
        }

        # Benchmark multi-hop search
        print("[4/5] Benchmarking multi-hop search...")
        multi_hop_results = []
        for query in test_queries[:3]:  # Fewer queries for slower multi-hop
            result = benchmark_multi_hop(searcher, query, runs=max(3, runs // 2))
            multi_hop_results.append(result)
            print(f"  '{query[:30]}...': {result['avg_ms']:.1f}ms avg")

        results["benchmarks"]["multi_hop_search"] = {
            "queries": multi_hop_results,
            "overall_avg_ms": round(
                statistics.mean([r["avg_ms"] for r in multi_hop_results]), 2
            ),
        }

        # Benchmark BM25 specifically
        print("[5/5] Benchmarking BM25 search...")
        bm25_results = []
        for query in test_queries:
            result = benchmark_bm25(searcher.bm25_index, query, runs=runs * 2)
            bm25_results.append(result)
            print(f"  '{query[:30]}...': {result['avg_ms']:.2f}ms avg")

        results["benchmarks"]["bm25_search"] = {
            "queries": bm25_results,
            "overall_avg_ms": round(
                statistics.mean([r["avg_ms"] for r in bm25_results]), 2
            ),
        }

        # Cleanup
        searcher.shutdown()

    except Exception as e:
        print(f"Search benchmark error: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if "single_hop_search" in results["benchmarks"]:
        print(
            f"Single-hop search avg: {results['benchmarks']['single_hop_search']['overall_avg_ms']:.1f}ms"
        )
    if "multi_hop_search" in results["benchmarks"]:
        print(
            f"Multi-hop search avg:  {results['benchmarks']['multi_hop_search']['overall_avg_ms']:.1f}ms"
        )
    if "bm25_search" in results["benchmarks"]:
        print(
            f"BM25 search avg:       {results['benchmarks']['bm25_search']['overall_avg_ms']:.2f}ms"
        )
    if "config_loading" in results["benchmarks"]:
        print(
            f"Config loading avg:    {results['benchmarks']['config_loading']['avg_ms']:.3f}ms"
        )
    if "query_routing" in results["benchmarks"]:
        print(
            f"Query routing avg:     {results['benchmarks']['query_routing']['avg_ms']:.3f}ms"
        )

    return results


def save_results(results: dict, filename: str = None):
    """Save benchmark results to JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"

    output_dir = Path(__file__).parent.parent / "benchmark_results"
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / filename
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Performance Benchmark Tool")
    parser.add_argument("--runs", type=int, default=10, help="Runs per test")
    parser.add_argument("--save", action="store_true", help="Save results to JSON")
    parser.add_argument("--output", type=str, help="Output filename")
    args = parser.parse_args()

    results = run_full_benchmark(runs=args.runs)

    if args.save:
        save_results(results, args.output)


if __name__ == "__main__":
    main()
