"""Shared FQN / line-number → chunk-id mapping helpers.

These functions were originally private helpers in
``scripts/benchmark/build_caller_oracle.py`` and are promoted here so that
both the oracle builder and the pyan-based external call-graph provider can
share the same logic without duplication.

Public API
----------
build_line_to_chunk_map   Build a per-file list of (start, end, chunk_id).
find_enclosing_chunk      Innermost chunk containing a given (file, line).
chunk_id_from_fqn         Best-effort FQN → chunk_id via module-path split.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from evaluation.metrics import normalize_chunk_id


def build_line_to_chunk_map(
    metadata_store: Any,
    semantic_types: frozenset[str] | None = None,
    normalize: bool = True,
) -> dict[str, list[tuple[int, int, str]]]:
    """Build a per-file sorted list of ``(start_line, end_line, chunk_id)``.

    Args:
        metadata_store: A dict-like store mapping raw chunk_id → entry dict.
            Each entry must have a nested ``"metadata"`` dict with keys
            ``relative_path``, ``start_line``, ``end_line``, and
            ``chunk_type``.
        semantic_types: Chunk types to include.  Defaults to
            ``{function, method, class, decorated_definition}``.
        normalize: When *True* (default), the stored ``chunk_id`` is the
            *normalized* id (line-range stripped via
            :func:`evaluation.metrics.normalize_chunk_id`).  When *False*,
            the raw store-key id is stored — required when mapping to graph
            node keys (which use raw ids).

    Returns:
        ``{relative_path: sorted [(start_line, end_line, chunk_id), ...]}``.
        The list for each path is sorted by ``(start_line, end_line)`` so
        that :func:`find_enclosing_chunk` can iterate it efficiently.
    """
    if semantic_types is None:
        semantic_types = frozenset(
            {"function", "method", "class", "decorated_definition"}
        )
    result: dict[str, list[tuple[int, int, str]]] = {}
    for raw_id, entry in metadata_store.items():
        meta = entry.get("metadata", {})
        path = meta.get("relative_path", "").replace("\\", "/")
        start = meta.get("start_line") or 0
        end = meta.get("end_line") or 0
        chunk_type = meta.get("chunk_type", "")
        if path and start and end and chunk_type in semantic_types:
            cid = normalize_chunk_id(raw_id) if normalize else raw_id
            result.setdefault(path, []).append((start, end, cid))
    for chunks in result.values():
        chunks.sort()
    return result


def find_enclosing_chunk(
    line_map: dict[str, list[tuple[int, int, str]]],
    rel_path: str,
    line_num: int,
) -> str | None:
    """Return the chunk_id of the innermost chunk containing ``(rel_path, line_num)``.

    "Innermost" means the chunk with the smallest line span that still
    contains *line_num*.  This correctly handles nested constructs (a method
    inside a class): the method chunk is returned rather than the class chunk.

    Args:
        line_map: Output of :func:`build_line_to_chunk_map`.
        rel_path: Relative path (forward-slash normalized) to look up.
        line_num: 1-based line number to locate.

    Returns:
        The chunk_id string (normalized or raw, matching whatever was stored in
        *line_map*), or *None* if no chunk contains the given line.
    """
    chunks = line_map.get(rel_path, [])
    best: str | None = None
    best_size = float("inf")
    for start, end, cid in chunks:
        if start <= line_num <= end:
            size = end - start
            if size < best_size:
                best_size = size
                best = cid
    return best


def chunk_id_from_fqn(
    fqn: str,
    line_map: dict[str, list[tuple[int, int, str]]],
    project_root: Path,  # noqa: ARG001  (kept for API parity / future use)
) -> str | None:
    """Best-effort mapping from a fully-qualified name to a chunk_id.

    Works for both PyCG-style FQNs and pyan-style FQNs, e.g.::

        search.relationship_analyzer.RelationshipAnalyzer._enrich_callers

    The algorithm progressively tries longer module paths paired with shorter
    name suffixes until it finds a file present in *line_map*, then picks the
    chunk whose normalized name matches the suffix.

    Args:
        fqn: Dotted fully-qualified name.
        line_map: Output of :func:`build_line_to_chunk_map`.
        project_root: Project root path (currently unused; kept for callers
            that pass it for context).

    Returns:
        A chunk_id string (normalized or raw, matching whatever was stored in
        *line_map*), or *None* if no match is found.
    """
    parts = fqn.split(".")
    # Try progressively longer module paths with shorter name suffixes.
    # E.g. for "a.b.C.method": tries "a/b/C.py::method", "a/b.py:C.method",
    # "a.py:b.C.method" in order.
    for split_at in range(len(parts) - 1, 0, -1):
        module_path = "/".join(parts[:split_at]) + ".py"
        name = ".".join(parts[split_at:])
        if module_path in line_map:
            for _, _, cid in line_map[module_path]:
                cid_name = cid.split(":")[-1]
                if cid_name == name or cid_name.endswith("." + name):
                    return cid
    return None
