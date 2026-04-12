#!/usr/bin/env python3
"""
MCP-based SSCG evaluation: evaluate 13 golden queries using pre-collected
results from the MCP server.

RAW_RESULTS are stored in benchmark_results/raw_mcp_results_{mode}.json.
Collect new results by running search_code(query, k=10, search_mode=MODE)
against the live MCP server and updating the corresponding JSON file.

Usage:
    python mcp_eval.py --mode hybrid
    python mcp_eval.py --mode bm25
    python mcp_eval.py --mode semantic
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    aggregate_metrics,
    calculate_metrics_from_results,
    normalize_chunk_ids,
)


# ---------------------------------------------------------------------------
# Mode labels and output naming
# ---------------------------------------------------------------------------
MODE_LABELS = {
    "hybrid": "hybrid/auto",
    "bm25": "BM25-only",
    "semantic": "semantic-only",
}


def load_raw_results(mode: str) -> dict[str, list]:
    """Load pre-collected MCP results from JSON data file."""
    data_path = PROJECT_ROOT / "evaluation" / f"raw_mcp_results_{mode}.json"
    if not data_path.exists():
        print(f"[ERROR] Raw results file not found: {data_path}", file=sys.stderr)
        print(
            f"  Collect results by running search_code(..., search_mode={mode!r})",
            file=sys.stderr,
        )
        print(f"  and saving to {data_path}", file=sys.stderr)
        sys.exit(1)
    with open(data_path) as f:
        data = json.load(f)
    # Convert [[score, chunk_id], ...] entries to [(score, chunk_id), ...]
    return {
        qid: [(s, c) for s, c in entries] for qid, entries in data["results"].items()
    }


def get_top_k_chunk_ids(raw: list, k: int = 10) -> list[str]:
    """Sort by score descending, return top-k normalized chunk IDs."""
    sorted_results = sorted(raw, key=lambda x: x[0], reverse=True)
    chunk_ids = [r[1] for r in sorted_results[:k]]
    return normalize_chunk_ids(chunk_ids)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP-based SSCG evaluation")
    parser.add_argument(
        "--mode",
        choices=["hybrid", "bm25", "semantic"],
        required=True,
        help="Search mode to evaluate",
    )
    args = parser.parse_args()
    mode = args.mode
    label = MODE_LABELS[mode]

    raw_results = load_raw_results(mode)

    golden_path = PROJECT_ROOT / "evaluation" / "golden_dataset.json"
    with open(golden_path) as f:
        golden = json.load(f)
    queries = {q["id"]: q for q in golden["queries"]}
    thresholds = golden["thresholds"]

    per_query = []
    print(f"\n{'=' * 80}")
    print(f"MCP-based SSCG Evaluation (k=10, {label} mode)")
    print(f"{'=' * 80}\n")
    print(
        f"{'ID':<6} {'Cat':<4} {'MRR':>6} {'R@5':>6} {'R@10':>6} {'Hit@5':>6} {'NDCG@5':>7}  Status"
    )
    print("-" * 70)

    for qid, raw in sorted(raw_results.items()):
        query_meta = queries[qid]
        retrieved = get_top_k_chunk_ids(raw, k=10)
        expected = query_meta["expected"]
        expected_primary = query_meta["expected_primary"]
        category = query_meta["category"]

        metrics = calculate_metrics_from_results(retrieved, expected, expected_primary)
        metrics["query_id"] = qid
        metrics["category"] = category
        metrics["query"] = query_meta["query"]
        per_query.append(metrics)

        hit = metrics.get("hit", False)
        status = "PASS" if hit else "FAIL"
        print(
            f"{qid:<6} {category:<4} "
            f"{metrics.get('mrr', 0):>6.3f} "
            f"{metrics.get('recall@5', 0):>6.3f} "
            f"{metrics.get('recall@10', 0):>6.3f} "
            f"{1.0 if hit else 0.0:>6.3f} "
            f"{metrics.get('ndcg@5', 0):>7.3f}  {status}"
        )

    agg = aggregate_metrics(per_query)
    print(f"\n{'=' * 70}")
    print(f"AGGREGATE METRICS ({label})")
    print(f"{'=' * 70}")
    thr_mrr = thresholds["mrr"]
    thr_r5 = thresholds["recall_at_5"]
    thr_hit = thresholds["hit_rate_at_5"]
    print(
        f"  MRR:          {agg.get('mrr', 0):.4f}  (threshold: {thr_mrr})  {'PASS' if agg.get('mrr', 0) >= thr_mrr else 'FAIL'}"
    )
    print(
        f"  Recall@5:     {agg.get('recall@5', 0):.4f}  (threshold: {thr_r5})  {'PASS' if agg.get('recall@5', 0) >= thr_r5 else 'FAIL'}"
    )
    print(
        f"  Hit Rate@5:   {agg.get('hit_rate@5', 0):.4f}  (threshold: {thr_hit})  {'PASS' if agg.get('hit_rate@5', 0) >= thr_hit else 'FAIL'}"
    )
    print(f"  Recall@10:    {agg.get('recall@10', 0):.4f}")
    print(f"  NDCG@5:       {agg.get('ndcg@5', 0):.4f}")
    print(f"  NDCG@10:      {agg.get('ndcg@10', 0):.4f}")

    # Per-category breakdown
    cats: dict = {}
    for pq in per_query:
        cats.setdefault(pq["category"], []).append(pq)
    print("\nPer-category MRR:")
    for c in sorted(cats):
        cat_mrrs = [m.get("mrr", 0) for m in cats[c]]
        cat_hits = [1.0 if m.get("hit", False) else 0.0 for m in cats[c]]
        print(
            f"  Category {c}: "
            f"MRR={sum(cat_mrrs) / len(cat_mrrs):.3f}  "
            f"Hit@5={sum(cat_hits) / len(cat_hits):.3f}  "
            f"(n={len(cat_mrrs)})"
        )

    failures = [pq for pq in per_query if not pq.get("hit", False)]
    if failures:
        print(f"\nFailing queries ({len(failures)}/{len(per_query)}):")
        for pq in failures:
            print(
                f"  {pq['query_id']} ({pq['category']}): "
                f"recall@5={pq.get('recall@5', 0):.3f} "
                f"mrr={pq.get('mrr', 0):.3f}  "
                f'"{pq["query"]}"'
            )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = (
        PROJECT_ROOT / "benchmark_results" / f"sscg_mcp_{mode}_k10_{timestamp}.json"
    )
    out_path.parent.mkdir(exist_ok=True)
    result = {
        "config_name": f"mcp_{mode}_k10",
        "timestamp": timestamp,
        "k": 10,
        "search_mode": mode,
        "aggregate": agg,
        "thresholds": thresholds,
        "per_query": per_query,
    }
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
