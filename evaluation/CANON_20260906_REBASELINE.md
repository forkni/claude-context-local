# Retrieval Canon Re-Baseline (2026-09-06)

## Status: MEASURED — gate PASSED, no fix required

Re-pin on top of `CANON_20260905B_ADR0063_REBASELINE.md` after commit `8e3522d`
(`feat(graph): opt-in contains-edge exclusion from centrality`), which touches indexed `graph/`
and `search/` files and therefore shifts the substrate. The base arms of the paired A/B in
`CONTAINS_CENTRALITY_ISOLATION_20260906.md` double as this pin (precedent: ADR-0019 base arms).
Full method, gates, incident log and attribution live in that document; this file is the
canon-of-record pointer.

## Substrate

Full force reindex (`tools/batch_index.py --path . --mode force`, after MCP `cleanup_resources`):
**235 files / 2,956 chunks** (+1 file, +11 chunks vs 09-05b — the new probe script and the
knob's code), 1,095 containment edges, graph 6,822 nodes / 30,449 edges.
`audit_golden_dataset.py` CLEAN on both datasets before capture. All legs with
`CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0` (harness self-pin, ADR-0021), strictly sequential.

## Pre-registered gate

|ΔMRR| ≤ 0.02 and Δrecall@20 ≥ −0.02 vs the 09-05b pin on both sets; guard-rails `Overall: PASS`
on every leg; 63q determinism bit-identical across rounds.

## Results (hybrid, k=10, deterministic)

| Dataset | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | NDCG@5 | pool_hit_rate | file |
|---|---|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8151** | 0.6443 | 0.7635 | 0.8300 | 0.6715 | 1.0000 | `canon_63q_r1_20260906.json` |
| Expanded (`golden_dataset_expanded.json`, non-D) | 133 | **0.6324** | 0.6002 | 0.7242 | 0.7860 | 0.5808 | 0.9098 | `canon_133q_r1_20260906.json` |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8657** | 0.6557 | 0.7730 | 0.8158 | 0.6913 | 1.0000 | `canon_63q_fsim_r1_20260906.json` |

## Delta vs the superseded pin (2026-09-05b: 0.8164 / 0.6286 / 0.8671)

| set | ΔMRR | Δrecall@20 | gate |
|---|---|---|---|
| 63q | −0.0013 | −0.0059 | PASS |
| 133q | +0.0038 | −0.0009 | PASS |
| F-via-similar | −0.0014 | −0.0059 | PASS |

Read as drift on a flat baseline. Determinism: the treatment 63q r1/r2 pair and the base 63q leg
vs its discarded first-run twin were all bit-identical (0/63 `retrieved` diffs).

## What this pin settles

The `contains`-edge PageRank channel that the 09-05 and 09-05b pins left entangled with pool
composition has now been isolated on this exact index: excluding all 1,095 `contains` edges from
centrality moves MRR by −0.0004 on both sets (see the isolation doc). The 09-05→09-05b canon
movement is pool composition (+74 chunks) plus ordinary substrate drift, not graph topology.

Supersedes `CANON_20260905B_ADR0063_REBASELINE.md` as current canon.
