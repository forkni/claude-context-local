# Chunking A/B: Community Merge (calibrated budgets) vs Merge-Off (2026-07-28)

## Verdict: REJECTED (do not enable now — with a large measurement caveat)

`enable_community_merge` stays `false` in the live config. On the strict
SSCG scorer the treatment regressed MRR by −0.090 (0.727 → 0.637 mean of
×2), far outside the ±0.02 adoption gate. However, the regression is
**mostly a scoring artifact, not a retrieval failure**: the benchmark
scorer matches on `file:type:name` and merged chunks
(`chunk_type=merged`, named after one representative symbol) can never
equal a golden ID even when they contain the exact target lines at rank 1.
Under containment-credit rescoring the gap collapses to ≈ −0.018 — at the
edge of the noise band. A fair re-evaluation requires scorer changes and
two integration fixes (see Follow-ups); per project direction the
workstream now prioritizes tuning chunking itself, and community merge is
deferred.

## Motivation

Stage-1 corpus study (`CHUNKING_CORPUS_ANALYSIS_20260728.md`): the live
merge-free config leaves 37.5% of content chunks under 150 real F2LLM
tokens (788/2,101), a fragmentation tail that dilutes dense retrieval.
The study also found the community-merge budget check unreachable
(`elif` ordering); that defect was fixed same-day in `cedcc87` with
regression tests, making community merge activatable config-only.
Post-fix simulation variant D (community merge, calibrated budgets
63/354 ws-tokens ≈ 150/840 real) predicted small-chunk share 37.5% →
30.0% with **zero tail inflation** (chunks > 2,048 real stay at exactly
the baseline 47). This A/B validates variant D against the 77-query SSCG
golden set.

## Protocol

- **Arms**: `merge_off_baseline` (live config: merge off, budgets
  50/1000) vs `merge_on_calibrated` (`enable_community_merge: true`,
  `min_chunk_tokens: 63`, `max_merged_tokens: 354`; all other config
  identical). ×2 replicates per arm.
- **Procedure**: baseline runs on the existing index; treatment config
  applied by editing `search_config.json` (hot-reloads on mtime), then a
  full non-incremental reindex (`tools/batch_index.py --mode force`,
  45.4 s; merge log: 2,101 → 1,940 content chunks, −7.7%; index total
  2,146 with 114 `merged` chunks). Benchmark:
  `scripts/benchmark/run_sscg_benchmark.py --project-path .`, golden set
  `evaluation/golden_dataset.json`, 63 scored queries (category D
  excluded by default).
- **Restore**: config restored byte-identical from `.bak` (cmp-verified,
  backup deleted), full force reindex back to baseline shape (2,306
  chunks, zero `merged`, BM25/dense synced), sanity search clean.
- **Gate**: ±0.02 MRR single-run noise band (project history).

## Results (strict scorer, mean of ×2)

| Metric | merge_off (r1 / r2) | merge_on (r1 / r2) | Δ (mean) |
|---|---|---|---|
| MRR | 0.724 / 0.730 (**0.727**) | 0.640 / 0.634 (**0.637**) | **−0.090** |
| Recall@5 | 0.573 / 0.577 | 0.488 / 0.484 | −0.089 |
| Recall@20 | 0.760 / 0.766 | 0.650 / 0.646 | −0.115 |
| Pool hit rate | 0.984 / 0.984 | 0.936 / 0.952 | −0.040 |
| Line recall | 0.915 / 0.952 | 0.921 / 0.911 | −0.018 |

Replicate spread is ≤ 0.006 MRR within each arm — the strict gap is
stable and real *at the scorer level*. Note line recall is essentially
flat: when results do match, the treatment surfaces the right lines just
as well, a first hint the deficit is identity-matching, not content.

### Containment-credit rescoring (generous)

The scorer normalizes IDs via `evaluation/metrics.py:normalize_chunk_id`
→ `search.chunk_id.dedup_key`, matching `file:type:name`. A merged chunk
has `type=merged` and the name of one representative member, so it can
**never** match a golden expectation — even when it contains the target
symbol's exact lines at rank 1. Rescoring that credits a merged chunk
when it demonstrably contains the expected symbol in the expected file:

| Run | Strict MRR | Generous MRR |
|---|---|---|
| merge_off r1 / r2 | 0.724 / 0.730 | 0.732 / 0.738 |
| merge_on r1 / r2 | 0.640 / 0.634 | 0.717 / 0.716 |

Gap under containment credit: **≈ −0.018** (0.735 vs 0.717 means) — at
the edge of the ±0.02 noise band. And this still *under*-credits the
treatment (see Q40 below), so true parity is plausible.

## Miss-set analysis

Eight queries account for the strict regression: Q01, Q36, Q38, Q39,
Q42, Q48, Q49, Q88 — in every case the golden target was retrieved
inside a merged container that the scorer cannot match.

- **Q01**: golden targets retrieved at ranks 1 and 6 as merged
  containers; strict score 0.0.
- **Q38 / Q39 / Q42**: target code at **rank 1** inside a merged chunk;
  strict score 0.0.
- **Q40 (containment proof, and the limit of name-based credit)**:
  expected `merkle/change_detector.py:method:ChangeDetector.get_files_to_remove`;
  treatment rank-1 was
  `merkle/change_detector.py:284-305:merged:ChangeDetector.get_files_to_reindex`.
  Source lines 284–305 contain **both** `get_files_to_reindex` (284–293)
  and the expected `get_files_to_remove` (295–305) — the chunk is simply
  named after its first member, so even name-based generous credit
  missed it. Line-range containment credit restores Q40 to MRR 1.0
  (baseline scored 1.0).
- Pool-hit-rate dip (0.984 → 0.936/0.952) has the same cause: golden IDs
  absent from the pool because their chunks were absorbed into merged
  containers, not because retrieval failed to fetch the code.

## Integration defects found (dormant with merge off)

Both discovered while auditing the treatment index's storage artifacts;
neither affects the live merge-off configuration.

1. **Inverted line ranges in merged chunks (2/114)**. The chunker emits
   `module_preamble` *after* all symbol chunks, and
   `_create_merged_chunk` (`chunking/languages/base.py:626-672`) takes
   `start_line` from `chunks[0]` and `end_line` from `chunks[-1]`,
   trusting emission order. When a file's last function merges with its
   preamble, the range inverts (e.g.
   `chunking/file_summarizer.py:79-11:merged:...`) and content is out of
   source order. Fix: sort members by `start_line` before merging (or
   take min/max).
2. **Community map not re-keyed after merge**. `CommunityStage`
   (`search/community_stage.py`) stores the community map *before*
   remerge, keyed by pre-merge chunk IDs. Post-merge IDs (all 114 merged
   chunks) are absent, so community-aware scoring in
   `search/ego_graph_retriever.py` (community-bounded expansion,
   cross-community penalty) and `search/subgraph_extractor.py` silently
   no-ops for merged chunks. Fix: re-key the stored map to post-merge
   IDs (representative's community) after remerge.

## Decision rationale

- The strict −0.090 fails the gate; enabling now would also ship the two
  defects above and make benchmark tracking incomparable with history.
- The generous −0.018 result means community merge is **not disproven**
  — the corpus-level win (30.0% small-chunk share, zero tail inflation)
  may well translate to neutral-or-better retrieval once measured
  fairly. But "not disproven" is not "proven": adoption requires a clean
  re-run, not a rescoring exercise.
- Project direction (2026-07-28): the main goal is adjusting chunking
  itself; community merge and its fixes are deferred rather than
  pursued now.

## What stays from this work

- Calibrated budgets (63/354 ws ≈ 150/840 real, 1 ws-token ≈ 2.369 real
  F2LLM tokens) — validated as binding and tail-safe post-`cedcc87`.
- The scorer-artifact diagnosis and per-query evidence, which any future
  merge evaluation must design around.
- Benchmark result JSONs: `benchmark_results/sscg_merge_off_baseline_20260728_{142030,142536}.json`,
  `benchmark_results/sscg_merge_on_calibrated_20260728_{143418,143943}.json`.

## Follow-ups (prerequisites for any future merge adoption)

1. Scorer containment credit in `evaluation/metrics.py`: match merged
   chunks via `merged_from` membership or line-range containment against
   golden expectations (Q40 shows name-based credit is insufficient).
2. Fix `_create_merged_chunk` member ordering (inverted ranges).
3. Re-key the stored community map to post-merge chunk IDs.
4. Only then: re-run this A/B; gate unchanged at ±0.02 MRR.
