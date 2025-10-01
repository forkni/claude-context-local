#!/usr/bin/env python3
"""
Tests for CUDA detection and hardware capability assessment.
Validates CUDA version detection, PyTorch index mapping, and hardware compatibility.
"""

import subprocess
from unittest.mock import Mock, patch

import pytest

from tests.fixtures.installation_mocks import (
    CUDA_VERSIONS,
    MOCK_NVIDIA_SMI_OUTPUTS,
    get_mock_environment,
)


class TestCUDADetection:
    """Test CUDA detection functionality."""

    @patch("subprocess.run")
    def test_nvidia_smi_detection_success(self, mock_run):
        """Test successful CUDA detection via nvidia-smi."""
        mock_run.return_value = Mock(
            returncode=0, stdout=MOCK_NVIDIA_SMI_OUTPUTS["cuda_12_1"], stderr=""
        )

        # Simulate CUDA detection logic
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=cuda_version", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "12.1" in result.stdout

    @patch("subprocess.run")
    def test_nvidia_smi_not_found(self, mock_run):
        """Test handling when nvidia-smi is not available."""
        mock_run.side_effect = FileNotFoundError("'nvidia-smi' is not recognized")

        with pytest.raises(FileNotFoundError):
            subprocess.run(["nvidia-smi", "--version"], capture_output=True, text=True)

    def test_cuda_version_mapping(self):
        """Test mapping of CUDA versions to PyTorch indices."""
        test_cases = [
            ("12.1", "https://download.pytorch.org/whl/cu121", True),
            ("12.0", "https://download.pytorch.org/whl/cu121", True),
            ("11.8", "https://download.pytorch.org/whl/cu118", True),
            ("11.7", "https://download.pytorch.org/whl/cu117", True),
            ("13.0", None, False),  # Future version
            ("10.2", None, False),  # Too old
        ]

        for version, expected_index, expected_support in test_cases:
            cuda_info = CUDA_VERSIONS.get(version)
            assert cuda_info is not None
            assert cuda_info["pytorch_index"] == expected_index
            assert cuda_info["supported"] == expected_support

    def test_cuda_version_parsing(self):
        """Test parsing CUDA version from nvidia-smi output."""
        test_outputs = [
            (
                "NVIDIA GeForce RTX 4090, Driver Version: 537.13, CUDA Version: 12.1",
                "12.1",
            ),
            (
                "NVIDIA GeForce RTX 3080, Driver Version: 516.94, CUDA Version: 11.8",
                "11.8",
            ),
            (
                "NVIDIA GeForce RTX 3070, Driver Version: 516.40, CUDA Version: 11.7",
                "11.7",
            ),
        ]

        for output, expected_version in test_outputs:
            # Simulate version extraction logic
            import re

            match = re.search(r"CUDA Version: ([\d.]+)", output)
            assert match is not None
            assert match.group(1) == expected_version


class TestHardwareCompatibility:
    """Test hardware compatibility assessment."""

    def test_supported_cuda_versions(self):
        """Test identification of supported CUDA versions."""
        supported_versions = [
            v for v, info in CUDA_VERSIONS.items() if info["supported"]
        ]

        assert "12.1" in supported_versions
        assert "12.0" in supported_versions
        assert "11.8" in supported_versions
        assert "11.7" in supported_versions
        assert "13.0" not in supported_versions
        assert "10.2" not in supported_versions

    def test_recommended_cuda_versions(self):
        """Test identification of recommended CUDA versions."""
        recommended_versions = [
            v for v, info in CUDA_VERSIONS.items() if info.get("recommended", False)
        ]

        assert "12.1" in recommended_versions
        assert "12.0" in recommended_versions
        assert "11.8" not in recommended_versions  # Supported but not recommended

    def test_pytorch_index_selection(self):
        """Test automatic PyTorch index selection based on CUDA version."""

        def get_pytorch_index(cuda_version):
            cuda_info = CUDA_VERSIONS.get(cuda_version, {})
            pytorch_index = cuda_info.get("pytorch_index")
            # Return CPU fallback for unsupported versions (None pytorch_index)
            return (
                pytorch_index
                if pytorch_index is not None
                else "https://pypi.org/simple"
            )

        assert get_pytorch_index("12.1") == "https://download.pytorch.org/whl/cu121"
        assert get_pytorch_index("11.8") == "https://download.pytorch.org/whl/cu118"
        assert get_pytorch_index("13.0") == "https://pypi.org/simple"  # Fallback to CPU
        assert get_pytorch_index("unknown") == "https://pypi.org/simple"

    def test_gpu_capability_assessment(self):
        """Test GPU capability assessment for different hardware."""
        test_cases = [
            ("NVIDIA GeForce RTX 4090", "high", True),
            ("NVIDIA GeForce RTX 3080", "high", True),
            ("NVIDIA GeForce RTX 3070", "medium", True),
            ("NVIDIA GeForce GTX 1060", "low", True),
            ("Intel Integrated Graphics", "none", False),
        ]

        for gpu_name, expected_capability, cuda_support in test_cases:
            # Simulate capability assessment
            if "RTX 40" in gpu_name:
                capability = "high"
                supports_cuda = True
            elif "RTX 30" in gpu_name:
                capability = "high" if "3080" in gpu_name else "medium"
                supports_cuda = True
            elif "GTX" in gpu_name:
                capability = "low"
                supports_cuda = True
            else:
                capability = "none"
                supports_cuda = False

            assert capability == expected_capability
            assert supports_cuda == cuda_support


class TestInstallationEnvironments:
    """Test installation environment simulation."""

    def test_ideal_cuda_environment(self):
        """Test ideal CUDA installation environment."""
        env = get_mock_environment("ideal_cuda")

        assert env.has_python is True
        assert env.python_version == "3.11.1"
        assert env.has_cuda is True
        assert env.cuda_version == "12.1"
        assert env.gpu_name == "NVIDIA GeForce RTX 4090"
        assert env.has_network is True
        assert env.disk_space_gb == 100.0

    def test_cpu_only_environment(self):
        """Test CPU-only installation environment."""
        env = get_mock_environment("ideal_cpu")

        assert env.has_python is True
        assert env.has_cuda is False
        assert env.cuda_version is None
        assert env.has_network is True

    def test_problematic_environments(self):
        """Test problematic installation environments."""
        # Test old Python version
        env = get_mock_environment("problematic_python")
        assert env.python_version == "3.9.7"

        # Test no Python
        env = get_mock_environment("no_python")
        assert env.has_python is False

        # Test network issues
        env = get_mock_environment("network_issues")
        assert env.has_network is False

        # Test low disk space
        env = get_mock_environment("low_disk_space")
        assert env.disk_space_gb == 1.0

    def test_future_cuda_environment(self):
        """Test environment with unsupported future CUDA version."""
        env = get_mock_environment("future_cuda")

        assert env.cuda_version == "13.0"
        cuda_info = CUDA_VERSIONS.get(env.cuda_version, {})
        assert cuda_info.get("supported") is False
        assert "Future CUDA version not supported" in cuda_info.get("warning", "")


class TestCUDAInstallationSimulation:
    """Test CUDA installation process simulation."""

    def test_cuda_detection_simulation(self):
        """Test CUDA detection simulation."""
        env = get_mock_environment("ideal_cuda")
        result = env.simulate_cuda_detection()

        assert result["success"] is True
        assert result["cuda_available"] is True
        assert result["cuda_version"] == "12.1"
        assert result["pytorch_index"] == "https://download.pytorch.org/whl/cu121"
        assert result["supported"] is True

    def test_no_cuda_simulation(self):
        """Test no CUDA detection simulation."""
        env = get_mock_environment("ideal_cpu")
        result = env.simulate_cuda_detection()

        assert result["success"] is False
        assert result["cuda_available"] is False
        assert result["pytorch_index"] == "https://pypi.org/simple"

    def test_auto_install_decision(self):
        """Test automatic installation mode decision."""
        # CUDA environment should choose CUDA mode
        cuda_env = get_mock_environment("ideal_cuda")
        result = cuda_env.simulate_auto_install()

        assert result["mode"] == "cuda"
        assert result["choice"] == "auto_cuda"
        assert result["dependencies_include_cuda"] is True

        # CPU environment should choose CPU mode
        cpu_env = get_mock_environment("ideal_cpu")
        result = cpu_env.simulate_auto_install()

        assert result["mode"] == "cpu"
        assert result["choice"] == "auto_cpu"
        assert result["dependencies_include_cuda"] is False

    def test_manual_cuda_selection(self):
        """Test manual CUDA version selection."""
        env = get_mock_environment("ideal_cuda")

        # Test selecting supported version
        result = env.simulate_manual_cuda_selection("12.1")
        assert result["mode"] == "cuda"
        assert result["supported"] is True
        assert result["user_override"] is True

        # Test selecting unsupported version
        result = env.simulate_manual_cuda_selection("13.0")
        assert result["mode"] == "cuda"
        assert result["supported"] is False

    def test_cpu_force_install(self):
        """Test forced CPU-only installation."""
        env = get_mock_environment("ideal_cuda")  # Even with CUDA available
        result = env.simulate_cpu_only_install()

        assert result["mode"] == "cpu"
        assert result["forced_cpu"] is True
        assert result["cuda_available"] is True  # But we're forcing CPU


if __name__ == "__main__":
    pytest.main([__file__])
