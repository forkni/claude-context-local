"""Deprecation utilities for gradual migration.

This module provides decorators and utilities for marking functions, methods,
and classes as deprecated while maintaining backward compatibility.

Usage:
    from utils.deprecation import deprecated

    @deprecated(replacement="new_function", version="0.7.0")
    def old_function():
        return "still works but warns"
"""

import functools
import warnings
from collections.abc import Callable


def deprecated(
    replacement: str | None = None,
    version: str = "0.7.0",
    removal_version: str = "0.8.0",
) -> Callable:
    """Mark a function or method as deprecated with a warning.

    This decorator emits a DeprecationWarning when the decorated function is called,
    informing users about the deprecation and suggesting alternatives.

    Args:
        replacement: Suggested replacement method/function (e.g., "self.new_method()")
        version: Version when deprecation started (default: "0.7.0")
        removal_version: Version when removal is planned (default: "0.8.0")

    Returns:
        Decorator function that wraps the deprecated callable

    Example:
        >>> @deprecated(replacement="new_method()", version="0.7.0")
        ... def old_method(self):
        ...     return self.new_method()

        When called, emits: "old_method is deprecated since v0.7.0.
                           Use new_method() instead.
                           Will be removed in v0.8.0."
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__qualname__} is deprecated since v{version}"
            if replacement:
                msg += f". Use {replacement} instead"
            msg += f". Will be removed in v{removal_version}."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        wrapper.__deprecated__ = True  # Mark for introspection
        return wrapper

    return decorator
