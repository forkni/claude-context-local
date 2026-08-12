# Per-split reporting on the standing canon — 2026-08-06

## Context

`evaluate-rag` skill audit (G1): every golden query has always carried a `train`/`val`/`test`
`split` field (canonical 43/16/18 file totals, 35/13/15 scored; expanded 86/28/33 file totals,
78/25/30 scored), but nothing published against it — `run_sscg_benchmark.py` had no `--split`
flag, and `aggregate_by_slice.py` (built 2026-08-04) had been run once, ad hoc, wired into no
workflow or canon doc. `CANON_20260804.md:105-113` already flagged the consequence: a real
train/val generalization gap (63q train 0.9143 vs val 0.6328 at the time). The ~20 config A/Bs
behind the current canon chain were all decided on the full set regardless.

## Policy (standing, effective this round)

- **Canon figures stay full-set** for comparability with every prior round — this file does
  not change what gets published as "the" MRR.
- **Every future canon re-pin additionally records** the `aggregate_by_slice.py` per-split
  table for its capture files, alongside the full-set number. This file is the first instance
  and the template; it is not applied retroactively to the seven `CANON_*.md` files that
  predate it (`CANON_20260803.md` through `CANON_20260805_CONFIG_SEAM_REPIN.md`) — those are
  immutable historical records, already superseded, and re-deriving their per-split tables
  would not change any decision already made.
- **Tuning consults train+val only.** `test` is quoted when re-pinning, for monitoring the
  generalization gap, and is never the basis for adopting or rejecting an arm.
- Paired-CI arm adoption (methodology rule 7, `RECALL_CAMPAIGN_CLOSEOUT_20260802.md`) and this
  split policy are independent and compose: an arm's paired delta can be computed on the
  train+val subset via `run_sscg_benchmark.py --split train` / `--split val` plus `--compare`.

## Per-split tables — `canon_j1` (current standing pin, `docs/adr/0031-...md`)

Generated via `python scripts/benchmark/aggregate_by_slice.py <file>` — reconciliation (sliced
mean vs published aggregate) passed on all four views, deltas ≤ 1.8e-5.

### 63q, intent-on arm (published baseline, MRR 0.8603)

| split | n | mrr | recall@5 | recall@10 | ndcg@5 | hit |
|---|---|---|---|---|---|---|
| train | 35 | 0.9152 | 0.6456 | 0.7785 | 0.7015 | 1.0000 |
| val | 13 | 0.6923 | 0.7385 | 0.8026 | 0.6999 | 1.0000 |
| test | 15 | 0.8778 | 0.6575 | 0.7908 | 0.7187 | 1.0000 |

### 63q, intent-off control (MRR 0.8458)

| split | n | mrr | recall@5 | recall@10 | ndcg@5 | hit |
|---|---|---|---|---|---|---|
| train | 35 | 0.9143 | 0.6469 | 0.7472 | 0.6995 | 1.0000 |
| val | 13 | 0.6777 | 0.6872 | 0.7923 | 0.6701 | 1.0000 |
| test | 15 | 0.8317 | 0.6241 | 0.7787 | 0.6691 | 1.0000 |

### 133q, intent-on arm (published baseline, MRR 0.6869)

| split | n | mrr | recall@5 | recall@10 | ndcg@5 | hit |
|---|---|---|---|---|---|---|
| train | 78 | 0.7002 | 0.6531 | 0.7756 | 0.6496 | 0.8846 |
| val | 25 | 0.6733 | 0.7227 | 0.7840 | 0.6581 | 0.9200 |
| test | 30 | 0.6636 | 0.6287 | 0.7454 | 0.5998 | 0.8667 |

### 133q, intent-off control (MRR 0.6725)

| split | n | mrr | recall@5 | recall@10 | ndcg@5 | hit |
|---|---|---|---|---|---|---|
| train | 78 | 0.6876 | 0.6409 | 0.7552 | 0.6378 | 0.8590 |
| val | 25 | 0.6657 | 0.6760 | 0.7787 | 0.6331 | 0.9200 |
| test | 30 | 0.6388 | 0.6121 | 0.7310 | 0.5736 | 0.8667 |

## Reading

- **The train/val gap persists on the current substrate.** 63q arm: train MRR 0.9152 vs val
  0.6923, a 0.223 gap — narrower than the 0.28 first measured against an earlier substrate
  (`CANON_20260804.md`), but not closed. 133q arm: train 0.7002 vs val 0.6733, a much smaller
  0.027 gap — the larger, more diverse expanded set generalizes better than the 63q canonical
  set, which is small enough (13-15 queries per non-train split) that per-query noise dominates
  any one split's mean.
- **`test` tracks close to `val` on both sizes** (63q: 0.8778 vs 0.6923 val — wider; 133q:
  0.6636 vs 0.6733 val — closer), which is consistent with `test` never having been tuned
  against, as intended.
- **13-15-query splits are noisy.** A single query's MRR swing (0 → 1) moves a 13-query split
  mean by ~0.077 — any single-round per-split comparison should be read as a rough signal, not
  a precise estimate; this is the same reasoning behind the paired-CI rule for full-set A/Bs,
  applied one level down.
- No adoption decision is being made or reversed by this report — it is the first application
  of the standing policy above, to the canon already in place.
