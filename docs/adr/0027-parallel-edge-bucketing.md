# Parallel edges carry through `find_connections` instead of collapsing to one primary type

Status: accepted
Date: 2026-08-04

## Context

`CodeGraphStorage.get_edge_data(u, v)` collapses a `(u, v)` pair on the underlying
`MultiDiGraph` — which can carry one edge per relationship type between the same two nodes — down
to a single **primary** edge, selected by `(resolver_confidence, is_calls)` with `calls` winning
ties. `GraphQueryEngine._traverse_inbound`/`_traverse_outbound` both called this method with no
`relationship_type`, so every `RelationshipEntry` they produced carried only that one primary
type. This was a documented, unfixed defect: a `KNOWN LIMITATION` docstring on `get_edge_data`
(`graph/graph_storage.py:750-762`) and on both traversals (`graph_queries.py:604-606`, `:664-671`)
named the exact repro — an `implements` edge to a base class shadowed by a `uses_constant` edge to
the same target, which happens whenever the base class's name is ALL_CAPS (e.g. `abc.ABC`, which
`ConstantExtractor` also treats as a constant reference).

Verification corrected two premises an earlier review draft got wrong:

- **The loss is not confined to filtered calls.** `analyze_impact` (`search/relationship_analyzer.py`)
  never passes `relation_types` into `get_relationships` — the call at `:112`/`:138` is bare, and
  `relationship_types` is applied later, at `:157`, to already-bucketed output via `_filter_by_types`.
  The discard therefore happens during bucketing in `_build_graph_relationships`, on the
  **unfiltered** path every `find_connections` call takes — a filter-only fix could not have
  reached it.
- **`get_edge_data` has five callers, not two.** `_traverse_inbound`, `_traverse_outbound`,
  `_build_path_result` (via `find_path`), `find_related_functions` (zero-caller dead code), and
  `_should_exclude_edge` — which already calls the keyed form (`graph_storage.py:677-679`), an
  in-repo precedent for threading a type through. `get_neighbors`/the ego-graph path is unaffected:
  `_iter_matching_neighbors` enumerates `out_edges`/`in_edges` directly and never goes through
  `get_edge_data`.

The relationship-type-to-bucket-key mapping (`chunking/relationships/relationship_types.py`)
already defines a forward/reverse field pair per type — `implements` →
`(implements_protocols, protocol_implementations)`, `uses_constant` →
`(uses_constants, constant_usages)`, and so on — populated straight from each entry's
`relationship_type`. Whichever type won the primary-edge selection was therefore the only type
ever visible in any bucket, for every relationship-bearing node pair with more than one edge type
between them.

## Decision

> The entry carries every parallel edge; the analyzer buckets from all of them, not just the one
> the entry happens to be labeled with.

- `RelationshipEntry` gains `parallel_edges: list[dict[str, Any]]`, populated by both traversals
  from the previously-orphaned `CodeGraphStorage.get_all_edge_data(u, v)` — zero callers before
  this fix, and already returning one fully-normalized dict per relationship type on the pair.
- A new `GraphQueryEngine._resolve_entry_type` staticmethod decides, per `(u, v)`, whether to
  report the pair and which type the entry's own `.relationship_type` carries:
  - `relation_types=None`: report unconditionally, keep the primary type — byte-identical to
    pre-fix selection.
  - `relation_types` given: report if **any** parallel edge's type matches the filter, even a
    non-primary one; ties among matching types are broken by sorted type name, replacing
    extractor-registry insertion order on this path only.
- `_build_graph_relationships` (`search/relationship_analyzer.py`) fans out over
  `entry.parallel_edges` through a `_fanout` helper — one `dataclasses.replace`d copy of the entry
  per parallel edge type — before bucketing, instead of reading `entry.relationship_type` once.
  Falls back to `[entry]` when `parallel_edges` is empty (hand-built test fixtures that don't
  populate it). This is the step that lets `implements_protocols` and `uses_constants` (or any
  other bucket pair) receive the same target node at the same time.
- `get_edge_data` keeps its exact primary-selection contract and docstring — `_build_path_result`
  and `_should_exclude_edge` still want one representative edge. It stops being the only thing the
  two traversals see.

### Why cardinality stays safe (the `calls`-always-wins proof)

Unfiltered cardinality is unchanged by construction: `_resolve_entry_type` reports unconditionally
and keeps the primary type when `relation_types is None`, so the entry list `_dedup_and_sort_edges`
consumes — and every field derived from it, `direct_callers`, `direct_callees`,
`indirect_callers`, `total_impacted`, `dependency_graph` — is byte-identical to pre-fix. Only the
`relationships` buckets change, and only by gaining rows that were being silently dropped.

`direct_callers`/`direct_callees`/`calls_outbound` specifically cannot be under-counted by the
fan-out: `resolver_confidence` is written in exactly one place
(`search/call_edge_injection.py:183/197`) and only onto `calls` edges; every other type defaults
to `0.0`, and `get_edge_data`'s primary-selection key is `(resolver_confidence, is_calls)` — so a
`calls` edge always wins the primary whenever one exists, ties included. There is no scenario
where a `calls` edge was the shadowed, non-primary type this fix needed to recover.

### Rejected alternatives

- **Analyzer-side re-querying** instead of threading `parallel_edges` through the entry: the other
  endpoint of a depth-1 entry is a `_node_variants` expansion of the origin, and at depth > 1 it is
  an unrecorded intermediate node — not reconstructible above depth 1, and it would duplicate the
  traversal's own graph walk (`graph_queries.py:569-585`) a second time from the analyzer.
- **Emitting one full `RelationshipEntry` per parallel edge type at traversal time** (growing the
  entry list itself, at depth 1): this would force the `reported` per-node dedup set (issue #23's
  invariant) to be re-keyed by `(node, type)` and a depth-1-only special case into both traversals,
  for no cardinality gain the `parallel_edges` fan-out doesn't already provide — the
  `calls`-always-primary proof above means there is no under-counted edge left to recover that way.

Retired the three now-stale `KNOWN LIMITATION` docstrings (`get_edge_data`, both traversals) in the
same commit, describing the new contract instead of the old bug. Left `get_edge_data`'s
primary-collapse *description* intact — the method keeps that contract by design.

## Consequences

- `find_connections`'s unfiltered `relationships` output can now show the same target node in more
  than one bucket simultaneously — this is the fix, not a regression, but any downstream reader
  that assumed "one relationship per node pair" needs to stop assuming that.
- `get_all_edge_data` stops being a zero-caller orphan.
- Filtered `relationship_types=[...]` queries can now report a node that would previously have been
  silently dropped; cardinality can only grow on this path, never shrink.
- Deterministic tiebreak (sorted type name) on the filtered path replaces extractor-registry
  insertion order — a query for `relationship_types=["implements", "uses_constant"]` against a pair
  carrying only those two parallel types will consistently label the entry `implements`
  (alphabetically first), not whichever extractor happened to run first in
  `chunking/relationships/relationship_extractors/registry.py`'s priority list.

## Verification

- New unit tests (`tests/unit/graph/test_graph_queries_relationships.py`,
  `tests/unit/graph/test_graph_storage.py`,
  `tests/unit/mcp_server/test_code_relationship_analyzer.py`) build a graph fixture with parallel
  `implements` + `uses_constant` edges between the same pair and assert: (a) the unfiltered path
  surfaces the node in both `relationships` buckets while `direct_callers`/`direct_callees`/
  `total_impacted` are unchanged; (b) a `relationship_types=["implements"]` call returns the node
  instead of dropping it; (c) `get_relationships(relation_types=None)`'s entry list is unchanged in
  length and `relationship_type` values; (d) `get_all_edge_data` is exercised.
- **Live MCP verification against a genuine, non-synthetic instance** in this project's own
  indexed source: `chunking/languages/base.py:113-1260:class:LanguageChunker`, whose base class is
  `abc.ABC` — reached by both an `implements` edge (from subclassing `ABC`) and a `uses_constant`
  edge (from `ConstantExtractor` treating the ALL_CAPS `ABC` as a constant reference), the exact
  repro the original `KNOWN LIMITATION` docstring named. An unfiltered `find_connections` call
  returns `ABC` in both `implements_protocols` and `uses_constants` simultaneously
  (`"note":"External or builtin type (not in index)","resolvable":false` on both, consistent with
  `abc.ABC` being an unindexed stdlib symbol); `direct_callers`/`direct_callees`/`total_impacted`
  (98)/`file_count` (46) are identical between that call and a
  `relationship_types=["implements"]`-filtered call against the same chunk, and the filtered call
  still returns the node rather than dropping it.
- Full unit suite green; `check_lint.sh --modified-only` clean.

## Out of scope

- Threading `relation_types` all the way into a keyed `get_edge_data()` call per candidate type
  (the fix direction the pre-fix docstring speculated about) — the `parallel_edges`/fan-out shape
  reaches the same result without adding a per-type keyed lookup on the hot traversal path.
- Any change to `get_edge_data`'s primary-edge selection contract, `resolver_confidence`
  semantics, or the `calls`-edge injection pipeline (`search/call_edge_injection.py`).
- `find_related_functions` (`graph_queries.py`, zero callers) — left as dead code, not touched or
  removed by this fix.
