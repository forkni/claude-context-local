"""Unit tests for JinaRerankerV3 and factory integration."""

from unittest.mock import MagicMock, patch

import torch

from search.neural_reranker import (
    JINA_V3_RERANKERS,
    JinaRerankerV3,
    create_reranker,
)
from search.reranker import SearchResult


class TestJinaRerankerV3:
    """Tests for JinaRerankerV3 class."""

    def test_lazy_loading(self):
        """Model should not load until first use."""
        reranker = JinaRerankerV3()
        assert reranker._model is None
        assert not reranker.is_loaded()

    def test_rerank_empty_candidates(self):
        """Empty candidates should return empty list."""
        reranker = JinaRerankerV3()
        result = reranker.rerank("query", [])
        assert result == []

    def test_rerank_maps_scores_correctly(self):
        """Reranking should map Jina scores back to SearchResult objects."""
        # Setup mock model with rerank method
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 1, "relevance_score": 0.95, "document": "code b"},
            {"index": 0, "relevance_score": 0.85, "document": "code a"},
        ]

        reranker = JinaRerankerV3()
        # Directly set the model to bypass lazy loading
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("find function", candidates, top_k=2)

        assert len(results) == 2
        # Results should be in order returned by Jina (b first, higher score)
        assert results[0].chunk_id == "b"
        assert results[0].score == 0.95
        assert results[0].metadata["reranker_score"] == 0.95
        assert results[1].chunk_id == "a"
        assert results[1].score == 0.85

    def test_rerank_uses_content_preview(self):
        """Reranking should use content_preview from metadata."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "code a"}
        ]

        reranker = JinaRerankerV3()
        # Directly set the model to bypass lazy loading
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            )
        ]

        reranker.rerank("test query", candidates, top_k=1)

        # Verify rerank was called with content_preview (with ID prefix)
        mock_model.rerank.assert_called_once()
        call_args = mock_model.rerank.call_args
        assert call_args[0][0] == "test query"  # Query
        assert call_args[0][1] == ["ID: a\ncode a"]  # Documents with ID prefix

    def test_rerank_fallback_to_chunk_id(self):
        """Should use chunk_id when content_preview is missing."""
        mock_model = MagicMock()
        mock_model.rerank.return_value = [
            {"index": 0, "relevance_score": 0.9, "document": "chunk_a"}
        ]

        reranker = JinaRerankerV3()
        # Directly set the model to bypass lazy loading
        reranker._model = mock_model

        candidates = [
            SearchResult(chunk_id="chunk_a", score=1.0, metadata={})  # No content
        ]

        reranker.rerank("test query", candidates, top_k=1)

        # Verify rerank was called with chunk_id as fallback (with ID prefix)
        call_args = mock_model.rerank.call_args
        assert call_args[0][1] == ["ID: chunk_a\nchunk_a"]  # ID prefix + chunk_id

    @patch("transformers.AutoModel.from_pretrained")
    def test_cleanup_releases_resources(self, mock_model_class):
        """Cleanup should release model and tokenizer."""
        mock_model_class.return_value = MagicMock()

        reranker = JinaRerankerV3()
        _ = reranker.model  # Trigger loading
        assert reranker.is_loaded()

        reranker.cleanup()
        assert not reranker.is_loaded()
        assert reranker._model is None

    def test_device_auto_detection(self):
        """Device should be auto-detected when not specified."""
        reranker = JinaRerankerV3()
        if torch.cuda.is_available():
            assert reranker.device == "cuda"
        else:
            assert reranker.device == "cpu"

    def test_custom_device(self):
        """Custom device should be respected."""
        reranker = JinaRerankerV3(device="cpu")
        assert reranker.device == "cpu"

    def test_vram_usage_when_not_loaded(self):
        """VRAM usage should be 0 when model not loaded."""
        reranker = JinaRerankerV3()
        assert reranker.get_vram_usage() == 0.0

    def test_rerank_handles_numpy_indices(self):
        """Should handle numpy.int64 indices from Jina model."""
        import numpy as np

        mock_model = MagicMock()
        # Jina returns numpy.int64 indices, not Python int
        mock_model.rerank.return_value = [
            {"index": np.int64(1), "relevance_score": 0.95, "document": "code b"},
            {"index": np.int64(0), "relevance_score": 0.85, "document": "code a"},
        ]

        reranker = JinaRerankerV3()
        reranker._model = mock_model

        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("test query", candidates, top_k=2)

        # Should successfully map numpy.int64 indices to candidates
        assert len(results) == 2
        assert results[0].chunk_id == "b"
        assert results[0].score == 0.95
        assert results[1].chunk_id == "a"
        assert results[1].score == 0.85

    @patch("transformers.AutoModel.from_pretrained")
    @patch("transformers.AutoConfig.from_pretrained")
    def test_model_property_resets_on_validation_failure(
        self, mock_config_class, mock_from_pretrained
    ):
        """Model should be reset to None if rerank attribute check fails."""
        mock_config = MagicMock()
        mock_config_class.return_value = mock_config

        # Return a model WITHOUT rerank method (but with to/eval)
        mock_model = MagicMock(spec=["to", "eval"])  # Has to/eval but NOT rerank
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = mock_model
        mock_from_pretrained.return_value = mock_model

        reranker = JinaRerankerV3()

        import pytest

        with pytest.raises(RuntimeError, match="does not support rerank"):
            _ = reranker.model

        # Critical: _model should be None so next access retries
        assert reranker._model is None


class TestCreateRerankerFactoryJina:
    """Tests for create_reranker factory with Jina models."""

    def test_creates_jina_v3_reranker(self):
        """Should create JinaRerankerV3 for Jina v3 model."""
        reranker = create_reranker("jinaai/jina-reranker-v3")
        assert isinstance(reranker, JinaRerankerV3)
        assert reranker.model_name == "jinaai/jina-reranker-v3"

    def test_device_passed_to_jina_reranker(self):
        """Device parameter should be passed through to JinaRerankerV3."""
        reranker = create_reranker("jinaai/jina-reranker-v3", device="cpu")
        assert reranker.device == "cpu"

    def test_all_jina_models_in_registry(self):
        """All models in JINA_V3_RERANKERS should create JinaRerankerV3."""
        for model_name in JINA_V3_RERANKERS:
            reranker = create_reranker(model_name)
            assert isinstance(reranker, JinaRerankerV3)
            assert reranker.model_name == model_name
