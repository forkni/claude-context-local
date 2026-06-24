"""
Class attribute definition extractor.

Extracts class-level attribute definitions (not instance attributes).
This enables queries like "Where is Config.timeout used?" or "What classes
have a max_retries attribute?"

Examples:
    # Class-level attribute definitions
    class Config:
        timeout = 30              # Simple assignment
        retries: int = 3          # Annotated assignment
        debug = False

        def __init__(self):
            self.instance_attr = 1  # NOT tracked (instance attribute)
"""

import ast
from typing import Any

from chunking.relationships.relationship_extractors.base_extractor import (
    BaseRelationshipExtractor,
)
from chunking.relationships.relationship_types import RelationshipType


class ClassAttributeExtractor(BaseRelationshipExtractor):
    """
    Extract class-level attribute definitions from Python code.

    Tracks:
    - Class body assignments (class Foo: x = 1)
    - Annotated assignments (class Foo: x: int = 1)

    Does NOT track:
    - Instance attributes (self.x = 1 in __init__)
    - Method definitions
    - Nested classes
    """

    def __init__(self) -> None:
        """Initialize class attribute extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.DEFINES_CLASS_ATTR

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._extract_class_attributes(node, chunk_metadata)

    def _extract_class_attributes(
        self, node: ast.ClassDef, chunk_metadata: dict[str, Any]
    ):
        """
        Extract class body assignments (not in methods).

        Args:
            node: ClassDef AST node
            chunk_metadata: Metadata about the chunk
        """
        class_name = node.name

        for item in node.body:
            # Simple assignment: attr = value
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        self._add_edge(
                            source_id=chunk_metadata["chunk_id"],
                            target_name=f"{class_name}.{target.id}",
                            line_number=item.lineno,
                            class_name=class_name,
                            attr_name=target.id,
                        )

            # Annotated assignment: attr: Type = value
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                self._add_edge(
                    source_id=chunk_metadata["chunk_id"],
                    target_name=f"{class_name}.{item.target.id}",
                    line_number=item.lineno,
                    class_name=class_name,
                    attr_name=item.target.id,
                    has_annotation=True,
                )
