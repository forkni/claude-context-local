# Delete `GraphScoringStage`'s upward `mcp_server` import instead of moving the class

Status: accepted
Date: 2026-08-20

## Context

An architecture review (candidate 4, `/improve-codebase-architecture`) flagged
`search/graph_scoring_stage.py`'s function-scoped `from
mcp_server.tools.searcher_view import SearcherView` (former `:158-162`) as an
[ADR-0004](0004-scoped-tracing-only-observability.md) layering violation:
*"`mcp_server/` code cannot be imported by `search/` code (that would invert the
layering)."* The class docstring's own claim — that the graph-scoring seam sits
"entirely within `search/`" — was false while this import existed.

The review's proposed fix was **Move Class**: relocate `GraphScoringStage` up into
`mcp_server/`. Verification against the live tree showed that fix would have been
disproportionate to the violation:

- The import buys exactly one thing: `SearcherView(searcher).is_hybrid`, a lazy
  `isinstance(self._s, HybridSearcher)` check (`mcp_server/tools/searcher_view.py:84-97`).
  `SearcherView` itself has zero `mcp_server`-specific dependencies — it is a thin
  `search`-layer concept that happens to live one directory up.
- The check is **redundant**. The full guard in `_inject_ego_centrality` was:

  ```python
  if (
      SearcherView(searcher).is_hybrid
      and hasattr(searcher, "ego_graph_retriever")
      and searcher.ego_graph_retriever is not None
      and centrality_scores
  ):
  ```

  `ego_graph_retriever` is assigned only in `search/hybrid_searcher.py:289,309,321`. No
  other searcher class defines it — `IntelligentSearcher` (`search/searcher.py`) has no
  such attribute. So clauses 2–3 already imply clause 1 for every real searcher; clause 1
  only ever matters for a bare `Mock()` in tests, where it happened to suppress injection
  as a side effect rather than by design.
- Live call-graph evidence (`find_connections`, 2026-08-20) confirmed the blast radius of
  removing the check is one method: `_inject_ego_centrality`'s only caller is
  `GraphScoringStage._apply_centrality`. `EgoGraphRetriever.set_centrality_scores`'s three
  direct callers (`EgoGraphRetriever._rank_neighbor`, `GraphScoringStage._inject_ego_centrality`,
  `HybridSearcher.clear_index`) are all `HybridSearcher`-reachable; `IntelligentSearcher`
  appears nowhere in that graph.
- The upward import only became upward as collateral of ADR-0030 Phase 2, which converted
  a *downward* `search.hybrid_searcher` import into a `SearcherView.is_hybrid` call during
  an `mcp_server/`-scoped cleanup — it was never a deliberate design choice for this class.

Moving `GraphScoringStage` would have legalized the violation at roughly 50x the blast
radius of removing it: 1 module (323 LOC) + 1 test file (492 LOC) + 6
`spec(reader="search/graph_scoring_stage.py")` tags in `search/config.py` (guarded by
`tests/unit/search/test_config_field_liveness.py::test_reader_files_exist`) + 3 live
golden-dataset chunk_ids in `evaluation/golden_dataset_expanded.json` + roughly 18
draft/candidate golden entries + the `CONTEXT.md` entry defining the graph-scoring seam as
`search/`-resident. It would also have contradicted `CONTEXT.md`'s own definition of the
term it was supposedly fixing.

## Decision

Delete the `SearcherView` import and the `is_hybrid` clause. Collapse the guard to:

```python
if (
    getattr(searcher, "ego_graph_retriever", None) is not None
    and centrality_scores
):
```

This is behaviour-identical for every real searcher (`HybridSearcher` is the only class
that ever sets `ego_graph_retriever`) and discharges the ADR-0004 violation with a ~7-line
diff in one file, rather than a ~800+ LOC relocation.

`SearcherView.is_hybrid` is not orphaned by this change — it has a separate, live caller in
`mcp_server/tools/search_orchestrator.py`'s `SearchOrchestrator._search`, which needs it for
`build_effective_config` (consistent with ADR-0048's note that `is_hybrid` stays live after
Block D's dispatch conditional was removed).

### Declined alternative: move `SearcherView` down into `search/`

`SearcherView` has zero `mcp_server`-specific dependencies, so moving it down into `search/`
was a coherent second option — it would have let `graph_scoring_stage.py` keep an
`is_hybrid` check via a downward import instead of deleting the check outright. Declined
because it touches 6 call sites plus the `tests/unit/mcp_server/test_searcher_view_ownership.py`
ownership gate, and is unnecessary once the redundant check is gone — there is no remaining
caller in `search/` that needs `is_hybrid` at all.

### Declined fallback: downward `isinstance(searcher, HybridSearcher)`

A smaller, more conservative fix — replace the upward `SearcherView` import with a
function-scoped `from search.hybrid_searcher import HybridSearcher` and an `isinstance`
check — would also have discharged the ADR-0004 violation (a downward import is fine) at
the cost of reintroducing an isinstance check the call graph shows is unnecessary. Not
needed: the guard collapse alone was sufficient and the file-scoped test suite (27/27,
including two new tests pinning the surviving guard) and the full unit suite (6142
passed, 1 skipped) both stayed green.

## Consequences

- `search/graph_scoring_stage.py`'s class docstring claim — the graph-scoring seam sits
  "entirely within `search/`" — is now true rather than aspirational.
- `^\s*(from|import)\s+mcp_server` under `search/` drops from 8 sites to 7 (the remaining
  7 — 5 in `incremental_indexer.py`, 1 in `search_executor.py:468`, 1
  `TYPE_CHECKING`-only in `effective_config.py:21` — are out of scope for this ADR).
- Two new tests pin the surviving guard directly:
  `test_inject_ego_centrality_skips_searcher_without_ego_graph_retriever` and
  `test_inject_ego_centrality_calls_set_centrality_scores_when_present`
  (`tests/unit/search/test_graph_scoring_stage.py`). These matter because the change is a
  real shift in test-time reachability, not just a style cleanup: `SearcherView(Mock()).is_hybrid`
  was `False` for every bare `Mock()` searcher in the suite, so injection previously
  short-circuited on clause 1 for all of them; after the collapse,
  `getattr(Mock(), "ego_graph_retriever", None)` is a truthy `Mock` unless the mock is
  constructed with `spec=[]`, so `set_centrality_scores` can now fire on mocks that
  previously skipped it. Harmless in production (no real searcher lacks the guard's
  invariant), but worth asserting rather than assuming.
- No benchmark re-run was performed. The change is behaviour-identical for every real
  searcher (proven by the `set_centrality_scores` call graph — three callers, all
  `HybridSearcher`-reachable, no `IntelligentSearcher` path), and the deployed benchmark
  noise band (±0.02, bf16/cuBLAS) could not distinguish "no change" from noise even if one
  were run.

## Out of scope

- Moving `SearcherView` down into `search/` — declined above; no live need once the
  redundant check is deleted.
- The other 7 `search/ -> mcp_server` import sites — none are ADR-0004 violations
  introduced or touched by this change; they were not part of the reviewed candidate.
