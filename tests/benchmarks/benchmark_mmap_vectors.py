"""Benchmark script for MmapVectorStorage performance.

Compares memory-mapped vector access vs FAISS reconstruct performance.
Tests cold start vs warm cache, sequential vs random access patterns.
"""

import tempfile
import time
from pathlib import Path

import numpy as np

try:
    import faiss
except ImportError:
    faiss = None

from search.faiss_index import FaissVectorIndex
from search.mmap_vectors import MmapVectorStorage


def format_time(microseconds):
    """Format microseconds for display."""
    if microseconds < 1:
        return f"{microseconds * 1000:.2f} ns"
    elif microseconds < 1000:
        return f"{microseconds:.2f} us"
    else:
        return f"{microseconds / 1000:.2f} ms"


def benchmark_mmap_vs_faiss():
    """Compare mmap vs FAISS reconstruct performance."""
    print("\n" + "=" * 70)
    print("MmapVectorStorage vs FAISS Reconstruct Benchmark")
    print("=" * 70)

    # Test parameters
    dimension = 1024
    vector_counts = [100, 1000, 5000]
    iterations = 1000

    for count in vector_counts:
        print(f"\n{'='*70}")
        print(f"Vector count: {count:,} (dimension: {dimension})")
        print(f"{'='*70}")

        # Setup
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        index_path = temp_path / "test.index"
        mmap_path = temp_path / "test_vectors.mmap"

        # Create test data
        embeddings = np.random.randn(count, dimension).astype(np.float32)
        # Normalize for FAISS
        faiss.normalize_L2(embeddings)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(count)]

        # Create FAISS index
        faiss_index = FaissVectorIndex(index_path)
        faiss_index.create(dimension, "flat")
        faiss_index.add(embeddings, chunk_ids)
        faiss_index.save()

        # Create mmap storage
        mmap_storage = MmapVectorStorage(mmap_path, dimension)
        mmap_storage.save(embeddings, chunk_ids)
        mmap_storage.load()

        print(f"\n1. Sequential Access (0 -> {count-1})")
        print("-" * 70)

        # Benchmark 1: FAISS reconstruct (sequential)
        indices_to_test = list(range(min(100, count)))
        start = time.perf_counter()
        for _ in range(iterations):
            for idx in indices_to_test:
                _ = faiss_index.reconstruct(idx)
        end = time.perf_counter()
        faiss_time_us = (
            (end - start) / (iterations * len(indices_to_test))
        ) * 1_000_000

        # Benchmark 2: Mmap access (sequential)
        start = time.perf_counter()
        for _ in range(iterations):
            for idx in indices_to_test:
                _ = mmap_storage.get_vector(idx)
        end = time.perf_counter()
        mmap_time_us = ((end - start) / (iterations * len(indices_to_test))) * 1_000_000

        speedup = faiss_time_us / mmap_time_us if mmap_time_us > 0 else float("inf")

        print(f"  FAISS reconstruct:  {format_time(faiss_time_us):>12}")
        print(f"  Mmap access:        {format_time(mmap_time_us):>12}")
        print(f"  Speedup:            {speedup:.2f}x faster")
        print(
            "  Target:             <1.00 us"
            + (" [OK]" if mmap_time_us < 1 else " [FAILED]")
        )

        print("\n2. Random Access")
        print("-" * 70)

        # Benchmark 3: FAISS reconstruct (random)
        random_indices = np.random.randint(0, count, size=min(100, count))
        start = time.perf_counter()
        for _ in range(iterations):
            for idx in random_indices:
                _ = faiss_index.reconstruct(idx)
        end = time.perf_counter()
        faiss_random_us = (
            (end - start) / (iterations * len(random_indices))
        ) * 1_000_000

        # Benchmark 4: Mmap access (random)
        start = time.perf_counter()
        for _ in range(iterations):
            for idx in random_indices:
                _ = mmap_storage.get_vector(idx)
        end = time.perf_counter()
        mmap_random_us = (
            (end - start) / (iterations * len(random_indices))
        ) * 1_000_000

        speedup_random = (
            mmap_random_us / mmap_random_us if mmap_random_us > 0 else float("inf")
        )

        print(f"  FAISS reconstruct:  {format_time(faiss_random_us):>12}")
        print(f"  Mmap access:        {format_time(mmap_random_us):>12}")
        print(f"  Speedup:            {speedup_random:.2f}x faster")

        print("\n3. Cold Start (First Access)")
        print("-" * 70)

        # Benchmark 5: Cold start - create new storage and time first access
        mmap_storage.close()
        mmap_storage2 = MmapVectorStorage(mmap_path, dimension)

        start = time.perf_counter()
        mmap_storage2.load()
        _ = mmap_storage2.get_vector(0)
        end = time.perf_counter()
        cold_start_us = (end - start) * 1_000_000

        print(f"  Load + first access: {format_time(cold_start_us):>12}")

        # Benchmark 6: Warm cache - subsequent access
        start = time.perf_counter()
        for _ in range(iterations):
            _ = mmap_storage2.get_vector(0)
        end = time.perf_counter()
        warm_cache_us = ((end - start) / iterations) * 1_000_000

        print(f"  Warm cache access:   {format_time(warm_cache_us):>12}")
        print(
            "  Target:              <1.00 us"
            + (" [OK]" if warm_cache_us < 1 else " [FAILED]")
        )

        # Cleanup
        mmap_storage.close()
        mmap_storage2.close()
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n{'='*70}")
    print("Benchmark Complete")
    print(f"{'='*70}\n")


def benchmark_different_dimensions():
    """Benchmark performance across different embedding dimensions."""
    print("\n" + "=" * 70)
    print("Dimension Scaling Benchmark")
    print("=" * 70)

    dimensions = [384, 768, 1024, 2048]
    count = 1000
    iterations = 1000

    results = []

    for dim in dimensions:
        print(f"\nDimension: {dim}")
        print("-" * 70)

        # Setup
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir)
        mmap_path = temp_path / f"vectors_{dim}d.mmap"

        # Create test data
        embeddings = np.random.randn(count, dim).astype(np.float32)
        chunk_ids = [f"file{i}.py:1-10:function:func{i}" for i in range(count)]

        # Create and load mmap storage
        storage = MmapVectorStorage(mmap_path, dim)
        storage.save(embeddings, chunk_ids)
        storage.load()

        # Benchmark warm cache access
        indices = list(range(100))
        start = time.perf_counter()
        for _ in range(iterations):
            for idx in indices:
                _ = storage.get_vector(idx)
        end = time.perf_counter()
        avg_time_us = ((end - start) / (iterations * len(indices))) * 1_000_000

        results.append((dim, avg_time_us))
        print(f"  Average access time: {format_time(avg_time_us):>12}")
        print(
            "  Target:              <1.00 us"
            + (" [OK]" if avg_time_us < 1 else " [FAILED]")
        )

        # Cleanup
        storage.close()
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n{'='*70}")
    print("Results Summary")
    print("-" * 70)
    for dim, time_us in results:
        print(f"  {dim:>4}d: {format_time(time_us):>12}")
    print(f"{'='*70}\n")


def main():
    """Run all benchmarks."""
    if faiss is None:
        print("ERROR: FAISS not available, skipping benchmarks")
        return

    print("\n" + "=" * 70)
    print("Memory-Mapped Vector Storage Performance Benchmarks")
    print("=" * 70)
    print("\nThese benchmarks measure the performance of memory-mapped vector")
    print("storage compared to FAISS's built-in reconstruct method.")
    print("\nTarget: <1us average access time after OS cache warm")
    print("=" * 70)

    benchmark_mmap_vs_faiss()
    benchmark_different_dimensions()

    print("\n" + "=" * 70)
    print("All Benchmarks Complete")
    print("=" * 70)
    print("\nNote: Access times <1us indicate successful memory-mapped performance.")
    print("First access may be slower due to OS page faults (expected).")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
