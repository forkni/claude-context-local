"""Property tests for the pure cores in evaluation/metrics.py (Phase 4.1).

The line-range helpers are checked against a model that is obviously right and shares no code
with the implementation: an inclusive range ``(s, e)`` is the set of line numbers
``{s, ..., e}``. Merging, intersecting and counting ranges must agree with set union,
intersection and ``len`` on those sets. The ranking metrics are checked against their
definitions (recall = found / relevant, MRR = 1 / rank of the first hit), worked out with
plain list operations, plus range and monotonicity invariants.

Break-and-revert evidence (2026-11-18, hand mutants in evaluation/metrics.py, each fails
at least one property here): merge_ranges `prev_end + 1` -> `prev_end + 2` and
`max(prev_end, end)` -> `end`; intersect_ranges `lo <= hi` -> `lo < hi`; line precision
denominator `end - start + 1` -> `end - start`. The pragma'd intersect pointer advance
`a[i][1] < b[j][1]` -> `<=` passes every property, which supports its equivalence note.
Mutants these properties kill that the example tests miss: tests/TESTING_GUIDE.md, Phase 17.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from evaluation.metrics import (
    calculate_line_iou,
    calculate_line_precision,
    calculate_line_recall,
    calculate_mrr,
    calculate_ndcg_at_k,
    calculate_precision_at_k,
    calculate_recall_at_k,
    count_lines,
    intersect_ranges,
    merge_ranges,
)


# ── Strategies ────────────────────────────────────────────────────────────────


@st.composite
def line_range(draw: st.DrawFn) -> tuple[int, int]:
    """An inclusive (start, end) with 1 <= start <= end, built rather than filtered."""
    start = draw(st.integers(min_value=1, max_value=60))
    length = draw(st.integers(min_value=0, max_value=15))
    return start, start + length


ranges = st.lists(line_range(), max_size=12)
paths = st.sampled_from(["a.py", "b.py", "pkg/c.py"])
range_maps = st.dictionaries(paths, st.lists(line_range(), min_size=1, max_size=6))


def lines_of(rs: list[tuple[int, int]]) -> set[int]:
    """Model: the set of line numbers a range list covers."""
    return {line for s, e in rs for line in range(s, e + 1)}


def file_lines(m: dict[str, list[tuple[int, int]]]) -> set[tuple[str, int]]:
    return {(path, line) for path, rs in m.items() for line in lines_of(rs)}


# ── merge_ranges / intersect_ranges / count_lines ─────────────────────────────


@given(ranges)
def test_merge_ranges_covers_exactly_the_same_lines(rs):
    assert lines_of(merge_ranges(rs)) == lines_of(rs)


@given(ranges)
def test_merge_ranges_output_is_sorted_disjoint_and_not_adjacent(rs):
    merged = merge_ranges(rs)
    assert all(s <= e for s, e in merged)
    # Adjacent ranges ((1, 3), (4, 6)) must have been merged, so each gap is at least one line.
    assert all(
        prev_end + 1 < start
        for (_, prev_end), (start, _) in zip(merged, merged[1:], strict=False)
    )


@given(ranges)
def test_merge_ranges_is_idempotent(rs):
    once = merge_ranges(rs)
    assert merge_ranges(once) == once


@given(ranges, ranges)
def test_intersect_ranges_matches_set_intersection(a, b):
    out = intersect_ranges(merge_ranges(a), merge_ranges(b))
    assert lines_of(out) == lines_of(a).intersection(lines_of(b))
    assert all(
        prev_end < start
        for (_, prev_end), (start, _) in zip(out, out[1:], strict=False)
    )


@given(ranges)
def test_count_lines_of_merged_ranges_is_number_of_distinct_lines(rs):
    assert count_lines(merge_ranges(rs)) == len(lines_of(rs))


# ── Line-level recall / precision / IoU ───────────────────────────────────────


@given(range_maps, range_maps)
def test_line_iou_matches_set_definition(retrieved, golden):
    r, g = file_lines(retrieved), file_lines(golden)
    expected = len(r & g) / len(r | g) if r | g else 0.0
    assert calculate_line_iou(retrieved, golden) == expected


@given(range_maps, range_maps)
def test_line_recall_matches_set_definition(retrieved, golden):
    r, g = file_lines(retrieved), file_lines(golden)
    expected = len(r & g) / len(g) if g else 0.0
    assert calculate_line_recall(retrieved, golden) == expected


@given(range_maps, range_maps)
def test_line_precision_is_overlap_over_raw_retrieved_lines(retrieved, golden):
    # The docstring fixes the denominator as the raw (un-merged) sum: duplicates are penalised.
    raw_retrieved = sum(e - s + 1 for rs in retrieved.values() for s, e in rs)
    overlap = len(file_lines(retrieved) & file_lines(golden))
    expected = overlap / raw_retrieved if raw_retrieved else 0.0
    assert calculate_line_precision(retrieved, golden) == expected


@given(
    st.dictionaries(paths, st.lists(line_range(), min_size=1, max_size=6), min_size=1)
)
def test_line_metrics_are_perfect_when_retrieved_equals_golden(golden):
    assert calculate_line_recall(golden, golden) == 1.0
    assert calculate_line_iou(golden, golden) == 1.0


# ── Ranking metrics ───────────────────────────────────────────────────────────

ids = st.sampled_from([f"f.py:fn{i}" for i in range(8)])
retrieved_lists = st.lists(ids, max_size=10, unique=True)
relevant_lists = st.lists(ids, min_size=1, max_size=5, unique=True)
cutoffs = st.integers(min_value=1, max_value=12)


@given(retrieved_lists, relevant_lists, cutoffs)
def test_recall_at_k_is_found_over_relevant(retrieved, relevant, k):
    found = [r for r in retrieved[:k] if r in relevant]
    assert calculate_recall_at_k(retrieved, relevant, k) == len(found) / len(relevant)


@given(retrieved_lists, relevant_lists, cutoffs)
def test_precision_at_k_is_found_over_k(retrieved, relevant, k):
    found = [r for r in retrieved[:k] if r in relevant]
    assert calculate_precision_at_k(retrieved, relevant, k) == len(found) / k


@given(retrieved_lists, relevant_lists, cutoffs)
def test_recall_at_k_never_decreases_as_k_grows(retrieved, relevant, k):
    assert calculate_recall_at_k(retrieved, relevant, k) <= calculate_recall_at_k(
        retrieved, relevant, k + 1
    )


@given(retrieved_lists, relevant_lists)
def test_mrr_is_reciprocal_rank_of_first_hit(retrieved, relevant):
    hits = [rank for rank, r in enumerate(retrieved, start=1) if r in relevant]
    expected = 1.0 / hits[0] if hits else 0.0
    assert calculate_mrr(retrieved, relevant) == expected


@given(retrieved_lists, relevant_lists, cutoffs)
def test_ndcg_is_between_zero_and_one(retrieved, relevant, k):
    ndcg = calculate_ndcg_at_k(retrieved, relevant, k)
    assert ndcg >= 0.0
    assert ndcg == pytest.approx(1.0) or ndcg < 1.0


@given(relevant_lists, st.lists(ids, max_size=5, unique=True), cutoffs)
def test_ndcg_is_one_when_all_relevant_come_first(relevant, tail, k):
    # An ideal ranking: every relevant id first, then only irrelevant ones.
    ranking = relevant + [t for t in tail if t not in relevant]
    assert calculate_ndcg_at_k(ranking, relevant, k) == pytest.approx(1.0)
