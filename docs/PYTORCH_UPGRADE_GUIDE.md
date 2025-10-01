# PyTorch 2.6.0 Upgrade Guide

## Why Upgrade?

- **Required for BGE-M3**: torch.load security fixes required by BGE-M3 model
- **Better performance**: Optimizations in PyTorch 2.6
- **Security**: Critical vulnerabilities patched in model loading
- **Compatibility**: CUDA 11.8, 12.4, 12.6 support (improved from 2.5.1)

## Quick Upgrade

```bash
# Close all Python processes first (Claude Code, Python scripts, etc.)
upgrade_pytorch_2.6.bat
```

The script will:

1. Check virtual environment
2. Safely uninstall old PyTorch versions
3. Install PyTorch 2.6.0 with CUDA 11.8
4. Verify installation
5. Test BGE-M3 compatibility

## Manual Upgrade

If you prefer manual installation:

```bash
# Using UV (recommended)
.venv\Scripts\uv.exe pip install "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cu118

# Using pip
.venv\Scripts\python.exe -m pip install "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cu118
```

## CUDA Compatibility

| Your CUDA Version | PyTorch Build to Use | Status | Notes |
|-------------------|---------------------|--------|-------|
| 12.1-12.3 | cu118 | ✅ Recommended | Fully compatible, backward compatible |
| 12.4-12.6 | cu124 | ✅ Native | Direct CUDA 12.4 support |
| 11.8 | cu118 | ✅ Native | Direct CUDA 11.8 support |
| <11.8 | CPU only | ⚠️ GPU not supported | Use CPU-only installation |

**Why CUDA 11.8 for CUDA 12.1 systems?**

- PyTorch 2.6.0 doesn't support CUDA 12.1 directly
- CUDA 11.8 build is fully compatible with CUDA 12.x drivers
- No performance loss, complete feature parity

## Verification

After installation, verify everything works:

```bash
# Check PyTorch version
.venv\Scripts\python.exe -c "import torch; print('PyTorch:', torch.__version__)"
# Expected: PyTorch: 2.6.0+cu118

# Check CUDA support
.venv\Scripts\python.exe -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"

# Test BGE-M3 import (optional)
.venv\Scripts\python.exe -c "from FlagEmbedding import BGEM3FlagModel; print('BGE-M3 ready')"
```

## What Changed from 2.5.1?

| Aspect | PyTorch 2.5.1 | PyTorch 2.6.0 | Impact |
|--------|---------------|---------------|--------|
| **CUDA 12.1** | Supported (cu121) | Not supported | Use cu118 instead (compatible) |
| **CUDA 11.8** | Supported | Supported | No change |
| **CUDA 12.4** | Not supported | Supported (cu124) | New option |
| **CUDA 12.6** | Not supported | Supported (cu126) | New option |
| **torch.load** | Security issues | Fixed | Required for BGE-M3 |
| **BGE-M3** | ❌ Not compatible | ✅ Compatible | Enables model upgrade |

## Troubleshooting

### Issue: File locked errors during installation

**Symptom:** "Access denied" or "file locked" errors

**Solution:**

1. Close all Python processes:
   - Claude Code
   - Any Python scripts
   - Command prompts with Python
   - VS Code Python extensions
2. Check Task Manager for python.exe processes
3. Retry installation

### Issue: CUDA not detected after upgrade

**Symptom:** `torch.cuda.is_available()` returns `False`

**Solution:**

```bash
# Verify NVIDIA driver
nvidia-smi

# Check PyTorch was installed with CUDA
.venv\Scripts\python.exe -c "import torch; print(torch.version.cuda)"
# Should show: 11.8 or 12.4

# If shows None, reinstall with --index-url
.venv\Scripts\uv.exe pip install "torch==2.6.0" --index-url https://download.pytorch.org/whl/cu118
```

### Issue: BGE-M3 still shows errors after upgrade

**Symptom:** "torch.load requires PyTorch 2.6+" error persists

**Solutions:**

1. Verify PyTorch version is actually 2.6.0+:

   ```bash
   .venv\Scripts\python.exe -c "import torch; assert torch.__version__.startswith('2.6'), f'Wrong version: {torch.__version__}'"
   ```

2. Clear Python cache:

   ```bash
   .venv\Scripts\python.exe -c "import sys; import shutil; [shutil.rmtree(p, ignore_errors=True) for p in sys.path if '__pycache__' in str(p)]"
   ```

3. Reinstall FlagEmbedding:

   ```bash
   .venv\Scripts\uv.exe pip install --upgrade "FlagEmbedding>=1.3.0"
   ```

## Next Steps After Upgrade

1. **Switch to BGE-M3** (optional but recommended):

   ```bash
   start_mcp_server.bat
   # Navigate: 3 → 4 → 2
   ```

2. **Clear old indexes** (required if switching models):
   - Old Gemma indexes (768 dim) incompatible with BGE-M3 (1024 dim)
   - Menu will prompt to clear automatically

3. **Re-index projects**:

   ```bash
   # In Claude Code
   /index_directory "C:\path\to\project"
   ```

4. **Run tests** (optional verification):

   ```bash
   .venv\Scripts\python.exe -m pytest tests/integration/test_model_switching.py -v
   ```

## Rollback to 2.5.1

If you need to revert:

```bash
# Uninstall 2.6.0
.venv\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio

# Reinstall 2.5.1
.venv\Scripts\uv.exe pip install "torch==2.5.1" "torchvision==0.20.1" "torchaudio==2.5.1" --index-url https://download.pytorch.org/whl/cu121
```

**Note:** After rollback, BGE-M3 will not work. Switch back to Gemma model.

## Resources

- **Migration Guide**: `docs/MODEL_MIGRATION_GUIDE.md`
- **Benchmarks**: `docs/BENCHMARKS.md` (Gemma vs BGE-M3 comparison)
- **Troubleshooting**: `README.md` (Troubleshooting section)
- **PyTorch Docs**: <https://pytorch.org/get-started/pytorch-2-6/>

## Summary

✅ **Upgrade when:** Using BGE-M3 or want latest PyTorch features
✅ **CUDA 12.1 systems:** Use cu118 build (fully compatible)
✅ **Installation time:** ~2-5 minutes
✅ **Breaking changes:** None for Gemma users
✅ **Benefits:** BGE-M3 support, security fixes, performance improvements
