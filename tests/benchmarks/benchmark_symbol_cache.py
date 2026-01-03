"""Benchmark script for Symbol Hash Cache performance.

Compares O(1) hash lookup vs O(n) variant checking performance.
"""

import tempfile
import time
from pathlib import Path

from search.metadata import MetadataStore


def benchmark_lookup_performance():
    """Benchmark hash cache vs variant checking for chunk lookups."""
    # Setup
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "metadata.db"
    store = MetadataStore(db_path)

    # Create test data: 1000 chunks
    chunk_ids = []
    for i in range(1000):
        chunk_id = f"search/module_{i % 10}.py:{i*10}-{i*10+10}:function:func_{i}"
        chunk_ids.append(chunk_id)
        metadata = {
            "relative_path": f"search/module_{i % 10}.py",
            "chunk_type": "function",
        }
        store.set(chunk_id, i, metadata)

    store.commit()

    print("\n=== Symbol Hash Cache Performance Benchmark ===\n")
    print(f"Test dataset: {len(chunk_ids)} chunks")

    # Benchmark 1: Hash cache lookup (O(1))
    print("\n1. Hash Cache Lookup (O(1)):")
    iterations = 1000
    start = time.perf_counter()

    for _ in range(iterations):
        for chunk_id in chunk_ids[:100]:  # Test with 100 chunks
            result = store.get(chunk_id)
            assert result is not None

    end = time.perf_counter()
    avg_time_us = ((end - start) / (iterations * 100)) * 1_000_000

    print(f"   Average time: {avg_time_us:.2f} us per lookup")
    print(f"   Total time for {iterations * 100:,} lookups: {(end - start):.3f}s")

    # Benchmark 2: Variant checking (without hash cache - worst case)
    print("\n2. Variant Checking (O(n) - worst case):")
    print("   Simulating 6 variant checks per lookup...")

    # Clear hash cache to force variant checking
    store._symbol_cache.clear()

    # For fair comparison, test variant checking on first lookup (cold cache)
    test_chunks = chunk_ids[:100]
    start = time.perf_counter()

    for chunk_id in test_chunks:
        # First lookup will do variant checking
        result = store.get(chunk_id)
        assert result is not None

    end = time.perf_counter()
    avg_time_us_variant = ((end - start) / len(test_chunks)) * 1_000_000

    print(f"   Average time: {avg_time_us_variant:.2f} us per lookup")
    print(f"   Total time for {len(test_chunks)} lookups: {(end - start):.3f}s")

    # Calculate speedup
    speedup = avg_time_us_variant / avg_time_us

    print("\n=== Results ===")
    print(f"   Hash Cache: {avg_time_us:.2f} us")
    print(f"   Variant Check: {avg_time_us_variant:.2f} us")
    print(f"   Speedup: {speedup:.1f}x faster")
    print(
        "   Performance target: <100 us" + (" OK" if avg_time_us < 100 else " FAILED")
    )

    # Hash cache statistics
    stats = store._symbol_cache.get_stats()
    print("\n=== Hash Cache Stats ===")
    print(f"   Total symbols: {stats['total_symbols']}")
    print(f"   Buckets used: {stats['used_buckets']}/{stats['bucket_count']}")
    print(f"   Load factor: {stats['load_factor']:.1f}%")
    print(f"   Avg bucket size: {stats['avg_bucket_size']:.2f}")
    print(f"   Max bucket size: {stats['max_bucket_size']}")
    print(f"   Memory estimate: {stats['memory_estimate_mb']:.3f} MB")

    store.close()

    return {
        "hash_cache_us": avg_time_us,
        "variant_check_us": avg_time_us_variant,
        "speedup": speedup,
        "stats": stats,
    }


if __name__ == "__main__":
    results = benchmark_lookup_performance()

    # Verify performance targets
    assert results["hash_cache_us"] < 100, "Hash cache lookup should be <100 μs"
    assert results["speedup"] > 1.0, "Hash cache should be faster than variant checking"

    print("\n✓ All performance targets met!")
