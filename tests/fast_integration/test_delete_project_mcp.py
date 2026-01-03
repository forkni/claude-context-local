"""Integration tests for delete_project MCP tool.

Tests the complete MCP tool workflow:
1. Index a test project
2. Delete via MCP tool
3. Verify cleanup
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server import tool_handlers
from mcp_server.state import get_state, reset_state


def _create_test_project(project_dir: Path):
    """Create a minimal test project with Python files."""
    project_dir.mkdir(parents=True, exist_ok=True)

    # Create test files
    (project_dir / "main.py").write_text(
        """
def hello():
    print("Hello World")

if __name__ == "__main__":
    hello()
"""
    )

    (project_dir / "utils.py").write_text(
        """
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
"""
    )


@pytest.fixture(autouse=True)
def reset_state_fixture():
    """Reset global state before each test."""
    reset_state()
    yield
    reset_state()


@pytest.fixture
def mock_embedder():
    """Mock embedder to avoid GPU/model requirements."""
    import numpy as np

    def mock_encode(sentences, **kwargs):
        # Return random embeddings
        return np.random.rand(len(sentences), 1024).astype(np.float32)

    with patch("embeddings.embedder.SentenceTransformer") as mock_st:
        mock_model = Mock()
        mock_model.encode.side_effect = mock_encode
        mock_st.return_value = mock_model
        yield mock_st


@pytest.mark.asyncio
async def test_delete_project_full_workflow(mock_embedder):
    """Test complete workflow: index → delete → verify cleanup."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        _create_test_project(project_dir)

        # Step 1: Index the project
        print("\n[STEP 1] Indexing project...")
        index_result = await tool_handlers.handle_index_directory(
            {"directory_path": str(project_dir), "incremental": False}
        )

        # Check for errors
        if "error" in index_result:
            pytest.fail(f"Indexing failed: {index_result['error']}")

        assert index_result.get("success") is True
        chunks_added = index_result.get(
            "total_chunks_added", index_result.get("chunks_added", 0)
        )
        assert chunks_added > 0
        print(f"  [OK] Indexed {chunks_added} chunks")

        # Step 2: Verify project is indexed
        print("\n[STEP 2] Verifying project is indexed...")
        status = await tool_handlers.handle_get_index_status({})
        assert status["current_project"] is not None
        chunk_count = status["index_statistics"].get("total_chunks", 0)
        assert chunk_count > 0
        print(f"  [OK] Project indexed with {chunk_count} chunks")

        # Step 3: Delete the project via MCP tool
        print("\n[STEP 3] Deleting project via MCP tool...")
        delete_result = await tool_handlers.handle_delete_project(
            {"project_path": str(project_dir), "force": True}
        )

        assert delete_result["success"] is True
        assert len(delete_result["deleted_directories"]) > 0
        print(f"  [OK] Deleted {len(delete_result['deleted_directories'])} directories")
        print(f"  [OK] Deleted {delete_result['deleted_snapshots']} snapshots")

        # Step 4: Verify project is no longer indexed
        print("\n[STEP 4] Verifying project is deleted...")
        status_after = await tool_handlers.handle_get_index_status({})
        # After deletion, current_project should not be the test project
        # (it may be None or fall back to another project)
        current = status_after.get("current_project")
        assert current is None or str(project_dir) not in str(current)
        print("  [OK] Project no longer indexed")


@pytest.mark.asyncio
async def test_delete_project_blocks_current_without_force(mock_embedder):
    """Test that deleting current project without force=True is blocked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "current_project"
        _create_test_project(project_dir)

        # Step 1: Index the project (makes it current)
        print("\n[STEP 1] Indexing project (becomes current)...")
        index_result = await tool_handlers.handle_index_directory(
            {"directory_path": str(project_dir)}
        )
        if "error" in index_result:
            pytest.fail(f"Indexing failed: {index_result['error']}")
        print("  [OK] Project indexed")

        # Step 2: Attempt to delete without force
        print("\n[STEP 2] Attempting delete without force=True...")
        delete_result = await tool_handlers.handle_delete_project(
            {"project_path": str(project_dir)}
        )

        assert "error" in delete_result
        assert "Cannot delete current project" in delete_result["error"]
        assert delete_result.get("is_current_project") is True
        print("  [OK] Deletion blocked as expected")

        # Step 3: Delete with force=True
        print("\n[STEP 3] Deleting with force=True...")
        delete_result = await tool_handlers.handle_delete_project(
            {"project_path": str(project_dir), "force": True}
        )

        assert delete_result["success"] is True
        print("  [OK] Deletion succeeded with force flag")


@pytest.mark.asyncio
async def test_delete_project_nonexistent():
    """Test deleting a non-existent project."""
    print("\n[TEST] Deleting non-existent project...")
    delete_result = await tool_handlers.handle_delete_project(
        {"project_path": "/nonexistent/path/to/project"}
    )

    assert "error" in delete_result
    assert "does not exist" in delete_result["error"]
    print("  [OK] Error returned as expected")


@pytest.mark.asyncio
async def test_delete_project_missing_path():
    """Test delete_project with missing project_path parameter."""
    print("\n[TEST] Calling delete_project without project_path...")
    delete_result = await tool_handlers.handle_delete_project({})

    assert "error" in delete_result
    assert "project_path is required" in delete_result["error"]
    print("  [OK] Validation error returned as expected")


@pytest.mark.asyncio
async def test_delete_project_multi_model(mock_embedder):
    """Test deleting project with multiple model indices."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "multi_model_project"
        _create_test_project(project_dir)

        # Enable multi-model mode
        state = get_state()
        original_multi_model = state.multi_model_enabled
        state.multi_model_enabled = True

        try:
            # Step 1: Index with default model
            print("\n[STEP 1] Indexing with first model...")
            index_result = await tool_handlers.handle_index_directory(
                {"directory_path": str(project_dir), "multi_model": False}
            )
            if "error" in index_result:
                pytest.fail(f"Indexing failed: {index_result['error']}")
            print("  [OK] Indexed with first model")

            # Step 2: List projects to see model directories
            print("\n[STEP 2] Listing projects...")
            projects = await tool_handlers.handle_list_projects({})
            print(f"  [OK] Found {len(projects.get('projects', []))} project(s)")

            # Step 3: Delete project (should remove all model dirs)
            print("\n[STEP 3] Deleting project...")
            delete_result = await tool_handlers.handle_delete_project(
                {"project_path": str(project_dir), "force": True}
            )

            assert delete_result["success"] is True
            print(
                f"  [OK] Deleted {len(delete_result['deleted_directories'])} model directories"
            )

        finally:
            # Restore original setting
            state.multi_model_enabled = original_multi_model


@pytest.mark.asyncio
async def test_delete_project_cleanup_queue_integration(mock_embedder):
    """Test that PermissionError adds to cleanup queue."""
    import shutil

    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "locked_project"
        _create_test_project(project_dir)

        # Step 1: Index the project
        print("\n[STEP 1] Indexing project...")
        index_result = await tool_handlers.handle_index_directory(
            {"directory_path": str(project_dir)}
        )
        if "error" in index_result:
            pytest.fail(f"Indexing failed: {index_result['error']}")
        print("  [OK] Project indexed")

        # Step 2: Mock shutil.rmtree to raise PermissionError
        print("\n[STEP 2] Simulating file lock...")
        original_rmtree = shutil.rmtree

        def mock_rmtree(path, *args, **kwargs):
            # Raise PermissionError for project directories
            if "locked_project" in str(path):
                raise PermissionError("File is locked")
            # Allow other deletions (temp dirs, etc)
            return original_rmtree(path, *args, **kwargs)

        with patch("shutil.rmtree", side_effect=mock_rmtree):
            delete_result = await tool_handlers.handle_delete_project(
                {"project_path": str(project_dir), "force": True}
            )

            assert delete_result["success"] is False
            assert len(delete_result.get("errors", [])) > 0
            assert delete_result.get("queued_for_retry") is not None
            print(f"  [OK] {delete_result['queued_for_retry']} items queued for retry")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
