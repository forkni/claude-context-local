# SSCG canon re-pin: `canon_h1` — `_extract_symbol_from_query` repaired, `find_similar` re-gated on — 2026-08-04

Re-pins the published canon to `canon_h1` (supersedes `canon_g1`) after Round C of the intent-layer
disposition: `search/intent_classifier.py`'s `_extract_symbol_from_query` was rewritten to reuse
`_detect_code_symbols`' tokenizer/predicate machinery instead of its buggy reversed-word-list
fallback (`3f80f2a`), then judged against a pre-registered gate on the 9 similarity (category F)
golden queries. The gate **passed on both datasets**, so `intent.enabled`'s default flips back
`False` → `True` in this same round, with `find_similar` now firing for real.

## Substrate

`cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force` → **204 files, 2323
chunks** (37.38s; up from `canon_g1`'s 2322 — the extractor rewrite and its new regression tests net
+189/−43 lines across 4 files). `audit_golden_dataset.py` CLEAN on both datasets (77q/147q) against
the fresh index. `PYTHONHASHSEED=0` (ADR-0021) + `CLAUDE_AUTO_REINDEX=0` for every capture.

## Procedure

1. `cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force`.
2. `audit_golden_dataset.py` — CLEAN on both datasets.
3. `CLAUDE_AUTO_REINDEX=0` + `PYTHONHASHSEED=0` for every capture (harness self-pins and re-execs).
4. Five captures, **one round each** — the standing policy justified by `canon_f1`'s 63q
   determinism-control pair (0 flips):
   - `sscg_canon_h1_63q_r1.json`, `sscg_canon_h1_133q_r1.json` — intent-off control, no `--set`
     override (the harness's `pin_intent_off=True` default already asserts `intent.enabled=False`).
   - `sscg_canon_h1_fview_r1.json` — the find_similar correct-anchor ceiling (`--f-via-similar`,
     63q golden dataset; the F category's 9 queries and their `anchor_chunk_id`s are identical in
     both datasets, so one F-view capture serves as the ceiling for both gate judgments).
   - `sscg_canon_h1_arm_63q_r1.json`, `sscg_canon_h1_arm_133q_r1.json` — intent-on arm
     (`--set intent.enabled=true`), the repaired extractor exercised through the real
     `search_orchestrator.py` redirect path.

## Results

All five views returned overall **PASS**.

| metric | `h1` 63q control | `h1` 133q control | `h1` F-view | `h1` 63q arm | `h1` 133q arm |
|---|---|---|---|---|---|
| total / success | 63 / 63 | 133 / 116 | 63 / 63 | 63 / 63 | 133 / 118 |
| **mrr** | **0.8275** | **0.6607** | **0.8836** | **0.8418** | **0.6750** |
| mrr_excl_redirect | 0.8275 | 0.6607 | — | 0.8418 | 0.6750 |
| redirect_rate | 0.0 | 0.0 | — | 0.0 | 0.0 |
| recall@1 | 0.2733 | 0.2836 | 0.2902 | 0.2804 | 0.2907 |
| recall@5 | 0.6789 | 0.6567 | 0.6818 | 0.6967 | 0.6751 |
| recall@10 | 0.7869 | 0.7635 | 0.7963 | 0.8036 | 0.7766 |
| recall@20 | 0.8567 | 0.8287 | 0.8455 | 0.8488 | 0.8250 |
| recall@50 | 0.8567 | 0.8325 | 0.8455 | 0.8488 | 0.8288 |
| precision@1 | 0.8254 | 0.6541 | 0.9048 | 0.8571 | 0.6767 |
| ndcg@5 | 0.6961 | 0.6253 | 0.7086 | 0.7157 | 0.6428 |
| ndcg@10 | 0.7444 | 0.6705 | 0.7588 | 0.7617 | 0.6851 |
| hit_rate@5 | 1.0 | 0.8722 | 1.0 | 1.0 | 0.8872 |
| hit_rate@7 | 1.0 | 0.9023 | 1.0 | 1.0 | 0.9098 |
| line_recall | 0.9386 | 0.8511 | 0.9413 | 0.9280 | 0.8397 |
| file_recall@5 | 0.8300 | 0.8324 | 0.8277 | 0.8309 | 0.8328 |
| file_recall@10 | 0.9136 | 0.9121 | 0.9144 | 0.9121 | 0.9114 |
| pool_hit_rate | 1.0 | 0.9474 | 1.0 | 0.9048 | 0.9023 |
| avg_pool_size | 29.0 | 28.2 | 28.9 | 25.4 | 26.3 |
| avg_latency_ms | 4331 | 4368 | 3705 | 3940 | 4137 |

`redirect_rate`/`mrr_excl_redirect` track only the (now-deleted) `find_path` redirect and are 0.0 /
== mrr everywhere, per ADR-0028's note that this machinery is kept only for JSON-schema
comparability. The `find_similar` redirect's firing is visible per-query via the `redirect_kind`
field instead (below), not the aggregate `redirect_rate`.

## The gate — 9 similarity (category F) queries, both datasets

**Gate** (pre-registered, `docs/adr/0029-...md`): MRR must **exceed** the same-substrate normal-path
mean, and recall@20 must **not fall below** the same-substrate F-view (correct-anchor) mean.

| | control (normal path) | F-view (ceiling) | intent-on arm | gate |
|---|---|---|---|---|
| **mrr** (9 F queries) | 0.4594 | 0.8519 | **0.5593** | **PASS** — arm > control (+0.0999) |
| **recall@20** (9 F queries) | 0.7966 | 0.7185 | **0.7418** | **PASS** — arm ≥ F-view (+0.0233) |

Identical on both the 63q and 133q datasets — the 9 F queries score identically regardless of which
dataset they run inside, since each query is scored independently and neither dataset changes their
`anchor_chunk_id`/expected sets.

Per-query MRR, control → arm:

| query | control | arm | Δ |
|---|---|---|---|
| Q70 | 0.125 | 0.500 | +0.375 |
| Q71 | 1.000 | 0.200 | −0.800 |
| Q93 | 1.000 | 1.000 | 0.000 |
| Q94 | 0.500 | 1.000 | +0.500 |
| Q95 | 0.333 | 0.333 | 0.000 |
| Q96 | 0.143 | 0.333 | +0.190 |
| Q97 | 0.200 | 0.333 | +0.133 |
| Q98 | 0.333 | 1.000 | +0.667 |
| Q99 | 0.500 | 0.333 | −0.167 |

Q71's regression is not an extractor failure — `redirect_kind: "find_similar"` fired and correctly
anchored on `InheritanceExtractor._extract_from_tree` (its retrieved set is the class's own sibling
methods, not an unrelated symbol); `find_similar`'s embedding neighborhood simply ranks same-class
siblings above the cross-class override methods the golden set wants. Q71 is one of the four F
queries carrying a hand-authored `similar_exclude_same_file=True` annotation
(`project_benchmark_noise_and_pool_hit` memory) that the redirect has no way to see — exactly the
gap the pre-registered ceiling (0.54–0.61 realistic, not the raw 0.8519) already priced in. Measured
arm MRR (0.5593) lands inside that predicted band.

## Delta vs `canon_g1` — small, and it is substrate drift, not a behavior change

| metric | `g1` 63q | `h1` 63q control | Δ | `g1` 133q | `h1` 133q control | Δ |
|---|---|---|---|---|---|---|
| mrr | 0.8352 | 0.8275 | −0.0077 | 0.6667 | 0.6607 | −0.0060 |
| recall@5 | 0.6749 | 0.6789 | +0.0040 | 0.6623 | 0.6567 | −0.0056 |
| recall@10 | 0.7922 | 0.7869 | −0.0053 | 0.7660 | 0.7635 | −0.0025 |
| recall@20 | 0.8567 | 0.8567 | 0.0000 | 0.8325 | 0.8287 | −0.0038 |
| precision@1 | 0.8413 | 0.8254 | −0.0159 | 0.6617 | 0.6541 | −0.0076 |
| pool_hit_rate | 1.0 | 1.0 | 0.0000 | 0.9474 | 0.9474 | 0.0000 |
| avg_pool_size | 29.0 | 29.0 | 0.0000 | 28.1 | 28.2 | +0.1 |

The `h1` control views (intent still pinned off by the harness) are compared against `g1`'s own
intent-off views, isolating substrate drift from the +1 chunk / 189-insertion tokenizer-promotion
commit — consistent in size and direction with every prior same-round re-pin delta (`e1 → f1`,
`f1 → g1`).

## What changed in production that only the intent-on arm can see

The control views never route through `_extract_symbol_from_query` (`intent.enabled=False`), so they
cannot observe the fix — same structural reason `canon_g1`'s control views couldn't observe the
`find_path` deletion. The arm capture is the direct evidence: Q70's query used to extract `'hook'`,
Q71/others `'to'`/`'around'`, per the four documented misfires in `docs/adr/0029-...md`'s Context —
all real golden queries, re-verified this round via `IntentClassifier().classify(...)` in a fresh
process, all now returning the correct dotted anchor symbol (e.g. `InheritanceExtractor._extract_from_tree`
for Q71, confirmed by the retrieved set being genuine relationship-extractor siblings, not a
trailing-prose-word tangent).

## Comparability

- **`canon_h1`'s intent-on arm becomes the published baseline** (63q, 133q) — the first re-pin where
  the shipped default (`intent.enabled=True`, restored this round) matches what the numbers above
  measure, rather than the harness's `pin_intent_off` control. The control views stay published
  alongside it as the intent-off reference point, same as `canon_B1b` was captured as a named arm
  against `canon_f1`.
- `canon_g1` (intent-off default) remains the baseline for anyone running with `intent.enabled=false`
  (e.g. via a local `search_overrides.json` opt-out) — not re-derived here beyond the control views'
  substrate-drift check above.
- Capture JSONs (`evaluation/sscg_canon_h1_*.json`) are **not tracked in git**, per the precedent set
  by every prior canon capture — this markdown file is the durable record.

## ADR

See `docs/adr/0029-repair-symbol-extraction-and-regate-find-similar.md` for the architectural
decision this capture verifies, `docs/adr/0028-intent-off-by-default-and-remove-find-path-redirect.md`
for Round B's stopgap, and `docs/adr/0026-canon-repin-and-b1b-intent-arm.md` for the measurement that
started this disposition.
