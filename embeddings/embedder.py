"""Code embedder for generating code embeddings.

Supports configurable embedding models including:
- EmbeddingGemma (google/embeddinggemma-300m)
- BGE-M3 (BAAI/bge-m3)

Single-GPU assumption: all torch.cuda.* calls target device index 0.
"""

import contextlib
import gc
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from chunking.python_ast_chunker import CodeChunk
from embeddings.chunk_cache import ChunkEmbeddingCache
from embeddings.chunk_metadata import ChunkMetadata
from embeddings.model_cache import ModelCacheManager
from embeddings.model_loader import ModelLoader
from embeddings.query_cache import QueryEmbeddingCache
from mcp_server.utils.config_helpers import (
    get_config_via_service_locator as _get_config_via_service_locator,
)
from search.config import (
    get_indexing_ram_fallback_override as _get_ram_fallback_override,
)
from search.exceptions import VRAMExhaustedError
from search.filters import normalize_path
from utils.console import get_progress_console
from utils.timing import timed


# ===== BATCH SIZE MEMORY ESTIMATION =====
# Empirically derived from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18% overhead
FRAGMENTATION_OVERHEAD = 0.82  # 1.0 - 0.18 = 82% usable VRAM, 18% fragmentation

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

# Known PyTorch CUDA OOM message text — compat fallback for legacy torch
# builds where torch.cuda.OutOfMemoryError is not a distinct exception class.
# str(exception).lower() yields the message text (not the class name), so only
# message-shape strings belong here. Kept as a tuple for future extensibility.
_PYTORCH_OOM_STRINGS = ("cuda out of memory",)


def estimate_activation_gb_from_config(
    config: Any,
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

    Validated against registered models with SAFETY=15, T_eff=1024
    (F2LLM-v2-0.6B not yet profiled):
        EmbeddingGemma-300M:  0.13 GB  (observed ~0.04 GB)   safe
        Qwen3-Embed-0.6B:     0.26 GB  (observed  0.27 GB)   safe

    Args:
        config: HuggingFace PretrainedConfig (has .hidden_size, etc.)

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
    # fp32 doubles activation memory vs fp16/bf16. float64 is not used by
    # embedding models in practice and is treated as fp16 here (2 bytes).
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

    # Effective sequence length: code chunks regularly reach 1500–3000 tokens.
    # Set to 2048 as a conservative cap (#46) — using model.max_ctx (up to 32K)
    # would massively over-estimate.
    t_eff = 2048

    # Safety multiplier: accounts for PyTorch allocator overhead, GEMM workspace
    # buffers, and block retention. Calibrated to be ≥ empirically observed costs.
    safety = 15

    gb_per_item = peak_per_token * t_eff * safety / (1024**3)
    return max(gb_per_item, 0.04)  # 40 MB floor


# Configure PyTorch CUDA allocator BEFORE any torch imports
# This must be done early to prevent fragmentation and enable better memory management
def _configure_cuda_allocator() -> None:
    """Configure PyTorch CUDA allocator for reduced fragmentation.

    Sets PYTORCH_CUDA_ALLOC_CONF before any CUDA allocation.  The env var is
    read when the caching allocator initialises on the *first* CUDA allocation,
    not at ``import torch`` (#30).  The call is made at module import time so
    it normally wins the race, but server entry-points should ideally set it
    even earlier (before importing this module) for guaranteed effect.

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
    any side effects.  Used by the PyTorch-cap path (``set_vram_limit``).

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
        - *cap_bytes*          — cap in bytes (diagnostic)
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
    the OS may spill to shared RAM.

    **FAISS**: ``set_per_process_memory_fraction`` only governs the PyTorch
    CUDA allocator.  FAISS GPU indexes use their own allocator and are not
    constrained here.

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
    # The module-level override (_indexing_ram_fallback_override in search.config) takes
    # priority over the persisted config value: it survives _config_manager = None resets
    # that happen on every model switch during multi-model indexing and would otherwise
    # silently restore allow_ram_fallback=True from disk between per-model embed passes.
    try:
        override = _get_ram_fallback_override()
        if override is not None:
            allow_fallback = override
        else:
            config = _get_config_via_service_locator()
            allow_fallback = bool(config and config.performance.allow_ram_fallback)
        if allow_fallback:
            logging.getLogger(__name__).info(
                "[VRAM_LIMIT] RAM fallback allowed - skipping PyTorch VRAM cap"
            )
            return True  # Don't set limit, allow PyTorch spillover
    except Exception as e:  # noqa: BLE001 - parse-recovery: config unavailable, use defaults
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
        logger.info(
            f"[DYNAMIC_BATCH] GPU: {free_gb:.1f}GB free / {total_gb:.1f}GB total, "
            f"model: {model_vram_gb:.1f}GB ({model_name or 'unknown'}), "
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
    metadata: ChunkMetadata


class CodeEmbedder:
    """Embedder for generating code embeddings.

    Supports configurable embedding models with automatic configuration detection.
    Default model is BAAI/bge-m3.
    """

    def __new__(cls, *args, **kwargs) -> "CodeEmbedder":
        """Pre-create the lifecycle lock before __init__ runs.

        This is a lock-init hook, NOT a singleton pattern — every call
        returns a fresh instance. It exists so __new__-only construction
        paths (test mocks, unpickling) that skip __init__ still end up with
        a functional ``_lifecycle_lock``, since the many
        ``with self._lifecycle_lock:`` sites throughout this class assume
        it is always present.
        """
        instance = super().__new__(cls)
        # pyrefly: ignore [missing-attribute]
        instance._lifecycle_lock = threading.RLock()
        return instance

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
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
            query_cache_size = config.embedding.query_cache_size if config else 128
        except (RuntimeError, AttributeError):
            fraction = 0.90
            query_cache_size = 128
        set_vram_limit(fraction)

        # Query embedding cache (LRU)
        self._query_cache = QueryEmbeddingCache(max_size=query_cache_size)

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
        self._model_vram_usage: dict[str, float] = {}  # model_name -> VRAM MB

        # File-content cache for _get_class_signature (#50).
        # Avoids O(chunks × filesize) repeated re-reads when many methods share a file.
        # Maps file_path → (mtime, full_file_content); invalidated on mtime change.
        self._class_file_cache: dict[str, tuple[float, str]] = {}
        # Derived-result caches for _extract_import_context (I2) and
        # _get_class_signature (I2b): the splitlines()/regex work over
        # _class_file_cache's cached content is itself identical per file
        # (import context) or per (file, parent class) (class signature) across
        # every chunk that shares it — memoizing collapses O(chunks) redundant
        # CPU to O(files) / O(classes). Invalidated on mtime change, same as
        # _class_file_cache.
        self._import_ctx_cache: dict[str, tuple[float | None, int, str]] = {}
        self._class_sig_cache: dict[tuple[str, str], tuple[float | None, int, str]] = {}
        # Removed: logging.basicConfig(level=INFO) — library code must not
        # mutate the root logger; it fights the MCP server's dual-handler
        # setup and overrides any earlier basicConfig call (#37).

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
        if self._model_loader is None:
            return
        self._model_loader.log_gpu_memory(stage)

    # pyrefly: ignore [missing-attribute]
    def _get_torch_dtype(self) -> "torch.dtype":
        """Delegate to ModelLoader.get_torch_dtype()."""
        if self._model_loader is None:
            raise RuntimeError(
                "Embedder has been cleaned up; obtain a fresh instance "
                "via model_pool_manager.get_embedder()."
            )
        return self._model_loader.get_torch_dtype()

    def get_embedding_provenance(self) -> str:
        """Delegate to ModelLoader.describe_numerics()."""
        if self._model_loader is None:
            raise RuntimeError(
                "Embedder has been cleaned up; obtain a fresh instance "
                "via model_pool_manager.get_embedder()."
            )
        return self._model_loader.describe_numerics()

    def _is_gpu_device(self) -> bool:
        """Check if current device is GPU (cuda/mps).

        Returns:
            True if device is GPU, False if CPU.
        """
        if not self.device:
            return False

        device_str = str(self.device).lower()
        return "cuda" in device_str or "mps" in device_str

    def _format_query_text(self, query: str, model_config: dict) -> str:
        """Apply instruction/prefix formatting for a single query string."""
        instruction_mode = model_config.get("instruction_mode")
        if instruction_mode == "prompt_name":
            return query
        if instruction_mode == "custom":
            return model_config.get("query_instruction", "") + query
        task_instruction = model_config.get("task_instruction", "")
        query_prefix = model_config.get("query_prefix", "")
        if task_instruction:
            sep = ": " if not task_instruction.endswith(": ") else ""
            return task_instruction + sep + query
        if query_prefix:
            return query_prefix + query
        return query

    def _tensor_to_numpy(self, emb: Any) -> np.ndarray:
        """Convert a tensor or array to a float32 numpy array."""
        # pyrefly: ignore [missing-attribute]
        if torch.is_tensor(emb):
            return emb.cpu().float().numpy()
        return emb

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
            total_memory = torch.cuda.get_device_properties(0).total_memory

            # Use allocated (not mem_get_info reserved) to avoid false 87%
            # warnings from allocator-reserved but unused blocks.
            allocated = torch.cuda.memory_allocated(0)
            usage_pct = allocated / total_memory if total_memory > 0 else 0.0

            should_warn = usage_pct > vram_warning_threshold
            should_abort = usage_pct > vram_abort_threshold

            return usage_pct, should_warn, should_abort
        except RuntimeError as e:
            self._logger.warning(f"Failed to check VRAM status: {e}")
            return 0.0, False, False

    @property
    def model(self) -> SentenceTransformer | None:
        """Lazy loading of the model. Thread-safe via double-checked lock."""
        if self._model is not None:
            return self._model
        # pyrefly: ignore [missing-attribute]
        with self._lifecycle_lock:
            if self._model is None:
                if self._model_loader is None:
                    raise RuntimeError(
                        "Embedder has been cleaned up; obtain a fresh instance "
                        "via model_pool_manager.get_embedder()."
                    )
                self._load_model()
            return self._model

    def _load_model(self) -> None:
        """Delegate to ModelLoader.load()."""
        self._model, self.device = self._model_loader.load()
        # Sync VRAM usage tracking from ModelLoader
        self._model_vram_usage.update(self._model_loader.model_vram_usage)

    def _read_source_cached(self, file_path: str) -> tuple[str, float | None]:
        """Read a source file's full content, cached by mtime (#50 / I1).

        Shared by `_extract_import_context` and `_get_class_signature` so a
        file with N chunks is opened once per index run instead of N times —
        each used to open the same file separately (O(chunks x filesize)).
        Cache key is file_path; invalidated when mtime changes.

        Returns ``(content, mtime)``. Callers that memoize their own derived
        result per file (I2 / I2b) validate against this same mtime, so no
        second ``stat()`` call is needed.

        Raises whatever `open()`/`.read()` raise (OSError, UnicodeDecodeError);
        callers handle those themselves so each keeps its own log message.
        """
        # getattr: tests that use __new__ (no __init__) won't have _class_file_cache.
        _file_cache: dict[str, tuple[float, str]] | None = getattr(
            self, "_class_file_cache", None
        )
        cached_mtime, content = (
            _file_cache.get(file_path, (None, None))
            if _file_cache is not None
            else (None, None)
        )
        try:
            current_mtime = Path(file_path).stat().st_mtime
        except OSError:
            current_mtime = None

        if content is None or cached_mtime != current_mtime:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            if _file_cache is not None and current_mtime is not None:
                _file_cache[file_path] = (current_mtime, content)

        return content, current_mtime

    def _extract_import_context(self, file_path: str, max_imports: int = 10) -> str:
        """Extract first N import statements from file header.

        Args:
            file_path: Absolute path to the source file
            max_imports: Maximum number of import lines to extract

        Returns:
            String containing import statements, or empty string if none found
        """
        try:
            content, mtime = self._read_source_cached(file_path)
        except (OSError, UnicodeDecodeError) as e:
            self._logger.debug(
                f"Failed to extract import context from {file_path}: {e}"
            )
            return ""

        # I2: the scan below is identical for every chunk in the same file at
        # the same max_imports setting — memoize it so a file with N chunks
        # scans once instead of N times (getattr guards __new__ test instances,
        # mirroring _read_source_cached's own guard).
        _ctx_cache: dict[str, tuple[float | None, int, str]] | None = getattr(
            self, "_import_ctx_cache", None
        )
        if _ctx_cache is not None:
            cached = _ctx_cache.get(file_path)
            if cached is not None and cached[0] == mtime and cached[1] == max_imports:
                return cached[2]

        lines = []
        for line in content.splitlines():
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
        result = "\n".join(lines)
        if _ctx_cache is not None:
            _ctx_cache[file_path] = (mtime, max_imports, result)
        return result

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
            import re

            # Shared with _extract_import_context (#50 / I1): avoids re-reading
            # the same file for every method chunk in it (O(chunks × filesize) → O(files)).
            content, mtime = self._read_source_cached(chunk.file_path)

            # I2b: the regex search + signature extraction below is identical
            # for every sibling method of the same parent class — memoize per
            # (file, parent_name) so N methods do it once instead of N times.
            _sig_cache: dict[tuple[str, str], tuple[float | None, int, str]] | None = (
                getattr(self, "_class_sig_cache", None)
            )
            cache_key = (chunk.file_path, chunk.parent_name)
            if _sig_cache is not None:
                cached = _sig_cache.get(cache_key)
                if cached is not None and cached[0] == mtime and cached[1] == max_lines:
                    return cached[2]

            # Find class definition containing this method
            # Pattern: "class ClassName" or "class ClassName(BaseClass)"
            class_pattern = rf"^class\s+{re.escape(chunk.parent_name)}\s*[\(:]"

            match = re.search(class_pattern, content, re.MULTILINE)
            if not match:
                if _sig_cache is not None:
                    _sig_cache[cache_key] = (mtime, max_lines, "")
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

            if _sig_cache is not None:
                _sig_cache[cache_key] = (mtime, max_lines, signature)
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
        except Exception as e:  # noqa: BLE001 - parse-recovery: context config unavailable, use defaults
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

    @staticmethod
    def _build_chunk_id(chunk: CodeChunk) -> str:
        """Build the unique chunk identifier from a CodeChunk."""
        normalized_path = normalize_path(str(chunk.relative_path))
        chunk_id = (
            f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
        )
        qualified_name = (
            f"{chunk.parent_name}.{chunk.name}"
            if chunk.parent_name and chunk.name
            else chunk.name
        )
        if qualified_name:
            chunk_id += f":{qualified_name}"
        return chunk_id

    @staticmethod
    def _build_chunk_metadata(chunk: CodeChunk) -> ChunkMetadata:
        """Build the metadata dict for an EmbeddingResult from a CodeChunk."""
        metadata: ChunkMetadata = {
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
            "decorators": chunk.decorators or [],
            "imports": chunk.imports or [],
            "complexity_score": chunk.complexity_score,
            "tags": chunk.tags or [],
            # In-memory carrier for downstream BM25 document indexing (read in
            # hybrid_searcher / indexer); stripped before persist so the
            # MetadataStore keeps only content_preview (#55). NOT used for token
            # counting — that runs at chunk build time on the live CodeChunk.
            "content": chunk.content,
            "content_preview": (
                chunk.content[:200] + "..."
                if len(chunk.content) > 200
                else chunk.content
            ),
            "calls": ([call.to_dict() for call in chunk.calls] if chunk.calls else []),
            "relationships": (
                [rel.to_dict() for rel in chunk.relationships]
                if chunk.relationships
                else []
            ),
            "language": getattr(chunk, "language", "python"),
        }
        # Only merged chunks carry member provenance; keep ordinary records lean.
        if chunk.merged_from:
            metadata["merged_from"] = chunk.merged_from
        return metadata

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
        # Acquire lifecycle lock just like embed_chunks / embed_query (#35) so
        # a concurrent cleanup() cannot null self.model mid-encode.
        # pyrefly: ignore [missing-attribute]
        with self._lifecycle_lock:
            # pyrefly: ignore [missing-attribute]
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

        chunk_id = self._build_chunk_id(chunk)
        metadata = self._build_chunk_metadata(chunk)

        return EmbeddingResult(
            embedding=embedding, chunk_id=chunk_id, metadata=metadata
        )

    def embed_chunks(
        self,
        chunks: list[CodeChunk],
        batch_size: int | None = None,
        *,
        cache: ChunkEmbeddingCache | None = None,
        cache_full_pass: bool = True,
    ) -> list[EmbeddingResult]:
        """Generate embeddings for multiple chunks with dynamic batching.

        Uses GPU-aware batch sizing when CUDA is available, falling back to
        a registry estimate or runtime tracking if measurement fails.

        Args:
            chunks: Code chunks to embed.
            batch_size: Optional override for batch size. When ``None``,
                resolves batch size from config (dynamic GPU sizing when
                enabled, otherwise ``config.embedding.batch_size``).
            cache: Optional persistent content-hash embedding cache (see
                ``embeddings.chunk_cache.ChunkEmbeddingCache``). When
                provided, chunks whose assembled embedding content is
                unchanged since the last run are served from disk instead
                of the GPU. On a 100% cache hit the model is never loaded.
                ``None`` (the default) reproduces today's behavior exactly.
            cache_full_pass: Forwarded to ``ChunkEmbeddingCache.save`` as
                ``full_pass``. ``True`` (the default — matches a full index)
                lets the save prune down to exactly this run's ``live_keys``.
                Callers embedding only a subset of the project's chunks (an
                incremental update, a module-summary refresh) must pass
                ``False``, or the tiny ``live_keys`` from that partial run
                would evict the vast majority of a cache built by prior full
                passes. Ignored when ``cache`` is ``None``.

        Returns:
            List of ``EmbeddingResult`` (one per input chunk, in order).
            Each result's ``embedding`` field is an ``np.ndarray`` of shape
            ``(embedding_dim,)`` with dtype ``float32``.
        """
        # Get model-specific configuration for prefixing
        model_config = self._get_model_config()
        passage_prefix = model_config.get("passage_prefix", "")

        # Precompute embedding content once per chunk (was recomputed inside the
        # batch loop every call). Hoisted above the model-load block (moved down
        # below, #Round-3) so a cache hit can be checked — and, on a 100% hit,
        # returned early — without ever loading the model. create_embedding_content
        # needs no model; passage_prefix is already resolved above.
        if passage_prefix:
            all_contents = [
                passage_prefix + self.create_embedding_content(chunk)
                for chunk in chunks
            ]
        else:
            all_contents = [self.create_embedding_content(chunk) for chunk in chunks]

        # --- Content-hash embedding cache (opt-in via cache=) ---------------
        # Partition chunks into cache hits and misses using the exact strings
        # that would be handed to model.encode() — all_contents already folds
        # in import context / class signature / structural header, so hashing
        # this string (never raw chunk.content) is correct even when a
        # neighbouring part of the file changed a chunk's assembled content.
        ordered_results: list[EmbeddingResult | None] = [None] * len(chunks)
        cache_keys: list[str | None] = [None] * len(chunks)
        pending_indices: list[int] = list(range(len(chunks)))

        # A cache failure must never fail the index. `cache_enabled` (not
        # `cache is not None`) gates every later cache use, including the
        # write-back — a read failure here disables the cache for the rest
        # of this call, falling back to embedding every chunk normally.
        cache_enabled = cache is not None
        if cache_enabled:
            try:
                pending_indices = []
                for idx, content in enumerate(all_contents):
                    key = cache.key_for(content)
                    cache_keys[idx] = key
                    cached_vector = cache.get(key)
                    if cached_vector is None:
                        pending_indices.append(idx)
                        continue
                    chunk = chunks[idx]
                    ordered_results[idx] = EmbeddingResult(
                        embedding=cached_vector,
                        chunk_id=self._build_chunk_id(chunk),
                        metadata=self._build_chunk_metadata(chunk),
                    )
            except Exception as exc:  # noqa: BLE001 - fail-soft: a cache read failure must never fail the index
                self._logger.warning(
                    "embed_chunks: chunk embedding cache read failed (%s) — "
                    "embedding all %d chunks without it",
                    exc,
                    len(chunks),
                )
                cache_enabled = False
                ordered_results = [None] * len(chunks)
                cache_keys = [None] * len(chunks)
                pending_indices = list(range(len(chunks)))

            if cache_enabled and not pending_indices:
                self._log_chunk_cache_stats(cache, "100% hit, model load skipped")
                return cast(list[EmbeddingResult], ordered_results)

        pending_chunks = [chunks[idx] for idx in pending_indices]
        pending_contents = [all_contents[idx] for idx in pending_indices]

        results: list[EmbeddingResult] = []

        # Ensure model is loaded BEFORE batch calculation (to get accurate VRAM).
        # ModelLoader.load() already performs warmup + activation measurement on both
        # backends, so accessing the property is enough — an extra encode(["warmup"])
        # here was a redundant GPU forward pass (#57).
        if not hasattr(self, "_model_warmed_up") or not self._model_warmed_up:
            # pyrefly: ignore [missing-attribute]
            with self._lifecycle_lock:
                # pyrefly: ignore [missing-attribute]
                _ = (
                    self.model
                )  # property access triggers lazy load; warmup done in load()
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
                # Tier 1: runtime-measured cost stored by ModelLoader at load time —
                # a torch peak-allocated delta, i.e. a true marginal per-item cost.
                activation_gb_per_item = getattr(
                    self._model, "_activation_gb_per_item", 0.0
                )
                # Tier 2: derive from HuggingFace model config when measurement unavailable
                if activation_gb_per_item <= 0.0:
                    hf_cfg = self._extract_hf_config()
                    if hf_cfg is not None:
                        activation_gb_per_item = estimate_activation_gb_from_config(
                            hf_cfg
                        )
                        self._logger.info(
                            f"[DYNAMIC_BATCH] Activation cost estimated from model config: "
                            f"{activation_gb_per_item:.3f} GB/item"
                        )

                # Derive memory_fraction from vram_limit_fraction to maintain consistent safety margin
                # Target ~81% of hard VRAM ceiling for batch sizing (0.8125 ratio)
                memory_fraction = config.performance.vram_limit_fraction * 0.8125
                memory_fraction = max(
                    0.05, min(memory_fraction, 0.95)
                )  # Clamp to safe range

                batch_size = calculate_optimal_batch_size(
                    embedding_dim=config.embedding.dimension,
                    min_batch=config.performance.dynamic_batch_min,
                    max_batch=config.performance.dynamic_batch_max,
                    memory_fraction=memory_fraction,
                    model_vram_gb=model_vram_gb,
                    model_name=self.model_name,
                    activation_gb_per_item=activation_gb_per_item,
                )
                self._logger.info(
                    f"Using dynamic GPU-optimized batch size {batch_size} "
                    f"for {len(pending_chunks)} chunks"
                )
            else:
                batch_size = config.embedding.batch_size
                self._logger.info(
                    f"Using static batch size {batch_size} from config "
                    f"for {len(pending_chunks)} chunks"
                )
        else:
            self._logger.info(
                f"Using explicit batch size {batch_size} for {len(pending_chunks)} chunks"
            )

        # Process in batches for efficiency with progress bar
        console = get_progress_console()
        # current_batch_size tracks the live batch size — may be halved on OOM.
        current_batch_size = batch_size
        total_batches = (
            len(pending_chunks) + current_batch_size - 1
        ) // current_batch_size

        # Sort the miss subset by content length descending before slicing into
        # fixed-size batches. Fixed-size windows over arbitrary chunk order pad
        # every batch to the longest member of a random draw; chunk lengths are
        # heavily right-skewed (median ~845 chars, p90 ~3083, capped at 6000), so
        # an unsorted batch routinely pads short chunks out to a rare long one.
        # Sorting first means each batch's members are near-uniform length, so
        # padding tracks real content instead of the corpus's long tail (#B1).
        #
        # Descending order so the single largest batch (worst-case VRAM) runs
        # first — an OOM surfaces on batch 1, not after 100 successful batches.
        # Results are appended in this sorted order and un-permuted back to
        # pending order (then scattered into the caller's input order, alongside
        # any cache hits) just before returning.
        sort_order = sorted(
            range(len(pending_chunks)),
            key=lambda idx: len(pending_contents[idx]),
            reverse=True,
        )
        sorted_chunks = [pending_chunks[idx] for idx in sort_order]
        sorted_contents = [pending_contents[idx] for idx in sort_order]

        # Suppress INFO logs during progress bar to prevent line mixing.
        # Use try/finally to restore the level even if VRAMExhaustedError or
        # an OOM re-raise escapes the loop — without this the module logger
        # stays permanently at WARNING, hiding all subsequent diagnostics (#20).
        original_log_level = self._logger.level
        self._logger.setLevel(logging.WARNING)
        try:
            with Progress(
                # spinner_name="line" - the default "dots" spinner renders
                # Braille glyphs (U+2800+) that raise UnicodeEncodeError on a
                # cp1252 Windows console; get_progress_console() does not set
                # legacy_windows, so LegacyWindowsTerm rendering runs regardless.
                # "line" is ASCII-only ('-', '\\', '|', '/').
                SpinnerColumn(spinner_name="line"),
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
                while i < len(pending_chunks):
                    batch = sorted_chunks[i : i + current_batch_size]
                    batch_contents = sorted_contents[i : i + current_batch_size]
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

                    # Generate embeddings for batch with OOM recovery
                    # Use convert_to_tensor for GPU to avoid CPU<->GPU transfers (10-20% faster)
                    use_tensor = self._is_gpu_device()

                    try:
                        # pyrefly: ignore [missing-attribute]
                        with self._lifecycle_lock:
                            # pyrefly: ignore [missing-attribute]
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
                        is_legacy_torch_oom = any(
                            s in err_str for s in _PYTORCH_OOM_STRINGS
                        )
                        is_oom = is_torch_oom or is_ort_oom or is_legacy_torch_oom
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
                            remaining_chunks = len(pending_chunks) - i
                            remaining_batches = (
                                remaining_chunks + current_batch_size - 1
                            ) // current_batch_size
                            progress.update(task, total=completed + remaining_batches)
                            # Flush GPU caches before retry
                            if torch and torch.cuda.is_available():
                                torch.cuda.empty_cache()
                            gc.collect()
                            batch_num -= (
                                1  # this attempt is retried, don't advance counter
                            )
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
                        zip(batch, batch_embeddings, strict=True)
                    ):
                        chunk_id = self._build_chunk_id(chunk)
                        metadata = self._build_chunk_metadata(chunk)

                        results.append(
                            EmbeddingResult(
                                embedding=embedding,
                                chunk_id=chunk_id,
                                metadata=metadata,
                            )
                        )

                    # Log VRAM after batch
                    self._log_vram_usage("BATCH_END", batch_num)

                    # Advance to next chunk position and update progress bar
                    i += current_batch_size
                    progress.update(task, advance=1)
        finally:
            # Restore log level even if VRAMExhaustedError / OOM escapes (#20).
            self._logger.setLevel(original_log_level)

        # `results` was built in length-sorted order over the miss subset (see
        # sort_order above); restore pending order first, then scatter into the
        # `ordered_results` array that cache hits (if any) already populated
        # during partitioning above. Callers (index_write_stage.py,
        # incremental_indexer.py) all zip this return value positionally
        # against the original `chunks` list, so a mis-scattered return
        # would silently mis-associate metadata.
        pending_ordered: list[EmbeddingResult | None] = [None] * len(pending_chunks)
        for sorted_pos, pending_idx in enumerate(sort_order):
            pending_ordered[pending_idx] = results[sorted_pos]
        assert all(r is not None for r in pending_ordered), (
            "embed_chunks: un-permute produced a hole — batch loop did not "
            "append exactly one result per pending chunk"
        )

        for pending_idx, original_idx in enumerate(pending_indices):
            ordered_results[original_idx] = pending_ordered[pending_idx]

        assert all(r is not None for r in ordered_results), (
            "embed_chunks: cache/miss scatter produced a hole — every input "
            "chunk must resolve to exactly one cache hit or fresh embedding"
        )

        # Write fresh embeddings back to the persistent cache. `cache_keys` was
        # fully populated for every index during partitioning above whenever
        # `cache_enabled` (both hits and misses got a key), so `live_keys`
        # covers this run's entire input — exactly what save()'s eviction must
        # never drop. Gated on `cache_enabled`, not `cache is not None`: a
        # cache-read failure above disables the cache for the rest of this
        # call, so a broken cache is never written back to either.
        if cache_enabled and cache is not None:
            for pending_idx, original_idx in enumerate(pending_indices):
                key = cache_keys[original_idx]
                if key is not None:
                    result = pending_ordered[pending_idx]
                    assert result is not None
                    cache.put(key, result.embedding)
            live_keys = {key for key in cache_keys if key is not None}
            cache.save(live_keys, full_pass=cache_full_pass)
            self._log_chunk_cache_stats(cache, "run complete")

        self._logger.info("Embedding generation completed")
        return cast(list[EmbeddingResult], ordered_results)

    def _log_chunk_cache_stats(self, cache: Any, label: str) -> None:
        """Log the persistent chunk-embedding cache's hit rate, best-effort.

        Without this, a normal high-hit run logs nothing at all about the
        cache's health — a silent drop to 0% hit rate would be invisible.
        Never raises: stats retrieval is diagnostic only.
        """
        try:
            stats = cache.get_stats()
            self._logger.info(
                "[CHUNK_CACHE] %s: hits=%s misses=%s hit_rate=%s size=%s cap=%s",
                label,
                stats["hits"],
                stats["misses"],
                stats["hit_rate"],
                stats["cache_size"],
                stats["max_entries"],
            )
        except Exception:  # noqa: BLE001 - fail-soft: stats are diagnostic only
            self._logger.debug("[CHUNK_CACHE] stats unavailable", exc_info=True)

    def get_cache_stats(self) -> dict:
        """Get query-embedding cache hit/miss statistics.

        Note: this is the *query* cache (``QueryEmbeddingCache``, used by
        ``embed_query``/``embed_queries_batch``) — not the persistent
        chunk-embedding cache passed into ``embed_chunks`` via ``cache=``.
        For that cache's stats, call ``.get_stats()`` on the
        ``ChunkEmbeddingCache`` instance directly.
        """
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
        instruction_mode = model_config.get("instruction_mode") or ""
        query_instruction = model_config.get("query_instruction", "")

        # Try to get from cache
        cached_embedding = self._query_cache.get(
            query=query,
            model_name=self.model_name,
            task_instruction=model_config.get("task_instruction", ""),
            query_prefix=model_config.get("query_prefix", ""),
            instruction_mode=instruction_mode,
            query_instruction=query_instruction,
        )

        if cached_embedding is not None:
            return cached_embedding
        encode_kwargs: dict[str, Any] = {"show_progress_bar": False}
        if self._is_gpu_device():
            encode_kwargs["convert_to_tensor"] = True
            encode_kwargs["device"] = self.device
        if instruction_mode == "prompt_name":
            prompt_name_value = model_config.get("prompt_name", "query")
            encode_kwargs["prompt_name"] = prompt_name_value
            self._logger.debug(
                f"Using prompt_name='{prompt_name_value}' for query encoding"
            )
        elif instruction_mode == "custom":
            self._logger.debug("Using custom instruction for query encoding")
        query_to_embed = self._format_query_text(query, model_config)

        # pyrefly: ignore [missing-attribute]
        with self._lifecycle_lock:
            # pyrefly: ignore [missing-attribute]
            embedding = self.model.encode([query_to_embed], **encode_kwargs)[0]
        # bf16 tensors must be cast to float32 before numpy conversion
        embedding = self._tensor_to_numpy(embedding)

        # Add to cache
        self._query_cache.put(
            query=query,
            model_name=self.model_name,
            embedding=embedding,
            task_instruction=model_config.get("task_instruction", ""),
            query_prefix=model_config.get("query_prefix", ""),
            instruction_mode=instruction_mode,
            query_instruction=query_instruction,
        )

        return embedding

    def embed_queries_batch(self, queries: list[str]) -> np.ndarray:
        """Embed N queries in one forward pass; cache hits skip the model call.

        Returns:
            np.ndarray of shape (N, embedding_dim), dtype float32.
        """
        model_config = self._get_model_config()
        if not queries:
            dim = int(model_config.get("dimension", 768))
            return np.empty((0, dim), dtype=np.float32)

        task_instruction = model_config.get("task_instruction", "")
        query_prefix = model_config.get("query_prefix", "")
        instruction_mode = model_config.get("instruction_mode") or ""
        query_instruction = model_config.get("query_instruction", "")

        results: list[np.ndarray | None] = [None] * len(queries)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, query in enumerate(queries):
            cached = self._query_cache.get(
                query=query,
                model_name=self.model_name,
                task_instruction=task_instruction,
                query_prefix=query_prefix,
                instruction_mode=instruction_mode,
                query_instruction=query_instruction,
            )
            if cached is not None:
                results[i] = cached
            else:
                uncached_indices.append(i)
                uncached_texts.append(self._format_query_text(query, model_config))

        if uncached_texts:
            encode_kwargs: dict[str, Any] = {"show_progress_bar": False}
            if instruction_mode == "prompt_name":
                encode_kwargs["prompt_name"] = model_config.get("prompt_name", "query")
            if self._is_gpu_device():
                encode_kwargs["convert_to_tensor"] = True
                encode_kwargs["device"] = self.device

            # pyrefly: ignore [missing-attribute]
            with self._lifecycle_lock:
                # pyrefly: ignore [missing-attribute]
                raw = self.model.encode(uncached_texts, **encode_kwargs)

            for local_i, orig_i in enumerate(uncached_indices):
                emb = self._tensor_to_numpy(raw[local_i])
                self._query_cache.put(
                    query=queries[orig_i],
                    model_name=self.model_name,
                    embedding=emb,
                    task_instruction=task_instruction,
                    query_prefix=query_prefix,
                    instruction_mode=instruction_mode,
                    query_instruction=query_instruction,
                )
                results[orig_i] = emb

        assert all(r is not None for r in results), (
            "BUG: cache miss left a result slot unfilled"
        )
        # pyrefly: ignore [no-matching-overload]
        return np.stack(results)

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the loaded model."""
        if self._model is None:
            return {"status": "not_loaded"}

        model = self._model
        # sentence-transformers >=5 renamed get_sentence_embedding_dimension ->
        # get_embedding_dimension. Prefer the new name; fall back for
        # pre-5.x sentence-transformers versions that only expose the old name.
        if hasattr(model, "get_embedding_dimension"):
            embedding_dimension = model.get_embedding_dimension()
        else:
            embedding_dimension = model.get_sentence_embedding_dimension()

        return {
            "model_name": self.model_name,
            "embedding_dimension": embedding_dimension,
            "max_seq_length": getattr(model, "max_seq_length", "unknown"),
            "device": str(model.device),
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

        Returns:
            Model VRAM usage in GB, or 0.0 if GPU not available
        """
        if torch is None or not torch.cuda.is_available():
            return 0.0

        try:
            allocated_bytes = torch.cuda.memory_allocated()
            return allocated_bytes / (1024**3)
        except RuntimeError as e:
            self._logger.debug(f"Failed to get model VRAM: {e}")
            return 0.0

    def _extract_hf_config(self) -> Any | None:
        """Extract HuggingFace PretrainedConfig from the loaded SentenceTransformer model.

        Returns the first config object found that has a ``hidden_size`` attribute,
        or None if the model is not loaded or the config cannot be extracted.
        """
        if self._model is None:
            return None
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
        # pyrefly: ignore [missing-attribute]
        with self._lifecycle_lock:
            if self._model is not None:
                try:
                    # Step 1: Free GPU memory.
                    # Move to CPU first to free VRAM, then delete.
                    if (
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
                        # pyrefly: ignore [bad-assignment]
                        self._model_loader = None
                        self._logger.info("Model loader cleared - lazy reload disabled")

                    # Step 5: Force garbage collection (frees RAM)
                    gc.collect()
                    self._logger.info("RAM freed via garbage collection")

                    # Step 6: Final CUDA cache clear
                    if torch is not None and torch.cuda.is_available():
                        torch.cuda.empty_cache()

                    self._logger.info("Model cleanup complete - VRAM and RAM freed")
                except Exception as e:  # noqa: BLE001 - cleanup: best-effort model teardown must not raise
                    self._logger.warning(f"Error during model cleanup: {e}")

    def __enter__(self) -> "CodeEmbedder":
        """Context manager entry - ensure model is loaded."""
        # Trigger model loading
        _ = self.model
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup resources."""
        self.cleanup()
        # pyrefly: ignore [bad-return]
        return False  # Don't suppress exceptions

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        with contextlib.suppress(Exception):
            # Non-blocking acquire: if another thread holds the lock, skip cleanup
            # rather than stalling the GC thread indefinitely.
            # pyrefly: ignore [missing-attribute]
            if self._lifecycle_lock.acquire(blocking=False):
                try:
                    self.cleanup()
                finally:
                    # pyrefly: ignore [missing-attribute]
                    self._lifecycle_lock.release()
