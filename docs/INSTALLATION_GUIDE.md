# Claude Context MCP Installation Guide

## Overview

This guide covers the complete installation process for the Claude Context MCP system, a general-purpose semantic code search tool for software development, including dependency management, PyTorch CUDA setup, and troubleshooting common issues.

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
- **Operating System**: Windows 10/11, macOS, or Linux
- **Disk Space**: 2-3 GB free space
  - EmbeddingGemma model: ~1.3 GB
  - PyTorch with CUDA: ~2.4 GB
  - Dependencies and cache: ~500 MB
- **Memory**: 4GB RAM minimum, 8GB+ recommended
- **GPU** (optional): NVIDIA GPU with CUDA 12.1 support

### Software Dependencies

- **Git**: For cloning the repository
- **UV Package Manager**: Recommended for dependency resolution
- **Claude Code**: For MCP integration

## Installation Methods

### Method 1: UV-Based Installation (Recommended)

**This method resolves all PyTorch+transformers dependency issues identified in September 2025.**

UV provides superior dependency resolution and is the recommended approach for complex ML packages.

#### Windows Installation

```powershell
# 1. Clone the repository
git clone https://github.com/forkni/claude-context-local.git
cd Claude-context-MCP

# 2. Clean installation from scratch (recommended)
rm -rf .venv  # Remove old environment if exists
python -m venv .venv

# 3. Install UV and run installation script
.\scripts\batch\install_pytorch_cuda.bat

# 4. Configure Claude Code
.\scripts\powershell\configure_claude_code.ps1 -Global
```

**What this provides:**

- ✅ Proper PyTorch version detection and compatibility
- ✅ transformers compatibility with PyTorch 2.5.1+cu121
- ✅ EmbeddingGemma gemma3_text architecture support
- ✅ CUDA 12.1 acceleration functionality

#### macOS/Linux Installation

```bash
# Standard installation
# Clone repository and run install script
git clone https://github.com/forkni/claude-context-local.git
cd Claude-context-MCP
./scripts/install.sh

# Manual UV installation
uv pip install torch>=2.4.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Method 2: Traditional pip Installation

```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Install PyTorch with CUDA
.\scripts\batch\install_pytorch_cuda.bat
```

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

# macOS/Linux
uv pip install torch>=2.4.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
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

### 1. Basic Installation Check

```python
# Test basic imports
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "from sentence_transformers import SentenceTransformer; print('Sentence Transformers: OK')"
python -c "from transformers import AutoModel; print('Transformers: OK')"
```

### 2. CUDA Verification

```python
# Test CUDA functionality
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU count:', torch.cuda.device_count())"
```

### 3. Full System Test

```bash
# Run the comprehensive test
python test_cuda_indexing.py
```

Expected output:

- PyTorch version: 2.5.1+cu121
- CUDA available: True
- GPU memory usage metrics
- Indexing performance stats
- Search functionality test

### 4. MCP Server Test

```bash
# Start MCP server
start_mcp_server.bat

# Expected: Server starts without errors
# Look for: "MCP Server starting up" message
```

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

- **Scripts**: `scripts/powershell/` (Windows), `scripts/` (Unix)
- **Configuration**: `CLAUDE.md`, `pyproject.toml`
- **Cache**: `~/.claude_code_search/`
- **Logs**: MCP server stdout/stderr
