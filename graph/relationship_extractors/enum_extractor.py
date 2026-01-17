"""
Enum member definition extractor.

Extracts Enum member definitions to enable queries like "Who uses RelationshipType.CALLS?"
or "What code depends on Status.ACTIVE?".

Examples:
    # Enum definition
    class Status(Enum):
        ACTIVE = 1
        INACTIVE = 2
        PENDING = "pending"

    # Enum usage
    def check_status(user):
        if user.status == Status.ACTIVE:  # Uses Status.ACTIVE
            return True
"""

import ast
from typing import Any

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class EnumMemberExtractor(BaseRelationshipExtractor):
    """
    Extract Enum member definitions from Python code.

    Tracks:
    - Enum member definitions (Status.ACTIVE, RelationshipType.CALLS)
    - Supports Enum, IntEnum, StrEnum, Flag variants

    Output Format:
    - Target name is "ClassName.MEMBER_NAME" (e.g., "Status.ACTIVE")
    - Metadata includes enum_class and member fields for filtering
    """

    def __init__(self) -> None:
        """Initialize enum extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.DEFINES_ENUM_MEMBER

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract enum member relationships from code.

        Args:
            code: Source code string to analyze
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of RelationshipEdge objects for enum members

        Example:
            >>> extractor = EnumMemberExtractor()
            >>> code = '''
            ... from enum import Enum
            ... class Status(Enum):
            ...     ACTIVE = 1
            ...     INACTIVE = 2
            ... '''
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:2-4:class:Status"})
            >>> len(edges)
            2  # Status.ACTIVE, Status.INACTIVE
            >>> edges[0].target_name
            'Status.ACTIVE'
        """
        self._reset_state()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.logger.debug(
                f"Syntax error parsing code in {chunk_metadata.get('chunk_id', 'unknown')}"
            )
            return []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._is_enum_class(node):
                    self._extract_enum_members(node, chunk_metadata)

        self._log_extraction_result(chunk_metadata)
        return self.edges

    def _is_enum_class(self, node: ast.ClassDef) -> bool:
        """
        Check if class inherits from Enum.

        Supports:
        - Direct: class Status(Enum)
        - Module: class Status(enum.Enum)
        - Variants: IntEnum, StrEnum, Flag, IntFlag

        Args:
            node: ClassDef AST node

        Returns:
            True if class inherits from an Enum variant

        Examples:
            >>> # class Status(Enum): → True
            >>> # class Status(IntEnum): → True
            >>> # class Status(enum.Enum): → True
            >>> # class Status(BaseClass): → False
        """
        enum_types = {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"}

        for base in node.bases:
            # Direct enum: class Foo(Enum)
            if isinstance(base, ast.Name) and base.id in enum_types:
                return True

            # Module enum: class Foo(enum.Enum)
            if isinstance(base, ast.Attribute) and base.attr in enum_types:
                return True

        return False

    def _extract_enum_members(self, node: ast.ClassDef, chunk_metadata: dict[str, Any]):
        """
        Extract Enum.MEMBER definitions from enum class body.

        Processes:
        - Simple assignments: ACTIVE = 1
        - Annotated assignments: ACTIVE: int = 1
        - Enum functional API calls (future enhancement)

        Args:
            node: ClassDef AST node for enum class
            chunk_metadata: Chunk metadata
        """
        class_name = node.name

        for item in node.body:
            # Simple assignment: ACTIVE = 1
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        self._add_enum_member_edge(
                            class_name=class_name,
                            member_name=target.id,
                            line_number=item.lineno,
                            chunk_metadata=chunk_metadata,
                            has_annotation=False,
                        )

            # Annotated assignment: ACTIVE: int = 1
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                self._add_enum_member_edge(
                    class_name=class_name,
                    member_name=item.target.id,
                    line_number=item.lineno,
                    chunk_metadata=chunk_metadata,
                    has_annotation=True,
                )

    def _add_enum_member_edge(
        self,
        class_name: str,
        member_name: str,
        line_number: int,
        chunk_metadata: dict[str, Any],
        has_annotation: bool = False,
    ):
        """
        Add an enum member definition edge.

        Creates edge with target_name "ClassName.MEMBER" for easy querying.

        Args:
            class_name: Name of enum class (e.g., "Status")
            member_name: Name of member (e.g., "ACTIVE")
            line_number: Line number of definition
            chunk_metadata: Chunk metadata
            has_annotation: Whether member has type annotation
        """
        # Skip special enum attributes (metadata, not members)
        if member_name.startswith("_"):
            return

        # Target name is qualified: "Status.ACTIVE"
        qualified_name = f"{class_name}.{member_name}"

        self._add_edge(
            source_id=chunk_metadata["chunk_id"],
            target_name=qualified_name,
            line_number=line_number,
            enum_class=class_name,
            member=member_name,
            has_annotation=has_annotation,
        )
