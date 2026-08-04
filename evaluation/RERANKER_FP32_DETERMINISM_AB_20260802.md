# fp32 Reranker Determinism A/B — REJECTED (2026-08-02)

## Verdict

**REJECTED.** Loading jina-reranker-v3 in fp32 (`reranker.listwise_dtype: "fp32"`)
does **not** reduce run-to-run flip counts, and its own round-to-round aggregate
spread is *worse* than the bf16 baseline's. The observed non-determinism is not
caused by bf16 weight precision — it originates upstream of the reranker
(GPU reduction-order non-determinism cascading through pool composition into the
context-dependent listwise scorer). Weight dtype is the wrong lever.

The `listwise_dtype` config field ships anyway (default `"auto"` = bf16,
byte-identical behavior; commit `0654761`) — it is a harmless, tested knob and
this note documents why flipping it to `fp32` buys nothing.

## Hypothesis (from campaign plan Step 2)

bf16 listwise scoring flips 4–5 boundary golden queries between identical SSCG
runs (pool_hit_rate 0.9695 vs 0.9542 across the two 20260802 baseline rounds);
fp32 weights were hypothesized to tighten score resolution at ranking
boundaries and reduce flips.

## Arms

All runs on the same INDEX_VERSION-4 index (2,253 vectors), same machine
(RTX 4090), sequential execution, no config differences other than
`--reranker-dtype fp32`.

| Run | Dataset | File |
|-----|---------|------|
| bf16 r1/r2 (baseline) | expanded 131q | `benchmark_results/sscg_expanded_h_20260802_r{1,2}.json` |
| fp32 r1/r2 | expanded 131q | `benchmark_results/sscg_fp32_expanded_r{1,2}_20260802.json` |
| fp32 sanity | canonical 63q | `benchmark_results/sscg_fp32_63q_r1_20260802.json` |

Analysis: `scripts/benchmark/analyze_dtype_determinism.py`.

## Results — round-to-round determinism (the gate)

| Metric | bf16 r1↔r2 | fp32 r1↔r2 | Gate | Pass? |
|--------|-----------|-----------|------|-------|
| mrr flips (any Δ) | 21 | 21 | fewer | ❌ |
| material flips (Δ ≥ 0.1) | 9 | 9 | fewer | ❌ |
| pool_hit flips | 4 | 3 | < 4 | ~ (noise) |
| pool_hit_rate spread | 0.0153 | **0.0229** | tighter | ❌ |
| aggregate MRR spread | 0.0004 | **0.0304** | — | ❌ (much worse) |
| recall@20 spread | 0.0071 | 0.0286 | — | ❌ |

fp32 flipped Q102 (1.0→0.0) and Q106 (1.0→0.0) between its *own* rounds — the
exact flappers that motivated the arm — plus a new full flip H054 (1.0→0.0) and
Q90 (1.0→0.333). The flapper *population* shifts but its *size* does not.

## Results — quality and latency (guards, all pass)

- fp32 r1 vs bf16 baseline: MRR +0.005, recall@10 +0.029, recall@20 +0.016 —
  all within the ±0.02 band or explained by the flapper set; no signal.
- 63q sanity: MRR 0.7938 vs canon 0.7987, pool_hit_rate 1.0 — flat.
- Latency: fp32 avg 4,320–4,377 ms vs bf16 4,470 ms — no regression.
- VRAM: no observed regression (0.6B model, ~2× weights still fits trivially).

## Interpretation

If bf16 rounding were the flip mechanism, identical inputs under fp32 would
produce identical scores and flips would collapse. They did not change at all
(21/21, 9/9). The remaining sources are:

1. **cuBLAS/cuDNN reduction-order non-determinism** — GPU matmul reductions are
   not bitwise-reproducible across runs regardless of weight dtype (activations
   still flow through non-deterministic kernels).
2. **Pool-composition cascade** — the listwise scorer is context-dependent, so
   any single upstream rank swap (dense leg, ego-graph tie-break) perturbs
   every score in the window, amplifying one bit-level difference into 4–5
   boundary flips.

True determinism would require `torch.use_deterministic_algorithms(True)` +
`CUBLAS_WORKSPACE_CONFIG` (latency cost, and some kernels lack deterministic
implementations) — out of scope; the 2-agreeing-rounds promotion rule remains
the operative mitigation.

## Consequences

- Deployed `search_config.json` stays on `listwise_dtype: "auto"` (bf16).
- No re-baseline: Steps 3–4 of the campaign measure against the existing bf16
  canon (63q MRR 0.7987 / expanded-131q ~0.659, pool_hit 0.954–0.969).
- The 2-agreeing-rounds rule for boundary promotions stays mandatory.
- Do not re-propose dtype changes (fp16 included — same kernel class) for
  determinism. A future determinism arm must target the kernel/algorithm layer
  (`torch.use_deterministic_algorithms`), not weight precision.
