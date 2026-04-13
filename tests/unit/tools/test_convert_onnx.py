"""Tests for tools/convert_onnx.py — standalone ONNX conversion script."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper: importable convert_onnx module
# ---------------------------------------------------------------------------

# The script lives in tools/, which is not a package. Add it to sys.path once.
_TOOLS_DIR = str(Path(__file__).parent.parent.parent.parent / "tools")
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

import convert_onnx  # noqa: E402


# ---------------------------------------------------------------------------
# _onnx_cache_dir
# ---------------------------------------------------------------------------


class TestConvertOnnxCacheDir:
    def test_default_base_uses_home_cache(self):
        result = convert_onnx._onnx_cache_dir("BAAI/bge-m3")
        expected = Path.home() / ".cache" / "huggingface" / "onnx" / "BAAI--bge-m3"
        assert result == expected

    def test_custom_base(self, tmp_path):
        result = convert_onnx._onnx_cache_dir("BAAI/bge-m3", base=tmp_path)
        assert result == tmp_path / "BAAI--bge-m3"

    def test_slash_replaced_with_double_dash(self, tmp_path):
        result = convert_onnx._onnx_cache_dir("org/my/model", base=tmp_path)
        assert result.name == "org--my--model"


# ---------------------------------------------------------------------------
# _is_converted (CLI version — stricter: requires model_optimized.onnx only)
# ---------------------------------------------------------------------------


class TestConvertOnnxIsConverted:
    def test_true_with_optimized_model(self, tmp_path):
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        assert convert_onnx._is_converted(tmp_path) is True

    def test_false_with_only_base_model(self, tmp_path):
        """CLI version requires model_optimized.onnx specifically — model.onnx alone is not enough."""
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model.onnx").write_bytes(b"")
        assert convert_onnx._is_converted(tmp_path) is False

    def test_false_missing_meta(self, tmp_path):
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        assert convert_onnx._is_converted(tmp_path) is False

    def test_false_empty_dir(self, tmp_path):
        assert convert_onnx._is_converted(tmp_path) is False


# ---------------------------------------------------------------------------
# convert()
# ---------------------------------------------------------------------------


class TestConvert:
    def _make_optimum_mocks(self, tmp_path, create_optimized=True):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        mock_optimizer = MagicMock()

        def _fake_optimize(**kw):
            if create_optimized:
                (tmp_path / "model_optimized.onnx").write_bytes(b"")

        mock_optimizer.optimize.side_effect = _fake_optimize
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        return mock_ort

    def test_ineligible_model_raises_value_error(self, tmp_path):
        with pytest.raises(ValueError, match="not eligible"):
            convert_onnx.convert("nomic-ai/CodeRankEmbed", output=tmp_path)

    def test_import_error_when_optimum_missing(self, tmp_path):
        with (
            patch.dict("sys.modules", {"optimum.onnxruntime": None}),
            pytest.raises(ImportError, match="optimum"),
        ):
            convert_onnx.convert("BAAI/bge-m3", output=tmp_path)

    def test_already_converted_skips_conversion(self, tmp_path, capsys):
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        # Should return early without touching optimum
        result = convert_onnx.convert("BAAI/bge-m3", output=tmp_path)
        assert result == tmp_path

    def test_export_failure_raises_runtime_error(self, tmp_path):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.side_effect = (
            RuntimeError("export boom")
        )
        with (
            patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}),
            pytest.raises(RuntimeError, match="export failed"),
        ):
            convert_onnx.convert("BAAI/bge-m3", output=tmp_path)

    def test_optimization_failure_raises_runtime_error(self, tmp_path):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        mock_optimizer = MagicMock()
        mock_optimizer.optimize.side_effect = RuntimeError("opt boom")
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with (
            patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}),
            pytest.raises(RuntimeError, match="optimization failed"),
        ):
            convert_onnx.convert("BAAI/bge-m3", output=tmp_path)

    def test_auto_device_detects_cuda(self, tmp_path):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_ort = self._make_optimum_mocks(tmp_path)
        with patch.dict(
            "sys.modules", {"optimum.onnxruntime": mock_ort, "torch": mock_torch}
        ):
            convert_onnx.convert("BAAI/bge-m3", device=None, output=tmp_path)
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.assert_called_once()
        call_kwargs = mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args[1]
        assert call_kwargs["provider"] == "CUDAExecutionProvider"

    def test_auto_device_detects_cpu(self, tmp_path):
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_ort = self._make_optimum_mocks(tmp_path)
        with patch.dict(
            "sys.modules", {"optimum.onnxruntime": mock_ort, "torch": mock_torch}
        ):
            convert_onnx.convert("BAAI/bge-m3", device=None, output=tmp_path)
        call_kwargs = mock_ort.ORTModelForFeatureExtraction.from_pretrained.call_args[1]
        assert call_kwargs["provider"] == "CPUExecutionProvider"

    def test_success_writes_meta_json(self, tmp_path):
        mock_ort = self._make_optimum_mocks(tmp_path, create_optimized=True)
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            convert_onnx.convert("BAAI/bge-m3", device="cpu", output=tmp_path)
        meta_path = tmp_path / "convert_meta.json"
        assert meta_path.is_file()
        meta = json.loads(meta_path.read_text())
        assert meta["source_model"] == "BAAI/bge-m3"
        assert meta["device"] == "cpu"
        assert meta["quality_validated"] is False

    def test_model_file_fallback_to_model_onnx(self, tmp_path):
        """When optimization produces model.onnx but not model_optimized.onnx, log warning and use fallback."""
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        mock_optimizer = MagicMock()

        def _fake_optimize(**kw):
            (tmp_path / "model.onnx").write_bytes(b"")

        mock_optimizer.optimize.side_effect = _fake_optimize
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            result = convert_onnx.convert("BAAI/bge-m3", device="cpu", output=tmp_path)
        assert result == tmp_path
        meta = json.loads((tmp_path / "convert_meta.json").read_text())
        assert meta["model_file"] == "model.onnx"

    def test_no_model_file_after_optimization_raises(self, tmp_path):
        mock_ort = MagicMock()
        mock_ort.ORTModelForFeatureExtraction.from_pretrained.return_value = MagicMock()
        mock_optimizer = MagicMock()
        mock_optimizer.optimize.return_value = None  # creates nothing
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with (
            patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}),
            pytest.raises(RuntimeError, match="No ONNX model file found"),
        ):
            convert_onnx.convert("BAAI/bge-m3", device="cpu", output=tmp_path)

    def test_custom_output_dir_used(self, tmp_path):
        custom = tmp_path / "my_output"
        mock_ort = self._make_optimum_mocks(custom, create_optimized=True)
        # Recreate optimizer to write into custom dir
        mock_optimizer = MagicMock()

        def _fake_optimize(**kw):
            custom.mkdir(parents=True, exist_ok=True)
            (custom / "model_optimized.onnx").write_bytes(b"")

        mock_optimizer.optimize.side_effect = _fake_optimize
        mock_ort.ORTOptimizer.from_pretrained.return_value = mock_optimizer
        with patch.dict("sys.modules", {"optimum.onnxruntime": mock_ort}):
            result = convert_onnx.convert("BAAI/bge-m3", device="cpu", output=custom)
        assert result == custom


# ---------------------------------------------------------------------------
# validate()
# ---------------------------------------------------------------------------


class TestValidate:
    def _make_validate_mocks(self, max_diff: float):
        """Return mocks for SentenceTransformer and ORT producing controlled embedding diff."""
        import torch

        # Create normalized embeddings with a known difference
        pt_embs = torch.tensor([[1.0, 0.0]])
        ort_hidden = torch.tensor([[[1.0 - max_diff, 0.0, 0.0]]])  # shape (1, 1, 3)

        mock_pt_model = MagicMock()
        mock_pt_model.encode.return_value = pt_embs

        mock_ort = MagicMock()
        mock_out = MagicMock()
        mock_out.last_hidden_state = ort_hidden
        mock_ort.return_value = mock_out

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.ones(1, 1, dtype=torch.long),
            "attention_mask": torch.ones(1, 1, dtype=torch.long),
        }

        mock_st_cls = MagicMock(return_value=mock_pt_model)
        mock_ort_cls = MagicMock()
        mock_ort_cls.from_pretrained.return_value = mock_ort
        mock_tokenizer_cls = MagicMock()
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        return mock_st_cls, mock_ort_cls, mock_tokenizer_cls

    def test_passes_when_diff_below_threshold(self, tmp_path):
        """When max cosine diff < 0.001, validate() returns True."""
        (tmp_path / "convert_meta.json").write_text(json.dumps({}))
        import torch

        pt_embs = torch.nn.functional.normalize(torch.ones(10, 8), p=2, dim=1)
        ort_embs = pt_embs.clone()  # identical → diff = 0

        mock_pt_model = MagicMock()
        mock_pt_model.encode.return_value = pt_embs

        mock_ort_model = MagicMock()
        mock_out = MagicMock()
        # last_hidden_state[:, 0, :] == ort_embs (shape N, 1, 8)
        mock_out.last_hidden_state = ort_embs.unsqueeze(1)
        mock_ort_model.return_value = mock_out

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.ones(10, 4, dtype=torch.long),
            "attention_mask": torch.ones(10, 4, dtype=torch.long),
        }

        mock_st_cls = MagicMock(return_value=mock_pt_model)
        mock_ort_cls = MagicMock()
        mock_ort_cls.from_pretrained.return_value = mock_ort_model
        mock_tokenizer_cls = MagicMock()
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        with patch.dict(
            "sys.modules",
            {
                "sentence_transformers": MagicMock(SentenceTransformer=mock_st_cls),
                "optimum.onnxruntime": MagicMock(
                    ORTModelForFeatureExtraction=mock_ort_cls
                ),
                "transformers": MagicMock(AutoTokenizer=mock_tokenizer_cls),
            },
        ):
            result = convert_onnx.validate("BAAI/bge-m3", tmp_path, device="cpu")

        assert result is True

    def test_fails_when_diff_above_threshold(self, tmp_path):
        """When max cosine diff > 0.001, validate() returns False."""
        (tmp_path / "convert_meta.json").write_text(json.dumps({}))
        import torch

        pt_embs = torch.nn.functional.normalize(torch.ones(10, 8), p=2, dim=1)
        # Make ONNX embeddings very different
        ort_embs_hidden = torch.zeros(10, 1, 8)  # all zeros → large diff after norm

        mock_pt_model = MagicMock()
        mock_pt_model.encode.return_value = pt_embs

        mock_ort_model = MagicMock()
        mock_out = MagicMock()
        mock_out.last_hidden_state = ort_embs_hidden
        mock_ort_model.return_value = mock_out

        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.ones(10, 4, dtype=torch.long),
            "attention_mask": torch.ones(10, 4, dtype=torch.long),
        }

        mock_st_cls = MagicMock(return_value=mock_pt_model)
        mock_ort_cls = MagicMock()
        mock_ort_cls.from_pretrained.return_value = mock_ort_model
        mock_tokenizer_cls = MagicMock()
        mock_tokenizer_cls.from_pretrained.return_value = mock_tokenizer

        with patch.dict(
            "sys.modules",
            {
                "sentence_transformers": MagicMock(SentenceTransformer=mock_st_cls),
                "optimum.onnxruntime": MagicMock(
                    ORTModelForFeatureExtraction=mock_ort_cls
                ),
                "transformers": MagicMock(AutoTokenizer=mock_tokenizer_cls),
            },
        ):
            result = convert_onnx.validate("BAAI/bge-m3", tmp_path, device="cpu")

        assert result is False

    def test_updates_meta_on_pass(self, tmp_path):
        (tmp_path / "convert_meta.json").write_text(
            json.dumps({"quality_validated": False})
        )
        import torch

        embs = torch.nn.functional.normalize(torch.ones(10, 8), p=2, dim=1)

        mock_pt_model = MagicMock()
        mock_pt_model.encode.return_value = embs
        mock_ort_model = MagicMock()
        mock_out = MagicMock()
        mock_out.last_hidden_state = embs.unsqueeze(1)
        mock_ort_model.return_value = mock_out
        mock_tokenizer = MagicMock()
        mock_tokenizer.return_value = {
            "input_ids": torch.ones(10, 4, dtype=torch.long),
            "attention_mask": torch.ones(10, 4, dtype=torch.long),
        }

        with patch.dict(
            "sys.modules",
            {
                "sentence_transformers": MagicMock(
                    SentenceTransformer=MagicMock(return_value=mock_pt_model)
                ),
                "optimum.onnxruntime": MagicMock(
                    ORTModelForFeatureExtraction=MagicMock(
                        from_pretrained=MagicMock(return_value=mock_ort_model)
                    )
                ),
                "transformers": MagicMock(
                    AutoTokenizer=MagicMock(
                        from_pretrained=MagicMock(return_value=mock_tokenizer)
                    )
                ),
            },
        ):
            convert_onnx.validate("BAAI/bge-m3", tmp_path)

        meta = json.loads((tmp_path / "convert_meta.json").read_text())
        assert meta["quality_validated"] is True
        assert "quality_max_diff" in meta

    def test_missing_sentence_transformers_returns_false(self, tmp_path):
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            result = convert_onnx.validate("BAAI/bge-m3", tmp_path)
        assert result is False


# ---------------------------------------------------------------------------
# list_models()
# ---------------------------------------------------------------------------


class TestListModels:
    def test_prints_ok_and_skip_markers(self, capsys):
        mock_registry = {
            "BAAI/bge-m3": {"description": "Dense embedding"},
            "nomic-ai/CodeRankEmbed": {"trust_remote_code": True},
        }
        with patch.dict(
            "sys.modules",
            {
                "search": MagicMock(),
                "search.config": MagicMock(MODEL_REGISTRY=mock_registry),
            },
        ):
            convert_onnx.list_models()

        captured = capsys.readouterr()
        assert "OK" in captured.out or "SKIP" in captured.out
        assert "BAAI/bge-m3" in captured.out
        assert "nomic-ai/CodeRankEmbed" in captured.out

    def test_import_error_calls_sys_exit(self):
        with (
            patch.dict("sys.modules", {"search": None, "search.config": None}),
            pytest.raises(SystemExit) as exc_info,
        ):
            convert_onnx.list_models()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# main() — argument parsing
# ---------------------------------------------------------------------------


class TestMain:
    def test_list_flag_calls_list_models_and_returns(self):
        with (
            patch("sys.argv", ["convert_onnx", "--list"]),
            patch("convert_onnx.list_models") as mock_list,
            patch("convert_onnx.convert") as mock_convert,
        ):
            convert_onnx.main()
        mock_list.assert_called_once()
        mock_convert.assert_not_called()

    def test_model_required_without_list_exits(self):
        with patch("sys.argv", ["convert_onnx"]), pytest.raises(SystemExit):
            convert_onnx.main()

    def test_force_deletes_existing_cache(self, tmp_path):
        (tmp_path / "convert_meta.json").write_text("{}")
        (tmp_path / "model_optimized.onnx").write_bytes(b"")
        assert tmp_path.exists()

        with (
            patch(
                "sys.argv",
                [
                    "convert_onnx",
                    "--model",
                    "BAAI/bge-m3",
                    "--force",
                    "--output",
                    str(tmp_path),
                ],
            ),
            patch("convert_onnx.convert", return_value=tmp_path),
            patch("shutil.rmtree") as mock_rmtree,
        ):
            convert_onnx.main()

        mock_rmtree.assert_called_once_with(tmp_path)

    def test_validate_flag_calls_validate_after_convert(self, tmp_path):
        with (
            patch(
                "sys.argv",
                [
                    "convert_onnx",
                    "--model",
                    "BAAI/bge-m3",
                    "--validate",
                    "--output",
                    str(tmp_path),
                ],
            ),
            patch("convert_onnx.convert", return_value=tmp_path),
            patch("convert_onnx.validate", return_value=True) as mock_validate,
            patch("convert_onnx._cuda_available", return_value=False),
            pytest.raises(SystemExit) as exc_info,
        ):
            convert_onnx.main()
        mock_validate.assert_called_once()
        assert exc_info.value.code == 0

    def test_convert_error_exits_with_code_1(self, tmp_path):
        with (
            patch(
                "sys.argv",
                ["convert_onnx", "--model", "BAAI/bge-m3", "--output", str(tmp_path)],
            ),
            patch("convert_onnx.convert", side_effect=ValueError("ineligible")),
            pytest.raises(SystemExit) as exc_info,
        ):
            convert_onnx.main()
        assert exc_info.value.code == 1
