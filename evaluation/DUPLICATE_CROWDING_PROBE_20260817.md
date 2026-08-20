# Duplicate-tree crowding — rerank-window probe (2026-08-17)

## Verdict

**Decision gate ABORTED — fold-don't-drop is NOT built.** Three of four
pre-registered conditions fail outright, and the fourth (P4, the B-category
false-positive canary) independently vetoes the mechanism regardless of the
others: at both tested `leg_search_multiplier` values, the count of B4/B5
sibling-pair chunks an exact-content-hash fold would collapse (9–15) meets or
exceeds the total number of newly-displayed chunks the fold produces
anywhere in the 30-query set (7–12). The lever would cost as much as it
gains, and the cost lands specifically on Category B — the query class where
this system's graph-aware retrieval most clearly beats chunkhound
(`CROSS_SYSTEM_RESULTS_CHUNKHOUND_20260817.md`).

This also corrects an overstated claim made from eyeballing display tables:
"both systems get crowded out by SDTD's duplicate source trees" implied a
shared, load-bearing weakness. Measured, it is real at the *rerank-window*
level (not just display) but small, mostly unrecoverable, and the one
population large enough to move the needle (exact `module_preamble`
boilerplate — shared import blocks / license headers across sibling files)
is not the kind of duplication the original claim was about.

## Method

Script: `scripts/benchmark/probe_duplicate_crowding.py` (read-only; no
`search_config.json` or production-code changes). Arm A
(`reranker.enabled=True`, `top_k_candidates=30`, `intent.enabled=True`)
reconstructed **in memory** via `evaluation.arm_overrides.apply_overrides`,
applied after `set_active_project_storage_dir` and before
`get_searcher(project_path="D:\dev\SDTD_040_Beta")` — `search_config.json`
itself was left in its ablated Arm-B state throughout (see Consequences).

For each of the 30 pre-registered cross-system queries
(`CROSS_SYSTEM_QUERIES_20260817.md`), instrumented every `_run_rerank` call
(Pass 1 hop-level, Pass 2 multi-hop merge, Pass 3 ego-graph/parent-expansion
tail — disambiguated by log prefix + nested-call ordinal) and the pre-fusion
`RRFReranker.rerank_simple` call. Content identity: SHA-256 of
CRLF-normalized, trailing-whitespace-stripped `metadata["bm25_text"]` (not
`content`, which is path/symbol-augmented for BM25-won candidates, and not
`content_preview`, which truncates at 200 chars) — no comment/docstring
stripping, no similarity threshold (both were independently shown
non-separable in `SIMILAR_DIVERSITY_20260728.md`, and reproduced again here
via the report-only Jaccard tier, never gated). A dedup-aware walk
(structural clone of `RerankingEngine._apply_graph_hop_window_cap`) computes
what each window would look like if duplicates deferred and content-distinct
candidates from the pool backfilled the freed slots. Pass 1 additionally
gets a `pass1_refused` variant: its captured leg lists replayed through the
real `RRFReranker.rerank_simple` at `max_results=60`, since Pass 1's
observed window structurally has `backfill_avail=0` (`fusion_k =
max(k, reranker_budget)` cuts the fused pool to exactly 30 before the
reranker ever sees it). P3 (display conversion) re-runs the real, loaded
cross-encoder (`RerankingEngine.neural_reranker.rerank`) on the dedup-aware
permutation of the last pass's window, then `dedupe_results`, and diffs the
resulting top-7 against the observed top-7.

Run at both `leg_search_multiplier ∈ {1, 5}` per the plan's unrecoverable-
parameter caveat (current config value is 1; dataclass/example default is 5;
which was live during the earlier Arm-A cross-system capture is
undeterminable). The two runs did not diverge materially (P1 slot totals
52 vs 52, identical `overall=ABORT` at both) — no HALT triggered.
`PYTHONHASHSEED=0` per ADR-0021; `leg_search_multiplier=1` rerun twice,
byte-identical per-query table, sensitivity rows, and gate output.

## Results

Denominator 30 queries × 30 Pass-2 window slots = 900.

| Metric | `leg_multiplier=1` | `leg_multiplier=5` | Gate threshold |
|---|---|---|---|
| G0 self-validity | PASS | PASS | probe window == `engine.last_window_ids`; `content_cov` ≥0.95 |
| P1 — Pass-2 `win_dup_slots` | **52/900 (5.8%)**, median 0 | **52/900 (5.8%)**, median 0 | ≥90 (10%) *and* median ≥2 |
| P2 — admitted_new / new_files (Pass 2+3) | 41 / 7 | 42 / 8 | ≥60 admitted *and* ≥30 files |
| P3 — queries changed / new chunks | 11/30 / **7** | 11/30 / **12** | ≥9 queries *and* ≥15 chunks |
| P4 — B-category canary | b_collapsed **9** ≥ p3_new_chunks 7 → **ABORT** | b_collapsed **15** ≥ p3_new_chunks 12 → **ABORT** | ABORT if collapse ≥ gain |
| Sensitivity (`MIN_NORM_CHARS` 0/40/120), total dup_slots all windows | 162 / 157 / 137 | 175 / 173 / 159 | report-only |

**Not a no-op.** The detector clearly fires: Pass 1 and Pass 3 windows (which
structurally cannot backfill, so aren't gated) show occupancy up to **40%**
(E8, `leg_multiplier=5`). The mechanism is real; it just doesn't clear the
recoverable/display/safety bar at Pass 2, where backfill is actually
possible.

**P1 fails on concentration, not just total.** Median Pass-2 `win_dup_slots`
is 0 at both leg multipliers — the 52 slots are concentrated in a handful of
TouchDesigner-extension queries (B4, B5, C3, C6, E4, E8), exactly the
queries the original claim named, while roughly two-thirds of the 30-query
set has zero Pass-2 window duplication. This confirms H3 was the wrong
concern (Pass 2 does have backfill available where duplication exists — see
P2's non-zero admitted_new) but **H1 was correct**: crowding is real but
immaterial in aggregate, concentrated where already known, and too small a
population to fold into a general-purpose mechanism.

**P4 detail — what actually collapses.** Every B-category canary hit is
either (a) a `module_preamble` chunk — shared import blocks / file-header
boilerplate that is byte-identical across sibling files *by construction*,
not meaningful logic duplication — or (b) a genuine B5 mirror-pair method
(`SharedMemEXT.Mode`, `.Connect`, `._trigger_change_callback`,
`onSetupParameters`, `onFrameStart`) that the query is *explicitly asking
for both copies of*. Folding either kind is a direct loss: preamble folding
destroys signal for zero benefit (nobody queries for import blocks), and
mirror-pair folding directly contradicts B5's own semantics ("where do these
two script sets mirror each other" cannot be answered by a mechanism that
hides one of the two mirrors). This reproduces and sharpens the house
finding from `SIMILAR_DIVERSITY_20260728.md`: same-file-vs-cross-file
"is this a duplicate" intent lives in the query text, which a hash-based
fold — like `find_similar_code`'s anchor-file exclusion before it — never
sees.

## Corrected claim

`CROSS_SYSTEM_RESULTS_CHUNKHOUND_20260817.md:712-717` overstated the
finding. Corrected text (applied in this session, see Consequences):

> Duplicate-tree noise measurably crowds the rerank window on a handful of
> TouchDesigner-extension queries (B4/B5/C3/C6/E4/E8 show Pass-2 window
> duplicate occupancy up to 33%, `DUPLICATE_CROWDING_PROBE_20260817.md`),
> but a probe with a pre-registered recoverability/display/safety gate found
> the effect too small and too concentrated to fold safely: only 5.8% of
> Pass-2 slots are duplicates against a 10% bar, and the one population large
> enough to matter (shared `module_preamble` import/header boilerplate) is
> not meaningful duplication. Both systems still show it in the visible
> top-7/top-10 (5 of 210 display slots across the 30-query set, 3 queries
> affected — B5, E4, E8), but it is a minor, mostly-cosmetic shared weakness,
> not a load-bearing one — and any fix wide enough to catch it would also
> collapse B5's own mirror-pair answer and B4's legitimately-parallel example
> scripts.

## Gate evaluation

Formally: **P1 FAIL, P2 FAIL, P3 FAIL, P4 ABORT** at both leg multipliers,
G0 PASS (probe trustworthy), not-a-no-op proven. The gate's own design
anticipated this outcome as plausible (P1's 10% bar was set "the point below
which the cross-encoder still sees ≥27 content-distinct candidates for 7
display slots" — 5.8% sits comfortably inside that region) and P4 was set
absolute specifically because Category B is this system's strongest
advantage over chunkhound. All four conditions independently support the
same conclusion; there is no near-miss to dispute.

## Consequences

- Deliverable #4 (fold-don't-drop design in `search/reranking_engine.py`,
  `reranker.fold_exact_duplicates` knob, ADR-0040) is **not built**.
- `search_config.json`'s ablated Arm-B state (`reranker.enabled=False`,
  `top_k_candidates=5`, `intent.enabled=False`) was **not** touched by this
  probe (by design — the probe reconstructs Arm A in memory only) and
  remains owed as a separate restoration to deployed defaults.
- Reopening condition (written, per house convention): reopen only if a
  future corpus shows Pass-2 window occupancy ≥20% **with** non-zero
  `backfill_avail` **and** a demonstrated recall loss attributable to it on
  a pooled-graded set — and any redesign must explain how it avoids
  collapsing B5-kind mirror pairs (this probe's P4 canary is the concrete
  regression test any future proposal must pass before it can even reach an
  A/B).
- The merged-pool-ordering and graph-band-evidence seams remain separately
  and permanently exhausted per prior probes; this closes the third named
  direction raised by the cross-system comparison (duplicate-tree crowding)
  with the same discipline — probe first, gate before build, disposition on
  failure.
