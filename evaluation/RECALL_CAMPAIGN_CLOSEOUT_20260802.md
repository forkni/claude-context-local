# Recall-Improvement Campaign — Close-Out (2026-08-02)

## Status: CLOSED

Every lever with any evidence behind it has been measured, shipped, rejected,
or spec'd-and-deferred. The recall frontier at config level is **exhausted**;
the one remaining code-level design (final-pool-assembly reserve) was probed
read-only, failed its build gate, and is deferred with a written spec and
reopening condition (`FINAL_POOL_RESERVE_PROBE_20260802.md`).

## Campaign arms — this campaign (chronological)

| Arm | Verdict | Record / commit |
|-----|---------|------------------|
| ADR-0020 config-field liveness audit | SHIPPED (substrate change) | `docs/adr/0020-config-field-liveness-audit.md`, commit `38950a4` |
| Stable-miss diagnosis (Q119/Q121/Q122/Q133/H063) | Diagnosis record | `STABLE_MISS_DIAGNOSIS_20260802.md`, commit `c5467e3` |
| fp32 listwise reranker (determinism) | **REJECTED** (flips unchanged 21/21; fp32's own spread worse) | `RERANKER_FP32_DETERMINISM_AB_20260802.md`, commit `ebb5ff7`; `listwise_dtype` knob ships default `"auto"` (`0654761`) |
| find_similar default k → config `default_k` (7) | **SHIPPED** (explicit-k byte-identical; F-view 0.8519 at k=7 ≡ k=10) | commit `730f67c` |
| multi-hop expansion 0.25 | **REJECTED** (pool_hit up, zero conversions, H034 1.0→0.2 / H067 1.0→0.5 replicated) | `MULTIHOP_EXPANSION_025_AB_20260802.md`, commit `09f27c0` |
| PPR ego-graph expansion | **REJECTED for recall** (only clean effects are losses: Q51 0.5→0.333 iron-clad, Q70→0.0; ~15% faster — future latency candidate) | `EGO_PPR_AB_20260802.md`, commit `7ca126d` |
| Final-pool-assembly reserve (probe-gated) | **GATE FAILED — spec'd-and-deferred** (zero stable misses rescuable; Q121 unreachable, Q122 hit by drift; best variant rescues flappers only) | `FINAL_POOL_RESERVE_PROBE_20260802.md`, commit `d71dc0a` |
| Post-ADR-0020 63q re-baseline | **NEW CANON** (see below) | `sscg_post_adr0020_63q_r{1,2}_20260802.json` |

## Previously settled levers (never re-propose)

Fusion weights / rrf_k (saturated), ADR-0019 intent-adaptive weights
(REJECTED+DELETED, `c03e0b4`), hop-1 `bm25_reserved_slots` (`1c9c81d`),
community merge (scorer-blocked), sibling merge (neutral, not worth
INDEX_VERSION bump), BM25 stopword removal (regressive), ADR-0012 query
expansion (fail-ships-disabled; re-eval closed `ca4c904`), `single_pass`
(latency-only knob, kills recall), `centrality_alpha > 0` (costs recall,
replicated), rerank window / doc-cap changes (VRAM-bounded at 30 / 4000),
reranker dtype incl. fp16 (kernel-class, not weight precision),
`expansion_factor ≠ 0.5`, PPR-for-recall. Shipped positives:
`hop1_reserved_slots=6` (ADR-0013, `1bf947b`), `exclude_same_file`
(`d468dcb`), F2LLM-v2-0.6B embedder, path/symbol token augmentation
(INDEX_VERSION 4), identifier-preserving BM25 tokenizer.

## Final canon baselines (all post-ADR-0020 substrate)

| Dataset | MRR | recall@20 | pool_hit | Files |
|---------|-----|-----------|----------|-------|
| canonical 63q (2 rounds) | **0.7597 / 0.7956 (μ 0.7777)** | 0.7979 / 0.8251 | 0.9841 / 1.0 | `sscg_post_adr0020_63q_r{1,2}_20260802.json` |
| expanded 131q (2 rounds) | 0.6510 / 0.6311 (μ 0.641) | 0.8311 / 0.8131 | 0.9542 / 0.9542 | `sscg_post_adr0020_expanded_r{1,2}_20260802.json` |
| F-via-similar (9 F queries, k=7) | 0.8519 | — | — | `sscg_f_via_similar_k7_20260802.json` |

The pre-ADR-0020 63q canon (0.7987) is **superseded**. The substrate is
quality-flat: new r2 vs old canon r2 = −0.0039 and vs the fp32-armed 63q run
(0.7938) = +0.0018 — both inside the ±0.02 band. Attribution of the μ drop
to 0.7777:

- **r1 was a flapper-heavy round**: Q07 flipped 0→1 between rounds
  (including the only pool-miss — Q07 is hereby added to the known-flapper
  list), Q90 0.333→1.0, Q77 0.5→1.0. Round spread 0.0359 — the largest
  observed on 63q, but flapper-borne, not systematic.
- **Q52 is a genuine replicated substrate move**: "what is
  MultiLanguageChunker responsible for" 1.0 → 0.5 in BOTH new rounds
  (pool_hit true; rank 1→2 demotion). Index drift 2,253 → 2,273 chunks.
- Small stable residue: Q86/Q89/Q01/Q96 minor down, Q54/Q70/Q12 minor up.

Comparison tool: `scripts/benchmark/analyze_dtype_determinism.py <r1> <r2>
--baseline <files...>`.

## Durable methodology rules (established this campaign)

1. **Control-arm attribution**: run a quality-neutral same-session control;
   queries moving identically in control and treatment are drift, not
   effect (`MULTIHOP_EXPANSION_025_AB_20260802.md`).
2. **Bimodal-flapper rule**: cross-session flappers (Q07, Q81, Q90, Q102,
   Q103, Q106, Q119, Q133, H048, H054, H063) get no credit and no debit;
   check any candidate win/loss against ALL prior same-substrate runs.
3. **Substrate re-baseline rule**: re-run A/B baselines after ANY commit
   touching the search path, even audit/liveness changesets.
4. **2-agreeing-rounds rule**: boundary-riding promotions require two
   agreeing grading rounds (bf16 noise floor: ~21 MRR flips / 9 material
   per identical 131q round pair).
5. **Probe before build**: read-only membership probes gate code levers;
   pool membership ≠ ranking win — probes measure ceilings, only A/Bs
   measure conversion.
6. **Re-probe before design**: stable-miss profiles drift with the index —
   re-diagnose on the current substrate before designing a lever (Q122
   became a hit and Q119 changed failure class between diagnosis and probe).

## Frontier disposition

- **Final-pool reserve**: deferred. Reopening condition = a recall@k-focused
  campaign; spec (V1 raw-BM25 top-3 carry-forward, zero-collateral, gate on
  recall@10/20 not MRR) in `FINAL_POOL_RESERVE_PROBE_20260802.md`.
- **Q121** is the only stable miss on the current substrate — rrf-arithmetic,
  confirmed no-lever (raw dense 84 / BM25 80 / fused 41; unreachable by any
  probed mechanism).
- **Latency campaign candidates** (recorded, NOT acted on): PPR expansion
  (−15% latency, tighter variance, Q51/Q70 quality debit priced in) and
  `single_pass` (recall debit). A determinism arm, if ever run, targets
  `torch.use_deterministic_algorithms`, not dtype.
- **Merged-cut class**: the 8/17 diagnosis-era classification is partially
  stale (Q122 drifted to hit); any future merged-cut work starts with a
  fresh diagnosis run.
