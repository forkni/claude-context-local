#!/usr/bin/env python3
"""
Semantic Search Test
Tests the semantic search functionality with isolated test data.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from conftest import create_test_embeddings

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher


@pytest.mark.slow
class TestSemanticSearch:
    """Test semantic search functionality with isolated test index."""

    @pytest.fixture(autouse=True)
    def mock_embedder(self):
        """Mock SentenceTransformer to prevent model downloads."""

        def mock_encode(sentences, show_progress_bar=False):
            if isinstance(sentences, str):
                return np.ones(768, dtype=np.float32) * 0.5
            else:
                return np.ones((len(sentences), 768), dtype=np.float32) * 0.5

        with patch("embeddings.embedder.SentenceTransformer") as mock_st:
            mock_model = MagicMock()
            mock_model.encode.side_effect = mock_encode
            mock_model.get_sentence_embedding_dimension.return_value = 768
            mock_st.return_value = mock_model
            yield mock_st

    @pytest.fixture
    def test_project_path(self):
        """Path to the test Python project."""
        return Path(__file__).parent.parent / "test_data" / "python_project"

    @pytest.fixture
    def indexed_searcher(self, test_project_path, tmp_path):
        """Create a searcher with pre-indexed test data."""
        # Create index directory
        index_dir = tmp_path / "test_index"
        index_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        index_manager = CodeIndexManager(str(index_dir))
        embedder = CodeEmbedder(cache_dir=str(tmp_path / "models"))
        chunker = MultiLanguageChunker(str(test_project_path))

        # Get chunks from test project
        chunks = []
        for py_file in test_project_path.rglob("*.py"):
            file_chunks = chunker.chunk_file(str(py_file))
            chunks.extend(file_chunks)

        # Create embeddings
        embeddings = create_test_embeddings(chunks, embedder=None, embedding_dim=768)

        # Add to index
        index_manager.add_embeddings(embeddings)

        # Create searcher
        searcher = IntelligentSearcher(index_manager, embedder)

        yield searcher

        # Cleanup
        embedder.cleanup()

    def test_semantic_search_basic(self, indexed_searcher):
        """Test basic semantic search functionality."""
        # Test with different queries
        test_queries = [
            "database connection",
            "authentication login",
            "error handling",
        ]

        for query in test_queries:
            results = indexed_searcher.search(query, k=3)

            # Verify we got results
            assert isinstance(results, list), f"Query '{query}' should return list"
            assert len(results) > 0, f"Query '{query}' should return at least 1 result"

            # Verify result structure
            first_result = results[0]
            assert hasattr(first_result, "file_path"), "Result should have file_path"
            assert hasattr(first_result, "name"), "Result should have name"
            assert hasattr(
                first_result, "content_preview"
            ), "Result should have content_preview"
            assert hasattr(
                first_result, "similarity_score"
            ), "Result should have similarity_score"

            # Verify score is reasonable
            assert (
                0 <= first_result.similarity_score <= 1.0
            ), "Score should be normalized [0,1]"

    def test_semantic_search_ranking(self, indexed_searcher):
        """Test that search results have reasonable similarity scores."""
        query = "authentication"
        results = indexed_searcher.search(query, k=5)

        assert len(results) > 1, "Should return multiple results for ranking test"

        # Verify all results have scores
        for result in results:
            assert hasattr(
                result, "similarity_score"
            ), "All results should have similarity_score"
            assert (
                0 <= result.similarity_score <= 1.0
            ), f"Score {result.similarity_score} should be in [0,1]"

        # Verify we get a range of scores (not all identical)
        scores = [r.similarity_score for r in results]
        unique_scores = set(scores)
        assert len(unique_scores) > 1, "Should have varied similarity scores"

    def test_semantic_search_top_k(self, indexed_searcher):
        """Test that k parameter limits results correctly."""
        query = "function"

        # Test different k values
        for k in [1, 3, 5]:
            results = indexed_searcher.search(query, k=k)
            assert len(results) <= k, f"Should return at most {k} results when k={k}"

    def test_semantic_search_empty_results(self, indexed_searcher):
        """Test behavior with query that might return few results."""
        # Use a very specific query that might not match well
        query = "quantum_entanglement_processor"
        results = indexed_searcher.search(query, k=3)

        # Should still return results (even with low scores) or empty list
        assert isinstance(results, list), "Should return list even for obscure query"
        # Don't assert length > 0 since it's possible to get no matches

    def test_semantic_search_file_filtering(self, indexed_searcher):
        """Test that results come from appropriate files."""
        query = "authentication"
        results = indexed_searcher.search(query, k=5)

        assert len(results) > 0, "Should find authentication-related code"

        # Verify all results have valid file paths
        for result in results:
            assert result.file_path, "Each result should have a file path"
            assert isinstance(result.file_path, str), "File path should be string"
            # Should be Python files
            assert result.file_path.endswith(".py"), "Results should be from .py files"


if __name__ == "__main__":
    # Run via pytest
    pytest.main([__file__, "-v", "--tb=short"])
