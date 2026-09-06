# `contains`-Edge Centrality Isolation (2026-09-06)

## Status: MEASURED — centrality channel inert, knob REJECTED for default-on, canon re-pinned

Closes the open item carried by `SESSION_LOG.md` (2026-09-06 entry) and by
`CANON_20260905B_ADR0063_REBASELINE.md` §Follow-up: the 09-05b re-pin re-baselined the whole
ADR-0063 substrate change but never separated its two channels —

1. **Centrality channel** — all 1,095 class→method `contains` edges (emitted from
   `parent_chunk_id` by `search/graph_integration.py::_containment_edge`) enter PageRank via
   `GraphQueryEngine._simple_digraph_view`, which applied no relation-type filter.
2. **Pool-composition channel** — +74 new retrievable chunks (+51 `method`, +23
   `decorated_definition`) competing in the BM25/dense pools, independent of graph topology.

**Verdict in one line:** removing every `contains` edge from PageRank at query time moves MRR by
−0.0004 on both golden sets and no recall metric by more than ±0.005, with no paired CI excluding
zero. The centrality channel is measurably inert; the whole 09-05→09-05b delta belongs to pool
composition. `graph_enhanced.centrality_exclude_containment` ships default-off and
benchmark-locked (`[decision]`).

Design decisions taken with the user before any measurement: probe first with an offline gate,
A/B only if the gate is live; Arm B (old chunk shape, `contains` excluded) is **not built** — the
09-05 pin is its proxy; any knob is a `GraphEnhancedConfig` field, default-off, `benchmark_locked`
(mirrors `centrality_exclude_phantoms`, ADR-0055).

## 2×2 arm picture

| | `contains` in centrality | `contains` excluded from centrality |
|---|---|---|
| old chunk shape (2,871) | 09-05 pin: 0.8234 / 0.6223 / 0.8697 | not built (proxy) |
| new chunk shape (2,956) | base arm: **0.8151 / 0.6324 / 0.8657** | treatment arm: **0.8147 / 0.6320 / —** |

The treatment arm is a **query-time** filter on the identical index: byte-identical pools, so
(treatment − base) isolates the centrality channel exactly, and
(base − 09-05 pin) − (treatment − base) attributes the remainder to pool composition (with the
caveat that the 09-05 pin is a proxy for Arm B and sits on a different substrate).

## Pre-registered gates (written before results were inspected)

### Phase 1 — offline probe gate

- **G-inert**: zero golden-relevant or canon-retrieved chunks change their BM25 adaptive boost
  when `contains` edges are removed from the PageRank graph → channel provably inert on this
  substrate; close with a probe-only disposition, attribute the full 09-05→09-05b delta to pool
  composition, skip the A/B.
- **G-live**: ≥1 golden-relevant chunk changes boost → build the knob and run the paired A/B;
  the affected query list is the pre-registered "expected movers".

### Phase 3 — paired A/B verdict

- Guard-rails `Overall: PASS` on every leg.
- Base arm vs 09-05b pin: |ΔMRR| ≤ 0.02 and Δrecall@20 ≥ −0.02 on both sets (canon re-pin gate).
- Treatment vs base: gate on recall@10 and recall@20 (ADR-0055 convention), MRR secondary.
  **Adopt** (flip the default) only if recall@10 and recall@20 are non-negative on both sets
  **and** the 133q paired CI on recall@20 or MRR excludes 0 in favour of treatment. **Reject**
  otherwise: knob stays default-off, citation tag becomes `[decision]`, key stays in
  `FORBIDDEN_AUTO_TUNE_KEYS`. Inert (0 movers) → same disposition, recorded as measured.
- Determinism: treatment 63q r2 `retrieved` lists bit-identical to r1.

## Phase 1 — probe result: **G-live**

`scripts/benchmark/probe_contains_centrality.py` (read-only, persisted graph, no GPU), output
`tmp/contains_centrality_probe_20260906.json`, run on the 09-05b substrate (2,945 chunks; graph
6,792 nodes / 30,286 edges):

| quantity | value |
|---|---|
| `contains` edges removed (by key == by attr) | 1,095 |
| simple-DiGraph edges with / without | 28,475 / 27,409 |
| PageRank max node (normaliser) with / without | `str` (phantom) both — normaliser unchanged |
| real chunks clearing the 0.02 boost threshold with / without | 14 / 13 |
| real chunks whose boost changes | 7 (all down, 0 up) |
| … of which golden-relevant or canon-retrieved (784 ids) | **6** |

The only threshold crossing is `BaseRelationshipExtractor.__init__` (boost 0.106 → 0.0), which
is not golden-relevant. The six golden-relevant movers all stay above threshold and lose
≤ 0.0032 of `blended_score`:

| chunk | Δboost | queries whose canon top-k retrieved it |
|---|---|---|
| `search/symbol_cache.py:method:SymbolHashCache.add` | −0.0032 | Q38 Q45 Q94 Q98 Q104 Q105 Q123 Q128 H007 H027 H032 H054 |
| `search/metadata.py:method:MetadataStore._ensure_open` | −0.0032 | Q47 Q57 Q89 Q104 H013 H027 H033 H041 H063 H066 |
| `mcp_server/cleanup_queue.py:method:CleanupQueue.add` | −0.0027 | Q40 Q104 Q115 H004 H012 H045 |
| `search/metadata.py:method:MetadataStore.exists` | −0.0023 | Q04 Q12 Q47 Q66 Q72 H032 |
| `search/faiss_index.py:method:FaissVectorIndex.add` | −0.0022 | Q04 Q12 Q19 Q34 Q44 Q45 Q94 Q97 Q120 H064 H066 H068 |
| `utils/path_utils.py:function:normalize_path` | −0.0012 | Q05 Q115 Q117 H020 H028 |

Pre-registered expectation for the A/B from the boost channel alone: sub-0.004 score shifts on
these chunks, i.e. at most tie-break reorderings; the aggregate should be near-flat.

## Mechanism note — a second live channel the 09-05b doc missed

The 09-05b doc (and the plan) stated the BM25 adaptive boost was the **only** live path for
`contains` → ranking. Reading `search/graph_scoring_stage.py:104-175` (Block F) shows a second
one: `_inject_ego_centrality` pushes the same max-normalised PageRank dict into
`EgoGraphRetriever.set_centrality_scores`, and `search/ego_graph_retriever.py:125-154` (QW1)
sorts each hop's `valid_neighbors` by those scores **before** truncating to
`max_neighbors_per_hop * k_hops`. So any PageRank shift can change which neighbours survive ego
expansion, which changes the final listwise-reranker pool — a pool-composition effect that the
probe's boost arithmetic cannot bound. `contains` still cannot be *traversed*
(`DEFAULT_RELATION_TYPES=("calls","called_by")`); it only re-orders neighbours reached over
`calls` edges. This is why the A/B was run even though the probe's boost deltas are tiny — and
the A/B confirms the channel is real: 42/63 and 81/133 `retrieved` lists differ between arms,
far more than the 17 queries the boost probe pre-registered, yet every divergence starts at
rank ≥ 2 and almost none touches a gold.

## Phase 2 — the knob (commit `8e3522d`)

- `GraphEnhancedConfig.centrality_exclude_containment: bool = False`
  (`flat_alias`, `reader="search/centrality_ranker.py"`, `benchmark_locked` → auto-derived into
  `FORBIDDEN_AUTO_TUNE_KEYS`).
- `GraphQueryEngine._scoring_graph_view(exclude_phantoms, exclude_containment)` generalises the
  ADR-0055 phantom filter: `nx.subgraph_view(..., filter_edge=lambda u, v, k: k != "contains")`,
  raw-graph fast path when both flags are off; threaded through `_simple_digraph_view` and all
  four `compute_centrality` methods. Read-only view — traversal is untouched.
- `CentralityRanker.get_centrality_scores` reads the flag and extends its cache key
  (`pagerank[:no_phantoms][:no_contains]`).
- Tests: `tests/unit/graph/test_graph_queries_centrality.py` (4 new, parametrised over all four
  methods), `tests/unit/search/test_centrality_ranker.py` (3 new), forbidden-keys pin updated.
  149 tests green.

## Phase 3 — arms

Substrate: full force reindex after `8e3522d` (the commit touches indexed `graph/` and `search/`
files, so the substrate shifted and the base arm had to be recaptured on it) — 235 files /
**2,956** chunks, 1,095 containment edges, graph 6,822 nodes / 30,449 edges; golden audit CLEAN.

All legs: `run_sscg_benchmark.py --project-path .` (harness self-pins `PYTHONHASHSEED=0`),
strictly sequential, **`CLAUDE_AUTO_REINDEX=0` exported** (see Incident below). Treatment legs add
`--set graph_enhanced.centrality_exclude_containment=true`. Every leg: guard-rails
`Overall: PASS`, zero `Auto-reindexing` lines, `centrality_seeded` = n/n, `ego_rerank_pass_fired`
= n/n on the hybrid legs.

| leg | file |
|---|---|
| base 63q (new canon pin) | `evaluation/canon_63q_r1_20260906.json` |
| treatment 63q r1 | `evaluation/ab_nocontains_63q_r1_20260906.json` |
| base 133q (new canon pin) | `evaluation/canon_133q_r1_20260906.json` |
| treatment 133q r1 | `evaluation/ab_nocontains_133q_r1_20260906.json` |
| base F-via-similar 63q (canon only) | `evaluation/canon_63q_fsim_r1_20260906.json` |
| treatment 63q r2 (determinism) | `evaluation/ab_nocontains_63q_r2_20260906.json` |

## Results

### Canon re-pin gate (base arm vs 09-05b pin) — PASSED

| set | MRR | Recall@5 | Recall@10 | Recall@20 | NDCG@5 | ΔMRR vs 09-05b | ΔR@20 vs 09-05b |
|---|---|---|---|---|---|---|---|
| 63q | **0.8151** | 0.6443 | 0.7635 | 0.8300 | 0.6715 | −0.0013 | −0.0059 |
| 133q | **0.6324** | 0.6002 | 0.7242 | 0.7860 | 0.5808 | +0.0038 | −0.0009 |
| F-via-similar 63q | **0.8657** | 0.6557 | 0.7730 | 0.8158 | 0.6913 | −0.0014 | −0.0059 |

All inside the ±0.02 band; recall@20 deltas ≥ −0.02. These three rows are the new canon
(supersede 09-05b: 0.8164 / 0.6286 / 0.8671). Determinism: treatment r2 = r1 bit-identical
(0/63 `retrieved` diffs); the base 63q leg also reproduced the discarded run-1 base leg
bit-identically (0/63), which doubles as the base-arm determinism check.

### Treatment vs base (paired, identical index)

| set | metric | base | treatment | mean Δ | 95% CI (normal) | n_moved |
|---|---|---|---|---|---|---|
| 63q | MRR | 0.8151 | 0.8147 | −0.0004 | — | 1 (Q70 −0.024) |
| 63q | recall@5 | 0.6443 | 0.6483 | +0.0040 | — | 1 (Q51 +0.25) |
| 63q | recall@10 | 0.7635 | 0.7653 | +0.0019 | — | 5 (Q19 −0.33, Q70 −0.14, Q81 +0.25, Q98 +0.20, Q99 +0.14) |
| 63q | recall@20 | 0.8300 | 0.8332 | +0.0032 | — | 1 (Q04 +0.20) |
| 63q | NDCG@5 | 0.6715 | 0.6713 | −0.0002 | — | 4 |
| 133q | MRR | 0.6324 | 0.6320 | −0.0004 | [−0.0010, +0.0002] | 3 (Q70 −0.024, H012 −0.034, Q128 +0.005) |
| 133q | recall@5 | 0.6002 | 0.6046 | +0.0044 | [−0.0017, +0.0105] | 2 (Q51 +0.25, Q131 +0.33) |
| 133q | recall@10 | 0.7242 | 0.7194 | **−0.0048** | [−0.0159, +0.0063] | 7 (adds Q126 −0.25, H012 −0.50) |
| 133q | recall@20 | 0.7860 | 0.7875 | +0.0015 | [−0.0014, +0.0045] | 1 (Q04 +0.20) |
| 133q | NDCG@5 | 0.5808 | 0.5829 | +0.0021 | [−0.0019, +0.0061] | 7 |
| 133q | hit_rate@5 | 0.8346 | 0.8346 | 0 | — | 0 |

Latency flat (63q 4,453 → 4,466 ms; 133q 4,562 → 4,578 ms). `retrieved` lists differ on 42/63
and 81/133 queries; on 63q the first divergence is at rank 2 (2 queries), 3–5 (11), 6–10 (29) —
rank 1 never changes; 31 chunks leave the top-10 and 31 enter across the set. Of the 17
pre-registered boost movers on the 63q set, 13 changed lists (Q05, Q12, Q34, Q66 did not); the
other 29 movers are the ego-neighbour-ordering channel.

### Verdict — REJECT (pre-registered rule)

- Adoption required recall@10 and recall@20 non-negative on **both** sets: 133q recall@10 is
  −0.0048 → fails.
- Adoption also required a 133q CI excluding 0 in favour: none does (recall@20 bootstrap
  [+0.0000, +0.0045] touches zero; MRR CI straddles zero).
- Nothing trips a guard-rail either. The channel is **measurably inert**: sub-0.005 aggregate
  moves, three MRR movers in 133 queries, mixed sign.

Disposition: knob stays `default=False`, `benchmark_locked` tag → `[decision]`, key remains in
`FORBIDDEN_AUTO_TUNE_KEYS`.

### Attribution of the 09-05 → 09-05b canon delta

| set | base − 09-05 pin (all channels + drift) | centrality channel (treat − base) | pool composition + substrate drift (remainder) |
|---|---|---|---|
| 63q MRR | 0.8151 − 0.8234 = −0.0083 | −0.0004 | **−0.0079** |
| 133q MRR | 0.6324 − 0.6223 = +0.0101 | −0.0004 | **+0.0105** |
| 63q recall@20 | 0.8300 − 0.8349 = −0.0049 | +0.0032 | −0.0081 |
| 133q recall@20 | 0.7860 − 0.7952 = −0.0092 | +0.0015 | −0.0107 |

Caveats: the 09-05 pin is a proxy for the unbuilt Arm B, and "remainder" also carries the
`8e3522d` substrate drift (2,945 → 2,956 chunks) plus the 09-05→09-05b step itself. Within those
caveats the centrality channel is an order of magnitude smaller than the remainder on every
row and of mixed sign, so the 09-05b doc's "noise around a flat baseline" reading stands, now
with the graph-topology explanation excluded.

## Reopening condition

Reopen only if (a) `contains` edges become traversable (`DEFAULT_RELATION_TYPES` gains
`contains`), which would open a third channel this A/B never measured, or (b) a future
centrality method or `centrality_alpha > 0` re-weights PageRank directly into `blended_score`
(today `centrality_alpha=0.0` leaves only the thresholded boost and the ego ordering). The Rust
`impl_item`/`mod_item` and C# `namespace_declaration` container-set item stays deferred per
ADR-0038/ADR-0063 — unrelated to this measurement.

## Incident — auto-reindex fired inside a benchmark leg (first run discarded)

The first chain (13:23–13:53) did not export `CLAUDE_AUTO_REINDEX=0`. The base 63q leg ran
inside the 30-minute snapshot window, but the treatment 63q leg started after the merkle snapshot
aged past `max_index_age_minutes=30.0`, so the orchestrator's `_maybe_reindex` fired on the
first query: "Chunking 0 files", index re-saved, `get_state().reset_searcher()`. The harness had
already instrumented the *first* `HybridSearcher` (rerank-call counter, `_centrality_scores`
probe), so its `confound_summary` read a stale object and reported `centrality_seeded 0/63`,
`ego_rerank_pass_fired 0/63` while `truncation_events` (logger-based) stayed at 408. Standalone
reproductions proved the knob itself worked; the counters were the artefact. The base 133q leg
hit the same reindex at 13:47. Both runs were discarded (archived under
`tmp/ab_run1_autoreindex/`) and the whole chain was re-run with the operator env var set,
matching the convention every probe script documents (`scripts/benchmark/probe_context_cost.py`
docstring). The clean re-run reproduced both discarded 63q legs **bit-for-bit** (0/63 diffs
each, MRR 0.8151 / 0.8147), which proves the rebuild was benign for results and that the
auto-reindex path does not call `invalidate_config_caches()` — the `--set` override survived.

Two smaller incidents from the same afternoon, for the record: (1) the run-1 treatment 63q
process hung at interpreter shutdown after saving its results (130 idle threads, 0 CPU) and had
to be killed; (2) stopping the run-1 chain killed only its current leg — the bash chain advanced
to its next leg and overlapped the restarted chain for 15 minutes with two Jina rerankers on the
GPU (21.9 GB), both stuck at reranker load. Kill the chain's `bash.exe` first, then the python
trees.

**Standing rules added:** every benchmark leg exports `CLAUDE_AUTO_REINDEX=0` (a mid-run
`reset_searcher()` silently detaches every harness instrument that holds a searcher reference);
when aborting a leg chain, kill the parent bash before the children.

## Substrate-drift note (post-capture edit)

After the captures, `search/config.py`'s `benchmark_locked` string and comment for this field
were rewritten from `[pending]` to `[decision]` (this doc's verdict). That edits one indexed
chunk (`GraphEnhancedConfig`) whose text has no search-path semantics; per the strict
substrate-drift rule the canon above is nominally one metadata-string edit stale. Recorded here
rather than re-running six GPU legs for a docstring; the next search-path commit re-pins anyway.
