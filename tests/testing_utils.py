"""Testing utilities for claude-context-local test suite.

Provides reusable decorators, context managers, and helper classes
for testing with hardware requirements, environment mocking, and output capture.

Based on patterns from HuggingFace Transformers testing utilities.
"""

import functools
import logging
import os
import sys
import unittest
from contextlib import contextmanager
from io import StringIO
from typing import Any, Callable, Optional


def require_torch_gpu(test_func: Callable) -> Callable:
    """Skip test if no CUDA GPU available.

    Usage:
        @require_torch_gpu
        def test_gpu_inference(self):
            ...

    Args:
        test_func: Test function to decorate

    Returns:
        Wrapped test function that skips if no GPU available
    """

    @functools.wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            import torch

            if not torch.cuda.is_available():
                raise unittest.SkipTest("No CUDA GPU available")
        except ImportError:
            raise unittest.SkipTest("PyTorch not installed") from None
        return test_func(*args, **kwargs)

    return wrapper


def require_torch(test_func: Callable) -> Callable:
    """Skip test if PyTorch not available.

    Usage:
        @require_torch
        def test_torch_feature(self):
            ...

    Args:
        test_func: Test function to decorate

    Returns:
        Wrapped test function that skips if PyTorch not installed
    """

    @functools.wraps(test_func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            import torch  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("PyTorch not installed") from None
        return test_func(*args, **kwargs)

    return wrapper


@contextmanager
def mockenv_context(**kwargs: str):
    """Context manager to temporarily set environment variables.

    Usage:
        with mockenv_context(CUDA_VISIBLE_DEVICES="0"):
            # CUDA_VISIBLE_DEVICES is "0" here
            run_test()
        # CUDA_VISIBLE_DEVICES restored here

    Args:
        **kwargs: Environment variables to set temporarily

    Yields:
        None
    """
    # Save old values
    old_env = {k: os.environ.get(k) for k in kwargs}

    # Set new values
    os.environ.update(kwargs)

    try:
        yield
    finally:
        # Restore old values
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def mockenv(**kwargs: str) -> Callable:
    """Decorator to temporarily set environment variables.

    Usage:
        @mockenv(CUDA_VISIBLE_DEVICES="0", MODEL_NAME="test")
        def test_model_selection(self):
            ...

    Args:
        **kwargs: Environment variables to set temporarily

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kw: Any) -> Any:
            with mockenv_context(**kwargs):
                return func(*args, **kw)

        return wrapper

    return decorator


class CaptureStdout:
    """Context manager to capture stdout.

    Usage:
        with CaptureStdout() as cs:
            print("test message")
        assert "test message" in cs.out

    Attributes:
        out: Captured stdout content (available after __exit__)
    """

    def __init__(self) -> None:
        """Initialize stdout capture."""
        self._stdout: Optional[Any] = None
        self._capture: Optional[StringIO] = None
        self.out: str = ""

    def __enter__(self) -> "CaptureStdout":
        """Start capturing stdout."""
        self._stdout = sys.stdout
        sys.stdout = self._capture = StringIO()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop capturing and restore stdout."""
        if self._capture:
            self.out = self._capture.getvalue()
        if self._stdout:
            sys.stdout = self._stdout


class CaptureStderr:
    """Context manager to capture stderr.

    Usage:
        with CaptureStderr() as cs:
            print("error", file=sys.stderr)
        assert "error" in cs.out

    Attributes:
        out: Captured stderr content (available after __exit__)
    """

    def __init__(self) -> None:
        """Initialize stderr capture."""
        self._stderr: Optional[Any] = None
        self._capture: Optional[StringIO] = None
        self.out: str = ""

    def __enter__(self) -> "CaptureStderr":
        """Start capturing stderr."""
        self._stderr = sys.stderr
        sys.stderr = self._capture = StringIO()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop capturing and restore stderr."""
        if self._capture:
            self.out = self._capture.getvalue()
        if self._stderr:
            sys.stderr = self._stderr


class CaptureStd:
    """Context manager to capture both stdout and stderr.

    Usage:
        with CaptureStd() as cs:
            print("stdout message")
            print("stderr message", file=sys.stderr)
        assert "stdout message" in cs.out
        assert "stderr message" in cs.err

    Attributes:
        out: Captured stdout content (available after __exit__)
        err: Captured stderr content (available after __exit__)
    """

    def __init__(self) -> None:
        """Initialize stdout/stderr capture."""
        self._stdout: Optional[Any] = None
        self._stderr: Optional[Any] = None
        self._capture_out: Optional[StringIO] = None
        self._capture_err: Optional[StringIO] = None
        self.out: str = ""
        self.err: str = ""

    def __enter__(self) -> "CaptureStd":
        """Start capturing stdout and stderr."""
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = self._capture_out = StringIO()
        sys.stderr = self._capture_err = StringIO()
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop capturing and restore stdout/stderr."""
        if self._capture_out:
            self.out = self._capture_out.getvalue()
        if self._capture_err:
            self.err = self._capture_err.getvalue()
        if self._stdout:
            sys.stdout = self._stdout
        if self._stderr:
            sys.stderr = self._stderr


class CaptureLogger:
    """Context manager to capture logging output.

    Usage:
        with CaptureLogger("search.hybrid_searcher") as cl:
            logger = logging.getLogger("search.hybrid_searcher")
            logger.info("test message")
        assert "test message" in cl.out

    Attributes:
        out: Captured log content (available after __exit__)
    """

    def __init__(self, logger_name: str, level: int = logging.DEBUG) -> None:
        """Initialize logger capture.

        Args:
            logger_name: Name of logger to capture
            level: Minimum logging level to capture (default: DEBUG)
        """
        self.logger_name = logger_name
        self.level = level
        self.logger: Optional[logging.Logger] = None
        self.handler: Optional[logging.StreamHandler] = None
        self.original_level: Optional[int] = None
        self.out: str = ""

    def __enter__(self) -> "CaptureLogger":
        """Start capturing logger output."""
        self.logger = logging.getLogger(self.logger_name)

        # Save original logger level and set to desired level
        self.original_level = self.logger.level
        self.logger.setLevel(self.level)

        self.handler = logging.StreamHandler(StringIO())
        self.handler.setLevel(self.level)

        # Add formatter to match typical log output
        formatter = logging.Formatter("%(levelname)s - %(message)s")
        self.handler.setFormatter(formatter)

        self.logger.addHandler(self.handler)
        return self

    def __exit__(self, *args: Any) -> None:
        """Stop capturing and remove handler."""
        if self.handler and self.handler.stream:
            self.out = self.handler.stream.getvalue()  # type: ignore
        if self.logger and self.handler:
            self.logger.removeHandler(self.handler)

        # Restore original logger level
        if self.logger and self.original_level is not None:
            self.logger.setLevel(self.original_level)
