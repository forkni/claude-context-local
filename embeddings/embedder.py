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

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    import torch
except Exception:
    torch = None

from chunking.python_ast_chunker import CodeChunk


# Phase 4: Helper function to access config via ServiceLocator (avoids circular imports)
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
    Default model is google/embeddinggemma-300m for backward compatibility.
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
        self._query_cache_size = 128  # Configurable cache size
        self._query_cache = {}  # Simple dict cache
        self._cache_order = []  # Track insertion order for LRU
        self._cache_hits = 0
        self._cache_misses = 0

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

        # Phase 4: Use ServiceLocator helper instead of inline import
        config = _get_config_via_service_locator()

        if not config.enable_fp16:
            return None  # fp16 disabled: use fp32

        # Check bf16 support (requires Ampere+ architecture)
        if config.prefer_bf16:
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
                    # Failed to delete corrupted cache - provide manual fix instructions
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

        # Add torch_dtype for PyTorch backend
        if torch_dtype is not None:
            model_kwargs_dict["torch_dtype"] = torch_dtype

        try:
            # Build constructor kwargs
            constructor_kwargs = {
                "cache_folder": self.cache_dir,
                "device": resolved_device,
                "trust_remote_code": True,  # Required for some models like Qodo
            }

            # Add model_kwargs if any options (e.g., torch_dtype)
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
                self._model_vram_usage[self.model_name] = round(vram_used_mb, 1)
                self._logger.info(
                    f"Model VRAM usage: {vram_used_mb:.1f} MB ({self.model_name})"
                )

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
        normalized_path = str(chunk.relative_path).replace("\\", "/")
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
            # Phase 4: Use ServiceLocator helper instead of inline import
            config = _get_config_via_service_locator()

            # Try dynamic GPU-based batch size first
            if (
                config.enable_dynamic_batch_size
                and config.prefer_gpu
                and torch
                and torch.cuda.is_available()
            ):
                batch_size = calculate_optimal_batch_size(
                    embedding_dim=config.model_dimension,
                    min_batch=config.dynamic_batch_min,
                    max_batch=config.dynamic_batch_max,
                    memory_fraction=config.gpu_memory_threshold,
                )
                self._logger.info(
                    f"Using dynamic GPU-optimized batch size {batch_size} for {len(chunks)} chunks"
                )
            else:
                batch_size = config.embedding_batch_size
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
                    normalized_path = str(chunk.relative_path).replace("\\", "/")
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
                        # Call graph data (Phase 1: Python only)
                        "calls": (
                            [call.to_dict() for call in chunk.calls]
                            if chunk.calls
                            else []
                        ),
                        # Phase 3: Relationship edges (all relationship types)
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

    def _get_query_cache_key(self, query: str, model_config: dict) -> str:
        """Generate deterministic cache key from query and model config."""
        import hashlib

        key_data = f"{query}|{self.model_name}|{model_config.get('task_instruction', '')}|{model_config.get('query_prefix', '')}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def _add_to_query_cache(self, key: str, embedding: np.ndarray):
        """Add embedding to cache with LRU eviction."""
        # Remove key if it already exists (to update order)
        if key in self._query_cache:
            self._cache_order.remove(key)

        # Evict oldest entry if cache is full
        if len(self._query_cache) >= self._query_cache_size:
            oldest_key = self._cache_order.pop(0)
            del self._query_cache[oldest_key]

        # Add to cache
        self._query_cache[key] = embedding.copy()
        self._cache_order.append(key)

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "cache_size": len(self._query_cache),
            "max_size": self._query_cache_size,
        }

    def clear_query_cache(self):
        """Clear the query embedding cache."""
        self._query_cache.clear()
        self._cache_order.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._logger.info("Query embedding cache cleared")

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a search query with LRU caching.

        Caches query embeddings to improve performance for repeated queries.
        Cache is keyed by query text + model name + prefixes/instructions.

        Supports both query_prefix (simple prefix) and task_instruction
        (instruction-based models like CodeRankEmbed).
        """
        # Get model-specific configuration
        model_config = self._get_model_config()

        # Create cache key from query + model config
        cache_key = self._get_query_cache_key(query, model_config)

        # Check cache
        if cache_key in self._query_cache:
            self._cache_hits += 1
            self._logger.debug(f"Cache hit for query: {query[:50]}...")
            return self._query_cache[cache_key].copy()

        self._cache_misses += 1
        self._logger.debug(f"Cache miss for query: {query[:50]}...")

        # Cache miss - generate embedding
        # Check for task_instruction (e.g., CodeRankEmbed) or query_prefix
        task_instruction = model_config.get("task_instruction")
        query_prefix = model_config.get("query_prefix", "")

        # Prepend prefix/instruction if it exists
        if task_instruction:
            # Task instructions need ": " separator
            separator = ": " if not task_instruction.endswith(": ") else ""
            query_to_embed = task_instruction + separator + query
        elif query_prefix:
            # Simple prefix (e.g., "Retrieval-document: ")
            query_to_embed = query_prefix + query
        else:
            query_to_embed = query

        # Generate embedding
        # Use convert_to_tensor for GPU to avoid CPU<->GPU transfers
        use_tensor = self._is_gpu_device()
        embedding = self.model.encode(
            [query_to_embed],
            show_progress_bar=False,
            convert_to_tensor=use_tensor,
            device=self.device if use_tensor else None,
        )[0]

        # Convert back to numpy if tensor
        # Note: bf16 tensors must be converted to float32 first (numpy doesn't support bf16)
        if torch and torch.is_tensor(embedding):
            embedding = embedding.cpu().float().numpy()

        # Add to cache
        self._add_to_query_cache(cache_key, embedding)

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

    def _get_model_cache_path(self) -> Optional[Path]:
        """Get the HuggingFace cache directory path for this model.

        Returns the models--{org}--{name} directory, or None if cache_dir not set.
        Does NOT check if the path exists.
        """
        if not self.cache_dir:
            return None

        cache_root = Path(self.cache_dir)

        # Hugging Face cache structure: cache_dir/models--{org}--{model_name}/
        # Handle both 'org/model_name' and 'model_name' formats
        parts = self.model_name.split("/")
        if len(parts) == 2:
            org, name = parts
            expected_model_dir_name = f"models--{org}--{name}"
        else:
            name = parts[0]
            expected_model_dir_name = f"models--{name}"

        return cache_root / expected_model_dir_name

    def _get_default_hf_cache_path(self) -> Optional[Path]:
        """Get the default HuggingFace cache directory path for this model.

        This is used as a fallback when trust_remote_code models ignore cache_folder.

        Returns the models--{org}--{name} directory in default HF cache.
        """
        default_hf_cache = Path.home() / ".cache" / "huggingface" / "hub"

        # Hugging Face cache structure: cache_dir/models--{org}--{model_name}/
        parts = self.model_name.split("/")
        if len(parts) == 2:
            org, name = parts
            expected_model_dir_name = f"models--{org}--{name}"
        else:
            name = parts[0]
            expected_model_dir_name = f"models--{name}"

        return default_hf_cache / expected_model_dir_name

    def _check_cache_at_location(self, cache_path: Path) -> tuple[bool, str]:
        """Check if valid model cache exists at a specific location.

        Args:
            cache_path: Path to models--{org}--{name} directory to validate

        Returns:
            (is_valid, reason) - True if cache is complete and valid, False with reason if not
        """
        import json

        # Check cache directory structure exists
        if not cache_path or not cache_path.exists():
            return False, "Cache directory not found"

        try:
            # Find snapshot directories (skip empty ones from interrupted downloads)
            all_snapshots = list(cache_path.glob("snapshots/*"))
            if not all_snapshots:
                return False, "No snapshots found in cache"

            # Filter out empty snapshots (common with interrupted downloads)
            valid_snapshots = [s for s in all_snapshots if list(s.iterdir())]
            if not valid_snapshots:
                return False, "All snapshots are empty (interrupted downloads)"

            # Use latest valid snapshot (sorted by modification time)
            snapshot_dir = max(valid_snapshots, key=lambda p: p.stat().st_mtime)

            # CRITICAL: Validate config.json exists and is valid
            config_path = snapshot_dir / "config.json"
            if not config_path.exists():
                return False, "Missing config.json (corrupted download)"

            # Validate config.json is valid JSON with required keys
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Check for model_type or architectures (required by transformers)
                    if "model_type" not in config and "architectures" not in config:
                        return (
                            False,
                            "Invalid config.json (missing model_type and architectures)",
                        )
            except json.JSONDecodeError as e:
                return False, f"Corrupted config.json (invalid JSON): {e}"
            except Exception as e:
                return False, f"Cannot read config.json: {e}"

            # Validate model weights exist (single-file or sharded formats)
            has_safetensors = (snapshot_dir / "model.safetensors").exists()
            has_pytorch = (snapshot_dir / "pytorch_model.bin").exists()
            has_pytorch_index = (snapshot_dir / "pytorch_model.bin.index.json").exists()
            has_safetensors_index = (
                snapshot_dir / "model.safetensors.index.json"
            ).exists()

            # For sharded models, validate that actual shard files exist
            if has_safetensors_index or has_pytorch_index:
                # Parse index.json to find shard files
                index_file = snapshot_dir / (
                    "model.safetensors.index.json"
                    if has_safetensors_index
                    else "pytorch_model.bin.index.json"
                )
                try:
                    with open(index_file, "r", encoding="utf-8") as f:
                        index_data = json.load(f)
                        shard_files = set(index_data.get("weight_map", {}).values())

                        if not shard_files:
                            return (
                                False,
                                f"Invalid index file (no shards listed): {index_file.name}",
                            )

                        # Check that all shard files exist (either as actual files or symlinks)
                        missing_shards = []
                        incomplete_shards = []

                        for shard in shard_files:
                            shard_path = snapshot_dir / shard
                            if not shard_path.exists():
                                # Check if it's a symlink pointing to a blob
                                if shard_path.is_symlink():
                                    target = shard_path.resolve()
                                    if not target.exists():
                                        # Check if there's an incomplete blob
                                        incomplete_blob = (
                                            target.parent / f"{target.name}.incomplete"
                                        )
                                        if incomplete_blob.exists():
                                            size_mb = incomplete_blob.stat().st_size / (
                                                1024**2
                                            )
                                            incomplete_shards.append(
                                                f"{shard} ({size_mb:.1f}MB incomplete)"
                                            )
                                        else:
                                            missing_shards.append(
                                                f"{shard} -> {target.name} (broken symlink)"
                                            )
                                else:
                                    missing_shards.append(shard)

                        if incomplete_shards:
                            return (
                                False,
                                f"Incomplete downloads detected: {', '.join(incomplete_shards)}. Run cleanup to remove partial downloads.",
                            )

                        if missing_shards:
                            return (
                                False,
                                f"Missing shard files: {', '.join(missing_shards)}",
                            )

                except json.JSONDecodeError as e:
                    return False, f"Corrupted index file {index_file.name}: {e}"
                except Exception as e:
                    return False, f"Error validating shards: {e}"

            elif not (has_safetensors or has_pytorch):
                return False, "Missing model weights (no .safetensors or .bin files)"

            # Validate tokenizer files exist (at least one)
            tokenizer_files = [
                "tokenizer.json",
                "tokenizer_config.json",
                "vocab.txt",
                "sentencepiece.bpe.model",
                "tokenizer.model",
            ]
            has_tokenizer = any((snapshot_dir / f).exists() for f in tokenizer_files)
            if not has_tokenizer:
                return False, "Missing tokenizer files"

            # All checks passed
            return True, f"Valid cache at {snapshot_dir}"

        except Exception as e:
            self._logger.debug(f"Error during cache validation: {e}")
            return False, f"Validation error: {str(e)}"

    def _validate_model_cache(self) -> tuple[bool, str]:
        """Validate cached model integrity with fallback to default HuggingFace cache.

        Checks both custom cache location and default HuggingFace cache for models
        with trust_remote_code=True (which may ignore cache_folder parameter).

        Returns:
            (is_valid, reason) - True if cache is complete and valid in either location
        """
        # First, check custom cache location
        custom_cache_path = self._get_model_cache_path()
        custom_valid, custom_reason = self._check_cache_at_location(custom_cache_path)

        if custom_valid:
            return True, custom_reason

        # Custom cache invalid - check if this is a trust_remote_code model
        model_config = self._get_model_config()
        requires_trust_remote_code = model_config.get("trust_remote_code", False)

        if requires_trust_remote_code:
            # Fallback: Check default HuggingFace cache location
            # Some models with trust_remote_code ignore cache_folder and use default location
            default_cache_path = self._get_default_hf_cache_path()
            default_valid, default_reason = self._check_cache_at_location(
                default_cache_path
            )

            if default_valid:
                # Cache found in default location instead of custom location
                self._logger.warning(
                    f"[CACHE LOCATION MISMATCH] Model weights found in default HuggingFace cache instead of custom cache.\n"
                    f"  Expected: {custom_cache_path}\n"
                    f"  Found: {default_cache_path}\n"
                    f"  Reason: Models with trust_remote_code=True may ignore cache_folder parameter.\n"
                    f"  Impact: Model will load successfully but from default cache location."
                )
                return True, f"Valid (found in default HF cache): {default_reason}"

        # Cache invalid in both locations
        return False, custom_reason

    def _check_incomplete_downloads(self) -> tuple[bool, str]:
        """Check if there are incomplete downloads that could cause validation failures.

        Scans the blobs directory for .incomplete files from interrupted HuggingFace downloads.

        Returns:
            (has_incomplete, message) - True if incomplete files exist with descriptive message
        """
        try:
            model_cache_path = self._get_model_cache_path()
            if not model_cache_path or not model_cache_path.exists():
                return False, "No cache directory"

            blobs_dir = model_cache_path / "blobs"
            if not blobs_dir.exists():
                return False, "No blobs directory"

            incomplete_files = list(blobs_dir.glob("*.incomplete"))
            if not incomplete_files:
                return False, "No incomplete downloads"

            # Calculate total size of incomplete files
            total_size = sum(f.stat().st_size for f in incomplete_files)
            size_mb = total_size / (1024**2)

            message = (
                f"Found {len(incomplete_files)} incomplete download(s) ({size_mb:.1f} MB total). "
                f"These may be from interrupted downloads. "
                f"Files: {[f.name[:16] + '...' for f in incomplete_files[:3]]}"
            )

            return True, message

        except Exception as e:
            self._logger.debug(f"Error checking incomplete downloads: {e}")
            return False, f"Error: {str(e)}"

    def _cleanup_incomplete_downloads(self) -> tuple[int, list[str]]:
        """Detect and clean up incomplete downloads in the blobs directory.

        Removes .incomplete files that were created by interrupted HuggingFace downloads.
        This allows subsequent downloads to start fresh instead of failing validation.

        Returns:
            (count, file_list) - Number of incomplete files removed and their names
        """
        try:
            model_cache_path = self._get_model_cache_path()
            if not model_cache_path or not model_cache_path.exists():
                return 0, []

            blobs_dir = model_cache_path / "blobs"
            if not blobs_dir.exists():
                return 0, []

            incomplete_files = []
            removed_count = 0

            # Find all .incomplete files
            for incomplete_file in blobs_dir.glob("*.incomplete"):
                size_mb = incomplete_file.stat().st_size / (1024**2)
                incomplete_files.append(
                    f"{incomplete_file.name[:16]}... ({size_mb:.1f}MB)"
                )

                try:
                    incomplete_file.unlink()
                    removed_count += 1
                    self._logger.info(
                        f"Removed incomplete download: {incomplete_file.name} ({size_mb:.1f}MB)"
                    )
                except Exception as e:
                    self._logger.warning(
                        f"Failed to remove {incomplete_file.name}: {e}"
                    )

            if removed_count > 0:
                sum(f.stat().st_size for f in blobs_dir.glob("*.incomplete")) / (
                    1024**2
                )
                self._logger.info(
                    f"Cleanup complete: Removed {removed_count} incomplete file(s)"
                )

            return removed_count, incomplete_files

        except Exception as e:
            self._logger.warning(f"Error during incomplete file cleanup: {e}")
            return 0, []

    def _is_model_cached(self) -> bool:
        """Check if model cache exists and is valid.

        Uses comprehensive validation to prevent loading corrupted caches.
        """
        is_valid, _ = self._validate_model_cache()
        return is_valid

    def _find_local_model_dir(self) -> Optional[Path]:
        """Locate the cached model directory if available.
        Returns the path to the snapshot directory containing the model files.
        Only returns path if cache is valid (uses _validate_model_cache).

        Checks both custom cache and default HuggingFace cache for models with
        trust_remote_code=True.
        """
        # Use validation to ensure cache is complete
        is_valid, reason = self._validate_model_cache()
        if not is_valid:
            self._logger.debug(f"Cache not valid: {reason}")
            return None

        try:
            # Helper to get latest snapshot from a cache path if validation passes
            def get_latest_snapshot_if_valid(cache_path: Path) -> Optional[Path]:
                # Check if this specific cache location is valid
                valid, _ = self._check_cache_at_location(cache_path)
                if not valid:
                    return None

                if cache_path and cache_path.exists():
                    snapshots = list(cache_path.glob("snapshots/*"))
                    # Filter out empty snapshots
                    valid_snapshots = [s for s in snapshots if list(s.iterdir())]
                    if valid_snapshots:
                        return max(valid_snapshots, key=lambda p: p.stat().st_mtime)
                return None

            # First try custom cache location
            model_cache_path = self._get_model_cache_path()
            custom_snapshot = get_latest_snapshot_if_valid(model_cache_path)
            if custom_snapshot:
                return custom_snapshot

            # Fallback: Check default HuggingFace cache for trust_remote_code models
            model_config = self._get_model_config()
            if model_config.get("trust_remote_code", False):
                default_cache_path = self._get_default_hf_cache_path()
                default_snapshot = get_latest_snapshot_if_valid(default_cache_path)
                if default_snapshot:
                    return default_snapshot

        except Exception as e:
            self._logger.debug(f"Error during _find_local_model_dir: {e}")
            return None
        return None

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
