"""Unit tests for ResultFactory."""


from search.reranker import SearchResult
from search.result_factory import ResultFactory


class TestResultFactory:
    """Test ResultFactory static methods."""

    def test_from_bm25_results_basic(self):
        """Test basic BM25 result conversion."""
        bm25_results = [
            ("chunk1", 0.85, {"file": "test.py", "content": "foo"}),
            ("chunk2", 0.72, {"file": "test.py", "content": "bar"}),
        ]

        results = ResultFactory.from_bm25_results(bm25_results)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].chunk_id == "chunk1"
        assert results[0].score == 0.85
        assert results[0].source == "bm25"
        assert results[0].rank == 0
        assert results[1].rank == 1

    def test_from_bm25_results_empty(self):
        """Test BM25 conversion with empty list."""
        results = ResultFactory.from_bm25_results([])
        assert results == []

    def test_from_bm25_results_preserves_metadata(self):
        """Test that BM25 conversion preserves all metadata fields."""
        bm25_results = [
            (
                "chunk1",
                0.85,
                {
                    "file": "test.py",
                    "content": "foo",
                    "docstring": "Test function",
                    "tags": ["test"],
                },
            )
        ]

        results = ResultFactory.from_bm25_results(bm25_results)

        assert results[0].metadata["file"] == "test.py"
        assert results[0].metadata["content"] == "foo"
        assert results[0].metadata["docstring"] == "Test function"
        assert results[0].metadata["tags"] == ["test"]

    def test_from_dense_results_basic(self):
        """Test basic dense result conversion."""
        dense_results = [
            ("chunk1", 0.92, {"file": "test.py", "content": "foo"}),
            ("chunk2", 0.88, {"file": "test.py", "content": "bar"}),
        ]

        results = ResultFactory.from_dense_results(dense_results)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].chunk_id == "chunk1"
        assert results[0].score == 0.92
        assert results[0].source == "semantic"
        assert results[0].rank == 0
        assert results[1].rank == 1

    def test_from_dense_results_empty(self):
        """Test dense conversion with empty list."""
        results = ResultFactory.from_dense_results([])
        assert results == []

    def test_from_dense_results_preserves_metadata(self):
        """Test that dense conversion preserves all metadata fields."""
        dense_results = [
            (
                "chunk1",
                0.92,
                {
                    "file": "test.py",
                    "content": "foo",
                    "embedding": [0.1, 0.2, 0.3],
                },
            )
        ]

        results = ResultFactory.from_dense_results(dense_results)

        assert results[0].metadata["file"] == "test.py"
        assert results[0].metadata["content"] == "foo"
        assert results[0].metadata["embedding"] == [0.1, 0.2, 0.3]

    def test_from_direct_lookup_basic(self):
        """Test direct lookup result creation."""
        chunk_id = "test.py:1-10:function:foo"
        metadata = {"file": "test.py", "content": "def foo(): pass"}

        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        assert isinstance(result, SearchResult)
        assert result.chunk_id == chunk_id
        assert result.score == 1.0
        assert result.source == "direct_lookup"
        assert result.rank == 0
        assert result.metadata["file"] == "test.py"

    def test_from_direct_lookup_normalizes_file_path(self):
        """Test that direct lookup normalizes file_path to file."""
        chunk_id = "test.py:1-10:function:foo"
        metadata = {"file_path": "test.py", "content": "def foo(): pass"}

        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        assert result.metadata["file"] == "test.py"
        assert "file_path" in result.metadata  # Original preserved

    def test_from_direct_lookup_normalizes_relative_path(self):
        """Test that direct lookup normalizes relative_path to file."""
        chunk_id = "test.py:1-10:function:foo"
        metadata = {"relative_path": "src/test.py", "content": "def foo(): pass"}

        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        assert result.metadata["file"] == "src/test.py"
        assert "relative_path" in result.metadata  # Original preserved

    def test_from_direct_lookup_prefers_file_path_over_relative_path(self):
        """Test that file_path takes precedence over relative_path."""
        chunk_id = "test.py:1-10:function:foo"
        metadata = {
            "file_path": "absolute/test.py",
            "relative_path": "relative/test.py",
            "content": "def foo(): pass",
        }

        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        # file_path should be preferred
        assert result.metadata["file"] == "absolute/test.py"

    def test_from_direct_lookup_preserves_existing_file_key(self):
        """Test that existing 'file' key is not overwritten."""
        chunk_id = "test.py:1-10:function:foo"
        metadata = {
            "file": "existing.py",
            "file_path": "other.py",
            "content": "def foo(): pass",
        }

        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        # Existing 'file' key should be preserved
        assert result.metadata["file"] == "existing.py"

    def test_from_direct_lookup_empty_fallback(self):
        """Test that direct lookup handles missing path keys gracefully."""
        chunk_id = "test.py:1-10:function:foo"
        metadata = {"content": "def foo(): pass"}  # No file/file_path/relative_path

        result = ResultFactory.from_direct_lookup(chunk_id, metadata)

        # Should default to empty string
        assert result.metadata["file"] == ""

    def test_bm25_and_dense_source_differ(self):
        """Test that BM25 and dense sources are correctly labeled."""
        bm25_results = [("chunk1", 0.85, {"file": "test.py"})]
        dense_results = [("chunk1", 0.92, {"file": "test.py"})]

        bm25 = ResultFactory.from_bm25_results(bm25_results)
        dense = ResultFactory.from_dense_results(dense_results)

        assert bm25[0].source == "bm25"
        assert dense[0].source == "semantic"
        assert bm25[0].source != dense[0].source

    def test_result_ordering_preserved(self):
        """Test that result order is preserved with correct ranks."""
        results = [
            ("chunk1", 0.95, {"file": "test.py"}),
            ("chunk2", 0.85, {"file": "test.py"}),
            ("chunk3", 0.75, {"file": "test.py"}),
            ("chunk4", 0.65, {"file": "test.py"}),
        ]

        converted = ResultFactory.from_bm25_results(results)

        for i, result in enumerate(converted):
            assert result.rank == i
            assert result.chunk_id == f"chunk{i+1}"
