"""Custom exceptions for the semantic code search system.

This module defines a hierarchy of exceptions for better error categorization
and handling throughout the codebase.

Exception Hierarchy:
    CodeSearchError (base)
    ├── IndexError - Index operations (create, load, save)
    ├── SearchError - Search operations (query, filter)
    ├── ModelLoadError - Embedding model loading
    ├── VRAMExhaustedError - GPU memory issues
    ├── ConfigurationError - Invalid configuration
    └── DimensionMismatchError - Embedder/index dimension incompatibility
"""


class CodeSearchError(Exception):
    """Base exception for all code search operations.

    All custom exceptions in this package inherit from this class,
    allowing callers to catch all code search errors with a single
    except clause if desired.

    Example:
        try:
            result = searcher.search(query)
        except CodeSearchError as e:
            logger.error(f"Search operation failed: {e}")
    """

    pass


class IndexError(CodeSearchError):
    """Exception raised for index-related errors.

    Raised when index operations fail, such as:
    - Creating an index with invalid parameters
    - Loading a corrupted or incompatible index
    - Saving an index to an invalid location

    Note:
        This shadows the built-in IndexError. Import as SearchIndexError
        if you need both: `from search.exceptions import IndexError as SearchIndexError`
    """

    pass


class SearchError(CodeSearchError):
    """Exception raised for search operation failures.

    Raised when search queries fail, such as:
    - Query dimension mismatch
    - Empty results when results expected
    - Filter validation errors
    """

    pass


class ModelLoadError(CodeSearchError):
    """Exception raised when embedding model loading fails.

    Raised when:
    - Model files are missing or corrupted
    - Model requires more VRAM than available
    - HuggingFace authentication fails
    - Model is incompatible with current configuration
    """

    pass


class VRAMExhaustedError(CodeSearchError):
    """Exception raised when GPU memory is insufficient.

    Raised when:
    - Model requires more VRAM than available
    - Batch size exceeds GPU memory capacity
    - Memory fragmentation prevents allocation

    Attributes:
        required_gb: Estimated VRAM required (if known)
        available_gb: Available VRAM when error occurred (if known)
    """

    def __init__(
        self,
        message: str,
        required_gb: float | None = None,
        available_gb: float | None = None,
    ):
        super().__init__(message)
        self.required_gb = required_gb
        self.available_gb = available_gb


class ConfigurationError(CodeSearchError):
    """Exception raised for configuration errors.

    Raised when:
    - Required configuration values are missing
    - Configuration values are invalid
    - Configuration file is malformed
    """

    pass
