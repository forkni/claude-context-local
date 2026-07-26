# Track D — BM25 path/symbol token augmentation (2026-07-26)

**Verdict: ADOPTED.** BM25 documents are augmented at build time with each chunk's
relative-path components and symbol name (whole + camel/snake sub-tokens via
`search.tokenization.build_path_symbol_text`). `INDEX_VERSION` 3 → 4. The persisted
`bm25_text` metadata stays **raw**; `augment_bm25_document` is applied in both
document-build paths (`HybridSearcher.add_embeddings` and
`IndexSynchronizer.resync_bm25_from_dense`), so augmentation is applied exactly once
no matter how often the BM25 index is rebuilt, and a version-mismatch resync upgrades
an old index without re-embedding.

Implementation commits: `0e15a3c` (v1), `57b199b` (A/B harness), plus the
raw-`bm25_text`/dual-path restructure commit that follows them on `development`.

## Primary gate — BM25-standalone A/B (PASS)

Harness: `scripts/benchmark/bm25_path_token_ab.py` — stored whole-tokenizer corpus
(2,174 docs, INDEX_VERSION 3) vs the same corpus with per-doc path/symbol tokens
appended (production `TextPreprocessor`, whole, stopwords on; BM25Okapi k1=1.5 b=0.75;
category-D excluded). Corpus growth: +15,345 tokens over 304,581 (**+5.0 %**, avg
+7.1 tokens/doc).

| Set | MRR | Recall@5 | Hit@5 | movers (R@5) |
|---|---|---|---|---|
| 63q | 0.3207 → **0.4337** (+0.113) | 0.3180 → **0.3992** (+0.081) | 0.5714 → **0.6825** | 13 ↑ / 1 ↓ |
| 96q | 0.2767 → **0.3600** (+0.083) | 0.2986 → **0.3589** (+0.060) | 0.5417 → **0.6458** | 16 ↑ / 2 ↓ |

Both regressions (Q75 −0.25, Q129 −0.5) are benign displacement — the gold stays at
rank 1; a secondary gold slips below the cut.

Full-corpus gold ranks for the three pool-miss queries barely move standalone
(Q102 19→20, Q103 1648→1650, Q122 1501→1503): their queries are pure paraphrases with
zero lexical overlap with path/symbol tokens ("repeated questions answered from
memory" shares nothing with `query_cache.get_stats`). The standalone win comes from
the broad mid-pack instead — identifier- and filename-flavored queries.

## Secondary gate — fused no-regression (PASS), replicated ×2, matched flags

`run_sscg_benchmark.py`, `--with-centrality --centrality-alpha 0.0 --k 7`, rebuilt
v4 index (2,182 docs — +8 from files added since the baseline build). Baselines:
`sscg_track_a_whole_{original,expanded}_confirm_20260726.json`. Noise floor ±0.02;
pool_hit/hit@5 carry ±1–2-query flicker.

| Set | Metric | Baseline | Track D r1 | Track D r2 |
|---|---|---|---|---|
| 96q | pool_hit | 0.9688 | **0.9792** | **0.9792** |
| 96q | hit@5 | 0.9583 | 0.9583 | 0.9583 |
| 96q | R@5 | 0.6696 | 0.6667 | 0.6784 |
| 96q | MRR | 0.6517 | 0.6290 | 0.6333 |
| 63q | pool_hit | 1.000 | 1.000 | 1.000 |
| 63q | hit@5 | 1.000 | 0.9841 | 1.000 |
| 63q | R@5 | 0.6715 | 0.6698 | 0.6817 |
| 63q | MRR | 0.7656 | 0.7580 | 0.7699 |

- **pool_hit improved and replicated**: expanded misses shrink {Q102, Q103, Q122} →
  **{Q103, Q122}** in both runs. Q102 — the fusion-cut miss whose gold sat at BM25
  rank 19 — now enters the rerank pool, exactly the mechanism predicted in
  `POOL_MISS_DIAGNOSIS.md`. (It is still a hit@5 miss: the reranker doesn't lift it
  to top-5 yet; pool entry is the prerequisite.)
- hit@5 miss set is **identical to baseline** in both expanded runs
  ({Q101, Q102, Q103, Q122}); the 63q r1 0.9841 is single-query flicker (r2 = 1.000).
- R@5 flat both sets; MRR −0.02 on the expanded set sits at the noise floor and does
  not replicate on the 63q set (r2 above baseline).

## Remaining misses

Q103 and Q122 are dense-leg-only rescuable: golds sit at BM25 full-corpus ranks
~1,650/~1,500 and no lexical knob (tokenizer, k1/b, path tokens) moves them. Any
further pool_hit work must target the dense leg or query-side expansion, not BM25.
