"""
Unit tests for graph/relationship_types.py

Tests:
- RelationshipType enum functionality
- RelationshipEdge dataclass
- Edge serialization/deserialization
- Helper functions
"""

import pytest

from graph.relationship_types import (
    CallEdge,
    RelationshipEdge,
    RelationshipType,
    create_call_edge,
    get_relationship_field_mapping,
)

# ===== RelationshipType Enum Tests =====


def test_relationship_type_enum_values():
    """Test that all 21 relationship types are defined."""
    expected_types = {
        # Priority 1: Foundation
        "calls",
        "inherits",
        "uses_type",
        "imports",
        # Priority 2: Core Relationships
        "decorates",
        "raises",
        "catches",
        "instantiates",
        # Priority 3: Advanced Relationships
        "implements",
        "overrides",
        "assigns_to",
        "reads_from",
        # Priority 4: Constants & Definitions (Entity Tracking)
        "defines_constant",
        "defines_enum_member",
        "defines_class_attr",
        "defines_field",
        # Priority 5: References & Usage (Entity Tracking)
        "uses_constant",
        "uses_default",
        "uses_global",
        "asserts_type",
        "uses_context_manager",
    }

    actual_types = {rt.value for rt in RelationshipType}

    assert (
        actual_types == expected_types
    ), f"Missing or extra types. Expected {expected_types}, got {actual_types}"


def test_relationship_type_from_string():
    """Test converting string to RelationshipType enum."""
    # Valid string
    result = RelationshipType.from_string("calls")
    assert result == RelationshipType.CALLS

    # Another valid string
    result = RelationshipType.from_string("inherits")
    assert result == RelationshipType.INHERITS

    # Invalid string
    result = RelationshipType.from_string("invalid_type")
    assert result is None


def test_relationship_type_priority_groups():
    """Test priority groups are correctly defined."""
    groups = RelationshipType.get_priority_groups()

    # Check structure
    assert 1 in groups
    assert 2 in groups
    assert 3 in groups

    # Check Priority 1 (4 types)
    priority1 = groups[1]
    assert len(priority1) == 4
    assert RelationshipType.CALLS in priority1
    assert RelationshipType.INHERITS in priority1
    assert RelationshipType.USES_TYPE in priority1
    assert RelationshipType.IMPORTS in priority1

    # Check Priority 2 (4 types)
    priority2 = groups[2]
    assert len(priority2) == 4
    assert RelationshipType.DECORATES in priority2
    assert RelationshipType.RAISES in priority2
    assert RelationshipType.CATCHES in priority2
    assert RelationshipType.INSTANTIATES in priority2

    # Check Priority 3 (4 types)
    priority3 = groups[3]
    assert len(priority3) == 4
    assert RelationshipType.IMPLEMENTS in priority3
    assert RelationshipType.OVERRIDES in priority3
    assert RelationshipType.ASSIGNS_TO in priority3
    assert RelationshipType.READS_FROM in priority3


# ===== RelationshipEdge Dataclass Tests =====


def test_relationship_edge_initialization():
    """Test basic RelationshipEdge initialization."""
    edge = RelationshipEdge(
        source_id="test.py:10-20:function:foo",
        target_name="bar",
        relationship_type=RelationshipType.CALLS,
        line_number=15,
    )

    assert edge.source_id == "test.py:10-20:function:foo"
    assert edge.target_name == "bar"
    assert edge.relationship_type == RelationshipType.CALLS
    assert edge.line_number == 15
    assert edge.confidence == 1.0  # Default
    assert edge.metadata == {}  # Default


def test_relationship_edge_with_metadata():
    """Test RelationshipEdge with metadata."""
    edge = RelationshipEdge(
        source_id="test.py:10-20:function:foo",
        target_name="User",
        relationship_type=RelationshipType.USES_TYPE,
        line_number=10,
        confidence=0.9,
        metadata={"annotation_location": "parameter", "index": 0},
    )

    assert edge.confidence == 0.9
    assert edge.metadata["annotation_location"] == "parameter"
    assert edge.metadata["index"] == 0


def test_relationship_edge_validation():
    """Test that RelationshipEdge validates inputs."""
    # Invalid confidence (too high)
    with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
        RelationshipEdge(
            source_id="test",
            target_name="test",
            relationship_type=RelationshipType.CALLS,
            confidence=1.5,
        )

    # Invalid confidence (negative)
    with pytest.raises(ValueError, match="Confidence must be 0.0-1.0"):
        RelationshipEdge(
            source_id="test",
            target_name="test",
            relationship_type=RelationshipType.CALLS,
            confidence=-0.1,
        )

    # Invalid relationship_type (not enum)
    with pytest.raises(TypeError, match="must be RelationshipType enum"):
        RelationshipEdge(
            source_id="test",
            target_name="test",
            relationship_type="calls",  # Should be RelationshipType.CALLS
        )


def test_relationship_edge_to_dict():
    """Test serialization to dictionary."""
    edge = RelationshipEdge(
        source_id="test.py:10-20:function:foo",
        target_name="bar",
        relationship_type=RelationshipType.INHERITS,
        line_number=15,
        confidence=0.85,
        metadata={"context": "base_class"},
    )

    result = edge.to_dict()

    # Check structure
    assert result["source_id"] == "test.py:10-20:function:foo"
    assert result["target_name"] == "bar"
    assert result["relationship_type"] == "inherits"  # Enum converted to string
    assert result["line_number"] == 15
    assert result["confidence"] == 0.85

    # Metadata should be nested
    assert result["metadata"] == {"context": "base_class"}


def test_relationship_edge_from_dict():
    """Test deserialization from dictionary."""
    data = {
        "source_id": "test.py:10-20:function:foo",
        "target_name": "bar",
        "type": "calls",
        "line": 15,
        "confidence": 0.9,
        "context": "function_call",
    }

    edge = RelationshipEdge.from_dict(data)

    assert edge.source_id == "test.py:10-20:function:foo"
    assert edge.target_name == "bar"
    assert edge.relationship_type == RelationshipType.CALLS
    assert edge.line_number == 15
    assert edge.confidence == 0.9
    assert edge.metadata["context"] == "function_call"


def test_relationship_edge_roundtrip():
    """Test that to_dict() and from_dict() are inverses."""
    original = RelationshipEdge(
        source_id="test.py:10-20:class:Child",
        target_name="Parent",
        relationship_type=RelationshipType.INHERITS,
        line_number=10,
        confidence=1.0,
        metadata={"is_multiple": False},
    )

    # Convert to dict and back
    data = original.to_dict()
    restored = RelationshipEdge.from_dict(data)

    # Check all fields match
    assert restored.source_id == original.source_id
    assert restored.target_name == original.target_name
    assert restored.relationship_type == original.relationship_type
    assert restored.line_number == original.line_number
    assert restored.confidence == original.confidence
    assert restored.metadata == original.metadata


def test_relationship_edge_is_high_confidence():
    """Test confidence checking method."""
    # High confidence
    edge = RelationshipEdge(
        source_id="test",
        target_name="test",
        relationship_type=RelationshipType.CALLS,
        confidence=0.9,
    )
    assert edge.is_high_confidence() is True
    assert edge.is_high_confidence(threshold=0.85) is True
    assert edge.is_high_confidence(threshold=0.95) is False

    # Low confidence
    edge.confidence = 0.5
    assert edge.is_high_confidence() is False
    assert edge.is_high_confidence(threshold=0.4) is True


def test_relationship_edge_get_context():
    """Test context extraction method."""
    # With context in metadata
    edge = RelationshipEdge(
        source_id="test",
        target_name="test",
        relationship_type=RelationshipType.USES_TYPE,
        metadata={"context": "return_type"},
    )
    assert edge.get_context() == "return_type"

    # Without context in metadata
    edge = RelationshipEdge(
        source_id="test", target_name="test", relationship_type=RelationshipType.CALLS
    )
    assert edge.get_context() == "unknown"


def test_relationship_edge_str_repr():
    """Test string representations."""
    edge = RelationshipEdge(
        source_id="test.py:10-20:function:foo",
        target_name="bar",
        relationship_type=RelationshipType.CALLS,
        line_number=15,
        confidence=0.95,
    )

    # __str__ for user-friendly output
    str_repr = str(edge)
    assert "test.py:10-20:function:foo" in str_repr
    assert "calls" in str_repr
    assert "bar" in str_repr
    assert "15" in str_repr
    assert "0.95" in str_repr

    # __repr__ for debugging
    repr_str = repr(edge)
    assert "RelationshipEdge" in repr_str
    assert "source_id=" in repr_str
    assert "target_name=" in repr_str


# ===== Legacy CallEdge Tests =====


def test_call_edge_to_relationship_edge():
    """Test legacy CallEdge conversion to RelationshipEdge."""
    call_edge = CallEdge(
        source_id="test.py:10-20:function:foo",
        target_name="bar",
        line_number=15,
        is_method=True,
    )

    rel_edge = call_edge.to_relationship_edge()

    assert rel_edge.source_id == "test.py:10-20:function:foo"
    assert rel_edge.target_name == "bar"
    assert rel_edge.relationship_type == RelationshipType.CALLS
    assert rel_edge.line_number == 15
    assert rel_edge.metadata["is_method"] is True


# ===== Helper Function Tests =====


def test_get_relationship_field_mapping():
    """Test relationship field mapping for ImpactReport."""
    mapping = get_relationship_field_mapping()

    # Check structure
    assert isinstance(mapping, dict)
    assert len(mapping) == 21

    # Check specific mappings
    assert mapping["inherits"] == ("parent_classes", "child_classes")
    assert mapping["uses_type"] == ("uses_types", "used_as_type_in")
    assert mapping["calls"] == ("direct_callers", None)
    assert mapping["raises"] == ("exceptions_raised", "exception_handlers")

    # Check all relationship types are covered
    for rel_type in RelationshipType:
        assert rel_type.value in mapping


def test_create_call_edge_convenience():
    """Test convenience function for creating call edges."""
    edge = create_call_edge("test.py:10-20:function:foo", "bar", 15)

    assert edge.source_id == "test.py:10-20:function:foo"
    assert edge.target_name == "bar"
    assert edge.relationship_type == RelationshipType.CALLS
    assert edge.line_number == 15
    assert edge.confidence == 1.0


# ===== Edge Cases =====


def test_relationship_edge_empty_metadata():
    """Test that empty metadata works correctly."""
    edge = RelationshipEdge(
        source_id="test", target_name="test", relationship_type=RelationshipType.CALLS
    )

    # to_dict() should not include metadata keys
    result = edge.to_dict()
    assert "context" not in result  # Metadata was empty


def test_relationship_edge_boundary_confidence():
    """Test confidence at boundaries."""
    # Exactly 0.0
    edge = RelationshipEdge(
        source_id="test",
        target_name="test",
        relationship_type=RelationshipType.INSTANTIATES,
        confidence=0.0,
    )
    assert edge.confidence == 0.0

    # Exactly 1.0
    edge = RelationshipEdge(
        source_id="test",
        target_name="test",
        relationship_type=RelationshipType.CALLS,
        confidence=1.0,
    )
    assert edge.confidence == 1.0


def test_relationship_edge_from_dict_missing_fields():
    """Test from_dict() with missing optional fields."""
    # Minimal data
    data = {"type": "calls", "source_id": "test", "target_name": "foo"}

    edge = RelationshipEdge.from_dict(data)

    assert edge.source_id == "test"
    assert edge.target_name == "foo"
    assert edge.relationship_type == RelationshipType.CALLS
    assert edge.line_number == 0  # Default
    assert edge.confidence == 1.0  # Default
    assert edge.metadata == {}  # Empty


def test_relationship_edge_from_dict_unknown_type():
    """Test from_dict() with unknown relationship type."""
    data = {"type": "unknown_type", "source_id": "test", "target_name": "foo"}

    edge = RelationshipEdge.from_dict(data)

    # Should default to CALLS
    assert edge.relationship_type == RelationshipType.CALLS
