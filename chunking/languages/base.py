"""Base classes for tree-sitter language chunkers.

This module contains the abstract base class and shared data structures
for all language-specific chunkers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from tree_sitter import Language, Parser

if TYPE_CHECKING:
    from search.config import ChunkingConfig

logger = logging.getLogger(__name__)


def estimate_tokens(content: str, method: str = "whitespace") -> int:
    """Estimate token count for content.

    Args:
        content: Text content to estimate
        method: Estimation method - "whitespace" (fast) or "tiktoken" (accurate)

    Returns:
        Estimated token count

    Note:
        Whitespace splitting approximates tokens for code reasonably well
        (~1 token per whitespace-separated word). For more accuracy, use
        tiktoken (adds ~0.5ms per call, requires package installation).
    """
    if method == "tiktoken":
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(content))
        except ImportError:
            # Fall back to whitespace if tiktoken not installed
            pass

    # Whitespace approximation: split on whitespace and count words
    return len(content.split())


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

    def _create_merged_chunk(self, chunks: List[TreeSitterChunk]) -> TreeSitterChunk:
        """Combine multiple chunks into a single merged chunk.

        Args:
            chunks: List of chunks to merge (must be non-empty)

        Returns:
            Single TreeSitterChunk combining all content

        Note:
            Preserves start_line from first chunk, end_line from last.
            Sets node_type to "merged" to indicate merged origin.
            Only should be called with chunks that have the same parent_class.
        """
        if len(chunks) == 1:
            return chunks[0]

        # Combine content with double newline separator for readability
        merged_content = "\n\n".join(c.content for c in chunks)

        # Collect names from all chunks for metadata
        merged_names = [
            c.metadata.get("name") for c in chunks if c.metadata.get("name")
        ]

        # Create merged metadata
        merged_metadata = {
            "merged_from": merged_names,
            "merged_count": len(chunks),
            "original_node_types": [c.node_type for c in chunks],
        }

        # Copy parent info from first chunk (all should have same parent)
        first_meta = chunks[0].metadata
        for key in ["parent_name", "parent_type"]:
            if key in first_meta:
                merged_metadata[key] = first_meta[key]

        return TreeSitterChunk(
            content=merged_content,
            start_line=chunks[0].start_line,
            end_line=chunks[-1].end_line,
            node_type="merged",
            language=chunks[0].language,
            metadata=merged_metadata,
            parent_class=chunks[0].parent_class,
        )

    def _greedy_merge_small_chunks(
        self,
        chunks: List[TreeSitterChunk],
        min_tokens: int = 50,
        max_merged_tokens: int = 1000,
        token_method: str = "whitespace",
    ) -> List[TreeSitterChunk]:
        """Merge adjacent small chunks using cAST greedy algorithm.

        Implements the greedy sibling merging from the cAST paper (EMNLP 2025):
        1. Iterate through chunks in order
        2. If chunk size < min_tokens, accumulate with next sibling
        3. Stop merging when accumulated size reaches max_merged_tokens
        4. Only merge chunks with same parent_class (true siblings)

        Args:
            chunks: List of chunks from AST traversal
            min_tokens: Minimum tokens before considering merge (default: 50)
            max_merged_tokens: Maximum tokens for merged chunk (default: 1000)
            token_method: Token estimation method ("whitespace" or "tiktoken")

        Returns:
            List of chunks with small siblings merged

        Example:
            >>> # Three tiny getter methods (10 tokens each)
            >>> chunks = [get_name(), get_age(), get_email()]
            >>> merged = chunker._greedy_merge_small_chunks(chunks, min_tokens=50)
            >>> len(merged)  # All 3 merged into 1
            1
        """
        if not chunks or len(chunks) == 1:
            return chunks

        result: List[TreeSitterChunk] = []
        current_group: List[TreeSitterChunk] = []
        current_tokens: int = 0
        current_parent: Optional[str] = None

        for chunk in chunks:
            chunk_tokens = estimate_tokens(chunk.content, token_method)
            chunk_parent = chunk.parent_class

            start_new_group = False

            # Case 1: Parent class changed (not true siblings)
            if current_group and chunk_parent != current_parent:
                start_new_group = True
            # Case 2: Adding this chunk would exceed max size
            elif current_group and current_tokens + chunk_tokens > max_merged_tokens:
                start_new_group = True
            # Case 3: Current chunk is large enough on its own
            elif chunk_tokens >= min_tokens:
                # Flush current group first
                if current_group:
                    result.append(self._create_merged_chunk(current_group))
                    current_group = []
                    current_tokens = 0
                # Add large chunk directly
                result.append(chunk)
                current_parent = None
                continue

            if start_new_group:
                # Flush current group
                if current_group:
                    result.append(self._create_merged_chunk(current_group))
                current_group = []
                current_tokens = 0

            # Add chunk to current group
            current_group.append(chunk)
            current_tokens += chunk_tokens
            current_parent = chunk_parent

        # Flush remaining group
        if current_group:
            result.append(self._create_merged_chunk(current_group))

        return result

    def chunk_code(
        self,
        source_code: str,
        config: Optional["ChunkingConfig"] = None,
    ) -> List[TreeSitterChunk]:
        """Chunk source code into semantic units.

        Args:
            source_code: Source code string
            config: Optional ChunkingConfig for merge settings.
                    If None, uses ServiceLocator to get global config.

        Returns:
            List of TreeSitterChunk objects (may include merged chunks)
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

        # Apply greedy sibling merging if enabled
        if config is None:
            config = self._get_chunking_config()

        if config and config.enable_greedy_merge and len(chunks) > 1:
            chunks = self._greedy_merge_small_chunks(
                chunks,
                min_tokens=config.min_chunk_tokens,
                max_merged_tokens=config.max_merged_tokens,
                token_method=config.token_estimation,
            )

        return chunks

    def _get_chunking_config(self) -> Optional["ChunkingConfig"]:
        """Get ChunkingConfig from ServiceLocator or return None.

        Returns:
            ChunkingConfig if available, None otherwise
        """
        try:
            from mcp_server.services import ServiceLocator

            config = ServiceLocator.instance().get_config()
            return config.chunking if config else None
        except (ImportError, AttributeError):
            return None
