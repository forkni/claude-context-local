"""ONNX model loader with auto-conversion for claude-context-local.

On first use with use_onnx=True, converts the model to ONNX using the same
pipeline as tools/convert_onnx.py, then caches the result. Subsequent loads
skip conversion and read directly from cache.

Cache layout:
    ~/.cache/huggingface/onnx/<org>--<model>/
        model_optimized.onnx      ← optimized ONNX graph
        tokenizer.json            ← HuggingFace tokenizer
        tokenizer_config.json
        convert_meta.json         ← conversion metadata (model, date, quality)
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


_log = logging.getLogger(__name__)

# Default optimization level — O4 = maximum transformer-specific fusions
_DEFAULT_OPTIMIZE = "O4"
# GEMM GELU fusion is more numerically stable than gelu_approximation
# (max diff 0.0004 vs 0.0011 per the Optimum benchmark notebook)
_GEMM_GELU = True


def _onnx_cache_dir(model_name: str) -> Path:
    """Return canonical ONNX cache path for a model.

    Mirrors the convention used by tools/convert_onnx.py:
        ~/.cache/huggingface/onnx/BAAI--bge-m3/
    """
    sanitized = model_name.replace("/", "--")
    return Path.home() / ".cache" / "huggingface" / "onnx" / sanitized


def _is_converted(onnx_dir: Path) -> bool:
    """True if a valid converted ONNX model exists at onnx_dir."""
    meta = onnx_dir / "convert_meta.json"
    # Accept both the optimized and base filenames
    model_exists = (onnx_dir / "model_optimized.onnx").is_file() or (
        onnx_dir / "model.onnx"
    ).is_file()
    return meta.is_file() and model_exists


def _resolve_provider(device: str) -> str:
    if device == "cuda":
        return "CUDAExecutionProvider"
    return "CPUExecutionProvider"


def _convert_model(model_name: str, onnx_dir: Path, device: str) -> None:
    """Export and optimize a model to ONNX.

    Uses the notebook-proven pattern:
      1. ORTModelForFeatureExtraction.from_pretrained(model, export=True)
      2. ORTOptimizer with AutoOptimizationConfig.O4() + GEMM GELU fusion

    Args:
        model_name: HuggingFace model name.
        onnx_dir: Target directory for the converted model.
        device: "cuda" or "cpu".

    Raises:
        ImportError: If optimum is not installed.
        RuntimeError: If export or optimization fails.
    """
    try:
        from optimum.onnxruntime import (
            AutoOptimizationConfig,
            ORTModelForFeatureExtraction,
            ORTOptimizer,
        )
    except ImportError as e:
        raise ImportError(
            "optimum[onnxruntime-gpu] is required for ONNX inference.\n"
            "Install with:  uv pip install -e .[onnx]\n"
            "           or: pip install optimum[onnxruntime-gpu]\n"
            "To disable ONNX, set use_onnx: false in search_config.json."
        ) from e

    provider = _resolve_provider(device)
    onnx_dir.mkdir(parents=True, exist_ok=True)

    _log.info(f"[ONNX] Auto-converting {model_name!r} (first run, one-time cost)...")
    _log.info(f"[ONNX] Output: {onnx_dir}")

    # Step 1: Export to ONNX
    _log.info("[ONNX] Step 1/2: Exporting model to ONNX...")
    try:
        ort_model = ORTModelForFeatureExtraction.from_pretrained(
            model_name,
            export=True,
            provider=provider,
        )
    except Exception as e:
        raise RuntimeError(
            f"[ONNX] Export failed for {model_name!r}: {e}\n"
            "The model architecture may not be supported by optimum for ONNX export.\n"
            "Set use_onnx: false in search_config.json to use PyTorch instead."
        ) from e

    # Step 2: Apply O4 optimization + GEMM GELU fusion
    _log.info(f"[ONNX] Step 2/2: Applying {_DEFAULT_OPTIMIZE} + GEMM GELU fusion...")
    try:
        optimizer = ORTOptimizer.from_pretrained(ort_model)
        opt_config_cls = getattr(AutoOptimizationConfig, _DEFAULT_OPTIMIZE)
        optimization_config = opt_config_cls()
        optimization_config.enable_gelu_approximation = False
        optimization_config.enable_gemm_fast_gelu_fusion = _GEMM_GELU
        optimizer.optimize(
            save_dir=str(onnx_dir),
            optimization_config=optimization_config,
        )
    except Exception as e:
        raise RuntimeError(f"[ONNX] Optimization failed: {e}") from e

    # Write metadata
    try:
        import optimum

        optimum_version = optimum.__version__
    except Exception:
        optimum_version = "unknown"

    model_file = (
        "model_optimized.onnx"
        if (onnx_dir / "model_optimized.onnx").is_file()
        else "model.onnx"
    )
    meta: dict[str, Any] = {
        "source_model": model_name,
        "optimization_level": _DEFAULT_OPTIMIZE,
        "gemm_gelu_fusion": _GEMM_GELU,
        "device": device,
        "provider": provider,
        "converted_at": datetime.now(UTC).isoformat(),
        "optimum_version": optimum_version,
        "model_file": model_file,
        "quality_validated": False,
    }
    (onnx_dir / "convert_meta.json").write_text(json.dumps(meta, indent=2))
    _log.info(f"[ONNX] Conversion complete → {onnx_dir}")


class ONNXModelLoader:
    """Loads ONNX embedding models, auto-converting from HuggingFace on first use.

    On the first call to load() with a model that hasn't been converted yet,
    performs the export + O4 optimization (a one-time cost). Subsequent loads
    read directly from the ONNX cache.

    Args:
        model_name: HuggingFace model name (e.g. "BAAI/bge-m3").
        cache_dir: HuggingFace model cache directory (used for fallback tokenizer lookup).
        device: Inference device — "cuda", "cpu", or "auto".
        onnx_cache_dir: Optional override for the ONNX output directory.
    """

    def __init__(
        self,
        model_name: str,
        cache_dir: str | None = None,
        device: str = "auto",
        onnx_cache_dir: Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._raw_device = device
        self._onnx_dir = onnx_cache_dir or _onnx_cache_dir(model_name)

    def _resolve_device(self) -> str:
        if self._raw_device != "auto":
            return self._raw_device
        try:
            import torch

            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    @property
    def onnx_dir(self) -> Path:
        return self._onnx_dir

    def is_converted(self) -> bool:
        """Return True if a valid ONNX model is already cached."""
        return _is_converted(self._onnx_dir)

    def convert_if_needed(self, device: str) -> None:
        """Run conversion if the ONNX model doesn't exist yet."""
        if not _is_converted(self._onnx_dir):
            _convert_model(self.model_name, self._onnx_dir, device)

    def load(self) -> tuple[Any, Any, str]:
        """Load the ONNX model, auto-converting from HuggingFace if needed.

        Returns:
            Tuple of (ort_model, tokenizer, resolved_device).

        Raises:
            ImportError: If optimum is not installed and conversion is needed.
            RuntimeError: If conversion or loading fails.
        """
        try:
            from optimum.onnxruntime import ORTModelForFeatureExtraction
            from transformers import AutoTokenizer
        except ImportError as e:
            raise ImportError(
                "optimum[onnxruntime-gpu] is required for ONNX inference.\n"
                "Install with:  uv pip install -e .[onnx]\n"
                "Set use_onnx: false in search_config.json to use PyTorch."
            ) from e

        device = self._resolve_device()
        provider = _resolve_provider(device)

        # Auto-convert on first run
        self.convert_if_needed(device)

        # Load the optimized ONNX model
        _log.info(
            f"[ONNX] Loading {self.model_name!r} from {self._onnx_dir} via {provider}"
        )
        # Suppress benign upstream tokenizer warning about incorrect regex pattern.
        # BGE-M3 (and Mistral-derived tokenizer configs) emit this during both
        # ORTModelForFeatureExtraction.from_pretrained() and AutoTokenizer.from_pretrained().
        try:
            import onnxruntime as ort

            session_options = ort.SessionOptions()
            # Suppress Memcpy/shape-op assignment warnings — ORT intentionally
            # assigns shape-related ops to CPU; the messages are noise, not errors.
            session_options.log_severity_level = 3  # ERROR only (0=VERBOSE, 3=ERROR)

            # Resolve the ONNX model filename from conversion metadata.
            # Optimum's default file resolution looks for "model.onnx" but our
            # optimized export produces "model_optimized.onnx" — passing file_name
            # explicitly silences the "could not find model.onnx" warning.
            #
            # convert_meta.json is read from a user-controlled cache directory, so
            # we treat `model_file` as untrusted: strip any path components, require
            # the .onnx extension, and fall back to the safe default if the resolved
            # path does not actually exist inside _onnx_dir.
            default_model_file = "model_optimized.onnx"
            model_file = default_model_file
            meta_path = self._onnx_dir / "convert_meta.json"
            if meta_path.is_file():
                try:
                    meta = json.loads(meta_path.read_text())
                    candidate = Path(meta.get("model_file", default_model_file)).name
                    if (
                        candidate.endswith(".onnx")
                        and (self._onnx_dir / candidate).is_file()
                    ):
                        model_file = candidate
                    else:
                        _log.warning(
                            f"[ONNX] Ignoring invalid model_file in convert_meta.json: "
                            f"{meta.get('model_file')!r} — using {default_model_file!r}"
                        )
                except Exception:
                    pass

            # Constrain ORT's own CUDA arena allocator so it cannot push the GPU
            # into WDDM shared-memory spillover on Windows.
            # Unlike PyTorch's set_per_process_memory_fraction (which ORT ignores),
            # gpu_mem_limit is respected by the CUDAExecutionProvider arena.
            # Uses the same effective-cap formula as set_vram_limit() so both
            # backends share the same budget.  Not applied for CPUExecutionProvider.
            provider_options = None
            if provider == "CUDAExecutionProvider":
                try:
                    from embeddings.embedder import compute_effective_vram_cap
                    from mcp_server.utils.config_helpers import (
                        get_config_via_service_locator as _get_cfg,
                    )

                    _cfg = _get_cfg()
                    _fraction = (
                        _cfg.performance.vram_limit_fraction
                        if _cfg and _cfg.performance
                        else 0.80
                    )
                    _onnx_cap_enabled = (
                        _cfg.performance.onnx_gpu_mem_limit
                        if _cfg and _cfg.performance
                        else True
                    )
                    if _onnx_cap_enabled:
                        _cap_result = compute_effective_vram_cap(_fraction)
                        if _cap_result is not None:
                            (
                                _,
                                _cap_bytes,
                                _free_gb,
                                _us_gb,
                                _other_gb,
                                _headroom_gb,
                            ) = _cap_result
                            provider_options = [
                                {
                                    "gpu_mem_limit": int(_cap_bytes),
                                    "arena_extend_strategy": "kSameAsRequested",
                                }
                            ]
                            _log.info(
                                f"[ONNX_VRAM] gpu_mem_limit={_cap_bytes / 1024**3:.2f}GB, "
                                f"arena=kSameAsRequested "
                                f"(free={_free_gb:.1f}GB, us={_us_gb:.1f}GB, "
                                f"other={_other_gb:.1f}GB, headroom={_headroom_gb:.1f}GB)"
                            )
                        else:
                            _log.debug(
                                "[ONNX_VRAM] CUDA not available — gpu_mem_limit not set"
                            )
                except Exception as _e:
                    _log.debug(f"[ONNX_VRAM] Could not compute cap (non-fatal): {_e}")

            # Suppress benign "incorrect regex pattern" warning from transformers.
            # BGE-M3 uses a Mistral-derived tokenizer that triggers this via logger.warning()
            # (not warnings.warn), so we must temporarily raise the transformers log level.
            _transformers_logger = logging.getLogger("transformers")
            _prev_level = _transformers_logger.level
            _transformers_logger.setLevel(logging.ERROR)
            try:
                ort_model = ORTModelForFeatureExtraction.from_pretrained(
                    str(self._onnx_dir),
                    file_name=model_file,
                    provider=provider,
                    session_options=session_options,
                    provider_options=provider_options,
                )
                try:
                    tokenizer = AutoTokenizer.from_pretrained(str(self._onnx_dir))
                except Exception:
                    # Unoptimized fallback exports may not have tokenizer files in the ONNX dir
                    tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            finally:
                _transformers_logger.setLevel(_prev_level)
        except Exception as e:
            raise RuntimeError(
                f"[ONNX] Failed to load from {self._onnx_dir}: {e}\n"
                f"Try re-converting: python tools/convert_onnx.py --model {self.model_name!r} --force"
            ) from e

        _log.info(f"[ONNX] Model loaded on {device} (provider={provider})")
        return ort_model, tokenizer, device
