# Add a content-only `index_is_current` freshness verdict

Status: accepted
Date: 2026-08-30

## Context

An agent reported "the index was built 2026-08-22, eight days stale, so it predates
[two commit SHAs]." The user had run a full reindex and said the claim couldn't be right — they
were correct. The agent had read `list_projects`' `created_at` field and treated it as a build
timestamp. `created_at` is written once, at first registration
(`mcp_server/storage_manager.py:299`, guarded by `if not project_info_file.exists()`), and is
never touched again on the existing-directory path (`storage_manager.py:285` returns early). It
is registration metadata, not a freshness signal, and was already documented as such after a
prior fix — but the documentation didn't stop the misread, because a correctly-labeled `created_at`
still sits next to a `last_indexed_at` whose *meaning* invites the same mistake.

The deeper problem survives even a perfect `last_indexed_at`: **a timestamp answers "when did the
indexer last run", not "does the index match the working tree".** An agent still has to infer the
second question from the first by cross-referencing git history — the same inference that
produced the false report. `last_indexed_at` can be old but still correct (nothing changed since),
or recent but already wrong (a file changed after that run, before the next one). Neither case is
distinguishable from a timestamp alone.

The codebase already had the machinery to answer the real question directly. Three call sites had
independently built the same `ChangeDetector` construction to do it:
`mcp_server/tools/search_handlers.py:_is_index_stale` (age + quick root-hash compare, gating
auto-reindex), `_check_auto_reindex` (repeats the same `project_info` + `get_effective_filters`
load), and `search/incremental_indexer.py:IncrementalIndexer.needs_reindex` (graph-scored 0.75/0.76
similar to `_is_index_stale`). None of them exposed the verdict to an MCP caller, and each carried
the load-bearing but easy-to-miss requirement that `ChangeDetector` be constructed with
`supported_extensions=set(TreeSitterChunker.get_supported_extensions())` — the exact set the
indexer used. Omitting it flips non-code files from a stat-based fast hash to content hashing, so
the stored snapshot no longer compares and *every* file reads as changed. Measured on two real
projects: with the flag, `current=True`/`current=False (1 modified)` in 0.06s/0.15s; without it,
`changed=True` on both, at 3.16s/9.69s — wrong verdict, ~50x slower.

## Decision

Extract the shared `ChangeDetector` construction out of `_is_index_stale` into
`mcp_server/index_freshness.py` (`build_change_detector` + `compute_index_freshness`), so the
`supported_extensions` invariant has exactly one owner instead of a fourth copy being added
alongside the existing three. Placement is `mcp_server/`, not `search/` or `merkle/`: the helper
needs `mcp_server.storage_manager.get_project_storage_dir` to resolve a project's stored
`project_info.json` (for include/exclude filters), and `search/` may not import `mcp_server/` at
runtime (ADR-0004, enforced by `tests/unit/search/test_layering_ownership.py`) — an initial draft
placed the module under `search/` on the separate (and still-true) reasoning that `merkle/` should
not gain a new `merkle → chunking` edge, but missed this second, binding constraint; the layering
test caught it immediately. `mcp_server/` has no such restriction and is where every one of this
module's callers (`search_handlers.py`, `status_handlers.py`) already lives, so this placement adds
no new import direction.

`compute_index_freshness(project_path, *, model_slug=None, dimension=None)` returns:

```python
{
    "index_is_current": bool,  # content-only: no snapshot age involved
    "pending_changes": {"added": int, "modified": int, "removed": int},
}
```

or `None` when no snapshot exists for that project/model — distinct from a `False` (current but
never indexed vs. indexed and stale are different facts). It calls
`ChangeDetector.detect_changes_from_snapshot` (a full diff, not `quick_check`'s root-hash bool),
because `pending_changes` needs counts, not just a boolean, and the added cost is the same 0.05–
0.15s measured above.

`_is_index_stale` itself is rewritten to call `build_change_detector` and keeps its existing
age-gated bool return unchanged — it has exactly one caller
(`SearchOrchestrator._maybe_reindex`) and stays byte-identical in behavior. `_check_auto_reindex`
and `IncrementalIndexer.needs_reindex` are left as-is; folding them into the same extraction would
widen this change's blast radius past what the bug needs (see Follow-up).

Exposed via two MCP tools, on the model/detector layer's per-model resolution:

- `get_index_status`: `index_is_current` / `pending_changes` computed for the active project **by
  default**, alongside the existing (now clearly-labeled) `last_indexed_time`. Default-on is
  deliberate — an opt-in flag would reproduce the original failure mode, since an agent keeps
  reading whichever field is simply present without being told a better one exists.
- `list_projects`: gated behind a new `check_freshness: bool = False` parameter. A sequential
  sweep across all 13 real indexed projects measured **13.87s** — too slow to make unconditional.
  When enabled, per-project/per-model checks are fanned out with `asyncio.gather` over
  `asyncio.to_thread`, bounded by the slowest single project rather than their sum (measured
  ~2.5s for the same 13 projects, vs. 13.87s sequential).

`get_snapshot_path` / `load_snapshot` / `has_snapshot` on `SnapshotManager` gained an optional
`model_slug` parameter (mirroring what a prior fix already gave `get_metadata_path`/
`load_metadata`), and `ChangeDetector` gained optional `model_slug`/`dimension` constructor
parameters threaded into its `load_snapshot` calls. Without this, `list_projects(check_freshness=
True)` could only ever resolve the *currently active* config's model when checking a project
indexed with a different one — the same asymmetry a prior fix left unresolved for the snapshot
(as opposed to metadata) file. A redundant early-return in `_get_model_slug_and_dimension` (dead
code — result-identical to falling through both branches below it) was deleted in the same pass.

### Alternatives considered and rejected

- **Ship only the `created_at`/`last_indexed_at` fix and rely on documentation.** This is what the
  prior commit did, and it didn't prevent the report this ADR responds to — a technically-accurate
  but still-inferential timestamp invites the same misread. Labeling the trap doesn't remove it;
  only answering the actual question does.
- **Make `check_freshness` default-on for `list_projects` too**, for symmetry with
  `get_index_status`. Rejected on the measured 13.87s sequential cost — even fanned out
  concurrently (~2.5s), that is a materially different latency profile for a tool an agent might
  call just to find a project path, not to audit staleness.

## Consequences

- An agent asking "is this index stale" now gets a direct, content-grounded answer instead of
  having to infer one from a timestamp plus git history — the exact inference that failed.
- `mcp_server/index_freshness.py` is the single place that owns the `supported_extensions` invariant
  for *new* freshness checks; `_is_index_stale` was migrated to it, removing one of the three
  pre-existing duplicates.
- `get_index_status` calls now do one additional Merkle diff (0.05–0.15s measured) by default.
  `list_projects` is unaffected unless `check_freshness=True` is passed.
- `created_at` is unchanged and still returned by `list_projects` — it remains legitimate
  registration metadata other callers may rely on; removing it was out of scope. With
  `index_is_current` now available, the incentive to misread `created_at` (or `last_indexed_at`)
  as a staleness signal is gone.

## Follow-up (not built here)

`_check_auto_reindex` (`search_handlers.py`) and `IncrementalIndexer.needs_reindex`
(`incremental_indexer.py:1145-1165`) remain independent constructions of the same
`ChangeDetector` pattern — the call-graph scored `needs_reindex` 0.75/0.76 similar to
`_is_index_stale` before this change. Folding them into `mcp_server/index_freshness.py` too is a
reasonable next step, deferred here to keep this change's diff scoped to the reported bug.

## Verification

`./scripts/test/run_tests.sh tests/unit/merkle/ tests/unit/mcp_server/ tests/unit/search/ -q` —
2384 pass. `./scripts/git/check_lint.sh --modified-only` — ruff, format, and markdownlint clean.

Confirmed over the live wire, after restarting the MCP server and re-indexing (not just
in-process): `get_index_status` on `claude-context-local` returns `index_is_current: true`
with `pending_changes` all zero; `list_projects()` (default) omits both fields on all 13
indexed projects; `list_projects(check_freshness=True)` returns a verdict for **13/13**
projects with no swallowed exceptions, exercising the `asyncio.gather(...,
return_exceptions=True)` fan-out and per-model `model_slug` threading end-to-end.

That sweep produced concrete instances of the two failure directions this ADR's Context
argues a timestamp can't distinguish:

- **Old but correct**: `agentic-perf-loop` — `last_indexed_at` 34 days old, yet
  `index_is_current: true` with zero pending changes. A timestamp heuristic reads this as a
  month stale; it is not.
- **Recent but already wrong**: `TD_INSTALLATION_MONITOR` — `last_indexed_at` only 5 days
  old, but 35 files modified since → `index_is_current: false`.
- **The original bug, closed**: `voro-engine` still carries
  `created_at: 2026-08-22T13:12:06` — the exact value the agent in the original report read
  as a build timestamp — now sitting directly beside `index_is_current: true`. The
  misleading field is still there; it is no longer the only field there.
