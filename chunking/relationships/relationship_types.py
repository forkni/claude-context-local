"""
Relationship types and edge representations for Phase 3.

This module defines the 21 relationship types used in code graph analysis
and provides a unified data structure for relationship edges.

Core Relationship Types (Priority 1-3):
- calls: Function calls another function
- inherits: Class inherits from parent class
- uses_type: Code uses type in annotation
- imports: Module imports another module/symbol
- decorates: Decorator decorates a function/class
- raises: Function raises an exception
- catches: Code catches an exception
- instantiates: Code creates instance of a class
- implements: Class implements a protocol/ABC
- overrides: Method overrides parent method
- assigns_to: Code assigns to an attribute
- reads_from: Code reads from an attribute

Entity Tracking Enhancements (Priority 4-5):
- defines_constant: Module-level constant definition
- defines_enum_member: Enum member definition
- defines_class_attr: Class attribute definition
- defines_field: Dataclass field definition
- uses_constant: References a constant
- uses_default: Default parameter value
- uses_global: global statement usage
- asserts_type: Type assertion (isinstance)
- uses_context_manager: Context manager usage

Edge Direction:
- Source (source_id): The code chunk creating the relationship
- Target (target_name): The symbol/entity being referenced

Example:
    class Child(Parent):  # inherits edge: Child -> Parent
        pass

    def foo(x: int):      # uses_type edge: foo -> int
        pass
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class RelationshipType(Enum):
    """
    Enumeration of all relationship types in Phase 3.

    Each relationship type represents a different kind of dependency
    or connection between code elements.
    """

    # Priority 1: Foundation (Week 1-2)
    CALLS = "calls"  # Function/method calls
    INHERITS = "inherits"  # Class inheritance
    USES_TYPE = "uses_type"  # Type annotation usage
    IMPORTS = "imports"  # Module/symbol imports

    # Priority 2: Core Relationships (Week 3)
    DECORATES = "decorates"  # Decorator application
    RAISES = "raises"  # Exception raising
    CATCHES = "catches"  # Exception handling
    INSTANTIATES = "instantiates"  # Object instantiation

    # Priority 3: Advanced Relationships (Week 4)
    IMPLEMENTS = "implements"  # Protocol/ABC implementation
    OVERRIDES = "overrides"  # Method overriding
    ASSIGNS_TO = "assigns_to"  # Attribute assignment
    READS_FROM = "reads_from"  # Attribute access

    # Priority 4: Constants & Definitions (Entity Tracking Enhancement)
    DEFINES_CONSTANT = "defines_constant"  # Module-level UPPER_CASE = value
    DEFINES_ENUM_MEMBER = "defines_enum_member"  # Enum.MEMBER = value
    DEFINES_CLASS_ATTR = "defines_class_attr"  # class Foo: attr = value
    DEFINES_FIELD = "defines_field"  # Dataclass field definitions

    # Priority 5: References & Usage (Entity Tracking Enhancement)
    USES_CONSTANT = "uses_constant"  # References a constant
    USES_DEFAULT = "uses_default"  # Default parameter values
    USES_GLOBAL = "uses_global"  # global x statement
    ASSERTS_TYPE = "asserts_type"  # assert isinstance(x, Type)
    USES_CONTEXT_MANAGER = "uses_context_manager"  # with X() as y:

    @classmethod
    def from_string(cls, type_str: str) -> Optional["RelationshipType"]:
        """
        Convert string to RelationshipType enum.

        Args:
            type_str: String representation of relationship type

        Returns:
            RelationshipType enum or None if not found

        Example:
            >>> RelationshipType.from_string("calls")
            <RelationshipType.CALLS: 'calls'>
        """
        try:
            return cls(type_str)
        except ValueError:
            return None

    @classmethod
    def get_priority_groups(cls) -> dict[int, list]:
        """
        Get relationship types grouped by implementation priority.

        Returns:
            Dict mapping priority level to list of relationship types

        Example:
            >>> groups = RelationshipType.get_priority_groups()
            >>> groups[1]  # Priority 1 types
            [<RelationshipType.CALLS>, <RelationshipType.INHERITS>, ...]
        """
        return {
            1: [cls.CALLS, cls.INHERITS, cls.USES_TYPE, cls.IMPORTS],
            2: [cls.DECORATES, cls.RAISES, cls.CATCHES, cls.INSTANTIATES],
            3: [cls.IMPLEMENTS, cls.OVERRIDES, cls.ASSIGNS_TO, cls.READS_FROM],
            4: [
                cls.DEFINES_CONSTANT,
                cls.DEFINES_ENUM_MEMBER,
                cls.DEFINES_CLASS_ATTR,
                cls.DEFINES_FIELD,
            ],
            5: [
                cls.USES_CONSTANT,
                cls.USES_DEFAULT,
                cls.USES_GLOBAL,
                cls.ASSERTS_TYPE,
                cls.USES_CONTEXT_MANAGER,
            ],
        }


@dataclass(slots=True)
class RelationshipEdge:
    """
    Unified representation of a relationship edge in the code graph.

    This dataclass replaces the old CallEdge and provides a consistent
    structure for all 12 relationship types.

    Attributes:
        source_id: Chunk ID of the source code element
        target_name: Name of the target symbol/entity
        relationship_type: Type of relationship (from RelationshipType enum)
        line_number: Line number where relationship occurs (default: 0)
        confidence: Confidence score 0.0-1.0 (default: 1.0)
        metadata: Additional relationship-specific data (default: empty dict)

    Examples:
        # Function call
        >>> edge = RelationshipEdge(
        ...     source_id="service.py:10-20:function:process",
        ...     target_name="validate_input",
        ...     relationship_type=RelationshipType.CALLS,
        ...     line_number=15
        ... )

        # Class inheritance
        >>> edge = RelationshipEdge(
        ...     source_id="models.py:30-50:class:Admin",
        ...     target_name="User",
        ...     relationship_type=RelationshipType.INHERITS,
        ...     line_number=30
        ... )

        # Type annotation usage
        >>> edge = RelationshipEdge(
        ...     source_id="service.py:10-20:function:process",
        ...     target_name="User",
        ...     relationship_type=RelationshipType.USES_TYPE,
        ...     line_number=10,
        ...     metadata={"annotation_location": "parameter"}
        ... )

        # Exception raising
        >>> edge = RelationshipEdge(
        ...     source_id="service.py:10-20:function:fetch_data",
        ...     target_name="NetworkError",
        ...     relationship_type=RelationshipType.RAISES,
        ...     line_number=18,
        ...     confidence=1.0
        ... )
    """

    source_id: str
    target_name: str
    relationship_type: RelationshipType
    line_number: int = 0
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate edge after initialization."""
        # Ensure confidence is in valid range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {self.confidence}")

        # Ensure relationship_type is a RelationshipType enum
        if not isinstance(self.relationship_type, RelationshipType):
            raise TypeError(
                f"relationship_type must be RelationshipType enum, "
                f"got {type(self.relationship_type)}"
            )

    def to_dict(self) -> dict[str, Any]:
        """
        Convert edge to dictionary for serialization.

        Returns:
            Dict suitable for JSON serialization or NetworkX edge attributes

        Example:
            >>> edge.to_dict()
            {
                'source_id': 'test.py:10-20:function:foo',
                'target_name': 'bar',
                'relationship_type': 'calls',
                'line_number': 15,
                'confidence': 1.0,
                'metadata': {}
            }
        """
        return {
            "source_id": self.source_id,
            "target_name": self.target_name,
            "relationship_type": self.relationship_type.value,
            "line_number": self.line_number,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RelationshipEdge":
        """
        Create RelationshipEdge from dictionary.

        Args:
            data: Dict with edge data (from to_dict() or NetworkX)

        Returns:
            RelationshipEdge instance

        Example:
            >>> data = {'source_id': 'test.py:10-20:function:foo', ...}
            >>> edge = RelationshipEdge.from_dict(data)
        """
        # Extract known fields (support both old NetworkX and new format)
        source_id = data.get("source_id", "")
        target_name = data.get("target_name", "")
        rel_type_str = data.get("relationship_type") or data.get("type", "calls")
        line_number = data.get("line_number") or data.get("line", 0)
        confidence = data.get("confidence", 1.0)

        # New format has metadata as nested dict, old format had it flattened
        if "metadata" in data and isinstance(data["metadata"], dict):
            metadata = data["metadata"]
        else:
            # Old format: everything else goes into metadata
            metadata_keys = {
                "source_id",
                "target_name",
                "type",
                "relationship_type",
                "line",
                "line_number",
                "confidence",
            }
            metadata = {k: v for k, v in data.items() if k not in metadata_keys}

        # Convert type string to enum
        rel_type = RelationshipType.from_string(rel_type_str)
        if rel_type is None:
            rel_type = RelationshipType.CALLS  # Default fallback

        return cls(
            source_id=source_id,
            target_name=target_name,
            relationship_type=rel_type,
            line_number=line_number,
            confidence=confidence,
            metadata=metadata,
        )

    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """
        Check if edge has high confidence.

        Args:
            threshold: Confidence threshold (default: 0.8)

        Returns:
            True if confidence >= threshold

        Example:
            >>> edge.confidence = 0.9
            >>> edge.is_high_confidence()
            True
        """
        return self.confidence >= threshold

    def get_context(self) -> str:
        """
        Get human-readable context information.

        Returns:
            Context string from metadata or default

        Example:
            >>> edge.metadata = {"annotation_location": "return_type"}
            >>> edge.get_context()
            'return_type'
        """
        return self.metadata.get("context", "unknown")

    def __str__(self) -> str:
        """String representation for debugging."""
        return (
            f"RelationshipEdge("
            f"{self.source_id} --[{self.relationship_type.value}]--> "
            f"{self.target_name}, line={self.line_number}, "
            f"confidence={self.confidence:.2f})"
        )

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"RelationshipEdge("
            f"source_id='{self.source_id}', "
            f"target_name='{self.target_name}', "
            f"relationship_type={self.relationship_type}, "
            f"line_number={self.line_number}, "
            f"confidence={self.confidence}, "
            f"metadata={self.metadata})"
        )


# ===== Legacy Support =====


@dataclass(slots=True)
class CallEdge:
    """
    Call relationship edge representation.

    Note: RelationshipEdge provides a more general interface for all
    relationship types. Consider using RelationshipEdge for new code.
    """

    source_id: str
    target_name: str
    line_number: int = 0
    is_method: bool = False

    def to_relationship_edge(self) -> RelationshipEdge:
        """
        Convert legacy CallEdge to RelationshipEdge.

        Returns:
            Equivalent RelationshipEdge

        Example:
            >>> call_edge = CallEdge("foo", "bar", 10, True)
            >>> rel_edge = call_edge.to_relationship_edge()
            >>> rel_edge.relationship_type
            <RelationshipType.CALLS: 'calls'>
        """
        return RelationshipEdge(
            source_id=self.source_id,
            target_name=self.target_name,
            relationship_type=RelationshipType.CALLS,
            line_number=self.line_number,
            metadata={"is_method": self.is_method},
        )


# ===== Helper Functions =====


def get_relationship_field_mapping() -> dict[str, tuple]:
    """
    Map relationship types to ImpactReport field names.

    Returns:
        Dict mapping RelationshipType value to (forward_field, reverse_field) tuples

    The forward field is used when the chunk is the source of the relationship.
    The reverse field is used when the chunk is the target of the relationship.

    Example:
        For "inherits" relationship:
        - When A inherits from B:
          - A's report shows B in "parent_classes" (forward)
          - B's report shows A in "child_classes" (reverse)

    Returns:
        {
            "calls": ("direct_callers", None),
            "inherits": ("parent_classes", "child_classes"),
            "uses_type": ("uses_types", "used_as_type_in"),
            ...
        }
    """
    return {
        "calls": ("direct_callers", None),  # Handled separately
        "inherits": ("parent_classes", "child_classes"),
        "uses_type": ("uses_types", "used_as_type_in"),
        "imports": ("imports", "imported_by"),
        "decorates": ("decorates", "decorated_by"),
        "raises": ("exceptions_raised", "exception_handlers"),
        "catches": ("exceptions_caught", None),
        "instantiates": ("instantiates", "instantiated_by"),
        "implements": ("implements_protocols", "protocol_implementations"),
        "overrides": ("overrides_methods", "overridden_by"),
        "assigns_to": ("assigned_by", None),  # Reverse lookup for attributes
        "reads_from": ("read_by", None),  # Reverse lookup for attributes
        # Entity tracking enhancements (Priority 4-5)
        "defines_constant": ("defines_constants", "constant_definitions"),
        "defines_enum_member": ("defines_enum_members", "enum_member_definitions"),
        "defines_class_attr": ("defines_class_attrs", "class_attr_definitions"),
        "defines_field": ("defines_fields", "field_definitions"),
        "uses_constant": ("uses_constants", "constant_usages"),
        "uses_default": ("uses_defaults", "default_usages"),
        "uses_global": ("uses_globals", "global_usages"),
        "asserts_type": ("asserts_types", "type_assertions"),
        "uses_context_manager": ("uses_context_managers", "context_manager_usages"),
    }


def create_call_edge(
    source_id: str, target_name: str, line_number: int = 0
) -> RelationshipEdge:
    """
    Create a "calls" relationship edge.

    Convenience function for creating the most common relationship type.

    Args:
        source_id: Chunk ID of calling function
        target_name: Name of called function
        line_number: Line number of call

    Returns:
        RelationshipEdge with type CALLS

    Example:
        >>> edge = create_call_edge("foo.py:10-20:function:foo", "bar", 15)
        >>> edge.relationship_type
        <RelationshipType.CALLS: 'calls'>
    """
    return RelationshipEdge(
        source_id=source_id,
        target_name=target_name,
        relationship_type=RelationshipType.CALLS,
        line_number=line_number,
        confidence=1.0,
    )
