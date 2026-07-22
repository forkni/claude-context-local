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

import ast
import logging
import threading
from abc import ABC, abstractmethod
from typing import Any

from chunking.relationships.relationship_types import RelationshipEdge, RelationshipType
from utils.path_utils import normalize_path


# Single-entry, per-thread memo for _walk_once (below): keyed by tree identity, storing
# (tree, nodes) so the tree never references the cache back -- no reference cycle, so refcounting
# reclaims each tree the moment the next chunk's tree replaces this entry. Thread-local because
# MultiLanguageChunker already runs each worker's extractors from a per-thread instance
# (``self._local``, see ``_init_thread_extractors``) -- this mirrors that existing model.
_WALK_CACHE = threading.local()


def _cached_walk(tree: ast.AST) -> list[ast.AST]:
    """Module-level twin of ``BaseRelationshipExtractor._walk_once`` for the one caller
    (``ConstantExtractor._collect_assignment_target_ids``) that needs the shared walk from a
    ``@staticmethod`` and so has no ``self`` to call ``_walk_once`` through."""
    cached = getattr(_WALK_CACHE, "entry", None)
    if cached is not None and cached[0] is tree:
        return cached[1]
    nodes = list(ast.walk(tree))
    _WALK_CACHE.entry = (tree, nodes)
    return nodes


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

    def __init__(self) -> None:
        """Initialize the base extractor."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self.relationship_type: RelationshipType | None = None  # Set by subclass
        self.edges: list[RelationshipEdge] = []

    def extract(
        self, code: str, chunk_metadata: dict[str, Any]
    ) -> list[RelationshipEdge]:
        """
        Extract relationships from code.

        Parses ``code`` with ``ast.parse`` then delegates to
        :meth:`_extract_from_tree`.  Subclasses should implement
        ``_extract_from_tree`` rather than overriding this method.

        For the parse-once fast path (shared tree across all extractors) use
        :meth:`extract_from_tree` instead.

        Args:
            code: Source code string to analyze
            chunk_metadata: Metadata about the code chunk
                - chunk_id: Unique identifier (e.g., "file.py:10-20:function:foo")
                - file_path: Path to source file
                - name: Symbol name (function/class name)
                - chunk_type: Type of chunk ("function", "class", etc.)

        Returns:
            List of RelationshipEdge objects found in the code

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
        self._reset_state()
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            self.logger.debug(
                f"Failed to parse code in {chunk_metadata.get('file_path')}: {e}"
            )
            return []
        self._extract_from_tree(tree, chunk_metadata)
        self._log_extraction_result(chunk_metadata)
        return self.edges

    def extract_from_tree(
        self,
        tree: ast.AST,
        code: str,
        chunk_metadata: dict[str, Any],
    ) -> list[RelationshipEdge]:
        """
        Extract relationships using a pre-parsed AST tree.

        Avoids a redundant ``ast.parse`` call when the same tree is shared
        across multiple extractors (parse-once optimisation, #15).  The
        ``code`` parameter is accepted for API symmetry but is unused by the
        default implementation; subclasses that need it should read from it.

        Args:
            tree: Already-parsed AST tree for *code*
            code: Source code string (unused by default, kept for subclass use)
            chunk_metadata: Same as :meth:`extract`

        Returns:
            List of RelationshipEdge objects found in the code
        """
        self._reset_state()
        self._extract_from_tree(tree, chunk_metadata)
        self._log_extraction_result(chunk_metadata)
        return self.edges

    @abstractmethod
    def _extract_from_tree(self, tree: ast.AST, chunk_metadata: dict[str, Any]) -> None:
        """
        Walk the AST and populate ``self.edges``.

        This is the primary extension point.  Called by both :meth:`extract`
        (after parsing ``code``) and :meth:`extract_from_tree` (with a
        shared pre-parsed tree).

        Args:
            tree: Parsed AST for the chunk
            chunk_metadata: Metadata about the code chunk
        """
        pass

    def _reset_state(self) -> None:
        """
        Reset extractor state before extraction.

        Call this at the beginning of extract() to clear accumulated edges
        from previous extractions.
        """
        self.edges = []

    def _log_extraction_result(self, chunk_metadata: dict[str, Any]) -> None:
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
        relationship_type: RelationshipType | None = None,
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
            relationship_type: Per-edge override for the relationship type.
                If None, falls back to ``self.relationship_type``.  Pass this
                explicitly for extractors that emit more than one edge type
                (e.g. ExceptionExtractor emits RAISES and CATCHES) so the
                slot does not need to be mutated between edges.
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
        rel_type = relationship_type or self.relationship_type
        if rel_type is None:
            raise ValueError(
                f"{self.__class__.__name__} must set self.relationship_type"
            )

        # Normalize source_id path to forward slashes for cross-platform consistency
        normalized_source_id = normalize_path(source_id)

        return RelationshipEdge(
            source_id=normalized_source_id,
            target_name=target_name,
            relationship_type=rel_type,
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
        relationship_type: RelationshipType | None = None,
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
            relationship_type: Per-edge override (see ``_create_edge``).
            **metadata: Additional metadata fields

        Example:
            >>> self._add_edge(
            ...     "test.py:10-20:function:foo",
            ...     "bar",
            ...     line_number=15
            ... )
        """
        edge = self._create_edge(
            source_id,
            target_name,
            line_number,
            confidence,
            relationship_type,
            **metadata,
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

    def _walk_once(self, tree: ast.AST) -> list[ast.AST]:
        """
        Return every node in *tree* in ``ast.walk`` order, memoized per-thread by tree identity.

        ``extract_from_tree`` already parses each chunk's source exactly once and shares the
        resulting tree across every registered extractor (see ``MultiLanguageChunker``'s "Parse
        once" note) -- but every extractor still ran its OWN independent ``ast.walk(tree)`` over
        that same shared tree just to re-filter for its own node types (``ClassDef``,
        ``FunctionDef``, ``Call``, ...), i.e. one full tree walk apiece. Caching the unfiltered
        node list collapses that fan-out to a single shared walk no matter how many extractors
        consume it -- each extractor still applies its own ``isinstance`` filter over the shared
        list, unchanged.

        Order is identical to a fresh ``ast.walk(tree)``: ``ast.walk`` is deterministic BFS, so
        this is exactly the sequence each extractor's own walk would have produced in isolation --
        extraction order (and therefore edge order) is unaffected.

        The memo is a single-entry, per-thread ``(tree, nodes)`` pair in ``_WALK_CACHE`` -- NOT an
        attribute on the tree. Storing it off the tree matters: attaching ``nodes`` directly to
        the tree (e.g. ``tree._shared_walk = nodes``) would create a reference cycle, since
        ``ast.walk`` yields the root node first -- the list's own first element would be the tree
        itself (``tree.__dict__ -> list -> tree``), reachable only by the cyclic GC. Keeping the
        cache external means refcounting alone reclaims each tree (and its node list) the moment
        the next chunk's tree replaces this thread's single entry -- no cyclic garbage generated
        in the first place, which matters to any long-running process that would rather not pay
        for cycle collection on every parsed chunk.

        Args:
            tree: Parsed AST for the chunk (the same object every extractor's
                ``extract_from_tree`` call receives for this chunk)

        Returns:
            Every node in *tree*, in ``ast.walk``'s BFS order
        """
        return _cached_walk(tree)
