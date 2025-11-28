"""
Exception Extractor

Extracts "raises" and "catches" relationships from Python code.

Relationships:
- raises: Function -> Exception class (for raise statements)
- catches: Function -> Exception class (for except handlers)

Example: raise ValueError("error")  →  func --[raises]--> ValueError
         except TypeError:          →  func --[catches]--> TypeError

AST Nodes Used: ast.Raise, ast.Try, ast.ExceptHandler
Complexity: Medium (handles two relationship types)
"""

import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class ExceptionExtractor(BaseRelationshipExtractor):
    """
    Extract exception raising and catching relationships from Python AST.

    Detection Method:
    - Parse ast.Raise nodes for exceptions raised
    - Parse ast.Try -> ast.ExceptHandler for exceptions caught

    Edge Direction:
    - Source: Function/code that raises or catches
    - Target: Exception class name

    Confidence Scoring:
    - 1.0: All cases (explicit exception names)

    Supported Patterns:
    - raise ValueError("error")
    - raise CustomError()
    - raise module.Error()
    - except ValueError:
    - except (TypeError, KeyError):
    - except module.Error as e:

    Example AST (raise):
    ```python
    raise ValueError("error")
    ```

    AST Structure:
    ```
    Raise(
        exc=Call(
            func=Name(id='ValueError', ctx=Load()),
            args=[Constant(value='error')]
        )
    )
    ```

    Example AST (except):
    ```python
    try:
        ...
    except ValueError:
        ...
    ```

    AST Structure:
    ```
    Try(
        body=[...],
        handlers=[
            ExceptHandler(
                type=Name(id='ValueError', ctx=Load()),
                name=None,
                body=[...]
            )
        ]
    )
    ```
    """

    def __init__(self):
        """Initialize the exception extractor."""
        super().__init__()
        # This extractor handles both RAISES and CATCHES
        # relationship_type is set dynamically during extraction
        self.relationship_type = None

    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        """
        Extract exception relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - file_path: File path
                - name: Symbol name
                - chunk_type: Type (function/class/etc)

        Returns:
            List of RelationshipEdge objects representing raises/catches

        Example:
            >>> extractor = ExceptionExtractor()
            >>> code = "raise ValueError('error')"
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:1-1:function:func"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'ValueError'
            >>> edges[0].relationship_type
            <RelationshipType.RAISES: 'raises'>
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

        # Extract exception relationships
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        if self.edges:
            raises_count = sum(
                1 for e in self.edges if e.relationship_type == RelationshipType.RAISES
            )
            catches_count = sum(
                1 for e in self.edges if e.relationship_type == RelationshipType.CATCHES
            )
            chunk_id = chunk_metadata.get("chunk_id", "unknown")
            self.logger.debug(
                f"Extracted {raises_count} raises, {catches_count} catches from {chunk_id}"
            )

        return self.edges

    def _extract_from_tree(self, tree, chunk_metadata: Dict[str, Any]):
        """
        Extract exceptions from AST tree.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        chunk_id = chunk_metadata.get("chunk_id", "")

        for node in ast.walk(tree):
            if isinstance(node, ast.Raise):
                self._extract_raise(node, chunk_id)
            elif isinstance(node, ast.Try):
                self._extract_except_handlers(node, chunk_id)

    def _extract_raise(self, node: ast.Raise, chunk_id: str):
        """
        Extract exception from a raise statement.

        Args:
            node: ast.Raise node
            chunk_id: Source chunk ID
        """
        if node.exc is None:
            return  # bare raise - re-raises current exception

        exception_name = self._get_exception_name(node.exc)
        if exception_name:
            # Set relationship type for this edge
            self.relationship_type = RelationshipType.RAISES
            self._add_edge(
                source_id=chunk_id,
                target_name=exception_name,
                line_number=node.lineno,
                confidence=1.0,
            )

    def _extract_except_handlers(self, node: ast.Try, chunk_id: str):
        """
        Extract exceptions from except handlers.

        Args:
            node: ast.Try node
            chunk_id: Source chunk ID
        """
        for handler in node.handlers:
            if handler.type is None:
                continue  # bare except: - catches all

            exception_names = self._get_handler_exception_names(handler.type)
            for exc_name in exception_names:
                # Set relationship type for this edge
                self.relationship_type = RelationshipType.CATCHES
                self._add_edge(
                    source_id=chunk_id,
                    target_name=exc_name,
                    line_number=handler.lineno,
                    confidence=1.0,
                )

    def _get_exception_name(self, exc_node) -> str:
        """
        Get the name of a raised exception.

        Handles:
        - raise ValueError (ast.Name) -> "ValueError"
        - raise ValueError() (ast.Call) -> "ValueError"
        - raise module.Error (ast.Attribute) -> "module.Error"
        - raise module.Error() (ast.Call with ast.Attribute)

        Args:
            exc_node: AST node representing the exception

        Returns:
            Exception name as string, or empty string if extraction fails
        """
        if isinstance(exc_node, ast.Name):
            return exc_node.id
        elif isinstance(exc_node, ast.Call):
            return self._get_exception_name(exc_node.func)
        elif isinstance(exc_node, ast.Attribute):
            return self._get_full_attribute_name(exc_node)
        return ""

    def _get_handler_exception_names(self, type_node) -> List[str]:
        """
        Get exception names from an except handler.

        Handles:
        - except Error (ast.Name) -> ["Error"]
        - except (Error1, Error2) (ast.Tuple) -> ["Error1", "Error2"]
        - except module.Error (ast.Attribute) -> ["module.Error"]

        Args:
            type_node: AST node representing the exception type(s)

        Returns:
            List of exception names
        """
        if isinstance(type_node, ast.Name):
            return [type_node.id]
        elif isinstance(type_node, ast.Tuple):
            names = []
            for elt in type_node.elts:
                if isinstance(elt, ast.Name):
                    names.append(elt.id)
                elif isinstance(elt, ast.Attribute):
                    names.append(self._get_full_attribute_name(elt))
            return names
        elif isinstance(type_node, ast.Attribute):
            return [self._get_full_attribute_name(type_node)]
        return []

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """
        Get the full dotted name from an Attribute node.

        Args:
            node: ast.Attribute node

        Returns:
            Full dotted name (e.g., "module.CustomError")
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))


# For testing
if __name__ == "__main__":
    extractor = ExceptionExtractor()

    test_code = """
def function_with_exceptions():
    try:
        if condition:
            raise ValueError("invalid value")
        if other_condition:
            raise custom.CustomError("custom error")
    except ValueError as e:
        print("value error")
    except (TypeError, KeyError):
        print("type or key error")
    except custom.AnotherError:
        print("another error")
"""

    edges = extractor.extract(
        test_code,
        {
            "chunk_id": "test.py:1-15:function:function_with_exceptions",
            "file_path": "test.py",
        },
    )

    print(f"Found {len(edges)} exception relationships:")
    for edge in edges:
        print(
            f"  {edge.source_id} --[{edge.relationship_type.value}]--> {edge.target_name}"
        )
