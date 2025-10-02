#!/usr/bin/env python3
"""Test script to verify auto-reindex functionality."""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.incremental_indexer import IncrementalIndexer
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher


@patch('embeddings.embedder.SentenceTransformer')
def test_auto_reindex(mock_sentence_transformer):
    """Test the auto-reindex feature."""

    # Mock the SentenceTransformer to avoid downloading models
    mock_model = Mock()
    mock_model.encode.return_value = np.random.randn(768).astype('float32')  # Return random embedding
    mock_model.get_sentence_embedding_dimension.return_value = 768
    mock_sentence_transformer.return_value = mock_model

    # Use the test project
    test_project = Path(__file__).parent.parent / "test_data" / "python_project"
    project_name = "test_project"

    print(f"\n{'=' * 60}")
    print("Testing Auto-Reindex Feature")
    print(f"{'=' * 60}\n")

    # Initialize components
    print("1. Initializing components...")
    storage_dir = Path.home() / ".claude_code_search" / "test_auto_reindex"
    storage_dir.mkdir(parents=True, exist_ok=True)

    index_dir = storage_dir / "index"
    index_dir.mkdir(exist_ok=True)

    embedder = CodeEmbedder(cache_dir=str(storage_dir / "models"))
    index_manager = CodeIndexManager(str(index_dir))
    chunker = MultiLanguageChunker(str(test_project))

    indexer = IncrementalIndexer(
        indexer=index_manager, embedder=embedder, chunker=chunker
    )

    # First index
    print("\n2. Performing initial index...")
    result1 = indexer.incremental_index(str(test_project), project_name)
    print(f"   - Files indexed: {result1.files_added}")
    print(f"   - Chunks created: {result1.chunks_added}")
    print(f"   - Time taken: {result1.time_taken:.2f}s")

    # Create searcher
    searcher = IntelligentSearcher(index_manager, embedder)

    # Test immediate search (should not reindex)
    print("\n3. Testing immediate search (should not trigger reindex)...")
    start = time.time()
    reindex_result = indexer.auto_reindex_if_needed(
        str(test_project), project_name, max_age_minutes=5
    )
    elapsed = time.time() - start

    print(
        f"   - Reindex triggered: {'Yes' if reindex_result.files_modified > 0 else 'No'}"
    )
    print(f"   - Time taken: {elapsed:.3f}s")

    # Check snapshot age
    stats = indexer.get_indexing_stats(str(test_project))
    if stats:
        age_seconds = stats.get("snapshot_age", 0)
        print(f"   - Index age: {age_seconds:.1f} seconds")

    # Simulate waiting (we'll use a very short time for testing)
    print("\n4. Testing with 0.1 minute (6 second) max age...")
    print("   Waiting 7 seconds...")
    time.sleep(7)

    # Test with very short max age
    start = time.time()
    reindex_result = indexer.auto_reindex_if_needed(
        str(test_project),
        project_name,
        max_age_minutes=0.1,  # 6 seconds
    )
    elapsed = time.time() - start

    print(
        f"   - Reindex triggered: {'Yes' if reindex_result.files_modified > 0 or reindex_result.files_added > 0 else 'No'}"
    )
    print(f"   - Time taken: {elapsed:.3f}s")

    # Check new snapshot age
    stats = indexer.get_indexing_stats(str(test_project))
    if stats:
        age_seconds = stats.get("snapshot_age", 0)
        print(f"   - New index age: {age_seconds:.1f} seconds")

    # Test search functionality after auto-reindex
    print("\n5. Testing search after auto-reindex...")
    results = searcher.search("database connection", k=3)
    print(f"   - Search returned {len(results)} results")
    if results:
        print(f"   - Top result: {results[0].name} in {results[0].file_path}")

    # Test needs_reindex function
    print("\n6. Testing needs_reindex function...")
    needs_now = indexer.needs_reindex(str(test_project), max_age_minutes=5)
    print(f"   - Needs reindex (5 min threshold): {needs_now}")

    needs_short = indexer.needs_reindex(
        str(test_project), max_age_minutes=0.01
    )  # 0.6 seconds
    print(f"   - Needs reindex (0.01 min threshold): {needs_short}")

    print(f"\n{'=' * 60}")
    print("[OK] Auto-reindex test completed!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    import logging

    try:
        test_auto_reindex()
        # Clean up logging handlers
        logging.shutdown()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        logging.shutdown()
        sys.exit(1)
