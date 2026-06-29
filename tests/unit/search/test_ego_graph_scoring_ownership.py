"""Completeness gate: ego-graph neighbor scoring lives in EgoGraphRetriever.

If this test fails you have either:
- Moved score_neighbors out of search/ego_graph_retriever.py, OR
- Left FAISS-reconstruct / cosine-scoring logic in search/hybrid_searcher.py.

Fix: ego-graph neighbor scoring must live in EgoGraphRetriever.score_neighbors;
hybrid_searcher._apply_ego_graph_expansion is the thin delegating wrapper.
"""

import ast
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Ownership gate
# ---------------------------------------------------------------------------


class TestEgoGraphScoringOwnership:
    """Completeness gate: scoring loop lives in EgoGraphRetriever, not HybridSearcher."""

    def _ast_names_in_file(self, path: str) -> set[str]:
        """Return all Name and Attribute node ids in a Python file."""
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            return set()
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        return names

    def test_score_neighbors_defined_in_retriever(self):
        """EgoGraphRetriever.score_neighbors must be defined in ego_graph_retriever.py."""
        tree = ast.parse(
            Path("search/ego_graph_retriever.py").read_text(encoding="utf-8")
        )
        methods: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "EgoGraphRetriever":
                for item in ast.walk(node):
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(item.name)
        assert "score_neighbors" in methods, (
            "EgoGraphRetriever.score_neighbors not found in search/ego_graph_retriever.py. "
            "Scoring must live in the retriever, not the orchestrator."
        )

    def test_faiss_reconstruct_not_in_hybrid_searcher(self):
        """hybrid_searcher.py must not reference _faiss_index.reconstruct (scoring leak)."""
        names = self._ast_names_in_file("search/hybrid_searcher.py")
        assert "reconstruct" not in names, (
            "search/hybrid_searcher.py still references 'reconstruct' — the FAISS "
            "reconstruction scoring loop must live in EgoGraphRetriever.score_neighbors."
        )

    def test_dense_index_chunk_ids_not_accessed_in_apply_expansion(self):
        """_apply_ego_graph_expansion must not iterate self.dense_index.chunk_ids."""
        tree = ast.parse(Path("search/hybrid_searcher.py").read_text(encoding="utf-8"))
        violations: list[str] = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == "_apply_ego_graph_expansion"
            ):
                continue
            # Walk inside the method body
            for child in ast.walk(node):
                if (
                    isinstance(child, ast.Attribute)
                    and child.attr == "chunk_ids"
                    and isinstance(child.value, ast.Attribute)
                    and child.value.attr == "dense_index"
                ):
                    violations.append(f"line {child.col_offset}")
        assert not violations, (
            "dense_index.chunk_ids accessed inside _apply_ego_graph_expansion: "
            f"{violations}. This belongs in EgoGraphRetriever.score_neighbors."
        )


# ---------------------------------------------------------------------------
# Unit tests for EgoGraphRetriever.score_neighbors
# ---------------------------------------------------------------------------


def _make_search_result(chunk_id: str, score: float):
    """Create a minimal SearchResult-like object."""
    from search.reranker import SearchResult

    return SearchResult(chunk_id=chunk_id, score=score, metadata={}, source="semantic")


def _make_dense_index(
    chunk_ids: list[str], embeddings: dict[str, np.ndarray] | None = None
):
    """Build a fake dense_index with chunk_ids, get_chunk_by_id, and _faiss_index."""
    mock = MagicMock()
    mock.chunk_ids = chunk_ids

    def _get_chunk_by_id(cid):
        return {"chunk_id": cid, "name": cid.split(":")[-1], "relative_path": "f.py"}

    mock.get_chunk_by_id.side_effect = _get_chunk_by_id

    if embeddings:
        # Real ndarray reconstruction
        def _reconstruct(idx):
            cid = chunk_ids[idx]
            return embeddings.get(cid, np.zeros(4, dtype=np.float32))

        mock._faiss_index.reconstruct.side_effect = _reconstruct
    else:
        # Reconstruction raises to test decay fallback
        mock._faiss_index.reconstruct.side_effect = AttributeError("no faiss")

    return mock


class TestScoreNeighborsDecayFallback:
    """Tests for EgoGraphRetriever.score_neighbors — decay path."""

    def _retriever(self):
        from search.ego_graph_retriever import EgoGraphRetriever

        graph = MagicMock()
        graph.get_neighbors.return_value = []
        graph.load_community_map.return_value = {}
        return EgoGraphRetriever(graph)

    def _config(self, threshold: float = 0.0):
        from search.config import EgoGraphConfig

        cfg = EgoGraphConfig()
        cfg.min_similarity_threshold = threshold
        return cfg

    def test_decay_fallback_when_embed_fails(self):
        """When embedder.embed_query raises, all neighbors get anchor_score * 0.5."""
        retriever = self._retriever()

        anchor = _make_search_result("f.py:1-10:function:foo", 0.8)
        neighbor_id = "f.py:11-20:function:bar"
        ego_graphs = {"f.py:1-10:function:foo": [neighbor_id]}
        expanded = ["f.py:1-10:function:foo", neighbor_id]

        embedder = MagicMock()
        embedder.embed_query.side_effect = RuntimeError("no GPU")
        dense_index = _make_dense_index(["f.py:1-10:function:foo", neighbor_id])

        results = retriever.score_neighbors(
            [anchor],
            ego_graphs,
            expanded,
            "query",
            self._config(),
            dense_index=dense_index,
            embedder=embedder,
        )

        assert len(results) == 1
        r = results[0]
        assert r.chunk_id == neighbor_id
        assert r.score == pytest.approx(0.8 * 0.5)  # anchor_score * 0.5 decay
        assert r.source == "ego_graph"

    def test_no_neighbors_returns_empty(self):
        """When ego_graphs has no neighbors, result is empty."""
        retriever = self._retriever()
        anchor = _make_search_result("f.py:1-10:function:foo", 0.9)
        ego_graphs: dict[str, list[str]] = {}
        expanded: list[str] = ["f.py:1-10:function:foo"]

        embedder = MagicMock()
        dense_index = _make_dense_index(["f.py:1-10:function:foo"])

        results = retriever.score_neighbors(
            [anchor],
            ego_graphs,
            expanded,
            "q",
            self._config(),
            dense_index=dense_index,
            embedder=embedder,
        )
        assert results == []

    def test_threshold_filters_low_similarity_neighbors(self):
        """Neighbors below min_similarity_threshold are excluded."""
        retriever = self._retriever()

        anchor = _make_search_result("a.py:1-5:function:a", 1.0)
        neighbor_id = "b.py:1-5:function:b"
        ego_graphs = {"a.py:1-5:function:a": [neighbor_id]}
        expanded = ["a.py:1-5:function:a", neighbor_id]

        # Query embedding and neighbor embedding — very low similarity
        query_emb = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
        neighbor_emb = np.array(
            [0.0, 1.0, 0.0, 0.0], dtype=np.float32
        )  # orthogonal → sim=0

        embedder = MagicMock()
        embedder.embed_query.return_value = query_emb
        dense_index = _make_dense_index(
            ["a.py:1-5:function:a", neighbor_id],
            embeddings={neighbor_id: neighbor_emb},
        )

        # threshold=0.5 should exclude the orthogonal neighbor
        results = retriever.score_neighbors(
            [anchor],
            ego_graphs,
            expanded,
            "query",
            self._config(threshold=0.5),
            dense_index=dense_index,
            embedder=embedder,
        )
        assert results == [], f"Expected empty (sim=0 < 0.5), got {results}"

    def test_cosine_similarity_scoring(self):
        """Neighbor score = anchor_score * cosine_similarity when embedding succeeds."""
        retriever = self._retriever()

        anchor = _make_search_result("a.py:1-5:function:a", 1.0)
        neighbor_id = "b.py:1-5:function:b"
        ego_graphs = {"a.py:1-5:function:a": [neighbor_id]}
        expanded = ["a.py:1-5:function:a", neighbor_id]

        # Identical unit vectors → cosine_sim = 1.0
        vec = np.array([1.0, 0.0], dtype=np.float32)
        embedder = MagicMock()
        embedder.embed_query.return_value = vec
        dense_index = _make_dense_index(
            ["a.py:1-5:function:a", neighbor_id],
            embeddings={neighbor_id: vec},
        )

        results = retriever.score_neighbors(
            [anchor],
            ego_graphs,
            expanded,
            "q",
            self._config(threshold=0.0),
            dense_index=dense_index,
            embedder=embedder,
        )
        assert len(results) == 1
        # anchor_score=1.0, similarity=1.0 → score=1.0
        assert results[0].score == pytest.approx(1.0)

    def test_anchor_not_included_in_results(self):
        """Anchors must not appear in score_neighbors output."""
        retriever = self._retriever()

        anchor_id = "a.py:1-5:function:a"
        anchor = _make_search_result(anchor_id, 0.9)
        ego_graphs = {"a.py:1-5:function:a": ["b.py:1-5:function:b"]}
        expanded = [anchor_id, "b.py:1-5:function:b"]

        embedder = MagicMock()
        embedder.embed_query.side_effect = RuntimeError("skip")
        dense_index = _make_dense_index([anchor_id, "b.py:1-5:function:b"])

        results = retriever.score_neighbors(
            [anchor],
            ego_graphs,
            expanded,
            "q",
            self._config(),
            dense_index=dense_index,
            embedder=embedder,
        )
        chunk_ids = {r.chunk_id for r in results}
        assert anchor_id not in chunk_ids, "Anchor must not appear in scored neighbors"
