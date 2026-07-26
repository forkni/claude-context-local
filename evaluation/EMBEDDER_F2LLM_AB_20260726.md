# Embedding A/B: codefuse-ai/F2LLM-v2-0.6B vs Qwen/Qwen3-Embedding-0.6B (2026-07-26)

## Verdict: ADOPTED

F2LLM-v2-0.6B replaces Qwen3-Embedding-0.6B as the deployed embedding model.
Consistent MRR gain (+0.026/+0.027 mean, 4/4 runs above baseline on both golden
sets), recall flat, hit@5 miss set identical, latency unchanged. Reversible in
<150ms via config switch (per-model index storage; the Qwen index is untouched).

## Motivation

After the A→I→C→D recall campaign, all remaining expanded-set top-5 misses
({Q101, Q102, Q103, Q122}) were ordering misses, and the 2 residual pool misses
(Q103/Q122) were dense-leg-only rescuable (BM25 gold ranks ~1,500-1,700,
param-immune — see `POOL_MISS_DIAGNOSIS.md`, `BM25_K1B_SWEEP_20260726.md`).
The dense embedder was the remaining lever. Candidate evidence:

| Property | F2LLM-v2-0.6B | Qwen3-Embedding-0.6B |
|---|---|---|
| MTEB multilingual avg | **66.47** | 64.02 |
| COREB code retrieval (v1 model) | nDCG@10 0.491 | 0.477 |
| Params / dim / license | 596M / 1024 / Apache-2.0 | 596M / 1024 / Apache-2.0 |
| Pooling / query prompt | last-token (EOS), `Instruct: ...\nQuery:` | same family |
| Max context / VRAM | 40,960 / ~2.2GB | 32,768 / ~2.3GB |

Registry entry (commit `5f49f2a`): `instruction_mode: "custom"` with the same
code-retrieval instruction as Qwen3 for a fair A/B; documents embedded raw;
`onnx_supported: False` (last-token pooling unsupported by onnx_wrapper).

## Protocol

- Corpus: 2,184 chunks / 227 files (excludes `_archive,tests,MagicMock,
  audit_reports,benchmark_results,htmlcov,log`), INDEX_VERSION 4 (path-token
  BM25 augmentation), fresh index in
  `claude-context-local_9e7f0a98_f2llm-v2-0.6b_1024d`.
- Flags: `--k 7 --with-centrality --centrality-alpha 0.0`, reranker unchanged
  (jinaai/jina-reranker-v3), weights 0.35/0.65, rrf_k 100.
- Both golden sets (expanded 96q / original 63q), x2 replicated.
- Baselines: `sscg_track_d_pathaug_{expanded,original}_{r1,r2}_20260726.json`
  (Qwen3-Embedding-0.6B, same flags, same day).
- Results: `sscg_f2llm_{expanded,original}_{r1,r2}_20260726.json`.

## Results (mean of x2)

| Metric | Expanded F2LLM | Expanded Qwen3 | Δ | Original F2LLM | Original Qwen3 | Δ |
|---|---|---|---|---|---|---|
| MRR | **0.6571** | 0.6307 | **+0.026** | **0.7910** | 0.7642 | **+0.027** |
| Recall@5 | 0.6722 | 0.6725 | flat | 0.6659 | 0.6765 | −0.011 (noise) |
| Recall@7 | 0.7238 | 0.7262 | flat | 0.7290 | 0.7327 | flat |
| hit@5 | 0.9583 | 0.9583 | = | 0.9921 | 0.9921 | = |
| pool_hit | 0.9740 | 0.9792 | −1q flicker | 1.000 | 1.000 | = |
| Latency/query | 1,035ms | 1,081ms | flat | — | — | — |

Per-run MRR: expanded 0.6486/0.6656 vs 0.6286/0.6327; original 0.7873/0.7946
vs 0.7584/0.7700 — every F2LLM run beats every corresponding baseline run
(4/4 directional consistency; mean deltas above the ±0.02 single-run noise
floor documented in the benchmark-noise memory).

## Miss-set analysis

- **hit@5 miss set unchanged**: expanded {Q101, Q102, Q103, Q122} in both
  runs; original {} / {Q99} — the same ±1-query flicker the baseline shows.
- **Pool-rescue hypothesis FAILED**: Q103/Q122 golds still never enter the
  fused pool — even the stronger embedder cannot bridge their bilateral
  paraphrase gap. These remain query-expansion territory, not embedder or
  lexical territory.
- Q102 flickered out of the pool in expanded r1 (pool_hit 0.9688) and back in
  r2 (0.9792): its Track-D path-token rescue sits at the fusion-cut boundary,
  so dense-leg reordering perturbs it run-to-run. Known ±1–2-query flicker.
- Remaining structure: Q101/Q102 = in-pool ordering misses (reranker
  territory); Q103/Q122 = pool misses (query-expansion territory only).

## Decision rationale

The primary gate (Q103/Q122 pool entry) was not met, but the secondary
criteria all passed with a bonus: MRR — the metric that tracks the dominant
failure mode (ranking misses, pool_hit ≈ 1.0) — improved consistently on both
sets with zero recall/latency/VRAM cost. Same parameter count, dimension, and
license; drop-in protocol compatibility. Adopted.

Revert path: switch `embedding.model_name` back to
`Qwen/Qwen3-Embedding-0.6B` (launcher 'M' menu option 5) — the Qwen per-model
index is intact.

## Follow-ups

- Optional Phase 2 (plan): single A/B of `Qwen/Qwen3-Reranker-4B` via
  `--reranker-model` for the Q101/Q102 ordering misses. Note a reranker cannot
  fix Q103/Q122 (pool misses).
- Q103/Q122: only remaining lever is query expansion / multi-query retrieval.
