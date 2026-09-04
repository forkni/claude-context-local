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

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from evaluation.metrics import normalize_chunk_id
from utils.path_utils import normalize_path


SPLIT_BLOCK = "split_block"

#: Chunk types mapped by default.  ``split_block`` fragments are included
#: since ADR-0061: every fragment of one oversized function/method is folded
#: into a single span keyed to that symbol (see :func:`_fold_split_groups`),
#: so a call-site line inside a long method resolves to the method rather
#: than to the enclosing ``class`` chunk.
#: "operator"/"network" are TouchDesigner network chunk types (ADR-0062,
#: Part C) -- included so line-mapped TD golden queries resolve to the
#: enclosing operator/network chunk the same way Python call sites do.
DEFAULT_SEMANTIC_TYPES: frozenset[str] = frozenset(
    {
        "function",
        "method",
        "class",
        "decorated_definition",
        SPLIT_BLOCK,
        "operator",
        "network",
    }
)


def _decorator_line_count(meta: Mapping[str, Any]) -> int:
    """Number of source lines the chunk's decorators occupy (0 when absent).

    ``metadata["decorators"]`` holds each decorator's full node text
    (``PythonChunker.extract_metadata``), which spans several lines for e.g.
    ``@pytest.mark.parametrize(\\n ...\\n)``; count lines, not entries.
    """
    decorators = meta.get("decorators") or []
    if not isinstance(decorators, (list, tuple)):
        return 0
    return sum(
        text.count("\n") + 1 if isinstance(text, str) else 1 for text in decorators
    )


def _definition_start(
    boundaries: list[tuple[int, int, int]],
    group_start: int,
    group_end: int,
) -> int:
    """Extend a split symbol's span backwards over its definition line(s).

    A ``split_block`` fragment starts at the first *body* statement, so the
    ``def`` line (plus any decorators and a multi-line signature) is covered
    by no fragment at all.  Both the LSP and the pyan resolver report a callee
    by exactly that ``def`` line, so without this extension the line lookup
    falls through to the enclosing class chunk.

    The definition is bounded below by every chunk that ends before the first
    fragment (the previous sibling: nothing but whitespace, comments,
    decorators and the signature can sit between its last line and the first
    body statement) and by every chunk that strictly encloses the group
    (the owning class: its ``class`` statement, plus one line per recorded
    decorator when it is a ``decorated_definition``, must stay outside the
    method's span).  The tightest of those bounds is used; a symbol with no
    preceding chunk at all extends to line 1.

    Args:
        boundaries: ``(start_line, end_line, decorator_count)`` for every
            chunk in the file with valid line numbers, any chunk type.
        group_start: Lowest ``start_line`` across the group's fragments.
        group_end: Highest ``end_line`` across the group's fragments.

    Returns:
        The 1-based line the merged span should start at (``<= group_start``).
    """
    candidates = [1]
    for start, end, n_decorators in boundaries:
        if end < group_start:
            candidates.append(end + 1)
        elif start < group_start and end >= group_end:
            # Strictly enclosing container: keep its own statement line (and
            # its decorator lines, which precede the statement) outside.
            candidates.append(start + 1 + n_decorators)
    return min(max(candidates), group_start)


def _fold_split_groups(
    groups: Mapping[tuple[str, str], list[tuple[int, int, str]]],
    boundaries: Mapping[str, list[tuple[int, int, int]]],
    normalize: bool,
) -> dict[str, list[tuple[int, int, str]]]:
    """Collapse each split symbol's fragments into one span with one chunk id.

    The span runs from the symbol's definition line (see
    :func:`_definition_start`) to the last line of its last fragment.  The id
    is the normalized symbol key when *normalize* is set (every fragment
    already shares it via :func:`evaluation.metrics.normalize_chunk_id`),
    otherwise the raw id of the fragment with the lowest ``start_line``.

    That is the same fragment the graph side already treats as the symbol's
    owner: ``GraphIntegration._resolve_callee`` picks the lowest-start
    fragment explicitly when a callee name matches only split blocks, and
    ``_extract_split_block_calls`` emits outgoing edges from the first
    fragment it *sees*, which is the lowest-start one because the chunker
    yields fragments in source order.  The election here sorts explicitly and
    does not depend on store iteration order.  No synthetic ``method:`` node
    is created (ADR-0061).
    """
    folded: dict[str, list[tuple[int, int, str]]] = {}
    for (path, key), fragments in groups.items():
        fragments.sort()
        group_start = fragments[0][0]
        group_end = max(end for _, end, _ in fragments)
        cid = key if normalize else fragments[0][2]
        start = _definition_start(boundaries.get(path, []), group_start, group_end)
        folded.setdefault(path, []).append((start, group_end, cid))
    return folded


def build_line_to_chunk_map(
    metadata_store: Any,
    semantic_types: frozenset[str] | None = None,
    normalize: bool = True,
) -> dict[str, list[tuple[int, int, str]]]:
    """Build a per-file sorted list of ``(start_line, end_line, chunk_id)``.

    ``split_block`` fragments (when included in *semantic_types*) never appear
    individually: all fragments of one symbol are folded into a single span
    that also covers the symbol's definition line, keyed to one chunk id —
    see :func:`_fold_split_groups`.  Every other chunk type maps one span
    per chunk.

    Args:
        metadata_store: A dict-like store mapping raw chunk_id → entry dict.
            Each entry must have a nested ``"metadata"`` dict with keys
            ``relative_path``, ``start_line``, ``end_line``, and
            ``chunk_type``.
        semantic_types: Chunk types to include.  Defaults to
            :data:`DEFAULT_SEMANTIC_TYPES`
            (``{function, method, class, decorated_definition, split_block}``).
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
        semantic_types = DEFAULT_SEMANTIC_TYPES
    result: dict[str, list[tuple[int, int, str]]] = {}
    # Every chunk with valid lines, any type: the bounds a split symbol's
    # definition line is searched between.
    boundaries: dict[str, list[tuple[int, int, int]]] = {}
    # (path, normalized symbol key) → raw fragments of one split symbol.
    split_groups: dict[tuple[str, str], list[tuple[int, int, str]]] = {}
    for raw_id, entry in metadata_store.items():
        meta = entry.get("metadata", {})
        path = normalize_path(meta.get("relative_path", ""))
        # Use get() without default so None and 0 both fall through to the
        # truthiness filter below (0 is not a valid 1-indexed line number).
        # Previously `or 0` masked None with 0, making the two cases indistinguishable
        # in any debug output — this makes the intent explicit (#48).
        start = meta.get("start_line")
        end = meta.get("end_line")
        chunk_type = meta.get("chunk_type", "")
        if not (path and start and end):
            continue
        boundaries.setdefault(path, []).append(
            (start, end, _decorator_line_count(meta))
        )
        if chunk_type not in semantic_types:
            continue
        if chunk_type == SPLIT_BLOCK:
            key = (path, normalize_chunk_id(raw_id))
            split_groups.setdefault(key, []).append((start, end, raw_id))
            continue
        cid = normalize_chunk_id(raw_id) if normalize else raw_id
        result.setdefault(path, []).append((start, end, cid))
    for path, spans in _fold_split_groups(split_groups, boundaries, normalize).items():
        result.setdefault(path, []).extend(spans)
    for chunks in result.values():
        chunks.sort()
    return result


def find_enclosing_chunk(
    line_map: Mapping[str, list[tuple[int, int, str]]],
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
            size = end - start + 1  # inclusive span (#48)
            if size < best_size:
                best_size = size
                best = cid
    return best


def _chunk_name(cid: str) -> str:
    """Return the name segment of ``path:[start-end:]kind:name``."""
    return cid.split(":")[-1]


def chunk_id_from_fqn(
    fqn: str,
    line_map: dict[str, list[tuple[int, int, str]]],
    project_root: Path,  # noqa: ARG001  (kept for API parity / future use)
) -> str | None:
    """Best-effort mapping from a fully-qualified name to a chunk_id.

    Works for both PyCG-style, pyan-style and LibCST-style FQNs, e.g.::

        search.relationship_analyzer.RelationshipAnalyzer._enrich_callers

    The algorithm progressively tries longer module paths paired with shorter
    name suffixes until it finds a file present in *line_map*, then picks the
    chunk whose normalized name matches the suffix.

    Match priority within a file (first non-empty tier wins):

    1. **Exact qualified match** — the chunk name equals the FQN tail
       (``module.func`` → ``function:func``; ``module.Class.method`` →
       ``method:Class.method``; ``module.Outer.Inner.m`` →
       ``method:Outer.Inner.m``).
    2. **Suffix match** — the chunk name ends with ``"." + tail`` (e.g. a
       pyan FQN that omits an enclosing class).  When several remain, the
       one with the fewest extra qualifying parts wins (``Klass.run`` beats
       ``Outer.Klass.run`` for tail ``run``); ties fall back to file order.

    Shape is taken from the chunk *name* (its dot-separated part count),
    never from the kind segment: ``decorated_definition`` wraps either
    shape, and :func:`search.chunk_id.dedup_key` collapses ``split_block``
    to ``method`` on normalization, so a split module-level function reads
    as ``method:big_func`` in a ``normalize=True`` line map.

    This tiering is what stops a same-file ``_NoopExporter.force_flush``
    method from shadowing the module-level ``force_flush`` function when
    the FQN is ``utils.observability.force_flush`` (resolver precision row
    11, 2026-09-02).

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
        chunks = line_map.get(module_path)
        if not chunks:
            continue
        suffix_best: tuple[int, int, str] | None = None
        for order, (_, _, cid) in enumerate(chunks):
            cid_name = _chunk_name(cid)
            if cid_name == name:
                return cid  # exact tier: first in file order wins
            if cid_name.endswith("." + name):
                extra = cid_name.count(".") - name.count(".")
                key = (extra, order, cid)
                if suffix_best is None or key < suffix_best:
                    suffix_best = key
        if suffix_best is not None:
            return suffix_best[2]
    return None
