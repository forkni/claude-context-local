# IndexWriteStage owns index-adds and the injection gate for both passes

Status: accepted
Date: 2026-08-20

## Context

Commit `17c000c` extracted `IndexWriteStage` as the home of write behaviour shared by the full
(`IncrementalIndexer._full_index` → `IndexWriteStage.run`) and incremental
(`_add_new_chunks`/`incremental_index`) passes, and `_build_write_pipeline` already bound both
passes to the *same* stage instance. But the extraction left three residues that kept the seam
half-real (an architecture review flagged them as Insider Trading / Shotgun Surgery / Divergent
Change):

1. **`add_embeddings` had two owners.** The full path added embeddings inside `run()`; the
   incremental path called `self.indexer.add_embeddings(...)` directly in `_add_new_chunks`, with
   its own hand-copied logging idiom. Same indexer object, two call sites to keep in sync.
2. **Cross-class private call.** `incremental_index` reached into
   `self._index_write_stage._inject_call_edges(project_path)` — a private of another class — and
   read the ADR-0044 gate (`get_search_config().call_graph.inject_on_incremental`) in the
   *caller*. The decision and the mechanism lived on opposite sides of the seam.
3. **The `SummaryStage` calling idiom was hand-copied twice.** The same 8-line
   generate-summaries-and-extend-chunks block (config gate → generate → `chunks.extend` → log)
   appeared in `_full_index` and `_add_new_chunks`, differing only in log prefix and noun.

A fourth suspect — graph-node pruning in `_remove_old_chunks` — was examined and deliberately
**left in place**: the full path clears the index wholesale (`clear_index()`), so pruning has no
full-path counterpart. Moving it would fail the deletion test and dilute the stage's
shared-behaviour identity.

## Decision

Finish the unification: **`IndexWriteStage` is the single owner of adding embeddings to the index
and of the incremental injection gate; `SummaryStage` is the single owner of its own calling
idiom.** Landed as three refactor commits plus this ratchet:

- `IndexWriteStage.add_to_index(embedding_results, *, log_prefix="") -> int` — the one
  `add_embeddings` call site in the pipeline. `run()` and `_add_new_chunks` both route through
  it. The empty-input warning is full-path semantics; the incremental call site keeps its
  `if all_embedding_results:` guard because an incremental pass with only removals legitimately
  adds nothing.
- `IndexWriteStage.inject_call_edges(project_path)` — pure rename of `_inject_call_edges`
  (public now; the full path calls it unconditionally, gated only by `if project_path:`).
- `IndexWriteStage.inject_call_edges_if_enabled(project_path)` — owns the ADR-0044
  `inject_on_incremental` config read. Gate off (the default) does **zero injection work** and
  returns an all-zero `InjectionStats()`; gate on delegates to `inject_call_edges`. Two named
  methods, not a boolean flag parameter — the caller states intent, the stage owns policy.
- `SummaryStage.generate_and_extend(chunks, *, log_prefix, appended_noun) -> int` — the copied
  idiom, including the `enable_file_summaries` config gate. Home is `SummaryStage` because it
  needs none of `IndexWriteStage`'s collaborators.

ADR-0044 is fully respected: the default stays `False`, the zero-work short-circuit is preserved
byte-for-byte, and the full path remains ungated. Only *where the gate is read* moved — from the
caller to behind the seam.

## Consequences

- `incremental_indexer.py` no longer reads `inject_on_incremental`, calls `add_embeddings`, or
  touches any `IndexWriteStage` private. Its passes describe *what* happens; the stages own *how*.
- Config-liveness `spec(reader=...)` repointed: `enable_file_summaries` →
  `search/summary_stage.py`, `inject_on_incremental` → `search/index_write_stage.py`.
- Rename blast radius repaired in the same commit: live goldens
  (`golden_dataset_expanded.json` Q131, `caller_golden.json`, `callee_golden.json`),
  `profile_full_index.py`'s attribute-name monkey-patch, `merge_hard_queries.py`,
  `docs/CALL_GRAPH_TUNING.md`, and ADR-0044's prose pointer. Archival evaluation snapshots and
  `VERSION_HISTORY.md` keep the old name (historical records are never rewritten).
- Name-shadow note: inside `index_write_stage.py`, the bare call `inject_call_edges(...)` in the
  method body resolves to the module-level function imported from `search.call_edge_injection`,
  not to the same-named method — documented in the method docstring.
- Test locality: gate on/off correctness lives with the owner
  (`test_index_write_stage.py::TestInjectCallEdgesIfEnabled`); the indexer suite keeps a single
  delegation test (`TestIncrementalCallEdgeInjection`).

## Verification

- Ratchet: `tests/unit/search/test_index_sync_ownership.py::TestIndexWriteSeamOwnership` —
  (a) `.add_embeddings(` call sites in the production tree only in `index_write_stage.py`
  (sole exception: HybridSearcher's internal `self.dense_index` delegation), (b) the
  `inject_on_incremental` attribute read only in `index_write_stage.py`, (c) the pre-rename
  `_inject_call_edges` symbol absent from production code.
- Behaviour: full `tests/unit/` green at each commit (6147 passed / 1 skipped at the rename
  commit); primary oracle `tests/integration/test_call_edge_injection_integration.py` ran
  against real pyan3 resolvers — 2 passed, not skipped — plus
  `tests/integration/test_auto_reindex_fixes.py` (9 passed total).
- Pure refactor: no MCP wire-surface change, no benchmark canon re-pin needed.
