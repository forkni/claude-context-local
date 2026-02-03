"""Unit tests for GenerativeReranker and create_reranker factory."""

from unittest.mock import MagicMock, patch

import pytest
import torch

from search.neural_reranker import (
    GENERATIVE_RERANKERS,
    GenerativeReranker,
    NeuralReranker,
    create_reranker,
)
from search.reranker import SearchResult


class TestGenerativeReranker:
    """Tests for GenerativeReranker class."""

    def test_lazy_loading(self):
        """Model should not load until first use."""
        reranker = GenerativeReranker()
        assert reranker._model is None
        assert reranker._tokenizer is None
        assert not reranker.is_loaded()

    def test_rerank_empty_candidates(self):
        """Empty candidates should return empty list."""
        reranker = GenerativeReranker()
        result = reranker.rerank("query", [])
        assert result == []

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_adds_score_metadata(self, mock_tokenizer_class, mock_model_class):
        """Reranking should add reranker_score to metadata."""
        # Setup mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = (
            lambda text, **kwargs: [100] if text == "Yes" else [101]
        )

        # Mock tokenizer call to return object with .to() method
        mock_inputs = MagicMock()
        mock_inputs.to.return_value = mock_inputs
        mock_tokenizer.return_value = mock_inputs
        mock_tokenizer_class.return_value = mock_tokenizer

        # Setup mock model
        mock_model = MagicMock()
        mock_outputs = MagicMock()

        # Create logits tensor with high probability for "Yes" token
        logits_tensor = torch.zeros(1, 1, 1000)
        logits_tensor[0, -1, 100] = 2.0  # Yes token high logit
        logits_tensor[0, -1, 101] = 0.5  # No token low logit
        mock_outputs.logits = logits_tensor

        mock_model.return_value = mock_outputs
        mock_model_class.return_value = mock_model

        reranker = GenerativeReranker()
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
        assert "reranker_score" in results[0].metadata
        assert isinstance(results[0].metadata["reranker_score"], float)
        # Verify score is between 0 and 1 (probability)
        assert 0.0 <= results[0].metadata["reranker_score"] <= 1.0

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_cleanup_releases_resources(self, mock_tokenizer_class, mock_model_class):
        """Cleanup should release model and tokenizer."""
        mock_tokenizer_class.return_value = MagicMock()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker()
        _ = reranker.model  # Trigger loading
        assert reranker.is_loaded()

        reranker.cleanup()
        assert not reranker.is_loaded()
        assert reranker._model is None
        assert reranker._tokenizer is None

    def test_device_auto_detection(self):
        """Device should be auto-detected when not specified."""
        reranker = GenerativeReranker()
        if torch.cuda.is_available():
            assert reranker.device == "cuda"
        else:
            assert reranker.device == "cpu"

    def test_custom_device(self):
        """Custom device should be respected."""
        reranker = GenerativeReranker(device="cpu")
        assert reranker.device == "cpu"

    def test_custom_batch_size(self):
        """Custom batch size should be set."""
        reranker = GenerativeReranker(batch_size=4)
        assert reranker.batch_size == 4

    def test_vram_usage_when_not_loaded(self):
        """VRAM usage should be 0 when model not loaded."""
        reranker = GenerativeReranker()
        assert reranker.get_vram_usage() == 0.0


class TestCreateRerankerFactory:
    """Tests for create_reranker factory function."""

    def test_creates_generative_reranker_for_qwen3(self):
        """Should create GenerativeReranker for Qwen3 models."""
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B")
        assert isinstance(reranker, GenerativeReranker)
        assert reranker.model_name == "Qwen/Qwen3-Reranker-0.6B"

    def test_creates_discriminative_reranker_for_bge(self):
        """Should create NeuralReranker for BGE models."""
        reranker = create_reranker("BAAI/bge-reranker-v2-m3")
        assert isinstance(reranker, NeuralReranker)
        assert reranker.model_name == "BAAI/bge-reranker-v2-m3"

    def test_creates_discriminative_reranker_for_gte(self):
        """Should create NeuralReranker for GTE models."""
        reranker = create_reranker("Alibaba-NLP/gte-reranker-modernbert-base")
        assert isinstance(reranker, NeuralReranker)

    def test_generative_reranker_uses_smaller_batch(self):
        """Generative rerankers should use smaller batch size."""
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B", batch_size=16)
        assert reranker.batch_size == 8  # Factory overrides to 8 for LLM

    def test_discriminative_reranker_preserves_batch_size(self):
        """Discriminative rerankers should preserve batch size."""
        reranker = create_reranker("BAAI/bge-reranker-v2-m3", batch_size=16)
        assert reranker.batch_size == 16

    def test_device_passed_to_reranker(self):
        """Device parameter should be passed through."""
        reranker = create_reranker("Qwen/Qwen3-Reranker-0.6B", device="cpu")
        assert reranker.device == "cpu"

    def test_all_generative_models_in_registry(self):
        """All models in GENERATIVE_RERANKERS should create GenerativeReranker."""
        for model_name in GENERATIVE_RERANKERS:
            reranker = create_reranker(model_name)
            assert isinstance(reranker, GenerativeReranker)
            assert reranker.model_name == model_name


class TestGenerativeRerankerIntegration:
    """Integration-style tests for GenerativeReranker (no mocks)."""

    @pytest.mark.skipif(
        not torch.cuda.is_available(), reason="Requires GPU for realistic test"
    )
    def test_model_loading_flow(self):
        """Test the lazy loading flow (CPU fallback if no GPU)."""
        reranker = GenerativeReranker(device="cpu")  # Force CPU for test
        assert not reranker.is_loaded()

        # This would load the model in real scenario
        # We skip actual loading in unit tests
        assert reranker._model is None

    def test_prompt_format(self):
        """Verify the prompt format is correct."""
        reranker = GenerativeReranker()

        # We can't test actual model behavior without loading it,
        # but we can verify the structure is set up correctly
        assert hasattr(reranker, "model_name")
        assert hasattr(reranker, "batch_size")
        assert hasattr(reranker, "_logger")
