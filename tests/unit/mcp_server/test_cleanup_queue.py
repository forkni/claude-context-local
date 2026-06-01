"""Unit tests for CleanupQueue (deferred project deletion retry mechanism)."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.cleanup_queue import CleanupQueue


@pytest.fixture
def mock_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory for tests."""
    storage_dir = tmp_path / "test_storage"
    storage_dir.mkdir(parents=True)
    return storage_dir


def test_cleanup_queue_add_and_load(mock_storage_dir):
    """Test adding items to queue and persisting to disk."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Create queue and add item
        queue = CleanupQueue()
        queue.add("/test/dir1", "Test reason 1")
        queue.add("/test/dir2", "Test reason 2")

        # Verify queue file exists
        queue_file = mock_storage_dir / "cleanup_queue.json"
        assert queue_file.exists()

        # Load queue data
        with open(queue_file, encoding="utf-8") as f:
            queue_data = json.load(f)

        assert len(queue_data) == 2
        assert queue_data[0]["directory"] == "/test/dir1"
        assert queue_data[0]["reason"] == "Test reason 1"
        assert queue_data[0]["attempts"] == 0
        assert queue_data[1]["directory"] == "/test/dir2"

        # Create new queue instance, should load from disk
        queue2 = CleanupQueue()
        pending = queue2.get_pending()
        assert len(pending) == 2
        assert pending[0]["directory"] == "/test/dir1"


def test_cleanup_queue_process_success(mock_storage_dir):
    """Test processing queue successfully deletes existing directories."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Directories must be under storage/projects/ (validated by process())
        projects = mock_storage_dir / "projects"
        projects.mkdir()
        dir1 = projects / "proj1_abc12345_bge_1536d"
        dir2 = projects / "proj2_def67890_bge_1536d"
        dir1.mkdir()
        dir2.mkdir()

        # Add to queue
        queue = CleanupQueue()
        queue.add(str(dir1), "Locked file")
        queue.add(str(dir2), "Permission denied")

        # Process queue
        result = queue.process()

        # Verify successful deletion
        assert result["processed"] == 2
        assert result["failed"] == []
        assert result["remaining"] == 0
        assert not dir1.exists()
        assert not dir2.exists()

        # Verify queue is empty
        assert len(queue.get_pending()) == 0


def test_cleanup_queue_process_already_deleted(mock_storage_dir):
    """Test processing queue skips directories that no longer exist."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Paths must be under storage/projects/ even if they no longer exist
        projects = mock_storage_dir / "projects"
        projects.mkdir()
        ghost1 = str(projects / "ghost1_aaa_bge_512d")
        ghost2 = str(projects / "ghost2_bbb_bge_512d")

        queue = CleanupQueue()
        queue.add(ghost1, "Already deleted")
        queue.add(ghost2, "Cleaned up externally")

        # Process queue
        result = queue.process()

        # Verify processed (skipped, dirs didn't exist)
        assert result["processed"] == 2
        assert result["failed"] == []
        assert result["remaining"] == 0
        assert len(queue.get_pending()) == 0


def test_cleanup_queue_process_permission_error_retry(mock_storage_dir):
    """Test processing queue retries failed deletions up to 3 times."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Directory must be under storage/projects/ to pass validation
        projects = mock_storage_dir / "projects"
        projects.mkdir()
        test_dir = projects / "locked_proj_abc_bge_512d"
        test_dir.mkdir()

        # Add to queue
        queue = CleanupQueue()
        queue.add(str(test_dir), "Locked file")

        # Mock shutil.rmtree to always raise PermissionError
        with patch("shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = PermissionError("File is locked")

            # Attempt 1
            result = queue.process()
            assert result["processed"] == 0
            assert result["failed"] == []
            assert result["remaining"] == 1
            pending = queue.get_pending()
            assert pending[0]["attempts"] == 1

            # Attempt 2
            result = queue.process()
            assert result["processed"] == 0
            assert result["failed"] == []
            assert result["remaining"] == 1
            pending = queue.get_pending()
            assert pending[0]["attempts"] == 2

            # Attempt 3 (final)
            result = queue.process()
            assert result["processed"] == 0
            assert len(result["failed"]) == 1
            assert result["remaining"] == 0
            assert str(test_dir) in result["failed"]

            # Verify no more retries
            assert len(queue.get_pending()) == 0


def test_cleanup_queue_clear(mock_storage_dir):
    """Test clearing all pending tasks from the queue."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Add items to queue
        queue = CleanupQueue()
        queue.add("/test/dir1", "Test 1")
        queue.add("/test/dir2", "Test 2")
        queue.add("/test/dir3", "Test 3")

        assert len(queue.get_pending()) == 3

        # Clear queue
        queue.clear()

        assert len(queue.get_pending()) == 0

        # Verify persisted to disk
        queue2 = CleanupQueue()
        assert len(queue2.get_pending()) == 0


def test_cleanup_queue_empty_process(mock_storage_dir):
    """Test processing an empty queue returns zero counts."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        queue = CleanupQueue()
        result = queue.process()

        assert result["processed"] == 0
        assert result["failed"] == []
        assert result["remaining"] == 0


def test_cleanup_queue_handles_corrupted_json(mock_storage_dir):
    """Test CleanupQueue handles corrupted JSON gracefully."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Create corrupted queue file
        queue_file = mock_storage_dir / "cleanup_queue.json"
        with open(queue_file, "w", encoding="utf-8") as f:
            f.write("{invalid json content")

        # Should handle gracefully and start with empty queue
        queue = CleanupQueue()
        assert len(queue.get_pending()) == 0


def test_cleanup_queue_refuses_path_outside_projects(mock_storage_dir):
    """process() must refuse to delete paths not under storage/projects/."""
    with patch(
        "mcp_server.cleanup_queue.get_storage_dir", return_value=mock_storage_dir
    ):
        # Create a directory that exists but is not under projects/
        outside = mock_storage_dir / "outside_dir"
        outside.mkdir()

        queue = CleanupQueue()
        queue.add(str(outside), "Should be refused")

        result = queue.process()

        # Path validation rejects it → lands in failed
        assert result["processed"] == 0
        assert len(result["failed"]) == 1
        assert str(outside) in result["failed"]
        # The directory must NOT have been deleted
        assert outside.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
