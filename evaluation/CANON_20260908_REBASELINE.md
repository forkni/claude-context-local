# Retrieval Canon Re-Baseline (2026-09-08)

> **SUPERSEDED (2026-09-20) — measured on a pyan-dark substrate.** The venv had silently
> drifted 34 packages behind `uv.lock` since `f5acd585` (2026-09-02); `pyan_available()` kept
> reporting the tier usable while the real `ImportError` fired inside a resolver subprocess and
> was swallowed as non-fatal (`ee63b8ef`, 2026-09-14). Every canon from 09-03 through this one
> — six consecutive re-baselines — silently missed the pyan cross-module edge tier (libcst-only
> in practice). This doc's numbers are not wrong as *measurements of that substrate*, but that
> substrate is not what any later canon (including 09-20) reflects. See
> `evaluation/CANON_20260920_REBASELINE.md`.

## Status: MEASURED — gate PASSED, no fix required

Re-pin owed by ADR-0069 ("fix phantom-node shadowing of resolved call edges, D1+D2") — a
pre-existing, language-agnostic defect in `graph/graph_queries.py` (traversal dedup order) and
`graph/graph_storage.py` (`get_edge_data` untagged-phantom default) that shadowed resolved
`"exact"`/`"ambiguous"` call-edge confidence tags behind untagged phantom-node edges, silently
defeating `hide_ambiguous_edges_default=True`. D1 reorders `_traverse_inbound`/`_traverse_outbound`
query-node iteration authority-first (real chunk nodes before phantom symbol-name nodes) so the
resolved edge always wins the first-visit dedup; D2 narrows `get_edge_data`'s blanket `1.0` default
so a genuinely-unresolved phantom `calls` edge reports `"ambiguous"` instead — except for a
Python-builtin exclusion (`hasattr(builtins, callee_id)`), since builtin calls are a confirmed
non-project reference, not an unresolved one. Both fixes are query/read-path only — no project's
persisted call graph needed reindexing for D1/D2 themselves — but the traversal reorder changes
which edges multi-hop/ego-graph expansion consumes, so this must be measured, not assumed inert.
See `docs/adr/0069-*.md` for the full decision record.

## Substrate

Full force reindex (`tools/batch_index.py --path . --mode force`, after MCP `cleanup_resources`):
**235 files / 2,978 chunks** (+13 vs the 09-07 pin's 2,965 — two files touched by this fix: the
new `import builtins` + D2 narrowing in `graph/graph_storage.py`, and the new
`test_get_edge_data_untagged_unresolved_call_to_python_builtin_stays_1_0` regression test in
`tests/unit/graph/test_graph_storage.py`), graph 6,855 nodes / 30,610 edges (vs 09-07's
6,833/30,478). `audit_golden_dataset.py` CLEAN on both datasets before capture. All legs with
`CLAUDE_AUTO_REINDEX=0`, `PYTHONHASHSEED=0` exported, strictly sequential
(`run_sscg_benchmark.py --project-path .`).

## Pre-registered gate

|ΔMRR| ≤ 0.02 and Δrecall@20 ≥ −0.02 vs the 09-07 pin (0.8228 / 0.6435 / 0.8657) on all three
views; guard-rails `Overall: PASS` on every leg; 63q determinism bit-identical across rounds.

## Results (hybrid, k=10, deterministic)

| Dataset | Queries | MRR | Recall@5 | Recall@10 | Recall@20 | NDCG@5 | pool_hit_rate | file |
|---|---|---|---|---|---|---|---|---|
| Canonical (`golden_dataset.json`, A–F excl. D) | 63 | **0.8241** | 0.6533 | 0.7634 | 0.8327 | 0.6806 | 1.0000 | `canon_63q_r1_20260908.json` |
| Expanded (`golden_dataset_expanded.json`, non-D) | 133 | **0.6469** | 0.6163 | 0.7235 | 0.7898 | 0.6032 | 0.9098 | `canon_133q_r1_20260908.json` |
| F-via-similar (anchor-chunk view, whole-63q aggregate) | 63 | **0.8671** | 0.6579 | 0.7553 | 0.8071 | 0.6913 | 1.0000 | `canon_63q_fsim_r1_20260908.json` |

## Delta vs the superseded pin (2026-09-07: 0.8228 / 0.6435 / 0.8657)

| set | ΔMRR | Δrecall@20 | gate |
|---|---|---|---|
| 63q | +0.0013 | +0.0063 | PASS |
| 133q | +0.0034 | +0.0174 | PASS |
| F-via-similar | +0.0014 | −0.0066 | PASS |

All inside the ±0.02 band; recall@20 deltas ≥ −0.02 (positive on two of three views). Determinism:
63q r1/r2 paired `--compare` showed `mean_d = +0.0000`, `n_moved = 0` on every metric across all 63
shared queries (`canon_63q_r2_20260908.json`) — bit-identical.

## What this pin settles

D1's traversal reorder is a real behavior change (it flips which of two same-call-site edges wins
the dedup, affecting `find_connections`'s `direct_callers`/`direct_callees`/`indirect_callers` and
therefore also multi-hop graph expansion and ego-graph neighbor selection, both of which consume
`GraphQueryEngine.get_relationships`) — yet across all three views the net effect on ranking
quality is flat-to-slightly-positive, well inside the standing ±0.02 drift band. D2's confidence
retagging cannot reach `TraversalPolicy`'s numeric gate at all (`edge_confidence()` reads raw graph
attributes, never `get_edge_data`), so it was expected to be inert for ranking and the measurement
confirms it. No regression, no follow-up required.

Live MCP spot-checks (not part of the pre-registered gate, but corroborating): on the Rust
`openheizenberg` project, `find_connections("UndoStack::push")` now reports exactly 2
`confidence: "exact"` default-visible callers (matching hand-verified ground truth) with 69
correctly hidden as `"ambiguous"` (`caller_confidence: {"exact": 3, "ambiguous": 69}` pre-filter —
the third "exact" is a pre-existing resolved-but-untagged test-file caller, unrelated to D1/D2). On
the Python self-index, `MetadataStore.get` — a common short method name with heavy call-site
collision — now shows only 3 default-visible callers (all `"exact"`) against a pre-filter total of
`{"exact": 3, "ambiguous": 386}`, where before this fix all 389 would have surfaced as `"exact"`.

Supersedes `CANON_20260907_REBASELINE.md` as current canon.
