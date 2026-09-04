# `drop_ambiguous_traversal_edges` live A/B (2026-09-03) — closes D1

**Verdict: REJECTED for default change.** No statistically significant effect on recall@10 or
recall@20 on either dataset (every paired-bootstrap 95% CI includes zero), and the offline
replay's named mechanism movers mostly do not reproduce in the live pipeline (1 of 6 named
gold-chunk predictions reproduced as an actual recall@10 win). The knob stays default `false`.
Phase 3 of `docs/plans/i-want-you-to-fuzzy-truffle.md`; this is the live A/B the
`AMBIGUOUS_EDGE_REPLAY_20260902.md` offline screen earned ("earns a live A/B on recall@10/20;
it does not earn a default change").

## Method

`--set graph_enhanced.drop_ambiguous_traversal_edges=true` via the generic override
mechanism (`evaluation/arm_overrides`), not a source patch — avoids the 2026-09-02 attempt's
schema mismatch (`tmp/apply_knob.py` predated the `TraversalPolicy` refactor and produced a
`recall@10 == recall@20 == recall@50` depth-collapse artifact). Base arm = Phase 2's
`verify_base_{63q,133q}_20260903.json` runs, same session, same substrate — no separate base
capture. Single round each under the seed-0 pin, matching canon protocol. Gate: recall@10 /
recall@20, paired bootstrap (`evaluation/paired_bootstrap.py`, 10,000 resamples, seed 0) — the
knob's own pre-registered lock text at `search/config.py:1386-1389`.

## Results

| dataset | metric | base | treatment | paired mean Δ | 95% CI | significant? |
|---|---|---|---|---|---|---|
| 63q | recall@10 | 0.7625 | 0.7642 | +0.0017 | [−0.0240, +0.0265] | no |
| 63q | recall@20 | 0.8446 | 0.8293 | −0.0152 | [−0.0382, +0.0059] | no |
| 133q | recall@10 | 0.7168 | 0.7398 | +0.0230 | [−0.0105, +0.0591] | no |
| 133q | recall@20 | 0.7929 | 0.7888 | −0.0041 | [−0.0313, +0.0248] | no |

Guard-rail (no CI excluding zero on the negative side): **satisfied** on all four rows —
none of the CIs exclude zero at all, positive or negative. That also means the guard-rail's
positive counterpart is not met: no metric clears significance in the improving direction
either. MRR moved slightly negative on both datasets (63q 0.8429→0.8349, 133q
0.6332→0.6304) — not gated, reported for completeness.

Latency, all four arms (base 63q/133q, treatment 63q/133q): 4,548.9–4,607.8 ms, a 58 ms /
1.3% spread — no material difference. Guard-rail satisfied.

## Named-mover mechanism check

The offline replay named six golds it predicted would move: rescues Q12, Q57, Q75, Q102
(133q); evictions Q44, Q51, Q77. Checked directly against the live per-query
`retrieved`/`recall@10` pairs (not the replay's own pool-membership proxy):

| query | retrieved list changed? | recall@10 base→treat | replay-predicted | reproduced? |
|---|---|---|---|---|
| Q12 | yes | 0.25 → 0.25 | rescue | no |
| Q57 | yes | 0.333 → 0.333 | rescue | no |
| Q75 | yes | 0.50 → 0.75 | rescue | **yes** |
| Q102 | yes | 0.50 → 0.50 | rescue | no |
| Q44 | yes | 1.00 → 1.00 | eviction | no |
| Q51 | yes | 1.00 → 1.00 | eviction | no |
| Q77 | yes | 1.00 → 1.00 | eviction | no |

Every named query's ranked-result composition did change (`retrieved != retrieved`,
confirming the knob is live and doing something on this substrate — not a no-op), but only
Q75 flipped its gold-hit outcome. The other five held steady despite composition churn: the
gold chunk stayed in (or out of) the top-10 regardless of the ambiguous-edge drop. This is
consistent with the replay measuring *ego-graph pool membership* (an upstream, necessary-not-
sufficient signal, as its own method section states) rather than final top-10 presence after
the full rerank pass — a chunk entering the pool doesn't guarantee it survives reranking, and
one leaving doesn't guarantee its slot isn't backfilled by an equally-relevant neighbor.

## Why this substrate isn't the replay's substrate

The replay ran when `tag:ambiguous` edges were 3,149/7,458 = 42.2% of traversable chunk→chunk
calls; the pyan CLASS gate (`RESOLVER_TIER_CALIBRATION_20260902.md` §12) has since cut pyan's
edge count roughly in half without touching the AST tier, so ambiguous edges are now
3,173/6,854 = **46.3%** of the (smaller) traversable graph — the replay's own stated caveat
("the thin +2-net margin may move in either direction") materialized as a full washout to
non-significance, not a direction flip.

## Disposition

D1 closes: **rejected, not adopted as default.** `graph_enhanced.drop_ambiguous_traversal_edges`
stays `false`; `hide_ambiguous_edges_default: true` (the `find_connections` display-only
filter, unaffected by this knob) is unchanged. Re-opening this lever would need either a
substrate where ambiguous share is lower again, or a design that reserves rescued pool slots
directly into the final rerank window rather than only into ego-graph traversal — outside this
plan's scope.
