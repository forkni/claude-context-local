# Research Brief: Recall-Fidelity Levers in claude-context-local (2026-08-14)

**Audience**: an external research agent with **zero prior context** on this project,
tasked with surveying literature and techniques for improving retrieval recall fidelity.
**Purpose**: give you the complete map of what is implemented, what was measured and
rejected (with the failure mechanism), and which failure classes remain unsolved — so
your survey targets only genuinely unexplored territory.
**Status**: local working document (untracked). Companion to
`docs/plans/RAG_IMPROVEMENT_ROADMAP_20260814.md`, which was the output of the *previous*
literature pass and is now largely executed.

---

## 1. Mission & rules of engagement

Your job: find external techniques — from IR, code-retrieval, RAG, and reranking
literature — that could improve recall fidelity in this system, and map them to the
failure classes in §4.

Hard rules for any proposal you produce:

1. **Name the failure class** (§4) the technique targets, and explain the causal path
   from mechanism to that class. "Generally improves retrieval" is not admissible.
2. **Nothing from the rejected catalog (§6) may be re-proposed** unless your proposal
   explicitly addresses that lever's recorded failure mechanism and satisfies its
   reopening condition. Every lever in §6 was measured on this system's own benchmark;
   a paper claiming the technique works elsewhere does not override a local negative
   result.
3. **Proposals must be testable under §9's methodology** — deterministic paired A/B on
   the two golden sets, pre-registered CI gates, probe-before-build for pool-membership
   interventions.
4. **Prefer locally implementable mechanisms**: single RTX 4090 (24 GB), no API-LLM
   calls in the retrieval loop, Python, models that fit alongside a 0.6B embedder and a
   0.6B reranker. Training/fine-tuning proposals are in scope if they run on this
   hardware.
5. §8 lists candidate literature directions per failure class. These are starting
   hypotheses, not boundaries — a direction not listed there is welcome if it passes
   rules 1–4.

## 2. The system as deployed

A local semantic code-search MCP server. Corpus for all benchmarks below is the
project's own codebase (~2,400 chunks, Python-dominant). 9 languages / 27 file
extensions are supported via tree-sitter AST chunking.

### 2.1 The retrieval funnel

Every stage below is load-bearing for the failure taxonomy in §4:

```text
query
  └─ hop-1: BM25 leg (k≈100) + dense leg (k≈100)
       └─ RRF fusion (weights 0.35 BM25 / 0.65 dense) → cut to ~30
            └─ hop-1 listwise rerank → top-20 become "seeds"
                 └─ expansion: graph neighbors of seeds (+~35, score 0.0)
                              + hop-2 semantic on seed vocabulary (+~28)
                      └─ merged pool ~83 candidates
                           └─ listwise rerank, window 30,
                              hop1_reserved_slots=6 protects top hop-1 seeds
                                └─ top-10
                                     └─ ego-graph expansion (+~20) → ~30
                                          └─ FINAL listwise rerank → top-10 returned
```

Key structural facts:

- The **final post-ego rerank runs on every query** (measured: 133/133 queries on the
  expanded set). Any pool-membership intervention that acts only at the merged-pool
  stage delivers nothing — its additions are cut again downstream.
- Graph-expansion candidates enter the merged pool with **literal score 0.0** (no
  fusion score); they survive only if the listwise reranker picks them out of the
  window.
- The two listwise passes (merged + final) are the same model over the same document
  representations — a representation change reshapes *membership*, not just ordering.

### 2.2 Components (deployed values — see §2.4 for doc discrepancies)

| Component | Deployed state |
|---|---|
| Embedder | F2LLM-v2-0.6B, 1024d (adopted 2026-07-26 A/B: MRR +0.026 vs Qwen3-0.6B) |
| Reranker | `jinaai/jina-reranker-v3`, listwise, bf16, 1000-char/doc cap (ADR-0011), window 30 |
| BM25 | identifier-preserving tokenizer (`bm25_tokenizer="whole"`, **no stemming**), stopwords kept, path/symbol token augmentation (INDEX_VERSION 4) |
| Fusion | RRF, weights 0.35/0.65 (BM25/dense) — benchmark-saturated, see §6 |
| Dense index | FAISS; per-model indices (instant model switching) |
| Chunking | tree-sitter AST; context enhancement ON (≤10 import lines prepended to functions, ≤5 class-signature lines to methods); `parent_chunk_id` linkage; synthetic module-summary chunks (demoted 0.82–0.90× at query time); cyclomatic complexity metadata |
| Call graph | layered resolvers, confidence-precedence merge: AST (always-on, string tags exact/ambiguous/recovered) → pyan wildcard 0.6 / direct 0.75 → LibCST FQN 0.90 → LSP/basedpyright 0.98. Deployed: `min_confidence=0.65`, `lsp_enabled=true` |
| Multi-hop | enabled, `expansion_factor=0.5` (0.25 measured and rejected) |
| Ego-graph | expansion **always runs**; the `ego_graph_enabled` flag only widens hop depth/neighbor caps |
| Centrality | PageRank over 21 relationship types, annotation always-on, `centrality_alpha=0.0` (blend rejected — recall degrades monotonically with alpha) |
| Intent classifier | enabled; live effects are exactly: SIMILARITY→redirect to find_similar, GLOBAL→suggest k=10+hybrid, auto-mode application. All other intent machinery measured inert and deleted (ADR-0031) |
| Reserves | `hop1_reserved_slots=6` at the merged-pool rerank window (ADR-0013) — the only reserve that survived measurement |
| Determinism | PYTHONHASHSEED=0 pinned in the benchmark harness (ADR-0021): r1 vs r2 bit-identical, 0 movers |

### 2.3 Benchmark substrate & vocabulary

- **63q canonical golden set**: 63 queries, gold = expected chunk IDs. Currently has
  ~zero hard misses — it functions as a **guard-rail** (a lever must not hurt it).
- **133q expanded golden set**: 108 original + commit-mined "H-category" queries.
  This is where the **upside** lives.
- **F-via-similar view**: 9 find-similar queries evaluated through the
  `find_similar_code` path (secondary view, current pin 0.9021).
- Scoring: strict chunk-ID match with containment credit for merged chunks.
- "**Canon**" = the pinned deterministic baseline for the current code+index state
  ("substrate"). **Substrate drift**: editing any indexed source file changes the
  corpus (the repo indexes itself), so canons are re-pinned after every search-path
  commit; cross-substrate comparisons are invalid.
- Adoption gate (pre-registered per campaign): paired 95% CI on recall@10/recall@20
  excluding zero on the 133q set, MRR guard-rail on both sets, aggregates only.

### 2.4 Doc-vs-deployed discrepancies (if you read the repo's own docs)

`docs/ADVANCED_FEATURES_GUIDE.md` is stale in places. Trust this brief (and
`search/config.py`) over it on: default embedder (guide says BGE-M3; deployed is
F2LLM-v2-0.6B), multi-hop expansion (guide says 0.3; deployed 0.5), ego-graph (guide
says disabled by default; expansion always runs — only widening is gated), and BM25
stemming (guide says Snowball always-on; deployed default is the identifier-preserving
no-stem tokenizer since v0.22.0).

## 3. Current performance & headroom

### 3.1 Deterministic canons (2026-08-14 substrate)

| Dataset | MRR | recall@5 | recall@10 | recall@20 | pool_hit | note |
|---|---|---|---|---|---|---|
| 63q canonical | **0.8722** | 0.7002 | 0.8089 | 0.8427 | 0.9206 | r1==r2 bit-identical |
| 133q expanded | **0.6843** | 0.6668 | 0.7898 | 0.8309 | 0.9248 | ndcg@10 0.6961 |

(63q recall@10/@20 were 0.8041/0.8414 on the immediately preceding Track-A pin of the
same canon; the small differences are substrate drift between same-day reindexes, not
treatment effects. Latency: ~4.0–4.6 s/query median, reranker-dominated.)

- `pool_hit` = the gold appeared in *some* pool at *some* stage (upper bound on what
  ranking fixes alone can recover).
- Query IDs like Q121 or H063 name individual golden-set queries; they appear below
  because campaign records are written at that granularity.

### 3.2 Headroom decomposition

Two distinct populations, requiring different levers:

1. **Membership misses** (gold never enters any pool; mrr=0, pool_hit=0). On the
   current substrate: **Q101, Q106, Q117, Q122, H008, H050** (6 of 133).
   ⚠️ This set is **substrate-dependent** — two members (H034, H066) exited it in the
   latest re-pin without any intervention. Re-derive the miss cohort from a fresh
   baseline before targeting it; never design against a stale list.
2. **In-pool ranking demotions** — the larger population. recall@20 0.8309 vs MRR
   0.6843 means many golds reach a pool but rank poorly (~35 queries at mrr ≤ 0.34 at
   last count). Known members: Q121 (in final window at rank ~20, its only gold),
   H063, Q119.

63q has nothing left to rescue; all upside claims must come from 133q.

## 4. Failure taxonomy — the classes a new lever must target

### 4.1 Merged-cut / pool-flooding (dominant)

The gold ranks well at hop-1, then graph expansion + hop-2 flood the merged pool to
~83 and the window-30 cut or the listwise re-sort demotes it. At the last full
diagnosis this class covered 8 of 17 graded stable-miss golds. It is also the recorded
*prerequisite blocker* for query expansion (§6): expanded queries produced pools of
66–83 in which previously rank-1 golds drowned. No lever has cracked this class; every
attempted pool-membership intervention (§6, reserves) either found nothing to rescue
or displaced more than it saved.

### 4.2 RRF-arithmetic exclusion

Both legs rank the gold mediocrely (measured example Q121: dense rank 84, BM25 rank
80 → fused rank 41) and reciprocal-rank fusion arithmetic cannot lift it into any cut.
Confirmed no-config-lever: no weight setting rescues a gold both legs agree is
mediocre. This class needs a *different fusion mathematics* or a better leg, not
tuning.

### 4.3 Reranker demotion

The gold is inside a rerank window and the listwise model ranks it low (examples:
Q122 model-demotion, Q119 hop-1-rerank demotion, Q121 final-window rank ~20). The one
attempted attack — compressing every document to signature+head so the model sees
structure instead of body (A4) — was CI-negative on recall on **both** sets (§6): the
listwise passes gate membership, so a global representation change trades one gold
population for another (11 lost vs 2 gained).

### 4.4 Vocabulary gap (rare — do not over-invest)

Only Q101 is a confirmed true vocabulary gap (query wording shares no tokens/semantics
with the gold). The curated query-expansion campaign proved the other suspected members
were *not* vocabulary gaps — their golds ranked 1–6 at hop-1 and died at the merged
cut (§4.1).

### 4.5 Solved classes (for closure — do not target)

- **Same-file dominance** in find-similar: solved by the `exclude_same_file` caller
  param (F-view 0.544 → 0.852).
- **Run-to-run non-determinism**: solved by pinning PYTHONHASHSEED=0. Root cause was
  Python set-iteration order changing pool composition — NOT GPU/cuBLAS numerics
  (fp32 made spread *worse*). Benchmarks are now bit-identical across rounds.

## 5. Levers shipped and working

| Lever | Mechanism | Evidence / reference |
|---|---|---|
| Hybrid RRF fusion 0.35/0.65 | BM25+dense reciprocal-rank fusion | benchmark-swept optimum; saturated (§6) |
| `hop1_reserved_slots=6` | protects top hop-1 seeds at the merged rerank window | ADR-0013; the only reserve that survived probing |
| F2LLM-v2-0.6B embedder | swap from Qwen3-0.6B | +0.026 MRR, recall flat (2026-07-26 A/B) |
| Path/symbol token augmentation + whole-identifier BM25 tokenizer | identifiers survive tokenization; path tokens searchable | INDEX_VERSION 4 (v0.22.0); stopword-removal counter-A/B confirmed keep-stopwords |
| Context enhancement at embed time | imports/class-signature prepended to chunk text before embedding | on by default; requires reindex to change |
| Module-summary chunks with query-time demotion | synthetic per-file chunks, demoted 0.82–0.90× | prevents displacement of real code |
| `exclude_same_file` on find_similar | caller-intent param | F-view MRR 0.544→0.852 (commit d468dcb) |
| find_similar default k=7 | aligned to config default | commit 730f67c |
| Containment-credit scorer | benchmark scorer credits merged-chunk containment | commit 5f9c7eb; prerequisite for any chunk-granularity A/B |
| Persistent chunk-embedding cache | reindex 33.9 s → 0.75 s (43×) | v0.22.0; enables cheap experimentation |
| Seed-0 determinism | PYTHONHASHSEED=0 auto-re-exec in harness | ADR-0021; bit-identical rounds |
| B1 `hide_ambiguous`, B4 `include_top_callers` | opt-in display-layer params (2026-08-14) | commits 63c1840, a20c805 — display only, no benchmark surface |

## 6. Levers measured and rejected — the never-re-propose catalog

Each entry: **failure mechanism** → *reopening condition*. Sources: campaign records in
`evaluation/` (§10).

### Fusion / weights

- **Fusion weight sweeps & rrf_k**: saturated — replicated sweeps found the current
  optimum; no setting rescues §4.2-class golds. → *Reopen only with a structurally
  different fusion (see §8.2), not re-sweeping.*
- **Intent-adaptive per-intent fusion weights** (ADR-0019, implemented then deleted):
  aggregates negative on both sets; replicated Q90 1.000→0.333 in 6/6 replay runs.
  Per-intent *static* profiles are the wrong granularity under a listwise-reranked
  funnel — the reranker re-sorts whatever the weights produce. → *Any weighting
  proposal must explain Q90 and operate per-query, not per-intent-class.*

### Pool assembly / reserves

- **Hop-1 `bm25_reserved_slots`** (fusion-stage reserve): injected fused-tail
  candidates do not survive multi-hop/ego/parent pool reshaping to the final pool;
  MRR −0.017/−0.034. → *Reserves must act at final pool assembly, not hop-1 — which
  led to the next two entries.*
- **Final-pool BM25 reserve (V1)**: 2026-08-02 read-only probe — rescued only
  bimodal flappers, zero stable misses. 2026-08-14 re-probe on the current substrate:
  3 miss-rescues but **0 under the no-final-pass stratum and 3 collateral evictions**.
  The earlier "reopen as recall@k campaign, V1-only" note is **superseded**. →
  *Re-probe before designing ANY reserve; the no-final-pass stratum is currently empty
  (final rerank runs on 133/133 queries), so every reserve must thread through the
  post-ego final call sites.*
- **A3 graph-channel final-pool reserve** (2026-08-14, NOT BUILT — probe gate failed):
  graph-hop candidates all carry score 0.0, so "top-3 by discovery order" is an
  evidence-free sample of a ~2.3-candidate/query channel; probe showed 2 rescues
  bought with in-window gold evictions on 5 queries, including making Q121 (closest
  ranking target) strictly worse. → *Reopening condition: an **in-channel ranking
  signal** — e.g. call-evidence scoring used only to ORDER the reserve source, never
  to compete in fusion — plus final-call-site threading.*

### Graph scoring / traversal

- **A1 call-evidence scoring for graph-hop candidates** (shipped disabled, λ=0.05
  arm): no primary CI excludes zero; the only near-significant signal is a 63q
  recall@20 *loss*. Mechanism: giving graph candidates real scores creates
  rerank-window competition that displaces hop-1 seeds — its genuine rescues (H034,
  H066 0→1.0) are paid for by displaced seeds. Do not hand-tune λ. → *Reopen only as
  evidence-without-competition: tie-break-only use, or scoring gated below the
  reserve line (this is exactly the A3 reopening condition above).*
- **A2 confidence-weighted graph traversal** (shipped disabled): **byte-identical**
  at every shipped-relevant setting. Structural: at max_depth=1, edge weight only
  orders a BFS priority queue whose full neighbor set is taken anyway; and the
  injection floor (`min_confidence=0.65`) plus AST-edge default-1.0 means no edge
  lives in (0, 0.65) for a traversal floor to filter. First floor that bites (0.8) is
  quality-neutral. → *Reopen only with multi-hop depth >1 traversal or an
  injection-floor redesign admitting sub-0.65 edges.*
- **PPR ego-graph (for recall)**: aggregates flat; the only clean causal effects are
  losses (Q51 0.5→0.333 in all replays, Q70→0.0). Kept as a **documented latency
  opt-in** (−15.8%, via smaller final pools — same mechanism as the debit). →
  *Latency campaigns only, recall debit priced in.*
- **centrality_alpha > 0** (PageRank blend into scores): recall degrades
  monotonically with alpha, replicated. Annotation stays; blend stays 0.
- **Multi-hop expansion_factor 0.25** (pool-slimming): pool_hit up but replicated
  losses (H034 1.0→0.2, H067 1.0→0.5) — hop-2 context was propping those golds.
  Stays 0.5. → *Config-level pool-flooding levers are exhausted; the fix must be
  smarter selection, not a smaller dial.*

### Reranker

- **A4 `doc_representation_mode=signature_head`** (shipped disabled; path|parent
  line plus docstring plus first 12 lines instead of full body): recall CI-negative on **both**
  sets (133q recall@10 −0.0789 [−0.1291, −0.0288]); pool trade 11 lost vs 2 gained;
  even the zero-upside 63q guard-rail set is harmed at recall@5. Only win: −19%
  latency, documented as a priced-in opt-in. In `FORBIDDEN_AUTO_TUNE_KEYS`. →
  *Global representation changes reshape membership through both listwise passes;
  any retry must be query- or candidate-conditional, not global.*
- **jina-reranker-v3.5 as default**: fails a pre-registered non-inferiority gate on
  all four train/val splits (e.g. 133q val ΔMRR −0.1200); ~43% faster but the gate is
  quality AND latency. Verdict independently re-verified from raw captures. The
  version-aware length-kwargs code stays (correctness fix).
- **Reranker dtype fp32/fp16**: flips were never precision — fp32's own round-spread
  was *worse* (0.0304 vs 0.0004 MRR); root cause was set-iteration pool composition,
  since solved by seed pinning. `listwise_dtype` knob ships as harmless "auto". →
  *Do not re-propose dtype changes for quality or determinism.*
- **Rerank window / doc-cap widening & `single_pass`**: window/cap widening rejected
  in sweeps; single_pass kills recall (latency knob only).

### Chunking / index granularity

- **Community-merge chunking**: REJECTED-for-now — the strict scorer could not match
  merged chunks. The containment-credit scorer has since landed, so the measurement
  blocker is gone, but the lever itself remains unmeasured-post-fix. → *Any
  chunk-granularity A/B is now possible; nobody has re-run this one.*
- **Sibling merge** (63/354 chunks): MRR flat (−0.008), recall@k +0.02–0.03, index
  −16% — an INDEX_VERSION bump was not justified by a neutral trade.

### Query side

- **Curated query expansion** (ADR-0012, feature-complete, ships disabled): its
  targets were NOT vocabulary gaps — golds ranked 1–6 at hop-1 and were demoted when
  the expanded pool hit 66–83 (§4.1). Re-evaluated once post-reserve: still flat,
  zero targets gained. → *Pool-flooding fix is the prerequisite. Only Q101 is a true
  vocab gap, and rescuing it needed a discount ≥0.75 that dilutes the dense leg.*
- **PRF / LLM query rewriting**: declined at ADR-0012 decision time in favor of the
  curated approach (determinism, latency, no-API constraints). → *Revisit is
  permitted, but inherits the same pool-flooding caveat AND the local-only
  constraint; a rewriting proposal must explain why its variants won't flood the
  merged pool the way curated variants did.*
- **BM25 stopword removal**: recall@5 −0.0349, MRR −0.0138. Keep stopwords.

### Other

- **LLM-generated hierarchical summaries** (ADR-0003): declined — cost/staleness/
  hallucination; module-summary chunks (deterministic aggregation) took the slot.
- **Intent policy tables** (edge-weight profiles, ego-threshold policy): measured
  bit-identical-inert; deleted (ADR-0031). The intent layer's entire measurable
  effect is its two redirects.
- **`get_file_tree` MCP tool**: rejected in the roadmap (agents already have tree
  tools; no retrieval effect).
- **DyCoder-style LLM-trajectory post-validation**: judged not transferable (requires
  an LLM in the retrieval loop; violates local-only constraint).

## 7. Deferred / spec'd-but-untried (known, unmeasured — not yours to re-derive)

- **Roadmap Track B display-layer levers** (token-efficiency, NOT recall): B2
  structure-preserving tree view, B3 signature+docstring enrichment of
  find_connections, B5 two-stage token budget. Out of scope for this brief's mission.
- **Community-merge re-measurement** now that the containment-credit scorer exists
  (see §6 chunking) — the one internal lever with a removed blocker and no
  post-blocker measurement.
- **EmbeddingGemma-300m**: formally dropped-undecided (registry keeps it; no verdict).
- **126 I-category candidate queries**: descoped with a written reopening condition
  (`evaluation/COMMIT_MINED_I_DESCOPE_20260802.md`) — benchmark-set expansion, not a
  lever.
- **Fresh merged-cut diagnosis** on the current substrate: the 2026-08-02 stable-miss
  taxonomy predates several substrate changes; any serious attack on §4.1 should
  start by re-grading the current misses (the harness + probe scripts exist).

## 8. Open opportunity map — literature directions per failure class

### 8.0 Already-mined literature (do not re-survey as if new)

The previous pass (2026-08-14 roadmap) already mined: **RepoScope** (arXiv
2507.14791) — produced B2/B4/B5 and the caller-utility finding behind
`include_top_callers`; **DyCoder** (arXiv 2608.01927) — produced A1/A2/A4 (all now
measured, §6) and one non-transferable idea; the **jina-reranker-v3.5 report** (arXiv
2607.18152) — measured, rejected. Earlier passes mined RepoGraph (ego-graph design),
GraphRAG/SOG/GRACE (SSCG design). Cite these only for contrast; their actionable
content is exhausted here.

### 8.1 Merged-cut / pool-flooding → candidate-selection & pool-assembly literature

The highest-value unsolved class. The system currently floods ~83 candidates into a
window-30 listwise cut with one blunt protection (6 reserved hop-1 slots). Directions:

- **Diversity/redundancy-aware selection** for the merged pool: MMR, DPP-based
  subset selection, facility-location submodular selection — anything that picks the
  window-30 by coverage rather than score order. Note graph/hop-2 candidates carry
  score 0.0, so the selector must handle unscored candidates (this killed naive
  reserves).
- **Calibrated/adaptive cut sizes**: score-distribution-aware windows (knee/elbow
  detection, score-gap truncation) instead of fixed 30 — the literature on dynamic
  cutoff prediction (e.g. choppy-style cutoff models) has never been tried here.
- **Listwise-context effects**: positional bias and set-composition sensitivity in
  LLM listwise rerankers — evidence on how pool composition (not just size) changes
  which items an LLM reranker promotes. This directly explains why flooding demotes
  hop-1 winners; mitigations (windowed tournament, sliding-window with overlap,
  setwise comparison) are unexplored here.
- **Two-stage retrieve-then-filter**: a cheap pointwise pre-filter (small
  cross-encoder or the embedder itself) to score the unscored expansion candidates
  *before* they enter the listwise window, so the window cut is evidence-based. This
  is the A3 reopening condition (§6) generalized beyond the graph channel.

### 8.2 RRF-arithmetic exclusion → score-fusion alternatives

- **Normalized-score fusion**: CombSUM/CombMNZ, z-score/min-max normalization,
  distribution-based normalization — RRF discards score magnitudes; a gold both legs
  consider "moderately relevant" (Q121: dense 84 / BM25 80) is arithmetically
  unreachable under reciprocal ranks but may not be under calibrated scores.
- **Learned fusion**: per-query learned leg weighting (query-performance prediction,
  pre/post-retrieval QPP signals). NB: distinct from the rejected per-INTENT static
  weights (§6) — per-QUERY learned weighting was never tried; a proposal must still
  explain Q90-style regressions.
- **Rank-fusion variants with evidence injection**: fusion that admits a third,
  sparse-evidence channel (call-graph, path match) as a tie-breaker rather than a
  competing leg (the A1 lesson: competition displaces; tie-breaking might not).

### 8.3 Reranker demotion → reranker adaptation

- **Repo-adapted reranker fine-tuning**: LoRA-style fine-tuning of the 0.6B listwise
  reranker on repo-mined (query, gold, hard-negative) triples — the benchmark's own
  miss records are a ready-made hard-negative source. Nothing has ever been trained
  on this corpus; all levers so far were inference-time.
- **Listwise vs setwise vs pairwise**: the code-reranking literature on comparison
  topology; setwise/tournament schemes may be less pool-composition-sensitive (§8.1)
  than single-window listwise.
- **Score calibration across passes**: the funnel reranks three times (hop-1, merged,
  final) with no cross-pass score consistency; literature on rank-consistency /
  cascade calibration is unexplored here.
- Constraint reminder: same-size-or-smaller model, bf16, ~4 s/query budget already
  reranker-dominated; and the v3.5 result (§6) shows newer-and-faster is not
  automatically better on code.

### 8.4 Membership misses → first-stage recall

- **Repo-adapted embedder fine-tuning**: contrastive fine-tuning of F2LLM-v2-0.6B on
  this repo (or code-domain) with hard negatives mined from the benchmark's own pool
  misses. As with §8.3, training is completely virgin territory here.
- **Late-interaction retrieval** (ColBERT-family, code-adapted variants): token-level
  matching could rescue §4.2/§4.4-class golds that single-vector dense and lexical
  BM25 both rank mediocrely. Cost: index size and a new leg in fusion (which §8.2
  must then handle).
- **Learned sparse retrieval** (SPLADE-family): a middle ground that might replace or
  augment the BM25 leg; interacts with the identifier-preserving tokenizer win (§5) —
  any replacement must keep whole-identifier matching.
- **Graph-based retrieval beyond call edges**: the call graph is the only graph
  signal used for expansion today; data-flow/type-flow/co-change (git history) edges
  as expansion channels are unexplored. Any such channel inherits the A3 lesson: it
  needs an in-channel ranking signal before it touches the pool.
- **Query-conditional retrieval routing**: predicting per-query which leg/channel to
  trust (QPP again) rather than fixed fusion — overlaps §8.2.

### 8.5 Cross-cutting / architectural

- **Agentic-iterative retrieval**: multi-turn query reformulation using result
  feedback, *executed by the calling agent* (the MCP client) rather than inside the
  pipeline — sidesteps the no-API-in-loop constraint because the caller is already an
  LLM. Literature on search-agent scaffolds and retrieval feedback loops applies; the
  system's own `include_top_callers`/`find_connections` tools are hooks for it.
- **Chunk representation research** (cAST-style structural chunking, context-enriched
  headers): partially implemented (context enhancement, §5); the unexplored half is
  *query-side* structure awareness and representation A/Bs now that the
  embedding-cache makes reindex cheap (0.75 s).
- **Test-time compute for retrieval**: sampling/self-consistency over reranker
  passes, or deeper rerank on low-confidence queries only (confidence = score-gap
  signals). Latency budget exists on easy queries; nothing adaptive is implemented.

### 8.6 Transferability constraints (apply to every direction)

Single RTX 4090 (24 GB) shared by embedder+reranker; no API-LLM inside the retrieval
pipeline; deterministic under PYTHONHASHSEED=0 (any stochastic component must be
seedable); INDEX_VERSION bumps force full user reindexes (real cost — sibling merge
died partly on this); Python/tree-sitter stack; benchmark = this repo's own codebase
(results on 2,400-chunk scale, not monorepo scale).

## 9. Methodology constraints any proposal must satisfy

Durable rules distilled from ~15 campaigns (violating these has produced every false
positive this project has caught):

1. **Substrate re-baseline**: re-pin baselines after ANY search-path commit — the repo
   indexes itself, so code edits drift the corpus. Never compare across substrates.
2. **Probe before build**: pool-membership interventions get a read-only ceiling probe
   (membership arithmetic on captured pools) with a zero-collateral gate BEFORE
   implementation. Two reserve designs died correctly at this gate.
3. **Re-derive miss profiles before targeting**: the hard-miss set changes with
   substrate (H034/H066 exited it without intervention).
4. **Paired-CI adoption gate**: pre-registered, paired 95% CI on recall@10/20
   excluding zero (133q upside), MRR guard-rail both sets. Point deltas are not
   evidence.
5. **Gate on aggregates only**: under seed-0, per-query values are realization
   properties; individual query moves are texture, not gates.
6. **Control-arm attribution**: queries moving identically in control+treatment are
   drift, not effect.
7. **Ship default-off / byte-identical**: every mechanism lands behind a default that
   is unit-tested byte-identical; defaults flip only on a gate pass.
8. **63q = guard-rail, 133q = upside**: a lever that "wins" only on 63q is suspect
   (nothing there to win); a lever that hurts 63q is rejected regardless of 133q.

## 10. Source-document index (in-repo ground truth)

Campaign dispositions (`evaluation/`): `RECALL_CAMPAIGN_CLOSEOUT_20260802.md` (master
arm table + methodology rules), `STABLE_MISS_DIAGNOSIS_20260802.md` (miss taxonomy +
funnel measurement), `TRACK_A_AB_20260814.md` (A1/A2), `REMAINING_LEVERS_AB_20260814.md`
(A4/B1/B4 + current canons), `GRAPH_RESERVE_PROBE_20260814.md` (A3 + reserve reopening
condition), `JINA_V35_AB_20260814.md`, `FINAL_POOL_RESERVE_PROBE_20260802.md`,
`COMMIT_MINED_I_DESCOPE_20260802.md`. ~46 evaluation records exist in total; the above
are load-bearing.

ADRs (`docs/adr/`): retrieval-relevant = 0001 (FAISS), 0003 (declined LLM summaries),
0010–0015 (centrality memo, reranker doc cap, query expansion, hop-1 reserve, config
overrides, community-subsystem removal), 0019 (intent-weight rejection), 0021
(determinism), 0027–0031 (graph output, intent gating), 0035–0036 (C++ call-edge
scope, include_dirs semantics).

Code ground truth: `search/config.py` (every live knob + `FORBIDDEN_AUTO_TUNE_KEYS` in
`search/index_probe.py`), `search_overrides.json` layer (ADR-0014).

Harness: `scripts/benchmark/run_sscg_benchmark.py` (deterministic runner),
`scripts/benchmark/probe_final_pool_reserve.py` (pool-membership probe with
provenance + `had_final_pass` stratification), `benchmark_results/remaining_levers/analyze_ab.py`
(paired-CI analysis), golden datasets under `evaluation/`.

Prior roadmap: `docs/plans/RAG_IMPROVEMENT_ROADMAP_20260814.md` (untracked, local).
