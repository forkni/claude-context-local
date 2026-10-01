# Hide FAISS positions behind `CodeIndexManager`

Status: accepted
Date: 2026-10-01

## Context

The 2026-10-01 architecture review (candidate 2) found search-layer modules reaching through
`CodeIndexManager` into `FaissVectorIndex`: `multi_hop_searcher` and `ego_graph_retriever` each
rebuilt a full `{chunk_id: faiss_position}` dict from `dense_index.chunk_ids` on every query
(O(N) per call, two copies) and called `_faiss_index.reconstruct` themselves. `hybrid_searcher`
and `index_sync` repeated `x.index.ntotal if x.index else 0` eleven times although
`CodeIndexManager.ntotal` already returns 0 for a missing index, and `multi_hop_searcher` called
the private `_matches_filters`.

## Decision

- `CodeIndexManager.reconstruct_embeddings(chunk_ids) -> (rows, matrix | None)` owns the
  chunk-id-to-position mapping. `rows` index into the input for ids that are indexed; absent ids
  are simply not returned. FAISS errors propagate.
- Callers use `dense_index.ntotal`; `_matches_filters` became public `matches_filters`.
- Ego-graph retrieval keeps its decay path for neighbours with no embedding (and for
  `RuntimeError`/`AttributeError`/`IndexError` from reconstruction).
- `bm25_index._doc_ids` was left alone: `size` counts `_documents`, so equivalence is unproven.

## Consequences

Pure refactor (`08fdee98`). Gate: 63q determinism pair on the same index, `eccf0c9c` vs HEAD,
0 movers, aggregate identical apart from `latency_ms`; full unit suite green. FAISS position
details now live in one module, so a future index-kind change cannot silently break the
searchers.
