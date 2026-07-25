"""Integration tests for Phase 2 implementation.

Tests:
- Phase 2: Symbol Hash Cache O(1) lookups
"""

import tempfile
import time
from pathlib import Path

from search.metadata import MetadataStore


def test_phase2_symbol_hash_cache():
    """Test that symbol hash cache provides O(1) lookups."""
    # Setup
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "metadata.db"
    store = MetadataStore(db_path)

    print("\n=== Phase 2: Symbol Hash Cache ===\n")

    # Add test chunks
    test_chunks = []
    for i in range(100):
        chunk_id = f"search/module_{i % 10}.py:{i * 10}-{i * 10 + 10}:function:func_{i}"
        metadata = {
            "relative_path": f"search/module_{i % 10}.py",
            "chunk_type": "function",
        }
        store.set(chunk_id, i, metadata)
        test_chunks.append(chunk_id)

    store.commit()

    # Verify hash cache is populated
    cache_stats = store._symbol_cache.get_stats()
    print("Cache Statistics:")
    print(f"  Total symbols: {cache_stats['total_symbols']}")
    print(
        f"  Buckets used: {cache_stats['used_buckets']}/{cache_stats['bucket_count']}"
    )
    print(f"  Load factor: {cache_stats['load_factor']:.1f}%")
    print(f"  Avg bucket size: {cache_stats['avg_bucket_size']:.2f}")
    print(f"  Memory estimate: {cache_stats['memory_estimate_mb']:.3f} MB")

    assert cache_stats["total_symbols"] == 100, "Should have 100 cached symbols"

    # Benchmark O(1) lookups
    iterations = 1000
    start = time.perf_counter()

    for _ in range(iterations):
        for chunk_id in test_chunks[:10]:  # Test with 10 chunks
            result = store.get(chunk_id)
            assert result is not None

    end = time.perf_counter()
    avg_time_us = ((end - start) / (iterations * 10)) * 1_000_000

    print("\nPerformance:")
    print(f"  Average lookup time: {avg_time_us:.2f} us")
    print(f"  Total time for {iterations * 10:,} lookups: {(end - start):.3f}s")

    # The hash cache is in-memory only (PYTHONHASHSEED randomizes hash() per
    # process, so a persisted cache would carry no working entries in a fresh
    # process anyway) — no cache file is ever written.
    cache_path = db_path.parent / f"{db_path.stem}_symbol_cache.json"
    assert not cache_path.exists(), "Symbol cache should never be persisted to disk"

    # A fresh MetadataStore starts with an empty in-memory cache, but the
    # underlying SQLite data is still there and reachable via get().
    store.close()
    store2 = MetadataStore(db_path)

    for chunk_id in test_chunks[:5]:
        assert chunk_id not in store2._symbol_cache, (
            f"Fresh store's in-memory cache should not contain {chunk_id}"
        )
        assert store2.get(chunk_id) is not None, (
            f"Symbol {chunk_id} should still be retrievable from SQLite"
        )

    print("\n[OK] Phase 2 tests passed!")
    print(f"[OK] Symbol cache O(1) lookups: {avg_time_us:.2f} us average")

    store2.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing Phase 2 Implementation")
    print("=" * 60)

    # Test Phase 2
    test_phase2_symbol_hash_cache()

    print("\n" + "=" * 60)
    print("[OK] Phase 2 integration test passed!")
    print("=" * 60 + "\n")
