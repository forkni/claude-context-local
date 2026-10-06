"""get_similar_chunks_batched goes through the FaissVectorIndex wrapper.

The wrapper owns query normalization and the legacy-metric score conversion,
so the batched path must not call the raw FAISS index. It also returns 1D
arrays for a single query, which the batched path has to lift back to 2D.
"""

import numpy as np
import pytest

from embeddings.embedder import EmbeddingResult
from search.indexer import CodeIndexManager


DIM = 8
N = 6


def _manager(tmp_path) -> tuple[CodeIndexManager, np.ndarray]:
    rng = np.random.RandomState(4)
    vectors = rng.randn(N, DIM).astype(np.float32)
    manager = CodeIndexManager(storage_dir=str(tmp_path / "ix"))
    manager.add_embeddings(
        [
            EmbeddingResult(
                embedding=vectors[i],
                chunk_id=f"f{i}.py:1-2:function:fn{i}",
                metadata={"relative_path": f"f{i}.py", "chunk_type": "function"},
            )
            for i in range(N)
        ]
    )
    return manager, vectors


def _cid(i: int) -> str:
    return f"f{i}.py:1-2:function:fn{i}"


class TestGetSimilarChunksBatchedWrapper:
    def test_single_query_returns_neighbors(self, tmp_path):
        manager, vectors = _manager(tmp_path)

        out = manager.get_similar_chunks_batched([_cid(0)], k=3)

        assert list(out) == [_cid(0)]
        neighbors = out[_cid(0)]
        assert len(neighbors) == 3
        assert all(cid != _cid(0) for cid, _, _ in neighbors)
        scores = [s for _, s, _ in neighbors]
        assert scores == sorted(scores, reverse=True)
        manager.close()

    def test_batched_scores_are_inner_products(self, tmp_path):
        manager, vectors = _manager(tmp_path)
        unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

        out = manager.get_similar_chunks_batched([_cid(1), _cid(4)], k=2)

        for anchor in (1, 4):
            for cid, score, _ in out[_cid(anchor)]:
                other = int(cid.split(".py")[0][1:])
                assert score == pytest.approx(
                    float(unit[anchor] @ unit[other]), abs=1e-5
                )
        manager.close()

    def test_uses_wrapper_search_not_raw_index(self, tmp_path, monkeypatch):
        manager, _ = _manager(tmp_path)
        calls = []
        wrapped = manager._faiss_index.search

        def spy(query, k):
            calls.append((query.shape, k))
            return wrapped(query, k)

        monkeypatch.setattr(manager._faiss_index, "search", spy)
        manager.get_similar_chunks_batched([_cid(2), _cid(3)], k=2)

        assert calls == [((2, DIM), 3)]
        manager.close()

    def test_unknown_ids_get_empty_lists(self, tmp_path):
        manager, _ = _manager(tmp_path)

        out = manager.get_similar_chunks_batched(["nope", _cid(0)], k=2)

        assert out["nope"] == []
        assert len(out[_cid(0)]) == 2
        manager.close()
