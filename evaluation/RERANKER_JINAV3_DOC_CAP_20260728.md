# Listwise reranker doc-cap sweep: 1000 vs 2000 chars (2026-07-28)

## Verdict: REVERT `listwise_doc_max_chars` TO 1000

## Motivation

A prior session raised `RerankerConfig.listwise_doc_max_chars` (the per-document
truncation budget `JinaRerankerV3` uses when packing all candidates into its
shared listwise context) from 1000 to 4000 chars, on the theory that the model's
131K-token context window and 2048-token per-document ceiling left "plenty of
headroom" — at 30 candidates the shared context only grows from ~5.4K to ~8.8K
tokens, and 0% of documents hit the 2048-token per-doc ceiling at either value.

This trial does not re-run the shipped 4000 value directly. It sweeps the two
values the original discovery work already had result files for —
**1000 (the pre-raise baseline) vs 2000 (an intermediate point)** — because
2000 already reproduces the failure mode this doc documents (VRAM exceeding the
physical card, bimodal latency with multi-minute stalls). Since cost is
hypothesized to scale roughly O(n²) in the packed sequence length, a value that
already breaks at 2000 does not need a 4000 run to be rejected: the live 4000
cap independently produced two `mcp__code-search__search_code` timeouts against
this exact project during unrelated plan-verification work in this same
session, which is corroborating field evidence, not just extrapolation.

## Pre-work

- Corpus/index unchanged — the reranker sits downstream of the index, so no
  reindex was needed between runs.
- Embedder: F2LLM-v2-0.6B (this project's configured default). Reranker:
  `jinaai/jina-reranker-v3`, `top_k_candidates` 30 (config default).
- Flags held constant across all four runs: `--k 7 --with-centrality
  --centrality-alpha 0.0`.
- `allow_ram_fallback: true` (local `search_config.json` default) was in effect
  for every run — this is precisely why VRAM overflow shows up as latency
  rather than an `OutOfMemoryError`.

## Protocol

Four runs, two per cap value, same session, same machine state, back to back:

| Run | Cap | Timestamp | Result file |
|---|---|---|---|
| r1 | 1000 | 2026-07-28T10:27:39 | `sscg_jinav3_cap1000_r1_20260728.json` |
| r2 | 1000 | 2026-07-28T10:34:17 | `sscg_jinav3_cap1000_r2_20260728.json` |
| r1 | 2000 | 2026-07-28T10:50:00 | `sscg_jinav3_cap2000_r1_20260728.json` |
| r2 | 2000 | 2026-07-28T11:12:48 | `sscg_jinav3_cap2000_r2_20260728.json` |

`config_metadata` in all four files confirms `reranker_model`,
`with_centrality`, `centrality_alpha`, `k`, and `project_path` are byte-for-byte
identical — the doc cap is the only variable that differs between the two
pairs. All four runs pass the benchmark's own gate thresholds (MRR ≥ 0.5,
recall@5 ≥ 0.55, hit_rate@5 ≥ 0.8) — the case against cap2000 is not that it
fails the gate, it's that it costs latency/VRAM for no quality gain.

## Results (mean of ×2)

| Metric | cap1000 (mean) | cap2000 (mean) | Δ |
|---|---|---|---|
| MRR | **0.682** | 0.665 | −0.017 |
| recall@20 | **0.813** | 0.789 | −0.024 |
| recall@50 | **0.815** | 0.794 | −0.021 |
| pool_hit_rate | **0.984** | 0.969 | −0.016 |
| success_count / 96 | **90** | 89 | −1 |
| avg_latency_ms | 3,986 | **11,876** | **+7,890 (~3×)** |
| peak_vram_reserved_gb | 13.0–13.5 | **27.66** | +14.2–14.7 |
| per-query p50 | 4.1s | **7.8s** | — |
| per-query p90 | 4.7s | **18.8s** | — |
| per-query max | 5.3s | **354.9s** | — |
| queries stalling > 8s | **0 / 96 (both runs)** | 42 / 96 (r1), 45 / 96 (r2) | — |

Per-run MRR: 0.6905 / 0.6735 (cap1000) vs 0.6667 / 0.6631 (cap2000) — cap1000
wins both replicates, but the −0.017 mean gap sits inside the ±0.02 single-run
MRR noise floor already established for this benchmark. recall@20 (−0.024) and
recall@50 (−0.021) are the only metrics that clear the noise floor, and they
move in cap1000's favor, not cap2000's — there is no metric where cap2000 wins
outside noise.

`peak_vram_reserved_gb` is identical to two decimal places across both cap2000
runs (27.66 / 27.66) despite wildly different latency — this is the WDDM
shared-memory spill's reservation ceiling, not per-run noise. On a 24GB card,
27.66 GB reserved is not physically possible as dedicated VRAM; the driver is
silently backing the excess with host RAM over PCIe, and `allow_ram_fallback:
true` means nothing intercepts that before it happens.

## Miss-set analysis

Comparing `hit` per query ID across all four runs (a query counts as a
consistent win/loss only if both replicates at a cap agree):

| Query | cap1000 (r1/r2) | cap2000 (r1/r2) | Note |
|---|---|---|---|
| Q121 | HIT / HIT | **MISS / MISS** | consistent loss at cap2000 |
| Q33 | MISS / MISS | **HIT / HIT** | consistent gain at cap2000 (mrr 0.25 vs 0.125–0.167) |

Exactly one query moves each way — this is noise-band churn, not a directional
pattern. Trading Q121 for Q33 is not a story of "cap2000 fixes real misses";
it's consistent with the −0.017 MRR delta being inside the noise floor, i.e.
neither cap is reliably better at the individual-query level either.

The latency picture tells a different, non-noise story. The worst stalls per
run:

- **cap2000 r1** (42 stalls / 96): Q73 51.5s (cap1000 baseline: 4.9s), Q50
  35.0s (4.1s), Q107 26.2s (4.4s), Q54 25.4s (4.4s), Q31 24.5s (4.9s), Q96
  24.0s (5.1s).
- **cap2000 r2** (45 stalls / 96): Q107 **354.9s** (4.4s baseline), Q110 97.1s,
  Q73 36.7s, Q126 27.2s, Q96 24.9s, Q102 23.0s.

Q107 illustrates the spill's non-determinism directly: 4.4s baseline at
cap1000, 26.2s in cap2000-r1, 354.9s in cap2000-r2 — an 80x spread on an
identical query against an identical index, which is a scheduling/contention
artifact of the shared-memory spill, not a property of that query's content.
Different queries dominate the stall list between r1 and r2, which is the same
signature: which allocation gets evicted to host RAM is not deterministic
per-query.

## Decision rationale

No quality metric improves at cap2000 outside the ±0.02 noise floor, and the
two metrics that do clear noise (recall@20, recall@50) favor cap1000. Against
that, latency roughly triples on average and up to ~80x for individual
queries, and reserved VRAM exceeds the physical 24GB card. Every criterion
points to keeping the lower cap; none point to raising it. Full reasoning and
the decision itself are recorded in
[ADR-0011](../docs/adr/0011-listwise-reranker-doc-cap.md), which reverts
`listwise_doc_max_chars` to 1000 in `search/config.py` and
`search/neural_reranker.py`. This document holds the sweep data; the ADR does
not repeat it.

## What stays from this work

- The falsified "no cliff at this scale" framing in
  `JinaRerankerV3.__init__`'s docstring and the class Performance block
  (`search/neural_reranker.py`) is corrected to describe the O(n²)
  activation-memory hypothesis and the measured spill, with a link back to
  ADR-0011.
- The truncation-rate finding (45.7% of chunks truncated at cap1000 vs 6.3% at
  cap4000) is retained as a candidate follow-up signal, not treated as
  decisive on its own — see the ADR's Considered Options.
- `scripts/benchmark/run_sscg_benchmark.py`'s `--listwise-doc-max-chars`
  argparse help text already read "Default: use config value (1000)" before
  this revert; it was stale relative to the shipped 4000 default and now
  matches the code again without further edits.
- The paper's own Table 5 (arXiv 2509.25085v4) independently supports this
  sweep's conclusion: it lists an "Effective Sequence Length" of 8,192,
  distinct from the 131,072 "Context Length" the original cap4000 rationale
  reasoned against — the ~8.8K-token estimate for cap4000 already crossed
  that tighter figure. See ADR-0011 for the full framing.

## Follow-ups

- Set `allow_ram_fallback: false` so a future VRAM-sizing regression raises a
  loud `OutOfMemoryError` instead of a silent multi-minute stall. Tracked as a
  separate change in ADR-0011, not bundled into this revert.
- If a smaller/more VRAM-efficient listwise model replaces `jina-reranker-v3`,
  or reference hardware gains meaningfully more dedicated VRAM, or
  `top_k_candidates`/`block_size` changes the packed-sequence length, re-sweep
  before assuming 1000 is still the right ceiling — see ADR-0011's
  re-evaluation triggers.
- An intermediate cap (1500) was not tested; the point of this finding is that
  the safe ceiling is empirical, and 2000 already reproduces the failure mode,
  so bisecting further was not pursued without a concrete reason to raise the
  cap again.
