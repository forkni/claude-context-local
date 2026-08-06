"""Post-hoc per-category and per-split aggregate reporting over a saved SSCG run.

Track-1/canon captures (`run_sscg_benchmark.py`) already save every query's
per-query metrics (`per_query[].category`, `.mrr`, `.recall@k`, ...) in the output
JSON -- this script slices that array by `category` (already present) and by
`split` (joined in from the golden dataset by `id`, since `split` is not itself
saved per-query). No harness rewrite; this is read-only over an existing result
file.

Golden-dataset splits, full file (verified 2026-08-06): canonical 43/16/18 (train/val/test),
expanded 86/28/33. Scored (category D excluded, what run_sscg_benchmark.py and this script's
per-split table actually cover): canonical 35/13/15, expanded 78/25/30.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/aggregate_by_slice.py \
        benchmark_results/sscg_canon_d1_63q_r1.json
    .venv/Scripts/python.exe scripts/benchmark/aggregate_by_slice.py \
        benchmark_results/sscg_canon_d1_131q_r1.json \
        --golden-dataset evaluation/golden_dataset_expanded.json
"""

import argparse
import json
import statistics
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

METRICS = ("mrr", "recall@5", "recall@10", "ndcg@5", "hit")


def _mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def _infer_golden_dataset(n_queries: int) -> Path:
    # Canonical = 63 non-D queries; expanded (post H-promotion) = 131 non-D.
    # D-category queries are excluded from search_code-based scoring by
    # construction (run_sscg_benchmark.py), so per_query never contains them --
    # counts below are the harness's own non-D totals, not file totals.
    if n_queries <= 70:
        return REPO_ROOT / "evaluation" / "golden_dataset.json"
    return REPO_ROOT / "evaluation" / "golden_dataset_expanded.json"


def _load_splits(golden_dataset_path: Path) -> dict[str, str]:
    data = json.loads(golden_dataset_path.read_text(encoding="utf-8"))
    return {q["id"]: q.get("split", "unknown") for q in data["queries"]}


def _slice_table(rows: list[dict], key: str) -> list[tuple[str, int, dict[str, float]]]:
    buckets: dict[str, list[dict]] = {}
    for row in rows:
        buckets.setdefault(row[key], []).append(row)
    table = []
    for name in sorted(buckets):
        bucket_rows = buckets[name]
        means = {m: _mean([r[m] for r in bucket_rows if m in r]) for m in METRICS}
        table.append((name, len(bucket_rows), means))
    return table


def _print_table(title: str, table: list[tuple[str, int, dict[str, float]]]) -> None:
    print(f"\n{title}")
    header = f"{'slice':<10}{'n':>5}" + "".join(f"{m:>10}" for m in METRICS)
    print(header)
    print("-" * len(header))
    for name, n, means in table:
        row = f"{name:<10}{n:>5}" + "".join(f"{means[m]:>10.4f}" for m in METRICS)
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", help="Path to a run_sscg_benchmark.py --output JSON")
    parser.add_argument(
        "--golden-dataset",
        default="",
        help="Golden dataset JSON to join `split` from (default: inferred from query count)",
    )
    args = parser.parse_args()

    results_path = Path(args.results)
    data = json.loads(results_path.read_text(encoding="utf-8"))
    per_query = data["per_query"]
    published_mrr = data["aggregate"]["mrr"]

    golden_dataset_path = (
        Path(args.golden_dataset)
        if args.golden_dataset
        else _infer_golden_dataset(len(per_query))
    )
    splits = _load_splits(golden_dataset_path)

    rows = []
    for q in per_query:
        row = dict(q)
        row["split"] = splits.get(q["id"], "unknown")
        rows.append(row)

    unmatched = [r["id"] for r in rows if r["split"] == "unknown"]

    by_category = _slice_table(rows, "category")
    by_split = _slice_table(rows, "split")

    print(f"Results: {results_path}")
    print(f"Golden dataset (for split join): {golden_dataset_path}")
    print(f"Queries: {len(rows)}  (published aggregate MRR: {published_mrr:.4f})")
    if unmatched:
        print(
            f"WARNING: {len(unmatched)} query id(s) not found in golden dataset: {unmatched}"
        )

    _print_table("Per-category", by_category)
    _print_table("Per-split", by_split)

    # Reconciliation: slicing must sum back to the published unsliced aggregate.
    # A mismatch here is a bug in this slicer, not a finding about the model.
    recomputed_mrr = _mean([r["mrr"] for r in rows])
    delta = abs(recomputed_mrr - published_mrr)
    # 5e-4 tolerance: the harness rounds `aggregate.mrr` to 4 decimals before
    # saving, so up to ~5e-5 vs full-precision per_query is expected on its
    # own; the rest of the budget covers statistics.fmean's summation order
    # differing from whatever the harness used. Neither is a slicer bug.
    status = "OK" if delta < 5e-4 else "MISMATCH"
    print(
        f"\nReconciliation: recomputed overall MRR {recomputed_mrr:.6f} vs "
        f"published {published_mrr:.6f} (delta {delta:.2e}) -> {status}"
    )
    if status != "OK":
        sys.exit(1)


if __name__ == "__main__":
    main()
