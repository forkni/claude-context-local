"""
Type annotation resolution for call graph extraction.

Extracts and resolves type annotations from Python function parameters
to enable accurate method call resolution (e.g., param.method() -> Type.method).
"""

import ast


class TypeResolver:
    """
    Resolves type annotations from Python function definitions.

    Handles:
    - Simple types: MyClass
    - Qualified types: module.MyClass (returns MyClass)
    - Generic types: Optional[X], List[X], Union[X, Y]
    - Forward references: "MyClass"
    """

    def extract_type_annotations(self, func_node: ast.FunctionDef) -> dict[str, str]:
        """
        Extract parameter type annotations from a function definition.

        Args:
            func_node: AST FunctionDef or AsyncFunctionDef node

        Returns:
            Dictionary mapping parameter names to type names
        """
        annotations = {}

        # Extract from positional arguments
        for arg in func_node.args.args:
            if arg.annotation:
                type_name = self.annotation_to_string(arg.annotation)
                if type_name:
                    annotations[arg.arg] = type_name

        # Extract from keyword-only arguments
        for arg in func_node.args.kwonlyargs:
            if arg.annotation:
                type_name = self.annotation_to_string(arg.annotation)
                if type_name:
                    annotations[arg.arg] = type_name

        # Extract from positional-only arguments (Python 3.8+)
        for arg in func_node.args.posonlyargs:
            if arg.annotation:
                type_name = self.annotation_to_string(arg.annotation)
                if type_name:
                    annotations[arg.arg] = type_name

        # Extract from *args
        if func_node.args.vararg and func_node.args.vararg.annotation:
            type_name = self.annotation_to_string(func_node.args.vararg.annotation)
            if type_name:
                annotations[func_node.args.vararg.arg] = type_name

        # Extract from **kwargs
        if func_node.args.kwarg and func_node.args.kwarg.annotation:
            type_name = self.annotation_to_string(func_node.args.kwarg.annotation)
            if type_name:
                annotations[func_node.args.kwarg.arg] = type_name

        return annotations

    def annotation_to_string(self, annotation: ast.AST) -> str | None:
        """
        Convert an AST annotation node to a string type name.

        Handles:
        - Simple names: MyClass
        - Attributes: module.MyClass (returns MyClass)
        - Subscripts: Optional[MyClass], List[MyClass] (returns MyClass)
        - Constants: "MyClass" (forward references)

        Args:
            annotation: AST node representing a type annotation

        Returns:
            Type name string or None if not resolvable
        """
        if isinstance(annotation, ast.Name):
            # Simple type: MyClass
            return annotation.id

        elif isinstance(annotation, ast.Attribute):
            # Qualified type: module.MyClass -> MyClass
            # We return just the class name for resolution
            return annotation.attr

        elif isinstance(annotation, ast.Subscript):
            # Generic type: Optional[X], List[X], Union[X, Y]
            if isinstance(annotation.value, ast.Name):
                container = annotation.value.id

                # Extract inner type from container types
                if container in (
                    "Optional",
                    "List",
                    "Set",
                    "Tuple",
                    "Sequence",
                    "Iterable",
                    "Iterator",
                    "Collection",
                    "Type",
                ):
                    return self.annotation_to_string(annotation.slice)

                # Handle Union - try to get first non-None type
                if container == "Union":
                    if isinstance(annotation.slice, ast.Tuple):
                        for elt in annotation.slice.elts:
                            # Skip None type
                            if isinstance(elt, ast.Constant) and elt.value is None:
                                continue
                            if isinstance(elt, ast.Name) and elt.id == "None":
                                continue
                            result = self.annotation_to_string(elt)
                            if result:
                                return result
                    else:
                        return self.annotation_to_string(annotation.slice)

            # Unresolvable generic (Dict, Callable, etc.)
            return None

        elif isinstance(annotation, ast.Constant):
            # Forward reference: "MyClass"
            if isinstance(annotation.value, str):
                # Extract class name from string (handle "module.Class")
                return annotation.value.split(".")[-1]
            return None

        # Unresolvable annotation type
        return None
