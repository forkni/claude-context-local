"""Unit tests for chunk-level IR benchmark metrics in evaluation/metrics.py.

Tests cover: THRESHOLDS constant, normalize_chunk_id, normalize_chunk_ids,
calculate_recall_at_k, calculate_precision_at_k, calculate_mrr,
calculate_ndcg_at_k, calculate_graded_ndcg_at_k, calculate_acc_at_k,
calculate_hard_negative_intrusion, chunk_ids_to_files, to_file_entries,
calculate_metrics_from_results, and aggregate_metrics.

These are the foundational metrics that drive SSCG benchmark pass/fail decisions.
"""

import math

import pytest

from evaluation.metrics import (
    THRESHOLDS,
    aggregate_metrics,
    calculate_acc_at_k,
    calculate_graded_ndcg_at_k,
    calculate_hard_negative_intrusion,
    calculate_metrics_from_results,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    chunk_ids_to_files,
    normalize_chunk_id,
    normalize_chunk_ids,
    to_file_entries,
)


# ---------------------------------------------------------------------------
# THRESHOLDS constant
# ---------------------------------------------------------------------------


class TestThresholds:
    def test_mrr_threshold(self):
        assert THRESHOLDS["mrr"] == 0.50

    def test_recall_at_5_threshold(self):
        assert THRESHOLDS["recall_at_5"] == 0.70

    def test_hit_rate_at_5_threshold(self):
        assert THRESHOLDS["hit_rate_at_5"] == 0.80


# ---------------------------------------------------------------------------
# normalize_chunk_id
# ---------------------------------------------------------------------------


class TestNormalizeChunkId:
    def test_standard_function_chunk(self):
        raw = "search/config.py:148-161:decorated_definition:EmbeddingConfig"
        assert (
            normalize_chunk_id(raw)
            == "search/config.py:decorated_definition:EmbeddingConfig"
        )

    def test_module_chunk(self):
        # Module chunks have fewer colons — no trailing :name
        raw = "merkle/__init__.py:1-8:module"
        assert normalize_chunk_id(raw) == "merkle/__init__.py:module"

    def test_already_normalized(self):
        # No line-range present — function must be idempotent
        already = "a.py:function:foo"
        assert normalize_chunk_id(already) == "a.py:function:foo"

    def test_only_first_range_stripped(self):
        # count=1 means only the first :\d+-\d+: is removed
        raw = "a.py:1-10:function:foo:20-30:bar"
        assert normalize_chunk_id(raw) == "a.py:function:foo:20-30:bar"

    def test_single_digit_range(self):
        # Boundary: single-line chunk where start == end
        raw = "a.py:1-1:function:tiny"
        assert normalize_chunk_id(raw) == "a.py:function:tiny"

    def test_large_line_numbers(self):
        raw = "big.py:99999-100000:class:Huge"
        assert normalize_chunk_id(raw) == "big.py:class:Huge"

    def test_empty_string(self):
        assert normalize_chunk_id("") == ""

    def test_split_block_collapses_to_method(self):
        raw = "graph/graph_integration.py:276-310:split_block:GraphIntegration.populate_from_embeddings"
        assert (
            normalize_chunk_id(raw)
            == "graph/graph_integration.py:method:GraphIntegration.populate_from_embeddings"
        )

    def test_windows_backslash_canonicalized(self):
        # Delegation to search.chunk_id.dedup_key adds separator canonicalization:
        # backslash and forward-slash forms of one chunk share a normalized ID.
        raw = "search\\reranker.py:36-137:method:rerank"
        assert normalize_chunk_id(raw) == "search/reranker.py:method:rerank"


# ---------------------------------------------------------------------------
# normalize_chunk_ids
# ---------------------------------------------------------------------------


class TestNormalizeChunkIds:
    def test_empty_list(self):
        assert normalize_chunk_ids([]) == []

    def test_single_item(self):
        result = normalize_chunk_ids(["a.py:1-10:function:foo"])
        assert result == ["a.py:function:foo"]

    def test_no_duplicates_after_normalization(self):
        # Distinct chunks — both preserved
        ids = ["a.py:1-10:function:foo", "b.py:5-20:class:Bar"]
        result = normalize_chunk_ids(ids)
        assert result == ["a.py:function:foo", "b.py:class:Bar"]

    def test_dedup_same_raw_ids(self):
        # Identical raw IDs collapse to one
        ids = ["a.py:1-10:function:foo", "a.py:1-10:function:foo"]
        assert normalize_chunk_ids(ids) == ["a.py:function:foo"]

    def test_dedup_different_line_ranges(self):
        # Critical: same logical chunk at two different line positions deduplicates.
        # This is the primary use case — chunk IDs shift as code evolves.
        ids = ["a.py:1-10:function:foo", "a.py:20-30:function:foo"]
        assert normalize_chunk_ids(ids) == ["a.py:function:foo"]

    def test_preserves_first_occurrence_order(self):
        # First occurrence is kept; later duplicates (after normalization) dropped
        ids = ["b.py:1-5:module", "a.py:1-10:function:foo", "b.py:6-12:module"]
        result = normalize_chunk_ids(ids)
        assert result == ["b.py:module", "a.py:function:foo"]

    def test_already_normalized_input(self):
        ids = ["a.py:function:foo", "b.py:class:Bar"]
        assert normalize_chunk_ids(ids) == ["a.py:function:foo", "b.py:class:Bar"]


# ---------------------------------------------------------------------------
# calculate_recall_at_k
# ---------------------------------------------------------------------------


class TestCalculateRecallAtK:
    def test_perfect_recall(self):
        assert calculate_recall_at_k(
            ["A", "B", "C"], ["A", "B", "C"], 3
        ) == pytest.approx(1.0)

    def test_zero_recall(self):
        assert calculate_recall_at_k(["X", "Y", "Z"], ["A", "B"], 3) == pytest.approx(
            0.0
        )

    def test_partial_recall(self):
        # 2 of 3 relevant items found within k=4
        assert calculate_recall_at_k(
            ["A", "X", "B", "Y"], ["A", "B", "C"], 4
        ) == pytest.approx(2 / 3)

    def test_k_limits_retrieval(self):
        # Relevant items C and D are at positions 3 and 4, but k=2 only sees A, B
        assert calculate_recall_at_k(
            ["A", "B", "C", "D"], ["C", "D"], 2
        ) == pytest.approx(0.0)

    def test_k_exceeds_list_length(self):
        # k much larger than retrieved list — slicing handles gracefully
        # A is relevant, B is not in relevant → 1 of 2 relevant found
        assert calculate_recall_at_k(["A"], ["A", "B"], 100) == pytest.approx(0.5)

    def test_empty_relevant(self):
        # Division-by-zero guard: |relevant|=0 → return 0.0
        assert calculate_recall_at_k(["A", "B"], [], 2) == pytest.approx(0.0)

    def test_empty_retrieved(self):
        assert calculate_recall_at_k([], ["A", "B"], 5) == pytest.approx(0.0)

    def test_both_empty(self):
        assert calculate_recall_at_k([], [], 5) == pytest.approx(0.0)

    def test_k_equals_one_hit(self):
        assert calculate_recall_at_k(["A", "B"], ["A"], 1) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_precision_at_k
# ---------------------------------------------------------------------------


class TestCalculatePrecisionAtK:
    def test_perfect_precision(self):
        assert calculate_precision_at_k(["A", "B"], ["A", "B"], 2) == pytest.approx(1.0)

    def test_zero_precision(self):
        assert calculate_precision_at_k(["X", "Y"], ["A", "B"], 2) == pytest.approx(0.0)

    def test_partial_precision(self):
        # 2 hits in 3 slots
        assert calculate_precision_at_k(
            ["A", "X", "B"], ["A", "B"], 3
        ) == pytest.approx(2 / 3)

    def test_k_larger_than_retrieved(self):
        # Denominator is k=5, not len(retrieved)=1; only A is hit
        assert calculate_precision_at_k(["A"], ["A", "B"], 5) == pytest.approx(1 / 5)

    def test_k_equals_zero(self):
        # Division-by-zero guard: k=0 → 0.0
        assert calculate_precision_at_k(["A"], ["A"], 0) == pytest.approx(0.0)

    def test_empty_retrieved(self):
        assert calculate_precision_at_k([], ["A"], 3) == pytest.approx(0.0)

    def test_empty_relevant(self):
        assert calculate_precision_at_k(["A", "B"], [], 2) == pytest.approx(0.0)

    def test_both_empty(self):
        assert calculate_precision_at_k([], [], 5) == pytest.approx(0.0)

    def test_precision_at_1_with_hit(self):
        assert calculate_precision_at_k(["A", "X"], ["A"], 1) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_mrr
# ---------------------------------------------------------------------------


class TestCalculateMrr:
    def test_first_position(self):
        assert calculate_mrr(["A", "B", "C"], ["A"]) == pytest.approx(1.0)

    def test_second_position(self):
        assert calculate_mrr(["X", "A", "C"], ["A"]) == pytest.approx(0.5)

    def test_third_position(self):
        assert calculate_mrr(["X", "Y", "A"], ["A"]) == pytest.approx(1 / 3)

    def test_no_hit(self):
        assert calculate_mrr(["X", "Y", "Z"], ["A"]) == pytest.approx(0.0)

    def test_multiple_relevant_uses_first(self):
        # A is at rank 2, B at rank 3 — MRR uses first hit (rank 2 = 0.5)
        assert calculate_mrr(["X", "A", "B"], ["A", "B"]) == pytest.approx(0.5)

    def test_empty_retrieved(self):
        assert calculate_mrr([], ["A"]) == pytest.approx(0.0)

    def test_empty_relevant(self):
        # relevant_set is empty; loop body never matches → 0.0
        assert calculate_mrr(["A", "B"], []) == pytest.approx(0.0)

    def test_both_empty(self):
        assert calculate_mrr([], []) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calculate_ndcg_at_k
# ---------------------------------------------------------------------------


class TestCalculateNdcgAtK:
    def test_perfect_ndcg(self):
        # Both relevant items at top → DCG = IDCG → 1.0
        assert calculate_ndcg_at_k(["A", "B"], ["A", "B"], 2) == pytest.approx(1.0)

    def test_zero_ndcg_no_hits(self):
        assert calculate_ndcg_at_k(["X", "Y", "Z"], ["A", "B"], 3) == pytest.approx(0.0)

    def test_single_relevant_at_top(self):
        # DCG = 1/log2(2) = 1.0, IDCG = 1/log2(2) = 1.0 → ratio = 1.0
        assert calculate_ndcg_at_k(["A", "X", "Y"], ["A"], 3) == pytest.approx(1.0)

    def test_relevant_at_various_positions(self):
        # retrieved: A at rank 1, B at rank 3, C at rank 5 (k=5)
        # relevant: A, B, C (3 items)
        # DCG = 1/log2(2) + 1/log2(4) + 1/log2(6)
        # IDCG = 1/log2(2) + 1/log2(3) + 1/log2(4)  (ideal: 3 hits at top 3)
        dcg = 1 / math.log2(2) + 1 / math.log2(4) + 1 / math.log2(6)
        idcg = 1 / math.log2(2) + 1 / math.log2(3) + 1 / math.log2(4)
        expected = dcg / idcg
        result = calculate_ndcg_at_k(["A", "X", "B", "X", "C"], ["A", "B", "C"], 5)
        assert result == pytest.approx(expected)

    def test_relevant_at_last_position(self):
        # Worst-case: single relevant item at position k=5
        # DCG = 1/log2(6), IDCG = 1/log2(2)
        dcg = 1 / math.log2(6)
        idcg = 1 / math.log2(2)
        expected = dcg / idcg
        result = calculate_ndcg_at_k(["X", "X", "X", "X", "A"], ["A"], 5)
        assert result == pytest.approx(expected)

    def test_k_smaller_than_relevant(self):
        # k=2, 3 relevant items; IDCG uses min(3, 2) = 2 ideal positions
        # All 3 retrieved are relevant, k=2 cuts off at position 2
        # DCG = 1/log2(2) + 1/log2(3), IDCG = 1/log2(2) + 1/log2(3) → perfect within k
        assert calculate_ndcg_at_k(
            ["A", "B", "C"], ["A", "B", "C"], 2
        ) == pytest.approx(1.0)

    def test_k_larger_than_retrieved(self):
        # Only 1 item retrieved but k=5; 2 relevant items
        # DCG = 1/log2(2) (A hit at rank 1)
        # IDCG = 1/log2(2) + 1/log2(3) (ideal: 2 items at top)
        dcg = 1 / math.log2(2)
        idcg = 1 / math.log2(2) + 1 / math.log2(3)
        expected = dcg / idcg
        result = calculate_ndcg_at_k(["A"], ["A", "B"], 5)
        assert result == pytest.approx(expected)

    def test_empty_relevant(self):
        # IDCG = 0 → guard returns 0.0
        assert calculate_ndcg_at_k(["A", "B"], [], 5) == pytest.approx(0.0)

    def test_empty_retrieved(self):
        # DCG = 0, IDCG > 0 → 0.0
        assert calculate_ndcg_at_k([], ["A", "B"], 5) == pytest.approx(0.0)

    def test_k_equals_one_with_hit(self):
        assert calculate_ndcg_at_k(["A", "B"], ["A"], 1) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_graded_ndcg_at_k
# ---------------------------------------------------------------------------


class TestCalculateGradedNdcgAtK:
    def test_perfect_ranking_by_grade(self):
        # Grades sorted descending already at the top → DCG == IDCG → 1.0
        grades = {"A": 3, "B": 2, "C": 1}
        assert calculate_graded_ndcg_at_k(["A", "B", "C"], grades, 3) == pytest.approx(
            1.0
        )

    def test_reversed_grade_order_scores_below_one(self):
        # Worst gains at the top → DCG < IDCG
        grades = {"A": 3, "B": 2, "C": 1}
        result = calculate_graded_ndcg_at_k(["C", "B", "A"], grades, 3)
        assert 0.0 < result < 1.0

    def test_unlabeled_id_scores_grade_zero(self):
        # "X" isn't in relevance_grades → treated as grade 0, contributes no gain
        grades = {"A": 3}
        dcg = (2**3 - 1) / math.log2(2) + 0.0 / math.log2(3)
        idcg = (2**3 - 1) / math.log2(2)
        assert calculate_graded_ndcg_at_k(["A", "X"], grades, 2) == pytest.approx(
            dcg / idcg
        )

    def test_all_zero_grades_returns_zero(self):
        # Every labeled grade is 0 → idcg == 0 → guard returns 0.0
        grades = {"A": 0, "B": 0}
        assert calculate_graded_ndcg_at_k(["A", "B"], grades, 2) == pytest.approx(0.0)

    def test_empty_grades_returns_zero(self):
        assert calculate_graded_ndcg_at_k(["A", "B"], {}, 2) == pytest.approx(0.0)

    def test_containment_credit_uses_max_grade(self):
        # A merged entry credited for both "A" (grade 1) and "B" (grade 3)
        # takes the higher grade at that rank.
        grades = {"A": 1, "B": 3}
        result = calculate_graded_ndcg_at_k([{"A", "B"}], grades, 1)
        assert result == pytest.approx(1.0)

    def test_exponential_gain_not_linear(self):
        # A single grade-3 hit at rank 1 must score strictly above a single
        # grade-1 hit at rank 1 relative to their own ideal (both are 1.0
        # individually) -- verify the *raw* gain uses 2**rel - 1, not rel,
        # by comparing DCG contributions directly via a shared IDCG denominator.
        grades_both = {"A": 3, "B": 1}
        # "A" (grade 3) ranked first beats "B" (grade 1) ranked first.
        best = calculate_graded_ndcg_at_k(["A", "B"], grades_both, 2)
        worst = calculate_graded_ndcg_at_k(["B", "A"], grades_both, 2)
        assert best == pytest.approx(1.0)
        assert worst < best


# ---------------------------------------------------------------------------
# calculate_acc_at_k
# ---------------------------------------------------------------------------


class TestCalculateAccAtK:
    def test_full_coverage_scores_one(self):
        assert calculate_acc_at_k(["A", "B", "X"], ["A", "B"], 3) == pytest.approx(1.0)

    def test_partial_coverage_scores_zero(self):
        # Recall@k would be 0.5 here; Acc@k is all-or-nothing → 0.0
        assert calculate_acc_at_k(["A", "X"], ["A", "B"], 2) == pytest.approx(0.0)

    def test_k_excludes_second_relevant_id(self):
        assert calculate_acc_at_k(["A", "X", "B"], ["A", "B"], 2) == pytest.approx(0.0)

    def test_empty_relevant_scores_zero(self):
        # Mirrors calculate_recall_at_k's empty-relevant guard, not vacuous truth
        assert calculate_acc_at_k(["A", "B"], [], 2) == pytest.approx(0.0)

    def test_empty_retrieved_scores_zero(self):
        assert calculate_acc_at_k([], ["A"], 5) == pytest.approx(0.0)

    def test_containment_credit_entry_covers_multiple_ids(self):
        # A single merged entry credited for both A and B covers the full set
        assert calculate_acc_at_k([{"A", "B"}], ["A", "B"], 1) == pytest.approx(1.0)

    def test_acc_never_exceeds_recall(self):
        retrieved = ["A", "X", "Y"]
        relevant = ["A", "B"]
        acc = calculate_acc_at_k(retrieved, relevant, 3)
        recall = calculate_recall_at_k(retrieved, relevant, 3)
        assert acc <= recall


# ---------------------------------------------------------------------------
# calculate_hard_negative_intrusion
# ---------------------------------------------------------------------------


class TestCalculateHardNegativeIntrusion:
    def test_negative_before_positive_is_true(self):
        result = calculate_hard_negative_intrusion(
            ["N", "P"], positive_ids=["P"], hard_negative_ids=["N"], k=10
        )
        assert result is True

    def test_positive_before_negative_is_false(self):
        result = calculate_hard_negative_intrusion(
            ["P", "N"], positive_ids=["P"], hard_negative_ids=["N"], k=10
        )
        assert result is False

    def test_no_positive_in_topk_is_none(self):
        result = calculate_hard_negative_intrusion(
            ["N", "X"], positive_ids=["P"], hard_negative_ids=["N"], k=10
        )
        assert result is None

    def test_no_negative_in_topk_is_none(self):
        result = calculate_hard_negative_intrusion(
            ["P", "X"], positive_ids=["P"], hard_negative_ids=["N"], k=10
        )
        assert result is None

    def test_neither_in_topk_is_none(self):
        result = calculate_hard_negative_intrusion(
            ["X", "Y"], positive_ids=["P"], hard_negative_ids=["N"], k=10
        )
        assert result is None

    def test_k_cutoff_excludes_late_negative(self):
        # Negative appears at rank 3, but k=2 never sees it
        result = calculate_hard_negative_intrusion(
            ["P", "X", "N"], positive_ids=["P"], hard_negative_ids=["N"], k=2
        )
        assert result is None

    def test_empty_hard_negatives_is_none(self):
        result = calculate_hard_negative_intrusion(
            ["P"], positive_ids=["P"], hard_negative_ids=[], k=10
        )
        assert result is None


# ---------------------------------------------------------------------------
# chunk_ids_to_files / to_file_entries
# ---------------------------------------------------------------------------


class TestFileLevelRollup:
    def test_chunk_ids_to_files_extracts_path(self):
        ids = ["a/b.py:function:foo", "a/b.py:class:Bar", "c/d.py:module"]
        assert chunk_ids_to_files(ids) == {"a/b.py", "c/d.py"}

    def test_chunk_ids_to_files_empty(self):
        assert chunk_ids_to_files([]) == set()

    def test_to_file_entries_maps_each_rank(self):
        entries = ["a/b.py:function:foo", "c/d.py:class:Bar"]
        assert to_file_entries(entries) == [{"a/b.py"}, {"c/d.py"}]

    def test_to_file_entries_preserves_containment_sets(self):
        # A merged rank credited for two chunk IDs in the same file collapses
        # to a single-file set.
        entries = [{"a/b.py:function:foo", "a/b.py:method:Bar.baz"}]
        assert to_file_entries(entries) == [{"a/b.py"}]

    def test_file_rollup_feeds_recall_at_k_unchanged(self):
        # Two chunks from the same relevant file both count as one file hit.
        retrieved = to_file_entries(["a/b.py:function:foo", "x/y.py:function:other"])
        relevant_files = list(chunk_ids_to_files(["a/b.py:function:foo"]))
        assert calculate_recall_at_k(retrieved, relevant_files, 2) == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# calculate_metrics_from_results
# ---------------------------------------------------------------------------


_EXPECTED_KEYS = {
    "recall@1",
    "recall@5",
    "recall@7",
    "recall@10",
    "recall@20",
    "recall@50",
    "precision@1",
    "precision@5",
    "precision@10",
    "mrr",
    "ndcg@5",
    "ndcg@10",
    "acc@5",
    "acc@10",
    "hit",
    "hit@7",
}

# Additional keys present only when relevance_grades is passed.
_EXPECTED_GRADED_KEYS = _EXPECTED_KEYS | {
    "ndcg@5_graded",
    "ndcg@10_graded",
    "hard_negative_intrusion",
}


class TestCalculateMetricsFromResults:
    def test_returns_all_expected_keys(self):
        result = calculate_metrics_from_results(["A"], ["A"])
        assert set(result.keys()) == _EXPECTED_KEYS

    def test_perfect_retrieval(self):
        retrieved = ["A", "B"]
        expected = ["A", "B"]
        result = calculate_metrics_from_results(retrieved, expected)
        assert result["recall@1"] == pytest.approx(0.5)  # only A in top-1 of 2 expected
        assert result["recall@5"] == pytest.approx(1.0)  # both in top-5
        assert result["precision@1"] == pytest.approx(1.0)  # A is relevant
        assert result["precision@5"] == pytest.approx(2 / 5)  # 2 hits / 5 slots
        assert result["mrr"] == pytest.approx(1.0)  # A at rank 1
        assert result["ndcg@5"] == pytest.approx(1.0)
        assert result["hit"] is True

    def test_no_overlap(self):
        result = calculate_metrics_from_results(["X", "Y"], ["A", "B"])
        for key in (
            "recall@1",
            "recall@5",
            "recall@10",
            "precision@1",
            "precision@5",
            "precision@10",
            "mrr",
            "ndcg@5",
            "ndcg@10",
        ):
            assert result[key] == pytest.approx(0.0), f"{key} should be 0.0"
        assert result["hit"] is False

    def test_empty_expected(self):
        # All guards in sub-functions return 0.0 when relevant is empty
        result = calculate_metrics_from_results(["A", "B"], [])
        for key in (
            "recall@1",
            "recall@5",
            "recall@10",
            "precision@1",
            "precision@5",
            "precision@10",
            "mrr",
            "ndcg@5",
            "ndcg@10",
        ):
            assert result[key] == pytest.approx(0.0), f"{key} should be 0.0"
        assert result["hit"] is False

    def test_expected_primary_used_for_mrr(self):
        # retrieved: X(miss), A(relevant), B(primary)
        # expected = ["A", "B"] (label>=2), expected_primary = ["B"] (label=3)
        # MRR should find B at rank 3 → 1/3
        # recall@5 uses expected=["A","B"] → both found → 1.0
        result = calculate_metrics_from_results(
            retrieved=["X", "A", "B"],
            expected=["A", "B"],
            expected_primary=["B"],
        )
        assert result["mrr"] == pytest.approx(1 / 3)
        assert result["recall@5"] == pytest.approx(1.0)

    def test_expected_primary_none_falls_back(self):
        # When expected_primary is None, MRR falls back to expected
        # A is at rank 1 → MRR = 1.0
        result = calculate_metrics_from_results(
            retrieved=["A", "B"],
            expected=["A", "B"],
            expected_primary=None,
        )
        assert result["mrr"] == pytest.approx(1.0)

    def test_hit_is_boolean(self):
        result = calculate_metrics_from_results(["A"], ["A"])
        assert isinstance(result["hit"], bool)

    def test_hit_false_when_no_recall_at_5(self):
        # 10 misses in a row — recall@5 = 0
        result = calculate_metrics_from_results(["X"] * 10, ["A"])
        assert result["hit"] is False

    def test_acc_at_k_full_coverage(self):
        result = calculate_metrics_from_results(["A", "B"], ["A", "B"])
        assert result["acc@5"] == pytest.approx(1.0)
        assert result["acc@10"] == pytest.approx(1.0)

    def test_acc_at_k_partial_coverage_scores_zero(self):
        result = calculate_metrics_from_results(["A", "X"], ["A", "B"])
        assert result["acc@5"] == pytest.approx(0.0)

    def test_relevance_grades_omitted_by_default(self):
        # No relevance_grades passed → graded keys entirely absent, not 0.0/None
        result = calculate_metrics_from_results(["A"], ["A"])
        assert set(result.keys()) == _EXPECTED_KEYS
        assert "ndcg@5_graded" not in result
        assert "hard_negative_intrusion" not in result

    def test_relevance_grades_adds_graded_keys(self):
        result = calculate_metrics_from_results(
            ["A", "B"],
            ["A", "B"],
            relevance_grades={"A": 3, "B": 2},
        )
        assert set(result.keys()) == _EXPECTED_GRADED_KEYS
        assert result["ndcg@5_graded"] == pytest.approx(1.0)
        assert result["ndcg@10_graded"] == pytest.approx(1.0)

    def test_relevance_grades_derives_hard_negatives_as_grade_one(self):
        # "N" is grade 1 → treated as a hard negative; ranked before the
        # positive "P" (grade 2) → intrusion True.
        result = calculate_metrics_from_results(
            ["N", "P"],
            ["P"],
            relevance_grades={"N": 1, "P": 2},
        )
        assert result["hard_negative_intrusion"] is True

    def test_relevance_grades_no_grade_one_ids_is_none(self):
        # No grade-1 label present → hard_negative_ids empty → always None
        result = calculate_metrics_from_results(
            ["P"],
            ["P"],
            relevance_grades={"P": 3},
        )
        assert result["hard_negative_intrusion"] is None


# ---------------------------------------------------------------------------
# aggregate_metrics
# ---------------------------------------------------------------------------

_ALL_ZERO_QUERY: dict = {
    "recall@1": 0.0,
    "recall@5": 0.0,
    "recall@10": 0.0,
    "precision@1": 0.0,
    "precision@5": 0.0,
    "precision@10": 0.0,
    "mrr": 0.0,
    "ndcg@5": 0.0,
    "ndcg@10": 0.0,
    "acc@5": 0.0,
    "acc@10": 0.0,
    "hit": False,
}

_ALL_ONE_QUERY: dict = {
    "recall@1": 1.0,
    "recall@5": 1.0,
    "recall@10": 1.0,
    "precision@1": 1.0,
    "precision@5": 1.0,
    "precision@10": 1.0,
    "mrr": 1.0,
    "ndcg@5": 1.0,
    "ndcg@10": 1.0,
    "acc@5": 1.0,
    "acc@10": 1.0,
    "hit": True,
}


class TestAggregateMetrics:
    def test_empty_input(self):
        assert aggregate_metrics([]) == {}

    def test_single_query_perfect(self):
        agg = aggregate_metrics([_ALL_ONE_QUERY])
        assert agg["total_queries"] == 1
        assert agg["success_count"] == 1
        assert agg["hit_rate@5"] == pytest.approx(1.0)
        assert agg["mrr"] == pytest.approx(1.0)
        assert agg["recall@5"] == pytest.approx(1.0)
        assert agg["pass_fail"]["mrr"] == "PASS"
        assert agg["pass_fail"]["recall@5"] == "PASS"
        assert agg["pass_fail"]["hit_rate@5"] == "PASS"

    def test_single_query_all_zeros(self):
        agg = aggregate_metrics([_ALL_ZERO_QUERY])
        assert agg["total_queries"] == 1
        assert agg["success_count"] == 0
        assert agg["hit_rate@5"] == pytest.approx(0.0)
        assert agg["mrr"] == pytest.approx(0.0)
        assert agg["pass_fail"]["mrr"] == "FAIL"
        assert agg["pass_fail"]["recall@5"] == "FAIL"
        assert agg["pass_fail"]["hit_rate@5"] == "FAIL"

    def test_two_queries_averaging(self):
        # Average of 1.0 and 0.0 = 0.5 for each float metric
        agg = aggregate_metrics([_ALL_ONE_QUERY, _ALL_ZERO_QUERY])
        assert agg["total_queries"] == 2
        assert agg["success_count"] == 1
        assert agg["hit_rate@5"] == pytest.approx(0.5)
        assert agg["mrr"] == pytest.approx(0.5)
        assert agg["recall@5"] == pytest.approx(0.5)
        assert agg["ndcg@5"] == pytest.approx(0.5)

    def test_pass_fail_at_boundary_mrr(self):
        # MRR exactly 0.50 → PASS (threshold uses >=)
        q = {**_ALL_ZERO_QUERY, "mrr": 0.50}
        agg = aggregate_metrics([q])
        assert agg["pass_fail"]["mrr"] == "PASS"

    def test_pass_fail_below_boundary_mrr(self):
        # MRR just below threshold → FAIL
        q = {**_ALL_ZERO_QUERY, "mrr": 0.49}
        agg = aggregate_metrics([q])
        assert agg["pass_fail"]["mrr"] == "FAIL"

    def test_pass_fail_recall_at_5_boundary(self):
        # recall@5 exactly 0.70 → PASS
        q = {**_ALL_ZERO_QUERY, "recall@5": 0.70}
        agg = aggregate_metrics([q])
        assert agg["pass_fail"]["recall@5"] == "PASS"

    def test_pass_fail_hit_rate_boundary(self):
        # 3/4 hits = 0.75 < 0.80 threshold → FAIL
        queries = [
            {**_ALL_ZERO_QUERY, "hit": True},
            {**_ALL_ZERO_QUERY, "hit": True},
            {**_ALL_ZERO_QUERY, "hit": True},
            {**_ALL_ZERO_QUERY, "hit": False},
        ]
        agg = aggregate_metrics(queries)
        assert agg["hit_rate@5"] == pytest.approx(0.75)
        assert agg["pass_fail"]["hit_rate@5"] == "FAIL"

    def test_missing_key_treated_as_zero(self):
        # Query dict missing 'mrr' — get(key, 0.0) defaults it to 0.0
        q_no_mrr = {k: v for k, v in _ALL_ONE_QUERY.items() if k != "mrr"}
        agg = aggregate_metrics([q_no_mrr])
        assert agg["mrr"] == pytest.approx(0.0)

    def test_line_overlap_keys_only_when_present(self):
        # Only one of two queries has line_recall — averaged across that one only
        q_with = {
            **_ALL_ONE_QUERY,
            "line_recall": 0.8,
            "line_precision": 0.6,
            "line_iou": 0.5,
        }
        q_without = {**_ALL_ONE_QUERY}
        agg = aggregate_metrics([q_with, q_without])
        assert agg["line_recall"] == pytest.approx(0.8)
        assert agg["line_precision"] == pytest.approx(0.6)
        assert agg["line_iou"] == pytest.approx(0.5)
        assert agg["line_recall_count"] == 1

    def test_line_overlap_keys_absent_when_none_have_them(self):
        # No query has line-overlap keys → keys must not appear in result
        agg = aggregate_metrics([_ALL_ONE_QUERY, _ALL_ZERO_QUERY])
        assert "line_recall" not in agg
        assert "line_precision" not in agg
        assert "line_iou" not in agg

    def test_hit_rate_computation(self):
        # 2 hits out of 3 queries → 0.6667 rounded to 4 decimal places
        queries = [
            {**_ALL_ONE_QUERY},
            {**_ALL_ONE_QUERY},
            {**_ALL_ZERO_QUERY},
        ]
        agg = aggregate_metrics(queries)
        assert agg["hit_rate@5"] == pytest.approx(2 / 3, abs=1e-4)
        assert agg["success_count"] == 2
        assert agg["total_queries"] == 3

    def test_acc_at_k_averaged_via_float_keys(self):
        agg = aggregate_metrics([_ALL_ONE_QUERY, _ALL_ZERO_QUERY])
        assert agg["acc@5"] == pytest.approx(0.5)
        assert agg["acc@10"] == pytest.approx(0.5)

    def test_graded_ndcg_keys_only_when_present(self):
        q_with = {**_ALL_ONE_QUERY, "ndcg@5_graded": 0.9, "ndcg@10_graded": 0.8}
        q_without = {**_ALL_ONE_QUERY}
        agg = aggregate_metrics([q_with, q_without])
        assert agg["ndcg@5_graded"] == pytest.approx(0.9)
        assert agg["ndcg@10_graded"] == pytest.approx(0.8)
        assert agg["ndcg@5_graded_count"] == 1

    def test_graded_ndcg_keys_absent_when_none_have_them(self):
        agg = aggregate_metrics([_ALL_ONE_QUERY, _ALL_ZERO_QUERY])
        assert "ndcg@5_graded" not in agg
        assert "ndcg@10_graded" not in agg

    def test_file_rollup_keys_only_when_present(self):
        q_with = {**_ALL_ONE_QUERY, "file_recall@5": 0.7, "file_acc@10": 0.4}
        q_without = {**_ALL_ONE_QUERY}
        agg = aggregate_metrics([q_with, q_without])
        assert agg["file_recall@5"] == pytest.approx(0.7)
        assert agg["file_acc@10"] == pytest.approx(0.4)
        assert "file_recall@10" not in agg
        assert "file_acc@5" not in agg

    def test_hard_negative_intrusion_rate_excludes_none_rows(self):
        # Only rows with a non-None hard_negative_intrusion count toward the rate.
        queries = [
            {**_ALL_ONE_QUERY, "hard_negative_intrusion": True},
            {**_ALL_ONE_QUERY, "hard_negative_intrusion": False},
            {**_ALL_ONE_QUERY, "hard_negative_intrusion": None},
            {**_ALL_ONE_QUERY},  # key absent entirely
        ]
        agg = aggregate_metrics(queries)
        assert agg["hard_negative_intrusion_rate"] == pytest.approx(0.5)
        assert agg["hard_negative_intrusion_count"] == 2

    def test_hard_negative_intrusion_rate_absent_when_all_none(self):
        queries = [
            {**_ALL_ONE_QUERY, "hard_negative_intrusion": None},
            {**_ALL_ONE_QUERY},
        ]
        agg = aggregate_metrics(queries)
        assert "hard_negative_intrusion_rate" not in agg
