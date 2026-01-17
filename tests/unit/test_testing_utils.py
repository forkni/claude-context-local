"""Tests for testing_utils module.

Verifies that testing utilities (decorators, context managers) work correctly.
"""

import logging
import os
import sys
import unittest

# Import utilities to test
from tests.testing_utils import (
    CaptureLogger,
    CaptureStd,
    CaptureStderr,
    CaptureStdout,
    mockenv,
    mockenv_context,
    require_torch,
    require_torch_gpu,
)


class TestOutputCapture(unittest.TestCase):
    """Test output capture context managers."""

    def test_capture_stdout(self):
        """Test CaptureStdout captures print statements."""
        with CaptureStdout() as cs:
            print("test message")
            print("another message")

        self.assertIn("test message", cs.out)
        self.assertIn("another message", cs.out)

    def test_capture_stderr(self):
        """Test CaptureStderr captures stderr output."""
        with CaptureStderr() as cs:
            print("error message", file=sys.stderr)

        self.assertIn("error message", cs.out)

    def test_capture_std_both(self):
        """Test CaptureStd captures both stdout and stderr."""
        with CaptureStd() as cs:
            print("stdout message")
            print("stderr message", file=sys.stderr)

        self.assertIn("stdout message", cs.out)
        self.assertIn("stderr message", cs.err)

    def test_capture_logger(self):
        """Test CaptureLogger captures logging output."""
        logger_name = "test.logger.capture"
        logger = logging.getLogger(logger_name)

        with CaptureLogger(logger_name) as cl:
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")

        self.assertIn("debug message", cl.out)
        self.assertIn("info message", cl.out)
        self.assertIn("warning message", cl.out)

    def test_capture_logger_level_filter(self):
        """Test CaptureLogger respects level filter."""
        logger_name = "test.logger.level"
        logger = logging.getLogger(logger_name)

        # Only capture WARNING and above
        with CaptureLogger(logger_name, level=logging.WARNING) as cl:
            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")

        # Debug and info should not be captured
        self.assertNotIn("debug message", cl.out)
        self.assertNotIn("info message", cl.out)
        # Warning and error should be captured
        self.assertIn("warning message", cl.out)
        self.assertIn("error message", cl.out)


class TestEnvironmentMocking(unittest.TestCase):
    """Test environment variable mocking utilities."""

    def test_mockenv_context_sets_var(self):
        """Test mockenv_context sets environment variables."""
        test_key = "TEST_MOCKENV_CONTEXT"
        test_value = "test_value_123"

        # Ensure key doesn't exist before
        if test_key in os.environ:
            del os.environ[test_key]

        with mockenv_context(**{test_key: test_value}):
            self.assertEqual(os.environ[test_key], test_value)

        # Key should be removed after context
        self.assertNotIn(test_key, os.environ)

    def test_mockenv_context_restores_original(self):
        """Test mockenv_context restores original values."""
        test_key = "TEST_MOCKENV_RESTORE"
        original_value = "original_123"
        new_value = "new_456"

        # Set original value
        os.environ[test_key] = original_value

        with mockenv_context(**{test_key: new_value}):
            self.assertEqual(os.environ[test_key], new_value)

        # Should restore original
        self.assertEqual(os.environ[test_key], original_value)

        # Clean up
        del os.environ[test_key]

    def test_mockenv_decorator(self):
        """Test mockenv decorator sets environment variables."""
        test_key = "TEST_MOCKENV_DECORATOR"
        test_value = "decorator_value"

        # Ensure key doesn't exist before
        if test_key in os.environ:
            del os.environ[test_key]

        @mockenv(**{test_key: test_value})
        def test_function():
            return os.environ[test_key]

        result = test_function()
        self.assertEqual(result, test_value)

        # Key should be removed after function
        self.assertNotIn(test_key, os.environ)

    def test_mockenv_multiple_vars(self):
        """Test mockenv_context sets multiple variables."""
        vars_to_set = {
            "TEST_VAR_1": "value1",
            "TEST_VAR_2": "value2",
            "TEST_VAR_3": "value3",
        }

        with mockenv_context(**vars_to_set):
            for key, value in vars_to_set.items():
                self.assertEqual(os.environ[key], value)

        # All should be removed after
        for key in vars_to_set:
            self.assertNotIn(key, os.environ)


class TestRequireDecorators(unittest.TestCase):
    """Test hardware requirement decorators."""

    def test_require_torch_skips_if_not_installed(self):
        """Test require_torch skips when torch not available."""
        # This test passes if torch IS installed, so we can't test the skip path
        # But we can verify the decorator doesn't break when torch is available
        try:
            import torch  # noqa: F401

            @require_torch
            def test_func():
                return "executed"

            result = test_func()
            self.assertEqual(result, "executed")
        except ImportError:
            # If torch not installed, the decorator should raise SkipTest
            @require_torch
            def test_func():
                return "should not execute"

            with self.assertRaises(unittest.SkipTest):
                test_func()

    def test_require_torch_gpu_skips_if_no_gpu(self):
        """Test require_torch_gpu skips when no GPU available."""
        try:
            import torch

            if torch.cuda.is_available():
                # GPU available - decorator should not skip
                @require_torch_gpu
                def test_func():
                    return "executed"

                result = test_func()
                self.assertEqual(result, "executed")
            else:
                # No GPU - decorator should skip
                @require_torch_gpu
                def test_func():
                    return "should not execute"

                with self.assertRaises(unittest.SkipTest):
                    test_func()
        except ImportError:
            # No torch - decorator should skip
            @require_torch_gpu
            def test_func():
                return "should not execute"

            with self.assertRaises(unittest.SkipTest):
                test_func()


if __name__ == "__main__":
    unittest.main()
