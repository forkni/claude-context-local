# Remove the community-detection subsystem; cancel the Leiden migration

Status: accepted
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

While the ablation ran, an independent repair of the subsystem was in
flight (uncommitted at verdict time): community detection moved to run
post-injection on the fully resolved call graph, and a summarizer chunk-id
collision that silently dropped some summaries was fixed. The decisive arms
(A2, A3) were re-measured on the repaired subsystem the same day; every
reason below is stated against the repaired architecture (tables: the
ablation doc's "Post-fix re-validation" section).

## Decision

Remove the community subsystem. Keep the query-time synthetic-chunk demotion
machinery (it serves the ~188–194 module chunks, which do rank). The
`enable_community_*` isolation flips from migration Phase 1 stand; the rest
of the Leiden migration is cancelled.

## Reasons

**Community summary chunks are effectively never retrieved for the queries
they exist to serve.** Under the production configuration (centrality
reranking on), zero community chunks appeared in any G top-10 — any arm,
any replicate, before or after the subsystem repair. The sole exception in
the whole campaign is non-production: post-repair, cent-off QG08 surfaced
one summary chunk at rank 5 in both replicates, lifting community-expanded
— but not strict — file recall; the decision metric never moved.
Community-expanded recall equals strict recall in every other run. This
fact depends only on the queries, not on gold grading.

**Removing the subsystem costs nothing measurable.** A2 (summaries off) and
A3 (detection off) match A0 within the ±0.02 noise gate on every gated A–F
metric, pre- and post-repair. On the G decision metric post-repair
(cent-on), both removal arms beat baseline: A2 +4.8/+2.4 pts, A3 +3.0/+2.4
pts strict `file_recall@10`. Cent-off G deltas are noise-dominated and
diagnostic-only; per protocol, near-threshold defaults to the cheaper
world.

**The query-time penalty is inert while provably exercised.** Neighbor
truncation fired ~410×/run pre-repair (432–434×/run post-repair) with the
anchor always present in the community map, yet community_bounded on/off
differs by ≤0.005 MRR — and post-repair A3, where the map is deleted
outright and the penalty structurally cannot fire (anchors in map: 0%),
still matches A0 within every gate.

**The structure being maintained is degenerate and non-reproducible — the
repair changed neither.** On the repaired, fully resolved graph: 210/237
communities are singletons; 18 exceed 50 members (max 175); only 26–27 are
summarizable (pre-repair: 361/391, 20 over 50, 29 summarizable). Two
consecutive reindexes of an identical corpus produce partitions differing
in 22 large groups of 18–187 members (2,145/2,182 assignments changed; only
the 220-chunk singleton tail is stable) despite seeded Louvain — pre-repair
it was 21 large groups, 2,135/2,236. The instability that motivated Leiden
is architecture-independent, and now moot.

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
- Full index builds get ~8–9% faster (post-repair pipeline: detection ~1 s +
  summarization ~4 s of a ~56 s build; the pre-repair pipeline measured
  7–9 s, ~11–14%); incremental reindexes drop drift bookkeeping.
- Category G remains as a benchmark category (pending human grading and
  promotion of `evaluation/golden_dataset_g_draft.json`) — its blind spots
  are real and now measurable independent of communities.
- The duplicate-summary bug (task_3e5203a9) is mooted by deletion.
- Revisit trigger: if a future retrieval feature needs subsystem-level
  grouping, re-run the ablation harness (flags and metrics are committed)
  rather than re-deriving the verdict.
