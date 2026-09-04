"""
Unit tests for the data-driven relationship extractor registry.

Tests:
- build_relationship_extractors() entity-tracking gating
- ExtractorSpec name uniqueness
- ImportExtractor receives the relation_filter from ExtractorContext
- Every mapped relationship type has a producing extractor (guard test)
- Every GLSL relationship-type string is a valid RelationshipType value
"""

from chunking.relationships.relationship_extractors.import_extractor import (
    ImportExtractor,
)
from chunking.relationships.relationship_extractors.registry import (
    RELATIONSHIP_EXTRACTORS,
    ExtractorContext,
    build_relationship_extractors,
)
from chunking.relationships.relationship_types import (
    RelationshipType,
    get_relationship_field_mapping,
)


# Source exercising every relationship type in get_relationship_field_mapping()
# except "calls" (produced by the call-graph pipeline, not an AST extractor) and
# the 8 TouchDesigner network types (ADR-0062 -- produced by TDNetworkChunker
# building RelationshipEdge objects directly from a .tdgraph.json snapshot, not
# by an AST extractor walking Python source).
# See test_extractor_roster_covers_every_mapped_relationship_type below.
_FIXTURE_SOURCE = '''
import os
from typing import Optional, Protocol
from enum import Enum

MAX_RETRIES = 30


class Status(Enum):
    ACTIVE = 1
    INACTIVE = 2


class MyProto(Protocol):
    def log(self, msg: str) -> None: ...


class BaseHandler:
    """Base handler with a hookable process method."""

    def process(self):
        pass


class Handler(BaseHandler):
    """Handler exercising most relationship types."""

    timeout: int = MAX_RETRIES
    debug = False

    @custom_decorator
    def process(self, value: str, count: int = MAX_RETRIES) -> Optional[str]:
        global _state
        _state = value
        super().process()
        assert isinstance(value, BaseHandler)
        with open("ignored.txt") as fh:
            pass
        with Resource() as r:
            pass
        try:
            raise ValueError("bad")
        except TypeError:
            pass
        obj = Widget()
        return obj


@dataclass
class Config:
    name: str
    retries: int = MAX_RETRIES
'''


def test_build_without_entity_tracking_returns_eleven():
    ctx = ExtractorContext(relation_filter=None)
    extractors = build_relationship_extractors(ctx, enable_entity_tracking=False)
    assert len(extractors) == 11


def test_build_with_entity_tracking_returns_sixteen():
    ctx = ExtractorContext(relation_filter=None)
    extractors = build_relationship_extractors(ctx, enable_entity_tracking=True)
    assert len(extractors) == 16


def test_extractor_spec_names_are_unique():
    names = [spec.name for spec in RELATIONSHIP_EXTRACTORS]
    assert len(names) == len(set(names))


def test_import_extractor_receives_relation_filter_from_context():
    sentinel = object()
    ctx = ExtractorContext(relation_filter=sentinel)
    extractors = build_relationship_extractors(ctx, enable_entity_tracking=False)
    import_extractors = [e for e in extractors if isinstance(e, ImportExtractor)]
    assert len(import_extractors) == 1
    assert import_extractors[0].relation_filter is sentinel


def test_extractor_roster_covers_every_mapped_relationship_type():
    """Every relationship type in get_relationship_field_mapping() (except
    "calls", produced by the call-graph pipeline, and the 8 TouchDesigner
    network types, produced by TDNetworkChunker -- neither is an AST
    extractor) must be producible by at least one registered extractor.

    Guards against the 2026-08-03 dead-relationship-type gap: four
    RelationshipType members (ASSERTS_TYPE, USES_GLOBAL, ASSIGNS_TO,
    READS_FROM) were listed in the field mapping / MCP filter vocabulary with
    no extractor anywhere ever emitting them, leaving six ImpactReport fields
    permanently empty. ASSERTS_TYPE/USES_GLOBAL got real extractors;
    ASSIGNS_TO/READS_FROM were pruned from the mapping instead (see the note
    in relationship_types.py). This test is behavioral, not a static
    attribute check, because ExceptionExtractor sets
    ``self.relationship_type = None`` and overrides it per-edge (RAISES vs
    CATCHES) -- reading the attribute statically would miss both.

    Runs each extractor's `.extract()` directly against one fixture source
    rather than the full chunk/index pipeline used by slow_integration's
    ``test_relationship_extraction_integration.py`` -- fast enough for every
    commit.
    """
    ctx = ExtractorContext(relation_filter=None)
    extractors = build_relationship_extractors(ctx, enable_entity_tracking=True)

    chunk_metadata = {
        "chunk_id": "fixture.py:1-999:module_preamble:module",
        "file_path": "fixture.py",
        "name": "module",
        "chunk_type": "module_preamble",
    }

    produced_types = set()
    for extractor in extractors:
        for edge in extractor.extract(_FIXTURE_SOURCE, chunk_metadata):
            produced_types.add(edge.relationship_type.value)

    # TouchDesigner network relationships (ADR-0062, Part C): built directly as
    # RelationshipEdge objects by TDNetworkChunker from a .tdgraph.json
    # snapshot -- there is no Python-source AST for them to come from, so they
    # can never appear in produced_types here. Same shape as "calls".
    td_network_types = {
        "wires_to",
        "docked_to",
        "contains",
        "references_op",
        "binds_to",
        "exports_to",
        "scripted_by",
        "shares_tag",
    }
    mapped_types = set(get_relationship_field_mapping()) - {"calls"} - td_network_types
    missing = mapped_types - produced_types
    assert not missing, (
        f"No extractor produced these mapped relationship types: {missing}. "
        "Either add an extractor that emits them, or remove the mapping "
        "entry (see the ASSIGNS_TO/READS_FROM precedent in "
        "relationship_types.py)."
    )


def test_glsl_relationship_strings_are_valid_relationship_types():
    """Every string literal GLSLChunker's `_add_relationship` (chunking/languages/glsl.py)
    passes as `rel_type` must round-trip through `RelationshipType(...)`.

    `materialize_relationship_edges` (chunking/relationships/edge_specs.py)
    builds edges from these strings dynamically via
    `RelationshipType(rel.get("relationship_type", "calls"))`, wrapped in a
    swallowed `except (ValueError, KeyError, TypeError)` that only
    `logger.debug`s and silently drops the edge. A typo in a GLSL
    `_add_relationship` call site would fail this way with no visible error --
    this test catches that at the string-literal level instead.

    This enumerates the five known GLSL relationship-type strings only, not the
    full Python AST extractor roster covered by
    test_extractor_roster_covers_every_mapped_relationship_type above. GLSL's
    five types are a strict subset of what the Python extractors emit, so this
    assertion cannot false-fail because of the GLSL surface.
    """
    glsl_relationship_strings = {
        "instantiates",
        "uses_type",
        "defines_field",
        "defines_constant",
        "imports",
    }
    for rel_type_str in glsl_relationship_strings:
        # Raises ValueError if rel_type_str is not a valid RelationshipType value.
        RelationshipType(rel_type_str)
