# Chunking Corpus Analysis — claude-context-local (2026-07-28)

**Scope**: Analysis + report only. No config or pipeline changes were made.
**Corpus**: This repository, filtered to the live index's exclusion set (204 files: 203 Python, 1 JavaScript).
**Method**: `scripts/benchmark/analyze_chunking_corpus.py` — reuses the production chunking pipeline
(`MultiLanguageChunker` + `RepoProfile` adaptive sizing), the production merge function
(`_greedy_merge_small_chunks`), the production community-graph preprocessing, and the real
F2LLM-v2-0.6B tokenizer. Raw numbers: `evaluation/chunking_corpus_stats.json`.
**Reference**: `_archive/IMPROVEMENTS/JULY_IMPROVEMENTS/Adaptive_chncking_strategies.md` (adaptive
chunking research; key claim: pure function-level chunking is the worst-performing strategy,
−3.57 to −5.64 pp, never Pareto-optimal).

---

## 1. Executive summary

1. **The live config runs the merge-free regime the research doc warns about.**
   `enable_community_merge: false` gates the *only* production merge call site, so
   `min_chunk_tokens`, `max_merged_tokens`, `size_method`, and `token_estimation` are inert.
   Result: **788 of 2,101 produced chunks (37.5%) are under 150 real tokens; 257 (12.2%) are
   under 50** — dominated by small methods (381), functions (155), and module preambles (112).
2. **The whitespace token estimator under-counts F2LLM tokens by 2.37×** (measured over 1,551
   Python functions). Every "token" budget in the chunking config is therefore ~2.4× larger in
   real tokens than its name implies: the live `max_merged_tokens: 1000` is a ~2,370-real-token
   budget; the code default `400` is ~950 real tokens — coincidentally close to the
   statistics-derived optimum of ~840.
3. **This study found — and got fixed — a control-flow defect that made `max_merged_tokens`
   unreachable in community mode.** Pre-fix, community merge collapsed entire same-file
   community runs unboundedly (max merged chunk 15,859 real tokens; chunks >2,048 real grew
   47 → 78). The fix landed same-day as commit `cedcc87` with regression tests (§6.1).
   **Post-fix (measured)**: budgets bind, the tail is identical to the no-merge baseline in
   every variant (47 chunks >2,048 real, max 14,818), and community merge with calibrated
   budgets cuts sub-150-real-token chunks from 37.5% → 30.0% **config-only**. The sibling
   merge remains distributionally strongest (→ 20.0%) but has no config gate — activating it
   is a code change.
4. **Validated as-is**: `community_resolution: 1.5` (on the ARI-stability plateau of a
   7γ × 5-seed Louvain sweep; §7), `max_chunk_lines: 100` (derived value 97), duplication
   handling (3.5% ratio, zero near-duplicate file pairs — no dedup machinery needed).

All recommendations are Stage-1 (statistics-derived). Stage-2 validation via the SSCG golden-set
benchmark is required before adopting any of them, and any chunking change triggers a full
non-incremental reindex (`INDEX_VERSION` bump).

---

## 2. As-built pipeline (verified against code)

1. **Split**: `LanguageChunker.chunk_parsed()` (`chunking/languages/base.py`) traverses the AST;
   nodes exceeding `max_chunk_lines` (100) **and** of type
   `function_definition`/`decorated_definition` are split at AST block boundaries by
   `_split_large_node()`, accumulating body children up to a non-whitespace-character threshold.
2. **Adaptive sizing**: `sizing_mode: "adaptive"` modulates that threshold per function via
   `compute_adaptive_threshold(CC, P75)` (`base.py:24-61`) using `RepoProfile.p75_chars`.
   Live profile: P75 = 1,180 nw-chars → thresholds range 590–1,534 nw-chars
   (≈ 185–481 real tokens) as complexity rises. `max_split_chars: 3000` is the fallback used
   only when no repo profile exists.
3. **Merge (dormant)**: `_greedy_merge_small_chunks()` (`base.py:674`) has exactly one
   production call site — `remerge_chunks_with_communities()`
   (`chunking/community_remerge.py:330`), invoked from `CommunityStage.run()` Step B behind
   `enable_community_merge`, which is **false** live (code default: true). The live index
   contains zero `merged` chunks.
4. **Community detection**: Louvain (`graph/community_detector.py:172`), hardcoded `seed=42`,
   phantom-collapse preprocessing (`max_phantom_degree: 20`), `community_resolution: 1.5`.
   Community + file summaries are appended post-detection.

### Live config vs code defaults (parameters under study)

| Parameter | Live | Code default | Status live |
|---|---|---|---|
| `enable_community_merge` | **false** | true | Gates the only merge path — dormant |
| `max_merged_tokens` | 1000 | 400 | Inert (merge dormant) |
| `min_chunk_tokens` | 50 | 50 | Inert (merge dormant) |
| `max_split_chars` | 3000 | 1600 | Fallback only (adaptive profile active) |
| `community_resolution` | 1.5 | 1.0 | Active |
| `sizing_mode` | adaptive | fixed | Active |
| `max_chunk_lines` | 100 | 100 | Active |
| `token_estimation` | whitespace | whitespace | Inert (merge dormant) |

---

## 3. Measured corpus statistics

### 3.1 Function/method sizes (Python, n = 1,551; top-level functions + methods, no nested double-count)

| Metric | p10 | p25 | p50 | p75 | p90 | max |
|---|---|---|---|---|---|---|
| Lines | 4 | 11 | 23 | 43 | **78** | 701 |
| nw-chars | 155 | 294 | 625 | 1,182 | **2,157** | 18,689 |
| ws-tokens | 18 | 40 | 82 | 161 | 287 | 2,271 |
| **Real (F2LLM) tokens** | **43** | 91.5 | **197** | 374 | **700** | 6,010 |
| Cyclomatic complexity | 1 | 1 | 3 | 6 | 11 | 117 |

Dispersion p90/p50 (real tokens) = **3.55**. JavaScript (n = 6) is too small to report; the
corpus is effectively single-language.

### 3.2 Classes (n = 131) and files (n = 204)

| Metric | p10 | p25 | p50 | p75 | p90 | max |
|---|---|---|---|---|---|---|
| Class real tokens | 139 | 400 | **1,358** | 2,625 | **5,168** | **14,818** |
| Class lines | 15 | 55 | 174 | 319 | 652 | 1,578 |
| File lines | 40 | 108 | 232 | 408 | 859 | 2,438 |

The split gate covers only `function_definition`/`decorated_definition` — **classes never
split**. A p90 class chunk (5,168 real tokens) far exceeds any embedding budget; the embedder's
`create_embedding_content()` (`embeddings/embedder.py:1020`) truncates content at 6,000 raw
chars (head + tail), so large class and module-preamble chunks are embedded from truncated text.

### 3.3 Comment/docstring density and duplication

- Python: comments = 14.8% of nw-chars, docstrings = 24.9% → ~40% of embedded content is
  natural-language prose. Contextual headers are *not* redundant with this — docstrings cover
  the chunk itself, headers cover imports/class context.
- Duplication (k = 8 ws-token shingles): ratio **3.5%**, zero file pairs with Jaccard ≥ 0.5.
  **No deduplication machinery is warranted for this corpus.**

---

## 4. Token-estimation calibration (measured, not assumed)

| Language | real tokens / ws-token | nw-chars / real token | n |
|---|---|---|---|
| Python | **2.369** | 3.187 | 1,551 |
| JavaScript | 2.214 | 2.96 | 6 |

Consequences for every "token"-denominated chunking parameter:

| Config value (ws) | Real F2LLM tokens |
|---|---|
| `min_chunk_tokens: 50` | ≈ 118 |
| `max_merged_tokens: 400` (default) | ≈ 950 |
| `max_merged_tokens: 1000` (live) | ≈ 2,370 |

The research doc's cAST nw-char band (2,000–2,500 nw-chars) maps to ≈ 630–785 real tokens at the
measured 3.187 nw-chars/token — consistent with the 0.6B-embedder sweet spot.

---

## 5. Produced-chunk audit (live config, merge-free)

Total produced content chunks: **2,101**. Distribution (real tokens): p10 = 42, p50 = 217,
p90 = 704, max = 14,818.

| Band | Count | Share |
|---|---|---|
| < 50 real tokens | 257 | 12.2% |
| **< 150 real tokens** | **788** | **37.5%** |
| > 800 real tokens | 163 | 7.8% |
| > 2,048 real tokens | 47 | 2.2% |

By chunk type: method 821 (381 under 150), function 463 (155), split_block 267 (20),
module_preamble 227 (112), decorated_definition 184 (97), class 131 (15 under 150 — but
p50 = 1,358, the *oversize* problem lives here), module 6, function_expression 2.

This is the pure function/method-chunking regime the research doc identifies as the worst
strategy. Over a third of the index consists of fragments below the ~150-token floor where
retrieval quality measurably degrades.

**Reconciliation with the live index** (230 files / 2,279 chunks, built 2026-07-26): our 2,101
content chunks + ~186 file-summary chunks + ~27 community summaries ≈ 2,314, vs 2,279 live —
within working-tree drift since the index was built (the 204-vs-230 file delta is the same
drift; the analysis script itself is part of the corpus it measures).

---

## 6. Merge simulations (production merge function, five variants)

All variants run the real `_greedy_merge_small_chunks` on the 2,101 produced chunks; community
variants use the live stored community map via the production `assign_community_ids` helper.
Numbers below are **post-fix** (commit `cedcc87`, see §6.1 — the pre-fix community numbers are
retained there as the evidence that found the bug).

| Variant | Boundary | min/max (ws) | Chunks | Merged | <150 real | <50 real | >800 real | >2,048 real | max real |
|---|---|---|---|---|---|---|---|---|---|
| Baseline (live, no merge) | — | — | 2,101 | 0 | 788 (37.5%) | 257 | 163 | 47 | 14,818 |
| A: community, live params | community | 50/1000 | 1,995 | 74 | 655 (32.8%) | 205 | 163 | 47 | 14,818 |
| B: sibling, live params | parent_class | 50/1000 | 1,856 | 143 | 481 (25.9%) | 91 | 163 | 47 | 14,818 |
| C: sibling, code defaults | parent_class | 50/400 | 1,850 | 147 | 476 (25.7%) | 88 | 164 | 47 | 14,818 |
| **D: community, calibrated** | community | **63/354** | **1,931** | **113** | **580 (30.0%)** | 202 | 163 | **47** | 14,818 |
| E: sibling, calibrated | parent_class | 63/354 | 1,733 | 192 | 347 (20.0%) | 75 | 166 | 47 | 14,818 |

Calibrated params (D/E): min 63 ws ≈ 150 real tokens, max 354 ws ≈ 840 real tokens
(= clamp(p90_func_real × 1.2, 400, 1000), §7).

Post-fix, every variant leaves the oversize tail untouched (47 chunks >2,048 real, max 14,818 —
all pre-existing class/preamble chunks, not merge products). **Variant D is the only
config-activatable option** (`enable_community_merge` reaches only the community path) and is
the Stage-2 A/B treatment arm. Variant E reshapes the distribution furthest but requires a new
config gate in code (follow-up, out of scope).

### 6.1 Finding (fixed): `max_merged_tokens` was unreachable in community mode

**Found by this study, fixed same day** — commit `cedcc87` ("fix: unreachable
budget/passthrough checks in community-mode greedy merge"), with three new regression tests in
`tests/unit/test_community_merge.py` (13/13 pass).

Pre-fix evidence: variant D was **byte-identical** to variant A despite a 2.8× smaller budget
(both: 1,368 chunks, 454 under 150 real, 78 over 2,048 real, max 15,859). Root cause: the
community-boundary check was an `elif` arm matching whenever `use_community_boundary and
current_group` — *including when the community was unchanged* — so the budget check (Case 2)
and large-chunk passthrough (Case 3) never executed while a group was open. Once any small
chunk started a group, every subsequent same-file, same-community chunk merged into it
regardless of size.

Post-fix (`chunking/languages/base.py:756-796`): `boundary_changed` is computed once per chunk
(community or parent-class, per mode) and gates a single `elif`, restoring Cases 2/3. Measured
effect (§6 table): A and D now differ, budgets bind (D max merged size respects 354 ws ≈ 840
real), and the community-mode tail matches the sibling baseline exactly. Community-merge
activation is no longer blocked.

### 6.2 Why residual small chunks remain

Merging only coalesces *file-adjacent* chunks sharing a boundary key. Sibling mode
(`parent_class`) leaves 347: small module-level functions with no adjacent small sibling,
singleton methods, and small module preambles have no merge partner. Community mode leaves more
(580) because it is *stricter*: partners must be file-adjacent **and** in the same call-graph
community, and Louvain communities frequently cut across file adjacency (plus 67 of 2,101
chunks match no stored community at all). Reaching further would require file-level grouping or
preamble-into-first-symbol merging (design changes).

---

## 7. Call graph, γ-sweep, community budgets

**Graph** (live stored graph, production phantom-collapse preprocessing): 5,338 nodes
(2,075 chunk + 3,263 phantom), 22,684 edges; collapsed: 2,075 nodes / 16,305 edges,
density 0.0076, avg clustering 0.414, 202 connected components; 91 phantoms skipped at
degree > 20. (The stored graph drifted slightly between the two analysis runs — incremental
index updates during the working session; distributions are structurally unchanged.)

**Louvain γ-sweep** (7 γ × 5 seeds, pair-counting ARI stability on the collapsed graph):

| γ | mean Q | mean communities | mean pairwise ARI |
|---|---|---|---|
| 0.5 | 0.629 | 208 | 0.571 |
| 0.75 | 0.589 | 213 | 0.592 |
| 1.0 | 0.567 | 216 | 0.661 |
| 1.25 | 0.549 | 219 | 0.662 |
| **1.5** | 0.533 | 222 | 0.677 |
| 1.75 | 0.518 | 225 | **0.694** |
| 2.0 | 0.505 | 227 | 0.643 |

Modularity Q declines monotonically with γ (expected); partition stability sits on a
**plateau at γ = 1.0–1.75** (ARI 0.66–0.69) with a run-dependent peak: the pre-fix sweep peaked
at 1.5 (ARI 0.660), this refresh at 1.75 (0.694), with 1.5 moving 0.660 → 0.677 between runs
on a near-identical graph — i.e. run-to-run ARI noise is ~±0.02 and the 1.5-vs-1.75 gap is
within it. **The live γ = 1.5 stays validated**; switching to 1.75 is not supported by this
data. (Stored map has 365 communities vs ~222 in the sweep: the stored map accumulates across
incremental updates; the sweep is a fresh detection on today's graph.)

**Community token budgets** (2,034 of 2,101 chunks matched to the stored map; 324 communities):
real-token sums p50 = 127, p90 = 1,042, max = 78,309; 290/324 communities fit within 1,000 real
tokens, 238/324 within 400. Most communities are merge-safe, and post-`cedcc87` the oversized
tail communities are harmless to the merge: the budget check binds per merged group (354 ws),
so a 78k-token community can never yield a runaway merged chunk (§6 confirms zero tail
inflation — chunks >2,048 real stay at exactly the baseline 47 in every post-fix variant).

---

## 8. Config audit — parameter by parameter

| Parameter | Live | Derived from measurements | Rationale | Confidence |
|---|---|---|---|---|
| `enable_community_merge` | false | **A/B-test true with calibrated budgets** (variant D) — safely activatable config-only post-`cedcc87` | §6 post-fix: sub-150 chunks 37.5% → 30.0%, zero tail inflation; retrieval impact unknown until Stage-2 | High for safety; MRR impact needs Stage-2 benchmark |
| Merge activation (strongest reshaper) | none | **Sibling merge, min 63 / max 354 ws** (≈ 150/840 real) — requires a new config gate (code change, follow-up) | Variant E: sub-150 chunks 37.5% → 20.0%, sub-50 257 → 75, tail unchanged | High for direction; blocked on plumbing + Stage-2 |
| `min_chunk_tokens` | 50 | **63** (ws) | 150-real-token floor ÷ 2.369 calibration | Medium-high |
| `max_merged_tokens` | 1000 | **354** (ws) | clamp(p90_func_real 700 × 1.2, 400, 1000) = 840 real ÷ 2.369 | Medium-high |
| `token_estimation` | whitespace | Keep, but document the 2.37× factor; or add a calibrated multiplier | Real-tokenizer counting at index time is costly; calibration is stable per language | High |
| `max_chunk_lines` | 100 | **97** (= p90 lines 78 × 1.25) | Live value effectively optimal | High — keep 100 |
| `max_split_chars` | 3000 | 2,000–2,500 nw-chars (fallback only) | p90 function = 2,157 nw-chars; cAST optimum band; live 3000 only matters when no repo profile exists | Low priority (rarely active) |
| `sizing_mode` / multipliers | adaptive, 1.3/0.5 | Keep; dispersion p90/p50 = 3.55 justifies adaptive over fixed | Live thresholds 590–1,534 nw-chars bracket the p75 sensibly | Medium |
| `community_resolution` | 1.5 | **1.5** — validated | On the γ-sweep ARI-stability plateau (1.0–1.75, ARI 0.66–0.69); 1.5-vs-1.75 gap within run-to-run noise | High |
| `max_phantom_degree` | 20 | Keep | Only 90 phantoms exceed it; collapse behaves as designed | Medium (not swept) |
| Class chunking | never split | Consider class-level splitting or summary-aware handling | 131 class chunks, p50 = 1,358 real tokens, max 14,818 — embedded truncated at ~6,000 chars | Medium (design change, out of scope) |
| Dedup machinery | none | **None needed** | 3.5% duplication, zero near-dup pairs | High |

**Parameters that must stay golden-set-tuned (not statistics-derived)**: `rrf_k_parameter`,
`bm25_weight`/`dense_weight`, `default_k`, `top_k_candidates`, `centrality_alpha` — these were
tuned on the 77-query SSCG benchmark and prior memory records their sweeps as saturated.

---

## 9. GLSL

Not measurable on this corpus — it contains no GLSL files. A shader-corpus run would need:
a representative TouchDesigner/GLSL project indexed with the same pipeline, the same
calibration pass (GLSL tokenizes differently — dense operators, few comments), and attention to
the split gate (GLSL's tree-sitter grammar uses `function_definition`, so splitting *does*
apply, unlike JS/TS/Go/Rust/C#).

---

## 10. Recommended next steps

1. ~~Fix the community-merge `elif` ordering so `max_merged_tokens` binds in community mode~~
   — **done**: commit `cedcc87` (`base.py:756-796`) + 3 regression tests; §6 numbers refreshed
   against the fixed code.
2. **Stage-2 validation (in progress)**: SSCG 77-query golden-set A/B — merge-off baseline vs
   community merge with calibrated budgets (variant D: `enable_community_merge: true`,
   `min_chunk_tokens: 63`, `max_merged_tokens: 354`), config-only, full non-incremental
   reindex per arm, live config restored afterward. Adoption gate: ±0.02 MRR noise band;
   secondary metrics recall@4/@20, pool_hit_rate. Report:
   `evaluation/CHUNKING_MERGE_AB_20260728.md`.
3. **Sibling-merge config gate** (variant E, the strongest distributional reshaper): add
   plumbing to select the parent-class boundary from config, then A/B against variant D.
   Code change — deferred until the variant-D A/B establishes whether merging moves retrieval
   at all.
4. **Class-chunk handling**: measure retrieval quality on queries targeting large classes
   (currently embedded from truncated text) before designing class-level splitting.
5. Any adopted change requires an `INDEX_VERSION` bump + full non-incremental reindex.

---

## Caveats

- The split gate (`function_definition`/`decorated_definition`) covers Python and C-family
  grammars only; JS/TS/Go/Rust/C# functions never split. Irrelevant for this ~99%-Python
  corpus; relevant for multi-language deployments.
- The analysis script lives in `scripts/benchmark/` and is therefore part of the corpus it
  measures; editing it between runs shifts totals by ±1 chunk.
- Corpus (204 files) vs live index (230 files) reflects working-tree drift since the
  2026-07-26 index build plus minor filter-semantics differences; chunk-type distributions
  reconcile structurally (§5).
- Merge simulations operate on today's produced chunks with the *stored* community map;
  a fresh detection would shift community assignments slightly (seed-sensitivity: ARI 0.66).
- The analysis ran twice (pre- and post-`cedcc87`). Chunk production is byte-stable between
  runs (identical 2,101-chunk distributions); the stored graph/community sections drifted
  slightly (incremental index updates during the session) and §7 reports the refreshed run.
  Comparing the two γ-sweeps bounds run-to-run ARI noise at ~±0.02.
- All real-token counts use the F2LLM-v2-0.6B tokenizer (the live embedding model);
  reranker (jina-reranker-v3) tokenization differs and was not measured.
