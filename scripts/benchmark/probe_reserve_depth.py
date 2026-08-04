#!/usr/bin/env python
"""Probe the minimal effective ``bm25_reserved_slots`` for a golden query (read-only).

``_select_with_reserve`` (``search/reranker.py``) carves reserved slots from the
fused-pool tail and fills them in **raw BM25 rank order**, skipping candidates
already present in the RRF head. A gold chunk is therefore only reachable at
reserve=N when fewer than N BM25-unique (not-in-head) candidates precede it in
the raw BM25 ranking. This probe measures that count per gold so a sweep can
target the right depth instead of guessing (the prior {3,5,8} sweep failed
because one gold sat at raw BM25 rank 19 behind a wall of unique candidates —
see ``evaluation/POOL_MISS_DIAGNOSIS.md``).

Approximation caveats (the probe is necessary-not-sufficient; sweep validates):

1. The head is captured at reserve=0. At reserve=N the RRF head shrinks to
   (pool_size - N), so the reported effective reserve is a best-case bound.
2. MEASURED 2026-07-28: ``_select_with_reserve`` injects at the *hop-1* fused
   list, but ``pool_hit`` is measured at the *final* reranker pool — and with
   the production pipeline enabled (multi-hop -> ego-graph -> parent expansion,
   ``hybrid_searcher.search`` lines 706-786), tail-injected candidates do not
   survive the reshaping. The probe predicted a reserve=3 rescue for Q12; the
   {0,3,5}x3 sweep showed pool_hit=False in 9/9 runs while aggregate MRR fell
   0.02-0.035 (see evaluation/BM25_RESERVED_SLOTS_Q12_AB_20260728.md). Treat a
   passing probe as "worth sweeping", never as a predicted rescue.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_reserve_depth.py \
        [--query-id Q12] [--dataset evaluation/golden_dataset.json] \
        [--project-path .] [--bm25-k 200] [--cap 10]

Exit code 0 when the minimal effective reserve over grade-3 golds is <= cap
(sweep is worth running), 1 when it exceeds the cap, 2 on setup errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import normalize_chunk_id  # noqa: E402


def load_query(dataset_path: Path, query_id: str) -> dict:
    """Return the golden-dataset entry for ``query_id`` (raises KeyError if absent)."""
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    for item in data["queries"]:
        if item["id"] == query_id:
            return item
    raise KeyError(f"{query_id} not found in {dataset_path}")


def capture_fused_head(searcher, query: str, k: int) -> list[str]:
    """Run one hybrid search at reserve=0 and return the normalized fused pool."""
    from evaluation.arm_overrides import apply_overrides
    from search.config import get_search_config

    # bm25_reserved_slots is not construction_baked - no reset needed on the
    # returned flag (see evaluation.arm_overrides.requires_rebuild).
    apply_overrides(get_search_config(), {"search_mode.bm25_reserved_slots": 0})
    engine = getattr(searcher, "reranking_engine", None)
    if engine is not None:
        engine.last_candidate_ids = None
    searcher.search(query, k=k)
    candidate_ids = getattr(engine, "last_candidate_ids", None) if engine else None
    if not candidate_ids:
        raise RuntimeError(
            "reranking_engine.last_candidate_ids is empty after hybrid search - "
            "is reranking enabled for this project config?"
        )
    return [normalize_chunk_id(cid) for cid in candidate_ids]


def raw_bm25_order(searcher, query: str, bm25_k: int) -> list[str]:
    """Return the pure (unfused) BM25 ranking as normalized chunk IDs.

    Calls ``SearchExecutor.search_bm25`` directly: ``searcher.search(...,
    search_mode="bm25")`` is NOT raw — ``multi_hop.enabled`` gates *before*
    the mode branch, so a bm25-mode top-level search still runs the full
    multi-hop/ego/parent pipeline and returns a reshaped, reranked list.
    """
    from search.config import get_search_config

    min_score = get_search_config().search_mode.min_bm25_score
    tuples = searcher.search_executor.search_bm25(query, bm25_k, min_score)
    return [normalize_chunk_id(t[0]) for t in tuples]


def effective_reserve(
    gold: str, head: set[str], bm25_ids: list[str]
) -> tuple[int | None, int | None]:
    """(raw_bm25_rank, reserve needed to pool ``gold``); (None, None) if unreachable.

    Needed reserve = 1 + count of not-in-head candidates strictly before the
    gold in raw BM25 order (the gold itself occupies the final reserve slot).
    A gold already in the head needs reserve 0.
    """
    if gold in head:
        return None, 0
    try:
        rank = bm25_ids.index(gold) + 1
    except ValueError:
        return None, None
    unique_before = sum(1 for cid in bm25_ids[: rank - 1] if cid not in head)
    return rank, unique_before + 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--query-id", default="Q12")
    parser.add_argument("--dataset", default="evaluation/golden_dataset.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=10, help="Hybrid search k")
    parser.add_argument("--bm25-k", type=int, default=200, help="Raw BM25 probe depth")
    parser.add_argument(
        "--cap", type=int, default=10, help="Max reserve worth sweeping"
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path
    try:
        item = load_query(dataset_path, args.query_id)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    query = item["query"]
    grades = {
        normalize_chunk_id(gid): grade
        for gid, grade in (item.get("relevance_grades") or {}).items()
    }
    if not grades:
        print(f"ERROR: {args.query_id} has no relevance_grades", file=sys.stderr)
        return 2

    from mcp_server.search_factory import get_searcher

    searcher = get_searcher(project_path=args.project_path)

    head_ids = capture_fused_head(searcher, query, k=args.k)
    head = set(head_ids)
    bm25_ids = raw_bm25_order(searcher, query, bm25_k=args.bm25_k)

    print(f"\nQuery {args.query_id}: {query!r}")
    print(f"Fused pool at reserve=0: {len(head_ids)} candidates")
    print(f"Raw BM25 leg depth: {len(bm25_ids)} candidates (k={args.bm25_k})\n")
    print(
        f"{'grade':>5}  {'in_head':>7}  {'bm25_rank':>9}  {'reserve_needed':>14}  gold"
    )

    grade3_needed: list[int] = []
    for gold, grade in sorted(grades.items(), key=lambda kv: -kv[1]):
        rank, needed = effective_reserve(gold, head, bm25_ids)
        in_head = gold in head
        rank_s = str(rank) if rank is not None else ("-" if in_head else ">bm25_k")
        needed_s = str(needed) if needed is not None else "unreachable"
        print(f"{grade:>5}  {str(in_head):>7}  {rank_s:>9}  {needed_s:>14}  {gold}")
        if grade == 3 and not in_head and needed is not None:
            grade3_needed.append(needed)

    print()
    if all(gold in head for gold, grade in grades.items() if grade == 3):
        print("All grade-3 golds already in the fused pool - no reserve needed.")
        print("VERDICT: no sweep (pool-hit already true this run; miss is run-noise)")
        return 0
    if not grade3_needed:
        print(f"No grade-3 gold reachable within the top-{args.bm25_k} BM25 leg.")
        print("VERDICT: no sweep (reserved slots cannot rescue this query)")
        return 1

    minimal = min(grade3_needed)
    print(f"Minimal effective reserve over out-of-pool grade-3 golds: {minimal}")
    if minimal > args.cap:
        print(f"VERDICT: no sweep (needed {minimal} > cap {args.cap})")
        return 1
    print(
        f"VERDICT: sweep worth running (arms: 0, {minimal}, {min(minimal + 2, args.cap)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
