# A/B: cuDNN SDPA backend for the Jina listwise reranker (2026-10-18)

## Status: MEASURED on `d293cb07`. NOT ADOPTED under the pre-registered rule (gate 3 misses by one query on 133q); knob stays opt-in. Override is the owner's call, see Decision

Knob: `reranker.listwise_attention_backend` (commit `e98c9b12`, opt-in, default `"default"`).
Control = `"default"` (torch's own SDPA dispatch, which lands on the **math** kernel for the
transformers 5.17 GQA path on Windows). Treatment = `"cudnn"` (`sdpa_kernel([CUDNN_ATTENTION,
MATH])`, cuDNN fused attention with MATH as the in-list fallback).

Why: `docs/PERF.md` attributes 95-96% of each Rerank call to the vendor `forward`, running on the
math backend (full L^2 score matrix, 7-11 GB peak). Micro-bench per layer at L=6361 bf16 causal:
math 43 ms / 5.9 GiB vs cuDNN 1.3-1.9 ms / 0.1-0.17 GiB. cuDNN changes floating-point output, so
a default flip needs this A/B and a canon re-pin.

## Substrate (fixed before any leg ran)

| item | value |
|---|---|
| code | `development` @ `d293cb07` (Step 0 pin `7c3725f6`, Step 1 knob `e98c9b12`, `set_priority` fix `d293cb07`) |
| reranker | `jinaai/jina-reranker-v3` pinned `revision=d7d7e73b6ea138ced340b83865931b5dfb6c97aa` (bit-identical with the unpinned load, Step 0 gate 0 movers) |
| embedder | `codefuse-ai/F2LLM-v2-0.6B` / 1024d, `IndexFlatIP` |
| torch / CUDA / cuDNN | 2.11.0+cu128, CUDA 12.8, cuDNN **91900** (9.19.0) |
| GPU | RTX 4090, sm89, 24 GB, WDDM |
| transformers | 5.17 (`sdpa_attention_forward`; real call probed 2026-10-18: q `(1,16,L,128)` / k,v `(1,8,L,128)` bf16, `attn_mask=None`, `is_causal=True`, `enable_gqa=True`, one packed prompt per forward so no padding mask; `can_use_cudnn_attention` True on that exact call) |
| index | one HEAD index shared by every leg, no indexed-file edits between legs (chunk count recorded below) |
| env | `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, **no `--deterministic-gpu`** (it refuses the cuDNN kernel; the treatment would silently become a second control) |
| harness | `scripts/benchmark/run_sscg_benchmark.py`, k=10, hybrid, `pin_intent_off=True`; treatment via `--set reranker.listwise_attention_backend=cudnn` |

A different cuDNN build is a different treatment: re-run, do not reuse these numbers.

## Pre-leg finding: the first treatment was inert (2026-10-18)

The first 63q legs on `e98c9b12` (`evaluation/ab_attn_{c63,t63_r1,t63_r2}_20261018.json`) came
back bit-identical across control and both treatment rounds (every paired delta +0.0000,
n_moved 0) with unchanged rerank latency. Diagnosis (`scratchpad/probe_cudnn_real.py`): the real
forward *is* cuDNN-eligible, but `torch.nn.attention.sdpa_kernel(backends)` only filters torch's
fixed priority order `[flash, efficient, math, cudnn]`, so `[CUDNN_ATTENTION, MATH]` still
dispatched MATH. Forced cuDNN-only on a 24-doc window: 409 ms / 1.69 GiB peak vs math 2025 ms /
9.69 GiB, same top-3. Fix `d293cb07`: `sdpa_kernel(backends, set_priority=True)`. Legs below are
re-run on `d293cb07` under new file names (`evaluation/ab2_attn_*_20261018.json`); the first
set is kept only as the record of the inert run. The load-time verdict log was right all along
(it probes the same shape the real call uses) but could not see the priority problem.

## Views and legs

| leg | view | dataset | flags |
|---|---|---|---|
| C63 | 63q | `evaluation/golden_dataset.json` | control |
| T63 r1 | 63q | same | `--set reranker.listwise_attention_backend=cudnn` |
| T63 r2 | 63q | same | treatment, determinism re-run |
| C133 / T133 | 133q | `evaluation/golden_dataset_expanded.json` | control / treatment |
| CF / TF | F-via-similar | `evaluation/golden_dataset.json --f-via-similar` | control / treatment |

Paired CIs from `run_sscg_benchmark.py --compare <control.json> <treatment.json>`. JSON dumps
stay unstaged (`evaluation/ab2_attn_*_20261018.json`).

## Gates (pre-registered)

1. **Drift gate** (control vs the 2026-10-01 canon 0.8415 / 0.6637 / 0.8915): MRR within
   +-0.02 and recall@20 >= -0.02 on all three views. A breach is recorded and explained, not
   a REJECT of the treatment (the treatment is judged paired against the control).
2. **Adoption gate** (treatment vs control): no paired bootstrap 95% CI excludes 0 on the
   negative side for MRR, recall@10 or recall@20 on any view.
3. `pool_hit_rate` non-decreasing on every view.
4. **Determinism**: T63 r1 == T63 r2 bit-identical (aggregates and retrieved lists). cuDNN
   documents SDPA fprop as deterministic; a miss is a REJECT.
5. **Finite scores**: every Rerank call in every leg returns only finite scores. The knob's
   MATH retry logs `Non-finite reranker scores` when it fires; any such line in a treatment leg
   log fails this gate.
6. **8 GB check** (reported, must not OOM): one treatment 63q leg with
   `performance.vram_limit_fraction` set so the effective cap is ~8 GB; no OOM retry and no
   window shrink.

Latency and VRAM are **reported, not gated**: `tmp/rerank_attribution.py --runs 8 --warmup 2`
and `scripts/benchmark/profiling/profile_search_latency.py --runs 8` on claude-context-local and
SDTD_042, control vs treatment.

Decision rule: all of 2-5 pass and 6 does not OOM -> flip the default to `"cudnn"` and re-pin
the canon (`evaluation/CANON_20261018_CUDNN_ATTN.md`). Otherwise the knob stays opt-in and the
result is recorded as REJECTED here and in `docs/PERF.md`.

## Results (legs run 2026-10-18/19 on `d293cb07`)

Substrate at leg time: 247 files / **3,283 chunks** (the 10-01 canon was measured on 3,114;
the index grew with the 10-01..10-18 commits, so the drift gate below compares across content
drift, see gate 1). Every leg exited 0; no leg log contains `Non-finite`, `OOM`, `retrying` or a
window-shrink line.

### Aggregates

| leg | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | gold_in_window | avg latency / query |
|---|---|---|---|---|---|---|---|
| C63 | 0.8173 | 0.6289 | 0.7662 | 0.8561 | 1.0000 | 1.000 | 4,539 ms |
| T63 r1 | 0.8226 | 0.6250 | 0.7839 | 0.8654 | 1.0000 | 1.000 | 1,253 ms |
| T63 r2 | 0.8226 | 0.6250 | 0.7839 | 0.8654 | 1.0000 | 1.000 | 1,259 ms |
| C133 | 0.6523 | 0.6386 | 0.7702 | 0.8554 | 0.9624 | 0.962 | 4,545 ms |
| T133 | 0.6587 | 0.6361 | 0.7799 | 0.8535 | **0.9549** | 0.962 | 1,220 ms |
| CF | 0.8656 | 0.6260 | 0.7755 | 0.8322 | 1.0000 | 1.000 | 3,900 ms |
| TF | 0.8722 | 0.6220 | 0.7901 | 0.8414 | 1.0000 | 1.000 | 1,084 ms |
| T63 8 GB cap | 0.8226 | 0.6250 | 0.7839 | 0.8654 | 1.0000 | 1.000 | 1,261 ms |

Dumps: `evaluation/ab2_attn_{c63,t63_r1,t63_r2,c133,t133,cf,tf,t63_8gb}_20261018.json` (unstaged).
C63 on `d293cb07` is bit-identical to C63 on `e98c9b12` (`ab_attn_c63`), so the `set_priority`
fix did not touch the control path.

### Paired deltas, treatment minus control (bootstrap 95% CI, `--compare`)

| view | MRR | recall@5 | recall@10 | recall@20 | n_moved (MRR) |
|---|---|---|---|---|---|
| 63q | +0.0053 [-0.0053, +0.0238] | -0.0040 [-0.0119, 0.0000] | +0.0177 [-0.0034, +0.0410] | +0.0093 [0.0000, +0.0238] | 3 |
| 133q | +0.0064 [-0.0043, +0.0196] | -0.0025 [-0.0100, +0.0038] | +0.0096 [-0.0177, +0.0375] | -0.0019 [-0.0138, +0.0081] | 19 |
| F-via-similar | +0.0066 [-0.0040, +0.0238] | -0.0040 [-0.0119, 0.0000] | +0.0146 [-0.0053, +0.0370] | +0.0093 [0.0000, +0.0238] | 2 |

Point estimates: MRR, recall@10 and recall@20 up on every view except 133q recall@20 (-0.0019);
recall@5 down by one query on each view. No CI excludes 0 in either direction.

### Gates

| # | gate | verdict | detail |
|---|---|---|---|
| 1 | drift, control vs 10-01 canon | **breached on 63q and F, recorded** | MRR: 63q 0.8173 vs 0.8415 (-0.0242), 133q 0.6523 vs 0.6637 (-0.0114), F 0.8656 vs 0.8915 (-0.0259). recall@20: +0.0136 / +0.0127 / +0.0159, all inside. Not a treatment verdict: the control runs the unchanged math kernel on the same index as the treatment. The substrate moved since the canon in two ways: content (3,114 -> 3,283 chunks) and about 30 search-path commits between 10-01 and `7c3725f6` (C-family chunking repairs, duplicate-chunk-id folding, the `case_gated` BM25 analyzer, `create_reranker(RerankerConfig)`), none of them re-pinned. The 09-20 and 10-01 pins recorded the same pattern; whichever kernel wins, the next canon re-pin absorbs this. |
| 2 | adoption CIs (MRR / recall@10 / recall@20, 3 views) | **PASS** | no paired CI excludes 0 on the negative side (table above); 9 of 9 lower bounds >= -0.0177 |
| 3 | `pool_hit_rate` non-decreasing, every view | **FAIL by one query (133q)** | 63q 1.0000 -> 1.0000, F 1.0000 -> 1.0000, 133q 0.9624 -> 0.9549 (128 -> 127 of 133). The lost query is H012 ("suppress a harmless ASGI error message the web server prints when stopped with Ctrl+C"): `pool_hit` True -> False, `gold_in_window` True in both legs, recall@10 0.5 -> 0.0, MRR 0.1667 -> 0.0, `file_recall@10` 1.0 in both. Under control the gold `app_lifespan` sat at rank 6 of the final list; under cuDNN the hop-1 window (30 entries, `gold_in_window` True in both legs) reranked it below the survivor cut, so it never entered the 30-candidate final pool and `JobRegistry.get` / `CleanupQueue.add` took ranks 3-4 instead. `file_recall@10` stays 1.0 (`_drop_benign_uvicorn_errors` in the same file is rank 1 in both). A deterministic reranker-numerics effect (T63 r1 == r2), not run noise. |
| 4 | determinism, T63 r1 == r2 | **PASS** | aggregates and every per-query row bit-identical (only `latency_ms` differs) |
| 5 | finite scores | **PASS** | 0 `Non-finite reranker scores` lines across 8 treatment leg logs (the MATH retry never fired) |
| 6 | 8 GB check | **PASS** | `--set performance.vram_limit_fraction=0.34` -> `[VRAM_LIMIT] Requested=34%, effective=27%` (~6.6 GB after the headroom formula, stricter than the 8 GB intended); 63/63 queries, no OOM retry, no window shrink, results bit-identical to the uncapped T63 |

### Decision (pre-registered rule applied)

Rule: "all of 2-5 pass and 6 does not OOM -> flip the default". Gates 2, 4, 5 and 6 pass; gate 3
misses by exactly one query on one view. **Under the rule as written the default is not flipped:
`listwise_attention_backend` stays opt-in (`"cudnn"`), and this result is recorded as NOT ADOPTED
on gate 3 here and in `docs/PERF.md`.**

What the rule does not weigh, recorded for the owner's call: the miss is a single query at the
pool-hit boundary (H012 was already at MRR 0.1667 under control), every quality CI is neutral
with positive point estimates on MRR and recall@10 on all three views, and the treatment is
deterministic and finite. Against that, the knob removes ~91% of per-query reranker time and
~68% of peak VRAM (next section), which is the whole motivation of this plan. Overriding gate 3
would mean: flip the default, re-pin the canon on the treatment legs, and write an ADR that names
H012 as the accepted cost. Not doing so keeps the canon and the math kernel, and 8 GB users opt in.

### Latency and VRAM (reported, not gated)

`tmp/rerank_attribution.py --runs 8 --warmup 2` (8 queries, 24 Rerank calls per run, median of 8):

| | claude-context-local control | claude-context-local cuDNN | SDTD_042 control | SDTD_042 cuDNN |
|---|---|---|---|---|
| wall per run, median (min-max) | 31.72 s | 3.65 s (3.32-5.37 for `run_rerank`) | 21.78 s | 2.92 s (2.51-4.62 for `run_rerank`) |
| `vendor_rerank` per run / per call | 30.61 s / 1,331.6 ms | 3.02 s / 132.6 ms | 20.88 s / 997.4 ms | 2.32 s / 105.3 ms |
| `forward` per call | 1,317.4 ms | 118.7 ms | 986.9 ms | 94.0 ms |
| `empty_cache` per run | 0.524 s | 0.052 s | 0.371 s | 0.047 s |
| peak allocated, median (min-max) | 8,213 MB (4,659-11,131) | 2,769 MB (2,584-2,875) | 6,845 MB (2,975-8,720) | 2,702 MB (2,429-2,793) |
| OOM retries | 0 | 0 | 0 | 0 |
| hop-1 `neural_rerank` stage, per query | 1,296 ms | 354 ms | 1,036 ms | 116 ms |

`scripts/benchmark/profiling/profile_search_latency.py --runs 8` (median of 8 runs):

| | claude-context-local control | claude-context-local cuDNN | SDTD_042 control | SDTD_042 cuDNN |
|---|---|---|---|---|
| total wall-clock (spread) | 31.75 s (31.67-31.84) | 3.70 s (3.64-5.63) | 21.76 s (21.73-21.85) | 2.89 s (2.84-4.39) |
| `rerank`, 24 calls (share) | 31.47 s (99.1%) | 3.43 s (92.6%) | 21.47 s (98.6%) | 2.58 s (89.4%) |
| `metadata_get`, ~1,615 calls | 0.124 s | 0.127 s | 0.130 s | 0.128 s |

Benchmark harness per-query latency (table above): 4.5 s -> 1.25 s on 63q, 4.5 s -> 1.22 s on
133q, 3.9 s -> 1.08 s on F (3.6x). The cuDNN legs show a wider max (one run at 5.4 s in the
attribution, 5.6 s in the profile): a one-off outlier in run 1 of 8 in each, the other 7 within
0.3 s of the median. Reranking drops from 99% to 89-93% of the search time (SDTD_042: 21.8 s -> 2.9 s per
8-query run, 7.5x). Peak VRAM 6.8-8.2 GB -> 2.7-2.8 GB median on both repos, which is what
makes the 8 GB tier viable without window shrinking.
