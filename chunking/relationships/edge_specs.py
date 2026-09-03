"""Spec-row table for which tree-sitter languages emit chunker-native edges.

Mirrors the pattern already used by ``chunking/language_registry.py``
(``LANGUAGE_SPECS``) and ``chunking/relationships/relationship_extractors/registry.py``
(``RELATIONSHIP_EXTRACTORS``): a data table instead of a hand-written
``language == "glsl"`` conditional. A tree-sitter language chunker that walks its own
parse tree and appends plain ``(name, line)`` pairs / relationship dicts to
``metadata["calls"]`` / ``metadata["relationships"]`` (as ``GLSLChunker`` does — see
``chunking/languages/glsl.py``) gets one row here; ``MultiLanguageChunker`` looks the
row up by ``tchunk.language`` instead of naming the language directly.

**Absence of a row is the "this language does not use this path" answer.** Python
deliberately gets no row: its call edges come from ``PythonCallGraphExtractor`` at a
different seam entirely (a re-parse of dedented chunk content via
``chunking/relationships/call_graph_extractor.py``), so a row here would either
double-extract or misrepresent that path's provenance.

Confidence caveat (verified — see the plan this table shipped under): a chunk-level
``call_confidence`` here is **not** the same signal as a resolver tier's
``resolver_confidence``. ``GraphIntegration._make_spec_from_chunk``
(``search/graph_integration.py``) projects each ``CallEdge`` down to
``callee_name``/``line_number``/``is_method_call``/``callee_qualified`` and drops
``confidence`` entirely — graph call edges carry the string tags ``"exact"`` /
``"ambiguous"`` instead. So ``call_confidence`` survives only in
``CodeChunk.calls[].confidence`` and its persisted ``to_dict()``; it never becomes a
``resolver_confidence`` value and is never compared against
``CallGraphConfig.min_confidence``. A future row with a low ``call_confidence`` is
*not* filtered by that floor — don't assume it is.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, NamedTuple

from chunking.relationships.call_graph_extractor import CallEdge
from chunking.relationships.relationship_types import RelationshipEdge, RelationshipType


if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk

logger = logging.getLogger(__name__)


class CallSite(NamedTuple):
    """One call-expression site emitted by a chunker's own parse-tree walk.

    Widens GLSL's plain ``(name, line)`` 2-tuple to also carry
    ``is_method_call`` and ``qualified`` for the C-family tree-sitter walk
    (``field_expression`` -> method calls, e.g. ``obj.m()``/``ptr->m()``;
    ``qualified_identifier`` -> ``std::sort``-shaped names, where ``qualified``
    is the full ``a::b::c`` text and ``name`` is just the last segment).

    ``materialize_call_edges`` accepts either shape in the same
    ``metadata["calls"]`` list — GLSL keeps emitting bare ``(name, line)``
    2-tuples, unchanged.
    """

    name: str
    line: int
    is_method_call: bool = False
    qualified: str | None = None


@dataclass(frozen=True)
class EdgeEmissionSpec:
    """One row: how one tree-sitter language's chunker-native edges materialize.

    Attributes:
        call_confidence: ``CallEdge.confidence`` assigned to every call edge this
            language emits. See the module docstring — this is not filtered by
            ``CallGraphConfig.min_confidence``.
        call_chunk_types: The ``CodeChunk.chunk_type`` values allowed to carry
            ``metadata["calls"]``. Narrower than Python's allowlist for languages
            (like GLSL) with no methods or decorators.
        imports_from_relationships: When True, a chunk's ``RelationshipType.IMPORTS``
            edges also populate ``CodeChunk.imports``. Scoped per-language on purpose
            — see ``materialize_relationship_edges``'s docstring for why this does
            not extend to Python by default.
    """

    call_confidence: float
    call_chunk_types: frozenset[str]
    imports_from_relationships: bool = False


EDGE_EMISSION_SPECS: dict[str, EdgeEmissionSpec] = {
    "glsl": EdgeEmissionSpec(
        call_confidence=0.9,
        call_chunk_types=frozenset({"function", "split_block"}),
        imports_from_relationships=True,
    ),
    "cpp": EdgeEmissionSpec(
        call_confidence=0.6,
        call_chunk_types=frozenset({"function", "method", "template", "split_block"}),
        imports_from_relationships=True,
    ),
    "c": EdgeEmissionSpec(
        call_confidence=0.6,
        call_chunk_types=frozenset({"function", "split_block"}),
        imports_from_relationships=True,
    ),
}


def _in_split_block_window(chunk: CodeChunk, line: int) -> bool:
    """Whether `line` falls within `chunk`'s own `[start_line, end_line]` window.

    A large GLSL function's `split_block` fragments all share the *same*
    `metadata["calls"]` / `metadata["relationships"]`: `_create_split_chunk`
    (chunking/languages/base.py) calls `extract_metadata` on the original,
    unsplit node for every fragment. Filtering by each fragment's own
    `[chunk.start_line, chunk.end_line]` here (rather than in `GLSLChunker`,
    which has no per-fragment context) is what keeps every split fragment
    from reporting the whole function's calls/relationships.

    Used by both `materialize_call_edges` and `materialize_relationship_edges` —
    previously duplicated inline in each before being hoisted into one predicate,
    then moved here from `chunking/multi_language_chunker.py`.
    """
    return chunk.start_line <= line <= chunk.end_line


def _as_call_site(entry: tuple) -> CallSite:
    """Normalize one `metadata["calls"]` entry to a `CallSite`.

    Accepts a `CallSite` NamedTuple (passed through unchanged), GLSL's plain
    `(name, line)` 2-tuple, or the C-family walk's plain
    `(name, line, is_method_call, qualified)` 4-tuple
    (`chunking/languages/_c_family.py`'s `extract_call_sites`). Neither
    language chunker imports `CallSite` itself -- see this module's docstring
    ("keeps `chunking/relationships/` out of the language chunker") -- so both
    emit plain tuples that only become `CallSite` instances here.
    `CallSite(*entry)` covers both tuple widths: trailing fields omitted from
    a 2-tuple fall back to `CallSite`'s own defaults (`is_method_call=False`,
    `qualified=None`).
    """
    if isinstance(entry, CallSite):
        return entry
    return CallSite(*entry)


def materialize_call_edges(
    chunk: CodeChunk,
    metadata: dict,
    chunk_id: str,
    spec: EdgeEmissionSpec,
) -> list[CallEdge] | None:
    """Convert a chunker's metadata["calls"] entries into CallEdge objects.

    A tree-sitter language chunker (e.g. `GLSLChunker.extract_metadata`, see
    `chunking/languages/glsl.py`) already walks call-expression nodes and filters
    builtins, type constructors, and similar noise at parse time — this just
    materializes the surviving entries into `CallEdge`s, with no re-parse and no
    `chunking/relationships/` import inside the language chunker. Each entry is
    either a plain `(name, line)` 2-tuple (GLSL) or a `CallSite` NamedTuple
    (C-family) — see `_as_call_site`.

    `metadata["calls"]` is only meaningful for the chunk types named in
    `spec.call_chunk_types` — GLSL's row narrows this to "function" and
    "split_block" since GLSL has no methods or decorators.

    See `_in_split_block_window` for why every candidate call is also filtered by
    the chunk's own line range.

    Args:
        chunk: CodeChunk being populated with call relationships. Read for
            `chunk_type`, `start_line`, `end_line` — never mutated here; the
            caller assigns the returned list to `chunk.calls`.
        metadata: The originating `TreeSitterChunk.metadata` dict.
        chunk_id: Chunk identifier, becomes CallEdge.caller_id.
        spec: This language's row from `EDGE_EMISSION_SPECS`.

    Returns:
        None when `metadata["calls"]` is absent or `chunk.chunk_type` is outside
        `spec.call_chunk_types` — signals "don't assign", distinct from an empty
        list, which signals "assign, nothing survived the line-window filter".
    """
    raw_calls = metadata.get("calls")
    if raw_calls is None or chunk.chunk_type not in spec.call_chunk_types:
        return None

    calls = [
        CallEdge(
            caller_id=chunk_id,
            callee_name=site.name,
            line_number=site.line,
            is_method_call=site.is_method_call,
            confidence=spec.call_confidence,
            callee_qualified=site.qualified,
        )
        for site in (_as_call_site(entry) for entry in raw_calls)
        if _in_split_block_window(chunk, site.line)
    ]
    if calls:
        logger.debug(f"Extracted {len(calls)} calls from {chunk_id}")
    return calls


def materialize_relationship_edges(
    chunk: CodeChunk,
    metadata: dict,
    chunk_id: str,
    spec: EdgeEmissionSpec,
) -> list[RelationshipEdge]:
    """Convert a chunker's metadata["relationships"] dicts into RelationshipEdge objects.

    Mirrors `materialize_call_edges`: a tree-sitter language chunker (e.g.
    `GLSLChunker.extract_metadata`, see `chunking/languages/glsl.py`) already walks
    the parse tree and classifies each relationship (imports, uses_type,
    instantiates, defines_field, defines_constant) at parse time — this just
    materializes the surviving plain dicts into `RelationshipEdge` objects, with no
    re-parse and no `chunking/relationships/` import inside the language chunker.

    Unlike calls, relationships can originate from several chunk types (GLSL: e.g.
    function/split_block for uses_type+instantiates, struct/union/enum for
    defines_field+uses_type, declaration/macro for defines_constant, include for
    imports) — so there is no single chunk_type allowlist here; presence of
    `metadata["relationships"]` is the only gate.

    See `_in_split_block_window` for why every candidate relationship is also
    filtered by the chunk's own line range.

    When `spec.imports_from_relationships` is set, this also populates
    `chunk.imports` from any `RelationshipType.IMPORTS` edges found — moved here
    verbatim from `MultiLanguageChunker._convert_tree_chunks`'s language check.
    GLSL's IMPORTS edges (from `#include`) are the only relationship type that
    also populates `CodeChunk.imports`; the general "imports=[] for every
    tree-sitter language" gap predates this and is left alone — flipping it on
    for every language would change `_build_file_summary`'s "# Imports:" section
    for every Python file, which needs its own before/after review, not a
    per-row one. `imports_from_relationships` is what keeps this scoped to the
    language(s) that opt in, rather than switching on for anyone else by
    accident. This is the one place this function mutates `chunk` directly — it
    reads the locally materialized `relationships` list (not `chunk.relationships`,
    which the caller has not assigned yet at this point) so the gate is exactly
    "would this call's own result populate chunk.relationships", independent of
    assignment order.

    Args:
        chunk: CodeChunk being populated with relationship edges, and — when
            `spec.imports_from_relationships` is set — with `chunk.imports`.
            Read for `start_line`, `end_line`; the caller assigns the returned
            list to `chunk.relationships` only when non-empty (see
            `materialize_relationship_edges`'s callers — `CodeChunk.relationships`
            defaults to `None`, not `[]`, so an unconditional assignment here
            would turn "nothing computed" into "computed, found nothing").
        metadata: The originating `TreeSitterChunk.metadata` dict.
        chunk_id: Chunk identifier, becomes RelationshipEdge.source_id.
        spec: This language's row from `EDGE_EMISSION_SPECS`.

    Returns:
        Always a list, possibly empty — the caller decides whether an empty
        result means "leave chunk.relationships untouched".
    """
    raw_relationships = metadata.get("relationships")
    if not raw_relationships:
        return []

    relationships: list[RelationshipEdge] = []
    for rel in raw_relationships:
        line = rel.get("line_number", 0)
        if not _in_split_block_window(chunk, line):
            continue
        try:
            relationships.append(
                RelationshipEdge(
                    source_id=chunk_id,
                    target_name=rel.get("target_name", "unknown"),
                    relationship_type=RelationshipType(
                        rel.get("relationship_type", "calls")
                    ),
                    line_number=line,
                    metadata=rel.get("metadata", {}),
                )
            )
        except (ValueError, KeyError, TypeError) as e:
            logger.debug(
                f"Skipping malformed GLSL relationship dict for {chunk_id}: {e}"
            )

    if relationships:
        logger.debug(f"Extracted {len(relationships)} relationships from {chunk_id}")

    if spec.imports_from_relationships and relationships:
        chunk.imports = [
            rel.target_name
            for rel in relationships
            if rel.relationship_type == RelationshipType.IMPORTS
        ]

    return relationships
