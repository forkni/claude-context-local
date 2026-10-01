# `GraphView` owns every code-graph read outside `graph/`

Status: accepted
Date: 2026-10-01

## Context

`search/graph_view.py` promised that `search/` would not touch `CodeGraphStorage.graph`, but
`call_edge_injection`, `centrality_ranker`, `graph_integration`, `relationship_analyzer`,
`mcp_server/tools/result_view` and `search_handlers` still read it directly (architecture review
candidate 3). Every site was a read; writes already go through storage methods.

## Decision

- `GraphView` gained `node_count`, `node_ids`, `nodes_with_attrs`, `node_attrs`, `edges(rel_type)`
  and `call_edge_confidence`; `EdgeRecord` gained `resolver_confidence`, `key` and `attrs`
  (`key`/`attrs` excluded from equality). Plain `DiGraph` fakes are supported (`key=None`).
- All listed sites route through `GraphView`, using explicit `node_count()`/`contains()` rather
  than truthiness (the `__len__` trap, [ADR-0066](0066-free-synthetic-reorder-from-graph-guard.md)).
- `tests/unit/search/test_graph_view_boundary.py` parses `search/` and `mcp_server/` and fails on
  any `.graph` attribute access outside `graph_view.py`.
- **Not done:** renaming `CodeGraphStorage.graph` to `_graph`. `graph/` and many tests use it;
  the boundary test enforces the rule without that churn. `graph/graph_queries.py` is in the
  graph layer and out of scope.

## Consequences

Pure refactor (`0c7ae7c0`). Same 63q gate as [ADR-0080](0080-hide-faiss-positions-behind-code-index-manager.md):
0 movers, identical aggregate. Live-verified via `search_code` caller/callee hints,
`find_connections` and `find_path`.
