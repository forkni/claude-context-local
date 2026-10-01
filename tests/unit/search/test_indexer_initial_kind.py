"""A fresh index's flat/IVF kind follows the size of the single first batch."""

import numpy as np
import pytest

from embeddings.embedder import EmbeddingResult
from search import faiss_index
from search.indexer import CodeIndexManager


DIM = 8
LIMIT = 50


@pytest.fixture(autouse=True)
def _low_ivf_threshold(monkeypatch):
    monkeypatch.setattr(faiss_index, "IVF_MIN_VECTORS", LIMIT)


def _results(n: int) -> list[EmbeddingResult]:
    rng = np.random.RandomState(3)
    return [
        EmbeddingResult(
            embedding=rng.randn(DIM).astype(np.float32),
            chunk_id=f"f{i}.py:1-2:function:fn{i}",
            metadata={"relative_path": f"f{i}.py", "chunk_type": "function"},
        )
        for i in range(n)
    ]


def _kind(manager: CodeIndexManager) -> str:
    return type(manager._faiss_index.index).__name__


def test_single_large_batch_builds_ivf(tmp_path):
    manager = CodeIndexManager(storage_dir=str(tmp_path / "ix"))
    manager.add_embeddings(_results(LIMIT + 10))
    assert _kind(manager) == "IndexIVFFlat"


def test_single_small_batch_builds_flat(tmp_path):
    manager = CodeIndexManager(storage_dir=str(tmp_path / "ix"))
    manager.add_embeddings(_results(LIMIT - 10))
    assert _kind(manager) == "IndexFlatIP"


def test_kind_is_frozen_by_the_first_batch(tmp_path):
    """Documents why a force reindex must add everything in one call."""
    manager = CodeIndexManager(storage_dir=str(tmp_path / "ix"))
    first = _results(LIMIT - 10)
    manager.add_embeddings(first)
    rest = [
        EmbeddingResult(embedding=r.embedding, chunk_id=f"g{i}", metadata=r.metadata)
        for i, r in enumerate(_results(LIMIT))
    ]
    manager.add_embeddings(rest)
    assert manager.ntotal > LIMIT
    assert _kind(manager) == "IndexFlatIP"
