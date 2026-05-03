"""Standalone ONNX conversion script for claude-context-local embedding models.

Exports a HuggingFace embedding model to ONNX with O4 graph optimization and
GEMM GELU fusion (best accuracy/speed tradeoff per the Optimum benchmark).

Usage:
    python tools/convert_onnx.py --model BAAI/bge-m3 --validate
    python tools/convert_onnx.py --model Alibaba-NLP/gte-modernbert-base --device cpu
    python tools/convert_onnx.py --list
    python tools/convert_onnx.py --model BAAI/bge-m3 --optimize O2 --output /custom/path

Install dependency first:
    uv pip install -e .[onnx]
    # or: pip install optimum[onnxruntime-gpu]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger(__name__)

# Models ineligible for ONNX export (custom code or generative arch)
_ONNX_INELIGIBLE = {
    "nomic-ai/CodeRankEmbed",  # NomicBERT requires trust_remote_code — no ORT config
    "jinaai/jina-reranker-v3",  # Listwise, custom model.rerank() API
    "Qwen/Qwen3-Reranker-0.6B",  # Generative causal LM, wrong paradigm for ONNX
    "Qwen/Qwen3-Reranker-4B",
    "Qwen/Qwen3-Embedding-0.6B",  # ORT requires position_ids not provided by tokenizer
    "BAAI/bge-code-v1",  # 2B params, GPU-bound — marginal ONNX gain
    "google/embeddinggemma-300m",  # Gemma3 ONNX trace breaks (TracerWarnings → wrong embeddings)
}

_OPTIMIZE_LEVELS = ("O1", "O2", "O3", "O4")


def _onnx_cache_dir(model_name: str, base: Path | None = None) -> Path:
    """Return the canonical ONNX output directory for a model.

    Convention: ~/.cache/huggingface/onnx/<org>--<name>/
    e.g. BAAI/bge-m3  →  ~/.cache/huggingface/onnx/BAAI--bge-m3/
    """
    sanitized = model_name.replace("/", "--")
    root = base or (Path.home() / ".cache" / "huggingface" / "onnx")
    return root / sanitized


def _is_converted(onnx_dir: Path) -> bool:
    """True if a valid converted model already exists at onnx_dir."""
    meta = onnx_dir / "convert_meta.json"
    return meta.is_file() and (
        (onnx_dir / "model_optimized.onnx").is_file()
        or (onnx_dir / "model.onnx").is_file()
    )


def list_models() -> None:
    """Print eligible models from MODEL_REGISTRY."""
    try:
        from search.config import MODEL_REGISTRY
    except ImportError:
        _log.error("Cannot import MODEL_REGISTRY. Run from the project root.")
        sys.exit(1)

    print("\nONNX-eligible models from MODEL_REGISTRY:")
    print("-" * 60)
    for name, cfg in MODEL_REGISTRY.items():
        if name in _ONNX_INELIGIBLE or cfg.get("trust_remote_code"):
            status = "SKIP"
            reason = (
                "trust_remote_code" if cfg.get("trust_remote_code") else "ineligible"
            )
        else:
            status = "OK  "
            reason = cfg.get("description", "")
        print(f"  [{status}]  {name}")
        if reason:
            print(f"          {reason}")
    print()


def _resolve_provider(device: str) -> str:
    """Map device string to ONNX Runtime execution provider."""
    if device == "cuda":
        return "CUDAExecutionProvider"
    return "CPUExecutionProvider"


def convert(
    model_name: str,
    optimize: str = "O4",
    device: str | None = None,
    output: Path | None = None,
) -> Path:
    """Export and optimize a model to ONNX.

    Args:
        model_name: HuggingFace model name (e.g. "BAAI/bge-m3").
        optimize: Optimization level — O1 / O2 / O3 / O4.
        device: "cuda" or "cpu". Auto-detected if None.
        output: Custom output directory. Defaults to ~/.cache/huggingface/onnx/<model>/.

    Returns:
        Path to the directory containing the optimized ONNX model.

    Raises:
        ImportError: If optimum[onnxruntime-gpu] is not installed.
        ValueError: If model is ONNX-ineligible.
        RuntimeError: If conversion or optimization fails.
    """
    if model_name in _ONNX_INELIGIBLE:
        raise ValueError(
            f"{model_name!r} is not eligible for ONNX export.\n"
            "Reason: custom architecture, generative model, or too large for meaningful gain.\n"
            "Run --list to see eligible models."
        )

    # Resolve output dir early so we can check the cache before importing optimum
    onnx_dir = output or _onnx_cache_dir(model_name)

    if _is_converted(onnx_dir):
        _log.info(
            "ONNX model already exists — skipping conversion (use --force to re-convert)."
        )
        return onnx_dir

    # Lazy import — only required when converting
    try:
        from optimum.onnxruntime import (
            AutoOptimizationConfig,
            ORTModelForFeatureExtraction,
            ORTOptimizer,
        )
    except ImportError as e:
        raise ImportError(
            "optimum[onnxruntime-gpu] is not installed.\n"
            "Install with:  uv pip install -e .[onnx]\n"
            "           or: pip install optimum[onnxruntime-gpu]"
        ) from e

    # Resolve device
    if device is None:
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"

    provider = _resolve_provider(device)

    _log.info(f"Model:     {model_name}")
    _log.info(f"Optimize:  {optimize}")
    _log.info(f"Device:    {device} ({provider})")
    _log.info(f"Output:    {onnx_dir}")

    onnx_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Export model to ONNX (in-memory export, not saved yet)
    _log.info("Step 1/2: Exporting to ONNX...")
    try:
        ort_model = ORTModelForFeatureExtraction.from_pretrained(
            model_name,
            export=True,
            provider=provider,
        )
    except Exception as e:
        raise RuntimeError(f"ONNX export failed for {model_name!r}: {e}") from e

    # Step 2: Optimize with O4 + GEMM GELU fusion
    # GEMM GELU fusion is more accurate than gelu_approximation (max diff 0.0004 vs 0.0011)
    # per the Faster_Embeddings_with_Optimum.ipynb benchmark.
    # For architectures not yet supported by ORTOptimizer (e.g. gemma3, qwen3), we fall back
    # to saving the unoptimized ONNX export so the model is still usable for inference.
    _log.info(f"Step 2/2: Applying {optimize} optimization + GEMM GELU fusion...")
    _optimized = True
    try:
        optimizer = ORTOptimizer.from_pretrained(ort_model)

        opt_config_cls = getattr(AutoOptimizationConfig, optimize)
        optimization_config = opt_config_cls()
        optimization_config.enable_gelu_approximation = False
        optimization_config.enable_gemm_fast_gelu_fusion = True

        optimizer.optimize(
            save_dir=str(onnx_dir),
            optimization_config=optimization_config,
        )
    except Exception as e:
        _unsupported = "not available yet" in str(
            e
        ) or "doesn't support the graph optimization" in str(e)
        if _unsupported:
            _log.warning(
                "ORTOptimizer does not support this architecture — saving unoptimized model."
            )
            _log.warning(f"  Reason: {e}")
            ort_model.save_pretrained(str(onnx_dir))
            # save_pretrained() saves model+config but not the tokenizer — save it explicitly
            try:
                from transformers import AutoTokenizer

                AutoTokenizer.from_pretrained(model_name).save_pretrained(str(onnx_dir))
            except Exception as tok_err:
                _log.warning(f"Could not save tokenizer to ONNX dir: {tok_err}")
            _optimized = False
        else:
            raise RuntimeError(f"ONNX optimization failed: {e}") from e

    # Verify the optimized model file exists
    model_file = onnx_dir / "model_optimized.onnx"
    if not model_file.is_file():
        # Some optimum versions save as model.onnx (unoptimized fallback)
        fallback = onnx_dir / "model.onnx"
        if fallback.is_file():
            _log.warning("Optimized model not found; falling back to model.onnx")
            model_file = fallback
        else:
            raise RuntimeError(
                f"No ONNX model file found in {onnx_dir}. Conversion may have failed."
            )

    # Write conversion metadata
    try:
        import optimum

        optimum_version = optimum.__version__
    except Exception:
        optimum_version = "unknown"

    meta = {
        "source_model": model_name,
        "optimization_level": optimize if _optimized else "none",
        "gemm_gelu_fusion": _optimized,
        "device": device,
        "provider": provider,
        "converted_at": datetime.now(UTC).isoformat(),
        "optimum_version": optimum_version,
        "model_file": model_file.name,
        "quality_validated": False,
    }
    (onnx_dir / "convert_meta.json").write_text(json.dumps(meta, indent=2))

    _log.info(f"Conversion complete → {onnx_dir}")
    return onnx_dir


def validate(model_name: str, onnx_dir: Path, device: str = "cpu") -> bool:
    """Quality gate: compare PyTorch vs ONNX embeddings.

    Encodes 10 code-like sentences with both backends. Passes if max absolute
    element-wise diff (on L2-normalised embeddings) < 0.001
    (threshold from the Optimum notebook benchmark: GEMM GELU max diff was 0.0004).

    Pooling strategy is read from MODEL_REGISTRY["onnx_pooling"] and must match
    what ONNXEmbeddingModel uses — otherwise validation results are meaningless for
    mean-pooling models (e.g. Qwen3-Embedding-0.6B, embeddinggemma-300m).

    Args:
        model_name: Original HuggingFace model name for PyTorch reference.
        onnx_dir: Directory containing the optimized ONNX model.
        device: Device for inference ("cuda" or "cpu").

    Returns:
        True if quality gate passes, False otherwise.
    """
    _log.info("Running quality validation (PyTorch vs ONNX)...")

    test_sentences = [
        "def embed_query(self, query: str) -> np.ndarray:",
        "class ModelLoader: handles loading and device management",
        "import torch\nfrom sentence_transformers import SentenceTransformer",
        "ONNX Runtime provides hardware-accelerated inference",
        "batch_embeddings = self.model.encode(batch_contents, convert_to_tensor=True)",
        "Search results are ranked candidates, not definitive answers",
        "def calculate_optimal_batch_size(embedding_dim, min_batch, max_batch):",
        "raise VRAMExhaustedError('VRAM exhausted, close other GPU apps')",
        "from optimum.onnxruntime import ORTModelForFeatureExtraction",
        "hybrid_score = bm25_weight * bm25_score + dense_weight * dense_score",
    ]

    try:
        import torch
        import torch.nn.functional as F  # noqa: N812
        from sentence_transformers import SentenceTransformer
        from transformers import AutoTokenizer
    except ImportError as e:
        _log.error(f"Missing dependency for validation: {e}")
        return False

    try:
        from optimum.onnxruntime import ORTModelForFeatureExtraction
    except ImportError as e:
        _log.error(f"optimum not available: {e}")
        return False

    # Resolve pooling strategy from MODEL_REGISTRY (default: "cls")
    try:
        from search.config import MODEL_REGISTRY

        pooling = MODEL_REGISTRY.get(model_name, {}).get("onnx_pooling", "cls")
    except ImportError:
        pooling = "cls"
    _log.info(f"Pooling strategy: {pooling!r} (from MODEL_REGISTRY)")

    provider = _resolve_provider(device)

    # Load PyTorch reference model
    _log.info("Loading PyTorch reference model...")
    pt_model = SentenceTransformer(model_name, device=device)
    pt_embeddings = pt_model.encode(
        test_sentences, convert_to_tensor=True, device=device
    )
    pt_embeddings = F.normalize(pt_embeddings.float(), p=2, dim=1)

    # Load ONNX model
    _log.info("Loading ONNX model...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(onnx_dir))
    except Exception:
        # Unoptimized fallback models may not have tokenizer saved in onnx_dir
        _log.info("Tokenizer not in ONNX dir — loading from original model name...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
    ort_model = ORTModelForFeatureExtraction.from_pretrained(
        str(onnx_dir), provider=provider
    )

    # Encode with ONNX
    encoded = tokenizer(
        test_sentences, padding=True, truncation=True, return_tensors="pt"
    )
    with torch.no_grad():
        ort_out = ort_model(**encoded)
    last_hidden = ort_out.last_hidden_state  # (N, seq_len, dim)
    if pooling == "mean":
        attention_mask = encoded["attention_mask"]
        mask_expanded = attention_mask.unsqueeze(-1).float()
        onnx_embeddings = (last_hidden * mask_expanded).sum(dim=1)
        onnx_embeddings = onnx_embeddings / mask_expanded.sum(dim=1).clamp(min=1e-9)
    else:  # cls
        onnx_embeddings = last_hidden[:, 0, :]
    onnx_embeddings = F.normalize(onnx_embeddings.float(), p=2, dim=1)

    # Element-wise |pt - onnx| on L2-normalised embeddings (Optimum benchmark metric).
    diffs = (pt_embeddings.cpu() - onnx_embeddings.cpu()).abs()
    max_diff = float(diffs.max())
    mean_diff = float(diffs.mean())
    threshold = 0.001

    _log.info(f"Max abs diff:  {max_diff:.6f}  (threshold: {threshold})")
    _log.info(f"Mean abs diff: {mean_diff:.6f}")

    if max_diff <= threshold:
        _log.info("Quality gate PASSED ✓")
        # Update metadata
        meta_path = onnx_dir / "convert_meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text())
            meta["quality_validated"] = True
            meta["quality_max_diff"] = max_diff
            meta["quality_mean_diff"] = mean_diff
            meta_path.write_text(json.dumps(meta, indent=2))
        return True
    else:
        _log.error(
            f"Quality gate FAILED ✗ — max diff {max_diff:.6f} exceeds threshold {threshold}"
        )
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export and optimize embedding models to ONNX for claude-context-local.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tools/convert_onnx.py --list
  python tools/convert_onnx.py --model BAAI/bge-m3 --validate
  python tools/convert_onnx.py --model Alibaba-NLP/gte-modernbert-base --optimize O4
  python tools/convert_onnx.py --model BAAI/bge-m3 --device cpu --output /tmp/bge-m3-onnx
        """,
    )
    parser.add_argument("--model", "-m", help="HuggingFace model name to convert")
    parser.add_argument(
        "--optimize",
        "-o",
        default="O4",
        choices=_OPTIMIZE_LEVELS,
        help="Optimization level (default: O4 — maximum fusions)",
    )
    parser.add_argument(
        "--device",
        "-d",
        choices=("cuda", "cpu"),
        default=None,
        help="Inference device (default: auto-detect)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Custom output directory (default: ~/.cache/huggingface/onnx/<model>/)",
    )
    parser.add_argument(
        "--validate",
        "-v",
        action="store_true",
        help="Run quality gate after conversion (PyTorch vs ONNX max diff < 0.001)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List ONNX-eligible models from MODEL_REGISTRY and exit",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Re-convert even if ONNX model already exists",
    )

    args = parser.parse_args()

    if args.list:
        list_models()
        return

    if not args.model:
        parser.error("--model is required unless --list is specified")

    if args.force:
        onnx_dir = args.output or _onnx_cache_dir(args.model)
        if onnx_dir.exists():
            import shutil

            # Sanity check: refuse to rmtree non-empty dirs that don't look like ONNX output
            _onnx_artifact_names = (
                "config.json",
                "tokenizer.json",
                "convert_meta.json",
            )
            _looks_like_onnx = any(onnx_dir.glob("*.onnx")) or any(
                (onnx_dir / f).exists() for f in _onnx_artifact_names
            )
            if any(onnx_dir.iterdir()) and not _looks_like_onnx:
                _log.error(
                    "--force refused: %s does not contain expected ONNX artifacts "
                    "(*.onnx / %s); pass an ONNX cache directory or remove it manually",
                    onnx_dir,
                    "/".join(_onnx_artifact_names),
                )
                sys.exit(2)

            _log.info(f"--force: removing existing ONNX cache at {onnx_dir}")
            shutil.rmtree(onnx_dir)

    try:
        onnx_dir = convert(
            model_name=args.model,
            optimize=args.optimize,
            device=args.device,
            output=args.output,
        )
    except (ValueError, ImportError, RuntimeError) as e:
        _log.error(str(e))
        sys.exit(1)

    if args.validate:
        # Default to CPU for quality validation — avoids ORT CUDA provider compatibility
        # issues on some systems. Use --device cuda to force CUDA validation explicitly.
        device = args.device or "cpu"
        ok = validate(args.model, onnx_dir, device=device)
        sys.exit(0 if ok else 1)


def _cuda_available() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False


if __name__ == "__main__":
    main()
