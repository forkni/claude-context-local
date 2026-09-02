# Route CUDA (.cu/.cuh) extensions to the existing tree-sitter-cpp grammar

Status: accepted
Date: 2026-08-22

## Context

Indexing two real TouchDesigner-adjacent C++ projects surfaced 18 `.cu`/`.cuh` files (2,091
lines) that matched no entry in `chunking/language_registry.py`'s `EXT_TO_LANGUAGE` and were
silently skipped — `is_supported()` was never even asked about them, since nothing routes an
unregistered extension there in the first place. Zero CUDA files were indexed, zero kernels
were searchable.

CUDA C++ is, for chunking purposes, C++ with two extensions the standard grammar cannot parse:

- Execution-space/memory-space attributes — `__global__`, `__device__`, `__host__`,
  `__forceinline__`, `__restrict__`, `__constant__`, `__shared__`, `__managed__` — which are not
  valid standard-C++ declaration specifiers and desync `tree-sitter-cpp`'s parser when it tries
  to absorb them into a type.
- The `<<<grid, block>>>` kernel-launch syntax, where `<` and `<<` are not valid prefix tokens in
  that position under ordinary C++ grammar (they lex as comparison/shift operators).

Measured on a CUDA sample: routing `.cu`/`.cuh` straight to `tree_sitter_cpp` with no CUDA-aware
handling already gets most of the way there — 62 ERROR lines (3.0%) — because a bare
`__global__ void kernel(...)` degrades the same way an unrecognized C++ export macro already
does (the declarator-name recovery in `chunking/languages/_c_family.py`, which has no dedicated
ADR of its own — it fixes a bug in an existing shared helper rather than introducing a new
architectural seam): the unknown token is either absorbed into a synthesized error-recovery node
or isolated into its own `ERROR` node, while the function declarator after it still parses as a
clean, correctly-named `function_definition`. With CUDA-specific blanking added ahead of parsing,
that drops to 0 ERROR lines (0.0%).

### Declined: add `tree-sitter-cuda` as a new grammar dependency

No maintained `tree-sitter-cuda` PyPI package with parity to `tree-sitter-cpp`'s node coverage
was found. Adding one would mean a new dependency, a new ABI surface to keep inside the
`tree-sitter>=0.25,<0.26` pin, and a second, largely-duplicate set of `NODE_TYPE_MAP` entries to
maintain in lockstep with C++'s — for a grammar whose only real deltas from C++ are the two
constructs above. Not worth the maintenance surface for what a length-preserving regex pre-pass
already resolves cleanly.

### Declined: register `"cuda"` as a tenth language name

A new `language_name` would require a new `LANGUAGE_SPECS` entry and would trip
`EXPECTED_LANGUAGES` in `tests/unit/chunking/test_language_spec_ownership.py` — real churn for a
language that, after the pre-pass, is structurally identical to C++ in every way that matters to
chunking (same node types, same declarator shapes, same call-graph capabilities — or lack
thereof). Keeping `language_name == "cpp"` (inherited, unchanged) means CUDA source is indistin­
guishable from C++ to every downstream consumer that keys off language name — which is exactly
the right amount of visibility: CUDA is a C++ dialect, not a separate ecosystem, from this
indexer's point of view.

## Decision

Route `.cu`/`.cuh` to the existing `tree_sitter_cpp` grammar via a new `CudaChunker(CppChunker)`
in `chunking/languages/cpp.py` that overrides only `preprocess_source_for_parse`:

```python
_CUDA_ATTRS = re.compile(
    rb"\b(?:__global__|__device__|__host__|__forceinline__"
    rb"|__restrict__|__constant__|__shared__|__managed__)\b"
)
_LAUNCH_CFG = re.compile(rb"<<<[^>]*>>>")


class CudaChunker(CppChunker):
    def preprocess_source_for_parse(self, source_bytes: bytes) -> bytes:
        rewritten = super().preprocess_source_for_parse(source_bytes)
        rewritten = _CUDA_ATTRS.sub(blank_preserving_layout, rewritten)
        rewritten = _LAUNCH_CFG.sub(blank_preserving_layout, rewritten)
        return rewritten
```

`super()` is called first so the CUDA-specific rules run against bytes that have already had
`#if`/`#ifdef`/... directive lines blanked by the inherited preprocessor-conditional
neutralization (Workstream A2) — both rewrites are independently length- and
newline-position-preserving, so composing them in either order produces the same result; the
ordering only avoids a CUDA regex matching text inside an already-blanked directive line.

`blank_preserving_layout` (promoted from `_c_family.py`'s originally-private
`_blank_preserving_layout`, now a shared public helper) is reused rather than duplicated: it is
the same `re.sub(rb"[^\n]", b" ", match.group(0))` form the plan calls the highest-severity risk
in this whole change set to get wrong. The naive alternative, `b" " * len(match.group(0))`,
preserves total byte length but collapses every newline inside a multi-line match — and both
`_CUDA_ATTRS`-adjacent code and `_LAUNCH_CFG` matches can span multiple lines (a
`<<<grid, block>>>` launch broken across lines, as CUDA code frequently formats it) — silently
shifting every downstream `start_line`/`end_line` for the rest of the file were the naive form
used instead.

Three registrations, following the v0.25.0 header-extension precedent (commit `68f1ff9`):

1. `chunking/language_registry.py`'s `EXT_TO_LANGUAGE`: `".cu": "cpp"`, `".cuh": "cpp"`.
2. `chunking/languages/__init__.py`: export `CudaChunker`.
3. `chunking/tree_sitter.py`'s `LANGUAGE_MAP`: `".cu"`/`".cuh"` → `CudaChunker(lang)`. This is the
   step `tests/unit/chunking/test_multi_language.py::test_chunk_cpp_header_file`'s docstring
   warns is easy to miss — registering an extension in `EXT_TO_LANGUAGE` without a matching
   `LANGUAGE_MAP` entry silently yields zero chunks while `is_supported()` still reports `True`.
   `tests/unit/chunking/test_cuda_chunking.py::TestExtensionRegisteredAndChunkFileWired` guards
   both extensions against the same regression.

Per-suffix chunker caching (`TreeSitterChunker._local.chunkers`, keyed by file suffix) means
`.cu`/`.cuh` get their own cached `CudaChunker` instance, distinct from `.cpp`'s `CppChunker` —
CUDA-specific blanking cannot leak into plain C++ files.

No change to `scripts/verify_installation.py` (it asserts grammar *packages* import;
`tree_sitter_cpp` is already covered), to `LANGUAGE_SPECS`, or to
`chunking/multi_language_chunker.py::_classify_file_role`'s GLSL-only shader-extension tuple —
`.cu`/`.cuh` correctly fall through to the `"src"` role by not being added to it.

## Consequences

- **CUDA files indexed: 0 → 18** on the two projects that motivated this change (2,091 lines).
- **CUDA ERROR lines: 62/2,091 (3.0%) → 0/2,091 (0.0%)** on the same sample, measured with and
  without the `CudaChunker`-only blanking pass.
- **No new PyPI dependency.** The `tree-sitter>=0.25,<0.26` ABI pin is untouched; `.cu`/`.cuh`
  route through the already-installed `tree_sitter_cpp` package.
- **`language_name` stays `"cpp"`.** `LANGUAGE_SPECS` and
  `tests/unit/chunking/test_language_spec_ownership.py::EXPECTED_LANGUAGES` are untouched. Every
  CUDA chunk reports `"language": "cpp"` in its metadata — confirmed by
  `tests/unit/chunking/test_cuda_chunking.py::TestCudaLanguageNameStaysCpp` and the
  `test_chunker_parity.py` `[cu]` snapshot.
- **Accepted: CUDA chunks carry no call-graph edges.** Per
  [ADR-0035](0035-cpp-call-edge-tier-scope.md), C++ (and therefore CUDA, which shares its
  `language_name`) has no call-edge extractor wired at all — CUDA chunks are searchable via
  `search_code` but contribute nothing to `find_connections`. Out of scope here; would be
  in scope only if/when ADR-0035's C++ call-edge tier is revisited.
- **Accepted: execution-space attribute tokens are not visible in indexed chunk content.**
  Unlike the preprocessor-conditional case (A2), where a blanked directive always sits *nested
  inside* a larger enclosing chunk and so its original text survives in that chunk's `content`,
  a CUDA attribute like `__device__` sits *before* the declaration node it modifies. Blanking it
  moves the declaration's node span to start after the blanked bytes, so the attribute keyword's
  literal text is excluded from every emitted chunk — not just from the parse tree, but from the
  indexed text a search result would show. The function's real name, body, and line numbers are
  unaffected; only the leading annotation keyword is invisible. This mirrors
  `GLSLChunker`'s own precedent (`_neutralize_anon_layout_qualifiers` comments out layout
  qualifier arguments rather than preserving them) and is within this workstream's stated scope:
  the success criteria are ERROR-line elimination and correct definition names/line numbers, not
  attribute-token recall. Documented in `CudaChunker`'s class docstring
  (`chunking/languages/cpp.py`) for future readers who diff a CUDA search result against the
  source file and notice the qualifier is missing.
- **New snapshot:** `tests/unit/chunking/__snapshots__/test_chunker_parity/test_chunker_metadata_parity[cu].json`,
  added via `CORPUS_EXTENSIONS` in `test_chunker_parity.py`. Confirmed to be the only change in
  the snapshots directory — the other 9 parametrized cases (`.py`/`.js`/`.ts`/`.go`/`.rs`/`.c`/
  `.cpp`/`.cs`/`.glsl`) remain byte-identical.
- **New test file:** `tests/unit/chunking/test_cuda_chunking.py` (12 tests) — extension
  registration + `LANGUAGE_MAP` wiring (the `.h`-regression double-assert pattern, for both
  `.cu` and `.cuh`), kernel name/line-number correctness for `__device__`/`__global__` and the
  five remaining `_CUDA_ATTRS` tokens, multi-line `<<<grid, block>>>` length/newline invariants
  including an explicit naive-blanker contrast case, and the `language_name == "cpp"` guard.

## Migration

`merkle/merkle_dag.py::hash_file` hashes files outside `supported_extensions` by
`name:size:mtime` and files inside it by content. Registering `.cu`/`.cuh` flips their hash
strategy, so on the next incremental pass they read as modified purely from that flip and get
indexed automatically — **no explicit `incremental=False` reindex is required for CUDA files.**
This is unlike the C/C++ declarator-recovery and preprocessor-conditional fixes (Workstreams A1/
A2), which change parsing of *already-registered* extensions and therefore do need one, per the
plan's separately-recorded migration note.
