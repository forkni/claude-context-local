"""Base classes for tree-sitter language chunkers.

This module contains the abstract base class and shared data structures
for all language-specific chunkers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from tree_sitter import Language, Parser

logger = logging.getLogger(__name__)


@dataclass
class TreeSitterChunk:
    """Represents a code chunk extracted using tree-sitter."""

    content: str
    start_line: int
    end_line: int
    node_type: str
    language: str
    metadata: Dict[str, Any]
    chunk_id: Optional[str] = None  # unique identifier for evaluation
    parent_class: Optional[str] = None  # Enclosing class name for methods

    def to_dict(self) -> Dict:
        """Convert to dictionary format compatible with existing system."""
        return {
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "type": self.node_type,
            "language": self.language,
            "metadata": self.metadata,
        }


class LanguageChunker(ABC):
    """Abstract base class for language-specific chunkers."""

    def __init__(self, language_name: str, language: Optional[Language] = None):
        """Initialize language chunker.

        Args:
            language_name: Programming language name
            language: Tree-sitter Language object (optional, will auto-load if not provided)
        """
        self.language_name = language_name
        if language is None:
            language = self._load_language()
        self.language = language
        self.parser = Parser(language)
        self.splittable_node_types = self._get_splittable_node_types()

    def _load_language(self) -> Language:
        """Load the tree-sitter language binding.

        Override in subclasses to provide language-specific loading.

        Returns:
            Language object

        Raises:
            ValueError: If language binding not available
        """
        raise ValueError(
            f"Language {self.language_name} not available. "
            f"Install tree-sitter-{self.language_name} or pass language explicitly."
        )

    @abstractmethod
    def _get_splittable_node_types(self) -> Set[str]:
        """Get node types that should be split into chunks.

        Returns:
            Set of node type names
        """
        pass

    @abstractmethod
    def extract_metadata(self, node: Any, source: bytes) -> Dict[str, Any]:
        """Extract metadata from a node.

        Args:
            node: Tree-sitter node
            source: Source code bytes

        Returns:
            Metadata dictionary
        """
        pass

    def should_chunk_node(self, node: Any) -> bool:
        """Check if a node should be chunked.

        Args:
            node: Tree-sitter node

        Returns:
            True if node should be chunked
        """
        return node.type in self.splittable_node_types

    def get_node_text(self, node: Any, source: bytes) -> str:
        """Get text content of a node.

        Args:
            node: Tree-sitter node
            source: Source code bytes

        Returns:
            Text content
        """
        return source[node.start_byte : node.end_byte].decode("utf-8")

    def get_line_numbers(self, node: Any) -> Tuple[int, int]:
        """Get start and end line numbers for a node.

        Args:
            node: Tree-sitter node

        Returns:
            Tuple of (start_line, end_line)
        """
        # Tree-sitter uses 0-based indexing, convert to 1-based
        return node.start_point[0] + 1, node.end_point[0] + 1

    def chunk_code(self, source_code: str) -> List[TreeSitterChunk]:
        """Chunk source code into semantic units.

        Args:
            source_code: Source code string

        Returns:
            List of TreeSitterChunk objects
        """
        source_bytes = bytes(source_code, "utf-8")
        tree = self.parser.parse(source_bytes)
        chunks = []

        def traverse(node, depth=0, parent_info=None):
            """Recursively traverse the tree and extract chunks."""
            if self.should_chunk_node(node):
                start_line, end_line = self.get_line_numbers(node)
                content = self.get_node_text(node, source_bytes)
                metadata = self.extract_metadata(node, source_bytes)

                # Add parent information if available
                if parent_info:
                    metadata.update(parent_info)

                # Extract parent class from parent_info if available
                parent_class_name = (
                    parent_info.get("parent_name") if parent_info else None
                )

                chunk = TreeSitterChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    node_type=node.type,
                    language=self.language_name,
                    metadata=metadata,
                    parent_class=parent_class_name,
                )
                chunks.append(chunk)

                # For classes, continue traversing to find methods
                # For other chunked nodes, stop traversal
                if node.type in ["class_definition", "class_declaration"]:
                    # Pass class info to children
                    class_info = {
                        "parent_name": metadata.get("name"),
                        "parent_type": "class",
                    }
                    for child in node.children:
                        traverse(child, depth + 1, class_info)
                return

            # Traverse children, passing along parent info
            for child in node.children:
                traverse(child, depth + 1, parent_info)

        traverse(tree.root_node)

        # If no chunks found, create a single module-level chunk
        if not chunks and source_code.strip():
            chunks.append(
                TreeSitterChunk(
                    content=source_code,
                    start_line=1,
                    end_line=len(source_code.split("\n")),
                    node_type="module",
                    language=self.language_name,
                    metadata={"type": "module"},
                )
            )

        return chunks
