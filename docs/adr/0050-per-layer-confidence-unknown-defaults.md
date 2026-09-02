# Decline a shared policy object for the four `resolver_confidence`-unknown defaults

Status: accepted
Date: 2026-08-20

## Context

An architecture review (candidate 8, `/improve-codebase-architecture`) proposed a shared
"policy object" so four sites that each default a missing `resolver_confidence` to a
different constant would agree on one. The sites:

| Site | Question it answers | Needs unknown to be… | Default |
|---|---|---|---|
| `graph/graph_storage.py:705-720` `_edge_confidence` (via `edge_confidence()`, `:60-107`) | **filter** — survive `min_traversal_confidence`? | ≥ every real float | `1.0` |
| `graph/graph_storage.py:942-944` `_primary_key` | **selection** — which parallel edge represents this pair? | ≤ every real float | `0.0` |
| `search/relationship_analyzer.py:220,226` | **dedup + ordering** among legacy AST peers | mid-pack | `0.5` |
| `mcp_server/tools/result_view.py:485` (`_enrich_results_with_top_callers`) | **ordering** within an already-tiered hint list | ≤ every real float | `0.0` |

The review's premise was that this divergence is accidental duplication. It is not: the
first two rows have **mathematically contradictory** requirements — a filter that must
never silently prune wants the missing case to look like the *most* trustworthy edge
(`1.0`, permissive); a tie-break that must not let an unscored edge win a real one wants
the opposite (`0.0`). No single constant satisfies both, so a policy object returning one
number would be wrong by construction. A policy object returning three or four named
numbers is the status quo plus a layer of indirection with no behaviour change and one
more place to keep in sync.

The *algorithm* these sites would need to share already exists:
`graph/graph_storage.py:60-107`'s `edge_confidence()` centralizes the
float → legacy-string-tag → `calls`-edge-default ladder and returns `None` for "no signal
at all," deliberately deferring the risk tolerance for that `None` case to each caller. This
is [ADR-0042](0042-publish-invariants-not-values.md)'s accepted principle applied one layer
down: publish the shared *invariant* (the resolution ladder), never the *value* (what a
caller should do when the ladder bottoms out at `None`) — because the right value is a
property of what the caller is doing with the number (filter vs. tie-break vs. display
ordering), not of the number's provenance.

Only one site — `_edge_confidence` — calls `edge_confidence()` directly.
`relationship_analyzer.py` and `result_view.py` don't route through it, and per the live
call graph (`find_connections` on `edge_confidence`, 2026-08-20) neither module appears in
its 3-file callee graph at all — the separation is real, not just documented.

The review also cited the confidence-default inversion fixed in `020f223` (2026-08-16,
`evaluation/CONFIDENCE_EGO_AB_20260816.md`) as evidence the divergence is a source of bugs.
That fix was a **single-site** error — one call site read the wrong tier of an already-
correct ladder — not a divergence error, and the fix deliberately *preserved* the
per-layer divergence rather than collapsing it. It is not evidence for this candidate.

## Decision

Decline the shared policy object. Keep the four defaults exactly where they are, each
justified by the question its site answers. `edge_confidence()` remains the one shared
piece: the resolution ladder, not the unknown-case value.

Two related knobs are **not** part of this shared-object discussion, despite touching the
same word "confidence" — they gate different things entirely:

- `CallGraphConfig.min_confidence` (`search/config.py:1579`) — a **build-time injection
  floor**: resolver edges below this confidence are never written into the graph at all.
- `GraphEnhancedConfig.min_traversal_confidence` (`search/config.py:1272`) — a **query-time
  traversal floor**: written edges below this confidence are skipped during `get_neighbors`
  BFS, independent of `_edge_confidence`'s unknown-case default.

Both are orthogonal gates over already-resolved confidence values, not additional instances
of the unknown-default question this ADR is about.

## Consequences

- No code changes from this decision alone; it exists so future architecture reviews stop
  re-flagging this divergence as an oversight.
- `graph/graph_storage.py:60-107`'s docstring was corrected in the same round (not by this
  decision) to fix two stale/incorrect claims: the dangling `result_view.py:275` line
  reference (real site is `_enrich_results_with_top_callers`, per
  [ADR-0043](0043-point-stale-prose-counts-at-derived-source.md)'s symbol-anchor pattern),
  and the false claim that `relationship_analyzer.py` reads from "already-decayed display
  dicts" — it reads raw `edge_data`, and the real reason it doesn't fold the string tag into
  the float is that the tag is surfaced separately as `d["confidence"]`, so folding it in
  would double-count it and shift `exact`-tagged edges from `0.5` to `0.7`.
- ~12 tests pin the four defaults by name
  (`tests/unit/graph/test_graph_storage_get_neighbors.py:624-650,813-821`,
  `tests/unit/search/test_relationship_analyzer.py:630-638`,
  `tests/unit/mcp_server/test_graph_enrichment.py:279,405-431` — the last pins *tier over
  float* precedence, which a numeric-only policy object would have needed to special-case
  anyway). None of them move.

## Out of scope

- Changing any of the four default values — none is a bug, each answers a different
  question correctly for its site.
- `CallGraphConfig.min_confidence` / `GraphEnhancedConfig.min_traversal_confidence` — real,
  separate, already-shared-via-config gates; nothing about them changes here.
