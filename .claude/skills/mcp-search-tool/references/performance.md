# Search Performance & Benchmark Reference

## Latest Validation (2026-07-26/27, post-Q2-sweep, `top_k_candidates=30`, F2LLM-v2-0.6B + jina-reranker-v3, RTX 4090 24GB)

Current-config benchmark headline, run **after** the Q2 sweep retuned `RerankerConfig.top_k_candidates` (`search/config.py:281`) from 50 to **30**
(quality-neutral within ±0.025, 32% faster). These runs used this machine's locally deployed models (`codefuse-ai/F2LLM-v2-0.6B` embedder +
`jinaai/jina-reranker-v3` reranker per `search_config.json`) — not the shipped code defaults (`BAAI/bge-m3` +
`Alibaba-NLP/gte-reranker-modernbert-base`); treat these numbers as validation of the *tuning*, not a claim about out-of-the-box behavior on a fresh
install.

**63-query SSCG set** (`sscg_f2llm_original_r1/r2_20260726.json`, `sscg_search_latency_verify_20260727.json`):

| Run | MRR | Recall@7 | Recall@20 | Hit@5 | Pool hit rate | Avg pool | Latency |
|-----|-----|----------|-----------|-------|---------------|----------|---------|
| original r1 | 0.7873 | 0.7244 | 0.8009 | **1.000** | 1.000 | 26.6 | 1394ms |
| original r2 | 0.7946 | 0.7336 | 0.8048 | **0.9841** (62/63) | 1.000 | 26.6 | 1397ms |
| latency-verify | 0.7955 | 0.7189 | 0.8083 | **1.000** | 1.000 | 26.7 | 967ms |

**One of these three runs does not hit Hit@5=1.000** — treat "Hit@5=100%" as typical, not guaranteed, on this 63-query set. Pool hit rate is a clean
1.000 across all three (every gold chunk still reaches the smaller 30-candidate pool).

**96-query expanded set** (`sscg_f2llm_expanded_r1/r2_20260726.json`) is a harder, broader query mix — MRR drops to 0.6486–0.6656 and pool hit rate is
**not** a uniform 1.000: r1 = 0.9688, r2 = 0.9792. On this set, ~2–3% of gold chunks miss the rerank pool entirely (a genuine retrieval miss, not just
an ordering miss) — the "gold chunk always reaches the pool" claim below is scoped to the 63-query set, not this one.

---

## Archived: Pre-Sweep Validation (2026-07-25, hybrid k=7, 63-query SSCG, jina-reranker-v3, RTX 4090 24GB)

> Superseded by the 2026-07-26/27 post-sweep runs above. Kept for the funnel-widening finding, which
> the sweep confirmed still holds at the smaller pool size.

Post-funnel-widening run (commit `803831d`) with `jinaai/jina-reranker-v3` (listwise, 50-candidate pool at the time) on the 24GB workstation. Two
replicate runs shown — the spread between them is the benchmark's run-to-run noise, not a config difference.

| Run | MRR | Recall@5 | Recall@7 | Recall@10 | Recall@20 | Hit@5 | NDCG@5 | Pool hit | Avg pool | Lat |
|-----|-----|----------|----------|-----------|-----------|-------|--------|----------|----------|-----|
| Pre-funnel baseline | 0.773 | 0.618 | 0.697 | 0.734 | 0.758 | 0.968 | 0.638 | 1.000 | 27.4 | 1086ms |
| **Widened funnel (rep 1)** | 0.776 | 0.653 | **0.723** | 0.770 | 0.780 | **1.000** | 0.657 | 1.000 | 27.5 | 1798ms |
| **Widened funnel (rep 2)** | 0.765 | **0.674** | 0.713 | **0.781** | **0.805** | **1.000** | 0.665 | 1.000 | 27.6 | 1730ms |

**What changed (commit `803831d`):**

- **Widened retrieval funnel** (`search/search_executor.py`): hybrid per-leg retrieval raised from
`k*2` to `max(reranker.top_k_candidates, k*5)`; the fused pool now fills the listwise reranker's 50-candidate budget (previously ~14 candidates at
k=7), truncated to `k` after reranking.
- **Configurable graph cap** (`search/graph_scoring_stage.py`): post-centrality result cap changed
from hardcoded `k*4` to `k × graph_enhanced.max_results_multiplier` (default 8).

**New metrics (in `evaluation/metrics.py` + `scripts/benchmark/run_sscg_benchmark.py`):** `recall@20` / `recall@50`, plus **pool_hit_rate** (was any
gold chunk present in the pre-rerank candidate pool?) and **avg_pool_size**. Pool-hit splits every miss into *retrieval miss* (gold never entered the
pool) vs *ranking miss* (gold was in the pool but ordered below the cutoff).

**Key findings:**

- **pool_hit_rate = 1.000** — every gold chunk reaches the rerank pool. All remaining misses are
*ranking* misses; further recall work should target reranking/fusion ordering quality, not funnel width.
- **Run-to-run noise ≈ ±0.01–0.025** on MRR/R@7 (GPU fp16 listwise reranker nondeterminism).
Single-run deltas below ~0.03 are not significant.
- **Never benchmark deep recall by raising `--k`.** At `--k 50` the pipeline collapses
(MRR 0.175, Hit@5 0.365) because multi-hop/ego expansion pools scale with k. Measure headroom via pool instrumentation at production k=7.
- **Tested and rejected** (no gate win, within noise): multi-hop `expansion_k` floor `max(5,…)`,
ego `min_similarity_threshold` 0.15→0.05, ego `expansion_mode` "bfs"→"ppr".
- **Latency cost:** ~1.1s → ~1.7–1.8s/query (reranking 50 candidates instead of ~14).

---

## Archived: Validation (2026-06-26, hybrid k=7, 63-query SSCG, gte-reranker, 8GB laptop)

> Superseded by the 2026-07-25 run above (different hardware + reranker + widened funnel).

Expanded benchmark: 63 queries (A–F coverage, from `scripts/benchmark/run_sscg_benchmark.py`). Active reranker:
`Alibaba-NLP/gte-reranker-modernbert-base` (validated best-available on laptop; Phase C experiment: bge-reranker-v2-m3 was worse, jina-reranker-v3 OOM
on 8GB GPU — see Phase C note below).

| MRR | Recall@5 | Recall@7 | Recall@10 | Hit@5 | NDCG@5 | Line Recall | Line Precision | Line IoU | Lat |
|-----|----------|----------|-----------|-------|--------|-------------|----------------|----------|-----|
| **0.700** | **0.625** | **0.696** | **0.734** | **0.984** (62/63) | **0.625** | 0.947 | 0.203 | 0.233 | 617ms |

All thresholds pass: MRR ≥ 0.50 ✓ | Recall@5 ≥ 0.55 ✓ | Hit@5 ≥ 0.80 ✓. Recommended operating point: **k=7**.

Note: the 2026-06-08 13-query baseline (MRR 0.797) used a smaller query set; numbers not directly comparable to this 63-query run.

## DSPy Agent Eval (2026-06-26, 77-query dataset, 4-tool, 18 test queries)

Full 4-tool harness (search_code, find_connections, find_path, find_similar_code) against the 18-query held-out test split (A–F coverage). Prior
baselines used 2 tools — those were an eval artifact; this is the corrected reference.

| Recall@7 | Traj Recall | MRR | NDCG@5 | Hit@7 | Tool Sel Acc |
|----------|-------------|-----|--------|-------|--------------|
| **0.9046** | 0.9537 | **0.8519** | **0.8116** | **1.000** | **1.000** |

Gap traj→final: +0.049 (chunks seen-but-dropped by agent, down from +0.167 with 2-tool harness).

## Phase C Reranker Experiment (2026-06-26) — NULL RESULT (8GB laptop)

> **Update (2026-07-25):** `jinaai/jina-reranker-v3` is now deployed and benchmark-validated on
> the 24GB RTX 4090 workstation — see "Latest Validation" above. The OOM conclusion below was
> specific to the 8GB laptop GPU. `gte-reranker-modernbert-base` remains the recommendation for
> ≤8GB hardware.

Tested two stronger rerankers against R0 gte baseline (SSCG R@7 0.696 / MRR 0.700):

- **`jinaai/jina-reranker-v3`** — OOM on 8GB laptop GPU. Listwise single-pass (131K context), fires 3×/query
(Hop-1 + multi-hop merge + post-ego-graph), `batch_size` silently dropped by factory, no fp16, idle ~5.7GB. Structurally incompatible with this
hardware. Do not attempt without code changes (fp16, CPU device override, single-pass gating).
- **`BAAI/bge-reranker-v2-m3`** — loaded fine (~1.1GB batched cross-encoder) but **scored worse**: SSCG
MRR 0.602 (−0.098), R@7 0.621 (−0.075), Hit@5 0.952 (−0.032). 5× slower (3301ms vs 617ms). bge-v2-m3 is a general-purpose model;
gte-reranker-modernbert-base is better tuned for this code corpus.

**Conclusion:** `Alibaba-NLP/gte-reranker-modernbert-base` is validated as the best available reranker on this laptop for this corpus. The active
config is already optimal among tested alternatives.

---

## Archived: SSCG 13-Query Baseline (2026-06-08, hybrid k=10)

---

| MRR | Recall@5 | Recall@7 | Recall@10 | Hit@5 | NDCG@5 | Line Recall | Line Precision | Line IoU |
|-----|----------|----------|-----------|-------|--------|-------------|----------------|----------|
| **0.797** | **0.689** | **0.736** | **0.770** | **1.00** (13/13) | **0.717** | 0.852 | 0.267 | 0.304 |

All thresholds pass: MRR ≥ 0.50 ✓ | Recall@5 ≥ 0.55 ✓ | Hit@5 ≥ 0.80 ✓. Recommended operating point: **k=7** (`golden_dataset.recommended_k=7`).

---

## SSCG Benchmark (2026-06-08, three-mode comparison)

Mode-comparison baseline. Evaluated against 13 queries across 4 categories with neural reranker active. The cross-encoder reranker dominates final
ranking — all three modes reach the same MRR (0.797).

**Thresholds:** MRR ≥ 0.50 | Recall@5 ≥ 0.55 | Hit@5 ≥ 0.80

| Mode | MRR | Recall@5 | Recall@7 | Recall@10 | Hit@5 | NDCG@5 | Best for |
|------|-----|----------|----------|-----------|-------|--------|----------|
| **Hybrid** (default) | 0.797 | **0.689** | **0.736** | 0.770 | 13/13 (100%) | **0.717** | Deep recall, balanced |
| **BM25** | 0.797 | **0.689** | 0.723 | **0.777** | 13/13 (100%) | **0.717** | Exact symbol lookup |
| **Semantic** | 0.797 | 0.676 | 0.723 | 0.758 | 13/13 (100%) | 0.705 | Concept/intent queries |

**Key findings:**

- **Reranker-dominated**: all modes reach MRR 0.797 and Hit@5 100%; individual BM25/dense weighting affects pre-rerank order only.
- **Hybrid**: best at deep recall — R@7 = 0.736, R@10 = 0.770. Default and recommended for general use.
- **BM25**: highest raw R@10 = 0.777. Fastest mode (~5ms vs ~85ms hybrid).
- **Semantic**: slightly lower R@5/R@10 on this benchmark; useful for pure intent/concept queries.
- **All modes**: 100% Hit@5 on this 13-query benchmark. Treat as a mode-comparison baseline, not a general reliability guarantee.

**Note on `k`:** Benchmark runs use `k=10` — metrics at `@5`/`@7`/`@10` are cutoff statistics from those ranked lists. Running at `k=10` does not
change `@5` values.

**Source files:**

- `evaluation/golden_dataset.json` — 13 queries at the time of this 2026-06-08 run; the dataset has
since grown to **77 queries** total (`_meta.total_queries`, split train=43/val=16/test=18) — labels, thresholds, metadata
- `scripts/benchmark/run_sscg_benchmark.py` — runner (supports `--search-mode {hybrid,bm25,semantic}`)
- `scripts/benchmark/run_benchmark.sh` — shell wrapper

**Re-run benchmark:**

```bash
# Single mode (default hybrid):
./scripts/benchmark/run_benchmark.sh --project-path <project-path>

# Specific mode:
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --search-mode bm25
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --search-mode semantic

# Weight sweep (4 BM25/dense splits):
./scripts/benchmark/run_benchmark.sh --project-path <project-path> --sweep
```

---

## Line-Overlap Metrics (LR / LP / LIoU)

In addition to chunk-level Recall/MRR/NDCG, the runner computes **Chroma-style line-range overlap** between retrieved chunks and the golden
`expected_primary` set.

| Metric | Symbol | Aggregate (hybrid, 2026-06-08) |
|--------|--------|-------------------------------|
| Line Recall | LR | **0.852** |
| Line Precision | LP | **0.267** |
| Line IoU | LIoU | **0.304** |

**Interpretation:**

- **LR 0.852** — 85% of the expected source lines appear in the top-k retrieved chunks.
- **LP 0.267** — 27% of the retrieved source lines are relevant (rest are context overhead from surrounding code in the same chunks).
- **LIoU 0.304** — intersection / union of line sets; lower than LR because retrieved chunks contain broader context.

Low LP / LIoU relative to LR is expected: code chunks span whole functions/classes, so retrieving the right chunk always brings surrounding lines. The
high LR (0.852) confirms the search is surfacing the correct file regions.

---

## Mode Selection Guide

| Mode | Best for |
|------|---------|
| `auto` (default) | Most queries — routes intelligently |
| `bm25` | Exact function/class names, API calls |
| `hybrid` | Concepts + exact terms combined |
| `semantic` | Intent/concept queries, fuzzy matching |

> The per-mode latency figures previously shown here (~5–85ms) were uncorroborated and roughly 20×
> lower than every measured end-to-end run in this file (617ms–1798ms with neural reranking
> active). Removed rather than left misleading — see the "Latest Validation" table above for real
> measured per-query latency (reranking dominates total time, not the retrieval mode).

**Practical rule:** Start with `auto`, `k=7`. Switch to `bm25` when you know the exact symbol name. Use `k=10` for architectural/global queries.

---

## Result Reliability

- **Hit@5 ≈ 98–100% on the 63-query SSCG benchmark** (hybrid, k=7 — see "Latest Validation" above; one of three post-sweep runs was 0.9841, not
  1.000). Still not a general reliability guarantee for arbitrary queries or codebases, and the broader 96-query set sees pool-miss rates of ~2–3%.
- **Why k=7 over k=5:** targets may rank 6–7 on complex or multi-target queries. The `golden_dataset.recommended_k=7` reflects this.
- **Rank-1 reliability:** all modes have P@1 ≈ 0.69 (MRR 0.797 — not all primaries rank first). Always scan all k results before concluding.
- **When rank-1 is most reliable:** exact symbol lookup, small function discovery ("get X", "validate Y").
- **When you must scan all results:** class overview, sibling pairs ("encode and decode", "save and load"), queries where module summary
  chunks may surface.
