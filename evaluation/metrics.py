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
        vals = [q[key] for q in per_query if key in q]
        agg[key] = round(mean(vals), 4) if vals else 0.0

    agg["hit_rate@5"] = round(agg["success_count"] / agg["total_queries"], 4)

    agg["pass_fail"] = {
        "mrr": "PASS" if agg["mrr"] >= THRESHOLDS["mrr"] else "FAIL",
        "recall@5": "PASS" if agg["recall@5"] >= THRESHOLDS["recall_at_5"] else "FAIL",
        "hit_rate@5": "PASS"
        if agg["hit_rate@5"] >= THRESHOLDS["hit_rate_at_5"]
        else "FAIL",
    }
    return agg
