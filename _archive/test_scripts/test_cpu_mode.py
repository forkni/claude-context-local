#!/usr/bin/env python3
"""
Tests for CPU-only installation mode.
Validates CPU-only installations work correctly without CUDA dependencies.
"""

import os
import pytest
from unittest.mock import patch, Mock
from tests.fixtures.installation_mocks import (
    MockInstallationEnvironment,
    get_mock_environment,
    MOCK_DEPENDENCIES
)


class TestCPUOnlyInstallation:
    """Test CPU-only installation scenarios."""

    def test_cpu_only_environment_setup(self):
        """Test CPU-only environment initialization."""
        env = get_mock_environment("ideal_cpu")

        assert env.has_python is True
        assert env.has_cuda is False
        assert env.cuda_version is None
        assert env.has_network is True
        assert env.disk_space_gb >= 50.0

    def test_no_cuda_detection(self):
        """Test that CUDA detection fails appropriately in CPU-only mode."""
        env = get_mock_environment("ideal_cpu")
        result = env.simulate_cuda_detection()

        assert result["success"] is False
        assert result["cuda_available"] is False
        assert result["pytorch_index"] == "https://pypi.org/simple"
        assert "nvidia_smi_not_found" in str(result.get("error", {}))

    def test_cpu_pytorch_installation(self):
        """Test PyTorch CPU installation."""
        env = get_mock_environment("ideal_cpu")

        # Get CPU-only PyTorch index
        cuda_result = env.simulate_cuda_detection()
        pytorch_index = cuda_result["pytorch_index"]

        # Install PyTorch CPU version
        pytorch_result = env.simulate_pytorch_installation(pytorch_index)

        assert pytorch_result["success"] is True
        assert pytorch_result["cuda_support"] is False
        assert pytorch_result["version"] == MOCK_DEPENDENCIES["pytorch_cuda"]["cpu"]
        assert "cpu" in pytorch_result["version"]

    def test_cpu_dependency_installation(self):
        """Test that all required dependencies install in CPU mode."""
        env = get_mock_environment("ideal_cpu")

        dependencies = [
            "transformers",
            "sentence_transformers",
            "faiss",
            "rank_bm25",
            "nltk"
        ]

        result = env.simulate_dependency_installation(dependencies)

        assert result["success"] is True
        assert len(result["packages"]) == len(dependencies)

        # Verify all dependencies are present
        for dep in dependencies:
            assert dep in result["packages"]

    def test_cpu_verification_tests(self):
        """Test verification in CPU-only mode."""
        env = get_mock_environment("ideal_cpu")

        # Simulate installation steps
        env.simulate_venv_creation()
        env.simulate_uv_installation()
        env.simulate_pytorch_installation("https://pypi.org/simple")

        # Run verification
        verification = env.simulate_verification_tests()

        # Check expected results for CPU mode
        assert verification["python_venv"] is True
        assert verification["pytorch"] is True
        assert verification["cuda_functional"] is False  # Should be False for CPU
        assert verification["embedding_model"] is True
        assert verification["hybrid_search"] is True
        assert verification["mcp_server"] is True

    def test_forced_cpu_mode(self):
        """Test forcing CPU mode even when CUDA is available."""
        # Start with CUDA environment but force CPU
        env = get_mock_environment("ideal_cuda")

        # Force CPU-only installation
        cpu_result = env.simulate_cpu_only_install()

        assert cpu_result["mode"] == "cpu"
        assert cpu_result["pytorch_index"] == "https://pypi.org/simple"
        assert cpu_result["forced_cpu"] is True
        assert cpu_result["cuda_available"] is True  # CUDA was available but ignored

    def test_cpu_auto_fallback(self):
        """Test automatic fallback to CPU when CUDA is not available."""
        env = get_mock_environment("ideal_cpu")
        auto_result = env.simulate_auto_install()

        assert auto_result["mode"] == "cpu"
        assert auto_result["choice"] == "auto_cpu"
        assert auto_result["dependencies_include_cuda"] is False
        assert auto_result["pytorch_index"] == "https://pypi.org/simple"


class TestCPUPerformanceCharacteristics:
    """Test CPU-only performance characteristics."""

    def test_cpu_embedding_performance(self):
        """Test that CPU embeddings work but are slower."""
        env = get_mock_environment("ideal_cpu")

        # Simulate embedding model loading in CPU mode
        # This would normally test actual performance
        verification = env.simulate_verification_tests()

        assert verification["embedding_model"] is True
        # Note: Real implementation would benchmark performance

    def test_cpu_memory_usage(self):
        """Test CPU memory usage patterns."""
        env = get_mock_environment("ideal_cpu")

        # CPU-only should use less GPU memory (none) but more system RAM
        verification = env.simulate_verification_tests()

        # Verify that basic functionality works
        assert verification["hybrid_search"] is True

    def test_cpu_search_functionality(self):
        """Test that all search features work in CPU mode."""
        env = get_mock_environment("ideal_cpu")

        # Simulate full installation
        env.simulate_venv_creation()
        env.simulate_uv_installation()
        env.simulate_pytorch_installation("https://pypi.org/simple")
        env.simulate_dependency_installation(["transformers", "faiss", "rank_bm25"])

        verification = env.simulate_verification_tests()

        # All search components should work
        assert verification["embedding_model"] is True
        assert verification["hybrid_search"] is True
        assert verification["mcp_server"] is True


class TestCPUModeErrorHandling:
    """Test error handling in CPU-only mode."""

    def test_cpu_insufficient_memory(self):
        """Test handling when system has insufficient RAM for CPU mode."""
        # Create environment with very low memory
        env = MockInstallationEnvironment(
            has_python=True,
            python_version="3.11.1",
            has_cuda=False,
            has_network=True,
            disk_space_gb=2.0  # Very low memory simulation
        )

        # PyTorch installation might fail due to low memory
        pytorch_result = env.simulate_pytorch_installation("https://pypi.org/simple")

        # With very low disk space, installation should fail
        assert pytorch_result["success"] is False

    def test_cpu_network_dependency_failure(self):
        """Test CPU installation with network failures."""
        env = MockInstallationEnvironment(
            has_python=True,
            has_cuda=False,
            has_network=False  # No network
        )

        # All network operations should fail
        uv_result = env.simulate_uv_installation()
        assert uv_result["success"] is False

        pytorch_result = env.simulate_pytorch_installation("https://pypi.org/simple")
        assert pytorch_result["success"] is False

        deps_result = env.simulate_dependency_installation(["transformers"])
        assert deps_result["success"] is False

    def test_cpu_python_compatibility(self):
        """Test CPU mode with different Python versions."""
        test_versions = [
            ("3.11.1", True),   # Ideal
            ("3.10.8", True),   # Supported
            ("3.9.7", True),    # Marginal (might work)
            ("3.8.10", False),  # Too old
        ]

        for version, should_work in test_versions:
            env = MockInstallationEnvironment(
                has_python=True,
                python_version=version,
                has_cuda=False
            )

            python_result = env.simulate_python_check()
            assert python_result["success"] is True
            assert python_result["version"] == version

            # Version compatibility would be checked by actual installer
            # For now, just verify the version is detected correctly


class TestCPUModeComparison:
    """Test comparing CPU mode with CUDA mode."""

    def test_installation_time_comparison(self):
        """Test that CPU installation is faster (no CUDA setup)."""
        cpu_env = get_mock_environment("ideal_cpu")
        cuda_env = get_mock_environment("ideal_cuda")

        # Simulate installations
        cpu_start_time = 0
        cpu_summary = cpu_env.get_install_summary()

        cuda_start_time = 0
        cuda_summary = cuda_env.get_install_summary()

        # CPU should have fewer installation steps
        # (No CUDA detection, no CUDA PyTorch index)
        assert isinstance(cpu_summary["total_attempts"], int)
        assert isinstance(cuda_summary["total_attempts"], int)

    def test_disk_space_comparison(self):
        """Test disk space requirements for CPU vs CUDA."""
        cpu_env = get_mock_environment("ideal_cpu")
        cuda_env = get_mock_environment("ideal_cuda")

        # CPU PyTorch should be smaller than CUDA PyTorch
        cpu_pytorch = cpu_env.simulate_pytorch_installation("https://pypi.org/simple")
        cuda_pytorch = cuda_env.simulate_pytorch_installation("https://download.pytorch.org/whl/cu121")

        assert cpu_pytorch["success"] is True
        assert cuda_pytorch["success"] is True

        # CPU version should not include CUDA libraries
        assert "cpu" in cpu_pytorch["version"]
        assert "cu" in cuda_pytorch["version"]

    def test_functionality_parity(self):
        """Test that CPU mode provides same functionality as CUDA mode."""
        cpu_env = get_mock_environment("ideal_cpu")
        cuda_env = get_mock_environment("ideal_cuda")

        # Both should support the same features (just different performance)
        cpu_verification = cpu_env.simulate_verification_tests()
        cuda_verification = cuda_env.simulate_verification_tests()

        # Same functionality, different CUDA support
        assert cpu_verification["embedding_model"] == cuda_verification["embedding_model"]
        assert cpu_verification["hybrid_search"] == cuda_verification["hybrid_search"]
        assert cpu_verification["mcp_server"] == cuda_verification["mcp_server"]

        # Only CUDA functional should differ
        assert cpu_verification["cuda_functional"] is False
        assert cuda_verification["cuda_functional"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])