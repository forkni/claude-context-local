# Embedder A/B: codefuse-ai/F2LLM-v2-1.7B vs F2LLM-v2-0.6B for the workstation tier (2026-10-19)

## Status: PRE-REGISTERED (legs not yet run)

Candidate: `codefuse-ai/F2LLM-v2-1.7B` as the `recommended_model` of the **workstation** VRAM
tier (18 GB+, `search/vram_manager.py`) in place of the deployed `codefuse-ai/F2LLM-v2-0.6B`.
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

Pending.
