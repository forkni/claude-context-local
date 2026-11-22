# Canon re-pin after the golden label audit (2026-11-22)

## Status: CANON OF RECORD — supersedes `CANON_20261019_CUDNN_ATTN.md` and the 2026-11-18 torch 2.13 pin

| View | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | pool_hit_rate |
|---|---|---|---|---|---|---|
| 63q (`golden_dataset.json`) | 63 | **0.8458** | 0.6509 | 0.7686 | 0.8539 | 1.0000 |
| 133q (`golden_dataset_expanded.json`) | 133 | **0.7162** | 0.6702 | 0.7951 | 0.8544 | 0.9624 |
| F-via-similar | 63 | **0.8983** | 0.6479 | 0.7748 | 0.8282 | 1.0000 |

Substrate: HEAD `ae0feb7e`, incremental reindex before the legs (250 files, 3,380 chunks),
`codefuse-ai/F2LLM-v2-0.6B`, `jinaai/jina-reranker-v3` on cuDNN attention, torch 2.13.0+cu130.
`CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0`, k=10, hybrid, `run_sscg_benchmark.py --project-path .`.
The MCP server stayed up, with no calls made to it during the legs. Dumps:
`evaluation/canon_<leg>_20261122.json` (local, not staged).

## Why the numbers moved

The label change is the whole delta. On the same index, the old labels give 63q 0.8273 and 133q
0.6718, against 0.8246 / 0.6718 in the 2026-11-18 pin (drift +0.0027 / 0.0000).

| View | Old labels | New labels | Delta | Result lists identical | MRR movers |
|---|---|---|---|---|---|
| 63q | 0.8273 | 0.8458 | +0.0185 | 63 / 63 | Q34 0.50 -> 1.00, Q55 0.33 -> 1.00 |
| 133q | 0.6718 | 0.7162 | +0.0444 | 133 / 133 | the 9 queries below |

63q r1 == r2: 63 / 63 retrieved lists identical.

## The label audit

Deep-research report candidate 2, narrowed. The audit read the rank-1 chunk of every query
whose gold chunk was in the pool but not at rank 1: 42 on 133q, 10 on 63q (canon legs
`ab_torch213_t*_20261118`). One reviewer (Claude Opus 5.5) read the code for each and classified
it: HOLE (correct answer, missing from the labels), PARTIAL or WRONG. Result: 133q 9 HOLE /
26 PARTIAL / 7 WRONG; 63q 2 HOLE / 8 PARTIAL. The project owner approved all fixes, the three
borderline calls (Q55, Q117, Q128) included.

Grade 3 added (so they count for MRR):

| Query | Added chunk | Why |
|---|---|---|
| Q34 | `FaissVectorIndex.add` | It normalizes, adds to FAISS and records chunk ids: how the class stores embeddings |
| Q55 | `ChangeDetector` (was grade 1) | Builds the current MerkleDAG and diffs it against the snapshot |
| Q114 | `TextPreprocessor._tokenize_identifiers` | Makes the camelCase / snake_case sub-tokens; the labelled `preprocess_code` calls it |
| Q117 | `_uri_to_path` (was grade 1) | Holds the only `%3A` drive-colon handling |
| Q128 | `derive_symbol_hint` | Recovers path and symbol from a drifted chunk id for the symbol retry |
| H003 | `TreeSitterChunker._log_parse_error_outcome` | Added in the labelled commit; it lowers the log level to DEBUG |
| H032 | `RelationshipAnalyzer._resolve_by_symbol` | The tiered lookup moved here out of the labelled `_resolve_target` |
| H064 | `handle_clear_index` | Purges every model directory's index files, BM25 included |
| H066 | `handle_get_index_status` | Calls `get_searcher()` lazily and sets `stats["synced"]` |

Set to grade 0 (wrong labels): Q04 `CodeIndexManager.validate_index_consistency` (checks counts,
not the id format); Q117 `_encode` (JSON-RPC framing, nothing to do with URIs).

Two causes: labels that were incomplete from the start (Q34, Q55, Q114, Q117, Q128), and
commit-mined H labels that went stale when the logic moved into a new function (H003, H032,
H064, H066). The old chunks still exist, so nothing flagged the stale labels. Repeat this audit
after refactors that extract helpers.

## Context: evaluation power (same day)

Per-query paired MRR differences in the stored A/Bs: sd 0.063-0.071 for reranker and model
changes, 0.115-0.173 for chunking changes. Smallest detectable change (80% power): 133q
0.016-0.017 for reranker and model A/Bs, 0.028-0.042 for chunking; 63q 0.022-0.048, so 63q is a
guard, not a detector. Only 16-24 of 133 queries move per A/B. Reordering the reranker's input
window alone (same members) moves 133q reranker-output MRR by -0.004 to +0.017 over 25-35
queries (`tmp/probe_rerank_order.py`), so the order noise floor is about the size of the gate.

## Next action

The owner re-runs this audit after a large refactor, and pre-registrations quote the smallest
detectable change beside each CI.
