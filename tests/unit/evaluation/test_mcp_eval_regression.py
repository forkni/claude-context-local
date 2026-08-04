"""CI regression gate for frozen MCP-collected search results.

`raw_mcp_results_{hybrid,bm25,semantic}.json` are frozen snapshots collected
by driving the live MCP `search_code` tool once and saving its raw
`[score, chunk_id]` output. This test scores those frozen snapshots through
the *real* metrics pipeline (`mcp_eval.get_top_k_chunk_ids` ->
`calculate_metrics_from_results` -> `aggregate_metrics`). It therefore gates
the scoring path (metrics math + golden-set coverage) and catches drift in
that path -- it is not a live retrieval-quality regression test, since the
raw results themselves do not change between runs.

Hybrid mode (collected 2026-07-31, k=10, 76/77 queries) is threshold-gated
against `golden_dataset.json`'s own thresholds, but only on categories
A/B/C/E (53 of 77 queries). Categories D and F are excluded from the gate:
per `golden_dataset.json`'s own category metadata, D queries are answered via
`find_connections` (not ranked search) and F queries via `find_similar_code`
(not ranked search) -- scoring them against `search_code`'s ranked results
would gate on a method mismatch, not a real regression. All 76 collected
hybrid queries are still scored and their full aggregate is asserted sane
(values in [0, 1]) for visibility, matching the chosen scope of "score
everything, gate only A/B/C/E".

One golden query, Q72, could not be collected at all: `search_code`'s intent
classifier deterministically misroutes its "from <chunk_id> to get" phrasing
to `find_path` semantics (returns `path_found: false` with no ranked results)
independent of `search_mode` -- reproduced 3x against the live server. This is
documented as a named, non-silent exception (`KNOWN_HYBRID_GAPS` below and the
`known_gaps` key in `raw_mcp_results_hybrid.json` itself) rather than a silent
gap, so any *other*, undocumented missing query still fails this test loudly.

bm25 and semantic are scored and pinned against a fixed baseline (small
tolerance for float noise) rather than threshold-gated: bm25-only was never
expected to clear the hybrid-tuned thresholds (at 77 queries it misses all
three by a wide margin -- documented, expected behaviour, not a bug), and
semantic intentionally stays frozen at its original 13-query collection.
"""

import json
from pathlib import Path

import pytest

from evaluation.metrics import aggregate_metrics, calculate_metrics_from_results
from scripts.benchmark.mcp_eval import get_top_k_chunk_ids, load_raw_results


REPO_ROOT = Path(__file__).resolve().parents[3]
EVALUATION_DIR = REPO_ROOT / "evaluation"

GATED_CATEGORIES = {"A", "B", "C", "E"}

# Documented, non-silent exceptions to "every golden ID must appear in the
# frozen hybrid results". Any *other* missing ID still fails loudly -- see
# module docstring and raw_mcp_results_hybrid.json's own known_gaps entry.
KNOWN_HYBRID_GAPS = {"Q72"}

# Pinned 2026-07-31 baselines. Small tolerance for float noise; not
# threshold-gated -- this is scoring-path drift detection, not a quality gate.
BM25_BASELINE = {
    "mrr": 0.2275,
    "recall@5": 0.2356,
    "recall@10": 0.3505,
    "hit_rate@5": 0.4805,
    "ndcg@5": 0.2141,
}
SEMANTIC_BASELINE = {
    "mrr": 0.7756,
    "recall@5": 0.6603,
    "recall@10": 0.7244,
    "hit_rate@5": 1.0,
    "ndcg@5": 0.6715,
}
TOLERANCE = 0.005


def _load_golden() -> tuple[dict[str, dict], dict[str, float]]:
    data = json.loads(
        (EVALUATION_DIR / "golden_dataset.json").read_text(encoding="utf-8")
    )
    return {q["id"]: q for q in data["queries"]}, data["thresholds"]


def _score_mode(mode: str, golden_queries: dict[str, dict]) -> list[dict]:
    """Score every frozen result for *mode* through the real metrics pipeline."""
    raw_results = load_raw_results(mode)
    per_query = []
    for qid, raw in sorted(raw_results.items()):
        qm = golden_queries[qid]
        retrieved = get_top_k_chunk_ids(raw, k=10)
        metrics = calculate_metrics_from_results(
            retrieved,
            qm["expected"],
            qm["expected_primary"],
            relevance_grades=qm.get("relevance_grades"),
        )
        metrics["query_id"] = qid
        metrics["category"] = qm["category"]
        per_query.append(metrics)
    return per_query


def test_every_golden_query_covered_by_frozen_hybrid_results():
    """Every golden query ID must appear in raw_mcp_results_hybrid.json.

    Except the documented KNOWN_HYBRID_GAPS. A *new*, undocumented gap (e.g.
    someone adds a query to golden_dataset.json without re-collecting hybrid
    results) must fail loudly rather than silently shrinking gate coverage.
    A gap that's listed in KNOWN_HYBRID_GAPS but no longer actually missing
    must also fail loudly, so the carve-out doesn't quietly outlive the bug.
    """
    golden_queries, _ = _load_golden()
    hybrid_data = json.loads(
        (EVALUATION_DIR / "raw_mcp_results_hybrid.json").read_text(encoding="utf-8")
    )
    collected_ids = set(hybrid_data["results"])

    missing = set(golden_queries) - collected_ids
    undocumented_missing = missing - KNOWN_HYBRID_GAPS
    assert not undocumented_missing, (
        f"Golden queries missing from raw_mcp_results_hybrid.json with no "
        f"documented reason: {sorted(undocumented_missing)}. Either "
        "re-collect them or add a known_gaps entry + KNOWN_HYBRID_GAPS carve-out."
    )

    stale_gaps = KNOWN_HYBRID_GAPS - missing
    assert not stale_gaps, (
        f"KNOWN_HYBRID_GAPS lists {sorted(stale_gaps)} as uncollectable, but "
        "they are now present in raw_mcp_results_hybrid.json -- drop them "
        "from KNOWN_HYBRID_GAPS (the underlying bug appears fixed)."
    )


def test_hybrid_gated_categories_pass_thresholds():
    """Hybrid mode, categories A/B/C/E only, must clear the golden thresholds.

    D ("find_connections, not ranked search") and F ("find_similar_code, not
    ranked search") are excluded -- see module docstring. Full-set hybrid
    aggregate (incl. D/F) is checked for sanity in a separate test below.
    """
    golden_queries, thresholds = _load_golden()
    per_query = _score_mode("hybrid", golden_queries)
    gated = [m for m in per_query if m["category"] in GATED_CATEGORIES]
    assert len(gated) == 53, (
        f"Expected 53 gated (A/B/C/E) queries, got {len(gated)} -- category "
        "counts in golden_dataset.json may have shifted; recheck GATED_CATEGORIES."
    )
    agg = aggregate_metrics(gated, thresholds=thresholds)
    pass_fail = agg["pass_fail"]
    assert pass_fail["mrr"] == "PASS", agg
    assert pass_fail["recall@5"] == "PASS", agg
    assert pass_fail["hit_rate@5"] == "PASS", agg


def test_hybrid_full_set_aggregate_is_sane():
    """All 76 collected hybrid queries (incl. D/F) score and land in [0, 1].

    Not threshold-gated: D/F drag this below the A/B/C/E-gated thresholds by
    design (see module docstring). This is a sanity check for visibility, not
    a regression gate, per the chosen scope (score everything, gate A/B/C/E).
    """
    golden_queries, _ = _load_golden()
    per_query = _score_mode("hybrid", golden_queries)
    assert len(per_query) == 76
    agg = aggregate_metrics(per_query)
    for key in ("mrr", "recall@5", "recall@10", "hit_rate@5", "ndcg@5", "ndcg@10"):
        value = agg[key]
        assert 0.0 <= value <= 1.0, f"{key}={value} out of [0, 1] range: {agg}"


def test_bm25_matches_pinned_baseline():
    """BM25-only aggregate is pinned, not threshold-gated.

    BM25 alone was never expected to clear the hybrid-tuned gate thresholds --
    at 77 queries it misses MRR/Recall@5/HitRate@5 by a wide margin, which is
    documented, expected behaviour. Pinning it here catches drift in the
    *scoring path* (metrics math, chunk-id normalization), not retrieval
    quality.
    """
    golden_queries, _ = _load_golden()
    per_query = _score_mode("bm25", golden_queries)
    assert len(per_query) == 77
    agg = aggregate_metrics(per_query)
    for key, expected in BM25_BASELINE.items():
        assert agg[key] == pytest.approx(expected, abs=TOLERANCE), (
            f"bm25 {key}={agg[key]!r} drifted from pinned baseline {expected!r}"
        )


def test_semantic_matches_pinned_baseline():
    """Semantic-only aggregate is pinned, not threshold-gated.

    Stays frozen at its original 13-query collection by design (see the
    plan) -- this is a scoring-path drift check, not a coverage check.
    """
    golden_queries, _ = _load_golden()
    per_query = _score_mode("semantic", golden_queries)
    assert len(per_query) == 13
    agg = aggregate_metrics(per_query)
    for key, expected in SEMANTIC_BASELINE.items():
        assert agg[key] == pytest.approx(expected, abs=TOLERANCE), (
            f"semantic {key}={agg[key]!r} drifted from pinned baseline {expected!r}"
        )
