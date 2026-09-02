"""Tree-sitter based code chunker with modular language support.

This module provides the main TreeSitterChunker class that delegates to
language-specific chunkers from the chunking.languages package.

Supported languages (9, all via tree-sitter):
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- Go (.go)
- Rust (.rs)
- C (.c)
- C++ (.cpp, .cc, .cxx, .c++, .h, .hpp, .hh, .hxx, .inl, .ipp, .tpp)
- CUDA (.cu, .cuh)
- C# (.cs)
- GLSL (.glsl, .frag, .vert, .comp, .geom, .tesc, .tese, .glslinc)
- Python (.py)
"""

from __future__ import annotations

import codecs
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tree_sitter import Language

from .language_registry import EXT_TO_LANGUAGE, LANGUAGE_SPECS

# Import base classes and language chunkers from languages package
from .languages import (
    CChunker,
    CppChunker,
    CSharpChunker,
    CudaChunker,
    GLSLChunker,
    GoChunker,
    JavaScriptChunker,
    LanguageChunker,
    PythonChunker,
    RustChunker,
    TreeSitterChunk,
    TypeScriptChunker,
)


if TYPE_CHECKING:
    from chunking.repo_profiler import RepoProfile


logger = logging.getLogger(__name__)

# Build AVAILABLE_LANGUAGES from LANGUAGE_SPECS — single grammar-loading owner.
# Each spec's load_grammar() is called once at import time; ImportError means
# the package is not installed (skip silently, log at DEBUG).
AVAILABLE_LANGUAGES: dict[str, Language] = {}

for _lang_name, _spec in LANGUAGE_SPECS.items():
    try:
        AVAILABLE_LANGUAGES[_lang_name] = _spec.load_grammar()  # type: ignore[assignment]
    except (ImportError, ValueError):
        logger.debug(
            "%s not installed (tree-sitter-%s). Install with: %s",
            _spec.grammar_module,
            _lang_name,
            _spec.install_hint
            or f"pip install {_spec.grammar_module.replace('_', '-')}",
        )

del _lang_name, _spec  # don't pollute module namespace

# Re-export for backwards compatibility
__all__ = [
    "ParsedSource",
    "TreeSitterChunk",
    "LanguageChunker",
    "TreeSitterChunker",
    "AVAILABLE_LANGUAGES",
    # Individual chunkers (for direct import if needed)
    "PythonChunker",
    "JavaScriptChunker",
    "TypeScriptChunker",
    "GoChunker",
    "RustChunker",
    "CChunker",
    "CppChunker",
    "CSharpChunker",
    "GLSLChunker",
]


# File read timeout configuration (5 seconds)
FILE_READ_TIMEOUT = 5


def _read_file_with_timeout(
    file_path: Path, timeout: float = FILE_READ_TIMEOUT
) -> bytes:
    """Read file with timeout protection against locked files.

    Reads raw bytes (not decoded text) so callers can derive both the binary
    check and the decoded content from a single open+read, instead of opening
    the file once to sniff for binary content and again to read it as text.

    Args:
        file_path: Path to file to read
        timeout: Timeout in seconds (default: 5s)

    Returns:
        Raw file contents as bytes

    Raises:
        TimeoutError: If file read exceeds timeout (likely locked)
        PermissionError: If file is not accessible
    """

    def read_file():
        with open(file_path, "rb") as f:
            return f.read()

    # Do NOT use 'with executor' — the context-manager's __exit__ calls
    # shutdown(wait=True), which blocks forever if the thread is hung on a
    # locked file, making the timeout illusory (#6).
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(read_file)
    try:
        return future.result(timeout=timeout)
    except FuturesTimeoutError:
        executor.shutdown(wait=False, cancel_futures=True)  # release, don't hang
        raise TimeoutError(
            f"File read timed out after {timeout}s (possibly locked): {file_path}"
        ) from None
    finally:
        executor.shutdown(wait=False)


@dataclass(frozen=True)
class ParsedSource:
    """A file that has been read and tree-sitter-parsed, ready to chunk.

    Produced by `TreeSitterChunker.parse_file` and consumed by both the
    repo-profiling pass (chunking/repo_profiler.py) and the chunking pass
    (`TreeSitterChunker.chunk_parsed`) — the seam that lets both passes agree
    on "how a file becomes a parsed tree" without re-implementing read/dispatch
    inline.

    Invariant: `tree` is a tree_sitter.Tree, valid only on the thread that
    produced it (tree-sitter Tree/Node objects are not thread-safe). Callers
    must produce and consume a given ParsedSource on the same thread.
    """

    abs_path: str
    rel_path: str
    content: str
    language_name: str
    chunker: LanguageChunker  # per-thread chunker that produced `tree`
    tree: Any  # tree_sitter.Tree
    # 1-based line ranges of genuine ERROR nodes, collected at parse time so
    # chunk_parsed can decide (post-chunking) whether their content actually
    # went missing. Empty when the parse is clean or the caller opted out of
    # parse warnings (the repo-profiling pre-pass).
    error_line_ranges: tuple[tuple[int, int], ...] = ()


def _collect_error_line_ranges(root_node: Any) -> tuple[tuple[int, int], ...]:
    """Collect 1-based line ranges of genuine ERROR-typed nodes in a tree.

    Deliberately stricter than `tree.root_node.has_error`, which also fires
    on harmless isolated MISSING-node artifacts (a single zero-width
    error-recovery node, e.g. GLSL's `precision highp float;`) with no real
    content loss. A true `ERROR`-typed node means the parser gave up on a
    span and its content (and everything nested under it) is unreliable for
    chunking — that's the case worth surfacing.

    Iterative (explicit stack), not recursive — tree-sitter trees can be
    deep enough on generated/minified sources to risk Python's recursion
    limit.

    Args:
        root_node: Root node of a parsed tree_sitter.Tree.

    Returns:
        One `(start_line, end_line)` pair per node where
        `node.type == "ERROR"` (nested ERROR nodes included, like the error
        count this replaces).
    """
    ranges: list[tuple[int, int]] = []
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type == "ERROR":
            ranges.append((node.start_point[0] + 1, node.end_point[0] + 1))
        stack.extend(node.children)
    return tuple(ranges)


def _uncovered_line_ranges(
    error_ranges: tuple[tuple[int, int], ...],
    chunks: list[TreeSitterChunk],
) -> list[tuple[int, int]]:
    """Subtract the chunks' line spans from `error_ranges`.

    Integer-line interval subtraction: chunk spans are merged first (adjacent
    spans coalesce — there is no line between N and N+1 to fall through), then
    each error range is reduced to the sub-ranges no chunk covers. Chunk
    content is the verbatim contiguous source slice of its line span, so a
    fully-covered error range means the ERROR text was indexed, not dropped.
    """

    def merge(ranges: list[tuple[int, int]]) -> list[list[int]]:
        merged: list[list[int]] = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        return merged

    covered = merge([(c.start_line, c.end_line) for c in chunks])

    uncovered: list[tuple[int, int]] = []
    # Merging the error ranges too keeps nested ERROR nodes (subranges of
    # their parent ERROR) from reporting the same uncovered lines twice.
    for start, end in merge(list(error_ranges)):
        cursor = start
        for cov_start, cov_end in covered:
            if cov_end < cursor:
                continue
            if cov_start > end:
                break
            if cov_start > cursor:
                uncovered.append((cursor, cov_start - 1))
            cursor = cov_end + 1
            if cursor > end:
                break
        if cursor <= end:
            uncovered.append((cursor, end))
    return uncovered


# Deliberately narrow: only brace/whitespace trivia is verified against real
# data (implementation.cc's 2 bare closing-`}` lines). Parens are excluded —
# a garbled punctuation run like `)))) ((((` is exactly what
# test_parse_error_warning_fires_when_content_dropped guards as a genuine
# loss, so widening this set would silently downgrade that case too.
_TRIVIA_CHARS = frozenset(" \t{}")


def _uncovered_is_pure_trivia(content: str, uncovered: list[tuple[int, int]]) -> bool:
    """True if every uncovered line strips to nothing but brace/whitespace
    trivia (e.g. a lone unmatched `}` left over from tree-sitter's error
    recovery). Such content carries no searchable symbols, so dropping it
    from chunking doesn't warrant a WARNING.
    """
    source_lines = content.splitlines()
    for start, end in uncovered:
        for lineno in range(start, end + 1):
            idx = lineno - 1
            if not (0 <= idx < len(source_lines)):
                return False
            if any(ch not in _TRIVIA_CHARS for ch in source_lines[idx]):
                return False
    return True


class TreeSitterChunker:
    """Main tree-sitter chunker that delegates to language-specific implementations."""

    # Map file extensions to (language_name, chunker_factory).
    # Language names come from EXT_TO_LANGUAGE (language_registry.py) — the
    # single source of truth.  Adding a new language only requires one edit there.
    LANGUAGE_MAP = {
        ".py": (EXT_TO_LANGUAGE[".py"], lambda lang: PythonChunker(lang)),
        ".js": (EXT_TO_LANGUAGE[".js"], lambda lang: JavaScriptChunker(lang)),
        ".ts": (
            EXT_TO_LANGUAGE[".ts"],
            lambda lang: TypeScriptChunker(lang, use_tsx=False),
        ),
        ".tsx": (
            EXT_TO_LANGUAGE[".tsx"],
            lambda lang: TypeScriptChunker(lang, use_tsx=True),
        ),
        ".go": (EXT_TO_LANGUAGE[".go"], lambda lang: GoChunker(lang)),
        ".rs": (EXT_TO_LANGUAGE[".rs"], lambda lang: RustChunker(lang)),
        ".c": (EXT_TO_LANGUAGE[".c"], lambda lang: CChunker(lang)),
        ".cpp": (EXT_TO_LANGUAGE[".cpp"], lambda lang: CppChunker(lang)),
        ".cc": (EXT_TO_LANGUAGE[".cc"], lambda lang: CppChunker(lang)),
        ".cxx": (EXT_TO_LANGUAGE[".cxx"], lambda lang: CppChunker(lang)),
        ".c++": (EXT_TO_LANGUAGE[".c++"], lambda lang: CppChunker(lang)),
        # Headers route to cpp (not c) -- tree_sitter_cpp parses both C and
        # C++ headers cleanly; tree_sitter_c errors on C++ headers. See
        # docs/adr/0037-decline-index-version-bump-for-cpp-parity.md and
        # docs/adr/0038-cpp-only-container-traversal-seam.md.
        ".h": (EXT_TO_LANGUAGE[".h"], lambda lang: CppChunker(lang)),
        ".hpp": (EXT_TO_LANGUAGE[".hpp"], lambda lang: CppChunker(lang)),
        ".hh": (EXT_TO_LANGUAGE[".hh"], lambda lang: CppChunker(lang)),
        ".hxx": (EXT_TO_LANGUAGE[".hxx"], lambda lang: CppChunker(lang)),
        ".inl": (EXT_TO_LANGUAGE[".inl"], lambda lang: CppChunker(lang)),
        ".ipp": (EXT_TO_LANGUAGE[".ipp"], lambda lang: CppChunker(lang)),
        ".tpp": (EXT_TO_LANGUAGE[".tpp"], lambda lang: CppChunker(lang)),
        # CUDA routes to the cpp grammar (language_name stays "cpp") with an
        # extra blanking pass for CUDA-only syntax -- see cpp.py's
        # CudaChunker and docs/adr/0054-route-cuda-extensions-to-cpp-grammar.md.
        ".cu": (EXT_TO_LANGUAGE[".cu"], lambda lang: CudaChunker(lang)),
        ".cuh": (EXT_TO_LANGUAGE[".cuh"], lambda lang: CudaChunker(lang)),
        ".cs": (EXT_TO_LANGUAGE[".cs"], lambda lang: CSharpChunker(lang)),
        ".glsl": (EXT_TO_LANGUAGE[".glsl"], lambda lang: GLSLChunker(lang)),
        ".frag": (EXT_TO_LANGUAGE[".frag"], lambda lang: GLSLChunker(lang)),
        ".vert": (EXT_TO_LANGUAGE[".vert"], lambda lang: GLSLChunker(lang)),
        ".comp": (EXT_TO_LANGUAGE[".comp"], lambda lang: GLSLChunker(lang)),
        ".geom": (EXT_TO_LANGUAGE[".geom"], lambda lang: GLSLChunker(lang)),
        ".tesc": (EXT_TO_LANGUAGE[".tesc"], lambda lang: GLSLChunker(lang)),
        ".tese": (EXT_TO_LANGUAGE[".tese"], lambda lang: GLSLChunker(lang)),
        ".glslinc": (EXT_TO_LANGUAGE[".glslinc"], lambda lang: GLSLChunker(lang)),
    }

    def __init__(self) -> None:
        """Initialize the tree-sitter chunker.

        Attributes:
            chunkers: Dictionary mapping file suffixes to initialized LanguageChunker
                instances. Lazily populated as files are processed.
            repo_profile: Optional RepoProfile for adaptive chunk sizing.
                Set by the indexer before chunking begins (full index only).
        """
        # Per-thread chunker cache: tree-sitter Parser objects are not thread-safe.
        # Each worker thread gets its own LanguageChunker instances via threading.local.
        self._local = threading.local()
        self.repo_profile: RepoProfile | None = None

    def get_chunker(self, file_path: str) -> LanguageChunker | None:
        """Get the appropriate chunker for a file.

        Args:
            file_path: Path to the file

        Returns:
            LanguageChunker instance or None if unsupported
        """
        suffix = Path(file_path).suffix.lower()

        if suffix not in self.LANGUAGE_MAP:
            return None

        language_name, chunker_factory = self.LANGUAGE_MAP[suffix]

        # Check if language is available
        if language_name not in AVAILABLE_LANGUAGES:
            logger.debug(
                f"Language {language_name} not available. "
                f"Install tree-sitter-{language_name}"
            )
            return None

        # Per-thread chunker cache (tree-sitter Parser is not thread-safe)
        if not hasattr(self._local, "chunkers"):
            self._local.chunkers = {}
        chunkers = self._local.chunkers

        # Lazy initialization of per-thread chunkers
        if suffix not in chunkers:
            try:
                language = AVAILABLE_LANGUAGES[language_name]
                chunkers[suffix] = chunker_factory(language)
            except Exception as e:  # noqa: BLE001 - resilience: per-language chunker init is optional, degrade to no chunker for this suffix
                logger.warning(
                    f"Failed to initialize chunker for {suffix}: {e}", exc_info=True
                )
                return None

        return chunkers[suffix]

    def parse_file(
        self,
        file_path: str,
        content: str | None = None,
        rel_path: str | None = None,
        emit_parse_warnings: bool = True,
    ) -> ParsedSource | None:
        """Read and tree-sitter-parse a file, without chunking it.

        Owns the same read+dispatch logic `chunk_file` used to inline
        (binary detection, timeout read, HTML/XML skip, per-thread chunker
        lookup) so callers that only need a parsed tree — e.g. the
        repo-profiling pass — don't have to reimplement it.

        Args:
            file_path: Path to the file
            content: Optional file content (will read from file if not provided)
            rel_path: Optional path to record on the result for callers that
                    track both absolute and relative paths. Defaults to
                    `file_path`.
            emit_parse_warnings: Whether to collect ERROR-node line ranges
                    onto the result's `error_line_ranges`, which
                    `chunk_parsed` turns into a `[PARSE_WARN]` warning only
                    if the ERROR content is missing from the emitted chunks
                    (retained content logs at DEBUG instead). Defaults to
                    True. The repo-profiling pre-pass parses every file a
                    second time before the chunking pass does and passes
                    False here, so a malformed file is only ever warned about
                    once per index run — by the chunking pass, which is the
                    one whose dropped content actually matters to the user.

        Returns:
            ParsedSource, or None for unsupported/binary/unreadable files
            (same contract `chunk_file` had).
        """
        chunker = self.get_chunker(file_path)

        if not chunker:
            logger.debug(f"No tree-sitter chunker available for {file_path}")
            return None

        if content is None:
            try:
                # Single timed read of raw bytes (was two opens: a binary
                # sniff via _is_binary_file, then a separate text read).
                raw = _read_file_with_timeout(Path(file_path))

                # Binary check on the bytes already in hand — same 8KB
                # null-byte rule _is_binary_file used, no second open needed.
                if b"\x00" in raw[:8192]:
                    logger.debug(f"[BINARY] Skipping binary file: {file_path}")
                    return None

                # Strip a leading UTF-8 BOM *after* the binary sniff (so the
                # sniff still sees the file's original prefix) and *before*
                # decode (so tree-sitter offsets aren't shifted by 3 phantom
                # bytes a BOM would otherwise leave at position 0).
                if raw.startswith(codecs.BOM_UTF8):
                    raw = raw[len(codecs.BOM_UTF8) :]

                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    logger.warning(
                        f"UTF-8 decode failed for {file_path}, trying with error handling"
                    )
                    content = raw.decode("utf-8", errors="ignore")

                # Reproduce text-mode open()'s universal-newline translation:
                # open(file_path, encoding="utf-8") (the old code path) decodes
                # \r\n and lone \r to \n by default. A raw bytes read + manual
                # decode() skips that, so do it explicitly to keep chunk content
                # (and offsets) identical to before on CRLF files.
                content = content.replace("\r\n", "\n").replace("\r", "\n")

                # Skip HTML/XML files that shouldn't be parsed as code
                content_start = content.lstrip()[:100].lower()
                if any(
                    marker in content_start
                    for marker in ["<!doctype html", "<html", "<?xml"]
                ):
                    logger.debug(f"[HTML/XML] Skipping markup file: {file_path}")
                    return None

            except TimeoutError as e:
                logger.warning(f"[TIMEOUT] {e}")
                return None
            except PermissionError:
                logger.warning(
                    f"[LOCKED] Cannot access file (permission denied): {file_path}"
                )
                return None
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}", exc_info=True)
                return None

        try:
            parse_bytes = chunker.preprocess_source_for_parse(bytes(content, "utf-8"))
            tree = chunker.parser.parse(parse_bytes)
        except Exception as e:  # noqa: BLE001 - parse-recovery: tree-sitter parsing of one file failing shouldn't abort the whole run
            logger.warning(
                f"Tree-sitter parsing failed for {file_path}: {e}", exc_info=True
            )
            return None

        # tree.root_node.has_error also fires on harmless isolated
        # MISSING-node artifacts (e.g. GLSL's `precision highp float;`
        # recovers via a single zero-width MISSING identifier — no content
        # lost, zero ERROR nodes). Only a genuine ERROR node can mean
        # dropped content, so gate the (tree-walk) collection behind the
        # cheap flag. Whether anything actually went missing is only
        # knowable after chunking — root-level ERROR text routinely
        # survives verbatim as a module_preamble chunk (e.g. TouchDesigner
        # textport-command files like `opcook -F override` externalized to
        # `.py`) — so the [PARSE_WARN] verdict is deferred to
        # chunk_parsed, which sees the emitted chunks.
        error_line_ranges: tuple[tuple[int, int], ...] = ()
        if emit_parse_warnings and tree.root_node.has_error:
            error_line_ranges = _collect_error_line_ranges(tree.root_node)

        return ParsedSource(
            abs_path=file_path,
            rel_path=rel_path if rel_path is not None else file_path,
            content=content,
            language_name=chunker.language_name,
            chunker=chunker,
            tree=tree,
            error_line_ranges=error_line_ranges,
        )

    def chunk_parsed(self, parsed_source: ParsedSource) -> list[TreeSitterChunk]:
        """Chunk an already-parsed file.

        Args:
            parsed_source: A ParsedSource produced by `parse_file` on this thread.

        Returns:
            List of TreeSitterChunk objects
        """
        try:
            config = self._get_chunking_config()
            chunks = parsed_source.chunker.chunk_parsed(
                parsed_source.tree,
                parsed_source.content,
                config=config,
                repo_profile=self.repo_profile,
            )
        except Exception as e:  # noqa: BLE001 - parse-recovery: chunking one file failing shouldn't abort the whole chunking run
            logger.warning(
                f"Tree-sitter chunking failed for {parsed_source.abs_path}: {e}",
                exc_info=True,
            )
            return []
        if parsed_source.error_line_ranges:
            self._log_parse_error_outcome(parsed_source, chunks)
        return chunks

    def _log_parse_error_outcome(
        self, parsed_source: ParsedSource, chunks: list[TreeSitterChunk]
    ) -> None:
        """Emit the deferred `[PARSE_WARN]` verdict now that chunks are known.

        Warning at parse time overstated the failure: tree-sitter ERROR spans
        frequently survive into chunks verbatim (root-level garbage lands in a
        module_preamble chunk), so warn only when some ERROR line ended up in
        no chunk — reporting impact (lines lost, share of file) rather than
        the raw unparsed-region count — and otherwise log the retained
        outcome at DEBUG. Uncovered content that is pure brace/whitespace
        trivia (e.g. a lone unmatched `}`) also logs at DEBUG: it carries no
        searchable symbols, so losing it isn't worth a WARNING.
        """
        uncovered = _uncovered_line_ranges(parsed_source.error_line_ranges, chunks)
        region_count = len(parsed_source.error_line_ranges)
        if not uncovered:
            logger.debug(
                f"[PARSE_WARN] {parsed_source.abs_path}: {region_count} unparsed "
                f"region(s) after parsing, but all content was retained in "
                f"emitted chunks"
            )
            return

        total_lines = len(parsed_source.content.splitlines()) or 1
        lines_lost = sum(end - start + 1 for start, end in uncovered)
        share = lines_lost / total_lines

        max_spans = 5
        span_strs = [
            str(start) if start == end else f"{start}-{end}" for start, end in uncovered
        ]
        if len(span_strs) > max_spans:
            spans = (
                f"{', '.join(span_strs[:max_spans])} "
                f"(+{len(span_strs) - max_spans} more)"
            )
        else:
            spans = ", ".join(span_strs)

        if _uncovered_is_pure_trivia(parsed_source.content, uncovered):
            logger.debug(
                f"[PARSE_WARN] {parsed_source.abs_path}: {lines_lost} of "
                f"{total_lines} line(s) ({share:.1%}) dropped from chunking "
                f"at line(s) {spans}, but it is punctuation/whitespace trivia"
            )
            return

        logger.warning(
            f"[PARSE_WARN] {parsed_source.abs_path}: {lines_lost} of "
            f"{total_lines} line(s) ({share:.1%}) dropped from chunking "
            f"across {region_count} unparsed region(s) — line(s) {spans}"
        )

    def chunk_file(
        self, file_path: str, content: str | None = None
    ) -> list[TreeSitterChunk]:
        """Chunk a file into semantic units.

        Args:
            file_path: Path to the file
            content: Optional file content (will read from file if not provided)

        Returns:
            List of TreeSitterChunk objects
        """
        parsed_source = self.parse_file(file_path, content=content)
        if parsed_source is None:
            return []
        return self.chunk_parsed(parsed_source)

    def _get_chunking_config(self):
        """Get ChunkingConfig from the current search config, or None if unavailable."""
        from search.config import get_chunking_config

        return get_chunking_config()

    def is_supported(self, file_path: str) -> bool:
        """Check if a file type is supported.

        Args:
            file_path: Path to the file

        Returns:
            True if file type is supported
        """
        suffix = Path(file_path).suffix.lower()
        if suffix not in self.LANGUAGE_MAP:
            return False

        language_name, _ = self.LANGUAGE_MAP[suffix]
        return language_name in AVAILABLE_LANGUAGES

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get list of supported file extensions.

        Returns:
            List of file extensions
        """
        supported = []
        for ext, (lang_name, _) in cls.LANGUAGE_MAP.items():
            if lang_name in AVAILABLE_LANGUAGES:
                supported.append(ext)
        return supported

    @classmethod
    def get_available_languages(cls) -> list[str]:
        """Get list of available languages.

        Returns:
            List of language names
        """
        return list(AVAILABLE_LANGUAGES.keys())
