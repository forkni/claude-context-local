# Decline an `INDEX_VERSION` bump for C++ chunking parity

Status: accepted
Date: 2026-08-12

## Context

This change (implementing the `development`-only `docs/plans/CPP_CHUNKING_PARITY.md`, Phases 1–4)
registers seven new C/C++ header extensions (`.h .hpp .hh .hxx .inl .ipp .tpp`), widens
`LANGUAGE_SPECS["cpp"]
.splittable_node_types` to include `field_declaration`/`declaration`/`alias_declaration`, and
fixes the container-traversal seam so C++ classes and namespaces stop swallowing their members
into unnamed blobs (see [ADR-0038](0038-cpp-only-container-traversal-seam.md)). Every one of
these is a chunk-shape change: chunk boundaries move, chunk_ids move, chunk counts move, for any
C/C++ file already indexed with the old grammar behavior.

The plan's original draft proposed pairing this with a `chunker_version` snapshot marker (Phase
5) analogous to `BM25SparseIndex.INDEX_VERSION` (`search/bm25_index.py:278`) — a version stamp
that would let the indexer detect "this file's chunks were produced by an older chunker" and
force a re-chunk automatically, the same way a BM25-format mismatch is detected today.

## Decision

Do not bump `BM25SparseIndex.INDEX_VERSION`, and do not add a `chunker_version` snapshot marker.
Ship Phases 1–4 as a code-only change; handle the one project that actually needs a re-chunk
(`cuda-link`) with a manual `index_directory(..., incremental=False)` call instead.

## Reasons

1. **`INDEX_VERSION` is the wrong subsystem.** It is scoped to the BM25 sparse-index document
   format (stemming, tokenizer variant, path/symbol augmentation — see the version-history
   comment at `search/bm25_index.py:274-277`), not to chunk shape. Chunking is upstream of both
   the dense (FAISS) and sparse (BM25) indices; conflating "the chunker changed" with "the BM25
   document format changed" would make the version number mean two unrelated things.
2. **The mismatch check is warn-only, not a hard failure.** `bm25_index.py:749-754` logs a
   `⚠️  BM25 index version mismatch` warning and keeps loading the stale index — it does not force
   a rebuild, refuse to serve stale results, or otherwise change behavior. Bumping the number for
   this change would not have caused C++ headers to get re-chunked; it would only have logged a
   warning that nobody reading BM25 log lines connects to "my C++ chunks are stale."
3. **A version bump is a false alarm for every non-C/C++ project.** `INDEX_VERSION` is process-
   global (a class constant, not project- or language-scoped). Every Python-only, Go-only,
   Rust-only project touched by nothing in this change would load its index, see the mismatch
   warning, and have no actionable fix — their chunks are unaffected, but the log would tell them
   to "re-index the project to rebuild with the current format" anyway.
4. **The one project that needs a re-chunk needs a full one regardless of any marker.**
   `merkle/merkle_dag.py:243-259` hashes unsupported extensions by `name:size:mtime` rather than
   file content. Registering the header extensions flips each header's hash from stat-based to
   content-based, so headers correctly read as *modified* and re-chunk on the next incremental
   pass. But `cuda-link`'s existing `.cpp`/`.c` files were already content-hashed under the old
   grammar — their file content and thus their hash did not change, so an incremental pass would
   silently keep their stale, coarse pre-parity chunks. A `chunker_version` marker would need to
   force a full reindex for exactly this project to fix that — which `index_directory(...,
   incremental=False)` already does directly, with no new state to maintain.

## Consequences

- `BM25SparseIndex.INDEX_VERSION` stays at `4`. No new `chunker_version` field is added to any
  index metadata file.
- Any project with previously-indexed C/C++ source keeps its old, coarser chunk shape (unnamed
  namespace blobs, header files invisible) until it is explicitly reindexed with
  `incremental=False`. This is a known, accepted staleness window — not a silent failure, since
  the chunker code itself is versioned in source control and the project's `CLAUDE.md`/changelog
  record when the parity change shipped.
- `cuda-link` (the only project measured to be affected — see the source plan's before/after
  table) is reindexed once, manually, as part of this change's rollout (task: reindex on
  `feat/cpp-custom-top` with `exclude_dirs=[tests, vendor]`).
- If a future change needs cross-project staleness detection tied to chunk shape specifically
  (not BM25 document format), that is a new, purpose-built mechanism — not a repurposing of
  `INDEX_VERSION` and not a resurrection of this deferred `chunker_version` marker without first
  designing how it avoids false-alarming non-affected languages.

## Out of scope

- Automatic re-chunk triggering for stale C/C++ indices. Deferred until a real second instance of
  "chunker changed, files didn't" makes a generic mechanism worth building.
