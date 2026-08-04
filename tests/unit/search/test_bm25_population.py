"""
Debug test script for BM25 index population issue.

This script directly tests the HybridSearcher to see if BM25 indices are being populated correctly.
"""

import logging
import os
import shutil
import tempfile
from pathlib import Path


# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Enable debug mode
os.environ["MCP_DEBUG"] = "1"


def test_bm25_population():
    """Test BM25 index population directly."""
    print("[TEST] Starting BM25 population test...")

    # Create temporary storage directory
    temp_dir = Path(tempfile.mkdtemp(prefix="test_bm25_"))
    print(f"[TEST] Using temporary storage: {temp_dir}")

    try:
        import numpy as np

        from embeddings.embedder import EmbeddingResult
        from search.config import MultiHopConfig, SearchConfig
        from search.hybrid_searcher import HybridSearcher

        # Initialize HybridSearcher
        print("[TEST] Initializing HybridSearcher...")
        searcher = HybridSearcher(str(temp_dir))

        # Create test embedding results. Each doc gets a distinct topic word —
        # sharing identical vocabulary across all 5 docs (as the original
        # fixture did) makes every term appear in 100% of the corpus, which
        # drives its BM25 IDF weight negative (classic Okapi IDF goes negative
        # once a term appears in more than half the corpus) and silently zeroes
        # out every search below. A unique-per-doc topic keeps IDF positive so
        # the search below can actually discriminate between documents.
        print("[TEST] Creating test embedding results...")
        topics = ["authentication", "database", "caching", "validation", "networking"]
        test_results = []
        for i, topic in enumerate(topics):
            result = EmbeddingResult(
                embedding=np.random.rand(768).astype(np.float32),
                chunk_id=f"test_chunk_{i}",
                metadata={
                    "content": f"Test content {i} implementing {topic} logic with function test_{i}() return True",
                    "file_path": f"test_{i}.py",
                    "content_preview": f"function test_{i}() code sample",
                    "raw_content": f"def test_{i}():\n    return True\n",
                },
            )
            test_results.append(result)

        print(f"[TEST] Created {len(test_results)} test embedding results")

        # Check initial state
        print(f"[TEST] Initial BM25 ready: {not searcher.bm25_index.is_empty}")
        print(f"[TEST] Initial BM25 size: {searcher.bm25_index.size}")
        print(
            f"[TEST] Initial dense ready: {searcher.dense_index.index is not None and searcher.dense_index.index.ntotal > 0}"
        )
        print(f"[TEST] Initial searcher ready: {searcher.is_ready}")

        assert searcher.bm25_index.is_empty, "BM25 index should start empty"
        assert searcher.bm25_index.size == 0, "BM25 index should start with size 0"

        # Add embeddings
        print("[TEST] Adding embeddings to HybridSearcher...")
        searcher.add_embeddings(test_results)

        # Check state after adding
        print(f"[TEST] After adding - BM25 ready: {not searcher.bm25_index.is_empty}")
        print(f"[TEST] After adding - BM25 size: {searcher.bm25_index.size}")
        print(
            f"[TEST] After adding - dense ready: {searcher.dense_index.index is not None and searcher.dense_index.index.ntotal > 0}"
        )
        print(f"[TEST] After adding - searcher ready: {searcher.is_ready}")

        assert not searcher.bm25_index.is_empty, (
            "BM25 index should be populated after add_embeddings"
        )
        assert searcher.bm25_index.size == len(test_results), (
            f"BM25 index size should equal {len(test_results)} added embeddings, "
            f"got {searcher.bm25_index.size}"
        )
        assert searcher.dense_index.index is not None
        assert searcher.dense_index.index.ntotal == len(test_results), (
            f"Dense index should hold {len(test_results)} embeddings, "
            f"got {searcher.dense_index.index.ntotal}"
        )
        assert searcher.is_ready, "Searcher should be ready after add_embeddings"

        # Save indices
        print("[TEST] Saving indices...")
        searcher.save_indices()

        # Check if BM25 files exist
        bm25_dir = temp_dir / "bm25"
        print(f"[TEST] BM25 directory exists: {bm25_dir.exists()}")
        assert bm25_dir.exists(), "BM25 directory should exist after save_indices"
        bm25_files = list(bm25_dir.iterdir())
        print(f"[TEST] BM25 files: {[f.name for f in bm25_files]}")
        assert bm25_files, "BM25 directory should contain saved index files"

        # Check file sizes
        for file in bm25_files:
            size = file.stat().st_size
            print(f"[TEST] {file.name}: {size} bytes")
            assert size > 0, f"Saved BM25 file {file.name} should not be empty"

        # Check dense files
        dense_files = [f for f in temp_dir.iterdir() if f.is_file()]
        print(f"[TEST] Dense index files: {[f.name for f in dense_files]}")
        assert dense_files, "Dense index directory should contain saved files"

        # Test search functionality. Query for a topic word unique to
        # test_chunk_2 ("caching") so BM25 has a discriminative term to match.
        # Uses search_mode="bm25" with an isolated SearchConfig (multi-hop
        # disabled) rather than "hybrid": this test's job is to verify BM25
        # population/retrieval, not RRF fusion quality, and hybrid mode would
        # let two things it doesn't control decide the outcome -- the ambient
        # ServiceLocator config (search() falls back to it whenever no
        # explicit `config=` is passed, so results would depend on whatever
        # search_config.json happens to be on disk) and dense_weight=0.65 of
        # the ranking coming from these documents' literally random,
        # query-uncorrelated embeddings (np.random.rand above).
        print("[TEST] Testing search functionality...")
        assert searcher.is_ready, "Searcher should be ready before searching"
        search_config = SearchConfig(multi_hop=MultiHopConfig(enabled=False))
        results = searcher.search(
            "caching", k=3, search_mode="bm25", config=search_config
        )
        print(f"[TEST] Search returned {len(results)} results")
        for i, result in enumerate(results):
            print(
                f"[TEST] Result {i + 1}: {result.chunk_id} (score: {result.score:.4f})"
            )
        assert results, "Search for 'caching' should return results"
        result_ids = {result.chunk_id for result in results}
        assert "test_chunk_2" in result_ids, (
            "Search for 'caching' should surface the chunk whose content "
            f"actually discusses caching; got {result_ids}"
        )

        # Create a new searcher to test loading
        print("[TEST] Testing index loading with new searcher...")
        searcher2 = HybridSearcher(str(temp_dir))
        print(f"[TEST] New searcher - BM25 ready: {not searcher2.bm25_index.is_empty}")
        print(f"[TEST] New searcher - BM25 size: {searcher2.bm25_index.size}")
        print(
            f"[TEST] New searcher - dense ready: {searcher2.dense_index.index is not None and searcher2.dense_index.index.ntotal > 0}"
        )
        print(f"[TEST] New searcher ready: {searcher2.is_ready}")

        assert not searcher2.bm25_index.is_empty, (
            "Reloaded searcher should have a populated BM25 index"
        )
        assert searcher2.bm25_index.size == len(test_results), (
            f"Reloaded BM25 index size should equal {len(test_results)}, "
            f"got {searcher2.bm25_index.size}"
        )
        assert searcher2.is_ready, "Reloaded searcher should be ready"

        searcher.shutdown()
        searcher2.shutdown()

        print("[TEST] BM25 population test completed successfully!")

    except Exception as e:
        print(f"[TEST] Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise AssertionError(f"Test failed with error: {e}") from e
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"[TEST] Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"[TEST] Failed to cleanup {temp_dir}: {e}")
