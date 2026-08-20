# Replace `SearchResult.source`'s bare `str` with a `ResultSource` StrEnum

Status: accepted
Date: 2026-08-19

## Context

`SearchResult.source` (`search/reranker.py`) is a retrieval-funnel provenance tag carried as a
bare `str`. Verified against the live index (`search_code`/`find_connections`, 2,564 chunks/215
files) rather than by grep alone: 13 distinct literals were stamped across 8 modules, with no
shared declaration, and six consumer sites branched on hand-typed string literals. Two of the
thirteen — `"dense"` and `"semantic"` — are two names for the same dense-retrieval channel
(`ResultFactory.from_dense_results` stamps `"semantic"`; `RRFReranker`/`SearchExecutor` stamp
`"dense"`), invisible today only because nothing consumes either value yet. Classic Primitive
Obsession; the fix is Replace Primitive with Object, following the in-repo precedent of
`SearchMode` (`search/config.py`).

`ResultFactory.from_similarity_results`/`from_expansion` also accepted an arbitrary `str` for
`source` with zero production callers passing anything but a known value — an unbounded interface
with no exercised generality.

## Decision

Added `ResultSource(StrEnum)` to `search/types.py`, grouped by funnel stage (leg / fusion /
expansion / lookup), with all 13 members holding today's exact string values, including both
`DENSE` and `SEMANTIC` kept as distinct members (unifying them is a behaviour-visible wire change,
deferred — nothing consumes either today, so nothing is lost by not unifying them here).

`SearchResult.source` is retyped to `ResultSource`, default `ResultSource.UNKNOWN`. No runtime
validation was added: dataclasses don't enforce annotations, and
`scripts/benchmark/probe_rerank_window.py --replay`'s `_SimResult` shim reconstructs pooled
results from captured JSON using plain `str` values — that must keep working unchanged, and does,
because `StrEnum` members hash and compare by value.

Every producer and consumer site was repointed at a member:

- **Producers**: `reranker.py` (`rerank_simple`/`rerank_tm2c2`/`rerank`), `result_factory.py` (all
  4 factory methods), `multi_hop_searcher.py`, `search_executor.py` (hybrid dense leg +
  query-expansion variant legs), `searcher.py` (`IntelligentSearcher._create_search_result`),
  `ego_graph_retriever.py` (3 call sites), `hybrid_searcher.py` (`_apply_parent_expansion`).
- **Non-`SearchResult` producer**: `subgraph_extractor.py`'s `_node_dict` stamps the same
  `"ego_graph"` wire value on a plain dict (ego-graph neighbor nodes in the SSCG subgraph) — this
  is exactly the drift the enum exists to prevent, so it uses the member too.
- **Consumers**: `types.py`'s `UNSCORED_SOURCES` frozenset, `reranking_engine.py`'s
  `_CHANNEL_TIER` dict and its three `== "graph_hop"` / `== "graph_hop"` band predicates
  (`_order_merged_pool`, `_apply_graph_hop_window_cap`), `hybrid_searcher.py`'s
  `drop_nonpositive_ego_results`, and two post-serialization dict consumers
  (`mcp_server/tools/result_view.py`'s `_annotate_each`, `search/graph_scoring_stage.py`'s
  `_extract_subgraph`) that compare `dict.get("source")` against the member — functionally a
  no-op either way since `StrEnum` equality against a plain string is unchanged, repointed for
  vocabulary consistency.

`ResultFactory.from_similarity_results`/`from_expansion` signatures were narrowed from `str` to
`ResultSource`. The only test referencing a non-member string (`test_from_tuples_sets_source_and_rank`,
against the private `_from_tuples` helper) needed no change — Python does not enforce parameter
annotations at runtime, so the plain string still round-trips exactly as before.

**Not touched**: `subgraph_extractor.py`'s `source=`/`_edge_dict`'s `e.source` on `SubgraphEdge`
(edge *source node*, an unrelated concept from provenance) and `graph_view.py`'s equivalents.

## Verification

- `./scripts/test/run_tests.sh tests/unit/search/ tests/unit/mcp_server/ -q` — 2,180 passed, zero
  test edits needed.
- `./scripts/git/check_lint.sh --modified-only` clean (ruff + pyrefly); `fix_lint.sh
  --modified-only` reformatted 2 files (line-wrapping only, from the `source="x"` →
  `source=ResultSource.X` token-length change).
- `scripts/benchmark/probe_rerank_window.py --replay evaluation/probe_rerank_window_20260815.json`
  — 124/124 usable queries, gate passes unchanged, matching the pre-change capture. This replay
  runs the real `_order_merged_pool`/`_apply_graph_hop_window_cap` predicates against `_SimResult`
  objects carrying plain `str` sources — the strongest available confirmation that `StrEnum`
  equality against replayed plain strings is unchanged.
- **Live-MCP wire byte-identity was not directly measured**: the running MCP server process loaded
  its modules before this change, so a live before/after `search_code` diff would only re-exercise
  the old code, not this change. Used the stronger in-process equivalent instead: the 4
  `tests/unit/mcp_server/test_search_results_snapshot.py` snapshot tests exercise
  `_format_search_results` (the sole `source`-to-wire emission site,
  `mcp_server/tools/result_view.py`) directly against `hybrid`/`dense`/`ego_graph` sources and all
  passed unchanged.

## Consequences

- One named vocabulary (`ResultSource`) for retrieval-funnel provenance; a typo can no longer
  silently create an unrecognized 14th channel.
- `DENSE`/`SEMANTIC` duplication is now named and comment-documented in one place rather than
  latent across two unrelated modules; unifying them remains future work, deliberately deferred.
- File-disjoint from Round 4b (`BaseSearcher`/`RetrievalRequest`) apart from `search/types.py`,
  where `ResultSource` now lives alongside `RetrievalRequest` — landed first per the round
  sequencing.

## Out of scope

- Unifying `DENSE`/`SEMANTIC` into one member — a behaviour-visible wire change with no current
  consumer forcing it.
- Round 4b (`BaseSearcher.execute` seam, `RetrievalRequest.build`) — separate ADR.
