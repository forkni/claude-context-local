# Derive `ToolSpec.mutation_lock` / `.requires_index` from decorator stamps

Status: accepted
Date: 2026-08-23

## Context

`mcp_server/tool_specs.py` is the repo's hottest MCP file (33 commits in 6 weeks). Each of its 18
`ToolSpec` rows is described by the module docstring as "the single declaration of an MCP tool's
wire schema, handler, and dispatch-time guards." Two of the three genuinely derive from the row —
`TOOL_DISPATCH` and `ADVANCED_TOOLS` are built from `handler` and `advanced`. The guard flags did
not: `mutation_lock` and `requires_index` were hand-typed on all 18 rows (36 kwargs total), while
the actual enforcement — `@with_mutation_lock` / `@require_indexed_project` — was hand-applied
separately at each handler's def-site. The two declarations could disagree with nothing to stop
it.

The repo had already built a guard against that drift:
`tests/unit/mcp_server/test_tool_handlers.py:33-167` walked each handler's `__wrapped__` chain and
grepped `layer.__code__.co_names` for the literal strings `"get_mutation_lock"` /
`"no_indexed_project"`. Three problems with it:

1. **`co_names` proves a name is referenced, not that a lock is taken.** Move the `async with` one
   call deeper and the assertion stays green while becoming vacuous.
2. **It already needed an escape hatch.** `_DECORATOR_SPECS` excluded `index_directory` — the one
   tool that takes the lock itself instead of via decorator — and substituted an assertion that a
   string sits in the bytecode constant table of a *private* function
   (`index_handlers._run_index_directory.__code__.co_names`). Renaming that private function would
   break the test for the wrong reason.
3. **`tool_specs.py:12` pointed readers at `tests/unit/mcp_server/test_tool_specs.py`** for this
   coverage. That file has no decorator or guard test in it — the tests it promised actually lived
   in `test_tool_handlers.py`.

Applying the deletion test to the *fields themselves* (not just the reflection test) settled what
kind of fix this needed: `grep` finds zero production readers of `.mutation_lock` /
`.requires_index` anywhere in the repo. The two names appear in exactly two files —
`tool_specs.py` (the 36 hand-typed kwargs) and the old test. Nothing else reads them. They were not
a seam; they were a mirror — a hand-typed claim whose sole purpose was to be compared against the
thing it describes. `co_names` was not the disease; verifying a mirror was.

### Alternatives considered and rejected

- **Have `TOOL_DISPATCH` apply the decorators to bare handlers at dispatch-build time**, so the row
  and the decoration become the same act. Rejected: the decorated handlers are consumed by name
  across 33 files (233 `handle_*(` occurrences) — `mcp_server/tools/__init__.py` re-exports all 18,
  and ~49 non-test references sit in 14 files (`server.py`, the four `*_handlers.py` modules,
  `search_orchestrator.py` calling `handle_find_similar_code` directly, plus
  `scripts/antigravity_bridge.py`, a profiler, and `probe_context_cost.py`). Moving decoration to
  dispatch-build time would silently strip `@require_indexed_project` / `@with_mutation_lock` from
  every one of them — a correctness regression, not a refactor.
- **An `_INTERNAL_LOCKERS` hand-typed side table in `tool_specs.py`** for the one tool
  (`index_directory`) that cannot be decorated directly. Rejected: it reintroduces the exact
  hand-typed-side-table smell this change removes, just at a smaller size.

## Decision

`with_mutation_lock` and `require_indexed_project` (`mcp_server/tools/decorators.py`) now stamp
`__mcp_guards__` — a `frozenset[str]` — on the wrapper they return, unioned with whatever the
wrapped function already carries:

```python
wrapper.__mcp_guards__ = getattr(func, "__mcp_guards__", frozenset()) | {
    "mutation_lock"
}
```

The union (not a plain assignment) matters because `functools.wraps` — already used by both
decorators — copies a stamp set by an *inner* decorator outward onto every enclosing wrapper's
`__dict__` (`functools.WRAPPER_UPDATES == ('__dict__',)`), and this line runs *after* that copy.
A plain assignment would clobber an inherited stamp from a decorator applied underneath it; the
union lets a handler wearing both guards accumulate both stamps regardless of application order.

`handle_index_directory` cannot be decorated with `@with_mutation_lock` directly: under
`wait=False` it hands the real work to `asyncio.create_task` and returns immediately, so a
decorator on the handler would only cover the fast job-creation call, not the actual indexing.
`_run_index_directory` instead takes `get_mutation_lock()` explicitly around its state-mutating
prologue and releases it before the reindex rwlock body runs. It is stamped directly at its
def-site instead:

```python
handle_index_directory.__mcp_guards__ = frozenset({"mutation_lock:internal"})
```

`ToolSpec.mutation_lock` / `.requires_index` are now `@property`s reading `__mcp_guards__` off
`self.handler`, not fields:

```python
@property
def mutation_lock(self) -> Literal["decorator", "internal", None]:
    guards = getattr(self.handler, "__mcp_guards__", frozenset())
    if "mutation_lock:internal" in guards:
        return "internal"
    return "decorator" if "mutation_lock" in guards else None


@property
def requires_index(self) -> bool:
    guards = getattr(self.handler, "__mcp_guards__", frozenset())
    return "requires_index" in guards
```

The 36 hand-typed `mutation_lock=`/`requires_index=` kwargs come out of the 18 `ToolSpec(...)`
rows in the same edit (leaving them in would be a `TypeError` against the now-fieldless
dataclass).

Both properties stay a plain read over the row — no DI container, consistent with
[ADR-0005](0005-no-di-container-module-singleton-state.md).

## Consequences

- A row can no longer drift from its handler's actual decorator chain — the flag *is* a query over
  the decoration, not a second claim about it. Adding a new mutation-guarded tool now only requires
  applying `@with_mutation_lock`; there is no second, hand-typed place to remember.
- `tests/unit/mcp_server/test_tool_handlers.py:33-167` (four reflection helpers, the exclusion
  list, three tests — ~130 lines) is deleted. Its one non-redundant guarantee — that
  `handle_index_directory` is *not* also `@with_mutation_lock`-decorated (decorating it would only
  guard job creation under `wait=False`, not the indexing, and the derived property would mask the
  mistake by still reporting `"internal"`) — is carried forward as an explicit assertion on the
  stamp set itself, in `test_tool_specs.py`.
- `tests/unit/mcp_server/test_tool_specs.py` gained
  `TestGuardFlagsDerivedFromDecoratorStamps`: for all 18 rows, an independently recomputed
  derivation (duplicated, not imported, so the test can't pass by construction if the property's
  own logic breaks) is asserted equal to `spec.mutation_lock` / `spec.requires_index`.
  `tool_specs.py:12`'s pointer at this file is now literally true — the guard coverage really does
  live there.
- `tests/unit/mcp_server/test_decorators.py`'s `TestWithMutationLockDecorator` gained two stamp
  tests: that `@with_mutation_lock` alone stamps `{"mutation_lock"}`, and that stacking it over
  `@require_indexed_project` produces the union `{"mutation_lock", "requires_index"}` rather than
  overwriting.
- `tests/unit/mcp_server/test_index_handlers.py`'s `TestIndexDirectoryAsyncJob` gained
  `test_wait_true_acquires_the_real_mutation_lock` — the one case a structural stamp check cannot
  reach, since a stamp only proves `handle_index_directory` is *marked* as an internal locker, not
  that `_run_index_directory`'s prologue actually acquires the lock at runtime. It drives the real
  handler end to end (only the heavy post-lock indexing work, `_setup_and_run`, is patched out) and
  spies on `get_state().get_mutation_lock()`'s `__aenter__`/`__aexit__` to prove real acquisition,
  and that the lock releases before the reindex rwlock body begins — the lock-order contract
  already documented on `with_mutation_lock`'s docstring.
- Behavior-preserving throughout: derived values are byte-identical to the pre-refactor hand-typed
  ones on all 18 rows (`sorted((s.name, s.mutation_lock, s.requires_index) for s in TOOL_SPECS)`
  diffed before/after), and the SSCG canons are untouched — nothing on the retrieval path was
  edited.

## Reasons

`mutation_lock` / `requires_index` still have zero production readers after this change — that was
never in question. What changed is which artifact is the source of truth. Before, the source of
truth was two independent, hand-synced statements (the decorator chain and the row), with a
bytecode-shaped test papering over the gap between them. After, the decorator chain *is* the source
of truth, and the row is a projection of it — the Speculative Generality (a declared field driving
nothing), Duplicated Code (the guard stated twice), and Shotgun Surgery (adding a tool touched row +
decorator + reflection test) are gone because there is only one place left to edit.

## Verification

`./scripts/test/run_tests.sh tests/unit/mcp_server/ -q` green after every mechanical step (one
recipe step at a time: stamp the decorators → stamp `handle_index_directory` → parallel-change
checkpoint tests → fields-to-properties conversion → remove the dead reflection block → add the
behavioural lock test → reword the docstring pointer). Full suite green at the end:
`./scripts/test/run_tests.sh tests/unit/ -q` (4190 passed, 2 pre-existing skips, unrelated to this
change) and `./scripts/test/run_tests.sh tests/fast_integration/ -q` (102 passed, including
`test_menu_config_parity.py` and `test_clear_index_integration.py`, both of which exercise handler
entry points). Live MCP smoke test against the running server: `switch_project` (decorator-guarded
mutation lock), `search_code` (`requires_index`-guarded), `get_index_status` — all three succeeded
against this repo's own index.
