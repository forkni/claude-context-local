# Multi-hop expansion 0.25 A/B — REJECTED (2026-08-02)

## Verdict

**REJECTED.** Halving the multi-hop expansion factor (0.5 → 0.25) improves
pool_hit_rate but converts none of that into watch-list ranking wins, and it
causes two large, replicated, arm-attributable regressions on queries that are
rank-1 at baseline (H034 1.0 → 0.2, H067 1.0 → 0.5). Aggregate MRR is flat.
The deployed `multi_hop.expansion_factor` stays 0.5.

This was the last surviving Phase-3 arm from
`evaluation/MULTIHOP_POOL_FLOODING_20260728.md`; with it rejected, the
pool-flooding family of config levers is exhausted — the remaining lever is
the reserve-at-final-pool-assembly *design* (code, not config), unchanged.

## Arms

Same INDEX_VERSION-4 index (2,253 vectors), sequential same-session runs.

| Run | Config | File |
|-----|--------|------|
| bf16 baseline r1/r2 (pre-ADR-0020 substrate) | default | `sscg_expanded_h_20260802_r{1,2}.json` |
| fp32 r1/r2 (same-session control) | `--reranker-dtype fp32` | `sscg_fp32_expanded_r{1,2}_20260802.json` |
| mhexp025 r1/r2 | `--multi-hop-expansion 0.25` | `sscg_mhexp025_expanded_r{1,2}_20260802.json` |

The fp32 rounds double as a **same-session quality-neutral control** (fp32 was
separately shown quality-flat, `RERANKER_FP32_DETERMINISM_AB_20260802.md`) —
any query that moves identically in fp32 and mhexp025 is session/substrate
drift, not an expansion effect. This control is what makes the per-query
attribution below trustworthy.

## Results — aggregates (131q)

| Metric | base r1/r2 | mhexp025 r1/r2 | delta vs base |
|--------|-----------|----------------|---------------|
| MRR | 0.6591 / 0.6587 | 0.6550 / 0.6487 | −0.004 / −0.010 (flat) |
| recall@10 | 0.7669 / 0.7633 | 0.7949 / 0.8002 | +0.03 (but fp32 control also +0.03 → mostly drift) |
| recall@20 | 0.8179 / 0.8108 | 0.8434 / 0.8217 | +0.02–0.03 |
| pool_hit_rate | 0.9695 / 0.9542 | **0.9771 / 0.9695** | genuinely better (min ≥ every other run's max) |
| avg latency | 4,470 ms | 4,515 ms | flat |

The pool_hit gain is real and mechanistically expected (less hop-2 flooding →
fewer hop-1 golds displaced from the final pool) — but it does not convert to
MRR because the queries it protects were already boundary-riding.

## Results — per-query attribution (six-run table)

| id | base r1/r2 | fp32 r1/r2 (control) | mh25 r1/r2 | Attribution |
|----|-----------|----------------------|------------|-------------|
| H034 | 1.000 / 1.000 | 1.000 / 1.000 | **0.200 / 0.200** | **arm-caused loss** (replicated) |
| H067 | 1.000 / 1.000 | 1.000 / 1.000 | **0.500 / 0.500** | **arm-caused loss** (replicated) |
| Q86 | 0.333 / 0.333 | 0.333 / 0.333 | 0.143 / 0.200 | arm-caused loss |
| Q70 | 0.111 / 0.125 | 0.125 / 0.143 | 0.000 / 0.000 | arm-caused loss (gold drops out of top-10) |
| Q01 | 0.167 / 0.167 | 0.200 / 0.200 | 0.500 / 0.333 | arm-caused win (only clear one) |
| H012 | 0.111 / 0.143 | 0.143 / 0.167 | 0.333 / 0.250 | modest arm win |
| Q81 | 1.000 / 1.000 | 0.500 / 0.500 | 0.500 / 0.500 | **substrate drift** (both arms identical) |
| Q123 | 0.500 / 0.500 | 0.250 / 0.250 | 0.250 / 0.250 | substrate drift |
| Q105 | 0.500 / 0.500 | 0.250 / 0.333 | 0.250 / 0.333 | substrate drift |
| Q133 | 0.000 / 0.000 | 0.500 / 0.500 | 0.500 / 0.500 | **substrate drift** (rescued in BOTH arms — not creditable to either) |
| Q102 | 1.000 / 0.000 | 1.000 / 0.000 | 0.000 / 0.000 | bf16 flapper (coin-flip) |
| Q103 | 0.333 / 0.500 | 0.333 / 0.143 | 1.000 / 0.200 | flapper, no credit |

### Watch-list (the gate's primary criterion)

- **Q122**: 0.0 in all six runs — no rescue. Stays documented merged-cut miss.
- **Q121**: 0.0 in all six runs — no rescue. Stays rrf-arithmetic no-lever.
- **Q119**: 0/0 base, 0.2/0.111 fp32, 0/0 mh25 — flapper; no arm rescue.
- **H063**: 0.10–0.14 everywhere — flapper region, unchanged.
- **Q133**: rescued to 0.5 — but by the substrate (both arms), not by expansion 0.25.

**Primary criterion fails** (zero arm-attributable watch-list wins, four
arm-attributable losses including two large ones); guard passes (MRR flat);
secondary pool_hit direction positive but non-converting. Reject.

## Substrate-drift confound (actionable finding)

Q81 / Q105 / Q123 / Q133 moved identically in both arms relative to the
morning baseline while being round-stable within every session. The
`sscg_expanded_h_20260802_r*` baseline rounds predate commit `38950a4`
(ADR-0020 config-liveness changeset) — the arms ran on a different code
substrate than their baseline. A fresh post-ADR-0020 default-config 2-round
baseline (`sscg_post_adr0020_expanded_r{1,2}_20260802.json`) supersedes the
morning rounds as the comparison substrate for Step 4 (PPR) and all future
arms. Durable rule: **an A/B baseline must be re-run after any code commit
that touches the search path, even "audit/liveness" changesets.**

## Consequences

- `multi_hop.expansion_factor` stays 0.5 (deployed and default).
- Do not re-propose expansion-factor reduction for recall; the mechanism
  (less flooding) is real but the collateral (H034/H067-class demotions —
  fewer hop-2 chunks also means losing genuinely-relevant hop-2 context that
  was propping up those golds' listwise scores) replicates and outweighs it.
- Pool-flooding config levers are now exhausted; the remaining lever is the
  final-pool-assembly reserve design.
- F-via-similar informational note (Step 5): at k=7 the F-view MRR is 0.8519 —
  identical to the k=10 baseline (all F hits at rank ≤ 3);
  `sscg_f_via_similar_k7_20260802.json`.
