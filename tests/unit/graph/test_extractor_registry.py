"""
Unit tests for the data-driven relationship extractor registry.

Tests:
- build_relationship_extractors() entity-tracking gating
- ExtractorSpec name uniqueness
- ImportExtractor receives the relation_filter from ExtractorContext
"""

from chunking.relationships.relationship_extractors.import_extractor import (
    ImportExtractor,
)
from chunking.relationships.relationship_extractors.registry import (
    RELATIONSHIP_EXTRACTORS,
    ExtractorContext,
    build_relationship_extractors,
)


def test_build_without_entity_tracking_returns_eleven():
    ctx = ExtractorContext(relation_filter=None)
    extractors = build_relationship_extractors(ctx, enable_entity_tracking=False)
    assert len(extractors) == 11


def test_build_with_entity_tracking_returns_fourteen():
    ctx = ExtractorContext(relation_filter=None)
    extractors = build_relationship_extractors(ctx, enable_entity_tracking=True)
    assert len(extractors) == 14


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
