# Use FAISS as the vector index backend; do not migrate to turbovec

Status: accepted
Date: 2026-05-15

We use faiss-cpu (`IndexFlatIP` for <10K vectors, `IndexIVFFlat` above) as the vector index
backend and have evaluated turbovec (TurboQuant scalar quantization, Rust + PyO3, v0.3.0) as a
possible replacement. We are not migrating: turbovec ships no Windows wheels, is alpha-status
with a single maintainer, has no GPU support and no GPU-accelerated retrieval fork on GitHub,
and its headline wins (15.8× compression, 12–20% speedup on ARM) target deployment scenarios
that do not apply to this project.

## Considered Options

- **FAISS — chosen.** Incumbent. `faiss-cpu` wheel works on Windows. GPU path available if
  needed (`faiss.index_cpu_to_all_gpus` exists in the wrapper, dormant because `faiss-cpu` is
  pinned). `IndexFlatIP` and `IndexIVFFlat` cover every corpus size we index today.
- **turbovec v0.3.0** — rejected. See below.
- **Custom GPU port of turbovec** — rejected. The only GPU-accelerated TurboQuant code on
  GitHub targets LLM KV-cache compression during inference (Triton/CUDA kernels for
  vLLM / llama.cpp). None of it is a vector-search index or drop-in for an `IndexBackend`.
  Getting GPU-turbovec for retrieval would be original engineering.

## Why not turbovec

- **No Windows wheels.** Release CI ships Linux x86_64, Linux aarch64, macOS aarch64. This
  repo is Windows-first (`install-windows.bat`, PowerShell, `.cmd` launchers). Users would
  have to build from Rust source on every fresh install.
- **Alpha quality, single maintainer.** v0.3.0, "Development Status :: 3 – Alpha", 2
  contributors (Ryan Codrai: 121/122 commits), 110 commits, last commit 2026-05-02.
- **One index type only.** Exhaustive scan over 2/3/4-bit quantized codes. No flat-IP exact
  search, no IVF, no HNSW, no PQ. Inner product / cosine only. Losing `IndexFlatIP` for
  small-N exact search would degrade recall with no configuration knob to recover it.
- **No GPU support.** Their docs admit "*trailing FAISS on NVIDIA for >10M datasets*." No
  GPU-capable retrieval fork exists on GitHub.
- **Benchmarks compare against a different baseline.** Their speed numbers are vs
  `IndexPQ` / `IndexPQFastScan` — quantized FAISS. We use unquantized `IndexFlatIP` /
  `IndexIVFFlat`. The comparison is not apples-to-apples.
- **Speed wins don't transfer.** The 12–20% gains are on Apple M3 Max (ARM, NEON). On
  x86 Windows our actual deployment), wins are ≤6% on 4-bit and −2–4% on 2-bit MT.
- **No compression driver.** Current RAM footprint: Qwen3-0.6B / BGE-M3 (d=1024) at typical
  corpus sizes is ~200 MB. Compression is solving a problem we don't have.
- **Recall loss.** R@1 on OpenAI d=1536 4-bit: turbovec 0.955 vs FAISS 0.966. GloVe d=200
  trails FAISS by 3–6 points. With no `nprobe`-equivalent to tune, recall is fixed at
  quantisation accuracy.

## Re-evaluation triggers

Revisit this decision only when **all** of the following hold:

1. turbovec ships official Windows wheels.
2. turbovec reaches "Beta" / "Production/Stable" PyPI classifier with >1 active maintainer.
3. We index corpora ≥1M chunks at d≥1536, or RAM ceiling becomes a documented pain point.
4. Either FAISS becomes unusable for us, or a GPU-capable retrieval port of TurboQuant
   appears on GitHub with meaningful adoption.
