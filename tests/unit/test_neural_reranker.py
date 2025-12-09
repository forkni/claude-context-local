"""Unit tests for NeuralReranker."""

from unittest.mock import MagicMock, patch

from search.neural_reranker import NeuralReranker
from search.reranker import SearchResult


class TestNeuralReranker:
    """Tests for NeuralReranker class."""

    def test_lazy_loading(self):
        """Model should not load until first use."""
        reranker = NeuralReranker()
        assert reranker._model is None
        assert not reranker.is_loaded()

    def test_rerank_empty_candidates(self):
        """Empty candidates should return empty list."""
        reranker = NeuralReranker()
        result = reranker.rerank("query", [])
        assert result == []

    @patch("sentence_transformers.CrossEncoder")
    def test_rerank_adds_score_metadata(self, mock_cross_encoder):
        """Reranking should add reranker_score to metadata."""
        # Setup mock
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.9, 0.5, 0.7]
        mock_cross_encoder.return_value = mock_model

        reranker = NeuralReranker()
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
            SearchResult(
                chunk_id="c", score=0.6, metadata={"content_preview": "code c"}
            ),
        ]

        results = reranker.rerank("find function", candidates, top_k=2)

        assert len(results) == 2
        assert results[0].chunk_id == "a"  # Highest score 0.9
        assert results[1].chunk_id == "c"  # Second highest 0.7
        assert "reranker_score" in results[0].metadata
        assert results[0].metadata["reranker_score"] == 0.9
        assert results[1].metadata["reranker_score"] == 0.7

    def test_cleanup_releases_model(self):
        """Cleanup should release model reference."""
        reranker = NeuralReranker()
        reranker._model = MagicMock()  # Simulate loaded model
        reranker.cleanup()
        assert reranker._model is None
        assert not reranker.is_loaded()

    @patch("sentence_transformers.CrossEncoder")
    def test_rerank_uses_content_preview(self, mock_cross_encoder):
        """Reranking should use content_preview from metadata."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]
        mock_cross_encoder.return_value = mock_model

        reranker = NeuralReranker()
        candidates = [
            SearchResult(
                chunk_id="test:1-10:function:foo",
                score=1.0,
                metadata={"content_preview": "def foo(): pass"},
            ),
        ]

        _ = reranker.rerank("function definition", candidates, top_k=1)

        # Verify content_preview was used
        call_args = mock_model.predict.call_args[0][0]
        assert call_args[0] == ("function definition", "def foo(): pass")

    @patch("sentence_transformers.CrossEncoder")
    def test_rerank_fallback_to_chunk_id(self, mock_cross_encoder):
        """Reranking should fallback to chunk_id if no content_preview."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]
        mock_cross_encoder.return_value = mock_model

        reranker = NeuralReranker()
        candidates = [
            SearchResult(chunk_id="test:1-10:function:foo", score=1.0, metadata={}),
        ]

        _ = reranker.rerank("function", candidates, top_k=1)

        # Verify chunk_id was used as fallback
        call_args = mock_model.predict.call_args[0][0]
        assert call_args[0] == ("function", "test:1-10:function:foo")

    @patch("search.neural_reranker.torch")
    def test_get_vram_usage_no_gpu(self, mock_torch):
        """VRAM usage should return 0.0 if no GPU available."""
        mock_torch.cuda.is_available.return_value = False

        reranker = NeuralReranker()
        reranker._model = MagicMock()  # Model loaded but no GPU

        assert reranker.get_vram_usage() == 0.0

    @patch("search.neural_reranker.torch")
    def test_get_vram_usage_not_loaded(self, mock_torch):
        """VRAM usage should return 0.0 if model not loaded."""
        mock_torch.cuda.is_available.return_value = True

        reranker = NeuralReranker()
        assert reranker.get_vram_usage() == 0.0

    @patch("search.neural_reranker.torch")
    def test_device_auto_detection_cpu(self, mock_torch):
        """Device should default to CPU when no GPU available."""
        with mock_torch:
            mock_torch.cuda.is_available.return_value = False

            reranker = NeuralReranker()
            assert reranker.device == "cpu"

    @patch("search.neural_reranker.torch")
    def test_device_auto_detection_cuda(self, mock_torch):
        """Device should default to CUDA when GPU available."""
        with mock_torch:
            mock_torch.cuda.is_available.return_value = True

            reranker = NeuralReranker()
            assert reranker.device == "cuda"

    def test_device_manual_override(self):
        """Device can be manually set."""
        reranker = NeuralReranker(device="cpu")
        assert reranker.device == "cpu"

    @patch("sentence_transformers.CrossEncoder")
    def test_batch_size_parameter(self, mock_cross_encoder):
        """Batch size parameter should be passed to predict."""
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.8]
        mock_cross_encoder.return_value = mock_model

        reranker = NeuralReranker(batch_size=32)
        candidates = [
            SearchResult(
                chunk_id="test", score=1.0, metadata={"content_preview": "code"}
            ),
        ]

        reranker.rerank("query", candidates, top_k=1)

        # Verify batch_size was used
        assert mock_model.predict.call_args[1]["batch_size"] == 32
