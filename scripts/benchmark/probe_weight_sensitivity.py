#!/usr/bin/env python
"""Probe per-query BM25/dense weight sensitivity across the golden set (read-only).

``run_sscg_benchmark.py --sweep`` answers "is there one best *global* weight?" —
no, the aggregate MRR is flat across the sweep (``evaluation/BM25_K1B_SWEEP_20260726.md``,
corroborated in ``POOL_MISS_DIAGNOSIS.md`` / ``index_probe.py``). It never asks the
question intent-adaptive weights actually bet on: does the best weight *vary per
query*? A flat aggregate is consistent with either "no query cares" or "queries
disagree and their preferences cancel out in the mean" — this probe distinguishes
the two by scoring every query at every weight point instead of only the mean.

HISTORICAL NOTE (2026-08-01): this probe served as the Step-1 evidence gate for
the intent-adaptive-fusion-weights A/B, which REJECTED the feature (ADR-0019 —
``INTENT_WEIGHT_PROFILES`` and the orchestrator gate were deleted). Two of the
``WEIGHT_COMBOS`` points (0.30/0.70, 0.40/0.60) were that table's operating
points and are kept for continuity. The probe remains a general per-query
weight-sensitivity tool.

For each golden query this sweeps ``WEIGHT_COMBOS`` (9 points spanning the axis:
the existing sweep's 4 interior points, 3 wider tails, and 2 historical
intent-profile points) and records the MRR of
the first grade-3 (highly-relevant) gold at each point via ``calculate_mrr``. A
query has "headroom" when its best combo's MRR exceeds the deployed baseline
(0.35/0.65) MRR by more than ``--noise-band`` (default 0.02 — the measured
run-to-run SSCG noise; see project memory / ``evaluation/*SWEEP*.md``).

Headroom queries are cross-tabbed by intent label, classified live via
``IntentClassifier`` for grouping only — the label is never fed back into search.
Feeding it back would confound retrieval quality with classifier accuracy; this
is the same discipline ``run_sscg_benchmark.py``'s ``_apply_centrality_stage``
documents for its own ``intent`` parameter (hand-labeled there, live-classified
here, but neither ever drives the search call it's reported alongside).

Loops weight combinations *outer*, queries *inner*: 9 config mutations total,
not one per query x combo pair. ``_set_weights`` mutates the live
``SearchConfig`` singleton in place, the same in-memory mechanism
``run_sscg_benchmark.py._apply_weight_overrides`` uses. No searcher reset is
needed between combinations: post-C2 (ADR-0018), ``HybridSearcher.search()``
resolves weights from the live config on every call (``bm25_weight``/
``dense_weight`` kwargs default to ``None``, falling through to
``effective_config.search_mode.*``) rather than a construction-time snapshot,
so mutating the singleton between searches is sufficient — unlike ``rrf_k`` or
the reranker doc budgets, no ``_maybe_reset_for_construction_overrides`` call
is required here.

Category D (call-graph) is excluded by default, matching
``run_sscg_benchmark.py``'s default filter: this probe scores via
``HybridSearcher.search()`` (the ``search_code`` path) only.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/probe_weight_sensitivity.py \
        [--dataset evaluation/golden_dataset.json] [--project-path .] \
        [--k 7] [--category A,B,C] [--noise-band 0.02]

Exit code 0 when at least one query's optimum exceeds --noise-band over the
baseline MRR; 1 when none do; 2 on setup errors.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.metrics import calculate_mrr, normalize_chunk_ids  # noqa: E402


# The existing sweep's 4 interior points (run_sscg_benchmark.SWEEP_CONFIGS)
# plus 3 wider tails, so a per-query preference the aggregate sweep would
# average away still has somewhere to show up — plus the two operating points
# of the (removed, ADR-0019) intent-adaptive weight table so those historical
# A/B numbers stay reproducible.
WEIGHT_COMBOS: list[tuple[float, float]] = [
    (0.10, 0.90),
    (0.20, 0.80),
    (0.30, 0.70),  # historical intent profile: GLOBAL / CONTEXTUAL
    (0.35, 0.65),  # deployed default / baseline
    (0.40, 0.60),  # historical intent profile: PATH_TRACING / SIMILARITY / HYBRID
    (0.50, 0.50),  # historical intent profile: NAVIGATIONAL
    (0.65, 0.35),
    (0.80, 0.20),
    (0.90, 0.10),
]
BASELINE_COMBO = (0.35, 0.65)
NOISE_BAND = 0.02  # measured SSCG run-to-run noise (project memory)


def _load_queries(dataset_path: Path, category_filter: str | None) -> list[dict]:
    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    queries = data["queries"]
    if category_filter:
        cats = {c.strip() for c in category_filter.split(",") if c.strip()}
        return [q for q in queries if q.get("category") in cats]
    # Exclude category D by default: this probe scores via HybridSearcher.search()
    # only, mirroring run_sscg_benchmark.py's default category filter.
    return [q for q in queries if q.get("category") != "D"]


def _set_weights(bm25_weight: float, dense_weight: float) -> None:
    """Mutate the live in-memory config (same mechanism as run_sscg_benchmark.py).

    No searcher reset needed — see the module docstring.
    """
    from search.config import get_search_config

    cfg = get_search_config()
    cfg.search_mode.bm25_weight = bm25_weight
    cfg.search_mode.dense_weight = dense_weight


def _classify_intents(queries: list[dict]) -> dict[str, str]:
    """Classify each query's intent label, for cross-tab reporting only.

    Never fed back into search — see the module docstring for why.
    """
    from search.intent_classifier import IntentClassifier

    classifier = IntentClassifier(enable_logging=False)
    return {q["id"]: classifier.classify(q["query"]).intent.value for q in queries}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", default="evaluation/golden_dataset.json")
    parser.add_argument("--project-path", default=".")
    parser.add_argument("--k", type=int, default=7)
    parser.add_argument(
        "--category",
        default=None,
        help="Comma-separated category filter (default: all but D)",
    )
    parser.add_argument("--noise-band", type=float, default=NOISE_BAND)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.is_absolute():
        dataset_path = REPO_ROOT / dataset_path
    try:
        queries = _load_queries(dataset_path, args.category)
    except (OSError, json.JSONDecodeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if not queries:
        print("ERROR: no queries matched the filter", file=sys.stderr)
        return 2

    from mcp_server.search_factory import get_searcher

    try:
        searcher = get_searcher(project_path=args.project_path)
    except Exception as e:
        print(f"ERROR: could not initialize searcher: {e}", file=sys.stderr)
        return 2

    intents = _classify_intents(queries)

    # combo -> qid -> mrr
    mrr_by_combo: dict[tuple[float, float], dict[str, float]] = {}
    for bm25_w, dense_w in WEIGHT_COMBOS:
        _set_weights(bm25_w, dense_w)
        per_query: dict[str, float] = {}
        for item in queries:
            qid = item["id"]
            expected = item["expected"]
            expected_primary = item.get("expected_primary") or expected
            results = searcher.search(item["query"], k=args.k)
            retrieved = normalize_chunk_ids([r.chunk_id for r in results])
            per_query[qid] = calculate_mrr(retrieved, expected_primary)
        mrr_by_combo[(bm25_w, dense_w)] = per_query

    baseline = mrr_by_combo[BASELINE_COMBO]

    # ------------------------------------------------------------------ report
    print(f"\nWeight-sensitivity probe  (k={args.k}, {len(queries)} queries)")
    print(f"Dataset: {dataset_path.name}\n")

    header = f"{'qid':>5} {'intent':>13} " + " ".join(
        f"{b:.2f}/{d:.2f}".rjust(11) for b, d in WEIGHT_COMBOS
    )
    print(header)
    print("-" * len(header))

    headroom_rows: list[tuple[str, str, float, tuple[float, float], float]] = []
    for item in queries:
        qid = item["id"]
        cells = []
        best_combo = BASELINE_COMBO
        best_mrr = -1.0
        for combo in WEIGHT_COMBOS:
            mrr = mrr_by_combo[combo][qid]
            cells.append(f"{mrr:.3f}".rjust(11))
            if mrr > best_mrr:
                best_mrr = mrr
                best_combo = combo
        print(f"{qid:>5} {intents[qid]:>13} " + " ".join(cells))

        gain = best_mrr - baseline[qid]
        if gain > args.noise_band:
            headroom_rows.append((qid, intents[qid], baseline[qid], best_combo, gain))

    print()
    if headroom_rows:
        print(
            f"{len(headroom_rows)}/{len(queries)} queries have an optimum outside "
            f"the +/-{args.noise_band} noise band:\n"
        )
        print(
            f"{'qid':>5} {'intent':>13} {'baseline':>9} {'best combo':>11} {'gain':>7}"
        )
        for qid, intent, base_mrr, combo, gain in headroom_rows:
            combo_s = f"{combo[0]:.2f}/{combo[1]:.2f}"
            print(f"{qid:>5} {intent:>13} {base_mrr:9.3f} {combo_s:>11} {gain:+7.3f}")

        by_intent: dict[str, int] = {}
        for _qid, intent, *_rest in headroom_rows:
            by_intent[intent] = by_intent.get(intent, 0) + 1
        print("\nHeadroom-query count by intent label:")
        for intent, count in sorted(by_intent.items(), key=lambda kv: -kv[1]):
            print(f"  {intent:>13}: {count}")
    else:
        print(f"No query has an optimum outside the +/-{args.noise_band} noise band.")

    print()
    if headroom_rows:
        verb = "has" if len(headroom_rows) == 1 else "have"
        print(
            f"VERDICT: evidence SUPPORTS the flip - {len(headroom_rows)} "
            f"quer{'y' if verb == 'has' else 'ies'} {verb} per-query headroom "
            "beyond noise."
        )
        return 0
    print("VERDICT: no evidence of per-query headroom beyond noise - do not flip yet.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
