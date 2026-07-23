"""Rendering seam: SearchResult -> MCP JSON.

Pure functions with no MCP-framework, orchestrator, or global-state
dependencies — a leaf module. Complements ``search/result_factory.py``,
which is the *input* side (raw tuples -> ``SearchResult``); this module is
the *output* side (``SearchResult`` -> MCP JSON dicts).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from graph.schema import get_reverse_relation
from search.filters import normalize_path


if TYPE_CHECKING:
    from search.indexer import CodeIndexManager

logger = logging.getLogger(__name__)


def _get_reverse_relation_name(rel_type: str) -> str:
    """Get the reverse name for a relationship type.

    Delegates to ``graph.schema.get_reverse_relation`` — the single owner
    of the forward→reverse mapping.

    Args:
        rel_type: Forward relationship type (e.g., "calls", "inherits")

    Returns:
        Reverse relationship name (e.g., "called_by", "inherited_by")
    """
    return get_reverse_relation(rel_type)


def _get_graph_data_for_chunk(
    index_manager: CodeIndexManager, chunk_id: str, max_per_type: int = 5
) -> dict | None:
    """Get all graph relationship data for a chunk (21 relationship types).

    Iterates outgoing and incoming edges, grouping by relationship type.
    Also checks incoming edges by bare symbol name, since edges often
    target symbol names (e.g., "login") rather than full chunk_ids.

    Args:
        index_manager: The index manager with graph storage
        chunk_id: The chunk to get graph data for
        max_per_type: Maximum targets/sources per relationship type (default: 5)

    Returns:
        dict mapping relationship names to lists of chunk_ids/symbols, or None
    """
    try:
        graph = index_manager.graph_storage
        normalized = normalize_path(chunk_id)
        result: dict[str, list[str]] = {}

        # Early return if node not in graph
        if normalized not in graph.graph:
            return None

        # Outgoing edges (this chunk is source) -> forward relation names
        for _, target, edge_data in graph.graph.out_edges(normalized, data=True):
            rel_type = edge_data.get("type", "calls")
            lst = result.setdefault(rel_type, [])
            if len(lst) < max_per_type:
                lst.append(target)

        # Incoming edges by chunk_id -> reverse relation names
        for source, _, edge_data in graph.graph.in_edges(normalized, data=True):
            rel_type = edge_data.get("type", "calls")
            reverse = _get_reverse_relation_name(rel_type)
            lst = result.setdefault(reverse, [])
            if len(lst) < max_per_type:
                lst.append(source)

        # Incoming edges by symbol name (edges often target bare names)
        symbol_name = normalized.rsplit(":", 1)[-1] if ":" in normalized else None
        if symbol_name and symbol_name != normalized and symbol_name in graph.graph:
            for source, _, edge_data in graph.graph.in_edges(symbol_name, data=True):
                rel_type = edge_data.get("type", "calls")
                reverse = _get_reverse_relation_name(rel_type)
                lst = result.setdefault(reverse, [])
                if len(lst) < max_per_type and source not in lst:
                    lst.append(source)

        return result if result else None
    except Exception as e:  # noqa: BLE001 - resilience: optional graph enrichment, degrade to no graph data
        logger.debug(f"Failed to get graph data for {chunk_id}: {e}")
    return None


def _format_search_results(results: list) -> list[dict]:
    """Format search results to JSON-serializable dicts.

    Args:
        results: List of SearchResult objects

    Returns:
        List of formatted result dictionaries
    """
    formatted_results = []
    for result in results:
        # Unified thin SearchResult format (reranker.SearchResult — all results)
        item = {
            "file": result.metadata.get("relative_path", ""),
            "lines": f"{result.metadata.get('start_line', 0)}-{result.metadata.get('end_line', 0)}",
            "kind": result.metadata.get("chunk_type", "unknown"),
            "score": round(result.score, 2),
            "chunk_id": result.chunk_id,
        }
        # Add name for module-type results (helps identify what the chunk represents)
        name = result.metadata.get("name", "")
        if name:
            item["name"] = name
        # Add docstring preview for module summaries (compressed context).
        # §V-B note: this is unsanitized resource content (paper term) — the raw
        # docstring text from the indexed repo, truncated but not filtered.
        # Accepted residual risk: exposure is metadata-only (never code bodies,
        # never executed/eval'd, capped at 200 chars) and the source is the
        # user's own indexed codebase, not an untrusted external fetch. A repo
        # containing a hostile docstring could still relay prompt-injection-like
        # text to the calling LLM as part of a search result; no content
        # filtering is applied here today.
        if result.metadata.get("chunk_type") in ("module", "community"):
            doc = result.metadata.get("docstring", "")
            if doc:
                item["summary"] = doc[:200]
        # Add reranker score if available (neural reranking)
        if "reranker_score" in result.metadata:
            item["reranker_score"] = round(result.metadata["reranker_score"], 4)
        # Add complexity score if available (functions only)
        if result.metadata.get("complexity_score"):
            item["complexity_score"] = result.metadata["complexity_score"]
        # Propagate source field for ego-graph neighbor identification
        if hasattr(result, "source") and result.source:
            item["source"] = result.source
        formatted_results.append(item)
    return formatted_results


def _parse_line(lines_str: str, part: int = 0) -> int:
    """Extract start (part=0) or end (part=-1) line from 'start-end' format."""
    try:
        return int(lines_str.split("-")[part])
    except (ValueError, IndexError, AttributeError):
        return 0


def _reorder_by_source_position(results: list[dict]) -> list[dict]:
    """Reorder results by file source position (DOS RAG technique).

    Groups results by file path and sorts each group by start line number.
    Inter-file ordering is preserved by each file group's highest score.
    Gap indicators are added between non-contiguous chunks from the same file.

    Based on: "Stronger Baselines for RAG with Long-Context LMs" (EMNLP 2025).
    Sorting retrieved chunks into original document order gives +5.3% accuracy
    over similarity-ranked order at zero retrieval cost.

    Args:
        results: List of formatted result dicts with "file" and "lines" fields

    Returns:
        Results reordered by source position, with gap indicators inserted
    """
    if not results:
        return results

    # Group results by file, preserving highest score per group for inter-file ordering
    file_groups: dict[str, list[dict]] = {}
    file_best_score: dict[str, float] = {}

    for result in results:
        file_key = result.get("file", "")
        bs = result.get("blended_score")
        score = bs if bs is not None else result.get("score", 0.0)
        if file_key not in file_groups:
            file_groups[file_key] = []
            file_best_score[file_key] = score
        else:
            file_best_score[file_key] = max(file_best_score[file_key], score)
        file_groups[file_key].append(result)

    # Sort file groups by their best score (descending)
    sorted_files = sorted(
        file_groups.keys(), key=lambda f: file_best_score[f], reverse=True
    )

    reordered: list[dict] = []
    for file_key in sorted_files:
        group = file_groups[file_key]
        # Sort chunks within each file by start line
        group.sort(key=lambda r: _parse_line(r.get("lines", "0"), 0))

        # Annotate gap info on the preceding chunk (gap_after field) to avoid
        # injecting synthetic rows that would dilute downstream [:k] slices.
        for i, chunk in enumerate(group):
            reordered.append(chunk)
            if i < len(group) - 1:
                curr_end = _parse_line(group[i].get("lines", "0"), -1)
                next_start = _parse_line(group[i + 1].get("lines", "0"), 0)
                gap = next_start - curr_end - 1
                if gap > 0:
                    chunk["gap_after"] = f"[... {gap} lines omitted ...]"

    return reordered


def _enrich_results_with_graph_data(
    results: list[dict], index_manager: CodeIndexManager | None
) -> list[dict]:
    """Add graph relationship data to search results.

    Args:
        results: List of formatted result dicts
        index_manager: Index manager with graph storage

    Returns:
        Results with graph data added where available
    """
    if not index_manager or index_manager.graph_storage is None:
        return results

    for item in results:
        chunk_id = item.get("chunk_id")
        # Skip per-result graph data for ego-graph neighbors (captured in subgraph_edges instead)
        # Saves ~400 chars per ego neighbor, ~8K chars total for 20 neighbors
        if chunk_id and item.get("source") != "ego_graph":
            graph_data = _get_graph_data_for_chunk(index_manager, chunk_id)
            if graph_data:
                item["graph"] = graph_data

    return results
