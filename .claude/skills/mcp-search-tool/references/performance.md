# Search Performance & Benchmark Reference

## SSCG Benchmark (2026-04-10, three-mode)

Evaluated against 13 queries across 4 categories (A: Small Function Discovery, B: Sibling Context, C: Class Overview, D: Connection Queries) on this project's own codebase. All three modes pass all thresholds.

**Thresholds:** MRR ≥ 0.50 | Recall@5 ≥ 0.55 | Hit@5 ≥ 0.80

| Mode | MRR | Recall@5 | Recall@10 | Hit@5 | NDCG@10 | P@1 | Best category |
|------|-----|----------|-----------|-------|---------|-----|---------------|
| **BM25** | **0.846** | 0.660 | 0.712 | 13/13 (100%) | 0.709 | **0.769** | A: 0.90 |
| **Hybrid** | 0.800 | 0.622 | **0.833** | 13/13 (100%) | **0.730** | 0.692 | A: 0.85 |
| **Semantic** | 0.712 | 0.660 | 0.731 | 13/13 (100%) | 0.685 | 0.692 | C: 0.80 |

**Key findings:**
- **BM25**: Best for exact symbol lookup (Cat A: 0.90, MRR 0.846). Fastest mode.
- **Hybrid**: Best at deep recall — R@10 = 0.833, NDCG@10 = 0.730. Best for architectural/conceptual queries.
- **Semantic**: Ties BM25 on Cat C (Class Overview: 0.80). Underperforms on Cat A (exact symbols: 0.60).
- **All modes**: 100% Hit@5 **on this 13-query SSCG benchmark** — the labeled target appeared in the top 5 for every query. This is not a general reliability guarantee; treat it as a mode-comparison baseline, not a property of arbitrary future queries.

**Source files:**
- `evaluation/golden_dataset.json` — 13 queries, labels, thresholds, metadata
- `benchmark_results/sscg_mcp_bm25_k10_20260410_175903.json`
- `benchmark_results/sscg_mcp_hybrid_k10_20260410_175331.json`
- `benchmark_results/sscg_mcp_semantic_k10_20260410_175331.json`

**Re-run benchmark:**

Replace `<project-path>` with the path to the project you want to evaluate. From the repo root of this project, pass `.` to re-run on itself.

```bash
# Run all three modes (hybrid, bm25, semantic):
./scripts/benchmark/run_benchmark.sh --project-path <project-path>

# Or run a single mode directly (cwd = repo root):
.venv/Scripts/python scripts/benchmark/mcp_eval.py --mode hybrid
.venv/Scripts/python scripts/benchmark/mcp_eval.py --mode bm25
.venv/Scripts/python scripts/benchmark/mcp_eval.py --mode semantic
```

---

## Mode Selection Guide

| Mode | Best for | Approximate latency |
|------|---------|---------------------|
| `auto` (default) | Most queries — routes intelligently | ~55ms |
| `bm25` | Exact function/class names, API calls | ~5ms |
| `hybrid` | Concepts + exact terms combined | ~85ms |
| `semantic` | Intent/concept queries, fuzzy matching | ~75ms |

**Practical rule:** Start with `auto`. Switch to `bm25` when you know the exact symbol name. Use `k=10` for architectural/global queries.

---

## Result Reliability

- **Hit@5 = 100% on this 13-query SSCG benchmark**: the labeled target appeared in the top 5 for every query at `k≥5`. This is a mode-comparison baseline, not a general reliability guarantee for arbitrary queries.
- **Rank-1 reliability:** BM25 highest (P@1 = 0.769), semantic/hybrid lower (P@1 = 0.692). Always scan all k results before concluding.
- **When rank-1 is most reliable:** exact symbol lookup, small function discovery ("get X", "validate Y").
- **When you must scan all results:** class overview, sibling pairs ("encode and decode", "save and load"), queries where module/community summary chunks may surface.
