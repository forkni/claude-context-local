# Run the Jina listwise reranker on cuDNN fused attention by default

Status: accepted
Date: 2026-10-19

`jinaai/jina-reranker-v3` scores one packed prompt per listwise call through 28
`Qwen3` attention layers with 16 query / 8 key-value heads (GQA). On this
machine (Windows, torch 2.11.0+cu128, transformers 5.17) torch's default SDPA
dispatch tries flash (absent on Windows), then memory-efficient (rejects
`enable_gqa=True`), then math. The math kernel materialises the full L x L
score matrix per layer, so a 6-7k-token window costs ~1.3 s and 7-11 GB of
peak VRAM per rerank call, which was 95-99% of the end-to-end search time
(`docs/PERF.md`, attribution table). cuDNN fused attention (sm80+, cuDNN 9.x)
handles the same shape and was never consulted because it sits last in
torch's priority list.

The opt-in knob `RerankerConfig.listwise_attention_backend` (`e98c9b12`,
`d293cb07`) wraps the listwise forward in `torch.nn.attention.sdpa_kernel`
with `set_priority=True`. Its pre-registered A/B
(`evaluation/ATTN_BACKEND_AB_20261018.md`) measured `"cudnn"` against the
math control on one index. This ADR flips the default to `"cudnn"`.

## Decision

1. `listwise_attention_backend` defaults to `"cudnn"` (`[CUDNN_ATTENTION,
   MATH]`, cuDNN tried first, MATH kept in the list so an ineligible shape or
   a machine without cuDNN attention falls back instead of raising).
   `"default"`, `"efficient"` and `"math"` stay selectable; `"math"` reproduces
   the pre-10-19 canon kernel exactly.
2. The field stays benchmark-locked: any other value is a different
   floating-point substrate and needs its own A/B before becoming the default.
3. Canon re-pinned on the treatment legs:
   `evaluation/CANON_20261019_CUDNN_ATTN.md`. The 2026-10-01 canon is
   superseded.
4. The two golden labels the A/B exposed as wrong are corrected in
   `evaluation/golden_dataset_expanded.json` (H012: grade-3 target was
   `_configure_logging`, a function the fixing commit `e0f72a39` never
   touched; the real answer `_drop_benign_uvicorn_errors` was unlabeled.
   H004: `_is_empty_file`, added by the fixing commit `dd76f350`, was
   unlabeled). The 133q legs were re-run on the corrected set, and because the
   MCP server had rebuilt the call graph between sessions (resolver edge
   counts moved, 59/133 control result sets differed), the 63q and
   F-via-similar legs were re-run too, so every canon view shares one
   substrate.

## Reasons

- **Speed and memory, measured on two repos.** Rerank call 1,332 -> 133 ms
  (this repo) and 997 -> 105 ms (SDTD_042); an 8-query run 31.7 -> 3.7 s and
  21.8 -> 2.9 s; peak allocation 8.2 -> 2.8 GB and 6.8 -> 2.7 GB. Reranking
  falls from 99% to 93% of search time. The 8 GB check (`vram_limit_fraction`
  cap, effective ~6.6 GB) ran 63/63 queries with no OOM retry and no window
  shrink, bit-identical to the uncapped leg.
- **Quality gates.** Adoption CIs (MRR / recall@10 / recall@20, three views):
  no paired CI excludes 0 on the negative side; point estimates positive on
  MRR on every view on the same-substrate 10-19 legs (63q +0.0062, 133q +0.0105 with a CI
  excluding 0, F-via-similar +0.0079). Determinism: 63q treatment r1 == r2
  bit-identical.
  Finite scores: the MATH retry never fired across every treatment leg.
- **Gate 3 (`pool_hit_rate` non-decreasing)** first failed by one query on
  133q (128 -> 127). A label audit of every negative mover found that query,
  H012, mislabeled: its gold set did not contain the answer, which both
  kernels ranked first. On the corrected labels the gate reads
  PASS: 127 -> 128 of 133, H009 regained, none lost. 63q and F-via-similar
  `pool_hit_rate` were 1.0 under both kernels throughout.
- **The 63q view is the stronger signal.** It is curated with unambiguous
  targets; the 133q H-category labels are mined from historical commits and
  can be stale, as H012/H004 showed. 63q moved by three queries, all one-place
  sibling swaps, none a pool loss, on the 10-18 legs; on the 10-19 legs:
  3 MRR movers (1 up, 2 down): Q95 0.333 -> 0.250; Q70 0.125 -> 0.100; Q90 0.500 -> 1.000.

## Considered Options

- **Keep math as default, cuDNN opt-in.** Rejected: the pre-registered rule
  passed once the one failing query was shown to be a label defect, and
  leaving the default on a kernel that is 10x slower and 3x hungrier would
  make the 8 GB tier depend on users finding the knob.
- **`"efficient"` backend.** Not viable: memory-efficient attention rejects
  the GQA call in this torch build, so it would be math under another name.
- **Patch the vendor model to use an explicit `attn_implementation`.**
  Rejected: the vendor code is loaded with `trust_remote_code=True` at a
  pinned revision (`7c3725f6`); the `sdpa_kernel` context reaches the same
  kernel without touching it.

## Consequences

- Every published number from this date is measured on cuDNN attention.
  Comparisons against pre-10-19 canons cross a kernel boundary as well as the
  usual content drift; `"math"` is the knob for a like-for-like replay.
- `--deterministic-gpu` (`torch.use_deterministic_algorithms(True)`) refuses
  the cuDNN SDPA kernel; with MATH in the list the forward silently runs math.
  The loader warns in that case. cuDNN fprop is itself deterministic on one
  machine and cuDNN version (r1 == r2 above), so the flag is not needed for
  reproducibility of the benchmark.
- A machine without cuDNN attention for this shape (pre-sm80, or a CPU
  reranker) falls back to MATH through the in-list fallback; the
  `can_use_cudnn_attention` verdict is logged at load.
- The H012/H004 label fix changes the 133q view for every future leg; the
  old-label aggregates are kept in the A/B doc for the record.
