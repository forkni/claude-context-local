"""
Override Extractor

Extracts "overrides" relationships from Python code.

Relationship: Child method -> Parent method
Example: class Child(Parent):
             def foo(self):  # Override
                 super().foo()
         →  Child.foo --[overrides]--> Parent.foo

AST Nodes Used: ast.ClassDef, ast.FunctionDef, ast.Call, ast.Attribute
Detection Strategy:
1. Methods with @override decorator (Python 3.12+)
2. Methods containing super().method_name() calls

Complexity: Medium (requires parent class resolution)
"""

import ast
from typing import Any, Dict, List

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class OverrideExtractor(BaseRelationshipExtractor):
    """
    Extract method override relationships from Python AST.

    Detection Methods:
    1. @override decorator (Python 3.12+):
       - Explicit override marker
       - Confidence: 1.0

    2. super().method_name() calls:
       - Calls to parent methods via super()
       - Confidence: 1.0 (direct evidence of override)

    Edge Direction:
    - Source: Child method (the one overriding)
    - Target: Parent method name (inferred from super() call or decorator)

    Confidence Scoring:
    - 1.0: @override decorator or super().method() call
    - 0.9: Method matches parent class method name (future enhancement)

    Example AST:
    ```python
    class Child(Parent):
        @override
        def process(self):
            super().process()
    ```

    AST Structure:
    ```
    ClassDef(
        name='Child',
        bases=[Name(id='Parent')],
        body=[
            FunctionDef(
                name='process',
                decorator_list=[Name(id='override')],
                body=[
                    Expr(Call(
                        func=Attribute(
                            value=Call(func=Name(id='super')),
                            attr='process'
                        )
                    ))
                ]
            )
        ]
    )
    ```
    """

    def __init__(self):
        """Initialize the override extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.OVERRIDES

    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        """
        Extract override relationships from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - file_path: File path
                - name: Symbol name (method name)
                - chunk_type: Type (should be "method" or "class")

        Returns:
            List of RelationshipEdge objects representing overrides

        Example:
            >>> extractor = OverrideExtractor()
            >>> code = '''
            ... class Child(Parent):
            ...     def foo(self):
            ...         super().foo()
            ... '''
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:2-4:method:Child.foo"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'foo'
        """
        self._reset_state()

        # Parse code
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Method chunks often fail to parse standalone
            self.logger.debug(
                f"Failed to parse code in {chunk_metadata.get('file_path')}: {e}"
            )
            return []

        # Extract override relationships
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: Dict[str, Any]) -> None:
        """
        Walk AST and extract override relationships.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                self._extract_from_class(node, chunk_metadata)

    def _extract_from_class(
        self, class_node: ast.ClassDef, chunk_metadata: Dict[str, Any]
    ) -> None:
        """
        Extract override relationships from a class definition.

        Args:
            class_node: ast.ClassDef node
            chunk_metadata: Chunk metadata for source_id

        Example:
            class Child(Parent):
                @override
                def process(self):
                    super().process()

            Creates override edge: Child.process -> process
        """
        # Only process if class has base classes (inheritance)
        if not class_node.bases:
            return

        class_name = class_node.name

        # Find all methods in the class
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                self._extract_from_method(node, class_name, chunk_metadata)

    def _extract_from_method(
        self,
        method_node: ast.FunctionDef,
        class_name: str,
        chunk_metadata: Dict[str, Any],
    ) -> None:
        """
        Extract override relationships from a method definition.

        Args:
            method_node: ast.FunctionDef node
            class_name: Name of the containing class
            chunk_metadata: Chunk metadata

        Detection:
        1. Check for @override decorator
        2. Check for super().method_name() calls in method body
        """
        method_name = method_node.name

        # Skip private methods (usually not overrides)
        if method_name.startswith("_") and not method_name.startswith("__"):
            return

        # Build source chunk ID (child method)
        source_id = self._build_method_chunk_id(
            chunk_metadata, class_name, method_name, method_node.lineno
        )

        # Check 1: @override decorator (Python 3.12+)
        if self._has_override_decorator(method_node):
            self._add_edge(
                source_id=source_id,
                target_name=method_name,
                line_number=method_node.lineno,
                confidence=1.0,
                detection_method="override_decorator",
            )
            return  # No need to check further

        # Check 2: super().method_name() calls
        super_methods = self._find_super_calls(method_node)
        for super_method_name, line_num in super_methods:
            self._add_edge(
                source_id=source_id,
                target_name=super_method_name,
                line_number=line_num,
                confidence=1.0,
                detection_method="super_call",
            )

    def _has_override_decorator(self, method_node: ast.FunctionDef) -> bool:
        """
        Check if method has @override decorator.

        Args:
            method_node: ast.FunctionDef node

        Returns:
            True if method has @override decorator

        Example:
            @override
            def foo(self): pass  # Returns True
        """
        for decorator in method_node.decorator_list:
            # Simple name: @override
            if isinstance(decorator, ast.Name) and decorator.id == "override":
                return True

            # Qualified name: @typing.override
            if isinstance(decorator, ast.Attribute) and decorator.attr == "override":
                return True

        return False

    def _find_super_calls(self, method_node: ast.FunctionDef) -> List[tuple[str, int]]:
        """
        Find all super().method_name() calls in method body.

        Args:
            method_node: ast.FunctionDef node

        Returns:
            List of (method_name, line_number) tuples for super() calls

        Example:
            def foo(self):
                super().bar()  # Returns [("bar", line_num)]
                super().baz(x) # Returns [("bar", line_num1), ("baz", line_num2)]
        """
        super_calls = []

        for node in ast.walk(method_node):
            if not isinstance(node, ast.Call):
                continue

            # Check if call is super().method_name()
            if isinstance(node.func, ast.Attribute):
                # Check if the value is a super() call
                if isinstance(node.func.value, ast.Call):
                    if isinstance(node.func.value.func, ast.Name):
                        if node.func.value.func.id == "super":
                            # Found super().method_name()
                            method_name = node.func.attr
                            line_number = node.lineno
                            super_calls.append((method_name, line_number))

        return super_calls

    def _build_method_chunk_id(
        self,
        chunk_metadata: Dict[str, Any],
        class_name: str,
        method_name: str,
        line_number: int,
    ) -> str:
        """
        Build chunk ID for a method.

        For methods, use qualified name: ClassName.method_name

        Args:
            chunk_metadata: Chunk metadata
            class_name: Name of containing class
            method_name: Name of the method
            line_number: Line number (unused, kept for compatibility)

        Returns:
            Chunk ID string

        Example:
            "test.py:10-30:method:Child.process"
        """
        # Use the chunk's actual chunk_id to ensure source_id matches indexed chunk_id
        chunk_id = chunk_metadata.get("chunk_id", "unknown:0-0:unknown:unknown")

        # If chunk is already a method, use it directly
        if ":method:" in chunk_id:
            return chunk_id

        # Otherwise, build qualified method name
        file_path = chunk_metadata.get("file_path", "unknown.py")
        return f"{file_path}:{line_number}:method:{class_name}.{method_name}"


# ===== Convenience Functions =====


def extract_override_relationships(
    code: str, file_path: str = "unknown.py"
) -> List[RelationshipEdge]:
    """
    Convenience function to extract override relationships.

    Args:
        code: Python source code
        file_path: Path to file (for chunk ID)

    Returns:
        List of override edges

    Example:
        >>> code = '''
        ... class Parent:
        ...     def foo(self):
        ...         pass
        ...
        ... class Child(Parent):
        ...     def foo(self):
        ...         super().foo()
        ... '''
        >>> edges = extract_override_relationships(code)
        >>> len(edges)
        1
        >>> edges[0].target_name
        'foo'
    """
    extractor = OverrideExtractor()
    chunk_metadata = {
        "chunk_id": f"{file_path}:0-0:module:module",
        "file_path": file_path,
        "name": "module",
        "chunk_type": "module",
    }

    return extractor.extract(code, chunk_metadata)
