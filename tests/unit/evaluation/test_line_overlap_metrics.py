"""Unit tests for line-range overlap metrics in evaluation/metrics.py.

Tests cover the Chroma-style IoU/Recall/Precision adapted to source line ranges,
including the range arithmetic helpers and the MetadataStore resolution utilities.
"""

import pytest

from evaluation.metrics import (
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
