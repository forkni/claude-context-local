# BM25 stopword A/B: `bm25_use_stopwords` True vs False (2026-08-01)

## Verdict: KEEP STOPWORDS

Recall-over-speed decision rule (project standing preference): drop stopword
filtering only if Recall@5/MRR hold within a −0.005 band with it off. Both
regressed past the threshold — `dRecall@5 −0.0349`, `dMRR −0.0138` — so the
import-time NLTK stopword-corpus download (`search/bm25_index.py` module
load) stays.

## Motivation

Dependency Optimization Plan, Phase F: decide whether
`nltk.data.find("corpora/stopwords")` / `nltk.download("stopwords",
quiet=True)` can be removed from the BM25 index module's import path. Mirrors
the Round-6/Track-A `bm25_tokenizer_ab.py` precedent — same harness shape,
same scoring path, one knob isolated.

## Protocol

`scripts/benchmark/bm25_stopwords_ab.py --project-path .` — **not** the live
hybrid pipeline. Both arms build a standalone in-process `rank_bm25.BM25Okapi`
index by re-tokenizing the on-disk `bm25_docs.json` corpus dump in memory
(`TextPreprocessor(use_stopwords=..., use_stemming=False, tokenizer="whole")`)
— no reindex, no embedding recompute, no MCP restart. Tokenizer held fixed at
`"whole"` (the shipped production default) across both arms so only the
stopword-filtering effect is isolated. Query-time and index-time tokenization
use the same preprocessor instance per arm, mirroring `BM25Index.search`.

- Corpus: 2,259 documents (the pre-incident index snapshot — see
  `BASELINE_20260801.md`'s provenance note).
- Dataset: `evaluation/golden_dataset.json` (default), 77 queries; the
  decision rule uses the 63-query **excluding-D** subset (14 category-D
  queries dropped), matching the canonical A–F set used elsewhere.
- k=10.
- Full JSON: `benchmark_results/bm25_stopwords_ab_20260801_220146.json`
  (gitignored, local).

## Results (excluding-D subset, 63 queries, k=10)

| Metric | stopwords_on | stopwords_off | Δ (off − on) |
|---|---|---|---|
| MRR | 0.4605 | 0.4467 | **−0.0138** |
| Recall@5 | 0.4519 | 0.4170 | **−0.0349** |
| Recall@10 | 0.5210 | 0.5134 | −0.0076 |
| NDCG@5 | 0.4112 | 0.3811 | −0.0301 |
| NDCG@10 | 0.4439 | 0.4243 | −0.0196 |
| hit_rate@5 | 0.7460 | 0.7143 | −0.0317 |
| acc@5 | 0.2063 | 0.1746 | −0.0317 |
| Tokenize time | 0.0998s | 0.0833s | −0.017s |
| Distinct stems | 12,039 | 12,165 | +126 |

All-categories (77 queries, informational — not the decision subset): MRR
0.3894 → 0.3760 (−0.0134), Recall@5 0.3825 → 0.3458 (−0.0367); same direction,
consistent with the excluding-D result.

Both variants independently `FAIL` the harness's built-in absolute
`pass_fail` thresholds for `mrr`/`recall@5`/`hit_rate@5` on both subsets —
those thresholds are calibrated for the live hybrid+reranker pipeline, not a
standalone BM25 leg, and are not the decision rule; the A/B **delta** is.

## Caveats

- **BM25-standalone, not the live hybrid pipeline.** This harness measures
  BM25 alone via an in-memory `rank_bm25` index rebuilt from the corpus
  dump — it does not exercise dense fusion, reranking, or multi-hop. The
  measured deltas describe the BM25 leg's contribution to retrieval, not the
  end-to-end `search_code` result a user would see.
- **Tokenization is baked in at index time.** Production adoption of a
  stopword-filtering change (either direction) would require rebuilding the
  live BM25 index (`index/bm25/`), not just a config flip — the on-disk
  `bm25_docs.json`/`bm25.index` reflect whatever `bm25_use_stopwords` was set
  when the corpus was last indexed.
- **No graded metrics emitted.** `run_variant` calls
  `calculate_metrics_from_results(retrieved, expected, expected_primary)`
  with three positional arguments (no `relevance_grades`) — per
  `evaluation/metrics.py:317-398` this is presence-based scoring by design,
  not a defect; `ndcg@5_graded`/`file_acc@*`/`hard_negative_intrusion_rate`
  are absent from this harness's output.
- **Index snapshot.** Corpus size (2,259 documents) matches the pre-incident
  index measured before this session's embedder-harness incident (see
  `EMBEDDER_GEMMA_AB_20260801.md`); the rebuilt index differs by one file
  (the deleted harness itself). Not re-run for this immaterial delta.

## Deliverables

- This document.
- `benchmark_results/bm25_stopwords_ab_20260801_220146.json` (gitignored,
  local — full per-query results for both arms).
- No code change: `bm25_use_stopwords` stays at its current default (`True`);
  the NLTK stopword-corpus dependency stays in `search/bm25_index.py`.
