# Retrieval Canon: `split_oversized_preamble` A/B (2026-09-23)

## Status: MEASURED — all three pre-registered gates PASSED; `split_oversized_preamble` ADOPTED as default

This closes Card B of the `study-session-log-md-log-sequential-lemur` plan: `_collect_module_preamble_chunks`
(`chunking/languages/base.py`) emits every root-level statement run not covered by function/class
chunking as a single verbatim `module_preamble` chunk with no size check — unlike the function-split
path, which applies `max_chunk_lines`/`max_split_chars`. A 1,034-line prose-as-`.py` file therefore
became one chunk, silently truncated by the embedding composer. The fix packs an oversized run into
size-bounded pieces at root sibling boundaries via `_pack_by_size` (the same packer `_split_large_node`
uses), gated behind `ChunkingConfig.split_oversized_preamble` — default off pending this A/B, now
default on. Sibling-boundary packing only; splitting inside a single giant node (one dict literal, no
sibling boundaries) is a known, deliberate limitation, pinned by
`TestPreamblePackingLimitations::test_single_giant_node_stays_one_chunk`.

No golden-set gold sits in any of the 25 affected preamble runs in this repo (the only preamble gold,
`merkle/__init__.py:module_preamble`, is unaffected), so the measurable effect is on pool composition
only.

## Substrate

`tools/batch_index.py --path . --mode force` at clean HEAD `092f14ab` (tree clean, `git_dirty: False`
on every leg, both arms): **238 files**. Control (`split_oversized_preamble=False`): **3,075 chunks**.
Treatment (`split_oversized_preamble=True`): **3,100 chunks** (**+25**). `codefuse-ai/F2LLM-v2-0.6B` /
1024d, LSP enabled. Resolver mix (`resolver_edge_counts`) identical on both arms —
`lsp 2046 / chunker 1137 / pyan 574 / libcst 775` — call-graph edges are chunk-content-derived, not
boundary-count-derived, so the knob cannot move this.

**Substrate-prediction check:** the plan pre-registered an estimate of about **+36** chunks (±10
tolerance), based on a pre-session simulation. The observed delta (+25) fell 11 outside that band, so
per the plan's own stop rule it was diagnosed before reading any metric: an independent, direct
re-derivation (`tmp/diag_cardb_delta.py`, walking the current source tree with the indexer's own
exclude-dirs list and diffing `MultiLanguageChunker.chunk_file()` output per file under both configs)
produced **+24**, matching the live +25 almost exactly. The gap to the original +36 estimate is fully
explained by this same session's own Step 2–4 edits to `base.py`/`config.py` shifting those files'
preamble-run boundaries after the estimate was made, plus ordinary intervening repo drift — not a
defect in the packing mechanism, which reproduces consistently between the simulation and the live
index. Diagnosis treated as resolved; proceeded to the benchmark legs.

All legs ran with `CLAUDE_AUTO_REINDEX=0 PYTHONHASHSEED=0` exported (plus
`CLAUDE_SPLIT_OVERSIZED_PREAMBLE=true` for treatment legs), strictly sequential
(`run_sscg_benchmark.py --project-path .`), one GPU, chunk cache left on. Both arms measured the
identical commit (`git_sha: 092f14ab`, `git_dirty: False` on every leg) — only the knob differed,
confirmed via each leg's `config_metadata.substrate` fingerprint (`files_indexed`/`git_sha`/
`resolver_edge_counts` byte-identical across arms; `total_chunks` differs by design).

## Pre-registered gates

### Gate 1 — Drift (control vs the 2026-09-23 canon: 0.8124 / 0.6431 / 0.8696 MRR)

`|ΔMRR| ≤ 0.02` and `Δrecall@20 ≥ −0.02` on all three views. **PASSED** on all three:

| set | control MRR | ΔMRR vs canon | control recall@20 | Δrecall@20 vs canon | verdict |
|---|---|---|---|---|---|
| 63q | 0.8263 | +0.0139 | 0.8101 | +0.0022 | PASS |
| 133q | 0.6516 | +0.0085 | 0.7791 | −0.0052 | PASS |
| F-via-similar | 0.8745 | +0.0049 | 0.7880 | 0.0000 | PASS |

### Gate 2 — Adoption (treatment `split_oversized_preamble=True` vs control `False`)

No paired-delta 95% CI (normal or bootstrap) excludes 0 in the negative direction on MRR or
recall@10/20, in any of the 3 views; guard-rails `Overall: PASS` on every leg; `pool_hit_rate` not
lower. **PASSED** — every CI below spans 0:

| set | ΔMRR (95% CI, normal) | Δrecall@10 (95% CI) | Δrecall@20 (95% CI) | pool_hit_rate (ctrl→treat) |
|---|---|---|---|---|
| 63q | −0.0086 `[−0.0242, +0.0070]` | −0.0018 `[−0.0169, +0.0134]` | +0.0043 `[−0.0148, +0.0235]` | 1.000 → 1.000 |
| 133q | +0.0011 `[−0.0184, +0.0206]` | −0.0159 `[−0.0443, +0.0126]` | −0.0017 `[−0.0257, +0.0222]` | 0.910 → 0.917 |
| F-via-similar | −0.0077 `[−0.0233, +0.0079]` | +0.0000 `[−0.0148, +0.0148]` | +0.0008 `[−0.0171, +0.0187]` | 1.000 → 1.000 |

Guard-rails printed `Overall: PASS` on all 8 legs (3 views × 2 arms, plus the 63q determinism repeat
in each arm). `pool_hit_rate` was non-decreasing on every view (unchanged on 63q and F-via-similar,
+0.007 on 133q).

**Honest reading of the point estimates:** mixed and small — 63q and F-via-similar MRR point
estimates are slightly negative (−0.0086, −0.0077), 133q MRR is slightly positive (+0.0011); 133q
recall@10 is the largest single movement (−0.0159) but its CI spans 0 by a wide margin. One
individual query, H035 ("free the GPU memory cache before returning..."), flipped from HIT to MISS
between control and treatment on the 133q leg — noted, but a single query flip inside a CI that
already spans 0 does not change the gate outcome. None of this is statistically distinguishable from
0 — expected, since the golden set's 63/133 queries were never designed to target the 25 affected
preamble runs (no gold sits in any of them).

### Gate 3 — Determinism

Within each arm, 63q r1 vs r2 non-latency fields identical apart from `timestamp`. **PASSED** —
control r1/r2 and treatment r1/r2 both bit-identical (MRR 0.8263/0.8263, recall@20 0.8101/0.8101 for
control; MRR 0.8177/0.8177, recall@20 0.8144/0.8144 for treatment).

## Decision

Per the pre-registered plan, adoption rests on the gate criteria above plus the correctness case: the
fix removes a silent, real defect (oversized preamble runs collapsing to one truncated chunk) that the
golden set is not positioned to detect either way — this mirrors the ADR-0077 "neutral ships on
correctness grounds" precedent used for the 09-23 `fill_budget` adoption above. **Adopted.**
`split_oversized_preamble` default flipped to `True` in `search/config.py` and
`search_config.json.example`. The self-index is left on the treatment substrate (already indexed with
the knob on: 238 files / 3,100 chunks) — no further reindex needed for this repo.

## Results (hybrid, k=10, deterministic, intent pinned off)

| Dataset | Queries | Control MRR | Treatment MRR | Control recall@20 | Treatment recall@20 | file (treatment) |
|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | 0.8263 | 0.8177 | 0.8101 | 0.8144 | `evaluation/ab_cardb_treat_63q_r1_20260923.json` |
| Expanded (`golden_dataset_expanded.json`, non-D) | 133 | 0.6516 | 0.6527 | 0.7791 | 0.7774 | `evaluation/ab_cardb_treat_133q_20260923.json` |
| F-via-similar (anchor-chunk view) | 63 | 0.8745 | 0.8668 | 0.7880 | 0.7888 | `evaluation/ab_cardb_treat_fvs_20260923.json` |

These treatment-arm numbers are **not** a new pinned canon-of-record — the 2026-09-23
`fill_budget`-substrate canon in `evaluation/CANON_20260923_REBASELINE.md` remains the current pin.
This doc records the `split_oversized_preamble` gate outcome only; the two knobs are orthogonal
(`body_truncation` affects composed embedding text, `split_oversized_preamble` affects chunk
boundaries) and were A/B'd independently against the same base canon.

## Deferred (handed to `/improve-codebase-architecture`, per the plan)

- Splitting inside a single giant non-function/class node (the real fix for files like
  `kb/ToolsDefinition.py` or the 72k-line log `.py` files, which stay one chunk under sibling-only
  packing).
- twozero-dev reindex (Step 7 of the plan) — deferred pending explicit user go-ahead. If adopted
  there too: 28 affected runs → ~271 chunks predicted, 164 of those from one 1.6 MB
  `ConstraintsProbe__Text__catalog_cache__td.glsl` file, worth flagging as a possible exclusion
  candidate before that reindex.
