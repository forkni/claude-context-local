"""Unit tests for ParallelChunker timeout handling."""

import time
from unittest.mock import Mock, patch

import pytest


class TestParallelChunkerTimeouts:
    """Test timeout handling in ParallelChunker."""

    def test_timeout_constants_defined(self):
        """Test that timeout constants are properly defined."""
        from search.parallel_chunker import (
            CHUNKING_TIMEOUT_PER_FILE,
            TOTAL_CHUNKING_TIMEOUT,
        )

        assert CHUNKING_TIMEOUT_PER_FILE == 10
        assert TOTAL_CHUNKING_TIMEOUT == 300

    def test_stalled_files_logged_on_timeout(self, tmp_path, caplog):
        """Test that stalled files are logged when timeout occurs."""
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        from search.parallel_chunker import ParallelChunker

        # Create a mock chunker that raises TimeoutError
        mock_chunker = Mock()
        mock_chunker.chunk_file.side_effect = FuturesTimeoutError("Simulated timeout")

        # Create test file
        test_file = tmp_path / "slow.py"
        test_file.write_text("pass")

        # Create parallel chunker with parallel mode disabled for simpler testing
        parallel_chunker = ParallelChunker(mock_chunker, enable_parallel=False)

        # Patch the timeout constant to make test faster
        with patch("search.parallel_chunker.CHUNKING_TIMEOUT_PER_FILE", 0.01):
            # This should log timeout warnings
            parallel_chunker.chunk_files(
                str(tmp_path), [str(test_file.relative_to(tmp_path))]
            )

        # Verify file chunking failure is logged
        # In sequential mode, timeout errors are caught as generic exceptions
        failure_logged = any(
            "Failed to chunk" in record.message
            and "Simulated timeout" in record.message
            for record in caplog.records
        )
        assert failure_logged, "Expected file chunking failure to be logged"

    def test_total_timeout_stops_processing(self, tmp_path):
        """Test that processing stops when total timeout exceeded."""
        from search.parallel_chunker import ParallelChunker

        mock_chunker = Mock()

        # Simulate slow processing by making chunk_file take time
        def slow_chunk(file_path):
            time.sleep(0.5)
            return []

        mock_chunker.chunk_file.side_effect = slow_chunk

        parallel_chunker = ParallelChunker(mock_chunker, enable_parallel=False)

        # Create dummy file paths for testing (relative paths)
        test_files = [f"test{i}.py" for i in range(10)]

        # With a very short total timeout, should stop early
        with patch("search.parallel_chunker.TOTAL_CHUNKING_TIMEOUT", 0.1):
            start_time = time.time()
            parallel_chunker.chunk_files(str(tmp_path), test_files)
            elapsed = time.time() - start_time

            # Verify processing stopped early (within reasonable margin)
            assert elapsed < 2.0, "Processing should stop early due to total timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
