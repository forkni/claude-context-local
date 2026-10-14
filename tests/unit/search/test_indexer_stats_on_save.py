"""save_index() refreshes stats.json, so a removal-only reindex reports live counts.

Hybrid mode saves the dense side through ``IndexSynchronizer`` ->
``CodeIndexManager.save_index()``. Before the fix only ``add_embeddings`` and
``save_indices`` rewrote ``stats.json``, so deleting a file left
``total_chunks``/``files_indexed`` at the pre-removal values until the next add.
"""

import json

import numpy as np

from embeddings.embedder import EmbeddingResult
from search.indexer import CodeIndexManager


DIM = 8


def _manager(tmp_path) -> CodeIndexManager:
    rng = np.random.RandomState(3)
    manager = CodeIndexManager(storage_dir=str(tmp_path / "ix"))
    manager.add_embeddings(
        [
            EmbeddingResult(
                embedding=rng.randn(DIM).astype(np.float32),
                chunk_id=f"{name}.py:{i}-{i + 1}:function:fn{i}",
                metadata={
                    "file_path": f"{name}.py",
                    "relative_path": f"{name}.py",
                    "chunk_type": "function",
                },
            )
            for name in ("keep", "gone")
            for i in range(3)
        ]
    )
    return manager


def _stats_on_disk(manager: CodeIndexManager) -> dict:
    return json.loads(manager.stats_path.read_text())


def test_save_index_after_removal_rewrites_stats(tmp_path):
    with _manager(tmp_path) as manager:
        assert _stats_on_disk(manager)["total_chunks"] == 6

        removed = manager.remove_files({"gone.py"})
        manager.save_index()
        live_chunk_count = len(manager.chunk_ids)

    assert removed == 3
    stats = _stats_on_disk(manager)
    assert stats["total_chunks"] == live_chunk_count == 3
    assert stats["index_size"] == 3
    assert stats["files_indexed"] == 1
