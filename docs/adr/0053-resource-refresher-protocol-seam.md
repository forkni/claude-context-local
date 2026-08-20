# Lift the MCP process-resource lifecycle out of `IncrementalIndexer` via a protocol seam

Status: accepted
Date: 2026-08-20

## Context

[ADR-0051](0051-delete-graph-scoring-stage-upward-import.md) closed one `search/ -> mcp_server`
upward import and named the remaining seven "out of scope for this ADR" — five of them one
class: `IncrementalIndexer._release_and_verify_resources`
(`search/incremental_indexer.py:564-674`), which reached upward into
`mcp_server.resource_manager`, `mcp_server.services`, `mcp_server.model_pool_manager`, and
`mcp_server.search_factory` to release GPU memory and reacquire a fresh embedder/searcher
around a full index pass. This closes that deferral.

The method also discarded its own constructor injection. `mcp_server/tools/index_handlers.py`
passes `indexer=`, `embedder=`, `chunker=` into `IncrementalIndexer.__init__`; the method then
overwrote two of them — `self.embedder = get_embedder()` and `self.indexer =
get_searcher(project_path, load_existing=False)`, the latter needing a `# pyrefly: ignore
[bad-assignment]` because the reacquired object's type didn't match the constructor parameter's.
A caller could not supply a test double and expect it to survive a full pass; production code
carried a branch whose own log message read `"(test mock)"` — the shape of the test doubles had
leaked into production control flow. Sixteen `patch.object(IncrementalIndexer,
"_release_and_verify_resources")` sites across `tests/unit/search/test_incremental_indexer.py`
existed only to neutralize this before any full-index assertion could run.

`search/` could not be imported without `mcp_server/` on the path, unlike the retrieval path,
which ADR-0018/0030/0045/0047/0048 had already freed of the same class of coupling.

### Declined: hoist the release to the MCP handler

The most direct-looking fix — call the release once in `mcp_server/tools/index_handlers.py`
before constructing `IncrementalIndexer`, instead of inside the class — was checked against the
live call graph and ruled out on three independent grounds:

- `_attempt_recovery` (`incremental_indexer.py:474-543`) starts a full pass **mid-incremental**,
  a runtime recovery decision reached from inside `incremental_index` itself. No MCP handler is
  on the call stack at that point to hoist the release into.
- `mcp_server/tools/search_handlers.py`'s own `IncrementalIndexer` construction (for
  auto-reindex-on-search) would have to duplicate the `has_snapshot` decision that determines
  whether a pass will be full or incremental, just to know whether to call the release —
  Shotgun Surgery plus a TOCTOU window between the duplicated check and the real one.
- The release currently runs inside the `traced_block("index.full", ...)` span
  (`incremental_indexer.py:261-264`). Hoisting it outside that span would silently re-attribute
  its cost in tracing output — a behaviour change disguised as a relocation.

`find_connections` on the method (2,574-chunk index, 2026-08-20) confirmed this structurally:
one `direct_caller` (`_full_index`, `exact`) but two `indirect_callers` — `incremental_index`
and `_attempt_recovery` — meaning a full pass genuinely has two in-class entry points, one of
them mid-pass. A single external call site does not exist to hoist into.

## Decision

Move the method's body up into `mcp_server/`, and leave behind a **seam** on
`IncrementalIndexer` that the MCP layer fills in:

```python
@runtime_checkable
class ResourceRefresher(Protocol):
    def refresh_before_full_index(
        self, project_path: str, embedder: CodeEmbedder, indexer: Any
    ) -> tuple[CodeEmbedder, Any]: ...

    def invalidate_searcher_cache(self) -> None: ...


class NullResourceRefresher:
    """Keeps the caller's own embedder/indexer; invalidates nothing."""
```

declared in the new `search/resource_refresh.py`, sibling to `search/index_write_stage.py` and
`search/summary_stage.py`. `McpResourceRefresher` in `mcp_server/resource_manager.py` — the
module [ADR-0005](0005-no-di-container-module-singleton-state.md) designates for resource
lifecycle — is the one production adapter, satisfying the protocol **structurally**: no base
class, no import of `search/resource_refresh.py`. No arrow crosses upward. The precedent for a
protocol declared in the lower layer and implemented above it is
`chunking/relationships/call_edge_resolver.py`'s `@runtime_checkable CallEdgeResolver`, whose
consuming seam depends only on the protocol and never imports the implementations above it.

`IncrementalIndexer.__init__` gained one keyword-only parameter,
`resource_refresher: ResourceRefresher | None = None`, defaulting to `NullResourceRefresher()`.
`_full_index` calls `self._resource_refresher.refresh_before_full_index(...)` directly and
rebinds `self.embedder`/`self.indexer` from the returned pair, with `_build_write_pipeline()` on
the very next line — preserving the invariant that `IndexWriteStage` must be rebuilt against the
post-refresh objects, not the released ones.

### Why one typed constructor parameter is not the DI container ADR-0005 declined

ADR-0005 declined a DI *container* and a `ServiceLocator` — a general mechanism for resolving
arbitrary dependencies by type at construction time, with the indirection and runtime-resolution
cost that implies. This is the opposite: one named, typed, keyword-only parameter with a
concrete default, on one class, resolved at the call site by the author, not by a resolver.
`IncrementalIndexer` already took `indexer=`, `embedder=`, `chunker=` this way before this
change; `resource_refresher=` is the fourth constructor-injected collaborator, not a new
pattern.

### Why a protocol and not two independent `Callable` parameters

The local idiom, set three weeks earlier by [ADR-0052](0052-index-write-stage-owns-add-and-inject-for-incremental-passes.md),
is bare callables (`IndexWriteStage.__init__` takes `build_metadata_fn` and `clear_gpu_fn`). It
does not fit here because the two members are not independent: `refresh_before_full_index`
acquires a `load_existing=False` searcher and commits it to `state.searcher`
(`mcp_server/search_factory.py`), and `invalidate_searcher_cache` is its compensating inverse on
the error path — exactly what the `#reindex-log-audit-2026-07-30` comment documents. Two
independent parameters could be wired inconsistently (a real refresher with a forgotten
invalidator leaves a write-only searcher live in process state after a failed reindex) with
nothing to catch it. One object makes the pair unwireable-apart.

### Declined: split into `release()` / `reacquire()`

Neither half has an independent call site — they are ~85 lines apart in one method with a
verification block between them — and a two-call interface would hand the caller the ability to
break the release → verify → reacquire ordering invariant. One method keeps that ordering
unreorderable by construction.

## Consequences

- Upward `mcp_server` imports under `search/`: **7 → 2**
  (`search/search_executor.py:468`, a documented runtime fallback; and
  `search/effective_config.py:21`, `TYPE_CHECKING`-only). Both are checked, not just counted:
  `tests/unit/search/test_layering_ownership.py::TestSearchMcpLayering` AST-walks every `.py`
  under `search/`, fails on any new non-`TYPE_CHECKING` `mcp_server` import outside an explicit
  allowlist, and separately fails if an allowlisted file stops importing `mcp_server` (dead
  documentation).
- `patch.object(IncrementalIndexer, "_release_and_verify_resources")`: **16 → 0** in production
  test code. The method no longer exists; the 16 sites were converted to
  `resource_refresher=NullResourceRefresher()` (matching prior patched-out behaviour) or
  `resource_refresher=McpResourceRefresher()` (for the handful of tests that exercised the real
  path unpatched). One reference survives, in this refactor's own new test file's docstring,
  explaining historically why the moved lines had never had unit coverage.
- `# pyrefly: ignore [bad-assignment]` in `search/incremental_indexer.py`: **1 → 0**. Deleted,
  not relocated — the indexer leg's `Any` typing on the protocol is what retires it; there is no
  equivalent suppression in `McpResourceRefresher`.
- `_release_and_verify_resources` textual references: **0** in production code. Every
  `IncrementalIndexer(...)` construction under `mcp_server/` now passes `resource_refresher=`
  explicitly, checked by `tests/unit/search/test_layering_ownership.py::TestResourceRefresherWiring`
  (an unadorned construction would silently fall back to `NullResourceRefresher()` in a process
  that owns real GPU/embedder/searcher state — a regression this ratchet catches at test time
  rather than in production logs).
- New unit coverage for the ~111 moved lines, previously untested because every test that
  reached `_full_index` patched the method away:
  `tests/unit/mcp_server/test_resource_manager.py::TestMcpResourceRefresherRefreshBeforeFullIndex`
  (happy path, verification-failure-does-not-abort, `_is_shutdown` true/absent/false branches,
  `get_searcher` raising propagates), `::TestMcpResourceRefresherInvalidateSearcherCache`, and
  `::TestMcpResourceRefresherSatisfiesProtocol` (`isinstance(McpResourceRefresher(),
  ResourceRefresher)`).
- The by-hand end-to-end oracle this plan specified — restart the live MCP server, run a full
  `index_directory`, and read the `[FULL_INDEX]` log lines by eye — was substituted with a
  targeted unit-test run (`-s --log-cli-level=INFO` against the happy-path test) that exercises
  the identical real code path and visually confirms the same three log lines
  (`Mandatory pre-reindex resource release starting…` → `Resource release completed` →
  `Fresh embedder acquired for reindex`) survived the move byte-identical. A literal server
  restart was avoided because the same live server backs this session's own connected search
  tools.
- No benchmark re-run, no reindex, no canon re-pin. This is a behaviour-preserving relocation of
  MCP process-resource management; it touches no retrieval path and
  `_release_and_verify_resources` appears in zero golden datasets — the same justification
  ADR-0051 recorded for its own move.

## Out of scope

Declined tidies, recorded so a future reviewer does not re-propose them as part of this change:

- **`state.reset_searcher()` in place of the bare `state.searcher = None`** — `reset_searcher()`
  acquires `state._lock` on an `asyncio.to_thread` worker; swapping it in would be a concurrency
  change wearing a cleanup's clothes.
- **Promoting `_cleanup_previous_resources` to a public name** — after this move, its only
  caller outside `mcp_server/resource_manager.py` is gone, so the leading underscore becomes
  correct rather than needing to change.
- **The pre-existing double release at `mcp_server/tools/index_handlers.py`'s
  `_setup_and_run`** — a separate, already-existing call path into resource release that this
  refactor did not touch and does not fix.
- **Deleting the 78-line verification block** inside `refresh_before_full_index` — the single
  cheapest change on the table, and one that passes the deletion test outright, but it removes
  six operator-facing log lines and a conditional `gc.collect()`/`empty_cache()`. Own hat, own
  commit, own ADR, afterwards — bundling it here would make every log line in the diff ambiguous
  between "moved" and "deleted".
