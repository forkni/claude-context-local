"""
Type Annotation Extractor

Extracts "uses_type" relationships from Python type hints.

Relationship: Function/Class -> Type used in annotation
Example: def foo(x: int) -> str  →  foo --[uses_type]--> int, str

AST Nodes Used: ast.arg.annotation, ast.FunctionDef.returns, ast.AnnAssign
Complexity: Medium (recursive type extraction from complex annotations)
"""

import ast
from typing import Any

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class TypeAnnotationExtractor(BaseRelationshipExtractor):
    """
    Extract type annotation usage relationships from Python AST.

    Detection Method:
    - Parse function/method signatures for parameter types
    - Extract return type annotations
    - Extract class attribute type hints
    - Recursively extract types from complex annotations (Generic[T], Union[A, B], etc.)

    Edge Direction:
    - Source: Function/method/class using the type
    - Target: Type being used

    Confidence Scoring:
    - 1.0: All type annotations (explicit in code)

    Example AST:
    ```python
    def process(user: User, count: int) -> Dict[str, int]:
        pass
    ```

    Creates edges:
    - process -> User (parameter)
    - process -> int (parameter)
    - process -> Dict (return type)
    - process -> str (return type, from Dict[str, int])
    - process -> int (return type, from Dict[str, int])
    """

    def __init__(self) -> None:
        """Initialize the type annotation extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.USES_TYPE
        self.current_function_id: str | None = None
        self.current_class_id: str | None = None

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract type annotation usage from code.

        Args:
            code: Source code string
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of RelationshipEdge objects for type usage
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

        # Extract type annotations
        self._extract_from_tree(tree, chunk_metadata)

        # Log results
        self._log_extraction_result(chunk_metadata)

        return self.edges

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        """
        Walk AST and extract type annotations.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        for node in ast.walk(tree):
            # Function/method type hints
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_from_function(node, chunk_metadata)

            # Class attribute type hints
            elif isinstance(node, ast.AnnAssign):
                self._extract_from_annotated_assignment(node, chunk_metadata)

    def _extract_from_function(
        self, func_node: ast.FunctionDef, chunk_metadata: dict[str, Any]
    ) -> None:
        """
        Extract type annotations from function/method definition.

        Args:
            func_node: ast.FunctionDef or ast.AsyncFunctionDef node
            chunk_metadata: Chunk metadata
        """
        # Build function chunk ID
        func_name = func_node.name
        func_chunk_id = self._build_function_chunk_id(
            chunk_metadata, func_name, func_node.lineno
        )

        # Set context for nested extractions
        old_function_id = self.current_function_id
        self.current_function_id = func_chunk_id

        # Extract parameter type hints
        for arg in func_node.args.args:
            if arg.annotation:
                self._extract_types_from_annotation(
                    arg.annotation,
                    func_chunk_id,
                    (
                        arg.annotation.lineno
                        if hasattr(arg.annotation, "lineno")
                        else func_node.lineno
                    ),
                    annotation_location="parameter",
                    parameter_name=arg.arg,
                )

        # Extract kwonly args
        for arg in func_node.args.kwonlyargs:
            if arg.annotation:
                self._extract_types_from_annotation(
                    arg.annotation,
                    func_chunk_id,
                    (
                        arg.annotation.lineno
                        if hasattr(arg.annotation, "lineno")
                        else func_node.lineno
                    ),
                    annotation_location="kwonly_parameter",
                    parameter_name=arg.arg,
                )

        # Extract return type annotation
        if func_node.returns:
            self._extract_types_from_annotation(
                func_node.returns,
                func_chunk_id,
                (
                    func_node.returns.lineno
                    if hasattr(func_node.returns, "lineno")
                    else func_node.lineno
                ),
                annotation_location="return_type",
            )

        # Restore context
        self.current_function_id = old_function_id

    def _extract_from_annotated_assignment(
        self, ann_assign_node: ast.AnnAssign, chunk_metadata: dict[str, Any]
    ) -> None:
        """
        Extract type from annotated assignment (class attribute, variable).

        Example:
            class MyClass:
                attr: int = 0  # AnnAssign

        Args:
            ann_assign_node: ast.AnnAssign node
            chunk_metadata: Chunk metadata
        """
        # Get source ID (current class or module)
        source_id = self.current_class_id or chunk_metadata.get("chunk_id")

        # Get attribute name
        if isinstance(ann_assign_node.target, ast.Name):
            attr_name = ann_assign_node.target.id
        else:
            attr_name = "unknown"

        # Extract type annotation
        if ann_assign_node.annotation:
            self._extract_types_from_annotation(
                ann_assign_node.annotation,
                source_id,
                ann_assign_node.lineno,
                annotation_location="attribute",
                attribute_name=attr_name,
            )

    def _extract_types_from_annotation(
        self, annotation_node: ast.AST, source_id: str, line_number: int, **metadata
    ) -> None:
        """
        Recursively extract all type names from a type annotation.

        Handles complex annotations like:
        - Simple: int, str, User
        - Generic: List[int], Dict[str, User]
        - Union: Union[int, str], Optional[User]
        - Nested: Dict[str, List[User]]

        Args:
            annotation_node: AST node representing the annotation
            source_id: Chunk ID of the code using this type
            line_number: Line number of annotation
            **metadata: Additional context (annotation_location, parameter_name, etc.)
        """
        type_names = self._get_all_type_names(annotation_node)

        for type_name in type_names:
            # Skip private/dunder names
            if type_name.startswith("_"):
                continue

            # Skip common typing module constructs (but NOT builtins like int, str)
            if type_name in {
                "Optional",
                "Union",
                "List",
                "Dict",
                "Set",
                "Tuple",
                "Callable",
                "Any",
                "TypeVar",
                "Generic",
                "ClassVar",
            }:
                continue

            # Create edge
            self._add_edge(
                source_id=source_id,
                target_name=type_name,
                line_number=line_number,
                confidence=1.0,
                **metadata,
            )

    def _get_all_type_names(self, node: ast.AST) -> list[str]:
        """
        Recursively extract all type names from annotation node.

        Args:
            node: AST node representing type annotation

        Returns:
            List of type names (may include duplicates)

        Example:
            Dict[str, List[User]] -> ['Dict', 'str', 'List', 'User']
        """
        type_names = []

        if isinstance(node, ast.Name):
            # Simple type: int, str, User
            type_names.append(node.id)

        elif isinstance(node, ast.Attribute):
            # Qualified type: module.User
            full_name = self._get_full_attribute_name(node)
            if full_name:
                type_names.append(full_name)

        elif isinstance(node, ast.Subscript):
            # Generic type: List[int], Dict[str, User]
            # Get base type
            base_types = self._get_all_type_names(node.value)
            type_names.extend(base_types)

            # Get type parameters
            if isinstance(node.slice, ast.Tuple):
                # Multiple parameters: Dict[str, int]
                for elt in node.slice.elts:
                    param_types = self._get_all_type_names(elt)
                    type_names.extend(param_types)
            else:
                # Single parameter: List[int]
                param_types = self._get_all_type_names(node.slice)
                type_names.extend(param_types)

        elif isinstance(node, ast.Constant):
            # String literal type hint (forward reference)
            if isinstance(node.value, str):
                type_names.append(node.value)

        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Union with | operator: int | str (Python 3.10+)
            left_types = self._get_all_type_names(node.left)
            right_types = self._get_all_type_names(node.right)
            type_names.extend(left_types)
            type_names.extend(right_types)

        return type_names

    def _get_full_attribute_name(self, attr_node: ast.Attribute) -> str | None:
        """
        Recursively extract full attribute path.

        Example:
            typing.Dict -> "typing.Dict"
            module.submodule.Class -> "module.submodule.Class"

        Args:
            attr_node: ast.Attribute node

        Returns:
            Full dotted name or None
        """
        if isinstance(attr_node.value, ast.Name):
            return f"{attr_node.value.id}.{attr_node.attr}"

        elif isinstance(attr_node.value, ast.Attribute):
            base = self._get_full_attribute_name(attr_node.value)
            if base:
                return f"{base}.{attr_node.attr}"
            return attr_node.attr

        else:
            return attr_node.attr

    def _build_function_chunk_id(
        self, chunk_metadata: dict[str, Any], func_name: str, line_number: int
    ) -> str:
        """
        Build chunk ID for a function.

        Args:
            chunk_metadata: Chunk metadata
            func_name: Function name
            line_number: Line number (unused, kept for compatibility)

        Returns:
            Chunk ID string
        """
        # Use the chunk's actual chunk_id to ensure source_id matches indexed chunk_id
        return chunk_metadata.get("chunk_id", "unknown:0-0:unknown:unknown")


# ===== Convenience Functions =====


def extract_type_usage_relationships(
    code: str, file_path: str = "unknown.py"
) -> list[RelationshipEdge]:
    """
    Convenience function to extract type annotation usage.

    Args:
        code: Python source code
        file_path: Path to file (for chunk ID)

    Returns:
        List of type usage edges

    Example:
        >>> code = '''
        ... def process(user: User, count: int) -> str:
        ...     pass
        ... '''
        >>> edges = extract_type_usage_relationships(code)
        >>> type_names = {e.target_name for e in edges}
        >>> 'User' in type_names
        True
        >>> 'int' in type_names
        True
        >>> 'str' in type_names
        True
    """
    extractor = TypeAnnotationExtractor()
    chunk_metadata = {
        "chunk_id": f"{file_path}:0-0:module:module",
        "file_path": file_path,
        "name": "module",
        "chunk_type": "module",
    }

    return extractor.extract(code, chunk_metadata)
