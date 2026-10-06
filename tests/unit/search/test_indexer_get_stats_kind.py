"""get_stats() reports the live index kind and IVF parameters (index-kind lifecycle)."""

import numpy as np

from search.indexer import CodeIndexManager


def _manager(tmp_path) -> CodeIndexManager:
    storage_dir = tmp_path / "index"
    storage_dir.mkdir()
    return CodeIndexManager(storage_dir=str(storage_dir))


def _load_vectors(manager: CodeIndexManager, kind: str, n: int = 200) -> None:
    rng = np.random.RandomState(1)
    manager._faiss_index.create(8, kind, expected_count=n)
    manager._faiss_index.add(
        rng.randn(n, 8).astype(np.float32), [f"c{i}" for i in range(n)]
    )


def test_get_stats_without_loaded_index_has_no_kind(tmp_path):
    assert "index_kind" not in _manager(tmp_path).get_stats()


def test_get_stats_overlays_live_ivf_parameters(tmp_path):
    manager = _manager(tmp_path)
    _load_vectors(manager, "ivf")

    stats = manager.get_stats()

    assert stats["index_kind"] == "ivf"
    assert stats["ivf_nlist"] == 5  # ivf_nlist_for(200): 200 // 39
    assert stats["ivf_nprobe"] == 5  # ivf_nprobe_for(5, 200): capped at nlist


def test_get_stats_reports_flat(tmp_path):
    manager = _manager(tmp_path)
    _load_vectors(manager, "flat")

    assert manager.get_stats()["index_kind"] == "flat"
