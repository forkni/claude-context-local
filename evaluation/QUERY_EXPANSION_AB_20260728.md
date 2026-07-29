# Query Expansion A/B — Curated Vocabulary Variant Legs (2026-07-28)

**Verdict: FAIL on primary criterion (a) — feature ships disabled (`enabled=False`).**

Phase 3 of the SSCG follow-ups plan. Feature: curated concept→terms vocabulary
(`config/query_expansion_variants.yaml`, 12 concepts) matched by deterministic
trigger containment, fused as discounted extra BM25 legs through the N-list
`RRFReranker.rerank()`. Full design rationale: `docs/adr/0012-curated-vocabulary-query-expansion.md`.

## 1. Targets and premise check

Targets (96q expanded set, all `hit=False, pool_hit=False` in the fresh
post-cleanup control `qe_control_r1`, aggregate MRR 0.6638):

| ID | Query (abridged) | Gold |
|----|------------------|------|
| Q101 | "…write the analyzed relationships out so they survive a restart" | `CodeGraphStorage.save` |
| Q104 | "…discarding the stalest entries when the store grows past its limit" | `ChunkEmbeddingCache._evict` |
| Q122 | "hold several loaded encoders at once and drop the least valuable…" | `ModelPoolManager` |

Q103 hits on the current index (MRR 0.333) and dropped out of the target set.

The plan's premise ("BM25 ranks ~1500+, dense misses too") was written against
the pre-v4 index. **On the current v4 index (identifier-preserving tokenizer +
path/symbol token augmentation) the premise no longer holds for two of the
three targets** — see §3.

## 2. Feature verification (matcher and fusion behave as designed)

- Trigger matching fires correctly: Q101→persistence, Q104→eviction,
  Q122→pooling+memory_pressure; neutral queries ("where is QueryRouter
  defined", "find function estimate_tokens") match nothing.
- Variant legs find the golds: raw variant-BM25 rank of the gold is **3**
  for both Q101 (persistence leg) and Q104 (eviction leg). Q122's gold sits
  at rank 79 in the pooling leg (class-level chunk, BM25-unfriendly).
- Disabled/unmatched queries take the exact pre-existing `rerank_simple`
  path (regression-tested, 1,784 unit tests green).

## 3. Root cause: the misses are not (mostly) retrieval gaps

Stage-by-stage trace at benchmark geometry (k=10 → multi-hop `initial_k=20`,
`expansion=0.5`, `multi_hop_mode=hybrid`, listwise jina-reranker-v3):

| Query | hop-1 rank (OFF) | hop-1 rank (ON) | In expanded pool | Final rank (both arms) |
|-------|------------------|-----------------|------------------|------------------------|
| Q101 | absent (top-20) | absent (top-20) | no | miss |
| Q104 | **1** | **1** | yes (77-pool) | miss |
| Q122 | **6** | **6** | yes (66–83-pool) | miss |

- **Q104 and Q122 have no vocabulary problem on the v4 index.** Their golds
  rank 1 and 6 out of hop-1. The loss happens when hop-2 expansion floods the
  candidate pool to ~66–83 chunks and the **listwise neural reranker demotes
  the hop-1 winners** below the top-10. At k=5 (smaller pool: `initial_k=10`,
  fewer expansion sources) Q104's gold ranks **1** in final results — the
  identical query flips from hit to miss purely by pool size. Query-side
  expansion has no direct leverage on this stage (though it can perturb pool
  composition — see the Q122 flip in §4). (Flagged as a separate follow-up:
  multi-hop pool flooding demoting hop-1 top hits.)
- **Q101 is the only genuine hop-1 vocabulary gap.** Its variant leg finds
  the gold at rank 3, but at the default `variant_weight_discount=0.5` the
  discounted RRF contribution leaves the gold at fused rank ~38 — outside the
  30-candidate fusion cut (a variant-leg fusion-cut miss). A discount sweep
  at depth-30 geometry:

  | discount | Q101 fused rank | Q104 fused rank | Q122 fused rank |
  |----------|-----------------|-----------------|-----------------|
  | 0.5 | 38 (out) | 2 | 21 |
  | 0.75 | 29 | 2 | 26 |
  | 1.0 | 16 | 2 | **36 (out)** |
  | 1.5 | 12 | 2 | 37 (out) |

  Rescuing Q101 at hop-1 requires discount ≥ 0.75–1.0, i.e. the variant leg
  at or near full primary-BM25 weight. Because RRF weights are normalized,
  that dilutes the dense leg — Q122's dense-sourced gold degrades from fused
  21 to 36 (out of pool) at discount 1.0. The knob that helps the one true
  vocabulary-gap query harms a dense-anchored query. No discount value
  passes more than one target, and even a rescued hop-1 entry still faces
  the §3 listwise demotion.

## 4. A/B runs

Deterministic mechanism-level traces (§3) show identical target outcomes in
both arms, so the enabled arm was run once per dataset (instead of 3×) to
measure aggregate neutrality (criterion b) and latency (criterion c);
criterion (a) is already decided structurally. Controls: `qe_control_r1`
(96q, this session) and the `q12_reserve_0_r{1,2,3}` 63q control mean
(0.7838) from Phase 1.

| Run | Dataset | MRR | recall@5 | hit_rate@5 | pool_hit_rate | avg latency |
|-----|---------|-----|----------|------------|---------------|-------------|
| qe_control_r1 (OFF) | 96q | 0.6638 | 0.6158 | 0.9479 | 0.9479 | 4539 ms |
| qe_enabled_r1 (ON) | 96q | 0.6693 | 0.6158 | 0.9583 | 0.9688 | 4495 ms |
| q12_reserve_0 mean (OFF) | 63q | 0.7838 | — | — | — | — |
| qe_enabled_63q_r1 (ON) | 63q | 0.7669 | 0.6019 | 0.9683 | 0.9841 | 4457 ms |

Per-target in the enabled arm (96q): Q101 miss (`pool_hit=False`), Q104 miss
(`pool_hit=False`), **Q122 flipped to hit** (MRR 0.2, recall@5 0.5,
`pool_hit=True`). The Q122 flip shows the §3 trace slightly understated the
feature's reach: the manual trace stopped at the multi-hop rerank, but in the
full pipeline the variant legs perturb pool composition enough for the
pool-sensitive listwise stage to retain Q122's gold. Q101/Q104 behave exactly
as the trace predicted.

63q guard: the −0.0169 MRR delta vs the 3-run control mean is within the
±0.02 noise band and is fully accounted for by two rank-1→2 flips (Q81, Q90,
−0.5 MRR each ≈ 0.016 aggregate). **Both match no concept trigger** — they
take the byte-identical `rerank_simple` path (regression-tested), so the
feature cannot be the cause; these are boundary-riding listwise flips. None
of the 12 trigger-matched 63q queries regressed ≥0.1 MRR.

## 5. Criteria evaluation

- **(a) ≥2 of {Q101, Q104, Q122} flip/materially improve in enabled runs:
  FAIL.** One target flips (Q122); Q101/Q104 cannot flip — Q104 fails at a
  stage query expansion cannot reach, and Q101 needs a weight setting that
  harms other queries (§3).
- **(b) Aggregates within ±0.02 of control: PASS.** 96q +0.0055 (mildly
  positive: recall@10 +0.008, recall@20 +0.015, pool_hit_rate +0.021);
  63q −0.0169 (noise, attributed above).
- **(c) Latency delta: PASS.** 96q −1.0% (4495 vs 4539 ms) — the extra
  BM25 leg is single-digit-ms; run-to-run variation dominates.

## 6. Decision

`QueryExpansionConfig.enabled` stays **False**. Criterion (a) — the reason
the feature exists — fails: 1/3 targets, below the 2/3 bar, with the two
non-flips structurally out of reach. The mildly positive 96q aggregates and
the Q122 flip are not adoption grounds on a single run against a criterion
the feature wasn't designed to pass indirectly.

The mechanism, config surface (6 flat aliases), vocabulary table, and tests
remain in the codebase for opt-in use and re-evaluation once the multi-hop
pool-flooding demotion is addressed — at that point Q101-class queries become
the honest test of the vocabulary bridge.

## 7. Re-evaluation post-ADR-0013 (2026-07-28, later)

ADR-0012's stated re-evaluation condition — "if the post-retrieval demotion
issue is addressed" — was met the same day: commit `1bf947b` (ADR-0013,
`hop1_reserved_slots=6` at the multi-hop rerank window) fixed the listwise
demotion of hop-1 winners. QE was re-run enabled on both datasets against the
new N=6 defaults. Controls are ADR-0013's shipped-default numbers, **not**
`qe_control_r1` (which predates the reserve).

| Run | Dataset | MRR | recall@20 | pool_hit_rate | avg latency |
|-----|---------|-----|-----------|---------------|-------------|
| N=6 control (ADR-0013) | 96q | 0.6668 | 0.8156 | 0.974 | — |
| qe_post_reserve_96q_r1 (ON) | 96q | 0.6663 | 0.8091 | 0.9688 | 4550 ms |
| N=6 control (ADR-0013) | 63q | 0.7795 | — | — | — |
| qe_post_reserve_63q_r1 (ON) | 63q | 0.7828 | 0.8107 | 1.0000 | 4573 ms |

Per-target (96q, QE ON): **Q104 hit at MRR 1.0** — but the reserve alone
already delivers that (it hits identically in the control arm); QE
contributes nothing. **Q122 miss** (`pool_hit=False`) — confirms the
model-demotion reclassification from ADR-0013 (distinct, un-fixable-by-reserve
failure mode); notably the Q122 pool-perturbation flip from §4 did **not**
survive the reserve's pool reshaping. **Q101 miss** — the one genuine
vocabulary gap, still unreachable at `variant_weight_discount=0.5` for the §3
reasons (rescue requires ≥0.75–1.0, which dilutes the dense leg).

Aggregates are flat to marginally negative on 96q (MRR −0.0005,
recall@20 −0.0065, pool_hit_rate −0.005) and flat on 63q (+0.0033) — all
within the ±0.02 noise band, with no target gained.

**Verdict: the re-evaluation condition is closed. With the demotion issue
fixed, QE adds zero targets and zero aggregate lift; the feature remains
opt-in/disabled. Any future case for it rests on Q101-class vocabulary-gap
queries appearing in real workloads, not on this golden set.**

## Reproduction

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/benchmark/run_sscg_benchmark.py \
  --project-path . --golden-dataset evaluation/golden_dataset_expanded.json \
  --query-expansion --config-name qe_enabled_r1 \
  --output benchmark_results/qe_enabled_r1.json --quiet --no-drilldown
```
