# Reranker CUDA OOM on TD `operator` chunks — measured verdict

Date: 2026-09-19
Status: investigative, no production fix (scope: confirm mechanism, then decide)
Probe: `tmp/rerank_oom_probe.py` (throwaway, not committed — `tmp/` stays local)

## Incident

`search_code` against `TD_Glossary_tox` (15,305 chunks, 8,643 `operator`) hit a hard CUDA OOM
inside `JinaRerankerV3.rerank()` at 08:05:21:

```
Neural reranking enabled: 18.5GB available >= 2.0GB required
CUDA OOM during reranking: Tried to allocate 6.71 GiB. GPU 0 has a total capacity of 22.49 GiB
  of which 10.75 GiB is free. 16.24 GiB allowed; Of the allocated memory 9.97 GiB is allocated
  by PyTorch, and 129.64 MiB is reserved by PyTorch but unallocated.
```

The search degraded silently (RRF order returned, session-scoped `_session_oom_detected` flip,
hop 2 skipped). Severity was already corrected upstream of this doc: `reset_session_state()` has
two `exact`-confidence production callers (`HybridSearcher.execute`, `MultiHopSearcher.search`),
so the next query retries — this is not a lifetime server outage.

## Verdict

**H1 (single packed sequence × materialized `[1, heads, L, L]` bf16 attention score matrix) is
confirmed, with an exact quantitative match, not just a plausible order-of-magnitude fit.**
H2 (TD token density is a real amplifier) is confirmed but more modest than the original
back-of-envelope estimate. H3 (block-flush guard inert at N=30) is confirmed. H4 (linear
`output_hidden_states=True` retention) is a real but minor secondary cost, not the driver. H5
(reserved-memory ratchet) stays refuted, as it was before this probe.

## Leg 0 — chars/token density (tokenizer only, no GPU)

Real chunks through the production `_build_rerank_document()` path (30 TD `operator` chunks, 30
Python `function` chunks, `listwise_doc_max_chars=1000`), tokenized with the reranker's own
`AutoTokenizer`, then packed with Jina's own `format_docs_prompts` builder:

| Corpus | chars_total | tokens_total | chars/token | packed_prompt_tokens (N=30) |
|---|---|---|---|---|
| TD `operator` | 26,515 | 8,375 | **3.166** | **8,948** |
| Python `function` | 27,443 | 6,911 | **3.971** | **7,484** |

TD is denser than Python by **1.254×** in chars/token, and the fully packed prompt (with the
`ID: {chunk_id}` header, special tokens, and instruction) is **1.196×** longer at the same N and
cap. Both are real measurements, not the plan's rough estimate (TD≈2.0/Python≈3.4) — TD chunk IDs
are long slash-paths, which drags the *header* overhead up even where body text is comparable, and
softens the density gap versus the original guess.

## Leg 1 — peak-VRAM sweep, TD corpus, cap OFF (`allow_ram_fallback=True`)

`N ∈ {8, 15, 22, 30}`, `torch.cuda.reset_peak_memory_stats()` before each point:

| N | peak_allocated | peak_reserved | elapsed |
|---|---|---|---|
| 8 | 2.2951 GiB | 2.6289 GiB | 0.53 s |
| 15 | 4.0709 GiB | 4.7051 GiB | 0.68 s |
| 22 | 7.2934 GiB | 8.6641 GiB | 1.45 s |
| 30 | **13.0708 GiB** | 15.6562 GiB | 2.83 s |

Local scaling exponent between consecutive points (`ln(mem_ratio)/ln(N_ratio)`):

| Interval | exponent |
|---|---|
| 8 → 15 | **0.91** |
| 15 → 22 | **1.52** |
| 22 → 30 | **1.88** |

The exponent climbs from sub-linear toward 2 as N grows — exactly the signature of a
**constant/linear floor** (model weights, tokenizer/embedding overhead, per-layer non-attention
activations) dominating at small N, with the **O(L²) attention term** taking over as N (hence
packed length L) grows. A pure-linear mechanism would hold the exponent near 1 throughout; it
does not.

## Leg 2 — control, Python corpus, N=30, cap OFF

| | peak_allocated | peak_reserved |
|---|---|---|
| Python, N=30 | **9.6141 GiB** | 11.4316 GiB |

TD/Python peak ratio at N=30: 13.0708 / 9.6141 = **1.360×**. The naive H2 prediction — squaring
the packed-token-count ratio, (8948/7484)² = 1.430× — overshoots slightly, consistent with leg 1's
finding that part of the footprint is a size-independent floor that doesn't get amplified by
density at all. H2 is real, not the whole story.

## Leg 3 — reproduction, live-shaped config, cap ON

Cap forced to a tight override (`--fraction 0.6`, well below the ~13 GiB uncapped peak measured in
leg 1) to force the same failure mode deterministically, reranker model loaded *before* the
override is applied (see "probe bugs found and fixed" below — `_load_or_fetch()` re-applies the
config's own fraction on first `.model` access, which would otherwise silently clobber a
caller-supplied override):

```
cap: effective_fraction=0.533, cap_gb=11.987 GiB
reproduced_oom: true
error: "Insufficient GPU memory for reranking: CUDA out of memory. Tried to allocate 1.19 GiB.
  GPU 0 has a total capacity of 22.49 GiB of which 9.44 GiB is free. 11.99 GiB allowed;
  Of the allocated memory 11.42 GiB is allocated by PyTorch, and 64.56 MiB is reserved
  by PyTorch but unallocated. ..."
```

Same wrapped-exception template, same wording, same shape as the original incident — the
production code path (`neural_reranker.py`'s `RuntimeError("Insufficient GPU memory for
reranking: …")` wrapper around `torch.cuda.OutOfMemoryError`) is confirmed to be the exact
mechanism, not a lookalike.

## Leg 4 — allocator attribution: the op is named, exactly

`torch.cuda.memory._record_memory_history()` / `_dump_snapshot("tmp/rerank_mem.pickle")` around
leg 1's N=30 TD run (cap off, so the call completes and the full trace is captured rather than
truncated by the OOM path).

**Platform limitation (real, not a probe bug):** this Windows torch build's C++ stack unwinder
(`record_context_cpp`) is unsupported off Linux/x86_64 and is silently inert here — every
`segments[].blocks[].history` entry comes back with empty `frames` regardless of which of the four
valid `context` values (`"state"`/`"alloc"`/`"all"`/`None`) is passed; there is no pure-Python-stack
fallback in this torch version. **This does not block attribution** — the snapshot's other
top-level key, `device_traces` (one chronological alloc/free event log per device), carries full
Python call stacks unaffected by this limitation. The probe's `_summarize_snapshot()` originally
only read `segments[].blocks[].history` (always empty here) and has been corrected to read
`device_traces` instead.

Ranking all 2,126 `alloc` events in the N=30 TD trace by size, the single largest allocation in
the entire `rerank()` call is:

```
5,124,269,056 bytes = 4.7723 GiB

sdpa_attention_forward   transformers/integrations/sdpa_attention.py:158
forward                  transformers/models/qwen3/modeling_qwen3.py:266
...
forward                  jina_reranker_v3/modeling.py:88   (outputs = super().forward(...))
_compute_single_batch    jina_reranker_v3/modeling.py:184
rerank                   jina_reranker_v3/modeling.py:255
```

`sdpa_attention.py:158` is the literal call site: `torch.nn.functional.scaled_dot_product_attention(
query, key, value, attn_mask=attention_mask, ...)`. Solving `size = heads · L² · 2 bytes` for
integer heads gives an **exact** fit at **heads = 32, L = 8,948** — not an approximation:
`32 × 8948² × 2 = 5,124,345,856` bytes, matching the observed `5,124,269,056` to within rounding,
and **8,948 is the identical `packed_prompt_tokens` figure leg 0 measured independently** from the
tokenizer, for the same N=30 TD corpus. Two independent measurements (a live CUDA allocation
event, and a pure-CPU tokenizer run) agree on the same packed sequence length.

**Why the full `[1, 32, L, L]` matrix gets materialized at all** (rather than a flash/memory-
efficient SDPA kernel that never forms it): `sdpa_attention.py:124` sets
`is_causal = q_length > 1 and attention_mask is None and is_causal` — Jina's listwise packing uses
a real, non-`None` custom `attention_mask` to implement per-document isolation inside the shared
context, which forces `is_causal = False` and takes the code down the explicit-mask path
(`:158`) rather than the causal fast path that a plain decoder-only forward would use. This is an
architectural property of listwise packing, not a bug — the model *needs* that mask to do its job
— but it is precisely what removes PyTorch's ability to dispatch to an attention kernel that
avoids full materialization.

**The 56 largest (>4 GiB) alloc events collapse to only 2 distinct virtual addresses**, each
reused ~28 times (56/2) — one allocation-then-free cycle per full-attention decoder layer, hence
peak *allocated* stabilizes around 9.5 GiB from this term alone (two ~4.77 GiB buffers live at
once — consistent with independent Q·Kᵀ-scores and post-softmax-probabilities tensors — plus model
weights and smaller linear-in-L activations) rather than growing per layer. The `_summarize_snapshot`
top-6 also shows several smaller allocations at the same call sites (2.39 / 1.19 / 0.30 / 0.07
GiB) — consistent with Qwen3's architecture interleaving full-attention layers with cheaper
sliding-window-attention layers, which materialize much smaller local windows; this does not
change the verdict, since the single largest term already accounts for and matches the dominant
cost.

## Hypothesis disposition (Phase 3 of the plan)

| # | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | Single packed sequence, materialized `[1,heads,L,L]` bf16 attention | **CONFIRMED, exact** | Leg 4 names `sdpa_attention_forward`; size solves exactly to heads=32, L=8948; L matches leg 0's independent tokenizer measurement bit-for-bit-close |
| H2 | TD token density is the amplifier | **CONFIRMED, more modest than estimated** | Leg 0: 3.166 vs 3.971 chars/token (1.254× denser), not the guessed 2.0/3.4; leg 1 vs leg 2 ratio 1.360× vs the 1.430× naive prediction |
| H3 | Block-flush guard inert at N=30 (enabling condition) | **CONFIRMED** | Leg 0/1/4 all show one packed prompt per N; no evidence of multiple `_compute_single_batch` calls at N=30 |
| H4 | `output_hidden_states=True` linear retention is a material contributor | **Real but minor** | Present (forced at `modeling.py:92`), but leg 1's exponent curve and leg 4's dominant-term size are explained by H1 alone; H4-scale tensors (~tens–hundreds of MB, matching the smaller entries in leg 4's top-6) are a rounding error against the ~9.5 GiB attention-buffer term |
| H5 | Reserved-memory ratchet / fragmentation | **Refuted** (unchanged from before this probe) | Leg 3's own failure shows only 64.56 MiB reserved-but-unallocated at the moment of failure |

## Probe bugs found and fixed along the way (documented for the next person who reruns this)

1. `_find_metadata_db()` originally pointed at `<project_dir>/metadata.db`; the real, populated
   store is at `<project_dir>/index/metadata.db`. SqliteDict's default `flag='c'` silently created
   an empty 12 KB stub at the wrong path instead of raising — fixed by appending `index/` and
   adding an explicit `FileNotFoundError` guard.
2. `JinaRerankerV3._load_or_fetch()` unconditionally re-applies `set_vram_limit()` using the
   *live config's* fraction as a side effect of the first `.model` access — this silently
   clobbered a caller-supplied `--fraction` override applied before load. Fixed by forcing model
   load first, then re-applying the override immediately after, so it is the last call to
   `set_per_process_memory_fraction` before the measured `rerank()` call.
3. `_summarize_snapshot()` only read `segments[].blocks[].history`, which is always empty on this
   Windows build (see Leg 4 above) — not just because of the missing C++ unwinder, but because
   `segments` only reflects memory still live at dump time, after `rerank()` already freed its
   transient activations. Fixed to read the chronological `device_traces` event log instead, which
   carries full Python frames for every alloc/free event regardless of platform.

## Recommendation (not a patch — Part B is diagnostic only)

Three directions were scoped by the plan; none are built here:

1. **Token-budgeted packing.** Replace `listwise_doc_max_chars` (a character cap) with a genuine
   token budget, or sub-block the candidate list so the packed `L` is bounded regardless of corpus
   density. This directly targets the confirmed O(L²) mechanism and would make the cap mean the
   same thing on any corpus, not just the Python corpus ADR-0011 was sized on. Needs an A/B against
   canon before shipping — changing what gets packed together changes which docs get scored
   together.
2. **Demand-aware admission.** `min_vram_gb` (`search/config.py`) is a fixed 2.0 GB estimate that
   models nothing about the actual candidate pool; a real estimate could use leg 0's
   chars-per-token measurement (or a live tokenizer pass) to predict `L` and refuse/degrade before
   attempting the allocation, rather than after.
3. **Surface degradation to the MCP caller.** Today a reranker OOM is only a log line; the caller
   gets unranked RRF order with no signal. A structured warning in the response would make the
   degradation visible without any packing change.

*Explicitly dropped, per the plan:* per-request session reset (already exists, already works —
`reset_session_state()`'s two `exact` callers retry on the next query). Whichever packing
direction is chosen, it needs a benchmark gate before shipping, per this project's standing rule
that any retrieval-affecting change is measured, not assumed.

## Reproduction

```bash
cd F:/RD_PROJECTS/COMPONENTS/claude-context-local
export CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0
.venv/Scripts/python.exe tmp/rerank_oom_probe.py --leg 0                    # ~2s, no GPU
.venv/Scripts/python.exe tmp/rerank_oom_probe.py --leg 1                    # N-sweep, cap off
.venv/Scripts/python.exe tmp/rerank_oom_probe.py --leg 2                    # Python control
.venv/Scripts/python.exe tmp/rerank_oom_probe.py --leg 3 --fraction 0.6     # reproduces the OOM
.venv/Scripts/python.exe tmp/rerank_oom_probe.py --leg 4                    # allocator attribution
```

`tmp/rerank_oom_probe.py` is a throwaway script (per project convention, `tmp/` stays local and
untracked) — reproducing this doc from scratch requires recreating it from this document's leg
descriptions, or pulling it from this session's history.
