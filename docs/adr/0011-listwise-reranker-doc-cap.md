# Cap JinaRerankerV3's listwise document budget at 1000 chars

Status: accepted
Date: 2026-07-28

`RerankerConfig.listwise_doc_max_chars` (`search/config.py`) governs how much
of each candidate's body `JinaRerankerV3` feeds into its shared listwise
context. A prior change raised it from 1000 to 4000; this ADR reverts that
change after a measured sweep showed the higher cap costs VRAM and latency
without a quality gain.

## Context

The 4000 default was justified by context-window occupancy:
`jina-reranker-v3` packs all candidates into one shared context (up to
131K tokens), and at 30 candidates the shared context only grows from
~5.4K to ~8.8K tokens going from a 1000- to a 4000-char cap — comfortably
inside the window, and 0% of individual documents crossed the model's own
2048-token per-doc ceiling at either cap. The `__init__` docstring concluded
"there is no cliff at this scale," and raising the cap also cut truncated
chunks in this index's corpus from 45.7% to 6.3%.

A 4-run SSCG benchmark sweep (two runs at each cap, identical `k=7`,
`centrality_alpha=0.0`, same embedder, cap the only variable) falsifies
that conclusion:

- MRR: 0.682 (cap1000) vs 0.665 (cap2000) — a −0.017 delta, but this sits
  *inside* the ±0.02 single-run MRR noise floor already established for
  this benchmark, so the honest reading is "no quality gain demonstrated,"
  not "a proven regression." `recall@20` (0.813 → 0.789), `recall@50`
  (0.815 → 0.794), and `pool_hit_rate` (0.984 → 0.969) move the same
  direction, all similarly close to noise.
- Mean rerank latency roughly tripled (~3,986ms → ~11,876ms), and the
  per-query distribution turned bimodal: cap1000 ran p50 4.1s / p90 4.7s /
  max 5.2s with zero queries over 8s; cap2000 ran p50 7.8s / p90 ~18.8s /
  **max 354.9s**, with **42–45 of 96 queries** stalling past 8 seconds.
- `peak_vram_reserved_gb` measured **27.66** at cap2000 on a **24GB** card —
  physically impossible as dedicated VRAM. This is direct evidence of a
  WDDM shared-memory spill: on Windows, the driver silently backs excess
  allocation with host RAM over PCIe rather than raising `OutOfMemoryError`.
  `allow_ram_fallback: true` (the local `search_config.json` default) makes
  `set_vram_limit()` skip the PyTorch VRAM cap entirely, so nothing
  intercepts the spill before it happens — it only shows up as latency.

The two runs were verified identical apart from the cap (same golden set,
same other config), so the cap is the only plausible explanatory variable.

## Decision

Revert `listwise_doc_max_chars` to **1000**, in `RerankerConfig`
(`search/config.py`), `JinaRerankerV3.__init__` and `create_reranker`
(`search/neural_reranker.py`). This does not touch `doc_max_chars`, the
separate *pointwise* budget used by `GenerativeReranker`, which stays at
4000 — its cost scales with `batch_size`, not with the full candidate pool
packed into one sequence, so it was never part of this sweep.

The original 1000-vs-4000 measurement was internally correct but incomplete:
it measured **context-window occupancy** (tokens against the 131K window)
and the **per-document token ceiling** (2048), and both checked out fine at
4000. Neither measures **attention activation memory during the forward
pass**, which is believed to be the actual binding constraint here: it
scales roughly O(n²) in the packed sequence length for a listwise model,
where context-window occupancy scales only linearly. The measured VRAM
ratio (27.66 / 13.2 ≈ 2.1×) sits closer to the sequence-length ratio
squared (≈2.66×) than to the sequence-length ratio itself (≈1.6×), which
is consistent with an O(n²) activation-memory mechanism — this is a
plausible explanation given the numbers, not a proven one; no profiler
trace was captured to confirm it directly.

## Considered Options

- **Keep the 4000 cap.** Rejected: no quality metric improved outside the
  noise band, latency roughly tripled, and reserved VRAM exceeded the
  physical card on the reference hardware.
- **Pick an intermediate cap (e.g. 1500–2500).** Rejected for now — the
  sweep only measured the two endpoints, and the entire point of this
  finding is that the safe ceiling is empirical, not something to guess at
  a third time without measurement. A future sweep could bisect if the
  1000-char truncation rate (45.7% of chunks in this index) becomes a
  problem worth revisiting.
- **Leave the cap at 4000 and instead set `allow_ram_fallback: false`** so
  a spill raises `OutOfMemoryError` instead of silently stalling. This is a
  real, separate improvement — it converts a silent multi-minute stall into
  a loud, immediate failure — but it does not fix the underlying cost, and
  is tracked as a follow-up rather than bundled into this revert.
- **Treat the 6.3%-vs-45.7% truncation-rate improvement as decisive on its
  own.** Rejected: truncation rate is an input-side proxy for how much
  content the reranker sees, not an outcome measure. The corpus's own MRR
  and recall numbers did not improve when truncation dropped, so the proxy
  did not translate into the result it was meant to serve.

## Consequences

- `JinaRerankerV3` truncates document bodies to 1000 chars again, matching
  the value the corpus was last measured under; no reindex or benchmark
  re-run is required to restore consistency.
- The class docstring's Performance block (`neural_reranker.py`) is
  re-labeled as measured at this 1000-char cap, since it always was — it
  had silently stopped describing the shipped default once that default
  moved to 4000 without the docstring being updated in step.
- `allow_ram_fallback: true` remains the default, so a future config change
  that revisits the cap (or any other reranker sizing change) can still
  silently spill instead of failing loudly. See the follow-up above.

## Re-evaluation triggers

Reconsider raising this cap if any of the following hold:

1. A smaller or more VRAM-efficient listwise model replaces
   `jina-reranker-v3`, changing the activation-memory cost per token.
2. The reference hardware changes to a card with meaningfully more
   dedicated VRAM than 24GB.
3. `top_k_candidates` (currently 30) or the model's `block_size` changes,
   altering the packed-sequence length this cap multiplies against.

Absent one of these, re-testing this exact configuration is unlikely to
produce a different result.
