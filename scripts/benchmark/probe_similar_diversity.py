#!/usr/bin/env python
"""Probe file-diversity policies for ``find_similar_to_chunk`` (read-only).

The F-via-similar view scores category-F golden queries through
``HybridSearcher.find_similar_to_chunk(anchor, rerank=False)`` — a dense-only
FAISS neighbourhood lookup with no file-level diversity
(``CodeIndexManager.get_similar_chunks`` filters only the anchor itself).
When an anchor's own-file neighbours dominate the top-k, cross-file sibling
implementations (the golds for queries like Q71) are crowded out.

This probe fetches one over-deep candidate list per F query (default
fetch-k=30, matching the ``min(k*3, ntotal)`` overfetch a ``max_per_file``
implementation would use) and simulates candidate policies **client-side**
from that single list — no ``search/`` code changes:

* ``current``            — today's behaviour (top-k as returned)
* ``exclude_anchor_file`` — drop candidates from the anchor's own file
* ``max_per_file=N``     — global per-file cap of N, N in {1, 2, 3}
* ``max_anchor_file=N``  — cap only the anchor's own file at N, others uncapped

Policies are applied to the *normalized, deduplicated* candidate order —
the same representation the benchmark scores (``normalize_chunk_ids``), so
simulated ranks are directly comparable to F-via-similar benchmark rows.

The dense path reuses the anchor's stored FAISS embedding: no query encoding,
no GPU model load, ~2 ms per query. Safe to run alongside other GPU work.

Silent-failure guard: an unloaded dense index makes ``get_similar_chunks``
return empty — the probe treats an empty candidate list as a setup error
(exit 2), never as a real result.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_similar_diversity.py \
        [--dataset evaluation/golden_dataset.json] [--project-path .] \
        [--k 10] [--fetch-k 30] [--query-id Q71]

Exit code 0 when at least one policy beats ``current`` on F-mean MRR by more
than --min-gain with no per-query MRR regression beyond --max-regression
(implementation gate passes); 1 when no policy clears the gate; 2 on setup
errors.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import (  # noqa: E402
    calculate_metrics_from_results,
    normalize_chunk_id,
    normalize_chunk_ids,
)


def chunk_file(chunk_id: str) -> str:
    """Extract the file-path component from a normalized chunk ID.

    Normalized IDs are ``file_path:type:name`` with forward-slash relative
    paths; a Windows drive letter (single-char first segment) is rejoined so
    absolute IDs cannot alias to their drive letter.
    """
    parts = chunk_id.split(":")
    if len(parts[0]) == 1 and len(parts) > 1:  # drive letter, e.g. "F:/..."
        return f"{parts[0]}:{parts[1]}"
    return parts[0]


def build_anchor_lookup(searcher) -> dict[str, list[str]]:
    """Map normalized chunk IDs to raw (line-ranged) index IDs.

    Mirrors ``_build_anchor_lookup`` in ``run_sscg_benchmark.py``: golden
    ``anchor_chunk_id`` values are stored normalized, but the MetadataStore
    lookup used by ``find_similar_to_chunk`` is exact-string over raw 4-part
    IDs. Values are lists because split_block parts can normalize to the
    same ID; resolution requires exactly one.
    """
    lookup: dict[str, list[str]] = {}
    for raw_id, _ in searcher.dense_index.metadata_store.items():
        lookup.setdefault(normalize_chunk_id(raw_id), []).append(raw_id)
    return lookup


def resolve_anchor(anchor: str, anchor_lookup: dict[str, list[str]]) -> str:
    """Resolve a normalized golden anchor to its unique raw index ID (or raise)."""
    raw_ids = anchor_lookup.get(normalize_chunk_id(anchor), [])
    if len(raw_ids) != 1:
        raise ValueError(
            f"anchor_chunk_id {anchor!r} resolves to {len(raw_ids)} live chunks "
            f"(need exactly 1): {raw_ids}"
        )
    return raw_ids[0]


def apply_policy(
    candidates: list[str], anchor_file: str, policy: str, k: int
) -> list[str]:
    """Apply a diversity policy to the ordered normalized candidate list."""
    if policy == "current":
        return candidates[:k]
    if policy == "exclude_anchor_file":
        return [c for c in candidates if chunk_file(c) != anchor_file][:k]
    if policy.startswith("max_per_file="):
        cap = int(policy.split("=", 1)[1])
        counts: dict[str, int] = {}
        kept: list[str] = []
        for c in candidates:
            f = chunk_file(c)
            if counts.get(f, 0) < cap:
                counts[f] = counts.get(f, 0) + 1
                kept.append(c)
            if len(kept) == k:
                break
        return kept
    if policy.startswith("max_anchor_file="):
        cap = int(policy.split("=", 1)[1])
        anchor_seen = 0
        kept = []
        for c in candidates:
            if chunk_file(c) == anchor_file:
                if anchor_seen >= cap:
                    continue
                anchor_seen += 1
            kept.append(c)
            if len(kept) == k:
                break
        return kept
    raise ValueError(f"unknown policy: {policy}")


def gold_ranks(retrieved: list[str], expected: set[str]) -> list[int]:
    """1-based ranks of expected golds within the retrieved list."""
    return [i for i, cid in enumerate(retrieved, 1) if cid in expected]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", default="evaluation/golden_dataset.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=10, help="Scoring depth")
    parser.add_argument(
        "--fetch-k",
        type=int,
        default=30,
        help="Overfetch depth (matches the min(k*3, ntotal) implementation plan)",
    )
    parser.add_argument(
        "--query-id", default=None, help="Probe a single query instead of all F"
    )
    parser.add_argument(
        "--min-gain",
        type=float,
        default=0.01,
        help="Mean-MRR gain over current a policy must exceed to pass the gate",
    )
    parser.add_argument(
        "--max-regression",
        type=float,
        default=0.10,
        help="Largest tolerated per-query MRR drop for a gate-passing policy",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path
    try:
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    queries = [
        q
        for q in data["queries"]
        if q.get("category") == "F" and q.get("anchor_chunk_id")
    ]
    if args.query_id:
        queries = [q for q in queries if q["id"] == args.query_id]
    if not queries:
        print(
            "ERROR: no category-F queries with anchor_chunk_id found", file=sys.stderr
        )
        return 2

    from mcp_server.search_factory import get_searcher

    searcher = get_searcher(project_path=args.project_path)
    anchor_lookup = build_anchor_lookup(searcher)

    policies = [
        "current",
        "exclude_anchor_file",
        "max_per_file=1",
        "max_per_file=2",
        "max_per_file=3",
        "max_anchor_file=1",
        "max_anchor_file=2",
        "max_anchor_file=3",
    ]
    mrr_by_policy: dict[str, list[float]] = {p: [] for p in policies}
    per_query_rows: list[dict] = []

    for item in queries:
        qid = item["id"]
        anchor = item["anchor_chunk_id"]
        anchor_file = chunk_file(normalize_chunk_id(anchor))
        expected = item["expected"]
        expected_primary = item.get("expected_primary", expected)
        expected_set = set(expected)

        try:
            raw_anchor = resolve_anchor(anchor, anchor_lookup)
        except ValueError as e:
            print(f"ERROR [{qid}]: {e}", file=sys.stderr)
            return 2

        start = time.perf_counter()
        results = searcher.find_similar_to_chunk(
            raw_anchor, k=args.fetch_k, rerank=False
        )
        latency_ms = (time.perf_counter() - start) * 1000.0

        if not results:
            print(
                f"ERROR [{qid}]: empty candidate list ({latency_ms:.1f} ms) - "
                "unloaded dense index signature, not a real result",
                file=sys.stderr,
            )
            return 2

        candidates = normalize_chunk_ids([r.chunk_id for r in results])
        same_file_top_k = sum(
            1 for c in candidates[: args.k] if chunk_file(c) == anchor_file
        )

        row = {
            "qid": qid,
            "anchor_file": anchor_file,
            "same_file_top_k": same_file_top_k,
            "latency_ms": latency_ms,
            "policies": {},
        }
        for policy in policies:
            retrieved = apply_policy(candidates, anchor_file, policy, args.k)
            metrics = calculate_metrics_from_results(
                retrieved=list(retrieved),
                expected=expected,
                expected_primary=expected_primary,
            )
            row["policies"][policy] = {
                "mrr": metrics["mrr"],
                "recall@5": metrics["recall@5"],
                "hit": metrics["hit"],
                "gold_ranks": gold_ranks(retrieved, expected_set),
                "n_returned": len(retrieved),
            }
            mrr_by_policy[policy].append(metrics["mrr"])
        per_query_rows.append(row)

    # ------------------------------------------------------------------ report
    print(f"\nF-query diversity probe  (k={args.k}, fetch_k={args.fetch_k})")
    print(f"Dataset: {dataset_path.name}  |  {len(queries)} queries\n")

    header = f"{'qid':>5} {'same_file@k':>11} " + " ".join(f"{p:>19}" for p in policies)
    print(header)
    print("-" * len(header))
    for row in per_query_rows:
        cells = []
        for p in policies:
            pm = row["policies"][p]
            ranks = ",".join(map(str, pm["gold_ranks"])) or "-"
            short = ""
            if pm["n_returned"] < args.k:
                short = f"!{pm['n_returned']}"
            cells.append(f"{pm['mrr']:.3f} [{ranks}]{short}".rjust(19))
        print(f"{row['qid']:>5} {row['same_file_top_k']:>11} " + " ".join(cells))

    print()
    current_mean = sum(mrr_by_policy["current"]) / len(queries)
    print(f"{'policy':>20}  {'mean MRR':>8}  {'delta':>7}  {'regressions':>11}")
    gate_passers: list[tuple[str, float]] = []
    for p in policies:
        mean = sum(mrr_by_policy[p]) / len(queries)
        delta = mean - current_mean
        regressions = [
            (
                per_query_rows[i]["qid"],
                mrr_by_policy["current"][i] - mrr_by_policy[p][i],
            )
            for i in range(len(queries))
            if mrr_by_policy[p][i] < mrr_by_policy["current"][i]
        ]
        worst = max((d for _, d in regressions), default=0.0)
        reg_s = ", ".join(f"{q}(-{d:.2f})" for q, d in regressions) or "none"
        print(f"{p:>20}  {mean:8.4f}  {delta:+7.4f}  {reg_s}")
        if p != "current" and delta > args.min_gain and worst <= args.max_regression:
            gate_passers.append((p, delta))

    avg_latency = sum(r["latency_ms"] for r in per_query_rows) / len(per_query_rows)
    print(f"\nAvg fetch latency: {avg_latency:.1f} ms/query (dense-only, no GPU load)")

    if gate_passers:
        best = max(gate_passers, key=lambda t: t[1])
        print(
            f"\nVERDICT: gate PASSES - best policy {best[0]} "
            f"(+{best[1]:.4f} mean MRR, regressions within {args.max_regression})"
        )
        return 0
    print(
        f"\nVERDICT: gate FAILS - no policy gains >{args.min_gain} mean MRR "
        f"without a >{args.max_regression} per-query regression"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
