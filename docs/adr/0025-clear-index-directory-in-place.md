# Clear and resync index objects in place instead of replacing them

Status: accepted
Date: 2026-08-03

## Context

Clearing or resyncing an index used to mean *replacing* the index objects that hold it, and six
modules each cached their own reference to one of `bm25_index`, `dense_index`/`_metadata_store`,
or `_metadata_cache`. Every swap therefore had to be followed by a hand-written repair list:
`HybridSearcher.clear_index` was 65 lines of repair, `IndexSynchronizer.clear_index` 83, and
`CodeIndexManager`'s own close/recreate pair inside `clear_index` and `close()` another. Three
teardowns, ~240 lines, each re-deriving the same close-gc-probe dance.

The cost is on the record, not speculative. Commit `db4c181` shipped fixes for two pre-existing
bugs in the clear/force-full-reindex path, neither with test coverage — exactly this shape. And
the repair list was still incomplete at the time this was found: `SearchExecutor` caches its own
`bm25_index` (`search_executor.py:55`) and searches it directly (`:354`), but nothing updated that
reference after `IndexSynchronizer.resync_bm25_from_dense` swapped in a freshly constructed
`BM25Index`. Since resync only fires once BM25 has drifted more than 10% from dense
(`DESYNC_THRESHOLD`), the BM25 leg then served stale results for the rest of the process — a live
retrieval-quality bug, on both resync entry points (`IncrementalIndexer.incremental_index` and
`IndexWriteStage.run`), caused by the swap-and-repair shape itself rather than by any one missed
call site.

Separately, `CodeIndexManager.close()` nulled `_metadata_store` while the `metadata_store`
property was annotated `-> MetadataStore` and just returned the field — so any metadata access
after `close()` raised `'NoneType' object has no attribute ...`, the same failure class the
`clear_index` repair list existed to prevent, reachable through a different door. Two
`# pyrefly: ignore [bad-assignment]` markers existed only to silence that type lie.

## Decision

> **Index object identity is stable for the lifetime of a `HybridSearcher`.**

`bm25_index`, `dense_index` (`CodeIndexManager`), and `dense_index._metadata_store`
(`MetadataStore`) are constructed once and never reassigned. Clearing, resyncing, or closing an
index now mutates that same object back to an empty/reset state in place, instead of constructing
a replacement and writing the new reference back onto every collaborator that cached the old one.

This was landed as four ordered commits, each its own hat:

1. **Bug fix** — `FaissVectorIndex.clear()` closed and unlinked `_mmap_path` without closing or
   nulling `_mmap_storage`, so a cleared index backed by an mmap'd file (≥`MMAP_THRESHOLD`
   vectors) could serve reconstructed vectors from a deleted file. Fixed first, independently of
   the identity refactor, because commit 2 below makes stable identity the rule everywhere and
   this bug had to stop being reachable before that.
2. **Refactoring, no behaviour change** — `BM25Index.clear()` and `MetadataStore.reset()` added as
   the in-place primitives; `CodeIndexManager.preflight_clear()`, `CodeIndexManager.clear_index`,
   `IndexSynchronizer.clear_index`, and `HybridSearcher.clear_index` rewritten to call them in
   place of construct-and-swap. Zero net behaviour change — same fields end up in the same state,
   just without the write-back step.
3. **Behaviour change** — `IndexSynchronizer.resync_bm25_from_dense` rebuilds the existing
   `bm25_index` in place (`clear()` then `index_documents()`) instead of constructing a fresh one.
   The stale-`search_executor.bm25_index` bug closes by construction: since nothing is ever
   reassigned, every collaborator that cached the object at construction time sees the resynced
   corpus without any write-back existing to forget.
4. **Behaviour change** — `CodeIndexManager.close()` collapses to a single
   `self._metadata_store.close()`. Handle release is unchanged (`MetadataStore.close` still does
   `commit` → `_db.close()` → `_db = None`); the object itself stays live and lazily reopens via
   `_ensure_open` on the next access. `HybridSearcher.close_metadata_connections`, which used to
   reach past the public property into `dense_index._metadata_store.close()` directly, now calls
   `dense_index.close()`.

## Consequences

- **The repair lists stop existing rather than getting longer.** The stale-reference class of bug
  — a swap somewhere not matched by a write-back somewhere else — becomes unrepresentable, because
  there is no longer a second reference to keep in sync. This is what closes the
  `search_executor.bm25_index` bug in commit 3.
- **The risk moves, it does not disappear.** The design trades "did you update every cached
  reference?" — distributed across five files, demonstrably never gotten right in practice — for
  "did you reset every field?" — local to one class, and directly unit-testable. The mitigation is
  a field-completeness test per store: `vars(fresh_instance).keys() == vars(cleared_instance).keys()`
  plus a per-field equality check (skipping non-comparable derived objects like loggers and
  preprocessors, which have no `__eq__`). A future field added to a store's `__init__` but
  forgotten in `clear()`/`reset()` fails that test immediately instead of surfacing as a stale-data
  bug later.
- **`MetadataStore.reset()` releases a handle, it does not delete data.** `reset()` closes the
  SQLite connection (releasing the Windows file lock) and replaces `_symbol_cache` with a fresh
  `SymbolHashCache()`, but never deletes `metadata.db` itself. True emptying is still a two-party
  contract: `CodeIndexManager.preflight_clear()` calls `reset()` then `probe_metadata_deletable()`,
  which is the caller that actually removes the file. This ADR does not change that contract, only
  removes the object-replacement step that used to follow it.
- **`FaissVectorIndex.clear()` now closes its mmap storage.** A cleared, then-refilled index backed
  by an mmap file can no longer serve reconstructed vectors from a deleted backing file.

## Verification

Full `tests/unit/` gate green after every step (5624 passed, 1 skipped at landing, up from 5619 —
the delta is new field-completeness, identity, and close/resync-outcome tests; no test count
regression). Manual check for commit 4: `cleanup_resources` followed by a live, auto-triggered
incremental reindex through `search_code` completed and returned correct, up-to-date results with
no `metadata.db` lock error — confirming the handle-release contract survived the refactor outside
the unit-test harness as well.

## Out of scope

- Candidate-3 litter-pickup (`ego_graph_retriever.py` Hide Delegate, `multi_hop_searcher.py`
  Remove Middle Man) — dropped to protect this refactor's appetite once scope grew from clear-only
  to clear + resync + `close()`; ~20 lines, pickable separately.
- Any change to index format, `INDEX_VERSION`, fusion weights, or the golden datasets.
- A DI container or service locator — declined by ADR-0005. The invariant here is enforced by
  removing swaps, not by adding indirection.
- Re-pinning the benchmark canon. This refactor edits indexed source under `search/`, which shifts
  the corpus via auto-reindex independently of retrieval quality; canon re-pin follows as a
  separate, standard post-landing step per ADR-0024's precedent, not part of this decision.

## Amendment (2026-08-28): `close()` was necessary but not sufficient

Decision item 4 above collapsed `CodeIndexManager.close()` to `self._metadata_store.close()` and
stated the mmap-backed FAISS handle was out of scope for that commit — correct as written, but it
left `close()`'s docstring claiming "Does not touch the FAISS index" as a standing fact rather
than a scope note, and nothing else in the class ever released that handle deterministically.

This surfaced as a real production failure: every force reindex of a project at or above
`MMAP_THRESHOLD` maps `code_vectors.mmap` twice in one process — a write-only "searcher #1"
(`get_searcher(..., load_existing=False)`, whose `load_existing` flag does not gate
`CodeIndexManager.__init__`'s unconditional `self._faiss_index.load()`), then "searcher #2" built
moments later for the actual reindex. `_cleanup_previous_resources()` calls
`close()`/`shutdown()` on searcher #1 between the two, which released its metadata connection but
left its FAISS mmap mapping live — held open only by GC-eligible stack references, not by
anything `close()` touched. Searcher #2's `clear_index()` then failed unlinking the shared file
out from under searcher #1's still-live mapping (`PermissionError [WinError 32]` on Windows;
invisible on POSIX, which unlinks mapped files freely). The self-handle close this ADR added
(item 1) was necessary — a cleared index no longer serves reconstructed vectors from a deleted
file — but it was never going to fix this failure, because the blocking handle always belonged
to a *different* `CodeIndexManager` instance, not the one calling `clear()`.

Fix: `FaissVectorIndex` gained a non-destructive `close()` (release the mmap handle, touch no
files — distinct from `clear()`, which deletes); `CodeIndexManager.close()` now calls it, and
`__exit__` delegates to `close()` instead of inlining its own metadata-only teardown (it
previously would have silently skipped the new mmap release). `__del__` was deliberately left
inlined rather than routed through `close()` — reaching across to another object during
interpreter teardown is the failure mode `__del__` is worst at, and
`MmapVectorStorage.__del__` remains the existing GC-time backstop for this same handle.
`FaissVectorIndex.clear()` and `save()` were also fixed to close their own mapping before
unlinking or truncating-and-rewriting the backing file, rather than only on the already-fixed
`clear()` path from item 1.

The decision itself — object identity stays stable, mutate in place — is unaffected and remains
correct. What changed is that "release a handle" needed its own explicit method
(`FaissVectorIndex.close()`) wired into every teardown path, the same discipline item 4 already
established for the metadata connection; it had just stopped short of the FAISS side once the
mmap complexity kicked in.

## Amendment (2026-08-31): the two-party emptying contract had no enforcement

The Consequences section above states the contract plainly: `MetadataStore.reset()` releases a
handle, it does not delete data; true emptying depends on `probe_metadata_deletable()` actually
unlinking the renamed file afterwards. That contract had a hole neither half of this ADR closed:
`probe_metadata_deletable()` short-circuited whenever a `metadata.db.deleting` sibling already
existed, returning that stale path **without renaming the live `metadata.db`**. `clear_index()`
then unlinked only the stale sibling — the real DB was never touched, and the next
`_ensure_open()` silently reopened it with its previous generation's rows intact.

This surfaced in production on `voro-engine`'s force-full reindex: a stale `.deleting` sibling
(stranded by an earlier aborted clear — this repo's recurring `WinError 32` mmap-handle failure,
same failure class as the amendment above, is one way to strand it) shadowed the live DB, and 148
rows from a previous index generation (pre-rename `cito_*` symbols, in a project since renamed to
`voro_*`) survived a reported-successful "full" clear. The rebuilt FAISS/chunk_ids side was
completely correct; only the leftover metadata rows failed the post-index consistency check,
minutes after the real work had already succeeded and saved.

Fix, in the same spirit as item 1 (self-handle close) above: a live `metadata.db` now always wins
over stale `.deleting` debris — the sibling is discarded first if both exist, then the live DB is
renamed as before. `MetadataStore` gained an actual `clear()` (delegates to `SqliteDict.clear()`),
called before `reset()` in `preflight_clear()`, so row-emptiness stops depending on the file-unlink
step succeeding at all. `clear_index()` now asserts the post-condition — zero remaining metadata
rows — and raises immediately, attributably, if it doesn't, rather than letting a stale generation
surface as an unexplained mismatch two minutes later. `IncrementalIndexer._full_index` also
self-heals: if a full index's *only* consistency issue is check 4's metadata surplus (checks 1-3
having already proven the FAISS/chunk_ids side intact), the orphan rows are pruned and the run
succeeds — full-index-only, since a full index makes metadata == chunk_ids by construction and any
surplus is provably stale debris, unlike the incremental path where surplus is a real signal
recovery already owns.

The decision itself is unaffected. What changed is the same lesson as the amendment above,
applied to the metadata side instead of the FAISS side: a documented two-party contract needs an
enforced post-condition, not just a comment describing the intended handoff.

## Amendment (2026-09-25): the 08-31 fix's own destructive pre-probe clear turned a cross-process race into permanent data loss (H1)

The 2026-08-31 amendment above added `MetadataStore.clear()` — a committed `DELETE FROM` — as a
step inside `preflight_clear()`, running *before* `reset()` and the rename probe, specifically so
row-emptiness would not depend on the file-unlink step succeeding. That traded one bug for a
worse one: the probe's whole contract is "a failed probe is a clean no-op", but with the clear
moved ahead of it, a failed probe left every row already deleted and committed regardless.

This is exactly what happened on `twozero-dev`. A CLI force-full reindex started at 10:23:43 and
held `metadata.db` open for the run. `start_mcp_server.cmd` POSTs `/cleanup` to the running MCP
server first, but that only releases the server's own resources — it does not suspend the
server's auto-reindex. At 10:27:50 a concurrent `search_code` call on the same project triggered
exactly that: `[AUTO_REINDEX]` saw a stale snapshot, called `IndexSynchronizer.clear_index` →
`preflight_clear()` → `MetadataStore.clear()` (committed, all 31,332 rows gone) → `reset()` →
`probe_metadata_deletable()`, which then failed the rename with `WinError 32` because the CLI
process still held the file open. The server aborted the clear as designed — but the rows were
already gone. The CLI process never observed any of this; it went on to finish chunking and
embedding, saved FAISS/BM25/graph (31,332 vectors each) on top of the now-empty metadata store,
and only caught the damage at its own post-index consistency check five minutes later
(`Metadata database size (0) != chunk_ids length (31332)`). Three alternative hypotheses (a TD
network file-set change, a silently swallowed `add_embeddings` commit, and a stale read against a
different store) were each falsified against the timestamped log and `stats.json` evidence before
settling on this one.

Two independent defects had to combine for this failure, and both needed fixing:

1. **Ordering.** `preflight_clear()` deleted before it probed. Fixed by dropping the pre-probe
   `MetadataStore.clear()` entirely and relying on the rename (the probe itself) plus
   `clear_index()`'s existing unlink of the renamed `.deleting` file to do the actual deletion —
   the same "live DB wins over stale `.deleting` debris" fix and zero-rows post-condition from
   the 08-31 amendment already guarantee an empty store once the probe *succeeds*, so the
   destructive pre-probe clear was never load-bearing for correctness, only for harm on the
   failure path. See `CodeIndexManager.preflight_clear()`'s docstring (`search/indexer.py:858`)
   for the in-code version of this rationale. This is a Windows-only fix: on POSIX, a rename over
   an open file handle succeeds silently regardless of who else holds it, so the reorder alone
   does not close the race there.
2. **No inter-process mutual exclusion.** The only lock guarding an index storage directory was
   the MCP server's in-process `_AsyncRWLock` (`mcp_server/state.py::get_reindex_rwlock`) —
   nothing stopped a CLI indexer process and the server's own auto-reindex from writing the same
   `metadata.db`/FAISS/BM25 files at the same time in the first place. Fixed with a new
   `search/index_write_lock.py`: `index_write_lock(storage_dir)` wraps a `filelock.FileLock`
   (OS-level, `timeout=0`, auto-released if the holder dies) around
   `IncrementalIndexer.incremental_index()` — the single chokepoint shared by CLI force-full
   reindex, MCP `index_directory`, and auto-reindex — so a second writer fails fast with
   `IndexWriteLockHeld` instead of racing the first at all, on any platform. A cheap
   `is_index_write_locked()` pre-gate was also added to `SearchOrchestrator._maybe_reindex`
   (`mcp_server/tools/search_orchestrator.py`) so a stale-index search skips building a
   `HybridSearcher` — which maps `code_vectors.mmap` and could itself contend with the other
   process's save — once the lock is already known to be held, rather than paying that cost only
   to fail at `incremental_index`'s own lock acquisition moments later.

The decision itself — object identity stays stable, mutate in place — remains unaffected. What
changed is the same lesson as both amendments above, extended one level further: a two-party
"probe, then destroy" contract is not actually two-party if the destructive half can run before
the probe succeeds, and a single-process contract is not enough once the same storage directory
has more than one process capable of writing to it. Every prior amendment to this ADR was a
single-process race (a stray handle from an earlier `CodeIndexManager` instance in the *same*
process); this is the first that required real cross-process exclusion.

### Follow-up (deferred, not part of this fix)

- Admin paths that bypass `incremental_index` — `handle_clear_index`, `handle_delete_project`,
  `tools/safe_clear_index.py` — do not yet take the write lock. Handed to
  `/improve-codebase-architecture`.
- `IncrementalIndexer._full_index` saves the snapshot before validating and keeps it on
  validation failure, so a failed full index can still look "current" to `needs_reindex` if there
  happen to be no pending changes. Invalidating or rolling back the snapshot on validation failure
  is deferred to the same follow-up.
- The CLI's `/cleanup` call only releases the server's resources; it does not ask the server to
  pause auto-reindex for the target project. The write lock now makes that unnecessary for
  correctness, but a clearer skip message earlier in the CLI run (rather than the server silently
  losing the race) would still be a usability improvement.
