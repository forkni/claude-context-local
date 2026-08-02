# PPR Ego-Graph Expansion — Opt-In Latency Profile (2026-08-02)

Arm B of the post-recall-campaign plan. PPR (`ego_graph.expansion_mode: "ppr"`)
was REJECTED for recall (commit `7ca126d`); this arm measured it as a latency
profile on the deterministic substrate (ADR-0021, `PYTHONHASHSEED=0` pinned).

**Verdict: DOCUMENTED as a supported opt-in per-project latency profile.
Default stays `bfs`.** −15.8% average query latency, replicated exactly, with
a priced-in recall debit (recall@20 −0.0250, MRR flat).

## Setup

- Substrate: index @ 2,286 chunks, post-B1 source (commit `e81c7db` adds the
  `ego_expansion` timing stage — proven behavior-neutral below; `918b3a5`
  later moved it from a `@timed` decorator to a call-site `timer()` so the
  method's chunk ID stays `method:` for golden-dataset stability, identical
  timing output). Deterministic harness (hash seed auto-pinned); fresh
  process per round, idle RTX 4090.
- Rounds: 1×131q `bfs` (same-session control; also verifies B1 neutrality)
  - 2×131q `--expansion-mode ppr`.

## B1 neutrality + control

The bfs control round is **0-flip identical** to the deterministic canon
(`sscg_hs0_expanded_r1_20260802.json`): MRR 0.6527, recall@10 0.7839,
recall@20 0.8365 exactly — the timing instrumentation is behavior-neutral and
the canon carries over. Latency 4,501 vs 4,471 ms (within noise).

## Results

| Arm | MRR | recall@10 | recall@20 | avg latency | ppr_fallbacks |
|-----|-----|-----------|-----------|-------------|---------------|
| bfs control (canon) | 0.6527 | 0.7839 | 0.8365 | 4,501 ms | 0 |
| ppr r1 | 0.6483 | 0.7742 | 0.8115 | 3,789 ms | 0 |
| ppr r2 | 0.6483 | 0.7742 | 0.8115 | 3,784 ms | 0 |

- **Determinism holds under ppr**: r1 ≡ r2, 0 MRR flips, 0 pool_hit flips,
  0.0000 spread on every metric.
- **Latency: −15.8%** (−712 ms/query), replicated to within 5 ms.

## Where the win actually is

Per-stage `[TIMING]` aggregates show the ego-expansion stage itself is NOT the
win — it is ~5 ms *slower* under ppr (36 vs 31 ms mean), and
`multi_hop_search`/hop-1 `neural_rerank` are flat. The saving is entirely in
the **post-expansion final listwise rerank**, driven by pool size:

| | bfs | ppr |
|---|-----|-----|
| mean post-expansion pool | 29.2 chunks | 21.7 chunks |
| neighbor-capping events | 112/131 queries | 0 |
| implied final-rerank cost | ~1,495 ms | ~811 ms |

BFS floods to the 20-neighbor cap on 112/131 queries; PPR's top-N-by-score
selection returns fewer, better-ranked neighbors and never hits the cap. The
smaller pool makes the final listwise pass ~680 ms cheaper — and is equally
the mechanism of the recall debit (fewer candidates survive to the k=20
window).

## Quality debit (exact under determinism)

- Aggregates: MRR −0.0044 (flat), recall@10 −0.0097, **recall@20 −0.0250**
  (the real cost — consistent with the recall-arm rejection), pool_hit net −1
  (Q101/Q102/H004 lost; Q119/Q121 gained).
- The known replicated losses reproduce exactly: Q51 0.5→0.333, Q70→0.0.
- 22 per-query MRR diffs vs canon total. Most are bimodal boundary queries
  re-freezing under ppr's different pool composition (Q102 1.0→0.0 while
  Q106 0.0→1.0 — the seed-0 realization swaps sides; H048/H052 0.5→1.0
  gains, Q126 1.0→0.333 loss). Per ADR-0021: judge on aggregates —
  realization swaps are not stable quality facts.

## Disposition

1. `expansion_mode` **default stays `bfs`** — best recall, canonical.
2. `ppr` is documented in `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`
   ("Latency profile") as a supported per-project opt-in via the ADR-0014
   `search_overrides.json` layer, with the measured numbers and the debit
   stated.
3. No new config code — `expansion_mode` has been live since ADR-0020.
4. The latency mechanism (pool size → final-rerank cost) suggests the same
   win is available to bfs by lowering `max_neighbors_per_anchor`, with its
   own recall trade-off — unmeasured, noted for any future latency campaign.

## Files

- Rounds: `benchmark_results/sscg_bfs_postB1_131q_r1_20260802.json`,
  `benchmark_results/sscg_ppr_hs0_131q_r{1,2}_20260802.json`
- Canon: `benchmark_results/sscg_hs0_expanded_r{1,2}_20260802.json`
- Prior recall rejection: `evaluation/RECALL_CAMPAIGN_CLOSEOUT_20260802.md`
