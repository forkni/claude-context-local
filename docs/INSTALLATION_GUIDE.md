# Claude Context MCP Installation Guide

## Overview

This guide covers the complete installation process for the Claude Context MCP system, a **Windows-optimized general-purpose semantic code search tool** for software development. The system provides streamlined installation with automated CUDA detection and comprehensive verification.

> **📁 Archived Content**: Development tools, test scripts, and TouchDesigner-specific features have been preserved in `_archive/` directory. See `_archive/README.md` for details.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation Methods](#installation-methods)
3. [Dependency Management](#dependency-management)
4. [PyTorch Installation](#pytorch-installation)
5. [Verification & Testing](#verification--testing)
6. [Troubleshooting](#troubleshooting)
7. [Performance Optimization](#performance-optimization)

## Prerequisites

### System Requirements

- **Python**: 3.11+ (tested with Python 3.11.1)
- **Operating System**: Windows 10/11
- **Disk Space**: 2-3 GB free space
  - EmbeddingGemma model: ~1.3 GB
  - PyTorch with CUDA: ~2.4 GB
  - Dependencies and cache: ~500 MB
- **Memory**: 4GB RAM minimum, 8GB+ recommended
- **GPU** (optional): NVIDIA GPU with CUDA 12.1 support

> **Windows Focus**: This system is optimized for Windows environments with automated installers and comprehensive verification tools.

### Software Dependencies

- **Git**: For cloning the repository
- **UV Package Manager**: Recommended for dependency resolution
- **Claude Code**: For MCP integration

## Installation Methods

### Recommended: Windows One-Click Installation

**The streamlined Windows installation process with automated verification.**

#### Windows Installation (Primary Method)

```powershell
# 1. Clone the repository
git clone https://github.com/forkni/claude-context-local.git
cd claude-context-local

# 2. Run the unified Windows installer
install-windows.bat

# 3. Verify installation
verify-installation.bat

# 4. (Optional) Configure Claude Code MCP integration
scripts\powershell\configure_claude_code.ps1 -Global
```

**What this provides:**

- ✅ **Smart CUDA Detection**: Automatically detects and installs appropriate PyTorch version
- ✅ **Complete Setup**: All dependencies including hybrid search components
- ✅ **Professional Organization**: Clean, streamlined script structure
- ✅ **Comprehensive Verification**: Built-in testing with verify-installation.bat
- ✅ **Windows Optimized**: Specifically designed for Windows environments

### Alternative Platforms

For macOS and Linux support, please use the cross-platform version at [FarhanAliRaza/claude-context-local](https://github.com/FarhanAliRaza/claude-context-local), which this project was forked from.

## HuggingFace Authentication

### Overview

The EmbeddingGemma model (`google/embeddinggemma-300m`) requires HuggingFace authentication to download and use. This is a one-time setup that the installer will guide you through.

### Prerequisites

1. **HuggingFace Account**: Create a free account at [https://huggingface.co](https://huggingface.co)
2. **Model Access**: Accept terms at [https://huggingface.co/google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m)
3. **Access Token**: Create a token with 'Read' permissions at [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### Installation Integration

The Windows installer (`install-windows.bat`) includes automatic HuggingFace authentication:

1. **Automatic Detection**: Checks if you're already authenticated
2. **Interactive Setup**: Prompts for your token if needed
3. **Validation**: Tests token and model access
4. **Error Guidance**: Provides clear steps if authentication fails

### Manual Authentication

If you need to authenticate manually after installation:

#### Option 1: Using PowerShell Helper Script (Recommended)

```powershell
# Authenticate with your token
scripts\powershell\hf_auth.ps1 -Token "hf_your_token_here"

# Test authentication only
scripts\powershell\hf_auth.ps1 -TestOnly

# Clear cache and re-authenticate
scripts\powershell\hf_auth.ps1 -Token "hf_your_token_here" -ClearCache
```

#### Option 2: Command Line

```powershell
# Set environment variable
$env:HF_TOKEN = "hf_your_token_here"

# Or use UV CLI login
.venv\Scripts\uv.exe run huggingface-cli login
```

#### Option 3: Standalone Verification

```powershell
# Check HuggingFace authentication status
verify-hf-auth.bat

# Or run the Python script directly
.venv\Scripts\python.exe scripts\verify_hf_auth.py
```

### Token Requirements

Your HuggingFace token must:

- **Start with `hf_`** (personal access tokens)
- **Have 'Read' permissions** (minimum required)
- **Be associated with an account** that has accepted the EmbeddingGemma model terms

### Troubleshooting Authentication

#### Common Issues

1. **Token Format Error**

   ```
   Error: Token should start with 'hf_'
   ```

   - Solution: Ensure you're using a personal access token, not a different type

2. **Model Access Denied**

   ```
   Error: Repository not found or access denied
   ```

   - Solution: Visit [https://huggingface.co/google/embeddinggemma-300m](https://huggingface.co/google/embeddinggemma-300m) and accept terms

3. **Authentication Failed**

   ```
   Error: Invalid token or insufficient permissions
   ```

   - Solution: Regenerate token with 'Read' permissions

#### Verification Commands

Test your authentication with these commands:

```powershell
# Quick authentication test
.venv\Scripts\python.exe -c "from huggingface_hub import whoami; print(whoami())"

# Model access test
.venv\Scripts\python.exe -c "from huggingface_hub import model_info; print(model_info('google/embeddinggemma-300m').modelId)"

# Full verification
verify-installation.bat
```

### Security Notes

- **Token Storage**: Tokens are stored locally in `~/.cache/huggingface/token`
- **Environment Variables**: Set `HF_TOKEN` for session-based authentication
- **No Transmission**: Your token is only used locally, never transmitted by our code

## Dependency Management

### Why UV is Recommended

1. **Advanced Dependency Resolution**
   - Handles complex version conflicts automatically
   - Prevents incompatible package combinations
   - Resolves PyTorch + transformers + sentence-transformers compatibility

2. **Performance Benefits**
   - Parallel downloads
   - Better caching mechanisms
   - Faster installation times

3. **PyTorch Integration**
   - Built-in support for PyTorch custom indexes
   - Automatic CUDA version detection
   - Handles mixed CPU/GPU dependencies

### UV vs pip Comparison

| Feature | UV | pip |
|---------|----|----|
| Dependency Resolution | Advanced SAT solver | Basic backtracking |
| Installation Speed | Fast (parallel) | Slower (sequential) |
| Cache Management | Efficient | Basic |
| PyTorch CUDA | Native support | Manual configuration |
| Conflict Detection | Proactive | Reactive |

## PyTorch Installation

### Version Requirements

- **Minimum PyTorch**: 2.4.0
- **Reason**: gemma3_text architecture support requires transformers >= 4.51.3, which needs PyTorch >= 2.4.0
- **CUDA Version**: 12.1 (cu121 builds)
- **Compatible Versions**:
  - PyTorch: 2.4.0+ to 2.5.1+cu121
  - transformers: 4.51.3+
  - sentence-transformers: 5.1.0+

### Installation Commands

#### UV Method (Recommended)

```bash
# Windows
uv pip install torch>=2.4.0 torchvision torchaudio --python .venv\Scripts\python.exe --index-url https://download.pytorch.org/whl/cu121

```

#### pip Method (Fallback)

```bash
pip install torch>=2.4.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### CUDA Index URLs

- **CUDA 12.1**: `https://download.pytorch.org/whl/cu121`
- **CUDA 11.8**: `https://download.pytorch.org/whl/cu118` (backward compatible)
- **CPU only**: `https://download.pytorch.org/whl/cpu`

## Verification & Testing

### Comprehensive Verification

The system includes a professional verification tool that tests all components:

```powershell
# Run the comprehensive verification script
verify-installation.bat

# Expected output:
# [PASS] 15 tests completed successfully
# [OVERALL] Installation is FULLY FUNCTIONAL
# System ready for Claude Code integration
```

**Verification Tests Include:**

- ✅ Virtual environment and Python version
- ✅ PyTorch CUDA availability and GPU detection
- ✅ Core dependencies (transformers, sentence-transformers, FAISS)
- ✅ Hybrid search dependencies (BM25, NLTK)
- ✅ MCP server functionality
- ✅ Multi-language parsers (Python, JS, TS, Java, Go, Rust, C, C++, C#, GLSL)
- ✅ Performance benchmark
- ✅ EmbeddingGemma model loading

### Manual Component Testing

```powershell
# Test basic imports
.venv\Scripts\python.exe -c "import torch; print('PyTorch:', torch.__version__)"

# Test CUDA functionality
.venv\Scripts\python.exe -c "import torch; print('CUDA available:', torch.cuda.is_available())"

# Start MCP server (interactive menu with 8 functional options)
start_mcp_server.bat

# Alternative launcher options
scripts\batch\start_mcp_debug.bat    # Debug mode with enhanced logging
scripts\batch\start_mcp_simple.bat   # Simple mode with minimal output
```

### Advanced Testing Tools

#### Comprehensive Test Suite

The project includes 37 test files organized into professional categories:

```powershell
# Run all tests (37 test files)
.venv\Scripts\python.exe -m pytest tests/ -v

# Unit tests only (14 files) - Fast component testing
.venv\Scripts\python.exe -m pytest tests/unit/ -v

# Integration tests only (23 files) - Workflow validation
.venv\Scripts\python.exe -m pytest tests/integration/ -v

# Run with coverage report
.venv\Scripts\python.exe -m pytest tests/ --cov=. --cov-report=html

# Quick validation test
.venv\Scripts\python.exe -m pytest tests/unit/test_imports.py -v
```

#### Test Categories

- **Unit Tests** (`tests/unit/`): Component isolation testing for search, indexing, evaluation
- **Integration Tests** (`tests/integration/`): End-to-end workflow testing for MCP, installation, CUDA
- **Test Fixtures** (`tests/fixtures/`): Reusable mocks and sample data
- **Test Data** (`tests/test_data/`): Sample projects in Python, GLSL, multi-language

#### Development Debug Tools

```powershell
# Development and debug tools available in archive
_archive/test_scripts/test-cpu-mode.bat     # CPU-only mode testing
_archive/debug_tools/debug_*.py            # Component-specific debugging

# Full test documentation
tests/README.md                            # Comprehensive test guide (285 lines)
```

📚 **Complete testing guide**: [tests/README.md](../tests/README.md)

### MCP Server Launcher Scripts

The system provides multiple launcher options for different use cases:

#### Main Launcher (start_mcp_server.bat)

```powershell
# Interactive menu with 8 functional options
start_mcp_server.bat
```

**Features:**

- Interactive menu with configuration options
- Performance benchmarking integration
- Installation and verification tools
- Project indexing and search utilities
- All menu options verified and functional

#### Debug Mode (start_mcp_debug.bat)

```powershell
# Enhanced logging and error reporting
scripts\batch\start_mcp_debug.bat
```

**Features:**

- Verbose output for troubleshooting
- Enhanced error reporting
- Debug environment variables set
- Detailed execution logging

#### Simple Mode (start_mcp_simple.bat)

```powershell
# Minimal output for production use
scripts\batch\start_mcp_simple.bat
```

**Features:**

- Minimal console output
- Suppressed debug messages
- Clean production startup
- Error-only reporting

## Performance Verification (Optional)

After successful installation, verify system performance and validate token efficiency claims:

### Quick Performance Test

```bash
# Interactive benchmark menu (Recommended)
run_benchmarks.bat
```

Select **Option 1: Token Efficiency Benchmark** for a quick validation (~10 seconds).

**Expected Results:**

- ✅ **Token Savings**: 98.6% reduction vs traditional file reading
- ✅ **GPU Acceleration**: 8.6x faster indexing (with CUDA GPU)
- ✅ **Search Quality**: High precision on test scenarios

### Individual Benchmarks

```bash
# Token efficiency only (fastest validation)
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency --max-instances 1

# Full token efficiency suite
.venv\Scripts\python.exe evaluation/run_evaluation.py token-efficiency

# Custom project evaluation
.venv\Scripts\python.exe evaluation/run_evaluation.py custom --project test_evaluation
```

### Performance Validation Checklist

- [ ] **GPU Detection**: System detects your GPU correctly
- [ ] **Token Efficiency**: Shows >99% token reduction
- [ ] **Indexing Speed**: Fast index building (seconds, not minutes)
- [ ] **Search Quality**: Finds relevant code chunks for queries
- [ ] **Memory Management**: Proper cleanup after benchmarks

**If benchmarks fail**: Check GPU drivers, verify PyTorch CUDA installation, or run with `--cpu` flag for CPU-only testing.

📊 **Complete benchmark results**: [View Detailed Benchmarks](BENCHMARKS.md)

## Troubleshooting

### Common Issues

#### 1. DLL Loading Errors

**Error**: `OSError: [WinError 193] %1 is not a valid Win32 application`

**Solution**:

```bash
# Clean installation with UV
.\scripts\batch\install_pytorch_cuda.bat
```

**Cause**: Corrupted PyTorch installation or architecture mismatch

#### 2. Version Conflicts

**Error**: `module 'torch.utils._pytree' has no attribute 'register_pytree_node'`

**Solution**:

```bash
# Ensure PyTorch >= 2.4.0
uv pip install --upgrade torch>=2.4.0 --index-url https://download.pytorch.org/whl/cu121
```

**Cause**: Old PyTorch version incompatible with newer transformers

#### 3. NumPy Compatibility

**Error**: `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.1.2`

**Solution**: UV automatically handles this, but for manual fix:

```bash
pip install "numpy<2.0"
```

#### 4. gemma3_text Architecture Error

**Error**: `The checkpoint you are trying to load has model type 'gemma3_text' but Transformers does not recognize this architecture`

**Solution**:

```bash
# Install transformers preview with EmbeddingGemma support
pip install git+https://github.com/huggingface/transformers@v4.56.0-Embedding-Gemma-preview

# Or use UV for automatic resolution
uv sync  # This will install correct transformers version
```

**Root Cause**: Standard transformers 4.51.3 doesn't include gemma3_text architecture. The v4.56.0-Embedding-Gemma-preview branch includes the required support.

### Debug Commands

```bash
# Check package versions
uv pip list | grep -E "(torch|transformers|sentence)"

# Test model loading
python -c "from sentence_transformers import SentenceTransformer; model = SentenceTransformer('google/embeddinggemma-300m'); print('Model loaded successfully')"

# Memory check
python -c "import torch; print('GPU memory:', torch.cuda.get_device_properties(0).total_memory // 1024**3, 'GB')"
```

## Performance Optimization

### GPU Acceleration

1. **CUDA Setup**
   - Install NVIDIA drivers (latest)
   - Verify CUDA toolkit compatibility
   - Use cu121 PyTorch builds for CUDA 12.1

2. **Memory Management**
   - Monitor GPU memory usage during indexing
   - Adjust batch sizes based on available VRAM
   - Clear cache after large operations

### Indexing Performance

1. **Hardware Recommendations**
   - NVIDIA RTX 4090: ~5x speedup vs CPU
   - 16GB+ VRAM for large codebases
   - SSD storage for faster file I/O

2. **Configuration Tuning**
   - Increase embedding batch size for more VRAM
   - Enable incremental indexing for large projects
   - Use FAISS GPU index for faster search

### Token Optimization Results

- **Traditional file reading**: ~5,600 tokens for 3 files
- **Semantic search**: ~400 tokens for targeted results
- **Reduction**: 93% fewer tokens used
- **Speed**: 5-10x faster than loading full files

## Maintenance

### Regular Updates

```bash
# Update the system
git pull
uv sync

# Update PyTorch if needed
.\scripts\batch\install_pytorch_cuda.bat
```

### Cache Management

```bash
# Clear embedding cache
rm -rf ~/.claude_code_search/models/

# Clear pip cache
pip cache purge

# Clear UV cache
uv cache clean
```

### Monitoring

- Check GPU memory usage with `nvidia-smi`
- Monitor disk space in `~/.claude_code_search/`
- Review MCP server logs for errors

## Support

For issues not covered in this guide:

1. Check the GitHub Issues for your repository
2. Review CLAUDE.md for project-specific documentation
3. Run diagnostic commands from the troubleshooting section
4. Provide system information when reporting bugs

---

## Quick Reference

### Essential Commands

```bash
# Install with UV (recommended)
.\scripts\batch\install_pytorch_cuda.bat

# Test installation
python test_cuda_indexing.py

# Start MCP server
start_mcp_server.bat

# Index a project
python -m mcp_server.tools index_directory "path/to/project"
```

### File Locations

- **Scripts**: `scripts/powershell/` (Windows PowerShell), `scripts/batch/` (Windows batch)
- **Configuration**: `CLAUDE.md`, `pyproject.toml`
- **Cache**: `~/.claude_code_search/`
- **Logs**: MCP server stdout/stderr
