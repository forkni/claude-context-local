# Retrieval Canon: `gar_interleave` window membership (2026-10-01)

## Status: MEASURED — pre-registered gate PASSED; `merged_pool_policy="gar_interleave"` ADOPTED as default

Full protocol, per-view tables, gate verdicts and movers: `evaluation/GAR_WINDOW_AB_20261001.md`.
Decision record: `docs/adr/0079-gar-style-rerank-window-membership.md`.

## Substrate

HEAD index, 3,114 chunks, `codefuse-ai/F2LLM-v2-0.6B` / 1024d, `jinaai/jina-reranker-v3`,
`CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`. Both A/B legs share one index with no reindex between
them.

## Canon (treatment, `gar_interleave`)

| view | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | gold_in_window_rate |
|---|---|---|---|---|---|---|
| 63q | **0.8415** | 0.6506 | 0.7631 | 0.8425 | 1.0000 | 1.000 |
| 133q | **0.6637** | 0.6558 | 0.7794 | 0.8427 | 0.9624 | 0.970 |
| F-via-similar | **0.8915** | 0.6459 | 0.7671 | 0.8163 | 1.0000 | 1.000 |

63q r1/r2 bit-identical.

## Decomposition (MRR; 63q / 133q / F-via-similar)

| step | 63q | 133q | F-via-similar |
|---|---|---|---|
| 09-23 canon (`092f14ab`, 3,100 chunks) | 0.8177 | 0.6527 | 0.8668 |
| HEAD, control `"score"` (3,114 chunks) | 0.8275 | 0.6268 | 0.8854 |
| HEAD, treatment `"gar_interleave"` | 0.8415 | 0.6637 | 0.8915 |

- canon -> control is content drift (14 more chunks, new files) acting on the pre-existing
  mixed-scale window defect. 133q MRR (-0.0259) and recall@20 (0.7774 -> 0.7521, -0.0253) move
  outside the +-0.02 drift band; 63q and F-via-similar MRR move up. Not a code regression: no
  ranking code changed in that range.
- control -> treatment is the fix: 133q recall@5/10/20 improve with CIs excluding 0 positive
  (+0.061 / +0.094 / +0.091); everything else is CI-spanning-0 positive.
- **Unresolved:** the first HEAD run of this investigation (02:56, same SHA and chunk count)
  scored 63q MRR 0.7980, not 0.8275. Nine queries differ; the cause is unknown (an index rebuild
  in between is suspected, unconfirmed). It does not affect the control-vs-treatment gate.

## Caveats carried forward

Same two as the 09-20 canon: numbers need this machine's non-default `search_config.json`, and are
measured with the intent layer pinned off.
