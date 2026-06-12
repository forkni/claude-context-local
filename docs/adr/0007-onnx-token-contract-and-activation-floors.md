# 2048-token ONNX contract and `max()` activation-cost floors

Status: accepted
Date: 2026-06-12

The ONNX inference path pins a **2048-token length contract** shared by the
tokenizer and the dynamic batch-sizer, and resolves per-item activation cost as
`max(measured/analytical, calibrated_floor)` rather than trusting a single
runtime probe. Both decisions trade a little indexing throughput for OOM safety
and quality on long code chunks.

## Context

The dynamic batch-sizer (`embeddings/embedder.py::calculate_optimal_batch_size`)
divides an activation budget by a per-item activation cost to pick a batch size.
Two things make this fragile on the ONNX Runtime (ORT) backend, especially on
memory-constrained GPUs (the 8 GB dev box):

1. **Length contract drift.** Activation cost scales with sequence length. The
   ORT path has no Flash-Attention, so it materializes a full T×T attention
   matrix and cost grows quadratically with T. Embedding models advertise large
   context windows (BGE-M3: 8192), but using `model_max_length` to size batches
   would massively over-estimate cost, while letting the tokenizer truncate at a
   different length than the batch-sizer assumed would silently under-estimate
   it. The tokenizer's truncation length and the batch-sizer's effective length
   (`t_eff`) must agree, or the safety margin is meaningless.

2. **Unreliable runtime measurement on ORT.** The loader probes activation cost
   with a warmup batch. On PyTorch this is a true marginal cost (`torch`
   peak-allocated delta). On ORT the only available signal is an NVML used-memory
   delta, which captures **BFCArena** arena growth (large contiguous buffers
   reserved up front) rather than the marginal per-item cost — it over-reports by
   several×. ORT single-op peaks (an attention MatMul, a residual Add) also do
   **not** scale linearly with batch, so a per-item estimate extrapolated from a
   small probe can be blown past by one large op at a bigger batch, causing a
   first-try OOM.

## Decision

### #46 — one 2048-token contract, both ends

- **Tokenizer:** `embeddings/onnx_wrapper.py` caps truncation at
  `min(model_max_length, 2048)` (`_max_len`, lines 116-124).
- **Batch-sizer:** `estimate_activation_gb_from_config` uses `t_eff = 2048`
  (`embeddings/embedder.py:180`).

2048 is the single source of truth for "how long is a representative chunk".
Code chunks regularly reach 1500–3000 tokens, so 2048 keeps quality high (no
aggressive truncation of large chunks) while bounding the quadratic ORT
attention cost. The value is deliberately **not** the model's max context. The
fix is the *consistency* between the two ends, not either number alone.

### #54 — calibrated floors as a permanent `max()` lower bound

- Keep `MODEL_ACTIVATION_COST_OVERRIDES_ONNX`
  (`embeddings/embedder.py`: `BAAI/bge-m3` → 0.28, `Alibaba-NLP/gte-modernbert-base`
  → 0.25 GB/item) as a **permanent** floor, not a fallback to be deleted once
  measurement works.
- Resolve the ONNX per-item cost as `max(estimate, floor)` via the Tier 2/Tier 3
  logic in the dynamic-batch consumer: analytical estimate first, then raise to
  the floor when the floor is larger.
- Probe with **2048-token** representative text so any measurement that *is* used
  reflects peak-length inputs: `_WARMUP_TEXT` is repeated to ~2048 tokens
  (`embeddings/model_loader.py:42`, `* 32`), matching the #46 contract.

### Interaction with the ONNX measurement fix (commit `2608aca`)

As of `2608aca`, the ONNX path **ignores the runtime-measured value entirely**
for batch sizing (the arena-polluted NVML delta is logged for diagnostics only),
so the resolved cost is effectively `max(analytical_estimate, floor)`. This makes
the calibrated floor *more* load-bearing on ORT, not less — it is the backstop
that keeps the first-try batch from OOMing, independent of any probe. The PyTorch
path is unchanged: it uses its trustworthy measured value directly and has no
floor.

## Consequences

- **Smaller batches / slower indexing on the ONNX path** in exchange for not
  OOMing on the first batch of a memory-constrained GPU. Accepted: correctness
  and "it runs at all" beat throughput here. On the 8 GB box the ONNX path showed
  no throughput win over PyTorch regardless (see `2608aca` analysis), so the
  trade is cheap in practice.
- The 2048 contract is enforced in two files that must change together. A comment
  at each site (`onnx_wrapper.py:118-119`, `embedder.py` `t_eff`) cross-references
  #46 so the coupling is visible.
- Floors are validated against a force-reindex on the constrained GPU; the
  in-code comments record the observed single-op peaks (e.g. BGE-M3 wanted 941 MB
  for one Add at batch=16) that justify each number. Re-validate on a force-reindex
  before changing them.
- PyTorch users see none of this: no floor, real measured cost, full-length
  `t_eff` only via the shared estimate path (which they rarely hit because their
  measured value is trusted).

## Alternatives considered

- **Use `model_max_length` (e.g. 8192) for `t_eff`.** Rejected: massively
  over-estimates activation cost → batch size collapses to 1–2 with no quality
  benefit, since real chunks are far shorter than 8192.
- **Delete the floors once the runtime probe works.** Rejected: the ORT probe
  fundamentally cannot measure marginal per-item cost (BFCArena + non-linear
  single-op peaks), so there is no "working probe" to fall back to. The floor is
  the measurement of record for ORT.
- **Trust the NVML delta and skip the floor.** Rejected — it over-reports by
  several× and silently defeats the floor; see `2608aca`.
