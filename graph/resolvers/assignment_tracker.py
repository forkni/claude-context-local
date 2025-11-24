"""
Assignment tracking for call graph extraction.

Tracks local variable assignments to infer types from constructor calls
and annotated assignments, enabling resolution of method calls on local variables.
"""

import ast
from typing import Dict, Optional

from .type_resolver import TypeResolver


class AssignmentTracker:
    """
    Tracks local variable assignments to infer types.

    Handles:
    - Constructor calls: x = MyClass()
    - Annotated assignments: x: MyClass = value
    - Named expressions: if (x := MyClass()):
    - Attribute assignments: self.handler = Handler()
    - With statement assignments: with Context() as ctx:
    """

    def __init__(self, imports: Optional[Dict[str, str]] = None):
        """
        Initialize the assignment tracker.

        Args:
            imports: Optional dict mapping imported names to qualified names
                    (for resolving aliased constructor calls)
        """
        self._imports = imports or {}
        self._type_resolver = TypeResolver()

    def set_imports(self, imports: Dict[str, str]) -> None:
        """Update the imports dictionary for alias resolution."""
        self._imports = imports

    def extract_local_assignments(self, tree: ast.AST) -> Dict[str, str]:
        """
        Extract type information from local variable assignments.

        Args:
            tree: AST tree to analyze

        Returns:
            Dictionary mapping variable names to inferred type names
        """
        assignments: Dict[str, str] = {}

        for node in ast.walk(tree):
            # Handle simple assignments: x = MyClass()
            if isinstance(node, ast.Assign):
                if isinstance(node.value, ast.Call):
                    type_name = self.infer_type_from_call(node.value)
                    if type_name:
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                # Simple variable: x = MyClass()
                                assignments[target.id] = type_name
                            elif isinstance(target, ast.Attribute):
                                # Attribute assignment: self.handler = Handler()
                                # Only track self.attr and cls.attr
                                if isinstance(target.value, ast.Name):
                                    if target.value.id in ("self", "cls"):
                                        attr_key = f"{target.value.id}.{target.attr}"
                                        assignments[attr_key] = type_name

            # Handle annotated assignments: x: MyClass = value
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    type_name = self._type_resolver.annotation_to_string(
                        node.annotation
                    )
                    if type_name:
                        assignments[node.target.id] = type_name

            # Handle named expressions (walrus operator): if (x := MyClass()):
            elif isinstance(node, ast.NamedExpr):
                if isinstance(node.value, ast.Call):
                    type_name = self.infer_type_from_call(node.value)
                    if type_name and isinstance(node.target, ast.Name):
                        assignments[node.target.id] = type_name

            # Handle with statement: with Context() as ctx:
            elif isinstance(node, ast.With):
                for item in node.items:
                    if item.optional_vars and isinstance(item.context_expr, ast.Call):
                        type_name = self.infer_type_from_call(item.context_expr)
                        if type_name and isinstance(item.optional_vars, ast.Name):
                            assignments[item.optional_vars.id] = type_name

        return assignments

    def infer_type_from_call(self, call_node: ast.Call) -> Optional[str]:
        """
        Infer type from a Call node (constructor or factory call).

        Handles:
        - Simple constructor: MyClass() -> "MyClass"
        - Qualified constructor: module.MyClass() -> "MyClass"
        - Aliased import: H() where H is alias for Handler -> "Handler"

        Args:
            call_node: AST Call node

        Returns:
            Type name or None if not inferable
        """
        func = call_node.func

        if isinstance(func, ast.Name):
            # Simple constructor: MyClass() or aliased H()
            name = func.id
            # Check if this is an imported name (possibly aliased)
            if name in self._imports:
                # Get the qualified name and extract the actual class name
                # e.g., "x.Handler" -> "Handler"
                qualified = self._imports[name]
                return qualified.split(".")[-1]
            return name

        elif isinstance(func, ast.Attribute):
            # Qualified constructor: module.MyClass() -> MyClass
            return func.attr

        # Factory method or other complex call - cannot infer
        return None
