"""CodeIndexManager.reconstruct_embeddings owns the chunk_id -> FAISS position lookup."""

from unittest.mock import Mock

import numpy as np

from search.indexer import CodeIndexManager


def _manager(tmp_path, chunk_ids, vectors):
    storage_dir = tmp_path / "index"
    storage_dir.mkdir()
    manager = CodeIndexManager(storage_dir=str(storage_dir))
    manager._faiss_index = Mock()
    manager._faiss_index.chunk_ids = chunk_ids
    manager._faiss_index.reconstruct.side_effect = lambda pos: vectors[pos]
    return manager


class TestReconstructEmbeddings:
    def test_returns_rows_and_stacked_matrix_in_input_order(self, tmp_path):
        vectors = [np.array([float(i), 0.0]) for i in range(3)]
        manager = _manager(tmp_path, ["a", "b", "c"], vectors)

        rows, matrix = manager.reconstruct_embeddings(["c", "a"])

        assert rows == [0, 1]
        assert matrix.shape == (2, 2)
        np.testing.assert_array_equal(matrix[0], vectors[2])
        np.testing.assert_array_equal(matrix[1], vectors[0])

    def test_skips_ids_absent_from_index(self, tmp_path):
        vectors = [np.array([1.0, 0.0])]
        manager = _manager(tmp_path, ["a"], vectors)

        rows, matrix = manager.reconstruct_embeddings(["x", "a", "y"])

        assert rows == [1]
        assert matrix.shape == (1, 2)

    def test_no_indexed_ids_returns_none_matrix(self, tmp_path):
        manager = _manager(tmp_path, ["a"], [np.zeros(2)])

        assert manager.reconstruct_embeddings(["x"]) == ([], None)
        assert manager.reconstruct_embeddings([]) == ([], None)
        manager._faiss_index.reconstruct.assert_not_called()

    def test_ntotal_is_zero_safe_without_index(self, tmp_path):
        manager = CodeIndexManager(storage_dir=str(tmp_path / "idx"))

        assert manager.ntotal == 0
