"""Read-only: per-query paired MRR SD, MDE, paired tests, reranker headroom, label stats.

Reads the per-query dumps ``evaluation/ab_*.json`` (local, not tracked) and prints, per stored
A/B: mean paired MRR difference, its SD, the smallest detectable change
(MDE = 2.80 x SD / sqrt(n), alpha 0.05 two-sided, power 0.80), how many queries moved, and
paired-t / randomization p-values. Then reranker headroom on the canon legs. Results of the
2026-11-22 run: evaluation/CANON_20261122_LABEL_AUDIT.md ("Context: evaluation power").

    .venv/Scripts/python.exe scripts/benchmark/probe_eval_power.py [evaluation-dir]
"""

import json
import math
import random
import statistics as st
import sys
from pathlib import Path


E = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else Path(__file__).resolve().parents[2] / "evaluation"
)
PAIRS = [  # (label, control, treatment)
    ("cardb 133", "ab_cardb_control_133q_20260923", "ab_cardb_treat_133q_20260923"),
    ("cardb 63", "ab_cardb_control_63q_r1_20260923", "ab_cardb_treat_63q_r1_20260923"),
    (
        "item1 133",
        "ab_item1_control_133q_r1_20260923",
        "ab_item1_treat_133q_r1_20260923",
    ),
    ("item1 63", "ab_item1_control_63q_r1_20260923", "ab_item1_treat_63q_r1_20260923"),
    ("attn2 133", "ab2_attn_c133_20261018", "ab2_attn_t133_20261018"),
    ("attn3 133", "ab3_attn_c133_20261019", "ab3_attn_t133_20261019"),
    ("attn3 63", "ab3_attn_c63_20261019", "ab3_attn_t63_r1_20261019"),
    ("f2llm1.7 133", "ab_f2llm1p7b_c133_20261019", "ab_f2llm1p7b_t133_20261019"),
    ("f2llm1.7 63", "ab_f2llm1p7b_c63_20261019", "ab_f2llm1p7b_t63_r1_20261019"),
    ("torch213 133", "ab_torch213_c133_20261118", "ab_torch213_t133_20261118"),
    ("torch213 63", "ab_torch213_c63_20261118", "ab_torch213_t63_20261118"),
    ("noise 63 r1/r2", "ab3_attn_t63_r1_20261019", "ab3_attn_t63_r2_20261019"),
]


def load(name):
    d = json.loads((E / f"{name}.json").read_text(encoding="utf-8"))
    return {r["id"]: r for r in d["per_query"]}


def t_p(diffs):
    n = len(diffs)
    sd = st.stdev(diffs) if n > 1 else 0.0
    if sd == 0:
        return 1.0
    t = st.mean(diffs) / (sd / math.sqrt(n))
    # normal approx for two-sided p (n >= 63)
    return math.erfc(abs(t) / math.sqrt(2))


def perm_p(diffs, iters=20000, seed=0):
    rng = random.Random(seed)
    obs = abs(sum(diffs))
    hit = 0
    for _ in range(iters):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs)
        if abs(s) >= obs - 1e-12:
            hit += 1
    return hit / iters


print(
    f"{'pair':16s} {'n':>4s} {'dMRR':>8s} {'sd_d':>6s} {'MDE':>6s} {'nz':>4s} {'t_p':>6s} {'perm_p':>6s}"
)
for label, c, t in PAIRS:
    try:
        a, b = load(c), load(t)
    except FileNotFoundError as exc:
        print(label, "missing", exc.filename)
        continue
    ids = sorted(set(a) & set(b))
    diffs = [b[i]["mrr"] - a[i]["mrr"] for i in ids]
    n = len(diffs)
    sd = st.stdev(diffs)
    nz = sum(1 for x in diffs if abs(x) > 1e-9)
    sd_nz = st.stdev([x for x in diffs if abs(x) > 1e-9]) if nz > 1 else 0.0
    print(
        f"{label:16s} {n:4d} {st.mean(diffs):+8.4f} {sd:6.3f} {2.8 * sd / math.sqrt(n):6.3f} {nz:4d} "
        f"{t_p(diffs):6.3f} {perm_p(diffs):6.3f}   sd|moved={sd_nz:.3f}"
    )

print("\nHeadroom and labels (current canon legs):")
for name in (
    "ab_torch213_t133_20261118",
    "ab_torch213_t63_20261118",
):  # the find-similar leg records no pool_hit
    rows = list(load(name).values())
    n = len(rows)
    pool = sum(r["pool_hit"] for r in rows) / n
    p1 = sum(r["precision@1"] for r in rows) / n
    mrr = sum(r["mrr"] for r in rows) / n
    in_pool_not_top = sum(1 for r in rows if r["pool_hit"] and r["precision@1"] < 1)
    pool_miss = sum(1 for r in rows if not r["pool_hit"])
    ne = st.mean(len(r["expected"]) for r in rows)
    npri = st.mean(len(r.get("expected_primary") or []) for r in rows)
    single = sum(1 for r in rows if len(r["expected"]) == 1)
    print(
        f"  {name}: n={n} pool_hit={pool:.3f} hit@1={p1:.3f} MRR={mrr:.4f} "
        f"in-pool-not-rank1={in_pool_not_top} pool_miss={pool_miss} "
        f"mean|expected|={ne:.1f} mean|primary|={npri:.1f} single-gold={single}"
    )
