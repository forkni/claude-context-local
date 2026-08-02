"""Compare run-to-run determinism between two SSCG benchmark rounds.

Step 2 gate analysis for the fp32 reranker determinism arm (campaign plan
2026-08-02): given two rounds of the *same* arm on the same dataset and
index, report

- flip count: queries whose per-query ``mrr`` differs between rounds
  (the bf16 baseline flips 4-5 boundary queries between identical runs);
- pool_hit flips and per-round ``pool_hit_rate`` (bf16 baseline spread:
  0.9695 vs 0.9542);
- aggregate MRR / recall deltas (guard band +/-0.02);
- mean latency per round (guard: no regression from the dtype change).

Usage:
    .venv/Scripts/python.exe scripts/benchmark/analyze_dtype_determinism.py \
        benchmark_results/sscg_fp32_expanded_r1_20260802.json \
        benchmark_results/sscg_fp32_expanded_r2_20260802.json \
        [--label fp32]
"""

import argparse
import json
from pathlib import Path


def load_round(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "aggregate": data["aggregate"],
        "avg_latency_ms": data.get("avg_latency_ms"),
        "per_query": {q["id"]: q for q in data["per_query"]},
    }


def compare_rounds(r1: dict, r2: dict, label: str) -> None:
    ids = sorted(set(r1["per_query"]) & set(r2["per_query"]))
    missing = set(r1["per_query"]) ^ set(r2["per_query"])
    if missing:
        print(f"WARNING: {len(missing)} ids not shared: {sorted(missing)}")

    mrr_flips = []
    pool_flips = []
    for qid in ids:
        a, b = r1["per_query"][qid], r2["per_query"][qid]
        if abs(a["mrr"] - b["mrr"]) > 1e-9:
            mrr_flips.append((qid, a["mrr"], b["mrr"]))
        if a.get("pool_hit") != b.get("pool_hit"):
            pool_flips.append((qid, a.get("pool_hit"), b.get("pool_hit")))

    agg1, agg2 = r1["aggregate"], r2["aggregate"]
    print(f"=== {label}: round-to-round determinism ({len(ids)} shared queries) ===")
    print(f"mrr flips: {len(mrr_flips)}")
    for qid, m1, m2 in mrr_flips:
        print(f"  {qid}: {m1:.4f} -> {m2:.4f}")
    print(f"pool_hit flips: {len(pool_flips)}")
    for qid, p1, p2 in pool_flips:
        print(f"  {qid}: {p1} -> {p2}")
    for key in ("mrr", "recall@10", "recall@20", "pool_hit_rate"):
        v1, v2 = agg1.get(key), agg2.get(key)
        if v1 is None or v2 is None:
            continue
        print(f"{key}: r1={v1:.4f} r2={v2:.4f} spread={abs(v1 - v2):.4f}")
    lat1, lat2 = r1["avg_latency_ms"], r2["avg_latency_ms"]
    if lat1 is not None and lat2 is not None:
        print(f"avg_latency_ms: r1={lat1:.0f} r2={lat2:.0f}")


def compare_arms(base: dict, arm: dict, label: str) -> None:
    """Aggregate + per-query delta of an arm round vs a baseline round."""
    print(f"=== {label}: arm vs baseline ===")
    for key in ("mrr", "recall@10", "recall@20", "pool_hit_rate"):
        b, a = base["aggregate"].get(key), arm["aggregate"].get(key)
        if b is None or a is None:
            continue
        print(f"{key}: base={b:.4f} arm={a:.4f} delta={a - b:+.4f}")
    ids = sorted(set(base["per_query"]) & set(arm["per_query"]))
    deltas = [
        (qid, arm["per_query"][qid]["mrr"] - base["per_query"][qid]["mrr"])
        for qid in ids
    ]
    changed = [(q, d) for q, d in deltas if abs(d) > 1e-9]
    print(f"per-query mrr changes: {len(changed)}")
    for qid, d in sorted(changed, key=lambda x: x[1]):
        print(f"  {qid}: {d:+.4f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("round1")
    parser.add_argument("round2")
    parser.add_argument("--label", default="arm")
    parser.add_argument(
        "--baseline",
        nargs="*",
        default=[],
        help="Optional baseline round file(s) to diff the arm's round1 against.",
    )
    args = parser.parse_args()

    r1 = load_round(args.round1)
    r2 = load_round(args.round2)
    compare_rounds(r1, r2, args.label)
    for base_path in args.baseline:
        base = load_round(base_path)
        compare_arms(base, r1, f"{args.label} r1 vs {Path(base_path).stem}")


if __name__ == "__main__":
    main()
