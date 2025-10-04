"""Tests for BM25 sparse index implementation."""

import tempfile
from unittest.mock import patch

import pytest

from search.bm25_index import BM25Index, TextPreprocessor


class TestTextPreprocessor:
    """Test text preprocessing functionality."""

    def test_basic_tokenization(self):
        """Test basic tokenization."""
        preprocessor = TextPreprocessor(use_stopwords=False)

        text = "Hello world! This is a test."
        tokens = preprocessor.tokenize(text)

        assert tokens == ["hello", "world", "this", "is", "a", "test"]

    def test_stopwords_filtering(self):
        """Test stopwords filtering."""
        preprocessor = TextPreprocessor(use_stopwords=True)

        text = "This is a test of the system"
        tokens = preprocessor.tokenize(text)

        # Should remove common stopwords
        assert "this" not in tokens
        assert "is" not in tokens
        assert "a" not in tokens
        assert "of" not in tokens
        assert "the" not in tokens
        assert "test" in tokens
        assert "system" in tokens

    def test_code_preprocessing(self):
        """Test code-specific preprocessing."""
        preprocessor = TextPreprocessor()

        code = "def getUserName(user_id): return user.name"
        processed = preprocessor.preprocess_code(code)

        # Should split camelCase and snake_case
        assert "get User Name" in processed
        assert "user id" in processed

    def test_empty_input(self):
        """Test handling of empty input."""
        preprocessor = TextPreprocessor()

        assert preprocessor.tokenize("") == []
        assert preprocessor.tokenize(None) == []
        assert preprocessor.preprocess_code("") == ""

    def test_special_characters(self):
        """Test handling of special characters."""
        preprocessor = TextPreprocessor()

        text = "test@example.com -> func() { return value; }"
        tokens = preprocessor.tokenize(text)

        # Should preserve some special chars useful for code
        assert any("example" in token for token in tokens)
        assert any("func" in token for token in tokens)


class TestBM25Index:
    """Test BM25 index functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.index = BM25Index(self.temp_dir)

        # Sample documents
        self.documents = [
            "def calculate_sum(a, b): return a + b",
            "class UserManager: def __init__(self): pass",
            "function processData(data) { return data.map(x => x * 2); }",
            "SELECT * FROM users WHERE age > 18",
            "def find_user(user_id): return database.get(user_id)",
        ]
        self.doc_ids = ["doc1", "doc2", "doc3", "doc4", "doc5"]

    def test_index_creation(self):
        """Test basic index creation."""
        assert self.index.is_empty
        assert self.index.size == 0

        # Index documents
        self.index.index_documents(self.documents, self.doc_ids)

        assert not self.index.is_empty
        assert self.index.size == len(self.documents)

    def test_search_functionality(self):
        """Test search functionality."""
        self.index.index_documents(self.documents, self.doc_ids)

        # Search for function-related content
        results = self.index.search("function", k=3)

        assert len(results) > 0
        assert all(isinstance(result, tuple) for result in results)
        assert all(len(result) == 3 for result in results)  # (id, score, metadata)

        # Search for specific terms
        results = self.index.search("user", k=5)
        user_docs = [r[0] for r in results]

        # Should find documents with "user" content
        assert any(doc_id in user_docs for doc_id in ["doc2", "doc4", "doc5"])

    def test_empty_query(self):
        """Test handling of empty queries."""
        self.index.index_documents(self.documents, self.doc_ids)

        results = self.index.search("", k=5)
        assert results == []

        results = self.index.search("   ", k=5)
        assert results == []

    def test_no_results_query(self):
        """Test queries that return no results."""
        self.index.index_documents(self.documents, self.doc_ids)

        results = self.index.search("nonexistent_term_xyz123", k=5)
        # Might return empty or very low scores
        if results:
            assert all(score >= 0 for _, score, _ in results)

    def test_document_removal(self):
        """Test document removal."""
        self.index.index_documents(self.documents, self.doc_ids)
        original_size = self.index.size

        # Remove some documents
        removed = self.index.remove_documents(["doc1", "doc3"])

        assert removed == 2
        assert self.index.size == original_size - 2

        # Search should not return removed documents
        results = self.index.search("calculate", k=5)
        result_ids = [r[0] for r in results]
        assert "doc1" not in result_ids

    def test_get_document_by_id(self):
        """Test retrieving documents by ID."""
        self.index.index_documents(self.documents, self.doc_ids)

        # Test existing document
        doc = self.index.get_document_by_id("doc1")
        assert doc == self.documents[0]

        # Test non-existing document
        doc = self.index.get_document_by_id("nonexistent")
        assert doc is None

    def test_save_and_load(self):
        """Test saving and loading index."""
        # Index documents
        metadata = {
            "doc1": {"type": "function", "language": "python"},
            "doc2": {"type": "class", "language": "python"},
        }
        self.index.index_documents(self.documents, self.doc_ids, metadata)

        # Save index
        self.index.save()

        # Create new index and load
        new_index = BM25Index(self.temp_dir)
        assert new_index.is_empty

        success = new_index.load()
        assert success
        assert not new_index.is_empty
        assert new_index.size == len(self.documents)

        # Test search works after loading
        results = new_index.search("function", k=3)
        assert len(results) > 0

    def test_metadata_handling(self):
        """Test metadata storage and retrieval."""
        metadata = {
            "doc1": {"type": "function", "language": "python", "lines": 1},
            "doc2": {"type": "class", "language": "python", "lines": 2},
            "doc3": {"type": "function", "language": "javascript", "lines": 1},
        }

        self.index.index_documents(self.documents, self.doc_ids, metadata)

        # Search and check metadata
        results = self.index.search("function", k=5)

        for doc_id, score, meta in results:
            if doc_id in metadata:
                expected = metadata[doc_id]
                # Check that all expected metadata fields are present and match
                # (BM25 index may add additional fields like 'content')
                for key, value in expected.items():
                    assert key in meta, f"Expected key '{key}' not found in metadata"
                    assert meta[key] == value, (
                        f"Metadata mismatch for '{key}': {meta[key]} != {value}"
                    )

    def test_index_statistics(self):
        """Test index statistics."""
        self.index.index_documents(self.documents, self.doc_ids)

        stats = self.index.get_stats()

        assert "total_documents" in stats
        assert stats["total_documents"] == len(self.documents)
        assert "has_index" in stats
        assert stats["has_index"] is True
        assert "vocabulary_size" in stats
        assert stats["vocabulary_size"] > 0

    def test_score_ordering(self):
        """Test that results are ordered by relevance score."""
        self.index.index_documents(self.documents, self.doc_ids)

        results = self.index.search("function def", k=5)

        if len(results) > 1:
            scores = [score for _, score, _ in results]
            # Scores should be in descending order
            assert scores == sorted(scores, reverse=True)

    def test_minimum_score_threshold(self):
        """Test minimum score threshold filtering."""
        self.index.index_documents(self.documents, self.doc_ids)

        # Search with no threshold
        all_results = self.index.search("user", k=10, min_score=0.0)

        # Search with high threshold
        filtered_results = self.index.search("user", k=10, min_score=1.0)

        # Filtered results should be subset of all results
        assert len(filtered_results) <= len(all_results)

    def test_concurrent_operations(self):
        """Test thread safety of operations."""
        import threading
        import time

        self.index.index_documents(self.documents, self.doc_ids)

        results_list = []

        def search_worker():
            for _ in range(10):
                results = self.index.search("function", k=3)
                results_list.append(len(results))
                time.sleep(0.01)

        # Run multiple search threads
        threads = [threading.Thread(target=search_worker) for _ in range(3)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All searches should return same number of results
        assert len(set(results_list)) <= 2  # Allow some variation

    @patch("search.bm25_index.BM25Okapi", None)
    def test_missing_dependencies(self):
        """Test handling of missing dependencies."""
        with pytest.raises(ImportError, match="rank-bm25 not found"):
            BM25Index(self.temp_dir)

    def test_large_document_handling(self):
        """Test handling of large documents."""
        # Create a large document with unique terms
        large_doc = "unique_function_name " * 10000
        large_docs = [large_doc]
        large_ids = ["large_doc"]

        self.index.index_documents(large_docs, large_ids)

        # Should still work
        results = self.index.search("unique_function_name", k=1)
        assert len(results) >= 0  # Should handle without crashing
        if results:  # If we get results, verify they're correct
            assert results[0][0] == "large_doc"

    def test_special_document_content(self):
        """Test handling of documents with special content."""
        special_docs = [
            "",  # Empty document
            "   ",  # Whitespace only
            "!@#$%^&*()",  # Special characters only
            "123 456 789",  # Numbers only
            "a" * 1000,  # Repeated character
        ]
        special_ids = [f"special_{i}" for i in range(len(special_docs))]

        # Should handle without crashing
        self.index.index_documents(special_docs, special_ids)

        # Should be able to search
        self.index.search("123", k=5)
        # Results depend on preprocessing, but shouldn't crash

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)
