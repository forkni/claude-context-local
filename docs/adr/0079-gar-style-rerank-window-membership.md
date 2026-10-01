# Decide rerank-window membership by interleaving, not by sorting mixed score scales

Status: proposed
Date: 2026-10-01

Multi-hop's Pass-2 rerank decides which 30 of the merged pool the listwise model
sees by sorting hop-1 survivors, graph expansions and semantic expansions together
on `.score`, then patching the result with the hop-1 reserve (ADR-0013), the
`graph_hop_unscored` bands (ADR-0039) and `graph_hop_window_cap`. The three score
scales are incomparable, so the sort is wrong for any composition and each patch
treats a symptom. This ADR replaces the sort with window membership by
interleaving (the GAR rule) and stops dropping candidates past the window. It stays
**proposed** until the pre-registered A/B in
`evaluation/GAR_WINDOW_AB_20261001.md` passes; the default remains `"score"` until
then.

## Context

The 09-23 canon (`092f14ab`) to HEAD showed MRR 63q 0.8177 -> 0.7980, 133q
0.6527 -> 0.6128, F-via-similar 0.8668 -> 0.8560. The ranking code did not change in
that range. The embeddings did not move either (cached vs fresh vectors: 1-cos
median 9.5e-4, the same-stack batch-composition noise floor is 1.0e-3), and the
dense stage still ranked the golds first (Q07, Q106, H048 at dense rank #1).

The loss is one deterministic step. `_order_merged_pool("score")` puts jina scores
(hop-1 survivors, about -0.1..+0.2), FAISS cosines (semantic expansions, 0.5-0.9)
and 0.0 (graph expansions) in one sort, so every hop-1 survivor, rank 1 included,
lands in the window's tail. `_apply_hop1_reserve(evict_policy="tail")` then promotes
hop-1 items from past the cut and evicts the window's tail, which is the better-ranked
hop-1 items. Evicted items leave the pool; they are not deferred. On the HEAD
index, 29 of 147 queries (20%) lose a gold at that step: 23 lose a hop-1 gold, 6 a
non-hop-1 gold. Content drift between the canon and HEAD changed how often the
defect fires; the defect itself is older.

`score_reserve_fix` (evict the lowest non-hop-1 first) cannot save those 6, and it
keeps the mixed-scale sort underneath.

## Decision

1. **Interleave membership.** New `merged_pool_policy` value `"gar_interleave"`.
   Hop-1 survivors, ordered by `hop1_rank`, alternate 1:1 with the frontier
   (expansion candidates); when one side runs out the other fills the rest. The
   frontier is ordered anchor-first: by `anchor_rank`, and inside one anchor graph
   and semantic candidates alternate, graph first. The policy bypasses
   `_apply_hop1_reserve` and `_apply_graph_hop_window_cap`, which would otherwise
   run after the order step and break the alternation.
2. **`anchor_rank`.** `MultiHopSearcher` stamps `metadata["anchor_rank"]` on every
   expansion candidate (commit `cf825fc1`): the lowest `hop1_rank` among the anchors
   that produced it, in either channel. Dedup stays first-claim; a later claim only
   lowers the stamp.
3. **Classification** of hop-1 vs frontier is by `metadata["hop1_rank"]`, never by
   `source`: hop-1 survivors are re-emitted as `"multi_hop"`, the same as semantic
   expansions.
4. **Backfill.** `_run_rerank` returns `listwise(window[:30])` followed by
   `candidates[30:]` in incoming order. Candidates are never dropped. This is shared
   by all three rerank passes (hop-1, Pass-2, ego tail) and is a no-op whenever the
   list fits the window, which includes every pass at the canonical k=10.
5. **Harness observability.** `run_sscg_benchmark.py` records per-query
   `gold_in_window` (the window the listwise model scored on the first
   `rerank_by_query` call, i.e. Pass-2 on a multi-hop query), `gold_evicted_by_reserve`
   on legacy-policy legs, and torch / transformers / sentence-transformers / faiss
   versions in `config_metadata.substrate`.

## Reasons

- **GAR (arXiv 2208.08942)** is this pipeline's shape: hop-1 is the initial ranked
  list, expansions are the frontier. GAR never compares scores across sources. It
  alternates sources, orders the frontier by the best-scoring source that produced
  it, and backfills unscored items. `anchor_rank` is that priority.
- **jina-reranker-v3 (arXiv 2509.25085)** ablates input order inside the window and
  finds it barely matters, so membership is the real decision. Its scores depend on
  the whole window, so ADR-0077's single-block invariant stays.
- One rule replaces four mechanisms that each patch the mixed-scale sort.
- Offline simulation on the 124 HEAD Pass-2 pools (`evaluation/GAR_WINDOW_AB_20261001.md`):
  golds in window 145 (`score`) -> 169 (`gar_anchor_first`); graph_hop window
  occupancy median 1 -> 10; hop-1 rank 1 in window 101/115 -> 115/115. Window
  membership only; it cannot say whether the 23 rescued queries gain top-10 rank.

## Considered Options

- **`score_reserve_fix`** (ADR-0013's follow-on): leaves the mixed-scale sort and
  cannot save non-hop-1 golds (6 of the 29). Not adopted, and not an automatic
  fallback if the A/B fails.
- **`channel_priority`** (all hop-1 first, then the frontier): disqualified in
  `evaluation/POOL_ORDER_AB_20260815.md` - 63q MRR CI [-0.0437, -0.0013], recall@5
  CI [-0.0529, -0.0013], graph_hop window occupancy median 7 -> 0, Q12 regressed.
  GAR's 1:1 alternation, with graph and semantic alternating inside the frontier,
  satisfies that report's reopening condition (b), "split the window budget by
  channel", with no tuning setting. The A/B gate re-checks exactly those two CIs.
- **Per-channel quotas:** another tuning setting, the same patching pattern.
- **Sliding-window listwise reranking (RankZephyr, arXiv 2312.02724):** window 30,
  stride 15 costs 3-5x listwise latency and conflicts with ADR-0011 and ADR-0077's
  single block. Deferred as a later, separately measured arm; the trigger is
  `gold_in_window` showing golds stuck past slot 30.
- **`anchor_rank` as first-claimer:** `_hybrid_expand` runs the graph channel over
  all anchors before the semantic channel, so first-claim would give a chunk the
  semantic channel found from anchor 1 the anchor of a later graph hit.

## Consequences

- `reranker.merged_pool_policy` gains a value; it is `benchmark_locked`, so the
  default flip, if the gate passes, is its own commit with a canon re-pin.
- If the gate passes: this ADR becomes *accepted*, ADR-0013 and ADR-0039 are marked
  superseded, and a follow-up refactor deletes the reserve, the bands, the cap, both
  score policies and their config fields. The config loader drops unknown keys, so
  existing config files keep loading.
- If the gate fails: the result is recorded here, the default stays `"score"`, and
  nothing is deleted.
- **Known follow-up, not in scope:** the Pass-3 ego tail rerank has the same
  mixed-scale defect class (Pass-2 outputs carry jina scores, ego neighbours carry
  embedding cosines, and the pool is plain-sorted). It is inert at k=10 (the pool is
  at most 30, so nothing is cut) and unmeasurable by the canon. Backfill stops it
  from dropping results at k>=11; interleaving its membership is deferred.
- `reranker.single_pass` (default off) keeps its plain-score `[:k]` and is out of
  scope.
