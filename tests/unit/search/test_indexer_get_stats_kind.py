"""get_stats() reports the live index kind and metric (index-kind lifecycle)."""

import numpy as np

from search.indexer import CodeIndexManager


def _manager(tmp_path) -> CodeIndexManager:
    storage_dir = tmp_path / "index"
    storage_dir.mkdir()
    return CodeIndexManager(storage_dir=str(storage_dir))


def _load_vectors(manager: CodeIndexManager, n: int = 200) -> None:
    rng = np.random.RandomState(1)
    manager._faiss_index.create(8)
    manager._faiss_index.add(
        rng.randn(n, 8).astype(np.float32), [f"c{i}" for i in range(n)]
    )


def test_get_stats_without_loaded_index_has_no_kind(tmp_path):
    assert "index_kind" not in _manager(tmp_path).get_stats()


def test_get_stats_reports_flat(tmp_path):
    manager = _manager(tmp_path)
    _load_vectors(manager)

    stats = manager.get_stats()

    assert stats["index_kind"] == "flat"
    assert stats["metric"] == "ip"
