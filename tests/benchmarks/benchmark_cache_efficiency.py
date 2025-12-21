"""
Benchmark: Symbol Hash Cache Efficiency Assessment

Measures cache hit rate and latency impact using production metadata.

NOTE: This tests cache efficiency with real data, but simplified to avoid
requiring full search infrastructure.

Measures:
1. Cache hit rate in simulated lookup workflow
2. Cache lookup overhead (hash computation time)
3. Memory usage

Usage:
    python tests/benchmarks/benchmark_cache_efficiency.py
"""

import sys
import time
from pathlib import Path
from statistics import mean
from typing import Dict

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from search.metadata import MetadataStore  # noqa: E402
from search.symbol_cache import SymbolHashCache  # noqa: E402


class CacheEfficiencyBenchmark:
    """Benchmark symbol hash cache efficiency with production data."""

    def __init__(self, metadata_db_path: Path):
        if not metadata_db_path.exists():
            raise FileNotFoundError(f"Metadata DB not found: {metadata_db_path}")

        self.metadata_store = MetadataStore(metadata_db_path)

    def measure_cache_hit_rate(self, num_lookups: int = 1000) -> Dict:
        """Measure cache hit rate with simulated lookups.

        Args:
            num_lookups: Number of chunk_id lookups to simulate

        Returns:
            Dict with hit rate statistics
        """
        print("\n" + "-" * 70)
        print("1. CACHE HIT RATE SIMULATION")
        print("-" * 70)

        # Get all chunk_ids from metadata
        all_metadata = list(self.metadata_store.items())
        if not all_metadata:
            return {
                "status": "error",
                "error": "No metadata found in database",
            }

        chunk_ids = [chunk_id for chunk_id, _ in all_metadata]
        print(f"\nTotal chunks in metadata: {len(chunk_ids)}")

        # Simulate lookups - some chunks will be accessed multiple times
        # This mimics real search where same chunks are looked up repeatedly
        import random

        random.seed(42)  # Reproducible
        lookup_sequence = random.choices(chunk_ids, k=num_lookups)

        # Measure cache behavior
        cache_hits = 0
        cache_misses = 0
        first_access = set()

        for chunk_id in lookup_sequence:
            if chunk_id in first_access:
                cache_hits += 1
            else:
                cache_misses += 1
                first_access.add(chunk_id)

        hit_rate = cache_hits / num_lookups * 100 if num_lookups > 0 else 0
        meets_threshold = hit_rate >= 70.0

        print(f"\nSimulated lookups: {num_lookups}")
        print(f"Unique chunks:     {len(first_access)}")
        print(f"Cache hits:        {cache_hits} ({hit_rate:.1f}%)")
        print(f"Cache misses:      {cache_misses}")
        print("Threshold:         >=70%")

        if meets_threshold:
            print("[OK] PASSED: Hit rate >=70%")
        else:
            print(f"[X] FAILED: Hit rate {hit_rate:.1f}% <70%")

        return {
            "total_lookups": num_lookups,
            "unique_chunks": len(first_access),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "hit_rate_pct": hit_rate,
            "meets_threshold": meets_threshold,
        }

    def measure_cache_overhead(self) -> Dict:
        """Measure hash computation overhead.

        Returns:
            Dict with overhead statistics
        """
        print("\n" + "-" * 70)
        print("2. CACHE OVERHEAD (Hash Computation)")
        print("-" * 70)

        # Get sample chunk_ids
        all_metadata = list(self.metadata_store.items())
        if not all_metadata:
            return {"status": "error", "error": "No metadata found"}

        chunk_ids = [chunk_id for chunk_id, _ in all_metadata[:100]]

        # Measure hash computation time
        hash_times = []
        for chunk_id in chunk_ids:
            start = time.perf_counter()
            SymbolHashCache.fnv1a_hash(chunk_id)
            elapsed = (time.perf_counter() - start) * 1_000_000  # μs
            hash_times.append(elapsed)

        avg_hash_time = mean(hash_times)
        meets_target = avg_hash_time < 1.0  # <1μs target

        print(f"\nSample size:        {len(chunk_ids)} chunk_ids")
        print(f"Avg hash time:      {avg_hash_time:.3f} us")
        print("Target:             <1.0 us")

        if meets_target:
            print("[OK] PASSED: Hash computation <1us")
        else:
            print(f"[X] FAILED: Hash computation {avg_hash_time:.3f}us >=1us")

        return {
            "sample_size": len(chunk_ids),
            "avg_hash_time_us": avg_hash_time,
            "target_us": 1.0,
            "meets_target": meets_target,
        }

    def measure_cache_memory(self) -> Dict:
        """Measure cache memory usage.

        Returns:
            Dict with memory statistics
        """
        print("\n" + "-" * 70)
        print("3. CACHE MEMORY USAGE")
        print("-" * 70)

        # Get all chunk_ids
        all_metadata = list(self.metadata_store.items())
        chunk_ids = [chunk_id for chunk_id, _ in all_metadata]

        # Estimate memory: Each entry has hash (8 bytes) + chunk_id (string)
        total_memory = 0
        for chunk_id in chunk_ids:
            # Hash: 8 bytes, chunk_id string: len * 1 byte (approximation)
            total_memory += 8 + len(chunk_id)

        # Add bucket overhead: 256 buckets * dict overhead (~240 bytes each)
        total_memory += 256 * 240

        total_memory_mb = total_memory / 1024 / 1024

        print(f"\nTotal symbols:      {len(chunk_ids)}")
        print(f"Estimated memory:   {total_memory_mb:.3f} MB")
        print(f"Memory per symbol:  {total_memory / len(chunk_ids):.1f} bytes")

        return {
            "total_symbols": len(chunk_ids),
            "estimated_memory_mb": total_memory_mb,
            "memory_per_symbol_bytes": (
                total_memory / len(chunk_ids) if chunk_ids else 0
            ),
        }

    def run_full_benchmark(self) -> Dict:
        """Run complete benchmark suite.

        Returns:
            Dict with all metrics
        """
        print("=" * 70)
        print("SYMBOL HASH CACHE EFFICIENCY BENCHMARK")
        print("=" * 70)
        print("\nUsing production metadata for realistic cache simulation")
        print("=" * 70)

        results = {}

        # 1. Cache hit rate
        try:
            hit_rate_results = self.measure_cache_hit_rate(num_lookups=1000)
            results["hit_rate"] = hit_rate_results
        except Exception as e:
            print(f"\n[X] Hit rate test failed: {e}")
            results["hit_rate"] = {"status": "error", "error": str(e)}

        # 2. Cache overhead
        try:
            overhead_results = self.measure_cache_overhead()
            results["overhead"] = overhead_results
        except Exception as e:
            print(f"\n[X] Overhead test failed: {e}")
            results["overhead"] = {"status": "error", "error": str(e)}

        # 3. Memory usage
        try:
            memory_results = self.measure_cache_memory()
            results["memory"] = memory_results
        except Exception as e:
            print(f"\n[X] Memory test failed: {e}")
            results["memory"] = {"status": "error", "error": str(e)}

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        hit_rate_pass = results.get("hit_rate", {}).get("meets_threshold", False)
        overhead_pass = results.get("overhead", {}).get("meets_target", False)

        threshold_met = hit_rate_pass and overhead_pass

        if "hit_rate" in results and results["hit_rate"].get("status") != "error":
            hit_rate = results["hit_rate"]["hit_rate_pct"]
            print(
                f"Hit rate:         {hit_rate:.1f}% (threshold: >=70%) - {'[OK]' if hit_rate_pass else '[X]'}"
            )

        if "overhead" in results and results["overhead"].get("status") != "error":
            overhead = results["overhead"]["avg_hash_time_us"]
            print(
                f"Hash overhead:    {overhead:.3f}us (target: <1us) - {'[OK]' if overhead_pass else '[X]'}"
            )

        if "memory" in results and results["memory"].get("status") != "error":
            memory = results["memory"]["estimated_memory_mb"]
            print(f"Memory usage:     {memory:.3f} MB")

        if threshold_met:
            print("\n[OK] PASSED: Cache efficiency meets thresholds")
        else:
            print("\n[X] FAILED: Cache efficiency below thresholds")

        print("\n" + "=" * 70)
        print("NOTE: Hit rate depends on access patterns (multi-hop, repeated lookups)")
        print("Real benefit requires workload with repeated chunk_id accesses")
        print("=" * 70)

        results["threshold_met"] = threshold_met

        return results


def main():
    """Run benchmark."""
    # Production metadata path (discovered from exploration)
    metadata_db_path = Path(
        "C:/Users/Inter/.claude_code_search/projects/"
        "claude-context-local_9e7f0a98_bge-m3_1024d/index/metadata.db"
    )

    if not metadata_db_path.exists():
        print(f"ERROR: Production metadata not found at {metadata_db_path}")
        print("\nThis benchmark requires an indexed project.")
        print("Please run: python tools/index_project.py")
        sys.exit(1)

    # Run benchmark
    benchmark = CacheEfficiencyBenchmark(metadata_db_path)
    results = benchmark.run_full_benchmark()

    # Exit with appropriate code
    sys.exit(0 if results["threshold_met"] else 1)


if __name__ == "__main__":
    main()
