"""GPU memory monitoring utilities for optimal batch sizing.

Extracted from hybrid_searcher.py (Phase 3.1 refactoring).
This module provides GPU memory monitoring functionality for determining
optimal batch sizes and checking GPU availability.
"""

import logging
from typing import Dict

try:
    import torch
except ImportError:
    torch = None


class GPUMemoryMonitor:
    """Monitor GPU memory usage for optimal batch sizing."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    def get_available_memory(self) -> Dict[str, int]:
        """Get available memory in bytes."""
        memory_info = {"gpu_available": 0, "gpu_total": 0, "gpu_utilization": 0.0}

        if torch and torch.cuda.is_available():
            try:
                device = torch.cuda.current_device()
                gpu_memory = torch.cuda.mem_get_info(device)
                memory_info["gpu_available"] = gpu_memory[0]
                memory_info["gpu_total"] = gpu_memory[1]
                memory_info["gpu_utilization"] = 1.0 - (gpu_memory[0] / gpu_memory[1])
            except Exception as e:
                self._logger.warning(f"Failed to get GPU memory info: {e}")

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
