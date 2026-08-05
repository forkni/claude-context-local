# Ego-per-request view: QW5 measured for the first time — 2026-08-05

Round 1 of `temporal-enchanting-blanket.md`'s two-round plan. ADR-0030's "Out of scope" section
left the intent policy tables' deletion pending a measurement that didn't exist: `_intent_ego_thresholds`
(QW5, `search/effective_config.py:74-93`) only fires when **both** `plan.ego_graph_enabled` and
`plan.intent_decision` are set on a request. No benchmark capture in this repo's history ever set
`plan.ego_graph_enabled` — the harness's pre-existing `--ego-graph on|off` flag overrides the
*config field* `ego_graph.enabled` (already `True` by default), a different switch that never
reaches QW5 — while production MCP callers pass it by default
(`mcp_server/tool_registry.py:157`). This round teaches the harness to set the per-request flag
(`--ego-per-request`), captures the four-view matrix that isolates QW5, and hands the result to
Round 2's gate.

## What changed (harness only, no production source touched)

`scripts/benchmark/run_sscg_benchmark.py`: new `--ego-per-request` flag, threaded through
`_run_query` → `run_benchmark` → `run_single` → `main()`'s three call sites, mirroring the
`--f-via-similar` precedent. When set, `_run_query` adds `arguments["ego_graph_enabled"] = True`
to the `SearchOrchestrator.run()` call — the one-line behavioral change the whole round exists to
enable. Two new unit tests (`tests/unit/evaluation/test_run_sscg_benchmark.py`) pin the flag
absent-by-default and present-when-set. This is a pure harness addition — `canon_i1` remains the
published canon and required no re-pin for this change alone.

## Substrate

`cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force` → **205 files, 2323
chunks** (unchanged from `canon_i1` — the harness/test-only edit doesn't touch indexed production
source, `tests/` is excluded from indexing). `audit_golden_dataset.py` CLEAN on both datasets
(77q/147q) against the fresh index. `PYTHONHASHSEED=0` (ADR-0021) + `CLAUDE_AUTO_REINDEX=0` for
every capture.

## Flag smoke test

Before spending capture time: `--ego-per-request --category A` (15 queries), grepped for
`[EGO_GRAPH] Enabled with k_hops=2, max_neighbors_per_hop=10` — present on **15/15** queries,
confirming the flag reaches `build_effective_config` end-to-end. The companion
`[EGO_GRAPH] Intent-adaptive threshold` line was correctly absent (this smoke test didn't also set
`intent.enabled=true`, so `plan.intent_decision` was unset and QW5's inner branch stayed dormant —
exactly the two-switch gating the plan describes).

## Four-view capture (63q, one round each)

| metric | A: ego-off control | B: ego-on control | C: ego-off arm | D: ego-on arm |
|---|---|---|---|---|
| total / success | 63 / 63 | 63 / 63 | 63 / 63 | 63 / 63 |
| **mrr** | 0.8375 | 0.8375 | **0.8524** | **0.8537** |
| recall@1 | 0.2839 | 0.2839 | 0.2910 | 0.2910 |
| recall@5 | 0.6662 | 0.6662 | 0.6800 | 0.6840 |
| recall@7 | 0.7446 | 0.7446 | 0.7529 | 0.7529 |
| recall@10 | 0.7879 | 0.7879 | 0.8179 | 0.8126 |
| recall@20 | 0.8524 | 0.8524 | 0.8446 | 0.8446 |
| precision@1 | 0.8571 | 0.8571 | 0.8889 | 0.8889 |
| ndcg@5 | 0.6976 | 0.6976 | 0.7139 | 0.7161 |
| ndcg@10 | 0.7523 | 0.7523 | 0.7747 | 0.7723 |
| hit_rate@5 | 1.0 | 1.0 | 1.0 | 1.0 |
| line_recall | 0.9302 | 0.9302 | 0.9264 | 0.9264 |
| file_recall@5 | 0.8353 | 0.8353 | 0.8362 | 0.8401 |
| pool_hit_rate | 1.0 | 1.0 | 0.9048 | 0.9048 |
| avg_pool_size | 29.0 | 29.0 | 25.3 | 24.5 |
| avg_latency_ms | 4318 | 4309 | 3905 | 3968 |

A = intent-off control (no `--set`, harness's `pin_intent_off=True` default). C/D = intent-on arm
(`--set intent.enabled=true`, matching the shipped default). B/D additionally set
`--ego-per-request`.

### G0 — B ≡ A, byte-identical (PASS)

Programmatic diff of all 63 per-query rows, every field except `latency_ms`: **0 diffs**.
Aggregates, `confound_summary`, and every scored metric identical to 4 decimal places. This
confirms the plan's fact 2 exactly: with `intent_decision` unset (control views never classify
intent), QW5 is dormant regardless of `plan.ego_graph_enabled`, and the plan-override block at
`search_orchestrator.py:132-135` is a no-op write (`k_hops=2`/`max_neighbors_per_hop=10` match the
live config already). Nothing else moves. Had this shown any diff, the no-op-write reasoning would
have been wrong and the whole round uninterpretable — it didn't.

### G1 — A reproduces `canon_i1`'s 63q control (PASS)

A's mrr 0.8375 vs `canon_i1`'s published 0.8384 control figure — Δ 0.0009, well inside the ±0.02
noise band established across prior rounds. The harness edit didn't disturb the measurement path.

## D − C: QW5, isolated

| metric | C (ego-off arm) | D (ego-on arm) | D − C |
|---|---|---|---|
| mrr | 0.8524 | 0.8537 | **+0.0013** |
| recall@1 | 0.2910 | 0.2910 | 0.0000 |
| recall@5 | 0.6800 | 0.6840 | +0.0040 |
| recall@7 | 0.7529 | 0.7529 | 0.0000 |
| recall@10 | 0.8179 | 0.8126 | **−0.0053** |
| recall@20 | 0.8446 | 0.8446 | 0.0000 |
| precision@1 | 0.8889 | 0.8889 | 0.0000 |
| ndcg@5 | 0.7139 | 0.7161 | +0.0022 |
| ndcg@10 | 0.7747 | 0.7723 | −0.0024 |
| file_recall@5 | 0.8362 | 0.8401 | +0.0039 |
| pool_hit_rate | 0.9048 | 0.9048 | 0.0000 |
| avg_pool_size | 25.3 | 24.5 | −0.8 |

Exactly **one** of 63 queries moved at all: `Q12` (category A, "check if index exists for
project") — `pool_hit` stayed `True` in both views, only its intra-pool rank shifted
(mrr 0.1667 → 0.25). Q12 is an already-known boundary-riding query (flagged in prior benchmark
rounds as sensitive to fusion-cut effects, unrelated to this change) — its movement here is
consistent with that pre-existing sensitivity, not a new QW5-specific effect. No other query's
`pool_hit` classification, rank, or score changed.

`avg_pool_size` shrinking by 0.8 (25.3 → 24.5) shows QW5's per-intent thresholds are doing
something real to the ego-expansion neighbor admission — `{local 0.25, navigational 0.20}` are
stricter than the uniform `0.15` default, `{global 0.10, similarity 0.10, contextual 0.12}` are
looser — and the 63q set's intent mix nets slightly stricter on average. This is the first time
that mechanism has been measured at all; it simply doesn't move the score.

**Verdict: flat.** `D − C` is +0.0013 MRR from a single already-known boundary query, with
`recall@10` moving in the opposite direction by a similar magnitude — no directional signal, both
well inside noise. Per the plan's pre-registered rule, a 133q extension is not warranted (63q shows
no movement worth chasing further) and no ADR is triggered by this finding alone; it feeds Round 2's
QW5 gate directly.

## What the ego-on production path scores for the first time

Every prior canon capture (`canon_e1` through `canon_i1`) measured the harness's control path —
`plan.ego_graph_enabled` unset — even on the "arm" views that turned intent on. Production MCP
callers set `ego_graph_enabled=True` on every `search_code` call by default
(`mcp_server/tool_registry.py:157`), meaning the score users actually experience in production has
never had a dedicated capture until views B and D above. The finding: it doesn't differ
measurably from the never-set-it path this repo has been benchmarking all along. That is itself
useful information for Round 2 — QW5 has now been measured on a live path and found to be inert,
which is a materially different claim than "unmeasured."

## Disposition

- **Round 2's QW5 gate**: flat ⇒ eligible for deletion, consistent with the gate's own stated rule
  ("Flat ⇒ delete").
- No ADR from this round alone (flat result, no behavior/production change). CHANGELOG entry
  filed under `[Unreleased] / Added`.
- Capture JSONs (`evaluation/egoreq_{a,b,c,d}_63q_r1.json`) are not tracked in git, per the
  precedent set by every prior canon/view capture — this markdown file is the durable record.

## Next

Round 2 (delete `_intent_ego_thresholds`, the `INTENT_EDGE_WEIGHT_PROFILES` consumption, and the
table itself, per `temporal-enchanting-blanket.md`) can proceed on the QW5 side. The A1 gate
(drift-cancelled difference-of-differences including `recall@10`) is unaffected by this round and
still requires its own pre/post comparison at deletion time.
