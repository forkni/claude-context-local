# PyTorch Version Compatibility Guide

## Overview

This document explains PyTorch version requirements and compatibility for claude-context-local.

## Version Requirements

### Minimum Versions

- **PyTorch 2.6.0+** - Required for BGE-M3 (the default model, security fixes)
- **PyTorch 2.4.0+** - Minimum for EmbeddingGemma-300m
- **transformers >= 4.51.3** - Required for EmbeddingGemma support

These floors apply to the current 4-model registry (BGE-M3, EmbeddingGemma-300m,
Qwen3-0.6B, F2LLM-v2-0.6B) — none of the models added since this guide was written
raise the minimum versions above. (`CodeRankEmbed` and `GTE-ModernBERT-base` were
removed from `MODEL_REGISTRY` in v0.23.0.)

### Recommended (and Enforced) Versions

- **PyTorch >=2.10.0, <2.11.0** - The only range installed by this project (see
  "Why `<2.11.0`?" below). Fully tested and supported ✅

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

# Result: PyTorch 2.10.x+cu128 (✅ Recommended)
```

**Older driver / cu128 unavailable:**

```batch
# Fall back to the legacy cu124 index
uv pip install torch==2.10.* torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Result: PyTorch 2.10.x+cu124
```

## Version Constraints in pyproject.toml

### Current Setup

```toml
[project]
dependencies = [
    "torch>=2.10.0,<2.11.0",
    "torchvision>=0.21.0",
    "torchaudio>=2.6.0",
]
```

### Why `<2.11.0`?

`torch` is **capped** at the next major boundary rather than left floor-only, matching the
project's index-availability constraint — this is intentional (commit history: `b68cfff8`
introduced the original `<2.9.0` ceiling, lifted 2026-08-06, see `docs/adr/0033-lift-torch-ceiling.md`):

- **The original `<2.9.0` ceiling is gone.** It existed because GTE-ModernBERT's
  `@torch.compile(dynamic=True)` decorator hit a `torch.inductor` `AssertionError` on PyTorch
  2.9.x/Windows. That rationale is now empirically dead on both legs: the GTE-ModernBERT
  **embedder** it protected was deleted from `MODEL_REGISTRY` in commit `24f6b8c` (2026-07-31),
  and the pinned `transformers>=5.3.0` floor **removed ModernBERT's `reference_compile` path
  entirely** (`grep torch.compile` over `transformers/models/modernbert/*.py` in the installed
  package returns nothing). The project itself never calls `torch.compile` — the only `_dynamo`
  hit in the codebase is a log suppressor (`mcp_server/server.py:207`), and nine benchmark logs
  showed TorchDynamo tracing zero frames even before the ceiling was lifted.
- **Security improvement**: lifting the ceiling to `2.10.0` closed 6 of 8 tracked CVEs, including
  both CVSS 8.8 `weights_only` unpickler bypasses (`CVE-2025-3001`... — see correction below,
  `CVE-2026-24747`). See the `pyproject.toml` "Deferred (no upstream fix)" tracking comment for
  the 2 CVEs that remain (`CVE-2026-4538`: no fix at any version; `CVE-2025-3000`: fixed in
  `2.13.0`, which the pinned `cu128` index does not publish).

  > **Correction**: an earlier version of this rationale (and of the pre-upgrade audit trail)
  > described `CVE-2025-3001` as a second `weights_only` unpickler bypass alongside
  > `CVE-2026-24747`. That's wrong — `CVE-2025-3001` is a `torch.lstm_cell` memory-corruption
  > bug, unrelated to unpickling. Only `CVE-2026-24747` is a `weights_only` bypass. Both are
  > fixed by `2.10.0`; the CVE *count* closed (6 of 8) was correct throughout, only the
  > characterization of `CVE-2025-3001` was mischaracterized.
- **New ceiling rationale**: `[tool.uv.sources]` pins `torch` to the explicit `pytorch-cu128`
  index, which tops out at `2.11.0` (PyPI itself has newer releases, but the CUDA-12.8 wheel
  index does not publish them) — `<2.11.0` reflects that hard platform limit, not a known
  regression. There is no known reason to avoid `2.11.0`+ once the index publishes it; re-check
  each cycle and raise the ceiling opportunistically.

### Acceptable Versions

| Version | Status | Notes |
| --- | --- | --- |
| 2.4.0-2.5.x | ⚠️ Works | Minimum for Gemma, but lacks BGE-M3 optimizations |
| 2.6.0-2.9.x | ⚠️ Works | Below the enforced floor; not installed by this project |
| 2.10.0-2.10.x | ✅ Recommended | The only range `pyproject.toml` allows (`>=2.10.0,<2.11.0`) |
| 2.11.0+ | ⚠️ Unpublished | Not yet available on the pinned `cu128` index; no known blocker once it lands |

## Installation Scenarios

### Scenario 1: Fresh Installation on a CUDA 12.8-Capable System

```
Detection: CUDA 12.8-capable driver
Installation: PyTorch 2.10.x+cu128 (via the pinned pytorch-cu128 index)
Result: ✅ FULLY COMPATIBLE
```

### Scenario 2: Patch Update Within 2.10.x

```
Before: PyTorch 2.10.0+cu128
After: PyTorch 2.10.x+cu128 (any later 2.10 patch)
Action: No index clearing required (same CUDA variant, same <2.11.0 ceiling)
Result: ✅ Seamless upgrade
```

### Scenario 3: Switching Between Models (Dimension Change)

```
Gemma (768d) → BGE-M3 (1024d)
Action: MUST clear indexes and re-index
Reason: Different embedding dimensions are incompatible
```

## Troubleshooting

### "PyTorch 2.11.x got installed and things broke"

**Status:** ⚠️ **This should not happen** — `pyproject.toml` pins `<2.11.0`

- Check `uv.lock` and `.venv` haven't drifted from the declared constraint
  (`uv sync` should always respect the ceiling)
- If it did install, downgrade: `uv lock --upgrade-package torch` then `uv sync` (uv will select
  the highest version satisfying `<2.11.0`)
- The `<2.11.0` ceiling reflects the pinned `cu128` index's current maximum, not a known
  regression — if you hit a real 2.11.x incompatibility, document it here before assuming it's
  just the platform-availability ceiling

### "CUDA 12.8 wheel installed but my driver only supports CUDA 12.4"

**Fix:** Switch to the legacy `cu124` index for this one dependency:

```batch
.venv\Scripts\uv.exe pip install torch==2.10.* torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124 --force-reinstall
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

# If shows "2.10.x+cpu", reinstall with CUDA
.venv\Scripts\uv.exe pip install torch==2.10.* torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128 --force-reinstall
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
- Torch CVE ledger and ceiling history: `pyproject.toml` "Deferred (no upstream fix)" tracking
  comment, `docs/adr/0033-lift-torch-ceiling.md`

## Summary

✅ **PyTorch 2.10.x+cu128 (via the pinned `pytorch-cu128` index) is the correct installation**
✅ **`torch>=2.10.0,<2.11.0` in pyproject.toml — the `<2.11.0` ceiling reflects the pinned
`cu128` index's current maximum, not a known regression; the old ModernBERT-inductor rationale
was disproved and lifted 2026-08-06 (see `docs/adr/0033-lift-torch-ceiling.md`)**
✅ **No index clearing needed when upgrading within 2.10.x**
✅ **Always clear indexes when switching embedding models**

**Last Updated:** 2026-08-06
