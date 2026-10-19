# Embedder A/B: codefuse-ai/F2LLM-v2-1.7B vs F2LLM-v2-0.6B for the workstation tier (2026-10-19)

## Status: REJECTED for the workstation tier (2026-10-19; gates 2, 3, 4 and 6 failed)

Candidate: `codefuse-ai/F2LLM-v2-1.7B` as the `recommended_model` of the **workstation** VRAM
tier (18 GB+, `search/vram_manager.py`) and as the big-GPU alternative to the deployed default
`codefuse-ai/F2LLM-v2-0.6B`. (Correction after the legs ran: `VRAM_TIERS["workstation"]`
still names `Qwen/Qwen3-Embedding-0.6B`; the 0.6B F2LLM is the deployed default through the
example config and the launcher, so the control arm is the deployed default, not the tier row.)
Motivation: the cuDNN attention switch (ADR-0088) cut the reranker's search-time peak from
7-11 GB to about 2.8 GB on the RTX 4090, which frees VRAM for a larger embedder on the big-GPU
tier only. The 0.6B stays the default for every other tier and in the example config.

## Candidate facts (Hub, fetched 2026-10-19)

| Property | F2LLM-v2-1.7B | F2LLM-v2-0.6B (deployed) |
|---|---|---|
| Base / layers / heads | Qwen3-1.7B, 28 layers, 16 Q / 8 KV | Qwen3-0.6B, 28 layers, 16 Q / 8 KV |
| Hidden size = embedding dim | **2048** | 1024 |
| Max position embeddings | 40,960 | 40,960 |
| Pooling / normalize | last-token (`include_prompt` true) / Normalize | same |
| Hub prompts (`config_sentence_transformers.json`) | identical to the 0.6B (generic `query`, empty document) | - |
| Weights (bf16 `model.safetensors`) | 3,441,183,720 bytes (3.44 GB) | 1.2 GB |
| Hub revision | `c5650fe0573b810008b5fbf79f51ff9bfa1f2e83` (2026-09-03) | `8786315a8711c242ee03ec67c74dd9ad0a61e2cf` |
| License | Apache-2.0 | Apache-2.0 |

Registry entry (this commit, `search/config.py`): `dimension 2048`, `max_context 40960`,
`vram_gb "3.5GB"`, `fallback_batch_size 128`, `vram_tier "workstation"`, and the same
`instruction_mode "custom"` / `query_instruction` / `code2code_instruction` as the 0.6B
(`evaluation/F2LLM_SETTINGS_AUDIT_20261008.md` found that template correct for the family; a
wording change is a separate A/B, not this one). Documents are embedded raw, as for the 0.6B.

## Substrate

| item | value |
|---|---|
| HEAD | `798661f8` plus the registry entry (committed before the legs; SHA recorded in Results) |
| corpus | this repo, one project hash `9e7f0a98`; control index `..._f2llm-v2-0.6b_1024d` (live, 247 files / 3,280 chunks at pre-registration), treatment index `..._f2llm-v2-1.7b_2048d` built fresh with `tools/batch_index.py --mode force`. Equal chunk and file counts are the substrate guard |
| reranker | `jinaai/jina-reranker-v3` pinned `d7d7e73b`, `listwise_attention_backend="cudnn"` (10-19 default) in both arms |
| torch / CUDA / cuDNN / transformers / ST | 2.11.0+cu128 / 12.8 / 9.19.0 / 5.17.0 / 6.1.0 |
| GPU | RTX 4090, sm89, 24 GB, WDDM; no other GPU job during a leg (`nvidia-smi` checked before each) |
| env per leg | `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, no `--deterministic-gpu` (canon parity; it refuses the cuDNN kernel) |
| model selection | `CLAUDE_EMBEDDING_MODEL=<model>` per leg; the registry syncs the dimension and the per-model index dir follows the slug. `search_config.json` is not edited |
| harness | `scripts/benchmark/run_sscg_benchmark.py`, k=10, hybrid 0.35/0.65 RRF, `pin_intent_off=True`, same flags as the 10-19 canon |

The control legs are **re-run in the same session** as the treatment legs rather than reusing
the 10-19 canon dumps: the cuDNN A/B showed that an MCP-server reindex between sessions rebuilds
the call graph and reorders heads (59/133 result sets differed on the same SHA), so paired legs
must share one session. The 10-19 canon serves only as the drift reference for the control.

## Views and legs

| leg | view | dataset | embedder |
|---|---|---|---|
| C63 / T63 r1 / T63 r2 | 63q | `evaluation/golden_dataset.json` | 0.6B / 1.7B / 1.7B (determinism) |
| C133 / T133 | 133q | `evaluation/golden_dataset_expanded.json` (H012/H004-corrected labels) | 0.6B / 1.7B |
| CF / TF | F-via-similar | `evaluation/golden_dataset.json --f-via-similar` | 0.6B / 1.7B |

Dumps: `evaluation/ab_f2llm1p7b_{c63,t63_r1,t63_r2,c133,t133,cf,tf}_20261019.json` (unstaged,
`evaluation/*.json` stays local). Paired CIs from `run_sscg_benchmark.py --compare <control> <treatment>`.

## Gates (pre-registered)

1. **Drift gate** (control vs the 10-19 canon 0.8235 / 0.6750 / 0.8735): MRR within +-0.02 and
   recall@20 >= -0.02 on all three views. A breach is recorded and explained, not a REJECT of
   the treatment (which is judged paired against the control).
2. **No-harm gate** (treatment vs control): no paired bootstrap 95% CI excludes 0 on the
   negative side for MRR, recall@10 or recall@20 on any view.
3. **Benefit gate**: a 3x larger model with a 2x larger index does not ship as a tier
   recommendation on a null result. Required: MRR point estimate >= control on all three views,
   and at least one paired CI on MRR, recall@10 or recall@20 excluding 0 on the positive side on
   63q or 133q. (The 0.6B adoption in `EMBEDDER_F2LLM_AB_20260726.md` had +0.026 MRR on both
   sets with 4/4 directional consistency; that is the bar in spirit.)
4. `pool_hit_rate` non-decreasing on every view.
5. **Determinism**: T63 r1 == T63 r2 bit-identical (aggregates and retrieved lists).
6. **Fit gate** (must hold, else REJECT for the tier): peak VRAM (torch `max_memory_reserved`)
   during indexing and during search with the Jina reranker stays under 16 GB, so a 24 GB
   workstation keeps headroom; no OOM retry in any leg log.

Reported, not gated: index build time and per-query latency (control vs treatment), the
dynamic batch the sizer picks for the 1.7B, index size on disk (FAISS flat 2048-d doubles the
0.6B's vectors), model download size.

Decision rule: gates 2-6 pass -> `VRAM_TIERS[workstation].recommended_model` flips to the 1.7B,
the launcher menu gains the option, and the canon is **not** re-pinned (the deployed default and
the example config stay on the 0.6B; the 1.7B index is a separate per-model index, so the
revert path is the model switch). Gate 2 or 4-6 fails -> REJECTED; the registry entry stays as
a measured opt-in and the result is recorded here, in `CHANGELOG.md` and `docs/BENCHMARKS.md`.
Gate 3 alone fails -> NOT ADOPTED for the tier (opt-in only), same record.

## Results

Substrate: HEAD `a8c7cf5b` (the registry entry commit). Every index build in this A/B produced
247 files / 3,066 collected chunks / 3,289 embedded chunks (223 module summaries), so the
substrate guard held. Nine legs ran 04:58-05:14 in one session, all exit 0; no OOM retry in any
leg log. Both sizers picked a dynamic batch of 16 (per-item activation cost 0.855 GB for the 0.6B,
0.871 GB for the 1.7B; the larger model loads 3.21 GB allocated vs 1.12 GB).

### Per view

| view | arm | MRR | recall@5 | recall@10 | recall@20 | NDCG@5 | pool_hit_rate | avg latency (ms) |
|---|---|---|---|---|---|---|---|---|
| 63q | 0.6B (C63) | 0.8237 | 0.6361 | 0.7747 | 0.8619 | 0.6744 | 1.0000 | 1247 |
| 63q | 1.7B (T63 r1 = r2) | 0.8161 | 0.6489 | 0.7594 | 0.8423 | 0.6781 | 1.0000 | 1963 (r1) / 1421 (r2) |
| 133q | 0.6B (C133) | 0.6747 | 0.6401 | 0.7817 | 0.8594 | 0.6191 | 0.9624 (128/133) | 1226 |
| 133q | 1.7B (T133) | 0.6649 | 0.6287 | 0.7705 | 0.8304 | 0.6084 | 0.9474 (126/133) | 1255 |
| F-via-similar | 0.6B (CF) | 0.8735 | 0.6331 | 0.7808 | 0.8361 | 0.6820 | 1.0000 | 1093 |
| F-via-similar | 1.7B (TF) | 0.8304 | 0.6221 | 0.7458 | 0.7932 | 0.6617 | 1.0000 | 1120 |

### Paired deltas, treatment minus control (95% bootstrap CI, `--compare`)

| view | MRR | recall@10 | recall@20 | movers (MRR) |
|---|---|---|---|---|
| 63q | -0.0075 [-0.0241, +0.0016] | -0.0153 [-0.0437, +0.0116] | **-0.0196 [-0.0413, -0.0005]** | 4 |
| 133q | -0.0098 [-0.0224, +0.0002] | -0.0113 [-0.0421, +0.0194] | **-0.0289 [-0.0598, -0.0019]** | 23 |
| F-via-similar | **-0.0431 [-0.0885, -0.0077]** | **-0.0350 [-0.0701, -0.0014]** | **-0.0430 [-0.0743, -0.0152]** | 5 |

Bold = CI excludes 0 on the negative side. Full output: `tmp/ab_e17_compare.txt`,
`tmp/ab_e17_compare133.txt` (local).

### Gates

| gate | result | evidence |
|---|---|---|
| 1 drift (control vs 10-19 canon) | PASS | MRR +0.0002 / -0.0003 / 0.0000; recall@20 +0.0053 / +0.0025 / +0.0053 (63q / 133q / F) |
| 2 no-harm | **FAIL** | recall@20 CI negative on all three views; F-via-similar MRR and recall@10 negative too |
| 3 benefit | **FAIL** | MRR point estimate below control on all three views; no positive-excluding CI anywhere |
| 4 pool_hit_rate | **FAIL** | 133q 0.9624 -> 0.9474 (128 -> 126 of 133); 63q and F 1.0 in both arms |
| 5 determinism | PASS | T63 r1 == r2 bit-identical (aggregates and retrieved lists; only `latency_ms` differs) |
| 6 fit | **FAIL** | cold force reindex: torch `max_memory_reserved` **16.37 GiB** (allocated 5.88 GiB), at the 16 GB line; search legs 7.55 GiB reserved (control 5.49) pass; no OOM retry |

**Verdict: REJECTED for the workstation tier.** `VRAM_TIERS`, the launcher model menu and the
docs tables stay unchanged; `codefuse-ai/F2LLM-v2-1.7B` remains in `MODEL_REGISTRY` as a
measured opt-in (`CLAUDE_EMBEDDING_MODEL=codefuse-ai/F2LLM-v2-1.7B`, own per-model index dir).
The canon of record stays the 10-19 cuDNN pin.

### Where the loss sits

- 63q and 133q are within noise on MRR (4 and 23 movers). `pool_hit_rate` and
  `gold_in_window_rate` are 1.0 for every 63q query in both arms, so the Jina reranker and the
  `gar_interleave` window order set the final rank; a different embedder only changes pool
  composition. The one large 63q mover is Q90 (`find_path`, 1.000 -> 0.500); Q70 / Q96 / Q97 are
  find-similar queries near 0.1 in both arms. On 133q the 0.5 drops are Q90 and H023, and two
  golds left the pool (gate 4).
- F-via-similar (dense-only code2code, no BM25 or reranker rescue) is where the embedder acts
  alone, and it is significantly worse: Q71 -0.875, Q94 -0.857, Q90 -0.500, Q70 -0.250,
  Q95 -0.233, no mover up.
- Pooling / padding defect ruled out (`tmp/ab_e17_padding_probe.py`, 32 real function bodies
  of 200-8,000 chars, through the project's own loader): both models bf16, `padding_side`
  right; batch-1 vs batch-16 cosine min 0.9954 (1.7B) / 0.9961 (0.6B), mean 0.9987 / 1.0002,
  shuffled batches the same; pairwise cosine between unrelated texts mean 0.16 / 0.17. The 1.7B
  embeds consistently; it is just not a better fit for this corpus under this pipeline (which
  was tuned, and whose gold sets were curated, against the 0.6B).

### Reported, not gated

| item | 0.6B | 1.7B |
|---|---|---|
| Hub download | 1,150 MB | 3,295 MB |
| per-model index dir (`code.index`) | 131 MB (13.5 MB) | 144 MB (26.9 MB, flat 2048-d) |
| force reindex, this repo | 66.7 s wall, 5.42 GiB reserved (`c_reindex`) | 124.2 s wall, 57 s of it embedding, 16.37 GiB reserved (`t_cold_reindex`) |
| search-leg peak (torch reserved / allocated) | 5.49 / 3.74 GiB | 7.55 / 5.88 GiB |
| `nvidia-smi` peak during the cold build | - | 20,690 MiB (idle baseline 3,531 MiB with the MCP server up) |
| avg query latency | 1247 / 1226 / 1093 ms | 1421 (r2) / 1255 / 1120 ms; the 1963 ms of T63 r1 is the first leg after the rebuild (warm-up) |

Cache caveat: the first treatment reindex leg (`t_reindex`, 71.3 s) was a 100% hit on the
persistent chunk embedding cache (`index/chunk_embeddings.bin`), so the model never loaded and
torch reported 0.00 GiB. Gate 6 was graded on a second build with that cache moved aside
(`chunk_embeddings.bin.pre_cold_rebuild`, left in place). The control's 66.7 s is a warm-cache
figure too and is not a like-for-like build time.
