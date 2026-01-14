"""
Instantiation Extractor

Extracts "instantiates" relationships from Python code.

Relationship: Function/code -> Class being instantiated
Example: obj = MyClass()  →  func --[instantiates]--> MyClass

AST Nodes Used: ast.Call
Complexity: Medium (uses heuristic to distinguish classes from functions)

Heuristic: Calls to names starting with uppercase letter are treated as
class instantiations. This may produce false positives for functions with
CamelCase names.
"""

import ast
from typing import Any

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class InstantiationExtractor(BaseRelationshipExtractor):
    """
    Extract class instantiation relationships from Python AST.

    Detection Method:
    - Parse ast.Call nodes
    - Use heuristic: names starting with uppercase are class instantiations

    Edge Direction:
    - Source: Code that instantiates
    - Target: Class being instantiated

    Confidence Scoring:
    - 0.8: Heuristic-based detection (may have false positives)

    Heuristic Details:
    - Name starts with uppercase: likely a class
    - Name is all uppercase: likely a constant (skipped)
    - Name starts with lowercase: likely a function (skipped)

    Supported Patterns:
    - obj = MyClass()
    - result = SomeFactory.create()
    - data = module.DataClass(arg)

    Example AST:
    ```python
    obj = MyClass()
    ```

    AST Structure:
    ```
    Assign(
        targets=[Name(id='obj', ctx=Store())],
        value=Call(
            func=Name(id='MyClass', ctx=Load()),
            args=[]
        )
    )
    ```

    Known Limitations:
    - May capture CamelCase functions as classes (e.g., `CreateWidget()`)
    - May capture NamedTuple instances
    - Does not analyze import statements to verify class types
    """

    def __init__(self) -> None:
        """Initialize the instantiation extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.INSTANTIATES

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract instantiation relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - file_path: File path
                - name: Symbol name
                - chunk_type: Type (function/class/etc)

        Returns:
            List of RelationshipEdge objects representing instantiations

        Example:
            >>> extractor = InstantiationExtractor()
            >>> code = "obj = MyClass()"
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:1-1:function:func"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'MyClass'
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

        # Extract instantiation relationships
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree, chunk_metadata: dict[str, Any]):
        """
        Extract instantiations from AST tree.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        chunk_id = chunk_metadata.get("chunk_id", "")

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                self._extract_instantiation(node, chunk_id)

    def _extract_instantiation(self, node: ast.Call, chunk_id: str):
        """
        Extract class instantiation from a Call node.

        Uses heuristic: class names start with uppercase letter.

        Args:
            node: ast.Call node
            chunk_id: Source chunk ID
        """
        call_name = self._get_call_name(node.func)
        if not call_name:
            return

        # Extract just the final name for checking (e.g., "module.MyClass" -> "MyClass")
        final_name = call_name.split(".")[-1]

        if not final_name:
            return

        # Heuristic checks:
        # 1. Skip if it's all uppercase (likely a constant like LOGGER())
        # 2. Skip if it doesn't start with uppercase (likely a function)
        # 3. Accept if starts with uppercase but not all uppercase (likely a class)

        if final_name[0].isupper() and not final_name.isupper():
            # Skip common builtins that look like classes
            if self._should_skip_class(final_name):
                return

            self._add_edge(
                source_id=chunk_id,
                target_name=call_name,
                line_number=node.lineno,
                confidence=0.8,  # Lower confidence due to heuristic
            )

    def _get_call_name(self, func_node) -> str:
        """
        Get the name of the called function/class.

        Handles:
        - MyClass() (ast.Name) -> "MyClass"
        - module.MyClass() (ast.Attribute) -> "module.MyClass"

        Args:
            func_node: AST node representing the function/class being called

        Returns:
            Full name as string, or empty string if extraction fails
        """
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return self._get_full_attribute_name(func_node)
        return ""

    def _get_full_attribute_name(self, node: ast.Attribute) -> str:
        """
        Get the full dotted name from an Attribute node.

        Args:
            node: ast.Attribute node

        Returns:
            Full dotted name (e.g., "module.MyClass")
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    def _should_skip_class(self, class_name: str) -> bool:
        """
        Check if a class name should be skipped.

        Skips builtin types and common patterns that aren't useful to track.

        Args:
            class_name: Name of the class (without module prefix)

        Returns:
            True if class should be skipped
        """
        # Common builtins and types to skip
        skip_classes = {
            # Builtin types
            "Exception",
            "BaseException",
            "StopIteration",
            "GeneratorExit",
            "KeyboardInterrupt",
            "SystemExit",
            # Common standard library classes
            "Path",
            "PurePath",
            "PosixPath",
            "WindowsPath",
            # Typing constructs (often called like classes)
            "Optional",
            "Union",
            "List",
            "Dict",
            "Set",
            "Tuple",
            "Type",
            "Callable",
            "Any",
            "TypeVar",
            "Generic",
            "Protocol",
            # Testing
            "Mock",
            "MagicMock",
            "AsyncMock",
        }

        return class_name in skip_classes


# For testing
if __name__ == "__main__":
    extractor = InstantiationExtractor()

    test_code = """
def function_with_instantiations():
    # Class instantiations
    obj = MyClass()
    result = SomeFactory()
    data = module.DataClass(arg)
    nested = outer.inner.DeepClass()

    # Should be skipped (lowercase - likely functions)
    value = some_function()
    result = get_data()

    # Should be skipped (all uppercase - likely constants)
    LOGGER()
    CONFIG()

    # Should be captured
    handler = ErrorHandler()
    client = HttpClient()
"""

    edges = extractor.extract(
        test_code,
        {
            "chunk_id": "test.py:1-20:function:function_with_instantiations",
            "file_path": "test.py",
        },
    )

    print(f"Found {len(edges)} instantiation relationships:")
    for edge in edges:
        print(
            f"  {edge.source_id} --[{edge.relationship_type.value}]--> {edge.target_name} (confidence: {edge.confidence})"
        )
