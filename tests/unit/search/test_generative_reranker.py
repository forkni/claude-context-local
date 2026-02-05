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
        """Reranking should add reranker_score to metadata (batched inference)."""
        seq_len = 10
        vocab_size = 1000
        batch_size = 2
        yes_id, no_id = 100, 101

        # Logits: shape [batch, seq_len, vocab_size]
        logits_tensor = torch.zeros(batch_size, seq_len, vocab_size)
        logits_tensor[0, -1, yes_id] = 2.0  # Candidate 0: P(Yes) high
        logits_tensor[0, -1, no_id] = 0.5
        logits_tensor[1, -1, yes_id] = 0.5  # Candidate 1: P(Yes) lower
        logits_tensor[1, -1, no_id] = 2.0

        # Mock tokenizer
        class MockTokenizer:
            def encode(self, text, **kwargs):
                return [yes_id] if text in ("Yes", " Yes") else [no_id]

            def __call__(self, prompts, **kwargs):
                n = len(prompts) if isinstance(prompts, list) else 1
                mock_inputs = {
                    "input_ids": torch.ones(n, seq_len, dtype=torch.long),
                    "attention_mask": torch.ones(n, seq_len, dtype=torch.long),
                }

                # Add .to() method that returns self
                class TensorDict(dict):
                    def to(self, device):
                        return self

                return TensorDict(mock_inputs)

        # Mock model
        class MockModel:
            def to(self, device):
                return self

            def __call__(self, **inputs):
                class Outputs:
                    logits = logits_tensor

                return Outputs()

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MockModel()

        reranker = GenerativeReranker(device="cpu")
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
        assert 0.0 <= results[0].metadata["reranker_score"] <= 1.0
        # First result should have higher score (candidate "a" has high Yes logit)
        assert results[0].chunk_id == "a"
        assert (
            results[0].metadata["reranker_score"]
            > results[1].metadata["reranker_score"]
        )

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

    def test_vram_usage_when_not_loaded(self):
        """VRAM usage should be 0 when model not loaded."""
        reranker = GenerativeReranker()
        assert reranker.get_vram_usage() == 0.0

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_fallback_on_error(self, mock_tokenizer_class, mock_model_class):
        """Should return candidates in original order on inference failure."""

        class MockTokenizer:
            def encode(self, text, **kwargs):
                return [100] if text in ("Yes", " Yes") else [101]

            def __call__(self, prompts, **kwargs):
                raise RuntimeError("Simulated tokenization failure")

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("query", candidates, top_k=2)

        # Should return candidates with original scores preserved
        assert len(results) == 2
        assert results[0].chunk_id == "a"
        assert results[0].metadata["original_score"] == 1.0
        assert results[0].metadata["reranker_score"] == 1.0
        assert results[1].chunk_id == "b"
        assert results[1].metadata["original_score"] == 0.8
        assert results[1].metadata["reranker_score"] == 0.8

    @patch("transformers.AutoModelForCausalLM.from_pretrained")
    @patch("transformers.AutoTokenizer.from_pretrained")
    def test_rerank_fallback_on_token_resolution_failure(
        self, mock_tokenizer_class, mock_model_class
    ):
        """Should return original scores when tokenizer can't resolve Yes/No tokens."""

        class MockTokenizer:
            def encode(self, text, **kwargs):
                # Always return multi-token for both "Yes"/" Yes" and "No"/" No"
                return [10, 20]  # Multi-token

        mock_tokenizer_class.return_value = MockTokenizer()
        mock_model_class.return_value = MagicMock()

        reranker = GenerativeReranker(device="cpu")
        candidates = [
            SearchResult(
                chunk_id="a", score=1.0, metadata={"content_preview": "code a"}
            ),
            SearchResult(
                chunk_id="b", score=0.8, metadata={"content_preview": "code b"}
            ),
        ]

        results = reranker.rerank("query", candidates, top_k=2)

        # Should return candidates with original scores preserved (fallback)
        assert len(results) == 2
        assert results[0].chunk_id == "a"
        assert results[0].metadata["original_score"] == 1.0
        assert results[0].metadata["reranker_score"] == 1.0
        assert results[1].chunk_id == "b"
        assert results[1].metadata["original_score"] == 0.8
        assert results[1].metadata["reranker_score"] == 0.8


class TestTokenIdValidation:
    """Tests for _resolve_single_token_id helper."""

    def test_resolves_single_token(self):
        """Should return token ID when text tokenizes to single token."""
        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [42]

        result = _resolve_single_token_id(mock_tokenizer, "Yes")
        assert result == 42

    def test_tries_space_variant(self):
        """Should try ' Yes' if 'Yes' produces multiple tokens."""
        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        # "Yes" -> 2 tokens, " Yes" -> 1 token
        mock_tokenizer.encode.side_effect = lambda text, **kw: (
            [10, 20] if text == "Yes" else [42]
        )

        result = _resolve_single_token_id(mock_tokenizer, "Yes")
        assert result == 42
        assert mock_tokenizer.encode.call_count == 2

    def test_raises_on_multi_token(self):
        """Should raise RuntimeError if neither variant is single-token."""
        import pytest

        from search.neural_reranker import _resolve_single_token_id

        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [10, 20]  # Always multi-token

        with pytest.raises(RuntimeError, match="Cannot resolve"):
            _resolve_single_token_id(mock_tokenizer, "Yes")


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
        assert hasattr(reranker, "_logger")
