# A1′ — Are untagged `calls` edges real? Execution-witness probe (2026-09-02)

**Verdict: the question is vacuous.** On the live self-index there is not one
`calls` edge between two chunk nodes that lacks a confidence signal. Every one of the
8,713 "untagged" edges A0 counted has a bare symbol (phantom) node as its callee, and
phantom nodes are filtered out of both expansion paths before any membership cap is
applied. The ω question A0 raised for the untagged bucket therefore dissolves, but not
because untagged edges are as good as tagged ones: they are not candidates at all.
The real low-quality mass is `tag:ambiguous`, which is 40% of chunk-to-chunk call edges
and is almost never witnessed.

Artifacts: `evaluation/untagged_edge_witness_20260902.json` (probe output),
`scripts/benchmark/probe_untagged_edge_witness.py` (read-only, deterministic),
`evaluation/tracer/scoring.py:confidence_bucket / extract_bucketed_edges /
score_confidence_buckets`, tests in `tests/unit/evaluation/tracer/test_scoring.py`.

## Question

A0 (`evaluation/EGO_MEMBERSHIP_PROBE_20260901.md` §D1) found that 84.6% / 86.6% of
traversed `calls`/`called_by` edges resolve below the 0.65 floor, and that the largest
single bucket was `untagged_calls`: edges with neither a float `resolver_confidence`
nor a legacy string `confidence` tag, which `graph/graph_storage.py:edge_confidence`
maps to 0.5. Every ω/θ design since has assumed those edges are worse than tagged
ones. WS-B's 1,894 execution-witnessed edges (`evaluation/traced_callgraph.json`) can
test that assumption directly: bucket every stored `calls` edge by the path
`edge_confidence` would take, then ask how often each bucket is witnessed.

Pre-registered rule (plan §5.2): `untagged` is "as reliable as ast" iff
`prec_lb_cov(untagged) ≥ 0.8 × prec_lb_cov(tag:exact)` and no secondary sub-bucket
with `edges_cov ≥ 100` has `prec_lb_cov` below half the untagged value; otherwise the
worst sub-bucket is the tagging target.

## Method

- Buckets mirror `edge_confidence`'s resolution order and A0's
  `_classify_confidence_source`: `resolver:<source>` (float present),
  `tag:<exact|ambiguous|recovered>` (string tag only), `untagged` (neither).
  Phantom-callee edges are counted per bucket but excluded from every denominator.
- Metrics per bucket are the Part 4 definitions verbatim: `edges`, `edges_cov` (caller ∈
  EXEC), `hits_traced`, `prec_lb`, `prec_lb_cov`, `hits_D`, `recall_marginal`,
  `unwitnessable`, plus `edge_share` = edges / all non-phantom `calls` edges.
- Caveat 1: A0 counted traversal *events*; this probe counts distinct static edges.
  The plan's out-degree-weighted share column was dropped: A0's own D1 histogram is
  the actual traversal exposure and is quoted below instead of a proxy.
- Caveat 2: witnessing is positive-only. An unwitnessed edge is unlabeled, not false.
  `prec_lb_cov` is a lower bound; comparing bounds across buckets is valid because the
  coverage restriction is applied identically to every bucket.

## Substrate

| | value |
|---|---|
| Index | 229 files / 2,760 chunks (refreshed 2026-09-02 by the MCP server's auto-reindex, 2 modified files, immediately before the probe ran) |
| Traced positives | `traced_callgraph.json` built on the 2026-09-02 morning index: D 1,675 direct, E_traced 1,894, EXEC 1,318 |
| Non-phantom `calls` edges | 6,894 (vs 6,876 in `resolver_tier_scores.json`; drift from the refresh) |
| Phantom-callee `calls` edges | 8,713 |

The refresh moved ~60 edges from the `ast` tier into the resolver tiers (lsp 1,355 →
1,416, libcst 475 → 494, pyan 1,136 → 1,159; `tag:*` total 3,825 vs the prior `ast`
tier's 3,891). Tier-level numbers below are therefore not bit-comparable with
`resolver_tier_scores.json`, but every qualitative ordering is unchanged.

## Results

| Bucket | edges | edge_share | edges_cov | prec_lb | prec_lb_cov | recall_marginal | A0 D1 events (63q) |
|---|---|---|---|---|---|---|---|
| `resolver:lsp` | 1,416 | 0.205 | 1,026 | 0.5784 | **0.7982** | 0.4872 | 35,647 (all three resolver tiers) |
| `resolver:libcst` | 494 | 0.072 | 318 | 0.4838 | **0.7516** | 0.1403 | ″ |
| `resolver:pyan` | 1,159 | 0.168 | 723 | 0.1605 | 0.2573 | 0.1093 | ″ |
| `tag:exact` | 1,074 | 0.156 | 667 | 0.2626 | 0.4228 | 0.1636 | 20,473 |
| `tag:ambiguous` | 2,751 | **0.399** | 1,769 | 0.0109 | **0.0170** | 0.0161 | 130,582 |
| `tag:recovered` | 0 | | | | | | |
| `untagged` (chunk → chunk) | **0** | 0.000 | 0 | n/a | n/a | 0 | 177,788 |
| `untagged` (chunk → phantom) | 8,713 | excluded | | | | | ″ |

Verdict fields: `vacuous = true`, `as_reliable_as_ast = false`, `untagged_edges = 0`,
`untagged_edges_cov = 0`, threshold 0.3382 (0.8 × 0.4228), no sub-buckets, no
tagging target.

## Reading

1. **`untagged` ≡ phantom.** `add_call_edge` (`graph/graph_storage.py:308-362`) writes
   `confidence` on every chunk-to-chunk AST edge and the resolvers write a float on
   every edge they touch. The only writer that emits a `calls` edge with neither is the
   phantom branch in `search/graph_integration.py` (the `phantom_edges` counter, ~:691),
   whose callee is a bare-name node. So A0's `untagged_calls` bucket (177,788 / 381,697
   traversal events, the largest bucket on both datasets) is entirely edges to nodes
   that can never be a search result.
2. **Phantoms do not take membership slots.** Multi-hop drops non-chunk neighbors before
   its `expansion_k` cap (`search/multi_hop_searcher.py:241`), and the ego retriever
   ranks only `is_chunk_id` nodes before its `max_total` cut
   (`search/ego_graph_retriever.py:225`). They do inflate A0's D1 histogram and the BFS
   `visited` set, so the "84.6% below floor" headline overstates the share of
   *candidate* edges below the floor. Restated on chunk-to-chunk edges only: 55.5% of
   edges (3,825 `tag:*` of 6,894) resolve to 0.5 or 0.7, i.e. below 0.65 for
   `tag:ambiguous` only (39.9%).
3. **`tag:ambiguous` is the actual low-quality mass.** 2,751 edges (40% of all
   chunk-to-chunk call edges, 35.8% of A0's traversal events), 1,769 of them from
   executed callers, and only 30 witnessed. Its `prec_lb_cov` of 0.017 is 25× below
   `tag:exact` and 47× below `resolver:lsp`. These are the AST resolver's
   "multiple candidate chunks with the same name" edges: one call site fanned out to
   every same-named definition in the index. They are exactly what `hide_ambiguous`
   already hides on `find_connections` (default on since 2026-08-16), but they still
   feed traversal at confidence 0.5, which clears the default
   `min_traversal_confidence = 0.0`.
4. **`resolver:pyan` is weak** (0.2573, half of `tag:exact` at 0.4228) while carrying
   a higher declared confidence (0.75 vs 0.7). This is the same ordering the tier
   calibration found (`RESOLVER_TIER_CALIBRATION_20260902.md`) and is the input B4
   needs.
5. **Sanity checks passed.** Bucket edges sum to 6,894 = all non-phantom `calls`
   edges; `tag:*` + `untagged` = 3,825 = the `ast` tier on the same graph; 8,713
   phantom edges all sit in `untagged`, none in any resolver or tag bucket.

## What this changes for the plan

- **A1 (ω table for untagged edges) is closed with no work.** There is nothing to tag.
  Any "untagged edge" seen in a traversal histogram is a phantom edge; the right fix,
  if any, is to stop iterating phantom neighbors inside `_traverse_neighbors` (a
  latency lever, not a quality lever, since both consumers already drop them).
- **The candidate for a θ lever is `tag:ambiguous`, not `untagged`.** A traversal floor
  of 0.6 was byte-identical in Track A (2026-08-14) because at `max_depth=1` ordering
  cannot gate membership and hop-1 fan-out is capped by `expansion_k`; this probe adds
  the reason it *should* have mattered: the 0.5 bucket is 98% unwitnessed. A cheaper
  test than another A/B is an offline replay that removes `tag:ambiguous` edges from
  the ego/multi-hop neighbor sets and counts distinct-gold rescues/evictions on the
  63q/133q sets, with the same ≥2-net-rescue bar the graph-band and window-cap probes
  used. If it rescues nothing, the ambiguous mass is inert at the current caps and the
  lever stays closed.
- **B4 (pyan)** now has two independent measurements putting pyan below `tag:exact`
  on witnessed precision; the decision still needs the hand-labeled sample to
  convert lower bounds into estimates.

## Blind spots carried from WS-B

Positive-only labels; `tests/` not indexed; pre-existing threads untraceable on
3.11; dataclass-generated `__init__` external. A `prec_lb_cov` of 0.017 does not mean
98% of ambiguous edges are wrong, only that the unit-test suite exercised almost none
of them; the ratio to `tag:exact` under identical coverage is the evidence.
