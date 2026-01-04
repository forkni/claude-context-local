"""Unit tests for cAST greedy sibling merging algorithm."""

from unittest.mock import MagicMock

import pytest

from chunking.languages.base import (
    TreeSitterChunk,
    estimate_tokens,
)
from search.config import ChunkingConfig


class TestEstimateTokens:
    """Test token estimation function."""

    def test_whitespace_method_basic(self):
        """Whitespace method splits on spaces."""
        content = "def foo(): pass"
        assert estimate_tokens(content, "whitespace") == 3

    def test_whitespace_method_multiline(self):
        """Handles multiline content."""
        content = """def foo():
    x = 1
    return x"""
        tokens = estimate_tokens(content, "whitespace")
        assert tokens >= 6  # Approximate

    def test_empty_content(self):
        """Empty content returns 0."""
        assert estimate_tokens("", "whitespace") == 0

    def test_single_word(self):
        """Single word returns 1."""
        assert estimate_tokens("hello", "whitespace") == 1

    def test_complex_code(self):
        """Complex code with operators."""
        content = "x = foo(a, b) + bar(c)"
        tokens = estimate_tokens(content, "whitespace")
        # Whitespace splitting gives: ['x', '=', 'foo(a,', 'b)', '+', 'bar(c)'] = 6 tokens
        assert tokens == 6


class TestCreateMergedChunk:
    """Test merged chunk creation."""

    @pytest.fixture
    def chunker(self):
        """Create a concrete chunker for testing."""
        from chunking.languages.python import PythonChunker

        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def test_single_chunk_passthrough(self, chunker):
        """Single chunk returns unchanged."""
        chunk = TreeSitterChunk(
            content="def foo(): pass",
            start_line=1,
            end_line=1,
            node_type="function_definition",
            language="python",
            metadata={"name": "foo"},
        )
        result = chunker._create_merged_chunk([chunk])
        assert result is chunk

    def test_merge_two_chunks(self, chunker):
        """Two chunks merge correctly."""
        chunks = [
            TreeSitterChunk(
                content="def foo(): pass",
                start_line=1,
                end_line=1,
                node_type="function_definition",
                language="python",
                metadata={"name": "foo"},
                parent_class="MyClass",
            ),
            TreeSitterChunk(
                content="def bar(): pass",
                start_line=3,
                end_line=3,
                node_type="function_definition",
                language="python",
                metadata={"name": "bar"},
                parent_class="MyClass",
            ),
        ]
        result = chunker._create_merged_chunk(chunks)

        assert result.node_type == "merged"
        assert result.start_line == 1
        assert result.end_line == 3
        assert "def foo" in result.content
        assert "def bar" in result.content
        assert result.metadata["merged_count"] == 2
        assert result.metadata["merged_from"] == ["foo", "bar"]
        assert result.parent_class == "MyClass"

    def test_merge_preserves_language(self, chunker):
        """Merged chunk preserves language."""
        chunks = [
            TreeSitterChunk(
                content="x = 1",
                start_line=1,
                end_line=1,
                node_type="assignment",
                language="python",
                metadata={},
            ),
            TreeSitterChunk(
                content="y = 2",
                start_line=2,
                end_line=2,
                node_type="assignment",
                language="python",
                metadata={},
            ),
        ]
        result = chunker._create_merged_chunk(chunks)
        assert result.language == "python"

    def test_merge_preserves_parent_info(self, chunker):
        """Merged chunk preserves parent info from first chunk."""
        chunks = [
            TreeSitterChunk(
                content="def a(): pass",
                start_line=1,
                end_line=1,
                node_type="function_definition",
                language="python",
                metadata={
                    "name": "a",
                    "parent_name": "MyClass",
                    "parent_type": "class",
                },
                parent_class="MyClass",
            ),
            TreeSitterChunk(
                content="def b(): pass",
                start_line=3,
                end_line=3,
                node_type="function_definition",
                language="python",
                metadata={
                    "name": "b",
                    "parent_name": "MyClass",
                    "parent_type": "class",
                },
                parent_class="MyClass",
            ),
        ]
        result = chunker._create_merged_chunk(chunks)
        assert result.metadata["parent_name"] == "MyClass"
        assert result.metadata["parent_type"] == "class"


class TestGreedyMergeSmallChunks:
    """Test the cAST greedy sibling merging algorithm."""

    @pytest.fixture
    def chunker(self):
        """Create a concrete chunker for testing."""
        from chunking.languages.python import PythonChunker

        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def _make_chunk(
        self,
        name: str,
        tokens: int,
        parent_class: str = None,
        start_line: int = 1,
        end_line: int = 1,
    ) -> TreeSitterChunk:
        """Helper to create test chunks with specific token counts."""
        # Generate content with approximately `tokens` whitespace-separated words
        content = " ".join([f"word{i}" for i in range(tokens)])
        return TreeSitterChunk(
            content=content,
            start_line=start_line,
            end_line=end_line,
            node_type="function_definition",
            language="python",
            metadata={"name": name},
            parent_class=parent_class,
        )

    def test_empty_list(self, chunker):
        """Empty input returns empty output."""
        result = chunker._greedy_merge_small_chunks([])
        assert result == []

    def test_single_chunk(self, chunker):
        """Single chunk returns unchanged."""
        chunk = self._make_chunk("foo", tokens=30)
        result = chunker._greedy_merge_small_chunks([chunk])
        assert len(result) == 1
        assert result[0] is chunk

    def test_all_small_chunks_merge(self, chunker):
        """All small chunks merge into one."""
        chunks = [
            self._make_chunk("a", tokens=10, start_line=1, end_line=1),
            self._make_chunk("b", tokens=10, start_line=3, end_line=3),
            self._make_chunk("c", tokens=10, start_line=5, end_line=5),
        ]
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=1000
        )
        assert len(result) == 1
        assert result[0].node_type == "merged"
        assert result[0].metadata["merged_count"] == 3

    def test_large_chunk_not_merged(self, chunker):
        """Large chunks remain separate."""
        chunks = [
            self._make_chunk("small", tokens=10),
            self._make_chunk("large", tokens=100),
            self._make_chunk("small2", tokens=10),
        ]
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=1000
        )
        # Large chunk should be in results unchanged
        large_found = False
        for r in result:
            if r.metadata.get("name") == "large":
                large_found = True
                assert r.node_type == "function_definition"
        assert large_found

    def test_max_size_limit_prevents_merge(self, chunker):
        """Merging stops at max_merged_tokens."""
        chunks = [
            self._make_chunk("a", tokens=40, start_line=1, end_line=1),
            self._make_chunk("b", tokens=40, start_line=3, end_line=3),
        ]
        # max_merged_tokens=70 means these two (40+40=80) won't merge together
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=70
        )
        # Both are < 50 tokens, but together > 70, so each gets its own merged chunk
        assert len(result) == 2

    def test_different_parent_class_not_merged(self, chunker):
        """Chunks with different parent_class are not merged."""
        chunks = [
            self._make_chunk("a", tokens=10, parent_class="ClassA"),
            self._make_chunk("b", tokens=10, parent_class="ClassA"),
            self._make_chunk("c", tokens=10, parent_class="ClassB"),
            self._make_chunk("d", tokens=10, parent_class="ClassB"),
        ]
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=1000
        )
        # a+b should merge (same parent), c+d should merge (same parent)
        assert len(result) == 2
        assert all(r.node_type == "merged" for r in result)
        assert result[0].parent_class == "ClassA"
        assert result[1].parent_class == "ClassB"

    def test_none_parent_class_merged(self, chunker):
        """Chunks with None parent_class can merge."""
        chunks = [
            self._make_chunk("a", tokens=10, parent_class=None),
            self._make_chunk("b", tokens=10, parent_class=None),
        ]
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=1000
        )
        assert len(result) == 1
        assert result[0].node_type == "merged"

    def test_preserves_line_numbers(self, chunker):
        """Merged chunk has correct start/end lines."""
        chunks = [
            self._make_chunk("a", tokens=10, start_line=5, end_line=7),
            self._make_chunk("b", tokens=10, start_line=10, end_line=12),
            self._make_chunk("c", tokens=10, start_line=15, end_line=20),
        ]
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=1000
        )
        assert len(result) == 1
        assert result[0].start_line == 5
        assert result[0].end_line == 20

    def test_all_large_chunks_unchanged(self, chunker):
        """When all chunks are large, none are merged."""
        chunks = [
            self._make_chunk("a", tokens=100),
            self._make_chunk("b", tokens=100),
            self._make_chunk("c", tokens=100),
        ]
        result = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=1000
        )
        assert len(result) == 3
        assert all(r.node_type == "function_definition" for r in result)


class TestChunkCodeWithMerging:
    """Test chunk_code() with greedy merge integration."""

    @pytest.fixture
    def chunker(self):
        """Create a concrete chunker for testing."""
        from chunking.languages.python import PythonChunker

        try:
            return PythonChunker()
        except ValueError:
            pytest.skip("tree-sitter-python not installed")

    def test_merge_disabled_by_config(self, chunker):
        """Merge is skipped when disabled in config."""
        code = """
def a(): pass
def b(): pass
def c(): pass
"""
        config = ChunkingConfig(enable_greedy_merge=False)
        chunks = chunker.chunk_code(code, config=config)
        # Should have 3 separate function chunks
        assert len(chunks) >= 3

    def test_merge_enabled_by_config(self, chunker):
        """Merge is applied when enabled in config."""
        # Three tiny functions that should merge
        code = """
def a(): pass
def b(): pass
def c(): pass
"""
        config = ChunkingConfig(
            enable_greedy_merge=True,
            min_chunk_tokens=50,  # These functions are < 50 tokens
            max_merged_tokens=1000,
        )
        chunks = chunker.chunk_code(code, config=config)
        # All 3 tiny functions should merge into 1
        assert len(chunks) == 1
        assert chunks[0].node_type == "merged"

    def test_config_from_service_locator(self, chunker):
        """Config is fetched from ServiceLocator when not provided."""
        from mcp_server.services import ServiceLocator

        # Register a config with merge disabled
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig(enable_greedy_merge=False)

        locator = ServiceLocator.instance()
        locator.register("config", mock_config)

        try:
            code = "def a(): pass\ndef b(): pass"
            chunks = chunker.chunk_code(code)  # No config passed
            # Merge should be disabled from ServiceLocator config
            assert len(chunks) >= 2
        finally:
            ServiceLocator.reset()


class TestChunkingConfig:
    """Test ChunkingConfig dataclass."""

    def test_default_values(self):
        """Default values are sensible."""
        config = ChunkingConfig()
        assert (
            config.enable_greedy_merge is False
        )  # Opt-in behavior (changed from True)
        assert config.min_chunk_tokens == 50
        assert config.max_merged_tokens == 1000
        assert config.token_estimation == "whitespace"
        assert config.enable_large_node_splitting is False
        assert config.max_chunk_lines == 100

    def test_custom_values(self):
        """Custom values are respected."""
        config = ChunkingConfig(
            enable_greedy_merge=False,
            min_chunk_tokens=100,
            max_merged_tokens=500,
            token_estimation="tiktoken",
        )
        assert config.enable_greedy_merge is False
        assert config.min_chunk_tokens == 100
        assert config.max_merged_tokens == 500
        assert config.token_estimation == "tiktoken"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
