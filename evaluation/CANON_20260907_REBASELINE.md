# Retrieval Canon Re-Baseline (2026-09-07)

## Status: MEASURED — gate PASSED, no fix required

Re-pin owed since ADR-0067 (`f30494a5`, "widen `find_similar_code(exclude_same_file=True)` on
starved pools") landed 2026-09-07 and moved the indexed substrate (+12 chunks) but gated on
bit-identity, not a re-pin — so the published `CANON_20260906_REBASELINE.md` (measured on 2,956
chunks) was stale by construction the moment ADR-0067 merged. This sitting also landed two more
substrate-moving commits before capturing: a dead-code cleanup (`cec770b5` — five zero-caller
symbols deleted, two signature narrowings) and a probe migration onto `evaluation/probe_harness.py`
(`1122254d` — `probe_reserve_depth.py`, lowering the `test_probe_hygiene.py` bootstrap ratchet
19→18). One re-pin closes all three; see `docs/adr/0068-*.md` for the full decision record.

## Substrate

Full force reindex (`tools/batch_index.py --path . --mode force`, after MCP `cleanup_resources`):
**235 files / 2,965 chunks** (+9 vs the 09-06 pin's 2,956 — net of ADR-0067's +12, the cleanup
commit's deletions, and the probe migration's rewrite), graph 6,833 nodes / 30,478 edges.
`audit_golden_dataset.py` CLEAN on both datasets before capture. All legs with
`CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0` exported, strictly sequential
(`run_sscg_benchmark.py --project-path .`).

## Pre-registered gate

|ΔMRR| ≤ 0.02 and Δrecall@20 ≥ −0.02 vs the 09-06 pin (0.8151 / 0.6324 / 0.8657) on all three
views; guard-rails `Overall: PASS` on every leg; 63q determinism bit-identical across rounds.

## Results (hybrid, k=10, deterministic)

| Dataset | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | NDCG@5 | pool_hit_rate | file |
|---|---|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8228** | 0.6519 | 0.7621 | 0.8264 | 0.6785 | 1.0000 | `canon_63q_r1_20260907.json` |
| Expanded (`golden_dataset_expanded.json`, non-D) | 133 | **0.6435** | 0.6082 | 0.7197 | 0.7724 | 0.5975 | 0.9023 | `canon_133q_r1_20260907.json` |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8657** | 0.6565 | 0.7584 | 0.8137 | 0.6892 | 1.0000 | `canon_63q_fsim_r1_20260907.json` |

## Delta vs the superseded pin (2026-09-06: 0.8151 / 0.6324 / 0.8657)

| set | ΔMRR | Δrecall@20 | gate |
|---|---|---|---|
| 63q | +0.0077 | −0.0036 | PASS |
| 133q | +0.0111 | −0.0136 | PASS |
| F-via-similar | 0.0000 | −0.0021 | PASS |

All inside the ±0.02 band; recall@20 deltas ≥ −0.02. Determinism: 63q r1/r2 paired `--compare`
showed `mean_d = +0.0000`, `n_moved = 0` on every metric across all 63 shared queries
(`canon_63q_r2_20260907.json`) — bit-identical. F-via-similar's exact MRR match to the superseded
pin (0.8657 both) is coincidental, not a stale-capture artifact — its own r1 leg is a fresh capture
against the new 2,965-chunk substrate, and the 63q/133q legs on the same substrate both moved.

## What this pin settles

The substrate drift across ADR-0067 (starvation-widening fix, provably inert on this repo's own
corpus per ADR-0067's own bit-identity verification) plus the cleanup/probe-migration commits (pure
deletions, signature narrowing, and a probe rewrite — no retrieval-path code touched) nets out to
ordinary noise on a flat baseline, same read as every prior re-pin since 09-01. No regression, no
follow-up required.

Supersedes `CANON_20260906_REBASELINE.md` as current canon.
