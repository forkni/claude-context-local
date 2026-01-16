"""Base classes for tree-sitter language chunkers.

This module contains the abstract base class and shared data structures
for all language-specific chunkers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Optional

from tree_sitter import Language, Parser

if TYPE_CHECKING:
    from chunking.python_ast_chunker import CodeChunk
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
            token_count = len(enc.encode(content))
            logger.debug(f"tiktoken: {len(content)} chars -> {token_count} tokens")
            return token_count
        except ImportError:
            # Fall back to whitespace if tiktoken not installed
            logger.warning(
                "tiktoken not installed, falling back to whitespace estimation. "
                "Install with: pip install tiktoken"
            )
            pass

    # Whitespace approximation: split on whitespace and count words
    token_count = len(content.split())
    logger.debug(f"whitespace: {len(content)} chars -> {token_count} tokens")
    return token_count


def estimate_characters(content: str, count_whitespace: bool = False) -> int:
    """Count characters in content (cAST paper approach).

    Args:
        content: Text content to measure
        count_whitespace: If False, count non-whitespace only (cAST default)

    Returns:
        Character count

    Reference:
        cAST (EMNLP 2025): Uses non-whitespace characters for language-agnostic sizing
    """
    if count_whitespace:
        return len(content)
    # Remove all whitespace characters for non-whitespace count
    return sum(1 for c in content if not c.isspace())


@dataclass
class TreeSitterChunk:
    """Represents a code chunk extracted using tree-sitter."""

    content: str
    start_line: int
    end_line: int
    node_type: str
    language: str
    metadata: dict[str, Any]
    chunk_id: Optional[str] = None  # unique identifier for evaluation
    parent_class: Optional[str] = None  # Enclosing class name for methods
    parent_chunk_id: Optional[str] = None  # Enclosing class chunk_id for methods
    community_id: Optional[int] = None  # Leiden community membership (Phase 0)

    def to_dict(self) -> dict:
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

    def __init__(self, language_name: str, language: Optional[Language] = None) -> None:
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
    def _get_splittable_node_types(self) -> set[str]:
        """Get node types that should be split into chunks.

        Returns:
            Set of node type names
        """
        pass

    @abstractmethod
    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
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

    def get_line_numbers(self, node: Any) -> tuple[int, int]:
        """Get start and end line numbers for a node.

        Args:
            node: Tree-sitter node

        Returns:
            Tuple of (start_line, end_line)
        """
        # Tree-sitter uses 0-based indexing, convert to 1-based
        return node.start_point[0] + 1, node.end_point[0] + 1

    def _create_merged_chunk(self, chunks: list[TreeSitterChunk]) -> TreeSitterChunk:
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

        # Copy parent info and file location from first chunk (all should have same parent)
        first_meta = chunks[0].metadata
        for key in ["parent_name", "parent_type", "name", "file_path", "relative_path"]:
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
        chunks: list[TreeSitterChunk],
        min_tokens: int = 50,
        max_merged_tokens: int = 1000,
        token_method: str = "whitespace",
        use_community_boundary: bool = False,
        size_method: str = "tokens",
    ) -> tuple[list[TreeSitterChunk], int, int]:
        """Merge adjacent small chunks using cAST greedy algorithm.

        Implements the greedy sibling merging from the cAST paper (EMNLP 2025):
        1. Iterate through chunks in order
        2. If chunk size < min_tokens, accumulate with next sibling
        3. Stop merging when accumulated size reaches max_merged_tokens
        4. Only merge chunks with same parent_class (true siblings) or same community_id

        Args:
            chunks: List of chunks from AST traversal
            min_tokens: Minimum tokens before considering merge (default: 50)
            max_merged_tokens: Maximum tokens for merged chunk (default: 1000)
            token_method: Token estimation method ("whitespace" or "tiktoken")
            use_community_boundary: Use community_id instead of parent_class (default: False)
            size_method: Size calculation method - "tokens" (default) or "characters" (cAST paper)

        Returns:
            Tuple of (merged_chunks, original_count, merged_count):
                - merged_chunks: List of chunks with small siblings merged
                - original_count: Number of chunks before merging
                - merged_count: Number of chunks after merging

        Example:
            >>> # Three tiny getter methods (10 tokens each)
            >>> chunks = [get_name(), get_age(), get_email()]
            >>> merged, orig, final = chunker._greedy_merge_small_chunks(chunks, min_tokens=50)
            >>> orig, final  # 3 chunks merged into 1
            (3, 1)
        """
        if not chunks or len(chunks) == 1:
            return chunks, len(chunks), len(chunks)

        # Define size calculation based on method
        if size_method == "characters":
            # cAST paper: ~4 chars per token ratio
            min_size = min_tokens * 4  # 50 tokens ≈ 200 chars
            max_size = max_merged_tokens * 4  # 1000 tokens ≈ 4000 chars
            logger.info(
                f"[SIZE_METHOD] Using character-based sizing: min={min_size} chars, max={max_size} chars"
            )

            def get_size(content: str) -> int:
                return estimate_characters(content, count_whitespace=False)

        else:
            min_size = min_tokens
            max_size = max_merged_tokens
            logger.info(
                f"[SIZE_METHOD] Using token-based sizing: min={min_size} tokens, max={max_size} tokens"
            )

            def get_size(content: str) -> int:
                return estimate_tokens(content, token_method)

        result: list[TreeSitterChunk] = []
        current_group: list[TreeSitterChunk] = []
        current_size: int = 0
        current_parent: Optional[str] = None
        current_community: Optional[int] = None  # Track community ID for Phase 1
        total_size_estimated: int = 0  # Track for summary logging

        current_file: Optional[str] = (
            None  # Track file path to prevent cross-file merging
        )

        for chunk in chunks:
            chunk_size = get_size(chunk.content)
            total_size_estimated += chunk_size
            chunk_parent = chunk.parent_class
            chunk_community = chunk.community_id
            chunk_file = chunk.metadata.get("file_path")  # Get file path from metadata

            start_new_group = False

            # Case 0: File boundary changed (NEVER merge across files)
            if current_group and chunk_file != current_file:
                start_new_group = True
            # Case 1: Boundary changed (community or parent class)
            elif use_community_boundary and current_group:
                # Phase 1: Use community_id as merge boundary
                if chunk_community != current_community:
                    start_new_group = True
            elif current_group and chunk_parent != current_parent:
                # Original: Use parent_class as merge boundary
                start_new_group = True
            # Case 2: Adding this chunk would exceed max size
            elif current_group and current_size + chunk_size > max_size:
                start_new_group = True
            # Case 3: Current chunk is large enough on its own
            elif chunk_size >= min_size:
                # Flush current group first
                if current_group:
                    result.append(self._create_merged_chunk(current_group))
                    current_group = []
                    current_size = 0
                # Add large chunk directly
                result.append(chunk)
                current_parent = None
                continue

            if start_new_group:
                # Flush current group
                if current_group:
                    result.append(self._create_merged_chunk(current_group))
                current_group = []
                current_size = 0

            # Add chunk to current group
            current_group.append(chunk)
            current_size += chunk_size
            current_parent = chunk_parent
            current_community = chunk_community  # Track for Phase 1
            current_file = chunk_file  # Track file path

        # Flush remaining group
        if current_group:
            result.append(self._create_merged_chunk(current_group))

        # Log at DEBUG level (per-file details suppressed during progress bar)
        # Summary will be aggregated and logged by parallel_chunker
        size_unit = "chars" if size_method == "characters" else "tokens"
        logger.debug(
            f"Greedy merge: {len(chunks)} → {len(result)} chunks, "
            f"{total_size_estimated} {size_unit} ({size_method})"
        )

        return result, len(chunks), len(result)

    @staticmethod
    def remerge_chunks_with_communities(
        chunks: list["CodeChunk"],
        community_map: dict[str, int],
        min_tokens: int = 50,
        max_merged_tokens: int = 1000,
        token_method: str = "whitespace",
        size_method: str = "tokens",
    ) -> list["CodeChunk"]:
        """Re-merge chunks using community boundaries (Community-based remerging).

        This is called AFTER community detection to re-merge chunks using
        community_id as boundaries instead of parent_class. Solves the circular
        dependency: chunking needs communities, but communities need chunks.

        Community merge flow:
            1. Chunk with AST boundaries → Build graph → Detect communities
            2. Re-merge using community_id boundaries ← THIS METHOD

        Args:
            chunks: List of CodeChunk (raw AST chunks)
            community_map: Dict mapping chunk_id to community_id from Louvain detection
            min_tokens: Minimum tokens before considering merge (default: 50)
            max_merged_tokens: Maximum tokens for merged chunk (default: 1000)
            token_method: Token estimation method ("whitespace" or "tiktoken")
            size_method: Size calculation method - "tokens" (default) or "characters" (cAST paper)

        Returns:
            List of CodeChunk re-merged with community boundaries

        Example:
            >>> # After community detection assigns IDs
            >>> community_map = {"file.py:1-10:method:foo": 0, "file.py:11-20:method:bar": 1}
            >>> remerged = remerge_chunks_with_communities(chunks, community_map)
            >>> # Methods from different communities won't merge
        """
        from dataclasses import replace

        if not chunks or not community_map:
            return chunks

        logger = logging.getLogger(__name__)
        logger.info(
            f"[REMERGE] Re-merging {len(chunks)} chunks with community boundaries"
        )

        # Step 1: Assign community_id to chunks from map
        chunks_with_community = []
        for chunk in chunks:
            # BUG FIX: chunk.chunk_id is None at this point, so generate lookup key
            # from chunk attributes instead of using None as dictionary key
            chunk_id = chunk.chunk_id

            # Generate lookup key from chunk attributes
            if chunk_id is None:
                # Normalize path separators to forward slashes for cross-platform consistency
                normalized_path = chunk.relative_path.replace("\\", "/")

                if chunk.parent_name and chunk.name:
                    lookup_key = f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}:{chunk.parent_name}.{chunk.name}"
                elif chunk.name:
                    lookup_key = f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}:{chunk.name}"
                else:
                    lookup_key = f"{normalized_path}:{chunk.start_line}-{chunk.end_line}:{chunk.chunk_type}"
            else:
                lookup_key = chunk_id

            community_id = community_map.get(lookup_key)

            # Debug: Log if community lookup failed
            if community_id is None:
                logger.debug(f"[REMERGE] No community found for {lookup_key}")

            # Create new chunk with community_id assigned
            updated_chunk = replace(chunk, community_id=community_id)
            chunks_with_community.append(updated_chunk)

        # Step 2: Convert CodeChunk → TreeSitterChunk for merge algorithm
        # The merge algorithm works on TreeSitterChunk
        from chunking.languages.base import TreeSitterChunk

        ts_chunks = []
        for chunk in chunks_with_community:
            ts_chunk = TreeSitterChunk(
                content=chunk.content,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                node_type=chunk.chunk_type,
                language=chunk.language,
                metadata={
                    "name": chunk.name,
                    "file_path": chunk.file_path,
                    "relative_path": chunk.relative_path,
                    # Preserve call graph and relationship data
                    "calls": chunk.calls,
                    "relationships": chunk.relationships,
                    "docstring": chunk.docstring,
                    "decorators": chunk.decorators,
                    "imports": chunk.imports,
                    "complexity_score": chunk.complexity_score,
                    "tags": chunk.tags,
                },
                chunk_id=chunk.chunk_id,
                parent_class=getattr(chunk, "parent_name", None),
                community_id=chunk.community_id,  # KEY: Now has community_id!
            )
            ts_chunks.append(ts_chunk)

        # Step 3: Re-run merge with use_community_boundary=True
        # Use LanguageChunker instance (language doesn't matter for merge)
        from chunking.languages.python import PythonChunker

        chunker = PythonChunker()
        merged_ts_chunks, orig_count, merged_count = chunker._greedy_merge_small_chunks(
            ts_chunks,
            min_tokens=min_tokens,
            max_merged_tokens=max_merged_tokens,
            token_method=token_method,
            use_community_boundary=True,  # KEY: Use community boundaries!
            size_method=size_method,  # Pass size method
        )

        logger.info(
            f"[REMERGE] Community-based merge: {orig_count} → {merged_count} chunks "
            f"({100 * (orig_count - merged_count) / orig_count:.1f}% reduction)"
        )

        # Step 4: Convert TreeSitterChunk → CodeChunk
        # Re-use structure from original chunks
        result_chunks = []
        for ts_chunk in merged_ts_chunks:
            # Find original chunk to copy metadata (by file_path and line overlap)
            # FIX: Correct line overlap logic and prevent cross-file metadata pollution
            merged_file = ts_chunk.metadata.get("file_path")
            original = None

            # First pass: Find original chunk CONTAINED within merged chunk's range
            # AND matches the file_path (prevent cross-file pollution)
            for c in chunks_with_community:
                # Must match file first (Bug #3 fix: prevent cross-file merging)
                if merged_file != c.file_path:
                    continue
                # Original chunk should be CONTAINED within merged chunk's range
                # Bug #2 fix: was inverted (merged >= original), now correct (original >= merged)
                if (
                    c.start_line >= ts_chunk.start_line
                    and c.end_line <= ts_chunk.end_line
                ):
                    original = c
                    break

            # Fallback: find any chunk from same file if exact overlap fails
            # Bug #1 fix: was dangerous fallback to [0], now same-file only
            if original is None:
                for c in chunks_with_community:
                    if merged_file == c.file_path:
                        original = c
                        logger.debug(
                            f"[REMERGE] Using fallback for {merged_file}:{ts_chunk.start_line}-{ts_chunk.end_line}"
                        )
                        break

            # Last resort: skip chunk if no valid original found
            # Bug #1 fix: was using wrong file, now skip instead
            if original is None:
                logger.warning(
                    f"[REMERGE] No original chunk found for merged chunk at "
                    f"{merged_file}:{ts_chunk.start_line}-{ts_chunk.end_line}, skipping"
                )
                continue  # Skip this malformed chunk instead of using wrong file

            # Create CodeChunk with correct fields
            from chunking.python_ast_chunker import CodeChunk

            code_chunk = CodeChunk(
                content=ts_chunk.content,
                chunk_type=(
                    ts_chunk.node_type if ts_chunk.node_type != "merged" else "merged"
                ),
                start_line=ts_chunk.start_line,
                end_line=ts_chunk.end_line,
                file_path=original.file_path,
                relative_path=original.relative_path,
                folder_structure=original.folder_structure,
                name=ts_chunk.metadata.get("name"),
                parent_name=ts_chunk.parent_class,
                language=original.language,
                chunk_id=None,  # Will be regenerated with proper format
                community_id=ts_chunk.community_id,  # Preserved!
                merged_from=ts_chunk.metadata.get(
                    "merged_from"
                ),  # Phase A6: Copy merged symbols
                # Preserve call graph and relationship data
                # For non-merged chunks, copy from original; for merged chunks, use empty lists
                calls=original.calls if ts_chunk.node_type != "merged" else [],
                relationships=(
                    original.relationships if ts_chunk.node_type != "merged" else []
                ),
                docstring=original.docstring,
                decorators=original.decorators,
                imports=original.imports,
                complexity_score=original.complexity_score,
                tags=original.tags,
            )
            result_chunks.append(code_chunk)

        return result_chunks

    def _get_block_boundary_types(self) -> set[str]:
        """Get node types that are valid split boundaries.

        Override in language-specific chunkers for language-appropriate boundaries.
        Default returns empty set (no splitting).

        Returns:
            Set of node type names that can be split points
        """
        return set()

    def _extract_signature(self, node: Any, source_bytes: bytes) -> str:
        """Extract function/method signature from a node.

        Override in language-specific chunkers for proper signature extraction.
        Default returns first line(s) until colon.

        Args:
            node: Tree-sitter node (function_definition, decorated_definition, etc.)
            source_bytes: Source code bytes

        Returns:
            Signature string including decorators, def line, and opening colon
        """
        content = self.get_node_text(node, source_bytes)
        lines = content.split("\n")
        sig_lines = []
        for line in lines:
            sig_lines.append(line)
            if line.rstrip().endswith(":"):
                break
        return "\n".join(sig_lines)

    def _find_body_node(self, node: Any) -> Optional[Any]:
        """Find the body/block child node of a function definition.

        Args:
            node: Function definition node

        Returns:
            Body block node or None
        """
        for child in node.children:
            if child.type == "block":
                return child
            # Handle decorated_definition: need to find the inner function first
            if child.type in ("function_definition", "class_definition"):
                return self._find_body_node(child)
        return None

    def _create_split_chunk(
        self,
        signature: str,
        nodes: list[Any],
        source_bytes: bytes,
        original_node: Any,
        parent_info: Optional[dict[str, Any]],
    ) -> TreeSitterChunk:
        """Create a single split chunk with signature prefix.

        Args:
            signature: Function signature to prefix
            nodes: List of AST nodes in this chunk
            source_bytes: Source code bytes
            original_node: Original function node (for metadata)
            parent_info: Parent class info

        Returns:
            TreeSitterChunk with prefixed content
        """
        # Get content from nodes
        start_byte = nodes[0].start_byte
        end_byte = nodes[-1].end_byte
        body_content = source_bytes[start_byte:end_byte].decode("utf-8")

        # Prefix with signature and docstring marker
        content = f"{signature}\n    # ... (split block)\n{body_content}"

        # Calculate lines
        start_line = nodes[0].start_point[0] + 1
        end_line = nodes[-1].end_point[0] + 1

        # Build metadata
        metadata = self.extract_metadata(original_node, source_bytes)
        metadata["split_block"] = True
        if parent_info:
            metadata.update(parent_info)

        parent_class_name = parent_info.get("parent_name") if parent_info else None

        return TreeSitterChunk(
            content=content,
            start_line=start_line,
            end_line=end_line,
            node_type="split_block",
            language=self.language_name,
            metadata=metadata,
            parent_class=parent_class_name,
        )

    def _split_large_node(
        self,
        node: Any,
        source_bytes: bytes,
        parent_info: Optional[dict[str, Any]],
        max_lines: int = 100,
        split_size_method: str = "characters",
        max_chars: int = 3000,
    ) -> list[TreeSitterChunk]:
        """Split a large function node at logical AST boundaries with size-based accumulation.

        Algorithm:
        1. Extract function signature for context prefix
        2. Find the function body block
        3. Accumulate nodes until size threshold reached
        4. Then split at nearest AST boundary
        5. Create chunks with signature prefix + accumulated statements

        Args:
            node: Tree-sitter node exceeding size threshold
            source_bytes: Source code bytes
            parent_info: Parent class information for methods
            max_lines: Maximum lines before split (for "lines" method)
            split_size_method: "lines" or "characters"
            max_chars: Maximum characters before split (for "characters" method)

        Returns:
            List of TreeSitterChunk objects with split content,
            or empty list if splitting not applicable
        """
        split_types = self._get_block_boundary_types()
        if not split_types:
            # No split types defined, return empty list
            return []

        # Extract signature and body
        signature = self._extract_signature(node, source_bytes)
        body_node = self._find_body_node(node)

        if not body_node:
            return []  # No body found, use default

        chunks = []
        current_nodes = []

        # Determine threshold based on method
        threshold = self._get_split_threshold(split_size_method, max_lines, max_chars)

        for child in body_node.children:
            # Check if adding this child would exceed threshold at a split boundary
            if current_nodes and child.type in split_types:
                # Calculate size with current child added
                test_nodes = current_nodes + [child]
                test_size = self._calculate_accumulated_size(
                    test_nodes, source_bytes, split_size_method
                )

                # If threshold exceeded, split BEFORE adding current child
                if test_size >= threshold:
                    chunk = self._create_split_chunk(
                        signature, current_nodes, source_bytes, node, parent_info
                    )
                    chunks.append(chunk)
                    current_nodes = [child]  # Start new chunk with current child
                    continue

            # Normal accumulation
            current_nodes.append(child)

        # Flush remaining nodes
        if current_nodes:
            chunk = self._create_split_chunk(
                signature, current_nodes, source_bytes, node, parent_info
            )
            chunks.append(chunk)

        # Only split if actually multiple chunks
        return chunks if len(chunks) > 1 else []

    def _get_split_threshold(
        self,
        method: str,
        max_lines: int,
        max_chars: int,
    ) -> int:
        """Determine the size threshold based on the split method.

        Args:
            method: Split size method ("lines" or "characters")
            max_lines: Maximum lines threshold
            max_chars: Maximum characters threshold

        Returns:
            The threshold value for the specified method
        """
        if method == "lines":
            return max_lines
        elif method == "characters":
            return max_chars
        return max_lines  # default fallback

    def _calculate_accumulated_size(
        self,
        nodes: list[Any],
        source_bytes: bytes,
        method: str,
    ) -> int:
        """Calculate the accumulated size of a list of AST nodes.

        Args:
            nodes: List of tree-sitter nodes
            source_bytes: Source code bytes
            method: Size calculation method ("lines" or "characters")

        Returns:
            The calculated size according to the specified method
        """
        if not nodes:
            return 0

        # Get text span from first to last node
        start = nodes[0].start_byte
        end = nodes[-1].end_byte
        text = source_bytes[start:end].decode("utf-8", errors="ignore")

        if method == "lines":
            return text.count("\n") + 1
        elif method == "characters":
            return estimate_characters(text)
        return text.count("\n") + 1  # default fallback

    def chunk_code(
        self,
        source_code: str,
        config: Optional["ChunkingConfig"] = None,
    ) -> list[TreeSitterChunk]:
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

        # Get config BEFORE traverse (needed for splitting decision in closure)
        if config is None:
            config = self._get_chunking_config()

        def traverse(node, depth=0, parent_info=None):
            """Recursively traverse the tree and extract chunks."""
            if self.should_chunk_node(node):
                start_line, end_line = self.get_line_numbers(node)
                node_lines = end_line - start_line + 1

                # Check if large node splitting is enabled and node exceeds threshold
                if (
                    config
                    and config.enable_large_node_splitting
                    and node_lines > config.max_chunk_lines
                    and node.type in ("function_definition", "decorated_definition")
                ):
                    split_chunks = self._split_large_node(
                        node,
                        source_bytes,
                        parent_info,
                        max_lines=config.max_chunk_lines,
                        split_size_method=config.split_size_method,
                        max_chars=config.max_split_chars,
                    )
                    if split_chunks:
                        chunks.extend(split_chunks)
                        return  # Don't create regular chunk or traverse children

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

        # Community merge happens during full index (graph-aware boundaries)
        # No greedy merge - raw AST chunks returned

        return chunks

    def _get_chunking_config(self) -> Optional["ChunkingConfig"]:
        """Get ChunkingConfig from ServiceLocator or direct config load.

        Returns:
            ChunkingConfig if available, None otherwise
        """
        # Try ServiceLocator first (MCP server context)
        try:
            from mcp_server.services import ServiceLocator

            config = ServiceLocator.instance().get_config()
            if config and config.chunking:
                return config.chunking
        except (ImportError, AttributeError):
            pass  # ServiceLocator not available, fall through to direct config

        # Fallback: Load config directly (batch indexing context)
        try:
            from search.config import get_search_config

            config = get_search_config()
            return config.chunking if config else None
        except (ImportError, AttributeError):
            return None
