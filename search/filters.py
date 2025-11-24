"""Directory and path filtering utilities for search operations.

This module provides shared filtering logic used across:
- HybridSearcher (search/hybrid_searcher.py)
- CodeIndexManager (search/indexer.py)
- CodeRelationshipAnalyzer (mcp_server/tools/code_relationship_analyzer.py)

Consolidated from three duplicate implementations as part of code organization refactoring.
"""

from typing import List, Optional


def normalize_path(path: str) -> str:
    """Normalize path separators for consistent matching.

    Args:
        path: File path with any separator style

    Returns:
        Path with forward slashes only
    """
    return path.replace("\\", "/")


def matches_directory_filter(
    relative_path: str,
    include_dirs: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
) -> bool:
    """Check if a file path matches directory filters.

    This is the canonical implementation for directory filtering across the codebase.
    Checks exclusions first (fast reject) then inclusions if specified.

    Args:
        relative_path: File path relative to project root
        include_dirs: If provided, path must start with one of these directories
        exclude_dirs: If provided, path must NOT start with any of these directories

    Returns:
        True if path passes both filters (not excluded AND matches include if specified)

    Examples:
        >>> matches_directory_filter("src/main.py", include_dirs=["src/"])
        True
        >>> matches_directory_filter("tests/test_main.py", exclude_dirs=["tests/"])
        False
        >>> matches_directory_filter("src/utils.py", include_dirs=["src/"], exclude_dirs=["src/vendor/"])
        True
    """
    # Normalize path separators
    normalized_path = normalize_path(relative_path)

    # Check exclusions first (fast reject)
    if exclude_dirs:
        for dir_pattern in exclude_dirs:
            # Ensure pattern ends with / for proper prefix matching
            pattern = normalize_path(dir_pattern).rstrip("/") + "/"
            if normalized_path.startswith(pattern):
                return False

    # Check inclusions (must match at least one)
    if include_dirs:
        for dir_pattern in include_dirs:
            pattern = normalize_path(dir_pattern).rstrip("/") + "/"
            if normalized_path.startswith(pattern):
                return True
        return False  # No include pattern matched

    return True  # No include filter, not excluded


class DirectoryFilter:
    """Reusable directory filter for batch operations.

    Provides a stateful wrapper around matches_directory_filter for efficient
    filtering of multiple paths with the same filter criteria.

    Attributes:
        include_dirs: Directories to include (None means all)
        exclude_dirs: Directories to exclude (None means none)

    Example:
        >>> filter = DirectoryFilter(include_dirs=["src/"], exclude_dirs=["src/vendor/"])
        >>> filter.matches("src/main.py")
        True
        >>> filter.matches("src/vendor/lib.py")
        False
        >>> filter.matches("tests/test_main.py")
        False
    """

    def __init__(
        self,
        include_dirs: Optional[List[str]] = None,
        exclude_dirs: Optional[List[str]] = None,
    ):
        """Initialize the directory filter.

        Args:
            include_dirs: List of directory prefixes to include
            exclude_dirs: List of directory prefixes to exclude
        """
        self.include_dirs = include_dirs
        self.exclude_dirs = exclude_dirs

    def matches(self, file_path: str) -> bool:
        """Check if a file path matches the filter criteria.

        Args:
            file_path: Path to check (relative or with normalized separators)

        Returns:
            True if the path should be included
        """
        return matches_directory_filter(file_path, self.include_dirs, self.exclude_dirs)

    def filter_paths(self, paths: List[str]) -> List[str]:
        """Filter a list of paths, returning only those that match.

        Args:
            paths: List of file paths to filter

        Returns:
            List of paths that pass the filter criteria
        """
        return [p for p in paths if self.matches(p)]

    def __repr__(self) -> str:
        return f"DirectoryFilter(include_dirs={self.include_dirs}, exclude_dirs={self.exclude_dirs})"
