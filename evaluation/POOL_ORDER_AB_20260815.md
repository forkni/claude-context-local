# Merged-Pool Ordering Campaign — Phase 4 A/B — NEITHER arm adopted (2026-08-15)

**Verdict: `channel_priority` and `score_reserve_fix` are both measured and rejected.**
`reranker.merged_pool_policy` stays at its `"score"` default. Both non-default policies remain
in-tree, unit-tested, and reachable via `--set reranker.merged_pool_policy=...` for future
research, but are now locked out of `index_probe.py`'s auto-tuner
(`FORBIDDEN_AUTO_TUNE_KEYS`/`BENCHMARK_LOCK_CITATIONS`, `search/index_probe.py:74`/`:102`).

See `POOL_ORDER_PROBE_20260815.md` for the corrected Phase 1 diagnosis and the pre-registered
gate this A/B was run against — reproduced here for reference, not adjusted post-hoc.

## Method

7 runs, `run_sscg_benchmark.py`, substrate pinned at 209 files / 2,446 chunks /
`codefuse-ai/F2LLM-v2-0.6B`, `PYTHONHASHSEED=0` (ADR-0021 auto-re-exec), `CLAUDE_AUTO_REINDEX=0`.
Every arm sets `--set intent.enabled=true` (the runner force-pins `intent.enabled=False`
otherwise, ADR-0023 B1b guard). Base canon arms use the same `intent.enabled=true` setting as the
policy arms — this re-pins the paired baseline under this campaign's fixed settings; it does not
reproduce the standing production canon (which runs with intent off by default) and is not meant
to.

Outputs: `benchmark_results/pool_order_ab/{base_63q_r1,base_63q_r2,base_133q_r1,
p1_channel_priority_63q,p1_channel_priority_133q,p2_reserve_fix_63q,p2_reserve_fix_133q}.json`
(run artifacts, not tracked in git per house style).

## Results

| Arm | Set | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | avg latency |
|---|---|---|---|---|---|---|---|
| `base_63q_r1` | 63q | 0.8603 | 0.6941 | 0.8094 | 0.8573 | 0.9048 | 4040ms |
| `base_63q_r2` | 63q | 0.8603 | 0.6941 | 0.8094 | 0.8573 | 0.9048 | 4095ms |
| `base_133q_r1` | 133q | 0.6815 | 0.6689 | 0.7860 | 0.8409 | 0.9173 | 4209ms |
| `p1_channel_priority_63q` | 63q | 0.8414 | 0.6690 | 0.8121 | 0.8507 | 0.9048 | 4075ms |
| `p1_channel_priority_133q` | 133q | 0.6784 | 0.6683 | 0.8239 | 0.8629 | 0.9248 | 4289ms |
| `p2_reserve_fix_63q` | 63q | 0.8524 | 0.6902 | 0.8068 | 0.8520 | 0.9048 | 4059ms |
| `p2_reserve_fix_133q` | 133q | 0.6850 | 0.6764 | 0.7967 | 0.8566 | 0.9248 | 4213ms |

**Byte-identity check:** `base_63q_r1` == `base_63q_r2` exactly on every aggregate field — 0
movers, determinism confirmed (ADR-0021).

## Paired 95% CIs (10,000-resample bootstrap, seed 0, vs the matching base arm)

| Metric | Set | `channel_priority` mean Δ | CI | `score_reserve_fix` mean Δ | CI |
|---|---|---|---|---|---|
| MRR | 63q | −0.0189 | **[−0.0437, −0.0013]** | −0.0079 | [−0.0238, +0.0000] |
| recall@5 | 63q | −0.0251 | **[−0.0529, −0.0013]** | −0.0040 | [−0.0119, +0.0000] |
| recall@10 | 63q | +0.0026 | [−0.0251, +0.0304] | −0.0026 | [−0.0079, +0.0000] |
| recall@20 | 63q | −0.0066 | [−0.0437, +0.0278] | −0.0053 | [−0.0159, +0.0000] |
| MRR | 133q | −0.0031 | [−0.0291, +0.0266] | +0.0035 | [−0.0162, +0.0269] |
| recall@10 | 133q | +0.0378 | **[+0.0065, +0.0724]** | +0.0107 | [−0.0175, +0.0407] |
| recall@20 | 133q | +0.0219 | [−0.0100, +0.0551] | +0.0157 | [−0.0125, +0.0457] |

Bold = CI excludes zero.

## Gate evaluation

**`channel_priority` (primary):**

- Upside: **met** — 133q recall@10 CI excludes zero on the positive side
  (`[+0.0065, +0.0724]`); the other's (recall@20) point estimate is +0.0219 ≥ 0.
- Guard-rail (MRR CI must not exclude zero on the loss side, either set): **breached** — 63q MRR
  CI is `[−0.0437, −0.0013]`, entirely negative.
- Named guard-rail (63q recall@5): **breached** — CI `[−0.0529, −0.0013]`, entirely negative. (63q
  recall@10 CI `[−0.0251, +0.0304]` is fine.)
- `pool_hit_rate` drop > 0.02: no breach — 63q flat at 0.9048, 133q *gained* 0.9173 → 0.9248.
- Latency: 63q Δ ≈ +35ms (noise-band), 133q Δ ≈ +80ms — under the 100ms explanation threshold.

**Verdict: disqualified.** The upside criterion is met, but two independent guard-rails are
breached on the same set (63q) — the gate specifies any breach disqualifies, without a tie-break
for meeting upside elsewhere. `channel_priority` trades 63q precision-heavy queries (mostly
symbol/local-intent, where hop-1's top few candidates matter most) for a real 133q mid-window
recall gain concentrated in H-category (commit-mined, more expansion-dependent) queries. This is
directionally consistent with the diagnosis — suppressing `graph_hop`'s zero-score window
occupancy helps candidates that would otherwise be crowded out at the far end of the window, but
also removes graph candidates that were previously providing real recall on 63q's smaller golden
set.

**`score_reserve_fix` (secondary):**

- Upside: **not met** — neither 133q recall@10 (`[−0.0175, +0.0407]`) nor recall@20
  (`[−0.0125, +0.0457]`) CI excludes zero on the positive side.
- Guard-rails: no breach — every 63q CI upper bound sits at or below +0.0000, i.e. never
  excludes zero on the loss side either.
- `pool_hit_rate`: no breach — same pattern as `channel_priority` (63q flat, 133q +0.0075).
- Latency: Δ ≈ 0 both sets, as predicted for a pure reordering fix.

**Verdict: not adopted.** No guard-rail breach, but also no case for adoption — every effect is
statistically indistinguishable from zero. `score_reserve_fix`'s narrower, more targeted fix
(evicting the lowest-scoring non-hop-1 candidate instead of blindly evicting the tail) measurably
reduces the finding-(E) mechanism's blast radius versus what an unpatched blind-tail eviction
would do, but on this substrate the underlying effect (34.4% of queries, uniformly spread across
hop-1 ranks) is too diffuse to move aggregate recall or MRR outside noise.

## Risk #4 — graph-sourced gold check (pre-registered, reported regardless of verdict)

`channel_priority` drives `graph_hop` window occupancy from median 7 → 0 (zero in 78/124 probe
queries). Checked the three named graph-sourced golds:

| Gold | Base | `channel_priority` |
|---|---|---|
| Q12 (63q, second gold) | hit=True, MRR=0.250, recall@10=0.500 | hit=**False**, MRR=0.143, recall@10=0.250 |
| H034 (133q, A1 rescue) | hit=True, MRR=0.500, recall@10=1.000 | hit=True, MRR=**0.200**, recall@10=1.000 |
| H066 (133q, A1 rescue) | hit=**False**, MRR=0.000, recall@10=0.000 | hit=**True**, MRR=1.000, recall@10=1.000 |

Mixed: Q12 regresses to a miss and H034 drops rank as predicted (confirming the debit direction),
but H066 flips from a miss to a perfect hit — `channel_priority`'s tier-2 semantic-before-graph
ordering evidently helps H066 by promoting a `multi_hop` candidate that graph-channel dilution was
previously crowding out. Net: 2 of 3 named checks regress, consistent with — but not uniformly
confirming — the predicted debit. Not independently gating (the aggregate 63q guard-rail breach
already disqualifies this arm), but recorded per the pre-registration.

## Disposition

- **Landed code is unchanged and stays in-tree.** `merged_pool_policy`, `_order_merged_pool`,
  `_apply_hop1_reserve(evict_policy=)` remain byte-identical at the `"score"` default. Both
  `channel_priority` and `score_reserve_fix` remain available via `--set` for future probes —
  this A/B closes the *default-change* question, not the code's existence.
- **`reranker.merged_pool_policy` added to `FORBIDDEN_AUTO_TUNE_KEYS` /
  `BENCHMARK_LOCK_CITATIONS`** (`search/index_probe.py:74`/`:102`, commit-to-follow) — locked
  post-verdict per the pre-registered plan, regardless of adopt/reject outcome, consistent with
  every other rejected knob in that list.
- **Reopening condition.** The underlying defect (raw-score sort mixing three incommensurable
  scales) is still live and still real — this A/B rejected two specific *fixes* for it, not the
  diagnosis. A future fix would need to either (a) give `graph_hop` a real anchor-conditioned
  score instead of literal `0.0` (addresses the root cause directly, rather than reordering
  channels around a broken score), or (b) split the window budget by channel with a low-dose
  `graph_hop` cap (N=3, deferred in the originating plan's Out-of-scope section) rather than an
  all-or-nothing tier ordering. Either direction is a new probe, not a re-run of this A/B.
