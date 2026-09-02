# Incremental-pass call-edge re-injection: opt-in only, default stays off

Status: accepted
Date: 2026-08-19

## Context

`inject_call_edges` (`search/call_edge_injection.py`) had exactly one production caller:
`IndexWriteStage.run`, reached only from `IncrementalIndexer._full_index`. On an incremental pass,
`_remove_old_chunks` calls `graph_storage.remove_file_nodes` for every removed *and modified*
file, destroying that file's attached graph edges; `_add_new_chunks` re-adds nodes via
`add_embeddings`, which restores only the always-on AST-level edges. Resolver-injected pyan
(confidence 0.75) / LibCST (0.90) / LSP (0.98) edges were permanently lost for any file touched by
an incremental pass and never regenerated short of a forced full reindex — monotonic decay, not a
staleness window. No ADR sanctioned this; it was an oversight, not a decision (ADR-0036, ADR-0037,
ADR-0014 each record a deliberate full-only behaviour for unrelated reasons).

This is the third of three commits closing the gap (see the "Close the full-vs-incremental
call-edge gap" plan, candidate 5 of an architecture review): Commit 1 unified the duplicated
full/incremental pairs behind the `SummaryStage`/`IndexWriteStage` seams with zero behaviour
change. Commit 2 added `CallGraphConfig.inject_on_incremental` (`search/config.py`, default
`False`) and wired the incremental path in `incremental_indexer.py` to call
`IndexWriteStage._inject_call_edges` when the flag is set (the gate has since moved behind the
seam as `IndexWriteStage.inject_call_edges_if_enabled` — see ADR-0052), positioned after `add_embeddings`
(graph populated) and before `finalize`'s `save_indices` (graph persisted) — the same ordering
invariant the full-index path already relies on.

**The resolvers already have a file-scoping seam.** `prepare_scoped_files`
(`chunking/relationships/call_edge_resolver.py:285-326`) composes `gather_py_files` →
`scope_to_indexed_files` → `validate_py_files`, and is shared by `PyanResolver`, `LibCSTResolver`,
`LSPResolver`, and `run_resolvers`. But it scopes to the *indexed* file set, not the *changed*
file set — `gather_py_files` still `rglob`s the whole project tree on every call, regardless of
how many files an incremental pass actually touched.

## Measurement

Measured against `tests/fixtures/mini_repo/` (4 Python files, real pyan3/LibCST/LSP resolvers, no
mocking of the resolver pipeline) — full index, then touch every file to force an incremental pass
that reprocesses the whole fixture:

| | `inject_on_incremental=False` (current default) | `inject_on_incremental=True` |
|---|---|---|
| Incremental pass latency | 0.28s | 1.86s |
| Resolver-attributed edges recovered | 0 | 5 (pyan, libcst, lsp all ran) |
| Edges in persisted graph JSON with `resolver_source` | 0 | 5 |

Latency delta: **+1.58s**, a ~6.7x multiplier over the undecorated incremental pass, on a
four-file fixture. The delta is dominated by resolver startup cost (LSP's `basedpyright-langserver`
subprocess spin-up in particular), not by per-file analysis work — consistent with
`prepare_scoped_files` scoping to the *whole indexed set* rather than the changed subset. This
means the cost does not shrink for small incremental changes and does not stay flat as project
size grows: `gather_py_files`'s full-tree `rglob` and the resolvers' full-scope analysis both scale
with total indexed file count, not with `changes.added`/`changes.modified`/`changes.removed`.

**RW-lock hold time (ADR-0008).** Both the auto-reindex path and the manual `index_directory` path
hold the reindex-vs-search write lock for the full duration of the reindex call, so the measured
latency delta above *is* the RW-lock hold-time delta — no separate instrumentation was needed. A
1.58s addition to every incremental pass's write-lock hold time is a direct, proportional increase
in how long concurrent searches queue behind a reindex.

## Decision

**Keep `inject_on_incremental` opt-in, default `False`. Do not flip the default (no Commit 3.)**

Incremental indexing exists specifically to make small edits cheap to reflect in the index. A fixed
multi-second-per-pass tax — paid in full regardless of how small the actual change is, and growing
with total project size rather than change size — contradicts that purpose. For a project larger
than the four-file fixture measured here, `gather_py_files`'s full-tree walk and the resolvers'
full-indexed-set analysis make this worse, not better; the fixture measurement is a lower bound.

This is a **measured-and-rejected** outcome for the always-on default, not a rejection of the
feature: the opt-in flag is real, tested, and available for callers who want fresher call-graph
data on every pass and can accept the latency/lock-hold cost (e.g. CI reindex jobs, or projects
where `find_connections` accuracy matters more than pass latency).

**Named follow-up, not built here:** a *changed-file-scoped* injection — resolving edges only for
`changes.added | changes.modified` (plus their direct neighbors, to catch edges pointing *into*
the changed set) instead of the full indexed set. `prepare_scoped_files` is already the shape to
imitate; the composition point (`gather_py_files` → `scope_to_indexed_files` → `validate_py_files`)
is one function, not three call sites needing a threaded parameter. This is ADR-0035 territory
(constrained by ADR-0034's pyan GPL quarantine) and is the reopening condition for flipping the
default: if a changed-file-scoped variant lands and its cost scales with change size rather than
project size, re-measure and reconsider.

## Consequences

- `CallGraphConfig.inject_on_incremental` ships, default `False`. Existing incremental-pass
  behaviour (monotonic call-edge decay) is unchanged for every caller that doesn't opt in.
- `IncrementalIndexResult.call_edges_injected` / `call_edge_resolvers` report real, non-zero values
  when the flag is set and injection runs; they stay `0` / `()` by default, same as before this
  work — no change to what the MCP client sees unless a caller opts in via
  `search_overrides.json`.
- `tests/integration/test_call_edge_injection_integration.py::test_incremental_index_recovers_edges_when_enabled`
  is the regression guard: it proves the opt-in path actually recovers resolver-attributed edges
  against a real pipeline (mirroring the existing full-index sibling's anti-mock-regression
  rationale — see that test's docstring re: commit 3adc724).
- `find_connections` on a symbol whose file was touched only by an incremental pass shows only
  AST-level edges by default; opting in (`inject_on_incremental=true`) restores resolver-attributed
  edges (`resolver_source`/`resolver_confidence`) at the measured cost above.

## Verification

- `tests/unit/search/test_incremental_indexer.py::TestIncrementalCallEdgeInjection` — both branches
  of the gate (enabled forwards `InjectionStats` into the result; disabled skips injection, result
  stays at 0/()).
- `tests/integration/test_call_edge_injection_integration.py` — both the full-index sibling and the
  new incremental sibling pass against real pyan3/LibCST/LSP resolvers.
- Full `tests/unit/` (6116 passed / 1 skipped) and `tests/fast_integration/` + `tests/integration/`
  (122 passed) green with the flag wired in at its default (`False`) — confirms zero behaviour
  change for any caller that doesn't opt in.
