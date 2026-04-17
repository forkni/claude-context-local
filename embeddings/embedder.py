"""Multi-model embedder for generating code embeddings.

Supports multiple embedding models including:
- EmbeddingGemma (google/embeddinggemma-300m)
- BGE-M3 (BAAI/bge-m3)

Single-GPU assumption: all torch.cuda.* calls target device index 0.
"""

import contextlib
import gc
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from chunking.python_ast_chunker import CodeChunk
from embeddings.model_cache import ModelCacheManager
from embeddings.model_loader import ModelLoader
from embeddings.query_cache import QueryEmbeddingCache
from mcp_server.utils.config_helpers import (
    get_config_via_service_locator as _get_config_via_service_locator,
)
from search.exceptions import VRAMExhaustedError
from search.filters import normalize_path
from utils.timing import timed


# ===== BATCH SIZE MEMORY ESTIMATION =====
# Empirically derived from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18% overhead
FRAGMENTATION_OVERHEAD = 0.82  # 1.0 - 0.18 = 82% usable VRAM, 18% fragmentation

# ONNX activation cost FLOORS — used as a safety floor for ONNX Runtime models
# whose runtime warmup / architecture-formula estimates have proven too optimistic
# in practice (BFCArena single-op peaks blow past per-item × batch budget).
#
# These values were empirically calibrated under conditions that did NOT trigger
# ORT BFCArena OOM on an 8GB RTX laptop. They act as a lower bound: the final
# per-item cost is `max(measured_or_estimated, override_floor)`. New ONNX models
# without a floor entry continue to use measured/estimated values.
#
# DO NOT remove without re-validating against a force-reindex run on a memory-
# constrained GPU — these are the values that prevent OOM on first-try batches.
MODEL_ACTIVATION_COST_OVERRIDES_ONNX: dict[str, float] = {
    # BGE-M3: ORT measured 4.5GB activations at batch=16 → 0.28 GB/item.
    # Without floor, runtime warmup (batch=4) reports 0.053 GB/item → batch=16 OOMs
    # (single Add op wants 941 MB at batch=16 vs 5 MB free).
    "BAAI/bge-m3": 0.28,
    # GTE-ModernBERT (ONNX): batch=22 at 0.15 GB/item spilled to shared memory.
    # Without floor, runtime warmup reports 0.046 GB/item → batch=32 OOMs
    # (single MatMul wants 1.34 GB at batch=32 vs 875 MB free).
    "Alibaba-NLP/gte-modernbert-base": 0.25,
}


def _get_onnx_cost_floor(model_name: str | None) -> float:
    """Look up the ONNX activation cost floor for a model (0.0 if no floor)."""
    if not model_name:
        return 0.0
    if model_name in MODEL_ACTIVATION_COST_OVERRIDES_ONNX:
        return MODEL_ACTIVATION_COST_OVERRIDES_ONNX[model_name]
    # Fuzzy match for local paths (e.g. "/cache/BAAI/bge-m3")
    for key, cost in MODEL_ACTIVATION_COST_OVERRIDES_ONNX.items():
        if model_name.endswith(key) or key in model_name:
            return cost
    return 0.0


# Model types that use gated MLP (SwiGLU/GeGLU): gate_proj + up_proj + down_proj.
# These use 2× intermediate_size memory vs standard FFN (one up + down projection).
_GATED_MLP_MODEL_TYPES = frozenset(
    {
        "qwen2",
        "qwen3",
        "qwen3_moe",
        "llama",
        "mistral",
        "gemma",
        "gemma2",
        "gemma3",
        "gemma3_text",
        "phi3",
        "nomic_bert",  # NomicBERT uses SwiGLU
        "new",  # nomic-ai/nomic-bert uses model_type="new"
    }
)


def estimate_activation_gb_from_config(
    config: Any,
    is_onnx: bool = False,
) -> float:
    """Estimate activation memory per batch item from HuggingFace model config.

    Computes per-token peak activation from transformer architecture parameters
    (hidden_size, intermediate_size, num_key_value_heads, head_dim), then scales
    by a conservative effective sequence length and safety multiplier.

    This replaces hardcoded tier-based constants with a formula that automatically
    handles different architectures (GQA, SwiGLU, standard FFN) and context lengths.

    Formula (per token, one transformer layer):
        attn_peak = (3·hidden + 2·n_kv·head_dim) · dtype_bytes
        mlp_peak  = (2·hidden + 2·intermediate) · dtype_bytes   [gated MLP]
                  = (2·hidden +   intermediate) · dtype_bytes   [standard FFN]
        peak_per_token = max(attn_peak, mlp_peak) + hidden·dtype_bytes

    Validated against all 6 registered models with SAFETY=15, T_eff=1024:
        EmbeddingGemma-300M:  0.13 GB  (observed ~0.04 GB)   safe
        BGE-M3 (ONNX):        0.41 GB  (observed  0.28 GB)   safe
        BGE-Code-v1:          0.65 GB  (observed  0.40 GB)   safe
        Qwen3-Embed-0.6B:     0.26 GB  (observed  0.27 GB)   safe
        CodeRankEmbed:        0.24 GB  (observed  0.25 GB)   safe
        GTE-ModernBERT (ONNX):0.26 GB  (observed  0.25 GB)   safe

    Args:
        config: HuggingFace PretrainedConfig (has .hidden_size, etc.)
        is_onnx: True for ONNX Runtime backend (applies 2× overhead factor)

    Returns:
        Conservative activation memory per batch item in GB (minimum 0.04 GB)
    """
    hidden: int = getattr(config, "hidden_size", 768)
    n_heads: int = getattr(config, "num_attention_heads", 12)
    n_kv: int = getattr(config, "num_key_value_heads", n_heads)
    # head_dim may be explicit (Gemma, Qwen3) or derived from hidden/heads
    head_dim: int = getattr(config, "head_dim", None) or (hidden // n_heads)
    # NomicBERT exposes intermediate as n_inner; fall back to 4×hidden
    intermediate: int = (
        getattr(config, "intermediate_size", None)
        or getattr(config, "n_inner", None)
        or 4 * hidden
    )
    model_type: str = getattr(config, "model_type", "").lower()
    _dtype = getattr(config, "torch_dtype", None)
    _fp32 = getattr(torch, "float32", None) if torch is not None else None
    dtype_bytes: int = (
        4 if ((_dtype is not None and _dtype == _fp32) or _dtype == "float32") else 2
    )

    has_gated_mlp = model_type in _GATED_MLP_MODEL_TYPES

    # Attention peak per token: residual + norm_output + Q(≈hidden) + K + V kept simultaneously
    attn_peak = (3 * hidden + 2 * n_kv * head_dim) * dtype_bytes
    # MLP peak per token: residual + norm_output + gate + up (gated) or just up (standard)
    mlp_peak = (
        2 * hidden + (2 * intermediate if has_gated_mlp else intermediate)
    ) * dtype_bytes

    # Running hidden state adds hidden per token on top of peak layer usage
    peak_per_token = max(attn_peak, mlp_peak) + hidden * dtype_bytes

    # Effective sequence length: code chunks are 200–800 tokens after tokenization.
    # Cap at 1024 — using model.max_ctx (up to 32K) would massively over-estimate.
    t_eff = 1024

    # Safety multiplier: accounts for PyTorch/ORT allocator overhead, GEMM workspace
    # buffers, and block retention. Calibrated to be ≥ empirically observed costs.
    safety = 15
    # ORT CUDAExecutionProvider: pre-plans memory arenas for entire graph + no
    # Flash-Attention (materializes T×T attention matrix) ≈ 2× PyTorch overhead.
    onnx_factor = 2.0 if is_onnx else 1.0

    gb_per_item = peak_per_token * t_eff * safety * onnx_factor / (1024**3)
    return max(gb_per_item, 0.04)  # 40 MB floor


# Configure PyTorch CUDA allocator BEFORE any torch imports
# This must be done early to prevent fragmentation and enable better memory management
def _configure_cuda_allocator() -> None:
    """Configure PyTorch CUDA allocator for reduced fragmentation.

    Must be called BEFORE any CUDA operations (import torch.cuda, tensor.cuda(), etc.)
    Sets PYTORCH_CUDA_ALLOC_CONF environment variable with optimal settings:
    - garbage_collection_threshold: Proactively frees old blocks at 80% usage
    - max_split_size_mb: Prevents splitting blocks >512MB (reduces fragmentation)

    Note: expandable_segments not included as it's unsupported on Windows.
    """
    if os.environ.get("PYTORCH_CUDA_ALLOC_CONF"):
        return  # User has custom config, don't override

    # garbage_collection_threshold: Proactive memory cleanup at 80% capacity
    #   Helps prevent fragmentation by recycling old blocks before memory fills
    # max_split_size_mb: Prevent large block splitting (reduces fragmentation slivers)
    #   Blocks >512MB won't be split, reducing memory fragmentation
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = (
        "garbage_collection_threshold:0.8,max_split_size_mb:512"
    )
    logging.getLogger(__name__).info(
        "[CUDA_ALLOC] Configured allocator: "
        "garbage_collection_threshold=0.8, max_split_size_mb=512"
    )


# Call early, before torch imports
_configure_cuda_allocator()

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
except ImportError:
    torch = None


def compute_effective_vram_cap(
    fraction: float,
) -> tuple[float, int, float, float, float, float] | None:
    """Compute effective VRAM cap accounting for other-process allocations.

    Pure function — reads current GPU state, does not set any limits or produce
    any side effects.  Call this from both the PyTorch-cap path
    (``set_vram_limit``) and the ORT-cap path (``onnx_loader.py``) to ensure
    both backends use identical budgets.

    Formula::

        T            = total device VRAM
        F            = system-wide free VRAM (excludes ALL processes)
        A_us         = bytes our PyTorch process currently holds
        A_other      = T - F - A_us  (held by every other process)
        headroom     = (1 − fraction) × T   (safety reserve)
        physical_cap = A_us + F − headroom  (max we can hold without spill)
        cap          = max(min(user_cap, physical_cap), A_us)
        effective_fraction = clamp(cap / T, 0.05, fraction)

    Args:
        fraction: Requested fraction of total VRAM (0.05–1.0).

    Returns:
        ``(effective_fraction, cap_bytes, free_gb, us_gb, other_gb, headroom_gb)``
        or ``None`` if CUDA is unavailable or measurement fails.

        - *effective_fraction* — value for ``set_per_process_memory_fraction``
        - *cap_bytes*          — value for ORT ``gpu_mem_limit`` provider option
        - *free_gb / us_gb / other_gb / headroom_gb* — diagnostic values for logs
    """
    if not torch or not torch.cuda.is_available():
        return None
    try:
        free_b, total_b = torch.cuda.mem_get_info(0)
        us_b = torch.cuda.memory_allocated(0)
        other_b = max(0, total_b - free_b - us_b)

        headroom_b = int((1.0 - fraction) * total_b)
        user_cap_b = int(fraction * total_b)
        physical_cap_b = us_b + free_b - headroom_b

        cap_b = min(user_cap_b, physical_cap_b)
        cap_b = max(cap_b, us_b)  # cannot shrink below what we already hold

        effective_fraction = (cap_b / total_b) if total_b > 0 else fraction
        effective_fraction = max(0.05, min(effective_fraction, fraction))

        return (
            effective_fraction,
            int(cap_b),
            free_b / 1024**3,
            us_b / 1024**3,
            other_b / 1024**3,
            headroom_b / 1024**3,
        )
    except (RuntimeError, ValueError, AssertionError):
        return None


def set_vram_limit(fraction: float = 0.90) -> bool:
    """Set hard VRAM limit on the PyTorch CUDA allocator to prevent spillover.

    On Windows, the NVIDIA driver preemptively evicts to shared memory when
    VRAM approaches capacity. This hard limit prevents that by raising OOM
    errors instead of spilling (which is much faster than slow spillover).

    The effective fraction is computed by ``compute_effective_vram_cap`` from
    live ``mem_get_info`` readings so that memory held by other processes
    (browser, games, other ML jobs) is subtracted from our budget.

    It is safe and expected to call this function multiple times; each call
    re-measures the system state and re-applies the cap.

    **Note on `allow_ram_fallback`**: when True in config, this function
    returns without applying any cap — the PyTorch allocator is uncapped and
    the OS may spill to shared RAM.  The flag does *not* affect the ORT
    ``gpu_mem_limit`` cap (set in ``embeddings/onnx_loader.py``), which is
    always-on when ``onnx_gpu_mem_limit=true``.

    **ORT / FAISS**: ``set_per_process_memory_fraction`` only governs the
    PyTorch CUDA allocator.  ORT's ``CUDAExecutionProvider`` and FAISS GPU
    indexes use their own allocators and are not constrained here.

    Args:
        fraction: Requested fraction of dedicated VRAM (default: 0.90 = 90%).
            The *effective* fraction may be lower when other processes hold VRAM.
            Recommended: 0.80–0.90 depending on GPU headroom needs.

    Returns:
        True if limit was set (or skipped due to allow_ram_fallback), else False.
    """
    if not torch or not torch.cuda.is_available():
        return False

    # Check if RAM fallback is allowed — if so, skip the PyTorch cap only.
    try:
        config = _get_config_via_service_locator()
        if config and config.performance.allow_ram_fallback:
            logging.getLogger(__name__).info(
                "[VRAM_LIMIT] RAM fallback allowed - skipping PyTorch VRAM cap"
            )
            return True  # Don't set limit, allow PyTorch spillover
    except Exception as e:
        logging.getLogger(__name__).debug(f"Config not available, using defaults: {e}")

    logger = logging.getLogger(__name__)
    result = compute_effective_vram_cap(fraction)
    if result is None:
        logger.warning("[VRAM_LIMIT] Failed to measure VRAM state — cap not applied")
        return False

    effective_fraction, cap_b, free_gb, us_gb, other_gb, headroom_gb = result

    # Warn when free memory is below the requested headroom (external GPU pressure).
    if free_gb < headroom_gb:
        logger.warning(
            f"[VRAM_LIMIT] Cannot honor requested headroom — GPU under external "
            f"pressure. Requested={fraction:.0%}, effective={effective_fraction:.0%} "
            f"(free={free_gb:.1f}GB, us={us_gb:.1f}GB, "
            f"other={other_gb:.1f}GB, headroom={headroom_gb:.1f}GB)"
        )
    else:
        logger.info(
            f"[VRAM_LIMIT] Requested={fraction:.0%}, effective={effective_fraction:.0%} "
            f"(free={free_gb:.1f}GB, us={us_gb:.1f}GB, "
            f"other={other_gb:.1f}GB, headroom={headroom_gb:.1f}GB)"
        )

    try:
        torch.cuda.set_per_process_memory_fraction(effective_fraction, device=0)
        return True
    except (RuntimeError, ValueError, AssertionError, TypeError) as e:
        logger.warning(f"[VRAM_LIMIT] Failed to set: {e}")
        return False


def calculate_optimal_batch_size(
    embedding_dim: int = 768,
    min_batch: int = 32,
    max_batch: int = 256,  # Conservative cap to prevent spillover
    memory_fraction: float = 0.8,  # Target 80% VRAM utilization (20% headroom)
    model_vram_gb: float = 0.0,
    model_name: str | None = None,
    activation_gb_per_item: float = 0.0,
    ort_cap_gb: float = 0.0,
) -> int:
    """Calculate optimal batch size from architecture-derived activation memory cost.

    Uses a mathematically derived activation cost per batch item (from model
    architecture parameters via ``estimate_activation_gb_from_config()``) rather
    than hardcoded tier-based constants.  The cost is supplied by the caller so
    that both runtime-measured and formula-estimated values can be used without
    duplicating GPU probing logic here.

    Args:
        embedding_dim: Embedding output dimension (unused, kept for API compat)
        min_batch: Minimum batch size (safety floor, default: 32)
        max_batch: Maximum batch size (conservative cap, default: 256)
        memory_fraction: Target VRAM utilization (default: 0.8 = 80%)
        model_vram_gb: Model weight VRAM in GB (used only for logging)
        model_name: Model identifier (used only for logging)
        activation_gb_per_item: Pre-computed activation cost per batch item in GB.
            Pass 0.0 to signal "unknown" — a 40 MB floor will be used.

    Returns:
        Batch size clamped to [min_batch, max_batch]

    Examples:
        >>> # RTX 3070 (8GB), BGE-M3, 0.28 GB/item measured
        >>> calculate_optimal_batch_size(activation_gb_per_item=0.28, model_vram_gb=1.07)
        16  # ~(4GB free × 0.8 × 0.82) / 0.28

        >>> # RTX 4090 (24GB), Qwen3-0.6B, 0.27 GB/item measured
        >>> calculate_optimal_batch_size(activation_gb_per_item=0.27, model_vram_gb=1.1)
        53  # ~(16GB free × 0.8 × 0.82) / 0.27
    """
    if not torch or not torch.cuda.is_available():
        return min_batch  # CPU fallback

    try:
        # Get system-wide free/total GPU memory (accounts for ALL processes)
        free_memory, total_memory = torch.cuda.mem_get_info(0)
        total_gb = total_memory / (1024**3)
        free_gb = free_memory / (1024**3)

        # Use free memory — model weights are already loaded so they're excluded
        available_gb = free_gb

        # For ONNX backend: constrain to the ORT arena's remaining activation budget.
        # ORT's CUDAExecutionProvider has a hard gpu_mem_limit; the model weights
        # already consume model_vram_gb of that cap.  Using system-wide free_gb
        # would overestimate — ORT cannot exceed its cap regardless of system free.
        if ort_cap_gb > 0.0:
            ort_remaining_gb = max(0.0, ort_cap_gb - model_vram_gb)
            if ort_remaining_gb < available_gb:
                available_gb = ort_remaining_gb

        # Apply fragmentation factor: PyTorch caching allocator reserves ~18% extra
        # Validated from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18%
        target_activation_gb = available_gb * memory_fraction * FRAGMENTATION_OVERHEAD

        # Use provided activation cost per item (0.0 → 40 MB safety floor)
        gb_per_item = activation_gb_per_item if activation_gb_per_item > 0 else 0.04

        # Calculate optimal batch size from activation budget
        optimal_batch = int(target_activation_gb / gb_per_item)

        # Apply GPU tier limits
        if total_gb <= 6:  # minimal tier (<6GB)
            max_batch = min(max_batch, 16)
            min_batch = min(min_batch, 2)
        elif total_gb <= 10:  # laptop tier (6–10GB)
            max_batch = min(max_batch, 32)
            min_batch = min(min_batch, 4)

        # Additional cap based on actual free memory (other processes may hold VRAM)
        if free_gb < 4:
            max_batch = min(max_batch, 8)
        elif free_gb < 6:
            max_batch = min(max_batch, 16)

        # Clamp to safe bounds
        result = max(min_batch, min(optimal_batch, max_batch))

        logger = logging.getLogger(__name__)
        ort_info = (
            f", ORT cap: {ort_cap_gb:.1f}GB → remaining: {max(0.0, ort_cap_gb - model_vram_gb):.1f}GB"
            if ort_cap_gb > 0.0
            else ""
        )
        logger.info(
            f"[DYNAMIC_BATCH] GPU: {free_gb:.1f}GB free / {total_gb:.1f}GB total, "
            f"model: {model_vram_gb:.1f}GB ({model_name or 'unknown'}){ort_info}, "
            f"available: {available_gb:.1f}GB → "
            f"target: {target_activation_gb:.1f}GB "
            f"({memory_fraction:.0%} × {FRAGMENTATION_OVERHEAD:.0%} frag), "
            f"cost: {gb_per_item:.3f}GB/item → batch: {result} chunks"
        )

        return result

    except (RuntimeError, ValueError) as e:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[DYNAMIC_BATCH] Failed to calculate batch size: {e}, "
            f"using min_batch={min_batch}"
        )
        return min_batch  # Fallback on error


def parse_vram_gb_from_registry(model_name: str) -> float:
    """Parse VRAM estimate from MODEL_REGISTRY for upfront batch sizing.

    Handles formats: "8-10GB" (range) → 10.0, "2.3GB" (exact) → 2.3, "2GB" → 2.0
    Uses upper bound of range for conservative batch sizing.

    Args:
        model_name: Model identifier (e.g., "BAAI/bge-code-v1")

    Returns:
        VRAM estimate in GB, or 0.0 if not found/parseable

    Examples:
        >>> parse_vram_gb_from_registry("BAAI/bge-code-v1")
        10.0  # From "8-10GB" (upper bound)

        >>> parse_vram_gb_from_registry("Qwen/Qwen3-Embedding-0.6B")
        2.3  # From "2.3GB"

        >>> parse_vram_gb_from_registry("BAAI/bge-m3")
        1.5  # From "1-1.5GB" (upper bound, actual measured: 1.07GB)
    """
    import re

    from search.config import get_model_config

    config = get_model_config(model_name)
    if not config:
        return 0.0

    vram_str = config.get("vram_gb", "")
    if not vram_str:
        return 0.0

    # Handle range format: "8-10GB" → use upper bound (10.0)
    range_match = re.match(r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)GB", vram_str)
    if range_match:
        return float(range_match.group(2))  # Upper bound for safety

    # Handle exact format: "2.3GB" or "2GB"
    exact_match = re.match(r"(\d+(?:\.\d+)?)GB", vram_str)
    if exact_match:
        return float(exact_match.group(1))

    return 0.0


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: np.ndarray
    chunk_id: str
    metadata: dict[str, Any]


class CodeEmbedder:
    """Multi-model embedder for generating code embeddings.

    Supports multiple embedding models with automatic configuration detection.
    Default model is google/embeddinggemma-300m.
    """

    def __init__(
        self,
        model_name: str = "google/embeddinggemma-300m",
        cache_dir: str | None = None,
        device: str = "auto",
    ) -> None:
        self.model_name = model_name
        self.cache_dir = cache_dir or str(
            Path.home() / ".cache" / "huggingface" / "hub"
        )
        self.device = device
        self._model = None
        self._logger = logging.getLogger(__name__)
        self._model_config = None

        # Set hard VRAM limit early to prevent shared memory spillover
        # This must be called before any CUDA allocations
        # Try to get fraction from config, fallback to 0.90
        try:
            config = _get_config_via_service_locator()
            if config and config.performance:
                fraction = config.performance.vram_limit_fraction
            else:
                fraction = 0.90
        except (RuntimeError, AttributeError):
            fraction = 0.90
        set_vram_limit(fraction)

        # Query embedding cache (LRU)
        self._query_cache = QueryEmbeddingCache(max_size=128)

        # Model cache manager
        self._cache_manager = ModelCacheManager(
            model_name=model_name,
            cache_dir=cache_dir or str(Path.home() / ".cache" / "huggingface" / "hub"),
            model_config_getter=self._get_model_config,
        )

        # Model loader
        self._model_loader = ModelLoader(
            model_name=model_name,
            cache_dir=cache_dir or str(Path.home() / ".cache" / "huggingface" / "hub"),
            device=device,
            cache_manager=self._cache_manager,
            model_config_getter=self._get_model_config,
        )

        # Track per-model VRAM usage
        self._model_vram_usage: dict[str, float] = {}  # model_key -> VRAM MB

        # Setup logging
        logging.basicConfig(level=logging.INFO)

    @classmethod
    def get_supported_models(cls) -> dict[str, dict[str, Any]]:
        """Get dictionary of supported models and their configurations."""
        from search.config import get_model_registry

        return get_model_registry()

    def _get_model_config(self) -> dict[str, Any]:
        """Get configuration for the current model.

        Returns model-specific config including dimension, prompt_name, etc.
        Falls back to sensible defaults for unknown models.
        """
        if self._model_config is not None:
            return self._model_config

        from search.config import get_model_config

        # Try to get from registry
        config = get_model_config(self.model_name)
        if config:
            self._model_config = config
            return config

        # Auto-detect based on model name for unknown models
        model_lower = self.model_name.lower()

        if "gemma" in model_lower:
            self._model_config = {
                "dimension": 768,
                "prompt_name": "Retrieval-document",
                "description": "EmbeddingGemma model",
            }
        elif "bge-m3" in model_lower or "bge_m3" in model_lower:
            self._model_config = {
                "dimension": 1024,
                "prompt_name": None,  # BGE-M3 doesn't use prompts
                "description": "BGE-M3 model",
            }
        else:
            # Default fallback
            self._logger.warning(
                f"Unknown model {self.model_name}, using default config"
            )
            self._model_config = {
                "dimension": 768,
                "prompt_name": None,
                "description": "Unknown model",
            }

        return self._model_config

    # ===== Model Loading Methods (delegated to ModelLoader) =====

    def _log_gpu_memory(self, stage: str) -> None:
        """Delegate to ModelLoader.log_gpu_memory()."""
        self._model_loader.log_gpu_memory(stage)

    def _get_torch_dtype(self) -> "torch.dtype":
        """Delegate to ModelLoader.get_torch_dtype()."""
        return self._model_loader.get_torch_dtype()

    def _is_gpu_device(self) -> bool:
        """Check if current device is GPU (cuda/mps).

        Returns:
            True if device is GPU, False if CPU.
        """
        if not self.device:
            return False

        device_str = str(self.device).lower()
        return "cuda" in device_str or "mps" in device_str

    def _check_vram_status(self) -> tuple[float, bool, bool]:
        """Check VRAM usage and return (usage_pct, should_warn, should_abort).

        Returns:
            Tuple of (usage_percentage, should_warn, should_abort)
            - usage_percentage: Current VRAM usage as percentage (0.0-1.0)
            - should_warn: True if usage > 85%
            - should_abort: True if usage > 95%
        """
        vram_warning_threshold = 0.85  # 85% usage
        vram_abort_threshold = 0.95  # 95% usage

        if not torch or not torch.cuda.is_available():
            return 0.0, False, False

        try:
            # Use PyTorch allocated memory, not CUDA driver-level mem_get_info().
            # mem_get_info() includes PyTorch's caching allocator reserved blocks,
            # which are pre-allocated and reused — not actual working-set pressure.
            # This caused false 87% warnings regardless of batch size.
            allocated = torch.cuda.memory_allocated(0)
            total_memory = torch.cuda.get_device_properties(0).total_memory
            usage_pct = allocated / total_memory if total_memory > 0 else 0.0

            should_warn = usage_pct > vram_warning_threshold
            should_abort = usage_pct > vram_abort_threshold

            return usage_pct, should_warn, should_abort
        except RuntimeError as e:
            self._logger.warning(f"Failed to check VRAM status: {e}")
            return 0.0, False, False

    @property
    def model(self) -> SentenceTransformer | None:
        """Lazy loading of the model."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self) -> None:
        """Delegate to ModelLoader.load()."""
        self._model, self.device = self._model_loader.load()
        # Sync VRAM usage tracking from ModelLoader
        self._model_vram_usage.update(self._model_loader.model_vram_usage)

    def _extract_import_context(self, file_path: str, max_imports: int = 10) -> str:
        """Extract first N import statements from file header.

        Args:
            file_path: Absolute path to the source file
            max_imports: Maximum number of import lines to extract

        Returns:
            String containing import statements, or empty string if none found
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = []
                for line in f:
                    stripped = line.strip()
                    # Collect import statements
                    if stripped.startswith(("import ", "from ")):
                        lines.append(line.rstrip())
                        if len(lines) >= max_imports:
                            break
                    # Stop at first non-import, non-comment, non-blank line
                    elif (
                        stripped
                        and not stripped.startswith("#")
                        and not stripped.startswith('"""')
                        and not stripped.startswith("'''")
                    ):
                        # Check if we've already collected imports
                        if lines:
                            break
                        # Otherwise keep scanning (might have docstring before imports)
                return "\n".join(lines)
        except (OSError, UnicodeDecodeError) as e:
            self._logger.debug(
                f"Failed to extract import context from {file_path}: {e}"
            )
            return ""

    def _get_class_signature(self, chunk: CodeChunk, max_lines: int = 5) -> str:
        """Extract parent class signature (header + docstring) for method chunks.

        Args:
            chunk: CodeChunk with chunk_type='method' and parent_name set
            max_lines: Maximum number of lines to extract from class definition

        Returns:
            String containing class signature, or empty string if not a method
        """
        # Only applicable to methods
        if chunk.chunk_type != "method" or not chunk.parent_name:
            return ""

        try:
            with open(chunk.file_path, encoding="utf-8") as f:
                content = f.read()

            # Find class definition containing this method
            # Pattern: "class ClassName" or "class ClassName(BaseClass)"
            import re

            class_pattern = rf"^class\s+{re.escape(chunk.parent_name)}\s*[\(:]"

            match = re.search(class_pattern, content, re.MULTILINE)
            if not match:
                return ""

            # Extract class header + first few lines (likely docstring)
            start = match.start()
            lines = content[start:].split("\n")[:max_lines]
            signature = "\n".join(lines).strip()

            # Clean up: if docstring is incomplete, truncate at opening quote
            if '"""' in signature or "'''" in signature:
                # Find first opening quote
                first_quote_idx = min(
                    signature.find('"""') if '"""' in signature else len(signature),
                    signature.find("'''") if "'''" in signature else len(signature),
                )
                # Find matching closing quote
                if '"""' in signature[first_quote_idx:]:
                    close_idx = signature.find('"""', first_quote_idx + 3)
                    if close_idx != -1:
                        signature = signature[: close_idx + 3]
                elif "'''" in signature[first_quote_idx:]:
                    close_idx = signature.find("'''", first_quote_idx + 3)
                    if close_idx != -1:
                        signature = signature[: close_idx + 3]

            return signature

        except (OSError, UnicodeDecodeError) as e:
            self._logger.debug(
                f"Failed to extract class signature for {chunk.parent_name}: {e}"
            )
            return ""

    def create_embedding_content(self, chunk: CodeChunk, max_chars: int = 6000) -> str:
        """Create clean content for embedding generation with size limits.

        Supports context enhancement features (v0.8.0+):
        - Import context: Include import statements from file header
        - Class context: Include parent class signature for methods

        Configuration is controlled via search/config.py EmbeddingConfig:
        - enable_import_context (bool, default: True)
        - enable_class_context (bool, default: True)
        - max_import_lines (int, default: 10)
        - max_class_signature_lines (int, default: 5)
        """
        # Prepare clean content without fabricated headers
        content_parts = []

        # Get configuration via ServiceLocator
        try:
            config = _get_config_via_service_locator()
            enable_import_ctx = config.embedding.enable_import_context
            enable_class_ctx = config.embedding.enable_class_context
            max_import_lines = config.embedding.max_import_lines
            max_class_sig_lines = config.embedding.max_class_signature_lines
            enable_structural_header = config.embedding.enable_structural_header
        except Exception as e:
            self._logger.debug(f"Failed to load context config, using defaults: {e}")
            # Fallback to defaults
            enable_import_ctx = True
            enable_class_ctx = True
            max_import_lines = 10
            max_class_sig_lines = 5
            enable_structural_header = True

        # NEW (v0.9.0): Structural header for module/name/type disambiguation
        if enable_structural_header:
            header_parts = []
            # Add file path for module context
            if hasattr(chunk, "relative_path") and chunk.relative_path:
                header_parts.append(chunk.relative_path)

            # Add chunk type + qualified name (ClassName.method_name or function_name)
            type_name = ""
            if chunk.chunk_type:
                type_name = chunk.chunk_type
            if chunk.parent_name and chunk.name:
                type_name += f" {chunk.parent_name}.{chunk.name}"
            elif chunk.name:
                type_name += f" {chunk.name}"

            if type_name:
                header_parts.append(type_name.strip())

            # Prepend structural header line if any parts exist
            if header_parts:
                content_parts.append(f"# {' | '.join(header_parts)}")

        # NEW: Add import context from file header (if enabled and available)
        if enable_import_ctx:
            import_context = self._extract_import_context(
                chunk.file_path, max_imports=max_import_lines
            )
            if import_context:
                content_parts.append(f"# Imports:\n{import_context}\n")

        # NEW: Add class context for methods (skeleton approach, if enabled)
        if enable_class_ctx:
            class_context = self._get_class_signature(
                chunk, max_lines=max_class_sig_lines
            )
            if class_context:
                content_parts.append(f"# Parent class:\n{class_context}\n")

        # Add docstring if available (important context for code understanding)
        docstring_budget = 300
        if chunk.docstring:
            # Keep docstring but limit length to stay within token budget
            docstring = (
                chunk.docstring[:docstring_budget] + "..."
                if len(chunk.docstring) > docstring_budget
                else chunk.docstring
            )
            content_parts.append(f'"""{docstring}"""')

        # Calculate remaining budget for code content
        # Account for import context, class context, and docstring
        context_len = sum(len(part) for part in content_parts)
        remaining_budget = max_chars - context_len - 10  # small buffer

        # Add the actual code content, truncating if necessary
        if len(chunk.content) <= remaining_budget:
            content_parts.append(chunk.content)
        else:
            # Smart truncation: try to keep function signature and important parts
            lines = chunk.content.split("\n")
            if len(lines) > 3:
                # Keep first few lines (signature) and last few lines (return/conclusion)
                head_lines = []
                tail_lines = []
                current_length = context_len

                # Add head lines (function signature, early logic)
                for _i, line in enumerate(lines[: min(len(lines) // 2, 20)]):
                    if current_length + len(line) + 1 > remaining_budget * 0.7:
                        break
                    head_lines.append(line)
                    current_length += len(line) + 1

                # Add tail lines (return statements, conclusions) if space remains
                remaining_space = (
                    remaining_budget - current_length - 20
                )  # buffer for "..."
                for line in reversed(lines[-min(len(lines) // 3, 10) :]):
                    if len("\n".join(tail_lines)) + len(line) + 1 > remaining_space:
                        break
                    tail_lines.insert(0, line)

                if tail_lines:
                    truncated_content = (
                        "\n".join(head_lines)
                        + "\n    # ... (truncated) ...\n"
                        + "\n".join(tail_lines)
                    )
                else:
                    truncated_content = (
                        "\n".join(head_lines) + "\n    # ... (truncated) ..."
                    )
                content_parts.append(truncated_content)
            else:
                # For short chunks, just truncate at character limit
                content_parts.append(
                    chunk.content[:remaining_budget] + "..."
                    if len(chunk.content) > remaining_budget
                    else chunk.content
                )

        return "\n".join(content_parts)

    def embed_chunk(self, chunk: CodeChunk) -> EmbeddingResult:
        """Generate embedding for a single code chunk."""
        content = self.create_embedding_content(chunk)

        # Get model-specific configuration
        model_config = self._get_model_config()
        passage_prefix = model_config.get("passage_prefix", "")

        # Prepend passage prefix if it exists
        content_to_embed = passage_prefix + content if passage_prefix else content

        # Use convert_to_tensor for GPU to avoid CPU<->GPU transfers
        use_tensor = self._is_gpu_device()
        embedding = self.model.encode(
            [content_to_embed],
            show_progress_bar=False,
            convert_to_tensor=use_tensor,
            device=self.device if use_tensor else None,
        )[0]

        # Convert back to numpy if tensor
        # Note: bf16 tensors must be converted to float32 first (numpy doesn't support bf16)
        if torch and torch.is_tensor(embedding):
            embedding = embedding.cpu().float().numpy()

        # Create unique chunk ID with normalized path separators
        normalized_path = normalize_path(str(chunk.relative_path))
        chunk_id = (
            f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
        )
        # Build qualified name for methods/functions inside classes
        qualified_name = (
            f"{chunk.parent_name}.{chunk.name}"
            if chunk.parent_name and chunk.name
            else chunk.name
        )
        if qualified_name:
            chunk_id += f":{qualified_name}"

        # Prepare metadata
        metadata = {
            "file_path": chunk.file_path,
            "relative_path": chunk.relative_path,
            "folder_structure": chunk.folder_structure,
            "chunk_type": chunk.chunk_type,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "name": chunk.name,
            "parent_name": chunk.parent_name,
            "parent_chunk_id": chunk.parent_chunk_id,
            "docstring": chunk.docstring,
            "decorators": chunk.decorators,
            "imports": chunk.imports,
            "complexity_score": chunk.complexity_score,
            "tags": chunk.tags,
            "content": chunk.content,  # Full content for accurate token counting
            "content_preview": (
                chunk.content[:200] + "..."
                if len(chunk.content) > 200
                else chunk.content
            ),
            # Call graph data
            "calls": [call.to_dict() for call in chunk.calls] if chunk.calls else [],
            # Relationship edges
            "relationships": (
                [rel.to_dict() for rel in chunk.relationships]
                if chunk.relationships
                else []
            ),
            "language": getattr(chunk, "language", "python"),
        }

        return EmbeddingResult(
            embedding=embedding, chunk_id=chunk_id, metadata=metadata
        )

    def embed_chunks(
        self, chunks: list[CodeChunk], batch_size: int | None = None
    ) -> list[EmbeddingResult]:
        """Generate embeddings for multiple chunks with dynamic batching.

        Uses GPU-aware batch sizing when CUDA is available, falling back to
        a registry estimate or runtime tracking if measurement fails.

        Args:
            chunks: Code chunks to embed.
            batch_size: Optional override for batch size. When ``None``,
                resolves batch size from config (dynamic GPU sizing when
                enabled, otherwise ``config.embedding.batch_size``).

        Returns:
            List of ``EmbeddingResult`` (one per input chunk, in order).
            Each result's ``embedding`` field is an ``np.ndarray`` of shape
            ``(embedding_dim,)`` with dtype ``float32``.
        """
        results = []

        # Get model-specific configuration for prefixing
        model_config = self._get_model_config()
        passage_prefix = model_config.get("passage_prefix", "")

        # Ensure model is loaded BEFORE batch calculation (to get accurate VRAM)
        # (model loads lazily on first encode() call - causes log interference)
        if not hasattr(self, "_model_warmed_up") or not self._model_warmed_up:
            self.model.encode(["warmup"], show_progress_bar=False)
            self._model_warmed_up = True

        # Log VRAM usage after model load
        self._log_vram_usage("MODEL_LOADED")

        # Re-apply VRAM cap with fresh memory readings — other processes may have
        # allocated VRAM since CodeEmbedder.__init__, which would otherwise let us
        # overcommit and trigger Windows WDDM shared-memory spillover.
        try:
            _embed_cfg = _get_config_via_service_locator()
            if _embed_cfg and _embed_cfg.performance:
                set_vram_limit(_embed_cfg.performance.vram_limit_fraction)
        except (RuntimeError, AttributeError) as _cap_err:
            self._logger.debug(
                "Ignoring %s re-applying VRAM cap", type(_cap_err).__name__
            )

        # Load batch size from config if not explicitly provided
        if batch_size is None:
            # Use ServiceLocator helper instead of inline import
            config = _get_config_via_service_locator()

            # Try dynamic GPU-based batch size first
            if (
                config.performance.enable_dynamic_batch_size
                and config.performance.prefer_gpu
                and torch
                and torch.cuda.is_available()
            ):
                # Get MEASURED model VRAM (after model load) for accurate batch sizing
                # This accounts for different GPUs/precision settings vs registry estimates
                model_vram_gb = self._get_model_vram_gb()

                # Fallback to registry estimate if measurement fails
                if model_vram_gb == 0.0:
                    model_vram_gb = parse_vram_gb_from_registry(self.model_name)
                    if model_vram_gb == 0.0:
                        # Last resort: use runtime tracking if available
                        model_vram_mb = self._model_vram_usage.get(self.model_name, 0.0)
                        model_vram_gb = model_vram_mb / 1024.0

                # --- Architecture-derived activation cost per batch item ---
                # Tier 1: use runtime-measured cost stored by ModelLoader at load time
                activation_gb_per_item = getattr(
                    self._model, "_activation_gb_per_item", 0.0
                )
                # Tier 2: derive from HuggingFace model config when measurement unavailable
                if activation_gb_per_item <= 0.0:
                    hf_cfg = self._extract_hf_config()
                    if hf_cfg is not None:
                        is_onnx = hasattr(self._model, "ort_model")
                        activation_gb_per_item = estimate_activation_gb_from_config(
                            hf_cfg, is_onnx=is_onnx
                        )
                        self._logger.info(
                            f"[DYNAMIC_BATCH] Activation cost estimated from model config: "
                            f"{activation_gb_per_item:.3f} GB/item"
                        )

                # Tier 3: ONNX safety floor.  Runtime warmup at batch=4 linearly
                # extrapolates per-item cost, but ORT BFCArena single-op peaks
                # (e.g. attention MatMul, residual Add) do not scale linearly
                # with batch and can blow past the per-item × batch budget.
                # Apply an empirically-validated floor for known ONNX models.
                if hasattr(self._model, "ort_model"):
                    onnx_floor = _get_onnx_cost_floor(self.model_name)
                    if onnx_floor > activation_gb_per_item:
                        self._logger.info(
                            f"[DYNAMIC_BATCH] Applying ONNX activation cost floor "
                            f"for {self.model_name!r}: "
                            f"{activation_gb_per_item:.3f} → {onnx_floor:.3f} GB/item "
                            f"(prevents BFCArena OOM on first-try batch)"
                        )
                        activation_gb_per_item = onnx_floor

                # Derive memory_fraction from vram_limit_fraction to maintain consistent safety margin
                # Target ~81% of hard VRAM ceiling for batch sizing (0.8125 ratio)
                memory_fraction = config.performance.vram_limit_fraction * 0.8125
                memory_fraction = max(
                    0.05, min(memory_fraction, 0.95)
                )  # Clamp to safe range

                # ORT cap: gpu_mem_limit is static (set at from_pretrained time), so
                # computing it once here (not per-batch) is correct and sufficient.
                ort_cap_gb = 0.0
                if hasattr(self._model, "ort_model"):
                    try:
                        _cap_result = compute_effective_vram_cap(
                            config.performance.vram_limit_fraction
                        )
                        if _cap_result is not None:
                            ort_cap_gb = _cap_result[1] / 1024**3  # bytes → GB
                    except Exception as _ort_err:
                        self._logger.debug(
                            "Ignoring %s computing ORT cap", type(_ort_err).__name__
                        )

                batch_size = calculate_optimal_batch_size(
                    embedding_dim=config.embedding.dimension,
                    min_batch=config.performance.dynamic_batch_min,
                    max_batch=config.performance.dynamic_batch_max,
                    memory_fraction=memory_fraction,
                    model_vram_gb=model_vram_gb,
                    model_name=self.model_name,
                    activation_gb_per_item=activation_gb_per_item,
                    ort_cap_gb=ort_cap_gb,
                )
                self._logger.info(
                    f"Using dynamic GPU-optimized batch size {batch_size} for {len(chunks)} chunks"
                )
            else:
                batch_size = config.embedding.batch_size
                self._logger.info(
                    f"Using static batch size {batch_size} from config for {len(chunks)} chunks"
                )
        else:
            self._logger.info(
                f"Using explicit batch size {batch_size} for {len(chunks)} chunks"
            )

        # Process in batches for efficiency with progress bar
        console = Console(force_terminal=True)
        # current_batch_size tracks the live batch size — may be halved on OOM.
        current_batch_size = batch_size
        total_batches = (len(chunks) + current_batch_size - 1) // current_batch_size

        # Suppress INFO logs during progress bar to prevent line mixing
        original_log_level = self._logger.level
        self._logger.setLevel(logging.WARNING)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("({task.completed}/{task.total} batches)"),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task("Embedding...", total=total_batches)
            i = 0
            batch_num = 0
            while i < len(chunks):
                batch = chunks[i : i + current_batch_size]
                batch_num += 1

                # Log VRAM before batch
                self._log_vram_usage("BATCH_START", batch_num)

                # Check VRAM before each batch
                vram_pct, should_warn, should_abort = self._check_vram_status()

                if should_abort:
                    self._logger.error(
                        f"[VRAM] Aborting embedding - VRAM at {vram_pct:.1%} (threshold: 95%)"
                    )
                    raise VRAMExhaustedError(
                        f"VRAM exhausted ({vram_pct:.1%}). "
                        "Close other GPU applications and retry."
                    )

                if should_warn:
                    self._logger.warning(f"[VRAM] High VRAM usage: {vram_pct:.1%}")

                # Prepend passage prefix if it exists
                if passage_prefix:
                    batch_contents = [
                        passage_prefix + self.create_embedding_content(chunk)
                        for chunk in batch
                    ]
                else:
                    batch_contents = [
                        self.create_embedding_content(chunk) for chunk in batch
                    ]

                # Generate embeddings for batch with OOM recovery
                # Use convert_to_tensor for GPU to avoid CPU<->GPU transfers (10-20% faster)
                use_tensor = self._is_gpu_device()

                try:
                    batch_embeddings = self.model.encode(
                        batch_contents,
                        show_progress_bar=False,
                        convert_to_tensor=use_tensor,
                        device=self.device if use_tensor else None,
                    )
                except RuntimeError as e:
                    # OOM recovery: halve current_batch_size and retry the same chunk
                    # position with a smaller batch.  Applies to both PyTorch CUDA OOM
                    # (torch.cuda.OutOfMemoryError subclasses RuntimeError) and ORT BFCArena OOM
                    # ("BFCArena::AllocateRawInternal Available memory … smaller than requested").
                    _oom_type = (
                        getattr(torch.cuda, "OutOfMemoryError", None)
                        if torch is not None
                        else None
                    )
                    is_torch_oom = isinstance(_oom_type, type) and isinstance(
                        e, _oom_type
                    )
                    err_str = str(e).lower()
                    is_ort_oom = "bfcarena" in err_str or (
                        "available memory" in err_str
                        and "smaller than requested" in err_str
                    )
                    is_oom = is_torch_oom or is_ort_oom or "out of memory" in err_str
                    if is_oom and current_batch_size > 1:
                        new_size = max(1, current_batch_size // 2)
                        self._logger.warning(
                            f"[OOM_RECOVERY] OOM at batch_size={current_batch_size} "
                            f"({type(e).__name__}) — halving to {new_size}. "
                            f"All subsequent batches will use size {new_size}."
                        )
                        current_batch_size = new_size
                        # Recalculate progress-bar total for the remaining smaller batches
                        completed = int(progress.tasks[task].completed)
                        remaining_chunks = len(chunks) - i
                        remaining_batches = (
                            remaining_chunks + current_batch_size - 1
                        ) // current_batch_size
                        progress.update(task, total=completed + remaining_batches)
                        # Flush GPU caches before retry
                        if torch and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        gc.collect()
                        batch_num -= 1  # this attempt is retried, don't advance counter
                        continue  # retry the same i with the smaller batch size
                    else:
                        if is_oom:
                            self._logger.error(
                                f"[OOM_RECOVERY] Cannot reduce batch further "
                                f"(current_batch_size={current_batch_size}), re-raising OOM"
                            )
                        raise

                # Convert back to numpy for consistency with rest of codebase
                # Note: bf16 tensors must be converted to float32 first (numpy doesn't support bf16)
                if torch and torch.is_tensor(batch_embeddings):
                    batch_embeddings = batch_embeddings.cpu().float().numpy()

                # Note: Manual cache clearing removed (2026-01-04)
                # CUDA allocator's garbage_collection_threshold:0.8 handles cleanup automatically
                # Empirical testing showed no performance or stability difference vs manual clearing

                # Create results
                for _j, (chunk, embedding) in enumerate(
                    zip(batch, batch_embeddings, strict=False)
                ):
                    # Normalize path separators for cross-platform consistency
                    normalized_path = normalize_path(str(chunk.relative_path))
                    chunk_id = f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
                    # Build qualified name for methods/functions inside classes
                    qualified_name = (
                        f"{chunk.parent_name}.{chunk.name}"
                        if chunk.parent_name and chunk.name
                        else chunk.name
                    )
                    if qualified_name:
                        chunk_id += f":{qualified_name}"

                    metadata = {
                        "file_path": chunk.file_path,
                        "relative_path": chunk.relative_path,
                        "folder_structure": chunk.folder_structure,
                        "chunk_type": chunk.chunk_type,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "name": chunk.name,
                        "parent_name": chunk.parent_name,
                        "parent_chunk_id": chunk.parent_chunk_id,
                        "docstring": chunk.docstring,
                        "decorators": chunk.decorators,
                        "imports": chunk.imports,
                        "complexity_score": chunk.complexity_score,
                        "tags": chunk.tags,
                        "content": chunk.content,  # Full content for accurate token counting
                        "content_preview": (
                            chunk.content[:200] + "..."
                            if len(chunk.content) > 200
                            else chunk.content
                        ),
                        # Call graph data (Python)
                        "calls": (
                            [call.to_dict() for call in chunk.calls]
                            if chunk.calls
                            else []
                        ),
                        # Relationship edges (all relationship types)
                        "relationships": (
                            [rel.to_dict() for rel in chunk.relationships]
                            if chunk.relationships
                            else []
                        ),
                        "language": getattr(chunk, "language", "python"),
                    }

                    results.append(
                        EmbeddingResult(
                            embedding=embedding, chunk_id=chunk_id, metadata=metadata
                        )
                    )

                # Log VRAM after batch
                self._log_vram_usage("BATCH_END", batch_num)

                # Advance to next chunk position and update progress bar
                i += current_batch_size
                progress.update(task, advance=1)

        # Restore original log level
        self._logger.setLevel(original_log_level)

        self._logger.info("Embedding generation completed")
        return results

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics."""
        return self._query_cache.get_stats()

    def clear_query_cache(self) -> None:
        """Clear the query embedding cache."""
        self._query_cache.clear()

    @timed("embed_query")
    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a search query with LRU caching.

        Caches query embeddings to improve performance for repeated queries.
        Cache is keyed by query text + model name + prefixes/instructions.
        Supports both query_prefix (simple prefix) and task_instruction
        (instruction-based models like CodeRankEmbed).

        Args:
            query: Natural-language search query to embed.

        Returns:
            np.ndarray of shape ``(embedding_dim,)`` with dtype ``float32``,
            where ``embedding_dim`` is model-specific (e.g., 1024 for BGE-M3,
            1024 for Qwen3-0.6B). Values are L2-normalized when the underlying
            model is configured for normalized output.
        """
        # Get model-specific configuration
        model_config = self._get_model_config()

        # Try to get from cache
        cached_embedding = self._query_cache.get(
            query=query,
            model_name=self.model_name,
            task_instruction=model_config.get("task_instruction", ""),
            query_prefix=model_config.get("query_prefix", ""),
        )

        if cached_embedding is not None:
            return cached_embedding

        # Cache miss - generate embedding
        # Priority: instruction_mode > task_instruction > query_prefix
        instruction_mode = model_config.get("instruction_mode")

        # Prepare encoding kwargs
        encode_kwargs = {
            "show_progress_bar": False,
        }

        # Use convert_to_tensor for GPU to avoid CPU<->GPU transfers
        use_tensor = self._is_gpu_device()
        if use_tensor:
            encode_kwargs["convert_to_tensor"] = True
            encode_kwargs["device"] = self.device

        # Determine query formatting based on instruction mode
        if instruction_mode == "prompt_name":
            # Option A: Use sentence-transformers built-in prompt
            prompt_name_value = model_config.get("prompt_name", "query")
            encode_kwargs["prompt_name"] = prompt_name_value
            query_to_embed = query
            self._logger.debug(
                f"Using prompt_name='{prompt_name_value}' for query encoding"
            )
        elif instruction_mode == "custom":
            # Option B: Custom Qwen3-style instruction format
            query_instruction = model_config.get("query_instruction", "")
            query_to_embed = query_instruction + query
            self._logger.debug("Using custom instruction for query encoding")
        else:
            # Fallback to legacy behavior for other models
            task_instruction = model_config.get("task_instruction")
            query_prefix = model_config.get("query_prefix", "")

            if task_instruction:
                # Task instructions need ": " separator (e.g., CodeRankEmbed)
                separator = ": " if not task_instruction.endswith(": ") else ""
                query_to_embed = task_instruction + separator + query
            elif query_prefix:
                # Simple prefix (e.g., "Retrieval-document: ")
                query_to_embed = query_prefix + query
            else:
                query_to_embed = query

        # Generate embedding
        embedding = self.model.encode(
            [query_to_embed],
            **encode_kwargs,
        )[0]

        # Convert back to numpy if tensor
        # Note: bf16 tensors must be converted to float32 first (numpy doesn't support bf16)
        if torch and torch.is_tensor(embedding):
            embedding = embedding.cpu().float().numpy()

        # Add to cache
        self._query_cache.put(
            query=query,
            model_name=self.model_name,
            embedding=embedding,
            task_instruction=model_config.get("task_instruction", ""),
            query_prefix=model_config.get("query_prefix", ""),
        )

        return embedding

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if self._model is None:
            return {"status": "not_loaded"}

        return {
            "model_name": self.model_name,
            "embedding_dimension": self._model.get_sentence_embedding_dimension(),
            "max_seq_length": getattr(self._model, "max_seq_length", "unknown"),
            "device": str(self._model.device),
            "status": "loaded",
        }

    def get_vram_usage(self) -> dict[str, float]:
        """Return per-model VRAM usage in MB.

        Returns:
            Dictionary mapping model names to VRAM usage in MB.
        """
        return dict(self._model_vram_usage)

    def _log_vram_usage(self, phase: str, batch_idx: int = 0) -> None:
        """Log current VRAM usage for debugging memory issues.

        Args:
            phase: Description of current phase (e.g., "MODEL_LOADED", "BATCH_START")
            batch_idx: Optional batch index for batch-specific logging
        """
        if torch is None or not torch.cuda.is_available():
            return

        try:
            allocated = torch.cuda.memory_allocated() / (1024**3)
            reserved = torch.cuda.memory_reserved() / (1024**3)
            total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            usage_percent = (allocated / total) * 100

            # Include batch index in message if provided
            batch_info = f"[Batch {batch_idx}] " if batch_idx > 0 else ""

            self._logger.info(
                f"[VRAM] {batch_info}{phase}: "
                f"Allocated={allocated:.2f}GB, "
                f"Reserved={reserved:.2f}GB, "
                f"Total={total:.1f}GB "
                f"({usage_percent:.1f}% used)"
            )

            # Warn if VRAM usage is high (>90%)
            if usage_percent > 90:
                self._logger.warning(
                    f"[VRAM] High memory usage detected ({usage_percent:.1f}%). "
                    f"Consider reducing batch_size to avoid OOM."
                )
        except RuntimeError as e:
            self._logger.debug(f"Failed to log VRAM usage: {e}")

    def _get_model_vram_gb(self) -> float:
        """Get actual model VRAM usage in GB (after model load).

        Returns GPU memory allocated by the model in gigabytes.
        Used for dynamic batch size calculation to avoid using registry estimates.

        For ONNX models: PyTorch's allocator reports 0 because ORT's
        CUDAExecutionProvider allocates CUDA memory outside PyTorch. ModelLoader
        stores the pynvml before/after delta on the wrapper as `_vram_gb` instead.

        Returns:
            Model VRAM usage in GB, or 0.0 if GPU not available
        """
        # ONNX path: use measured ORT allocation delta (set by ModelLoader._load_onnx)
        if (
            self._model is not None
            and hasattr(self._model, "_vram_gb")
            and self._model._vram_gb > 0
        ):
            return self._model._vram_gb

        # PyTorch path
        if torch is None or not torch.cuda.is_available():
            return 0.0

        try:
            allocated_bytes = torch.cuda.memory_allocated()
            return allocated_bytes / (1024**3)
        except RuntimeError as e:
            self._logger.debug(f"Failed to get model VRAM: {e}")
            return 0.0

    def _extract_hf_config(self) -> Any | None:
        """Extract HuggingFace PretrainedConfig from the loaded model.

        Works for both SentenceTransformer (PyTorch) and ONNXEmbeddingModel backends.
        Returns the first config object found that has a ``hidden_size`` attribute,
        or None if the model is not loaded or the config cannot be extracted.
        """
        if self._model is None:
            return None
        # ONNX backend: config lives on ort_model
        ort_model = getattr(self._model, "ort_model", None)
        if ort_model is not None:
            cfg = getattr(ort_model, "config", None)
            if cfg is not None and hasattr(cfg, "hidden_size"):
                return cfg
        # SentenceTransformer: first module is typically a Transformer
        # SentenceTransformer[0].auto_model.config is the HF config
        try:
            first_module = self._model[0]
            auto_model = getattr(first_module, "auto_model", None)
            if auto_model is not None:
                cfg = getattr(auto_model, "config", None)
                if cfg is not None and hasattr(cfg, "hidden_size"):
                    return cfg
        except (IndexError, TypeError, AttributeError):
            pass
        return None

    def cleanup(self) -> None:
        """Clean up model from memory to free GPU/CPU resources."""
        import sys

        if sys.meta_path is None:
            # Python interpreter is shutting down; imports are unavailable.
            # Skip cleanup to avoid spurious errors from gc/torch teardown.
            return
        if self._model is not None:
            try:
                import gc

                # Step 1: Free GPU memory.
                # ONNX path: call cleanup() to explicitly destroy the ORT CUDA session,
                # which is the only way to release CUDA memory allocated by ORT's
                # CUDAExecutionProvider (not tracked by torch.cuda.memory_allocated).
                # PyTorch path: move to CPU first to free VRAM, then delete.
                if hasattr(self._model, "cleanup"):
                    self._logger.info("Releasing ONNX Runtime CUDA session...")
                    self._model.cleanup()
                    self._logger.info("ONNX VRAM freed")
                elif (
                    torch is not None
                    and torch.cuda.is_available()
                    and hasattr(self._model, "cpu")
                ):
                    self._logger.info("Moving model from GPU to CPU...")
                    self._model = self._model.cpu()
                    torch.cuda.synchronize()  # Wait for GPU operations
                    torch.cuda.empty_cache()
                    self._logger.info("VRAM freed")

                # Step 2: Delete model reference (allows RAM to be freed)
                del self._model
                self._model = None
                self._logger.info("Model reference deleted")

                # Step 3: Clear query cache (numpy arrays)
                if hasattr(self, "_query_cache"):
                    self._query_cache.clear()
                    self._logger.info("Query cache cleared")

                # Step 4: Clear model loader to prevent lazy reload (CRITICAL for VRAM cleanup)
                # Preserving model loader causes immediate reload when .model is accessed
                # This defeats cleanup purpose - forces creation of fresh embedder instead
                if hasattr(self, "_model_loader"):
                    self._model_loader = None
                    self._logger.info("Model loader cleared - lazy reload disabled")

                # Step 5: Force garbage collection (frees RAM)
                gc.collect()
                self._logger.info("RAM freed via garbage collection")

                # Step 6: Final CUDA cache clear
                if torch is not None and torch.cuda.is_available():
                    torch.cuda.empty_cache()

                self._logger.info("Model cleanup complete - VRAM and RAM freed")
            except Exception as e:
                self._logger.warning(f"Error during model cleanup: {e}")

    def __enter__(self) -> "CodeEmbedder":
        """Context manager entry - ensure model is loaded."""
        # Trigger model loading
        _ = self.model
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup resources."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        # Intentional: cleanup during interpreter shutdown may fail
        # Logging is unreliable in __del__, so suppress is acceptable
        with contextlib.suppress(Exception):
            self.cleanup()

    # ===== Cache Management Methods (delegated to ModelCacheManager) =====

    def _get_model_cache_path(self) -> Path | None:
        """Delegate to ModelCacheManager.get_model_cache_path()."""
        return self._cache_manager.get_model_cache_path()

    def _get_default_hf_cache_path(self) -> Path | None:
        """Delegate to ModelCacheManager.get_default_hf_cache_path()."""
        return self._cache_manager.get_default_hf_cache_path()

    def _check_config_at_location(self, cache_path: Path) -> bool:
        """Delegate to ModelCacheManager.check_config_at_location()."""
        return self._cache_manager.check_config_at_location(cache_path)

    def _check_weights_at_location(self, cache_path: Path) -> bool:
        """Delegate to ModelCacheManager.check_weights_at_location()."""
        return self._cache_manager.check_weights_at_location(cache_path)

    def _ensure_split_cache_symlink(self) -> bool:
        """Delegate to ModelCacheManager.ensure_split_cache_symlink()."""
        return self._cache_manager.ensure_split_cache_symlink()

    def _check_cache_at_location(self, cache_path: Path) -> tuple[bool, str]:
        """Delegate to ModelCacheManager.check_cache_at_location()."""
        return self._cache_manager.check_cache_at_location(cache_path)

    def _validate_model_cache(self) -> tuple[bool, str]:
        """Delegate to ModelCacheManager.validate_cache()."""
        return self._cache_manager.validate_cache()

    def _check_incomplete_downloads(self) -> tuple[bool, str]:
        """Delegate to ModelCacheManager.check_incomplete_downloads()."""
        return self._cache_manager.check_incomplete_downloads()

    def _cleanup_incomplete_downloads(self) -> tuple[int, list[str]]:
        """Delegate to ModelCacheManager.cleanup_incomplete_downloads()."""
        return self._cache_manager.cleanup_incomplete_downloads()

    def _is_model_cached(self) -> bool:
        """Delegate to ModelCacheManager.is_cached()."""
        return self._cache_manager.is_cached()

    def _find_local_model_dir(self) -> Path | None:
        """Delegate to ModelCacheManager.find_local_model_dir()."""
        return self._cache_manager.find_local_model_dir()

    def _resolve_device(self, requested: str | None) -> str:
        """Delegate to ModelLoader.resolve_device()."""
        return self._model_loader.resolve_device(requested)
