"""Unit tests for ParallelChunker timeout handling and helper methods.

Tests cover:
- Timeout behaviour in both sequential and parallel modes
- _accumulate_chunk_stats: merge-stats extraction and accumulation
- _log_chunking_summary: logging with and without merge percentage
- chunk_files: parallel mode basic return and merge-stats propagation
"""

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


class TestAccumulateChunkStats:
    """Direct tests for the _accumulate_chunk_stats static helper."""

    def test_with_merge_stats_tuple(self):
        """When chunks[0]._merge_stats is (orig, merged), totals are updated from it."""
        from search.parallel_chunker import ParallelChunker

        chunk = Mock()
        chunk._merge_stats = (10, 7)
        new_orig, new_merged = ParallelChunker._accumulate_chunk_stats([chunk], 5, 5)
        assert new_orig == 15
        assert new_merged == 12

    def test_without_merge_stats_uses_len(self):
        """When no _merge_stats attribute, each chunk counts as one original and merged."""
        from search.parallel_chunker import ParallelChunker

        chunks = [Mock(spec=[]) for _ in range(3)]  # spec=[] → no attributes
        new_orig, new_merged = ParallelChunker._accumulate_chunk_stats(chunks, 0, 0)
        assert new_orig == 3
        assert new_merged == 3

    def test_merge_stats_not_a_tuple_falls_back_to_len(self):
        """When _merge_stats is not a tuple (e.g. None), fallback to len(chunks)."""
        from search.parallel_chunker import ParallelChunker

        chunk = Mock()
        chunk._merge_stats = None  # hasattr passes, isinstance fails
        new_orig, new_merged = ParallelChunker._accumulate_chunk_stats([chunk], 2, 2)
        assert new_orig == 3
        assert new_merged == 3


class TestLogChunkingSummary:
    """Direct tests for the _log_chunking_summary static helper."""

    def test_logs_merge_percentage_when_counts_differ(self, caplog):
        """When total_original != total_merged the log line includes merge-% and original count."""
        import logging

        from search.parallel_chunker import ParallelChunker

        file_paths = ["a.py", "b.py"]
        all_chunks = [Mock()] * 7  # 7 chunks after merge

        with caplog.at_level(logging.INFO, logger="search.parallel_chunker"):
            ParallelChunker._log_chunking_summary(file_paths, all_chunks, 10, 7)

        assert any("30.0% merged from 10 original" in r.message for r in caplog.records)

    def test_logs_simple_count_when_no_merge(self, caplog):
        """When counts are equal the simple count message is logged (no 'merged' word)."""
        import logging

        from search.parallel_chunker import ParallelChunker

        file_paths = ["a.py"]
        all_chunks = [Mock()] * 5

        with caplog.at_level(logging.INFO, logger="search.parallel_chunker"):
            ParallelChunker._log_chunking_summary(file_paths, all_chunks, 5, 5)

        messages = [r.message for r in caplog.records]
        assert any("5 chunks" in m for m in messages)
        assert all("merged" not in m for m in messages)

    def test_logs_simple_count_when_total_original_zero(self, caplog):
        """When total_original == 0 (no chunks at all), falls through to simple count."""
        import logging

        from search.parallel_chunker import ParallelChunker

        with caplog.at_level(logging.INFO, logger="search.parallel_chunker"):
            ParallelChunker._log_chunking_summary(["a.py"], [], 0, 0)

        messages = [r.message for r in caplog.records]
        assert any("0 chunks" in m for m in messages)


class TestChunkFilesPublicInterface:
    """Tests for chunk_files behaviour exercised through the public interface."""

    def test_parallel_mode_returns_all_chunks(self, tmp_path):
        """Parallel path (enable_parallel=True, ≥2 files) returns all chunks from all files."""
        from search.parallel_chunker import ParallelChunker

        fake_chunk = Mock()
        mock_chunker = Mock()
        mock_chunker.chunk_file.return_value = [fake_chunk, fake_chunk]  # 2 per file

        pc = ParallelChunker(mock_chunker, enable_parallel=True, max_workers=2)
        # 3 files → triggers parallel path (len > 1)
        result = pc.chunk_files(str(tmp_path), ["a.py", "b.py", "c.py"])

        assert len(result) == 6
        assert mock_chunker.chunk_file.call_count == 3

    def test_merge_stats_propagation_in_summary_log(self, tmp_path, caplog):
        """Chunks with _merge_stats cause the summary to log a merge percentage."""
        import logging

        from search.parallel_chunker import ParallelChunker

        chunk_with_stats = Mock()
        chunk_with_stats._merge_stats = (
            4,
            3,
        )  # 4 original → 3 after merge = 25% reduction

        mock_chunker = Mock()
        mock_chunker.chunk_file.return_value = [chunk_with_stats]

        pc = ParallelChunker(mock_chunker, enable_parallel=False)

        with caplog.at_level(logging.INFO, logger="search.parallel_chunker"):
            pc.chunk_files(str(tmp_path), ["a.py"])

        assert any("25.0% merged" in r.message for r in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
