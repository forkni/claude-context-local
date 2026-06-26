#!/usr/bin/env python3
"""MCP pipeline emission-order evaluation.

Runs A/B/C golden queries through SearchOrchestrator.run() — the actual MCP
server code path — and measures position-sensitive MRR/Recall@7 on the
EMISSION ORDER (no post-sort by score).

This is distinct from run_sscg_benchmark.py which calls searcher.search()
directly (bypasses SearchOrchestrator._apply_source_order_and_budget).

Usage:
    uv run python scripts/benchmark/run_mcp_pipeline_eval.py
    uv run python scripts/benchmark/run_mcp_pipeline_eval.py --k 7 --category A,B,C
    uv run python scripts/benchmark/run_mcp_pipeline_eval.py --split test
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from statistics import mean


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    aggregate_metrics,
    calculate_metrics_from_results,
    normalize_chunk_ids,
)


# ---------------------------------------------------------------------------
# Result extraction helpers
# ---------------------------------------------------------------------------


def _extract_chunk_ids_in_order(response: dict, k: int) -> list[str]:
    """Extract chunk_ids from orchestrator response in emission order (no re-sort)."""
    results = response.get("results", [])
    ids = []
    for r in results:
        cid = r.get("chunk_id") if isinstance(r, dict) else None
        if cid:
            ids.append(cid)
    return normalize_chunk_ids(ids[:k])


def _summarize_order(response: dict) -> list[tuple[str, float, float]]:
    """Return [(chunk_id, reranker_score, blended_score), ...] in emission order."""
    out = []
    for r in response.get("results", []):
        if not isinstance(r, dict):
            continue
        cid = r.get("chunk_id", "?")
        rs = r.get("reranker_score", 0.0)
        bs = r.get("blended_score") or r.get("score", 0.0)
        out.append((cid, rs, bs))
    return out


# ---------------------------------------------------------------------------
# Main benchmark loop
# ---------------------------------------------------------------------------


async def run_query(orchestrator, query: str, k: int) -> tuple[dict, float]:
    start = time.perf_counter()
    response = await orchestrator.run(
        {
            "query": query,
            "k": k,
            "include_context": True,
            "search_mode": "auto",
            "use_routing": True,
        }
    )
    latency = (time.perf_counter() - start) * 1000.0
    return response, latency


async def main_async(args) -> None:
    from mcp_server.tools.search_orchestrator import SearchOrchestrator

    golden_path = _PROJECT_ROOT / "evaluation" / "golden_dataset.json"
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)

    categories = set(args.category.split(",")) if args.category else {"A", "B", "C"}
    split_filter = args.split  # None = all splits

    queries = [
        q
        for q in golden["queries"]
        if q["category"] in categories
        and (split_filter is None or q.get("split") == split_filter)
    ]

    k = args.k
    orchestrator = SearchOrchestrator()

    print(f"\n{'=' * 80}")
    print(
        f"MCP Pipeline Emission-Order Evaluation  k={k}  categories={sorted(categories)}"
        + (f"  split={split_filter}" if split_filter else "")
    )
    print("source_order_output: FALSE  (results in relevance/centrality order)")
    print(f"{'=' * 80}\n")
    print(
        f"{'ID':<6} {'Cat':<4} {'Spl':<5} {'MRR':>6} {'R@7':>6} {'Hit':>5} "
        f"{'NDCG@5':>7} {'ms':>6}  Status"
    )
    print("-" * 75)

    per_query = []
    for q in queries:
        qid = q["id"]
        query_text = q["query"]
        category = q["category"]
        split = q.get("split", "?")

        response, latency = await run_query(orchestrator, query_text, k)

        if "error" in response:
            print(f"{qid:<6} {category:<4} {split:<5} -- error: {response['error']}")
            continue

        retrieved = _extract_chunk_ids_in_order(response, k)
        expected = q.get("expected", [])
        expected_primary = q.get("expected_primary", [])

        metrics = calculate_metrics_from_results(retrieved, expected, expected_primary)
        metrics.update(
            {
                "query_id": qid,
                "category": category,
                "split": split,
                "query": query_text,
                "latency_ms": round(latency, 1),
            }
        )
        per_query.append(metrics)

        hit = metrics.get("hit", False)
        status = "PASS" if hit else "FAIL"
        print(
            f"{qid:<6} {category:<4} {split:<5} "
            f"{metrics.get('mrr', 0):>6.3f} "
            f"{metrics.get('recall@7', 0):>6.3f} "
            f"{1.0 if hit else 0.0:>5.1f} "
            f"{metrics.get('ndcg@5', 0):>7.3f} "
            f"{latency:>6.0f}  {status}"
        )

        if args.verbose and not hit:
            order_info = _summarize_order(response)
            print(f"  expected_primary={expected_primary}")
            print(f"  retrieved_order (first {min(k, 7)}):")
            for i, (cid, rs, bs) in enumerate(order_info[:k]):
                marker = (
                    "***"
                    if cid in set(normalize_chunk_ids(expected_primary))
                    else "   "
                )
                print(f"    [{i}] rs={rs:.4f} bs={bs:.4f}  {marker} {cid}")

    if not per_query:
        print("No queries matched the filter criteria.")
        return

    agg = aggregate_metrics(per_query)

    print(f"\n{'=' * 75}")
    print(f"AGGREGATE  (n={len(per_query)} queries)")
    print(f"{'=' * 75}")
    print(
        f"  MRR:        {agg.get('mrr', 0):.4f}  "
        f"(baseline 0.700 searcher-only; 0.8519 DSPy-agent)"
    )
    print(f"  Recall@7:   {agg.get('recall@7', 0):.4f}  (baseline 0.696 searcher-only)")
    print(f"  Hit@7:      {agg.get('hit_rate@7', agg.get('hit_rate@5', 0)):.4f}")
    print(f"  NDCG@5:     {agg.get('ndcg@5', 0):.4f}")
    print(f"  Recall@5:   {agg.get('recall@5', 0):.4f}")
    if per_query:
        lats = [m["latency_ms"] for m in per_query]
        print(f"  Latency:    avg={mean(lats):.0f}ms  max={max(lats):.0f}ms")

    cats: dict = {}
    for pq in per_query:
        cats.setdefault(pq["category"], []).append(pq)
    print("\nPer-category MRR / Recall@7 / Hit@7:")
    for c in sorted(cats):
        ms = cats[c]
        mrrs = [m.get("mrr", 0) for m in ms]
        r7s = [m.get("recall@7", 0) for m in ms]
        hits = [1.0 if m.get("hit", False) else 0.0 for m in ms]
        print(
            f"  {c}: MRR={mean(mrrs):.3f}  R@7={mean(r7s):.3f}  "
            f"Hit@7={mean(hits):.3f}  (n={len(ms)})"
        )

    failures = [pq for pq in per_query if not pq.get("hit", False)]
    if failures:
        print(f"\nFailing queries ({len(failures)}/{len(per_query)}):")
        for pq in failures:
            print(
                f"  {pq['query_id']} ({pq['category']}/{pq['split']}): "
                f"R@7={pq.get('recall@7', 0):.3f}  "
                f'MRR={pq.get("mrr", 0):.3f}  "{pq["query"]}"'
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP pipeline emission-order SSCG eval"
    )
    parser.add_argument(
        "--k", type=int, default=7, help="Results per query (default: 7)"
    )
    parser.add_argument(
        "--category",
        default=None,
        help="Comma-separated category filter, e.g. A,B,C (default: A,B,C)",
    )
    parser.add_argument(
        "--split", default=None, help="Restrict to train/val/test split (default: all)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show emission order detail for failing queries",
    )
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
