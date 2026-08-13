# Fix the container-traversal seam for C++ only; defer the Rust/C# analogues

Status: accepted
Date: 2026-08-12

## Context

`docs/plans/CPP_CHUNKING_PARITY.md` (Phases 2–3) fixes a traversal bug in C++ chunking: when the
chunker reaches a node that itself gets chunked as a single unit (e.g. a `class_specifier` or
`namespace_definition`), the pre-existing code stopped traversing into its children entirely.
Every method inside the class, every function inside the namespace, collapsed into that one
parent chunk instead of surfacing as its own named, independently-chunked function/method. On
`cuda-link`'s `native_waiter.cpp` (404 LOC), this produced 5 chunks total, two of them unnamed
`namespace_definition` blobs of 48 and 139 lines swallowing 18 function definitions, 1 class, and
1 enum between them.

The fix (`chunking/languages/base.py:207-209`) makes the previously-hardcoded check overridable:

```python
_CONTAINER_NODE_TYPES: frozenset[str] = frozenset(
    {"class_definition", "class_declaration"}
)
```

`CppChunker` overrides this to `{class_specifier, struct_specifier, union_specifier,
namespace_definition}` (`chunking/languages/cpp.py:28`), so traversal continues into C++
classes/structs/unions/namespaces after chunking them, picking up their members as separate
chunks. The base default is byte-identical to the pre-fix hardcoded check for every other
language, which is why every non-C++ parity snapshot
(`test_chunker_metadata_parity[rs|cs|py|glsl|go|js|ts]`) stayed unchanged when this landed.

While verifying the fix, the identical bug was confirmed live in two other languages that were
never in this plan's scope:

- **Rust**: `impl_item` is splittable (`language_registry.py:380`) but not a container. `impl
  Point { fn new(...) {...} }` chunks as a single `impl_item` blob; `fn new` never surfaces as its
  own chunk. `mod_item` (`:384`) has the same shape.
- **C#**: `namespace_declaration` is splittable (`language_registry.py:432`) but not a container.
  A C# file's `namespace Foo { class Bar { ... } }` chunks the namespace as one blob; nothing
  inside it — not even `Bar` — gets its own chunk unless it happens to appear outside any
  namespace.

## Decision

Ship the container-traversal seam fix for C++ only in this change. Do not add `impl_item`/
`mod_item` to Rust's container set, and do not add `namespace_declaration` to C#'s, even though
the one-line spec change for either is mechanically identical to what `CppChunker` already does.

## Reasons

1. **Widening a language's container set moves every chunk_id nested inside that container
   type.** `chunk_id` encodes byte/line ranges and hierarchy; a Rust file with an `impl` block
   that stops being a single opaque chunk and starts yielding one chunk per method changes the
   chunk_id of every one of those methods, in every already-indexed Rust project. Same for any
   C# file with a namespace. That is a real, index-invalidating migration for two languages this
   plan was never scoped to touch, verify snapshots for, or reindex real projects against.
2. **No affected project is in scope for this change.** The plan's stated purpose is indexing
   `cuda-link` (C++) and `voro-tensor` (checked, contributes zero C-family source — see the
   plan's measurement table). Neither project has Rust or C# source that this bug affects. Fixing
   it here would be scope creep against no measured need.
3. **The fix is genuinely one line per language once the seam exists.** `_CONTAINER_NODE_TYPES`
   is now an overridable class attribute specifically so this is cheap to pick up later —
   `RustChunker._CONTAINER_NODE_TYPES = frozenset({"impl_item", "mod_item"})` and
   `CSharpChunker._CONTAINER_NODE_TYPES = frozenset({"namespace_declaration"})` are the entire
   fix, mirroring `cpp.py:28`. This ADR exists so that future work doesn't have to rediscover the
   bug from scratch, and doesn't have to re-derive that the seam already supports the fix.

## Consequences

- `RustChunker` and `CSharpChunker` do not override `_CONTAINER_NODE_TYPES`; they keep the base
  default (`{class_definition, class_declaration}`), which does not match either language's own
  node-type vocabulary — meaning the base default is inert for both today (neither
  `class_definition` nor `class_declaration` is a Rust or C# grammar node type; Rust's analogue is
  `struct_item`/`impl_item`, C#'s is `class_declaration` — which C# already produces via
  `LANGUAGE_SPECS["csharp"].splittable_node_types` at `:428`, so C# classes *do* already chunk
  their members; only namespaces are affected). This is unchanged pre-existing behavior, not a
  regression introduced by this ADR.
- Rust `impl`/`mod` blocks and C# namespaces keep swallowing their contents into single chunks
  until the reopening condition below is acted on.
- The Rust and C# instances are recorded here (not left as an undocumented "noticed in passing")
  specifically so re-discovering this from a support report or a future audit isn't necessary.

## Reopening condition

Reopen when either language has a real project driving the need — i.e. a project analogous to
`cuda-link` for Rust or C# gets added to this codebase's indexing scope, or an existing indexed
Rust/C# project is measured to have the same coarse-chunk symptom `cuda-link` had. At that point:
add the one-line `_CONTAINER_NODE_TYPES` override to the affected chunker, extend that language's
`tests/fixtures/chunker_corpus/` fixture the way `sample.cpp` was extended in this change, and
re-record only that language's `test_chunker_metadata_parity` snapshot — following the exact
Phase 6a pattern this change used for C++, plus a full reindex of the affected project (no
`INDEX_VERSION`/`chunker_version` marker exists to detect this automatically — see
[ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md)).

## Glossary

Two terms introduced by this fix, also recorded in `CONTEXT.md`:

- **Container node** — an AST node type that is both independently chunked *and* has its
  traversal continue into its children afterward, so nested chunkable nodes (methods, nested
  functions) surface as their own separate chunks. Declared per-language via the
  `_CONTAINER_NODE_TYPES` class attribute (`chunking/languages/base.py:207`).
- **Transparent node** — an AST node type that is chunked as a single opaque unit, with traversal
  stopping at its boundary; anything nested inside it is absorbed into that one chunk rather than
  surfacing separately. This was the *only* behavior available before this fix, and remains the
  default for any splittable node type not listed in `_CONTAINER_NODE_TYPES` (e.g. Rust's
  `impl_item`, C#'s `namespace_declaration` — see Consequences above).
