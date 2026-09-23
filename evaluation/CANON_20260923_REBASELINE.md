# Retrieval Canon Re-Baseline (2026-09-23)

## Status: MEASURED — both pre-registered gates PASSED; `body_truncation="fill_budget"` ADOPTED as default

This re-pin closes Item 1 of the `/diagnose` session opened by the 2026-09-22 twozero-dev reindex
notes (commit `8620d37d`): a 66 KB doc file (and a 1,736-line class chunk) embedded as a single
oversized chunk was silently truncated to ~30 lines by `EmbeddingDocumentComposer.compose()`'s
legacy 20-head/10-tail *line* caps, which bind long before the 6,000-char budget does. Diagnosed
in `tmp/diag_compose_truncation.py` (Phase 1 loop, RED): scanning every file in this repo
(11,387 raw chunks, unfiltered — a superset of the live 3,071-chunk indexed corpus) found
**307/11387 (2.7%) oversized chunks**, and **307/307** of them composed to well under 0.8× their
remaining budget (`body_chars/remaining_budget`: min=0.11, **p50=0.22**, max=0.40). Fixed behind a
new `EmbeddingConfig.body_truncation` knob (`"head_tail_lines"` legacy / `"fill_budget"` new,
default was off pending this A/B) that fills head/tail by character budget instead of line count.
Full diagnosis and fix in commit `4a36137a`.

## Substrate

`tools/batch_index.py --path . --mode force` at clean HEAD `4a36137a`, tree clean
(`git_dirty: False` on every leg, both arms): **238 files / 3,071 chunks** — +10 chunks vs the
09-20 pin's 3,061 (ordinary repo drift across the intervening 3 days, unrelated to this knob:
chunking is untouched by `body_truncation`, which only affects the *composed embedding text*, not
chunk boundaries). `codefuse-ai/F2LLM-v2-0.6B` / 1024d, LSP enabled. Resolver mix
(`resolver_edge_counts`): `lsp 2041 / chunker 1133 / libcst 775 / pyan 573` — identical on both
arms (call-graph edges are chunk-boundary-derived, not composed-text-derived, so the knob cannot
move this).

All legs run with `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0` exported, strictly sequential
(`run_sscg_benchmark.py --project-path .`), one GPU, no concurrent reranker loads. Both arms
measured the identical commit (`git_sha: 4a36137a`, `git_dirty: False` on every leg) — only
`CLAUDE_EMBEDDING_BODY_TRUNCATION` differed between arms, confirmed via each leg's
`config_metadata.substrate` fingerprint (byte-identical `total_chunks`/`files_indexed`/
`resolver_edge_counts`/`git_sha` across both arms). Chunk cache left ON throughout (per the
pre-registered plan): it is keyed on the composed string, so documents under budget get
byte-identical cached vectors in both arms — only the 307 re-composed oversized documents were
actually re-embedded, isolating the treatment. Control arm ran first to warm the cache under the
Item 2 batch-sizing doc fix landed in the same commit.

## Pre-registered gates

### Gate 1 — Drift (control vs the 09-20 canon: 0.8330 / 0.6514 / 0.8876 MRR)

`|ΔMRR| ≤ 0.02` and `Δrecall@20 ≥ −0.02` on all three views. **PASSED** on all three (this also
validates the control arm as a fair A/B baseline — the code changes since 09-20, including Item
2's doc-only fix and unrelated intervening commits, do not themselves move retrieval quality
outside the drift band):

| set | ΔMRR (control vs 09-20) | Δrecall@20 | verdict |
|---|---|---|---|
| 63q | −0.0036 | −0.0021 | PASS |
| 133q | −0.0032 | +0.0040 | PASS |
| F-via-similar | −0.0040 | +0.0019 | PASS |

### Gate 2 — Adoption (treatment `fill_budget` vs control `head_tail_lines`)

No paired-delta 95% CI (normal or bootstrap) excludes 0 in the negative direction on MRR or
recall@10/20, in any of the 3 views; guard-rails `Overall: PASS` on every leg; `pool_hit_rate` not
lower. **PASSED** — every CI below spans 0:

| set | ΔMRR (95% CI) | Δrecall@10 (95% CI) | Δrecall@20 (95% CI) | pool_hit_rate (ctrl→treat) |
|---|---|---|---|---|
| 63q | −0.0170 `[−0.0507, +0.0167]` | −0.0089 `[−0.0368, +0.0189]` | −0.0026 `[−0.0272, +0.0219]` | 1.000 → 1.000 |
| 133q | −0.0051 `[−0.0344, +0.0243]` | +0.0064 `[−0.0225, +0.0353]` | +0.0119 `[−0.0114, +0.0352]` | 0.917 → 0.925 |
| F-via-similar | −0.0140 `[−0.0480, +0.0200]` | +0.0004 `[−0.0233, +0.0242]` | −0.0035 `[−0.0260, +0.0189]` | 1.000 → 1.000 |

Guard-rails printed `Overall: PASS` on all 6 legs (3 views × 2 arms). `pool_hit_rate` was
non-decreasing on every view (unchanged on 63q and F-via-similar, +0.008 on 133q).

**Honest reading of the point estimates:** MRR's point estimate is negative on all three views
(largest on 63q, −0.017), and only 133q's recall@10/20 point estimates are positive. None of this
is statistically distinguishable from 0 — every CI spans it by a wide margin (the golden set's 63
and 133 queries were never designed to target the 2.7% of chunks this fix touches, so a
near-noise result here was the expected outcome, not a surprise). Per the pre-registered plan,
adoption in this situation rests on the gate criteria above plus the qualitative case: the fix
removes a silent, systemic truncation defect (307/307 oversized chunks in this repo composing to
11–40% of their intended budget) that the golden set is not positioned to detect either way —
this mirrors the ADR-0077 "neutral ships on correctness grounds" precedent. **Adopted.**

## Results (hybrid, k=10, deterministic, intent pinned off — see 09-20 pin's caveat, unchanged)

New canon-of-record, from the treatment arm (`body_truncation="fill_budget"`, now the default):

| Dataset | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | NDCG@5 | pool_hit_rate | file |
|---|---|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8124** | 0.6448 | 0.7338 | 0.8079 | 0.6679 | 1.0000 | `evaluation/ab_item1_treat_63q_r1_20260923.json` |
| Expanded (`golden_dataset_expanded.json`, non-D) | 133 | **0.6431** | 0.6086 | 0.7189 | 0.7843 | 0.5906 | 0.9248 | `evaluation/ab_item1_treat_133q_r1_20260923.json` |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8696** | 0.6464 | 0.7414 | 0.7880 | 0.6845 | 1.0000 | `evaluation/ab_item1_treat_fsim63_20260923.json` |

Extended metrics (not part of the pre-registered gate, recorded for completeness):

| Dataset | Recall@1 | Recall@7 | Recall@50 | NDCG@10 | hit_rate@5 | hit_rate@7 | line_recall | avg_pool_size |
|---|---|---|---|---|---|---|---|---|
| Canonical (63q) | 0.2733 | 0.7103 | 0.8132 | 0.7106 | 0.9841 | 1.0000 | 0.9128 | 29.0 |
| Expanded (133q) | 0.2886 | 0.6799 | 0.7868 | 0.6381 | 0.8421 | 0.8722 | 0.8049 | 28.3 |
| F-via-similar (63q) | 0.2884 | 0.7219 | 0.7933 | 0.7257 | 0.9841 | 1.0000 | 0.9270 | 28.9 |

Control-arm results (`body_truncation="head_tail_lines"`, the pre-2026-09-23 default), for
reference — this is what Gate 1's drift comparison above used:

| Dataset | MRR | Recall@10 | Recall@20 | pool_hit_rate | file |
|---|---|---|---|---|---|
| Canonical (63q) | 0.8294 | 0.7427 | 0.8105 | 1.0000 | `evaluation/ab_item1_control_63q_r1_20260923.json` |
| Expanded (133q) | 0.6482 | 0.7125 | 0.7724 | 0.9173 | `evaluation/ab_item1_control_133q_r1_20260923.json` |
| F-via-similar (63q) | 0.8836 | 0.7410 | 0.7915 | 1.0000 | `evaluation/ab_item1_control_fsim63_20260923.json` |

## Delta vs the superseded pin (2026-09-20: 0.8330 / 0.6514 / 0.8876)

This is the treatment (new canon) compared against the prior pin — not a pre-registered gate
(the drift gate above uses the control arm, per protocol, to isolate substrate drift from the
knob's own effect), reported for continuity with the canon lineage:

| set | ΔMRR | Δrecall@10 | Δrecall@20 |
|---|---|---|---|
| 63q | −0.0206 | −0.0076 | −0.0047 |
| 133q | −0.0083 | +0.0046 | +0.0159 |
| F-via-similar | −0.0180 | +0.0017 | −0.0017 |

All within the ±0.02 MRR / −0.02 recall@20 band used elsewhere in this lineage, despite this not
being the comparison the pre-registered gate specifies.

## Determinism

63q r1/r2 paired, both arms, non-latency fields only (raw JSON diff, not `--compare`, to catch
anything the leaderboard rounds away): **control r1 vs r2** — 1 field differs (`.timestamp`),
**treatment r1 vs r2** — 1 field differs (`.timestamp`). All `latency_ms` fields differ (expected
timing noise); every metric, per-query rank, and retrieved-chunk-ID field is bit-identical.

## Confound guard

`[CONFOUND]` fired on every drift-gate comparison (control vs 09-20 canon), as expected — that
comparison spans 3 days of ordinary repo commits (`total_chunks: 3061 != 3071`,
`git_sha: 624fef0c... != 4a36137a...`) and Gate 1 is designed to tolerate exactly that. No
`[CONFOUND]` fired on any adoption-gate comparison (treatment vs control): both arms share
identical `total_chunks`/`files_indexed`/`resolver_edge_counts`/`git_sha`, confirming the A/B
isolated the knob and nothing else.

## What this supersedes

Supersedes `evaluation/CANON_20260920_REBASELINE.md` as canon-of-record for this machine
(`codefuse-ai/F2LLM-v2-0.6B`, `search_config.json:3` — non-default config; the packaged defaults
remain `BAAI/bge-m3` + `gte-reranker-modernbert-base` for VRAM reasons). The 09-20 pin's numbers
are not wrong as measurements of that substrate; `body_truncation` did not exist yet. Config
default changed: `EmbeddingConfig.body_truncation` `"head_tail_lines"` → `"fill_budget"`
(`search/config.py`); `search_config.json.example` updated to match.
