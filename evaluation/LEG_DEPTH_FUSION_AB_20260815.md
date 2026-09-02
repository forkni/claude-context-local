# Leg-Depth-Widen + TM2C2 Fusion A/B: Both Arms REJECTED (2026-08-15)

**Verdict: neither arm adopted.** `search_mode.leg_search_multiplier` stays `5`
(byte-identical default), `search_mode.fusion_function` stays `"rrf"`. Both
knobs ship in the codebase, default-off/byte-identical, covered by unit tests
(`test_funnel_characterization.py`, `test_search_executor.py`,
`test_reranker.py`) — but no default flips. This closes the plan
`study-the-plan-verify-cheeky-pike.md` (Leg-Search-Depth Probe + TM2C2 retest
at depth) end to end.

Phase 1's read-only probe (`evaluation/LEG_DEPTH_FUSION_PROBE_20260814.md`)
passed both pre-registered screening gates — Gate A (depth alone, net gold-
membership gain at d∈{100,200} under RRF) and Gate B (TM2C2 beats RRF at the
same depth, including a Q121-class rescue). Phase 2 built both knobs and ran
the full end-to-end pipeline (not a merge-pool-membership proxy) against the
pre-registered adoption gate. **Both arms failed it** — the exact "screening
pass doesn't convert to end-metric gain" hazard the plan called out in
advance, citing `probe_reserve_depth.py`'s own conclusion: *"Treat a passing
probe as 'worth sweeping', never as a predicted rescue."*

| Arm | Config | 133q recall@10/20 gate | Verdict |
|---|---|---|---|
| `legwide` | `leg_search_multiplier=10` (depth 200, RRF) | Δ −0.0069 / −0.0025, CI incl-0 | **REJECTED** |
| `tm2c2` | `fusion_function=tm2c2 tm2c2_alpha=0.8` (depth 100 = default multiplier, the Gate-B-validated depth) | Δ −0.0160 / −0.0132, CI incl-0 | **REJECTED** |

Both point estimates are *negative*, not merely non-significant — the gate
required a paired 95% CI **excluding zero on the upside**; instead every
recall metric on 133q moved the wrong direction for both arms.

## Substrate

Corpus post Phase-2 code landing (`search/config.py`, `search_executor.py`,
`reranker.py` — `leg_search_multiplier`, `fusion_function`, `tm2c2_alpha`
fields + dispatch, not yet committed at capture time). Deterministic-harness
conventions: PYTHONHASHSEED=0 auto-re-exec, `CLAUDE_AUTO_REINDEX=0`,
`--set intent.enabled=true` on every run, `--k 10`. 63q r1 vs r2: **0 movers,
MRR 0.8595 both rounds** — determinism holds on this substrate; every
per-query delta below is causal, not flap.

Artifacts (gitignored): `benchmark_results/leg_depth_ab/{base_63q_r1,
base_63q_r2,base_133q_r1,legwide_63q,legwide_133q,tm2c2_63q,tm2c2_133q}.{json,log}`

+ `analyze_ab.py` (paired-CI analysis).

**New deterministic canons (this substrate):**

+ 63q: **MRR 0.8595**, recall@10 0.8041, recall@20 0.8348, pool_hit_rate 0.9048
+ 133q: **MRR 0.6766**, recall@10 0.7791, recall@20 0.8209, pool_hit_rate 0.9098

These differ from the 2026-08-14 remaining-levers canons (0.8722/0.6843) —
expected substrate drift from the intervening Phase-2 code landing + reindex;
not itself evidence for or against either arm (both arms are compared against
these same-substrate baselines, not the stale ones).

Re-derived 133q hard-miss cohort (mrr=0.0, `base_133q_r1`): `H008, H050, H054,
H066, Q101, Q103, Q117, Q122` — supersedes any inherited list.

## `legwide` — depth 200 under RRF (`leg_search_multiplier=10`)

### 133q upside gate — FAILED

| metric | base | arm | Δ mean | 95% CI | gate |
|---|---|---|---|---|---|
| recall@10 | 0.7791 | 0.7723 | −0.0069 | [−0.0419, +0.0281] | incl-0, wrong direction |
| recall@20 | 0.8209 | 0.8184 | −0.0025 | [−0.0350, +0.0300] | incl-0, wrong direction |
| mrr | 0.6766 | 0.6730 | −0.0036 | [−0.0409, +0.0336] | incl-0 |
| recall@5 | 0.6526 | 0.6658 | +0.0132 | [−0.0241, +0.0505] | incl-0, only positive metric |
| recall@50 | 0.8284 | 0.8202 | −0.0081 | [−0.0408, +0.0245] | incl-0 |
| ndcg@10 | 0.6872 | 0.6815 | −0.0057 | [−0.0357, +0.0242] | incl-0 |
| pool_hit_rate | 0.9098 | 0.9098 | +0.0000 | — | flat |
| latency_ms | 4278.9 | 4228.0 | −50.9 | — | no debit (slightly faster) |

27 MRR movers, roughly balanced by count but not by story: H048/Q102/Q116 flip
1.0→0.0 (perfect hit to total miss), while Q103/Q122/H008/H066 (all prior
hard misses) get rescued, two of them to 1.0. **Net churn, not net gain** —
the deeper leg swaps which golds the funnel finds, it doesn't grow the set.

### 63q guard-rail — held (no significant loss)

mrr −0.0093 [−0.0250, +0.0065] incl-0; recall@5 −0.0132 [−0.0281, +0.0017]
incl-0-close. Guard-rail not violated, but moot given the upside gate failed.

### Q121 (the exemplar) — gets *worse*, not rescued

`Q121: 0.0435 → 0.0000` on 133q. The specific case that motivated this whole
campaign (raw dense rank 84 / BM25 rank 80 / RRF-fused rank 41, unreachable at
deployed depth 50/100) goes from a weak partial hit to a total miss when the
leg is widened to depth 200. Widening the leg changed what else entered the
pool and out-competed it in the merge/rerank — the same conversion-hazard
mechanism the plan pre-registered, now confirmed on the named exemplar itself.

## `tm2c2` — TM2C2 fusion at depth 100 (default multiplier, Gate-B-validated depth)

### 133q upside gate — FAILED, and `pool_hit_rate` regressed

| metric | base | arm | Δ mean | 95% CI | gate |
|---|---|---|---|---|---|
| recall@10 | 0.7791 | 0.7631 | −0.0160 | [−0.0502, +0.0181] | incl-0, wrong direction |
| recall@20 | 0.8209 | 0.8077 | −0.0132 | [−0.0484, +0.0220] | incl-0, wrong direction |
| mrr | 0.6766 | 0.6613 | −0.0153 | [−0.0541, +0.0235] | incl-0 |
| recall@5 | 0.6526 | 0.6382 | −0.0144 | [−0.0539, +0.0251] | incl-0 |
| recall@50 | 0.8284 | 0.8077 | −0.0207 | [−0.0542, +0.0128] | incl-0 |
| ndcg@10 | 0.6872 | 0.6697 | −0.0175 | [−0.0513, +0.0163] | incl-0 |
| pool_hit_rate | 0.9098 | 0.8797 | **−0.0301** | — | regression |
| latency_ms | 4278.9 | 4207.9 | −71.0 | — | no debit |

`pool_hit_rate` is the exact metric the Phase-1 screening probe used to pass
Gate B — here, measured end-to-end at the validated depth, it goes *down*.
pool_hit losers: Q101, Q102, Q103, Q133, H006, H007, H039, H066 (8 lost) vs
gains concentrated in H063 (0.10→1.00) and H066 (0.0→1.0, also a pool_hit
gain — net still negative). 31 MRR movers; three prior perfect hits (H006,
H007, Q102, each 1.0→0.0) are lost outright.

### 63q guard-rail — MRR holds, but recall@5 shows a real loss

| metric | base | arm | Δ mean | 95% CI | gate |
|---|---|---|---|---|---|
| mrr | 0.8595 | 0.8669 | +0.0074 | [−0.0085, +0.0233] | incl-0 |
| recall@10 | 0.8041 | 0.8160 | +0.0119 | [−0.0131, +0.0369] | incl-0 |
| recall@5 | 0.6994 | 0.6730 | **−0.0265** | [−0.0473, **−0.0056**] | **EXCL-0, loss** |

The primary guard-rail metric (MRR) doesn't exclude zero, so the pre-
registered guard-rail is technically not violated — but recall@5 on the
canonical, low-noise 63q set shows a statistically significant regression,
which is a warning sign the MRR guard-rail alone wouldn't have caught.

### Q121 — marginal, not a rescue

`Q121: 0.0435 → 0.0625` on 133q — rank improves slightly (~rank 23 → ~16) but
stays far outside any usable cut. Consistent with the Phase 1 disposition's
own caveat: *"Q121 exemplar reproduces as a swap not pure win."*

## Mechanism

Both levers reach the funnel — Phase 1 already proved 0 divergence between
the offline probe and the live merge pool at depth 50/100/200 (the fidelity
check), and this A/B confirms the reach: pool composition visibly moves for
both arms (`pool_hit movers` lists above are non-empty, unlike a no-op). But
`fusion_k` (the merge cut, 30) and the reranker's final window are unchanged
by either lever, so the deeper/differently-fused pool competes for the same
fixed number of slots. A gold entering the wider pool at a low raw rank
displaces a candidate that was previously winning the neural rerank on
relevance grounds, not membership. The net effect on this pipeline, both times
measured end-to-end, is churn that nets negative on the metrics that matter
(recall@10/20, MRR) even when raw pool membership (Gate A/B's screening
metric) moves favorably in isolated cases.

This is the second consecutive campaign (`GRAPH_RESERVE_PROBE_20260814.md`,
`TM2C2_FUSION_PROBE_20260814.md` before it, both closed 2026-08-14) where a
funnel-composition change (reserve slots, deeper legs, alternate fusion
arithmetic) shows real, non-null movement in pool membership but fails to
convert to an end-metric win on this reranker/pipeline. The reranker's final
window, not pool composition, is the binding constraint — future levers
targeting recall should act on the window itself (size, selection policy) or
the reranker's relevance judgment, not on what competes to enter it.

## Latency

Neither arm shows a meaningful debit — both were *slightly faster* than
baseline on 133q (legwide −50.9ms, tm2c2 −71.0ms out of ~4,250ms/query),
likely within run-to-run noise given per-query latency wasn't the gated
metric. No latency-only opt-in case exists here (unlike A4/PPR) since there's
no recall upside to trade against; a small latency change with a recall loss
is not a shippable trade in either direction.

## Methodology notes

+ 63q r1/r2 identity (0 movers, MRR 0.8595 both) confirms PYTHONHASHSEED=0
  determinism on this substrate — per-query deltas in both arms are causal.
+ The rogue background campaign that produced these results ran via a
  duplicated (venv + system-Python) concurrent invocation per arm, discovered
  mid-run and left to complete rather than killed (user decision, this
  session). Post-hoc integrity check: all 7 output files have correct,
  non-duplicated query-id counts (63/133), no tracebacks/errors in any log,
  and the r1/r2 determinism pair is bit-identical on MRR — the duplication did
  not corrupt the results, but it is not a pattern to repeat; future campaigns
  in this repo should launch via a single tracked process.
+ Gate was pre-registered before any arm ran: recall@10/20 paired 95% CI
  excluding zero on 133q for upside, MRR guard-rail both sets, aggregates
  only, latency priced explicitly. Both arms failed in the direction opposite
  the gate (negative point estimates, not merely non-significant).
+ Phase 2's `probe_rerank_window.py` re-run (plan step, gated on "the winning
  arm") is **not applicable** — neither arm won.

## Reopening condition

Do not re-propose leg-depth widening or TM2C2 fusion as isolated levers
without also changing the merge cut (`fusion_k`) or final rerank window
policy in the same arm — per the Mechanism section above, pool-composition
levers alone have now failed twice on this pipeline (this campaign +
`TM2C2_FUSION_PROBE_20260814.md`'s inert result) for the same structural
reason. A future campaign should target window-size/selection or reranker
relevance-judgment directly, informed by this doc's mechanism finding.
