"""Base classes for tree-sitter language chunkers.

This module contains the abstract base class and shared data structures
for all language-specific chunkers.
"""

from __future__ import annotations

import logging
from abc import ABC
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tree_sitter import Language, Parser


if TYPE_CHECKING:
    from chunking.repo_profiler import RepoProfile
    from search.config import ChunkingConfig

logger = logging.getLogger(__name__)


def compute_adaptive_threshold(
    complexity: int,
    base_threshold: int,
    max_complexity: int = 30,
    multiplier_max: float = 1.3,
    multiplier_min: float = 0.5,
    hard_cap: int = 8000,
) -> int:
    """Compute complexity-modulated chunk size threshold.

    Implements the research formula for adaptive chunk sizing:
      Cv = min(complexity / max_complexity, 1.0)   # normalize: 0=linear, 1=max
      T(Cv) = T_max - (T_max - T_min) × Cv         # high CC → smaller chunks

    Args:
        complexity: Cyclomatic complexity of the function (raw integer, min 1)
        base_threshold: Project baseline (P75 of function sizes) in non-whitespace chars
        max_complexity: Normalization ceiling — CC >= this → Cv = 1.0 (default 30)
        multiplier_max: T_max = base_threshold × this (for low-complexity code, default 1.3)
        multiplier_min: T_min = base_threshold × this (for high-complexity code, default 0.5)
        hard_cap: Absolute ceiling in non-whitespace chars (~2500-token context cliff, default 8000)

    Returns:
        Effective max_chars threshold, always in range [T_min, hard_cap]

    Examples:
        >>> compute_adaptive_threshold(1, 3000)   # linear code: ~3900 chars
        3858
        >>> compute_adaptive_threshold(15, 3000)  # moderate: ~2700 chars
        2700
        >>> compute_adaptive_threshold(30, 3000)  # complex: 1500 chars
        1500
    """
    cv = min(complexity / max(max_complexity, 1), 1.0)
    t_max = base_threshold * multiplier_max
    t_min = base_threshold * multiplier_min
    effective = t_max - (t_max - t_min) * cv
    return min(int(effective), hard_cap)


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
    # C-level non-whitespace count: str.split() drops runs of (Unicode) whitespace,
    # so joining the pieces back together and measuring their length avoids a
    # per-character Python-level generator. Parity with str.isspace() is exact in
    # CPython (both use the same Unicode whitespace definition).
    return len("".join(content.split()))


@dataclass
class TreeSitterChunk:
    """Represents a code chunk extracted using tree-sitter."""

    content: str
    start_line: int
    end_line: int
    node_type: str
    language: str
    metadata: dict[str, Any]
    chunk_id: str | None = None  # unique identifier for evaluation
    parent_class: str | None = None  # Enclosing class name for methods
    parent_chunk_id: str | None = None  # Enclosing class chunk_id for methods
    community_id: int | None = None  # Louvain community membership ID

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


class LanguageChunker(ABC):  # noqa: B024 — abstract by documentation; _extra_metadata is an intentional no-op hook
    """Abstract base class for language-specific chunkers."""

    def __init__(self, language_name: str, language: Language | None = None) -> None:
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
        """Load the tree-sitter language binding from the LANGUAGE_SPECS table.

        Reads the grammar spec for ``self.language_name`` from
        ``chunking.language_registry.LANGUAGE_SPECS`` and delegates to
        ``LanguageSpec.load_grammar()``.  Subclasses that need custom loading
        (e.g. TypeScriptChunker's tsx/non-tsx branching) can still override
        this method — but most leaves no longer need to.

        Returns:
            Language object

        Raises:
            ValueError: If the language spec or grammar package is not available.
        """
        from chunking.language_registry import LANGUAGE_SPECS  # avoid circular import

        spec = LANGUAGE_SPECS.get(self.language_name)
        if spec is None:
            raise ValueError(
                f"No LanguageSpec registered for {self.language_name!r}. "
                f"Add an entry to LANGUAGE_SPECS in chunking/language_registry.py."
            )
        return spec.load_grammar()  # type: ignore[return-value]

    def _get_splittable_node_types(self) -> set[str]:
        """Get node types that should be split into chunks.

        Reads ``splittable_node_types`` from the LANGUAGE_SPECS entry for
        ``self.language_name``.  Subclasses may still override this method
        if they need dynamic or context-sensitive node-type selection, but
        most leaves can rely on this default.

        Returns:
            Set of node type names

        Raises:
            ValueError: If no spec is registered for this language.
        """
        from chunking.language_registry import LANGUAGE_SPECS  # avoid circular import

        spec = LANGUAGE_SPECS.get(self.language_name)
        if spec is None:
            raise ValueError(
                f"No LanguageSpec registered for {self.language_name!r}. "
                f"Add an entry to LANGUAGE_SPECS in chunking/language_registry.py."
            )
        return set(spec.splittable_node_types)  # defensive copy

    #: Tuple of tree-sitter node type strings used by the default
    #: :meth:`extract_metadata` template to identify the name child.
    #: Defaults to ``("identifier",)`` — suitable for JS, Go, C#.
    #: Override to ``("identifier", "type_identifier")`` in leaves whose
    #: grammar uses ``type_identifier`` for type/struct names (Rust, TS).
    _NAME_ID_TYPES: tuple[str, ...] = ("identifier",)

    def extract_metadata(self, node: Any, source: bytes) -> dict[str, Any]:
        """Extract metadata from a node.

        Default template-method implementation:

        1. Seeds *metadata* with ``{"node_type": node.type}``.
        2. Finds the node name via :meth:`_extract_name` using
           :attr:`_NAME_ID_TYPES`.
        3. Delegates language-specific extras to :meth:`_extra_metadata`.
        4. Returns *metadata*.

        Complex leaves (C, C++, GLSL, Python) that need declarator-aware
        name logic override this method entirely.  Simple leaves (JS, TS,
        Go, Rust, C#) implement only :meth:`_extra_metadata`.

        Args:
            node: Tree-sitter node
            source: Source code bytes

        Returns:
            Metadata dictionary
        """
        metadata: dict[str, Any] = {"node_type": node.type}
        name = self._extract_name(node, source, id_types=self._NAME_ID_TYPES)
        if name is not None:
            metadata["name"] = name
        self._extra_metadata(node, source, metadata)
        return metadata

    def _extra_metadata(  # noqa: B027 — intentional no-op hook; complex leaves override extract_metadata instead
        self,
        node: Any,
        source: bytes,
        metadata: dict[str, Any],
    ) -> None:
        """Language-specific extras hook called by the template :meth:`extract_metadata`.

        Simple leaf chunkers implement this instead of overriding
        :meth:`extract_metadata` directly.  The *metadata* dict already
        contains ``node_type`` and ``name`` when this hook fires; add any
        additional keys in-place.

        Complex leaves that override :meth:`extract_metadata` entirely never
        call this hook — the default no-op body is never executed for them.

        Args:
            node: Tree-sitter node.
            source: Source code bytes.
            metadata: Mutable metadata dict to update in-place.
        """

    def get_node_complexity(self, node: Any) -> int:
        """Get cyclomatic complexity for a node.

        Default implementation returns 1 (no complexity info — treated as linear code).
        Override in language-specific chunkers that support complexity analysis.

        Args:
            node: Tree-sitter node (function_definition or similar)

        Returns:
            Cyclomatic complexity (minimum 1). Used by adaptive sizing to modulate
            chunk size thresholds — higher CC → smaller chunks.
        """
        return 1

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

    def _extract_name(
        self,
        node: Any,
        source: bytes,
        *,
        id_types: tuple[str, ...] = ("identifier",),
    ) -> str | None:
        """Find the first child whose type is in *id_types* and return its text.

        This is the shared name-finding loop used by simple leaf chunkers:
        walk ``node.children``, match the first child whose ``.type`` is in
        *id_types*, and return its decoded text.

        Complex leaves (C, C++, GLSL, Python) that need declarator-aware or
        typedef/template traversal should keep their own name logic instead of
        calling this helper.

        Args:
            node: Tree-sitter node whose children to search.
            source: Source code bytes.
            id_types: Tuple of tree-sitter node type strings to match.
                Defaults to ``("identifier",)`` (Pattern 1 — JS, Go, C#).
                Pass ``("identifier", "type_identifier")`` for Pattern 2 — Rust, TS.

        Returns:
            Decoded text of the first matching child, or ``None`` if not found.
        """
        for child in node.children:
            if child.type in id_types:
                return self.get_node_text(child, source)
        return None

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
        current_parent: str | None = None
        current_community: int | None = None  # Current community for boundary detection
        total_size_estimated: int = 0  # Track for summary logging

        current_file: str | None = None  # Track file path to prevent cross-file merging

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
                # Use community_id as merge boundary
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
            current_community = (
                chunk_community  # Update for community boundary detection
            )
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

    def _find_body_node(self, node: Any) -> Any | None:
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
        parent_info: dict[str, Any] | None,
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
        parent_info: dict[str, Any] | None,
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
        config: ChunkingConfig | None = None,
        repo_profile: RepoProfile | None = None,
    ) -> list[TreeSitterChunk]:
        """Chunk source code into semantic units.

        Back-compat adapter: parses `source_code` and delegates to
        `chunk_parsed`. Callers that already hold a parsed tree (e.g. the
        repo-profiling pass, via TreeSitterChunker.parse_file) should call
        `chunk_parsed` directly to avoid re-parsing the same source.

        Args:
            source_code: Source code string
            config: Optional ChunkingConfig for merge settings.
                    If None, uses ServiceLocator to get global config.
            repo_profile: Optional RepoProfile for adaptive chunk sizing.
                    When provided and config.sizing_mode == "adaptive", chunk size
                    thresholds are adjusted per-function based on P75 baseline and
                    cyclomatic complexity.

        Returns:
            List of TreeSitterChunk objects (may include merged chunks)
        """
        source_bytes = bytes(source_code, "utf-8")
        tree = self.parser.parse(source_bytes)
        return self.chunk_parsed(
            tree, source_code, config=config, repo_profile=repo_profile
        )

    def chunk_parsed(
        self,
        tree: Any,
        source_code: str,
        config: ChunkingConfig | None = None,
        repo_profile: RepoProfile | None = None,
    ) -> list[TreeSitterChunk]:
        """Chunk an already-parsed tree into semantic units.

        Same behavior as `chunk_code`, but takes a pre-parsed tree-sitter
        `Tree` instead of parsing `source_code` itself — lets callers that
        already produced a tree (e.g. via TreeSitterChunker.parse_file) skip
        the redundant parse.

        Args:
            tree: tree_sitter.Tree parsed from `source_code` by this chunker's
                    `self.parser` (must be produced on the current thread —
                    tree-sitter Tree/Node objects are not thread-safe).
            source_code: The source code string `tree` was parsed from.
            config: Optional ChunkingConfig for merge settings.
                    If None, uses ServiceLocator to get global config.
            repo_profile: Optional RepoProfile for adaptive chunk sizing.
                    When provided and config.sizing_mode == "adaptive", chunk size
                    thresholds are adjusted per-function based on P75 baseline and
                    cyclomatic complexity.

        Returns:
            List of TreeSitterChunk objects (may include merged chunks)
        """
        source_bytes = bytes(source_code, "utf-8")
        chunks = []

        # Get config BEFORE traverse (needed for splitting decision in closure)
        if config is None:
            config = self._get_chunking_config()

        def traverse(
            node: Any, depth: int = 0, parent_info: dict | None = None
        ) -> None:
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
                    # Determine effective split threshold:
                    # - "fixed" mode: use static max_split_chars from config
                    # - "adaptive" mode: modulate based on P75 baseline + complexity
                    effective_max_chars = config.max_split_chars
                    if (
                        config.sizing_mode == "adaptive"
                        and repo_profile is not None
                        and repo_profile.p75_chars > 0
                    ):
                        complexity = self.get_node_complexity(node)
                        effective_max_chars = compute_adaptive_threshold(
                            complexity=complexity,
                            base_threshold=repo_profile.p75_chars,
                            max_complexity=repo_profile.max_complexity
                            or config.max_complexity_cap,
                            multiplier_max=config.adaptive_multiplier_max,
                            multiplier_min=config.adaptive_multiplier_min,
                        )
                        logger.debug(
                            f"[ADAPTIVE] node CC={complexity}, P75={repo_profile.p75_chars}, "
                            f"threshold={effective_max_chars} (static={config.max_split_chars})"
                        )

                    split_chunks = self._split_large_node(
                        node,
                        source_bytes,
                        parent_info,
                        max_lines=config.max_chunk_lines,
                        split_size_method=config.split_size_method,
                        max_chars=effective_max_chars,
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

        # Fix A: top-of-file executable statements (import-time side effects,
        # module constants, `if __name__ == "__main__":` guards, etc.) sit
        # between chunked def/class nodes at the root level and would
        # otherwise never be emitted as a chunk — only `should_chunk_node`
        # types are chunkable, so bare statements are invisible to semantic
        # search even though the synthetic file-summary chunk never contains
        # their actual text (see chunking/file_summarizer.py). Collect
        # contiguous root-level runs of such statements as real, line-numbered
        # chunks, distinct from the synthetic "module" summary type so they
        # are never subject to synthetic-chunk demotion/exclusion logic
        # (search/graph_scoring_stage.py, search/centrality_ranker.py, etc.).
        chunks.extend(
            self._collect_module_preamble_chunks(tree.root_node, source_bytes)
        )

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

    # Node types that make a root-level statement run boilerplate-only (safe to
    # skip) when they're the *entire* run — imports carry no side effects and
    # are already surfaced via the file-summary chunk's import list. A run
    # containing anything else (assignments, calls, control flow, side-effecting
    # expressions) is emitted as a real chunk.
    _PREAMBLE_BOILERPLATE_TYPES = frozenset(
        {
            "comment",
            "import_statement",
            "import_from_statement",
            "future_import_statement",
        }
    )

    def _collect_module_preamble_chunks(
        self, root_node: Any, source_bytes: bytes
    ) -> list[TreeSitterChunk]:
        """Collect contiguous root-level statement runs not covered by
        function/class/decorated_definition chunking (Fix A).

        Bare top-of-file statements (import-time side effects, module
        constants, `if __name__ == "__main__":` guards, ...) sit between
        chunked def/class nodes but have no chunkable ancestor type, so
        ``traverse`` never emits them. This collects them as distinct,
        line-numbered ``module_preamble`` chunks.

        Only inspects *direct* children of the module root — non-chunkable
        code nested inside e.g. an `if TYPE_CHECKING:` guard is out of scope;
        the reported gap was specifically top-of-file statements.

        Args:
            root_node: The tree-sitter root node (whole file).
            source_bytes: UTF-8-encoded source, for verbatim byte-range slicing.

        Returns:
            One chunk per contiguous run that contains more than
            imports/comments/docstring text; empty list if every run is
            boilerplate-only (e.g. an imports-only file).
        """
        preamble_chunks: list[TreeSitterChunk] = []
        run_nodes: list[Any] = []

        def flush() -> None:
            if not run_nodes or self._is_boilerplate_run(run_nodes):
                run_nodes.clear()
                return
            start_line = run_nodes[0].start_point[0] + 1
            end_line = run_nodes[-1].end_point[0] + 1
            content = source_bytes[
                run_nodes[0].start_byte : run_nodes[-1].end_byte
            ].decode("utf-8", errors="replace")
            if not any(ch.isalnum() for ch in content):
                # Punctuation-only leftover (e.g. an orphan trailing `;` after
                # a struct/typedef declaration whose body was already chunked
                # separately) — nothing worth indexing.
                run_nodes.clear()
                return
            preamble_chunks.append(
                TreeSitterChunk(
                    content=content,
                    start_line=start_line,
                    end_line=end_line,
                    node_type="module_preamble",
                    language=self.language_name,
                    metadata={"type": "module_preamble"},
                )
            )
            run_nodes.clear()

        for child in root_node.children:
            if self._child_is_chunked(child):
                flush()
                continue
            run_nodes.append(child)
        flush()

        return preamble_chunks

    def _child_is_chunked(self, node: Any) -> bool:
        """True if `traverse()` would emit a chunk for `node` or a descendant.

        Mirrors `traverse()`'s recursive fall-through: a root child that is
        itself non-chunkable (e.g. TS/JS `export_statement`) still has its
        children visited, so its wrapped `function_declaration`/
        `class_declaration` gets chunked independently. Without this check,
        the preamble collector would re-capture that already-chunked content
        verbatim as a duplicate `module_preamble` chunk (observed for the TS
        fixture: the whole file re-appeared as one giant preamble chunk on
        top of its already-correct per-symbol chunks).
        """
        if self.should_chunk_node(node):
            return True
        return any(self._child_is_chunked(child) for child in node.children)

    def _is_boilerplate_run(self, nodes: list[Any]) -> bool:
        """True if a root-level statement run is only imports/comments/docstring.

        Such runs carry no side effects worth indexing separately as a
        preamble chunk — imports are already surfaced via the file-summary
        chunk's import list, and a bare docstring-only ``expression_statement``
        (a lone ``string`` child) has no executable content.
        """
        for node in nodes:
            # Comment node type names vary by grammar (Python/JS/TS/C/C++/Go/
            # GLSL/C# all use "comment"; Rust splits it into "line_comment"/
            # "block_comment") — substring match instead of an exhaustive enum.
            if "comment" in node.type:
                continue
            if node.type in self._PREAMBLE_BOILERPLATE_TYPES:
                continue
            if (
                node.type == "expression_statement"
                and len(node.children) == 1
                and node.children[0].type == "string"
            ):
                continue  # bare docstring/comment-as-string
            return False
        return True

    def _get_chunking_config(self) -> ChunkingConfig | None:
        """Get ChunkingConfig from the current search config, or None if unavailable."""
        from search.config import get_chunking_config

        return get_chunking_config()
