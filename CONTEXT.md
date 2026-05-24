# Domain Context

Terms and concepts that are meaningful to domain experts working on
claude-context-local. Implementation details belong in code comments; this
file captures the **why** and **what** of the domain language.

---

## Module summary

A synthetic `CodeChunk` with `chunk_type="module"` that summarizes a source
file as a whole. Generated deterministically by `chunking/file_summarizer.py`
from the file's AST metadata (imports, top-level definitions, docstring). One
per indexed file. Used as a retrieval unit for file-level queries and as
structural input to community summaries.

Not to be confused with **community summary** (which spans multiple files).

---

## Community summary

A synthetic `CodeChunk` with `chunk_type="community_summary"` that describes a
Louvain community of related source files. Generated deterministically by
`graph/community_summarizer.py` from the module summaries of the files in the
community, ranked by PageRank centrality. One per detected community. Enables
architectural-level retrieval ("which files implement the search pipeline?").

The community map is persisted via `graph/graph_storage.py:load_community_map()`
so incremental index runs can read it without re-running community detection.

---

## QueryIntent

An enum (`search/intent_classifier.py`) that classifies a user query by the
type of information sought. Values include:

- **LOCAL** — function/class detail within a single file.
- **GLOBAL** — architectural or cross-file questions ("how does search work?").
- **NAVIGATIONAL** — finding a specific named symbol.
- **CONTEXTUAL** — understanding the context around a code site.
- **PATH_TRACING** — following call chains or data flow.
- **SIMILARITY** — finding code structurally similar to a given example.
- **HYBRID** — queries that span multiple intent types.

Intent drives search mode selection, ego-graph weights, and multi-hop hop
count. The golden evaluation dataset currently covers only LOCAL and related
structural intents; GLOBAL queries are not yet benchmarked.

---

## Remerge

The post-community-detection step in `_full_index` that reassigns chunks to
their community's primary representative after Louvain detection. Chunks that
span multiple communities are merged under the highest-centrality community
member. The two-phase summary compute/append split in `_full_index` exists
specifically because chunk IDs change during remerge; summaries must be
computed after final chunk IDs are stable.

---

## Ego-graph expansion

A retrieval step that expands initial search results by traversing the code
graph `k` hops outward from each result node. Controlled by `EgoGraphConfig`.
Adds semantically related chunks (callers, callees, co-imported symbols) that
direct vector similarity would miss. Neural reranking is applied
post-expansion to unify scoring across primary and expanded results.

---

## Multi-hop search

A search mode that iteratively expands the query graph by following edges
between code chunks for a configurable number of hops. Implemented in
`search/multi_hop_searcher.py`. Complementary to ego-graph expansion: multi-hop
operates at query time before the initial result set is assembled; ego-graph
operates after.

---

## Merkle-DAG incremental indexing

The indexing strategy that tracks file content via a Merkle DAG
(`merkle/merkle_dag.py`) to detect additions, modifications, and deletions
between runs. Only changed files are re-chunked and re-embedded on incremental
runs. The change detector output (`FileChanges`) drives `_add_new_chunks` and
`_remove_old_chunks` in `search/incremental_indexer.py`.
