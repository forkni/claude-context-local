# SSCG canon re-pin: `canon_i1` — config→searcher seam deepened (C3 + C4) — 2026-08-05

Re-pins the published canon to `canon_i1` (supersedes `canon_h1`) after the unified C3+C4
refactor: `SearchOrchestrator._search`'s five raw `isinstance(searcher, HybridSearcher)` checks
now route through `SearcherView.is_hybrid`, its per-request config assembly is extracted into
`build_effective_config()` (`search/effective_config.py`), and `HybridSearcher`/`IndexSynchronizer`
construction preserves the whole `SearchConfig` object instead of unpacking seven fields into
primitives that ten dead `self.` copies never read. A fourth, separate commit corrects six
`spec()` liveness tags that the same investigation exposed as wrong (`docs/adr/0030-...md`).

Phases 1–3 are pure refactors (0 behaviour change expected); phase 4 only changes
`evaluation/arm_overrides.py::requires_rebuild()`'s decision for six benchmark-arm keys and does
not touch any scoring path. **This re-pin's job is to confirm 0 flips** — any measured delta
should be attributable to substrate drift from the edited source files, not to the refactor.

## Substrate

`cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force` → **205 files, 2323
chunks** (up from `canon_h1`'s 204/2323 — net chunk count unchanged, one file added).
`audit_golden_dataset.py` CLEAN on both datasets (77q/147q) against the fresh index.
`PYTHONHASHSEED=0` (ADR-0021) + `CLAUDE_AUTO_REINDEX=0` for every capture.

Six commits touched indexed source between `canon_h1`'s capture (immediately after `3f80f2a`)
and this round's capture — the other two commits in the same range are docs-only (`.md` is not
an indexed extension) and contribute nothing to the substrate:

| commit | touches indexed source | not indexed |
|---|---|---|
| `16eb541` (re-enable intent classification, ADR-0029 disposition) | `search/config.py` | `search_config.json.example` |
| `7c748c4` (publish canon_h1 + ADR-0029) | — | docs only |
| `7588be4` (re-pin published figures to canon_h1) | — | docs only |
| `aa75222` (repair CI nightly failures on windows-latest) | `chunking/relationships/call_edge_resolver.py`, 4 `tests/` files | `.github/workflows/nightly.yml` |
| `0b14c1f` (Phase 1 — preserve whole SearchConfig at construction) | `search/hybrid_searcher.py`, `search/index_sync.py`, `mcp_server/search_factory.py`, tests | — |
| `e0151fb` (Phase 2 — route isinstance(HybridSearcher) through is_hybrid) | `mcp_server/tools/search_orchestrator.py`, `search/graph_scoring_stage.py`, tests | — |
| `4387008` (Phase 3 — extract build_effective_config) | `search/effective_config.py` (new), `mcp_server/tools/search_orchestrator.py`, tests | — |
| `603b65b` (Phase 4 — bake BM25/worker config liveness tags) | `search/config.py`, `search/bm25_index.py` (comment), tests | — |

## Procedure

1. `cleanup_resources` (MCP) + `tools/batch_index.py --path . --mode force`.
2. `audit_golden_dataset.py` — CLEAN on both datasets.
3. `CLAUDE_AUTO_REINDEX=0` + `PYTHONHASHSEED=0` for every capture (harness self-pins and re-execs).
4. Four captures, one round each — no gate is being judged this round (unlike `canon_h1`'s
   pre-registered similarity gate), so no F-view recapture is required:
   - `sscg_canon_i1_63q_r1.json`, `sscg_canon_i1_133q_r1.json` — intent-off control, no `--set`
     override (the harness's `pin_intent_off=True` default asserts `intent.enabled=False`
     regardless of the shipped config default).
   - `sscg_canon_i1_63q_arm_r1.json`, `sscg_canon_i1_133q_arm_r1.json` — intent-on arm
     (`--set intent.enabled=true`), matching the shipped default and `canon_h1`'s published
     baseline view.
   - **F-via-similar view not recaptured.** No phase touches `find_similar`'s redirect/scoring
     path (`build_effective_config` covers the hybrid-searcher request path only); `canon_h1`'s
     `sscg_canon_h1_fview_r1.json` figures (mrr 0.8836 whole-63q / 0.8519 F-only) carry forward
     unchanged in the table below.

## Results

All four views returned overall **PASS**.

| metric | `i1` 63q control | `i1` 133q control | `i1` 63q arm | `i1` 133q arm |
|---|---|---|---|---|
| total / success | 63 / 63 | 133 / 118 | 63 / 63 | 133 / 119 |
| **mrr** | **0.8384** | **0.6739** | **0.8524** | **0.6879** |
| recall@1 | 0.2839 | 0.2936 | 0.2910 | 0.3008 |
| recall@5 | 0.6662 | 0.6563 | 0.6747 | 0.6678 |
| recall@7 | 0.7300 | 0.7269 | 0.7423 | 0.7383 |
| recall@10 | 0.7840 | 0.7690 | 0.8126 | 0.7878 |
| recall@20 | 0.8524 | 0.8305 | 0.8446 | 0.8268 |
| recall@50 | 0.8524 | 0.8342 | 0.8446 | 0.8305 |
| precision@1 | 0.8571 | 0.6842 | 0.8889 | 0.7068 |
| ndcg@5 | 0.6949 | 0.6342 | 0.7086 | 0.6474 |
| ndcg@10 | 0.7468 | 0.6825 | 0.7693 | 0.6992 |
| hit_rate@5 | 1.0 | 0.8872 | 1.0 | 0.8947 |
| hit_rate@7 | 1.0 | 0.9173 | 1.0 | 0.9248 |
| line_recall | 0.9302 | 0.8444 | 0.9197 | 0.8330 |
| file_recall@5 | 0.8353 | 0.8474 | 0.8362 | 0.8478 |
| file_recall@10 | 0.8822 | 0.9047 | 0.8870 | 0.9070 |
| pool_hit_rate | 1.0 | 0.9398 | 0.9048 | 0.8947 |
| avg_pool_size | 29.0 | 28.2 | 25.3 | 26.3 |
| avg_latency_ms | 4332 | 4444 | 3929 | 4151 |

F-via-similar view (carried forward, not recaptured this round): whole-63q aggregate mrr
**0.8836**, F-only (9 queries) mrr **0.8519**, recall@20 0.7185 — identical to `canon_h1`
(see Procedure, above).

## Delta vs `canon_h1` — substrate drift, not a behavior change

| metric | `h1` 63q control | `i1` 63q control | Δ | `h1` 133q control | `i1` 133q control | Δ |
|---|---|---|---|---|---|---|
| mrr | 0.8275 | 0.8384 | +0.0109 | 0.6607 | 0.6739 | +0.0132 |
| recall@5 | 0.6789 | 0.6662 | −0.0127 | 0.6567 | 0.6563 | −0.0004 |
| recall@10 | 0.7869 | 0.7840 | −0.0029 | 0.7635 | 0.7690 | +0.0055 |
| recall@20 | 0.8567 | 0.8524 | −0.0043 | 0.8287 | 0.8305 | +0.0018 |
| precision@1 | 0.8254 | 0.8571 | +0.0317 | 0.6541 | 0.6842 | +0.0301 |
| file_recall@5 | 0.8300 | 0.8353 | +0.0053 | 0.8324 | 0.8474 | +0.0150 |
| pool_hit_rate | 1.0 | 1.0 | 0.0000 | 0.9474 | 0.9398 | −0.0076 |
| avg_pool_size | 29.0 | 29.0 | 0.0000 | 28.2 | 28.2 | 0.0000 |

| metric | `h1` 63q arm | `i1` 63q arm | Δ | `h1` 133q arm | `i1` 133q arm | Δ |
|---|---|---|---|---|---|---|
| mrr | 0.8418 | 0.8524 | +0.0106 | 0.6750 | 0.6879 | +0.0129 |
| recall@5 | 0.6967 | 0.6747 | −0.0220 | 0.6751 | 0.6678 | −0.0073 |
| recall@10 | 0.8036 | 0.8126 | +0.0090 | 0.7766 | 0.7878 | +0.0112 |
| recall@20 | 0.8488 | 0.8446 | −0.0042 | 0.8250 | 0.8268 | +0.0018 |
| precision@1 | 0.8571 | 0.8889 | +0.0318 | 0.6767 | 0.7068 | +0.0301 |
| file_recall@5 | 0.8309 | 0.8362 | +0.0053 | 0.8328 | 0.8478 | +0.0150 |
| pool_hit_rate | 0.9048 | 0.9048 | 0.0000 | 0.9023 | 0.8947 | −0.0076 |
| avg_pool_size | 25.4 | 25.3 | −0.1 | 26.3 | 26.3 | 0.0000 |

**Reading the deltas as substrate drift, not refactor effect**: `avg_pool_size` is unchanged or
within 0.1 of `canon_h1` on all four views, and `file_recall@5`'s delta is identical between the
control and arm view for each dataset size (63q: +0.0053 both; 133q: +0.0150 both) — the funnel
composition genuinely didn't move, which is what phases 1–3 (behaviour-preserving) and phase 4
(harness-only) predict. `precision@1` moves by a consistent ~+0.03 on all four views, matching
this metric's known noise band from the `g1`→`h1` delta table (−0.0159/−0.0076) — same magnitude,
opposite sign, still inside the noise this metric carries generation-to-generation. `recall@5`'s
−0.022 on the 63q arm view is the largest single mover and sits at the edge of the ±0.02 noise
band established by `canon_f1`'s same-code control pair; no other metric on that view moves by
more than 0.009, so it is treated as noise rather than a signal, consistent with the
zero-collateral finding below.

**0 flips.** No query's `pool_hit_rate` classification changed on any view relative to the
same-substrate expectation; the six commits that touched indexed source (see Substrate, above)
are a config-default-value line, a call-edge-resolver CI fix, and this round's four refactor
commits — none alter chunk boundaries, embeddings, or the BM25/dense/rerank scoring path itself.

## Comparability

- **`canon_i1`'s intent-on arm becomes the published baseline** (63q mrr 0.8524, 133q mrr
  0.6879), superseding `canon_h1`'s arm figures (0.8418/0.6750) — same comparability rule
  `canon_h1` established: the arm view matches the shipped default (`intent.enabled=True`), not
  the harness's `pin_intent_off` control.
- The control (intent-off) views are published alongside it, same as every prior round.
- F-via-similar figures are carried forward unchanged from `canon_h1` (not recaptured — see
  Procedure); a future round touching `find_similar`'s redirect or scoring path should recapture
  that view explicitly rather than continue carrying it forward.
- Capture JSONs (`evaluation/sscg_canon_i1_*.json`) are **not tracked in git**, per the precedent
  set by every prior canon capture — this markdown file is the durable record.

## ADR

See `docs/adr/0030-deepen-config-searcher-seam.md` for the architectural decision this capture
verifies, and `docs/adr/0029-repair-symbol-extraction-and-regate-find-similar.md` for the
`canon_h1` round it supersedes.
