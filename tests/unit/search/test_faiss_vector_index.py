"""Unit tests for FaissVectorIndex class.

Tests the FAISS vector storage layer extracted from CodeIndexManager
as part of Phase 4 refactoring.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pytest

from search.faiss_index import (
    FaissVectorIndex,
    estimate_index_memory_usage,
    get_available_memory,
)


class TestHelperFunctions:
    """Tests for module-level helper functions."""

    def test_get_available_memory(self):
        """Test get_available_memory returns expected keys."""
        memory = get_available_memory()

        assert "system_total" in memory
        assert "system_available" in memory
        assert "gpu_total" in memory
        assert "gpu_available" in memory

        # System memory should be positive
        assert memory["system_total"] > 0
        assert memory["system_available"] > 0

        # GPU memory should be >= 0 (may not have GPU)
        assert memory["gpu_total"] >= 0
        assert memory["gpu_available"] >= 0

    def test_estimate_index_memory_usage_flat(self):
        """Test memory estimation for flat index."""
        estimate = estimate_index_memory_usage(1000, 768, "flat")

        assert "vectors" in estimate
        assert "overhead" in estimate
        assert "total" in estimate

        # Verify calculations
        expected_vectors = 1000 * 768 * 4  # float32
        assert estimate["vectors"] == expected_vectors
        assert estimate["overhead"] == int(expected_vectors * 0.1)
        assert estimate["total"] == estimate["vectors"] + estimate["overhead"]

    def test_estimate_index_memory_usage_ivf(self):
        """Test memory estimation for IVF index."""
        estimate = estimate_index_memory_usage(1000, 768, "ivf")

        # IVF has higher overhead (30% vs 10%)
        expected_vectors = 1000 * 768 * 4
        assert estimate["vectors"] == expected_vectors
        assert estimate["overhead"] == int(expected_vectors * 0.3)


class TestFaissVectorIndexBasicOperations:
    """Tests for basic CRUD operations."""

    def test_initialization(self):
        """Test FaissVectorIndex initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            assert index.index_path == index_path
            assert index.chunk_id_path == Path(tmpdir) / "chunk_ids.pkl"
            assert index.index is None
            assert index.ntotal == 0
            assert index.dimension is None
            assert not index.is_on_gpu
            assert len(index.chunk_ids) == 0

    def test_create_flat_index(self):
        """Test creating a flat index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            index.create(768, "flat")

            assert index.index is not None
            assert index.dimension == 768
            assert index.ntotal == 0
            assert len(index.chunk_ids) == 0

    def test_create_ivf_index(self):
        """Test creating an IVF index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            index.create(768, "ivf")

            assert index.index is not None
            assert index.dimension == 768
            assert index.ntotal == 0

    def test_create_invalid_index_type(self):
        """Test creating index with invalid type raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            with pytest.raises(ValueError, match="Unsupported index type"):
                index.create(768, "invalid_type")

    def test_add_and_search(self):
        """Test adding vectors and searching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Generate deterministic embeddings
            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]

            # Add to index
            index.add(embeddings, chunk_ids)

            assert index.ntotal == 10
            assert len(index.chunk_ids) == 10

            # Search with first embedding
            query = embeddings[0:1]
            distances, indices = index.search(query, k=3)

            assert len(distances) == 3
            assert len(indices) == 3
            # First result should be exact match (index 0)
            assert indices[0] == 0
            # Distance should be close to 1.0 (cosine similarity of normalized vector with itself)
            assert abs(distances[0] - 1.0) < 0.01

    def test_add_without_create_raises_error(self):
        """Test that adding to non-existent index raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            embeddings = np.random.randn(5, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(5)]

            with pytest.raises(ValueError, match="No index exists"):
                index.add(embeddings, chunk_ids)

    def test_search_empty_index_raises_error(self):
        """Test that searching empty index raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            query = np.random.randn(768).astype(np.float32)

            with pytest.raises(ValueError, match="Index is empty"):
                index.search(query, k=5)

    def test_reconstruct(self):
        """Test reconstructing vectors from index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add vectors
            rng = np.random.RandomState(42)
            embeddings = rng.randn(5, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(5)]
            index.add(embeddings, chunk_ids)

            # Reconstruct first vector (normalized version)
            reconstructed = index.reconstruct(0)

            # Should be same dimension
            assert reconstructed.shape == (768,)

            # Should be close to normalized original (cosine similarity check)
            import faiss

            normalized = embeddings[0:1].copy()
            faiss.normalize_L2(normalized)
            similarity = np.dot(reconstructed, normalized[0])
            assert abs(similarity - 1.0) < 0.01


class TestFaissVectorIndexPersistence:
    """Tests for save/load operations."""

    def test_save_and_load(self):
        """Test saving and loading index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"

            # Create and populate index
            index1 = FaissVectorIndex(index_path)
            index1.create(768, "flat")

            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]
            index1.add(embeddings, chunk_ids)

            # Save
            index1.save()

            # Load into new instance
            index2 = FaissVectorIndex(index_path)
            loaded = index2.load()

            assert loaded is True
            assert index2.ntotal == 10
            assert index2.dimension == 768
            assert len(index2.chunk_ids) == 10
            assert index2.chunk_ids == chunk_ids

            # Verify search works on loaded index
            query = embeddings[0:1]
            distances, indices = index2.search(query, k=3)
            assert indices[0] == 0

    def test_load_nonexistent_index(self):
        """Test loading when no index exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "nonexistent.index"
            index = FaissVectorIndex(index_path)

            loaded = index.load()

            assert loaded is False
            assert index.index is None
            assert index.ntotal == 0

    def test_save_without_index(self):
        """Test saving when no index exists logs warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            # Should not raise, just log warning
            index.save()

    def test_dimension_mismatch_detection(self):
        """Test that dimension mismatch is detected when loading with embedder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"

            # Create index with 768 dimensions
            index1 = FaissVectorIndex(index_path)
            index1.create(768, "flat")
            rng = np.random.RandomState(42)
            embeddings = rng.randn(5, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(5)]
            index1.add(embeddings, chunk_ids)
            index1.save()

            # Try to load with embedder expecting 1024 dimensions
            mock_embedder = Mock()
            mock_embedder.get_model_info.return_value = {"embedding_dimension": 1024}
            mock_embedder.model_name = "test-model"

            index2 = FaissVectorIndex(index_path, embedder=mock_embedder)
            loaded = index2.load()

            # Should return False due to mismatch
            assert loaded is False
            assert index2.index is None


class TestFaissVectorIndexGPU:
    """Tests for GPU operations."""

    def test_gpu_is_available(self):
        """Test GPU availability check."""
        # This will return True or False depending on system
        result = FaissVectorIndex.gpu_is_available()
        assert isinstance(result, bool)

    def test_move_to_gpu_when_unavailable(self):
        """Test moving to GPU when GPU is unavailable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Mock GPU as unavailable
            with patch.object(FaissVectorIndex, "gpu_is_available", return_value=False):
                result = index.move_to_gpu()
                assert result is False
                assert not index.is_on_gpu

    def test_move_to_cpu_when_on_cpu(self):
        """Test moving to CPU when already on CPU."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Should be on CPU by default (unless GPU auto-move happened)
            # Force CPU state
            index._on_gpu = False

            result = index.move_to_cpu()
            assert result is False


class TestFaissVectorIndexMemory:
    """Tests for memory management operations."""

    def test_check_memory_requirements(self):
        """Test memory requirements check."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add some vectors
            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]
            index.add(embeddings, chunk_ids)

            # Check memory requirements for adding more
            check = index.check_memory_requirements(100, 768)

            assert "available_memory" in check
            assert "estimated_usage" in check
            assert "sufficient_memory" in check
            assert "prefer_gpu" in check
            assert "current_vectors" in check
            assert "new_vectors" in check
            assert "total_vectors_after" in check

            assert check["current_vectors"] == 10
            assert check["new_vectors"] == 100
            assert check["total_vectors_after"] == 110

    def test_get_memory_status(self):
        """Test getting memory status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add vectors
            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]
            index.add(embeddings, chunk_ids)

            status = index.get_memory_status()

            assert "available_memory" in status
            assert "index_vectors" in status
            assert "on_gpu" in status
            assert "estimated_index_memory" in status

            assert status["index_vectors"] == 10


class TestFaissVectorIndexClear:
    """Tests for clear operations."""

    def test_clear_index(self):
        """Test clearing index."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add vectors and save
            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]
            index.add(embeddings, chunk_ids)
            index.save()

            # Verify files exist
            assert index.index_path.exists()
            assert index.chunk_id_path.exists()

            # Clear
            index.clear()

            # Verify state reset
            assert index.index is None
            assert index.ntotal == 0
            assert len(index.chunk_ids) == 0

            # Verify files deleted
            assert not index.index_path.exists()
            assert not index.chunk_id_path.exists()

    def test_clear_releases_loaded_mmap_handle(self):
        """Test that clear() closes and drops a loaded mmap storage.

        Regression test: clear() used to unlink the mmap file without
        closing the open mmap.mmap/file handle backing self._mmap_storage.
        On Windows the unlink itself would fail (WinError 32, file in use);
        on POSIX it would succeed but reconstruct() would keep serving
        vectors from the now-deleted file via the still-open mapping.
        """
        from search.mmap_vectors import MmapVectorStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(8, "flat")

            rng = np.random.RandomState(42)
            embeddings = rng.randn(3, 8).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(3)]
            index.add(embeddings, chunk_ids)

            # Directly populate the mmap file and load it into the index's
            # storage slot the same way the >MMAP_THRESHOLD save path does
            # (create() below threshold, so exercise the load explicitly).
            mmap_storage = MmapVectorStorage(index._mmap_path, dimension=8)
            mmap_storage.save(embeddings, chunk_ids)
            index._mmap_storage = MmapVectorStorage(index._mmap_path, dimension=8)
            assert index._mmap_storage.load()
            assert index._mmap_storage.is_loaded

            index.clear()

            assert index._mmap_storage is None
            assert not index._mmap_path.exists()

    def test_close_releases_mmap_handle_so_second_instance_can_clear(self):
        """Regression test for the WinError 32 force-reindex failure.

        Mirrors the production bug: two ``FaissVectorIndex`` instances map
        the same ``code_vectors.mmap`` file in one process, because
        ``CodeIndexManager.__init__`` loads the FAISS index unconditionally
        (``search/indexer.py:117-118``) -- a write-only "searcher #1" built
        via ``get_searcher(..., load_existing=False)`` maps the file during
        construction, and a fresh "searcher #2" built moments later for the
        actual reindex maps it again. Before this fix, nothing released
        searcher #1's mmap handle deterministically: ``CodeIndexManager.close()``
        only closed the metadata store, so ``clear()`` on searcher #2's index
        failed unlinking the shared file out from under searcher #1's still-live
        mapping (``PermissionError`` / WinError 32 on Windows).

        The fix is ``close()`` -- closing instance1's own handle, unrelated to
        any call on instance2, is what frees the OS-level lock. This assertion
        holds on every platform (POSIX already tolerated the stale mapping;
        this closes the resource properly instead of relying on that).
        """
        import pickle

        import faiss

        from search.mmap_vectors import MmapVectorStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"

            rng = np.random.RandomState(42)
            embeddings = rng.randn(3, 8).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(3)]

            # Plant a real on-disk index + mmap file -- the same shape
            # save() writes above MMAP_THRESHOLD -- built directly so the
            # test doesn't need 10,000 real vectors.
            seed = FaissVectorIndex(index_path)
            seed.create(8, "flat")
            seed.add(embeddings, chunk_ids)
            # pyrefly: ignore [missing-attribute]
            faiss.write_index(seed.index, str(seed.index_path))
            with open(seed.chunk_id_path, "wb") as f:
                pickle.dump(chunk_ids, f)
            MmapVectorStorage(seed._mmap_path, dimension=8).save(embeddings, chunk_ids)

            # Two independent instances load the same on-disk index, each
            # mapping code_vectors.mmap with its own mmap.mmap/file handle.
            instance1 = FaissVectorIndex(index_path)
            assert instance1.load()
            assert instance1._mmap_storage is not None
            assert instance1._mmap_storage.is_loaded

            instance2 = FaissVectorIndex(index_path)
            assert instance2.load()
            assert instance2._mmap_storage is not None

            instance1.close()
            assert instance1._mmap_storage is None

            instance2.clear()

            assert instance2._mmap_storage is None
            assert not instance2._mmap_path.exists()
            assert not instance2.index_path.exists()
            assert not instance2.chunk_id_path.exists()

    @pytest.mark.skipif(
        sys.platform != "win32", reason="POSIX unlinks mapped files freely"
    )
    def test_clear_still_blocked_by_live_foreign_mapping(self):
        """A second instance's clear() must still fail if nobody closes the
        foreign live mapping -- ``close()`` releases handles, it must not
        make ``clear()`` silently tolerate a mapping it does not own.

        Companion to ``test_close_releases_mmap_handle_so_second_instance_can_clear``:
        guards against a fix that hides the real error instead of closing
        the actual blocking handle.
        """
        import pickle

        import faiss

        from search.mmap_vectors import MmapVectorStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"

            rng = np.random.RandomState(42)
            embeddings = rng.randn(3, 8).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(3)]

            seed = FaissVectorIndex(index_path)
            seed.create(8, "flat")
            seed.add(embeddings, chunk_ids)
            # pyrefly: ignore [missing-attribute]
            faiss.write_index(seed.index, str(seed.index_path))
            with open(seed.chunk_id_path, "wb") as f:
                pickle.dump(chunk_ids, f)
            MmapVectorStorage(seed._mmap_path, dimension=8).save(embeddings, chunk_ids)

            instance1 = FaissVectorIndex(index_path)
            assert instance1.load()

            instance2 = FaissVectorIndex(index_path)
            assert instance2.load()

            # instance1 is never closed here -- its live handle must still
            # block instance2's unlink.
            with pytest.raises(PermissionError):
                instance2.clear()

            instance1.close()


class TestFaissVectorIndexBatchOperations:
    """Tests for batch operations."""

    def test_add_empty_embeddings(self):
        """Test that adding empty embeddings is a no-op."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add empty array
            index.add(np.array([]).reshape(0, 768).astype(np.float32), [])

            assert index.ntotal == 0
            assert len(index.chunk_ids) == 0

    def test_multiple_add_operations(self):
        """Test multiple add operations accumulate correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            rng = np.random.RandomState(42)

            # Add first batch
            emb1 = rng.randn(10, 768).astype(np.float32)
            ids1 = [f"chunk_{i}" for i in range(10)]
            index.add(emb1, ids1)

            assert index.ntotal == 10

            # Add second batch
            emb2 = rng.randn(5, 768).astype(np.float32)
            ids2 = [f"chunk_{i}" for i in range(10, 15)]
            index.add(emb2, ids2)

            assert index.ntotal == 15
            assert len(index.chunk_ids) == 15
            assert index.chunk_ids == ids1 + ids2


class TestFaissVectorIndexDimensionValidation:
    """Tests for dimension mismatch validation in add() and search()."""

    def test_add_dimension_mismatch_raises_error(self):
        """Test that adding embeddings with wrong dimension raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Try to add embeddings with wrong dimension (1024 instead of 768)
            rng = np.random.RandomState(42)
            wrong_dim_embeddings = rng.randn(5, 1024).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(5)]

            with pytest.raises(
                ValueError,
                match="Embedding dimension mismatch: embeddings have 1024d but index expects 768d",
            ):
                index.add(wrong_dim_embeddings, chunk_ids)

            # Verify index is unchanged
            assert index.ntotal == 0

    def test_search_dimension_mismatch_raises_error(self):
        """Test that searching with wrong dimension query raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add some vectors
            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]
            index.add(embeddings, chunk_ids)

            # Try to search with wrong dimension query (1024 instead of 768)
            wrong_dim_query = rng.randn(1024).astype(np.float32)

            with pytest.raises(
                ValueError,
                match="FATAL: Dimension mismatch between query \\(1024d\\) and index \\(768d\\)",
            ):
                index.search(wrong_dim_query, k=5)

    def test_add_correct_dimension_succeeds(self):
        """Test that adding embeddings with correct dimension succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add embeddings with correct dimension
            rng = np.random.RandomState(42)
            embeddings = rng.randn(5, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(5)]

            # Should succeed
            index.add(embeddings, chunk_ids)
            assert index.ntotal == 5

    def test_search_correct_dimension_succeeds(self):
        """Test that searching with correct dimension query succeeds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)
            index.create(768, "flat")

            # Add vectors
            rng = np.random.RandomState(42)
            embeddings = rng.randn(10, 768).astype(np.float32)
            chunk_ids = [f"chunk_{i}" for i in range(10)]
            index.add(embeddings, chunk_ids)

            # Search with correct dimension
            query = rng.randn(768).astype(np.float32)

            # Should succeed
            distances, indices = index.search(query, k=5)
            assert len(distances) == 5
            assert len(indices) == 5
