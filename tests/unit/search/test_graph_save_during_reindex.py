"""Regression tests for graph save during reindex operations."""

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from search.ego_graph_retriever import EgoGraphRetriever
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

    @staticmethod
    def _make_mock_graph_integration(storage, node_count):
        """Build a mock GraphIntegration whose truthiness matches the real class.

        A plain `Mock(spec=GraphIntegration)` does NOT implement `__len__` even
        though the spec class defines it — only `MagicMock` wires up magic
        methods from a spec. That gap is why the original version of this test
        passed even with the truthiness bug present: its mock was truthy no
        matter what, so it never exercised the "new graph has 0 nodes" case
        that made `if self.dense_index._graph:` evaluate False in production.
        """
        mock_graph_integration = MagicMock(spec=GraphIntegration)
        mock_graph_integration.storage = storage
        mock_graph_integration.__len__.return_value = node_count
        return mock_graph_integration

    def _make_mock_searcher(self, mock_dense_index):
        """Build a mock HybridSearcher with the attributes clear_index() touches."""
        mock_searcher = Mock(spec=HybridSearcher)

        mock_index_sync = Mock()
        mock_index_sync.dense_index = mock_dense_index
        mock_index_sync.bm25_index = Mock()

        mock_searcher.index_sync = mock_index_sync
        mock_searcher._logger = Mock()
        mock_searcher.bm25_index = Mock()
        mock_searcher.dense_index = Mock()
        mock_searcher.reranking_engine = None
        mock_searcher.search_executor = Mock()
        mock_searcher.multi_hop_searcher = Mock()
        old_graph_storage = Mock()  # Old (pre-clear) reference
        mock_searcher._graph_storage = old_graph_storage
        mock_searcher.multi_hop_searcher.graph_storage = old_graph_storage
        mock_searcher.ego_graph_retriever = EgoGraphRetriever(old_graph_storage)
        mock_searcher._metadata_cache = {}  # Added by BaseSearcher.__init__; cleared by clear_index()
        return mock_searcher

    def test_clear_index_resyncs_when_new_graph_is_empty(self):
        """clear_index() must re-sync graph_storage/_graph even when the freshly
        cleared graph has zero nodes.

        Regression test for the __len__-without-__bool__ trap: GraphIntegration
        defines __len__ (node count) but no __bool__, so Python falls back to
        `len(obj) != 0` for `bool(obj)`. A guard written as
        `if self.dense_index._graph:` is therefore False immediately after a
        full-reindex clear (0 nodes), silently skipping the re-sync and leaving
        self._graph/_graph_storage pointed at the stale pre-clear object for the
        rest of the reindex — which throws away 100% of that reindex's resolver
        edges. The fix uses an explicit `is not None` check instead.
        """
        mock_graph_storage = Mock()
        mock_graph_integration = self._make_mock_graph_integration(
            mock_graph_storage, node_count=0
        )
        # Sanity: confirm the mock actually reproduces the falsy-when-empty
        # behavior being tested against — if this assertion ever fails, the
        # test below would silently stop covering the bug.
        self.assertFalse(mock_graph_integration)

        mock_dense_index = Mock(spec=CodeIndexManager)
        mock_dense_index._graph = mock_graph_integration
        mock_searcher = self._make_mock_searcher(mock_dense_index)

        HybridSearcher.clear_index(mock_searcher)

        self.assertIs(mock_searcher._graph_storage, mock_graph_storage)
        # The re-sync must have rebuilt _graph via GraphIntegration.from_storage
        # (a real instance, not the mock) wrapping the same storage object.
        self.assertIsInstance(mock_searcher._graph, GraphIntegration)
        self.assertIs(mock_searcher._graph.storage, mock_graph_storage)
        # Regression: clear_index() previously left ego_graph_retriever and
        # multi_hop_searcher.graph_storage pointed at the old, emptied storage
        # object — silently zeroing ego-graph expansion and degrading
        # graph/hybrid multi-hop search until the server process restarted.
        self.assertIs(mock_searcher.ego_graph_retriever.graph, mock_graph_storage)
        self.assertIs(
            mock_searcher.ego_graph_retriever._gv._storage, mock_graph_storage
        )
        self.assertIs(
            mock_searcher.multi_hop_searcher.graph_storage, mock_graph_storage
        )

    def test_clear_index_resyncs_when_new_graph_is_nonempty(self):
        """Same re-sync must also happen when the new graph already has nodes.

        Pins the branch the original test covered, so a fix for the empty-graph
        case above can't accidentally regress this one.
        """
        mock_graph_storage = Mock()
        mock_graph_integration = self._make_mock_graph_integration(
            mock_graph_storage, node_count=100
        )
        self.assertTrue(mock_graph_integration)

        mock_dense_index = Mock(spec=CodeIndexManager)
        mock_dense_index._graph = mock_graph_integration
        mock_searcher = self._make_mock_searcher(mock_dense_index)

        HybridSearcher.clear_index(mock_searcher)

        self.assertIs(mock_searcher._graph_storage, mock_graph_storage)
        self.assertIsInstance(mock_searcher._graph, GraphIntegration)
        self.assertIs(mock_searcher._graph.storage, mock_graph_storage)
        self.assertIs(mock_searcher.ego_graph_retriever.graph, mock_graph_storage)
        self.assertIs(
            mock_searcher.ego_graph_retriever._gv._storage, mock_graph_storage
        )
        self.assertIs(
            mock_searcher.multi_hop_searcher.graph_storage, mock_graph_storage
        )

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
