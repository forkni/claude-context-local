# Bound the Jina listwise packed window by tokens

Status: accepted
Date: 2026-09-19

`JinaRerankerV3.rerank()` packs every candidate document into one flat prompt
and scores them in a single forward pass. On token-dense corpora (TD operator
chunks) that pass raises `torch.cuda.OutOfMemoryError`. This ADR bounds the
packed window by tokens instead, engaging a multi-block regime Jina already
ships but that nothing in this codebase previously used.

## Context

Diagnosed in `evaluation/RERANKER_TD_TOKEN_DENSITY_20260919.md` (committed as
`08d99f1f`). The symptom is not a crash: `RerankingEngine._run_rerank`
(`search/reranking_engine.py`) already catches the OOM, logs a warning,
returns the candidates unreranked, and sets `_session_oom_detected = True` —
which disables neural reranking for **every subsequent search in the
session** (reset only by `reset_session_state()`). The real cost is silent
recall loss: one dense query turns off the reranker for the rest of the
session with nothing telling the caller.

**Mechanism.** The checkpoint's `config.json` declares `num_attention_heads:
16`, 28 layers, hidden 1024, bfloat16. Two live `[1, 16, L, L]` attention
score buffers give **64 bytes/element × L²** on top of a several-GiB floor —
quadratic in the packed sequence length `L`, not linear.

**Why it was unbounded.** `_PINNED_RERANK_LENGTH_KWARGS`
(`search/neural_reranker.py`) pins `max_doc_length=2048` /
`max_query_length=512`, bounding each *document* but never their **sum**;
`RerankerConfig.top_k_candidates` bounds document *count*, not token mass.
Nothing bounded `L` itself.

**The fix.** Jina's own `rerank()` (vendor `modeling.py`, `trust_remote_code`)
already has a multi-block regime: it reads `max_length =
self._tokenizer.model_max_length`, derives `length_capacity = max_length -
2 * query_length`, and flushes a block whenever `len(block_docs) >=
block_size` (125) or `length_capacity <= max_doc_length`. The shipped
`model_max_length` is huge (`max_position_embeddings: 131072`), so the loop
degenerates to one block regardless of how many candidates are packed.
Lowering `model_max_length` engages the vendor's own sub-blocking — no
hand-built prompts, no attention changes, no new inference code. This class's
docstring already forbids constructing the sandwich prompt by hand; this fix
respects that constraint by working entirely through the tokenizer.

### Recall risk is real but bounded to the tail

Attention inside one packed block is plain causal over the flat prompt —
`_compute_single_batch` builds its mask from the tokenizer's own
`padding=True, padding_side="left"` call, nothing custom, so there is no
per-document isolation between candidates sharing a block. Splitting into
blocks is therefore not free:

1. **Block 1 is near-invariant.** Candidates are packed in fusion/RRF order,
   so an unsplit window and a split one put the same leading candidates in
   block 1 with the same predecessor set — only a preamble literal
   (document count) differs.
2. **Perturbation lands on the fusion tail.** Block 2+ candidates lose their
   block-1 predecessors and are renumbered from zero, so the model reads them
   as an independent ranking task. These are exactly the low-RRF tail
   candidates a caller is least likely to have already trusted.
3. **The query vector changes globally but coherently** — one weighted
   average of per-block query embeddings scores every document; no
   cross-block scale mismatch.

This is why the derivation below carries a soft invariant keeping block 1 at
least `top_k` candidates deep: the un-degraded, highest-confidence slice of a
search should never itself shrink below what the caller asked for.

> **Correction (2026-09-19, ADR-0077):** claim 1 above ("block 1 is
> near-invariant") is refuted. Vendor `modeling.py` discards per-block
> scores entirely and computes one global sort over a query vector that is
> the *max-weighted average* of every block's query embedding
> (`np.average(query_embeddings, axis=0, weights=block_weights)`,
> `weights` = each block's best score) — so a strong hit in block 2 tilts
> the reference vector block 1 is scored against, too. There is no
> un-degraded slice when the final sort is global. The 3-leg gate on this
> ADR's own commits confirmed it empirically: forcing a multi-block split
> (Leg 3) moved recall@5/NDCG@5 — the *head* of the ranking, not the tail —
> by more than the pre-registered ±0.02 tolerance. Claim 3 (the query
> vector changes globally) was correct and is what actually explains the
> damage. ADR-0077 replaces the soft "first block ≥ top_k" invariant below
> with a hard single-block invariant enforced by adaptive per-document
> truncation; this ADR's token-budget derivation, OOM retry, and
> `RuntimeError` contract are unchanged and remain in effect as the backstop
> for when that truncation under-shoots. See
> `docs/adr/0077-single-block-listwise-invariant.md`.

## Decision

### New config field

`RerankerConfig.listwise_packed_token_budget: int = 8192`
(`search/config.py`) — `construction_baked=True` (baked into `JinaRerankerV3`
at construction, alongside its sibling length knobs `doc_max_chars` /
`listwise_doc_max_chars` / `listwise_dtype`), `range=(2048, 32768)`, `env=`
set (no `mcp=` — not caller-tunable per search). At 8192 the fitted peak is
~11.3 GiB, inside the tightest observed cap (11.99 GiB) with headroom.

### Derive `model_max_length` by greedy-fill simulation

`search/neural_reranker.py` adds `_simulate_listwise_blocks`,
`_packed_block_length`, and `derive_listwise_model_max_length` as pure,
independently testable functions (no tokenizer or model dependency): they
mirror the vendor's own block-flush loop exactly, including that a block can
overshoot the token budget by up to one document since the loop appends
before checking capacity — which is also why the derivation cannot be
closed-form or binary-searched (block boundaries shift with the candidate
`model_max_length`, so validity is not strictly monotone in it). The search
seeds from a closed-form upper bound, then verifies by simulation and steps
down (bounded coarse-then-fine scan) until every simulated block validates
against the budget.

Two invariants:

- **Hard floor:** `model_max_length >= 2 * query_length + max_doc_length +
  1` — one document per block is the minimum unit of progress.
- **Soft invariant:** among valid values, prefer the largest whose first
  block holds at least `top_k` documents; when none does, take the largest
  valid value and log a warning rather than fail the request.

`JinaRerankerV3._attempt_rerank` applies the derived value to
`model._tokenizer.model_max_length` (after `model._ensure_tokenizer()`,
since the tokenizer is lazily loaded and its pre-load can legitimately have
failed) and restores the original value in `finally`, on every code path —
the tokenizer is shared, cached state on a long-lived model. The mechanism
is gated on `_resolve_length_kwargs(model)` being non-empty: v3.5 has no
`max_doc_length`/`max_query_length` parameters, hardcodes different lengths,
and uses hybrid sliding-window attention with different O(L²) scaling, so
this ADR's mechanism does not apply to it — the gate is the same
capability probe `_resolve_length_kwargs` already performs to decide
whether to pass the length pins at all.

### Tier 2 — one halved-budget retry on OOM

`rerank()` calls `_attempt_rerank` up to twice when the window-bounding
mechanism can engage: once at `listwise_packed_token_budget`, and — only on
`torch.cuda.OutOfMemoryError` — once more at half that budget, before giving
up. `_attempt_rerank`'s own `finally` empties the CUDA cache on every
attempt (the same pool-wide policy this class already followed pre-fix, now
run once per attempt instead of once per call, so the retry starts from a
clean cache). No dynamic VRAM-fraction bound was added — no such probe
exists in this codebase, and the fitted quadratic model above rests on a
five-point curve, not enough to trust a live per-process fraction.

The final `RuntimeError` message on exhausted retries is preserved
**verbatim** (`f"Insufficient GPU memory for reranking: {e}"`) — this string
is load-bearing: `RerankingEngine._run_rerank` detects OOM by matching
`"cuda"` and `"out of memory"`/`"oom"` on `str(e)` to set
`_session_oom_detected`. Changing the message, or switching to a typed
exception, would silently break that session-disable backstop.

### Surface the degradation to callers

Both possible degradations are now reported, not just the pre-existing
silent one:

- `JinaRerankerV3.last_block_count` records the block count from the most
  recent `rerank()` call (`None` when the mechanism didn't engage).
  `RerankingEngine._run_rerank` copies it (and a new
  `last_rerank_skipped` flag) onto `self`, alongside the existing
  `last_window_ids` — same "last pass wins" semantics, and recorded inside
  `_run_rerank` itself rather than at a call site, since a hop-1
  `apply_neural_reranking` pass can reach it without going through
  `rerank_by_query` at all. `_run_rerank`'s signature is unchanged —
  `evaluation/probe_harness.py`'s `ProbeSession.instrument` patches it
  directly.
- `mcp_server/tools/searcher_view.py` gains a read-only `reranking_engine`
  property (styled on the existing `index_manager` property) so MCP handlers
  reach the engine only through `SearcherView`, never by reaching into the
  searcher directly.
- `mcp_server/tools/search_orchestrator.py`'s `_build_response` gains
  `rerank_block_count` / `rerank_skipped` parameters, threaded from
  `_assemble` (which already builds a `SearcherView` and already threads
  `reindexed` the same way — no new `ExecutionOutcome` field was needed).
  Two system messages, mirroring the existing `index_refreshed` block: a
  block-split note, and the OOM-fallback note that was previously silent.

## Considered Options

- **Lower `listwise_doc_max_chars` instead.** Rejected: that field is
  `construction_baked`, benchmark-relevant (ADR-0011), and bounds per-document
  length, not the packed window's total token mass — it does not by itself
  prevent an OOM on a corpus with many long documents.
- **A dynamic, live VRAM-fraction-derived budget.** Rejected: no
  `get_per_process_memory_fraction()`-style probe exists in this codebase,
  and the fitted VRAM-vs-length curve behind this ADR rests on five data
  points — not enough to trust a live per-process bound over a fixed,
  benchmarked ceiling.
- **Hand-build a smaller sandwich prompt ourselves instead of using Jina's
  block loop.** Rejected outright by this class's own docstring/design
  constraint: `JinaRerankerV3` must never construct the listwise prompt by
  hand (`format_docs_prompts_func` and its special embedding-marker tokens
  are the model's own responsibility). Working through
  `model_max_length` keeps 100% of prompt construction inside vendor code.
- **Binary-search `model_max_length`.** Rejected: block boundaries are not a
  monotone function of `model_max_length` (a block can overshoot by up to
  one document), so eliminating half the search space on an assumed trend
  risks missing a valid, larger value. The chosen coarse-then-fine linear
  scan always re-verifies by direct simulation.

## Consequences

- No OOM at any window size or density that this budget was calibrated
  against; reranking is no longer silently disabled for a whole session
  without the caller being told.
- A benign perturbation is introduced on the fusion tail of split searches
  (see "Recall risk" above) — measured, not assumed, via the three-leg gate
  in the companion plan (self-index no-split control expected bit-identical;
  self-index sensitivity leg within the pre-registered ±0.02 drift band;
  the OOM corpus is the only leg where recall can actually move).
- `listwise_packed_token_budget` is not `benchmark_locked` — it is a safety
  ceiling, not a quality-tuned value, and may be revisited once real-corpus
  data on split frequency accumulates.
- Cross-references, does not supersede, **ADR-0011**: its trigger #3 flags
  the multi-block regime as untested against `top_k_candidates` exceeding
  Jina's `block_size = 125`; this ADR is that test. ADR-0011's own decision
  (the 1000-char `listwise_doc_max_chars` cap) and `accepted` status are
  unaffected — that field still bounds per-document length independently of
  this one bounding the packed window.
- Precedent: **ADR-0007** (now superseded — the ONNX path it described was
  deleted wholesale, ADR-0016) had already decided, one layer down, "one
  2048-token contract, both ends" and that the contract length is
  deliberately *not* the model's max context. This ADR is the same shape of
  decision — a token budget chosen for a governing cost, not for the
  model's advertised window — applied to the listwise reranker instead of
  the embedder.

## Standing risk — no upstream revision is pinned

The fix depends on vendor internals (`trust_remote_code`) at the currently
cached checkpoint revision (`10fb694fc21f…`); no revision is pinned anywhere
in this repository. A future republish of `jinaai/jina-reranker-v3` could:

- Change the block-flush rule (`block_size`, the `length_capacity <=
  max_doc_length` condition, or the block-boundary accounting this ADR's
  simulation mirrors), silently invalidating the derivation's agreement with
  the real loop.
- Add `truncation=True` to `_compute_single_batch`'s tokenizer call, which
  today passes no such argument — a lowered `model_max_length` currently
  only emits a length warning and never truncates the packed prompt. If a
  republish added truncation, this mechanism would start silently dropping
  content instead of splitting it.

This is a standing risk, not a resolved one — mitigated by a guard test
(`tests/unit/search/test_jina_reranker_v3.py`) that asserts the vendor call
site does not pass `truncation=True`, so a republish that changes this trips
a test failure instead of a silent behavior change.

## Glossary

- **Listwise block:** one packed prompt scored in a single forward pass. A
  rerank window is covered by one or more blocks; document ids restart
  within each block (Jina's own indexing, not ours).
- **Packed-token budget:** the ceiling, in tokens, on one block's packed
  prompt length (query + preamble + every document in that block) — distinct
  from `max_doc_length` (the per-document cap) and `top_k_candidates` (the
  window's document count).

## Re-evaluation triggers

Reconsider this design if any of the following hold:

1. The vendor checkpoint republishes with a different block-flush rule or
   adds truncation to `_compute_single_batch` (see "Standing risk" above).
2. `top_k_candidates` or `listwise_doc_max_chars` change enough that the
   soft top-k invariant routinely fails to hold even at the maximum allowed
   budget (32768) — that would indicate the budget range itself needs
   revisiting, not just the default.
3. A smaller or more VRAM-efficient listwise model replaces
   `jinaai/jina-reranker-v3`, changing the 64 B/element factorization this
   ADR's default was calibrated against.
