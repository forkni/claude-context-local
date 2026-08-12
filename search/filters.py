"""Directory and path filtering utilities for search operations.

This module provides shared filtering logic used across:
- HybridSearcher (search/hybrid_searcher.py)
- CodeIndexManager (search/indexer.py)
- CodeRelationshipAnalyzer (mcp_server/tools/code_relationship_analyzer.py)

Consolidated from three duplicate implementations as part of code organization refactoring.
"""

import fnmatch
import hashlib
import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from chunking.language_registry import DEFAULT_IGNORED_DIRS, DEPENDENCY_TREE_DIRS
from utils.path_utils import normalize_path


logger = logging.getLogger(__name__)


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


def find_project_at_different_drive(original_path: str) -> str | None:
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


# ---------------------------------------------------------------------------
# Pattern engine — gitignore-style include/exclude patterns for indexing-time
# directory filtering.
#
# This replaces the four independent "should I ignore this path" gates that
# used to disagree with each other (MerkleDAG.should_ignore,
# IncrementalIndexer._is_supported_file/_add_new_chunks,
# MultiLanguageChunker.chunk_directory) with a single precedence-ordered
# resolver: PathFilter. See docs/plans (filter-override fix) for the full
# design rationale — in short:
#   - An explicit include_dirs entry can re-admit a directory that
#     DEFAULT_IGNORED_DIRS would otherwise prune (e.g. "venv", "site-packages").
#   - Includes admit only their own target subtree, never ancestor files.
#   - exclude_dirs always wins over include_dirs.
#   - Patterns support absolute paths (resolved against the project root) and
#     gitignore-style wildcards: a separator-free pattern matches its basename
#     at ANY depth; a pattern containing "/" (or a leading "/") is anchored to
#     the project root.
#
# DirectoryFilter/matches_directory_filter below are UNCHANGED and remain the
# implementation for search-time result filtering (HybridSearcher,
# CodeIndexManager, CodeRelationshipAnalyzer), which filters already-relative
# chunk metadata paths and has no project-root/filesystem-walk concept. Only
# the indexing-time gates listed above are routed through PathFilter.
# ---------------------------------------------------------------------------


class MatchKind(Enum):
    """Result of matching a single DirPattern against a path's segments."""

    NONE = "none"  # Pattern cannot match this path or anything under it (yet)
    ANCESTOR = "ancestor"  # Path is a parent of the pattern's target — keep descending
    INSIDE = "inside"  # Path is at or under the pattern's target — matched


@dataclass(frozen=True)
class DirPattern:
    """A single parsed include/exclude pattern.

    Attributes:
        raw: The exact string the user supplied — kept for logs, diagnostics,
            and persistence (project_info.json stores raw strings, not this).
        segments: Normalized, forward-slash path segments with no empty parts.
            Unanchored patterns always have exactly one segment.
        anchored: True when the pattern must match starting at the project
            root (it contained a "/", started with "/", or was an absolute
            path resolved against the root). False when it matches its single
            segment as a basename at any depth.
        has_wildcard: True if the pattern contains glob metacharacters
            (*, ?, [). Informational — matching always goes through fnmatch,
            wildcard or not, so this doesn't gate behavior.
    """

    raw: str
    segments: tuple[str, ...]
    anchored: bool
    has_wildcard: bool


def parse_dir_pattern(raw: str, root_path: str | Path | None) -> DirPattern | None:
    """Parse a raw include/exclude string into a DirPattern.

    Handles the MCP JSON double-backslash transport bug, absolute paths
    (resolved against root_path — dropped with a warning if they fall outside
    the project root), "./" and leading/trailing "/" normalization, and
    gitignore-style anchoring (a "/" anywhere in the pattern anchors it to the
    root; no separator means "match this basename at any depth").

    Args:
        raw: The user-supplied pattern string.
        root_path: Project root, used to resolve absolute patterns. Absolute
            patterns are dropped (with a warning) if root_path is None.

    Returns:
        A DirPattern, or None if the pattern is empty/unresolvable — callers
        must not silently treat None as "matches everything"; it means "this
        pattern was dropped and will never match" (a warning was already
        logged).
    """
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None

    normalized = unescape_mcp_path(stripped)
    anchored = False

    is_unc = normalized.startswith("//")
    is_windows_drive = bool(re.match(r"^[A-Za-z]:/", normalized))
    is_posix_abs = normalized.startswith("/") and not is_unc

    if is_windows_drive or is_unc or is_posix_abs:
        if root_path is None:
            logger.warning(
                f"[PATH_FILTER] Absolute pattern '{raw}' given without a "
                "project root — dropping it (it will never match)"
            )
            return None
        try:
            abs_path = Path(normalized).resolve()
            root_resolved = Path(root_path).resolve()
            rel = abs_path.relative_to(root_resolved)
        except (ValueError, OSError):
            logger.warning(
                f"[PATH_FILTER] Absolute pattern '{raw}' does not resolve "
                f"under project root '{root_path}' — dropping it (it will "
                "never match)"
            )
            return None
        normalized = rel.as_posix()
        anchored = True

    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/"):
        anchored = True
        normalized = normalized.lstrip("/")
    normalized = normalized.rstrip("/")

    if not normalized:
        logger.warning(
            f"[PATH_FILTER] Pattern '{raw}' normalizes to empty — dropping it"
        )
        return None

    anchored = anchored or ("/" in normalized)
    has_wildcard = any(c in normalized for c in "*?[")
    segments = tuple(normalized.split("/"))

    return DirPattern(
        raw=raw, segments=segments, anchored=anchored, has_wildcard=has_wildcard
    )


def is_dependency_pattern(pattern: DirPattern) -> bool:
    """Whether an include pattern reaches into a dependency/package tree.

    A pattern is "additive" (re-admits a slice of a normally-ignored
    dependency tree on top of the regular root-down scope) iff any of its
    path segments names a dependency-tree directory, e.g.
    "venv/Lib/site-packages/torch" contains both "venv" and "site-packages".
    A pattern with no such segment (e.g. "src/core") is "narrowing" — it
    restricts the whole indexed scope to just the paths it names.

    Deliberately conservative: a bare "torch" (no dependency segment) stays
    narrowing, since there's no way to tell whether it means
    "site-packages/torch" or a source directory named "torch".
    """
    return any(seg in DEPENDENCY_TREE_DIRS for seg in pattern.segments)


def _segment_matches(pattern_seg: str, path_seg: str) -> bool:
    """Match one path segment against one pattern segment.

    Uses fnmatch.fnmatch (not fnmatchcase) so case-folding follows
    os.path.normcase automatically — case-insensitive on Windows,
    case-sensitive on POSIX — matching the OS's own filesystem semantics.
    """
    return fnmatch.fnmatch(path_seg, pattern_seg)


def _combine(a: MatchKind, b: MatchKind) -> MatchKind:
    """Combine two MatchKind results, preferring the stronger match."""
    if a is MatchKind.INSIDE or b is MatchKind.INSIDE:
        return MatchKind.INSIDE
    if a is MatchKind.ANCESTOR or b is MatchKind.ANCESTOR:
        return MatchKind.ANCESTOR
    return MatchKind.NONE


def _match_rec(
    pat: tuple[str, ...], pi: int, parts: tuple[str, ...], si: int
) -> MatchKind:
    """Backtracking matcher for anchored patterns containing '**'.

    '**' matches zero or more path segments. Only invoked when a pattern
    actually contains '**' — the common case (no wildcard segments) uses the
    fast iterative path in _match_anchored instead.
    """
    if pi == len(pat):
        return MatchKind.INSIDE
    if pat[pi] == "**":
        zero = _match_rec(pat, pi + 1, parts, si)
        if si >= len(parts):
            return zero
        one = _match_rec(pat, pi, parts, si + 1)
        return _combine(zero, one)
    if si >= len(parts):
        return MatchKind.ANCESTOR
    if not _segment_matches(pat[pi], parts[si]):
        return MatchKind.NONE
    return _match_rec(pat, pi + 1, parts, si + 1)


def _match_anchored(pat_segs: tuple[str, ...], parts: tuple[str, ...]) -> MatchKind:
    """Match an anchored (root-relative) pattern against path segments."""
    if "**" not in pat_segs:
        pattern_len = len(pat_segs)
        parts_len = len(parts)
        limit = min(pattern_len, parts_len)
        for i in range(limit):
            if not _segment_matches(pat_segs[i], parts[i]):
                return MatchKind.NONE
        return MatchKind.INSIDE if parts_len >= pattern_len else MatchKind.ANCESTOR

    return _match_rec(pat_segs, 0, parts, 0)


def _match_unanchored(pat_segs: tuple[str, ...], parts: tuple[str, ...]) -> MatchKind:
    """Match an unanchored (basename-any-depth) single-segment pattern."""
    s0 = pat_segs[0]
    for part in parts:
        if _segment_matches(s0, part):
            return MatchKind.INSIDE
    # No segment along this path matched yet, but a deeper descendant might.
    return MatchKind.ANCESTOR


def match_pattern(pattern: DirPattern, rel_parts: tuple[str, ...]) -> MatchKind:
    """Match a parsed pattern against a path's relative segments.

    Args:
        pattern: A DirPattern from parse_dir_pattern().
        rel_parts: The candidate path's components relative to the project
            root, e.g. ("StreamDiffusion", "venv", "Lib", "site-packages",
            "diffusers", "foo.py").

    Returns:
        MatchKind.INSIDE if rel_parts is at or under the pattern's target,
        MatchKind.ANCESTOR if rel_parts is a parent of the target (so a
        directory walk should keep descending), MatchKind.NONE otherwise.
    """
    if pattern.anchored:
        return _match_anchored(pattern.segments, rel_parts)
    return _match_unanchored(pattern.segments, rel_parts)


# Directories that can never be re-admitted by an include pattern, regardless
# of user configuration — unlike DEFAULT_IGNORED_DIRS, which an include can
# override.
ALWAYS_IGNORED_DIRS: set[str] = {".git", ".hg", ".svn"}


class PathFilter:
    """Single source of truth for indexing-time include/exclude/default-ignore
    precedence.

    Replaces the four gates that used to independently reimplement (and
    disagree on) this logic: MerkleDAG.should_ignore,
    IncrementalIndexer._is_supported_file / _add_new_chunks, and
    MultiLanguageChunker.chunk_directory.

    Decision order (identical for should_traverse_dir/should_index_file,
    only the include requirement in step 3 differs):
      1. Basename in ALWAYS_IGNORED_DIRS -> reject, unconditionally.
      2. Any exclude pattern is INSIDE -> reject (exclude beats include).
      3. If narrowing include patterns are configured: a file requires
         INSIDE; a directory requires INSIDE or ANCESTOR. Otherwise ->
         reject. "Narrowing" patterns are include patterns that do NOT
         reach into a dependency tree (see is_dependency_pattern) — e.g.
         "src/core". Patterns that DO (e.g. "venv/Lib/site-packages/torch")
         are "additive" and skip this step entirely, so they only ever
         widen scope via step 4, never restrict it. `include_exclusive=True`
         disables this distinction and treats every include pattern as
         narrowing, matching pre-additive behavior exactly.
      4. Basename in `defaults` -> reject, UNLESS the path is INSIDE or
         ANCESTOR of an include pattern (this is what lets an explicit
         include re-admit "venv", "site-packages", etc.).
      5. Accept.
    """

    def __init__(
        self,
        include_dirs: list[str] | None,
        exclude_dirs: list[str] | None,
        root_path: str | Path,
        *,
        defaults: set[str] | None = None,
        include_exclusive: bool = False,
    ) -> None:
        """Build a filter for one project root.

        Args:
            include_dirs: Raw user include patterns (may be None/empty).
            exclude_dirs: Raw user exclude patterns (may be None/empty).
            root_path: Project root — used to resolve absolute patterns and
                as the base for relative-segment matching.
            defaults: Overridable default-ignored basenames. Defaults to
                DEFAULT_IGNORED_DIRS (chunking/language_registry.py).
            include_exclusive: When True, every include pattern is treated
                as narrowing (the whitelist-only behavior from before
                additive dependency-tree patterns existed), even ones that
                reach into a dependency tree. Escape hatch for "index ONLY
                these libraries" — a case additive-by-default can no longer
                express on its own.
        """
        self.root_path = Path(root_path)
        self._defaults = defaults if defaults is not None else DEFAULT_IGNORED_DIRS
        self.include_exclusive = include_exclusive
        self.include_patterns = self._parse_all(include_dirs)
        self.exclude_patterns = self._parse_all(exclude_dirs)
        if include_exclusive:
            self.narrowing_patterns = self.include_patterns
            self.additive_patterns: list[DirPattern] = []
        else:
            self.narrowing_patterns = [
                p for p in self.include_patterns if not is_dependency_pattern(p)
            ]
            self.additive_patterns = [
                p for p in self.include_patterns if is_dependency_pattern(p)
            ]
        # Per-pattern hit counters, used for zero-match diagnostics (a pattern
        # that never matched anything — e.g. a typo'd package name — must be
        # reported loudly, not silently dropped).
        self.include_hits: dict[str, int] = dict.fromkeys(
            (p.raw for p in self.include_patterns), 0
        )
        self.exclude_hits: dict[str, int] = dict.fromkeys(
            (p.raw for p in self.exclude_patterns), 0
        )

    def _parse_all(self, raw_list: list[str] | None) -> list[DirPattern]:
        if not raw_list:
            return []
        parsed = []
        for raw in raw_list:
            pat = parse_dir_pattern(raw, self.root_path)
            if pat is not None:
                parsed.append(pat)
        return parsed

    @staticmethod
    def _rel_parts(rel_path: str) -> tuple[str, ...]:
        normalized = normalize_path(str(rel_path)).strip("/")
        if not normalized or normalized == ".":
            return ()
        return tuple(normalized.split("/"))

    @staticmethod
    def _best_match(
        patterns: list[DirPattern], rel_parts: tuple[str, ...]
    ) -> tuple[MatchKind, "DirPattern | None"]:
        """Return the strongest match across all patterns (INSIDE beats ANCESTOR)."""
        best_kind = MatchKind.NONE
        best_pattern = None
        for pat in patterns:
            kind = match_pattern(pat, rel_parts)
            if kind is MatchKind.INSIDE:
                return MatchKind.INSIDE, pat
            if kind is MatchKind.ANCESTOR and best_kind is MatchKind.NONE:
                best_kind = MatchKind.ANCESTOR
                best_pattern = pat
        return best_kind, best_pattern

    def _classify(
        self, rel_path: str, *, is_dir: bool
    ) -> tuple[bool, "DirPattern | None", MatchKind]:
        rel_parts = self._rel_parts(rel_path)

        # Checked across ALL segments (not just the basename) so this stays
        # correct for callers that check a file directly without having
        # walked/pruned its ancestor chain first (e.g. IncrementalIndexer's
        # per-file gates operating on a flat change list) — not just for the
        # recursive MerkleDAG walk, where each ancestor is already vetted one
        # level at a time by the time a leaf is reached.
        if any(part in ALWAYS_IGNORED_DIRS for part in rel_parts):
            return False, None, MatchKind.NONE

        exclude_kind, exclude_pat = self._best_match(self.exclude_patterns, rel_parts)
        if exclude_kind is MatchKind.INSIDE:
            if exclude_pat is not None:
                self.exclude_hits[exclude_pat.raw] += 1
            return False, None, MatchKind.NONE

        # include_kind/include_pat are always matched against ALL include
        # patterns (narrowing + additive combined) — step 4's re-admission
        # below needs to see additive patterns even when no narrowing
        # pattern is configured. Only the requirement gate immediately below
        # is conditional, and it's gated on narrowing_patterns specifically:
        # an all-additive include list (e.g. the site-packages-only case)
        # must NOT force every file to match one of those patterns, or the
        # whole point of "additive" collapses back into "whitelist".
        include_kind = MatchKind.NONE
        include_pat = None
        if self.include_patterns:
            include_kind, include_pat = self._best_match(
                self.include_patterns, rel_parts
            )
        if self.narrowing_patterns:
            required = (
                (MatchKind.INSIDE, MatchKind.ANCESTOR)
                if is_dir
                else (MatchKind.INSIDE,)
            )
            if include_kind not in required:
                return False, None, MatchKind.NONE

        if any(part in self._defaults for part in rel_parts) and include_kind not in (
            MatchKind.INSIDE,
            MatchKind.ANCESTOR,
        ):
            return False, None, MatchKind.NONE

        return True, include_pat, include_kind

    def should_traverse_dir(self, rel_path: str) -> bool:
        """Whether the walker should descend into this directory."""
        allowed, _, _ = self._classify(rel_path, is_dir=True)
        return allowed

    def should_index_file(self, rel_path: str) -> bool:
        """Whether this file should be indexed."""
        allowed, include_pat, include_kind = self._classify(rel_path, is_dir=False)
        if allowed and include_kind is MatchKind.INSIDE and include_pat is not None:
            self.include_hits[include_pat.raw] += 1
        return allowed

    def unmatched_patterns(self) -> list[str]:
        """Raw include/exclude patterns that matched zero indexed files."""
        unmatched = [raw for raw, count in self.include_hits.items() if count == 0]
        unmatched += [raw for raw, count in self.exclude_hits.items() if count == 0]
        return unmatched

    def all_includes_unmatched(self) -> bool:
        """True if include patterns were configured but none matched anything."""
        return bool(self.include_patterns) and all(
            count == 0 for count in self.include_hits.values()
        )

    def only_dependency_paths_matched(self, rel_paths: list[str]) -> bool:
        """True if narrowing is active and every matched path is dependency-only.

        The residual failure mode Part 1's additive-by-default classification
        cannot catch: a *narrowing* include pattern (e.g. bare "torch", which
        has no dependency-tree segment of its own so isn't classified as
        additive) — or the ``include_exclusive`` escape hatch, which forces
        *every* pattern back to narrowing — can still happen to resolve
        entirely inside a dependency tree, silently wiping first-party
        source exactly like the original incident.

        Short-circuits on the first path that does NOT contain a
        dependency-tree segment (a first-party file survived — nothing to
        guard against). Vacuously False when no narrowing patterns are
        active (Part 1 already guarantees additive-only include sets can't
        discard source) or when ``rel_paths`` is empty (an empty result is
        ``all_includes_unmatched``'s problem, not this one's).

        Args:
            rel_paths: The final matched/supported file paths for this run
                (OS-native separators are fine — routed through
                ``_rel_parts``/``normalize_path`` same as everywhere else).
        """
        if not self.narrowing_patterns or not rel_paths:
            return False
        for rel_path in rel_paths:
            if not any(
                part in DEPENDENCY_TREE_DIRS for part in self._rel_parts(rel_path)
            ):
                return False
        return True

    def dependency_segments(self, rel_paths: list[str]) -> list[str]:
        """Dependency-tree segment names actually present across rel_paths.

        For an actionable guard message naming exactly what swallowed the
        project (e.g. ``["site-packages", "venv"]``) instead of a generic
        "nothing but libraries matched".
        """
        found: set[str] = set()
        for rel_path in rel_paths:
            for part in self._rel_parts(rel_path):
                if part in DEPENDENCY_TREE_DIRS:
                    found.add(part)
        return sorted(found)


def matches_directory_filter(
    relative_path: str,
    include_dirs: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
    is_traversal: bool = False,
) -> bool:
    """Check if a file path matches directory filters.

    This is the canonical implementation for directory filtering across the codebase.
    Checks exclusions first (fast reject) then inclusions if specified.

    Args:
        relative_path: File path relative to project root
        include_dirs: If provided, path must be in or be an ancestor of these directories
        exclude_dirs: If provided, path must NOT start with any of these directories
        is_traversal: If True, allows ancestor directories of include_dirs to pass through.
                     This enables tree traversal to reach nested include targets.

    Returns:
        True if path passes both filters (not excluded AND matches include if specified)

    Examples:
        >>> matches_directory_filter("src/main.py", include_dirs=["src/"])
        True
        >>> matches_directory_filter("tests/test_main.py", exclude_dirs=["tests/"])
        False
        >>> matches_directory_filter("src/utils.py", include_dirs=["src/"], exclude_dirs=["src/vendor/"])
        True
        >>> # Traversal mode: ancestor directories pass through
        >>> matches_directory_filter("Scripts/", include_dirs=["Scripts/StreamDiffusionTD/"], is_traversal=True)
        True
    """
    # Normalize path separators
    normalized_path = normalize_path(relative_path)

    # Ensure path ends with / for directory matching
    if not normalized_path.endswith("/"):
        normalized_path = f"{normalized_path}/"

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

            # Case 1: Path is inside the include pattern (file/subdir match)
            if normalized_path.startswith(pattern):
                return True

            # Case 2: Path is an ANCESTOR of include pattern (traversal mode only)
            # This allows parent directories to pass through so traversal can reach nested targets
            if is_traversal and pattern.startswith(normalized_path):
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
        include_dirs: list[str] | None = None,
        exclude_dirs: list[str] | None = None,
    ):
        """Initialize the directory filter.

        Args:
            include_dirs: List of directory prefixes to include
            exclude_dirs: List of directory prefixes to exclude
        """
        self.include_dirs = include_dirs
        self.exclude_dirs = exclude_dirs

    def matches(self, file_path: str, is_traversal: bool = False) -> bool:
        """Check if a file path matches the filter criteria.

        Args:
            file_path: Path to check (relative or with normalized separators)
            is_traversal: If True, allow ancestor directories to pass through

        Returns:
            True if the path should be included
        """
        return matches_directory_filter(
            file_path, self.include_dirs, self.exclude_dirs, is_traversal
        )

    def matches_for_traversal(self, dir_path: str) -> bool:
        """Check if a DIRECTORY path should be traversed (allows ancestors).

        Use this during tree traversal to allow parent directories of include_dirs
        to pass through so the traversal can reach nested target directories.

        Args:
            dir_path: Directory path to check

        Returns:
            True if the directory should be traversed
        """
        return self.matches(dir_path, is_traversal=True)

    def matches_for_file(self, file_path: str) -> bool:
        """Check if a FILE path matches (strict mode, no ancestor passthrough).

        Use this for filtering actual files after traversal is complete.

        Args:
            file_path: File path to check

        Returns:
            True if the file should be included
        """
        return self.matches(file_path, is_traversal=False)

    def filter_paths(self, paths: list[str]) -> list[str]:
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

    include_dirs: list[str] | None = None
    exclude_dirs: list[str] | None = None
    file_pattern: list[str] | None = None  # Normalized to list
    chunk_type: str | None = None
    tags: set[str] | None = None
    folder_structure: set[str] | None = None
    extra_filters: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, filters: dict[str, Any]) -> "FilterCriteria":
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
    def from_dict(cls, filters: dict[str, Any]) -> "FilterEngine":
        """Factory method to create FilterEngine from a filter dictionary.

        Args:
            filters: Dictionary containing filter specifications

        Returns:
            FilterEngine instance ready for filtering
        """
        return cls(FilterCriteria.from_dict(filters))

    def matches(self, metadata: dict[str, Any]) -> bool:
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
        if self.criteria.file_pattern and not any(
            pattern in relative_path for pattern in self.criteria.file_pattern
        ):
            return False

        # 3. Chunk type (exact match)
        if (
            self.criteria.chunk_type
            and metadata.get("chunk_type") != self.criteria.chunk_type
        ):
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
        self, results: list[dict], metadata_key: str = "metadata"
    ) -> list[dict]:
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
        Tuple of (effective_include_dirs, effective_exclude_dirs, include_exclusive)
        - effective_include_dirs: List of include directories or None
        - effective_exclude_dirs: List of exclude directories or None

    Migration Compatibility:
        - Supports old structure (include_dirs, exclude_dirs)
        - Supports new structure (user_included_dirs, user_excluded_dirs, default_excluded_dirs)

    Note:
        DEFAULT_IGNORED_DIRS is intentionally NOT folded into the returned
        exclude_dirs here. Callers pass these straight through to
        MerkleDAG/PathFilter, which already applies the current defaults
        internally with correct any-depth/basename semantics and lets an
        explicit include_dirs pattern override them. Laundering the defaults
        into exclude_dirs here would re-interpret them as root-anchored user
        excludes and — since exclude now beats include — silently defeat
        every include_dirs override (this was the original bug).
    """
    # Check for old structure (backward compatibility)
    if "exclude_dirs" in project_info and "user_excluded_dirs" not in project_info:
        # Old structure: treat as user-defined only. Predates include_exclusive
        # entirely, so it defaults to False (today's additive-for-dependency-
        # trees behavior applies rather than the pre-migration whitelist-only one).
        include_dirs = project_info.get("include_dirs")
        exclude_dirs = project_info.get("exclude_dirs")
        return include_dirs, exclude_dirs, False

    # New structure: return only the user's own raw lists. Defaults are
    # applied inside PathFilter, not laundered in here.
    exclude_dirs = project_info.get("user_excluded_dirs") or None
    include_dirs = project_info.get("user_included_dirs") or None
    include_exclusive = bool(project_info.get("include_exclusive", False))

    return include_dirs, exclude_dirs, include_exclusive
