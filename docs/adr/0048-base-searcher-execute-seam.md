# One retrieval seam on `BaseSearcher`: `execute(request)` behind `search(...)`

Status: accepted
Date: 2026-08-19

## Context

`BaseSearcher.search(self, query: str, k: int = 5, **kwargs)` (`search/base_searcher.py`) was a
contract so loose that both concrete searchers violated it: `HybridSearcher.search` and
`IntelligentSearcher.search` each declared their own, genuinely different signature, and both
carried `# pyrefly: ignore [bad-override]` to silence the mismatch. Because the two signatures
differed, `search_orchestrator.py`'s Block D had to ask *which concrete class am I holding* and
hand-write two call sites — the conditional ADR-0030 Phase 2 explicitly deferred (*"replacing
that one is Replace Conditional with Polymorphism on `BaseSearcher` ... out of scope for this
round"*). This is not an ADR-0018 leftover — ADR-0018 collapsed the *callback* contract inside
`HybridSearcher`, never this arity.

Two findings shrank the work before it started:

- `IntelligentSearcher.search` accepted `search_mode` and discarded it
  (`return self._semantic_search(query, k, context_depth, filters)`) — so the two adapters
  differed by exactly one real field, `context_depth`.
- `bm25_weight`/`dense_weight` on `search()` had no production caller. Every probe/benchmark that
  varies weights already builds a `RetrievalRequest` directly; ADR-0019's stated reason for
  keeping those kwargs on `search()` was stale.

The trap to avoid was collapsing `search(query, k, …)` into `search(request)` directly — that
breaks roughly 11 benchmark/probe call sites and ~20 unit-test sites, editing the measuring
instrument in the same change as the thing being measured.

## Decision

Split the seam from the convenience. `BaseSearcher` gains an abstract `execute`:

```python
@abstractmethod
def execute(self, request: RetrievalRequest) -> list[SearchResult]: ...

def search(self, query, k=..., *, config=None, **overrides) -> list[SearchResult]:
    return self.execute(RetrievalRequest.build(query, k, config or get_search_config(), **overrides))
```

- `execute` is the seam: one signature, two real adapters (`HybridSearcher`, `IntelligentSearcher`),
  no `**kwargs`. Both `pyrefly: ignore [bad-override]` suppressions are deleted — the two adapters
  now share one real signature, so there is nothing left to suppress.
- `search` stays a concrete method on `BaseSearcher` with today's call shape, so every existing
  script/probe/test call site keeps working unedited. It survives the deletion test: delete it and
  every call site would have to hand-build a `RetrievalRequest` instead.
- `RetrievalRequest.build(...)` (new `@classmethod` on `search/types.py`) is the one place every
  `None` resolves against `config`: `bm25_weight`, `dense_weight`, `min_bm25_score`,
  `use_parallel`, and `SearchMode(x)`-with-`ValueError`-fallback normalization. `config` is a
  required parameter, so `types.py` carries no runtime import of `search/config.py`; the
  `config or get_search_config()` fallback lives in `BaseSearcher.search` via a local import, the
  same pattern `mcp_server/search_factory.py` already uses.
- `RetrievalRequest` gained a tenth field, `context_depth: int = 1`. It defaults, so every existing
  constructor call site needed zero edits. `HybridSearcher.execute` ignores it exactly as it
  ignored nothing today; `IntelligentSearcher.execute` reads it — mirroring the existing asymmetry
  where `IntelligentSearcher` already ignores `bm25_weight`/`use_parallel`/`min_bm25_score`.
- Each adapter's default search mode became a class attribute (`_DEFAULT_SEARCH_MODE`), read by
  `BaseSearcher.search`, replacing a conditional. Since `IntelligentSearcher` discards the value
  anyway, this is cosmetic-but-honest.
- `search_orchestrator.py`'s Block D collapsed from a two-branch `is_hybrid` dispatch to one
  `searcher.search(...)` call site (`:414-433`). `SearcherView.is_hybrid` stays live — it is still
  needed by `build_effective_config(plan, base_config, is_hybrid)`, which legitimately gates
  ego-graph/parent-retrieval. Only the *dispatch* conditional went away.

### Two hats — three commits

1. **Refactor, no behaviour** (`eabe24d`). Added `execute` + `RetrievalRequest.build` +
   `context_depth`; `RetrievalRequest.build`'s `min_bm25_score` stayed the literal `0.0`, i.e.
   today's undeclared default. Deleted both `pyrefly: ignore` lines. Collapsed Block D. Nothing
   observable changed.
2. **Behaviour: one BM25 floor** (`937c31b`). Flipped `build`'s `min_bm25_score` resolution from
   the literal `0.0` to `config.search_mode.min_bm25_score` (`0.1`), deleting the last duplicate
   default — mirroring the pre-existing `bm25_weight`/`dense_weight` `None`-fallback pattern in
   the same method. `search_orchestrator.py` (feeding `search_code`) always passes
   `min_bm25_score` explicitly (`:428`), so this commit is mechanically inert on `search_code`.
   The only affected call sites are `RelationshipAnalyzer._resolve_by_symbol`
   (`relationship_analyzer.py:643-669`) and `_resolve_type_chunk` (`:786-805`) — both feed
   `find_connections`, reached via `_enrich_callers`, `_enrich_callees`, `_resolve_target`, and
   `_enrich_forward`. Both previously relied on the undeclared `0.0` default and now see the
   `0.1` config floor instead. Gated separately from commit 1 so it is independently revertable.
3. **Docs** (this commit). This ADR, the `docs/adr/README.md` row, a `SESSION_LOG.md` entry, and
   the stale `search_orchestrator.py:498-501`/`:511` line references in `RetrievalRequest`'s
   docstring and ADR-0018 — the real current sites are `:414-416`
   (`build_effective_config`) and the search call at `:424`.

## Verification

- **Commit 1 (refactor).** Pinned canon before touching anything: 63q MRR 0.8357, 133q 0.6647
  (workstation tier, F2LLM-v2-0.6B + jina-reranker-v3, `PYTHONHASHSEED=0`). Post-commit-1 re-runs
  were *not* bit-identical against that pin (63q mrr 0.8418, 133q deltas in the ±0.01 range) —
  investigated via a same-code self-repeat control run
  (`evaluation/round4b_post_commit1_63q_r2.json`), which showed the *same order of magnitude* of
  run-to-run divergence (mrr delta 0.0020) purely from re-running identical code. This matches
  documented project history: `PYTHONHASHSEED=0` (ADR-0021) eliminates Python set/dict
  iteration-order flips but not GPU/cuBLAS floating-point nondeterminism in the bf16 reranker.
  Conclusion: the refactor is behaviour-neutral — its divergence from the pin sits inside the
  established noise band, not outside it — but "expect bit-identical results" does not hold in
  practice against this pre-existing, previously-accepted limitation. Golden-dataset chunk-ID
  audit was clean on both datasets despite the anticipated chunk-boundary-shift risk (removing
  ~30 lines from `HybridSearcher.search` could have shifted its two `split_block` chunk
  boundaries; it did not).
- **Commit 2 (behaviour).** `search_code`'s path was proven mechanically unaffected by static
  analysis (grep confirms `search_orchestrator.py` has exactly one `min_bm25_score=` call site,
  always explicit) rather than a benchmark re-run, since the change cannot reach that path.
  **The `find_connections` gate was not fully executed as originally specified.** The plan called
  for a live-MCP before/after diff on `direct_callers`/`direct_callees` for chunk_ids whose
  callers include `resolver_confidence` 0.5 AST/semantic-fallback entries. In practice this
  requires deliberately engineering a Tier-1 graph-lookup *miss* so `_resolve_by_symbol` falls
  through to its Tier-2 BM25 search (the only path the `min_bm25_score` change touches), and
  independently reloading the running MCP server's `search/types.py` module state between "before"
  and "after" captures — neither was achieved this round. (ADR-0047 hit the same limitation for
  its own live-MCP gate and used snapshot tests as the stronger available substitute; the same
  reasoning applies here.) Verification instead rests on: the full unit + fast_integration +
  integration suite (6138 + 122 passed) both before and after the edit; `pyrefly`/`ruff` clean;
  and code review confirming every `RetrievalRequest` unit test constructs the dataclass directly,
  bypassing `build()` entirely, so is structurally immune to this default-value change. The
  Tier-1→Tier-2 cascade itself (the mechanism `min_bm25_score` gates) is covered by
  `tests/unit/mcp_server/test_code_relationship_analyzer.py`'s existing resolver-cascade tests,
  unchanged by this commit and passing throughout.
- `./scripts/git/check_lint.sh --modified-only` clean at both commits, `pyrefly` clean **without**
  the two deleted suppressions — the point of the round.
- `scripts/benchmark/audit_golden_dataset.py --dataset` clean on both `golden_dataset.json` (77
  queries) and `golden_dataset_expanded.json` (147 queries).

## Known limits (stated plainly, not oversold)

- `IntelligentSearcher` is reachable only when `search_mode.enable_hybrid` is `False`
  (`config.py`, default `True`; `search_factory.py`). It is a real adapter with a real
  construction path, but it is not the deployed one — this is closer to "one adapter plus a
  fallback" than to a fully exercised two-adapter seam.
- The registry/indirection lesson from Workstream B applies again: once Block D calls
  `searcher.execute(request)` instead of naming a class, no static resolver (AST/pyan/LSP) binds
  the orchestrator to either concrete `execute`. `find_connections` on those methods reports
  `direct_callers: []` — a permanent, accurate consequence of the refactor, not a stale index. The
  codebase already pays this elsewhere: `find_connections` on `SearchExecutor.search_bm25` lists
  only probe/harness call sites, never `HybridSearcher`, because production reaches it through
  `_parallel_search`/`_sequential_search` closures.
- Commit 2's `find_connections` gate is unproven by direct live-MCP measurement (see Verification
  above) — it rests on unit-test coverage of the resolver cascade plus static call-site analysis,
  not an executed before/after diff of the actual runtime BM25 floor change.

## Consequences

- One retrieval seam (`execute`) for both adapters; the orchestrator dispatch conditional is gone.
- One BM25 floor: `find_connections`' resolver fallback and `search_code` now agree
  (`config.search_mode.min_bm25_score`, `0.1`), where they previously silently diverged (`0.0` vs
  `0.1`).
- `RetrievalRequest.build` is now the single place request-field resolution happens, mirrored by
  the `execute`/`search` split rather than duplicated per adapter.

## Out of scope

- Unifying `HybridSearcher`/`IntelligentSearcher`'s deployment gating — `IntelligentSearcher`
  stays reachable only via `enable_hybrid=False`; changing that default is a separate decision.
- A verified live-MCP diff for commit 2's `find_connections` behaviour change — documented above
  as an open gap, not silently assumed clean.
