"""Rendering seam: SearchResult -> MCP JSON.

Pure functions with no MCP-framework, orchestrator, or global-state
dependencies — a leaf module. Complements ``search/result_factory.py``,
which is the *input* side (raw tuples -> ``SearchResult``); this module is
the *output* side (``SearchResult`` -> MCP JSON dicts).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
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
        if result.metadata.get("chunk_type") == "module":
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
        # Flag fabricated-score results (D9) so a caller can tell unranked
        # context (e.g. parent-expansion's fixed 0.0) from an actual ranked
        # hit. Only added when true -- matches this function's existing
        # only-add-when-relevant convention for source/reranker_score/etc.
        if getattr(result, "is_unscored", False):
            item["is_unscored"] = True
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


def _extract_signature_estimate(
    text: str,
    max_lines: int = 15,
    no_anchor_lines: int = 3,
    max_chars: int = 600,
) -> str:
    """Extract a signature-only prefix from raw chunk source text.

    Line-scans for a ``def ``/``async def ``/``class `` anchor and stops at the
    first line ending in ``:`` seen at or after the anchor, capped at
    ``max_lines``. Originally ported from a probe-only reimplementation in
    ``scripts/benchmark/probe_context_cost.py``; that copy has since been
    retired (ADR-0040) in favor of importing this function directly, so this
    is now the single implementation both the wire field and the offline
    ``_signature_view_tokens`` estimate use. Two additions beyond the
    original line-scan:

    1. When no anchor is seen within ``max_lines`` — non-Python chunks, whose
       grammars don't share Python's ``def``/``class`` keywords, and
       ``module_preamble``/``module`` chunks with no anchor at all — only the
       first ``no_anchor_lines`` lines are returned instead of the full
       15-line body. Without this, an un-anchored chunk would silently
       degenerate from a signature into an arbitrary body excerpt.
    2. The result is truncated to ``max_chars``. The line caps bound *line
       count*, not line *length*: a minified/single-line chunk (e.g. bundled
       JS) can pack thousands of characters into one "line" and blow past any
       reasonable token budget despite passing both line caps untouched.
       Measured on a 9,610-chunk corpus: 0.9% of chunks carry 7.5% of all
       signature tokens, with one minified-JS chunk alone producing a
       3,877-token "signature". ``max_chars=600`` sits between the p99 (420)
       and p99.9 (672) character length of legitimate anchored signatures, so
       it clips well under 1% of real signatures while bounding the tail.

    Args:
        text: Raw chunk source (``bm25_text`` from the metadata store).
        max_lines: Cap on the anchored scan (default: 15).
        no_anchor_lines: Cap when no anchor is found (default: 3).
        max_chars: Cap on the final extracted text length (default: 600).

    Returns:
        The extracted signature text (may be shorter than either cap).
    """
    lines = text.split("\n")
    sig_lines: list[str] = []
    seen_start = False
    for line in lines[:max_lines]:
        sig_lines.append(line)
        stripped = line.strip()
        if stripped.startswith(("def ", "async def ", "class ")):
            seen_start = True
        if seen_start and stripped.endswith(":"):
            break
    if not seen_start:
        sig_lines = lines[:no_anchor_lines]
    return "\n".join(sig_lines)[:max_chars]


_NON_SIGNATURE_CHUNK_TYPES = frozenset({"module_preamble", "module"})
"""Chunk kinds with no callable contract to summarize.

Measured over 2,534 corpus chunks (reproduced on a second, 9,610-chunk
corpus): every ``method``/``function``/``split_block``/``decorated_definition``/
``class`` chunk is 100% anchored by ``_extract_signature_estimate``, while
``module_preamble``/``module`` chunks are 0% anchored — their "signature" is
whatever the first ``no_anchor_lines`` lines happen to be (a docstring line,
an import, a comment). Skipping these two kinds removes ~20-22% of signature
tokens and 0% of callable contracts; see ``_enrich_results_with_signatures``.
"""


def _annotate_each(
    results: list[dict],
    index_manager: CodeIndexManager | None,
    *,
    storage_attr: str,
    skip_ego: bool,
    skip_kinds: frozenset[str],
    annotate: Callable[[dict, str], None],
) -> list[dict]:
    """Run *annotate* over each enrichable item, owning guard/skip/resilience.

    Shared scaffolding hand-copied by all three result enrichers before this
    extraction: the index-manager/storage guard, the per-item falsy-``chunk_id``
    skip, the optional ego-graph skip, the optional kind skip, and a per-item
    ``try/except Exception`` -> ``logger.debug`` so one bad chunk cannot abort
    enrichment for the rest of the batch. ``annotate`` receives the
    already-guarded ``(item, chunk_id)`` pair and mutates ``item`` in place;
    its return value is ignored.

    Args:
        results: List of formatted result dicts.
        index_manager: Index manager providing the storage named by
            ``storage_attr``; enrichment is skipped entirely when this is
            ``None`` or that storage attribute is ``None``.
        storage_attr: Attribute name on ``index_manager`` whose presence
            gates enrichment (``"graph_storage"`` or ``"metadata_store"``).
        skip_ego: Skip results whose ``source`` is ``"ego_graph"``.
        skip_kinds: Skip results whose ``kind`` is in this set.
        annotate: Per-item callable ``(item, chunk_id) -> None``.

    Returns:
        The same ``results`` list, mutated in place.
    """
    if not index_manager or getattr(index_manager, storage_attr) is None:
        return results

    for item in results:
        chunk_id = item.get("chunk_id")
        if not chunk_id:
            continue
        if skip_ego and item.get("source") == "ego_graph":
            continue
        if item.get("kind") in skip_kinds:
            continue
        try:
            annotate(item, chunk_id)
        except Exception as e:  # noqa: BLE001 - resilience: optional result enrichment, degrade to no field
            logger.debug(f"Failed to enrich result for {chunk_id}: {e}")

    return results


def _enrich_results_with_signatures(
    results: list[dict],
    index_manager: CodeIndexManager | None,
) -> list[dict]:
    """Attach a ``signature`` field (signature-only view) to each result.

    ``search_code`` returns coordinates only (file/lines/kind/score) — no
    chunk content. A context agent that finds the right chunk still needs a
    follow-up ``Read`` to judge it (measured: 0% of results carry any content
    field, `evaluation/CONTEXT_COST_PROBE_20260818.md`). This attaches a
    cheap, opt-in counterfactual: the first def/class line(s) of the chunk,
    extracted from ``bm25_text`` via ``_extract_signature_estimate``.

    Results whose ``kind`` is in ``_NON_SIGNATURE_CHUNK_TYPES`` are skipped
    entirely (no ``signature`` field attached, matching the existing
    skip-on-falsy behavior below) — these kinds carry no def/class anchor, so
    their "signature" would be filler rather than a callable contract.

    ``bm25_text`` — the raw chunk source persisted by the indexer
    (``hybrid_searcher.py``) — is read via ``index_manager.metadata_store``
    rather than any field on the formatted result dict: results reach this
    function post-``_format_search_results``, which carries no ``.metadata``.
    The same metadata entry already carries ``chunk_type``, so the kind-gate
    above costs no extra lookup.

    §V-B note: this is unsanitized resource content (paper term) — raw source
    text from the indexed repo, truncated but not filtered. Accepted residual
    risk: exposure is metadata-only (never a full code body — capped at 15
    lines and 600 chars — never executed/eval'd) and the source is the user's
    own indexed codebase, not an untrusted external fetch. A repo containing a
    hostile docstring or comment could still relay prompt-injection-like text
    to the calling LLM as part of a search result; no content filtering is
    applied here today. Same exposure class already accepted for the
    ``summary`` field above.

    Args:
        results: List of formatted result dicts
        index_manager: Index manager with metadata storage

    Returns:
        Results with ``signature`` added where ``bm25_text`` is available
    """

    def _annotate(item: dict, chunk_id: str) -> None:
        entry = index_manager.metadata_store.get(chunk_id)
        if not entry:
            return
        bm25_text = entry.get("metadata", {}).get("bm25_text")
        if not bm25_text:
            return
        item["signature"] = _extract_signature_estimate(bm25_text)

    return _annotate_each(
        results,
        index_manager,
        storage_attr="metadata_store",
        skip_ego=False,
        skip_kinds=_NON_SIGNATURE_CHUNK_TYPES,
        annotate=_annotate,
    )


def _enrich_results_with_top_callers(
    results: list[dict],
    index_manager: CodeIndexManager | None,
    max_callers: int = 2,
) -> list[dict]:
    """Attach a ``top_callers`` hint (up to ``max_callers``) to each result.

    Per result, scans raw incoming ``calls``-type edges on the chunk_id node.
    Unresolved AST call edges target the bare symbol-name node rather than the
    chunk_id node (see ``graph_storage.add_call_edge``) — the common case when
    the ``[callgraph]`` extras are absent — so the bare-symbol node is
    consulted as a *fallback*, mirroring ``_get_graph_data_for_chunk``'s
    two-lookup pattern, and only when the chunk node alone yields fewer than
    ``max_callers`` candidates.

    The symbol-node fallback is unreliable in a way the chunk-node lookup is
    not: an edge into a bare symbol name like ``get`` or ``add`` conflates
    every definition of that name across the whole project (100% of these
    edges carry no confidence tag at all — see the Fix #2 census), so a
    common method name produces false hints while a unique name produces true
    ones. There is no per-edge signal to distinguish the two cases, so this
    function treats the *lookup tier* itself as the confidence signal:
    chunk-node candidates always sort before symbol-node candidates,
    regardless of any ``resolver_confidence`` float either carries. Within
    each tier, ranking is ``resolver_confidence`` descending where the float
    exists, insertion order otherwise. Skips silently when the graph or node
    is absent.

    Args:
        results: List of formatted result dicts
        index_manager: Index manager with graph storage
        max_callers: Maximum caller entries per result (default: 2)

    Returns:
        Results with ``top_callers: [{name, file}]`` added where callers exist
    """
    if not index_manager or index_manager.graph_storage is None:
        return results

    graph = index_manager.graph_storage.graph

    def _collect(node: str, seen: set[str], normalized: str) -> list[tuple[str, dict]]:
        """In-edge ``calls`` candidates at ``node``, deduped against ``seen``."""
        found: list[tuple[str, dict]] = []
        if node not in graph:
            return found
        for source, _, edge_data in graph.in_edges(node, data=True):
            if edge_data.get("type", "calls") != "calls":
                continue
            if source in seen or source == normalized:
                continue
            seen.add(source)
            found.append((source, edge_data))
        return found

    def _annotate(item: dict, chunk_id: str) -> None:
        normalized = normalize_path(chunk_id)
        symbol_name = normalized.rsplit(":", 1)[-1] if ":" in normalized else None

        seen: set[str] = set()
        chunk_candidates = _collect(normalized, seen, normalized)

        symbol_candidates: list[tuple[str, dict]] = []
        if (
            len(chunk_candidates) < max_callers
            and symbol_name
            and symbol_name != normalized
        ):
            symbol_candidates = _collect(symbol_name, seen, normalized)

        if not chunk_candidates and not symbol_candidates:
            return

        # Chunk-node tier always sorts before symbol-node tier; within a
        # tier, float-confident edges first (desc), the rest keep
        # discovery order via missing-confidence -> 0.0.
        tiered = [(c, False) for c in chunk_candidates] + [
            (c, True) for c in symbol_candidates
        ]
        tiered.sort(key=lambda t: (t[1], -(t[0][1].get("resolver_confidence") or 0.0)))

        top_callers = []
        for (source, _), _is_symbol_tier in tiered[:max_callers]:
            node_name = graph.nodes[source].get("name") if source in graph else None
            top_callers.append(
                {
                    "name": node_name
                    or (source.rsplit(":", 1)[-1] if ":" in source else source),
                    "file": source.split(":")[0] if ":" in source else "",
                }
            )
        item["top_callers"] = top_callers

    return _annotate_each(
        results,
        index_manager,
        storage_attr="graph_storage",
        skip_ego=False,
        skip_kinds=frozenset(),
        annotate=_annotate,
    )


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

    def _annotate(item: dict, chunk_id: str) -> None:
        graph_data = _get_graph_data_for_chunk(index_manager, chunk_id)
        if graph_data:
            item["graph"] = graph_data

    # Skip per-result graph data for ego-graph neighbors (captured in
    # subgraph_edges instead) — saves ~400 chars per ego neighbor, ~8K chars
    # total for 20 neighbors. Unlike the other two enrichers, this one had no
    # per-item try/except of its own: routing it through the shared one in
    # _annotate_each is a narrowing of failure surface, not a widening —
    # _get_graph_data_for_chunk already swallows its own exceptions and
    # returns None.
    return _annotate_each(
        results,
        index_manager,
        storage_attr="graph_storage",
        skip_ego=True,
        skip_kinds=frozenset(),
        annotate=_annotate,
    )


@dataclass(frozen=True)
class ResultEnricher:
    """One registry row: a gate key, the field it writes, and its apply function."""

    key: str
    field: str
    apply: Callable[[list[dict], CodeIndexManager | None], list[dict]]


RESULT_ENRICHERS: tuple[ResultEnricher, ...] = (
    ResultEnricher("graph", "graph", _enrich_results_with_graph_data),
    ResultEnricher("top_callers", "top_callers", _enrich_results_with_top_callers),
    ResultEnricher("signatures", "signature", _enrich_results_with_signatures),
)
"""Every result enricher, in application order (today's ``_assemble`` order).

Adding a fourth enricher is a new row here plus a gate entry in
``SearchOrchestrator._enrichment_gates`` — nothing else in this module or
the caller needs to change.
"""


def enrich_results(
    results: list[dict],
    index_manager: CodeIndexManager | None,
    gates: Mapping[str, bool],
) -> list[dict]:
    """Apply every gated enricher in ``RESULT_ENRICHERS`` order.

    Args:
        results: List of formatted result dicts.
        index_manager: Index manager passed through to each enricher.
        gates: Per-enricher on/off decision, keyed by ``ResultEnricher.key``.
            A missing key is treated as off, not an error.

    Returns:
        The same ``results`` list, mutated in place by whichever enrichers
        were gated on.
    """
    for enricher in RESULT_ENRICHERS:
        if gates.get(enricher.key):
            results = enricher.apply(results, index_manager)
    return results
