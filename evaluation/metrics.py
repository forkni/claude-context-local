"""Information Retrieval evaluation metrics for SSCG benchmark.

Deterministic ground-truth-based metrics — no LLM judge required.
All functions accept normalized chunk IDs (line ranges stripped).

Ported from: _archive/BENCHMARKING/tools/benchmark_retrieval_quality.py
"""

import math
from collections.abc import Iterable, Sequence
from statistics import mean
from typing import Any

from search.chunk_id import dedup_key
from utils.path_utils import normalize_path


THRESHOLDS = {
    "mrr": 0.50,
    "recall_at_5": 0.70,
    "hit_rate_at_5": 0.80,
}


def normalize_chunk_id(chunk_id: str) -> str:
    """Strip line-range component and normalize split_block type from a chunk ID.

    Line numbers shift as code evolves; split_block is a structural detail.
    Comparison uses only the stable ``file_path:type:name`` portion, with path
    separators canonicalized to forward slashes.

    Thin wrapper over :func:`search.chunk_id.dedup_key` — the single owner of
    dedup-key semantics shared by the live search path and this evaluation code.

    Examples::

        "search/config.py:148-161:decorated_definition:EmbeddingConfig"
        → "search/config.py:decorated_definition:EmbeddingConfig"

        "merkle/__init__.py:1-8:module"
        → "merkle/__init__.py:module"

        "graph/graph_integration.py:276-310:split_block:GraphIntegration.populate_from_embeddings"
        → "graph/graph_integration.py:method:GraphIntegration.populate_from_embeddings"
    """
    return dedup_key(chunk_id)


def normalize_chunk_ids(chunk_ids: list[str]) -> list[str]:
    """Normalize a list of chunk IDs, deduplicating after normalization."""
    seen: set[str] = set()
    result: list[str] = []
    for cid in chunk_ids:
        normalized = normalize_chunk_id(cid)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


# ---------------------------------------------------------------------------
# Core metric functions (deterministic, zero external dependencies)
#
# Each retrieved position is either a plain normalized chunk ID (str) or a
# set of IDs the chunk at that rank can be credited as — the containment-
# credit representation for merged chunks (own ID plus every golden ID whose
# symbol the merged chunk absorbed).  A str entry behaves exactly like a
# one-element set, so plain-ID callers see identical scores as before.
# ---------------------------------------------------------------------------

RetrievedEntry = str | set[str]


def _entry_ids(entry: RetrievedEntry) -> set[str]:
    """Return the set of IDs a retrieved position can match as."""
    return entry if isinstance(entry, set) else {entry}


def flatten_entries(entries: Sequence[RetrievedEntry]) -> set[str]:
    """Union all IDs across retrieved entries (for pool-membership checks)."""
    ids: set[str] = set()
    for entry in entries:
        ids |= _entry_ids(entry)
    return ids


def chunk_ids_to_files(chunk_ids: Iterable[str]) -> set[str]:
    """Map normalized chunk IDs to their containing file paths.

    A normalized chunk ID's file-path component is everything before the
    first ``:`` — ``normalize_chunk_id`` always produces relative,
    forward-slash paths with no embedded colons (see the module docstring).
    """
    return {normalize_path(cid.split(":", 1)[0]) for cid in chunk_ids}


def to_file_entries(entries: Sequence[RetrievedEntry]) -> list[set[str]]:
    """Convert per-rank retrieved entries into per-rank file-path sets (SweRank max-pool rollup).

    Same per-rank shape as the input (str or set[str] per rank, via
    :func:`_entry_ids`), but rolled up to the file each chunk belongs to.
    Feeds straight into :func:`calculate_recall_at_k` / :func:`calculate_acc_at_k`
    unchanged, scoring file-level coverage instead of chunk-level coverage.

    This is a **different axis** from the Category-G
    ``calculate_file_recall_at_k`` machinery further below, which scores
    community-summary-expansion coverage against ``expected_files`` using
    result metadata. This is a plain rollup of *which files* an already-scored
    chunk-level retrieved list came from — no community credit involved.
    """
    return [chunk_ids_to_files(_entry_ids(entry)) for entry in entries]


def calculate_recall_at_k(
    retrieved: Sequence[RetrievedEntry], relevant: list[str], k: int
) -> float:
    """Recall@k = |matched relevant IDs in retrieved[:k]| / |relevant|.

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        relevant: Set of relevant chunk IDs (normalized, label ≥ 2).
        k: Cut-off rank.

    Returns:
        Recall score in [0.0, 1.0].
    """
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    matched: set[str] = set()
    for entry in retrieved[:k]:
        matched |= _entry_ids(entry) & relevant_set
    return len(matched) / len(relevant_set)


def calculate_precision_at_k(
    retrieved: Sequence[RetrievedEntry], relevant: list[str], k: int
) -> float:
    """Precision@k = |matched relevant IDs in retrieved[:k]| / k.

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        relevant: Set of relevant chunk IDs (normalized, label ≥ 2).
        k: Cut-off rank.

    Returns:
        Precision score in [0.0, 1.0].
    """
    if k == 0:  # pragma: no mutate
        return 0.0
    relevant_set = set(relevant)
    matched: set[str] = set()
    for entry in retrieved[:k]:
        matched |= _entry_ids(entry) & relevant_set
    return len(matched) / k


def calculate_mrr(retrieved: Sequence[RetrievedEntry], relevant: list[str]) -> float:
    """Mean Reciprocal Rank of the first highly-relevant (label=3) result.

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        relevant: Set of primary/highly-relevant chunk IDs (normalized, label=3).

    Returns:
        Reciprocal rank (1/rank) of first hit, or 0.0 if none found.
    """
    relevant_set = set(relevant)
    for i, entry in enumerate(retrieved, 1):
        if _entry_ids(entry) & relevant_set:
            return 1.0 / i
    return 0.0


def calculate_ndcg_at_k(
    retrieved: Sequence[RetrievedEntry], relevant: list[str], k: int
) -> float:
    """NDCG@k with binary relevance (label ≥ 2 = 1, otherwise 0).

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        relevant: Set of relevant chunk IDs (normalized, label ≥ 2).
        k: Cut-off rank.

    Returns:
        NDCG score in [0.0, 1.0].
    """
    relevant_set = set(relevant)
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, entry in enumerate(retrieved[:k], 1)
        if _entry_ids(entry) & relevant_set
    )
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant_set), k) + 1))
    return dcg / idcg if idcg > 0 else 0.0  # pragma: no mutate


def calculate_graded_ndcg_at_k(
    retrieved: Sequence[RetrievedEntry],
    relevance_grades: dict[str, int],
    k: int,
) -> float:
    """Graded NDCG@k using exponential gain ``2**grade - 1`` (TREC/pytrec_eval).

    Unlike :func:`calculate_ndcg_at_k` (binary relevance: label >= 2 counts as
    1, everything else as 0), this uses the full 0-3 relevance grade as gain,
    so a rank-1 grade-3 hit scores higher than a rank-1 grade-1 hit. An entry
    that can match multiple golden IDs (containment credit) is scored by the
    highest grade among its matches (max-pooled), matching how recall/
    precision already credit the best available match at a rank.

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        relevance_grades: ``{normalized_chunk_id: grade}`` for the query,
            grade in 0-3. IDs absent from this dict score grade 0.
        k: Cut-off rank.

    Returns:
        NDCG score in [0.0, 1.0], or 0.0 when no positive-grade ID exists.
    """

    def _gain(entry: RetrievedEntry) -> float:
        top_grade = max(
            (relevance_grades.get(cid, 0) for cid in _entry_ids(entry)), default=0
        )
        return float(2**top_grade - 1)

    dcg = sum(
        _gain(entry) / math.log2(i + 1) for i, entry in enumerate(retrieved[:k], 1)
    )
    ideal_grades = sorted(
        (g for g in relevance_grades.values() if g > 0), reverse=True
    )[:k]
    idcg = sum(
        (2**grade - 1) / math.log2(i + 1) for i, grade in enumerate(ideal_grades, 1)
    )
    return dcg / idcg if idcg > 0 else 0.0  # pragma: no mutate


def calculate_acc_at_k(
    retrieved: Sequence[RetrievedEntry], relevant: list[str], k: int
) -> float:
    """Acc@k (SweRank-style strict set coverage): 1.0 iff every relevant ID is covered.

    Unlike Recall@k (partial credit for each matched ID), Acc@k is
    all-or-nothing: ``retrieved[:k]`` must cover every ID in ``relevant``, not
    just some. Acc@k <= Recall@k always, for the same (retrieved, relevant, k).

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        relevant: Set of relevant chunk IDs (normalized, label >= 2).
        k: Cut-off rank.

    Returns:
        1.0 if ``retrieved[:k]`` covers all of ``relevant``, else 0.0. Empty
        ``relevant`` returns 0.0 (mirrors :func:`calculate_recall_at_k`'s
        empty-relevant guard, not vacuous-truth semantics) so an unlabeled
        query never contributes a free pass to the aggregate.
    """
    if not relevant:
        return 0.0
    relevant_set = set(relevant)
    covered = flatten_entries(retrieved[:k])
    return 1.0 if relevant_set <= covered else 0.0


def calculate_hard_negative_intrusion(
    retrieved: Sequence[RetrievedEntry],
    positive_ids: list[str],
    hard_negative_ids: list[str],
    k: int = 10,
) -> bool | None:
    """CoREB-style Hard-Negative Intrusion: did a hard negative outrank every positive?

    A hard negative "intrudes" when it appears in ``retrieved[:k]`` at a rank
    strictly before the first positive ID -- i.e. a near-duplicate distractor
    (grade=1) out-competed the actual answer.

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        positive_ids: Relevant chunk IDs (label >= 2, i.e. ``expected``).
        hard_negative_ids: Hard-negative chunk IDs (label == 1).
        k: Cut-off rank.

    Returns:
        ``True`` if a hard negative ranked before the first positive within
        ``retrieved[:k]``; ``False`` if the first positive ranked before every
        hard negative seen; ``None`` if ``retrieved[:k]`` surfaced no positive,
        no hard negative, or neither -- callers must never average ``None``
        in as 0.0, since "no negative was seen" is not evidence the negative
        never intrudes.
    """
    positive_set = set(positive_ids)
    negative_set = set(hard_negative_ids)
    first_positive_rank: int | None = None
    first_negative_rank: int | None = None
    for i, entry in enumerate(retrieved[:k], 1):
        ids = _entry_ids(entry)
        if first_positive_rank is None and ids & positive_set:
            first_positive_rank = i
        if first_negative_rank is None and ids & negative_set:
            first_negative_rank = i
        if first_positive_rank is not None and first_negative_rank is not None:
            break
    if first_positive_rank is None or first_negative_rank is None:
        return None
    return first_negative_rank < first_positive_rank


def calculate_metrics_from_results(
    retrieved: Sequence[RetrievedEntry],
    expected: list[str],
    expected_primary: list[str] | None = None,
    relevance_grades: dict[str, int] | None = None,
) -> dict[str, float | bool | None]:
    """Calculate all retrieval metrics for a single query.

    Args:
        retrieved: Ordered list of retrieved entries (normalized chunk IDs,
            or per-rank ID sets for containment credit).
        expected: Relevant chunk IDs with label ≥ 2.
        expected_primary: Highly-relevant chunk IDs with label = 3.
            Falls back to ``expected`` if not provided (for MRR calculation).
        relevance_grades: Optional ``{normalized_chunk_id: grade}`` map
            (grade 0-3) for the query. When provided, adds graded-NDCG
            (``ndcg@5_graded`` / ``ndcg@10_graded``, exponential gain) and the
            CoREB-style ``hard_negative_intrusion`` flag (grade == 1 IDs are
            treated as hard negatives). Omitted entirely when not provided --
            these are optional, presence-based keys, never defaulted to
            0.0/False.

    Returns:
        Dict with keys: recall@1, recall@5, recall@7, recall@10, recall@20,
        recall@50, precision@1, precision@5, precision@10, mrr, ndcg@5,
        ndcg@10, acc@5, acc@10, hit, hit@7. Plus, only when
        ``relevance_grades`` is provided: ndcg@5_graded, ndcg@10_graded,
        hard_negative_intrusion (bool or None -- see
        :func:`calculate_hard_negative_intrusion`).

    Note:
        recall@20 / recall@50 are only meaningful when ``retrieved`` is at
        least that deep — with a shallower list they degenerate to recall
        at the list length (recall-headroom instrumentation, R0).
    """
    primary = expected_primary if expected_primary is not None else expected
    recall_5 = calculate_recall_at_k(retrieved, expected, 5)  # pragma: no mutate
    recall_7 = calculate_recall_at_k(retrieved, expected, 7)  # pragma: no mutate
    result: dict[str, float | bool | None] = {
        "recall@1": calculate_recall_at_k(retrieved, expected, 1),
        "recall@5": recall_5,
        "recall@7": recall_7,
        "recall@10": calculate_recall_at_k(
            retrieved,
            expected,
            10,  # pragma: no mutate
        ),
        "recall@20": calculate_recall_at_k(
            retrieved,
            expected,
            20,  # pragma: no mutate
        ),
        "recall@50": calculate_recall_at_k(
            retrieved,
            expected,
            50,  # pragma: no mutate
        ),
        "precision@1": calculate_precision_at_k(retrieved, expected, 1),
        "precision@5": calculate_precision_at_k(retrieved, expected, 5),
        "precision@10": calculate_precision_at_k(retrieved, expected, 10),
        "mrr": calculate_mrr(retrieved, primary),
        "ndcg@5": calculate_ndcg_at_k(retrieved, expected, 5),  # pragma: no mutate
        "ndcg@10": calculate_ndcg_at_k(retrieved, expected, 10),  # pragma: no mutate
        "acc@5": calculate_acc_at_k(retrieved, expected, 5),
        "acc@10": calculate_acc_at_k(retrieved, expected, 10),
        "hit": recall_5 > 0,  # pragma: no mutate
        "hit@7": recall_7 > 0,  # pragma: no mutate
    }
    if relevance_grades is not None:
        result["ndcg@5_graded"] = calculate_graded_ndcg_at_k(
            retrieved, relevance_grades, 5
        )
        result["ndcg@10_graded"] = calculate_graded_ndcg_at_k(
            retrieved, relevance_grades, 10
        )
        hard_negative_ids = [
            cid for cid, grade in relevance_grades.items() if grade == 1
        ]
        result["hard_negative_intrusion"] = calculate_hard_negative_intrusion(
            retrieved, expected, hard_negative_ids, k=10
        )
    return result


def aggregate_metrics(
    per_query: list[dict[str, Any]],
    thresholds: dict | None = None,
) -> dict[str, Any]:
    """Compute aggregate statistics across all per-query metric dicts.

    Args:
        per_query: List of dicts, each from ``calculate_metrics_from_results``.
        thresholds: Optional threshold dict (keys: mrr, recall_at_5,
            hit_rate_at_5). When provided, its values override the module-level
            ``THRESHOLDS`` constant for the ``pass_fail`` assessment.  Pass
            ``dataset.get("thresholds")`` to honour the golden-dataset JSON
            thresholds instead of the hardcoded module constant.  Falls back to
            ``THRESHOLDS`` for any keys not present in the override.

    Returns:
        Aggregate dict with means, pass/fail assessment, and counts.
    """
    if not per_query:
        return {}

    float_keys = [
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
    ]
    agg: dict[str, Any] = {
        "total_queries": len(per_query),
        "success_count": sum(
            1
            for q in per_query
            if q.get("hit", False)  # pragma: no mutate
        ),
        "success_count@7": sum(
            1
            for q in per_query
            if q.get("hit@7", False)  # pragma: no mutate
        ),
    }
    for key in float_keys:
        # Use 0.0 for queries missing a key (e.g. error rows) so they count
        # against the aggregate rather than being silently excluded.
        vals = [float(q.get(key, 0.0)) for q in per_query]
        agg[key] = round(mean(vals), 4) if vals else 0.0  # pragma: no mutate

    agg["hit_rate@5"] = round(
        agg["success_count"] / agg["total_queries"],
        4,  # pragma: no mutate -- rounding precision doesn't affect threshold comparison
    )
    agg["hit_rate@7"] = round(
        agg["success_count@7"] / agg["total_queries"],
        4,  # pragma: no mutate -- rounding precision doesn't affect threshold comparison
    )

    _thresholds = {**THRESHOLDS, **(thresholds or {})}
    agg["pass_fail"] = {
        "mrr": "PASS" if agg["mrr"] >= _thresholds["mrr"] else "FAIL",
        "recall@5": "PASS" if agg["recall@5"] >= _thresholds["recall_at_5"] else "FAIL",
        "hit_rate@5": "PASS"
        if agg["hit_rate@5"] >= _thresholds["hit_rate_at_5"]  # pragma: no mutate
        else "FAIL",
    }

    # Line-overlap metrics — only average queries where the key is present
    # (queries without golden line ranges are excluded, not counted as 0).
    # Same rule for Category-G file recall (only queries with expected_files),
    # the secondary community-credit MRR (absent = N/A on community-free
    # arms — never averaged in as 0.0), graded NDCG (absent when
    # relevance_grades wasn't passed to calculate_metrics_from_results), and
    # the file-level rollup (absent when the runner didn't compute it).
    for key in (
        "line_recall",
        "line_precision",
        "line_iou",
        "file_recall_strict",
        "file_recall_expanded",
        "mrr_community_credit",
        "ndcg@5_graded",
        "ndcg@10_graded",
        "file_recall@5",
        "file_recall@10",
        "file_acc@5",
        "file_acc@10",
    ):
        vals = [float(q[key]) for q in per_query if key in q]
        if vals:
            agg[key] = round(mean(vals), 4)  # pragma: no mutate
            agg[f"{key}_count"] = len(vals)

    # Pre-rerank pool-hit-rate (R0) — presence-based like line metrics.
    # pool_hit answers "was any gold chunk in the fused candidate pool at
    # all?", splitting failures into retrieval misses (pool too narrow /
    # vocabulary gap) vs ranking misses (in pool, ranked below cutoff).
    pool_rows = [q for q in per_query if "pool_hit" in q]
    if pool_rows:
        agg["pool_hit_rate"] = round(
            mean([1.0 if q["pool_hit"] else 0.0 for q in pool_rows]),
            4,  # pragma: no mutate
        )
        agg["pool_hit_count"] = len(pool_rows)
        sizes = [float(q.get("pool_size", 0)) for q in pool_rows]
        agg["avg_pool_size"] = round(mean(sizes), 1)  # pragma: no mutate

    # Hard-Negative Intrusion Rate (CoREB) — presence-based; a row's key is
    # either absent (relevance_grades wasn't passed) or explicitly None (no
    # positive+negative pair surfaced in top-k). Both must be excluded, not
    # averaged in as 0.0/non-intrusion — .get() returns None for either case,
    # so a single filter handles both.
    intrusion_rows = [
        q for q in per_query if q.get("hard_negative_intrusion") is not None
    ]
    if intrusion_rows:
        agg["hard_negative_intrusion_rate"] = round(
            mean(
                [1.0 if q["hard_negative_intrusion"] else 0.0 for q in intrusion_rows]
            ),
            4,  # pragma: no mutate
        )
        agg["hard_negative_intrusion_count"] = len(intrusion_rows)

    return agg


# ---------------------------------------------------------------------------
# Line-range overlap metrics (Chroma-style, adapted to source line ranges)
#
# Adapted from: Chroma Technical Report "Evaluating Chunking Strategies for
# Retrieval" (Smith & Troynikov, 2024). Character-range arithmetic translated
# to inclusive line-number ranges since every chunk stores start_line/end_line.
#
# All range inputs/outputs use (start_line, end_line) inclusive tuples, e.g.
# (5, 8) covers lines 5, 6, 7, 8 = 4 lines.
# ---------------------------------------------------------------------------


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent line ranges into non-overlapping sorted ranges.

    Args:
        ranges: List of (start_line, end_line) inclusive tuples (may overlap).

    Returns:
        Sorted list of non-overlapping (start, end) tuples.

    Examples::

        merge_ranges([(1, 5), (3, 8), (12, 15)]) -> [(1, 8), (12, 15)]
        merge_ranges([(1, 3), (4, 6)])            -> [(1, 6)]  # adjacent
        merge_ranges([])                           -> []
    """
    if not ranges:
        return []
    sorted_ranges = sorted(ranges)
    merged: list[tuple[int, int]] = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:  # pragma: no mutate
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 1:  # overlapping or directly adjacent
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def intersect_ranges(
    a: list[tuple[int, int]], b: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Compute the intersection of two sorted, non-overlapping range lists.

    Both inputs should already be merged (from ``merge_ranges``).

    Args:
        a: First sorted, merged range list.
        b: Second sorted, merged range list.

    Returns:
        Sorted, non-overlapping intersection ranges.

    Examples::

        intersect_ranges([(1, 10)], [(5, 15)]) -> [(5, 10)]
        intersect_ranges([(1, 5)],  [(7, 10)]) -> []
    """
    result: list[tuple[int, int]] = []
    i = j = 0
    while i < len(a) and j < len(b):  # pragma: no mutate
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if lo <= hi:
            result.append((lo, hi))
        if a[i][1] < b[j][1]:  # pragma: no mutate
            i += 1
        else:
            j += 1
    return result


def count_lines(ranges: list[tuple[int, int]]) -> int:
    """Count total lines covered by a list of ranges (inclusive).

    Args:
        ranges: List of (start_line, end_line) inclusive tuples.

    Returns:
        Total line count. ``(5, 8)`` covers 4 lines.

    Examples::

        count_lines([(5, 8), (12, 13)]) -> 6
        count_lines([])                  -> 0
    """
    return sum(end - start + 1 for start, end in ranges)


def calculate_line_recall(
    retrieved_ranges: dict[str, list[tuple[int, int]]],
    golden_ranges: dict[str, list[tuple[int, int]]],
) -> float:
    """Line-level Recall = covered_golden_lines / total_golden_lines.

    Uses merged ranges on both sides to avoid double-counting.
    Only files present in ``golden_ranges`` contribute to the score.

    Args:
        retrieved_ranges: ``{relative_path: [(start, end), ...]}`` for retrieved chunks.
        golden_ranges: ``{relative_path: [(start, end), ...]}`` for ground-truth lines.

    Returns:
        Recall score in [0.0, 1.0].
    """
    total_golden = 0
    covered = 0
    for path, g_ranges in golden_ranges.items():
        merged_golden = merge_ranges(g_ranges)
        total_golden += count_lines(merged_golden)
        if path in retrieved_ranges:
            merged_retrieved = merge_ranges(retrieved_ranges[path])
            overlap = intersect_ranges(merged_golden, merged_retrieved)
            covered += count_lines(overlap)
    return covered / total_golden if total_golden > 0 else 0.0  # pragma: no mutate


def calculate_line_precision(
    retrieved_ranges: dict[str, list[tuple[int, int]]],
    golden_ranges: dict[str, list[tuple[int, int]]],
) -> float:
    """Line-level Precision = overlap_lines / total_retrieved_lines.

    Uses the **raw sum** of retrieved lines (before merging) as the denominator
    to penalise redundant overlapping chunks — matching Chroma's precision
    approach where retrieving duplicate content hurts precision.

    Args:
        retrieved_ranges: ``{relative_path: [(start, end), ...]}`` for retrieved chunks.
        golden_ranges: ``{relative_path: [(start, end), ...]}`` for ground-truth lines.

    Returns:
        Precision score in [0.0, 1.0].
    """
    # Raw (un-merged) sum of retrieved lines penalizes chunk redundancy
    total_retrieved = sum(
        end - start + 1 for ranges in retrieved_ranges.values() for start, end in ranges
    )
    if total_retrieved == 0:  # pragma: no mutate
        return 0.0
    # Overlap uses merged ranges on both sides to avoid double-counting the numerator
    overlap = 0
    for path, g_ranges in golden_ranges.items():
        if path in retrieved_ranges:
            merged_golden = merge_ranges(g_ranges)
            merged_retrieved = merge_ranges(retrieved_ranges[path])
            overlap += count_lines(intersect_ranges(merged_golden, merged_retrieved))
    return overlap / total_retrieved


def calculate_line_iou(
    retrieved_ranges: dict[str, list[tuple[int, int]]],
    golden_ranges: dict[str, list[tuple[int, int]]],
) -> float:
    """Line-level IoU (Intersection over Union) = overlap_lines / union_lines.

    Uses merged ranges for both the overlap and the union computation.

    Args:
        retrieved_ranges: ``{relative_path: [(start, end), ...]}`` for retrieved chunks.
        golden_ranges: ``{relative_path: [(start, end), ...]}`` for ground-truth lines.

    Returns:
        IoU score in [0.0, 1.0].
    """
    overlap = 0
    for path, g_ranges in golden_ranges.items():
        if path in retrieved_ranges:
            merged_golden = merge_ranges(g_ranges)
            merged_retrieved = merge_ranges(retrieved_ranges[path])
            overlap += count_lines(intersect_ranges(merged_golden, merged_retrieved))

    golden_lines = sum(
        count_lines(merge_ranges(ranges)) for ranges in golden_ranges.values()
    )
    retrieved_lines = sum(
        count_lines(merge_ranges(ranges)) for ranges in retrieved_ranges.values()
    )
    union = golden_lines + retrieved_lines - overlap
    return overlap / union if union > 0 else 0.0  # pragma: no mutate


def build_chunk_line_lookup(
    metadata_store: Any,
) -> dict[str, tuple[str, int, int]]:
    """Build a lookup from normalized chunk ID to (relative_path, start_line, end_line).

    Scans the MetadataStore once and normalises all raw chunk IDs (which include
    line ranges) so they can be matched against the normalized chunk IDs used in
    the golden dataset.

    Args:
        metadata_store: An open ``MetadataStore`` instance.

    Returns:
        Dict mapping ``normalized_chunk_id → (relative_path, start_line, end_line)``.
        Only entries with non-zero start/end lines are included.

    Example::

        lookup = build_chunk_line_lookup(searcher.dense_index.metadata_store)
        # lookup["search/config.py:decorated_definition:EmbeddingConfig"]
        # -> ("search/config.py", 148, 161)
    """
    lookup: dict[str, tuple[str, int, int]] = {}
    for raw_id, entry in metadata_store.items():
        meta = entry.get("metadata", {})
        path = normalize_path(meta.get("relative_path", "") or "")
        # Same as chunk_mapping: get() without default so None and 0 are
        # both filtered by the truthiness test below (#48).
        start = meta.get("start_line")
        end = meta.get("end_line")
        if path and start and end:
            normalized = normalize_chunk_id(raw_id)
            lookup[normalized] = (path, int(start), int(end))
    return lookup


def resolve_chunk_ids_to_ranges(
    chunk_ids: list[str],
    lookup: dict[str, tuple[str, int, int]],
) -> dict[str, list[tuple[int, int]]]:
    """Resolve normalized chunk IDs to per-file line ranges.

    Uses a pre-built lookup table from ``build_chunk_line_lookup`` so the
    MetadataStore does not need to be queried per-chunk at evaluation time.

    Args:
        chunk_ids: Normalized chunk IDs (line ranges already stripped).
        lookup: Pre-built ``{normalized_id: (relative_path, start_line, end_line)}``.

    Returns:
        ``{relative_path: [(start_line, end_line), ...]}`` grouped by file.
        Missing chunk IDs are silently skipped.

    Example::

        ranges = resolve_chunk_ids_to_ranges(
            ["search/config.py:decorated_definition:EmbeddingConfig"],
            lookup,
        )
        # ranges == {"search/config.py": [(148, 161)]}
    """
    result: dict[str, list[tuple[int, int]]] = {}
    for cid in chunk_ids:
        normalized = normalize_chunk_id(cid)
        if normalized in lookup:
            path, start, end = lookup[normalized]
            result.setdefault(path, []).append((start, end))
    return result


# ---------------------------------------------------------------------------
# Containment credit for merged chunks
#
# Merged chunks carry chunk_type="merged" and the name of one representative
# member, so their dedup key can never equal a golden expectation — even when
# the chunk contains the target symbol's exact lines at rank 1 (see
# evaluation/CHUNKING_MERGE_AB_20260728.md, Q40).  Fair scoring credits a
# merged chunk for every golden ID whose symbol it absorbed, via the
# ``merged_from`` member list persisted in chunk metadata.
# ---------------------------------------------------------------------------


def build_merged_membership(
    metadata_store: Any,
) -> dict[str, tuple[str, frozenset[str]]]:
    """Build a lookup of merged chunks to their absorbed member symbols.

    Scans the MetadataStore once; only entries whose metadata carries a
    non-empty ``merged_from`` list (i.e. merged chunks) are included.  On a
    merge-free index this returns an empty dict, making containment-credit
    scoring an exact no-op.

    Args:
        metadata_store: An open ``MetadataStore`` instance.

    Returns:
        Dict mapping the **raw** chunk ID (line range intact — merged IDs are
        only unique with it) to ``(relative_path, member_names)``, where
        ``member_names`` are qualified symbol names (``Class.method`` /
        ``function``) and the path is forward-slash normalized.
    """
    membership: dict[str, tuple[str, frozenset[str]]] = {}
    for raw_id, entry in metadata_store.items():
        meta = entry.get("metadata", {})
        members = meta.get("merged_from")
        if not members:
            continue
        path = normalize_path(meta.get("relative_path", "") or "")
        if path:
            membership[raw_id] = (path, frozenset(members))
    return membership


def _golden_id_matches_member(
    golden_id: str, path: str, members: frozenset[str]
) -> bool:
    """True when a normalized golden ID names a symbol absorbed by a merged chunk.

    Golden IDs use the normalized ``file:type:name`` form; the type component
    is ignored because merged members lose their original kind and the
    (path, qualified name) pair is already unambiguous within one file.
    """
    parts = golden_id.split(":")
    if len(parts) < 3:
        return False  # nameless IDs (e.g. "file.py:module") cannot be members
    return normalize_path(parts[0]) == path and parts[-1] in members


def expand_retrieved_with_containment(
    raw_chunk_ids: list[str],
    expected: list[str],
    membership: dict[str, tuple[str, frozenset[str]]],
) -> list[RetrievedEntry]:
    """Normalize retrieved IDs, crediting merged chunks for absorbed golds.

    Drop-in replacement for ``normalize_chunk_ids`` on the scoring path: each
    output position is the normalized chunk ID, widened to a set that also
    contains every golden ID from ``expected`` whose symbol the chunk absorbed
    (per ``membership``).  Deduplication matches ``normalize_chunk_ids`` —
    positions whose normalized own-ID was already seen are dropped.

    With an empty ``membership`` (merge-free index) the output equals
    ``normalize_chunk_ids(raw_chunk_ids)`` exactly.

    Args:
        raw_chunk_ids: Raw retrieved chunk IDs (line ranges intact).
        expected: Normalized golden IDs for the query (label ≥ 2; primaries
            are a subset, so one expansion serves recall and MRR alike).
        membership: Lookup from ``build_merged_membership``.

    Returns:
        Ordered list of entries for the ``calculate_*`` metric functions.
    """
    seen: set[str] = set()
    entries: list[RetrievedEntry] = []
    for raw in raw_chunk_ids:
        normalized = normalize_chunk_id(raw)
        if normalized in seen:
            continue
        seen.add(normalized)
        merged = membership.get(raw)
        if merged is None:
            entries.append(normalized)
            continue
        path, members = merged
        contained = {g for g in expected if _golden_id_matches_member(g, path, members)}
        entries.append({normalized} | contained if contained else normalized)
    return entries


# ---------------------------------------------------------------------------
# Community-aware file-coverage metrics (Category G, community ablation)
#
# Golden ids can never equal a synthetic community chunk's id
# ("__community__/<label>:community:<label>"), so chunk-id scoring is blind to
# whatever coverage community summaries provide.  Category G therefore scores
# **file recall**, reported twice side by side:
#
#   - strict: real code chunks only — a retrieved community chunk covers
#     nothing.  This is the decision metric.
#   - community-expanded: a retrieved community chunk covers its member
#     file-set, recovered by inverting the *persisted* community_map by the
#     chunk-id path token (merge-agnostic).  Reported next to strict — the
#     gap between the two is the finding, never a blended number.
#
# Community ids are read from result metadata ``tags`` ("community:<id>") at
# scoring time and NEVER stored in golden JSON (Louvain ids shift per reindex).
# ---------------------------------------------------------------------------

SYNTHETIC_COMMUNITY_PREFIX = "__community__/"


def extract_community_id(tags: Sequence[str] | None) -> int | None:
    """Return the community id from a ``community:<id>`` tag, or ``None``."""
    for tag in tags or []:
        if tag.startswith("community:"):
            try:
                return int(tag.split(":", 1)[1])
            except ValueError:
                return None
    return None


def build_community_file_map(
    community_map: dict[str, int],
) -> dict[int, frozenset[str]]:
    """Invert a persisted community map into per-community member file-sets.

    Member chunk_ids in the persisted map are raw pre-remerge ids
    (``file:lines:type[:name]``); the path token before the first colon is
    the member file, forward-slash normalized.  Merge-agnostic by
    construction — merged chunks never appear in the persisted map.

    Args:
        community_map: ``{chunk_id: community_id}`` as persisted in
            ``{project_id}_communities.json``.

    Returns:
        ``{community_id: frozenset of member relative paths}``.
    """
    files: dict[int, set[str]] = {}
    for chunk_id, community_id in community_map.items():
        path = normalize_path(chunk_id.split(":", 1)[0])
        if path:
            files.setdefault(community_id, set()).add(path)
    return {cid: frozenset(paths) for cid, paths in files.items()}


def build_file_entries(
    results_meta: Sequence[dict[str, Any]],
    community_files: dict[int, frozenset[str]] | None = None,
) -> tuple[list[set[str]], list[set[str]]]:
    """Derive per-rank file-coverage sets from result metadata, strict + expanded.

    Args:
        results_meta: One dict per retrieved result (rank order preserved) with
            ``relative_path`` and optionally ``tags``.  Synthetic community
            chunks are recognized by the ``__community__/`` path prefix.
        community_files: Inverted community map from
            ``build_community_file_map``; ``None``/empty means community
            chunks expand to nothing (detection-off arms).

    Returns:
        ``(strict_entries, expanded_entries)`` — parallel lists of per-rank
        file sets for ``calculate_file_recall_at_k``.  In strict entries a
        community chunk covers the empty set; in expanded entries it covers
        its community's member file-set (empty when the id is unknown).
    """
    strict: list[set[str]] = []
    expanded: list[set[str]] = []
    for meta in results_meta:
        path = normalize_path(meta.get("relative_path", "") or "")
        if path.startswith(SYNTHETIC_COMMUNITY_PREFIX):
            strict.append(set())
            community_id = extract_community_id(meta.get("tags"))
            members: frozenset[str] = frozenset()
            if community_id is not None:
                members = (community_files or {}).get(community_id, frozenset())
            expanded.append(set(members))
        else:
            file_set = {path} if path else set()
            strict.append(file_set)
            expanded.append(set(file_set))
    return strict, expanded


def calculate_file_recall_at_k(
    file_entries: Sequence[set[str]],
    expected_files: list[str],
    k: int,
) -> float:
    """File recall@k = |covered expected files in ranks [:k]| / |expected files|.

    Args:
        file_entries: Per-rank file-coverage sets (from ``build_file_entries``).
        expected_files: Golden ``expected_files`` (relative paths; normalized
            here so separator style never matters).
        k: Cut-off rank.

    Returns:
        Recall score in [0.0, 1.0].
    """
    if not expected_files:
        return 0.0
    expected_set = {normalize_path(f) for f in expected_files}
    covered: set[str] = set()
    for entry in file_entries[:k]:
        covered |= {normalize_path(f) for f in entry} & expected_set
    return len(covered) / len(expected_set)


def build_community_membership(
    community_map: dict[str, int],
) -> dict[int, frozenset[tuple[str, str]]]:
    """Invert a persisted community map into (path, symbol-name) member pairs.

    Companion to ``build_community_file_map`` for the symbol-level secondary
    metric: nameless member ids (e.g. ``file.py:1-8:module``) contribute no
    pair, mirroring ``_golden_id_matches_member``.

    Returns:
        ``{community_id: frozenset of (normalized_path, qualified_name)}``.
    """
    members: dict[int, set[tuple[str, str]]] = {}
    for chunk_id, community_id in community_map.items():
        parts = chunk_id.split(":")
        if len(parts) < 4:
            continue
        path = normalize_path(parts[0])
        name = parts[-1]
        if path and name:
            members.setdefault(community_id, set()).add((path, name))
    return {cid: frozenset(pairs) for cid, pairs in members.items()}


def expand_retrieved_with_community_credit(
    raw_chunk_ids: list[str],
    result_tags: Sequence[Sequence[str] | None],
    expected: list[str],
    community_membership: dict[int, frozenset[tuple[str, str]]],
) -> list[RetrievedEntry]:
    """Normalize retrieved IDs, crediting community chunks for member golds.

    The ``mrr_community_credit`` counterpart of
    ``expand_retrieved_with_containment``: a retrieved community-summary chunk
    is widened to every golden ID whose (path, name) pair belongs to that
    community's persisted membership.  Unlike merge containment credit (which
    fixed a proven false-negative scorer artifact), this encodes a *policy* —
    that "the answer lives in this retrieved neighborhood" deserves rank
    credit at all — so it is a labeled SECONDARY metric, never a decision
    trigger.  On community-free indexes callers must report N/A, not 0.0.

    Args:
        raw_chunk_ids: Raw retrieved chunk IDs (rank order preserved).
        result_tags: Per-result ``tags`` lists, parallel to ``raw_chunk_ids``.
        expected: Normalized golden IDs (primaries for MRR use).
        community_membership: Lookup from ``build_community_membership``.

    Returns:
        Ordered entries for the ``calculate_*`` metric functions.
    """
    seen: set[str] = set()
    entries: list[RetrievedEntry] = []
    for raw, tags in zip(raw_chunk_ids, result_tags, strict=True):
        normalized = normalize_chunk_id(raw)
        if normalized in seen:
            continue
        seen.add(normalized)
        community_id = extract_community_id(tags)
        pairs = (
            community_membership.get(community_id) if community_id is not None else None
        )
        if not pairs:
            entries.append(normalized)
            continue
        contained = set()
        for golden_id in expected:
            parts = golden_id.split(":")
            if len(parts) >= 3 and (normalize_path(parts[0]), parts[-1]) in pairs:
                contained.add(golden_id)
        entries.append({normalized} | contained if contained else normalized)
    return entries
