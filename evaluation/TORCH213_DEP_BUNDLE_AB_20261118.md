# torch 2.13 + dependency bundle A/B (2026-11-18)

## Status: MEASURED — no retrieval change on the shared index; within noise after a full reindex. Bundle ADOPTED

Branch `chore/torch-2.13-dep-bundle`: `855d844f` (torch 2.11.0+cu128 -> 2.13.0+cu130,
setuptools 81.0.0 -> 84.2.1), `40f5fee8` (pyan 2.9 `Scope` argument fix), `5d7b29cb`
(`uv lock --upgrade`, 84 packages, pytest-asyncio loop-scope setting).

## Why

`/deps-audit` 2026-11-18: torch CVE-2025-3000 (fix 2.13.0) and setuptools CVE-2026-59890 /
GHSA-xmj3-9gf7-h52w (blocked by torch 2.11's `setuptools<82`). The cu128 wheel index stops at
2.11.0, so the pin moves to the cu130 index. Driver 621.24 supports CUDA 13.0.

## Substrate

| | control | treatment |
|---|---|---|
| torch / cuDNN | 2.11.0+cu128 / 9.19.0 | 2.13.0+cu130 / 9.20.0 |
| transformers | 5.17.0 | 5.23.0 |
| sentence-transformers | 6.1.0 | 6.3.0 |
| faiss-cpu | 1.15.1 | 1.16.0 |
| huggingface-hub | 1.26.1 | 2.4.0 |
| pyan3 | 2.8.1 | 2.9.0 |

Index: 3,381 chunks / 250 files, `codefuse-ai/F2LLM-v2-0.6B`, reranker `jinaai/jina-reranker-v3`
(cuDNN attention, ADR-0088). `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, k=10, hybrid, no
`--deterministic-gpu`. MCP server stopped for the whole protocol; no indexed-file edits between
the control and the shared-index treatment legs.

Legs (dumps `evaluation/ab_torch213_<leg>_20261118.json`, unstaged):

- `c63`, `c133`, `cf`: control, old venv, index built at `a9e7cdbc`.
- `t63`, `t63r2`, `t133`, `tf`, `t63_8gb`: new venv, **same index and call graph** as control.
- `r63`, `r133`, `rf`: new venv after `tools/batch_index.py --mode force` (call graph rebuilt with
  pyan 2.9; resolver edges lsp 2318 / libcst 809 / chunker 1183 / pyan 619 -> 621).

## Results

| view | control MRR | shared-index MRR | reindexed MRR | control r@20 | reindexed r@20 | pool_hit (all legs) |
|---|---|---|---|---|---|---|
| 63q | 0.8248 | 0.8248 | 0.8246 | 0.8668 | 0.8562 | 1.0000 |
| 133q | 0.6738 | 0.6738 | 0.6718 | 0.8605 | 0.8554 | 0.9624 |
| F-via-similar | 0.8750 | 0.8750 | 0.8750 | 0.8388 | 0.8388 | 1.0000 |

- **Shared index (dependency effect alone):** every retrieved list identical to control, same
  order, on 63q (63/63), 133q (133/133) and F-via-similar (63/63). The treatment was live:
  `library_versions` show the new stack and the log shows `cudnn kernel active (cudnn=92000)`.
- **Reindexed (dependency + rebuilt call graph):** paired deltas, bootstrap 95% CI:
  63q MRR -0.0002 [-0.0005, +0.0000], recall@20 -0.0106 [-0.0317, +0.0000];
  133q MRR -0.0020 [-0.0058, +0.0000], recall@20 -0.0050 [-0.0150, +0.0000];
  F MRR +0.0000, recall@20 +0.0000. No CI excludes 0. MRR movers: Q70 0.091 -> 0.083,
  Q97 0.071 -> 0.067, H022 0.500 -> 0.250 (133q only). Order changes on 19/63, 34/133 and 16/63
  queries. The same size of movement followed a reindex alone in the 10-19 canon (59/133 sets
  changed), so this is read as graph-rebuild noise, not a dependency effect.

## Gates (ATTN_BACKEND_AB_20261018 protocol)

1. Drift (control vs 10-19 canon 0.8235 / 0.6750 / 0.8735): +0.0013 / -0.0012 / +0.0015. PASS.
2. No paired CI excludes 0 on the negative side (MRR, recall@10, recall@20, all views): PASS.
3. `pool_hit_rate` non-decreasing: PASS (unchanged on every view).
4. Determinism `t63` == `t63r2` (every per-query row except latency): PASS.
5. No `Non-finite reranker scores` in any treatment log: PASS.
6. 8 GB leg (`vram_limit_fraction=0.34`, effective 27%, about 6.2 GB): no OOM, metrics identical. PASS.

## Latency (avg ms per query, reported, not gated)

| view | control | shared-index | reindexed |
|---|---|---|---|
| 63q | 1295 | 733 | 697 |
| 133q | 1255 | 874 | 658 |
| F-via-similar | 1186 | 796 | 600 |

About 30-50% faster on the new stack. The 8 GB leg averaged 902 ms.

## Breakages found and fixed

- pyan3 2.9.0 calls `Scope(table, marker_prefix)`; `_ModuleOnlyTopScope.__init__` took only
  `table`, so every file failed and the pyan tier resolved 0 edges (12 unit tests failed).
  Fixed in `40f5fee8`. pyan 2.9.0 still blanks any scope named `top`, so the workaround stays.
- pytest-asyncio 1.5.0 warns on an unset `asyncio_default_fixture_loop_scope`; with
  `filterwarnings = error` that stops pytest before collection. Set to `"fixture-scope"`.

Unit tier after the fixes: 5,595 passed, 2 skipped.

## Canon

The 10-19 canon numbers stay valid as a reference (control drift is inside the band). The
reindexed legs are the new substrate of record: 63q MRR **0.8246**, 133q **0.6718**,
F-via-similar **0.8750**.

## Open

- Users on drivers older than R580 (no CUDA 13.0) cannot run the cu130 wheels; the installer
  now says so.
- sqlitedict CVE-2024-35515 stays deferred (no upstream fix; JSON encode/decode mitigation intact).
