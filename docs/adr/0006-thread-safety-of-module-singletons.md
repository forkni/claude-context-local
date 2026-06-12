# Thread-safety of module singletons via coarse locks

Status: accepted
Date: 2026-06-11

`ApplicationState` lazy-init and teardown are guarded by a `threading.RLock`;
the `_model_pool_manager` factory singleton is guarded by a separate module-level
`threading.Lock`.  Both use the double-checked locking pattern.

## Context

In HTTP stateless mode the MCP server receives concurrent `call_tool` requests.
The `ApplicationState` singleton holds `searcher`, `index_manager`, and the
embedder pool — all expensive to construct (FAISS load, BM25 load, GPU model
load).  Before this change there was no synchronization:

- Two concurrent `search_code` requests on a cold server could each enter the
  `get_searcher` lazy-init block, constructing two `HybridSearcher` objects.
  The second would overwrite the first; the first's VRAM allocation was leaked.
- A concurrent `switch_project` / `clear_index` teardown could null
  `state.searcher` while another coroutine was mid-search on it.
- `ModelPoolManager` (`mcp_server/model_pool_manager.py`) had its own
  module-level `_model_pool_manager` singleton with the same check-then-act gap;
  two concurrent pool-creation calls doubled VRAM.

The call chain `get_searcher → get_index_manager → get_embedder` is reentrant:
a single thread may hold the outer lock when it calls the inner function.

## Decision

### `ApplicationState` lock

Add `_lock: threading.RLock = field(default_factory=threading.RLock)` to the
`ApplicationState` dataclass (`mcp_server/state.py`).  The `reset()` method does
**not** reassign `_lock` — the same lock object survives project/model switches so
that in-flight threads always hold a stable lock reference.

Every lazy-init site in `mcp_server/search_factory.py` (`get_index_manager`,
`get_searcher`) acquires `state._lock` and re-tests the `is None` / cache-invalid
condition inside the lock (double-checked locking).  Every teardown site
(`switch_project`, `switch_model`, `clear_embedders`, `reset_search_components`,
`reset_searcher`, `reset_for_model_switch`) also acquires `state._lock` so
teardown cannot interleave with an in-progress construction.

### Model-pool factory lock

Add `_pool_lock = threading.Lock()` at module level in
`mcp_server/model_pool_manager.py`.  All sites that construct or reset
`_model_pool_manager` acquire this lock with double-checked locking.

### Why `RLock` on `ApplicationState`

The nested call chain (`get_searcher` calls `get_index_manager` which calls
`get_embedder`) means the same thread acquires the lock three times on a cold
start.  A plain `Lock` would deadlock.  `RLock` permits reentrant acquisition
by the same thread.

The pool lock is a plain `Lock` because `get_model_pool_manager` is a flat
factory: it constructs the singleton directly with no further lock acquisitions
on the same thread.

## Alternatives considered

**Fine-grained per-field locks** (one lock per `state.searcher`, per
`state.index_manager`, etc.) — rejected.  The nested construction chain means
holding `searcher_lock` while acquiring `index_manager_lock` while acquiring
`embedder_lock`.  Any inconsistent acquisition order across code paths risks
deadlock.  The coarse `RLock` is simpler and the critical sections are short
(< 1 ms except during actual construction, which is rare).

**`asyncio.Lock` for everything** — rejected.  `get_searcher` and the teardown
functions are called from both the async event loop (via `asyncio.to_thread`
boundaries) and from `threading.Thread` workers.  `asyncio.Lock` is bound to a
single event loop and cannot be acquired from a thread.  `threading.RLock` works
in both contexts.

## Consequences

- Concurrent `call_tool` requests no longer risk double VRAM allocation or a
  lost searcher reference.
- A teardown (`switch_project`, `clear_index`) cannot null `state.searcher`
  while another coroutine is using it.
- The `_lock` field survives `reset()` — tests that call `reset_state()` for
  isolation are unaffected because `_lock` carries no per-test state.
- Lock contention is negligible: construction happens once at startup and
  rarely thereafter; teardown is user-driven.
- Related: `asyncio.to_thread` offloads for blocking handlers (ADR documented
  inline in `mcp_server/tools/search_orchestrator.py` comments, 2026-06-11).
