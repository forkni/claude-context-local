"""CodeIndexManager.search widens the FAISS window when a filter starves it.

Unfiltered searches make exactly one FAISS call at ``k*3`` (pinned by
``test_funnel_characterization.py``). With a metadata filter the first pass is
the same, then the window grows x4 up to ``FILTERED_SEARCH_CAP`` (or ntotal)
until ``k`` survivors are found, mirroring ``get_similar_chunks`` (ADR-0067).
"""

from unittest.mock import Mock

import numpy as np
import pytest

from embeddings.embedder import EmbeddingResult
from search import indexer as indexer_mod
from search.indexer import CodeIndexManager


DIM = 8
N = 200
RARE_EVERY = 25  # 8 "rare" chunks out of 200 carry chunk_type="class"


def _manager(tmp_path) -> tuple[CodeIndexManager, np.ndarray]:
    rng = np.random.RandomState(11)
    vectors = rng.randn(N, DIM).astype(np.float32)
    manager = CodeIndexManager(storage_dir=str(tmp_path / "ix"))
    manager.add_embeddings(
        [
            EmbeddingResult(
                embedding=vectors[i],
                chunk_id=f"f{i}.py:1-2:x:fn{i}",
                metadata={
                    "relative_path": f"pkg/f{i}.py",
                    "chunk_type": "class" if i % RARE_EVERY == 0 else "function",
                },
            )
            for i in range(N)
        ]
    )
    return manager, vectors


def _spy(manager: CodeIndexManager) -> Mock:
    real = manager._faiss_index.search
    spy = Mock(side_effect=real)
    manager._faiss_index.search = spy
    return spy


class TestFilteredWidening:
    def test_unfiltered_makes_one_call_at_k_times_3(self, tmp_path):
        manager, vectors = _manager(tmp_path)
        spy = _spy(manager)

        out = manager.search(vectors[0], k=5)

        assert len(out) == 5
        assert [c.args[1] for c in spy.call_args_list] == [15]
        manager.close()

    def test_filter_widens_until_k_survivors(self, tmp_path):
        manager, vectors = _manager(tmp_path)
        spy = _spy(manager)

        out = manager.search(vectors[1], k=5, filters={"chunk_type": "class"})

        # 8 rare chunks exist; k=5 of them must be found, which a fixed k*3=15
        # window over 200 vectors almost surely cannot deliver.
        assert len(out) == 5
        assert all(m["chunk_type"] == "class" for _, _, m in out)
        widths = [c.args[1] for c in spy.call_args_list]
        assert widths[0] == 15
        assert widths == sorted(widths) and len(widths) > 1
        assert all(w <= N for w in widths)
        scores = [s for _, s, _ in out]
        assert scores == sorted(scores, reverse=True)
        manager.close()

    def test_filter_satisfied_on_first_pass_does_not_widen(self, tmp_path):
        manager, vectors = _manager(tmp_path)
        spy = _spy(manager)

        out = manager.search(vectors[2], k=5, filters={"chunk_type": "function"})

        assert len(out) == 5
        assert [c.args[1] for c in spy.call_args_list] == [15]
        manager.close()

    def test_widening_stops_at_ntotal_when_fewer_than_k_match(self, tmp_path):
        manager, vectors = _manager(tmp_path)
        spy = _spy(manager)

        out = manager.search(vectors[3], k=20, filters={"chunk_type": "class"})

        assert len(out) == N // RARE_EVERY  # every rare chunk, no more exist
        assert spy.call_args_list[-1].args[1] == N
        manager.close()

    def test_widening_is_capped(self, tmp_path, monkeypatch):
        monkeypatch.setattr(indexer_mod, "FILTERED_SEARCH_CAP", 60)
        manager, vectors = _manager(tmp_path)
        spy = _spy(manager)

        out = manager.search(vectors[4], k=20, filters={"chunk_type": "class"})

        assert len(out) < 20
        widths = [c.args[1] for c in spy.call_args_list]
        assert widths[-1] == 60
        assert all(w <= 60 for w in widths)
        manager.close()

    def test_no_match_returns_empty(self, tmp_path):
        manager, vectors = _manager(tmp_path)

        assert manager.search(vectors[5], k=3, filters={"chunk_type": "module"}) == []
        manager.close()

    @pytest.mark.parametrize("k", [1, 7])
    def test_filtered_results_match_brute_force(self, tmp_path, k):
        manager, vectors = _manager(tmp_path)
        unit = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
        rare = [i for i in range(N) if i % RARE_EVERY == 0]
        q = 6
        expected = sorted(rare, key=lambda i: -float(unit[i] @ unit[q]))[:k]

        out = manager.search(vectors[q], k=k, filters={"chunk_type": "class"})

        got = [int(cid.split(":")[-1][2:]) for cid, _, _ in out]
        assert got == expected
        manager.close()
