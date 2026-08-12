# SSCG canon re-pin: `canon_g1` — intent layer off by default, `find_path` removed — 2026-08-04

Re-pins the published canon to `canon_g1` (supersedes `canon_f1`) after Round B of the intent-layer
disposition ADR-0026 adopted: `intent.enabled`'s default flipped `True` → `False`
(`c55c20a`), and the `find_path` redirect — construction branch, execution arm, extractor, and its
tests — was deleted outright (`6a6dc18`). Both commits edit indexed source, so the substrate-drift
rule requires a re-pin regardless of whether the change is expected to move the score.

## Substrate

`cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force` → **204 files, 2322
chunks** (38.08s; down from `canon_f1`'s 2324 — the two commits net-delete ~121 lines across 4
files). `audit_golden_dataset.py` CLEAN on both datasets (77q/147q) against the fresh index.
`PYTHONHASHSEED=0` (ADR-0021) + `CLAUDE_AUTO_REINDEX=0` for every capture.

## Procedure

1. `cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force`.
2. `audit_golden_dataset.py` — CLEAN on both datasets.
3. `CLAUDE_AUTO_REINDEX=0` + `PYTHONHASHSEED=0` for every capture (harness self-pins and re-execs).
4. Three captures, **one round each** — the standing policy `canon_f1` justified (0 flips on its 63q
   determinism-control pair): `sscg_canon_g1_63q_r1.json`, `sscg_canon_g1_133q_r1.json`,
   `sscg_canon_g1_fview_r1.json`. No `--set` overrides — this is the plain production default, run
   with no config the harness has to fight (the harness's own `pin_intent_off=True` default was
   already asserting `intent.enabled=False` per query for every non-arm capture; `canon_g1` is the
   first re-pin where that pin and the source default agree).

## Results

All three views returned overall **PASS**.

| metric | `g1` 63q | `g1` 133q | `g1` F-view |
|---|---|---|---|
| total / success | 63 / 63 | 133 / 117 | 63 / 63 |
| **mrr** | **0.8352** | **0.6667** | **0.8915** |
| mrr_excl_redirect | 0.8352 | 0.6667 | — |
| redirect_rate | 0.0 | 0.0 | — |
| recall@1 | 0.2812 | 0.2873 | 0.2982 |
| recall@5 | 0.6749 | 0.6623 | 0.6818 |
| recall@10 | 0.7922 | 0.7660 | 0.8016 |
| recall@20 | 0.8567 | 0.8325 | 0.8455 |
| recall@50 | 0.8567 | 0.8362 | 0.8455 |
| precision@1 | 0.8413 | 0.6617 | 0.9206 |
| ndcg@5 | 0.6973 | 0.6307 | 0.7122 |
| ndcg@10 | 0.7503 | 0.6754 | 0.7648 |
| hit_rate@5 | 1.0 | 0.8797 | 1.0 |
| hit_rate@7 | 1.0 | 0.9023 | 1.0 |
| line_recall | 0.9439 | 0.8466 | 0.9413 |
| file_recall@5 | 0.8300 | 0.8399 | 0.8277 |
| file_recall@10 | 0.9136 | 0.9121 | 0.9144 |
| pool_hit_rate | 1.0 | 0.9474 | 1.0 |
| avg_pool_size | 29.0 | 28.1 | 28.9 |
| avg_latency_ms | 4326 | 4407 | 3705 |

The F-view's whole-63q aggregate is 0.8915; the **F-only mean over its 9 anchored queries is
0.8519**, bit-identical to `canon_f1`'s figure (filter `per_query` to `category == 'F'`, average
`mrr`; `recall@10`/`recall@20` also bit-identical at 0.7185/0.7185). This view calls
`find_similar_code` directly (the harness's `--f-via-similar` flag), bypassing the intent classifier
and `search_code` entirely, so Round B's changes cannot touch it — the match is the expected
no-op confirmation, not a coincidence.

## Delta vs `canon_f1` — small, and it is substrate drift, not a behavior change

| metric | `f1` 63q | `g1` 63q | Δ | `f1` 133q | `g1` 133q | Δ |
|---|---|---|---|---|---|---|
| mrr | 0.8458 | 0.8352 | −0.0106 | 0.6692 | 0.6667 | −0.0025 |
| recall@5 | 0.6789 | 0.6749 | −0.0040 | 0.6680 | 0.6623 | −0.0057 |
| recall@10 | 0.7882 | 0.7922 | +0.0040 | 0.7716 | 0.7660 | −0.0056 |
| recall@20 | 0.8567 | 0.8567 | 0.0000 | 0.8300 | 0.8325 | +0.0025 |
| precision@1 | 0.8571 | 0.8413 | −0.0158 | 0.6617 | 0.6617 | 0.0000 |
| pool_hit_rate | 1.0 | 1.0 | 0.0000 | 0.9474 | 0.9474 | 0.0000 |
| avg_pool_size | 29.0 | 29.0 | 0.0000 | 28.2 | 28.1 | −0.1 |

**Why this is drift, not the removal taking effect:** the harness's `run_single` already re-asserted
`get_search_config().intent.enabled = False` before every non-arm capture (`pin_intent_off=True` is
the default; only an arm whose own overrides set `intent.enabled` stands it down — see
`run_sscg_benchmark.py:707-711`). `canon_f1` was therefore already measuring the intent-off
condition at the harness level, even though the *shipped default* was still `True` at the time.
`canon_g1` measures the same condition from the *source* default instead of a harness pin — the
pools and rankings the benchmark exercises are unaffected by the flip itself. The residual ~0.01 MRR
and sub-0.02 metric shifts track the 2324→2322 chunk substrate change from deleting the `find_path`
code (docstring lines, the construction/execution branches, `_extract_path_endpoints`, and their
test bodies), consistent with the size and direction of prior same-round re-pin deltas
(`canon_e1 → canon_f1`: 0.8363/0.8362 → 0.8458 63q).

## What changed in production that the harness cannot see

The harness's `pin_intent_off` isolated the benchmark from ever exercising the `find_path` bug this
round removes — `canon_f1`'s normal-path 63q/133q numbers never routed Q72/Q121 through
`_extract_path_endpoints` in the first place. The fix is real but only observable outside the
harness's per-query pin: a direct capture with intent forced on (analogous to `canon_B1b`) confirms
it. Re-running Q72's query (*"strip line range from chunk_id to get stable normalized
identifier"*) with `intent.enabled=true` and `find_path` still present returned an empty result set
(`fallback_on_error=False`); against `canon_g1`'s own capture — intent off, the branch gone — Q72
scores **mrr 1.0** via the normal ranked path, `pool_size=29`. This the plan's end-to-end check for
Round B: no `[INTENT] Redirecting PATH_TRACING` log line can fire (`intent.enabled=False` and the
branch no longer exists), and the query that used to return nothing now returns ranked results.

## Comparability

- **`canon_g1` supersedes `canon_f1`** as the published baseline (63q, 133q, and F-view). `canon_g1`
  is the first re-pin where the harness's long-standing `pin_intent_off` default and the shipped
  `search/config.py` default agree — no more "the harness measures something the default doesn't
  ship" asterisk.
- `canon_B1b` (the intent-on arm ADR-0026 captured) remains a named arm on the prior substrate, not
  re-derived here — Round C will capture its own intent-on arm against this round's repaired
  extractor, on this substrate, rather than diffing against `canon_B1b` directly (drift rule).
- Capture JSONs (`evaluation/sscg_canon_g1_*.json`) are **not tracked in git**, per the precedent set
  by every prior canon capture — this markdown file is the durable record.

## ADR

See `docs/adr/0028-intent-off-by-default-and-remove-find-path-redirect.md` for the architectural
decision this capture verifies, and `docs/adr/0026-canon-repin-and-b1b-intent-arm.md` for the
measurement that motivated it.
