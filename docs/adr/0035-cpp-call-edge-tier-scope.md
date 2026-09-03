# C/C++ call-edge strategy: tree-sitter tier only, sequenced behind chunking parity

Status: accepted
Date: 2026-08-07

## Context

An external research survey ("Robust Call-Graph Generators for Code RAG: Python, C/C++,
GLSL — Ranked Recommendations (2026)") recommends a three-tier C/C++ call-graph ladder:
tree-sitter name matching (≈0.6) → libclang AST resolution (≈0.85) → clangd LSP call hierarchy
(≈0.97), the latter two gated on a `compile_commands.json` compile database, with Joern as a
no-compile-DB fallback. `docs/CALL_GRAPH_TUNING.md` §1's ladder (AST → pyan → LibCST → LSP) and
`chunking/relationships/lsp_call_graph.py`'s basedpyright driver are the closest existing
analogues for Python; nothing equivalent exists yet for C/C++.

This project's actual C/C++ support today: `tree-sitter-c>=0.24.2` and
`tree-sitter-cpp>=0.23.4` are already core runtime dependencies (`pyproject.toml`), used for
chunking. `chunking/languages/c.py` (50 lines) and `chunking/languages/cpp.py` (57 lines) do
name extraction only — neither sets `metadata["calls"]` or `metadata["relationships"]`, so zero
call-graph edges are produced for either language today.

**The generator choice is not the current blocker.** Chunking is. `chunking/languages/base.py`
hardcodes the containers it descends into (`["class_definition", "class_declaration"]` at line
975, unconditional return at line 983), so traversal stops at `namespace_definition` and never
reaches member functions. Measured: `Calculator.cpp`, 67 lines, produces 4 chunks total — no
member-function chunks exist to attach call edges to. This was fixed by
`docs/plans/CPP_CHUNKING_PARITY.md` (a `development`-only plan doc; landed as
[ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md) and
[ADR-0038](0038-cpp-only-container-traversal-seam.md)); the plan's own out-of-scope section
named the two follow-on hardcodes a call-edge tier would hit next:
`chunking/multi_language_chunker.py`'s chunk-type allowlist excludes `"method"` (exactly what
C++ member functions chunk as, once parity lands), and `is_method_call=False` is hardcoded
there — wrong for `obj.m()`, `ptr->m()`, and `A::f()`.

**Toolchain constraints on this machine rule out tiers 2–3 as specified.** No clangd, libclang
Python bindings, cmake, or ninja are installed; only Visual Studio 2022 is available, and
MSBuild does not emit `compile_commands.json` the way CMake/ninja or Bazel do. Adding libclang
would mean a new LLVM dependency; adding clangd support with no compile-database source to
detect would ship a resolver tier that silently never activates for the majority of this
project's actual Windows/MSBuild users.

GLSL is the working precedent for what a tree-sitter-only tier looks like done well:
`chunking/languages/glsl.py:655-707` walks `call_expression` nodes at confidence 0.9, with
builtin-function filtering, type-constructor filtering, TouchDesigner `TD*`-prefix filtering,
and struct-constructor → `INSTANTIATES` reclassification — already at or above what the survey
calls "near-optimal" for a single-tier language.

## Decision

**Recommend and scope tier 1 only: a tree-sitter `call_expression` walk in `cpp.py`/`c.py`,
modeled directly on `glsl.py`'s existing extractor.** Confidence ≈0.6, matching the survey's own
estimate for name-matching without type resolution — appropriate given C++ name lookup,
overload resolution, and ADL cannot be done correctly from syntax alone.

**Sequence this behind the chunking-parity prerequisite.** There is nothing to attach edges
to until member-function chunks exist. This is not a new dependency — it reuses the plan's own
stated scope, which already lists the chunk-type-allowlist and `is_method_call` hardcodes as
follow-on work for exactly this reason. *(Update 2026-08-13: this prerequisite has since landed
— see [ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md) and
[ADR-0038](0038-cpp-only-container-traversal-seam.md). The chunk-type-allowlist and
`is_method_call` hardcodes above are still open follow-on work for a future call-edge tier.)*

**Do not add libclang or clangd tiers now.** Recorded as deferred, not rejected — see reopening
condition below. This also means declining Joern (Apache-2.0, JVM-based, no-compile-DB
fallback) as premature: it exists to backstop libclang/clangd when no compile database is
available, which only matters once those tiers exist.

**Do not add a GPL/GPL-adjacent C/C++ analyzer.** No such tool was under consideration for
C/C++ specifically in the survey (unlike glsl_analyzer for GLSL, declined separately); noted
here only to close the door on introducing one as a substitute for libclang.

## Consequences

- No code changes ship from this ADR by itself. It is a scope decision, recorded so a future
  C/C++ call-edge implementation starts from tier 1, not from re-litigating the ladder depth.
- The chunking-parity prerequisite (`docs/plans/CPP_CHUNKING_PARITY.md`, a `development`-only
  plan doc) has landed — see [ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md) and
  [ADR-0038](0038-cpp-only-container-traversal-seam.md). This ADR's own decision (tier 1 only,
  a tree-sitter `call_expression` walk) is unaffected and remains the open next step.
- *(Update 2026-08-23: `chunking/relationships/edge_specs.py`'s `EDGE_EMISSION_SPECS` spec-row
  table now exists — see [ADR-0056](0056-spec-row-edge-emission-seam.md), which generalized
  GLSL's bridge into a lookup table keyed on language name. The tier-1 walk described above now
  lands as one new row plus the tree-sitter walk itself, with zero edits to
  `MultiLanguageChunker`. The chunk-type-allowlist and `is_method_call` hardcodes named earlier
  in this ADR remain the two open follow-on items for that PR — ADR-0056 verified
  `EDGE_EMISSION_SPECS.call_confidence` does not reach `CallGraphConfig.min_confidence`, so a
  ≈0.6 C/C++ row is not filtered by that floor either.)*
- Reopening condition for tiers 2–3: a consumer of this project has a real `compile_commands.json`
  (CMake/ninja or Bazel build), or clangd/libclang become available in this development
  environment. Until then, shipping those tiers would mean dead code paths for most Windows/
  MSBuild users and no way to validate them here.
- *(Update 2026-09-03: the tier-1 walk this ADR scoped has shipped — see
  [ADR-0060](0060-c-family-call-edge-tier.md), which records the implementation, the Wall-1/Wall-2
  split, and restates the still-unmet tiers 2–3 reopening condition above. This ADR's scope
  decision stands as the record of *why* tier 1 was chosen; ADR-0060 is the record of what was
  built.)*
- Reusable asset for that future work: `chunking/relationships/lsp_call_graph.py`'s `_LspClient`
  is already ~70% language-agnostic — frame codec, JSON-RPC ID correlation, the aggregate-budget
  watchdog, `_uri_to_path`, `_kill_process_tree`, and the `prepareCallHierarchy`/
  `outgoingCalls` driver all generalize to clangd. Only binary discovery (currently
  `basedpyright-langserver`-specific), the `"languageId": "python"` literal in `didOpen`, and
  `_find_def_position`'s Python `def`/`class` regex are Python-bound and would need a clangd
  variant. `gather_py_files` (`call_edge_resolver.py:192`) hardcodes `rglob("*.py")` and would
  need parameterizing for any non-Python resolver, tree-sitter tier included.

## Verification

Not applicable — no code changes. Verification applies to the eventual implementation PR. The
prerequisite gate (member-function chunks existing, confirmed via `index_directory` +
`search_code` returning `method`-kind chunks for a C++ fixture) is now satisfied — see
[ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md) and
[ADR-0038](0038-cpp-only-container-traversal-seam.md) — so a future call-edge tier PR can be
verified directly against real chunk output rather than needing this prerequisite step first.
