# GPU Determinism Arm — A/B Record (2026-08-02)

Arm A of the post-recall-campaign plan: pin deterministic CUDA kernel paths
(`torch.use_deterministic_algorithms(True)` + `CUBLAS_WORKSPACE_CONFIG=:4096:8` +
cuDNN determinism flags) behind a new `performance.deterministic_gpu` knob, and gate
on whether identical benchmark rounds stop flipping.

**Verdict: the GPU pin is REJECTED as the reproducibility mechanism — and the
inherited "kernel-layer noise" theory from the fp32 arm is corrected. The entire
round-to-round flip phenomenon is Python hash randomization (`PYTHONHASHSEED`),
not CUDA kernels.** Pinning the hash seed alone produces bit-identical rounds at
zero latency cost; the GPU pin adds ~2–4% latency and changes nothing.

## Setup

- Substrate: index @ 2,286 chunks (post-ADR-0020 source, commit `a2e7edf` knob
  changeset; no search-path edits during any round — freeze held throughout).
- Knob: `performance.deterministic_gpu` (default `False` = byte-identical),
  `utils/determinism.py::apply_gpu_determinism`, applied before first model load.
  Benchmark flag `--deterministic-gpu` (strict, `warn_only=False` unless
  `--determinism-warn-only`).
- Strict-mode smoke (A2): 5 queries through the full funnel with
  `warn_only=False` — **no RuntimeError**. Every op in the funnel (F2LLM-v2-0.6B
  embedder, jina-reranker-v3 listwise passes, FAISS/BM25 fusion) has a
  deterministic implementation. This fact became the key diagnostic below.
- Rounds: fresh process per round (`run_sscg_benchmark.py`), sequential on idle
  RTX 4090, MCP server GPU hold released first.

## A3 result: GPU pin does not reduce flips

Identical-round pairs, `analyze_dtype_determinism.py`:

| Pair (same arm, r1 vs r2)         | MRR flips | pool_hit flips | MRR spread | avg latency |
|-----------------------------------|-----------|----------------|------------|-------------|
| bf16 control 131q (canon pair)    | 25        | 4              | 0.0199     | 4,464 / 4,437 ms |
| **detgpu 131q**                   | **25**    | **4**          | 0.0146     | 4,659 / 4,646 ms |
| bf16 control 63q (canon pair)     | 6         | 1              | 0.0359     | 4,461 / 4,480 ms |
| **detgpu 63q**                    | **3**     | **0**          | 0.0176     | 4,553 / 4,635 ms |

Identical flip counts on the 131q pair (25/25, 4/4). The 63q halving (6→3) is
small-n. Material flips (|Δmrr| ≥ 0.25): bf16 5, detgpu 7 — if anything, worse.
Latency cost of the pin: **+2–4%**. Gate (material flips → ~0, pool_hit flips 0)
**FAILED**.

## Diagnosis: the flips were never kernel noise

The strict smoke is the tell. `warn_only=False` raising nothing means every op
has a deterministic implementation, so a *single process* re-running the same
query stream reproduces bit-identically — yet *separate processes* flip. The
non-determinism therefore lives in per-process state that changes the **inputs**
to (deterministic) kernels. Prime suspect: Python hash randomization. Chunk-ID
`set`s iterate in a per-process order, and the funnel truncates mid-iteration
(graph expansion discovery order, "Capping ego-graph neighbors: 45 → 20"), so
candidate-pool *composition* varies per process; the listwise rerank cascade
amplifies composition deltas into MRR flips. This is the same pool-composition
cascade the fp32 arm identified — but the seed of the variance is `hash()`, not
cuBLAS reduction order.

## Falsification probe: PYTHONHASHSEED=0

4×63q, factorial over the two candidate levers:

| Pair (r1 vs r2)              | MRR flips | pool_hit flips | all-metric spread | avg latency |
|------------------------------|-----------|----------------|-------------------|-------------|
| PYTHONHASHSEED=0 + detgpu    | **0**     | **0**          | **0.0000**        | 4,596 / 4,613 ms |
| PYTHONHASHSEED=0 only        | **0**     | **0**          | **0.0000**        | 4,419 / 4,421 ms |

Both pairs: bit-identical rounds — MRR μ 0.7942, recall@10 0.7795, recall@20
0.8465, pool_hit 1.0, exactly reproduced. Cross-pair check (hs0-only r1 vs
hs0+detgpu r1): **0 flips, 0 spread** — the GPU pin does not change a single
per-query result even at the fourth decimal. bf16 cuBLAS/SDPA kernels are
already cross-process deterministic for identical inputs on this stack.

Conclusion: **hash-seed pinning is necessary and sufficient; the GPU pin is
neither.** Its only measurable effect is +2–4% latency (4,605 vs 4,420 ms avg).

## 131q verification + new canons

2×131q, `PYTHONHASHSEED=0`, no GPU pin: **0 MRR flips, 0 pool_hit flips,
0.0000 spread on every metric** — MRR μ **0.6527**, recall@10 0.7839, recall@20
0.8365, pool_hit_rate 0.9618, latency 4,471/4,453 ms (indistinguishable from
unpinned bf16 ~4,450 ms; zero cost). vs the bf16 canon rounds: MRR +0.0017 /
+0.0216, recall@10 −0.0154 / +0.0032 — quality flat-to-positive, within band.

**Realization-freeze effect** (inherent to pinning, not a regression): each
bimodal flapper collapses onto one side under a fixed seed. Seed 0 froze
Q106 (1.0→0.0 vs both canon rounds), H067, H050 unfavorably and Q102 (0→1.0),
Q126, Q127, H054, Q90 favorably; the aggregate nets flat-positive. Any lever
that changes seed-0's pool composition will shift individual flappers — judge
future arms on replicated deltas against the deterministic canon, which are now
exact (any nonzero per-query delta is a real effect of the change under test).

**New canons (supersede the post-ADR-0020 flapper-band canons):**

- 63q: `sscg_hs0_only_63q_r{1,2}_20260802.json` — MRR **0.7942**, recall@10
  0.7795, recall@20 0.8465, pool_hit 1.0
- 131q: `sscg_hs0_expanded_r{1,2}_20260802.json` — MRR **0.6527**, recall@10
  0.7839, recall@20 0.8365, pool_hit 0.9618

Comparability break vs all prior (unpinned) baselines is deliberate and final.
The flapper list, the 2-agreeing-rounds promotion rule, and same-substrate
cross-checking retire **for benchmark work** (they remain the right lens when
reading pre-2026-08-02 records).

## Disposition (A4)

1. **Benchmark harness pins the hash seed** — `run_sscg_benchmark.py` re-execs
   itself with `PYTHONHASHSEED=0` when the variable is unset (any explicit
   caller value, including `random`, is respected as the escape hatch). One
   round per arm is now sufficient in principle; a second round stays cheap
   insurance against environment drift.
2. **`--deterministic-gpu` stays opt-in** (never defaulted): it is a
   measured no-op on results with a +2–4% latency cost. Retained as a
   diagnostic for future GPU-stack changes (e.g. verifying a new torch/CUDA
   version still runs strict-deterministic end to end).
3. **`performance.deterministic_gpu` is NOT promoted to production** — it
   stays `False` in the dataclass default, the deployed config, and the
   example config. The knob and `utils/determinism.py` remain (harmless,
   default-off, precedent: `listwise_dtype`).
4. **Production MCP server stays unpinned.** Within one server process results
   are already reproducible (one process = one hash seed); cross-restart
   variance is quality-neutral pool re-realization. Pinning
   `PYTHONHASHSEED` at server launch is available as a zero-cost option if
   cross-restart reproducibility ever matters operationally.
5. **fp32-arm record corrected**: the pool-composition cascade mechanism
   stands; the root attribution moves from cuBLAS reduction order to Python
   hash randomization. The fp32 REJECTED verdict is unaffected (fp32's own
   round spread was measured under unpinned seeds like everything else, and
   dtype remains irrelevant to determinism).

See `docs/adr/0021-benchmark-hash-seed-determinism.md`.

## Files

- Rounds: `benchmark_results/sscg_detgpu_{63q,expanded}_r{1,2}_20260802.json`,
  `benchmark_results/sscg_hs0_detgpu_63q_r{1,2}_20260802.json`,
  `benchmark_results/sscg_hs0_only_63q_r{1,2}_20260802.json`,
  `benchmark_results/sscg_hs0_expanded_r{1,2}_20260802.json`
- Baselines: `benchmark_results/sscg_post_adr0020_{63q,expanded}_r{1,2}_20260802.json`
- Analyzer: `scripts/benchmark/analyze_dtype_determinism.py`
- Prior art corrected: `evaluation/RERANKER_FP32_DETERMINISM_AB_20260802.md`
  (its "cuBLAS reduction order" attribution; its *pool-cascade* mechanism stands)
