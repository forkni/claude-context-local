# Community ablation benchmark — 2026-07-30

Answers: **do we need the community subsystem at all?** Verdict gates the planned
Leiden migration. Protocol per the reviewed plan (community-ablation benchmark,
Phases 0–3). All runs on this repo's live index config except the noted per-arm
flag flips; `enable_community_merge=false` held constant throughout.

**Verdict: DELETE the community subsystem** (detector, summarizer, community
stage, community-refresh stage, remerge, drift promotion, map storage). Leiden
migration cancelled. The query-time demotion machinery survives — it serves the
~194 module chunks, which *do* rank. Conditional: Category G golds are LLM-drafted
and not yet human-graded (see Caveats); the verdict holds unless grading
materially changes the G gold sets.

## Setup

- Index: 2,426–2,428 chunks (corpus drifted ±2 files during the campaign), 28–29
  synthetic community summary chunks, bge-m3 1024d. Dominant-directory Windows
  path bug fixed first (0a, commit `5bd4c99d`) so summaries carry real labels —
  zero `__community__/root_*` labels in every measured index.
- Harness: `scripts/benchmark/run_sscg_benchmark.py` with ablation flags
  (`--ego-graph`, `--community-bounded`, `--expansion-mode`), centrality warmup,
  hand-labeled intent plumbing, and per-query confound logging (commit
  `92725400` + `660a9444`).
- A–F: 63 queries (D excluded), k=5 thresholds. Category G: 14 GLOBAL/thematic
  draft queries (QG01–QG14, commit `8b3b1a5b`), k=10, scored from
  `evaluation/golden_dataset_g_draft.json` (draft golds — **not** promoted into
  `golden_dataset.json`; human-grading gate held).
- G decision metric: **strict** `file_recall@10` over `expected_files` (community
  chunks credit nothing); community-expanded variant reported alongside; the gap
  is the finding. `mrr_community_credit` secondary, N/A when the index has no
  community chunks.
- ×2 replicates per cell. Raw JSONs: `benchmark_results/community_ablation/`
  (gitignored, local).

### Community structure (live map, post-0a)

2,236 chunks in map, 390–391 communities: 361 singletons, 4 sized 2–9, 5 sized
10–49, **20 sized 50+** (max 156–163). Only 29 communities are summarizable
(≥2 members). Structure is degenerate: half the mapped corpus sits in ~20
mega-communities, and G coverage is structurally capped at 29 summaries.

## Results

### A–F (63 queries, k=5, means shown as rep1/rep2)

| Arm (cent-on) | MRR | recall@5 | recall@10 |
| --- | --- | --- | --- |
| A0 baseline | 0.6832 / 0.6865 | 0.5938 / 0.5991 | 0.7121 / 0.7289 |
| A2 summaries off | 0.6876 / 0.6881 | 0.5952 / 0.5991 | 0.7298 / 0.7404 |
| A3 detection off | 0.6931 / 0.6905 | 0.5969 / 0.5969 | 0.7306 / 0.7306 |

| Arm (cent-off) | MRR | recall@5 |
| --- | --- | --- |
| A0 | 0.6248 / 0.6616 | 0.5224 / 0.5409 |
| A2 | 0.6560 / 0.6714 | 0.5303 / 0.5356 |
| A3 | 0.6366 / 0.6465 | 0.5264 / 0.5272 |

Cent-off replicate spread reaches 0.037 MRR (A0) — treat cent-off deltas as
noise-dominated. Cent-on: **A0 ≈ A2 ≈ A3 within the ±0.02 gate on every
metric**. Removing summaries, then removing detection entirely, costs nothing
on A–F — no pollution to remove, no coverage lost.

### A1 — query-time community penalty (cent-on, ego on)

| | MRR | recall@5 | hit@5 |
| --- | --- | --- | --- |
| community_bounded off | 0.6907 / 0.6854 | 0.5929 / 0.5929 | 0.9524 |
| community_bounded on | 0.6871 / 0.6865 | 0.5991 / 0.5991 | 0.9841 |

The penalty machinery was **genuinely exercised**: neighbor truncation fired
~410 times per run and the anchor was in the community map on 100% of those
events (all three gates open). Effect: ≤0.005 MRR, ≤0.007 recall@5 — inert,
not un-exercised. Supports the migration-Phase-1 isolation flip; nothing to
revert. (Ego off itself: MRR 0.6954/0.6962, recall@5 0.6031/0.6084, but
recall@10 drops 0.691 vs 0.729–0.735 — the ego trade is precision@top vs tail
recall, out of scope here.)

### A4 — BFS vs PPR expansion (cent-on, A–F)

bfs MRR 0.6877/0.6878, recall@10 0.7227/0.7157; ppr MRR 0.6942/0.6934,
recall@10 0.7359/0.7319. Zero PPR fallbacks (ran natively). PPR ≈ BFS, slight
unthresholded tail-recall edge.

### Category G (14 draft queries, k=10) — the central question

**Strict file_recall@10** (decision metric):

| Arm | cent-on | cent-off |
| --- | --- | --- |
| A0 (summaries present) | 0.5833 / 0.5595 | 0.5357 / 0.5357 |
| A2 (summaries off) | 0.5833 / 0.5833 | 0.5595 / 0.5595 |
| A3 (detection off, bfs) | 0.5179 / 0.5357 | 0.5833 / 0.5357 |
| A3 + PPR | 0.5119 / 0.4881 | 0.5119 / 0.4881 |

Load-bearing facts:

1. **Expanded == strict in every G run** (gap = 0.0 on all 14 queries × all
   arms), and `mrr_community_credit == mrr` at A0. Retrieval scan confirms why:
   **zero community chunks appeared in any G top-10** — in any arm, either
   centrality mode. The 28 summary chunks never rank for exactly the query class
   they exist to serve. (They do surface for A–F: 11 appearances across the 4 A0
   baseline runs, all cent-off, with no metric benefit.)
2. A2 ≥ A0 on the decision metric — removing summaries lost nothing on G.
3. A3 vs A0 is within replicate noise and direction-inconsistent (cent-on
   −3.5 pts mean, cent-off +2.4 pts on one rep; one file flip ≈ 2.4 pts at
   n=14). Per protocol, near-threshold ⇒ insufficient evidence ⇒ default to the
   cheaper world.
4. PPR under A3 does **not** beat BFS on G file coverage (−3 to −5 pts) — the
   replacement lever isn't needed for the deletion case (A3 ≈ A0 directly), and
   it isn't a G win either. G MRR is uniformly low (0.20–0.38) across arms; the
   blind spots QG02/QG06/QG10 (module-chunk-only hits; intent_classifier and
   merkle layers invisible to their thematic queries) persist in every arm —
   they are retrieval-model gaps, not community gaps.

### Orthogonality (0i)

The call graph contains zero `__community__` nodes or edge references — ego
expansion structurally cannot source community chunks; every community-chunk
appearance is direct dense/BM25 retrieval of summary text.

### Determinism check (A3→A0 restore)

Two consecutive force reindexes on an identical corpus: same 2,236 keys, same
391 communities, but **2,135/2,236 assignments differ**, and partition-level
comparison (labels ignored) shows **21 large groups per side with different
membership** (group sizes ~30–158). Seeded Louvain is label- *and*
partition-unstable on this graph; only singletons/small groups are stable.
Under a keep verdict this was the Leiden-motivating evidence; under deletion it
is additional removal justification — the structure being deleted was not
reproducible run to run.

### Build cost

A0-config force reindex 62.5–64.6 s; A3 (detection off) 55.5 s; A2 (summaries
off) 59.8 s. Detection + summarization ≈ 7–9 s (~11–14%) of every full build.

## Decision-tree application

- A2 shows G benefit ≥ threshold? **No** (A2 ≥ A0; zero G retrieval of
  summaries). Keep-for-summaries branch dead.
- A3 ≈ A0 on G? **Yes** (within noise, direction-inconsistent) ⇒ **delete the
  community subsystem**; Leiden cancelled; ADR-0015 is a removal record.
- A1 community_bounded helps? **No** (inert while provably exercised) ⇒
  isolation flip stands.
- A4 PPR ≥ summaries on G under A3? PPR ≤ BFS on G — irrelevant to the deletion
  case, no GLOBAL routing change recommended.

## Caveats

- **Category G golds are LLM-drafted, validated against the live index and the
  grading harness, but not human-graded** (`golden_dataset.json` untouched;
  gate held). The strongest evidence — zero community-chunk retrieval on G —
  depends only on the *queries*, not the golds, and grading cannot change it.
  File-level deltas could shift by a few points under regraded `expected_files`.
- n=14 G queries; per-query flips ≈ 2.4 pts of aggregate. Cent-off A–F replicate
  spread up to 0.037 MRR.
- Only 29/391 communities were ever summarizable — G coverage by summaries was
  structurally capped before measurement began.
- The ego-gated secondary rerank pass fired on 63/63 A–F queries in every arm —
  a constant confound, logged, not eliminated.

## Deliverables

- This document; ADR `docs/adr/0015-remove-community-subsystem.md`.
- Draft G dataset `evaluation/golden_dataset_g_draft.json` (pending human
  grading before promotion).
- Raw per-run JSONs with per-query rows, confound counters, and community
  stats under `benchmark_results/community_ablation/` (local).
