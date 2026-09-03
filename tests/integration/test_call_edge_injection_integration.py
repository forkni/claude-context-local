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
from mcp_server.resource_manager import McpResourceRefresher
from merkle import SnapshotManager
from search.config import get_search_config
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
    # inject_call_edges reads self._indexer.dense_index.metadata_store and
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
        resource_refresher=McpResourceRefresher(),
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


@requires_pyan
def test_incremental_index_recovers_edges_when_enabled(mini_repo_project, tmp_path):
    """An incremental pass over a touched file must recover the resolver edges
    ``_remove_old_chunks``/``_add_new_chunks`` destroy for that file, but only
    when ``CallGraphConfig.inject_on_incremental`` is opted in.

    Regression coverage for the monotonic call-edge decay bug: without this
    flag, a file touched by any incremental pass permanently loses its
    resolver-attributed (pyan/LibCST/LSP) edges until a forced full reindex.
    """
    embedder = CodeEmbedder()
    hybrid_searcher = HybridSearcher(
        storage_dir=str(tmp_path / "index"),
        embedder=embedder,
        project_id="mini_repo_test",
    )
    chunker = MultiLanguageChunker.for_project(str(mini_repo_project))
    incremental_indexer = IncrementalIndexer(
        indexer=hybrid_searcher,
        embedder=embedder,
        chunker=chunker,
        snapshot_manager=SnapshotManager(storage_dir=tmp_path / "snapshots"),
        resource_refresher=McpResourceRefresher(),
    )

    full_result = incremental_indexer.incremental_index(
        str(mini_repo_project), "mini_repo_test"
    )
    assert full_result.success
    assert full_result.call_edges_injected > 0

    # Touch service.py (calls repository.get_widget, a cross-module edge only
    # pyan/LibCST resolve) so the next pass takes the incremental-modify path,
    # which prunes and re-adds its graph nodes via remove_file_nodes/
    # add_embeddings -- restoring only the always-on AST-level edges.
    service_file = mini_repo_project / "service.py"
    service_file.write_text(service_file.read_text() + "\n# touched\n")

    config = get_search_config()
    original_flag = config.call_graph.inject_on_incremental
    config.call_graph.inject_on_incremental = True
    try:
        incremental_result = incremental_indexer.incremental_index(
            str(mini_repo_project), "mini_repo_test"
        )
    finally:
        config.call_graph.inject_on_incremental = original_flag

    assert incremental_result.success
    assert incremental_result.files_modified == 1
    assert incremental_result.call_edges_injected > 0
    assert "pyan" in incremental_result.call_edge_resolvers

    graph_path = hybrid_searcher.dense_index.graph_storage.graph_path
    data = json.loads(graph_path.read_text())
    resolved_edges = [edge for edge in data["edges"] if edge.get("resolver_source")]
    assert resolved_edges, "expected at least one edge with resolver_source set"


@pytest.fixture
def split_method_project(tmp_path):
    """A project whose only class has one method long enough to be split.

    ``main.run`` calls ``Worker.process`` cross-module, and ``Worker.process``
    calls ``helpers.compute`` cross-module. Both call sites live in or target
    a method the chunker breaks into ``split_block`` fragments (the body is
    far past ``max_chunk_lines``/``max_split_chars``), so before ADR-0061 the
    resolver line map mapped every line of that method to ``class:Worker``.
    """
    project_dir = tmp_path / "split_method_project"
    project_dir.mkdir()
    (project_dir / "helpers.py").write_text(
        '"""Leaf helper called from inside the long method."""\n\n\n'
        "def compute(value: int) -> int:\n"
        '    """Double the value."""\n'
        "    return value * 2\n",
        encoding="utf-8",
    )
    # The splitter only cuts between block-boundary statements (if/for/...)
    # that are direct children of the function body, so the padding is a flat
    # run of small ``if`` blocks rather than one big loop.
    body = "".join(
        f"        if total >= {i}:  # padding block {i}\n"
        f"            total = total + compute(items[{i} % len(items)])\n"
        for i in range(120)
    )
    (project_dir / "worker.py").write_text(
        '"""Holder of the oversized method."""\n\n'
        "from helpers import compute\n\n\n"
        "class Worker:\n"
        '    """Owns one method long enough to be split into fragments."""\n\n'
        "    def process(self, items: list[int]) -> int:\n"
        '        """Sum the doubled items, very verbosely."""\n'
        "        total = 0\n" + body + "        return total\n",
        encoding="utf-8",
    )
    (project_dir / "main.py").write_text(
        '"""Entry point calling the split method cross-module."""\n\n'
        "from worker import Worker\n\n\n"
        "def run() -> int:\n"
        '    """Drive the worker."""\n'
        "    return Worker().process([1, 2, 3])\n",
        encoding="utf-8",
    )
    return project_dir


@requires_pyan
def test_split_method_callee_lands_on_split_block_not_class(
    split_method_project, tmp_path
):
    """ADR-0061 through the production path: a resolver edge into a long
    (split) method must target one of its ``split_block`` nodes, never the
    enclosing ``class`` node.

    ``inject_call_edges`` builds its line map with the default
    ``semantic_types`` (search/call_edge_injection.py), so this is the same
    map every real index build uses, not only the evaluation tooling.
    """
    embedder = CodeEmbedder()
    hybrid_searcher = HybridSearcher(
        storage_dir=str(tmp_path / "index"),
        embedder=embedder,
        project_id="split_method_test",
    )
    chunker = MultiLanguageChunker.for_project(str(split_method_project))
    incremental_indexer = IncrementalIndexer(
        indexer=hybrid_searcher,
        embedder=embedder,
        chunker=chunker,
        snapshot_manager=SnapshotManager(storage_dir=tmp_path / "snapshots"),
        resource_refresher=McpResourceRefresher(),
    )

    result = incremental_indexer.incremental_index(
        str(split_method_project), "split_method_test"
    )
    assert result.success
    assert result.call_edges_injected > 0

    graph_path = hybrid_searcher.dense_index.graph_storage.graph_path
    data = json.loads(graph_path.read_text())
    split_nodes = [
        node["id"]
        for node in data["nodes"]
        if ":split_block:Worker.process" in node["id"]
    ]
    assert len(split_nodes) >= 2, f"method was not split: {split_nodes}"

    resolved = [edge for edge in data["edges"] if edge.get("resolver_source")]
    into_split = [e for e in resolved if ":split_block:Worker.process" in e["target"]]
    assert into_split, "no resolver edge reached a Worker.process split_block node"
    # ``Worker()`` in main.run is a genuine class-target edge. Its ``line`` is
    # whichever rail last wrote it: the LSP resolver records the callee's
    # ``class`` statement line, while the AST rail (kept when libcst reports
    # line=0, see search/call_edge_injection.py) records the call site
    # relative to the caller chunk — neither falls inside the class body. The
    # bug this guards against is the *other* kind: a callee ``def`` line
    # strictly inside the class body falling through to the class chunk
    # because no fragment covered it.
    (class_id,) = [n["id"] for n in data["nodes"] if ":class:Worker" in n["id"]]
    class_start, class_end = (int(part) for part in class_id.split(":")[1].split("-"))
    inside_body = [
        e
        for e in resolved
        if e["target"] == class_id and class_start < (e.get("line") or 0) <= class_end
    ]
    assert not inside_body, (
        f"resolver edges still land on the class body: {inside_body}"
    )
