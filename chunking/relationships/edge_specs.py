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

from dataclasses import dataclass


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
            — see ``multi_language_chunker.py``'s switch-3 comment for why this does
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
}
