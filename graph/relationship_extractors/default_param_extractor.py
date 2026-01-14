"""
Default parameter value extractor.

Extracts default parameter values that reference symbols (constants, classes, functions).
Enables queries like "What functions use DEFAULT_TIMEOUT?" or "Where is Config() used as default?".

Examples:
    # Using constant as default
    def connect(timeout=DEFAULT_TIMEOUT, retries=MAX_RETRIES):
        pass

    # Using callable as default
    def process(callback=default_handler, config=Config()):
        pass

    # Using None (skipped - too common)
    def foo(x=None):  # Not tracked
        pass
"""

import ast
from typing import Any

from graph.relationship_extractors.base_extractor import BaseRelationshipExtractor
from graph.relationship_types import RelationshipEdge, RelationshipType


class DefaultParameterExtractor(BaseRelationshipExtractor):
    """
    Extract default parameter value references from function definitions.

    Tracks:
    - Non-literal default values (names, calls, attributes)
    - Excludes trivial defaults (None, True, False, 0, "", [])
    - Excludes builtin defaults (list, dict, set)

    Output Format:
    - Target name is the referenced symbol (e.g., "DEFAULT_TIMEOUT")
    - Metadata includes parameter name for context
    """

    def __init__(self) -> None:
        """Initialize default parameter extractor."""
        super().__init__()
        self.relationship_type = RelationshipType.USES_DEFAULT

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract default parameter relationships from code.

        Args:
            code: Source code string to analyze
            chunk_metadata: Metadata about the code chunk

        Returns:
            List of RelationshipEdge objects for default parameters

        Example:
            >>> extractor = DefaultParameterExtractor()
            >>> code = '''
            ... DEFAULT_TIMEOUT = 30
            ... def connect(timeout=DEFAULT_TIMEOUT):
            ...     pass
            ... '''
            >>> edges = extractor.extract(code, {"chunk_id": "test.py:2-3:function:connect"})
            >>> len(edges)
            1
            >>> edges[0].target_name
            'DEFAULT_TIMEOUT'
        """
        self._reset_state()

        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.logger.debug(
                f"Syntax error parsing code in {chunk_metadata.get('chunk_id', 'unknown')}"
            )
            return []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_defaults(node, chunk_metadata)

        self._log_extraction_result(chunk_metadata)
        return self.edges

    def _extract_defaults(self, node: ast.FunctionDef, chunk_metadata: dict[str, Any]):
        """
        Extract default values that are names (not literals).

        Processes:
        - Regular args with defaults: def foo(x=DEFAULT)
        - Keyword-only args with defaults: def foo(*, x=DEFAULT)
        - Excludes None, True, False, numeric/string literals

        Args:
            node: FunctionDef or AsyncFunctionDef AST node
            chunk_metadata: Chunk metadata
        """
        args = node.args

        # Regular args with defaults
        # Defaults are aligned right (last N args have defaults)
        defaults_offset = len(args.args) - len(args.defaults)
        for i, default in enumerate(args.defaults):
            arg_name = args.args[defaults_offset + i].arg
            self._extract_default_value(default, arg_name, chunk_metadata, node.lineno)

        # Keyword-only args with defaults
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=False):
            if default:  # kw_defaults can have None entries
                self._extract_default_value(
                    default, arg.arg, chunk_metadata, node.lineno
                )

    def _extract_default_value(
        self,
        default: ast.AST,
        param_name: str,
        chunk_metadata: dict[str, Any],
        func_lineno: int,
    ):
        """
        Extract a single default value if it references a symbol.

        Tracks:
        - Name references: def foo(x=DEFAULT_TIMEOUT)
        - Attribute access: def foo(x=config.TIMEOUT)
        - Call expressions: def foo(x=Config())

        Skips:
        - Literals: None, True, False, 0, "", []
        - Builtins: list, dict, set

        Args:
            default: AST node for default value
            param_name: Parameter name this default belongs to
            chunk_metadata: Chunk metadata
            func_lineno: Line number of function definition
        """
        # Skip trivial defaults
        if self._is_trivial_default(default):
            return

        # Extract name/symbol from default
        target_name = self._get_symbol_name(default)

        if target_name and not self._is_builtin(target_name):
            self._add_edge(
                source_id=chunk_metadata["chunk_id"],
                target_name=target_name,
                line_number=(
                    default.lineno if hasattr(default, "lineno") else func_lineno
                ),
                parameter=param_name,
                default_type=self._get_default_type(default),
            )

    @staticmethod
    def _is_trivial_default(default: ast.AST) -> bool:
        """
        Check if default value is trivial (skip these).

        Trivial defaults:
        - None, True, False
        - Numeric literals (0, 1, -1, 0.0)
        - String literals ("", "default")
        - Empty collections ([], {}, ())

        Args:
            default: AST node for default value

        Returns:
            True if default is trivial

        Examples:
            >>> # def foo(x=None): → trivial
            >>> # def foo(x=0): → trivial
            >>> # def foo(x=DEFAULT): → not trivial
        """
        # Constant values (None, True, False, numbers, strings)
        if isinstance(default, ast.Constant):
            value = default.value
            # None, booleans
            if value is None or isinstance(value, bool):
                return True
            # Small numbers
            if isinstance(value, (int, float)) and -10 <= value <= 10:
                return True
            # Empty strings
            if isinstance(value, str) and len(value) == 0:
                return True

        # Empty collections
        if isinstance(default, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
            if isinstance(default, ast.Dict):
                return len(default.keys) == 0
            else:
                return len(default.elts) == 0

        return False

    @staticmethod
    def _get_symbol_name(default: ast.AST) -> str:
        """
        Extract symbol name from default value AST node.

        Handles:
        - Name: DEFAULT_TIMEOUT → "DEFAULT_TIMEOUT"
        - Attribute: config.TIMEOUT → "config.TIMEOUT"
        - Call: Config() → "Config"

        Args:
            default: AST node for default value

        Returns:
            Symbol name or empty string if not applicable

        Examples:
            >>> # def foo(x=DEFAULT): → "DEFAULT"
            >>> # def foo(x=Config()): → "Config"
            >>> # def foo(x=module.Config()): → "module.Config"
        """
        # Simple name reference
        if isinstance(default, ast.Name):
            return default.id

        # Attribute access (module.symbol or obj.attr)
        if isinstance(default, ast.Attribute):
            return DefaultParameterExtractor._get_attr_path(default)

        # Call expression (extract callee)
        if isinstance(default, ast.Call):
            if isinstance(default.func, ast.Name):
                return default.func.id
            elif isinstance(default.func, ast.Attribute):
                return DefaultParameterExtractor._get_attr_path(default.func)

        return ""

    @staticmethod
    def _get_attr_path(node: ast.Attribute) -> str:
        """
        Get full attribute path (e.g., "module.Class.attr").

        Recursively builds path for nested attributes.

        Args:
            node: Attribute AST node

        Returns:
            Full attribute path

        Examples:
            >>> # config.TIMEOUT → "config.TIMEOUT"
            >>> # module.config.TIMEOUT → "module.config.TIMEOUT"
        """
        parts = [node.attr]
        current = node.value

        while isinstance(current, ast.Attribute):
            parts.insert(0, current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.insert(0, current.id)

        return ".".join(parts)

    @staticmethod
    def _get_default_type(default: ast.AST) -> str:
        """
        Get type of default value for metadata.

        Args:
            default: AST node for default value

        Returns:
            Type string ("name", "call", "attribute")

        Examples:
            >>> # def foo(x=DEFAULT): → "name"
            >>> # def foo(x=Config()): → "call"
            >>> # def foo(x=config.TIMEOUT): → "attribute"
        """
        if isinstance(default, ast.Name):
            return "name"
        elif isinstance(default, ast.Call):
            return "call"
        elif isinstance(default, ast.Attribute):
            return "attribute"
        else:
            return "unknown"
