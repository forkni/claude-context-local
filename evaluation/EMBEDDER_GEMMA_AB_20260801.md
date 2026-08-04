# Embedder A/B: google/embeddinggemma-300m vs F2LLM-v2-0.6B (2026-08-01) — INCIDENT, DROPPED

## Verdict: DROPPED — not scheduled

The A/B never produced a comparison. Its own harness
(`scripts/benchmark/embedder_gemma_vs_bgem3_ab.py`) destroyed the deployed
search index mid-run, on a safety premise that was false at HEAD. The harness
has been deleted (repo policy: delete-don't-leave-dormant, per
ADR-0015/ADR-0016/ADR-0019). This comparison is **dropped, not deferred**:
Gemma-vs-F2LLM is not a pending task and will not be re-run absent a new
harness satisfying the precondition in Decision 3 below. `google/embeddinggemma-300m`
(768d, `MODEL_REGISTRY` entry, `search/config.py:20-27`) stays in the registry
and remains selectable via manual model switch — only the comparison is
dropped, not the model.

## What happened

The harness's "Safety design" docstring claimed that swapping
`config.embedding.model_name` in memory (never calling `save_config()`)
confines a force-reindex to an isolated `..._gemma-300m_768d` storage
directory, leaving the deployed F2LLM index untouched. That premise does not
hold at HEAD.

`handle_index_directory` calls `invalidate_config_caches()`
(`mcp_server/tools/index_handlers.py:862`, added for ADR-0014 per-project
overrides). That function sets `search.config._config_manager = None`
(`mcp_server/state.py:321`), so the very next `get_search_config()` call
re-reads `search_config.json` **from disk** — where the model was still
`codefuse-ai/F2LLM-v2-0.6B`, precisely because the swap was deliberately
never persisted. `get_project_storage_dir`
(`mcp_server/storage_manager.py:229-231`) then resolves the storage
directory from that re-read config, landed on the **deployed** F2LLM
directory instead of the intended isolated Gemma one, and the full-reindex
path cleared it.

`reset_for_model_switch()` (`mcp_server/state.py:261-273`) clears the
embedder/index-manager/searcher singletons but **not** `_config_manager` —
so the harness's own pre-reindex `get_project_storage_dir()` call correctly
printed the Gemma path (and created that empty directory) moments before the
actual reindex resolved F2LLM instead. The two disagreeing resolutions
within one run are the signature of this defect.

The run then raised `PermissionError` on `metadata.db` — the harness's own
arm-1 searcher still held the sqlite handle — but only *after* the
deletions below had already happened.

## Damage (verified on disk, all under `claude-context-local_9e7f0a98_f2llm-v2-0.6b_1024d`)

| Path | State before repair |
|---|---|
| `index/code.index` | deleted |
| `index/chunk_ids.pkl` | deleted |
| `index/bm25/` (3 files) | deleted, directory emptied |
| Merkle snapshot | deleted |
| `index/metadata.db` | survived (14.5 MB), left inconsistent with the missing indices |
| `index/chunk_embeddings.bin` | survived (18.5 MB) — v0.22.0 persistent embedding cache |
| `project_info.json` | survived, `user_excluded_dirs` intact (9 entries) |
| `..._call_graph.json` | survived (8.4 MB) |

An empty `claude-context-local_9e7f0a98_gemma-300m_768d/` (only
`project_info.json`) was also created and remains, orphaned, as a record of
the intended-but-never-populated isolated directory.

Arm 1 (F2LLM read-only re-measurement, 63 scored queries at k=7) completed
before the crash, but the script prints its aggregate only after both arms
finish — those numbers never printed and no JSON reached
`benchmark_results/`. No loss of value: arm 1 alone duplicated, at a
different k, what `BASELINE_20260801.md` already measured at k=10.

## Repair

`.venv/Scripts/python.exe tools/batch_index.py --path . --mode force
--exclude-dirs "_archive,tests,MagicMock,audit_reports,benchmark_results,
htmlcov,log,tmp,code-search-extension"` (exclude list transcribed verbatim
from the surviving `project_info.json.user_excluded_dirs`), followed by an
MCP server restart. Result: 195 files / 2,251 chunks (196/2,259
pre-incident, minus the one file removed when the harness itself was
deleted — chunk delta consistent with a single multi-chunk script file, not
a partial or corrupted rebuild). Verified via `get_index_status` and a
`search_code` smoke query.

## Decisions

1. **Delete the harness.** Its core safety claim is provably false; fixing
   it in place would leave a dormant script whose only demonstrated
   behavior, under the stated usage pattern, is destroying the deployed
   index. No golden-dataset or other production dependency referenced it
   (`grep embedder_gemma` post-deletion: only this document and
   `evaluation/raw_mcp_results_hybrid.json`, a historical raw-results
   artifact needing no edit).
2. **No production guardrail.** Deleting the harness removes the only
   caller that could trigger this specific sequence; a code-level guard was
   considered and explicitly declined in favor of documenting the defect
   here.
3. **`embeddinggemma-300m` stays in `MODEL_REGISTRY`**, dropped rather than
   evaluated. This A/B is not scheduled for a retry. If a future need arises
   anyway, the precondition is a harness that either (a) persists the
   model swap via `save_config()`/`_switch_active_model` before reindexing
   so cache invalidation resolves the *intended* directory, or (b) drives
   the isolated reindex through a separate `--project-path` pointed at a
   throwaway storage root, never through the live server's config-caching
   path.
4. **Orphaned storage.** The empty `claude-context-local_9e7f0a98_gemma-300m_768d/`
   directory (created by the harness's pre-reindex storage-dir lookup,
   described above) contains only `project_info.json` and is safe to remove —
   it regenerates automatically if anyone ever switches to that model. No
   functional effect either way; it lives outside the repo
   (`C:\Users\Inter\.claude_code_search\projects\`), not tracked by git.

## Durable lesson

An in-memory-only config mutation (`cfg.embedding.model_name = X` without
`save_config()`) cannot survive any code path that calls
`invalidate_config_caches()`. `handle_index_directory` does. "Unsaved swap
⇒ isolated reindex" is therefore unsound as a safety pattern in this
codebase — it looks isolated because the pre-reindex storage-dir lookup
still reflects the in-memory value, but the reindex itself re-derives config
from whatever was last persisted to disk. Any future harness that swaps
`embedding.model_name` for an isolated-index experiment must either persist
the swap before reindexing or avoid the shared config-cache path entirely.

## Deliverables

- This document.
- `scripts/benchmark/embedder_gemma_vs_bgem3_ab.py` — **deleted**.
- No comparative embedder numbers — the question is open, not closed.
