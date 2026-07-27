#!/usr/bin/env python3
"""Search-latency phase profiling (measure-only, no production code changes).

Drives the *real* search path — `mcp_server.tools.search_handlers.
handle_search_code`, the same entry point the `search_code` MCP tool calls —
and times four specific sites inside it by monkey-patching them in this
process only. No file under `search/`, `graph/`, or `mcp_server/` is modified.

Why this script exists (search-latency plan, "remove CPU-side waste, close
one lock gap"): `scripts/benchmark/run_sscg_benchmark.py --with-centrality`
already times all four sites end-to-end, but its replicate spread is ~68ms
(the fp16 listwise reranker is nondeterministic run-to-run — no
`torch.manual_seed`/`use_deterministic_algorithms` anywhere in that path),
which swamps three of the four individually. This script isolates each site
with its own `time.perf_counter()` wrapper so its cost is visible against the
noise floor, independent of reranker jitter.

The four attributed sites:
  1. `MetadataStore.get` (Fix 2 — one-op sentinel-based get, `outer_stack=False`)
  2. `GraphQueryEngine.compute_centrality` / `CentralityRanker.get_centrality_scores`
     (Fix 3 — the centrality memo repair; this is the largest measured win)
  3. `GraphScoringStage._extract_subgraph` (Fix 4 — skipped when the caller
     will discard it, i.e. `include_subgraph=False`)
  4. `SearchOrchestrator._assemble` (Fix 5 — the block whose scope moves
     inside the reindex read lock; not a CPU-cost fix, but timed here so its
     wall-clock share and stability are visible before/after the lock change)

`RerankingEngine.rerank_by_query` is also timed, unpatched, purely as
background context — it is explicitly OUT of scope (~80% of wall-clock,
buys ranking quality; "we do not trade speed for accuracy").

Layer 1 (phase wall-clock attribution) only — this script has no cProfile
layer and no GPU/CPU split; those are file-index-profiling concerns
(`profile_full_index.py`) not applicable to the CPU-side waste this measures.

Reused from `profile_full_index.py`: the `_Recorder` / `_timed_wrap` pattern
and the warm-up-then-N-timed-runs / median-of-clean-runs structure. Reused
from `utils/timing.py`: none directly (that module's `@timed`/`timer` log
through the `logging` module rather than an in-process recorder, which
would require parsing log lines to attribute per-phase totals — the
`_timed_wrap` monkey-patch approach used here and in `profile_full_index.py`
is more direct for this measurement).

Usage:
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_search_latency.py
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_search_latency.py --runs 8
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_search_latency.py --project /path/to/other/repo
    .venv/Scripts/python.exe scripts/benchmark/profiling/profile_search_latency.py --queries "auth flow" "embedding cache"
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import json
import logging
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def _check_venv() -> None:
    """Fail fast if not running inside the project .venv."""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    if not in_venv:
        print(
            "ERROR: Run from .venv to ensure all dependencies are available.\n"
            "       Use: .venv/Scripts/python.exe scripts/benchmark/profiling/profile_search_latency.py",
            file=sys.stderr,
        )
        sys.exit(1)


# Representative queries exercising this repo's own indexed code. Chosen to
# hit both a graph-rich area (call-graph/centrality/search internals) and a
# plainer one (config/metadata), so the profiled phases aren't an artifact of
# one unusually graph-dense query.
_DEFAULT_QUERIES = [
    "semantic search embedding function",
    "centrality ranking pagerank computation",
    "chunk metadata storage sqlite",
    "graph scoring stage subgraph extraction",
    "reindex read write lock",
    "hybrid searcher rerank fusion",
    "neural reranker cross encoder",
    "merkle dag file hashing",
]


# ---------------------------------------------------------------------------
# Recorder — collects (phase_name -> [duration, ...]) for the CURRENT run.
# A fresh Recorder is installed per run; wrapper closures below always read
# the module-level `_recorder` at call time, not at patch time.
# ---------------------------------------------------------------------------


class _Recorder:
    def __init__(self) -> None:
        self.times: dict[str, list[float]] = defaultdict(list)

    def record(self, name: str, elapsed: float) -> None:
        self.times[name].append(elapsed)

    def total(self, name: str) -> float:
        return sum(self.times.get(name, []))

    def count(self, name: str) -> int:
        return len(self.times.get(name, []))


_recorder: _Recorder | None = None


def _record(name: str, elapsed: float) -> None:
    if _recorder is not None:
        _recorder.record(name, elapsed)


def _timed_wrap(obj: Any, attr_name: str, phase_name: str) -> bool:
    """Patch obj.attr_name with a perf_counter wrapper recording under phase_name.

    Works uniformly for module-level functions (obj=module) and class methods
    (obj=class — getattr/setattr operate on the plain function, so instance
    calls still pass `self` through *args correctly).

    `orig` may be a coroutine function (e.g. `SearchOrchestrator._search`) —
    calling it only *creates* a coroutine object without running its body, so
    a plain synchronous wrapper would measure near-zero (the coroutine object
    construction), and the real cost would be attributed to whatever line
    later `await`s it instead. Detected via `asyncio.iscoroutinefunction` and
    given an async wrapper that awaits `orig` inside the timed span.

    Returns False (and logs a warning instead of raising) if attr_name isn't
    found — some targets are optional (e.g. graph-enhanced features may be
    unavailable if the project has no graph_storage).
    """
    if not hasattr(obj, attr_name):
        print(
            f"[WARN] Cannot wrap {obj!r}.{attr_name} — attribute not found",
            file=sys.stderr,
        )
        return False

    orig = getattr(obj, attr_name)

    if asyncio.iscoroutinefunction(orig):

        @functools.wraps(orig)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            try:
                return await orig(*args, **kwargs)
            finally:
                _record(phase_name, time.perf_counter() - t0)

        setattr(obj, attr_name, async_wrapper)
        return True

    @functools.wraps(orig)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        t0 = time.perf_counter()
        try:
            return orig(*args, **kwargs)
        finally:
            _record(phase_name, time.perf_counter() - t0)

    setattr(obj, attr_name, wrapper)
    return True


def _install_patches() -> None:
    from graph.graph_queries import GraphQueryEngine
    from mcp_server.tools.search_orchestrator import SearchOrchestrator
    from search.centrality_ranker import CentralityRanker
    from search.graph_scoring_stage import GraphScoringStage
    from search.metadata import MetadataStore
    from search.reranking_engine import RerankingEngine

    # Fix 2 — MetadataStore one-op get.
    _timed_wrap(MetadataStore, "get", "metadata_get")

    # Fix 3 — centrality memo repair (both the outer cached-facing call and
    # the raw nx.pagerank/DiGraph-copy computation it wraps, so a future
    # memo hit is visible as get_scores time collapsing toward zero while
    # centrality_compute stays flat or drops to nothing).
    _timed_wrap(CentralityRanker, "get_centrality_scores", "centrality_get_scores")
    _timed_wrap(GraphQueryEngine, "compute_centrality", "centrality_compute")

    # Fix 4 — discarded subgraph extraction when include_subgraph=False.
    _timed_wrap(GraphScoringStage, "_extract_subgraph", "subgraph_extract")

    # Fix 5 — the block whose scope moves inside the reindex read lock.
    # `_execute` no longer exists (search-latency plan Fix 5 split it): Block A
    # is now `_maybe_reindex` (its own write-lock scope, outside the read
    # lock), Blocks B-D are `_search` (runs under the read lock, alongside
    # `_assemble` after the ADR-0008 amendment).
    _timed_wrap(SearchOrchestrator, "_assemble", "assemble")
    _timed_wrap(SearchOrchestrator, "_maybe_reindex", "maybe_reindex")
    _timed_wrap(SearchOrchestrator, "_search", "search")

    # Background context only — NOT a fix target (~80% of wall-clock, buys
    # ranking quality; explicitly out of scope per "we do not trade speed
    # for accuracy").
    _timed_wrap(RerankingEngine, "rerank_by_query", "rerank")


_PHASE_NAMES = [
    "metadata_get",
    "centrality_get_scores",
    "centrality_compute",
    "subgraph_extract",
    "assemble",
    "maybe_reindex",
    "search",
    "rerank",
]


def _print_phase_table(recorder: _Recorder, total_wall: float) -> None:
    print()
    print("=" * 78)
    print("PHASE WALL-CLOCK (this run, summed across all queries)")
    print("=" * 78)
    print(f"{'Phase':<26} {'seconds':>10} {'% total':>9} {'calls':>7} {'avg ms':>9}")
    print("-" * 78)
    for name in _PHASE_NAMES:
        t = recorder.total(name)
        n = recorder.count(name)
        pct = (t / total_wall * 100) if total_wall > 0 else 0.0
        avg_ms = (t / n * 1000) if n else 0.0
        print(f"{name:<26} {t:>10.3f} {pct:>8.1f}% {n:>7} {avg_ms:>8.2f}")
    print("-" * 78)
    print(f"{'TOTAL (query loop wall-clock)':<26} {total_wall:>10.3f} {'100.0%':>9}")


async def _run_query_set(
    queries: list[str], k: int
) -> tuple[float, list[dict[str, Any]]]:
    """Run every query once, sequentially, inside the current event loop.

    Sequential and single-event-loop by design: `SearchOrchestrator._execute`
    acquires `ApplicationState.get_reindex_rwlock(...)`, whose `asyncio.
    Condition` is created on first use and bound to that loop for its
    lifetime (mcp_server/state.py). Calling `asyncio.run()` once per query
    (a fresh loop each time) would reuse that cached lock across loops on the
    second query and raise — so the whole measurement runs under one
    `asyncio.run()` (see `main()`), and this coroutine just awaits each query
    in turn.
    """
    from mcp_server.tools.search_handlers import handle_search_code

    results = []
    t0 = time.perf_counter()
    for query in queries:
        result = await handle_search_code({"query": query, "k": k})
        results.append(result)
    elapsed = time.perf_counter() - t0
    return elapsed, results


def _check_result(query: str, result: dict[str, Any]) -> None:
    """Fail loudly if a query returned an error response instead of results.

    A silently-empty result set would make every phase's timing look small
    for the wrong reason (nothing to format/score/extract) — this is the
    same "success alone isn't proof" pitfall profile_full_index.py guards
    against for indexing.
    """
    if "error" in result:
        raise RuntimeError(
            f"search_code('{query}') returned an error: {result['error']}"
        )
    if not result.get("results"):
        print(
            f"[WARN] search_code('{query}') returned zero results — is the "
            f"project indexed? Phase timings for this query will be near-zero.",
            file=sys.stderr,
        )


async def _main_async(args: argparse.Namespace) -> dict[str, Any]:
    import os

    from mcp_server.resource_manager import initialize_server_state

    os.environ.setdefault("CLAUDE_DEFAULT_PROJECT", args.project)
    initialize_server_state()

    global _recorder
    _install_patches()

    queries = args.queries or _DEFAULT_QUERIES
    print(f"Project: {args.project}")
    print(f"Queries: {len(queries)}  k={args.k}  runs={args.runs}")

    if not args.no_warmup:
        print("\nWarm-up run (untimed, real search_code calls)...")
        _recorder = _Recorder()
        t0 = time.perf_counter()
        _, warmup_results = await _run_query_set(queries, args.k)
        for query, result in zip(queries, warmup_results, strict=True):
            _check_result(query, result)
        print(f"  done in {time.perf_counter() - t0:.1f}s")

    run_totals: list[float] = []
    run_records: list[_Recorder] = []

    for run_idx in range(1, args.runs + 1):
        print(f"\nTimed run {run_idx}/{args.runs}...")
        _recorder = _Recorder()
        total_wall, run_results = await _run_query_set(queries, args.k)
        for query, result in zip(queries, run_results, strict=True):
            _check_result(query, result)
        print(f"  done in {total_wall:.3f}s")
        _print_phase_table(_recorder, total_wall)
        run_totals.append(total_wall)
        run_records.append(_recorder)

    median_total = statistics.median(run_totals)
    print()
    print("#" * 78)
    print(f"SUMMARY — median of {len(run_totals)} run(s)")
    print("#" * 78)
    print(
        f"{'total wall-clock':<26} {median_total:>10.3f}s  "
        f"(spread: {min(run_totals):.3f}-{max(run_totals):.3f}s)"
    )
    medians: dict[str, float] = {}
    for name in _PHASE_NAMES:
        vals = [r.total(name) for r in run_records]
        medians[name] = statistics.median(vals)
        if medians[name] > 0 or any(vals):
            pct = medians[name] / median_total * 100 if median_total > 0 else 0.0
            spread = f"{min(vals):.3f}-{max(vals):.3f}s"
            print(
                f"{name:<26} {medians[name]:>10.3f}s {pct:>8.1f}%  (spread: {spread})"
            )

    return {
        "project": args.project,
        "queries": queries,
        "k": args.k,
        "runs": args.runs,
        "run_totals": run_totals,
        "per_run_phases": [
            {name: r.total(name) for name in _PHASE_NAMES if r.count(name)}
            for r in run_records
        ],
        "per_run_phase_call_counts": [
            {name: r.count(name) for name in _PHASE_NAMES if r.count(name)}
            for r in run_records
        ],
        "median": {
            "total_wall_clock": median_total,
            "phases": medians,
        },
    }


def main() -> None:
    _check_venv()
    logging.getLogger().setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        description=(
            "Profile the real search_code pipeline, attributing wall-clock "
            "to the four search-latency-plan fix sites (measure-only, no "
            "production code changes)."
        )
    )
    parser.add_argument(
        "--project",
        default=str(_PROJECT_ROOT),
        help="Indexed project to search (default: this repo)",
    )
    parser.add_argument(
        "--queries",
        nargs="+",
        default=None,
        help="Queries to run each timed rep (default: 8 built-in queries covering this repo)",
    )
    parser.add_argument(
        "--k", type=int, default=8, help="Results per query (default: 8)"
    )
    parser.add_argument(
        "--runs", type=int, default=5, help="Timed reps; reports median (default: 5)"
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="Skip the untimed warm-up rep (default: 1 untimed warm-up rep first)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(_PROJECT_ROOT / "benchmark_results"),
        help="Directory for the JSON artifact",
    )
    args = parser.parse_args()

    args.project = str(Path(args.project).resolve())
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Single event loop for the entire measurement — see _run_query_set's
    # docstring for why calling asyncio.run() once per query would break the
    # reindex read lock's event-loop-bound asyncio.Condition.
    artifact = asyncio.run(_main_async(args))

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    artifact["timestamp"] = timestamp
    json_path = output_dir / f"search_latency_profile_{timestamp}.json"
    json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    print(f"\nJSON artifact: {json_path}")


if __name__ == "__main__":
    main()
