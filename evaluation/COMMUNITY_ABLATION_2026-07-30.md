# Community ablation benchmark — 2026-07-30

Answers: **do we need the community subsystem at all?** Verdict gates the planned
Leiden migration. Protocol per the reviewed plan (community-ablation benchmark,
Phases 0–3). All runs on this repo's live index config except the noted per-arm
flag flips; `enable_community_merge=false` held constant throughout.

**Verdict: DELETE the community subsystem** (detector, summarizer, community
stage, community-refresh stage, remerge, drift promotion, map storage). Leiden
migration cancelled. The query-time demotion machinery survives — it serves the
~188–194 module chunks (count drifts with the corpus), which *do* rank.
Conditional: Category G golds are LLM-drafted and not yet human-graded (see
Caveats); the verdict holds unless grading materially changes the G gold sets.
**Re-validated same day on the repaired subsystem** (see Post-fix
re-validation below): one pre-fix claim required re-scoping, the verdict did
not change.

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

1. **Expanded == strict in every pre-fix G run** (gap = 0.0 on all 14 queries
   × all arms), and `mrr_community_credit == mrr` at A0. Retrieval scan
   confirms why: **zero community chunks appeared in any pre-fix G top-10** —
   in any arm, either centrality mode. Under the production configuration
   (cent-on) this stayed true after the subsystem repair as well; the sole
   exception anywhere in the campaign is one **post-fix, cent-off** QG08 hit
   (see Post-fix re-validation). The 28 summary chunks never rank for exactly
   the query class they exist to serve. (They do surface for A–F: 11
   appearances across the 4 A0 baseline runs, all cent-off, with no metric
   benefit.)
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

## Post-fix re-validation (2026-07-30, repaired subsystem)

Everything above was measured on the pre-repair architecture. An independent
repair (in-flight, uncommitted at verdict time) moved community detection to
run **post-injection on the fully resolved call graph**
(`CommunityStage.run_post_injection`, wired through `IndexWriteStage`) and
fixed a summarizer chunk-id collision (`{dir}_{symbol}` →
`{dir}_{symbol}_c{community_id}`) that had silently clobbered summaries via
metadata upsert. Both mechanisms change which summaries exist and what they
say, so the decisive arms (A2, A3) were re-measured on the repaired
subsystem per the campaign's fix-before-measuring principle.

Provenance: HEAD `b64b0b0a` plus the uncommitted tree (the repair and a
lock-only deps pass — libcst 1.8.6→1.9.0, pyan3 2.6.1→2.6.2; both shift
resolved edges and are confounded with the repair — acceptable, the question
is repaired-world totals, not attribution). The deps pass was committed
mid-campaign as `43327360` with content identical to what the runs
measured, so the results stand. Index: 2,425–2,428 chunks,
26–27 community chunks, 188–194 module chunks (corpus drifts with the
working tree). `enable_community_merge=false` asserted before every arm;
per-arm force reindex; no MCP searches between reindex and runs
(auto-reindex would mutate the index).

### What changed vs the pre-fix claims

**The universal zero-retrieval claim is falsified as written; the
production-scoped claim survives.** Post-repair, QG08 retrieves
`__community__/search_IncrementalIndexer_c24` at rank 5 in both cent-off A0
replicates (strict 0.3333, expanded 0.6667, `mrr_community_credit` 0.20,
`mrr` 0.0) — the only G retrieval of a community chunk in the whole
campaign. Under production settings (cent-on), community chunks remain
absent from every G top-10 in every arm, and the strict decision metric
never moved. A–F appearances stay cent-off-only (7 across the two
A0-postfix cent-off runs: Q33/Q45/Q53/Q93), unchanged in kind from pre-fix.

### A–F (63 queries, k=5, rep1/rep2)

| Arm (cent-on) | MRR | recall@5 | recall@10 |
| --- | --- | --- | --- |
| A0-postfix | 0.6929 / 0.6847 | 0.6044 / 0.5991 | 0.7312 / 0.7183 |
| A2-postfix | 0.6763 / 0.6811 | 0.5855 / 0.5785 | 0.6697 / 0.6684 |
| A3-postfix | 0.6839 / 0.6793 | 0.5917 / 0.5895 | 0.6824 / 0.6969 |

Cent-on MRR deltas vs A0-postfix: A2 −0.0166/−0.0036, A3 −0.0090/−0.0054 —
all within the ±0.02 gate; cent-off likewise (deltas −0.0023 to +0.0112,
still noise-dominated). One flagged observation: recall@10 sits 2–6 pts
below A0-postfix in all eight A2/A3 runs. This is not attributable to a
community mechanism — A3 has no map at all, and the pre-fix campaign moved
recall@10 in the *opposite* direction (A2/A3 ≥ A0) — it is consistent with
build-to-build resolver variance across the reindex boundary (the A2 build
itself ran 9 s slower than every A0-config build), the campaign's
acknowledged cross-reindex noise source, visible here at the tail. The
gated metrics (MRR, recall@5) hold in every run.

### Category G (14 queries, k=10, strict `file_recall@10`, rep1/rep2)

| Arm | cent-on | cent-off |
| --- | --- | --- |
| A0-postfix | 0.5119 / 0.5357 | 0.5595 / 0.5119 |
| A2-postfix | 0.5595 / 0.5595 | 0.4643 / 0.5119 |
| A3-postfix | 0.5417 / 0.5595 | 0.5119 / 0.5119 |

A2 ≥ A0 (+4.8/+2.4 pts) and A3 ≥ A0 (+3.0/+2.4 pts) on the decision metric
under cent-on; cent-off is mixed and diagnostic-only (A2's own cent-off
replicate spread is 4.8 pts at n=14). A0-postfix cent-on sits 2–7 pts below
pre-fix A0 (0.5833/0.5595) — within n=14 replicate noise (one file flip
≈ 2.4 pts). `file_recall_expanded == file_recall_strict` in every A2/A3
run (their indexes contain no community chunks; `mrr_community_credit`
correctly absent). The only expanded>strict gap anywhere is A0-postfix
cent-off: +2.38 pts in both replicates, entirely QG08's community hit.

### Penalty (A1 conclusion transfers without a new arm)

A0-postfix exercised the penalty fully — 432–434 truncation events/run with
the truncated anchor in the community map 100% of the time — while
A3-postfix structurally disables it (220 truncation events, anchors in map
0%: no map exists) and still matches A0 within every gate. The
inert-while-exercised conclusion transfers to the repaired architecture.

### Structure and determinism (repaired architecture)

Fresh map: 2,178–2,182 mapped, 237 communities = 210 singletons, 18 sized
50+ (max 175), 26–27 summarizable, modularity 0.525 — still degenerate.
Two consecutive force reindexes on an identical corpus: same 2,182 keys,
same 237 communities, but 2,145/2,182 label assignments differ; ignoring
labels, 215 groups are identical (covering only 220/2,182 chunks — the
singleton tail) and **22 large groups per side (18–187 members) have
different membership**. Pre-fix measured 21 large groups / 2,135 of 2,236
at 391 communities — the instability is unchanged by the repair.

### Build cost (repaired pipeline)

A0-config builds: 55.77 / 56.13 / 56.34 s; A3 (detection off) 53.22 s; A2
(summaries off) 65.25 s — an outlier demonstrating that resolver variance
dominates end-to-end deltas. Phase logs put post-injection detection at
~1 s and summarization (compute + embed + index) at ~4 s: **~5 s ≈ 8–9%**
of a full build, down from the pre-fix 7–9 s (~11–14%) measured on the
pre-repair pipeline. The ADR's build-cost consequence is re-derived
accordingly.

### Verdict after re-validation

Unchanged: **delete the community subsystem**. Keep-for-summaries remains
dead (A2 ≥ A0 on G strict); A3 ≈/≥ A0 on every gated metric; the penalty is
inert even when its map is deleted outright; the structure is still
degenerate and still non-reproducible. ADR-0015 amended: Reason #1
re-scoped to production with the QG08 cent-off exception named, Reasons #2
and #4 re-cited from the post-fix arms, build-cost consequence re-derived.
Status remains proposed pending human grading of the G golds.

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
