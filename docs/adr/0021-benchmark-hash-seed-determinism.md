# Benchmark determinism: pin PYTHONHASHSEED, reject the GPU kernel pin

Status: accepted
Date: 2026-08-02

Round-to-round MRR flips between identical benchmark rounds (~25/131 queries,
the noise floor that forced the flapper list and the 2-agreeing-rounds rule)
are caused by Python hash randomization, not GPU kernel non-determinism.
`run_sscg_benchmark.py` now re-execs itself with `PYTHONHASHSEED=0` when the
variable is unset, making rounds bit-identical at zero latency cost. The
`performance.deterministic_gpu` knob shipped for this arm is retained as an
opt-in diagnostic but rejected for any default: it is a measured no-op on
results with a +2–4% latency cost.

## Context

The fp32 reranker arm (`evaluation/RERANKER_FP32_DETERMINISM_AB_20260802.md`)
established that the flips were not weight precision and attributed them to
"cuBLAS reduction order cascading through the listwise rerank pool." This arm
tested that attribution directly by pinning the deterministic kernel paths —
`torch.use_deterministic_algorithms(True)` (strict, `warn_only=False`),
`CUBLAS_WORKSPACE_CONFIG=:4096:8`, cuDNN determinism — behind a new
`performance.deterministic_gpu` config knob and a `--deterministic-gpu`
benchmark flag (commit `a2e7edf`).

Two observations broke the kernel theory:

1. **Strict mode never raised.** Every op in the funnel has a deterministic
   implementation, so a single process re-running the same queries reproduces
   bit-identically. The flips only appear across processes.
2. **The pin changed nothing.** 2×131q with the pin: 25 MRR flips / 4 pool_hit
   flips — exactly the bf16 control's counts on the same substrate.

Non-determinism that survives deterministic kernels but varies per process must
live in per-process state that changes kernel *inputs*. The funnel iterates
`set`s of chunk IDs and truncates mid-iteration (graph-expansion discovery
order, ego-neighbor capping), and `str` hashing — hence set iteration order —
is randomized per process. Different pool composition per process, amplified by
the listwise rerank cascade, is the flip mechanism. The fp32 arm's cascade
model was right; its seed was wrong.

## Decision

- **Pin `PYTHONHASHSEED=0` in the benchmark harness.** `run_sscg_benchmark.py`
  re-execs itself with the variable set when unset; any explicit caller value
  (including `random`) is respected as the escape hatch.
- **Adopt the deterministic rounds as new canons** — 63q MRR μ 0.7942
  (`sscg_hs0_only_63q_r{1,2}_20260802.json`), 131q MRR μ 0.6527
  (`sscg_hs0_expanded_r{1,2}_20260802.json`). Deliberate comparability break
  with all unpinned baselines. The flapper list and 2-agreeing-rounds rule
  retire for benchmark work.
- **Keep `--deterministic-gpu` and `performance.deterministic_gpu` opt-in,
  default off, everywhere.** No production promotion. The helper
  (`utils/determinism.py`) stays as a diagnostic (e.g. re-validating strict
  determinism after a torch/CUDA upgrade), precedent `listwise_dtype`.
- **Leave the production MCP server unpinned.** One long-lived process has one
  hash seed, so live sessions are already internally consistent; cross-restart
  pool re-realization is quality-neutral.

## Evidence

Factorial over the two candidate levers, identical-round pairs
(`analyze_dtype_determinism.py`):

| Arm                          | Dataset | MRR flips | pool_hit flips | spread | latency |
|------------------------------|---------|-----------|----------------|--------|---------|
| bf16 unpinned (control)      | 131q    | 25        | 4              | 0.0199 | ~4,450 ms |
| GPU pin only                 | 131q    | 25        | 4              | 0.0146 | ~4,650 ms |
| hash seed only               | 131q    | **0**     | **0**          | 0.0000 | ~4,460 ms |
| hash seed only               | 63q     | **0**     | **0**          | 0.0000 | ~4,420 ms |
| hash seed + GPU pin          | 63q     | **0**     | **0**          | 0.0000 | ~4,600 ms |

Cross-check: hash-seed-only vs hash-seed+GPU-pin rounds are per-query
identical (0 flips) — bf16 cuBLAS/SDPA kernels on this stack are already
cross-process deterministic for identical inputs; the GPU pin buys nothing and
costs 2–4%. Quality vs the unpinned canons is flat-to-positive (131q MRR
+0.0017/+0.0216; 63q within band). Full tables and the realization-freeze
analysis (which flappers froze on which side under seed 0):
`evaluation/GPU_DETERMINISM_AB_20260802.md`.

## Consequences

- A/B arms need one round per arm in principle (two stay cheap insurance);
  any nonzero per-query delta against the deterministic canon is a real effect
  of the change under test. Attribution machinery built for the unpinned era
  (flapper cross-referencing, quality-neutral control arms for drift) is no
  longer needed for benchmark work — but remains the correct lens when reading
  pre-2026-08-02 records, which all carry unpinned-seed noise.
- Seed 0 is one arbitrary-but-fixed realization of every set-iteration
  tie-break. Per-query values on boundary queries (Q106 frozen to 0.0, Q102
  frozen to 1.0, etc.) are properties of the pinned realization, not stable
  facts about quality; aggregate comparisons remain the decision basis.
- Any future change to iteration order (e.g. replacing a set with a sorted
  list in the funnel) is substrate-visible and moves the canon — same rule as
  any search-path commit: re-baseline after.
- Other benchmark entry points (`run_mcp_pipeline_eval.py`, probe scripts) are
  not pinned by this ADR; pin them the same way if they ever gate decisions on
  per-query stability.
