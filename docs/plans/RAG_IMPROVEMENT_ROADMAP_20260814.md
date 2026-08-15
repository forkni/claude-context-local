# RAG Improvement Roadmap — RepoScope + DyCoder transfer (2026-08-14)

Status: **A1 + A2 in scope (approved)** | A3/A4/Track B **deferred design record**

Source papers (in `docs/plans/`):

- **RepoScope** (ICSE'26, arXiv 2507.14791, `2507.14791v2.pdf`)
- **DyCoder** (ASE'26, arXiv 2608.01927, `2608.01927v1.pdf`)

## Context

Both papers target retrieval-for-code-generation; this system is retrieval-for-search
(MRR/recall on the 63q/131q golden sets). The transferable ideas are (A) new in-pipeline
scoring/retrieval **mechanisms** and (B) agent-facing **context assembly** — not the
papers' generation-time evaluation.

Key transferable findings:

- **RepoScope**: callers & call chains have the highest utility-per-token; call-chain
  candidates scored by `λ1·embedding_sim + λ2·log2(shared call counts + 1)`; body-free
  entity embeddings (name + signature + docstring + path); structure-preserving
  serialization (file→class→member tree); two-stage token budget (uniform pre-allocation,
  priority-ordered reclamation).
- **DyCoder**: post-validation of every claimed dependency against the repo index
  (discard on miss); graph-derived context is complementary to dense retrieval
  (+7.5–31% on any retriever); LLMs identify callees easily but **cannot identify
  callers without global analysis** — the index must supply them.

**Architectural mapping**: this MCP server + the consuming agent *is* the DyCoder
architecture — the agent plays the reasoning LLM (Select/Expand); the tools play Visit,
validation, and global caller lookup.

### Hard constraints honored by this roadmap

1. The recall campaign is **CLOSED** (`evaluation/RECALL_CAMPAIGN_CLOSEOUT_20260802.md`):
   every config-level lever measured-and-rejected. Only genuinely **new mechanisms**
   remain as a recall path.
2. The final-pool reserve V1 gate **FAILED** (`evaluation/FINAL_POOL_RESERVE_PROBE_20260802.md`);
   it is a deferred spec with an explicit reopening condition (recall@k campaign,
   gated on recall@10/20, V1-only).
3. **Merged-cut** dominates stable misses (8/17 graded golds,
   `evaluation/STABLE_MISS_DIAGNOSIS_20260802.md`).
4. Deterministic benchmark methodology: PYTHONHASHSEED=0 canons; re-baseline after any
   search-path commit (substrate-drift rule); gate on aggregates; quality-neutral control
   arms; new signals ship disabled-until-A/B-pass. INDEX_VERSION bumps force full reindex.
5. Presentation-layer changes are not gated by the recall campaign; they must stay
   deterministic, token-efficient, and additive for existing MCP clients.

---

## Track A — In-pipeline retrieval scoring (benchmark-gated)

### Grounding facts (verified by direct file reads, 2026-08-14)

- `MultiHopSearcher._graph_expand` hard-codes `score=0.0` for every graph-hop candidate
  (`search/multi_hop_searcher.py:226`), while semantic hop-2 candidates carry real FAISS
  cosine (`:140`). `RerankingEngine.rerank_by_query` sorts the ~83-candidate merged pool
  by raw `.score` (`search/reranking_engine.py:332`) before cutting to the 30-slot rerank
  window — three incomparable scales (hop-1 rerank scores, cosine similarity, constant
  0.0). Graph-hop candidates always sort to the bottom regardless of relevance: a
  **structural defect, not a tuning problem**.
- `CodeGraphStorage.get_neighbors` weighted BFS weights edges purely by relationship type
  (`graph/graph_storage.py:522`); an ambiguous AST edge (resolver_confidence 0.5) gets
  identical traversal priority to an LSP-resolved edge (0.98). `_iter_matching_neighbors`
  already has `edge_data` in scope at both yield points — confidence is persisted per-edge
  but never threaded through. No reindex needed.
- Terminology caution: the containment-credit scorer in `evaluation/metrics.py:800-885`
  is an unrelated benchmark-scoring mechanism that shares the word "merged" — the
  merged-cut lever is multi-hop pool-assembly flooding, not chunk merging.

### A1. Call-evidence scoring for graph-hop candidates — IN SCOPE (flagship)

RepoScope's chain score transfers onto data we already have; its K-means/cluster
machinery is rejected (overkill — call counts and adjacency are already queryable; no
offline clustering, no new index artifact, no INDEX_VERSION bump).

1. New `GraphQueryEngine.score_call_evidence(chunk_id, reference_ids) -> float` in
   `graph/graph_queries.py`: returns `λ2·log2(fan_in + 1)` **gated on call-adjacency to
   at least one reference id** (the hop-1 top-k). The query-conditioning is what
   distinguishes it from the rejected static `centrality_alpha` — it only fires when the
   candidate is call-connected to something the query already surfaced.
2. In `_graph_expand`, replace `score=0.0` with
   `score = anchor_score · cosine(query, candidate) + call_evidence`, capped
   (`min(…, anchor_score)`). Candidate embeddings via **batched FAISS reconstruction** —
   reuse the two-pass pattern in `EgoGraphRetriever.score_neighbors`
   (`search/ego_graph_retriever.py:311-476`): batched `_faiss_index.reconstruct` +
   one-matmul cosine, anchor-score-scaled decay fallback. Zero new embedding compute.
3. Thread `query_embedding` through `_graph_expand`/`_hybrid_expand` signatures
   (precedent: `search()` already threads it into `_single_hop_search`). It is **None in
   BM25 mode or on embed failure** — degrade gracefully. The `single_pass` branch also
   consumes the new scores; include in regression coverage.
4. Optional follow-up (only if 1–3 under-deliver): pool-cohesion boost in
   `CentralityRanker.rerank()` — pure ranking quality, outside recall-campaign scope.

- Config: `GraphEnhancedConfig` (`search/config.py:995-1081`) —
  `graph_hop_call_evidence_enabled` (default **False**),
  `graph_hop_call_evidence_lambda` (start at paper's λ2=2.0 rescaled). Field pattern:
  `field(default=…, metadata=spec(flat_alias=…, reader="search/multi_hop_searcher.py"))`.
  Add to `FORBIDDEN_AUTO_TUNE_KEYS` only after ship-and-lock.
- A/B gate: 63q + 131q, 2 rounds, deterministic harness. Primary **recall@10/recall@20**,
  MRR secondary; paired CI excludes zero; quality-neutral control arm; fresh re-baseline
  immediately before running.
- Risks: hot path (O(1) lookups only); mis-tuned λ2 = config-resweep failure mode (tune
  only via A/B); real graph scores add window competition for hop-1 seeds
  (`hop1_reserved_slots=6` still protects the top; gate catches regression);
  `_graph_expand` serves both `multi_hop_mode="graph"` and `"hybrid"` — full regression
  suite required.

### A2. Confidence-weighted graph traversal — IN SCOPE

DyCoder's "discard unvalidated claims", transposed to traversal time: extend
`_iter_matching_neighbors` to also yield `edge_data`; in the weighted-BFS branch of
`get_neighbors` (`graph/graph_storage.py:503-524`), multiply the type-weight by
`edge_data.get("resolver_confidence", 1.0)` and/or drop edges below a config floor
before pushing to the priority queue.

Verified attribute semantics: `add_call_edge` persists `resolver_confidence` /
`resolver_source` / `confidence` only via `**kwargs` — the float is present on
resolver-touched **calls** edges only, so the 1.0 default leaves non-call relationship
edges and legacy edges byte-identical. Read only the float `resolver_confidence`; never
parse the legacy string `confidence` tags. The `min_confidence` floor in
`search/call_edge_injection.py:185-197` applies only to the resolver-injection merge —
base in-file AST edges are never floored; this closes that gap.

- Config: `min_traversal_confidence` (default **0.0 = byte-identical no-op**) +
  `traversal_confidence_weighting_enabled` (default False). Zero INDEX_VERSION impact.
- A/B gate: changes neighbor *sets* — gate on **recall@10/20 + pool_hit_rate**, MRR as
  guard-rail. Control arm = threshold 0.0.
- Risk: some "ambiguous" edges are correct-but-unconfirmed; strict paired-CI rule.

### A3. Final-pool-assembly reserve V1 — DEFERRED

After A1/A2 land, re-run the read-only probe
(`scripts/benchmark/probe_final_pool_reserve.py`) on the new substrate; build only if
the ceiling still shows zero-collateral recall@10/20 upside. If built: exactly the
deferred spec (raw-BM25 top-3 captured in `SearchExecutor.execute_single_hop`, threaded
to `HybridSearcher` final assembly, `_apply_hop1_reserve` generalized;
`final_pool_bm25_reserved_slots` default 0 = byte-identical). The graph-channel
extension (reserving direct callers of top dense hits) requires its own membership
probe first — probe-before-build rule. Expectation: the original probe rescued only
flappers/secondary golds — low-cost, small-upside.

### A4. Body-free auxiliary embedding view — DEFERRED

`create_embedding_content` (`embeddings/embedder.py:914-1048`) already prepends the
structural header, imports, parent-class signature, and docstring; the function
signature is the first line of `chunk.content` and survives truncation. A second
signature-only leg duplicates most of that signal at 2× embedding compute/storage plus
an INDEX_VERSION bump, with no cheap fusion path. **Reopening path**: a reranker-only
pilot — feed the reranker a signature+docstring+path document representation derived
from `chunk.content` head lines (no index change) — run only if A1–A3 leave the
Q121-style name-heavy misses unconverted.

### Not transferable: DyCoder's LLM-trajectory post-validation core

No LLM-driven Select→Visit→Expand hop exists in this pipeline to validate. Its two
transferable ideas are captured: channel complementarity → A3; discard-unvalidated-
claims → A2 (+ B1 at the display layer).

---

## Track B — Agent-facing context assembly (MCP surface) — DEFERRED

Each item is independently shippable, additive, default-off; not gated by the recall
campaign. Recommended order B1→B5.

### B1. Confidence filtering of graph edges in `find_connections`

Opt-in `min_resolver_confidence` (or `hide_ambiguous`) on `find_connections`. Filter
callers/callees/indirect after `_dedup_and_sort_edges`
(`search/relationship_analyzer.py:201-227`), keeping the `caller_confidence` /
`callee_confidence` breakdown counts intact. Pure display-layer filter. Files:
`search/relationship_analyzer.py`, `mcp_server/tools/search_handlers.py`,
`mcp_server/tool_registry.py`. Effort S (~1 day).

### B2. Structure-preserving tree view (RepoScope serialization)

Opt-in `include_tree_view` on `search_code`/`find_connections`: a supplementary
pre-rendered string field (file → class → member, preorder + indentation, scores
annotated) — never replaces the flat ranked lists. Deterministic ordering; string
passes through verbose/compact/ultra untouched (`mcp_server/output_formatter.py` leaves
string values alone). Reuse `_reorder_by_source_position` grouping
(`mcp_server/tools/result_view.py:153-210`). Effort S (1–2 days).

### B3. Signature+docstring enrichment of `find_connections` entries

Opt-in `include_signatures`: entries additionally carry persisted `docstring` (capped
~100 chars) and a one-line signature derived from persisted `content_preview` — no
schema change, no reindex. Phase 2 (persisted `signature` key + reindex) deferred
pending evidence the approximation is insufficient. Effort S (2–3 days).

### B4. Inline top-caller hints on `search_code` results

Opt-in `include_top_callers`: per result, read incoming `calls` edges via in-memory
`GraphView.in_edges()`/`node()` (`search/graph_view.py`), top-2 by resolver confidence,
attach minimal `top_callers: [{name, file}]` (~10–15 tokens/result). Narrower than the
heavy `include_result_graph` path. Effort S (~2 days).

### B5. Two-stage token budget (RepoScope)

Refactor `SearchOrchestrator._apply_source_order_and_budget`
(`mcp_server/tools/search_orchestrator.py:438-485`) into partition (by `source` tag) →
fixed-weight pre-allocation → per-partition truncation → priority-ordered reclamation.
Activation gate unchanged (`max_context_tokens > 0`; default 0/unlimited). Higher-value
variant on `find_connections`: opt-in `max_context_tokens` allocating callers → callees
→ indirect → similar. Order is never changed — only which already-ranked items survive
truncation. Effort M (3–4 days).

**Rejected**: a `get_file_tree` MCP tool (DyCoder entry-point selection) — redundant
with the consuming agent's native Glob/ls.

---

## Verification protocol (Track A)

- `./scripts/test/run_tests.sh tests/unit/ -x -q` green throughout; targeted suites for
  touched areas; byte-identity test for every new config field at its default.
- A/B per arm: fresh re-baseline (63q + 131q, 2 rounds, PYTHONHASHSEED=0 harness) →
  treatment + control in the same session → gate recall@10/20 (+pool_hit_rate for A2),
  paired 95% CI excluding zero, MRR guard-rail → default flip only on a pass; negative
  results recorded in `evaluation/`.
- Per-query watch-list (informational; gate stays on aggregates): Q122, H063
  (`handle_find_connections`), Q121 (`CodeIndexManager` grade-2), Q119 grade-2s.
- A1 and A2 land as separate commits so the combined re-baseline brackets a clean
  substrate.
