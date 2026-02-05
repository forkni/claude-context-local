"""Multi-model embedder for generating code embeddings.

Supports multiple embedding models including:
- EmbeddingGemma (google/embeddinggemma-300m)
- BGE-M3 (BAAI/bge-m3)
"""

import gc
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

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


# ===== BATCH SIZE MEMORY ESTIMATION CONSTANTS =====
# Empirically derived from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18% overhead
FRAGMENTATION_OVERHEAD = 0.82  # 1.0 - 0.18 = 82% usable VRAM, 18% fragmentation

# Activation memory costs per batch item (GB) based on model size tier
# Larger models have deeper layer stacks → more activation memory per item
GB_PER_ITEM_LARGE_MODEL = 0.40  # ~400MB per item (e.g., Qwen3-4B: 36 layers)
GB_PER_ITEM_MEDIUM_MODEL = 0.08  # ~80MB per item (e.g., BGE-M3: ~12 layers)
GB_PER_ITEM_SMALL_MODEL = 0.04  # ~40MB per item (e.g., CodeRankEmbed: ~6 layers)


# Configure PyTorch CUDA allocator BEFORE any torch imports
# This must be done early to prevent fragmentation and enable better memory management
def _configure_cuda_allocator():
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


def set_vram_limit(fraction: float = 0.90) -> bool:
    """Set hard VRAM limit to prevent shared memory spillover.

    On Windows, the NVIDIA driver preemptively evicts to shared memory when
    VRAM approaches capacity. This hard limit prevents that by raising OOM
    errors instead of spilling (which is much faster than slow spillover).

    If allow_ram_fallback is True in config, skip setting the limit to allow
    slower but more reliable spillover to system RAM.

    Args:
        fraction: Fraction of dedicated VRAM to use (default: 0.90 = 90%)
                  Recommended: 0.85-0.95 depending on GPU headroom needs

    Returns:
        True if limit was set successfully, False otherwise

    Note:
        Should be called early, before heavy CUDA allocations.
    """
    if not torch or not torch.cuda.is_available():
        return False

    # Check if RAM fallback is allowed
    try:
        config = _get_config_via_service_locator()
        if config and config.performance.allow_ram_fallback:
            logging.getLogger(__name__).info(
                "[VRAM_LIMIT] RAM fallback allowed - skipping hard VRAM limit"
            )
            return True  # Don't set limit, allow spillover
    except Exception as e:
        logging.getLogger(__name__).debug(f"Config not available, using defaults: {e}")

    try:
        torch.cuda.set_per_process_memory_fraction(fraction, device=0)
        logging.getLogger(__name__).info(
            f"[VRAM_LIMIT] Set hard limit to {fraction:.0%} of dedicated VRAM"
        )
        return True
    except Exception as e:
        logging.getLogger(__name__).warning(f"[VRAM_LIMIT] Failed to set: {e}")
        return False


def calculate_optimal_batch_size(
    embedding_dim: int = 768,
    min_batch: int = 32,
    max_batch: int = 256,  # Conservative cap to prevent spillover
    memory_fraction: float = 0.8,  # Target 80% VRAM utilization (20% headroom)
    model_vram_gb: float = 0.0,
    model_name: Optional[str] = None,
) -> int:
    """Calculate optimal batch size using model-aware activation memory estimation.

    Uses empirical activation memory costs per batch item based on model complexity.
    Larger models (more layers) have proportionally larger activation memory per
    batch item, so batch size must be reduced accordingly.

    Activation Cost Tiers (empirically derived):
    - Large models (≥6GB): 0.40 GB/item (e.g., Qwen3-4B with 36 layers)
    - Medium models (2-6GB): 0.08 GB/item (e.g., BGE-M3 with ~12 layers)
    - Small models (<2GB): 0.04 GB/item (e.g., CodeRankEmbed with ~6 layers)

    Target VRAM utilization: 80% of available memory (20% headroom for CUDA overhead)

    Args:
        embedding_dim: Embedding dimension (unused, kept for API compatibility)
        min_batch: Minimum batch size (safety floor, default: 32)
        max_batch: Maximum batch size (conservative cap, default: 256)
        memory_fraction: Target VRAM utilization (default: 0.8 = 80%)
        model_vram_gb: Model VRAM usage in GB (measured after model load)
        model_name: Optional model name for logging (not used for overrides)

    Returns:
        Batch size based on model-aware activation estimation, clamped to [min_batch, max_batch]

    Examples:
        >>> # RTX 4090 (24GB) with Qwen3-4B (7.5GB model, large)
        >>> calculate_optimal_batch_size(model_vram_gb=7.5)
        33  # (24 - 7.5) * 0.8 / 0.40 = 33 batch

        >>> # RTX 4090 (24GB) with BGE-M3 (2GB model, medium)
        >>> calculate_optimal_batch_size(model_vram_gb=2.0)
        205  # (24 - 2) * 0.8 / 0.08 = 205 batch

        >>> # RTX 4090 (24GB) with CodeRankEmbed (0.5GB model, small)
        >>> calculate_optimal_batch_size(model_vram_gb=0.5)
        256  # (24 - 0.5) * 0.8 / 0.04 = 469 → capped at 256
    """
    if not torch or not torch.cuda.is_available():
        return min_batch  # CPU fallback

    try:
        # Get total GPU memory (not free, to be consistent across runs)
        _, total_memory = torch.cuda.mem_get_info()
        total_gb = total_memory / (1024**3)

        # Calculate available memory for activations (total - model weights)
        available_gb = total_gb - model_vram_gb

        # Apply fragmentation factor: PyTorch reserves ~18% extra for block management
        # Validated from OOM analysis: 2.67GB fragmentation / 14.74GB allocated = 18% overhead
        # This accounts for "reserved but unallocated" memory that can't be used for tensors
        fragmentation_overhead = FRAGMENTATION_OVERHEAD

        # Target VRAM for activations (leave headroom for CUDA overhead + fragmentation)
        target_activation_gb = available_gb * memory_fraction * fragmentation_overhead

        # Determine activation cost per batch item based on model size
        # Larger models have deeper layer stacks → more activation memory per item
        if model_vram_gb >= 6:  # Large models (e.g., Qwen3-4B: 7.5GB, 36 layers)
            gb_per_item = GB_PER_ITEM_LARGE_MODEL
            model_tier = "large"
        elif model_vram_gb >= 2:  # Medium models (e.g., BGE-M3: 2GB, ~12 layers)
            gb_per_item = GB_PER_ITEM_MEDIUM_MODEL
            model_tier = "medium"
        else:  # Small models (e.g., CodeRankEmbed: 0.5GB, ~6 layers)
            gb_per_item = GB_PER_ITEM_SMALL_MODEL
            model_tier = "small"

        # Calculate optimal batch size based on activation memory budget
        optimal_batch = int(target_activation_gb / gb_per_item)

        # Apply tier-aware batch limits for small GPUs
        # This prevents OOM on 8GB and 6GB GPUs where batch sizes need to be conservative
        if total_gb <= 6:  # minimal tier (<6GB) - Check FIRST
            max_batch = min(max_batch, 16)
            min_batch = min(min_batch, 2)
        elif total_gb <= 10:  # laptop tier (6-10GB)
            max_batch = min(max_batch, 32)
            min_batch = min(min_batch, 4)

        # Clamp to safe bounds
        result = max(min_batch, min(optimal_batch, max_batch))

        # Log calculation details for debugging
        logger = logging.getLogger(__name__)
        logger.info(
            f"[DYNAMIC_BATCH] GPU: {total_gb:.1f}GB total, "
            f"model: {model_vram_gb:.1f}GB ({model_tier}), "
            f"available: {available_gb:.1f}GB → "
            f"target: {target_activation_gb:.1f}GB ({memory_fraction:.0%} × {fragmentation_overhead:.0%} frag), "
            f"cost: {gb_per_item:.2f}GB/item → "
            f"batch: {result} chunks"
        )

        return result

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[DYNAMIC_BATCH] Failed to calculate batch size: {e}, using min_batch={min_batch}"
        )
        return min_batch  # Fallback on error


def parse_vram_gb_from_registry(model_name: str) -> float:
    """Parse VRAM estimate from MODEL_REGISTRY for upfront batch sizing.

    Handles formats: "8-10GB" (range) → 10.0, "2.3GB" (exact) → 2.3, "2GB" → 2.0
    Uses upper bound of range for conservative batch sizing.

    Args:
        model_name: Model identifier (e.g., "Qwen/Qwen3-Embedding-4B")

    Returns:
        VRAM estimate in GB, or 0.0 if not found/parseable

    Examples:
        >>> parse_vram_gb_from_registry("Qwen/Qwen3-Embedding-4B")
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
        cache_dir: Optional[str] = None,
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
        VRAM_WARNING_THRESHOLD = 0.85  # 85% usage
        VRAM_ABORT_THRESHOLD = 0.95  # 95% usage

        if not torch or not torch.cuda.is_available():
            return 0.0, False, False

        try:
            allocated = torch.cuda.memory_allocated()
            total = torch.cuda.get_device_properties(0).total_memory
            usage_pct = allocated / total if total > 0 else 0.0

            should_warn = usage_pct > VRAM_WARNING_THRESHOLD
            should_abort = usage_pct > VRAM_ABORT_THRESHOLD

            return usage_pct, should_warn, should_abort
        except Exception as e:
            self._logger.warning(f"Failed to check VRAM status: {e}")
            return 0.0, False, False

    @property
    def model(self) -> Optional[SentenceTransformer]:
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
            with open(file_path, "r", encoding="utf-8") as f:
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
        except Exception as e:
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
            with open(chunk.file_path, "r", encoding="utf-8") as f:
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

        except Exception as e:
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
        except Exception as e:
            self._logger.debug(f"Failed to load context config, using defaults: {e}")
            # Fallback to defaults
            enable_import_ctx = True
            enable_class_ctx = True
            max_import_lines = 10
            max_class_sig_lines = 5

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
        if passage_prefix:
            content_to_embed = passage_prefix + content
        else:
            content_to_embed = content

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
        self, chunks: list[CodeChunk], batch_size: Optional[int] = None
    ) -> list[EmbeddingResult]:
        """Generate embeddings for multiple chunks with batching."""
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

                # Derive memory_fraction from vram_limit_fraction to maintain consistent safety margin
                # Target ~81% of hard VRAM ceiling for batch sizing (0.8125 ratio)
                memory_fraction = config.performance.vram_limit_fraction * 0.8125

                batch_size = calculate_optimal_batch_size(
                    embedding_dim=config.embedding.dimension,
                    min_batch=config.performance.dynamic_batch_min,
                    max_batch=config.performance.dynamic_batch_max,
                    memory_fraction=memory_fraction,
                    model_vram_gb=model_vram_gb,
                    model_name=self.model_name,
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
        total_batches = (len(chunks) + batch_size - 1) // batch_size

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
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                batch_num = (i // batch_size) + 1

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
                except (RuntimeError, torch.cuda.OutOfMemoryError) as e:
                    # OOM recovery: Clear cache, halve batch, retry
                    if "out of memory" in str(e).lower():
                        half_batch_size = len(batch_contents) // 2
                        if half_batch_size < 1:
                            self._logger.error(
                                "[OOM_RECOVERY] Cannot reduce batch further, re-raising OOM"
                            )
                            raise  # Can't reduce further

                        self._logger.warning(
                            f"[OOM_RECOVERY] CUDA OOM detected! "
                            f"Reducing batch from {len(batch_contents)} to {half_batch_size}, "
                            f"clearing cache, and retrying..."
                        )

                        # Clear GPU cache and Python garbage
                        if torch and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                        gc.collect()

                        # Split batch in half and process each half
                        half1 = batch_contents[:half_batch_size]
                        half2 = batch_contents[half_batch_size:]

                        # Process first half
                        emb1 = self.model.encode(
                            half1,
                            show_progress_bar=False,
                            convert_to_tensor=use_tensor,
                            device=self.device if use_tensor else None,
                        )

                        # Process second half
                        emb2 = self.model.encode(
                            half2,
                            show_progress_bar=False,
                            convert_to_tensor=use_tensor,
                            device=self.device if use_tensor else None,
                        )

                        # Combine results
                        if torch and torch.is_tensor(emb1):
                            batch_embeddings = torch.cat([emb1, emb2], dim=0)
                        else:
                            batch_embeddings = np.vstack([emb1, emb2])

                        self._logger.info(
                            "[OOM_RECOVERY] Successfully recovered from OOM by splitting batch"
                        )
                    else:
                        raise  # Different error, re-raise

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

                # Update progress bar
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

    def _log_vram_usage(self, phase: str, batch_idx: int = 0):
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
        except Exception as e:
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
        except Exception as e:
            self._logger.debug(f"Failed to get model VRAM: {e}")
            return 0.0

    def cleanup(self) -> None:
        """Clean up model from memory to free GPU/CPU resources."""
        if self._model is not None:
            try:
                import gc

                # Step 1: Move model to CPU (frees VRAM immediately)
                if torch is not None and torch.cuda.is_available():
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

    def __enter__(self):
        """Context manager entry - ensure model is loaded."""
        # Trigger model loading
        _ = self.model
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        try:
            self.cleanup()
        except Exception:
            # Intentional: cleanup during interpreter shutdown may fail
            # Logging is unreliable in __del__, so suppress is acceptable
            pass

    # ===== Cache Management Methods (delegated to ModelCacheManager) =====

    def _get_model_cache_path(self) -> Optional[Path]:
        """Delegate to ModelCacheManager.get_model_cache_path()."""
        return self._cache_manager.get_model_cache_path()

    def _get_default_hf_cache_path(self) -> Optional[Path]:
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

    def _find_local_model_dir(self) -> Optional[Path]:
        """Delegate to ModelCacheManager.find_local_model_dir()."""
        return self._cache_manager.find_local_model_dir()

    def _resolve_device(self, requested: Optional[str]) -> str:
        """Delegate to ModelLoader.resolve_device()."""
        return self._model_loader.resolve_device(requested)
