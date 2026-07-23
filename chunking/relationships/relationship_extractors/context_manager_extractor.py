"""
Context manager usage extractor.

Extracts context manager usage from `with` statements.
This enables queries like "Where is Progress() used as context manager?" or
"What functions use atomic() transactions?"

Examples:
    # Context manager usage
    with open("file.txt") as f:       # Uses 'open' (builtin - skipped)
        pass

    with Progress() as p:              # Uses 'Progress' as context manager
        pass

    with transaction.atomic():         # Uses 'atomic' as context manager
        pass

    async with session.get(url) as resp:  # Async context manager
        pass
"""

import ast
from typing import Any

from chunking.relationships.relationship_extractors.base_extractor import (
    BaseRelationshipExtractor,
)
from chunking.relationships.relationship_types import RelationshipType


# Builtin context managers to exclude
BUILTIN_CONTEXT_MANAGERS = {
    "open",
    "suppress",
    "redirect_stdout",
    "redirect_stderr",
}


class ContextManagerExtractor(BaseRelationshipExtractor):
    """
    Extract context manager usage from with statements.

    Tracks:
    - `with` statement context expressions
    - `async with` statement context expressions

    Filtering Rules:
    - Excludes builtin context managers (open, suppress, etc.)
    - Tracks both direct usage (Progress()) and attribute access (db.transaction())
    """

    def __init__(self) -> None:
        """Initialize context manager extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.USES_CONTEXT_MANAGER

    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        for node in self._walk_once(tree):
            if isinstance(node, (ast.With, ast.AsyncWith)):
                for item in node.items:
                    self._extract_context_expr(item.context_expr, chunk_metadata)

    def _extract_context_expr(
        self, node: ast.AST, chunk_metadata: dict[str, Any]
    ) -> None:
        """
        Extract the context manager being used.

        Args:
            node: Context expression AST node
            chunk_metadata: Metadata about the chunk
        """
        if isinstance(node, ast.Call):
            # with Manager() or with func()
            func_name = self._get_call_name(node.func)
            if func_name and not self._is_builtin_context_manager(func_name):
                self._add_edge(
                    source_id=chunk_metadata["chunk_id"],
                    target_name=func_name,
                    line_number=node.lineno,
                )
        elif isinstance(node, ast.Name):
            # with existing_manager:
            if not self._is_builtin_context_manager(node.id):
                self._add_edge(
                    source_id=chunk_metadata["chunk_id"],
                    target_name=node.id,
                    line_number=node.lineno,
                )

    def _get_call_name(self, node: ast.AST) -> str | None:
        """
        Get the name from a Call node's func.

        Args:
            node: AST node

        Returns:
            Function/method name or None
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            # For db.transaction(), return 'transaction'
            return node.attr
        return None

    def _is_builtin_context_manager(self, name: str) -> bool:
        """
        Check if name is a builtin context manager.

        Args:
            name: Context manager name

        Returns:
            True if builtin
        """
        return name in BUILTIN_CONTEXT_MANAGERS
