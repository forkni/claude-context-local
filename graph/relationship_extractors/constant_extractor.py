"""
Constant definition and usage extractor.

Extracts module-level constant definitions (UPPER_CASE assignments) and their usages.
This enables queries like "Where is FAISS_INDEX_FILENAME used?" or "What constants
does this function depend on?"

Examples:
    # Module-level constant definition
    TIMEOUT = 30
    MAX_RETRIES = 3
    CONFIG_PATH = "/etc/config"

    # Usage in function
    def connect():
        time.sleep(TIMEOUT)  # Uses TIMEOUT constant
"""

import ast
from typing import Any, Dict, List, Set

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class ConstantExtractor(BaseRelationshipExtractor):
    """
    Extract constant definitions and usages from Python code.

    Tracks:
    - Module-level UPPER_CASE constant definitions
    - References to constants in functions/methods

    Filtering Rules:
    - Only UPPER_CASE names (e.g., TIMEOUT, MAX_RETRIES)
    - Excludes private constants (_INTERNAL)
    - Excludes single-character names (too generic)
    - Excludes all-numeric values (trivial constants)
    """

    def __init__(self):
        """Initialize constant extractor."""
        super().__init__()
        self.known_constants: Set[str] = set()

    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        """
        Extract constant relationships from code.

        Args:
            code: Source code string to analyze
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier
                - chunk_type: Type of chunk ("module", "function", etc.)

        Returns:
            List of RelationshipEdge objects for constant relationships

        Example:
            >>> extractor = ConstantExtractor()
            >>> code = '''
            ... TIMEOUT = 30
            ... def connect():
            ...     time.sleep(TIMEOUT)
            ... '''
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:1:module"})
            >>> len(edges)
            2  # One DEFINES_CONSTANT, one USES_CONSTANT
        """
        self._reset_state()
        self.known_constants.clear()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.logger.debug(
                f"Syntax error parsing code in {chunk_metadata.get('chunk_id', 'unknown')}"
            )
            return []

        chunk_type = chunk_metadata.get("chunk_type", "")

        # Extract definitions from module-level chunks
        if chunk_type == "module":
            self._extract_constant_definitions(tree, chunk_metadata)

        # Extract usages from all chunks
        self._extract_constant_usages(tree, chunk_metadata)

        self._log_extraction_result(chunk_metadata)
        return self.edges

    def _extract_constant_definitions(
        self, tree: ast.AST, chunk_metadata: Dict[str, Any]
    ):
        """
        Extract UPPER_CASE = value at module level.

        Only processes top-level assignments (not inside functions/classes).

        Args:
            tree: AST tree to analyze
            chunk_metadata: Chunk metadata
        """
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and self._is_constant_name(
                        target.id
                    ):
                        # Check if value is trivial (skip all-numeric constants)
                        if not self._is_trivial_value(node.value):
                            self.relationship_type = RelationshipType.DEFINES_CONSTANT
                            self._add_edge(
                                source_id=chunk_metadata["chunk_id"],
                                target_name=target.id,
                                line_number=node.lineno,
                                definition=True,
                            )
                            self.known_constants.add(target.id)

    def _extract_constant_usages(self, tree: ast.AST, chunk_metadata: Dict[str, Any]):
        """
        Extract references to known constants.

        Finds all Name nodes that:
        1. Match constant naming convention (UPPER_CASE)
        2. Are not assignment targets (left-hand side of =)
        3. Are not trivial (single char, builtin)

        Args:
            tree: AST tree to analyze
            chunk_metadata: Chunk metadata
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and self._is_constant_name(node.id):
                # Skip if this is an assignment target
                if not self._is_assignment_target(node, tree):
                    # Skip builtins (e.g., True, False, None)
                    if not self._is_builtin(node.id):
                        self.relationship_type = RelationshipType.USES_CONSTANT
                        self._add_edge(
                            source_id=chunk_metadata["chunk_id"],
                            target_name=node.id,
                            line_number=node.lineno,
                        )

    @staticmethod
    def _is_constant_name(name: str) -> bool:
        """
        Check if name follows CONSTANT_CASE convention.

        Rules:
        - All uppercase (A-Z, 0-9, _)
        - At least 2 characters (excludes single-char like X)
        - Not private (doesn't start with _)

        Args:
            name: Variable name to check

        Returns:
            True if name looks like a constant

        Examples:
            >>> ConstantExtractor._is_constant_name("TIMEOUT")
            True
            >>> ConstantExtractor._is_constant_name("MAX_RETRIES")
            True
            >>> ConstantExtractor._is_constant_name("timeout")
            False
            >>> ConstantExtractor._is_constant_name("_INTERNAL")
            False
            >>> ConstantExtractor._is_constant_name("X")
            False
        """
        return (
            len(name) >= 2
            and name.isupper()
            and not name.startswith("_")
            and not name.endswith("_")
        )

    @staticmethod
    def _is_trivial_value(node: ast.AST) -> bool:
        """
        Check if assignment value is trivial (skip these).

        Trivial values:
        - Single-digit numbers (0-9)
        - Empty strings ONLY (non-empty strings are important constants)
        - Empty collections

        Args:
            node: AST node representing the value

        Returns:
            True if value is trivial

        Examples:
            >>> # MAX_RETRIES = 3 → trivial (single digit)
            >>> # TIMEOUT = 30 → not trivial
            >>> # EMPTY = "" → trivial
            >>> # CONFIG_PATH = "/etc/config" → not trivial
        """
        # Single-digit numbers only
        if isinstance(node, ast.Constant):
            if isinstance(node.value, int) and -9 <= node.value <= 9:
                return True
            # Only empty strings are trivial
            if isinstance(node.value, str) and len(node.value) == 0:
                return True

        # Empty collections
        if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
            return len(node.elts if hasattr(node, "elts") else node.keys) == 0

        return False

    @staticmethod
    def _is_assignment_target(node: ast.Name, tree: ast.AST) -> bool:
        """
        Check if a Name node is the target of an assignment.

        This prevents counting "TIMEOUT = 30" as a usage of TIMEOUT.

        Args:
            node: Name node to check
            tree: Full AST tree for context

        Returns:
            True if node is assignment target (left-hand side of =)
        """
        for parent in ast.walk(tree):
            if isinstance(parent, ast.Assign):
                for target in parent.targets:
                    if target is node:
                        return True
            elif isinstance(parent, ast.AnnAssign) and parent.target is node:
                return True

        return False

    def _reset_state(self):
        """Reset extractor state before extraction."""
        super()._reset_state()
        # Note: We don't reset known_constants here because we want to track
        # constants across definitions and usages in the same extraction call
