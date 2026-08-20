"""Unit tests for IndexWriteStage pipeline stage."""

import time
from unittest.mock import Mock, patch

from search.call_edge_injection import InjectionStats
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
    indexer.resync_if_desynced.return_value = bm25_result
    snapshot_manager = Mock()
    build_metadata_fn = Mock(return_value={"project_name": "test"})
    clear_gpu_fn = Mock()
    dag = Mock()

    stage = IndexWriteStage(
        embedder=embedder,
        indexer=indexer,
        snapshot_manager=snapshot_manager,
        build_metadata_fn=build_metadata_fn,
        clear_gpu_fn=clear_gpu_fn,
    )
    return (
        stage,
        embedder,
        indexer,
        snapshot_manager,
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
        stage, _, _, _, _, _, dag = _make_stage(embed_results=[embed_result])

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
        indexer.resync_if_desynced.side_effect = lambda *a, **kw: (
            call_order.append("bm25") or (False, 0)
        )
        snapshot_manager = Mock()
        snapshot_manager.save_snapshot.side_effect = lambda *a, **kw: call_order.append(
            "save_snapshot"
        )
        clear_gpu_fn = Mock(side_effect=lambda *a, **kw: call_order.append("gpu"))

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=snapshot_manager,
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
        stage, _, _, _, build_metadata_fn, _, dag = _make_stage(
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
# Task 14 — min_confidence floor in inject_call_edges
# ---------------------------------------------------------------------------


class TestInjectCallEdgesMinConfidence:
    """inject_call_edges must discard edges below min_confidence before injection."""

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
        inject_call_edges accesses (graph, dense_index.metadata_store)."""
        import networkx as nx

        g = nx.MultiDiGraph()
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
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch(
                "search.call_edge_injection.run_resolvers", return_value=merged_edges
            ),
            patch("search.call_edge_injection.PyanResolver", return_value=Mock()),
        ):
            stage.inject_call_edges("/fake/project")

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
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch(
                "search.call_edge_injection.run_resolvers", return_value=merged_edges
            ),
            patch("search.call_edge_injection.PyanResolver", return_value=Mock()),
        ):
            stage.inject_call_edges("/fake/project")

        calls = [str(c) for c in storage.add_call_edge.call_args_list]
        assert any("caller_a" in c and "callee_a" in c for c in calls), (
            f"Expected pyan (0.75) edge injected with min_confidence=0.0; calls: {calls}"
        )


# ---------------------------------------------------------------------------
# resolvers=[] vs resolvers=None (config-driven resolver selection)
# ---------------------------------------------------------------------------


class TestInjectCallEdgesResolverSelection:
    """CallGraphConfig.resolvers=[] must skip pyan/libcst entirely (per its own
    docstring: "Set to [] to skip entirely"), distinct from resolvers=None
    (unset, falls back to the ["pyan", "libcst"] default). Regression test for
    a bug where `cg_cfg.resolvers or ["pyan", "libcst"]` treated an explicit
    empty list the same as unset, because `[]` is falsy in Python.
    """

    @staticmethod
    def _make_stage_for_injection() -> tuple[IndexWriteStage, Mock]:
        """Graph must be non-empty — an empty graph now short-circuits via the
        loud empty-graph guard (G0) before resolver selection is even reached,
        which is exactly what these tests exercise."""
        import networkx as nx

        g = nx.MultiDiGraph()
        g.add_node("caller_a")
        g.add_node("callee_a")

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
            build_metadata_fn=Mock(return_value={}),
            clear_gpu_fn=Mock(),
        )
        return stage, storage

    def test_empty_resolvers_list_skips_injection_entirely(self) -> None:
        """resolvers=[] with lsp_enabled=False must leave zero resolvers -- no
        call to run_resolvers, no edges injected."""
        from search.config import CallGraphConfig

        stage, storage = self._make_stage_for_injection()

        cg_cfg = CallGraphConfig(resolvers=[], lsp_enabled=False)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch("search.call_edge_injection.run_resolvers") as mock_run_resolvers,
        ):
            stage.inject_call_edges("/fake/project")

        mock_run_resolvers.assert_not_called()
        storage.add_call_edge.assert_not_called()

    def test_none_resolvers_falls_back_to_default_pair(self) -> None:
        """resolvers=None (unset) must still default to pyan+libcst."""
        from search.config import CallGraphConfig

        stage, storage = self._make_stage_for_injection()

        cg_cfg = CallGraphConfig(resolvers=None, lsp_enabled=False)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch(
                "search.call_edge_injection.run_resolvers", return_value={}
            ) as mock_run_resolvers,
        ):
            stage.inject_call_edges("/fake/project")

        mock_run_resolvers.assert_called_once()
        resolver_instances = mock_run_resolvers.call_args.args[0]
        assert len(resolver_instances) == 2, (
            f"Expected pyan+libcst (2 resolvers) with resolvers=None; got {resolver_instances}"
        )

    def test_lsp_in_resolvers_list_warns_and_has_no_effect(self, caplog) -> None:
        """resolvers=["pyan", "libcst", "lsp"] must warn that "lsp" has no
        effect there (2026-08-06 config-liveness audit, D3) and build an
        identical resolver ladder to resolvers=["pyan", "libcst"] at the same
        lsp_enabled=False - "lsp" in the list neither enables nor duplicates
        Stage 3, which is governed solely by the separate lsp_enabled bool.
        """
        import logging

        from search.config import CallGraphConfig

        stage, storage = self._make_stage_for_injection()

        cg_cfg = CallGraphConfig(resolvers=["pyan", "libcst", "lsp"], lsp_enabled=False)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch(
                "search.call_edge_injection.run_resolvers", return_value={}
            ) as mock_run_resolvers,
            caplog.at_level(logging.WARNING, logger="search.call_edge_injection"),
        ):
            stage.inject_call_edges("/fake/project")

        mock_run_resolvers.assert_called_once()
        resolver_instances = mock_run_resolvers.call_args.args[0]
        assert len(resolver_instances) == 2, (
            "Expected pyan+libcst (2 resolvers) with resolvers=[..., 'lsp'], "
            f"lsp_enabled=False; got {resolver_instances}"
        )
        assert any(
            "lsp" in rec.message and "lsp_enabled" in rec.message
            for rec in caplog.records
        ), f"Expected a warning naming 'lsp'/'lsp_enabled'; got {caplog.records}"

    def test_unrecognized_resolver_name_warns(self, caplog) -> None:
        """A garbage name in resolvers=[...] must warn and be ignored, not
        silently dropped -- the failure mode a typo'd config value shares
        with the historical inert-guardrail bug class."""
        import logging

        from search.config import CallGraphConfig

        stage, storage = self._make_stage_for_injection()

        cg_cfg = CallGraphConfig(
            resolvers=["pyan", "not-a-real-resolver"], lsp_enabled=False
        )
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch(
                "search.call_edge_injection.run_resolvers", return_value={}
            ) as mock_run_resolvers,
            caplog.at_level(logging.WARNING, logger="search.call_edge_injection"),
        ):
            stage.inject_call_edges("/fake/project")

        mock_run_resolvers.assert_called_once()
        resolver_instances = mock_run_resolvers.call_args.args[0]
        assert len(resolver_instances) == 1, (
            f"Expected only pyan (1 resolver); got {resolver_instances}"
        )
        assert any("not-a-real-resolver" in rec.message for rec in caplog.records), (
            f"Expected a warning naming the unrecognized resolver; got {caplog.records}"
        )


# ---------------------------------------------------------------------------
# inject_call_edges_if_enabled — the incremental opt-in gate (ADR-0044)
# ---------------------------------------------------------------------------


class TestInjectCallEdgesIfEnabled:
    """The stage owns the `inject_on_incremental` gate: off (the default) is
    zero injection work with all-zero stats; on delegates to inject_call_edges.
    """

    @staticmethod
    def _make_stage() -> IndexWriteStage:
        return IndexWriteStage(
            embedder=Mock(),
            indexer=Mock(),
            snapshot_manager=Mock(),
            build_metadata_fn=Mock(return_value={}),
            clear_gpu_fn=Mock(),
        )

    @staticmethod
    def _patch_config(enabled: bool):
        mock_cfg = Mock()
        mock_cfg.call_graph.inject_on_incremental = enabled
        return patch(
            "search.index_write_stage.get_search_config", return_value=mock_cfg
        )

    def test_gate_off_is_zero_work(self) -> None:
        """Gate off must return all-zero InjectionStats without touching the
        indexer's graph/metadata collaborators (ADR-0044's zero-work path)."""
        stage = self._make_stage()
        with (
            self._patch_config(enabled=False),
            patch.object(stage, "inject_call_edges") as mock_inject,
        ):
            stats = stage.inject_call_edges_if_enabled("/fake/project")

        mock_inject.assert_not_called()
        assert stats == InjectionStats()
        assert stats.injected == 0
        assert stats.resolvers_run == ()

    def test_gate_on_delegates(self) -> None:
        stage = self._make_stage()
        sentinel = InjectionStats(injected=3, resolvers_run=("pyan",))
        with (
            self._patch_config(enabled=True),
            patch.object(
                stage, "inject_call_edges", return_value=sentinel
            ) as mock_inject,
        ):
            stats = stage.inject_call_edges_if_enabled("/fake/project")

        mock_inject.assert_called_once_with("/fake/project")
        assert stats is sentinel


# ---------------------------------------------------------------------------
# MultiDiGraph edge-injection correctness (#3 follow-up)
# ---------------------------------------------------------------------------


class TestInjectCallEdgesMultiGraph:
    """inject_call_edges must handle MultiDiGraph edge keying correctly.

    Regression tests for the two bugs introduced by the DiGraph→MultiDiGraph migration
    that were missed by the original blast-radius sweep:

    Bug 1 (reported): g.edges[u, v] 2-tuple subscript → ValueError on MultiDiGraph.
    Bug 2 (latent):   g.has_edge(u, v) returns True for any parallel edge type;
                      a pre-existing "imports" edge caused upgrade_call_edge to be called
                      for a "calls" edge that didn't exist → KeyError.
    """

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
    def _make_stage_with_real_graph(extra_nodes=None):
        """Return (stage, storage, g) where g is a real MultiDiGraph.

        storage.add_call_edge / upgrade_call_edge are Mocks so calls are assertable,
        but storage.graph is the *real* MultiDiGraph so g.edges[...] exercises real code.
        """
        import networkx as nx

        g = nx.MultiDiGraph()
        for node in ["src/a.py:1:function:foo", "src/b.py:1:function:bar"] + (
            extra_nodes or []
        ):
            g.add_node(node)

        storage = Mock()
        storage.graph = g

        graph_integration = Mock()
        graph_integration.storage = storage

        dense_index = Mock()
        dense_index.metadata_store = Mock()

        indexer = Mock()
        indexer._graph = graph_integration
        indexer.dense_index = dense_index

        stage = IndexWriteStage(
            embedder=Mock(),
            indexer=indexer,
            snapshot_manager=Mock(),
            build_metadata_fn=Mock(return_value={}),
            clear_gpu_fn=Mock(),
        )
        return stage, storage, g

    def test_upgrade_branch_reads_calls_edge_no_valueerror(self):
        """Upgrade path: existing "calls" edge → upgrade_call_edge called, no ValueError.

        Pre-fix: g.edges[u, v] raised ValueError on MultiDiGraph (expected 3-tuple key).
        """
        from search.config import CallGraphConfig

        caller = "src/a.py:1:function:foo"
        callee = "src/b.py:1:function:bar"
        stage, storage, g = self._make_stage_with_real_graph()

        # Seed a "calls" edge at low confidence — injection should upgrade it.
        g.add_edge(caller, callee, key="calls", resolver_confidence=0.5)

        edge = self._make_resolved_edge(
            caller, callee, confidence=0.90, source="libcst"
        )
        merged = {(caller, callee): edge}

        cg_cfg = CallGraphConfig(min_confidence=0.0)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch("search.call_edge_injection.run_resolvers", return_value=merged),
            patch("search.call_edge_injection.PyanResolver", return_value=Mock()),
        ):
            # Must not raise ValueError (was the crash)
            stage.inject_call_edges("/fake/project")

        storage.upgrade_call_edge.assert_called_once()
        storage.add_call_edge.assert_not_called()

    def test_parallel_imports_edge_does_not_block_calls_injection(self):
        """Latent bug: "imports" parallel edge must not shadow missing "calls" edge.

        Pre-fix: g.has_edge(u, v) returned True for the "imports" key, routing to the
        upgrade branch which then did g.edges[u, v, "calls"] → KeyError.
        """
        from search.config import CallGraphConfig

        caller = "src/a.py:1:function:foo"
        callee = "src/b.py:1:function:bar"
        stage, storage, g = self._make_stage_with_real_graph()

        # Only an "imports" edge exists — NO "calls" edge yet.
        g.add_edge(caller, callee, key="imports", type="imports", confidence=1.0)

        edge = self._make_resolved_edge(caller, callee, confidence=0.75, source="pyan")
        merged = {(caller, callee): edge}

        cg_cfg = CallGraphConfig(min_confidence=0.0)
        mock_cfg = Mock()
        mock_cfg.call_graph = cg_cfg

        with (
            patch(
                "search.call_edge_injection.build_line_to_chunk_map", return_value={}
            ),
            patch("search.index_write_stage.get_search_config", return_value=mock_cfg),
            patch("search.call_edge_injection.run_resolvers", return_value=merged),
            patch("search.call_edge_injection.PyanResolver", return_value=Mock()),
        ):
            stage.inject_call_edges("/fake/project")

        # The "calls" edge did NOT exist → add_call_edge must be called, not upgrade.
        storage.add_call_edge.assert_called_once()
        storage.upgrade_call_edge.assert_not_called()


class TestIndexWriteStageEmbeddingFailure:
    """Embedding failure is reported loudly: success=False, no snapshot written."""

    def test_embedding_failure_returns_failure_result(self):
        embedder = Mock()
        embedder.embed_chunks.side_effect = RuntimeError("CUDA OOM")
        indexer = Mock()
        snapshot_manager = Mock()
        clear_gpu_fn = Mock()

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=snapshot_manager,
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


# ---------------------------------------------------------------------------
# Round 3 — persistent content-hash embedding cache wiring
# ---------------------------------------------------------------------------


class TestResolveChunkCache:
    """_resolve_chunk_cache: lazy per-run resolution, fail-soft on Mock storage_dir."""

    def test_mock_storage_dir_yields_no_cache_and_run_still_succeeds(self):
        """All five pre-existing Mock()-based cases above already exercise this
        path unmodified (indexer=Mock() ⇒ indexer.storage_dir is a Mock, so
        Path(...) on it fails inside the try/except and _resolve_chunk_cache
        returns None). This test pins that behaviour explicitly: embed_chunks
        must be called with cache=None and the run must still succeed."""
        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}
        stage, embedder, _, _, _, _, dag = _make_stage(embed_results=[embed_result])

        result = stage.run(
            all_chunks=[chunk],
            project_name="p",
            dag=dag,
            all_files=[],
            supported_files=[],
            start_time=time.time(),
            repo_profile=None,
        )

        assert result.success is True
        call_kwargs = embedder.embed_chunks.call_args.kwargs
        assert call_kwargs.get("cache") is None

    def test_real_storage_dir_passes_cache_with_expected_path(self, tmp_path):
        """A real tmp_path storage_dir ⇒ embed_chunks receives a non-None
        cache whose on-disk path is storage_dir / "chunk_embeddings.bin"."""
        from search.config import EmbeddingConfig

        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}
        embedder = Mock()
        embedder.embed_chunks.return_value = [embed_result]

        indexer = Mock()
        indexer.storage_dir = tmp_path
        indexer.resync_if_desynced.return_value = (False, 0)

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=Mock(),
            build_metadata_fn=Mock(return_value={"project_name": "test"}),
            clear_gpu_fn=Mock(),
        )

        mock_cfg = Mock()
        mock_cfg.embedding = EmbeddingConfig(enable_chunk_cache=True)

        with patch("search.config.get_search_config", return_value=mock_cfg):
            result = stage.run(
                all_chunks=[chunk],
                project_name="p",
                dag=Mock(),
                all_files=[],
                supported_files=[],
                start_time=time.time(),
                repo_profile=None,
            )

        assert result.success is True
        call_kwargs = embedder.embed_chunks.call_args.kwargs
        cache = call_kwargs.get("cache")
        assert cache is not None
        assert cache._path == tmp_path / "chunk_embeddings.bin"

    def test_provenance_unavailable_sentinel_for_mock_embedder(self, tmp_path):
        """embedder=Mock() auto-generates get_embedding_provenance() as a
        callable returning a Mock, not a str. The isinstance guard in
        _resolve_embedding_provenance must catch this and fall back to the
        "unavailable" sentinel rather than handing a Mock to
        ChunkEmbeddingCache, which would fail .encode() in save()."""
        from search.config import EmbeddingConfig

        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}
        embedder = Mock()
        embedder.embed_chunks.return_value = [embed_result]

        indexer = Mock()
        indexer.storage_dir = tmp_path
        indexer.resync_if_desynced.return_value = (False, 0)

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=Mock(),
            build_metadata_fn=Mock(return_value={"project_name": "test"}),
            clear_gpu_fn=Mock(),
        )

        mock_cfg = Mock()
        mock_cfg.embedding = EmbeddingConfig(enable_chunk_cache=True)

        with patch("search.config.get_search_config", return_value=mock_cfg):
            result = stage.run(
                all_chunks=[chunk],
                project_name="p",
                dag=Mock(),
                all_files=[],
                supported_files=[],
                start_time=time.time(),
                repo_profile=None,
            )

        assert result.success is True
        cache = embedder.embed_chunks.call_args.kwargs.get("cache")
        assert cache is not None
        assert cache._provenance == "unavailable"

    def test_disabled_by_config_yields_no_cache(self, tmp_path):
        """enable_chunk_cache=False ⇒ embed_chunks receives cache=None even
        with a real, writable storage_dir."""
        from search.config import EmbeddingConfig

        chunk = _make_chunk()
        embed_result = Mock()
        embed_result.metadata = {}
        embedder = Mock()
        embedder.embed_chunks.return_value = [embed_result]

        indexer = Mock()
        indexer.storage_dir = tmp_path
        indexer.resync_if_desynced.return_value = (False, 0)

        stage = IndexWriteStage(
            embedder=embedder,
            indexer=indexer,
            snapshot_manager=Mock(),
            build_metadata_fn=Mock(return_value={"project_name": "test"}),
            clear_gpu_fn=Mock(),
        )

        mock_cfg = Mock()
        mock_cfg.embedding = EmbeddingConfig(enable_chunk_cache=False)

        with patch("search.config.get_search_config", return_value=mock_cfg):
            stage.run(
                all_chunks=[chunk],
                project_name="p",
                dag=Mock(),
                all_files=[],
                supported_files=[],
                start_time=time.time(),
                repo_profile=None,
            )

        call_kwargs = embedder.embed_chunks.call_args.kwargs
        assert call_kwargs.get("cache") is None


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
