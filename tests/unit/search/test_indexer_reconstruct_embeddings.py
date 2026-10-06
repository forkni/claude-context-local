"""CodeIndexManager.reconstruct_embeddings owns the chunk_id -> FAISS position lookup."""

import numpy as np
import pytest

from search.indexer import CodeIndexManager


DIM = 8


def _manager(tmp_path, chunk_ids, vectors) -> CodeIndexManager:
    storage_dir = tmp_path / "index"
    storage_dir.mkdir()
    manager = CodeIndexManager(storage_dir=str(storage_dir))
    manager._faiss_index.create(DIM, "flat")
    manager._faiss_index.add(np.asarray(vectors, dtype=np.float32), list(chunk_ids))
    return manager


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def vectors():
    rng = np.random.RandomState(2)
    return rng.randn(3, DIM).astype(np.float32)


class TestReconstructEmbeddings:
    def test_returns_rows_and_stacked_matrix_in_input_order(self, tmp_path, vectors):
        manager = _manager(tmp_path, ["a", "b", "c"], vectors)

        rows, matrix = manager.reconstruct_embeddings(["c", "a"])

        assert rows == [0, 1]
        assert matrix.shape == (2, DIM)
        np.testing.assert_allclose(matrix[0], _unit(vectors[2]), atol=1e-6)
        np.testing.assert_allclose(matrix[1], _unit(vectors[0]), atol=1e-6)
        manager.close()

    def test_skips_ids_absent_from_index(self, tmp_path, vectors):
        manager = _manager(tmp_path, ["a"], vectors[:1])

        rows, matrix = manager.reconstruct_embeddings(["x", "a", "y"])

        assert rows == [1]
        assert matrix.shape == (1, DIM)
        manager.close()

    def test_duplicates_are_returned_per_input_row(self, tmp_path, vectors):
        manager = _manager(tmp_path, ["a", "b", "c"], vectors)

        rows, matrix = manager.reconstruct_embeddings(["b", "b"])

        assert rows == [0, 1]
        np.testing.assert_array_equal(matrix[0], matrix[1])
        manager.close()

    def test_no_indexed_ids_returns_none_matrix(self, tmp_path, vectors):
        manager = _manager(tmp_path, ["a"], vectors[:1])

        assert manager.reconstruct_embeddings(["x"]) == ([], None)
        assert manager.reconstruct_embeddings([]) == ([], None)
        manager.close()

    def test_lookup_reflects_later_additions(self, tmp_path, vectors):
        """The position cache must not go stale after the index grows."""
        manager = _manager(tmp_path, ["a", "b"], vectors[:2])
        assert manager.reconstruct_embeddings(["c"]) == ([], None)

        manager._faiss_index.add(vectors[2:3], ["c"])
        rows, matrix = manager.reconstruct_embeddings(["c"])

        assert rows == [0]
        np.testing.assert_allclose(matrix[0], _unit(vectors[2]), atol=1e-6)
        manager.close()

    def test_ntotal_is_zero_safe_without_index(self, tmp_path):
        manager = CodeIndexManager(storage_dir=str(tmp_path / "idx"))

        assert manager.ntotal == 0
