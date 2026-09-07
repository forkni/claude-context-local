# Free the synthetic-chunk reorder from Block F's graph guard

Status: accepted
Date: 2026-09-06

## Context

A `/improve-codebase-architecture` pass surfaced six candidates (C1-C6) from a hot-spot scan of
this repo. C1 landed as [ADR-0064](0064-index-write-target-protocol-seam.md), C2 as
[ADR-0065](0065-relationship-analyzer-result-projection-unification.md). This ADR is the review's
C3.

`search/graph_scoring_stage.py` guarded Block F (centrality) with:

```python
if (graph_config and graph_config.centrality_annotation
        and index_manager and index_manager.graph_storage):
```

Block G (subgraph) guards with `index_manager.graph_storage is not None` instead.
`CodeGraphStorage` defines `__len__` but no `__bool__` (`graph/graph_storage.py:1378-1387`, whose
own docstring warns about exactly this trap, citing the `clear_index()` re-sync bug it once caused
in `hybrid_searcher.py`). Python falls back to `len(obj) != 0` when `__bool__` is absent, so
Block F's guard was a node-count test in disguise: a valid, freshly-constructed, or just-cleared
graph storage is falsy.

The substantive consequence was never centrality itself — it was that `_reorder_synthetic`
(intent-aware module-summary demotion) ran at the end of the same guarded `try` block, alongside
`GraphQueryEngine`, `CentralityRanker`, and friends. Verified live via MCP `find_connections`:
`_reorder_synthetic`'s only direct callee is its own `@staticmethod` `_result_score`, which reads
three score keys off a plain dict — no `CodeGraphStorage`, no `GraphQueryEngine`, no
`CentralityRanker`. It was the one non-graph callee sitting among eight graph ones inside Block F.
Net effect: on an empty or just-cleared graph, module-summary chunks silently stopped being
demoted for non-`GLOBAL` queries, for a reason that had nothing to do with the graph. The same
skip also fired whenever the guarded `except (ImportError, ValueError, KeyError, RuntimeError,
TypeError)` caught an error, or whenever `centrality_annotation` was `False`.

**A one-token guard flip (`graph_storage` → `graph_storage is not None`) was considered and
rejected.** It would newly run `GraphQueryEngine`, `CentralityRanker`, and `ranker.rerank()`/
`ranker.annotate()` on a 0-node graph, and with `enable_size_normalization=True`
(`search/config.py:1267`, the default) apply size-normalization penalties on that empty-graph
path — a behavior change nobody asked for, and unrelated to the actual defect. The guard flip is
not the fix; hoisting `_reorder_synthetic` out from under the guard is.

`GraphScoringStage._apply_centrality` is a grade-2 golden chunk
(`evaluation/golden_dataset_expanded.json`) — kept as a named method throughout; only its
parameter list narrowed. `_reorder_synthetic` and `_result_score` have zero golden references and
were free to move.

## Decision

**Two separate commits, two hats** — a pure guard refactor first, the reviewed behavior change
second, so the wire-visible half stays independently revertible.

**Commit 1** (`61e7695`, behavior-preserving): rewrote Block F's guard to state its intent
explicitly —

```python
and index_manager.graph_storage is not None
and len(index_manager.graph_storage) > 0
```

— semantically identical to the old truthiness check on every real `CodeGraphStorage`/`None`
value, so it changes nothing on its own. Also corrected the class docstring (`:28-38`) and the
`CONTEXT.md` "Graph-scoring stage" glossary entry, both of which previously described Block F's
guard using only the `centrality_annotation` conjunct and omitted the storage check entirely.

Gate 0 (committed inside `406a48f`, *before* any production edit): three characterization tests
in `tests/unit/search/test_graph_scoring_stage.py::TestReorderSyntheticGraphGuardGate0`, using a
real `CodeGraphStorage` (empty and populated) rather than a `Mock`-configured `__len__`, so the
tests bind to the actual `__len__`/`__bool__` semantics instead of an assumption about them. One
pinned today's bug (empty storage → module chunks NOT demoted), one pinned the inertness case
(populated storage → module chunks ARE demoted, unaffected by either commit), one pinned the
independent `centrality_annotation=False` skip.

Repairing Commit 1 exposed a latent test smell rather than a behavior gap: five existing
`TestApplyCentrality` tests set `im.graph_storage = Mock()` (bare `Mock`, not `MagicMock`) to
simulate a truthy graph storage under the old guard. A bare `Mock` has no `__len__` at all —
`len(Mock())` raises `TypeError` — so the new `len(...) > 0` check broke them. Fixed by adding a
`_truthy_graph_storage()` helper (`MagicMock(**{"__len__.return_value": 1})`) and swapping those
five occurrences; the other six `Mock()` occurrences elsewhere in the file were left untouched
because they never reach the `len()` check (short-circuited first by `graph_config=None` or
`centrality_annotation=False`). A sixth fixture,
`tests/unit/mcp_server/test_search_orchestrator.py::test_reindex_and_concurrent_searches_never_overlap`,
hit the same `TypeError` via a different path: its shared `_make_ready_searcher()` helper never
sets `dense_index.graph_storage`, so accessing it auto-vivified a bare child `Mock()`. Under the
old guard this bare Mock's truthiness let Block F's `try` run, and whatever it raised against the
fully-fake graph was silently swallowed by the broad `except` — meaning the test's prior "pass"
never actually exercised correct centrality behavior. Fixed with one explicit
`searcher.dense_index.graph_storage = None` line inside that single test (not the shared fixture,
which eight other tests depend on without any graph-storage assumption), with a comment recording
why. Both fixes repair test doubles that relied on incidental Mock behavior; neither weakens the
production guard.

**Commit 2** (`ae871ce2`, the reviewed behavior change): moved the `_reorder_synthetic` call out
of Block F's guarded `try` and into `run()`, between `_apply_centrality` and `_cap_results` —
preserving its position relative to `rerank`/`annotate` (it still reads
`reranker_score`/`blended_score`/`score`, which `ranker.rerank()` rewrites) and relative to the
cap. Dropped the now-unused `intent_decision` parameter from `_apply_centrality`'s signature — a
Change Function Declaration on the grade-2 golden method: name and kind untouched, only the
parameter list narrows. Updated the two Gate 0 tests that pinned the bug
(`test_empty_real_graph_storage_skips_synthetic_reorder_today` →
`test_empty_real_graph_storage_still_demotes_synthetic`,
`test_centrality_annotation_off_skips_synthetic_reorder_today` →
`test_centrality_annotation_off_still_demotes_synthetic`) to their fixed-state expectations; the
inertness pin (populated storage) needed no change.

## Verification

The change is provably inert on a populated substrate: all four preconditions for divergence
(empty/missing graph, `centrality_annotation=False`, missing `index_manager`, or the guarded
`except` firing) are absent there, and `_reorder_synthetic` already ran at exactly the same point
in the sequence. So the gate was a **bit-identity check, not a drift-band re-pin** — a stronger
claim, chosen deliberately because it fails loudly if the inertness reasoning is wrong.

Compared against a **fresh paired self-baseline**, not the published canon: the live index had
already drifted past the pinned 2026-09-06 canon (2,967 vs. 2,956 chunks, from ADR-0064/ADR-0065's
own intervening commits), so bit-identity against the published number was impossible and would
have manufactured a false failure.

1. Full non-incremental reindex (`tools/batch_index.py --path . --mode force`, after MCP
   `cleanup_resources` released the metadata.db handle held by the live MCP server): 235 files /
   2,967 chunks. `audit_golden_dataset.py` CLEAN on both datasets.
2. **Leg 1** — 63-query benchmark on the *pre-Commit-2* code (Commit 2's diff stashed). MRR
   0.8228, guard-rails `Overall: PASS`, `centrality_seeded` 63/63, `ego_rerank_pass_fired` 63/63,
   zero auto-reindex events (`CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0` exported for both legs).
3. Commit 2's diff restored (stash pop). **No reindex between legs** — the diff must isolate the
   code change alone.
4. **Leg 2** — same 63 queries, same index. Aggregate metrics, `pass_fail`, and
   `confound_summary` compared byte-for-byte equal to Leg 1; per-query `retrieved` lists compared
   equal on all 63 queries (0 movers). The only field that differed anywhere in the two result
   files was `latency_ms` (timing noise) — every score and ranking was bit-identical.

Leg 1's MRR (0.8228) vs. the published 0.8151 canon is recorded here only as an informational
substrate-drift note (+11 chunks from ADR-0064/ADR-0065's own code) — it is not this change's
drift and not a gate.

Full unit suite green at every step (4,655 passed, 2 skipped, +3 vs. the 4,652 baseline for the
three new Gate 0 tests — no other regressions); lint, format, and pyrefly clean on both commits.

## Consequences

- Intent-aware synthetic-chunk ordering no longer depends on graph state at all — it runs
  whenever `intent_decision` says to, independent of whether Block F ran, errored, or was
  disabled.
- Block F's guard now states what it means (`is not None and len(...) > 0`) instead of relying on
  a documented `__len__`/`__bool__` trap; the class docstring, `run()`'s `graph_config` arg
  docstring, and the `CONTEXT.md` glossary entry all describe the corrected behavior.
- `_apply_centrality`'s signature narrowed (`intent_decision` removed); its docstring now points
  callers at `run()` for the ordering step.

## Out of scope

- **Relocating `GraphScoringStage`** — [ADR-0051](0051-graph-scoring-stage-search-seam.md)
  rejected moving it into `mcp_server/` (~7-line diff chosen over ~800 LOC), and six
  `spec(reader="search/graph_scoring_stage.py")` tags are enforced by
  `test_config_field_liveness.py::test_reader_files_exist`. Not reopened here.
- **C4 (`CodeGraphStorage` ownership)** — still deferred: it sits on the scoring hot path, and
  centrality normalizes by `max_score`, so any PageRank shift moves the whole corpus across
  `centrality_boost_threshold=0.02` → full canon re-pin.
- **C5 (probe/instrumentation seam) and C6 (`search/config.py` divergent change)** — recovered
  from the original review, neither built here.
- `graph/graph_storage.py:1395 get_graph()` (dead code — zero production callers) and
  `search/graph_view.py:14`'s stale ADR citation (miscites ADR-0001/0005/0006; the real ones are
  ADR-0004/0051) — both one-line fixes, deliberately not bundled into this gate.
