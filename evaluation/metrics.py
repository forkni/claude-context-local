"""Information Retrieval evaluation metrics for SSCG benchmark.

Deterministic ground-truth-based metrics — no LLM judge required.
All functions accept normalized chunk IDs (line ranges stripped).

Ported from: _archive/BENCHMARKING/tools/benchmark_retrieval_quality.py
"""

import math
import re
from statistics import mean
from typing import Any


# Regex to strip line-number ranges from chunk IDs.
# Matches: "file/path.py:123-456:type:name" → "file/path.py:type:name"
# Also handles module chunks: "file/path.py:1-8:module" → "file/path.py:module"
_LINE_RANGE_RE = re.compile(r":\d+-\d+:")

THRESHOLDS = {
    "mrr": 0.50,
    "recall_at_5": 0.70,
    "hit_rate_at_5": 0.80,
}


def normalize_chunk_id(chunk_id: str) -> str:
    """Strip line-range component from a chunk ID for stable comparison.

    Line numbers shift as code evolves. Comparison uses only the stable
    ``file_path:type:name`` portion.

    Examples::

        "search/config.py:148-161:decorated_definition:EmbeddingConfig"
        → "search/config.py:decorated_definition:EmbeddingConfig"

        "merkle/__init__.py:1-8:module"
        → "merkle/__init__.py:module"
    """
    return _LINE_RANGE_RE.sub(":", chunk_id, count=1)


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
# ---------------------------------------------------------------------------


def calculate_recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """Recall@k = |retrieved[:k] ∩ relevant| / |relevant|.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (normalized).
        relevant: Set of relevant chunk IDs (normalized, label ≥ 2).
        k: Cut-off rank.

    Returns:
        Recall score in [0.0, 1.0].
    """
    if not relevant:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / len(relevant_set)


def calculate_precision_at_k(
    retrieved: list[str], relevant: list[str], k: int
) -> float:
    """Precision@k = |retrieved[:k] ∩ relevant| / k.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (normalized).
        relevant: Set of relevant chunk IDs (normalized, label ≥ 2).
        k: Cut-off rank.

    Returns:
        Precision score in [0.0, 1.0].
    """
    if k == 0:
        return 0.0
    retrieved_k = set(retrieved[:k])
    relevant_set = set(relevant)
    return len(retrieved_k & relevant_set) / k


def calculate_mrr(retrieved: list[str], relevant: list[str]) -> float:
    """Mean Reciprocal Rank of the first highly-relevant (label=3) result.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (normalized).
        relevant: Set of primary/highly-relevant chunk IDs (normalized, label=3).

    Returns:
        Reciprocal rank (1/rank) of first hit, or 0.0 if none found.
    """
    relevant_set = set(relevant)
    for i, chunk_id in enumerate(retrieved, 1):
        if chunk_id in relevant_set:
            return 1.0 / i
    return 0.0


def calculate_ndcg_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    """NDCG@k with binary relevance (label ≥ 2 = 1, otherwise 0).

    Args:
        retrieved: Ordered list of retrieved chunk IDs (normalized).
        relevant: Set of relevant chunk IDs (normalized, label ≥ 2).
        k: Cut-off rank.

    Returns:
        NDCG score in [0.0, 1.0].
    """
    relevant_set = set(relevant)
    dcg = sum(
        1.0 / math.log2(i + 1)
        for i, cid in enumerate(retrieved[:k], 1)
        if cid in relevant_set
    )
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(relevant_set), k) + 1))
    return dcg / idcg if idcg > 0 else 0.0


def calculate_metrics_from_results(
    retrieved: list[str],
    expected: list[str],
    expected_primary: list[str] | None = None,
) -> dict[str, float]:
    """Calculate all retrieval metrics for a single query.

    Args:
        retrieved: Ordered list of retrieved chunk IDs (normalized).
        expected: Relevant chunk IDs with label ≥ 2.
        expected_primary: Highly-relevant chunk IDs with label = 3.
            Falls back to ``expected`` if not provided (for MRR calculation).

    Returns:
        Dict with keys: recall@1, recall@5, recall@10, precision@1,
        precision@5, precision@10, mrr, ndcg@5, ndcg@10, hit.
    """
    primary = expected_primary if expected_primary is not None else expected
    return {
        "recall@1": calculate_recall_at_k(retrieved, expected, 1),
        "recall@5": calculate_recall_at_k(retrieved, expected, 5),
        "recall@10": calculate_recall_at_k(retrieved, expected, 10),
        "precision@1": calculate_precision_at_k(retrieved, expected, 1),
        "precision@5": calculate_precision_at_k(retrieved, expected, 5),
        "precision@10": calculate_precision_at_k(retrieved, expected, 10),
        "mrr": calculate_mrr(retrieved, primary),
        "ndcg@5": calculate_ndcg_at_k(retrieved, expected, 5),
        "ndcg@10": calculate_ndcg_at_k(retrieved, expected, 10),
        "hit": calculate_recall_at_k(retrieved, expected, 5) > 0,
    }


def aggregate_metrics(per_query: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics across all per-query metric dicts.

    Args:
        per_query: List of dicts, each from ``calculate_metrics_from_results``.

    Returns:
        Aggregate dict with means, pass/fail assessment, and counts.
    """
    if not per_query:
        return {}

    float_keys = [
        "recall@1",
        "recall@5",
        "recall@10",
        "precision@1",
        "precision@5",
        "precision@10",
        "mrr",
        "ndcg@5",
        "ndcg@10",
    ]
    agg: dict[str, Any] = {
        "total_queries": len(per_query),
        "success_count": sum(1 for q in per_query if q.get("hit", False)),
    }
    for key in float_keys:
        # Use 0.0 for queries missing a key (e.g. error rows) so they count
        # against the aggregate rather than being silently excluded.
        vals = [float(q.get(key, 0.0)) for q in per_query]
        agg[key] = round(mean(vals), 4) if vals else 0.0

    agg["hit_rate@5"] = round(agg["success_count"] / agg["total_queries"], 4)

    agg["pass_fail"] = {
        "mrr": "PASS" if agg["mrr"] >= THRESHOLDS["mrr"] else "FAIL",
        "recall@5": "PASS" if agg["recall@5"] >= THRESHOLDS["recall_at_5"] else "FAIL",
        "hit_rate@5": "PASS"
        if agg["hit_rate@5"] >= THRESHOLDS["hit_rate_at_5"]
        else "FAIL",
    }

    # Line-overlap metrics — only average queries where the key is present
    # (queries without golden line ranges are excluded, not counted as 0)
    for key in ("line_recall", "line_precision", "line_iou"):
        vals = [float(q[key]) for q in per_query if key in q]
        if vals:
            agg[key] = round(mean(vals), 4)
            agg[f"{key}_count"] = len(vals)

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
    for start, end in sorted_ranges[1:]:
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
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if lo <= hi:
            result.append((lo, hi))
        if a[i][1] < b[j][1]:
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
    return covered / total_golden if total_golden > 0 else 0.0


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
    if total_retrieved == 0:
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
    return overlap / union if union > 0 else 0.0


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
        path = meta.get("relative_path", "")
        start = meta.get("start_line") or 0
        end = meta.get("end_line") or 0
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
