# Recover dropped C-family regions: parse-only repairs, preamble descent, doc-comment adoption

Status: accepted
Date: 2026-10-14

## Context

Indexing TouchDesigner 2025.33230 (opencv, CPython `Include/`, USD `codegenTemplates`) logged hundreds of
`[PARSE_WARN]` lines. PARSE_WARN (`_log_parse_error_outcome` in `chunking/tree_sitter.py`) reports only
ERROR-node lines that end up in no chunk, so it undercounts the loss. A whole-file audit
(`scripts/benchmark/measure_parse_recall.py`, 1,025 C-family files) counts every **dropped line**: a
non-blank line in no chunk and no adopted docstring.

The audit found 6,427 dropped code lines and 11,814 dropped comment lines. Only 3,533 of those code lines
were ERROR lines that PARSE_WARN could see. Most of the loss sat in nodes that parsed cleanly, 3,405 lines
of it inside `extern "C" {}`.

Causes:

- **A.** Only `CudaChunker` blanked the CUDA specifiers (`__device__ __forceinline__`). The `cudev/*.hpp`
  headers go through the C++ chunker, so each one collapsed into a single root ERROR.
- **B.** Bare macro lines with no `;` derail the parse of the code after them. Examples:
  `CV_CPU_OPTIMIZATION_HAL_NAMESPACE_BEGIN`, `PyObject_HEAD`, `OPENCV_HAL_IMPL_*(…)`.
- **C.** `repair_macro_wrapped_declarations` fired only when an ERROR started at the macro, so it missed
  ERRORs that start after it.
- **D.** USD `codegenTemplates` are Jinja templates saved as `.cpp` and `.h`.
- **E.** Both grammars lex a `#define` body as one `preproc_arg` token, and that token ends at `/*`. A
  comment with body text on both sides splits the body, which ERRORs the macro and often the code after
  it (`ocl_defs.hpp`, `moduleobject.h`, the HAL intrinsics headers).
- **F.** `_collect_module_preamble_chunks` skipped every root child that had a chunked descendant. Code
  inside `extern "C"`, namespaces, ERROR nodes and declarations went into no chunk: prototypes,
  `#define`s, `using`s.
- **G.** `_trim_claimed_trailing_comments` drops a comment directly above a chunked node, on the
  assumption that the node adopts it. Only GLSL adopted comments. Comment-only runs after the first chunk
  were also dropped as boilerplate.
- **Phantom end row.** A C-family preprocessor node owns its trailing newline. Row math therefore ended
  chunks, and the runs between them, one line past the content.

## Decision

Every repair is a **parse-only repair**: a length- and newline-preserving rewrite that only the parser
sees. Chunk text keeps the original bytes.

1. **(A)** `_CFamilyChunker._neutralize` blanks the CUDA specifiers for every C-family chunker.
   `CudaChunker` keeps only the `<<<…>>>` launch configuration.
2. **(C)** `repair_macro_wrapped_declarations` runs on any ERROR that intersects the macro's line.
3. **(B)** `repair_bare_macro_lines` blanks bare macro lines, together with their invocation arguments,
   wherever they intersect an ERROR. It runs at most 4 rounds and keeps a round only if the number of
   ERROR lines strictly falls; this is the strict-decrease guard. It skips:
   - keywords;
   - a line followed by `{`, `:` or `->` (gtest `TEST(a, b) {`, constructor init lists, trailing returns);
   - a line that continues the one before it (that line ends in `\`, `,`, `(` or an operator).
4. **(E)** `neutralize_define_comments` blanks a `/* */` only when it splits a `#define` body, meaning
   there is body content both before and after it. It keeps any `\`+newline inside the comment. It
   leaves alone leading and trailing comments, comment markers inside string literals, and comments
   outside `#define`s.
5. **(F) Generic preamble descent, in every file.**
   - The base hook `_preamble_descend_children(node)` returns `None`, so the other languages are
     unchanged and their parity snapshots stay byte-identical.
   - The C-family override applies to a node that holds a chunk but is neither chunked itself nor a
     `template_declaration`. It returns the named children of that node's body.
   - The collector then flushes **preamble chunks** inside `extern "C"`, namespaces, ERROR nodes and
     declarations. It dedupes at line level against the chunks already emitted.
6. **(D)** `codegenTemplates` is added to `DEFAULT_IGNORED_DIRS`; `include_dirs` can re-admit it.
7. **Multi-line macros.** A multi-line `#define` (`preproc_def` or `preproc_function_def`) becomes a named
   `macro` chunk. One-line `#define`s stay inside preamble chunks; there are 13.3k of them in the corpus,
   and as separate chunks they would be noise.
8. **(G) Doc comments.**
   - The C and C++ `extract_metadata` set `docstring` from the comment run directly above or beside the
     node (`_extract_sibling_comment_docstring`), as GLSL does. CUDA inherits this.
   - `_CFamilyChunker._is_boilerplate_run` keeps comment-only runs of 3 or more lines. One-line labels
     and dividers are still dropped.
9. **Phantom end row.** `node_line_span` and the base `_last_row` remove the extra row for all sibling
   and preamble row math.
10. **Reporting.** The `lines_lost` count in PARSE_WARN no longer includes blank lines.

Declined:

- **A tree-sitter-cuda grammar.** [ADR-0054](0054-route-cuda-extensions-to-cpp-grammar.md) routes CUDA to
  tree-sitter-cpp, and the specifiers were the only gap.
- **Running a real preprocessor.** It needs per-project include paths and defines, and it breaks the
  mapping from chunk text back to the source.
- **Parsing Jinja.** The template inputs are excluded instead.
- **Anchoring comments to `template <…>` and `typedef` wrappers.** About 70 lines are at stake.

## Results

Harness: `.venv/Scripts/python.exe -m scripts.benchmark.measure_parse_recall ROOT [--index-filter]`.
The table covers the indexed set, `--index-filter`, which is what indexing sees:

| Tier | Files | Chunks | Definitions | Dropped code | Dropped comment | ERROR lines | ERROR dropped |
|---|---|---|---|---|---|---|---|
| Baseline | 916 | 28,920 | 25,522 | 5,300 | 9,595 | 23,560 | 2,812 |
| T1 repairs (A, B, C) | 916 | 29,290 | 25,934 | 3,627 | 9,507 | 10,131 | 539 |
| T2 descent (F) | 916 | 29,818 | 25,934 | 278 | 7,856 | 10,131 | 44 |
| T3 templates (D), end row | 904 | 29,686 | 25,847 | 274 | 7,807 | 8,513 | 17 |
| T4 multi-line macros | 904 | 30,888 | 27,047 | 298 | 8,332 | 8,513 | 19 |
| T5 doc comments (G), E | 904 | 31,167 | 27,044 | 297 | 334 | 7,956 | 15 |

Full tree, 1,025 files including the templates, baseline → T5:

| Metric | Baseline | T5 |
|---|---|---|
| Dropped code | 6,427 | 399 |
| Dropped comment | 11,814 | 683 |
| ERROR lines | 32,638 | 16,819 |
| ERROR dropped | 3,533 | 120 |
| Definitions | 29,628 | 32,086 |
| Chunks | 34,102 | 37,732 |

- No file gained ERROR lines at any tier.
- The only lost definitions were bogus fragments that error recovery had produced from macro invocations
  parsed as functions.
- T4 raised dropped comments by 525. These are comments above the new macro chunks, trimmed by cause G
  until T5 adopted them.
- T4 also raised dropped code by 24 lines: 17 inside `extern "C"`, 5 with no enclosing node, and 2
  inside function-like macros.
- After T5, only two indexed files still emit PARSE_WARN at WARNING level: `warpers.hpp` (7 lines) and
  `tracking_legacy.hpp` (1 line). The files named in the original log no longer warn: `vec_math.hpp`,
  `pyerrors.h`, `intrin_rvv_scalable.hpp`, `longobject.h`.
- Indexed files with dropped ERROR lines fell from 65 to 9. The rest are logged at DEBUG, either because
  the dropped lines are punctuation only, or because the content was kept in other chunks.

## Consequences

- Chunking of the existing `.c`, `.h`, `.cpp`, `.hpp`, `.cu` and `.cuh` extensions changed. Existing
  indexes need one `incremental=False` reindex;
  [ADR-0037](0037-decline-index-version-bump-for-cpp-parity.md) declined an automatic version bump.
- Chunks grow by 7.8% on the indexed set and by 10.6% on the full tree.
- `measure_parse_recall` is the gate for future C-family chunking changes. Run it with `--compare` against
  a saved JSON, both with and without `--index-filter`.
- Residual dropped code on the full tree:
  - 216 lines inside `extern "C"`, the largest being `msa_macros.h` with 42;
  - 137 lines with no enclosing node. These are lines blanked by the bare-macro repair that no preamble
    run reaches; the largest is `NPP_staging.hpp` with 52. A gap filler for them is not implemented.
  - 18 `template <…>` header lines.
- Residual dropped comments are kept out by design. About 360 lines are one-line labels directly above
  `#if` or `#endif`, or followed by a blank line. About 70 lines sit above `template` and `typedef`
  wrappers.
- Deferred:
  - GLSL preprocessor nodes have the same phantom end row.
  - Go, Rust, TypeScript and JavaScript probably share cause G, since only GLSL and C-family adopt
    comments. Measure them separately.

## Addendum (2026-10-14): unique preamble ids

A full reindex of TouchDesigner failed after this change:
`[SYNC_CHECK] Duplicate chunk_ids: 33325 total, 33324 unique`, then
`unicodeobject.h:780-780:module_preamble has index_id 23675 but is at position 23674`. A chunk id is
`path:start-end:type[:name]`, and preamble chunks have no name, so two preambles on one line share an id.
The metadata store upserts, so the full path fails its position check and an incremental pass silently
loses one chunk.

Cause: the C-family chunker chunked **bodyless specifiers**: type references such as `enum
PyUnicode_Kind kind`, forward declarations, `class Foo;`. A prototype naming such a type therefore held
a chunk, decision 5 descended it, and the runs flushed on either side of the specifier both landed on
line 780.

1. **Bodyless specifiers are not chunks.** `_CFamilyChunker.should_chunk_node` rejects a
   `struct_`/`enum_`/`union_`/`class_specifier` with no `body` field.
2. **Preamble ids are unique by construction, in every language.** `_collect_module_preamble_chunks`
   folds a group that starts on the line the previous preamble ends on into that preamble. Whatever lies
   between the two groups sits on that one line. This also closes the same-line case in minified JS/TS.
3. **Write-boundary backstop.** `IndexWriteStage.add_to_index`, the one `add_embeddings` seam for the
   full and incremental paths, keeps the first result per `chunk_id` and logs one WARNING. A future
   collision costs one chunk, not the reindex. It still makes one `add_embeddings` call, which flat/IVF
   sizing needs on a fresh index.
4. **Harness.** `measure_parse_recall` reports `duplicate_ids` and chunks per node type; `--compare`
   flags any file with a duplicate as regressed.

Results against T5 (no file changed ERROR lines; every lost definition is a bodyless specifier;
`duplicate_ids` 0, from 29 extra in 6 files):

| View | Chunks | Definitions | Dropped code | Dropped comment |
|---|---|---|---|---|
| Indexed (904 files) | 30,512 (−655) | 26,380 (−664) | −4 | −12 |
| Full (1,025 files) | 36,825 (−907) | 31,327 (−759) | −28 | −13 |
