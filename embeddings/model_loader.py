"""Model loading and device management for embedding models.

This module handles loading SentenceTransformer models with:
- Automatic cache corruption recovery
- Device resolution (CUDA/MPS/CPU)
- Precision selection (fp16/bf16/fp32)
- VRAM usage tracking
"""

import logging
import os
import shutil
from typing import Any, Callable, Dict, Optional

try:
    import torch
except ImportError:
    torch = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from embeddings.model_cache import ModelCacheManager


# Helper function to access config via ServiceLocator (avoids circular imports)
def _get_config_via_service_locator():
    """Get SearchConfig via ServiceLocator to avoid circular dependencies."""
    from mcp_server.services import ServiceLocator

    return ServiceLocator.instance().get_config()


class ModelLoader:
    """Handles loading and device management for embedding models.

    Manages model loading with automatic recovery from cache corruption,
    device resolution, and precision selection for optimal performance.

    Example:
        >>> cache_manager = ModelCacheManager(...)
        >>> loader = ModelLoader(
        ...     model_name="BAAI/bge-m3",
        ...     cache_dir="/path/to/cache",
        ...     device="auto",
        ...     cache_manager=cache_manager,
        ...     model_config_getter=lambda: {...}
        ... )
        >>> model, device = loader.load()
    """

    def __init__(
        self,
        model_name: str,
        cache_dir: str,
        device: str,
        cache_manager: ModelCacheManager,
        model_config_getter: Callable[[], Dict[str, Any]],
    ):
        """Initialize model loader.

        Args:
            model_name: Name of the model (e.g., "BAAI/bge-m3")
            cache_dir: Path to cache directory
            device: Target device ("auto", "cuda", "mps", or "cpu")
            cache_manager: ModelCacheManager instance for cache operations
            model_config_getter: Callback function that returns model config dict
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.device = device
        self._cache_manager = cache_manager
        self._get_model_config = model_config_getter
        self._logger = logging.getLogger(__name__)
        self._model_vram_usage: Dict[str, float] = {}

    def log_gpu_memory(self, stage: str):
        """Log GPU memory usage at specific loading stages.

        Args:
            stage: Description of the loading stage (e.g., "BEFORE_LOAD", "AFTER_LOAD")
        """
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

    def get_torch_dtype(self):
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

    def resolve_device(self, requested: Optional[str]) -> str:
        """Resolve target device string.

        Args:
            requested: Requested device ("auto", "cuda", "mps", "cpu", or None)

        Returns:
            Resolved device string ("cuda", "mps", or "cpu")

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
            except (AttributeError, RuntimeError):
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
            except RuntimeError:
                return "cpu"
        # Default fallback
        return "cpu"

    def load(self) -> tuple[Any, str]:
        """Load model with automatic cache corruption recovery and fallback.

        Returns:
            Tuple of (loaded_model, resolved_device)

        Raises:
            ImportError: If sentence-transformers not installed
            ValueError: If model not found on HuggingFace Hub
            RuntimeError: If model loading fails after all recovery attempts
        """
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers not found. Install with: "
                "pip install sentence-transformers>=5.0.0"
            )

        self._logger.info(f"Loading model: {self.model_name}")

        # Step 1: Validate cache integrity (comprehensive checks)
        cache_valid, cache_reason = self._cache_manager.validate_cache()
        cache_path_obj = self._cache_manager.get_model_cache_path()

        # Check if cache directory exists but is corrupted
        if cache_path_obj and cache_path_obj.exists() and not cache_valid:
            # Step 1a: Check if corruption is due to incomplete downloads
            has_incomplete, incomplete_msg = (
                self._cache_manager.check_incomplete_downloads()
            )

            if has_incomplete and "Incomplete downloads detected" in cache_reason:
                # Corruption is due to incomplete downloads - try cleanup first
                self._logger.warning(
                    f"[INCOMPLETE DOWNLOADS] {incomplete_msg}\n"
                    f"[AUTO-CLEANUP] Removing incomplete files and retrying..."
                )

                # Clean up incomplete downloads
                removed_count, removed_files = (
                    self._cache_manager.cleanup_incomplete_downloads()
                )

                if removed_count > 0:
                    self._logger.info(
                        f"[CLEANUP SUCCESS] Removed {removed_count} incomplete file(s)"
                    )

                    # Re-validate cache after cleanup
                    cache_valid_retry, cache_reason_retry = (
                        self._cache_manager.validate_cache()
                    )

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
                local_model_dir = self._cache_manager.find_local_model_dir()
                if local_model_dir:
                    self._logger.info(
                        f"Loading model from validated cache: {local_model_dir}"
                    )
            except Exception as _e:
                self._logger.debug(f"Offline mode detection skipped: {_e}")

        # Step 4: Load model with automatic fallback
        resolved_device = self.resolve_device(self.device)
        self.log_gpu_memory("BEFORE_LOAD")

        # Track VRAM before loading model
        vram_before = 0
        if torch and torch.cuda.is_available():
            vram_before = torch.cuda.memory_allocated()

        # Determine precision (fp16/bf16) for GPU inference
        torch_dtype = self.get_torch_dtype()

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

            model = SentenceTransformer(model_source, **constructor_kwargs)

            # Build detailed info string
            precision_info = f" ({torch_dtype})" if torch_dtype else " (fp32 default)"

            self._logger.info(
                f"Model loaded successfully on device: {model.device} [backend=pytorch]{precision_info}"
            )
            self.log_gpu_memory("AFTER_LOAD")

            # Track VRAM usage for this model
            if torch and torch.cuda.is_available():
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
                self._cache_manager.ensure_split_cache_symlink()

            return model, resolved_device

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
                    model_config = self._get_model_config()
                    truncate_dim = model_config.get("truncate_dim")
                    if truncate_dim is not None:
                        fallback_kwargs["truncate_dim"] = truncate_dim

                    # Preserve model_kwargs (e.g., torch_dtype)
                    if model_kwargs_dict:
                        fallback_kwargs["model_kwargs"] = model_kwargs_dict

                    model = SentenceTransformer(
                        self.model_name,  # Use model name, not local path
                        **fallback_kwargs,
                    )
                    self._logger.info(
                        "[FALLBACK SUCCESS] Downloaded fresh model from HuggingFace"
                    )
                    self.log_gpu_memory("AFTER_FALLBACK_LOAD")

                    # Track VRAM usage for this model (fallback path)
                    if torch and torch.cuda.is_available():
                        vram_after = torch.cuda.memory_allocated()
                        vram_used_mb = (vram_after - vram_before) / (1024 * 1024)
                        # Clamp to 0 minimum to handle multi-model memory accounting
                        vram_used_mb = max(0, vram_used_mb)
                        self._model_vram_usage[self.model_name] = round(vram_used_mb, 1)
                        self._logger.info(
                            f"Model VRAM usage: {vram_used_mb:.1f} MB ({self.model_name})"
                        )

                    return model, resolved_device

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

    @property
    def model_vram_usage(self) -> Dict[str, float]:
        """Get VRAM usage tracking dictionary.

        Returns:
            Dictionary mapping model names to VRAM usage in MB
        """
        return self._model_vram_usage
