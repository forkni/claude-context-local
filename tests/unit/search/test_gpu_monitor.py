"""Tests for GPU memory monitoring functionality.

Extracted from test_hybrid_search.py (Phase 3.1 refactoring).
"""

from unittest.mock import patch

from search.gpu_monitor import GPUMemoryMonitor


class TestGPUMemoryMonitor:
    """Test GPU memory monitoring functionality."""

    def test_memory_info_without_gpu(self):
        """Test memory info when GPU is not available."""
        with patch("search.gpu_monitor.torch", None):
            monitor = GPUMemoryMonitor()
            info = monitor.get_available_memory()

            assert info["gpu_available"] == 0
            assert info["gpu_total"] == 0
            assert info["gpu_utilization"] == 0.0

    @patch("search.gpu_monitor.torch")
    def test_memory_info_with_gpu(self, mock_torch):
        """Test memory info when GPU is available."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.current_device.return_value = 0
        mock_torch.cuda.mem_get_info.return_value = (
            4 * 1024**3,
            8 * 1024**3,
        )  # 4GB free, 8GB total

        monitor = GPUMemoryMonitor()
        info = monitor.get_available_memory()

        assert info["gpu_available"] == 4 * 1024**3
        assert info["gpu_total"] == 8 * 1024**3
        assert info["gpu_utilization"] == 0.5  # 50% utilized

    @patch("search.gpu_monitor.torch")
    def test_can_use_gpu(self, mock_torch):
        """Test GPU availability checking."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            2 * 1024**3,
            8 * 1024**3,
        )  # 2GB available

        monitor = GPUMemoryMonitor()

        assert monitor.can_use_gpu(1024**3)  # 1GB requirement - should pass
        assert not monitor.can_use_gpu(3 * 1024**3)  # 3GB requirement - should fail

    def test_batch_memory_estimation(self):
        """Test batch memory estimation."""
        monitor = GPUMemoryMonitor()

        # Test memory estimation
        memory = monitor.estimate_batch_memory(100, 768)
        expected = 100 * 768 * 4 * 2  # batch_size * dim * float32 * safety_margin
        assert memory == expected
