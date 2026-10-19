# Retrieval Canon: cuDNN fused attention for the Jina listwise reranker (2026-10-19)

## Status: MEASURED — pre-registered gates PASSED on corrected labels; `reranker.listwise_attention_backend="cudnn"` ADOPTED as default

Full protocol, per-view tables, gate verdicts, label audit and movers:
`evaluation/ATTN_BACKEND_AB_20261018.md`.
Decision record: `docs/adr/0088-cudnn-attention-for-listwise-reranker.md`.

## Substrate

HEAD `3bb9d7bad25d82233befb9f5143c4ff10d497e52` index, 3,283 chunks / 247 files,
`codefuse-ai/F2LLM-v2-0.6B` / 1024d, `jinaai/jina-reranker-v3` pinned at `d7d7e73b`
(`7c3725f6`), torch 2.11.0+cu128, cuDNN 9.19.0, RTX 4090 (sm89),
`CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, no `--deterministic-gpu` (it refuses the cuDNN kernel).
All seven legs (133q control/treatment, 63q control/treatment r1/r2, F-via-similar
control/treatment) ran in one session on one index with no reindex between them
(`config_metadata.substrate` identical: resolver edges lsp 2209 / libcst 804 / chunker 1174 / pyan 615). Control = `"default"`
(torch's own dispatch, the math kernel), treatment = `"cudnn"`. Golden sets:
`golden_dataset_expanded.json` with the H012/H004 label fix from the A/B's label audit;
`golden_dataset.json` unchanged.

## Canon (treatment, `"cudnn"`)

| view | MRR | recall@5 | recall@10 | recall@20 | pool_hit_rate | gold_in_window_rate |
|---|---|---|---|---|---|---|
| 63q | **0.8235** | 0.6321 | 0.7662 | 0.8566 | 1.0000 | 1.000 |
| 133q | **0.6750** | 0.6483 | 0.7727 | 0.8569 | 0.9624 | 0.962 |
| F-via-similar | **0.8735** | 0.6292 | 0.7755 | 0.8308 | 1.0000 | 1.000 |

63q r1/r2 bit-identical (every per-query row, only `latency_ms` differs).

## Decomposition (MRR; 63q / 133q / F-via-similar)

| step | 63q | 133q | F-via-similar |
|---|---|---|---|
| 10-01 canon (`gar_interleave`, 3,114 chunks, old labels) | 0.8415 | 0.6637 | 0.8915 |
| 10-18 control, math kernel (`d293cb07`, 3,283 chunks, old labels) | 0.8173 | 0.6523 | 0.8656 |
| 10-19 control, math kernel (`3bb9d7bad25d82233befb9f5143c4ff10d497e52`, 3,283 chunks, corrected labels) | 0.8173 | 0.6645 | 0.8656 |
| 10-19 treatment, cuDNN kernel | 0.8235 | 0.6750 | 0.8735 |

- 10-01 canon -> 10-18 control is substrate drift, not a kernel effect: content (3,114 -> 3,283
  chunks) plus about 30 un-pinned search-path commits between 10-01 and `7c3725f6`. It breaches
  the +-0.02 MRR band on 63q and F-via-similar (recorded as gate 1 in the A/B doc); the control
  runs the unchanged math kernel on the same index as the treatment.
- 10-18 control -> 10-19 control: same chunk count, but the MCP server reindexed between the two
  sessions and rebuilt the call graph (resolver edge counts lsp 2099 -> 2209, libcst 733 -> 804,
  pyan 599 -> 615), and 133q carries the label fix. 59 of 133 result sets differ. Mechanism as
  in the 09-20 canon: PageRank centrality reaches ranking through the BM25 adaptive boost and the
  ego-graph ordering. Paired legs must share one session; these do.
- control -> treatment is the kernel. Paired deltas (treatment minus control, bootstrap 95% CI):
  63q MRR +0.0062 [-0.0040, +0.0234], recall@10 +0.0019 [-0.0180, +0.0225], recall@20 +0.0053 [0.0000, +0.0159];
  133q MRR +0.0105 [+0.0006, +0.0231] (CI excludes 0), recall@10 +0.0071 [-0.0198, +0.0340], recall@20 +0.0088 [-0.0075, +0.0288];
  F-via-similar MRR +0.0079 [0.0000, +0.0238], recall@10 +0.0019 [-0.0180, +0.0225], recall@20 +0.0053 [0.0000, +0.0159].
  No CI excludes 0 on the negative side. `pool_hit_rate`: 63q and F 1.0 under both kernels,
  133q 127 -> 128 of 133.
- 63q: 3 MRR movers (1 up, 2 down): Q95 0.333 -> 0.250; Q70 0.125 -> 0.100; Q90 0.500 -> 1.000.
- F-via-similar: 1 MRR movers (1 up, 0 down): Q90 0.500 -> 1.000.
- 133q: 17 MRR movers (10 up, 7 down): Q95 0.333 -> 0.250; Q105 0.333 -> 0.250; H049 0.333 -> 0.250; Q122 0.250 -> 0.200; Q70 0.125 -> 0.100; H045 0.100 -> 0.083; H021 0.077 -> 0.071; Q103 0.091 -> 0.111; Q128 0.077 -> 0.125; Q111 0.200 -> 0.250; Q125 0.200 -> 0.250; Q114 0.250 -> 0.333; H009 0.000 -> 0.125; H022 0.333 -> 0.500; Q119 0.000 -> 0.200; Q90 0.500 -> 1.000; H062 0.500 -> 1.000.

## Caveats carried forward

The two from the 09-20 and 10-01 canons: numbers need this machine's non-default
`search_config.json`, and are measured with the intent layer pinned off. New: this pin crosses a
kernel boundary, so a like-for-like replay against older pins needs
`--set reranker.listwise_attention_backend=default` (or `math`); and 133q is on the corrected
H012/H004 labels, so pre-10-19 133q numbers differ by those two queries as well as by substrate.
