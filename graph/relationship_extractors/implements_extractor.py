"""
Implements Extractor

Extracts "implements" relationships from Python code.

Relationship: Implementation class -> Protocol/ABC
Example: class Handler(LoggingProtocol):
             def log(self, msg: str): pass
         →  Handler --[implements]--> LoggingProtocol

AST Nodes Used: ast.ClassDef, ast.ClassDef.bases
Detection Strategy:
1. Classes inheriting from typing.Protocol
2. Classes inheriting from abc.ABC or abc.ABCMeta
3. Classes inheriting from collections.abc abstract base classes

Complexity: Low (similar to inheritance extraction with filtering)
"""

import ast
from typing import Any

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class ImplementsExtractor(BaseRelationshipExtractor):
    """
    Extract protocol/ABC implementation relationships from Python AST.

    Detection Method:
    - Parse ast.ClassDef nodes
    - Check if base classes are protocols or ABCs
    - Filter using known protocol/ABC markers

    Edge Direction:
    - Source: Implementation class (the one implementing)
    - Target: Protocol/ABC class (the interface being implemented)

    Confidence Scoring:
    - 1.0: Explicit Protocol/ABC inheritance

    Recognized Patterns:
    1. typing.Protocol:
       - class Foo(Protocol): pass
       - from typing import Protocol

    2. abc.ABC:
       - class Foo(ABC): pass
       - from abc import ABC, ABCMeta

    3. collections.abc:
       - class Foo(Iterable): pass
       - from collections.abc import Iterable

    Example AST:
    ```python
    from typing import Protocol

    class LoggingProtocol(Protocol):
        def log(self, msg: str) -> None: ...

    class FileHandler(LoggingProtocol):
        def log(self, msg: str) -> None:
            print(msg)
    ```

    AST Structure:
    ```
    ClassDef(
        name='FileHandler',
        bases=[Name(id='LoggingProtocol', ctx=Load())],
        body=[...]
    )
    ```
    """

    # Known protocol/ABC markers (base class names)
    PROTOCOL_MARKERS: set[str] = {
        "Protocol",  # typing.Protocol
        "ABC",  # abc.ABC
        "ABCMeta",  # abc.ABCMeta
        # collections.abc abstract base classes
        "Callable",
        "Iterable",
        "Iterator",
        "Mapping",
        "MutableMapping",
        "Sequence",
        "MutableSequence",
        "Set",
        "MutableSet",
        "Container",
        "Collection",
        "Sized",
        "Hashable",
        # Additional typing protocols (Python 3.8+)
        "SupportsAbs",
        "SupportsBytes",
        "SupportsComplex",
        "SupportsFloat",
        "SupportsIndex",
        "SupportsInt",
        "SupportsRound",
    }

    def __init__(self) -> None:
        """Initialize the implements extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.IMPLEMENTS

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract implementation relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - file_path: File path
                - name: Symbol name (class name)
                - chunk_type: Type (should be "class")

        Returns:
            List of RelationshipEdge objects representing protocol implementations

        Example:
            >>> extractor = ImplementsExtractor()
            >>> code = '''
            ... from typing import Protocol
            ... class MyProtocol(Protocol):
            ...     def foo(self): pass
            ... class Implementation(MyProtocol):
            ...     def foo(self): pass
            ... '''
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:5-7:class:Implementation"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'MyProtocol'
        """
        self._reset_state()

        # Parse code
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.logger.debug(
                f"Failed to parse code in {chunk_metadata.get('file_path')}: {e}"
            )
            return []

        # Extract implementation relationships
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        """
        Walk AST and extract implementation relationships.

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
        Extract implementation relationships from a class definition.

        Args:
            class_node: ast.ClassDef node
            chunk_metadata: Chunk metadata for source_id

        Example:
            class Handler(LoggingProtocol, ABC):
                pass

            Creates two edges:
            - Handler -> LoggingProtocol (if LoggingProtocol is a protocol)
            - Handler -> ABC
        """
        # Only process if class has base classes
        if not class_node.bases:
            return

        # Get source ID (implementation class)
        impl_class_name = class_node.name
        source_id = self._build_class_chunk_id(
            chunk_metadata, impl_class_name, class_node.lineno
        )

        # Extract protocol/ABC base classes
        for base_node in class_node.bases:
            protocol_name = self._get_base_class_name(base_node)

            if not protocol_name:
                continue  # Skip if we can't extract the name

            # Check if this is a protocol/ABC
            if self._is_protocol_or_abc(protocol_name):
                # Create implementation edge
                self._add_edge(
                    source_id=source_id,
                    target_name=protocol_name,
                    line_number=class_node.lineno,
                    confidence=1.0,
                    is_protocol=self._is_protocol_marker(protocol_name),
                    is_abc=self._is_abc_marker(protocol_name),
                )

    def _get_base_class_name(self, base_node: ast.AST) -> str | None:
        """
        Extract base class name from AST node.

        Handles:
        - Simple names: ast.Name -> "Protocol"
        - Attributes: ast.Attribute -> "typing.Protocol"
        - Subscripts: ast.Subscript -> "Protocol" (for Protocol[T])

        Args:
            base_node: AST node representing a base class

        Returns:
            Base class name or None if cannot be determined

        Example:
            ast.Name(id='Protocol') -> "Protocol"
            ast.Attribute(value=Name('typing'), attr='Protocol') -> "Protocol"
        """
        if isinstance(base_node, ast.Name):
            # Simple name: class Foo(Protocol)
            return base_node.id

        elif isinstance(base_node, ast.Attribute):
            # Qualified name: class Foo(typing.Protocol)
            # Extract just the class name (not module path)
            return base_node.attr

        elif isinstance(base_node, ast.Subscript):
            # Generic protocol: class Foo(Protocol[T])
            # Extract the base type (ignore type parameters)
            return self._get_base_class_name(base_node.value)

        elif isinstance(base_node, ast.Call):
            # Metaclass: class Foo(metaclass=ABCMeta)
            # Extract the function name
            return self._get_base_class_name(base_node.func)

        # Unknown node type
        return None

    def _is_protocol_or_abc(self, class_name: str) -> bool:
        """
        Check if class name represents a protocol or ABC.

        Args:
            class_name: Name of the base class (without module path)

        Returns:
            True if class is a protocol/ABC marker

        Example:
            "Protocol" -> True
            "ABC" -> True
            "Iterable" -> True
            "MyClass" -> False
        """
        # Extract just the class name (handle module.ClassName)
        base_name = class_name.split(".")[-1]
        return base_name in self.PROTOCOL_MARKERS

    def _is_protocol_marker(self, class_name: str) -> bool:
        """
        Check if class is specifically a Protocol (not ABC).

        Args:
            class_name: Name of the base class

        Returns:
            True if class is Protocol

        Example:
            "Protocol" -> True
            "ABC" -> False
        """
        base_name = class_name.split(".")[-1]
        return base_name == "Protocol"

    def _is_abc_marker(self, class_name: str) -> bool:
        """
        Check if class is specifically an ABC (not Protocol).

        Args:
            class_name: Name of the base class

        Returns:
            True if class is ABC/ABCMeta

        Example:
            "ABC" -> True
            "ABCMeta" -> True
            "Protocol" -> False
        """
        base_name = class_name.split(".")[-1]
        return base_name in {"ABC", "ABCMeta"}

    def _build_class_chunk_id(
        self, chunk_metadata: dict[str, Any], class_name: str, line_number: int
    ) -> str:
        """
        Build chunk ID for a class.

        Args:
            chunk_metadata: Chunk metadata
            class_name: Name of the class
            line_number: Line number

        Returns:
            Chunk ID string

        Example:
            "test.py:10-30:class:Handler"
        """
        # Use the chunk's actual chunk_id to ensure source_id matches indexed chunk_id
        return chunk_metadata.get("chunk_id", "unknown:0-0:unknown:unknown")


# ===== Convenience Functions =====


def extract_implementation_relationships(
    code: str, file_path: str = "unknown.py"
) -> list[RelationshipEdge]:
    """
    Convenience function to extract implementation relationships.

    Args:
        code: Python source code
        file_path: Path to file (for chunk ID)

    Returns:
        List of implementation edges

    Example:
        >>> code = '''
        ... from typing import Protocol
        ...
        ... class LoggingProtocol(Protocol):
        ...     def log(self, msg: str): ...
        ...
        ... class FileHandler(LoggingProtocol):
        ...     def log(self, msg: str):
        ...         print(msg)
        ... '''
        >>> edges = extract_implementation_relationships(code)
        >>> len(edges)
        1
        >>> edges[0].target_name
        'LoggingProtocol'
    """
    extractor = ImplementsExtractor()
    chunk_metadata = {
        "chunk_id": f"{file_path}:0-0:module:module",
        "file_path": file_path,
        "name": "module",
        "chunk_type": "module",
    }

    return extractor.extract(code, chunk_metadata)
