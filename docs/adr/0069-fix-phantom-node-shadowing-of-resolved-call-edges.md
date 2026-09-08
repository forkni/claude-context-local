# Fix phantom-node shadowing of resolved call edges (D1 + D2)

Status: accepted
Date: 2026-09-08

## Context

While verifying Phase 4 of the Rust call-graph plan (chunking/extraction/resolution walls landed,
uncommitted, on `openheizenberg`), a live end-to-end `find_connections` check on `UndoStack::push`
returned 72 callers, against hand-verified ground truth of exactly 2. None were hidden by
`hide_ambiguous`, and all 72 landed in the `"exact"` bucket of `caller_confidence` — their
`confidence` field carrying the literal float `1.0` rather than a tag. The Rust plan's precision
gate ("≥ 0.85 strict on default-visible edges, `confidence == "exact"`") was unmeasurable as a
result, blocking Phase 4.

Tracing it found the Rust work was not the cause. The raw graph on disk was correct — all 72 edges
carried `confidence: "ambiguous"` — so ADR-0060's `downgrade_method_confidence` worked exactly as
designed at index time. The tag was destroyed at **query** time by a pre-existing, language-agnostic
defect in shared code: `graph/graph_queries.py`, `graph/graph_storage.py`, and
`search/relationship_analyzer.py` were all unmodified in the working tree, and the bug reproduced
on the pure-Python self-index at HEAD.

## The defect

Every call site writes **two** edges into the `MultiDiGraph`:

| # | edge | attrs |
| --- | --- | --- |
| a | `caller_chunk_id → resolved_callee_chunk_id` | `is_resolved: True`, `confidence: "exact"` / `"ambiguous"` |
| b | `caller_chunk_id → "<bare_symbol_name>"` (phantom node) | `is_resolved: False`, no `confidence` key at all |

`_node_variants()` expands a query into `[chunk_id, "Class.name", "name"]`. `_traverse_inbound`/
`_traverse_outbound` iterated those variants out of a `set` (arbitrary order) and deduped results
with `reported`, keyed on the caller — identical for edges (a) and (b). First-visit-wins: when the
phantom node won, `get_edge_data` found no `confidence` key and defaulted it to float `1.0`;
`_enrich_callers` treated the truthy float as passing through, then `1.0 != "ambiguous"` bucketed it
as `"exact"`; `filter_ambiguous_edges` keys on the literal string `"ambiguous"`, so the lost tag was
invisible to it and the edge could not be hidden.

Two separable sub-defects:

- **D1 — shadowing.** The phantom edge discards the resolved edge's data; an ambiguous tag becomes
  exact.
- **D2 — untagged phantoms.** A genuinely unresolved phantom-only edge has no confidence signal at
  all, yet was presented as a high-confidence `"exact"` caller.

ADR-0060 made this materially worse for C/C++ (it retags every C-family method edge `"ambiguous"`
and relies entirely on the display filter to hide them). Measured blast radius before the fix:
Python self-index 1,362/3,502 (38.9%) ambiguous tags lost to shadowing; Rust `openheizenberg`
2,169/2,169 (100%).

## Decision

### D1 — authority-first traversal order (`graph/graph_queries.py`)

Added `GraphQueryEngine._authority_order()`: a deterministic, authority-first sort — real chunk
nodes before phantom symbol-name nodes, then lexicographic — reusing the single sanctioned
`is_phantom_node` predicate from `graph/schema.py`. Applied at both `_traverse_inbound`'s and
`_traverse_outbound`'s loop heads, so the resolved edge (carrying the real confidence tag) always
wins the first-visit dedup.

This does not stop querying symbol-name variants — only reorders them; `_node_variants` and
`origin_set` are untouched. Phantoms are **reordered, not deleted**: ADR-0055 explicitly declined a
global phantom purge because `find_path` routes through symbol-name nodes on purpose, and
`prune_orphan_symbol_nodes` only removes degree-0 phantoms — a shadowing phantom (degree ≥ 1) could
never be pruned anyway. The sort also incidentally makes traversal output order deterministic (it
was previously hash-order-dependent).

### D2 — tag unresolved phantom call edges (`graph/graph_storage.py`)

Narrowed `get_edge_data`'s blanket `1.0` default: an untagged `calls` edge with
`is_resolved is False` now defaults to `"ambiguous"` instead of `1.0` — identical to the value
`edge_confidence()` (the raw-attribute resolver used by `TraversalPolicy`) already assigns an
untagged `calls` edge, so this is the *display* layer catching up to a policy value that already
existed, not a new opinion. Resolved-but-untagged edges (`is_resolved=True`, no confidence key —
legitimately high-tier-resolver edges) and non-`calls` edges are unaffected.

**Builtin-call exception, found during implementation.** The index-time edge-creation code in
`search/graph_integration.py` has three paths, not two: (1) unique resolved match — tagged
`"exact"`/`"ambiguous"` already; (2) multiple real candidates — tagged `"ambiguous"` explicitly,
already, at index time; (3) zero project candidates found — `is_resolved=False`, no confidence key.
D2's untagged-phantom population is *only* path 3, but path 3 conflates two different things: a
genuinely unresolvable name, and a confirmed non-project reference (a Python builtin like `len` or
`print` — `_resolve_call_target` checks `hasattr(builtins, callee_name)` before attempting any
resolution and returns `None` specifically to produce a phantom edge for these). A builtin-target
phantom edge is not an unresolved *project* reference, so D2 excludes it via
`hasattr(builtins, callee_id)` (exact, not heuristic — `callee_id` for this edge shape is always the
bare symbol name) and leaves it at the `1.0` default.

This exception is scoped to Python builtins only, via the stdlib `builtins` module — zero
import-cycle risk. It deliberately does **not** extend to the C-family/Rust common-member
blocklists (`_C_FAMILY_COMMON_MEMBERS`, `_RUST_COMMON_MEMBERS`) or the cross-language
`_COMMON_METHODS` set: those live in `search/graph_integration.py`, a layer above `graph/`, and
importing them into `graph_storage.py` would invert that dependency. Left as a documented scope
boundary for future work, not an oversight — no test currently pins that broader distinction.

## Verification

- New regression tests: a two-insertion-order `MultiDiGraph` case in
  `tests/unit/graph/test_graph_queries_relationships.py` pinning D1 under both node-insertion
  orders; four new cases in `tests/unit/graph/test_graph_storage.py` pinning D2 (unresolved phantom
  → `"ambiguous"`; resolved-but-untagged → `1.0`; `is_resolved` absent → `1.0`; non-`calls`
  untagged → `1.0`) plus the builtin-exception case
  (`test_get_edge_data_untagged_unresolved_call_to_python_builtin_stays_1_0`); an end-to-end
  `filter_ambiguous_edges` assertion in `tests/unit/search/test_relationship_analyzer.py`. All
  pre-existing load-bearing guards stayed green:
  `test_python_class_still_finds_callers_via_symbol_variant`,
  `test_float_confidence_relationship_buckets_untouched`, `TestIsPhantomNodeSingleDefinition`.
- Full suites: `tests/unit/` 4,691 passed / 2 skipped / 0 failed;
  `tests/fast_integration/` 108 passed / 0 failed (up from 107 passed / 1 failed — the fix flipped
  `TestBuiltinFalsePositiveGuard::test_builtin_call_stays_phantom_not_ambiguous` to green with no
  other regressions, including all 6 `test_rust_call_graph_resolution.py` cases).
- Live substrate check (self-index, direct storage read, no MCP): of 3,348 raw
  `confidence == "ambiguous"` edges, 0 leaked to a different value via `get_relationships` in either
  traversal direction (was up to 38.9% before the fix). Of 9,326 raw untagged phantom `calls` edges,
  7,018 correctly downgraded to `"ambiguous"` and 2,308 correctly kept at `1.0` via the builtin
  exception (sample of excepted targets: `len`, `next`, `range`, `sum`, `any`, `bytes`,
  `frozenset`, `bytearray`, `min`, `repr`).
- Live MCP spot-checks: `find_connections("UndoStack::push")` on `openheizenberg` now reports 2
  default-visible `"exact"` callers (matching hand-verified ground truth) plus 69 correctly hidden
  `"ambiguous"` ones (`caller_confidence: {"exact": 3, "ambiguous": 69}` pre-filter — the third
  `"exact"` is a pre-existing resolved-but-untagged test-file caller, unrelated to D1/D2). On the
  Python self-index, `MetadataStore.get` (a common short method name with heavy call-site
  collision) now shows only 3 default-visible callers (all `"exact"`) against a pre-filter total of
  `{"exact": 3, "ambiguous": 386}` — before the fix all 389 would have surfaced as `"exact"`.
- Golden-canon re-pin: `evaluation/CANON_20260908_REBASELINE.md`. Full force reindex (235 files /
  2,978 chunks), all three views gate PASSED vs the 09-07 pin (63q ΔMRR +0.0013/Δrecall@20 +0.0063;
  133q ΔMRR +0.0034/Δrecall@20 +0.0174; F-via-similar ΔMRR +0.0014/Δrecall@20 −0.0066 — all inside
  ±0.02, recall@20 ≥ −0.02), 63q determinism bit-identical across two rounds.

## Consequences

- `find_connections`'s `hide_ambiguous_edges_default=True` (shipped 2026-08-16) now does what it
  claims. This **retroactively qualifies the 2026-08-16 `hide_ambiguous` A/B**
  (`evaluation/CONFIDENCE_EGO_AB_20260816.md`): its measured precision gains (0.4051→0.4082,
  0.2648→0.4014) were taken while up to 38.9% of ambiguous tags on the Python substrate (100% on
  Rust) were silently shadowed to `"exact"` and therefore never eligible to be hidden in the first
  place. The qualitative direction of that A/B is not disputed by this fix, but its precision
  numerator was measured against a smaller effective ambiguous-edge population than the graph
  actually contained.
- Any future precision gate keyed on `confidence == "exact"` (e.g. the Rust Phase 4 hand-labeled
  sample, `evaluation/CPP_CALLGRAPH_PRECISION_SAMPLE_20260903.md`'s successor) is now measuring what
  it claims to measure.
- `evaluation/CANON_20260908_REBASELINE.md` supersedes `CANON_20260907_REBASELINE.md` as current
  canon.
- Traversal output order is now deterministic where it previously depended on Python's set-iteration
  hash order.

## Out of scope

- Extending D2's builtin exception to the C-family/Rust common-member sets, or importing them into
  `graph/graph_storage.py` — would invert the `graph/` ← `search/` layering; left as a documented
  boundary, not attempted here.
- The Rust call-graph Phase 4 remaining items (hand-labeled precision sample, `voro-engine`
  blast-radius reindex, full non-incremental reindex of `openheizenberg`, ADR-0070) — this fix was a
  blocking prerequisite for Phase 4's precision gate to be meaningful; Phase 4 itself resumes
  separately.
- The `find_connections(symbol_name=...)` mis-resolution loose end noted against
  `Graph::add_node`/`Lfo::cook` on `openheizenberg` — not the same defect as D1/D2, sidestepped by
  passing `chunk_id` directly, worth its own look later.
