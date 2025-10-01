# PyTorch Version Compatibility Guide

## Overview

This document explains PyTorch version requirements and compatibility for claude-context-local.

## Version Requirements

### Minimum Versions
- **PyTorch 2.6.0+** - Required for BGE-M3 model (security fixes)
- **PyTorch 2.4.0+** - Minimum for EmbeddingGemma-300m
- **transformers >= 4.51.3** - Required for EmbeddingGemma support

### Recommended Versions
- **PyTorch 2.6.0 - 2.7.x** - Fully tested and supported
- **PyTorch 2.7.1** - Latest version, fully compatible ✅

## CUDA Compatibility

### PyTorch 2.6.0+ CUDA Support
PyTorch 2.6.0 and later only provide CUDA 11.8 builds (`cu118`), which are **fully backward and forward compatible** with:
- CUDA 11.7, 11.8
- **CUDA 12.0, 12.1, 12.2, 12.3, 12.4, 12.6** (all CUDA 12.x versions)

### Why cu118 for CUDA 12.x?
This is **intentional and correct**:
- PyTorch no longer provides cu121, cu124, etc. builds
- The cu118 build uses backward-compatible CUDA runtime
- Your GPU driver's CUDA version (shown in nvidia-smi) is what matters
- Driver CUDA 12.x can run PyTorch cu118 binaries without issues

### Installation Examples

**CUDA 12.1 System:**
```batch
# Correct installation (uses cu118)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Result: PyTorch 2.7.1+cu118 (✅ Works perfectly with CUDA 12.1)
```

**CUDA 11.8 System:**
```batch
# Uses cu118 (native support)
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Result: PyTorch 2.7.1+cu118 (✅ Native support)
```

## Version Constraints in pyproject.toml

### Current Setup
```toml
[project]
dependencies = [
    "torch>=2.6.0",
    "torchvision>=0.21.0",
    "torchaudio>=2.6.0",
]
```

### Why `>=2.6.0` Instead of `==2.6.0`?
- **Security updates**: Allows automatic security fixes (2.6.1, 2.7.0, 2.7.1)
- **Bug fixes**: Minor version updates include important stability improvements
- **API stability**: PyTorch maintains backward compatibility within major versions
- **UV package manager**: Automatically selects the latest compatible version

### Acceptable Versions
| Version | Status | Notes |
|---------|--------|-------|
| 2.4.0-2.5.x | ⚠️ Works | Minimum for Gemma, but lacks BGE-M3 optimizations |
| 2.6.0 | ✅ Recommended | First version with BGE-M3 security fixes |
| 2.6.1 | ✅ Recommended | Security patches |
| 2.7.0 | ✅ Recommended | Latest minor version |
| 2.7.1 | ✅ Recommended | Latest patch (as of 2025-10-01) |
| 3.0.0+ | ❓ Unknown | Not yet released; may require code changes |

## Installation Scenarios

### Scenario 1: Fresh Installation on CUDA 12.1 System
```
Detection: CUDA 12.1 detected
Installation: PyTorch 2.7.1+cu118
Result: ✅ FULLY COMPATIBLE
```

**Why this works:**
- CUDA 12.1 driver supports CUDA 11.8 runtime
- PyTorch cu118 binaries run natively on CUDA 12.x drivers
- No performance penalty

### Scenario 2: Update from PyTorch 2.6.0 to 2.7.1
```
Before: PyTorch 2.6.0+cu118
After: PyTorch 2.7.1+cu118
Action: No index clearing required (same CUDA variant)
Result: ✅ Seamless upgrade
```

### Scenario 3: Switching Between Models (Dimension Change)
```
Gemma (768d) → BGE-M3 (1024d)
Action: MUST clear indexes and re-index
Reason: Different embedding dimensions are incompatible
```

## Troubleshooting

### "PyTorch 2.7.1 installed but expected 2.6.0"
**Status:** ✅ **This is normal and correct**
- `pyproject.toml` specifies `>=2.6.0`
- UV installs the latest compatible version (2.7.1)
- 2.7.1 includes all 2.6.0 features plus improvements
- **No action needed**

### "CUDA 11.8 installed but I have CUDA 12.1"
**Status:** ✅ **This is correct**
- PyTorch 2.6.0+ only provides cu118 builds
- cu118 binaries work with CUDA 12.x drivers
- This is PyTorch's official recommendation
- **No action needed**

### "torch.cuda.is_available() returns False"
**Possible Causes:**
1. CPU-only PyTorch installed
2. CUDA driver not installed
3. Wrong PyTorch variant (cpu instead of cu118)

**Fix:**
```batch
# Check current installation
.venv\Scripts\python.exe -c "import torch; print(torch.__version__)"

# If shows "2.7.1+cpu", reinstall with CUDA
.venv\Scripts\uv.exe pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
```

## Verification Commands

### Check PyTorch Version
```batch
.venv\Scripts\python.exe -c "import torch; print('PyTorch:', torch.__version__)"
```

### Check CUDA Support
```batch
.venv\Scripts\python.exe -c "import torch; print('CUDA:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

### Full System Check
```batch
.\verify-installation.bat
```

## References

- PyTorch Install Guide: https://pytorch.org/get-started/locally/
- CUDA Compatibility: https://pytorch.org/get-started/previous-versions/
- BGE-M3 Requirements: https://huggingface.co/BAAI/bge-m3

## Summary

✅ **PyTorch 2.7.1+cu118 is the correct installation for CUDA 12.x systems**
✅ **Version `>=2.6.0` in pyproject.toml is intentional**
✅ **No index clearing needed when upgrading within same CUDA variant**
✅ **Always clear indexes when switching embedding models**

**Last Updated:** 2025-10-01
