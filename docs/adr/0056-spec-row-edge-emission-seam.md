# Spec-row seam for tree-sitter chunker-native call/relationship edges

Status: accepted
Date: 2026-08-23

## Context

Relationship extraction had two interfaces for one job. Python chunks go through the
`BaseRelationshipExtractor` / `CallGraphExtractor` seam
(`chunking/relationships/relationship_extractors/`,
`chunking/relationships/call_graph_extractor.py`) — an AST-parse-bound path. GLSL, the only
other language chunker that emitted call/relationship edges, appended plain dicts to
`metadata["calls"]` / `metadata["relationships"]` from inside `GLSLChunker.extract_metadata`
(`chunking/languages/glsl.py`), and `MultiLanguageChunker` carried two bespoke bridge methods
(`_extract_glsl_call_relationships`, `_extract_glsl_phase3_relationships`) plus three
`tchunk.language == "glsl"` type-code switches to translate them into `CallEdge` /
`RelationshipEdge` objects. The other seven tree-sitter languages (C, C++, C#, Go, Rust, JS,
TS) got nothing.

[ADR-0035](0035-cpp-call-edge-tier-scope.md) scoped a C/C++ call-edge tier as "modeled directly
on `glsl.py`'s existing extractor," named it "the open next step," and its chunking-parity
prerequisite ([ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md),
[ADR-0038](0038-cpp-only-container-traversal-seam.md)) has landed. Without a seam, the next PR
in this area would turn the triple switch into
`tchunk.language in ("glsl", "cpp", "c", "cu")` and multiply the bridge methods — the
Rule-of-Three moment for this code, arriving before the tier rather than after it.

Two alternative designs were considered and rejected — verified against live MCP
`find_connections` output, not just read:

- **A polymorphic hook on `LanguageChunker`** (`emitted_edges()`, mirroring `_extra_metadata`).
  Rejected: `MultiLanguageChunker`'s bridge call sites hold a `TreeSitterChunk` — a plain
  dataclass with no chunker reference — so reaching a chunker instance to call a hook would
  mean a per-chunk `get_chunker(file_path)` lookup (grammar load + thread-local cache) and a
  new parameter through two signatures multiple tests call positionally. The seam is
  unreachable from where the decision is made.
- **A field on `LanguageSpec`.** Rejected: `LanguageSpec` is consumed at chunker-construction
  time (grammar module, splittable node types); edge emission is a per-chunk,
  conversion-time concern. Its own docstring scopes it to "a single tree-sitter language
  binding." Widening it also drags an unrelated ownership test file into the blast radius for
  no gain.
- **A language dimension on `ExtractorSpec`.** Rejected: `BaseRelationshipExtractor.extract_from_tree`
  is CPython-`ast.Module`-bound; a `language` field would be the same constant on every row,
  feeding no dispatch, and would reverse the dependency direction `chunking/languages/`
  deliberately does not have into `chunking/relationships/`.

## Decision

A frozen spec-row table, `EdgeEmissionSpec` + `EDGE_EMISSION_SPECS`
(`chunking/relationships/edge_specs.py`), keyed on `language` name — mirroring the two idioms
the repo already uses elsewhere: the frozen-row-plus-table shape of
`ExtractorSpec` / `RELATIONSHIP_EXTRACTORS`, and the `dict[str, ...]`-keyed-on-language-name
shape of `CallGraphExtractorFactory._extractors` / `LANGUAGE_SPECS`.

A row declares three things: `call_confidence` (the `CallEdge.confidence` this language's
chunker-native calls carry), `call_chunk_types` (which `CodeChunk.chunk_type`s may carry
`metadata["calls"]`), and `imports_from_relationships` (whether `RelationshipType.IMPORTS`
edges also populate `CodeChunk.imports`). Absence of a row is the "this language does not use
this path" answer — Python deliberately has none, since its call edges come from
`PythonCallGraphExtractor` at a different seam (a re-parse of dedented chunk content), and a
row here would double-extract or misattribute provenance.

Two module-level functions, `materialize_call_edges` / `materialize_relationship_edges`,
replace the two bridge methods verbatim (moved via the standard extract-function →
introduce-parameter-object → move-function → replace-conditional-with-lookup-table sequence).
`MultiLanguageChunker` now asks `EDGE_EMISSION_SPECS.get(tchunk.language)` instead of comparing
against the string `"glsl"`; a future C/C++ tier becomes one added row in `edge_specs.py`, with
**zero** edits to `MultiLanguageChunker`.

`imports_from_relationships` also carries forward a scoping decision unchanged: GLSL's
`IMPORTS` edges (from `#include`) are the only relationship type that populates
`CodeChunk.imports`. Extending that to every language (Python included) would change
`_build_file_summary`'s "# Imports:" section for every Python file — a behavior change that
needs its own before/after review, not a byproduct of this refactor. The flag is what keeps a
future language from opting in by accident instead of on purpose.

### Verified but not fixed: `call_confidence` is inert past this seam

`GraphIntegration._make_spec_from_chunk` (`search/graph_integration.py`) projects each
`CallEdge` down to `callee_name` / `line_number` / `is_method_call` / `callee_qualified` and
drops `confidence` entirely; graph call edges instead carry the string tags `"exact"` /
`"ambiguous"`. So `EdgeEmissionSpec.call_confidence` survives only in
`CodeChunk.calls[].confidence` and its persisted `to_dict()` — it never becomes a
`resolver_confidence` value and is never compared against `CallGraphConfig.min_confidence`. A
future row with a low `call_confidence` (e.g. a C/C++ tier at ≈0.6, per ADR-0035) is **not**
filtered by that floor. This is documented as an invariant in the row's own docstring rather
than fixed here — dropping edges is a behavior change, and the C/C++ tier is the first caller
that would actually need it.

## Consequences

- `chunking/multi_language_chunker.py` no longer contains any `tchunk.language == "<language>"`
  comparison other than the pre-existing Python/tree-sitter dispatch fork (`!= "python"`) —
  enforced by an AST-scan drift test,
  `TestEdgeEmissionSpecTable.test_no_stray_language_literal_switch`
  (`tests/unit/chunking/test_language_spec_ownership.py`).
- A C/C++ call-edge tier (ADR-0035) can now land as one new `EDGE_EMISSION_SPECS` row plus the
  tree-sitter walk itself, with no edits to `MultiLanguageChunker`, `language_registry.py`, or
  the `ExtractorSpec` registry.
- `is_method_call` remains hardcoded `False` for every chunker-native edge (a per-*call* fact,
  not a per-language one) — not solved by this seam, and deliberately not pre-built here;
  ADR-0035 already flags it as follow-on work for the C/C++ tier itself.
- Behavior-preserving: every `tests/unit/chunking/test_glsl_relationships.py` test, the
  `test_chunker_parity.py` snapshot gate (no `--snapshot-update`), and the 63q / 133q /
  F-via-similar SSCG canons are unchanged.

## Reasons

Rejected registering `"glsl"` in `CallGraphExtractorFactory._extractors`, despite two
`# Future:` comment lines that used to sit in that dict inviting exactly that. That factory's
contract is `extract_calls(code, chunk_metadata)` — a re-parse — which is precisely what the
chunker-native metadata path exists to avoid. The two paths are legitimately different shapes;
this seam only makes them look like one from the caller's side, which is all that was actually
broken. Both stale comment lines are deleted, replaced with a one-line pointer to
`EDGE_EMISSION_SPECS`.

## Verification

`./scripts/test/run_tests.sh tests/unit/chunking/ -q` and
`./scripts/test/run_tests.sh tests/unit/ -q` both green throughout, one commit per refactoring
step; `test_chunker_parity.py` passed with no `--snapshot-update` at every step (structurally
guaranteed — nothing under `chunking/languages/` was touched). See
`docs/plans/vivid-orbiting-donut.md` for the full step-by-step recipe and its characterization
tests (`tests/unit/chunking/test_glsl_edge_bridge_characterization.py`).
