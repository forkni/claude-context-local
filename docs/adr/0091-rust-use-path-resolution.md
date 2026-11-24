# Resolve Rust call paths through use imports and the module tree

Status: accepted
Date: 2026-11-24

The tree-sitter Rust tier (ADR-0070) resolves a call by its bare name plus one
`Type::m` lookup. It never reads `use` imports, because file-root `use`
statements land in `module_preamble` chunks, and those chunks skip metadata
extraction. So `Arc::new()` imported from `std` falls through to an unrelated
project `new`, and an imported `mix()` fans out to every project `mix`.
ADR-0070 recorded this as the one systematic stratum-A defect (12 of 75 rows on
openheizenberg). On hyprzero, 267,258 Rust `calls` edges were ambiguous.

`search/rust_module_index.py` (`RustModuleIndex`) now reads the layout from
disk during the graph build. The crates come from the Cargo workspace: each
target is its own crate, and the dependencies are split into workspace members
and outside crates. The module tree follows the 2018 rules and reads
`#[path = "..."]`. A scope holds named, grouped, aliased and glob imports,
`pub use` re-exports, local items, `type` aliases and `use` inside function
bodies. `resolve(file, line, path)` returns *internal* (crate, module, item),
*external* (`std`/`core`/`alloc`, the std prelude, or a declared outside
dependency) or *unknown*.

`GraphIntegration._two_pass_build` asks the index about each Rust plain or
path call, before the ADR-0070 lookups:

- **External**: no resolved or ambiguous edge. Only the bare-name phantom edge
  stays, which `add_chunk` already writes.
- **Internal free item**: the candidates in the module the path names. If none
  is in that module, a unique match in the target crate is linked with
  `resolution="rust_use_fallback"`. Otherwise the call is refused.
- **Internal `Type::m`**: the `Type::m` candidates in the type's crate, then in
  workspace crates that depend on it (trait impls, orphan rule). If none exists,
  the call is refused. Derived and macro-made methods have no chunk.
- **Several candidates left**: ambiguous edges among those candidates only,
  under `ambiguous_fanout_cap`.
- **Unknown, and all receiver calls `x.m()`**: unchanged. These need types
  (see "E" below).

D-made edges carry `resolution="rust_use"`. Each build logs one line:
`[RUST_USE] resolved= fallback= refused_external= internal_missing= unknown=
files_parsed= secs=`. The switch is `call_graph.rust_use_paths`, default on.
Other languages are byte-identical.

## Evidence

The hyprzero call graph was built offline from the saved metadata, once with
the switch off and once on (`evaluation/RUST_USE_PATH_GATE_20261124.md`, local
only).

- Exact edges went from 75,443 to 93,693 and ambiguous edges from 267,258 to
  214,360. The graph build took 10.3 s longer (24.6 to 34.9 s).
- In the hand-labelled sample, each outcome scored 10 of 10 correct: resolved,
  fallback, refused_external and internal_missing (strict, Wilson lower bound
  0.72). The gate was at least 9 of 10 in each outcome, and at most 15 s extra.
- All 7 ADR-0070 misfire shapes on openheizenberg (209 call sites) now get no
  project edge. For example, `Params::new` is a `type` alias to `BTreeMap` and
  now resolves to std.

## Considered options

- **rust-analyzer SCIP inside the reindex ("E").** Rejected as a default. A cold
  run on hyprzero took 634 s and used 16.48 GB at peak. E stays planned as an
  opt-in tier that reads a cached `.scip` file and joins its references to
  tree-sitter call sites. Only E can resolve receiver calls.
- **Refuse every unmatched path head.** Rejected. A head that is not std, not a
  dependency and not in scope (a macro-made module, a cfg twin) stays *unknown*
  and keeps today's resolution, so D removes only what it can show is wrong.
- **Parse `use` statements in the chunker.** Rejected. Chunk metadata does not
  know the module tree or the Cargo layout. `#[path]` (465 in hyprzero) and
  re-exports need the whole crate.

## Consequences

- Each build parses every mounted Rust file again (4,421 on hyprzero, about
  7 s). The chunker's trees are gone by then.
- The fallback outcome is rare (30 times on hyprzero) and was sampled mostly on
  one helper, so its evidence is weak.
- No retrieval canon re-pin is needed. The self-index has no Rust code.
- ADR-0070's "unresolvable qualifier falls through to a bare name" defect is
  closed for plain and path calls.
