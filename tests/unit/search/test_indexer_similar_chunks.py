"""Unit tests for CodeIndexManager.get_similar_chunks.

Covers the caller-controlled ``exclude_same_file`` filter (2026-07-28,
evaluation/SIMILAR_DIVERSITY_20260728.md): the default path must stay
byte-identical (k+1 fetch, anchor filtered), while the exclusion path
overfetches k*3+1 and drops every candidate from the anchor's own file.
"""

from unittest.mock import Mock

import numpy as np

from search.indexer import CodeIndexManager


def _make_manager(tmp_path, ntotal: int, search_results):
    """CodeIndexManager with mocked metadata store, FAISS index, and search."""
    storage_dir = tmp_path / "index"
    storage_dir.mkdir()
    manager = CodeIndexManager(storage_dir=str(storage_dir))

    manager._metadata_store = Mock()
    manager._metadata_store.get.return_value = {
        "index_id": 0,
        "metadata": {"relative_path": "pkg/anchor.py"},
    }

    manager._faiss_index = Mock()
    manager._faiss_index.index = Mock()
    manager._faiss_index.index.ntotal = ntotal
    manager._faiss_index.reconstruct.return_value = np.zeros(768, dtype=np.float32)

    manager.search = Mock(return_value=search_results)
    return manager


ANCHOR = "pkg/anchor.py:1-10:function:anchor_func"

# 3 same-file neighbors + anchor itself + 3 cross-file candidates.
MIXED_RESULTS = [
    (
        "pkg/anchor.py:12-20:function:sibling_a",
        0.95,
        {"relative_path": "pkg/anchor.py"},
    ),
    (ANCHOR, 0.94, {"relative_path": "pkg/anchor.py"}),
    (
        "pkg/anchor.py:22-30:function:sibling_b",
        0.90,
        {"relative_path": "pkg/anchor.py"},
    ),
    ("pkg/other.py:1-10:function:analogue_a", 0.85, {"relative_path": "pkg/other.py"}),
    (
        "pkg/anchor.py:32-40:function:sibling_c",
        0.80,
        {"relative_path": "pkg/anchor.py"},
    ),
    ("pkg/third.py:1-10:function:analogue_b", 0.75, {"relative_path": "pkg/third.py"}),
    (
        "pkg/fourth.py:1-10:function:analogue_c",
        0.70,
        {"relative_path": "pkg/fourth.py"},
    ),
]


class TestGetSimilarChunksDefault:
    def test_default_fetches_k_plus_one(self, tmp_path):
        """Default path must keep the historical k+1 fetch depth."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)

        manager.get_similar_chunks(ANCHOR, k=3)

        manager.search.assert_called_once()
        assert manager.search.call_args[0][1] == 4

    def test_default_keeps_same_file_neighbors(self, tmp_path):
        """Default path filters only the anchor, never same-file neighbors."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)

        results = manager.get_similar_chunks(ANCHOR, k=3)

        chunk_ids = [cid for cid, _, _ in results]
        assert ANCHOR not in chunk_ids
        assert chunk_ids == [
            "pkg/anchor.py:12-20:function:sibling_a",
            "pkg/anchor.py:22-30:function:sibling_b",
            "pkg/other.py:1-10:function:analogue_a",
        ]


class TestGetSimilarChunksExcludeSameFile:
    def test_overfetches_three_x(self, tmp_path):
        """Exclusion path fetches k*3+1 (probe-validated depth)."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)

        manager.get_similar_chunks(ANCHOR, k=3, exclude_same_file=True)

        manager.search.assert_called_once()
        assert manager.search.call_args[0][1] == 10

    def test_overfetch_capped_at_ntotal(self, tmp_path):
        """search_k never exceeds the number of indexed vectors."""
        manager = _make_manager(tmp_path, ntotal=7, search_results=MIXED_RESULTS)

        manager.get_similar_chunks(ANCHOR, k=3, exclude_same_file=True)

        assert manager.search.call_args[0][1] == 7

    def test_filters_all_anchor_file_chunks(self, tmp_path):
        """Every candidate sharing the anchor's relative_path is dropped."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)

        results = manager.get_similar_chunks(ANCHOR, k=3, exclude_same_file=True)

        assert [cid for cid, _, _ in results] == [
            "pkg/other.py:1-10:function:analogue_a",
            "pkg/third.py:1-10:function:analogue_b",
            "pkg/fourth.py:1-10:function:analogue_c",
        ]
        assert all(meta["relative_path"] != "pkg/anchor.py" for _, _, meta in results)

    def test_short_return_when_few_cross_file_candidates(self, tmp_path):
        """Fewer than k cross-file candidates -> returns what exists."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)

        results = manager.get_similar_chunks(ANCHOR, k=5, exclude_same_file=True)

        assert len(results) == 3

    def test_truncates_to_k(self, tmp_path):
        """More cross-file candidates than k -> truncated to k."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)

        results = manager.get_similar_chunks(ANCHOR, k=2, exclude_same_file=True)

        assert [cid for cid, _, _ in results] == [
            "pkg/other.py:1-10:function:analogue_a",
            "pkg/third.py:1-10:function:analogue_b",
        ]

    def test_missing_metadata_entry_returns_empty(self, tmp_path):
        """Unknown anchor behaves the same on both paths."""
        manager = _make_manager(tmp_path, ntotal=100, search_results=MIXED_RESULTS)
        manager._metadata_store.get.return_value = None

        assert manager.get_similar_chunks(ANCHOR, k=3, exclude_same_file=True) == []
        manager.search.assert_not_called()
