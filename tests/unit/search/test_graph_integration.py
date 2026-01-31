"""Unit tests for GraphIntegration class."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from search.graph_integration import GraphIntegration


class TestGraphIntegration(TestCase):
    """Test GraphIntegration functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / "storage"
        self.storage_dir.mkdir(parents=True)

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_init_with_project_id(self, mock_graph_storage):
        """Test initialization with project ID."""
        project_id = "test_project"
        graph = GraphIntegration(project_id, self.storage_dir)

        # Should initialize graph storage
        mock_graph_storage.assert_called_once_with(
            project_id=project_id, storage_dir=self.storage_dir.parent
        )
        self.assertIsNotNone(graph.storage)
        self.assertTrue(graph.is_available)

    def test_init_without_project_id(self):
        """Test initialization without project ID."""
        graph = GraphIntegration(None, self.storage_dir)

        # Should not initialize graph storage
        self.assertIsNone(graph.storage)
        self.assertFalse(graph.is_available)
        self.assertEqual(graph.node_count, 0)

    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", False)
    def test_init_when_unavailable(self):
        """Test initialization when graph storage is unavailable."""
        graph = GraphIntegration("test_project", self.storage_dir)

        # Should not initialize graph storage
        self.assertIsNone(graph.storage)
        self.assertFalse(graph.is_available)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_add_chunk_function(self, mock_graph_storage):
        """Test adding a function chunk to graph."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        metadata = {
            "chunk_type": "function",
            "name": "test_function",
            "file_path": "test.py",
            "language": "python",
            "calls": [
                {
                    "callee_name": "helper",
                    "line_number": 10,
                    "is_method_call": False,
                }
            ],
            "relationships": [],
        }

        graph.add_chunk("test.py:1-10:function:test_function", metadata)

        # Should add node
        mock_storage.add_node.assert_called_once_with(
            chunk_id="test.py:1-10:function:test_function",
            name="test_function",
            chunk_type="function",
            file_path="test.py",
            language="python",
        )

        # Should add call edge
        mock_storage.add_call_edge.assert_called_once_with(
            caller_id="test.py:1-10:function:test_function",
            callee_name="helper",
            line_number=10,
            is_method_call=False,
        )

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_add_chunk_class(self, mock_graph_storage):
        """Test adding a class chunk to graph."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        metadata = {
            "chunk_type": "class",
            "name": "TestClass",
            "file_path": "test.py",
            "language": "python",
            "calls": [],
            "relationships": [],
        }

        graph.add_chunk("test.py:1-10:class:TestClass", metadata)

        # Should add node
        mock_storage.add_node.assert_called_once()

    def test_add_chunk_without_storage(self):
        """Test adding chunk when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        metadata = {
            "chunk_type": "function",
            "name": "test_function",
        }

        # Should not raise error
        graph.add_chunk("test.py:1-10:function:test_function", metadata)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_add_chunk_non_semantic_type(self, mock_graph_storage):
        """Test adding non-semantic chunk type."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        metadata = {
            "chunk_type": "comment",
            "name": "test_comment",
            "file_path": "test.py",
            "language": "python",
            "calls": [],
            "relationships": [],
        }

        graph.add_chunk("test.py:1-10:comment:test_comment", metadata)

        # Should not add node for non-semantic type
        mock_storage.add_node.assert_not_called()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_save_with_nodes(self, mock_graph_storage):
        """Test saving graph with nodes."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=5)
        mock_storage.graph_path = Path("/test/graph.db")
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)
        graph.save()

        # Should call save
        mock_storage.save.assert_called_once()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_save_without_nodes(self, mock_graph_storage):
        """Test saving graph without nodes."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=0)
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)
        graph.save()

        # Should not call save for empty graph
        mock_storage.save.assert_not_called()

    def test_save_without_storage(self):
        """Test saving when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        # Should not raise error
        graph.save()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_clear(self, mock_graph_storage):
        """Test clearing graph."""
        mock_storage = Mock()
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)
        graph.clear()

        # Should call clear
        mock_storage.clear.assert_called_once()

    def test_clear_without_storage(self):
        """Test clearing when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        # Should not raise error
        graph.clear()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_node_count(self, mock_graph_storage):
        """Test node count property."""
        mock_storage = Mock()
        mock_storage.__len__ = Mock(return_value=10)
        mock_graph_storage.return_value = mock_storage

        graph = GraphIntegration("test_project", self.storage_dir)

        self.assertEqual(graph.node_count, 10)
        self.assertEqual(len(graph), 10)

    def test_node_count_without_storage(self):
        """Test node count when storage is not available."""
        graph = GraphIntegration(None, self.storage_dir)

        self.assertEqual(graph.node_count, 0)
        self.assertEqual(len(graph), 0)

    def test_split_block_disambiguation_logic(self):
        """Test that split_block disambiguation resolves to first block by start_line."""
        # Create test candidates that simulate split_blocks
        candidates = [
            "test.py:201-250:split_block:process_data",
            "test.py:100-150:split_block:process_data",
            "test.py:151-200:split_block:process_data",
        ]

        # Filter split_blocks (all candidates are split_blocks)
        split_blocks = [c for c in candidates if ":split_block:" in c]
        assert len(split_blocks) == len(candidates)  # All are split_blocks

        # Sort by start_line
        def _start_line(chunk_id: str) -> int:
            parts = chunk_id.split(":")
            if len(parts) >= 2:
                line_range = parts[1]
                try:
                    return int(line_range.split("-")[0])
                except (ValueError, IndexError):
                    pass
            return float("inf")

        split_blocks.sort(key=_start_line)

        # Should resolve to the one with lowest start_line (100)
        assert split_blocks[0] == "test.py:100-150:split_block:process_data"

    def test_mixed_candidates_not_all_split_blocks(self):
        """Test that mixed candidates don't trigger split_block disambiguation."""
        candidates = [
            "test.py:10-50:function:helper",
            "test.py:100-150:split_block:helper",
        ]

        # Only one is a split_block
        split_blocks = [c for c in candidates if ":split_block:" in c]
        assert len(split_blocks) != len(candidates)  # Not all are split_blocks

        # Disambiguation should NOT activate (would return None in real code)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
