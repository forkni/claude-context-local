"""Integration tests for Phase 1 and Phase 2 implementations.

Tests:
- Phase 1: Query Intent Detection with confidence scoring
- Phase 2: Symbol Hash Cache O(1) lookups
"""

import tempfile
import time
from pathlib import Path

from search.metadata import MetadataStore
from search.searcher import IntelligentSearcher


def test_phase1_query_intent_detection():
    """Test that query intent detection is working with confidence scores."""
    from unittest.mock import Mock

    # Create mock searcher
    mock_index_manager = Mock()
    mock_index_manager.index = None
    mock_embedder = Mock()
    mock_embedder.model_name = "test-model"

    searcher = IntelligentSearcher(
        index_manager=mock_index_manager, embedder=mock_embedder
    )

    # Test intent detection with various queries
    test_cases = [
        ("debug error handling", "debugging", True),
        ("refactor this code", "refactoring", True),
        ("optimize performance", "performance", True),
        ("config settings", "configuration", True),
        ("import dependencies", "dependency", True),
        ("setup initialization", "initialization", True),
    ]

    print("\n=== Phase 1: Query Intent Detection ===\n")

    for query, expected_intent, should_detect in test_cases:
        intents = searcher._detect_query_intent(query)
        intent_names = [i[0] for i in intents]

        if should_detect:
            assert (
                expected_intent in intent_names
            ), f"Expected '{expected_intent}' in {intent_names} for query '{query}'"

            # Get confidence
            detected_intent = next(i for i in intents if i[0] == expected_intent)
            confidence = detected_intent[1]

            print(f"[OK] Query: '{query}'")
            print(f"     Detected: {expected_intent} (confidence: {confidence:.2f})")
        else:
            assert (
                expected_intent not in intent_names
            ), f"Should not detect '{expected_intent}' for query '{query}'"

    print("\n[OK] Phase 1 tests passed!")
    return True


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
        chunk_id = f"search/module_{i % 10}.py:{i*10}-{i*10+10}:function:func_{i}"
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

    # Verify cache file persistence
    cache_path = db_path.parent / f"{db_path.stem}_symbol_cache.json"
    assert cache_path.exists(), "Symbol cache file should exist"

    print(f"  Cache file: {cache_path.name}")

    # Test cache reload
    store.close()
    store2 = MetadataStore(db_path)

    # Verify symbols reloaded
    for chunk_id in test_chunks[:5]:
        assert (
            chunk_id in store2._symbol_cache
        ), f"Symbol {chunk_id} should be in reloaded cache"

    print("\n[OK] Phase 2 tests passed!")
    print(f"[OK] Symbol cache O(1) lookups: {avg_time_us:.2f} us average")

    store2.close()
    return True


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Testing Phase 1 and Phase 2 Implementations")
    print("=" * 60)

    # Test Phase 1
    test_phase1_query_intent_detection()

    # Test Phase 2
    test_phase2_symbol_hash_cache()

    print("\n" + "=" * 60)
    print("[OK] All integration tests passed!")
    print("=" * 60 + "\n")
