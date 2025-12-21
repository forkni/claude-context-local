"""Test mmap file cleanup during index clearing and threshold management."""

import shutil
import tempfile
from pathlib import Path

import numpy as np

from search.faiss_index import FaissVectorIndex


def test_mmap_cleanup_on_clear():
    """Test that mmap files are deleted when clear() is called."""
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create index (mmap auto-enabled for >10K vectors)
        index_path = temp_dir / "code.index"
        faiss_index = FaissVectorIndex(index_path)

        # Create and populate index
        faiss_index.create(dimension=768, index_type="flat")
        embeddings = np.random.rand(100, 768).astype(np.float32)
        chunk_ids = [f"chunk_{i}" for i in range(100)]
        faiss_index.add(embeddings, chunk_ids)

        # Manually create a fake mmap file (simulating old file)
        mmap_path = temp_dir / "code_vectors.mmap"
        mmap_path.write_text("fake mmap data")

        print(f"Before clear: mmap exists = {mmap_path.exists()}")
        assert mmap_path.exists(), "Mmap file should exist before clear"

        # Call clear() - should delete mmap file
        faiss_index.clear()

        print(f"After clear: mmap exists = {mmap_path.exists()}")
        assert not mmap_path.exists(), "Mmap file should be deleted after clear"

        print("[OK] Test passed: Mmap file deleted on clear()")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mmap_threshold_management():
    """Test that mmap files are created/deleted based on vector count threshold."""
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # Create index (mmap auto-enabled for >10K vectors)
        index_path = temp_dir / "code.index"
        faiss_index = FaissVectorIndex(index_path)

        # Create index with few vectors (below 10K threshold)
        faiss_index.create(dimension=768, index_type="flat")
        embeddings = np.random.rand(100, 768).astype(np.float32)
        chunk_ids = [f"chunk_{i}" for i in range(100)]
        faiss_index.add(embeddings, chunk_ids)

        # Manually create old mmap file (simulating file from before threshold)
        mmap_path = temp_dir / "code_vectors.mmap"
        mmap_path.write_text("old mmap data")
        assert mmap_path.exists(), "Setup: mmap file should exist"

        # Save with vector count below threshold - should DELETE mmap
        faiss_index.save()

        print(
            f"After save (100 vectors < 10K threshold): mmap exists = {mmap_path.exists()}"
        )
        assert (
            not mmap_path.exists()
        ), "Mmap file should be deleted when below threshold"

        print("[OK] Test passed: Mmap file deleted when below threshold")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=" * 70)
    print("MMAP CLEANUP TESTS")
    print("=" * 70)

    test_mmap_cleanup_on_clear()
    print()
    test_mmap_threshold_management()

    print()
    print("=" * 70)
    print("ALL TESTS PASSED [OK]")
    print("=" * 70)
