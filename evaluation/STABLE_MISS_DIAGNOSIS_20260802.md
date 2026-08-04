# Stable-miss funnel diagnosis — Q119 / Q121 / Q122 / Q133 / H063 (2026-08-02)

**Probe**: `scripts/benchmark/probe_stable_misses.py` (new, read-only). For each
graded gold: raw dense/BM25 leg ranks at depth 200, deep RRF fused rank, hop-1
fused-pool membership (legs at production `search_k=100`, cut 30), emulated
hop-1 seed membership (fused pool neural-reranked, cut `[:initial_k]`=20), and
the live production pipeline's final pool (`last_candidate_ids`), listwise
window (`last_window_ids`), and final top-10. Index: fresh 2026-08-02, 2255
chunks, F2LLM-v2-0.6B, post-ADR-0020 commit `38950a4`. Raw JSON:
`benchmark_results/probe_stable_misses_20260802.json`.

**Funnel shape confirmed during the probe** (deployed config, k=10): hop-1 legs
at k=100 → RRF cut 30 → hop-1 listwise rerank → top-20 seeds → graph expand
(+35) + hop-2 (+28) = 83 merged → listwise rerank window 30 (with
`hop1_reserved_slots=6`) → top-10 → ego-graph expansion of those 10 anchors
(+20 capped neighbors) = 30 → final listwise rerank → top-10. `pool_hit` is
measured at the last 30-candidate pool, so pool membership = {multi-hop
top-10} ∪ {20 ego neighbors} — a gold cut by multi-hop can re-enter as a graph
neighbor (Q119's primary did exactly that this run).

## Classification per query

| Query | Primary-gold verdict | Mechanism |
|---|---|---|
| Q119 | **model-demotion** (this run) | Primary (`compute_drive_agnostic_hash`) is invisible to both legs at useful depth (dense 194, BM25 absent) but re-enters the final pool as an **ego-graph neighbor** (pool 22, window, final 15). Grade-2 `find_project_at_different_drive` HIT@2 this run. Baseline pool-loss verdict is **flappy**, not structural. |
| Q121 | **rrf-arithmetic** | Primary (`FaissVectorIndex`) sits at dense 84 / BM25 80 — both inside leg depth — but fused rank 41 > 30 cut. No config lever in scope (window widening closed by Q2 sweep). Grade-2 `CodeIndexManager` is a merged-cut (seed 4 emulated, lost at merge). |
| Q122 | **merged-cut** | All three golds survive hop-1 as seeds (emulated seed ranks 10/12/1) and are flooded out at the 83→30 merged rerank, beyond the 6 reserved slots. The canonical pool-flooding query. |
| Q133 | **HIT this run** (bf16 flapper) | Primary HIT@2, `_LspClient` HIT@1 live — after mrr=0 in *both* baseline rounds. Pure run-to-run instability; the strongest single datapoint for the fp32 determinism arm. |
| H063 | **merged-cut** + **rrf-arithmetic** | `handle_find_connections` seed 9 → flooded out (though it HIT@8 in the first, single-hop-shaped probe run — also flappy). `handle_find_similar_code` is BM25-only (rank 2; dense absent) and fused to rank 116 — destroyed by RRF arithmetic, structurally unreachable. |

## Cross-cutting findings

1. **Merged-cut dominates** (8 of 17 graded golds): hop-1 seeds with emulated
   seed ranks 1–14 routinely fail to reach the final pool. `hop1_reserved_slots=6`
   protects only the top 6, and raising N is closed (N≥8 collateral damage,
   ADR-0013 sweep). The flooding source is the +63 hop-2/graph candidates —
   **Step 3 (`--multi-hop-expansion 0.25`) attacks exactly this** and is now the
   best-motivated arm of the campaign.
2. **bf16 instability is visible at probe granularity**: Q133 (both-round miss)
   hit at rank 1–2 live; Q119's grade-2 hit at rank 2; H063's primary hit at
   rank 8 in one probe shape and missed in the other. Also one emulated-seed
   rank-1 gold (`_update_stored_path_if_changed`) absent from the production
   pool implies the production hop-1 pass ranked it >6 where the emulation put
   it #1 — divergence of that size between two passes over near-identical
   inputs is the bf16 listwise variance in action. **Step 2 (fp32) is
   well-motivated.**
3. **True no-lever misses**: Q121 primary and H063's `handle_find_similar_code`
   are RRF-arithmetic exclusions (legs see them; fusion math buries them).
   Only a reserve-at-final-pool-assembly design (future work, per the
   bm25_reserved_slots rejection note) could reach these. Q119's
   `compute_legacy_hash` (grade 1) is a genuine vocab gap.
4. **Q122 reclassified**: earlier records called it "in-window model-demotion,
   un-fixable by reserve at any N". This probe shows it losing *pool membership*
   at the merged rerank (not in-window demotion) — consistent with the reserve
   sweep's failure, but it means pool-flooding reduction (Step 3) has a real
   shot at it.

## Caveats

- Single live run; the emulated hop-1 seed set uses the same bf16 model and can
  diverge from the production pass at boundaries (measured divergence noted
  above). Treat seed-rank numbers as indicative, not exact.
- Classifications label the *first* funnel stage that loses the gold this run;
  under bf16, boundary golds can lose at a different stage on a different run.

## Implications for the campaign

- Step 2 (fp32): strongly supported — 2 of the 4 "stable" misses are actually
  flappers at probe granularity.
- Step 3 (expansion 0.25): strongly supported — merged-cut is the dominant
  class; primary per-query watch-list: Q122 (all golds), H063
  (`handle_find_connections`), Q121 (`CodeIndexManager`, pool_hit only),
  Q119 (grade-2s), Q133 (`request`, `_reader_loop`).
- Step 4 (PPR): Q119 shows ego-graph re-entry rescuing a leg-invisible primary;
  PPR changes which neighbors re-enter — watch Q119/Q122 specifically.
- No re-proposal of window widening / doc-cap / reserve-N changes: nothing in
  this probe contradicts those closures.
