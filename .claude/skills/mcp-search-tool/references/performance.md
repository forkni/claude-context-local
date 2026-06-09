# Search Performance & Benchmark Reference

## Latest Validation (2026-06-08, hybrid k=10)

Post golden-set drift fix (`b5cfc24`) and line-overlap harness fix (`184e13b`). Thresholds enforced from `evaluation/golden_dataset.json`. Metrics auto-computed by `scripts/benchmark/run_sscg_benchmark.py`.

| MRR | Recall@5 | Recall@7 | Recall@10 | Hit@5 | NDCG@5 | Line Recall | Line Precision | Line IoU |
|-----|----------|----------|-----------|-------|--------|-------------|----------------|----------|
| **0.797** | **0.689** | **0.736** | **0.770** | **1.00** (13/13) | **0.717** | 0.852 | 0.267 | 0.304 |

All thresholds pass: MRR ≥ 0.50 ✓ | Recall@5 ≥ 0.55 ✓ | Hit@5 ≥ 0.80 ✓. Recommended operating point: **k=7** (`golden_dataset.recommended_k=7`).

---

## SSCG Benchmark (2026-06-08, three-mode comparison)

Mode-comparison baseline. Evaluated against 13 queries across 4 categories with neural reranker active. The cross-encoder reranker dominates final ranking — all three modes reach the same MRR (0.797).

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

**Note on `k`:** Benchmark runs use `k=10` — metrics at `@5`/`@7`/`@10` are cutoff statistics from those ranked lists. Running at `k=10` does not change `@5` values.

**Source files:**
- `evaluation/golden_dataset.json` — 13 queries, labels, thresholds, metadata
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

In addition to chunk-level Recall/MRR/NDCG, the runner computes **Chroma-style line-range overlap** between retrieved chunks and the golden `expected_primary` set.

| Metric | Symbol | Aggregate (hybrid, 2026-06-08) |
|--------|--------|-------------------------------|
| Line Recall | LR | **0.852** |
| Line Precision | LP | **0.267** |
| Line IoU | LIoU | **0.304** |

**Interpretation:**
- **LR 0.852** — 85% of the expected source lines appear in the top-k retrieved chunks.
- **LP 0.267** — 27% of the retrieved source lines are relevant (rest are context overhead from surrounding code in the same chunks).
- **LIoU 0.304** — intersection / union of line sets; lower than LR because retrieved chunks contain broader context.

Low LP / LIoU relative to LR is expected: code chunks span whole functions/classes, so retrieving the right chunk always brings surrounding lines. The high LR (0.852) confirms the search is surfacing the correct file regions.

---

## Mode Selection Guide

| Mode | Best for | Approximate latency |
|------|---------|---------------------|
| `auto` (default) | Most queries — routes intelligently | ~55ms |
| `bm25` | Exact function/class names, API calls | ~5ms |
| `hybrid` | Concepts + exact terms combined | ~85ms |
| `semantic` | Intent/concept queries, fuzzy matching | ~75ms |

**Practical rule:** Start with `auto`, `k=7`. Switch to `bm25` when you know the exact symbol name. Use `k=10` for architectural/global queries.

---

## Result Reliability

- **Hit@5 = 100% on the 2026-06-08 13-query SSCG benchmark** (all three modes, k=7). This is a mode-comparison baseline, not a general reliability guarantee for arbitrary queries.
- **Why k=7 over k=5:** targets may rank 6–7 on complex or multi-target queries. The `golden_dataset.recommended_k=7` reflects this.
- **Rank-1 reliability:** all modes have P@1 ≈ 0.69 (MRR 0.797 — not all primaries rank first). Always scan all k results before concluding.
- **When rank-1 is most reliable:** exact symbol lookup, small function discovery ("get X", "validate Y").
- **When you must scan all results:** class overview, sibling pairs ("encode and decode", "save and load"), queries where module/community summary chunks may surface.
