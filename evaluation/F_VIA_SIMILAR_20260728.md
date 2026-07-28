# Category F via find_similar_code — secondary benchmark view (2026-07-28)

**Outcome: shipped as an opt-in harness view (`--f-via-similar`, default off).
Official aggregates keep scoring F via `search_code` — no comparability break.**

The 9 category-F queries ("find implementations similar to X") describe exactly what the
`find_similar_code` MCP tool does, yet the benchmark has always scored them through
`search_code`, i.e. through query-text retrieval of a query that mostly *names an anchor
symbol*. This change measures F both ways: the official view (unchanged) and a flagged
secondary view that drives `HybridSearcher.find_similar_to_chunk(anchor, rerank=False)` —
the same call path as the shipped MCP handler.

## 1. Mechanics

- **Anchors**: each F entry in both dataset files now carries `anchor_chunk_id` — the
  normalized ID of the chunk named after "similar to" in the query text. In all 9 queries
  this is the grade-1 `relevance_grades` entry whose trailing symbol matches the named
  symbol, and it is never in `expected`/`expected_primary`, so ranked scoring is
  unchanged. (The plan's original "exactly one grade-1 not in expected" rule failed for
  7/9 queries; the named-symbol match rule is unique for all 9.)
- **Resolution**: anchors are stored normalized (stable across reindexes), but
  `find_similar_to_chunk` resolves through the MetadataStore / symbol cache, whose keys
  are raw 4-part IDs with line ranges and whose lookup is exact-string. The harness
  builds a one-time normalized→raw map from `metadata_store.items()` and requires
  exactly one raw candidate per anchor (`_resolve_anchor`); ambiguity or a stale anchor
  turns that row into an error row.
- **Validation**: `scripts/benchmark/audit_golden_dataset.py` now includes
  `anchor_chunk_id` in `gold_ids()`, so a stale anchor fails the audit (exit 1) with an
  `ANCHOR` marker. Current audit: CLEAN on both datasets.
- **Scoring**: `find_similar_to_chunk` returns SearchResult objects, so the metrics
  pipeline is unchanged. `pool_metrics` is empty for these rows — the call is a
  dense-only single-leg FAISS search with no fused pool (documented, expected).
  Latency is measured around the `find_similar_to_chunk` call alone.

## 2. Results — 9 F queries, post-cleanup index, k=5

Baseline = `search_code` F rows meaned over the three post-cleanup control runs
(`q12_reserve_0_r{1,2,3}`, 63q each). Similar-view = `--category F --f-via-similar`.
The dense-similarity path is deterministic (stored-vector reconstruct + exact FAISS
search, no reranker): a second run reproduced identical ranks.

| Aggregate | search_code (3-run mean) | find_similar | Δ |
|---|---|---|---|
| MRR | 0.4360 | **0.5444** | **+0.108** |
| Recall@5 | 0.5265 | **0.6452** | **+0.119** |
| Hit-rate@5 | — | 1.000 (9/9) | — |
| Mean latency / query | ≈ 4 470 ms | **1.8 ms** | ~2 500× |

The latency gap is structural: the similar path reconstructs the anchor's stored
embedding (no query-encoder forward pass, no reranker, no fusion/expansion pipeline).

Per query (MRR and R@5, baseline → similar):

| ID | MRR base | MRR sim | Δ | R@5 base | R@5 sim | Δ |
|---|---|---|---|---|---|---|
| Q70 | 0.134 | 0.500 | **+0.366** | 0.143 | 0.429 | +0.286 |
| Q71 | 1.000 | 0.200 | **−0.800** | 1.000 | 0.333 | −0.667 |
| Q93 | 1.000 | 1.000 | 0 | 1.000 | 1.000 | 0 |
| Q94 | 0.500 | 1.000 | **+0.500** | 0.333 | 1.000 | +0.667 |
| Q95 | 0.333 | 0.333 | 0 | 0.333 | 0.667 | +0.333 |
| Q96 | 0.159 | 0.200 | +0.041 | 0.600 | 0.600 | 0 |
| Q97 | 0.159 | 0.333 | +0.175 | 0.500 | 0.750 | +0.250 |
| Q98 | 0.306 | 1.000 | **+0.694** | 0.400 | 0.600 | +0.200 |
| Q99 | 0.333 | 0.333 | 0 | 0.429 | 0.429 | 0 |

## 3. Reading

- **5 improve, 3 flat, 1 regresses.** The wins are the queries where query-text
  retrieval struggles to get past the anchor's own file (Q70 chunker constructors,
  Q94 add_chunk analogs, Q98 cache get/put) — embedding-space neighbors are exactly
  the cross-file analogs the query asks for.
- **The one regression (Q71) is the mirror failure**: dense similarity's top ranks are
  dominated by *same-file* neighbors of the anchor (its own class chunk, module
  preamble, sibling `_extract_from_class`) before the true cross-file
  `_extract_from_tree` overrides appear. `search_code` happens to score 1.0 here
  because the query names the abstract hook, which BM25 nails. A future
  `find_similar_code` quality lever: optionally demote or filter same-file results —
  not pursued here.
- **Takeaway for tool routing**: for "find similar implementations" intents where the
  anchor is known, `find_similar_code` is both better (aggregate) and ~3 orders of
  magnitude cheaper than `search_code`. This matches the tool's intended use and is
  now measurable per release.

## 4. Additive-change guard (no-flag run)

A full 63q run without the flag after the harness change
(`p2_noflag_check`) reproduces the control baseline within the ±0.02 noise band —
aggregate MRR 0.778 vs 0.7838 control mean (Δ −0.006). All 9 F rows hit with per-query
MRR matching the control means within run noise (largest delta: Q70 0.091 vs 0.134,
a known rank-jitter query), and `f_via_similar` is absent from the run's
`config_metadata`. The change is purely additive when the flag is off.

## 5. Operational note

One early `--f-via-similar` run returned empty results for all 9 rows with 0 ms
latencies: that process had transiently failed to load the dense index ("No existing
index found", 0 vectors) — most likely a collision with the MCP server touching the
index files — and `CodeIndexManager.get_similar_chunks` returns `[]` silently when
`self.index is None` (`search/indexer.py:333-334`). This failure mode predates this
change (an unloaded index empties *every* search path); an all-zero F leaderboard with
~0 ms latencies is the signature. Re-running once the index load succeeds is the fix.

Result files (not committed): `benchmark_results/f_via_similar_r{1,2}.json`,
`benchmark_results/p2_noflag_check.json`.
