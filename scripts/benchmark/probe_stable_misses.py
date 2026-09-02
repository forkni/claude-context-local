#!/usr/bin/env python
"""Classify stable golden-set misses by funnel stage (read-only diagnosis).

For each query, measures where every graded gold chunk sits in the retrieval
funnel and assigns one of five miss classes:

- ``vocab-gap``            — neither leg retrieves it within the probe depth
- ``depth-truncation``     — a leg sees it, but beyond the production
                             ``search_k`` (``leg_search_depth`` — live
                             ``leg_search_multiplier``, not a fixed ``k*5``)
- ``rrf-arithmetic``       — both legs within production depth, but the fused
                             RRF rank falls outside the hop-1 pool cut
- ``hop1-rerank-demotion`` — inside the hop-1 fused pool, but the hop-1
                             listwise rerank cuts it at ``[:initial_k]`` so it
                             never becomes a multi-hop seed
- ``merged-cut``           — survives hop-1 as a seed, but absent from the
                             final rerank pool after multi-hop/ego/parent
                             merging (the ADR-0013 territory)
- ``model-demotion``       — inside the final rerank pool (pool_hit=True), the
                             listwise reranker ranks it below top-k
- ``window-cut``           — inside the final pool but outside the listwise
                             window (``last_window_ids``)

Methodology follows evaluation/POOL_MISS_DIAGNOSIS.md; pool/window capture uses
the same ``RerankingEngine.last_candidate_ids`` / ``last_window_ids``
observability attributes the SSCG benchmark reads for ``pool_hit``.

Reused, not re-implemented, from the shared probe harness (probe/production
arithmetic drift is what invalidates a diagnosis):

- ``evaluation/probe_harness.py``: searcher/config lifecycle (``open_probe``),
  golden-query loading (``load_golden_queries``, no category exclusion and
  ungraded entries allowed per its own docstring — this probe diagnoses named
  queries regardless of grading status).
- ``search.search_executor.leg_search_depth`` / ``fused_pool_cut`` for
  ``search_k``/``hop1_cut`` at the hop-1-widened ``hop1_k`` — never a
  re-derived ``max(reranker_budget, hop1_k * 5)`` literal. The
  ``hop1_k = k * multi_hop.initial_k_multiplier`` widening itself has no
  harness equivalent (``ProbeSession.replay_legs`` takes whatever ``k`` it is
  given verbatim) and stays local, matching ``probe_leg_depth_fusion.py``'s
  identical judgment call.

  This migration surfaced exactly the drift ``probe_harness``'s own module
  docstring warns about: at migration time (2026-08-17) this project's live
  *base* ``search_config.json`` (not the ADR-0014 ``search_overrides.json``
  layer, which carries no ``search_mode`` key) pinned
  ``leg_search_multiplier=1`` (not the dataclass default 5), so the
  pre-migration hardcoded ``* 5`` reported ``search_k=100`` for a k=10 query
  while the actual deployed funnel ran ``search_k=30`` — a real, silent
  numeric bug in the retired hand-copied formula, not a migration
  regression. Confirmed via before/after capture against Q119/Q121/H063: only
  ``search_k`` (and classes gated on it) changed; every other field matched.
  The pin was restored to the adopted default 5 on 2026-08-18 (see ADR-0040).

This probe fetches raw legs at ``probe_depth`` once and re-cuts them at
multiple depths (``search_k``, ``probe_depth``) via its own ``fuse()``
closure, which ``ProbeSession.replay_legs`` (single depth per call) does not
support — so the raw ``executor.search_bm25``/``search_dense`` calls and the
``fuse()`` closure stay local rather than routed through ``replay_legs``.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_stable_misses.py \
        --query-ids Q119 Q121 Q122 Q133 H063 \
        [--dataset evaluation/golden_dataset_expanded.json] \
        [--project-path .] [--k 10] [--probe-depth 200] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from evaluation import probe_harness
from evaluation.metrics import normalize_chunk_id
from search.search_executor import fused_pool_cut, leg_search_depth


def rank_of(gold: str, ids: list[str]) -> int | None:
    """1-based rank of ``gold`` in ``ids``, or None when absent."""
    try:
        return ids.index(gold) + 1
    except ValueError:
        return None


def classify(
    gold: str,
    k: int,
    search_k: int,
    hop1_cut: int,
    ranks: dict[str, int | None],
    membership: dict[str, bool],
) -> str:
    """Assign the funnel-stage miss class for one gold chunk."""
    final_rank = ranks["final"]
    if final_rank is not None and final_rank <= k:
        return f"HIT@{final_rank} (run-noise if scored as miss)"
    if membership["final_pool"]:
        if membership["final_window"]:
            return "model-demotion (in listwise window, ranked out of top-k)"
        return "window-cut (in final pool, outside listwise window)"
    if membership["hop1_seeds"]:
        return "merged-cut (hop-1 seed lost in multi-hop/ego merged-pool assembly)"
    if membership["hop1_pool"]:
        return "hop1-rerank-demotion (fused pool member cut at hop-1 [:initial_k])"
    dense_r, bm25_r = ranks["dense"], ranks["bm25"]
    if dense_r is None and bm25_r is None:
        return "vocab-gap (absent from both legs at probe depth)"
    best_leg = min(r for r in (dense_r, bm25_r) if r is not None)
    if best_leg > search_k:
        return f"depth-truncation (best leg rank {best_leg} > search_k={search_k})"
    fused_r = ranks["fused_deep"]
    fused_s = str(fused_r) if fused_r is not None else f">{hop1_cut} (deep)"
    return f"rrf-arithmetic (legs within depth, fused rank {fused_s} > {hop1_cut})"


def probe_query(
    session: probe_harness.ProbeSession,
    item: probe_harness.GoldenQuery,
    k: int,
    probe_depth: int,
) -> dict[str, Any]:
    """Measure per-gold funnel positions for one golden query."""
    config = session.config
    searcher = session.searcher
    query = item.query
    grades = item.grades

    executor = searcher.search_executor
    min_score = config.search_mode.min_bm25_score
    # With multi-hop enabled, hop 1 runs at a widened k (multi_hop_searcher.py:
    # initial_k = int(k * initial_k_multiplier)), which widens search_k and the
    # hop-1 [:initial_k] seed cut with it.
    hop1_k = (
        int(k * config.multi_hop.initial_k_multiplier)
        if config.multi_hop.enabled
        else k
    )
    search_k = leg_search_depth(config, hop1_k)
    hop1_cut = fused_pool_cut(config, hop1_k)

    # Raw legs at probe depth (production depth is a prefix of these).
    bm25_deep = executor.search_bm25(query, probe_depth, min_score, None)
    dense_deep = executor.search_dense(query, probe_depth, None, None)
    bm25_ids = [normalize_chunk_id(t[0]) for t in bm25_deep]
    dense_ids = [normalize_chunk_id(t[0]) for t in dense_deep]

    weights = (config.search_mode.bm25_weight, config.search_mode.dense_weight)
    reserved = config.search_mode.bm25_reserved_slots

    def fuse(depth: int, cut: int) -> list:
        return executor.reranker.rerank_simple(
            bm25_results=bm25_deep[:depth],
            dense_results=dense_deep[:depth],
            max_results=cut,
            bm25_weight=weights[0],
            dense_weight=weights[1],
            reserved_slots=reserved,
        )

    # Production hop-1 fused pool (legs at search_k, cut at fusion_k), a deep
    # fusion for full fused-rank visibility, and the emulated hop-1 seed set:
    # the fused pool neural-reranked then cut at [:initial_k], exactly as
    # execute_single_hop does inside the hop-1 leg. (bf16 non-determinism
    # means this emulation can differ from the production pass at boundaries.)
    hop1_fused = fuse(search_k, hop1_cut)
    hop1_pool = [normalize_chunk_id(r.chunk_id) for r in hop1_fused]
    fused_deep_ids = [
        normalize_chunk_id(r.chunk_id) for r in fuse(probe_depth, probe_depth)
    ]
    reranked = searcher.reranking_engine.apply_neural_reranking(
        query, list(hop1_fused), hop1_k, context="search"
    )
    hop1_seed_ids = [normalize_chunk_id(r.chunk_id) for r in reranked[:hop1_k]]

    # Full production pipeline (multi-hop + ego + parent + listwise rerank).
    engine = getattr(searcher, "reranking_engine", None)
    if engine is not None:
        engine.last_candidate_ids = None
        engine.last_window_ids = None
    results = searcher.search(query, k=k)
    final_ids = [normalize_chunk_id(r.chunk_id) for r in results]
    pool_ids = [
        normalize_chunk_id(cid)
        for cid in (getattr(engine, "last_candidate_ids", None) or [])
    ]
    window_ids = [
        normalize_chunk_id(cid)
        for cid in (getattr(engine, "last_window_ids", None) or [])
    ]

    golds = []
    for gold, grade in sorted(grades.items(), key=lambda kv: -kv[1]):
        ranks = {
            "dense": rank_of(gold, dense_ids),
            "bm25": rank_of(gold, bm25_ids),
            "fused_deep": rank_of(gold, fused_deep_ids),
            "hop1_pool": rank_of(gold, hop1_pool),
            "hop1_seeds": rank_of(gold, hop1_seed_ids),
            "final_pool": rank_of(gold, pool_ids),
            "final": rank_of(gold, final_ids),
        }
        membership = {
            "hop1_pool": ranks["hop1_pool"] is not None,
            "hop1_seeds": ranks["hop1_seeds"] is not None,
            "final_pool": ranks["final_pool"] is not None,
            "final_window": gold in set(window_ids),
        }
        golds.append(
            {
                "gold": gold,
                "grade": grade,
                "ranks": ranks,
                "membership": membership,
                "class": classify(gold, k, search_k, hop1_cut, ranks, membership),
            }
        )

    return {
        "id": item.id,
        "query": query,
        "search_k": search_k,
        "hop1_cut": hop1_cut,
        "final_pool_size": len(pool_ids),
        "window_size": len(window_ids),
        "golds": golds,
    }


def print_report(report: dict[str, Any]) -> None:
    """Human-readable per-query table."""
    print(f"\n=== {report['id']}: {report['query']!r}")
    print(
        f"    search_k={report['search_k']} hop1_cut={report['hop1_cut']} "
        f"final_pool={report['final_pool_size']} window={report['window_size']}"
    )
    header = (
        f"{'grade':>5} {'dense':>6} {'bm25':>6} {'fused':>6} "
        f"{'hop1':>5} {'seed':>5} {'pool':>5} {'final':>6}  class / gold"
    )
    print(header)
    for g in report["golds"]:
        r = g["ranks"]

        def s(v: int | None) -> str:
            return str(v) if v is not None else "-"

        print(
            f"{g['grade']:>5} {s(r['dense']):>6} {s(r['bm25']):>6} "
            f"{s(r['fused_deep']):>6} {s(r['hop1_pool']):>5} "
            f"{s(r['hop1_seeds']):>5} {s(r['final_pool']):>5} "
            f"{s(r['final']):>6}  {g['class']}"
        )
        print(f"{'':>56}  {g['gold']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        parents=[probe_harness.probe_parser(__doc__.splitlines()[0])],
    )
    parser.add_argument("--probe-depth", type=int, default=200)
    args = parser.parse_args()
    if not args.query_ids:
        parser.error("--query-ids is required (this probe diagnoses named queries)")

    dataset_path = probe_harness.resolve_dataset_path(args.dataset)
    try:
        items = probe_harness.load_golden_queries(
            dataset_path,
            args.query_ids,
            exclude_categories=(),
            require_grades=False,
        )
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    with probe_harness.open_probe(args) as session:
        reports = []
        for item in items:
            report = probe_query(session, item, k=args.k, probe_depth=args.probe_depth)
            print_report(report)
            reports.append(report)

        if args.json_out:
            probe_harness.write_probe_json(args.json_out, reports)
    return 0


if __name__ == "__main__":
    sys.exit(main())
