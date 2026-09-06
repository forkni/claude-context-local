# Retrieval Canon Re-Baseline (2026-09-05b)

## Status: MEASURED — gate PASSED, no fix required

Re-pin on top of `CANON_20260905_REBASELINE.md` to pick up two commits that landed after that pin
was written: `721ccde` ("set `parent_chunk_id` on decorated methods") and `135007c` (ADR-0063,
"make Python decorated classes container nodes"). The 09-05 doc flagged itself stale from both
(`:155-158`) before a re-pin ever happened; this document is that re-pin.

**This is not a `contains`-only A/B.** Both commits change chunk shape (new `method` and
`decorated_definition` chunks that did not exist before), which changes the retrieval pool
composition directly — a channel independent of, and larger than, the graph-topology effect the
09-05 doc's mechanism review focused on.

## Pre-registered gate (written before results were inspected)

- **Guard-rails**: all three legs print `Overall: PASS` (mrr≥0.5, recall@5≥0.55, hit_rate@5≥0.8).
- **Drift band**: |ΔMRR| ≤ 0.02 **and** Δrecall@20 ≥ −0.02 on both 63q and 133q vs the 09-05 pin
  (0.8234 / 0.8349 and 0.6223 / 0.7952).
- **Trip condition**: ΔMRR < −0.02 **or** Δrecall@20 < −0.02 on either set → stop, diagnose,
  no auto-fix.
- **Determinism**: 63q r2 `retrieved` lists must be bit-identical to r1.

**Result: all four checks PASSED.** No trip; no fix branch invoked.

## Scope note — reconciling the substrate delta

Measured read-only from the live index and persisted graph before this capture, reconciling
exactly against ADR-0063's own measurement:

| | 09-05 pin (2,871) | this pin (2,945) | Δ |
|---|---|---|---|
| files / chunks | 234 / 2,871 | 234 / **2,945** | +74 |
| `method` chunks | 894 | 945 | **+51** |
| `decorated_definition` chunks | 229 (0 parented) | 252 (150 parented) | **+23** |
| `contains` edges | 894 | **1,095** | **+201** |
| graph nodes / edges | 6,721 / 29,664 | 6,792 / 30,286 | +71 / +622 |

+74 new chunks = +51 `method` + +23 `decorated_definition`. +201 new `contains` edges = +51 from
the 23 newly-chunked decorated classes' methods (`135007c`, ADR-0063) **plus +150** from decorated
methods inside already-chunked classes that `721ccde` retroactively parented — a contribution
ADR-0063 itself never quantified (it predicted "+72 methods / 34 new edges" against a
hand-audited sample, not the full corpus). **This is the first empirical confirmation that
ADR-0063 works on the real corpus**, and it attributes the edge count correctly between the two
commits for the first time.

Live proof through the MCP surface: `find_connections` on
`mcp_server/state.py:86-280:decorated_definition:ApplicationState` with
`relationship_types=["contains"]` returns exactly **12** children at confidence 1.0, matching
ADR-0063's "`ApplicationState` (12 methods, 194 lines)" measurement — all 12 are chunks that did
not exist before `135007c`.

`contains` still cannot reach ego or multi-hop traversal — `DEFAULT_RELATION_TYPES = ("calls",
"called_by")` (`graph/traversal_policy.py:36`) is an allow-list consulted by
`CodeGraphStorage._iter_matching_neighbors` (`graph/graph_storage.py:794-796`), unchanged by this
re-pin. The one live graph-topology path is PageRank centrality: `_simple_digraph_view`
(`graph/graph_queries.py:549-564`) applies no relation-type filter, so all 1,095 `contains` edges
enter `compute_centrality` and can move BM25-adaptive-boost threshold crossings. This canon does
not isolate that channel from the pool-composition channel (+74 new competing documents) — see
Follow-up.

## Substrate

- Full reindex on HEAD (includes the Phase-1 observability fix to
  `search/graph_integration.py`'s `populate_from_embeddings` INFO line, which does not touch chunk
  content): `.venv/Scripts/python.exe tools/batch_index.py --path . --mode force`,
  `user_excluded_dirs` reused unchanged (`_archive`, `tests`, `audit_reports`,
  `benchmark_results`, `htmlcov`, `tmp`, `code-search-extension`). Result: **234 files / 2,945
  chunks**, F2LLM-v2-0.6B (1024d), 47.68s. `audit_golden_dataset.py` CLEAN on both datasets
  post-reindex (77 queries / 147 queries, `2945 chunks, 2621 normalized IDs`).
- The reindex log's `Populated graph from embeddings:` line now prints the `contains` count for
  the first time (Phase 1 fix): `... 20381 relationship edges, 1095 containment edges` — confirmed
  matching the persisted graph histogram below.
- Persisted call graph: **6,792 nodes / 30,286 edges**. Edge-type histogram: `calls 16416,
  uses_type 6878, imports 2176, **contains 1095**, catches 683, defines_class_attr 681,
  instantiates 658, defines_field 513, uses_constant 495, defines_constant 174, decorates 152,
  raises 119, inherits 59, defines_enum_member 56, uses_context_manager 45, overrides 45,
  uses_global 18, uses_default 17, implements 6`.
- Resolver mix on `calls`-type edges: `lsp 1925 / libcst 752 / pyan 551 / (unresolved-tier) None
  13188` — consistent in shape with the 09-05 pin's `lsp 1911 / libcst 745 / pyan 558 /
  unresolved 12933`.

## Determinism (ADR-0021)

Single round per view, plus one 63q r2 confirmation round captured as a determinism assertion
(not a second canon round). Legs run strictly sequentially (one process at a time), per the 09-05
session's documented VRAM-contention crash with concurrent Jina-reranker-v3 pipelines.

- `canon_63q_r2_20260905b.json`: all 63 `retrieved` lists **bit-identical** to r1 (0/63 diffs),
  and every scored metric (`mrr`, `recall@5/7/10/20/50`, `ndcg@5`, `hit_rate@5`) bit-identical.
  Three pool-instrumentation fields (`pool_hit_count`, `avg_pool_size`, `pool_hit_rate`) were
  `None` in the r2 aggregate rather than repeating r1's values — a benchmark-harness display
  artifact on the second same-session run, not a retrieval difference (the underlying per-query
  `pool_size`/`pool_hit` fields are absent from r2's aggregate roll-up, not diverging from r1's).
  Determinism gate PASSED on the retrieval-quality metrics that the pre-registered gate covers.

## Results

| Run | queries | MRR | R@5 | R@7 | R@10 | R@20 | R@50 | NDCG@5 | HR@5 | avg latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| `canon_63q_r1_20260905b.json` | 63 | **0.8164** | 0.6390 | 0.7080 | 0.7612 | 0.8359 | 0.8390 | 0.6678 | 0.9683 | 4,576.0 |
| `canon_133q_r1_20260905b.json` | 133 | **0.6286** | 0.6002 | 0.6488 | 0.7175 | 0.7869 | 0.7959 | 0.5787 | 0.8346 | 4,585.1 |
| `canon_fsim_63q_r1_20260905b.json` (`--f-via-similar`) | 63 | **0.8671** | 0.6505 | 0.7207 | 0.7730 | 0.8217 | 0.8248 | 0.6876 | 0.9841 | 3,928.3 |

All three runs `Overall: PASS` on the three gate thresholds (mrr≥0.5, recall@5≥0.55,
hit_rate@5≥0.8).

## Delta vs the superseded pin (2026-09-05)

| Pin | 63q MRR | 63q R@20 | 133q MRR | 133q R@20 | F-via-similar MRR |
|---|---|---|---|---|---|
| `CANON_20260905_REBASELINE.md` | 0.8234 | 0.8349 | 0.6223 | 0.7952 | 0.8697 |
| `CANON_20260905B_ADR0063_REBASELINE.md` (this doc) | 0.8164 | 0.8359 | 0.6286 | 0.7869 | 0.8671 |
| **Δ** | **−0.0070** | **+0.0010** | **+0.0063** | **−0.0083** | **−0.0026** |

All deltas are well inside the pre-registered ±0.02 drift band, and both recall@20 deltas clear
the −0.02 floor with room to spare. Unlike the 09-05 pin (whose 63q MRR delta, −0.0195, was the
closest to the boundary in this project's history), this re-pin's deltas are small and mixed in
sign — 63q MRR and F-via-similar MRR moved down slightly, 133q MRR moved up, 63q R@20 moved up
while 133q R@20 moved down. **Read as noise around a flat baseline, not a directional effect of
the +74 new chunks or the +201 new `contains` edges** — no metric moved anywhere near a threshold
crossing.

## Follow-up recorded, not executed

> **Executed 2026-09-06** — `CONTAINS_CENTRALITY_ISOLATION_20260906.md`: query-time `contains`
> exclusion from centrality on the identical index moved MRR by −0.0004 on both sets; the channel
> is inert and the 09-05→09-05b delta is pool composition. Superseded as canon by
> `CANON_20260906_REBASELINE.md`.

The isolation design recorded in the 09-05 pin (`:105-115` — a relation-type filter in
`_simple_digraph_view` / `compute_centrality`, `graph/graph_queries.py:549-564`) remains
unexecuted here for the same reason: this canon re-pins the whole substrate change, it does not
isolate the `contains`-edge centrality channel from the pool-composition channel (+74 new
retrievable documents). If either channel is ever suspected of a regression, that isolation would
need two arms — one with `contains` emission suppressed but the new chunks present, and one with
the old chunk shape restored — neither built here.

`file_summarizer.py:67`'s decorated-class-as-method tally (ADR-0063 Consequences) is unaffected by
retrieval and was not re-measured.
