"""Configuration helper utilities.

Provides utilities for accessing configuration without circular dependencies.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


def get_config_via_service_locator(key: str | None = None, default: Any = None) -> Any:
    """Retrieve configuration via ServiceLocator to avoid circular dependencies.

    This helper function provides a way to access the SearchConfig without
    creating circular import dependencies. It uses lazy importing to defer
    the import of ServiceLocator until runtime.

    Args:
        key: Optional configuration key to retrieve. If None, returns entire config.
        default: Default value if key not found or config unavailable.

    Returns:
        Configuration value, entire config object, or default.

    Raises:
        AttributeError: If the requested key doesn't exist and no default provided.

    Example:
        >>> config = get_config_via_service_locator()
        >>> bm25_weight = get_config_via_service_locator("bm25_weight", 0.4)
    """
    from mcp_server.services import ServiceLocator

    config = ServiceLocator.instance().get_config()

    if config is None:
        return default

    if key is None:
        return config

    return getattr(config, key, default)


@contextmanager
def temporary_ram_fallback_off() -> Generator[bool, None, None]:
    """Context manager to temporarily disable allow_ram_fallback during indexing.

    This improves indexing performance by preventing shared memory spillover.
    The original setting is restored after indexing completes (success or failure).

    Yields:
        bool: The original allow_ram_fallback value before modification.

    Example:
        >>> with temporary_ram_fallback_off() as original_value:
        ...     # Indexing operations run with allow_ram_fallback=False
        ...     incremental_indexer.incremental_index(project_path)
        ... # Original value automatically restored here
    """
    from search.config import get_config_manager

    logger = logging.getLogger(__name__)
    config_manager = get_config_manager()
    config = config_manager.load_config()

    original_value = config.performance.allow_ram_fallback
    was_modified = False

    try:
        if original_value:
            # Temporarily disable RAM fallback for faster indexing.
            # Toggle the in-memory singleton only — no disk write needed because the embedder
            # reads the flag via ServiceLocator (same _config object), and writing to disk would
            # change the file's mtime, causing the Merkle DAG to flag a spurious change and
            # trigger an infinite reindex loop on every subsequent search_code call.
            config.performance.allow_ram_fallback = False
            was_modified = True
            logger.info(
                "[REINDEX_CONFIG] Temporarily disabled allow_ram_fallback for indexing "
                "(was: True, now: False)"
            )
        yield original_value
    finally:
        if was_modified:
            # Restore original value in-memory (same singleton — no disk write required)
            config.performance.allow_ram_fallback = original_value
            logger.info(
                f"[REINDEX_CONFIG] Restored allow_ram_fallback to original value: {original_value}"
            )
