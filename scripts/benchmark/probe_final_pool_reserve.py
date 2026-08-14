#!/usr/bin/env python
"""Simulate final-pool-assembly reserve variants over the golden set (read-only).

The recall campaign (2026-08-02) rejected every config-level lever; the one
remaining evidenced design is a reserve at *final* pool assembly — promoting
candidates into the last listwise window (the ~30-candidate pool built from
multi-hop top-k + ego neighbors) immediately before the final rerank, where no
downstream stage can strip them (the hop-1 fusion reserve failed exactly
because everything downstream reshaped it away — see
evaluation/BM25_RESERVED_SLOTS_Q12_AB_20260728.md).

For every golden query this probe captures, from one production search pass:

- raw dense / raw BM25 leg order (``SearchExecutor.search_dense/search_bm25``
  directly — top-level ``search_mode="bm25"`` is NOT raw, multi-hop gates
  before the mode branch);
- a deep RRF fusion for full fused-rank visibility (``rerank_simple``);
- the multi-hop *merged* rerank order (instrumented ``_run_rerank``: the
  ``rerank_by_query`` call with ``hop1_reserved_slots > 0``) — its ranks
  beyond ``[:k]`` are the merged-cut victims;
- the *final* rerank pool + window + output order (the ``hop1_reserved_slots
  == 0`` call; falls back to the merged call when ego growth skipped the
  final pass).

It then simulates reserve variants at membership level (no reranker re-runs):
inject N source candidates absent from the final window, evict the same count
from the window's pre-rerank tail (the ``_apply_hop1_reserve`` semantics).

- V1  raw-BM25 top-3 carry-forward
- V2  raw-dense top-3 carry-forward
- V3  merged-rerank ranks 11-15 protected
- V1+V3 combined
- V4  graph-hop channel top-3 (candidates with ``source == "graph_hop"`` in
  the multi-hop *merged* pool, pool order — A1's arm data showed these are
  the only channel reaching H034/H066-class golds; see
  evaluation/TRACK_A_AB_20260814.md and the A3 reopening condition)

A gold is "window-rescued" when it enters the new window; a query is
"collateral" when a gold currently *in* the window gets evicted. Membership is
the ceiling, not the win: the listwise model re-scores the whole window, so
only an A/B measures conversion (the mhexp-0.25 lesson — pool_hit gains that
never converted).

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_final_pool_reserve.py \
        [--dataset evaluation/golden_dataset_expanded.json] \
        [--project-path .] [--k 10] [--probe-depth 200] \
        [--query-ids Q121 H063 ...] [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import normalize_chunk_id  # noqa: E402


# Stable misses + boundary flappers from evaluation/STABLE_MISS_DIAGNOSIS_20260802.md.
WATCHLIST = ("Q119", "Q121", "Q122", "Q133", "H063")

VARIANT_SOURCES = (
    "v1_bm25_top3",
    "v2_dense_top3",
    "v3_merged_11_15",
    "v1_plus_v3",
    "v4_graph_hop",
)


def load_queries(dataset_path: Path, query_ids: list[str] | None) -> list[dict]:
    """Golden entries with grades; category D excluded (matches the benchmark)."""
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    queries = [
        q
        for q in data["queries"]
        if q.get("category") != "D" and q.get("relevance_grades")
    ]
    if query_ids:
        by_id = {q["id"]: q for q in queries}
        missing = [qid for qid in query_ids if qid not in by_id]
        if missing:
            raise KeyError(f"{missing} not found (or category-D) in {dataset_path}")
        return [by_id[qid] for qid in query_ids]
    return queries


def rank_of(gold: str, ids: list[str]) -> int | None:
    """1-based rank of ``gold`` in ``ids``, or None when absent."""
    try:
        return ids.index(gold) + 1
    except ValueError:
        return None


def instrument_rerank(engine) -> list[dict[str, Any]]:
    """Record every ``_run_rerank`` pass: pool, window, reranked output order.

    ``rerank_by_query`` truncates its return to ``[:k]``, hiding the reranked
    window order this probe needs (merged ranks 11+). Wrapping ``_run_rerank``
    exposes the full reordered window; a paired ``rerank_by_query`` wrapper
    tags each pass with its ``hop1_reserved_slots`` so the multi-hop merged
    call (slots > 0) is distinguishable from the final post-ego call (0) and
    from hop-1 ``apply_neural_reranking`` passes (tag None).
    """
    calls: list[dict[str, Any]] = []
    state: dict[str, int | None] = {"hop1_slots": None}
    orig_rbq = engine.rerank_by_query
    orig_run = engine._run_rerank

    def rbq_wrap(*args: Any, **kwargs: Any) -> Any:
        state["hop1_slots"] = kwargs.get("hop1_reserved_slots", 0)
        try:
            return orig_rbq(*args, **kwargs)
        finally:
            state["hop1_slots"] = None

    def run_wrap(
        query_or_content: str,
        candidates: list,
        k: int,
        log_prefix: str,
        config: Any = None,
    ) -> list:
        out = orig_run(query_or_content, candidates, k, log_prefix, config=config)
        calls.append(
            {
                "hop1_slots": state["hop1_slots"],
                "k": k,
                "pool_ids": [normalize_chunk_id(r.chunk_id) for r in candidates],
                # Provenance-preserving view of the pool: graph-hop expansion
                # candidates carry source == "graph_hop" (tested contract, see
                # test_multi_hop_searcher.py) and survive un-fused into the
                # merged pool — the v4 variant selects on this.
                "pool_sources": [
                    (normalize_chunk_id(r.chunk_id), getattr(r, "source", None))
                    for r in candidates
                ],
                "window_ids": [
                    normalize_chunk_id(cid) for cid in (engine.last_window_ids or [])
                ],
                "output_ids": [normalize_chunk_id(r.chunk_id) for r in out],
            }
        )
        return out

    engine.rerank_by_query = rbq_wrap
    engine._run_rerank = run_wrap
    return calls


def simulate_reserve(
    window_ids: list[str], source_ids: list[str], cap: int
) -> tuple[list[str], list[str], list[str]]:
    """(new_window, injected, evicted) under `_apply_hop1_reserve` semantics.

    Injects source candidates absent from the window; evicts the same count
    from the window's pre-rerank tail once the ``cap`` is exceeded.
    """
    window_set = set(window_ids)
    injected = [c for c in source_ids if c not in window_set]
    evict_count = max(0, len(window_ids) + len(injected) - cap)
    kept = window_ids[: len(window_ids) - evict_count] if evict_count else window_ids
    evicted = window_ids[len(window_ids) - evict_count :] if evict_count else []
    return list(kept) + injected, injected, evicted


def probe_query(searcher, item: dict, k: int, probe_depth: int) -> dict[str, Any]:
    """Capture funnel positions + run reserve simulations for one query."""
    from search.config import get_search_config

    config = get_search_config()
    query = item["query"]
    grades = {
        normalize_chunk_id(gid): grade
        for gid, grade in item["relevance_grades"].items()
    }
    cap = config.reranker.top_k_candidates

    executor = searcher.search_executor
    min_score = config.search_mode.min_bm25_score
    bm25_deep = executor.search_bm25(query, probe_depth, min_score)
    dense_deep = executor.search_dense(query, probe_depth, None)
    bm25_ids = [normalize_chunk_id(t[0]) for t in bm25_deep]
    dense_ids = [normalize_chunk_id(t[0]) for t in dense_deep]
    fused_deep = executor.reranker.rerank_simple(
        bm25_results=bm25_deep,
        dense_results=dense_deep,
        max_results=probe_depth,
        bm25_weight=config.search_mode.bm25_weight,
        dense_weight=config.search_mode.dense_weight,
        reserved_slots=config.search_mode.bm25_reserved_slots,
    )
    fused_ids = [normalize_chunk_id(r.chunk_id) for r in fused_deep]

    engine = searcher.reranking_engine
    calls = getattr(engine, "_probe_rerank_calls", None)
    if calls is None:
        calls = instrument_rerank(engine)
        engine._probe_rerank_calls = calls
    calls.clear()

    results = searcher.search(query, k=k)
    final_ids = [
        normalize_chunk_id(getattr(r, "chunk_id", None) or r["chunk_id"])
        for r in results
    ]

    rbq_calls = [c for c in calls if c["hop1_slots"] is not None]
    merged_calls = [c for c in rbq_calls if c["hop1_slots"] > 0]
    final_calls = [c for c in rbq_calls if c["hop1_slots"] == 0]
    merged = merged_calls[-1] if merged_calls else None
    final = final_calls[-1] if final_calls else merged
    if final is None:
        # Degenerate path (no rerank_by_query fired) — nothing to simulate.
        return {
            "id": item["id"],
            "category": item.get("category", "?"),
            "query": query,
            "degenerate": True,
            "golds": [
                {"gold": g, "grade": gr, "final_rank": rank_of(g, final_ids)}
                for g, gr in grades.items()
            ],
            "variants": {},
        }

    window = final["window_ids"]
    window_set = set(window)
    merged_out = merged["output_ids"] if merged else []

    golds = []
    for gold, grade in sorted(grades.items(), key=lambda kv: -kv[1]):
        golds.append(
            {
                "gold": gold,
                "grade": grade,
                "dense_rank": rank_of(gold, dense_ids),
                "bm25_rank": rank_of(gold, bm25_ids),
                "fused_rank": rank_of(gold, fused_ids),
                "merged_pool_rank": rank_of(gold, merged["pool_ids"])
                if merged
                else None,
                "merged_out_rank": rank_of(gold, merged_out) if merged else None,
                "final_pool_rank": rank_of(gold, final["pool_ids"]),
                "in_final_window": gold in window_set,
                "final_rank": rank_of(gold, final_ids),
            }
        )

    best_final = min(
        (g["final_rank"] for g in golds if g["final_rank"] is not None),
        default=None,
    )
    currently_hit = best_final is not None and best_final <= k

    # Graph-hop channel: pool order is the ranking proxy — graph candidates all
    # score 0.0 under the current default (A1 not adopted), so the merged pool's
    # stable sort preserves discovery order.
    graph_hop_ids = [
        cid
        for cid, source in (merged["pool_sources"] if merged else [])
        if source == "graph_hop"
    ]

    sources = {
        "v1_bm25_top3": bm25_ids[:3],
        "v2_dense_top3": dense_ids[:3],
        "v3_merged_11_15": merged_out[k : k + 5],
        "v1_plus_v3": bm25_ids[:3] + merged_out[k : k + 5],
        "v4_graph_hop": graph_hop_ids[:3],
    }
    variants: dict[str, Any] = {}
    for name, source in sources.items():
        new_window, injected, evicted = simulate_reserve(window, source, cap)
        new_set = set(new_window)
        rescued = [
            {"gold": g["gold"], "grade": g["grade"]}
            for g in golds
            if not g["in_final_window"] and g["gold"] in new_set
        ]
        evicted_golds = [
            {"gold": g["gold"], "grade": g["grade"]}
            for g in golds
            if g["in_final_window"] and g["gold"] in set(evicted)
        ]
        variants[name] = {
            "injected": injected,
            "evicted_count": len(evicted),
            "rescued_golds": rescued,
            "evicted_golds": evicted_golds,
        }

    return {
        "id": item["id"],
        "category": item.get("category", "?"),
        "query": query,
        "currently_hit": currently_hit,
        "best_final_rank": best_final,
        "window_size": len(window),
        "merged_pool_size": len(merged["pool_ids"]) if merged else None,
        "final_pool_size": len(final["pool_ids"]),
        "had_final_pass": bool(final_calls),
        "golds": golds,
        "variants": variants,
    }


def summarize(reports: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate rescue/collateral counts per variant."""
    summary: dict[str, Any] = {}
    for name in VARIANT_SOURCES:
        rescued_q: list[str] = []
        rescued_miss_q: list[str] = []
        rescued_miss_no_final_q: list[str] = []
        rescued_watch: list[str] = []
        collateral_q: list[str] = []
        for rep in reports:
            var = rep.get("variants", {}).get(name)
            if not var:
                continue
            if var["rescued_golds"]:
                rescued_q.append(rep["id"])
                if not rep.get("currently_hit", False):
                    rescued_miss_q.append(rep["id"])
                    # Stratified gate (A3): the simulation targets the FINAL
                    # call's window, but a merged-call-only reserve build can
                    # only deliver rescues on queries where the merged output
                    # IS final (no separate post-ego rerank ran). Rescues on
                    # had_final_pass=True queries require also threading the
                    # reserve through the hybrid_searcher final call sites.
                    if not rep.get("had_final_pass", True):
                        rescued_miss_no_final_q.append(rep["id"])
                if rep["id"] in WATCHLIST:
                    rescued_watch.append(rep["id"])
            if var["evicted_golds"] and rep.get("currently_hit", False):
                collateral_q.append(rep["id"])
        summary[name] = {
            "queries_with_rescued_gold": rescued_q,
            "currently_miss_rescued": rescued_miss_q,
            "currently_miss_rescued_no_final_pass": rescued_miss_no_final_q,
            "watchlist_rescued": rescued_watch,
            "collateral_hit_queries": collateral_q,
        }
    return summary


def print_summary(reports: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    """Human-readable rollup + watch-list sanity block."""
    print(f"\n=== Final-pool reserve simulation over {len(reports)} queries ===")
    print(
        f"{'variant':<18} {'any_rescue':>10} {'miss_rescue':>11} "
        f"{'watchlist':>9} {'collateral':>10}"
    )
    for name in VARIANT_SOURCES:
        s = summary[name]
        print(
            f"{name:<18} {len(s['queries_with_rescued_gold']):>10} "
            f"{len(s['currently_miss_rescued']):>11} "
            f"{len(s['watchlist_rescued']):>9} "
            f"{len(s['collateral_hit_queries']):>10}"
        )
    for name in VARIANT_SOURCES:
        s = summary[name]
        print(f"\n{name}:")
        print(f"  miss-rescued: {', '.join(s['currently_miss_rescued']) or '-'}")
        print(
            "  ^ no-final-pass (merged-only build reachable): "
            + (", ".join(s["currently_miss_rescued_no_final_pass"]) or "-")
        )
        print(f"  watchlist:    {', '.join(s['watchlist_rescued']) or '-'}")
        print(f"  collateral:   {', '.join(s['collateral_hit_queries']) or '-'}")

    print("\n=== Watch-list funnel detail (sanity vs STABLE_MISS_DIAGNOSIS) ===")
    by_id = {rep["id"]: rep for rep in reports}
    for qid in WATCHLIST:
        rep = by_id.get(qid)
        if rep is None:
            continue
        print(f"\n{qid}: {rep['query']!r}")
        print(
            f"{'grade':>5} {'dense':>6} {'bm25':>6} {'fused':>6} {'mrg_out':>7} "
            f"{'pool':>5} {'window':>6} {'final':>6}  gold"
        )
        for g in rep.get("golds", []):

            def s(v: int | None) -> str:
                return str(v) if v is not None else "-"

            print(
                f"{g['grade']:>5} {s(g.get('dense_rank')):>6} "
                f"{s(g.get('bm25_rank')):>6} {s(g.get('fused_rank')):>6} "
                f"{s(g.get('merged_out_rank')):>7} "
                f"{s(g.get('final_pool_rank')):>5} "
                f"{str(g.get('in_final_window', '-')):>6} "
                f"{s(g.get('final_rank')):>6}  {g['gold']}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", default="evaluation/golden_dataset_expanded.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--probe-depth", type=int, default=200)
    parser.add_argument("--query-ids", nargs="*", default=None)
    parser.add_argument("--json", dest="json_out", default=None)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path
    try:
        items = load_queries(dataset_path, args.query_ids)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    from mcp_server.search_factory import get_searcher

    searcher = get_searcher(project_path=args.project_path)

    reports = []
    for i, item in enumerate(items, 1):
        print(f"[{i:3d}/{len(items)}] {item['id']}", flush=True)
        reports.append(
            probe_query(searcher, item, k=args.k, probe_depth=args.probe_depth)
        )

    summary = summarize(reports)
    print_summary(reports, summary)

    if args.json_out:
        payload = {"summary": summary, "reports": reports}
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nJSON written to {args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
