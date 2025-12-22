"""Directory and path filtering utilities for search operations.

This module provides shared filtering logic used across:
- HybridSearcher (search/hybrid_searcher.py)
- CodeIndexManager (search/indexer.py)
- CodeRelationshipAnalyzer (mcp_server/tools/code_relationship_analyzer.py)

Consolidated from three duplicate implementations as part of code organization refactoring.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


def normalize_path(path: str) -> str:
    """Normalize path separators for consistent matching.

    Args:
        path: File path with any separator style

    Returns:
        Path with forward slashes only
    """
    return path.replace("\\", "/")


def extract_drive_agnostic_path(path: str) -> str:
    """Extract path portion without drive letter on Windows.

    Args:
        path: Full file path (e.g., "F:\\Projects\\MyApp")

    Returns:
        Path without drive letter, normalized with forward slashes
        (e.g., "/Projects/MyApp")

    Examples:
        >>> extract_drive_agnostic_path("F:\\Projects\\MyApp")
        '/Projects/MyApp'
        >>> extract_drive_agnostic_path("F:/Projects/MyApp")
        '/Projects/MyApp'
        >>> extract_drive_agnostic_path("/home/user/projects")
        '/home/user/projects'
    """
    normalized = normalize_path(path)
    # Remove Windows drive letter (e.g., "F:/Projects" -> "/Projects")
    drive_pattern = r"^[A-Za-z]:/?"
    return re.sub(drive_pattern, "/", normalized)


def compute_drive_agnostic_hash(path: str, length: int = 8) -> str:
    """Compute MD5 hash from drive-agnostic path portion.

    This enables project indices to remain valid when external drives change
    drive letters (e.g., F: → E:). The hash is computed from the path portion
    after the drive letter, making it portable across drive assignments.

    Args:
        path: Full file path
        length: Hash length in characters (default 8)

    Returns:
        Truncated MD5 hash of drive-agnostic path

    Examples:
        >>> hash1 = compute_drive_agnostic_hash("F:/Projects/MyApp")
        >>> hash2 = compute_drive_agnostic_hash("E:/Projects/MyApp")
        >>> hash1 == hash2
        True
    """
    resolved = str(Path(path).resolve())
    agnostic_path = extract_drive_agnostic_path(resolved)
    return hashlib.md5(agnostic_path.encode()).hexdigest()[:length]


def compute_legacy_hash(path: str, length: int = 8) -> str:
    """Compute hash using legacy (full path) method for backward compatibility.

    This hash includes the drive letter, which was the original implementation.
    Used for finding existing indices created with earlier versions.

    Args:
        path: Full file path
        length: Hash length in characters (default 8)

    Returns:
        Truncated MD5 hash of full resolved path

    Examples:
        >>> hash1 = compute_legacy_hash("F:/Projects/MyApp")
        >>> hash2 = compute_legacy_hash("E:/Projects/MyApp")
        >>> hash1 != hash2
        True
    """
    resolved = str(Path(path).resolve())
    return hashlib.md5(resolved.encode()).hexdigest()[:length]


def find_project_at_different_drive(original_path: str) -> Optional[str]:
    """Find project at a different drive letter.

    Scans common removable drive letters to locate a project that may have
    moved when an external drive was reassigned a different letter.

    Args:
        original_path: Original stored path (e.g., "F:/Projects/MyApp")

    Returns:
        New path if found, None otherwise

    Examples:
        >>> # If project exists at E:/Projects/MyApp but was indexed at F:
        >>> find_project_at_different_drive("F:/Projects/MyApp")
        'E:/Projects/MyApp'
    """
    agnostic = extract_drive_agnostic_path(original_path)
    orig_name = Path(original_path).name

    # Check common removable drive letters (D-N covers most scenarios)
    for letter in "DEFGHIJKLMN":
        candidate = f"{letter}:{agnostic}"
        candidate_path = Path(candidate)
        if candidate_path.exists() and candidate_path.name == orig_name:
            return str(candidate_path.resolve())

    return None


def normalize_path_lower(path: str) -> str:
    """Normalize path separators and convert to lowercase.

    Useful for case-insensitive path matching and test file detection.

    Args:
        path: File path with any separator style

    Returns:
        Path with forward slashes only, lowercase

    Example:
        >>> normalize_path_lower("Tests\\Test_Main.PY")
        'tests/test_main.py'
    """
    return path.replace("\\", "/").lower()


def unescape_mcp_path(path: str) -> str:
    """Handle MCP JSON transport double-escape bug.

    The MCP JSON transport layer sometimes double-escapes backslashes,
    converting single backslashes to double backslashes. This utility
    handles both cases and normalizes to forward slashes.

    Args:
        path: File path that may have double-escaped backslashes

    Returns:
        Path with forward slashes only

    Example:
        >>> unescape_mcp_path("path\\\\to\\\\file.py")
        'path/to/file.py'
        >>> unescape_mcp_path("path\\to\\file.py")
        'path/to/file.py'
    """
    return path.replace("\\\\", "\\").replace("\\", "/")


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


# Known filter keys that have special handling
_KNOWN_FILTER_KEYS = {
    "include_dirs",
    "exclude_dirs",
    "file_pattern",
    "chunk_type",
    "tags",
    "folder_structure",
}


@dataclass
class FilterCriteria:
    """Unified filter criteria for search operations.

    Consolidates all filter types used across CodeIndexManager and HybridSearcher.
    Supports directory filtering, file patterns, chunk types, tags, and generic metadata matching.

    Attributes:
        include_dirs: Directories to include (None means all)
        exclude_dirs: Directories to exclude (None means none)
        file_pattern: File path patterns (substring match)
        chunk_type: Specific chunk type to match (function, class, method, etc.)
        tags: Tags that must be present (set intersection)
        folder_structure: Folder structure elements that must be present (set intersection)
        extra_filters: Generic key-value filters for metadata comparison
    """

    include_dirs: Optional[List[str]] = None
    exclude_dirs: Optional[List[str]] = None
    file_pattern: Optional[List[str]] = None  # Normalized to list
    chunk_type: Optional[str] = None
    tags: Optional[Set[str]] = None
    folder_structure: Optional[Set[str]] = None
    extra_filters: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, filters: Dict[str, Any]) -> "FilterCriteria":
        """Create FilterCriteria from a filter dictionary.

        Args:
            filters: Dictionary containing filter specifications

        Returns:
            FilterCriteria instance with normalized values
        """
        # Normalize file_pattern to list
        file_pattern = filters.get("file_pattern")
        if file_pattern is not None:
            if isinstance(file_pattern, str):
                file_pattern = [file_pattern]
            elif not isinstance(file_pattern, list):
                file_pattern = list(file_pattern)

        # Normalize tags to set
        tags = filters.get("tags")
        if tags is not None and not isinstance(tags, set):
            tags = set(tags) if isinstance(tags, (list, tuple)) else {tags}

        # Normalize folder_structure to set
        folder_structure = filters.get("folder_structure")
        if folder_structure is not None and not isinstance(folder_structure, set):
            folder_structure = (
                set(folder_structure)
                if isinstance(folder_structure, (list, tuple))
                else {folder_structure}
            )

        # Extract extra filters (any keys not in known filter keys)
        extra_filters = {
            k: v for k, v in filters.items() if k not in _KNOWN_FILTER_KEYS
        }

        return cls(
            include_dirs=filters.get("include_dirs"),
            exclude_dirs=filters.get("exclude_dirs"),
            file_pattern=file_pattern,
            chunk_type=filters.get("chunk_type"),
            tags=tags,
            folder_structure=folder_structure,
            extra_filters=extra_filters if extra_filters else None,
        )


class FilterEngine:
    """Unified filter engine for code search results.

    Consolidates filter logic from CodeIndexManager._matches_filters and
    HybridSearcher._matches_bm25_filters into a single, tested implementation.

    Supports:
    - Directory filtering (include/exclude with prefix matching)
    - File pattern matching (substring in relative path)
    - Chunk type filtering (exact match)
    - Tag intersection (must have overlapping tags)
    - Folder structure matching (must have overlapping folder elements)
    - Generic metadata comparison (arbitrary key-value filters)

    Example:
        >>> engine = FilterEngine.from_dict({
        ...     "include_dirs": ["src/"],
        ...     "chunk_type": "function",
        ...     "file_pattern": "utils"
        ... })
        >>> engine.matches({"relative_path": "src/utils.py", "chunk_type": "function"})
        True
    """

    def __init__(self, criteria: FilterCriteria):
        """Initialize FilterEngine with filter criteria.

        Args:
            criteria: FilterCriteria instance with normalized filter values
        """
        self.criteria = criteria

    @classmethod
    def from_dict(cls, filters: Dict[str, Any]) -> "FilterEngine":
        """Factory method to create FilterEngine from a filter dictionary.

        Args:
            filters: Dictionary containing filter specifications

        Returns:
            FilterEngine instance ready for filtering
        """
        return cls(FilterCriteria.from_dict(filters))

    def matches(self, metadata: Dict[str, Any]) -> bool:
        """Check if metadata matches all filter criteria.

        Applies filters in order of computational cost (fast reject first):
        1. Directory filter (fastest - prefix matching)
        2. File pattern (fast - substring search)
        3. Chunk type (fast - exact comparison)
        4. Tags (medium - set intersection)
        5. Folder structure (medium - set intersection)
        6. Extra filters (variable - depends on filter)

        Args:
            metadata: Chunk metadata dictionary to check

        Returns:
            True if metadata passes all filter criteria, False otherwise
        """
        if not self.criteria:
            return True

        # 1. Directory filter (fast reject)
        relative_path = metadata.get("relative_path", "")
        if not matches_directory_filter(
            relative_path, self.criteria.include_dirs, self.criteria.exclude_dirs
        ):
            return False

        # 2. File pattern (substring matching)
        if self.criteria.file_pattern:
            if not any(
                pattern in relative_path for pattern in self.criteria.file_pattern
            ):
                return False

        # 3. Chunk type (exact match)
        if self.criteria.chunk_type:
            if metadata.get("chunk_type") != self.criteria.chunk_type:
                return False

        # 4. Tags (set intersection)
        if self.criteria.tags:
            chunk_tags = set(metadata.get("tags", []))
            if not self.criteria.tags.intersection(chunk_tags):
                return False

        # 5. Folder structure (set intersection)
        if self.criteria.folder_structure:
            chunk_folders = set(metadata.get("folder_structure", []))
            if not self.criteria.folder_structure.intersection(chunk_folders):
                return False

        # 6. Generic key matching
        if self.criteria.extra_filters:
            for key, value in self.criteria.extra_filters.items():
                if key in metadata and metadata[key] != value:
                    return False

        return True

    def filter_results(
        self, results: List[Dict], metadata_key: str = "metadata"
    ) -> List[Dict]:
        """Filter a list of search results.

        Args:
            results: List of result dictionaries
            metadata_key: Key in each result containing metadata (default: "metadata")

        Returns:
            List of results that pass the filter criteria
        """
        return [r for r in results if self.matches(r.get(metadata_key, r))]


def get_effective_filters(project_info: dict) -> tuple:
    """Resolve default + user-defined filters from project_info.

    Uses current DEFAULT_IGNORED_DIRS for runtime filtering (always up-to-date),
    even though project_info.json stores a snapshot for transparency.

    Args:
        project_info: Dictionary containing filter information from project_info.json

    Returns:
        Tuple of (effective_include_dirs, effective_exclude_dirs)
        - effective_include_dirs: List of include directories or None
        - effective_exclude_dirs: List of exclude directories or None

    Migration Compatibility:
        - Supports old structure (include_dirs, exclude_dirs)
        - Supports new structure (user_included_dirs, user_excluded_dirs, default_excluded_dirs)
    """
    from chunking.multi_language_chunker import MultiLanguageChunker

    # Check for old structure (backward compatibility)
    if "exclude_dirs" in project_info and "user_excluded_dirs" not in project_info:
        # Old structure: treat as user-defined only
        include_dirs = project_info.get("include_dirs")
        exclude_dirs = project_info.get("exclude_dirs")
        return include_dirs, exclude_dirs

    # New structure: resolve default + user-defined
    # Resolve exclude dirs - use CURRENT defaults (not stored snapshot)
    exclude_dirs = list(MultiLanguageChunker.DEFAULT_IGNORED_DIRS)
    if project_info.get("user_excluded_dirs"):
        exclude_dirs.extend(project_info["user_excluded_dirs"])

    # Resolve include dirs (no default includes currently)
    include_dirs = project_info.get("user_included_dirs") or []

    return include_dirs or None, exclude_dirs or None
