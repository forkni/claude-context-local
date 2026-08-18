# Dedup/sort `find_connections`' `indirect_callers`; decline the fan-out cap

Status: accepted
Date: 2026-08-18

## Context

The prior L5 + L2a plan (commits `589f989` / `345a165` / `5450c29`) closed with three items
explicitly left open: "L3/L4 remain gateable-not-built, `ego_graph_enabled`'s behavior and the
dead-code `guidance.py` key mismatch are untouched." `docs/plans/CODE_RETRIEVAL_AGENT_DISPOSITION_20260818.md`'s
L4 entry framed the open item as "cap the unbounded call-edge lists," measured off a single worst-case
number (317 direct callers on `MetadataStore.get`, driven by known `_node_variants` bare-symbol
conflation) and gated on `scripts/benchmark/run_caller_recall.py` showing no recall drop.

Reconnaissance for this change found that framing rests on two wrong premises, plus a real but
different defect in the same code:

1. **L4 aimed at the wrong list.** `evaluation/CONTEXT_COST_PROBE_20260818.json`'s
   `connections_fanout` data (28 non-error anchors, 14 primary + 14 secondary) shows
   `direct_callers` maxes at **56** (median 2.5) and `direct_callees` at **21** (median 3.0) — both
   small and already effectively bounded in practice. The entire cost lives in `indirect_callers`:
   median **17** (primary) / **18.5** (secondary), max **480** on `C005`
   (`HybridSearcher.get_by_chunk_id`) / **636** on `Q66` (`FaissVectorIndex.load`), at a stable
   marginal **~97–99 tiktoken tokens per impacted entry** (linear fit of `tokens_tiktoken` against
   `total_impacted` across all 28 anchors, slope ≈99.4, intercept ≈1,251). Cost is also sharply
   concentrated: the top 2 primary anchors by token count are **61.7%** of all primary fan-out
   tokens; the top 4 secondary anchors are **77.9%** of secondary. A cap sized against
   `direct_callers`/`direct_callees` — the framing in the original L4 entry — would move
   essentially nothing.
2. **L4's proposed gate is vacuous.** `run_caller_recall.py:108-110` reads only
   `report.direct_callees` / `report.direct_callers` against 7 golds each in
   `evaluation/caller_golden.json` / `callee_golden.json`. It cannot observe `indirect_callers` at
   all, so it would pass by construction for a cap on the one list that actually matters. **No
   indirect-caller ground truth exists in this repo.**
3. **The real defect in `indirect_callers` is hygiene, not size.**
   `search/relationship_analyzer.py:125-126` (pre-fix) read:

   ```python
   direct_callers = self._dedup_and_sort_edges(enriched_direct)
   indirect_callers = enriched_indirect          # <-- the one list that skipped it
   ```

   `_dedup_and_sort_edges` exists because `_enrich_callers` can emit the same `chunk_id` more than
   once with different provenance (a symbol-name AST edge recovered at 0.5 confidence and a
   directly-resolved LSP/libcst edge at 0.9–0.98 pointing at the same target), and because graph
   edge-iteration order depends on which resolver finishes first under the thread pool and is
   otherwise non-deterministic run-to-run. That reasoning applies verbatim to `indirect_callers`,
   the longest of the three lists and the only one that shipped raw. The production MCP server does
   not run under `PYTHONHASHSEED=0`, so `find_connections` was returning `indirect_callers` in an
   unstable order on every call, with duplicates possibly inflating `total_impacted`.

## Decision

Route `indirect_callers` through the same `_dedup_and_sort_edges` helper its two sibling lists
already used — one line, `search/relationship_analyzer.py:126`:

```python
indirect_callers = self._dedup_and_sort_edges(enriched_indirect)
```

This dedups by `chunk_id` (keeping the entry with the highest `resolver_confidence`) and sorts by
`(-resolver_confidence, chunk_id)`, restoring parity with `direct_callers`/`direct_callees` and
making `find_connections` output deterministic for the first time. `total_impacted` now reflects
the deduped length, which can shift the count `generate_impact_message` reports — that is a
correction of a previously-inflated number, not a regression.

**Decline to build the fan-out cap.** The cap is not implemented in this change and has no
gate it could pass today.

## Measured (in-process, 2026-08-18, self-index, `max_depth=3`)

Driven directly via `RelationshipAnalyzer.analyze_impact()` (in-process, no MCP round trip — the
raw C005/Q66 payloads are 56–71K tiktoken tokens each and would flood an agent context if fetched
live), matching `run_caller_recall.py`'s existing in-process pattern:

| Anchor | raw enriched (pre-dedup) | unique `chunk_id`s | post-fix (deduped/sorted) | duplicates collapsed | determinism (2 calls) |
|---|---|---|---|---|---|
| C005 (`HybridSearcher.get_by_chunk_id`) | 566 | 566 | 566 | 0 | `order1 == order2` → **True** |
| Q66 (`FaissVectorIndex.load`) | 706 | 701 | 701 | 5 | `order1 == order2` → **True** |

Two things worth recording precisely because they cut against the plan's own working hypothesis:

- **The live counts (566 / 701) differ from the probe's captured 480 / 636.** The self-index has
  grown/changed since `evaluation/CONTEXT_COST_PROBE_20260818.json` was captured — expected
  substrate drift, not a discrepancy in the fix.
- **Dedup's raw duplicate-collapse effect is small — 0 and 5 entries respectively — not the "the
  tail collapses" outcome the plan flagged as an open hypothesis.** `_traverse_inbound`
  (`graph/graph_queries.py:718-731`) already dedups by graph *node* via its `reported` set, and
  `_node_variants`' many-to-one node→chunk_id mapping turns out to produce few actual collisions on
  these two anchors today. **The determinism fix, not a size reduction, is this change's real
  effect** — `find_connections` previously returned a different `indirect_callers` order (and
  potentially a different duplicate count) on every call against the same target; it now returns
  the same list, in the same order, every time.

## Deferred: the fan-out cap

Not built. The gate gap identified above stands: `run_caller_recall.py` cannot grade indirect
edges, and no indirect-caller golden set exists in this repo, so there is currently no way to
measure whether truncating `indirect_callers` at some N would discard a caller an agent actually
needed.

**Reopening condition**: build an indirect-caller golden set first (mirroring
`evaluation/caller_golden.json`'s direct-caller structure, scoped to depth >1 edges), then design
and gate a cap against it. When that cap is eventually built:

- It must apply *after* the `_dedup_and_sort_edges` sort this change adds — truncating a
  non-deterministically-ordered list would return a different set of "top N" callers on every call,
  which is exactly the bug this change fixes for the untruncated list.
- It should surface an explicit `indirect_callers_truncated: N` count in the response, following
  the P11 lesson from the L5 work (silent truncation is a defect class of its own, distinct from
  the truncation itself).

## Out of scope

- **Building the fan-out cap** — blocked on the missing indirect-caller golden set described above.
- Re-deriving the concentration/median/max figures against a fresh probe run — the numbers above
  are a point-in-time measurement (2026-08-18 self-index); if a future cap design needs current
  numbers, re-run `scripts/benchmark/probe_context_cost.py`'s `connections_fanout` arm rather than
  reusing these.
