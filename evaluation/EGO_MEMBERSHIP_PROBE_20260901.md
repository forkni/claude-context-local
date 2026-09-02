# Ego-Membership Headroom Probe — Gate PASSES on both datasets (2026-09-01)

**Verdict: bucket (b) is non-empty and confidence-degenerate on both 63q and 133q. The
pre-registered Phase 2 gate passes decisively. Phase 2 (config-knob build) is warranted by this
probe's own criteria but remains out of scope for this A0 block per explicit user scoping
("A0 probe only") — starting it requires a separate go-ahead.**

## Context

`docs/plans/IMPLEMENTATION_PLAN_CALLGRAPH_RECALL_20260901.md`'s scoping pass concluded that only
*membership* levers (not ordering) can move ego-graph retrieval metrics, on the premise that
`[:max_total]` truncation order is irrelevant because it is discarded by a later PageRank re-sort.
That premise was falsified during scoping: every re-baselined canon reports
`centrality_seeded: 0` — `EgoGraphRetriever._centrality_scores` is empty on every query, the
re-sort never fires, and `[:max_total]` keeps raw BFS/priority-queue discovery order, which itself
degenerates to insertion order because `calls`/`called_by` both resolve to edge-weight 1.0. Gate 2
(`[:max_total]`) fires hundreds of times per canon run (`truncation_events` 422/63q, 902/133q), so
the question this probe answers is narrow and empirical: **does any golden-set gold actually get
cut by one of the five membership gates**, or does the ego set survive intact with all loss
attributable to reranker demotion (a different, already-measured-and-rejected lever)?

Full gate inventory, deployed values, and the D1–D5 diagnostic design are specified in the plan
(`C:\Users\Inter\.claude\plans\thoroughly-study-the-plan-drifting-bear.md`) and are not repeated
here in full; see Results below for what each diagnostic measured.

## Method

`scripts/benchmark/probe_ego_membership.py` (new, read-only, ~built this session on the ADR-0040
probe-harness seam and the `probe_duplicate_crowding.py` class-level-patch pattern). Class-level
patches on `CodeGraphStorage.get_neighbors_ranked`, `CodeGraphStorage._iter_matching_neighbors`,
`EgoGraphRetriever.retrieve_ego_graph`, `EgoGraphRetriever.score_neighbors`, and
`HybridSearcher._apply_ego_graph_expansion` record chunk-id strings (never live, in-place-mutated
result objects) at each of the five gates; a `logging.Handler` attached to the
`search.ego_graph_retriever` logger reuses `run_sscg_benchmark.py`'s `_EgoConfoundRecorder`
technique verbatim to derive an independent gate-2 event count as a cross-check against the canon.
Every golden query routes through `SearchOrchestrator.run()` — the same path the canons use — with
`get_search_config().intent.enabled` re-asserted `False` before each query (see Diagnostic below).

Run against the 219-file/2,642-chunk index re-baselined in `CANON_20260901_REBASELINE.md`, at
`--k 10` (matching the canon's `max_ego = min(20, k*3) = 20`), `PYTHONHASHSEED=0` confirmed in
both log headers, single round per the project's standing convention.

## Two bugs found and fixed before any bucket count could be trusted

**Bug 1 — `is_chunk_id`/`normalize_chunk_id` colon-count mismatch.** `normalize_chunk_id`'s
`dedup_key` strips a chunk id's line-range segment (e.g. a 3-colon raw id → a 2-colon normalized
id), but `is_chunk_id`'s bare-symbol filter requires ≥3 colons. `classify_gold`'s first draft
tested `is_chunk_id` against the already-normalized gold string, so every reachable non-anchor
gold spuriously failed the 3-colon minimum and was misclassified as bucket-b1 (symbol-filtered).
Fixed by keeping traversal-list *values* raw (only dict *keys* — anchor identities — stay
normalized for lookup) and testing `is_chunk_id` against each raw entry before normalizing for set
membership. Verified via smoke-test re-run on Q33: `b1_symbol_filtered` dropped from a
nonzero false-positive count to the correct 0, and genuine `a_survivor_neighbor` /
`b2_gate2_truncated` classifications appeared for the first time.

**Bug 2 — missing intent-pin, which failed the plan's own mandatory canon cross-check.** The first
real 63q run reported `gate2_log_event_count=373` against a required 422, and
`centrality_scores_empty_after_run=False` against a required `True` — both cross-checks the plan
states must hold or "every bucket count is void." Root-caused by diffing per-query truncation
counts against `canon_63q_r1_20260901.json`'s `confounds`: an exact 49-event, 9-query divergence,
all 9 in category F ("find X implementations similar to..."). Reading
`run_sscg_benchmark.py::_run_query` revealed an undocumented (to this probe) `pin_intent_off=True`
default that re-asserts `get_search_config().intent.enabled = False` before every query,
specifically to suppress `SearchOrchestrator`'s intent-based `find_similar` redirect on
category-F queries — a redirect that runs a much lighter ego-graph traversal than the canon
measures. Fixed by adding the identical re-assertion to the probe's per-query loop. This single
fix resolved both symptoms simultaneously: the re-run reproduces `gate2_log_event_count=422` and
`centrality_scores_empty_after_run=True` exactly on 63q, and `902`/`True` exactly on 133q.

Both datasets' final runs pass **all** of the plan's Verification-section checks: `PYTHONHASHSEED=0`
re-exec confirmed in both log headers; `anchor_exception_count=0` on both (no per-anchor exceptions
were silently swallowed inside `retrieve_ego_graph`); gate-2 log-derived count exactly matches the
canon's `truncation_events` on both datasets; `_centrality_scores` is empty on both, matching
`centrality_seeded: 0`.

## Pre-registered gate

> Build Phase 2 only if bucket (b) contains ≥ 2 distinct golds on *each* of 63q and 133q, AND the
> confidence histogram shows ≥ 10% of traversed edges below 0.65.

| Check | 63q | 133q | Threshold | Result |
|---|---|---|---|---|
| Bucket (b) distinct golds | **47** | **83** | ≥ 2 each | **PASS** |
| D1 below-0.65 confidence fraction | **84.6%** | **86.6%** | ≥ 10% each | **PASS** |
| **Gate verdict** | | | | **PASS** |

Both legs clear their thresholds by a wide margin — this is not a boundary call. Unlike this
repo's three prior membership/ordering probes on adjacent seams (graph reserve: 0/0 rescues;
evidence-ordered graph band: net headroom 0; TM2C2: 0 rescues over 392 query×α evaluations), this
one finds real, substantial headroom.

## Results

### Bucket breakdown, both datasets

| Bucket | 63q | 133q |
|---|---|---|
| (a) survivor — anchor | 185 | 303 |
| (a) survivor — neighbor | 47 | 62 |
| (b1) symbol-filtered | 0 | 0 |
| (b2) gate-2 truncated | 49 | 82 |
| (b3) similarity-cut | 1 | 2 |
| (b4) max_ego-cut | 7 | 13 |
| (c) unreachable | 13 | 25 |
| **bucket (b), distinct golds** | **47** | **83** |
| Cross-check: gate-2 log events | 422 (= canon) | 902 (= canon) |
| Anchor exceptions swallowed | 0 | 0 |

Bucket (b) is overwhelmingly gate-2 (`[:max_total]` truncation) on both datasets — 49/57 and
82/97 of the non-anchor-non-c raw bucket-b entries respectively — consistent with the plan's
framing that gate 2's 422/902 firings, not gates 3 or 4, are the dominant membership-loss
mechanism. Gate 4 (`max_ego` cap) fires on the large majority of queries (D3 below) but contributes
comparatively few *distinct-gold* losses, because most of what it cuts at the query's tail is
already non-gold filler.

### D1 — confidence histogram of traversed `calls`/`called_by` edges

| | 63q | 133q |
|---|---|---|
| Total edges observed | 364,490 | 790,353 |
| Below-0.65 count | 308,370 | 684,187 |
| Below-0.65 fraction | **0.846** | **0.866** |
| Mean gap below floor | 0.150 | 0.150 |
| `untagged_calls` (→0.5) | 177,788 | 381,697 |
| `tag:ambiguous` (→0.5) | 130,582 | 302,490 |
| `tag:exact` (→0.7) | 20,473 | 41,789 |
| `resolver_confidence` (lsp/libcst/pyan) | 35,647 | 64,377 |

Confirms the plan's expectation: the mean gap below floor is exactly 0.15 on both datasets because
the two dominant buckets (`untagged_calls`, `tag:ambiguous`) both resolve to exactly 0.5 against a
0.65 floor — this is a flat, structural degeneracy, not a noisy distribution. `resolver_confidence`
(the only bucket that would clear 0.65) is under 10% of traversed edges on both datasets.

### D2 — reachability under widened `relation_types`

| | 63q | 133q |
|---|---|---|
| Bucket-(c) unreachable golds tested | 13 | 25 |
| Newly reachable under all 21 `DEFAULT_EDGE_WEIGHTS` types | **0** | **0** |

Widening ego traversal beyond `calls`/`called_by` would rescue none of the currently-unreachable
golds on either dataset — this lever, floated as a "largest untouched membership restriction" in
the plan, is confirmed empirically inert for the *unreachable* bucket specifically. It does not
bear on bucket (b), which is the gate this probe is scoped to.

### D3 — per-anchor gate pressure

| | 63q | 133q |
|---|---|---|
| Total anchors traversed | 630 | 1,330 |
| Gate-2 fired (fraction of anchors) | 422 (67.0%) | 902 (67.8%) |
| Gate-4 fired (fraction of queries) | 58/63 (92.1%) | 106/133 (79.7%) |

Gate 2 bites roughly two-thirds of all anchors on both datasets — this is not an edge case, it is
the typical traversal outcome. Gate 4 binds on the large majority of queries too, confirming the
ego set is routinely being cut at multiple stages, not just occasionally overflowing one cap.

### D4 — centrality-injection defect (diagnose-and-report only, per plan scope)

`centrality_scores_empty_after_run: True` on both datasets, exactly matching the canons'
`centrality_seeded: 0`. Because the probe routes every query through `SearchOrchestrator.run()` —
the identical path the canons use — this rules out a probe-bypasses-the-orchestrator artifact:
`GraphScoringStage._inject_ego_centrality` genuinely never reaches the retriever instance that
production traversal uses, confirmed on the same canon-comparable substrate this probe validated
via the gate-2/centrality cross-checks. This corroborates the plan's central finding that the QW1
comment at `ego_graph_retriever.py:139-140` ("rank by centrality before truncation so hub
functions survive the cap") describes behavior that does not happen in production. **Not fixed
here** — per plan scope, this is a real membership lever in its own right (it would change which
of N neighbors survive the 422/902 gate-2 truncations) and belongs in its own change with its own
A/B, should Phase 2 be authorized.

### D5 — config echo (both datasets identical, confirming no drift from documented defaults)

`ego_graph`: `enabled=True, expansion_mode="bfs", k_hops=2, max_neighbors_per_hop=10,
min_similarity_threshold=0.15, deduplicate=True`. `graph_enhanced`:
`min_traversal_confidence=0.0, traversal_confidence_weighting_enabled=False,
centrality_annotation=True`. Matches the plan's stated deployed values exactly; `search_overrides.json`
carries no `ego_graph`/`graph_enhanced` section on this substrate.

## Disposition

- **Gate PASSES on both datasets, decisively** — bucket (b) is 47/63q and 83/133q distinct golds
  (far above the ≥2 threshold), and D1's below-0.65 fraction is 84.6%/86.6% (far above the ≥10%
  threshold). Unlike the three prior probes this repo ran on adjacent seams (all measured zero
  headroom), this probe finds real, substantial membership headroom: gate 2 alone truncates
  two-thirds of all traversed anchors, and the confidence signal that could in principle inform
  which neighbors get cut is currently completely flat (everything defaults to 0.5 against a 0.65
  floor) because of the untagged/ambiguous-tag confidence collapse documented in D1.
- **Phase 2 is warranted by the plan's own pre-registered criteria** but is explicitly **out of
  scope for this A0 block**, per the user's earlier scoping decision ("A0 probe only"). Starting
  Phase 2 (A2′ hard-filter, A4 size-bucketed sweep, and/or a QW1 centrality-injection repair per
  D4) requires a separate go-ahead and, per the plan, its own A/B gated on paired 95% CI on
  recall@10/recall@20 (not MRR), 10,000-resample bootstrap, seed 0.
- **No production code changed.** `scripts/benchmark/probe_ego_membership.py` is new and read-only
  (no `save_config()`, no writes to `search/`, `graph/`, `chunking/`, or `mcp_server/`). The two
  bugs found and fixed this session were entirely inside the new probe script itself
  (`classify_gold`'s raw/normalized handling; the missing `intent.enabled` pin), not in any
  production path.
- **B1–B3 (execution-witnessed tracer) and all of Phase 1 remain deferred**, unchanged from the
  plan's own deferral list — this document closes A0 only.
