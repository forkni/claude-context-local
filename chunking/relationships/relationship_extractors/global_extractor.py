"""
Global/nonlocal usage extractor.

Extracts `global` and `nonlocal` statement usage from function bodies.
Enables queries like "What functions mutate GLOBAL_STATE?" or "Where is
_cache declared global?".

Examples:
    # Global statement
    def increment():
        global counter
        counter += 1

    # Multiple names in one statement
    def reset():
        global counter, total
        counter = 0
        total = 0

    # Nonlocal statement (closures)
    def outer():
        x = 0
        def inner():
            nonlocal x
            x += 1
        return inner
"""

import ast
from typing import Any

from chunking.relationships.relationship_extractors.base_extractor import (
    BaseRelationshipExtractor,
)
from chunking.relationships.relationship_types import RelationshipType


class GlobalUsageExtractor(BaseRelationshipExtractor):
    """
    Extract global/nonlocal statement usage from function bodies.

    Tracks:
    - `global name` statements (module-level variable rebinding)
    - `nonlocal name` statements (enclosing-scope variable rebinding)

    Output Format:
    - Target name is the declared variable (e.g., "counter")
    - Metadata distinguishes "global" from "nonlocal" via `scope`
    """

    def __init__(self) -> None:
        """Initialize global usage extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.USES_GLOBAL

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        for node in self._walk_once(tree):
            if isinstance(node, (ast.Global, ast.Nonlocal)):
                self._extract_names(node, chunk_metadata)

    def _extract_names(
        self,
        node: ast.Global | ast.Nonlocal,
        chunk_metadata: dict[str, Any],
    ) -> None:
        """
        Extract each declared name from a global/nonlocal statement.

        Args:
            node: ast.Global or ast.Nonlocal node
            chunk_metadata: Chunk metadata
        """
        scope = "global" if isinstance(node, ast.Global) else "nonlocal"
        for name in node.names:
            self._add_edge(
                source_id=chunk_metadata["chunk_id"],
                target_name=name,
                line_number=node.lineno,
                scope=scope,
            )
