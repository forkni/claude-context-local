"""Multi-model embedder for generating code embeddings.

Supports multiple embedding models including:
- EmbeddingGemma (google/embeddinggemma-300m)
- BGE-M3 (BAAI/bge-m3)
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from embeddings.model_cache import ModelCacheManager
from embeddings.query_cache import QueryEmbeddingCache
from search.filters import normalize_path

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
except Exception:
    torch = None

from chunking.python_ast_chunker import CodeChunk


# Helper function to access config via ServiceLocator (avoids circular imports)
def _get_config_via_service_locator():
    """Get SearchConfig via ServiceLocator to avoid circular dependencies."""
    from mcp_server.services import ServiceLocator

    return ServiceLocator.instance().get_config()


def calculate_optimal_batch_size(
    embedding_dim: int = 768,
    min_batch: int = 32,
    max_batch: int = 512,
    memory_fraction: float = 0.7,
) -> int:
    """Calculate optimal batch size based on GPU VRAM tiers.

    Uses simple GPU memory tiers for reliable batch sizing that accounts for
    model activation memory (not just embedding output):
    - ≤8GB VRAM: 128 batch size
    - 10-16GB VRAM: 256 batch size
    - ≥24GB VRAM: 512 batch size

    Args:
        embedding_dim: Embedding dimension (unused, kept for API compatibility)
        min_batch: Minimum batch size (safety floor, default: 32)
        max_batch: Maximum batch size (default: 512)
        memory_fraction: Unused, kept for API compatibility

    Returns:
        Batch size based on GPU tier, clamped to [min_batch, max_batch]

    Examples:
        >>> # RTX 3070 (8GB VRAM)
        >>> calculate_optimal_batch_size()
        128

        >>> # RTX 4080 (16GB VRAM)
        >>> calculate_optimal_batch_size()
        256

        >>> # RTX 4090 (24GB VRAM)
        >>> calculate_optimal_batch_size()
        512
    """
    if not torch or not torch.cuda.is_available():
        return min_batch  # CPU fallback

    try:
        # Get total GPU memory (not free, to be consistent across runs)
        _, total_memory = torch.cuda.mem_get_info()
        total_gb = total_memory / (1024**3)

        # GPU-tiered batch sizes (conservative, accounts for model activations)
        if total_gb <= 8:
            optimal_batch = 128
        elif total_gb <= 16:
            optimal_batch = 256
        else:  # 24GB+
            optimal_batch = 512

        # Clamp to config limits
        result = max(min_batch, min(optimal_batch, max_batch))

        # Log for debugging
        logger = logging.getLogger(__name__)
        logger.info(
            f"[DYNAMIC_BATCH] GPU: {total_gb:.1f}GB total → batch size: {result} (tier-based)"
        )

        return result

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"[DYNAMIC_BATCH] Failed to calculate batch size: {e}, using min_batch={min_batch}"
        )
        return min_batch  # Fallback on error


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: np.ndarray
    chunk_id: str
    metadata: Dict[str, Any]


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
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir or str(
            Path.home() / ".cache" / "huggingface" / "hub"
        )
        self.device = device
        self._model = None
        self._logger = logging.getLogger(__name__)
        self._model_config = None

        # Query embedding cache (LRU)
        self._query_cache = QueryEmbeddingCache(max_size=128)

        # Model cache manager
        self._cache_manager = ModelCacheManager(
            model_name=model_name,
            cache_dir=cache_dir or str(Path.home() / ".cache" / "huggingface" / "hub"),
            model_config_getter=self._get_model_config,
        )

        # Track per-model VRAM usage
        self._model_vram_usage: Dict[str, float] = {}  # model_key -> VRAM MB

        # Setup logging
        logging.basicConfig(level=logging.INFO)

    @classmethod
    def get_supported_models(cls) -> Dict[str, Dict[str, Any]]:
        """Get dictionary of supported models and their configurations."""
        from search.config import get_model_registry

        return get_model_registry()

    def _get_model_config(self) -> Dict[str, Any]:
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

    def _log_gpu_memory(self, stage: str):
        """Log GPU memory usage at specific loading stages."""
        if torch is None or not torch.cuda.is_available():
            return

        try:
            for gpu_id in range(torch.cuda.device_count()):
                allocated = torch.cuda.memory_allocated(gpu_id) / 1024**3  # GB
                reserved = torch.cuda.memory_reserved(gpu_id) / 1024**3  # GB
                total = torch.cuda.get_device_properties(gpu_id).total_memory / 1024**3

                self._logger.info(
                    f"[GPU_{gpu_id}] {stage}: "
                    f"Allocated={allocated:.2f}GB, "
                    f"Reserved={reserved:.2f}GB, "
                    f"Total={total:.2f}GB "
                    f"({allocated / total * 100:.1f}% used)"
                )
        except Exception as e:
            self._logger.debug(f"GPU memory logging failed: {e}")

    def _get_torch_dtype(self):
        """Get torch dtype based on config and GPU capability.

        Returns:
            torch dtype (fp16/bf16) for GPU, or None for fp32 default.

        Precision hierarchy:
            1. bf16 (bfloat16) - Ampere+ GPUs, better accuracy than fp16
            2. fp16 (float16) - All CUDA GPUs, fastest inference
            3. None (fp32) - CPU or fp16 disabled
        """
        if torch is None or not torch.cuda.is_available():
            return None  # CPU: use fp32 default

        # Use ServiceLocator helper instead of inline import
        config = _get_config_via_service_locator()

        if not config.performance.enable_fp16:
            return None  # fp16 disabled: use fp32

        # Check bf16 support (requires Ampere+ architecture)
        if config.performance.prefer_bf16:
            try:
                if torch.cuda.is_bf16_supported():
                    self._logger.info(
                        "[PRECISION] Using bfloat16 (bf16) for model inference (Ampere+ GPU detected)"
                    )
                    return torch.bfloat16
            except Exception as e:
                self._logger.debug(f"bf16 check failed: {e}, falling back to fp16")

        # Fallback to fp16 for all CUDA GPUs
        self._logger.info(
            "[PRECISION] Using float16 (fp16) for model inference (30-50% faster)"
        )
        return torch.float16

    def _is_gpu_device(self) -> bool:
        """Check if current device is GPU (cuda/mps).

        Returns:
            True if device is GPU, False if CPU.
        """
        if not self.device:
            return False

        device_str = str(self.device).lower()
        return "cuda" in device_str or "mps" in device_str

    @property
    def model(self):
        """Lazy loading of the model."""
        if self._model is None:
            self._load_model()
        return self._model

    def _load_model(self):
        """Load model with automatic cache corruption recovery and fallback."""
        import shutil

        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers not found. Install with: "
                "pip install sentence-transformers>=5.0.0"
            )

        self._logger.info(f"Loading model: {self.model_name}")

        # Step 1: Validate cache integrity (comprehensive checks)
        cache_valid, cache_reason = self._validate_model_cache()
        cache_path_obj = self._get_model_cache_path()

        # Check if cache directory exists but is corrupted
        if cache_path_obj and cache_path_obj.exists() and not cache_valid:
            # Step 1a: Check if corruption is due to incomplete downloads
            has_incomplete, incomplete_msg = self._check_incomplete_downloads()

            if has_incomplete and "Incomplete downloads detected" in cache_reason:
                # Corruption is due to incomplete downloads - try cleanup first
                self._logger.warning(
                    f"[INCOMPLETE DOWNLOADS] {incomplete_msg}\n"
                    f"[AUTO-CLEANUP] Removing incomplete files and retrying..."
                )

                # Clean up incomplete downloads
                removed_count, removed_files = self._cleanup_incomplete_downloads()

                if removed_count > 0:
                    self._logger.info(
                        f"[CLEANUP SUCCESS] Removed {removed_count} incomplete file(s)"
                    )

                    # Re-validate cache after cleanup
                    cache_valid_retry, cache_reason_retry = self._validate_model_cache()

                    if cache_valid_retry:
                        # Cache is now valid after cleanup!
                        self._logger.info(
                            "[RECOVERY SUCCESS] Cache is now valid after incomplete download cleanup"
                        )
                        cache_valid = True
                        cache_reason = "Valid after cleanup"
                    else:
                        # Still corrupted after cleanup - proceed with full cache deletion
                        self._logger.warning(
                            f"[CLEANUP INSUFFICIENT] Cache still corrupted after cleanup: {cache_reason_retry}\n"
                            f"[AUTO-RECOVERY] Deleting entire cache and re-downloading..."
                        )
                else:
                    self._logger.warning(
                        "[CLEANUP FAILED] Could not remove incomplete files\n"
                        "[AUTO-RECOVERY] Proceeding with cache deletion..."
                    )

            # Step 1b: If still corrupted, delete cache and force re-download
            if not cache_valid:
                # Cache exists but is corrupted - attempt automatic recovery
                self._logger.warning(
                    f"[CACHE CORRUPTED] {cache_reason}\n"
                    f"[AUTO-RECOVERY] Deleting corrupted cache and re-downloading from HuggingFace..."
                )

                try:
                    # Delete corrupted cache directory
                    shutil.rmtree(cache_path_obj)
                    self._logger.info(f"[DELETED] Corrupted cache: {cache_path_obj}")
                    cache_valid = False  # Force re-download
                except Exception as e:
                    # Failed to delete corrupted cache - provide manual cleanup instructions
                    raise RuntimeError(
                        f"[CACHE CORRUPTION] Cache cannot be deleted automatically.\n"
                        f"Cache path: {cache_path_obj}\n"
                        f"Error: {e}\n\n"
                        f"Manual fix required:\n"
                        f"  1. Close all applications using the model\n"
                        f"  2. Delete directory: {cache_path_obj}\n"
                        f"  3. Re-run indexing to download fresh model\n\n"
                        f"Alternative: Use cleanup utility:\n"
                        f'  python tools/cleanup_model_cache.py --model "{self.model_name}"'
                    ) from e

        # Step 2: Validate model exists on HuggingFace (if no valid cache)
        if not cache_valid:
            # Model not cached or cache was corrupted - validate on HuggingFace Hub
            try:
                from huggingface_hub import model_info

                self._logger.info(
                    f"Checking if '{self.model_name}' exists on HuggingFace Hub..."
                )
                info = model_info(self.model_name)
                self._logger.info(
                    f"Model found: {info.modelId} (library: {info.library_name or 'unknown'})"
                )
            except ImportError:
                self._logger.warning(
                    "huggingface_hub not available, skipping model existence check. "
                    "Install with: pip install huggingface_hub"
                )
            except Exception as e:
                # Model not found on HuggingFace Hub
                from search.config import MODEL_REGISTRY

                available_models = list(MODEL_REGISTRY.keys())
                raise ValueError(
                    f"Model '{self.model_name}' not found on HuggingFace Hub!\n"
                    f"Error: {e}\n"
                    f"Available models in registry: {available_models}\n"
                    f"Please check:\n"
                    f"  1. Model name for typos (e.g., 'Qodo/Qodo-Embed-1-1.5B')\n"
                    f"  2. Model exists on https://huggingface.co/{self.model_name}\n"
                    f"  3. You have internet access to download the model"
                ) from e

        # Step 3: Prepare for loading (enable offline mode if cache is valid)
        local_model_dir = None
        if cache_valid:
            # Only use cached path if validation passed
            try:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
                self._logger.info(
                    "[VALIDATED CACHE] Enabling offline mode for faster startup."
                )
                local_model_dir = self._find_local_model_dir()
                if local_model_dir:
                    self._logger.info(
                        f"Loading model from validated cache: {local_model_dir}"
                    )
            except Exception as _e:
                self._logger.debug(f"Offline mode detection skipped: {_e}")

        # Step 4: Load model with automatic fallback
        resolved_device = self._resolve_device(self.device)
        self._log_gpu_memory("BEFORE_LOAD")

        # Track VRAM before loading model
        import torch

        vram_before = 0
        if torch.cuda.is_available():
            vram_before = torch.cuda.memory_allocated()

        # Determine precision (fp16/bf16) for GPU inference
        torch_dtype = self._get_torch_dtype()

        # Step 4a: Use PyTorch backend only
        model_source = str(local_model_dir) if local_model_dir else self.model_name
        model_kwargs_dict = {}

        # Add dtype for PyTorch backend (renamed from torch_dtype in sentence-transformers 5.x)
        if torch_dtype is not None:
            model_kwargs_dict["dtype"] = torch_dtype

        try:
            # Build constructor kwargs
            constructor_kwargs = {
                "cache_folder": self.cache_dir,
                "device": resolved_device,
                "trust_remote_code": True,  # Required for some models like Qodo
            }

            # Add Matryoshka Representation Learning (MRL) support
            model_config = self._get_model_config()
            truncate_dim = model_config.get("truncate_dim")
            if truncate_dim is not None:
                constructor_kwargs["truncate_dim"] = truncate_dim
                self._logger.info(
                    f"Matryoshka MRL enabled: truncating output to {truncate_dim} dimensions"
                )

            # Add model_kwargs if any options (e.g., dtype)
            if model_kwargs_dict:
                constructor_kwargs["model_kwargs"] = model_kwargs_dict

            # Debug: Log constructor args
            self._logger.debug(
                f"SentenceTransformer constructor kwargs: {constructor_kwargs}"
            )

            self._model = SentenceTransformer(model_source, **constructor_kwargs)

            self.device = resolved_device

            # Build detailed info string
            precision_info = f" ({torch_dtype})" if torch_dtype else " (fp32 default)"

            self._logger.info(
                f"Model loaded successfully on device: {self._model.device} [backend=pytorch]{precision_info}"
            )
            self._log_gpu_memory("AFTER_LOAD")

            # Track VRAM usage for this model
            if torch.cuda.is_available():
                vram_after = torch.cuda.memory_allocated()
                vram_used_mb = (vram_after - vram_before) / (1024 * 1024)
                # Clamp to 0 minimum to handle multi-model memory accounting
                vram_used_mb = max(0, vram_used_mb)
                self._model_vram_usage[self.model_name] = round(vram_used_mb, 1)
                self._logger.info(
                    f"Model VRAM usage: {vram_used_mb:.1f} MB ({self.model_name})"
                )

            # If cache was invalid (fresh download), ensure symlink for future loads
            if not cache_valid:
                self._ensure_split_cache_symlink()

        except Exception as e:
            # Step 5: Fallback - If loading from cache failed, try network download
            if local_model_dir:
                self._logger.warning(
                    f"[CACHE LOAD FAILED] {str(e)}\n"
                    f"[FALLBACK] Attempting network re-download..."
                )

                # Disable offline mode to allow re-download
                os.environ.pop("HF_HUB_OFFLINE", None)
                os.environ.pop("TRANSFORMERS_OFFLINE", None)

                try:
                    # Build constructor kwargs for fallback
                    fallback_kwargs = {
                        "cache_folder": self.cache_dir,
                        "device": resolved_device,
                        "trust_remote_code": True,
                    }

                    # Preserve truncate_dim for MRL support
                    if truncate_dim is not None:
                        fallback_kwargs["truncate_dim"] = truncate_dim

                    # Preserve model_kwargs (e.g., torch_dtype)
                    if model_kwargs_dict:
                        fallback_kwargs["model_kwargs"] = model_kwargs_dict

                    self._model = SentenceTransformer(
                        self.model_name,  # Use model name, not local path
                        **fallback_kwargs,
                    )
                    self.device = resolved_device
                    self._logger.info(
                        "[FALLBACK SUCCESS] Downloaded fresh model from HuggingFace"
                    )
                    self._log_gpu_memory("AFTER_FALLBACK_LOAD")

                    # Track VRAM usage for this model (fallback path)
                    if torch.cuda.is_available():
                        vram_after = torch.cuda.memory_allocated()
                        vram_used_mb = (vram_after - vram_before) / (1024 * 1024)
                        # Clamp to 0 minimum to handle multi-model memory accounting
                        vram_used_mb = max(0, vram_used_mb)
                        self._model_vram_usage[self.model_name] = round(vram_used_mb, 1)
                        self._logger.info(
                            f"Model VRAM usage: {vram_used_mb:.1f} MB ({self.model_name})"
                        )
                except Exception as e2:
                    # Both cache and network download failed
                    raise RuntimeError(
                        f"[MODEL LOAD FAILED] All recovery attempts exhausted.\n\n"
                        f"Attempted:\n"
                        f"  ✓ Cache validation - {'PASSED' if cache_valid else 'FAILED (' + cache_reason + ')'}\n"
                        f"  ✓ Cache load - FAILED ({str(e)})\n"
                        f"  ✓ Network re-download - FAILED ({str(e2)})\n\n"
                        f"Possible causes:\n"
                        f"  1. Network connectivity issues\n"
                        f"  2. HuggingFace Hub access blocked\n"
                        f"  3. Model incompatible with sentence-transformers version\n"
                        f"  4. Insufficient disk space for download\n\n"
                        f"Manual fixes:\n"
                        f"  1. Check internet connection and retry\n"
                        f'  2. Clear cache: python tools/cleanup_model_cache.py --model "{self.model_name}"\n'
                        f"  3. Verify model exists: https://huggingface.co/{self.model_name}\n"
                        f"  4. Check disk space and permissions"
                    ) from e2
            else:
                # No cache to fall back from - this is a direct download failure
                raise RuntimeError(
                    f"[MODEL DOWNLOAD FAILED] {str(e)}\n\n"
                    f"Attempted:\n"
                    f"  ✓ Cache validation - {'PASSED' if cache_valid else 'FAILED (' + cache_reason + ')'}\n"
                    f"  ✓ Network download - FAILED\n\n"
                    f"Please check:\n"
                    f"  1. Internet connectivity\n"
                    f"  2. HuggingFace Hub access\n"
                    f"  3. Model name is correct: {self.model_name}\n"
                    f"  4. Sufficient disk space for download"
                ) from e

    def create_embedding_content(self, chunk: CodeChunk, max_chars: int = 6000) -> str:
        """Create clean content for embedding generation with size limits."""
        # Prepare clean content without fabricated headers
        content_parts = []

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
        docstring_len = len(content_parts[0]) if content_parts else 0
        remaining_budget = max_chars - docstring_len - 10  # small buffer

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
                current_length = docstring_len

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
        self, chunks: List[CodeChunk], batch_size: Optional[int] = None
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple chunks with batching."""
        results = []

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
                batch_size = calculate_optimal_batch_size(
                    embedding_dim=config.embedding.dimension,
                    min_batch=config.performance.dynamic_batch_min,
                    max_batch=config.performance.dynamic_batch_max,
                    memory_fraction=config.performance.gpu_memory_threshold,
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

        # Get model-specific configuration for prefixing
        model_config = self._get_model_config()
        passage_prefix = model_config.get("passage_prefix", "")

        # Ensure model is loaded before starting progress bar
        # (model loads lazily on first encode() call - causes log interference)
        if not hasattr(self, "_model_warmed_up") or not self._model_warmed_up:
            self.model.encode(["warmup"], show_progress_bar=False)
            self._model_warmed_up = True

        # Process in batches for efficiency with progress bar
        console = Console(force_terminal=True)
        total_batches = (len(chunks) + batch_size - 1) // batch_size

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

                # Generate embeddings for batch
                # Use convert_to_tensor for GPU to avoid CPU<->GPU transfers (10-20% faster)
                use_tensor = self._is_gpu_device()
                batch_embeddings = self.model.encode(
                    batch_contents,
                    show_progress_bar=False,
                    convert_to_tensor=use_tensor,
                    device=self.device if use_tensor else None,
                )

                # Convert back to numpy for consistency with rest of codebase
                # Note: bf16 tensors must be converted to float32 first (numpy doesn't support bf16)
                if torch and torch.is_tensor(batch_embeddings):
                    batch_embeddings = batch_embeddings.cpu().float().numpy()

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

                # Update progress bar
                progress.update(task, advance=1)

        self._logger.info("Embedding generation completed")
        return results

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics."""
        return self._query_cache.get_stats()

    def clear_query_cache(self):
        """Clear the query embedding cache."""
        self._query_cache.clear()

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

    def get_model_info(self) -> Dict[str, Any]:
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

    def get_vram_usage(self) -> Dict[str, float]:
        """Return per-model VRAM usage in MB.

        Returns:
            Dictionary mapping model names to VRAM usage in MB.
        """
        return dict(self._model_vram_usage)

    def cleanup(self):
        """Clean up model from memory to free GPU/CPU resources."""
        if self._model is not None:
            try:
                # Move model to CPU and delete
                if hasattr(self._model, "to"):
                    self._model.to("cpu")
                if torch is not None and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                del self._model
                self._model = None
                self._logger.info("Model cleaned up and memory freed")
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
        """Resolve target device string.
        - "auto": prefer cuda, then mps, else cpu
        - explicit values are validated and coerced to available devices
        """
        req = (requested or "auto").lower()
        # If torch is not available, default to CPU
        if torch is None:
            return "cpu"
        if req in ("auto", "none", ""):
            if torch.cuda.is_available():
                return "cuda"
            # MPS for Apple Silicon
            try:
                if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    return "mps"
            except Exception:
                pass
            return "cpu"
        # Validate explicit devices
        if req.startswith("cuda"):
            return "cuda" if torch.cuda.is_available() else "cpu"
        if req == "mps":
            try:
                return (
                    "mps"
                    if hasattr(torch.backends, "mps")
                    and torch.backends.mps.is_available()
                    else "cpu"
                )
            except Exception:
                return "cpu"
        # Default fallback
        return "cpu"
