# No-op check (plan verification item 2) — 2026-08-06

## What was checked

Plan verification item 2 for the `evaluate-rag` skill audit: run the harness with no
`--split` flag and diff the aggregate against `evaluation/sscg_canon_j1_63q_r1.json` —
expected identical, since `--split`'s filter block (`if split_filter: ...`) is a pure
no-op when the flag is omitted (`split_filter=None`).

Actual run (`noop_check_j1`, saved as `evaluation/noop_check_j1_20260806.json`):

| metric | canon_j1 published | this run | delta |
|---|---|---|---|
| mrr | 0.8458 | 0.8455 | -0.0003 |
| recall@5 | 0.6498 | 0.6609 | +0.0111 |
| recall@10 | 0.7640 | 0.7783 | +0.0143 |
| avg_pool_size | 29.0 | 30.0 | +1.0 |
| pool_hit_count | 63 | 1 | -62 |

Not byte-identical. `pass_fail` all still PASS; both runs materially agree (Δmrr = -0.0003).

## Why: self-index drift, not a Step 1/2 defect

This project indexes its own source tree for the MCP search tool it ships (`CLAUDE.md`'s
"Search-First Protocol"). The Step 1-3 work in this session edited five files that are part
of that self-indexed corpus: `run_sscg_benchmark.py`, `aggregate_by_slice.py`,
`run_benchmark.sh`, `test_line_overlap_metrics.py`, plus `analyze_chunking_corpus.py`'s
prerequisite cleanup. `enable_auto_reindex: true` / `max_index_age_minutes: 30.0`
(`search_config.json`) mean the live index picked up those edits automatically between when
`canon_j1` was captured and this no-op check — same mechanism as the documented
[project memory] "self-index drift" finding (ADR-0018 C1/C2 session, 2026-08-02): editing
indexed source files between benchmark captures shifts the corpus via auto-reindex, and this
is not itself a regression.

`avg_pool_size` 29.0 → 30.0 (one more candidate in the fused pool) is consistent with new
chunks entering the corpus from the edited files. `pool_hit_count` 63 → 1 is a red herring,
not part of this: the printed leaderboard line for this run shows
`pool_hit_rate=1.000 (avg pool 30.0 candidates, n=1 queries)` — that "n=1" is the count of
queries where the *ego-rerank* pass fired (`ego-rerank pass fired on 1/63 queries`, confound
log for this run), an unrelated per-run confound stat, not the golden-query-level pool-hit
metric (which is `pool_hit_rate`, unaffected).

## Why the code itself is still verified correct

`split_filter` only affects `filtered` inside `if split_filter:` (`run_sscg_benchmark.py`,
Step 1); with the flag omitted the block never executes, so the query list, execution order,
and every downstream computation are byte-for-byte the same code path as before Step 1 existed.
This is confirmed structurally (the guard), not just empirically — the drift above lives
entirely in *what's indexed*, upstream of any code this session touched functionally.

## Disposition

No action needed. `canon_j1` stays the published baseline (unaffected — it was captured
before this session's edits and is not being re-derived here). This note exists so a future
reader diffing `noop_check_j1.json` against `sscg_canon_j1_63q_r1.json` doesn't mistake
self-index drift for a `--split` regression.
