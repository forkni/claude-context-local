# Reader-writer lock for auto-reindex vs. in-flight searches

Status: accepted (amended 2026-07-27 — see Amendment below)
Date: 2026-07-12

Per-project async reader-writer lock on the event loop: searches hold the
shared read lock across searcher acquisition and execution
(`SearchOrchestrator._execute` Blocks B-D); a reindex (auto-triggered by a
stale search, or a manual `index_directory` call) holds the exclusive write
lock. Combined with deleting the now-defunct single-model embedder teardown
that previously ran at the start of every auto-reindex.

**2026-07-27 amendment:** the read lock's scope widened to also cover result
assembly (former Blocks E-I), not just Blocks B-D — see Amendment section.
`_execute` no longer exists; it split into `_maybe_reindex` (Block A) and
`_search` (Blocks B-D).

## Context

`_archive/ERROR_LOG.md` captured two errors from a concurrent `search_code`
session: `RuntimeError: Embedder has been cleaned up` and a Rust tokenizer
panic (`Already borrowed`). Both traced back to the same root cause: a
search that found the index stale triggered a **full auto-reindex**, whose
first act (`incremental_indexer.py`, `auto_reindex_if_needed`) was a
destructive global teardown — `state.clear_embedders()`,
`reset_pool_manager()`, `embedder.cleanup()` — while sibling searches were
still running on the shared embedder and rerankers. Severity: "world (b)",
no hard crash — `@error_handler` converts the exceptions to `status=error`
responses, and code paths that catch the failure (ego-graph scoring) degrade
to a fixed-decay fallback. The real harm was silent quality degradation:
searches losing reranking or graph scoring while reporting `status=ok`.

The teardown's stated purpose was avoiding VRAM exhaustion when switching
between multiple loaded embedding models. That regime has been removed —
`state.embedders` is single-entry by construction (`set_embedder` is only
ever called with the key `"default"`) — so the teardown now only ever
destroys and reloads the *same* model, buying nothing.

Beyond the teardown, the existing per-project reindex lock
(`search_orchestrator.py`, then a plain `asyncio.Lock` from
`get_reindex_lock`) only wrapped the reindex-check step (Block A). Searcher
acquisition (Block B) and search execution (Block D) ran outside it, so even
with the teardown removed, a reindex could still rewrite index files while a
concurrent search was reading them.

## Decision

**Part 1 — reranker inference mutex.** Give each of the three rerankers
(`JinaRerankerV3`, `NeuralReranker`, `GenerativeReranker` in
`search/neural_reranker.py`) a per-instance `threading.Lock` (`_infer_lock`),
mirroring the pattern `CodeEmbedder._lifecycle_lock` already uses to
serialize inference. The lazily-loaded model is resolved via its property
*before* the lock is acquired, so a one-time load stays under the reranker's
own `_load_lock` and lock ordering stays one-directional
(`_infer_lock` → `_load_lock`, never reversed).

**Part 2a — delete the auto-reindex teardown.** Remove the
`clear_embedders` / `reset_pool_manager` / `gc.collect` /
`torch.cuda.empty_cache` / `embedder.cleanup()` block from
`auto_reindex_if_needed`. Reindexing now reuses the live `self.embedder`
directly. `state.clear_embedders`, `reset_pool_manager`, and
`reset_for_model_switch` are untouched — they still back
`cleanup_resources` (user-invoked memory release) and
`switch_embedding_model` (the model genuinely changes).

**Part 2b — async reader-writer lock.** Add `_AsyncRWLock`
(`mcp_server/state.py`) — a small writer-preference RW-lock built on
`asyncio.Condition`, exposed per-project via
`ApplicationState.get_reindex_rwlock(project_path)` (replacing
`get_reindex_lock`). `SearchOrchestrator._execute` is restructured:

1. A cheap, lock-free staleness pre-check (`_is_index_stale`, extracted from
   the old `_check_auto_reindex`) reads only the merkle snapshot mtime and a
   quick change-detector diff — no lock, no embedder/searcher construction.
2. Only if genuinely stale does the request take the **write** lock and run
   the heavy reindex (`_check_auto_reindex`, unchanged apart from the
   extraction). `_check_auto_reindex`'s internal `needs_reindex()` call
   re-verifies staleness under the lock, so two requests that both saw
   "stale" during the lock-free pre-check don't double-reindex.
3. Searcher acquisition and search execution (Blocks B-D) run under the
   **read** lock, so they can never straddle a concurrent index-file
   rewrite.

Writer preference: once a writer is waiting, new readers queue behind it, so
a steady stream of searches cannot starve out a pending reindex indefinitely.
The write lock still waits for in-flight readers (already-running searches)
to drain before proceeding.

`index_handlers.py`'s manual `handle_index_directory` path also switched
from the old `get_reindex_lock` to `get_reindex_rwlock(...).write()`,
preserving its pre-existing intentional serialization against
`search_code`'s auto-reindex path (both are index-file writers keyed to the
same project).

## Alternatives considered

**Widen the existing exclusive lock over Blocks B-D** (make every search
take a full mutual-exclusion lock, not just reindex) — rejected. Simple, but
serializes *all* concurrent searches even when no reindex is happening,
eliminating read concurrency for no benefit.

**A `threading` RW-lock inside the `asyncio.to_thread` workers** — rejected.
This would add a second locking layer beneath the event-loop-level reindex
lock, inconsistent with how the rest of the server (the existing
`get_reindex_lock` / `get_mutation_lock` asyncio locks, ADR-0006) serializes
workflows on the loop rather than inside worker threads.

**Make searches resilient to a torn-down embedder via fresh-fetch/retry
only** — rejected. Doesn't address half-rewritten index files being read
mid-reindex, which the teardown removal alone does not fix.

## Consequences

- This partially revisits ADR-0006's "one coarse lock, no finer-grained
  locks" stance, but only for this one seam (reindex vs. search
  workflows). `state._lock` (`threading.RLock`) is unchanged and still
  guards fine-grained field swaps within `ApplicationState`; the new
  `_AsyncRWLock` operates one layer up, at the workflow level, and only on
  the event loop.
- A reindex now waits for in-flight searches to drain before it can start;
  a long-running search (e.g. ~200s) delays a pending reindex. Acceptable —
  reindex is rare and correctness (not staleness) is the priority once
  triggered.
- Concurrent searches now serialize briefly at the rerank step (Part 1).
  Acceptable — a single GPU already serializes CUDA kernels, and rerank is a
  small slice of total search time.
- `_AsyncRWLock` instances are event-loop-bound (`asyncio.Condition`) and
  must only be constructed/acquired from coroutines, never from a
  `threading.Thread` worker — mirrors the existing constraint on
  `get_reindex_lock` / `get_mutation_lock`.

## Amendment (2026-07-27): widen the read lock through `_assemble`

**Context.** A separate latency pass added a version-keyed centrality memo
to `CodeGraphStorage` (own ADR) so `_assemble`'s graph-scoring step —
Block F (`CentralityRanker`) and Block G (`SubgraphExtractor`) — now reads
`index_manager.graph_storage` against a long-lived cache instead of a
throwaway per-query copy. Tracing that path surfaced a pre-existing gap
that the memo makes more consequential: `_assemble` ran *outside* the read
lock this ADR established. `_assemble` is synchronous, so it can't be
interleaved with other coroutines on the event loop, but a concurrent reindex runs its heavy
work via `asyncio.to_thread` — a real OS thread — so it mutates
`graph_storage.graph` (`add_node`, `add_call_edge`, `remove_file_nodes`,
etc.) in true parallel with a search's Block F/G reads. This is exactly the
failure class this ADR exists to prevent: a request that reports
`status=ok` while silently scoring against a graph that is being rewritten
underneath it.

**Decision.** Extend the read lock to span `_search` (Blocks B-D) *and*
`_assemble` (Blocks E-I). `_AsyncRWLock` is non-reentrant (a reader blocks
while a writer is waiting; a writer blocks while readers hold the lock), so
simply moving the `async with ... .read():` block to wrap the old
`_execute` call in `run()` would deadlock against Block A's own write lock.
Block A was split out into its own method, `_maybe_reindex`, so it can run
*before* the read lock opens and fully release before it does:

```python
early = await self._maybe_reindex(plan)  # Block A — own write-lock scope
if isinstance(early, dict):
    return early
reindexed_flag, lock_project = early
async with get_state().get_reindex_rwlock(lock_project).read():
    outcome = await self._search(plan, reindexed_flag)  # Blocks B-D
    if isinstance(outcome, dict):
        return outcome
    return self._assemble(plan, outcome)  # now inside the lock
```

`_execute` (Blocks A-D, self-managing its own read lock around B-D) no
longer exists. `_maybe_reindex` covers Block A only; `_search` covers
Blocks B-D and expects the caller to already hold the read lock — `run()`
is the only caller.

**Consequences.**

- A pending reindex now waits for a search's assembly step (formatting,
  centrality scoring, subgraph extraction, source-order/budget truncation),
  not just its raw search call, before the write lock can proceed. Measured
  as a low tens-of-ms addition to worst-case reindex latency — assembly is
  CPU-bound formatting/graph-read work, not another model inference pass.
  Searches are unaffected: read-side concurrency is unchanged.
- No new call sites acquire `get_reindex_rwlock` directly; the widening is
  entirely inside `SearchOrchestrator.run()`.
- Covered by `tests/unit/mcp_server/test_search_orchestrator.py::TestExecuteConcurrencyIntegration`,
  retargeted from `_execute()` to `run()` so the exercised lock span matches
  production (previously it only proved Blocks B-D were race-free; it now
  proves Blocks B-I are).
