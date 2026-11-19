# PyTorch Version Compatibility Guide

## Overview

This document explains PyTorch version requirements and compatibility for claude-context-local.

## Version Requirements

### Model Compatibility Floors

These are the floors the *models* need. The versions a fresh install actually gets are set by
`pyproject.toml` (the source of truth for the `torch`, `transformers`, and `sentence-transformers`
ranges) and `uv.lock`, and are intentionally not copied here.

- **PyTorch 2.6.0+** - Required for BGE-M3 (the default model, security fixes)
- **PyTorch 2.4.0+** - Minimum for EmbeddingGemma-300m
- **transformers >= 4.51.3** - Required for EmbeddingGemma support

These floors apply to the current 4-model registry (BGE-M3, EmbeddingGemma-300m,
Qwen3-0.6B, F2LLM-v2-0.6B) — none of the models added since this guide was written
raise the minimum versions above. (`CodeRankEmbed` and `GTE-ModernBERT-base` were
removed from `MODEL_REGISTRY` in v0.23.0.)

### Recommended (and Enforced) Versions

- **PyTorch >=2.13.0, <2.14.0** - The only range installed by this project (see
  "Why `<2.14.0`?" below). Fully tested and supported ✅

## CUDA Compatibility

### CUDA Index Selection (`pyproject.toml`)

This project pins `torch` to an **explicit CUDA-13.0 wheel index** via `[tool.uv.sources]`:

```toml
[[tool.uv.index]]
name = "pytorch-cu130"
url = "https://download.pytorch.org/whl/cu130"
explicit = true

# CUDA 12.6 index (fallback for drivers without CUDA 13.0 support)
[[tool.uv.index]]
name = "pytorch-cu126"
url = "https://download.pytorch.org/whl/cu126"
explicit = true

[tool.uv.sources]
torch = [
    { index = "pytorch-cu130", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
```

- **`cu130`** is the default index. It needs an NVIDIA driver that supports CUDA 13.0
  (R580 or newer). It works on RTX 30/40/50-series cards.
- **`cu126`** is kept in the index list as a fallback for an older driver (R560 to R579) that
  cannot run `cu130` wheels. It is not wired into `[tool.uv.sources]` by default: switch to it
  manually if the `cu130` install does not detect your GPU (see Troubleshooting below).
- The `cu128` index used before 2026-11-18 stops at `torch 2.11.0`, and `cu124` publishes no
  build for this range, so neither can serve the current pin.
- The wheel bundles its own CUDA runtime and cuDNN; no CUDA Toolkit install is needed. Your
  driver's CUDA version (shown in `nvidia-smi`) must be >= the wheel's CUDA version; newer
  drivers are backward compatible with older CUDA runtime wheels, not the reverse.

### Installation Examples

**Default (driver R580 or newer):**

```batch
# uv resolves torch via the pinned pytorch-cu130 index automatically -- no extra flags needed
uv sync

# Result: PyTorch 2.13.x+cu130 (✅ Recommended)
```

**Older driver (R560 to R579):**

```batch
# Fall back to the cu126 index
uv pip install torch==2.13.* --index-url https://download.pytorch.org/whl/cu126

# Result: PyTorch 2.13.x+cu126
```

## Version Constraints in pyproject.toml

### Current Setup

```toml
[project]
dependencies = [
    "torch>=2.13.0,<2.14.0",
]
```

`torchvision` and `torchaudio` are not project dependencies and are not required by the codebase.

### Why `<2.14.0`?

`torch` is **capped** at the next minor boundary rather than left floor-only, so a torch move
always goes through a retrieval A/B. This is intentional (commit history: `b68cfff8` introduced
the original `<2.9.0` ceiling, lifted 2026-08-06, see `docs/adr/0033-lift-torch-ceiling.md`):

- **The original `<2.9.0` ceiling is gone.** It existed because GTE-ModernBERT's
  `@torch.compile(dynamic=True)` decorator hit a `torch.inductor` `AssertionError` on PyTorch
  2.9.x/Windows. That rationale is now empirically dead on both legs: the GTE-ModernBERT
  **embedder** it protected was deleted from `MODEL_REGISTRY` in commit `24f6b8c` (2026-07-31),
  and the pinned `transformers>=5.3.0` floor (since raised; see `pyproject.toml`) **removed ModernBERT's `reference_compile` path
  entirely** (`grep torch.compile` over `transformers/models/modernbert/*.py` in the installed
  package returns nothing). The project itself never calls `torch.compile` — the only `_dynamo`
  hit in the codebase is a log suppressor (`mcp_server/server.py:207`), and nine benchmark logs
  showed TorchDynamo tracing zero frames even before the ceiling was lifted.
- **Security**: `2.11.0` closed 7 of 8 tracked CVEs, including both CVSS 8.8
  `weights_only` unpickler bypasses (`CVE-2026-24747`; see correction below re: `CVE-2025-3001`)
  and `CVE-2026-4538` (`PYSEC-2026-139`, a `pt2` loader deserialization issue). `2.13.0` closes
  the last one, `CVE-2025-3000` (`torch.jit.script` memory corruption).

  > **Correction**: an earlier version of this rationale (and of the pre-upgrade audit trail)
  > described `CVE-2025-3001` as a second `weights_only` unpickler bypass alongside
  > `CVE-2026-24747`. That's wrong — `CVE-2025-3001` is a `torch.lstm_cell` memory-corruption
  > bug, unrelated to unpickling. Only `CVE-2026-24747` is a `weights_only` bypass. Both were
  > fixed by `2.10.0`; the CVE count closed was correct throughout, only the characterization of
  > `CVE-2025-3001` was mischaracterized.
  >
  > **Second correction (same day)**: the initial `2.10.0` adoption pass claimed
  > `CVE-2026-4538` had "no upstream fix at any version" and closed the ledger at 6 of 8. That
  > was wrong — `pip-audit`'s default OSV lookup silently drops findings for local-version wheels
  > like `torch==2.10.0+cu128` (no `skip_reason`, the entry is just absent from the report).
  > Querying the OSV API directly (`https://api.osv.dev/v1/vulns/PYSEC-2026-139`) shows
  > `last_affected: "2.10.0"` with a merged fix PR (`pytorch/pytorch#176791`) — i.e. `2.10.0`
  > was still vulnerable, and `2.11.0` is the version that actually closes it. **Always verify
  > torch CVE claims against the raw OSV API, not just `pip-audit`'s report, when the installed
  > wheel carries a local version suffix.**
- **2026-11-18 move to `2.13.0` / `cu130`**: the old `<2.12.0` ceiling followed the `cu128`
  index, which never published `2.12`+. The pin moved to the `cu130` index instead. Retrieval
  A/B: `evaluation/TORCH213_DEP_BUNDLE_AB_20261118.md` (no ranking change on a shared index,
  within noise after a reindex, 30-50% lower search latency). `2.14.x` is published on `cu130`
  too; raise the ceiling only after the same A/B.
- **setuptools side effect resolved**: `torch==2.11.0` declared `setuptools<82`, which held the
  venv's `setuptools` at `81.0.0` (`CVE-2026-59890`, `GHSA-xmj3-9gf7-h52w`). `2.13.0` drops
  that cap, and the lock now resolves `setuptools 84.2.1`.

### Acceptable Versions

| Version | Status | Notes |
| --- | --- | --- |
| 2.4.0-2.5.x | ⚠️ Works | Minimum for Gemma, but lacks BGE-M3 optimizations |
| 2.6.0-2.12.x | ⚠️ Works | Below the enforced floor; not installed by this project |
| 2.13.0-2.13.x | ✅ Recommended | The only range `pyproject.toml` allows (`>=2.13.0,<2.14.0`) |
| 2.14.0+ | ⚠️ Not adopted | Published on `cu130`; needs a retrieval A/B before the ceiling moves |

## Installation Scenarios

### Scenario 1: Fresh Installation on a System with Driver R580+

```
Detection: driver supports CUDA 13.0
Installation: PyTorch 2.13.x+cu130 (via the pinned pytorch-cu130 index)
Result: ✅ FULLY COMPATIBLE
```

### Scenario 2: Patch Update Within 2.13.x

```
Before: PyTorch 2.13.0+cu130
After: PyTorch 2.13.x+cu130 (any later 2.13 patch)
Action: No index clearing required (same CUDA variant, same <2.14.0 ceiling)
Result: ✅ Seamless upgrade
```

### Scenario 3: Switching Between Models (Dimension Change)

```
Gemma (768d) → BGE-M3 (1024d)
Action: MUST clear indexes and re-index
Reason: Different embedding dimensions are incompatible
```

## Troubleshooting

### "PyTorch 2.14.x got installed and things broke"

**Status:** ⚠️ **This should not happen** — `pyproject.toml` pins `<2.14.0`

- Check `uv.lock` and `.venv` haven't drifted from the declared constraint
  (`uv sync` should always respect the ceiling)
- If it did install, downgrade: `uv lock --upgrade-package torch` then `uv sync` (uv will select
  the highest version satisfying `<2.14.0`)

### "cu130 wheel installed but my driver does not support CUDA 13.0"

**Fix:** Update the NVIDIA driver to R580 or newer, or switch to the `cu126` index for this
one dependency (driver R560 or newer):

```batch
.venv\Scripts\uv.exe pip install torch==2.13.* --index-url https://download.pytorch.org/whl/cu126 --force-reinstall
```

### "torch.cuda.is_available() returns False"

**Possible Causes:**

1. CPU-only PyTorch installed
2. CUDA driver not installed, or older than R580 for `cu130` wheels
3. Wrong PyTorch variant (cpu instead of cu130/cu126)

**Fix:**

```batch
# Check current installation
.venv\Scripts\python.exe -c "import torch; print(torch.__version__)"

# If shows "2.13.x+cpu", reinstall with CUDA
.venv\Scripts\uv.exe pip install torch==2.13.* --index-url https://download.pytorch.org/whl/cu130 --force-reinstall
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
- Torch CVE ledger and ceiling history: `pyproject.toml` security tracking comment,
  `docs/adr/0033-lift-torch-ceiling.md`, `evaluation/TORCH213_DEP_BUNDLE_AB_20261118.md`

## Summary

✅ **PyTorch 2.13.x+cu130 (via the pinned `pytorch-cu130` index) is the correct installation**
✅ **`torch>=2.13.0,<2.14.0` in pyproject.toml — the ceiling holds each torch move to a
retrieval A/B; the old ModernBERT-inductor rationale was disproved and lifted 2026-08-06 (see
`docs/adr/0033-lift-torch-ceiling.md`)**
✅ **Driver R580+ for `cu130`; `cu126` is the fallback for R560 to R579**
✅ **No index clearing needed when upgrading within 2.13.x**
✅ **Always clear indexes when switching embedding models**

**Last Updated:** 2026-11-18
