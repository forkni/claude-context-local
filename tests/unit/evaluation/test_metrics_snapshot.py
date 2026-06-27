"""Snapshot tests for evaluation/metrics.py.

Pins the full output contract of:
  - calculate_metrics_from_results() → 12-key dict
  - aggregate_metrics()              → aggregate dict incl. nested pass_fail block

No volatile fields → no masking needed.
Run ``pytest --snapshot-update tests/unit/evaluation/test_metrics_snapshot.py``
once to generate the JSON snapshots, then commit the ``__snapshots__/`` dir.
"""

import pytest
from syrupy.extensions.json import JSONSnapshotExtension

from evaluation.metrics import aggregate_metrics, calculate_metrics_from_results


@pytest.fixture
def snapshot(snapshot):
    """Use diffable JSON serialisation instead of the default amber format."""
    return snapshot.use_extension(JSONSnapshotExtension)


# ── Fixed per-query rows (all 12 keys produced by calculate_metrics_from_results) ──

_ZERO_QUERY: dict = {
    "recall@1": 0.0,
    "recall@5": 0.0,
    "recall@7": 0.0,
    "recall@10": 0.0,
    "precision@1": 0.0,
    "precision@5": 0.0,
    "precision@10": 0.0,
    "mrr": 0.0,
    "ndcg@5": 0.0,
    "ndcg@10": 0.0,
    "hit": False,
    "hit@7": False,
}

_ONE_QUERY: dict = {
    "recall@1": 1.0,
    "recall@5": 1.0,
    "recall@7": 1.0,
    "recall@10": 1.0,
    "precision@1": 1.0,
    "precision@5": 1.0,
    "precision@10": 1.0,
    "mrr": 1.0,
    "ndcg@5": 1.0,
    "ndcg@10": 1.0,
    "hit": True,
    "hit@7": True,
}


class TestCalculateMetricsFromResultsSnapshot:
    """Snapshot the full 12-key dict for representative input cases.

    These cases mirror the deterministic assertions in test_benchmark_metrics.py
    but capture the *entire* output dict so any new or changed key is caught.
    """

    def test_perfect_retrieval(self, snapshot):
        """A at rank 1 of [A, B]: recall@1=0.5, mrr=1.0, hit=True."""
        result = calculate_metrics_from_results(["A", "B"], ["A", "B"])
        assert result == snapshot

    def test_no_overlap(self, snapshot):
        """Retrieved [X, Y], expected [A, B]: all float metrics = 0, hit=False."""
        result = calculate_metrics_from_results(["X", "Y"], ["A", "B"])
        assert result == snapshot

    def test_expected_primary_override(self, snapshot):
        """X(miss), A(label>=2), B(label=3/primary) at rank 3 → mrr=1/3."""
        result = calculate_metrics_from_results(
            ["X", "A", "B"],
            ["A", "B"],
            expected_primary=["B"],
        )
        assert result == snapshot

    def test_empty_expected(self, snapshot):
        """Empty expected list: all metrics default to 0 (guard in sub-functions)."""
        result = calculate_metrics_from_results(["A", "B"], [])
        assert result == snapshot


class TestAggregateMetricsSnapshot:
    """Snapshot the full aggregate dict including nested pass_fail block.

    These tests also verify that optional line_* keys only appear when present
    in the per-query input, and that custom thresholds override the module-level
    THRESHOLDS constant.
    """

    def test_single_query_all_zeros(self, snapshot):
        """All metrics 0 → pass_fail all FAIL, hit counts 0."""
        result = aggregate_metrics([_ZERO_QUERY])
        assert result == snapshot

    def test_single_query_all_ones(self, snapshot):
        """All metrics 1 → pass_fail all PASS, hit counts 1."""
        result = aggregate_metrics([_ONE_QUERY])
        assert result == snapshot

    def test_two_queries_mixed(self, snapshot):
        """Average of 1.0 and 0.0 → 0.5 for all float metrics; hit_rate@5 = 0.5."""
        result = aggregate_metrics([_ONE_QUERY, _ZERO_QUERY])
        assert result == snapshot

    def test_with_line_overlap_keys(self, snapshot):
        """line_* keys present → aggregated and counted; absent queries skipped."""
        queries = [
            {**_ONE_QUERY, "line_recall": 0.8, "line_precision": 0.9, "line_iou": 0.75},
            {**_ZERO_QUERY, "line_recall": 0.0, "line_precision": 0.0, "line_iou": 0.0},
        ]
        result = aggregate_metrics(queries)
        assert result == snapshot

    def test_custom_thresholds(self, snapshot):
        """Custom thresholds override the module THRESHOLDS for pass_fail."""
        # mrr=0.5 and recall@5=0.5: below defaults (0.50/0.70) → PASS/FAIL
        # but above custom lows (0.4/0.4) → both PASS
        queries = [{**_ZERO_QUERY, "mrr": 0.5, "recall@5": 0.5}]
        custom = {"mrr": 0.4, "recall_at_5": 0.4, "hit_rate_at_5": 0.4}
        result = aggregate_metrics(queries, thresholds=custom)
        assert result == snapshot
