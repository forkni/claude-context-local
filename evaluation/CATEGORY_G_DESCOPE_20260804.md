# Category G global/thematic queries: DESCOPED (2026-08-04)

## Verdict: DESCOPED — not graded, not promoted, not scheduled

`evaluation/golden_dataset_g_draft.json` holds 14 Category G queries (QG01–QG14),
drafted 2026-07-30, status `"DRAFT — NOT PROMOTED"`. **They stay in that state.**
The file is not deleted, not modified, and not merged into `golden_dataset.json` or
`golden_dataset_expanded.json`. This closes G out on the same precedent as
`evaluation/COMMIT_MINED_I_DESCOPE_20260802.md` (I-category), rather than leaving it
as a silently stalled to-do.

## What G is

Global/thematic queries — "trace how X travels from A to B", "how does the indexer
keep BM25 and dense in sync" — with LLM-drafted golds scoped to `expected_files`
(file-level sets), not `expected`/`expected_primary` chunk IDs at the usual grade-3
precision. All 14 rows carry `expected_files`; none have been human-graded. They were
authored for the community-detection ablation benchmark, which no longer exists
(`docs/adr/0015-remove-community-subsystem.md` removed that subsystem) — G's only
consumer is gone.

## Why this isn't "just grade 14 rows and merge"

The previous plan draft treated G's blocker as a missing scorer. That's wrong — the
scorer exists: `calculate_file_recall_at_k` (`evaluation/metrics.py:984`) backs
`file_recall_strict`/`file_recall_expanded`, and every query in every run already gets
`file_recall@{5,10}`/`file_acc@{5,10}` reported (`evaluation/metrics.py:486-487`).
Wiring is not the gap.

The actual blocker is the same one that closed I-category:

1. **File-level sets aren't what the harness gates on.** `file_recall@k` /
   `file_acc@k` are secondary reporting metrics everywhere they appear; promotion
   thresholds, `test_golden_set_guard.py`, and `test_mcp_eval_regression.py` are all
   built around rank-sensitive chunk metrics (MRR, `recall@k` over `expected`). A
   file-set query scored only by a secondary metric has no primary signal to gate on
   — promoting it into the canonical/expanded datasets would silently sit outside
   every threshold check that currently protects those datasets.
2. **Nobody has human-graded these 14 rows.** They are LLM drafts against a deleted
   consumer; grading effort here has no benchmark to report into even if every row
   turned out clean.
3. **Precedent.** Same reasoning as I-category's descope: don't ship dataset changes
   the scorer can't reliably *gate* on — extend the promotion/threshold tooling to a
   file-level primary metric first, then revisit the data.

## Disposition

- `evaluation/golden_dataset_g_draft.json` is **unmodified** — all 14 QG rows stay
  exactly as drafted, status `"DRAFT — NOT PROMOTED"`.
- No `golden_dataset.json` / `golden_dataset_expanded.json` changes from this
  decision.
- No benchmark re-runs required — nothing in the retrieval or scoring path changed.

## Reopening condition

Revisit only if either becomes true:

- A file-level or set-level metric is promoted from secondary reporting to a
  **primary**, gate-checked metric (i.e. `test_golden_set_guard.py`/
  `test_mcp_eval_regression.py`-equivalent coverage exists for `file_recall@k`), so a
  promoted G query has something to be gated on.
- A concrete new consumer for file-level thematic queries appears (the community
  ablation G was drafted for is gone; G has no current use).

If either lands, human-grading is a review pass over 14 existing rows, not a new
authoring effort — `golden_dataset_g_draft.json`'s `expected_files`/`expected` are
already populated, only the "human-graded" step is missing.

## Deliverables

- This document.
- No code change, no re-baseline (mirrors the I-category closeout).
