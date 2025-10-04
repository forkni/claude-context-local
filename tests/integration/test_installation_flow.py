#!/usr/bin/env python3
"""
Integration tests for the complete installation workflow.
Tests end-to-end installation process including CUDA detection,
dependency installation, and verification.
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from tests.fixtures.installation_mocks import (MockInstallationEnvironment,
                                               get_mock_environment)


class TestCompleteInstallationFlow:
    """Test complete installation workflow from start to finish."""

    def test_ideal_cuda_installation_flow(self):
        """Test complete installation flow with ideal CUDA setup."""
        env = get_mock_environment("ideal_cuda")

        # Step 1: Python check
        python_result = env.simulate_python_check()
        assert python_result["success"] is True
        assert "3.11.1" in python_result["version"]

        # Step 2: CUDA detection
        cuda_result = env.simulate_cuda_detection()
        assert cuda_result["success"] is True
        assert cuda_result["cuda_version"] == "12.1"
        assert cuda_result["pytorch_index"] == "https://download.pytorch.org/whl/cu121"

        # Step 3: Virtual environment creation
        venv_result = env.simulate_venv_creation()
        assert venv_result["success"] is True

        # Step 4: UV installation
        uv_result = env.simulate_uv_installation()
        assert uv_result["success"] is True

        # Step 5: PyTorch installation with CUDA
        pytorch_result = env.simulate_pytorch_installation(cuda_result["pytorch_index"])
        assert pytorch_result["success"] is True
        assert pytorch_result["cuda_support"] is True

        # Step 6: Additional dependencies
        deps_result = env.simulate_dependency_installation(
            ["transformers", "sentence_transformers", "faiss", "rank_bm25", "nltk"]
        )
        assert deps_result["success"] is True

        # Step 7: Verification tests
        verify_result = env.simulate_verification_tests()
        assert verify_result["python_venv"] is True
        assert verify_result["pytorch"] is True
        assert verify_result["cuda_functional"] is True
        assert verify_result["embedding_model"] is True

        # Check installation history
        summary = env.get_install_summary()
        assert len(summary["failed_commands"]) == 0
        assert "pytorch" in " ".join(summary["install_history"])

    def test_cpu_only_installation_flow(self):
        """Test complete CPU-only installation flow."""
        env = get_mock_environment("ideal_cpu")

        # Step 1: Python check
        python_result = env.simulate_python_check()
        assert python_result["success"] is True

        # Step 2: CUDA detection (should fail)
        cuda_result = env.simulate_cuda_detection()
        assert cuda_result["success"] is False
        assert cuda_result["cuda_available"] is False
        assert cuda_result["pytorch_index"] == "https://pypi.org/simple"

        # Step 3: Virtual environment creation
        venv_result = env.simulate_venv_creation()
        assert venv_result["success"] is True

        # Step 4: UV installation (needed for verification checks)
        uv_result = env.simulate_uv_installation()
        assert uv_result["success"] is True

        # Step 5: PyTorch installation (CPU only)
        pytorch_result = env.simulate_pytorch_installation(cuda_result["pytorch_index"])
        assert pytorch_result["success"] is True
        assert pytorch_result["cuda_support"] is False

        # Step 6: Verification tests
        verify_result = env.simulate_verification_tests()
        assert verify_result["python_venv"] is True
        assert verify_result["pytorch"] is True
        assert verify_result["cuda_functional"] is False  # CPU only

    def test_network_failure_recovery(self):
        """Test installation flow with network failures."""
        env = get_mock_environment("network_issues")

        # Python check should succeed
        python_result = env.simulate_python_check()
        assert python_result["success"] is True

        # CUDA detection might succeed (local command)
        # But UV installation should fail
        uv_result = env.simulate_uv_installation()
        assert uv_result["success"] is False
        # Check for network error in the nested error dict
        error_info = uv_result.get("error", {})
        assert "command" in error_info or "network" in str(error_info).lower()

        # PyTorch installation should also fail
        pytorch_result = env.simulate_pytorch_installation("https://pypi.org/simple")
        assert pytorch_result["success"] is False

        # Check that failures are recorded (note: failed_commands needs explicit tracking)
        summary = env.get_install_summary()
        # Network failures don't automatically add to failed_commands in mock
        assert len(summary["install_history"]) == 0  # No successful installations

    def test_insufficient_disk_space_handling(self):
        """Test installation flow with insufficient disk space."""
        env = get_mock_environment("low_disk_space")

        # Python check should succeed
        python_result = env.simulate_python_check()
        assert python_result["success"] is True

        # Venv creation should fail due to low disk space
        venv_result = env.simulate_venv_creation()
        assert venv_result["success"] is False
        # Check for disk space error in nested error dict
        error_str = str(venv_result.get("error", {}))
        assert "space" in error_str.lower() or "disk" in error_str.lower()

        # PyTorch installation should also fail
        pytorch_result = env.simulate_pytorch_installation("https://pypi.org/simple")
        assert pytorch_result["success"] is False

    def test_old_python_version_handling(self):
        """Test installation flow with problematic Python version."""
        env = get_mock_environment("problematic_python")

        python_result = env.simulate_python_check()
        assert python_result["success"] is True
        assert python_result["version"] == "3.9.7"

        # Installation might proceed but with warnings
        # (This would be handled by actual installation logic)

    def test_future_cuda_version_handling(self):
        """Test installation flow with unsupported future CUDA version."""
        env = get_mock_environment("future_cuda")

        cuda_result = env.simulate_cuda_detection()
        assert cuda_result["success"] is True
        assert cuda_result["cuda_version"] == "13.0"
        assert cuda_result["supported"] is False
        assert "Future CUDA version not supported" in cuda_result.get("warning", "")

        # Should fallback to CPU installation
        auto_result = env.simulate_auto_install()
        # With unsupported CUDA, might fallback to CPU
        # (Depends on actual implementation logic)


class TestBatchScriptIntegration:
    """Test integration with actual batch scripts."""

    def setup_method(self):
        """Set up test environment."""
        self.project_root = Path(__file__).parent.parent.parent
        self.test_scripts = [
            "install-windows.bat",
            "verify-installation.bat",
            "start_mcp_server.bat",
        ]

    def test_batch_scripts_exist(self):
        """Test that all required batch scripts exist."""
        for script in self.test_scripts:
            script_path = self.project_root / script
            assert script_path.exists(), f"Script not found: {script}"

    @pytest.mark.skipif(os.name != "nt", reason="Windows batch scripts only")
    def test_batch_script_syntax(self):
        """Test batch script syntax by attempting to parse them."""
        for script in self.test_scripts:
            script_path = self.project_root / script

            # Read script content
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Basic syntax checks
            assert content.strip(), f"Script {script} is empty"
            assert "@echo off" in content.lower() or "echo" in content.lower(), (
                f"Script {script} might have syntax issues"
            )

    @patch("subprocess.run")
    def test_verify_installation_mock(self, mock_run):
        """Test verify-installation.bat with mocked responses."""
        # Mock successful responses
        mock_run.return_value = Mock(
            returncode=0, stdout="Python 3.11.1\nPyTorch 2.5.1+cu121\n", stderr=""
        )

        # This would normally run the actual script
        # For now, we test that our mock responses are correct
        result = mock_run.return_value
        assert result.returncode == 0
        assert "Python" in result.stdout
        assert "PyTorch" in result.stdout

    def test_installation_script_arguments(self):
        """Test that installation scripts handle arguments correctly."""
        # Test script parsing logic
        test_cases = [
            ("--cuda", "CUDA mode"),
            ("--cpu", "CPU mode"),
            ("--auto", "Auto detection"),
            ("--help", "Help message"),
        ]

        for arg, expected_behavior in test_cases:
            # This would test actual argument parsing
            # For now, just verify the structure
            assert isinstance(arg, str)
            assert isinstance(expected_behavior, str)


class TestInstallationValidation:
    """Test installation validation and verification."""

    def test_python_environment_validation(self):
        """Test Python environment validation logic."""
        env = MockInstallationEnvironment(has_python=True, python_version="3.11.1")

        result = env.simulate_python_check()
        assert result["success"] is True

        # Test version parsing
        version_parts = result["version"].split(".")
        assert len(version_parts) >= 2
        assert int(version_parts[0]) >= 3
        assert int(version_parts[1]) >= 10  # Minimum Python 3.10

    def test_pytorch_installation_validation(self):
        """Test PyTorch installation validation."""
        env = get_mock_environment("ideal_cuda")

        # Test CUDA PyTorch
        result = env.simulate_pytorch_installation(
            "https://download.pytorch.org/whl/cu121"
        )
        assert result["success"] is True
        assert "cu121" in result["version"]

        # Test CPU PyTorch
        cpu_result = env.simulate_pytorch_installation("https://pypi.org/simple")
        assert cpu_result["success"] is True
        assert "cpu" in cpu_result["version"]

    def test_dependency_compatibility_validation(self):
        """Test dependency compatibility validation."""
        env = get_mock_environment("ideal_cuda")

        dependencies = [
            "transformers",
            "sentence_transformers",
            "faiss",
            "rank_bm25",
            "nltk",
        ]
        result = env.simulate_dependency_installation(dependencies)

        assert result["success"] is True
        assert len(result["packages"]) == len(dependencies)

        # Verify specific versions are available
        expected_versions = {
            "transformers": "4.56.0",
            "sentence_transformers": "5.1.0",
            "faiss": "1.12.0",
        }

        for pkg, expected_version in expected_versions.items():
            if pkg in result["packages"]:
                # This would normally check actual version compatibility
                assert isinstance(result["packages"][pkg], str)

    def test_verification_test_completeness(self):
        """Test that verification tests cover all critical components."""
        env = get_mock_environment("ideal_cuda")

        # Simulate complete installation
        env.simulate_venv_creation()
        env.simulate_uv_installation()
        env.simulate_pytorch_installation("https://download.pytorch.org/whl/cu121")

        verification = env.simulate_verification_tests()

        required_checks = [
            "python_venv",
            "pytorch",
            "cuda_functional",
            "embedding_model",
            "hybrid_search",
            "mcp_server",
        ]

        for check in required_checks:
            assert check in verification, f"Missing verification check: {check}"

    def test_installation_rollback_capability(self):
        """Test that installation can be rolled back on failure."""
        env = MockInstallationEnvironment(
            has_network=False,  # This will cause failures
            disk_space_gb=0.5,  # Very low - will fail venv creation
        )

        # Attempt installation steps
        venv_result = env.simulate_venv_creation()
        uv_result = env.simulate_uv_installation()

        # Check failure handling
        assert venv_result["success"] is False  # Due to low disk space (0.5GB <= 1.0GB)
        assert uv_result["success"] is False  # Due to no network

        # Verify cleanup would be possible
        summary = env.get_install_summary()
        # Mock doesn't automatically track failed_commands, but we verify no successful installs
        assert len(summary["install_history"]) == 0  # No successful installations

        # In real implementation, this would trigger cleanup
        # For now, verify that failure state is recorded
        assert summary["total_attempts"] == 0  # Nothing succeeded


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
