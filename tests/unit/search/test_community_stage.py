"""Unit tests for CommunityStage pipeline stage."""

from unittest.mock import MagicMock, Mock, patch

from search.community_stage import CommunityStage


def _make_chunk(chunk_id: str = "file.py:1-10:function:foo"):
    chunk = Mock()
    chunk.chunk_id = chunk_id
    chunk.file_path = "file.py"
    chunk.content = f"def {chunk_id.split(':')[-1]}(): pass"
    return chunk


def _make_config(
    *,
    enable_community_detection: bool = True,
    enable_community_summaries: bool = True,
    enable_community_merge: bool = True,
    enable_file_summaries: bool = True,
    community_resolution: float = 1.0,
    min_chunk_tokens: int = 20,
    max_merged_tokens: int = 500,
    token_estimation: str = "approx",
    size_method: str = "tokens",
):
    config = MagicMock()
    cfg = config.chunking
    cfg.enable_community_detection = enable_community_detection
    cfg.enable_community_summaries = enable_community_summaries
    cfg.enable_community_merge = enable_community_merge
    cfg.enable_file_summaries = enable_file_summaries
    cfg.community_resolution = community_resolution
    cfg.min_chunk_tokens = min_chunk_tokens
    cfg.max_merged_tokens = max_merged_tokens
    cfg.token_estimation = token_estimation
    cfg.size_method = size_method
    # getattr fallback for max_phantom_degree
    cfg.max_phantom_degree = 20
    return config


class TestCommunityStagePassThrough:
    """When remerge/summaries are disabled, chunks pass through unchanged."""

    def test_all_flags_off_returns_original_chunks(self):
        chunks = [
            _make_chunk("f.py:1-5:function:a"),
            _make_chunk("f.py:6-10:function:b"),
        ]
        config = _make_config(
            enable_community_detection=False,
            enable_community_summaries=False,
            enable_community_merge=False,
            enable_file_summaries=False,
        )
        stage = CommunityStage(
            build_graph_fn=Mock(),
            regenerate_ids_fn=Mock(),
            summary_stage=Mock(),
        )
        result = stage.run(chunks, "/project", config)
        assert result == chunks

    def test_empty_chunks_returns_empty(self):
        config = _make_config()
        stage = CommunityStage(
            build_graph_fn=Mock(),
            regenerate_ids_fn=Mock(),
            summary_stage=Mock(),
        )
        result = stage.run([], "/project", config)
        assert result == []

    def test_merge_disabled_skips_detection_entirely(self):
        """enable_community_merge=False (the live production config — see
        search_config.json) must skip detection entirely in run(): the graph
        it would feed only exists to drive remerge. Detection for real,
        persisted communities happens later in run_post_injection()."""
        chunks = [_make_chunk("f.py:1-5:function:a")]
        build_graph_fn = Mock()
        summary_stage = Mock()
        summary_stage.generate_module_summaries.return_value = []

        stage = CommunityStage(
            build_graph_fn=build_graph_fn,
            regenerate_ids_fn=Mock(),
            summary_stage=summary_stage,
        )
        config = _make_config(enable_community_merge=False)
        result = stage.run(chunks, "/project", config)

        build_graph_fn.assert_not_called()
        assert result == chunks


class TestCommunityStageRemerge:
    """Community-based remerge (pre-embed) — the only graph work left in run()."""

    def _make_stage_and_mocks(self):
        chunks = [_make_chunk("f.py:1-5:function:a")]
        temp_graph = Mock()
        temp_graph.storage = Mock()

        build_graph_fn = Mock(return_value=temp_graph)
        regenerate_ids_fn = Mock(side_effect=lambda c, p: c)
        summary_stage = Mock()
        summary_stage.generate_module_summaries.return_value = []

        stage = CommunityStage(
            build_graph_fn=build_graph_fn,
            regenerate_ids_fn=regenerate_ids_fn,
            summary_stage=summary_stage,
        )
        return (
            stage,
            chunks,
            build_graph_fn,
            regenerate_ids_fn,
            summary_stage,
            temp_graph,
        )

    def test_graph_built_once(self):
        stage, chunks, build_graph_fn, _, _, _ = self._make_stage_and_mocks()
        config = _make_config()

        with patch("search.community_stage.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch(
                "chunking.community_remerge.remerge_chunks_with_communities"
            ) as mock_remerge:
                mock_remerge.return_value = chunks
                stage.run(chunks, "/project", config)

        build_graph_fn.assert_called_once_with(chunks)

    def test_transient_partition_not_persisted(self):
        """The partition run() detects to feed remerge is remerge input only
        — it must never reach store_community_map. Only run_post_injection()
        persists the authoritative, post-injection map."""
        stage, chunks, _, _, _, temp_graph = self._make_stage_and_mocks()
        config = _make_config()
        community_map = {"f.py:1-5:function:a": 0}

        with patch("search.community_stage.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            with patch(
                "chunking.community_remerge.remerge_chunks_with_communities"
            ) as mock_remerge:
                mock_remerge.return_value = chunks
                stage.run(chunks, "/project", config)

        temp_graph.storage.store_community_map.assert_not_called()

    def test_module_summaries_appended_after_remerge(self):
        stage, chunks, _, regenerate_ids_fn, summary_stage, _ = (
            self._make_stage_and_mocks()
        )
        config = _make_config()
        module_summary = _make_chunk("f.py:module")
        summary_stage.generate_module_summaries.return_value = [module_summary]

        with patch("search.community_stage.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch(
                "chunking.community_remerge.remerge_chunks_with_communities"
            ) as mock_remerge:
                mock_remerge.return_value = chunks
                result = stage.run(chunks, "/project", config)

        regenerate_ids_fn.assert_called_once()
        assert module_summary in result

    def test_no_community_summaries_computed_in_run(self):
        """compute_community_summaries must never be called from run() —
        that's exclusively run_post_injection()'s job now."""
        stage, chunks, _, _, summary_stage, _ = self._make_stage_and_mocks()
        config = _make_config()

        with patch("search.community_stage.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch(
                "chunking.community_remerge.remerge_chunks_with_communities"
            ) as mock_remerge:
                mock_remerge.return_value = chunks
                stage.run(chunks, "/project", config)

        summary_stage.compute_community_summaries.assert_not_called()


class TestCommunityStageGracefulDegradation:
    """Community detection/remerge failure leaves chunks intact."""

    def test_detection_exception_continues_without_community_data(self):
        chunks = [_make_chunk("f.py:1-5:function:a")]
        build_graph_fn = Mock(side_effect=RuntimeError("graph build failed"))
        summary_stage = Mock()
        summary_stage.generate_module_summaries.return_value = []

        stage = CommunityStage(
            build_graph_fn=build_graph_fn,
            regenerate_ids_fn=Mock(),
            summary_stage=summary_stage,
        )
        config = _make_config()
        result = stage.run(chunks, "/project", config)

        # No exception propagated; chunks unchanged (no remerge without community_map)
        assert result == chunks
        summary_stage.compute_community_summaries.assert_not_called()

    def test_remerge_exception_continues_with_unmerged_chunks(self):
        chunks = [_make_chunk("f.py:1-5:function:a")]
        temp_graph = Mock()
        temp_graph.storage = Mock()
        build_graph_fn = Mock(return_value=temp_graph)
        summary_stage = Mock()
        summary_stage.generate_module_summaries.return_value = []

        stage = CommunityStage(
            build_graph_fn=build_graph_fn,
            regenerate_ids_fn=Mock(),
            summary_stage=summary_stage,
        )
        config = _make_config()

        with patch("search.community_stage.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch(
                "chunking.community_remerge.remerge_chunks_with_communities"
            ) as mock_remerge:
                mock_remerge.side_effect = RuntimeError("remerge failed")
                result = stage.run(chunks, "/project", config)

        # Chunks unchanged; no exception propagated
        assert result == chunks


class TestCommunityStagePostInjection:
    """run_post_injection(): authoritative detection on the resolved graph."""

    def _make_stage_and_mocks(self):
        graph_storage = Mock()
        graph_integration = Mock()
        graph_integration.storage = graph_storage

        indexer = Mock()
        indexer._graph = graph_integration
        indexer.storage_dir = "/fake/storage"

        embedder = Mock()

        summary_stage = Mock()

        stage = CommunityStage(
            build_graph_fn=Mock(),
            regenerate_ids_fn=Mock(),
            summary_stage=summary_stage,
            embedder=embedder,
            indexer=indexer,
        )
        return (
            stage,
            indexer,
            embedder,
            summary_stage,
            graph_storage,
            graph_integration,
        )

    def test_no_op_without_indexer(self):
        """Constructed without embedder/indexer (the five pre-existing
        construction sites in this file that only exercise run()) must no-op
        cleanly, returning 0."""
        stage = CommunityStage(
            build_graph_fn=Mock(),
            regenerate_ids_fn=Mock(),
            summary_stage=Mock(),
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]

        with patch("search.community_stage.get_search_config") as mock_get_cfg:
            mock_get_cfg.return_value = _make_config()
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 0

    def test_no_op_on_empty_chunks(self):
        stage, indexer, embedder, summary_stage, graph_storage, _ = (
            self._make_stage_and_mocks()
        )

        with patch("search.community_stage.get_search_config") as mock_get_cfg:
            mock_get_cfg.return_value = _make_config()
            result = stage.run_post_injection([], "myproject")

        assert result == 0
        graph_storage.store_community_map.assert_not_called()

    def test_detects_against_indexer_graph_storage_not_temp_graph(self):
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]
        community_map = {"f.py:1-5:function:a": 0}
        summary_stage.compute_community_summaries.return_value = []

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config()
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            stage.run_post_injection(chunks, "myproject")

        mock_detector_cls.assert_called_once_with(graph_storage)

    def test_community_map_persisted_to_real_graph_storage(self):
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]
        community_map = {"f.py:1-5:function:a": 0}
        summary_stage.compute_community_summaries.return_value = []

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config()
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            stage.run_post_injection(chunks, "myproject")

        graph_storage.store_community_map.assert_called_once_with(community_map)

    def test_summaries_computed_with_real_graph_integration(self):
        """compute_community_summaries must receive the real GraphIntegration
        (for centrality), not a temp graph."""
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]
        community_map = {"f.py:1-5:function:a": 0}
        summary_stage.compute_community_summaries.return_value = []

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config()
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            stage.run_post_injection(chunks, "myproject")

        summary_stage.compute_community_summaries.assert_called_once_with(
            chunks, community_map, graph_integration
        )

    def test_summaries_embedded_and_indexed_with_project_name(self):
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]
        community_map = {"f.py:1-5:function:a": 0}
        community_summary = _make_chunk("__community__/f_a_c0:0-0:community:f_a_c0")
        summary_stage.compute_community_summaries.return_value = [community_summary]

        embed_result = Mock()
        embed_result.metadata = {}
        embedder.embed_chunks.return_value = [embed_result]

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config()
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 1
        assert embed_result.metadata["project_name"] == "myproject"
        assert embed_result.metadata["content"] == community_summary.content
        indexer.add_embeddings.assert_called_once_with([embed_result])

    def test_no_op_when_detection_disabled(self):
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]

        with patch("search.community_stage.get_search_config") as mock_get_cfg:
            mock_get_cfg.return_value = _make_config(enable_community_detection=False)
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 0
        graph_storage.store_community_map.assert_not_called()
        embedder.embed_chunks.assert_not_called()

    def test_map_still_persisted_when_summaries_disabled(self):
        """enable_community_summaries=False must still persist the detected
        map — EgoGraphRetriever/SubgraphExtractor consume it independently of
        summaries — but skip building/embedding summary chunks."""
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]
        community_map = {"f.py:1-5:function:a": 0}

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config(enable_community_summaries=False)
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 0
        graph_storage.store_community_map.assert_called_once_with(community_map)
        summary_stage.compute_community_summaries.assert_not_called()

    def test_detection_exception_returns_zero(self):
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config()
            mock_detector_cls.side_effect = RuntimeError("boom")
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 0
        embedder.embed_chunks.assert_not_called()

    def test_embed_exception_returns_zero(self):
        stage, indexer, embedder, summary_stage, graph_storage, graph_integration = (
            self._make_stage_and_mocks()
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]
        community_map = {"f.py:1-5:function:a": 0}
        community_summary = _make_chunk("__community__/f_a_c0:0-0:community:f_a_c0")
        summary_stage.compute_community_summaries.return_value = [community_summary]
        embedder.embed_chunks.side_effect = RuntimeError("embed failed")

        with (
            patch("search.community_stage.get_search_config") as mock_get_cfg,
            patch("search.community_stage.CommunityDetector") as mock_detector_cls,
        ):
            mock_get_cfg.return_value = _make_config()
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 0
        indexer.add_embeddings.assert_not_called()

    def test_missing_graph_storage_returns_zero(self):
        indexer = Mock()
        indexer._graph = None
        embedder = Mock()
        stage = CommunityStage(
            build_graph_fn=Mock(),
            regenerate_ids_fn=Mock(),
            summary_stage=Mock(),
            embedder=embedder,
            indexer=indexer,
        )
        chunks = [_make_chunk("f.py:1-5:function:a")]

        with patch("search.community_stage.get_search_config") as mock_get_cfg:
            mock_get_cfg.return_value = _make_config()
            result = stage.run_post_injection(chunks, "myproject")

        assert result == 0
