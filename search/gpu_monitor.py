"""GPU memory monitoring utilities for optimal batch sizing.

Extracted from hybrid_searcher.py.
This module provides GPU memory monitoring functionality for determining
optimal batch sizes and checking GPU availability.
"""

import gc
import logging


try:
    import torch
except ImportError:
    torch = None


class GPUMemoryMonitor:
    """Monitor GPU memory usage for optimal batch sizing."""

    def __init__(self) -> None:
        """Initialize GPU monitor."""
        self._logger = logging.getLogger(__name__)

    def get_available_memory(self) -> dict[str, int]:
        """Get available memory in bytes."""
        memory_info = {"gpu_available": 0, "gpu_total": 0, "gpu_utilization": 0.0}

        if torch and torch.cuda.is_available():
            try:
                device = torch.cuda.current_device()
                gpu_memory = torch.cuda.mem_get_info(device)
                memory_info["gpu_available"] = gpu_memory[0]
                memory_info["gpu_total"] = gpu_memory[1]
                memory_info["gpu_utilization"] = 1.0 - (gpu_memory[0] / gpu_memory[1])
            except Exception as e:  # noqa: BLE001 - resilience: GPU query optional, default zeroed memory_info returned
                self._logger.warning(f"Failed to get GPU memory info: {e}")

        # pyrefly: ignore [bad-return]
        return memory_info

    def can_use_gpu(self, required_memory: int = 1024 * 1024 * 1024) -> bool:
        """Check if GPU can be used for operations."""
        if not torch or not torch.cuda.is_available():
            return False

        memory_info = self.get_available_memory()
        return memory_info["gpu_available"] > required_memory

    def estimate_batch_memory(self, batch_size: int, embedding_dim: int = 768) -> int:
        """Estimate memory usage for a batch."""
        # float32 = 4 bytes, plus overhead
        return batch_size * embedding_dim * 4 * 2  # 2x safety margin


def release_gpu_memory(*, synchronize: bool = True) -> None:
    """Release GPU memory and run garbage collection.

    Calls ``gc.collect()`` unconditionally, then empties the PyTorch CUDA
    cache and (when *synchronize* is True) blocks until all CUDA kernels
    complete.  No-op safe when PyTorch / CUDA is absent.
    """
    gc.collect()
    if torch and torch.cuda.is_available():
        torch.cuda.empty_cache()
        if synchronize:
            torch.cuda.synchronize()
