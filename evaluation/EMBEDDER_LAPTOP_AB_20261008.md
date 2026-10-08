# Laptop embedder A/B: F2LLM-v2-330M vs BGE-M3, with and without gte reranker (2026-10-08)

Hardware: RTX 4060 Laptop, 8188 MiB, 1.3-1.6 GB held by desktop apps at the start of each leg.
HEAD 66541d06 + uncommitted registry entry for `codefuse-ai/F2LLM-v2-330M` (`search/config.py`).
Corpus: this repo, 243 files / 3146 chunks for every leg (equal counts are the substrate guard).
Settings: `--deterministic-gpu`, `PYTHONHASHSEED=0`, `CLAUDE_AUTO_REINDEX=0`, one run per view
(63q r1/r2 were bit-identical for A1 and A0).

## Part 1: BGE-M3 implementation audit. Correct

| Paper / HF card | Ours | OK |
|---|---|---|
| e = norm(H[CLS]) | ST `1_Pooling` cls_token + `2_Normalize` | yes |
| Score = inner product | IP FAISS index + `normalize_L2` | yes |
| No query instruction | none | yes |
| max_len 8192 | composer output under about 2K tokens, never truncates | yes |

The sparse and ColBERT heads are intentionally unused. The paper's Table 11 puts a Lucene-style BM25 at or
above M3-sparse on MLDR, and our identifier-preserving BM25 is the lexical leg. Fusion is RRF rather than the
paper's score sum. Minor: the CrossEncoder reranker loads in fp32 (`search/neural_reranker.py:524`).

## Part 2: leaderboard (MTEB Code v1, scraped 2026-10-08)

| Model | Params | Dim | MTEB-Code | bf16 weights | License |
|---|---|---|---|---|---|
| BAAI/bge-m3 | 568M | 1024 | 58.22 | 1.07 GB | MIT |
| codefuse-ai/F2LLM-v2-330M | 334M | 896 | 75.74 | 0.67 GB | Apache-2.0 |
| codefuse-ai/F2LLM-v2-160M (not run) | 159M | 640 | 70.38 | about 0.32 GB | Apache-2.0 |
| F2LLM-v2-0.6B (4090 lineage) | 596M | 1024 | 77.41 | 1.2 GB | Apache-2.0 |

F2LLM trained on some MTEB-Code splits, so its leaderboard number is optimistic. The golden sets below are
the real test.

## Results

| Leg | Embedder | Reranker | View | MRR | R@5 | R@10 | R@20 | Hit@5 | Latency | Peak VRAM |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | bge-m3 | gte | 63q | 0.7000 | 0.5563 | 0.6931 | 0.8040 | 0.9206 | 431 ms | 1.90 GB |
| A1 | | | 133q | 0.5032 | 0.5245 | 0.6546 | 0.7403 | 0.7895 | 436 ms | |
| A1 | | | fsim | 0.7217 | 0.5466 | 0.6879 | 0.7599 | 0.9206 | 360 ms | |
| A0 | bge-m3 | off | 63q | 0.6350 | 0.4993 | 0.5769 | 0.6069 | 0.8571 | 138 ms | 1.57 GB |
| A0 | | | 133q | 0.5193 | 0.4987 | 0.5517 | 0.5791 | 0.7820 | 113 ms | |
| A0 | | | fsim | 0.6314 | 0.4906 | 0.5681 | 0.5871 | 0.8730 | 88 ms | |
| B1 | F2LLM-330M | gte | 63q | 0.7047 | 0.5822 | 0.7142 | 0.8199 | 0.9524 | 400 ms | 4.24 GB |
| B1 | | | 133q | 0.5080 | 0.5362 | 0.6653 | 0.7578 | 0.8195 | 410 ms | |
| B1 | | | fsim | 0.7430 | 0.5855 | 0.7237 | 0.7904 | 0.9524 | 338 ms | |
| B0 | F2LLM-330M | off | 63q | 0.6026 | 0.5181 | 0.6132 | 0.6428 | 0.8730 | 132 ms | 4.24 GB |
| B0 | | | 133q | 0.4768 | 0.4770 | 0.5311 | 0.5597 | 0.7444 | 129 ms | |
| B0 | | | fsim | 0.6190 | 0.5202 | 0.6179 | 0.6417 | 0.8889 | 112 ms | |

Peak VRAM is torch `max_memory_reserved`. For B the search-side peak (4.24 GB) exceeds the index-side
peak (4.04 GB). The dynamic batch estimator picks batch 4 for the 330M because it prices activations
conservatively, so VRAM headroom exists for a larger batch. The B0 peak equals B1 because the reranker
never loads in B0 and the peak comes from the embedder.

### Paired deltas (95% bootstrap CI, point estimate shown)

Primary, B1 minus A1 (embedder swap with gte on):

| View | MRR | R@10 | R@20 |
|---|---|---|---|
| 63q | +0.0047 [-0.025, +0.034] | +0.0212 [-0.004, +0.046] | +0.0159 [-0.007, +0.039] |
| 133q | +0.0048 [-0.014, +0.024] | +0.0107 [-0.009, +0.031] | +0.0175 [-0.002, +0.037] |
| fsim | +0.0212 [-0.023, +0.066] | +0.0358 [+0.005, +0.067] | +0.0305 [+0.001, +0.060] |

Secondary, B0 minus A0 (embedder swap, dense plus BM25 only):

| View | MRR | R@10 | R@20 |
|---|---|---|---|
| 63q | -0.0323 [-0.087, +0.022] | +0.0363 [-0.010, +0.083] | +0.0359 [-0.013, +0.084] |
| 133q | -0.0425 [-0.080, -0.005] | -0.0206 [-0.064, +0.022] | -0.0194 [-0.064, +0.025] |
| fsim | -0.0124 [-0.071, +0.046] | +0.0498 [+0.005, +0.095] | +0.0546 [+0.006, +0.103] |

Reranker effect (gte on minus off), recall@20:

| Embedder | 63q | 133q | fsim |
|---|---|---|---|
| bge-m3 | +0.197 [+0.125, +0.269] | +0.161 [+0.106, +0.216] | +0.173 [+0.104, +0.242] |
| F2LLM-330M | +0.177 [+0.094, +0.260] | +0.198 [+0.137, +0.260] | +0.149 [+0.067, +0.230] |

## Gate verdict (pre-registered)

- **Quality, B1 vs A1: PASS.** No CI excludes 0 negatively on MRR, R@10 or R@20 on any view. MRR and R@20
  improve (point estimate) on all 3 views. The only CIs excluding 0 are positive (fsim R@10 and R@20).
- **VRAM fit: PASS.** Worst `free_at_start` was 6.5 GB (B1: 8188 - 1477 MiB), so the 0.9x limit is 5.9 GB.
  The worst peak was 4.24 GB. The reindex logs show no OOM-halving.
- **Keep gte: PASS.** B0 never beats B1. gte lifts R@20 by 0.15-0.20 for both embedders with CIs excluding 0.

## Caveats

- Effect sizes for B1 over A1 are small (R@20 +0.016 to +0.031) and mostly inside the CIs. The result reads
  "at least as good, not clearly better". The decisive evidence is that a smaller model (0.67 GB vs 1.07 GB)
  matches bge-m3 when the reranker is on.
- With the reranker off, the 330M is mixed: better R@10/R@20 on 63q and fsim, worse MRR on 133q (CI excludes 0).
  With gte on, the 330M's first-stage recall gain carries through.
- The 330M peaks at 4.24 GB against 1.9 GB for bge-m3, because of its larger activation footprint at
  batch 4. Fit holds, but there is less spare VRAM for other GPU users.
- Single corpus (this repo, Python-heavy). 160M was first skipped because the 330M passed the VRAM gate; it
  was run afterwards, see the addendum.

## Gotcha found: per-model storage dirs start with no exclude filters

`~/.claude_code_search/projects/<project>_<hash>_<model>_<dim>d/project_info.json` is per model. A fresh
dir has no `user_excluded_dirs`, so the first reindex fell back to defaults and indexed 562 files /
10,810 chunks instead of 243 / 3,146. That run was discarded. Fix applied: seed the new project_info.json
with the existing filters (`tests`, `logs`, `benchmark_results`, `audit_reports`). Compare file and chunk counts
across legs before reading any metric.

## Addendum: F2LLM-v2-160M legs (C1 = 160M + gte, C0 = 160M with the reranker off)

Run the same day on the same corpus (243 files / 3146 chunks) with the same flags. The harness
`[CONFOUND]` flag fires on these comparisons only because `embedding_model` differs, which is the
variable under test.

| View | Leg | MRR | R@5 | R@10 | R@20 | Hit@5 | Latency |
|---|---|---|---|---|---|---|---|
| 63q | C1 | 0.7115 | 0.5611 | 0.6997 | 0.8107 | 0.9365 | 385 ms |
| 63q | C0 | 0.6182 | 0.5178 | 0.6008 | 0.6318 | 0.8889 | 123 ms |
| 133q | C1 | 0.5017 | 0.5155 | 0.6452 | 0.7384 | 0.7895 | 399 ms |
| 133q | C0 | 0.4993 | 0.4875 | 0.5346 | 0.5686 | 0.7669 | 121 ms |
| fsim | C1 | 0.7478 | 0.5631 | 0.7035 | 0.7754 | 0.9524 | 329 ms |
| fsim | C0 | 0.6276 | 0.5210 | 0.6143 | 0.6413 | 0.9206 | 104 ms |

Peak VRAM: 3.86 GB at search and 3.65 GB at index (330M: 4.24 / 4.04 GB; bge-m3: 1.9 GB at search).

Paired deltas for C1; no 95% CI excludes 0:

| Contrast | View | MRR | R@10 | R@20 |
|---|---|---|---|---|
| C1 - B1 (160M vs 330M, gte on) | 63q | +0.007 | -0.015 | -0.009 |
| | 133q | -0.006 | -0.020 | -0.019 |
| | fsim | +0.005 | -0.020 | -0.015 |
| C1 - A1 (160M vs bge-m3, gte on) | 63q | +0.012 | +0.007 | +0.007 |
| | 133q | -0.002 | -0.009 | -0.002 |
| | fsim | +0.026 | +0.016 | +0.016 |

With the reranker off (C0 - B0), MRR is +0.016 / +0.023 / +0.009 and R@20 is -0.011 / +0.009 / -0.000
on 63q / 133q / fsim, none significant.

Reading: the 160M ties bge-m3 and sits slightly below the 330M on R@10 and R@20 on all three views
(-0.01 to -0.02, inside the CIs). It saves only about 0.4 GB of peak VRAM against the 330M, because the
reranker and activation buffers dominate the peak rather than the weights. On 8 GB the 330M stays the
recall-first choice (ADR-0084). The 160M is the fallback if a card under 6 GB OOMs, and that card was
not tested.
