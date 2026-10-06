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
    ivf_nlist_for,
    ivf_nprobe_for,
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

            index.create(768, "ivf", expected_count=60_000)

            assert index.index is not None
            assert index.dimension == 768
            assert index.ntotal == 0
            assert index.index.nlist == ivf_nlist_for(60_000)
            assert index.index.nprobe == ivf_nprobe_for(index.index.nlist, 60_000)
            # IndexIVFFlat defaults to METRIC_L2 when the metric is omitted;
            # scores must be inner products like the flat index.
            import faiss

            assert index.index.metric_type == faiss.METRIC_INNER_PRODUCT
            assert index.describe()["metric"] == "ip"

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

    def test_save_without_index(self, caplog):
        """Test saving when no index exists logs warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test.index"
            index = FaissVectorIndex(index_path)

            with caplog.at_level("WARNING"):
                index.save()

            assert not index_path.exists()
            assert "No index to save" in caplog.text

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
        sys.platform != "win32", reason="only Windows has a share-mode to prove here"
    )
    def test_clear_no_longer_blocked_by_live_foreign_mapping(self):
        """A second instance's clear() must succeed even if nobody closes a
        foreign live mapping first.

        Supersedes the old (pre-share-delete) contract asserted by this test:
        this repo's recurring WinError-32 mmap-handle failure
        (docs/adr/0025-clear-index-directory-in-place.md) kept recurring
        because releasing *this* instance's own handle can never help when
        the blocking handle always belongs to a *different* instance --
        ``_check_auto_reindex`` (mcp_server/tools/search_handlers.py) built a
        second HybridSearcher/CodeIndexManager on a warm project without
        ever closing the first. The fix instead removes the OS precondition:
        ``MmapVectorStorage`` opens ``code_vectors.mmap`` with
        ``FILE_SHARE_DELETE`` on Windows, matching POSIX's always-unlinkable
        semantics, so a foreign live mapping no longer blocks ``clear()`` at
        all -- companion coverage in ``test_indexer_clear_index.py`` exercises
        the same shape one layer up, through ``CodeIndexManager``.
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

            # instance1 is deliberately never closed here -- clear() must
            # succeed anyway now, without needing to close a handle it does
            # not own.
            instance2.clear()

            assert instance2._mmap_storage is None
            assert not instance2._mmap_path.exists()

            # instance1's own mapping stays valid (reading the deleted
            # file's old bytes) until it is separately closed -- Windows
            # share-delete semantics, matching POSIX unlink-of-open-file.
            instance1.close()


class TestFaissVectorIndexIVFReconstruct:
    """reconstruct() on IVF indexes across the server's save/load lifecycle.

    Regression: ``save()`` at or above MMAP_THRESHOLD released this instance's
    mmap mapping (``close()``) and rewrote the file through a local
    ``MmapVectorStorage`` without re-attaching it. ``reconstruct()`` then fell
    through to FAISS ``reconstruct()``, which an ``IndexIVFFlat`` cannot serve
    without a direct map ("direct map not initialized") -- so multi-hop hop-2
    expansion failed on every IVF project after any in-process reindex, until
    the server restarted. Flat indexes were unaffected (no direct map needed).
    """

    DIM = 8
    N = 400  # ivf_nlist_for(400) == 10 centroids; plenty of training points

    @pytest.fixture(autouse=True)
    def _low_mmap_threshold(self, monkeypatch):
        """Keep the mmap path reachable with small, fast indexes."""
        from search import faiss_index

        monkeypatch.setattr(faiss_index, "MMAP_THRESHOLD", 100)

    def _embeddings(self) -> tuple[np.ndarray, list[str]]:
        rng = np.random.RandomState(7)
        return (
            rng.randn(self.N, self.DIM).astype(np.float32),
            [f"chunk_{i}" for i in range(self.N)],
        )

    def _assert_reconstructs(self, index: FaissVectorIndex, source: np.ndarray):
        """reconstruct() returns the L2-normalized stored vector at any position."""
        for pos in (0, self.N // 2, self.N - 1):
            expected = source[pos] / np.linalg.norm(source[pos])
            np.testing.assert_allclose(index.reconstruct(pos), expected, atol=1e-5)

    def test_reconstruct_after_fresh_ivf_save(self, tmp_path):
        """create -> add -> save -> reconstruct in the same process."""
        embeddings, chunk_ids = self._embeddings()
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "ivf", expected_count=self.N)
        index.add(embeddings, chunk_ids)
        index.save()

        self._assert_reconstructs(index, embeddings)
        index.close()

    def test_reconstruct_after_load_then_save(self, tmp_path):
        """The live server's lifecycle: load from disk, then a reindex saves."""
        embeddings, chunk_ids = self._embeddings()
        seed = FaissVectorIndex(tmp_path / "code.index")
        seed.create(self.DIM, "ivf", expected_count=self.N)
        seed.add(embeddings, chunk_ids)
        seed.save()
        seed.close()

        server = FaissVectorIndex(tmp_path / "code.index")
        assert server.load()
        self._assert_reconstructs(server, embeddings)

        server.save()  # auto-reindex / incremental reindex writes again

        self._assert_reconstructs(server, embeddings)
        server.close()

    def test_save_reattaches_mmap_storage(self, tmp_path):
        """After an at-or-above-threshold save the instance maps its own file."""
        embeddings, chunk_ids = self._embeddings()
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "flat")
        index.add(embeddings, chunk_ids)
        index.save()

        assert index._mmap_storage is not None
        assert index._mmap_storage.is_loaded
        assert index._mmap_storage.count == index.ntotal
        index.close()

    def test_ivf_reconstruct_without_mmap_uses_direct_map(self, tmp_path, monkeypatch):
        """With no mmap (below threshold), IVF still reconstructs via FAISS."""
        from search import faiss_index

        monkeypatch.setattr(faiss_index, "MMAP_THRESHOLD", 10**9)  # no mmap at all
        embeddings, chunk_ids = self._embeddings()
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "ivf", expected_count=self.N)
        index.add(embeddings, chunk_ids)
        index.save()
        assert index._mmap_storage is None

        self._assert_reconstructs(index, embeddings)

        reloaded = FaissVectorIndex(tmp_path / "code.index")
        assert reloaded.load()
        assert reloaded._mmap_storage is None
        self._assert_reconstructs(reloaded, embeddings)

    def test_load_sets_ivf_nprobe(self, tmp_path):
        """Indexes persisted with nprobe=1 must be searched wider after load()."""
        import faiss

        from search import faiss_index

        embeddings, chunk_ids = self._embeddings()
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "ivf", expected_count=self.N)
        index.add(embeddings, chunk_ids)
        index.save()
        index.close()

        reloaded = FaissVectorIndex(tmp_path / "code.index")
        assert reloaded.load()

        ivf = faiss.try_extract_index_ivf(reloaded.index)
        assert ivf is not None
        assert ivf.nprobe == faiss_index.ivf_nprobe_for(ivf.nlist, self.N)
        reloaded.close()


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


class TestFaissVectorIndexRemovePositions:
    """remove_positions() rebuilds the index without the dropped vectors."""

    DIM = 8

    def _built(self, tmp_path, n: int = 6) -> tuple[FaissVectorIndex, np.ndarray]:
        rng = np.random.RandomState(3)
        embeddings = rng.randn(n, self.DIM).astype(np.float32)
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "flat")
        index.add(embeddings, [f"chunk_{i}" for i in range(n)])
        return index, embeddings

    def test_partial_removal_keeps_vectors_and_order(self, tmp_path):
        index, embeddings = self._built(tmp_path)

        assert index.remove_positions({1, 4}) is True

        assert index.chunk_ids == ["chunk_0", "chunk_2", "chunk_3", "chunk_5"]
        assert index.ntotal == 4
        assert type(index.index).__name__ == "IndexFlatIP"
        for new_pos, old_pos in enumerate((0, 2, 3, 5)):
            expected = embeddings[old_pos] / np.linalg.norm(embeddings[old_pos])
            np.testing.assert_allclose(index.reconstruct(new_pos), expected, atol=1e-5)
        index.close()

    def test_removing_everything_returns_false_and_leaves_index(self, tmp_path):
        index, _ = self._built(tmp_path, n=3)

        assert index.remove_positions({0, 1, 2}) is False

        assert index.ntotal == 3
        assert len(index.chunk_ids) == 3
        index.close()

    def test_reconstruct_failure_raises_and_leaves_index(self, tmp_path, monkeypatch):
        """BatchOperations renumbers survivors assuming none were skipped, so a
        reconstruction failure must abort the rebuild, not drop vectors."""
        index, _ = self._built(tmp_path, n=3)

        def boom(*_args):
            raise RuntimeError("boom")

        monkeypatch.setattr(index.index, "reconstruct_n", boom)

        with pytest.raises(RuntimeError, match="boom"):
            index.remove_positions({0})

        assert index.ntotal == 3
        assert len(index.chunk_ids) == 3
        index.close()

    def test_id_list_index_size_mismatch_raises(self, tmp_path):
        index, _ = self._built(tmp_path, n=3)
        index._chunk_ids.append("ghost")

        with pytest.raises(RuntimeError, match="size mismatch"):
            index.remove_positions({0})

        assert index.ntotal == 3
        index.close()

    def test_out_of_range_positions_are_ignored(self, tmp_path):
        index, _ = self._built(tmp_path, n=3)

        assert index.remove_positions({1, 7, -2}) is True

        assert index.chunk_ids == ["chunk_0", "chunk_2"]
        index.close()

    def test_bulk_rebuild_matches_per_vector_reconstruct(self, tmp_path):
        """Vectors kept by the reconstruct_n + mask path equal reconstruct(pos)."""
        index, _ = self._built(tmp_path, n=8)
        before = {pos: index.reconstruct(pos) for pos in (0, 3, 5, 7)}

        assert index.remove_positions({1, 2, 4, 6}) is True

        # add() re-normalizes on re-add, so allow float32 rounding (1 ulp).
        for new_pos, old_pos in enumerate((0, 3, 5, 7)):
            np.testing.assert_allclose(
                index.reconstruct(new_pos), before[old_pos], atol=1e-6
            )
        index.close()

    def test_gpu_placement_is_restored(self, tmp_path, monkeypatch):
        index, _ = self._built(tmp_path)
        moves = []
        monkeypatch.setattr(index, "move_to_gpu", lambda: moves.append(True) or True)
        index._on_gpu = True

        assert index.remove_positions({0}) is True

        # create() also calls move_to_gpu(); the restore is the extra call.
        assert len(moves) == 2
        index.close()


class TestIndexKindFollowsSize:
    """The flat/IVF decision has one owner and is re-made at every rebuild."""

    DIM = 8
    LIMIT = 50  # monkeypatched IVF_MIN_VECTORS so tests stay small and fast

    @pytest.fixture(autouse=True)
    def _low_ivf_threshold(self, monkeypatch):
        from search import faiss_index

        monkeypatch.setattr(faiss_index, "IVF_MIN_VECTORS", self.LIMIT)

    def _built(self, tmp_path, n: int, kind: str) -> FaissVectorIndex:
        rng = np.random.RandomState(5)
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, kind, expected_count=n)
        index.add(
            rng.randn(n, self.DIM).astype(np.float32), [f"chunk_{i}" for i in range(n)]
        )
        return index

    def test_index_kind_for_boundary(self):
        from search.faiss_index import index_kind_for

        assert index_kind_for(self.LIMIT) == "flat"
        assert index_kind_for(self.LIMIT + 1) == "ivf"

    def test_default_threshold_is_fifty_thousand(self, monkeypatch):
        from search import faiss_index

        monkeypatch.undo()
        assert faiss_index.IVF_MIN_VECTORS == 50_000
        assert faiss_index.index_kind_for(50_000) == "flat"
        assert faiss_index.index_kind_for(50_001) == "ivf"

    def test_rebuild_keeps_ivf_when_still_large(self, tmp_path):
        index = self._built(tmp_path, 200, "ivf")

        assert index.remove_positions({0, 1, 2})

        assert type(index.index).__name__ == "IndexIVFFlat"
        assert index.ntotal == 197
        assert index.index.nlist == ivf_nlist_for(197)
        assert index.index.nprobe == ivf_nprobe_for(index.index.nlist, 197)
        index.reconstruct(0)  # direct map present after the rebuild
        index.close()

    def test_rebuild_promotes_grown_flat_index_to_ivf(self, tmp_path):
        index = self._built(tmp_path, 200, "flat")

        assert index.remove_positions({0})

        assert type(index.index).__name__ == "IndexIVFFlat"
        assert index.ntotal == 199
        index.close()

    def test_rebuild_demotes_ivf_that_shrank_below_threshold(self, tmp_path):
        index = self._built(tmp_path, 200, "ivf")

        assert index.remove_positions(set(range(0, 160)))

        assert type(index.index).__name__ == "IndexFlatIP"
        assert index.ntotal == 40
        index.close()


class TestFaissVectorIndexDescribe:
    """describe() reports the live kind and IVF search parameters."""

    DIM = 8

    def _index(self, tmp_path, kind: str, n: int = 200) -> FaissVectorIndex:
        rng = np.random.RandomState(9)
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, kind, expected_count=n)
        index.add(
            rng.randn(n, self.DIM).astype(np.float32), [f"c{i}" for i in range(n)]
        )
        return index

    def test_no_index(self, tmp_path):
        assert FaissVectorIndex(tmp_path / "code.index").describe() == {
            "index_kind": None
        }

    def test_flat(self, tmp_path):
        assert self._index(tmp_path, "flat").describe() == {
            "index_kind": "flat",
            "metric": "ip",
        }

    def test_ivf_reports_nlist_and_nprobe(self, tmp_path):
        info = self._index(tmp_path, "ivf").describe()

        assert info["index_kind"] == "ivf"
        assert info["ivf_nlist"] == ivf_nlist_for(200) == 5  # 200 // 39
        assert info["ivf_nprobe"] == ivf_nprobe_for(5, 200) == 5


class TestFaissVectorIndexMetric:
    """IVF scores are inner products (same convention as the flat index)."""

    DIM = 8
    N = 400

    def _vectors(self) -> tuple[np.ndarray, list[str]]:
        rng = np.random.RandomState(11)
        return (
            rng.randn(self.N, self.DIM).astype(np.float32),
            [f"c{i}" for i in range(self.N)],
        )

    def test_ivf_scores_match_flat_ip(self, tmp_path):
        import faiss

        vectors, ids = self._vectors()
        flat = FaissVectorIndex(tmp_path / "flat" / "code.index")
        flat.index_path.parent.mkdir()
        flat.create(self.DIM, "flat")
        flat.add(vectors, ids)
        ivf = FaissVectorIndex(tmp_path / "ivf" / "code.index")
        ivf.index_path.parent.mkdir()
        ivf.create(self.DIM, "ivf", expected_count=self.N)
        ivf.add(vectors, ids)
        faiss.try_extract_index_ivf(ivf.index).nprobe = ivf.index.nlist  # exhaustive

        query = vectors[5]
        flat_scores, flat_ids = flat.search(query, 10)
        ivf_scores, ivf_ids = ivf.search(query, 10)

        np.testing.assert_array_equal(flat_ids, ivf_ids)
        np.testing.assert_allclose(flat_scores, ivf_scores, atol=1e-5)
        assert ivf_scores[0] == pytest.approx(1.0, abs=1e-5)  # self-match is IP 1
        assert np.all(np.diff(ivf_scores) <= 1e-6)  # descending = larger-is-better
        flat.close()
        ivf.close()

    def test_legacy_l2_ivf_shim(self, tmp_path, caplog):
        """An on-disk IVF built with METRIC_L2 (pre-fix) loads, warns once, and
        returns inner-product scores converted from its squared L2 distances."""
        import pickle

        import faiss

        vectors, ids = self._vectors()
        unit = vectors.copy()
        faiss.normalize_L2(unit)
        legacy = faiss.IndexIVFFlat(faiss.IndexFlatIP(self.DIM), self.DIM, 10)
        assert legacy.metric_type == faiss.METRIC_L2
        legacy.train(unit)
        legacy.add(unit)
        faiss.write_index(legacy, str(tmp_path / "code.index"))
        with open(tmp_path / "chunk_ids.pkl", "wb") as f:
            pickle.dump(ids, f)

        index = FaissVectorIndex(tmp_path / "code.index")
        with caplog.at_level("WARNING", logger="search.faiss_index"):
            assert index.load()
        warnings = [r for r in caplog.records if "Legacy L2-metric" in r.message]
        assert len(warnings) == 1
        assert index.describe()["metric"] == "l2"

        faiss.try_extract_index_ivf(index.index).nprobe = 10
        scores, found = index.search(vectors[3], 5)

        assert found[0] == 3
        assert scores[0] == pytest.approx(1.0, abs=1e-5)
        expected = unit[found] @ unit[3]
        np.testing.assert_allclose(scores, expected, atol=1e-5)
        assert np.all(np.diff(scores) <= 1e-6)

        # Batched path converts too, and -1 padding maps to the IP floor.
        batch_scores, batch_ids = index.search(vectors[:2], 5)
        assert batch_scores.shape == (2, 5)
        assert batch_scores[0, 0] == pytest.approx(1.0, abs=1e-5)
        index.close()

    def test_fresh_ivf_is_not_flagged_legacy(self, tmp_path):
        vectors, ids = self._vectors()
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "ivf", expected_count=self.N)
        index.add(vectors, ids)
        index.save()
        index.close()

        reloaded = FaissVectorIndex(tmp_path / "code.index")
        assert reloaded.load()
        assert reloaded._legacy_l2 is False
        assert reloaded.describe()["metric"] == "ip"
        reloaded.close()


class TestFaissVectorIndexPositionLookup:
    """position_of() / reconstruct_batch() replace per-row lookups and reconstructs."""

    DIM = 8

    def _built(self, tmp_path, n: int = 6, kind: str = "flat") -> FaissVectorIndex:
        rng = np.random.RandomState(5)
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, kind, expected_count=n)
        index.add(
            rng.randn(n, self.DIM).astype(np.float32), [f"c{i}" for i in range(n)]
        )
        return index

    def test_position_of_known_and_unknown(self, tmp_path):
        index = self._built(tmp_path)

        assert index.position_of("c0") == 0
        assert index.position_of("c5") == 5
        assert index.position_of("nope") is None
        index.close()

    def test_position_cache_invalidated_by_add_and_clear(self, tmp_path):
        index = self._built(tmp_path)
        assert index.position_of("c5") == 5  # builds the cache

        index.add(np.ones((1, self.DIM), dtype=np.float32), ["extra"])
        assert index.position_of("extra") == 6

        index.clear()
        assert index.position_of("c0") is None
        index.close()

    def test_position_cache_invalidated_by_remove_positions(self, tmp_path):
        index = self._built(tmp_path)
        assert index.position_of("c3") == 3

        assert index.remove_positions({1}) is True

        assert index.position_of("c1") is None
        assert index.position_of("c3") == 2
        index.close()

    def test_reconstruct_batch_matches_reconstruct(self, tmp_path):
        index = self._built(tmp_path)

        matrix = index.reconstruct_batch([4, 0, 2])

        assert matrix.shape == (3, self.DIM)
        assert matrix.dtype == np.float32
        for row, pos in zip(matrix, (4, 0, 2), strict=True):
            np.testing.assert_array_equal(row, index.reconstruct(pos))
        index.close()

    def test_reconstruct_batch_empty(self, tmp_path):
        index = self._built(tmp_path)

        assert index.reconstruct_batch([]).shape == (0, self.DIM)
        index.close()

    def test_reconstruct_batch_ivf_uses_direct_map(self, tmp_path):
        index = self._built(tmp_path, n=400, kind="ivf")

        matrix = index.reconstruct_batch(np.array([399, 7]))

        np.testing.assert_array_equal(matrix[0], index.reconstruct(399))
        np.testing.assert_array_equal(matrix[1], index.reconstruct(7))
        index.close()

    def test_reconstruct_batch_prefers_mmap(self, tmp_path, monkeypatch):
        from search import faiss_index

        monkeypatch.setattr(faiss_index, "MMAP_THRESHOLD", 1)
        index = self._built(tmp_path)
        index.save()
        assert index._mmap_storage is not None and index._mmap_storage.is_loaded

        def boom(*_args):
            raise AssertionError("FAISS reconstruct_batch should not be used")

        monkeypatch.setattr(index.index, "reconstruct_batch", boom)
        matrix = index.reconstruct_batch([1, 3])

        np.testing.assert_array_equal(matrix[0], index.reconstruct(1))
        np.testing.assert_array_equal(matrix[1], index.reconstruct(3))
        index.close()


class TestIvfPolicy:
    """ADR-0083: nlist/nprobe follow the vector count, never a fixed value."""

    DIM = 8

    @pytest.mark.parametrize(
        ("n", "nlist"),
        [
            (1, 1),  # never zero lists
            (200, 5),  # 200 // 39 training cap wins over round(4 * sqrt(200)) == 57
            (400, 10),
            (17_197, 440),  # the measured 17K real corpus: 4 * sqrt(N)
            (50_001, 894),
            (100_000, 1265),
        ],
    )
    def test_nlist_rule(self, n, nlist):
        assert ivf_nlist_for(n) == nlist

    def test_nlist_never_exceeds_training_cap(self):
        from search.faiss_index import IVF_MIN_TRAIN_PER_CENTROID

        for n in (39, 100, 1_000, 10_000, 50_001, 1_000_000):
            assert ivf_nlist_for(n) * IVF_MIN_TRAIN_PER_CENTROID <= max(
                n, IVF_MIN_TRAIN_PER_CENTROID
            )

    @pytest.mark.parametrize(
        ("nlist", "n", "nprobe"),
        [
            (894, 50_001, 447),  # half the lists
            (100, 21_910, 50),  # legacy on-disk nlist=100 gets re-probed at load
            (10, 400, 10),  # 420 * 10 / 400 > 10 -> capped at nlist
            (5, 200, 5),
            (1, 1, 1),
        ],
    )
    def test_nprobe_rule(self, nlist, n, nprobe):
        assert ivf_nprobe_for(nlist, n) == nprobe

    def test_nprobe_can_visit_leg_depth_ceiling(self):
        from search.faiss_index import IVF_MIN_VISITED

        for n in (50_001, 75_000, 100_000, 500_000):
            nlist = ivf_nlist_for(n)
            nprobe = ivf_nprobe_for(nlist, n)
            assert nprobe * n / nlist >= IVF_MIN_VISITED

    def test_create_ivf_requires_expected_count(self, tmp_path):
        index = FaissVectorIndex(tmp_path / "code.index")

        with pytest.raises(ValueError, match="expected_count"):
            index.create(self.DIM, "ivf")

    def test_flat_ignores_expected_count(self, tmp_path):
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "flat")
        index.create(self.DIM, "flat", expected_count=10)
        assert type(index.index).__name__ == "IndexFlatIP"

    def test_load_reapplies_nprobe_from_ntotal(self, tmp_path):
        """A persisted nprobe is ignored; the policy is re-derived from ntotal."""
        import faiss

        rng = np.random.RandomState(2)
        n = 400
        index = FaissVectorIndex(tmp_path / "code.index")
        index.create(self.DIM, "ivf", expected_count=n)
        index.add(
            rng.randn(n, self.DIM).astype(np.float32), [f"c{i}" for i in range(n)]
        )
        faiss.try_extract_index_ivf(index.index).nprobe = 1  # stale on-disk value
        index.save()
        index.close()

        reloaded = FaissVectorIndex(tmp_path / "code.index")
        assert reloaded.load()
        ivf = faiss.try_extract_index_ivf(reloaded.index)
        assert ivf.nprobe == ivf_nprobe_for(ivf.nlist, n)
        reloaded.close()
