"""
Type assertion extractor.

Extracts `isinstance()`/`issubclass()` type assertions from `assert`
statements. Enables queries like "Where is Config asserted at runtime?" or
"What functions narrow x to Handler?".

Examples:
    # Single type
    assert isinstance(x, Handler)

    # Tuple of types
    assert isinstance(x, (Handler, FallbackHandler))

    # Qualified type
    assert isinstance(x, module.Handler)

    # issubclass
    assert issubclass(cls, BaseHandler)

    # Builtin types are skipped (too common, no signal)
    assert isinstance(x, str)  # Not tracked
"""

import ast
from typing import Any

from chunking.relationships.name_resolution import dotted_name
from chunking.relationships.relationship_extractors.base_extractor import (
    BaseRelationshipExtractor,
)
from chunking.relationships.relationship_types import RelationshipType


# Assertion functions this extractor tracks.
_ASSERTION_FUNCS = frozenset({"isinstance", "issubclass"})


class TypeAssertionExtractor(BaseRelationshipExtractor):
    """
    Extract isinstance()/issubclass() type assertions from assert statements.

    Tracks:
    - `assert isinstance(x, Type)` and `assert issubclass(x, Type)`
    - Tuple-of-types form: `assert isinstance(x, (A, B))`
    - Qualified types: `assert isinstance(x, module.Type)`

    Filtering Rules:
    - Excludes builtin types (str, int, dict, ...) — no signal
    - Only recognizes bare `isinstance`/`issubclass` calls, not aliased or
      qualified forms (e.g. `builtins.isinstance`)

    Output Format:
    - Target name is the asserted type (e.g., "Handler")
    - Metadata includes the assertion function name for context
    """

    def __init__(self) -> None:
        """Initialize type assertion extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.ASSERTS_TYPE

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        for node in self._walk_once(tree):
            if isinstance(node, ast.Assert):
                self._extract_assertion(node, chunk_metadata)

    def _extract_assertion(
        self, node: ast.Assert, chunk_metadata: dict[str, Any]
    ) -> None:
        """
        Extract asserted types from a single assert statement.

        Args:
            node: ast.Assert node
            chunk_metadata: Chunk metadata
        """
        test = node.test
        if not isinstance(test, ast.Call) or not isinstance(test.func, ast.Name):
            return
        func_name = test.func.id
        if func_name not in _ASSERTION_FUNCS or len(test.args) < 2:
            return

        type_arg = test.args[1]
        for type_name in self._extract_type_names(type_arg):
            if not self._is_builtin(type_name):
                self._add_edge(
                    source_id=chunk_metadata["chunk_id"],
                    target_name=type_name,
                    line_number=node.lineno,
                    assertion_func=func_name,
                )

    @staticmethod
    def _extract_type_names(node: ast.expr) -> list[str]:
        """
        Extract type names from the second argument of isinstance/issubclass.

        Handles:
        - Single type: Handler -> ["Handler"]
        - Qualified type: module.Handler -> ["module.Handler"]
        - Tuple of types: (A, B) -> ["A", "B"]

        Args:
            node: AST node for the type argument

        Returns:
            List of type names found
        """
        if isinstance(node, ast.Tuple):
            names = []
            for elt in node.elts:
                name = dotted_name(elt)
                if name:
                    names.append(name)
            return names

        name = dotted_name(node)
        return [name] if name else []
