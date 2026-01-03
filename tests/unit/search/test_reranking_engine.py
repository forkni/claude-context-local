"""Tests for reranking engine functionality.

Extracted from test_hybrid_search.py (Phase 3.2 refactoring).
"""

from unittest.mock import MagicMock, patch

import numpy as np

from search.reranker import SearchResult
from search.reranking_engine import RerankingEngine


class TestRerankingEngine:
    """Test reranking engine functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_embedder = MagicMock()
        self.mock_metadata_store = MagicMock()
        self.engine = RerankingEngine(
            embedder=self.mock_embedder, metadata_store=self.mock_metadata_store
        )

    @patch("search.reranking_engine.torch")
    def test_should_enable_neural_reranking_no_gpu(self, mock_torch):
        """Test neural reranking disabled when no GPU available."""
        mock_torch.cuda.is_available.return_value = False

        with patch("search.config.get_search_config") as mock_config:
            config = MagicMock()
            config.reranker.enabled = True
            mock_config.return_value = config

            result = self.engine.should_enable_neural_reranking()
            assert result is False

    @patch("search.reranking_engine.torch")
    def test_should_enable_neural_reranking_insufficient_vram(self, mock_torch):
        """Test neural reranking disabled with insufficient VRAM."""
        mock_torch.cuda.is_available.return_value = True
        mock_device = MagicMock()
        mock_device.total_memory = 2 * 1024**3  # 2GB total
        mock_torch.cuda.get_device_properties.return_value = mock_device
        mock_torch.cuda.memory_allocated.return_value = 0

        with patch("search.config.get_search_config") as mock_config:
            config = MagicMock()
            config.reranker.enabled = True
            config.reranker.min_vram_gb = 4  # Requires 4GB
            mock_config.return_value = config

            result = self.engine.should_enable_neural_reranking()
            assert result is False

    @patch("search.reranking_engine.torch")
    def test_should_enable_neural_reranking_sufficient_vram(self, mock_torch):
        """Test neural reranking enabled with sufficient VRAM."""
        mock_torch.cuda.is_available.return_value = True
        mock_device = MagicMock()
        mock_device.total_memory = 8 * 1024**3  # 8GB total
        mock_torch.cuda.get_device_properties.return_value = mock_device
        mock_torch.cuda.memory_allocated.return_value = 0

        with patch("search.config.get_search_config") as mock_config:
            config = MagicMock()
            config.reranker.enabled = True
            config.reranker.min_vram_gb = 4  # Requires 4GB
            mock_config.return_value = config

            result = self.engine.should_enable_neural_reranking()
            assert result is True

    def test_rerank_by_query_empty_results(self):
        """Test reranking with empty results."""
        results = self.engine.rerank_by_query("test query", [], k=5)
        assert results == []

    def test_rerank_by_query_embedding_based(self):
        """Test embedding-based reranking."""
        # Create test results
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
            SearchResult(chunk_id="chunk3", score=0.6, metadata={}),
        ]

        # Mock embedder and metadata
        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        chunk_embeddings = {
            "chunk1": np.array([0.8, 0.6, 0.0]),  # similarity ~0.8
            "chunk2": np.array([0.0, 1.0, 0.0]),  # similarity ~0.0
            "chunk3": np.array([1.0, 0.0, 0.0]),  # similarity ~1.0
        }

        def mock_get(chunk_id):
            return {"embedding": chunk_embeddings.get(chunk_id).tolist()}

        self.mock_metadata_store.get.side_effect = mock_get

        # Rerank - prevent neural reranking from interfering
        with patch.object(
            self.engine, "should_enable_neural_reranking", return_value=False
        ):
            reranked = self.engine.rerank_by_query(
                "test query", results, k=3, search_mode="semantic"
            )

        # Check ordering - chunk3 should be first (similarity=1.0)
        assert len(reranked) == 3
        assert reranked[0].chunk_id == "chunk3"
        assert reranked[0].score > reranked[1].score

    def test_rerank_by_query_no_embedder(self):
        """Test reranking without embedder (keeps original scores)."""
        engine = RerankingEngine(embedder=None, metadata_store=self.mock_metadata_store)

        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
        ]

        # Prevent neural reranking from interfering with score-based sorting
        with patch.object(engine, "should_enable_neural_reranking", return_value=False):
            reranked = engine.rerank_by_query(
                "test query", results, k=2, search_mode="bm25"
            )

        # Should keep original ordering (sorted by score)
        assert len(reranked) == 2
        assert reranked[0].chunk_id == "chunk2"  # Higher score
        assert reranked[1].chunk_id == "chunk1"

    @patch("search.reranking_engine.NeuralReranker")
    def test_shutdown_cleans_up_neural_reranker(self, mock_neural_reranker_class):
        """Test shutdown method cleans up neural reranker."""
        mock_reranker = MagicMock()
        self.engine.neural_reranker = mock_reranker

        self.engine.shutdown()

        mock_reranker.cleanup.assert_called_once()
        assert self.engine.neural_reranker is None

    def test_shutdown_without_neural_reranker(self):
        """Test shutdown without neural reranker doesn't error."""
        self.engine.neural_reranker = None
        self.engine.shutdown()  # Should not raise

    def test_rerank_with_precomputed_embedding(self):
        """Test reranking with pre-computed query embedding."""
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
        ]

        query_emb = np.array([1.0, 0.0, 0.0])
        chunk_emb = np.array([1.0, 0.0, 0.0])

        self.mock_metadata_store.get.return_value = {"embedding": chunk_emb.tolist()}

        # Pass pre-computed embedding - embedder should NOT be called
        reranked = self.engine.rerank_by_query(
            "test query", results, k=1, search_mode="hybrid", query_embedding=query_emb
        )

        self.mock_embedder.embed_query.assert_not_called()
        assert len(reranked) == 1

    def test_rerank_handles_missing_embeddings(self):
        """Test reranking gracefully handles missing chunk embeddings."""
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
        ]

        query_emb = np.array([1.0, 0.0, 0.0])
        self.mock_embedder.embed_query.return_value = query_emb

        # chunk1 has embedding, chunk2 doesn't
        def mock_get(chunk_id):
            if chunk_id == "chunk1":
                return {"embedding": [0.8, 0.6, 0.0]}
            return {}  # No embedding

        self.mock_metadata_store.get.side_effect = mock_get

        # Should not raise, keeps original score for chunk2
        reranked = self.engine.rerank_by_query(
            "test query", results, k=2, search_mode="semantic"
        )

        assert len(reranked) == 2

    @patch("search.reranking_engine.torch")
    @patch("search.reranking_engine.NeuralReranker")
    def test_neural_reranker_reload_after_disable_reenable(
        self, mock_neural_reranker_class, mock_torch
    ):
        """Test neural reranker properly reloads after disable/re-enable cycle.

        Regression test for Issue 1: Reranker doesn't reload after disable/re-enable.
        The cached _neural_reranking_enabled flag prevented config re-evaluation.
        """
        # Setup: GPU available with sufficient VRAM
        mock_torch.cuda.is_available.return_value = True
        mock_device = MagicMock()
        mock_device.total_memory = 8 * 1024**3  # 8GB
        mock_torch.cuda.get_device_properties.return_value = mock_device
        mock_torch.cuda.memory_allocated.return_value = 0

        # Mock NeuralReranker
        mock_reranker_instance = MagicMock()
        mock_neural_reranker_class.return_value = mock_reranker_instance

        # Create test results
        results = [
            SearchResult(chunk_id="chunk1", score=0.5, metadata={}),
            SearchResult(chunk_id="chunk2", score=0.7, metadata={}),
        ]

        # Phase 1: Enable neural reranking
        with patch("search.config.get_search_config") as mock_config:
            config = MagicMock()
            config.reranker.enabled = True
            config.reranker.min_vram_gb = 4
            config.reranker.model_name = "BAAI/bge-reranker-v2-m3"
            config.reranker.batch_size = 16
            config.reranker.top_k_candidates = 50
            mock_config.return_value = config

            # First search - should initialize reranker
            mock_reranker_instance.rerank.return_value = results
            self.engine.rerank_by_query("test query", results, k=2)

            assert self.engine.neural_reranker is not None
            assert mock_neural_reranker_class.call_count == 1

        # Phase 2: Disable neural reranking
        with patch("search.config.get_search_config") as mock_config:
            config = MagicMock()
            config.reranker.enabled = False  # Disabled
            mock_config.return_value = config

            # Second search - should cleanup reranker
            self.engine.rerank_by_query("test query", results, k=2)

            mock_reranker_instance.cleanup.assert_called_once()
            assert self.engine.neural_reranker is None

        # Phase 3: Re-enable neural reranking (THIS WAS BROKEN BEFORE FIX)
        with patch("search.config.get_search_config") as mock_config:
            config = MagicMock()
            config.reranker.enabled = True  # Re-enabled
            config.reranker.min_vram_gb = 4
            config.reranker.model_name = "BAAI/bge-reranker-v2-m3"
            config.reranker.batch_size = 16
            config.reranker.top_k_candidates = 50
            mock_config.return_value = config

            # Third search - should RE-INITIALIZE reranker
            mock_reranker_instance.rerank.return_value = results
            self.engine.rerank_by_query("test query", results, k=2)

            # Key assertion: Reranker should be reloaded (not None)
            assert self.engine.neural_reranker is not None
            assert (
                mock_neural_reranker_class.call_count == 2
            )  # Called twice (init + re-init)
            assert (
                mock_reranker_instance.rerank.call_count == 2
            )  # Used in phase 1 and 3
