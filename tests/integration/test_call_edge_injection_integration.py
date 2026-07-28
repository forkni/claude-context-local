"""Integration test for the G0 call-edge injection seam (search/call_edge_injection.py).

``tests/unit/search/test_index_write_stage.py`` asserts injection only against a
``Mock`` graph storage — ``storage.add_call_edge.call_args_list``. That shape is
exactly what let a past bug (3adc724) ship silently: the mocked call happened,
and the discarded return value was never inspected. This test drives the real
pipeline — ``IncrementalIndexer`` -> ``IndexWriteStage`` -> ``inject_call_edges``
-- against ``tests/fixtures/mini_repo/`` (real files with genuine cross-module
calls) and asserts on the *count* the pipeline produced and what actually landed
in the persisted graph JSON, not on which mocks were called.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from chunking.relationships.external_call_graph import pyan_available
from embeddings.embedder import CodeEmbedder
from merkle import SnapshotManager
from search.hybrid_searcher import HybridSearcher
from search.incremental_indexer import IncrementalIndexer


MINI_REPO = Path(__file__).parent.parent / "fixtures" / "mini_repo"

# Injection needs real pyan3 call-graph analysis to guarantee non-zero edges
# from this fixture; the product degrades gracefully when pyan3 is absent, so
# this test must skip rather than produce a false failure in minimal-dep envs.
# Install the '[callgraph]' extra (pyan3) to run it. Mirrors the convention in
# tests/unit/chunking/relationships/test_external_call_graph.py.
requires_pyan = pytest.mark.skipif(
    not pyan_available(),
    reason="pyan3 not installed — install the '[callgraph]' extra",
)


@pytest.fixture(autouse=True)
def _mock_model_load():
    """Prevent real model downloads — mirrors tests/integration/test_auto_reindex_fixes.py."""
    import numpy as np

    class _FakeEmbeddingModel:
        max_seq_length = 512
        device = "cpu"

        def encode(
            self, sentences, show_progress_bar=False, convert_to_tensor=False, **kwargs
        ):
            n = 1 if isinstance(sentences, str) else len(sentences)
            return np.zeros((n, 768), dtype=np.float32)

        def get_sentence_embedding_dimension(self):
            return 768

    with patch(
        "embeddings.model_loader.ModelLoader.load",
        return_value=(_FakeEmbeddingModel(), "cpu"),
    ):
        yield


@pytest.fixture
def mini_repo_project(tmp_path):
    """Copy the mini_repo fixture into an isolated project directory."""
    project_dir = tmp_path / "mini_repo_project"
    shutil.copytree(MINI_REPO, project_dir)
    return project_dir


@requires_pyan
def test_full_index_injects_real_call_edges(mini_repo_project, tmp_path):
    """A full index of mini_repo/ must surface a non-zero, resolver-attributed count.

    Regression test for the shape of 3adc724: the resolver pipeline running
    against a Mock and the result being discarded is exactly how a project
    can end up with ``success=True`` and zero edges, silently.
    """
    # _inject_call_edges reads self._indexer.dense_index.metadata_store and
    # self._indexer._graph — attributes CodeIndexManager alone does not
    # expose. Production wires a HybridSearcher as IncrementalIndexer's
    # "indexer" (mcp_server/tools/index_handlers.py:142, docstring: "indexer:
    # HybridSearcher or CodeIndexManager"); a bare CodeIndexManager here would
    # exercise a path production never takes. project_id must also be
    # non-empty — a falsy project_id leaves graph storage as None.
    embedder = CodeEmbedder()
    hybrid_searcher = HybridSearcher(
        storage_dir=str(tmp_path / "index"),
        embedder=embedder,
        project_id="mini_repo_test",
    )
    # IncrementalIndexer's bare-constructor chunker fallback has no root_path
    # (see MultiLanguageChunker.for_project's docstring: "the rootless
    # IncrementalIndexer.__init__ chunker fallback"), so every chunk's
    # relative_path becomes an absolute path instead of a project-relative
    # one — which makes scope_to_indexed_files() filter out every resolver
    # file, since it compares against genuinely-relative indexed paths.
    # Production always builds the chunker via .for_project() (
    # mcp_server/tools/index_handlers.py:879); mirror that here.
    chunker = MultiLanguageChunker.for_project(str(mini_repo_project))
    incremental_indexer = IncrementalIndexer(
        indexer=hybrid_searcher,
        embedder=embedder,
        chunker=chunker,
        snapshot_manager=SnapshotManager(storage_dir=tmp_path / "snapshots"),
    )

    result = incremental_indexer.incremental_index(
        str(mini_repo_project), "mini_repo_test"
    )

    assert result.success
    # Assert on the count the pipeline produced, not on whether a resolver
    # method was called — that is the anti-regression rule this test exists
    # to enforce (see tests/TESTING_GUIDE.md).
    assert result.call_edges_injected > 0
    assert "pyan" in result.call_edge_resolvers

    # Confirm the edges actually reached the persisted graph JSON — not just
    # the in-memory InjectionStats — with resolver provenance attached.
    graph_path = hybrid_searcher.dense_index.graph_storage.graph_path
    assert graph_path.exists()
    data = json.loads(graph_path.read_text())
    resolved_edges = [edge for edge in data["edges"] if edge.get("resolver_source")]
    assert resolved_edges, "expected at least one edge with resolver_source set"
