# Explicit `PassKind` for the chunk cache; index-kind invariant pinned

Status: accepted
Date: 2026-10-01

## Context

Architecture review candidates 5 and 6.

Candidate 5: `ChunkEmbeddingCache.save/_evict` took `full_pass: bool = True` (threaded through
`embed_chunks` as `cache_full_pass`). A new incremental caller that forgot the flag would silently
get the full-pass eviction cap and collapse the cache to the live set.

Candidate 6: `CodeIndexManager.add_embeddings` picks flat vs IVF from the first batch
(`index_kind_for`). That is correct only because `IndexWriteStage.add_to_index` adds every vector
in one call. The review proposed plumbing `expected_total` through four hops.

## Decision

- `PassKind` (`FULL` / `INCREMENTAL`) in `embeddings/chunk_cache.py` replaces the bool. It is a
  required keyword on `save`, `_evict`, `IndexWriteStage.embed_and_attach_metadata`, and on
  `embed_chunks` whenever `cache` is given (`ValueError` otherwise). No default.
- C6 is **not** plumbed. With a single `add_to_index` call, `expected_total` would always equal
  the first batch size, so it adds a parameter and no behaviour. Instead the invariant is
  documented on `add_embeddings` and `add_to_index`, and pinned by
  `tests/unit/search/test_indexer_initial_kind.py` (large batch -> IVF, small -> flat, kind
  frozen by the first batch). Revisit if a second batched caller appears.

## Consequences

- A forgotten pass kind fails loudly instead of degrading the cache.
- Retrieval is unaffected (refactor only).
- Deviation from the review's plan: no `expected_total` parameter.
