# PyTorch Version Compatibility Guide

## Overview

This document explains PyTorch version requirements and compatibility for claude-context-local.

## Version Requirements

### Minimum Versions

- **PyTorch 2.6.0+** - Required for BGE-M3 (the default model, security fixes)
- **PyTorch 2.4.0+** - Minimum for EmbeddingGemma-300m
- **transformers >= 4.51.3** - Required for EmbeddingGemma support

These floors apply to the current 6-model registry (BGE-M3, EmbeddingGemma-300m,
Qwen3-0.6B, F2LLM-v2-0.6B, CodeRankEmbed, GTE-ModernBERT-base) — none of the
models added since this guide was written raise the minimum versions above.

### Recommended (and Enforced) Versions

- **PyTorch >=2.8.0, <2.9.0** - The only range installed by this project (see
  "Why the `<2.9.0` Ceiling?" below). Fully tested and supported ✅

## CUDA Compatibility

### CUDA Index Selection (`pyproject.toml`)

Unlike older PyTorch releases (which shipped a single `cu118` build compatible with all CUDA
12.x drivers), this project pins `torch`/`torchvision`/`torchaudio` to an **explicit CUDA-12.8
wheel index** via `[tool.uv.sources]`:

```toml
[[tool.uv.index]]
name = "pytorch-cu128"
url = "https://download.pytorch.org/whl/cu128"
explicit = true

# Legacy CUDA 12.4 index (fallback for older systems)
[[tool.uv.index]]
name = "pytorch-cu124"
url = "https://download.pytorch.org/whl/cu124"
explicit = true

[tool.uv.sources]
torch = [
    { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

- **`cu128`** is the default and recommended index — required for RTX 50-series GPUs, and works
  fine on older Ampere/Ada cards (RTX 30/40-series) too as long as the driver is new enough.
- **`cu124`** is kept in the index list as a fallback for systems with an older NVIDIA driver
  that can't satisfy `cu128`'s minimum driver requirement, but is not wired into
  `[tool.uv.sources]` by default — switch to it manually if `cu128` install fails to detect your
  GPU (see Troubleshooting below).
- Your GPU driver's CUDA version (shown in `nvidia-smi`) must be >= the wheel's CUDA version;
  newer drivers are backward compatible with older CUDA runtime wheels, not the reverse.

### Installation Examples

**Default (CUDA 12.8-capable driver):**

```batch
# uv resolves torch via the pinned pytorch-cu128 index automatically -- no extra needed
uv sync

# Result: PyTorch 2.8.x+cu128 (✅ Recommended)
```

**Older driver / cu128 unavailable:**

```batch
# Fall back to the legacy cu124 index
uv pip install torch==2.8.* torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Result: PyTorch 2.8.x+cu124
```

## Version Constraints in pyproject.toml

### Current Setup

```toml
[project]
dependencies = [
    "torch>=2.8.0,<2.9.0",
    "torchvision>=0.21.0",
    "torchaudio>=2.6.0",
]
```

### Why the `<2.9.0` Ceiling?

Unlike a typical floor-only constraint, `torch` is **capped** here — this is intentional, not an
oversight (commit `b68cfff8`):

- **PyTorch 2.9.x breaks GTE-ModernBERT on Windows**: ModernBERT's
  `@torch.compile(dynamic=True)` decorator hits a `torch.inductor` `AssertionError` (a template
  conflict in the compiled-graph cache) starting with PyTorch 2.9.0 on Windows.
- **Security trade-off, tracked and accepted**: this ceiling blocks 5 fixed CVEs (all fixed at
  `2.9.0`/`2.9.1`) plus 2 more requiring `2.10.0`/`2.13.0` — 8 CVEs total, deferred and mitigated
  (local-only tool, HTTPS/safetensors-only model loads, no untrusted `.pth` ingestion). See
  `audit_reports/deferred-cves-2026-07-30.md` and the `pyproject.toml` "Deferred (no upstream
  fix)" tracking comment for full CVE-by-CVE detail.
- **Re-check each cycle**: if pytorch/pytorch fixes the inductor regression on 2.9.x/Windows, the
  ceiling can be raised, closing most of the deferred CVEs at once.

### Acceptable Versions

| Version | Status | Notes |
| --- | --- | --- |
| 2.4.0-2.5.x | ⚠️ Works | Minimum for Gemma, but lacks BGE-M3 optimizations |
| 2.6.0-2.7.x | ⚠️ Works | Below the enforced floor; not installed by this project |
| 2.8.0-2.8.x | ✅ Recommended | The only range `pyproject.toml` allows (`>=2.8.0,<2.9.0`) |
| 2.9.0+ | ❌ Blocked | ModernBERT `torch.compile(dynamic=True)` inductor `AssertionError` on Windows |

## Installation Scenarios

### Scenario 1: Fresh Installation on a CUDA 12.8-Capable System

```
Detection: CUDA 12.8-capable driver
Installation: PyTorch 2.8.x+cu128 (via the pinned pytorch-cu128 index)
Result: ✅ FULLY COMPATIBLE
```

### Scenario 2: Patch Update Within 2.8.x

```
Before: PyTorch 2.8.0+cu128
After: PyTorch 2.8.x+cu128 (any later 2.8 patch)
Action: No index clearing required (same CUDA variant, same <2.9.0 ceiling)
Result: ✅ Seamless upgrade
```

### Scenario 3: Switching Between Models (Dimension Change)

```
Gemma (768d) → BGE-M3 (1024d)
Action: MUST clear indexes and re-index
Reason: Different embedding dimensions are incompatible
```

## Troubleshooting

### "PyTorch 2.9.x got installed and things broke"

**Status:** ⚠️ **This should not happen** — `pyproject.toml` pins `<2.9.0`

- Check `uv.lock` and `.venv` haven't drifted from the declared constraint
  (`uv sync` should always respect the ceiling)
- If it did install, downgrade: `uv lock --upgrade-package torch` then `uv sync` (uv will select
  the highest version satisfying `<2.9.0`)
- 2.9.x triggers a `torch.inductor` `AssertionError` from GTE-ModernBERT's
  `@torch.compile(dynamic=True)` decorator on Windows — this is the known, tracked reason for the
  ceiling

### "CUDA 12.8 wheel installed but my driver only supports CUDA 12.4"

**Fix:** Switch to the legacy `cu124` index for this one dependency:

```batch
.venv\Scripts\uv.exe pip install torch==2.8.* torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
```

### "torch.cuda.is_available() returns False"

**Possible Causes:**

1. CPU-only PyTorch installed
2. CUDA driver not installed
3. Wrong PyTorch variant (cpu instead of cu128/cu124)

**Fix:**

```batch
# Check current installation
.venv\Scripts\python.exe -c "import torch; print(torch.__version__)"

# If shows "2.8.x+cpu", reinstall with CUDA
.venv\Scripts\uv.exe pip install torch==2.8.* torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
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
.\verify-installation.cmd
```

## References

- PyTorch Install Guide: <https://pytorch.org/get-started/locally/>
- CUDA Compatibility: <https://pytorch.org/get-started/previous-versions/>
- BGE-M3 Requirements: <https://huggingface.co/BAAI/bge-m3>
- Deferred torch CVEs: `audit_reports/deferred-cves-2026-07-30.md`

## Summary

✅ **PyTorch 2.8.x+cu128 (via the pinned `pytorch-cu128` index) is the correct installation**
✅ **`torch>=2.8.0,<2.9.0` in pyproject.toml is intentional — the `<2.9.0` ceiling blocks a
ModernBERT `torch.compile` inductor regression on Windows, and defers 8 known CVEs (see
`audit_reports/deferred-cves-2026-07-30.md`)**
✅ **No index clearing needed when upgrading within 2.8.x**
✅ **Always clear indexes when switching embedding models**

**Last Updated:** 2026-07-30
