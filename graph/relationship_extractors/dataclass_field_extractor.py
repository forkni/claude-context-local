"""
Dataclass field definition extractor.

Extracts field definitions from @dataclass decorated classes.
This enables queries like "What uses SearchResult.score?" or "Where is
EmbeddingResult.embedding_vector defined?"

Examples:
    # Dataclass field definitions
    @dataclass
    class User:
        name: str               # Required field
        age: int = 0            # Field with default
        email: str = field(default="")  # Using field()
"""

import ast
from typing import Any

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class DataclassFieldExtractor(BaseRelationshipExtractor):
    """
    Extract dataclass field definitions from Python code.

    Tracks:
    - Fields in @dataclass decorated classes
    - Both annotated fields (name: str) and with defaults (age: int = 0)

    Filtering Rules:
    - Only classes with @dataclass decorator
    - Only annotated assignments in class body (field requires annotation)
    """

    def __init__(self) -> None:
        """Initialize dataclass field extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.DEFINES_FIELD

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract dataclass field relationships from code.

        Args:
            code: Source code string to analyze
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - chunk_type: Type of chunk

        Returns:
            List of RelationshipEdge objects for dataclass field relationships
        """
        self._reset_state()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.logger.debug(
                f"Syntax error parsing code in {chunk_metadata.get('chunk_id', 'unknown')}"
            )
            return []

        # Walk the tree to find class definitions
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._has_dataclass_decorator(node):
                    self._extract_dataclass_fields(node, chunk_metadata)

        self._log_extraction_result(chunk_metadata)
        return self.edges

    def _has_dataclass_decorator(self, node: ast.ClassDef) -> bool:
        """
        Check if class has @dataclass decorator.

        Args:
            node: ClassDef AST node

        Returns:
            True if class has @dataclass decorator
        """
        for decorator in node.decorator_list:
            # @dataclass
            if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
                return True
            # @dataclass(...)
            if isinstance(decorator, ast.Call):
                if (
                    isinstance(decorator.func, ast.Name)
                    and decorator.func.id == "dataclass"
                ):
                    return True
            # @dataclasses.dataclass
            if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
                return True
        return False

    def _extract_dataclass_fields(
        self, node: ast.ClassDef, chunk_metadata: dict[str, Any]
    ):
        """
        Extract dataclass field definitions.

        Args:
            node: ClassDef AST node
            chunk_metadata: Metadata about the chunk
        """
        class_name = node.name

        for item in node.body:
            # Dataclass fields are annotated assignments
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                has_default = item.value is not None

                self._add_edge(
                    source_id=chunk_metadata["chunk_id"],
                    target_name=f"{class_name}.{field_name}",
                    line_number=item.lineno,
                    class_name=class_name,
                    field_name=field_name,
                    has_default=has_default,
                )
