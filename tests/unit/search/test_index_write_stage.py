"""Unit tests for IndexWriteStage pipeline stage."""

import time
from unittest.mock import Mock, patch

from search.index_write_stage import IncrementalIndexResult, IndexWriteStage


def _make_chunk(chunk_id: str = "file.py:1-10:function:foo"):
    chunk = Mock()
    chunk.chunk_id = chunk_id
    chunk.content = "def foo(): pass"
    return chunk


def _make_stage(
    *,
    embed_results=None,
    bm25_result=(False, 0),
):
    embedder = Mock()
    if embed_results is None:
        embed_result = Mock()
        embed_result.metadata = {}
        embed_results = [embed_result]
    embedder.embed_chunks.return_value = embed_results

    indexer = Mock()
    snapshot_manager = Mock()
    bm25_sync = Mock()
    bm25_sync.sync_if_needed.return_value = bm25_result
    build_metadata_fn = Mock(return_value={"project_name": "test"})
    clear_gpu_fn = Mock()
    dag = Mock()

    stage = IndexWriteStage(
        embedder=embedder,
        indexer=indexer,
        snapshot_manager=snapshot_manager,
        bm25_sync=bm25_sync,
        build_metadata_fn=build_metadata_fn,
        clear_gpu_fn=clear_gpu_fn,
    )
    return (
        stage,
        embedder,
        indexer,
        snapshot_manager,
        bm25_sync,
        build_metadata_fn,
        clear_gpu_fn,
        dag,
    )


class TestIndexWriteStageResult:
    """Verify IncrementalIndexResult fields on success."""

    def test_successful_run_returns_correct_result(self):
        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}
        stage, _, _, _, _, _, _, dag = _make_stage(embed_results=[embed_result])

        start = time.time()
        result = stage.run(
            all_chunks=[chunk],
            project_name="myproject",
            dag=dag,
            all_files=["a.py", "b.py"],
            supported_files=["a.py"],
            start_time=start,
            repo_profile=None,
        )

        assert isinstance(result, IncrementalIndexResult)
        assert result.success is True
        assert result.error is None
        assert result.files_added == 1  # len(supported_files)
        assert result.files_removed == 0
        assert result.files_modified == 0
        assert result.chunks_added == 1
        assert result.chunks_removed == 0
        assert result.time_taken >= 0

    def test_bm25_flags_propagated(self):
        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}
        stage, *_, dag = _make_stage(
            embed_results=[embed_result], bm25_result=(True, 42)
        )

        result = stage.run(
            all_chunks=[chunk],
            project_name="p",
            dag=dag,
            all_files=[],
            supported_files=[],
            start_time=time.time(),
            repo_profile=None,
        )

        assert result.bm25_resynced is True
        assert result.bm25_resync_count == 42

    def test_files_added_equals_len_supported_files(self):
        embed_result = Mock()
        embed_result.metadata = {}
        stage, *_, dag = _make_stage(embed_results=[embed_result])
        supported = ["a.py", "b.py", "c.py"]

        result = stage.run(
            all_chunks=[_make_chunk()],
            project_name="p",
            dag=dag,
            all_files=supported + ["untracked.txt"],
            supported_files=supported,
            start_time=time.time(),
            repo_profile=None,
        )

        assert result.files_added == 3


class TestIndexWriteStageOrdering:
    """Embed → add → snapshot → save_indices → bm25 → gpu must happen in that order."""

    def test_call_order(self):
        call_order = []
        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}

        embedder = Mock()
        embedder.embed_chunks.side_effect = lambda *a, **kw: (
            call_order.append("embed") or [embed_result]
        )
        indexer = Mock()
        indexer.add_embeddings.side_effect = lambda *a, **kw: call_order.append("add")
        indexer.save_indices.side_effect = lambda *a, **kw: call_order.append(
            "save_indices"
        )
        snapshot_manager = Mock()
        snapshot_manager.save_snapshot.side_effect = lambda *a, **kw: call_order.append(
            "save_snapshot"
        )
        bm25_sync = Mock()
        bm25_sync.sync_if_needed.side_effect = lambda *a, **kw: (
            call_order.append("bm25") or (False, 0)
        )
        clear_gpu_fn = Mock(side_effect=lambda *a, **kw: call_order.append("gpu"))

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=snapshot_manager,
            bm25_sync=bm25_sync,
            build_metadata_fn=Mock(return_value={}),
            clear_gpu_fn=clear_gpu_fn,
        )
        stage.run(
            all_chunks=[chunk],
            project_name="p",
            dag=Mock(),
            all_files=[],
            supported_files=[],
            start_time=time.time(),
            repo_profile=None,
        )

        assert call_order == [
            "embed",
            "add",
            "save_snapshot",
            "save_indices",
            "bm25",
            "gpu",
        ]

    def test_snapshot_metadata_passes_is_full_true(self):
        embed_result = Mock()
        embed_result.metadata = {}
        stage, _, _, _, _, build_metadata_fn, _, dag = _make_stage(
            embed_results=[embed_result]
        )

        stage.run(
            all_chunks=[_make_chunk()],
            project_name="proj",
            dag=dag,
            all_files=["f.py"],
            supported_files=["f.py"],
            start_time=time.time(),
            repo_profile=None,
        )

        call_kwargs = build_metadata_fn.call_args.kwargs
        assert call_kwargs["is_full"] is True
        assert call_kwargs["cumulative_changed_files"] == 0
        assert call_kwargs["project_name"] == "proj"

    def test_embedding_metadata_updated(self):
        chunk = _make_chunk("f.py:1-5:function:foo")
        chunk.content = "def foo(): pass"
        embed_result = Mock()
        embed_result.metadata = {}
        stage, *_, dag = _make_stage(embed_results=[embed_result])

        stage.run(
            all_chunks=[chunk],
            project_name="myproj",
            dag=dag,
            all_files=[],
            supported_files=[],
            start_time=time.time(),
            repo_profile=None,
        )

        assert embed_result.metadata["project_name"] == "myproj"
        assert embed_result.metadata["content"] == "def foo(): pass"


# ---------------------------------------------------------------------------
# Task 14 — min_confidence floor in _inject_call_edges
# ---------------------------------------------------------------------------


class TestInjectCallEdgesMinConfidence:
    """_inject_call_edges must discard edges below min_confidence before injection."""

    @staticmethod
    def _make_resolved_edge(
        caller: str, callee: str, confidence: float, source: str = "pyan"
    ):
        from chunking.relationships.call_edge_resolver import ResolvedEdge

        return ResolvedEdge(
            caller_id=caller,
            callee_id=callee,
            line=1,
            is_method=False,
            source=source,
            confidence=confidence,
        )

    @staticmethod
    def _make_stage_for_injection() -> IndexWriteStage:
        """Return an IndexWriteStage whose _indexer has all the attributes
        _inject_call_edges accesses (graph, dense_index.metadata_store)."""
        import networkx as nx

        g = nx.DiGraph()
        g.add_node("caller_a")
        g.add_node("callee_a")
        g.add_node("caller_b")
        g.add_node("callee_b")

        storage = Mock()
        storage.graph = g

        graph_integration = Mock()
        graph_integration.storage = storage

        meta_store = Mock()
        dense_index = Mock()
        dense_index.metadata_store = meta_store

        indexer = Mock()
        indexer._graph = graph_integration
        indexer.dense_index = dense_index

        stage = IndexWriteStage(
            embedder=Mock(),
            indexer=indexer,
            snapshot_manager=Mock(),
            bm25_sync=Mock(),
            build_metadata_fn=Mock(return_value={}),
            clear_gpu_fn=Mock(),
        )
        return stage, storage

    def test_edge_below_min_confidence_not_injected(self) -> None:
        """An edge with confidence=0.75 must be dropped when min_confidence=0.80."""
        from search.config import CallGraphConfig

        stage, storage = self._make_stage_for_injection()

        pyan_edge = self._make_resolved_edge("caller_a", "callee_a", 0.75)
        libcst_edge = self._make_resolved_edge(
            "caller_b", "callee_b", 0.90, source="libcst"
        )

        merged_edges = {
            ("caller_a", "callee_a"): pyan_edge,
            ("caller_b", "callee_b"): libcst_edge,
        }

        cg_cfg = CallGraphConfig(min_confidence=0.80)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch("search.index_write_stage.build_line_to_chunk_map", return_value={}),
            patch("search.config.get_search_config", return_value=mock_cfg),
            patch("search.index_write_stage.run_resolvers", return_value=merged_edges),
            patch("search.index_write_stage.PyanResolver", return_value=Mock()),
        ):
            stage._inject_call_edges("/fake/project")

        # Only the 0.90 edge (caller_b → callee_b) should have been injected.
        calls = [str(c) for c in storage.add_call_edge.call_args_list]
        assert any("caller_b" in c and "callee_b" in c for c in calls), (
            f"Expected libcst (0.90) edge to be injected; add_call_edge calls: {calls}"
        )
        assert not any("caller_a" in c and "callee_a" in c for c in calls), (
            f"Expected pyan (0.75) edge to be dropped; add_call_edge calls: {calls}"
        )

    def test_zero_min_confidence_injects_all(self) -> None:
        """With min_confidence=0.0 (default), no edges are dropped."""
        from search.config import CallGraphConfig

        stage, storage = self._make_stage_for_injection()

        pyan_edge = self._make_resolved_edge("caller_a", "callee_a", 0.75)
        merged_edges = {("caller_a", "callee_a"): pyan_edge}

        cg_cfg = CallGraphConfig(min_confidence=0.0)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch("search.index_write_stage.build_line_to_chunk_map", return_value={}),
            patch("search.config.get_search_config", return_value=mock_cfg),
            patch("search.index_write_stage.run_resolvers", return_value=merged_edges),
            patch("search.index_write_stage.PyanResolver", return_value=Mock()),
        ):
            stage._inject_call_edges("/fake/project")

        calls = [str(c) for c in storage.add_call_edge.call_args_list]
        assert any("caller_a" in c and "callee_a" in c for c in calls), (
            f"Expected pyan (0.75) edge injected with min_confidence=0.0; calls: {calls}"
        )


class TestIndexWriteStageEmbeddingFailure:
    """Embedding failure is reported loudly: success=False, no snapshot written."""

    def test_embedding_failure_returns_failure_result(self):
        embedder = Mock()
        embedder.embed_chunks.side_effect = RuntimeError("CUDA OOM")
        indexer = Mock()
        snapshot_manager = Mock()
        bm25_sync = Mock()
        bm25_sync.sync_if_needed.return_value = (False, 0)
        clear_gpu_fn = Mock()

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=snapshot_manager,
            bm25_sync=bm25_sync,
            build_metadata_fn=Mock(return_value={}),
            clear_gpu_fn=clear_gpu_fn,
        )

        result = stage.run(
            all_chunks=[_make_chunk()],
            project_name="p",
            dag=Mock(),
            all_files=[],
            supported_files=[],
            start_time=time.time(),
            repo_profile=None,
        )

        assert result.success is False
        assert result.error is not None
        assert "CUDA OOM" in result.error
        assert result.chunks_added == 0
        indexer.add_embeddings.assert_not_called()
        snapshot_manager.save_snapshot.assert_not_called()
        clear_gpu_fn.assert_called_once_with("FULL_INDEX")

    def test_empty_chunks_skips_embed_and_add(self):
        stage, embedder, indexer, *_ = _make_stage()

        result = stage.run(
            all_chunks=[],
            project_name="p",
            dag=Mock(),
            all_files=[],
            supported_files=[],
            start_time=time.time(),
            repo_profile=None,
        )

        embedder.embed_chunks.assert_not_called()
        indexer.add_embeddings.assert_not_called()
        assert result.chunks_added == 0


class TestIncrementalIndexResultDataclass:
    """Verify IncrementalIndexResult fields and to_dict."""

    def test_defaults(self):
        r = IncrementalIndexResult(
            files_added=1,
            files_removed=0,
            files_modified=0,
            chunks_added=10,
            chunks_removed=0,
            time_taken=0.5,
            success=True,
        )
        assert r.error is None
        assert r.bm25_resynced is False
        assert r.bm25_resync_count == 0

    def test_to_dict_round_trip(self):
        r = IncrementalIndexResult(
            files_added=3,
            files_removed=1,
            files_modified=2,
            chunks_added=30,
            chunks_removed=10,
            time_taken=2.0,
            success=False,
            error="boom",
            bm25_resynced=True,
            bm25_resync_count=5,
        )
        d = r.to_dict()
        assert d["files_added"] == 3
        assert d["error"] == "boom"
        assert d["bm25_resynced"] is True
        assert d["bm25_resync_count"] == 5
