"""Single owner of the chunk_id wire format: 'file:lines:type:name'.

Format invariant: at least 3 colons, components are:
  parts[0] = relative file path (forward slashes after normalization)
  parts[1] = "start-end" line range
  parts[2] = chunk kind (function, class, method, split_block, ...)
  parts[3] = symbol name, possibly qualified ("ClassName.method")

All callers that need to read or validate chunk_ids should import from here
rather than re-implementing the format themselves.
"""

import logging
from dataclasses import dataclass

from utils.path_utils import normalize_path


logger = logging.getLogger(__name__)

# Minimum number of ":" separators for a string to be a valid chunk_id.
# Symbol-only strings ("Exception", "login") have 0–2 colons.
MIN_CHUNK_ID_COLONS = 3


# ---------------------------------------------------------------------------
# ChunkId value type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ChunkId:
    """Parsed representation of a chunk_id string.

    Prefer the module-level helper functions for simple one-shot needs;
    use ChunkId.parse() when you need to access multiple fields.
    """

    file_path: str  # normalized (forward-slash) relative path
    line_start: int
    line_end: int
    kind: str  # e.g. "function", "class", "method", "split_block"
    name: str  # may be qualified: "ClassName.method"

    @classmethod
    def parse(cls, raw: str) -> "ChunkId | None":
        """Parse a raw chunk_id string.

        Returns None when the string does not match the expected format.

        Examples:
            >>> ChunkId.parse("search/filters.py:22-31:function:normalize_path")
            ChunkId(file_path='search/filters.py', line_start=22, line_end=31,
                    kind='function', name='normalize_path')
            >>> ChunkId.parse("login")   # bare symbol name
            None
        """
        parts = raw.split(":")
        if len(parts) < 4:
            return None
        line_range = parts[1]
        if "-" not in line_range:
            return None
        try:
            start, end = map(int, line_range.split("-", 1))
        except ValueError:
            return None
        return cls(
            file_path=normalize_path(parts[0]),
            line_start=start,
            line_end=end,
            kind=parts[2],
            name=parts[3],
        )

    @property
    def line_count(self) -> int:
        """Number of lines in this chunk (inclusive)."""
        return self.line_end - self.line_start + 1

    def without_line_range(self) -> str:
        """Return 'file:kind:name' without the line-range component.

        Used for split_block deduplication: two split_block pieces of the same
        function share the same without_line_range() value.
        """
        return f"{self.file_path}:{self.kind}:{self.name}"

    def __str__(self) -> str:
        """Round-trip back to the canonical wire format."""
        return f"{self.file_path}:{self.line_start}-{self.line_end}:{self.kind}:{self.name}"


# ---------------------------------------------------------------------------
# Module-level helpers — the seam most call sites actually use
# ---------------------------------------------------------------------------


def is_chunk_id(raw: str) -> bool:
    """Return True if *raw* looks like a chunk_id rather than a bare symbol name.

    Real chunk IDs have format: "file.py:10-20:function:name" (≥3 colons).
    Symbol names ("Exception", "login") have 0–2 colons.

    This is intentionally a cheap heuristic (colon count), not a full parse.
    """
    return raw.count(":") >= MIN_CHUNK_ID_COLONS


def _canonical_path_sep(path: str) -> str:
    """Backslashes (single or double/JSON-escaped) → '/', then collapse repeats.

    Idempotent.  A relative path never legitimately contains '//' or '\\', so
    collapsing is lossless.  Fixes the gap where ``normalize_path`` turns the
    double-escaped ``\\\\`` into ``//`` instead of ``/``.

    Examples:
        >>> _canonical_path_sep("search\\\\reranker.py")   # double-escaped
        "search/reranker.py"
        >>> _canonical_path_sep("search//reranker.py")     # repeated slash
        "search/reranker.py"
    """
    p = normalize_path(path)  # "\\" and "\" → "/" (double-backslash becomes "//")
    while "//" in p:
        p = p.replace("//", "/")
    return p


def normalize(raw: str) -> str:
    """Normalize path separators in *raw* to a single canonical forward slash.

    Handles Windows backslashes (single and JSON-double-escaped) in the
    file-path component and collapses any repeated slashes introduced by the
    double-escape round-trip.  Reconstructs the colon-delimited structure so
    only the file path is touched.

    This is the **single owner** of chunk_id path canonicalization.  Route all
    callers here rather than reimplementing.

    Idempotent: ``normalize(normalize(x)) == normalize(x)``

    Examples:
        >>> normalize("search\\\\reranker.py:36-137:method:rerank")
        "search/reranker.py:36-137:method:rerank"
        >>> normalize("search\\reranker.py:36-137:method:rerank")
        "search/reranker.py:36-137:method:rerank"
        >>> normalize("search/reranker.py:36-137:method:rerank")
        "search/reranker.py:36-137:method:rerank"
    """
    parts = raw.split(":")
    if len(parts) >= 4:
        return f"{_canonical_path_sep(parts[0])}:{':'.join(parts[1:])}"
    return _canonical_path_sep(raw)


def extract_name(raw: str) -> str:
    """Extract the symbol name (4th component) from a chunk_id.

    Returns an empty string if the string has fewer than 4 components.

    Examples:
        "search/searcher.py:37-52:method:IntelligentSearcher.__init__"
            → "IntelligentSearcher.__init__"
        "scripts/list_projects_display.py:24-85:function:main" → "main"
        "login"  → ""
    """
    parts = raw.split(":")
    return parts[3] if len(parts) >= 4 else ""


def extract_line_count(raw: str) -> int:
    """Parse the line-range component and return the line count.

    Returns 0 when the format is unrecognised or the range cannot be parsed.

    Examples:
        "embeddings/embedder.py:276-1330:class:CodeEmbedder" → 1055
        "search/filters.py:22-31:function:normalize_path" → 10
        "invalid:format" → 0
    """
    parts = raw.split(":")
    if len(parts) < 2:
        logger.warning("Malformed chunk_id (insufficient parts): %s", raw)
        return 0
    line_range = parts[1]
    if "-" not in line_range:
        logger.warning("Malformed chunk_id (no line range): %s", raw)
        return 0
    try:
        start, end = map(int, line_range.split("-", 1))
        return end - start + 1
    except (ValueError, IndexError):
        logger.warning("Malformed chunk_id (invalid line range): %s", raw)
        return 0


def strip_line_range(raw: str) -> str:
    """Return 'file:kind:name' without the line-range component.

    Mirrors ChunkId.without_line_range() for callers that do not need a parsed
    ChunkId object.  Returns *raw* unchanged when it has fewer than 4 components.

    Used for split_block deduplication in MRR / Recall evaluation.

    Examples:
        "search/filters.py:22-31:function:normalize_path"
            → "search/filters.py:function:normalize_path"
        "login" → "login"
    """
    parts = raw.split(":")
    if len(parts) < 4:
        return raw
    return f"{parts[0]}:{parts[2]}:{parts[3]}"
