# Commit-mined I-category candidates: DESCOPED (2026-08-02)

## Verdict: DESCOPED — not graded, not promoted, not scheduled

Of the 194 commit-mined candidates in `evaluation/commit_mined_candidates.json`
(`_meta.category_counts`), the 68 H-category (bug-fix localization) candidates
were paraphrased, graded across 2 rounds, and 37 promoted into
`golden_dataset_expanded.json` on 2026-08-02 (`scripts/benchmark/merge_h_queries.py`,
see `evaluation/BASELINE_20260801.md`'s addendum). **The 126 I-category
candidates are formally descoped**: they will not be paraphrased, graded, or
promoted under the current scorer. They remain in
`commit_mined_candidates.json` as raw, ungraded data — not deleted.

## Motivation

The benchmarking-harness plan's Track 3 called for grading H first ("cleanest
signal"), then I. H's grading is done; this document closes out I rather than
leaving it as a silently stalled to-do.

## Why I doesn't fit the current scorer

Computed directly from `evaluation/commit_mined_candidates.json`
(`_meta.classification`: I = ">=3 matched functions, >=2 files"):

| | H (promoted) | I (descoped) |
|---|---|---|
| candidates | 68 | 126 |
| golds/query | mean 1.26, max 2 | mean **6.1**, median 5, max **19** |
| files/query | 1 (by construction) | mean **3.5**, median 3, max 11 |
| total golds across category | 86 | **766** |
| candidates with >10 golds | 0 | 12 |

1. **The harness can't score them at the comparability-fixed k.** Every
   Track-1/Track-3 SSCG run in this plan holds k=10 for comparability. A
   19-gold query caps recall@10 at 0.53 even for a perfect retriever, and MRR
   degenerates to "wherever the luckiest single gold landed" — a
   file-localization signal, not a ranking signal. `file_acc@k` /
   `file_recall@k` (added in `21a438c` specifically for this shape of query)
   are the correct instrument, but the golden-set thresholds and gating tests
   (`tests/unit/evaluation/test_mcp_eval_regression.py`,
   `test_golden_set_guard.py`) are built around rank-sensitive metrics, not
   file-rollup ones.
2. **The promotion bar would reject most of them anyway.** Grading H exposed
   bf16 neural-reranker batch-composition non-determinism: 4 of 42 queries
   that ranked top-10 in round 1 dropped to `pool_miss` in round 2 against the
   **same unchanged index**, purely from reranker batch-size effects at
   different query-set sizes (`BASELINE_20260801.md`'s addendum). That
   established a 2-agreeing-rounds bar for promotion. At 6.1 golds spread
   across 3.5 files, most I candidates would land in the same
   boundary-riding zone — roughly 9× H's total gold count would need
   re-verification for a low expected yield.
3. **Precedent.** Mirrors the reasoning that closed the sibling/community
   chunk-merge A/Bs (see `MEMORY.md`'s benchmark-findings entry): don't ship
   dataset changes the scorer can't reliably measure — fix or extend the
   scorer first, then revisit the data.

## Disposition

- `evaluation/commit_mined_candidates.json` is **unmodified in content** —
  all 126 I candidates stay exactly as mined, with `_meta.i_category_status`
  added pointing here (see below) so the raw file doesn't read as pending
  work.
- No `golden_dataset_expanded.json` changes from this decision.
- No benchmark re-runs required — nothing in the retrieval or scoring path
  changed.

## Reopening condition

Revisit only if either becomes true:

- The scorer gains a set-level or file-level **primary** metric usable for
  gating/promotion decisions (today `file_acc@k`/`file_recall@k` exist as
  secondary reporting metrics — see `evaluation/metrics.py`, `21a438c` —
  but promotion/threshold tooling is still rank-metric-centric).
- Containment credit (`evaluation/metrics.py:846-885`,
  `expand_retrieved_with_containment`) is extended to properly credit
  multi-gold, multi-file sets rather than single-chunk containment.

If either lands, grading is a run, not a build:
`grade_candidate_queries.py --candidates evaluation/commit_mined_candidates.json --only <I-ids>`
already works against this file (the `--candidates` flag was added
specifically to unblock H, and is category-agnostic).

## Deliverables

- This document.
- `evaluation/commit_mined_candidates.json`: `_meta.i_category_status` field
  added (see next commit in this closeout).
- No code change, no re-baseline.
