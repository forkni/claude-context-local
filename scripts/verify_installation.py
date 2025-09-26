#!/usr/bin/env python3
"""
Installation Verification Script for Claude Context MCP
Comprehensive testing of all system components
"""

import os
import sys
import subprocess
import tempfile
import shutil
import importlib.util
import platform
from pathlib import Path
from typing import Tuple, Optional, Dict, Any


class InstallationVerifier:
    """Comprehensive installation verification for Claude Context MCP."""

    def __init__(self):
        """Initialize the verification system."""
        self.pass_count = 0
        self.fail_count = 0
        self.warn_count = 0
        self.temp_dir = tempfile.mkdtemp(prefix="claude_verify_")
        self.project_dir = Path(__file__).parent.parent.absolute()
        self.python_exe = self.project_dir / ".venv" / "Scripts" / "python.exe"

        print("=================================================")
        print("Claude Context MCP - Installation Verification")
        print("=================================================")
        print(f"[INFO] Using temp directory: {self.temp_dir}")
        print()

    def _run_python_test(self, code: str, description: str = "") -> Tuple[bool, str]:
        """Run a Python code snippet and return success status and output."""
        try:
            result = subprocess.run(
                [str(self.python_exe), "-c", code],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Test timed out after 60 seconds"
        except Exception as e:
            return False, f"Failed to run test: {e}"

    def _print_test_result(self, test_name: str, passed: bool, output: str = "", details: str = ""):
        """Print formatted test result."""
        if passed:
            print(f"[PASS] {test_name}")
            self.pass_count += 1
            if details:
                print(f"       {details}")
        else:
            print(f"[FAIL] {test_name}")
            self.fail_count += 1
            if output:
                print(f"       Error: {output.strip()}")

        if output and passed and details != output.strip():
            for line in output.strip().split('\n'):
                if line.strip():
                    print(f"       {line.strip()}")

    def _print_warning(self, test_name: str, message: str, output: str = ""):
        """Print formatted warning."""
        print(f"[WARN] {test_name}")
        print(f"       {message}")
        self.warn_count += 1
        if output:
            for line in output.strip().split('\n'):
                if line.strip():
                    print(f"       {line.strip()}")

    def test_virtual_environment(self) -> bool:
        """Test if virtual environment exists and is functional."""
        print("=== System Check ===")
        print()

        # Check if virtual environment directory exists
        if not self.python_exe.exists():
            self._print_test_result("Virtual Environment", False,
                                  f"Virtual environment not found at {self.python_exe}")
            return False

        self._print_test_result("Virtual Environment", True,
                              details="Virtual environment exists")
        return True

    def test_python_version(self) -> bool:
        """Test Python version."""
        success, output = self._run_python_test("import sys; print(f'Python {sys.version.split()[0]}')",
                                               "Python Version")

        if success:
            version_line = output.strip()
            self._print_test_result("Python Version", True, details=f"{version_line} working")
            return True
        else:
            self._print_test_result("Python Version", False,
                                  "Python not working in virtual environment")
            return False

    def test_pytorch_cuda(self) -> bool:
        """Test PyTorch installation and CUDA availability."""
        print()
        print("=== PyTorch CUDA Check ===")
        print()

        # Test PyTorch installation
        pytorch_code = """
import torch
print(f'PyTorch version: {torch.__version__}')
"""
        success, output = self._run_python_test(pytorch_code, "PyTorch Installation")

        if not success:
            self._print_test_result("PyTorch Installation", False, output)
            return False

        self._print_test_result("PyTorch Installation", True,
                              details="PyTorch imported successfully")
        print(f"       {output.strip()}")

        # Test CUDA availability
        cuda_code = """
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA devices: {torch.cuda.device_count()}')
else:
    print('CUDA devices: 0')
"""
        success, output = self._run_python_test(cuda_code, "CUDA Availability")

        if not success:
            self._print_test_result("CUDA Availability", False,
                                  "CUDA test failed - Python/PyTorch error")
            print(f"       This usually means PyTorch is not installed correctly")
            return False

        # Check if CUDA is actually available
        if "CUDA available: True" in output:
            self._print_test_result("CUDA Availability", True,
                                  details="CUDA acceleration available")
            print(f"       {output.strip()}")

            # Get GPU information
            gpu_code = """
import torch
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')
else:
    print('  No CUDA devices')
"""
            gpu_success, gpu_output = self._run_python_test(gpu_code, "GPU Information")
            if gpu_success:
                print("       GPU Information:")
                print(f"       {gpu_output.strip()}")
        else:
            self._print_warning("CUDA Availability", "Running in CPU-only mode", output)

        return True

    def test_core_dependencies(self) -> bool:
        """Test core dependencies."""
        print()
        print("=== Core Dependencies Check ===")
        print()

        dependencies = [
            ("Transformers Library", "import transformers; print(f'Transformers version: {transformers.__version__}')"),
            ("Sentence Transformers", "from sentence_transformers import SentenceTransformer; print('SentenceTransformer available')"),
            ("FAISS Vector Search", "import faiss; print('FAISS version:', getattr(faiss, '__version__', 'Available'))"),
        ]

        all_passed = True
        for name, code in dependencies:
            success, output = self._run_python_test(code, name)
            if success:
                self._print_test_result(name, True, details=f"{name.split()[0]} library working")
                if output.strip():
                    print(f"       {output.strip()}")
            else:
                self._print_test_result(name, False, f"{name} import failed")
                if output.strip():
                    print(f"       {output.strip()}")
                all_passed = False

        return all_passed

    def test_hybrid_search_dependencies(self) -> bool:
        """Test hybrid search dependencies."""
        print()
        print("=== Hybrid Search Dependencies ===")
        print()

        # Test BM25
        bm25_code = "import rank_bm25; print('BM25 available')"
        success, output = self._run_python_test(bm25_code, "BM25 Text Search")

        if success:
            self._print_test_result("BM25 Text Search", True,
                                  details="BM25 text search available")
        else:
            self._print_test_result("BM25 Text Search", False,
                                  "BM25 (rank_bm25) import failed")

        # Test NLTK
        nltk_code = "import nltk; print(f'NLTK version: {nltk.__version__}')"
        nltk_success, nltk_output = self._run_python_test(nltk_code, "NLTK Natural Language Processing")

        if nltk_success:
            self._print_test_result("NLTK Natural Language Processing", True,
                                  details="NLTK available")
            print(f"       {nltk_output.strip()}")

            # Test NLTK data
            nltk_data_code = """
import nltk
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
    print('NLTK data available')
except:
    raise Exception('NLTK data not found')
"""
            data_success, data_output = self._run_python_test(nltk_data_code, "NLTK Data Resources")

            if data_success:
                self._print_test_result("NLTK Data Resources", True,
                                      details="NLTK data resources available")
            else:
                self._print_warning("NLTK Data Resources",
                                  "NLTK data not fully available - downloading...")

                # Try to download NLTK data
                download_code = """
import nltk
nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
print('NLTK data downloaded')
"""
                download_success, download_output = self._run_python_test(download_code, "NLTK Data Download")

                if download_success:
                    self._print_test_result("NLTK Data Resources", True,
                                          details="NLTK data downloaded successfully")
                else:
                    self._print_test_result("NLTK Data Resources", False,
                                          "NLTK data download failed")
        else:
            self._print_test_result("NLTK Natural Language Processing", False,
                                  "NLTK import failed")

        return success and nltk_success

    def test_mcp_server(self) -> bool:
        """Test MCP server functionality."""
        print()
        print("=== MCP Server Check ===")
        print()

        # Test MCP server import
        mcp_code = "from mcp_server import server; print('MCP server module available')"
        success, output = self._run_python_test(mcp_code, "MCP Server Module")

        if success:
            self._print_test_result("MCP Server Module", True,
                                  details="MCP server module available")
        else:
            self._print_test_result("MCP Server Module", False,
                                  "MCP server import failed")
            return False

        # Test MCP server help command
        try:
            result = subprocess.run(
                [str(self.python_exe), "-m", "mcp_server.server", "--help"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                self._print_test_result("MCP Server Functionality", True,
                                      details="MCP server responds to commands")
            else:
                self._print_test_result("MCP Server Functionality", False,
                                      "MCP server not responding")
                return False
        except Exception as e:
            self._print_test_result("MCP Server Functionality", False,
                                  f"MCP server test failed: {e}")
            return False

        return True

    def test_tree_sitter_parsers(self) -> bool:
        """Test tree-sitter parsers."""
        print()
        print("=== Tree-sitter Parsers Check ===")
        print()

        parser_code = """
try:
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_java
    import tree_sitter_go
    import tree_sitter_rust
    import tree_sitter_c
    import tree_sitter_cpp
    import tree_sitter_c_sharp
    import tree_sitter_glsl
    print('All tree-sitter parsers available')
    print('Supported: Python, JS, TS, Java, Go, Rust, C, C++, C#, GLSL')
except ImportError as e:
    print(f'Some parsers missing: {e}')
    raise
"""

        success, output = self._run_python_test(parser_code, "Multi-language Parsers")

        if success:
            self._print_test_result("Multi-language Parsers", True,
                                  details="All tree-sitter parsers available")
            for line in output.strip().split('\n'):
                if line.strip():
                    print(f"       {line.strip()}")
        else:
            self._print_warning("Multi-language Parsers",
                              "Some tree-sitter parsers missing", output)

        return True  # Don't fail the overall test for missing parsers

    def test_performance(self) -> bool:
        """Run quick performance benchmark."""
        print()
        print("=== Performance Test ===")
        print()

        perf_code = """
import torch
import time

print('Testing tensor operations...')
device = 'cuda' if torch.cuda.is_available() else 'cpu'
size = 500

start = time.time()
x = torch.randn(size, size).to(device)
y = torch.randn(size, size).to(device)
result = torch.matmul(x, y)

if device == 'cuda':
    torch.cuda.synchronize()

elapsed = time.time() - start
print(f'Matrix multiplication ({size}x{size}) on {device}: {elapsed:.3f}s')

if elapsed < 1.0:
    perf = 'Good'
elif elapsed < 5.0:
    perf = 'Acceptable'
else:
    perf = 'Slow'

print(f'Performance: {perf}')
"""

        success, output = self._run_python_test(perf_code, "Quick Performance Benchmark")

        if success:
            self._print_test_result("Quick Performance Benchmark", True,
                                  details="Performance test completed")
            for line in output.strip().split('\n'):
                if line.strip():
                    print(f"       {line.strip()}")
        else:
            self._print_test_result("Quick Performance Benchmark", False,
                                  "Performance test failed")

        return success

    def test_embedding_model(self) -> bool:
        """Test EmbeddingGemma model loading (optional)."""
        print()
        print("=== EmbeddingGemma Model Test ===")
        print()
        print("[INFO] This test will download ~1.2GB model if not cached...")

        embedding_code = """
try:
    from sentence_transformers import SentenceTransformer
    import torch

    print('Loading EmbeddingGemma model...')
    model = SentenceTransformer('google/embeddinggemma-300m')
    print(f'Model loaded on device: {model.device}')

    test_text = 'def hello_world(): return "Hello World"'
    embedding = model.encode([test_text])
    print(f'Generated embedding shape: {embedding.shape}')
    print('EmbeddingGemma test successful')

except Exception as e:
    print(f'EmbeddingGemma test failed: {e}')
    print('Note: This is acceptable if model is not downloaded yet')
    raise
"""

        success, output = self._run_python_test(embedding_code, "EmbeddingGemma Model Loading")

        if success:
            self._print_test_result("EmbeddingGemma Model Loading", True,
                                  details="EmbeddingGemma model working")
            for line in output.strip().split('\n'):
                if line.strip():
                    print(f"       {line.strip()}")
        else:
            self._print_warning("EmbeddingGemma Model Loading",
                              "EmbeddingGemma model test failed",
                              "Model will be downloaded on first use")

        return True  # Don't fail overall test for model download issues

    def print_summary(self):
        """Print test results summary."""
        print()
        print("=================================================")
        print("Installation Verification Summary")
        print("=================================================")
        print()

        print("Test Results:")
        print(f"   [+] Passed: {self.pass_count} tests")
        if self.warn_count > 0:
            print(f"   [!] Warnings: {self.warn_count} tests")
        if self.fail_count > 0:
            print(f"   [-] Failed: {self.fail_count} tests")

        print()

        # Overall status
        if self.fail_count > 0:
            print("[OVERALL] Installation has CRITICAL ISSUES")
            print("Recommendation: Run install-windows.bat to repair installation")
        elif self.warn_count > 0:
            print("[OVERALL] Installation is MOSTLY WORKING")
            print("Some optional components may need attention")
            print("The system should work for basic functionality")
        else:
            print("[OVERALL] Installation is FULLY FUNCTIONAL")
            print("All components are working correctly")
            print("Ready for hybrid search with Claude Code!")

        print()

        # System status
        print("System Status:")
        system_code = """
import torch
cuda_available = torch.cuda.is_available()
device_count = torch.cuda.device_count() if cuda_available else 0

print(f'  PyTorch: {torch.__version__}')
print(f'  CUDA: {"Available" if cuda_available else "CPU-Only"}')

if cuda_available:
    print(f'  GPU Devices: {device_count}')
    for i in range(device_count):
        print(f'    {i}: {torch.cuda.get_device_name(i)}')
else:
    print('  Note: Running in CPU-only mode (slower but functional)')
"""

        success, output = self._run_python_test(system_code, "System Status")
        if success:
            for line in output.strip().split('\n'):
                print(line)

        print()
        print("Next Steps:")
        if self.fail_count > 0:
            print("1. Fix critical issues by running: install-windows.bat")
            print("2. Re-run verification: verify-installation.bat")
        else:
            print("1. Start MCP server: start_mcp_server.bat")
            print("2. Configure Claude Code: scripts\\powershell\\configure_claude_code.ps1")
            print("3. Test with Claude Code: /index_directory \"your-project-path\"")
        print()

    def run_all_tests(self):
        """Run all verification tests."""
        try:
            # Critical tests - stop if these fail
            if not self.test_virtual_environment():
                return

            if not self.test_python_version():
                return

            # Continue with other tests regardless of individual failures
            self.test_pytorch_cuda()
            self.test_core_dependencies()
            self.test_hybrid_search_dependencies()
            self.test_mcp_server()
            self.test_tree_sitter_parsers()
            self.test_performance()
            self.test_embedding_model()

        except KeyboardInterrupt:
            print()
            print("[INFO] Verification interrupted by user")
            self.fail_count += 1
        except Exception as e:
            print()
            print(f"[ERROR] Unexpected error during verification: {e}")
            self.fail_count += 1

    def cleanup(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                print(f"[INFO] Temp files cleaned successfully")
            except Exception as e:
                print(f"[WARN] Could not remove all temp files: {e}")
                print(f"[WARN] Location: {self.temp_dir}")


def main():
    """Main entry point."""
    verifier = InstallationVerifier()
    try:
        verifier.run_all_tests()
        verifier.print_summary()
    finally:
        verifier.cleanup()

    return verifier.fail_count


if __name__ == "__main__":
    exit_code = main()
    print()
    # Only wait for input if running interactively
    if sys.stdin.isatty():
        print("Press any key to exit...")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(exit_code)