"""Unit tests for MCP server functionality."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mock FastMCP to avoid dependency issues in tests
sys.modules["mcp.server.fastmcp"] = MagicMock()


class TestMCPServerImport:
    """Test that MCP server can be imported."""

    def test_mcp_server_can_import(self):
        """Test that MCP server module can be imported without errors."""
        try:
            import mcp_server.server  # noqa: F401

            assert True  # If we get here, import succeeded
        except ImportError as e:
            pytest.fail(f"Failed to import MCP server: {e}")


class TestGetterFunctions:
    """Test MCP server getter functions return proper values."""

    @patch("graph.graph_storage.CodeGraphStorage")
    @patch("mcp_server.server.CodeIndexManager")
    @patch("mcp_server.server.get_project_storage_dir")
    def test_get_index_manager_returns_value(
        self, mock_get_storage, mock_index_manager_class, mock_graph_storage
    ):
        """Test that get_index_manager() returns a CodeIndexManager instance.

        This is a regression test for a bug where get_index_manager() was missing
        a return statement, causing it to return None instead of the manager object.
        """
        # Import here after mocks are set up
        import mcp_server.server as server

        # Set up mocks - create a proper Path mock with mkdir method
        mock_storage_dir = MagicMock(spec=Path)
        mock_storage_dir.name = "project_abc123_1024d"
        mock_index_dir = MagicMock(spec=Path)
        mock_index_dir.mkdir = MagicMock()  # Mock mkdir to avoid file operations
        mock_storage_dir.__truediv__ = MagicMock(
            return_value=mock_index_dir
        )  # Mock / operator

        mock_get_storage.return_value = mock_storage_dir

        # Mock CodeGraphStorage to prevent production directory pollution
        mock_graph_instance = MagicMock()
        mock_graph_storage.return_value = mock_graph_instance

        mock_manager_instance = MagicMock()
        mock_index_manager_class.return_value = mock_manager_instance

        # Call the function
        result = server.get_index_manager("/mock/project/path")

        # Verify it returns the manager instance, not None
        assert result is not None, "get_index_manager() must return a value, not None"
        assert (
            result is mock_manager_instance
        ), "get_index_manager() must return the CodeIndexManager instance"

        # Verify the manager was created with correct parameters
        mock_index_manager_class.assert_called_once()
        call_args = mock_index_manager_class.call_args
        assert (
            "project_id" in call_args.kwargs
        ), "CodeIndexManager must be initialized with project_id"


# Note: Most MCP server functionality is tested in integration tests
# where the actual decorators and FastMCP framework are working properly.
# Unit tests here would just be testing mocks, not real functionality.
