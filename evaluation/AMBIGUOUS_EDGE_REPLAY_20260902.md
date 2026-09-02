# `tag:ambiguous` edge-drop replay screen (2026-09-02)

**Verdict: PASSED at the bar, not above it.** Removing every `tag:ambiguous` call edge
from the ego-graph expansion changes membership for 58/63 and 118/133 queries and moves
six distinct golden chunks on each dataset: four rescued, two evicted, net +2 on both.
The pre-registered rule (net rescues ≥ 2 on each dataset, the graph-band and window-cap
bar) is met exactly, with no margin. The multi-hop proxy arm is clearer (net +8 / +6)
but is a proxy, not the production pool. The lever therefore earns a live A/B on
recall@10/20; it does not earn a default change.

Artifacts: `evaluation/ambiguous_edge_replay_20260902.json`,
`scripts/benchmark/probe_ambiguous_edge_replay.py` (read-only, deterministic, no GPU).

## Question

A1′ (`evaluation/UNTAGGED_EDGE_WITNESS_20260902.md`) found that the AST resolver's
`confidence == "ambiguous"` edges are 40% of chunk-to-chunk `calls` edges and are
witnessed 25× less often than `tag:exact`, yet still feed traversal at 0.5, above the
default `min_traversal_confidence = 0.0`. Track A's floor of 0.6 was byte-identical on
2026-08-14 because at depth 1 ordering cannot gate membership. The ego path traverses at
depth 2 and cuts at 20 per anchor, so there the question is open: does dropping the
ambiguous mass change *which* golds reach the reranker?

## Method

Both arms run on the same on-disk graph (paired), from the anchors captured by
`probe_ego_membership.py` on 2026-09-01:

- base = today's call graph; treated = the same graph with every edge removed whose
  `confidence` tag is `ambiguous` and which carries no float `resolver_confidence`
  (resolver-upgraded edges keep their float and stay).
- ego arm = production sequence for each anchor: `get_neighbors_ranked` depth 2, weighted
  BFS, stdlib/builtin/third-party imports excluded, gate 1 `is_chunk_id`, gate 2 `[:20]`
  in traversal order (centrality was empty on the canon run, D4 of the membership probe).
  Verified against the real `EgoGraphRetriever.retrieve_ego_graph` on today's graph:
  157/157 anchors identical.
- multi-hop proxy = depth 1, skip nodes already in the pool, cap 5 per seed. The real
  seeds and merged pool are not captured, so ego anchors stand in for seeds and the
  anchor set for the pool.
- rescue = gold admitted only in treated; eviction = gold admitted only in base; counted
  as distinct golds per dataset. Replay stops at gate 2: necessary, not sufficient.

Anchors are matched by normalized id; `module_preamble` and `module` chunks map too
(they have fewer colons than `is_chunk_id` requires, but are real anchors).

## Substrate

| | value |
|---|---|
| Graph | 6,450 nodes / 28,270 edges; 7,458 chunk→chunk `calls` edges; 3,149 `tag:ambiguous` removed (42.2%) |
| Captured anchors | 630 (63q) / 1,330 (133q), 10 per query, from the 2,581-chunk 2026-09-01 index |
| Anchors missing on today's graph | 74 / 142 (11.7% / 10.7%): chunks renamed, resplit or deleted since 2026-09-01 |
| Anchors mapping to several raw nodes (split fragments) | 47 / 121; first fragment in sorted order is used |

## Results

| dataset | arm | queries changed | rescued | evicted | net | bar ≥ 2 |
|---|---|---|---|---|---|---|
| 63q | ego | 58/63 | 4 | 2 | **+2** | PASS |
| 63q | multi-hop proxy | 55/63 | 9 | 1 | +8 | PASS |
| 133q | ego | 118/133 | 4 | 2 | **+2** | PASS |
| 133q | multi-hop proxy | 113/133 | 9 | 3 | +6 | PASS |

Ego movers (query, base→treated pool size, gold):

| query | pool | rescued | evicted |
|---|---|---|---|
| Q12 | 64→89 | `index_handlers.py:decorated_definition:handle_index_directory` | |
| Q44 | 72→77 / 85→90 | | `bm25_index.py:method:BM25Index.save` |
| Q51 | 109→101 | | `search_executor.py:decorated_definition:SearchExecutor.search_bm25` |
| Q57 | 94→80 / 96→91 | `metadata.py:decorated_definition:MetadataStore.normalize_chunk_id`; `MetadataStore.get_chunk_metadata` (63q only) | |
| Q75 | 104→107 | `graph_storage.py:method:CodeGraphStorage.get_callers` | |
| Q77 | 94→86 / 83→77 | | `SearchExecutor.search_bm25` |
| Q102 (133q) | 121→122 | `graph_integration.py:method:GraphIntegration.clear` | |

Q12 is the long-standing boundary-riding miss (fusion-cut, see the 2026-07-28 notes);
this is the first lever that admits its gold to the ego pool at all. The two evictions
are the same golds on both datasets, and both are BM25-related methods reached today
only through an ambiguous `save`/`search_bm25` fan-out edge that happens to be right.

## Fidelity of the replay to the canon-era cut

The captured 2026-09-01 gate-2 cut and today's replayed cut agree poorly per anchor
(median Jaccard 0.11 / 0.12) even though the depth-2 reachable sets agree almost fully
(98.7% / 99.5% of captured cut members are still reachable today). Cause: gate 2
truncates in weighted-BFS order whose tie-break is edge insertion order, so every
reindex realises a different top-20 from the same neighbourhood. Consequences:

- The paired comparison is valid on today's graph (both arms share the substrate and
  the replay matches the real retriever), but the specific golds that move are a
  property of this realisation. A live A/B will be on yet another realisation.
- The canon-era cut leaned harder on ambiguous edges than today's: 30.4% of captured
  cut members are unreachable without them, against 8.4% of today's base cut. The
  lever's membership footprint on the 2026-09-01 substrate was therefore larger than
  this replay shows; direction of the gold effect there is unknown.
- Gate 2's insertion-order sensitivity is itself a finding: the ego pool is ~30%
  arbitrary across reindexes, which is consistent with the A0/QW1 result that
  centrality sorting there was inert (`EGO_GATE2_AB_20260901.md`).

## Caveats

1. Membership at gate 2 is necessary, not sufficient. The listwise reranker and the
   final k=10 cut decide the metric; every prior membership lever that passed a replay
   (window cap net +1) lost recall@20 live.
2. Net +2 is the minimum passing value on both datasets. The rescues are four distinct
   golds across four queries; the two evictions show the lever removes true edges too.
3. The multi-hop arm is a proxy. Its seeds and pool are not the production ones.
4. 11% of anchors did not map to today's graph; their contribution is unmeasured.
5. The ambiguous share removed today (42.2% of chunk→chunk calls) is higher than A1′'s
   39.9% because the 2026-09-02 reindex grew the graph.

## Next lever

Live A/B on 63q/133q, seed-0 deterministic harness, gated on recall@10 and recall@20
with the paired bootstrap, MRR reported not gated. Treatment = a `GraphEnhancedConfig`
knob (default off, listed in `FORBIDDEN_AUTO_TUNE_KEYS`) that drops `tag:ambiguous`
edges from traversal, applied in `_traverse_neighbors`; equivalently a traversal floor
of 0.6 that is finally reachable at depth 2 on the ego path only. Two arms are enough:
base and drop. If recall@20's CI includes zero on either dataset, the lever closes with
this record as the reason.
