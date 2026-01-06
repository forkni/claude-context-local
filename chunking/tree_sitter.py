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
from typing import Dict, List, Optional

from tree_sitter import Language

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
AVAILABLE_LANGUAGES: Dict[str, Language] = {}

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
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(read_file)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeoutError:
            raise TimeoutError(
                f"File read timed out after {timeout}s (possibly locked): {file_path}"
            ) from None


class TreeSitterChunker:
    """Main tree-sitter chunker that delegates to language-specific implementations."""

    # Map file extensions to chunker factories
    # Each entry: (language_name, factory_function)
    LANGUAGE_MAP = {
        ".py": ("python", lambda lang: PythonChunker(lang)),
        ".js": ("javascript", lambda lang: JavaScriptChunker(lang)),
        ".ts": ("typescript", lambda lang: TypeScriptChunker(lang, use_tsx=False)),
        ".tsx": ("tsx", lambda lang: TypeScriptChunker(lang, use_tsx=True)),
        ".go": ("go", lambda lang: GoChunker(lang)),
        ".rs": ("rust", lambda lang: RustChunker(lang)),
        ".c": ("c", lambda lang: CChunker(lang)),
        ".cpp": ("cpp", lambda lang: CppChunker(lang)),
        ".cc": ("cpp", lambda lang: CppChunker(lang)),
        ".cxx": ("cpp", lambda lang: CppChunker(lang)),
        ".c++": ("cpp", lambda lang: CppChunker(lang)),
        ".cs": ("csharp", lambda lang: CSharpChunker(lang)),
        ".glsl": ("glsl", lambda lang: GLSLChunker(lang)),
        ".frag": ("glsl", lambda lang: GLSLChunker(lang)),
        ".vert": ("glsl", lambda lang: GLSLChunker(lang)),
        ".comp": ("glsl", lambda lang: GLSLChunker(lang)),
        ".geom": ("glsl", lambda lang: GLSLChunker(lang)),
        ".tesc": ("glsl", lambda lang: GLSLChunker(lang)),
        ".tese": ("glsl", lambda lang: GLSLChunker(lang)),
    }

    def __init__(self):
        """Initialize the tree-sitter chunker.

        Attributes:
            chunkers: Dictionary mapping file suffixes to initialized LanguageChunker
                instances. Lazily populated as files are processed.
        """
        self.chunkers: Dict[str, LanguageChunker] = {}

    def get_chunker(self, file_path: str) -> Optional[LanguageChunker]:
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
                logger.warning(f"Failed to initialize chunker for {suffix}: {e}")
                return None

        return self.chunkers[suffix]

    def chunk_file(
        self, file_path: str, content: Optional[str] = None
    ) -> List[TreeSitterChunk]:
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
            try:
                content = _read_file_with_timeout(Path(file_path))
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
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read file {file_path}: {e}")
                    return []
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                return []

        try:
            # Get config for merge settings
            config = self._get_chunking_config()
            return chunker.chunk_code(content, config=config)
        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed for {file_path}: {e}")
            return []

    def _get_chunking_config(self):
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
    def get_supported_extensions(cls) -> List[str]:
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
    def get_available_languages(cls) -> List[str]:
        """Get list of available languages.

        Returns:
            List of language names
        """
        return list(AVAILABLE_LANGUAGES.keys())
