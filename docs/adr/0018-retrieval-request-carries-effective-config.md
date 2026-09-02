# RetrievalRequest carries the effective config; per-layer re-fetch removed

Status: accepted
Date: 2026-08-01

`search/types.py` gains a frozen `RetrievalRequest` dataclass — query, k, search mode, fusion
weights, filters, and the effective `SearchConfig` — constructed once by `HybridSearcher.search`
and threaded unchanged through `MultiHopSearcher`, the single-hop callback, and
`SearchExecutor.execute_single_hop`. The nine `get_search_config()`/`get_config_via_service_locator()`
re-fetches those layers previously made are deleted; they now read `request.config`.

## Context

Two loose parameters — `bm25_weight`, `dense_weight` — were dropped between
`HybridSearcher.search` and `MultiHopSearcher.search`: the multi-hop branch called into
`_single_hop_search` with nine keyword arguments and neither weight among them, so
`SearchExecutor` fell back to a construction-time snapshot. `MultiHopConfig.enabled` defaults `True`
and ships `True`, so multi-hop is the only branch production ever takes — intent-adaptive fusion
weights have therefore never executed, despite a log line and a `CONTEXT.md` entry both describing
them as live.

The parameter was droppable, and the drop was silent, because it travelled as one of nine untyped
positional/keyword arguments across a callback seam (`single_hop_callback`) with no single object
whose shape a type checker or a test could pin. Collapsing the nine parameters into one module
(`RetrievalRequest`) was the direct fix. That immediately raised a second question: should the
*effective config* — already resolved once per request by the orchestrator, deep-copied and
per-intent mutated at `search_orchestrator.py:427-433` — travel on the same object, or continue
being re-fetched from the process-global singleton at each of the seven sites that currently call
`get_search_config()`?

Alternatives considered:

- **Leave config as a global re-fetch, only collapse the leg parameters.** Smaller diff, and it
  avoids anything that looks like the DI container [ADR-0005](0005-no-di-container-module-singleton-state.md)
  declined. Rejected: the same request already observably disagrees with itself under this shape —
  `reranker.single_pass` is read from the orchestrator's per-request copy at
  `hybrid_searcher.py:782` and from the global singleton at `multi_hop_searcher.py:486` and
  `search_executor.py:222`, within one request. Today the two values agree (nothing mutates
  `single_pass`), so the divergence is latent — but it is the same *shape* as the weight bug this
  ADR exists to close, one level up, and leaving it in place after fixing D1 would be inconsistent.
- **A config-resolving service/DI container.** Rejected per ADR-0005 for the same reasons: no real
  swappability consumer, and it is the layer-inversion vector — four modules already import
  `mcp_server/utils/config_helpers.py` (a documented pass-through to `search/config.get_search_config`)
  purely to call `search.config` by a longer name, which is itself an
  [ADR-0004](0004-scoped-tracing-only-observability.md)-violating import cycle. Deleting one such
  import (`multi_hop_searcher.py:12-14`) is a direct consequence of this decision, not its
  motivation.
- **Config as a field on the request, re-fetches deleted.** Adopted. One object is now the sole
  source of truth for a request's config; `request.config` cannot diverge from itself the way two
  independent re-fetches can.

## Decision

`RetrievalRequest.config: SearchConfig` is populated once, in `HybridSearcher.search`, from the same
`effective_config` the orchestrator already resolved (`config` kwarg if given, else
`get_search_config()` — unchanged resolution, just moved to one call site). Every layer below reads
`request.config` instead of re-fetching: `search_executor.py:138, 160, 202, 212, 222` and
`multi_hop_searcher.py:399, 486`. `reranking_engine.py`'s five re-fetches are out of scope — the
reranker takes no request today; threading one in is a follow-on candidate (C1), not this decision.

The freeze is shallow: `RetrievalRequest` is `frozen=True, slots=True`, but `config` is a mutable
`SearchConfig` reachable through it. Nothing below `HybridSearcher.search` may mutate it — the
orchestrator's only config mutation (intent-driven edge weights,
`search_orchestrator.py:414-416`) happens *before* the request is built (`:424`), so no caller
observes a request whose config changes mid-flight. This is a documented invariant on the
dataclass, not an enforced one.

## Consequences

- The nine-parameter callback contract collapses to `(request, query_embedding=None)` at every
  layer; `HybridSearcher._single_hop_search`, previously a 9-parameter pure pass-through, collapses
  to two arguments.
- `SearchExecutor` and `HybridSearcher` lose their own `bm25_weight`/`dense_weight` constructor
  parameters and instance fields — the exact `is not None` fallback shape that hid the original
  defect is deleted, not patched. `HybridSearcher.optimize_weights` depended on mutating that now-
  deleted instance field via `_set_hybrid_weights`; it had zero production callers, and its
  objective (`analyze_fusion_quality`'s diversity/coverage-balance composite) cannot measure
  retrieval quality regardless — it is deleted alongside, not repaired.
- A searcher's config-derived state (weights, `single_pass`, everything now read from
  `request.config`) reflects the config at *request time*, not construction time. Before this ADR,
  `SearchExecutor`'s weight fields were frozen at construction and could go stale across a config
  reload; after, `request.config` is resolved fresh per call. This is a behaviour change only in the
  presence of a runtime config change between requests — the stale-snapshot case was already a
  latent bug (see the `single_pass` divergence above), not a value anyone relied on.
- Test fallout: any test that patches config at one layer and expects a different layer to see its
  own separately-mocked config no longer works — config now flows through one object. Mock configs
  used in tests must set every field the pipeline reads truthy-checks on (e.g.
  `query_expansion.enabled = False`), since a bare `Mock()` is truthy and will now be reached by
  code that previously never saw it.
- Landing this behind `SearchModeConfig.intent_adaptive_weights = False` (opt-in pending A/B, same
  pattern as `QueryExpansionConfig.enabled` in [ADR-0012](0012-curated-vocabulary-query-expansion.md))
  means this refactor alone is benchmarked to show *no* movement against the existing 96q/63q golden
  baselines; a later, separate commit flips the flag and is benchmarked on its own.
