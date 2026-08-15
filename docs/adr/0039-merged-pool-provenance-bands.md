# Replace the merged-pool score sort's incidental graph band with an explicit one

Status: accepted
Date: 2026-08-15

## Context

`RerankingEngine._order_merged_pool(results, "score")` (`search/reranking_engine.py`) sorts the
Pass-2 merged multi-hop pool by raw `.score` immediately before the `top_k_candidates` rerank-window
cut. That single `sorted(..., key=lambda r: r.score, reverse=True)` compares three incommensurable
scales:

| Channel | Score provenance |
|---|---|
| hop-1 survivors (`source="multi_hop"`, `hop1_rank` set) | jina listwise relevance, overwritten by `neural_reranker.py`'s `_apply_rerank_score` |
| semantic expansion (`source="hybrid"`/`"multi_hop"`) | raw FAISS cosine |
| graph expansion (`source="graph_hop"`) | a **fabricated literal `0.0`** placeholder (`multi_hop_searcher.py`'s `_graph_expand`, legacy fallback) — never a relevance signal |

Comparing a fabricated placeholder against real relevance scores is a meaningless operation, per the
standing directive: *"I don't want the code to perform actions which don't make sense even if they
are corrected upstream."* The jina reranker does re-score the window afterward, but window
*membership* is decided by this sort, so the nonsense is load-bearing, not cosmetic.

Three separate merged-pool campaigns closed before this change — `channel_priority`,
`score_reserve_fix`, and `graph_hop_window_cap` A/Bs (`evaluation/POOL_ORDER_AB_20260815.md`,
`POOL_ORDER_CAP_AB_20260815.md`) — all measured-and-rejected and locked in
`FORBIDDEN_AUTO_TUNE_KEYS`. Each tried to *change behaviour* around the broken score. This change
does the opposite: it is scoped to be behaviour-preserving and changes only what the code says about
itself.

## The key discovery: the sort is already banded, by accident

Python's `sorted()` is stable and `reverse=True` does not reverse ties. The pre-existing sort already
produces exactly three bands:

```
[ non-graph, score > 0, descending ] + [ every graph entry at 0.0, insertion order ] + [ non-graph, score < 0, descending ]
```

Measured over `evaluation/probe_rerank_window_20260815.json` (124 queries, 7,071 pool entries):

- `graph_hop`: 2,942 entries, **2,942 exactly `0.0`** (zero exceptions).
- non-graph (`hybrid` 2,480 + `multi_hop` 1,649 = **4,129**): **0 exactly `0.0`**.

So the de facto semantics were already *signal-positive first, unscored graph next in
anchor/insertion order, signal-negative last*. The one condition under which an explicit band and the
incidental sort could diverge — a non-graph candidate scoring exactly `0.0` — fired 0 of 4,129 times
in the capture.

## Decision

Make the banding explicit via a caller-declared, default-off `graph_hop_unscored: bool` parameter,
rather than a config field or a new `merged_pool_policy` value (that key is verdict-locked by the
closed campaigns above).

`_order_merged_pool(results, policy, graph_hop_unscored: bool = False)`, in the
`("score", "score_reserve_fix")` branch:

```python
if not graph_hop_unscored:
    return sorted(results, key=lambda r: r.score, reverse=True)
positive, graph, nonpositive = [], [], []
for r in results:
    if r.source == "graph_hop":
        graph.append(r)
    elif r.score > 0:
        positive.append(r)
    else:
        nonpositive.append(r)
positive.sort(key=lambda r: r.score, reverse=True)
nonpositive.sort(key=lambda r: r.score, reverse=True)
return positive + graph + nonpositive
```

The invariant the flag asserts: every `graph_hop` entry in this pool carries the placeholder. The
band predicate keys on `source` alone (no float comparison) — correctness rests on the caller's
declaration, not on re-deriving it from the data.

**Pinned tie rule:** a non-graph candidate scoring exactly `0.0` lands in the `nonpositive` band,
i.e. after graph, since jina's zero crossing is the signal-negative boundary. Pinned by
`test_order_merged_pool_graph_hop_unscored_divergence_pin`
(`tests/unit/search/test_funnel_characterization.py`) rather than left undocumented.

`MultiHopSearcher.search()` derives the flag from the same gate `_graph_expand` itself reads:

```python
ge_cfg = getattr(config, "graph_enhanced", None)
graph_hop_unscored = not (ge_cfg is not None and ge_cfg.graph_hop_call_evidence_enabled)
```

and passes it at both Pass-2 sites: the `rerank_by_query` call, and the `single_pass` branch's own
identical sort (converted from an in-place `merged_results.sort(...)` to
`RerankingEngine._order_merged_pool(merged_results, "score", graph_hop_unscored)`, since the static
returns a new list rather than sorting in place).

**A1 interaction (preserved exactly):** when `graph_enhanced.graph_hop_call_evidence_enabled=True`
(a separate, measured-and-rejected, default-off mechanism), `graph_hop` candidates carry real
anchor-conditioned scores, so the caller derives `graph_hop_unscored=False` and the plain sort
applies — A1's already-measured behaviour is untouched. The scorer's crash-fallback re-fabricates
`0.0` while the flag still says `False`, so that degenerate path falls back to exactly today's
behaviour rather than being newly banded; this is a documented fail-safe, not a fix.

**Pass-3 excluded — load-bearing, not an oversight.** `hybrid_searcher.py`'s two tail-rerank call
sites pass no `graph_hop_unscored` and take the `False` default. Pass-2 survivors reaching Pass-3 are
still tagged `source="graph_hop"` but by then carry **real jina scores** —
`neural_reranker.py`'s `_apply_rerank_score` overwrites `.score` while preserving `.source`. Banding
those would demote a top-scored graph survivor below every positive candidate: a genuine listwise
input-order change, not a no-op. Banding must stay scoped to where the placeholder actually
originates.

## Verification

- `_order_merged_pool` docstring and `search/config.py`'s `merged_pool_policy` field comment
  corrected: the old comment claimed graph candidates "structurally outrank every hop-1 winner
  regardless of actual relevance", which is false (`0.0` never beats a positive score).
- Unit tests added (`tests/unit/search/test_funnel_characterization.py`,
  `tests/unit/search/test_multi_hop_searcher.py`): default-off byte-identity, banded-equals-plain-sort
  on a realistic pool, the divergence pin, graph-band insertion-order/permutation invariance,
  `channel_priority` unaffected, the Pass-3-style unaffected call, and A1-off/A1-on threading.
  `./scripts/test/run_tests.sh tests/unit/search/ -x -q` — 1,628 passed.
- **Empirical byte-identity gate**: `scripts/benchmark/probe_rerank_window.py --replay
  evaluation/probe_rerank_window_20260815.json`, which replays all 124 captured production pools
  through the changed code and compares the resulting windows against window IDs captured from the
  pre-change code. G3 self-validity: **124/124 PASS**, confirming the banded implementation
  reproduces pre-reformulation production behaviour exactly on real data, not just on constructed
  test pools.

## Consequences

- No measurable behaviour change on any call path exercised today. `graph_hop_unscored` defaults
  `False` everywhere except the two Pass-2 sites in `MultiHopSearcher.search()`, which derive it from
  existing config rather than introducing a new tunable.
- The one live reopening direction this ADR does *not* take — giving `graph_hop` a real,
  anchor-conditioned score instead of a `0.0` placeholder — remains a separate, from-first-principles
  campaign; the A2/A3/A4 mechanisms already measured-and-rejected around this pool are unaffected and
  stay locked in `FORBIDDEN_AUTO_TUNE_KEYS`.
- The false "graph outranks everything" comment in `search/config.py` is corrected, so future readers
  no longer inherit the actual bug that this ADR headed off.
