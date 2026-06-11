"""Tree-sitter based code chunker with modular language support.

This module provides the main TreeSitterChunker class that delegates to
language-specific chunkers from the chunking.languages package.

Supported languages (8 tree-sitter + 1 AST):
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- Go (.go)
- Rust (.rs)
- C (.c)
- C++ (.cpp, .cc, .cxx, .c++)
- C# (.cs)
- GLSL (.glsl, .frag, .vert, .comp, .geom, .tesc, .tese)
- Python (.py) - via separate AST-based chunker
"""

import logging
import warnings
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from pathlib import Path

from tree_sitter import Language

from .language_registry import EXT_TO_LANGUAGE

# Import base classes and language chunkers from languages package
from .languages import (
    CChunker,
    CppChunker,
    CSharpChunker,
    GLSLChunker,
    GoChunker,
    JavaScriptChunker,
    LanguageChunker,
    PythonChunker,
    RustChunker,
    TreeSitterChunk,
    TypeScriptChunker,
)


logger = logging.getLogger(__name__)

# Try to import language bindings
AVAILABLE_LANGUAGES: dict[str, Language] = {}

try:
    import tree_sitter_python as tspython

    AVAILABLE_LANGUAGES["python"] = Language(tspython.language())
except ImportError:
    logger.debug("tree-sitter-python not installed")

try:
    import tree_sitter_javascript as tsjavascript

    AVAILABLE_LANGUAGES["javascript"] = Language(tsjavascript.language())
except ImportError:
    logger.debug("tree-sitter-javascript not installed")

try:
    import tree_sitter_typescript as tstypescript

    # TypeScript has two grammars: typescript and tsx
    AVAILABLE_LANGUAGES["typescript"] = Language(tstypescript.language_typescript())
    AVAILABLE_LANGUAGES["tsx"] = Language(tstypescript.language_tsx())
except ImportError:
    logger.debug("tree-sitter-typescript not installed")

try:
    import tree_sitter_go as tsgo

    AVAILABLE_LANGUAGES["go"] = Language(tsgo.language())
except ImportError:
    logger.debug("tree-sitter-go not installed")

try:
    import tree_sitter_rust as tsrust

    AVAILABLE_LANGUAGES["rust"] = Language(tsrust.language())
except ImportError:
    logger.debug("tree-sitter-rust not installed")

try:
    import tree_sitter_c as tsc

    AVAILABLE_LANGUAGES["c"] = Language(tsc.language())
except ImportError:
    logger.debug("tree-sitter-c not installed")

try:
    import tree_sitter_cpp as tscpp

    AVAILABLE_LANGUAGES["cpp"] = Language(tscpp.language())
except ImportError:
    logger.debug("tree-sitter-cpp not installed")

try:
    import tree_sitter_c_sharp as tscsharp

    AVAILABLE_LANGUAGES["csharp"] = Language(tscsharp.language())
except ImportError:
    logger.debug("tree-sitter-c-sharp not installed")

try:
    import tree_sitter_glsl as tsglsl

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="int argument support is deprecated")
        AVAILABLE_LANGUAGES["glsl"] = Language(tsglsl.language())
except ImportError:
    logger.debug("tree-sitter-glsl not installed")

# Re-export for backwards compatibility
__all__ = [
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


def _read_file_with_timeout(file_path: Path, timeout: float = FILE_READ_TIMEOUT) -> str:
    """Read file with timeout protection against locked files.

    Args:
        file_path: Path to file to read
        timeout: Timeout in seconds (default: 5s)

    Returns:
        File contents as string

    Raises:
        TimeoutError: If file read exceeds timeout (likely locked)
        PermissionError: If file is not accessible
        UnicodeDecodeError: If file encoding is invalid
    """

    def read_file():
        with open(file_path, encoding="utf-8") as f:
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


def _is_binary_file(file_path: Path, sample_size: int = 8192) -> bool:
    """Check if a file is binary by looking for null bytes.

    Args:
        file_path: Path to the file
        sample_size: Number of bytes to sample (default 8KB)

    Returns:
        True if file appears to be binary
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
            # Null bytes are strong indicator of binary content
            return b"\x00" in chunk
    except OSError:
        return False  # If we can't read it, let the main logic handle it


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
        ".cs": (EXT_TO_LANGUAGE[".cs"], lambda lang: CSharpChunker(lang)),
        ".glsl": (EXT_TO_LANGUAGE[".glsl"], lambda lang: GLSLChunker(lang)),
        ".frag": (EXT_TO_LANGUAGE[".frag"], lambda lang: GLSLChunker(lang)),
        ".vert": (EXT_TO_LANGUAGE[".vert"], lambda lang: GLSLChunker(lang)),
        ".comp": (EXT_TO_LANGUAGE[".comp"], lambda lang: GLSLChunker(lang)),
        ".geom": (EXT_TO_LANGUAGE[".geom"], lambda lang: GLSLChunker(lang)),
        ".tesc": (EXT_TO_LANGUAGE[".tesc"], lambda lang: GLSLChunker(lang)),
        ".tese": (EXT_TO_LANGUAGE[".tese"], lambda lang: GLSLChunker(lang)),
    }

    def __init__(self) -> None:
        """Initialize the tree-sitter chunker.

        Attributes:
            chunkers: Dictionary mapping file suffixes to initialized LanguageChunker
                instances. Lazily populated as files are processed.
            repo_profile: Optional RepoProfile for adaptive chunk sizing.
                Set by the indexer before chunking begins (full index only).
        """
        self.chunkers: dict[str, LanguageChunker] = {}
        self.repo_profile: object | None = None  # chunking.repo_profiler.RepoProfile

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

        # Lazy initialization of chunkers
        if suffix not in self.chunkers:
            try:
                language = AVAILABLE_LANGUAGES[language_name]
                self.chunkers[suffix] = chunker_factory(language)
            except Exception as e:
                logger.warning(
                    f"Failed to initialize chunker for {suffix}: {e}", exc_info=True
                )
                return None

        return self.chunkers[suffix]

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
        chunker = self.get_chunker(file_path)

        if not chunker:
            logger.debug(f"No tree-sitter chunker available for {file_path}")
            return []

        if content is None:
            # Check for binary files before attempting text read
            if _is_binary_file(Path(file_path)):
                logger.debug(f"[BINARY] Skipping binary file: {file_path}")
                return []

            try:
                content = _read_file_with_timeout(Path(file_path))

                # Skip HTML/XML files that shouldn't be parsed as code
                content_start = content.lstrip()[:100].lower()
                if any(
                    marker in content_start
                    for marker in ["<!doctype html", "<html", "<?xml"]
                ):
                    logger.debug(f"[HTML/XML] Skipping markup file: {file_path}")
                    return []

            except TimeoutError as e:
                logger.warning(f"[TIMEOUT] {e}")
                return []
            except PermissionError:
                logger.warning(
                    f"[LOCKED] Cannot access file (permission denied): {file_path}"
                )
                return []
            except UnicodeDecodeError:
                logger.warning(
                    f"UTF-8 decode failed for {file_path}, trying with error handling"
                )
                try:
                    with open(file_path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read file {file_path}: {e}", exc_info=True)
                    return []
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}", exc_info=True)
                return []

        try:
            # Get config for merge settings
            config = self._get_chunking_config()
            return chunker.chunk_code(
                content, config=config, repo_profile=self.repo_profile
            )
        except Exception as e:
            logger.warning(
                f"Tree-sitter parsing failed for {file_path}: {e}", exc_info=True
            )
            return []

    def _get_chunking_config(self):
        """Get ChunkingConfig from the current search config.

        Returns:
            ChunkingConfig if available, None otherwise
        """
        try:
            from search.config import get_search_config

            config = get_search_config()
            return config.chunking if config else None
        except (ImportError, AttributeError):
            return None

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
