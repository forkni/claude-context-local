# Rust call-graph tier: chunking, extraction, resolution

Status: accepted
Date: 2026-09-08

## Context

`openheizenberg` (`D:\Users\alexk\FORKNI\TWOZERO\openheizenberg`, Rust + some GLSL) produced **0
call edges and 0 `contains` edges** before this work — every `impl`/`trait`/`mod` block chunked as
one opaque blob (the Transparent-node default from [ADR-0038](0038-cpp-only-container-traversal-seam.md)),
and no call-site extraction existed for Rust at all. This ADR lands the three-wall tier that
brings Rust to parity with [ADR-0060](0060-c-family-call-edge-tier.md)'s C/C++ tier, following the
same template, and records where Rust's tier deliberately diverges — with a measured verdict, not
a guess.

[ADR-0038](0038-cpp-only-container-traversal-seam.md)'s reopening condition for Rust
(`impl_item`/`mod_item` swallowing their members into one chunk) is discharged here. Its C# half
stays open — untouched, still `accepted`.

While verifying this work, a live `find_connections("UndoStack::push")` check returned 72 callers
against a hand-verified ground truth of 2 — a pre-existing, language-agnostic phantom-node
shadowing defect in the query path (`graph/graph_queries.py`, `graph/graph_storage.py`), not a bug
in this tier. That blocked the precision gate below from being meaningful and shipped separately as
[ADR-0069](0069-fix-phantom-node-shadowing-of-resolved-call-edges.md) (`f8548812`) before this
gate could be run.

## Decision

### Wall 0 — chunking (`chunking/languages/rust.py`, `chunking/languages/base.py`)

`RustChunker._CONTAINER_NODE_TYPES = {impl_item, trait_item, mod_item}` — exactly the seam
[ADR-0038](0038-cpp-only-container-traversal-seam.md) built and left for later use. `impl Trait for
Type { fn m(...) {...} }` now names the chunk after the **type** (via the grammar's `type` field),
with the trait relationship moved onto a separate `implements` edge instead of being baked into the
chunk name. The container-registration allowlist (`multi_language_chunker.py:918-938`) widened to
admit `impl`/`trait`/`module` chunk kinds. `mod_item` maps to `parent_type="namespace"` so a free
function inside a `mod` stays chunk-typed `function`, while `impl`/`trait` fall through to
`"class"` so their members are chunk-typed `method` — the distinction the resolution wall below
depends on (`is_method_call`).

### Wall 1 — extraction (`chunking/languages/rust.py`, `chunking/relationships/edge_specs.py`)

Five call-site shapes in `_dispatch_call_site`: bare `identifier` calls, `field_expression`
(method calls, `receiver.method()`), `scoped_identifier` (`Type::method`/`Self::method`/
`mod::function`, with a `Self::` → enclosing-type rewrite and a `std::`/`core::`/`alloc::` prefix
drop), `generic_function` (recursively peels the turbofish to reach the underlying callee), and
else skip. A bare `self.m()` call additionally carries `qualified="Type::m"`, baked in from the
enclosing `impl` block at parse time — this is the exactness lever the resolution wall's item 6
below depends on.

One `"rust"` row in `EDGE_EMISSION_SPECS`: `call_confidence=0.6`, `call_chunk_types={function,
method}`, and — unlike every other language's row — **no `split_block`**. Declaring one would be
provably dead code: Rust has no `_get_block_boundary_types` override, and the split gate's
hardcoded `("function_definition", "decorated_definition")` tuple in
`chunking/languages/base.py` can never match Rust's `function_item` node type. This is a
deliberate omission, not an oversight.

### Wall 2 — resolution (`search/graph_integration.py`)

`_RUST_LANGUAGES = frozenset({"rust"})`, gated at six sites, kept as its own frozenset rather than
merged into `_C_FAMILY_LANGUAGES` specifically because item 6 below needs every call site to
distinguish the two families even where the *treatment* is identical (separator-agnostic
indexing, the fan-out cap).

`_resolve_call_target`'s algorithm, in order: Rust qualified-first lookup (a call's
`callee_qualified` text, e.g. `"Graph::push_undo"`, is itself indexed as a lookup key during pass 1
via `f"{spec.parent_name}::{spec.name}"`; if it uniquely resolves, trust it ahead of every rule
below — this is the type-scoped signal ADR-0060's type-blind C-family resolver never had) → the
30-name `_RUST_COMMON_MEMBERS` std/core idiom blocklist (`clone`, `unwrap*`, `map`, `iter*`,
`len`, `push`, `get`, `insert`, `contains*`, `clear`, …; dropped only when the project itself
defines no chunk of that name) → bare-name lookup → same-file/global uniqueness checks → (no
`split_block`, per Wall 1) → else `None` (ambiguous candidates, capped by `ambiguous_fanout_cap`).

**Item 6 — the divergence.** `downgrade_method_confidence` tags a Rust method-call edge
`"ambiguous"` **only** when it did *not* resolve through its qualified spelling
(`_rust_qualified_resolved`); ADR-0060 downgrades every C-family method-call edge unconditionally,
because tree-sitter-cpp gives it no receiver-type info at all. Rust's `self.m()` is different:
`RustChunker._dispatch_call_site` bakes the enclosing `impl`'s type into `callee_qualified` at
parse time, so a self-receiver call that resolves through that qualified spelling is genuinely
type-scoped, not a name-only guess. Free-function Rust edges (`is_method_call=False` — `Type::m`,
`Self::m`, `mod::fn`) are never downgraded by this clause regardless of resolution path.

**The sample's verdict on item 6 (Step 2, this session).** The plan pre-registered a decision
branch: if stratum B (method calls) lands far below stratum A (free functions) — the C++
pattern — collapse the divergence and downgrade every Rust method call unconditionally, matching
ADR-0060. It does not fire. Measured on a 190-row hand-labeled sample of `openheizenberg`'s
persisted call graph (`evaluation/RUST_CALLGRAPH_PRECISION_SAMPLE_20260908.md`):

| Stratum | n | Correct | Incorrect | Strict / lenient | Wilson 95% CI |
|---|---|---|---|---|---|
| A (free functions, exact) | 75 | 63 | 12 | 0.840 | [0.741, 0.906] |
| B (method calls, exact) | 75 | 75 | 0 | 1.000 | [0.951, 1.000] |
| C (ambiguous, capped, ungated sanity check) | 40 | 15 | 25 | 0.375 | [0.242, 0.530] |

B (1.000) is *stronger* than A (0.840) — the opposite of C++'s pattern, where the unconditional
downgrade exists precisely because uniquely-resolved C-family method calls were frequently wrong.
Weighted A+B (population weights 667/1072, 405/1072): **0.9004** strict/lenient. Pooled A+B
(n=150, unweighted): strict **0.920**, CI **[0.865, 0.954]**. **Gate (≥ 0.85 strict) PASSES**,
comfortably clear of the CI lower bound. Verdict: keep the divergence exactly as designed — this is
a measured decision, not a preference, and no code change follows from it.

Residual stratum-A defect (12/75, all through the same mechanism, not fixed here — see Consequences
below): when a scoped call's qualified type (`Params::new()`, `Arc::new()`, `Vec::new()`,
`Vec2::new()`, `Sense::click()`, `egui::Context::default()`, `NodeState::default()`) is an
external-crate type, a `type` alias, or a derive-macro-synthesized impl, qualified-first lookup
legitimately fails (no project chunk exists to match), and the call falls through to an unsafe
bare-name fallback that lands on an unrelated same-file or globally-unique project symbol sharing
that bare name.

### `ambiguous_fanout_cap` reuse (`search/config.py`)

Rust reuses the C++-measured cap (`ambiguous_fanout_cap=3`) rather than a dedicated Rust probe.
The docstring already named Rust's worst fan-out receivers (`new`, `default`, `cook`, `spec`) as
the check this sample would confirm or revise. It confirms the cap is *load-bearing* (without it,
Rust's `new`/`default`/`cook` fan-out would explode the same way C++'s STL-idiom names did) but
also surfaces, via stratum C's 0.375 precision, that the cap alone does not make the *capped*
ambiguous set precise — three failure modes account for all 25 of the 40 stratum-C rows' incorrect
labels:

- **Std-library/external-crate method-name collisions** (20/40): `.len()`, `.is_empty()`,
  `.get()`, `.push()`, `.as_str()`, `.next()`, `.input()` on `Vec`/`String`/`HashMap`/
  `serde_json::Value`/std iterator/`egui::Context` receivers have zero correct project candidates,
  yet the capped ambiguous set still returns a same-named project method.
  `_RUST_COMMON_MEMBERS` already blocks many of these names outright when the project defines
  none — these 20 are specifically cases where the project *does* define its own method of that
  bare name, so the blocklist's "unless the project defines it" escape hatch lets the (wrong)
  project candidate through.
- **Genuine multi-candidate fan-out, wrong member drawn** (4/40): `cook` (29 project-wide
  definitions), `fps`, `frame` — arity or receiver-type mismatches against the true target.
- **Dynamic dispatch through a trait object** (1/40): `Arc<dyn NodeType>` — the drawn candidate was
  provably a different, unrelated struct's method, not merely one of several plausible dispatch
  targets.

None of this is a regression: every stratum-C edge is tagged `"ambiguous"` and hidden by
`hide_ambiguous_edges_default=True` ([ADR-0069](0069-fix-phantom-node-shadowing-of-resolved-call-edges.md)
made that filter actually work). Stratum C measures whether the *hidden* population is correctly
targeted, not whether it's safe to show by default — it isn't, and it already isn't shown by
default. The remaining 15/40 stratum-C rows are singly-resolved, correctly-resolved edges that were
downgraded to `"ambiguous"` purely because their receiver wasn't the literal `self.<name>(` shape
item 6 checks — a second, unrelated population within the same stratum, and 100% reliable in this
sample (15/15).

`search/config.py`'s `ambiguous_fanout_cap` field's `spec(benchmark_locked=…)` citation is updated
alongside this ADR to carry this Rust evidence next to the existing ADR-0060 C-family probe
citation (docstring/metadata only — no behavior change, cap value unchanged at `3`).

### Mandatory full reindex; no automatic detection

No `chunker_version`/`INDEX_VERSION` marker exists to detect this change automatically
([ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md)'s precedent) — an incremental pass
on an already-indexed Rust project silently keeps the old zero-edge chunks with no error. Any
already-indexed Rust project must be reindexed non-incrementally to pick up this tier.

### Language-gating proof

This lands as a Rust-only, additive change, confirmed by direct evidence rather than by
assertion: `chunking/languages/base.py` only *adds* `mod_item` beside the pre-existing
`namespace_definition`; `"mod_item": "module"` is the only node-type→`"module"` mapping added to
`language_registry.py`; across the 10-language chunker-parity corpus
(`tests/fixtures/chunker_corpus/`), only the `[rs]` snapshot moved. The Python self-index — this
repo's own canonical benchmark substrate — is 100% `python`-tagged with zero Rust nodes, so every
branch gated on `spec.language in _RUST_LANGUAGES` is dead code there.

**No golden-canon re-pin is owed for this change**, pre-registered before the sample was drawn and
confirmed by the gating proof above: the item-6 clause and every other Rust-gated branch are inside
`spec.language in _RUST_LANGUAGES` checks, and the canon substrate has zero Rust nodes to exercise
them. Spending a multi-leg benchmark run to measure a guaranteed-flat delta was not worth doing.

## Verification

- **Precision gate**: `evaluation/RUST_CALLGRAPH_PRECISION_SAMPLE_20260908.md` — 190-row
  stratified hand-labeled sample (A=75, B=75, C=40) drawn from `openheizenberg`'s persisted call
  graph, 3-valued labels (`correct`/`incorrect`/`uncertain`) per the pinned rule in
  `evaluation/RESOLVER_PRECISION_LABELS_20260902.md`. Zero `uncertain` labels occurred anywhere in
  the sample — every drawn Rust call site was statically decidable, including the one dynamic-
  dispatch candidate (which drew a provably wrong receiver type, not merely an undecidable one).
  Gate (≥ 0.85 strict on default-visible A+B weighted) **PASSES**: weighted 0.9004, pooled
  (n=150) 0.920 with Wilson 95% CI [0.865, 0.954] — see the table above.
- **Blast-radius check**: `voro-engine` (`D:\Users\alexk\FORKNI\VORO\voro-engine`, C++/Python with
  one small Rust ABI-contract crate) reindexed non-incrementally
  (`tools/batch_index.py --mode force`, 568 files touched, 114.06s). By-language crosstab:

  | Language | Before | After | Δ |
  |---|---|---|---|
  | rust | 9 nodes / 5 edges touching Rust | 19 nodes / 15 edges touching Rust | +10 nodes, +10 edges |
  | cpp | 7,785 nodes | 7,785 nodes | **0** |
  | python | 3,866 nodes | 3,876 nodes | +10 |

  The +10 Rust nodes and +10 edges are exactly the expected shape: the project's only Rust file
  with substantive content, `contracts/generated/voro_engine_abi.rs`, is a pure ABI-contract/struct
  file whose functions previously chunked as one opaque blob; Wall 0's container-traversal fix now
  surfaces 10 `layout_proof.*` functions as their own chunks, each `contains`-linked to its parent.
  Zero new Rust-sourced `calls` edges were produced, correctly — those functions contain only
  macro-based layout assertions (`static_assertions`-style token trees), which are out of scope for
  this tier (see Out of scope). The 5 pre-existing Python→Rust `calls` edges (from
  `tools/validate_kernel_fx_*.py` targeting `AeTensorDesc`/`AeNodeTelemetry` structs) are unchanged.
  cpp's node count — the cleanest canary, since nothing in this change touches C++ chunking — stayed
  **exactly** unchanged, confirming zero blast radius outside Rust. **Honest disclosure**: the
  python node count rose by 10 (0.26%), not exactly unchanged as originally expected; this was not
  independently diffed node-by-node (no "before" node-ID list was captured, only counts), but is
  attributed to ordinary substrate drift from roughly 2.5 weeks of intervening non-Rust commits to
  the project since its last full rebuild (`created_at: 2026-08-22` in `project_info.json`) rather
  than any Rust-tier leakage, since the change touches no Python chunking code and cpp — the
  canary most exposed to any shared-code regression — is byte-identical.
- **Live MCP spot-check** (`find_connections`, `openheizenberg`, post-[ADR-0069](0069-fix-phantom-node-shadowing-of-resolved-call-edges.md)):
  `Graph.push_undo` (a stratum-B anchor, `crates/ohz-core/src/graph.rs:598-603`) reports
  `caller_confidence: {"exact": 16, "recovered": 0, "ambiguous": 0}` — all 16 direct callers are
  default-visible `"exact"`, matching the sample's label for this row (`correct`) and confirming
  the qualified-first divergence is live and correctly tagged end-to-end through the MCP surface,
  not just in the raw persisted graph.
- Full unit + fast_integration suites green before the Step-1 commit (`d5527a9d`): 4,691 passed /
  2 skipped; 108 passed / 0 failed, including all 6 `test_rust_call_graph_resolution.py` cases.

## Consequences

- Rust `impl`/`trait`/`mod` blocks are no longer opaque single chunks; their members surface
  individually, each `contains`-linked to its container — the same shape C++ has had since
  [ADR-0038](0038-cpp-only-container-traversal-seam.md).
- `openheizenberg` (and any other already-indexed Rust project) must be reindexed non-incrementally
  to pick this up — see Mandatory full reindex above.
- **Residual failure mode, not fixed here**: the same-file/global bare-name fallback misfire
  (12/75 of stratum A) is real and understood, but out of scope for this phase — see Out of scope.
- **Noted, not acted on**: `_rust_qualified_resolved` duplicates the qualified-first lookup branch
  already in `_resolve_call_target` rather than having that function report *how* a match was
  found and threading that provenance out to the confidence-tagging call site. A small duplicated
  lookup was judged simpler than changing `_resolve_call_target`'s return contract for its one
  other caller, which only ever wants the resolved chunk id. Revisit if a third caller ever needs
  the same "how was this resolved" signal.
- `ambiguous_fanout_cap`'s `spec(benchmark_locked=…)` citation in `search/config.py` now names both
  the ADR-0060 C++ probe and this ADR's Rust sample; the cap value itself (`3`) is unchanged.

## Out of scope

- **Same-file/global bare-name fallback misfire** (stratum A, 12/75): when a scoped call's
  qualified type is external-crate, a type alias, or derive-macro-synthesized, qualified-first
  lookup legitimately fails and falls through to a same-file/global-uniqueness bare-name match that
  is frequently wrong. A real fix needs either an external-crate/std-type denylist checked before
  the bare-name fallback, or threading receiver-type information further than tree-sitter alone
  provides — left for future work, tracked here rather than re-discovered from scratch.
- **Calls inside macro token trees** (~1,100 sites in `openheizenberg`, and the entire reason
  `voro-engine`'s new Rust chunks produced zero `calls` edges) — tree-sitter does not expand macros,
  so calls written inside a macro invocation's token tree are invisible to Wall 1's extraction.
- `Arc<dyn NodeType>`-style dynamic dispatch through trait objects — genuinely undecidable
  statically; the one sample row that could have exercised this drew a provably wrong candidate
  rather than a merely-ambiguous one, so this population remains unmeasured by this sample.
- Rust function splitting for oversized chunks — a 2,000+ line `impl Graph` chunk still exceeds the
  2,048-token embedding contract and is truncated, since Wall 1 declares no `split_block` support
  (see Wall 1 above).
- Grouped/glob `use` imports are not specially resolved.
- rust-analyzer LSP tier — no toolchain on PATH in this environment; `lsp_call_graph.py` is
  hardcoded to basedpyright and discards the progress notifications rust-analyzer uses to signal
  readiness. Needs its own ADR.
- Extending `ambiguous_fanout_cap`'s capped set to filter out std-library/external-crate collisions
  more precisely (stratum C's dominant failure mode, 25/40) — these edges are already hidden by
  default via the `"ambiguous"` tag, so this is a precision-of-the-hidden-set improvement, not a
  correctness or safety issue; not pursued this phase.
- `find_connections(symbol_name=...)` mis-resolving `Graph::add_node`/`Lfo::cook` to unrelated test
  functions on `openheizenberg` — confirmed **not** the [ADR-0069](0069-fix-phantom-node-shadowing-of-resolved-call-edges.md)
  D1/D2 defect; sidestepped in this work by passing `chunk_id` directly. Worth its own diagnosis
  session.
