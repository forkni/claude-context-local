"""Unit tests for line-range overlap metrics in evaluation/metrics.py.

Tests cover the Chroma-style IoU/Recall/Precision adapted to source line ranges,
including the range arithmetic helpers and the MetadataStore resolution utilities.
"""

import pytest

from evaluation.metrics import (
    THRESHOLDS,
    aggregate_metrics,
    build_chunk_line_lookup,
    calculate_line_iou,
    calculate_line_precision,
    calculate_line_recall,
    count_lines,
    intersect_ranges,
    merge_ranges,
    resolve_chunk_ids_to_ranges,
)


# ---------------------------------------------------------------------------
# merge_ranges
# ---------------------------------------------------------------------------


class TestMergeRanges:
    def test_empty(self):
        assert merge_ranges([]) == []

    def test_single(self):
        assert merge_ranges([(5, 10)]) == [(5, 10)]

    def test_disjoint(self):
        assert merge_ranges([(1, 3), (5, 7)]) == [(1, 3), (5, 7)]

    def test_overlapping(self):
        assert merge_ranges([(1, 5), (3, 8)]) == [(1, 8)]

    def test_adjacent(self):
        # Lines 1-3 and 4-6 are adjacent (no gap), should merge
        assert merge_ranges([(1, 3), (4, 6)]) == [(1, 6)]

    def test_contained(self):
        # Inner range fully contained in outer
        assert merge_ranges([(1, 10), (3, 7)]) == [(1, 10)]

    def test_multiple_overlapping(self):
        result = merge_ranges([(1, 5), (3, 8), (12, 15)])
        assert result == [(1, 8), (12, 15)]

    def test_unsorted_input(self):
        # Should sort before merging
        assert merge_ranges([(10, 15), (1, 5), (3, 7)]) == [(1, 7), (10, 15)]

    def test_identical_ranges(self):
        assert merge_ranges([(5, 10), (5, 10)]) == [(5, 10)]

    def test_third_range_overlaps_second_not_first(self):
        """Kills merged[-1→0] mutation: 3rd range overlaps 2nd group, not 1st.

        With mutation merged[0]=... instead of merged[-1]=..., the 3rd range
        incorrectly updates the first group instead of the last.
        """
        # (1,3) and (5,7) don't overlap → two groups. (6,9) overlaps (5,7) → extends it.
        assert merge_ranges([(1, 3), (5, 7), (6, 9)]) == [(1, 3), (5, 9)]


# ---------------------------------------------------------------------------
# intersect_ranges
# ---------------------------------------------------------------------------


class TestIntersectRanges:
    def test_empty_both(self):
        assert intersect_ranges([], []) == []

    def test_empty_one(self):
        assert intersect_ranges([(1, 10)], []) == []
        assert intersect_ranges([], [(1, 10)]) == []

    def test_full_overlap(self):
        assert intersect_ranges([(1, 10)], [(1, 10)]) == [(1, 10)]

    def test_partial_overlap(self):
        assert intersect_ranges([(1, 10)], [(5, 15)]) == [(5, 10)]

    def test_no_overlap(self):
        assert intersect_ranges([(1, 5)], [(7, 10)]) == []

    def test_one_contains_other(self):
        assert intersect_ranges([(1, 20)], [(5, 10)]) == [(5, 10)]

    def test_multiple_ranges(self):
        a = [(1, 5), (10, 15)]
        b = [(3, 12)]
        result = intersect_ranges(a, b)
        assert result == [(3, 5), (10, 12)]

    def test_adjacent_no_overlap(self):
        # (1,3) and (4,6) share no lines — adjacent but not overlapping
        assert intersect_ranges([(1, 3)], [(4, 6)]) == []

    def test_single_line_overlap(self):
        assert intersect_ranges([(1, 5)], [(5, 10)]) == [(5, 5)]

    def test_two_element_b_forces_j_advance(self):
        # single wide a, two b ranges → j advances twice while i stays at 0
        assert intersect_ranges([(1, 20)], [(3, 5), (8, 10)]) == [(3, 5), (8, 10)]

    def test_both_pointers_advance_with_overlaps(self):
        # i and j both advance, interleaved: kills i/j-pointer-advance mutants
        assert intersect_ranges([(1, 5), (8, 15)], [(3, 10), (12, 20)]) == [
            (3, 5),
            (8, 10),
            (12, 15),
        ]


# ---------------------------------------------------------------------------
# count_lines
# ---------------------------------------------------------------------------


class TestCountLines:
    def test_empty(self):
        assert count_lines([]) == 0

    def test_single_line(self):
        assert count_lines([(5, 5)]) == 1

    def test_range_inclusive(self):
        # (5, 8) = lines 5, 6, 7, 8 = 4 lines
        assert count_lines([(5, 8)]) == 4

    def test_multiple_ranges(self):
        assert count_lines([(1, 3), (10, 12)]) == 6

    def test_large_range(self):
        assert count_lines([(1, 100)]) == 100


# ---------------------------------------------------------------------------
# calculate_line_recall
# ---------------------------------------------------------------------------


class TestCalculateLineRecall:
    def test_perfect_recall(self):
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 10)]}
        assert calculate_line_recall(retrieved, golden) == 1.0

    def test_zero_recall_different_file(self):
        golden = {"file.py": [(1, 10)]}
        retrieved = {"other.py": [(1, 10)]}
        assert calculate_line_recall(retrieved, golden) == 0.0

    def test_zero_recall_empty_retrieved(self):
        golden = {"file.py": [(1, 10)]}
        assert calculate_line_recall({}, golden) == 0.0

    def test_partial_recall(self):
        # Golden is lines 1-10 (10 lines), retrieved covers lines 1-5 (5 lines)
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 5)]}
        assert calculate_line_recall(retrieved, golden) == pytest.approx(0.5)

    def test_empty_golden(self):
        assert calculate_line_recall({"file.py": [(1, 10)]}, {}) == 0.0

    def test_multi_file(self):
        # Golden: file_a lines 1-10 (10), file_b lines 1-5 (5) = 15 total
        # Retrieved: file_a lines 1-10 (fully covered), file_b not covered
        golden = {"file_a.py": [(1, 10)], "file_b.py": [(1, 5)]}
        retrieved = {"file_a.py": [(1, 10)]}
        assert calculate_line_recall(retrieved, golden) == pytest.approx(10 / 15)

    def test_overlapping_retrieved_still_counts_once(self):
        # Two retrieved chunks cover same lines — should not double-count
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 7), (5, 10)]}
        assert calculate_line_recall(retrieved, golden) == 1.0

    def test_retrieved_extends_beyond_golden(self):
        # Retrieved covers more than golden — recall should be 1.0
        golden = {"file.py": [(5, 8)]}
        retrieved = {"file.py": [(1, 20)]}
        assert calculate_line_recall(retrieved, golden) == 1.0


# ---------------------------------------------------------------------------
# calculate_line_precision
# ---------------------------------------------------------------------------


class TestCalculateLinePrecision:
    def test_perfect_precision(self):
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 10)]}
        assert calculate_line_precision(retrieved, golden) == 1.0

    def test_zero_precision_no_overlap(self):
        golden = {"file.py": [(1, 5)]}
        retrieved = {"file.py": [(10, 15)]}
        assert calculate_line_precision(retrieved, golden) == 0.0

    def test_empty_retrieved(self):
        golden = {"file.py": [(1, 10)]}
        assert calculate_line_precision({}, golden) == 0.0

    def test_retrieved_larger_than_golden(self):
        # Retrieved 1-20 (20 lines raw), golden 1-10 (10 lines overlap)
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 20)]}
        assert calculate_line_precision(retrieved, golden) == pytest.approx(10 / 20)

    def test_redundant_chunks_penalized(self):
        # Two chunks each covering lines 1-10 = 20 raw retrieved lines
        # Overlap with golden (1-10) = 10 lines
        # Precision = 10/20 = 0.5 (penalized for redundancy)
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 10), (1, 10)]}
        assert calculate_line_precision(retrieved, golden) == pytest.approx(0.5)

    def test_partial_precision(self):
        # Retrieved 1-10 (10 lines), golden 5-10 (6 lines overlap)
        golden = {"file.py": [(5, 10)]}
        retrieved = {"file.py": [(1, 10)]}
        assert calculate_line_precision(retrieved, golden) == pytest.approx(6 / 10)

    def test_denominator_inclusive_length_start_gt_1(self):
        # (3,5) = 3 lines inclusive; Add→Mod mutant `end-start%1` yields 5 → precision 3/5
        golden = {"file.py": [(3, 5)]}
        retrieved = {"file.py": [(3, 5)]}
        assert calculate_line_precision(retrieved, golden) == 1.0


# ---------------------------------------------------------------------------
# calculate_line_iou
# ---------------------------------------------------------------------------


class TestCalculateLineIou:
    def test_perfect_iou(self):
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(1, 10)]}
        assert calculate_line_iou(retrieved, golden) == 1.0

    def test_zero_iou_no_overlap(self):
        golden = {"file.py": [(1, 5)]}
        retrieved = {"file.py": [(10, 15)]}
        assert calculate_line_iou(retrieved, golden) == 0.0

    def test_zero_iou_empty_retrieved(self):
        golden = {"file.py": [(1, 10)]}
        assert calculate_line_iou({}, golden) == 0.0

    def test_partial_iou(self):
        # golden 1-10 (10 lines), retrieved 5-15 (11 lines)
        # overlap 5-10 (6 lines), union = 10 + 11 - 6 = 15
        golden = {"file.py": [(1, 10)]}
        retrieved = {"file.py": [(5, 15)]}
        assert calculate_line_iou(retrieved, golden) == pytest.approx(6 / 15)

    def test_multi_file(self):
        # golden: file_a 1-10, file_b 1-5
        # retrieved: file_a 1-10, file_b 3-7
        # overlap: file_a 10, file_b 3 (3-5) = 13
        # union: (10+5) + (10+5) - 13 = 17
        golden = {"file_a.py": [(1, 10)], "file_b.py": [(1, 5)]}
        retrieved = {"file_a.py": [(1, 10)], "file_b.py": [(3, 7)]}
        overlap = 10 + 3  # file_a full, file_b (3,5)
        golden_lines = 10 + 5
        retrieved_lines = 10 + 5
        union = golden_lines + retrieved_lines - overlap
        assert calculate_line_iou(retrieved, golden) == pytest.approx(overlap / union)

    def test_empty_both(self):
        assert calculate_line_iou({}, {}) == 0.0


# ---------------------------------------------------------------------------
# build_chunk_line_lookup
# ---------------------------------------------------------------------------


class TestBuildChunkLineLookup:
    def _make_store(self, data: dict):
        """Create a minimal mock MetadataStore that supports .items()."""

        class MockStore:
            def items(self):
                return iter(data.items())

        return MockStore()

    def test_basic_lookup(self):
        store_data = {
            "search/config.py:148-161:decorated_definition:EmbeddingConfig": {
                "metadata": {
                    "relative_path": "search/config.py",
                    "start_line": 148,
                    "end_line": 161,
                }
            }
        }
        lookup = build_chunk_line_lookup(self._make_store(store_data))
        assert "search/config.py:decorated_definition:EmbeddingConfig" in lookup
        assert lookup["search/config.py:decorated_definition:EmbeddingConfig"] == (
            "search/config.py",
            148,
            161,
        )

    def test_missing_lines_excluded(self):
        store_data = {
            "file.py:0-0:module": {
                "metadata": {
                    "relative_path": "file.py",
                    "start_line": 0,
                    "end_line": 0,
                }
            }
        }
        lookup = build_chunk_line_lookup(self._make_store(store_data))
        assert len(lookup) == 0

    def test_multiple_chunks(self):
        store_data = {
            "a.py:1-10:function:foo": {
                "metadata": {"relative_path": "a.py", "start_line": 1, "end_line": 10}
            },
            "a.py:12-20:function:bar": {
                "metadata": {"relative_path": "a.py", "start_line": 12, "end_line": 20}
            },
        }
        lookup = build_chunk_line_lookup(self._make_store(store_data))
        assert len(lookup) == 2
        assert lookup["a.py:function:foo"] == ("a.py", 1, 10)
        assert lookup["a.py:function:bar"] == ("a.py", 12, 20)

    def test_empty_store(self):
        lookup = build_chunk_line_lookup(self._make_store({}))
        assert lookup == {}

    def test_truthy_path_start_but_falsy_end_excluded(self):
        # path & start truthy, end=0 falsy: original (and) excludes;
        # and→or mutant on second `and` would include → this kills it
        store_data = {
            "a.py:10-0:function:foo": {
                "metadata": {"relative_path": "a.py", "start_line": 10, "end_line": 0}
            }
        }
        assert build_chunk_line_lookup(self._make_store(store_data)) == {}


# ---------------------------------------------------------------------------
# resolve_chunk_ids_to_ranges
# ---------------------------------------------------------------------------


class TestResolveChunkIdsToRanges:
    def _make_lookup(self) -> dict[str, tuple[str, int, int]]:
        return {
            "search/config.py:decorated_definition:EmbeddingConfig": (
                "search/config.py",
                148,
                161,
            ),
            "search/filters.py:function:normalize_path": (
                "search/filters.py",
                22,
                31,
            ),
            "search/filters.py:function:normalize_path_lower": (
                "search/filters.py",
                33,
                42,
            ),
        }

    def test_single_chunk(self):
        lookup = self._make_lookup()
        result = resolve_chunk_ids_to_ranges(
            ["search/config.py:decorated_definition:EmbeddingConfig"], lookup
        )
        assert result == {"search/config.py": [(148, 161)]}

    def test_missing_chunk_skipped(self):
        lookup = self._make_lookup()
        result = resolve_chunk_ids_to_ranges(["nonexistent:function:foo"], lookup)
        assert result == {}

    def test_multiple_chunks_same_file(self):
        lookup = self._make_lookup()
        result = resolve_chunk_ids_to_ranges(
            [
                "search/filters.py:function:normalize_path",
                "search/filters.py:function:normalize_path_lower",
            ],
            lookup,
        )
        assert "search/filters.py" in result
        assert (22, 31) in result["search/filters.py"]
        assert (33, 42) in result["search/filters.py"]

    def test_multiple_files(self):
        lookup = self._make_lookup()
        result = resolve_chunk_ids_to_ranges(
            [
                "search/config.py:decorated_definition:EmbeddingConfig",
                "search/filters.py:function:normalize_path",
            ],
            lookup,
        )
        assert "search/config.py" in result
        assert "search/filters.py" in result

    def test_empty_input(self):
        lookup = self._make_lookup()
        assert resolve_chunk_ids_to_ranges([], lookup) == {}

    def test_empty_lookup(self):
        result = resolve_chunk_ids_to_ranges(
            ["search/config.py:decorated_definition:EmbeddingConfig"], {}
        )
        assert result == {}

    def test_normalized_ids_accepted(self):
        # Chunk IDs that already have line ranges stripped should still resolve
        lookup = self._make_lookup()
        # Already normalized (no :\d+-\d+: segment)
        result = resolve_chunk_ids_to_ranges(
            ["search/filters.py:function:normalize_path"], lookup
        )
        assert result == {"search/filters.py": [(22, 31)]}


# ---------------------------------------------------------------------------
# _extract_ranges_from_results  (regression: must read .metadata, not attrs)
# ---------------------------------------------------------------------------


class TestExtractRangesFromResults:
    """Regression tests for _extract_ranges_from_results.

    The real HybridSearcher returns search.reranker.SearchResult whose only
    fields are chunk_id/score/metadata/source/rank.  Line data lives inside
    .metadata — NOT as top-level attributes.  Earlier code used getattr() on
    top-level attrs and always returned {}, making all line-overlap metrics 0.
    """

    def _make_sr(self, chunk_id: str, meta: dict):
        """Build a real reranker.SearchResult with the given metadata."""
        from search.reranker import SearchResult

        return SearchResult(chunk_id=chunk_id, score=1.0, metadata=meta)

    def _extract(self, results):
        from scripts.benchmark.run_sscg_benchmark import _extract_ranges_from_results

        return _extract_ranges_from_results(results)

    def test_reads_from_metadata_not_top_level_attrs(self):
        """Core regression: line data in .metadata must produce non-empty output."""
        sr = self._make_sr(
            "search/config.py:function:foo",
            {"relative_path": "search/config.py", "start_line": 10, "end_line": 20},
        )
        result = self._extract([sr])
        assert result == {"search/config.py": [(10, 20)]}

    def test_windows_backslash_path_normalized(self):
        """Windows raw relative_path with backslashes must be normalized to forward slashes."""
        sr = self._make_sr(
            "search/config.py:function:foo",
            {"relative_path": "search\\config.py", "start_line": 10, "end_line": 20},
        )
        result = self._extract([sr])
        assert "search/config.py" in result
        assert "search\\config.py" not in result
        assert result["search/config.py"] == [(10, 20)]

    def test_missing_line_fields_skipped(self):
        """A result without start_line/end_line in metadata must be silently skipped."""
        sr = self._make_sr(
            "search/config.py:module:search",
            {"relative_path": "search/config.py"},
        )
        result = self._extract([sr])
        assert result == {}

    def test_zero_line_fields_skipped(self):
        """A module-summary result with start=0/end=0 must be silently skipped."""
        sr = self._make_sr(
            "search/config.py:module:search",
            {"relative_path": "search/config.py", "start_line": 0, "end_line": 0},
        )
        result = self._extract([sr])
        assert result == {}

    def test_multiple_results_grouped_by_file(self):
        """Multiple results in the same file should be grouped under one path key."""
        sr1 = self._make_sr(
            "search/config.py:function:foo",
            {"relative_path": "search/config.py", "start_line": 1, "end_line": 10},
        )
        sr2 = self._make_sr(
            "search/config.py:function:bar",
            {"relative_path": "search/config.py", "start_line": 12, "end_line": 20},
        )
        result = self._extract([sr1, sr2])
        assert "search/config.py" in result
        assert (1, 10) in result["search/config.py"]
        assert (12, 20) in result["search/config.py"]

    def test_empty_results_returns_empty_dict(self):
        assert self._extract([]) == {}

    def test_non_numeric_start_line_skipped(self):
        """Non-numeric metadata values must not raise ValueError — silently skip."""
        sr = self._make_sr(
            "search/config.py:function:foo",
            {"relative_path": "search/config.py", "start_line": "N/A", "end_line": 20},
        )
        result = self._extract([sr])
        assert result == {}


# ---------------------------------------------------------------------------
# aggregate_metrics — thresholds override contract (b5cfc24)
# ---------------------------------------------------------------------------


class TestAggregateMetricsThresholds:
    """Tests for the aggregate_metrics(thresholds=...) JSON-override contract.

    The module constant THRESHOLDS has recall_at_5 = 0.70 (high bar).
    The golden_dataset.json ships thresholds.recall_at_5 = 0.55 (lower bar).
    The merge ``_thresholds = {**THRESHOLDS, **(thresholds or {})}`` means the
    JSON value wins for supplied keys; module constant is the fallback.
    """

    def _minimal_query(self, recall5: float, hit: bool) -> dict:
        """Minimal per-query dict that satisfies aggregate_metrics float_keys."""
        return {
            "recall@1": 0.0,
            "recall@5": recall5,
            "recall@7": 0.0,
            "recall@10": 0.0,
            "precision@1": 0.0,
            "precision@5": 0.0,
            "precision@10": 0.0,
            "mrr": 0.6,  # above THRESHOLDS["mrr"] = 0.50 → always PASS
            "ndcg@5": 0.0,
            "ndcg@10": 0.0,
            "hit": hit,
            "hit@7": hit,
        }

    def test_module_constant_fails_low_recall(self):
        """Without override, recall@5 < 0.70 (module constant) → FAIL."""
        per_query = [self._minimal_query(recall5=0.60, hit=True)]
        result = aggregate_metrics(per_query)
        assert result["pass_fail"]["recall@5"] == "FAIL"

    def test_json_override_passes_low_recall(self):
        """With JSON override recall_at_5=0.55, same 0.60 score → PASS."""
        per_query = [self._minimal_query(recall5=0.60, hit=True)]
        result = aggregate_metrics(per_query, thresholds={"recall_at_5": 0.55})
        assert result["pass_fail"]["recall@5"] == "PASS"

    def test_unspecified_keys_fall_back_to_module_constant(self):
        """Keys absent from the override dict must use THRESHOLDS as fallback."""
        per_query = [self._minimal_query(recall5=0.60, hit=True)]
        # Only override recall_at_5; mrr and hit_rate_at_5 must use module constants
        result = aggregate_metrics(per_query, thresholds={"recall_at_5": 0.55})
        # mrr is 0.6, THRESHOLDS["mrr"] is 0.50 → PASS (fallback in effect)
        assert result["pass_fail"]["mrr"] == "PASS"

    def test_none_thresholds_behaves_as_module_constant(self):
        """Passing thresholds=None must behave identically to the module constant."""
        per_query = [self._minimal_query(recall5=0.60, hit=True)]
        default_result = aggregate_metrics(per_query)
        explicit_none_result = aggregate_metrics(per_query, thresholds=None)
        assert default_result["pass_fail"] == explicit_none_result["pass_fail"]

    def test_module_thresholds_dict_contents(self):
        """Sanity: the module THRESHOLDS constant must contain the expected keys."""
        assert "mrr" in THRESHOLDS
        assert "recall_at_5" in THRESHOLDS
        assert "hit_rate_at_5" in THRESHOLDS
