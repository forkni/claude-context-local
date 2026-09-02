#!/usr/bin/env python
"""Probe TM2C2 normalized-score fusion vs deployed RRF (read-only).

TM2C2 (Bruch, Gai & Ingber, "An Analysis of Fusion Functions for Hybrid
Retrieval", ACM TOIS 2023, arXiv 2210.11934) fuses BM25 and dense legs as a
convex combination of *theoretical-min-max*-normalized scores, rather than
RRF's reciprocal-rank arithmetic. It targets the RRF-exclusion class: a
candidate that ranks decently (not top) on BOTH legs can still miss RRF's
fused cut because reciprocal rank saturates fast (Q121 exemplar: dense rank
84 / BM25 rank 80 / RRF fused rank 41, all beyond a 30-slot cut).

This probe replays, for every golden query, the exact deployed leg-search
depth and fused-pool cut (``ProbeSession.replay_legs`` -- itself
``search_executor.leg_search_depth``/``fused_pool_cut``, never a re-derived
literal; see ``evaluation/probe_harness.py``), then compares RRF's cut
membership (``RRFReranker.rerank_simple``, unmodified) against a **local**
TM2C2 implementation at two pre-registered alpha values. No production code
is touched; ``_theoretical_min_max_normalize``/``fuse_tm2c2`` here are the
reference implementation later lifted verbatim into ``search/reranker.py``
if the gate passes (probe/production drift would invalidate the gate).

Normalization:
- BM25 theoretical min: 0.0 (floored -- Okapi IDF can go slightly negative,
  but 0.0 is the textbook floor TM2C2 uses for a probabilistic-IR leg).
- Dense theoretical min: -1.0 (cosine similarity floor; this project's FAISS
  index is inner-product over L2-normalized vectors, i.e. cosine).
- Max is the empirical per-query max score on that leg.
- ``norm = (score - theoretical_min) / (empirical_max - theoretical_min)``;
  a non-positive denominator (degenerate query, e.g. all-zero leg) yields
  all-zero norms for that leg rather than dividing by zero.
- ``fused = alpha * norm_dense + (1 - alpha) * norm_bm25``. ``alpha`` is the
  dense-side weight, matching the deployed RRF orientation (dense 0.65 /
  bm25 0.35), so the two are comparable at corresponding settings.
- A candidate present in both legs sums both weighted terms; a candidate
  present in only one leg gets that one term only (no missing-leg penalty
  beyond what its absence already implies).

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_tm2c2_fusion.py \
        [--dataset evaluation/golden_dataset_expanded.json] \
        [--project-path .] [--k 10] \
        [--query-ids Q121 H063 ...] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from evaluation import probe_harness
from evaluation.metrics import normalize_chunk_id


# Pre-registered alpha values (dense-side weight) -- no sweep.
ALPHAS: tuple[float, ...] = (0.65, 0.8)

# Theoretical score floors (see module docstring).
BM25_THEORETICAL_MIN = 0.0
DENSE_THEORETICAL_MIN = -1.0

# Q121 -- the named exemplar of the RRF-exclusion class this probe targets.
WATCHLIST = ("Q121",)


def rank_of(gold: str, ids: list[str]) -> int | None:
    """1-based rank of ``gold`` in ``ids``, or None when absent."""
    try:
        return ids.index(gold) + 1
    except ValueError:
        return None


def theoretical_min_max_normalize(
    scored: list[tuple[str, float]], theoretical_min: float
) -> dict[str, float]:
    """Per-leg TM2C2 normalization: ``(score - theoretical_min) / (max - theoretical_min)``.

    ``max`` is the empirical per-query max on this leg. A non-positive
    denominator (degenerate query) yields all-zero norms rather than a
    division error -- this is the reference implementation later lifted
    verbatim into ``search/reranker.py``'s production helper.
    """
    if not scored:
        return {}
    empirical_max = max(score for _, score in scored)
    denom = empirical_max - theoretical_min
    if denom <= 0:
        return {chunk_id: 0.0 for chunk_id, _ in scored}
    return {chunk_id: (score - theoretical_min) / denom for chunk_id, score in scored}


def fuse_tm2c2(
    bm25_results: list[tuple[str, float, dict]],
    dense_results: list[tuple[str, float, dict]],
    alpha: float,
) -> list[tuple[str, float]]:
    """Convex combination of theoretical-min-max-normalized leg scores.

    ``alpha`` is the dense-side weight. Returns ``(chunk_id, fused_score)``
    sorted descending -- the same shape ``RRFReranker._select_with_reserve``
    consumes, so the production dispatch can reuse it unchanged.
    """
    bm25_norm = theoretical_min_max_normalize(
        [(c, s) for c, s, _ in bm25_results], BM25_THEORETICAL_MIN
    )
    dense_norm = theoretical_min_max_normalize(
        [(c, s) for c, s, _ in dense_results], DENSE_THEORETICAL_MIN
    )
    fused: dict[str, float] = {}
    for chunk_id, norm in bm25_norm.items():
        fused[chunk_id] = fused.get(chunk_id, 0.0) + (1 - alpha) * norm
    for chunk_id, norm in dense_norm.items():
        fused[chunk_id] = fused.get(chunk_id, 0.0) + alpha * norm
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)


def probe_query(
    session: probe_harness.ProbeSession, item: probe_harness.GoldenQuery, k: int
) -> dict[str, Any]:
    """Capture leg orders + RRF/TM2C2 cut membership for one query."""
    query = item.query
    grades = item.grades

    capture = session.replay_legs(query, k=k)
    search_k = capture.search_k
    cut = capture.cut

    rrf_ids = capture.fused
    rrf_set = set(rrf_ids)

    variants: dict[str, Any] = {}
    for alpha in ALPHAS:
        tm2c2_full = fuse_tm2c2(capture.raw_bm25, capture.raw_dense, alpha)
        tm2c2_ids = [normalize_chunk_id(cid) for cid, _ in tm2c2_full][:cut]
        tm2c2_set = set(tm2c2_ids)

        rescued = []
        evicted = []
        for gold, grade in sorted(grades.items(), key=lambda kv: -kv[1]):
            dense_rank = capture.rank_of(gold, "dense")
            bm25_rank = capture.rank_of(gold, "bm25")
            row = {
                "gold": gold,
                "grade": grade,
                "dense_rank": dense_rank,
                "bm25_rank": bm25_rank,
                "rrf_rank": capture.rank_of(gold, "fused"),
                "tm2c2_rank": rank_of(gold, tm2c2_ids),
                # Q121-class: ranks beyond the cut on BOTH raw legs individually
                # (so RRF's reciprocal-rank arithmetic can't favor it) yet
                # visible within the leg-search depth on both.
                "q121_class": bool(
                    dense_rank is not None
                    and bm25_rank is not None
                    and dense_rank > cut
                    and bm25_rank > cut
                ),
            }
            in_rrf = gold in rrf_set
            in_tm2c2 = gold in tm2c2_set
            if in_tm2c2 and not in_rrf:
                rescued.append(row)
            elif in_rrf and not in_tm2c2:
                evicted.append(row)
        variants[str(alpha)] = {"rescued_golds": rescued, "evicted_golds": evicted}

    return {
        "id": item.id,
        "category": item.category,
        "query": query,
        "cut": cut,
        "search_k": search_k,
        "variants": variants,
    }


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Per-alpha rescue/eviction rollup -- the pre-registered gate inputs."""
    summary: dict[str, Any] = {}
    for alpha in ALPHAS:
        key = str(alpha)
        rescued_q: list[str] = []
        evicted_q: list[str] = []
        rescued_count = 0
        evicted_count = 0
        q121_rescues: list[tuple[str, str]] = []
        watchlist_rescued: list[str] = []
        for rep in reports:
            var = rep["variants"][key]
            if var["rescued_golds"]:
                rescued_q.append(rep["id"])
                rescued_count += len(var["rescued_golds"])
                if rep["id"] in WATCHLIST:
                    watchlist_rescued.append(rep["id"])
                for g in var["rescued_golds"]:
                    if g["q121_class"]:
                        q121_rescues.append((rep["id"], g["gold"]))
            if var["evicted_golds"]:
                evicted_q.append(rep["id"])
                evicted_count += len(var["evicted_golds"])
        summary[key] = {
            "queries_with_rescued_gold": rescued_q,
            "queries_with_evicted_gold": evicted_q,
            "rescued_gold_count": rescued_count,
            "evicted_gold_count": evicted_count,
            "net": rescued_count - evicted_count,
            "q121_class_rescues": q121_rescues,
            "watchlist_rescued": watchlist_rescued,
        }
    return summary


def print_summary(reports: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Human-readable rollup + gate-relevant detail."""
    print(f"\n=== TM2C2 vs RRF cut-membership over {len(reports)} queries ===")
    print(
        f"{'alpha':<8} {'rescued_q':>9} {'evicted_q':>9} {'rescued':>8} "
        f"{'evicted':>8} {'net':>6} {'q121_class':>11} {'watchlist':>10}"
    )
    for alpha in ALPHAS:
        s = summary[str(alpha)]
        print(
            f"{alpha:<8} {len(s['queries_with_rescued_gold']):>9} "
            f"{len(s['queries_with_evicted_gold']):>9} "
            f"{s['rescued_gold_count']:>8} {s['evicted_gold_count']:>8} "
            f"{s['net']:>6} {len(s['q121_class_rescues']):>11} "
            f"{len(s['watchlist_rescued']):>10}"
        )
    for alpha in ALPHAS:
        s = summary[str(alpha)]
        print(f"\nalpha={alpha}:")
        print(f"  rescued queries: {', '.join(s['queries_with_rescued_gold']) or '-'}")
        print(f"  evicted queries: {', '.join(s['queries_with_evicted_gold']) or '-'}")
        print(
            "  q121-class rescues: "
            + (
                ", ".join(f"{qid}:{gold}" for qid, gold in s["q121_class_rescues"])
                or "-"
            )
        )
        print(f"  watchlist rescued: {', '.join(s['watchlist_rescued']) or '-'}")

    print("\n=== Watch-list funnel detail ===")
    by_id = {rep["id"]: rep for rep in reports}
    for qid in WATCHLIST:
        rep = by_id.get(qid)
        if rep is None:
            continue
        print(f"\n{qid}: {rep['query']!r} (cut={rep['cut']})")
        for alpha in ALPHAS:
            var = rep["variants"][str(alpha)]
            print(
                f"  alpha={alpha}: rescued={var['rescued_golds']} evicted={var['evicted_golds']}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        parents=[probe_harness.probe_parser(__doc__.splitlines()[0])],
    )
    args = parser.parse_args()

    dataset_path = probe_harness.resolve_dataset_path(args.dataset)
    try:
        items = probe_harness.load_golden_queries(dataset_path, args.query_ids)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    with probe_harness.open_probe(args) as session:
        reports = []
        for i, item in enumerate(items, 1):
            print(f"[{i:3d}/{len(items)}] {item.id}", flush=True)
            reports.append(probe_query(session, item, k=args.k))

        summary = summarize(reports)
        print_summary(reports, summary)

        if args.json_out:
            payload = {"summary": summary, "reports": reports}
            probe_harness.write_probe_json(args.json_out, payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
