# LSP Re-Baseline — Close-Out §4 (2026-08-22)

## Status: MEASURED

Executes the held §4 ("re-baseline the canons") from the 2026-08-22 call-graph
close-out plan (`SESSION_LOG.md:722`). §2/§3 of that plan (re-lock `[lsp]`, fix ten
stale "LSP is opt-in" doc sites) already landed; §1 (three commits) stays held per
standing instruction — this document makes no commit.

Three mutually inconsistent canon pins were live across the repo simultaneously:
63q 0.8722/133q 0.6843 (2026-08-14, predates the +154-chunk index growth), 63q
0.8357/133q 0.6647 (2026-08-16, measured mid-way through the same growth), and 63q
0.8323/133q 0.6526 (2026-08-19 `DEFECT_CLOSURE_20260819.md`, measured but never
published). None reproduce on the current substrate. This document supersedes all
three with one authoritative number, measured with `[lsp]` confirmed live.

## Substrate

- `HEAD` = `11f1535`, working tree dirty (64 files modified/untracked — Workstream
  D/E, C-family chunking parity, docs). This canon pins to the working tree, not a
  commit, exactly like the three pins it supersedes.
- Index: 217 files / 2,611 chunks, F2LLM-v2-0.6B (1024d) + jina-reranker-v3,
  built via a genuine **full** reindex completing 19:48:13 (`logs/mcp_server.log`,
  `[INDEX] incremental=False` → `[FULL_INDEX] Index saved`) — required because
  ADR-0044 keeps resolver-edge injection full-index-only.
- basedpyright 1.39.10 (based on pyright 1.1.412) — the LSP resolver tier's engine.
- Resolver mix, re-derived at publish time from the persisted call graph
  (`claude-context-local_9e7f0a98_f2llm-v2-0.6b_call_graph.json`, `edges[].resolver_source`):
  **26,422 total edges — `lsp` 1,355, `pyan` 1,136, `libcst` 475, unresolved (AST-only) 23,456.**
  Matches the full-reindex log line exactly (`lsp 1358 resolved [145 added/1210
  upgraded]` at injection time; the persisted count differs trivially from in-flight
  resolution count). Non-zero `lsp` confirms the measurement was taken with LSP live —
  the entire point of this re-baseline.
- `scripts/benchmark/audit_golden_dataset.py` — **CLEAN, exit 0, both datasets**
  (77 canonical / 147 expanded queries; every `expected`/`expected_primary`/
  `relevance_grades` key and category-F `anchor_chunk_id` resolves against the live
  index). Re-run as this campaign's first command.
- Per-project `search_overrides.json` carries perf-only knobs (embedding/reranker
  batch sizes, chunking workers) — no quality-affecting fields, not a confound.
- Workstream D/E confirmed inert for this measurement: `centrality_exclude_phantoms`
  defaults `False` (byte-identical path); `prune_orphan_symbol_nodes` fires only on
  the *incremental* `_remove_old_chunks` path, which a full reindex's `clear()`
  bypasses entirely.

## Determinism (ADR-0021)

Two 63q rounds run sequentially (`PYTHONHASHSEED=0` auto-re-exec). **Bit-identical,
0 movers** on every paired metric (`--compare`, n=63 shared queries):

| metric | mean_d | n_moved |
|---|---|---|
| mrr | +0.0000 | 0 |
| recall@5 | +0.0000 | 0 |
| recall@10 | +0.0000 | 0 |
| ndcg@5 | +0.0000 | 0 |
| hit | +0.0000 | 0 |

Determinism reconfirmed on this substrate — per user direction, the 133q and
F-via-similar batches were each captured as a **single round** (no independent
value in a second bit-identical run once the mechanism is reverified).

## Results

| Run | queries | MRR | R@5 | R@10 | R@20 | R@50 | NDCG@5 | HR@5 | pool_hit_rate |
|---|---|---|---|---|---|---|---|---|---|
| `canon_63q_r1_20260822.json` | 63 | **0.8462** | 0.6562 | 0.7618 | 0.8430 | 0.8536 | 0.6854 | 1.000 | 1.000 |
| `canon_63q_r2_20260822.json` | 63 | 0.8462 | 0.6562 | 0.7618 | 0.8430 | 0.8536 | 0.6854 | 1.000 | 1.000 |
| `canon_133q_r1_20260822.json` | 133 | **0.6482** | 0.6233 | 0.7403 | 0.8060 | 0.8185 | 0.6066 | 0.8647 | — |
| `canon_fsim_63q_20260822.json` (`--f-via-similar`) | 63 | **0.9034** | 0.6630 | 0.7775 | 0.8479 | 0.8479 | 0.7021 | 1.000 | — |

Avg latency: 4,414–4,501 ms across `search_code`-mode runs, 3,850 ms for the
anchor-`chunk_id`-routed F-via-similar view (no BM25/dense fusion leg on that path).

## Corpus-identity note: two incidental no-op incremental passes

`last_indexed_time` moved from `2026-08-22T19:48:13` (pre-campaign) to
`2026-08-22T21:19:32` (post-campaign) — the plan's literal verification target
("timestamp unchanged") did not hold. Traced via `logs/mcp_server.log`: two
independent 30-minute-staleness auto-reindex triggers fired mid-campaign (20:48:45,
between Batch A and Batch B; 21:19:32, at Batch C's process startup), each logging
`Changes detected - Added: 1, Removed: 0, Modified: 0` → `[INCREMENTAL] Chunking 0
files`. The "added" file both times is a new `evaluation/*.json` benchmark-output
file — `.json` is not one of the 27 indexed source extensions, so the incremental
pass detects it, chunks nothing, and only bumps the staleness timestamp.

Confirmed a genuine non-event, not corpus drift: `get_index_status` post-campaign
still reads `total_chunks: 2611`, `files_indexed: 217` (unchanged), and the
resolver-mix re-derivation above (`lsp 1355 / pyan 1136 / libcst 475`) is
byte-identical to the pre-campaign snapshot taken right after the full reindex. All
four runs in this document measure the same searchable content and the same call
graph; only an unrelated on-disk metadata timestamp moved.

## Delta vs the three superseded pins

| Pin | 63q MRR | 133q MRR | Δ this canon |
|---|---|---|---|
| 2026-08-14 (`docs/BENCHMARKS.md`, stale) | 0.8722 | 0.6843 | −0.0260 / −0.0361 |
| 2026-08-16 (`CLAUDE.md:43`, stale) | 0.8357 | 0.6647 | +0.0105 / −0.0165 |
| 2026-08-19 (`DEFECT_CLOSURE_20260819.md`, unpublished) | 0.8323 | 0.6526 | +0.0139 / −0.0044 |

Per project convention (see every prior re-pin in `docs/BENCHMARKS.md`'s
comparability-breaks history) this is a **comparability break, not a trend line** —
the three prior pins were measured on different chunk counts (2,457–2,548 vs today's
2,611) and, for two of them, a dark `[lsp]` extra (pruned 2026-08-20, restored
2026-08-22). The 63q number moved in both directions relative to the three priors
(down vs 08-14, up vs 08-16/08-19); the 133q number is down against all three,
consistent with H-category (commit-mined) queries being the harder, LSP/graph-mix-
sensitive half of the expanded set.

## Hard-miss cohort (133q, recall@10 = 0, re-derived from this canon)

12/133 queries score zero recall@10 this generation — supersedes any prior
hard-miss list (per project convention, "the miss set is substrate-dependent —
re-derive before targeting," `REMAINING_LEVERS_AB_20260814.md`):

| id | cat | mrr | query (truncated) |
|---|---|---|---|
| Q101 | A | 0.000 | write the analyzed relationships between code entities out so they sur… |
| Q103 | A | 0.000 | how often repeated questions were answered from memory instead of reco… |
| Q106 | A | 0.000 | return the ids and distances of the closest stored vectors for a query… |
| H004 | H | 0.040 | avoid logging a warning for files that are genuinely empty rather than… |
| H008 | H | 0.000 | make a parameter-sweep script rebuild its searcher instance fresh on e… |
| H021 | H | 0.091 | fix several protocol bugs in the language-server call-graph resolver: … |
| H033 | H | 0.062 | fix the storage-directory resolver logging a spurious error when the a… |
| H034 | H | 0.000 | cap the inference batch size for the ONNX backend based on free GPU me… |
| H050 | H | 0.000 | fix a failing test around the search-code handler not being ready to u… |
| H054 | H | 0.000 | add a second phase of call-graph edge resolution when saving indices, … |
| H063 | H | 0.000 | update call sites in the connection-analysis and similar-code handlers… |
| H066 | H | 0.000 | make the index-status report include a synced flag by lazily initializ… |

11/12 are H-category (commit-mined) — consistent with H034/H066 already being
named unreachable-by-any-graph-lever in
`REMAINING_LEVERS_AB_20260814.md`/`graph_hop_window_cap` closeout; H021/H033/H054
are new to this cohort and self-referentially about the call-graph resolver
subsystem itself (queries describing the LSP-resolver bugfix and edge-resolution
phasing) — plausibly hard because their golds are recent, small, terminology-dense
commits that don't share vocabulary with the query phrasing. No intervention
proposed here; this is a starting point for a future targeting pass, per plan scope.

## Artifacts

`canon_63q_r{1,2}_20260822.json`, `canon_133q_r1_20260822.json`,
`canon_fsim_63q_20260822.json`. This document.

## Out of scope (unchanged from the close-out plan)

- §1 (three held commits) — no git commits made by this document or its campaign.
- Workstream D/E (`centrality_exclude_phantoms` ADR-0055 A/B) — deferred, measured
  here only at its shipped `default=False`.
- Re-running the full reindex — already correctly done pre-campaign; not repeated.
