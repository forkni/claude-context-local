"""Grade hard-query candidates against the live index (Track 1.2 authoring aid).

Loads evaluation/hard_query_candidates.json, runs each query through the same
searcher the SSCG benchmark uses, and prints per-query grading output:
intended-gold validity, rank in top-k, rerank-pool membership, and the top-k
normalized IDs so labels can be assigned by inspection.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/grade_candidate_queries.py \
        [--project-path F:/RD_PROJECTS/COMPONENTS/claude-context-local] \
        [--k 10] [--only Q100,Q105]
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import (  # noqa: E402
    build_chunk_line_lookup,
    normalize_chunk_id,
    normalize_chunk_ids,
)


CANDIDATES_PATH = REPO_ROOT / "evaluation" / "hard_query_candidates.json"


def build_index_id_sets(searcher) -> tuple[set[str], dict[str, list[str]]]:
    """Return (all normalized ids, trailing-name -> normalized ids) from the index."""
    lookup = build_chunk_line_lookup(searcher.dense_index.metadata_store)
    all_ids = set(lookup)
    by_name: dict[str, list[str]] = defaultdict(list)
    for norm in all_ids:
        tail = norm.rsplit(":", 1)[-1].rsplit(".", 1)[-1]
        by_name[tail].append(norm)
    return all_ids, by_name


def suggest(
    intended: str, all_ids: set[str], by_name: dict[str, list[str]]
) -> list[str]:
    """Suggest up to 5 index IDs whose trailing symbol matches the intended one."""
    tail = intended.rsplit(":", 1)[-1].rsplit(".", 1)[-1]
    hits = by_name.get(tail, [])
    if not hits:
        # substring fallback on the symbol name
        hits = [i for i in all_ids if tail.lower() in i.lower()]
    return sorted(hits)[:5]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-path", default=str(REPO_ROOT))
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument("--only", default="", help="Comma-separated query IDs to run")
    args = parser.parse_args()

    from mcp_server.search_factory import get_searcher

    print(f"Loading searcher for {args.project_path} ...", flush=True)
    searcher = get_searcher(project_path=args.project_path)
    rerank_engine = getattr(searcher, "reranking_engine", None)

    all_ids, by_name = build_index_id_sets(searcher)
    print(f"Index: {len(all_ids)} unique normalized chunk IDs\n", flush=True)

    data = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    candidates = data["candidates"]
    if args.only:
        wanted = {q.strip() for q in args.only.split(",")}
        candidates = [c for c in candidates if c["id"] in wanted]

    tally = {
        "easy": [],
        "medium": [],
        "hard": [],
        "pool_only": [],
        "pool_miss": [],
        "invalid": [],
    }

    for cand in candidates:
        qid, query = cand["id"], cand["query"]
        intended = cand["intended"]

        invalid = [i for i in intended if i not in all_ids]
        if rerank_engine is not None:
            rerank_engine.last_candidate_ids = None
        results = searcher.search(query, k=args.k)

        retrieved = []
        seen: set[str] = set()
        for r in results:
            norm = normalize_chunk_id(r.chunk_id)
            if norm not in seen:
                seen.add(norm)
                retrieved.append((norm, getattr(r, "score", 0.0)))

        pool_ids: set[str] = set()
        if rerank_engine is not None and rerank_engine.last_candidate_ids:
            pool_ids = set(normalize_chunk_ids(rerank_engine.last_candidate_ids))

        ranks = {}
        for gold in intended:
            rank = next(
                (i + 1 for i, (norm, _) in enumerate(retrieved) if norm == gold), None
            )
            ranks[gold] = rank

        best = min((r for r in ranks.values() if r), default=None)
        valid_golds = [g for g in intended if g not in invalid]
        any_in_pool = any(g in pool_ids for g in valid_golds)

        if invalid and not valid_golds:
            bucket = "invalid"
        elif best is not None and best <= 2:
            bucket = "easy"
        elif best is not None and best <= 7:
            bucket = "medium"
        elif best is not None:
            bucket = "hard"
        elif any_in_pool:
            bucket = "pool_only"
        else:
            bucket = "pool_miss"
        tally[bucket].append(qid)

        print(f"=== {qid} [{cand['category']}] -> {bucket.upper()}")
        print(f"    Q: {query}")
        for gold in intended:
            if gold in invalid:
                print(f"    GOLD INVALID: {gold}")
                for s in suggest(gold, all_ids, by_name):
                    print(f"        suggestion: {s}")
            else:
                r = ranks[gold]
                pool = "in-pool" if gold in pool_ids else "NOT-IN-POOL"
                print(f"    GOLD rank={r if r else '-'} ({pool}): {gold}")
        print(f"    pool_size={len(pool_ids)}")
        for i, (norm, score) in enumerate(retrieved[: args.k], 1):
            marker = " <== GOLD" if norm in intended else ""
            print(f"      {i:2d}. {score:7.4f}  {norm}{marker}")
        print(flush=True)

    print("=" * 70)
    total = sum(len(v) for v in tally.values())
    print(f"SUMMARY ({total} queries)")
    for bucket, qids in tally.items():
        print(f"  {bucket:10s} {len(qids):2d}  {', '.join(qids)}")


if __name__ == "__main__":
    main()
