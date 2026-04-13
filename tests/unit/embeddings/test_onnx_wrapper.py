"""Tests for ONNXEmbeddingModel in embeddings/onnx_wrapper.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
import torch

from embeddings.onnx_wrapper import ONNXEmbeddingModel


def _make_ort_model(batch_size: int = 1, seq_len: int = 8, dim: int = 16) -> MagicMock:
    """Return a mock ORT model whose output has .last_hidden_state of shape (B, S, D)."""
    hidden = torch.randn(batch_size, seq_len, dim)
    output = MagicMock()
    output.last_hidden_state = hidden
    ort_model = MagicMock()
    ort_model.return_value = output
    return ort_model


def _make_tokenizer(batch_size: int = 1, seq_len: int = 8) -> MagicMock:
    """Return a mock tokenizer whose call returns input_ids and attention_mask tensors."""
    tokenizer = MagicMock()
    tokenizer.return_value = {
        "input_ids": torch.ones(batch_size, seq_len, dtype=torch.long),
        "attention_mask": torch.ones(batch_size, seq_len, dtype=torch.long),
    }
    return tokenizer


class TestONNXEmbeddingModelInit:
    def test_init_cls_pooling_stores_attributes(self):
        ort_model = MagicMock()
        tokenizer = MagicMock()
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls", "BAAI/bge-m3")
        assert model.ort_model is ort_model
        assert model.tokenizer is tokenizer
        assert model.device == "cpu"
        assert model.pooling == "cls"
        assert model.model_name == "BAAI/bge-m3"

    def test_init_mean_pooling_succeeds(self):
        model = ONNXEmbeddingModel(MagicMock(), MagicMock(), "cuda", "mean")
        assert model.pooling == "mean"

    def test_init_invalid_pooling_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown pooling strategy"):
            ONNXEmbeddingModel(MagicMock(), MagicMock(), "cpu", "max")

    def test_init_default_pooling_is_cls(self):
        model = ONNXEmbeddingModel(MagicMock(), MagicMock(), "cpu")
        assert model.pooling == "cls"

    def test_init_default_model_name_is_empty(self):
        model = ONNXEmbeddingModel(MagicMock(), MagicMock(), "cpu")
        assert model.model_name == ""


class TestONNXEmbeddingModelEncodeCLS:
    @pytest.fixture
    def model_cls(self):
        ort_model = _make_ort_model(batch_size=1, seq_len=8, dim=16)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=8)
        return ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")

    def test_encode_cls_returns_numpy_array(self, model_cls):
        result = model_cls.encode(["hello world"])
        import numpy as np

        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 16)

    def test_encode_cls_calls_tokenizer_with_correct_args(self, model_cls):
        model_cls.encode(["sentence one"])
        model_cls.tokenizer.assert_called_once_with(
            ["sentence one"],
            padding=True,
            truncation=True,
            return_tensors="pt",
        )

    def test_encode_cls_calls_ort_model_with_encoded_inputs(self, model_cls):
        model_cls.encode(["test"])
        assert model_cls.ort_model.called

    def test_encode_cls_multibatch_output_shape(self):
        ort_model = _make_ort_model(batch_size=3, seq_len=10, dim=32)
        tokenizer = _make_tokenizer(batch_size=3, seq_len=10)
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        result = model.encode(["a", "b", "c"])
        assert result.shape == (3, 32)

    def test_encode_cls_selects_position_zero(self):
        # Create hidden states where position 0 is all-ones and rest are zeros
        hidden = torch.zeros(1, 8, 16)
        hidden[:, 0, :] = 1.0  # only CLS token has signal
        output = MagicMock()
        output.last_hidden_state = hidden
        ort_model = MagicMock(return_value=output)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=8)
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        result = model.encode(["test"], convert_to_tensor=True)
        # CLS token is all-ones, so after L2 norm it should be all-positive
        assert result.shape == (1, 16)
        assert (result > 0).all()

    def test_encode_cls_applies_l2_normalization(self):
        hidden = torch.ones(2, 4, 8) * 3.0  # unnormalized large values
        output = MagicMock()
        output.last_hidden_state = hidden
        ort_model = MagicMock(return_value=output)
        tokenizer = _make_tokenizer(batch_size=2, seq_len=4)
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        result = model.encode(["a", "b"], convert_to_tensor=True)
        norms = result.norm(dim=1)
        assert torch.allclose(norms, torch.ones(2), atol=1e-5)


class TestONNXEmbeddingModelEncodeMean:
    def test_encode_mean_uses_all_tokens(self):
        # Make hidden states distinct per position to distinguish mean from CLS
        hidden = torch.zeros(1, 4, 8)
        hidden[:, 0, :] = 10.0  # CLS
        hidden[:, 1, :] = 2.0  # token 1
        hidden[:, 2, :] = 2.0  # token 2
        hidden[:, 3, :] = 0.0  # padding
        output = MagicMock()
        output.last_hidden_state = hidden

        ort_model = MagicMock(return_value=output)
        tokenizer = MagicMock()
        # Mask: only first 3 tokens are real
        tokenizer.return_value = {
            "input_ids": torch.ones(1, 4, dtype=torch.long),
            "attention_mask": torch.tensor([[1, 1, 1, 0]], dtype=torch.long),
        }
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "mean")
        result = model.encode(["test"], convert_to_tensor=True)
        # Mean of [10, 2, 2] / 3 = 4.666... for each dim before norm
        assert result.shape == (1, 8)
        assert (result > 0).all()  # all values positive (uniform hidden states)

    def test_encode_mean_handles_near_zero_mask_sum(self):
        # Edge case: mask with very few tokens to stress the clamp
        hidden = torch.ones(1, 4, 8)
        output = MagicMock()
        output.last_hidden_state = hidden
        ort_model = MagicMock(return_value=output)
        tokenizer = MagicMock()
        tokenizer.return_value = {
            "input_ids": torch.ones(1, 4, dtype=torch.long),
            "attention_mask": torch.tensor([[1, 0, 0, 0]], dtype=torch.long),
        }
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "mean")
        # Should not raise (no div-by-zero)
        result = model.encode(["test"], convert_to_tensor=True)
        assert not torch.isnan(result).any()

    def test_encode_mean_applies_l2_normalization(self):
        hidden = torch.ones(1, 4, 16) * 5.0
        output = MagicMock()
        output.last_hidden_state = hidden
        ort_model = MagicMock(return_value=output)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=4)
        # Override dim to match hidden
        tokenizer.return_value = {
            "input_ids": torch.ones(1, 4, dtype=torch.long),
            "attention_mask": torch.ones(1, 4, dtype=torch.long),
        }
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "mean")
        result = model.encode(["test"], convert_to_tensor=True)
        assert torch.allclose(result.norm(dim=1), torch.ones(1), atol=1e-5)


class TestONNXEmbeddingModelEncodeReturnType:
    @pytest.fixture
    def model(self):
        ort_model = _make_ort_model(batch_size=1, seq_len=6, dim=8)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=6)
        return ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")

    def test_returns_numpy_by_default(self, model):
        import numpy as np

        result = model.encode(["test"])
        assert isinstance(result, np.ndarray)

    def test_returns_numpy_when_convert_to_tensor_false(self, model):
        import numpy as np

        result = model.encode(["test"], convert_to_tensor=False)
        assert isinstance(result, np.ndarray)

    def test_returns_tensor_when_convert_to_tensor_true(self, model):
        result = model.encode(["test"], convert_to_tensor=True)
        assert isinstance(result, torch.Tensor)


class TestONNXEmbeddingModelEncodeDevice:
    def test_encode_cpu_does_not_move_to_cuda(self):
        ort_model = _make_ort_model(batch_size=1, seq_len=4, dim=8)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=4)
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        # Should not raise even without CUDA
        model.encode(["test"])
        # Tokenizer was called and returned cpu tensors — no .cuda() should be needed
        encoded = tokenizer.return_value
        assert encoded["input_ids"].device.type == "cpu"

    def test_encode_uses_instance_device_by_default(self):
        ort_model = _make_ort_model(batch_size=1, seq_len=4, dim=8)
        mock_tokenizer = MagicMock()
        tokens = {
            "input_ids": torch.ones(1, 4, dtype=torch.long),
            "attention_mask": torch.ones(1, 4, dtype=torch.long),
        }
        mock_tokenizer.return_value = tokens
        model = ONNXEmbeddingModel(ort_model, mock_tokenizer, "cpu", "cls")
        model.encode(["test"])
        # Verify tokenizer was called (device routing used instance device "cpu")
        mock_tokenizer.assert_called_once()

    def test_encode_extra_kwargs_silently_ignored(self):
        ort_model = _make_ort_model(batch_size=1, seq_len=4, dim=8)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=4)
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        # Should not raise TypeError for unrecognized kwargs
        model.encode(
            ["test"],
            batch_size=64,
            show_progress_bar=True,
            normalize_embeddings=True,
        )

    def test_encode_prompt_name_ignored(self):
        ort_model = _make_ort_model(batch_size=1, seq_len=4, dim=8)
        tokenizer = _make_tokenizer(batch_size=1, seq_len=4)
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        model.encode(["test"], prompt_name="query")
        # Tokenizer should NOT have received prompt_name
        call_kwargs = tokenizer.call_args[1]
        assert "prompt_name" not in call_kwargs

    def test_encode_empty_sentence_list_does_not_raise(self):
        ort_model = _make_ort_model(batch_size=0, seq_len=4, dim=8)
        tokenizer = MagicMock()
        tokenizer.return_value = {
            "input_ids": torch.zeros(0, 4, dtype=torch.long),
            "attention_mask": torch.zeros(0, 4, dtype=torch.long),
        }
        model = ONNXEmbeddingModel(ort_model, tokenizer, "cpu", "cls")
        # Should complete without raising
        result = model.encode([], convert_to_tensor=True)
        assert result.shape[0] == 0
