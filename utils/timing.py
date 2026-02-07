"""Timing utilities for performance tracking.

Provides decorator and context manager for consistent operation timing.
"""

import functools
import logging
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import TypeVar


T = TypeVar("T")
logger = logging.getLogger(__name__)


def timed(name: str | None = None) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to log function execution time.

    Args:
        name: Optional name for the operation (defaults to function name)

    Example:
        @timed("search_operation")
        def search(query: str) -> list:
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        operation_name = name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.info(f"[TIMING] {operation_name}: {elapsed_ms:.2f}ms")

        return wrapper

    return decorator


@contextmanager
def timer(name: str) -> Generator[dict[str, float], None, None]:
    """Context manager for timing code blocks.

    Args:
        name: Name of the operation being timed

    Yields:
        Dict that will contain 'elapsed_ms' after block completes

    Example:
        with Timer("embedding_generation") as t:
            embedding = model.encode(text)
        print(f"Took {t['elapsed_ms']:.2f}ms")
    """
    timing_info: dict[str, float] = {"elapsed_ms": 0.0}
    start = time.perf_counter()
    try:
        yield timing_info
    finally:
        timing_info["elapsed_ms"] = (time.perf_counter() - start) * 1000
        logger.info(f"[TIMING] {name}: {timing_info['elapsed_ms']:.2f}ms")
