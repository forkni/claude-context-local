"""
Decorator Extractor

Extracts "decorates" relationships from Python code.

Relationship: Decorated function/class -> Decorator
Example: @decorator
         def func(): pass  →  func --[decorates]--> decorator

AST Nodes Used: ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef
Complexity: Low (single-pass, straightforward extraction)
"""

import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class DecoratorExtractor(BaseRelationshipExtractor):
    """
    Extract decorator application relationships from Python AST.

    Detection Method:
    - Parse ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef nodes
    - Extract decorator names from decorator_list attribute

    Edge Direction:
    - Source: Decorated function/class (the one being decorated)
    - Target: Decorator (the decorator being applied)

    Confidence Scoring:
    - 1.0: Direct decorator application (all cases)

    Supported Decorator Forms:
    - @decorator (ast.Name)
    - @module.decorator (ast.Attribute)
    - @decorator(args) (ast.Call)
    - @module.decorator(args) (ast.Call with ast.Attribute)

    Example AST:
    ```python
    @decorator
    def func():
        pass
    ```

    AST Structure:
    ```
    FunctionDef(
        name='func',
        decorator_list=[Name(id='decorator', ctx=Load())],
        body=[...]
    )
    ```
    """

    def __init__(self):
        """Initialize the decorator extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.DECORATES

    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        """
        Extract decorator relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - file_path: File path
                - name: Symbol name
                - chunk_type: Type (function/class/etc)

        Returns:
            List of RelationshipEdge objects representing decorator usage

        Example:
            >>> extractor = DecoratorExtractor()
            >>> code = "@decorator\\ndef func():\\n    pass"
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:1-3:function:func"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'decorator'
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

        # Extract decorator relationships
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree, chunk_metadata: Dict[str, Any]):
        """
        Extract decorators from AST tree.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        chunk_id = chunk_metadata.get("chunk_id", "")

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in node.decorator_list:
                    decorator_name = self._get_decorator_name(decorator)
                    if decorator_name:
                        # Skip builtins like property, staticmethod, classmethod
                        # These are so common they add noise without value
                        if self._should_skip_decorator(decorator_name):
                            continue

                        self._add_edge(
                            source_id=chunk_id,
                            target_name=decorator_name,
                            line_number=decorator.lineno,
                            confidence=1.0,
                        )

    def _get_decorator_name(self, decorator_node) -> str:
        """
        Get the full name of a decorator.

        Handles:
        - @decorator (ast.Name) -> "decorator"
        - @module.decorator (ast.Attribute) -> "module.decorator"
        - @decorator(args) (ast.Call) -> "decorator"
        - @module.submodule.decorator (nested ast.Attribute)

        Args:
            decorator_node: AST node representing the decorator

        Returns:
            Full decorator name as string, or empty string if extraction fails
        """
        if isinstance(decorator_node, ast.Name):
            return decorator_node.id
        elif isinstance(decorator_node, ast.Attribute):
            return self._get_full_attribute_name(decorator_node)
        elif isinstance(decorator_node, ast.Call):
            # For calls like @decorator(args), get the function being called
            return self._get_decorator_name(decorator_node.func)
        return ""

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """
        Get the full dotted name from an Attribute node.

        Handles nested attributes like a.b.c.d

        Args:
            node: ast.Attribute node

        Returns:
            Full dotted name (e.g., "module.submodule.decorator")
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _should_skip_decorator(self, decorator_name: str) -> bool:
        """
        Check if a decorator should be skipped.

        Skips common builtins that add noise without providing useful
        relationship information.

        Args:
            decorator_name: Name of the decorator

        Returns:
            True if decorator should be skipped
        """
        # Common decorators that are typically not useful to track
        skip_decorators = {
            "property",
            "staticmethod",
            "classmethod",
            "abstractmethod",
            "abstractproperty",
            "overload",
            # functools
            "functools.wraps",
            "functools.cache",
            "functools.lru_cache",
            "functools.cached_property",
        }

        # Check both full name and just the final part
        final_name = decorator_name.split(".")[-1]

        return decorator_name in skip_decorators or final_name in {
            "property",
            "staticmethod",
            "classmethod",
            "abstractmethod",
            "abstractproperty",
        }


# For testing
if __name__ == "__main__":
    extractor = DecoratorExtractor()

    test_code = """
@decorator
def simple_decorated():
    pass

@module.decorator
def module_decorated():
    pass

@decorator(arg=value)
def decorated_with_args():
    pass

@dataclass
class MyDataClass:
    x: int
    y: str

@pytest.fixture
def my_fixture():
    return 42
"""

    edges = extractor.extract(
        test_code, {"chunk_id": "test.py:1-20:module", "file_path": "test.py"}
    )

    print(f"Found {len(edges)} decorator relationships:")
    for edge in edges:
        print(
            f"  {edge.source_id} --[{edge.relationship_type.value}]--> {edge.target_name}"
        )
