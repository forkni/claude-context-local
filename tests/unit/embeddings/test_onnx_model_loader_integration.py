"""Tests for the ONNX integration methods in embeddings/model_loader.py.

Covers _should_use_onnx(), _load_onnx(), and the ONNX fast path in load().
Follows the same patterns as tests/unit/embeddings/test_model_loader.py.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from embeddings.model_cache import ModelCacheManager
from embeddings.model_loader import ModelLoader


class TestShouldUseOnnx:
    """Tests for ModelLoader._should_use_onnx()."""

    @pytest.fixture
    def temp_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def model_config_basic(self):
        return {"model_type": "bert", "dimension": 768}

    @pytest.fixture
    def model_loader(self, temp_cache_dir, model_config_basic):
        cache_manager = ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config_basic,
        )
        return ModelLoader(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            device="auto",
            cache_manager=cache_manager,
            model_config_getter=lambda: model_config_basic,
        )

    def _make_config(self, use_onnx: bool) -> MagicMock:
        config = MagicMock()
        config.performance.use_onnx = use_onnx
        return config

    def test_returns_true_when_enabled_and_eligible(self, model_loader):
        with patch(
            "mcp_server.utils.config_helpers.get_config_via_service_locator",
            return_value=self._make_config(True),
        ):
            assert model_loader._should_use_onnx() is True

    def test_returns_false_when_disabled(self, model_loader):
        with patch(
            "mcp_server.utils.config_helpers.get_config_via_service_locator",
            return_value=self._make_config(False),
        ):
            assert model_loader._should_use_onnx() is False

    def test_returns_false_when_trust_remote_code(self, temp_cache_dir):
        trust_config = {"trust_remote_code": True, "dimension": 768}
        cache_manager = ModelCacheManager(
            model_name="nomic-ai/CodeRankEmbed",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: trust_config,
        )
        loader = ModelLoader(
            model_name="nomic-ai/CodeRankEmbed",
            cache_dir=str(temp_cache_dir),
            device="auto",
            cache_manager=cache_manager,
            model_config_getter=lambda: trust_config,
        )
        with patch(
            "mcp_server.utils.config_helpers.get_config_via_service_locator",
            return_value=self._make_config(True),
        ):
            assert loader._should_use_onnx() is False

    def test_returns_false_when_config_raises_exception(self, model_loader):
        with patch(
            "mcp_server.utils.config_helpers.get_config_via_service_locator",
            side_effect=RuntimeError("service locator down"),
        ):
            assert model_loader._should_use_onnx() is False

    def test_returns_false_when_config_is_none(self, model_loader):
        with patch(
            "mcp_server.utils.config_helpers.get_config_via_service_locator",
            return_value=None,
        ):
            assert model_loader._should_use_onnx() is False

    def test_returns_false_when_no_use_onnx_attr(self, model_loader):
        """Performance config without use_onnx attribute defaults to False."""
        config = MagicMock()
        # Remove use_onnx from the mock spec so getattr fallback kicks in
        del config.performance.use_onnx
        with patch(
            "mcp_server.utils.config_helpers.get_config_via_service_locator",
            return_value=config,
        ):
            assert model_loader._should_use_onnx() is False


class TestLoadOnnx:
    """Tests for ModelLoader._load_onnx()."""

    @pytest.fixture
    def temp_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def _make_loader(self, temp_cache_dir, model_config):
        cache_manager = ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config,
        )
        return ModelLoader(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            device="cpu",
            cache_manager=cache_manager,
            model_config_getter=lambda: model_config,
        )

    def test_creates_loader_with_correct_args(self, temp_cache_dir):
        model_config = {"dimension": 768, "onnx_pooling": "cls"}
        loader = self._make_loader(temp_cache_dir, model_config)

        mock_ort = MagicMock()
        mock_tokenizer = MagicMock()
        mock_ort_loader = MagicMock()
        mock_ort_loader.load.return_value = (mock_ort, mock_tokenizer, "cpu")

        with (
            patch(
                "embeddings.onnx_loader.ONNXModelLoader", return_value=mock_ort_loader
            ) as mock_loader_cls,
            patch("embeddings.onnx_wrapper.ONNXEmbeddingModel"),
        ):
            loader._load_onnx()

        mock_loader_cls.assert_called_once_with(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            device="cpu",
        )

    def test_creates_wrapper_with_cls_pooling_from_registry(self, temp_cache_dir):
        model_config = {"dimension": 768, "onnx_pooling": "cls"}
        loader = self._make_loader(temp_cache_dir, model_config)

        mock_ort = MagicMock()
        mock_tokenizer = MagicMock()
        mock_ort_loader = MagicMock()
        mock_ort_loader.load.return_value = (mock_ort, mock_tokenizer, "cpu")

        with (
            patch(
                "embeddings.onnx_loader.ONNXModelLoader", return_value=mock_ort_loader
            ),
            patch("embeddings.onnx_wrapper.ONNXEmbeddingModel") as mock_wrapper_cls,
        ):
            loader._load_onnx()

        call_kwargs = mock_wrapper_cls.call_args[1]
        assert call_kwargs["pooling"] == "cls"

    def test_creates_wrapper_with_mean_pooling_from_registry(self, temp_cache_dir):
        model_config = {"dimension": 768, "onnx_pooling": "mean"}
        loader = self._make_loader(temp_cache_dir, model_config)

        mock_ort = MagicMock()
        mock_tokenizer = MagicMock()
        mock_ort_loader = MagicMock()
        mock_ort_loader.load.return_value = (mock_ort, mock_tokenizer, "cpu")

        with (
            patch(
                "embeddings.onnx_loader.ONNXModelLoader", return_value=mock_ort_loader
            ),
            patch("embeddings.onnx_wrapper.ONNXEmbeddingModel") as mock_wrapper_cls,
        ):
            loader._load_onnx()

        call_kwargs = mock_wrapper_cls.call_args[1]
        assert call_kwargs["pooling"] == "mean"

    def test_defaults_pooling_to_cls_when_not_in_config(self, temp_cache_dir):
        model_config = {"dimension": 768}  # no onnx_pooling key
        loader = self._make_loader(temp_cache_dir, model_config)

        mock_ort_loader = MagicMock()
        mock_ort_loader.load.return_value = (MagicMock(), MagicMock(), "cpu")

        with (
            patch(
                "embeddings.onnx_loader.ONNXModelLoader", return_value=mock_ort_loader
            ),
            patch("embeddings.onnx_wrapper.ONNXEmbeddingModel") as mock_wrapper_cls,
        ):
            loader._load_onnx()

        call_kwargs = mock_wrapper_cls.call_args[1]
        assert call_kwargs["pooling"] == "cls"

    def test_returns_wrapper_and_device(self, temp_cache_dir):
        model_config = {"dimension": 768}
        loader = self._make_loader(temp_cache_dir, model_config)

        mock_wrapper = MagicMock()
        mock_ort_loader = MagicMock()
        mock_ort_loader.load.return_value = (MagicMock(), MagicMock(), "cuda")

        with (
            patch(
                "embeddings.onnx_loader.ONNXModelLoader", return_value=mock_ort_loader
            ),
            patch(
                "embeddings.onnx_wrapper.ONNXEmbeddingModel", return_value=mock_wrapper
            ),
        ):
            result_model, result_device = loader._load_onnx()

        assert result_model is mock_wrapper
        assert result_device == "cuda"

    def test_passes_ort_model_and_tokenizer_to_wrapper(self, temp_cache_dir):
        model_config = {"dimension": 768}
        loader = self._make_loader(temp_cache_dir, model_config)

        mock_ort = MagicMock()
        mock_tokenizer = MagicMock()
        mock_ort_loader = MagicMock()
        mock_ort_loader.load.return_value = (mock_ort, mock_tokenizer, "cpu")

        with (
            patch(
                "embeddings.onnx_loader.ONNXModelLoader", return_value=mock_ort_loader
            ),
            patch("embeddings.onnx_wrapper.ONNXEmbeddingModel") as mock_wrapper_cls,
        ):
            loader._load_onnx()

        call_kwargs = mock_wrapper_cls.call_args[1]
        assert call_kwargs["ort_model"] is mock_ort
        assert call_kwargs["tokenizer"] is mock_tokenizer


class TestModelLoaderLoadOnnxFastPath:
    """Tests verifying the ONNX fast path in ModelLoader.load()."""

    @pytest.fixture
    def temp_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def model_loader(self, temp_cache_dir):
        model_config = {"dimension": 768}
        cache_manager = ModelCacheManager(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            model_config_getter=lambda: model_config,
        )
        return ModelLoader(
            model_name="BAAI/bge-m3",
            cache_dir=str(temp_cache_dir),
            device="cpu",
            cache_manager=cache_manager,
            model_config_getter=lambda: model_config,
        )

    def test_onnx_path_taken_when_eligible(self, model_loader):
        mock_model = MagicMock()
        with (
            patch.object(model_loader, "_should_use_onnx", return_value=True),
            patch.object(
                model_loader, "_load_onnx", return_value=(mock_model, "cpu")
            ) as mock_load_onnx,
            patch("embeddings.model_loader.SentenceTransformer") as mock_st,
        ):
            result_model, result_device = model_loader.load()

        mock_load_onnx.assert_called_once()
        mock_st.assert_not_called()
        assert result_model is mock_model
        assert result_device == "cpu"

    def test_pytorch_path_taken_when_onnx_not_eligible(self, model_loader):
        mock_st_model = MagicMock()
        mock_st_model.device = "cpu"

        with (
            patch.object(model_loader, "_should_use_onnx", return_value=False),
            patch(
                "embeddings.model_loader.SentenceTransformer",
                return_value=mock_st_model,
            ) as mock_st,
            patch.object(
                model_loader._cache_manager, "validate_cache", return_value=(True, "ok")
            ),
            patch.object(model_loader, "resolve_device", return_value="cpu"),
            patch.object(model_loader, "get_torch_dtype", return_value=None),
        ):
            result_model, result_device = model_loader.load()

        mock_st.assert_called_once()

    def test_onnx_path_bypasses_cache_validation(self, model_loader):
        mock_model = MagicMock()
        with (
            patch.object(model_loader, "_should_use_onnx", return_value=True),
            patch.object(model_loader, "_load_onnx", return_value=(mock_model, "cpu")),
            patch.object(
                model_loader._cache_manager, "validate_cache"
            ) as mock_validate,
        ):
            model_loader.load()

        mock_validate.assert_not_called()
