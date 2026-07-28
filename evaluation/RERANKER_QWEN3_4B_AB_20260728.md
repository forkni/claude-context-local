# Reranker A/B: Qwen/Qwen3-Reranker-4B vs jinaai/jina-reranker-v3 (2026-07-28)

## Verdict: REJECTED

Qwen3-Reranker-4B is deployed nowhere. `jina-reranker-v3` remains the reranker.
Every metric on both golden sets, both replicates, favors jina-v3 by a wide
margin — well above the ±0.02 single-run MRR noise floor. Published MTEB-Code
/ CoIR superiority does not transfer to this project's golden set; the COREB
counter-evidence cited in the plan (no off-the-shelf reranker beats a strong
first-stage retriever on code) held.

## Motivation

Follow-up from `EMBEDDER_F2LLM_AB_20260726.md`: after the F2LLM-v2-0.6B
embedder A/B, the remaining expanded-set top-5 misses split into
**Q101/Q102 = in-pool ordering misses (reranker territory)** and
**Q103/Q122 = pool misses (query-expansion territory only, no reranker can
fix these)**. This trial targeted Q101/Q102 with a larger, higher-quality
generative reranker (Qwen3-Reranker-4B, MTEB-Code 81.20 vs 73.42 for the 0.6B
variant already tested; CoIR nDCG@10 73.91 vs 70.64 for jina-reranker-v3;
Apache-2.0 vs jina-v3's CC-BY-NC-4.0).

## Pre-work (Step 1, landed before the trial)

`GenerativeReranker` had three defects that only bite at 4B scale, fixed and
unit-tested before running the A/B:

- Unbounded single-batch forward pass (`[30, 512, 151936]` ≈ 4.35 GiB logits
  tensor) → chunked into `batch_size`-sized groups, `logits_to_keep=1` +
  left padding shrinks the per-batch logits tensor to `[B, 1, V]`.
- fp16 autocast default silently overriding bf16 weights → resolved dtype
  (`bfloat16` on this GPU) stored once in `_ensure_loaded` and passed
  explicitly to `torch.autocast(dtype=...)` in `rerank()`.
- Silent OOM/inference-failure fallback to unranked order → `fallback_count`
  instrumentation added; a run with any fallback is discarded per the gate
  below.

Quantization plumbing (fp8/8bit/4bit/mxfp8 via `RerankerConfig.quantization`)
was built per the user's request but **not exercised in this A/B** — the
trial ran BF16 by design so quality numbers aren't confounded by quantization
loss.

## Protocol

- Corpus/index unchanged from the F2LLM A/B (reranker sits downstream of the
  index; no reindex needed).
- Flags held constant: `--k 7 --with-centrality --centrality-alpha 0.0`,
  weights 0.35/0.65 (config default), `rrf_k 100` (config default),
  `top_k_candidates 30` (config default), embedder F2LLM-v2-0.6B.
- Both golden sets (expanded 96q effective / original 63q effective), ×2
  replicated, control (`jinaai/jina-reranker-v3`) re-run fresh alongside each
  4B run so both arms see identical machine state.
- Pre-flight smoke test (category A subset, 15 queries): model downloaded
  (~8 GB, one-time), loaded on `cuda:0` in `torch.bfloat16`,
  `quantization=none`, peak VRAM 11.67 GB (well under the 19.3 GB cap),
  `fallback_count` gate clean.
- Results: `sscg_rerank_{qwen4b,jinav3}_{expanded,original}_{r1,r2}_20260728.json`.
- Full run log: `benchmark_results/rerank_4b_ab.log`. Zero `fallback_count`
  hits, zero `Batched inference failed` lines, zero OOM/tracebacks across all
  8 runs — gate passed, results are trustworthy.

## Results (mean of ×2)

| Metric | Expanded jina-v3 | Expanded Qwen4B | Δ | Original jina-v3 | Original Qwen4B | Δ |
|---|---|---|---|---|---|---|
| MRR | **0.6495** | 0.617 | **−0.033** | **0.788** | 0.723 | **−0.065** |
| Recall@5 | **0.6685** | 0.5745 | **−0.094** | **0.6745** | 0.556 | **−0.119** |
| Recall@7 | **0.720** | 0.659 | **−0.061** | **0.7215** | 0.6305 | **−0.091** |
| Recall@10 | **0.7485** | 0.704 | **−0.045** | **0.7725** | 0.685 | **−0.088** |
| hit@5 | 0.9585 | 0.958 | flat | **1.000** | 0.968 | **−0.032** |
| NDCG@5 | **0.6485** | 0.571 | **−0.078** | **0.683** | 0.5675 | **−0.116** |
| Latency/query | 888ms | 944ms | +56ms | 897ms | 948ms | +51ms |
| Peak VRAM | 7.91 GB | 13.13 GB | +5.22 GB | 7.91 GB | 13.13 GB | +5.22 GB |

Per-run MRR: expanded 0.640/0.659 (jina) vs 0.617/0.617 (qwen4b); original
0.783/0.793 (jina) vs 0.724/0.722 (qwen4b) — **4/4 directional consistency,
every jina-v3 run beats its paired qwen4b run**, on both MRR and recall,
by margins several times the ±0.02 single-run noise floor.

## Miss-set analysis (Q101/Q102 — the queries this trial targeted)

| Query | jina-v3 (r1/r2) | Qwen4B (r1/r2) |
|---|---|---|
| Q101 | MISS / MISS | **HIT (0.333) / HIT (0.333)** |
| Q102 | MISS / MISS | MISS / MISS |

Qwen4B does fix Q101 consistently (both replicates) — a genuine, reproducible
targeted win. It does **not** move Q102. But this narrow gain comes with
collateral damage across the other ~94 expanded-set queries and all 63
original-set queries, driving recall@5 down by 0.09–0.12 and MRR down by
0.03–0.07 in aggregate. A one-query fix that costs double-digit recall
elsewhere is not a net win.

## Decision rationale

The plan's adopt bar was ≥0.02 mean MRR **gain** on both sets with 4/4 runs
above control. The actual result is the **opposite direction** at 1.5–3× that
magnitude, plus a recall regression far outside noise, plus +56ms latency and
+5.2 GB VRAM. Every criterion in the decision rule points to reject, and none
point to adopt. Apache-2.0 licensing is a real tiebreaker on a *marginal*
call, but this isn't marginal — jina-v3 wins decisively on quality, and its
CC-BY-NC-4.0 license is unchanged risk, not new risk. Rejected.

The published benchmark gap (MTEB-Code 81.20 vs 73.42; CoIR 73.91 vs 70.64)
did not transfer to this codebase's golden set. This is the COREB paper's
finding in miniature: with an already-strong first-stage retriever (hybrid
BM25+dense, graph-boosted, centrality-scored), a generic off-the-shelf
reranker — even a larger, benchmark-stronger one — is not guaranteed net
positive on code retrieval, and generative-yes/no rerankers may simply be a
worse fit for this task's candidate pool than jina-v3's listwise architecture.

Revert path: config already reverted to `reranker.model_name =
"jinaai/jina-reranker-v3"`, `reranker.quantization = "none"` (this repo's
`search_config.json`, confirmed via `SearchConfigManager.load_config()`
round-trip). No reindex needed. Launcher menu (`start_mcp_server.cmd` →
Search Config → Configure Neural Reranker → Select Reranker Model) still
exposes Qwen3-Reranker-4B as option 4 and quantization as option 5 for anyone
who wants to re-run or experiment — the plumbing stays, only the deployment
choice reverts.

## What stays from this work

- `GenerativeReranker` batch-chunking, left-padding, `logits_to_keep=1`,
  bf16-autocast, and `fallback_count` fixes are real correctness/safety
  improvements independent of this verdict — they make the 0.6B generative
  path faster and safer too, and were unit-tested
  (`tests/unit/search/test_generative_reranker.py`).
- Quantization plumbing (`RerankerConfig.quantization`, launcher option 5,
  `[quant]` extra) is untested end-to-end (no `bitsandbytes`/`torchao`
  installed) but unit-tested at the config-building level. Available for
  future use, not exercised by this A/B by design.
- `RERANKER_SWEEP` gained a `qwen_4b` entry in
  `scripts/benchmark/run_sscg_benchmark.py` for any future re-sweep.

## Follow-ups

- Q101/Q102: Q101 is now known fixable by Qwen4B specifically, but not at an
  acceptable cost with this architecture/pool combination. Q102 remains
  unaddressed by any reranker tried so far.
- Q103/Q122 remain pool misses — still query-expansion territory only, per
  the F2LLM A/B's own finding. No reranker (0.6B, jina-v3, or 4B) can reach
  them since they never enter the fused candidate pool.
- If Qwen3-Reranker-4B is revisited, worth checking whether its regression is
  architecture-specific (generative yes/no logit vs jina-v3's listwise
  scoring) rather than scale-specific — the 0.6B generative variant's
  standing relative to jina-v3 on this same golden set is not separately
  on record and could isolate the variable.
