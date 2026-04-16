"""Tests for ONNXModelLoader and module-level helpers in embeddings/onnx_loader.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from embeddings.onnx_loader import (
    ONNXModelLoader,
    _is_converted,
    _onnx_cache_dir,
    _resolve_provider,
)


# ---------------------------------------------------------------------------
# _onnx_cache_dir
# ---------------------------------------------------------------------------


class TestOnnxCacheDir:
    def test_slash_replaced_with_double_dash(self):
        result = _onnx_cache_dir("BAAI/bge-m3")
        assert result.name == "BAAI--bge-m3"

    def test_no_slash_unchanged(self):
        result = _onnx_cache_dir("some-model")
        assert result.name == "some-model"

    def test_multiple_slashes(self):
        result = _onnx_cache_dir("org/sub/model")
        assert result.name == "org--sub--model"

    def test_default_parent_path(self):
        result = _onnx_cache_dir("BAAI/bge-m3")
        expected = Path.home() / ".cache" / "huggingface" / "onnx" / "BAAI--bge-m3"
        assert result == expected


# ---------------------------------------------------------------------------
# _is_converted
# ---------------------------------------------------------------------------


class TestIsConverted:
    def test_true_with_optimized_model(self, tmp_path):
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        assert _is_converted(tmp_path) is True

    def test_true_with_base_model_fallback(self, tmp_path):
        """model.onnx is accepted as fallback when model_optimized.onnx is absent."""
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model.onnx").write_bytes(b"")
        assert _is_converted(tmp_path) is True

    def test_false_missing_meta(self, tmp_path):
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        assert _is_converted(tmp_path) is False

    def test_false_missing_model_file(self, tmp_path):
        (tmp_path / "convert_meta.json").write_text("{}")
        assert _is_converted(tmp_path) is False

    def test_false_empty_dir(self, tmp_path):
        assert _is_converted(tmp_path) is False

    def test_false_nonexistent_dir(self, tmp_path):
        assert _is_converted(tmp_path / "does_not_exist") is False


# ---------------------------------------------------------------------------
# _resolve_provider
# ---------------------------------------------------------------------------


class TestResolveProvider:
    def test_cuda_returns_cuda_provider(self):
        assert _resolve_provider("cuda") == "CUDAExecutionProvider"

    def test_cpu_returns_cpu_provider(self):
        assert _resolve_provider("cpu") == "CPUExecutionProvider"

    def test_unknown_device_returns_cpu_provider(self):
        assert _resolve_provider("tpu") == "CPUExecutionProvider"
        assert _resolve_provider("mps") == "CPUExecutionProvider"


# ---------------------------------------------------------------------------
# _convert_model
# ---------------------------------------------------------------------------


class TestConvertModel:
    """Tests for the internal _convert_model() function."""

    def _make_optimum_mocks(self, tmp_path, create_optimized=True):
        """Build mock optimum.onnxruntime module and optionally create the model file."""
        mock_ort_model = MagicMock()
        mock_optimizer = MagicMock()
        mock_opt_config_cls = MagicMock()
        mock_opt_config = MagicMock()
        mock_opt_config_cls.return_value = mock_opt_config
        mock_optimizer.optimize = MagicMock(
            side_effect=lambda **kw: (
                (tmp_path / "model_optimized.onnx").write_bytes(b"")
                if create_optimized
                else None
            )
        )

        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = (
            mock_ort_model
        )
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        mock_ort.AutoOptimizationConfig.O4 = mock_opt_config_cls
        return mock_ort

    def test_import_error_when_optimum_missing(self, tmp_path):
        with patch.dict("sys.modules", {"optimum.onnxruntime": None}):
            from embeddings.onnx_loader import _convert_model

            with pytest.raises(ImportError, match="optimum"):
                _convert_model("BAAI/bge-m3", tmp_path, "cpu")

    def test_export_failure_raises_runtime_error(self, tmp_path):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.side_effect = (
            RuntimeError("export boom")
        )
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            from embeddings.onnx_loader import _convert_model

            with pytest.raises(RuntimeError, match="Export failed"):
                _convert_model("BAAI/bge-m3", tmp_path, "cpu")

    def test_optimization_failure_raises_runtime_error(self, tmp_path):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        mock_optimizer = MagicMock()
        mock_optimizer.optimize.side_effect = RuntimeError("opt boom")
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            from embeddings.onnx_loader import _convert_model

            with pytest.raises(RuntimeError, match="Optimization failed"):
                _convert_model("BAAI/bge-m3", tmp_path, "cpu")

    def test_success_writes_meta_json(self, tmp_path):
        mock_ort = self._make_optimum_mocks(tmp_path, create_optimized=True)
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            from embeddings.onnx_loader import _convert_model

            _convert_model("BAAI/bge-m3", tmp_path, "cpu")

        meta_path = tmp_path / "convert_meta.json"
        assert meta_path.is_file()
        meta = json.loads(meta_path.read_text())
        assert meta["source_model"] == "BAAI/bge-m3"
        assert meta["optimization_level"] == "O4"
        assert meta["gemm_gelu_fusion"] is True
        assert meta["device"] == "cpu"
        assert meta["quality_validated"] is False

    def test_success_creates_directory(self, tmp_path):
        new_dir = tmp_path / "sub" / "cache"
        mock_ort = self._make_optimum_mocks(new_dir, create_optimized=True)
        # Recreate side_effect to write into new_dir
        mock_optimizer = MagicMock()
        mock_optimizer.optimize = MagicMock(
            side_effect=lambda **kw: (new_dir / "model_optimized.onnx").write_bytes(b"")
        )
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            from embeddings.onnx_loader import _convert_model

            _convert_model("test-model", new_dir, "cpu")

        assert new_dir.is_dir()

    def test_model_file_fallback_to_model_onnx(self, tmp_path):
        """When model_optimized.onnx absent but model.onnx present, meta records model.onnx."""
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        mock_optimizer = MagicMock()

        def _fake_optimize(**kw):
            (tmp_path / "model.onnx").write_bytes(b"")  # only base model created

        mock_optimizer.optimize.side_effect = _fake_optimize
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            from embeddings.onnx_loader import _convert_model

            _convert_model("BAAI/bge-m3", tmp_path, "cpu")

        meta = json.loads((tmp_path / "convert_meta.json").read_text())
        assert meta["model_file"] == "model.onnx"

    def test_model_file_optimized_recorded_in_meta(self, tmp_path):
        mock_ort = self._make_optimum_mocks(tmp_path, create_optimized=True)
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            from embeddings.onnx_loader import _convert_model

            _convert_model("BAAI/bge-m3", tmp_path, "cpu")

        meta = json.loads((tmp_path / "convert_meta.json").read_text())
        assert meta["model_file"] == "model_optimized.onnx"


# ---------------------------------------------------------------------------
# ONNXModelLoader — init & properties
# ---------------------------------------------------------------------------


class TestONNXModelLoaderInit:
    def test_stores_attributes(self, tmp_path):
        loader = ONNXModelLoader("BAAI/bge-m3", cache_dir=str(tmp_path), device="cpu")
        assert loader.model_name == "BAAI/bge-m3"
        assert loader.cache_dir == str(tmp_path)
        assert loader._raw_device == "cpu"

    def test_default_onnx_dir_is_derived_from_model_name(self):
        loader = ONNXModelLoader("BAAI/bge-m3")
        expected = Path.home() / ".cache" / "huggingface" / "onnx" / "BAAI--bge-m3"
        assert loader._onnx_dir == expected

    def test_custom_onnx_cache_dir_overrides_default(self, tmp_path):
        custom = tmp_path / "custom_onnx"
        loader = ONNXModelLoader("BAAI/bge-m3", onnx_cache_dir=custom)
        assert loader._onnx_dir == custom

    def test_onnx_dir_property_returns_onnx_dir(self, tmp_path):
        custom = tmp_path / "onnx"
        loader = ONNXModelLoader("BAAI/bge-m3", onnx_cache_dir=custom)
        assert loader.onnx_dir == custom


# ---------------------------------------------------------------------------
# ONNXModelLoader — _resolve_device
# ---------------------------------------------------------------------------


class TestONNXModelLoaderResolveDevice:
    def test_explicit_cpu(self):
        loader = ONNXModelLoader("m", device="cpu")
        assert loader._resolve_device() == "cpu"

    def test_explicit_cuda(self):
        loader = ONNXModelLoader("m", device="cuda")
        assert loader._resolve_device() == "cuda"

    def test_auto_with_cuda_available(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        loader = ONNXModelLoader("m", device="auto")
        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert loader._resolve_device() == "cuda"

    def test_auto_without_cuda(self):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        loader = ONNXModelLoader("m", device="auto")
        with patch.dict("sys.modules", {"torch": mock_torch}):
            assert loader._resolve_device() == "cpu"

    def test_auto_no_torch_defaults_to_cpu(self):
        loader = ONNXModelLoader("m", device="auto")
        # Simulate missing torch by setting sys.modules entry to None (causes ImportError)
        with patch.dict("sys.modules", {"torch": None}):
            result = loader._resolve_device()
        assert result == "cpu"


# ---------------------------------------------------------------------------
# ONNXModelLoader — is_converted & convert_if_needed
# ---------------------------------------------------------------------------


class TestONNXModelLoaderIsConverted:
    def test_delegates_to_module_function(self, tmp_path):
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path)
        # Nothing in tmp_path → not converted
        assert loader.is_converted() is False
        # Add required files
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        assert loader.is_converted() is True


class TestONNXModelLoaderConvertIfNeeded:
    def test_converts_when_not_cached(self, tmp_path):
        loader = ONNXModelLoader("BAAI/bge-m3", onnx_cache_dir=tmp_path)
        with (
            patch("embeddings.onnx_loader._convert_model") as mock_convert,
            patch("embeddings.onnx_loader._is_converted", return_value=False),
        ):
            loader.convert_if_needed("cpu")
            mock_convert.assert_called_once_with("BAAI/bge-m3", tmp_path, "cpu")

    def test_skips_when_already_cached(self, tmp_path):
        loader = ONNXModelLoader("BAAI/bge-m3", onnx_cache_dir=tmp_path)
        with (
            patch("embeddings.onnx_loader._convert_model") as mock_convert,
            patch("embeddings.onnx_loader._is_converted", return_value=True),
        ):
            loader.convert_if_needed("cpu")
            mock_convert.assert_not_called()


# ---------------------------------------------------------------------------
# ONNXModelLoader — load()
# ---------------------------------------------------------------------------


class TestONNXModelLoaderLoad:
    def _setup_load_mocks(self, tmp_path):
        """Return (mock_ort_model, mock_tokenizer, mock_ort_module, mock_transformers)."""
        mock_ort_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = (
            mock_ort_model
        )
        mock_tf = MagicMock()
        mock_tf.AutoTokenizer.from_pretrained.return_value = mock_tokenizer
        return mock_ort_model, mock_tokenizer, mock_ort, mock_tf

    def test_import_error_if_optimum_missing(self, tmp_path):
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cpu")
        with (
            patch.dict("sys.modules", {"optimum.onnxruntime": None}),
            pytest.raises(ImportError, match="optimum"),
        ):
            loader.load()

    def test_skips_conversion_when_cached(self, tmp_path):
        mock_ort_model, mock_tokenizer, mock_ort, mock_tf = self._setup_load_mocks(
            tmp_path
        )
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cpu")
        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
            patch("embeddings.onnx_loader._convert_model") as mock_convert,
        ):
            loader.load()
            mock_convert.assert_not_called()

    def test_auto_converts_when_not_cached(self, tmp_path):
        mock_ort_model, mock_tokenizer, mock_ort, mock_tf = self._setup_load_mocks(
            tmp_path
        )
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cpu")
        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=False),
            patch("embeddings.onnx_loader._convert_model") as mock_convert,
        ):
            loader.load()
            mock_convert.assert_called_once_with("m", tmp_path, "cpu")

    def test_returns_ort_model_tokenizer_device(self, tmp_path):
        mock_ort_model, mock_tokenizer, mock_ort, mock_tf = self._setup_load_mocks(
            tmp_path
        )
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cpu")
        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
        ):
            result = loader.load()
        assert len(result) == 3
        ort_model, tokenizer, device = result
        assert ort_model is mock_ort_model
        assert tokenizer is mock_tokenizer
        assert device == "cpu"

    def test_cuda_device_passes_cuda_provider(self, tmp_path):
        mock_ort_model, mock_tokenizer, mock_ort, mock_tf = self._setup_load_mocks(
            tmp_path
        )
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cuda")
        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
        ):
            loader.load()
        call_kwargs = mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args
        assert call_kwargs.args == (str(tmp_path),)
        assert call_kwargs.kwargs["provider"] == "CUDAExecutionProvider"
        assert "session_options" in call_kwargs.kwargs

    def test_runtime_error_on_model_load_failure(self, tmp_path):
        mock_ort_model, mock_tokenizer, mock_ort, mock_tf = self._setup_load_mocks(
            tmp_path
        )
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.side_effect = Exception(
            "load boom"
        )
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cpu")
        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
            pytest.raises(RuntimeError, match="Failed to load"),
        ):
            loader.load()


# ---------------------------------------------------------------------------
# ORT provider_options — gpu_mem_limit cap
# ---------------------------------------------------------------------------


class TestOrtProviderOptions:
    """Verify that ONNXModelLoader.load() passes gpu_mem_limit to the ORT session
    when CUDAExecutionProvider is used and onnx_gpu_mem_limit is enabled.

    The cap logic uses lazy imports (inside the function body) to avoid circular
    imports.  Patching must target the *source* module attributes, not the
    onnx_loader namespace (since the names are resolved at call time via
    ``from X import Y`` inside the function).
    """

    def _mock_ort(self):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        return mock_ort

    def _mock_tf(self):
        mock_tf = MagicMock()
        mock_tf.AutoTokenizer.from_pretrained.return_value = MagicMock()
        return mock_tf

    def _make_cfg(self, fraction=0.8, onnx_gpu_mem_limit=True):
        perf = MagicMock()
        perf.vram_limit_fraction = fraction
        perf.onnx_gpu_mem_limit = onnx_gpu_mem_limit
        cfg = MagicMock()
        cfg.performance = perf
        return cfg

    def test_cuda_provider_passes_gpu_mem_limit(self, tmp_path):
        """CUDAExecutionProvider with onnx_gpu_mem_limit=True gets gpu_mem_limit > 0."""
        mock_ort = self._mock_ort()
        mock_tf = self._mock_tf()
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cuda")

        # Patch compute_effective_vram_cap to return a deterministic cap (6 GB).
        # Must patch at the source module because the import is lazy (inside fn body).
        _cap_bytes = int(6 * 1024**3)
        _cap_result = (0.75, _cap_bytes, 8.0, 0.0, 0.5, 1.6)

        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
            patch(
                "embeddings.embedder.compute_effective_vram_cap",
                return_value=_cap_result,
            ),
            patch(
                "mcp_server.utils.config_helpers.get_config_via_service_locator",
                return_value=self._make_cfg(onnx_gpu_mem_limit=True),
            ),
        ):
            loader.load()

        call_kwargs = (
            mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args.kwargs
        )
        assert "provider_options" in call_kwargs
        po = call_kwargs["provider_options"]
        assert po is not None
        assert len(po) == 1
        assert po[0]["gpu_mem_limit"] == _cap_bytes
        assert po[0]["arena_extend_strategy"] == "kSameAsRequested"

    def test_onnx_gpu_mem_limit_false_passes_none(self, tmp_path):
        """When onnx_gpu_mem_limit=False, provider_options is None."""
        mock_ort = self._mock_ort()
        mock_tf = self._mock_tf()
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cuda")

        _cap_result = (0.75, int(6 * 1024**3), 8.0, 0.0, 0.5, 1.6)

        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
            patch(
                "embeddings.embedder.compute_effective_vram_cap",
                return_value=_cap_result,
            ),
            patch(
                "mcp_server.utils.config_helpers.get_config_via_service_locator",
                return_value=self._make_cfg(onnx_gpu_mem_limit=False),
            ),
        ):
            loader.load()

        call_kwargs = (
            mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args.kwargs
        )
        assert call_kwargs.get("provider_options") is None

    def test_cpu_provider_passes_none(self, tmp_path):
        """CPUExecutionProvider never gets provider_options (no gpu_mem_limit concept)."""
        mock_ort = self._mock_ort()
        mock_tf = self._mock_tf()
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cpu")

        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
        ):
            loader.load()

        call_kwargs = (
            mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args.kwargs
        )
        assert call_kwargs.get("provider_options") is None

    def test_cap_compute_failure_falls_back_to_none(self, tmp_path):
        """If compute_effective_vram_cap returns None, provider_options is None (non-fatal)."""
        mock_ort = self._mock_ort()
        mock_tf = self._mock_tf()
        loader = ONNXModelLoader("m", onnx_cache_dir=tmp_path, device="cuda")

        with (
            patch.dict(
                "sys.modules",
                {"optimum.onnxruntime": mock_ort, "transformers": mock_tf},
            ),
            patch("embeddings.onnx_loader._is_converted", return_value=True),
            patch(
                "embeddings.embedder.compute_effective_vram_cap",
                return_value=None,
            ),
            patch(
                "mcp_server.utils.config_helpers.get_config_via_service_locator",
                return_value=self._make_cfg(onnx_gpu_mem_limit=True),
            ),
        ):
            loader.load()  # must not raise

        call_kwargs = (
            mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args.kwargs
        )
        assert call_kwargs.get("provider_options") is None
