# Prefer module singletons over DI containers for process-global state

Status: accepted
Date: 2026-05-29

`ApplicationState` is a module-level singleton accessed via
`mcp_server.state.get_state()`; config is accessed via
`search.config.get_search_config()`.  The `ServiceLocator` DI container
introduced in an earlier refactor was removed.

## Context

A `ServiceLocator` registry (`mcp_server/services.py`) was added to provide
"dependency injection" for `ApplicationState` and `SearchConfig`.  A `ResourceManager`
class and `SearchFactory` class each wrapped the global state with an empty
`__init__`, a lazy module singleton, and a second layer of backward-compat
free-function wrappers.  The locator also leaked into lower layers:
`search/config.py`, `chunking/tree_sitter.py`, `chunking/languages/base.py`, and
`merkle/snapshot_manager.py` all called `ServiceLocator.instance().get_config()`
as their primary config access path.

## Decision

Remove `ServiceLocator`, the empty `ResourceManager`/`SearchFactory` classes,
their singletons, and the locator-first paths in the lower-layer modules.

Canonical accessors:
- **Application state**: `from mcp_server.state import get_state`
- **Search config**: `from search.config import get_search_config`
- **Resources/cleanup**: module-level functions in `mcp_server/resource_manager.py`
- **Searcher/index-manager**: module-level functions in `mcp_server/search_factory.py`

`mcp_server/services.py` is kept as a two-line re-export shim so existing handler
files (`from mcp_server.services import get_state, get_config`) continue to work
without an import sweep.

Test isolation: `reset_state()` in `mcp_server/state.py` (already the real mechanism)
+ `config_manager._config = None` in `tests/conftest.py`.  Test injection of mock
configs uses `patch("search.config.get_search_config", return_value=mock_config)`.

## Reasons

**The locator was a closed loop with zero real swappability consumers.**
No production code ever registered a non-default state or config into the locator.
The only `register()` calls were: `state.py` auto-registering `_app_state` on import,
`search/config.py` auto-registering a `get_search_config` factory on import, and tests
testing the locator itself.  Every path through the locator ended at the same module
singleton.

**The locator was a layer-inversion vector.**  Lower-layer modules
(`chunking/`, `merkle/`, `search/config.py`) imported from `mcp_server.services`
to call `ServiceLocator.instance().get_config()`.  They each already had a
`get_search_config()` fallback; removing the locator-first path collapsed each
to the fallback — zero behaviour change, one fewer layer inversion.

**Three indirection layers with no payoff.**  `get_searcher()` resolved as:
`search_factory.get_searcher()` → `get_search_factory().get_searcher()` →
`SearchFactory().get_searcher()` → `get_state().searcher`.  The class and singleton
held no state and enabled nothing.

## Consequences

- `mcp_server/services.py` exports `get_state` and `get_config` as re-exports
  (2 lines instead of 170).
- `mcp_server/resource_manager.py` exposes `_cleanup_previous_resources()`,
  `close_project_resources()`, and `initialize_server_state()` as module-level
  functions (no class, no singleton).
- `mcp_server/search_factory.py` exposes `get_index_manager()` and `get_searcher()`
  as module-level functions; `mcp_server/server.py` re-exports are unchanged.
- Tests that injected mock configs via `ServiceLocator.register("config", ...)` now
  use `patch("search.config.get_search_config", return_value=mock_config)`.
- `test_services.py` (29 tests of the locator mechanism) deleted.
- Three lower-layer config paths simplified from ServiceLocator-first to direct
  `get_search_config()` calls.

## Re-evaluation triggers

Reconsider a DI container if and when:
1. Multiple non-test implementations of `ApplicationState` or `SearchConfig` are needed
   in the same process (e.g., multi-tenant mode), AND
2. The swapping cannot be achieved via environment variables, config files, or
   process-level arguments.

Until both conditions hold simultaneously, the module-singleton pattern is simpler,
easier to navigate, and carries zero overhead.

## Addendum (2026-06-11)

The `ApplicationState` singleton's concurrent construction and teardown are now
lock-guarded; the model-pool factory singleton also carries its own lock.
See [ADR-0006](0006-thread-safety-of-module-singletons.md) for the locking design.
