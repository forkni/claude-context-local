"""
Debug test script for BM25 index population issue.

This script directly tests the HybridSearcher to see if BM25 indices are being populated correctly.
"""

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Set up debug logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Enable debug mode
os.environ["MCP_DEBUG"] = "1"

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_bm25_population():
    """Test BM25 index population directly."""
    print("[TEST] Starting BM25 population test...")

    # Create temporary storage directory
    temp_dir = Path(tempfile.mkdtemp(prefix="test_bm25_"))
    print(f"[TEST] Using temporary storage: {temp_dir}")

    try:
        import numpy as np

        from embeddings.embedder import EmbeddingResult
        from search.hybrid_searcher import HybridSearcher

        # Initialize HybridSearcher
        print("[TEST] Initializing HybridSearcher...")
        searcher = HybridSearcher(str(temp_dir))

        # Create test embedding results
        print("[TEST] Creating test embedding results...")
        test_results = []
        for i in range(5):
            result = EmbeddingResult(
                embedding=np.random.rand(768).astype(np.float32),
                chunk_id=f"test_chunk_{i}",
                metadata={
                    "content": f"Test content {i} with some code function test_{i}() return True",
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

        # Save indices
        print("[TEST] Saving indices...")
        searcher.save_index()

        # Check if BM25 files exist
        bm25_dir = temp_dir / "bm25"
        print(f"[TEST] BM25 directory exists: {bm25_dir.exists()}")
        if bm25_dir.exists():
            bm25_files = list(bm25_dir.iterdir())
            print(f"[TEST] BM25 files: {[f.name for f in bm25_files]}")

            # Check file sizes
            for file in bm25_files:
                size = file.stat().st_size
                print(f"[TEST] {file.name}: {size} bytes")

        # Check dense files
        dense_files = [f for f in temp_dir.iterdir() if f.is_file()]
        print(f"[TEST] Dense index files: {[f.name for f in dense_files]}")

        # Test search functionality
        print("[TEST] Testing search functionality...")
        if searcher.is_ready:
            try:
                results = searcher.search("test function", k=3, search_mode="hybrid")
                print(f"[TEST] Search returned {len(results)} results")
                for i, result in enumerate(results):
                    print(
                        f"[TEST] Result {i + 1}: {result.chunk_id} (score: {result.score:.4f})"
                    )
            except Exception as e:
                print(f"[TEST] Search failed: {e}")
        else:
            print("[TEST] Searcher not ready, skipping search test")

        # Create a new searcher to test loading
        print("[TEST] Testing index loading with new searcher...")
        searcher2 = HybridSearcher(str(temp_dir))
        print(f"[TEST] New searcher - BM25 ready: {not searcher2.bm25_index.is_empty}")
        print(f"[TEST] New searcher - BM25 size: {searcher2.bm25_index.size}")
        print(
            f"[TEST] New searcher - dense ready: {searcher2.dense_index.index is not None and searcher2.dense_index.index.ntotal > 0}"
        )
        print(f"[TEST] New searcher ready: {searcher2.is_ready}")

        searcher.shutdown()
        searcher2.shutdown()

        print("[TEST] BM25 population test completed successfully!")
        # Test passes
        assert True

    except Exception as e:
        print(f"[TEST] Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        raise AssertionError(f"Test failed with error: {e}")
    finally:
        # Cleanup
        try:
            shutil.rmtree(temp_dir)
            print(f"[TEST] Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"[TEST] Failed to cleanup {temp_dir}: {e}")


if __name__ == "__main__":
    success = test_bm25_population()
    sys.exit(0 if success else 1)
