# Final-pool-assembly reserve — membership probe (2026-08-02)

## Verdict

**Decision gate FAILED — the reserve is NOT built.** It is recorded here as a
spec'd-and-deferred lever (this note is the spec). The gate required some
variant to pool-rescue **≥3 stable misses with zero collateral gold
evictions**. The best variant (V1, raw-BM25 top-3 carry-forward) rescues
**zero stable misses**: its three watch-list rescues (Q119, Q133, H063) are
all documented bf16/bimodal flappers per
`STABLE_MISS_DIAGNOSIS_20260802.md`, and Q133 sits at MRR 1.0 in this very
run. The two genuinely stable 0.0 misses are out of reach entirely:

- **Q121** (rrf-arithmetic): reproduced exactly — grade-3 `FaissVectorIndex`
  at raw dense 84 / raw BM25 80 / fused 41. Not in any raw-leg top-3, not in
  merged-rerank ranks 11-15. **Unreachable by every variant.** The diagnosis
  "no-lever" classification stands.
- **Q122** (merged-cut in the diagnosis): **currently a HIT on this
  substrate** (grade-2 `ModelPoolManager.get_embedder` at final rank 3). The
  diagnosed "seeds 10/12/1" profile no longer exists — see Substrate drift
  below.

With no stable miss rescuable, the probe's ceiling does not cover the
problem the reserve was designed for, and the A/B build (campaign close-out
Step 3) is not justified.

## Method

Script: `scripts/benchmark/probe_final_pool_reserve.py` (read-only; no
config or code changes). For each of the 131 expanded golden queries
(category D excluded, matching the benchmark):

1. Capture raw legs directly: `SearchExecutor.search_bm25` /
   `search_dense` at depth 200 (NOT top-level `search_mode="bm25"`, which
   multi-hop gates before the mode branch), plus a deep RRF fusion via
   `reranker.rerank_simple` for fused ranks.
2. Run the production `HybridSearcher.search(query, k=10)` with
   `rerank_by_query` / `_run_rerank` instrumented (calls tagged by their
   `hop1_reserved_slots` kwarg: >0 = multi-hop merged rerank, 0 = final
   post-ego rerank). `_run_rerank` wrapping is required because
   `rerank_by_query` returns `sorted_results[:k]` — the full reranked
   window order (merged ranks 11+) is otherwise invisible.
3. Record per gold: dense/BM25/fused ranks, merged-pool and merged-output
   ranks, final-pool rank, final-window membership, final rank.
4. Simulate reserve variants at **membership level** (no reranker re-runs):
   inject source candidates absent from the final 30-window, evict an equal
   count from the window's pre-rerank tail once the cap is exceeded —
   `_apply_hop1_reserve` semantics generalized to the final pool.

### Variants

| Variant | Source injected into final window |
|---------|-----------------------------------|
| V1 | raw BM25 top-3 |
| V2 | raw dense top-3 |
| V3 | merged-rerank output ranks 11-15 |
| V1+V3 | union of V1 and V3 |

### Sanity gate (reproduce diagnosis facts before trusting simulation)

- **H063** ✅ — grade-3 `handle_find_similar_code`: raw BM25 rank 3, fused
  118 (diagnosis: BM25 2-3 → fused 116-118; within index drift).
- **Q121** ✅ — dense 84 / BM25 80 / fused 41 (diagnosis: 84/80/41, exact).
- **Q122** ❌ (substrate drift, not probe error) — golds no longer in the
  merged-cut profile; the query is currently a hit. See below.

## Results (full 131q run; artifacts `benchmark_results/probe_final_pool_reserve_20260802.{json,log}`)

| Variant | queries w/ rescued gold | currently-miss rescued | watch-list rescued | collateral (evicted gold on hit query) |
|---------|------------------------|------------------------|--------------------|-----------------------------------------|
| V1 bm25_top3 | 7 | 2 (Q119, H063) | 3 (Q119, Q133, H063) | **0** |
| V2 dense_top3 | 11 | 1 (Q119) | 2 (Q119, Q133) | 0 |
| V3 merged_11_15 | 17 | 2 (Q119, H021) | 2 (Q119, Q133) | 1 (Q44) |
| V1+V3 | 19 | 3 (Q119, H021, H063) | 3 | 1 (Q44) |

Window stats: 113/131 queries run a full 30-window (min 13). V1 injects a
mean of 1.16 candidates/query (36 queries need zero injection).

### Per-rescue detail (V1, the zero-collateral variant)

| Query | Status | Rescued gold |
|-------|--------|--------------|
| Q119 | MISS (flapper) | g2 `find_project_at_different_drive` (BM25 rank 1) |
| H063 | MISS (flapper) | g3 `handle_find_similar_code` (BM25 rank 3) |
| Q133 | **HIT, MRR 1.0** | g2 `_LspClient.request` (secondary gold — recall-only upside) |
| Q38/Q49/Q99/Q117 | all HIT rank 1 | secondary golds (recall-only upside) |

### Why V3 / V1+V3 are strictly worse

- **Q44 collateral**: grade-1 `BM25Index.save` (currently in-window at final
  rank 12 on a query already at MRR 1.0) is tail-evicted.
- **H021 is a wash, not a rescue**: V3 injects grade-3 `_path_to_uri`
  (merged output rank 12) but its tail-eviction removes H021's *other*
  grade-3 gold `LSPResolver._run_lsp` (currently in-window at final rank
  12). Net in-window gold count on H021: unchanged.

## Gate evaluation

Formally, V1 posts "3 watch-list rescues, zero collateral" — but the gate
says *stable misses*, and the diagnosis taxonomy is explicit: Q119, Q133
and H063 are bf16/bimodal flappers whose MRR is already nonzero in some
rounds (Q133 is 1.0 in this run; H063 flaps 0-0.143; Q119 flaps 0-0.2).
Any MRR conversion from rescuing flappers would land inside the measured
bf16 noise floor (~21 MRR flips / 9 material per identical round pair,
`RERANKER_FP32_DETERMINISM_AB_20260802.md`) and could not survive the
campaign's own attribution rules (bimodal flappers get no credit). The two
queries the reserve was designed for — Q121 and Q122 — get nothing from any
variant. **Gate fails on substance, not on arithmetic.**

Standing caveat, moot now but binding on any future build: pool membership
≠ ranking win (the mhexp-0.25 lesson — pool_hit gains that never convert).
This probe measures the *ceiling*; only an A/B measures conversion. The
membership simulation also cannot predict listwise reshuffling: injecting
candidates changes every score in the window (context-dependent scorer), so
even the zero-collateral accounting is a membership-level statement only.

## Substrate drift findings (recorded for future diagnosis)

Index at probe time: 2,273 chunks (diagnosis era: 2,253). Two profiles moved:

- **Q122 is now a HIT** (best final rank 3). Its grade-1 gold sits at fused
  rank 1 but is hop-1-rerank-demoted (never enters the merged pool);
  the grade-2 gold carries the query. The merged-cut classification for
  Q122 is stale on this substrate.
- **Q119 reclassified this substrate: hop-1-rerank-demotion, not pool
  assembly.** Its two strongest golds sit at fused ranks 1 and 11 yet
  neither reaches the merged pool — the hop-1 listwise rerank demotes both
  below the seed cut (initial_k=20). No final-pool mechanism can touch
  that; the failure happens two stages earlier.

Consequence (durable, reaffirms the substrate-drift rule): stable-miss
profiles must be re-probed on the current substrate before designing any
lever against them.

## Spec for the deferred lever (if ever revisited)

If a future campaign builds this — most plausibly a **recall@k campaign**,
where V1's zero-collateral membership gains on 7 queries are real upside —
the spec is:

- **Variant: V1 only** (raw-BM25 top-3 carry-forward). V2 adds nothing V1
  doesn't; V3-class protection costs collateral (Q44) for wash-level gains.
- Capture raw-BM25 top-N chunk ids in `SearchExecutor.execute_single_hop`
  (`search/search_executor.py:110-234`); thread to `HybridSearcher.search`
  final pool assembly (`search/hybrid_searcher.py` ~766-812, before the
  final `rerank_by_query`); generalize `_apply_hop1_reserve`
  (`search/reranking_engine.py:253-294`) — promote into the 30-window,
  evict the pre-rerank tail.
- Config field default **0 = byte-identical**; benchmark flag incl. the
  `_maybe_reset_for_construction_overrides` force-reset list if
  construction-time; unit tests incl. default-0 byte-identity.
- Gate on **recall@10/recall@20 conversion**, not MRR (the rescuable
  population is flappers + secondary golds on already-hit queries).
  Attribution rules as established (control arm, no flapper credit,
  2-agreeing rounds, fresh same-substrate baseline).

## Consequences

- Campaign close-out Step 3 (reserve build + A/B) is **skipped**.
- The recall-improvement campaign's lever list is now fully dispositioned:
  every config lever measured-and-rejected, the final code lever probed and
  deferred with a written spec and reopening condition (a recall@k-focused
  campaign).
- Remaining stable-miss reality on the current substrate: **Q121 only**
  (rrf-arithmetic, no-lever). Q122 hit by drift; Q119/Q133/H063 remain
  flapper-class, mitigated by the 2-agreeing-rounds rule, with Q119's
  hop-1-rerank-demotion profile noted for any future hop-1 work.
