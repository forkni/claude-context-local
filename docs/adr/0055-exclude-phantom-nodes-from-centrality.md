# Exclude phantom placeholder nodes from centrality computation (default off)

Status: accepted

Date: 2026-08-22

## Context

`graph.graph_storage.add_call_edge`/`add_relationship_edge` create a placeholder node for every
unresolved call/symbol target that isn't a real chunk -- e.g. `str`, `int`, `__init__`,
`self.logger`. These "phantom" nodes exist so `find_path` and callee/caller queries can still
traverse through an unresolved reference, but they were never meant to participate in centrality
scoring: a phantom accumulates an incoming edge from every call site that happens to reference the
same bare name, so generic, extremely common names inflate to enormous in-degree with no relation
to how important the *real* chunk on the other end of that call actually is.

Read-only pre-flight against this repo's own index
(`scripts/benchmark/graph_phantom_preflight.py`, `.venv/Scripts/python.exe -m
scripts.benchmark.graph_phantom_preflight --project-name claude-context-local`):

```
Total nodes: 6053   Phantom nodes: 3675 (60.7%)   orphan/degree-0: 0
Top-20 phantom fraction: 75.00%    Max-PageRank node is phantom: True  ("str", 0.0273)
Real chunks clearing threshold=0.02: 17/2378 (0.71%)
```

(Re-run at ADR-write time; a slightly earlier pass during this same review measured 6058 nodes /
2383 real chunks / 19 clearing the threshold — ordinary incremental-reindex substrate drift from
this session's own edits, not a methodology change. The percentages and the qualitative picture
are stable across both measurements.)

Phantoms are 60.7% of all nodes and 75% of the top-20 raw-PageRank nodes; the single highest
PageRank node in the whole graph is the phantom `"str"`. `search/centrality_ranker.py` max-
normalizes every score against the graph's single highest PageRank value before comparing it to
`centrality_boost_threshold` (default `0.02`). With `"str"` as that normalizer, under 1% of real
chunks clear the threshold at all.

### The defect this workstream measured (not fixed by default)

`centrality_bm25_boost` defaults `True` (`search/config.py`) and is centrality's only live
consumer -- `centrality_alpha` is `0.0`, so the blend path contributes nothing. Live verification
via `search_code` against the current index confirmed the 0.8% that *does* clear the gate is not a
random sample: it is systematically the generic, high-fan-in utility methods that accumulate call
edges by being generic, not by being semantically important --

| chunk | centrality | reranker_score | blended_score |
|---|---|---|---|
| `search/symbol_cache.py:get` | 0.1049 | -0.1376 | **+0.0132** |
| `embeddings/chunk_cache.py:get` | 0.0942 | -0.1438 | **+0.0132** |
| `search/metadata.py:get` | 0.0868 | -0.1007 | **+0.066** |
| `search/metadata.py:set` | 0.0434 | -0.1265 | **+0.0264** |
| `search/faiss_index.py:add` | 0.0258 | -0.0965 | **+0.0383** |

Each sits at `min(centrality * boost_factor, boost_cap)` (`5.0`/`0.15`), i.e. pinned at the cap.
So the boost is not dormant -- it fires for ~0.8% of the corpus, and that 0.8% is precisely the
set of low-information `get`/`set`/`add` helpers, promoted over semantically better matches for
the query. This is a real, live defect in the shipped defaults. It predates this workstream; this
workstream is the first to measure and name it.

## Decision

Ship two independent, narrowly-scoped mechanisms, both aimed at the phantom-node problem from
different angles, and keep the actual centrality-scoring behavior default-off pending a
pre-registered A/B:

**Workstream D -- `CodeGraphStorage.prune_orphan_symbol_nodes()`.** Removes phantom nodes that
have dropped to degree 0 (no incident edges in either direction), wired into
`search/incremental_indexer.py::_remove_old_chunks`, run immediately after the
`remove_file_nodes` loop in the same incremental pass. `remove_file_nodes` matches by
`node_id.startswith(f"{path}:")` and can never reach a phantom (bare symbol name, no `path:`
prefix); without this, a phantom whose only referents were all deleted survives indefinitely
across incremental reindexes. A from-scratch index via `Indexer.clear()` is unaffected -- the
whole graph, phantoms included, is discarded together.

This is pruning, not filtering: it only removes nodes that are already unreachable garbage. It has
no effect on the phantoms that matter for the defect above, which are exactly the ones with high
in-degree -- provably a no-op on this repo's own index (`orphan/degree-0: 0`). It exists as
insurance against unbounded accumulation on long-lived incrementally-reindexed projects, not as a
fix for the centrality-quality defect.

**Workstream E -- `GraphEnhancedConfig.centrality_exclude_phantoms`.** Excludes phantom nodes from
the centrality computation itself, across all four centrality methods, via a read-only
`graph.subgraph(...)` view in `graph/graph_queries.py` that never mutates the stored graph. This is
the mechanism that actually addresses the defect above: with phantoms excluded, the normalizer is
the highest-PageRank *real* chunk instead of `"str"`.

Ships **default `False`** and listed in `FORBIDDEN_AUTO_TUNE_KEYS` (`search/index_probe.py`) --
not because the mechanism is unsafe, but because flipping it is not a drop-in fix. Excluding
phantoms changes what the normalizer is: the current top real chunk
(`search/symbol_cache.py:get`, centrality 0.1049 normalized, raw PageRank ~0.0029) becomes the new
denominator, so most of the corpus would newly clear `centrality_boost_threshold=0.02` -- the
"almost nothing gets boosted" failure mode would flip to "almost everything gets boosted", a
different failure mode, not a fix. An A/B that only flips the flag without re-tuning
`centrality_boost_threshold` inside the same arm would not be a fair test of the mechanism.

### Declined: flip `centrality_exclude_phantoms` to default `True` now

Rejected for the reason above -- it trades one untested failure mode for another, unmeasured one,
with no A/B evidence either direction. Also declined: turning `centrality_bm25_boost` off
entirely as a cheaper first move, since it may be recall-neutral and would let the whole mechanism
be retired instead of repaired -- plausible, but likewise unmeasured. Both remain open reopening
conditions (see Consequences).

### Declined: a global phantom purge (delete every phantom node outright)

Would break `find_path`, which deliberately routes through symbol-name nodes to represent
unresolved-but-plausible call chains (`graph/graph_queries.py`). Phantoms are legitimate graph
structure for traversal; they are only wrong as centrality-scoring input.

## Consequences

- **`prune_orphan_symbol_nodes` ships wired and tested, currently a no-op on this repo's index**
  (0 orphan phantoms) but insurance against future incremental-only accumulation.
- **`centrality_exclude_phantoms` ships default `False`; the defect it targets stays live** in
  shipped defaults until the A/B below runs. Not a regression introduced by this ADR -- the defect
  predates it and was previously unmeasured.
- **Reopening condition:** run the pre-registered A/B, both golden sets, two rounds per arm, gated
  on recall@10/recall@20 (project convention, not MRR), sweeping `centrality_boost_threshold`
  *inside* the treatment arm rather than flipping the flag alone. Until that lands, do not hand-tune
  `centrality_exclude_phantoms` -- it stays in `FORBIDDEN_AUTO_TUNE_KEYS`.
- **Cheaper alternative reopening condition, not yet tried:** measure `centrality_bm25_boost=False`
  in isolation first. If recall-neutral, the whole boost mechanism can be retired rather than
  repaired, which is a smaller change than re-normalizing centrality.
- The phantom-node predicate (`NODE_ATTR_TYPE == NODE_TYPE_SYMBOL_NAME or NODE_ATTR_IS_TARGET_NAME`)
  is now defined once, in `graph.schema.is_phantom_node`, and imported at all four sites that
  previously duplicated it inline (`graph/graph_queries.py`, `graph/graph_storage.py`,
  `scripts/benchmark/graph_phantom_preflight.py`, `scripts/benchmark/analyze_chunking_corpus.py`).
  `tests/unit/graph/test_schema.py::TestIsPhantomNodeSingleDefinition` gates all four staying in
  sync.
