# Make include_dirs additive for dependency trees, narrowing for source

Status: accepted
Date: 2026-08-07

## Context

A user indexed `D:\dev\SDTD_040_Beta` through the `start_mcp_server.cmd` "index new project" menu
and typed 8 include patterns, all pointing inside `StreamDiffusion/venv/Lib/site-packages`
(`diffusers*`, `insightface`, `huggingface_hub`, `polygraphy`, `onnx*`, `accelerate`, `peft`,
`controlnet_aux`). The run reported **success** and produced a 41,590-chunk index containing 100%
third-party library code and **zero of their own source** — `IPAdapterModule`,
`engine_manager.get_engine_path`, `wrapper.py` all became unsearchable.

The patterns were correct — all 8 resolved properly from the project root and matched thousands of
files. Nothing was typo'd, which is exactly why nothing errored: the existing guard
`all_includes_unmatched()` requires **every** pattern to match zero files, and all 8 matched.

### The real defect: two jobs conflated into one parameter

`include_dirs` did two unrelated things at once:

- **Narrowing** — "index only `src/core`" (an exhaustive whitelist)
- **Re-admitting** — "also index `site-packages/torch`" (an exception to the default excludes)

`FILTER_SEMANTICS_VERSION`'s own comment (`mcp_server/storage_manager.py`) described the second job
as the feature's purpose: *"an include_dirs pattern can override a default-ignored directory (e.g.
`venv`, `site-packages`)"*. But `PathFilter._classify`'s old step 3 put re-admission behind a
whitelist test that rejected every unnamed path first — so the feature built to *add*
`site-packages/torch` could only be used by simultaneously *discarding* the entire source tree.
There was no way to express re-admission alone. This is corroborated three times in-tree:
`FILTER_SEMANTICS_VERSION`'s comment, `PathFilter`'s class docstring, and
`get_effective_filters`'s note all describe `include_dirs` as a mechanism for overriding a
default-ignored directory — never as a whole-project whitelist. The implementation had drifted
from its own documented intent.

### The asymmetry, in one file

A real `project_info.json` from this repo shows the inconsistency plainly. Its
`user_excluded_dirs` **adds to** the ~50 `default_excluded_dirs` — the author never had to
re-list `__pycache__` or `.git` to keep them excluded. `user_included_dirs`, in the same file,
written by the same UI prompt pair, **replaced** the default scope instead of adding to it:

| Field | Composition with defaults |
|---|---|
| `user_excluded_dirs` | **additive** — defaults ∪ yours |
| `user_included_dirs` | **replacing** — yours only, defaults' scope discarded |

Nothing in the UI, the schema, or the docs signalled that the two behaved oppositely. The user
followed the documented example (`start_mcp_server.cmd`'s own sample was
`venv/Lib/site-packages/torch,venv/Lib/site-packages/transformers` — precisely the shape that
silently wipes first-party code).

## Decision

> **A pattern reaching into a dependency tree (`venv`, `site-packages`, `node_modules`, …) is
> ADDED to the normal root-down scope. Any other pattern RESTRICTS indexing to just the paths
> named.**

| Input | Before | After |
|---|---|---|
| `venv/Lib/site-packages/diffusers*` (the incident) | only that lib | **full source + that lib** |
| `src/core` | only `src/core` | only `src/core` *(unchanged)* |
| `src/core,venv/Lib/site-packages/torch` | both, source lost | `src/core` + `torch` |

Landed as an ordered sequence:

1. **`DEPENDENCY_TREE_DIRS` constant** (`chunking/language_registry.py:115-129`) — 13 members
   (`site-packages`, `node_modules`, `venv`, `.venv`, `env`, `.env`, `.direnv`, `.yarn`,
   `.pnpm-store`, `.gradle`, `.mvn`, `.tox`, `.uv-cache`), pinned as a strict subset of
   `DEFAULT_IGNORED_DIRS` via an `assert` (`:130-132`) so the subset can't drift. Deliberately
   excludes `build`/`dist`/`out`/`public`/`target`/`bin`/`obj` — those are plausible real
   source-dir names, and treating `Include: out/src` as additive would silently refuse to narrow.
2. **Classification at parse time** (`search/filters.py`) — `is_dependency_pattern(pattern:
   DirPattern) -> bool` (`:304-318`) returns True iff any of the pattern's normalized segments is
   in `DEPENDENCY_TREE_DIRS`. `PathFilter.__init__` partitions `self.include_patterns` into
   `self.narrowing_patterns` / `self.additive_patterns` (`:466-480`) based on this predicate,
   unless `include_exclusive=True` forces everything into `narrowing_patterns`.
3. **The behaviour change is one line** — `_classify`'s step 3 whitelist test now gates on
   `self.narrowing_patterns` instead of `self.include_patterns` (`:558`). Step 4's re-admission
   (unchanged) still scans all include patterns via `_best_match`, so the net effect is exactly
   the union semantics wanted: only-narrowing input is byte-identical to before; only-additive
   input skips step 3 entirely so first-party files survive; mixed input unions both sets.
4. **`include_exclusive: bool = False` escape hatch** — forces every pattern back to narrowing
   (today's pre-change whitelist-only behavior), preserving the "index *only* these libraries"
   capability the new default can no longer express. Threaded through the full call chain:
   `PathFilter.__init__` → `MerkleDAG`/`IncrementalIndexer` → `index_handlers._run_indexing` →
   `tool_registry` schema → `batch_index.py --include-exclusive`. Persisted in
   `project_info.json` alongside `user_included_dirs` (`get_project_storage_dir`,
   `mcp_server/storage_manager.py`), because `search_handlers._check_auto_reindex` rebuilds its own
   `IncrementalIndexer` from stored filters on every stale-index reindex — without persistence an
   exclusive project would silently revert to additive.
5. **`FILTER_SEMANTICS_VERSION` bumped 2 → 3** (`mcp_server/storage_manager.py:41`) with a new v3
   branch in `check_filter_semantics_migration` warning that a stored all-additive include list
   will now index *more* than before — a benign widening, but announced rather than silently
   changing an existing index on the next full reindex. `filters_changed` was extended to compare
   the stored `filter_semantics_version` too, so the bump alone forces a reindex.
6. **Backstop guard** (`search/incremental_indexer.py::_full_index`, between the existing
   `all_includes_unmatched` abort and the destructive `delete_snapshot`/`clear_index` calls) — a
   *narrowing* include list (or `include_exclusive=True`) can still resolve entirely inside a
   dependency tree (e.g. `Include: torch`). `PathFilter.only_dependency_paths_matched(rel_paths)`
   / `.dependency_segments(rel_paths)` (`:599-643`) detect this and hard-abort via
   `self._zero_result(..., success=False)`, downgrading to a `logger.warning` and proceeding only
   when `include_exclusive` was passed deliberately. These helpers live on `PathFilter`, not
   inline at the call site, because `MerkleDAG.get_all_files()` returns OS-native separators
   (`StreamDiffusion\venv\Lib\...` on Windows) — a naive `f.split("/")` at the call site would
   never match on the exact platform where this incident happened.
7. **Wording updated on six user-facing surfaces** — `start_mcp_server.cmd`'s "index new project"
   prompts, `mcp_server/tool_registry.py`'s `include_dirs` schema description,
   `docs/MCP_TOOLS_REFERENCE.md`, `tools/batch_index.py --include-dirs` help text,
   `docs/ADVANCED_FEATURES_GUIDE.md` (which previously claimed the zero-match abort alone covered
   this case), and `search/filters.py`'s `PathFilter` docstring — all now state the
   additive-vs-narrowing rule side by side with `exclude_dirs`' always-additive rule.
8. **`--dry-run` made reachable and self-teaching** — `batch_index.py --dry-run` now prints a
   per-pattern `[additive ]`/`[narrowing]` classification, a summary breakdown, and runs the same
   dependency-only-match check the real indexing path uses (warn-and-proceed under
   `--include-exclusive`, hard error otherwise). `start_mcp_server.cmd`'s "index new project" flow
   gained an optional preview step (via a new `:index_new_project_filters` label enabling a
   proceed/cancel/edit-filters loop) that runs this dry-run before committing to a real index.
   The preview also prints the concrete inventory it would index — root-level files by name, then
   every directory that directly contains a matched file with its file count and size, capped at
   150 rows per section (`--dry-run-full` lists every row) — so a filter set that "succeeds" while
   silently discarding first-party source is visible before a full index is paid for, not just
   inferred from a bare total.

## Consequences

- **Positive**: the acceptance criterion — *"include specific folders which are otherwise excluded
  by default, but other folders should be indexed as usual if not specified"* — is now what the
  user's original, unmodified 8-pattern input does, with no flag and no edit to their input.
  Sub-package scoping also falls out for free: `.../site-packages/transformers/models/clip` is
  additive and re-admits exactly that subtree while the rest of `transformers` stays excluded.
- **Positive**: trimming a dependency-only include list back down is now pure subtraction — no
  risk to first-party code, since removing a pattern from an all-additive list can only shrink the
  re-admitted set, never the normal root-down scope.
- **Blast radius is small**: any project with an empty/absent `user_included_dirs` (including this
  repo's own index, which uses excludes only) has no include patterns, so `narrowing_patterns` is
  empty either way and `_classify` is byte-identical. Only projects that set include patterns
  reaching into a dependency tree change behaviour, and only by gaining files, never losing them.
- **A narrowing list can still wipe source** if every pattern happens to resolve entirely inside a
  dependency tree (e.g. `Include: torch` alone) — item 6's backstop guard is the safety net for
  that residual case, and for `include_exclusive=True` re-enabling the original failure mode by
  request.
- **Conservative by design**: a bare `torch` (no `venv`/`site-packages` segment) still classifies
  as narrowing — the code cannot know whether the user means "the `torch` library" or "a source
  directory named `torch`", and narrowing was the pre-existing default. The backstop guard, not
  auto-classification, is what catches that ambiguity when it goes wrong.

## Rejected alternatives

- **Pure-additive** (drop narrowing entirely, `include_dirs` only ever re-admits). Rejected:
  removes the "index only these paths" capability the MCP tool contract and several existing
  callers rely on, with no escape hatch.
- **A separate `also_index_dirs` parameter**, leaving `include_dirs` purely narrowing. Rejected:
  explicit, but grows the API surface with a second directory-list parameter that has to be
  threaded through every layer `include_dirs` already touches, and does nothing to prevent the
  same confusion from recurring for the next person who reaches for `include_dirs` expecting
  re-admission (the documented, in-tree intent all along).

## Verification

- `tests/unit/search/test_dir_patterns.py` — new `TestPatternClassification` class covers the
  literal 8-pattern incident input (classifies all-additive, admits
  `StreamDiffusion/src/wrapper.py`), a plain `src/core` pattern staying narrowing, a mixed-list
  union, `out/src` staying narrowing (not additive), backslash-input classification (pins the
  Windows separator trap), and `include_exclusive=True` restoring the old whitelist-only
  behavior. Three pre-existing tests that encoded the old narrowing-only semantics for
  dependency-tree patterns were updated: two renamed and pinned via `include_exclusive=True`
  (preserving their original assertions as an explicit-opt-in regression test), with new
  companion tests added alongside asserting the new default-additive behavior. 50 passed.
- `tests/unit/search/test_incremental_indexer.py` — 5 new tests on `_full_index`: the backstop
  guard aborts with `success is False` and the survival property holds
  (`delete_snapshot.assert_not_called()` + `clear_index.assert_not_called()`);
  `all_includes_unmatched` still takes precedence (`only_dependency_paths_matched` is never even
  called once that abort has fired); `include_exclusive=True` downgrades the guard to a warning
  and lets indexing proceed; the incremental (non-full) path never applies the guard at all. 64
  passed.
- `tests/unit/merkle/test_merkle.py` — two pre-existing tests
  (`test_include_dirs_overrides_default_ignored_dir`,
  `test_include_dirs_excludes_ancestor_files_regression`) encoded the same old narrowing-only
  semantics one layer down, at `MerkleDAG` construction. Fixed the same way: the first now asserts
  additive-by-default (root-down scope survives), with a new
  `test_include_exclusive_overrides_default_ignored_dir_narrowing_only` pinning the old behavior;
  the second was pinned via `include_exclusive=True` with a new
  `test_dependency_include_dirs_is_additive_by_default` asserting the new default.
- `tests/unit/` full suite — 5778 passed, 1 skipped, 0 failed. Also repaired unrelated collateral
  drift surfaced by the same run: `get_project_storage_dir` (`mcp_server/storage_manager.py`)
  grew past the chunker's split-block threshold after gaining the `include_exclusive` parameter
  and its docstring, changing its golden chunk_id from `function:get_project_storage_dir` to
  `method:get_project_storage_dir` (`evaluation/golden_dataset_expanded.json`, query H033) — a
  pure chunk-shape rename, not a retrieval-quality change.
- `tests/fast_integration/test_menu_config_parity.py` — 2 passed; the new `.cmd` preview prompts
  don't break `test_menu_choice_ranges_match_handlers_and_guards`.
- **End-to-end on the real repro**: ran `batch_index.py --dry-run` against `D:\dev\SDTD_040_Beta`
  with the user's *original, unmodified* 8-pattern input. All 8 patterns classified additive (0
  narrowing); the walk matched 3,440 files across the 8 libraries plus 532 additional first-party
  files pulled in by the now-preserved root-down scope. Directly confirmed via
  `PathFilter.should_index_file` against the exact three symbols lost in the original incident —
  `StreamDiffusion/src/streamdiffusion/wrapper.py`,
  `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py`, and
  `StreamDiffusion/src/streamdiffusion/modules/ipadapter_module.py` — all now `True`, while an
  unrequested dependency (`venv/Lib/site-packages/torch/...`) stays `False`. A full real index of
  this ~3,440+-file external project was not run (multi-GB, long-running, and mutates that
  project's own on-disk index state); the dry-run and `should_index_file` checks exercise the
  identical `PathFilter` code path the real indexer calls, so this is equivalent proof without the
  cost.

## Out of scope

Two findings from the prior session's log verification (commits `f8ce309`, `1b60ce7`, `64c311c`,
confirmed working) remain unaddressed and are not part of this change: pyan's silent stall (its
`[PYAN]` logs are stranded in a spawned child whose logger has no handlers, and
`future.result()` has no timeout), and BM25 persisting the corpus 3× uncompressed on disk.
