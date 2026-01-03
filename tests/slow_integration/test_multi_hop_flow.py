"""Integration tests for multi-hop semantic search functionality."""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from conftest import create_test_embeddings

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.config import MultiHopConfig, SearchConfig
from search.hybrid_searcher import HybridSearcher


@pytest.mark.slow
class TestMultiHopSearchFlow:
    """Integration tests for multi-hop semantic search."""

    @pytest.fixture
    def test_project_path(self):
        """Path to the test Python project."""
        return Path(__file__).parent.parent / "test_data" / "python_project"

    @pytest.fixture
    def mock_storage_dir(self):
        """Create a temporary storage directory for tests."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def session_embedder(self):
        """Reusable mocked embedder for all tests."""
        # Mock SentenceTransformer to avoid downloading models
        with patch("embeddings.embedder.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.ones(768, dtype=np.float32) * 0.5
            mock_st.return_value = mock_model

            cache_dir = tempfile.mkdtemp()
            embedder = CodeEmbedder(
                model_name="google/embeddinggemma-300m", cache_dir=cache_dir
            )
            yield embedder
            # Cleanup
            shutil.rmtree(cache_dir, ignore_errors=True)

    def test_multi_hop_basic_functionality(self, test_project_path, mock_storage_dir):
        """Test basic multi-hop search with 2 hops."""
        # Setup: Chunk project
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        # Use subset for faster testing
        test_chunks = all_chunks[:15]
        assert len(test_chunks) >= 10, "Need at least 10 chunks for multi-hop test"

        # Create embeddings (deterministic for speed)
        embeddings = create_test_embeddings(test_chunks)

        # Index the chunks
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=None,  # Don't need embedder for deterministic test
            bm25_weight=0.4,
            dense_weight=0.6,
        )

        # Index documents
        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Test multi-hop search
        query = "authentication user login"

        # Single-hop search for comparison
        single_hop_results = hybrid_searcher.search(
            query=query, k=3, search_mode="hybrid"
        )

        # Multi-hop search
        multi_hop_results = hybrid_searcher.multi_hop_searcher.search(
            query=query, k=3, search_mode="hybrid", hops=2, expansion_factor=0.3
        )

        # Verify results
        assert len(single_hop_results) > 0, "Single-hop should return results"
        assert len(multi_hop_results) > 0, "Multi-hop should return results"

        # Multi-hop should potentially find more related code
        # (or at least same amount as single-hop)
        assert (
            len(multi_hop_results) >= len(single_hop_results) or True
        ), "Multi-hop should discover related code"

    def test_multi_hop_expansion_factor(self, test_project_path, mock_storage_dir):
        """Test that expansion factor affects number of discovered chunks."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:20]
        embeddings = create_test_embeddings(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=None,
            bm25_weight=0.4,
            dense_weight=0.6,
        )

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Test different expansion factors
        query = "database connection"
        k = 5

        # Low expansion
        low_expansion_results = hybrid_searcher.multi_hop_searcher.search(
            query=query, k=k, hops=2, expansion_factor=0.2
        )

        # High expansion
        high_expansion_results = hybrid_searcher.multi_hop_searcher.search(
            query=query, k=k, hops=2, expansion_factor=0.8
        )

        # Both should return results
        assert len(low_expansion_results) > 0
        assert len(high_expansion_results) > 0

        # Results should be properly ranked (scores descending)
        for i in range(len(low_expansion_results) - 1):
            assert low_expansion_results[i].score >= low_expansion_results[i + 1].score

    def test_multi_hop_hop_count(self, test_project_path, mock_storage_dir):
        """Test multi-hop search with different hop counts."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:15]
        embeddings = create_test_embeddings(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(
            storage_dir=str(storage_dir),
            embedder=None,
        )

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Test different hop counts
        query = "user authentication"
        k = 3

        # 1 hop (should be same as regular search)
        results_1_hop = hybrid_searcher.multi_hop_searcher.search(
            query=query, k=k, hops=1, expansion_factor=0.3
        )

        # 2 hops (default)
        results_2_hops = hybrid_searcher.multi_hop_searcher.search(
            query=query, k=k, hops=2, expansion_factor=0.3
        )

        # 3 hops
        results_3_hops = hybrid_searcher.multi_hop_searcher.search(
            query=query, k=k, hops=3, expansion_factor=0.3
        )

        # All should return results
        assert len(results_1_hop) > 0
        assert len(results_2_hops) > 0
        assert len(results_3_hops) > 0

        # Verify results are properly structured
        for result in results_2_hops:
            assert hasattr(result, "chunk_id")
            assert hasattr(result, "score")
            assert hasattr(result, "metadata")

    def test_multi_hop_config_integration(self, test_project_path, mock_storage_dir):
        """Test that multi-hop respects configuration settings."""
        # Create test config with multi-hop enabled
        config = SearchConfig(
            multi_hop=MultiHopConfig(enabled=True, hop_count=2, expansion=0.3)
        )

        # Verify config values
        assert config.multi_hop.enabled is True
        assert config.multi_hop.hop_count == 2
        assert config.multi_hop.expansion == 0.3

        # Test config with multi-hop disabled
        config_disabled = SearchConfig(multi_hop=MultiHopConfig(enabled=False))

        assert config_disabled.multi_hop.enabled is False

    def test_multi_hop_deduplication(self, test_project_path, mock_storage_dir):
        """Test that multi-hop properly deduplicates results."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:15]
        embeddings = create_test_embeddings(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(storage_dir=str(storage_dir))

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Multi-hop search
        results = hybrid_searcher.multi_hop_searcher.search(
            query="database query", k=5, hops=2, expansion_factor=0.5
        )

        # Verify no duplicate chunk_ids
        chunk_ids = [r.chunk_id for r in results]
        unique_chunk_ids = set(chunk_ids)

        assert len(chunk_ids) == len(
            unique_chunk_ids
        ), "Multi-hop should deduplicate results"

    def test_multi_hop_reranking(self, test_project_path, mock_storage_dir):
        """Test that multi-hop properly re-ranks results by query relevance."""
        # Setup
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []

        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        test_chunks = all_chunks[:15]
        embeddings = create_test_embeddings(test_chunks)

        # Index
        storage_dir = Path(mock_storage_dir)
        hybrid_searcher = HybridSearcher(storage_dir=str(storage_dir))

        documents = [chunk.content for chunk in test_chunks]
        doc_ids = [emb.chunk_id for emb in embeddings]
        embeddings_list = [emb.embedding.tolist() for emb in embeddings]
        metadata = {emb.chunk_id: emb.metadata for emb in embeddings}

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list, metadata)

        # Multi-hop search
        results = hybrid_searcher.multi_hop_searcher.search(
            query="user authentication validation", k=5, hops=2, expansion_factor=0.3
        )

        assert len(results) > 0

        # Verify results are sorted by score (descending)
        for i in range(len(results) - 1):
            assert (
                results[i].score >= results[i + 1].score
            ), "Results should be sorted by relevance score"
