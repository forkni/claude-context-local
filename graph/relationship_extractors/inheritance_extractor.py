"""
Inheritance Extractor

Extracts "inherits" relationships from Python code.

Relationship: Child class -> Parent class
Example: class Child(Parent): pass  →  Child --[inherits]--> Parent

AST Nodes Used: ast.ClassDef, ast.ClassDef.bases
Complexity: Low (single-pass, straightforward extraction)
"""

import ast
from typing import Any, Optional

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class InheritanceExtractor(BaseRelationshipExtractor):
    """
    Extract inheritance relationships from Python AST.

    Detection Method:
    - Parse ast.ClassDef nodes
    - Extract base class names from ClassDef.bases

    Edge Direction:
    - Source: Child class (the one inheriting)
    - Target: Parent class (the one being inherited from)

    Confidence Scoring:
    - 1.0: Direct inheritance (all cases)

    Example AST:
    ```python
    class Child(Parent):
        pass
    ```

    AST Structure:
    ```
    ClassDef(
        name='Child',
        bases=[Name(id='Parent', ctx=Load())],
        body=[...]
    )
    ```
    """

    def __init__(self) -> None:
        """Initialize the inheritance extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.INHERITS

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract inheritance relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - file_path: File path
                - name: Symbol name
                - chunk_type: Type (function/class/etc)

        Returns:
            List of RelationshipEdge objects representing inheritance

        Example:
            >>> extractor = InheritanceExtractor()
            >>> code = "class Child(Parent):\\n    pass"
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:1-2:class:Child"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'Parent'
        """
        self._reset_state()

        # Parse code
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # DEBUG: Method chunks often fail to parse standalone but parent class chunks succeed
            self.logger.debug(
                f"Failed to parse code in {chunk_metadata.get('file_path')}: {e}"
            )
            return []

        # Extract inheritance relationships
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        """
        Walk AST and extract inheritance relationships.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._extract_from_class(node, chunk_metadata)

    def _extract_from_class(
        self, class_node: ast.ClassDef, chunk_metadata: dict[str, Any]
    ) -> None:
        """
        Extract inheritance relationships from a class definition.

        Args:
            class_node: ast.ClassDef node
            chunk_metadata: Chunk metadata for source_id

        Example:
            class Child(Parent, Mixin):
                pass

            Creates two edges:
            - Child -> Parent
            - Child -> Mixin
        """
        # Get source ID (child class)
        child_class_name = class_node.name
        source_id = self._build_class_chunk_id(
            chunk_metadata, child_class_name, class_node.lineno
        )

        # Extract parent class names from bases
        for base_node in class_node.bases:
            parent_name = self._get_base_class_name(base_node)

            if not parent_name:
                continue  # Skip if we can't extract the name

            # Skip builtins and common base classes that aren't interesting
            if self._should_skip_parent(parent_name):
                continue

            # Create inheritance edge
            self._add_edge(
                source_id=source_id,
                target_name=parent_name,
                line_number=class_node.lineno,
                confidence=1.0,  # Direct inheritance is always confident
                is_multiple=len(class_node.bases) > 1,
            )

    def _get_base_class_name(self, base_node: ast.AST) -> Optional[str]:
        """
        Extract base class name from AST node.

        Handles:
        - Simple names: ast.Name -> "Parent"
        - Attributes: ast.Attribute -> "module.Parent"
        - Subscripts (generics): ast.Subscript -> "List" (extracts base, ignores type params)

        Args:
            base_node: AST node representing a base class

        Returns:
            Base class name or None if cannot be determined

        Example:
            ast.Name(id='Parent') -> "Parent"
            ast.Attribute(value=Name('module'), attr='Parent') -> "module.Parent"
            ast.Subscript(value=Name('Generic'), ...) -> "Generic"
        """
        if isinstance(base_node, ast.Name):
            # Simple name: class Child(Parent)
            return base_node.id

        elif isinstance(base_node, ast.Attribute):
            # Qualified name: class Child(module.Parent)
            return self._get_full_attribute_name(base_node)

        elif isinstance(base_node, ast.Subscript):
            # Generic base: class Child(Generic[T])
            # Extract the base type (ignore type parameters)
            return self._get_base_class_name(base_node.value)

        elif isinstance(base_node, ast.Call):
            # Metaclass call: class Child(metaclass=Meta)
            # We extract the function name
            return self._get_base_class_name(base_node.func)

        # Unknown node type
        self.logger.debug(f"Unknown base class node type: {type(base_node)}")
        return None

    def _get_full_attribute_name(self, attr_node: ast.Attribute) -> str:
        """
        Recursively extract full attribute path.

        Example:
            ast.Attribute(value=Attribute(value=Name('a'), attr='b'), attr='c')
            -> "a.b.c"

        Args:
            attr_node: ast.Attribute node

        Returns:
            Full dotted name
        """
        if isinstance(attr_node.value, ast.Name):
            return f"{attr_node.value.id}.{attr_node.attr}"

        elif isinstance(attr_node.value, ast.Attribute):
            # Recursive case
            base = self._get_full_attribute_name(attr_node.value)
            return f"{base}.{attr_node.attr}"

        else:
            # Fallback: just return the attribute name
            return attr_node.attr

    def _should_skip_parent(self, parent_name: str) -> bool:
        """
        Check if parent class should be skipped.

        Skip:
        - Builtins (object, Exception, etc.)
        - Generic marker classes (Generic, Protocol)
        - Private classes (starting with _)

        Args:
            parent_name: Name of parent class

        Returns:
            True if should skip this parent
        """
        # Extract just the class name (not module path)
        class_name = parent_name.split(".")[-1]

        # Skip common base classes that aren't interesting
        uninteresting_bases = {
            "object",  # Default base class (implicit)
            "type",  # Metaclass
            "Generic",  # typing.Generic
            "Protocol",  # typing.Protocol (handled by protocol extractor)
            "ABC",  # abc.ABC (handled by protocol extractor)
            # Note: We DO track list, dict, Exception, etc. as they're useful base classes
        }

        if class_name in uninteresting_bases:
            return True

        # Skip private/dunder classes
        if class_name.startswith("_"):
            return True

        return False

    def _build_class_chunk_id(
        self, chunk_metadata: dict[str, Any], class_name: str, line_number: int
    ) -> str:
        """
        Build chunk ID for a class.

        Args:
            chunk_metadata: Chunk metadata
            class_name: Name of the class (unused, kept for compatibility)
            line_number: Line number (unused, kept for compatibility)

        Returns:
            Chunk ID string

        Example:
            "test.py:10-30:class:Child"
        """
        # Use the chunk's actual chunk_id to ensure source_id matches indexed chunk_id
        return chunk_metadata.get("chunk_id", "unknown:0-0:unknown:unknown")


# ===== Convenience Functions =====


def extract_inheritance_relationships(
    code: str, file_path: str = "unknown.py"
) -> list[RelationshipEdge]:
    """
    Convenience function to extract inheritance relationships.

    Args:
        code: Python source code
        file_path: Path to file (for chunk ID)

    Returns:
        List of inheritance edges

    Example:
        >>> code = '''
        ... class Parent:
        ...     pass
        ...
        ... class Child(Parent):
        ...     pass
        ... '''
        >>> edges = extract_inheritance_relationships(code)
        >>> len(edges)
        1
        >>> edges[0].target_name
        'Parent'
    """
    extractor = InheritanceExtractor()
    chunk_metadata = {
        "chunk_id": f"{file_path}:0-0:module:module",
        "file_path": file_path,
        "name": "module",
        "chunk_type": "module",
    }

    return extractor.extract(code, chunk_metadata)
