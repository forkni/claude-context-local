# Merged-Pool Ordering Campaign — `graph_hop_window_cap` Phase 3 A/B — REJECTED (2026-08-15)

**Verdict: neither `cap=2` nor `cap=3` is adopted.** `reranker.graph_hop_window_cap` stays at its
`0` (off) default. The mechanism remains in-tree, unit-tested, and reachable via
`--set reranker.graph_hop_window_cap=N` for future research, but is now locked out of
`index_probe.py`'s auto-tuner (`FORBIDDEN_AUTO_TUNE_KEYS`/`BENCHMARK_LOCK_CITATIONS`,
`search/index_probe.py:75`/`:104`).

See `POOL_ORDER_CAP_PROBE_20260815.md` for the Phase 1 offline-replay gate this A/B was
pre-registered against — reproduced here for reference, not adjusted post-hoc.

## Method

7 runs, `run_sscg_benchmark.py`, fresh force-reindex first (this campaign's own Phase 2b commit
touches indexed source — substrate-drift rule): 209 files / 2,454 chunks / `codefuse-ai/F2LLM-v2-0.6B`
(substrate drifted +8 chunks from the prior `POOL_ORDER_AB_20260815.md` pin of 2,446 — expected,
this campaign's own intervening commits, not investigated further). `PYTHONHASHSEED=0` (ADR-0021
auto-re-exec), `CLAUDE_AUTO_REINDEX=0`. Every arm sets `--set intent.enabled=true` (the runner
force-pins `intent.enabled=False` otherwise, ADR-0023 B1b guard).

Outputs: `benchmark_results/pool_order_cap_ab/{base_63q_r1,base_63q_r2,base_133q_r1,
cap2_63q,cap2_133q,cap3_63q,cap3_133q}.json` (run artifacts, not tracked in git per house style).

## Results

| Arm | Set | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | avg latency |
|---|---|---|---|---|---|---|---|
| `base_63q_r1` | 63q | 0.8603 | 0.6889 | 0.8107 | 0.8573 | 0.9048 | 3949ms |
| `base_63q_r2` | 63q | 0.8603 | 0.6889 | 0.8107 | 0.8573 | 0.9048 | 3955ms |
| `base_133q_r1` | 133q | 0.6849 | 0.6727 | 0.7804 | 0.8384 | 0.9173 | 4174ms |
| `cap2_63q` | 63q | 0.8603 | 0.6804 | 0.8081 | 0.8462 | 0.9048 | 3958ms |
| `cap2_133q` | 133q | 0.6888 | 0.6661 | 0.7754 | 0.8212 | 0.9023 | 4138ms |
| `cap3_63q` | 63q | 0.8444 | 0.6783 | 0.8081 | 0.8462 | 0.9048 | 3921ms |
| `cap3_133q` | 133q | 0.6815 | 0.6695 | 0.7791 | 0.8231 | 0.9023 | 4175ms |

**Byte-identity check:** `base_63q_r1` == `base_63q_r2` exactly on every aggregate field — 0
movers, determinism confirmed (ADR-0021).

## Paired 95% CIs (10,000-resample bootstrap, seed 0, vs the matching base arm)

| Metric | Set | `cap=2` mean Δ | CI | `cap=3` mean Δ | CI |
|---|---|---|---|---|---|
| recall@10 | 133q | −0.0050 | [−0.0207, +0.0088] | −0.0013 | [−0.0188, +0.0163] |
| recall@20 | 133q | −0.0172 | [−0.0431, +0.0045] | −0.0153 | [−0.0395, +0.0050] |
| MRR | 133q | +0.0038 | [−0.0084, +0.0175] | −0.0034 | [−0.0173, +0.0086] |
| MRR | 63q | +0.0000 | [−0.0238, +0.0238] | −0.0159 | [−0.0397, +0.0000] |
| recall@5 | 63q | −0.0085 | [−0.0222, +0.0000] | −0.0106 | [−0.0317, +0.0106] |
| recall@10 | 63q | −0.0026 | [−0.0238, +0.0159] | −0.0026 | [−0.0238, +0.0159] |

No CI in either arm excludes zero in either direction — every interval straddles or touches zero.

## Gate evaluation

**Upside (both arms): not met.** The gate requires the 133q recall@10 or recall@20 CI to exclude
zero *positively*. Neither metric does so at either cap — and unlike `score_reserve_fix`'s flat
zero-centered result in the prior A/B, both point estimates here are **negative** on both upside
metrics at both caps (recall@10: −0.0050/−0.0013; recall@20: −0.0172/−0.0153). The mechanism does
not merely fail to clear the bar — it trends the wrong direction on the metric it was designed to
help.

**Guard-rails: no breach at either cap.**

- MRR CI loss-side exclusion: none. `cap=3` 63q MRR upper bound sits exactly at `+0.0000` (same
  hug-the-boundary pattern `score_reserve_fix` showed in the prior A/B) — does not exclude zero.
- Named guard-rail (63q recall@5): no breach — both CIs include zero (`cap=2` upper bound also
  exactly `+0.0000`).
- `pool_hit_rate` drop > 0.02: no breach — 63q flat at 0.9048 in both arms; 133q drops
  0.9173 → 0.9023 (Δ −0.0150), under threshold.
- Latency: 133q Δ ≈ −36ms (`cap=2`) / +1ms (`cap=3`); 63q Δ ≈ +3–9ms (`cap=2`) / −29ms (`cap=3`) vs
  `base_63q_r1` — all under the 100ms explanation threshold.

**Verdict: both arms rejected.** No guard-rail breach, but no upside case either — the campaign's
central hypothesis (capping zero-signal `graph_hop` window occupancy reclaims slots for
better-signal candidates and lifts 133q recall) does not hold on this substrate at either dose.
`cap=3`'s 63q MRR debit (−0.0159 point, though CI doesn't exclude zero) mirrors the direction of
`channel_priority`'s rejected 63q precision debit at much smaller magnitude — consistent with the
same underlying tension (evicting `graph_hop` slots costs 63q's smaller, more precision-sensitive
golden set more than it helps), just not large enough here to breach a guard-rail on its own.

## Risk check — Q12 / H034 / H066 (pre-registered, reported regardless of verdict)

| Gold | Set | Base | `cap=2` | `cap=3` |
|---|---|---|---|---|
| Q12 | 63q | mrr=0.2500, recall@10=0.500, hit=True | mrr=0.2500, recall@10=0.500, hit=True | mrr=0.2500, recall@10=0.500, hit=True |
| Q12 | 133q | mrr=0.2500, recall@10=0.500, hit=True | mrr=0.2500, recall@10=0.500, hit=True | mrr=0.2500, recall@10=0.500, hit=True |
| H034 | 133q | mrr=1.0000, recall@10=1.000, hit=True | mrr=1.0000, recall@10=1.000, hit=True | mrr=1.0000, recall@10=1.000, hit=True |
| H066 | 133q | mrr=1.0000, recall@10=1.000, hit=True | mrr=1.0000, recall@10=1.000, hit=True | mrr=1.0000, recall@10=1.000, hit=True |

Zero movement on all three named golds at either cap on either dataset — exactly as the Phase 1
offline replay predicted (Q12's graph-sourced gold is structurally unreachable at every cap tested;
H034/H066 aren't touched by the cap mechanism). No substrate-drift flag needed — live results agree
with the replay's prediction.

## Disposition

- **Landed code is unchanged and stays in-tree.** `_apply_graph_hop_window_cap`,
  `RerankerConfig.graph_hop_window_cap`, and the Pass-2 call-site kwarg remain byte-identical at
  the `0` (off) default. The mechanism stays available via `--set` for future probes — this A/B
  closes the *default-change* question, not the code's existence.
- **`reranker.graph_hop_window_cap` added to `FORBIDDEN_AUTO_TUNE_KEYS` /
  `BENCHMARK_LOCK_CITATIONS`** (`search/index_probe.py:75`/`:104`, this commit) — locked
  post-verdict per the pre-registered plan, consistent with every other rejected knob in that list.
  `tests/unit/search/test_index_probe.py`'s pinned frozenset literal updated in lockstep.
- **Reopening condition.** The underlying diagnosis (raw-score sort mixing three incommensurable
  scales; `graph_hop`'s literal `0.0` score) is still live and still real — this A/B rejected the
  *window-cap* fix, not the diagnosis, and it is the second of the two reopening directions
  pre-registered in `POOL_ORDER_AB_20260815.md` to be measured and rejected (`channel_priority` and
  `score_reserve_fix` before it). The remaining, not-yet-attempted direction from that doc's
  Disposition — giving `graph_hop` a real anchor-conditioned score instead of literal `0.0`
  (addresses the root cause directly, rather than reordering or capping channels around a broken
  score) — has not been probed. A future attempt at that direction is a new probe from first
  principles, not a re-run of either closed A/B. Absent a concrete new mechanism proposal, this
  campaign is closed.
