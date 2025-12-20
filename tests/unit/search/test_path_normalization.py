"""Unit tests for path normalization in chunk IDs.

Tests the fixes for Issue 1 (direct chunk_id lookup failure) and Issue 2 (Phase 3
relationships empty) by verifying path separator normalization works correctly
across Windows/Unix platforms.

Root Cause: JSON double-escaping of Windows backslashes in MCP transport + path
separator mismatches between graph edges and chunk_id lookups.

Fix: Multi-variant lookup that handles all escaping scenarios + normalization at
chunk_id creation and edge storage.
"""

import pytest

from search.indexer import CodeIndexManager
from search.metadata import MetadataStore


class TestChunkIdNormalization:
    """Test normalize_chunk_id() helper function."""

    def test_normalize_backslash_to_forward_slash(self):
        """Windows backslash paths should normalize to forward slash."""
        chunk_id = r"search\reranker.py:36-137:method:rerank"
        result = MetadataStore.normalize_chunk_id(chunk_id)
        assert result == "search/reranker.py:36-137:method:rerank"

    def test_normalize_already_forward_slash(self):
        """Forward slash paths should remain unchanged."""
        chunk_id = "search/reranker.py:36-137:method:rerank"
        result = MetadataStore.normalize_chunk_id(chunk_id)
        assert result == "search/reranker.py:36-137:method:rerank"

    def test_normalize_mixed_separators(self):
        """Mixed path separators should all become forward slash."""
        chunk_id = r"mcp_server\tools/impact_analysis.py:71-500:class:Analyzer"
        result = MetadataStore.normalize_chunk_id(chunk_id)
        assert result == "mcp_server/tools/impact_analysis.py:71-500:class:Analyzer"

    def test_normalize_nested_paths(self):
        """Deeply nested paths should normalize correctly."""
        chunk_id = r"graph\relationship_extractors\type_extractor.py:20-356:class:TypeAnnotationExtractor"
        result = MetadataStore.normalize_chunk_id(chunk_id)
        assert (
            result
            == "graph/relationship_extractors/type_extractor.py:20-356:class:TypeAnnotationExtractor"
        )

    def test_normalize_preserves_colon_structure(self):
        """Normalization should not affect colon separators in chunk_id format."""
        chunk_id = r"file.py:10-20:function:my_func"
        result = MetadataStore.normalize_chunk_id(chunk_id)
        assert result.count(":") == 3  # file:lines:type:name
        assert result == "file.py:10-20:function:my_func"


class TestChunkIdVariants:
    """Test get_chunk_id_variants() helper function."""

    def test_variants_include_original(self):
        """First variant should always be the original chunk_id."""
        chunk_id = "search/reranker.py:36-137:method:rerank"
        variants = MetadataStore.get_chunk_id_variants(chunk_id)
        assert variants[0] == chunk_id

    def test_variants_include_un_double_escaped(self):
        """Should include un-double-escaped variant to fix MCP bug."""
        chunk_id = r"search\\reranker.py:36-137:method:rerank"
        variants = MetadataStore.get_chunk_id_variants(chunk_id)
        # Un-double-escape: \\\\ -> \\
        assert r"search\reranker.py:36-137:method:rerank" in variants

    def test_variants_include_forward_slash(self):
        """Should include forward slash variant for cross-platform compat."""
        chunk_id = r"search\reranker.py:36-137:method:rerank"
        variants = MetadataStore.get_chunk_id_variants(chunk_id)
        assert "search/reranker.py:36-137:method:rerank" in variants

    def test_variants_include_backslash(self):
        """Should include backslash variant to match Windows storage."""
        chunk_id = "search/reranker.py:36-137:method:rerank"
        variants = MetadataStore.get_chunk_id_variants(chunk_id)
        assert r"search\reranker.py:36-137:method:rerank" in variants

    def test_variants_deduplicated(self):
        """Duplicate variants should be removed."""
        chunk_id = "search/reranker.py:36-137:method:rerank"
        variants = MetadataStore.get_chunk_id_variants(chunk_id)
        # Should not have duplicates
        assert len(variants) == len(set(variants))

    def test_variants_order_preserved(self):
        """Variants should be in priority order: original, un-escaped, forward, back."""
        chunk_id = r"search\reranker.py:36-137:method:rerank"
        variants = MetadataStore.get_chunk_id_variants(chunk_id)
        # Original first
        assert variants[0] == chunk_id
        # Others follow (exact order may vary due to deduplication)
        assert len(variants) >= 2


class TestChunkIdLookup:
    """Test get_chunk_by_id() multi-variant lookup."""

    @pytest.fixture
    def mock_index_manager(self, tmp_path):
        """Create a mock CodeIndexManager with a test metadata database."""
        storage_dir = tmp_path / "test_index"
        storage_dir.mkdir()

        # Create index manager
        manager = CodeIndexManager(storage_dir=str(storage_dir))

        # Mock the metadata with test data
        test_metadata = {
            "chunk_id": r"search\reranker.py:36-137:method:rerank",
            "file_path": r"search\reranker.py",
            "start_line": 36,
            "end_line": 137,
            "chunk_type": "method",
            "name": "rerank",
        }

        # Store with Windows backslash (as it would be indexed on Windows)
        manager.metadata_store.set(
            r"search\reranker.py:36-137:method:rerank",
            index_id=0,
            metadata=test_metadata,
        )

        return manager

    def test_lookup_with_exact_match(self, mock_index_manager):
        """Exact match should work (original behavior)."""
        result = mock_index_manager.get_chunk_by_id(
            r"search\reranker.py:36-137:method:rerank"
        )
        assert result is not None
        assert result["name"] == "rerank"

    def test_lookup_with_double_escaped(self, mock_index_manager):
        """Double-escaped path (MCP bug) should find the chunk."""
        # This is what MCP transport sends due to JSON escaping
        result = mock_index_manager.get_chunk_by_id(
            r"search\\reranker.py:36-137:method:rerank"
        )
        assert result is not None
        assert result["name"] == "rerank"

    def test_lookup_with_forward_slash(self, mock_index_manager):
        """Forward slash variant should find Windows-indexed chunk."""
        result = mock_index_manager.get_chunk_by_id(
            "search/reranker.py:36-137:method:rerank"
        )
        assert result is not None
        assert result["name"] == "rerank"

    def test_lookup_nonexistent_returns_none(self, mock_index_manager):
        """Non-existent chunk_id should return None (not raise error)."""
        result = mock_index_manager.get_chunk_by_id("nonexistent.py:1-10:function:foo")
        assert result is None

    def test_lookup_all_variants_return_same_chunk(self, mock_index_manager):
        """All path separator variants should return identical chunk."""
        variants = [
            r"search\reranker.py:36-137:method:rerank",
            r"search\\reranker.py:36-137:method:rerank",
            "search/reranker.py:36-137:method:rerank",
        ]

        results = [mock_index_manager.get_chunk_by_id(v) for v in variants]

        # All should succeed
        assert all(r is not None for r in results)

        # All should return same name
        names = [r["name"] for r in results]
        assert all(n == "rerank" for n in names)


class TestCrossPlatformPaths:
    """Test cross-platform path handling scenarios."""

    def test_windows_path_indexing(self):
        """Simulate indexing on Windows (backslash paths)."""
        # This is what happens during chunking on Windows
        windows_path = r"mcp_server\tools\code_relationship_analyzer.py"
        normalized = MetadataStore.normalize_chunk_id(
            f"{windows_path}:71-500:class:CodeRelationshipAnalyzer"
        )

        # Should normalize to forward slash
        assert "/" in normalized
        assert "\\" not in normalized

    def test_unix_path_indexing(self):
        """Simulate indexing on Unix (forward slash paths)."""
        unix_path = "mcp_server/tools/code_relationship_analyzer.py"
        normalized = MetadataStore.normalize_chunk_id(
            f"{unix_path}:71-500:class:CodeRelationshipAnalyzer"
        )

        # Should remain forward slash
        assert "/" in normalized
        assert "\\" not in normalized

    def test_cross_platform_lookup(self):
        """Chunk indexed on Windows should be findable with Unix paths."""
        # Indexed on Windows
        indexed_id = r"search\reranker.py:36-137:method:rerank"

        # Looked up from Unix or after normalization
        lookup_id = "search/reranker.py:36-137:method:rerank"

        # Get variants for lookup
        variants = MetadataStore.get_chunk_id_variants(lookup_id)

        # Windows indexed path should be in variants
        assert (
            indexed_id in variants
            or r"search\reranker.py:36-137:method:rerank" in variants
        )


class TestRegressionIssue1:
    """Regression tests for Issue 1: Direct chunk_id lookup failure.

    Issue: search_code returns chunk_id with backslashes on Windows. When this
    chunk_id is passed back to search_code for direct lookup, it fails with
    "Chunk not found" due to JSON double-escaping in MCP transport.

    Fix: Multi-variant lookup tries all path separator combinations.
    """

    @pytest.fixture
    def simulated_mcp_scenario(self, tmp_path):
        """Simulate the exact MCP scenario that caused the bug."""
        storage_dir = tmp_path / "mcp_test"
        storage_dir.mkdir()

        manager = CodeIndexManager(storage_dir=str(storage_dir))

        # Chunk indexed with Windows backslash (real scenario)
        test_metadata = {
            "chunk_id": r"search\reranker.py:36-137:method:rerank",
            "file_path": r"search\reranker.py",
            "name": "rerank",
        }
        manager.metadata_store.set(
            r"search\reranker.py:36-137:method:rerank",
            index_id=0,
            metadata=test_metadata,
        )

        return manager

    def test_issue1_regression(self, simulated_mcp_scenario):
        """
        Regression test for Issue 1.

        Scenario:
        1. search_code returns: {"chunk_id": "search\\reranker.py:..."}
        2. JSON serialization: "search\\\\reranker.py" (escaped)
        3. Client receives and re-sends: chunk_id="search\\\\reranker.py"
        4. Server receives: "search\\\\\\\\reranker.py" (double-escaped!)
        5. Lookup should STILL work despite double-escaping

        Expected: Lookup succeeds (not "Chunk not found")
        """
        # What client sends (double-escaped due to MCP transport)
        double_escaped = r"search\\reranker.py:36-137:method:rerank"

        # This should NOT fail
        result = simulated_mcp_scenario.get_chunk_by_id(double_escaped)

        assert (
            result is not None
        ), "Issue 1 regression: Chunk not found with double-escaped path!"
        assert result["name"] == "rerank"
