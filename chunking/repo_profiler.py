"""Repository profiler for adaptive chunk sizing.

Performs a lightweight pre-indexing pass to analyze function size distribution
and cyclomatic complexity, enabling the adaptive sizing algorithm from:
  "A Comprehensive Analysis of Chunking Strategies for Code-Specific RAG Systems"

The profile drives two levels of adaptation:
  Level 1: P75 of function sizes → project-level baseline chunk size
  Level 2: Per-function complexity → modulate threshold up/down from baseline
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from statistics import quantiles
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Minimum number of functions needed for a meaningful profile
MIN_FUNCTIONS_FOR_PROFILE = 10

# File read size cap: skip giant files during profiling (same as chunking)
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@dataclass
class RepoProfile:
    """Statistical profile of a repository's function sizes.

    All size measurements use non-whitespace characters (cAST paper approach),
    which is language-agnostic and avoids indentation inflation.
    """

    function_count: int
    p25_chars: int  # 25th percentile
    p50_chars: int  # median
    p75_chars: int  # 75th percentile — the adaptive baseline
    p90_chars: int  # 90th percentile — split trigger reference
    mean_chars: int  # average function size
    max_complexity: int  # maximum cyclomatic complexity found (Python only)

    def __str__(self) -> str:
        return (
            f"RepoProfile({self.function_count} functions: "
            f"P25={self.p25_chars}, P50={self.p50_chars}, "
            f"P75={self.p75_chars}, P90={self.p90_chars}, "
            f"mean={self.mean_chars}, max_cc={self.max_complexity})"
        )


def profile_repository(
    project_path: str,
    supported_files: list[str],
) -> RepoProfile | None:
    """Profile a repository's function size and complexity distribution.

    Performs a lightweight AST scan — reuses the same tree-sitter parsers
    as the main chunking pipeline (TreeSitterChunker.get_chunker()), so
    no additional parsing infrastructure is needed.

    Args:
        project_path: Absolute path to the repository root
        supported_files: List of relative file paths to scan (already filtered
            by the indexer to supported extensions only)

    Returns:
        RepoProfile if >= 10 functions found, None otherwise (caller should
        fall back to static config defaults when None is returned)
    """
    # Import here to avoid circular imports at module level
    from chunking.tree_sitter import TreeSitterChunker

    chunker_dispatcher = TreeSitterChunker()

    sizes: list[int] = []  # Non-whitespace char counts per function
    complexities: list[int] = []  # Cyclomatic complexity (Python only)

    files_scanned = 0
    files_skipped = 0

    for rel_path in supported_files:
        abs_path = str(Path(project_path) / rel_path)

        # Skip files that are too large
        try:
            file_size = os.path.getsize(abs_path)
            if file_size > MAX_FILE_SIZE_BYTES:
                files_skipped += 1
                continue
        except OSError:
            files_skipped += 1
            continue

        # Get language-specific chunker (reuses cached parsers)
        chunker = chunker_dispatcher.get_chunker(abs_path)
        if chunker is None:
            continue

        # Read file content
        try:
            with open(abs_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            files_skipped += 1
            continue

        if not content.strip():
            continue

        # Parse and scan for function nodes
        try:
            source_bytes = bytes(content, "utf-8")
            tree = chunker.parser.parse(source_bytes)

            _scan_tree(
                tree.root_node,
                source_bytes,
                chunker,
                sizes,
                complexities,
            )
            files_scanned += 1
        except Exception as e:
            logger.debug(f"[PROFILER] Skipped {rel_path}: {e}")
            files_skipped += 1
            continue

    logger.info(
        f"[PROFILER] Scanned {files_scanned} files "
        f"({files_skipped} skipped), found {len(sizes)} functions"
    )

    if len(sizes) < MIN_FUNCTIONS_FOR_PROFILE:
        logger.info(
            f"[PROFILER] Too few functions ({len(sizes)} < {MIN_FUNCTIONS_FOR_PROFILE}) "
            "for meaningful profile — using static defaults"
        )
        return None

    # Calculate percentiles (statistics.quantiles uses inclusive interpolation)
    sorted_sizes = sorted(sizes)
    quants = quantiles(sorted_sizes, n=4)  # [P25, P50, P75]
    p90_idx = max(0, int(len(sorted_sizes) * 0.9) - 1)

    profile = RepoProfile(
        function_count=len(sizes),
        p25_chars=int(quants[0]),
        p50_chars=int(quants[1]),
        p75_chars=int(quants[2]),
        p90_chars=sorted_sizes[p90_idx],
        mean_chars=int(sum(sizes) / len(sizes)),
        max_complexity=max(complexities) if complexities else 1,
    )

    logger.info(f"[PROFILER] {profile}")
    return profile


def _scan_tree(
    root_node: object,
    source_bytes: bytes,
    chunker: object,
    sizes: list[int],
    complexities: list[int],
) -> None:
    """Recursively walk the AST, collecting function node sizes and complexities.

    Only collects top-level functions and methods (not nested functions) to
    avoid double-counting. Uses depth-first traversal matching chunk_code().

    Args:
        root_node: Tree-sitter root node
        source_bytes: Source bytes for text extraction
        chunker: LanguageChunker instance (provides splittable_node_types)
        sizes: Accumulator for non-whitespace character counts
        complexities: Accumulator for cyclomatic complexity scores (Python only)
    """
    from chunking.languages.base import estimate_characters

    function_node_types = _get_function_node_types(chunker)
    if not function_node_types:
        return

    def traverse(node: object, inside_function: bool = False) -> None:
        """Traverse tree, collecting function nodes at top scope only."""
        node_type = node.type  # type: ignore[attr-defined]

        is_function = node_type in function_node_types

        if is_function and not inside_function:
            # Measure this function
            start = node.start_byte  # type: ignore[attr-defined]
            end = node.end_byte  # type: ignore[attr-defined]
            text = source_bytes[start:end].decode("utf-8", errors="ignore")
            char_count = estimate_characters(text, count_whitespace=False)
            sizes.append(char_count)

            # Compute complexity for Python functions
            complexity = chunker.get_node_complexity(node)  # type: ignore[attr-defined]
            if complexity > 1:
                complexities.append(complexity)

            # Still traverse children (for class methods)
            # But mark as inside_function to avoid collecting nested functions
            for child in node.children:  # type: ignore[attr-defined]
                traverse(child, inside_function=True)
            return

        # For class nodes: traverse children to find methods
        if node_type in _get_class_node_types(chunker) and not inside_function:
            for child in node.children:  # type: ignore[attr-defined]
                traverse(child, inside_function=False)
            return

        # For non-function/class nodes: continue traversal
        if not inside_function:
            for child in node.children:  # type: ignore[attr-defined]
                traverse(child, inside_function=False)

    traverse(root_node)


def _get_function_node_types(chunker: object) -> frozenset[str]:
    """Get the set of AST node types that represent functions/methods.

    Filters splittable_node_types to exclude class-level types, since we
    want function sizes for the distribution analysis.
    """
    # Class-level node types to exclude from function measurement
    class_types = _get_class_node_types(chunker)

    splittable = getattr(chunker, "splittable_node_types", frozenset())
    return frozenset(t for t in splittable if t not in class_types)


def _get_class_node_types(chunker: object) -> frozenset[str]:
    """Get node types that represent class definitions."""
    # Common class node types across languages
    return frozenset(
        {
            "class_definition",  # Python
            "class_declaration",  # JavaScript, TypeScript, C#
            "class_specifier",  # C++
            "impl_item",  # Rust (impl block)
            "struct_item",  # Rust
            "interface_declaration",  # Go, TypeScript, C#
            "struct_declaration",  # Go, C#
        }
    )
