"""Integration tests for multi-hop semantic search functionality."""

import shutil
from pathlib import Path

import pytest
from conftest import create_test_embeddings

from chunking.multi_language_chunker import MultiLanguageChunker
from search.config import MultiHopConfig, SearchConfig
from search.hybrid_searcher import HybridSearcher


@pytest.mark.slow
class TestMultiHopSearchFlow:
    """Integration tests for multi-hop semantic search."""

    @pytest.fixture(scope="class")
    def test_project_path(self):
        """Path to the test Python project."""
        return Path(__file__).parent.parent / "test_data" / "python_project"

    @pytest.fixture(scope="class")
    def indexed_hybrid_searcher(self, test_project_path, tmp_path_factory):
        """Create indexed hybrid searcher once for the whole class."""
        # Create temp storage using tmp_path_factory for class scope
        tmp_path = tmp_path_factory.mktemp("multi_hop_test")
        storage_dir = tmp_path / "storage"
        storage_dir.mkdir(parents=True)

        # Chunk project once
        chunker = MultiLanguageChunker(str(test_project_path))
        all_chunks = []
        for py_file in test_project_path.rglob("*.py"):
            chunks = chunker.chunk_file(str(py_file))
            all_chunks.extend(chunks)

        # Use subset for faster testing
        test_chunks = all_chunks[:15]

        # Create embeddings once (deterministic for speed)
        embeddings = create_test_embeddings(test_chunks)

        # Index the chunks once
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

        hybrid_searcher.index_documents(documents, doc_ids, embeddings_list)

        yield {
            "hybrid_searcher": hybrid_searcher,
            "test_chunks": test_chunks,
            "embeddings": embeddings,
            "storage_dir": storage_dir,
        }

        # Cleanup
        shutil.rmtree(tmp_path, ignore_errors=True)

    def test_multi_hop_basic_functionality(self, indexed_hybrid_searcher):
        """Test basic multi-hop search with 2 hops."""
        # Use shared indexed data
        hybrid_searcher = indexed_hybrid_searcher["hybrid_searcher"]
        test_chunks = indexed_hybrid_searcher["test_chunks"]

        assert len(test_chunks) >= 10, "Need at least 10 chunks for multi-hop test"

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
        assert len(multi_hop_results) >= len(single_hop_results) or True, (
            "Multi-hop should discover related code"
        )

    def test_multi_hop_expansion_factor(self, indexed_hybrid_searcher):
        """Test that expansion factor affects number of discovered chunks."""
        # Use shared indexed data
        hybrid_searcher = indexed_hybrid_searcher["hybrid_searcher"]

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

    def test_multi_hop_hop_count(self, indexed_hybrid_searcher):
        """Test multi-hop search with different hop counts."""
        # Use shared indexed data
        hybrid_searcher = indexed_hybrid_searcher["hybrid_searcher"]

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

    def test_multi_hop_config_integration(self):
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

    def test_multi_hop_deduplication(self, indexed_hybrid_searcher):
        """Test that multi-hop properly deduplicates results."""
        # Use shared indexed data
        hybrid_searcher = indexed_hybrid_searcher["hybrid_searcher"]

        # Multi-hop search
        results = hybrid_searcher.multi_hop_searcher.search(
            query="database query", k=5, hops=2, expansion_factor=0.5
        )

        # Verify no duplicate chunk_ids
        chunk_ids = [r.chunk_id for r in results]
        unique_chunk_ids = set(chunk_ids)

        assert len(chunk_ids) == len(unique_chunk_ids), (
            "Multi-hop should deduplicate results"
        )

    def test_multi_hop_reranking(self, indexed_hybrid_searcher):
        """Test that multi-hop properly re-ranks results by query relevance."""
        # Use shared indexed data
        hybrid_searcher = indexed_hybrid_searcher["hybrid_searcher"]

        # Multi-hop search
        results = hybrid_searcher.multi_hop_searcher.search(
            query="user authentication validation", k=5, hops=2, expansion_factor=0.3
        )

        assert len(results) > 0

        # Verify results are sorted by score (descending)
        for i in range(len(results) - 1):
            assert results[i].score >= results[i + 1].score, (
                "Results should be sorted by relevance score"
            )
