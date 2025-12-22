"""
Abstract base class for relationship extractors.

All relationship extractors inherit from BaseRelationshipExtractor and
implement the extract() method to find specific types of relationships
in Python code.

Example:
    class MyExtractor(BaseRelationshipExtractor):
        def extract(self, code: str, chunk_metadata: Dict[str, Any]):
            # Parse code and find relationships
            edges = []
            # ... extraction logic ...
            return edges
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List

from graph.relationship_types import RelationshipEdge, RelationshipType
from search.filters import normalize_path


class BaseRelationshipExtractor(ABC):
    """
    Abstract base class for all relationship extractors.

    Subclasses must implement the extract() method to find relationships
    in Python code using AST parsing.

    Attributes:
        logger: Logger instance for this extractor
        relationship_type: Type of relationship this extractor finds (set by subclass)
        edges: Accumulated edges during extraction (reset for each extract() call)
    """

    def __init__(self):
        """Initialize the base extractor."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.relationship_type: RelationshipType = None  # Set by subclass
        self.edges: List[RelationshipEdge] = []

    @abstractmethod
    def extract(
        self, code: str, chunk_metadata: Dict[str, Any]
    ) -> List[RelationshipEdge]:
        """
        Extract relationships from code.

        This method must be implemented by all subclasses.

        Args:
            code: Source code string to analyze
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier (e.g., "file.py:10-20:function:foo")
                - file_path: Path to source file
                - name: Symbol name (function/class name)
                - chunk_type: Type of chunk ("function", "class", etc.)

        Returns:
            List of RelationshipEdge objects found in the code

        Raises:
            SyntaxError: If code cannot be parsed (should be caught and logged)

        Example:
            >>> extractor = InheritanceExtractor()
            >>> edges = extractor.extract(
            ...     "class Child(Parent): pass",
            ...     {"chunk_id": "test.py:1-2:class:Child", "file_path": "test.py"}
            ... )
            >>> len(edges)
            1
            >>> edges[0].relationship_type
            <RelationshipType.INHERITS: 'inherits'>
        """
        pass

    def _reset_state(self):
        """
        Reset extractor state before extraction.

        Call this at the beginning of extract() to clear accumulated edges
        from previous extractions.
        """
        self.edges = []

    def _log_extraction_result(self, chunk_metadata: Dict[str, Any]):
        """
        Log extraction results for debugging.

        Args:
            chunk_metadata: Metadata about the processed chunk
        """
        chunk_id = chunk_metadata.get("chunk_id", "unknown")
        num_edges = len(self.edges)

        if num_edges > 0:
            self.logger.debug(
                f"Extracted {num_edges} {self.relationship_type.value if self.relationship_type else 'unknown'} "
                f"relationship(s) from {chunk_id}"
            )
        else:
            self.logger.debug(
                f"No {self.relationship_type.value if self.relationship_type else 'unknown'} "
                f"relationships found in {chunk_id}"
            )

    def _create_edge(
        self,
        source_id: str,
        target_name: str,
        line_number: int = 0,
        confidence: float = 1.0,
        **metadata,
    ) -> RelationshipEdge:
        """
        Create a relationship edge with this extractor's type.

        Convenience method for creating edges with the correct relationship type.

        Args:
            source_id: Chunk ID of source
            target_name: Name of target symbol
            line_number: Line number where relationship occurs
            confidence: Confidence score (0.0-1.0)
            **metadata: Additional metadata fields

        Returns:
            RelationshipEdge instance

        Example:
            >>> edge = self._create_edge(
            ...     "test.py:10-20:function:foo",
            ...     "bar",
            ...     line_number=15,
            ...     context="call_argument"
            ... )
        """
        if self.relationship_type is None:
            raise ValueError(
                f"{self.__class__.__name__} must set self.relationship_type"
            )

        # Normalize source_id path to forward slashes for cross-platform consistency
        normalized_source_id = normalize_path(source_id)

        return RelationshipEdge(
            source_id=normalized_source_id,
            target_name=target_name,
            relationship_type=self.relationship_type,
            line_number=line_number,
            confidence=confidence,
            metadata=metadata,
        )

    def _add_edge(
        self,
        source_id: str,
        target_name: str,
        line_number: int = 0,
        confidence: float = 1.0,
        **metadata,
    ):
        """
        Create and add an edge to the accumulated edges list.

        Convenience method that combines _create_edge() and appending to self.edges.

        Args:
            source_id: Chunk ID of source
            target_name: Name of target symbol
            line_number: Line number where relationship occurs
            confidence: Confidence score (0.0-1.0)
            **metadata: Additional metadata fields

        Example:
            >>> self._add_edge(
            ...     "test.py:10-20:function:foo",
            ...     "bar",
            ...     line_number=15
            ... )
        """
        edge = self._create_edge(
            source_id, target_name, line_number, confidence, **metadata
        )
        self.edges.append(edge)

    def _is_builtin(self, name: str) -> bool:
        """
        Check if a name is a Python builtin.

        Use this to filter out builtins from relationship extraction.

        Args:
            name: Symbol name to check

        Returns:
            True if name is a builtin

        Example:
            >>> self._is_builtin("print")
            True
            >>> self._is_builtin("MyClass")
            False
        """
        import builtins

        return hasattr(builtins, name)

    def _is_standard_library(self, module_name: str) -> bool:
        """
        Check if a module name is from the Python standard library.

        Args:
            module_name: Module name to check (e.g., "os", "sys")

        Returns:
            True if module is in standard library

        Example:
            >>> self._is_standard_library("os")
            True
            >>> self._is_standard_library("my_custom_module")
            False
        """
        # Common standard library modules
        stdlib_modules = {
            "abc",
            "asyncio",
            "collections",
            "datetime",
            "functools",
            "io",
            "itertools",
            "json",
            "logging",
            "os",
            "pathlib",
            "re",
            "sys",
            "time",
            "typing",
            "unittest",
            "warnings",
            "copy",
            "enum",
            "math",
            "random",
            "string",
            "subprocess",
            "threading",
            "queue",
            "socket",
            "http",
            "urllib",
            "email",
            "csv",
            "sqlite3",
            "pickle",
            "hashlib",
            "base64",
            "uuid",
            "tempfile",
            "shutil",
            "glob",
            "argparse",
            "configparser",
        }

        # Extract top-level module name
        top_level = module_name.split(".")[0]
        return top_level in stdlib_modules

    def _should_skip_target(
        self, target_name: str, include_stdlib: bool = False
    ) -> bool:
        """
        Check if a target should be skipped in relationship extraction.

        Args:
            target_name: Name of the target symbol/module
            include_stdlib: If False, skip standard library symbols

        Returns:
            True if target should be skipped

        Example:
            >>> self._should_skip_target("print")
            True  # Builtin
            >>> self._should_skip_target("os.path")
            True  # Stdlib (if include_stdlib=False)
            >>> self._should_skip_target("MyClass")
            False  # User-defined
        """
        # Skip builtins
        if self._is_builtin(target_name):
            return True

        # Skip stdlib if requested
        if not include_stdlib and self._is_standard_library(target_name):
            return True

        # Skip private/dunder names
        if target_name.startswith("_"):
            return True

        return False


class MultiPassExtractor(BaseRelationshipExtractor):
    """
    Base class for extractors that require multiple passes over the code.

    Some relationship types (e.g., protocol implementation, method overrides)
    require analyzing the code in multiple passes to build context before
    extracting relationships.

    Subclasses should override:
    - extract(): Main entry point (call _extract_pass_1() then _extract_pass_2())
    - _extract_pass_1(): First pass to build context
    - _extract_pass_2(): Second pass to extract relationships using context

    Example:
        class ProtocolExtractor(MultiPassExtractor):
            def extract(self, code, chunk_metadata):
                self._reset_state()
                tree = ast.parse(code)

                # Pass 1: Identify protocols
                self._extract_pass_1(tree, chunk_metadata)

                # Pass 2: Find implementations
                self._extract_pass_2(tree, chunk_metadata)

                return self.edges
    """

    def __init__(self):
        """Initialize multi-pass extractor."""
        super().__init__()
        self.context: Dict[str, Any] = {}  # Context built in first pass

    def _reset_state(self):
        """Reset state including context."""
        super()._reset_state()
        self.context = {}

    def _extract_pass_1(self, tree, chunk_metadata: Dict[str, Any]):
        """
        First pass: Build context.

        Override this to collect information needed for the second pass.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        pass

    def _extract_pass_2(self, tree, chunk_metadata: Dict[str, Any]):
        """
        Second pass: Extract relationships using context.

        Override this to extract relationships using information from first pass.

        Args:
            tree: AST tree
            chunk_metadata: Chunk metadata
        """
        pass
