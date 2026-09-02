# Evidence-Ordered Graph Band Probe — Gate FAILS, campaign closed (2026-08-15)

**Verdict: reopening direction (a) is discharged. No config knob created.**
`evaluation/POOL_ORDER_AB_20260815.md:122-128` named two reopening directions for the merged-pool
graph-band ordering seam. Direction (b) (channel cap) was built and rejected
(`044140b`/`32b086c`/`e152851`). This probe closes direction (a) (evidence-ordered graph band) at
the pre-registered Phase 1 offline gate — **the merged-pool ordering seam is now permanently
exhausted; both named directions are closed.**

## Context

`_order_merged_pool` (`search/reranking_engine.py`, ADR-0039) orders the Pass-2 merged pool as
three provenance bands: signal-positive → `graph_hop` (in raw anchor/BFS discovery order) →
signal-nonpositive. When `top_k_candidates=30` cuts into the graph band, which candidates survive
is decided by discovery order, not relevance. This probe tested whether ordering the graph band
internally by the existing (currently-unused) A1 call-evidence score
(`MultiHopSearcher._score_graph_candidates`) rescues any grade-3 golden-dataset queries, with the
reorder quarantined to *within* the band only — band boundaries and non-graph candidate positions
stay fixed, so this cannot reproduce A1's own rejection mechanism (cross-scale seed displacement).

## Phase 0 re-gate (fresh substrate)

`05ca8d5` (ADR-0039) landed since the plan's original Phase 0 estimate, and the index has drifted
209 files / 2,446 → 2,454 chunks — the substrate-drift rule requires re-deriving any prior
capture-based estimate before trusting it (confirmed necessary below). Band replay against the
fresh capture (`evaluation/probe_graph_band_default_20260815.json`, 124 queries) reproduced the
observed production window on **124/124** queries — ADR-0039 byte-identity holds on the new
substrate.

## Phase 1 method

Two consolidated GPU captures (`probe_rerank_window.py --all --json-out ...`,
`PYTHONHASHSEED=0`, `CLAUDE_AUTO_REINDEX=0`), both 124 queries:

1. **Default** — `evaluation/probe_graph_band_default_20260815.json`. Default config
   (`graph_hop_call_evidence_enabled=False`), serves as both the Phase-0 fresh re-gate substrate
   and the Phase-1 pairing baseline.
2. **Evidence side-channel** — `evaluation/probe_graph_band_evidence_20260815.json`. Same
   invocation plus `--set graph_enhanced.graph_hop_call_evidence_enabled=true
   --force-graph-hop-unscored`. The A1 scorer writes real per-candidate evidence scores into the
   pool, but the new `--force-graph-hop-unscored` flag makes `patched_rerank_by_query` overwrite
   `kwargs["graph_hop_unscored"] = True` on every call, re-entering the banding branch so those
   scores cannot influence the *live* production window — only the captured pool snapshot's
   `.score` field carries the evidence values through to offline replay.

Offline replay (`--band-order-replay`, `scripts/benchmark/probe_rerank_window.py`) then:
reconstructs each query's merged pool as real `_SimResult` objects; runs the actual production
`RerankingEngine._order_merged_pool(..., graph_hop_unscored=True)` to get the anchor-ordered pool;
locates the contiguous `graph_hop` slice (contiguity is structural, guaranteed by
`_order_merged_pool`'s list-concatenation construction); re-sorts *only that slice* descending by
the captured evidence score (stable ties = original anchor order); splices it back in; runs the
real `_apply_hop1_reserve` on both the anchor-ordered and evidence-ordered pools to get final
windows; diffs window ID sets against the grade-3 gold set per query. This ID-set diff
(`rescues = |evidence − anchor| ∩ golds`, `evictions = |anchor − evidence| ∩ golds`) yields
collision-aware and slot-aware correctness for free — no bespoke classifier was needed beyond the
existing `_cap_gold_net` pattern already used by the (rejected) channel-cap probe.

**Gate P1 (pre-registered before results were computed):**

- **G1 headroom**: net gold window-membership delta ≥ 2 (raised from the cap probe's `> 0` — that
  probe's Phase 1 gate passed at exactly net +1 and its Phase 3 live A/B was then rejected; net +1
  is a documented false positive on this exact seam).
- **G2 retention**: no gold whose window membership is graph-band-attributable at baseline leaves
  the window under evidence ordering.
- **G3 self-validity**: (a) replayed anchor-order windows match the observed default-capture
  production windows; (b) observed default-capture and observed evidence-capture production
  windows are byte-identical (confirms the forced-unscored side channel neutralized evidence
  scores' influence on the live run, as designed).

## Results

`evaluation/probe_graph_band_order_gate_20260815.json`, 124/124 queries usable:

| Check | Result |
|---|---|
| G1 headroom (net ≥ 2) | **FAIL** — rescues=0, evictions=0, net=**0** |
| G2 retention | PASS (vacuous — evictions=0) |
| G3a self-validity (anchor replay == observed default window) | PASS — 124/124 |
| G3b self-validity (observed default window == observed evidence window) | PASS — 124/124 |
| Gate verdict | **ABORT** |

G3a/G3b both passing at 124/124 confirms the replay mechanism itself correctly reproduces
production behavior on the new substrate, and that the evidence side-channel technique worked
exactly as designed — the failure is a clean premise failure (headroom is empirically zero), not a
tooling or self-validity problem.

## Diagnostic: why net=0, and is the mechanism actually inert?

Verified the reordering mechanism is mechanically active before accepting net=0 at face value:

- **65/124 queries** show the evidence-ordered window ID set differs from the anchor-ordered
  window ID set — i.e. band-internal reordering by evidence score does change which non-gold
  graph candidates enter the window, in the majority of queries. The splice/replay logic is not a
  no-op.
- Only **8 grade-3 golds** across the full 124-query set have a `graph_hop`-sourced pool entry at
  all: `Q12`, `Q56`, `Q72`, `Q102`, `Q112`, `Q119`, `H021`, `H065`.
- All **8/8** of those golds are absent from the window under **both** anchor and evidence
  ordering (`(in_anchor_window, in_evidence_window) = (False, False)` for every one). None of them
  sit close enough to the window boundary for internal band reordering to ever place them inside
  it — reordering shuffles who fills the admitted graph slots, but for every gold-bearing query,
  the gold's graph-band position never intersects the admitted-slot range under either ordering.

**Conclusion: genuine zero headroom, not a bug.** The mechanism works; the premise (that some
graph-band gold sits near enough to the window cut for evidence-order to matter) is empirically
false on this substrate.

## Correction to the prior Phase 0 estimate

The plan's original Phase 0 analysis (run against a stale capture, predating `05ca8d5` and the
2,446 → 2,454 chunk index drift) estimated 5 rescuable golds — Q12, Q56, Q72, Q102, Q112 — via the
same collision-/slot-aware method. That estimate is **superseded by substrate drift**, per the
project's standing substrate-drift rule: any search-path commit plus index drift invalidates prior
captures until re-derived on fresh substrate. The fresh capture and replay (this document)
supersede it directly — all 5 of those named golds are graph_hop-sourced and grade-3, matching the
prior identification, but on the current substrate none of them are window-reachable under any
graph-band ordering, anchor or evidence.

## Disposition

- **Campaign closed.** Reopening direction (a) (evidence-ordered graph band) is discharged at the
  Phase 1 offline gate. Phase 2 (config knob build) and Phase 3 (live GPU A/B) do not proceed, per
  the plan's pre-registered failure path.
- **No config knob created.** `search/config.py`, `search/reranking_engine.py`, and
  `search/multi_hop_searcher.py` are unchanged. There is nothing to lock in
  `FORBIDDEN_AUTO_TUNE_KEYS` / `BENCHMARK_LOCK_CITATIONS` — no knob was ever built.
  `scripts/benchmark/probe_rerank_window.py`'s new probe-only code
  (`simulate_evidence_band_order`, `--band-order-replay`, `--force-graph-hop-unscored`) stays
  in-tree as a research tool; it does not touch any production search-path file.
- **Merged-pool ordering seam permanently exhausted.** Both directions named in
  `POOL_ORDER_AB_20260815.md:122-128` are now closed: (b) channel cap — built, live A/B rejected;
  (a) evidence-ordered band — offline gate rejected, zero measured headroom. No further untried
  levers are known for this seam. A future reopening would require a materially different
  diagnosis (e.g. a change to which candidates get admitted into the graph band's slots at all,
  rather than how they're ordered within it), not a variant of either measured approach.
