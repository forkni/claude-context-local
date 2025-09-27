#!/usr/bin/env python3
"""
Mock data and fixtures for installation testing.
Provides consistent test environments for different hardware configurations.
"""

from typing import Dict, List, Optional

# Mock CUDA versions for testing
CUDA_VERSIONS = {
    "12.1": {
        "pytorch_index": "https://download.pytorch.org/whl/cu121",
        "supported": True,
        "recommended": True,
    },
    "12.0": {
        "pytorch_index": "https://download.pytorch.org/whl/cu121",
        "supported": True,
        "recommended": True,
    },
    "11.8": {
        "pytorch_index": "https://download.pytorch.org/whl/cu118",
        "supported": True,
        "recommended": False,
    },
    "11.7": {
        "pytorch_index": "https://download.pytorch.org/whl/cu117",
        "supported": True,
        "recommended": False,
    },
    "13.0": {
        "pytorch_index": None,
        "supported": False,
        "recommended": False,
        "warning": "Future CUDA version not supported",
    },
    "10.2": {
        "pytorch_index": None,
        "supported": False,
        "recommended": False,
        "warning": "CUDA version too old",
    },
}

# Mock nvidia-smi outputs for different configurations
MOCK_NVIDIA_SMI_OUTPUTS = {
    "cuda_12_1": """
NVIDIA GeForce RTX 4090, Driver Version: 537.13, CUDA Version: 12.1
    """.strip(),
    "cuda_11_8": """
NVIDIA GeForce RTX 3080, Driver Version: 516.94, CUDA Version: 11.8
    """.strip(),
    "cuda_11_7": """
NVIDIA GeForce RTX 3070, Driver Version: 516.40, CUDA Version: 11.7
    """.strip(),
    "multiple_gpus": """
NVIDIA GeForce RTX 4090, Driver Version: 537.13, CUDA Version: 12.1
NVIDIA GeForce RTX 3080, Driver Version: 537.13, CUDA Version: 12.1
    """.strip(),
    "future_cuda": """
NVIDIA GeForce RTX 5090, Driver Version: 600.00, CUDA Version: 13.0
    """.strip(),
    "driver_mismatch": """
NVIDIA GeForce RTX 4090, Driver Version: 511.23, CUDA Version: 12.1
    """.strip(),
}

# Mock Python version outputs
MOCK_PYTHON_VERSIONS = {
    "python_3_11": "Python 3.11.1",
    "python_3_12": "Python 3.12.0",
    "python_3_10": "Python 3.10.8",
    "python_3_9": "Python 3.9.7",  # Potentially problematic
    "python_3_8": "Python 3.8.10",  # Too old
}

# Mock dependency versions
MOCK_DEPENDENCIES = {
    "pytorch_cuda": {
        "cu121": "2.5.1+cu121",
        "cu118": "2.4.0+cu118",
        "cu117": "2.1.0+cu117",
        "cpu": "2.5.1+cpu",
    },
    "transformers": "4.56.0",
    "sentence_transformers": "5.1.0",
    "faiss": "1.12.0",
    "rank_bm25": "0.2.2",
    "nltk": "3.8",
}

# Mock error scenarios
ERROR_SCENARIOS = {
    "python_not_found": {
        "command": "python --version",
        "error": FileNotFoundError(
            "'python' is not recognized as an internal or external command"
        ),
        "exit_code": 1,
        "recommendation": "Install Python 3.11+ and add to PATH",
    },
    "nvidia_smi_not_found": {
        "command": "nvidia-smi",
        "error": FileNotFoundError(
            "'nvidia-smi' is not recognized as an internal or external command"
        ),
        "exit_code": 1,
        "meaning": "No NVIDIA GPU or drivers installed",
    },
    "network_error": {
        "command": "pip install torch",
        "error": "Connection error: Unable to reach PyPI",
        "exit_code": 1,
        "recommendation": "Check internet connection and try again",
    },
    "insufficient_space": {
        "command": "pip install torch",
        "error": "No space left on device",
        "exit_code": 1,
        "recommendation": "Free up at least 5GB disk space",
    },
    "permission_error": {
        "command": "python -m venv .venv",
        "error": "Permission denied",
        "exit_code": 1,
        "recommendation": "Run as administrator or check folder permissions",
    },
}


class MockInstallationEnvironment:
    """Mock environment for testing installation scenarios."""

    def __init__(
        self,
        has_python: bool = True,
        python_version: str = "3.11.1",
        has_cuda: bool = False,
        cuda_version: Optional[str] = None,
        gpu_name: str = "NVIDIA GeForce RTX 4090",
        has_network: bool = True,
        disk_space_gb: float = 50.0,
    ):
        self.has_python = has_python
        self.python_version = python_version
        self.has_cuda = has_cuda
        self.cuda_version = cuda_version
        self.gpu_name = gpu_name
        self.has_network = has_network
        self.disk_space_gb = disk_space_gb

        self.install_history: List[str] = []
        self.failed_commands: List[str] = []

    def simulate_python_check(self) -> Dict:
        """Simulate python --version check."""
        if not self.has_python:
            return {"success": False, "error": ERROR_SCENARIOS["python_not_found"]}

        return {
            "success": True,
            "version": self.python_version,
            "output": f"Python {self.python_version}",
        }

    def simulate_cuda_detection(self) -> Dict:
        """Simulate CUDA detection via nvidia-smi."""
        if not self.has_cuda:
            return {
                "success": False,
                "cuda_available": False,
                "error": ERROR_SCENARIOS["nvidia_smi_not_found"],
                "pytorch_index": "https://pypi.org/simple",
            }

        cuda_info = CUDA_VERSIONS.get(self.cuda_version, {})

        return {
            "success": True,
            "cuda_available": True,
            "cuda_version": self.cuda_version,
            "gpu_name": self.gpu_name,
            "pytorch_index": cuda_info.get("pytorch_index"),
            "supported": cuda_info.get("supported", False),
            "warning": cuda_info.get("warning"),
        }

    def simulate_venv_creation(self) -> Dict:
        """Simulate virtual environment creation."""
        if self.disk_space_gb < 1:
            return {"success": False, "error": ERROR_SCENARIOS["insufficient_space"]}

        self.install_history.append("venv_created")
        return {
            "success": True,
            "venv_path": ".venv",
            "python_executable": ".venv/Scripts/python.exe",
        }

    def simulate_uv_installation(self) -> Dict:
        """Simulate UV package manager installation."""
        if not self.has_network:
            return {"success": False, "error": ERROR_SCENARIOS["network_error"]}

        self.install_history.append("uv_installed")
        return {"success": True, "version": "0.1.0"}

    def simulate_pytorch_installation(self, index_url: str) -> Dict:
        """Simulate PyTorch installation."""
        if not self.has_network:
            return {"success": False, "error": ERROR_SCENARIOS["network_error"]}

        if self.disk_space_gb < 3:
            return {"success": False, "error": ERROR_SCENARIOS["insufficient_space"]}

        # Determine PyTorch version based on index
        if "cu121" in index_url:
            version = MOCK_DEPENDENCIES["pytorch_cuda"]["cu121"]
        elif "cu118" in index_url:
            version = MOCK_DEPENDENCIES["pytorch_cuda"]["cu118"]
        elif "cu117" in index_url:
            version = MOCK_DEPENDENCIES["pytorch_cuda"]["cu117"]
        else:
            version = MOCK_DEPENDENCIES["pytorch_cuda"]["cpu"]

        self.install_history.append(f"pytorch_{version}")
        return {
            "success": True,
            "version": version,
            "cuda_support": "cu" in version,
            "index_url": index_url,
        }

    def simulate_dependency_installation(self, packages: List[str]) -> Dict:
        """Simulate installation of additional dependencies."""
        if not self.has_network:
            return {"success": False, "error": ERROR_SCENARIOS["network_error"]}

        installed_packages = {}
        for package in packages:
            if package in MOCK_DEPENDENCIES:
                installed_packages[package] = MOCK_DEPENDENCIES[package]
                self.install_history.append(f"installed_{package}")

        return {"success": True, "packages": installed_packages}

    def simulate_auto_install(self) -> Dict:
        """Simulate auto-installation choice."""
        cuda_info = self.simulate_cuda_detection()

        if cuda_info["cuda_available"]:
            return {
                "mode": "cuda",
                "pytorch_index": cuda_info["pytorch_index"],
                "dependencies_include_cuda": True,
                "choice": "auto_cuda",
            }
        else:
            return {
                "mode": "cpu",
                "pytorch_index": "https://pypi.org/simple",
                "dependencies_include_cuda": False,
                "choice": "auto_cpu",
            }

    def simulate_manual_cuda_selection(self, selected_version: str) -> Dict:
        """Simulate manual CUDA version selection."""
        cuda_info = CUDA_VERSIONS.get(selected_version, {})

        return {
            "mode": "cuda",
            "pytorch_index": cuda_info.get("pytorch_index", "https://pypi.org/simple"),
            "user_override": True,
            "selected_version": selected_version,
            "supported": cuda_info.get("supported", False),
        }

    def simulate_cpu_only_install(self) -> Dict:
        """Simulate forced CPU-only installation."""
        return {
            "mode": "cpu",
            "pytorch_index": "https://pypi.org/simple",
            "forced_cpu": True,
            "cuda_available": self.has_cuda,  # Still show CUDA was available
        }

    def simulate_verification_tests(self) -> Dict:
        """Simulate post-installation verification."""
        results = {
            "python_venv": "installed" in " ".join(self.install_history),
            "pytorch": any("pytorch" in item for item in self.install_history),
            "cuda_functional": False,
            "embedding_model": False,
            "hybrid_search": False,
            "mcp_server": False,
        }

        # Check CUDA functionality
        if self.has_cuda and any("cu" in item for item in self.install_history):
            results["cuda_functional"] = True

        # Check if core dependencies were installed
        if any("uv_installed" in item for item in self.install_history):
            results["embedding_model"] = True
            results["hybrid_search"] = True
            results["mcp_server"] = True

        return results

    def get_install_summary(self) -> Dict:
        """Get summary of installation attempts."""
        return {
            "environment": {
                "python": self.python_version if self.has_python else None,
                "cuda": self.cuda_version if self.has_cuda else None,
                "gpu": self.gpu_name if self.has_cuda else None,
                "network": self.has_network,
                "disk_space_gb": self.disk_space_gb,
            },
            "install_history": self.install_history,
            "failed_commands": self.failed_commands,
            "total_attempts": len(self.install_history) + len(self.failed_commands),
        }


# Pre-configured test environments
TEST_ENVIRONMENTS = {
    "ideal_cuda": MockInstallationEnvironment(
        has_python=True,
        python_version="3.11.1",
        has_cuda=True,
        cuda_version="12.1",
        gpu_name="NVIDIA GeForce RTX 4090",
        has_network=True,
        disk_space_gb=100.0,
    ),
    "ideal_cpu": MockInstallationEnvironment(
        has_python=True,
        python_version="3.11.1",
        has_cuda=False,
        has_network=True,
        disk_space_gb=50.0,
    ),
    "older_cuda": MockInstallationEnvironment(
        has_python=True,
        python_version="3.11.1",
        has_cuda=True,
        cuda_version="11.8",
        gpu_name="NVIDIA GeForce RTX 3080",
        has_network=True,
        disk_space_gb=50.0,
    ),
    "problematic_python": MockInstallationEnvironment(
        has_python=True,
        python_version="3.9.7",  # Older Python
        has_cuda=True,
        cuda_version="12.1",
        has_network=True,
        disk_space_gb=50.0,
    ),
    "no_python": MockInstallationEnvironment(
        has_python=False,
        has_cuda=True,
        cuda_version="12.1",
        has_network=True,
        disk_space_gb=50.0,
    ),
    "network_issues": MockInstallationEnvironment(
        has_python=True,
        python_version="3.11.1",
        has_cuda=True,
        cuda_version="12.1",
        has_network=False,
        disk_space_gb=50.0,
    ),
    "low_disk_space": MockInstallationEnvironment(
        has_python=True,
        python_version="3.11.1",
        has_cuda=True,
        cuda_version="12.1",
        has_network=True,
        disk_space_gb=1.0,  # Very low
    ),
    "future_cuda": MockInstallationEnvironment(
        has_python=True,
        python_version="3.11.1",
        has_cuda=True,
        cuda_version="13.0",  # Future unsupported version
        gpu_name="NVIDIA GeForce RTX 5090",
        has_network=True,
        disk_space_gb=50.0,
    ),
}


def get_mock_environment(env_name: str) -> MockInstallationEnvironment:
    """Get a pre-configured test environment."""
    if env_name not in TEST_ENVIRONMENTS:
        raise ValueError(
            f"Unknown environment: {env_name}. Available: {list(TEST_ENVIRONMENTS.keys())}"
        )

    return TEST_ENVIRONMENTS[env_name]


def create_custom_environment(**kwargs) -> MockInstallationEnvironment:
    """Create a custom test environment with specific parameters."""
    return MockInstallationEnvironment(**kwargs)


# Mock subprocess responses for common commands
MOCK_SUBPROCESS_RESPONSES = {
    "python --version": {"success": ("Python 3.11.1", 0), "failure": ("", 1)},
    "nvidia-smi --version": {
        "success": (MOCK_NVIDIA_SMI_OUTPUTS["cuda_12_1"], 0),
        "failure": ("", 1),
    },
    "pip install uv": {
        "success": ("Successfully installed uv", 0),
        "network_error": ("Connection error", 1),
    },
    "uv sync": {
        "success": ("Dependencies installed", 0),
        "failure": ("Failed to install dependencies", 1),
    },
}


def get_mock_subprocess_response(command: str, scenario: str = "success"):
    """Get mock subprocess response for testing."""
    command_responses = MOCK_SUBPROCESS_RESPONSES.get(command, {})
    return command_responses.get(scenario, ("Command not found", 127))
