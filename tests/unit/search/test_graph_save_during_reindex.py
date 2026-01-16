"""Regression tests for graph save during reindex operations."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from search.graph_integration import GraphIntegration
from search.hybrid_searcher import HybridSearcher
from search.indexer import CodeIndexManager


class TestGraphSaveDuringReindex(TestCase):
    """Test graph storage persistence during reindex operations."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_dir = Path(self.temp_dir) / "storage"
        self.storage_dir.mkdir(parents=True)
        self.project_id = "test_project_reindex"

    def tearDown(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clear_index_preserves_graph_storage_reference(self):
        """Test that clear_index() updates graph_storage reference to match new dense_index.

        Regression test for bug where graph_storage became None after clear_index()
        because IndexSynchronizer created a new CodeIndexManager but graph_storage
        reference wasn't updated.
        """
        # Create mock HybridSearcher with minimal setup
        mock_searcher = Mock(spec=HybridSearcher)

        # Create mock dense_index with valid graph storage
        mock_dense_index = Mock(spec=CodeIndexManager)
        mock_graph_integration = Mock(spec=GraphIntegration)
        mock_graph_storage = Mock()
        mock_graph_integration.storage = mock_graph_storage
        mock_dense_index._graph = mock_graph_integration

        # Create mock index_sync
        mock_index_sync = Mock()
        mock_index_sync.dense_index = mock_dense_index
        mock_index_sync.bm25_index = Mock()

        # Set up searcher attributes
        mock_searcher.index_sync = mock_index_sync
        mock_searcher._logger = Mock()
        mock_searcher.bm25_index = Mock()
        mock_searcher.dense_index = Mock()
        mock_searcher.reranking_engine = None
        mock_searcher.search_executor = Mock()
        mock_searcher.multi_hop_searcher = Mock()
        mock_searcher._graph_storage = Mock()  # Old reference

        # Call the REAL clear_index method
        HybridSearcher.clear_index(mock_searcher)

        # Verify _graph_storage was updated to match new dense_index._graph.storage
        # Note: clear_index() sets self._graph_storage directly, not via property setter
        self.assertEqual(mock_searcher._graph_storage, mock_graph_storage)
        self.assertIsNotNone(mock_searcher._graph_storage)

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_save_index_with_valid_graph(self, mock_graph_storage):
        """Test that save_index() saves graph correctly when storage is valid."""
        # Create mock graph storage with nodes
        mock_storage = Mock()
        mock_storage.graph = Mock()
        mock_storage.graph.number_of_nodes.return_value = 100
        mock_storage.__len__ = Mock(return_value=100)  # Add __len__ support
        mock_graph_storage.return_value = mock_storage

        # Create CodeIndexManager with project_id
        indexer = CodeIndexManager(
            str(self.storage_dir), embedder=None, project_id=self.project_id
        )

        # Verify graph is available
        self.assertIsNotNone(indexer._graph.storage)

        # Call save_index
        indexer.save_index()

        # Verify save was called on graph
        mock_storage.save.assert_called_once()

    @patch("search.graph_integration.CodeGraphStorage")
    @patch("search.graph_integration.GRAPH_STORAGE_AVAILABLE", True)
    def test_defensive_warning(self, mock_graph_storage):
        """Test defensive warning when graph storage is None.

        Regression test for bug where graph_storage could be None during save_index(),
        causing silent failure to save graph. Now logs warning instead of failing silently.
        """
        # Create mock storage
        mock_storage = Mock()
        mock_storage.graph = Mock()
        mock_storage.graph.number_of_nodes.return_value = 0
        mock_graph_storage.return_value = mock_storage

        # Create CodeIndexManager with project_id
        indexer = CodeIndexManager(
            str(self.storage_dir), embedder=None, project_id=self.project_id
        )

        # Simulate graph storage being None (bug scenario)
        indexer._graph = GraphIntegration(None, self.storage_dir)
        self.assertIsNone(indexer._graph.storage)

        # Call save_index - should log warning but not crash
        with self.assertLogs("search.indexer", level="WARNING") as log_context:
            indexer.save_index()
            # Verify warning was logged
            self.assertTrue(
                any(
                    "[SAVE] Graph storage is None" in message
                    for message in log_context.output
                )
            )

    def test_graph_storage_none_without_project_id(self):
        """Test that graph storage stays None when project_id is None."""
        # Create CodeIndexManager without project_id
        indexer = CodeIndexManager(
            str(self.storage_dir), embedder=None, project_id=None
        )

        # Verify graph storage is None
        self.assertIsNone(indexer._graph.storage)

        # Save should not crash even with None storage and None project_id
        indexer.save_index()

        # Verify still None
        self.assertIsNone(indexer._graph.storage)
