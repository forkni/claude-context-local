# Retrieval Canon Re-Baseline (2026-09-05)

## Status: MEASURED — gate PASSED, no fix required

Re-pin after a 16-commit search-path burst (`5d50708`…`abeef6f`, 2026-09-03→09-05), most
notably `abeef6f` ("emit class->method `contains` edges from `parent_chunk_id`"). `contains`
previously existed only for opt-in TouchDesigner networks (ADR-0062); on an ordinary Python
project it is now a brand-new, densely-populated edge type (894 edges, one per method chunk).
Per this project's standing rule, any search-path commit — including a graph-topology change —
requires a canon re-run before the pin is trusted. **This document re-pins the whole 16-commit
burst; it is not an isolated measurement of `contains` alone** — see Scope note below.

Supersedes `CANON_20260903_REBASELINE.md` (63q 0.8429 / 133q 0.6332 / F-via-similar 0.8856).

## Pre-registered gate (written before results were inspected)

- **Guard-rails**: all three legs print `Overall: PASS` (mrr≥0.5, recall@5≥0.55, hit_rate@5≥0.8).
- **Drift band**: |ΔMRR| ≤ 0.02 **and** Δrecall@20 ≥ −0.02 on both 63q and 133q vs the 09-03
  base arm.
- **Trip condition**: ΔMRR < −0.02 **or** Δrecall@20 < −0.02 on either set → stop, diagnose,
  no auto-fix.
- **Determinism**: 63q r2 `retrieved` lists must be bit-identical to r1.

**Result: all four checks PASSED.** No trip; no fix branch invoked.

## Scope note — why this is a 16-commit re-pin, not a `contains` A/B

The burst includes two other graph-affecting changes beyond `abeef6f`: `76a4e87` (filtered
relationship BFS — expands through matching edges only) and `5d50708` (phantom-flag clearing on
node promotion). Ranking commit `c42dd80` is verified inert on this corpus:
`effective_chunk_kind` only remaps chunks carrying a `td_class` tag or a `.tdgraph.json` path,
and this repository has neither. `contains` itself cannot reach ego or multi-hop traversal —
`DEFAULT_RELATION_TYPES = ("calls", "called_by")` (`graph/traversal_policy.py:36`) is an
allow-list consulted by `CodeGraphStorage._iter_matching_neighbors`
(`graph/graph_storage.py:794-796`), and neither `TraversalPolicy.ego` nor `.graph_hop` overrides
it. The one live path by which `contains` can move rankings is PageRank centrality:
`_simple_digraph_view` (`graph/graph_queries.py:549-564`) applies no relation-type filter, so
all 894 new edges enter `compute_centrality`; scores are max-normalised
(`search/centrality_ranker.py:150-164`) and feed the BM25 adaptive boost
(`centrality_bm25_boost=True`, threshold 0.02, factor 5.0, cap 0.15) even though
`centrality_alpha=0.0` makes the direct rerank blend inert. New edges redistributing PageRank
mass can move BM25-boost threshold crossings — but this canon does not isolate that effect from
the other 15 commits; see Follow-up.

## Substrate

- Clean Phase 0 force reindex: `.venv/Scripts/python.exe tools/batch_index.py --path . --mode
  force`, `user_excluded_dirs` reused unchanged (`_archive`, `tests`, `audit_reports`,
  `benchmark_results`, `htmlcov`, `tmp`, `code-search-extension`). Result: **234 files / 2,871
  chunks**, F2LLM-v2-0.6B (1024d). `audit_golden_dataset.py` CLEAN on both datasets post-reindex
  (77 queries / 147 queries, `2871 chunks, 2547 normalized IDs`).
- Persisted call graph: **6,721 nodes / 29,664 edges**. Edge-type histogram: `calls 16147,
  uses_type 6751, imports 2172, defines_class_attr 681, catches 678, instantiates 652,
  **contains 894**, defines_field 513, uses_constant 489, defines_constant 174, decorates 152,
  raises 116, inherits 59, defines_enum_member 56, overrides 45, uses_context_manager 44,
  uses_default 17, uses_global 18, implements 6`. The `contains` count (894) matches "one edge
  per method chunk" exactly, confirming the mechanism from `abeef6f` is complete and live on
  this corpus.
- Resolver mix on `calls`-type edges: `lsp 1911 / libcst 745 / pyan 558 / (unresolved-tier) None
  12933` — consistent in shape with the 09-03 pin's `lsp 1875 / ast 3707 / libcst 720 / pyan
  552` (histogram key naming differs between capture scripts; both agree `lsp` is live and
  `pyan`/`libcst` volumes are stable within noise).

## Determinism (ADR-0021)

Single round per view, plus one 63q r2 confirmation round captured as a determinism assertion
(not a second canon round). **Both concurrent-launch attempts of the fsim and r2 legs crashed**
with `torch.AcceleratorError: CUDA error: an illegal memory access was encountered` — two
Jina-reranker-v3 pipelines contending for the RTX 4090 at 96.7% VRAM (22.3/23.0 GB) is not a
supported configuration on this box. Both legs were relaunched sequentially (one process at a
time) and completed cleanly on the retry; no output from the crashed attempts was used.

- `canon_63q_r2_20260905.json`: all 63 `retrieved` lists **bit-identical** to r1, and the
  `aggregate` block is bit-identical (MRR 0.8234, recall@5 0.6564, recall@20 0.8349, etc.).
  Zero diffs. Determinism gate PASSED.

## Results

| Run | queries | MRR | R@5 | R@7 | R@10 | R@20 | R@50 | NDCG@5 | HR@5 | avg latency (ms) |
|---|---|---|---|---|---|---|---|---|---|---|
| `canon_63q_r1_20260905.json` | 63 | **0.8234** | 0.6564 | 0.7165 | 0.7538 | 0.8349 | 0.8372 | 0.6842 | 1.000 | 4,535.9 |
| `canon_133q_r1_20260905.json` | 133 | **0.6223** | 0.6166 | 0.6649 | 0.7296 | 0.7952 | 0.7982 | 0.5913 | 0.8496 | 4,567.3 |
| `canon_fsim_63q_r1_20260905.json` (`--f-via-similar`) | 63 | **0.8697** | 0.6610 | 0.7247 | 0.7558 | 0.8177 | 0.8177 | 0.6961 | 1.000 | 3,959.4 |

All three runs `Overall: PASS` on the three gate thresholds (mrr≥0.5, recall@5≥0.55,
hit_rate@5≥0.8).

## Delta vs the superseded pin (2026-09-03)

| Pin | 63q MRR | 63q R@20 | 133q MRR | 133q R@20 | F-via-similar MRR |
|---|---|---|---|---|---|
| `CANON_20260903_REBASELINE.md` | 0.8429 | 0.8446 | 0.6332 | 0.7929 | 0.8856 |
| `CANON_20260905_REBASELINE.md` (this doc) | 0.8234 | 0.8349 | 0.6223 | 0.7952 | 0.8697 |
| **Δ** | **−0.0195** | **−0.0097** | **−0.0109** | **+0.0023** | **−0.0159** |

All three MRR deltas are negative but stay inside the pre-registered ±0.02 drift band — the
63q leg (−0.0195) is the closest to the boundary of any canon delta recorded in this project's
history, worth watching on the next re-pin but not a trip. Both recall@20 deltas clear the
−0.02 floor; 133q recall@20 actually improved. **Read as substrate drift across the whole
16-commit burst, not a quality regression and not an isolated effect of `contains`** — the
mechanism review above establishes centrality-boost threshold crossings as the one plausible
channel, but this canon does not distinguish that from the BFS-filtering (`76a4e87`) or
phantom-flag (`5d50708`) changes landing in the same window.

## Follow-up recorded, not executed

If the 63q MRR delta widens further on the next re-pin, or a mitigation is ever wanted, the
isolation design is: a default-preserving switch to suppress `contains`-edge emission, one force
reindex per arm, re-run only the regressing leg. The only seam that would actually work is a
relation-type filter inside `_simple_digraph_view` / `compute_centrality`
(`graph/graph_queries.py:549-564`) — **not** the edge weight (`DEFAULT_EDGE_WEIGHTS["contains"]
= 0.9`, `graph/graph_storage.py:162`, which is read only on a traversal path `contains` never
enters and is never consulted by `nx.pagerank`), and not `EgoGraphConfig.relation_types` (already
excludes `contains` via the `("calls", "called_by")` default). Not executed this session by
explicit scope decision — this canon is a re-pin, not a regression investigation.
