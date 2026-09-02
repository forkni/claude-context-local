#!/usr/bin/env python
"""Probe leg-search depth x fusion function jointly, read-only.

Background: the closed TM2C2 fusion probe (``evaluation/TM2C2_FUSION_PROBE_20260814.md``)
found zero gold-membership change on both datasets at both pre-registered alpha, and
root-caused it to depth, not arithmetic: Q121's grade-3 gold sits at raw dense rank 84 /
raw BM25 rank 80 / RRF fused rank 41 (an earlier probe run at depth 200), but the probe
that returned the null result replayed the leg-search formula
(``search_k = max(reranker.top_k_candidates, k*5)``, ``search_executor.py:130``) at the
TOP-LEVEL ``k=10`` it was given, i.e. search_k=50 -- too shallow for Q121 to appear on
either leg at all.

CORRECTION (found while building this probe, 2026-08-14): search_k=50 is not actually the
depth a default query experiences. ``multi_hop.enabled=True`` by default
(``search/config.py``), and ``MultiHopSearcher.search()`` (``multi_hop_searcher.py:537-538``)
substitutes the request's k for hop-1 with ``initial_k = k * multi_hop.initial_k_multiplier``
(default multiplier 2.0) *before* calling the single-hop leg -- so a top-level ``k=10`` query's
hop-1 stage actually runs at k=20, giving ``search_k = max(30, 20*5) = 100``. Depth 50 is only
what a direct single-hop-mode call (``multi_hop.enabled=False``, or an explicit bypass) would
see. **Depth 100 is the true default-path reference cell**, not depth 50. This probe therefore
treats:

- depth  50 -- single-hop-mode floor (diagnostic only, NOT the deployed baseline)
- depth 100 -- the actual deployed default (hop-1 leg-search under multi_hop.enabled=True)
- depth 200 -- the widening arm under test

Evaluates a 3 (depth) x 3 (fusion: RRF / TM2C2 alpha=0.65 / TM2C2 alpha=0.8) matrix per
golden query, with the fused-pool cut fixed at ``fusion_k = max(k, reranker.top_k_candidates)``
(= 30 at defaults) in every cell, so depth is never confounded with a wider cut.

Reused, not re-implemented, from prior probes and the shared probe harness (probe/production
arithmetic drift is what invalidates a gate, and probe/probe drift between this and the closed
TM2C2 probe would be equally bad):

- ``evaluation/probe_harness.py``: searcher/config lifecycle (``open_probe``), golden-query
  loading (``load_golden_queries``, D+F excluded per its own docstring), and
  ``search.search_executor.fused_pool_cut`` for the fixed-across-depths fusion cut -- never a
  re-derived ``max(k, reranker_budget)`` literal.
- ``probe_tm2c2_fusion.py``: ``rank_of``, ``theoretical_min_max_normalize``, ``fuse_tm2c2``,
  ``ALPHAS``.
- ``probe_reserve_depth.py``: the raw-leg-call gotcha -- ``SearchExecutor.search_bm25`` /
  ``search_dense`` are the only RAW entry points; ``searcher.search(..., search_mode="bm25")``
  is NOT raw, ``multi_hop.enabled`` gates before the mode branch.
- ``probe_rerank_window.py``: ``Instrumentation``, reused for the fidelity check below (kept
  as its own cross-import -- its pass2/pass3 ordinal disambiguation is a distinct, more
  sophisticated adapter than ``probe_harness.ProbeSession.instrument``'s single-pass records,
  and this fidelity check is already a good reuse pattern, not hand-copied arithmetic).

Fidelity check (pre-registered, run before trusting any depth delta). This probe's raw leg
calls replay hop-1's OWN internal fused-cut, computed via the exact same
``RRFReranker.rerank_simple(..., max_results=fusion_k)`` call production makes
(``SearchExecutor.execute_single_hop``, hybrid branch) over the same raw legs at the same
depth. Production's hop-1 then runs that cut through its own neural-rerank pass
(``SearchExecutor.apply_neural_reranking``, tagged ``"[NEURAL_RERANK-SEARCH]"`` inside
``RerankingEngine._run_rerank``) BEFORE the multi-hop merge. That neural-rerank call's
``candidate_ids`` field -- the *input* it receives, before any reranker-internal reordering
or truncation -- is the exact fused-cut-30 set this probe computes offline at depth 100. On
a sample of queries this probe therefore compares, as SETS: this probe's depth-100/RRF
cut-30 vs. the live ``"[NEURAL_RERANK-SEARCH]"``-tagged call's ``candidate_ids``. They should
be IDENTICAL (same formula, same inputs, same depth) -- any mismatch means this probe's
replay differs from what production actually computes for hop-1, and no depth delta computed
from it can be trusted.

No production code is touched. ``min_bm25_score``-driven leg truncation and per-depth
wall-clock are recorded explicitly, since a "wider" depth argument does not guarantee a
longer BM25 leg (``bm25_index.py:462-490`` applies a score floor that can return fewer than
the requested depth).

Usage (module form required -- the ``scripts.benchmark.probe_tm2c2_fusion`` cross-import
below only resolves with the repo root on ``sys.path``, which ``-m`` provides and a direct
file invocation does not; ``scripts`` is not part of the editable-install package map that
makes bare ``evaluation``/``search`` imports work either way):
    .venv/Scripts/python.exe -m scripts.benchmark.probe_leg_depth_fusion \
        [--dataset evaluation/golden_dataset_expanded.json] [--project-path .] [--k 10] \
        [--depths 50 100 200] [--query-ids Q121 ...] [--json out.json] \
        [--fidelity-sample 10] [--skip-fidelity]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from evaluation import probe_harness
from evaluation.metrics import normalize_chunk_id
from scripts.benchmark.probe_tm2c2_fusion import (
    ALPHAS,
    fuse_tm2c2,
    rank_of,
    theoretical_min_max_normalize,  # noqa: F401  (re-exported for reuse/inspection)
)


# Depths under test. DEPLOYED_DEPTH is the reference cell -- see module docstring
# correction: it is NOT 50, because multi_hop.enabled=True substitutes k*2 before
# execute_single_hop's own k*5 widening (100 = max(30, 20*5) at k=10).
DEPTHS: tuple[int, ...] = (50, 100, 200)
DEPLOYED_DEPTH = 100
FUSION_ARMS: tuple[str, ...] = ("rrf",) + tuple(f"tm2c2_{a}" for a in ALPHAS)
HOP1_RERANK_LOG_PREFIX = "[NEURAL_RERANK-SEARCH]"


def leg_results_at_depth(executor, config, query: str, depth: int) -> dict[str, Any]:
    """Raw BM25 + dense leg results at ``depth``, with actual length + wall-clock."""
    min_score = config.search_mode.min_bm25_score
    t0 = time.time()
    bm25 = executor.search_bm25(query, depth, min_score, None)
    bm25_time = time.time() - t0
    t0 = time.time()
    dense = executor.search_dense(query, depth, None, None)
    dense_time = time.time() - t0
    return {
        "bm25": bm25,
        "dense": dense,
        "bm25_len": len(bm25),
        "dense_len": len(dense),
        "bm25_time_s": round(bm25_time, 4),
        "dense_time_s": round(dense_time, 4),
    }


def fuse_at_depth(executor, config, leg: dict, cut: int) -> dict[str, list[str]]:
    """Cut-``cut`` chunk-id lists at this leg depth, one per fusion arm."""
    bm25, dense = leg["bm25"], leg["dense"]
    rrf_fused = executor.reranker.rerank_simple(
        bm25_results=bm25,
        dense_results=dense,
        max_results=cut,
        bm25_weight=config.search_mode.bm25_weight,
        dense_weight=config.search_mode.dense_weight,
        reserved_slots=config.search_mode.bm25_reserved_slots,
    )
    cuts = {"rrf": [normalize_chunk_id(r.chunk_id) for r in rrf_fused]}
    for alpha in ALPHAS:
        tm2c2_full = fuse_tm2c2(bm25, dense, alpha)
        cuts[f"tm2c2_{alpha}"] = [normalize_chunk_id(cid) for cid, _ in tm2c2_full][
            :cut
        ]
    return cuts


def probe_query(
    session: probe_harness.ProbeSession,
    item: probe_harness.GoldenQuery,
    k: int,
    depths: tuple[int, ...],
) -> dict[str, Any]:
    """Capture the depth x fusion matrix for one query."""
    from search.search_executor import fused_pool_cut

    config = session.config
    query = item.query
    grades = item.grades
    executor = session.searcher.search_executor
    cut = fused_pool_cut(config, k)  # fusion_k, fixed across all depths

    cells: dict[int, dict[str, Any]] = {}
    for depth in depths:
        leg = leg_results_at_depth(executor, config, query, depth)
        bm25_ids = [normalize_chunk_id(c) for c, _, _ in leg["bm25"]]
        dense_ids = [normalize_chunk_id(c) for c, _, _ in leg["dense"]]
        cuts = fuse_at_depth(executor, config, leg, cut)

        gold_rows: dict[str, Any] = {}
        for gold, grade in grades.items():
            dense_rank = rank_of(gold, dense_ids)
            bm25_rank = rank_of(gold, bm25_ids)
            row: dict[str, Any] = {
                "grade": grade,
                "dense_rank": dense_rank,
                "bm25_rank": bm25_rank,
                # Q121-class: ranks beyond the cut on BOTH raw legs individually
                # (RRF's reciprocal-rank arithmetic structurally can't favor it)
                # yet visible within the leg-search depth on both.
                "q121_class": bool(
                    dense_rank is not None
                    and bm25_rank is not None
                    and dense_rank > cut
                    and bm25_rank > cut
                ),
            }
            for arm in FUSION_ARMS:
                row[f"{arm}_rank"] = rank_of(gold, cuts[arm])
            gold_rows[gold] = row

        cells[depth] = {
            "bm25_len": leg["bm25_len"],
            "dense_len": leg["dense_len"],
            "bm25_time_s": leg["bm25_time_s"],
            "dense_time_s": leg["dense_time_s"],
            "cuts": cuts,
            "golds": gold_rows,
        }

    return {
        "id": item.id,
        "category": item.category,
        "query": query,
        "cut": cut,
        "cells": cells,
    }


def _membership_delta(
    reports: list[dict[str, Any]], depth: int, arm: str, ref_depth: int, ref_arm: str
) -> dict[str, Any]:
    """Gold rescued/evicted at (depth, arm) vs the (ref_depth, ref_arm) cell."""
    rescued: list[tuple[str, str]] = []
    evicted: list[tuple[str, str]] = []
    q121_rescues: list[tuple[str, str]] = []
    for rep in reports:
        ref_cut = set(rep["cells"][ref_depth]["cuts"][ref_arm])
        arm_cut = set(rep["cells"][depth]["cuts"][arm])
        for gold, row in rep["cells"][depth]["golds"].items():
            in_ref = gold in ref_cut
            in_arm = gold in arm_cut
            if in_arm and not in_ref:
                rescued.append((rep["id"], gold))
                if row["q121_class"]:
                    q121_rescues.append((rep["id"], gold))
            elif in_ref and not in_arm:
                evicted.append((rep["id"], gold))
    return {
        "rescued": rescued,
        "evicted": evicted,
        "net": len(rescued) - len(evicted),
        "q121_class_rescues": q121_rescues,
    }


def summarize(reports: list[dict[str, Any]], depths: tuple[int, ...]) -> dict[str, Any]:
    """Gate-relevant rollup: membership deltas vs the deployed reference cell
    (Gate A input) and same-depth arm-vs-RRF deltas (Gate B input).

    ``DEPLOYED_DEPTH`` is the fixed semantic reference point (not swept); every
    other depth is read from ``depths``, the actual set of depths this run
    probed, which is NOT guaranteed to equal the module-level ``DEPTHS`` tuple
    (``--depths`` can narrow or widen it).
    """
    summary: dict[str, Any] = {"vs_reference": {}, "vs_same_depth_rrf": {}}
    for depth in depths:
        for arm in FUSION_ARMS:
            summary["vs_reference"][f"{depth}:{arm}"] = _membership_delta(
                reports, depth, arm, DEPLOYED_DEPTH, "rrf"
            )
    for depth in depths:
        for arm in FUSION_ARMS:
            if arm == "rrf":
                continue
            summary["vs_same_depth_rrf"][f"{depth}:{arm}"] = _membership_delta(
                reports, depth, arm, depth, "rrf"
            )
    return summary


def leg_stats(
    reports: list[dict[str, Any]], depths: tuple[int, ...]
) -> dict[int, dict[str, float]]:
    """Per-depth mean leg length (BM25-floor saturation) and mean wall-clock."""
    stats: dict[int, dict[str, float]] = {}
    for depth in depths:
        bm25_lens = [rep["cells"][depth]["bm25_len"] for rep in reports]
        dense_lens = [rep["cells"][depth]["dense_len"] for rep in reports]
        bm25_times = [rep["cells"][depth]["bm25_time_s"] for rep in reports]
        dense_times = [rep["cells"][depth]["dense_time_s"] for rep in reports]
        n = len(reports) or 1
        stats[depth] = {
            "mean_bm25_len": sum(bm25_lens) / n,
            "mean_dense_len": sum(dense_lens) / n,
            "bm25_saturated_frac": sum(1 for x in bm25_lens if x < depth) / n,
            "mean_bm25_time_s": sum(bm25_times) / n,
            "mean_dense_time_s": sum(dense_times) / n,
        }
    return stats


def fidelity_check(
    searcher, reports: list[dict[str, Any]], k: int, sample_size: int
) -> dict[str, Any]:
    """Compare this probe's depth-DEPLOYED_DEPTH/RRF cut-30 SET against the live
    hop-1-internal neural-rerank input (tagged "[NEURAL_RERANK-SEARCH]") for a
    sample of queries. See module docstring for why these should be identical.
    """
    from scripts.benchmark.probe_rerank_window import Instrumentation

    sample = reports[:sample_size]
    instr = Instrumentation(searcher)
    instr.install()
    mismatches: list[dict[str, Any]] = []
    try:
        for rep in sample:
            instr.reset()
            searcher.search(rep["query"], k=k)
            hop1_calls = [
                c
                for c in instr.run_rerank_calls
                if c["log_prefix"] == HOP1_RERANK_LOG_PREFIX
            ]
            if not hop1_calls:
                mismatches.append(
                    {"id": rep["id"], "reason": "no hop1-internal rerank call observed"}
                )
                continue
            live_ids = set(hop1_calls[0]["candidate_ids"])
            probe_ids = set(rep["cells"][DEPLOYED_DEPTH]["cuts"]["rrf"])
            if live_ids != probe_ids:
                mismatches.append(
                    {
                        "id": rep["id"],
                        "only_live": sorted(live_ids - probe_ids),
                        "only_probe": sorted(probe_ids - live_ids),
                    }
                )
    finally:
        instr.uninstall()
    return {
        "sampled": [rep["id"] for rep in sample],
        "mismatches": mismatches,
        "passed": not mismatches,
    }


def print_summary(
    reports: list[dict[str, Any]],
    summary: dict[str, Any],
    stats: dict[int, dict[str, float]],
    fidelity: dict[str, Any] | None,
    depths: tuple[int, ...],
) -> None:
    print(f"\n=== Leg depth x fusion probe over {len(reports)} queries ===")
    print(f"Reference cell: depth={DEPLOYED_DEPTH} arm=rrf (the true deployed default)")

    print("\n--- Leg saturation / latency per depth ---")
    print(
        f"{'depth':>6} {'mean_bm25_len':>14} {'mean_dense_len':>15} {'bm25_sat_frac':>14} {'bm25_ms':>9} {'dense_ms':>9}"
    )
    for depth in depths:
        s = stats[depth]
        print(
            f"{depth:>6} {s['mean_bm25_len']:>14.1f} {s['mean_dense_len']:>15.1f} "
            f"{s['bm25_saturated_frac']:>14.2f} {s['mean_bm25_time_s'] * 1000:>9.1f} "
            f"{s['mean_dense_time_s'] * 1000:>9.1f}"
        )

    print(f"\n--- Gate A: depth alone (RRF), vs reference depth={DEPLOYED_DEPTH} ---")
    print(f"{'depth':>6} {'rescued':>8} {'evicted':>8} {'net':>6} {'q121_class':>11}")
    for depth in depths:
        d = summary["vs_reference"][f"{depth}:rrf"]
        print(
            f"{depth:>6} {len(d['rescued']):>8} {len(d['evicted']):>8} {d['net']:>6} "
            f"{len(d['q121_class_rescues']):>11}"
        )

    print("\n--- Gate B: TM2C2 vs RRF at the same depth ---")
    print(
        f"{'depth':>6} {'arm':>12} {'rescued':>8} {'evicted':>8} {'net':>6} {'q121_class':>11}"
    )
    for depth in depths:
        for arm in FUSION_ARMS:
            if arm == "rrf":
                continue
            d = summary["vs_same_depth_rrf"][f"{depth}:{arm}"]
            print(
                f"{depth:>6} {arm:>12} {len(d['rescued']):>8} {len(d['evicted']):>8} "
                f"{d['net']:>6} {len(d['q121_class_rescues']):>11}"
            )

    print("\n--- All cells vs reference (full matrix) ---")
    print(
        f"{'depth':>6} {'arm':>12} {'rescued':>8} {'evicted':>8} {'net':>6} {'q121_class':>11}"
    )
    for depth in depths:
        for arm in FUSION_ARMS:
            d = summary["vs_reference"][f"{depth}:{arm}"]
            print(
                f"{depth:>6} {arm:>12} {len(d['rescued']):>8} {len(d['evicted']):>8} "
                f"{d['net']:>6} {len(d['q121_class_rescues']):>11}"
            )

    if fidelity is not None:
        print(f"\n--- Fidelity check ({len(fidelity['sampled'])} queries) ---")
        print(f"sampled: {', '.join(fidelity['sampled']) or '-'}")
        if fidelity["passed"]:
            print(
                "PASSED: depth-100/RRF replay is set-identical to the live hop-1 rerank input"
            )
        else:
            print(f"FAILED: {len(fidelity['mismatches'])} mismatch(es)")
            for m in fidelity["mismatches"]:
                print(f"  {m}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        parents=[probe_harness.probe_parser(__doc__.splitlines()[0])],
    )
    parser.add_argument("--depths", type=int, nargs="*", default=list(DEPTHS))
    parser.add_argument("--fidelity-sample", type=int, default=10)
    parser.add_argument("--skip-fidelity", action="store_true")
    args = parser.parse_args()

    # DEPLOYED_DEPTH is the fixed reference cell every gate compares against
    # (see module docstring) -- always computed even if the caller narrowed
    # --depths to exclude it, or summarize()'s membership deltas would KeyError.
    depths = tuple(sorted(set(args.depths) | {DEPLOYED_DEPTH}))

    dataset_path = probe_harness.resolve_dataset_path(args.dataset)
    try:
        items = probe_harness.load_golden_queries(
            dataset_path, args.query_ids, exclude_categories=("D", "F")
        )
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    with probe_harness.open_probe(args) as session:
        reports = []
        for i, item in enumerate(items, 1):
            print(f"[{i:3d}/{len(items)}] {item.id}", flush=True)
            reports.append(probe_query(session, item, k=args.k, depths=depths))

        summary = summarize(reports, depths)
        stats = leg_stats(reports, depths)

        fidelity = None
        if not args.skip_fidelity and args.fidelity_sample > 0:
            fidelity = fidelity_check(
                session.searcher, reports, k=args.k, sample_size=args.fidelity_sample
            )

        print_summary(reports, summary, stats, fidelity, depths)

        if args.json_out:
            payload = {
                "summary": summary,
                "leg_stats": stats,
                "fidelity": fidelity,
                "reports": reports,
            }
            probe_harness.write_probe_json(args.json_out, payload)

    if fidelity is not None and not fidelity["passed"]:
        print(
            "\nVERDICT: RED - fidelity check failed, depth deltas are not trustworthy"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
