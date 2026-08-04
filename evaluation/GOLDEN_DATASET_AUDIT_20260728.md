# Golden Dataset Audit and Repair — 2026-07-28

Full-dataset alignment audit of `evaluation/golden_dataset.json` (77 queries) and
`evaluation/golden_dataset_expanded.json` (110 queries) against the freshly re-indexed
codebase (2,316 chunks / 2,063 normalized IDs, F2LLM-v2-0.6B index), plus root-cause
repair of the two persistent zero-MRR queries Q12 and Q99.

> **COMPARABILITY BREAK**: this repair changes gold labels for 20 queries. Aggregate
> MRR / recall / nDCG from any run on the repaired dataset are **not comparable** to
> numbers in reports dated before 2026-07-28. The `qfix_rebaseline_r1/r2` runs below
> are the new baseline.

## 1. Root cause of "stale" golds: dedup_key normalization asymmetry

`search/chunk_id.py:dedup_key` (used by `evaluation/metrics.normalize_chunk_id`)
rewrites `split_block` → parent kind (`method`/`function`) **only for 4-part IDs that
carry a line range**. Live index IDs always carry line ranges, so they always normalize
to parent-kind form. Golden IDs are stored 3-part (line range stripped), so a golden
`split_block:X` survives normalization unchanged — and can **never** match a live
chunk, even when the live index still chunks that exact symbol as a `split_block`
(verified for all 19 affected entries).

Consequences:

- Stale golds silently cap any-match recall (denominator counts them; no retrieved
  chunk can ever match). No error is raised anywhere.
- Production search is unaffected (live IDs are always 4-part).
- Repair rule going forward: **store golds in parent-kind form** — robust to both
  chunking outcomes. Enforced by the new audit script (§2).

A 2026-07-21 changelog entry had deliberately *added* `split_block` golds for Q19/Q32
("chunker emits split_block not method") — correct at the time it was written, but the
subsequent dedup_key rewrite silently turned those entries into permanent misses.

## 2. Reusable auditor: `scripts/benchmark/audit_golden_dataset.py`

Read-only script that normalizes every golden ID (`expected`, `expected_primary`,
`relevance_grades`) and checks membership in the normalized live-index ID set
(auto-locates `metadata.db` from `search_config.json` + `~/.claude_code_search`, or
takes `--metadata-db`). Prints stale entries with same-file/same-symbol retarget
candidates. Exit 0 clean / 1 stale / 2 error. Run it after any refactor or chunker
change.

Post-repair status: **CLEAN on both dataset files** (0 unresolvable golds); all 77
shared queries byte-identical between the two files.

## 3. Mechanical repairs (16 queries, 19 stale entries)

All `split_block:X` golds rewritten to parent-kind form, grades preserved, applied
identically to both files:

| Query (cat) | Retargeted symbol (split_block → method) |
|---|---|
| Q45 (B), Q64 (D) | `IncrementalIndexer.incremental_index` |
| Q46 (B), Q54 (C) | `HybridSearcher._apply_ego_graph_expansion` |
| Q50 (C) | `RRFReranker.rerank` |
| Q58 (D) | `handle_find_path` |
| Q60 (D) | `CommunityRefreshStage.run`, `IndexWriteStage.run` |
| Q62 (D) | `IncrementalIndexer.incremental_index`, `_check_auto_reindex` |
| Q65 (D) | `CodeGraphStorage.get_edge_data`, `GraphQueryEngine.find_path` |
| Q69 (E) | `IndexWriteStage.run` |
| Q83 (D) | `IncrementalIndexer._full_index` |
| Q88 (E), Q94 (F) | `GraphIntegration.build_graph_from_chunks` |
| Q90 (E) | `get_searcher` |
| Q19 (B), Q32 (C) | `CodeEmbedder.embed_chunks` — split_block entry **deleted** (method-form duplicate already present at the same grade 3) |

(Category D queries — Q58, Q60, Q62, Q64, Q65, Q83 — are excluded from scoring but
repaired for hygiene.)

## 4. Semantic repairs

### Q12 — "check if index exists for project" (was: pool miss, MRR 0.0)

- **Label repair**: added the most literal answer,
  `mcp_server/tools/status_handlers.py:decorated_definition:handle_get_index_status`,
  at grade 3 (expected + expected_primary). Existing golds kept (`has_snapshot` 3,
  `needs_reindex` 3, `MetadataStore.exists` 2, `handle_index_directory` 1).
- **Per-leg probes (repaired golds)**: BM25-only HIT (gold rank 3, MRR 0.333);
  semantic-only HIT (new gold rank 3, MRR 0.333). Both leg HITs are **post-rerank**
  ranks — the reranker rescues the golds inside single-leg pools.
- **Hybrid rides the fusion boundary**: golds' *raw* leg ranks are deep enough that RRF
  fusion (weights 0.35/0.65, rrf_k=100) only marginally admits them into the
  30-candidate rerank pool. Q12 MISSed in both `qfix_rebaseline` runs but **HIT in the
  expanded run under identical config** (MRR 0.333, pool_hit true) — run-to-run
  retrieval jitter decides whether a gold crosses the pool cut. This is a genuine
  **fusion-cut** retrieval shortfall, not a label problem: the labels are now correct
  and rescuable (the reranker ranks them top-3 whenever they enter the pool), and the
  query is retained as a legitimately hard case.
- **Regression timeline**: Q12 held pool_hit=true / MRR 1.0 through 2026-07-26 and
  early 2026-07-28, degraded 1.0 → 0.5 → 0.2 across the 07-28 force-reindex runs, and
  crossed to pool_hit=false at `sscg_merge_off_baseline_20260728_142030`. No single
  config change is responsible — corpus/embedding drift from the 07-28 full reindexes
  pushed a boundary-riding query over the edge.
- **Contributing pollution**: the 07-28 reindex swept in gitignored scratch files
  (18 `tmp/` chunks, 10 `code-search-extension/` chunks); `tmp/verify_fixes.py:
  function:seed_snapshot` ranks 5th in Q12's hybrid pool. Index hygiene follow-up
  filed separately.
- **Follow-up lever (out of scope here)**: `bm25_reserved_slots` A/B — Q12's golds are
  inside the BM25 top-30, so reserved BM25 slots could rescue it without label changes.

### Q99 — "find save and restore implementations similar to GraphIntegration.save" (was: ranking miss, MRR 0.0)

The entry violated the category-F rule it was labeled under: the grade-3 "cross-file
similar" tier held only same-class siblings. Repair per the rule:

- Added four cross-file persistence implementations at grade 3 (new expected_primary):
  `CodeGraphStorage.save`, `CodeIndexManager.save_index`,
  `HybridSearcher.save_indices`, `FaissVectorIndex.save`.
- Demoted `GraphIntegration.from_storage` 3 → 2 (same-class sibling; stays in
  expected).
- Result: Q99 now HIT — MRR 0.333, R@5 0.429 (r1).

## 5. Weak-query review (10 queries, fix-only-provable-mislabels rule)

| Query | Decision | Change / rationale |
|---|---|---|
| Q96 | **fixed** | + `SearchExecutor.search_dense`, `SearchExecutor._parallel_search` (grade 2). Query asks for methods that wrap "BM25 **or dense** retrieval"; sibling `_sequential_search` was already gold at 2. |
| Q97 | **fixed** | + `FaissVectorIndex.clear` (grade 2) — a lifecycle method the query explicitly asks for. |
| Q98 | **fixed** | + `ChunkEmbeddingCache.get` / `.put` (grade 3, expected_primary) — cross-file caching get/put implementations per the category-F rule. `QueryEmbeddingCache.put` kept at 3 (the query names "put" explicitly). |
| Q56 | **fixed** | + `CodeIndexManager.index` (grade 3) — the literal orchestration method for "what does CodeIndexManager orchestrate during indexing"; lesser methods were gold while the central one was missing. |
| Q33 | **fixed** | + `IncrementalIndexer.detect_changes` (grade 3) — the method named for the query subject, retrieved at rank 1, absent from golds. |
| Q04 | **fixed** | + `search/chunk_id.py:function:is_chunk_id` (grade 3) — the canonical validator; the dataset predates the `chunk_id.py` centralization and only credited the `graph_integration` twin. |
| Q70 | left as hard | Golds (concrete language-chunker `__init__`s) match the query exactly; near-identical constructors are genuinely hard for embedding retrieval. |
| Q95 | left as hard | Golds faithful; rank-1 interloper is benchmark scaffolding (`bm25_tokenizer_ab.py`), not a mislabeled answer. |
| Q55 | left as hard | Query targets MerkleDAG internals; retrieval preferring `ChangeDetector` is a ranking difficulty, not a labeling error. |
| Q01 | left as hard | Golds cover the config-lookup path correctly; retrieval prefers `ModelPoolManager` chunks (already graded 2). |

## 6. Re-baseline results (repaired primary dataset, 63 scored queries)

Pre-repair baseline (3 runs, 2026-07-28, merge-off): MRR 0.7236 / 0.7300 / 0.7371
(mean 0.7302), pool_hit_rate 0.968.

| Run | MRR | R@5 | R@7 | R@10 | HR@5 | nDCG@5 | pool_hit_rate |
|---|---|---|---|---|---|---|---|
| qfix_rebaseline_r1 | 0.7673 | 0.6144 | 0.6941 | 0.7632 | 0.9683 | 0.6351 | 0.9841 |
| qfix_rebaseline_r2 | 0.7686 | 0.5958 | 0.7095 | 0.7491 | 0.9841 | 0.6253 | 0.9841 |
| purge_tmp_rebaseline_r1 | 0.7825 | 0.6249 | 0.7099 | 0.7751 | 0.9683 | 0.6451 | 0.9841 |
| purge_tmp_rebaseline_r2 | 0.7774 | 0.5998 | 0.7011 | 0.7539 | 0.9683 | 0.6264 | 0.9841 |

New baseline: **MRR ≈ 0.768** (was 0.7302 pre-repair mean) — the two runs agree within
0.002, well inside the ±0.02 noise band. Q99 is stable at MRR 0.333 in both runs; Q12's
miss reproduces in both (fusion-cut, §4).

**2026-07-28 index-hygiene purge** (follow-up #2 below, resolved): full non-incremental
reindex excluding `tmp/` and `code-search-extension/` (2,316 → 2,293 chunks, −23 net after
203 files re-chunked). `purge_tmp_rebaseline_r1/r2` MRR 0.7825/0.7774 sits inside the noise
band above the `qfix_rebaseline` baseline — no regression. Verified zero `tmp/` or
`code-search-extension/` entries in any query's `retrieved` list across both runs (63
queries × 2 runs). **Q12 remained MISS in both runs** (MRR 0.0), confirming the audit's
diagnosis in §4 that Q12's failure is a fusion-cut ranking boundary, not tmp pollution —
tmp was only ever "contributing", never causal. `bm25_reserved_slots` (follow-up #1) is
still the open lever for Q12.

Expanded dataset (`qfix_expanded_r1`, 96 scored of 110): MRR 0.6545, R@5 0.6223,
R@7 0.7019, HR@5 0.9583, pool_hit_rate 0.9583 — PASS. Remaining misses are the known
expanded-only hard queries Q101/Q102/Q104/Q122 (query-expansion follow-up territory);
Q103 now hits (MRR 0.333). Notably **Q12 HIT in this run** (MRR 0.333, pool_hit true)
under identical config — see §4.

Verification checks:

- Q99: MRR 0.333, R@5 0.429 (was 0.0) — target met.
- Q12: MISS in both rebaseline runs, HIT in the expanded run — **explained** (§4): the
  original "pool_hit true" target assumed a pure label problem; probes proved the
  labels are now correct and rescuable, and the residual instability is a boundary-
  riding fusion cut with a documented follow-up lever (`bm25_reserved_slots`).
- Per-query deltas vs the pre-repair baseline run
  (`sscg_containment_noop_check_20260728_151757`): all substantive gains sit on
  repaired queries (Q04 +0.167 MRR, Q33 +0.875, Q56 +0.5, Q54 +0.167, Q88 +0.5,
  Q97 +0.024, Q99 +0.333, plus recall gains on Q19/Q32/Q45/Q46/Q50/Q69/Q96); the
  remaining small deltas (Q48, Q74, Q77, Q86, Q92 …) match the documented ±0.02
  run-to-run retrieval jitter observed across the three pre-repair baseline runs.
- Audit script: CLEAN on both files; 77 shared queries in sync.

## 7. Follow-ups (out of scope for this repair)

1. **`bm25_reserved_slots` A/B** for fusion-cut misses (Q12 is the test case).
2. ~~**Index hygiene**: full reindex currently sweeps in gitignored `tmp/` and
   `code-search-extension/` files; purge and prevent (task filed).~~ **RESOLVED
   2026-07-28**: `tmp`/`temp` added to `DEFAULT_IGNORED_DIRS`
   (`chunking/language_registry.py`), `code-search-extension` added to this project's
   `user_excluded_dirs`, live index purged (see re-baseline row above). Full `.gitignore`
   parsing remains a separate, deliberately out-of-scope follow-up (would change the
   corpus for every indexed project — needs its own ADR).
3. **Query expansion / multi-query retrieval** — the only identified lever for
   Q103/Q122-class expanded-set misses.
4. Scoring category F through `find_similar_code` instead of `search_code`
   (harness change).
