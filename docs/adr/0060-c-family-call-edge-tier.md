# C/C++ call-edge tier: tree-sitter name matching, shipped

Status: accepted
Date: 2026-09-03

## Context

[ADR-0035](0035-cpp-call-edge-tier-scope.md) scoped a tree-sitter-only C/C++ call-edge tier and
deferred libclang/clangd, but did not implement it — chunking parity for C/C++ (ADR-0037/0038)
had to land first, and it recorded the chunk-type-allowlist and `is_method_call` hardcodes as the
two concrete follow-on items blocking a call-edge tier. [ADR-0056](0056-spec-row-edge-emission-seam.md)
then generalized GLSL's call-edge bridge into `EDGE_EMISSION_SPECS`, a spec-row table keyed on
language, so a new tier could land as rows plus a walk instead of new `MultiLanguageChunker`
branches.

Three real external codebases indexed by this MCP server — `voro-td`, `voro-engine`,
`cuda-link` — are C/C++. Before this work, every C/C++ chunk was a graph-isolated node: 56,840
combined `calls` edges across the three projects' live graphs, **zero** originating from a C/C++
chunk. `find_connections` on a C++ chunk returned empty callers/callees; `find_path` between two
C++ chunks in the same file could not route. Confirmed live via the MCP tools on voro-td's mixed
C++/Python index (2026-09-02): a 647-line C++ method returned `direct_callers: []`,
`direct_callees: []`, while a same-index Python control chunk returned 10 direct + 10 indirect
callers. Same graph, same tools — Python traversed, C++ did not.

A Phase-0 offline probe (simulated against voro-engine's live 295-file graph, `build/` excluded)
established both the naming design and the one hard blocker before any production code:

- Call-site shapes (33,996 sites): `identifier` 39%, `field_expression` (method calls) 33%,
  `qualified_identifier` (`std::sort`, `voro::helper`) 21%, `template_function` 7%. GLSL's
  existing walk handles only the first shape and zero method calls — not reusable verbatim.
- Naive name-matching resolved 24.1% of sites, 25.5% ambiguous, 50.4% phantom. Static noise
  filters (`std::`-prefix drop, STL member-name set) raised resolution to 36.7% for a cost of
  only 95 lost edges. Prefer-definition disambiguation (decl-in-header / def-in-source) rescued a
  further 614, reaching 39.5% resolved.
- **Blocking finding**: `_get_ambiguous_candidates` was `return
  list(name_to_chunk_ids.get(callee_name, []))` — uncapped. Vendored SDK headers (voro-td carries
  6 byte-identical copies of `CPlusPlus_Common.h`) mean 1,850 call sites have fan-out ≥10.
  Uncapped, this adds 77,172 edges (+190% graph links) on voro-engine alone; existing filters
  (`hide_ambiguous_edges_default`, `drop_ambiguous_traversal_edges`) are display/traversal-time
  only — the edges are still built and stored. A build-time cap is a hard requirement, not a
  refinement.

Confirmed at design time and unchanged today: no clangd, libclang bindings, cmake, or ninja are
on this machine's PATH; none of the three target projects produce a live, current
`compile_commands.json` (voro-engine's CMake generator is Visual Studio, which does not emit one;
cuda-link's is stale, pointing at deleted sources). ADR-0035's reopening condition for tiers 2–3
still does not hold.

## Decision

**Ship tier 1 as scoped by ADR-0035**: a tree-sitter `call_expression` walk at confidence 0.6,
modeled on `glsl.py`'s extractor but with a real dispatch table for all four call-site shapes.
This supersedes ADR-0035's "not yet implemented" status — the design it scoped is now landed.

**Wall 1 — chunk-time extraction** (`chunking/languages/_c_family.py`, shared by `CChunker` and
`CppChunker`; `CudaChunker` inherits it, and `.h/.hpp/.cu/.cuh` already route to the `cpp`
grammar, so headers and CUDA get the walk for free):

- Dispatch by the `call_expression`'s `function` field type: `identifier` → plain call;
  `field_expression` → method call (`obj.m()`/`ptr->m()`, `is_method_call=True`); C++
  `qualified_identifier` → last `::` segment as `name`, full text as `qualified`; C++
  `template_function` → template name, args stripped. Everything else (function pointers,
  parenthesized/lambda calls) is skipped — ~0.2% of sites in the probe.
- `new_expression` becomes an `INSTANTIATES` relationship, not a call.
- Static, cheap noise filtering only: `std::`/`::std::`-prefixed qualified calls and a small STL
  member-name set are dropped unconditionally — chunk time has no project symbol table, so this
  is the only filtering that belongs here (mirrors `glsl.py`'s `_is_call_noise` composition
  pattern: a namespace-prefix rule plus a name set, not a hand-maintained blocklist).
- `CallSite` NamedTuple (`chunking/relationships/edge_specs.py`) widens the emitted tuple to
  `(name, line, is_method_call=False, qualified=None)`. GLSL keeps emitting bare `(name, line)`
  2-tuples — `_as_call_site` normalizes both shapes via `CallSite(*entry)`, so
  `test_glsl_relationships.py` needed no changes. This discharges the follow-on ADR-0056 flagged
  in its own Consequences section (`materialize_call_edges` no longer hardcodes
  `is_method_call=False`/`callee_qualified=None`).
- Two new `EDGE_EMISSION_SPECS` rows: `"cpp"` (`call_chunk_types={function, method, template,
  split_block}`, `call_confidence=0.6`, `imports_from_relationships=True`) and `"c"` (same minus
  `method`/`template`, which C has no grammar for). Relationships shipped this round: `calls`,
  `imports` (`preproc_include`), `instantiates` (`new_expression`), `inherits`
  (`base_class_clause`). `uses_type`/`overrides`/`defines_field` deferred — the enum already has
  all 21 `RelationshipType` values, so adding them later is purely a scoping choice, not a schema
  change.

**Wall 2 — index-time resolution** (`search/graph_integration.py`), all gated on
`_BuildSpec.language` so every addition is a byte-identical no-op for Python callers by
construction, verified by a dedicated Python-invariance unit test per item, not just inspection:

1. The Python-builtins phantom check (`hasattr(builtins, callee_name)`) now runs only when
   `language == "python"`. Ungated, it silently phantomed any C++ project function named `min`,
   `max`, `abs`, `hash`, `next`, `filter`, `set`, `type`, `id`, `open`, `format`, `sum`, `all`,
   `any`, `iter`, `round`, `print`, …
2. `_C_FAMILY_COMMON_MEMBERS` — a C-family sibling of `_COMMON_METHODS` (STL/idiom member names:
   `size`, `data`, `push_back`, `begin`, `end`, `c_str`, `find`, `insert`, `erase`, …), applied
   with the same "unless the project itself defines a symbol of that name" rule already used for
   Python.
3. Separator-agnostic Pass-1 indexing: C/C++ chunk names for the *same logical symbol* arrive
   under both `.` (synthesized `parent_name.method` for in-class declarations) and `::` (verbatim
   out-of-class definitions, e.g. `TensorPluginTOP::execute`). Both spellings — full name, last
   segment, and canonical `parent+sep+leaf` under both separators — now land in the same
   `name_to_chunk_ids` bucket. This is deliberately a *union*, not a switch to `::`-only: splitting
   the two spellings into separate buckets would make a decl/def pair permanently unresolvable
   against each other, which is the opposite of what item 4 needs.
4. Prefer-definition disambiguation: once item 3 puts a decl/def pair in one bucket, exactly one
   candidate in a `.cpp/.cc/.cxx/.cu` source file among otherwise-header candidates wins — the
   definition carries the body and thus the outbound edges. Probe-measured to rescue 614 sites
   and address 191 of 715 colliding names (the single largest ambiguity cause).
5. Build-time ambiguous fan-out cap: `CallGraphConfig.ambiguous_fanout_cap` (default 3),
   resolved once per graph build and threaded into `_get_ambiguous_candidates`, which truncates
   `candidates[:fanout_cap]` only when `language in _C_FAMILY_LANGUAGES`. Reduces voro-engine's
   projected ambiguous-edge growth from +77,172 (+190% links) to +36,318 (+90%).
6. `_qualified_to_file_suffix`'s dotted→`.py` mapping is left Python-only, not extended — the
   C-family analogue (an `#include`-set signal) is deferred as a later refinement, not first-tier
   scope.

**Rollout: default-on for C-family languages**, kill-switchable only via
`CallGraphConfig.ambiguous_fanout_cap=0` (disables the cap; there is no separate feature flag,
since the walk itself has no failure mode that removing it would fix — C/C++ chunks had zero
outbound call edges before this, so shipping strictly adds edges where none existed). All three
target projects require a full `incremental=False` reindex — file content is unchanged, so
content hashes are unchanged and an incremental pass would leave the old zero-edge chunks in
place (this is the third instance of the `chunker_version` staleness pattern ADR-0037 twice
declined to solve generally; see that ADR's follow-on note).

**Not built, and explicitly out of scope for this ADR**: libclang or clangd tiers (ADR-0035's
reopening condition — a real `compile_commands.json`, or clangd/libclang on this machine — still
does not hold), a GPL/GPL-adjacent analyzer (never under consideration for C/C++ specifically),
and any change to `chunking/relationships/call_edge_resolver.py`'s pyan/LibCST/LSP ladder (that
ladder's `gather_py_files`/`rglob("*.py")` scoping is tier-2+ machinery, orthogonal to a
tree-sitter tier).

## Consequences

- C/C++ chunks now participate in `find_connections`, `find_path`, and ego-graph/multi-hop
  traversal the same way Python chunks do — closing the capability gap that motivated this work
  for `voro-td`/`voro-engine`/`cuda-link`.
- Every Wall-2 change is in code the Python path also executes. Verified via: (a) construction —
  each addition is gated on `language`, with `language` defaulting to `"python"` for any caller
  that doesn't pass it; (b) a dedicated unit test,
  `test_python_ambiguous_fanout_uncapped_regardless_of_cap_value`
  (`tests/unit/search/test_graph_integration.py`), pinning that Python resolution is unaffected
  by any `fanout_cap` value; (c) full unit suite green (4,377 passed / 2 skipped) and
  `tests/unit/chunking/` green (517 passed / 2 skipped) after all Wall-1/Wall-2 commits; (d) 63q
  and 133q golden-set canon re-runs both flat against the pre-existing pin within ordinary
  corpus-drift noise, and — the stronger, non-noisy proof — the fan-out cap's code path is
  structurally unreachable on this project's own self-index, which is 100% Python (`top_tags`
  reports zero `cpp`/`c` chunks; `tests/` is excluded from self-indexing). Full writeup:
  `evaluation/CANON_GATE_FANOUT_CAP_20260903.md`.
- No type information is available to this tier. `v.size()` and `myObj.size()` are
  indistinguishable to tree-sitter; all method-call resolution is name-based. This is exactly
  what a clangd tier would fix, and remains the reopening condition below.
- `extern "C"` DLL plugin boundaries are invisible to this tier. voro-td resolves
  `cito_engine.dll` via `LoadLibrary`/`GetProcAddress`; voro-engine loads ~20 plugin DLLs through
  an `extern "C"` ABI. These are the architecture's most important seams and no static,
  single-translation-unit analysis will ever see them.
- Vendored-header duplication inflates ambiguity beyond what a single-project codebase would see
  — voro-td's 6 copies of `CPlusPlus_Common.h` and 3 of `CHOP_CPlusPlusBase.h` make every TD SDK
  symbol a 6-way collision before the fan-out cap even applies. The cap contains the blast
  radius; excluding vendored SDK header directories at reindex time would contain it better, and
  is a per-project `exclude_dirs` decision rather than a tier-level one.
- `#ifdef`-gated code (e.g. `CITO_ENABLE_CUDA`) is captured for whichever preprocessor
  configuration tree-sitter's single parse sees — there is no multi-configuration analysis.
- Reopening condition for tiers 2–3 is unchanged from ADR-0035: a consumer of this project has a
  real `compile_commands.json` (CMake/ninja or Bazel build), or clangd/libclang become available
  in this development environment.

## Verification

- `./scripts/test/run_tests.sh tests/unit/ -q` — 4,377 passed, 2 skipped.
- `./scripts/test/run_tests.sh tests/unit/chunking/ -q` — 517 passed, 2 skipped, 10 snapshots
  passed (`test_chunker_parity.py` snapshots refreshed to show non-zero `calls` for
  `cpp`/`c`/`cu` fixtures, reviewed as a real diff, not blindly regenerated).
- `tests/unit/chunking/test_c_family_relationships.py` — new file, the missing counterpart to
  `test_glsl_relationships.py`; asserts `metadata["calls"]`/`metadata["relationships"]` content
  for representative C/C++ fixtures across all four call-site shapes plus imports/instantiates/
  inherits.
- 63q/133q golden-set canon: see `evaluation/CANON_GATE_FANOUT_CAP_20260903.md` for the full
  disposition — flat aggregates, no systematic mover concentration, corpus-drift explained.
- *(Update 2026-09-03: the Phase-0 probe re-run against the shipped pipeline is done — see
  `evaluation/CPP_CALLGRAPH_PROBE_20260903.md`. Full root-cause breakdown of all 12,968 phantom
  edges on voro-engine's real reindex found one genuine, fixable Wall-1 gap — unfiltered
  `static_cast`/`dynamic_cast`/`const_cast`/`reinterpret_cast` "calls" (6.6% of phantom mass,
  same class as the existing `std::`-prefix drop, now fixed in `_c_family.py` via
  `_is_cast_keyword`) — plus two non-defects: 22.8% is the "unless the project defines it"
  blocklist deliberately phantoming (Python-parity by design, per `_resolve_call_target`'s own
  docstring contract), and 70.7% is genuine external-library calls (CUDA runtime, Win32, a
  vendored JSON library) a tier-1 resolver cannot and should not resolve. Net: 3 of 4 Phase-0
  quantitative gates (resolved ≥8,000, phantom ≤25%, growth ≤+100%) still fail against real
  numbers even after the fix, root-caused to the gates having been probe-estimated on a
  simulation whose methodology and sample didn't match the shipped design or a real
  externally-integrated codebase — see the linked doc's Recommendation section, which proposes
  demoting those three to informational trend metrics and keeping only the fan-out cap (passes:
  3, 0 violations) and hand-labeled precision as hard gates. The ~150–200-edge hand-labeled
  precision sample and the `incremental=False` reindex of voro-td and cuda-link (voro-engine's is
  already current as of this update) remain open, tracked as plan tasks #13/#14.)*
- *(Update 2026-09-03: the hand-labeled precision sample (task #13) landed —
  `evaluation/CPP_CALLGRAPH_PRECISION_SAMPLE_20260903.md` — and found the `>= 0.85` gate failed
  decisively overall (0.583 strict / 0.660 lenient, n=180), entirely concentrated in
  `is_method=True` member-call resolution (0.162 strict, 68/180 of the sample but 46 of 54
  confirmed-incorrect labels): tree-sitter has no receiver-type information, so `.empty()`/
  `.size()`/`.count()`/`.get()` on an arbitrary project type routinely resolve to an unrelated
  class's same-named method. Free-function (`is_method=False`) resolution was unaffected and
  already cleared gate on its own (0.839 strict / 0.922 lenient). Fix: `_two_pass_build`
  (`search/graph_integration.py`) now tags every C-family resolved edge with `is_method_call=True`
  as `confidence="ambiguous"` — reusing the existing, already-shipped, already-A/B-tested
  `hide_ambiguous_edges_default=True`/`filter_ambiguous_edges` machinery
  (`evaluation/CONFIDENCE_EGO_AB_20260816.md`) instead of adding a new confidence tier, so no new
  config/schema/doc surface was needed. The genuinely-ambiguous (`_get_ambiguous_candidates`)
  branch was already tagged `"ambiguous"` unconditionally and needed no change. Re-crossing the
  same 180-edge hand-labeled dataset by what's default-visible after the fix
  (`confidence=="exact" & is_method==False`) measures **0.988 strict / 1.0 lenient (n=83)** —
  clears gate decisively. Empirically re-verified on a real `--mode force` rebuild of
  voro-engine's graph: zero `(is_method=True, confidence="exact")` edges exist post-fix, and total
  resolved+ambiguous volume is byte-identical to the pre-fix probe (10,850), confirming this is a
  pure re-tag with no change to what resolves. Full breakdown and re-verification numbers in the
  precision-sample doc's "Update 2026-09-03" section. Unblocks task #14.)*
