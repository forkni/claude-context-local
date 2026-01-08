"""Unit tests for community-based chunk merging (Phase 1)."""

from chunking.languages.base import TreeSitterChunk
from chunking.languages.python import PythonChunker
from search.config import ChunkingConfig


class TestCommunityMerge:
    """Tests for community-based merge functionality."""

    def create_test_chunk(
        self,
        content: str,
        start_line: int,
        end_line: int,
        parent_class: str = None,
        community_id: int = None,
    ) -> TreeSitterChunk:
        """Helper to create test chunks."""
        return TreeSitterChunk(
            content=content,
            start_line=start_line,
            end_line=end_line,
            node_type="function",
            language="python",
            metadata={},
            parent_class=parent_class,
            community_id=community_id,
        )

    def test_community_merge_same_community(self):
        """Chunks with same community_id merge together."""
        chunker = PythonChunker()

        # Three small chunks (10 tokens each) in same community
        chunks = [
            self.create_test_chunk("def foo(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def bar(): pass", 3, 4, community_id=0),
            self.create_test_chunk("def baz(): pass", 5, 6, community_id=0),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # All 3 should merge into 1 (same community)
        assert orig == 3
        assert final == 1
        assert len(merged) == 1

    def test_community_merge_different_communities(self):
        """Chunks with different community_id stay separate."""
        chunker = PythonChunker()

        # Three small chunks in different communities
        chunks = [
            self.create_test_chunk("def foo(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def bar(): pass", 3, 4, community_id=1),
            self.create_test_chunk("def baz(): pass", 5, 6, community_id=2),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # All should stay separate (different communities)
        assert orig == 3
        assert final == 3
        assert len(merged) == 3

    def test_community_merge_respects_token_limit(self):
        """Even same community splits at max_tokens."""
        chunker = PythonChunker()

        # Two chunks in same community, but large content
        chunks = [
            self.create_test_chunk(
                "def foo(): " + "x = 1\n" * 100, 1, 100, community_id=0
            ),  # ~200 tokens
            self.create_test_chunk(
                "def bar(): " + "y = 2\n" * 100, 101, 200, community_id=0
            ),  # ~200 tokens
        ]

        # Merge with max_merged_tokens=300
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, max_merged_tokens=300, use_community_boundary=True
        )

        # Should stay separate (would exceed max_merged_tokens)
        assert final == 2
        assert len(merged) == 2

    def test_community_merge_disabled_uses_parent_class(self):
        """Config disable falls back to parent_class."""
        chunker = PythonChunker()

        # Two chunks: same parent_class but different community
        chunks = [
            self.create_test_chunk(
                "def foo(): pass", 1, 2, parent_class="MyClass", community_id=0
            ),
            self.create_test_chunk(
                "def bar(): pass", 3, 4, parent_class="MyClass", community_id=1
            ),
        ]

        # Merge with community boundary DISABLED (use parent_class)
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=False
        )

        # Should merge (same parent_class, community_id ignored)
        assert final == 1
        assert len(merged) == 1

    def test_community_merge_mixed_boundaries(self):
        """Complex case: some same community, some different."""
        chunker = PythonChunker()

        # 5 chunks: [0, 0, 1, 1, 2]
        chunks = [
            self.create_test_chunk("def a(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def b(): pass", 3, 4, community_id=0),
            self.create_test_chunk("def c(): pass", 5, 6, community_id=1),
            self.create_test_chunk("def d(): pass", 7, 8, community_id=1),
            self.create_test_chunk("def e(): pass", 9, 10, community_id=2),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # Should merge into 3 groups: [0+0], [1+1], [2]
        assert orig == 5
        assert final == 3
        assert len(merged) == 3

    def test_community_merge_large_chunk_not_merged(self):
        """Large chunks don't merge even if same community."""
        chunker = PythonChunker()

        # Two chunks: one large (100 tokens), one small (10 tokens), same community
        chunks = [
            self.create_test_chunk(
                "def foo(): " + "x = 1\n" * 50, 1, 50, community_id=0
            ),  # ~100 tokens
            self.create_test_chunk(
                "def bar(): pass", 51, 52, community_id=0
            ),  # ~3 tokens
        ]

        # Merge with min_tokens=50
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # Large chunk stays separate, small chunk added directly
        # Result: [large_chunk, small_chunk] (no merge because first is large)
        assert final == 2

    def test_community_merge_none_community_id(self):
        """Chunks with None community_id handled gracefully."""
        chunker = PythonChunker()

        # Three chunks: [None, None, 0]
        chunks = [
            self.create_test_chunk("def a(): pass", 1, 2, community_id=None),
            self.create_test_chunk("def b(): pass", 3, 4, community_id=None),
            self.create_test_chunk("def c(): pass", 5, 6, community_id=0),
        ]

        # Merge with community boundary enabled
        merged, orig, final = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # First two should merge (both None), third separate
        assert final == 2

    def test_community_id_field_exists(self):
        """TreeSitterChunk has community_id field."""
        chunk = TreeSitterChunk(
            content="test",
            start_line=1,
            end_line=2,
            node_type="function",
            language="python",
            metadata={},
        )

        # community_id should be None by default
        assert hasattr(chunk, "community_id")
        assert chunk.community_id is None

        # Should be settable
        chunk.community_id = 5
        assert chunk.community_id == 5

    def test_community_merge_preserves_content(self):
        """Merged chunks preserve all content."""
        chunker = PythonChunker()

        chunks = [
            self.create_test_chunk("def foo(): pass", 1, 2, community_id=0),
            self.create_test_chunk("def bar(): pass", 3, 4, community_id=0),
        ]

        merged, _, _ = chunker._greedy_merge_small_chunks(
            chunks, min_tokens=50, use_community_boundary=True
        )

        # Merged chunk should contain both functions
        assert "def foo(): pass" in merged[0].content
        assert "def bar(): pass" in merged[0].content

    def test_config_integration(self):
        """ChunkingConfig has community_resolution field (auto-select architecture)."""
        config = ChunkingConfig()

        # community_resolution field should exist with default 1.0
        assert hasattr(config, "community_resolution")
        assert config.community_resolution == 1.0

        # Should be settable (tuning parameter for Louvain algorithm)
        config.community_resolution = 1.5
        assert config.community_resolution == 1.5

        # enable_community_merge no longer exists (auto-enabled for full index)
        assert not hasattr(config, "enable_community_merge")
        assert not hasattr(config, "enable_community_detection")
