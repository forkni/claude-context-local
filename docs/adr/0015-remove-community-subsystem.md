# Remove the community-detection subsystem; cancel the Leiden migration

Status: proposed (pending human grading of Category G golds)
Date: 2026-07-30

We planned to migrate community detection from Louvain to Leiden. Before
committing, we ran an ablation benchmark to answer the prior question — do we
need communities at all? The benchmark says no: delete the subsystem
(detector, summarizer, community stage, community-refresh stage, remerge,
drift promotion, community-map storage) and cancel the migration. Full
protocol and tables: `evaluation/COMMUNITY_ABLATION_2026-07-30.md`.

## Context

The community subsystem exists to serve global/thematic queries: Louvain
communities over the call graph are summarized into synthetic
`__community__/*` chunks intended to surface when a query targets a
subsystem rather than a symbol. It also feeds a query-time cross-community
penalty inside ego-graph expansion. Cost: ~7–9 s (~11–14%) of every full
index build, a persisted community map, two pipeline stages, and drift
bookkeeping on incremental reindexes.

No existing benchmark category measured the global-query case, so we built
one (Category G, 14 GLOBAL/thematic queries with file-level golds) plus
ablation arms: A0 baseline, A1 penalty on/off, A2 summaries off, A3
detection off, A4 BFS vs PPR expansion; ×2 replicates; A–F regression
guarded at k=5, G scored on strict `file_recall@10`.

## Decision

Remove the community subsystem. Keep the query-time synthetic-chunk demotion
machinery (it serves the ~194 module chunks, which do rank). The
`enable_community_*` isolation flips from migration Phase 1 stand; the rest
of the Leiden migration is cancelled.

## Reasons

**Community summary chunks are never retrieved for the queries they exist to
serve.** Across all 14 G queries × 4 arms × 2 centrality modes × 2 replicates,
zero community chunks appeared in any top-10; community-expanded file recall
equals strict file recall everywhere (gap 0.0). This fact depends only on the
queries, not on gold grading.

**Removing the subsystem costs nothing measurable.** A2 (summaries off) and
A3 (detection off) match A0 within the ±0.02 noise gate on every A–F metric,
and A2 ≥ A0 on the G decision metric. A3-vs-A0 G deltas are within replicate
noise and direction-inconsistent; per protocol, near-threshold defaults to
the cheaper world.

**The query-time penalty is inert while provably exercised.** Neighbor
truncation fired ~410×/run with the anchor always present in the community
map, yet community_bounded on/off differs by ≤0.005 MRR.

**The structure being maintained was degenerate and non-reproducible.**
361/391 communities are singletons; 20 exceed 50 members (max ~160); only 29
were summarizable. Two consecutive reindexes of an identical corpus produced
partitions differing in 21 large groups (2,135/2,236 assignments changed)
despite seeded Louvain — the instability that motivated Leiden, now moot.

**The G blind spots communities were meant to cover are retrieval-model
gaps.** QG02/QG06/QG10 (config-override flow, intent classification, merkle
snapshots) miss their symbol golds identically in every arm, with or without
communities.

## Considered Options

- **Keep for summaries only + Leiden (planned)** — rejected: summaries
  contribute zero measured G benefit; the branch's precondition (A2 G win,
  vanishing under A3) failed.
- **Replace with PPR expansion for GLOBAL queries** — rejected: PPR ≤ BFS on
  G file coverage under A3; deletion doesn't need a replacement to win.
- **Delete the subsystem** — accepted.

## Consequences

- Deletion targets: `graph/community_detector.py`,
  `graph/community_summarizer.py`, `search/community_stage.py`,
  `search/community_refresh_stage.py`, community remerge/drift promotion in
  the incremental indexer, community-map persistence, and the
  `enable_community_*` / `community_*` config surface (staged removal in a
  follow-up change; this ADR records the verdict, not the diff).
- Full index builds get ~11–14% faster; incremental reindexes drop drift
  bookkeeping.
- Category G remains as a benchmark category (pending human grading and
  promotion of `evaluation/golden_dataset_g_draft.json`) — its blind spots
  are real and now measurable independent of communities.
- The duplicate-summary bug (task_3e5203a9) is mooted by deletion.
- Revisit trigger: if a future retrieval feature needs subsystem-level
  grouping, re-run the ablation harness (flags and metrics are committed)
  rather than re-deriving the verdict.
