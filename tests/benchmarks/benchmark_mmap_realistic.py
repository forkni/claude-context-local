"""
Benchmark: Mmap Vector Storage Realistic Performance Assessment

Measures:
1. Access time distribution (cold vs warm cache)
2. Comparison with FAISS reconstruct() at current scale (964 vectors)
3. Memory usage comparison

Usage:
    python tests/benchmarks/benchmark_mmap_realistic.py
"""

import random
import sys
import time
from pathlib import Path
from statistics import mean, median
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from search.faiss_index import FaissVectorIndex  # noqa: E402
from search.mmap_vectors import MmapVectorStorage  # noqa: E402


def percentile(data: List[float], p: float) -> float:
    """Calculate percentile of data.

    Args:
        data: Sorted list of values
        p: Percentile (0-100)

    Returns:
        Value at percentile p
    """
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (p / 100)
    f = int(k)
    c = int(k) + 1 if k != int(k) else int(k)

    if c >= len(sorted_data):
        return sorted_data[-1]
    if f == c:
        return sorted_data[f]

    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


class MmapRealisticBenchmark:
    """Benchmark mmap vector storage with realistic access patterns."""

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir

        # Find indexed project
        self.project_dirs = list(self.storage_dir.glob("projects/*/"))
        if not self.project_dirs:
            raise ValueError(f"No indexed projects found in {storage_dir}")

        self.project_dir = self.project_dirs[0]
        self.index_dir = self.project_dir / "index"

        print(f"Using project: {self.project_dir.name}")

        # Find FAISS index and mmap files
        faiss_files = list(self.index_dir.glob("*_vectors.index"))
        mmap_files = list(self.index_dir.glob("*_vectors.mmap"))

        if not faiss_files:
            raise ValueError(f"No FAISS index found in {self.index_dir}")

        self.faiss_path = faiss_files[0]
        self.mmap_path = mmap_files[0] if mmap_files else None

        # Determine dimension from filename (e.g., "1024d_vectors.index")
        filename = self.faiss_path.stem
        if "768d" in filename:
            self.dimension = 768
        elif "1024d" in filename:
            self.dimension = 1024
        else:
            self.dimension = 1024  # Default

        print(f"FAISS index: {self.faiss_path.name}")
        print(f"Mmap file:   {self.mmap_path.name if self.mmap_path else 'NOT FOUND'}")
        print(f"Dimension:   {self.dimension}d")

    def measure_access_time_distribution(self) -> Dict:
        """Measure realistic access times (cold and warm)."""
        print("\n" + "-" * 70)
        print("1. ACCESS TIME DISTRIBUTION (COLD vs WARM)")
        print("-" * 70)

        if not self.mmap_path or not self.mmap_path.exists():
            print("⚠️  Mmap file not found, skipping test")
            return {"status": "skipped", "reason": "mmap file not found"}

        # Load mmap storage
        storage = MmapVectorStorage(self.mmap_path, self.dimension)
        if not storage.load():
            print("⚠️  Failed to load mmap storage")
            return {"status": "failed", "reason": "failed to load"}

        vector_count = storage.count
        print(f"\nVector count: {vector_count}")

        # Cold access (first 10 vectors - may trigger page faults)
        print("\nCold access (first 10 vectors, potential page faults):")
        cold_times = []
        for i in range(min(10, vector_count)):
            start = time.perf_counter()
            _vector = storage.get_vector(i)
            elapsed = (time.perf_counter() - start) * 1_000_000  # μs
            cold_times.append(elapsed)

        if cold_times:
            print(f"  Mean:   {mean(cold_times):7.2f} μs")
            print(f"  Median: {median(cold_times):7.2f} μs")
            print(f"  P50:    {percentile(cold_times, 50):7.2f} μs")
            print(f"  P99:    {percentile(cold_times, 99):7.2f} μs")

        # Warm access (100 sequential accesses)
        print("\nWarm access (100 sequential accesses, cache warm):")
        warm_times = []
        for i in range(min(100, vector_count)):
            start = time.perf_counter()
            _vector = storage.get_vector(i)
            elapsed = (time.perf_counter() - start) * 1_000_000  # μs
            warm_times.append(elapsed)

        if warm_times:
            print(f"  Mean:   {mean(warm_times):7.2f} μs")
            print(f"  Median: {median(warm_times):7.2f} μs")
            print(f"  P50:    {percentile(warm_times, 50):7.2f} μs")
            print(f"  P99:    {percentile(warm_times, 99):7.2f} μs")

        # Check if <1μs claim is met
        warm_median = median(warm_times)
        meets_claim = warm_median < 1.0

        if meets_claim:
            print(f"\n✅ <1μs claim verified: {warm_median:.2f} μs median")
        else:
            print(f"\n❌ <1μs claim NOT met: {warm_median:.2f} μs median")

        storage.close()

        return {
            "status": "success",
            "vector_count": vector_count,
            "cold_mean_us": mean(cold_times),
            "cold_median_us": median(cold_times),
            "cold_p99_us": percentile(cold_times, 99),
            "warm_mean_us": mean(warm_times),
            "warm_median_us": median(warm_times),
            "warm_p99_us": percentile(warm_times, 99),
            "meets_1us_claim": meets_claim,
        }

    def measure_mmap_vs_faiss_at_current_scale(self) -> Dict:
        """Compare mmap vs FAISS at 964 vectors (current scale)."""
        print("\n" + "-" * 70)
        print("2. MMAP vs FAISS AT CURRENT SCALE")
        print("-" * 70)

        # Load FAISS index
        faiss_index = FaissVectorIndex(self.faiss_path)
        if not faiss_index.load():
            print("⚠️  Failed to load FAISS index")
            return {"status": "failed", "reason": "failed to load FAISS"}

        vector_count = faiss_index._index.ntotal
        print(f"\nVector count: {vector_count}")

        # Random access pattern (realistic for search)
        num_trials = 100
        indices = [random.randint(0, vector_count - 1) for _ in range(num_trials)]

        print(f"\nTesting {num_trials} random accesses...")

        # FAISS reconstruct timing
        print("\nFAISS reconstruct():")
        faiss_times = []
        for idx in indices:
            start = time.perf_counter()
            _vector = faiss_index.reconstruct(idx)
            elapsed = (time.perf_counter() - start) * 1_000_000  # μs
            faiss_times.append(elapsed)

        print(f"  Mean:   {mean(faiss_times):7.2f} μs")
        print(f"  Median: {median(faiss_times):7.2f} μs")
        print(f"  P95:    {percentile(faiss_times, 95):7.2f} μs")

        # Mmap timing (if available)
        mmap_times = []
        if self.mmap_path and self.mmap_path.exists():
            storage = MmapVectorStorage(self.mmap_path, self.dimension)
            if storage.load():
                print("\nMmap get_vector():")
                for idx in indices:
                    start = time.perf_counter()
                    _vector = storage.get_vector(idx)
                    elapsed = (time.perf_counter() - start) * 1_000_000  # μs
                    mmap_times.append(elapsed)

                print(f"  Mean:   {mean(mmap_times):7.2f} μs")
                print(f"  Median: {median(mmap_times):7.2f} μs")
                print(f"  P95:    {percentile(mmap_times, 95):7.2f} μs")

                storage.close()

        # Calculate speedup
        if faiss_times and mmap_times:
            speedup = mean(faiss_times) / mean(mmap_times)
            print(f"\nSpeedup: {speedup:.2f}x")

            meets_threshold = speedup >= 2.0
            if meets_threshold:
                print(f"✅ PASSED: Mmap {speedup:.2f}x faster (≥2x threshold)")
            else:
                print(f"❌ FAILED: Mmap only {speedup:.2f}x faster (<2x threshold)")
        else:
            speedup = None
            meets_threshold = False
            print("\n⚠️  Could not calculate speedup (mmap not available)")

        return {
            "status": "success",
            "vector_count": vector_count,
            "faiss_mean_us": mean(faiss_times) if faiss_times else None,
            "faiss_median_us": median(faiss_times) if faiss_times else None,
            "mmap_mean_us": mean(mmap_times) if mmap_times else None,
            "mmap_median_us": median(mmap_times) if mmap_times else None,
            "speedup": speedup,
            "meets_2x_threshold": meets_threshold,
        }

    def measure_memory_usage(self) -> Dict:
        """Measure memory usage with/without mmap."""
        print("\n" + "-" * 70)
        print("3. MEMORY USAGE COMPARISON")
        print("-" * 70)

        try:
            import psutil
        except ImportError:
            print("⚠️  psutil not installed, skipping memory test")
            return {"status": "skipped", "reason": "psutil not available"}

        process = psutil.Process()

        # Measure FAISS memory
        print("\nMeasuring FAISS memory usage...")
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        faiss_index = FaissVectorIndex(self.faiss_path)
        faiss_index.load()
        mem_after_faiss = process.memory_info().rss / 1024 / 1024  # MB
        mem_faiss = mem_after_faiss - mem_before
        vector_count = faiss_index._index.ntotal if faiss_index._index else 0

        print(f"  FAISS memory: {mem_faiss:.2f} MB")

        # Measure mmap memory
        mem_mmap = None
        if self.mmap_path and self.mmap_path.exists():
            print("\nMeasuring mmap memory usage...")
            mem_before = process.memory_info().rss / 1024 / 1024  # MB
            storage = MmapVectorStorage(self.mmap_path, self.dimension)
            storage.load()

            # Access some vectors to trigger page loading
            for i in range(min(100, storage.count)):
                storage.get_vector(i)

            mem_after_mmap = process.memory_info().rss / 1024 / 1024  # MB
            mem_mmap = mem_after_mmap - mem_before

            print(f"  Mmap memory:  {mem_mmap:.2f} MB")
            storage.close()

        # Check storage files
        faiss_size = self.faiss_path.stat().st_size / 1024 / 1024  # MB
        mmap_size = (
            self.mmap_path.stat().st_size / 1024 / 1024 if self.mmap_path else 0
        )  # MB

        print("\nDisk storage:")
        print(f"  FAISS index: {faiss_size:.2f} MB")
        if mmap_size > 0:
            print(f"  Mmap file:   {mmap_size:.2f} MB")
            print(f"  Total:       {faiss_size + mmap_size:.2f} MB (duplicate storage)")

        return {
            "status": "success",
            "vector_count": vector_count,
            "faiss_memory_mb": mem_faiss,
            "mmap_memory_mb": mem_mmap,
            "faiss_disk_mb": faiss_size,
            "mmap_disk_mb": mmap_size,
            "total_disk_mb": faiss_size + mmap_size,
        }

    def run_full_benchmark(self) -> Dict:
        """Run complete benchmark suite."""
        print("=" * 70)
        print("MMAP VECTOR STORAGE REALISTIC PERFORMANCE BENCHMARK")
        print("=" * 70)

        results = {}

        # 1. Access time distribution
        results["access_time"] = self.measure_access_time_distribution()

        # 2. Mmap vs FAISS at current scale
        results["mmap_vs_faiss"] = self.measure_mmap_vs_faiss_at_current_scale()

        # 3. Memory usage
        results["memory"] = self.measure_memory_usage()

        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        if results["access_time"]["status"] == "success":
            warm_median = results["access_time"]["warm_median_us"]
            print(f"Warm access time:  {warm_median:.2f} μs (claim: <1 μs)")

        if results["mmap_vs_faiss"]["status"] == "success":
            speedup = results["mmap_vs_faiss"]["speedup"]
            if speedup:
                print(f"Mmap speedup:      {speedup:.2f}x (threshold: ≥2x)")

        if results["memory"]["status"] == "success":
            total_disk = results["memory"]["total_disk_mb"]
            print(f"Total disk usage:  {total_disk:.2f} MB (FAISS + mmap)")

        # Overall assessment
        _meets_1us = results["access_time"].get("meets_1us_claim", False)
        meets_2x = results["mmap_vs_faiss"].get("meets_2x_threshold", False)

        threshold_met = meets_2x  # Primary criterion is 2x speedup

        if threshold_met:
            print("\n✅ PASSED: Mmap provides ≥2x speedup")
        else:
            print("\n❌ FAILED: Mmap does not provide ≥2x speedup")
            print("   Conclusion: Not justified at current scale (964 vectors)")

        results["threshold_met"] = threshold_met

        return results


def main():
    """Run benchmark."""
    # Determine storage directory
    storage_dir = Path("C:/Users/Inter/.claude_code_search")

    if not storage_dir.exists():
        print(f"ERROR: Storage directory not found: {storage_dir}")
        sys.exit(1)

    try:
        # Run benchmark
        benchmark = MmapRealisticBenchmark(storage_dir)
        results = benchmark.run_full_benchmark()

        # Exit with appropriate code
        sys.exit(0 if results["threshold_met"] else 1)

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
