#!/usr/bin/env python
"""Probe whether hop-1 top-10 golds survive the multi-hop rerank window cut (read-only).

Background: ``evaluation/QUERY_EXPANSION_AB_20260728.md`` (root-cause section) observed
golden-set queries Q104/Q122 ranking 1 and 6 out of hop-1 (``MultiHopSearcher``), reaching
the merged expansion pool (~66-83 chunks at k=10), yet missing the final top-10. This probe
instruments the exact boundary between "gold is in the merged pool" and "gold is in the
window the listwise reranker actually scores" to distinguish three failure modes:

- **window-cut**: gold is in the merged pool (``multi_hop_searcher.py:478``) but falls
  outside ``candidates[:top_k_candidates]`` at the hard cut (``reranking_engine.py:217``) —
  the model never sees it.
- **model-demotion**: gold is inside the window but the listwise model still ranks it > k.
- **pool-loss**: gold never reached the merged pool at all (a pre-existing retrieval gap,
  out of scope for this probe).

Mechanism (three incomparable score scales feed the ``:270`` sort that determines the cut):
hop-1 survivors carry a jina relevance score overwritten in place
(``neural_reranker.py:1117-1119``, range observed ~+0.22..-0.12); semantic-expansion chunks
carry raw FAISS cosine (``multi_hop_searcher.py:141``, ~0.5-0.9); graph-expansion chunks carry
literal ``0.0`` (``multi_hop_searcher.py:227``). Sorting all three together at the merge-pool
rerank means cosine-scored expansion chunks systematically outrank hop-1 winners.

Instrumentation (in-probe monkeypatching only — nothing lands in ``search/``):

- ``MultiHopSearcher._single_hop_search`` wrapped to capture the hop-1 output list (order =
  hop-1 rank).
- ``RerankingEngine.rerank_by_query`` wrapped to capture its incoming ``results`` argument
  before the internal sort — this is the merged pool at ``multi_hop_searcher.py:478`` for the
  first call, and the ego-graph tail's pool for any subsequent call
  (``hybrid_searcher.py:768/781``).
- ``RerankingEngine._run_rerank`` wrapped to capture ``candidates[:rerank_count]`` (the
  window actually scored) and the boundary candidate's score. Hop-1's own rerank pass
  (``SearchExecutor.apply_neural_reranking``) uses the distinct log_prefix
  ``"[NEURAL_RERANK-SEARCH]"``; only ``"[NEURAL_RERANK]"``-tagged calls (from
  ``rerank_by_query``) are attributed to the merge-pool / ego-tail stages, in call order.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --query-id Q104,Q122 --dataset evaluation/golden_dataset_expanded.json --k 10

    .venv/Scripts/python.exe scripts/benchmark/probe_rerank_window.py \
        --all --dataset evaluation/golden_dataset_expanded.json --k 10

Exit code 0 (green) when every grade-3 gold that is inside hop-1 top-10 is also inside the
merge-pool rerank window; 1 (red) when at least one such gold is window-cut; 2 on setup errors.
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


MERGE_LOG_PREFIX = "[NEURAL_RERANK]"


def load_queries(dataset_path: Path, query_ids: list[str] | None) -> list[dict]:
    """Return golden-dataset entries, optionally filtered to ``query_ids``.

    Excludes category D (call-graph queries this probe's plain ``search()`` call cannot
    evaluate, matching the benchmark harness default) and category F (scored via
    ``find_similar_code`` anchors, a different pipeline this probe does not exercise).
    """
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    items = [q for q in data["queries"] if q.get("category") not in ("D", "F")]
    if query_ids:
        wanted = set(query_ids)
        items = [q for q in items if q["id"] in wanted]
        missing = wanted - {q["id"] for q in items}
        if missing:
            raise KeyError(
                f"query id(s) not found (or excluded D/F): {sorted(missing)}"
            )
    return items


class Instrumentation:
    """Installs/removes monkeypatches on MultiHopSearcher and RerankingEngine classes."""

    def __init__(self, searcher) -> None:
        self._multi_hop_searcher = searcher.multi_hop_searcher
        self._engine_cls = type(searcher.reranking_engine)
        # _single_hop_search is a per-instance bound-callback attribute set in
        # MultiHopSearcher.__init__ (single_hop_callback=self._single_hop_search from
        # HybridSearcher), not a class method - must patch the instance, not the class.
        self._orig_single_hop = self._multi_hop_searcher._single_hop_search
        self._orig_rerank_by_query = self._engine_cls.rerank_by_query
        self._orig_run_rerank = self._engine_cls._run_rerank
        self.reset()

    def reset(self) -> None:
        self.hop1_ids: list[str] | None = None
        self.rerank_by_query_calls: list[dict] = []
        self.run_rerank_calls: list[dict] = []

    def install(self) -> None:
        instrumentation = self
        orig_single_hop = self._orig_single_hop
        orig_rerank_by_query = self._orig_rerank_by_query
        orig_run_rerank = self._orig_run_rerank

        def patched_single_hop(*args, **kwargs):
            # orig_single_hop is already a bound method (HybridSearcher._single_hop_search
            # bound to the live searcher instance) - no self_searcher param to thread through.
            result = orig_single_hop(*args, **kwargs)
            instrumentation.hop1_ids = [normalize_chunk_id(r.chunk_id) for r in result]
            return result

        def patched_rerank_by_query(self_engine, query, results, k, *args, **kwargs):
            instrumentation.rerank_by_query_calls.append(
                {
                    "pool_ids": [normalize_chunk_id(r.chunk_id) for r in results],
                    "scores": {
                        normalize_chunk_id(r.chunk_id): r.score for r in results
                    },
                    "sources": {
                        normalize_chunk_id(r.chunk_id): getattr(r, "source", "unknown")
                        for r in results
                    },
                    "hop1_reserved_slots": kwargs.get(
                        "hop1_reserved_slots", args[1] if len(args) > 1 else 0
                    ),
                }
            )
            return orig_rerank_by_query(self_engine, query, results, k, *args, **kwargs)

        def patched_run_rerank(
            self_engine, query_or_content, candidates, k, log_prefix, config=None
        ):
            if config is None:
                from search.config import get_search_config

                config = get_search_config()
            rerank_count = min(config.reranker.top_k_candidates, len(candidates))
            window = candidates[:rerank_count]
            instrumentation.run_rerank_calls.append(
                {
                    "log_prefix": log_prefix,
                    "candidate_ids": [
                        normalize_chunk_id(c.chunk_id) for c in candidates
                    ],
                    "window_ids": [normalize_chunk_id(c.chunk_id) for c in window],
                    "rerank_count": rerank_count,
                    "boundary_score": window[-1].score if window else None,
                }
            )
            return orig_run_rerank(
                self_engine, query_or_content, candidates, k, log_prefix, config=config
            )

        self._multi_hop_searcher._single_hop_search = patched_single_hop
        self._engine_cls.rerank_by_query = patched_rerank_by_query
        self._engine_cls._run_rerank = patched_run_rerank

    def uninstall(self) -> None:
        self._multi_hop_searcher._single_hop_search = self._orig_single_hop
        self._engine_cls.rerank_by_query = self._orig_rerank_by_query
        self._engine_cls._run_rerank = self._orig_run_rerank

    def merge_pool_call(self) -> dict | None:
        """The multi-hop merge-pool rerank_by_query call (index 0), if it ran."""
        return self.rerank_by_query_calls[0] if self.rerank_by_query_calls else None

    def merge_pool_window(self) -> dict | None:
        """The [NEURAL_RERANK]-tagged _run_rerank call matching the merge pool (index 0)."""
        tagged = [
            c for c in self.run_rerank_calls if c["log_prefix"] == MERGE_LOG_PREFIX
        ]
        return tagged[0] if tagged else None


def classify_query(
    instr: Instrumentation, gold_ids: dict[str, int], final_ids: list[str]
) -> list[dict]:
    """Per grade-3 gold: hop1_rank, in_merged_pool, in_rerank_window, final_rank, score/source."""
    hop1_ids = instr.hop1_ids or []
    merge_call = instr.merge_pool_call()
    window_call = instr.merge_pool_window()
    pool_ids = set(merge_call["pool_ids"]) if merge_call else set()
    window_ids = set(window_call["window_ids"]) if window_call else set()
    rows = []
    for gold, grade in sorted(gold_ids.items(), key=lambda kv: -kv[1]):
        if grade != 3:
            continue
        hop1_rank = hop1_ids.index(gold) + 1 if gold in hop1_ids else None
        in_pool = gold in pool_ids
        in_window = gold in window_ids
        final_rank = final_ids.index(gold) + 1 if gold in final_ids else None
        score = merge_call["scores"].get(gold) if merge_call else None
        source = merge_call["sources"].get(gold) if merge_call else None
        if hop1_rank is not None and hop1_rank <= 10 and in_pool and not in_window:
            classification = "window-cut"
        elif (
            hop1_rank is not None
            and hop1_rank <= 10
            and in_window
            and (final_rank is None or final_rank > 10)
        ):
            classification = "model-demotion"
        elif not in_pool:
            classification = "pool-loss"
        else:
            classification = "ok"
        rows.append(
            {
                "gold": gold,
                "hop1_rank": hop1_rank,
                "in_merged_pool": in_pool,
                "in_rerank_window": in_window,
                "final_rank": final_rank,
                "score": score,
                "source": source,
                "classification": classification,
            }
        )
    return rows


def print_query_report(
    query_id: str, query_text: str, instr: Instrumentation, rows: list[dict]
) -> None:
    merge_call = instr.merge_pool_call()
    window_call = instr.merge_pool_window()
    print(f"\nQuery {query_id}: {query_text!r}")
    if merge_call is None:
        print(
            "  (no rerank_by_query call observed - single_pass or multi_hop disabled?)"
        )
    else:
        print(f"  Merged pool size: {len(merge_call['pool_ids'])}")
        if window_call is not None:
            print(
                f"  Rerank window: {window_call['rerank_count']} "
                f"(boundary score={window_call['boundary_score']})"
            )
            hist: dict[str, int] = {}
            for cid in window_call["window_ids"]:
                src = merge_call["sources"].get(cid, "unknown")
                hist[src] = hist.get(src, 0) + 1
            print(f"  Window source histogram: {hist}")
    print(
        f"  {'grade':>5}  {'hop1_rank':>9}  {'in_pool':>7}  {'in_window':>9}  "
        f"{'final_rank':>10}  {'score':>8}  {'source':>10}  class"
    )
    for row in rows:
        hop1_s = str(row["hop1_rank"]) if row["hop1_rank"] is not None else "-"
        final_s = str(row["final_rank"]) if row["final_rank"] is not None else "miss"
        score_s = f"{row['score']:.3f}" if row["score"] is not None else "-"
        source_s = row["source"] or "-"
        print(
            f"  {3:>5}  {hop1_s:>9}  {str(row['in_merged_pool']):>7}  "
            f"{str(row['in_rerank_window']):>9}  {final_s:>10}  {score_s:>8}  "
            f"{source_s:>10}  {row['classification']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--query-id", default="Q104,Q122", help="Comma-separated query IDs"
    )
    parser.add_argument("--all", action="store_true", help="Sweep all non-D/F queries")
    parser.add_argument("--dataset", default="evaluation/golden_dataset_expanded.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=10)
    parser.add_argument(
        "--hop1-reserved-slots",
        type=int,
        default=None,
        help=(
            "Override reranker.hop1_reserved_slots in the in-memory config for "
            "this run (fix verification arm). Default: use config value. "
            "Sugar for --set reranker.hop1_reserved_slots=<value>."
        ),
    )
    parser.add_argument(
        "--set",
        dest="set_overrides",
        action="append",
        metavar="section.field=value",
        help=(
            "Override an arbitrary SearchConfig field for this run, e.g. "
            "'--set reranker.top_k_candidates=33'. Repeatable; later "
            "duplicates win. Routed through evaluation.arm_overrides - value "
            "is coerced to the field's declared type and validated against "
            "its spec(range=...)/choices=... before anything is mutated."
        ),
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path

    query_ids = (
        None if args.all else [q.strip() for q in args.query_id.split(",") if q.strip()]
    )
    try:
        items = load_queries(dataset_path, query_ids)
    except (OSError, KeyError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if not items:
        print("ERROR: no queries selected", file=sys.stderr)
        return 2

    from evaluation.arm_overrides import (
        ArmOverrideError,
        apply_overrides,
        parse_set_flags,
    )

    try:
        overrides = parse_set_flags(args.set_overrides)
        if args.hop1_reserved_slots is not None:
            overrides["reranker.hop1_reserved_slots"] = args.hop1_reserved_slots
    except ArmOverrideError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Apply before constructing the searcher: this probe builds one searcher
    # per run (no cached-searcher reset path), so any construction_baked
    # field only takes effect if it is set first.
    if overrides:
        from search.config import get_search_config

        try:
            apply_overrides(get_search_config(), overrides)
        except ArmOverrideError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(f"[OVERRIDE] {overrides}")

    from mcp_server.search_factory import get_searcher

    searcher = get_searcher(project_path=args.project_path)

    instr = Instrumentation(searcher)
    instr.install()

    window_cut_count = 0
    model_demotion_count = 0
    pool_loss_count = 0
    ok_count = 0
    any_red = False

    try:
        for item in items:
            query_id = item["id"]
            query_text = item["query"]
            grades = {
                normalize_chunk_id(gid): grade
                for gid, grade in (item.get("relevance_grades") or {}).items()
            }
            grade3 = {g: gr for g, gr in grades.items() if gr == 3}
            if not grade3:
                continue

            instr.reset()
            final_results = searcher.search(query_text, k=args.k)
            final_ids = [normalize_chunk_id(r.chunk_id) for r in final_results]

            rows = classify_query(instr, grades, final_ids)
            print_query_report(query_id, query_text, instr, rows)

            for row in rows:
                if row["classification"] == "window-cut":
                    window_cut_count += 1
                    any_red = True
                elif row["classification"] == "model-demotion":
                    model_demotion_count += 1
                elif row["classification"] == "pool-loss":
                    pool_loss_count += 1
                else:
                    ok_count += 1
    finally:
        instr.uninstall()

    print(
        f"\nTotals: window-cut={window_cut_count} model-demotion={model_demotion_count} "
        f"pool-loss={pool_loss_count} ok={ok_count}"
    )

    if any_red:
        print(
            f"VERDICT: RED - {window_cut_count} grade-3 gold(s) window-cut at k={args.k}"
        )
        return 1
    print(f"VERDICT: GREEN - no window-cuts observed at k={args.k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
