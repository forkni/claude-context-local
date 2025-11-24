#!/usr/bin/env python3
"""
Simple timing test for specific optimizations.
Minimal overhead, focused measurements.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_config_loading_overhead():
    """Measure config loading overhead."""
    from search.config import SearchConfigManager

    print("=" * 60)
    print("Config Loading Test")
    print("=" * 60)

    # Cold load (first time)
    start = time.perf_counter()
    config_manager = SearchConfigManager()
    config1 = config_manager.load_config()
    cold_time = (time.perf_counter() - start) * 1000

    # Warm loads (repeated)
    times = []
    for _ in range(100):
        start = time.perf_counter()
        config_manager = SearchConfigManager()
        config = config_manager.load_config()
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    avg_time = sum(times) / len(times)

    print(f"Cold load:  {cold_time:.3f}ms")
    print(f"Warm load:  {avg_time:.3f}ms (avg of 100 runs)")
    print(f"Total time: {sum(times):.1f}ms for 100 loads")
    print()

    return {"cold_ms": cold_time, "warm_avg_ms": avg_time, "total_ms": sum(times)}


def test_query_router_overhead():
    """Measure query routing overhead."""
    from search.query_router import QueryRouter

    print("=" * 60)
    print("Query Router Test")
    print("=" * 60)

    queries = [
        "error handling exception",
        "configuration loading",
        "merkle tree implementation",
    ]

    # Without reuse (create new instance per query)
    start = time.perf_counter()
    for _ in range(50):
        for query in queries:
            router = QueryRouter()
            decision = router.route(query)
    no_reuse_time = (time.perf_counter() - start) * 1000

    # With reuse (singleton pattern)
    router = QueryRouter()
    start = time.perf_counter()
    for _ in range(50):
        for query in queries:
            decision = router.route(query)
    reuse_time = (time.perf_counter() - start) * 1000

    print(
        f"No reuse (150 queries):  {no_reuse_time:.1f}ms ({no_reuse_time/150:.3f}ms per query)"
    )
    print(
        f"With reuse (150 queries): {reuse_time:.1f}ms ({reuse_time/150:.3f}ms per query)"
    )
    print(
        f"Savings: {no_reuse_time - reuse_time:.1f}ms ({(1 - reuse_time/no_reuse_time)*100:.1f}% faster)"
    )
    print()

    return {"no_reuse_ms": no_reuse_time, "reuse_ms": reuse_time}


def test_threadpool_creation():
    """Measure ThreadPoolExecutor creation overhead."""
    from concurrent.futures import ThreadPoolExecutor

    print("=" * 60)
    print("ThreadPool Creation Test")
    print("=" * 60)

    def dummy_task():
        return 42

    # Create new pool per task (BAD)
    start = time.perf_counter()
    for _ in range(50):
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(dummy_task)
            future2 = executor.submit(dummy_task)
            _ = future1.result()
            _ = future2.result()
    new_pool_time = (time.perf_counter() - start) * 1000

    # Reuse pool (GOOD)
    pool = ThreadPoolExecutor(max_workers=2)
    start = time.perf_counter()
    for _ in range(50):
        future1 = pool.submit(dummy_task)
        future2 = pool.submit(dummy_task)
        _ = future1.result()
        _ = future2.result()
    reuse_pool_time = (time.perf_counter() - start) * 1000
    pool.shutdown(wait=True)

    print(
        f"New pool per task (50 tasks):  {new_pool_time:.1f}ms ({new_pool_time/50:.2f}ms per task)"
    )
    print(
        f"Reuse pool (50 tasks):          {reuse_pool_time:.1f}ms ({reuse_pool_time/50:.2f}ms per task)"
    )
    print(
        f"Savings: {new_pool_time - reuse_pool_time:.1f}ms ({(1 - reuse_pool_time/new_pool_time)*100:.1f}% faster)"
    )
    print()

    return {"new_pool_ms": new_pool_time, "reuse_pool_ms": reuse_pool_time}


if __name__ == "__main__":
    print("\n")
    print("+" + "=" * 58 + "+")
    print("|" + " " * 10 + "SIMPLE TIMING TEST" + " " * 30 + "|")
    print("+" + "=" * 58 + "+")
    print()

    config_results = test_config_loading_overhead()
    router_results = test_query_router_overhead()
    threadpool_results = test_threadpool_creation()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Config loading overhead:   {config_results['warm_avg_ms']:.3f}ms per load")
    print(
        f"Query routing savings:     {router_results['no_reuse_ms'] - router_results['reuse_ms']:.1f}ms for 150 queries"
    )
    print(
        f"ThreadPool reuse savings:  {threadpool_results['new_pool_ms'] - threadpool_results['reuse_pool_ms']:.1f}ms for 50 tasks"
    )
    print("=" * 60)
