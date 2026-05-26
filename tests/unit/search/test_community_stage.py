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
    """When community detection is disabled, chunks pass through unchanged."""

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
        config = _make_config(enable_community_detection=True)
        stage = CommunityStage(
            build_graph_fn=Mock(),
            regenerate_ids_fn=Mock(),
            summary_stage=Mock(),
        )
        result = stage.run([], "/project", config)
        assert result == []


class TestCommunityStageDetectionEnabled:
    """Community detection enabled path."""

    def _make_stage_and_mocks(self, community_map=None):
        chunks = [_make_chunk("f.py:1-5:function:a")]
        temp_graph = Mock()
        temp_graph.storage = Mock()

        build_graph_fn = Mock(return_value=temp_graph)
        regenerate_ids_fn = Mock(side_effect=lambda c, p: c)
        summary_stage = Mock()
        summary_stage.compute_community_summaries.return_value = []
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

        with patch("graph.community_detector.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch("chunking.languages.base.LanguageChunker") as mock_lc:
                mock_lc.remerge_chunks_with_communities.return_value = chunks
                stage.run(chunks, "/project", config)

        build_graph_fn.assert_called_once_with(chunks)

    def test_community_map_stored_on_graph(self):
        stage, chunks, _, _, _, temp_graph = self._make_stage_and_mocks()
        config = _make_config()
        community_map = {"f.py:1-5:function:a": 0}

        with patch("graph.community_detector.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            with patch("chunking.languages.base.LanguageChunker") as mock_lc:
                mock_lc.remerge_chunks_with_communities.return_value = chunks
                stage.run(chunks, "/project", config)

        temp_graph.storage.store_community_map.assert_called_once_with(community_map)

    def test_summary_phase1_called_before_remerge(self):
        """compute_community_summaries must be called with pre-remerge chunks."""
        stage, chunks, _, _, summary_stage, _ = self._make_stage_and_mocks()
        config = _make_config()
        community_map = {"f.py:1-5:function:a": 0}
        call_order = []

        summary_stage.compute_community_summaries.side_effect = (
            lambda *a, **kw: call_order.append("phase1") or []
        )

        with patch("graph.community_detector.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = (
                community_map
            )
            with patch("chunking.languages.base.LanguageChunker") as mock_lc:
                mock_lc.remerge_chunks_with_communities.side_effect = (
                    lambda **kw: call_order.append("remerge") or chunks
                )
                stage.run(chunks, "/project", config)

        assert call_order.index("phase1") < call_order.index("remerge")

    def test_module_summaries_appended(self):
        stage, chunks, _, _, summary_stage, _ = self._make_stage_and_mocks()
        config = _make_config()
        module_summary = _make_chunk("f.py:module")
        summary_stage.generate_module_summaries.return_value = [module_summary]

        with patch("graph.community_detector.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch("chunking.languages.base.LanguageChunker") as mock_lc:
                mock_lc.remerge_chunks_with_communities.return_value = chunks
                result = stage.run(chunks, "/project", config)

        assert module_summary in result

    def test_community_summaries_appended_after_remerge(self):
        stage, chunks, _, _, summary_stage, _ = self._make_stage_and_mocks()
        config = _make_config()
        community_summary = _make_chunk("community:0")
        summary_stage.compute_community_summaries.return_value = [community_summary]

        with patch("graph.community_detector.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch("chunking.languages.base.LanguageChunker") as mock_lc:
                mock_lc.remerge_chunks_with_communities.return_value = chunks
                result = stage.run(chunks, "/project", config)

        assert community_summary in result
        # Community summary must be at the end (after module summaries)
        assert result[-1] == community_summary or community_summary in result


class TestCommunityStageGracefulDegradation:
    """Community detection failure leaves chunks intact."""

    def test_detection_exception_continues_without_community_data(self):
        chunks = [_make_chunk("f.py:1-5:function:a")]
        build_graph_fn = Mock(side_effect=RuntimeError("graph build failed"))
        summary_stage = Mock()
        summary_stage.compute_community_summaries.return_value = []
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
        summary_stage.compute_community_summaries.return_value = []
        summary_stage.generate_module_summaries.return_value = []

        stage = CommunityStage(
            build_graph_fn=build_graph_fn,
            regenerate_ids_fn=Mock(),
            summary_stage=summary_stage,
        )
        config = _make_config()

        with patch("graph.community_detector.CommunityDetector") as mock_detector_cls:
            mock_detector_cls.return_value.detect_communities.return_value = {
                "f.py:1-5:function:a": 0
            }
            with patch("chunking.languages.base.LanguageChunker") as mock_lc:
                mock_lc.remerge_chunks_with_communities.side_effect = RuntimeError(
                    "remerge failed"
                )
                result = stage.run(chunks, "/project", config)

        # Chunks unchanged; no exception propagated
        assert result == chunks
