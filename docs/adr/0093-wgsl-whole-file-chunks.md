# Index WGSL shaders as whole-file chunks

Status: accepted
Date: 2026-11-24

hyprzero has 89 WGSL shaders (`.wgsl`, 3,477 lines, about 39 lines each) that
the index skipped, so search could not find shader code. Function-level chunks
need a tree-sitter grammar. Of the three on PyPI, `tree-sitter-wgsl` 0.0.7
installs no importable module, and `tree-sitter-wgsl-bevy` 0.1.4 is the same
grammar as the `wgsl` entry in `tree-sitter-language-pack` 1.25.2. That grammar
parses 56 of the 89 files with no errors. It fails on current WGSL statements:
module-level `const`, `var<storage, read_write>` and bare call statements such
as `workgroupBarrier();`. Some files are templates with `$TYPE` placeholders
that no grammar can parse.

We index each `.wgsl` file as one **whole-file chunk** with no grammar:

- **Chunk.** `chunk_type="whole_file"`, `language="wgsl"`, the full text, lines
  1 to the last line, named after the file (`decode.wgsl`), tags `wgsl` and
  `role:shader`. An empty file gives no chunk. A file with one chunk gets no
  synthetic `module` summary, so each shader is exactly one chunk.
- **New chunk type.** Four places in search treat the synthetic `"module"`
  file summary specially (`graph_scoring_stage.py`, `ranking_heuristics.py`,
  `centrality_ranker.py`, `graph_integration.py`), and the live server moves
  those chunks down the results. A new type keeps shader chunks ranked like
  ordinary code.
- **Large files stay one chunk.** Three files are over 6,000 bytes (the
  largest is 34,729). The chunk keeps the full text. The embedding composer's
  character budget (`EmbeddingConfig.body_truncation="fill_budget"`, about
  6,000 characters) cuts only the embedded text.
- **No calls.** `wgsl` is in `PSEUDO_LANGUAGES`, so its chunks are graph nodes
  but never call targets. A Rust call `reduce()` cannot link to `reduce.wgsl`
  by name.
- **Switch.** `ChunkingConfig.enable_wgsl_whole_file`, default on, read only
  through `chunking.language_registry.wgsl_whole_file_enabled()`. `.wgsl` is
  registered in `EXT_TO_LANGUAGE` unconditionally, like `.tdgraph.json`
  (ADR-0062), and the gate is applied at each site that decides whether a file
  is chunkable: `MultiLanguageChunker.is_supported`,
  `TreeSitterChunker.get_supported_extensions` and the `tools/batch_index.py`
  dry run. Turn it off in `search_config.json` and reindex to remove the
  chunks.

## Considered options

- **Use `tree-sitter-wgsl-bevy` and accept partial parses.** Rejected for now.
  Function chunks would follow the grammar's error recovery, so lines inside
  ERROR regions could be lost or chunked wrongly, and it adds a dependency for
  a grammar that is behind the language.
- **Leave `.wgsl` unindexed.** Rejected: shader code stays unsearchable.
- **Reuse `"module"` as the chunk type.** Rejected: the four special cases
  above would move shader chunks down the results.
- **Split large files at blank lines.** Rejected: it affects 3 of 89 files,
  and one chunk per file is the definition of a whole-file chunk.
- **Default off, like ADR-0062.** Rejected: only projects with `.wgsl` files
  see a change, and the self-index has none (`git ls-files '*.wgsl'` is
  empty), so the benchmark canon does not move.

## Consequences

- hyprzero gets 89 new `whole_file` chunks on its next full reindex.
- A maintained WGSL grammar can replace this later with function chunks; the
  switch and the chunk type then become the fallback for files it cannot parse.
- `whole_file` is a general chunk type. Another language with no usable parser
  can reuse `MultiLanguageChunker._chunk_whole_file` with its own gate.
