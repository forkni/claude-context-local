# Retrieval Canon Re-Baseline (2026-09-03)

## Status: MEASURED

Phase 2 of the pyan-fidelity-verification plan
(`docs/plans/i-want-you-to-fuzzy-truffle.md`). Substrate drifted since the 2026-09-01 pin
(219→233 files, 2,642→2,832 chunks) from the call-graph-recall commit burst
(`adf4efb`…`cc6419e`, see `RESOLVER_TIER_CALIBRATION_20260902.md` §13). Supersedes
`CANON_20260901_REBASELINE.md` (63q 0.8419 / 133q 0.6378 / F-via-similar 0.8843) as *drift
from corpus growth*, not a regression finding — this document is not itself a test of the
pyan work; it exists to give Phase 3's A/B a valid base arm.

## Substrate

- Clean Phase 0 force reindex: `.venv/Scripts/python.exe tools/batch_index.py --path . --mode
  force`, `user_excluded_dirs` reused unchanged (`_archive`, `tests`, `audit_reports`,
  `benchmark_results`, `htmlcov`, `tmp`, `code-search-extension`). Result: **233 files / 2,832
  chunks**, F2LLM-v2-0.6B (1024d).
- `get_index_status` confirmed `index_is_current: true`, `pending_changes: {added:0,
  modified:0, removed:0}` before capture began.
- Resolver mix re-derived from the fresh persisted call graph (chunk→chunk `calls` edges):
  `lsp 1875 / <ast> 3707 / libcst 720 / pyan 552`, total 6,854 — matches §13's composed-HEAD
  fidelity numbers on the same substrate.

## Determinism (ADR-0021)

Single round per view, per the established canon protocol (`CANON_20260901_REBASELINE.md`
§Determinism) — `PYTHONHASHSEED=0` auto-re-exec confirmed in every run's log header. One
extra r2 confirmation round was captured on 63q only, as a determinism assertion (not a
second canon round):

- `verify_base_63q_r2_20260903.json`: all 63 `retrieved` lists **bit-identical** to r1, and
  every `aggregate`-level retrieval-quality metric bit-identical (MRR 0.8429, recall@5 0.6485,
  etc.). r2 additionally reports `pool_hit_rate`/`pool_hit_count`/`avg_pool_size` keys r1
  lacks, and per-query `confounds` (`rerank_calls`, `ego_rerank_pass`, `centrality_seeded`)
  diverge on all 63 queries (r1: 0/63 engaged; r2: 63/63 engaged).
- **This is a benchmark-harness instrumentation artifact, not a retrieval determinism
  regression.** Confirmed during Phase 3: two back-to-back treatment-arm runs in the same
  session showed the identical binary pattern in the *opposite* direction (`drop_amb_63q`:
  63/63 engaged; `drop_amb_133q`, run immediately after: 0/133 engaged) — i.e. the confound
  telemetry is bimodal per-process, uncorrelated with dataset, knob, or query content, and
  every run's actual `retrieved` lists and aggregate metrics were unaffected regardless of
  which state it landed in. Root cause not chased further (out of scope for a retrieval
  verification pass — `_instrument_rerank_calls`/`_EgoConfoundRecorder` in
  `scripts/benchmark/run_sscg_benchmark.py` attach to `searcher.reranking_engine` /
  `searcher.ego_graph_retriever` object references that plausibly go stale against a
  lazily-(re)constructed searcher on some runs and not others). Flagged here as a minor
  harness observability gap, not a blocker: the plan's stop-and-report rule targets ADR-0021-
  class pool-composition flips, and there were none — 0/63 `retrieved`-list diffs.

## Results

| Run | queries | MRR | R@5 | R@7 | R@10 | R@20 | R@50 | NDCG@5 | HR@5 | avg latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| `verify_base_63q_20260903.json` | 63 | **0.8429** | 0.6485 | 0.7184 | 0.7625 | 0.8446 | 0.8446 | 0.6829 | 1.000 | 4,607.8 |
| `verify_base_133q_20260903.json` | 133 | **0.6332** | 0.6172 | 0.6606 | 0.7168 | 0.7929 | 0.7929 | 0.5954 | 0.8496 | 4,556.6 |
| `verify_base_fsim_20260903.json` (`--f-via-similar`) | 63 | **0.8856** | 0.6478 | — | 0.7637 | 0.8190 | 0.8190 | 0.6905 | 1.000 | 3,930.9 |

All three runs `Overall: PASS` on the three gate thresholds (mrr≥0.5, recall@5≥0.55,
hit_rate@5≥0.8). The F-via-similar run again exits process code 1 despite a clean `Overall:
PASS` print and a valid saved JSON — the same benign teardown artifact `CANON_20260901_
REBASELINE.md` documented; not re-investigated.

## Delta vs the superseded pin

| Pin | 63q MRR | 133q MRR | F-via-similar MRR | Δ this canon |
|---|---|---|---|---|
| 2026-09-01 (`CANON_20260901_REBASELINE.md`) | 0.8419 | 0.6378 | 0.8843 | +0.0010 / −0.0046 / +0.0013 |

All three deltas are inside the run-to-run noise band this project's benchmark history has
consistently shown (±0.02 typical spread per `feedback`/project memory on SSCG run noise).
Read as substrate drift from the +14-file/+190-chunk corpus growth, not a quality regression
or a quality improvement attributable to the call-graph fixes — the retrieval canon and the
call-graph fidelity measurement (§13) are different axes, and neither moved the other here.

## Corpus-identity note

`get_index_status` reported `index_refreshed: true` once mid-campaign, from a later
`search_code` MCP call. Checked and confirmed benign, same non-event pattern as the
2026-09-01 pin's precedent: writing `evaluation/*.json` benchmark output files triggers the
30-minute staleness auto-reindex's "Added: N" detection, which then chunks 0 files (`.json`
is not an indexed source extension). `get_index_status` immediately after showed
`index_is_current: true`, `pending_changes: {added:0, modified:0, removed:0}`, and file/chunk
counts unchanged at 233/2,832 — no Phase 0 substrate guard violation occurred.
