"""Unit tests for cAST greedy sibling merging algorithm."""

from unittest.mock import MagicMock, patch

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

        # tree-sitter-python is a hard dependency (pyproject.toml), not
        # optional -- PythonChunker() never raises ValueError (its __init__
        # is a plain attribute assignment; grammar loading is lazy and
        # unrelated to construction), so the skip masked no real scenario.
        return PythonChunker()

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
        assert result.metadata["merged_from"] == ["MyClass.foo", "MyClass.bar"]
        assert result.parent_class == "MyClass"

    def test_merge_sorts_members_by_source_position(self, chunker):
        """Out-of-emission-order members (module_preamble last) sort by line.

        Regression: the chunker emits module_preamble after symbol chunks;
        trusting emission order produced inverted line ranges (e.g. 79-11).
        """
        chunks = [
            TreeSitterChunk(
                content="def tail(): pass",
                start_line=79,
                end_line=80,
                node_type="function_definition",
                language="python",
                metadata={"name": "tail"},
            ),
            TreeSitterChunk(
                content="import os",
                start_line=1,
                end_line=11,
                node_type="module_preamble",
                language="python",
                metadata={"name": "module_preamble"},
            ),
        ]
        result = chunker._create_merged_chunk(chunks)

        assert result.start_line == 1
        assert result.end_line == 80
        assert result.metadata["merged_from"] == ["module_preamble", "tail"]
        # Content must be in source order too
        assert result.content.index("import os") < result.content.index("def tail")

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


class TestChunkCodeWithMerging:
    """Test chunk_code() with greedy merge integration."""

    @pytest.fixture
    def chunker(self):
        """Create a concrete chunker for testing."""
        from chunking.languages.python import PythonChunker

        # tree-sitter-python is a hard dependency (pyproject.toml), not
        # optional -- see TestCreateMergedChunk.chunker above for why the
        # skip-on-ValueError was dead code.
        return PythonChunker()

    def test_merge_disabled_by_config(self, chunker):
        """Merge is skipped when disabled in config."""
        code = """
def a(): pass
def b(): pass
def c(): pass
"""
        config = ChunkingConfig()
        chunks = chunker.chunk_code(code, config=config)
        # Should have 3 separate function chunks
        assert len(chunks) >= 3

    def test_merge_enabled_by_config(self, chunker):
        """chunk_code returns raw AST chunks without merging."""
        # Three tiny functions - returned as separate chunks
        code = """
def a(): pass
def b(): pass
def c(): pass
"""
        config = ChunkingConfig(
            min_chunk_tokens=50,  # These functions are < 50 tokens
            max_merged_tokens=1000,
        )
        chunks = chunker.chunk_code(code, config=config)
        # chunk_code returns raw AST chunks (merging happens later during indexing)
        assert len(chunks) == 3
        assert all(c.node_type == "function_definition" for c in chunks)

    def test_config_fetched_when_not_provided(self, chunker):
        """Config is fetched from get_search_config when not explicitly passed."""
        mock_config = MagicMock()
        mock_config.chunking = ChunkingConfig()

        with patch("search.config.get_search_config", return_value=mock_config):
            code = "def a(): pass\ndef b(): pass"
            chunks = chunker.chunk_code(code)  # No config passed
            # Should work with default config
            assert len(chunks) >= 2


class TestChunkingConfig:
    """Test ChunkingConfig dataclass."""

    def test_default_values(self):
        """Default values are sensible."""
        config = ChunkingConfig()
        assert config.min_chunk_tokens == 50
        assert config.max_merged_tokens == 400
        assert config.token_estimation == "whitespace"
        assert config.enable_large_node_splitting is True
        assert config.max_chunk_lines == 100
        assert config.size_method == "tokens"

    def test_custom_values(self):
        """Custom values are respected."""
        config = ChunkingConfig(
            min_chunk_tokens=100,
            max_merged_tokens=500,
            token_estimation="tiktoken",
            size_method="characters",
        )
        assert config.min_chunk_tokens == 100
        assert config.max_merged_tokens == 500
        assert config.token_estimation == "tiktoken"
        assert config.size_method == "characters"
