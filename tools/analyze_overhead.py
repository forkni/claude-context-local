"""Analyze real performance overhead from comparison results."""

import json
from pathlib import Path

def analyze_overhead():
    """Analyze real overhead excluding outliers."""
    results_path = Path(__file__).parent.parent / "analysis" / "comparison_results.json"

    with open(results_path, 'r') as f:
        data = json.load(f)

    queries = data['queries']

    # Sort by single-hop time to identify outliers
    times = [(
        q['query'],
        q['single_hop']['time_ms'],
        q['multi_hop']['time_ms'],
        q['comparison']['unique_discovery_count'],
        q['comparison']['value_rating']
    ) for q in queries]

    times.sort(key=lambda x: x[1])

    print("=" * 100)
    print("REAL PERFORMANCE ANALYSIS (First query excluded as outlier)")
    print("=" * 100)
    print()

    # Exclude first query (outlier)
    normal_queries = times[1:]

    # Calculate real averages
    avg_single = sum(t[1] for t in normal_queries) / len(normal_queries)
    avg_multi = sum(t[2] for t in normal_queries) / len(normal_queries)
    avg_overhead = avg_multi - avg_single
    avg_overhead_pct = (avg_overhead / avg_single) * 100

    print(f"Outlier excluded: '{times[0][0]}' (single: {times[0][1]:.1f}ms, multi: {times[0][2]:.1f}ms)")
    print()
    print(f"Real Averages (14 queries):")
    print(f"  Single-hop: {avg_single:.1f}ms")
    print(f"  Multi-hop:  {avg_multi:.1f}ms")
    print(f"  Overhead:   +{avg_overhead:.1f}ms (+{avg_overhead_pct:.1f}%)")
    print()

    # Analysis by value rating
    print("Performance by Value Rating:")
    print()

    for rating in ['HIGH', 'MEDIUM', 'LOW', 'NONE']:
        rated = [t for t in normal_queries if t[4] == rating]
        if rated:
            avg_s = sum(t[1] for t in rated) / len(rated)
            avg_m = sum(t[2] for t in rated) / len(rated)
            avg_disc = sum(t[3] for t in rated) / len(rated)
            overhead = avg_m - avg_s
            print(f"  {rating:6} ({len(rated):2} queries): {avg_s:5.1f}ms → {avg_m:5.1f}ms "
                  f"(+{overhead:4.1f}ms, {avg_disc:.1f} discoveries)")

    print()
    print("=" * 100)
    print("DETAILED QUERY BREAKDOWN")
    print("=" * 100)
    print()
    print(f"{'Query':45} | {'Single':>6} | {'Multi':>6} | {'Overhead':>10} | {'Disc':>4} | {'Value':>6}")
    print("-" * 100)

    for q, s, m, disc, val in times[1:]:  # Exclude outlier
        overhead = m - s
        overhead_pct = (overhead / s * 100) if s > 0 else 0
        q_short = q[:42] + "..." if len(q) > 45 else q
        print(f"{q_short:45} | {s:6.1f} | {m:6.1f} | +{overhead:5.1f}ms {overhead_pct:+5.0f}% | {disc:4} | {val:>6}")

if __name__ == "__main__":
    analyze_overhead()
