#!/usr/bin/env python3
"""Semantic Intent Classification Evaluation Script.

Tests whether the semantic_enabled parameter in IntentConfig improves retrieval
quality by comparing classification decisions (semantic on vs off) across:
  - 13 SSCG golden dataset queries
  - 8 novel phrasings using synonyms not in keyword lists

Two phases:
  Part A: Classification Comparison — no search needed, fast
           Compare intent + confidence for each query with semantic on vs off.
  Part B: Retrieval Impact — only for queries where classification changed
           Apply intent-driven param adjustments, run search, compare vs ground truth.

The benchmark runner (run_sscg_benchmark.py) bypasses intent classification
because it calls searcher.search() directly. This script tests the classification
layer specifically.

Usage:
    .venv/Scripts/python.exe scripts/benchmark/test_semantic_intent.py \\
        --project-path F:/RD_PROJECTS/COMPONENTS/claude-context-local

    # Skip Part B (classification-only, faster)
    ... --no-retrieval

    # Save JSON results
    ... --output results/semantic_intent_test.json
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# sys.path setup — must run before project imports
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from evaluation.metrics import (  # noqa: E402
    aggregate_metrics,
    calculate_metrics_from_results,
    normalize_chunk_ids,
)
from search.intent_classifier import IntentClassifier  # noqa: E402

# ---------------------------------------------------------------------------
# Novel phrasings — synonyms / paraphrases NOT in keyword lists
# These should benefit most from semantic scoring.
# ---------------------------------------------------------------------------
NOVEL_QUERIES: list[dict[str, Any]] = [
    {
        "id": "N01",
        "query": "who invokes the embedding function",
        "expected_intent": "navigational",
        "note": "'invokes' not in keyword list",
    },
    {
        "id": "N02",
        "query": "explain the overall system design",
        "expected_intent": "global",
        "note": "paraphrase, no standard keyword",
    },
    {
        "id": "N03",
        "query": "locate the token counter",
        "expected_intent": "local",
        "note": "'locate' not in keyword list",
    },
    {
        "id": "N04",
        "query": "what's the purpose of community detection",
        "expected_intent": "global",
        "note": "'purpose' phrasing",
    },
    {
        "id": "N05",
        "query": "things that resemble RRFReranker",
        "expected_intent": "similarity",
        "note": "'resemble' not standard",
    },
    {
        "id": "N06",
        "query": "show me the neighborhood of CodeEmbedder",
        "expected_intent": "contextual",
        "note": "'neighborhood' novel phrasing",
    },
    {
        "id": "N07",
        "query": "encode and decode operations",
        "expected_intent": "hybrid",
        "note": "sibling pattern",
    },
    {
        "id": "N08",
        "query": "data flow from query to FAISS",
        "expected_intent": "path_tracing",
        "note": "'data flow' synonym for path tracing",
    },
]


# ---------------------------------------------------------------------------
# Setup helpers
# ---------------------------------------------------------------------------


def _setup_project(project_path: str) -> None:
    try:
        from mcp_server.services import get_state

        state = get_state()
        state.current_project = project_path
    except Exception as e:
        print(f"[WARN] Could not set project via get_state(): {e}", file=sys.stderr)


def _get_searcher(project_path: str) -> Any:
    """Initialize HybridSearcher (also loads the embedding model)."""
    try:
        from mcp_server.search_factory import get_searcher

        return get_searcher(project_path=project_path)
    except TypeError:
        from mcp_server.search_factory import get_searcher  # type: ignore[import]

        return get_searcher()


def _extract_embedder(searcher: Any) -> Any | None:
    """Extract CodeEmbedder from an initialized HybridSearcher."""
    try:
        return searcher.search_executor.embedder
    except AttributeError:
        return None


# ---------------------------------------------------------------------------
# Classification comparison (Part A)
# ---------------------------------------------------------------------------


def _classify_one(
    query: str,
    semantic_enabled: bool,
    embedder: Any | None,
    confidence_threshold: float = 0.35,
) -> dict[str, Any]:
    """Run IntentClassifier on a single query, return classification details."""
    classifier = IntentClassifier(
        confidence_threshold=confidence_threshold,
        enable_logging=False,
        embedder=embedder if semantic_enabled else None,
        semantic_enabled=semantic_enabled,
        semantic_weight=0.3,
    )
    decision = classifier.classify(query)
    return {
        "intent": decision.intent.value,
        "confidence": round(decision.confidence, 4),
        "reason": decision.reason,
        "scores": {k: round(v, 4) for k, v in (decision.scores or {}).items()},
        "suggested_params": decision.suggested_params,
    }


def run_classification_comparison(
    queries: list[dict[str, Any]],
    embedder: Any | None,
    confidence_threshold: float = 0.35,
) -> list[dict[str, Any]]:
    """Classify all queries with semantic on and off, return comparison rows."""
    rows = []
    for item in queries:
        qid = item["id"]
        query = item["query"]
        expected_intent = item.get("expected_intent")  # None for SSCG queries

        off = _classify_one(query, semantic_enabled=False, embedder=None,
                            confidence_threshold=confidence_threshold)
        on = _classify_one(query, semantic_enabled=True, embedder=embedder,
                           confidence_threshold=confidence_threshold)

        changed = off["intent"] != on["intent"]
        conf_delta = round(on["confidence"] - off["confidence"], 4)

        # For novel queries: did semantic score the expected intent higher?
        correct_improvement = None
        if expected_intent and changed:
            # Was the change from wrong→right or right→wrong?
            if on["intent"] == expected_intent:
                correct_improvement = True
            elif off["intent"] == expected_intent:
                correct_improvement = False

        rows.append(
            {
                "id": qid,
                "query": query,
                "category": item.get("category", "novel"),
                "expected_intent": expected_intent,
                "intent_off": off["intent"],
                "intent_on": on["intent"],
                "conf_off": off["confidence"],
                "conf_on": on["confidence"],
                "conf_delta": conf_delta,
                "changed": changed,
                "correct_improvement": correct_improvement,
                "note": item.get("note"),
                "scores_off": off["scores"],
                "scores_on": on["scores"],
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Retrieval comparison (Part B)
# ---------------------------------------------------------------------------


def _apply_intent_params(
    intent: str,
    suggested_params: dict[str, Any],
    base_k: int,
    confidence: float,
    confidence_threshold: float,
) -> dict[str, Any]:
    """Replicate the parameter adjustments from handle_search_code().

    Returns kwargs dict suitable for searcher.search() plus a note string.
    """
    k = base_k
    ego_graph_enabled = False
    ego_graph_k_hops = 2

    high_confidence = confidence >= confidence_threshold

    if intent == "global" and high_confidence:
        suggested_k = suggested_params.get("k", k)
        if suggested_k > k:
            k = suggested_k

    if intent == "contextual" and suggested_params.get("ego_graph_enabled"):
        ego_graph_enabled = True
        ego_graph_k_hops = suggested_params.get("ego_graph_k_hops", 2)

    return {
        "k": k,
        "ego_graph_enabled": ego_graph_enabled,
        "ego_graph_k_hops": ego_graph_k_hops,
    }


def _run_query_with_params(
    searcher: Any,
    query: str,
    k: int,
    ego_graph_enabled: bool = False,
    ego_graph_k_hops: int = 2,
) -> tuple[list[str], float]:
    start = time.perf_counter()
    # searcher.search() signature: search(query, k, ego_graph_enabled, ego_graph_k_hops)
    try:
        results = searcher.search(
            query,
            k=k,
            ego_graph_enabled=ego_graph_enabled,
            ego_graph_k_hops=ego_graph_k_hops,
        )
    except TypeError:
        # Fallback if ego_graph args aren't supported directly
        results = searcher.search(query, k=k)
    latency_ms = (time.perf_counter() - start) * 1000.0
    raw_ids = [r.chunk_id for r in results]
    return normalize_chunk_ids(raw_ids), latency_ms


def run_retrieval_comparison(
    changed_rows: list[dict[str, Any]],
    sscg_queries: list[dict[str, Any]],
    searcher: Any,
    confidence_threshold: float = 0.35,
    base_k: int = 4,
) -> list[dict[str, Any]]:
    """For classification-changed queries, compare retrieval with semantic on vs off."""
    # Build lookup for golden dataset expected results
    golden_lookup: dict[str, dict[str, Any]] = {
        q["id"]: q for q in sscg_queries
    }

    results = []
    for row in changed_rows:
        qid = row["id"]
        query = row["query"]

        # Only evaluate retrieval for SSCG queries (we have ground truth)
        if qid not in golden_lookup:
            results.append(
                {
                    "id": qid,
                    "query": query,
                    "note": "novel query -- no ground truth for retrieval comparison",
                }
            )
            continue

        golden = golden_lookup[qid]
        expected = golden["expected"]
        expected_primary = golden.get("expected_primary", expected)

        # Build params for each config
        params_off = _apply_intent_params(
            row["intent_off"],
            _classify_one(query, False, None, confidence_threshold)["suggested_params"],
            base_k,
            row["conf_off"],
            confidence_threshold,
        )
        params_on = _apply_intent_params(
            row["intent_on"],
            _classify_one(query, True, searcher.search_executor.embedder if hasattr(searcher, "search_executor") else None, confidence_threshold)["suggested_params"],
            base_k,
            row["conf_on"],
            confidence_threshold,
        )

        retrieved_off, lat_off = _run_query_with_params(searcher, query, **params_off)
        retrieved_on, lat_on = _run_query_with_params(searcher, query, **params_on)

        metrics_off = calculate_metrics_from_results(
            retrieved=retrieved_off,
            expected=expected,
            expected_primary=expected_primary,
        )
        metrics_on = calculate_metrics_from_results(
            retrieved=retrieved_on,
            expected=expected,
            expected_primary=expected_primary,
        )

        mrr_delta = round(metrics_on["mrr"] - metrics_off["mrr"], 4)
        recall_delta = round(metrics_on["recall@5"] - metrics_off["recall@5"], 4)
        verdict = (
            "IMPROVED" if mrr_delta > 0.01 else
            "REGRESSED" if mrr_delta < -0.01 else
            "UNCHANGED"
        )

        results.append(
            {
                "id": qid,
                "query": query,
                "params_off": params_off,
                "params_on": params_on,
                "retrieved_off": retrieved_off,
                "retrieved_on": retrieved_on,
                "mrr_off": round(metrics_off["mrr"], 4),
                "mrr_on": round(metrics_on["mrr"], 4),
                "mrr_delta": mrr_delta,
                "recall5_off": round(metrics_off["recall@5"], 4),
                "recall5_on": round(metrics_on["recall@5"], 4),
                "recall_delta": recall_delta,
                "latency_off_ms": round(lat_off, 1),
                "latency_on_ms": round(lat_on, 1),
                "verdict": verdict,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

COL_W = 42  # Query column width


def _trunc(s: str, width: int) -> str:
    return s if len(s) <= width else s[: width - 1] + "~"


def print_classification_table(rows: list[dict[str, Any]]) -> None:
    print()
    print("=" * 110)
    print("PART A -- CLASSIFICATION COMPARISON (semantic off vs on)")
    print("=" * 110)
    header = (
        f"{'ID':<6} {'Query':<{COL_W}} {'Intent(off)':<14} {'Intent(on)':<14} "
        f"{'Conf(off)':<10} {'Conf(on)':<10} {'dConf':<8} {'Changed?'}"
    )
    print(header)
    print("-" * 110)

    sscg_rows = [r for r in rows if r["category"] != "novel"]
    novel_rows = [r for r in rows if r["category"] == "novel"]

    def _print_section(section_rows: list[dict[str, Any]], label: str) -> None:
        if not section_rows:
            return
        print(f"\n  -- {label} --")
        for r in section_rows:
            changed_flag = "YES <<<" if r["changed"] else "no"
            if r["changed"] and r["correct_improvement"] is True:
                changed_flag = "YES [OK] (to correct)"
            elif r["changed"] and r["correct_improvement"] is False:
                changed_flag = "YES [!!] (wrong->right was off)"
            print(
                f"  {r['id']:<4} {_trunc(r['query'], COL_W):<{COL_W}} "
                f"{r['intent_off']:<14} {r['intent_on']:<14} "
                f"{r['conf_off']:<10.3f} {r['conf_on']:<10.3f} "
                f"{r['conf_delta']:+.3f}   {changed_flag}"
            )
            if r.get("note"):
                print(f"       note: {r['note']}")

    _print_section(sscg_rows, "SSCG Golden Dataset (13 queries)")
    _print_section(novel_rows, "Novel Phrasings (8 queries -- not in keyword lists)")

    total = len(rows)
    changed = [r for r in rows if r["changed"]]
    improved_novel = [r for r in novel_rows if r.get("correct_improvement") is True]
    regressed_novel = [r for r in novel_rows if r.get("correct_improvement") is False]

    print()
    print("-" * 110)
    print(f"  Summary: {len(changed)}/{total} queries changed intent")
    print(f"    SSCG queries changed   : {sum(1 for r in sscg_rows if r['changed'])}/{len(sscg_rows)}")
    print(f"    Novel queries changed  : {len(changed) - sum(1 for r in sscg_rows if r['changed'])}/{len(novel_rows)}")
    if novel_rows:
        print(f"    Novel -> correct intent : {len(improved_novel)}")
        print(f"    Novel -> wrong intent   : {len(regressed_novel)}")
    avg_conf_delta = sum(r["conf_delta"] for r in rows) / len(rows) if rows else 0
    print(f"    Avg confidence delta   : {avg_conf_delta:+.4f}")
    print()


def print_retrieval_table(results: list[dict[str, Any]]) -> None:
    print()
    print("=" * 110)
    print("PART B -- RETRIEVAL IMPACT (queries with changed classification only)")
    print("=" * 110)
    sscg_results = [r for r in results if "mrr_off" in r]
    novel_results = [r for r in results if "mrr_off" not in r]

    if not sscg_results:
        print("  No SSCG queries had classification changes -- no retrieval comparison needed.")
    else:
        header = (
            f"  {'ID':<5} {'Query':<{COL_W}} {'MRR(off)':<10} {'MRR(on)':<10} "
            f"{'dMRR':<8} {'R@5(off)':<10} {'R@5(on)':<10} {'dR@5':<8} {'Verdict'}"
        )
        print(header)
        print("  " + "-" * 106)
        for r in sscg_results:
            print(
                f"  {r['id']:<5} {_trunc(r['query'], COL_W):<{COL_W}} "
                f"{r['mrr_off']:<10.3f} {r['mrr_on']:<10.3f} "
                f"{r['mrr_delta']:+.3f}    "
                f"{r['recall5_off']:<10.3f} {r['recall5_on']:<10.3f} "
                f"{r['recall_delta']:+.3f}    {r['verdict']}"
            )

    if novel_results:
        print()
        print("  Novel query notes:")
        for r in novel_results:
            print(f"    {r['id']}: {r['note']}")
    print()


def print_summary(
    class_rows: list[dict[str, Any]],
    retrieval_results: list[dict[str, Any]] | None,
) -> None:
    print("=" * 110)
    print("VERDICT")
    print("=" * 110)

    sscg_changed = [r for r in class_rows if r["category"] != "novel" and r["changed"]]
    novel_improved = [r for r in class_rows if r["category"] == "novel" and r.get("correct_improvement") is True]
    novel_regressed = [r for r in class_rows if r["category"] == "novel" and r.get("correct_improvement") is False]

    retrieval_improved = []
    retrieval_regressed = []
    if retrieval_results:
        retrieval_improved = [r for r in retrieval_results if r.get("verdict") == "IMPROVED"]
        retrieval_regressed = [r for r in retrieval_results if r.get("verdict") == "REGRESSED"]

    print()
    if sscg_changed:
        print(f"  [!!] {len(sscg_changed)} SSCG queries changed classification -- check for regressions.")
    else:
        print("  [OK] No SSCG queries changed classification (semantic scoring reinforces existing decisions).")

    if novel_improved:
        print(f"  [OK] {len(novel_improved)}/8 novel phrasings correctly reclassified with semantic on.")
    if novel_regressed:
        print(f"  [!!] {len(novel_regressed)}/8 novel phrasings misclassified with semantic on.")
    if not novel_improved and not novel_regressed:
        print("  [--] Novel phrasings: no classification changes (keyword scoring already handles these).")

    if retrieval_improved:
        print(f"  [OK] Retrieval improved for {len(retrieval_improved)} queries (MRR delta > 0.01).")
    if retrieval_regressed:
        print(f"  [!!] Retrieval regressed for {len(retrieval_regressed)} queries (MRR delta < -0.01).")

    # Overall recommendation
    print()
    if not sscg_changed and not novel_regressed and not retrieval_regressed:
        print("  RECOMMENDATION: semantic_enabled=True is safe -- no regressions detected.")
        if novel_improved or retrieval_improved:
            print("  BENEFIT: Improves novel phrasings / retrieval for reclassified queries.")
        else:
            print("  BENEFIT: Neutral -- no regressions and no detectable improvements on this dataset.")
            print("           (The keyword classifier already handles these queries well.)")
    else:
        print("  RECOMMENDATION: Review regressions before keeping semantic_enabled=True.")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project-path",
        required=True,
        help="Path to the indexed project",
    )
    parser.add_argument(
        "--golden-dataset",
        default=None,
        help="Path to golden_dataset.json (default: evaluation/golden_dataset.json)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Save JSON results to this file",
    )
    parser.add_argument(
        "--no-retrieval",
        action="store_true",
        help="Skip Part B (retrieval comparison), only run classification comparison",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.35,
        help="IntentClassifier confidence threshold (default: 0.35)",
    )
    args = parser.parse_args()

    project_path = str(Path(args.project_path).resolve())
    golden_path = (
        Path(args.golden_dataset)
        if args.golden_dataset
        else _PROJECT_ROOT / "evaluation" / "golden_dataset.json"
    )

    print(f"\nSemantic Intent Classification Evaluation")
    print(f"  Project : {project_path}")
    print(f"  Dataset : {golden_path}")
    print(f"  Conf threshold: {args.confidence_threshold}")
    print()

    # Load golden dataset
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)
    sscg_queries = golden["queries"]

    # Prepare combined query list for classification test
    sscg_for_class = [
        {
            "id": q["id"],
            "query": q["query"],
            "category": q.get("category", "?"),
            "expected_intent": None,  # SSCG queries don't have expected intent labels
        }
        for q in sscg_queries
    ]
    all_queries = sscg_for_class + NOVEL_QUERIES

    # Initialize searcher (loads embedding model)
    print("Loading searcher and embedding model (may take 5-15s)...")
    _setup_project(project_path)
    t0 = time.perf_counter()
    searcher = _get_searcher(project_path)
    load_time = time.perf_counter() - t0
    print(f"  Searcher ready in {load_time:.1f}s")

    # Extract embedder for semantic scoring
    embedder = _extract_embedder(searcher)
    if embedder is None:
        print("[WARN] Could not extract embedder from searcher -- semantic scoring will be disabled")
    else:
        print(f"  Embedder: {getattr(embedder, 'model_name', 'unknown')}")

    # -----------------------------------------------------------------------
    # Part A: Classification comparison
    # -----------------------------------------------------------------------
    print(f"\nRunning Part A: classifying {len(all_queries)} queries (semantic on vs off)...")
    t_a = time.perf_counter()
    class_rows = run_classification_comparison(
        all_queries,
        embedder=embedder,
        confidence_threshold=args.confidence_threshold,
    )
    print(f"  Done in {time.perf_counter() - t_a:.1f}s")
    print_classification_table(class_rows)

    # -----------------------------------------------------------------------
    # Part B: Retrieval comparison (only for changed SSCG queries)
    # -----------------------------------------------------------------------
    retrieval_results: list[dict[str, Any]] | None = None
    if not args.no_retrieval:
        changed_rows = [r for r in class_rows if r["changed"]]
        if changed_rows:
            print(f"Running Part B: retrieval comparison for {len(changed_rows)} changed queries...")
            t_b = time.perf_counter()
            retrieval_results = run_retrieval_comparison(
                changed_rows,
                sscg_queries=sscg_queries,
                searcher=searcher,
                confidence_threshold=args.confidence_threshold,
            )
            print(f"  Done in {time.perf_counter() - t_b:.1f}s")
            print_retrieval_table(retrieval_results)
        else:
            print("Part B: No queries changed classification -- skipping retrieval comparison.")
            retrieval_results = []
    else:
        print("Part B: Skipped (--no-retrieval)")

    # -----------------------------------------------------------------------
    # Summary verdict
    # -----------------------------------------------------------------------
    print_summary(class_rows, retrieval_results)

    # -----------------------------------------------------------------------
    # Save JSON results
    # -----------------------------------------------------------------------
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "project_path": project_path,
            "confidence_threshold": args.confidence_threshold,
            "embedder_model": getattr(embedder, "model_name", None),
            "classification_comparison": class_rows,
            "retrieval_comparison": retrieval_results,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
