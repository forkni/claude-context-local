#!/usr/bin/env python3
"""
Semantic Search Test
Tests the semantic search functionality with isolated test data.
"""

from pathlib import Path

import pytest

from chunking.multi_language_chunker import MultiLanguageChunker
from embeddings.embedder import CodeEmbedder
from search.indexer import CodeIndexManager
from search.searcher import IntelligentSearcher
from tests.helpers.embeddings import create_test_embeddings


@pytest.mark.slow
class TestSemanticSearch:
    """Test semantic search functionality with isolated test index.

    Uses the real embedder (no mock): patching
    ``embeddings.embedder.SentenceTransformer`` is a no-op since the model is
    actually constructed in ``embeddings.model_loader``, so a prior version of
    this fixture silently loaded the real model anyway while lying about it
    with a hardcoded 768-dim stub. Building the index through the real
    embedder keeps query/index dimensions in agreement by construction,
    whatever the configured model's dimension is.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def test_project_path(cls):
        """Path to the test Python project."""
        return Path(__file__).parent.parent / "test_data" / "python_project"

    @pytest.fixture(scope="class")
    @classmethod
    def indexed_searcher(cls, test_project_path, tmp_path_factory):
        """Create a searcher with pre-indexed test data."""
        # Create index directory using tmp_path_factory for class scope
        tmp_path = tmp_path_factory.mktemp("semantic_search_test")
        index_dir = tmp_path / "test_index"
        index_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components. embedder is constructed before index_manager
        # and passed in so the FAISS dimension-validation guard is armed.
        embedder = CodeEmbedder(cache_dir=str(tmp_path / "models"))
        index_manager = CodeIndexManager(str(index_dir), embedder=embedder)
        chunker = MultiLanguageChunker(str(test_project_path))

        # Get chunks from test project
        chunks = []
        for py_file in test_project_path.rglob("*.py"):
            file_chunks = chunker.chunk_file(str(py_file))
            chunks.extend(file_chunks)

        # Create embeddings with the real embedder so the index dimension
        # always matches whatever the configured model actually produces.
        embeddings = create_test_embeddings(chunks, embedder=embedder)

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

            # Verify result structure (thin SearchResult: score + metadata)
            first_result = results[0]
            assert hasattr(first_result, "score"), "Result should have score"
            assert hasattr(first_result, "metadata"), "Result should have metadata"
            assert (
                "file_path" in first_result.metadata
                or "relative_path" in first_result.metadata
            ), "Result metadata should have file_path or relative_path"

            # Verify score is reasonable
            assert 0 <= first_result.score <= 1.0, "Score should be normalized [0,1]"

    def test_semantic_search_ranking(self, indexed_searcher):
        """Test that search results have reasonable similarity scores."""
        query = "authentication"
        results = indexed_searcher.search(query, k=5)

        assert len(results) > 1, "Should return multiple results for ranking test"

        # Verify all results have scores
        for result in results:
            assert hasattr(result, "score"), "All results should have score"
            assert 0 <= result.score <= 1.0, f"Score {result.score} should be in [0,1]"

        # Verify we get a range of scores (not all identical)
        scores = [r.score for r in results]
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

        # Verify all results have valid file paths (SearchResult carries this
        # in .metadata, not as a top-level attribute — see search/reranker.py)
        for result in results:
            file_path = result.metadata.get("file_path")
            assert file_path, "Each result should have a file path"
            assert isinstance(file_path, str), "File path should be string"
            # Should be Python files
            assert file_path.endswith(".py"), "Results should be from .py files"
